# Deepening the unified domain model

## 1. Review contract and conclusion

**Proposed target; source-inspected and Interface-checked, 2026-11-01.** Library-targeted,
design/target review across the full core 3.3 standard, heuristics 1.0 and code-intelligence 1.4.
Scope includes all eleven requested guides, current semantic/runtime/native/analytical consumers,
and model-centered functional expansion. This is a completed design inquiry, not implementation
or product qualification. Tests, probes, provider journeys and measurements were **not_run**.

**Recommendation: deepen the existing compiled semantic release into the complete connection
between authored meaning, owned operation contracts, qualified implementations and consumers.**
The strongest target preserves scoped upstream schemas, LinkML application definitions, Python
domain functions, PostgreSQL integrity, typed Arrow/DuckDB execution and qualified RDF views.
The next improvements concern meaningful connections and reuse across these responsibilities.
The PostgreSQL followup selects **domain APIs backed by generated typed relational/native
implementations**, with minimal maintained SQL authorship. Retaining database-side execution
does not select handwritten SQL as its authoring mechanism.

Original source baseline `1cb8e62003489d588a8f2041ea52b73ba096ec0f`; diagnostic publication
`cc2998d9`, **UM-20261101-r2**. Concurrent STATUS, PDF plan/evidence and Arrow/DuckDB guide edits
were read as context and preserved. Source under the product package was clean during that original
inspection. Audit freshness and inherited limits are in the [audit](../audit/README.md).
October 29 DA/CBO conclusions were reconsidered where used; they are not freshly open by default.

Three scoped contributors mapped implementation, semantic capabilities and typed/analytical
capabilities; a fresh design reviewer independently compared integrated options after diagnostic
publication. The coordinator inspected decisive current sources and reconciled their judgments.
No recommendation audit or product remediation was initiated.

**PostgreSQL followup (2026-11-01):** original principal preserved at `f999ffcb`;
continuing diagnostic publication `54cd74cb` / UM-20261101-r3. All seven additional PostgreSQL
guides were read end to end, with Context7 then installed/tagged sources for consequential
interfaces. A fresh design reviewer assessed the integrated authoring alternatives. Dirty
contracts/PDF-staging model, native-candidate, PDF contracts/validators/publication, correspondence
and identity SQL, tests and evidence were treated as evolving source, not qualified deployments.
R01–R04/O01–O03 retain their identities; R05–R09 develop the added authoring target.

## 2. Current model and strengths to preserve

Paths in source citations below are relative to `python/corpus-structure/src/corpus_structure/`.
Architectural context is DESIGN §1/§B4/§B5, D1–D3 and D6–D8; pivot §13–15, the completed
PostgreSQL capability series, and the active PDF series distinguish delivery from accepted targets.

The current foundation is substantive:

- `semantic/composed.py:22–60` archives execution inputs. `contracts.py:713–745` requires the
  exact archived normalized product; consumers do not obtain a current-model fallback.
- `contracts.py:194–407` represents concepts, endpoint roles, relationship identity, state
  dimensions, transitions, invariants, effects, implementations, operation contracts and projections.
  `operation_results.py:61–99` validates actual results against release-owned dimensions.
- `semantic/sql/execution_projection_check.sql:11–40` reconstructs operation/transition/edge/effect
  products. `execution_guards.sql:1–96` enforces native lifecycle, ownership, receipts and sealing.
  These correct important earlier DA-026/041 manifestations; the catalog is operationally consumed.
- `boundary.py:154–239`, `types.py:379–430` and `prepare.py:731–741` provide prepared strict
  Pydantic boundaries, field metadata reuse, finite floats and structural/accepted validation scope.
- `analytics.py:498–507,637–700` derives Arrow fields from shared physical metadata.
  `companion_projection.py:82–163` derives SQL/Arrow return shapes. `pdf_payloads.py:45–169`
  preserves supplied fields and integer/binary64 distinctions in schema-derived IPC.
- `ontology.py:496–770` binds qualified graphs to their exact release, closure, collection
  positions, literal precision and snapshot; graph conformance remains distinct from inference.
- `inference.py:59–276` computes qualification-sensitive common closure with direct proofs,
  repeatable input and revision-fenced publication. A generic reachability result is a weaker contract.

These mechanisms establish implementation by static inspection. Their historical tests retain
their original dates and scope; this review does not independently requalify them.

## 3. Target architecture and interfaces

The release should connect six responsibilities: content/relationships, operations, state,
policy, scoped validation and consumer projections. Each semantic distinction has an owner;
representations are generated or explicitly mapped from that owner.

```text
domain definitions + trusted execution contracts + pinned native schema/vocabulary dependencies
                              |
                effective, checked, immutable semantic release
                              |
      +-----------------------+-----------------------+
      |                       |                       |
 Python construction     native integrity       qualified projections
 and domain operations   and atomic effects     Arrow/SQL, JSON, RDF/SHACL
      +-----------------------+-----------------------+
                              |
       bound query / explanation / export / agent / evaluation consumers
```

