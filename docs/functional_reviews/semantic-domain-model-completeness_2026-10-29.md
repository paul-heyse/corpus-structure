# Complete domain model for the transitioned semantic system

**Functional-extension review · Proposed · 2026-10-29.** This review recommends a stronger target;
it does not amend accepted decisions, implementation plans or package completion. The
[target-model companion](semantic-domain-model-completeness_2026-10-29_target-model.md) specifies
the connected model, relationships, lifecycle contracts and enforcement responsibilities.

## 1. Conclusion and functional value

Retain the existing semantic release and PostgreSQL architecture. Extend its authoritative
model to cover operational concepts, relationship semantics, composed state and operation
contracts as completely as it covers domain values and assertion shapes.

The recommended realization is **LinkML-centered and composed**: authored LinkML definitions
and typed behavioral contracts govern ordinary domain functions, generated boundary types,
SQLAlchemy Core composition and protected PostgreSQL transitions. Specialized source placement,
scientific comparison, identity and proof algorithms remain owned functions. Their inputs,
applicability, effects, outcomes and implementation dependencies become explicit parts of the
same model. A universal workflow engine or conversion of every algorithm into YAML would add
machinery without supplying the missing semantic guarantees.

This lets the operator, an extraction agent and the next implementer answer:

- What does this relationship mean, which endpoints can it connect, and what authorizes it?
- What can happen to this task, run or result now, and what would completion establish?
- Which differences represent another fact, another source occurrence, another assessment or
  another execution attempt?
- Where is a constraint enforced, including when a caller bypasses Python preflight?
- Can a new relation, rule or transition be declared without independently reconstructing its
  meaning in adapters, SQL, source packets and analytical views?

The proposed benefit is better extension locality, discoverability and consistent enforcement.
It is reasoned from the inspected implementation; no new performance or runtime qualification
claim follows.

## 2. Baseline, scope and evidence

The inspected source is main **80fe11b4c7aa4ea86966262093fe943c54d6686a**, including the existing
uncommitted working tree, on 2026-10-29. The supplied PyOxigraph, Oxrdflib and linkml-map
overviews were present as untracked documents. They were read and preserved.

Scope is SP-00–SP-05 and delivered SP-06/SP-07 behavior in the
[pivot coordinator](../plans/semantic-model-pivot_2026-10-29.md), including migrated paths within
shared modules. Remaining SP-08–SP-10 migration is excluded. A legacy path is not a completeness
gap merely because its future pivot package is unfinished. Proposed improvements can change
already-transitioned operations wherever the stronger model requires it.

The applicable standard is core 3.3, efficient-architecture heuristics 1.0, code-intelligence
profile 1.4 and the corpus-structure binding, selected by
[standard.toml](../design_review/design_principles/standard.toml). FP-04/FP-05 and
DP-01–DP-08 govern semantic authority, relationships and behavior. FP-07/A4 constrain realization;
CI-01–CI-06 and CI-08/10/11/13 preserve provenance, fidelity, context and completeness.
The test-assessment companion informs the scenarios in §8, not a new test campaign.

**Evidence strength:** implementation observations below are static source inspection.
Consequential library mechanisms were checked through Context7 and primary/installed sources;
exact versions and candidate limits are recorded in §6. No production changes, installations,
probes, benchmarks, type checks, lint cleanup or product tests were performed for this review.
Existing passing type and targeted-test receipts remain passing with their original scopes.
This is a functional review, not a diagnostic audit, completion audit or regrade.

### Inspected source anchors

Paths below name the source locations inspected, not new authorities.

