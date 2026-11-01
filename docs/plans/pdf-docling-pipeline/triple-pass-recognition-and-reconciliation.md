# Triple-pass recognition and integrated content selection

**Status:** Implemented and targeted-tested; actual full-book recognition passed. Integrated publication and independent quality assessment remain in the coordinator. **2026-10-31.**
[Coordinator](../pdf-docling-pipeline_2026-10-31.md) owns current state and investigations.
Consumes the [review](../../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md)
O01/O03/O04/O05/O06 and its target at `d25fff8`. PDF-13 owns shared contracts;
PDF-16 owns downstream migration. Native StandardPdfPipeline/RapidOCR remains one attributed route.

## Implemented mechanisms — 2026-10-31

The owned producer uses public union crops, finite page workers and streamed fenced retention of
submitted images, raw text, full HTTP responses and decisions. The isolated runtime preserves the
root full-Docling environment. Native GPU work releases its owned child before Nemotron wakes;
retained Standard or integrated pins reuse exactly the requested product.

Selection maps rich table/chart/caption/inline structures through Docling, normalizes headings once
across the document and preserves intact sections. Sparse page/geometry candidates and RapidFuzz
supply comparisons; the archived policy explicitly requests lexical comparison for keep/add/replace
or unresolved alternatives. Positioned parsing and SymPy remain explicit stronger demands, avoiding
unconsumed symbolic work during integration. Bulk typed-reference removal replaces the pinned
library's quadratic deletion path while preserving surviving identity and validating the Docling tree.
Coarse inherited evidence stays coarse; selected cells do not acquire invented fine boxes.

[Integrated evidence](../../design_review/evidence/2026-10-31_pdf-integrated-adoption/README.md)
retains actual recognition and bounded mapping/publication controls, original failures and recoveries.
Whole-book integrated publication and independent knowledge/source assessment remain distinct obligations.

## Foundation and selected realization

Use the complete public NVIDIA multipass capability, not a port of the ParseBench scheduler and
merge helpers. Docling's `nemotron_parse_v3_5` preset is single-pass and is not an equivalent route.
The public API/source was inspected at revision `4035ffb1d8f8bafcdb867dfaf6f7514f101464f9`,
package `nemotron-parse` 3.5.0.post7; this is a research baseline, not a qualified weight/runtime pin.
I09 selects exact executable pins before dependent runtime integration.

Keep application interpretation separate from upstream provider merging. Public
`merge_policy="alternatives"` preserves competing structural readings; it does not select the
repository's authoritative consumer text. The benchmark's best-alternative table selection cannot
establish the quality of a single selected transcription. A/B/C share one model family, not three
independent votes.

<a id="PDF-14"></a>
## PDF-14 — Owned true triple-pass recognition and retained observations

**Inputs:** PDF-12 decision/pin results, PDF-13 observation/receipt contract and protected artifact
admission slice; I10 transforms before grounded use. **Output:** real A/B/C observations and useful
partial/failure receipts under the current method/attempt ownership, reusable without another inference.

Use `nemotron_parse.inference.DocumentParser.parse_triple(image, triple_regions="union")`.
A parses the full page; B separately detects layout; C reparses retained Table/Chart crops from the
union of detector/parser boxes. A valid page may have no crop requests. Use explicit triple mode
on `parse_many`/`parse_prepared`; `prepare` amortizes image preparation only within its valid recipe.
Raw output must preserve coordinate/class tokens (`skip_special_tokens=False`). Effective parameters,
model revision and actual response model identity are retained, not inferred from endpoint name.

Public HTTP `parse_many` eagerly prepares all supplied inputs: bound input page batches or use finite
page calls. Request concurrency alone does not bound decoded pixels/encoded images. Delegate internal
crop scheduling to NVIDIA, constrained by operation-wide page/crop capacity; do not create a DB task
per request. Render each admitted page at a declared frame and reuse it for crops where supported.
Retain exact submitted bytes or a reconstruction contract that actually reproduces them.

Use a narrow recording backend `backend(image, *, prompt, stage, settings)` or an observed supplied
client. Record successful and failed request evidence before later stages fail: default HTTP handling
retains raw text/finish reason/usage but drops other fields, and later exceptions can omit successful
earlier stages from the returned result. Preserve raw coordinates/classes, crop IDs, selected regions,
render transforms and normalization/omission dispositions. Retain full logprobs only for a named
consumer; lack of logprobs does not block semantic validity. Do not rebuild the entire parser to add
receipts. If its public seam cannot retain required decisions, document the precise gap and the
smallest adapter/upstream change; counters alone are not complete decision provenance.

Use a pinned isolated environment for NVIDIA parser and serving, a finite DB-free controller worker
and local external vLLM. Extend the current environment-aware launch/lifecycle seam as necessary;
no permanent HTTP controller or second workflow engine is required. Root Torch2.15/Transformers5.22.1
are outside the researched package bounds, so do not downgrade Docling's root environment. Preserve
full Docling extras. Review remote code before trust and retain immutable code/weights/tokenizer pins.

