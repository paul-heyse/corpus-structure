---
id: ADR-0039
title: Integrate PDF recognizers through one governed document and provenance model
status: accepted
date: 2026-10-31
supersedes: [ADR-0038]
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A required consumer cannot faithfully or reasonably use Docling content plus typed companion relations, or the selected multipass runtime cannot serve the supported workload.
---

## Context

The operator confirmed both integrated-pipeline and governed-content-replacement changes on
2026-10-31 (PDF coordinator RC06/07). The native PDF baseline through 0055 exists. A single-parent
Docling envelope cannot represent raw recognition observations and multiple inputs to reconciliation.
The [review](../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md) and its target at
`d25fff8` recommend a singular downstream document, retaining both providers as attributed evidence.
The [PDF coordinator](../plans/pdf-docling-pipeline_2026-10-31.md) owns delivery and qualification.

## Options

1. Keep two independent provider documents or attach raw JSON. Small initial change, but every
   consumer reconstructs selection and loses shared evidence/lifecycle guarantees. Rejected.
2. Replace both content schemas with an application-owned hybrid. Potentially richer native
   alternatives, but requires replacing hierarchy, table/formula/chart interchange and consumers
   without a demonstrated representation gap. Revisit for an actual required consumer limitation.
3. Select Docling content with mandatory model-owned companion relations and a narrow PDF product
   identity supertype. Selected: preserves native structure, enables one shared read/selection
   boundary and relational custody without pretending recognition receipts are documents. It adds
   projections/migrations and explicit compatibility, while reusing compiler, tasks and publication.

## Decision

**Accepted target (2026-10-31); integration implementation and qualification are tracked in PDF-12–16.**
The native PDF baseline exists; acceptance of this successor does not establish the new provider or consumer capability.

1. PDF is the sole input to new ingestion. Use full Docling StandardPdfPipeline with in-page RapidOCR, table/formula/hierarchy support,
   combined with Nemotron3.5 true page-parse/layout-detection/Table-Chart-crop interpretation.
   Reuse NVIDIA public multipass orchestration rather than rebuild its scheduler and merger.
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
6. One integrated document contract is the selected source-structure product: Docling content
   plus mandatory typed provenance, correspondence, selection and coverage relations. Both recognizers
   retain their immutable raw products. Governed integration may add or replace native content,
   preserving alternatives and reasons; consumers do not merge providers independently. Build only purposeful, source-qualified
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

12. A PDF-scoped product supertype owns qualified identity/custody for native documents,
    recognition observations and integrated documents. Typed bodies preserve their different meanings.
    Multiple direct input relations replace single-parent-only provenance; optional structural parent
    remains a compatibility convenience. Publish complete immutable input sets atomically, admitting
    only prior published input pins before inserting a new product. No forward/self inputs or later
    edge mutations are allowed. This establishes acyclicity without a global graph lock. Backfill old
    identities/parent edges without changing native payloads or claiming new recognition.
13. Raw request success/failure receipts survive later-pass failures. Product admission, request
    completion, source fidelity and coverage remain separate. Provider-coordinate mappings grant only
    precision actually established; unboxed math does not acquire exact PDF glyph positions. Model
    agreement from one family is correlated evidence, not independent truth.

## Consequences

All surviving PDF-only custody, scoped schema authority, precise occurrence/address distinctions,
intact sections, lazy scientific interpretation, consolidation authority, protected lifecycle and
independent automated grading clauses are restated above. The Standard-only/conditional secondary
interpretation target is replaced; an integrated selection can use either provider. HTML5 repair,
original-TeX acquisition and active HTML writers are not reintroduced. ADR-0024/0035 govern unaffected
semantic release and scientific responsibilities. No new scheduler, cache or universal ontology is added.

PDF-13 implements contracts/storage/reads; PDF-14 supplies real inference and PDF-15 selection;
PDF-16 migrates actual consumers. PDF-10/11 retain operational cutover and assembled qualification.
An isolated pinned runtime avoids root dependency conflicts. Bounded page preparation and shared
resource ownership prevent whole-book hydrated-state amplification. Keeping raw responses permits
policy-only remapping without model work. No speed, capacity or fidelity improvement is established
by this decision. Provider mapping and local runtime investigations remain explicit prerequisites.