The diagram identifies meaning and dependency direction, not a service or execution stage per
box. Specialized algorithms remain ordinary functions with owned input/result/effect contracts.
Native Docling schemas remain upstream authorities bound by the application release. Application
identity, relationships, coverage and lifecycle remain application-owned.

**Deeper derivation target.** Extend the existing effective-definition and projection owners so
an added field/relationship supplies construction, reference positions, native requirements,
analytical shape and relevant graph/export views through checked mappings. Preserve intentional
different representations and scope. An engine-specific recipe may contain implementation detail;
its domain meanings must resolve to the release rather than another editable list.

**Operation interfaces.** Retain finite `OperationContract`, `ImplementationBinding`, result
dimensions and effect/transition products. Where an operation's concrete request/result shape
restates a declared concept, derive the structural part or bind a checked shape to the same
effective definition. Keep runtime resource inputs explicit and separate from semantic policy.
Avoid generating a universal dispatcher from arbitrary authored strings. Existing trusted symbol
bindings remain the effectful execution boundary.

**Feature realization.** Extend the admitted grammar only for selected required semantics,
including richer relationship roles, presence and constraint composition when they serve a real
consumer. Qualify the complete affected path before admitting the construct. Use current
required-capability/admission mechanisms; this requires no second feature registry or alignment lint.
Separate shape, occurrence, accepted-value, context and concurrent-state enforcement.

**Serialization.** Prefer prepared Pydantic serialization for mechanical supplied-field dumps
when it preserves the exact existing contract. Reference collection/rewriting retains its shared
semantic visitor (`reference_positions.py:31–221`), including paths, duplicate occurrences and
explicit collision policy. Decimal/date values, aliases and tuple/list distinctions constrain any
replacement of `_plain`/`_native` (`domain_operations.py:328–352`).

## 4. Corrections and complete-option comparison

<a id="R01"></a>

### R01 — Compile comparison policy separately from fact identity

**Proposed; DA-001 narrowed, A2/G1 unresolved.** `domain_operations.py:2589–2603` filters typed
qualification roles, then interprets raw `cs:qualifiers` minus `cs:identity_qualifiers` to obtain
comparison context. `prepare.py:985–1006` archives these predicate annotations independently.

Select a checked comparison projection that names context, compared meaning and retained evidence,
and relates them explicitly to full fact identity. Resolve references against effective properties
during preparation; scientific-policy consumers use the compiled projection. Reuse current
LinkML definitions, normalized products and ordinary typed functions.

Retaining raw interpretation leaves an extension dependent on hidden knowledge of two policies.
Forcing identical keys would reject legitimate comparison groups. Ownership statements differing
in interval or attribution must retain distinct facts even when a policy deliberately compares
them. The proposed contract makes that distinction deliberate; it does not infer current data
corruption from different keys. Closure needs an independent valid coarser-grouping example and
an invalid reference/cross-scope example reaching the real comparison consumer.

<a id="R02"></a>

### R02 — Bind named-query implementation meaning to the serving journey

**Proposed correction of current DA-028; highest consequence.**
`semantic/regeneration.py:109–125` archives `operation/queries.py`, but `cli/query.py:25–46`
selects the run's domain and imports the current pack through `serve/registry.py:51–76`.
Path/current-byte module hashing avoids cache collision but does not bind to the producing release.
Query versions in `serve/journey.py:117–127,199–203` help continuation handling; an unchanged
handwritten version cannot detect a changed implementation.

Preserve the query protocol and require an explicit trusted implementation identity/compatibility
binding against the archived release and query revision. On incompatibility, use a retained
supported implementation or refuse/reselect explicitly. Data snapshot, parameters, continuation,
explanation and evidence requests must agree on that meaning.

Current-file execution without a binding is inadequate. Arbitrarily executing archived Python
bytes creates dependency/security/lifetime obligations and is not selected. Blanket historical
runtime retention is also unnecessary: define supported compatibility and honest refusal through
the existing reader/admission boundary. Closure exercises the actual old-run CLI query, a plugin
edit, continuation and explanation/evidence access.

<a id="R03"></a>

### R03 — Resolve invariant-to-enforcer contract meaning

**Proposed clarification; DA-027 remains unresolved.** `contracts.py:1078–1090` checks invariant
and native-guard references; the native product comparator reconstructs operations, transitions,
edges and effects, not an equivalent invariant product. Handwritten guards do enforce conditions.

State which invariant fields are observable guarantees, which implementation/version realizes
each required invariant, and whether `failure_code` is a promised failure contract or descriptive
classification. If promised, its realizing boundary must preserve it. If descriptive, consumers
must not treat it as a guaranteed native diagnostic. Use existing bindings/admission where sufficient.

Generating all guards from a general constraint language is not selected. Metadata reconstruction
cannot prove a SQL body correct. Database-side enforcement remains appropriate for concurrent relational
invariants; its authoring should be structured/generated where feasible (R07). A residual
handwritten body needs a specific justification rather than a default exemption. Preserve
independent expectations when enforcement correctness is tested. Resolve this
ownership question before planning additional lowering or claiming an A2/G3 pass.

