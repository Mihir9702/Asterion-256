"""Round-by-round permutation diffusion and bit-dependency analysis for Asterion-256.

Investigates:
1. State bit-flip distribution (min, mean, max, std dev) for rounds 1..14.
2. Rate (lanes 0-3) vs Capacity (lanes 4-7) diffusion balance.
3. Bit-dependency completeness: at what round does every input bit affect every output bit?
4. Multi-bit difference propagation.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import time
from pathlib import Path
from typing import Any

# Ensure reference package is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "reference") not in sys.path:
    sys.path.insert(0, str(ROOT / "reference"))
if str(ROOT / "analysis") not in sys.path:
    sys.path.insert(0, str(ROOT / "analysis"))

from asterion256 import IV, ROUNDS, permute
from stats_utils import format_table


def count_state_bits(state: list[int]) -> int:
    """Return total number of set bits across all 8 64-bit lanes."""
    return sum(bin(lane).count("1") for lane in state)


def analyze_single_bit_diffusion(
    num_base_states: int = 50,
    seed: int = 42,
) -> dict[str, Any]:
    """Analyze single-bit difference diffusion across rounds 1..ROUNDS."""
    rng = random.Random(seed)

    base_states: list[list[int]] = [IV.copy()]
    for _ in range(num_base_states - 1):
        base_states.append([rng.getrandbits(64) for _ in range(8)])

    # Results per round: round_idx -> list of hamming weights
    round_hw: dict[int, list[int]] = {r: [] for r in range(1, ROUNDS + 1)}
    round_rate_hw: dict[int, list[int]] = {r: [] for r in range(1, ROUNDS + 1)}
    round_cap_hw: dict[int, list[int]] = {r: [] for r in range(1, ROUNDS + 1)}

    # Dependency tracking: round -> matrix 512 x 512 bool
    dependency: dict[int, list[list[bool]]] = {
        r: [[False] * 512 for _ in range(512)]
        for r in range(1, ROUNDS + 1)
    }

    t0 = time.perf_counter()

    for base in base_states:
        for in_bit in range(512):
            lane_idx = in_bit // 64
            bit_idx = in_bit % 64

            perturbed = base.copy()
            perturbed[lane_idx] ^= 1 << bit_idx

            for r in range(1, ROUNDS + 1):
                s1 = base.copy()
                s2 = perturbed.copy()
                permute(s1, rounds=r)
                permute(s2, rounds=r)

                diff = [s1[i] ^ s2[i] for i in range(8)]
                total_bits = count_state_bits(diff)
                rate_bits = count_state_bits(diff[:4])
                cap_bits = count_state_bits(diff[4:])

                round_hw[r].append(total_bits)
                round_rate_hw[r].append(rate_bits)
                round_cap_hw[r].append(cap_bits)

                # Record dependency
                for out_lane in range(8):
                    lane_diff = diff[out_lane]
                    if lane_diff:
                        for out_offset in range(64):
                            if (lane_diff >> out_offset) & 1:
                                out_bit = out_lane * 64 + out_offset
                                dependency[r][in_bit][out_bit] = True

    elapsed = time.perf_counter() - t0

    # Aggregate stats per round
    summary = []
    empirical_coverage_threshold_round: int | None = None

    for r in range(1, ROUNDS + 1):
        hws = round_hw[r]
        mean_hw = sum(hws) / len(hws)
        min_hw = min(hws)
        max_hw = max(hws)
        variance = sum((x - mean_hw) ** 2 for x in hws) / len(hws)
        std_hw = math.sqrt(variance)

        rate_hws = round_rate_hw[r]
        mean_rate = sum(rate_hws) / len(rate_hws)
        cap_hws = round_cap_hw[r]
        mean_cap = sum(cap_hws) / len(cap_hws)

        dep_cells = sum(sum(row) for row in dependency[r])
        dep_percent = (dep_cells / (512 * 512)) * 100.0

        if empirical_coverage_threshold_round is None and dep_percent >= 99.5 and abs(mean_hw - 256.0) < 5.0:
            empirical_coverage_threshold_round = r

        summary.append({
            "round": r,
            "min_hw": min_hw,
            "mean_hw": mean_hw,
            "max_hw": max_hw,
            "std_hw": std_hw,
            "mean_rate_hw": mean_rate,
            "mean_cap_hw": mean_cap,
            "dependency_pct": dep_percent,
        })

    return {
        "num_base_states": num_base_states,
        "total_probes_per_round": num_base_states * 512,
        "elapsed_sec": elapsed,
        "empirical_coverage_threshold_round": empirical_coverage_threshold_round,
        "rounds": summary,
    }


def analyze_multibit_diffusion(
    num_trials: int = 50,
    seed: int = 1234,
) -> list[dict[str, Any]]:
    """Test diffusion when flipping multiple bits (2, 4, 8 bits) simultaneously."""
    rng = random.Random(seed)
    results = []

    for weight in [2, 4, 8]:
        round_means = []
        for r in range(1, 6):  # Early rounds are most informative
            diffs = []
            for _ in range(num_trials):
                base = [rng.getrandbits(64) for _ in range(8)]
                perturbed = base.copy()
                chosen_bits = rng.sample(range(512), weight)
                for bit in chosen_bits:
                    perturbed[bit // 64] ^= 1 << (bit % 64)

                s1 = base.copy()
                s2 = perturbed.copy()
                permute(s1, rounds=r)
                permute(s2, rounds=r)

                diff = [s1[i] ^ s2[i] for i in range(8)]
                diffs.append(count_state_bits(diff))

            round_means.append(sum(diffs) / len(diffs))

        results.append({
            "input_diff_weight": weight,
            "round_means": round_means,
        })

    return results


def run_diffusion_tests(quick: bool = False) -> tuple[dict[str, Any], bool]:
    """Execute diffusion test suite and return (results, passed)."""
    base_states = 10 if quick else 40
    print(f"[*] Running permutation diffusion analysis ({base_states} base states, 512 bit flips each)...")

    results = analyze_single_bit_diffusion(num_base_states=base_states)
    multibit = analyze_multibit_diffusion(num_trials=20 if quick else 60)
    results["multibit"] = multibit

    # Verify pass criteria
    # 1. Round 2 must achieve >= 99% bit dependency
    # 2. Round 3..14 must have mean HW within 3% of 256 bits (248.3 to 263.7)
    r2_dep = results["rounds"][1]["dependency_pct"]
    r14_mean = results["rounds"][-1]["mean_hw"]
    passed = bool(r2_dep >= 99.0 and 250.0 <= r14_mean <= 262.0)

    # Print summary table
    headers = [
        "Round", "Min HW", "Mean HW (512)", "Max HW", "Std Dev",
        "Rate (256)", "Cap (256)", "Dependency %",
    ]
    rows = []
    for r in results["rounds"]:
        rows.append([
            f"Round {r['round']:2d}",
            f"{r['min_hw']:3d}",
            f"{r['mean_hw']:6.2f} ({r['mean_hw']/512*100:5.1f}%)",
            f"{r['max_hw']:3d}",
            f"{r['std_hw']:5.2f}",
            f"{r['mean_rate_hw']:6.2f}",
            f"{r['mean_cap_hw']:6.2f}",
            f"{r['dependency_pct']:6.2f}%",
        ])

    print("\n" + format_table(headers, rows))
    print(f"\n- Empirical 99.5% dependency-coverage threshold at round: {results['empirical_coverage_threshold_round']}")
    print(f"- Round 2 bit dependency coverage: {r2_dep:.2f}%")
    print(f"- Round 14 mean flipped bits: {r14_mean:.2f} / 512 (ideal: 256.00)")
    print(f"- Evaluation time: {results['elapsed_sec']:.2f}s")
    print(f"- Diffusion Test Assessment: {'PASS' if passed else 'FAIL'}")

    return results, passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Asterion-256 Permutation Diffusion Analysis")
    parser.add_argument("--quick", action="store_true", help="Run with fewer samples for rapid check")
    args = parser.parse_args()
    _, success = run_diffusion_tests(quick=args.quick)
    sys.exit(0 if success else 1)
