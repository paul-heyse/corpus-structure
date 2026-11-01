---
id: ADR-0041
title: Publish large PDF companions as bounded native records
status: accepted
date: 2026-10-31
supersedes: []
superseded-by: null
design: [§B4]
evidence: Proposed
revisit: A required canonical artifact approaches PostgreSQL's bytea limit, or an individual native content value exceeds JSONB representation limits.
---

## Context

[D3](../design/D3-database.md) already stores canonical PDF artifact bytes separately from
normalized occurrences, relations and endpoints. The real book's protected publication failed
before semantic checks because its complete envelope was first cast to JSONB. Exact retained
replay contains270,447 valid relations occupying355,630,981 canonical bytes; PostgreSQL18 rejects
that aggregate array at its28-bit JSONB container limit. Its largest relation is25,216 bytes.
The complete canonical artifact is558,190,320 bytes; selected Docling content alone successfully
casts to137,752,426 JSONB bytes. This is an aggregate transport/representation mismatch, not
invalid evidence or a need to split document sections.

[Scoped raw diagnosis](../design_review/evidence/2026-10-31_pdf-integrated-adoption/integration/raw/book-task86-jsonb-field-casts.json)
and [exact prepared sizes](../design_review/evidence/2026-10-31_pdf-integrated-adoption/integration/raw/book-task86-prepared-sizes.json)
retain the failed native cast and independently tested field boundaries. Full-book publication
remains open in the [PDF coordinator](../plans/pdf-docling-pipeline_2026-10-31.md).

## Options

1. Truncate relations, divide semantic sections or remove alternatives. Rejected: changes the
   document/evidence meaning to accommodate a physical representation.
2. Increase PostgreSQL memory/TOAST settings. Rejected: the JSONB container limit is structural.
3. Reuse whole KG Arrow publication. Its typed pgpq COPY mechanisms are useful, but the existing
   canonical binder reaggregates a whole JSONB batch and would reproduce the limit. A new staging
   binder would require independent exact-wire correspondence and additional lifecycle/security
   machinery without a present need to change the logical wire contract.
4. Retain canonical bytea and use PostgreSQL JSON text to decompose bounded records into existing
   relations, narrowing only native content and individual records to JSONB. Selected: preserves
   scoped model authority, independent server checks and current consumer identity while matching
   storage to relational operations. PostgreSQL's native JSON functions supply the mechanism.

## Decision

**Accepted realization target (2026-10-31); implementation and qualification remain in PDF-15/10/11.**
The canonical artifact bytes/digest and single Docling content plus mandatory companion contract
remain unchanged. At protected publication, parse the wire envelope as PostgreSQL `json` text,
then narrow individual companion records into existing typed JSONB/relational rows. Keep the
selected DoclingDocument as native JSONB. The descriptor CHECK and selected-content view must
extract through JSON text before narrowing; no path may reconstruct the oversized relation array.

Generate closed shapes, scalar types, nested records and array cardinalities from the same
trusted model. Preserve all task/attempt/holder fences, archived contract binding, exact replay
bytes/artifact sets, qualified input custody, endpoint existence, selected occurrence inventory,
governing decisions and attributable coverage. Client validation or a claimed hash alone cannot
replace independent server correspondence to the actual wire bytes.

Cache scalar/header values and bounded native content before record loops. JSON text reparses
on access, so do not query the558MB envelope for each occurrence/relation. Extract each wide
array once and process its records; no new workflow, generic graph store or semantic chunking.
Deploy a new frozen forward migration; existing deployed revisions remain unchanged.

## Consequences

Large companion sets become additional rows without a giant JSONB container. Existing scoped
readers already use those rows; explicit whole-artifact exports retain complete canonical bytes.
This changes physical handling rather than recognition, policy, source meaning or claim authority.

JSON parsing and row validation still perform required work, and the retained single bytea artifact
has PostgreSQL's own size boundary. A future larger requirement should revise physical artifact
transport/custody while preserving the logical document, rather than silently discard evidence.
No throughput or universal corpus-fidelity improvement is claimed by this decision. Applicable
native negative controls, exact book publication and assembled consumer qualification remain required.
