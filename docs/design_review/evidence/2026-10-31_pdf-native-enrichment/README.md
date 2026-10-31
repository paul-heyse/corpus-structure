# Native PDF enrichment and vector-gap discovery

**Outcome: partial, 2026-10-31.** These bounded results qualify native adapter mechanisms, not
whole-book completion, database publication, extraction, independent grading or universal fidelity.
Root owns evidence-record finalization and assembled acceptance.

## Actual native execution

`probe.py --source <retained Full.pdf>` ran one physical-page85 conversion in the application
Docling 2.145.0/core 2.105.0/parse 7.24.2 environment, with explicit producer-worktree
`PYTHONPATH`, `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. All selected layout, formula,
table and OCR files were copied into the verified content-addressed model bundle. Its manifest
records immutable HF snapshot revisions and every selected file hash. Layout/table/formula
ran on CUDA; the three OCR sessions used the explicitly selected CPU provider. Raw native JSON,
effective options, package/provider report and recipe remain in `raw/`.

The initial source-location failure occurred before inference because corpus originals are ignored
and absent from the worktree. Its logs remain under `initial-source-location.*`; the corrected
command explicitly selected the original in the main checkout.

The native cell extension processed all nine nonempty page85 cells successfully using native
formula inference and retained rich-cell references. This does not establish all nine cells as
mathematics: prose/header outputs demonstrate why selected-cell processing and semantic
classification must remain separate. Required consumer work retains ordinary cell text/header
roles and publishes math references only with attributed classification.

## Missing inline content and the structural correction

The first inline no-op processed zero candidates and therefore does **not** establish inline
support, despite the initial probe script labeling that empty operation passed. Actual native
paragraphs omit inline vector math. CPU-only native parser inspection found 437 words, 463 vector
paths, and Liberation/DejaVu fonts rather than mathematical fonts. The naive connected-shape
API returned one full-page box because a background rectangle connected everything.

The corrected capture escalates already-computed shapes through public Docling-Parse page-result
materialization, filters backgrounds and text-explained paths, uses Docling's spatial index and
NetworkX connected components, and groups native vector islands by surrounding native word gaps.
It retains compact candidate boxes/context before native cleanup, not all glyph/path arrays in
PostgreSQL. The pinned adapter accesses the native backend's owned page-result handle; native
input release remains the enclosing lifetime owner.

`vector_candidates.py` exercises that geometry with no inference. `vector_crop_probe.py` then
uses the retained page85 native product and the same qualified formula-model family to recognize
22 anchored inline regions, with no second document conversion. It recovered symbols including
D, k, n, A and S_i. Disconnected regions sharing a native text anchor become one native formula
with multiple provenance regions and declared crop composition. Original native paragraph text
remains in the parent product and `orig`; derived inline groups retain prose and formula children.

Actual outputs also expose matrix/binomial ambiguity and adjacent-prose crop contamination.
Inference success is **not** source-fidelity success. Absolute crop-padding refinement and
independent source checks remain consumer qualification work. The initial strict recipe-decoding
failure is retained under `initial-recipe.*`; decoding now uses strict typed JSON while retaining
original archived bytes independently.

New formula provenance spans are local to their original item text. Parent-text/cell offsets are
separate `derivation_mappings` qualified by the parent product; an empty vector-text anchor is not
an exact PDF-glyph position. Source-view projection preserves inline adjacency and marks block
separators explicitly.

## Focused controls and limits

Seventeen focused controls passed against the application interpreter, and scoped Pyrefly passed
with zero errors. Controls include native tree validation, source-path mutation, swallowed native
inference failures, rich cell links, native inline adjacency and parent-offset versus native-local
provenance. Fake engines in failure controls establish contracts only, never provider success.

The latest candidate capture is qualified by CPU native page-result geometry plus the native
crop recognition; assembled full-book execution remains required. Existing finalized evidence
was not modified. No throughput, complete inline discovery or mathematical-correctness claim is made.
