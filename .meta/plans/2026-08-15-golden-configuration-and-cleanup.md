# Implementation Plan: Golden Configuration, Error Architecture & Constant Cleanup (Milestone 0)

**Date:** 2026-08-15  
**Status:** Plan-Ready  
**Type:** Refactoring & Architecture Foundation  
**Priority:** Mandatory prerequisite before implementing Phase 1 & Phase 2  
**Goal:** Eradicate 100% of hardcoded constants and magic numbers across the codebase, deploy a strict 3-tier configuration architecture, build the standardized `EgoVaultError` hierarchy with actionable diagnostic hints, and fix the vector divergence bug in `scripts/reembed.py`.

---

## 1. Context & Identified Issues

The exhaustive codebase audit and adversarial peer review uncovered:
1. **18 critical hardcoded constants** (Whisper models, bitrates, RRF parameters, API rate limits, timeouts, curate confidence weights).
2. **Missing unified Error Architecture:** Errors currently lack machine-readable `error_code`, `http_status`, and `actionable_hint` fields, resulting in unhelpful generic tracebacks across CLI, API, and MCP surfaces.
3. **`scripts/reembed.py` divergence bug:** Notes are currently re-embedded with `docstring` only instead of `title + docstring + body`.
4. **Test ripple effect:** Modifying `Settings` requires a universal `pytest` fixture to ensure the 511 existing tests remain 100% deterministic and green.

---

## 2. Task Breakdown

### Task 1: Golden YAML Configuration & Strict Pydantic Models
- **Files:** [`config/system.yaml`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/config/system.yaml), [`config/user.yaml.example`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/config/user.yaml.example), [`config/install.yaml.example`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/config/install.yaml.example), [`core/config.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/core/config.py)
- **Actions:**
  1. Populate `config/system.yaml` with sections:
     - `chunking`
     - `embedding`
     - `note_segmentation` (`sensitivity_k: 0.5`, `min_similarity_floor: 0.35`, `min_chunks_per_note: 3`, `max_notes_per_source: 30`, `max_chunks_per_candidate: 12`, `agent_claim_ttl_seconds: 300`, `human_claim_ttl_seconds: 3600`)
     - `curate.confidence` (`reviewed_note_weight: 1.0`, `unreviewed_note_weight: 0.7`, `rrf_k: 60`)
     - `ingest.pdf`, `ingest.ocr`, `ingest.media`
     - `llm`, `upload`, `web`, `taxonomy`
  2. Populate `config/user.yaml.example` with: `embedding`, `llm`, `vault`, `export.typst`.
  3. Populate `config/install.yaml.example` with: `paths`, `hardware`, `database`, `api`, `providers`.
  4. Implement strict Pydantic models in `core/config.py` with validation bounds (`Field(ge=..., le=...)`) and types.
  5. Add unit tests in `tests/core/test_config.py`.

### Task 2: Standardized Error Architecture V2 (`core/errors.py`)
- **Files:** [`core/errors.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/core/errors.py), [`api/main.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/api/main.py), [`cli/output.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/cli/output.py)
- **Actions:**
  1. Create the base `EgoVaultError(Exception)` class requiring:
     - `error_code: str` (e.g. `provider_unavailable`, `candidate_already_claimed`)
     - `user_message: str` (clean human-readable description)
     - `actionable_hint: str` (clear instruction to resolve the issue)
     - `http_status: int` (HTTP status code for API mapping)
     - `context: dict | None` (safe structured metadata)
  2. Implement specific exception subclasses:
     - `ConfigError` (`MissingConfigError`, `InvalidConfigValueError`, `MissingSecretError`)
     - `ProviderError` (`ProviderUnavailableError`, `ModelNotFoundError`, `ProviderTimeoutError`)
     - `ResourceError` (`NotFoundError`, `ConflictError`, `CandidateClaimedError`, `ExpiredLockError`)
     - `SecurityError` (`PathTraversalError`, `SSRFBlockedError`)
  3. Add global FastAPI exception handler in `api/main.py` serializing `EgoVaultError` to structured JSON.
  4. Update `cli/output.py` to format diagnostic cards displaying `Error`, `Code`, and `💡 Hint`.

### Task 3: Critical Fix for `scripts/reembed.py` & Vector Space Alignment
- **Files:** [`scripts/reembed.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/scripts/reembed.py), [`tests/scripts/test_reembed.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/tests/scripts/test_reembed.py)
- **Actions:**
  1. Update `scripts/reembed.py` to concatenate `title`, `docstring`, and `body` when re-indexing notes, matching [`tools/text/embed_note.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/tools/text/embed_note.py).
  2. Update `tests/scripts/test_reembed.py` to verify faithful vector reconstruction.

### Task 4: Media Tools & Export Sanitization
- **Files:** [`tools/media/transcribe.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/tools/media/transcribe.py), [`tools/media/compress.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/tools/media/compress.py), [`tools/media/fetch_subtitles.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/tools/media/fetch_subtitles.py), [`tools/export/typst.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/tools/export/typst.py), [`workflows/ingest.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/workflows/ingest.py)
- **Actions:**
  1. Refactor `transcribe.py` to accept Whisper parameters (`model`, `device`, `compute_type`) from `ctx.settings`.
  2. Refactor `compress.py` to read `bitrate_kbps` from `ctx.settings.system.ingest.media.audio_compression_bitrate_kbps`.
  3. Refactor `fetch_subtitles.py` to read fallback languages from `system.yaml`.
  4. Refactor `typst.py` to read default fonts and language from `user.yaml`.
  5. Update `workflows/ingest.py` to pass `ctx` to all media extractors.

### Task 5: Infrastructure, Database & Curate Configuration
- **Files:** [`infrastructure/db.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/infrastructure/db.py), [`infrastructure/embedding_provider.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/infrastructure/embedding_provider.py), [`infrastructure/llm_provider.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/infrastructure/llm_provider.py), [`tools/vault/curate.py`](file:///C:/Users/Vincent/GitHub/Vincent-20-100/egovault/tools/vault/curate.py)
- **Actions:**
  1. In `infrastructure/db.py`, inject `busy_timeout_ms` from `settings.install.database.busy_timeout_ms`.
  2. In `infrastructure/db.py::_rrf_fuse`, pass constant `k` dynamically from `settings.system.curate.confidence.rrf_k`.
  3. In `tools/vault/curate.py`, pass `reviewed_note_weight` and `unreviewed_note_weight` from `settings.system.curate.confidence`.
  4. In `infrastructure/embedding_provider.py`, use `settings.install.providers.ollama_timeout_s` instead of hardcoded `60`.
  5. In `infrastructure/llm_provider.py`, read `settings.system.llm.max_tokens` and `settings.system.llm.temperature`.

### Task 6: Universal Test Fixture & Regression Shield
- **Files:** `tests/conftest.py`
- **Actions:**
  1. Implement a universal `pytest` fixture providing an initialized `Settings` instance to prevent ripple breaks across the test suite.
  2. Verify that `uv run pytest` executes with **100% green tests (511+ passed, 0 failed)**.

---

## 3. Test Plan & Validation Criteria

1. **Unit Tests `test_config.py` & `test_errors.py`:**
   - Verify all configuration values are bounded and strictly typed.
   - Verify every exception in `core/errors.py` has valid `error_code`, `http_status`, and `actionable_hint`.
2. **Regression Suite:**
   - Run full pytest suite (`uv run pytest`) $\to$ **511+ passed, 0 failed**.
3. **Zero-Hardcode Verification:**
   - Grep verification: zero occurrences of hardcoded `"base"` / `"cpu"` / `"int8"` or magic confidence numbers in `tools/`.
