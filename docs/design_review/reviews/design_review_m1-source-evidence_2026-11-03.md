# M1 source evidence and composed context target

**2026-11-03 · design/target · combined focus · Accept scoped, Proposed target only.**
Independent design-reviewer contribution integrated by the coordinator. Source baseline:
`1c56a68fa58565d3de783adb3ef7d6a5978ac9ed`, initially clean. Audit consumed:
[M1-20261103-r2](../audit/README.md#m1-source-evidence-refresh). Core3.3, heuristics1.0 and
code-intelligence1.4; test-assessment1.2 informs future verification without refreshing that audit.
Concurrent family assembly/pipeline changes were excluded. No runtime or release qualification.

## 1. Scope, outcome and coverage

**Proposed.** Extend the same-view private canonical subset with independently pinned related
selected views, captured recognition text and explicit readings across synthetic whitespace.
Initially ordinary related views share the same native product. OCR-word admission is excluded
until native enforcement authenticates decoded addresses. Arbitrary ordinary cross-product joins,
scientific truth, accuracy, capacity, deployment and assembled M1 qualification are outside scope.
Completed UM functionality/validation is not reopened.

The current immutable products, selected-view custody, field states, evidence sets and native
private guards are strengths. The expanded target needs a versioned source-binding contract,
consumed by the existing binder, context, native completion and later publication projection.
It needs neither another store nor a universal locator/provenance service.

## 2. Responsibilities, dependencies and fidelity

| Owner | Meaning and responsibility |
| --- | --- |
| Effective release, prepared adapters, record binder | Field/state/evidence/source-binding variants, identity and permitted reading operations |
| Published document/SourceView | Actual selected content, placement, membership, projection and recipe |
| Retained PDF products/occurrences | Recognition observation, typed lineage, raw evidence and original provider precision |
| Context owner | Scoped preparation, bounded serialization and source mapping |
| Native completion | Authenticate supported addresses against persisted custody or refuse |
| Consolidation/publication/read owners | Accepted standing and faithful released query/export projections |

The dependency direction remains source custody → prepared bindings → context/model observations
→ interpretation → protected publication. Supplied coordinate text is a binding input, not native
custody. Equal strings do not identify equal occurrences.

| Fact | Fidelity and identity | Coverage limit |
| --- | --- | --- |
| Selected projection/native text | Extracted product/view/projection/recipe/item/cell/range | Exact text does not establish glyph geometry |
| Related note/declaration | Own selected view pin and address | Applicability needs declared relation policy; proximity is insufficient |
| Captured recognition text | Observed product/occurrence/text subrange | Exact string slicing does not establish source accuracy or geometry |
| OCR line/word | Observed payload/page/region/line/word and estimated geometry | Actual retained inventory unknown; native decoded-text admission unresolved |
| Model field/classification | Heuristic invocation/context/schema/model/window | Missing diagnostics and examined scope remain explicit |
| Record reading | Derived interpretation over located inputs | Acceptance and scientific truth remain separate |

Source citations below are relative to `python/corpus-structure/src/corpus_structure/`.
`model/semantic/observations.yaml:180` and `semantic/record_contracts.py:20` retain product placement;
`semantic/sql/source_record_graph.sql:1` retains native graph fences.

## 3. Target contracts and constraints

**Proposed related views.** Keep primary occurrence identity while permitting an anchor's own
related selected-view pin and typed relationship. Authenticate both views against this run's
selected membership; retain each projection/recipe and validate actual item/cell/ranges. Released
relation/field policy decides applicability. Search candidates, exclusions and failed retrieval
are computation dependencies rather than automatically supporting evidence. A related note need
not redefine the primary occurrence; occurrence-recipe inclusion must be explicit. Old proposal
frames2/3 keep direct-ancestor meaning; context1 keeps its historical behavior.

**Proposed recognition address.** Name selected view/occurrence, exact recognition ProductReference
and occurrence, admitted typed lineage, captured-text subrange and original provider address/region
precision plus available raw-response/image provenance. Exact captured characters and uncertain
PDF mapping are different claims. Do not set or reinterpret provider occurrence start/end for the
new slice: `semantic/pdf_integrated.py:100,475` and `semantic/sql/pdf_observation.sql:52` preserve
unknown/coarse/block occurrence precision. Current `recognized_text` resolves canonical node.text
(`semantic/records.py:124`); that label cannot authorize retained recognition evidence.

Native completion must check captured text and exact lineage or refuse. Compose protected sealed
record selectors/context endpoints (`semantic/pdf_record_reader_native.py:17` and
`semantic/sql/pdf_record_context.sql:1`) with retained recognition bodies. Do not assume selected
output endpoints all occupy legacy occurrence tables. `trace_pdf_occurrence` is a useful bounded
read, not authority to accept every upstream relation. The released operation names admissible
relation kinds/outcomes and supporting-context versus retained-alternative standing.

**Proposed OCR limit.** External IPC authentication (`semantic/pdf_record_reader.py:755`) and OCR
validators (`semantic/pdf_ocr_contracts.py:77`) do not authenticate an unchecked caller-decoded
scalar at native ingress. Until a bounded protected projection or equivalent enforcement exists,
OCR-word/line evidence admission is unsupported. No fake canonical text/pointers or general
PostgreSQL Arrow decoder follows. Actual retained-book availability remains unknown.

**Proposed whitespace reading.** A permitted role/policy can read real source pieces separated
only by synthetic whitespace. Return ordered genuine anchors and explicit context-gap diagnostics.
No synthetic character receives a source locator. Labels, punctuation, synthetic-only spans and
unsupported preprocessing changes still refuse. Preserve `original_pieces`/RecordTextSequence;
a joined display is a separately normalized representation, never a continuous literal quote.
Existing literal reconstruction (`semantic/record_contracts.py:325`) remains. `2 bar` and `2 h`
remain different unit observations even when their numeric component matches.

## 4. Composition and execution fit

**Proposed.** Prepare immutable source maps once within a bounded invocation/run-owned lifetime:
validated pins, parsed piece partition, native item/cell map and interval index. Compose many
bounded contexts from these values. Current context construction reparses each full native_context
(`semantic/source_contexts.py:256,409`), repeating stable work for the declared shared-source
workload. Do not add a global cache, persistent preparation store or second reuse authority.
Native ingress continues to authenticate untrusted addresses.

| Stage | Work/reuse boundary | Output and limit |
| --- | --- | --- |
| Source preparation | Existing published selectors; once per immutable frame | Prepared source maps, pins and complete dependencies |
| Related-source selection | Bounded set-oriented queries and released policy | Considered sources, relations, exclusions and explicit outcomes |
| Recognition binding | Protected selected endpoints plus retained observation bodies | Typed address, original precision and admitted lineage |
| Context composition | Slice prepared maps | Exact model text, compact intervals, explicit bounds |
| Span reading | Map positions; no equal-string search | Genuine ordered source pieces or refusal |
| Record binding | Existing release adapter and owned cross-object validator | Private candidates; no publication standing |

H5/H8/H12/H15/H18/H19/H23 guide selected scope, amortized preparation, bounded relevant work,
source-oriented access and enforcement at trust boundaries. This is qualitative fit, not measured
speed or capacity; model work remains outside publication transactions.

## 5. Revealing changes and failures

| Scenario | Expected owned propagation |
| --- | --- |
| Changed table note | Source/context and dependent interpretation change even if winning numeric anchor is unchanged |
| Rejected recognition alternative removed | Recompute decision dependencies; rejected evidence is not a proof premise |
| Repeated strings/equal-valued cells | Distinct pointers/cells/ranges survive; no string-search identity |
| New recognition product | Bind exact new product/occurrence; equal text cannot reuse old product pin |
| Ordinary selected-product substitution | Select/prepare new context; no silent cross-product reuse |
| Synthetic whitespace crossing | Ordered real pieces plus gap receipt; no synthetic quote |
| Pressure `2 bar` versus `2 h` | Preserve actual unit/referent/condition evidence and assignment-relative interpretation |
| OCR only in external IPC | Unsupported admission until decoded-address authentication exists |
| Many contexts sharing long frame | Reuse prepared index; avoid repeated full-frame parsing |
| Missing lineage/text or exhausted budget | Explicit unavailable/unsupported/limited outcome; no canonical fallback or inspected-empty claim |

## 6. Correctness, fidelity and gates

At **Proposed scoped target** strength, G1–G8 and CI-G1–CI-G3 are satisfied by one effective
semantic authority, separated source/model/text/geometry claims, explicit effects and outcomes,
protected enforce-or-refuse admission, complete reuse dependencies, versioned transformation,
truthful coverage and existing library/source composition. Reference/fitting/final populations
remain isolated from extraction inputs. This does not pass an implemented G3: actual native
recognition/related-source enforcement remains required. OCR decoded-address enforcement is
unresolved and excluded, never implicitly passed.

## 7. Findings and preserved strengths

These review-local IDs are new M1 extension obligations, not DA diagnoses or old UM closures.
The coordinator alone owns current disposition.

| ID | Finding, principles and correction | Closure obligation |
| --- | --- | --- |
| F01 | Anchor-equals-primary-pin (`record_contracts.py:217`, native completion:26) cannot represent related evidence. FP02/03/04/05, A1/A2/A3, DP01/02/04/08/24. Version per-anchor source bindings. | Independent related-view expected reading and direct native forged/stale/unselected-pin refusals |
| F02 | Canonical `recognized_text` and one precision dimension cannot express observed-string exactness plus coarse geometry. FP02/04/05, A2, DP02/08/11/24, CI01/02/06/11. Add captured-occurrence address. | Native product/occurrence/substring/lineage checks and precision-substitution refusals |
| F03 | Authenticated external IPC does not authenticate decoded record evidence. FP04/05, A2, DP03/15/22, CI11. Exclude OCR admission. | Revisit only with concrete native decoded-address authentication; inventory alone cannot close |
| F04 | Per-context full-frame preparation repeats stable work. FP06/07, A4, DP09/10, CI08. Prepare immutable source/index once. | Source inspection of lifetime/dependencies and consumers without repeated full parsing; no benchmark required |

Preserve published placement, private task/source custody and accepted-standing refusal, explicit
states/alternatives, ordered sets, exact decimal spelling, graph product fences, old ancestry,
synthetic intervals, immutable archives and exact implementation matching. FP01–06 are satisfied
by the proposed contracts; FP07 requires the prepare-once route. Keeping repeated full preparation
would leave A4 unresolved for the expanded workload.

## 8. Capability fit and evidence strength

**Interface-checked by source inspection, 2026-11-03.** Reuse `load_source_view`,
PublishedDocumentBinding, bounded `read_pdf_product(..., occurrence_id=...)`/`trace_pdf_occurrence`,
protected record endpoints, prepared release adapters and authenticated selected payload readers.
Ordinary immutable mappings and sorted interval lookup suffice for context preparation; no new
indexing dependency is justified. No external library API recommendation, dependency change or
new library qualification is introduced. Existing Arrow custody does not settle native decoded
text admission.

## 9. Alternatives and tradeoffs

Keeping the same-view canonical subset is an honest temporary baseline but cannot deliver this
expanded outcome. Appending alternate strings to canonical text collapses identity/precision.
Trusting supplied coordinate text after Python-only validation permits direct native bypass.
A generic address framework, provenance service or second store adds lifecycle burden without
resolving this trust boundary. Select versioned typed bindings composed with existing owners;
accept the coordinated binder/native/reader integration burden for faithful evidence. Defer a
new OCR text projection until its concrete enforcement and consumer need are established.

## 10. Verification boundary and uncertainty

**not_run:** tests, database operations, model/provider calls and benchmarks. This contribution
is static source inspection. Adoption needs independently expected related-view and recognition
examples; native stale/unselected/forged pin, wrong occurrence/substring/lineage refusals; separate
exact text/coarse geometry; whitespace-only multi-piece success and punctuation/label refusal;
repeated-address controls; changed note/rejected alternative invalidation; old context readability;
prepared-index lifetime; and later protected publication. Native100 is not edited.

Actual retained recognition/OCR availability is unknown. Recognition native lineage enforcement
must compose current sealed selectors and observation custody; a Python trace receipt alone is
insufficient. Public projections, all-family reading quality, independent statistical sufficiency
and operational fit remain enclosing M1 obligations.

## 11. Rule impacts and disposition

| ID | Current rule | Proposed change and authorization route |
| --- | --- | --- |
| RC01 | One pin per record/anchor | Version per-anchor admitted source bindings; keeping it limits same-view evidence |
| RC02 | Canonical recognized_text/one precision | Add captured-recognition address with independent text and provider precision |
| RC03 | Context1 refuses every synthetic crossing and reparses full frame | Preserve context1; add explicit whitespace reading and prepared composition |

The selected M1 outcome and execution authorization cover these extensions. ADR-0049's one
release/context/invalidation direction and ADR-0050's product placement are preserved. The
coordinator routes the consequential contract meanings through ADR-0051 and architectural owners
before implementation. This review itself changes no rule or execution state. M1-03/05 own
binding/context obligations, M1-11 public adoption; their state is not copied here.

## 12. Architectural judgment and decision

At **Proposed scoped target strength**, A1 local change, A2 explicit domain meaning, A3 composition
and A4 execution fit are satisfied: source custody, evidence meaning, preparation and admission
retain coherent owners; actual source identity and text/geometry uncertainty stay explicit;
existing selectors/adapters/guards compose; prepare-once slicing bounds relevant repeated work.

**Accept scoped.** Same-product related selected views, authenticated captured-recognition text
slices and explicitly permitted synthetic-whitespace readings are the selected direction. Current
code has not implemented this expanded support. Exclude OCR-word admission, arbitrary ordinary
cross-product joins, unsupported lineage, lossy mappings and synthetic labels/punctuation as evidence.
Source substitution requires new context preparation/dependency identity. Public record projections
and assembled qualification remain open. Preserve native100, frozen receipts, exact implementation
matching, protected publication and reference isolation.
