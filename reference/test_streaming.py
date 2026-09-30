"""Test suite for Asterion-256 Python reference streaming implementation.

Tests:
1. Streaming vs one-shot equivalence across variable lengths and split sizes.
2. Hashlib-style API: update(), digest(), hexdigest(), copy(), reset(), destroy().
3. Known Answer Vector streaming verification.
4. Error conditions and input validation.
"""

from __future__ import annotations

import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "reference") not in sys.path:
    sys.path.insert(0, str(ROOT / "reference"))

from asterion256 import Asterion256, asterion256, asterion256_bytes


class TestAsterion256Streaming(unittest.TestCase):
    def test_known_answer_vectors_streaming(self) -> None:
        vectors_path = ROOT / "vectors" / "known-answer-vectors.json"
        with open(vectors_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for vec in data["vectors"]:
            msg = bytes.fromhex(vec["messageHex"])
            domain = vec["domainUtf8"]
            expected = vec["digestHex"]

            # Stream message in 3-byte chunks
            hasher = Asterion256(domain=domain)
            chunk_size = 7
            for i in range(0, len(msg), chunk_size):
                hasher.update(msg[i : i + chunk_size])

            self.assertEqual(hasher.hexdigest(), expected, f"Failed on vector {vec['name']}")

    def test_streaming_equivalence(self) -> None:
        rng = random.Random(42)
        for length in range(0, 258):
            data = bytes((i * 73 + 29) & 0xFF for i in range(length))
            one_shot = asterion256(data)

            hasher = Asterion256()
            offset = 0
            step = 1
            while offset < len(data):
                take = min(len(data) - offset, ((step * 17) % 41) + 1)
                hasher.update(data[offset : offset + take])
                offset += take
                step += 1

            self.assertEqual(hasher.hexdigest(), one_shot, f"Mismatch at length {length}")

    def test_copy_branching(self) -> None:
        base = Asterion256().update("prefix-data-")
        branch1 = base.copy().update("branch1")
        branch2 = base.copy().update("branch2")

        digest1 = branch1.hexdigest()
        digest2 = branch2.hexdigest()

        self.assertNotEqual(digest1, digest2)
        self.assertEqual(digest1, asterion256("prefix-data-branch1"))
        self.assertEqual(digest2, asterion256("prefix-data-branch2"))

    def test_reset(self) -> None:
        hasher = Asterion256()
        hasher.update("run-one")
        d1 = hasher.hexdigest()

        hasher.reset()
        hasher.update("run-one")
        d2 = hasher.hexdigest()

        self.assertEqual(d1, d2)

    def test_destroy_and_finalization(self) -> None:
        hasher = Asterion256()
        hasher.update("secret")
        hasher.destroy()

        with self.assertRaises(RuntimeError):
            hasher.update("more")
        with self.assertRaises(RuntimeError):
            hasher.digest()
        with self.assertRaises(RuntimeError):
            hasher.copy()

    def test_input_validation(self) -> None:
        hasher = Asterion256()
        hasher.update(b"bytes")
        hasher.update(bytearray(b"bytearray"))
        hasher.update(memoryview(b"memoryview"))
        hasher.update("str")

        with self.assertRaises(TypeError):
            hasher.update(12345)  # type: ignore
        with self.assertRaises(TypeError):
            hasher.update(None)  # type: ignore
        with self.assertRaises(TypeError):
            Asterion256(domain=123)  # type: ignore


if __name__ == "__main__":
    unittest.main()