<a id="R04"></a>

### R04 — Propagate resources and close the supported lazy-result boundary

**Proposed correction of narrowed DA-020.** `settings.py:98–108` declares analytical threads,
memory and scratch controls. `domain_operations.py:2050–2075` creates `AnalysisScope(packet)`
with separate defaults (`analytics.py:1018–1025`). Pass selected typed process resources through
the operation boundary; retain release-owned arithmetic policy separately. New environment access,
settings roots, source providers and resource registries would not repair that missing input.

**Unresolved lifetime qualification:** `analytics.py:429–462,1170–1183` guards borrowed
relations/connections/readers but not Python generators. Installed DuckDB's delayed `iter_rows`
submits on first iteration. A later iteration therefore bypasses the scope's explicit guard;
successful post-close consumption was not demonstrated. Select the supported lazy interfaces
and guard consumption or refuse unsupported delayed results using the existing owner. Preserve
detached materialized outputs and the guarded Arrow-reader route. A focused pre/post-close
consumption case is appropriate before a stronger correctness claim.

### Integrated alternatives

| Complete option | Judgment and reason |
|---|---|
| Patch each consumer independently | Repairs individual symptoms but retains repeated policy interpretation and incomplete implementation binding. Insufficient target. |
| Extend effective release products and existing typed/native consumers | **Selected target.** Preserves real guarantees, localizes semantic additions, reuses library execution and allows appropriate physical specialization. |
| Universal RDF/SHACL execution | Graph conformance cannot discharge leases, atomic publication or concurrent native transitions; added graph conversion would leave those mechanisms necessary. |
| Broad Map/Datalog replacement | Relevant capabilities exist, but their stable semantics do not discharge the present complete translation/inference contracts. Named future use remains eligible. |
| Universal workflow/operation interpreter | Finite implementation bindings already provide the needed seam. Another language and execution lifecycle lacks a concrete requirement. |

<a id="R05"></a>

### R05 — Generate the complete typed domain-call boundary

**Proposed.** Ordinary callers use named domain operations with typed arguments/requests and
results. The selected operation definition and trusted implementation binding supply parameter
identity, codec, nullability, cardinality, result projection and failures. Existing `claim_tasks`
and companion export already expose domain-facing APIs; extend their internal continuity.

Generate explicit implementation signatures, model-derived Core function calls/selects, private
bind dictionaries and result materializers together. Reuse `TypedColumns`, narrow column protocols,
`GenericFunction[T]`/typed table-valued calls and explicit positional projections; emit `__row_pos__`
when whole-row typing is required. Materialize external rows through the bound validated result
contract. Keep genuinely dynamic records at declared checked boundaries, with unknowns explicit.

`with_cols` only adds static information; it performs no runtime validation. SQLAlchemy parameter
mappings are not statically linked to the statement, and `RowMapping` values are `Any`. Generating
only annotations or casting a final mapping therefore does not establish this target. A named
function signature must reject incompatible parameters statically, and runtime admission must
still reject incompatible actual server output. Do not replace domain calls with a general
`execute(name, dict)` API. Generate thin code in existing owners; no service or registry is needed.

<a id="R06"></a>

### R06 — Author relational implementations through model-bound expressions

**Proposed selected primary route: SQLAlchemy Core.** Reuse the current effective metadata and
typed projections for joins, CTEs, lateral/recursive relations, aggregates, JSON access, typed
casts and insert-from-select/conflict DML. Preserve native set operations and complete qualified
universes rather than pulling data into Python to avoid SQL syntax.

Concrete first applications are companion `cp:sql` expressions/joins and inference seed/update
queries. Resolve projection inputs to authoritative fields, operation parameters and typed
transformations; generate Core expressions and static result shapes from that definition.
SQL strings in YAML, `literal_column`, `text`, `tstring`, f-strings and compiler templates all
remain authored SQL when a maintainer must specify their grammar. Moving them is not elimination.
A small existing expression vocabulary may suffice; do not invent a general query language.
Where a specialized algorithm is clearer in ordinary typed Python composing Core, retain that
implementation behind its domain contract instead of forcing the algorithm into schema data.

Selective imperative ORM mapping over existing generated tables, composites and hybrids is a
credible alternative for a named editable aggregate. Wholesale ORM is not selected for immutable
releases, protected publication or analytical batches: sessions, identity maps, flushes and hidden
loading add obligations, and object events do not protect independent writers or bulk DML.

<a id="R07"></a>

### R07 — Make native SQL a generated product wherever the contract permits

**Proposed target, partly Interface-checked; complete procedural elimination unresolved.**
Use existing Core Table/Constraint/Index/CreateView DDL first. Use pglast PostgreSQL nodes for
missing declarations, names, ownership/privilege/trigger forms and appropriate SQL-language
function bodies. Its 8.7 `CreateFunctionStmt.sql_body` printer supports `ReturnStmt` and
`BEGIN ATOMIC` sequences. This is an affirmative route beyond opaque string bodies.

