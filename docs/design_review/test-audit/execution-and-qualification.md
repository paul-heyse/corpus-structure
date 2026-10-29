# Execution, isolation and qualification

Findings about test resource lifecycle, repeated preparation, replay and the route that turns
test results into qualification evidence: FP-05, FP-06, FP-07/A4, DP-09/10/19/20/21, CI-04 and
CI-10 by analogy, and [companion](../design_principles/core/test-assessment.md) §6 and §8.
Baseline, scope and method are in the [README](README.md). Paths are relative to
`python/corpus-structure/` unless they start at the repository root.

The native semantic harness has solid foundations, and they bound any remedy:
- It authenticates real restricted logins instead of using `SET ROLE` (`tests/semantic/conftest.py:73-92`).
- It uses `NullPool` engines and unique database names (`cs_sem_test_<pid>_<uuid12>`).
- Missing roles, a missing template or a wrong extension make a test fail with a remediation
  message rather than skip (`:45-46`, `:49`).
- It refuses a template that already has application schemas (`:51-53`).
- Its drop retry is narrow and re-raises (`:56-70`), and it avoids `DROP … WITH (FORCE)`, unlike the legacy
  harness ([Q4-01](../../plans/phase-0_2026-10-28.md#11-findings-disposition)).

The legacy harness already reuses preparation: a migrated template behind an advisory-lock lease,
with a liveness-respecting sweep (`tests/conftest.py:238-318`). Its key premises have their own
findings, [DA-018](../audit/boundaries-and-composition.md#da-018) and
[DA-019](../audit/boundaries-and-composition.md#da-019).

<a id="dta-002"></a>

## DTA-002 — The native semantic harness fuses isolation, head bootstrap and migration-as-subject in one per-test fixture

**Principles:** FP-07/A4, FP-01, FP-03, DP-10, DP-19; H2, H12, H19, H20, H27; companion §6, §8.
**Subject:** implemented (`tests/semantic/conftest.py:23-70`; module helpers such as
`tests/semantic/test_operations.py` `setup`, `tests/semantic/test_query.py` `seed`).

**Diagnosis.** For every native semantic test, the one function-scoped fixture
`semantic_db_engine` does all of the following:
1. creates `cs_sem_test_<pid>_<uuid12>` from the bare `cs_template`;
2. checks the extensions and asserts there are no application schemas;
3. runs `semantic.migrations.upgrade` to head (`conftest.py:54`): 26 revision modules under
   `semantic_alembic/versions/`, which also execute their sibling SQL files;
4. drops the database afterwards.

Three distinct responsibilities are fused here:
- **(a) A fresh, uniquely owned database.** Most native claims really need this: they use real
  commits, separate restricted logins, SERIALIZABLE races and lost-commit cases. The legacy `db`
  fixture's rolled-back outer transaction could not serve them.
- **(b) Bootstrap to head.** This is the same stable preparation on every use.
- **(c) Migration as the thing under test.** It is the claim only in `tests/semantic/test_migrations.py`.

Everywhere else, (b) repeats an unchanged conclusion (H20) instead of being prepared once while its
premises hold (H12, H19). The test helpers then add per-test release preparation, persistence and
project/realization setup. Because they use constant identities, they tie isolation to the
database:
- `project_id="p"` and `realization_id="z"` in `test_operations.py` `setup`;
- `Z="realization:query"` in `test_query.py`.

The same fusion explains a missing capability. The fixture always yields a head-revision database,
and no test upgrades from an intermediate revision with data in place. A search of `tests/` for
`semantic_00NN` revision ids and targeted `upgrade(conn, target)` calls found none; the production
`upgrade(connection, target)` (`src/corpus_structure/semantic/migrations.py:36`) accepts a target
but no harness route uses one. The SP-10
["Physical evolution"](../../plans/semantic-model-pivot/regeneration-and-acceptance.md#SP-10)
evidence needs a "fresh bootstrap and controlled physical revision". With today's harness, the
only revision evidence is "head from empty", which an incorrect incremental migration passes.

**Consequence.**
- **Execution and maintenance amplification grows as revisions × native tests.** At T0 a static
  count found about 214 of the 447 collected semantic items, in 32 modules, depending on the
  fixture directly or transitively; for example, all 25 items in `test_execution_release` and in
  `test_domain_operations`. Every new revision (scenario SC1) adds bootstrap work to all of them,
  and later pivot packages add native tests to the same fixture. This is demonstrated repeated
  work; it is not a measured bottleneck.
- **The controlled-revision evidence SP-10 requires has no harness route.**

**Footprint.**
- *Known:* the fixture and helpers cited above. The 214-item count is a static AST count of
  fixture dependencies and parametrize lengths at T0. Revision count at T0 and at reconciliation:
  26.
- *Inferred:* the revision count is still growing; all 26 revision files were added on
  2026-10-29.
- *Suspected:* none beyond the above.

**Lifecycle residue (secondary, same harness).**
- Cleanup is only the fixture's `finally`. The docstring states that there is deliberately
  "no legacy migration or sweeper", and the legacy sweep does not cover `cs_sem_test_*`.
- So a killed or hung run (compare [I2A-01](../../plans/phase-0_2026-10-28.md#11-findings-disposition))
  leaves its database behind. Residue is checked by hand at closeouts (pivot coordinator §8:
  "No owned `cs_sem_test_*` databases remain").
- A read-only catalog query on the 5434 cluster at 2026-10-29T13:36-04:00, with no pytest running,
  found no `cs_sem_test_*` database. It also found no stray agent clone (`ci_test_<pid>_agent_*`)
  and 15 retained legacy `cs_tpl_*` templates, which the legacy harness keeps by design.
- So residue is a structural exposure, not an observed accumulation.

**Counterevidence.**
- The only measurement is one test at an earlier head, from the
  [SP-06 execution-fit evidence](../evidence/2026-10-29_sp06-execution-fit/README.md): about
  0.10 s of migration and about 0.05 s of `CREATE DATABASE` against a 2.69 s test body. Per-test
  bootstrap was therefore small for that test. The suite-wide share is unmeasured.
- The PostgreSQL plan asks for "uniquely owned fresh extension-only databases … frozen Alembic
  deployment" (`docs/plans/semantic-model-pivot/postgresql-and-publication.md`). Whether a fresh
  clone of a template built by the same frozen deployment satisfies that is an operator
  interpretation, and it is open.

**Uncertainty.** That interpretation. Optionally, one timing of the setup phase across
`tests/semantic` at the current head would show the suite-wide share; no timing was taken.

**Leads (optional).**
- Prepare the head bootstrap once per session and clone it per test. Keep bootstrap from bare for
  migration tests, and add a revision-pair route for controlled revisions.
- Any reused template must key on every premise: the `.py` and `.sql` revision files, extension
  versions and cluster role state. The revisions read sibling SQL files and set roles (for example
  `semantic_alembic/versions/0014_entity_input_lineage.py`). A key copied from the legacy hash
  (`tests/conftest.py:138-148`, [DA-018](../audit/boundaries-and-composition.md#da-018)) would go
  stale on SQL-only or role changes.
- A lease or sweep could give residue an owner (compare
  [DA-019](../audit/boundaries-and-composition.md#da-019) on the legacy sweep's own races).

**Bears on:** SP-10 physical-evolution evidence; every later native test package; developer
iteration on focused native tests.

<a id="dta-003"></a>

## DTA-003 — The qualification route cannot separate required passes from skipped, blocked, hung or unreplayable outcomes

**Principles:** FP-05, DP-21, DP-22, CI-04 and CI-10 by analogy; companion §6.
**Subject:** implemented (`justfile` recipes `check`, `test-all`, `test`, `py-test`;
`pyproject.toml` `[tool.pytest.ini_options]`; `tests/conftest.py:69-99`).

**Diagnosis.** `just test-all` is `just check`, which runs `cargo nextest run --release
--workspace --no-tests=pass` and then a bare `uv run pytest` (`justfile:14-17`, `:61-62`, `:79-80`).
It is the route the repository uses for integrated functional acceptance. The SP-10 plan requires
that each required obligation be recorded as `passed`, `failed`, `blocked` or `not_run`, and that
an unavailable required obligation stay open
([regeneration-and-acceptance](../../plans/semantic-model-pivot/regeneration-and-acceptance.md#SP-10)).
The route loses that information in several independent ways.

**1. Zero Rust tests report as a pass.**
- `--no-tests=pass` turns an empty Rust suite into success. The crate is a stub with no tests.

**2. Skips fold into a count.**
- pytest runs with `-q` and default report characters, so skip reasons never reach the summary and
  the run exits 0.
- The skip conditions include:
  - missing `pyrefly` (`tests/core/test_method.py:233`);
  - missing `linkml-lint` (`tests/schema/test_model.py:53,59`; `tests/schema/test_packs.py:127`);
  - the `corpus` marker (`tests/conftest.py:93-99`), which skips when `docs/statistics_corpus` is
    absent. That directory is git-ignored, so in any fresh checkout or worktree the seven
    corpus-gated tests skip silently (ingest, math, llm, fixtures and agent modules).

**3. A hang yields no outcome.**
- There is no per-test timeout (no pytest-timeout configured).
- A hung test, as recorded in [I2A-01](../../plans/phase-0_2026-10-28.md#11-findings-disposition),
  produces neither `failed` nor `blocked`.

**4. Generated cases are not replayable from the route.**
- Hypothesis profiles `ci` (derandomized, `database=None`, `print_blob`, 300 examples) and `dev` are
  registered. The profile comes from `HYPOTHESIS_PROFILE` (`tests/conftest.py:69-73`), and no
  recipe or `.envrc` sets it.
- Qualification therefore runs `dev`: randomized, using the local example database and no blob
  printing. Two qualification runs on the same tree exercise different generated cases, and a
  generated failure cannot be replayed from the route's output.

**5. Provider context is ambient and unrecorded.**
- For example, the PostgreSQL → ADBC journey takes the driver from `Settings()` and the environment
  (`tests/semantic/test_columnar_journey.py`).
- The pivot receipts had to state the explicit driver path by hand (coordinator §8).

**6. No selection unit exists for the native union.**
- `DB_FIXTURES` (`tests/conftest.py:75`) does not include the semantic fixtures. The automatic `db`
  marker therefore misses every native semantic item, and `-m "not db"` would still run them.
- The marker has no consumer in any recipe.

**Consequence.**
- Required evidence can be absent while the route reports success.
- Generated outcomes differ between qualifying runs.
- A failure, hang or skip cannot be classified or replayed from the route's output alone.
- The SP-10 union will have to reconstruct by hand what the route discards, as the pivot receipts
  already do.

**Footprint.**
- *Known:* the recipes, configuration and markers cited above.
- *Suspected:* tier-2 property tests that run DuckDB per example (`tests/pool/test_engines.py`
  `@given` cases) may hit the `dev` profile's default deadline on a loaded host (not observed).
- *Suspected:* `tests/math/test_grammar.py:366` asserts a tight wall-clock bound that is itself the
  claim; its margin under contention is unverified.

**Counterevidence.**
- Server, template, extension and role problems fail rather than skip, with remediation text.
- Skip reasons are honestly labelled `blocked:`.
- `tests/semantic` has no skips, environment reads or `@given` tests (search over that directory).
- Wall-clock asserts in `tests/db/test_store.py:42`, `tests/agent/test_tools.py:417` and
  `tests/orchestrate/test_liveness.py:91` have generous margins.

**Related.**
- [DA-022](../audit/local-reasoning-and-assurance.md#da-022) is a sibling overclaim in `just deps`;
  its cause is distinct.
- [I2A-01](../../plans/phase-0_2026-10-28.md#11-findings-disposition) owns the math pool hang.
  This finding owns only the route's inability to report it.

**Bears on:** SP-10 required-union accounting; any qualification receipt citing `just test-all`.
