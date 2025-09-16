#!/usr/bin/env python3
"""
Generate API auth secrets for CI/CD and Kubernetes.

Outputs values to populate GitHub Secrets (and optionally YAML/env snippets):
  - API_TOKEN_PEPPER: high-entropy random string
  - ADMIN_API_TOKENS_HASHED: comma-separated sha256(pepper + token) for admin tokens
  - ADMIN_API_TOKENS: optionally generate and print plaintext admin tokens

Usage examples:
  # Provide admin tokens as a JSON array; generate a new pepper
  python scripts/generate_api_admin_secrets.py --tokens '["tokA","tokB"]'

  # Read tokens from a file (one per line) and output YAML snippet
  python scripts/generate_api_admin_secrets.py --tokens-file tokens.txt --format yaml

  # Use an existing pepper (do not generate)
  python scripts/generate_api_admin_secrets.py --tokens-file tokens.txt --pepper "$EXISTING"

  # Generate 2 fresh admin tokens and a pepper; print everything as env
  python scripts/generate_api_admin_secrets.py --generate 2 --format env

Notes:
  - By default, the script does NOT echo plaintext admin tokens to stdout.
    Use --echo-tokens if you explicitly want to print them (not recommended).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import secrets
from typing import Iterable, List, Tuple


def generate_pepper(bytes_len: int = 48) -> str:
    """Return a high-entropy, URL-safe base64 string (~64 chars).

    48 random bytes → base64url without padding ≈ 64 characters.
    """
    raw = os.urandom(int(bytes_len))
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def parse_tokens(
    tokens_arg: str | None,
    tokens_file: str | None,
    multi_tokens: Iterable[str],
    *,
    generate: int | None = None,
    token_bytes: int = 32,
) -> List[str]:
    """Parse admin tokens from JSON array, newline-delimited file, comma list, or repeats.

    Priority order:
      1) --tokens-file (one token per line; empty lines ignored)
      2) --tokens (JSON array preferred; then newline- or comma-separated)
      3) repeated --token values
    """
    # 0) Generate N tokens if requested
    if generate and int(generate) > 0:
        n = int(generate)
        return [secrets.token_urlsafe(int(token_bytes)) for _ in range(n)]

    # 1) File wins if provided
    if tokens_file:
        with open(tokens_file, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.readlines()]
        return [t for t in lines if t]

    # 2) Single tokens_arg
    if tokens_arg:
        s = tokens_arg.strip()
        # Prefer JSON array
        try:
            data = json.loads(s)
            if isinstance(data, list):
                return [str(x) for x in data if str(x)]
            if isinstance(data, str) and data:
                return [data]
        except Exception:
            pass
        # Fallbacks: newline then comma
        parts = [p.strip() for p in s.splitlines() if p.strip()]
        if parts:
            return parts
        return [p.strip() for p in s.split(",") if p.strip()]

    # 3) Repeated --token flags
    toks = [t.strip() for t in (multi_tokens or []) if t and t.strip()]
    return toks


def hash_admin_tokens(pepper: str, tokens: Iterable[str]) -> List[str]:
    """sha256(pepper + token) for each provided token; hex digests."""
    out: List[str] = []
    for t in tokens:
        h = hashlib.sha256((pepper + t).encode("utf-8")).hexdigest()
        out.append(h)
    return out


def format_output(fmt: str, pepper: str, hashed_csv: str, *, echo_tokens: List[str] | None = None) -> str:
    """Render output in env, yaml, or json formats."""
    fmt = (fmt or "env").lower()
    if fmt == "yaml":
        lines = [
            f"API_TOKEN_PEPPER: \"{pepper}\"",
            f"ADMIN_API_TOKENS_HASHED: \"{hashed_csv}\"",
        ]
        if echo_tokens:
            lines.append("# ADMIN_API_TOKENS (plaintext) — handle with care")
            if len(echo_tokens) == 1:
                lines.append(f"# {echo_tokens[0]}")
            else:
                lines.extend([f"# - {t}" for t in echo_tokens])
        return "\n".join(lines) + "\n"

    if fmt == "json":
        payload = {
            "API_TOKEN_PEPPER": pepper,
            "ADMIN_API_TOKENS_HASHED": hashed_csv,
        }
        if echo_tokens:
            payload["ADMIN_API_TOKENS"] = echo_tokens if len(echo_tokens) > 1 else echo_tokens[0]
        return json.dumps(payload, ensure_ascii=False) + "\n"

    # default: env
    lines = [
        f"API_TOKEN_PEPPER={pepper}",
        f"ADMIN_API_TOKENS_HASHED={hashed_csv}",
    ]
    if echo_tokens:
        if len(echo_tokens) == 1:
            lines.append(f"ADMIN_API_TOKENS={echo_tokens[0]}")
        else:
            # newline-delimited is safer for secrets UIs that accept it
            joined = "\\n".join(echo_tokens)
            lines.append(f"ADMIN_API_TOKENS={joined}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate API_TOKEN_PEPPER and ADMIN_API_TOKENS_HASHED")
    src = ap.add_mutually_exclusive_group(required=False)
    src.add_argument("--tokens", help="Admin tokens input (JSON array preferred; or comma/newline separated)")
    src.add_argument("--tokens-file", help="Path to file with admin tokens, one per line")
    src.add_argument("--generate", type=int, help="Generate N fresh admin tokens (plaintext) with high entropy")
    ap.add_argument("--token", action="append", default=[], help="Repeatable flag for providing admin tokens individually")
    ap.add_argument("--pepper", help="Use an existing pepper instead of generating a new one")
    ap.add_argument("--format", choices=["env", "yaml", "json"], default="env", help="Output format")
    ap.add_argument("--echo-tokens", action="store_true", help="Also print ADMIN_API_TOKENS (plaintext). Use with caution.")
    ap.add_argument("--token-bytes", type=int, default=32, help="Entropy (bytes) for generated admin tokens; default 32")

    args = ap.parse_args(argv)

    tokens = parse_tokens(
        args.tokens,
        args.tokens_file,
        args.token,
        generate=args.generate,
        token_bytes=args.token_bytes,
    )
    if not tokens:
        print("ERROR: No admin tokens provided. Use --tokens, --tokens-file, or --token.", file=sys.stderr)
        return 2

    pepper = args.pepper or generate_pepper()
    hashed = hash_admin_tokens(pepper, tokens)
    hashed_csv = ",".join(hashed)

    # If tokens were generated, echo by default unless user suppressed
    echo = tokens if (args.echo_tokens or args.generate) else None
    sys.stdout.write(format_output(args.format, pepper, hashed_csv, echo_tokens=echo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
