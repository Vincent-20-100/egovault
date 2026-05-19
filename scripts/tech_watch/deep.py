"""Deep mode for /tech-watch: clone + fingerprint + tree for one repo.

Emits a single JSON document on stdout. The LLM consumes this JSON and writes
the tiered audit card. All the deterministic work lives here; analysis and
narrative stay with the skill.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}
LANG_EXTENSIONS = {
    ".py": "Python",
    ".rs": "Rust",
    ".go": "Go",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++",
    ".cs": "C#",
    ".swift": "Swift",
    ".md": "Markdown",
    ".sh": "Shell",
    ".lua": "Lua",
    ".php": "PHP",
}


def slugify(url: str) -> str:
    name = url.rstrip("/").split("/")[-1]
    name = re.sub(r"\.git$", "", name)
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")


def parse_owner_repo(url: str) -> tuple[str, str] | None:
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not match:
        return None
    return match.group(1), match.group(2)


def clone(url: str, dest: Path) -> None:
    subprocess.run(
        ["git", "clone", "--depth=1", "--filter=blob:none", url, str(dest)],
        check=True,
        capture_output=True,
        text=True,
    )


def walk_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            files.append(path)
    return files


def detect_primary_language(files: list[Path]) -> str:
    counts: Counter[str] = Counter()
    for f in files:
        lang = LANG_EXTENSIONS.get(f.suffix.lower())
        if lang and lang != "Markdown":
            counts[lang] += 1
    return counts.most_common(1)[0][0] if counts else "unknown"


def detect_repo_type(root: Path) -> str:
    signals: list[tuple[str, str]] = [
        (".claude/skills", "agentic"),
        ("copier.yml", "template"),
        ("cookiecutter.json", "template"),
        ("Cargo.toml", "library_or_app"),
        ("pyproject.toml", "library_or_app"),
        ("package.json", "library_or_app"),
        ("Dockerfile", "app"),
        ("docker-compose.yml", "app"),
    ]
    detected = [label for marker, label in signals if (root / marker).exists()]
    if any((f.suffix == ".ipynb") for f in root.rglob("*.ipynb")):
        detected.append("research")
    if not detected:
        return "other"
    return "/".join(dict.fromkeys(detected))


def read_license(root: Path) -> str:
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
        path = root / name
        if path.exists():
            first_line = path.read_text(encoding="utf-8", errors="replace").splitlines()
            return first_line[0].strip() if first_line else "present"
    return "none"


def read_pitch(root: Path) -> str:
    readme = next(
        (p for p in root.iterdir() if p.name.lower().startswith("readme")),
        None,
    )
    if not readme or not readme.is_file():
        return ""
    lines = readme.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("!["):
            continue
        return stripped[:240]
    return ""


def gh_metadata(owner: str, repo: str) -> dict[str, str | int]:
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"stars": "unknown", "last_commit": "unknown"}
    data = json.loads(result.stdout)
    return {
        "stars": data.get("stargazers_count", "unknown"),
        "last_commit": data.get("pushed_at", "unknown"),
    }


def build_tree(root: Path, max_depth: int = 2) -> str:
    lines: list[str] = [root.name + "/"]

    def recurse(current: Path, depth: int, prefix: str) -> None:
        if depth > max_depth:
            return
        entries = sorted(
            [p for p in current.iterdir() if p.name not in SKIP_DIRS],
            key=lambda p: (not p.is_dir(), p.name),
        )
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            branch = "└── " if is_last else "├── "
            lines.append(f"{prefix}{branch}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir():
                extension = "    " if is_last else "│   "
                recurse(entry, depth + 1, prefix + extension)

    recurse(root, 1, "")
    return "\n".join(lines)


def fingerprint_repo(root: Path, url: str) -> dict[str, object]:
    files = walk_files(root)
    fp: dict[str, object] = {
        "primary_lang": detect_primary_language(files),
        "repo_type": detect_repo_type(root),
        "file_count": len(files),
        "license": read_license(root),
        "pitch": read_pitch(root),
    }
    owner_repo = parse_owner_repo(url)
    if owner_repo:
        fp.update(gh_metadata(*owner_repo))
    else:
        fp.update({"stars": "unknown", "last_commit": "unknown"})
    return fp


def run_deep(url: str, angle: str = "general") -> int:
    slug = slugify(url)
    tmp_root = Path(tempfile.gettempdir()) / f"tech-watch-deep-{slug}"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)

    try:
        clone(url, tmp_root)
    except subprocess.CalledProcessError as exc:
        payload = {
            "mode": "deep",
            "slug": slug,
            "url": url,
            "angle": angle,
            "error": "clone_failed",
            "stderr": (exc.stderr or "").strip(),
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 1

    try:
        fingerprint = fingerprint_repo(tmp_root, url)
        tree_output = build_tree(tmp_root, max_depth=2)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    payload = {
        "mode": "deep",
        "slug": slug,
        "url": url,
        "angle": angle,
        "fingerprint": fingerprint,
        "tree_output": tree_output,
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0
