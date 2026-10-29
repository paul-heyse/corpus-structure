# Operator and engineering workflows

Opportunities in the SP-09 regeneration command path, runtime principal selection, the native
test harness and the qualification route. Where the [test audit](../../design_review/test-audit/README.md)
already diagnosed the cause, the opportunity links that finding and frames only the capability that
could own it. Baseline, scope and labels are in the [README](README.md). Paths are relative to
`python/corpus-structure/src/corpus_structure/` unless they start with `python/`, `docs/`,
`scripts/` or `justfile`. Line numbers cite the reconciled tree at `f697233`.

Strengths that bound these opportunities:
- `scripts/pg_semantic_roles.sh` is idempotent, self-verifying and fails safe. Shell is the right
  tool for that provisioning.
- `semantic/migrations.upgrade(connection, target)` runs on the caller's connection and accepts a
  target.
- The settings factory is lazy, so `--help` never touches the database.
- ADBC uses the bundled driver by default; `analytics.adbc_driver_path` (`settings.py:73`) is an
  optional override.
- The native test harness authenticates real restricted logins and fails rather than skips when
  infrastructure is missing.

<a id="cbo-004"></a>

## CBO-004 — The SP-09 regeneration path has no command route, and restricted principals exist only in tests

**Label:** accepted planned (SP-09). **Altitude:** operator workflow.

