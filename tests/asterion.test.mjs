import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import {
  Asterion256,
  asterion256,
} from '../dist/Asterion-256.js'

const vectors = JSON.parse(
  await readFile(
    new URL('../vectors/known-answer-vectors.json', import.meta.url),
    'utf8',
  ),
).vectors

function bytesToHex(bytes) {
  return [...bytes]
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('')
}

test('all committed known-answer vectors match', () => {
  for (const vector of vectors) {
    const message = Uint8Array.from(
      Buffer.from(vector.messageHex, 'hex'),
    )
    const actual = new Asterion256(vector.domainUtf8)
      .update(message)
      .digest('hex')

    assert.equal(actual, vector.digestHex, vector.name)
  }
})

test('streaming is equivalent to one-shot hashing', () => {
  for (let length = 0; length <= 257; length++) {
    const message = Uint8Array.from(
      { length },
      (_, index) => (index * 73 + 29) & 0xff,
    )

    const oneShot = new Asterion256()
      .update(message)
      .digest('hex')

    const streaming = new Asterion256()
    let offset = 0
    let step = 1

    while (offset < message.length) {
      const take = Math.min(
        message.length - offset,
        ((step * 17) % 41) + 1,
      )
      streaming.update(message.subarray(offset, offset + take))
      offset += take
      step++
    }

    assert.equal(
      streaming.digest('hex'),
      oneShot,
      `length=${length}`,
    )
  }
})

test('hex and byte output encode the same digest', () => {
  const message = new TextEncoder().encode('Asterion bytes')
  const hex = new Asterion256().update(message).digest('hex')
  const bytes = new Asterion256().update(message).digest('bytes')

  assert.equal(bytes.length, 32)
  assert.equal(bytesToHex(bytes), hex)
})

test('domain separation changes the digest namespace', () => {
  const message = 'same message'
  const a = asterion256(message, 'domain:a')
  const b = asterion256(message, 'domain:b')

  assert.notEqual(a, b)
})

test('exact 32-byte domain boundary remains separated', () => {
  const message = 'probe'
  const a = asterion256(message, 'a'.repeat(32))
  const b = asterion256(message, 'a'.repeat(33))

  assert.notEqual(a, b)
})

test('digest can only finalize once', () => {
  const hash = new Asterion256().update('x')
  hash.digest()

  assert.throws(
    () => hash.digest(),
    /may only be called once/,
  )
})

test('update after digest is rejected', () => {
  const hash = new Asterion256().update('x')
  hash.digest()

  assert.throws(
    () => hash.update('y'),
    /cannot update after digest/,
  )
})
