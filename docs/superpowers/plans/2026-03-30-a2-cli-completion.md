# A2 CLI — Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the A2 CLI spec — add `NotFoundError`/`ConflictError` to `core/errors.py`, add `--status` to `note update`, add `--status` filter to `note list`, and add the `note approve` command.

**Architecture:** The CLI is already substantially implemented. This plan covers the delta between the current implementation and the updated spec. `note approve` lives in the CLI routing layer — it calls `update_note` then conditionally `finalize_source`. Zero business logic is added to the tools. A4-dependent commands (`source generate-note`, `ingest --generate-note`) are deferred to the A4 plan.

**Tech Stack:** `typer`, `rich`, `core/errors.py`, `tools/vault/update_note.py`, `tools/vault/finalize_source.py`, `infrastructure/db.py`, existing test patterns via `typer.testing.CliRunner`.

---

## File Map

**Modify:**
- `core/errors.py` — add `NotFoundError`, `ConflictError`
- `tools/vault/update_note.py` — raise `NotFoundError` instead of `ValueError`
- `tools/vault/finalize_source.py` — raise `NotFoundError` instead of `ValueError`
- `cli/commands/notes.py` — add `--status` to `note_update`, add `note_list --status`, add `note_approve`
- `tests/cli/test_notes.py` — add tests for `--status` on update, `note approve`, `note list --status`
- `tests/tools/vault/test_update_note.py` — update: expect `NotFoundError` instead of `ValueError`
- `tests/tools/vault/test_finalize_source.py` — update: expect `NotFoundError` instead of `ValueError`

---

## Task 1: Add `NotFoundError` and `ConflictError` to `core/errors.py`

**Files:**
- Modify: `core/errors.py`

- [ ] **Step 1: Add the two new error classes**

Open `core/errors.py` and add after the existing `LargeFormatError` class:

```python
class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, uid: str):
        self.resource = resource
        self.uid = uid
        super().__init__(f"{resource} not found: {uid}")


class ConflictError(Exception):
    """Raised when an operation conflicts with current resource state."""

    def __init__(self, resource: str, uid: str, reason: str):
        self.resource = resource
        self.uid = uid
        self.reason = reason
        super().__init__(f"{resource} '{uid}': {reason}")
```

- [ ] **Step 2: Verify import works**

```bash
cd /c/Users/Vincent/GitHub/Vincent-20-100/egovault
.venv/Scripts/python -c "from core.errors import NotFoundError, ConflictError; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add core/errors.py
git commit -m "feat: add NotFoundError and ConflictError to core/errors.py"
```

---

## Task 2: Use `NotFoundError` in `update_note` and `finalize_source`

**Files:**
- Modify: `tools/vault/update_note.py:31`
- Modify: `tools/vault/finalize_source.py:30`
- Modify: `tests/tools/vault/test_update_note.py`
- Modify: `tests/tools/vault/test_finalize_source.py`

- [ ] **Step 1: Update `update_note.py`**

In `tools/vault/update_note.py`, replace:
```python
    note = get_note(settings.vault_db_path, uid)
    if note is None:
        raise ValueError(f"Note not found: {uid}")
```
With:
```python
    from core.errors import NotFoundError
    note = get_note(settings.vault_db_path, uid)
    if note is None:
        raise NotFoundError("Note", uid)
```

- [ ] **Step 2: Update `finalize_source.py`**

In `tools/vault/finalize_source.py`, replace:
```python
    source = get_source(settings.vault_db_path, source_uid)
    if source is None:
        raise ValueError(f"Source not found: {source_uid}")
```
With:
```python
    from core.errors import NotFoundError
    source = get_source(settings.vault_db_path, source_uid)
    if source is None:
        raise NotFoundError("Source", source_uid)
```

- [ ] **Step 3: Update test for `update_note` — expect `NotFoundError`**

In `tests/tools/vault/test_update_note.py`, find the test that checks not-found behavior and update it:

```python
from core.errors import NotFoundError

def test_update_note_not_found(tmp_path, settings):
    with pytest.raises(NotFoundError):
        update_note("nonexistent-uid", {"title": "New"}, settings)
```

- [ ] **Step 4: Update test for `finalize_source` — expect `NotFoundError`**

In `tests/tools/vault/test_finalize_source.py`, find the test that checks not-found behavior and update it:

```python
from core.errors import NotFoundError

def test_finalize_source_not_found(tmp_path, settings):
    with pytest.raises(NotFoundError):
        finalize_source("nonexistent-uid", settings)
```

- [ ] **Step 5: Run affected tests**

```bash
.venv/Scripts/python -m pytest tests/tools/vault/test_update_note.py tests/tools/vault/test_finalize_source.py -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add tools/vault/update_note.py tools/vault/finalize_source.py \
        tests/tools/vault/test_update_note.py tests/tools/vault/test_finalize_source.py
git commit -m "fix: use NotFoundError in update_note and finalize_source"
```

---

## Task 2.5: Add `status` field to `Note` schema and `db.update_note`

**Files:**
- Modify: `core/schemas.py`
- Modify: `infrastructure/db.py`

