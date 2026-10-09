# Asterion-256 research analysis

**Status: experimental. No published security proof, independently validated full-round attack bound, or cryptographic security margin.**

The analysis/ tree has two different kinds of code:

| Code | What it actually establishes | What it does not establish |
|---|---|---|
| diffusion.py | Measured state differences for sampled input pairs | Proven bit dependency or attack resistance |
| avalanche.py | Sampled Strict Avalanche statistics, limited BIC correlations | Full independence or cryptographic strength |
| uniformity.py | Selected frequency/runs/byte-distribution tests | Random oracle behavior or security |
| collisions.py | Truncated 16/20/24-bit collision smoke and birthday scaling | 256-bit collision resistance |
| rotational.py | Sampled rotational difference Hamming weights | Absence of rotational characteristics |
| smt_differential.py | Exhaustive modular-addition XOR-difference examples (4/8-bit); optional exact reduced-word SMT witness | Any full-size differential weight lower bound |
| algebraic_degree.py | Propagated upper bounds; exact 4-bit addition ANF cross-check | Actual 512-bit degrees or cube-attack resistance |
| reduced_round_research.py | Exhaustive 16-bit *surrogate* differential and seeded full-width samples | Full-round differential probability bounds |
| test_models.py | Validates local mathematical routines against known formulas and the reference permutation | Independent external review |

## Corrected methodological errors

1. **Active modular addition does not imply positive differential weight.** For addition modulo 2^w, choosing XOR input differences (2^(w-1),0) gives output difference 2^(w-1) with probability **1**. Any model assigning every active addition a fixed positive lower weight is false.
2. **Max-plus degree propagation is an upper bound.** XOR cancellation can lower actual degree. Degree ceilings reached by the bound (even after one round) are not evidence of algebraic saturation.
3. **SAC observations are correlated.** A summed SAC cell chi-square statistic does not automatically follow the reference chi-square distribution if cells share baseline messages or exhibit correlation. Aggregate p-values are descriptive nominal values, not proved significance levels.
4. **Randomness sanity tests are not cryptanalysis.** A healthy Hamming distribution can coexist with exploitable structure.
5. **Reduced-word surrogate models differ from 64-bit Asterion.** Constants are truncated and rotations are reduced modulo word width. Their attack results do not transfer without explicit proof.

## Reproducibility

From repository root, after npm ci:

~~~bash
npm run verify                       # correctness + models + empirical sanity
npm run test:models                  # exact toy ANFs, addition distributions, equivalence tests
npm run test:interop                 # Python vs TypeScript incl. 64KB domains, Unicode
npm run test:analysis                # quick empirical smoke (not a security pass)
npm run test:analysis:full           # more samples (still not a security proof)
npm run test:research                # sampled and exhaustive surrogate experiments
python analysis/smt_differential.py --quick
python analysis/algebraic_degree.py
python analysis/reduced_round_research.py --quick --json research/reduced-round-results.json
~~~

The optional SMT experiment requires z3-solver==5.1.0.0; CI installs it. A timed-out solver query returning unknown is inconclusive, never a positive security result.

Scripts use explicit deterministic seeds. A reproducible result records Git commit, runtime/solver versions, sample selection, and experiment parameters. The committed JSON study uses a fixed seed and baseline revision and is **not** a validated security bound.

## Interpretation rules

- Development tests may say PASS **only** for tested deterministic behavior or explicitly stated sample thresholds.
- Mathematical proof requires valid premises and derivations, not a scorecard.
- A failed attack search is *not* evidence no attack exists.
- A 256-bit output and a 256-bit capacity do not imply 256-bit security.
- Full 14-round security remains **unknown**.

## Open work

Full-width differential characteristic enumeration/bounding; trail and hull effects; rotational-XOR characteristics; invariant subspaces; exact algebraic structure beyond toy examples; collision/preimage/second-preimage evaluation; sponge assumptions; external cryptanalytic review.
