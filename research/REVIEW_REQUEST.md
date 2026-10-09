# Asterion-256 — Independent Cryptanalysis Review Request

**Review status: OPEN / NO INDEPENDENT REVIEW COMPLETED.**

## What is being reviewed

Asterion-256 v0.1.0 is a custom 512-bit, 14-round ARX sponge permutation hash producing 256-bit digests at 256-bit rate and 256-bit capacity. SPEC.md and vectors/known-answer-vectors.json form the frozen normative baseline. Implementation hardening is packaged separately as v0.1.1 without intentionally changing algorithm outputs.

No claim is made of SHA-256 equivalence, achieved 128-bit security, or a particular count of safe permutation rounds. For any real security application, use standardized cryptographic primitives.

## Evidence included

- SPEC.md, DESIGN.md, SECURITY.md — construction, honest assumptions, unresolved questions.
- Asterion-256.ts and reference/asterion256.py — TypeScript and Python implementations.
- vectors/known-answer-vectors.json — 24 existing interoperability vectors.
- tests/ and analysis/test_models.py — correctness, cross-language and local mathematical validation.
- analysis/smt_differential.py — exact small-addition differential histograms and optional reduced-word bitvector experiment.
- analysis/algebraic_degree.py — degree upper bounds, explicitly *not* actual degrees.
- analysis/reduced_round_research.py and research/reduced-round-results.json — seeded experiments and an exhaustive 16-bit surrogate.

## Priority review questions

1. Are framing, padding, domain separation and message-length binding unambiguous and free of exploitable structure?
2. Are there useful reduced-round XOR-differential trails, differentials or clustered hulls?
3. Can invariant sets, sparse subspaces or rotations distinguish meaningful numbers of 64-bit rounds?
4. Does the braid introduce weak classes or exploitable periodic structure?
5. Can rebound or meet-in-the-middle methods improve collision or preimage complexities?
6. Can 64-bit addition differential transition probabilities be validly bounded across full rounds?
7. Are implementation disagreements, boundary conditions or practical bugs left?
8. Do documentation claims exceed evidence?

## Definition of independently completed review

A named outside cryptographer/team separately examines the construction and reports scope, methods, assumptions, checked commit, and limitations. Running the repository's own tests **does not qualify**.

Contribute with a GitHub issue for ordinary findings or follow SECURITY.md for sensitive disclosures. Negative or inconclusive findings are welcome when reproducible.

**Current decision:** Experimental research only; external approval and production suitability remain unestablished.