| Anchor | Implementation and relevant contract |
|---|---|
| S1 | [Semantic core](../../python/corpus-structure/src/corpus_structure/model/semantic/core.yaml), AssertionOccurrence/SemanticFact at lines 157–197; values, qualifications, conditions and bindings |
| S2 | [Physical model](../../python/corpus-structure/src/corpus_structure/model/semantic/physical.yaml), project/realization at 327–383, run/task at 1208–1370; fixed keys, foreign keys and SQL checks |
| S3 | [Preparation](../../python/corpus-structure/src/corpus_structure/semantic/prepare.py), unsupported constructs at 60–78, adapters/products at 784–843, operation artifacts at 942–1002 |
| S4 | [Releases](../../python/corpus-structure/src/corpus_structure/semantic/releases.py), persist/load/activate at 238/330/424 |
| S5 | [Operations](../../python/corpus-structure/src/corpus_structure/semantic/operations.py), run binding, task scheduling/claim/completion, source custody and held submissions |
| S6 | [Lifecycle guards](../../python/corpus-structure/semantic_alembic/versions/semantic_0012_observation_inputs.sql), run/task/cut guards at 39–126; [final-cut barrier](../../python/corpus-structure/semantic_alembic/versions/semantic_0015_source_selection.sql) |
| S7 | [Agent submission](../../python/corpus-structure/src/corpus_structure/intervene/semantic.py), held/refused/terminal results at 152–229; [native hold/cancel](../../python/corpus-structure/semantic_alembic/versions/semantic_0020_agent_resubmission.sql) |
| S8 | [Domain operations](../../python/corpus-structure/src/corpus_structure/semantic/domain_operations.py), immutable replay at 184–242, coverage at 945–955, atomic evaluation at 1555–1740, scientific policy and assessments afterward |
| S9 | [Publication](../../python/corpus-structure/src/corpus_structure/semantic/publication.py), typed rows/batches and one retry owner; [current frozen transport](../../python/corpus-structure/semantic_alembic/versions/semantic_0021_transport.sql) |
| S10 | [Ontology projection](../../python/corpus-structure/src/corpus_structure/semantic/ontology.py), scoped generation at 122–234, qualified assertions at 357, validation at 398 |
| S11 | [Inference](../../python/corpus-structure/src/corpus_structure/semantic/inference.py), snapshot/finite closure; [native grounding](../../python/corpus-structure/semantic_alembic/versions/semantic_0007_inference.sql) |
| S12 | [Analytics](../../python/corpus-structure/src/corpus_structure/semantic/analytics.py), packet/snapshot and AnalysisScope at 313–466; [Arrow publication](../../python/corpus-structure/src/corpus_structure/semantic/arrow_publication.py) |
| S13 | [Source reports](../../python/corpus-structure/src/corpus_structure/model/semantic/observations.yaml), [query contracts](../../python/corpus-structure/src/corpus_structure/semantic/query.py), [source-run adapter](../../python/corpus-structure/src/corpus_structure/orchestrate/semantic.py) |
| S14 | [Scientific rule input](../../python/corpus-structure/src/corpus_structure/semantic/domain_operations.py), ReleasedRulesPolicy; [authored SQL admission](../../python/corpus-structure/src/corpus_structure/semantic/authored_sql.py) |

## 3. What already works, and what completeness adds

The current implementation contains substantial semantics and important protection. Preserve:
immutable release inputs/products and exact reload; parent-plus-generation activation;
qualified occurrence/fact identity; release/realization composite references; source placement;
task attempts and reuse binding; native terminal/sealing guards; final-cut barriers; exact
batch receipts; grounded finite inference; atomic source/proof/result publication; immutable
completed replay; one PostgreSQL snapshot for Arrow/DuckDB; exact source numeric representations.
These are implemented mechanisms, not gaps created by this review.

The remaining opportunity is the **composition and authority of their definitions**:

| Area | Observed seam | Useful stronger capability |
|---|---|---|
| Conceptual relations | Core LinkML describes content; physical LinkML describes many persisted relationships, often through string fields and JSON-encoded SQL annotations (S1/S2) | One connected semantic definition of endpoint kinds, roles, cardinality, context, authorization and identity, with physical foreign keys as its realization |
| State | Status lists exist in physical checks; allowed behavior also lives in Python and several native revisions (S2/S5/S6) | Explicit composed state and allowed transitions that existing writers and readers consume |
| Outcomes | Source coverage includes unknown/unsupported; semantic coverage uses unanalysed. Envelope coverage currently forwards outcome strings across that boundary (S8/S13) | Owned typed outcome domains and a meaning-preserving translation, rather than accidental enum compatibility |
| Decision relations | Assessments/groups are retained; some comparison-counterpart detail is serialized inside reason text (S8) | Typed comparison subjects, counterpart, context, rule/version and uncertainty usable by current explanation |
| Execution inputs | Consolidation creates a candidate packet to obtain an AnalysisScope; a captured database packet has different provenance (S8/S12) | Distinct candidate-input and captured-snapshot contracts sharing the same engine lifetime |
| Constraints | The admitted compiler refuses native LinkML rules; upstream generators implement unequal subsets (S3/S10, §6) | Supported invariant declarations with an identified enforcing lowering and explicit rejection of unsupported required semantics |

