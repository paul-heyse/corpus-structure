# PDF foundations and capability investigations

**Status:** Implemented mechanisms described below; the coordinator owns current qualification and adoption state.
The [coordinator](../pdf-docling-pipeline_2026-10-31.md) owns package state, review O01–O08
and investigation I01–I08 disposition. This document explains PDF-00/01, not a second queue.
Consumes the [functional review](../../functional_reviews/pdf-docling-pipeline_2026-10-31.md)
at `2c33372` and its [target model](../../functional_reviews/pdf-docling-pipeline_2026-10-31_target-model.md).

## Implemented foundation — 2026-10-31

ADR-0038 governs the selected PDF-only boundary. Installed Docling 2.145.0/core 2.105.0 and the
native validation schema 1.10.0 replace the review's earlier inspection baseline. Actual native,
raster, visible broken-layer and invisible-layer cases establish the selected local route.
CPU RapidOCR is explicit; CUDA execution is claimed only for the observed native model stages.
The complete original conversion is retained. Investigation conclusions and conditional features
remain owned by the coordinator; source conversion does not establish universal OCR fidelity.


## Foundation assessment

The existing semantic runtime already has immutable originals/products, a trusted finite
operation catalog, archived release reconstruction, attempt fencing and protected publication.
`semantic/contracts.py` currently admits HTML recognition/canonical projection implementations;
`ingest/html.py` and `sources/siegrist.yaml` encode DOM/CSS semantics. Those are actual replacement
surfaces, not a generic input-format switch. `semantic/parsing_products.py` can carry qualified
products, but its current integer-coordinate assumptions do not represent PDF geometry.

Retain the useful orchestration/storage contracts while changing their source semantics.
Native Docling JSON should become the document-structure product, with operation-shaped derived
views; do not retain an HTML-shaped primary rendition merely to avoid migrating consumers.
The target workload is one 1,589-page PDF, many intact sections and bounded item reads. One
original, conversion, page, section and analysis selection are different units. Their semantic
identity does not mandate a separate task, transaction or service for each.

Apply core 3.3, the efficiency heuristics and the applicable fidelity/relationship profile through
[standard.toml](../../design_review/design_principles/standard.toml). This focused foundation
assessment does not refresh a broad diagnostic audit or change historical audit premises.

<a id="PDF-00"></a>
## PDF-00 — Confirmed decisions and enduring architectural owners

**Owner:** architecture/model integration. **Inputs:** selected PDF-only outcome and the
operator's explicit acceptance of RC01–RC05 on 2026-10-31. **Output:** decision successors and
architectural clauses governing subsequent implementation, plus a concrete consumer/deletion map.
The confirmation is a planning decision, not evidence of implementation or new accepted ADRs.

| Review change | Confirmed target | Execution route |
|---|---|---|
| RC01 | Replace HTML5/DOM ingestion and CSS profiles with PDF-only StandardPdfPipeline. | Reconcile ADR-0036/0037 and D4/D6 source-operation owners; remove the obsolete active path during PDF-10. |
| RC02 | Distinguish original PDF bytes, PDF regions, recognized LaTeX and text-projection offsets. | Update D1 evidence and D3/D8 source-address clauses before dependent writes/read APIs. |
| RC03 | Version section units, packets/source frames and source APIs. | Update D4/D5/D8 consumer contracts; PDF-07/08 migrate the actual consumers. |
| RC04 | Docling owns its native schema; LinkML governs application behavior and cross-product relations. | Update D2/D3 authority and artifact-binding clauses alongside the governing decision. |
| RC05 | Replace/retire unnecessary parser stages and dependency bindings. | Update D4/D6 operation/demand recipes and implementation manifests; PDF-06/09/10 deliver migration. |

Read the current owning ADR clauses before choosing successors. Supersede affected accepted
records through the ADR workflow; never rewrite accepted rationale or preassign an ADR number.
Update enduring D1–D8 owners with the decision that changes their meaning. Preserve unaffected
release authority, consolidation ownership, independent automated evaluation and historical
source custody. Additional changes outside these confirmed outcomes need their own decision.

