# SQL Dialect Syntax & Optimization Reference

> Cross-engine SQL cheat-sheet (PostgreSQL, MySQL/MariaDB, SQL Server, SQLite, DuckDB) — for when the concept is clear but the exact syntax or dialect gap isn't. Source: [sql.sh](https://sql.sh/).

---

## 1. Join Types — Syntax & Semantics

| Join | Returns |
|---|---|
| `INNER JOIN` | Rows where the condition matches in both tables |
| `LEFT JOIN` | All left rows, matched right or `NULL` |
| `RIGHT JOIN` | All right rows, matched left or `NULL` |
| `FULL JOIN` | Union of `LEFT` + `RIGHT` |
| `CROSS JOIN` | Full Cartesian product — see Cartesian Explosion trap in `./advanced_relational_patterns_and_sql_traps.md` |
| `SELF JOIN` | A table joined to itself via aliases (hierarchies, comparisons) |
| `NATURAL JOIN` | Auto-joins on identically-named columns — **avoid in production code**: implicit and silently breaks if the schema later adds an unrelated same-named column |

**Dialect gaps to know**:
- **MySQL/MariaDB has no `FULL JOIN`** — emulate with `LEFT JOIN ... UNION ... RIGHT JOIN ...`.
- **SQLite** only gained `RIGHT JOIN` / `FULL JOIN` in 3.39 (2022) — older SQLite (or apps pinned to an older build) supports `LEFT JOIN` only; rewrite `RIGHT JOIN` as a `LEFT JOIN` with tables swapped for portability.

---

## 2. Common Function Equivalents

| Task | PostgreSQL | MySQL | SQL Server | SQLite | DuckDB |
|---|---|---|---|---|---|
| Current timestamp | `NOW()` | `NOW()` | `GETDATE()` | `datetime('now')` | `NOW()` |
| String concat | `\|\|` / `CONCAT()` | `CONCAT()` | `+` / `CONCAT()` | `\|\|` | `\|\|` / `CONCAT()` |
| Substring | `SUBSTRING()` | `SUBSTRING()` | `SUBSTRING()` | `SUBSTR()` | `SUBSTRING()` |
| Type cast | `::type` / `CAST()` | `CAST()` / `CONVERT()` | `CAST()` / `CONVERT()` | `CAST()` | `CAST()` / `::type` |
| Upsert | `INSERT ... ON CONFLICT` | `INSERT ... ON DUPLICATE KEY UPDATE` | `MERGE` | `INSERT ... ON CONFLICT` | `INSERT ... ON CONFLICT` |
| Auto-increment PK | `GENERATED ALWAYS AS IDENTITY` / `SERIAL` | `AUTO_INCREMENT` | `IDENTITY(1,1)` | `INTEGER PRIMARY KEY` (implicit rowid) | `SEQUENCE` |

Always verify on the target engine's own docs before shipping — this table is a starting point for "does this even exist here", not a guarantee of identical semantics (e.g. upsert conflict-resolution granularity differs).

---

## 3. Optimization Pitfalls (query-time, complements design-time traps)

**Anti-patterns to flag in review:**
- `SELECT *` in application code — always select the columns actually needed.
- Leading wildcard `LIKE '%abc'` — can't use a standard B-tree index, forces a full scan.
- Wrapping an indexed column in a function inside `WHERE` (`WHERE YEAR(created_at) = 2026`) defeats the index — rewrite as a sargable range predicate: `WHERE created_at >= '2026-01-01' AND created_at < '2027-01-01'`.
- `WHERE x NOT IN (subquery)` against a nullable column — see the NULL trap in `./advanced_relational_patterns_and_sql_traps.md`; prefer `NOT EXISTS`.
- A query re-run inside an application loop (N+1 pattern) instead of one batched/joined query.

**Structural checklist:**
- Index every foreign key and every column driving a selective `WHERE` / `JOIN` / `ORDER BY` / `GROUP BY`.
- Prefer numeric surrogate PKs for join performance over wide text/composite naturals (see key typology in `./database_modeling_and_relations.md` §0).
- Run `EXPLAIN` (or `EXPLAIN ANALYZE` where available) before assuming a query is slow "because of data size" — verify it's actually a missing index or a bad plan first.

---

## Sources
- [sql.sh — Cours SQL](https://sql.sh/cours), [Jointures](https://sql.sh/cours/jointures), [Optimisation](https://sql.sh/optimisation).
