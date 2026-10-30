# Support structure, composition and domain authority

Findings about where test support lives, what it restates and how tests couple to production artifacts,
to boundaries and to each other. FP-01, FP-02, FP-03, FP-04, FP-06, DP-01, DP-06, DP-17, DP-24, A1/A2/A3,
and [companion](../design_principles/core/test-assessment.md) §2 and §5. Baseline, scope and method are in
the [README](README.md). Paths are relative to `python/corpus-structure/` unless they start at the
repository root.

Several strengths bound the findings below:
- Consumers see an `Engine`, so a change to the lifecycle mechanism concentrates in two conftests and the
  lifecycle's own controls (SC8).
- Real releases now supply native catalogs: `test_publication.py:147-172`, `test_operations.py:114-116`.
- Hostile tests build a valid batch through production and then tamper with it, so the negative input
  reaches the native boundary.
- Fault helpers reach their intended boundaries. `tests/semantic/archive_faults.py` and `snapshot_restore.py`
  restrict targets, pause only named triggers and restore state, and a renamed trigger fails loudly.
- `tests/semantic/test_migrations.py` checks the migrated catalog against declared physical metadata, and
  `test_native_closure.py:313-333` byte-compares derived products with committed revisions.
- Wrap-and-count observations with a positive assertion are sound against route removal
  (`test_occurrence_context.py:225-230`, `test_query.py:459-476`).

<a id="dta-016"></a>

## DTA-016 — Journeys labelled "actual" stop short of the production wire, pool and failure boundary

**Principles:** FP-02, FP-05, FP-06, DP-23; companion §5, §6, §3.
**Subject:** implemented (`tests/semantic/test_runtime_entrypoints.py`, `test_semantic_mcp.py`,
`test_agent_resubmission.py`, `test_source_routing.py`, `test_operations.py`; `tests/test_cli.py`,
`tests/db/test_store.py`; `src/corpus_structure/core/db/store.py`, `src/corpus_structure/cli/status.py`).

**Diagnosis.** Stand-ins are placed at the most consequential boundaries, and the stand-ins' differences
from production are not recorded. Three boundaries share this.

*Connection layer.* Both production and the harness use SQLAlchemy `NullPool`
(`store.py:78-98`; `scripts/native_test_support.py:662`). The difference sits underneath: production draws
from `psycopg_pool` with reused backends, a bounded `max_size`, `check_connection` and the runtime principal
check, while the harness opens a fresh unbounded backend per checkout with none of that.
- Reaching the production layer: `test_runtime_entrypoints.py:37` (one write journey), `test_serving.py:574-684`
  and `test_cli_failures.py:152`, `:196` (reads), `test_interop.py:57-72`, `test_alternate_principal.py:67`,
  `tests/acceptance/test_regeneration.py`.
- Not reaching it: `orchestrate.ENGINE` is patched at `test_source_routing.py:99`, `:254`,
  `test_runtime_entrypoints.py:157`, `:233`, `test_operations.py:887` and `test_known_reference_mcp.py:266`,
  which cover `project init`, `run`, `run finalize`, `run cancel`, `direct`, `tasks` and `status`.
- What could differ: `consolidate_cut` runs a read-only snapshot, a read-only cut, a writable span insert and
  a SERIALIZABLE publication on one engine (`semantic/domain_operations.py:230-234`, `:619-623`, `:2029`), and
  on `min_size=1` these can be one backend. `read_snapshot` claims "SQLAlchemy/psycopg reset ownership"
  (`semantic/query.py:336`), but its restoration is asserted on a `NullPool` engine, where closing discards the
  session, so the assertion cannot detect a leak on a reused session. Real-pool reset evidence exists for
  `SERIALIZABLE` (`test_interop.py:57-72`), not for `postgresql_readonly`. The library chain reads as correct, and
  no defect is expected; what is absent is regression protection.

