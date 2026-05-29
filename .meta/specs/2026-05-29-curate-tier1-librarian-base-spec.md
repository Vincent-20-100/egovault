# Spec — curate() tier-1 base: "Librarian sub-context" (no API key)

**Date:** 2026-05-29
**Status:** Draft (brainstorm validated, pending user review)
**Topic:** Answer vault questions via an isolated fresh-context LLM step that uses the
host's own LLM — no EgoVault API key or local model required.
**Scope:** BASE layer only. Server-side LLM synthesis and MCP sampling are explicitly
out of scope (separate, later specs) but the output contract is designed to fit them.

---

## 1. Problem & intent

`curate()` today stops at tier 0: deterministic retrieval (notes -> chunks escalation),
returns an assembled `CuratedContext` with no synthesis. The desired tier-1 behavior:

> Give a fresh-context agent the question + a generous pile of retrieved sources +
> a system prompt. Let it triage, keep only what's relevant, synthesize the answer,
> and return to the main conversation ONLY the answer + the UIDs of the sources it
> actually used. Putting many candidates into the isolated agent (without polluting
> the main conversation) is the whole point — it lets the LLM pick the truly useful.

**Constraint chosen by the user:** the base case must require no extra API key and no
local model — it should plug directly into the host's existing LLM (the user's Claude),
when EgoVault is used via MCP.

## 2. Why this architecture (decision record)

The elegant server-driven mechanism is **MCP sampling** (`sampling/createMessage`):
the server asks the client to run an LLM completion. **Verified 2026-05-29: neither
Claude Code nor Claude Desktop support inbound sampling today** (open feature request
anthropics/claude-code#1785; FastMCP `ctx.sample()` raises if the client doesn't
advertise the capability). So sampling cannot be the base today.

An MCP tool result ALWAYS returns into the calling (main) context. The only way to keep
the retrieved pile out of the main conversation *without* sampling is for the host to
**voluntarily run an isolated step**. A server cannot invoke that; it can only ship the
configuration that enables it. The complete option space for {host LLM + no key +
real isolation + today} is therefore exactly two delivery vehicles:

- **Slash command** (`/egovault:ask-vault <q>`) — explicit invocation, **guaranteed** isolation.
- **Librarian subagent** — auto-delegation by the host, **heuristic** (not guaranteed).

Both are cleanly shippable together as a **Claude Code plugin** (one `/plugin install`
bundles the MCP server config + subagent + slash command). This removes the manual
file-copy friction. Sampling remains the target end-state (transparent + automatic +
reliable) — tracked as technical debt, migrate when clients support it.

## 3. Output contract (STABLE — shared across all future layers)

```
{
  answer: str,                 # the synthesized response
  used_source_uids: list[str]  # ONLY the sources actually used (note/chunk/source UIDs)
}
```

This same shape must be produced later by the server-side `ctx.complete()` layer and by
the sampling layer, so the three are interchangeable from the consumer's point of view.

## 4. Data flow

```
User asks a vault question (main conversation, host LLM)
  -> /egovault:ask-vault "<q>"        (explicit, guaranteed)   OR
     host auto-delegates to librarian subagent   (heuristic)
  -> FRESH SUB-CONTEXT:
       curate(query, generous mode) -> large pile {notes+chunks, UIDs, full content}
       LLM triages + synthesizes
  -> returns to main conversation ONLY: { answer, used_source_uids }
     (the pile never enters the main context)
```

## 5. Selection method — the feature's foundation

This is the substrate: if retrieval surfaces noise, the librarian synthesizes noise.
The key reframe is that **the librarian changes what retrieval optimizes for**.

- In tier-0 pure, `curate()` returns context directly, so it must be **precise** (noise
  hurts).
- Here, **the sub-agent provides precision** — it triages the pile, keeps the relevant,
  discards the rest. So the deterministic retrieval layer's job becomes **recall**: never
  *miss* a relevant source, even at the cost of over-returning. The LLM does the fine sort.

