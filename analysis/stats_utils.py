"""Statistical utilities and hypothesis test implementations for Asterion-256 analysis.

All calculations use pure Python standard libraries without external dependencies.
"""

from __future__ import annotations

import math
from typing import Sequence


def chi2_p_value(chi2: float, df: int) -> float:
    """Compute the survival function (p-value) P(X >= chi2) for Chi-Square distribution."""
    if chi2 <= 0.0:
        return 1.0
    if df <= 0:
        return 0.0

    # Regularized incomplete gamma Q(a,x), with stable branches:
    # P-series for x < a+1, Q-continued fraction otherwise.
    a = df / 2.0
    x = chi2 / 2.0
    log_factor = a * math.log(x) - x - math.lgamma(a)
    eps = 1e-13
    tiny = 1e-300
    if x < a + 1.0:
        acc = 1.0 / a
        term = acc
        for n in range(1, 10000):
            term *= x / (a + n)
            acc += term
            if abs(term) <= abs(acc) * eps:
                break
        q = 1.0 - math.exp(log_factor) * acc
    else:
        b = x + 1.0 - a
        c = 1.0 / tiny
        d = 1.0 / (b if abs(b) >= tiny else tiny)
        h = d
        for i in range(1, 10000):
            an = -i * (i - a)
            b += 2.0
            d = an * d + b
            if abs(d) < tiny:
                d = tiny
            c = b + an / c
            if abs(c) < tiny:
                c = tiny
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) <= eps:
                break
        q = math.exp(log_factor) * h
    return max(0.0, min(1.0, float(q)))


def normal_p_value(z: float) -> float:
    """Compute two-sided p-value for a standard normal Z-statistic: P(|Z| >= |z|)."""
    return float(math.erfc(abs(z) / math.sqrt(2.0)))


def monobit_test(ones: int, total_bits: int) -> tuple[float, float, bool]:
    """NIST SP 800-22 Frequency (Monobit) Test.

    Returns:
        (ratio_of_ones, p_value, passed)
    """
    if total_bits <= 0:
        return 0.0, 0.0, False

    ratio = ones / total_bits
    s_obs = abs(2 * ones - total_bits) / math.sqrt(total_bits)
    p_val = float(math.erfc(s_obs / math.sqrt(2.0)))
    passed = p_val >= 0.01
    return ratio, p_val, passed


def runs_test(bits: Sequence[int]) -> tuple[float, float, bool]:
    """NIST SP 800-22 Runs Test.

    Tests whether the number of runs of consecutive zeros and ones is as
    expected for a random sequence.

    Returns:
        (observed_runs, p_value, passed)
    """
    n = len(bits)
    if n < 100:
        return 0.0, 0.0, False

    ones = sum(bits)
    pi = ones / n

    if abs(pi - 0.5) >= (2.0 / math.sqrt(n)):
        return 0.0, 0.0, False

    v_obs = 1 + sum(1 for i in range(n - 1) if bits[i] != bits[i + 1])
    e_v = 2.0 * n * pi * (1.0 - pi)
    den = 2.0 * math.sqrt(2.0 * n) * pi * (1.0 - pi)

    if den == 0.0:
        return float(v_obs), 0.0, False

    p_val = float(math.erfc(abs(v_obs - e_v) / den))
    passed = p_val >= 0.01
    return float(v_obs), p_val, passed


def longest_run_ones_test(bits: Sequence[int]) -> tuple[float, float, bool]:
    """NIST SP 800-22 Longest Run of Ones in a Block Test (M=128 bits).

    Returns:
        (chi2, p_value, passed)
    """
    M = 128
    K = 5
    pi = [0.1174, 0.2430, 0.2493, 0.1752, 0.1027, 0.1124]

    n = len(bits)
    N = n // M
    if N < 49:
        return 0.0, 0.0, False  # Insufficient sample, not a PASS

    freq = [0] * 6
    for block_idx in range(N):
        block = bits[block_idx * M : (block_idx + 1) * M]
        max_run = 0
        current_run = 0
        for bit in block:
            if bit == 1:
                current_run += 1
                if current_run > max_run:
                    max_run = current_run
            else:
                current_run = 0

        if max_run <= 4:
            freq[0] += 1
        elif max_run == 5:
            freq[1] += 1
        elif max_run == 6:
            freq[2] += 1
        elif max_run == 7:
            freq[3] += 1
        elif max_run == 8:
            freq[4] += 1
        else:
            freq[5] += 1

    chi2 = sum(((freq[i] - N * pi[i]) ** 2) / (N * pi[i]) for i in range(6))
    p_val = chi2_p_value(chi2, K)
    passed = p_val >= 0.01
    return float(chi2), p_val, passed


