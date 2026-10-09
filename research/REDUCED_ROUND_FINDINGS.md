# Reduced-Round Findings — Asterion-256 v0.1.0

**Status:** Exploratory research with a frozen seed. Neither a security proof nor an attack on the full 14-round hash.

## Study reproducibility

- Baseline construction: commit f439376b80fb8fd7b3da312639365d2988752a6a
- Script: analysis/reduced_round_research.py
- Seed: 20261008
- Full-width chosen-state-pair probes: 256 per round count, rounds 1 through 14
- Toy-model differential enumeration: complete 65,536 inputs, two-bit words, 8 lanes, fixed input XOR delta 1 in lane zero
- Machine-readable results: reduced-round-results.json in this directory
- Rerun: python analysis/reduced_round_research.py --json research/reduced-round-results.json

## Actual 64-bit one-round observation

For the full 512-bit permutation, with 256 random state pairs at input Hamming distance one, the one-round mean output Hamming distance was approximately **206.11 / 512**, whereas an ideal random permutation would yield approximately **256 / 512** for uniformly sampled pairs.

This is a concrete **empirical one-round chosen-difference distinguisher signal**. It is an observation about the permutation after exactly one round, not an exploit against the 14-round sponge.

At round two, the same sample gave approximately **255.16 / 512**. The remaining sample means also stayed near 256. No conclusion about full-round differential trail probability follows from convergence of the means.

An approximation using independent ideal-permutation samples gives a one-round mean standard error of sqrt(128 / 256), but this is not a cryptographic probability bound, independent confirmation, or a protection against chosen-state/sample-selection biases.

## Exhaustive reduced-word surrogate

The independently coded reduced-word model uses **two-bit words**, truncates round constants and reduces rotations modulo two. It is not the production 64-bit permutation.

For a fixed 1-bit input XOR difference, exhaustive enumeration gives:

| Toy rounds | States evaluated | Most likely output XOR-difference probability |
|---|---:|---:|
| 1 | 65,536 | 0.031250 (1/32) |
| 2 | 65,536 | 0.001953125 (1/512) |

These are exact values for the two-bit surrogate only. They must not be compared against full 64-bit claimed security levels or extrapolated to rounds 3–14.

## Modeling corrections

- For XOR differentials through modular addition, a nonzero most-significant-bit difference can propagate with probability one. The previous blanket lower weight of 4 for every active addition was invalid.
- The new Z3 model encodes both full operation streams with concrete modular additions. Its optional optimization search may return UNKNOWN under timeout; unit tests independently verify its symbolic evaluation on multiple toy word widths.
- The upper-bound degree model reaches its maximum cap after one round, illustrating how loose and uninformative it can be. This is not actual algebraic degree.

## Next peer-review questions

Can one analytically characterize or exploit the observed one-round differential deficiency beyond round two, find viable 64-bit differential trails or hulls, construct a rotational/invariant distinguisher for more rounds, or identify sponge-specific collision/preimage improvements?

**Conclusion:** A reproducible reduced-round distinguisher signal exists; **no full-round hash break has been shown**.
