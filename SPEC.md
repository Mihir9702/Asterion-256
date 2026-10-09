# Asterion-256 v0.1.0 — Normative Specification

Status: **experimental and unaudited**.

This document defines the byte-level behavior of Asterion-256 v0.1.0. If prose elsewhere conflicts with this file, this file and the committed known-answer vectors define the intended behavior.

## 1. Parameters and notation

- State width: 512 bits
- State lanes: eight unsigned 64-bit words `s[0] ... s[7]`
- Rate: 256 bits / 32 bytes / lanes 0–3
- Capacity: 256 bits / lanes 4–7
- Output: 256 bits / 32 bytes
- Permutation rounds: 14
- Arithmetic: modulo `2^64`
- Lane byte order: little-endian
- String encoding: UTF-8 via WHATWG `TextEncoder`

`ROTL64(x, n)` is a 64-bit left rotation by `n mod 64`.

A message is specified as bytes. A string API first UTF-8 encodes the string; no Unicode normalization is performed.
## 2. Initial state

The initial 64-bit lane values are:

```text
s0 = 4153544552494f4e
s1 = 2d3235362f415258
s2 = 53504f4e47452f52
s3 = 4154453d32353621
s4 = 9e3779b97f4a7c15
s5 = d1b54a32d192ed03
s6 = 94d049bb133111eb
s7 = 8538ebc64b43a1d7
```

The first four words encode ASCII construction identifiers. The remaining fixed words are frozen parameters of v0.1.0; provenance and limitations are discussed in DESIGN.md.

## 3. Round constants

The 14 64-bit round constants are:

```text
243f6a8885a308d3  13198a2e03707344
a4093822299f31d0  082efa98ec4e6c89
452821e638d01377  be5466cf34e90c6c
c0ac29b7c97c50dd  3f84d5b5b5470917
9216d5d98979fb1b  d1310ba698dfb5ac
2ffd72dbd01adfb7  b8e1afed6a267e96
ba7c9045f12c7f99  24a19947b3916cf7
```
## 4. Four-lane ARX mixer

For lane indices `a,b,c,d` and rotation distances `r0,r1,r2,r3`:

```text
s[a] = s[a] + s[b]
s[d] = ROTL64(s[d] XOR s[a], r0)

s[c] = s[c] + s[d]
s[b] = ROTL64(s[b] XOR s[c], r1)

s[a] = s[a] + s[b]
s[d] = ROTL64(s[d] XOR s[a], r2)

s[c] = s[c] + s[d]
s[b] = ROTL64(s[b] XOR s[c], r3)
```

Every addition is reduced modulo `2^64`.

## 5. Permutation

For rounds `r = 0 ... 13`, let `RC = round_constant[r]`.

### 5.1 Round injection

```text
s0 = s0 XOR RC
s4 = s4 XOR ROTL64(RC, 29)
s7 = s7 + (r + 1) * 0x9e3779b9
```

The final addition is modulo `2^64`.
### 5.2 Local mixing

Apply:

```text
MIX4(0,1,2,3, 32,21,17,13)
MIX4(4,5,6,7, 31,23,16,11)
```

### 5.3 Cross-state mixing

Apply:

```text
MIX4(0,5,2,7, 27,19,15,9)
MIX4(4,1,6,3, 25,18,14,7)
```

### 5.4 Lane braid

Using temporary copies of the pre-braid values:

```text
new s1 = old s5
new s5 = old s3
new s3 = old s7
new s7 = old s1

new s2 = old s6
new s6 = old s2
```

Lanes 0 and 4 remain in place during the braid.
### 5.5 Round-dependent rotations

```text
s1 = ROTL64(s1, 1 + ((r *  7) mod 63))
s3 = ROTL64(s3, 1 + ((r * 11) mod 63))
s5 = ROTL64(s5, 1 + ((r * 17) mod 63))
s7 = ROTL64(s7, 1 + ((r * 23) mod 63))
```

That completes one round.

## 6. Rate-block absorption

A rate block is exactly 32 bytes. Parse it as four little-endian 64-bit words `m0..m3`.

For a frame value `F`:

```text
s0 ^= m0
s1 ^= m1
s2 ^= m2
s3 ^= m3

s6 ^= (F << 48) mod 2^64
s7 ^= ROTL64(F * 0x9e37, 17)

PERMUTE(s)
```

The frame values used by v0.1.0 are defined below.
## 7. Domain initialization

The default domain string is `"Asterion-256"`.

1. UTF-8 encode the domain into `D`.
2. Start from the IV.
3. Inject:

```text
s6 ^= (len(D) << 48) mod 2^64
s7 ^= a5a55a5ac3c33c3c
```

4. For every complete 32-byte domain block, absorb it with frame `0xd1`.
5. Construct one mandatory terminating 32-byte domain block, even when `len(D)` is a multiple of 32:
   - copy the remaining 0–31 domain bytes at the start;
   - XOR `0x01` into byte position `remainder_length`;
   - XOR `0x80` into byte position 31.
6. Absorb that terminating block with frame `0xd0`.

Thus domain encoding is structurally separated from message encoding.
## 8. Message absorption

Streaming and one-shot input are equivalent.

Every complete 32-byte message block is absorbed immediately with frame `0x4d`.

The implementation tracks the total message length in bytes.

## 9. Final message block

At `digest()`, always construct one final 32-byte block:

1. Copy the unabsorbed 0–31 message bytes at the start.
2. XOR `0x1f` into byte position `remainder_length`.
3. XOR `0x80` into byte position 31.
4. Absorb the block with frame `0xf1`.

This block is present even when the message length is an exact multiple of 32 bytes.

## 10. Message-length binding

Let:

```text
B = message length in bytes mod 2^64
L = (8 * B) mod 2^64
```

Then:
 ```text
s4 ^= L
s5 ^= ROTL64(B, 17)
s6 ^= 0100000000000101
s7 ^= bitwise_not(B) mod 2^64
```

For the normative v0.1.0 profile, inputs SHOULD be shorter than `2^64` bytes so this binding is unique with respect to byte length.

## 11. Finalization barrier

After length binding:

```text
PERMUTE(s)

s0 ^= 46494e414c213235
s3 ^= 3600000000000001

PERMUTE(s)
```

No digest bytes are exposed before both final permutations complete.

## 12. Squeeze

Serialize `s0, s1, s2, s3` as four little-endian 64-bit words and concatenate them. The result is the 32-byte / 256-bit digest.

Hex output is the lowercase hexadecimal encoding of those 32 bytes.

## 13. API lifecycle

A digest operation finalizes exactly once per initialization.

- `update()` after `digest()` is an error until reset.
- A second `digest()` call before reset is an error.
- `reset()` starts a new session with the specified domain.
- `destroy()` irreversibly disables the instance (including reset).
- Bypassing domain initialization is not part of this protocol.
- Consecutive text chunks are combined as UTF-16 text before WHATWG UTF-8
  encoding, including pairs of surrogates split across text chunks.
  A pending high surrogate followed by bytes is first replaced by U+FFFD.
## 14. Versioning

Asterion-256 v0.1.0 fixes all IV values, constants, rotation schedules, frames, padding rules, length binding, and output order above.

Any change to those values defines a different algorithm and must use a different version identifier. Implementations must not silently change v0.1.0 behavior.

## 15. Security status

This specification describes behavior, not a security proof.

The 256-bit capacity places a generic sponge-security ceiling around 128 bits even under ideal-permutation assumptions. Asterion's custom permutation has not received sufficient cryptanalysis to claim that bound.

The algorithm must therefore be treated as an experimental research construction, not a production cryptographic primitive.
