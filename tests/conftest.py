import pytest
from pathlib import Path


@pytest.fixture
def vault(tmp_path):
    """Crée un vault minimal pour les tests."""
    for folder in ["notes", "sources/raw-sources/_archive"]:
        (tmp_path / folder).mkdir(parents=True)
    return tmp_path


def make_note(vault, folder, filename, tags, date="2026-03-19", links=None):
    """Helper : crée une note avec frontmatter YAML valide."""
    links_section = ""
    if links:
        links_section = "\n## Liens\n" + "\n".join(f"- [[{l}]]" for l in links)
    content = f"""---
date_creation: {date}
date_modification: {date}
note_type: synthese
source_type: personnel
depth: note
tags: {tags}
---

> Docstring test.

# Titre test
{links_section}
"""
    (vault / folder / filename).write_text(content, encoding="utf-8")
