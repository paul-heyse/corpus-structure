---
id: ADR-0040
title: Maintain the integrated PDF architecture without historical HTML compatibility
status: accepted
date: 2026-10-31
supersedes: [ADR-0039]
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: A maintained go-forward PDF consumer needs a capability lost by retiring a historical HTML contract.
---

## Context

The operator explicitly withdrew compatibility requirements for historical HTML-derived documents
and outputs on 2026-10-31 while authorizing completion of the PDF series. The native PDF baseline
and PDF-13 foundation exist; real multipass recognition, integration and adoption remain open.
[The coordinator](../plans/pdf-docling-pipeline_2026-10-31.md) owns their completion.

## Options

1. Preserve historical HTML readers, ABI branches, source profiles and replay fixtures. This keeps
   dual source semantics and maintenance burden for outputs with no required consumer. Rejected.
2. Delete all archives and generic text/math support. This conflates compatibility with data custody
   and would break current PDF preparation and qualified native reuse. Rejected.
3. Maintain one integrated PDF contract and retire HTML compatibility after migrating its current
   consumers. Selected: narrows semantic authority and interfaces while retaining useful algorithms,
   frozen migration/evidence records and current PDF source reuse without destructive cleanup.

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
   useful derived representation, not the PDF's primary structure or universal identity. Retained
   historical rendition/anchor bytes are not rewritten, but HTML-derived documents and outputs
   have no maintained reader/API compatibility guarantee. New PDF evidence uses qualified identities. Do not force complete PDF-byte lexical partitions through an HTML decoder model.
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
    retained historical answers/grades as inert records. Historical HTML-derived outputs no longer
    require runtime readers, API compatibility or positive replay gates. Remove their adapters and
    compatibility-only tests after current PDF consumers migrate. Never relabel HTML anchors as PDF evidence.
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

This record restates the surviving PDF-only custody, full Docling/RapidOCR+true Nemotron composition,
scoped model authority, integrated selection, typed provenance, intact sections and independent
automated grading requirements. The only retired obligation is maintained compatibility for historical
HTML-derived documents/outputs. Generic release reconstruction and current PDF product pinning remain
necessary; legacy-looking names are not removed until maintained users have migrated.

No database purge or rewriting of historical records is authorized by compatibility retirement.
Frozen migrations, plans and evidence stay. Current models/registrations/dependencies and qualification
are simplified around the integrated architecture. Forward migrations establish its schema; normal
execution must not depend on retired HTML tables or projection conventions. PDF-12/14–16 and PDF-10/11
own implementation, real providers and adoption. Acceptance of this decision does not establish them.
