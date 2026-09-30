"""Independent reference implementation of Asterion-256 v0.1.0.

Experimental and unaudited. Do not use for production cryptography.
"""

from __future__ import annotations

MASK64 = (1 << 64) - 1
RATE_BYTES = 32
ROUNDS = 14

IV = [
    0x4153544552494F4E,
    0x2D3235362F415258,
    0x53504F4E47452F52,
    0x4154453D32353621,
    0x9E3779B97F4A7C15,
    0xD1B54A32D192ED03,
    0x94D049BB133111EB,
    0x8538EBC64B43A1D7,
]

ROUND_CONSTANTS = [
    0x243F6A8885A308D3, 0x13198A2E03707344,
    0xA4093822299F31D0, 0x082EFA98EC4E6C89,
    0x452821E638D01377, 0xBE5466CF34E90C6C,
    0xC0AC29B7C97C50DD, 0x3F84D5B5B5470917,
    0x9216D5D98979FB1B, 0xD1310BA698DFB5AC,
    0x2FFD72DBD01ADFB7, 0xB8E1AFED6A267E96,
    0xBA7C9045F12C7F99, 0x24A19947B3916CF7,
]


def u64(value: int) -> int:
    return value & MASK64


def rotl64(value: int, bits: int) -> int:
    bits &= 63
    value &= MASK64
    if bits == 0:
        return value
    return u64((value << bits) | (value >> (64 - bits)))


def mix4(
    state: list[int],
    a: int, b: int, c: int, d: int,
    r0: int, r1: int, r2: int, r3: int,
) -> None:
    state[a] = u64(state[a] + state[b])
    state[d] = rotl64(state[d] ^ state[a], r0)
    state[c] = u64(state[c] + state[d])
    state[b] = rotl64(state[b] ^ state[c], r1)

    state[a] = u64(state[a] + state[b])
    state[d] = rotl64(state[d] ^ state[a], r2)
    state[c] = u64(state[c] + state[d])
    state[b] = rotl64(state[b] ^ state[c], r3)


def permute(state: list[int], rounds: int = ROUNDS) -> None:
    if rounds < 0 or rounds > len(ROUND_CONSTANTS):
        raise ValueError(f"rounds must be between 0 and {len(ROUND_CONSTANTS)}")
    for rnd in range(rounds):
        rc = ROUND_CONSTANTS[rnd]
        state[0] ^= rc
        state[4] ^= rotl64(rc, 29)
        state[7] = u64(state[7] + (rnd + 1) * 0x9E3779B9)

        mix4(state, 0, 1, 2, 3, 32, 21, 17, 13)
        mix4(state, 4, 5, 6, 7, 31, 23, 16, 11)
        mix4(state, 0, 5, 2, 7, 27, 19, 15, 9)
        mix4(state, 4, 1, 6, 3, 25, 18, 14, 7)

        lane1, lane2, lane3 = state[1], state[2], state[3]
        lane5, lane6, lane7 = state[5], state[6], state[7]

        state[1], state[5] = lane5, lane3
        state[3], state[7] = lane7, lane1
        state[2], state[6] = lane6, lane2
        state[1] = rotl64(state[1], 1 + ((rnd * 7) % 63))
        state[3] = rotl64(state[3], 1 + ((rnd * 11) % 63))
        state[5] = rotl64(state[5], 1 + ((rnd * 17) % 63))
        state[7] = rotl64(state[7], 1 + ((rnd * 23) % 63))


def absorb_block(state: list[int], block: bytes, frame: int) -> None:
    if len(block) != RATE_BYTES:
        raise ValueError("Asterion-256 blocks must be exactly 32 bytes")

    for lane in range(4):
        start = lane * 8
        state[lane] ^= int.from_bytes(block[start:start + 8], "little")

    state[6] ^= u64(frame << 48)
    state[7] ^= rotl64(frame * 0x9E37, 17)
    permute(state)


def _domain_state(domain: str) -> list[int]:
    domain_bytes = domain.encode("utf-8")
    state = IV.copy()

    state[6] ^= u64(len(domain_bytes) << 48)
    state[7] ^= 0xA5A55A5AC3C33C3C

    offset = 0
    while offset + RATE_BYTES <= len(domain_bytes):
        absorb_block(
            state,
            domain_bytes[offset:offset + RATE_BYTES],
            0xD1,
        )
        offset += RATE_BYTES

    remainder = domain_bytes[offset:]
    final_block = bytearray(RATE_BYTES)
    final_block[:len(remainder)] = remainder
    final_block[len(remainder)] ^= 0x01
    final_block[-1] ^= 0x80
    absorb_block(state, bytes(final_block), 0xD0)
    return state


def asterion256_bytes(
    message: bytes,
    domain: str = "Asterion-256",
) -> bytes:
    state = _domain_state(domain)
    offset = 0

    while offset + RATE_BYTES <= len(message):
        absorb_block(
            state,
            message[offset:offset + RATE_BYTES],
            0x4D,
        )
        offset += RATE_BYTES

    remainder = message[offset:]
    final_block = bytearray(RATE_BYTES)
    final_block[:len(remainder)] = remainder
    final_block[len(remainder)] ^= 0x1F
    final_block[-1] ^= 0x80
    absorb_block(state, bytes(final_block), 0xF1)

    byte_length = u64(len(message))
    bit_length = u64(len(message) << 3)

    state[4] ^= bit_length
    state[5] ^= rotl64(byte_length, 17)
    state[6] ^= 0x0100000000000101
    state[7] ^= (~byte_length) & MASK64

    permute(state)

    state[0] ^= 0x46494E414C213235
    state[3] ^= 0x3600000000000001

    permute(state)

    return b"".join(
        u64(state[lane]).to_bytes(8, "little")
        for lane in range(4)
    )


def asterion256(
    message: bytes | str,
    domain: str = "Asterion-256",
) -> str:
    if isinstance(message, str):
        message = message.encode("utf-8")
    return asterion256_bytes(message, domain).hex()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Asterion-256 v0.1.0 reference implementation"
    )
    parser.add_argument("message", help="UTF-8 text message")
    parser.add_argument(
        "--domain",
        default="Asterion-256",
        help="UTF-8 domain string",
    )
    args = parser.parse_args()
    print(asterion256(args.message, args.domain))
