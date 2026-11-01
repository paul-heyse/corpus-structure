# Integrated PDF/Docling and Nemotron pipeline

**Status:** Active;0060 deployed/0061–0065 undeployed. PDF-20/21 publication and PDF-24 readers/exports are implemented with scoped verification; PDF-25 migration adapters are implemented but operational cutover remains open. Native global finalization remains materialized.
Whole-book recognition passed; integrated publication, actual consumer adoption and complete qualification remain open.
**Created:** 2026-10-31. **Revised:** 2026-11-01.
**Basis:** Original [PDF review](../functional_reviews/pdf-docling-pipeline_2026-10-31.md)
at `2c333722fe9b3ad03c8004d14c5f50a1605c3f4b` and its target; added
[triple-pass review](../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md) and
[integrated target](../functional_reviews/docling-nemotron-triple-pass_2026-10-31_target-model.md)
at `d25fff8`. This coordinator alone owns package state, source-qualified opportunity dispositions
and investigations I01–I20. Supporting documents own technical explanations, not duplicate queues.
New planning basis: [streaming/storage review](../functional_reviews/pdf-streaming-and-storage_2026-11-01.md)
and [target](../functional_reviews/pdf-streaming-and-storage_2026-11-01_target-model.md) at `1c6fc710`;
O01–O06 selected for planning, O07 conditional. No new implementation is established by this amendment.

## Library improvement planning basis — 2026-11-01

Consume [streaming improvement review](../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md)
at `5d7a72c4`. The operator approved this plan integration on2026-11-01. Existing PDF-20–25 owners
absorb the amendments; no new plan series, workflow engine or generic resource framework is added.
The source review's I01–I11 references are qualified by review path, distinct from this coordinator's
I01–I20 investigation IDs. The disposition table below is the sole scheduled-status owner.

Required additions strengthen native finalization inputs, release-owned configuration, owned
seekable source/crop lifetime, record/batch handoffs, completion/diagnostic semantics and selected
views. Public scheduler adoption is an investigation outcome, not a promised available seam.
Additional code/picture/table recognizers and serving caches remain conditional; native guarded
multipass substitution and broader input/service changes remain unselected. No new rule change
is selected: ADR-0042, mandatory true triple pass/alternatives, intact sections, atomic publication
and independent automated grading remain the target. A contrary investigation outcome needs an
explicit decision before dependent scope changes. Plan authoring is not production delivery.

## Current operator correction — 2026-10-31

Historical HTML-derived documents and outputs no longer require compatibility. ADR-0040 records
this explicit instruction. It supersedes historical-read/replay requirements elsewhere in this
series; prior dated implementation receipts remain true within their original scope. PDF-16/10
retire compatibility-only readers, profiles, fixtures, old ABI branches and dependencies after
migrating current PDF users. Current PDF reuse and generic release/text/math semantics survive.
No database purge, frozen migration rewrite, plan/evidence deletion or grading-policy change is implied.

## 1. Outcome and fixed boundaries

The selected target is **PDF → StandardPdfPipeline with in-page RapidOCR + Nemotron3.5 true
triple pass → one integrated document → section-grounded knowledge consumers**. DoclingDocument
is the content graph; mandatory application relations carry multiple-input provenance, alternatives,
selection and coverage. Governed selection may add or replace content from either recognizer while
preserving originals and raw observations. Consumers do not merge provider documents independently. The initial
original is `docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf`: 1,589 pages and
211,502,518 bytes per the source review. Retain original bytes, native document products,
conversion health and domain knowledge as separate connected meanings.

**No section chunking is planned.** Preserve intact sections/subsections. Bounded responses,
transport pages and native stage batches do not create semantic chunks. Upstream conversion
from other formats to PDF is outside this series. Nemotron table/chart recognition is selected; unrelated model families, extra OCR ensembles,
picture descriptions and services remain conditional. Recognition is not a knowledge claim;
consolidation remains the claim authority.

Docling owns its native versioned schema. LinkML/trusted execution definitions own application
operations, transitions, coverage, dependency recipes and cross-product/domain relationships.
PostgreSQL owns instance custody and native enforcement. Derive operation-shaped views from
native products rather than retain an HTML-shaped primary representation with attached JSON.

The standard is core 3.3 plus efficient-architecture heuristics 1.0 and applicable profile/binding
guidance. Apply qualitative execution fit before fixing physical representations. No broad audit,
new alignment lint, cost model, generic workflow engine or additional proof framework is introduced.

### Structural streaming target — confirmed planning scope, 2026-11-01

One logical Docling+companion document is realized through lossless typed records, ordered
memberships and native-address maps, with bounded artifact parts and Arrow batch movement.
Its logical identity is independent of physical batch boundaries; exact original/retained/export
byte identities remain distinct. Private append → freeze → complete native validation → atomic
publication reuses task/attempt authority. Default readers see published documents; conditional
sealed scopes need their own immutable pins and closure evidence. The model owns all domain
operations, states, relations and invariants. A single logical document does not require a
single JSONB or bytea value; bounded extension JSON remains available where useful.

PDF-17–19 implement the record/identity foundation; PDF-20/21 and PDF-24 mechanisms now have scoped native/reader verification. PDF-22/23 producers retain materialized global finalization; PDF-25 deployment and operational integration remain open. PDF-26 is conditional. Existing0060/0061 and PDF-00–16 receipts
remain baseline evidence. Docling global reading-order/heading/enrichment behavior must survive;
no strict bounded-memory claim follows until I14 establishes the exact producer route.

### Remaining execution decisions — 2026-11-01

The operator approved completing all remaining mandatory publication, reader, migration and
adoption scope, preserving the materialized native global-finalization boundary. Strict global
memory streaming is deferred: revisit on an actual normal-workload limitation or a suitable
upstream seam. I14 must report the actual remaining working set, not claim that page/IPC bounds
bound the whole native graph. I19/PDF-26 remains deferred because no selected early-consumption
workflow establishes closure ahead of native global inference; revisit when such a consumer exists.

[ADR-0043](../adr/0043-segmented-artifact-byte-identity.md) records the selected byte identity:
new segmented streams require actual parts/lengths and native-verified canonical byte folds;
conventional serialization SHA-256 is separately scoped optional export metadata. Original/raw/
historical digests stay unchanged. No server hashing extension is required. Complete native
callback conformance is an explicit finite materialization over the fixed candidate, alongside
independent model-derived PostgreSQL row/set/byte enforcement. Neither result replaces the other.