This is required for `note approve` to work in A2. The DB column (`ALTER TABLE notes ADD COLUMN status`) is added in the A4 migration — until then, Pydantic uses the default value `"active"` for all existing notes.

- [ ] **Step 1: Add `status` field to `Note` schema**

In `core/schemas.py`, in the `Note` class, add after `sync_status`:

```python
status: str = "active"       # approval state: draft (auto-generated) | active (human-approved)
```

- [ ] **Step 2: Add `"status"` to `update_note` allowed fields**

In `infrastructure/db.py`, in the `update_note` function, add `"status"` to the `allowed` set:

```python
    allowed = {
        "title", "docstring", "body", "note_type", "source_type",
        "rating", "sync_status", "date_modified", "url", "status",
    }
```

- [ ] **Step 3: Run existing tests to verify nothing is broken**

```bash
.venv/Scripts/python -m pytest tests/ -v --tb=short -q
```
Expected: all PASS — `status` defaults to `"active"` for all existing notes.

- [ ] **Step 4: Commit**

```bash
git add core/schemas.py infrastructure/db.py
git commit -m "feat: add status field to Note schema and update_note (DB column deferred to A4)"
```

---

## Task 3: Add `--status` to `note update` CLI command

**Files:**
- Modify: `cli/commands/notes.py`

- [ ] **Step 1: Add `--status` parameter to `note_update`**

In `cli/commands/notes.py`, in the `note_update` function signature, add after `url`:

```python
    status: Annotated[Optional[str], typer.Option("--status", help="Set approval status: draft or active")] = None,
```

And in the `fields` dict construction, add after the `url` block:

```python
    if status is not None:
        if status not in ("draft", "active"):
            print_error("Invalid status. Must be 'draft' or 'active'.", "validation_error",
                        json_mode, verbose)
            raise typer.Exit(1)
        fields["status"] = status
```

And update the `except ValueError` catch to also catch `NotFoundError`:

```python
    except Exception as e:
        from core.errors import NotFoundError
        if isinstance(e, NotFoundError):
            print_error(f"Note not found: {uid}", "not_found", json_mode, verbose)
        else:
            print_error("Note update failed.", "update_error", json_mode, verbose, str(e))
        raise typer.Exit(1)
```

- [ ] **Step 2: Run existing note update tests to verify nothing broke**

```bash
.venv/Scripts/python -m pytest tests/cli/test_notes.py -v -k "update"
```
Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add cli/commands/notes.py
git commit -m "feat: add --status option to egovault note update"
```

---

## Task 4: Add `--status` filter to `note list`

**Files:**
- Modify: `cli/commands/notes.py`
- Modify: `infrastructure/db.py`

Note: the `status` column on `notes` is added in the A4 migration. Until that migration runs, the `status` filter silently returns all notes (the column doesn't exist yet). The CLI and DB layer are wired now — the feature activates automatically when A4 migration runs.

- [ ] **Step 1: Add `status` filter to `list_notes` in `infrastructure/db.py`**

In `infrastructure/db.py`, in the `list_notes` function, add after the `tags` block:

```python
    if status:
        where_clauses.append("n.status = ?")
        params.append(status)
```

The full function signature becomes:
```python
def list_notes(
    db_path: Path,
    note_type: str | None,
    tags: list[str] | None,
    limit: int,
    offset: int,
    status: str | None = None,
) -> list[Note]:
```

- [ ] **Step 2: Add `--status` parameter to `note_list` in `cli/commands/notes.py`**

In the `note_list` function signature, add:

```python
    status: Annotated[Optional[str], typer.Option("--status", help="Filter by approval status: draft or active")] = None,
```

Update the `_list_notes` call:

```python
    notes = _list_notes(settings.vault_db_path, note_type, tag_list, limit, offset, status=status)
```

And update the `_list_notes` helper to pass through the status:

```python
def _list_notes(db_path, note_type, tags, limit, offset, status=None):
    from infrastructure.db import list_notes
    return list_notes(db_path, note_type=note_type, tags=tags, limit=limit, offset=offset, status=status)
```

- [ ] **Step 3: Run existing tests**

```bash
.venv/Scripts/python -m pytest tests/cli/test_notes.py -v -k "list"
```
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add cli/commands/notes.py infrastructure/db.py
git commit -m "feat: add --status filter to note list (activates after A4 migration)"
```

---

## Task 5: Add `egovault note approve` command

**Files:**
- Modify: `cli/commands/notes.py`
- Modify: `tests/cli/test_notes.py`

- [ ] **Step 1: Write failing tests first**

Add to `tests/cli/test_notes.py`:

