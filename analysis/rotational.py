"""Rotational Cryptanalysis and Symmetry Breaking Analysis for Asterion-256.

Investigates:
1. Propagation of rotational characteristics: x -> (x <<< k).
2. Rotational difference: Delta_rot(x, k) = permute(x <<< k) ^ (permute(x) <<< k).
3. Evaluates all rotation offsets k in {1, 2, 7, 8, 13, 16, 23, 31, 32}.
4. Quantifies the role of round constants, non-stationary rotations, and carry propagation.
"""

from __future__ import annotations

import argparse
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

from asterion256 import ROUND_CONSTANTS, ROUNDS, mix4, permute, rotl64, u64
from stats_utils import format_table


def rot_state(state: list[int], k: int) -> list[int]:
    """Rotate each 64-bit lane in state left by k bits."""
    return [rotl64(lane, k) for lane in state]


def count_bits_in_state(state: list[int]) -> int:
    """Return total number of set bits across all lanes."""
    return sum(bin(x).count("1") for x in state)


def permute_without_constants(state: list[int], rounds: int = ROUNDS) -> None:
    """Variant permutation with round constants and round-number additions omitted.

    Used strictly for comparative research to isolate the effect of round constants.
    """
    for rnd in range(rounds):
        mix4(state, 0, 1, 2, 3, 32, 21, 17, 13)
        mix4(state, 4, 5, 6, 7, 31, 23, 16, 11)
        mix4(state, 0, 5, 2, 7, 27, 19, 15, 9)
        mix4(state, 4, 1, 6, 3, 25, 18, 14, 7)

        lane1, lane2, lane3 = state[1], state[2], state[3]
        lane5, lane6, lane7 = state[5], state[6], state[7]

        state[1], state[5] = lane5, lane3
        state[3], state[7] = lane7, lane1
        state[2], state[6] = lane6, lane2

        state[1] = rotl64(state[1], 1 + ((rnd * 7) % 63))
        state[3] = rotl64(state[3], 1 + ((rnd * 11) % 63))
        state[5] = rotl64(state[5], 1 + ((rnd * 17) % 63))
        state[7] = rotl64(state[7], 1 + ((rnd * 23) % 63))


def evaluate_rotational_distance(
    k: int,
    rounds: int = 14,
    samples: int = 50,
    seed: int = 42,
    with_constants: bool = True,
) -> dict[str, Any]:
    """Measure the rotational Hamming distance for rotation offset k."""
    rng = random.Random(seed + k)
    diff_hws: list[int] = []

    for _ in range(samples):
        base = [rng.getrandbits(64) for _ in range(8)]
        base_rot = rot_state(base, k)

        s1 = base.copy()
        s2 = base_rot.copy()

        if with_constants:
            permute(s1, rounds=rounds)
            permute(s2, rounds=rounds)
        else:
            permute_without_constants(s1, rounds=rounds)
            permute_without_constants(s2, rounds=rounds)

        # Theoretical rotational image: s1 rotated by k
        s1_rot = rot_state(s1, k)
        # Rotational difference
        diff = [s2[i] ^ s1_rot[i] for i in range(8)]
        diff_hws.append(count_bits_in_state(diff))

    mean_hw = sum(diff_hws) / len(diff_hws)
    min_hw = min(diff_hws)
    max_hw = max(diff_hws)

    return {
        "k": k,
        "rounds": rounds,
        "samples": samples,
        "mean_hw": mean_hw,
        "min_hw": min_hw,
        "max_hw": max_hw,
        "fraction": mean_hw / 512.0,
    }


def evaluate_rotational_by_round(
    k: int = 1,
    samples: int = 40,
) -> list[dict[str, Any]]:
    """Track rotational distance round-by-round from round 1 to round 14."""
    results = []
    for r in range(1, ROUNDS + 1):
        std_res = evaluate_rotational_distance(k=k, rounds=r, samples=samples, with_constants=True)
        no_const_res = evaluate_rotational_distance(k=k, rounds=r, samples=samples, with_constants=False)
        results.append({
            "round": r,
            "std_mean_hw": std_res["mean_hw"],
            "no_const_mean_hw": no_const_res["mean_hw"],
        })
    return results


def run_rotational_tests(quick: bool = False) -> tuple[dict[str, Any], bool]:
    """Execute rotational symmetry and distinguisher analysis."""
    samples = 30 if quick else 100
    offsets = [1, 2, 7, 8, 13, 16, 23, 31, 32]

    print(f"[*] Running rotational symmetry analysis ({samples} samples per offset k)...")

    offset_results = []
    all_passed = True

    for k in offsets:
        res = evaluate_rotational_distance(k=k, rounds=14, samples=samples, with_constants=True)
        offset_results.append(res)
        # Expected: ~256 bits out of 512 (ideal = 0.50). Any value < 200 or > 312 indicates rotational weakness
        if not (230.0 <= res["mean_hw"] <= 282.0):
            all_passed = False

    by_round = evaluate_rotational_by_round(k=1, samples=25 if quick else 60)

    # Format table for offsets
    headers = ["Offset (k)", "Samples", "Min HW", "Mean HW (512)", "Max HW", "Fraction", "Status"]
    rows = []
    for r in offset_results:
        status = "PASS" if (230.0 <= r["mean_hw"] <= 282.0) else "WARN"
        rows.append([
            f"k = {r['k']:2d}",
            str(r["samples"]),
            f"{r['min_hw']:3d}",
            f"{r['mean_hw']:6.2f}",
            f"{r['max_hw']:3d}",
            f"{r['fraction']*100:5.1f}%",
            status,
        ])

    print("\n" + format_table(headers, rows))

    print("\n[*] Round-by-Round Rotational Comparison (k=1): With vs Without Round Constants")
    r_headers = ["Round", "With Constants Mean HW", "Without Constants Mean HW"]
    r_rows = []
    for r in by_round:
        r_rows.append([
            f"Round {r['round']:2d}",
            f"{r['std_mean_hw']:6.2f} / 512",
            f"{r['no_const_mean_hw']:6.2f} / 512",
        ])
    print(format_table(r_headers, r_rows))

    print(f"\n- Rotational Cryptanalysis Status: {'PASS' if all_passed else 'FAIL'}")

    return {
        "offsets": offset_results,
        "by_round": by_round,
    }, all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Asterion-256 Rotational Cryptanalysis")
    parser.add_argument("--quick", action="store_true", help="Run with fewer samples for rapid check")
    args = parser.parse_args()
    _, success = run_rotational_tests(quick=args.quick)
    sys.exit(0 if success else 1)