These observations identify design opportunities. No live bypass or failing runtime journey
was attempted, and no inference is made about untested paths.

## 4. Selected architecture and alternatives

Select a unified model with **explicit semantic scopes**:

1. A trusted, code-versioned execution model owns run/task/cut/publication/resource lifecycle
   and privilege-sensitive invariants.
2. Each immutable semantic release owns domain classes, relations, qualification, vocabularies,
   scientific policy and analytical interpretation.
3. The release binding names the compatible execution-model revision and implementations it uses.
   Their composed contract is the model consumed by operations and projections.

These are coherent modules within one model, not competing writable definitions. An extracted
document or candidate domain release cannot redefine task ownership, transaction isolation or
publication privileges. Logical meaning is distinct from the fixed physical schema; candidate
domain definitions continue to populate registry data rather than create tables.

| Alternative | Judgment |
|---|---|
| Consolidate prose around the current code | Useful explanation, insufficient as the sole executable model |
| Depend entirely on native LinkML generators | Suitable for supported local constraints; cannot supply uniform generator coverage, scientific algorithms or PostgreSQL transaction semantics |
| Typed LinkML contracts plus owned functions/Core/native enforcement | **Selected:** connects definitions and execution, preserves existing mechanisms and extension locality |
| Coherent code-authoritative types/functions with LinkML structural models | A valid minimal realization where contracts are fully owned; enrich it with typed, linked contracts here because packets, release preparation and projections already consume the model and need discoverable shared meanings |
| General workflow/FSM/rule execution platform | No demonstrated benefit sufficient to justify a new runtime or second orchestration authority |
| RDF store as the new instance/transaction authority | Reject for this target: duplicates or replaces the existing protected instance authority without a supported functional need |

Ordinary functions remain authoritative for irreducible algorithms. Their executable contract
must resolve from the model to one owner, with typed inputs, applicability, outputs and effects;
a function-name annotation or duplicate prose specification is insufficient.

## 5. Recommended opportunities

<a id="O01"></a>
### O01 — One connected conceptual and relationship model

**Proposed; foundational.** Extend the logical LinkML modules to cover existing operational,
evidence, decision and projection concepts. Give relationships typed endpoints, semantic identity,
scope, roles, multiplicity and authorization. Generate or derive the mechanical boundary and
relational descriptors from these definitions; retain physical-only layout choices separately.

The implementer can add a qualified relation or source relationship in one semantic owner and
follow it through construction, persistence and current reads. The operator can distinguish
support, selection, lineage and derivation without interpreting storage conventions.
S1/S2/S9 show both the reusable foundation and the present separation.

Delivery is demonstrated by a new relation preserving its qualifications, repeated occurrences,
endpoint references and declared constraints across the existing publication/query journey.

<a id="O02"></a>
### O02 — Complete composed lifecycle and transition semantics

**Proposed; foundational with O01.** Define the finite state dimensions, valid combinations,
transition contracts and cross-object invariants in companion LinkML types. Trusted execution
definitions change with application releases; domain policy remains release-authored.
Do not add a giant state enum or dormant transitions solely because storage permits a string.

Keep source_ready as a response outcome, held as submission disposition, and completed-result
immutability as an explicit predicate/relationship. None becomes an interchangeable task/run
status. The existing native guards remain the starting realization. A complete allowed-edge
contract would additionally define nonterminal transitions and attempt/holder/lease requirements
that are not fully specified by the current prohibition guards (S5–S7).

This enables consistent scheduling, cancellation, retry and refusal across existing callers.
Delivery requires an illegal transition to refuse at the native write boundary and an ordinary
caller to receive the same typed reason, with current atomicity and replay preserved.

<a id="O03"></a>
### O03 — Executable invariant and operation contracts

