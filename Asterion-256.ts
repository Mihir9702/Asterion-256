/**
 * Asterion-256
 * ---------------------------------------------------------------------------
 * Experimental 256-bit cryptographic hash construction.
 *
 * Architecture:
 *   512-bit internal state
 *   8 × 64-bit lanes
 *   256-bit absorption rate
 *   256-bit capacity
 *   14-round ARX permutation
 *   Streaming input
 *   Domain separation
 *   Framed absorption
 *   Message-length binding
 *   Double-permutation finalization barrier
 *
 * ---------------------------------------------------------------------------
 * SECURITY WARNING
 * ---------------------------------------------------------------------------
 *
 * This is a NEW and UNAUDITED cryptographic construction.
 *
 * It is suitable for experimentation, research, hashing demos, procedural
 * fingerprints, educational work, and exploring hash-function architecture.
 *
 * It should NOT replace established primitives such as:
 *
 *   SHA-256
 *   SHA-3
 *   BLAKE2
 *   BLAKE3
 *   Argon2id
 *
 * for real security boundaries.
 * ---------------------------------------------------------------------------
 */

const MASK_64 = 0xffff_ffff_ffff_ffffn

const RATE_BYTES = 32
const OUTPUT_BYTES = 32
const ROUNDS = 14

/**
 * 512-bit initialization vector.
 *
 * The first four words deliberately identify the construction rather than
 * hiding the initialization behind unexplained "nothing-up-my-sleeve"
 * constants.
 */
const IV = [
  0x4153_5445_5249_4f4en, // "ASTERION"
  0x2d32_3536_2f41_5258n, // "-256/ARX"
  0x5350_4f4e_4745_2f52n, // "SPONGE/R"
  0x4154_453d_3235_3621n, // "ATE=256!"

  0x9e37_79b9_7f4a_7c15n,
  0xd1b5_4a32_d192_ed03n,
  0x94d0_49bb_1331_11ebn,
  0x8538_ebc6_4b43_a1d7n,
] as const

/**
 * Round constants.
 *
 * They destroy round symmetry and ensure identical-looking internal
 * configurations do not travel through identical permutations.
 */
const ROUND_CONSTANTS = [
  0x243f_6a88_85a3_08d3n,
  0x1319_8a2e_0370_7344n,
  0xa409_3822_299f_31d0n,
  0x082e_fa98_ec4e_6c89n,
  0x4528_21e6_38d0_1377n,
  0xbe54_66cf_34e9_0c6cn,
  0xc0ac_29b7_c97c_50ddn,
  0x3f84_d5b5_b547_0917n,
  0x9216_d5d9_8979_fb1bn,
  0xd131_0ba6_98df_b5acn,
  0x2ffd_72db_d01a_dfb7n,
  0xb8e1_afed_6a26_7e96n,
  0xba7c_9045_f12c_7f99n,
  0x24a1_9947_b391_6cf7n,
] as const

const encoder = new TextEncoder()

const ROT_SHIFTS = Array.from({ length: 64 }, (_, i) => ({
  shl: BigInt(i),
  shr: BigInt(64 - i),
}))

const ROUND_CONSTANTS_ROTL29 = ROUND_CONSTANTS.map(
  (rc) => ((rc << 29n) | (rc >> 35n)) & MASK_64,
)

const ROUND_S7_ADD = Array.from(
  { length: ROUNDS },
  (_, r) => (BigInt(r + 1) * 0x9e37_79b9n) & MASK_64,
)

const ROUND_LANE_ROTS = Array.from({ length: ROUNDS }, (_, r) => ({
  r1: 1 + ((r * 7) % 63),
  r3: 1 + ((r * 11) % 63),
  r5: 1 + ((r * 17) % 63),
  r7: 1 + ((r * 23) % 63),
}))

const HEX_TABLE = Array.from({ length: 256 }, (_, i) =>
  i.toString(16).padStart(2, '0'),
)

/* -------------------------------------------------------------------------- */
/*                                64-bit core                                 */
/* -------------------------------------------------------------------------- */

function u64(value: bigint): bigint {
  return value & MASK_64
}

function add64(a: bigint, b: bigint): bigint {
  return (a + b) & MASK_64
}

function rotl64(value: bigint, bits: number): bigint {
  const n = bits & 63

  if (n === 0) {
    return value & MASK_64
  }

  const rot = ROT_SHIFTS[n]
  return (
    (value << rot.shl) |
    (value >> rot.shr)
  ) & MASK_64
}

/* -------------------------------------------------------------------------- */
/*                              Byte conversion                               */
/* -------------------------------------------------------------------------- */

