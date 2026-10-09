# Preliminary Performance Review — v0.1.1

**Scope:** Exploratory same-machine benchmark, not a cross-platform or statistically rigorous performance certification.

## Tested environment

- Node.js v24.18.0, x64, Windows.
- Benchmark: benchmarks/bench.mjs, with 50 ms warm-up and approximately 500 ms per measured case.
- Payloads: 32 B, 64 B, 1 KiB, 64 KiB, 1 MiB.
- Baselines: native Node/OpenSSL SHA-256 and SHA3-256 vs Asterion-256 TypeScript BigInt implementation.

## Observed throughput (MiB/s, rounded as measured by the script)

| Message length | Asterion-256 | Asterion streaming | Native SHA-256 | Native SHA3-256 |
|---|---:|---:|---:|---:|
| 32 B | 0.18 | 0.18 | 21.43 | 15.61 |
| 64 B | 0.37 | 0.37 | 48.69 | 36.16 |
| 1 KiB | 0.82 | 0.82 | 511.03 | 248.99 |
| 64 KiB | 0.95 | 0.99 | 1995.60 | 419.98 |
| 1 MiB | 1.00 | 0.85 | 2036.90 | 406.86 |

For 1 MiB payloads, the script measured Asterion-256 one-shot latency around 1003 ms and a throughput around 1 MiB/s, compared with native SHA3-256 around 407 MiB/s and native SHA-256 around 2037 MiB/s.

**Conclusion:** The current pure TypeScript BigInt engine offers no measured throughput advantage over either standard native hash baseline in this environment. It should not be presented as a speed-oriented replacement.

## Limitations

- Only one local run on one Windows machine; no isolated CPU affinity, multiple independent trials, variance/confidence intervals, memory profiling, or CPU-frequency controls.
- Direct comparison to native optimized OpenSSL implementations conflates algorithm architecture with implementation/runtime choice.
- The script's amortized operations-per-second method can overshoot its 500 ms target when one operation takes longer.
- CPU and architecture variations, browser execution, and 32-bit implementations have not been evaluated.
- A performance gain would **not** imply cryptographic security.

## Future work

Use repeated independent trials, median/percentile estimates, stable CPU-load conditions, and memory measurements. Keep any optimized implementation bit-for-bit compatible with all reference vectors and cross-language property tests. Do not optimize custom cryptography toward production usage without a separate security argument.
