# Structured payload model and persisted semantic validation

**Status:** Implemented and targeted Tested2026-11-01 for PDF-27/28; enclosing PDF adoption remains open. **Created:** 2026-11-01.
The [coordinator](../pdf-docling-pipeline_2026-10-31.md) alone owns PDF-27/28, investigation
I21–I25 and source-qualified recommendation dispositions. Basis: [structured-data review](../../plan_improvement_reviews/pdf-docling-structured-data_2026-11-01.md)
I01–I09 at `e11c89db`, consuming product baseline `0878ba1b`. Operator confirmed both rule
changes on2026-11-01 and approved this plan-authoring scope. The [integration review](../../plan_improvement_reviews/pdf-postgresql-capability-integration_2026-11-01.md)
at `94c847cc` refines this target with shared PostgreSQL realization and Arrow processing.
RC12 (explicitly confirmed2026-11-01) selects rebuilding current products from compatible retained
evidence, retiring mandatory historical reader/layout migration. This document schedules product
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

Implementation baseline refreshed2026-11-01: PostgreSQL capability scope merged into main;
compiler19 adds archived model/codec/frozen-validator sources. The forward native successor is
`semantic_pdf_20261101` (0067) over `semantic_pg_20261101` (0066). The shared deployed book remains
0060/compiler14/core0.6.2, untouched. Native reading-order/heading finalization still materializes
global state; this package does not claim to remove that boundary.

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
revisions against the settled head and current-realization rebuild (RC12). Preserve retained
evidence, not mandatory old published-pin readers. No default changes follow from successful probes.

<a id="PDF-27"></a>
## PDF-27 — Payload contracts and prepared representation bridge

**Inputs:** RC10/11/12 decision slice; existing PDF-18/19 release, identity and artifact contracts;
I21 type profile and early I23 reader needs. **Outputs:** executable per-family declarations,
prepared codecs and projection mappings, integrated with the first OCR/candidate consumer.

Compose existing release/compiler preparation with PG-03 typed generation and PG-06
`CompanionProjection`; PG-04 `ArrowWriteProfile` handles directional SQL transfer. Keep four
contracts explicit: logical family schema, nested payload codec, relational projection and SQL
wire profile. Static `TypedColumns`/`Named` and table-valued `.with_cols()` describe SQL-visible
columns, not native payload semantics or validation. Extend these generators for envelopes and
necessary projections; finite payload codecs derive from native/app authority rather than form
another schema compiler. Preparation binds semantic release, codec/mapping, physical/compiler,
projection and directional profile identities; it retains no live connection or privilege conclusion.
A same-typed field meaning change must invalidate affected preparation even when SQL types agree.

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
in existing bytea/artifact custody. Reuse `ArrowWriteProfile.new_encoder` and
`copy_arrow_stream` for outer SQL envelopes/parts, not to convert every nested interior to SQL
arrays/composites or JSON strings. Keep a fresh pgpq encoder per stream. Existing Python rows use
Psycopg `Copy.set_types/write_row`; resident relational movement uses server-side set operations
such as Core `Insert.from_select`, with defaults/correlation semantics checked. ADBC-owned ingest
is an alternative only for a complete justified operation; it cannot share another session's scratch.
Directional binary/large-binary and nested support must be qualified for the selected driver.
`Schema.serialize`/`ipc.read_schema` can archive the physical
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

Use owned `RecordBatchReader`/batch iteration for real columnar consumers;
`from_batches(schema, iterable)` adapts an actual producer without a full `Table`.
`compute.struct_field`, `list_flatten`, `list_parent_indices`, `filter`, `take`, `is_valid`,
checked arithmetic and explicit Kleene/null policies can perform selected projections/rules.
Preserve original indexes and null/empty/absent state before flattening; do not reconstruct all
Python objects between each stage. `RecordBatchReader.cast` is lazy but requires an authorized
safe conversion with matching names/order; it is not permission to repair mismatched exact profiles.
Use Arrow C Stream/PyCapsule only with actual compatible consumers, not a bespoke interchange layer.
Keep DuckDB for existing relational analytics; Acero is a candidate only to remove a real local
projection/filter intermediate. Native/custom validators retain semantics not expressed by kernels.

