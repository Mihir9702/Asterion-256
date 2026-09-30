"""Statistical Uniformity and Bias Analysis for Asterion-256.

Performs:
1. NIST SP 800-22 Frequency (Monobit) test.
2. Per-bit position bias / stuck-bit detection across all 256 output positions.
3. Byte-level Chi-Square goodness-of-fit uniformity test (df=255).
4. Evaluations across multiple input distributions:
   - Sequential integer counters ("0", "1", "2", ...)
   - Random byte buffers
   - Low-entropy repeated characters ("a", "aa", ...)
   - Sparse vectors (single bit set in zero block)
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "reference") not in sys.path:
    sys.path.insert(0, str(ROOT / "reference"))
if str(ROOT / "analysis") not in sys.path:
    sys.path.insert(0, str(ROOT / "analysis"))

from asterion256 import asterion256_bytes
from stats_utils import bytes_to_bits, chi2_p_value, format_table, monobit_test


def evaluate_dataset(
    name: str,
    generator: Callable[[int], bytes],
    num_samples: int = 5000,
) -> dict[str, Any]:
    """Evaluate statistical uniformity over a dataset produced by generator."""
    bit_counts = [0] * 256
    byte_counts = [0] * 256
    total_ones = 0
    total_bits = num_samples * 256

    t0 = time.perf_counter()

    for idx in range(num_samples):
        msg = generator(idx)
        digest = asterion256_bytes(msg)

        # Byte counts
        for b in digest:
            byte_counts[b] += 1

        # Bit counts
        bits = bytes_to_bits(digest)
        for bit_idx, bit_val in enumerate(bits):
            if bit_val:
                bit_counts[bit_idx] += 1
                total_ones += 1

    elapsed = time.perf_counter() - t0

    # 1. Monobit test
    one_ratio, monobit_p, monobit_pass = monobit_test(total_ones, total_bits)

    # 2. Per-bit bias test (Z-scores)
    max_z = 0.0
    biased_bits: list[int] = []
    # Bonferroni threshold for 256 tests at alpha = 0.001 -> p = 0.001 / 256 = 3.9e-6 -> |Z| >= 4.61
    z_threshold = 4.5
    for bit_idx, count in enumerate(bit_counts):
        z = abs(2.0 * count - num_samples) / math.sqrt(num_samples)
        if z > max_z:
            max_z = z
        if z > z_threshold:
            biased_bits.append(bit_idx)

    # 3. Byte-level Chi-square test
    total_bytes = num_samples * 32
    expected_byte_count = total_bytes / 256.0
    chi2_bytes = sum(((c - expected_byte_count) ** 2) / expected_byte_count for c in byte_counts)
    byte_chi2_p = chi2_p_value(chi2_bytes, 255)

    passed = bool(monobit_pass and len(biased_bits) == 0 and byte_chi2_p >= 0.001)

    return {
        "dataset": name,
        "samples": num_samples,
        "elapsed_sec": elapsed,
        "one_ratio": one_ratio,
        "monobit_p": monobit_p,
        "monobit_pass": monobit_pass,
        "max_bit_z": max_z,
        "biased_bit_count": len(biased_bits),
        "byte_chi2": chi2_bytes,
        "byte_chi2_p": byte_chi2_p,
        "passed": passed,
    }


def run_uniformity_tests(quick: bool = False) -> tuple[list[dict[str, Any]], bool]:
    """Execute uniformity analysis across multiple input profiles."""
    samples = 2000 if quick else 10000
    rng = random.Random(999)

    print(f"[*] Running statistical uniformity & bias tests ({samples} digests per dataset)...")

    pairs: list[tuple[int, int]] = []
    for p1 in range(256):
        for p2 in range(p1 + 1, 256):
            pairs.append((p1, p2))
            if len(pairs) >= samples:
                break
        if len(pairs) >= samples:
            break

    def make_sparse(i: int) -> bytes:
        b1, b2 = pairs[i]
        buf = bytearray(32)
        buf[b1 // 8] |= 1 << (b1 % 8)
        buf[b2 // 8] |= 1 << (b2 % 8)
        return bytes(buf)

    datasets: list[tuple[str, Callable[[int], bytes]]] = [
        ("Sequential Counters", lambda i: str(i).encode("utf-8")),
        ("Random 32-byte buffers", lambda _: bytes(rng.getrandbits(8) for _ in range(32))),
        ("Low-Entropy (repeated 'a' + index)", lambda i: b"a" * 28 + i.to_bytes(4, "little")),
        ("Sparse 2-Bit Vectors (32-byte)", make_sparse),
    ]

    results = []
    all_passed = True

    for name, gen in datasets:
        res = evaluate_dataset(name, gen, num_samples=samples)
        results.append(res)
        if not res["passed"]:
            all_passed = False

    # Summary table
    headers = [
        "Dataset", "Samples", "One Ratio", "Monobit p-val",
        "Max Bit |Z|", "Biased Bits", "Byte Chi2 p-val", "Status",
    ]
    rows = []
    for r in results:
        rows.append([
            r["dataset"],
            str(r["samples"]),
            f"{r['one_ratio']:.4f}",
            f"{r['monobit_p']:.4f}",
            f"{r['max_bit_z']:.2f}",
            str(r["biased_bit_count"]),
            f"{r['byte_chi2_p']:.4f}",
            "PASS" if r["passed"] else "FAIL",
        ])

    print("\n" + format_table(headers, rows))
    print(f"\n- Overall Uniformity Status: {'PASS' if all_passed else 'FAIL'}")

    return results, all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Asterion-256 Uniformity & Bias Analysis")
    parser.add_argument("--quick", action="store_true", help="Run with fewer samples for rapid check")
    args = parser.parse_args()
    _, success = run_uniformity_tests(quick=args.quick)
    sys.exit(0 if success else 1)
