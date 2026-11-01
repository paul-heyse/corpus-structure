# Structured payload model and persisted semantic validation

**Status:** Planned; implementation and qualification not_run. **Created:** 2026-11-01.
The [coordinator](../pdf-docling-pipeline_2026-10-31.md) alone owns PDF-27/28, investigation
I21–I25 and source-qualified recommendation dispositions. Basis: [structured-data review](../../plan_improvement_reviews/pdf-docling-structured-data_2026-11-01.md)
I01–I09 at `e11c89db`, consuming product baseline `0878ba1b`. Operator confirmed both rule
changes on2026-11-01 and approved this plan-authoring scope. This document schedules product
changes; it establishes no deployed enforcement change.

## Target and foundation assessment

A complete domain model governs schemas, relationships, operations and transitions regardless
of where bytes reside. Docling/core owns native content definitions; LinkML/trusted semantic
releases own application payloads, mappings, validation placement and lifecycle. Arrow is a
physical representation derived from these authorities, not an independent ontology. PostgreSQL
owns transactional custody and the relationships/lookup projections that SQL actually uses.

Start with page-scoped OCR/candidate payloads. OCR is used by discovery, alignment, enrichment,
coverage and replay, not only validation. Preserve word indexes, spans, frames, confidence,
source evidence and candidate correspondence. Keep hierarchy/order/native addresses, distinct
occurrences, relation endpoints, selected inputs and coverage/support queryable where existing
SQL joins require them. Do not scalarize every OCR word solely for storage or hide required
relationships inside opaque values. Page storage units never split semantic sections.

Source ABI17/compiler4/core0.6.4 includes0065; the owned application remains0060/compiler14/core0.6.2.
Existing exact metadata bytes and single-cursor exports already solve important fidelity/access
problems. `semantic/pdf_record_model.py` currently derives SQL-shaped Arrow fields, with JSONB
as strings; that is not the nested payload target. `pdf_record_reader.py::native_product_values`
explicitly hydrates the whole native product; `native_metadata` lacks page selection. Native
reading-order/heading finalization still materializes global state. These are distinct boundaries.

The existing [Arrow26 probe](../../design_review/evidence/2026-11-01_pdf-structured-data/README.md)
shows construction and `validate(full=True)` accepting nulls under non-nullable declarations and
ignoring range metadata. Structural validation cannot establish requiredness or domain validity.
No storage-speed or global-memory benefit has been measured. Apply core3.3/heuristics1.0 and the
applicable profile/binding: preserve fidelity, ownership and evidence closure while removing
unnecessary representations and repeated work. No broad audit, generic registry or proof service.

## Confirmed authority changes and dependency route

Coordinator RC10/11 record explicit **Adopt both changes**,2026-11-01:
qualify ADR-0042's mandatory independent PostgreSQL interior validation for selected families;
qualify ADR-0044's mandatory native JSON-schema route where SQL no longer interprets interiors.
PostgreSQL still enforces custody, release/source/attempt bindings, declared relational invariants
and atomic publication. This intentionally changes assurance placement; it is not independent
server validation under another encoding.

PDF-27 first schedules a successor ADR through the existing decision process, superseding the
affected clauses of immutable ADR-0042/0044, and updates DESIGN §B4 and affected D1/D2/D3/D4/D6/D8
owners. Accepted ADRs are not edited during plan authoring. Preserve ADR-0043 exact-byte/logical/
export distinctions. Every committed migration through0065 stays frozen; PDF-25 supplies forward
revisions and explicit retained-data derivation. No default changes follow from successful probes.

<a id="PDF-27"></a>
## PDF-27 — Payload contracts and prepared representation bridge

**Inputs:** RC10/11 decision slice; existing PDF-18/19 release, identity and artifact contracts;
I21 type profile and early I23 reader needs. **Outputs:** executable per-family declarations,
prepared codecs and projection mappings, integrated with the first OCR/candidate consumer.

Extend existing semantic release/dependency/artifact facilities with each selected family's logical
owner/schema, encoding/profile, retrieval unit, invariant/validator owner, publication scope and
required projections. Reuse generated Core/boundary products; do not create another hand-maintained
schema authority or general Arrow-schema registry. A new family should add declarations and a
finite adapter where necessary, without duplicating storage and validation policy in each reader.

