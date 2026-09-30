"""Strict Avalanche Criterion (SAC) and Bit Independence Criterion (BIC) analysis for Asterion-256.

Normative verification of Webster & Tavares (1985) avalanche properties on full hash outputs.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "reference") not in sys.path:
    sys.path.insert(0, str(ROOT / "reference"))
if str(ROOT / "analysis") not in sys.path:
    sys.path.insert(0, str(ROOT / "analysis"))

from asterion256 import asterion256_bytes
from stats_utils import bytes_to_bits, count_set_bits, format_table, sac_metrics


def evaluate_sac_for_length(
    msg_len_bytes: int,
    samples: int = 100,
    max_input_bits: int = 256,
    seed: int = 42,
) -> dict[str, Any]:
    """Evaluate SAC for a specific message byte length over multiple random samples."""
    rng = random.Random(seed)
    if msg_len_bytes == 1:
        # 1-byte messages: evaluate exhaustively over all 128 disjoint pairs per bit
        tested_bits = list(range(8))
        counts = [[0] * 256 for _ in range(8)]
        hamming_distances: list[int] = []
        effective_samples = 128
        t0 = time.perf_counter()
        for bit in range(8):
            for m in range(256):
                if (m >> bit) & 1 == 0:
                    h1 = bytes_to_bits(asterion256_bytes(bytes([m])))
                    h2 = bytes_to_bits(asterion256_bytes(bytes([m ^ (1 << bit)])))
                    hd = sum(1 for b1, b2 in zip(h1, h2) if b1 != b2)
                    hamming_distances.append(hd)
                    for j in range(256):
                        if h1[j] != h2[j]:
                            counts[bit][j] += 1
        elapsed = time.perf_counter() - t0
        metrics = sac_metrics(counts, effective_samples)
        mean_hd = sum(hamming_distances) / len(hamming_distances) if hamming_distances else 0.0
        min_hd = min(hamming_distances) if hamming_distances else 0
        max_hd = max(hamming_distances) if hamming_distances else 0
        return {
            "msg_len_bytes": 1,
            "input_bits_tested": 8,
            "samples": effective_samples,
            "total_probes": 8 * effective_samples,
            "elapsed_sec": elapsed,
            "mean_hd": mean_hd,
            "min_hd": min_hd,
            "max_hd": max_hd,
            **metrics,
        }

    total_input_bits = msg_len_bytes * 8

    # If message is long, systematically sample up to max_input_bits to bound runtime
    if total_input_bits <= max_input_bits:
        tested_bits = list(range(total_input_bits))
    else:
        step = total_input_bits / max_input_bits
        tested_bits = [int(i * step) for i in range(max_input_bits)]

    counts = [[0] * 256 for _ in tested_bits]
    hamming_distances = []

    t0 = time.perf_counter()

    for _ in range(samples):
        msg = bytearray(rng.getrandbits(8) for _ in range(msg_len_bytes))
        h_orig = asterion256_bytes(bytes(msg))
        bits_orig = bytes_to_bits(h_orig)

        for row_idx, in_bit in enumerate(tested_bits):
            byte_idx = in_bit // 8
            bit_idx = in_bit % 8

            perturbed = bytearray(msg)
            perturbed[byte_idx] ^= 1 << bit_idx
            h_pert = asterion256_bytes(bytes(perturbed))
            bits_pert = bytes_to_bits(h_pert)

            diff_bytes = bytes(b1 ^ b2 for b1, b2 in zip(h_orig, h_pert))
            hd = count_set_bits(diff_bytes)
            hamming_distances.append(hd)

            for out_bit in range(256):
                if bits_orig[out_bit] != bits_pert[out_bit]:
                    counts[row_idx][out_bit] += 1

    elapsed = time.perf_counter() - t0
    metrics = sac_metrics(counts, samples)

    mean_hd = sum(hamming_distances) / len(hamming_distances) if hamming_distances else 0.0
    min_hd = min(hamming_distances) if hamming_distances else 0
    max_hd = max(hamming_distances) if hamming_distances else 0

    return {
        "msg_len_bytes": msg_len_bytes,
        "input_bits_tested": len(tested_bits),
        "samples": samples,
        "total_probes": len(tested_bits) * samples,
        "elapsed_sec": elapsed,
        "mean_hd": mean_hd,
        "min_hd": min_hd,
        "max_hd": max_hd,
        **metrics,
    }


def evaluate_bit_independence(
    msg_len_bytes: int = 32,
    samples: int = 200,
    seed: int = 777,
) -> dict[str, float]:
    """Evaluate Bit Independence Criterion (BIC) by measuring output pair correlation."""
    rng = random.Random(seed)
    # Collect diff vectors for bit 0 flips
    diff_matrix: list[list[int]] = []

    for _ in range(samples):
        msg = bytearray(rng.getrandbits(8) for _ in range(msg_len_bytes))
        h_orig = asterion256_bytes(bytes(msg))
        bits_orig = bytes_to_bits(h_orig)

        msg[0] ^= 1  # flip input bit 0
        h_pert = asterion256_bytes(bytes(msg))
        bits_pert = bytes_to_bits(h_pert)

        diff = [1 if bits_orig[i] != bits_pert[i] else 0 for i in range(256)]
        diff_matrix.append(diff)

    # Compute correlation between output pairs (sample 100 pairs)
    correlations: list[float] = []
    pairs = [(i, (i + 37) % 256) for i in range(100)]

    for j, k in pairs:
        col_j = [diff_matrix[s][j] for s in range(samples)]
        col_k = [diff_matrix[s][k] for s in range(samples)]
        mean_j = sum(col_j) / samples
        mean_k = sum(col_k) / samples
        var_j = sum((x - mean_j) ** 2 for x in col_j)
        var_k = sum((x - mean_k) ** 2 for x in col_k)
        if var_j > 0 and var_k > 0:
            cov = sum((col_j[s] - mean_j) * (col_k[s] - mean_k) for s in range(samples))
            r = cov / math.sqrt(var_j * var_k)
            correlations.append(abs(r))

    mean_abs_corr = sum(correlations) / len(correlations) if correlations else 0.0
    max_abs_corr = max(correlations) if correlations else 0.0

    return {
        "mean_abs_correlation": mean_abs_corr,
        "max_abs_correlation": max_abs_corr,
    }


def run_avalanche_tests(quick: bool = False) -> tuple[list[dict[str, Any]], bool]:
    """Execute full SAC analysis across key boundary lengths."""
    samples = 50 if quick else 200
    lengths = [1, 16, 31, 32, 33, 64] if not quick else [1, 32, 33]

    print(f"[*] Running Strict Avalanche Criterion (SAC) tests ({samples} samples per length)...")

    results = []
    all_passed = True

    for length in lengths:
        res = evaluate_sac_for_length(
            msg_len_bytes=length,
            samples=samples,
            max_input_bits=256 if not quick else 128,
        )
        results.append(res)
        if not res["passed"]:
            all_passed = False

    bic = evaluate_bit_independence(samples=100 if quick else 300)

    # Format table
    headers = [
        "Message Len", "Samples", "Mean HW (256)", "Mean Prob",
        "Empirical MAD", "Expected MAD", "Max Dev", "Chi-Square p-val", "Status",
    ]
    rows = []
    for r in results:
        rows.append([
            f"{r['msg_len_bytes']} bytes",
            str(r["samples"]),
            f"{r['mean_hd']:6.2f}",
            f"{r['mean_p']:.4f}",
            f"{r['mad']:.4f}",
            f"{r['expected_mad']:.4f}",
            f"{r['max_dev']:.4f}",
            f"{r['p_value']:.4f}",
            "PASS" if r["passed"] else "FAIL",
        ])

    print("\n" + format_table(headers, rows))
    print(f"\n- Bit Independence Criterion (BIC) mean |r|: {bic['mean_abs_correlation']:.4f} (ideal: ~0.00)")
    print(f"- Overall SAC Status: {'PASS' if all_passed else 'FAIL'}")

    return results, all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Asterion-256 SAC / Avalanche Analysis")
    parser.add_argument("--quick", action="store_true", help="Run with fewer samples for rapid check")
    args = parser.parse_args()
    _, success = run_avalanche_tests(quick=args.quick)
    sys.exit(0 if success else 1)