*Wire and host.* Every tool journey uses `fastmcp.Client(server)`, an in-memory transport carrying message
objects. The single subprocess test stops at `initialize` (`test_runtime_entrypoints.py:176-214`). So framing,
the process boundary, `.mcp.json`, the child configuration with `--semantic-run` (no test reference beyond a
docstring), the published tool schema (`list_tools` only on a synthetic server), concurrent calls and disconnect
go unobserved. `…survives_session_restart…` calls `release_claim` first (`test_agent_resubmission.py:302-311`),
and a killed host never does.

*Failure boundary.* The store's real exhaustion and lost-connection branches have no real exercise, and a control shows the
result. On 2026-10-30, with `CORPUS_DATABASE__URL` and `CORPUS_DATABASE__READER_URL` pointed at a nonexistent socket:
- **`ci query claims --project p` ends in an uncaught `PoolTimeout: pool initialization incomplete after 30.0 sec`** with a traceback and exit 1, not
  `database_retry`. `failure_boundary` catches `DBAPIError` (`cli/failures.py:23`), and `pool.wait` (`store.py:93`) fails before SQLAlchemy can wrap
  anything. *Inferred* from source for the other `failure_boundary` commands (`schema check`, `db check`, `regenerate`, `golden`).
- `ci status` handles this case and reports settings, which is the only path `tests/test_cli.py:41` stubs.
  `test_cli_failures.py:194-251` injects only `DBAPIError` after the engine is open, so no test sees the raw error.

Two narrower results, from pure controls with no database:
- `create_engine("postgresql+psycopg://", creator=<raises PoolTimeout>, poolclass=NullPool).connect()` raises `sqlalchemy.exc.OperationalError`, which
  `cli/status.py:103` does not catch, and nothing above it handles it. So a checkout failure after pool start escapes the path its comment calls
  "unreachable". The window is narrow: `pool.wait` must succeed and the next checkout must time out.
- `classify_error` returns `retry` for `PoolTimeout`, `PoolClosed` and `TooManyRequests` (`store.py:112-114`), because they subclass
  `psycopg.OperationalError` with no SQLSTATE. Retry is defensible for the first and third. Only `PoolClosed` is wrong, and no route reaching it
  was identified (`pool.close()` runs at `store.py:59-67`, `:96`; other holders not traced).

**Claim at risk.** The labels: `test_actual_cli_source_scope_agent_unknown_limit_and_cancel`,
`test_cli_finalization_returns_real_receipt_and_exact_replay`, "Native semantic-run MCP dispatch". Dispatch and logic
are real, but connection supply, registry and transport are replaced.

**Consequence.** A regression in pool reset, `_open_engine`, principal gating or pool sizing on the finalize route, or
a `fastmcp`/`mcp` bump (SC6), could pass the suite and first show in an operational run. And the ordinary failure of a
database being down or refusing credentials produces a traceback on the query path, not the structured refusal these routes
promise (DP-21). `open_runtime_engine` also runs the principal check on open (`semantic/runtime.py:80-83`), so a `DBAPIError` from an
unmigrated target would likewise escape `ci status` (*Inferred;* not run).

**Footprint.**
- *Known:* the sites above and the controls' results. Reachability beyond the observed `ci query` run is *Inferred*.
- *Inferred:* other journeys using the in-memory client, by search.
- *Suspected:* JSON adapter differences for non-finite floats, because `configure` installs `allow_nan=False`
  (`store.py:41-49`) and the harness does not. The failure class would differ, not valid data.

**Counterevidence.**
- `build_semantic_server()` without injection runs a real pooled lifespan through a full lease, read and propose
  (`test_runtime_entrypoints.py:37`).
- `ENGINE` and `PHASE0` are declared seams, are thin, and hand in the correct writer. Stubbing them makes `run` hermetic
  against the real pack, a legitimate isolation choice.
- `docs/design_review/evidence/2026-10-30_runtime-adoption/README.md` records real provider runs through a run-bound
  MCP child and fresh stdio discovery. That is real evidence at one source state, not a regression check.
- A search for session-state leakage found none on the live path: temp tables use `ON COMMIT DROP`, the only advisory
  lock is transaction-scoped and settings use `SET LOCAL` (not extended to `semantic_alembic/versions`).
