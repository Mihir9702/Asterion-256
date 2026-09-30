import assert from 'node:assert/strict'
import test from 'node:test'

import { asterion256 } from '../dist/Asterion-256.js'

function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2)
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = Number.parseInt(hex.slice(i * 2, i * 2 + 2), 16)
  }
  return bytes
}

function countBits(bytes) {
  let count = 0
  for (const b of bytes) {
    let x = b
    while (x > 0) {
      count += x & 1
      x >>= 1
    }
  }
  return count
}

test('statistical smoke: single-bit message flips achieve ~50% avalanche', () => {
  const baseMessage = 'Asterion statistical validation!'
  const baseBytes = new TextEncoder().encode(baseMessage)
  const baseHash = hexToBytes(asterion256(baseBytes))

  const hammingDistances = []

  // Flip each bit in the base message
  for (let byteIdx = 0; byteIdx < baseBytes.length; byteIdx++) {
    for (let bitIdx = 0; bitIdx < 8; bitIdx++) {
      const perturbed = new Uint8Array(baseBytes)
      perturbed[byteIdx] ^= 1 << bitIdx
      const pertHash = hexToBytes(asterion256(perturbed))

      const diff = new Uint8Array(32)
      for (let i = 0; i < 32; i++) {
        diff[i] = baseHash[i] ^ pertHash[i]
      }
      hammingDistances.push(countBits(diff))
    }
  }

  const mean = hammingDistances.reduce((a, b) => a + b, 0) / hammingDistances.length
  const min = Math.min(...hammingDistances)
  const max = Math.max(...hammingDistances)

  // 256-bit ideal mean is 128. Allow +/- 4% on mean across all bit flips
  assert.ok(
    mean >= 122 && mean <= 134,
    `Expected mean avalanche around 128, got ${mean.toFixed(2)}`,
  )

  // No single flip should produce fewer than 85 or more than 171 flipped bits (> 5.3 sigma)
  assert.ok(
    min >= 85 && max <= 171,
    `Extreme avalanche outlier observed: min=${min}, max=${max}`,
  )
})

test('statistical smoke: domain character flip achieves ~50% avalanche', () => {
  const message = 'constant payload'
  const h1 = hexToBytes(asterion256(message, 'Asterion-256'))
  const h2 = hexToBytes(asterion256(message, 'Bsterion-256')) // 1 bit flip in 'A' -> 'B' (0x41 vs 0x42 has 2 bits; 'A' vs '@' has 1 bit)

  const diff = new Uint8Array(32)
  for (let i = 0; i < 32; i++) {
    diff[i] = h1[i] ^ h2[i]
  }
  const flippedBits = countBits(diff)

  // Should flip ~128 bits
  assert.ok(
    flippedBits >= 100 && flippedBits <= 156,
    `Domain flip resulted in ${flippedBits} / 256 bits changed`,
  )
})

test('statistical smoke: output bit balance across sequential inputs is near 50%', () => {
  let totalOnes = 0
  const sampleCount = 400
  const totalBits = sampleCount * 256

  for (let i = 0; i < sampleCount; i++) {
    const hashBytes = hexToBytes(asterion256(`counter:${i}`))
    totalOnes += countBits(hashBytes)
  }

  const ratio = totalOnes / totalBits
  // 400 * 256 = 102,400 bits. Standard error = 0.5 / sqrt(102400) = 0.00156.
  // 3 sigma bound is [0.495, 0.505].
  assert.ok(
    ratio >= 0.490 && ratio <= 0.510,
    `Output bit balance deviated: ${(ratio * 100).toFixed(2)}%`,
  )
})
