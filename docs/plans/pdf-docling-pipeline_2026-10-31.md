# Integrated PDF/Docling and Nemotron pipeline

**Status:** Active; native deployment through 0058, integrated producers/selection/readers implemented.
Whole-book recognition passed; integrated publication, actual consumer adoption and complete qualification remain open.
**Created/revised:** 2026-10-31.
**Basis:** Original [PDF review](../functional_reviews/pdf-docling-pipeline_2026-10-31.md)
at `2c333722fe9b3ad03c8004d14c5f50a1605c3f4b` and its target; added
[triple-pass review](../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md) and
[integrated target](../functional_reviews/docling-nemotron-triple-pass_2026-10-31_target-model.md)
at `d25fff8`. This coordinator alone owns package state, source-qualified opportunity dispositions
and investigations I01–I13. Supporting documents own technical explanations, not duplicate queues.

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

## 2. Baseline and foundation assessment

The current execution baseline deploys native0060 with compiler14/core0.6.2, full
Docling2.145.0/core2.105.0 and native schema1.10.0. Integrated producers, governed selection,
scoped readers and forward-only consumers are implemented. Actual all-page Nemotron recognition
and fresh composed toy publication passed; whole-book integrated publication and assembled
consumer/evaluator adoption remain separate acceptance obligations. Prior PP/PDF receipts retain
their original scope; no source result is relabelled as knowledge or fidelity qualification.

