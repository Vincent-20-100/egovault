# Pre-reinit Code & Test Audit — 2026-05-17

**Scope:** DB layer (`infrastructure/db.py` + schema vs DATABASES.md + `reembed.py`),
`scripts/`, and full test-suite quality. Run before the planned data cleanup +
DB reinit + real-condition ingestion test.
**Method:** house audit spec (`.meta/specs/2026-03-31-project-audit-spec.md`),
severities CRITICAL (blocks reinit/ingest test) / MAJOR / MINOR.
**Executed by:** 3 parallel read-only audit agents (DB, scripts, tests).

---

## Headline

- **The "7 pre-existing failures" contain ZERO real product bugs.** 5/7 are a single
  test-infra defect (session-scoped `client` + global rate-limit state bleeding across
  API tests → spurious 429). 2/7 are stale tests referencing removed/changed signatures.
- **A green suite is NOT a trustworthy gate**: non-deterministic (order-dependent) AND
  structurally blind to cosine relevance + ingest chunk/embed (all mocked). The
  upcoming real-data run is the *first true integration signal*, not a confirmation.
- **The DB layer is NOT safe for reinit as-is** (DB-C1). A from-empty reinit mitigates
  DB-C2 by procedure but a guard is cheap insurance.

---

## CRITICAL — fix before the reinit/ingest test

### DB-C1 — Fresh `init_db` schema is missing `previous_status` / `previous_sync_status`
`infrastructure/db.py:46-117` (`_SCHEMA_SQL`) creates `sources`/`notes` without these
columns; they are only added by `scripts/temp/_002_add_previous_status.py`, which
`build_context()` / API lifespan never run. On a fresh reinit, the first
`soft_delete_*` / `restore_*` / `delete_*` (db.py:581,591,645,655) raises
`OperationalError: no such column: previous_status`. Delete/purge via CLI/MCP/API
hard-fails on a clean DB.
**Fix:** fold both columns into `_SCHEMA_SQL` (`previous_status TEXT`,
`previous_sync_status TEXT`) — they are permanent schema per DATABASES.md, not a migration.

### DB-C2 — `init_db` cannot detect a stale pre-cosine DB (silent L2 metric)
`init_db` uses `CREATE VIRTUAL TABLE IF NOT EXISTS` (db.py:121-128). On a DB created
before cosine (a30e443), the vec tables keep `distance_metric=l2` while embeddings are
now normalized → `curate()` tier-0 threshold (`escalation_max_distance=0.5`, cosine
∈[0,2]) silently mis-scores. **Mitigated** if the test starts from an empty data dir
(true full reinit). **Fix (cheap insurance):** startup check reads vec0 DDL from
`sqlite_master`, warn/refuse if `distance_metric=cosine` absent (mirror the existing
embedding_dim mismatch warning, db.py:203-214).

### TEST-C1 — API suite is non-deterministic → green run is order-dependent
`tests/api/conftest.py` `client`/`tmp_settings` are `scope="session"`; the app's
module-level `api.main._request_counts` rate-limit dict is never reset between files.
Causes the 5 spurious failures. Only `test_rate_limiting.py` clears it.
**Fix:** make `client` `scope="function"`, OR add an autouse fixture in
`tests/api/conftest.py` clearing `api.main._request_counts` before each test.

### TEST-C2 — Semantic relevance / ingest chunk+embed are never really tested
Global `ctx` fixture: `embed=lambda text: make_embedding()` → identical vector for all
text. `test_search.py` asserts only `len==1`; `test_db.py::test_search_chunks_returns_results`
asserts only `distance>=0`. `tests/workflows/test_ingest.py` mocks BOTH `chunk_text`
and `embed_text` in every test. The product's core (cosine ranking, F2 area, ingest
chunking/embedding) has effectively one real regression test
(`test_db.py::test_vec_tables_use_cosine_distance`, SQL-layer) and none end-to-end.
**Fix (post-reinit acceptable):** add a DB test with distinct-direction vectors
asserting the relevant chunk ranks first; add one ingest test with real `chunk_text` +
a deterministic hash-based fake embed.

---

## MAJOR