Current `native_inventory.py:20–26` requires `AS`, hashes the source string, and
`native_objects.py:311–314` rejects observed SQL-standard bodies. Extend inventory, native
identity/body custody, catalog normalization, dependency comparison and admission together
before using the structured route. Definition-time name/dependency binding differs from
string-body behavior. `CREATE OR REPLACE`, overload/result changes, safe search paths, owner,
ACLs, volatility and replacement dependencies must retain their declared semantics.

For guarded mutation, compare typed relational predicates/DML plus a bounded assertion/effect
pattern against each actual routine. `sql/selection.sql` and `sql/fact.sql` offer concrete
assert + delete/insert-from-select cases. Existing operation/state/effect catalogs provide
contracts, but do not currently encode executable predicates, order or locking sufficient to
generate arbitrary bodies. Typed implementation programs must supply that realization and
remain bound to their semantic owner. A small lowering must earn its total machinery cost.

Retained procedural families requiring qualification include trigger `NEW`/`OLD`/return behavior,
IF/RAISE and SQLSTATE, mutable record/variable assignment, loops and dynamic EXECUTE. pglast's
PL/pgSQL parser returns dictionaries; SQLGlot does not supply a complete procedural authoring
contract. Full elimination is therefore **unestablished**, not categorically impossible. Each
residual needs a named construct gap, scope, owner and elimination route; a handwritten renderer
still counts as SQL maintenance. Do not weaken native locks, atomic effects or restricted writer
privileges to remove source strings. Arbitrary procedural compilation is not selected.

Keep the actual Alembic Plugin/comparator/operation/renderer chain, explicit predecessor/desired
sets, before/after catalog checks and frozen payload execution. Structured authoring changes the
input to that lifecycle. Frozen migrations remain immutable products independent of current
compiler code. Cover catalog queries with Inspector where complete; use bounded model-derived
Core catalog expressions for necessary omitted properties, preserving version and scope.

<a id="R08"></a>

### R08 — Use SQLGlot as complementary model-derived analysis where valuable

**Proposed selected capability direction; first integration conditional on exact-version checks.**
The named candidate is companion-family projection qualification/type/dependency analysis and
its contribution to O02. Derive `MappingSchema` and UDF return metadata from the same effective
model/native signatures, construct `exp` nodes directly, and use qualification/scopes,
`annotate_types` and column lineage to explain output dependencies and catch unresolved mappings.
Use strict column qualification before lineage (whose default internal pass disables validation).
Distinguish declared routine parameters from driver placeholders. Unknown types/functions remain
unresolved; unsupported PostgreSQL constructs must fail explicitly.
Use exact PostgreSQL dialect semantics and compare any generated output with server admission.

This is stronger value than adding another SQL renderer. Keep Core as the primary relational
implementation so SQLGlot is not a second writable schema or mandatory AST hop for every query.
A bounded secondary projection may be worthwhile for dependency analysis, with a mapping from
its fields to model identities. A central SQLGlot IR would unify more analysis but requires much
broader parameter/result/DDL/catalog/driver bridges; its unproven benefit does not justify that
migration now. Parsing already-generated SQL is acceptable for analysis, but does not itself
remove authorship; direct model lowering remains the authoring objective.

AST Python classes and runtime SQL type annotation are not static domain/result typing, server
function-overload resolution or authorization. AST diff/lineage contributes declared syntactic
impact, not behavioral equivalence, row provenance or complete semantic change detection.

<a id="R09"></a>

### R09 — Preserve domain typing through directional transport and execution

**Proposed extension of existing profiles, not a transport rewrite.** Derive bindings, codecs,
result shapes and wire mappings from the operation's authoritative model and verify them at
external boundaries. Retain current Core/Psycopg transaction ownership and pgpq fresh encoders for
atomic scratch/publication writes; pgpq DDL is not an alternate semantic schema. Psycopg row
factories/custom adapters fit only where they remove a real conversion gap without duplicating
model definitions or bypassing Core's owner. Custom PostgreSQL types require explicit OID and
schema lifecycle, not just a Python class.

Keep separate ADBC sessions and imported snapshots for selected analytical reads. Generated Core
SQL for COPY is already machine output, so literal rendering need not be replaced solely to
reduce authored SQL. ADBC 1.13 supports `$n` bound result queries, but uses a non-COPY PGresult
path without COPY batch hints, with potentially lazy execution per parameter set. Select that
route only for a concrete parameterized consumer whose memory/effect/lifetime contract fits.
ADBC ingestion does not automatically preserve the current same-session staging/adoption contract.
Model exact numeric/null/JSON/temporal/array/composite asymmetries rather than treating Arrow,
Python and PostgreSQL storage types as identical.

## 5. Library coverage and comparative dispositions

Focused mechanisms, exact-version evidence and residual obligations are preserved in the
[semantic assessment](../../library_leverage/libraries/unified-model-semantics_2026-11-01.md) and
[boundary assessment](../../library_leverage/libraries/unified-model-boundaries_2026-11-01.md).
Those accounts distinguish capability existence from contextual fit; this section selects direction.

