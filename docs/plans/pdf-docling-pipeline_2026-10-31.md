# PDF-only Docling pipeline

**Status:** Active implementation and integration; PDF-00 delivered, native producer and
consumer contracts integrated through 0050. Book publication, assembled consumer qualification
and operational adoption remain open. **Created:** 2026-10-31.
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
| <a id="PDF-01"></a>PDF-01 | [Investigations](pdf-docling-pipeline/foundations-and-investigations.md#PDF-01): qualified library/runtime choices | Source PDF, review; early PDF-02 agreement where needed | Partial: bounded native probes; remaining integration open |
| <a id="PDF-02"></a>PDF-02 | [Model](pdf-docling-pipeline/model-contracts-and-storage.md#PDF-02): connected contracts and prepared ports | PDF-00; I03/04/06 before final producer contracts | Integrated: SourceView, native frames/addresses, runtime/cell/coverage contracts and explicit request demands; assembled finalization open |
| <a id="PDF-03"></a>PDF-03 | [Storage](pdf-docling-pipeline/model-contracts-and-storage.md#PDF-03): native JSON, derived access rows and integrity | Agreed PDF-02; I06 | Integrated through 0050: protected native publication, indexed items/regions/derivations/cells/coverage/runtime; bounded controls passed |
| <a id="PDF-04"></a>PDF-04 | [Conversion](pdf-docling-pipeline/conversion-and-document-hierarchy.md#PDF-04): PDF producer with explicit health | I01/02/03; relevant PDF-02 support | Integrated: offline pinned assets, native vector/font candidates and demanded cell/inline enrichment; whole-book envelope repair and qualification open |
| <a id="PDF-05"></a>PDF-05 | [Hierarchy](pdf-docling-pipeline/conversion-and-document-hierarchy.md#PDF-05): intact sections and qualified views | PDF-04, PDF-02, I04; PDF-03 for persistence | Integrated: intact grouping, direct/descendant SourceViews and per-view coverage; actual whole-book hierarchy qualification open |
| <a id="PDF-06"></a>PDF-06 | [Math](pdf-docling-pipeline/interpretation-and-domain-consumers.md#PDF-06): direct formula input and lazy M09/M11 | PDF-04/05, I03/05 | Integrated: M09 retained interpretation, M11 hydration without reparsing, demand-specific scientific questions; native controls passed |
| <a id="PDF-07"></a>PDF-07 | [Consumers](pdf-docling-pipeline/interpretation-and-domain-consumers.md#PDF-07): M13/domain recognition and rich packets | PDF-05, agreed PDF-06 states and PDF-02 frame contract | Integrated: M13 ancestry dependencies, native packets/frames, policy queue and exact piece aliases; finalization/reference journey open |
| <a id="PDF-08"></a>PDF-08 | [Interfaces](pdf-docling-pipeline/source-interfaces-and-runtime.md#PDF-08): typed CLI/MCP, placement and exports | PDF-03/05; PDF-06/07 for their views | Integrated: typed CLI/MCP selectors, render demands and streaming exports; actual adopted-source external journeys open |
| <a id="PDF-09"></a>PDF-09 | [Runtime](pdf-docling-pipeline/source-interfaces-and-runtime.md#PDF-09): owned conversion lifecycle and publication | PDF-02/03/04; I07 before adoption | Integrated: retained originals, exact adoption pins, cleanup and source-ready requests; first book publication failed, repair/retry open |
| <a id="PDF-10"></a>PDF-10 | [Adoption](pdf-docling-pipeline/adoption-and-retirement.md#PDF-10): PDF defaults, consumer cutover, HTML removal | Integrated PDF-03–09; I08 | Partial: active HTML producer removed and archived inputs retained; completed PDF selection/defaults open |
| <a id="PDF-11"></a>PDF-11 | [Acceptance](pdf-docling-pipeline/adoption-and-retirement.md#PDF-11): actual journeys and required-union evidence | Complete selected functional scope, PDF-10 | In progress: bounded controls passed; full-book publication, actual extraction/evaluation and complete required union open |

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
| [O01](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O01) | PDF adapter and health | Open · PDF-01/02/04/09 | Actual conversion distinguishes partial/failure and enrichment health; restricted publication. |
| [O02](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O02) | Native custody, scoped schema and indexed projections | Open · PDF-02/03/08 | Native JSON reload, source custody, relational endpoint integrity and bounded real reads. |
| [O03](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O03) | Sections/subsections without chunking | Open · PDF-01/05/07 | Actual hierarchy and ordered membership; packet/selection uses intact structure. |
| [O04](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O04) | Formula items into lazy math | Open · PDF-01/04/06 | Detected/inline/table coverage, native input compatibility, occurrence identity and honest uncertainty. |
| [O05](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O05) | Real domain and packet consumers | Open · PDF-05/06/07 | Rich context enters packet/source-frame identity, scope and consolidation; no CSS truth substitution. |
| [O06](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O06) | Structural placement and serving | Open · PDF-08/11 | Real CLI/MCP, direct item/cell citations and source-qualified exports. |
| [O07](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O07) | Book-scale lifecycle and retirement | Open · PDF-01/09/10/11 | Full-book source feasibility, reusable products, no active HTML route and historical read. |
| [O08](../functional_reviews/pdf-docling-pipeline_2026-10-31.md#O08) | Explicit primary OCR; conditional verification | Open · PDF-01/04/09 | Actual selected provider/recipe and recovery behavior; optional verification dispositions below. |

## 6. Investigation queue

PDF-01 explains methods and decision consequences; this is the sole mutable investigation state.
Each result names source scope, conclusion, limits and affected package; evidence uses existing
repository records when a probe produces an accepted result. No new permanent capability register.

| ID | Question and necessary output | State / constrains |
|---|---|---|
| I01 | Exact PDF-only extras, Python 3.14/runtime/model compatibility and actual per-stage providers | Partial: full installation/native runs; actual OCR CUDA and offline replay open · PDF-04/09 |
| I02 | Heron versus Egret Large region detection; crop/repetition settings and chosen recipe | Bounded comparison delivered: retain Heron; no measured quality improvement · PDF-04 |
| I03 | Attributable formula health; inline and table-cell coverage; supported rich-cell enrichment route if necessary | Partial: fallback/table gap confirmed; native cell extension prototype; production health/coverage open · PDF-02/04/06/07 |
| I04 | Heading levels versus actual section groups; ordered intact hierarchy and descendant-selection semantics | Mechanism delivered: derived groups preserve refs/order; semantic heading fidelity remains PDF-05/07 · PDF-02/05/07 |
| I05 | Native SymPy compatibility on real recognized formulas; smallest required grammar/occurrence gap | Compatibility gap identified: native default grammar insufficient; PDF-06 remedy/qualification open · PDF-06 |
| I06 | JSON/schema roundtrip, validation mutation, image custody and native/region address precision | Bounded native/schema/JSONB probe passed; protected application publication remains PDF-03 · PDF-02/03/08 |
| I07 | Full-book conversion live state, cleanup, cancellation and stage capacity | Partial: representative lifecycle only; full-book/cancellation qualification with PDF-09 · PDF-09/10/11 |
| I08 | Source inventory/defaults, independent PDF reference anchoring and concrete acceptance journey selection | Migration/split decisions delivered; actual anchors/provider/evaluation remain PDF-10/11 · PDF-10/11 |

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

**Current checkpoint (2026-10-31):** Native source and consumer implementation is integrated
through 0051; the owned operational PDF database is at 0050 while whole-book source run 2
performs private inference. Its original and recipe are committed before conversion. Run 1
remains failed at optional application-envelope validation, with its original log retained in
[adoption evidence](../design_review/evidence/2026-10-31_pdf-adoption/README.md).
The repaired adapter omits absent optional wire fields and prepares minimal native capture
before organization/application metadata. Actual page85 raw/full preparation and protected
publication/failed-result retention controls passed; these are bounded source/publication claims.

Immutable SourceViews, exact product adoption, native M09/M11/M13, policy queueing, source
frames, CLI/MCP reads, demanded rendering and JSONL/Parquet/complete Docling JSON exports are
implemented. Model revision 0.6.0 supplies SourceView enum authority. Native source observations
carry actual unit pins. Sentence preparation and packets use explicit admitted configuration.
The statistics scope uses five maximal intact descendant sections; context-only ancestor views
are separate. No section chunks or active HTML producer remain. HTML-only direct dependency
html5lib is development-only for archived fixtures; actual old outputs remain readable.

The assembled journey exposed native finalization and independent-reference anchor issues:
0051 admits qualified native citations at finalization. The remaining 0052 work retains complete
independent reference frames and qualified ancestor sources, so reference normalization uses its
own frame and direct-child context premises remain citable in ancestor coordinates. PDF-09 also
closes the concrete native-thread cancellation exposure through one owned serial process, keeping
private inference outside database publication and preserving exact task fences. These are
preservation obligations in the current scope, not exceptions or relaxed grading requirements.

**Verification (2026-10-31):** warning-inclusive global `just types` passed at the integrated
producer/configuration endpoint; scoped subsequent typing controls passed. Native publication,
SourceView, request, math, packet/registry, export and archived-read controls passed within their
recorded selections. The actual policy/MCP/consolidation/reference-storage journey reaches
grading; its reference-anchor mismatch is still being repaired, so no assembled grading pass is
claimed. The original failed/interrupted records remain. Complete `just test-all`, applicable
hygiene, actual provider extraction/evaluation and PDF default adoption remain open. Lint-only
maintenance does not invalidate unaffected type/test results.

**Next:** finish qualified ancestor/reference-frame custody and owned worker cancellation,
integrate their actual consumer controls, publish/reuse the whole-book source result, then run
actual five-section extraction, independent automated evaluation, CLI/external MCP and exports.
Select the completed PDF result and update defaults only after those journeys, then close the
required functional/provider/nonfunctional union and final documentation/worktrees.
