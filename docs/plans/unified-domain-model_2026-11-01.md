# Unified domain model: typed operations and generated realization

**Status:** Planned — plan series authored; implementation not started by this undertaking.
**Created:** 2026-11-01. **Target claims:** Proposed; library interface checks and historical
implementation evidence retain their stated scope. This coordinator alone owns package state,
execution queue and source-review disposition for the new series.

## Outcome, authority and selected scope

Deliver R01–R09 and O01–O03 from the [integrated review](../design_review/reviews/design_review_unified-domain-model_2026-11-01.md)
at `370f0643`. One coherent release governs concepts, relationships, operations, state,
comparison/invariant policy and qualified consumers. Ordinary callers use domain APIs;
model-derived typed implementations generate relational/native products and minimize maintained
SQL. Preserve database enforcement and exact/pinned evidence across Python, SQL, Arrow and RDF.

This is a new implementation series. Existing plans, their historical qualification and their
scheduled finding ownership remain unchanged. The review is design evidence; DESIGN/D-documents
and accepted ADRs remain architectural authority. UM-00 schedules selected authority amendments
before dependent new behavior. No production code, database, dependency or default was changed
while authoring this series. Creating these plans does not itself start implementation.

Operator decisions, 2026-11-01: all nine recommendations and three functional opportunities enter
this series, including bounded investigations. RC01–RC03 accepted; RC04 rejected. A conditional
mechanism must receive an explicit result and realization decision; it cannot silently erase
its selected capability. Complete procedural SQL elimination remains unestablished.

## Baseline and focused foundation assessment

Inspected source `370f0643`, with the current dirty PDF model/contracts, generated columns,
native-candidate, readers/producers, payload/metadata validation, native functions/SQL and tests
read where relevant. The principal review used `1cb8e620`/`f999ffcb`, diagnostic revisions
UM-20261101-r2/r3, publications `cc2998d9`/`54cd74cb`. Current source remains substantially founded
on effective LinkML definitions, prepared Pydantic boundaries, native execution bindings,
Core metadata/typed columns, qualified graphs, owned Arrow/DuckDB analysis, protected publication
and Alembic native operations. They are reused, not presumed absent.

The additional user direction is explicit: the PDF series is still changing; use the inspected
current snapshot and reconcile later in a **discrete update**, rather than continuously tracking
or integrating its work. The PDF coordinator retains current-book completion, provider/evaluator
journeys, deployment/default adoption and its evidence. A later change affecting a consumed
contract requires focused reinspection before executing that affected package. It does not
invalidate unrelated settled design or require another full review.

