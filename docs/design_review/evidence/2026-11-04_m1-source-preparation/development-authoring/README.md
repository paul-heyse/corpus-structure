# Persistent development operation

**Tested,2026-11-04.** Operator direction replaces the mandatory disposable workflow.
The dedicated18/corpus operator login paul now has SUPERUSER/CREATEDB/CREATEROLE. The retained
source archive was restored directly as that operator into persistent corpus_structure_dev.
The database is retained for implementation; it is not a test disposal target.

Actual normal connections passed for maintenance, write, read, admit, evaluate and fit.
The reader sees all11 retained source views. Native revision is semantic_m1_preparation_20261104.
The first handwritten inventory query used a nonexistent migration-table name; the normal
current_revision operation corrected that query. This was not a permission failure.

`uv run ci schema native-candidate --out docs/design_review/evidence/2026-11-04_m1-source-preparation/development-authoring/attempt-001 --json`
passed against the configured persistent database with zero native and zero ordinary changes;
its candidate transaction rolled back. [attempt-001](attempt-001/native_operations.json) retains
all133 desired managed objects. Existing source data remains available.

`uv run ci db check --release release:3713a45c7097314fc5958b92baf814b314fdc46c5c8f031f016e177f4265efbe --json`
passed through the normal reader/native correspondence route. `just ready` passed after the
permission/environment change. Scoped CLI/settings tests passed26cases; shell syntax, typing
and lint checks passed. This qualifies the development workflow, not M1 family quality.

ADR-0056, D3 and AGENTS.md own the resulting requirements. The original native99 database remains
available. Historical isolated-database attempts stay retained with their actual failures/results.
