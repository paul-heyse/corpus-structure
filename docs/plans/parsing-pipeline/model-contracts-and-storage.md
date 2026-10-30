# Parsing model, contracts and storage

**Status:** Execution in progress; the coordinator owns package completion and receipts.
**Created:** 2026-10-30.
[Coordinator](../parsing-pipeline_2026-10-30.md) owns PP-00/01/04 state and review O01/O02/O03/O06 disposition.
Consumes the [target](../../functional_reviews/parsing-pipeline_2026-10-30_target-model.md),
review revision `b3a8313` and current semantic compiler/native foundations.

## Foundation assessment and resulting design

`semantic/metadata.py` already compiles trusted physical LinkML through SchemaView to shared,
fixed Core Table objects. `semantic/contracts.py` provides OperationContract, endpoint and
RelationshipDefinition semantics. `analysis_contracts.py` has immutable prepared contexts,
dependency-aware demands and finite recipe support; `semantic/operations.py` already binds
source results to fenced attempts and selects producing builds. These are the integration points.

Extend their domain coverage. Do not author independent Pydantic/ORM graph meanings, interpret
arbitrary workflows from rows, or require database access inside pure token processing. Full
source partition and graph constraints need enforcement consumers, not merely a schema describing
their shape. Keep content identity separate from parser provenance: canonical text, complete
segments/sentences and macros determine the rendition; mapping products belong to a build.

<a id="PP-00"></a>
## PP-00 — Decisions and architectural owners

**Owner:** architecture/model integration. **Input:** coordinator's confirmed PP-RC01/02 and
html5lib envelope. **Output:** current architectural clauses supporting the new capabilities.

Trace D1's canonical-coordinate wording, D2 compilation, D3 storage, D4 method promises, D5
binding, D6 operation lifecycle and D7/D8 evidence journeys to their accepted decision successors.
Retain existing identities and grading isolation. Adopt representation-qualified coordinates and
versioned method/output changes through the existing ADR route where clauses change; do not edit
accepted ADRs or assume superseded ADR-0012/0019 are still the decision owner.

Update enduring owners alongside the relevant decision during execution, before consumers depend
on changed meanings. Additional rule impacts return for explicit confirmation. Pure additions
within accepted contracts do not require ceremonial decisions. **Completion:** required clause
changes have one owner and accepted route; unsupported changes remain explicit dependencies.

<a id="PP-01"></a>
## PP-01 — Connected domain contracts and prepared ports

**Owner:** semantic model/compiler plus parsing operation owners. **Inputs:** relevant PP-00
decisions, review mechanisms and concrete native constraints. **Supplies:** shared agreed contract
slice for PP-02, then enforced model-derived runtime/native definitions for producers/readers.

PP-01 owns pure contract compilation, runtime boundaries and emitted native requirements;
PP-04 owns their physical deployment. Native enforcement acceptance waits for PP-04, but does
not block completing the agreed/pure contract slice that PP-02/04 need. Do not create a circular
prerequisite by requiring deployed instance tables before defining their contracts.

Model source artifact, representation, component occurrence, structural node, relationship
occurrence/endpoints, transformation mapping, interpretation, assessment and product/build bindings.
Use existing endpoint roles, ordering, multiplicity and unresolved references. Coordinate values
always identify representation, unit and half-open range; raw bytes and decoded/canonical code
points cannot be substituted. Preserve original bytes on decoding failure. Distinguish a complete
partition from partial recognition and from complete provenance.

The partition covers its declared representation once, without gaps/overlap, retaining unknown
material and whitespace. Structural/semantic spans may overlap above it. A transformation names
ordered source/target extent sets and operation/reason, permitting many-to-many, reordered,
excluded and synthetic output. Macro origins include invocation, argument, definition/default
and fallback authority across artifacts; a normalized spelling cannot establish that origin.

Define discrete decomposition, HTML interpretation, canonical projection, text preparation,
math interpretation/assessment and source publication operations. Each owns applicability,
required universe, typed inputs/results, effects, dependencies and failure/coverage semantics.
Adapter support includes frontend/grammar revision, coordinate fidelity, repair/ambiguity policy
and lifetime. Co-design ports around qualified native products; do not flatten every tree into
an untyped dictionary or freeze exact signatures before PP-02's evidence is available.

Separate computation lifecycle from semantic outcome and completeness. Not-requested/pending/
running/available/failed/cancelled are not grammatical OK/ambiguous/invalid/unsupported/unknown.
Timeout is attempt-dependent; an unevaluated Integral is an available mathematical representation.
Reuse existing transition/effect machinery only where durable lifecycle is actually required.

### Concrete mechanisms and enforcement

- Use LinkML `SchemaView.class_induced_slots()`/`induced_slot()` for effective inherited definitions;
  extend the current compiler and finite implementation admission. Unsupported required recipes
  refuse before effects, with authored location and remedy. Library algorithms stay ordinary code.
- Derive Pydantic discriminated variants (`Literal` tags, `Field(discriminator=...)`) and reused
  `TypeAdapter`s from compiled contracts. Existing recursive Segment models remain useful tree
  boundaries; shared/cyclic structures use explicit IDs/edges. `frozen=True` is not deep
  immutability, and `model_copy(update=...)` is not validated construction.
- Generate the declared JSON Schema dialect, call its validator's `check_schema` during trusted
  preparation, reuse validators and a pinned local `referencing.Registry`, and retain
  `iter_errors` instance/schema locations. Format validation is explicit; unknown formats do
  not establish additional properties. Cross-record existence is a native relational obligation.
