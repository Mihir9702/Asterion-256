# Phase 1–6 engineering and research record (v0.1.1 candidate)

This record separates **completed engineering** from **open scientific/external prerequisites**.

| Phase | Work performed | Honest status |
|---|---|---|
| 1 — Research claims | Removed invented differential bounds, unbreakable labels, false degree proof, and security PASS statements | Implemented |
| 2 — Runtime contracts | Irreversible destroy(), null-domain rejection, domain masking, UTF-16 streaming, best-effort zeroization, invalid format handling | Implemented |
| 3 — Tests and CI | Cross-language tests, surrogate tests, mathematical validation, Python tests in CI, pinned solver, seeded research runner | Implemented; CI needs a green run |
| 4 — Mathematics | Exact small-word XOR-addition histograms, faithful toy bitvector formulas, exact 4-bit ANF check, precise chi-square evaluation | Limited model validation complete; full security bounds remain unknown |
| 5 — Attack research | Seeded full-width reduced-round difference sampling; exhaustive 16-bit surrogate fixed-difference enumeration | Initial reproducible experiment complete; comprehensive cryptanalysis open |
| 6 — Independent review | Review scope, reproducibility evidence, submission criteria and a public request packet prepared | Independent human/expert review **pending** |

## Release integrity requirements

- All 24 original v0.1.0 known-answer hashes unchanged.
- Runtime regression, Python vectors, cross-language cases and mathematical model tests pass.
- Record test/CI status precisely, never invent a green result.
- No hash parameters altered in a patch. A permutation, IV, padding, framing, rate/capacity, endian or algorithmic length-rule change requires an incompatible algorithm identifier.
- Peer review and credible full-round security bounds cannot be checked into existence by the project's own CI.

## Security approval

The construction is not approved for any production cryptographic application. An implementation milestone can close while research security remains unknown; completing an external security review requires actual external evidence.