function readU64LE(
  bytes: Uint8Array,
  offset: number,
): bigint {
  if (offset + 8 <= bytes.length) {
    return new DataView(
      bytes.buffer,
      bytes.byteOffset + offset,
      8,
    ).getBigUint64(0, true)
  }

  let value = 0n

  for (let i = 0; i < 8; i++) {
    value |= BigInt(bytes[offset + i] ?? 0) << BigInt(i * 8)
  }

  return value
}

function writeU64LE(
  value: bigint,
  output: Uint8Array,
  offset: number,
): void {
  if (offset + 8 <= output.length) {
    new DataView(
      output.buffer,
      output.byteOffset + offset,
      8,
    ).setBigUint64(0, value, true)
    return
  }

  let x = value & MASK_64

  for (let i = 0; i < 8; i++) {
    output[offset + i] = Number(x & 0xffn)
    x >>= 8n
  }
}

function toHex(bytes: Uint8Array): string {
  let output = ''

  for (let i = 0; i < bytes.length; i++) {
    output += HEX_TABLE[bytes[i]]
  }

  return output
}

/* -------------------------------------------------------------------------- */
/*                              Asterion mixer                                */
/* -------------------------------------------------------------------------- */

/**
 * Four-lane reversible ARX mixer.
 *
 * ARX:
 *
 *   A = Addition
 *   R = Rotation
 *   X = XOR
 *
 * The intentionally asymmetric rotation distances stop the two halves
 * of the mixer from behaving as mirrors of one another.
 */
function mix4(
  state: bigint[],
  a: number,
  b: number,
  c: number,
  d: number,
  r0: number,
  r1: number,
  r2: number,
  r3: number,
): void {
  state[a] = add64(
    state[a],
    state[b],
  )

  state[d] = rotl64(
    state[d] ^ state[a],
    r0,
  )

  state[c] = add64(
    state[c],
    state[d],
  )

  state[b] = rotl64(
    state[b] ^ state[c],
    r1,
  )

  state[a] = add64(
    state[a],
    state[b],
  )

  state[d] = rotl64(
    state[d] ^ state[a],
    r2,
  )

  state[c] = add64(
    state[c],
    state[d],
  )

  state[b] = rotl64(
    state[b] ^ state[c],
    r3,
  )
}

/* -------------------------------------------------------------------------- */
/*                         512-bit Asterion permutation                       */
/* -------------------------------------------------------------------------- */

/**
 * The heart of Asterion.
 *
 * One permutation performs:
 *
 *   round-constant injection
 *            ↓
 *   local hemisphere mixing
 *            ↓
 *   cross-hemisphere mixing
 *            ↓
 *   reversible lane braid
 *            ↓
 *   round-dependent rotations
 *
 * The goal is rapid diffusion:
 *
 * one changed input bit
 *
 *        ↓
 *
 * changes one lane
 *
 *        ↓
 *
 * crosses into neighboring lanes
 *
 *        ↓
 *
 * crosses state hemispheres
 *
 *        ↓
 *
 * gets relocated by the braid
 *
 *        ↓
 *
 * enters subsequent rounds from a different position.
 */
function permute(state: bigint[]): void {
  for (let round = 0; round < ROUNDS; round++) {
    state[0] ^= ROUND_CONSTANTS[round]
    state[4] ^= ROUND_CONSTANTS_ROTL29[round]
    state[7] = add64(state[7], ROUND_S7_ADD[round])

    /* ---------------------------------------------------------------------- */
    /*                           Local diffusion                              */
    /* ---------------------------------------------------------------------- */

    mix4(
      state,
      0,
      1,
      2,
      3,
      32,
      21,
      17,
      13,
    )

    mix4(
      state,
      4,
      5,
      6,
      7,
      31,
      23,
      16,
      11,
    )

    /* ---------------------------------------------------------------------- */
    /*                         Cross-state diffusion                          */
    /* ---------------------------------------------------------------------- */

    mix4(
      state,
      0,
      5,
      2,
      7,
      27,
      19,
      15,
      9,
    )

    mix4(
      state,
      4,
      1,
      6,
      3,
      25,
      18,
      14,
      7,
    )

    /* ---------------------------------------------------------------------- */
    /*                             Lane braid                                 */
    /* ---------------------------------------------------------------------- */

    const lane1 = state[1]
    const lane2 = state[2]
    const lane3 = state[3]

    const lane5 = state[5]
    const lane6 = state[6]
    const lane7 = state[7]

    /*
     * Outer braid:
     *
     *     1 ─────→ 7
     *     ↑        │
     *     │        ↓
     *     5 ←───── 3
     */

    state[1] = lane5
    state[5] = lane3
    state[3] = lane7
    state[7] = lane1

    /*
     * Inner swap:
     *
     *     2 ↔ 6
     */

    state[2] = lane6
    state[6] = lane2

    /* ---------------------------------------------------------------------- */
    /*                       Non-stationary lane phase                        */
    /* ---------------------------------------------------------------------- */

    const rots = ROUND_LANE_ROTS[round]
    state[1] = rotl64(state[1], rots.r1)
    state[3] = rotl64(state[3], rots.r3)
    state[5] = rotl64(state[5], rots.r5)
    state[7] = rotl64(state[7], rots.r7)
  }
}

