"""
Source finalization tool.

Input  : source uid
Output : FinalizeResult
Marks source as vaulted, moves media to permanent storage.
"""

import shutil
from pathlib import Path

from core.context import VaultContext
from core.schemas import FinalizeResult
from core.logging import loggable
from core.errors import NotFoundError


@loggable("finalize_source")
def finalize_source(source_uid: str, ctx: VaultContext) -> FinalizeResult:
    """
    Mark source as vaulted and archive its media file.
    - Updates sources.status to 'vaulted'
    - Moves media file from staging to permanent media/ directory
    """
    source = ctx.db.get_source(source_uid)
    if source is None:
        raise NotFoundError("Source", source_uid)

    media_moved_to = None
    if source.media_path:
        src_file = Path(source.media_path)
        if src_file.exists():
            dest_dir = ctx.media_path / source.slug
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / src_file.name
            shutil.move(str(src_file), str(dest_file))
            media_moved_to = str(dest_file)

    ctx.db.update_source_status(source_uid, "vaulted")

    return FinalizeResult(
        source_uid=source_uid,
        new_status="vaulted",
        media_moved_to=media_moved_to,
    )
