# Domain-data-model construction and terminology target review

## Scope, outcome and evidence

**Design / target · combined library and domain-model/principles focus · 2026-11-10.**
**Decision: Accept scoped, at Proposed target-design strength**, for DMC-03–06's recipe,
directional archive, structural-subtree and qualified terminology foundations. No blocking
architectural finding or rule impact is established. This judgment enables implementation of
the selected target; it does not establish implementation, conversion qualification or release
acceptance.

The implemented source inspected is committed `403822dfb6bca2e0fbc1167ebcefc913eccdbccb`.
The audit input is the co-published
[construction/terminology refresh](../audit/README.md#domain-data-model-construction-terminology-refresh)
at that source, inheriting the earlier DMC entry and PTD accounts at their original strength.
This publication is a different source event. Concurrent DMC-03–06 edits, including the direct
Pronto declaration, recipe changes, nested normalization and ADR-0076, are excluded from the
implemented baseline; ADR-0076 is considered an accepted target decision only.

Standards: core3.3, efficient-architecture heuristics1.0, code-intelligence1.4, repository binding
and test-assessment1.2. The functional target is the operator's coherent released domain model
with reproducible authoring, archival interpretation and useful statistical terminology. The
[coordinator](../../plans/domain-data-model_2026-11-10.md),
[construction companion](../../plans/domain-data-model/construction-and-archives.md),
[terminology companion](../../plans/domain-data-model/terminology-and-measurements.md) and accepted
conversational execution plan define the selected delivery. D2/D4 own preparation and recipes;
D1/D5 own source/structural meaning; D8 owns public reads. ADR-0031/0063/0075 preserve archive,
runtime and inspection custody. ADR-0076 records the new terminology rationale.

All source observations below are **Source-inspected, 2026-11-10**. Target behavior and benefits
are **Proposed**. Planning-time inline library diagnostics are attributed to the coordinator,
not claimed as fresh reviewer tests. This review ran no tests, provider, database or benchmark
commands. DMC-07–10's populated bindings, filters, grounding, update reports and measurements,
DMC-11's richer diagnostic custody and DMC-17's assembled qualification remain outside this decision.

## Responsibilities and fact fidelity

| Responsibility | Owner and consumers | Consequential boundary |
| --- | --- | --- |
| Complete recipe reconstruction | `ingest/pdf.py` `PdfRecipe.from_bytes`; actual retained-wire readers | Actual class owns field presence, types and constructor invariants; typed worker/configuration routes remain separate |
| Archive wire interpretation | Existing `releases._products`, `archive_reader.open_release_parts`/`reconstruct_release`; database and candidate capsule readers | Typed conversion replaces mechanical mapping, while independent digest, ABI and coherence checks remain |
| Structural report normalization | `observations.bind_result`, release-owned `property_adapter`; outer report/publication | Handwritten semantic closure and source-codec checks compose with the released nested boundary |
| Terminology acquisition/preparation | Explicit source acquisition, `ontology.py`, `prepare.py`; immutable metadata and inspection | Original source, qualified projection and local membership are different products with explicit provenance |
| Ordinary terminology reading | Prepared release metadata and inspection report; CLI/MCP | Old meaning comes from recorded products, without current ontology or mutable adapter |

| Fact family | Provider/meaning and identity | Coverage and consumer limits |
| --- | --- | --- |
| Recipe value | Exact supplied wire reconstructed under the actual PdfRecipe class | Reconstruction preserves the selected accepted timeout values; it does not newly qualify NaN/infinite deadlines for native execution |
| Archive product | Recorded archive3, manifest/input/artifact identities | Decoding is not authentication, native admission or a request to regenerate current products |
| Structural source value | Existing tagged source codec and declared private report | Shape validation cannot replace hexadecimal, field-order, citation, variant or source-closure semantics |
| Enum/PV declaration | Supplied module, logical declaration path and source digest | Contributor uncertainty remains explicit; inspection v1's missing enum detail is unavailable rather than absent |
| Statistical meaning | Explicit local field/member associated with pinned STATO meaning | Distribution family/attribute is not a parameterization, sample estimator, local record role or global corpus identity |
| Ontology relationship | Original predicate, direction and endpoints; qualified OBO projection where supported | Asserted named-parent edges are not full OWL entailment; dbxref is not exact mapping |
| Source-term binding | Later located observation/selection | A metadata match or source example does not establish a checked binding or selected knowledge |

The model is adequate for this foundation because those distinctions govern the operations,
not merely report labels. DMC-06's two independent optional fields can describe a family without
an attribute or an attribute without a named family. Explicit finite membership avoids importing
an ontology's unrelated semantic categories into local operational policy.

## Construction choices and alternatives

### Recipe preparation

The selected fallback keeps the exact-field JSON guard, then reuses a class-keyed
`TypeAdapter(actual_cls).validate_json(..., strict=True)`. Pydantic2.14.1/core2.50.1 ordinary
strict JSON tuple reconstruction and constructor lifecycle remain the delegated mechanism.
The planning diagnostic found that the proposed `BeforeValidator` route loses the necessary
nested JSON tuple behavior. A duplicate derived wire model or private core-schema program buys
little for this small boundary; retaining the second parse is proportionate (FP-02/03/07,
H4/H12/H26). Cache keys must be actual class objects, not an inherited base-class attribute.

The operator explicitly selected unchanged NaN/infinity acceptance. The implementation must
therefore preserve it and avoid claiming a new finite-deadline invariant. A future execution-only
finite-timeout policy is a distinct decision, not a prerequisite for this reconstruction target.

### Directional archive mapping

A frozen typed product root plus wire-only artifact and registry-row types is the smallest
sufficient representation. It reuses semantic dataclasses rather than copying their definitions.
The archive-scoped cattrs26.2.1 converter configures exact primitive/container and wire hooks before
composite generation. Keeping the name `body_hex` in the wire type gives useful field/index paths;
a renamed semantic `body` field would require error remapping to recover the external name.

The source demonstrates why typed decoding belongs before raw product uses in
`open_release_parts`, including vocabulary manifest corroboration and artifact ordering. Decode
once there; an internal hydrated-product path should not restructure it again. Keep the existing
database header/cache/relational coherence owner and candidate capsule's outer digest/canonical
container checks. Preserve duplicate descriptor/content-row checks and exact kind-set equality
independently of generated field validation. Final exact `_archive_bytes` equality prevents a
lenient hex decoder or leaf default from normalizing a malformed stored archive into acceptance.

Omit only the fields the current writer omits, rather than enabling global omission of defaults.
Retain publication JSON conversion: its bytea, tuple, key collision and nonfinite behavior is a
different direction. Pydantic serialization or a new codec is not a demonstrated equivalent total
replacement. This keeps archive3/capsule1/boundary12 and avoids an unnecessary data migration.

### Nested structural composition

The target's single JSON bridge touches only `structural_product`, using its prepared field
adapter with explicit structural context, before the outer SourceObservationBatch validation.
Existing handwritten closure and comparison-condition codec operations retain their independent
semantic purpose. The outer model still owns enclosing conditions; extracting a field adapter
does not make it inherit every parent rule. The selected extension scenario can add a supported
nested declaration without another consumer traversal branch. A round trip alone cannot settle
source-value or identity fidelity, so the planned independent invalid/known-answer controls remain.

## Terminology projection, change and execution fit

The selected STATO source is a pinned original, not an ambient selector. Acquisition retains
original OWL and deterministic Pronto2.7.4 OBO output, converter options, warnings and coverage.
Independent comparison against original RDF covers the selected labels, definitions and named
parents; original RDF retains annotation and mapping predicates the projection cannot express.
This is a qualified membership/metadata route, never a full OWL-equivalence claim.

One operation-owned OAK0.7.4 adapter per source amortizes application metadata, ownership and
traversal preparation. Explicit prefix setup is necessary for the wrapped-ontology constructor.
Term Validator0.4.5 retains its supported file bridge and may perform its own internal parsing;
the target does not require private cache injection or a second enum interpreter. Complete union
then subtraction and validation of excluded dependencies remain application-owned semantics.

Inspection payload v2 adds enum/PV locators; vocabulary metadata v1 supplements the unchanged
VocabularyMember wire. Old v1 class/property inspection remains useful while missing new detail
is explicit. Bounded CLI/MCP reads use immutable selected products, not an adapter, service or
per-member ontology parse. Current snapshots require one intended compiler21 move with both
native compatibility guards and the generated descriptor updated together. Source/runtime
capture keeps incidental code distinct from meaning-bearing declarations and conversion inputs.

| Change/failure scenario | Credible owning route and required evidence |
| --- | --- |
| Recipe subclass adds a field | Actual-class field set/cache; base and subclass payload controls establish isolation without unrelated producer setup |
| Product/row malformed in a retained capsule | Same typed archive mapping and authentication as database opening; wire-located cause and unchanged state |
| Add a nested report declaration | Prepared subtree adapter consumes it; source/variant closure and outer validation remain separately testable |
| Term removed, obsolete or renamed | New pinned metadata/membership product and explicit checks; old releases reopen old products and later update reporting names its surveyed scope |
| Pronto/OAK replaced or upgraded | Requalify declared projection/metadata fidelity against original bytes; consumers retain the release metadata contract |
| More unrelated ontology terms or repeated reads | Capture only promised metadata/relations; prepare once per operation and decode/reuse by release lifetime, without all-pairs expansion or per-read source acquisition |
| Conversion warning affects a required selected predicate | Refuse or explicitly narrow the supported projection before dependent delivery; retaining bytes alone does not establish fidelity |

The retained originals and converted snapshot have a real lifecycle consumer: independent
qualification and offline historical reopening. Their copy cost purchases that capability. The
same justification does not extend to a generic cache, service, all-pairs hierarchy or binary
transport. Expected improvements are qualitative work-shape gains; no latency/capacity claim or
benchmark requirement follows (FP-07/A4, H5/H12/H16/H18–20/H26–28).

## Judgments, verification and decision

| Judgment | Verdict and basis at target-design strength |
| --- | --- |
| A1 Localize change | Satisfied: recipe class, archive wire, released subtree and ontology acquisition have coherent reasons to change and named adjacent consumers |
| A2 Explicit domain meaning | Satisfied: wire/authentication/admission, source/shape, descriptive metadata/membership and term/binding identities remain distinct and authoritative |
| A3 Local reasoning and composition | Satisfied: pure reconstruction and scoped preparation reuse existing validators; no ambient current release or private adapter cache |
| A4 Execution fit | Satisfied: bounded recipe preparation, once-per-contract hooks, one subtree bridge and operation/release lifetime reuse serve the selected workload without new coordination machinery |

FP-01–07 are satisfied for these selected scenarios; relevant DP-01–12/15/18–24 are supported by
the authority, construction, lifetime and verification routes above. No full-system conclusion
is inferred. Gates G1–G8 pass for the specified target; implementation evidence remains due.
CI-G1 passes because provenance, relationship kinds and coverage are explicit; CI-G2 passes
because served detail closes over retained source/product references; CI-G3 passes because the
planned independent source/byte/invalid controls do not derive expected semantics from the same
producer. No new heuristic scientific assertion is selected. Those are design judgments, not
claims that unexecuted tests passed.

Required acceptance remains with the coordinator: independent recipe byte/digest/subclass cases;
exact archived and capsule bytes/errors/authentication; two-release nested semantic controls;
real selected term/source controls and conversion loss cases; offline old/new metadata reads;
final native archive/admission and public inspection through actual reader roles. Preserve
failed/interrupted receipts and final source/context applicability. Provider runs, Rust behavior,
unit conversion and full-series qualification are not selected by these packages.

**Findings:** no additional blocking finding. **Rule impacts:** none required; the selected
metadata/profile route preserves existing semantic and publication authority. Do not treat the
accepted target as source conversion qualification or package completion. The DMC coordinator
owns I02/I03 decisions, the resolved I01 slice, implementation and selected acceptance; DMC-17
owns the assembled review and enclosing qualification.
