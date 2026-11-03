# M1 semantic contracts and field evidence

**Proposed design and Planned work · 2026-11-03.** This companion develops M1-02 and M1-03.
The [coordinator](../first-production-milestone_2026-11-03.md) owns package state, dependencies,
opportunity disposition and assembled completion. This document defines the local target and
completion conditions; it is not a second progress ledger. Plan authoring authorizes no product
changes or deployment.

## Basis and foundation assessment

Consume the [M1 proposal](../../target-pipeline-design/first-production-milestone.md),
[functional review O03/O07](../../functional_reviews/m1-target-design_2026-11-03.md#O03), and
[GLiNER deployment contract](../../target-pipeline-design/gliner-deployment.md). The inspected
source baseline is `4a929aba`, with the operator-owned GLiNER reference at blob
`3daefdd5af8a3118f4767d9a558da4bc712cbacd` left unchanged. Initially dirty, those same bytes were
committed externally as `4720b9a7` during authoring. The operator's 2026-11-03 direction
establishes that prior UM functionality implementation and validation are complete; its remaining
agent assessment/followup stays with that owner and is not an M1 functional prerequisite.
M1's new contracts and consumers still require their own implementation and qualification.

The [assembly/interpretation companion](record-assembly-and-bounded-interpretation.md) consumes
these contracts; [publication/consumers](publication-and-consumer-adoption.md) migrates their served
forms, and [evaluation](evaluation-qualification-and-gap-driven-expansion.md) supplies independent
faithful-reading expectations. These packages share the model's meanings without taking over
each other's operations or completion claims.

[D1](../../design/D1-knowledge-representation.md), [D2](../../design/D2-schema-and-guidelines.md),
[D3](../../design/D3-database.md) and [D5](../../design/D5-consolidation-identity-confidence.md)
remain the semantic, release, persistence and publication owners. Their applicable decisions,
including ADR-0024/0027/0047, govern extension. M1-00 resolves authority changes before dependent
effects; this companion does not amend accepted decisions by implication.

The useful existing spine is concrete:

| Existing producer/consumer | Reuse and required M1 extension |
| --- | --- |
| [observations.yaml](../../../python/corpus-structure/src/corpus_structure/model/semantic/observations.yaml), `SourceObservationBatch`, `SourceObservation`, `SourceCoverage` | Immutable producer-bound source reports, linked inputs, terminal outcomes and measurements. A single location per observation is insufficient for field-to-many-anchor evidence and does not define a qualified whole record. |
| [observations.py](../../../python/corpus-structure/src/corpus_structure/semantic/observations.py), `bind_result` | Release validation and deterministic report identities already exclude task/attempt IDs. Extend this boundary rather than bypassing it with an untyped JSON store. Preserve native-versus-rendition coordinate exclusion. |
| [publication.py](../../../python/corpus-structure/src/corpus_structure/semantic/publication.py), `OccurrenceRow`, `OccurrenceEvidenceRow`, `OccurrenceEvidenceRoleRow`, `PublicationBatch` | Reuse many-to-many occurrence evidence and role relations. Add the missing released field/set/grouping semantics and native projections; a role string alone does not enforce a field contract. |
| [domain_operations.py](../../../python/corpus-structure/src/corpus_structure/semantic/domain_operations.py), `consolidate_cut` | Existing domain policy, cut binding and atomic publication remain the only admission route. Candidate interpretation prepares records privately and supplies a declared publication product. |
| [execution-model.yaml](../../../python/corpus-structure/src/corpus_structure/model/semantic/execution-model.yaml), release preparation and generated boundaries | Extend the effective model and its invariant/operation/projection bindings coherently; do not add independently editable family schemas or a parallel validation engine. |

The foundation change is a versioned representation of complete record occurrences with
field-addressable evidence and honest outcome meanings. It is warranted because the consumer
must distinguish a measurement's value evidence from its header, unit and condition, and because
one record may lower to several qualified assertions. Existing many-to-many evidence is retained;
its current existence does not establish those new meanings. A separate family database or one
opaque passage-cited JSON payload would duplicate custody or leave the consumer to guess.

## M1-02: released record, field and outcome model

**Proposed.** Consume M1-00's authority decisions and M1-01's family guidelines, supported subsets
and population identities. Settle the shared contracts early enough for preparation, extraction,
assemblers, interpretation and evaluation to design against them. Working integration requires
the admitted new release and its generated/enforced products, not only agreement on names.

The release owns family identifiers, role definitions, applicability, requiredness, literal versus
classified value kinds, allowed normalization/derivation, occurrence recipe, operation results,
and field/completeness invariants. Statistics supplies initial meanings; engineering examples
challenge reusable contracts without releasing a second domain. These are domain responsibilities,
not instructions to create a class, service or table for every concept.

| Product | Required content and consumer |
| --- | --- |
| Qualified record occurrence | Family, source occurrence identity, released role values/states, coherent interpretation identity, acceptance standing and policy version; assemblers produce candidates, interpretation resolves, publication admits, D8 serves. |
| Field value | Original source spelling where literal, typed original/classified/normalized/derived value, state, evidence set references, alternatives and lineage; numeric values preserve the existing exact decimal/scientific policy. |
| Interpretation result | Inspected decisions/candidate domains, coherent alternatives, dependency groups, feasibility, search/truncation/exactness scope, terminal reason and policy/calibration standing; raw model score is not acceptance confidence. |
| Routing disposition | Source/family applicability, requested/selected pack and operational scheduling/terminal outcome, including not-run and unsupported reasons; it cannot claim actual inspection. |
| Observation coverage | Scope actually inspected by a completed invocation, with complete/partial/unknown/unsupported/failed distinctions under the released contract; complete-empty remains meaningful without a record. |
| Gap | Source-grounded missing role or omitted region, failure stage/reason, available candidate evidence and bounded next action; a gap is neither a fabricated field value nor proof of source absence. |

Field states are `present`, `unstated`, `inapplicable`, and `unresolved`. `Unresolved` retains a
reason and available alternatives; absence of a decoder candidate alone cannot establish
`unstated`. Applicability and faithful-reading rules come from the family guideline. Failure,
cancelled, unsupported operation, infeasible search and not-run are operation/routing meanings,
not replacement field states. A required meaning-changing unresolved role prevents full-record
acceptance. Optional content can remain unstated. Required decoder cardinality cannot supply
missing evidence. Release invariants also reject a present literal field with a fictitious exact
span, a normalized value without its original/policy, and a derived value without premises/rule.

Keep scientific truth, source-reading confidence, author modality, source reliability and corpus
support distinct. A source says “may increase” even when the reading is highly certain. A derived
unit conversion cites its numeric policy, exact operands and conversion rule; a probability score
cannot substitute for that derivation. Model-calibrated standing requires the evaluator's held-out
evidence and version, and may remain provisional when fitting data are insufficient.

Identity follows the operation being represented:

- A record occurrence binds family, selected source/product/projection pin, native occurrence or
  anchor membership, and the released occurrence recipe. Equal strings at two positions remain
  distinct. Native learned slots and array indices are temporary diagnostics.
- A candidate distinguishes operation/input/schema/window/alternative under that source identity.
  Repeated windows remain separate observations before reconciliation, with common upstream groups.
- A normalized fact follows existing qualified semantic equivalence; grouping cannot erase
  condition, role, provenance or separate source occurrences. One record's several facts retain
  an explicit common record membership rather than reconstructing it from adjacent fact rows.
- A retry has its own attempt receipt but the same logical invocation/observation identities
  when its effective inputs are unchanged. Changed input, schema or policy creates the appropriate
  new computation identity rather than overwriting immutable reports.

Implement through the existing LinkML declarations and prepared Pydantic boundary adapters,
then operation/invariant/projection bindings. [D2 release preparation](../../design/D2-schema-and-guidelines.md#semantic-release-preparation-entry-point)
and [review O03](../../functional_reviews/m1-target-design_2026-11-03.md#O03) provide the concrete
mechanism. Family schema shape derives from those definitions; authored extraction descriptions
remain versioned policy under the same owner. Unknown required constructs refuse instead of
being silently omitted. Freeze predecessor observations; do not relabel old single anchors as
new multi-anchor records or require historical backfill to activate M1.

### Completion conditions for M1-02

The new release prepares, validates, archives, opens and admits the M1 contract products under
their actual supported routes. All immediate producers/consumers use the same field and outcome
definitions. Focused tests cover state/requiredness combinations, deterministic identity under
retry, equal text at different occurrences, exact numeric preservation, unsupported declarations,
and serialization/archive round trips with independent expected cases. These are new M1 tests,
not requalification of prior UM scope. Query/export/evaluator adoption remains in the coordinator's
consumer packages; M1-02 exposes their required typed contracts without claiming assembled release.

## M1-03: field evidence, observation binding and native lowering

**Proposed.** Consume M1-02's admitted contracts. Extend the source-report/binding and publication
spine as one change, including projections readers use. Context design may proceed against settled
anchor meaning while working mapping integration waits for this implemented contract.

An evidence set names its record field/role and contains ordered or explicitly unordered located
pieces as the role requires. Each piece retains selected source pin, source-view/product identity,
native item/cell/formula pointer, coordinate space and interval where available, mapping precision,
and the original source piece. Named sets allow a field to cite a cell plus header path and note,
or a discontinuous term and declaration. Consulted context is a computation dependency, not
automatically evidence establishing every field. Dependencies include counterevidence and rejected
alternatives whose removal could change acceptance.

Use explicit coordinate kinds rather than guessing from numeric pairs: selected-view projection,
recognized text, original source/native location, and model-context offsets stay distinct. Exact
text reconstruction is checked only for literal spans in the declared source space. An item-level
anchor remains coarse; it never becomes an exact character span merely because the model supplied
offsets in serialized input. A multi-piece match crossing synthetic text either resolves to its
separate genuine source pieces under the field's contract or remains unresolved/refused. No
synthetic separator or appended punctuation obtains a source locator.

The extension to `bind_result` accepts source-bound family candidates plus these evidence sets,
provenance/diagnostics and actual inspected scope, validates them through the prepared release,
and preserves immutable raw reports. Native payload alternatives remain inspectable even when
publication rejects them. Provenance includes operation/package/checkpoint/tokenizer identities,
effective schema/configuration/context/normalization, ontology/calibration versions actually
consumed, window identity and dependency groups, feasibility/violations and available suppression
or candidate limits. Missing library diagnostics are marked unavailable; no complete lattice is
invented. Runtime measurements retain their metric identity/units and source-bound producer.

Native lowering uses existing occurrence evidence/role and support relations where their meanings
fit, adding released field/evidence-set membership and record-to-assertion membership where absent.
It preserves many-to-many links rather than copying full passages per field. The release owns
invariants such as matching source pins, legal coordinate ranges, unique set membership, role
applicability and literal reconstruction. Enforce them at boundary/native admission according to
the declared placement; unsupported enforcement refuses activation. Validators are shared by
producer/publication consumers, while semantic expectations in tests remain independently authored.

For “Group A: mean 12, SD 3; Group B: mean 10, SD 2,” distinct numeric occurrences identify four
value candidates and two coherent measurement groups. A common population note can support both;
one observed value occurrence is not reused across exclusive same-role instances. A classified
`mean`/`dispersion` role keeps its model association and independently located source cue. GLiNER
enum offsets pointing at the record anchor or `(0,0)` do not locate the enum's literal label.
When no cue is available the classified result and unavailable evidence remain explicit; a family
requiring located role evidence cannot accept it by pretending the label was extracted.

Publication still enters `consolidate_cut` with private prepared records and rechecks the
source/release/policy premises at atomic publication. There is no family-specific write bypass.
Keep observation inspected-empty distinct from no accepted record: the latter may reflect
infeasible interpretation, a missing qualifier or publication conflict. A changed table note or
withdrawn rejected alternative invalidates affected interpretations even when winning value
evidence is unchanged. Preserve earlier accepted cuts and record the new computation.

### Completion conditions for M1-03

Focused implementation checks extend the relevant observation/publication/native-context tests
under `python/corpus-structure/tests/semantic/`. Exercise a table record with full parent/child
headers, native cell and inherited note; two repeated strings; a discontinuous definition; formula
and declaration in separate coordinate spaces; classified enum with misleading offsets; coarse
recognition; synthetic-span refusal; changed countercandidate; stale source pin; and replay of a
completed invocation. Assert independent source positions and field memberships, not output
reconstructed by the same mapper under test. Publication failure must leave observations retained
and no partially selected record.

The consumer packages must later retrieve/export the same set IDs, precision, field states and
record grouping through CLI/MCP/query/evaluation. M1-03 is complete only when its storage/binding
and reader contracts function coherently; final operator journeys and per-family release gates
remain assembled obligations at the coordinator. Local model execution is not required to test
the mapper's deterministic semantics, but fabricated candidates cannot qualify GLiNER inference.

## Boundaries and decisions left to execution

No new semantic store, evidence service, generic validator registry or historical migration is
selected. Local class/table names and whether compact field data share an existing value object
are implementation choices. The consequential unresolved placement question is which existing
occurrence/role projections can express field-set and record membership without losing precision.
During M1-02/03, inspect their effective model and native constraints and demonstrate the table
round trip. Reuse if faithful; extend the owned model/projections if not. Do not accept opaque
payload-only persistence that strands query/export/evaluator consumers.

All verification above is **Planned**. For this plan-writing contribution, product tests, database
operations, provider inference and qualification are **not_run**. Package states and any future
evidence receipts belong only to the coordinator.
