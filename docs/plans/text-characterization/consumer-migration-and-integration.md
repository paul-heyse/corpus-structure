# Consumer migration, native admission and ingest integration

**Proposed · 2026-11-10.** Owns TC-09 design; the
[coordinator](../text-characterization_2026-11-10.md) owns current state and O05/O06 disposition.
Consumes [model/retention](model-and-retention.md), [primary semantics](constructions-and-interpretation.md)
and [contextual layers](contextual-characterization.md). This is planned implementation, not code
already migrated. Existing plans are not inputs or prerequisites.

<a id="TC-09"></a>

## TC-09 · One primary meaning owner with complete consumer migration

The [review](../../functional_reviews/text-characterization_2026-11-10.md#O06) requires a replacement
across producers, consumers and native support. Current
[procedure roles](../../../python/corpus-structure/src/corpus_structure/methods/structural_roles.py)
construct roles/coordination/negation independently of general
[predicate frames](../../../python/corpus-structure/src/corpus_structure/methods/predicate_frames.py).
Native [source-contribution SQL](../../../python/corpus-structure/src/corpus_structure/semantic/sql/source_contributions.sql)
also reconstructs role inventories and reading layout. Preserve the purpose of source checks while
replacing repeated language-producing policy.

### Migration inventory and target behavior

| Owning surface | Required replacement and completion condition |
| --- | --- |
| Source preparation, sentence/annotation products and views | Produce/preserve the base document and positioned native layers; the combined view exposes exact hierarchy, items and source maps without per-consumer inference. |
| Named annotation rules, predicate/procedure frames and qualifier recipes | Rehome useful linguistic declarations under TC-05/06; replace private host, inheritance, polarity and role reconstruction with shared term/role/choice references. |
| HanLP native projection | Retain complete native evidence with its scheme; frame/cue interpretation belongs to the shared construction owner. |
| Definition declaration/applicability, assertion qualification and source capture | Consume naming/predication/function/role/scope outputs, then perform explicitly domain-owned interpretation. Do not repeat lexical/dependency recognition privately. |
| Mathematical/field syntax and binding consumers | Read positioned formal products and source operator context; scientific equivalence/truth and domain symbol resolution retain separate operations and prerequisites. |
| Structural contribution/comparison/dossier assembly | Use exact primary member/operand/role references; add conceptual relationships and groups to document views with distinct provenance. Partial parts remain independently useful. |
| Contextual query/retrieval and model replay | Consume retained mentions/referents/definition applicability and contextual layers. Retrieval ranking and conceptual link selection remain later operations. |
| Native admission and semantic release generation | Authenticate source, producer, layer, role and choice closure under the selected release; enforce declared invariants independently of semantic efficacy. |
| Reader, CLI, MCP, export and evaluation | Use the same pinned combined-view operations; preserve group membership, alternatives, source support, statuses and independent reference separation. |

Before execution, find all call sites of `predicate_frames`, `procedure_frames`, predicate qualifier
and cross-block helpers, `DefinitionBasisWitness`, annotation restoration and current math tree
codecs. This is an integration inventory inside TC-09, not an excuse to limit migration to a few
examples. Deliver necessary consumer slices alongside TC-02–08; close TC-09 only when every affected
current producer/read/admission path uses the new contracts.

### Native validation and independent correctness

Classify each existing SQL reconstruction check by its guarantee. Source pin, native address,
annotation origin, token/extent correspondence, endpoint membership, allowed role vocabulary,
choice dependencies and publication permissions remain native-enforced obligations. Mechanical
shape/invariant checks derive from executable declarations where suitable. Interpretation policies
that decide which predicate/participant/host the language supports belong to the shared primary
owner, not a second handwritten SQL NLP implementation.

Model-only host predictions remain private proposals until a separately declared support policy
qualifies their stronger use. A retained model reply proves what the model emitted. A source-aligned typed result proves where
its evidence is located. Neither proves linguistic correctness. Native admission must verify
retained witness premises and released deterministic support constraints for every claim of a
witnessed role/attachment. Authentic producer identity alone never substitutes for that check; do not
replace that obligation with trusting any arbitrary caller-supplied primary result. Only genuine
released producer outputs with authenticated dependencies qualify. Independent assessment challenges
the actual role/scope meaning rather than reproducing the producer as expected truth.

Reject an authentic producer result with correct source/extents but a wrong unsupported host, an
authentic source pin with invalid role extents, a role from another layer/revision, an
unsupported host attachment, a fabricated producer or a conflicting choice bundle. Valid isolated
parts survive refused siblings. New typed witnesses must preserve required semantic support; old
witnesses never authorize a newly enriched meaning just because source text matches.

### Ingest scheduling and analysis readiness

PDF capture first publishes the immutable base document. The ordinary pipeline can then schedule
the selected full characterization profile, coalescing identical source/model preparation and
retaining independently completed layers. Record capture readiness, per-family enrichment state
and composed-view completeness separately. A failed NLP family does not erase the captured document
or completed independent layers; it also cannot satisfy a stronger analytic dependency.

Provide a first-class enriched-document demand for later consumers. If the exact required layers
already exist, analytics reads them. If unavailable, the owning pipeline schedules the versioned
primary operation under its declared dependency; it does not execute a hidden parser inside a query.
Ingest and later demands share operations and retained results, not duplicate NLP implementations.
No change to PDF recognition is needed just to attach linguistic layers.

Keep model/CPU work outside publication transactions. Cancellation propagates through the actual
worker/reader borrower; settle partial/failure state and retain valid effects under existing task
fences. Use complete dependency identities for reuse. A scope-rule update regenerates semantic
layers and dependent analytics while retaining compatible capture/model work.

### Cutover and retirement

Use forward released contracts and current-only consumer cutover under
[ADR-0067](../../adr/0067-witnessed-current-only-cutover.md). Authenticated evidence may migrate only
when it supplies all new meanings. Otherwise regenerate obsolete derived closures from retained
source. Preserve original sources, plans and evidence; no database-wide reset or cross-project
mutation is implied. Retain old outputs as historical evidence without maintaining obsolete
semantic decoders or fallback interpretations in the production path.

Retire replaced recipe branches, private role walkers, mechanism-specific configuration, historical
semantic adapters and tests that only assert obsolete mechanics. Preserve independent reference
expectations, deliberately invalid inputs, provenance/source protection and actual required behavior.
Coordinate schema, producer payload, method version, native functions, readers and reference
applicability in the same coherent change; an agreed interface alone does not establish a usable
migration prerequisite.

**Acceptance:** one shared negation/condition construction feeds both definition and procedure
consumers; comparison and linking inspect the same retained scopes; a topic/group spanning pages
preserves membership through Reader/CLI/MCP/detached export. Source-only, partially enriched and full
views are distinguishable. Native invalid-extent/forged-origin/incompatible-choice controls refuse
without damaging valid siblings. Fresh and retained-source ingest reach equivalent supported view
meaning without repeating unchanged capture. Old private interpretation branches have no current
callers. Actual named scenarios, native deployment and full-profile qualification close under TC-11;
a passing pure function test does not establish admission or corpus quality.