The SQLGlot guide's Advanced Capabilities Addendum (supplied lines 1121–2724) was assessed in full
on 2026-11-01 after the principal review. [UM-08](unified-domain-model/relational-implementations-and-projections.md#added-sqlglot-capabilities-disposition-and-limits)
records all added capability-family dispositions. Selected improvements include non-output
dependencies, pinned source composition, rich type descriptions, origin diagnostics and explicit
AST completeness admission, consumed by O02/O03. Exact v30.27.0 source confirms the remaining
PostgreSQL procedural-generation gap. Core-primary execution and native enforcement are retained;
no architectural rule change beyond the confirmed RC decisions is introduced.

Foundation conclusions:

- Comparison grouping needs its own checked projection; different fact/comparison identities can
  be legitimate. Preserve current policy behavior until an explicit semantic change is selected.
- Invariant failure codes become domain-facing promises only through an admitted enforcer and
  stable native diagnostic identity; SQLSTATE or message text alone cannot identify an invariant.
- Existing domain APIs and typed columns do not type every bind or row materialization. Generate
  actual signatures, expressions and materializers together; retain independent runtime admission.
- Relational execution stays set-based. Structured SQL-language body generation is feasible at
  the interface level; current AS-body custody and prosqlbody refusal require versioned changes.
- Resources and lazy-result ownership are runtime inputs/contracts, separate from semantic policy.
- O01–O03 must consume the same contracts and validators as real operations, without a second
  interpreter, schema authority or universal workflow framework.

## Rule decisions and architectural routes

| Item | Operator decision, 2026-11-01 | Consequence / route before dependent implementation |
|---|---|---|
| RC01 | Accept | Domain APIs and model-derived Core authoring; UM-00 amends D2/D3/D8 ownership detail through the governing ADR route where binding meaning changes. Completed PG-plan history is not rewritten. |
| RC02 | Accept | Structured SQL-language bodies with versioned inventory/custody/catalog/admission; UM-00/06/07 update D3 and the relevant accepted decision through its existing ADR route before new admission. No automatic general procedure/PLpgSQL support. |
| RC03 | Accept | Qualify and deliver a useful model-bound projection analysis consumer. UM-08 selects an exact SQLGlot release after verification; normal dependency selection alone needs no ADR. Changed authority would. |
| RC04 | Reject | Retain §B4 server-side enforcement and restricted writers. No client-side replacement of protected publication or added publisher privileges. |

## Reading route and ownership

| Companion | Owns |
|---|---|
| [Semantic contracts and policies](unified-domain-model/semantic-contracts-and-policies.md) | UM-01/02, comparison and invariant semantics; shared contract authority |
| [Typed domain operations](unified-domain-model/typed-domain-operations.md) | UM-03, generated requests/results/callables and materializers |
| [Relational implementations and projections](unified-domain-model/relational-implementations-and-projections.md) | UM-05/08, Core recipes and SQLGlot analysis |
| [Native authoring and evolution](unified-domain-model/native-authoring-and-evolution.md) | UM-06/07, native generation, custody/admission and frozen evolution |
| [Query compatibility and serving](unified-domain-model/query-compatibility-and-serving.md) | UM-04, old-run query meaning and complete serving journey |
| [Execution resources and transport](unified-domain-model/execution-resources-and-transport.md) | UM-09/10, configured execution, lazy results and directional transport |
| [Operation explanations, semantic impact and validation](unified-domain-model/operation-explanations-semantic-impact-and-validation.md) | UM-11/12/13, real CLI/MCP operator/agent capabilities |
| [Integration, adoption and qualification](unified-domain-model/integration-adoption-and-qualification.md) | UM-14/15, combined consumer coverage, adoption and acceptance |

Companions explain local designs, mechanisms, alternatives and package acceptance. They link here
for mutable package state. Shared model declarations, generator inputs, manifests and generated
outputs require one writer per integrated slice. Logical independence does not confer concurrent
edit ownership. Document boundaries are not execution barriers or permanent worker assignments.

## Package queue and working prerequisites

All rows are **Planned**. The table is the sole current package-state owner. A prerequisite means
usable contract/behavior, not that an entire companion must finish. Early contracts and later
admission/consumer closure are deliberately separate.

| Package | Required working input | Delivered behavior / completion boundary |
|---|---|---|
| UM-00 | Confirmed decisions and current owner/source snapshot | Architecture/rule amendments, explicit supported versions and source-to-consumer baseline for this series; no new audit |
| UM-01 | Effective property definitions and current comparison policy | Checked comparison context/meaning/evidence projection, used by scientific decisions without changing fact identity |
| UM-02 | Current invariant/enforcer/operation definitions | Observable versus descriptive invariant contract and qualified diagnostic mapping consumed by real enforcers |
| UM-03 | Settled request/result concepts; UM-02 only for promised failure mapping | Generated typed domain calls, binds, Core/result projections and materializers used by initial and remaining owned callers |
| UM-04 | Existing serving protocol; settled implementation compatibility binding | Archived-run query/continuation/explanation/evidence meaning is compatible or explicitly refused |
| UM-05 | UM-03 signature/projection contract slice, not full caller migration | Model-bound Core companion and inference recipes replacing independently authored relational text |
| UM-06 | UM-02 enforcement contract and UM-05 selected native expression recipes | Structured native declarations and eligible SQL-language bodies with versioned identity/dependency/admission |
| UM-07 | UM-06 first qualified desired product plus existing Alembic lifecycle | Frozen forward native transitions, before/after drift/ACL/recreation controls; old revisions unchanged |
| UM-08 | One settled UM-05 companion recipe and model/native signature metadata | Qualified projection type/dependency analysis with SQLGlot, unknowns explicit, used by UM-12 |
| UM-09 | Existing Settings and AnalysisScope owners | Non-default resources reach operations; supported lazy results enforce owner lifetime |
| UM-10 | UM-03/05 directional operation contracts and relevant UM-09 owners | Model-derived exact transfer/decoding used in actual publication and analytical read/export |
| UM-11 | Operation/state/binding contracts plus actual owner checks | CLI/MCP operation/prerequisite explanations; effects recheck atomically |
| UM-12 | UM-01/02 semantics, UM-05 projection dependencies, relevant UM-08 analysis | CLI/MCP semantic impact and declared consumer changes, with conservative unknowns |
| UM-13 | Existing validator outputs and an early shared diagnostic contract | Model/path/operation/scope-located diagnostic consumers preserving failure categories |
| UM-14 | Working producer and affected consumer products from each package | Remaining maintained callers migrated; replacement paths retired and supported archives/adoption reconciled |
| UM-15 | All selected functional scope and UM-14 final-source integration | Required functional/native/provider/nonfunctional union has applicable evidence; honest unresolved/benefit limits |

Useful order: begin UM-00 and shared contract definition; UM-04 and UM-09 can progress independently.
Develop UM-01/02 and UM-03 contracts early, then UM-05/06/07 and UM-10 as working products become
available. UM-13's diagnostic contract can precede its full consumer delivery; UM-08 can begin from
one projection. Deliver O01/O03 incrementally with actual operations; O02 follows semantic
contracts. Producers migrate their directly affected consumers within their package. UM-14
completes the remaining inventory; it is not permission to postpone required integration.

## Source-review disposition and retained alternatives

This table schedules new review obligations, not a second copy of an older plan's DA progress.
Original audit IDs and older scheduled homes remain linked; this series owns its R/O delivery.

| Source item | Package owner | Closure obligation |
|---|---|---|
| R01 / DA-001 | UM-01 | Explicit checked grouping, independent coarser-grouping and invalid-reference controls |
| R02 / DA-028 | UM-04 | Old-run plugin edit through real CLI, continuation, explanation and evidence |
| R03 / DA-027 | UM-02 | Qualified invariant/diagnostic contract realized by enforcers, not metadata parity alone |
| R04 / DA-020 | UM-09 | Resource propagation and lazy-consumption supported boundary |
| R05 | UM-03 | Static call/parameter/result continuity plus runtime output admission |
| R06 | UM-05 | Single model recipe, Core consumers, exact scope/null/multiplicity semantics |
| R07 | UM-06/07 | Structured native authoring/custody and explicit procedural-family disposition |
| R08 | UM-08 | Useful qualified projection analysis and actual impact consumer |
| R09 | UM-10 | Exact directional codecs and existing transaction/snapshot ownership |
| O01 | UM-11 | Actual CLI/MCP applicability explanation and stale-preflight refusal |
| O02 | UM-12 | Changed qualifier/result/projection consumer impact plus explicit unknown |
| O03 | UM-13 | Invalid value/cross-record/validator-failure diagnostics through actual consumers |
| Review §§3/6/8–12 | UM-14/15, plus local owners | All maintained consumers, qualified relationship/lifecycle/substitution/growth/failure cases and truthful acceptance |

LinkML-Map 0.5.4 remains a candidate for a named pure translation, not publication replacement;
join multiplicity, exact types and provenance must fit. LinkML-Datalog 0.2.0 remains a candidate
for a required inference family beyond the selected qualified SQL kernel; numeric/provenance and
modern compatibility gaps remain. Selective ORM requires a named editable aggregate. Universal
SQL/procedural DSL, central SQLGlot IR, arbitrary archived-code execution and client enforcement
replacement are not selected. These choices and revisit triggers remain in the relevant companion;
no library adoption quota follows from coverage of eighteen guides.

## Mechanism and evidence preservation

Each implementing package owns its local explanation of authoritative definition → exact library
APIs/composition → real consumer → preserved guarantees and failure case, including versions,
primary/installed source pointers and residual obligations. Selected/candidate/unresolved are
choice labels, distinct from Proposed/Interface-checked/Implemented/Tested/Measured.

Reuse the focused [semantic](../library_leverage/libraries/unified-model-semantics_2026-11-01.md),
[boundary](../library_leverage/libraries/unified-model-boundaries_2026-11-01.md) and
[PostgreSQL](../library_leverage/libraries/unified-model-postgresql_2026-11-01.md) assessments.
Exact versions are not silently promoted from newer addenda: current review pins include
LinkML/runtime1.12.1, RDFLib7.6.0, pySHACL0.40.1, Valuesets0.4.2, Pydantic2.14.1,
settings2.16.1, jsonschema4.26.0, Arrow26.0.0, DuckDB2.0.0; SQLAlchemy2.1.6,
Alembic1.20.1, pglast8.7, Psycopg3.3.6/pool3.3.3, pgpq0.12.0, ADBC1.13.0.
SQLGlot30.27.0 is researched but uninstalled. UM-00 reconciles actual pins before execution;
needed version moves are deliberate, exact and affected-test scoped, not a wholesale upgrade.

## Investigations, acceptance and current boundary

Companions own bounded investigations with settling evidence and dependent packages: generated
static signatures, structured-body server/custody equivalence, delayed iterator behavior,
serializer equivalence, SQLGlot projection fidelity, and any selected transport/type substitution.
Each outcome must change a choice, allow dependent work or leave a named obligation open.
No investigation is a pretext for a broad benchmark campaign or another library survey.

[UM-14/15](unified-domain-model/integration-adoption-and-qualification.md) defines the combined
acceptance and later discrete PDF drift reconciliation. Independent semantic expectations,
native authorization/concurrency, actual CLI/MCP use and maintained consumer migration matter;
annotation existence or self-round-tripping does not establish correctness. Run targeted checks
during implementation; final maintenance precedes integrated qualification at complete scope.
No speed, memory, capacity or quality improvement is established by these plan documents.

**Next:** execute UM-00 and ready shared-contract/UM-04/UM-09 work only after implementation is
separately authorized. At authoring completion, all packages remain Planned; historical PDF/PG
receipts are context, not qualification of this series.
