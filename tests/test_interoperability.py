"""Cross-language property tests against the separate TypeScript implementation."""
from __future__ import annotations

import json
import random
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))
from asterion256 import Asterion256, asterion256


class CrossLanguage(unittest.TestCase):
    def test_random_vectors_domains_and_streaming(self) -> None:
        rng = random.Random(20261008)
        cases = []
        for length in [0, 1, 2, 15, 16, 31, 32, 33, 63, 64, 65, 127, 128, 129, 1024, 2049]:
            data = bytes(rng.getrandbits(8) for _ in range(length))
            for domain in ["", "Asterion-256", "x" * 32, "x" * 33]:
                cases.append({"domain": domain, "messageHex": data.hex()})
        for _ in range(96):
            length = rng.randrange(0, 4096)
            data = bytes(rng.getrandbits(8) for _ in range(length))
            pieces = []
            i = 0
            while i < length:
                n = rng.randrange(1, 58)
                pieces.append(data[i:i+n].hex())
                i += n
            cases.append({"domain": "random-domain", "byteChunks": pieces})
        # Regression: TypeScript used to exceed the 64-bit domain lane width.
        for length in (65535, 65536, 65537):
            cases.append({"domain": "X" * length, "messageHex": "ff"})
        # Supplementary-plane surrogate pair split across calls.
        cases += [
            {"domain": "unicode", "stringChunks": ["\ud83d", "\ude00", "!"]},
            {"domain": "unicode", "stringChunks": ["\ud83d"]},
            {"domain": "unicode", "stringChunks": ["\ud83d", "x"]},
            {"domain": "unicode", "stringChunks": ["hello", " ", "\ud83d", "\ude00"]},
        ]

        expected = []
        for row in cases:
            h = Asterion256(row["domain"])
            if "stringChunks" in row:
                for chunk in row["stringChunks"]:
                    h.update(chunk)
            elif "byteChunks" in row:
                for chunk in row["byteChunks"]:
                    h.update(bytes.fromhex(chunk))
            else:
                h.update(bytes.fromhex(row["messageHex"]))
            expected.append(h.hexdigest())

        proc = subprocess.run(
            ["node", str(ROOT / "tests" / "interop_runner.mjs")],
            input=json.dumps(cases, ensure_ascii=True) + "\n",
            capture_output=True, text=True, encoding="utf-8", cwd=ROOT, check=True,
        )
        actual = json.loads(proc.stdout)
        self.assertEqual(len(actual), len(expected))
        for i, (a, e) in enumerate(zip(actual, expected)):
            self.assertEqual(a, e, f"case={i}, domain={cases[i]['domain'][:24]!r}")


if __name__ == "__main__":
    unittest.main()
