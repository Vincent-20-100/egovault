"""
Source finalization tool.

Input  : source uid
Output : FinalizeResult
Marks source as vaulted, moves media to permanent storage.
"""

import shutil
from pathlib import Path

from core.schemas import FinalizeResult
from core.config import Settings
from core.logging import loggable
from core.errors import NotFoundError


@loggable("finalize_source")
def finalize_source(source_uid: str, settings: Settings) -> FinalizeResult:
    """
    Mark source as vaulted and archive its media file.
    - Updates sources.status to 'vaulted'
    - Moves media file from staging to permanent media/ directory
    The associated note is resolved via: SELECT uid FROM notes WHERE source_uid = ?
    """
    from infrastructure.db import get_source, update_source_status

    source = get_source(settings.vault_db_path, source_uid)
    if source is None:
        raise NotFoundError("Source", source_uid)

    media_moved_to = None
    if source.media_path:
        src_file = Path(source.media_path)
        if src_file.exists():
            dest_dir = settings.media_path / source.slug
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / src_file.name
            shutil.move(str(src_file), str(dest_file))
            media_moved_to = str(dest_file)

    update_source_status(settings.vault_db_path, source_uid, "vaulted")

    return FinalizeResult(
        source_uid=source_uid,
        new_status="vaulted",
        media_moved_to=media_moved_to,
    )
