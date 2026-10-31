# PDF-only Docling pipeline — connected target model

**Proposed · 2026-10-31.** Companion to the [functional review](pdf-docling-pipeline_2026-10-31.md).
This document describes a target for subsequent planning. No production/schema change, new
accepted ADR, corpus conversion or deployment is claimed.

## 1. One source structure, with scoped authorities

```text
retained PDF bytes
  → StandardPdfPipeline conversion + separate health report
  → immutable native DoclingDocument JSON
  → derived Docling section/subsection hierarchy (where grouping is needed)
  → section/item/cell/formula access views + qualified text projections
  → source observations, scope, lazy mathematical interpretation
  → section-grounded proposal packets → consolidation → queries/exports
```

Docling/core owns its native document schema. LinkML and the trusted execution companion own
application operations, behaviors, states, dependencies, identity recipes, domain recognition
rules and relationships between products. PostgreSQL owns immutable instance custody and native
publication invariants. SQLAlchemy Core, Pydantic boundaries, JSON Schema and existing RDF/SHACL
projections realize their respective contracts; none independently redefines domain policy.

A complete domain model does not require reproducing all upstream model internals in LinkML.
Pin/archive the upstream schema and supported adapter capability, and define how the application
consumes them. Changes in native schema require explicit compatibility handling; unsupported
versions refuse interpretation rather than silently discard fields.

The PDF is the only acquisition format. Source-to-PDF rendering is upstream and unimplemented.
The pipeline rejects active HTML ingestion. Historical stored products are still their original
products; removal of an adapter does not require reconversion or rewriting old evidence.

## 2. Concepts, identity and relationships

| Concept | Owned meaning and connection |
|---|---|
| PDF original | Retained bytes/content hash plus acquisition identity; independent of conversion success. |
| Conversion specification | Selected pipeline/backend, package/schema versions, resolved model revisions, OCR/formula/table/hierarchy options and runtime binding. |
| Conversion product | Immutable native document JSON and dependency on original/specification; actual output identity retained even if repeated inference differs. |
| Conversion health | Status, errors, coverage and available stage diagnostics; linked to conversion, not injected into the native schema. |
| Document item occurrence | Conversion-qualified native pointer; content equality does not merge separate occurrences. |
| Page region | Physical page number, bounding box, coordinate origin and page dimensions; multiple regions per item are allowed. |
| Section/subsection | Hierarchical containment with ordered content; extracted/inferred/derived basis explicit. |
| Analysis selection | Section/subsection or operation-specific ordered item membership; not a PDF page or token chunk. |
| Text projection | Versioned linearization for text consumers; native-item mappings and synthetic text recorded. |
| Formula recognition | Formula occurrence, untreated extracted text, recognized LaTeX, recognition health and PDF-region evidence. |
| Interpretation/assessment | Separate demand/result over formula plus explicit context, assumptions and question; unsupported/unknown states retained. |
| Domain recognition | Attributed statement/proof/exercise/binding observations over document evidence; not automatic mathematical truth. |
| Recognition evidence (conditional) | Alternative OCR candidate and region/alignment/outcome; never an implicit second editable document authority. |

Ordered containment, caption/table associations, reading order, source-region links, derivation and
interpretation dependencies retain their own kinds and occurrence identities. `self_ref` is
qualified by a conversion; a pointer such as `#/texts/3` alone is not a stable cross-build ID.
Cross-build correspondence, if needed, is a separate attributed relation, never pointer equality.

Original byte ranges, PDF point geometry, native item text offsets and derived canonical offsets
are distinct address spaces. A recognized formula symbol can have an exact offset in recognized
LaTeX while its PDF grounding remains only a formula-region box. Do not manufacture glyph-level
accuracy or label a visual recognition as an exact original-text copy.

## 3. Hierarchy is preserved; section chunking is absent

Enable `HeadingHierarchyOptions(enabled=True)` with the supported bookmark/numbering/style
signals. In tagged 2.145.0, full parsed-page retention is unnecessary for the style signal.
Record the selected rules and retain uncertainty where heading inference is ambiguous.

