"""Entry point for /tech-watch: sweep mode (no args) or deep mode (URL arg).

Usage:
    uv run python -m scripts.tech_watch                    # sweep
    uv run python -m scripts.tech_watch --deep             # sweep, deep budgets
    uv run python -m scripts.tech_watch --refresh-themes   # sweep, re-bootstrap
    uv run python -m scripts.tech_watch <url> [--angle X]  # deep analysis of one repo

Sweep mode emits a JSON RunReport. Deep mode emits a JSON fingerprint+tree.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def _is_url(value: str) -> bool:
    return value.startswith(("http://", "https://", "git@"))


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="tech-watch",
        description="/tech-watch — unified tech-watch (sweep + deep modes)",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Repo URL for deep mode. Omit for sweep mode.",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Sweep mode: wider fetch budgets for quarterly SOTA survey",
    )
    parser.add_argument(
        "--refresh-themes",
        action="store_true",
        help="Sweep mode: force re-bootstrap of research-themes.yaml",
    )
    parser.add_argument(
        "--angle",
        default="general",
        help="Deep mode: optional analysis angle hint",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Sweep mode: project root (default: cwd)",
    )
    args = parser.parse_args()

    if args.target and _is_url(args.target):
        from .deep import run_deep

        return run_deep(url=args.target, angle=args.angle)

    if args.refresh_themes:
        print('{"action": "refresh_themes"}')
        return 0

    from .sweep.core import run

    mode = "deep" if args.deep else "normal"
    report = run(mode=mode, project_dir=args.project_dir)
    print(report.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
