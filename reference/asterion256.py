"""Independent reference implementation of Asterion-256 v0.1.0.

Experimental and unaudited. Do not use for production cryptography.
"""

from __future__ import annotations

MASK64 = (1 << 64) - 1
RATE_BYTES = 32
ROUNDS = 14


def encode_text(text: str) -> bytes:
    """Emulate WHATWG TextEncoder for Python strings, including lone surrogates."""
    return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace").encode("utf-8")


def encode_text(text: str) -> bytes:
    """Emulate WHATWG TextEncoder for Python strings, including lone surrogates."""
    return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace").encode("utf-8")

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


class Asterion256:
    """Asterion-256 stateful hasher supporting streaming input.
    
    Provides hashlib-like names, but digest() and hexdigest() FINALIZE.
    State overwrite is best-effort; immutable integers cannot be securely erased.
    """

    def __init__(self, domain: str = "Asterion-256") -> None:
        if not isinstance(domain, str):
            raise TypeError("Asterion256: domain must be a string")
        self._domain = domain
        self._state: list[int] = [0] * 8
        self._buffer = bytearray()
        self._total_bytes = 0
        self._finalized = False
        self._destroyed = False
        self._pending_high_surrogate = ""
        self._init_domain(domain)

    def _init_domain(self, domain: str) -> None:
        domain_bytes = encode_text(domain)
        self._state = IV.copy()
        self._state[6] ^= u64(len(domain_bytes) << 48)
        self._state[7] ^= 0xA5A55A5AC3C33C3C

        offset = 0
        while offset + RATE_BYTES <= len(domain_bytes):
            absorb_block(
                self._state,
                domain_bytes[offset : offset + RATE_BYTES],
                0xD1,
            )
            offset += RATE_BYTES

        remainder = domain_bytes[offset:]
        final_block = bytearray(RATE_BYTES)
        final_block[: len(remainder)] = remainder
        final_block[len(remainder)] ^= 0x01
        final_block[-1] ^= 0x80
        absorb_block(self._state, bytes(final_block), 0xD0)

    def update(self, message: bytes | bytearray | memoryview | str) -> Asterion256:
        """Feed additional message bytes into the hasher."""
        if self._finalized:
            raise RuntimeError("Asterion256: cannot update after digest() or destroy()")

        if isinstance(message, str):
            text = self._pending_high_surrogate + message
            self._pending_high_surrogate = ""
            if text and 0xD800 <= ord(text[-1]) <= 0xDBFF:
                self._pending_high_surrogate = text[-1]
                text = text[:-1]
            data = encode_text(text)
        elif isinstance(message, (bytes, bytearray, memoryview)):
            data = bytes(message)
        else:
            raise TypeError(
                "Asterion256.update: input must be bytes, bytearray, memoryview, or str"
            )

        if not isinstance(message, str) and self._pending_high_surrogate:
            self._pending_high_surrogate = ""
            self.update("\ufffd")

        self._total_bytes += len(data)
        self._buffer.extend(data)

        # Absorb full 32-byte rate blocks
        while len(self._buffer) >= RATE_BYTES:
            block = bytes(self._buffer[:RATE_BYTES])
            del self._buffer[:RATE_BYTES]
            absorb_block(self._state, block, 0x4D)

        return self

    def digest(self, format: str = "bytes") -> bytes | str:
        """Finalize and return the 32-byte digest in 'bytes' or 'hex' format."""
        if self._finalized:
            raise RuntimeError("Asterion256: digest() may only be called once")
        if format not in ("bytes", "hex"):
            raise ValueError("format must be bytes or hex")
        if self._pending_high_surrogate:
            self._pending_high_surrogate = ""
            self.update("\ufffd")
        self._finalized = True

        remainder = bytes(self._buffer)
        final_block = bytearray(RATE_BYTES)
        final_block[: len(remainder)] = remainder
        final_block[len(remainder)] ^= 0x1F
        final_block[-1] ^= 0x80
        absorb_block(self._state, bytes(final_block), 0xF1)

        byte_length = u64(self._total_bytes)
        bit_length = u64(self._total_bytes << 3)

        self._state[4] ^= bit_length
        self._state[5] ^= rotl64(byte_length, 17)
        self._state[6] ^= 0x0100000000000101
        self._state[7] ^= (~byte_length) & MASK64

        permute(self._state)

        self._state[0] ^= 0x46494E414C213235
        self._state[3] ^= 0x3600000000000001

        permute(self._state)

        digest_bytes = b"".join(
            u64(self._state[lane]).to_bytes(8, "little") for lane in range(4)
        )

        # Best-effort cleanup; immutable Python integers cannot be guaranteed erased.
        self._state[:] = [0] * 8
        self._buffer.clear()
        self._total_bytes = 0
        self._pending_high_surrogate = ""

        if format == "bytes":
            return digest_bytes
        elif format == "hex":
            return digest_bytes.hex()
        else:
            raise ValueError("format must be 'bytes' or 'hex'")

    def hexdigest(self) -> str:
        """Finalize and return the 64-character lowercase hex digest."""
        res = self.digest(format="hex")
        assert isinstance(res, str)
        return res

    def copy(self) -> Asterion256:
        """Create an independent copy of this hasher at its current state."""
        if self._finalized:
            raise RuntimeError("Asterion256: cannot copy a finalized or destroyed instance")
        clone = Asterion256.__new__(Asterion256)
        clone._domain = self._domain
        clone._state = self._state.copy()
        clone._buffer = bytearray(self._buffer)
        clone._total_bytes = self._total_bytes
        clone._finalized = self._finalized
        clone._destroyed = self._destroyed
        clone._pending_high_surrogate = self._pending_high_surrogate
        return clone

    clone = copy

    def reset(self, domain: str = "Asterion-256") -> Asterion256:
        """Reset a non-destroyed hasher to its initial state."""
        if self._destroyed:
            raise RuntimeError("Asterion256: cannot reset a destroyed instance")
        if not isinstance(domain, str):
            raise TypeError("Asterion256.reset: domain must be a string")
        self._domain = domain
        self._state[:] = [0] * 8
        self._pending_high_surrogate = ""
        self._buffer.clear()
        self._total_bytes = 0
        self._finalized = False
        self._init_domain(domain)
        return self

    def destroy(self) -> None:
        """Best-effort overwrite of reachable state; irreversibly disable this instance."""
        self._state[:] = [0] * 8
        self._buffer.clear()
        self._total_bytes = 0
        self._pending_high_surrogate = ""
        self._destroyed = True
        self._finalized = True


def asterion256_bytes(
    message: bytes | bytearray | memoryview | str,
    domain: str = "Asterion-256",
) -> bytes:
    res = Asterion256(domain).update(message).digest("bytes")
    assert isinstance(res, bytes)
    return res


def asterion256(
    message: bytes | bytearray | memoryview | str,
    domain: str = "Asterion-256",
) -> str:
    return Asterion256(domain).update(message).hexdigest()


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
