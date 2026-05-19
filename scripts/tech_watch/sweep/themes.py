from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .sources.base import Item

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


@dataclass
class Theme:
    name: str
    keywords: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=lambda: ["github", "hf", "rss", "reddit"])
    weight: float = 1.0


@dataclass
class ThemesConfig:
    default_theme: str
    max_new_per_source: int = 5
    max_new_per_theme: int = 15
    themes: list[Theme] = field(default_factory=list)


def load_themes(path: Path) -> ThemesConfig:
    """Load themes from a YAML file. Returns a minimal default if file missing."""
    if not path.exists():
        return ThemesConfig(default_theme="general")

    if yaml is None:
        raise ImportError("PyYAML not available — cannot load themes")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    themes = [
        Theme(
            name=t["name"],
            keywords=t.get("keywords", []),
            negative_keywords=t.get("negative_keywords", []),
            sources=t.get("sources", ["github", "hf", "rss", "reddit"]),
            weight=float(t.get("weight", 1.0)),
        )
        for t in raw.get("themes", [])
    ]
    return ThemesConfig(
        default_theme=raw.get("default_theme", "general"),
        max_new_per_source=int(raw.get("max_new_per_source", 5)),
        max_new_per_theme=int(raw.get("max_new_per_theme", 15)),
        themes=themes,
    )


def save_themes(config: ThemesConfig, path: Path) -> None:
    """Write themes config to YAML."""
    if yaml is None:
        raise ImportError("PyYAML not available — cannot save themes")

    data = {
        "default_theme": config.default_theme,
        "max_new_per_source": config.max_new_per_source,
        "max_new_per_theme": config.max_new_per_theme,
        "themes": [
            {
                "name": t.name,
                "keywords": t.keywords,
                "negative_keywords": t.negative_keywords,
                "sources": t.sources,
                "weight": t.weight,
            }
            for t in config.themes
        ],
    }
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def score_item(item: Item, theme: Theme) -> float:
    """Score an item against a theme using substring matching.

    Returns a weighted score >= 0. Negative keywords eliminate the item (return -1).
    Score >= 1.0 means the item passes the threshold.
    """
    text = (item.title + " " + item.pitch).lower()

    # Negative keywords hard-exclude
    for neg in theme.negative_keywords:
        if neg.lower() in text:
            return -1.0

    # Count positive keyword hits
    hits = sum(1 for kw in theme.keywords if kw.lower() in text)
    if hits == 0:
        return 0.0

    return hits * theme.weight


def filter_items(
    items: list[Item],
    themes: list[Theme],
    threshold: float = 1.0,
) -> dict[str, list[Item]]:
    """Filter and assign items to themes.

    Returns a dict {theme_name: [items]} where each item scored >= threshold.
    An item can appear in multiple themes.
    """
    result: dict[str, list[Item]] = {t.name: [] for t in themes}
    for item in items:
        for theme in themes:
            s = score_item(item, theme)
            if s >= threshold:
                result[theme.name].append(item)
    return result