- The worst outcome of the failure-boundary defects is an unstructured error, not wrong data. It fails closed and it is loud.

**Uncertainty.** Whether a killed-host restart or concurrent tool calls matter enough. No defect is claimed for them.

**Leads (optional).** Extend the stdio exchange past `initialize` to `tools/list` and one tool call. Run one finalize
route through the unstubbed `_open_engine` with `max_size=1`, which would force one backend to carry the read-only, write
and SERIALIZABLE sequence and would surface nested acquisition.

**Bears on:** SC6 and SC8; the runtime principal gate on stubbed routes (SC7); `database_retry` meaning.

<a id="dta-005"></a>

## DTA-005 — A product composer now exists, but native journeys mostly do not consume it

**Lineage.** Formerly "Each native journey assembles its own release; no shared or product composition is exercised".

**Principles:** FP-04, FP-03, DP-06, DP-01 by analogy, A2/A3; companion §2, §1.
**Subject:** implemented (`src/corpus_structure/semantic/regeneration.py:46-300`; `tests/semantic`).

**Diagnosis.** The prior premise that no production code composes a release is gone. `regeneration.py` has `prepare_pack`,
`acquire_pack`, `compose_pack_inputs` and `prepare_packs`, which `cli/regenerate.py` and `cli/schema.py` consume. Tests
that do consume it: `test_pack_acquisition.py`, `test_analysis_contracts.py:311-327`, `test_execution_projection.py:338-341`
(the native product-composed statistics release in `tests/semantic`) and `test_trace_reference_fixture.py:41`, `:121` (not
native). In `tests/semantic`, 23 modules still call layering helpers and 44 call `prepare_release(`. Many are deliberately
minimal, and nothing marks which.

| Choice | Product | `test_statistics_cut.py:52-72` | `test_known_reference_mcp.py:53-80` |
|---|---|---|---|
| Core import name | `semantic_core` | `semantic_core` | `core` |
| Metric layer | `prepare_source_inputs` | `observation_inputs` | `observation_inputs` |
| Rules | pack and core, aliases, execution model | pack and core only | `rules: []` |
| Operation artifacts (methods, policies, slices, profiles) | present | absent | absent |
| Scientific rebinding | yes | no | no |

`test_statistics_cut.py:1` says "Actual released statistics relations", but the release it persists is not what
`prepare_pack(domains/statistics)` produces.