The remaining execution includes actual owned-database forward deployment, retained-book
migration/publication/export, five-section extraction, independent full-section A/B/C references,
automated grading, completed-result/default adoption and final-source qualification. Optional
recognizers/caches and progressive scope activation remain unselected. Implementation and measured
results are reported separately below; these decisions alone establish neither.

## 2. Baseline and foundation assessment

The deployed execution baseline remains native0060/compiler14/core0.6.2; source now contains
ABI16, relational compiler4/core0.6.4 and undeployed0062–0064 private foundations/staging. Full
Docling2.145.0/core2.105.0 and native schema1.10.0. Integrated producers, governed selection,
scoped readers and forward-only consumers are implemented. Actual all-page Nemotron recognition
and fresh composed toy publication passed; whole-book integrated publication and assembled
consumer/evaluator adoption remain separate acceptance obligations. Prior PP/PDF receipts retain
their original scope; no source result is relabelled as knowledge or fidelity qualification.

Reuse trusted release/compiler preparation, Core metadata, original/native custody, protected
publication, finite worker ownership, selected SourceViews and lazy scientific consumers. The baseline already supplies multi-input lineage, raw partial-response custody, governed
selection and scoped consumer reads. The new work replaces required whole-document materialization
and transport while preserving those meanings. Current indexed items are access projections, not
a proven lossless substitute for every Docling field. Existing Arrow COPY is reusable but its
full-table freezing/canonical-body constructor must not remain on the required streaming path.

Public NVIDIA orchestration avoids porting scheduling/cropping/merge internals. PDF-14 supplies only
necessary custody/runtime adapters; PDF-15 owns cross-provider selection. Docling content plus
mandatory companion semantics is favored over replacing the entire content schema. Revisit that
choice only for a required consumer distinction that cannot be faithfully or reasonably represented.
The isolated runtime preserves root Torch/Transformers. Actual Blackwell MTP/FA2 and coarse
geometry/mapping controls passed; independent source-quality benefit remains unestablished. Apply FP-04/A2, CI attribution/precision/evidence rules and FP-07/A4 qualitatively;
no new generic scheduler, broad audit, numerical cost model or alignment lint is introduced.

## 3. Confirmed rule changes

Operator explicitly selected **Adopt all five** on 2026-10-31. These are approved planning
envelopes, not already deployed architectural decisions. PDF-00 schedules the existing ADR route
and enduring owner updates before dependent product behavior. Accepted ADRs remain immutable.

| Review item | Confirmed change | Route and prerequisite |
|---|---|---|
| RC01 | Replace HTML5/DOM ingestion and source-profile rules with PDF-only conversion. | PDF-00 reconciles ADR-0036/0037 and D1/D4/D6; PDF-04/10 implement and retire. |
| RC02 | Distinguish PDF regions, native/recognized text and derived offsets; recognized LaTeX is not original author TeX. | PDF-00 D1/D3 clauses; PDF-02 address/identity semantics before persistence/consumers. |
| RC03 | Version section units, packets/source frames and source APIs. | PDF-00 D4/D5/D7/D8 ownership; PDF-05–08 actual migration. |
| RC04 | Docling owns its native schema; LinkML governs application behavior and cross-product semantics. | PDF-00 D2/D3 authority; PDF-02 archived upstream schema and derived contracts. |
| RC05 | Replace/retire obsolete parser stages, bindings and dependency recipes. | PDF-00 D4/D6; PDF-06/09/10 remove active old paths with replacements. |

On 2026-10-31 the operator explicitly selected **Adopt both** for the added review's rule impacts:

| Plan rule item | Confirmed change | Route before dependent behavior |
|---|---|---|
| RC06 | Promote Standard+RapidOCR and true full-page Nemotron parse/detect/Table-Chart-crop interpretation to the selected pipeline. | PDF-12 successor ADR superseding ADR-0038 and D1/D2/D3/D4/D6 owner updates; PDF-14 actual runtime/producer. |
| RC07 | Publish one integrated document, permitting governed content addition/replacement from either provider with originals, alternatives and evidence preserved. | Same successor ADR; D1–D8 affected contract/consumer owners; PDF-13/15/16 implement. |