Use explicit `pa.field`, `pa.struct`, `pa.list_` and appropriate offset types for actual page
structures. Preserve absent/default/explicit-null distinctions, list/map ordering, original indexes,
exact strings including NUL, float semantics and stable variant tags. A missing value must not
be silently converted to an empty collection. I21 determines the smallest complete supported
profile, including custom native values and actual Python/Rust interchange requirements. Unsupported
schema evolution refuses with a located field/type rather than dropping information.

Prepare native model validators and reusable Pydantic `TypeAdapter` instances per pinned contract,
not per row. Derive mappings from native definitions and application declarations, distinguishing
validation and serialization schema modes, aliases, fields-set, coercion, unknown fields and
custom serializers. Native methods remain responsible for native behavior. `model_dump` is not
zero-copy and shape-only JSON Schema does not reproduce Python/native validators. Existing lowering
already excludes computed fields; retained `TableData.grid` derivation remains migration-only.
Generalize the successful explicit native-class inventory rather than selecting whichever union
branch happens to validate first. Preserve subclass content deliberately under the pinned profile.

For selected whole-page consumption, start with self-contained `ipc.new_stream/open_stream` units
in existing bytea/artifact custody. `Schema.serialize`/`ipc.read_schema` can archive the physical
schema under the existing release. Bare `RecordBatch.serialize` messages are not self-contained
schema/dictionary custody. Compare `new_file/open_file/get_batch` only for a real seekable batch
consumer. Existing bounded artifact parts remain available for unusually large individual pages;
no value approaches the PostgreSQL approximately1GiB limit. Grouping pages needs demonstrated
retrieval/locality benefit and retained per-page indexing; never default to a whole-book blob.

Select Arrow where consumers can retain useful typed arrays; exact JSON bytes remain the simpler
option for families with only native-object reconstruction and no columnar advantage. Native
composites/domains are alternatives for stable cohesive SQL-operated values, not a universal
replacement: composite declarations alone do not carry field NOT NULL/CHECK constraints; arrays
need deliberate shape rules, and PostgreSQL text still excludes NUL. Psycopg `CompositeInfo` /
`register_composite` plus Core bind/result mapping would need qualification if that route is selected.
Neither ADBC nor pgpq automatically maps arbitrary nested Arrow types into PostgreSQL types.

**Completion:** independent expected cases establish selected payload round trips, exact native
variants/presence and required projections, including empty/null/default cases and unsupported
schema changes. Trace a candidate to its original OCR word/pixels and a claim through selected
input relations. Broad replacement of rich table/chart/native interiors waits for a total pinned
mapping and useful selective consumer; I21/I23 must explicitly select or defer each such family.

<a id="PDF-28"></a>
## PDF-28 — Complete semantic validation over persisted payloads

**Inputs:** PDF-27 agreed family/identity contracts; I22 boundary decision; PDF-20 durable payload
read/adoption slice. **Outputs:** model-bound validation over actual frozen members and a result
consumed by PDF-21. Publication SQL remains owned by PDF-20/21, not duplicated here.

Reuse `semantic/pdf_ocr_contracts.py` and native/app validators. Separate IPC/buffer checks from
required fields, finite ranges, word/line substring equality, raster-to-PDF geometry, candidate
endpoints, alignment reports, coverage and whole-product closure. Arrow kernels may implement
batch-shaped rules only where equivalent semantics are established; arbitrary Python validators
do not automatically compile to kernels. Independent expectations must expose wrong validators.

Close the specific persisted-union gap: `pdf_publication.py` captures header/native/membership/
artifact families for native callbacks, while OCR companion metadata is omitted. Its native child
validates the Docling graph; per-row metadata JSON Schema does not establish the cross-field rules
called by `pdf_contracts.py` on producer drafts. This does not imply OCR was never checked upstream
or malformed corpus data was published. Include the actual frozen OCR/candidate/report payloads
and necessary joined projections/inputs in the validation scope before relying on their validity.

Read durable immutable members, check exact byte/schema/release bindings and evaluate page-local
rules incrementally; evaluate cross-page/reference/coverage closure over the complete required
set. Bind the existing validation result to frozen membership, relevant dependencies and validator
implementation contract. Reuse established validity while those premises hold. A caller boolean,
schema label, physical checksum or native-only callback cannot stand in for semantic validity.

