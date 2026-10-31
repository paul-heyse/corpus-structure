# PDF-only Docling pipeline

**Status:** Implementation integrated through native 0055. Whole-book source publication,
selected enrichment and exact retained-product consumer preparation have passed. Actual
provider extraction/reference grading, operational default selection and complete qualification
remain open. **Created:** 2026-10-31.
**Basis:** [functional review](../functional_reviews/pdf-docling-pipeline_2026-10-31.md) at
`2c333722fe9b3ad03c8004d14c5f50a1605c3f4b` and its [target model](../functional_reviews/pdf-docling-pipeline_2026-10-31_target-model.md).
This coordinator owns package state, scheduled O01–O08 dispositions and investigations I01–I08.
Supporting plans own their technical explanations, not duplicate execution queues.

## 1. Outcome and fixed boundaries

Replace active HTML ingestion with **PDF → StandardPdfPipeline → native DoclingDocument JSON
in PostgreSQL**, and migrate actual consumers to section-grounded source structure. The initial
original is `docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf`: 1,589 pages and
211,502,518 bytes per the source review. Retain original bytes, native document products,
conversion health and domain knowledge as separate connected meanings.

**No section chunking is planned.** Preserve intact sections/subsections. Bounded responses,
transport pages and native stage batches do not create semantic chunks. Upstream conversion
from other formats to PDF is outside this series. Optional model families, charts, OCR ensembles
and services are not silently selected because their schemas/APIs exist.

Docling owns its native versioned schema. LinkML/trusted execution definitions own application
operations, transitions, coverage, dependency recipes and cross-product/domain relationships.
PostgreSQL owns instance custody and native enforcement. Derive operation-shaped views from
native products rather than retain an HTML-shaped primary representation with attached JSON.

The standard is core 3.3 plus efficient-architecture heuristics 1.0 and applicable profile/binding
guidance. Apply qualitative execution fit before fixing physical representations. No broad audit,
new alignment lint, cost model, generic workflow engine or additional proof framework is introduced.

## 2. Baseline and foundation assessment

Production inspected at `5a6045f`; subsequent commits through `2c33372` changed review/handoff
content only. Compiler 11/profile 6/native 0046 and the completed PP-00–PP-10 implementation
remain the starting point. Their historical receipts are not PDF qualification.

Reuse `semantic/metadata.py`, `contracts.py`, `operations.py`, `parsing_products.py`, immutable
release/archive readers and existing protected publication. Preserve original byte custody,
attempt/source fences, replay, named dependencies, bounded read selection and independent grading.
Shared text layouts and scientific assessment remain useful **derived consumers**.

Replace foundation assumptions where necessary: `approved_implementations()` currently imports
HTML/source-capture; request demands rebuild macro artifacts; locators use whole-rendition text;
packets primarily expose sentences; native source frames bind canonical ranges. PDF identity,
geometry and rich context cannot be introduced only in an ingress wrapper. PDF-02/03/06–09 own
the structural changes through these actual consumers.

