# Semantic-model pivot — series coordinator

**Status:** SP-00–SP-05 implemented within their declared supported profiles; scoped acceptance below. SP-06/SP-07 are implemented and scoped-tested for their supported profile, including exclusions (§11). SP-C01–SP-C05 and supported admission closure are implemented and scoped-tested in §10; SP-08 consumers are implemented with scoped checks and an open native model-binding defect; SP-09 has selected statistics/transfer results and an incomplete fresh-frame journey; SP-10 qualification is incomplete (§12). **Created:** 2026-10-29 · **Revised:** 2026-10-29.
**Claim strength:** ADR-0024–ADR-0027 govern the accepted baseline. The completeness extension is implemented and scoped Tested for transitioned supported operations. Implemented/Tested claims are bounded to the declared package profiles and receipts; consumer cutover and assembled qualification remain open.

## 1. Scope, authority and baseline

Implement the whole target in the [functional review](../functional_reviews/semantic-postgresql-model_2026-10-29.md) and [target model](../functional_reviews/semantic-postgresql-model_2026-10-29_target-model.md), consumed at `5ba9a5c`. Select O01–O06 together. The result is one executable semantic model governing dynamic classes, attributes and relationships, required ontology dependencies, PostgreSQL authority, and every affected current consumer.

This is the dedicated pivot series. Plans outside this series keep their scopes/statuses. Their findings retain their current owners, especially [phase 0 §11](phase-0_2026-10-28.md#11-findings-disposition). This series owns only its pivot packages and new pivot issues; it does not copy old findings, certify their closure, or silently absorb unfinished phase 0 features. Replacement of current consumers and capabilities necessary to demonstrate the new target are in scope. Unrelated provider additions and product features are not.

Foundation execution began from `cea3f73`; its scoped implementation source is `7474f7a` (2026-10-29).
The selected legacy core/system model and generated physical metadata remain byte-identical to
that starting selection. Supplied documents and prior dirty work were already committed at
execution start. Those are foundation-era facts, not the current execution baseline. The originally
pending sibling worktrees were subsequently integrated during closeout (§9). The completeness extension was planned from `dcc5e0b`; current execution is recorded in §12
at `feeefad`. Inspect changed source/context before further execution.

The [completeness review](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md)
and [target model](../functional_reviews/semantic-domain-model-completeness_2026-10-29_target-model.md)
at `dcc5e0b` add O01–O07 selected for planning by the operator's 2026-10-29 instruction.
They strengthen already-transitioned behavior; §10 owns their current disposition. The original
review's O01–O06 retain their distinct identities in §6. Existing receipts stay passing and scoped.
The original plan-extension baseline included preserved uncommitted work; no production work was
performed while creating that extension. Subsequent authorized implementation is recorded in §10.

Use the [architecture map](../design/README.md) and owning D1–D8 sections for current contracts, then the approved decision work below for replacements. Core 3.3, efficient-architecture heuristics and profile 1.4 selected by `standard.toml` govern design; their test-assessment companion governs evidence design. This focused foundation assessment does not initiate a broad diagnostic audit. Apply existing review cadence at changed architectural boundaries.

## 2. Rule changes confirmed by the operator

Each item was **accepted for planning, 2026-10-29**, through explicit confirmation in the plan-creation conversation. Acceptance is not an implementation claim or a completed ADR.

| Source impact | Accepted consequence | Scheduled route |
|---|---|---|
| Review RC01 | Replace frozen claim/key forms where needed; separate assertion occurrences, semantic facts and identity | SP-00: ADR/DESIGN D1, §B1, ADR-0023 successor/amendment route |
| Review RC02 | Unified immutable semantic releases and registry-backed dynamic domain storage | SP-00: §B4/§B5, D2/D3 and ADR-0020/0022 decision routes |
| Review RC03 | Explicit observation, consolidation, publication and derived-fact responsibilities | SP-00: §B2, D5/D6, affected ADR-0014/0019 routes |
| Review RC04 | New interchange/query bindings and required internal ontology/RDF validation | SP-00: D7/D8, §1.2, ADR-0021 route |

Use superseding ADRs where accepted decisions change; accepted ADR text is immutable. Make actual owner amendments with those decisions during execution. Additional material rule changes require their own explicit decision; these four are not permission to change unrelated architecture.

### Completeness refinements and decision routes

The operator selected the completeness review for plan integration, not automatic production
execution or amendment of accepted ADRs. Static comparison with ADR-0024–0027 and DESIGN §B1/§B2/
§B4/§B5 found no required rule replacement. These impacts refine the accepted goals:

| Completeness-review §7 impact | Planned interpretation and route |
|---|---|
| Complete logical/execution model composition | SP-C01/SP-C02 define trusted code-versioned execution contracts and compatible domain releases; retain one composed authority and update D1/D2/D6 during implementation |
| Shared guards and stricter allowed transitions | SP-C03 realizes existing validity/fencing requirements with shared definitions and new frozen migrations; preserve D3/D5/D6 authority |
| Typed analytical input/publication dependencies | SP-C05 makes source snapshots and intent explicit without changing ADR-0026 arithmetic, snapshot or publication guarantees |
| Richer internal graph validation | SP-C02/SP-C05 extend faithfully enforced profiles; retain PostgreSQL transaction authority and qualified assertions |

Accepted ADRs remain immutable. Execution records clarifications at their architectural owners;
a genuine change to accepted meaning requires the existing confirmation/ADR route before dependent
work. In particular, domain-replaceable privileged lifecycles, weakened native enforcement,
changed decimal/snapshot guarantees, silently accepted required semantics or different inference
premise authorization are not approved by this planning selection. A current compiler refusal
is a supported-profile limit, not an operator rule requiring reconfirmation merely to extend it.

## 3. Combined target and foundation assessment

A release binds local LinkML sources/imports, pinned ontology artifacts, admitted axiom scope, materialized vocabulary membership, identity rules, operation/rule profiles and compiler versions. The data realization/snapshot is separate. Prepare immutable runtime lookups once; domain requests consume these rather than live SchemaView caches or mutable ontology services.

SQLAlchemy Core is the central relational realization: one model-derived `MetaData` describes the stable system/semantic tables, constraints and physical access paths. Typed Core expressions implement publication predicates, selection, joins and recursive closure; PostgreSQL executes them. Dynamic domain definitions become registry rows and handles over that stable schema, not a new `Table` for each class. LinkML owns meaning; MetaData owns its generated relational representation, not a second editable semantic model.

| Foundation inspected | Reuse and required change |
|---|---|
| `schema/model.py`, `lookup.py`, `batches.py`, `registry.py` | Reuse SchemaView resolution, frozen lookup and dynamic boundary generation. Replace installed-only interpretation/version dispatch with admitted release bindings and explicit supported-semantics coverage. |
| `schema/relational.py`, `core/db/_tables.py`, `overlay.py` | Already compile MetaData, native constraints and indexes. Generate the new stable semantic core and queryable typed values; remove table-specific meaning reconstructed elsewhere. |
| `core/db/store.py`, `repo.py` | Current store already has **one psycopg-pool owner**, SQLAlchemy `NullPool` and `creator=pool.getconn`. Preserve this composed route; do not add a second pool. Existing caller-owned transactions/COPY are useful, but admitted knowledge requires a protected publisher. |
| `consolidate/assemble.py` | Current fusion selects a canonical dump by claim key. Retain set kernels where valid; it cannot be the storage identity for independent assertion occurrences. |
| `pool/contract.py`, `load.py`, `duckdb_engine.py`, `write.py` | Existing Arrow schemas, coherent read transaction and scoped registrations are useful. Replace installed-schema/upcaster assumptions, lossy crossings and generic admitted-base-table writes. |
| Serving, intervention, orchestration and evaluation | Existing pins, fencing, evidence readers and comparison algorithms are reusable. Replace old key/table assumptions throughout, preserving unknowns, source fidelity and independent references. |

**Reconciliation with the review:** its O03 wording about retaining a SQLAlchemy pooling route did not identify the actual external psycopg pool/NullPool composition. Preserve the inspected single-pool composition. SQLAlchemy remains the execution and transaction boundary. No backend or dependency bump is needed merely to make this correction.

Pydantic is the release-derived validation/serialization bridge; Pydantic Settings owns process configuration only. pglast supplies authored-SQL AST inspection and dependency diagnostics, with catalog/role validation delegated to PostgreSQL. Alembic deploys physical metadata and explicit routines; no migration occurs for an ordinary new semantic class. These mechanisms are detailed in their owning supporting packages.

Occurrence identity is source/publication occurrence identity, including repeated items from one source. A separately keyed semantic fact groups compatible occurrences; confidence and support aggregation do not erase source records. Inference deduplicates eligible semantic conclusions while preserving premise/support references. Identity derivation and qualification live in the semantic plan, not in independently chosen storage/query hash recipes.

The completeness target adds typed logical relationship, state/transition, invariant, operation
and projection contracts to the existing semantic foundation. Trusted execution definitions and
release-authored domain policy compose through a versioned binding; ordinary domain functions
remain owners of specialized algorithms. [Completeness §2](semantic-model-pivot/domain-model-completeness.md#2-foundation-assessment-and-selected-design)
records the focused foundation assessment and selected realization. Current source/native protections
are reused, not discarded or assumed absent. No generic workflow engine or second graph authority
is introduced.

## 4. Documents and contract ownership

| Document | Owns |
|---|---|
| [Complete model and contracts](semantic-model-pivot/domain-model-completeness.md) | Added connected definitions, ownership, SP-C01/SP-C02 compiler/admission and compatibility contracts |
| [Complete model realization](semantic-model-pivot/domain-model-realization.md) | Added SP-C03–SP-C05 lifecycle/outcome/scientific/projection realization and current consumer adoption |
| [Semantic model and releases](semantic-model-pivot/semantic-model-and-releases.md) | Meaning, identities, supported ontology/constraint profile, release preparation and binding |
| [PostgreSQL and publication](semantic-model-pivot/postgresql-and-publication.md) | MetaData lowering, physical layout, Core execution, roles, transaction/COPY publisher |
| [Domain operations](semantic-model-pivot/domain-operations.md) | Evidence/producers, orchestration bindings, resolution, consolidation, validation and inference |
| [Interchange and analytics](semantic-model-pivot/interchange-and-analytics.md) | Arrow projections, coherent loading, DuckDB set operations and resource lifetime |
| [Queries and consumers](semantic-model-pivot/queries-and-consumers.md) | Semantic query handles, explain, agent/CLI/intervention contracts and evaluation |
| [Regeneration and acceptance](semantic-model-pivot/regeneration-and-acceptance.md) | Fresh realization, retirement, native journeys and whole-series qualification |

The two completeness documents own added work; existing documents retain baseline mechanisms and later-package responsibilities, with linked amendments. Architectural authorities remain DESIGN/D-documents and accepted ADRs. Supporting documents own package design and local evidence. This coordinator alone owns current package state, the executable queue and series disposition. Short summaries elsewhere are not additional status ledgers. Shared model declarations, generated metadata and manifests have one writer per integrated slice; logical independence does not authorize concurrent edits to those surfaces.

## 5. Dependencies and execution queue

SP-00–SP-05 are implemented within their declared profiles. SP-02/SP-03 supply fixed physical
metadata, exact archived releases, generation-checked activation and protected native publication.
Their [package owner](semantic-model-pivot/postgresql-and-publication.md) states capability/refusal
boundaries. SP-04 supplies native semantic reads/explanations; SP-05 supplies the columnar
foundation and existing set kernels. SP-06/SP-07 are implemented and scoped-tested for their supported profile, including exclusions (§11). Current SP-08–SP-10 implementation and remaining obligations are in §12. No assembled-series qualification is claimed. Stable IDs
link to the supporting documents.

| Package | Required working input | Capability (current state above and in §10) |
|---|---|---|
| [SP-00](semantic-model-pivot/semantic-model-and-releases.md#SP-00) | Confirmed RC01–RC04 and current owners | Architectural decisions, supported-profile contracts, exact library compatibility disposition |
| [SP-01](semantic-model-pivot/semantic-model-and-releases.md#SP-01) | SP-00 | Typed semantic core and pure compiler/binding for local model, ontology and value sets |
| [SP-02](semantic-model-pivot/postgresql-and-publication.md#SP-02) | SP-01 definitions and relational mappings | Fresh physical core, immutable release persistence and activation |
| [SP-03](semantic-model-pivot/postgresql-and-publication.md#SP-03) | SP-02 and SP-01 constraints/identities | Atomic protected publication, including COPY and concurrent constraint enforcement |
| [SP-04](semantic-model-pivot/queries-and-consumers.md#SP-04) | SP-03 plus SP-01 query mappings | Early declaration → qualified write → semantic query/explain native journey |
| [SP-05](semantic-model-pivot/interchange-and-analytics.md#SP-05) | SP-01; SP-02 for loader, SP-03 for publication integration | Lossless Arrow bindings, scoped snapshot loader and DuckDB kernels |
| [SP-06](semantic-model-pivot/domain-operations.md#SP-06) | SP-03; SP-04 early journey | All existing evidence/proposal producers and orchestration use release/data bindings |
| [SP-07](semantic-model-pivot/domain-operations.md#SP-07) | SP-06 and SP-05 | Consolidation/domain validation and qualified inference publish under the new model |
| [SP-C01](semantic-model-pivot/domain-model-completeness.md#SP-C01) | Delivered foundations and completeness review target | Connected logical relations, composed states and owned operation/invariant contracts |
| [SP-C02](semantic-model-pivot/domain-model-completeness.md#SP-C02) | SP-C01; admission closure additionally needs actual relevant SP-C03–SP-C05 enforcement | Normalized contract products, strict adapters, compatible exact archives and required invariant admission |
| [SP-C03](semantic-model-pivot/domain-model-realization.md#SP-C03) | SP-C02 contract products and delivered native/source mechanisms | Model-governed lifecycle, all-writer guards and protected atomic effects |
| [SP-C04](semantic-model-pivot/domain-model-realization.md#SP-C04) | SP-C02 contract products; SP-C03 for integrated publication | Typed outcomes, assessments, scientific and qualified inference behavior |
| [SP-C05](semantic-model-pivot/domain-model-realization.md#SP-C05) | SP-C02 contract products, SP-04/SP-05, relevant SP-C04; SP-C03 for publication | Faithful graph/read/analytical projections, provenance and lifetimes |
| [SP-08](semantic-model-pivot/queries-and-consumers.md#SP-08) | SP-04 and required SP-07 outputs; relevant SP-C03–SP-C05 working products and SP-C02 admission closure; SP-05 for exports | Full affected serving, agent, CLI, intervention and evaluation migration |
| [SP-09](semantic-model-pivot/regeneration-and-acceptance.md#SP-09) | SP-05–SP-08 plus SP-C01–SP-C05 working integrations | Clean regeneration, retired old paths and operational cutover |
| [SP-10](semantic-model-pivot/regeneration-and-acceptance.md#SP-10) | SP-09 final functional source | Required native evidence union and integrated qualification |

The delivered foundations remain the working baseline. The current extension route is SP-C01 →
SP-C02 contract products → SP-C03/SP-C04/SP-C05 as their actual prerequisites become available.
SP-C02 admission closure then requires the relevant enforcing implementations. This is not a
whole-package dependency cycle: normalization/adapters can be usable before a new constraint is
activatable, and activation cannot claim an unenforced required invariant.

Current migrated callers adopt contracts within their SP-C package. SP-08 migrates the remaining
surface using those products, SP-09 performs regeneration/cutover and SP-10 owns assembled
qualification. Consumer design can begin from settled contracts; integrated claims require working
prerequisites. No automatic restart of the paused phase-0 run or production implementation follows
from this document revision.

## 6. Opportunity coverage and completion

The following rows refer to the **original semantic-PostgreSQL review**, not the completeness review.
Completeness-review disposition is solely in §10.

| Original-review opportunity | Scheduled realization and closure boundary |
|---|---|
| O01 | SP-01/SP-02 release admission; SP-04 and SP-08 demonstrate dynamic definitions actually reach consumers |
| O02 | SP-01 ontology/value-set scope; SP-06 extraction and SP-07 inference consume the same binding |
| O03 | SP-02/SP-03 native schema and race-safe publisher, including forbidden direct mutation |
| O04 | SP-01 supported semantics and SP-07 qualified domain/inference operations |
| O05 | SP-04/SP-06/SP-08 migrate all current affected entry points |
| O06 | SP-05 lossless interchange and actual SP-07/SP-08 consumer use |

Completion requires the declared current consumer union, regenerated statistics and a transfer fixture, evidence-backed answers, independent evaluation, refusal/error/concurrency cases and retirement of superseded production paths. A passing representative slice does not complete the enclosing migration. Detailed scenarios and command timing are owned by the acceptance plan.

The architecture minimizes per-domain DDL, per-item crossings and repeated preparation. It retains real costs: recursive values add joins, global constraints need sufficient scope, and high-degree closures may expand substantially. Prefer selective Core predicates and set operations before hydration; do not equate a small page with bounded execution. No speed/capacity claim, benchmark campaign, runtime cost model or new alignment lint follows from this series. Completeness additionally requires the implemented obligations in §10 and the expanded SP-09/SP-10 scenarios; prior passing profiles are not erased by these added requirements.

## 7. Scope exclusions and bounded uncertainties

No historical data migration, dual writes, old key scheme support, general OWL DL, arbitrary rule engine, graph service, public SPARQL endpoint, new provider, Rust rewrite or compatibility upcaster inventory. LinkML-Datalog remains a deferred candidate: revisit only for required rule behavior beyond the selected SQL profile with faithful qualification, numeric and provenance support.

SP-00 checks exact installed/potential pins together on Python 3.14.10 and verifies the chosen bounded generator/membership profile. Failure blocks dependent release activation work; resolve through a deliberate pin/mechanism change or explicitly rejected unsupported construct, never a silent validation gap. Package acceptance verifies the actual publisher and RDF mappings; documentation alone is not readiness evidence.

Current inspection establishes a proposed implementable route, not tested compatibility. New ontology dependencies are added exactly pinned during execution, using Context7 then primary/installed sources. Preserve failed/interrupted receipts. An unavailable required provider remains an open acceptance obligation; mocks supply local checks only.

## 8. Publication evidence

Plan-authoring evidence remains separate from subsequent execution. SP-00 adopts ADR-0024,
which supersedes ADR-0013/0019/0020–0023 while preserving their surviving clauses and staged
runtime selection. The exact ontology stack is installed; only existing setuptools moved
(84.2.1 → 81.0.0 for OAK's <82 requirement). Python support declarations now match 3.14;
interpreter 3.14.10 is unchanged. No database was deployed or legacy generated projection selected.
Existing plans keep their scope and finding ownership; a stale pgvector link was repaired only.

Execution evidence (2026-10-29): `just ready`, native library/plugin imports and selected existing
model/shape checks passed. Combined semantic/core/schema controls passed. Final semantic corrections are covered by
`uv run pytest python/corpus-structure/tests/semantic` on final source; unchanged core/schema
controls retain their applicability. Scoped Ruff/Pyrefly passed after test typing repairs. Documentation publication passed after adding the supplied proposal's
H1 and correcting two stale pgvector links. Failed intermediate checks remain in the execution
record; they do not establish final-source acceptance. Full-series qualification remains SP-10.


SP-01 completion is bounded to pure preparation and its explicit diagnostic/refusal profile.
Its receipt does not establish later database capability. Native standard
LinkML type imports, nested enum checks, source-relative imported IRIs, polymorphic boundaries,
constraint scopes and contradictory inheritance refusals have regression controls. Earlier
unsupported-import and projection-consistency failures were corrected rather than waived.

Final scoped commands: `uv run pytest python/corpus-structure/tests/semantic`,
`uv run pytest python/corpus-structure/tests/semantic python/corpus-structure/tests/core python/corpus-structure/tests/schema`,
`uv run ruff check python/corpus-structure/src/corpus_structure/semantic python/corpus-structure/tests/semantic`,
`uv run pyrefly check python/corpus-structure/src/corpus_structure/semantic python/corpus-structure/tests/semantic`,
`just docs-check`, `just ready`, and `uv run python scripts/check_pins.py` passed within their
stated scopes. `just turn-end` passed; incidental pre-pivot formatting was restored byte-for-byte.
`just test-all` and `just hygiene` were not run: assembled-series qualification remains SP-10.


Final receipts (2026-10-29, implementation source `7474f7a`): combined semantic/core/schema run
passed 777 tests before the final two inheritance refusal controls; final semantic suite passed
51 tests including those controls and native Valuesets import. The unchanged core/schema controls remain applicable, with the final semantic rerun establishing the changed scope. Ruff passed; Pyrefly reported 0 errors;
docs-check published 212 canonical pages. Upstream OAK/SSSOM deprecation warnings remain.
Owned implementation worktrees were removed after patch-equivalence and clean-state checks;
paused-task worktrees were preserved. That foundation receipt does not establish SP-02 or SP-10.

SP-02/SP-03 execution (2026-10-29) began from `c84f59c`. [ADR-0025](../adr/0025-semantic-publication.md)
and the [PostgreSQL package](semantic-model-pivot/postgresql-and-publication.md) own the concrete
contracts. Fresh uniquely owned databases on 5434 use a 28-table trusted LinkML projection, a separate
Alembic history through `semantic_0003`, and frozen routines/grants. Actual restricted logins verify
publication; no historical database or selected legacy model/generated metadata was changed.
Pglast 8.7 moved from development-only to the product dependency set; its version stayed fixed.
Explicit ontology dependency selection and compiler profile `2` prevent unrelated binary/SQL
artifacts from being parsed as ontologies and give changed compiler products a new identity.

Package acceptance includes native archive/activation, ownership/privilege and staging attacks,
identity/selection/recursive report fidelity, concurrency/retry/ambiguous and interrupted commit,
actual pinned-ontology activation/publication, authored SQL catalog binding, exact ADBC boundaries
and single-pool return/reset. Intermediate failures and their corrections remain in the package's
acceptance account. Final functional source is `0f70052`; the following results cover that source
after maintenance (2026-10-29). The later §B4/§B5 authority links and this receipt are documentation
changes only; no SP-10 or consumer-cutover claim follows from this package acceptance.

| Command | Outcome and scope |
|---|---|
| `uv run pytest python/corpus-structure/tests/semantic python/corpus-structure/tests/core python/corpus-structure/tests/schema --tb=short` | `passed`: 858 tests, including native restricted-role/frozen-migration controls and existing core/schema regressions |
| `uv run ruff check python/corpus-structure/src/corpus_structure/semantic python/corpus-structure/tests/semantic python/corpus-structure/semantic_alembic python/corpus-structure/src/corpus_structure/schema/relational.py` | `passed` |
| `uv run pyrefly check python/corpus-structure/src/corpus_structure/semantic python/corpus-structure/tests/semantic python/corpus-structure/semantic_alembic python/corpus-structure/src/corpus_structure/schema/relational.py` | `passed`: 0 errors; 14 upstream warnings remain |
| `just docs-check`, `just adr-lint`, `uv run python scripts/check_pins.py`, `just ready` | `passed`: 213 pages, decision links, exact pins and tools; initial docs failure for missing ADR-0025 §B links was corrected |
| `just turn-end` | `passed`; incidental formatting in 38 unchanged pre-pivot files restored byte-for-byte |
| `just test-all`, `just hygiene` | `not_run`: assembled-series qualification and unmigrated consumers remain SP-10; bounded package checks do not establish whole-repository health |

The SP-02/SP-03 operational bootstrap **passed**, using `uv run python` to invoke the same
`upgrade` → `persist_release` → `activate_release` → `load_release` API path. Database
`cs_semantic_20261029_0f70052` on 5434 initially used `semantic_0003`; project `semantic-pivot` has generation
1 and realization `semantic-foundation` is active at data revision 0, with no facts. The archived
core binding is `release:f070811a1127ce5860a3bdda89c571bd1ea87ff67a582ee7e66991fddffec736`.
Actual writer/reader authentication passed. The bootstrap leaves the old database and default
runtime URL unchanged. OAK/SSSOM deprecation and LinkML repeated-attribute diagnostics remain;
they did not prevent exact archive reconstruction or native activation. No source acquisition,
historical data copy or domain publication was performed.

All three implementation worktrees were removed after clean-tree and patch-equivalence checks;
their branches remain. No owned `cs_sem_test_*` databases remain. The paused phase-0 worktrees
are preserved. That receipt established the input for SP-04, not an old phase-0 completion header.


### SP-04/SP-05 acceptance and current operational binding (2026-10-29)

Execution began at `903a2ff`; final functional source is `aac9aa6`. The query and interchange
package owners describe the implemented boundary and later consumer obligations. ADR-0026
records one local DuckDB engine, release-bound analytical rounding, imported PostgreSQL snapshots
and protected Arrow publication. pgpq `0.12.0` is the only added product dependency; its exact pin
and narrow lockfile change passed readiness/pin checks. Runtime resource settings cannot alter
semantic arithmetic policy. DataFusion was considered and deferred.

The native journey covers exact archive/activation → restricted publication → semantic
query/explanation → imported ADBC snapshot → Arrow → DuckDB → pgpq → protected selection
publication. Independent expected rows/set results cover qualified meaning, numeric fidelity,
unknowns, repeated occurrences, equivalent qualification objects, aliases/fusion/views, exact replay,
stale analysis and resource cleanup. SP-04/SP-05 do not complete current serving/evaluation or
consolidation migration, recursive inference, selective consumer universes or runtime cutover.

| Command | Outcome and scope |
|---|---|
| `uv run pytest python/corpus-structure/tests/semantic python/corpus-structure/tests/core python/corpus-structure/tests/schema python/corpus-structure/tests/pool python/corpus-structure/tests/db/test_pool_write.py python/corpus-structure/tests/test_settings.py --tb=short` | `passed`: 917 tests on final functional source, including actual native PostgreSQL/ADBC/COPY and adjacent regressions; 2 upstream warnings |
| `CORPUS_ANALYTICS__ADBC_DRIVER_PATH=/home/paul/.config/adbc/drivers/postgresql_linux_amd64_v1.13.0/libadbc_driver_postgresql.so uv run pytest python/corpus-structure/tests/semantic/test_columnar_journey.py --tb=short` | `passed`: 1 native journey using the explicitly installed dbc driver; the preceding union uses the bundled default |
| `uv run ruff check python/corpus-structure/src/corpus_structure/semantic python/corpus-structure/tests/semantic python/corpus-structure/semantic_alembic python/corpus-structure/src/corpus_structure/pool/write.py python/corpus-structure/tests/db/test_pool_write.py python/corpus-structure/src/corpus_structure/settings.py` | `passed` |
| `uv run pyrefly check python/corpus-structure/src/corpus_structure/semantic python/corpus-structure/tests/semantic python/corpus-structure/semantic_alembic python/corpus-structure/src/corpus_structure/pool/write.py python/corpus-structure/tests/db/test_pool_write.py python/corpus-structure/src/corpus_structure/settings.py` | `passed`: 0 errors, 18 warnings |
| `just docs-check`, `just adr-lint`, `uv run python scripts/check_pins.py`, `just ready` | `passed`: 214 pages, decision links, exact pins and tools |
| `just turn-end` | `passed`; incidental formatting in unchanged pre-pivot files restored byte-for-byte; final functional source covered by the test union above |
| `just test-all`, `just hygiene` | `not_run`: assembled-series qualification remains SP-10; no whole-repository or performance claim |

Initial native/typing/formatting failures were corrected and affected checks rerun. A numeric-only
integer fixture violated existing physical lexical-value constraints; the fixture was corrected,
not the constraints. Canonical hexadecimal floats and disagreement grouping by qualification
meaning were corrected after independent review. Those earlier failures receive no acceptance
credit; upstream OAK/SSSOM diagnostics remain.

The dedicated database `cs_semantic_20261029_0f70052` on `18/corpus:5434` is now upgraded through
`semantic_0005`. The same `uv run python` API path (`upgrade`, `persist_release`, `activate_release`,
`load_release`) passed exact persistence/activation/offline reload. Project `semantic-pivot` is at
generation 2 with analytical release
`release:0343e3e201f05c3173a0080d710eba29753b7109b146c78bc8e3b94a6cfde3d6`.
Its new active realization `columnar-foundation` is empty at revision 0. Existing
`semantic-foundation` remains at revision 0 bound to its original release above. No domain data,
historical database or default runtime selection was changed. Driver manifest discovery alone is
not qualification: the explicit dbc path above was exercised, with no fallback.

Implementation worktrees were removed after clean-state and patch-equivalence checks; branches
remain. Those paused phase-0 worktrees were subsequently integrated and removed at closeout (§9). No owned `cs_sem_test_*` databases remain.
The current stop boundary and remaining SP-06/SP-07 qualification are in §9. Existing phase-0
findings retain their owner.

## 9. Prior SP-06/SP-07 closeout checkpoint (2026-10-29)

**Implemented; scoped Tested, not package completion. Work stopped at the operator's request.**
The [domain-operations owner](semantic-model-pivot/domain-operations.md#current-execution-contract-2026-10-29)
records delivered mechanisms, refusal boundaries and remaining qualification. ADR-0027 and D1,
D2, D5, D6 carry the architectural contract. Compiler 6 and migrations `semantic_0006`–`0021`
are source implementation; the existing operational bootstrap database remains on `0005` and
its original compiler-2 release. No deploy, default cutover, prior-result regrade or paused
phase-0 run restart occurred.

All three implementation branches were cherry-picked and reconciled on main, then ancestry
merged without reintroducing superseded intermediate code. Both retained phase-0 branches were
merged, resolving overlaps in favor of current semantic selection and the corrected scoped
parameter mappings. Their original evidence folders are preserved with their original scope.
All five worktrees were removed after clean-state checks; only the main checkout remains.
Branch references remain as recovery pointers. Workers have stopped.

The [measured execution-fit repair](../design_review/evidence/2026-10-29_sp06-execution-fit/README.md)
separates the old 98.381 s test-body bottleneck from the repaired 2.686 s result. Native graph
canonicalization, preview-only binding and bounded pure-preparation reuse preserve artifact
integrity and avoid repeated graph preparation. This is one local test, not assembled performance.

Type checking and targeted tests completed successfully. Their passing results remain valid;
subsequent lint maintenance does not invalidate them or require a repeat. Completed scoped
receipts include 76 method/math/validation controls and 86 preparation/proposal/archive/ontology
controls, alongside the merged-branch regression selection below. Lint cleanup remains separate.
The operator subsequently directed documentation-only closeout.

| Command | Actual outcome and boundary |
|---|---|
| `uv run --no-sync pytest python/corpus-structure/tests/db/test_queries.py::test_parameter_mapping_excludes_other_members_of_requested_construction python/corpus-structure/tests/orchestrate/test_slices.py python/corpus-structure/tests/orchestrate/test_complete.py --tb=short` | `passed`: 7 merged-branch regression controls |
| `uv run --no-sync pyrefly check --summary=none` | `passed`: 0 errors |
| `just ready` | `passed`: declared tools/environment |
| `just turn-end` | `passed`: ADR index and formatting command; does not imply a clean lint result |
| `uv run --no-sync ruff check --output-format=concise` | `failed`: last completed whole-project report had 45 findings; worker corrections overlapped that report, so it is not a final-tree count. Cleanup stopped; no subsequent whole-project lint receipt |

The working tree retains uncommitted formatting/lint corrections from the interrupted cleanup.
The passing type and test receipts above remain the verification record. The latest committed
integration is `80fe11b`; all worktree contributions are already integrated. Remaining lint
cleanup is open, not a reason to run another type/test campaign. The operator explicitly directs that lint-only
changes must not trigger follow-on type checking or testing. No owned check/test processes remain.

`just test-all` and `just hygiene`: **not_run** within this package closeout; SP-10 owns complete
assembled qualification. This pre-existing series boundary does not negate the passing type and
targeted-test results. SP-06/SP-07 package completion remains open
until their full required obligation union has been reconciled and qualified on the final source.
SP-08–SP-10 remain planned; existing finding dispositions remain with phase 0 §11. This is the
production closeout receipt. The subsequently authored completeness queue is in §10; it does not
restart production work or turn lint maintenance into a reason to rerun passing type/tests.

## 10. Domain-model completeness integration

**Implemented for transitioned supported scope; scoped Tested, 2026-10-29.** Source review/target
consumed at `dcc5e0b`. O01–O06 are closed at that boundary by actual enforcement/consumer
adoption and the receipts below; O07 retains the later SP-08–SP-10 integration obligation.
This section is their single scheduled-disposition owner. The supporting plans contain design,
packages and local evidence, not competing progress registers.

| Item | Responsible component/package | Consequence and intended change | Disposition · dependency | Closure boundary |
|---|---|---|---|---|
| [Completeness O01](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O01) | Logical model/compiler; SP-C01/SP-C02 | Connected concepts and typed relationship semantics, including scoped identity/authorization | Closed for transitioned supported scope · qualified graph/query, native custody and composed journey receipts below | Declared qualified/repeated/n-ary relationship reaches actual current enforcement and explanation through SP-C03–SP-C05 |
| [Completeness O02](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O02) | Lifecycle; SP-C01/SP-C03 | Composed state, valid combinations and full allowed transitions | Closed for transitioned supported scope · compiled edges, ownership/held/terminal and private-result native cases | Existing scheduling/submission/cut/cancel/publication writers enforce the same contracts |
| [Completeness O03](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O03) | Preparation/admission and native/domain guards; SP-C02/SP-C03/SP-C04 | Resolve owned operation/invariant implementations and refuse missing required enforcement | Prior supported-profile closure retained; native statement-binding adoption remains open in SP-08 (§12) | Required semantics faithfully execute; unsupported lowering cannot silently admit |
| [Completeness O04](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O04) | Source/domain outcomes; SP-C04 | Distinct typed outcomes, coverage translations and assessment subject/counterpart relations | Closed for transitioned supported scope · coverage/science, measurement custody and source/explanation cases | Refused content, unknown coverage and undecided science retain distinct meanings in actual consumers |
| [Completeness O05](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O05) | Projection/analytics; SP-C05 | Captured/candidate provenance, append/derived publication and resource contracts | Closed for transitioned supported scope · projection, derived fencing/replay and mixed lifetime cases | Current query/Arrow/DuckDB/COPY paths preserve scope, precision and mandatory derived-result fences |
| [Completeness O06](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O06) | Graph validation; SP-C02/SP-C05 | Rich relational constraints over qualified declared graph closure | Closed for declared qualified closure · missing/wrong-scope references, collection/null and shape cases | Required relation constraints execute without collapsing occurrences/qualification or replacing native transaction authority |
| [Completeness O07](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O07) | Composed binding and current consumers; SP-C01–SP-C05, then SP-08–SP-10 | Compatible admission/evolution and observable operation/binding/refusal references | Open · consumers migrated; native statement binding, fresh-frame completion and assembled acceptance remain (§12) | Complete model governs transitioned behavior; later consumers, regeneration and assembled acceptance use those same contracts |

### Current package queue

| Package | Current state | Next capability/readiness boundary |
|---|---|---|
| SP-C01 | Implemented; scoped Tested | Connected definitions govern supported transitioned consumers |
| SP-C02 | Implemented; supported admission closure scoped Tested | Exact compiler/native/SQL/physical binding; unsupported semantics refuse |
| SP-C03 | Implemented; scoped Tested | Native lifecycle, typed consumers and result atomicity connected |
| SP-C04 | Implemented; scoped Tested | Typed coverage/assessment/measurement custody and decision/inference consumers connected |
| SP-C05 | Implemented; scoped Tested | Qualified graph, captured/candidate input, derived publication and result lifetimes connected |

The next boundary is SP-08 adoption of the remaining consumer surface, followed by SP-09
regeneration/default cutover and SP-10 assembled qualification. SP-06/SP-07 retain their prior
implemented profiles and outstanding enclosing obligations; SP-00–SP-05 retain scoped passing
receipts. These closures do not claim arbitrary ontology/rule execution or whole-series acceptance.

### Investigation and coverage routing

The [contract plan §4](semantic-model-pivot/domain-model-completeness.md#SP-C02)
owns supported-rule lowering and compatibility design. The
[realization plan §5](semantic-model-pivot/domain-model-realization.md#library-dispositions)
owns graph/mapping/backend selection conditions and deferred triggers. These are package design
questions; their status follows the owning SP-C package here.

- Target §§1–3 definitions/authority/relationships → SP-C01/SP-C02, actual adoption SP-C03–SP-C05.
- Target §§4–5 state/transitions/outcomes/operations → SP-C01 definitions, SP-C03/SP-C04 realization.
- Target §6.1 preparation/constraint placement → SP-C02; actual native/graph routes SP-C03/SP-C05.
- Target §6.2 PostgreSQL effects → SP-C03, retaining native source/proof publication with SP-C04.
- Target §§6.3–6.4 graph/analytical semantics → SP-C05, with SP-C02 required invariant admission.
- Target §7 evolution/consumers/delivery → all SP-C packages, SP-08 adoption and SP-09/SP-10 union.
- Review §6 library mechanisms → selected existing stack in both new plans; direct PyOxigraph and
  linkml-map are conditional investigations; Oxrdflib/linkml-datalog are deferred with explicit triggers.
- Review §8 scenarios → package-local demonstrations plus the expanded SP-10 required union.

The original plan-integration revision was documentation-only. The implementation receipts below
record subsequent authorized product work. No new finding ledger, alignment gate or proof system
was introduced, and no phase-0 disposition is copied or closed.

### Prior SP-C01/SP-C02 receipts (2026-10-29; compiler-7 boundary)

Source includes compiler 7, explicit composed contracts, native conditional fragments, archive2
and semantic_0022 admission fence. No operational deployment or default cutover occurred.
Existing profile/receipt history remains intact; all completeness-review opportunity rows stay
open until their actual consumer/enforcement closure boundaries are met.

- Root targeted union: pytest test_contracts.py, test_composed.py, test_conditional_rules.py,
  test_prepare.py, test_rule_products.py, test_proposals.py, test_observations.py,
  test_execution_release.py, test_releases.py, test_release_publication.py and test_migrations.py
  under python/corpus-structure/tests/semantic, with --tb=short: 150 passed, one diagnostic-order
  expectation failed; the affected contract component is rerun after correction. Earlier initial
  collection/catalog failures are superseded and receive no passing credit.
- uv run --no-sync pyrefly check --summary=none: passed, zero errors at the integrated endpoint.
- Separate native archive/CAS scope before the final archive-fence case: 26 passed. The root
  union above includes the enabled-fence check and actual authenticated initializer refusal.
- Admission closure: blocked by missing future native lifecycle/conditional enforcement, as
  deliberately required. SP-C01/SP-C02 products do not claim SP-C03–SP-C05 implementation.

Final affected-component correction: uv run --no-sync pytest
python/corpus-structure/tests/semantic/test_contracts.py --tb=short: passed, 25 cases after the
reference-first diagnostic fix. Its scoped Pyrefly also passed. Together with the root union's
passing unaffected cases, this establishes the selected component/native scope; the failed
initial diagnostic expectation is not credited as a pass. Independent static review reported
no material correctness findings. Broader SP-C03–SP-C05 and SP-10 claims remain open.

Scoped Ruff passed after formatting and two lint-only edits (a variable rename and literal-line
split). Product typing/tests were not repeated after lint. just ready passed; the jsonschema
lock diff adds the direct dependency only. Documentation publication is recorded in STATUS.
Product checks remain distinct from formatting/index maintenance.

### SP-C03–SP-C05 and supported SP-C02 admission closure (2026-10-29)

**Implemented; scoped Tested, not SP-10 assembled qualification.** Compiler 8 / execution compiler 2
and immutable revisions `semantic_0023`–`0026` are integrated on main. The final execution binding
is `execution:ba807ea0f3d649f0e59a29033a03209d3e19ab2c5769882cd97b73a82103fc78`.
[Realization §7](semantic-model-pivot/domain-model-realization.md#7-implemented-mechanisms-2026-10-29)
owns mechanisms, library dispositions and supported-profile limits. cattrs 26.2.1 is a direct
product pin; attrs/msgspec were considered and deferred without adding parallel model authorities.

Native admission now verifies actual enforcing functions/triggers and restricted positive/negative
privileges. It fixes historical NOINHERIT grants previously masked by PUBLIC permissions, without
reopening PUBLIC. Existing SQL-admission artifact integrity and fatal diagnostic exceptions match
Python activation, inside its savepoint before CAS. Function/trigger checks are set-based; the
private descriptor is frozen source, not a new database ledger. Method/unit/configuration metadata
is immutable; legacy missing metadata remains unresolved rather than fabricated for semantic-2.

Current source/MCP/orchestration, consolidation, inference, explanation, graph and analytical
consumers use these contracts. Native measurement insertion is set-based and position-preserving;
late writer mutation refuses. Mixed borrowed/detached result lifetimes coexist within one scope,
and owned child connections close with the scope. A separate result-lifetime state on the scope
was removed because it misrepresented that existing behavior. No algorithms were regraded.

| Command / selected scope | Actual outcome and final-source applicability |
|---|---|
| `uv run --no-sync pytest python/corpus-structure/tests/semantic --tb=short` | Initial union **failed**: 81 failed, 356 passed (437 cases). Failures exposed restricted grant omissions, changed query/FK expectations and a source fixture without explicit metric inputs. Preserved as failed; not a passing full-suite run. |
| Same pytest command with the 79 repaired failed node IDs selected from that run | **78 passed, 1 failed**; the remaining CLI fixture omitted explicit source metric definitions. Earlier 26 failures / 172 passes in the smaller 198-case selection remain superseded failure history. |
| `uv run --no-sync pytest python/corpus-structure/tests/semantic/test_query.py::test_release_loaded_once_and_recursive_values_batched python/corpus-structure/tests/semantic/test_metadata.py --tb=short` | **passed**, 13 cases: missing two metadata selections plus affected scope/FK/query regression. Empty occurrence context reads now return before database access; the loaded source schema requires six bulk reads. |
| `uv run --no-sync pytest python/corpus-structure/tests/semantic/test_source_routing.py::test_actual_cli_source_scope_agent_unknown_limit_and_cancel --tb=short` | **passed**, final CLI fixture correction. The original 437-case selection is covered by passing unaffected and repaired selections; it was not rerun as one full suite. Raw overlapping receipt counts are not added together. |
| `uv run --no-sync pytest python/corpus-structure/tests/semantic/test_contracts.py python/corpus-structure/tests/semantic/test_analytics.py --tb=short` | **passed**, 51 cases after scope-model correction; an additional owned-child-cursor regression passed. |
| `uv run --no-sync pytest python/corpus-structure/tests/semantic/test_composed_journey.py python/corpus-structure/tests/semantic/test_execution_native.py -k 'composed_source or private_evaluation or method_version or writer_cannot' --tb=short` | **passed**, 4 cases under final model identity: real native source/MCP → cut → completed result → accepted query/explanation, private-result commit refusal, method contract and terminal writer denial. |
| `uv run --no-sync pytest python/corpus-structure/tests/semantic/test_composed_journey.py --tb=short` | **passed**, 2 journeys after the final SQL-admission/diagnostic helper change. |
| Scoped `test_execution_release.py` / `test_authored_sql.py` node selections | **passed**, actual restricted native activation, missing/corrupt SQL artifact refusal, diagnostic exception policy and existing activation/CAS rollback. Initial suffix-function error failed, was corrected, and the affected three-case selection passed. Prior native selection covered ABI/owner/trigger drift and missing positive privileges; affected final positive admission passed after each descriptor refresh. |
| Scoped `test_execution_native.py` held cancel/fail selections and measurement source/native selections | **passed**, four held-progress cases; exact metric bag/null/typed source values, actual source → cut → publication → finish → reader, malformed/direct/post-completion write denial. Independent positive inverse/symmetric/transitive/subtype native admission passed. |
| `uv run --no-sync pyrefly check --summary=none` | **passed**, zero whole-project errors after final integrated source, before maintenance/lint. Earlier errors were repaired; this is not a skipped check. |
| `just ready` | **passed**, declared tool/environment readiness after direct dependency change; not product qualification. |

Independent source review identified measurement custody and cancellation-cleanup defects; both
were repaired and their affected cases passed. Its ordinary held-cancel overwrite concern was
withdrawn after checking the existing 0020 guard; separate collision hardening remains tested.
The review did not establish external provider behavior or whole-series qualification.

Only owned fresh native test databases were migrated. Operational database
`cs_semantic_20261029_0f70052` at `18/corpus:5434` remains `semantic_0005`; no activation/default
cutover, prior-result regrade or paused phase-0 restart occurred. `just test-all` / `just hygiene`
are **not_run** for enclosing SP-10 qualification. Final `just turn-end`, `uv run --no-sync ruff check --output-format=concise` and `just docs-check`
passed (228 canonical pages, no publication/link errors). Initial Ruff found 32 style/line issues;
a formatter attempt failed on a temporary literal-wrap syntax error, corrected before the final
passing maintenance. No product typing/tests were repeated after lint-only maintenance; the
passing receipts above remain valid. All useful worker changes were integrated or superseded
on main and independently confirmed by their owners before removing the two clean worktrees.


## 11. SP-06/SP-07 remaining-scope completion (2026-10-29)

**Implemented; scoped Tested.** The operator authorized explicit evidence-backed identity exclusions,
not scored fuzzy matching or human grading. ADR-0029 and the
[domain-operations completion audit](semantic-model-pivot/domain-operations.md#completion-audit-2026-10-29)
carry the contract and assessment. SP-06 producer/settings and SP-07 occurrence/scientific/inference
obligations are implemented in the supported transitioned profile. New exclusions use LinkML-owned
source and execution definitions, source/evidence custody, deterministic identity partitioning,
protected bulk publication and actual snapshot/explanation/graph/Arrow consumers.

Compiler 9, semantic-domain-2, analytical-4 and frozen semantic_0027 are integrated. The trusted
execution model is execution:c6920439423e0c2826e701c095608408455c4a04559d2bad47fccc2657e54131.
Existing bindings are not silently upcast; baseline profiles cannot invoke the new capability.
No dependency versions moved. Existing native citation/locator and staging protections are retained.
Metadata scope tests follow the actual transitive FK chains instead of requiring redundant FKs.

| Command and scope | Actual outcome |
|---|---|
| `uv run --no-sync pytest python/corpus-structure/tests/semantic/test_contracts.py --tb=short` | Initial 2 failed/29 passed after catalog additions; corrected capability expectation and preserved existing relation order; affected component passed 31 cases. |
| `uv run --no-sync pytest python/corpus-structure/tests/semantic python/corpus-structure/tests/test_settings.py --tb=short` | Initial consolidated selection **failed**, 4 failed/484 passed. Failures: staging disposal with absent new tables, existing locator forgery regression, invalid inherited-input fixture, and overly specific direct-FK expectation. These failures receive no passing credit. |
| `uv run --no-sync pytest python/corpus-structure/tests/semantic/test_metadata.py python/corpus-structure/tests/semantic/test_identity_exclusions.py python/corpus-structure/tests/semantic/test_identity_exclusion_reads.py --tb=short` | **passed**, 16 cases after source-build/global-reference fixture correction and transitive-FK expectations. A preceding collection attempt during a cherry-pick conflict failed; conflicts were resolved before the passing run. |
| `uv run --no-sync pytest python/corpus-structure/tests/semantic/test_domain_operations.py::test_stage_disposal_refuses_writer_owned_imitation python/corpus-structure/tests/semantic/test_evaluation_boundaries.py::test_native_source_locator_is_checked_against_stored_citation python/corpus-structure/tests/semantic/test_identity_exclusions_native.py python/corpus-structure/tests/semantic/test_proposals.py python/corpus-structure/tests/semantic/test_identity_exclusions.py python/corpus-structure/tests/semantic/test_identity_exclusion_reads.py --tb=short` | **passed**, final 31 affected cases. Covers both native regressions, exact citation bags, omission/collapse/forgery and direct-write refusal, literal source identifiers, actual source/MCP, mandatory contradiction, inherited constraints, reader/explanation/RDF/Arrow/DuckDB and profile advertisement. |
| `uv run --no-sync pyrefly check --summary=none` | **passed**, zero whole-project errors before maintenance/lint. Earlier structural inference, optional-fixture and stray-variable errors were repaired. |

The original 488-case selection is covered by its passing unaffected cases and repaired affected
selections; no single final full-suite rerun is claimed and overlapping counts are not added.
Worker component receipts include 17 pure source/resolution controls and 51 graph/analytics controls.
Native intermediate owner/custody/grounding and fixture failures were corrected and rerun. Independent
crossing reviews identified locator correspondence and wildcard source-ID issues; both were repaired.
No further material gap remained in the inspected original SP-06/SP-07 and exclusion scope.

Only owned fresh native test databases were migrated. Operational cs_semantic_20261029_0f70052 on
18/corpus:5434 remains semantic_0005. No deployment/default cutover, prior-result regrade or phase-0
restart occurred. SP-08–SP-10 and completeness O07 follow-through remain open. Enclosing
`just test-all` / `just hygiene` are **not_run** here; SP-10 owns that assembled qualification.
Final `just turn-end`, read-only Ruff and `just docs-check` passed (229 canonical pages, zero
publication/link errors). Initial Ruff found 12 style/line issues; repaired without functional/type
repetition. An unresolved architectural reference in ADR-0028 was corrected by superseding it with
ADR-0029 under immutable-record policy; the semantic decision is unchanged. The retired record
remains recoverable in Git. All useful worker contributions are integrated; owned worktrees were
clean before removal. No push occurred. Lint-only effects do not invalidate passing receipts.


## 12. SP-08–SP-10 implementation checkpoint (2026-10-29)

**Implemented with scoped Tested evidence; package and series closure remain open.** Source
baseline `feeefad` includes the worker integrations and their recorded ancestry. All owned
worktrees have been integrated and removed. Concurrent library-leverage documentation remains
separately owned; its recommendations have not been adopted by this execution.

### Delivered behavior and mechanisms

- Current named/generic serving, statistics/toy queries, explanations, schema compilation,
  CLI/MCP defaults, intervention records and qualified JSONL/Parquet exports use semantic
  releases and completed result bindings. SQLAlchemy Core retains selective/batched access;
  rendition search has a native GIN prefilter. Dynamic qualification subtypes survive JSON.
- Independent references have LinkML definitions, protected `eval` storage, immutable authored
  passes/citation frames and `ReferenceEvaluation` grades. The evaluator principal is separate
  from the source writer. Existing matching, mathematical undecided outcomes, conflict groups,
  premise aliases and archived split/sampling policies are connected to these consumers.
  Grading is automated; no human grading or extraction-accuracy threshold was introduced.
- Compiler 10 and semantic_0028–0030 add the reference boundary, generation-CAS result selection
  and typed source-frame projections. Exact packet frames bind local statement handles to
  source locators through protected append-only routines. Original-packet backfill verifies the
  archived packet hash and preserves source observations. Known canonical non-MCP reports retain
  independently checked native source bindings.
- `ci regenerate` acquires explicit pack/dependency bytes, executes real source methods,
  invokes authenticated Claude through a fresh restricted stdio MCP server, and finalizes
  source-to-result work. Resumption uses the archived run and original task identities. Selected
  result and active interpretation are separate pointers. Credential purposes share one storage
  endpoint; extraction has no reference access. Replaced legacy runtime/write paths and their
  obsolete storage harnesses have been retired; useful pure algorithms/independent fixtures remain.
- All source/test/generator typing suppressions were removed structurally. Four exact dev pins
  add PyYAML, jsonschema, SciPy and html5lib stubs; lockfile additions are limited to that family.
  `just types` now includes domain plug-ins and exposes warning-level diagnostics.

### Actual deployment and verification

The [retained evidence](../design_review/evidence/2026-10-29_semantic-consumer-regeneration/README.md)
owns raw outputs, failures and the database checkpoint. `corpus_semantic` on 18/corpus:5434 is at
semantic_0030. Trusted execution is
`execution:6e6f27d22ad3d4ce187c22d52fefaebca5c58850011ec84886b11fada576d9b5`;
physical metadata is
`physical:a1d1377c7f65ba528b52f096ec737094228f2075802db0a70af9afec78bf1f2e`.
The earlier operational database and existing MCP process were not migrated or restarted.

| Scope / command | Actual outcome |
|---|---|
| `just types` (`--min-severity warn`, including domain plug-ins) | **passed**, zero errors/warnings before maintenance. Source/test/generator suppression scan is empty. Earlier type errors and missing-stub warnings were repaired; lint does not invalidate this result. |
| `just ready` after typing-library installation | **passed**. |
| Consumer/native/CLI selections | **passed** within their selections: serving/paging/explanation/search, both exports and cancellation; restricted references/actual golden and evaluation CLI; schema-derived reference roles, identity refusal, premise aliases, split/sampling policy and source strata. Worker receipts retain separate scopes; counts are not summed. |
| Generated models/source preparation selection | **passed**, 143 cases spanning core shapes/references, Stage B, conditional rules and actual statistics/toy preparation. Later native frame changes have separate receipts. |
| Source-frame controls | **passed**, scoped original-packet backfill, immutable observation/replay and native privilege/FK/function-body drift cases. The final admission selection contains five native and two pure cases. |
| `ci regenerate ... --project semantic-pivot --resume-run 1` | **passed**: real statistics extraction, consolidation/inference and selected `result:semantic-pivot:1`. Earlier local-anchor collision failure is retained; no re-extraction was required. |
| `ci regenerate ... --project semantic-pivot-transfer --resume-run 2` | **passed**: selected `result:semantic-pivot-transfer:2`, inspection query preserving two organization roles and `12.3400 kg`, and native ADBC-to-Parquet export. Earlier selection-privilege failure is retained. |
| Independent transfer reference evaluation | **passed as an execution check**; actual grade is zero matches. Reference label `P-17` and extracted label `vessel P-17` do not align under the current policy. The grade is retained unchanged; no accuracy improvement is claimed. |
| Fresh frame/MCP run 3 | **failed** during consolidation: valid `ToySourceStatement` is refused by a native literal `SourceStatement` membership check. Run 3 is sealed, `consolidating`, with no result or selected pointer. |
| First `just test-all` | **failed** at Python collection (six errors): inherited typed-extra schema was injected into closed subclasses. The hook was corrected; Rust compiled with zero test cases. |
| Revised `just test-all` | **incomplete / not passed**. The Python run emitted an early failure marker, then was interrupted without a completed assertion summary. No failing node or full result is established by this receipt. Its worker processes and owned `ci_test_708452` database were cleaned up. |
| Full `just hygiene` | **not_run**; full-series qualification remains open. Final closeout maintenance/publication results are recorded in STATUS. |
| `just turn-end`; `uv run ruff check --output-format=concise` | Maintenance **passed**; read-only Ruff **failed**, 64 remaining diagnostics. No typing/functional repetition followed lint. |
| `just docs-check` | **passed**, 268 canonical pages, zero publication/link errors. |
| `just evidence` | **failed**, five older-record errors (two unresolved dependencies and three missing hashes), 37 warnings. The new partial checkpoint record finalized successfully; older records were not repaired. |

### Remaining obligations

1. Couple native statement applicability to the admitted release's
   `AgentStatementBinding.statement` range and same-release class hierarchy. Python already
   consumes that binding; the native predicate still restates a base-class assumption. Explicit
   bindings must refuse incompatible base/unrelated classes, and malformed bindings must refuse.
   Adjacent applicability/range predicates have not received a completed assessment of this gap.
2. The initial ancestor-only 0031 draft is **unapplied and superseded in mechanism**. It is retained
   under evidence solely for review provenance. No active 0031 migration, updated fingerprint or
   native passing result exists. A class-name exception or blanket descendant allowance is not
   the accepted correction for an explicit binding.
3. Complete the fresh-frame run after a validated forward correction; preserve its original
   packet/task/cut identities and completed statistics/transfer results.
4. Diagnose the incomplete broad run, resolve the remaining lint diagnostics and complete the
   applicable final functional/provider and nonfunctional union. Existing scoped passes remain valid at their stated boundaries; they do
   not establish SP-10 or O07 closure. No quality benchmark or regrading campaign is scheduled here.