| Library and capability families surveyed | Current use and target disposition |
|---|---|
| **LinkML:** effective slots/imports, mixins/keys, rules/presence/extension, relationship roles/OWL, generators including Rust, units/vocabulary metadata | Retain closed preparation and contextual induction. Deepen checked comparison/relationship/operation projections where selected. Standard role metadata can improve discoverability, but requires faithful admitted lowerings. Rust generation is not selected without a maintained native consumer; unit metadata is not dimensional computation. |
| **RDFLib:** terms/collections, Graph/Dataset, paths/closure, query/update/algebra, canonicalization, stores, parsing/serialization and patching | Retain qualified occurrence-aware graph views. Reuse supported shared paths when consumers need them. No new graph service/store/publication or patch-based transaction authority is justified by current scope. |
| **pySHACL:** Core/SPARQL components, targets/focus, qualified constraints, reports, rules/functions, RDFS/OWL-RL/JS, CLI/service | Retain explicit nonmutating conformance. Parameterized components fit repeated graph constraints and O03. Targeted validation needs full relevant universe; dataset union is not isolation. Advanced rules/entailment remain separately scoped candidates, not native lifecycle enforcement. |
| **Pydantic:** models/dataclasses/TypedDict, dynamic schemas/adapters, annotated types, variants, strictness/presence, validators/serializers, custom core schemas, callables, diagnostics, experimental APIs | Retain prepared strict boundaries and shared field/reference products. Reuse serializers for equivalent mechanical projection. Callable shape checks do not authorize effects. Lazy/omission/partial APIs need explicit failure/coverage semantics; no adoption for novelty. |
| **pydantic-settings:** nested acquisition, merge/aliases, files/secrets/cloud sources, CLI models, custom sources/cache/reload | Retain one deliberately restricted process snapshot; repair resource propagation. Reuse semantic types appropriately. Extra acquisition sources or CLI-framework replacement have no demonstrated consumer here. |
| **Valuesets:** rich enums, hierarchy/mappings/SSSOM, dynamic membership, classification, quantities, generation/governance | Consume useful vocabulary definitions through pinned full snapshots. Source search found no direct product import of valuesets: pin/determinant inclusion is not demonstrated direct execution. Existing OAK/Term Validator membership is real use of that ecosystem. RichEnum is a projection, not complete vocabulary authority. |
| **jsonschema:** draft-specific assertions, conditionals/references/dynamic resources, registries, errors, custom keywords/types/formats/dialects | Retain checked cached validators with retained local resources. Explicitly qualify format/dialect/custom semantic enforcement; output JSON Schema is a projection of executable behavior. Structured errors support O03 without creating another validator. |
| **LinkML-Map:** class/slot/enum derivation, expressions/units/sentinels, collection/pivot/join, typed targets, schema mapping/inversion/compiler, streaming writers | **Conditional named pure translation only.** Stable joins select at most one match/key; SQL lacks interpreter parity; columnar output stages JSONL/inferred types. Not selected for typed candidate/publication replacement. Preserve source occurrences, exact types, presence and provenance before adopting a concrete mapping. |
| **LinkML-Datalog:** schema/property inference, de-reification/classification, validation, custom Soufflé relations, exporter/runner/materialization | **Retain qualified SQL inference.** Alpha numeric lowering, asserted/derived interaction, occurrence/set semantics and incomplete materialization leave replacement fit unestablished. Reconsider for a named required rule family beyond the current kernel, with modern compatibility and proof qualification. |
| **PyArrow:** nested/extension types, compute/UDFs, Acero/Substrait, datasets/scanners, joins/aggregation, IPC/Parquet, memory/interchange/devices, Flight/filesystems | Retain schema-derived IPC and operation-shaped columnar products; preserve explicit presence/exactness and memory ownership. Native compute/Acero can replace a kernel where its full semantics fit. Substrait portability, Flight/cloud/device infrastructure have no selected consumer; extension metadata alone does not enforce domain meaning. |
| **DuckDB 2:** typed relations/expressions/macros, joins/recursion/windows, nested/JSON/VARIANT, readers/appender, optimizer/spill, constraints/triggers, graph/spatial/search/extensions, storage/federation/lakehouse/secrets | Retain owned relational analysis with explicit scopes and resources. Select native set/bulk operations by operation semantics. VARIANT/TRY/approximation cannot erase distinctions silently. DuckPGQ is a candidate projection, not a new graph authority. Federation/lakehouse/search/secrets add no selected requirement here. |

The inspected manifest pins Pydantic 2.14.1, settings 2.16.1, pySHACL 0.40.1, jsonschema 4.26.0,
Arrow 26.0.0, DuckDB 2.0.0, LinkML/runtime 1.12.1, RDFLib 7.6.0 and Valuesets 0.4.2. Map and
Datalog are not product dependencies. Pydantic 2.14.2/settings 2.16.2/pySHACL 0.40.2 addenda
identify candidate upgrades; their fixes are not credited to current pins. Map 0.6 prerelease and
unmerged Datalog work are separate from stable/alpha candidates. Version moves belong to selected
implementation and affected qualification, not a blanket upgrade or adoption requirement.

