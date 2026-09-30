# Asterion-256 Cryptanalysis & Statistical Testing Suite

This directory contains the empirical cryptanalysis and statistical testing toolkit for **Asterion-256 v0.1.0**.

The suite evaluates both the underlying 512-bit ARX permutation and the full sponge hash construction against standard empirical criteria from academic cryptanalysis and NIST randomness testing frameworks.

> [!NOTE]
> As established in [SPEC.md](../SPEC.md) and [DESIGN.md](../DESIGN.md), empirical statistical testing and absence of low-round defects are necessary sanity checks, but they **do not constitute a proof of cryptographic security** or resistance to advanced structural attacks.

---

## Architecture & Modules

| Module | Script | Scope | Primary Metrics |
|---|---|---|---|
| **1. Permutation Diffusion** | [`diffusion.py`](diffusion.py) | 512-bit state / rounds 1–14 | Round-by-round HW distribution, bit-dependency completeness, rate vs capacity diffusion |
| **2. Strict Avalanche (SAC)** | [`avalanche.py`](avalanche.py) | Full sponge hash | Webster-Tavares SAC matrix, Empirical vs Expected MAD, Chi-Square p-value, Bit Independence (BIC) |
| **3. Uniformity & Bias** | [`uniformity.py`](uniformity.py) | Full sponge hash | NIST SP 800-22 Monobit test, per-bit position Z-scores, 256-bin byte Chi-Square goodness-of-fit |
| **4. Collision Scaling** | [`collisions.py`](collisions.py) | Full sponge hash | Truncated Birthday Paradox scaling ($k \in \{16, 20, 24\}$), 256-bit collision-free smoke test |
| **5. Rotational Analysis** | [`rotational.py`](rotational.py) | 512-bit state / rounds 1–14 | Rotational difference $\Delta_{rot}(x, k)$, symmetry breaking, with vs without round constants |
| **Statistical Utilities** | [`stats_utils.py`](stats_utils.py) | Shared math | Exact $\chi^2$ p-values (Wilson-Hilferty & incomplete gamma), table formatting, bit helpers |
| **Unified Suite Runner** | [`run_suite.py`](run_suite.py) | All modules | Top-level CLI driver, ASCII executive scorecard, JSON export |

---

## Mathematical Formulations

### 1. Strict Avalanche Criterion (SAC)
Introduced by Webster and Tavares (1985), a hash function satisfies the SAC if, whenever a single input bit $i$ is complemented, each output bit $j$ changes with probability $p_{i,j} = 0.5$:

$$P(\Delta y_j = 1 \mid \Delta x_i = 1) = 0.5 \quad \forall i, j$$

For $N$ random baseline samples, let $A[i][j]$ denote the observed flip count. The empirical probability is $\hat{p}_{i,j} = \frac{A[i][j]}{N}$.

#### Finite-Sample Expected Mean Absolute Deviation (MAD)
Because finite sample sizes introduce natural binomial noise, comparing empirical MAD directly against 0 would be statistically incorrect. For $N$ independent binomial trials $B(N, 0.5)$, the expected absolute deviation is:

$$E[|\hat{p} - 0.5|] \approx \frac{1}{\sqrt{2\pi N}} \approx \frac{0.39894}{\sqrt{N}}$$

The suite computes this theoretical expectation to verify that observed variations match normal binomial dispersion rather than systematic bias.

#### SAC Chi-Square Test
Each cell $(i, j)$ contributes:

$$\chi_{i,j}^2 = \frac{4 \left(A[i][j] - \frac{N}{2}\right)^2}{N}$$

The total test statistic is $\chi_{total}^2 = \sum_{i,j} \chi_{i,j}^2$ with degrees of freedom $df = \text{input\_bits} \times 256$. The p-value is computed via the survival function $P(X \ge \chi_{total}^2)$.

---

### 2. Bit Independence Criterion (BIC)
Output bit changes $\Delta y_j$ and $\Delta y_k$ ($j \neq k$) upon an input bit flip should be pairwise uncorrelated:

$$r_{j,k} = \frac{\text{Cov}(\Delta y_j, \Delta y_k)}{\sqrt{\text{Var}(\Delta y_j) \cdot \text{Var}(\Delta y_k)}} \approx 0$$

The suite computes the mean absolute correlation across output bit pairs.

---

### 3. Permutation Bit-Dependency Completeness
A permutation exhibits full dependency at round $R$ if every output bit $j \in [0, 511]$ depends on every input bit $i \in [0, 511]$:

$$\text{Coverage}(R) = \frac{1}{512 \times 512} \sum_{i=0}^{511} \sum_{j=0}^{511} \mathbb{I}(\text{bit } j \text{ flipped at least once by bit } i)$$

Asterion-256 achieves **99.9% dependency coverage by Round 2**, with the average number of flipped bits reaching $256.0 \pm 0.2$ out of 512 bits.

---

### 4. Birthday Paradox Collision Scaling
For a $k$-bit truncated digest, the theoretical expected number of random evaluations before encountering the first collision is:

$$E[N] \approx \sqrt{\frac{\pi}{2} \cdot 2^k} \approx 1.2533 \cdot 2^{k/2}$$

The ratio of empirical iterations $\bar{N}_{coll}$ to theoretical expectation $E[N]$ should be approximately $1.0$ (typically within $[0.8, 1.25]$ over finite trials).

---

### 5. Rotational Cryptanalysis
Rotational cryptanalysis investigates the propagation of rotated inputs $\vec{x}^{\lll k}$. The rotational difference is defined as:

$$\Delta_{rot}(\vec{x}, k) = \text{permute}(\vec{x}^{\lll k}) \oplus (\text{permute}(\vec{x}))^{\lll k}$$

Because Asterion-256 injects asymmetric constants ($\pi$ words, $s_7$ round addition) and non-stationary lane rotations, rotational symmetry is completely broken in Round 1: the mean rotational difference immediately reaches $\approx 256$ bits (50%) out of 512 bits across all tested offsets $k \in \{1, 2, 7, 8, 13, 16, 23, 31, 32\}$.

---

## Running the Suite

### Quick Smoke Check (Recommended for CI)
```bash
npm run test:analysis
# Or directly:
python analysis/run_suite.py --quick
```

### Full Cryptanalysis Suite (High Statistical Power)
```bash
npm run test:analysis:full
# Or directly:
python analysis/run_suite.py --full
```

### Export Machine-Readable JSON Report
```bash
python analysis/run_suite.py --quick --json analysis/report.json
```

### Run an Individual Analysis Module
```bash
python analysis/diffusion.py
python analysis/avalanche.py
python analysis/uniformity.py
python analysis/collisions.py
python analysis/rotational.py
```
