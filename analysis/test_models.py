"""Validation and adversarial controls for RESEARCH MODELS only."""
from __future__ import annotations
import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "analysis"), str(ROOT / "reference")]
from algebraic_degree import (
    add_degree_upper_bound, exact_addition_anf_degrees,
    run_algebraic_degree_analysis, xor_bounds,
)
from smt_differential import (
    addition_xor_distribution, exact_word_permute,
    exact_word_permute_z3, smt_reduced_round_witness, z3,
)
from asterion256 import permute
from stats_utils import chi2_p_value, longest_run_ones_test


class ModelValidation(unittest.TestCase):
    def test_active_addition_can_have_zero_weight(self) -> None:
        for width in (2, 4, 8):
            msb = 1 << (width - 1)
            self.assertEqual(addition_xor_distribution(msb, 0, width), {msb: 1 << (2 * width)})

    def test_histograms_sum_to_all_operand_pairs(self) -> None:
        for width in (2, 4):
            for da in range(1 << width):
                for db in range(1 << width):
                    hist = addition_xor_distribution(da, db, width)
                    self.assertEqual(sum(hist.values()), 1 << (2 * width))

    def test_exact_addition_anf_small_words(self) -> None:
        for width in (1, 2, 3, 4, 5):
            self.assertEqual(exact_addition_anf_degrees(width), list(range(1, width + 1)))
            bound = add_degree_upper_bound([1] * width, [1] * width)
            self.assertTrue(all(actual <= upper for actual, upper in zip(list(range(1, width+1)), bound)))

    def test_bound_is_not_exact_degree(self) -> None:
        self.assertEqual(xor_bounds([1], [1]), [1])
        self.assertEqual(1 ^ 1, 0)  # cancellation makes the actual degree zero
        result = run_algebraic_degree_analysis(2)
        self.assertIsNone(result["actual_512bit_degrees"])
        self.assertIsNone(result["security_margin"])

    def test_reduced_model_exact_at_64bit(self) -> None:
        rng = random.Random(9901)
        for rnd in (0, 1, 2, 4, 14):
            for _ in range(4):
                base = [rng.getrandbits(64) for _ in range(8)]
                expected = base.copy()
                permute(expected, rounds=rnd)
                self.assertEqual(exact_word_permute(base, rounds=rnd, word_bits=64), expected)

    def test_exact_chi2_known_distributions(self) -> None:
        for x in (0.1, 1.0, 10.0, 100.0):
            self.assertAlmostEqual(chi2_p_value(x, 2), math.exp(-x/2), places=10)
            self.assertAlmostEqual(chi2_p_value(x, 4), math.exp(-x/2)*(1+x/2), places=10)
            self.assertAlmostEqual(chi2_p_value(x, 1), math.erfc(math.sqrt(x/2)), places=10)

    def test_insufficient_longest_run_samples_do_not_pass(self) -> None:
        self.assertFalse(longest_run_ones_test([0, 1] * 300)[2])

    @unittest.skipIf(z3 is None, "Optional z3-solver not installed")
    def test_symbolic_toy_round_matches_executable_model(self) -> None:
        rng = random.Random(100)
        for width in (2, 4, 8):
            for rounds in (0, 1, 2):
                for _ in range(4):
                    base = [rng.randrange(1 << width) for _ in range(8)]
                    terms = [z3.BitVecVal(x, width) for x in base]
                    symbolic = exact_word_permute_z3(terms, rounds, width)
                    self.assertEqual(
                        [z3.simplify(expr).as_long() for expr in symbolic],
                        exact_word_permute(base, rounds, width),
                    )

    @unittest.skipIf(z3 is None, "Optional z3-solver not installed")
    def test_optional_solver_does_not_claim_margin(self) -> None:
        report = smt_reduced_round_witness(word_bits=2, rounds=1, timeout_ms=1000)
        self.assertNotIn("full_round_security_margin", report)
        self.assertIn(report["status"], ("unknown", "SAT_WITNESS_VALIDATED", "NOT_RUN"))


if __name__ == "__main__":
    unittest.main()
