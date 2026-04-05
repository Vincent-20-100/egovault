"""
Mermaid diagram export tool.

Input  : note_uid (graph centered on one note) OR tag (all notes sharing a tag)
Output : ExportResult (path to .md file with Mermaid diagram)
No DB write.
"""

from pathlib import Path

from core.schemas import ExportResult
from core.config import Settings
from core.logging import loggable


@loggable("export_mermaid")
def export_mermaid(
    settings: Settings,
    note_uid: str | None = None,
    tag: str | None = None,
) -> ExportResult:
    """
    Export note relationships to a Mermaid graph diagram (.md file).
    note_uid: graph centered on one note (shows notes sharing its tags).
    tag: graph of all notes sharing a tag.
    No DB write.
    """
    from infrastructure.db import get_vault_connection

    if note_uid is None and tag is None:
        raise ValueError("Must provide either note_uid or tag")

    conn = get_vault_connection(settings.vault_db_path)

    if note_uid:
        # Find all notes sharing at least one tag with the pivot note
        rows = conn.execute(
            """
            SELECT DISTINCT n.uid, n.slug, n.title
            FROM notes n
            JOIN note_tags nt ON nt.note_uid = n.uid
            JOIN tags t ON t.uid = nt.tag_uid
            WHERE t.uid IN (
                SELECT tag_uid FROM note_tags WHERE note_uid = ?
            )
            """,
            (note_uid,),
        ).fetchall()
        pivot = conn.execute(
            "SELECT slug, title FROM notes WHERE uid = ?", (note_uid,)
        ).fetchone()
        conn.close()
        filename = f"graph-note-{note_uid[:8]}.md"
        diagram = _build_diagram(rows, pivot_slug=pivot["slug"] if pivot else None)
    else:
        rows = conn.execute(
            """
            SELECT DISTINCT n.uid, n.slug, n.title
            FROM notes n
            JOIN note_tags nt ON nt.note_uid = n.uid
            JOIN tags t ON t.uid = nt.tag_uid
            WHERE t.name = ?
            """,
            (tag,),
        ).fetchall()
        conn.close()
        filename = f"graph-tag-{tag}.md"
        diagram = _build_diagram(rows)

    output_dir = settings.media_path / "graphs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    output_path.write_text(diagram, encoding="utf-8")

    return ExportResult(output_path=str(output_path), format="mermaid")


def _build_diagram(rows, pivot_slug: str | None = None) -> str:
    lines = ["```mermaid", "graph LR"]
    for row in rows:
        label = row["title"].replace('"', "'")
        style = ":::pivot" if row["slug"] == pivot_slug else ""
        lines.append(f'    {row["slug"]}["{label}"]{style}')
    lines.append("```")
    return "\n".join(lines)