Inventory producer, storage, request, packet, placement, domain-query, CLI/MCP and export consumers.
Schedule each migration beside the replacement contract, with PDF-10 checking retirement coverage.
There is no new HTML-to-PDF renderer, section chunking, universal OCR arbitration service or
workflow engine in this target. If chunking is ever reconsidered after a demonstrated consumer
failure, parts must remain lower-level children of their original section; no chunking is built now.

**Acceptance:** changed rules have an accepted decision route and one enduring owner before
production consumers rely on them. The inventory identifies active code to replace versus minimal
archived-record decoding to preserve. This package does not claim PDF conversion or fidelity.

<a id="PDF-01"></a>
## PDF-01 — Resolve the consequential native-capability questions

**Owner:** PDF adapter/integration lead. **Inputs:** PDF-00 target, the retained Siegrist original,
review mechanisms and the early identity/health contract agreement from PDF-02. **Output:**
qualified mechanisms, actual limits and decisions consumed by later packages. This early agreement
is not deployed storage; do not require PDF-03 DDL merely to investigate a library capability.

Start from the [Docling reference](../../libraries/docling.md), [OCR technical-PDF guidance](../../libraries/docling_ocr.md),
Context7 and version-tagged upstream sources. Use representative actual pages/sections to resolve
real uncertainties. Probe artifacts belong under `docs/design_review/evidence/<date>_<topic>/`
with the existing evidence conventions. Do not add a new permanent probe framework or a general
benchmark campaign. Preserve failed/partial attempts and their precise input/model/configuration.

| Investigation | Evidence and decision to supply | Consumers constrained |
|---|---|---|
| I01 — Runtime and exact pins | Resolve full `docling` distribution with all operator-requested extras, matching core, Python 3.14 wheels, native dependencies and model revisions. Confirm actual ONNX provider and per-stage device. | PDF-04/09 dependency and execution binding. |
| I02 — Layout/formula composition | Compare `layout_heron_default` with `layout_egret_large` on dense equations, headings and formula-bearing tables; distinguish detection misses from transcription errors. | PDF-04 selected layout and recognition scope. |
| I03 — Formula health and coverage | Expose enrichment success versus caught failure/fallback; cover inline, display and ordinary table-cell math separately. Investigate supported cell-aware enrichment only for an actual gap. | PDF-04/06/07 health semantics and frontend retirement. |
| I04 — Hierarchy | Verify heading-level output versus actual section containers, reading order and section/subsection membership across pages. | PDF-05 grouping recipe and PDF-07 unit policy. |
| I05 — Native mathematics | Feed actual recognized LaTeX to SymPy Lark; cover sets, relations, binders, matrices, equation numbers, ambiguity and occurrence positioning. | PDF-06 retained native extensions and removed stages. |
| I06 — Schema, images and geometry | Roundtrip native JSON through its versioned schema; check reference integrity, validation normalization, coordinates, image references and source-region inspection needs. | PDF-02/03 contracts/layout and PDF-08 evidence reads. |
| I07 — Long-book lifetime | After representative cases, run a real full-book conversion and assess combined live state, retained formula backends, bounded queues, cancellation and cleanup. | PDF-09 capacity/lifetime choices and PDF-11 whole-book acceptance. |
| I08 — References and consumer cutover | Identify new PDF anchors and actual intact-section journeys; design independently authored/re-anchored evaluation inputs without changing historical grades or grading policy. | PDF-07/10/11 packet/evaluation/adoption scope. |

The coordinator owns the results and current dispositions. Each result names the tested source
universe, what it permits, remaining limitations and dependent work. A source-checked option
is not a corpus-tested configuration; sampled pages are not full-book completion.

### Mechanisms to preserve in the investigation result

