"""Algebraic degree UPPER BOUNDS for Asterion-256 (not security proofs).

The max-plus propagation below discards monomial cancellations and shared
dependencies. A calculated bound of 511 does NOT establish degree 511, and
neither would establish that cube or higher-order attacks are impossible.
"""
from __future__ import annotations

import argparse
from typing import Any

from stats_utils import format_table

STATE_BITS = 512
LANE_BITS = 64
MAX_DEGREE = STATE_BITS - 1  # Conservative upper cap for balanced full-state coordinates


def add_degree_upper_bound(a: list[int], b: list[int]) -> list[int]:
    """Conservative algebraic-degree bounds of modular addition output bits."""
    carry = 0
    bounds: list[int] = []
    for i in range(len(a)):
        bounds.append(min(MAX_DEGREE, max(a[i], b[i], carry)))
        carry = min(MAX_DEGREE, max(a[i] + b[i], max(a[i], b[i]) + carry))
    return bounds


def rotate_bounds(a: list[int], bits: int) -> list[int]:
    return [a[(i - bits) % len(a)] for i in range(len(a))]


def xor_bounds(a: list[int], b: list[int]) -> list[int]:
    return [max(x, y) for x, y in zip(a, b)]


def mix_bounds(s: list[list[int]], a: int, b: int, c: int, d: int,
               r0: int, r1: int, r2: int, r3: int) -> None:
    s[a] = add_degree_upper_bound(s[a], s[b])
    s[d] = rotate_bounds(xor_bounds(s[d], s[a]), r0)
    s[c] = add_degree_upper_bound(s[c], s[d])
    s[b] = rotate_bounds(xor_bounds(s[b], s[c]), r1)
    s[a] = add_degree_upper_bound(s[a], s[b])
    s[d] = rotate_bounds(xor_bounds(s[d], s[a]), r2)
    s[c] = add_degree_upper_bound(s[c], s[d])
    s[b] = rotate_bounds(xor_bounds(s[b], s[c]), r3)


def exact_addition_anf_degrees(word_bits: int = 4) -> list[int]:
    """Exhaustive Mobius transform: exact ANF degree of a SMALL addition."""
    if word_bits < 1 or word_bits > 6:
        raise ValueError("Exact local example limited to 1..6 bits")
    variables = 2 * word_bits
    size = 1 << variables
    bitmask = (1 << word_bits) - 1
    degrees = []
    for output_bit in range(word_bits):
        truth = [
            (((((input_code & bitmask) + (input_code >> word_bits)) & bitmask)
                >> output_bit) & 1)
            for input_code in range(size)
        ]
        for i in range(variables):
            for mask in range(size):
                if mask & (1 << i):
                    truth[mask] ^= truth[mask ^ (1 << i)]
        degrees.append(max((code.bit_count() for code, v in enumerate(truth) if v), default=0))
    return degrees


def run_algebraic_degree_analysis(max_rounds: int = 14) -> dict[str, Any]:
    if not 1 <= max_rounds <= 14:
        raise ValueError("rounds must be in 1..14")
    s = [[1] * LANE_BITS for _ in range(8)]
    round_data: list[dict[str, Any]] = []
    first_bound_ceiling: int | None = None
    # spec indexes rounds from zero; rnd+1 is only a display label.
    for rnd in range(max_rounds):
        mix_bounds(s, 0, 1, 2, 3, 32, 21, 17, 13)
        mix_bounds(s, 4, 5, 6, 7, 31, 23, 16, 11)
        mix_bounds(s, 0, 5, 2, 7, 27, 19, 15, 9)
        mix_bounds(s, 4, 1, 6, 3, 25, 18, 14, 7)
        s[1], s[5], s[3], s[7] = s[5], s[3], s[7], s[1]
        s[2], s[6] = s[6], s[2]
        for lane, mult in ((1, 7), (3, 11), (5, 17), (7, 23)):
            s[lane] = rotate_bounds(s[lane], 1 + ((rnd * mult) % 63))
        values = [v for lane in s for v in lane]
        row = {
            "round": rnd + 1, "min_bound": min(values),
            "max_bound": max(values), "mean_bound": sum(values) / len(values),
            "at_upper_cap_count": sum(x == MAX_DEGREE for x in values),
        }
        round_data.append(row)
        if first_bound_ceiling is None and row["min_bound"] == MAX_DEGREE:
            first_bound_ceiling = rnd + 1
    exact_toy = exact_addition_anf_degrees(4)
    expected_bounds = add_degree_upper_bound([1] * 4, [1] * 4)
    if any(e > b for e, b in zip(exact_toy, expected_bounds)):
        raise AssertionError("Local modular-addition upper bound refuted")
    return {
        "status": "UPPER_BOUNDS_ONLY",
        "rounds": round_data,
        "upper_bound_ceiling_round": first_bound_ceiling,
        "verified_exact_4bit_add_degrees": exact_toy,
        "verified_upper_4bit_add_bounds": expected_bounds,
        "actual_512bit_degrees": None,
        "security_margin": None,
    }


def print_report(res: dict[str, Any]) -> None:
    print("\nALGEBRAIC DEGREE UPPER BOUNDS — NOT EXACT DEGREES")
    print(format_table(
        ["Round", "min bound", "mean bound", "max bound", "at ceiling"],
        [[str(x["round"]), str(x["min_bound"]),
          f'{x["mean_bound"]:.2f}', str(x["max_bound"]),
          str(x["at_upper_cap_count"])] for x in res["rounds"]]
    ))
    print("Exact 4-bit addition degree:", res["verified_exact_4bit_add_degrees"])
    print("Conservative 4-bit bound:", res["verified_upper_4bit_add_bounds"])
    print("Actual full-permutation algebraic degrees: UNKNOWN")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=14)
    args = parser.parse_args()
    print_report(run_algebraic_degree_analysis(args.rounds))