**Proposed; depends on O01/O02.** Model each material operation's inputs, applicable context,
result/effect alternatives, invariant references and dependencies. Reuse LinkML metamodel
expressions for supported local constraints; use owned typed predicates and domain functions
for scientific, relational and transaction-sensitive behavior.

Preparation resolves every required definition and implementation reference. A required
invariant without an enforcing realization refuses admission. One owned predicate or lowering
supplies Python preflight and native SQL where both are needed; separately hand-maintained
Boolean approximations would recreate the problem. Existing SQLAlchemy/Core and protected native
routines remain the execution mechanisms.

The functional gain is meaningful extension: a new contract can be inspected and invoked without
reverse-engineering unrelated control flow. It does not require registering every utility
function or generating an application-wide operation interpreter.

<a id="O04"></a>
### O04 — Typed outcome, assessment and uncertainty relationships

**Proposed; depends on O01/O03.** Give task transport, submission disposition, source coverage,
semantic coverage, scientific decision, publication and query completeness distinct outcome
types. Define their translations and preserve originating codes/reasons.

Represent assessment subjects and comparison counterparts as typed references rather than
machine-significant reason text. Fact acceptance remains a contextual selection, not a mutation
of proposition identity. Source success never implies scientific acceptance; missing or
unsupported analysis never becomes absence.

The current operator and explanation consumer gain a stable answer to what completed and what
remains unknown. The companion specifies the coverage mapping and independent decision dimensions.

<a id="O05"></a>
### O05 — Model-derived projection and analytical contracts

**Proposed; depends on O01/O03/O04.** Define named projection contracts for occurrence, fact,
accepted knowledge, source reports, graph validation and analytical input/results. Each states
its universe, preserved identities/relations, collection semantics, precision and completeness.

Distinguish captured database packets from candidate-operation inputs, and append publication
from snapshot-dependent result publication. Bind the latter to mandatory source revisions.
Use the existing Arrow schemas, DuckDB scope and protected pgpq route; keep lazy handles scoped
and materialized results detachable.

This enables reusable analytical operations without implying that copied schema metadata proves
correct provenance or that every Arrow packet represents a database capture.

<a id="O06"></a>
### O06 — Rich relation validation with qualified graph projections

**Proposed; supporting O01/O03/O05.** Use SHACL Core/property paths and selected SHACL-SPARQL for
constraints that benefit from graph structure. Build the declared validation closure, including
required related nodes and before/after records where needed. Keep assertion occurrences,
qualification, source support and proof links explicit.

RDFLib remains the baseline graph interface; existing native RDFC canonicalization is retained.
Direct PySHACL/PyOxigraph validation is a qualified backend candidate, without an Oxrdflib
requirement. SHACL validates represented state; native PostgreSQL enforces concurrent transition
and publication authority. Avoid whole-corpus graph reconstruction for ordinary operations.

The operator gains reusable relational diagnostics. No new graph service, persistent second
authority or general OWL/Datalog execution is required.

<a id="O07"></a>
### O07 — Complete model admission, evolution and explanation

**Proposed; integrates O01–O06.** Admit the composed definitions, dependencies, projections and
supported enforcing capabilities as one compatible binding. Preserve exact archived inputs,
compiler identity and library versions. Logical policy changes produce new semantic releases;
trusted execution/physical changes use application revisions and new immutable Alembic migrations.

Current packet, query and explanation primitives should expose the relevant definition/operation,
binding and refusal references. Do not add a new general introspection service or pull unfinished
SP-08 journeys into scope. This enables an implementer to establish why an operation applied and
which model authorized its result.

## 6. Library selections and boundaries

The capability overviews supplied by the operator informed the inquiry. Concrete selections:

| Library and inspected baseline | Selected role and material limit |
|---|---|
| [LinkML/runtime 1.12.1](../libraries/linkml.md) | SchemaView, classes/slots/enums/keys and supported conditional expressions; typed companion contracts. Native language expressiveness does not establish parity between repository adapters and generators. |
| [valuesets 0.4.2](../libraries/valuesets.md) | Reusable semantic enumerations and ontology meanings; preserve explicit acquisition and frozen expansion. It is not a lifecycle engine. |
| [PySHACL 0.40.1](../libraries/pyshacl.md) | validate, Core/path/SPARQL constraints and structured reports over declared projections. SHACL rules are optional derived-graph behavior, not transaction updates. |
| [RDFLib 7.6.0](../libraries/rdflib.md) | Graph/Dataset/typed terms and generator interoperability. Set semantics require explicit occurrence/member records to preserve duplicates and order. |
| [PyOxigraph 0.5.13](../libraries/PyOxigraph.md) | Retain existing native canonicalization; direct validation/query backend is a candidate. Its store transaction does not cover PostgreSQL; decimal arithmetic has a bounded fixed-point envelope. |
| [Oxrdflib](../libraries/Oxrdflib.md) | Defer unless a concrete consumer requires RDFLib's store interface over Oxigraph. It adds an adapter and documented fallback/transaction limitations. |
| [linkml-map](../libraries/linkml-map.md) | Candidate for a concrete supported source/import/export mapping using TransformationSpecification/ObjectTransformer with strict behavior. Do not make completeness depend on it; SQLCompiler/DuckDBTransformer are not a complete lowering of the mapping language. |
| [linkml-datalog](../libraries/linkml-datalog.md) | Defer package adoption. Its inspected generator does not supply this application's exact qualified numeric, occurrence and proof contract. Existing finite qualified relational inference remains selected. |
| [SQLAlchemy 2.1.5](../libraries/sqlalchemy.md) | Shared MetaData, Core joins/constraints, guarded DML, RETURNING and locking. Domain definitions own meaning; no ORM or FSM replacement. |
| [psycopg 3.3.6](../libraries/psycopg.md), [pool 3.3.3](../libraries/psycopg-pool.md) | COPY and connection lending through the existing single pool/SQLAlchemy transaction owner. No independent driver commit owner. |
| [pglast 8.7](../libraries/pglast.md) | AST and dependency inspection for authored SQL; restricted PostgreSQL analysis still establishes catalog/type/access binding. Parsing does not prove semantic equivalence. |
| [pgpq 0.12.0](../libraries/pgpq.md) | Typed binary encoding into protected staging on the existing connection. Wire compatibility does not authorize domain publication. |
| [Alembic 1.20.0](../libraries/alembic.md) | New frozen deployment revisions from trusted model changes. Autogeneration alone does not establish behavioral guard equivalence. |
| [PyArrow 26.0.0](../libraries/pyarrow.md), [DuckDB 2.0.0](../libraries/duckdb_2.md) | Explicit typed relations, conversions and local set operations with owned reader/connection lifetimes. Preserve accepted decimal policy and snapshot semantics. |
| [Pydantic 2.14.1](../libraries/pydantic.md), [Settings 2.16.1](../libraries/pydantic-settings.md) | Strict boundary/result types and one entry-point configuration resolution. Local validation does not establish relational/concurrency authorization; settings cannot override semantic policy. |
| [rule-engine 5.1.0](../libraries/rule-engine.md) | Released typed scientific decision rules; reuse typed input definitions where compatible. It does not establish scientific equivalence, grounded proof or transaction lifecycle. |

### Consequential primary-source findings