Keep current claim/attempt/holder authority, cancellation, heartbeat, finite child settlement and
freeze/result/seal lifecycle. PostgreSQL verifies the matching validation result and relational
premises at short seal; failed/missing/stale results refuse publication. A changed payload,
projection, source, model release or required membership invalidates the affected result. Keep
native graph materialization explicit where needed, without another whole-book companion object.

**Completion:** structurally legal payloads with bad offsets, out-of-page coordinates, omitted
candidate targets, false complete coverage, required nulls or wrong embedded schema fail before
public use. Exercise mismatched projections, stale membership/result, cross-source references,
conflicting replay and cancellation. Successful validation must not expose private data; tests of
seal verify the actual immutable stored bytes and corresponding release, not detached drafts.

## Integration with existing package owners

| Owner | Concrete amendment and completion boundary |
|---|---|
| PDF-18/19 | Consume PDF-27 placement/bridge; retain genuine SQL relations and derive read-only projections from one pinned authority. Keep exact byte folds, logical identity and export SHA distinct across compression/dictionaries/rebatching. |
| PDF-20/21 | Adopt bounded payload units and projections in the existing SQLAlchemy-owned transaction; preserve durable append/freeze/fences/seal/recovery. Replace selected per-field schema compilation with PDF-28 validation. Inventory remaining pg_jsonschema consumers before relaxing its dependency; preserve necessary SQL-used validation. |
| PDF-22/23 | Produce/consume selected typed page units; bind effective native options and source/image lifetimes. Use one native-serializer-aware envelope instead of JSON encode/decode/encode. |
| PDF-24 | Page/group/field selectors locate data before decoding; return owned batches to columnar consumers, retaining explicit native materialization only for native behavior. Maintain relational context joins and full exports. |
| PDF-25/10/11 | Forward migration and retained derivation, current consumer cutover, removal of replaced machinery, book publication and actual evidence-aware adoption. No second authoritative store or duplicate acceptance queue. |

I23 also assesses `pdf_record_context.sql`: retain occurrence→endpoint and coverage→input/mapping
joins, but offer their set-shaped result to large-context consumers instead of obligatorily
materializing one JSONB envelope. Convenience envelopes need a supported scoped use; pagination
or response limits alone do not establish bounded examined work. Preserve repeat occurrences and
qualified pointers even when values/endpoints match.

## Investigations and execution fit

The coordinator owns I21–I25 state. These questions refine implementation within the accepted
hybrid target; a new rule impact returns for operator confirmation before dependent work.

| Investigation | Method, decision output and constrained work |
|---|---|
| I21 — Complete type/bridge profile | Inspect pinned native/app definitions and consumers; probe only uncertain variants/presence/extensions. Decide supported mappings, located refusal and actual cross-language needs. Required before PDF-27 codecs and broad native replacement. |
| I22 — Persisted semantic coverage | Trace existing validators through frozen read/result/seal; use deliberate invalid persisted cases. Specify exact page-local and complete-set inputs and result binding. Blocks PDF-28/21 acceptance until closed. |
| I23 — Selective access and placement | Trace actual discovery/alignment/diagnostic/section/export journeys. Compare typed units with current exact JSON and identify queryable projections. Blocks the affected PDF-27 family choice and PDF-24 migration, not unrelated native-profile work. |
| I24 — Complete operation comparison | Compare encode→store→retrieve→validate→use on representative selected pages/section/export, including copying, schema preparation, compression/TOAST and conversion. Choose the simpler useful route; measurements precede numerical benefit claims, not a synthetic IPC-only ranking. Owned by PDF-20/24/25. |
| I25 — Effective options and image lifetime | Inspect actual prepared native stages and later crop consumers; decide required crops versus retained full rasters/exact rerender from original, including recovery/cancellation. PDF-22/23 own implementation; retain I14's materialized global boundary. |

Use the same transaction/pool owner for publication and checked Psycopg COPY access; do not layer
psycopg-pool around SQLAlchemy or introduce an ADBC writer needing another transaction. Pglast
parsing does not compile PL/pgSQL bodies: qualify generated routines in actual PostgreSQL catalog
context. Core expressions are suitable for relational operations; SQL authoring simplification is
not a new lint or validator framework. No unrelated PG-00–12 dependency upgrades are absorbed.

## Capability references and selection conditions

Context7 was consulted first during preparation and authoring, followed by primary/pinned sources.
Arrow26/Pydantic2.14.1/Settings2.16.1 and Docling2.145/core2.105/schema1.10.0 are the inspected
baseline. General latest documentation is orientation, not evidence that every newer API is installed.