**Consequence.** SC5 now has one product owner and some direct evidence. Native journeys (cut, MCP, finalize, reference
evaluation through `source_task`) still describe test-assembled releases, so a defect specific to product artifacts or
rebinding reaches only the narrower consumers. [DTA-015](evidence-and-discrimination.md#dta-015) is an instance: aliases
reach only the product composition's route, and the journeys that would exercise them on a composed release do not supply them.

**Footprint.**
- *Known:* the counts and table above.
- *Inferred:* each new consumer test adds a recipe rather than consuming one.

**Counterevidence.** Minimal schemas are a legitimate isolation choice, and migrating them is not implied. `tests/acceptance/test_regeneration.py`
exercises real preparation. The gap is now a choice rather than a necessity.

**Leads (optional).** Test builders that parameterize a product composition where the claim is about the real pack.

**Bears on:** SC5; the phase-0 rescoping of domain packs; real-pack evidence in [DTA-004](retirement-transfer.md#dta-004).

<a id="dta-009"></a>

## DTA-009 — Shared scenario builders live inside test modules, and their flags and defaults shape other modules' claims

**Principles:** FP-06, FP-01, FP-03, DP-17; companion §2, §3.
**Subject:** implemented (`tests/semantic`).

**Diagnosis.** The two new support modules are fault helpers. Scenario builders still live in test modules, and the
footprint has grown: **35 modules import from other test modules, from 14 hosts** (nine modules at the prior baseline; regex
`from .test_x import` over `tests/semantic`).

| Host | Main helpers | Importing modules |
|---|---|---:|
| `test_agent_resubmission` | `source_task`, `lease_and_read` | 9 |
| `test_domain_operations` | `fixture`, `locate_proposal` | 4 |
| `test_operations`, `test_analytics`, `test_proposals`, `test_publication`, `test_releases`, `test_archive_reader` | `setup` and others | 4 each |
| `test_execution_release`, `test_identity_exclusions` | | 3, 2 |
| `test_query`, `test_conditional_rules`, `test_inference`, `test_ontology` | | 1 each |

Hidden defaults and coupled flags decide what downstream tests check:
- `fixture` (`test_domain_operations.py:57-564`, 508 lines, 19 keyword flags). `two_reports` also makes `Person` globally
  scoped and case-preserving (`:99-100`). `known` changes the run binding's `data_revision`, adds `unique_keys` and sets
  `raw["entities"] = []`. `statement_packets` is three-valued. `local_known`, `broken` and `second_math` are inert alone.
  `graph`, `nary`, `formulas`, `claim_chain` and `cycle` rewrite `raw` in sequence, so combinations are order-determined.
- `test_occurrence_context.py:45` patches `fixture.__module__ + ".locate_proposal"`, so its scenario depends on how the helper
  resolves names.
- Magic numbers fixed by hidden structure: `test_source_routing.py:227` `total == 7`, and `test_operations.py:660`, `:686`, `:781`.
  A new stage edits at least four sites.
- `archive=` on `test_operations.setup` is a dead parameter (`:26`, passed only at `:860`).

A module-level compile adds a further dependency: `test_publication.py:144` and `test_arrow_publication.py:41` run
`R = fixture_model()[1].release_id` at import, and `test_analysis_boundaries`, `test_execution_native` and the database-free
`test_shared_math` inherit it. A preparation failure for this small fixture becomes a collection error across five modules,
which withholds unrelated results on a default run (*Inferred*). `_qualification_schema` (`test_publication.py:722-724`) now
ignores its arguments.

**Consequence.**
- A change to a hub for one consumer's case alters other modules' scenarios, which amplifies churn and obstructs diagnosis. Churn
  has moved from `setup` to `fixture` (`c50a747..HEAD`: `test_domain_operations` 9 commits, `test_agent_resubmission` 6,
  `test_operations` 3). The prior account's "35 and 19 commits" could not be reproduced and is not carried forward.
- A focused run inherits import-time work.

**Footprint.**
- *Known:* the sites cited. `world` in tier-3 support has shrunk to two definitions.
- *Inferred:* the collection-error consequence.

**Counterevidence.** Shared real-route setup also closed part of [DTA-008](#dta-008), so this is a consolidation with a benefit.
Hub failures are mostly setup-shaped and loud. The only silent shaping of a consumer found is the `two_reports` scope coupling.
`source_task` has five flags visible at call sites.

**Bears on:** every package adding native semantic tests; selective runs; failure diagnosis.

<a id="dta-012"></a>

## DTA-012 — Support restates source and pack declarations, and file-path loading defeats its own caches

**Principles:** FP-04, DP-01, DP-06, FP-07; companion §2, §8.
**Subject:** implemented (conftests under `tests/{llm,evaluate,ingest,agent,consolidate,db}`; `tests/math_support.py`;
`tests/validate/support.py`).

**Diagnosis.**
- The recipe for "the production rendition of a reference page" is restated at `tests/ingest/conftest.py:22-35`,
  `tests/llm/conftest.py:46`, `:95-105`, `tests/evaluate/conftest.py:43`, `:83-95`, `tests/math_support.py:43`, `:116-123`, and locally
  in `tests/math/test_scope.py`, `tests/ingest/test_corpus.py` and `test_renditions.py`. `"siegrist_random/random"` is literal at 11 sites.
- `PACK_MACROS` has three copies (`tests/llm/conftest.py:57`, `tests/evaluate/conftest.py:46`, `tests/math_support.py:54`), and
  `tests/agent/conftest.py:40` derives from `domains/statistics/methods.yaml`. The math copy now states a real reason: it retains
  the independent historical oracle configuration (`tests/math_support.py:11`). The llm and evaluate docstrings still say "until that
  file exists", though it exists.
- `tests/validate/support.py:47-63` loads other test files by path, and `test_batch.py:26-32`, `test_runner.py:41-45` and
  `test_views.py:48-57` each load `support.py` separately. Each load is a new module object with its own `@cache`, so caches hold
  only within one test module, and renditions and A0 parses are rebuilt per consumer. `sys.modules["validate_support"]` is overwritten on
  each load.
- Sharing mechanisms remain mixed: fixtures, file-path loads, `helpers` fixtures, relative imports of test modules, and `db_support`
  (`tests/conftest.py:139-155`), which hand-mirrors nine names on the reasoning that the conftest is unimportable, though those helpers
  moved to an importable module.

**Consequence.** If the source root or URI convention changes, keys derived from `source_uri` in frozen reference sets diverge without
failing, and each copy needs a separate edit. A `methods.yaml` macro change leaves these suites green against the old table: right for
parity tests, unstated for `test_align.py` and `test_equivalence.py`.

**Footprint.**
- *Known:* the sites cited. The three macro copies currently equal `methods.yaml` (computed 2026-10-30), so there is no drift yet.

**Counterevidence.** A rendition build is about 0.2 s per page in-process under [the receipt's conditions](execution-and-qualification.md#measurements),
so repeating seven pages across four caches is immaterial. Grammar analysis is costlier and also runs through independent implementations and caches
(`tests/agent/conftest.py:58-82`, `tests/math_support.py:116-146`) over overlapping pages: math session fixtures take 18.18 s and 22.55 s, and first touches of pages in
`test_packet.py` total about 50 s. Attributing that time to analysis is *Inferred*, and worker wall time is not CPU time. Most of this support serves code under [DTA-014](retirement-transfer.md#dta-014),
so any remedy follows that decision.

**Bears on:** source-profile changes in the phase-0 rescoping.

<a id="dta-008"></a>

## DTA-008 — Hand-built method descriptors exercise a tolerant branch of `record_method`

**Lineage.** Formerly "Hand-written stand-ins for production-written release, catalog and descriptor artifacts are not tied to what
production writes".

**Closed, with positive evidence.** Stand-in `sem.release` rows and hand-written catalog rows are gone. `test_publication.py:147-172` seeds
through real `prepare_release` and `persist_release`, `test_arrow_publication.py:47-50` delegates to it, `test_operations.setup` always persists
a real release (`:114-116`) and `test_inference.setup` prepares a real schema. A search of the tests for `prepared_bytes=b`,
`content_digest="test"` and inserts into `sem.*` catalog tables finds only deliberate cases: a tamper (`test_release_compatibility.py:400`), a
historical persister replay (`test_native_closure.py:429-435`) and a denied insert (`test_native_fixtures.py:175`). `test_native_closure.py:68`, `:85` also insert into `sem.input`, as finalized-release denials. Publication tests no longer
take the `native_range` fallback. The closure's price is in [DTA-009](#dta-009).

**Principles:** FP-04, DP-01, DP-24, FP-02; companion §1, §5. **Subject:** implemented (`tests/semantic`;
`src/corpus_structure/semantic/operations.py:145-149`, `:166`).

**Diagnosis (what remains).** An AST count of `SimpleNamespace` calls carrying a name, version and family finds 26 sites in `tests/semantic`,
13 untyped (no `unit_type` or `Config`). `test_operations.py` has 10 with one typed, and `test_native_agent_hold`, `test_native_source_selection`,
`test_packet_input_snapshot` and `test_semantic_mcp` are also untyped. `record_method` keeps `hasattr` tolerance.

**Consequence.** Mostly SC1 and SC3 coupling rather than concealed defects: no guard depending on the method's `unit_type` value was found, because
`execution_guards.sql` reads the task's column. Other readers of `ops.method.unit_type` were not fully traced.

**Counterevidence.** Typed descriptors appear in `test_execution_native` (6/6), `test_domain_operations`, `test_agent_resubmission`, `test_serving` and
`test_statistics_cut`. The tolerance was introduced for unresolved legacy method metadata.

**Bears on:** physical-catalog evolution.
