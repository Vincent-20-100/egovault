#!/usr/bin/env python3
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


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    cmd: str = data.get("tool_input", {}).get("command", "")
    if not re.search(r"\bgit\b.*\bcommit\b", cmd):
        return 0
    name = git_identity("user.name")
    email = git_identity("user.email")
    if not name or not email:
        return 0
    cmd_final = f"{strip_author_flag(cmd).rstrip()} --author='{name} <{email}>'"
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": {"command": cmd_final}}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