- Keep validation violations separate from validator/runtime failure and unassessed coverage.
  A schema engine exception is not evidence that the source is invalid, and a skipped check is
  not a valid or absent result. Preserve authored/instance locations and an actionable reason.
- Derive RDF/SHACL views where selected consumers require them. Model occurrence nodes because
  triples alone lose repeated assertions. Validate the intended Graph/snapshot, avoiding Dataset
  union surprises. Keep current ontology conformance (`inference='none'`, advanced/imports/
  mutation disabled). Any rules/inference is separately admitted derived work, not silently
  enabled validation. Focused shape execution does not find all change-affected nodes for free.

Sources: local [LinkML](../../libraries/linkml.md), [Pydantic](../../libraries/pydantic.md),
[JSON Schema](../../libraries/jsonschema.md), [RDFLib](../../libraries/rdflib.md),
[pySHACL](../../libraries/pyshacl.md); review's version/source table applies. Standard `gen-sqla`
or SQLStore is not a replacement for this repository's PostgreSQL admission/migration protocol.

**Acceptance:** independent source-defined examples reject swapped coordinate spaces, missing
endpoint custody, duplicate occurrence identities, illegal order/containment and partial-as-complete
results. Adding a supported category or convention flows through its declaration, adapter support,
runtime producer and consumer. Agreement between generated validators alone proves no semantics.

<a id="PP-04"></a>
## PP-04 — Durable representation and source readers

**Owner:** physical model, storage/query integration. **Inputs:** PP-01 contracts and PP-02's
selected origin/mapping requirements. **Supplies:** enforced persistent products and bounded reads
for PP-07/09; producer integration can use pure contract slices before deployment.

Before DDL, fix the layout against three concrete queries: inspect a representation's categorized
components by extent/category; trace canonical output to original input and transformation basis;
retrieve typed ordered occurrence edges for structural/binding analysis. Compare compact typed
partition sequences with normalized component rows using locality, native integrity and actual
join needs. Record the chosen layout and why; no mandatory per-character rows, dense mapping
matrix or task per token. Stable semantic IDs and typed range/edge readers are required either way.

Use fixed release-scoped contract rows for supported variation. Add instance tables only where
the new product/endpoint/query responsibility requires them. Generate Core metadata from the
physical LinkML companion, add frozen forward native migrations and preserve immutable older
revisions. Bulk products enter through existing restricted publication, not ad hoc ORM sessions.

Implement shared `Table`/`select`, joins, `exists`, set-based `insert().from_select`/DML and
`returning` where useful. A recursive `.cte(recursive=True)` has explicit relation universe and
cycle termination; not every source relation is containment. ORM association objects/view-only
relationships are conditional on actual navigation benefit; they cannot bypass native authority.
See [SQLAlchemy](../../libraries/sqlalchemy.md) and its cited Core selectable/DML references.

Store product identity and producing build separately from content-identical renditions. Preserve
source custody, release/recipe/dependency bindings, coverage, immutable original artifact references
and exact value/range types. Keep raw partition, canonical partition and transformation coverage
independent. Typed payload storage does not excuse hiding cross-record references used by joins.

Implement bounded readers accepting pinned run/build selection. Reuse existing `text_layouts`
producing-task and `reused_task_id` resolution; ambiguous multiple builds refuse rather than
selecting latest. Missing products can expose declared reconstruction/unavailable support;
matching corrupt products must refuse, not quietly rebuild them as valid history.

**Acceptance:** actual restricted database writes/reads preserve occurrence multiplicity, extent
units, exact/synthetic mappings and separate builds sharing one rendition. Invalid foreign keys,
undeclared or out-of-scope cross-build references, mutation and incorrect completeness fail at
the correct boundary. Explicitly pinned macro-definition/default/fallback dependency artifacts
may originate in other builds; admit them through named dependency and endpoint custody rather
than rejecting all cross-build relationships. Pure decoder
tests cannot replace native/publication checks. PP-09 owns atomic publication/replay, not a
second copy of its state machine here. PP-10 owns final adopted-consumer qualification.

### Selected realization — 2026-10-30

**Implemented foundation; integration qualification in progress.** Original artifacts use
content-addressed `kb.source_artifact` bytea custody, retained during document registration rather
than waiting for successful interpretation. Parsing products bind to `ops.rendition_build.task_id`;
canonical rendition identity remains separate. Fixed representation, component, node,
relationship/endpoint and mapping/endpoint tables expose references used by joins. Bulk native
publication inserts a whole product inside the existing source transaction. The immutable encoded
manifest is retained alongside those projections and checked on read.

Normalized component rows were selected over opaque compact sequences because extent/category
inspection, endpoint integrity and ordered mapping joins are required consumers. One row represents
a meaningful component or contribution extent, never a character by policy; native buffers and
merged runs stay inside adapters. PostgreSQL primary keys and foreign keys preserve occurrence
identity and named dependency custody; source products sharing one canonical rendition remain
separate builds. The manifest provides bounded whole-product transport, while typed query ports
serve targeted access. This choice adds rows and index work; no throughput or storage saving is
claimed.

Complete partition, recognition and original-to-canonical provenance remain independent. An exact
local copy does not prove source origin, and canonical self-copy cannot close provenance coverage.
The initial finite transformation support refuses nonempty complete-provenance claims until the
decoder and projection mechanisms are qualified. PP-03 supplies those mechanisms; the full target
is retained rather than weakened by an availability label.
