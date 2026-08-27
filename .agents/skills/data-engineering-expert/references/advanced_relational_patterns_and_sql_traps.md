# Advanced Relational Patterns & SQL Traps

> The relational patterns and query-time traps that separate a working schema from a correct one — the topics a novice designer almost always gets wrong on the first try. Complements the foundations in [`./database_modeling_and_relations.md`](./database_modeling_and_relations.md).

---

## 🗂️ 1. State & Status Modeling (the #1 novice trap)

Two failure modes dominate first attempts at modeling anything with a lifecycle (orders, tickets, applications, subscriptions):

1. **A single mutable `status` column with no history** — answers "what is it now" but not "when/why did it change", which the business always ends up needing.
2. **"Boolean soup"** — independent flags bolted on over time (`is_shipped`, `shipped_at`, `is_cancelled`, `cancelled_at`, `is_refunded`...) that let the database hold **impossible states** (`is_shipped=true AND is_cancelled=true`) because nothing enforces mutual exclusivity.

**Three legitimate patterns — pick by actual need, don't default to the heaviest one:**

| Pattern | What it answers | When to use |
|---|---|---|
| Current-state column + append-only history table | "What is it now" (fast) + "full history" (audit) | Default choice for most lifecycle entities |
| Pure event-sourced (no mutable current column) | Current state *derived* from the event log | Domains where the history IS the source of truth (finance, compliance) |
| Explicit transition table enforcing legal moves | Prevents nonsense transitions (`shipped → pending`) from ever being written | High-stakes workflows with strict business rules on ordering |

```sql
-- Pattern 1 — the default: mutable current state + immutable history
CREATE TABLE orders (
    order_id UUID PRIMARY KEY,
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('pending','paid','shipped','delivered','cancelled','refunded')),
    ...
);

CREATE TABLE order_status_history (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(order_id),
    status VARCHAR(20) NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changed_by TEXT,
    reason TEXT
);
-- "What is it now" -> orders.status (O(1) read)
-- "How long did it sit in 'paid'" -> window function (LEAD/LAG) over order_status_history

-- Pattern 3 — explicit legal-transitions table (add when illegal jumps are a real risk)
CREATE TABLE order_status_transitions (
    from_status VARCHAR(20) NOT NULL,
    to_status   VARCHAR(20) NOT NULL,
    PRIMARY KEY (from_status, to_status)
);
-- Application/trigger checks (from_status, to_status) exists here before writing to history.
```

**Rule of thumb**: if you catch yourself adding a third boolean flag to a lifecycle entity, stop — it's a `status` column with a history table trying to happen.

---

## ⏱️ 2. Temporal & Bitemporal Modeling

Two independent time axes get conflated constantly:
- **Valid time**: when something was true *in the real world* (`valid_from` / `valid_to`).
- **Transaction time**: when the system *learned about / recorded* it (separate from valid time — a correction entered today can be valid-from last month).

**Practical rule**: if the requirement is "current state + full history of changes", **SCD Type 2** (`valid_from`, `valid_to`, `is_current`, see `./database_modeling_and_relations.md` §3) is enough — that's one axis, and it's what 95% of "we need history" requests actually mean. Reach for true **bitemporal** (both axes tracked independently) only when you must reconstruct *"what did the system report as true, as of a past date, including corrections made since"* — regulated/financial reporting is the classic case. Don't build bitemporal by default; it roughly doubles query complexity for a question most projects never ask.

---

## 🌲 3. Hierarchies & Self-Referencing Relationships

| Technique | "Children of X" | "All ancestors of X" | Write cost | Verdict |
|---|---|---|---|---|
| Adjacency List (`parent_id` self-FK) | 1 query | Needs recursion | Cheap (1 row) | Base structure — always start here |
| + Recursive CTE | `WITH RECURSIVE` | `WITH RECURSIVE` | Cheap | **Default modern answer** (Postgres, SQL Server, SQLite 3.8.3+, DuckDB) |
| Closure Table (all ancestor–descendant pairs materialized) | 1 query | 1 query | Expensive (fan-out write on every move) | Deep trees queried heavily *both* directions (permission trees, file systems) |
| Nested Sets (`lft`/`rgt`) | 1 query | 1 query | Very expensive (renumber on every insert) | Rarely justified today — recursive CTEs cover most of its former use cases |

