# Visual evidence and delivery

**Development inspection verified, typed enrichment proposed · 2026-11-08.** Companion to the [Chandra coordinator](../chandra-2-post-nemotron_2026-11-08.md). Owns the initial operator and agent workflow for O01, O02, O08 and the comparison portion of O04.

<a id="CH-03"></a>
## CH-03 · Inspect an original region and its alternatives

### Consumer contract

An operator selects the exact run, producing task, product key and digest, with a page, item or qualified region. They request the observation explicitly through the existing managed invocation/effect route and inspect the retained result after it settles. A read returns the qualified original region and admitted Chandra observation, alongside relevant incumbent evidence within the same scope. Include producer, outcome, precision and locators for each result. Partial or unavailable observation evidence leaves the incumbent available with its own standing. Use the existing image rendering and artifact delivery routes for authorized original pixels.

Extend the shared native source Reader with an explicit visual-evidence selection over CH-02 observations. Reuse this contract in `ci source inspect`, the MCP `inspect_source` route and an explicitly requested source-packet evidence view. Expose a bounded way to inspect the generated response and parsed items. Use existing `render_source_region` for the original rather than embedding page images in the default packet. Apply source and observation selection before expanding children. Keep row, byte and render bounds effective across reads. A missing child region can carry an attributed enclosing block reference with coarse precision. A mismatched pin or invalid scope refuses rather than substituting another product. [Native Reader](../../../python/corpus-structure/src/corpus_structure/serve/native_source.py) · [CLI source adapters](../../../python/corpus-structure/src/corpus_structure/cli/source.py) · [MCP source tools](../../../python/corpus-structure/src/corpus_structure/intervene/semantic_server.py)

### Typed content

Represent the printed caption, a loose caption candidate, provider description, child table, formula text, Mermaid code, and relevant picture metadata according to their native kind and source standing. Preserve picture ancestry and repeated source occurrences. A nested caption can carry the parser's attachment. A detached caption remains a separate item and can carry a source-qualified association candidate. Allow one caption to cover multiple panels and distinguish shared caption from same artifact. Figure 3.5 on p108 is a shared-caption case. Pages 301 and 334 support useful descriptions and true printed captions while supplying no structured series. An invented title or a graph-derived estimate cannot replace a printed fact through this read. [Picture and caption mapping](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py) · [Case outcomes](../../design_review/evidence/2026-11-08_chandra-post-nemotron/README.md#executed-cases)

The normal projection traverses picture children and the standard source packet derives text handles from admitted pieces. Chandra table cells or Mermaid code could therefore masquerade as prose if inserted in that route. Keep new evidence in the explicit typed selection with its own locators. Do not feed it into the normal section projection, search index, claim-input handles or selected product through CH-03. Docling's ordinary chunk serializer skips picture children. A `ChunkingSerializerProvider` with `MarkdownParams(traverse_pictures=True)` can include them for a bounded alternate inspection view, but can flatten their distinction from source text. Compare that optional view to the shared typed read. `TreeChunkExpander` and `PageChunkExpander` can supply inspection context where needed. Current sections and occurrence identity govern all normal consumers. [Existing projection](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_hierarchy.py) · [Existing packet handles](../../../python/corpus-structure/src/corpus_structure/semantic/proposals.py) · [Docling serialization and expansion](https://docling-project.github.io/docling/_generated/examples/advanced_chunking_and_serialization/)

### Completion

Starting with a real CH-02 result, verify the same source-qualified evidence through Reader, CLI, MCP and packet, including original image retrieval. Use p108 shared caption, p301 detached captions and figure text, p151 table comparison, p416 readable formula alternative, and the chart and Mermaid fixtures. Verify generated content stays distinguishable in explicit output and is absent from ordinary section text, search, and claim handles. Check unrelated items, wrong pins, inherited region precision, result budgets, unavailable raw output, and a refusal that preserves the incumbent. This is inspection acceptance. CH-04 owns any selected source change and CH-05–06 own future specialist meanings.

<a id="CH-09"></a>
## CH-09 · Deliver attributable structure through normal evidence access

**Proposed implementation · 2026-11-08.** Extend the existing bounded visual evidence
Reader and its CLI, MCP and evidence-packet adapters. A source-scoped manifest from
CH-10 lets callers discover exact settled observations without guessing a latest result.
Explicit CH-02 observations remain usable without that manifest. Filter by exact
published source, observation, page or item, and supported kind before expanding children.
Return exact candidate or relation addresses, producer and field standing, and source
region precision. Use the existing artifact and original-image read. Preserve already
issued cursors and source addresses under their released contract. See [CH-10](automatic-routing-and-qualification.md#CH-10).

Deliver these structures first.

- **Figure and caption discovery.** Offer figure and source panel records, caption
  occurrence and association candidates, literal figure text, and attributed generated
  description as distinct fields. Support a bounded, opt-in typed figure discovery
  query that links back to Reader and original image. Ordinary source search and claim
  packets use only their selected source projection. Use CH-08's qualified relations
  where available. An enclosing picture or several alt strings do not locate individual
  panels. The parser joins nested image alt strings and removes their image elements.
  Preserve useful raw child evidence and keep unlocated children explicitly coarse.
  [Pinned picture mapping](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py#L692-L783) ·
  [Current source search](../../../python/corpus-structure/src/corpus_structure/serve/source_search.py)
- **Rich comparison.** The current visual mapper reduces table cells to text and grid
  attributes. Preserve the Core `RichTableCell.ref` to its exact candidate group when
  present, with a bounded child read, literal/formula alternatives and retained header
  paths. Use original `TableData.table_cells` indexes and spans because the expanded
  grid repeats merged cells. Attach each frame to the level it actually locates. Retain the picture parent
  on chart tables and Mermaid children and apply CH-05's evidence distinctions. A
  readable alternate formula remains a transcription while its grammar is unsupported.
  [Core rich-cell references](https://github.com/docling-project/docling-core/blob/v2.106.0/docling_core/types/doc/items/table/table_data.py#L64-L87) ·
  [Current visual mapper](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_visual_mapping.py)

Preserve raw adapter-returned HTML alongside parsed Docling objects. Use
`parse_chandra_html(..., normalize_heading_levels=False)` for per-page replay, and
normalize heading levels once at the document owner for a qualified outline. A raw
layout label without a dedicated parsed type, such as `Complex-Block` or
`Table-Of-Contents`, can remain attributed discovery evidence. Do not infer its semantics
from a fallback label. If an explicit Markdown export is useful, pass only the selected
bounded typed view to `ChunkingSerializerProvider` with
`MarkdownParams(traverse_pictures=True)`. Keep it a rendering of that view.
[Page parser](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/chandra_utils.py#L832-L903) ·
[Document-wide heading normalization](https://github.com/docling-project/docling/blob/v2.148.0/docling/utils/vlm_utils.py) ·
[Core chunk serializer](https://github.com/docling-project/docling-core/blob/v2.106.0/docling_core/transforms/chunker/hierarchical_chunker.py#L154-L226)

Acceptance uses p108's shared caption and independently checked panels, the adjacent
p301 figures, a rich table cell and an oversize table, and the chart and natural diagram
controls. Include a picture with both a nested chart table and chart metadata. Show a figure query and rich-cell read in the actual Reader and MCP packet,
with exact image navigation. Reject wrong source and observation pins and out-of-scope
children. Keep estimates, Mermaid and generated text out of ordinary sections, search
and claim handles. Check that a known unavailable or partial field remains distinct
from an empty qualified result.