I09 verifies RTX5090 startup, effective attention backend and MTP. vLLM0.26's Blackwell fallback is
source evidence, not local runtime success. If MTP blocks execution, investigate a non-speculative
recipe explicitly; do not silently substitute it or claim vendor parity. Initially phase GPU use
across native CUDA, Nemotron and other model services through the existing capacity owner. No nested
independent pools, connections across process boundaries or transaction held during inference.
Cancellation drains/terminates owned work, retains receipts and prevents stale publication.

**Targeted acceptance:** actual A/B/C with and without crops; capped/truncated/unknown-class results;
later crop failure preserves prior responses; cancellation and replay; same recipe reuses exact
observations; changed model/prompt/render/decoding invalidates recognition reuse. I12 demonstrates
bounded page buffers and cleanup, not a throughput claim. Required unavailable runtime stays open;
a single-pass stub or mocked provider is not passed triple-pass delivery.

<a id="PDF-15"></a>
## PDF-15 — Mapping, correspondence and governed integration

**Inputs:** PDF-13 working contract/storage and PDF-14 real retained observations; I10 frame and I11
mapping conclusions. **Output:** one admitted integrated document with selected rich content and
mandatory decision/provenance/coverage relations, ready for PDF-16.

Map native Nemotron block serialization through Docling's `parse_nemotron_parse_v3_5` where semantics
fit. Keep raw before mapping. Disable per-page heading normalization during mapping; concatenate
page documents and normalize once document-wide, following Docling's native assembly behavior.
Preserve existing section organization and both heading hypotheses without inventing new chunks.

Keep chart Markdown before any NVIDIA HTML chart-render transform: Docling's chart mapper consumes
Markdown rows, producing pictures with classification/tabular-chart metadata and panel associations.
Retain table spans/headers, captions, series/axis/unit context and generated-value attribution.
Nemotron cell text has no native cell boxes; use coarse table grounding unless a validated
cell correspondence supports finer geometry. Cross-page table continuity/reference links are
separate modeled derivations: neither pipeline guarantees them automatically. If I11 finds a
consequential continuation gap, implement a qualified relation/derivation or leave the named
capability partial with an actionable remedy, never assert it from page adjacency alone.

Build sparse page/region correspondence candidates using intersection/containment and text context;
use existing RapidFuzz `Levenshtein.opcodes` for alignment, positioned LaTeX for structure and lazy
SymPy comparison only where needed. Text agreement, parse structure and equivalence under assumptions
are different results. Avoid all-items similarity matrices, unconditional symbolic calculations or
pgvector merely to match nearby page content. Matching kernels do not own acceptance policy.

A versioned integration policy selects keep/add/replace or unresolved alternatives, including native
content replacement authorized by the operator. The application contract owns permissible actions,
evidence requirements and failure effects; the algorithm realizes them. Preserve both observations,
reasons and transformed output references. Do not silently flatten competing overlapping tables or
choose the highest confidence as truth. The public alternatives merge and ParseBench add-before-
guarded-replacement behavior are attributed provider transformations, not final adjudication.

For missing glyphs inside retained native text, keep Nemotron outside the PDF-first OCR merger;
that merger can discard intersecting OCR lines. `force_backend_text` applies only to DOCTAGS and
cannot protect Nemotron prose. Native OCR words and compact heading lines remain useful evidence;
full parsed-page retention is not needed solely for heading style. Revise FormulaPageLifetime's
last-use assumptions for actual additional render/crop consumers rather than retaining all pages.

Validate resulting content using Docling `validate_document`/`validate_tree`, archived schema and
application invariants before publication. Mapping drops, repaired/clamped geometry, deduplication
and unsupported labels retain dispositions. Zero charspans and unboxed inline formulas do not gain
false PDF precision. Coverage is scoped by pass/content family/section/selection policy: finishing
B with zero regions proves completion of that output, not absence of tables in the original.

**Targeted acceptance:** selected inline/vector math and a table/chart contribution consumed through
one document; preserved rejected/ambiguous readings; repeated equal occurrences; malformed/truncated
inputs; independently known transformed geometry; semantic table/chart structure after export;
policy-only remapping over unchanged raw responses. Do not use the mapper as both producer and
oracle. PDF-11 owns actual knowledge-pipeline qualification and any independent benefit comparison.

## Sources, alternatives and deferred work

[Public parser](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/4035ffb1d8f8bafcdb867dfaf6f7514f101464f9/docs/postprocessing.md),
[inference implementation](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/4035ffb1d8f8bafcdb867dfaf6f7514f101464f9/nemotron_parse/inference.py),
[Docling mapper](https://github.com/docling-project/docling/blob/v2.145.0/docling/utils/nemotron_parse_v3_5_utils.py),
[review mechanisms](../../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md#library-realization-and-responsibility-choices).
Verify newly uncertain details with Context7 then exact pinned sources. The ParseBench CLI remains
an optional parity control, not production orchestration. Root in-process Transformers is an alternate
investigation only if isolation fails. Granite chart extraction is a bounded comparison if needed,
not a second default chart pass. Full token logprobs, embeddings, new graph stores, native forms/raw
PDF-object inventory and independent chart-description models need a named unmet consumer.
