from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _generate_jwk() -> dict[str, str]:
    key = Ed25519PrivateKey.generate()
    private_bytes = key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "kid": "local-dev",
        "d": _b64url(private_bytes),
        "x": _b64url(public_bytes),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a stable local-only Ed25519 JWT signing JWK.")
    parser.add_argument("--out", default=".local-jwt-signing-private.jwk.json")
    args = parser.parse_args()

    output = Path(args.out)
    if output.exists():
        print(f"ok: {output} already exists")
        return
    output.write_text(json.dumps(_generate_jwk(), indent=2, sort_keys=True) + "\n")
    output.chmod(0o600)
    print(f"ok: created {output}")


if __name__ == "__main__":
    main()
