from __future__ import annotations

import re
from pathlib import Path

from .sources.base import Item

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from a markdown file. Returns (meta, body)."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ": " in line:
            key, _, value = line.partition(": ")
            meta[key.strip()] = value.strip()
    body = text[match.end() :]
    return meta, body


def _render_frontmatter(meta: dict[str, str]) -> str:
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def write_new_card(item: Item, theme: str, research_dir: Path) -> Path:
    """Write a new card file and return its path.

    Creates: research_dir/cards/<theme>/<source>-<slug>.md
    """
    cards_dir = research_dir / "cards" / theme
    cards_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(item.title)
    filename = f"{item.source_name}-{slug}.md"
    card_path = cards_dir / filename

    # Avoid clobbering an existing card with the same slug
    if card_path.exists():
        filename = f"{item.source_name}-{slug}-{item.discovered.strftime('%Y%m%d')}.md"
        card_path = cards_dir / filename

    today_str = item.discovered.isoformat()
    content = (
        f"---\n"
        f"source: {item.source_name}\n"
        f"source_url: {item.url}\n"
        f"title: {item.title}\n"
        f"pitch: {item.pitch[:120]}\n"
        f"tier: card\n"
        f"discovered: {today_str}\n"
        f"mentions_count: 1\n"
        f"tags: []\n"
        f"themes: [{theme}]\n"
        f"has_synthesis: false\n"
        f"---\n"
        f"## Pitch\n\n{item.pitch}\n\n"
        f"## Why it's relevant\n\n_To be filled._\n\n"
        f"## Mentions\n\n"
        f"- {today_str} — {item.source_name} (score: {item.score_raw:.0f})\n\n"
        f"## Links\n\n- {item.url}\n"
    )
    card_path.write_text(content, encoding="utf-8")
    return card_path


def append_mention(card_path: Path, item: Item) -> None:
    """Append a mention to an existing card and increment mentions_count."""
    text = card_path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)

    # Increment mentions_count
    count = int(meta.get("mentions_count", "1")) + 1
    meta["mentions_count"] = str(count)

    # Append mention line under ## Mentions section
    today_str = item.discovered.isoformat()
    mention_line = f"- {today_str} — {item.source_name} (score: {item.score_raw:.0f})\n"

    if "## Mentions" in body:
        body = body.replace(
            "## Mentions\n",
            f"## Mentions\n{mention_line}",
            1,
        )
    else:
        body += f"\n## Mentions\n\n{mention_line}"

    card_path.write_text(_render_frontmatter(meta) + body, encoding="utf-8")


def _slugify(text: str) -> str:
    """Convert text to a url-safe slug, max 50 chars."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text[:50]


def find_card_by_url(canonical_url: str, research_dir: Path) -> Path | None:
    """Find an existing card whose source_url matches canonical_url."""
    cards_dir = research_dir / "cards"
    if not cards_dir.exists():
        return None
    for card_path in cards_dir.rglob("*.md"):
        text = card_path.read_text(encoding="utf-8")
        meta, _ = _parse_frontmatter(text)
        if meta.get("source_url") == canonical_url:
            return card_path
    return None