A typed derivative of existing `PdfCoverageSupport` is conditional on an actual support-analysis
consumer: current PG companion `supports_json` is not already a typed nested list. Derive its
list/struct representation from the same model, or a protected support-row projection for SQL
joins; preserve parent coverage identity and qualified inputs. Do not add another support authority.

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

Extend the existing frozen child's validation-derived projection phase and the parent's bounded
adoption to emit required page projections from the exact validated persisted payload. Retain
early SQL locator/custody fields and independent relationship enforcement. A contradictory supplied
projection must refuse; avoid a second producer-owned mirrored-fact/projection coordinator or
loading page-local payloads into the materialized native graph merely to derive them.

Read durable immutable members, check exact byte/schema/release bindings and evaluate page-local
rules incrementally; evaluate cross-page/reference/coverage closure over the complete required
set. Bind the existing validation result to frozen membership, relevant dependencies and validator
implementation contract. Reuse established validity while those premises hold. A caller boolean,
schema label, physical checksum or native-only callback cannot stand in for semantic validity.

Reuse PG-02 outcome semantics and PG-05 `BorrowerCancellation`/`owned_adbc_read` at the actual
operation owner. One regular Psycopg pool lends through SQLAlchemy `NullPool`; Core owns its
transaction and COPY borrows that driver. ADBC owns its separate imported snapshot. Close/drain
results, settle effects and retire cancellation registration before reuse. Database cancellation
cannot stop a CPU validation child or another driver's query; retain finite child settlement.
Distinguish cancellation/fencing, rollback and uncertain commit, resolving the original publication
identity rather than replaying under a new one. A trusted child result bridge is not invalid merely
because its protected registration uses a boolean; its enforced input/result binding is decisive.

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
| PDF-25/10/11 | Current-realization forward construction and compatible retained-evidence rebuild, current consumer cutover, removal of replaced machinery, book publication and actual evidence-aware adoption. No second authoritative store or duplicate acceptance queue. |

I23 also assesses `pdf_record_context.sql`: retain occurrence→endpoint and coverage→input/mapping
joins, but offer their set-shaped result to large-context consumers instead of obligatorily
materializing one JSONB envelope. Convenience envelopes need a supported scoped use; pagination
or response limits alone do not establish bounded examined work. Preserve repeat occurrences and
qualified pointers even when values/endpoints match.

## PostgreSQL prerequisites and current adoption boundary

The [PG coordinator](../postgresql-capability-leverage_2026-11-01.md) owns the merged prerequisite
implementation and its dated319-case targeted receipt. This package consumes those actual interfaces;
that prior receipt does not qualify these subsequent PDF changes. No worktree or unmerged prerequisite
remains. Disposable current-realization databases qualify the new forward native revision without
upgrading the shared deployed book.

| Required capability | PG owner | PDF integration responsibility |
|---|---|---|
| Model-derived typed projections/preparation | PG-03/06 | PDF-27 extends generators/profiles, then PDF-24 migrates its actual callers. |
| Shared same-session COPY | PG-04 | PDF-20 supplies authenticated target, limits, identity and protected adoption; PG supplies transfer mechanics. |
| Outcomes, borrower/cancel settlement | PG-02/05 | PDF-20/21/24/28 propagate handles through actual cursors/results, frozen validation and publication. |
| Selected-source context and detached capture | PG-06/10 | PDF-24 consolidates closure and adds payload locators; it does not copy serializers or force Arrow through JSONL. |
| Native authoring, source diagnostics, current head | PG-01/08/09/11 | PDF-27/25 consume Plugin/NativeTransitionOp/render/admission on caller Connection and select the actual successor revision. |

Contract agreement permits independent design work; live acceptance requires working relevant
prerequisites. Do not wait for unrelated PG packages or implement substitute authorities while
waiting for integration. Shared editing/native-generation surfaces need one integration owner.

## Investigations and execution fit

The coordinator owns I21–I25 state. These questions refine implementation within the accepted
hybrid target; a new rule impact returns for operator confirmation before dependent work.

