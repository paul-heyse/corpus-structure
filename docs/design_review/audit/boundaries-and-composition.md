# Boundaries and composition

Findings about library and infrastructure boundaries, configuration and lifecycle: FP-01–FP-03,
FP-05, DP-01, DP-09, DP-15 and DP-19–DP-20. Baseline, scope and scenarios are in the
[README](README.md).

The product code's own boundaries hold up:
- `core` imports only the standard library, Pydantic and `regex`, and its modules depend on each
  other acyclically.
- Settings take their environment as an argument.
- The CLI builds settings lazily, and its planned groups say honestly that they are not built.

No finding here concerns the module structure.

<a id="da-018"></a>

## DA-018 — Server extension versions are neither pinned nor reconciled, and the test template ignores them

**Principles:** DP-15, DP-09, DP-21, FP-05.
**Subject:** implemented (`scripts/pg_provision.sh`, `python/corpus-structure/tests/conftest.py`);
accepted target (D3 §1, §3).

**Diagnosis.** D3 names pg_textsearch 1.5.1 and vector 0.8.7, and its BM25 answer relies on
version-specific behaviour (the silent fallback when the index predicate is omitted). Yet no part
of the system records or checks those versions:
- Provisioning runs `CREATE EXTENSION IF NOT EXISTS` and never `ALTER EXTENSION … UPDATE`
  (`pg_provision.sh:74-79`).
- The fixtures' check and the planned 0001 assertion test for presence only (`conftest.py:200-215`).
- The migrated test template `cs_tpl_<hash>` is keyed only on the Alembic versions directory
  (`versions_hash`, `conftest.py:121-130`). A clone keeps serving after `cs_template` is
  reprovisioned or its extensions upgraded.
- `docs/pins.md` has no row for either extension.
- `db-status` labels the `corpus` database's extensions as the template's (`pg_provision.sh:28-30`).

**Consequence.** **S8:** an `apt` upgrade of `postgresql-18-pg-textsearch` changes the server library
under the old extension SQL. Tests keep running on the stale template, and nothing reports what ran.

**Counterevidence.** Package upgrades are deliberate operator actions. Whether the packages are held
with `apt-mark` was not checked.

**Leads:** one record of the expected `extversion`, compared by `ci db` and the fixtures; the
template's extension versions included in the template hash.

<a id="da-019"></a>

## DA-019 — Test-database sweeping can drop a template another live session is using

**Principles:** DP-19, DP-20, FP-05.
**Subject:** implemented (test infrastructure, `conftest.py`).

**Diagnosis.**
- `sweep()` drops every `cs_tpl_*` whose hash differs from the current checkout's
  (`conftest.py:217-230`).
- `clone()` runs `CREATE DATABASE … TEMPLATE` outside the template lock (`conftest.py:249-256`).
- Liveness is checked only for `ci_test_<pid>` databases, and only by local PID.

So a second checkout at another migration head, such as a parallel worktree, which AGENTS.md
permits, can drop the template the first session is cloning from. A session on another host
sharing `CORPUS_DATABASE__URL` has its `ci_test_*` databases swept as dead.

**Consequence.** Migration work in parallel lanes (P0-F-4 onward) gets intermittent fixture failures.

**Counterevidence.** Parallel worktrees are rare, and the lock does serialize template builds
against sweeps.

**Leads:** retention by age or lease rather than "not current, so drop".

<a id="da-020"></a>

## DA-020 — The cluster's coordinates are repeated, and the provisioning prose is stale

**Principles:** DP-01, DP-24.
**Subject:** implemented and design text.

**Diagnosis.**
- **Coordinates repeated.** Port 5434 and the template name are written separately in four places:
  - `settings.py:36-37`;
  - `conftest.py:46-48`;
  - `pg_provision.sh:15-19`;
  - `ops/postgresql/corpus.conf:4`.
- **Prose stale.** D3 §3 still describes manual one-time provisioning steps, and the planned 0001
  assertion message repeats them. Both were superseded by D3 §13's `just db-provision`.

**Consequence:** low, because a mismatch fails loudly.

**Related:** [DA-011](semantic-model-and-authority.md#da-011).
