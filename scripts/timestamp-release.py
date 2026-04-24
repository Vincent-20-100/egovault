#!/usr/bin/env python3
"""Timestamp a version tag via OpenTimestamps calendar servers.

Pure Python, no external dependencies. Works on Windows, Mac, Linux.
Usage: python scripts/timestamp-release.py v0.3.0
"""

import hashlib
import os
import re
import subprocess
import sys
import urllib.request

HEADER_MAGIC = bytes.fromhex(
    "004f70656e54696d657374616d7073000050726f6f6600bf89e2e884e89294"
)
MAJOR_VERSION = b"\x01"
OP_SHA256 = b"\x08"
OP_APPEND = b"\xf0"

CALENDARS = [
    "https://a.pool.opentimestamps.org",
    "https://b.pool.opentimestamps.org",
    "https://a.pool.eternitywall.com",
]

TIMESTAMP_DIR = ".timestamps"


def _varint(n: int) -> bytes:
    buf = []
    while n > 0x7F:
        buf.append((n & 0x7F) | 0x80)
        n >>= 7
    buf.append(n)
    return bytes(buf)


def _submit(digest: bytes, calendar_url: str) -> bytes:
    req = urllib.request.Request(
        f"{calendar_url}/digest",
        data=digest,
        headers={
            "Accept": "application/vnd.opentimestamps.v1",
            "Content-Type": "application/octet-stream",
            "User-Agent": "egovault-ots/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read(10_000)


def _build_ots(file_hash: bytes, nonce: bytes, calendar_proof: bytes) -> bytes:
    return b"".join([
        HEADER_MAGIC,
        MAJOR_VERSION,
        OP_SHA256,
        file_hash,
        OP_APPEND,
        _varint(len(nonce)),
        nonce,
        OP_SHA256,
        calendar_proof,
    ])


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <tag>", file=sys.stderr)
        return 1

    tag = sys.argv[1]

    if not re.match(r"^v\d+\.\d+\.0$", tag):
        print(f"ERROR: only v0.X.0 tags are timestamped (got {tag})", file=sys.stderr)
        return 1

    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", tag], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        print(f"ERROR: tag {tag} does not exist", file=sys.stderr)
        return 1

    os.makedirs(TIMESTAMP_DIR, exist_ok=True)
    ots_path = os.path.join(TIMESTAMP_DIR, f"{tag}.ots")
    hash_path = os.path.join(TIMESTAMP_DIR, f"{tag}.hash")

    if os.path.isfile(ots_path):
        print(f"{tag} already timestamped")
        return 0

    with open(hash_path, "wb") as f:
        f.write(commit_hash.encode("ascii"))

    file_hash = hashlib.sha256(commit_hash.encode("ascii")).digest()
    nonce = os.urandom(16)
    commitment = hashlib.sha256(file_hash + nonce).digest()

    calendar_proof = None
    calendar_used = None
    for url in CALENDARS:
        try:
            calendar_proof = _submit(commitment, url)
            calendar_used = url
            break
        except Exception as e:
            print(f"  calendar {url} failed: {e}", file=sys.stderr)

    if calendar_proof is None:
        print("ERROR: all calendar servers unreachable", file=sys.stderr)
        return 1

    ots_bytes = _build_ots(file_hash, nonce, calendar_proof)
    with open(ots_path, "wb") as f:
        f.write(ots_bytes)

    print(f"[OTS] Timestamped {tag} ({commit_hash})")
    print(f"      Calendar: {calendar_used}")
    print(f"      Proof:    {ots_path}")
    print()
    print("Next steps:")
    print(f"  git add {TIMESTAMP_DIR}/ && git commit -m 'chore: add OTS proof for {tag}'")
    print("  Wait 1-2 hours, then verify at https://opentimestamps.org")
    return 0


if __name__ == "__main__":
    sys.exit(main())
