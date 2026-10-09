import assert from 'node:assert/strict'
import test from 'node:test'

import {
  Asterion256,
  asterion256,
  createAsterionTransformStream,
  timingSafeEqual,
} from '../dist/Asterion-256.js'

test('finalization prevents further use (not a zeroization proof)', () => {
  const hasher = new Asterion256()
  hasher.update('secret cryptographic key material')
  const digest = hasher.digest('hex')
  assert.equal(typeof digest, 'string')
  assert.equal(digest.length, 64)

  // Verify calling digest again is rejected
  assert.throws(() => hasher.digest(), /may only be called once/)

  // Verify calling update after digest is rejected
  assert.throws(() => hasher.update('more'), /cannot update after digest/)

  // Verify cloning a finalized instance is rejected
  assert.throws(() => hasher.clone(), /cannot clone a finalized/)
})

test('destroy() prevents further use', () => {
  const hasher = new Asterion256()
  hasher.update('sensitive payload')
  hasher.destroy()

  assert.throws(() => hasher.update('data'), /cannot update after digest\(\) or destroy\(\)/)
  assert.throws(() => hasher.digest(), /may only be called once/)
  assert.throws(() => hasher.clone(), /cannot clone a finalized or destroyed instance/)
})

test('clone() enables branching hash calculations', () => {
  const prefix = new Asterion256().update('common-protocol-header-')

  // Fork two independent branches
  const branchA = prefix.clone().update('branch-A')
  const branchB = prefix.clone().update('branch-B')

  const digestA = branchA.digest('hex')
  const digestB = branchB.digest('hex')

  assert.notEqual(digestA, digestB)
  assert.equal(digestA, asterion256('common-protocol-header-branch-A'))
  assert.equal(digestB, asterion256('common-protocol-header-branch-B'))
})

test('reset() reinitializes hasher for instance reuse', () => {
  const hasher = new Asterion256()
  hasher.update('first-run')
  const digest1 = hasher.digest('hex')

  hasher.reset()
  hasher.update('first-run')
  const digest2 = hasher.digest('hex')

  assert.equal(digest1, digest2)
})

test('best-effort comparison works for hex strings and byte arrays', () => {
  const hexA = asterion256('message 1')
  const hexB = asterion256('message 1')
  const hexC = asterion256('message 2')

  assert.equal(timingSafeEqual(hexA, hexB), true)
  assert.equal(timingSafeEqual(hexA, hexC), false)
  assert.equal(timingSafeEqual(hexA, 'short'), false)

  const bytesA = new Asterion256().update('msg').digest('bytes')
  const bytesB = new Asterion256().update('msg').digest('bytes')
  const bytesC = new Asterion256().update('alt').digest('bytes')

  assert.equal(timingSafeEqual(bytesA, bytesB), true)
  assert.equal(timingSafeEqual(bytesA, bytesC), false)

  assert.throws(
    () => timingSafeEqual(hexA, bytesA),
    /arguments must both be strings or both be Uint8Arrays/,
  )
})

test('createAsterionTransformStream streams data correctly', async () => {
  const transformStream = createAsterionTransformStream('hex')
  const writer = transformStream.writable.getWriter()
  const reader = transformStream.readable.getReader()

  const readPromise = reader.read()
  await writer.write(new TextEncoder().encode('streamed '))
  await writer.write(new TextEncoder().encode('data '))
  await writer.write(new TextEncoder().encode('chunks'))
  await writer.close()

  const { value, done } = await readPromise
  assert.equal(done, false)
  assert.equal(value, asterion256('streamed data chunks'))

  const next = await reader.read()
  assert.equal(next.done, true)
})

test('input validation handles various buffer types and rejects invalid inputs', () => {
  const hasher = new Asterion256()

  // String
  hasher.update('str')

  // Uint8Array
  hasher.update(new Uint8Array([1, 2, 3]))

  // ArrayBuffer
  const ab = new ArrayBuffer(4)
  hasher.update(ab)

  // Subarray / TypedArray view
  const u32 = new Uint32Array([0x12345678])
  hasher.update(u32)

  // Rejects invalid types
  assert.throws(() => hasher.update(null), /must be a string, Uint8Array/)
  assert.throws(() => hasher.update(undefined), /must be a string, Uint8Array/)
  assert.throws(() => hasher.update(12345), /must be a string, Uint8Array/)
  assert.throws(() => hasher.update({}), /must be a string, Uint8Array/)

  // Rejects invalid domain in constructor and reset
  assert.throws(() => new Asterion256(123), /domain must be a string/)
  assert.throws(() => hasher.reset(999), /domain must be a string/)
})



test('destroy is irreversible; reset cannot reactivate the instance', () => {
  const h = new Asterion256()
  h.update('secret').destroy()
  assert.throws(() => h.reset(), /cannot reset a destroyed instance/)
})

test('digest input validation does not consume a hasher', () => {
  const h = new Asterion256().update('hello')
  assert.throws(() => h.digest('bad'), /format must be hex or bytes/)
  assert.equal(h.digest('hex'), asterion256('hello'))
})

test('split UTF-16 surrogate pairs match one-shot strings', () => {
  const high = String.fromCharCode(0xd83d)
  const low = String.fromCharCode(0xde00)
  const full = asterion256('Hello 😀!')
  const split = new Asterion256().update('Hello ').update(high).update(low + '!').digest('hex')
  assert.equal(split, full)
})

test('switching from text to raw bytes flushes a pending lone surrogate', () => {
  const high = String.fromCharCode(0xd83d)
  const h = new Asterion256().update(high).update(Uint8Array.from([0x78]))
  assert.equal(h.digest('hex'), asterion256(String.fromCharCode(0xfffd) + 'x'))
})

test('public constructor rejects null-domain bypass', () => {
  assert.throws(() => new Asterion256(null), /domain must be a string/)
})

test('clones preserve pending UTF-16 surrogate state independently', () => {
  const prefix = new Asterion256().update(String.fromCharCode(0xd83d))
  const one = prefix.clone().update(String.fromCharCode(0xde00)).digest('hex')
  const other = prefix.clone().update('Z').digest('hex')
  assert.equal(one, asterion256('😀'))
  assert.equal(other, asterion256(String.fromCharCode(0xfffd) + 'Z'))
})
