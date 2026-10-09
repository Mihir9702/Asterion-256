# Changelog

## 0.1.1 — Research integrity and implementation correctness (candidate)

No intentional changes to the normative Asterion-256 v0.1.0 digest construction.

- Withdrawn fictitious differential security margins and unsupported algebraic-degree security claims; exploratory models now explicitly report uncertainty.
- Added exact small-word modular-addition XOR-difference histograms, reduced-word SMT formula validation, exact 4-bit addition ANF checks, and an exhaustive 16-bit surrogate study.
- Replaced approximate chi-square survival calculation with an incomplete-gamma implementation, and stopped declaring insufficient runs-test samples a pass.
- Hardened lifecycle semantics: destroy is irreversible, unsupported digest formats are rejected before finalization, and public null-domain bypass is rejected.
- Fixed TypeScript domain-length masking for domains exceeding 65,535 bytes.
- Added cross-update UTF-16 surrogate handling, with Python behavior aligned to WHATWG TextEncoder.
- Corrected misleading descriptions of memory overwriting, constant-time comparison, hashlib compatibility, and empirical statistical evidence.
- Added cross-language randomized tests, targeted regressions, research-model validation, complete Python CI coverage, and the independent-review request packet.
- Original 24 known-answer vectors preserved; no production security claims introduced.

**Pending:** GitHub CI confirmation and independent external cryptanalytic review. v0.1.1 is an implementation patch, not a validated cryptographic redesign.
