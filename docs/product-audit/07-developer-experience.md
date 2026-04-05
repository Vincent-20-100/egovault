# 7. Developer experience (DX)

**Parent:** [`PRODUCT-AUDIT.md`](../PRODUCT-AUDIT.md)

---

## 7.1 What works well

- **README** is compelling: "Aha Moment" narrative, Mermaid diagrams, comparison table, philosophy section. One of the best project READMEs at this stage.
- **ARCHITECTURE.md** is a model reference document — single source of truth, glossary, dependency rules, pre-commit checklist.
- **248 tests** with full coverage of tools/workflows/api/mcp.
- **Hexagonal architecture** is clean and well-enforced.

## 7.2 What will lose a developer in 10 minutes

| Problem | Fix | Priority |
|---------|-----|----------|
| **Quick Start ends at `pytest`** — no "try this" moment | Add "Ingest your first video" section with 3 commands (requires CLI) | Tier 1 |
| **MCP setup = "point it to mcp/server.py"** | Per-client setup guide (Claude Desktop JSON, Cursor config, etc.) | Tier 1 |
| **No CLI** — cannot do anything without writing Python | `egovault` CLI with `ingest`, `search`, `status` subcommands | Tier 1 |
| **API described as `[coming]` in README** but is implemented | Update README architecture section | Tier 2 |
| **Empty vault after setup** — no data to test with | Seed example or "try ingesting this YouTube URL" in Quick Start | Tier 2 |
| **No smoke test** — 248 unit tests pass but no end-to-end verification | Add `scripts/smoke_test.py` that ingests a real URL and verifies the full path | Tier 3 |
| **No Docker** — requires Python + uv + ffmpeg + Ollama installed manually | Future consideration, not blocking for dev audience | Tier 4 |

## 7.3 CLI spec sketch

```
egovault ingest youtube <url>          → triggers ingest_youtube workflow
egovault ingest audio <file>           → triggers ingest_audio workflow
egovault ingest pdf <file>             → triggers ingest_pdf workflow
egovault ingest web <url>              → triggers ingest_web workflow (future, see section 11)
egovault ingest document <file>        → auto-detect: DOCX, EPUB, PPTX (future, see section 11)
egovault search "query" [--mode notes|chunks] [--limit 5]
egovault status                        → shows recent jobs, vault stats
egovault notes [--limit 10]            → lists recent notes
egovault sources [--limit 10]          → lists recent sources
egovault export [--tags X] [--format md|json|zip] → selective vault export (future)
egovault mcp                           → starts MCP server (alias for current __main__)
egovault api                           → starts FastAPI server
egovault setup                         → interactive first-time config (user.yaml + install.yaml)
```

Implementation: `typer` or `click`, single `cli.py` file calling existing tools/workflows. Estimated cost: simple (all business logic already exists).