```sql
CREATE TABLE categories (
    category_id UUID PRIMARY KEY,
    parent_id   UUID REFERENCES categories(category_id),
    name        TEXT NOT NULL
);

WITH RECURSIVE category_tree AS (
    SELECT category_id, parent_id, name, 0 AS depth
    FROM categories WHERE category_id = :root_id
    UNION ALL
    SELECT c.category_id, c.parent_id, c.name, ct.depth + 1
    FROM categories c JOIN category_tree ct ON c.parent_id = ct.category_id
)
SELECT * FROM category_tree;
```

---

## 🧬 4. Supertype / Subtype (Entity Inheritance)

When entities share a core identity but diverge in attributes (`Vehicle` → `Car`, `Truck`):

- **Single Table Inheritance**: one wide table, nullable columns per subtype. Simple but sparse, and the database can't stop a `Car` row from having `Truck`-only fields filled.
- **Class Table Inheritance** *(Mere Mortals' recommended default)*: a `vehicles` supertype table (shared PK + common attributes) + one subtype table per type (`cars`, `trucks`) whose PK is also a FK to `vehicles.vehicle_id`. The shared key guarantees exactly one subtype row per supertype row. "All vehicles" queries hit the supertype; subtype-specific queries join down.
- **Concrete Table Inheritance**: fully separate tables per subtype, no shared supertype. Loses the ability to query "all vehicles" without a `UNION` — only acceptable when subtypes are never queried together.

---

## 🚫 5. Polymorphic Associations — catch this in review

*"A `comments` table with `commentable_type` + `commentable_id` pointing at either `posts` or `photos`"* looks elegant and **cannot be enforced by a real foreign key** — a FK targets exactly one table. Result: orphaned comments after a delete nobody caught, zero referential integrity on the relationship that matters most.

**Fix**: either (a) one junction table per target type (`post_comments`, `photo_comments`), or (b) if genuinely generic, promote the targets to a proper supertype (`commentable_items`, per §4) so the FK targets the supertype and stays enforceable.

---

## 🔺 6. N-ary (Ternary+) Relationships

A relationship that genuinely depends on 3+ entities together (`Student` enrolls in `Course` during `Semester`, and the grade depends on all three) **cannot** be decomposed into three separate binary M:N tables without losing information. Model it as one junction table carrying all three FKs plus the relationship's own attributes (`grade`) — not three pairwise tables that can drift out of sync with each other.

---

## ⚠️ 7. Classic SQL Traps (Query-Time, Not Just Design-Time)

- **Fan Trap**: joining one "one" row to two independent "many" children (e.g. `department JOIN employees JOIN projects`, where both are 1:N from `department`) multiplies rows and silently inflates any `SUM()`/`COUNT()` across the join. **Fix**: aggregate each "many" side in its own subquery/CTE *before* joining — never aggregate across a double fan-out join directly.
- **Chasm Trap**: two entities connected only through an *optional* intermediate relationship, so a plain `INNER JOIN` silently drops rows lacking the intermediate link (e.g. customers with zero orders vanish from `customers JOIN orders`). **Fix**: know which side must be preserved and use `LEFT`/`RIGHT JOIN` deliberately.
- **NULL Is Not a Value**: `NOT IN (SELECT ...)` silently returns **zero rows** the moment the subquery produces even one `NULL` (three-valued logic: `x <> NULL` is `UNKNOWN`, not `TRUE`). Prefer `NOT EXISTS` over `NOT IN` against any nullable column. `COUNT(column)` skips NULLs; `COUNT(*)` doesn't — pick deliberately.
- **Cartesian Explosion**: a missing/wrong `JOIN ... ON` condition (or an accidental comma-join) silently multiplies row counts instead of erroring. Sanity-check row counts before/after a join against the expected cardinality.
- **Gaps and Islands**: detecting contiguous runs (consecutive dates, consecutive identical statuses) needs the `ROW_NUMBER()`-difference trick (subtract a same-ordered sequence to group runs), not an ad-hoc self-join — a well-known named problem, don't reinvent it from scratch.
- **Implicit Type Coercion**: comparing a text column to a number, or a date stored as text, silently defeats indexes and can silently coerce mismatched values as equal. Match types explicitly.

---

## Sources
- *Database Design for Mere Mortals*, Michael J. Hernandez — normalization methodology, supertype/subtype modeling.
- Fan trap / chasm trap: classic entity-relationship modeling literature (originating with Howe, *Data Analysis for Database Design*).
