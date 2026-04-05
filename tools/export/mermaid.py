"""
Mermaid diagram export tool.

Input  : note_uid (graph centered on one note) OR tag (all notes sharing a tag)
Output : ExportResult (path to .md file with Mermaid diagram)
No DB write.
"""

from core.context import VaultContext
from core.schemas import ExportResult
from core.logging import loggable


@loggable("export_mermaid")
def export_mermaid(
    ctx: VaultContext,
    note_uid: str | None = None,
    tag: str | None = None,
) -> ExportResult:
    """
    Export note relationships to a Mermaid graph diagram (.md file).
    note_uid: graph centered on one note (shows notes sharing its tags).
    tag: graph of all notes sharing a tag.
    No DB write.
    """
    if note_uid is None and tag is None:
        raise ValueError("Must provide either note_uid or tag")

    # Delegate query to VaultDB — returns nodes + optional pivot_slug
    graph = ctx.db.get_graph_data(note_uid=note_uid, tag=tag)

    if note_uid:
        filename = f"graph-note-{note_uid[:8]}.md"
    else:
        filename = f"graph-tag-{tag}.md"

    diagram = _build_diagram(graph["nodes"], pivot_slug=graph["pivot_slug"])

    output_dir = ctx.media_path / "graphs"
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
