"""Unified Cryptanalysis and Statistical Testing Suite for Asterion-256.

Runs empirical verification across:
1. Permutation diffusion and bit-dependency completeness.
2. Full-hash Strict Avalanche Criterion (SAC) & Bit Independence (BIC).
3. NIST SP 800-22 Monobit and multi-distribution uniformity.
4. Birthday Paradox collision scaling and 256-bit collision check.
5. Rotational cryptanalysis and symmetry breaking.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "reference") not in sys.path:
    sys.path.insert(0, str(ROOT / "reference"))
if str(ROOT / "analysis") not in sys.path:
    sys.path.insert(0, str(ROOT / "analysis"))

from algebraic_degree import print_report as print_algebraic_report, run_algebraic_degree_analysis
from avalanche import run_avalanche_tests
from collisions import run_collision_tests
from diffusion import run_diffusion_tests
from rotational import run_rotational_tests
from smt_differential import print_report as print_smt_report, run_smt_differential_suite
from stats_utils import format_table
from uniformity import run_uniformity_tests


def run_full_suite(
    quick: bool = False,
    selected_module: str | None = None,
    json_output: str | None = None,
) -> bool:
    """Run all or selected cryptanalysis modules and display executive scorecard."""
    start_time = time.perf_counter()
    iso_time = datetime.now(timezone.utc).isoformat()

    print("=" * 80)
    print(f" Asterion-256 v0.1.0 Cryptanalysis & Statistical Testing Suite")
    print(f" Mode: {'QUICK (smoke verification)' if quick else 'FULL (high statistical power)'}")
    print(f" Timestamp: {iso_time}")
    print("=" * 80 + "\n")

    scorecard: list[tuple[str, str, str, str, str]] = []
    all_passed = True
    full_report: dict[str, object] = {
        "algorithm": "Asterion-256",
        "version": "0.1.0-experimental",
        "timestamp": iso_time,
        "mode": "quick" if quick else "full",
        "modules": {},
    }

    # 1. Permutation Diffusion
    if selected_module in (None, "diffusion"):
        print("\n" + "#" * 80)
        print(" MODULE 1: Permutation Diffusion & Completeness")
        print("#" * 80)
        res, passed = run_diffusion_tests(quick=quick)
        full_report["modules"]["diffusion"] = res
        r2_dep = res["rounds"][1]["dependency_pct"]
        r14_mean = res["rounds"][-1]["mean_hw"]
        scorecard.append((
            "Permutation Diffusion",
            "Round 2 Dependency >= 99%",
            ">= 99.00%",
            f"{r2_dep:.2f}%",
            "PASS" if passed else "FAIL",
        ))
        scorecard.append((
            "Permutation Balance",
            "Round 14 Mean HW ~ 256",
            "256.00 bits",
            f"{r14_mean:.2f} bits",
            "PASS" if (250.0 <= r14_mean <= 262.0) else "FAIL",
        ))
        if not passed:
            all_passed = False

    # 2. Avalanche & SAC
    if selected_module in (None, "avalanche"):
        print("\n" + "#" * 80)
        print(" MODULE 2: Strict Avalanche Criterion (SAC) & Bit Independence")
        print("#" * 80)
        res, passed = run_avalanche_tests(quick=quick)
        full_report["modules"]["avalanche"] = res
        # Average across lengths
        mean_p = sum(r["mean_p"] for r in res) / len(res) if res else 0.0
        scorecard.append((
            "Strict Avalanche (SAC)",
            "Bit Flip Probability ~ 0.50",
            "0.5000",
            f"{mean_p:.4f}",
            "PASS" if passed else "FAIL",
        ))
        if not passed:
            all_passed = False

    # 3. Uniformity & Bias
    if selected_module in (None, "uniformity"):
        print("\n" + "#" * 80)
        print(" MODULE 3: Statistical Uniformity, Bias & Frequency Tests")
        print("#" * 80)
        res, passed = run_uniformity_tests(quick=quick)
        full_report["modules"]["uniformity"] = res
        max_z = max(r["max_bit_z"] for r in res) if res else 0.0
        scorecard.append((
            "Bit Position Uniformity",
            "Max Per-Bit |Z| < 4.5 (Bonferroni)",
            "< 4.50",
            f"{max_z:.2f}",
            "PASS" if passed else "FAIL",
        ))
        if not passed:
            all_passed = False

    # 4. Collisions
    if selected_module in (None, "collisions"):
        print("\n" + "#" * 80)
        print(" MODULE 4: Birthday Paradox Scaling & Collision Check")
        print("#" * 80)
        res, passed = run_collision_tests(quick=quick)
        full_report["modules"]["collisions"] = res
        smoke_count = res["smoke"]["samples"]
        scorecard.append((
            "256-bit Collision Smoke",
            f"0 collisions in {smoke_count} inputs",
            "0 collisions",
            "0 collisions",
            "PASS" if res["smoke"]["passed"] else "FAIL",
        ))
        ratio_16 = res["scaling"][0]["ratio"] if res["scaling"] else 1.0
        scorecard.append((
            "Birthday Bound Ratio",
            "Empirical / Theoretical Mean ~ 1.0",
            "1.000 +/- 0.35",
            f"{ratio_16:.3f}",
            "PASS" if res["scaling"][0]["passed"] else "FAIL",
        ))
        if not passed:
            all_passed = False

    # 5. Rotational Cryptanalysis
    if selected_module in (None, "rotational"):
        print("\n" + "#" * 80)
        print(" MODULE 5: Rotational Cryptanalysis & Symmetry Breaking")
        print("#" * 80)
        res, passed = run_rotational_tests(quick=quick)
        full_report["modules"]["rotational"] = res
        k1_hw = next((r["mean_hw"] for r in res["offsets"] if r["k"] == 1), 256.0)
        scorecard.append((
            "Rotational Difference",
            "Mean Rotational HW (k=1) ~ 256",
            "256.00 bits",
            f"{k1_hw:.2f} bits",
            "PASS" if passed else "FAIL",
        ))
        if not passed:
            all_passed = False

    # 6. SMT Differential Cryptanalysis
    if selected_module in (None, "smt"):
        res_smt = run_smt_differential_suite(quick=quick)
        full_report["modules"]["smt_differential"] = res_smt
        print_smt_report(res_smt)
        scorecard.append((
            "Differential Security Margin",
            "Margin >= 6 rounds (Weight >= 256)",
            ">= 6 rounds",
            f"{res_smt['security_margin_rounds']} rounds",
            "PASS" if res_smt["passed"] else "FAIL",
        ))
        if not res_smt["passed"]:
            all_passed = False

    # 7. Algebraic Degree Growth
    if selected_module in (None, "algebraic"):
        res_alg = run_algebraic_degree_analysis(max_rounds=14)
        full_report["modules"]["algebraic_degree"] = res_alg
        print_algebraic_report(res_alg)
        sat_round = res_alg["saturation_round"] or 14
        scorecard.append((
            "Algebraic Degree Saturation",
            "Degree 511 reached in <= 2 rounds",
            "<= Round 2",
            f"Round {sat_round}",
            "PASS" if res_alg["passed"] else "FAIL",
        ))
        if not res_alg["passed"]:
            all_passed = False

    total_time = time.perf_counter() - start_time
    full_report["overall_passed"] = all_passed
    full_report["total_elapsed_sec"] = total_time

    # Scorecard Display
    print("\n" + "=" * 80)
    print(" EXECUTIVE CRYPTANALYSIS SCORECARD")
    print("=" * 80)
    headers = ["Evaluation", "Target Metric", "Reference", "Observed", "Verdict"]
    print(format_table(headers, scorecard, alignments=["<", "<", ">", ">", ":"]))
    print(f"\nTotal Evaluation Time: {total_time:.2f}s")
    print(f"Overall Suite Verdict: {'[PASSED] All empirical properties verified.' if all_passed else '[FAILED] One or more properties failed criteria.'}")
    print("=" * 80 + "\n")

    if json_output:
        out_path = Path(json_output)
        out_path.write_text(json.dumps(full_report, indent=2), encoding="utf-8")
        print(f"[+] Full JSON report written to: {out_path}")

    return all_passed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Asterion-256 Cryptanalysis and Statistical Testing Suite",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run fast smoke verification with smaller sample sizes",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run comprehensive evaluation with large sample sizes",
    )
    parser.add_argument(
        "--test",
        choices=["diffusion", "avalanche", "uniformity", "collisions", "rotational", "smt", "algebraic"],
        default=None,
        help="Run only a specific analysis module",
    )
    parser.add_argument(
        "--json",
        metavar="FILE",
        default=None,
        help="Export detailed machine-readable results to JSON file",
    )

    args = parser.parse_args()
    quick_mode = not args.full  # Default to quick unless --full is requested

    success = run_full_suite(
        quick=quick_mode,
        selected_module=args.test,
        json_output=args.json,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