**Operation and consumer.** [SP-09](../../plans/semantic-model-pivot/regeneration-and-acceptance.md#SP-09)
requires a reproducible path: prepare release → bootstrap → ingest → extract → consolidate/derive →
serve → evaluate. It also requires that CLI, MCP and run defaults all move to the new realization at
cutover, that interruption leaves the current default intact, and that source and release
dependencies are recorded. The consumer is the operator.

**Current mechanism.**
- **The operational bootstrap is run by hand.** It is a `uv run python` sequence: `upgrade` →
  `persist_release` → `activate_release` → `load_release` (pivot coordinator §8). Its receipts are
  prose.
- **`ci db init/migrate` targets the legacy store.** It runs `core.db.migrations`, not
  `semantic_alembic`.
- **No command admits a release.** `ci project init --semantic-release` requires "an already
  admitted semantic release" (`cli/orchestrate.py:101`), and no command admits one. Composing the
  release is [CBO-002](release-preparation.md#cbo-002).
- **Principals are selected only in tests.** `Settings` has one `database.url` (`settings.py:35`).
  The restricted writer, reader and publisher principals are selected only in tests, via
  `url.set(username=…)` in `python/corpus-structure/tests/semantic/conftest.py`. Production code
  carries the role names only as constants (`semantic/routines.py:81-83` and admission checks).
- **The semantic MCP server opens the legacy store** (`intervene/semantic_server.py:186-191`).
- **Default selection at cutover is spread out.** It is distributed over parallel `*_bound_*`
  command functions and `--semantic` flags in `orchestrate/commands.py`, `cli/orchestrate.py` and
  `cli/status.py`.

**Why it matters.** SP-09's completion conditions — a reproducible path, no partial selection,
consistent defaults — are currently satisfied by hand and recorded as prose.
[CBO-007](consumers-and-operations.md#cbo-007) shows the same gap for analytics: connection
derivation does not transfer from the production engine.

**Patterns.** LOP-12, LOP-08 (engine and principal lifecycle), LOP-09.

**Preservation constraints.**
- [ADR-0025](../../adr/0025-semantic-publication.md): frozen Alembic history and definer-owned
  staging.
- The main 5432 cluster of other projects is never touched, and the old database stays untouched
  until disposal is scoped.
- Interruption keeps the current default; restart uses release and batch identities.
- The SP-08 text says not to create another CLI parser merely because Settings offers one. Typer
  stays under `cli/`.

**Counterevidence.** There is a single operator. The plan says no general hot-upgrade or recovery
framework is needed.

**Research leads.**
- [typer](../../libraries/typer.md): sub-app composition.
- [pydantic-settings](../../libraries/pydantic-settings.md): nested per-principal sections.
- [psycopg-pool](../../libraries/psycopg-pool.md) and [sqlalchemy](../../libraries/sqlalchemy.md):
  one engine per principal composed with the single-pool rule.
- [alembic](../../libraries/alembic.md): the command API is already wrapped.

**Questions for library research.**
1. How should Settings model distinct publisher, writer and reader connections, and should each
   command declare the principal it needs?
2. Can prepare → persist → activate run as one refusal-safe command whose failure leaves the
   selection unchanged?
3. How does the ADBC capture connection derive from the same principal configuration?

**Library assessment (2026-10-29).** The publisher is `NOLOGIN`, so it is not a connection principal. Since `3d97504`, `connection_settings(settings, purpose)` derives write/read/evaluate/maintenance URLs. `NullConnectionPool` behind SQLAlchemy is ruled out at psycopg-pool 3.3.3 ([psycopg](../libraries/psycopg/README.md#applicability-cbo-004), [pydantic-settings](../libraries/pydantic-settings/README.md#applicability-cbo-004)).

<a id="cbo-010"></a>

## CBO-010 — Native test databases have no reusable migrated template or revision-pair route

**Label:** current; accepted planned (SP-10 native union and physical evolution). **Altitude:**
engineering subsystem.

**Diagnosis owner.** [DTA-002](../../design_review/test-audit/execution-and-qualification.md#dta-002):
each native test bootstraps to head through 26 revisions, no revision-pair route exists, and no
owner reclaims leftover databases. This entry frames only the capability that could own those
responsibilities.

**Operation and consumer.**
- Provide each native test with a fresh, isolated database at a declared revision, cheaply.
- Provide a route from revision N−1, with data loaded, to N.
- Reclaim leftover databases.

The consumers are developers, the SP-08 consumer tests and the SP-10 qualification union.

**Capability candidates.**
- PostgreSQL's native `CREATE DATABASE … TEMPLATE`, which the harness already uses against the bare
  template, applied to a migrated head template built once per session.
- `migrations.upgrade(conn, target)` for revision pairs.
- pytest-postgresql 9.1.1 as a complete harness:
  - `postgresql_noproc` against the existing cluster;
  - session-level template population with per-test cloning (overview §2.2, §4);
  - hierarchical templates through `depends_on` (§5);
  - `DatabaseJanitor` cleanup.

  See [pytest-postgresql](../../libraries/pytest-postgresql.md). Another agent researched it during
  this audit.

**Patterns.** LOP-07, LOP-08, LOP-12.

**Preservation constraints.**
- Tests authenticate as restricted roles.
- A template may have no connections while it is being cloned.
- The template key must cover every premise: revision `.py` and `.sql` files, extension versions
  and role state. DTA-002 shows that copying the legacy hash would go stale.
- Bootstrap from bare stays for migration tests.
- Legacy precedents: [DA-018](../../design_review/audit/boundaries-and-composition.md#da-018) and
  [DA-019](../../design_review/audit/boundaries-and-composition.md#da-019).

**Questions for library research.**
1. Does pytest-postgresql's noproc mode compose with restricted-role logins and a migrated template
   on the shared 5434 cluster?
2. Can its template key include the full revision directory and role state?

**Library assessment (2026-10-29).** **Premise failure.** `CREATE DATABASE … TEMPLATE` does not copy database-level grants. Revisions 0003 and 0007 revoke `TEMP` from `PUBLIC` at that level, so a cloned head template would re-grant TEMP to every role. Any template route must replay the database ACL after cloning ([LOP-X007](../assessment-patterns.md#lop-x007)). The template key must also cover the role inventory: a fourth role exists, and revisions now number 28 ([postgresql](../libraries/postgresql/README.md#applicability-cbo-010)).

<a id="cbo-011"></a>

## CBO-011 — The qualification route cannot classify outcomes for the required union

**Label:** current; accepted planned (SP-10). **Altitude:** engineering workflow.

**Diagnosis owner.** [DTA-003](../../design_review/test-audit/execution-and-qualification.md#dta-003):
the route turns empty Rust suites, skips and hangs into success or silence, and runs randomized
generated cases. This entry frames only the capability that could own outcome classification.

**Operation and consumer.**
- Record each required obligation as passed, failed, blocked or not_run.
- Make hangs observable.
- Make generated cases replayable.
- Record provider context.

The consumer is the SP-10 assembled qualification.

**Capability candidates.**
- pytest's built-in JUnit XML and `-r` skip reporting.
- Per-test timeouts; pytest-timeout is not declared and has no overview page.
- An explicit Hypothesis profile selection in the route ([hypothesis](../../libraries/hypothesis.md)).
- nextest without `--no-tests=pass`.

Current configuration: `pyproject.toml` `[tool.pytest.ini_options]` (`-q`) and the `justfile`
`check`, `test-all` and `py-test` recipes.

**Patterns.** LOP-12, LOP-03 (built-in reporting unused).

**Preservation constraints.**
- Repository reporting vocabulary (passed / failed / blocked / not_run, each with its command).
- No new alignment lint.
- Infrastructure failures must keep failing rather than skipping.

**Questions for library research.**
1. Which built-in pytest output records skip reasons and per-test outcomes faithfully enough to
   account for the union?
2. Is a timeout plugin needed, or does an existing facility bound hangs?

**Library assessment (2026-10-29).** pytest-timeout's `signal` method conflicts with the math grammar's `SIGALRM` deadline. faulthandler-exit makes a hang observable but writes no JUnit file. `--hypothesis-profile=ci` overrides the conftest default ([pytest](../libraries/pytest/README.md#applicability-cbo-011), [hypothesis](../libraries/hypothesis/README.md#applicability-cbo-011)).