/* -------------------------------------------------------------------------- */
/*                              Asterion-256                                  */
/* -------------------------------------------------------------------------- */

export class Asterion256 {
  #state: bigint[] = [...IV]

  #buffer = new Uint8Array(
    RATE_BYTES,
  )

  #bufferLength = 0

  #totalBytes = 0n

  #finalized = false

  /**
   * Domain separation allows the same primitive to be used for logically
   * different purposes without treating their inputs as belonging to the
   * same namespace.
   *
   * @param domain UTF-8 domain separator string (or null for internal cloning).
   */
  constructor(
    domain: string | null = 'Asterion-256',
  ) {
    if (domain === null) {
      // Internal sentinel for cloning: bypass domain absorption
      return
    }

    if (typeof domain !== 'string') {
      throw new TypeError(
        'Asterion256: domain must be a string.',
      )
    }

    this.#initDomain(domain)
  }

  #initDomain(domain: string): void {
    const domainBytes =
      encoder.encode(domain)

    this.#state = [...IV]

    this.#state[6] ^=
      BigInt(domainBytes.length) << 48n

    this.#state[7] ^=
      0xa5a5_5a5a_c3c3_3c3cn

    let offset = 0

    /*
     * Consume complete domain blocks first.
     */
    while (
      offset + RATE_BYTES <=
      domainBytes.length
    ) {
      this.#absorbBlock(
        domainBytes.subarray(
          offset,
          offset + RATE_BYTES,
        ),
        0xd1n,
      )

      offset += RATE_BYTES
    }

    /*
     * Domain material ALWAYS receives an explicit terminating block.
     */
    const finalDomainBlock =
      new Uint8Array(
        RATE_BYTES,
      )

    const remainder =
      domainBytes.subarray(offset)

    finalDomainBlock.set(
      remainder,
    )

    finalDomainBlock[
      remainder.length
    ] ^= 0x01

    finalDomainBlock[
      RATE_BYTES - 1
    ] ^= 0x80

    this.#absorbBlock(
      finalDomainBlock,
      0xd0n,
    )
  }

  /* ------------------------------------------------------------------------ */
  /*                             Lifecycle Methods                            */
  /* ------------------------------------------------------------------------ */

  /**
   * Creates an independent deep clone of this hasher at its current state.
   * Enables state snapshotting to efficiently hash branching prefixes.
   */
  clone(): Asterion256 {
    if (this.#finalized) {
      throw new Error(
        'Asterion256: cannot clone a finalized or destroyed instance.',
      )
    }

    const copy = new Asterion256(null)
    copy.#state = [...this.#state]
    copy.#buffer = new Uint8Array(this.#buffer)
    copy.#bufferLength = this.#bufferLength
    copy.#totalBytes = this.#totalBytes
    copy.#finalized = this.#finalized
    return copy
  }

  /**
   * Resets the hasher instance back to its initial state for the specified domain.
   */
  reset(domain = 'Asterion-256'): this {
    if (typeof domain !== 'string') {
      throw new TypeError(
        'Asterion256.reset: domain must be a string.',
      )
    }

    this.#buffer.fill(0)
    this.#bufferLength = 0
    this.#totalBytes = 0n
    this.#finalized = false
    this.#initDomain(domain)
    return this
  }

  /**
   * Explicitly wipes all sensitive internal state, buffer memory, and counters.
   * Permanently finalizes this instance so it cannot be used or inspected.
   */
  destroy(): void {
    this.#state.fill(0n)
    this.#buffer.fill(0)
    this.#bufferLength = 0
    this.#totalBytes = 0n
    this.#finalized = true
  }

  /* ------------------------------------------------------------------------ */
  /*                                 Update                                   */
  /* ------------------------------------------------------------------------ */

  update(
    input: string | Uint8Array | ArrayBufferView | ArrayBuffer,
  ): this {
    if (this.#finalized) {
      throw new Error(
        'Asterion256: cannot update after digest() or destroy().',
      )
    }

    let bytes: Uint8Array

    if (typeof input === 'string') {
      bytes = encoder.encode(input)
    } else if (input instanceof Uint8Array) {
      bytes = input
    } else if (ArrayBuffer.isView(input)) {
      bytes = new Uint8Array(
        input.buffer,
        input.byteOffset,
        input.byteLength,
      )
    } else if (input instanceof ArrayBuffer) {
      bytes = new Uint8Array(input)
    } else {
      throw new TypeError(
        'Asterion256.update: input must be a string, Uint8Array, Buffer, or ArrayBuffer.',
      )
    }

    this.#totalBytes +=
      BigInt(bytes.length)

    let offset = 0

    /*
     * Fast path: absorb complete 32-byte blocks directly without copying
     * into intermediate buffer when buffer is empty. Uses a single DataView
     * over the input bytes to eliminate per-block object allocation.
     */
    if (this.#bufferLength === 0 && bytes.length >= RATE_BYTES) {
      const view = new DataView(
        bytes.buffer,
        bytes.byteOffset,
        bytes.byteLength,
      )

      while (offset + RATE_BYTES <= bytes.length) {
        this.#absorbWords(
          view.getBigUint64(offset, true),
          view.getBigUint64(offset + 8, true),
          view.getBigUint64(offset + 16, true),
          view.getBigUint64(offset + 24, true),
          0x4dn,
        )
        offset += RATE_BYTES
      }
    }

    while (
      offset < bytes.length
    ) {
      const available =
        RATE_BYTES -
        this.#bufferLength

      const remaining =
        bytes.length -
        offset

      const take = Math.min(
        available,
        remaining,
      )

      this.#buffer.set(
        bytes.subarray(
          offset,
          offset + take,
        ),
        this.#bufferLength,
      )

      this.#bufferLength += take
      offset += take

      /*
       * A complete 256-bit rate block is absorbed immediately.
       */
      if (
        this.#bufferLength ===
        RATE_BYTES
      ) {
        this.#absorbBlock(
          this.#buffer,
          0x4dn,
        )

        this.#buffer.fill(0)

        this.#bufferLength = 0
      }
    }

    return this
  }

  /* ------------------------------------------------------------------------ */
  /*                                Finalize                                  */
  /* ------------------------------------------------------------------------ */

  digest(
    format: 'hex' | 'bytes' =
      'hex',
  ): string | Uint8Array {
    if (this.#finalized) {
      throw new Error(
        'Asterion256: digest() may only be called once.',
      )
    }

    this.#finalized = true

    /* ---------------------------------------------------------------------- */
    /*                           Final input block                            */
    /* ---------------------------------------------------------------------- */

    const finalBlock =
      new Uint8Array(
        RATE_BYTES,
      )

    finalBlock.set(
      this.#buffer.subarray(
        0,
        this.#bufferLength,
      ),
    )

    /*
     * Beginning of final-padding marker.
     */
    finalBlock[
      this.#bufferLength
    ] ^= 0x1f

    /*
     * End-of-rate marker.
     */
    finalBlock[
      RATE_BYTES - 1
    ] ^= 0x80

    this.#absorbBlock(
      finalBlock,
      0xf1n,
    )

    /* ---------------------------------------------------------------------- */
    /*                         Message-length binding                         */
    /* ---------------------------------------------------------------------- */

    const bitLength = u64(
      this.#totalBytes << 3n,
    )

    const byteLength = u64(
      this.#totalBytes,
    )

    /*
     * Length information enters the CAPACITY side rather than being treated
     * as ordinary message content.
     */

    this.#state[4] ^=
      bitLength

    this.#state[5] ^=
      rotl64(
        byteLength,
        17,
      )

    this.#state[6] ^=
      0x0100_0000_0000_0101n

    this.#state[7] ^=
      (~byteLength) &
      MASK_64

    /* ---------------------------------------------------------------------- */
    /*                         Finalization barrier                           */
    /* ---------------------------------------------------------------------- */

    /*
     * No internal state is exposed immediately after message absorption.
     */

    permute(
      this.#state,
    )

    /*
     * Explicit finalization frame.
     */

    this.#state[0] ^=
      0x4649_4e41_4c21_3235n

    this.#state[3] ^=
      0x3600_0000_0000_0001n

    /*
     * Second complete permutation separates the digest state from the
     * absorption state.
     */

    permute(
      this.#state,
    )

    /* ---------------------------------------------------------------------- */
    /*                              Squeeze                                   */
    /* ---------------------------------------------------------------------- */

    const output =
      new Uint8Array(
        OUTPUT_BYTES,
      )

    const outView = new DataView(
      output.buffer,
      output.byteOffset,
      OUTPUT_BYTES,
    )

    outView.setBigUint64(0, this.#state[0], true)
    outView.setBigUint64(8, this.#state[1], true)
    outView.setBigUint64(16, this.#state[2], true)
    outView.setBigUint64(24, this.#state[3], true)

    /* ---------------------------------------------------------------------- */
    /*                     Secure state zeroization                           */
    /* ---------------------------------------------------------------------- */

    this.#state.fill(0n)
    this.#buffer.fill(0)
    this.#bufferLength = 0
    this.#totalBytes = 0n

    return format === 'bytes'
      ? output
      : toHex(output)
  }

  /* ------------------------------------------------------------------------ */
  /*                                Absorb                                    */
  /* ------------------------------------------------------------------------ */

  #absorbWords(
    m0: bigint,
    m1: bigint,
    m2: bigint,
    m3: bigint,
    frame: bigint,
  ): void {
    this.#state[0] ^= m0
    this.#state[1] ^= m1
    this.#state[2] ^= m2
    this.#state[3] ^= m3

    this.#state[6] ^=
      frame << 48n

    this.#state[7] ^=
      rotl64(
        frame * 0x9e37n,
        17,
      )

    permute(
      this.#state,
    )
  }

  #absorbBlock(
    block: Uint8Array,
    frame: bigint,
  ): void {
    if (block.byteLength >= RATE_BYTES) {
      const view = new DataView(
        block.buffer,
        block.byteOffset,
        RATE_BYTES,
      )
      this.#absorbWords(
        view.getBigUint64(0, true),
        view.getBigUint64(8, true),
        view.getBigUint64(16, true),
        view.getBigUint64(24, true),
        frame,
      )
    } else {
      let m0 = 0n
      let m1 = 0n
      let m2 = 0n
      let m3 = 0n

      m0 = readU64LE(block, 0)
      m1 = readU64LE(block, 8)
      m2 = readU64LE(block, 16)
      m3 = readU64LE(block, 24)

      this.#absorbWords(m0, m1, m2, m3, frame)
    }
  }
}

