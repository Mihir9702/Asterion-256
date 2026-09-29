"""Verify Asterion-256 v0.1.0 known-answer vectors with the Python reference."""

from __future__ import annotations

import json
from pathlib import Path

from asterion256 import asterion256_bytes

ROOT = Path(__file__).resolve().parents[1]
VECTOR_FILE = ROOT / "vectors" / "known-answer-vectors.json"


def main() -> None:
    document = json.loads(VECTOR_FILE.read_text(encoding="utf-8"))
    failures: list[str] = []

    if document.get("algorithm") != "Asterion-256":
        failures.append("algorithm metadata mismatch")

    for vector in document["vectors"]:
        message = bytes.fromhex(vector["messageHex"])
        actual = asterion256_bytes(
            message,
            vector["domainUtf8"],
        ).hex()
        if actual != vector["digestHex"]:
            failures.append(
                f"{vector['name']}: expected "
                f"{vector['digestHex']}, got {actual}"
            )

    if failures:
        for failure in failures:
            print("FAIL:", failure)
        raise SystemExit(1)

    print(
        f"PASS: {len(document['vectors'])} "
        "Asterion-256 known-answer vectors"
    )


if __name__ == "__main__":
    main()
