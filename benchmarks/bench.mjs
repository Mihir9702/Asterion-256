/**
 * Performance Benchmark Suite for Asterion-256.
 *
 * Compares Asterion-256 throughput and latency against standard hash baselines
 * (SHA-256, SHA3-256) across message payload sizes: 32B, 64B, 1KB, 64KB, 1MB.
 */

import crypto from 'node:crypto'
import { Asterion256, asterion256 } from '../dist/Asterion-256.js'

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(0)} MB`
}

function runBenchmark(fn, targetDurationMs = 500) {
  // Warmup (50ms)
  const warmStart = performance.now()
  while (performance.now() - warmStart < 50) {
    fn()
  }

  // Measured run
  let ops = 0
  const start = performance.now()
  let elapsed = 0

  while (elapsed < targetDurationMs) {
    // Run batch of 5 to reduce timing overhead
    fn()
    fn()
    fn()
    fn()
    fn()
    ops += 5
    elapsed = performance.now() - start
  }

  const opsPerSec = (ops / elapsed) * 1000
  const avgLatencyUs = (elapsed / ops) * 1000

  return { opsPerSec, avgLatencyUs, elapsedMs: elapsed, totalOps: ops }
}

function main() {
  const SIZES = [32, 64, 1024, 64 * 1024, 1024 * 1024]

  console.log('='.repeat(86))
  console.log(' Asterion-256 Performance & Throughput Benchmark')
  console.log(` Runtime: Node.js ${process.version} (${process.arch}-${process.platform})`)
  console.log('='.repeat(86))

  const results = []

  for (const size of SIZES) {
    const data = crypto.randomBytes(size)
    const sizeStr = formatBytes(size)

    console.log(`\n[*] Benchmarking payload size: ${sizeStr} (${size.toLocaleString()} bytes)...`)

    // 1. Asterion-256 (One-shot)
    const astRes = runBenchmark(() => {
      asterion256(data)
    })
    const astThroughput = (size * astRes.opsPerSec) / (1024 * 1024)

    // 2. Asterion-256 (Streaming in 16KB chunks if size > 16KB)
    let astStreamThroughput = astThroughput
    let astStreamRes = astRes
    if (size >= 64 * 1024) {
      const chunkSize = 16 * 1024
      astStreamRes = runBenchmark(() => {
        const h = new Asterion256()
        for (let offset = 0; offset < size; offset += chunkSize) {
          h.update(data.subarray(offset, Math.min(offset + chunkSize, size)))
        }
        h.digest('hex')
      })
      astStreamThroughput = (size * astStreamRes.opsPerSec) / (1024 * 1024)
    }

    // 3. SHA-256 (Node crypto / OpenSSL native baseline)
    const sha256Res = runBenchmark(() => {
      crypto.createHash('sha256').update(data).digest('hex')
    })
    const sha256Throughput = (size * sha256Res.opsPerSec) / (1024 * 1024)

    // 4. SHA3-256 (Node crypto / Keccak sponge baseline)
    const sha3Res = runBenchmark(() => {
      crypto.createHash('sha3-256').update(data).digest('hex')
    })
    const sha3Throughput = (size * sha3Res.opsPerSec) / (1024 * 1024)

    results.push({
      size: sizeStr,
      bytes: size,
      astThroughput,
      astLatency: astRes.avgLatencyUs,
      astStreamThroughput,
      sha256Throughput,
      sha3Throughput,
    })
  }

  // Summary Table
  console.log('\n' + '='.repeat(86))
  console.log(' THROUGHPUT COMPARISON SUMMARY (MB/s)')
  console.log('='.repeat(86))

  const header = `| Payload Size | Asterion-256 | Asterion (Streaming) | SHA-256 (Native) | SHA3-256 (Native) |`
  const sep = `|:-------------|-------------:|---------------------:|-----------------:|------------------:|`
  console.log(header)
  console.log(sep)

  for (const r of results) {
    const ast = `${r.astThroughput.toFixed(2)} MB/s`.padStart(12)
    const astStream = `${r.astStreamThroughput.toFixed(2)} MB/s`.padStart(20)
    const sha256 = `${r.sha256Throughput.toFixed(2)} MB/s`.padStart(16)
    const sha3 = `${r.sha3Throughput.toFixed(2)} MB/s`.padStart(17)
    console.log(`| ${r.size.padEnd(12)} | ${ast} | ${astStream} | ${sha256} | ${sha3} |`)
  }

  console.log('\n' + '='.repeat(86))
  console.log(' LATENCY COMPARISON SUMMARY (Per-Hash Duration)')
  console.log('='.repeat(86))
  console.log(`| Payload Size | Asterion-256 Latency |`)
  console.log(`|:-------------|---------------------:|`)
  for (const r of results) {
    const latStr = r.astLatency < 1000
      ? `${r.astLatency.toFixed(2)} µs`
      : `${(r.astLatency / 1000).toFixed(2)} ms`
    console.log(`| ${r.size.padEnd(12)} | ${latStr.padStart(20)} |`)
  }
  console.log('='.repeat(86) + '\n')
}

main()
