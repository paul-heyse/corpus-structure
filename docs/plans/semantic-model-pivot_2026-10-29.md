# Semantic-model pivot — series coordinator

**Status:** Improvement integration planned in §14; production remains partial. Completion-audited at `ad4593f` (2026-10-29), including all partial/open scope.
The foundation and many scoped mechanisms are implemented; complete model governance and the
series are **not complete**. Current package states, findings, deviations and next work are in
§13. Earlier receipts retain their original scope and are not whole-series qualification.
**Created:** 2026-10-29 · **Revised:** 2026-10-29.
**Claim strength:** Source-inspected audit conclusions plus explicitly dated scoped Tested evidence;
no new product/native/provider qualification or broad performance/accuracy claim.

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

The additional SP-I01–SP-I09 route and current improvement priorities are in §14. Original IDs
and dependency meanings below remain; added working products supply their remaining closure.

Current package closure is determined by §13, including partial original and completeness scope.
Earlier SP-00–SP-05 receipts establish their stated profiles, not every current binding or consumer.
SP-02/SP-03 supply fixed physical
metadata, exact archived releases, generation-checked activation and protected native publication.
Their [package owner](semantic-model-pivot/postgresql-and-publication.md) states capability/refusal
boundaries. SP-04 supplies native semantic reads/explanations; SP-05 supplies the columnar
foundation and existing set kernels. SP-06/SP-07 retain scoped passing exclusion/source evidence (§11), but current model-binding
and operation-contract gaps keep their complete delivery open. §12 retains actual consumer and
regeneration receipts; §13 owns current obligations. No assembled-series qualification is claimed. Stable IDs
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

**Substantially implemented; closure reassessed by §13 (2026-10-29).** Source review/target
consumed at `dcc5e0b`. Earlier scoped enforcement/consumer receipts remain valid. Current
completeness opportunities remain open at their identified behavioral/admission/projection seams;
O07 additionally retains SP-08–SP-10 integration and qualification.
The opportunity rows here link to the single current gap/disposition owner in §13. The supporting plans contain design,
packages and local evidence, not competing progress registers.

