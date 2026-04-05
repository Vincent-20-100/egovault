"""
Source restore tool.

Input  : source uid
Output : RestoreSourceResult
Restores a source from pending_deletion to its previous status.
"""

from core.schemas import RestoreSourceResult
from core.config import Settings
from core.logging import loggable


@loggable("restore_source")
def restore_source(uid: str, settings: Settings) -> RestoreSourceResult:
    """
    Restore a source previously marked for deletion.
    Reverts the source to its status prior to the soft-delete.
    """
    from core.errors import NotFoundError, ConflictError
    from infrastructure.db import get_source, restore_source as restore_source_db

    source = get_source(settings.vault_db_path, uid)
    if source is None:
        raise NotFoundError("Source", uid)
    if source.status != "pending_deletion":
        raise ConflictError("Source", uid, "not marked for deletion")

    restored_status = restore_source_db(settings.vault_db_path, uid)
    return RestoreSourceResult(uid=uid, restored_status=restored_status)
