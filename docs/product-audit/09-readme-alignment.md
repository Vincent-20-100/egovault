# 9. README alignment

**Parent:** [`PRODUCT-AUDIT.md`](../PRODUCT-AUDIT.md)

---

## 9.1 Current state

The README is aspirational — it describes the full vision, not the current implementation. This is a deliberate choice by the owner (helps orient LLM-assisted development).

## 9.2 Specific inaccuracies to address

| README claim | Reality | Action |
|---|---|---|
| "api/ [coming]" and "frontend/ [future]" in architecture section | API is implemented | Update to reflect current state |
| Mermaid diagram shows "Note draft (optional LLM)" | No LLM integration exists (by design — MCP-first) | Keep as-is (aspirational) but add beta disclaimer |
| "MCP server — bring your own LLM" | Works but no setup doc | Fix with MCP documentation (Tier 1) |
| `mode="notes"` implied as working in "RAG on notes" section | `notes_vec` is never populated | Fix with `embed_note` (Tier 1) |

## 9.3 Recommended action

Add a visible disclaimer near the top of the README:

```markdown
> **Beta** — EgoVault is under active development. Core architecture is stable.
> Some features described below are specced but not yet implemented.
> Check [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) section 7 for current status.
```

No content removed. Planning and implementation should converge toward the README vision.
