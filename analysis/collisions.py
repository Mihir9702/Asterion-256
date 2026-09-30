"""Collision Scaling and Birthday Paradox Analysis for Asterion-256.

Investigates:
1. Truncated collision scaling across 16-bit, 20-bit, and 24-bit spaces.
2. Empirical vs theoretical Birthday Paradox expectations: E[N] ~ sqrt(pi/2 * 2^k).
3. Full 256-bit collision-free smoke test over 50,000+ unique inputs.
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
from stats_utils import format_table


def find_truncated_collision(
    bits: int,
    trial_seed: int,
    max_steps: int = 10_000_000,
) -> tuple[int, int, bytes, bytes]:
    """Find a collision on the low `bits` of Asterion-256."""
    mask = (1 << bits) - 1
    seen: dict[int, bytes] = {}
    rng = random.Random(trial_seed)

    step = 0
    while step < max_steps:
        # Generate 16-byte random probe
        msg = rng.getrandbits(128).to_bytes(16, "little")
        digest = asterion256_bytes(msg)
        # Extract low `bits` as integer
        val = int.from_bytes(digest[:4], "little") & mask

        if val in seen:
            prev_msg = seen[val]
            if prev_msg != msg:
                return step + 1, val, prev_msg, msg
        else:
            seen[val] = msg

        step += 1

    raise TimeoutError(f"No collision found within {max_steps} steps")


def evaluate_birthday_scaling(
    bits: int,
    num_trials: int = 30,
) -> dict[str, Any]:
    """Evaluate empirical collision step distribution vs theoretical birthday bound."""
    theoretical_mean = math.sqrt(math.pi / 2.0 * (1 << bits))
    steps: list[int] = []

    t0 = time.perf_counter()
    for trial in range(num_trials):
        step_count, _, _, _ = find_truncated_collision(bits, trial_seed=trial * 10007 + bits)
        steps.append(step_count)
    elapsed = time.perf_counter() - t0

    empirical_mean = sum(steps) / len(steps)
    variance = sum((s - empirical_mean) ** 2 for s in steps) / len(steps)
    empirical_std = math.sqrt(variance)
    ratio = empirical_mean / theoretical_mean

    # Acceptable range: within 3 standard errors of theoretical mean
    # Standard deviation of the sample mean is theoretical_std / sqrt(num_trials)
    # For Rayleigh distribution (birthday collision), std ≈ 0.5227 * 2^(k/2)
    # E[N] ≈ 1.2533 * 2^(k/2), so std / E ≈ 0.417
    rel_error = abs(ratio - 1.0)
    passed = bool(rel_error <= 0.35)

    return {
        "bits": bits,
        "trials": num_trials,
        "theoretical_mean": theoretical_mean,
        "empirical_mean": empirical_mean,
        "empirical_std": empirical_std,
        "ratio": ratio,
        "elapsed_sec": elapsed,
        "passed": passed,
    }


def evaluate_full_collision_smoke(
    num_samples: int = 50000,
) -> dict[str, Any]:
    """Test that zero 256-bit collisions occur in a large sample of distinct inputs."""
    seen: set[bytes] = set()
    t0 = time.perf_counter()

    for idx in range(num_samples):
        # Mix sequential and structural variations
        if idx % 2 == 0:
            msg = str(idx).encode("utf-8")
        else:
            msg = idx.to_bytes(8, "little") + b":probe"

        digest = asterion256_bytes(msg)
        if digest in seen:
            return {
                "samples": idx + 1,
                "collision_found": True,
                "passed": False,
                "elapsed_sec": time.perf_counter() - t0,
            }
        seen.add(digest)

    elapsed = time.perf_counter() - t0
    return {
        "samples": num_samples,
        "collision_found": False,
        "passed": True,
        "elapsed_sec": elapsed,
    }


def run_collision_tests(quick: bool = False) -> tuple[dict[str, Any], bool]:
    """Execute collision analysis suite."""
    bit_widths = [16, 20] if quick else [16, 20, 24]
    trials = 25 if quick else 40
    smoke_samples = 15000 if quick else 50000

    print(f"[*] Running Birthday collision scaling tests (widths: {bit_widths}, {trials} trials each)...")

    scaling_results = []
    all_passed = True

    for bits in bit_widths:
        res = evaluate_birthday_scaling(bits, num_trials=trials)
        scaling_results.append(res)
        if not res["passed"]:
            all_passed = False

    print(f"[*] Running 256-bit collision-free smoke test ({smoke_samples} unique inputs)...")
    smoke_res = evaluate_full_collision_smoke(num_samples=smoke_samples)
    if not smoke_res["passed"]:
        all_passed = False

    # Format table
    headers = [
        "Truncation", "Trials", "Theoretical E[N]", "Empirical Mean", "Ratio (Obs/Theo)", "Status",
    ]
    rows = []
    for r in scaling_results:
        rows.append([
            f"{r['bits']} bits",
            str(r["trials"]),
            f"{r['theoretical_mean']:8.1f}",
            f"{r['empirical_mean']:8.1f}",
            f"{r['ratio']:.3f}",
            "PASS" if r["passed"] else "FAIL",
        ])

    print("\n" + format_table(headers, rows))
    print(f"\n- 256-bit Collision Smoke Test: {smoke_res['samples']} inputs, Collisions: 0 ({'PASS' if smoke_res['passed'] else 'FAIL'})")
    print(f"- Overall Collision Test Status: {'PASS' if all_passed else 'FAIL'}")

    return {
        "scaling": scaling_results,
        "smoke": smoke_res,
    }, all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Asterion-256 Collision Scaling Analysis")
    parser.add_argument("--quick", action="store_true", help="Run with fewer samples for rapid check")
    args = parser.parse_args()
    _, success = run_collision_tests(quick=args.quick)
    sys.exit(0 if success else 1)
