# Relational access compile probe (library-leverage assessment, cluster R1)

**Date:** 2026-10-29. **Purpose:** settle, without a database, whether the SQLAlchemy Core and
psycopg routes named in the first library applicability assessment can express the shapes the
relational cluster depends on. Evidence only; it decides nothing.

## Questions

1. Does Core `col.in_(ids)` expand to one bind parameter per element under the psycopg dialect,
   and does `col == any_(bindparam(..., type_=ARRAY(Text)))` render a single array parameter?
2. Do release-scoped predicates over `typed_value`/`value_role`, and a set-oriented explanation read
   keyed by `fact_id = ANY(:ids)`, compose into single statements whose filters stay in SQL?
3. Can a reachability closure (fact → value, value → child value, value → entity) be written as a
   recursive CTE over a non-recursive `UNION ALL` edge relation with one recursive reference,
   against the shared semantic MetaData?
4. Does `CreateTable(...)` over the shared MetaData reproduce the frozen `CREATE TABLE` text of a
   recent revision (`semantic_0027_exclusions.sql`)?
5. Does `psycopg.conninfo.make_conninfo` derive a per-principal conninfo (overriding `user`) from
   the configured libpq URL offline?
6. Can an authoring-time generator render transport SQL offline with `psycopg.sql`, and how does
   its identifier quoting compare with SQLAlchemy's identifier preparer?

## Environment

- Source tree at `d739b883e322adef7a3202e2896766ff71bcac5d` (clean).
- Python 3.14.10 via `uv run --no-sync python`; SQLAlchemy 2.1.5, psycopg 3.3.6 (binary), the
  installed `.venv`. No database connection, no network service, no installs.

## Command

```
uv run --no-sync python docs/design_review/evidence/2026-10-29_library-leverage-relational/probe.py \
  > docs/design_review/evidence/2026-10-29_library-leverage-relational/probe-output.txt 2>&1
```

Exit status 0. Raw output: [probe-output.txt](probe-output.txt). Script: [probe.py](probe.py).

## Outcome (probe-observed, compile only)

1. `in_()` compiles to `IN (__[POSTCOMPILE_...])` and expands to one `%(…)s` per element
   (5 ids → 5 parameters), so SQL text and parameter count vary with list size. `= ANY(%(ids)s::TEXT[])`
   renders one parameter regardless of size.
2. Both compose: nested `EXISTS` over `value_role`/`typed_value` with release/realization scope,
   C-collated keyset predicate, `ORDER BY … COLLATE "C"` and `LIMIT` stay in one SELECT; the
   support read keyed by `fact_id = ANY(:fact_ids)` is one statement.
3. Expressible: `WITH RECURSIVE reach … UNION SELECT … FROM (… UNION ALL … UNION ALL …) AS edges
   JOIN reach ON …` with exactly one recursive reference.
4. `CreateTable` text equals the frozen 0027 text for `data.identity_exclusion` and
   `data.identity_exclusion_evidence` after whitespace normalization.
5. `make_conninfo(url, user=…, application_name=…)` yields a keyword/value conninfo with the
   overridden user; `conninfo_to_dict` parses it.
6. `psycopg.sql` renders with `as_string(None)` (no connection): `Identifier` always quotes
   (`"sp_fact"`), `Literal` doubles quotes. SQLAlchemy's `identifier_preparer.quote` quotes only
   when required (`sp_fact`, `"Mixed"`), which matches the existing frozen transport spelling.

## Limits

- Compile-only. Nothing here establishes that PostgreSQL accepts, plans or executes these statements
  efficiently, nor any timing. Q3's planner behaviour (parameterized pushdown into the `UNION ALL`
  branches) is unverified.
- Q4 compares two tables of one revision; it does not establish parity for every revision, for
  CHECK/index/grant/function text or for the transport routine.
- Under the psycopg dialect, binds against `Text` columns render a `::VARCHAR` cast; harmless for
  equality/ordering by PostgreSQL's implicit cast, but noted.
- Q5 does not test whether the ADBC driver accepts keyword/value conninfo (owned elsewhere).
