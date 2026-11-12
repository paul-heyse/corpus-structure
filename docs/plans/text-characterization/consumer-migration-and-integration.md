# Consumer migration, native admission and ingest integration

**Reopened by the 2026-11-12 completion audit: TC-09 is incomplete (TC-E08–E11).** The demand,
ingest, view-binding, native-guard and detached-closure parts are implemented and were Tested on
2026-11-11 source; the default `ci run` composition, three inventory rows and current-only
retirement are not delivered. [Open TC-09 obligations](#open-tc-09-obligations) holds the local
detail. Owns TC-09 design; the
[coordinator](../text-characterization_2026-11-10.md) owns current state and O05/O06 disposition.
Consumes [model/retention](model-and-retention.md), [primary semantics](constructions-and-interpretation.md)
and [contextual layers](contextual-characterization.md). The coordinator distinguishes implemented source, native deployment and qualification. Existing plans are not inputs or prerequisites.

<a id="TC-09"></a>

## TC-09 · One primary meaning owner with complete consumer migration

The [review](../../functional_reviews/text-characterization_2026-11-10.md#O06) requires a replacement
across producers, consumers and native support. At the 2026-11-10 authoring baseline,
[procedure roles](../../../python/corpus-structure/src/corpus_structure/methods/structural_roles.py)
constructed roles/coordination/negation independently of general
[predicate frames](../../../python/corpus-structure/src/corpus_structure/methods/predicate_frames.py).
Native [source-contribution SQL](../../../python/corpus-structure/src/corpus_structure/semantic/sql/source_contributions.sql)
also reconstructed role inventories and reading layout. The delivered cutover preserves source
and declared mechanical witness checks while replacing duplicated language-producing policy.

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

The implemented migration covered call sites of `predicate_frames`, `procedure_frames`, predicate qualifier
and cross-block helpers, `DefinitionBasisWitness`, annotation restoration and current math tree
codecs. Current producer/read/admission paths use shared primary products and mechanical native
support constraints. SQL NLP helpers and the superseded recognizers behind those call sites were
retired; the current contract inventory below names the delivered consumers. The migration did not
cover every inventory row.

<a id="open-tc-09-obligations"></a>

### Open TC-09 obligations · 2026-11-12 audit

The [coordinator](../text-characterization_2026-11-10.md#completion-audit) owns status and closure;
this table records which inventory rows and statements in this document are not yet true.

| Finding | Inventory row or statement here | What is still the case |
| --- | --- | --- |
| [TC-E08](../text-characterization_2026-11-10.md#TC-E08) | "The default analytical command graph also performs capture, primary demand and exact-view binding before consumers" | True for direct Python callers, `ci regenerate` and the M1 policy. The `ci run` CLI passes the phase-0 graph and registry, so the demand is skipped. Repair owned by BEP-E12. |
| [TC-E09](../text-characterization_2026-11-10.md#TC-E09) | HanLP native projection: "frame/cue interpretation belongs to the shared construction owner" | The private parser projector still authors predicate frames and qualifier cues from its own lexicons, and contribution composition, the retained declaration parser and source-contribution admission still read them. |
| [TC-E10](../text-characterization_2026-11-10.md#TC-E10) | Contextual query/retrieval and model replay: "consume retained mentions/referents/definition applicability and contextual layers" | Contextual query binds private parser frames, Maverick clusters and DiPO trees. It is absent from the migrated-contract list below. |
| [TC-E11](../text-characterization_2026-11-10.md#TC-E11) | Definition declaration/applicability and assertion qualification: "do not repeat lexical/dependency recognition privately" | Assertion qualification re-scans raw tokens for negation, modal tag and a dependency gate. The declaration chain walks raw HanLP dependency columns and awaits a domain-owned-or-migrate decision. |

Consequently the acceptance statement "Old private interpretation branches have no current
callers" is not yet met, and current-only retirement under ADR-0067 is open for these surfaces.

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
callers. The coordinator records the delivered named functional scenarios, native deployment and
applicable-provider union. Independent semantic assessment and full-book qualification remain
TC-10/11; a passing pure function test does not establish corpus quality.

## Implemented execution interfaces

**Implemented except the default `ci run` composition (TC-E08); bounded functional scope Tested on
2026-11-11 source.** Provider residency, release preparation, reuse compatibility and recovery
described here have since been replaced or extended under BEP (ADR-0083–0087); the coordinator's
audit records that layering. `ci run characterize --request FILE`
executes the typed `CharacterizationDemandRequest` from
[the demand owner](../../../python/corpus-structure/src/corpus_structure/orchestrate/characterization.py).
The request binds project, release, realization, domain, exact native base, original source scope
and completed source references. Optional selected layers retain complete dependency closure;
`active_layers` chooses the current analytical population. `run_missing: false` composes retained
inputs without inference. `fresh_methods` explicitly retries named primary producers through the
existing scheduler, preserving earlier partial results. No automatic retry loop is selected.

Ordinary source execution runs native/formal inputs, constructions, contextual evidence, model
characterization and one contextual evaluation in their real dependency order. Runtime and artifact
identities are frozen before task identity/reuse. Unchanged exact outputs are reused before a
pure contextual refresh selects original raw populations. Ingest's `--enrichment-options FILE`
uses these same operations after completing source capture, publishes natural-unit results and
composes one document view. The existing task/cut lifecycle remains the recovery boundary.

The default analytical command graph is accepted to perform capture, primary demand and exact-view
binding before consumers; the `ci run` CLI does not yet reach that route (TC-E08). It uses the selected custom domain registry throughout and moves effective
consumer named-rule declarations into primary construction; conflicting definitions refuse rather
than selecting a winner. Source-only execution and explicitly authored custom graphs retain their
declared boundaries. The analytical run's immutable options and reports retain exact view pins,
including on regeneration resume. Natural-unit preparation shares one scoped provider session.
Repeated capture of an unchanged exact SourceView retains an existing completed original source
binding, validated by the native source owner before inference; a new capture run alone therefore
does not invalidate every primary task. Explicit primary freshness reaches the same demand stages.
M1 consumer-specific named declarations are combined with the selected domain's primary producer
configuration, macros and binder policy, preserving both authorities.

Evaluation selects its upstream producers explicitly; a prior evaluation output cannot become
its own input on repeated demand. Selected empty/image-only views publish examined-empty language
coverage without loading providers. Formal eligibility is independent: unprojected retained formula
bytes remain available under native-item anchors, with unavailable mapping or recognition recorded
as partial/failed. A missing text population does not erase the document or manufacture a provider
failure. Canonical projection recipes remain enforced.

`ci run --characterization-view JSON` accepts repeated exact view-pin JSON objects. Consumer binding
freezes active pins and selects the views' original SourceView references from their immutable
producer dependency manifests. It skips capture/recognition, including across consumer releases;
text or projection equality never relabels source IDs. Settled views can be consumed while their
producer run remains unfinished when original source custody is complete. Source-only reads remain
separate. ADR-0082 owns selection versus dependency retention.

Current migrated contracts are scoped relations17/predicate6, artifact identity5, comparison6,
definition10, declaration2, clause3, math extraction/normalization10, symbol scope8 and native
source request5. The primary navigation owner supplies naming, headings, artifact cues and table
language; the formal owner supplies field syntax and lexical categories; math scope cues live in
primary constructions. Consumers add domain relationships or scientific interpretation over exact
references. Older derived semantic closures require regeneration; original source/report bytes
retain their archived contracts.

Comparison's existing 256-character and adjusted-exponent bounds apply to the downstream typed
projection; primary formal evidence retains larger finite values. Registered table weights are
authenticated using the registry's canonical decimal-string representation. These analytical bounds
and policies do not reparse the primary language or discard its exact facts.

The coordinator records the full-campaign/replacement functional union, including native admission
and actual-provider controls. This establishes the tested functional boundary, while independent
linguistic quality and full-book qualification remain TC-10/11. No activation, promotion or project
selection occurred.