The source review checked tagged Docling 2.145.0/core 2.103.1 and installed SymPy 1.14.0 APIs.
Docling/Torch/OCR were absent from the project environment at that inspection. All corpus/model
behavior and exact dependency compatibility below remain **not_run** until PDF-01 execution.
Concurrent library overview drafts are inputs, not files owned by this plan-authoring change.

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
| <a id="PDF-10"></a>PDF-10 | [Adoption](pdf-docling-pipeline/adoption-and-retirement.md#PDF-10): PDF defaults, consumer cutover, HTML removal | Integrated PDF-03–09; I08 | Partial: HTML producers retired, statistics/toy inputs native PDF; completed PDF result/default selection open |
| <a id="PDF-11"></a>PDF-11 | [Acceptance](pdf-docling-pipeline/adoption-and-retirement.md#PDF-11): actual journeys and required-union evidence | Complete selected functional scope, PDF-10 | Incomplete: source/targeted controls passed; broad receipt failed/incomplete; provider/evaluation/current external journey and final union open |

Begin with PDF-00 and PDF-01's environment/corpus questions. PDF-02 can agree identity, geometry,
health and dependency slices while PDF-01 resolves native details. Final contract enforcement
consumes those results; prototype library conversions do not require deployed application tables.
PDF-03 storage and PDF-04 producer can develop against agreed contracts, then integrate through
PDF-09. Consumer design can use agreed shapes, but passing adoption requires actual stored
producers. Shared compiler/model/native files need one integrated editing owner when work is
assigned; package numbering is not a mandatory worker sequence or global barrier.

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
| [O08](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O08) | Explicit primary OCR; conditional verification | Delivered selected primary OCR in bounded scope · PDF-01/04/09 | Actual CPU ONNX OCR and CUDA model-stage reports, word/raster transforms and broken-layer controls; independent secondary verification remains conditional. |

## 6. Investigation queue

PDF-01 explains methods and decision consequences; this is the sole mutable investigation state.
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

A known table-cell formula gap cannot disappear into a generic "unsupported" label while claiming
supported table-math completion. Implement the selected supported enrichment route if required;
otherwise keep that capability open with its evidence/remedy. Changing the selected document
pipeline requires an explicit revised decision, not an unrecorded fallback.

## 7. Conditional capabilities and exclusions

| Candidate | Current disposition | Revisit trigger / owner |
|---|---|---|
| Section chunking / HybridChunker | Not planned | Actual required consumer fails on an actual oversized section; future parts must be child groups under that section. |
| Secondary OCR and reconciliation | Conditional, not ordinary conversion | Consequential unresolved region/value or selected precision-sensitive consumer; PDF-04/08 design the evidence if activated. |
| Granite formula-stage preset | Conditional comparison | Demonstrated CodeFormulaV2 limitation; I02/I03, retains StandardPdfPipeline. |
| MinerU / Nemotron Parse / whole-page VLM | Investigative alternatives, not selected production entry | Material unresolved selected-pipeline gap; revised recommendation/decision required. |
| RapidOCR medium/orientation retries | Conditional tuning | Observed difficult/rotated text; I02, no universal quality claim. |
| Chart/picture description/code enrichment | Deferred | Named consumer needing attributed information beyond retained objects/captions. |
| TableFormer V2 preview | Not baseline | Actual V1 structural limitation with evidence warranting comparison. |
| Native forms/raw glyph inventory | Deferred | Supported input/consumer requiring information absent from selected model. |
| New graph engine, Docling Serve/Jobkit/MCP | Not selected | Concrete operation cannot be served reasonably by current Core/native/local ownership. |

## 8. Completion and current execution boundary

Completion requires actual PDF producers, native custody/enforcement, intact hierarchy and migrated
math/domain/packet/interface consumers, operational PDF-only adoption and retired HTML entry paths.
PDF-11 owns the declared required qualification union; full-book source conversion and representative
end-to-end section journeys have distinct claims. No throughput, fidelity improvement, universal
formula coverage or all-section agent-extraction claim follows from source conversion alone.

Keep package-local checks targeted, integrated functional qualification at complete scope, and
independent fidelity assessment separate from pipeline correctness. Resolve substantial typing
issues at coherent endpoints. Applicable lint-only maintenance does not invalidate prior tests.
No grading-policy change, human grading or automatic historical re-anchoring is included.

**Current checkpoint (2026-10-31):** Native contracts/migrations through 0055 are integrated
and deployed to owned `corpus_pdf_20261031`. System/core revision 0.6.1 positively separates
historical enum projections from the current native SourceView vocabulary; frozen legacy D3
CHECKs/migrations remain unchanged. The public native enums and all admitted native inputs were
verified unchanged by that projection correction.

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

**Verification:** Global warning-inclusive typing and focused native/legacy/CLI/reuse controls
passed. The original broad `just test-all` receipt is failed/incomplete: eight failures were
repaired and all eight passed a fresh focused rerun; a grammar deadline case terminated the
session before complete reporting. Its bounded lazy-relation/deadline correction passed all 90 grammar/stage controls after
isolating the test-owned memo; final global types, Ruff and other closeout checks are recorded
in the adoption evidence. Zero listed Rust tests establish no Rust
functional coverage. Preserve original failures and bounded source/context applicability; no
full-plan qualification follows from these targeted results.

**Remaining execution:** prepare a compatible current consumer release from
`enriched-source-pin.json` after the final math adapter correction, reusing task7. Regenerate
independent reference inputs for that exact consumer; do not relabel run6 frames. Execute the
current external MCP/render journey, complete independent full-section A/B/C authoring before
actual five-section extraction, register/grade the completed result, then select it and adopt
PDF defaults. Finish the complete functional/provider/nonfunctional union and its evidence.
All agent processes have settled and no implementation worktrees remain. Passing type/test
receipts remain applicable across cosmetic maintenance; no grading policy or audit premise changed.
