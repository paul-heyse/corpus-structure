# Unified domain model: typed operations and generated realization

**Status:** Active — completion audit found bounded delivery plus implementation/consumer gaps; product qualification failed, assembled acceptance open (2026-11-02).
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

## PDF consumer reconciliation

**Scoped plan amendment, 2026-11-01; target Proposed, all UM packages remain Planned.**
The operator selected updating this series only. This is the discrete reconciliation for the
published-document consumer case; other changed PDF contracts still require focused reinspection
before dependent execution. It changes no PDF package state or execution scope, architecture,
database, dependency or operational default. Existing RC01–RC04 decisions remain in force.

Inspected source `5dec0c2f` and identified dirty PDF/status/evidence context. Read-only inspection
of owned `corpus_pdf_20261101` found published task10/product `integrated`, logical digest
`d3482c7126a5db75d8bb1962bb34cabd1b8f772bc136cd3f5987744dfec7bce0`.
The subsequent source-preparation attempt failed constraint
`fk_source_view_native_task_id_native_product_key_sectio_e425`. Source-view publication reads
the new published record projection, while the physical model/FK still targets
`kb.native_document_item`; rendered-artifact FK likewise targets `kb.native_document_region`,
and rendering still directly selects that old relation. Integrated reuse also reconstructs,
serializes and reloads the book merely to prepare selected sections. These are inspected
foundations/gaps, not UM implementation results. The [PDF coordinator](pdf-docling-pipeline_2026-10-31.md)
retains current deployment, repair and actual consumer/provider/evaluator/default acceptance.
This amendment does not promote that publication to completed knowledge or full qualification.