RC06/07 are local plan identifiers linked to the [new review rule impacts](../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md#rule-impacts-and-recommended-sequence); they do not
renumber original-review RC01–05. The approved target is not deployed behavior. ADR-0039 now supersedes immutable ADR-0038. PDF-12
runtime/geometry/mapping feasibility remains open; the decision alone does not establish it.

Additional rule changes discovered during execution need their own explicit disposition; these
confirmations do not authorize changing grading policy, audit premises or historical evidence.

### Additional confirmed rules — 2026-11-01

The operator explicitly accepted each item during plan preparation. These approve the planning
target; they do not retroactively change deployed behavior or mutable authority in accepted ADRs.

| Plan rule item | Confirmed change | Route before dependent behavior |
|---|---|---|
| RC08 | Replace mandatory whole-document JSONB/canonical bytea values with lossless model-governed records, bounded artifact parts and a versioned streaming identity contract; retain one logical document and historical pin/byte meaning. | PDF-17 new ADR superseding the affected ADR-0041 realization; D1/D2/D3/D8 owner changes; PDF-18/19 model/identity before new writes. |
| RC09 | Replace monolithic admission with private append, freeze, validation and final publication operations; preserve independent PostgreSQL enforcement and atomic whole-document visibility. | Same successor decision; D3/D6 operation/lifecycle ownership; PDF-20/21 protected implementation before activation. |

Progressive section consumption remains conditional on I19 and any additional rule disposition;
physical streaming does not authorize semantic section chunking or provisional knowledge claims.

## 4. Documents and execution packages

| Package | Supporting owner / result | Required inputs | State |
|---|---|---|---|
| <a id="PDF-00"></a>PDF-00 | [Foundations](pdf-docling-pipeline/foundations-and-investigations.md#PDF-00): architectural decisions and enduring owners | Confirmed RC01–05, current clauses | Delivered: ADR-0038 and architectural owners |
| <a id="PDF-01"></a>PDF-01 | [Investigations](pdf-docling-pipeline/foundations-and-investigations.md#PDF-01): qualified library/runtime choices | Source PDF, review; early PDF-02 agreement where needed | Implemented and bounded provider-tested: full distribution, actual OCR/native cases and full-book source; final union remains PDF-11 |
| <a id="PDF-02"></a>PDF-02 | [Model](pdf-docling-pipeline/model-contracts-and-storage.md#PDF-02): connected contracts and prepared ports | PDF-00; I03/04/06 before final producer contracts | Implemented and targeted-tested: SourceViews, qualified frames/addresses, runtime/cell/coverage/alignment contracts and explicit demands |
| <a id="PDF-03"></a>PDF-03 | [Storage](pdf-docling-pipeline/model-contracts-and-storage.md#PDF-03): native JSON, derived access rows and integrity | Agreed PDF-02; I06 | Implemented through 0055: protected native publication, indexed items/regions/cells/coverage/runtime/alignment, qualified frames, syntax and OCR provenance; native controls passed |
| <a id="PDF-04"></a>PDF-04 | [Conversion](pdf-docling-pipeline/conversion-and-document-hierarchy.md#PDF-04): PDF producer with explicit health | I01/02/03; relevant PDF-02 support | Implemented and provider-tested: full-book source and selected inline/cell enrichment; remaining alignment gaps are typed and source-qualified |
| <a id="PDF-05"></a>PDF-05 | [Hierarchy](pdf-docling-pipeline/conversion-and-document-hierarchy.md#PDF-05): intact sections and qualified views | PDF-04, PDF-02, I04; PDF-03 for persistence | Implemented and source-tested: intact hierarchy, unique five-root selection, per-view coverage and explicit analysis/context identity |
| <a id="PDF-06"></a>PDF-06 | [Math](pdf-docling-pipeline/interpretation-and-domain-consumers.md#PDF-06): direct formula input and lazy M09/M11 | PDF-04/05, I03/05 | Implemented and targeted-tested: M09 retained interpretation, M11 hydration, qualified partial context and demand-specific assessment; final union open |
| <a id="PDF-07"></a>PDF-07 | [Consumers](pdf-docling-pipeline/interpretation-and-domain-consumers.md#PDF-07): M13/domain recognition and rich packets | PDF-05, agreed PDF-06 states and PDF-02 frame contract | Implemented and targeted-tested: native policies, qualified context, packets, finalization and reference frames; actual provider/grading journey open |
| <a id="PDF-08"></a>PDF-08 | [Interfaces](pdf-docling-pipeline/source-interfaces-and-runtime.md#PDF-08): typed CLI/MCP, placement and exports | PDF-03/05; PDF-06/07 for their views | Implemented and targeted-tested: CLI run6 reads passed; historical external reads/export passed; current external render/MCP journey not_run |
| <a id="PDF-09"></a>PDF-09 | [Runtime](pdf-docling-pipeline/source-interfaces-and-runtime.md#PDF-09): owned conversion lifecycle and publication | PDF-02/03/04; I07 before adoption | Implemented and source-tested: retained originals, finite child lifecycle, exact conversion/enrichment reuse and scoped request authority |
| <a id="PDF-10"></a>PDF-10 | [Adoption](pdf-docling-pipeline/adoption-and-retirement.md#PDF-10): PDF defaults, consumer cutover, HTML removal | Integrated PDF-03–09, PDF-13–16 and PDF-17–25; I08/I13 | Partial: HTML producers retired, statistics/toy inputs native PDF; completed PDF result/default selection open |
| <a id="PDF-11"></a>PDF-11 | [Acceptance](pdf-docling-pipeline/adoption-and-retirement.md#PDF-11): actual journeys and required-union evidence | Complete selected functional scope, PDF-10 | Incomplete:0060 functional baseline2643passed; committed0061 has focused verification only; whole-book publication, actual provider/evaluation/current external journeys and final-source union remain open |
| <a id="PDF-12"></a>PDF-12 | [Foundations](pdf-docling-pipeline/foundations-and-investigations.md#PDF-12): successor decision and consequential feasibility | RC06/07 and current source | ADR-0039 delivered; isolated actual runtime, transforms and bounded mapping controls passed; corpus benefit remains separately assessed |
| <a id="PDF-13"></a>PDF-13 | [Integrated model](pdf-docling-pipeline/integrated-document-model-and-lineage.md#PDF-13): connected contract/storage, multi-input lineage | PDF-12 decision route; I10/11 for affected final constraints | Implemented foundation; targeted verification below; provider precision remains gated |
| <a id="PDF-14"></a>PDF-14 | [Triple recognition](pdf-docling-pipeline/triple-pass-recognition-and-reconciliation.md#PDF-14): owned public parser and retained request outcomes | I09 pins/runtime; PDF-13 observation/publication slice; I10 for grounded use | Implemented; actual full-book A/B/C recognition passed with retained primary failures and two named recoveries; assembled publication remains PDF-10/11 |
| <a id="PDF-15"></a>PDF-15 | [Integration](pdf-docling-pipeline/triple-pass-recognition-and-reconciliation.md#PDF-15): mapped rich content, correspondence and governed selection | Working PDF-13/14; I10/11 | Implemented and targeted-tested; ADR-0041/0060 bypasses the relation-array JSONB limit;0061 set-join child validation is committed/undeployed; actual whole-book acceptance remains open |
| <a id="PDF-16"></a>PDF-16 | [Consumers](pdf-docling-pipeline/integrated-document-consumers.md#PDF-16): singular reader, scientific/extraction/interface/evidence migration | Agreed PDF-13 for design; working PDF-15 for acceptance | Implemented; current external/provider/evaluator journeys remain PDF-10/11 |
| <a id="PDF-17"></a>PDF-17 | [Relational foundations](pdf-docling-pipeline/relational-document-model-and-identity.md#PDF-17): successor decision and investigation outcomes | Confirmed RC08/09, review/current source | Delivered ADR-0042 and foundation outcomes; I14 producer and downstream activation remain scoped open |
| <a id="PDF-18"></a>PDF-18 | [Lossless model](pdf-docling-pipeline/relational-document-model-and-identity.md#PDF-18): native records, memberships, generated lowerings | PDF-17 decision slice; I15; early I14 | Implemented codec/generated metadata/private0062+0063; targeted controls, no live deployment |
| <a id="PDF-19"></a>PDF-19 | [Identity/custody](pdf-docling-pipeline/relational-document-model-and-identity.md#PDF-19): logical identity, native addresses, exact artifact parts | I16, PDF-18 model, PDF-17 decision | Implemented versioned fold/part primitives and SQL parity; complete staged correspondence remains PDF-20/21 |
| <a id="PDF-20"></a>PDF-20 | [Private staging](pdf-docling-pipeline/staged-publication-and-validation.md#PDF-20): typed COPY, durable records/parts and replay | PDF-18/19 contracts, I17 append slice, I18, PDF-17 decision | Implemented typed COPY, bounded metadata byte fields, exact replay/resume and native model-derived JSON Schema; scoped controls passed. Book-scale adoption remains PDF-25 |
| <a id="PDF-21"></a>PDF-21 | [Freeze/seal](pdf-docling-pipeline/staged-publication-and-validation.md#PDF-21): full native closure and atomic publication | Working PDF-20, PDF-18/19 invariants, I17 | Implemented modeled freeze, private preparation, actual-record identity, required native callbacks and atomic seal; scoped PostgreSQL controls passed. Whole-book seal and complete failure/concurrency union remain open |
| <a id="PDF-22"></a>PDF-22 | [Standard streaming](pdf-docling-pipeline/streaming-processing-and-arrow.md#PDF-22): native-equivalent assembly/enrichment adaptation | Early I14; PDF-18/19 contracts; PDF-20 for actual persistence | Implemented private producer; retained1589-page assembly/enrichment replay and fresh pages20/1211 passed after explicit class/raster-scale corrections. Native global state remains materialized; strict streaming deferred under I14 |
| <a id="PDF-23"></a>PDF-23 | [Arrow/reconciliation](pdf-docling-pipeline/streaming-processing-and-arrow.md#PDF-23): incremental recognition/selection and resource ownership | PDF-18/19, I18, working PDF-20; PDF-22 for assembled acceptance | Implemented completion-driven recognition, file-backed source and Arrow/DuckDB reconciliation/companions with private IPC/adoption; scoped controls passed, public cutover remains PDF-21/24/25 |
| <a id="PDF-24"></a>PDF-24 | [Streaming consumers](pdf-docling-pipeline/integrated-document-consumers.md#PDF-24): shared pinned readers and complete exports | PDF-18/19 early contract; working PDF-21/23 for acceptance | Implemented published-pin readers, shared source-context authority, exact byte-field decoding and single-cursor native/integrated exports; scoped controls passed. Current external/full-book journeys remain open |
| <a id="PDF-25"></a>PDF-25 | [Structural cutover](pdf-docling-pipeline/adoption-and-retirement.md#PDF-25): retained-data migration and deployed contract handoff | Working PDF-18–24 | Implemented exact-envelope migration/resume adapter and validated computed-grid derivation; deployment, book publication and actual cutover not_run. PDF-10/11 retain final adoption/qualification |
| <a id="PDF-26"></a>PDF-26 | [Progressive scopes](pdf-docling-pipeline/integrated-document-consumers.md#PDF-26): immutable dependency-closed sections | I19 outcome and explicit selection; working PDF-18–24 primitives | Conditional; not a blocker for initial atomic-document completion |

**Current sequence:** PDF-17 successor ADR and PDF-18/19 record/identity contracts are implemented.
Private PDF-22/23 and the minimum PDF-20 staging path are implemented and scoped-tested.
Continue PDF-21 to freeze/validate/publish immutable staged unions, then PDF-24 selected consumers.
Native global finalization remains materialized under the selected execution boundary; strict I14
requires a further upstream/adapter remedy. Follow these with PDF-25
migration and PDF-10/11 actual adoption/qualification. Interface readiness is not native/provider
acceptance. Independent investigation/design slices may proceed together; shared model/compiler
surfaces retain one integrated editing owner. PDF-26 remains conditional on I19.

I14 preserves native global finalization; I20 selected completion-driven finite page workers because
public batch orchestration lacks the required concurrent observation seam. PDF-20 implements the agreed
private source/replay and wire contracts. Working producers, frozen validation and
actual readers must converge before PDF-25/10/11 assembled acceptance. No optional recognizer,
serving-cache experiment or progressive scope blocks the initial required union. Record actual
limits where native global objects remain; a page iterator or protective refusal is insufficient.

Do not qualify an obsolete monolithic book route merely before implementing its successor.
Preserve0061's corrected child semantics in forward guards and all frozen SQL/receipts unchanged.
PDF-00–16 delivery remains scoped to the baseline; only affected new guarantees need fresh evidence.
The [integrated evidence](../design_review/evidence/2026-10-31_pdf-integrated-adoption/README.md)
retains actual raw recognition, failed publication and passing controls.

## 5. Opportunity disposition

All references below are scoped to the [PDF review](../functional_reviews/pdf-docling-pipeline_2026-10-31.md),
not similarly numbered items from prior parsing reviews. No opportunity is closed by plan creation.

| Item | Component and planned correction | Disposition / dependencies | Closure evidence |
|---|---|---|---|
| [O01](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O01) | PDF adapter and health | Implemented and source-tested · PDF-01/02/04/09 | Whole-book publication, final native/OCR controls and selected enrichment preserve separate conversion/recognition outcomes; final union remains PDF-11. |
| [O02](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O02) | Native custody, scoped schema and indexed projections | Delivered in bounded native/read scope · PDF-02/03/08 | Protected PostgreSQL controls, full Docling JSON reload/tree validation, lexical exports and actual pinned reads; assembled qualification remains PDF-11. |
| [O03](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O03) | Sections/subsections without chunking | Implemented and source-tested · PDF-01/05/07 | Full retained hierarchy, five maximal intact roots, explicit direct context and role-qualified projection identity; universal heading fidelity is not claimed. |
| [O04](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O04) | Formula items into lazy math | Implemented; actual fidelity qualification open · PDF-01/04/06 | Native display/inline/cell outputs, retained occurrences, lazy interpretation and source-qualified partial coverage; independent corpus grading not_run. |
| [O05](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O05) | Real domain and packet consumers | Open · PDF-05/06/07 | Rich context enters packet/source-frame identity, scope and consolidation; no CSS truth substitution. |
| [O06](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O06) | Structural placement and serving | Open · PDF-08/11 | Real CLI/MCP, direct item/cell citations and source-qualified exports. |
| [O07](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O07) | Book-scale lifecycle and retirement | Open · PDF-01/09/10/11 | Full-book source feasibility, reusable products, no active HTML route and historical read. |
| [O08](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O08) | Explicit primary OCR; conditional verification | Delivered selected primary OCR in bounded scope · PDF-01/04/09 | Actual CPU ONNX OCR and CUDA model-stage reports, word/raster transforms and broken-layer controls; the added triple-pass route is planned in PDF-14, not covered by this receipt. |

### Added triple-pass review opportunities

All seven opportunities are selected for planning. IDs below refer to the added review, not the
original PDF review. Closure requires delivered behavior; source inspection is not implementation.

| Source item | Planned owner and benefit | Current disposition / completion evidence |
|---|---|---|
| [O01](../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md#O01) | PDF-12/14 public true triple pass | Implemented and actual all-page recognition passed; retained submitted pixels/raw/full HTTP, valid zero-C and separately identified recovery outcomes in integrated evidence |
| [O02](../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md#O02) | PDF-13 multi-input identity, relations and custody | Implemented and targeted-tested · PDF-13; real fenced publication, scoped ancestry/trace, native backfill and archived replay |
| [O03](../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md#O03) | PDF-15 governed content selection | Implemented and bounded rich selection/replay controls passed; actual selected book/knowledge journey remains PDF-10/11 |
| [O04](../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md#O04) | PDF-15/16 hierarchy/table/chart semantics | Implemented and targeted-tested: rich tables/chart panels/captions/inline structure, coarse cell grounding, repeated occurrences and alternatives; independent corpus fidelity remains PDF-11 |
| [O05](../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md#O05) | PDF-13/14/15 modeled outcomes, coverage and reuse | Implemented protected raw capture, explicit failed/partial outcomes, scoped coverage and recipe-qualified replay; actual raw book inventory complete, integrated publication remains PDF-10/11 |
| [O06](../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md#O06) | PDF-12/14 isolated runtime and shared capacity | Implemented; actual Blackwell/MTP/FA2, finite public page workers and native→Nemotron GPU phase control passed; no throughput claim |
| [O07](../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md#O07) | PDF-16 and PDF-10/11 real evidence-aware consumers | Consumer mechanisms implemented; actual external MCP/render/extraction/claim trace and adopted result remain PDF-10/11 |

### Streaming/storage review opportunities — at `1c6fc710`

These source-qualified IDs refer to the2026-11-01 review, not either earlier O01 set.
Plan authoring closes none of these capabilities.

| Source item | Responsible packages / value | Disposition and closure |
|---|---|---|
| [O01](../functional_reviews/pdf-streaming-and-storage_2026-11-01.md#O01) | PDF-17–19/25 lossless records, native mappings and identity | Foundation implemented; native reconstruction and exact-byte primitives tested; PDF-25 retained-data cutover remains open |
| [O02](../functional_reviews/pdf-streaming-and-storage_2026-11-01.md#O02) | PDF-20/21 private staging/freeze/native seal | Private staging/freeze/actual-row validation/seal implemented with scoped native controls; full integrated book publication remains PDF-21/25 |
| [O03](../functional_reviews/pdf-streaming-and-storage_2026-11-01.md#O03) | PDF-17/22/23 bounded local work with global finalization | Private producer implemented/tested; heavy pages/artifacts and IPC streamed, native global graph remains materialized; strict I14 open |
| [O04](../functional_reviews/pdf-streaming-and-storage_2026-11-01.md#O04) | PDF-19/20/23/24 common Arrow transport/compute/read lifetime | Arrow IPC/COPY/reconciliation plus published selective reads and exact single-cursor exports implemented/scoped-tested; actual full-book/external journeys remain PDF-24/25 |
| [O05](../functional_reviews/pdf-streaming-and-storage_2026-11-01.md#O05) | PDF-20/21/23/25 systematic transactions/validation | Typed transactions, frozen validation and atomic seal implemented/scoped-tested through0065; deployed book validation remains PDF-21/25 |
| [O06](../functional_reviews/pdf-streaming-and-storage_2026-11-01.md#O06) | PDF-24 pinned selective consumers/full exports | Published readers and native/integrated streaming exports implemented/scoped-tested; current external and whole-book journeys not_run |
| [O07](../functional_reviews/pdf-streaming-and-storage_2026-11-01.md#O07) | I19/PDF-26 early section consumption | Conditional; explicit closure/value outcome before activation; not required for atomic completion |

### Library improvement recommendations — at `5d7a72c4`

References here name the improvement review, not similarly numbered coordinator investigations.
Private producer/staging outcomes below are implemented and scoped-tested on2026-11-01;
[streaming runtime receipts](../design_review/evidence/2026-11-01_pdf-streaming-runtime/README.md)
retain their limits. PDF-17–19 receipts keep their original scope.

| Source recommendation | Owning packages / investigation | Current disposition and closure |
|---|---|---|
| [I01](../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md#I01) parser/queue/consumer capacity | PDF-22/23; PDF-20/24 consumers; I18 | Implemented effective recipe controls, page-spool ACK backpressure and bounded IPC adoption; public consumer/resource composition remains PDF-24 |
| [I02](../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md#I02) compact native finalization | PDF-22; I14 | Implemented retained heading/list/assembly inputs and exact bounded native differential; retained-book lowering measured. Full native global graph remains materialized; strict I14 open |
| [I03](../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md#I03) public scheduling and custody | PDF-23; I20; PDF-20 receipt contract | Selected completion-driven finite page replenishment; public prepared/pipelined API lacks current concurrent crop/request observation seam. True parse/union/alternatives and exact receipts preserved |
| [I04](../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md#I04) native Docling multipass | Conditional choices; PDF-23 | Substitution deferred: current guarded merge/failure/sampling/evidence contract differs; revisit on suitable hooks or separately selected narrower semantics |
| [I05](../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md#I05) owned source/replay capabilities | PDF-20/22/23/25 | Implemented immutable digest-bound seekable source, verified bounded replay descriptors and claim-owned child/source settlement; operational retirement remains PDF-25 |
| [I06](../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md#I06) model-bound batches/selective readers | PDF-20/21/23/24 | Implemented model-bound private wire profiles and same-session COPY/adoption; frozen-union/snapshot readers remain PDF-21/24 |
| [I07](../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md#I07) enrichment lifetime/richer content | PDF-22/23; PDF-24 consumers | Shared source/raster/crop/type lifetime implemented/tested; extra recognizers remain conditional, no new eager stages |
| [I08](../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md#I08) transformations/complete views | PDF-23/24 | Private reconciliation uses native graph and shared selection kernel with Arrow companion journals; complete selected reader/export migration remains PDF-24 |
| [I09](../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md#I09) completion/diagnostics | PDF-20/21/23/24 | Private native completion/errors/recipe artifacts and existing recognition failure/partial/zero-C custody retained; frozen validation and demanded public diagnostics remain PDF-21/24 |
| [I10](../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md#I10) image/serving cache reuse | PDF-23; conditional runtime choices | Conditional: actual plugin/API support and avoided-work comparison; stable content/frame/processor keys and retained-byte fallback |
| [I11](../plan_improvement_reviews/pdf-docling-streaming-improvements_2026-11-01.md#I11) table-matching source correction | PDF-22/23 comparison premises; I15/I18 | Corrected planning premise: disabled matching uses backend text, not independent visual transcription; retain matching baseline pending actual deficiency |

## 6. Investigation queue

PDF-01 explains original investigations; PDF-12 explains added methods and decision consequences; this is the sole mutable investigation state.
Each result names source scope, conclusion, limits and affected package; evidence uses existing
repository records when a probe produces an accepted result. No new permanent capability register.

| ID | Question and necessary output | State / constrains |
|---|---|---|
| I01 | Exact PDF-only extras, Python 3.14/runtime/model compatibility and actual per-stage providers | Delivered selected runtime: full installation/offline assets; actual CUDA model stages and explicit CPU ONNX OCR, without an OCR CUDA claim · PDF-04/09 |
| I02 | Heron versus Egret Large region detection; crop/repetition settings and chosen recipe | Bounded comparison delivered: retain Heron; no measured quality improvement · PDF-04 |
| I03 | Attributable formula health; inline and table-cell coverage; supported rich-cell enrichment route if necessary | Implemented: selected inline/cell enrichment, exact outcome/coverage and bounded unresolved diagnostics; actual source fidelity remains PDF-11 · PDF-02/04/06/07 |
| I04 | Heading levels versus actual section groups; ordered intact hierarchy and descendant-selection semantics | Mechanism delivered: derived groups preserve refs/order; semantic heading fidelity remains PDF-05/07 · PDF-02/05/07 |
| I05 | Native SymPy compatibility on real recognized formulas; smallest required grammar/occurrence gap | Implemented: direct native LaTeX with versioned Lark/SymPy frontend and retained occurrence/context; targeted semantics/deadline controls, final union PDF-11 · PDF-06 |
| I06 | JSON/schema roundtrip, validation mutation, image custody and native/region address precision | Delivered: protected native JSONB and source-qualified projections; full Docling JSON reload/tree validation and lexical exports passed · PDF-02/03/08 |
| I07 | Full-book conversion live state, cleanup, cancellation and stage capacity | Whole-book publication and final child cancellation/lease-loss controls passed; consumer adoption remains PDF-09 · PDF-09/10/11 |
| I08 | Source inventory/defaults, independent PDF reference anchoring and concrete acceptance journey selection | Source inventory, five-section scope and independent native reference inputs delivered; actual A/B/C/provider/evaluation remain PDF-10/11 · PDF-10/11 |
| I09 | Exact public API/package/weights/tokenizer/decoding pins, isolated runtime and sm120 attention/plugin/MTP | Resolved selected runtime: pinned public source, isolated Python3.12/vLLM0.26/Torch2.11/Transformers5.14.1; actual RTX5090 MTP/FA2 and whole-book requests passed · PDF-12/14 |
| I10 | Submitted-pixel, PDF CropBox/rotation and crop transform precision, including rotated OCR | Bounded independent CropBox/rotation/crop/normalization controls passed; mismatched frames remain unresolved, no fine glyph/cell precision claim · PDF-13/14/15 |
| I11 | Mapping/merge losses, table/chart/inline structure and selection policy over real responses | Mapping/selection mechanisms and real-response/bounded structure controls passed; cross-page continuity is explicitly not inferred, universal fidelity unqualified · PDF-13/15 |
| I12 | Bounded preparation, combined GPU lifetime, partial receipts/cancellation and replay | Partial: finite workers, raw replay and GPU phase controls passed;0060 passes the oversized aggregate cast, but attempt7 cancelled during correlated child validation.0061 shared set join has bounded controls only; deployment/whole-book publication remain PDF-10/11 obligations |
| I13 | Concrete integrated source/section/consumer/reference scope and independent benefit challenges | Scope fixed before provider execution: whole-book source, five intact analysis roots, two independent full-section A/B/C references and six frozen original-PDF challenges; actual journeys remain PDF-10/11 |
| I14 | Streaming review I01: exact native assembly/enrichment and remaining global state | Partial · exact pinned adapter, actual bounded native differential and retained1589-page record/IPC replay passed; operator selected materialized native global finalization. Strict end-to-end streaming remains open; no book-size graph-memory bound |
| I15 | Streaming review I02: total native schema lowering/reconstruction and oversized leaves | Foundation resolved · PDF-18 schema/codec and callback placement tested; frozen-union enforcement remains PDF-21 |
| I16 | Streaming review I03: independent native byte/record correspondence and batch-independent logical identity | Foundation resolved · PDF-19 bounded protocol/SQL parity/part replay tested; actual staged/native export correspondence remains PDF-20/21/24 |
| I17 | Streaming review I04: immutable freeze/validate/seal under cancellation, concurrency and lease change | Modeled append/freeze/native validation/seal/resume implemented; scoped actual PostgreSQL visibility, replay and heartbeat controls passed. Complete cancellation/crash/concurrency and integrated-book obligations remain PDF-21/25 |
| I18 | Streaming review I05: Arrow/pgpq/PostgreSQL/ADBC type and resource/operator profiles | Private COPY/IPC/DuckDB and published cursor/byte-field/export lifetimes implemented/scoped-tested. Current external/full-book integration remains PDF-24/25; pg_jsonschema0.3.4 compiles per row, so bounded schema-compilation amortization remains an execution improvement before book-scale acceptance |
| I19 | Streaming review I06: progressive section dependency closure and useful early consumer | Open investigation · PDF-17/26; optional capability, not a blocker for atomic-document acceptance |
| I20 | Improvement review I03: public pipelined scheduler versus completion-driven pages under exact receipt/crop/cancellation contracts | Resolved selected route · completion-driven finite page workers, versioned image/source recipe and exact existing raw/partial/zero-C custody. Public bounded-group orchestration lacks concurrency-safe observation hooks; future adoption requires that seam |

A known table-cell formula gap cannot disappear into a generic "unsupported" label while claiming
supported table-math completion. Implement the selected supported enrichment route if required;
otherwise keep that capability open with its evidence/remedy. Changing the selected document
pipeline requires an explicit revised decision, not an unrecorded fallback.

## 7. Conditional capabilities and exclusions

| Candidate | Current disposition | Revisit trigger / owner |
|---|---|---|
| Section chunking / HybridChunker | Not planned | Actual required consumer fails on an actual oversized section; future parts must be child groups under that section. |
| Additional OCR engines beyond selected composition | Conditional | Named unresolved precision need; PDF-12 assesses added value. Integrated reconciliation itself is selected PDF-13/15 scope. |
| Granite formula-stage preset | Conditional comparison | Demonstrated CodeFormulaV2 limitation; I02/I03, retains StandardPdfPipeline. |
| Nemotron3.5 true triple pass | Actual all-page recognition delivered; assembled adoption open | PDF-12–16 and RC06/07; MinerU/other whole-page VLM replacements remain alternatives for a demonstrated blocker. |
| RapidOCR medium/orientation retries | Conditional tuning | Observed difficult/rotated text; I02, no universal quality claim. |
| Nemotron chart recognition / other picture enrichment | Nemotron chart structure selected; extra description/code models deferred | PDF-15/16 map and consume charts; Standard chart enrichment only a bounded comparison if needed. |
| TableFormer V2 preview | Not baseline | Actual V1 structural limitation with evidence warranting comparison. |
| Native forms/raw glyph inventory | Deferred | Supported input/consumer requiring information absent from selected model. |
| New graph engine, Docling Serve/Jobkit/MCP | Not selected | Concrete operation cannot be served reasonably by current Core/native/local ownership. |
| Native Docling multipass substitution | Deferred | Required raw/image/HTTP/alternatives and failure hooks, or separately selected narrower contract; review I04 / PDF-23. |
| Additional code/picture/table/chart enrichment | Conditional | Selected technical-content consumer or demonstrated unresolved gap; PDF-22 lifetime/model first, PDF-23 comparison and PDF-24 real consumer migration. |
| Prepared-image/vLLM processor caching | Conditional | Exact Nemotron plugin support, recipe-qualified media identity, eviction/replay behavior and representative avoided work; PDF-23 / review I10. |
| Remote NIM/client, non-PDF intake, ASR, PII/translation and TikZ execution | Separate/deferred | Explicit workflow/value and required semantic/lifecycle decision; no automatic expansion of this series. |

## 8. Completion and current execution boundary

Completion now includes mandatory PDF-17–25 as well as PDF-12–16 and the single logical integrated
document contract. PDF-26 remains conditional; I19 must have an explicit disposition, not automatic
implementation. PDF-11 requires lossless native-field/byte reconstruction, identity across rebatching,
oversized-value support, native seal/visibility failure controls, selective readers and both streamed
exports over the retained book. A queue bound or compatible JSON cast alone is not streaming completion. PDF-11 must establish
whole-book integrated-source lifecycle accounting for all 1,589 pages, including explicit failures/
exclusions (reuse compatible retained Standard products), plus the scoped five-section knowledge journeys. Representative triple-pass probes alone
are not whole-book acceptance. No all-book agent extraction or universal source fidelity is required.
Original evidence below describes the pre-extension baseline, not integrated delivery.


Completion requires actual PDF producers, native custody/enforcement, intact hierarchy and migrated
math/domain/packet/interface consumers, operational PDF-only adoption and retired HTML entry paths.
PDF-11 owns the declared required qualification union; full-book source conversion and representative
end-to-end section journeys have distinct claims. No throughput, fidelity improvement, universal
formula coverage or all-section agent-extraction claim follows from source conversion alone.

Keep package-local checks targeted, integrated functional qualification at complete scope, and
independent fidelity assessment separate from pipeline correctness. Resolve substantial typing
issues at coherent endpoints. Applicable lint-only maintenance does not invalidate prior tests.
No grading-policy change, human grading or automatic historical re-anchoring is included.

**Current checkpoint (2026-11-01):** Source ABI17/relational compiler4/core0.6.4 includes
forward0065. Owned `corpus_pdf_20261031` remains0060/compiler14/core0.6.2;0061–0065 are
undeployed. `pg_jsonschema`0.3.4 is installed in the dedicated cluster templates and owned database,
with the existing extension version record/provisioner; this is not an application migration.
[ADR-0043](../adr/0043-segmented-artifact-byte-identity.md) separates verified byte identity from
optional export SHA; [ADR-0044](../adr/0044-native-pdf-metadata-jsonschema.md) governs native,
model-derived metadata validation without text substitution.

The targeted integrated union exercised121cases:117 passed initially; two stale current-helper
mutation assertions and two nonimportable spawn fixtures were repaired, and all four affected
controls passed. They are overlapping corrections, not125cases. Global warning-inclusive Pyrefly,
Ruff and scoped checks on the corrected fixtures passed. Full current `just test-all` is not_run;
the earlier0060 broad receipt retains its own scope. Actual whole-book native global replay passed,
and fresh pages20/1211 exercise current class-preserving replay and exact native raster scale.
See [publication/producer receipts](../design_review/evidence/2026-11-01_pdf-publication-adoption/README.md).

The retained exact558190320-byte witness parses and derives192verified computed grids across
107tables and85chart tables without changing supplied native cells or historical bytes. Its
migration driver is prepared but has not written products. Whole-book staged validation/seal,
current CLI/external MCP/render/export, five-section extraction, independent references/grading,
completed knowledge and default selection remain open. The inference service remains down;
all owned workers and native jobs are settled, and no auxiliary worktrees remain.

Source-ready run2/task2 retains native and organized Docling products for all 1,589 pages.
Run5/task7 retains the selected enrichment as `math-enriched`, digest
`8468df6fb3af853b1d0757b18facc7ecd2ff25fa301e8f4b8e05aa2930b6948d`.
It recovered 648 inline anchors and retains 36 source-qualified unresolved reports, with honest
partial scope coverage. Native word/crop order recovers punctuation and repeated contexts;
ambiguous cases preserve source geometry and diagnostics rather than invented offsets.

Run6 (`release:743bdc97c3a1390bca0e0485c9ccbc44fb1856495bc038d3b4b69bf5bbcccbdc`)
passed consumer source preparation over that exact enriched pin without another native inference
or a relabelled producer. Five analysis views and five direct ancestor-context views are selected;
M09/M11/M13 completed and five AgentOpus tasks await extraction. View role is included before
identity construction. Exact recipe/policy/scoped-coverage and existing-view custody guard reuse.
Native source CLI views/product reads passed. Current-run external MCP/render remains `not_run`.

Independent reference preparation for run6 passed and retains its own native frames, complete
source/schema/guideline inputs and original page images. No author A/B/C, extraction provider,
reference registration, grading or completed PDF result/default cutover is claimed. References
will annotate both selected reference sections fully; six frozen original-PDF facts separately
challenge source fidelity. Reference bytes and evaluator privileges do not enter extraction.

**Verification, 2026-11-01:** `just test-all` source-stable0060 baseline passed2643 Python tests/
10warnings (`20261101T042650Z-4190256`). Earlier failed/interrupted records and the2638-pass0059
baseline retain their exact outcomes.0060 bounded controls68 and20 passed; subsequent0061 focused
controls9 and final exact reproduction1 passed. Merged-main warning-inclusive `just types` and
`uv run ruff check .` passed. Zero listed Rust tests establish no Rust functional coverage.
`just docs-check` failed on existing parsing-profile/moved logging-library links; existing publisher
target resolution passed for the seven changed PDF/architecture/evidence pages. No cosmetic
formatting invalidates applicable passing type/test evidence. Whole-plan acceptance remains open.

**PDF-17–19 verification, 2026-11-01:** the final foundation/schema regression union passed
394tests/4warnings, including private native tables, record reconstruction, independent identity
vectors, archive compatibility and frozen forward-product reproduction. Warning-inclusive
`just types`, `uv run ruff check .` and `just model check` passed. Source core/system0.6.3 records
relational compiler3; deployed0060 retains core0.6.2.0061–0063 remain undeployed. The earlier
187-case union and five overlapping controls retain their scope and are not added to the394.
[Foundation receipts](../design_review/evidence/2026-11-01_pdf-record-foundations/README.md)
preserve initial failures, corrections and remaining producer/seal/consumer limits.

**Remaining execution:** Deploy reviewed0065 and its release, execute retained-book migration,
qualify actual integrated seal/read/export and the remaining failure/concurrency controls, then
complete PDF-10/11 adopted-result/default selection. Preserve
all retained raw/native products and old pins; reuse inference when recipes remain compatible.
PDF-10/11 still require exact current consumer views, real external interfaces, five-section
extraction, independent two-section references, the six frozen original-PDF challenges, automated
grading, resumed replay and complete final-source qualification. These obligations are extended,
not credited by document creation or silently duplicated in PDF-25. Defaults remain
`corpus_parsing_20261030` / `parsing-pipeline`; no audit-premise or grading-policy change is included.

## Plan-authoring verification — 2026-11-01

**Improvement integration, passed:** focused foundation/contract assessment and independent
coherence check; existing publisher discovery/staging, mdBook build and target resolution across
all10 changed plan/status pages (`build/pdf-improvement-plan-links.log`). Review I01–I11 each have
an explicit coordinator disposition, new I20 is unique and PDF-17–26 anchors remain intact.
No production source, migration, dependency or library-reference draft changed. Product/type/provider
and performance checks are **not_run** for this documentation-only amendment. Full `just docs-check`
was not rerun; its historical failures below are not new results. Optional models/caches and PDF-26
remain outside the initial required union. Plan completion does not establish their implementation.

**Earlier plan creation receipt (retained scope):**

**passed:** focused foundation/source assessment and independent obligation/dependency review;
existing publisher target resolution across all14 PDF/discovery plan pages, unique PDF-17–26
coordinator/technical anchors and I14–I19 presence (`build/pdf-stream-plans-links.log`).
**failed:** `just docs-check` on existing parsing-profile/logging links and source links affected
by concurrent PostgreSQL library-document moves outside this task (`build/pdf-stream-plans-docs.log`).
New/updated plan links use the current library locations; unrelated moves remain untouched.
**not_run:** product tests, inference, native migrations/publication, data conversion and provider
journeys: this amendment creates plans only. Prior product receipts retain their original scope.

## PDF-13 foundation verification — 2026-10-31

**Implemented and targeted-tested; not assembled/provider qualification.** Forward0056 adds the
model-derived common PDF identity/typed companion tables, protected publication and bounded evidence
readers. ADR-0039 delivers PDF-12's decision prerequisite; its runtime/mapping investigations remain
open at that foundation checkpoint. Its tests exercised isolated databases with the operational
deployment then at0055; later deployment and actual producer outcomes are reported above.

- **passed:** `uv run pytest tests/test_pdf_contracts.py python/corpus-structure/tests/semantic/test_native_documents.py python/corpus-structure/tests/semantic/test_archive_reader.py python/corpus-structure/tests/semantic/test_execution_release.py python/corpus-structure/tests/semantic/test_schema_product_cli.py python/corpus-structure/tests/semantic/test_migrations.py --disable-warnings --maxfail=2` — final 79 contract/native/archive/execution/authoring/migration tests; this supersedes the narrower 71-test receipt, not an additional disjoint count.
- **passed:** `uv run pytest python/corpus-structure/tests/semantic/test_pdf_integrated.py --report-log=build/test-receipts/pdf13/fifth.reportlog` — 32 tests including six real PostgreSQL cases; `build/test-receipts/pdf13/fifth.log` retains output. Earlier initial/second/third/fourth attempts remain failed receipts, not relabelled passes.
- **passed:** `just types` — global warning-inclusive Pyrefly after functional fixes; no suppressions added.
- **passed:** `just turn-end`, `uv run ruff check`, `just docs-check` and deterministic comparison of both frozen0056 SQL products. Frozen0047–0055 remain unchanged.
- **passed:** independent implementation review of contract, SQL, lineage, archive and bounded read invariants; no remaining material findings at reviewed boundary.
- **not_run:** Nemotron runtime/inference, provider geometry/fidelity, operational0056 deployment, all-consumer/default adoption and complete PDF-11 qualification. No broad test-all campaign was initiated for this bounded package.

The table-cell trace follows two recognition inputs and their exact provider/image/raw-response
metadata. Native payloads survive actual pre0056 migration/backfill/replay unchanged. Wrong source,
project, digest, endpoint and stale attempts refuse; partial coverage cannot become complete merely
by assertion. Publisher retains earlier failed-pass evidence and exact artifact-set replay. Original
PDF bytes are not retransmitted with each observation. Formatting does not invalidate unaffected
passing functional/type evidence.