Reuse trusted release/compiler preparation, Core metadata, original/native custody, protected
publication, finite worker ownership, selected SourceViews and lazy scientific consumers. Material
extensions are multi-input lineage (currently one parent), raw partial-response custody, executable
integration policy, combined resource lifetimes and consumer selection/evidence reachability.
PDF-13 migrates the foundation rather than attaching unconnected NVIDIA JSON to the old reader.

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
| <a id="PDF-10"></a>PDF-10 | [Adoption](pdf-docling-pipeline/adoption-and-retirement.md#PDF-10): PDF defaults, consumer cutover, HTML removal | Integrated PDF-03–09 and PDF-13–16; I08/I13 | Partial: HTML producers retired, statistics/toy inputs native PDF; completed PDF result/default selection open |
| <a id="PDF-11"></a>PDF-11 | [Acceptance](pdf-docling-pipeline/adoption-and-retirement.md#PDF-11): actual journeys and required-union evidence | Complete selected functional scope, PDF-10 | Incomplete:0060 functional baseline2643passed; committed0061 has focused verification only; whole-book publication, actual provider/evaluation/current external journeys and final-source union remain open |
| <a id="PDF-12"></a>PDF-12 | [Foundations](pdf-docling-pipeline/foundations-and-investigations.md#PDF-12): successor decision and consequential feasibility | RC06/07 and current source | ADR-0039 delivered; isolated actual runtime, transforms and bounded mapping controls passed; corpus benefit remains separately assessed |
| <a id="PDF-13"></a>PDF-13 | [Integrated model](pdf-docling-pipeline/integrated-document-model-and-lineage.md#PDF-13): connected contract/storage, multi-input lineage | PDF-12 decision route; I10/11 for affected final constraints | Implemented foundation; targeted verification below; provider precision remains gated |
| <a id="PDF-14"></a>PDF-14 | [Triple recognition](pdf-docling-pipeline/triple-pass-recognition-and-reconciliation.md#PDF-14): owned public parser and retained request outcomes | I09 pins/runtime; PDF-13 observation/publication slice; I10 for grounded use | Implemented; actual full-book A/B/C recognition passed with retained primary failures and two named recoveries; assembled publication remains PDF-10/11 |
| <a id="PDF-15"></a>PDF-15 | [Integration](pdf-docling-pipeline/triple-pass-recognition-and-reconciliation.md#PDF-15): mapped rich content, correspondence and governed selection | Working PDF-13/14; I10/11 | Implemented and targeted-tested; ADR-0041/0060 bypasses the relation-array JSONB limit;0061 set-join child validation is committed/undeployed; actual whole-book acceptance remains open |
| <a id="PDF-16"></a>PDF-16 | [Consumers](pdf-docling-pipeline/integrated-document-consumers.md#PDF-16): singular reader, scientific/extraction/interface/evidence migration | Agreed PDF-13 for design; working PDF-15 for acceptance | Implemented; current external/provider/evaluator journeys remain PDF-10/11 |

**Current sequence:** PDF-12 decisions/feasibility and early PDF-13 contract design can advance
independently. Final runtime pins and transforms constrain the affected executable boundaries,
not all model reasoning. PDF-14 consumes an admitted observation/artifact slice, then PDF-15 publishes
the selected integrated product and PDF-16 migrates real consumers. PDF-10/11 finish deployment,
actual provider/reference journeys and qualification for this target. Do not first finish an obsolete
Standard-only extraction/grading journey. Original PDF-00–09 delivery claims remain scoped to the
baseline, with extension obligations in PDF-12–16; no prior receipt is erased or globally invalidated.
Shared compiler/schema/native files need one integrated editing owner; package numbers are not a
mandatory worker sequence. PDF-13–16 mechanisms are implemented. PDF-10/11 still own assembled publication, actual consumer/reference journeys, adoption and the required qualification union. See the current [integrated evidence](../design_review/evidence/2026-10-31_pdf-integrated-adoption/README.md).

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
| Nemotron3.5 true triple pass | Selected target, not deployed | PDF-12–16 and RC06/07; MinerU/other whole-page VLM replacements remain alternatives for a demonstrated blocker. |
| RapidOCR medium/orientation retries | Conditional tuning | Observed difficult/rotated text; I02, no universal quality claim. |
| Nemotron chart recognition / other picture enrichment | Nemotron chart structure selected; extra description/code models deferred | PDF-15/16 map and consume charts; Standard chart enrichment only a bounded comparison if needed. |
| TableFormer V2 preview | Not baseline | Actual V1 structural limitation with evidence warranting comparison. |
| Native forms/raw glyph inventory | Deferred | Supported input/consumer requiring information absent from selected model. |
| New graph engine, Docling Serve/Jobkit/MCP | Not selected | Concrete operation cannot be served reasonably by current Core/native/local ownership. |

## 8. Completion and current execution boundary

Completion now includes PDF-12–16 and the single integrated document contract. PDF-11 must establish
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

**Current checkpoint (2026-11-01):** Native contracts/migrations through0060 are integrated
and deployed to owned `corpus_pdf_20261031`, with compiler14/core0.6.2. Committed0061 is undeployed.
Actual recognition covers every original page; attempt7 passed0060's JSON-text admission cast
but was cancelled during native child validation. No integrated book product committed or result
was selected.0061's shared child-edge set join has focused verification, not book-scale acceptance.
All owned processes/tasks are concluded and worktrees removed. Exact raw recognition and prepared
replay remain retained; the dedicated inference service is down with its model/environment retained.

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

**Remaining execution:** review the JSONB publication/child-validation evidence and committed0061
before further deployment and normal cached book preparation. PDF-14–16 mechanisms are implemented;
whole-book integrated publication and PDF-10/11 assembled acceptance remain incomplete. Generate
consumer views and independent frames for their exact integrated selection; do not relabel run6.
Reference-author passes A/B/C are independent full-section authoring,
not Nemotron parse/detect/crop roles. Complete actual external MCP/render, five-section provider
extraction, reference registration/grading, replay and completed-result/default selection through
PDF-10/11, then the declared qualification union. Old missing acceptance remains missing; applicable
passed type/test evidence survives unaffected cosmetic changes. Operational defaults remain
`corpus_parsing_20261030` / `parsing-pipeline`. No grading-policy or audit-premise update is included.

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