Use body-tree reading order. Verify whether conversion emits actual section containers, not
merely `SectionHeaderItem.level`. If grouping is missing, derive another native DoclingDocument
using `GroupLabel.SECTION`/`CHAPTER`, `add_group(parent=...)` and supported item relationships.
Preserve the original conversion untouched, map every derived occurrence to its source, and
validate the resulting tree before publication. Chapters, sections, subsections, lists, tables,
formulas, figures and captions remain visible to downstream consumers.

**No chunker, section split, token window or chunk-storage subsystem belongs to this target.**
Use intact sections/subsections. Section-level methods select their declared content once;
ancestor context does not authorize reprocessing all ancestors/descendants. Item-specific
methods operate on items under their section without introducing persistent section parts.

Bounded responses, export batches and packet transport pages do not change document structure.
If a real required consumer later cannot handle an actual large section, investigate that
specific failure. Only then consider splitting; resulting parts must be child groups at a lower
level under the original section within the derived Docling hierarchy, with ordered membership
and source mappings. This is a future design constraint, not current planned scope.

## 4. Governed operations and lifecycle

| Operation | Input → output | Meaning-changing boundary |
|---|---|---|
| Convert PDF | Original + resolved specification → document + health | Native extraction, OCR, layout/table/formula recognition and hierarchy inference. |
| Organize sections | Conversion + grouping recipe → derived Docling document | Explicit section containers; no invented author text or chunks. |
| Project source views | Pinned document + view recipe → item/edge/region/cell indexes or text view | Reading order, content layers, separators and coverage declared. |
| Recognize domain structure | Pinned section/items + rules → observations | Theorem/proof/exercise/function/binding attribution; uncertain evidence stays uncertain. |
| Interpret mathematics | Qualified formula + context + demand → interpretation | Native SymPy adapter, ambiguity and unsupported constructs. |
| Assess mathematics | Interpretation + assumptions/question → assessment | Definedness and inference premises; no automatic truth from normalized equality. |
| Build packet | Section/items + domain context → packet/source frame | Exact supplied context enters packet identity. |
| Inspect/export | Pinned product + typed selector → bounded answer/artifact | Supported fidelity and unavailable/partial results exposed. |
| Verify recognition (conditional) | Suspicious region + explicit recognizer → alternative evidence | No automatic majority correction or untracked mutation. |

Compose these into existing run/task/publication ownership. These semantic operations do not
require a task/transaction for every item. A conversion can execute native stages together;
section grouping and access projections can share one owned preparation/publication unit when
failure and visibility semantics permit. Do not add a second workflow engine.

Existing pending/running/completion/failure/cancellation and attempt fences govern application
work. Conversion statuses map to those outcomes through the admitted adapter. Completion of a
conversion is distinct from complete formula recognition, a structurally valid tree, source
fidelity, completed knowledge extraction and independent grading.

A partial result remains inspectable under explicit coverage and cannot substitute for a required
complete product. Cancellation drains owned work and prevents stale publication. Retry reuses
verified immutable inputs/results; it does not rerun successful model inference merely to serialize
or query. Recognition inference is not declared byte-deterministic without evidence.

Docling formula enrichment can silently retain fallback text after a caught model exception.
The adapter must resolve whether attributable success/unknown/failure can be captured through
supported stage integration. Until established, do not expose every FORMULA `text` as certified
LaTeX. ConversionResult status alone is insufficient for this distinction.

## 5. OCR and mathematical interpretation

Primary proposed OCR binding is RapidOCR/ONNX, explicit English (`iso:en`),
`OcrMode.PDF_AWARE_LAYOUT_REGIONS`, `replace_broken_text_layer=True`, and `do_ocr=True`.
Package/model compatibility and corpus results must qualify it before deployment. Preserve
reliable native text, OCR missing raster/vector regions, and replace detectably broken pages.
PDF-first merge is geometric precedence, not character-level arbitration. A plausible wrong
native digit may remain unverified; no-disagreement is not a verification result.

Keep OCR scale, retained-image scale, model language/weights, thresholds and orientation choices
explicit. Full-page and OCR-first layout-region modes are alternatives for actual bad-source
cases, not universal upgrades. Full-page OCR can discard native information. Do not automatically
run multiple engines or a whole-book verification pass. If a precision-sensitive consumer or
observed disagreement justifies independent verification, retain candidates, geometry, alignment
and resolution as separate evidence; a correction creates a new derived document.

