"""Attack-oriented exploratory research for Asterion-256.

Do not interpret toy-word or sampled results as bounds for the 64-bit
14-round construction. Reproducible inputs, counts and limitations are exported.
"""
from __future__ import annotations
import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "reference"), str(ROOT / "analysis")]
from asterion256 import permute
from smt_differential import exact_word_permute


def state_to_word(state: list[int], bits: int) -> int:
    return sum(lane << (i * bits) for i, lane in enumerate(state))


def small_word_exhaustive(rounds: int = 1, word_bits: int = 2) -> dict:
    """All 2^16 inputs for fixed 1-bit difference of the 16-bit toy permutation."""
    if word_bits != 2 or rounds not in (1, 2):
        raise ValueError("Exhaustive profile: 2-bit words, 1 or 2 rounds")
    output_differences = Counter()
    states = 1 << (8 * word_bits)
    for encoded in range(states):
        lanes = [(encoded >> (word_bits * i)) & 3 for i in range(8)]
        peer = lanes.copy()
        peer[0] ^= 1
        a = state_to_word(exact_word_permute(lanes, rounds, word_bits), word_bits)
        b = state_to_word(exact_word_permute(peer, rounds, word_bits), word_bits)
        delta = a ^ b
        if delta == 0:
            raise AssertionError("Toy permutation lost bijectivity")
        output_differences[delta] += 1
    max_count = max(output_differences.values())
    dominant = min(d for d, count in output_differences.items() if count == max_count)
    return {
        "model": "2-bit-per-lane truncated-constant surrogate, NOT Asterion-256",
        "input_difference": "lane 0, bit 0",
        "rounds": rounds, "enumerated_states": states,
        "distinct_output_differences": len(output_differences),
        "highest_count": max_count,
        "most_frequent_output_difference_hex": hex(dominant),
        "max_observed_differential_probability": max_count / states,
        "cryptographic_claim": "none; surrogate only",
    }


def full_width_sampled_diffusion(seed: int = 20261008, samples: int = 96) -> list[dict]:
    """Search only for sampled low-weight output differences by round."""
    rng = random.Random(seed)
    bases = [[rng.getrandbits(64) for _ in range(8)] for _ in range(samples)]
    flip_positions = [rng.randrange(512) for _ in range(samples)]
    results = []
    for r in range(1, 15):
        histogram = []
        for base, bit in zip(bases, flip_positions):
            other = base.copy()
            other[bit // 64] ^= 1 << (bit % 64)
            a, b = base.copy(), other.copy()
            permute(a, rounds=r)
            permute(b, rounds=r)
            histogram.append(sum((x ^ y).bit_count() for x, y in zip(a, b)))
        results.append({
            "rounds": r, "samples": len(histogram),
            "minimum_output_hw": min(histogram),
            "mean_output_hw": sum(histogram) / len(histogram),
            "maximum_output_hw": max(histogram),
            "security_claim": "none; this cannot bound differential probability",
        })
    return results


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true")
    p.add_argument("--json", default=None)
    args = p.parse_args()
    result = {
        "algorithm": "Asterion-256 v0.1.0",
        "baseline_revision": "f439376b80fb8fd7b3da312639365d2988752a6a",
        "seed": 20261008,
        "method": "fixed seed sampled full-width differences; exhaustive 16-bit surrogate",
        "full_width": full_width_sampled_diffusion(samples=64 if args.quick else 256),
        "toy_differential": [
            small_word_exhaustive(rounds=1, word_bits=2),
            small_word_exhaustive(rounds=2, word_bits=2),
        ],
        "conclusion": "No upper bound on full-round characteristic probabilities established; insufficient for security claims.",
    }
    first = result["full_width"][0]
    count = first["samples"]
    model_se = (128.0 / count) ** 0.5  # random independent 512-bit output differences
    result["one_round_empirical_distinguisher"] = {
        "experiment": "single-bit perturbation of full internal state, 1 permutation round",
        "observed_mean_hw": first["mean_output_hw"],
        "ideal_random_permutation_mean_hw": 256.0,
        "approx_se_under_independent_ideal_samples": model_se,
        "descriptive_deviation_in_se_units":
            (first["mean_output_hw"] - 256.0) / model_se,
        "caution": "an exploratory one-round distinguishability signal only; no 14-round attack or bound",
    }
    print("FULL-WIDTH SAMPLED DIFFERENCES (not a security bound)")
    for row in result["full_width"]:
        print(f'rounds={row["rounds"]:2d}  min={row["minimum_output_hw"]:3d}  mean={row["mean_output_hw"]:7.2f}')
    print("\nEXHAUSTIVE REDUCED WORD SURROGATE RESULTS")
    for row in result["toy_differential"]:
        print(f'rounds={row["rounds"]} states={row["enumerated_states"]} '
              f'max_probability={row["max_observed_differential_probability"]:.6f}')
    print("Asterion-256 14-round security: UNKNOWN")
    if args.json:
        dst = Path(args.json)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("Wrote", dst)


if __name__ == "__main__":
    main()
