# 6. Spec reprioritization

**Parent:** [`PRODUCT-AUDIT.md`](../PRODUCT-AUDIT.md)

---

## 6.1 Current order (from CLAUDE.md)

```
0. Security Phase 1 (pre-launch)     ← blocking for open-source
1. Monitoring                         ← internal optimization
2. Security Phase 2 (hardening)       ← application-level fixes
3. Reranking                          ← search optimization
4. Semantic cache                     ← perf optimization (includes embedding.dims fix)
5. Benchmark                          ← quality measurement
6. Frontend                           ← user surface
```

## 6.2 Problem

Specs 1-5 optimize internals before the core value loop works. The user cannot create notes via MCP effectively, cannot search at note level, and has no CLI. Optimizing search quality for a search that returns 0 note results is premature.

## 6.3 Recommended order

```
0. Security Phase 1 (pre-launch)          ← unchanged, blocking for GitHub
1. ★ MCP flow fix (Priority A, section 2) ← NEW, unblocks the core value loop
   - embed_note
   - MCP tool completeness + descriptions
   - MCP setup documentation
2. ★ CLI                                  ← NEW, first human-facing surface
3. ★ Delete operations                    ← NEW, basic CRUD completeness
4. ★ Internal LLM path (Priority B)       ← NEW, low marginal cost after #1
5. embedding.dims fix                     ← extracted from semantic cache spec
6. Security Phase 2 (hardening)           ← application-level fixes
7. Monitoring                             ← now users exist, observability matters
8. Frontend                               ← moved up: users need a surface
9. Reranking                              ← search optimization (notes_vec now populated)
10. Semantic cache                        ← perf optimization
11. Benchmark                             ← quality measurement (can now test notes)
```

**Rationale for key changes:**
- Items 1-4 (★) are new work items that were not specced. They need `superpowers:writing-plans` before implementation.
- `embedding.dims` fix extracted from semantic cache spec — it's a cross-cutting prerequisite, not an optimization.
- Frontend moved before reranking/cache/benchmark — users need a surface before internal optimizations matter.
- Benchmark moved last — it now has populated `notes_vec` to test against.

## 6.4 Dependency map

```
Security P1 ──→ (repo goes public)
                    ↓
MCP flow fix ──→ CLI ──→ Delete ops ──→ Internal LLM path
                    ↓
            embedding.dims fix
                    ↓
            Security P2 ──→ Monitoring
                                ↓
                          Frontend ──→ Reranking ──→ Semantic cache ──→ Benchmark
```

**Implicit dependencies now made explicit:**
- Frontend depends on monitoring (dashboard shows runs/costs) — monitoring must come first
- Benchmark depends on `notes_vec` being populated — MCP flow fix must come first
- Semantic cache includes `embedding.dims` fix — extracted as standalone prerequisite
- Reranking and cache improve search quality — meaningless until notes exist in `notes_vec`
