# Design-principle audit probes: native privileges, enforcement, schema parity and native semantics

**Purpose.** Settle native-integrity premises for the
[design-principle audit](../../audit/README.md) refreshed on 2026-10-29. The questions concern what
the database itself enforces at the head revision, as distinct from what the code or design text
says.
- **P1:** what each restricted principal can do at head (table, schema, function and database
  privileges), which tables carry refusal triggers, and how SECURITY DEFINER functions are
  configured.
- **P2:** whether `corpus_sem_publisher` can INSERT into `sem.*`. An earlier tree ran release
  persistence under `SET LOCAL ROLE corpus_sem_publisher`.

## Environment

- Dedicated PostgreSQL 18 cluster `18/corpus` on port 5434, server 18.6. Connected through the
  maintenance principal (`connection_settings(settings, "maintenance")`, login `paul`).
- Source `ad4593f` (clean tree), Python 3.14.10.
- One throwaway database named `cs_sem_probe_<pid>_<hex>_a`, created from `cs_template` and
  upgraded through `semantic.migrations.upgrade` to `semantic_0030` (head). Afterwards it was
  dropped with a plain `DROP` and retry. The operational databases and port 5432 were not touched.

## Command

```bash
cd python/corpus-structure
uv run --no-sync python ../../docs/design_review/evidence/2026-10-29_design-principle-audit-probes/probe_catalog.py \
  > ../../docs/design_review/evidence/2026-10-29_design-principle-audit-probes/catalog.json
```

Raw output is in [catalog.json](catalog.json); stderr was empty
([catalog.stderr.txt](catalog.stderr.txt)). The probe is read-only apart from creating, migrating
and dropping its own database. It reports a residue count, which was 0.

## First probe: privileges and enforcement (passed, both questions answered)

**P2. The publisher cannot write `sem.*`.**
- All 14 `sem.*` tables are owned by the operator login `paul`.
- Every restricted role, the publisher included, holds only `SELECT` on them; schema `sem` grants
  `USAGE` only.
- The operator is a member of `corpus_sem_publisher` with `SET` but without `INHERIT`.

So release persistence works only under the operator/owner login. At `ad4593f`, `ci regenerate`
calls `persist_release` without `SET ROLE`
(`python/corpus-structure/src/corpus_structure/cli/regenerate.py:80-82`), and it sets the
publisher role only for the selection CAS (`:146`).

**P1. Privileges and enforcement at head:**

| Observation | Value |
|---|---|
| Tables in `sem`, `data`, `ops`, `eval`, `kb` | 71: 59 owned by the operator, 18 by `corpus_sem_publisher` (9 `data`, 7 `eval`, 2 `ops`) |
| Publisher table privileges beyond SELECT | `data`: INSERT 30, UPDATE 29, DELETE 10, TRUNCATE 9 · `eval`: INSERT, UPDATE, DELETE, TRUNCATE 7 each · `kb`: INSERT 6, UPDATE 5 · `ops`: INSERT 14, UPDATE 12, DELETE 2, TRUNCATE 2 |
| Writer table privileges beyond SELECT | INSERT on 7 `ops` and 4 `kb` tables; nothing on `data` or `sem` |
| Reader, evaluator | SELECT only |
| Tables with a BEFORE UPDATE refusal trigger | 13: `data.assessment`, `entity_input`, `fact_input`, `project`, `realization`; `ops.completed_result`, `measurement`, `method`, `run`, `run_rendition`, `source_frame`, `source_frame_sentence`, `task`. Some of these are lifecycle guards, not immutability refusals |
| `sem` and `data` tables without any BEFORE UPDATE trigger | 39 of 44 |
| Functions in these schemas | 90. 53 are SECURITY DEFINER, all owned by `corpus_sem_publisher`, all with a `search_path` setting; none is executable by PUBLIC |
| Database TEMP | publisher yes, writer yes, reader no, evaluator no |
| Default privileges | none |
| Schema CREATE | publisher on `data`, `ops`, `eval`, `kb` |

