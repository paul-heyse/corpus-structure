# Docling and Nemotron 3.5 triple-pass parsing

**2026-10-31 · Functional-extension review · Combined library and domain-model focus.**
All recommendations are **Proposed**. Source inspection establishes the mechanisms described;
it does not establish local model accuracy, throughput or completed product qualification.

## Outcome and recommendation

Adopt, subject to the focused feasibility questions below, a composed source interpretation:
Docling StandardPdfPipeline with in-page RapidOCR preserves native text and positioned observations;
Nemotron 3.5 supplies full-page interpretation, separately prompted layout detection, and table/chart
crop interpretations. A governed reconciliation operation produces one integrated consumer document without
rewriting either recognizer's observations. Recommend Docling as its content graph with a mandatory
typed companion for the combined evidence and selection semantics. Downstream extraction consumes that selection with its
alternatives, coverage and evidence links. Consolidation remains responsible for knowledge claims.

This is valuable beyond fixing inline math. It can expose missing tables, chart series and labels,
stronger reading-order/heading hypotheses and better contextual grounding for definitions and
mathematical statements. Those are plausible functional gains, **not demonstrated quality gains**.
A chart's generated data table remains a recognition hypothesis; it is not original numerical data.

A consequential improvement over the supplied reference's alternatives is NVIDIA's public
`DocumentParser` API. Use its complete triple-pass capability rather than porting the reference
scheduler, crop selector and merger. Keep application semantics in the existing model/compiler,
method lifecycle and PostgreSQL publication boundaries. The target companion specifies this
composition: [target model](docling-nemotron-triple-pass_2026-10-31_target-model.md).

## Baseline and evidence limits

Inspected production baseline: `39eda6e55020c1b5b50f5bfcb4ae682757334741`, 2026-10-31.
Concurrent inputs are the modified [OCR reference](../libraries/docling_ocr.md) and untracked
[triple-pass reference](../libraries/docling_nemotron_triple_pass_reference.md); both are preserved.
The latter describes `1513b29`, so its run-4 recovery narrative and some API alternatives are stale.
Current [STATUS](../../STATUS.md) and the [PDF coordinator](../plans/pdf-docling-pipeline_2026-10-31.md)
record schema 0055, retained full-book native publication, run5/task7 selected enrichment (648 aligned
anchors, 36 unresolved reports), and run6 reuse. These are earlier receipts, not fresh model runs.
The current enrichment retains unresolved reports instead of failing the entire selection.

Current strengths include immutable PDF originals/native JSON, archived contracts, native item and
region indexes, intact section scopes, separate health/coverage, process-owned conversion,
method/attempt fencing, retained reads and on-demand region rendering. Full Docling 2.145.0 with
requested extras remains the distribution; its internal `docling-slim` dependency is not a proposed
replacement. Remaining old-plan extraction, MCP and independent grading obligations remain open;
this review neither completes nor makes them prerequisites for architectural inquiry.

The review used source inspection, Context7 and primary NVIDIA/Docling sources. **not_run:**
Nemotron installation/startup/inference, local quality comparison, geometry fixtures, measured
capacity and assembled consumer qualification. No dependency, service, database or product change
was made. No broad diagnostic audit or audit-premise update was performed.

Standard: core 3.3, efficient-architecture heuristics 1.0, code-intelligence profile 1.4 and the
[repository binding](../design_review/design_principles/binding/corpus-structure.md). FP-04/A2
require modeled behavior as well as records; CI-01–06/10–13 preserve attribution, unknowns,
relationships, evidence closure and independent evaluation. FP-07/A4 and H2–4/12–17/21–28 favor
native orchestration, bounded live state and reuse of inference across later interpretations.

## Choosing the singular downstream document model

The user's clarification is adopted: downstream stages should consume one integrated document
contract after both recognition routes, rather than independently merging Docling and NVIDIA outputs.
The choice is not constrained to either vendor's schema. Compared four alternatives: plain Docling,
NVIDIA blocks/Markdown, an integrated application contract using Docling content plus mandatory typed
companion relations, and a new hybrid content schema replacing both. Recommend the third.

It preserves a single rich hierarchy and existing scientific/query consumers while integrating
Nemotron text, formulas, tables and charts. The mandatory companion represents both providers,
multiple-input lineage, correspondence, alternatives and selection; it is part of the singular model,
not a disconnected sidecar. Upstream Docling owns the embedded content shape; the application owns
the integrated contract and its behavior. No consumer performs an ad hoc second merge.

