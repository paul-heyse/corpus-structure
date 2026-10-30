# Test code design principle audit

This is the separate living diagnostic account for test code, test evidence and shared test
infrastructure. The [skill](../../../.claude/skills/design-principle-audit-tests/SKILL.md) owns
the audit method; the [repository binding](../design_principles/binding/corpus-structure.md#test-code-design-principle-audit)
owns invocation, finding identity and follow-up routes. The
[test-assessment companion](../design_principles/core/test-assessment.md) supplies the test-specific
interpretation of the selected core and applicable domain profiles.

<a id="baseline"></a>

## Baseline

| | |
|---|---|
| Audited source | commit `599d479` (2026-10-30T08:51-04:00), clean tree. Line numbers cite this commit |
| Reconciled through | commit `1efd4fe` (2026-10-30T10:13-04:00), which landed during the audit. It adds one functional review and edits `STATUS.md`, touching no test, source or configuration, and collection is unchanged |
| Date | 2026-10-30 |
| Standard | core 3.3 (principles; efficient-architecture heuristics 1.0); test-assessment companion 1.2; code-intelligence profile 1.4, applied by analogy (CI-04, CI-06, CI-10, CI-11, CI-12); [binding](../design_principles/binding/corpus-structure.md) |
| Kind | Second test audit: a full refresh of the first (`c6f8d16`, reconciled through `c50a747`, 2026-10-29), which read much of the tree only as representative samples or through a transfer lens. Tiers are retired. The [broad audit](../audit/README.md) has its own baseline |
| Change since the prior baseline | 229 commits. Package tests: 150 files changed (58 added, 23 deleted). `src`: 170 files changed. The harness was rebuilt under [ADR-0032](../../adr/0032-native-test-deployment-equivalence.md) and the [qualification plan](../../plans/semantic-model-pivot/qualification-infrastructure.md) |
| Inventory | `uv run --no-sync pytest --collect-only -q` (`addopts` already sets `-q`, so this prints per-file counts): **passed**. 168 modules and 2,429 tests, no collection errors. This equals the node count in `STATUS.md` |
| Publishing commit | The commit that adds this account, distinct from the source baseline |

Paths in this account are relative to `python/corpus-structure/` unless they start at the
repository root (`docs/`, `domains/`, `fixtures/`, `sources/`, `ops/`, `scripts/`, `justfile`,
`pyproject.toml`).

## Scope

All testing responsibilities in the tree, by the operator's instruction for a full and complete audit.

| Area | Python lines | Collected tests | Read |
|---|---:|---:|---|
| `tests/semantic` | 24,507 | 828 | All 88 files in full |
| `tests/core`, `schema`, `validate` | 9,778 | 879 | All 28 files in full |
| `tests/math`, `ingest`, `llm`, `evaluate`, `data` | 5,821 | 288 | All Python in full. JSON sampled, then re-derived and compared |
| `tests/db`, `orchestrate`, `consolidate`, `agent`, `acceptance`, `pool`, `fixtures`, root modules | 7,682 | 307 | All Python in full. `d3_ddl.sql` partially; reader archives by top-level keys |
| Shared harness: package and semantic conftests, `test_db_fixtures`, `test_native_fixtures` (their nodes are counted in the rows above) | | | In full |
| Root `tests/scripts`, `tests/evidence`, `tests/conftest.py` | | 127 | In full |
| Outside the test tree: `scripts/native_test_support.py`, `test_receipts.py`, `qualification_plugin.py`, `test_prerequisites.py`, `pg_provision.sh`, `pg_semantic_roles.sh`; pytest, Hypothesis and nextest configuration; `justfile` routes; `ops/postgresql/corpus.conf` | | | In full |
| Repository-root reference data: `fixtures/{s0,tex,packs,toy,trace}` (49 files) | | | Mixed; see [limits](#coverage-limits-and-open-questions) |
| Rust | | 0 | `crates/corpus-structure` has no tests; `just test` uses `--no-tests=warn` and the route classifies an empty selection as `not_run` |

All 220 tracked files under `python/corpus-structure/tests` and root `tests/` were assigned exactly once, and every contributor returned a disposition per file; the coordinator checked those ledgers against
the generated list. Production contracts and dependencies were read only as far as needed to judge a claim. This account does not imply that the enclosing production system was audited or qualified.

**Excluded:** spike code and instruments under `docs/design_review/evidence/` (tests that read those folders stay in scope as a dependency); `build/` environments, except reading one retained receipt.

## Method

- **Contributors.** Seven read-only contributors covered a partition of the tree, each considering FP-01–FP-07 with particular attention to FP-07/A4, rechecking assigned prior findings as leads and answering
  assigned library questions. Prior conclusions and library hypotheses were handed over as unverified.
- **Coordinator verification.** The coordinator read the decisive sources behind each finding, merged candidates by structural cause, and recounted disputed figures with one method.
- **Independent challenge.** One further reviewer, seeing the draft findings and sources without the coordinator's reasoning, looked for false positives and for causes missed across contributor boundaries. It overturned two
  "lost" verdicts in [DTA-004](retirement-transfer.md#dta-004), corrected the [DTA-014](retirement-transfer.md#dta-014) count, added the escaped `PoolTimeout` in [DTA-016](support-structure.md#dta-016) and the cost join in
  [DTA-013](evidence-and-discrimination.md#dta-013). The coordinator verified those before adopting them.
- **Change scenarios:** SC1 add a `semantic_alembic` migration; SC2 bump the compiler version or profile; SC3 a lifecycle guard changes; SC4 retire `core.keys` or the old store; SC5 add a dynamic class or second pack;
  SC6 upgrade an ontology or library pin; SC7 add a restricted principal or database ACL; SC8 a behaviour-preserving swap of the harness lifecycle mechanism.
- **Execution.** No test, timing, benchmark or mutation campaign was run. What ran, all read-only:
  - collection, `pytest --setup-plan` on one module, and AST and search scripts;
  - one retained receipt read as a [measurement under its stated conditions](execution-and-qualification.md#measurements);
  - read-only catalog queries on the 5434 cluster, dated where cited;
  - pure controls with no database writes, cited in [DTA-015](evidence-and-discrimination.md#dta-015), [DTA-016](support-structure.md#dta-016) and the pgpq observation, including `ci query` and `ci status` against a nonexistent socket. Their outputs are cited as observations and not retained as evidence.
- **Leads examined and rejected:**
  - *Adopt `pytest-postgresql` for the harness.* [Below](#postgresql-library-lens).
  - *`NullPool` in the harness differs from a pooled production engine.* Both use `NullPool`; the real difference is the `psycopg_pool` layer underneath ([DTA-016](support-structure.md#dta-016)).
  - *1,200+ database nodes.* 448 nodes are marked `db`; 1,224 is the count of parametrized nodes.
  - *Evidence-folder reads are fragile.* They are ordinary Git text with no LFS filter, read as data only.
  - *pgpq timezone, type and JSONB limits.* Not reachable from production's stage types.
  - *Raw SQL couples tests to physical names.* A hand classification of 72 sites in the release and admission tests finds about 57 correct (native ABI, catalog and fault-injection subjects). `table("schema.name")` names the same columns.

## How the foundations were assessed

- **FP-01 (separation of concerns) and FP-03 (composition).** Who owns scenario construction, lifecycle and reference data, and whether a retirement or new consumer can proceed locally. Findings:
  [DTA-009](support-structure.md#dta-009), [DTA-014](retirement-transfer.md#dta-014), [DTA-005](support-structure.md#dta-005), [DTA-012](support-structure.md#dta-012).
- **FP-02 (stable contracts).** What tests observe, and where a stand-in replaces a boundary. Findings: [DTA-016](support-structure.md#dta-016), [DTA-010](evidence-and-discrimination.md#dta-010), [DTA-015](evidence-and-discrimination.md#dta-015),
  [DTA-008](support-structure.md#dta-008).
- **FP-04 (explicit domain model and scoped semantic authority).** Whether expectations are independent and whether an oracle still has something to judge. Much evidence is deliberately independent; see the
  [strengths](evidence-and-discrimination.md). Findings: [DTA-004](retirement-transfer.md#dta-004), [DTA-014](retirement-transfer.md#dta-014), [DTA-011](evidence-and-discrimination.md#dta-011), [DTA-019](evidence-and-discrimination.md#dta-019),
  [DTA-020](evidence-and-discrimination.md#dta-020).
- **FP-05 (explicit structure and constraints).** Whether enforcement points are actually discriminated and outcomes explicit. Findings: [DTA-001](evidence-and-discrimination.md#dta-001), [DTA-006](evidence-and-discrimination.md#dta-006),
  [DTA-013](evidence-and-discrimination.md#dta-013), [DTA-003](execution-and-qualification.md#dta-003).
- **FP-06 (local reasoning).** Hidden defaults, ambient state, order dependence and misleading self-descriptions. Findings: [DTA-009](support-structure.md#dta-009), [DTA-017](execution-and-qualification.md#dta-017),
  [DTA-007](evidence-and-discrimination.md#dta-007).
- **FP-07/A4 (execution fit), the governing efficiency criterion.** Assessed statically through H2, H5, H12, H19, H20 (preparation lifetime and repeated conclusions), H21, H22 (scheduling and shared capacity), H25, H27 (machinery against participants
  and full lifecycle), then checked against one receipt.
  - The former major shortfall, per-test head bootstrap, is closed ([DTA-002](execution-and-qualification.md#dta-002)). Clones are about 3.7% of recorded phase time under that receipt, and the route fits its claim.
  - The larger questions are what the expense buys. Under that receipt, modules challenging code with no execution route cost about 20% ([DTA-014](retirement-transfer.md#dta-014)), and the three costliest nodes, 29.8%, all carry weak assertions ([DTA-013](evidence-and-discrimination.md#dta-013)).
  - Demonstrated repeated work remains in read-mostly matrices ([DTA-018](execution-and-qualification.md#dta-018)), at most about 5.5% by the modules cited. Grammar analysis repeats across independent caches ([DTA-012](support-structure.md#dta-012)), with its attribution inferred.
  - Judged immaterial or unproven: repeated rendition builds across caches, clone connection counts, `CREATE DATABASE` strategy and the eight-entry preparation cache.
- **Domain profile.** The code-intelligence profile applied by analogy: CI-04 unknown is not absent ([DTA-003](execution-and-qualification.md#dta-003)); CI-10 hermetic inputs ([DTA-017](execution-and-qualification.md#dta-017)); CI-12 non-circular evaluation
  ([DTA-011](evidence-and-discrimination.md#dta-011), [DTA-004](retirement-transfer.md#dta-004)).

## Synthesis

1. **The harness and route were largely repaired, and the account now shows it.** Per-test bootstrap, the release and catalog stand-ins, and five of six ways the route lost outcomes are closed with positive evidence. Test isolation and classification are now
   a strength. The remaining harness concerns are about what surrounds the lifecycle owner, not its core ([DTA-002](execution-and-qualification.md#dta-002), [DTA-003](execution-and-qualification.md#dta-003), [DTA-017](execution-and-qualification.md#dta-017)).
2. **Retirement stopped at execution routing, and this is the largest structural matter.** About a quarter of collected nodes challenge code with no execution route, and the independent oracles for surviving behaviour lost their actuals. Strong tests sit
   on dormant code while the live path holds synthetic evidence ([DTA-014](retirement-transfer.md#dta-014), [DTA-004](retirement-transfer.md#dta-004)). "2,429 required nodes" over-reads as product assurance.
3. **One concrete defect illustrates the gap.** The pack's head-word key never matches on the surviving route, so `The normal distribution` and `normally distributed` stay split on the composed pack, and a sound unit oracle cannot see it, because it hard-codes the other form. No split is visible in the current small target
   ([DTA-015](evidence-and-discrimination.md#dta-015)).
4. **Refusal evidence is improving but uneven.** A stronger two-principal form exists and has spread, while 32 bare refusals remain and some cannot reach the guard they name. This matters because PL/pgSQL guard logic has no static evidence, so behavioural
   tests carry it ([DTA-001](evidence-and-discrimination.md#dta-001)).
5. **Composed claims read stronger than their observation.** Journeys assert presence where the claim is an expected set, and "actual" journeys stop short of the wire, pool and failure boundary. An unreachable database produces an uncaught traceback on `ci query`, where these routes promise a structured refusal
   ([DTA-006](evidence-and-discrimination.md#dta-006), [DTA-016](support-structure.md#dta-016)).
6. **Expense and assurance are not aligned.** The clone route fits, but about a fifth of recorded time goes to code with no execution route, and the three costliest nodes are all weak-assertion sites ([DTA-014](retirement-transfer.md#dta-014), [DTA-013](evidence-and-discrimination.md#dta-013)).

No plan has adopted these findings: a search of `docs/plans`, `docs/plan_improvement_reviews`, `docs/design_review/reviews`, `docs/adr` and `STATUS.md` for `DTA-` finds none. Scheduling them is a separate, instructed step.

<a id="findings"></a>

## Findings

Ordered by consequence for current consumers at this baseline (original SP-09/SP-10 and the phase-0 rescoping). IDs are stable and never reused, so their numbers do not imply order. The prior account's "pivot relevance" column is replaced by state, because the
tier and retirement premises it relied on have moved.

| ID | Finding | State at this baseline | Page |
|---|---|---|---|
| [DTA-004](retirement-transfer.md#dta-004) | Independently stated outcomes for surviving behaviour lost their actual on the live path | Revised: risk realized | transfer |
| [DTA-014](retirement-transfer.md#dta-014) | About a quarter of collected nodes challenge code with no execution route, and nothing separates them from live evidence | New: 585 nodes, about 20% of recorded time | transfer |
| [DTA-001](evidence-and-discrimination.md#dta-001) | Refusal tests can pass for a reason other than the guard they name | Revised: widened, partly closed | evidence |
| [DTA-015](evidence-and-discrimination.md#dta-015) | The surviving label route supplies head-word keys the normalizer cannot match, and the only oracle uses the other form | New: production cause, control confirms; not visible in the current target | evidence |
| [DTA-016](support-structure.md#dta-016) | Journeys labelled "actual" stop short of the production wire, pool and failure boundary | New: production cause on the failure path, control confirms | structure |
| [DTA-006](evidence-and-discrimination.md#dta-006) | Composed journeys assert presence or lower bounds where the claim is an expected set | Confirmed: footprint surveyed | evidence |
| [DTA-017](execution-and-qualification.md#dta-017) | The harness leaves a real target as the ambient connection, and only names separate targets from sweepable databases | New | execution |
| [DTA-005](support-structure.md#dta-005) | A product composer now exists, but native journeys mostly do not consume it | Revised: premise changed | structure |
| [DTA-011](evidence-and-discrimination.md#dta-011) | Semantic key assembly is evidenced only by cross-implementation agreement | Revised: value vectors now pinned | evidence |
| [DTA-007](evidence-and-discrimination.md#dta-007) | Determinism, reload and work-avoidance claims are observed through process state the tests do not control | Revised: narrowed | evidence |
| [DTA-018](execution-and-qualification.md#dta-018) | Read-only and rollback cases rebuild a complete write journey per case | New | execution |
| [DTA-009](support-structure.md#dta-009) | Shared scenario builders live inside test modules, and their flags and defaults shape other modules' claims | Confirmed: larger | structure |
| [DTA-010](evidence-and-discrimination.md#dta-010) | Compiler refusal cases target catalog entries by position and observe only the first, often generic, diagnostic | Confirmed: widened; predicted failure occurred | evidence |
| [DTA-019](evidence-and-discrimination.md#dta-019) | Frozen oracles and genuine archives have no declared basis for accepting a deliberate change | New | evidence |
| [DTA-013](evidence-and-discrimination.md#dta-013) | Some generated and quantified assertions can pass vacuously | Confirmed: footprint extended; on the three costliest nodes | evidence |
| [DTA-020](evidence-and-discrimination.md#dta-020) | "Historical" test inputs are built by the current producers | New | evidence |
| [DTA-012](support-structure.md#dta-012) | Support restates source and pack declarations, and file-path loading defeats its own caches | Revised | structure |
| [DTA-008](support-structure.md#dta-008) | Hand-built method descriptors exercise a tolerant branch of `record_method` | Narrowed: release and catalog stand-ins closed | structure |
| [DTA-002](execution-and-qualification.md#dta-002) | The lifecycle owner covers databases only; killed runs and cluster-level test effects leave what it cannot see | Narrowed: per-test bootstrap closed | execution |
| [DTA-003](execution-and-qualification.md#dta-003) | The qualification route records context it did not use and misclassifies undeclared prerequisites | Narrowed: five of six losses closed | execution |

<a id="postgresql-library-lens"></a>

## PostgreSQL library lens

The operator supplied overviews for shared test infrastructure. They were used to recognize weaknesses and as sources of leads, not as remedies. Library behaviour a finding rests on was confirmed from installed source or primary documentation. These results
concern fit at this baseline, and adopting a library belongs to a later review.

| Library | Question | Result |
|---|---|---|
| `pytest-postgresql` | Does `PgAdmin` (a 509-line class in `scripts/native_test_support.py`) repeat what the library provides? | **No, for most of it.** Accepted [ADR-0032](../../adr/0032-native-test-deployment-equivalence.md) rejected it, and its premises were tested, not relitigated. Upstream `janitor.py` at v9.1.1 terminates backends and has no ownership stamp, lease, sweep, ACL or settings replay, or prerequisite classification. Restricted backends and residue on a shared cluster are real constraints, and PostgreSQL does not copy database grants or `ALTER DATABASE SET`. Generic rows are trivial in volume, and the bespoke choice has a stated reason, so there is no DP-13, DP-16 or G8 finding at this scope. One premise is qualified: the server is dedicated against other projects, not against real targets ([DTA-017](execution-and-qualification.md#dta-017)). The legacy family's cache no longer pays for itself ([DTA-014](retirement-transfer.md#dta-014)) |
| `pytest-postgresql` | Does `depends_on` template layering bear on repeated scenarios? | A lead only, and no library is needed: `PgAdmin.database(name, source, policy=…)` already clones any sealed source ([DTA-018](execution-and-qualification.md#dta-018)) |
| `pytest-postgresql` | Does the suite need xdist? | No finding. See the serial-execution [observation](execution-and-qualification.md#observations-recorded-without-a-finding) |
| SQLAlchemy | Does outer-rollback `db` hide commit boundaries? | Yes in principle: `Connection.commit()` commits the outer transaction, and a later rollback would not undo it. No code under test commits inside `db`, and `join_transaction_mode` is `Session`-only. Little consequence, because the fixture serves code under [DTA-014](retirement-transfer.md#dta-014) |
| SQLAlchemy | Are event-based spies sound? | Mostly. See [DTA-007](evidence-and-discrimination.md#dta-007). They cannot see server-side work, which is the right limit to state |
| psycopg | Can refusal tests observe more than `DBAPIError`? | Yes, with a limit: SQLSTATE resolves declarative confounds, but most RAISE guards share `23514` and set no `constraint_name`. `diag.message_primary` is unused and narrower than `str(DBAPIError)`, which a control shows includes `CONTEXT` ([DTA-001](evidence-and-discrimination.md#dta-001)) |
| psycopg | Are prepared statements reached? | Not on harness engines, which open a new session per checkout; production's default `prepare_threshold` applies on reused sessions. No defect found ([DTA-016](support-structure.md#dta-016)) |
| psycopg-pool | Where is the production pool evidenced? | Positive paths are real (`test_interop.py:57-72`). Exhaustion, closure and lost-connection branches have none, and a control shows `PoolTimeout` escaping `failure_boundary` on `ci query` ([DTA-016](support-structure.md#dta-016)). `tests/pool` concerns a different pool (Arrow observation relations) |
| pglast | Do tests share a parser with the code they challenge? | No: nothing in `tests/semantic` imports it, and expectations are hand-written. `tests/db/test_port_check.py` makes no semantic overclaim, but its D3 premise is no longer live ([DTA-014](retirement-transfer.md#dta-014)). PL/pgSQL bodies are opaque by design, which raises the stakes of [DTA-001](evidence-and-discrimination.md#dta-001) |
| pgpq | Is its buffering and type surface evidenced? | The multi-chunk path is not exercised, confirmed on the installed 0.12.0, and no plausible mistake was found. Type limits are unreachable. See the [observation](evidence-and-discrimination.md#observations-recorded-without-a-finding) |

## Existing findings linked, not rediagnosed

| Finding | Owner | State here |
|---|---|---|
| [DA-018](../audit/boundaries-and-composition.md#da-018), [DA-019](../audit/boundaries-and-composition.md#da-019) | Broad audit, where both are retired | DA-019 routes residue to [DTA-002](execution-and-qualification.md#dta-002). Not refreshed |
| [DA-002](../audit/semantic-model-and-authority.md#da-002), [DA-009](../audit/semantic-model-and-authority.md#da-009) | Broad audit | Legacy mirror and key-pinning observations; the semantic-identity analogue is [DTA-011](evidence-and-discrimination.md#dta-011) |
| [DA-014](../audit/structure-and-invariants.md#da-014) | Broad audit | Not reexamined |
| F01, F02, F03 | [Phase 0 §11](../../plans/phase-0_2026-10-28.md#11-findings-disposition) (alignment review, operator exception) | F01 is a sibling of [DTA-001](evidence-and-discrimination.md#dta-001). F02's test-scope state is in [DTA-004](retirement-transfer.md#dta-004) |
| Q4-01, I2A-01 | [Phase 0 §11](../../plans/phase-0_2026-10-28.md#11-findings-disposition) | The test paths each observed have changed; see the [execution page](execution-and-qualification.md). Disposition is that owner's |

## Strengths to keep

Each page opens with the strengths that bound its findings. In summary:
- a harness with real restricted principals, fresh committed clones, fail-closed policy replay and independent controls for each;
- a route that classifies conservatively, retains failures, and cannot manufacture a pass;
- a two-principal refusal pattern that separates privilege from the guard behind it;
- real races that prove they raced, and hostile batches built through production;
- hand-written expected sets, independently authored references and a server-side content oracle;
- genuine archives with a recorded route, and frozen reference data that cannot launder a regression.

## Coverage limits and open questions

- **Read depth.** All Python test code was read in full by its assigned contributor. Decisive sources were read by the coordinator, not all 50,000 lines. JSON reference data was sampled, then re-derived and compared where a stdlib generator exists. Partially read or not
  read: `tests/db/data/d3_ddl.sql` (first 50 lines); `fixtures/s0/*.json` (shape from README, generator and one file; `build.py` not re-derived because it imports production); `fixtures/toy/{ownership,registers}.json`, whose status rests on consumer searches;
  `fixtures/trace/build_*.py` and vendored HTML, whose integrity is checked by tests.
- **No execution.** Every "would fail" or "would pass" is reasoning from source unless a control is cited. No test ran.
- **The receipt** is one run at `2869e6e` with unknown host load. It supplies no capacity or speedup claim.
- **Reachability** is relative to `cli.app`, the single console entry point, with `justfile`, `import_module` and `__import__` searched by name. The live-or-dormant split per test module is the contributors' classification, and `tests/core/test_shapes.py` was not partitioned.
- **Absence claims** state their search scope where they are made, and none settles a question beyond it.
- **Unavailable:** `/etc/postgresql/18/corpus/{semantic_hba,pg_ident}.conf` are not readable by the operator, so auth rows were not inspected.
- **Open questions for the operator:**
  - Are `validate`, `schema.compile` and `key_claims` a declared reservoir, or to retire with transfer? This decides [DTA-014](retirement-transfer.md#dta-014) and much of [DTA-012](support-structure.md#dta-012).
  - Is S0 parity a current obligation for the semantic scorer, or a finished port check? This affects [DTA-004](retirement-transfer.md#dta-004) and [DTA-019](evidence-and-discrimination.md#dta-019).
  - Do retained pre-9 decoders have a consumer ([DTA-020](evidence-and-discrimination.md#dta-020))?
  - Do Alpha and Beta reports stay separate, or fuse as provenance ([DTA-004](retirement-transfer.md#dta-004))?
- **Controls that would settle open points, not run:** dropping `validate_measurement_definition` on a disposable clone ([DTA-001](evidence-and-discrimination.md#dta-001)); `cache_info()` at session end ([DTA-007](evidence-and-discrimination.md#dta-007)); printing `diagnostics[0]` per case
  ([DTA-010](evidence-and-discrimination.md#dta-010)); a finalize route through the unstubbed engine with `max_size=1`, and `ci status` against an unmigrated target ([DTA-016](support-structure.md#dta-016)).
- **Challenge limits.** The independent reviewer did not separately challenge [DTA-005](support-structure.md#dta-005), [DTA-010](evidence-and-discrimination.md#dta-010), [DTA-012](support-structure.md#dta-012), [DTA-019](evidence-and-discrimination.md#dta-019) or [DTA-020](evidence-and-discrimination.md#dta-020) beyond citations, and it read about 45 citations rather than all of them.
- **Concurrency limit:** changes after the source baseline are not reconciled unless stated above.

## Reading the account

| Page | Main concerns |
|---|---|
| [evidence-and-discrimination.md](evidence-and-discrimination.md) | Refusal reach, expected sets, independence from the code under test, reference data, generated cases |
| [execution-and-qualification.md](execution-and-qualification.md) | Native harness lifecycle, repeated preparation, ambient state, measurements, the qualification route |
| [support-structure.md](support-structure.md) | Boundary stand-ins, where support lives, what it restates, coupling to production artifacts and to other tests |
| [retirement-transfer.md](retirement-transfer.md) | What retirement left behind and what was lost |

Findings explain:
- what claim is at risk and why the structural cause matters;
- the inspected footprint (Known, Suspected, Inferred);
- the decisive sources, contrary evidence and material uncertainty.

They use the standard's evidence vocabulary and cite core and profile principles plus companion
sections. Source reasoning can establish a structural weakness without running the suite; a passing
suite does not establish its evidential quality.

## Finding ownership and history

New test findings use stable DTA-nnn identities. Each finding has one primary home, and the
index above is for navigation only. Identity and lineage are kept as explanations or topic
boundaries change, and retired IDs are never reused.

**Relation to the broad account.** The broad and test accounts examine related paths at different
baselines. Where a structural cause is already a finding in the broad account, its identity and
home are kept and it is linked here, with a statement of what was reexamined; this account does not
claim to refresh the other. A new, distinct cause gets its own finding, but sharing a component or
principle is not reason enough to merge diagnoses. A move records its lineage and leaves a route
from the former home.

**Who owns what.**
- The account owns diagnosis at its stated baseline.
- Reviews own correction alternatives and judgment.
- Implementation plans own scheduled disposition, progress and closure evidence; link those owners
  without copying mutable status.

**Removal and history.** Resolved material is removed only on evidence, with closure recoverable
through the removal commit. Git holds earlier accounts; there is no separate audit archive or
execution register.

**Refreshing.** Ordinary implementation does not maintain this collection as a recurring gate. A
test-scope audit or a subsequent review uses the binding's deliberate invocation and freshness
rules. A refresh uses intervening test, production-contract, dependency and configuration changes
as leads, and revisits findings whose premises changed. This account performs no repairs and
establishes no scientific or product qualification.
