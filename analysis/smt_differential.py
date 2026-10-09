"""Exploratory Asterion differential research.

This is NOT a proof of collision resistance or a full-round security margin.
All XOR-difference probabilities here are exact only for the identified
small modular-addition model. The optional SMT experiment searches for
witnesses in a reduced-word surrogate, not the 64-bit construction.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REF_DIR = str(Path(__file__).resolve().parents[1] / 'reference')
if REF_DIR not in sys.path:
    sys.path.insert(0, REF_DIR)

from stats_utils import format_table

try:
    import z3
except ImportError:
    z3 = None


def addition_xor_distribution(alpha: int, beta: int, word_bits: int = 8) -> dict[int, int]:
    """Exact XOR difference histogram for z=(x+y) mod 2**word_bits.

    The histogram has 2**(2*word_bits) equiprobable operand pairs.
    Restrict to <=8-bit words to keep this reference computation bounded.
    """
    if not 1 <= word_bits <= 8:
        raise ValueError("word_bits must be in 1..8")
    n = 1 << word_bits
    if not (0 <= alpha < n and 0 <= beta < n):
        raise ValueError("differences exceed word width")
    mask = n - 1
    counts: dict[int, int] = {}
    for x in range(n):
        for y in range(n):
            gamma = ((x + y) & mask) ^ (((x ^ alpha) + (y ^ beta)) & mask)
            counts[gamma] = counts.get(gamma, 0) + 1
    return counts


def addition_xor_probability(alpha: int, beta: int, gamma: int, word_bits: int = 8) -> float:
    counts = addition_xor_distribution(alpha, beta, word_bits)
    return counts.get(gamma, 0) / float(1 << (2 * word_bits))


def exact_word_permute(state: list[int], rounds: int = 1, word_bits: int = 4) -> list[int]:
    """Explicit surrogate: truncate constants and rotate modulo word_bits.

    For word_bits=64 this construction matches the Asterion permutation.
    Reduced widths are ONLY models, not security results for Asterion-256.
    """
    from asterion256 import ROUND_CONSTANTS

    if not 1 <= word_bits <= 64 or not 0 <= rounds <= len(ROUND_CONSTANTS):
        raise ValueError("invalid reduced-round model parameters")
    mask = (1 << word_bits) - 1
    s = [v & mask for v in state]

    def rot(x: int, n: int) -> int:
        n %= word_bits
        return ((x << n) | (x >> (word_bits - n))) & mask if n else x & mask

    def mix(a: int, b: int, c: int, d: int, rs: tuple[int, int, int, int]) -> None:
        s[a] = (s[a] + s[b]) & mask
        s[d] = rot(s[d] ^ s[a], rs[0])
        s[c] = (s[c] + s[d]) & mask
        s[b] = rot(s[b] ^ s[c], rs[1])
        s[a] = (s[a] + s[b]) & mask
        s[d] = rot(s[d] ^ s[a], rs[2])
        s[c] = (s[c] + s[d]) & mask
        s[b] = rot(s[b] ^ s[c], rs[3])

    for rnd in range(rounds):
        rc = ROUND_CONSTANTS[rnd] & mask
        s[0] ^= rc
        s[4] ^= rot(rc, 29)
        s[7] = (s[7] + (rnd + 1) * 0x9E3779B9) & mask
        mix(0, 1, 2, 3, (32, 21, 17, 13))
        mix(4, 5, 6, 7, (31, 23, 16, 11))
        mix(0, 5, 2, 7, (27, 19, 15, 9))
        mix(4, 1, 6, 3, (25, 18, 14, 7))
        s[1], s[5], s[3], s[7] = s[5], s[3], s[7], s[1]
        s[2], s[6] = s[6], s[2]
        for lane, mul in ((1, 7), (3, 11), (5, 17), (7, 23)):
            s[lane] = rot(s[lane], 1 + ((rnd * mul) % 63))
    return s


def exact_word_permute_z3(state: list[Any], rounds: int = 1, word_bits: int = 4) -> list[Any]:
    """Encode BOTH actual operand streams using bit-vector modular addition."""
    if z3 is None:
        raise RuntimeError("Install z3-solver to run the optional SMT experiment")
    from asterion256 import ROUND_CONSTANTS

    mask = (1 << word_bits) - 1
    s = list(state)

    def rot(x: Any, n: int) -> Any:
        return z3.RotateLeft(x, n % word_bits)

    def mix(a: int, b: int, c: int, d: int, rs: tuple[int, int, int, int]) -> None:
        s[a] = s[a] + s[b]
        s[d] = rot(s[d] ^ s[a], rs[0])
        s[c] = s[c] + s[d]
        s[b] = rot(s[b] ^ s[c], rs[1])
        s[a] = s[a] + s[b]
        s[d] = rot(s[d] ^ s[a], rs[2])
        s[c] = s[c] + s[d]
        s[b] = rot(s[b] ^ s[c], rs[3])

    for rnd in range(rounds):
        rc = ROUND_CONSTANTS[rnd] & mask
        s[0] = s[0] ^ z3.BitVecVal(rc, word_bits)
        s[4] = s[4] ^ rot(z3.BitVecVal(rc, word_bits), 29)
        s[7] = s[7] + z3.BitVecVal((rnd + 1) * 0x9E3779B9 & mask, word_bits)
        mix(0, 1, 2, 3, (32, 21, 17, 13))
        mix(4, 5, 6, 7, (31, 23, 16, 11))
        mix(0, 5, 2, 7, (27, 19, 15, 9))
        mix(4, 1, 6, 3, (25, 18, 14, 7))
        s[1], s[5], s[3], s[7] = s[5], s[3], s[7], s[1]
        s[2], s[6] = s[6], s[2]
        for lane, mul in ((1, 7), (3, 11), (5, 17), (7, 23)):
            s[lane] = rot(s[lane], 1 + ((rnd * mul) % 63))
    return s


def smt_reduced_round_witness(word_bits: int = 4, rounds: int = 1, timeout_ms: int = 5000) -> dict[str, Any]:
    """Find a valid toy-model single-bit input difference and minimize output HW.

    The Optimize objective is only a search heuristic. Do NOT call its result
    a probability bound, attack complexity, or security margin.
    """
    if z3 is None:
        return {"status": "NOT_RUN", "reason": "z3-solver not installed"}
    if not 2 <= word_bits <= 8 or not 1 <= rounds <= 3:
        raise ValueError("toy solver limited to 2..8 bit words, 1..3 rounds")
    a = [z3.BitVec(f"a{i}", word_bits) for i in range(8)]
    b = [z3.BitVec(f"b{i}", word_bits) for i in range(8)]
    mask = (1 << word_bits) - 1
    solver = z3.Optimize()
    solver.set(timeout=timeout_ms)
    # Fix an input XOR difference (one bit in lane zero).
    for i in range(8):
        solver.add(b[i] == (a[i] ^ z3.BitVecVal(1 if i == 0 else 0, word_bits)))
    out_a = exact_word_permute_z3(a, rounds, word_bits)
    out_b = exact_word_permute_z3(b, rounds, word_bits)
    delta = [out_a[i] ^ out_b[i] for i in range(8)]
    bit_count = z3.Sum([
        z3.If(z3.Extract(bit, bit, d) == z3.BitVecVal(1, 1), 1, 0)
        for d in delta for bit in range(word_bits)
    ])
    solver.minimize(bit_count)
    status = solver.check()
    if status != z3.sat:
        return {"status": str(status), "word_bits": word_bits, "rounds": rounds}
    model = solver.model()
    base = [model.eval(x).as_long() & mask for x in a]
    peer = [model.eval(x).as_long() & mask for x in b]
    oa = exact_word_permute(base, rounds, word_bits)
    ob = exact_word_permute(peer, rounds, word_bits)
    observed = sum((x ^ y).bit_count() for x, y in zip(oa, ob))
    reported = model.eval(bit_count).as_long()
    if reported != observed or (base[0] ^ peer[0]) != 1 or any(base[i] != peer[i] for i in range(1, 8)):
        raise AssertionError("SMT witness failed independent executable toy-model replay")
    return {
        "status": "SAT_WITNESS_VALIDATED",
        "word_bits": word_bits, "rounds": rounds,
        "input_hw": 1, "output_hw": observed,
        "base_state": [hex(x) for x in base],
        "paired_state": [hex(x) for x in peer],
        "claim": "toy-model witness only; no full-size security conclusion",
    }


def run_smt_differential_suite(quick: bool = False) -> dict[str, Any]:
    """Return factual findings; no invented security margins or PASS verdict."""
    examples = []
    for width in (4, 8):
        alpha = 1 << (width - 1)
        dist = addition_xor_distribution(alpha, 0, width)
        expected = 1 << (2 * width)
        assert dist == {alpha: expected}, "MSB counterexample mismatch"
        examples.append({
            "word_bits": width, "alpha": hex(alpha), "beta": "0x0",
            "gamma": hex(alpha), "probability": 1.0, "differential_weight": 0.0,
        })
    witness = smt_reduced_round_witness(word_bits=4, rounds=1, timeout_ms=1500 if quick else 5000)
    return {
        "status": "EXPLORATORY_ONLY", "full_round_security_margin": None,
        "addition_counterexamples": examples,
        "toy_solver": witness,
        "safety_conclusion": "Unknown; no differential bound is established",
    }


def print_report(results: dict[str, Any]) -> None:
    print("\nEXPLORATORY DIFFERENTIAL RESEARCH — NO SECURITY PASS/FAIL")
    print(format_table(
        ["word bits", "input XOR", "output XOR", "probability", "weight"],
        [[str(x["word_bits"]), x["alpha"], x["gamma"], "1.0", "0.0"]
         for x in results["addition_counterexamples"]]))
    print("Toy SMT:", results["toy_solver"]["status"])
    if results["toy_solver"]["status"] == "SAT_WITNESS_VALIDATED":
        print("Verified toy output Hamming weight:", results["toy_solver"]["output_hw"])
    print("Full Asterion-256 differential-security margin: UNKNOWN")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    print_report(run_smt_differential_suite(args.quick))