```python
def test_note_approve_success():
    """Approves a draft note — calls update_note then finalize_source."""
    note = _make_note(uid="nuid-approve")
    note_result = _make_note_result(note)
    from core.schemas import FinalizeResult
    finalize_result = FinalizeResult(source_uid="src-1", new_status="vaulted", media_moved_to=None)

    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._get_note", return_value=note), \
         patch("cli.commands.notes._update_note", return_value=note_result) as mock_update, \
         patch("cli.commands.notes._finalize_source", return_value=finalize_result) as mock_finalize:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["approve", "nuid-approve"])

    assert result.exit_code == 0
    mock_update.assert_called_once()
    assert mock_update.call_args[0][1] == {"status": "active"}


def test_note_approve_no_source():
    """Approves a note with no source_uid — no finalize_source call."""
    note = _make_note(uid="nuid-nosrc")
    note_no_source = note.model_copy(update={"source_uid": None})
    note_result = _make_note_result(note_no_source)

    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._get_note", return_value=note_no_source), \
         patch("cli.commands.notes._update_note", return_value=note_result), \
         patch("cli.commands.notes._finalize_source") as mock_finalize:
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["approve", "nuid-nosrc"])

    assert result.exit_code == 0
    mock_finalize.assert_not_called()


def test_note_approve_not_found():
    """Returns exit code 1 when note does not exist."""
    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._get_note", return_value=None):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["approve", "nonexistent"])

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_note_approve_json_mode():
    """--json flag outputs JSON."""
    note = _make_note(uid="nuid-json")
    note_result = _make_note_result(note)

    with patch("cli.commands.notes._load_settings") as mock_settings, \
         patch("cli.commands.notes._get_note", return_value=note), \
         patch("cli.commands.notes._update_note", return_value=note_result), \
         patch("cli.commands.notes._finalize_source", return_value=None):
        mock_settings.return_value = MagicMock()
        result = runner.invoke(app, ["approve", "nuid-json", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "uid" in data
```

- [ ] **Step 2: Run failing tests to confirm they fail**

```bash
.venv/Scripts/python -m pytest tests/cli/test_notes.py -v -k "approve"
```
Expected: FAIL — `note approve` command does not exist yet.

- [ ] **Step 3: Add `_get_source_status` and `_finalize_source` helpers to `cli/commands/notes.py`**

Add after the existing helpers at the top of the file:

```python
def _get_source_for_note(db_path, source_uid):
    from infrastructure.db import get_source
    return get_source(db_path, source_uid)


def _finalize_source(source_uid, settings):
    from tools.vault.finalize_source import finalize_source
    return finalize_source(source_uid, settings)
```

- [ ] **Step 4: Add `note_approve` command to `cli/commands/notes.py`**

Add after the `note_update` function:

```python
@app.command("approve")
def note_approve(
    uid: Annotated[str, typer.Argument(help="Note UID to approve")],
    json_mode: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show all fields")] = False,
) -> None:
    """Approve a draft note and finalize its linked source if applicable."""
    try:
        settings = _load_settings()
    except Exception as e:
        print_error("Configuration not found.", "config_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    note = _get_note(settings.vault_db_path, uid)
    if note is None:
        print_error(f"Note not found: {uid}", "not_found", json_mode, verbose)
        raise typer.Exit(1)

    try:
        result = _update_note(uid, {"status": "active"}, settings)
    except Exception as e:
        print_error("Failed to approve note.", "approve_error", json_mode, verbose, str(e))
        raise typer.Exit(1)

    finalized = False
    if note.source_uid:
        source = _get_source_for_note(settings.vault_db_path, note.source_uid)
        if source and source.status == "rag_ready":
            try:
                _finalize_source(note.source_uid, settings)
                finalized = True
            except Exception as e:
                print_error("Note approved but source finalization failed.",
                            "finalize_error", json_mode, verbose, str(e))
                raise typer.Exit(1)

    fields: dict = {
        "uid": result.note.uid,
        "slug": result.note.slug,
        "status": result.note.status,
    }
    if finalized:
        fields["source_finalized"] = note.source_uid

    print_panel("Note approved", fields, json_mode)
```

- [ ] **Step 5: Run tests**

```bash
.venv/Scripts/python -m pytest tests/cli/test_notes.py -v -k "approve"
```
Expected: all PASS

- [ ] **Step 6: Run full CLI test suite**

```bash
.venv/Scripts/python -m pytest tests/cli/ -v
```
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add cli/commands/notes.py tests/cli/test_notes.py
git commit -m "feat: add egovault note approve command"
```

---

## Task 6: Final smoke test and full suite

- [ ] **Step 1: Run the full test suite**

```bash
.venv/Scripts/python -m pytest tests/ -v --tb=short
```
Expected: all PASS (259+ tests)

- [ ] **Step 2: Manual smoke test — verify CLI works end to end**

```bash
.venv/Scripts/python -m cli.main note --help
.venv/Scripts/python -m cli.main note approve --help
.venv/Scripts/python -m cli.main note list --help
.venv/Scripts/python -m cli.main note update --help
```
Expected: all show the new flags without error.

- [ ] **Step 3: Final commit if any fixups needed**

```bash
git add -p
git commit -m "chore: A2 CLI completion — fixups"
```

---

## Deferred to A4 plan

The following CLI additions require A4 tools to be implemented first:
- `egovault source generate-note <uid> [--template standard]` — requires `tools/vault/generate_note_from_source.py`
- `egovault ingest --generate-note` / `--no-generate-note` — requires workflow `auto_generate_note` param
- `egovault note list --status draft` fully operational — requires `003_add_note_status.py` migration
- `egovault note update --status active` fully operational — requires same migration
