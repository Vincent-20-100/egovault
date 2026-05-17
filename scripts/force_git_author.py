#!/usr/bin/env python3
"""PreToolUse(Bash) hook: force git commits to use the configured git identity.

Inserts `--author='Name <email>'` directly after the `commit` keyword of the
commit segment — NOT at the end of the whole command — so compound commands
like `git commit -m x && git status` do not get `--author` appended to the
last (non-commit) segment.
"""
from __future__ import annotations
import json, re, subprocess, sys


def git_identity(key: str) -> str:
    try:
        return subprocess.check_output(["git", "config", key], text=True).strip()
    except subprocess.CalledProcessError:
        return ""


def strip_author_flag(cmd: str) -> str:
    cmd = re.sub(r"\s+--author=['\"]?[^'\"\s][^'\"]*['\"]?", "", cmd)
    cmd = re.sub(r"\s+--author='[^']*'", "", cmd)
    cmd = re.sub(r'\s+--author="[^"]*"', "", cmd)
    return cmd


def rewrite_command(cmd: str, name: str, email: str) -> str | None:
    """Return the rewritten command, or None if it must not be rewritten.

    None when: not a `git ... commit`, or the git identity is missing.
    The `--author` flag is inserted right after the `commit` keyword of the
    commit segment (bounded by shell separators &, |, ;) so it cannot leak
    onto a different chained command.
    """
    if not re.search(r"\bgit\b.*\bcommit\b", cmd):
        return None
    if not name or not email:
        return None
    stripped = strip_author_flag(cmd)
    author = f"--author='{name} <{email}>'"
    return re.sub(
        r"(\bgit\b[^&|;]*?\bcommit\b)",
        rf"\1 {author}",
        stripped,
        count=1,
    )


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    cmd: str = data.get("tool_input", {}).get("command", "")
    cmd_final = rewrite_command(cmd, git_identity("user.name"), git_identity("user.email"))
    if cmd_final is None:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": {"command": cmd_final},
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
