# Chandra 2 after Nemotron evidence

**Measured and interface-checked · 2026-11-08.** These bounded probes inform the [functional review](../../../functional_reviews/chandra-2-post-nemotron_2026-11-08.md). The book baseline is the authenticated 518-page PDF, Standard run 297/cut 413 and integrated run 312/cut 431. The [case selection](cases.json) and [supplemental source ledger](raw/supplemental-reference.json) were set from the source before output assessment. The PDF render and source-text references support scoped judgments. The five supplemental cases are authored stimuli. They test mechanisms and do not establish performance on natural handwriting, scientific literature or production forms.

## Executed cases

All 20 live conversions returned an HTML prediction and Docling `success`. The Transformers route reported `unspecified` stop reasons. Scope is 12 original book pages, five supplemental cases and three original-pixel crops. [Raw responses and receipts](raw/live-responses.jsonl) · [Object and projection trace](raw/consumer-trace.json)

| Source | Checked result and remaining limit |
|---|---|
| p11 | All 20 numeric literals and the floor expression survive. The printed table caption is a separate item, so structured attachment still needs evidence. |
| p108 | One picture covers both panels. The correct shared caption survives as a loose item, and visible panel parameters and approximate peaks are described. The picture text enters the current projection as ordinary body text. |
| p142 | Short displays and prose remain separate. The control checks these boundaries, with no claim of exact equivalence for the full passage. |
| p151 | Two typed native tables. Table 4.2 retains all four fractions and both levels of axes. The caption is loose. The incumbent page and crop also contain those values. The retained crop mapper renders a 5×4 structure and the integrated selected product lost the table. Chandra's 4×4 candidate and the retained crop can both support a better selection decision. |
| p301 | Correct printed Figures 7.2 and 7.3 and useful separate descriptions. The triangle is symmetric. No structured series is recovered. The captions remain loose. |
| p334 | Correct symmetric bell-curve description and printed Figure 9.1 caption. The response avoids the incumbent's conflicting values at ±2 by supplying description rather than a point series. |
| p398 | Exact 21×13 dimensions, rich mathematical column headers, and the early Profit and Z12 values missing or shifted in the combined arm. Among 260 data cells, row 7 Z5 is 0 instead of 2. The Standard Reader's exact table matched the source cells, so Chandra's reading is evidence for the discrepancy with Combined and a regression if applied wholesale. |
| p416 | Six matrices are present as complete labeled LaTeX strings and survive the repository projection. The current math grammar reports `failed` on all six. The retained Standard and Combined Reader results each show a truncated selected formula and matrix content in `original_text`. [Reader and grammar control](raw/matrix-consumer.json) |
| p439 | Correct equal-probability `i/N` and neighboring recurrence. The layout splits an exercise and its conditions across siblings. Standard also retains the main symbols. |
| p506 | Two running-header items, both furniture, and an empty projected body. Matches the Combined control. |
| p509 | Upright logical reading of the sideways table, with totals 928 and 205. The first bin label is duplicated or malformed, Medians falls under the wrong group, and some values shift or disappear. The transformed upright crop recovers the repeated 63 in the note and removes the extra 62.2 label, but its `Below 62.2` header still merges printed labels and its cell alignment remains unsafe. |
| p510 | All 344 inspected source data values match. Both groups and ages survive. The exact integrated table also matches these cells. |
| Diagram | All three directed edges and both branch labels are present in unboxed Mermaid code under a located picture. Default Docling Markdown omits it. The existing projection includes the code, so a future typed graph read needs separate admission from prose. |
| Chart | Correct axes, mL units and 60/40/30 in a child table. The numbers match the fixture, while the table gives all three the same standing. Only 60 was printed as a bar value. The child table has no direct provenance or canonical chart metadata. |
| Language | French, Hindi, Arabic RTL and scripted English remain ordered. Hindi and Arabic literals match the fixture. The French curly apostrophe is normalized. The last line is typed in a script font. |
| Chemistry | Correct propan-2-ol interpretation and `CC(C)O` in attributed molecular metadata. The source picture has a region and nested OH text is unboxed. The existing text projection does not surface molecule metadata. |
| Form | Exact visible BX-71 and both checkbox states. The text is an ordinary item and the marks are separate picture children. Native widget identity and label association are absent from the visual result. The fixture separately verifies native `/V` and `/AS`. |
| p151 and p416 crops | The p151 crop repeats the correct four values, grid and caption. The p416 crop repeats six complete arrays and caption. Neither crop establishes an advantage over the full-page result for those local outputs. Their source transforms and request rasters are retained separately. |

The probe compares live output through direct Chandra HTML replay, native object inventory and the actual repository's `project_section_nodes`. It also queries both retained p416 products through `ci source inspect`. No Chandra observation was admitted to the production product. New Reader/CLI/MCP endpoints, guarded promotion, a fresh Standard upgrade-only conversion, protected gain and corpus-wide recall remain separate qualification questions. The exact Nemotron response replay compares 21 page/crop response summaries, which all match under 2.145.0 and 2.148.0. It uses normalized geometry and does not reproduce publication. [Mapper replay](raw/nemotron-replay.json)

