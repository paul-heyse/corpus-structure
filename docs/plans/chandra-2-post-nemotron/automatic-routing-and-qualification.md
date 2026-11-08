# Automatic routing and qualification

**Proposed target · 2026-11-08.** Companion to the [Chandra coordinator](../chandra-2-post-nemotron_2026-11-08.md).
This work turns the operating-policy investigation in [CH-07](specialist-extensions-and-scale.md#CH-07)
into a release-scoped routing and qualification package.

<a id="CH-10"></a>
## CH-10 · Select and qualify automatic post-Nemotron work

### Evaluation and requests

Run the evaluator against one exact, published integrated PDF and its admitted Standard and
Nemotron dependencies. Produce a versioned decision per physical page and requested capability.
Record the scope, reason and input references, including when an incumbent repair suffices, a page
is skipped, or coverage is unknown. A successful parse, an absent row, and a verified blank have
different meanings. Use these rules in order and coalesce reasons for the same effective request.

| Observed condition | Target action |
| --- | --- |
| Required text, a region, or a typed value is absent from the selected view, but retained native or A/C evidence supplies it with a qualified locator | Nominate the earliest supported repair to CH-08. Re-evaluate coverage after the repair. |
| Retained scoped coverage identifies an actual omission, limit, failure or incomplete reading on a usable published baseline | Request Chandra for the unresolved scope if the same recipe has no reusable result. Generic Nemotron partial coverage alone is too broad to trigger. If no integrated baseline exists, use incumbent ingest recovery. |
| A located source or layout cue indicates an unresolved typed need | Request Chandra for an unrepresented table header path, caption/panel association, mathematical region, or demanded picture field. A/B/C agreement on text does not settle structure. B can nominate a region from its retained layout response and recorded C crop decision. Its mapped document is intentionally empty. |
| Located readings disagree in a consequential cell, symbol, layout relation, or figure field and the incumbent cannot settle it | Request a Chandra reading as additional evidence. Geometry, parser validity and similarity rank candidates. They confer no admission authority. |
| A page has source-qualified blank body or the required content and structure are covered | Skip, with a distinct blank or covered reason. Include eligible skipped pages in a fixed, stratified qualification sample. A running header is compatible with a blank body. |

Use the Standard page candidate inventory, OCR regions, qualified word/glyph and drawing
geometry, admitted request pins and comparison reports. Native
`DoclingParsePageBackend.has_content_in` can help nominate a region if the backend and
frame are qualified. A negative return on an invalid or unassessed backend is insufficient. Preserve unassessed values. The existing
inventory can collapse null counts to zero and its vector flag indicates API availability.
Expose a narrow page-scoped read where these distinctions are lost. Avoid treating an empty B
mapping, a deliberately unrequested C crop, or an unsupported item as proof of absence.
The evaluator consumes published evidence and the release's requested feature scope. It does
not create a new layout model or a corpus-wide all-item match.
[Standard candidate inventory](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_candidates.py) ·
[Recognition and retained crop decisions](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_recognition.py) ·
[Mapper and reconciliation reports](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_reconciliation.py)

Use a whole page for reading order, hierarchy, shared captions, and missing items without an
addressable enclosing region. Use an existing pointer and region index for local detail, and a
quarter-turn crop only when source orientation or line direction warrants it. Retain a full-page
result when a crop discards necessary context. A higher-detail render is a separate, bounded
recipe. The current renderer crops a fixed 2× page and rotation adds no resolution. First verify
effective detail after processor resizing, inverse mapping and cost. Keep arbitrary source-region
requests outside this slice until a protected region selector is needed and specified.
[Current visual selector](../../../python/corpus-structure/src/corpus_structure/semantic/visual_requests.py) ·
[Renderer and transform](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_visual_mapping.py) ·
[Preset](https://github.com/docling-project/docling/blob/v2.148.0/docling/datamodel/stage_model_specs.py) ·
[Native image normalization for comparison](https://github.com/datalab-to/chandra/blob/v0.2.0/chandra/model/util.py) ·
[Pinned checkpoint processor](https://huggingface.co/datalab-to/chandra-ocr-2/blob/af93b47dba1b47b6640c86ccf487ed2260ab9a09/preprocessor_config.json) ·
[Docling Parse occupancy query](https://github.com/docling-project/docling/blob/v2.148.0/docling/backend/docling_parse_backend.py#L206-L218)

### Managed execution and visibility

Add the automatic route after ordinary publication. Use the existing managed run/task/attempt
and shared PDF GPU lease. A bounded group can amortize model load. Each member keeps its own
exact source, page or crop, frame, provider and decode identity, retained raw result, mapped
pin and outcome. Preserve scope per task for a multi-selection run. The singleton CLI
request currently stores scope in run options and is insufficient as a batch custody contract.
Keep one canonical pending demand per source and request key in the managed run. The GPU
lease serializes capacity and exact twin reuse only covers settled results. Keep policy reasons
separate from the inference key so a rules-only change can reuse the exact observation. Replay raw when only the parser changes. Keep exact replay tied to its original
source and request scope. Any cross-revision reuse requires explicitly checking and recording
scope equivalence under the new selection.

Keep preparation outside protected publication, bound buffered images and outstanding requests,
and release GPU ownership between bounded groups so the incumbent routes can progress. Local
Docling `VlmConvertModel.process_images` with pinned Transformers BF16 remains the reference.
Its Transformers `predict_batch` reads generation and processor settings from the first
input. Batch only homogeneous recipes, check one returned result per submitted frame and
compare single-image and grouped output and completion handling before adopting batching.
Keep unknown stops explicit. Prove ordinary batching under that binding before vLLM or MTP. Expose grouped
progress and individual failures through the managed result and an exact source-scoped
observation manifest. Read that manifest through CH-09. Retain successes and refusals on
interruption. Resume unsettled members under the existing fences without duplicating admitted
requests. Enforce explicit cancellation, page/frame bounds and provider failure handling
without a fixed deadline for the complete document. Resolve the relevant CH-02 F03 same-run
adoption, active cancellation and GPU handoff obligations before making those runtime claims
or enabling automatic work.
[Docling VLM stage](https://github.com/docling-project/docling/blob/v2.148.0/docling/models/stages/vlm_convert/vlm_convert_model.py) ·
[Transformers batch and stop contract](https://github.com/docling-project/docling/blob/v2.148.0/docling/models/inference_engines/vlm/transformers_engine.py#L447-L643) ·
[Shared GPU lease](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_capacity.py) ·
[CH-02 custody and recovery](recognition-and-observation-custody.md#CH-02)

### First qualification and operating decision

1. Freeze the original, the published incumbent and incumbent-only repair policy, router version,
   reason semantics, per-arm scope, and independent adjudication instructions. Run dry decisions
   over all 518 physical book pages using the archived inputs. Include a mixed cohort of
   born-digital and scanned material, dense or sideways tables, multi-column or multi-script
   pages, figures and flowcharts. Include natural specimens for any specialist capability under
   consideration and identify unavailable classes explicitly. Keep known development examples
   separate from the held-out observations used to choose activation.
2. Obtain a full-page Chandra observation or exact same-recipe reuse on each book page and
   cohort page for the all-page shadow arm. Run nominated crop variants only when the
   selective arm calls for them. Compare incumbent-only repair, explicit known requests,
   automatic selection, and all-page shadow using matched observations wherever possible.
   Include independent source checks of material candidate changes, known negatives, and a
   deterministic sample stratified by source family and structural demand, with unflagged
   and model-agreement pages represented. Freeze that sample before examining Chandra. Report remaining
   unadjudicated pages separately from verified negatives. Complete inference coverage does
   not imply independent content review of every page.
3. For each capability report independently supported additions and corrections, known
   missed opportunities, rejected or unresolved proposals, harmful changes that a proposed
   admission rule would have allowed, and what the intended consumer can actually use.
   Separate “router skipped”, “pass failed”, “parser lost”, “candidate wrong” and
   “witness unavailable”. Record observed work and failure boundaries for the shared GPU,
   including request count, reuse, setup, active inference, and interference with incumbent
   work. Vendor figures and the original 20-case panel are outside this workload measurement.
4. Select **automatic selective** when it captures the material gains and the remaining
   misses do not justify all-page work. Select **all-page** only if independently verified
   useful changes on unflagged pages are materially missed by feasible cheaper cues and
   the same GPU/recovery contract fits the workload. Retain **explicit** if the evidence
   or operational prerequisites are insufficient. Withhold any policy that enables a
   harmful source change on the protected controls. Record one policy and its actual
   qualified capability scope in the coordinator. Qualification is shadow-only.
   Default activation is a separate release-scoped effect after the decision, with the
   explicit route available and an operator rollback to explicit mode. Source promotion
   remains separately governed by CH-08 and CH-11.

Acceptance includes repeatable decisions from identical archived inputs, skipped clean and
blank controls, pages 4 and 119 with inline locations on their parents, missing typed
content on an otherwise clean page, an empty B mapping with retained layout, a no-baseline
refusal, and wrong-source and crop scope rejection. Verify reusable raw after a policy change,
concurrent deduplication, interruption after one successful group member, and a rotated
CropBox control distinct from p509's extra crop rotation. Verify the
ordinary published result remains readable while shadow work runs. Use targeted
`uv run ci test -- PATH…` and managed development journeys on the actual runtime before the
combined qualification. [Book and cohort baseline](../next-corpus-enrichment_2026-11-07.md#full-book-execution) ·
[Prior runtime observations](../../design_review/evidence/2026-11-08_chandra-execution/README.md)