/* -------------------------------------------------------------------------- */
/*                           Convenience function                             */
/* -------------------------------------------------------------------------- */

export function asterion256(
  input: string | Uint8Array | ArrayBufferView | ArrayBuffer,
  domain = 'Asterion-256',
): string {
  return new Asterion256(domain)
    .update(input)
    .digest('hex') as string
}

/* -------------------------------------------------------------------------- */
/*                        Constant-Time Comparison                            */
/* -------------------------------------------------------------------------- */

/**
 * Constant-time equality comparison for two digests (hex strings or Uint8Array bytes)
 * to prevent timing side-channel attacks during authentication or verification.
 */
export function timingSafeEqual(
  a: string | Uint8Array,
  b: string | Uint8Array,
): boolean {
  if (typeof a === 'string' && typeof b === 'string') {
    if (a.length !== b.length) {
      return false
    }
    let diff = 0
    for (let i = 0; i < a.length; i++) {
      diff |= a.charCodeAt(i) ^ b.charCodeAt(i)
    }
    return diff === 0
  }

  if (a instanceof Uint8Array && b instanceof Uint8Array) {
    if (a.length !== b.length) {
      return false
    }
    let diff = 0
    for (let i = 0; i < a.length; i++) {
      diff |= a[i] ^ b[i]
    }
    return diff === 0
  }

  throw new TypeError(
    'timingSafeEqual: arguments must both be strings or both be Uint8Arrays.',
  )
}

/* -------------------------------------------------------------------------- */
/*                           WHATWG Stream Support                            */
/* -------------------------------------------------------------------------- */

/**
 * Creates a WHATWG TransformStream for streaming hashing in Node.js 18+, browsers,
 * Deno, and Bun. Emits a single digest (hex string or Uint8Array) upon stream completion.
 */
export function createAsterionTransformStream(
  format: 'hex' | 'bytes' = 'hex',
  domain = 'Asterion-256',
): TransformStream<Uint8Array | string, string | Uint8Array> {
  const hasher = new Asterion256(domain)
  return new TransformStream({
    transform(chunk) {
      hasher.update(chunk)
    },
    flush(controller) {
      controller.enqueue(hasher.digest(format))
    },
  })
}