## CPU controls and operation

The [paired parser controls](raw/parser-controls.json) cover malformed and absent geometry, rotated cropped coordinates, blank and invalid responses, nested versus loose captions, document-wide versus page-local headings, forms, picture traversal, molecule metadata, rich cells, and oversized or continued tables. The 1,000-column constructed row survives while the 1,001-column row leaves an empty table and the adjacent content. The 2.148 parser retains the inline boundary whitespace that 2.145 lost in the fixture. The generated object can retain superscript metadata through a lossy Markdown view. An explicit length stop produces partial status in the synthetic response-status control. Unmarked truncated markup and repeated text can parse and report success. That control tests status interpretation without forcing a live failure.

Target overlay used exact Docling and Slim 2.148.0 and Core 2.106.0, with Typer 0.27.0 prepended for target dependency compatibility. The root environment otherwise supplied Torch 2.15.0+cu132 and Transformers 5.22.1. The host is an RTX 5090 using process-local 615.71.10 NVIDIA libraries. Serial inference used the official BF16 checkpoint and unquantized Transformers. The first offline attempt failed because Docling's snapshot fetch asked for uncached ancillary files. The successful run bound the complete inference files from the pinned local snapshot through `artifacts_path`. The two optional optimized kernel packages were absent, so PyTorch used reference kernels. This is evidence for the actual local run and workload. [Runtime](raw/runtime.json) · [First attempt](raw/first-attempt.txt)

The probe sums 346.93 seconds across case conversion calls, including model initialization in each of the two runs. Peak Torch-allocated memory was 11,720,269,824 bytes. The three crop receipts include hashes and sizes of the submitted engine rasters. The first run retained the source identities and configured render scale and did not record the actual engine rasters. Processor-internal tensor dimensions were outside this capture. The rotated affine fixture and [crop frame ledger](raw/crop-frames.json) preserve the coordinate boundaries independently.

## Reproduction

Run from the repository root. Install the target overlay under build, preserving the root lockfile. The exact snapshot is `datalab-to/chandra-ocr-2@af93b47dba1b47b6640c86ccf487ed2260ab9a09`. Place it at the `datalab-to--chandra-ocr-2` child of the specified artifacts directory. The driver variable below is specific to this host.

```sh
ev=docs/design_review/evidence/2026-11-08_chandra-post-nemotron
work=build/chandra-review
pdf=docs/statistics_corpus/corpus/grinstead_snell/Introduction_to_probability_grinstead_and_snell.pdf
uv pip install --target "$work/site" --no-deps 'docling==2.148.0' 'docling-slim==2.148.0' 'docling-core==2.106.0'
uv --no-config pip install --target "$work/cli-site" --no-deps 'typer==0.27.0'
uv pip install --target "$work/supplemental/site" 'reportlab==4.4.5' 'pypdf==6.1.3'
PYTHONPATH="$work/supplemental/site" .venv/bin/python "$ev/supplemental.py" "$work/supplemental" "$work/supplemental-reference.json"
.venv/bin/python "$ev/crops.py" "$pdf" "$work/crops"
export PYTHONPATH="$PWD/$work/cli-site:$PWD/$work/site"
export LD_LIBRARY_PATH="$PWD/build/nce-full-book/nemotron/driver-615/usr/lib/x86_64-linux-gnu"
export HF_HUB_OFFLINE=1
.venv/bin/python "$ev/probe.py" "$pdf" "$work/panel" --artifacts "$work/artifacts" \
  --page 151 --page 416 --page 11 --page 108 --page 142 --page 301 --page 334 \
  --page 398 --page 439 --page 506 --page 509 --page 510 \
  --image "$work/supplemental/diagram.png" --image "$work/supplemental/chart.png" \
  --image "$work/supplemental/language.png" --image "$work/supplemental/chemistry.png" \
  --image "$work/supplemental/form.png"
.venv/bin/python "$ev/probe.py" "$pdf" "$work/crop-panel" --artifacts "$work/artifacts" \
  --image "$work/crops/joint-distribution.png" --image "$work/crops/markov-arrays.png" \
  --image "$work/crops/appendix-upright.png"
.venv/bin/python "$ev/trace.py" "$work"/panel/*.native.json "$work"/crop-panel/*.native.json --out "$work/trace.json"
env -u PYTHONPATH .venv/bin/python "$ev/controls.py" "$work/controls-2.145.json"
.venv/bin/python "$ev/controls.py" "$work/controls-2.148.json" --baseline "$work/controls-2.145.json"
.venv/bin/python "$ev/nemotron_replay.py" build/nce-full-book/integrated-source/recognition
```

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**chandra-post-nemotron**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Local Chandra 2 post-Nemotron capability panel](records/chandra.post-nemotron-live-panel.json) | functional-review | partial | O01, O02, O03, O04, O05, O06, O07, O08, O09, ADR-0040 | 2026-11-08 |
<!-- evidence-index:end -->
