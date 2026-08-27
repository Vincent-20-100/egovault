"""Universal Security Gate Hook for AI Coding Agents.

Enforces:
1. DENY (Hard Block): Destructive commands (sudo, mkfs, dd, rm -rf, curl|sh),
   reading/writing secrets (~/.ssh, ~/.aws, ~/.gnupg, .env files, .git internals).
2. FORCE_ASK (Human Confirmation Required): git push, git reset --hard,
   heavy deletions, dropping database tables.
3. ALLOW (Automatic / Autonomous): Normal dev workflow (uv, pytest, ruff, python,
   git commit/add/diff/status, mkdir, mv, file edits, etc.).
"""

import json
import re
import sys

# Patterns that MUST BE DENIED outright (Never executed by agent)
DENY_COMMAND_PATTERNS = [
    r"\brm\s+-rf\s+(/|~|\.\.|[a-zA-Z]:|\*|/\*)",
    r"\brm\s+-rf\b",
    r"\bdel\s+/[sfaq]*\s+(\*|[a-zA-Z]:\\)",
    r"\b(rmdir|rd)\s+/[sq]\s+(\*|[a-zA-Z]:\\)",
    r"\bsudo\b",
    r"\bsu\s+",
    r"\bdd\s+if=",
    r"\bmkfs\b",
    r"\bformat\s+[a-zA-Z]:",
    r"\bchmod\s+-R\s+777",
    r"\bcurl\s+.*\|\s*(ba)?sh",
    r"\bwget\s+.*\|\s*(ba)?sh",
    r"\bgit\s+push\s+.*--force",
    r"\bgit\s+clean\s+-[xdf]+",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",  # forkbomb
]

# Paths/Files that MUST NEVER be read or edited (Secrets & VCS internals)
DENY_PATH_PATTERNS = [
    r"[/\\]\.ssh([/\\]|$)",
    r"[/\\]\.aws([/\\]|$)",
    r"[/\\]\.gnupg([/\\]|$)",
    r"[/\\]\.pypirc$",
    r"[/\\]\.netrc$",
    r"[/\\]id_rsa([._].*)?$",
    r"[/\\]id_ed25519([._].*)?$",
    r"(^|[/\\])\.env(\.[a-zA-Z0-9_-]+)?$",  # Matches .env, .env.local, but NOT .env.example
    r"[/\\]\.git[/\\](config|hooks|objects|refs)",
]

# Sensitive operations that REQUIRE EXPLICIT HUMAN APPROVAL (force_ask)
ASK_COMMAND_PATTERNS = [
    r"\bgit\s+push\b",
    r"\bgit\s+reset\s+--hard",
    r"\bgit\s+restore\s+\.",
    r"\bRemove-Item\b.*-Recurse.*-Force",
    r"\bdrop\s+(database|table|schema)\b",
]

KEY_MARKERS = [
    "-----" + "BEGIN OPENSSH PRIVATE KEY" + "-----",
    "-----" + "BEGIN RSA PRIVATE KEY" + "-----",
]


def check_path_denial(path: str) -> tuple[bool, str]:
    if not path:
        return False, ""
    # Allow .env.example explicitly
    if path.endswith(".env.example"):
        return False, ""
    for pattern in DENY_PATH_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return True, f"Access to secret/restricted path pattern '{pattern}' is forbidden."
    return False, ""


def check_command(cmd: str) -> dict:
    if not cmd:
        return {"decision": "allow"}

    # 1. Deny check
    for pattern in DENY_COMMAND_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return {
                "decision": "deny",
                "reason": f"Command blocked by security policy: matched dangerous pattern '{pattern}'",
            }

    # Deny secret paths referenced in command string
    denied, reason = check_path_denial(cmd)
    if denied:
        return {"decision": "deny", "reason": reason}

    # 2. Ask check (Explicit confirmation required)
    for pattern in ASK_COMMAND_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return {
                "decision": "force_ask",
                "reason": f"Confirmation required for sensitive operation: '{cmd}'",
            }

    # 3. Allow everything else
    return {"decision": "allow"}


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return

        payload = json.loads(raw_input)
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        # Check run_command (Antigravity) or bash (Claude)
        if tool_name in ("run_command", "bash", "Bash"):
            cmd = args.get("CommandLine") or args.get("command") or ""
            result = check_command(cmd)
            print(json.dumps(result))
            return

        # Check file read / write / edit tools
        file_path_keys = [
            "TargetFile",
            "AbsolutePath",
            "SearchPath",
            "DirectoryPath",
            "file_path",
            "path",
        ]
        for key in file_path_keys:
            if key in args:
                path = str(args[key])
                denied, reason = check_path_denial(path)
                if denied:
                    print(json.dumps({"decision": "deny", "reason": reason}))
                    return

        # Check code content for accidental hardcoded private keys being written
        if tool_name in ("write_to_file", "replace_file_content", "Edit", "Write"):
            content = (
                args.get("CodeContent", "")
                or args.get("ReplacementContent", "")
                or args.get("content", "")
            )
            for marker in KEY_MARKERS:
                if marker in content and not any(
                    k in content for k in ("KEY_MARKERS", "check_path_denial")
                ):
                    print(
                        json.dumps(
                            {
                                "decision": "deny",
                                "reason": "Writing unencrypted private SSH/RSA keys is strictly prohibited.",
                            }
                        )
                    )
                    return

        # Default: Allow autonomous execution
        print(json.dumps({"decision": "allow"}))

    except Exception as e:
        # Fallback to ask if unexpected error occurs
        print(json.dumps({"decision": "ask", "reason": f"Security hook check error: {e!s}"}))


if __name__ == "__main__":
    main()
