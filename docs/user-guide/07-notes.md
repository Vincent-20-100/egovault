# 07 — Notes

Notes are the unit you actually re-read. Sources are *evidence*; notes are
*knowledge*.

## Anatomy of a note

A note is one row in `notes` + one Markdown file in `vault/notes/<slug>.md`.

| Field | Constraint | Notes |
|---|---|---|
| `uid` | UUID4, immutable | Stable identifier; what every other table references |
| `slug` | `kebab-case`, lowercase, ASCII | Auto-generated from title; file name on disk |
| `title` | ≥1 char | Used for embedding + display |
| `docstring` | optional | One-paragraph summary; the **searchable abstract** |
| `body` | ≥10 chars | Full Markdown body |
| `note_type` | from `taxonomy.note_types` at approval | e.g. `synthese`, `concept`, `reflexion` — see [03](03-configuration.md) |
| `source_type` | from `taxonomy.source_types` at approval | What the underlying source was (`youtube`, `pdf`...) |
| `generation_template` | template name | `standard` by default |
| `tags` | 1–10 items, kebab + ASCII + lowercase | Auto-slugified at generation time |
| `rating` | 1–5 or null | Set ONLY by the user — never by the LLM |
| `sync_status` | `synced` / `pending_deletion` | Tracks Obsidian sync state |
| `status` | `draft` / `active` | **Lifecycle gate** — see below |
| `source_uid` | optional FK | If derived from one source; null for free-form / cross-source notes |

## Lifecycle: draft → active

```
LLM generates → status=draft → user reviews → user approves → status=active
                  │
                  └── (no Obsidian file yet; not surfaced as approved knowledge)
```

A `draft` note is **created in the DB but not exposed in the Obsidian vault
as an active asset**. The vault writer writes it to `vault/notes/<slug>.md`,
but tags/templates indicate "draft." Once approved:

- The note's `status` flips to `active`
- The taxonomy fields (`note_type`, `source_type`) are validated against
  `system.yaml` `taxonomy:` (this is when invalid types raise — see below)
- The note becomes part of the corpus that `curate()` returns

### Why the draft gate exists

LLMs hallucinate, mis-tag, or pick a `note_type` outside your taxonomy. The
draft gate is the **human-in-the-loop checkpoint** — you read the note
before it lives in your vault.

> **Important:** the LLM-side validation at generation time **does NOT enforce
> taxonomy** (deliberate — see provider spec §3.1). It only enforces structural
> rules (title ≥1 char, body ≥10, tags kebab/ASCII/lowercase, ≤10). Taxonomy
> is checked at approval, with a clear error message if the LLM proposed an
> unknown `note_type`. You can either edit the field or add the new value to
> `system.yaml`.

## Generation workflow

### 1. Auto on ingest (set-and-forget)

```yaml
# user.yaml
llm:
  auto_generate_note: true
```

After every successful `ingest_*`, the workflow calls
`generate_note_from_source(source_uid, ctx)` and a `draft` note appears.

### 2. On demand (explicit)

```bash
# CLI
egovault note generate <source_uid>

# MCP
generate_note_from_source(uid="<source_uid>")
```

### 3. Manual (you write it yourself)

```bash
# CLI
egovault note create --from-file my-note.yaml

# MCP
create_note(content={...}, source_uid=None)
```

A manual note can be source-less (you wrote it from scratch, no `source_uid`)
or source-linked (you composed it after reading several sources). The
content uses the same `NoteContentInput` schema.

## Templates

`config/templates/generation/<name>.yaml` defines:

```yaml
name: standard
description: "Default note generator — distillation of a source"
system_prompt: |
  ...the LLM's role...
output_schema: |
  ...the JSON schema the LLM must emit...
```

The default is `standard`. Add your own templates (e.g., `book-notes`,
`technical-deep-dive`) by:

1. Writing the `.yaml` in `config/templates/generation/`
2. Registering its name in `system.yaml` `taxonomy.generation_templates`
3. Setting `user.yaml` `vault.default_generation_template` OR passing
   `template_name=` at generation time

Templates are **versioned in the repo** (`config/`) — they're tuning you
intentionally share across the project. Personal tuning lives in
`user.yaml`'s `default_generation_template` choice.

## Tag rules (the trap to know)

The validator on `tags`:

- Each tag: 1–80 chars, **lowercase**, **ASCII only** (no accents),
  **kebab-case** (`^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$`)
- The list: 1–10 unique tags

If you write content in French, your LLM will WANT to emit `systèmes`,
`décentralisation`, `bio-éthique`. These fail validation.

**EgoVault auto-slugifies tags at generation time** in both providers:

```
"Systèmes"        → "systemes"
"Décentralisation"→ "decentralisation"
"Bio-Éthique"     → "bio-ethique"
"Knowledge Compiler" → "knowledge-compiler"
```

The transformation: `unicodedata.NFKD → encode ascii ignore → lowercase →
replace whitespace/underscore with hyphen → drop everything outside [a-z0-9-]
→ collapse multiple hyphens → strip leading/trailing hyphens → dedupe`.

The same normalization runs on the Claude path for strict provider parity
(see F5 follow-up commit `93ee644`).

## Deleting and restoring

```bash
# Soft delete — status flips to pending_deletion, file removed from vault
egovault note delete <uid>

# Restore — status returns to previous (active/draft), file regenerated
egovault note restore <uid>

# Hard delete — gone forever; chunks_fts/notes_fts cleaned automatically
egovault note delete <uid> --hard
```

Soft-deleting is preferred — leaves a recoverable trace. Hard-delete is
permanent and requires `allow_destructive_ops: true` to expose via MCP.

## Updating a note

```bash
egovault note update <uid> --title "..." --docstring "..."
```

When `title` or `docstring` change, the note's FTS5 row is automatically
resynced (`update_note` re-INSERTs into `notes_fts`) so BM25 sees the new
text.

Body edits — easier to do directly in the `.md` file in your Obsidian vault;
the watcher (if `vault.obsidian_sync: true`) picks them up.

## Manual note YAML format

```yaml
# my-note.yaml — for `egovault note create --from-file my-note.yaml`
title: "Tier-2 vs tier-1 retrieval"
docstring: |
  Compiled notes embed and rank better than raw chunks — proven on a 25-source FR corpus.
body: |
  ## Idea
  ...full Markdown body here...
note_type: synthese
source_type: youtube              # or null for source-less
tags: ["retrieval", "compiler"]
url: null                         # optional, for source-less notes citing an external URL
source_uid: null                  # set if linking to an ingested source
```

## What's next

- [08 — CLI reference](08-cli.md): every `egovault note ...` command
- [10 — Obsidian](10-obsidian.md): how notes show up in the graph
- [11 — Maintenance](11-maintenance.md): backups and reembedding