## Second probe: schema parity and native semantics

[probe_parity_semantics.py](probe_parity_semantics.py), run on 2026-10-29 at source `ad4593f`.
- **Databases.** It creates two throwaway databases from `cs_template`:
  - one upgraded to head (`semantic_0030`) through `semantic.migrations.upgrade`;
  - one given the five schemas and `metadata.create_all` from the shared MetaData.
- **Comparison.** Their catalogs are compared on columns (type, nullability, default), constraints
  (definition and name) and indexes (definition with the name blanked).
- **Native calls.** The function checks run under `SET LOCAL ROLE corpus_sem_publisher`, because
  the operator login holds no EXECUTE on them. That is itself consistent with the privilege model.
- **Output.** Raw output is in [parity_semantics.json](parity_semantics.json). Stderr holds only
  SQLAlchemy's FK-cycle sort warning ([parity_semantics.stderr.txt](parity_semantics.stderr.txt)).
- **Residue:** 0.

**P3. At head, a fresh migrated schema equals the MetaData body for body; the drift is in names.**
- **Columns:** 471 against 471, with identical type, nullability and default.
- **Indexes:** 112 against 112, with identical definitions.
- **Constraints:**
  - 729 against 727. The difference is exactly the two native deferrable constraint triggers on
    `ops.run`: `completed_result_required` and `run_evaluation_atomic` from revision 0023. That is
    expected. No other constraint definition is present on one side only.
  - **69 constraints have the same definition under a different name.** The hand-written revision
    SQL mostly carries PostgreSQL default names (`alternative_group_pkey`, `…_fkey`, `…_check`).
    The MetaData naming convention produces `pk_…`, `fk_…` and `ck_<table>_physical_<digest>`.
- **Alembic's configured check:** 49 operations (24 `remove_constraint`, 24 `add_constraint`,
  1 `modify_default`). This is the same count the comparative review saw at `semantic_0029`.

This comparison covers fresh databases only. A database built from an earlier text of an edited
revision would differ, and no check on a long-lived database exists.

**P4. Python and native canonical JSON disagree on non-integer numbers.**
- Input: `[1e-05,1.0E2,-0.0,0.1,12345678901234567890.5]`.
- Native `data.canonical_json` gives `[0.00001,100,0.0,0.1,12345678901234567890.5]`.
- Python `canonical_bytes` gives `[1e-05,100.0,-0.0,0.1,1.2345678901234567e+19]`.

The two agree only on the subset the producers currently emit: strings, integers, booleans and
null, with decimals carried as strings or `{"decimal": …}` objects.

**P5. Native locator whitespace normalization differs from Python's.**
- Native `regexp_replace(normalize(s,NFC),'[[:space:]]+',' ','g')` was run under the database
  locale (provider `c`, `C.UTF-8`). Python is `core.locators.normalize`.

| Character | Native | Python | Equal |
|---|---|---|---|
| NBSP (U+00A0) | not collapsed | collapsed to a space | no |
| NEL (U+0085) | not collapsed | collapsed | no |
| File separator (U+001C) | not collapsed | collapsed | no |
| Ideographic space (U+3000), em space (U+2003), tab | collapsed | collapsed | yes |
| Zero-width space (U+200B) | kept | kept | yes |

**P6. An untrusted decimal lexical with a huge exponent is not refused.**
- `data.decimal_canonical('1e400000000')` raises SQLSTATE `XX000`, "invalid memory alloc request
  size 3200000008".
- `'1e2147483648'` raises `22003`, "integer out of range".

Neither is the refusal class `23514`.

## Limits

- The probe establishes privileges and trigger presence. It does not establish trigger semantics
  (whether a trigger refuses or merely guards a transition) or row-level behaviour. The audit reads
  the trigger functions for that.
- It covers fresh databases at head only. A long-lived database migrated through earlier revisions
  can differ, for example through the in-place edits the audit discusses.
- It does not cover column privileges or RLS (no policies exist), and it does not cover the
  legacy `alembic` tree.
