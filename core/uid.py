"""
UUID4 generation and slug derivation for EgoVault v2.

Rules:
- uid: UUID4, system-generated, immutable after creation
- slug: kebab-case derived from title, stable but not a primary key
"""

import uuid
import unicodedata
import re


def generate_uid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def make_slug(title: str) -> str:
    """
    Derive a kebab-case slug from a title.

    Rules applied in order:
    1. Lowercase
    2. Strip accents (NFD normalization + ASCII encoding)
    3. Replace any character not in [a-z0-9] with a hyphen
    4. Collapse consecutive hyphens into one
    5. Strip leading and trailing hyphens
    6. Truncate to 80 characters, cutting at the last hyphen if mid-word
    """
    # 1. Lowercase
    slug = title.lower()
    # 2. Strip accents (NFD → ASCII)
    slug = unicodedata.normalize("NFD", slug)
    slug = slug.encode("ascii", "ignore").decode("ascii")
    # 3. Replace non-[a-z0-9] with hyphen (+ collapses consecutive via +)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # 4. Strip leading/trailing hyphens
    slug = slug.strip("-")
    # 5. Truncate to 80 chars, cut at last hyphen if mid-word
    if len(slug) > 80:
        slug = slug[:80]
        last_hyphen = slug.rfind("-")
        if last_hyphen > 0:
            slug = slug[:last_hyphen]
    return slug


def make_unique_slug(title: str, existing_slugs: set[str]) -> str:
    """
    Derive a slug that does not collide with existing ones.
    Appends -2, -3, etc. until unique. Never silently overwrites.
    """
    base = make_slug(title)
    if base not in existing_slugs:
        return base
    counter = 2
    while f"{base}-{counter}" in existing_slugs:
        counter += 1
    return f"{base}-{counter}"
