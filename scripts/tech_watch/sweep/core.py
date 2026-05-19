from __future__ import annotations

import logging
from pathlib import Path

from .cards import append_mention, find_card_by_url, write_new_card
from .dedup import canonicalize, is_known
from .index import regenerate_index
from .report import RunReport, SourceResult
from .sources.base import Item, Source
from .sources.github import GitHubSource
from .sources.huggingface import HuggingFaceSource
from .sources.reddit import RedditSource
from .sources.rss import RSSSource
from .themes import ThemesConfig, filter_items, load_themes

logger = logging.getLogger(__name__)

# Default RSS feeds shipped with the template (overridable via themes yaml)
DEFAULT_RSS_FEEDS = [
    "https://hnrss.org/frontpage",
    "https://www.reddit.com/r/MachineLearning/hot/.rss",
    "https://www.reddit.com/r/LocalLLaMA/hot/.rss",
    "https://simonwillison.net/atom/everything/",
]

DEFAULT_SUBREDDITS = ["MachineLearning", "LocalLLaMA", "artificial"]


def build_sources(config: ThemesConfig) -> list[Source]:
    """Build the list of active sources for a run."""
    active_source_names = set()
    for theme in config.themes:
        active_source_names.update(theme.sources)

    sources: list[Source] = []
    if "github" in active_source_names:
        sources.append(GitHubSource())
    if "hf" in active_source_names:
        sources.append(HuggingFaceSource())
    if "rss" in active_source_names:
        for url in DEFAULT_RSS_FEEDS:
            if "reddit.com" not in url:
                sources.append(RSSSource(url))
    if "reddit" in active_source_names:
        sources.append(RedditSource(DEFAULT_SUBREDDITS))
    return sources


def run(
    mode: str = "normal",
    project_dir: Path | None = None,
) -> RunReport:
    """Main /tech-watch run: fetch → dedup → score → rank → write → index.

    Args:
        mode: "normal" for top-K veille, "deep" for wider budgets.
        project_dir: root of the generated project (default: cwd).

    Returns:
        RunReport serializable to JSON for the skill to present.
    """
    if project_dir is None:
        project_dir = Path.cwd()

    themes_path = project_dir / ".meta" / "research-themes.yaml"
    research_dir = project_dir / ".meta" / "references" / "research"
    index_path = research_dir / "INDEX.md"

    config = load_themes(themes_path)
    if not config.themes:
        logger.warning("No themes configured. Create %s first.", themes_path)
        return RunReport(mode=mode)

    limit_per_source = 30 if mode == "deep" else 15
    top_k = config.max_new_per_theme * (2 if mode == "deep" else 1)

    report = RunReport(mode=mode)
    all_new_items: list[Item] = []

    # --- Fetch phase ---
    sources = build_sources(config)
    for source in sources:
        issues = source.check()
        if issues:
            logger.warning("Source %s not ready: %s", source.__class__.__name__, issues)
            report.sources.append(
                SourceResult(
                    source_name=source.__class__.__name__,
                    fetched=0,
                    new=0,
                    known=0,
                    failed=True,
                    error="; ".join(issues),
                )
            )
            continue

        # Fetch with each theme's keywords as queries
        items: list[Item] = []
        for theme in config.themes:
            if source.__class__.__name__.lower().replace("source", "") not in [
                s.lower() for s in theme.sources
            ] and not any(s in source.__class__.__name__.lower() for s in theme.sources):
                continue
            query = " ".join(theme.keywords[:3])  # use top 3 keywords
            fetched = source.fetch(query=query, limit=limit_per_source)
            items.extend(fetched)

        # Dedup seen URLs within this batch
        seen_urls: set[str] = set()
        unique_items: list[Item] = []
        for item in items:
            canonical = canonicalize(item.url, item.source_name)
            if canonical not in seen_urls:
                seen_urls.add(canonical)
                unique_items.append(item)

        # Partition known / new
        source_new = 0
        source_known = 0
        for item in unique_items:
            canonical = canonicalize(item.url, item.source_name)
            if is_known(canonical, index_path):
                # Append mention to existing card
                card = find_card_by_url(canonical, research_dir)
                if card:
                    append_mention(card, item)
                source_known += 1
            else:
                all_new_items.append(item)
                source_new += 1

        report.sources.append(
            SourceResult(
                source_name=source.__class__.__name__,
                fetched=len(unique_items),
                new=source_new,
                known=source_known,
            )
        )

    # --- Score + filter + rank phase ---
    themed = filter_items(all_new_items, config.themes)
    discarded = 0

    for theme_name, items in themed.items():
        if not items:
            logger.info("No new items for theme %s", theme_name)
            continue

        # Rank by native score desc, take top K
        ranked = sorted(items, key=lambda i: i.score_raw, reverse=True)
        top = ranked[:top_k]
        discarded += len(ranked) - len(top)

        # Write new cards
        research_dir.mkdir(parents=True, exist_ok=True)
        top_dicts = []
        for item in top:
            card_path = write_new_card(item, theme_name, research_dir)
            top_dicts.append(
                {
                    "title": item.title,
                    "url": item.url,
                    "source": item.source_name,
                    "score": item.score_raw,
                    "card_path": str(card_path),
                }
            )
        report.top_items_per_theme[theme_name] = top_dicts

    report.discarded_count = discarded

    # --- Promotion candidates (mentions_count newly >= 3) ---
    cards_dir = research_dir / "cards"
    if cards_dir.exists():
        from .cards import _parse_frontmatter  # local import to avoid circular

        for card_path in cards_dir.rglob("*.md"):
            text = card_path.read_text(encoding="utf-8")
            meta, _ = _parse_frontmatter(text)
            if (
                int(meta.get("mentions_count", "0")) >= 3
                and meta.get("has_synthesis", "false") == "false"
            ):
                report.promotion_candidates.append(str(card_path))

    # --- Regenerate index ---
    regenerate_index(research_dir)

    return report
