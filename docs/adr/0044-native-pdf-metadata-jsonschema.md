---
id: ADR-0044
title: Validate lossless PDF metadata with native model-derived JSON Schema
status: accepted
date: 2026-11-01
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: The pinned native validator cannot enforce a released metadata schema or its deployment burden exceeds a conforming native alternative.
---

## Context

PDF metadata includes exact OCR text and other native strings. Segmented bytes can preserve
embedded NUL characters, but PostgreSQL's built-in JSON traversal rejects them, including when
looking up a different field. Converting to JSONB, substituting characters or trusting a client
projection cannot establish lossless native instance enforcement. This surfaced in the actual
PDF-20/21 publication control after byte-field reader integration; all earlier migrations stay frozen.

[D3](../design/D3-database.md#native-pdf-metadata-validation) owns native admission.
The semantic release already owns each metadata class's JSON Schema and projection policy.

## Options

1. Keep generated built-in JSON/JSONB shape checks. This is sufficient for JSONB-safe values,
   but cannot validate all strings admitted by the released metadata schemas.
2. Move metadata schema enforcement entirely to the existing finite Python callback. This
   preserves bytes but gives up independent server-side enforcement of metadata instances.
3. Use the existing packaged `pg_jsonschema` native extension with released JSON Schema.
   This adds one pinned server dependency and supports full schema constraints without
   duplicating a JSON parser or changing stored text. It is selected.
4. Implement a custom parser, character substitution or a second metadata record hierarchy.
   These add avoidable semantic machinery or fail exact-value preservation.

## Decision

Pin `pg_jsonschema`0.3.4 through the existing extension record and provision the dedicated cluster's
templates and owned application database. Metadata admission passes the actual retained JSON text
to schema-qualified `public.json_matches_schema(json,json)`. Generate its schema from the existing
release-bound model boundary, retaining its definitions and constraints. No second schema owner
or generic validation framework is introduced.

Verify typed lookup projections against the same actual value using schema constraints, without
traversing or sanitizing NUL-containing JSON with PostgreSQL's built-in extractors. Preserve exact
metadata byte fields and the ordinary typed/queryable companion envelope. Native byte integrity,
graph/endpoint checks and required Docling/Pydantic callbacks remain separate obligations.
Only scoped health summaries omit diagnostic text; they carry a qualified reference to its exact
metadata record. Full reads and exports reconstruct the original value.

## Consequences

The library owns JSON Schema evaluation; the model owns the schema and projection semantics;
PostgreSQL owns instance admission and immutable custody. Deployment must supply the pinned
extension before the new migration/release is usable. The package is
`postgresql-18-pg-jsonschema=0.3.4-3PIGSTY~noble` in the configured package repository.
Existing provision/startup checks account for its version. No other PostgreSQL cluster is changed.

Validate bounded batches under their actual class schema and avoid unnecessary recompilation or
whole-book aggregation. This makes no performance claim. Actual publication, invalid-value refusal,
lossless export and deployed-book qualification remain with
[PDF-20/21/24/25](../plans/pdf-docling-pipeline_2026-10-31.md); accepting this decision does not close them.