### PostgreSQL followup coverage

The [seven-library assessment](../../library_leverage/libraries/unified-model-postgresql_2026-11-01.md)
records the full capability-family survey, actual utilization and exact-version conditions for
SQLAlchemy 2.1.6, pglast 8.7, SQLGlot candidate 30.27.0, Alembic 1.20.1, pgpq 0.12.0,
Psycopg 3.3.6/pool 3.3.3 and ADBC PostgreSQL 1.13.0. SQLGlot is not currently a product dependency.
Core/compiler/native authoring, ORM alternatives, Alembic operation rewriting, adapters/row
factories and ADBC binding/ingestion were considered, not just previously used entry points.
Async/pipelines/TPC/notifications, generic dialect portability and new federation do not currently
remove the identified authorship gap and are not selected additions. No dependency was installed.

## 6. Change, failure and execution-fit scenarios

**Qualified business relation:** add ownership with validity interval, attribution and repeated
source assertions. Effective fields govern construction/reference closure; R01 states which
interval/attribution distinctions enter comparison; SQL preserves occurrence/reference integrity;
Arrow and graph views preserve scope/multiplicity. A primitive `(subject, object)` edge would be
insufficient. This reveals why typed relational progress helps while Map's single-match join is
not equivalent to this operation.

**Lifecycle extension:** add a terminal partial outcome or a required transition effect. Existing
finite contracts/native rows should carry supported variation; new algorithmic semantics still
need a qualified implementation/version. O01 can explain readiness, but a concurrent writer can
invalidate preflight. Native atomic guards remain authoritative before effects.

**Mechanism substitution:** replace one pure translator or analytical kernel. Preserve exact
values, absent/null, multiplicity/order, projection universe, outcomes and dependencies. SQL/Arrow
may fuse work without another hop per semantic concept. Match transformation and failure behavior,
not just field names; a Map configuration or Arrow cast is not automatically equivalent.

**Evolution:** edit a query plugin after completing a run. R02 must retain compatible meaning or
refuse, including continuations/explanations. Change a comparison projection or validation profile:
O02 should identify declared affected consumers; existing archives retain their producing contract.
No blanket historical HTML compatibility requirement is added.

**Growth/recovery:** high-degree closure can require much more work than the returned page.
Keep common closure, joins and aggregation in suitable engines, reduce inputs only when universe
semantics permit, and hydrate useful detail. Streaming interfaces do not make blocking operators
constant-memory. Keep immutable preparation reusable; preserve exact pinned premises through
validation/seal rather than reconstructing them at every crossing. Partial OCR or failed validation
does not imply absence or a completed product. Cancellation settles owned readers/work; R04 ensures
resources and supported lazy results honor that existing ownership boundary.

These are source-reasoned design scenarios, not executed journeys or capacity measurements.

**Followup acceptance scenarios (future implementation):** (1) add/change an operation parameter
and result field through generated domain signature, native binding and decoder; include wrong
types, NULL and cardinality. (2) add a companion field and change JSON path/cast/scope; derive
Core/Arrow/result types and dependency analysis together. (3) generate and deploy a structured
SQL-language body; verify body/dependency/catalog identity, privilege refusal and changed result
recreation. (4) change a guarded mutation without losing lock/failure timing or atomic rollback;
exercise stale-owner/independent-writer and duplicate/conflicting inputs. (5) evolve a view or
same-name constraint while preserving frozen predecessors and drift refusal. (6) compare bound
ADBC with COPY on exact schema/value and partial-consumption/cancellation semantics.
Static negative typing cases and native independent expectations establish different guarantees.
None of these scenarios was executed for this source-based followup.

## 7. Findings, functional opportunities and disposition

The diagnostic findings retain DA identities and one primary home. R01–R04 above are remedy
references; R03 is an unresolved assessment, not a new proven violation. DA-028 supports an
immediate correction; DA-020 supports a bounded integration correction. Other depth improvements
can be worthwhile without diagnostic failure. No new finding ledger or accepted schedule is created.

<a id="O01"></a>

### O01 — Explain available operations and missing prerequisites

**Proposed; operator/agent value.** Given a release and subject, explain declared operations,
their inputs/results, supported implementations, applicable state and missing prerequisites.
Reuse `OperationContract`, transitions/dependencies and implementation bindings
(`contracts.py:307–355,1176–1224`), plus actual owner-specific checks. Return unavailable and
unresolved distinctly. This helps agents choose valid next actions and operators diagnose refusal.
Descriptive invariant text must not become executable policy. Preflight explains; the operation
rechecks mutable conditions atomically. Start with maintained read/analysis/publication operations,
not a new universal dispatcher. Delivery needs real CLI/MCP use and a stale-preflight refusal case.

<a id="O02"></a>

### O02 — Explain semantic changes and affected consumers

