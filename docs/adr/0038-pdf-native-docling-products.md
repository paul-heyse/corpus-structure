---
id: ADR-0038
title: Use PDF-native Docling products under governed domain contracts
status: superseded
date: 2026-10-31
supersedes: [ADR-0036, ADR-0037]
superseded-by: ADR-0039
design: [§B4, §B5]
evidence: Proposed
revisit: A required PDF capability cannot preserve source-qualified relationships or honest recognition health through StandardPdfPipeline, or an actual intact section exceeds a required consumer's capacity.
---

## Context

The operator selected PDF as the sole new pipeline input, StandardPdfPipeline with OCR and
formula enrichment, native DoclingDocument JSON in PostgreSQL, and intact section/subsection
organization. RC01–RC05 of the [PDF functional review](../functional_reviews/pdf-docling-pipeline_2026-10-31.md)
were explicitly accepted on 2026-10-31. Section chunking is excluded until an actual required
consumer encounters a demonstrated oversized-section problem. The [PDF coordinator](../plans/pdf-docling-pipeline_2026-10-31.md)
owns execution, investigations and acceptance.

ADR-0036/0037 established immutable source custody, qualified occurrences and parsing layers,
but also retained HTML5 repair, original TeX/macro acquisition, canonical-only evidence anchors
and particular frontend stages. PDF conversion changes those source assumptions and the actual
packet, frame, query and mathematical input contracts. Native structured JSON must be consumed,
not attached passively to an unchanged HTML-shaped primary representation.

## Options

1. Keep the HTML-shaped model and attach Docling JSON. This minimizes initial migration but
   retains duplicate parsing/reconstruction, hides native tables/formulas/regions from consumers,
   and makes the document's new semantics subordinate to incidental old storage contracts.
2. Re-author every Docling type in LinkML or create a separate document/workflow service. This
   duplicates upstream meaning or operational ownership and adds synchronization, conversion and
   maintenance work without a corresponding required consumer.
3. Use native Docling JSON under scoped schema authority, with governed application operations
   and useful derived views. Selected. It preserves rich native structure while current Core/native
   custody and operation ownership continue to serve bounded consumers. It requires versioned
   contract migration and explicit native health/coverage qualification.

## Decision

**Accepted target; Proposed implementation (2026-10-31).** No PDF producer, migration, default
cutover or corpus qualification follows from accepting this record.

1. PDF is the sole input to new ingestion. Use StandardPdfPipeline, OCR enhancement, table
   structure, formula enrichment and heading-hierarchy recovery through qualified native adapters.
   Source-to-PDF rendering is upstream and outside this capability. Installing full Docling and
   all operator-selected extras does not activate other input formats or every model stage.
2. Retain original PDF bytes in PostgreSQL bytea before conversion, independent of success.
   Store immutable native DoclingDocument JSON in JSONB, separately linked to conversion health,
   source acquisition, specification, producing task/release and artifact custody. A correction or
   organizational transformation creates a derived product; it does not mutate native conversion.
3. Docling/core owns its versioned native schema. LinkML/trusted execution definitions govern
   application concepts, operations, relationships, identity/dependency recipes, states, coverage
   and effects. Archive the supported upstream schema and runtime/model bindings; do not maintain
   a competing hand-authored copy. Shared Core metadata, JSON Schema/Pydantic boundaries and
   selected analytical/ontology views realize scoped contracts, not independent policy authorities.
4. Use conversion-qualified native pointers and independently identified ordered relationships.
   Repeated equal text/formulas remain separate occurrences. PDF physical pages/point regions,
   native text spans, recognized LaTeX offsets and derived text projection offsets are different
   address spaces. An item box does not establish glyph alignment; recognized LaTeX is not the
   author's original TeX. Preserve explicit partial/unknown fidelity and multiple source regions.
5. Sections/subsections organize the document. Heading levels require verified containment;
   use a derived DoclingDocument when native output lacks section groups, preserving source
   pointer mappings and body reading order. No section chunks, token windows or chunk subsystem
   are introduced. Batches/transport pages are execution units, not semantic document parts.
6. Native Docling JSON is the source-structure product. Build only purposeful, source-qualified
   item/edge/region/cell indexes and text views for actual operations. Canonical text remains a
   useful derived representation, not the PDF's primary structure or universal identity. Existing
   historical rendition/anchor meanings remain unchanged; new PDF evidence uses new qualified
   identities. Do not force complete PDF-byte lexical partitions through an HTML decoder model.
7. Separate conversion lifecycle, per-stage health, recognition coverage, structural validity,
   mathematical interpretation and source fidelity. Formula labels/nonempty text do not certify
   successful enrichment. Inline and table-cell mathematics require their own qualified support;
   unsupported output never establishes absence. Required gaps remain open with an actionable
   inspection/reconversion or supported-extension route, not optimistically admitted metadata.
8. Formula items supply recognized LaTeX directly to native mathematical parsing. Retire obsolete
   HTML delimiter, macro-acquisition and rendering-conversion work as consumers migrate. Preserve
   occurrence multiplicity/positions, explicit ambiguity, scoped declarations/forward applicability,
   binder identity, assumptions and definedness. Native SymPy remains mathematical machinery,
   not source-occurrence authority. Preserve weak/strong demands and do no hidden stronger work.
9. Version method contracts, source addresses, packet/source-frame evidence and actual consumers
   together. Agents receive section ancestry, relevant items/cells/formulas/captions, regions and
   health bound into packet identity. Document labels are attributed recognition, not truth;
   only consolidation writes knowledge claims. Physical page breaks do not terminate logical scope.
10. Reuse existing run/task/attempt fences, immutable dependencies, protected atomic publication,
    producing-build selection and archived readers. Prepare native work outside publication locks;
    one declared semantic distinction does not require one task/transaction. Bound the combined
    parser/model/image live state and use native batching/cleanup before adding operational layers.
    Ambiguous selection and corrupt products refuse rather than silently choose latest or rebuild
    valid-looking history. No second scheduler, workflow interpreter or generic cache is added.
11. Preserve independent automated reference preparation, evaluator authority, grading policy and
    historical answers/grades. Historical records remain readable without retaining active HTML
    conversion or promising to rerun retired adapters. Never relabel HTML anchors as PDF evidence.
    Preserve frozen migrations and prior evidence; actual retirement/adoption belongs to PDF-10/11.

## Consequences

This consolidates the surviving clauses of ADR-0036/0037 under PDF-native source semantics.
Immutable custody, qualified relationship/derivation meaning, lazy demands, native publication and
historical/evaluation protection survive. Mandatory HTML5 repair, original-TeX/macro provenance,
universal canonical-only evidence and particular HTML-oriented lexical/structural stages are
replaced for new PDF ingestion. Existing HTML implementation/evidence remain accurately labeled
until the PDF packages replace their active consumers. ADR-0024/0035 continue to govern unaffected
release/semantic and scientific preparation responsibilities; they are not superseded.

Native JSON plus bounded projections buys native interchange and efficient selective access at the
cost of projection/index publication and explicit compatibility handling. Selective OCR/layout and
formula enrichment perform different work from HTML processing; no speedup, universal mathematical
coverage, exact transcription or source-fidelity improvement is claimed. PDF-01 resolves mechanisms
and limits, PDF-02/03 implement contracts/storage, PDF-04–09 integrate producers/consumers/runtime,
and PDF-10/11 own retirement, actual adoption and qualification. Library internals do not become
ontology instances merely to assert completeness of the application model.
