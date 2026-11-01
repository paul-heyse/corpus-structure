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

Source baseline `1cb8e62003489d588a8f2041ea52b73ba096ec0f`; diagnostic publication
`cc2998d9`, **UM-20261101-r2**. Concurrent STATUS, PDF plan/evidence and Arrow/DuckDB guide edits
were read as context and preserved. Source under the product package was clean during this
inspection. Audit freshness and inherited limits are in the [audit](../audit/README.md).
October 29 DA/CBO conclusions were reconsidered where used; they are not freshly open by default.

Three scoped contributors mapped implementation, semantic capabilities and typed/analytical
capabilities; a fresh design reviewer independently compared integrated options after diagnostic
publication. The coordinator inspected decisive current sources and reconciled their judgments.
No recommendation audit or product remediation was initiated.

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
cannot prove a SQL body correct. Handwritten SQL remains appropriate for concurrent relational
invariants, with independent expectations when enforcement correctness is tested. Resolve this
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

## 12. Decision and next boundary

**Revise the inspected supported design; recommend the extended compiled-release target.**
Keep existing SQL/Arrow/graph/typed foundations. Correct query implementation pinning and resource
propagation, make comparison projection explicit, and settle invariant/enforcer observability.
Use those foundations for applicability explanation, semantic impact and actionable validation.
Select concrete improvements for implementation planning; no product changes are authorized by
this report. Target implementation and its complete relevant acceptance remain future work.
