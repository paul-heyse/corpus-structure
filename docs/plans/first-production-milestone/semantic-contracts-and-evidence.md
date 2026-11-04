# M1 semantic contracts and field evidence

**Target: Proposed; mixed implementation maturity · reconciled 2026-11-04.** This companion
owns the detailed design and completion conditions for M1-02/03. The
[coordinator](../first-production-milestone_2026-11-03.md) owns current package state,
dependencies, findings and assembled acceptance. Foundation notes retain their stated source
and receipt context; the coordinator owns the current integrated implementation and selected
verification. Remaining targets below are not blanket claims that every listed capability is
unimplemented. Whole-M1 qualification remains open.

**Execution baseline, 2026-11-04:** selected AC acceptance remains bounded to71a78774/native105.
Subsequent M1 native125, actual CPU publication/reuse/recovery, independent source-only references
and candidate consumer results have their own receipts in the coordinator. Actual development
quality fails and no fitted acceptance policy exists. Preserve those separate implementation,
functional and quality boundaries; no whole M1 package is complete.

## Basis and foundation assessment

Consume the [M1 proposal](../../target-pipeline-design/first-production-milestone.md),
[functional review O03/O07](../../functional_reviews/m1-target-design_2026-11-03.md#O03), and
[GLiNER deployment contract](../../target-pipeline-design/gliner-deployment.md). The original
review inputs remain those recorded by the coordinator. The current foundation is the
[amended AC target](../audit-closure_2026-11-03.md#13-adopted-targeted-amendments-and-next-execution):
semantic compiler16, immutable readers14–16, execution24 and RuleValue ABI2, with frozen native105.
Selected AC14 acceptance and AC-CA01–09 closure are complete under coordinator §15. Prior UM functionality/validation is
complete under the operator's ruling; M1 does not reopen it.

The [assembly/interpretation companion](record-assembly-and-bounded-interpretation.md) consumes
these contracts; [publication/consumers](publication-and-consumer-adoption.md) migrates their served
forms, and [evaluation](evaluation-qualification-and-gap-driven-expansion.md) supplies independent
faithful-reading expectations. These packages share the model's meanings without taking over
each other's operations or completion claims.

[D1](../../design/D1-knowledge-representation.md), [D2](../../design/D2-schema-and-guidelines.md),
[D3](../../design/D3-database.md) and [D5](../../design/D5-consolidation-identity-confidence.md)
remain the semantic, release, persistence and publication owners. Their applicable decisions,
including ADR-0024/0027/0047 and AC contract decision ADR-0054, govern extension. M1-00 resolves authority changes before dependent
effects; this companion does not amend accepted decisions by implication.

The useful existing spine is concrete:

| Existing producer/consumer | Reuse and required M1 extension |
| --- | --- |
| [observations.yaml](../../../python/corpus-structure/src/corpus_structure/model/semantic/observations.yaml), `SourceObservationBatch`, `SourceObservation`, `SourceCoverage` | Immutable producer-bound reports, typed record candidates, field evidence and coverage exist. Finish actual attributed producer/accepted-publication integration; do not replace them with a single passage citation. |
| [observations.py](../../../python/corpus-structure/src/corpus_structure/semantic/observations.py), `bind_result` | Release validation and deterministic report identities already exclude task/attempt IDs. Extend this boundary rather than bypassing it with an untyped JSON store. Preserve native-versus-rendition coordinate exclusion. |
| [publication.py](../../../python/corpus-structure/src/corpus_structure/semantic/publication.py), `OccurrenceRow`, `OccurrenceEvidenceRow`, `OccurrenceEvidenceRoleRow`, `PublicationBatch` | Reuse occurrence evidence plus the existing finite `record_projection.py` relations for fields, anchors, evidence sets, dependencies, admission and assertions. Finish accepted lowering under the released policy; a candidate projection is not accepted knowledge. |
| [domain_operations.py](../../../python/corpus-structure/src/corpus_structure/semantic/domain_operations.py), `consolidate_cut` | Existing domain policy, cut binding and atomic publication remain the only admission route. Candidate interpretation prepares records privately and supplies a declared publication product. |
| [execution-model.yaml](../../../python/corpus-structure/src/corpus_structure/model/semantic/execution-model.yaml), release preparation and generated boundaries | Extend the effective model and its invariant/operation/projection bindings coherently; do not add independently editable family schemas or a parallel validation engine. |

The versioned record declarations, `record_contracts.bind_record_candidates`, and private/native
custody already represent complete candidate occurrences with field-addressable evidence. The
remaining change carries these meanings through evaluated acceptance and actual producer/publication
journeys, preserving AC attribute-specific support and machine-readable operation reasons. It is warranted because the consumer
must distinguish a measurement's value evidence from its header, unit and condition, and because
one record may lower to several qualified assertions. Existing many-to-many evidence is retained;
candidate storage alone does not establish evaluated acceptance of those meanings. A separate family database or one
opaque passage-cited JSON payload would duplicate custody or leave the consumer to guess.

## M1-02: released record, field and outcome model


**Accepted amendment,2026-11-04 (ADR-0058).** Native table/cell custody supplies structural row
location. The statistics contract uses meaning-changing `row_label` without requiring a quoted
label to be present; explicit source absence/inapplicability can be represented, unknown still
blocks acceptance. Missing parser header flags are not source absence. No copied whole-row
literal, fabricated row pointer or redundant persisted extent scalar is introduced. The generic
projection ABI2 and table+cell occurrence recipe remain; new releases/references carry the role
change without rebinding old records or calibrated membership. Current execution is owned by
coordinator M1-INT-F15.

**Remaining target.** Reuse implemented declarations and bound products; consume M1-00's authority decisions and M1-01's family guidelines, supported subsets
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

Extend the implemented LinkML record declarations, `record_contracts.py` identities/validation,
`record_projection.py` and prepared Pydantic adapters and their operation/invariant/projection bindings rather than rebuilding these boundaries. [D2 release preparation](../../design/D2-schema-and-guidelines.md#semantic-release-preparation-entry-point)
and [review O03](../../functional_reviews/m1-target-design_2026-11-03.md#O03) provide the concrete
mechanism. Family schema shape derives from those definitions; authored extraction descriptions
remain versioned policy under the same owner. Unknown required constructs refuse instead of
being silently omitted. Freeze predecessor observations; do not relabel old single anchors as
new multi-anchor records or require historical backfill to activate M1.

Operational vocabularies such as reference splits come from the exact bound execution product
(`ExecutionModelProducts.reference_splits`), independently of domain extraction classes. Domain
roles/subsets come from the producing semantic release. A domain collision must not override an
operational subset. I01 of the adopted AC improvement review requires nondefault and historical
consumer cases, not another registry. Keep RuleValue ABI2 as the shared rule projection: a record
adapter must not reconstruct a partial rule view or equate a shape-valid value with supported evidence.

### Completion conditions for M1-02

The new release prepares, validates, archives, opens and admits the M1 contract products under
their actual supported routes. All immediate producers/consumers use the same field and outcome
definitions. Focused tests cover state/requiredness combinations, deterministic identity under
retry, equal text at different occurrences, exact numeric preservation, unsupported declarations,
and serialization/archive round trips with independent expected cases. These are new M1 tests,
not requalification of prior UM scope. Query/export/evaluator adoption remains in the coordinator's
consumer packages; M1-02 exposes their required typed contracts without claiming assembled release.

## M1-03: field evidence, observation binding and native lowering

**Remaining target.** Consume M1-02's implemented admitted contracts. Reuse the current
source-report binding, authenticated coordinates and finite publication projection as one spine;
finish the attributed producer and evaluated accepted-assertion route with its reader/evaluator consumers. Context design may proceed against settled
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

The existing `bind_result` / `bind_record_candidates` path accepts source-bound family candidates
with these evidence sets. Complete the producers using that path: retain provenance/diagnostics
and actual inspected scope, validate them through the prepared release and preserve immutable
raw reports. Native payload alternatives remain inspectable even when
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

AC source assertions are attribute-specific: support for a numeric value cannot establish its
unit, role, condition or a different field. Structural assignments and derived values keep their
different authority and premises. Carry machine reasons from actual operations into persisted
assessments and CLI/MCP/evaluator responses; human explanation changes must not change semantic
identity. Storage, class-display and scientific representatives remain separate policies, with
original occurrences and qualified alternatives preserved.

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
are implementation choices. The implemented finite record
projection now owns field-set and record membership; do not reopen placement as a greenfield
choice. Extend that owner only for a demonstrated missing meaning, and demonstrate the accepted
table/header/note round trip. Any native change after frozen105 uses a new forward successor
under AC review I03, never a rewrite of historical migration bytes. Do not accept opaque
payload-only persistence that strands query/export/evaluator consumers.

Remaining acceptance checks above are **Planned**; the coordinator retains scoped existing results. For this plan-writing contribution, product tests, database
operations, provider inference and qualification are **not_run**. Package states and any future
evidence receipts belong only to the coordinator.

The [AC improvement review](../../plan_improvement_reviews/audit-closure_2026-11-03.md) I01–I03
and [AC completion audit](../audit-closure_2026-11-03.md#12-completion-audit--claimed-integrated-slices)
constrain the reused foundation. The coordinator alone owns their M1 dependency impact and
current evidence applicability. New checks are selected for unresolved obligations; historical
passes are not promoted to final-source or whole-milestone qualification.
