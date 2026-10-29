# Library leverage R2 — Alembic offline rendering and pytest route classification

**Interface-checked / probe-observed, 2026-10-29.** Two pure-Python probes supporting the first
`leverage-library-assessment` pass (cluster R2: PostgreSQL native capability, migrations and test
harness). Neither probe connects to a database, installs anything or uses a network service.
They settle two narrow interface questions; they are not application tests and make no
performance claim. No evidence record has been written; the coordinator decides whether a record
is warranted.

Environment: Python 3.14.10 via `uv run --no-sync python`, from the repository root, at source
`3d97504` (which includes the concurrent `4de601c` SP-08 revision `semantic_0028`). Library
realizations: Alembic 1.20.0, SQLAlchemy 2.1.5, pytest 9.2.0, Hypothesis 6.170.12.

## Probe 1 — Alembic offline rendering of the semantic MetaData

```sh
PYTHONHASHSEED=0 uv run --no-sync python docs/design_review/evidence/2026-10-29_library-leverage-postgres-migrations/alembic_offline_probe.py
PYTHONHASHSEED=1 uv run --no-sync python docs/design_review/evidence/2026-10-29_library-leverage-postgres-migrations/alembic_offline_probe.py
```

**Questions.** (A) Which MetaData properties fall outside what Alembic 1.20 autogenerate compares?
(B) Can Alembic `Operations` in offline mode (`MigrationContext.configure(dialect_name="postgresql",
opts={"as_sql": True, "output_buffer": …})`, no connection) render a MetaData table as SQL, and
does that text match the frozen revision SQL for the same table?

**Outcome** (`raw/alembic_offline_probe_hashseed{0,1}.txt`):
- MetaData has 69 tables in `data, eval, kb, ops, sem`; every table that frozen SQL creates (41)
  exists in MetaData, so no SQL-only table would surface as a spurious `remove_table`.
- Two partial indexes (`postgresql_where` on `data.typed_value`) and one GIN expression index
  (`kb.rendition`). Installed-source inspection of `alembic/ddl/postgresql.py`
  (`compare_indexes`, `_dialect_options`) shows 1.20 compares index uniqueness, expressions and
  only `postgresql_nulls_not_distinct`; `postgresql_where`, `postgresql_using` and
  `postgresql_include` are not compared. The partial-index names do not embed their predicate.
- Offline `Operations.invoke(CreateTableOp.from_table(t))` renders `data.identity_exclusion` with
  exactly the same column and constraint lines as the frozen `semantic_0027_exclusions.sql`, but
  in a different constraint order; the order also differed between processes (an earlier unseeded
  run produced `pk, ck_…b87f…, fk_…right…, uq_…, ck_…5b61…, fk_…left…, fk_…observation…, ck_…f8ed…`;
  both seeded runs produced `pk, uq, ck_…5b61…, fk_…right…, ck_…f8ed…, fk_…observation…, fk_…left…, ck_…b87f…`).
  `PYTHONHASHSEED` does not control it (object identity ordering of `Table.constraints`).
  SQLAlchemy's own `CreateTable(t).compile(postgresql)` is whitespace-normalized equal to the
  frozen text (reference only; the DDL compiler is another cluster's subject).

**Limits.** One table compared. No reflection, `compare_metadata`, `produce_migrations` or
`command.check` was run: all three need a live connection, which probes here may not open. What a
head-migrated database would report remains unsettled.

## Probe 2 — pytest/Hypothesis outcome classification on a route

```sh
uv run --no-sync python docs/design_review/evidence/2026-10-29_library-leverage-postgres-migrations/pytest_route_probe.py
```

The driver runs `python -m pytest` in `pytest_cases/` with its own `-c` ini files (so the
repository's pytest configuration is not used) and `HYPOTHESIS_PROFILE` removed from the
environment. `outcomes/conftest.py` registers `ci` (derandomized, `print_blob`) and `dev` and loads
the profile from an environment default at import, mirroring the repository's pattern.

**Outcome** (`raw/pytest_route_probe.txt`, per-run stdout and JUnit files in `raw/`):
1. Built-in `--junitxml` records every test with a per-test outcome; the `skipped` element carries
   the skip reason text (`blocked: …`); a Hypothesis failure under `ci` carries the
   `@reproduce_failure('6.170.12', b'…')` blob in the failure text. Under the env-default `dev`
   profile no blob appears. Hypothesis also adds `hypothesis-statistics-<nodeid>` global
   properties to the JUnit file.
2. `--hypothesis-profile=ci` overrides the profile the conftest loaded from the environment at
   import (`test_profile_visible` passes only in that run).
3. With built-in `faulthandler_timeout = 2` and `faulthandler_exit_on_timeout = true`, a hung test
   ends the process with exit code 1 and a traceback naming the hung test; later tests do not run
   and **no JUnit file is written**.

**Limits.** Synthetic cases only; the repository suite was not run. pytest-timeout was not
installed or exercised (its documented behavior is cited in the assessment, not observed here).
Hypothesis wrote a `.hypothesis/constants` cache in `pytest_cases/` even with `database=None`;
it was deleted after the run.

## Files

- `alembic_offline_probe.py`, `pytest_route_probe.py` — probe drivers
- `pytest_cases/probe.ini`, `pytest_cases/hang.ini`, `pytest_cases/outcomes/conftest.py`,
  `pytest_cases/outcomes/test_outcomes.py`, `pytest_cases/hang/test_hang.py` — synthetic cases
- `raw/` — captured outputs: `alembic_offline_probe_hashseed0.txt`,
  `alembic_offline_probe_hashseed1.txt`, `pytest_route_probe.txt`, `profile_ci.stdout.txt`,
  `profile_default.stdout.txt`, `hang_faulthandler_exit.stdout.txt`, `junit_profile_ci.xml`,
  `junit_profile_default.xml`
