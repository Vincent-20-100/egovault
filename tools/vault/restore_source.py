"""
Source restore tool.

Input  : source uid
Output : RestoreSourceResult
Restores a source from pending_deletion to its previous status.
"""

from core.context import VaultContext
from core.schemas import RestoreSourceResult
from core.logging import loggable


@loggable("restore_source")
def restore_source(uid: str, ctx: VaultContext) -> RestoreSourceResult:
    """
    Restore a source previously marked for deletion.
    Reverts the source to its status prior to the soft-delete.
    """
    from core.errors import NotFoundError, ConflictError

    source = ctx.db.get_source(uid)
    if source is None:
        raise NotFoundError("Source", uid)
    if source.status != "pending_deletion":
        raise ConflictError("Source", uid, "not marked for deletion")

    restored_status = ctx.db.restore_source(uid)
    return RestoreSourceResult(uid=uid, restored_status=restored_status)