| Investigation | Method, decision output and constrained work |
|---|---|
| I21 — Complete type/bridge profile | Inspect pinned native/app definitions and consumers; probe only uncertain variants/presence/extensions. Decide native/nested mappings versus flat read/write profiles, metadata/presence rules, located refusal and actual cross-language needs; reuse PG generators. Required before PDF-27 codecs and broad native replacement. |
| I22 — Persisted semantic coverage | Trace existing validators through frozen read/result/seal; use deliberate invalid persisted cases. Specify actual page-local/complete-set inputs, validation-derived projections and result binding; reuse PG lifecycle, which does not supply missing semantic checks. Blocks PDF-28/21 acceptance until closed. |
| I23 — Selective access and placement | Trace actual discovery/alignment/diagnostic/section/export journeys. Compare typed units with exact JSON; reuse PG selected-context/projection contracts, consolidate context selectors and define page/field locators. Blocks the affected PDF-27 family choice and PDF-24 migration, not unrelated native-profile work. |
| I24 — Complete operation comparison | Compare encode→store→retrieve→validate→use on representative selected pages/section/export, including unified COPY, detached capture, nested computation, copying, preparation and compression/TOAST. Choose the simpler useful route; measurements precede numerical benefit claims, not a synthetic IPC-only ranking. Owned by PDF-20/24/25. |
| I25 — Effective options and image lifetime | Inspect actual prepared native stages and later crop consumers; decide required crops versus retained full rasters/exact rerender from original, including recovery/cancellation, Arrow thread/readahead and backing-buffer lifetime. PDF-22/23 own implementation; retain I14's materialized global boundary. |

Retain one regular Psycopg physical pool with SQLAlchemy `NullPool` lending/return; Core owns
publication transactions and COPY borrows the checked driver. Do not add another pool or introduce
an ADBC writer inside that transaction. Pglast
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

## Conditional consumer improvements

PDF-24/25 may use a verified manifest's exact file list and schema with
`dataset(...).scanner(columns=..., filter=...).to_batches()` for an actual detached Arrow consumer.
Retain direct DuckDB/Parquet for existing SQL consumers rather than insert another scan. Qualify
Parquet `ARROW:schema`/type fidelity independently of exact IPC; no new archival copy by default.
`IpcReadOptions.included_fields` prunes top-level deserialization, not PG bytea transfer or nested
children. Coordinate `use_threads`, batch/fragment readahead and reader/backing-buffer ownership;
small batches/Arrow allocation counters do not bound whole-operation memory.

For an actual codec/projection/native-version refusal, reuse PG-07 `ci db describe` and PG-09
source-qualified candidate/admission diagnostics for declared-versus-observed bindings and concrete
existing remediation commands. Physical/query schema is not opaque payload schema or domain
validity. No alignment gate, daemon or new capability registry is selected. Both enhancements
retain explicit triggers/disposition in the coordinator; they do not block initial atomic completion.

## Execution sequence and acceptance

Agree PDF-27 authority/placement and I21/I23 contract slices first; implement codecs with the first
page consumer. PDF-20 adoption and PDF-28 validators can then converge on actual frozen inputs;
PDF-21 publication acceptance requires both. PDF-24 migrates the affected consumers alongside the
new representation. PDF-25 performs forward deployment/current-product rebuild from compatible retained evidence after working readers
and validators; PDF-10/11 own actual external/provider/evaluator/default adoption. I25 and local
serialization/copy improvements need not wait for unrelated type experiments. Shared model/compiler
surfaces retain one integration owner; packages are not automatic agent or worktree assignments.

Targeted checks accompany coherent functional changes. PDF-11 defines the revised required union
before final qualification, preserving independent original-PDF expectations and failed/interrupted
receipts. Include shuffled page selection without unrelated-book decode, one formula diagnostic,
a large intact section with field-contained tables/cells, shared pages and outside references,
full export, same-typed semantic field changes, exact native variants/presence, projection corruption,
semantic-invalid payloads and interruption before/after append/freeze/seal. Final functional and
applicable hygiene checks follow complete scope; numerical benefits need complete-operation
measurements. Existing formatting does not invalidate otherwise applicable types/tests.

## Delivered realization — 2026-11-01

