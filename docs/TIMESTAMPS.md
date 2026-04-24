# Timestamp verification

Major releases (v0.X.0) of this repository are timestamped in the Bitcoin
blockchain via [OpenTimestamps](https://opentimestamps.org/).

## Rule

**Only v0.X.0 tags are timestamped.** If a change deserves a timestamp, it deserves
to be a v0.X.0 release. No exceptions.

## Create a timestamp

```bash
# 1. Tag the release
git tag -a v0.X.0 -m "Description of this milestone"

# 2. Timestamp it (pure Python, no external dependencies)
python scripts/timestamp-release.py v0.X.0

# 3. Commit the proof
git add .timestamps/ && git commit -m "chore: add OTS proof for v0.X.0"

# 4. Push tags
git push origin --tags
```

## Verify a timestamp

Upload the `.ots` file and its matching `.hash` file at https://opentimestamps.org/.

Or with the OTS CLI (if installed): `ots verify .timestamps/v0.3.0.ots .timestamps/v0.3.0.hash`

## What this proves

The SHA256 hash of the git commit tagged v0.X.0 was registered in the Bitcoin blockchain
at the indicated date. Since a git commit hash covers the entire repository state (all files,
all history, author, date), this proves the complete project existed at that date.

## Timestamped releases

| Tag | Date | Description |
|-----|------|-------------|
| v0.1.0 | 2026-03 | Initial project — hexagonal architecture, MCP server, 3 ingest workflows |
| v0.2.0 | 2026-03-31 | VaultContext architecture — DI facade, full codebase migration, G4 compliant |
| v0.3.0 | 2026-04-16 | Knowledge compiler vision, librarian agent pattern, context engineering |