| ID | File | Issue | Fix |
|----|------|-------|-----|
| DB-M1 | db.py:606-625 et al. | Hard-delete = 4 funcs, 4 connections, no atomicity; crash → orphaned `chunks_vec`/notes | Single transactional `purge_source(db_path, uid)`, vec deletes first |
| DB-M2 | db.py (all), embedding_provider.py:49 | Raw `sqlite3` errors propagate uncaught; bare `except Exception` no log; no `core/errors.py` use | Wrap DB boundary errors + log; catch specific exc |
| DB-M3 | db.py (~50 funcs) | No `try/finally: conn.close()` → connection/WAL leak = the documented "DB lock in API tests" root cause | `with vault_conn(...)` context manager |
| DB-M4 | db.py:414-464 | `search_chunks/notes` ignore `filters` arg → curate pulls chunks from `failed`/`pending_deletion`/`raw` sources | Apply status whitelist; honor filters |
| SCRIPT-M1 | reembed.py:27-31 | Drops vec tables before probing provider; no backup/confirm → half-rebuilt index on Ollama failure | Probe `ctx.embed("test")` first; backup `vault.db`; `--yes` flag |
| SCRIPT-M2 | scripts/temp/* | Dead one-shot migrations; `001` unconditionally `DROP TABLE IF EXISTS tool_logs` (line 69) — landmine on fresh db; `_003` hardcodes db path | Delete `scripts/temp/` + stale `__pycache__` |
| TEST-M1 | — | No test: `api/routers/monitoring.py`, `tools/text/summarize.py`, `tools/media/extract_audio.py` | Add test files (testing.md parity rule) |
| TEST-M2 | tests/cli/test_notes.py::test_note_create_from_file | Stale: patches removed `_get_existing_slugs` → AttributeError (F4 #6) | Patch `_create_note` only / `VaultDB.get_existing_slugs` |
| TEST-M3 | tests/tools/test_export_typst.py | Orphan at wrong path, obsolete 1-arg signature; superseded by tests/tools/export/test_typst.py (F4 #7) | Delete orphan file |

## MINOR (selected)

- DB-m1 `_build_metadata_sql` f-string into SQL (db.py:132-137) — parameterize.
- DB-m2 Schema doc drift: DATABASES.md stale on `jobs` columns, vec `distance_metric`,
  `_build_vec_schema_sql` name, unimplemented `.system.db` tables. Update doc.
- SCRIPT-m1 `timestamp-release.py:87-89` relative `.timestamps/` — same cwd bug class
  as the just-fixed hook; anchor to repo root.
- TEST-m1 `make_embedding(0.0)` zero-vector still used in `test_ingest.py` /
  `test_embedding_provider.py` — latent divide-by-zero in any real-normalization path
  (the exact F2/48891bd degenerate input).
- Stale `scripts/__pycache__` for ~12 deleted scripts — cosmetic clutter.

## Already fixed this session

- HOOK (finding C in scratch): `force_git_author.py` invoked via relative path broke
  all Bash on cwd drift → fixed `$CLAUDE_PROJECT_DIR` (commit `664d953`).
- Pre-reinit findings A (CLI UTF-8 mojibake — display only, data clean) and B
  (`sources.title=None` after ingest) logged in
  `.meta/scratch/2026-05-17-prereinit-findings.md` — B to triage during real ingest.

---

## Verdicts

- **DB layer:** NOT safe as-is. Fix DB-C1 (mandatory). Reinit from empty dir mitigates
  DB-C2; add the guard for insurance. DB-M3 matters only if the test exercises
  concurrent API ingestion (CLI ingest is single-conn → lower risk).
- **Scripts:** `init_user_dir.py` SAFE (cwd-anchored, non-destructive, layout matches
  ARCHITECTURE §2). `reembed.py` correct but unsafe-by-default (SCRIPT-M1) — not run on
  fresh DB anyway. `scripts/temp/` must NOT run and should be deleted (SCRIPT-M2).
- **Tests:** green suite NOT a trustworthy gate (TEST-C1 non-determinism + TEST-C2
  blindness). Zero real product bugs in the 7. Treat the real-data ingest as the first
  genuine integration signal.

## Resolution status (étape 4 — DONE 2026-05-17)

| Fix | Commit | Result |
|-----|--------|--------|
| DB-C1 | `0434e07` | previous_status/previous_sync_status folded into _SCHEMA_SQL |
| SCRIPT-M2 | `cc8ef7f` | scripts/temp/ + 2 obsolete migration tests deleted; helper simplified |
| TEST-C1 | `44f333b` | autouse rate-counter reset in tests/api/conftest.py |
| TEST-M3 | `c017db4` | orphan typst test deleted, quote-escape ported to canonical |
| TEST-M2 | `c017db4` | stale `_get_existing_slugs` patch removed |
| DB-C2 | `dd9dd4b` | init_db warns on stale L2 vec table |

**Full suite after étape 4: 481 passed / 0 failed / 1 skipped — deterministic.**
The historical "7 pre-existing failures" (F4) are fully eliminated and were
confirmed to contain ZERO real product bugs.

**Still deferred (tracked debt, post-reinit):** DB-M1 (atomic purge_source),
DB-M2 (DB error wrapping/logging), DB-M3 (connection-leak / try-finally —
systemic ~50 funcs), DB-M4 (search ignores filters), SCRIPT-M1 (reembed
backup/probe), TEST-C2 (no real semantic-relevance / ingest e2e test),
TEST-M1 (missing test files: monitoring router, summarize, extract_audio),
plus listed MINORs.

## Recommended fix order before reinit (étape 4)

1. **DB-C1** — fold previous_status columns into `_SCHEMA_SQL` (mandatory, ~2 lines).
2. **SCRIPT-M2** — delete `scripts/temp/` (removes the `DROP tool_logs` landmine).
3. **TEST-C1** — function-scope client / autouse counter reset (makes suite deterministic).
4. **TEST-M2 + TEST-M3** — fix stale test_notes, delete orphan typst → suite fully green & trustworthy.
5. **DB-C2 guard** — cheap startup cosine-metric check (insurance).
6. Defer to post-reinit: DB-M1/M2/M3/M4, SCRIPT-M1, TEST-C2, TEST-M1 (tracked debt).