The shared target connects an enforced published-address invariant, typed domain operations,
model-bound selected-section projection and native effect relationships. The
[relational companion](unified-domain-model/relational-implementations-and-projections.md#published-document-consumers)
is the single technical owner of binding keys and projection design; UM-02 owns invariant meaning.
Build/revision placement stays internal, preserving semantic product pins and original/frozen
evidence. Existing publication can feed newly prepared consumers; consumer-only changes do not
require recognition or whole-book republication. Necessary global validation and explicit complete
exports retain their own guarantees. No new identity registry, parallel schema or benchmark follows.

| Existing package | Required contribution to this case |
|---|---|
| UM-00/02 | Reconcile actual PDF prerequisite; resolve enforced relationship and operation/state/failure meaning. |
| UM-03/05 | Typed request/result/bind/materializer continuity, selected projection and shared read/effect endpoint binding. |
| UM-06/07 | Model-derived composite constraints, native insert/replay correspondence and frozen forward admission. |
| UM-09/10 | Appropriate selected/batch reads, resource propagation, snapshot/cancellation and retained immutable assurance. |
| UM-11/12/13 | Shared prerequisite explanation, declared relationship impact and model/address-located native diagnostics. |
| UM-14/15 | Actual affected-consumer closure and independent small native success/refusal/recovery journeys. |

The case extends R03/R05/R06/R07/R09 and O01–O03 through their existing owners, without inventing
new review findings or duplicating scheduled PDF obligations. SQLGlot analysis remains qualified
projection evidence, not proof of native relational enforcement. UM-04's query-compatibility
contract and UM-01's scientific comparison obligations remain unchanged.

Define shared contracts early; integrate each producer with the consumers it changes once its
required PDF foundation is usable. Do not defer a broken effect-side relationship to final UM-14
cleanup or make unrelated UM work wait for the whole PDF series. If PDF repairs land first,
inspect and reuse their actual binding/reader contracts rather than implement a second route.
The [UM-14/15 acceptance case](unified-domain-model/integration-adoption-and-qualification.md#published-document-consumer-acceptance)
owns the additional planned controls. No production test or provider result is established by
this plan amendment; historical receipts retain their dates, source and scope.

Amendment authoring checks (2026-11-01): `git diff --check` passed; bounded document review
found no material ownership/status/link issues. `just docs-check` failed on existing deferred
library-reorganization links, with no reported UM-series error. Product tests and provider
execution were not_run for these documentation changes. Read-only catalog inspection establishes
only the publication/constraint baseline above, not assembled UM or PDF acceptance.

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

The table is the sole current package-state owner. Early implementation is not assembled qualification. A prerequisite means
usable contract/behavior, not that an entire companion must finish. Early contracts and later
admission/consumer closure are deliberately separate.

| Package | State | Required working input | Delivered behavior / completion boundary |
|---|---|---|---|
| UM-00 | In progress | Confirmed decisions and current owner/source snapshot | Architecture/rule amendments, explicit supported versions and source-to-consumer baseline for this series; no new audit |
| UM-01 | In progress | Effective property definitions and current comparison policy | Checked comparison context/meaning/evidence projection, used by scientific decisions without changing fact identity |
| UM-02 | In progress | Current invariant/enforcer/operation definitions | Observable versus descriptive invariant contract and qualified diagnostic mapping consumed by real enforcers |
| UM-03 | In progress | Settled request/result concepts; UM-02 only for promised failure mapping | Generated typed domain calls, binds, Core/result projections and materializers, including published-document consumers with private placement bindings |
| UM-04 | In progress | Existing serving protocol; settled implementation compatibility binding | Archived-run query/continuation/explanation/evidence meaning is compatible or explicitly refused |
| UM-05 | In progress | UM-03 signature/projection contract slice, not full caller migration; working PDF foundation for its consumer case | Model-bound Core companion/inference recipes plus published-address read/effect bindings and selected-section projection |
| UM-06 | In progress | UM-02 enforcement contract and UM-05 selected native expression recipes | Structured native declarations and eligible SQL-language bodies with versioned identity/dependency/admission |
| UM-07 | In progress | UM-06 first qualified desired product plus existing Alembic lifecycle | Frozen forward native transitions including changed consumer constraints/inserts/replay, before/after drift/ACL/recreation controls; old revisions unchanged |
| UM-08 | In progress | One settled UM-05 companion recipe and model/native signature metadata | Qualified projection type/dependency analysis with SQLGlot, unknowns explicit, used by UM-12 |
| UM-09 | In progress | Existing Settings and AnalysisScope owners | Non-default resources reach operations; supported lazy results enforce owner lifetime |
| UM-10 | In progress | UM-03/05 directional operation contracts and relevant UM-09 owners | Model-derived exact transfer/decoding used in actual publication and analytical read/export |
| UM-11 | In progress | Operation/state/binding contracts plus actual owner checks | CLI/MCP operation/prerequisite explanations; effects recheck atomically |
| UM-12 | In progress | UM-01/02 semantics, UM-05 projection dependencies, relevant UM-08 analysis | CLI/MCP semantic impact and declared consumer changes, with conservative unknowns |
| UM-13 | In progress | Existing validator outputs and an early shared diagnostic contract | Model/path/operation/scope-located diagnostic consumers preserving failure categories |
| UM-14 | In progress | Working producer and affected consumer products from each package | Remaining maintained callers migrated; replacement paths retired and supported archives/adoption reconciled |
| UM-15 | In progress | All selected functional scope and UM-14 final-source integration | Required functional/native/provider/nonfunctional union has applicable evidence; honest unresolved/benefit limits |

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
SQLGlot30.27.0 is now installed exactly (2026-11-02). UM-00 reconciled actual pins;
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

**Next:** resolve the completion-audit obligations below through their existing package owners, then reassess affected functional evidence and the required acceptance union. Historical PDF/PG receipts retain their scope and do not qualify UM replacements.

## Execution checkpoint — 2026-11-02

The operator authorized the complete UM-00–15 execution approach. ADR-0046 records accepted RC01–RC03 realization boundaries while preserving RC04; D2/D3/D8 and DESIGN §B4/§B5 carry the target. SQLGlot30.27.0 was added exactly, with only its intended lock/dependency changes; `just ready` passed. These steps do not establish UM-08 analysis or native body support.

One writer owns shared model/preparation/archive/generation changes; separate owners implement query compatibility and resource/lifetime consumers. Current source/body profiles, frozen migrations, book task10 pin and dirty concurrent PDF/library files remain preserved. Independent focused checks precede complete-scope qualification. Available disk was about6GB at kickoff; small owned tests and retained products avoid full database/book copies. No cache/database/evidence cleanup was performed.

Product qualification has a failed completed attempt; required-union and applicable provider obligations remain open, as assessed below.

### Integrated implementation checkpoint — 2026-11-02

The working tree implements checked comparison/PRESENT contracts, qualified invariant diagnostics,
87 fixed correspondences (76 native and11 Core), query implementation custody, execution resources
and lazy ownership, finite relational/projection analysis, and model-bound reports. Core registration
and document/rendition/original custody retain their named algorithms while generated requests,
TypedColumns/closed column protocols, value projections and strict materializers own correspondence.
Dynamic configuration, domain records, fixed-point working relations and Arrow families retain their
existing checked boundaries. Static continuity is not a claim to infer every algorithm from schema.

Compiler23 distinguishes native versus Core binding products. Exact20–22 archive decoding remains
separate from current source/effect admission; immutable products are not re-normalized through
current capabilities. Actual old20 static CLI/MCP inspection and explicit unsupported subject refusal
passed with the current23 reader. Full query continuation/plugin-edit/compatibility journeys passed
under their scoped custody owner. Report changes retain exact member facts, absence/null and ordered
membership; native diagnostics retain available producing model/release and original failure scope.

Forward83–90 are frozen. The current desired native state has61 objects and12 SQL-standard bodies.
The original published-address constraints/backfill remain unchanged; observation-only retention
replaces current aggregate document writes. Current native support checks resolve every declared
edge against exact input pin, coverage ID, scope and family; integrated complete coverage needs a
complete witness. Native intrinsic coverage and weaker/mixed cases retain their declared meanings.
Validation epochv5 rejects stale unfinished receipts. Published reads instead use their original
immutable receipt, keeping projection and schema-source contracts distinct. The final descriptor-only
successors bind the actual callback/operation source; they do not change native policy or epoch.
See the [native evidence](../design_review/evidence/2026-11-02_um-native-evolution/README.md).

Scoped tests include76 shared Core/archive/resource controls,28 added receipt-call controls,
19 optional-support callback controls and25 current report/product controls. Native authoring,
actual admission, frozen82→90 replay, drift/stale-state refusals, exact empty candidates and outer
rollback passed. Counts overlap and are not added. Failed/interrupted receipts remain unchanged;
formatting does not itself invalidate typing or functional results.

Assembled acceptance is still open. Earlier native88 failures and their affected repairs retain
individual receipts. Repository-root qualification initially passed281 cases with2 fixture failures
(`build/test-receipts/qualification/20261102T131710Z-2800697`); those same2 corrected fixtures passed
in `build/um-root-retained-fixtures-00001.log`, without repeating unaffected cases. The product run
completed with3107 passed/30 failed/0 skipped. Its exact failures and applicability are assessed in
the completion audit below. Rust exited0 with zero tests, establishing no Rust functional coverage.
Package/local passes do not close UM-14/15 or import PDF provider/book/default acceptance.

No target deployment occurred. Actual task10 retained-v4 receipt inspection was read-only; the book
remains at82 and was neither recognized again nor republished. The PDF coordinator retains its
operational/provider/evaluator/default-adoption obligations.

## Completion audit — 2026-11-02

**Boundary and source.** Assessed every claimed Implemented/Tested or completed subscope in this
coordinator and all eight companions, including claims inside In-progress packages. No package
was declared wholly complete: UM-00–14 remain In progress; UM-15 now records the qualification
attempt as In progress. Read-only independent reviews covered semantic/Core contracts, native/
resource realization and query/report consumers; the coordinator reconciled authority/adoption
and acceptance. Inspected HEAD `4a95c219b444c70c46d9cdb997cf70c2f6989c3a` plus staged/unstaged UM
implementation and frozen83–90. Pre-publication tracked `git diff HEAD --binary` SHA256 was
`3da300dc7c4d8ba269ce7bb104498f93444e81be895860ebae6374330ca45e24`.
Concurrent PDF/library changes were preserved. No production repairs, tests, database changes,
provider calls or broad diagnostic-audit updates were performed for this completion audit.

**Implementation judgment.** ADR-0046 and D2/D3/D8 implement the selected authority amendments.
Checked comparison/invariant declarations, generated fixed-call boundaries, Core inference,
query implementation custody, bounded native authoring/evolution, resource/lazy ownership,
directional transfer and report products have real maintained consumers. This is substantive
partial delivery, not annotations alone. It is not complete delivery of the accepted series:
archive compatibility, base-protocol caller migration, native preview and selected export settings
have concrete defects. Selected analysis and diagnostic consumer capabilities remain unfinished.

**Library judgment.** Pydantic reusable adapters/strict boundaries, SQLAlchemy typed Core plus
closed column protocols, pglast SQL-standard bodies and PostgreSQL-normalized dependencies,
Alembic frozen transitions, Psycopg/pgpq caller-owned writes, Arrow/ADBC snapshot reads and DuckDB
borrowed-result guards are used substantively. The retained small semantic serialization visitors
have a concrete supplied-value/reference/presentation rationale (UM-I03), and specialized protected
procedural kernels have explicit family dispositions; neither is a missing-library finding.
Current SQLGlot qualification/type/scope/lineage is real for materialized recipes, but does not
settle the selected nested source-composition profile. Graph reporting and typed catalog
observation also need the dispositions below. Candidate LinkML-Map/Datalog/ORM and new transport
profiles are not library-adoption quotas.

### Remaining obligations and disposition

All rows below are **open**, owned here for current disposition; companions retain technical detail.
These refine R01–R09/O01–O03 delivery without changing their source IDs or older finding homes.

| ID / owner | Missing obligation and source evidence | Repair or settling evidence required |
|---|---|---|
| UM-CA01 — UM-03/04/14 | Historical schema reconstruction applies current numeric-bound lowering: `semantic/archive_reader.py:229–264`, `boundary.py:33–43,200–203`. Retained compiler10 and historical capture fail on `38` versus `{'decimal':'38'}`. Exact archived bytes alone do not preserve an executable supported reader. | Version-aware reconstruction preserving producing schema meaning/identity; independently expected historical query/capture and current numeric-schema controls. Never rewrite archives or skip schema comparison. |
| UM-CA02 — UM-03/14 | `operations.end_source_run:1696–1706` and `orchestrate/project.py:57–62` unconditionally select composed projection admission for semantic-1 runs, although the native base protocol remains supported. Native cancellation/hold and explicit project-init cases fail before effects. | Restore an explicit supported base route or settle an authorized transition, retaining strict current composed context checks; actual cancellation/late-completion/hold and project-init controls. |
| UM-CA03 — UM-06/07/14 | `cli/schema.py:160` → `forward_products` → `pdf_publication_native.py:1507` requests admission without server-normalized dependencies. `source_view_native.py:327–328` correctly refuses. Nine product failures include actual `schema derive` routes. | Integrate a supported preview with the normalized native pipeline, or explicitly retire/migrate its maintained callers; CLI and changed-model preview controls, preserving unbound deployment refusal. The working native-candidate/replay route remains valid bounded evidence. |
| UM-CA04 — UM-09/14 | `serve/companion_export.py:129–133` ignores `analytics.adbc_driver_path` and uses the default driver, unlike capture. Driver selection is an accepted invocation resource. | Configured driver reaches actual export acquisition with snapshot import, batch options, cancellation and lifetime preserved. |
| UM-CA05 — UM-08/12/13 | `projection_analysis.py:148–185` lowers current derived sources as CTEs and runs qualification/types/scope/lineage. The selected finite external-source expansion profile and nested/collision/opaque/placeholder/type controls are not delivered. Current materialized-recipe lineage is not thereby wrong. | Deliver the selected source-map capability and its actual impact/diagnostic consumers, or document a justified equivalent/authorized narrowing preserving its guarantees; do not expand materialized objects merely to use `exp.expand`. |
| UM-CA06 — UM-13/14 | `graph_validation_report` has no production caller; `ontology.validate_projected_graph:983–995` returns raw GraphValidation. Direct adapter tests do not migrate graph-validation/CLI/MCP consumers. | Connect existing validator outcomes to the shared located projection at maintained consumers; independent actual nonconformance, shape and execution-failure responses retaining raw RDF report identity and scope. |
| UM-CA07 — UM-13/14 | `cli/failures.py:59–61` and `semantic/refusals.py:66–73` call failure projection without available release/operation context. Invalid live subject after `cli/schema.py:403–409` opened the release yields path/category but loses release/model/operation. | Preserve known context across actual CLI/MCP failure translation; assert independent release/model/operation/path/category, retaining unknown context when genuinely unavailable and native cause distinctions. |
| UM-CA08 — UM-06 | Selected Inspector/typed Core catalog observation remains unresolved: specialist catalog SQL in `native_objects.py:277–317,368–386` and `native_sql_body.py:170–178` remains textual. Inspector incompleteness explains partial retention, not the entire typed-Core substitution. No runtime-invalidity claim follows. | Complete applicable typed observation migration or reconcile a concrete equivalent/necessary retained-kernel rationale against the selected target. Metadata parity alone cannot establish independent admission. |
| UM-CA09 — UM-03/14 | `test_typed_realization.py:28` detects stale `_typed_columns.py` physical-model identity. Generated-field correctness is not established by leaving the drift check failed. | Reconcile generation with the authoritative physical model, inspect the actual generated delta and pass drift plus relevant static positive/negative controls. |
| UM-CA11 — UM-12/14 | `compare_semantic_releases` reaches standalone CLI diff/MCP comparison, but no compatibility/regeneration-advice consumer. The accepted advice workflow in the report companion remains unimplemented. | Feed the shared impact result into existing advice, retaining changed definitions and explicit unknowns without granting activation/migration authority. |
| UM-CA12 — UM-03/14 | Public nested `CompletionReceipt` still declares task/run/attempt as `int` and release as `str` (`_operation_calls.py:78–85`, `contracts.yaml:35–43`, nested generator:400–421). Top-level call IDs do not establish nested identifier continuity. No runtime corruption is established. | Model-derived nested identifier distinctions and real positive/negative typing of completion results, alongside unchanged native wire validation. |
| UM-CA10 — UM-14/15 | Failed product qualification, unmigrated retired-writer/export test paths and empty declared required-obligation coverage leave acceptance open. UM-11 live-evaluator and stale-preflight→atomic-refusal acceptance is still explicitly outstanding. Nine obsolete-message assertions and obsolete compiler/hash/PRESENT assumptions are test migration, not proof the corresponding refusal/feature is defective. Rich mapped-document custody refusal still needs fixture-versus-producer diagnosis. | Faithfully migrate tests without weakening independent expectations; resolve remaining real defects, diagnose custody, map the required union and rerun only affected scope unless shared changes require broader reassessment. Preserve all failed receipts. |

### Verification, benefits and next work

**Failed, completed product attempt:**
`uv run python scripts/test_receipts.py run --python-only --out-dir build/test-receipts/qualification/20261102-um-product-agent -- python/corpus-structure/tests --failed-first`.
The retained classification reports3137 selected,3107 passed,30 failed,0 skipped; all failures are
call-phase, with no collection errors, worker loss or active phases. Exact nodes and causes live
in that directory's `failure-summary.json`. Its empty `required`/coverage lists do not establish
the UM-15 required union. The receipt source hash differs from this audit's dirty baseline;
retain its recorded context and assess affected applicability rather than asserting final-source
qualification or discarding all passing results. The audit itself introduced documentation only.

**Passed, bounded prior evidence:** query/plugin-edit/continuation/explanation/evidence journeys,
frozen83–90 authoring/admission/replay/drift/role/rollback, current recipe analysis and Core/ADBC/
Parquet presence controls retain their original dates and limits. Frozen rehearsal is not book
deployment. Query-specific controls do not close the shared historical reader defect. Counts
from overlapping selections are not added. Types passed at recorded shared/scoped endpoints;
no new type/test run was needed for this document audit, and formatting does not invalidate them.
Final applicable hygiene and required-union acceptance remain open, not falsely reported passed.

**Benefits:** structural single-source correspondence, bounded selected reads and shared adapters
are source-inspected; no quantified speed/memory/quality benefit is established or required here.
Complete behavioral equivalence, universal lineage and PDF provider/default adoption are not
inferred. No new benchmark, validator framework, alignment lint or audit-premise refresh is needed.

**Next execution:** address UM-CA01/02/03/04/06/07/11/12 and generated drift at their existing model/consumer
owners; settle UM-CA05/08 capability realization without silently reducing accepted scope; then
finish UM-CA10 acceptance. Changes to captured native inputs require proper forward evolution,
not edits to frozen83–90. The audit authorizes these plan corrections, not production repairs.

**Audit publication checks (2026-11-02):** `git diff --check -- STATUS.md
 docs/plans/unified-domain-model docs/plans/unified-domain-model_2026-11-01.md` passed;
static document inspection found twelve unique owned obligations and audit conclusions in all eight
companions. `just docs-check` failed on deferred library-reorganization links, including pre-existing
links in the UM plans; log: `build/um-completion-audit-docs-check.log`. These references are not newly
introduced audit links and were not repaired as part of this audit. No product/type tests were
rerun. Root `just turn-end` passed (`build/um-completion-audit-turn-end.log`): all779 Python files were unchanged. This maintenance neither repaired product defects nor invalidated prior type/functional evidence.

## Current-only execution amendment — 2026-11-02

The operator approved all remaining scope plus repository legacy retirement, and selected resetting
all seven identified project-result databases on5434. ADR-0047 changes the supported runtime target:
current composed execution and record PDF publications only, with immutable current release custody.
UM-CA01/02 are now authorized retirement/transition work, not promises to repair historical results.
All other UM-CA obligations remain open until implementation and actual controls close them.

The audited203-file working implementation was committed as63cc99e5 before isolated concurrent work.
Three sparse worktrees exclude large evidence payloads. A mistaken full checkout was removed before
work began; no original evidence was deleted. After exact OID/owner/zero-client verification, all
seven selected result databases were dropped. Receipt build/um-current-result-reset.json records
24,341,479,424 bytes reclaimed (about22.67GiB); filesystem free space increased from about11GiB to33GiB.
Templates and the separately owned authoring database were preserved. No fresh intake has run yet.

Execution owners: current-model/generators/runtime and historical document removal; report/analysis/
graph/advice integration; native observation/authoring/export; root integration, legacy executor
retirement, forward freezing, fresh bootstrap/intake and final qualification. All reported passing
predecessor checks retain their limits. Final source must be qualified after broad retirement.
