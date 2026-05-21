# 10 — Obsidian

Your notes live as plain Markdown files in `egovault-user/vault/notes/`. That
folder is a regular Obsidian vault — open it, get a graph for free.

## Vault layout

```
egovault-user/
└── vault/                          ← the Obsidian vault root
    ├── notes/                      ← every active note as <slug>.md
    │   ├── algorithmes-consensus.md
    │   ├── methode-scientifique.md
    │   └── ...
    └── .obsidian/                  ← Obsidian config (pre-seeded)
        ├── app.json
        ├── appearance.json
        ├── core-plugins.json
        └── ...
```

The `.obsidian/` config is created by `init_user_dir.py` on first run and
ships with sensible defaults (graph enabled, tags pane on, dark theme).
Customize freely — `.obsidian/` is *your* config; EgoVault never overwrites
it after initial creation (unless you re-init with `--force`).

## Open the vault

1. Launch Obsidian
2. "Open folder as vault" → select `egovault-user/vault/`
3. Notes appear in the file explorer; tags appear in the tags pane; graph
   view shows links

## Note structure on disk

Every note is a Markdown file with YAML frontmatter:

```markdown
---
uid: 8f47dc81-efde-4105-8cbd-6190831ab577
slug: organisation-decentralisee-des-fourmis
note_type: synthese
source_type: youtube
source_uid: a3c91b...
tags: [fourmis, decentralisation, intelligence-collective]
date_created: 2026-05-20
date_modified: 2026-05-20
status: active
---

# Organisation décentralisée des fourmis

(docstring as a callout — see Obsidian markdown style)

## Idée principale

...the body in Markdown...
```

You can edit the file freely in Obsidian:

- **Body edits** are picked up by the sync watcher (when
  `user.yaml` `vault.obsidian_sync: true`) and persisted back to the DB.
- **Frontmatter edits** (e.g. adding a tag) require the watcher; otherwise
  the DB row diverges from disk.
- **Renaming a file** breaks the `slug ↔ uid` link — don't rename in
  Obsidian. Use `egovault note update --slug ...` instead (rebuilds the file).

## Tags

Tags are stored both in:

- the DB (`tags` table, `note_tags` junction) — for search filters
- the Markdown frontmatter (`tags: [...]` array) — for Obsidian's tag pane

Frontmatter tags use the kebab-case ASCII format EgoVault enforces; Obsidian
displays them as-is in the pane (`#decentralisation`, `#intelligence-collective`).

## Links

EgoVault doesn't auto-link notes by default. Two ways to add links:

1. **Manually in Obsidian** — write `[[other-note-slug]]` in the body.
   Obsidian renders, EgoVault watcher persists.
2. **In the generation template** — extend a template to ask the LLM for
   `related_notes: [...]` and write them as wikilinks. Future templates may
   ship this.

The graph view auto-builds from the links + tags. Even without explicit
links, tags create implicit clusters.

## The sync watcher

When `user.yaml` `vault.obsidian_sync: true` (default), a background watcher
follows file changes in `vault/notes/` and updates the corresponding DB rows.
This is the **vault → DB** direction. The reverse (DB → vault) happens at
`finalize_source`, `create_note`, `update_note`, `delete_note` via
`infrastructure/vault_writer.py`.

> Full bidirectional sync (programmatic DB edits reflected live in the open
> Obsidian session) is a deferred item — see `docs/FUTURE-WORK.md` § Full
> bidirectional watcher.

## Drafts vs active

Only **`active`** notes are written to the Obsidian vault as `.md` files.
Drafts live in the DB only — they're inspectable via the CLI (`egovault note
get <uid>`) or MCP (`get_note(uid)`) but invisible in Obsidian until approval.

This is intentional: your Obsidian vault should be **trusted knowledge**, not
LLM scratch.

## Backups

`vault/` is **a private git repo by design** (see [01-concepts.md](01-concepts.md)
§ Three storage locations). Treat it like any project repo:

```bash
cd egovault-user/vault
git init                            # one-time
git remote add origin <private>     # one-time
git add -A && git commit -m "snapshot $(date -I)"
git push
```

Cron a daily `git commit && git push` and your notes are continuously
backed up off-machine.

`data/vault.db` is binary — back it up by copying the file:

```bash
cp egovault-user/data/vault.db ~/backups/vault-$(date +%F).db
```

See [11-maintenance.md](11-maintenance.md) for the full backup playbook.

## Plugin recommendations

EgoVault's `.obsidian/` ships with:

- **Tag pane** enabled
- **Graph view** with sensible defaults
- **Daily notes** disabled (EgoVault notes are evergreen, not journal-like)

Plugins worth adding manually:
- **Templater** — for your own note formatting shortcuts
- **Dataview** — query your notes as a DB inside Obsidian (great for
  cross-corpus analytics: "all `note_type: concept` notes from this month")

These are user choices; EgoVault doesn't depend on them.

## What's next

- [11 — Maintenance](11-maintenance.md): re-embed, backup, FTS5 backfill
- [07 — Notes](07-notes.md): the lifecycle behind the files