Formula enrichment (`CodeFormulaVlmOptions.from_preset("codeformulav2")`) is separate from general
OCR. Its native text output becomes direct mathematical input, not a reason to run HTML delimiters,
MathJax macro extraction or reconstruction of rendered notation. Native SymPy Lark parsing is the
starting candidate; extend native grammar/transformer only for demonstrated supported contract
gaps. Retain occurrence extraction only where consumed; a SymPy expression does not preserve
source multiplicity or source positions.

M09 consumes formula occurrences; M11 consumes explicit lazy interpretation/assessment demands;
M13 consumes section/item ancestry plus attributed binding/declaration evidence, including source
position and forward applicability extent. A mid-section declaration cannot retroactively govern
earlier formulas or leak into unrelated sibling units. Native document
structure improves contextual grounding but does not resolve all mathematical ambiguity. Keep
sets, relations, function roles, binders, assumptions and definedness explicitly modeled. A failed
recognizer cannot cause downstream complete-absence claims. Source readiness does not trigger
symbolic normalization or grading.

## 6. Persistence, execution and consumers

Store the native Docling JSON in PostgreSQL JSONB, separate from original PDF bytea and conversion
health. The derived hierarchy is a distinct versioned native JSON product if grouping changes
are needed. Derived rows serve bounded item/region/table/section queries without loading the full
book. Their only writable meaning comes from their producer and declared source dependencies;
ordinary consumers do not edit them independently.

Finalize library validation/normalization before hashing; core `validate_document()` may clamp
geometry. Archive schema and serialization policy. Reference images through owned immutable
artifacts where required; do not embed every rasterized page by default. A reload resolves only
supported trusted artifacts. A missing image is unavailable payload, not absence of the picture.

Use the established Core/native publication and migration route, not per-section dynamic DDL.
Native schema invariants, LinkML relationships and runtime boundaries have complementary scopes;
never assume generic JSON validation enforces all cross-product custody.

Maintain one operation-owned converter/model lifetime and use Docling's stage batching and bounded
queues. Bound parser results, thread counts and model memory together. Formula crops can retain
PDF backends; release native resources after their final use. No additional process pool,
repeated per-section conversion, or page-shard/concatenation scheme is selected without an actual
need. Full-book feasibility remains untested; a page-range conversion is not automatically a
complete section hierarchy.

Packets/source frames must expose actual rich context: section path, source item references,
formulas with recognition state, table cells/headers, captions, regions and scope coverage.
Hash that context. Existing sentence layouts remain reusable derived views, not the primary
source model. Use direct source references for citation placement; fuzzy matching is a bounded
fallback within the declared section/item scope.

CLI/MCP provide pinned hierarchy/item/formula/table/region reads and explicit health. Keep model
loading out of ordinary service registration and read-only queries. Arrow/Parquet/DuckDB use
purposeful projections retaining conversion and source references; no second semantic authority.

## 7. Migration and acceptance boundary

The future implementation must replace the active HTML method, profiles, hint synthesis,
source inventory/defaults, admitted operations, implementation archive, dependency recipes and
consumer input contracts together. Remove HTML-only dependencies after caller analysis. The
PDF-only slim packaging candidate avoids unrelated formats and their dependency constraints.
No version change was made by this review.

Preserve frozen migrations, historical original bytes, native products, answers and grades.
Historical reads may decode archived records without retaining an active HTML producer. New
PDF anchors are new evidence, not relabeled HTML anchors. Evaluation reference adaptation is
explicit and independent; neither grading-policy changes nor human grading is introduced.

Representative delivery scenarios are owned by the [review investigations](pdf-docling-pipeline_2026-10-31.md#12-investigation-and-delivery-scenarios):
intact section/subsection navigation; repeated formula occurrence identity; inline and display
coverage; table-cell and figure evidence; direct actual packet/citation use; partial conversion
and failed enrichment; native JSON roundtrip; protected publication/cancellation/reuse;
full-book resource behavior; PDF-only fresh operation and historical read preservation.

No universal OCR correctness, exact original LaTeX recovery, full inline-math coverage,
mathematical completeness, source fidelity improvement or performance benefit is established.
Those claims require their own applicable evidence. This target selects the direction and the
smallest responsibilities to investigate, rather than retaining every old parser stage or adding
all available Docling features.