Resulting method (resolves open question #7 with already-measured evidence):

1. **Recall = hybrid RRF (cosine + BM25).** Already built (`search_*_hybrid`,
   `infrastructure/db.py`). The 2026-05-21 experiment measured **1 big win (the canonical
   finding-E case Q2 — an exact-topic source cosine missed, BM25 caught via the keyword),
   0 regression**. Hybrid is precisely a recall booster.
2. **Precision = the sub-agent's reasoning.** This is the elegant part: PageIndex gets
   precision by making an LLM reason over a tree; here the sub-agent reasons over the
   retrieved pile. We get the "LLM-reasoned precision" half **without** building a
   structural index. Retrieval only has to maximize recall.
3. **Structural tier (claude-obsidian `hot.md`/`index.md` precedence) = OUT of scope** —
   the 2026-05-21 doc itself classifies it as a "separate, larger redesign".

Concretely, the "generous mode" (§6.3) = **hybrid RRF + wide net**: notes *and* chunks
together (no sparse-notes escalation gate), high limit, untruncated content.

**Decision:** the generous mode **forces hybrid retrieval**, independent of the global
`curate.use_hybrid_retrieval` flag (default `false`). Rationale: recall is the explicit
design goal of the librarian and the experiment measured 0 regression; the global flag
governs the *conservative deterministic tier-0* default — a different consumer with a
different objective. Two consumers, two defaults.

**Tunable, not unbounded:** the wide-net limit must be a config value (cost/latency of
the sub-context scales with pile size). Exact default set in the plan.

## 6. Components

### 6.1 Plugin package (new)
- `.claude-plugin/plugin.json` — manifest.
- Bundles: existing `.mcp.json` (MCP server config), `agents/librarian.md` (subagent),
  `commands/ask-vault.md` (slash command).
- Install: one `/plugin install`. In-repo use of the subagent also works out-of-box via a
  checked-in `.claude/agents/librarian.md`.

### 6.2 Librarian behavior (prompt; shared by subagent + slash command)
- Input: the user's query.
- Steps: call `curate(query, generous)`; read the pile; triage; synthesize an answer
  grounded in the sources; cite ONLY the UIDs actually used.
- Output: the §3 contract. If the pile is empty/irrelevant: say so plainly, do not invent.
- Tags/citations follow existing vault conventions (UIDs are verifiable).

### 6.3 `curate()` generous-retrieval mode (the ONLY Python change)
- Add a parameter for sub-context consumption that implements §5: force hybrid RRF,
  return both notes and chunks (bypass the sparse-notes escalation gate), high tunable
  `limit`, untruncated content (skip `synthesis_max_chars_per_item`).
- Tier-0 deterministic behavior is unchanged when the parameter is off.
- Exact param name/shape and default limit to be finalized in the plan.

## 7. Error handling
- Empty / low-relevance retrieval -> librarian answers "rien de pertinent dans le vault",
  never hallucinates.
- Non-Claude-Code clients (no subagent/slash support) -> the base is simply unavailable;
  `curate` tier-0 still works (assembled context, no isolation/synthesis). The documented
  path for those clients is the future server-side tier-1.

## 8. Testing
- `curate()` generous mode: normal unit tests (forces hybrid, both tiers returned,
  truncation off, limit respected, ordering).
- Plugin files: a smoke test asserting `plugin.json` / agent / command files are
  well-formed and parseable.
- Honest limitation: the librarian prompt behavior is config/prompt, validated by
  real-use, not by unit tests. State this explicitly; do not fake coverage.

## 9. Technical debt (kept front-and-center — user requirement)
- **PROJECT-STATUS.md / Known technical debt:** "Librarian base relies on host-side
  delegation (subagent/slash) because MCP sampling is unsupported by Claude Code/Desktop
  (verified 2026-05-29). MIGRATE to MCP sampling when clients ship support -> transparent +
  automatic + reliable server-side isolation. Track: anthropics/claude-code#1785."
- This spec's §2 is the decision record.
- `SESSION-CONTEXT.md`: note the sampling-migration as an active deferred item.

## 10. Migration path -> sampling (future)
When a client advertises the sampling capability: `curate()` (or a thin wrapper) checks
`client_capabilities.sampling`; if present, perform the synthesis server-side via
`ctx.sample(system_prompt, query, pile)` and return the §3 contract directly — the
host no longer needs the subagent/slash. The contract does not change, so consumers are
unaffected. Same hook will host the server-side ollama/API layer for non-MCP consumers
(frontend), which is the next spec.

## 11. Documentation (automatism #8)
- `docs/user-guide/` MCP chapter: plugin install + the librarian pattern + when isolation
  applies. Search/curate chapter: mention generous mode + the recall-first selection method.
- Commit notes whether each change is user-visible.

## 12. Out of scope (do NOT build here)
- Server-side `ctx.complete()` LLM synthesis (ollama/API) — next spec; serves frontend.
- MCP sampling implementation — future, gated on client support.
- Structural tier-0 (claude-obsidian `index`/`hot` precedence) — separate, larger redesign.
- `/curate` API endpoint, frontend.
- Any change to tier-0 retrieval semantics beyond adding the generous mode.