| Mechanism / references | Intended use and material limit |
|---|---|
| [Arrow IPC](https://arrow.apache.org/docs/python/ipc.html), [read options](https://arrow.apache.org/docs/python/generated/pyarrow.ipc.IpcReadOptions.html), [write options](https://arrow.apache.org/docs/python/generated/pyarrow.ipc.IpcWriteOptions.html) | `IpcReadOptions.included_fields` selects top-level fields during deserialization; it does not make PostgreSQL fetch part of opaque bytea or prune nested children. Compare `IpcWriteOptions(compression=...)` with TOAST; dictionaries add ownership/unification conditions. |
| [Arrow nested types](https://arrow.apache.org/docs/python/data.html), [repo reference](../../libraries/pyarrow.md) | Keep `RecordBatchReader`/arrays through real computation. Assess `compute.struct_field`, `list_flatten` and `list_parent_indices` for needed nested projections; preserve explicit word/index identities and null semantics when flattening. DuckDB/Acero are existing analytical options, not new engines to install. |
| [Pydantic performance](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/performance.md), [serialization](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/serialization.md), [repo reference](../../libraries/pydantic.md) | Reuse TypeAdapter; native `model_validate`, serialization modes and `model_fields_set` preserve their distinct responsibilities. Do not replace custom serializers with a raw field walk or assume Arrow→Pydantic zero-copy. |
| [Settings](../../libraries/pydantic-settings.md) | Nested `BaseSettings` and explicit `settings_customise_sources` precedence resolve resource/transport configuration before worker/model creation. Capture requested and effective native settings; producing interpretation choices belong to the recipe, domain policies remain release-owned. |
| [PostgreSQL18 TOAST](https://www.postgresql.org/docs/18/storage-toast.html), [storage assessment](../../libraries/postgresql/Storing_complex_PyArrow_schemas_and_data_in_postgresql.md) | bytea/existing parts preserve opaque structure. `EXTERNAL` avoids TOAST compression and aids uncompressed substring reads, with a storage tradeoff; it supplies no Arrow range adapter. Large Objects, Parquet and columnar extensions require a demonstrated separate benefit. |
| [Docling](../../libraries/primary_intake/docling.md), [OCR](../../libraries/primary_intake/docling_ocr.md), [triple-pass reference](../../libraries/primary_intake/docling_nemotron_triple_pass_reference.md), [integration review](../../functional_reviews/docling-nemotron-triple-pass_2026-10-31.md) | Preserve native hierarchy and one integrated content graph plus companion, original provider submissions and alternatives. Native reading-order/heading methods remain global; filters/concatenation do not establish equivalent independent page inference. |

PDF-22/23 generalize the effective1.67 formula raster-scale correction into the prepared runtime
profile. Compare required crops/exact rerender with all-page raster retention under original/backend/
frame/crop recipe, retaining exact submitted provider evidence. In isolated native validation,
assess using the owned immutable input as the comparison original instead of two `deepcopy` calls;
retain a private validation copy and mutation refusal. Establish unchanged rejection behavior before
claiming savings. These work-removal opportunities can proceed independently of broad native Arrow
replacement once their contracts are agreed.

## Execution sequence and acceptance

Agree PDF-27 authority/placement and I21/I23 contract slices first; implement codecs with the first
page consumer. PDF-20 adoption and PDF-28 validators can then converge on actual frozen inputs;
PDF-21 publication acceptance requires both. PDF-24 migrates the affected consumers alongside the
new representation. PDF-25 performs forward deployment/retained derivation after working readers
and validators; PDF-10/11 own actual external/provider/evaluator/default adoption. I25 and local
serialization/copy improvements need not wait for unrelated type experiments. Shared model/compiler
surfaces retain one integration owner; packages are not automatic agent or worktree assignments.

Targeted checks accompany coherent functional changes. PDF-11 defines the revised required union
before final qualification, preserving independent original-PDF expectations and failed/interrupted
receipts. Include shuffled page selection without unrelated-book decode, one formula diagnostic,
a large intact section, full export, exact native variants/presence, projection corruption,
semantic-invalid payloads and interruption before/after append/freeze/seal. Final functional and
applicable hygiene checks follow complete scope; numerical benefits need complete-operation
measurements. Existing formatting does not invalidate otherwise applicable types/tests.