**Proposed; developer/operator value.** Compare normalized release products and identify changed
comparison roles, result dimensions, invariants, projections or implementation requirements and
their declared consumers. Reuse existing dependencies, identities and archive products rather than
inventing a semantic-diff language. The output guides compatibility/regeneration decisions more
directly than YAML diffs. Unknown impact stays explicit; it does not claim complete behavioral
equivalence or replace independent verification. Begin after R01/R03 clarify the relevant contracts.
Delivery needs a changed qualifier/result/projection example and a conservative unknown case.

<a id="O03"></a>

### O03 — Actionable validation across representations

**Proposed; operator/agent value.** Locate a failure by model concept/relationship, exact path,
operation and enforcement scope, retaining the original diagnostic and a remedy category.
Compose existing preparation diagnostics, Pydantic errors, JSON Schema located errors and
`GraphDiagnostic`; enrich reports through explicit mappings. Reuse repeated pySHACL SPARQL
components when useful. Preserve nonconformance, invalid shape, execution failure and unassessed
coverage as distinct outcomes. Do not create a second semantic validator or infer a common
truth value from superficially similar messages. Delivery needs actual consumers for an invalid
input, cross-record failure and validator infrastructure failure.

O01/O03 have the clearest immediate operational value; O02 depends on clearer policy/dependency
contracts. R02 has highest correctness consequence. Prerequisite order differs: resolve R01/R03
before richer derived policy/impact tooling; R04 can proceed independently. Detailed work packages,
API wire shapes and final acceptance unions belong to subsequent selected implementation planning.
Unscheduled proposals remain here; accepted plans will own their disposition and closure evidence.

R05–R09 strengthen O01 with generated callable contracts, O02 with qualified projection
lineage, and O03 with exact model/parameter/output locations. They introduce no separate
opportunity ledger. Their prerequisite route is shared semantic request/result/projection
contracts → domain-call generation and Core lowering → structured native custody/admission →
consumer migration. SQLGlot analysis can start with one settled projection; it need not block
all domain calls or native generation. R02's existing query-pinning defect remains urgent.

## 8. Independent architectural judgments

| Judgment | Inspected current design | Recommended target |
|---|---|---|
| A1 Change locality | Substantial effective-model/physical derivation; plugin and qualifier policies still require independent edits/knowledge. | Extend current compilation and implementation bindings; preserve specialized kernels. |
| A2 Model adequacy and governance | **Revise:** DA-028 is a concrete consumer gap; DA-001 and invariant correspondence require explicit semantics. Existing operation/state governance is real. | Coherent six-responsibility model with R01–R03; conditional until invariant scope is settled and realization verified. |
| A3 Composition/local reasoning | Strong explicit preparation, snapshots, finite bindings and typed/native boundaries. | Reuse those owners for richer consumers; no universal interpreter. |
| A4 Execution fit | Credible set/columnar route; DA-020 resource propagation needs correction; lazy iterator support unresolved. | Preserve native execution/precision/closure and bounded ownership; correct resource inputs. No quantitative benefit established. |

Applicable FP-01–07 and DP rules are assessed through these scenarios: FP-02/04 and DP-01/08/09/24
are affected by R02; FP-04/DP-04 by R01's explicit equivalence relations; FP-05/DP-03 by R03;
FP-01/06/07 and DP-18/20 by R04. DP-13–16 favor complete existing library capabilities over
new generic machinery, while preserving actual residual semantic obligations. No novelty or
dependency-count score determines alignment.

**Followup delta:** A1/A3 favor generated domain boundaries plus existing Core/Alembic owners;
A2 needs executable signature/projection/enforcer correspondence beyond static AST annotations;
A4 preserves bulk server/columnar execution and avoids a mandatory second AST/catalog per call.
The proposed structured-native route has unresolved admission/body-dependency equivalence.
Current G1/G6 failures and other unresolved gates below remain; no authoring-library choice
closes them automatically. G8's positive scoped comparison now includes all seven libraries.

## 9. Correctness and fidelity gates

These are **current inspected-scope** judgments; none is an assembled-product acceptance result.

| Gate | Verdict | Evidence and limit |
|---|---|---|
| G1 Authority | fail | DA-028 live plugin interpretation for archived runs. |
| G2 Semantic fidelity | unresolved | Strong qualified typed/graph/IPC mechanisms; broader supported consumers not dynamically qualified here. R01 needs declared comparison semantics. |
| G3 Validity | unresolved | Existing structural/native/graph enforcement; R03 invariant correspondence and full enforcement union not settled by this inspection. |
| G4 Hidden behavior | unresolved | Explicit scoped effects and closed imports are strengths; live plugin binding needs correction; all execution paths not audited in depth. |
| G5 Consistency/recovery | unresolved | Native projected transitions, fences and receipts exist; no new concurrent/recovery journeys run. |
| G6 Transformation/reuse | fail | Pinned data and continuation version do not pin current plugin implementation meaning. |
| G7 Truthful claims | pass for this report | Source/interface/proposed labels and not_run boundaries are explicit; no system-wide capability certification. |
| G8 Library leverage | pass for scoped selection | All eleven surveyed; complete alternatives and concrete residual obligations considered. Conditional Map/Datalog use remains eligible. |
| CI-G1 Typed fidelity | unresolved | Qualified graph/unknown/occurrence mechanisms exist; all supported assertion consumers not qualified here. |
| CI-G2 Evidence closure | unresolved | Source/result pinning strengths; query implementation gap and no fresh evidence journey. |
| CI-G3 Independent evaluation | unresolved | Existing independent evaluation retained; test/evaluation architecture and provider qualification were not refreshed. |