For I01, use the full `docling` distribution with all ten requested extras, superseding the review’s minimal-package recommendation. The
review identifies unrelated Office/web dependencies and a `pylatexenc<3` interaction with the
current 3.0b2. Exact pins/lock changes belong to execution and move only the selected family.
Record model repository revisions/checkpoint identities, not an unqualified mutable `main`.

For I02/I03 use `LayoutObjectDetectionOptions.from_preset(...)` and
`CodeFormulaVlmOptions.from_preset("codeformulav2", scale=2.0,
expansion_factor=0.18, stop_on_repetition=True)`. Compare a margin such as `0.08` only where
neighboring equation numbers/text contaminate crops; check clipped formula parts as well as
repetition. `granite_docling` is a conditional formula-stage comparison, not another input route.

The tagged enrichment implementation catches inference exceptions and yields unchanged text;
label FORMULA, nonempty text and `text != orig` cannot certify success. Resolve an attributable
stage outcome through supported integration or retain explicit unknown. For ordinary table cells,
[issue #3828](https://github.com/docling-project/docling/issues/3828) identifies a specific producer
gap despite rich-cell representational capacity. If encountered, prefer native cell-to-formula
extension using existing regions; do not reverse-engineer two-dimensional math from garbled text.
`mineru2_pro`/Nemotron Parse remain investigative alternatives for material failures; switching
whole-document pipelines requires a revised decision, not a hidden fallback. Nemotron-OCR is a
different capability with a narrower runtime baseline.

For I04 enable `HeadingHierarchyOptions(enabled=True)`. In tagged 2.145.0 the heading-style
signal does not require full `generate_parsed_pages=True`; avoid unnecessary page retention.
A page-range result does not establish globally equivalent hierarchy or table continuation.
For I05 prefer `parse_latex(..., backend="lark")`/prepared `LarkLaTeXParser`; ANTLR's prefix
acceptance is not an equivalent fallback. Keep recognized-text offsets separate from PDF geometry.

### Completion and verification boundary

PDF-01 supplies the decisions needed by each dependent slice, not one global stop until every
investigation finishes. I07 depends on an actual integrated converter/lifetime route; it therefore
finishes with PDF-09 before PDF-11, rather than blocking initial contracts or local producer work.
I08 can identify reference/consumer obligations early while operational proof finishes later.

If a native capability fails, retain the gap and its dependent work; do not silently weaken the
required coverage, declare absence or preserve an unneeded old frontend indefinitely. Named
conditional alternatives need explicit evidence of value before implementation. No multi-engine
OCR voting, mandatory whole-book second pass, preview table model or chart extraction is selected.

**Acceptance:** applicable investigation results identify concrete APIs/configuration and support
limits, with input/source references and an actionable route for unresolved outcomes. Native
roundtrip and real consumer evidence remain separate from source inspection. Integration and
assembled qualification belong to PDF-03–11 and their owners, not to a probe's success label.

## Execution checkpoint — 2026-10-31

ADR-0038 supersedes0036/0037 and updates D1–D8/§B4/§B5 as accepted targets; the installed HTML
route remains explicitly retained until later migration. Early PDF-02 agreement is recorded in
the model/storage owner. [Foundation evidence](../../design_review/evidence/2026-10-31_pdf-docling-foundations/README.md)
owns actual native probe outcomes and failures. Coordinator I01–I08 rows retain remaining obligations.

Operator-selected installation (supersedes the minimal-package recommendation):

```sh
uv add "docling[asr,easyocr,htmlrender,ocrmac,onnxruntime,rapidocr,remote-serving,tesserocr,vlm,xbrl]"
```

Executed with an explicitly selected separately locked evidence project; application manifests and
locks are unchanged. Full model breadth is installed, not automatically selected for execution.
No application migration, default cutover, actual agent/evaluator run or full-book qualification
is established. Most sampled recognized strings require more than the default SymPy grammar;
retirement of the existing mathematical frontend remains conditional on PDF-06 qualification.