def bytes_to_bits(data: bytes | bytearray) -> list[int]:
    """Convert bytes to a list of integer bit values 0 or 1 (little-endian per byte)."""
    bits: list[int] = []
    for byte in data:
        for bit_idx in range(8):
            bits.append((byte >> bit_idx) & 1)
    return bits


def count_set_bits(data: bytes | bytearray) -> int:
    """Count the total number of set bits (1s) in a byte buffer."""
    return sum(bin(b).count("1") for b in data)


def sac_metrics(
    counts_matrix: list[list[int]],
    samples: int,
) -> dict[str, float | int | bool]:
    """Compute Strict Avalanche Criterion (SAC) metrics on an input-bit x output-bit count matrix."""
    rows = len(counts_matrix)
    cols = len(counts_matrix[0]) if rows > 0 else 0
    total_cells = rows * cols

    if total_cells == 0 or samples == 0:
        return {
            "mean_p": 0.0,
            "mad": 0.0,
            "expected_mad": 0.0,
            "max_dev": 0.0,
            "chi2": 0.0,
            "p_value": 0.0,
            "passed": False,
        }

    sum_p = 0.0
    sum_abs_dev = 0.0
    max_dev = 0.0
    chi2_total = 0.0

    for i in range(rows):
        for j in range(cols):
            count = counts_matrix[i][j]
            p_ij = count / samples
            dev = abs(p_ij - 0.5)
            sum_p += p_ij
            sum_abs_dev += dev
            if dev > max_dev:
                max_dev = dev
            # Cell chi-square: (count - E)^2 / Var, where E = 0.5 * N, Var = 0.25 * N
            cell_chi2 = 4.0 * ((count - samples / 2.0) ** 2) / samples
            chi2_total += cell_chi2

    mean_p = sum_p / total_cells
    mad = sum_abs_dev / total_cells
    # Theoretical expected MAD for Binomial(N, 0.5) / N:
    expected_mad = 0.39894228 / math.sqrt(samples)
    p_val = chi2_p_value(chi2_total, total_cells)

    # Descriptive smoke thresholds. The nominal cell chi-square p-value
    # assumes independence that is not established for correlated SAC cells.
    # Therefore it is NOT a security or formal significance gate.
    mean_ok = abs(mean_p - 0.5) <= 0.03
    passed = bool(mean_ok and mad <= expected_mad * 1.7)

    return {
        "mean_p": mean_p,
        "mad": mad,
        "expected_mad": expected_mad,
        "max_dev": max_dev,
        "chi2": chi2_total,
        "df": total_cells,
        "p_value": p_val,
        "passed": passed,
    }


def format_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    alignments: Sequence[str] | None = None,
) -> str:
    """Format tabular data into a clean ASCII table."""
    num_cols = len(headers)
    if alignments is None:
        alignments = ["<"] + [">"] * (num_cols - 1)

    widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(str(cell)))

    # Header row
    header_parts = []
    for h, w, a in zip(headers, widths, alignments):
        if a == "<":
            header_parts.append(h.ljust(w))
        elif a == ">":
            header_parts.append(h.rjust(w))
        else:
            header_parts.append(h.center(w))
    header_line = "| " + " | ".join(header_parts) + " |"

    # Separator row
    sep_parts = []
    for w, a in zip(widths, alignments):
        if a == "<":
            sep_parts.append(":" + "-" * (w - 1))
        elif a == ">":
            sep_parts.append("-" * (w - 1) + ":")
        else:
            sep_parts.append(":" + "-" * (w - 2) + ":")
    sep_line = "|-" + "-|-".join(sep_parts) + "-|"

    # Content rows
    row_lines = []
    for row in rows:
        parts = []
        for cell, w, a in zip(row, widths, alignments):
            s = str(cell)
            if a == "<":
                parts.append(s.ljust(w))
            elif a == ">":
                parts.append(s.rjust(w))
            else:
                parts.append(s.center(w))
        row_lines.append("| " + " | ".join(parts) + " |")

    return "\n".join([header_line, sep_line] + row_lines)
