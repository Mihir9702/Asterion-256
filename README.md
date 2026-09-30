# Asterion-256

> **EXPERIMENTAL / UNAUDITED / NOT FOR PRODUCTION CRYPTOGRAPHY**

Asterion-256 is a research implementation of a custom 256-bit hash construction written in TypeScript. It uses a 512-bit state, a 256-bit sponge rate, a 256-bit capacity, and a custom 14-round 64-bit ARX permutation.

**Do not use Asterion-256 to protect passwords, authentication, signatures, financial data, production secrets, encryption keys, software updates, or any other real security boundary.** Use established, reviewed primitives instead.

Asterion-256 produces a **256-bit digest**. That is not a claim of 256-bit security. With a 256-bit sponge capacity, the generic sponge security ceiling is roughly 128 bits even if the underlying permutation behaves ideally. No comparable security level has been established for Asterion's custom permutation.

## Status

- Version: **0.1.0-experimental**
- Security review: **none**
- Cryptanalytic review: **none**
- Production use: **not recommended**
- npm publication: intentionally disabled with `"private": true`
## Construction

- 512-bit state: 8 × 64-bit lanes
- 256-bit rate: lanes 0–3
- 256-bit capacity: lanes 4–7
- 14-round ARX permutation
- Little-endian lane encoding
- Streaming message absorption
- UTF-8 domain separation
- Distinct domain/message/final frames
- Explicit final padding
- 64-bit message-length binding
- Two-permutation finalization barrier
- 256-bit output from lanes 0–3

The exact algorithm is defined by [SPEC.md](SPEC.md). Design choices and unresolved questions are documented in [DESIGN.md](DESIGN.md).

## Quick use

```ts
import { Asterion256, asterion256 } from './Asterion-256.js'

const oneShot = asterion256('hello')

const streaming = new Asterion256()
  .update('he')
  .update('llo')
  .digest('hex')
```
The current default-domain `hello` vector is:

```text
d9657b5802a1f9fccd5b063ea5a2230855daf1b8b6ef702bb36867ea3e03410e
```

## Verification

```bash
npm ci
npm run typecheck
npm test
python reference/verify_vectors.py
npm run test:analysis
```

Committed known-answer tests cover empty input and lengths around the 32-byte rate boundary, including 31/32/33, 63/64/65, 127/128/129, and a 1024-byte case. They also cover domain separation and UTF-8 input.

The independent Python implementation in [reference/asterion256.py](reference/asterion256.py) is intentionally separate from the TypeScript runtime and is checked against the same vectors.

The empirical cryptanalysis and statistical testing suite in [analysis/](analysis/) evaluates permutation diffusion, Strict Avalanche Criterion (SAC), statistical uniformity, Birthday collision scaling, and rotational symmetry.

## Documentation

- [SPEC.md](SPEC.md) — normative byte-level specification
- [DESIGN.md](DESIGN.md) — rationale, constants, limitations, and research agenda
- [SECURITY.md](SECURITY.md) — security status and vulnerability reporting
- [vectors/known-answer-vectors.json](vectors/known-answer-vectors.json) — interoperability vectors
- [analysis/README.md](analysis/README.md) — cryptanalysis and statistical testing suite
## What the tests do — and do not — establish

Current development checks verify deterministic behavior, one-shot/streaming equivalence, framing behavior, boundary lengths, lifecycle guards, and agreement between two implementations.

Development-time statistical smoke tests have also shown near-50% output-bit balance and avalanche behavior on sampled inputs. **Those observations are not cryptanalysis and are not evidence of cryptographic security.**

Important open work includes differential, rotational, linear/differential-linear, algebraic, rebound-style, and reduced-round analysis of the permutation.

## License

Apache License 2.0. See [LICENSE](LICENSE).

## Research contributions

External review is welcome. A useful result includes attacks, distinguishers, reduced-round results, structural observations, specification ambiguities, implementation mismatches, or improved test methodology. Please see [SECURITY.md](SECURITY.md) before reporting a security-sensitive issue.
