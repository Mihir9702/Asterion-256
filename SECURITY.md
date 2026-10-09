# Security Policy

## Status

Asterion-256 is an **experimental, unaudited cryptographic research construction**.

It is not approved for production security use and carries no claim of resistance comparable to established standardized hash functions.

Do **not** use Asterion-256 for:

- password storage or password derivation;
- authentication or authorization;
- digital signatures;
- MACs or keyed authentication;
- encryption-key derivation;
- TLS or protocol transcript hashing;
- software-update integrity;
- financial or medical data protection;
- production secrets;
- any other real security boundary.

Use established, independently reviewed primitives for those purposes.
## What counts as a useful security report?

Reports are welcome for:

- collisions or practical near-collisions;
- preimage or second-preimage improvements;
- reduced-round attacks or distinguishers;
- differential, rotational, linear, or algebraic weaknesses;
- invariant subspaces or weak-state classes;
- framing, padding, domain-separation, or length-binding ambiguity;
- mismatches between SPEC.md and an implementation;
- test-vector inconsistencies;
- implementation bugs that change digest behavior;
- repository or release-chain vulnerabilities.

A result does not need to break all 14 rounds to be valuable. Reduced-round analysis helps establish whether the full-round construction has a meaningful margin.

## Reporting

For a security-sensitive report, use GitHub's **Security → Report a vulnerability** flow when available. This allows private discussion before public disclosure.

For non-sensitive cryptanalysis or specification discussion, a normal GitHub issue is appropriate.
## Disclosure

There is no deployed security product depending on Asterion-256, so the project favors open technical discussion. However, private reporting is still appropriate when a repository, release, or account-level vulnerability could affect maintainers or users.

## Supported versions

Only the latest tagged experimental version is maintained.

Version 0.1.0 is behaviorally frozen by SPEC.md and the committed known-answer vectors. A cryptographic parameter change must receive a new incompatible algorithm version rather than silently altering v0.1.0.

## Security claims

Asterion-256 outputs 256 bits but has a 256-bit sponge capacity. Even under an ideal-permutation model, that does not support a claim of 256-bit generic security.

The custom 14-round permutation has not received sufficient public cryptanalysis to establish even the generic bound. The correct current security status is therefore **unknown / experimental**.

The analysis scorecard is not a proof. Earlier scripts incorrectly calculated
differential weight from active additions and interpreted algebraic upper
bounds as actual degree. Those claims have been withdrawn.

The v0.1.1 implementation uses BEST-EFFORT object overwrites, not assured
erasure of garbage-collected BigInts or immutable Python integers. The
JavaScript timingSafeEqual utility has NO constant-time execution guarantee.
No independent cryptographic review or production security certification exists.
