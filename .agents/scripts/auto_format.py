"""Post-Tool Hook for Automatic Python Formatting & Lint Fixes.

Automatically runs `uv run ruff format` and `uv run ruff check --fix`
whenever a Python file is written or edited.
"""

import json
import os
import subprocess
import sys


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({}))
            return

        payload = json.loads(raw_input)
        tool_call = payload.get("toolCall", {})
        args = tool_call.get("args", {})
        target_file = (
            args.get("TargetFile")
            or args.get("AbsolutePath")
            or args.get("file_path")
            or args.get("path")
        )

        if target_file and str(target_file).endswith(".py") and os.path.exists(target_file):
            subprocess.run(
                ["uv", "run", "ruff", "format", target_file],
                capture_output=True,
                timeout=10,
                check=False,
            )
            subprocess.run(
                ["uv", "run", "ruff", "check", target_file, "--fix"],
                capture_output=True,
                timeout=10,
                check=False,
            )

    except Exception:
        pass  # Never block execution if formatter fails or is unavailable

    # PostToolUse must return an empty JSON object
    print(json.dumps({}))


if __name__ == "__main__":
    main()