A new hybrid content schema could be justified if a required distinction cannot be faithfully
expressed or efficiently consumed this way. Current evidence shows gaps in lineage and behavioral
contracts, not a need to replace Docling's whole content schema. Reimplementing ordered hierarchy,
rich tables, formulas, charts, validation and all consumers would add substantial machinery. The
[target comparison](docling-nemotron-triple-pass_2026-10-31_target-model.md#one-consumer-model-multiple-evidence-sources)
preserves that alternative and its concrete revisit condition.

## Current integration surfaces

| Responsibility | Inspected owner / consequence |
|---|---|
| Native conversion | `ingest/pdf.py`, `pdf_ocr.py`, `pdf_candidates.py`: native text, PDF-aware OCR, CodeFormulaV2, accurate TableFormer and hierarchy; a successful conversion does not establish exhaustive transcription. |
| Page lifetime | `ingest/pdf_health.py::FormulaPageLifetime`: current recipe excludes image exports and other image enrichments. Revise its last-use assumptions deliberately for shared render/crop consumers. |
| Native contracts | `model/semantic/pdf-products.yaml`, `semantic/pdf_contracts.py`: LinkML companion owns the envelope, Docling owns document shape, archived schema validates retained products. |
| Custody and lineage | `semantic/pdf_storage.py::selected_native_ancestry`: follows a single parent chain. The envelope/physical native product also have one parent. This cannot represent a reconciled result's complete multiple-input provenance. |
| Orchestration | `ingest/pdf_methods.py`, `pdf_worker.py`, `core/method.py`: finite config/input digests, owned workers, no DB handles in compute children, existing method/task/attempt and publication protection. |
| Consumers | `serve/native_source.py`, `serve/native_regions.py`, native SourceViews, scientific methods and agent/reference preparation: input selection and ancestry determine which evidence is reachable. A new JSON field alone cannot integrate the new recognizer. |

## Opportunities

<a id="O01"></a>
### O01 — Reuse a complete true triple-pass capability

**Recommended foundation.** NVIDIA's public `DocumentParser.parse_triple(image,
triple_regions="union")` expresses full-page parse A, layout detection B and table/chart crop parse C.
`parse_many`, `prepare`/`parse_prepared` support batching and prepared inputs; a supported backend
callable permits an observed API boundary. The public package, not merely the standalone ParseBench
script, should own its supported crop preparation and internal pass scheduling.

Docling's `nemotron_parse_v3_5` preset implements A only. It is useful as a control or mapping path,
not an equivalent implementation of triple pass. Triple pass does not imply three independent models,
and crop C does not automatically reinterpret every inline formula or prose region.

Use a narrow repository adapter around the public API. Pin the package/source revision, prompts,
weights, rendering and effective decoding options. Capture raw stages before projecting to the integrated document. Explicitly select triple mode
on general/batch APIs. Public `merge_policy="alternatives"` is the preferred provider output because
it retains competing table/chart interpretations; it is not the final consumer selection policy.
The benchmark can choose the best alternative table, so its headline accuracy cannot establish the
quality of one selected transcription.
Expose pass/crop roles in contracts without creating one database task per primitive request.
Separate internal crop scheduling from the existing scheduler's semantic task/attempt ownership.

**Alternative:** the ParseBench CLI offers closer benchmark reproduction but imports file layouts,
process pools and different postprocessing. Prefer it as a bounded parity/reference route, not the
production control plane. Porting its internals increases maintenance without an established gap.
Docling-only single-pass conversion loses the proposed detection/crop capability.

**Delivery example:** one page request returns A/B/C observations, declared merge settings and coverage,
including the valid zero-crop case. A later mapping revision reuses those observations without GPU work.

<a id="O02"></a>
### O02 — Model multiple observations and reconciliation as a provenance graph

**Required foundation, not an optional audit sidecar.** Extend the native-product model with qualified
input relations (product pin, input role, scope) and first-class correspondence and selection decisions.
Keep an optional base parent for convenient structural derivation; it is not the entire lineage.
A reconciliation result consumes the Docling product, Nemotron observation products and exact policy
release. Every selected or added item links to its supporting observations and transformations.

Correspondence supports one-to-many/many-to-one, unmatched and ambiguous endpoints. Repeated equal
text or equations remain different occurrences. Relation identity includes its own scope/evidence;
endpoint pairs and similarity scores alone are insufficient. Use model-defined record kinds and
operations so additional recognizers/policies become additional instances and bindings where their
semantics fit, rather than separate hardcoded branches.

Extend ancestry, authorization, source frames, evidence retrieval, export and reuse together. A
consumer must traverse all admitted inputs within its bound run and project, not discover unrelated
ambient products. Source ancestry is a DAG of direct input relations; materialize no universal path
closure. Validate acyclicity at publication and use indexed recursive reads when demanded.

**Alternative:** separate unconnected Nemotron JSON is useful for a probe but fails the target's
connected behavior and evidence requirements. Overwriting native text loses competing evidence.
Reusing historical HTML machinery is unnecessary: reuse suitable contract patterns, not retired input paths.

<a id="O03"></a>
### O03 — Make rich reconciliation actionable without claiming source truth

**Recommended functional core.** Retain both recognizers, then produce a new selected DoclingDocument
plus modeled decisions. Selection can keep native content, add a missing occurrence, choose a better
supported interpretation, or preserve unresolved alternatives. Whole-page replacement may be a
supported explicit policy; unrestricted silent replacement is not.

Use NVIDIA `stages.fullpage/detection/crops` and its declared merge mode as provider output. Distinguish
that provider merge from repository cross-recognizer reconciliation. Source tracing shows the
ParseBench path does add-only before guarded replacement, so a crop can participate in both before
duplicate cleanup. Do not assume this is an exclusive replace/add/skip decision. Prefer explicit
repository decisions over treating the benchmark's final Markdown as adjudicated source content.

Correspondence candidates should use page intersection/containment plus text alignment. Existing
RapidFuzz `Levenshtein.opcodes` is a useful text mechanism; positioned LaTeX and lazy SymPy can support
mathematical comparisons. Formula equivalence under assumptions is not exact transcription equality.
Use sparse candidate neighborhoods, not an all-items similarity matrix. Matching algorithms do not
supply semantic acceptance policy; that belongs to the authoritative operation contract.

Retain raw bodies, parsed blocks, normalization and repairs. Unknown labels, malformed coordinates,
truncation and duplicate suppression have visible dispositions. A model-generated omission does not
prove absence; A/B agreement is correlated, and logprobs are not calibrated fidelity probabilities.

**Value:** extraction can inspect a definition containing previously absent vector math, with a chosen
transcription and visible alternative/source crop, instead of receiving broken native prose or an
unexplained correction. The policy may legitimately leave the selection partial.

<a id="O04"></a>
### O04 — Preserve hierarchy, chart/table semantics and contextual evidence

**Recommended expansion.** Preserve intact sections/subsections, table header/span relationships,
formula occurrences, captions and chart series/panels. Map through Docling's
`parse_nemotron_parse_v3_5`, `DoclingDocument.concatenate` and document-wide heading normalization
where their native semantics fit. Compare both hierarchy hypotheses rather than normalize each page
independently. Do not flatten the selected product to Markdown or add section chunking.

Docling maps chart content to `PictureItem` with `PictureClassificationMetaField` and
`TabularChartMetaField`; retain those native types and attributed generated values. Map their useful
relationships into extraction inputs so captions, axis labels, units and conditions remain associated.
Do not let a chart-derived number become a knowledge value without its recognition/evidence status.
Page-local recognition does not automatically join continued tables or establish equation-reference,
footnote or chart-to-prose relationships across pages; those require separate modeled derivations.

Inspect mapping losses explicitly: Nemotron blocks have no word/character boxes or boxed table cells;
Docling mapping uses placeholder `charspan=(0,0)` and inline children can lack provenance. Zero is not
an exact source offset. Preserve an enclosing block/region witness and an offset into recognized text,
with correspondence unknown where finer grounding cannot be established.

The installed StandardPdfPipeline retains compact parsed heading lines before assembly and drops
parsed pages after hierarchy. Do not enable full `generate_parsed_pages` solely because older
online heading guidance says it is needed. Additional parsed-page/image retention needs a consumer.

Standard's `do_chart_extraction` (Granite Vision, with classification) is a genuine alternative for
bounded chart enrichment, but the current recipe forbids it. Compare it if Nemotron chart mapping is
inadequate; do not run both generative chart routes by default. Native outlines, AcroForms and bitmap
bytes are separate capabilities, not automatically recovered by more visual passes. Their retention
should follow concrete content needs, not become a general PDF-object archival project.

The expanded OCR reference still overstates `force_backend_text` for grounded formats, despite the
triple-pass errata claiming correction. Installed `vlm_pipeline.py` applies it only to DOCTAGS;
it cannot force Nemotron output to preserve native prose. The user-owned reference is left untouched.

<a id="O05"></a>
### O05 — Reuse observations while making state and coverage executable

**Required foundation.** Extend the existing execution-model contracts with recognition, mapping,
reconciliation and selection operations, their input roles, permitted transitions and publication
effects. An inference result, a structurally admitted product and a selected consumer input have
separate meanings. Reuse completed raw stages to repeat mapping/selection, not inference; a changed
model/prompt/render/decoding recipe changes recognition identity.

Coverage is scoped to original/pages/sections, pass, content family and output representation.
A completed detection request with zero Table/Chart candidates is complete for that detection output,
not proof of no tables in the PDF. Region caps or truncated replies are partial. Transport errors,
unrequested passes, unsupported classes and ambiguous mappings remain distinguishable.

The public API retains successful raw stage text with finish reason and usage, but a later exception
need not return earlier successful stages. Its default HTTP backend drops additional response fields.
Use a narrow observed backend/client boundary to retain per-request success/failure and useful raw
responses before subsequent processing can fail. Do not wrap the complete scheduler again. Only
retain token/logprob arrays when a concrete diagnostic or consumer needs them.

The CLI should show which bound source is selected, unresolved decisions, uncovered scope, and the
next compatible action: retry failed recognition, remap retained output, or reconcile under a named
policy. Diagnostics derive from modeled outcomes; they are not a new alignment lint or independent
rule registry. Provider availability must not silently switch methods or mark empty work successful.

<a id="O06"></a>
### O06 — Isolate runtime compatibility and coordinate the whole GPU operation

**Recommended placement; feasibility unresolved.** Use a dedicated pinned Nemotron environment and
an externally served model, with the public parser in a finite DB-free worker/client environment.
The parent method retains the existing attempt/cancellation/publication lifecycle. This can require
an environment-aware worker launcher; it does not require a second workflow system or a permanent
HTTP controller around `DocumentParser`.

The package's declared Torch/Transformers bounds do not match the root's Torch 2.15 / Transformers
5.22.1 baseline. NVIDIA's validated Python3.12/vLLM0.26/Torch2.11 configuration is a starting point,
not proof on the RTX5090. Do not downgrade the full Docling environment to fit it. Review pinned
remote code before trust, and record model code, tokenizer, weights and runtime identities separately.

The plugin has model-scoped defaults plus broader compatibility patches. Separate environments reduce
unrelated model interactions; do not claim all defaults affect every model. vLLM0.26 source has a
Blackwell attention fallback (major12 defaults FA2); this settles that FA3 is not an assumed local
path, not that Nemotron+MTP works locally. Start without speculative decoding as a simpler diagnostic
if MTP blocks startup, record the changed recipe, and qualify equivalence before substituting it.

Prefer phased/exclusive GPU use initially: Docling CUDA stages, Nemotron and the planned Qwen service
share 32GiB. Reuse the existing capacity owner. Model weight size does not establish KV/cache/workspace
capacity. Bound concurrent pages, crop fan-out and image lifetime together. Release pages after all
actual consumers, not after the last formula crop. Crop batching is a physical unit, not section
chunking. Public HTTP `parse_many` eagerly prepares its input batch; HTTP concurrency alone does not bound
hydrated-page memory. Supply bounded page batches or finite per-page calls rather than preparing
the whole book. No throughput/capacity improvement is claimed without local measurement.

<a id="O07"></a>
### O07 — Deliver evidence-aware consumer journeys

**Required integration.** A selected SourceView pins the integrated product and its role; all consumers use this single
contract rather than separate provider models. Scientific
methods request recognized LaTeX and proper section context; symbolic interpretation remains lazy.
Agents receive selected content plus alternatives, unresolved status and source references. Query,
CLI/MCP inspection, render demands, JSON/Parquet exports and independent reference frames follow the
same selection and multi-input ancestry. Lightweight reads must not initialize Docling/Nemotron.

Demonstrate a complete example: select a section containing a table or inline formula, inspect the
chosen occurrence and competing recognizer output, render the original page/crop, extract a statement,
and follow the resulting claim's evidence back through the selected input and reconciliation decision.
A new selection creates new dependent extraction identity; old answers remain interpretable under
old pins. Automated reference creation/grading remains independent and unchanged in authority.

## Library realization and responsibility choices

| Capability | Recommended use and limit |
|---|---|
| LinkML | Extend existing companion and execution schemas; use `SchemaView.induced_slot`/effective constraints and existing compilation. Keep policy, input roles, vocabulary and effects connected; LinkML is not a workflow scheduler or universal integrity engine. |
| Pydantic / settings | Existing generated/frozen boundary adapters and discriminated records; separate answer-affecting recipe from result-neutral endpoint/cache settings. No second hand-maintained mirror of Docling's recursive model. |
| jsonschema | Retained schema with `validator_for`, `check_schema` and reusable validators; bounded `iter_errors` diagnostics. Keep references local as current native contracts require; a referencing registry is only needed if deliberately introducing retained multi-resource schemas. Schema validity does not establish custody or fidelity. |
| SQLAlchemy / PostgreSQL | Existing Core metadata, typed direct-input/decision relations, composite custody FKs, bounded selects/recursive CTEs and fenced bulk publication. JSONB retains native structures; purpose-built projections support selective reads. Do not upsert mutable corrections over immutable products. |
| Psycopg / pool / pgpq | Existing connection owner, short publication transaction and COPY/bulk path as appropriate. No DB connection across inference. pgpq only if a real Arrow record batch reduces movement; no Arrow conversion just to copy heterogeneous raw JSON. One pooling owner, not stacked pools. |
| Alembic / pglast | Deliberate migrations/backfill and explicit compatibility; extend existing SQL inspection for changed generated functions if needed. Parsing SQL does not establish state-machine correctness or custody. No new alignment gate. |
| RDFLib / pySHACL / valuesets | Typed URI vocabulary and optional RDF evidence export; SHACL constraints for required graph invariants where the existing release pipeline needs them. Freeze value sets per release. RDF entailment is not evidence of document truth. Check generator coverage: unsupported LinkML rules are not magically enforced by SHACL. No mandatory second graph store. |
| Tokenizers | Preserve Nemotron special coordinate/class tokens (`skip_special_tokens=False`). Tokenizer text offsets refer to submitted/recognized text, not PDF glyph positions. Reuse existing stored token streams for downstream text analysis. |
| pgvector | Defer. Embedding similarity could rank hard correspondence candidates later, but is not required for page/geometry/text alignment and cannot certify identity. |

See the supplied [library references](../libraries/README.md) for orientation. Mechanisms above are
selected for their responsibilities, not a requirement to activate every available library feature.

## Decisions, investigation and evidence needed

| Question | Disposition / concrete next evidence |
|---|---|
| Public API versus reference port | Prefer public `DocumentParser`; source-inspected. Pin and smoke-test its precise exported signature and result shape before implementation binds them. |
| Reference add/replace ordering (reference U-4) | Source-resolved: add-only then guarded replacement in the ParseBench path. Preserve provider merge identity; do not claim it is the only public API merge behavior. |
| Single selected hierarchy versus observations only | Recommend rich selected derivative with retained alternatives (O02–04); source observations alone do not realize the consumer benefit. |
| Which weight revision/decoding recipe | Unresolved: Docling preset `e7ea7924…` and benchmark `e5e0406c…` differ from current source revision. Review diffs, select explicitly; compare greedy and benchmark sampling only where it changes recommendation. Never import the published score as local evidence. |
| sm120/plugin/attention/MTP (U-1/U-11) | Actual pinned startup and one A/B/C round trip, recording capacity and effective backend. No concurrency128/192 copied from H100. |
| Root Transformers route (U-2) | Not preferred due version constraints. Investigate only if isolated runtime is infeasible; no root dependency churn for speculative convenience. |
| Logprobs/MTP (U-3) | Optional diagnostic, not a prerequisite for coverage or semantic validity. Verify response shape if a consumer justifies retention. |
| Geometry/rotation (U-5/U-9) | Nonzero CropBox, MediaBox mismatch, rotation and crop transforms against independently known geometry. Neither text alignment nor schema validation establishes coordinate correctness. |
| Chart mapping (U-8) | Map actual raw chart/panel/table responses and verify surviving structure, labels and missing provenance; retain raw on mapping loss. |
| Local benefit (U-7/U-10) | Selected normal/native-text, inline/vector math, table/chart and OCR pages with independent expectations, criteria fixed before inference. Include current ambiguous cases but do not tune against historical grades. |
| Consumer completion | Actual bound source/CLI/MCP/render/extraction/evidence journey; do not promote component parsing success to complete knowledge-pipeline acceptance. |

Development probes should use a small representative selection, including the page85 inline-math
lead and retained unresolved examples after confirming exact PDF-page identity, repeated equal
occurrences, rotated/cropped geometry, merged table headers, chart series and cross-page context.
Exercise malformed/truncated/unknown-class output, later-pass failure, retry/reuse and cancellation.
No full-book rerun, broad benchmark or regrading campaign is needed to choose the architecture.

## Rule impacts and recommended sequence

A selected implementation needs a successor ADR superseding [ADR-0038](../adr/0038-pdf-native-docling-products.md):
expand the selected production interpretation beyond the original StandardPdfPipeline-only entry,
permit governed derived content replacement/addition and revise the region-only investigative role.
Preserve PDF-only input, original/native custody, intact sections, attributed recognition and the
consolidation boundary. Revise D1/D2 (evidence/model), D3 (multi-input integrity), D4 (methods),
D5 (claim evidence), D6 (lifecycle/resources), D7 (independent frames), D8 (inspection/serving) together.
No rule or active plan was changed by this review.

First resolve runtime and mapping feasibility sufficiently to select pins. Then implement O02/O05
with O01/O06 as one coherent producer foundation; integrate O03/O04 and O07 before claiming the
functional gain. Retire overlapping candidate/enrichment work only after its required coverage and
fine grounding are supplied by the composed route. Richer Nemotron text alone is not a reason to
remove native OCR/word observations or exact occurrence anchors.

## Primary-source leads checked 2026-10-31

- [NVIDIA public postprocessing API](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/4035ffb1d8f8bafcdb867dfaf6f7514f101464f9/docs/postprocessing.md), [public inference implementation](https://huggingface.co/nvidia/Nemotron-3.5-Parse/blob/4035ffb1d8f8bafcdb867dfaf6f7514f101464f9/nemotron_parse/inference.py). Source revision is not a selected production weight pin.
- [NVIDIA source repository](https://huggingface.co/nvidia/Nemotron-3.5-Parse/tree/4035ffb1d8f8bafcdb867dfaf6f7514f101464f9): package bounds, serving guidance and `reference/parsebench/pipeline/{parse_results,postprocess}.py` supply runtime and merge details; the supplied reference §§3–11/14 supplies additional pinned leads.
- [Docling2.145 source](https://github.com/docling-project/docling/tree/v2.145.0/docling): `datamodel/stage_model_specs.py`, `utils/nemotron_parse_v3_5_utils.py`, `pipeline/vlm_pipeline.py`, `pipeline/standard_pdf_pipeline.py` and API-engine implementation. Installed sources outrank contradictory older Context7 snippets for this version.
- [vLLM0.26 plugin system](https://github.com/vllm-project/vllm/blob/v0.26.0/docs/design/plugin_system.md), [Blackwell attention selection](https://github.com/vllm-project/vllm/blob/v0.26.0/vllm/v1/attention/backends/fa_utils.py), [memory controls](https://github.com/vllm-project/vllm/blob/v0.26.0/docs/configuration/conserving_memory.md).
- [LinkML effective slots](https://linkml.io/linkml/_modules/linkml_runtime/utils/schemaview.html), [SHACL generator](https://linkml.io/linkml/_modules/linkml/generators/shaclgen.html), [generator support](https://linkml.io/linkml/generators/dashboard.html): generation coverage must be checked against pinned installed versions.
- [SQLAlchemy PostgreSQL dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html): Core JSON/table-valued expressions and conflict handling; immutable application custody remains the repository contract.
