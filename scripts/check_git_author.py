#!/usr/bin/env python3
"""Pre-commit hook: blocks commits with a forbidden author identity."""
from __future__ import annotations
import os, subprocess, sys

FORBIDDEN = ["claude", "anthropic"]


def check_author() -> str | None:
    if os.environ.get("CI"):
        return None
    env_name = os.environ.get("GIT_AUTHOR_NAME", "").lower()
    if env_name and any(bad in env_name for bad in FORBIDDEN):
        return f"$GIT_AUTHOR_NAME='{env_name}' est interdit"
    try:
        ident = subprocess.check_output(["git", "var", "GIT_AUTHOR_IDENT"], text=True).strip()
    except subprocess.CalledProcessError:
        return None
    name = ident.split("<", 1)[0].strip().lower()
    if any(bad in name for bad in FORBIDDEN):
        return f"Auteur '{name}' est interdit — configure git config user.name"
    return None


def main() -> int:
    error = check_author()
    if error:
        print(f"[check-git-author] BLOQUÉ : {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