## 10. Evidence limits and rejection of unsupported claims

Library guides orient full-family coverage; exact consequential contracts were checked through
Context7 followed by installed/tagged sources, with precise routes in both applicability accounts.
Static inspection established current DA-028/020 manifestations and the narrower DA-001/027
questions. A suspected enum key/text loss was rejected because LinkML normalization prevents
the proposed input. Rejected unsupported LinkML features are profile boundaries, not defects.

No test suite, runtime probe, external service, database mutation or dependency change was used.
No measured speed/memory/quality benefit follows. New Map/Datalog compatibility and runtime lazy
iterator behavior remain untested. Unexamined native guard bodies and test/provider universes
remain coverage limits; historical tests are not promoted to current passes.

**Documentation verification (2026-11-01):** `just docs-check` **failed** on existing
library-reorganization publication/source links (for example old `docs/libraries/pyarrow.html`
and `linkml_extension_libraries.html` routes). Its diagnostics named no new unified-model report
or applicability path. This review does not repair that unrelated link migration. Product tests
and probes remain **not_run**, appropriate to this source/documentation review.

**Followup documentation verification (2026-11-01):** `just docs-check` **failed** on the
existing library-reorganization `.html` links; diagnostics named no unified-model principal,
new PostgreSQL applicability account or followup audit anchor. No product test/probe was run.
The earlier check above retains its original scope; this is the followup command outcome.

## 11. Rule impacts and transition boundaries

No mandatory replacement of §B decisions is selected. R01–R04 fit scoped semantic authority,
finite implementation admission and PostgreSQL instance integrity. Implementation must amend D2/D5
comparison ownership, D8 query implementation compatibility, D2/D3 invariant observability and D6
resource composition as their meanings are selected. Any concrete change to an accepted decision
needs its existing ADR route; this review does not amend accepted ADRs.

O01–O03 expand functional scope only if selected. A concrete Map adoption or broader inference
profile would need its source/target/rule contract, supported realization and consumer acceptance.
The old Datalog deferral is reconsidered here on current evidence rather than treated as a veto.
Current PDF deployment/default adoption and qualification stay with the PDF coordinator. This
review neither imports that unfinished work into another series nor closes its findings.

### Followup rule impacts

| ID | Current owner/choice affected | Proposed change and decision route |
|---|---|---|
| RC01 | D2/D3 and PG-03's retained native set-SQL choice | Domain APIs become normal caller boundary; model-derived Core and typed operation materializers replace independently authored query/call/projection text. Authorship reduction is now a concrete benefit. Amend architectural owners through selected implementation planning; do not edit the completed PG plan's historical scope. |
| RC02 | Native-body retention in D3/PG native-object realization; current AS-only/prosqlbody-refused profile | Permit qualified structured SQL-language bodies and generated native declarations; version body/custody/catalog/admission products together. Extend supported scope deliberately via existing ADR/owner route. No automatic procedures/general PL/pgSQL support. |
| RC03 | New SQLGlot analysis realization supporting D2/D8/O02 | Select one model-bound analysis consumer and exact dependency only if useful after qualification. Routine dependency addition needs no ADR by itself; any changed semantic authority does. |
| RC04 | Hypothetical client-side replacement of protected functions | Would change §B4 enforcement/privilege responsibilities. Not selected; requires explicit architectural decision if later proposed. |

R05–R09 are recommendations, not implementation permission. No plan, accepted ADR, operational
default, native deployment or dependency manifest is changed by this report. Generated/frozen
SQL and deliberate invalid SQL fixtures remain legitimate output/evidence; maintained handwritten
queries, bodies, annotations and compiler templates remain within the minimization objective.
No zero-SQL or fully-static end-to-end implementation claim is made.

## 12. Decision and next boundary

**Revise the inspected supported design; recommend the extended compiled-release target.**
Keep PostgreSQL execution, Arrow/graph fidelity and typed foundations. Select generated typed
domain APIs, Core relational implementations, structured pglast native declarations/appropriate
SQL-language bodies and current Alembic lifecycle. Add complementary SQLGlot analysis for a named
projection when it supplies useful qualification/dependency information. Minimize maintained SQL
through R05–R09; complete procedural SQL elimination remains unresolved construct by construct.
Correct query implementation pinning and resource propagation, make comparison projection explicit,
and settle invariant/enforcer observability.
Use those foundations for applicability explanation, semantic impact and actionable validation.
Select concrete improvements for implementation planning; no product changes are authorized by
this report. Target implementation and its complete relevant acceptance remain future work.