- `model/semantic/pdf-payloads.yaml` declares the selected family, logical owner, codec, retrieval,
  identity, validation and projection placement. `pdf_payloads.py::prepare_payload_family` derives
  nested structs/lists from the released `PdfInlineCandidatePage` schema. Supplied-field bitmaps
  and tagged signed64/binary64 values preserve absence, explicit values, NUL, numeric kinds and
  signed zero; unsupported schemas/values refuse. Prepared validators/schemas are cached by exact
  contract. Decimal-valued schema bounds survive frozen capture without conversion to strings/floats.
- Page IPC uses existing artifact parts and fresh shared COPY encoders for outer records. The
  envelope supplies page/schema/codec/logical locators; frozen validation recomputes logical identity
  from actual bytes. Compression/framing affect byte custody, not typed logical identity. Reports,
  native Docling records, tables/charts and diagnostics remain exact existing representations;
  broad native nested replacement is deliberately deferred until a complete mapping and useful
  consumer exist. No dictionary or cross-language profile is presently required.
- `PublishedPdfReader.native_metadata(page_nos=...)` filters before payload retrieval;
  `iter_payload_batches` returns owning Arrow arrays. `candidate_inventory` uses list/struct kernels
  for candidate/region/word counts. Logical exports decode the selected physical profile, preserving
  existing exact source/evidence and logical serialization distinctions. Both paginated and set-shaped
  section context use the same relational selector. SQL NUMERIC projections stay exact Decimal/Core
  boundaries and are explicitly excluded from upload profiles rather than assigned invented precision.
- `pdf_payload_validation.FrozenPayloadStore` retains captured parts and companions in a temporary
  disk-backed store owned by the existing finite child. It validates every declared metadata family,
  page-local OCR/candidate semantics, source/health/report rules and complete-set coverage against
  actual frozen bytes and captured release schemas. Page lookup hydrates a requested page; native
  Docling graph validation and its global access/region projection remain explicit materialization.
- Native0067 uses the existing Plugin/NativeTransitionOp authoring/admission route, preserves prior
  managed objects and frozen migrations, and registers the matching current physical contract.
  The result binds the complete admitted dependency contract, frozen input identity and finalized
  access/region membership. Build-row serialization closes projection/finalization races while
  retaining independent task heartbeats. Finalized projections accept exact replay only.

I21 is resolved for the first application page family. I22 closes only with the integrated stored
payload/refusal/result controls below. I23 selects this concrete columnar consumer and shared context
selector; support derivatives and detached dataset scanning remain conditional on actual consumers.
I24 has a functional complete-operation route but no measured performance claim. I25 effective native
options/image-retention redesign remains PDF-22/23 scope. RC12 fresh construction is exercised by
forward database tests; shared-book rebuild/publication and external grading remain PDF-25/10/11.

## Verification — 2026-11-01

**passed:** the selected283-case functional union across20 files, including actual disposable
PostgreSQL migration/admission, frozen payload validation, publication, replay, cancellation/lifetime,
selective Arrow reads, logical exports and native-source reproduction. Receipt
`build/test-receipts/qualification/pdf-payloads-final-20261101` records282passed/1failed; the sole
remaining failure was a historical DDL assertion looking in the publication successor instead of
its foundation. That assertion alone was corrected and the exact case passed in
`build/test-receipts/qualification/pdf-payloads-final-native-control-20261101`. No production change
followed the final283-case invocation; the282 unaffected passing cases retain applicability.
Each receipt's `invocation.json` records the complete `uv run python scripts/test_receipts.py run
--python-only -- ...` command and actual selection. No overlapping counts are added.

**passed:** `uv run pyrefly check --min-severity warn --summary=none` (zero warnings/errors),
`uv run ruff check .`, `just model check`, `just adr-lint`, `git diff --check` and root
`just turn-end`. Formatting did not invalidate otherwise applicable typing/functional evidence.
**failed, retained:** first283-case attempt `pdf-payloads-20261101` had279passed/4failed: two stale
historical assertions and two current-source native provenance mismatches, all subsequently resolved.
**failed:** `just docs-check` on existing moved-library/retired-profile links outside changed documents;
no publication errors were reported for this package's changed plan/architecture/ADR pages.
**not_run:** whole-book inference/rebuild, adopted-result/default changes, external provider journeys,
independent grading, Rust tests and whole-repository qualification. These are not requirements of
this selected payload package and remain under PDF-25/10/11; no measured performance claim follows.