Installed LinkML 1.12.1 ShaclGenerator recognizes only particular rule patterns: presence implies
a true Boolean flag, and an enum condition implies same-slot maximum cardinality. Other patterns
can be skipped; bidirectional/else semantics are not uniformly preserved. JsonSchemaGenerator has
broader if/then/else handling, but the repository builds its own adapters (S3). Therefore simply
allowing native rules or successfully generating SHACL would not close O03.
Sources: [conditional rules](https://linkml.io/linkml/schemas/advanced.html) and the inspected
installed 1.12.1 distribution: .venv/lib/python3.14/site-packages/linkml/generators/shaclgen.py
419–535 and jsonschemagen.py 582–622. The installed-version evidence, rather than a newer
upstream implementation, establishes the stated generator limitations.

PySHACL's direct PyOxigraph Store support is present at the pinned version; Oxrdflib is not
needed for it. It remains application-unqualified here. Sources:
[0.40.0 release](https://github.com/RDFLib/pySHACL/releases/tag/v0.40.0),
[0.40.1 abstraction](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/graph_abstraction.py).
Oxrdflib can fall back from parsed queries to RDFLib execution; successful execution alone
does not establish native placement. See [Oxrdflib limitations](https://github.com/oxigraph/oxrdflib).

PyOxigraph decimal execution is bounded by its fixed-point representation. Literal transport
does not establish equivalence to arbitrary scientific Decimal arithmetic or preservation of
original decimal spelling. Keep exact canonical/source lexical values and numerical execution
as separate contracts. See [pinned decimal implementation](https://github.com/oxigraph/oxigraph/blob/v0.5.13/lib/oxsdatatypes/src/decimal.rs).

linkml-map offers useful typed derivations, joins and strict transformation interfaces, but
its stable/current documentation and prerelease capabilities must not be mixed. No adoption pin
or Python 3.14 integration was established here. See
[mapping specifications](https://linkml.io/linkml-map/writing-specs/) and
[backend architecture and limits](https://linkml.io/linkml-map/#architecture).
The inspected linkml-datalog generator includes unconditional dereification and numeric
collapsing that do not satisfy this domain's qualifications/proofs; this is a package-fit
judgment, not a limitation of Datalog as a language. See
[generator](https://github.com/linkml/linkml-datalog/blob/main/linkml_datalog/generators/dataloggen.py).

## 7. Integration, priorities and decision impacts

O01/O02 establish the model; O03 makes it authoritative; O04/O05 complete its existing consumer
contracts; O06 supplies graph-oriented enforcement where useful; O07 integrates admission and
evolution. Implementing only a new schema file would not deliver the combined capability.

Use the existing compilers, functions, snapshot/batch mechanisms and privileged boundaries.
Compile stable definitions once; reuse immutable validity; hydrate narrow required relations;
keep direct provenance compact. Native placement is selected for semantics and workload fit,
not assumed to be faster. No benchmark campaign, alignment lint, cost model, transition event
ledger or new service is proposed.

| Proposed impact | Decision route if adopted |
|---|---|
| Complete logical/execution model composition and definition scopes | ADR-0024/0027 and D1/D2/D6; amend or supersede only where accepted meaning changes |
| Shared relationship/guard lowering and stricter allowed transitions | ADR-0025/0027 and D3/D5/D6; new native migration for changed enforcement |
| Typed analytical input/publication dependency distinctions | ADR-0026 and D3/D5; preserve decimal and snapshot guarantees |
| Richer internal graph validation/projection profile | D2/D3 and the governing semantic-release decision; no public RDF service implied |

These are proposals. The existing pivot plans retain their scope and dispositions. Their
amendment and any new implementation series require subsequent planning/adoption.

## 8. Demonstration scenarios and evidence limits

The target companion connects every modeled family to operations and enforcement. Useful
delivery scenarios are:

1. Add a qualified binary or n-ary relationship; preserve endpoint roles, context, repeated
   source occurrences, collection order and known-input references through publication/explanation.
2. Attempt an illegal nonterminal transition, stale claim or completion, concurrent seal/cancel,
   and duplicate submission; preserve current rejection and exact-replay distinctions.
3. Complete a task with a refused proposal; retain the report and failed/unknown semantic
   coverage without fabricating accepted facts or reporting transport failure.
4. Validate a supported local rule and a relational invariant; reject an unsupported required
   lowering instead of silently emitting weaker JSON Schema, SHACL or native enforcement.
5. Compare scientific candidates under incompatible context; preserve undecided assessment,
   source facts and alternatives. Derive only authorized finite conclusions with grounded proofs.
6. Round-trip declared graph/Arrow projections with qualified duplicate assertions, null/empty
   distinctions and decimal precision boundaries; preserve each projection's promised semantics.
7. Publish a snapshot-derived result after its input advances; return recompute-required.
   Replay a completed result after the same change; return its original receipt.
8. Close an analysis scope with outstanding lazy readers; distinguish detached materialized
   output from invalid borrowed handles and preserve bounded owned cleanup.

These are proposed delivery demonstrations, not new tests run by this review. Independent
expectations must challenge the model and its lowerings; regenerating expected answers from
the same declaration alone cannot establish semantic completeness.

The recommended model is complete with respect to the bounded transitioned responsibilities
specified in the companion. That is a **Proposed design**, not a claim of complete
implementation, formal proof, arbitrary ontology support or tested library compatibility.