| Item | Responsible component/package | Consequence and intended change | Disposition · dependency | Closure boundary |
|---|---|---|---|---|
| [Completeness O01](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O01) | Logical model/compiler; SP-C01/SP-C02 | Connected concepts and typed relationship semantics, including scoped identity/authorization | Partial · CA-01 explicit statement binding and CA-05 graph contract attribution; earlier generic relationship receipts retained | Declared qualified/repeated/n-ary relationship reaches actual current enforcement and explanation through SP-C03–SP-C05 |
| [Completeness O02](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O02) | Lifecycle; SP-C01/SP-C03 | Composed state, valid combinations and full allowed transitions | Current 38 ordinary edge tuples match · CA-04 actual operation correspondence and CA-06 maintained model-centered correspondence remain open | Existing scheduling/submission/cut/cancel/publication writers enforce the same contracts |
| [Completeness O03](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O03) | Preparation/admission and native/domain guards; SP-C02/SP-C03/SP-C04 | Resolve owned operation/invariant implementations and refuse missing required enforcement | Partial · CA-01 admission/native/source adoption, CA-02 conditional scope, CA-04 result/enforcer contracts and CA-06 correspondence; not solely SP-08 | Required semantics faithfully execute; unsupported lowering cannot silently admit |
| [Completeness O04](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O04) | Source/domain outcomes; SP-C04 | Distinct typed outcomes, coverage translations and assessment subject/counterpart relations | Partial · CA-04 actual source/hold/scientific alternatives; coverage conversion and measurement receipts retained | Refused content, unknown coverage and undecided science retain distinct meanings in actual consumers |
| [Completeness O05](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O05) | Projection/analytics; SP-C05 | Captured/candidate provenance, append/derived publication and resource contracts | Analytical mechanisms implemented · CA-03 named read-universe and CA-06 correspondence remain open | Current query/Arrow/DuckDB/COPY paths preserve scope, precision and mandatory derived-result fences |
| [Completeness O06](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O06) | Graph validation; SP-C02/SP-C05 | Rich relational constraints over qualified declared graph closure | Qualified closure controls retained · CA-05 graph-contract resolution and CA-06 correspondence remain open | Required relation constraints execute without collapsing occurrences/qualification or replacing native transaction authority |
| [Completeness O07](../functional_reviews/semantic-domain-model-completeness_2026-10-29.md#O07) | Composed binding and current consumers; SP-C01–SP-C05, then SP-08–SP-10 | Compatible admission/evolution and observable operation/binding/refusal references | Open · CA-01–CA-06 govern current behavioral closure; CA-07–CA-11 retain retirement, authority, scope and qualification obligations (§13) | Complete model governs transitioned behavior; later consumers, regeneration and assembled acceptance use those same contracts |

### Current package queue

| Package | Current state | Next capability/readiness boundary |
|---|---|---|
| SP-C01 | Definitions implemented; behavioral closure partial | CA-01/CA-04/CA-06; declarations do not establish complete adoption |
| SP-C02 | Contract products implemented; admission/lowering closure partial | CA-01/CA-02/CA-04/CA-06 |
| SP-C03 | Substantial native lifecycle implementation; partial | CA-01/CA-04/CA-06; no current ordinary-edge drift found |
| SP-C04 | Substantial domain implementation; partial | CA-01/CA-02/CA-04; scientific/measurement/proof receipts retained |
| SP-C05 | Analytical/qualified-closure mechanisms implemented; graph closure partial | CA-05/CA-06; named consumer gap CA-03 |

The next boundary is the §13 model/admission/operation/projection corrections across already
transitioned packages and SP-08, followed by SP-09 completion and SP-10 qualification. SP-06/SP-07 retain their prior
implemented profiles and outstanding enclosing obligations; SP-00–SP-05 retain scoped passing
receipts. Earlier scoped conclusions do not claim arbitrary ontology/rule execution or whole-series acceptance.

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

**Prior scoped receipt.** §13 owns the current completion judgment; all passing commands below retain their original scope.

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

**Historical implementation checkpoint with scoped Tested evidence; §13 owns current package
and series closure.** Source
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


## 13. Completion audit (2026-10-29)

### Boundary and conclusion

**Source-inspected at `ad4593f4f4e2e0c7bf8cdfbb63de82361ccf1fcd`; complete series delivery is
partial, not qualified.** This assessment covers all eight supporting plans, SP-00–SP-10 and
SP-C01–SP-C05, narrative obligations, selected original-review O01–O06 and completeness-review
O01–O07, decisions, investigations, migration/retirement and acceptance. Supporting plans contain
the item-level determinations; this section is the sole current gap/disposition owner.

The target is **100% model governance with zero disconnected behavior** in the declared domain.
Schemas and relationships alone are insufficient: material applicability, states/transitions,
inputs/results/outcomes, invariants, effects and dependencies must be connected to their
actual implementations and consumers. Handwritten scientific or native algorithms are not
inherently exceptions; their relevant semantics must still be model-governed. No exception has
been accepted to close a gap. The operator clarified model-centered proactive identification and
resolution during this audit; CA-06 carries that completion work. The later choice of CLI,
generator or script is not decided or implemented here.

Three fresh read-only implementation reviewers independently examined model/persistence,
operations/lifecycle and projections/consumers, including all 49 current catalog operations.
Root inspected regeneration, actual defaults, retirement, architecture, evidence and cross-package
obligations. Reviewers checked actual callers and the selected pre-pivot baseline where needed;
implementation summaries, counts and prior closure labels were not treated as proof. The audit changed documentation only; it ran no product/native/provider tests, migrations or
services and changed no operational state.
An unrelated concurrent design-principle-audit evidence folder remains outside this work.

Implementation is substantial: exact archives/CAS, fixed model-derived storage, protected bulk
publication, source custody, qualified values/proofs, snapshot/columnar ownership, reference
isolation and many current routes are real mechanisms. **Specific remaining model connections
are missing or inconsistent**, and SP-09 retirement/authority work plus SP-10 qualification are
unfinished. Existing scoped passing results remain credited; this audit does not promote them
to final-source whole-series acceptance.

### All-package disposition

| Package | Current implementation conclusion | Qualification / remaining owner |
|---|---|---|
| SP-00 | Decisions, pins and bounded supported/refused profile implemented; original profile promise unresolved | CA-08 authority reconciliation; CA-11 initial pattern/placement promise |
| SP-01 | Core/ontology/identity preparation implemented; current conditional/binding preparation partial | CA-01/CA-02; original pure-profile receipts retained |
| SP-02 | Exact archive/reload/bootstrap/CAS implemented; semantic activation closure partial | CA-01/CA-06; native foundation receipts retained |
| SP-03 | Generic protected COPY/retry/receipt mechanism implemented; complete source publication partial | CA-01/CA-02/CA-06; not a new broad native pass |
| SP-04 | Native release-bound query/explanation primitives implemented | Scoped query receipts retained; later named-query defect belongs to SP-08 |
| SP-05 | Selected Arrow/ADBC/DuckDB/pgpq mechanisms implemented | Exact/bounded profile and lifetime receipts retained; no capacity claim |
| SP-06 | Producer/settings mechanisms substantial; full binding adoption partial | CA-01/CA-04; CA-09 settings acceptance accounting |
| SP-07 | Identity/science/qualified-inference mechanisms substantial; current source-to-result delivery partial | CA-01/CA-02/CA-04; existing exclusions/proofs retain credit |
| SP-C01 | Connected definitions implemented; effective operation-contract closure partial | CA-01/CA-04/CA-06; catalog counts are inventory |
| SP-C02 | Contract products implemented; faithful admission/lowering closure partial | CA-01/CA-02/CA-04/CA-06 |
| SP-C03 | Native finite state/atomic effects substantial; current governed journey partial | CA-01/CA-04/CA-06; current 38 ordinary edges match |
| SP-C04 | Typed decisions/measurements/domain mechanisms substantial; result and source contracts partial | CA-01/CA-02/CA-04 |
| SP-C05 | Analytical/provenance/lifetime and qualified closure mechanisms implemented; graph binding partial | CA-05/CA-06; current named read seam CA-03 |
| SP-08 | Existing consumer migration substantial; complete current behavior partial | CA-01/CA-03/CA-04; scoped reference/CLI/export receipts retained |
| SP-09 | Two actual selected workflows and resumption delivered; functional closure partial | CA-01 plus CA-07 retirement and CA-08 authorities |
| SP-10 | Incomplete required union and broad qualification | CA-09/CA-10 and affected native/provider closure after substantive fixes |

The two source reviews keep distinct opportunity identities. Original O01 dynamic operation
adoption remains open under CA-01/CA-04; O02 ontology mechanisms have scoped evidence; O03 generic
native storage/publication has scoped evidence but current complete applicability is partial;
O04 domain behavior is affected by CA-01/CA-02/CA-04; O05 consumers by CA-03/CA-04; O06 columnar
mechanisms have scoped evidence with CA-05/CA-06 at related contract boundaries. None of those
rows independently closes the enclosing series. Completeness O01–O07 current disposition is in §10.

### Findings and remaining obligations

CA identifiers below are stable and local to this series. Each row names its primary owner;
affected packages link here instead of duplicating mutable findings.

| ID / kind | Missing obligation and source evidence | Owner and actionable closure |
|---|---|---|
| **CA-01 · implementation** | Explicit statement bindings are not resolved completely by public preparation/admission; runtime `semantic/statement_types.py:8–21` is too late. `semantic_0030_source_frames.sql:171–178` and earlier occurrence-context revisions retain literal `SourceStatement`; `semantic/source_projection.py:82–87` independently rejects a valid narrowed relation range. | **SP-C02/SP-C03**, affected SP-01/02/03/06/07/C04/08/09. Resolve the admitted binding once, validate its required class/shape/kind contract and consume the same range/hierarchy at every source/native boundary. Forward migration/admission changes and independent subtype/base/unrelated/malformed/cross-release cases must reach activation rollback and actual continuation of run 3. No class-name exception or ancestor-only patch closes this. |
| **CA-02 · implementation** | `semantic/prepare.py:811–813` installs conditional validation on every object; `conditional_rules.py:232–249` has no validation-purpose/scope distinction. When `PreparationProfile.constraint_scope="accepted_value"`, the archived/native rule is accepted-value scoped (`prepare.py:849`, `semantic_0023_execution.sql:78–107`). Thus an unselected source report can be refused as though already accepted. | **SP-C02**, affected SP-01/C03/C04/07. Preserve structural ingress validation and enforce accepted-only conditions at their declared projection boundary. Independent submitted/unselected/selected cases must cross preparation, archive/reload and native publication; invalid selected state must still fail atomically. |
| **CA-03 · implementation** | `serve/journey.py:84–92,227–240` treats all present complete family records as complete coverage of the requested run/multi-member scope. Missing members are absent from the check, so empty named query can incorrectly report `absent`; primitive QuerySpec uses an explicit coverage-scope witness. | **SP-08**, affected SP-C05/O05. Require the applicable global witness or demonstrate complete coverage of every required member through the shared modeled coverage meaning. Independent complete-A/missing-B and partial multi-unit/document cases must remain unknown. |
| **CA-04 · implementation/model correspondence** | Catalog result/enforcer declarations do not match several actual bound implementations. `execute_source` declares task protocol products/outcomes, but `run_source_methods` returns source readiness; `hold_submission` declares held/refused_context but helper returns held/proceed; `scientific_policy` omits emitted warning/refuted; check_submission/packet_reads binds only `locate_proposal`, while session/read/attempt checks are owned by the composed caller/native commit. `contracts.py:498–579` compares names and authored tuples, not these actual correspondences. | **SP-C01/SP-C02/SP-C03/SP-C04**, affected SP-06/07/08. Reconcile each actual semantic operation/phase with its typed result and enforcing composition. Preserve distinct outcome dimensions; do not blindly union unrelated alternatives or relabel readiness as completion. Account for raw source-read return/error translations. Independently exercise all finite alternatives and verify missing enforcing links refuse preparation/admission. |
| **CA-05 · implementation/model attribution** | `semantic/ontology.py:416–443` requires a nonempty caller-supplied projection ID, but graph_project/graph_validate do not resolve it against the bound graph ProjectionContract. Current known caller supplies the expected ID and closure, so no invalid current graph output is alleged; the contract attribution itself is unchecked. | **SP-C05**, affected SP-C02/08/O06. Resolve the declared graph contract from the bound model, check source universe/kinds/precision/omission/lifetime and refuse unknown/incompatible attribution while retaining qualified closure and independent expected graphs. |
| **CA-06 · clarified completion requirement** | Existing unresolved-reference/capability/archive/native-body/privilege checks are useful, but matching callable names/fingerprints alone does not demonstrate model-to-behavior correspondence. The 38 ordinary model/native edge tuples match now, yet no retained generator or maintained complete correspondence route was found. CA-01/CA-03/CA-04 show concrete drift can remain accepted. | **SP-C02 with SP-C03/SP-C04/SP-C05 and SP-08 owners.** Complete the model-centered derivation/correspondence route for material behavior, including finite transitions, actual result domains/enforcement composition and projection attribution. Diagnostics must identify the model contract, implementation/consumer boundary and actionable repair. Choose CLI/codegen/script details later; never rewrite deployed migration history or treat diagnostics as a substitute for coupling. No disconnected exception is adopted. |
| **CA-07 · retirement** | Current entry points route semantically, but public dormant legacy DB code remains: `orchestrate/runs.py:216–228` retains old meta.project/key-scheme run construction; old context/routing readers and core/db exported legacy metadata/overlay remain. Searches found no current caller of the old run constructor/routing path. | **SP-09.** Finish the explicit superseded-production-route/projection retirement obligation, extracting genuinely retained helpers such as code_commit/RunError. Do not call this a demonstrated live current bypass or delete useful pure/source algorithms. Verify current entrypoint/library inventory no longer offers retired admitted writers/readers. |
| **CA-08 · authority/documentation** | Current defaults and ADR-0030's fresh automatic extractor coexist with §B3/accepted ADR-0015's “pipeline never calls the agent”; detailed D3/D6/D7/D8 pages still describe earlier selected routes as current/future. B5 alone does not reconcile those owners. | **SP-00/SP-09.** Reconcile the accepted new regeneration behavior with B3 and enduring owners through the required successor ADR/decision route; accepted ADRs remain immutable. Update current contracts and remove contradictory current claims, preserving unrelated unfinished legacy targets. No runtime failure is inferred solely from stale prose. |
| **CA-09 · qualification accounting** | SP-06 explicitly names mid-run environment-change and cross-field-error controls. Inspected settings/registry tests cover precedence, nested/bad keys, frozen settings, masking and environment-independent registry, but no bound-run mid-execution environment case was located; no actual applicable cross-field invariant was identified. | **SP-06/SP-10.** Locate or supply meaningful bound-run evidence; explicitly settle cross-field applicability rather than inventing a rule/test or claiming an absent receipt passed. Immutable implementation is present; this is not an established runtime defect. |
| **CA-10 · qualification/evidence** | No passing complete final functional/native/provider/nonfunctional union: initial test-all collection failed, repaired broad run remained incomplete with an unresolved failure marker, full hygiene is not_run and last Ruff had 64 diagnostics. Global evidence had five older-record errors; the local execution-fit record lacks finalized hashes. | **SP-10**, with existing evidence owners for older records. After substantive fixes, complete affected native/provider obligations and the applicable final union/broad routes. Retain failed/interrupted outputs and earlier scoped/type passes; do not repeat them because lint ran. Settle required evidence dependencies without expanding to unrelated old-plan repairs. Local timing remains a reported scoped measurement, not audited capacity/speed benefit. |
| **CA-11 · scope reconciliation** | SP-00 initially promises patterns and declared occurrence/context scopes; the PostgreSQL package/admission explicitly refuses native patterns and occurrence/context grouping. ADR-0025 calls these limitations rather than capability completion; no current required workflow using those placements was found. | **SP-00/SP-C02.** Explicitly reconcile the initial promise with the admitted language and required workflows. Faithfully implement any required construct or settle the supported-profile decision through its owner. Safe refusal is valid behavior but is not delivery of the refused capability; neither arbitrary OWL support nor a generic regex/grouping engine is silently added. |

Source paths in the finding table are relative to `python/corpus-structure/src/corpus_structure`
for Python modules and `python/corpus-structure/semantic_alembic/versions` for frozen SQL.

### Deviations judged against the target

- **Justified:** finite owned native kernels/ordinary scientific functions instead of a universal
  workflow/rule interpreter; iterative Core fixed-point inference instead of one recursive CTE;
  local pinned OAK file materialization; separate SQL-byte identity/catalog-admission products;
  unsupported historical compiler refusal; cattrs frozen-product conversion. The inspected
  mechanisms preserve their accepted behavior and authority without additional services.
- **Justified bounded choices:** full realization capture rather than premature selective Arrow
  loading preserves the declared universe and makes no selective-load performance claim;
  RDFLib/owned projections and retained pure matching/science algorithms have real consumers.
  Candidate DataFusion/linkml-map/direct stores/attrs/msgspec/Datalog installations are not
  obligations merely because researched.
- **Not gaps:** unimplemented future MCP inspection/golden profiles were not existing capabilities
  at `5ba9a5c`; current implemented tools and CLI/API routes were migrated. A zero transfer grade
  is an actual evaluation outcome, not failure of a nonexistent accuracy threshold or a request
  to regrade. Old external DB/MCP preservation is explicitly authorized, not an implicit disposal
  requirement.
- **Not acceptable substitutions:** an ordinary implementation with a catalog label but mismatched
  results/predicates; profile labels hiding a valid admitted subtype; copied projection metadata;
  unsupported/refused capability counted as implemented; earlier scoped passes relabeled as
  assembled qualification. CA-01–CA-06 remain open under the zero-disconnected-behavior target.

### Evidence, benefits and next execution boundary

The eight supporting audit sections contain every reconstructed item and the required acceptance
families; all 49 current operation IDs are represented there. Source inspection establishes the
identified missing connections without a product test run. A read-only comparison found exact
correspondence of all 38 ordinary lifecycle source-artifact tuples; two reference edges use their
separate protected routines. This is current artifact correspondence, not native qualification
or a maintained future drift mechanism.

Root's read-only PostgreSQL inspection (`uv run --no-sync python`, default_transaction_read_only=on)
confirmed semantic_0030 in `public.semantic_alembic_version`, projects' active/selected pointers,
finished sealed runs 1/2 and sealed/consolidating run 3 without a result. The existing retained
[consumer/regeneration evidence](../design_review/evidence/2026-10-29_semantic-consumer-regeneration/README.md)
remains the workflow/command record. No new provider, regrade, migration, database disposal or
product/type/lint campaign was performed. Root documentation maintenance/publication is recorded
in STATUS; those checks establish document integrity only.

No system throughput/capacity/accuracy improvement is established. Elimination of per-class DDL,
shared preparation, native bulk ownership and coherent typed projections are implemented design
properties at their stated boundaries. The reported local 98.381 s→2.686 s preparation experiment
retains its original scope and unfinished record-hash limitation; it is not a new measured claim.

Next authorized production scope should first reconcile actual model/operation/projection meaning
(CA-01–CA-06), preserving existing invariant and error distinctions. Complete retirement/authority
and profile/settings accounting (CA-07/08/09/11), then finish the affected fresh native journey and
required final qualification (CA-10). This audit does not authorize those repairs. No earlier
phase-0 finding is transferred or closed. The coordinator's current conclusion is **partial
implementation, incomplete qualification, bounded benefits; no disconnected exceptions accepted**.


## 14. Improvement integration (2026-10-29)

**Planned; no implementation progress claimed.** Consume
[improvement review I01–I11](../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md)
at `1f66fd4`, reconciled with authoring baseline `8578710` (product `ad4593f`). The newly committed
broader diagnostic account is separately owned; this integration does not silently adopt its
additional findings or refresh it. Review CBO premises corrected by that review remain corrected.

Target 100% domain-model governance with zero disconnected behavior. Preserve authored semantic
scope, independent occurrence/fact identity, exact values, qualified evidence/uncertainty, protected
PostgreSQL transactions, immutable completed output, automatic grading and scoped evidence.
Ordinary code remains appropriate when it effectively realizes its model contract; no callback,
fingerprint, diagnostic or unsupported-profile label substitutes for missing behavioral connection.

### Accepted planning decisions and rule routes

The operator explicitly selected all three recommended options on 2026-10-29. These are target
choices accepted for planning; execution must establish the successor authority before depending
on them. Accepted ADRs are immutable. No production deployment follows from this document update.

| Decision | Accepted consequence | Required route / dependent work |
|---|---|---|
| PR-01 release opening/verification and determinants | Open supported runtime products from immutable archives; verify fully at persist/replay, activation, run start and explicit request; distinguish byte identity from runtime validator/deployment compatibility | Successor to ADR-0025 reload policy and relevant ADR-0024/D1/D2/D3/D8 clauses before SP-I04 dispatch/cutover. Complete recipes and required old answers must remain usable. |
| PR-02 restricted release admission | Dedicated non-owner admission login and controlled complete archive/finalization/activation operations; migration credentials outside ordinary regeneration | ADR-0025/0030 and D3/D9 authority reconciliation before SP-I03 admission. No broad sem DML, publisher membership or reference privilege; deployment-specific admission remains separately modeled. |
| PR-03 native fixture equivalence | Fresh per-test clones of session-migrated template with ACL/settings replay and independent posture checks; cold bootstrap/revision tests retained | Amend owning PostgreSQL/acceptance interpretation and test-support contract before SP-I08 fixture adoption. This does not replace required native commits/principals/races. |

Preserve current per-consumer scientific evidence→decision mappings during extraction; a later
numeric policy change is not accepted here. Preserve lossless representation/identity while
specifying lexical meaning; intentional lexical/identity normalization needs its own decision.
Retain no-generic-writer-TEMP through protected fixed inference workspace. If a necessary broader
privilege/rule change emerges, obtain the explicit decision before dependent work. B3's automated
extractor conflict is scheduled successor-decision work, not silently repaired prose.

### Added document ownership and package route

Three new documents own added integrated work; the original eight retain their contract meanings,
original package IDs and dated evidence. There is one coordinator queue/disposition owner.
Original packages do not become complete merely because additional remediation is planned.

| Package | Owning document / responsibility | Working input and readiness / closure contribution |
|---|---|---|
| SP-I01 | [Model execution](semantic-model-pivot/model-execution-closure.md#SP-I01): effective bindings, scoped constraints, real phases/results/enforcement and graph contracts | Existing SP-C products; normalization usable early, admission waits for actual native consumers. Supplies CA-01/02/04/05/06/11 corrections. |
| SP-I02 | [Model execution](semantic-model-pivot/model-execution-closure.md#SP-I02): retained native authoring, correspondence and forward physical reconciliation | SP-I01 finite products + physical MetaData. DDL/views/transport/edges/descriptors have one derivation route, deployed in new frozen revisions. |
| SP-I03 | [Model execution](semantic-model-pivot/model-execution-closure.md#SP-I03): immutable meaning, restricted admission, purposes/workspace and native codec | PR-02 and SP-I01/02 products. Must enforce meaning closure and cumulative checks before their consumers remove redundant work. |
| SP-I04 | [Release/consumers](semantic-model-pivot/release-and-consumer-consolidation.md#SP-I04): acquisition/composition/open/verify/index/transition | PR-01, complete SP-I01 recipe; SP-I03 protection before dropping coherence checks. Required compiler-10 access works before new cutover. |
| SP-I05 | [Release/consumers](semantic-model-pivot/release-and-consumer-consolidation.md#SP-I05): public reads, required-universe coverage, visitor and refusals | SP-I01 descriptors; SP-I04 index when ready. Independent predicate/finite-float/coverage fixes need not await full archive transition. |
| SP-I06 | [Release/consumers](semantic-model-pivot/release-and-consumer-consolidation.md#SP-I06): scientific evidence and semantic rule views | SP-I01 result contracts and exact codec; preserve explicit current policies. Working migrated consumers precede legacy math/value retirement. |
| SP-I07 | [Release/consumers](semantic-model-pivot/release-and-consumer-consolidation.md#SP-I07): analytical bindings, used-input/evidence closure and retirement | Working references/projections and full identity candidate universe; post-resolution carrying preserves required closure. Optional optimizations stay triggered. |
| SP-I08 | [Qualification](semantic-model-pivot/qualification-infrastructure.md#SP-I08): session native preparation and posture | PR-03 and actual role/workspace contract from SP-I03; cold fixture/consumer contract preparation can proceed earlier. |
| SP-I09 | [Qualification](semantic-model-pivot/qualification-infrastructure.md#SP-I09): streamed outcome/watchdog/required-union accounting | Existing test route, independent of product corrections. Supplies actionable final qualification, not a substitute for real native/provider tests. |

All nine packages are **planned**. Semantic definitions, generated declarations and manifests retain
one writer per integrated slice; logical readiness does not imply safe parallel edits. One root
author/integrator reconciles shared changes. Focused source/library/design advice is used only
for actual open contracts, not a fixed recurring role sequence or another broad audit.

### Recommendation and opportunity selection

Review recommendations are selected for planning with the conditions below. Retain judgments
carry their concrete adjustments; optional candidates remain explicitly deferred, not missing
mandatory installation. CA current disposition remains §13; these references supply execution
ownership/closure work without copying the audit into a new ledger.

| Improvement | Additional packages / original obligations | Selection and closure meaning |
|---|---|---|
| [I01](../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md#I01) | SP-I01/02/03; SP-01/C01–C05/06–08; CA-01/02/04/05/06/11 | Required effective model consumption and actual enforcing boundary; no schema-only closure. |
| [I02](../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md#I02) | SP-I02; SP-02/03/C03/09/10; CA-01/06/07 | Retained emitter, forward reconciliation and independent transition/effect expectations. |
| [I03](../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md#I03) | SP-I03/07; SP-03/07; CA-06 | Meaning-closure immutability prerequisite; remove only discharged meaning checks, preserve cumulative checks and required input closure. |
| [I04](../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md#I04) | SP-I04; SP-01/C02/08/09; CA-06/08 | PR-01 selected; exact recipe/runtime compatibility, controlled determinant transition and working old-answer access. |
| [I05](../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md#I05) | SP-I05; SP-04/C05/08; CA-03/04 | One public interpretation/snapshot route, exact predicates and required-universe coverage; no future MCP tool expansion. |
| [I06](../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md#I06) | SP-I06; SP-C04/07/08; CA-04/07 | Shared evidence kernel and semantic rule view; current consumer policies preserved, changes separately decided. |
| [I07](../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md#I07) | SP-I01/03/05; SP-C02/C04/08; CA-01/02/04 | One reference-position/value meaning, finite fields, independent codec/native vectors and archived-reference interpretation. |
| [I08](../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md#I08) | SP-I07; SP-05/C05/07/08; CA-07 | Native relation binding/ownership selected. Delta inference, streaming, additional exports/backends remain conditional. |
| [I09](../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md#I09) | SP-I03/05; SP-03/08/09; CA-08 | PR-02 restricted admission, actual principal checks, explicit purpose/shared target. Sequential pools retained. |
| [I10](../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md#I10) | SP-I08; SP-10; CA-09/10 | PR-03 clone equivalence and actual privilege/cleanup posture; cold migration/upgrade controls retained. |
| [I11](../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md#I11) | SP-I09; SP-10; CA-09/10 | Report stream/watchdog and honest required-scope classification. Required skip cannot pass; optional inapplicability is distinct. |

| CBO | Planned disposition / work owner |
|---|---|
| CBO-001 | SP-I05 public selection/hydration, exact object predicates, coverage and bounded explanation. |
| CBO-002 | SP-I04 explicit acquisition/pure composition; preserve already normalized input order. |
| CBO-003 | SP-I04 open/verify under PR-01, complete recipe and old-answer prerequisite. |
| CBO-004 | SP-I03 restricted purpose/principals; retain sequential pools. Withdrawn first-persist SET ROLE hazard stays withdrawn. |
| CBO-005 | SP-I06 semantic rule view/accessor migration and deliberate view-version transition. |
| CBO-006 | SP-I06 shared scientific evidence; preserve explicit per-consumer policies. |
| CBO-007 | Retain physical PyArrow export/shared opener, SP-I05/07; new export demands remain triggered. |
| CBO-008 | SP-I02 Core-derived forward reconciliation and bounded Alembic/native checks; lowering relocation follows real retirement need. |
| CBO-009 | SP-I04 determinant ownership, runtime validation compatibility and SymPy dependencies; exact dependency moves only on actual use. |
| CBO-010 | SP-I08 session template/ACL/settings replay, bare/revision fixtures and cleanup owner. |
| CBO-011 | SP-I09 streamed worker/node/phase outcomes and watchdog; no collection-order or all-skips=blocked inference. |
| CBO-012 | SP-I05 domain refusal/DBAPI outcome adapters after actual phase/enforcer contracts. |
| CBO-013 | SP-I01/04/05 finite-float fields and non-identity root index; adapters built for consumers. |
| CBO-014 | SP-I02 native emitter/views/descriptor and obsolete deployment-helper retirement. |
| CBO-015 | SP-I03 codec specification, native differential plus independent vectors; no silent lexical normalization. |
| CBO-016 | SP-I01/05 effective position classifier/validated visitor; explicit collision/sequence policy. |
| CBO-017 | Retain frozen cattrs products; SP-I01 actual result/enforcement use. Tuple defaults are subordinate simplification. |
| CBO-018 | SP-I07 semantic set kernels/native bindings before deleting useful old scaffolding. |
| CBO-019 | SP-I03 closure-level immutability then discharged-check removal; cumulative validations remain. |
| CBO-020 | SP-I07 set-oriented complete candidates and minimal post-resolution evidence carrying. Narrow recursive input scope needs equivalence. |
| CBO-021 | Retain seeded offline SchemaView/induction/generator isolation, SP-I01/04; do not substitute lossy materialized-derived schema. |
| CBO-022 | Deferred SP-I07 trigger: relevant repeated-join workload after correctness; preserve conclusions and final proof policy. |
| CBO-023 | Retain main-thread grammar deadline. Revisit process machinery only for an accepted concurrent grammar consumer. |
| CBO-024 | Retain pinned local ontology workaround. New term-validator/backend consumer or changed release triggers reassessment, not automatic dependency adoption. |
| CBO-025 | SP-I05 one explicit read-only opener/binders, SP-I03 shared purpose/target; preserve ADBC snapshot lifecycle. |

CA-01→SP-I01/02/03; CA-02→SP-I01; CA-03→SP-I05; CA-04→SP-I01/05/06;
CA-05→SP-I01; CA-06→SP-I01/02/03/04; CA-07→SP-I02/06/07 and original SP-09;
CA-08→SP-00 decision work + SP-I03/04; CA-09→SP-I08/09 and original SP-06;
CA-10→SP-I08/09 + affected original packages and final SP-10;
CA-11→SP-I01 profile decision with original SP-00/C02. All remain open until actual closure.
Original and completeness review O-identities retain their distinct mappings in §§6/10.

### Execution reasoning and acceptance

Prioritize behavioral correctness (bindings, conditionals, result/enforcement, graph attribution,
coverage, exact predicates and finite values) and shared scientific interpretation first. Settle
common products before dependent adapters, but do not impose whole-document barriers. Retained
native generation/reconciliation and meaning protection precede cheaper open and validation
removal. Establish template/reporting support before expanding expensive native parity checks.

Bundle the compiler/archive/rule-view/native/principal transition so fresh regeneration is done
once for a coherent capability. Required old query/explanation/export must still work with their
original IDs/dependencies and native read behavior before and after new activation. Selection
occurs only after complete output; failure preserves the existing answer. Original run 3 continuation
keeps task/packet/cut identity; completed results and reference grades are not reinterpreted.

Acceptance examples in the new packages extend the original required union: public malformed/
narrowed binding admission, submitted/unselected/selected constraint placement, every real result
alternative/enforcer, global versus missing-member coverage, graph-contract/closure attribution,
finalized-release and value-child insertion, prior/fresh physical migration, actual restricted
principals/workspaces, codec vectors, scientific policy tiers, used-input evidence, lifetime/
cancellation, clone ACLs and interrupted qualification. Independent expected cases remain alongside
model-derived parity checks. No proof ledger, generic rule engine or mandatory benchmark is added.

SP-09 still owns actual final source/provider regeneration/current entrypoints/retirement;
SP-10 still owns complete functional/native/provider/nonfunctional qualification. New support or
publication checks do not replace either. Preserve dated passing type/test evidence and failed/
interrupted records. Lint/format-only work does not trigger or invalidate functional/type checks.
Quantitative performance/quality benefits are unmeasured unless existing scoped receipts say
otherwise. Optional optimization, new providers, general historical migration/upcasters and
unrelated phase-0 features are not silently selected.

Document authoring uses the review's API/pin research and focused foundation advice against actual
archive/admission/inference code. No product/native/provider tests, dependency moves, migrations
or runtime cutover are performed by this revision. Publication/maintenance results are recorded
in STATUS. Plan selection is not implementation evidence; all added packages remain planned.
