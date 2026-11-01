# Analytical, operator and selected-source consumers

**Implemented and targeted Tested, 2026-11-01.** [Coordinator](../postgresql-capability-leverage_2026-11-01.md)
owns PG-06/07/10 and PG-I03. These are completed delivery scope. This document records their
interfaces, meanings and realization; the coordinator records their final selected functional/native acceptance.
Existing published/read contracts are prerequisites; unfinished work in another plan is not imported.

## Implemented services and shared application boundary

**Implemented and targeted Tested, 2026-11-01:**
[`serve/companion_export.py`](../../../python/corpus-structure/src/corpus_structure/serve/companion_export.py),
[`serve/database_description.py`](../../../python/corpus-structure/src/corpus_structure/serve/database_description.py)
and [`serve/selected_source.py`](../../../python/corpus-structure/src/corpus_structure/serve/selected_source.py)
provide the shared application operations below. `cli/source.py` and `cli/db.py` parse requests
and render their results. `NativeSourceRequest`/`export_native_source` route
`format="selected-source-v1"` to selected export; complete native formats retain their full-root
meaning. `export_selected_source` owns the protected selected-event cursor;
`pdf_selected_source_native.py` defines its set-based selection/closure SQL, composing the shared
event machinery from `pdf_record_reader_native.py` and the context-row selector.
`PublishedPdfReader` supplies the borrowed-event serializers. No new MCP surface or external
consumer contract is claimed.

| Implemented type / operation | Meaning |
|---|---|
| `PublishedSourcePin` | Frozen `project_id`, `run_id`, `release_id`, `task_id`, `product_key`, `content_digest`; validated against authorized published ancestry in a read snapshot. |
| `CompanionExportRequest` | Pin, nonempty unique families from `input/relation/coverage/mapping_report`, fresh destination; defaults to all four families. |
| `export_companion_parquet(request, settings)` | Owns capture resources; returns detached `CompanionExportManifest` after atomic publication. |
| `inventory_companion_export(path)` | Verifies a manifest path and files, then returns a dictionary with pin, projection, family inventories and `not_requested`; owns no PostgreSQL connection. |
| `compare_companion_exports(left, right)` | Verifies two manifest paths; returns a dictionary containing both inventories, `comparable`, optional `reason`, and side-qualified multiset `differences`. There are no exported `CompanionInventory`/`CompanionComparison` classes. |
| `DatabaseDescriptionRequest` / `describe_database` | Literal schemas/relations, depth, optional parameter-free query with `release_id`, estimates and output bounds; returns `DatabaseDescription`. |
| `SelectedSourceExportRequest` / `export_selected_source` | Pin, `SelectedSourceSelection(root, membership="descendants")`, destination and context policy; returns `SelectedSourceExportReceipt`. |
| `SelectedSourceReader.prepare_formula_inputs(context, ...)` | Verifies the offline package and retained admitted `PreparedInterpretationContext`; returns `PreparedSelectedFormulaInputs` through the existing formula preparation frontend. |

**Closure evidence, 2026-11-01:** PG-06/07/10 and PG-I03 are complete at `c5394eaa`.
The coordinator owns the final affected-scope command/receipt
`build/test-receipts/qualification/pg-series-final-c5394eaa`: **passed**, 319 tests across 32 files,
zero failures/errors/skips, JUnit time 89.560 seconds. Relevant independent cases are
`test_companion_export.py`, `test_companion_export_native.py`, `test_database_description.py`,
`test_selected_source.py` and `test_selected_source_native.py` under
`python/corpus-structure/tests/semantic/`. The remaining imperative text specifies the delivered
contract and its controls, not pending implementation. Database cutover remains PDF RC12;
there is no measured speed/memory/deadline claim.

Request/result types belong with the existing application/model declarations and trusted boundary
adapters, not a manually synchronized schema beside them. Family fields, endpoint roles, presence,
coverage outcomes and source qualification derive from the model. Stable explicit format versions
name different public meanings; a breaking request change migrates the actual callers together.
Existing exception/failure boundaries consume PG-02 outcomes. Domain refusals remain distinct from
I/O, driver, database and cancellation failures. A transport exception cannot become an empty result.

## PG-06 — Companion Parquet and DuckDB inventory

### Authorized capture and detached manifest

The source CLI provides `ci source companion-export`, using the same explicit run,
producing-task, product, digest and output options as `native-export`, plus repeatable `--family`.
The default family set is all four; an explicit subset is recorded and never inferred complete.
`--json` returns the same manifest/receipt structure that the service returns. It also provides
`ci source companion-inventory <manifest>` and `ci source companion-compare <left> <right>` as
rendering clients of the local operations, supporting JSON and human output from the same application result.
Do not change `ci export`'s existing whole-semantic-projection meaning to achieve this feature.

Consume the protected typed family functions selected in
[typed realization](typed-realization-and-transfer.md#pg-06--authorized-typed-companion-projections).
`ops.read_published_input_batch`, `read_published_relation_batch`,
`read_published_coverage_batch` and `read_published_mapping_report_batch` return the
model-derived static columns, qualified endpoint rows and stable occurrence keys. The ordinary principal receives EXECUTE on those protected
projections, not SELECT on private/native record tables. Publication, run/project ancestry and
pin checks are independent native enforcement, including on paths bypassing the Python service.
The generic JSON row reader is not the Arrow schema source, and ADBC metadata does not infer
application meanings from physical column spelling.

In one Core read-only REPEATABLE READ snapshot, validate the pin and projection, then export the
snapshot. A fresh nonpooled ADBC read-only REPEATABLE READ session imports it before any data
query. Use the fixed function-call Select compiled with PostgreSQL's dialect literal renderer
for the COPY-result path; user strings are values, not SQL fragments. Capture all requested
families through that same imported snapshot. Empty supported families still produce schema-bearing
Parquet files with zero rows. Unsupported family names refuse before capture. A supported empty
family and a family not requested have different manifest states.

Stream `fetch_record_batch()` into `ParquetWriter.write_batch`, close reader/cursor/writer and
settle the imported transaction before releasing the exporting snapshot. No inference or DuckDB
analysis holds these sessions. Preserve exact schemas and declared field metadata, lexical values,
SQL-null/JSON-null distinctions and qualified references through the directional transport profile.
Parquet ordering follows modeled keys, not incidental ADBC batch boundaries. No global Python
`to_pylist`/sort or whole-document reconstruction is required.

The detached `CompanionExportManifest` fields are `format="pdf-companion-export-v1"`, `pin`,
`projection_id`, `profile_id`, `created_at`, `families` and `not_requested`. Each `FamilyFile`
contains `path`, `schema_base64`, `rows`, `logical_digest`, `sha256` and `byte_length`.
Serialized Arrow schema metadata binds projection, pin, profile, release, physical model, family
and product.
Unrequested families are named in `not_requested`, not represented by empty files. Capture uses
atomic temporary-directory publication. The admitted product digest is distinct from export-byte
identity; a snapshot identifier is not a durable detached import capability.

A result returned after rename owns no live reader, transaction, connection or temporary spool.
The destination is durable caller-owned output; `close()` must not delete it. Internal scratch
and a not-yet-published manifest remain service-owned and are removed on failure/cancellation.
Reject existing destinations; never overwrite unrelated artifacts. Failed partial files do not
publish a successful manifest. Readers reject absolute/traversing paths and unexpected schema or
hash bindings before use; no current/latest file discovery is permitted.

### Inventory and comparison semantics

The inventory dictionary carries the manifest pin/projection, requested family results and these
operation-shaped tables, each labeled as an inventory of that projection:

- Inputs: counts by modeled role and source product binding, retaining source task/product/digest,
  input ordinal and repeated uses. Equal source bytes do not imply one input use.
- Relations: relation occurrence counts by kind; endpoint counts by modeled role and qualified
  target binding/address; `target_scope` distinguishes `own_product` from `external_product` for this whole-product export; v1 published endpoints remain fully resolved under the existing occurrence-addressed model. Count relation IDs
  from the relation identity surface, not the number of joined endpoints. Preserve endpoint
  ordinal and repeated endpoints rather than collapsing them with DISTINCT.
- Coverage: outcome distributions keyed by the actual modeled `scope`, `coverage_family` and `discovery_policy`. Complete, partial, failed, unknown and not-requested remain distinct; missing rows
  do not establish zero failures or successful complete recognition.
- Mapping reports: outcome counts keyed by input index and task/product/digest, coordinate frame,
  coordinate scale and normalization; outcome distinctions are not coerced to a success flag.

DuckDB uses explicit schemas and manifest-listed `read_parquet` relations, scoped views/CTEs and
GROUP BY/joins at these keys. It does not read a wildcard directory or auto-union incompatible
schemas. Retain all inputs required by a statistic; output filtering cannot remove endpoints
needed to decide whether a relation is dangling or outside the selected universe.

Comparability is decided before reporting semantic deltas. Require the same semantic projection,
family set and field meanings, compatible schema/profile/digest recipes and comparable source
selection/context policies. Two different product pins are allowed and are precisely what a
revision comparison describes. A different project, native/model schema, interpretation release
or selection policy requires an already explicit equivalence/translation contract; v1 supplies
none and returns `comparable=false` with a reason and both inventories.
Different physical batch/file boundaries alone do not make exports incomparable.

The implemented comparator additionally requires identical input bindings (including ordinals
and multiplicity) for different pins, and therefore requires the input family for cross-pin
comparison. It returns `comparable=false` and a reason when that premise is unavailable or differs.
The result always retains both inventories.

For the same pin, each family's `removed`/`added` records use `EXCEPT ALL` over exact projected
value columns, preserving duplicate multiplicity. For different comparable pins there is no
cross-product occurrence correspondence: every left record is side-qualified `removed`, and every
right record is side-qualified `added`, even if local IDs or row values happen to match. Each
family result carries `left_pin`, `right_pin`, `columns` and `correspondence` (`same_product` or
`none`). No changed-value pairing is fabricated across pins, and equal counts never establish
semantic equivalence. A missing family remains `not_requested` or causes incomparable scope,
never a zero delta. Lexical values remain authoritative.

### Retained acceptance controls

Exercise the public service and CLI with actual authorized PostgreSQL → ADBC batches → Parquet →
DuckDB. Independently specified fixtures include two same-kind relations with repeated endpoints,
one external endpoint, one empty legitimate family, partial/unknown coverage and two products
sharing local pointer spelling with different meaning. Expected identities/counts are authored
independently of the projection builder. Verify both comparable same-contract revisions and
incomparable release/profile/family selections, equal counts with unequal contents, batch reordering
and different Parquet grouping. Swap a same-typed column, file/hash or pin and expect refusal.

Test hidden staging, cross-project ancestry, unsupported family, sink failure, canceled/abandoned
reader, changed selection during capture and a destination collision. After capture, close the
DB resources and run local analysis successfully; conversely, a closed incomplete reader must not
produce a manifest. A mock driver or a writer/reader round trip alone is not the actual journey.

## PG-07 — `ci db describe`

### Shared request and honest result

The existing Typer `db` group exposes `describe` with the shared JSON/human result. Settings select the
current database target; a request supplies one or more **literal schema names**, optional literal relation names,
`depth=schemas|relations|columns|constraints`, positive object/column/output bounds and
`estimates=false|true`. Relation filters require their schema; no cross-database traversal is
implied. Query description optionally supplies one SELECT plus
`release_id` through the existing model/native admission route; there is no separate query-reference field. V1 query description is parameter-free: reject submitted parameters/placeholders before admission. The current `admit_sql` has no bound-parameter input and its supported AST excludes `ParamRef`; extending that authority is not required for useful metadata description.
The query and release ID must be supplied together; an absent query does not mean an arbitrary catalog query.

`DatabaseDescription` records actual database/schema/relation context, request selectors/depth,
observation time, principal scope and observations tagged `physical`, `query_output` or `estimate`. Query observations include the
admitted release/physical binding; there is no separate model-observation family. Each observation has `available`, `not_requested`, `unsupported`, `no_visible_match`
or `refused` meaning where appropriate; absent estimates and unsupported physical details can be
`unavailable`. Bounds reached produce an explicitly incomplete/refused
bounded description, never a complete empty catalog. A top-level transport error remains a
failure, not a metadata-status record that could be mistaken for success.

Selectors are literal names, including percent/underscore/backslash characters; there is no v1
pattern language. Resolve/authorize their actual catalog scope through bound Core/native catalog
equality predicates. ADBC search-pattern filters are only a discovery optimization: use a
library-specific literal-pattern adapter and exact-name equality on returned records. If a driver
cannot express that optimization faithfully, use the already resolved exact-object Core/native
metadata path rather than widening user selectors. Never treat a public name as a SQL identifier
fragment, or return unselected metadata just because the driver's filter matched more objects.

### Metadata APIs have distinct contracts

| Selected API | Use and reported limitation |
|---|---|
| `adbc_get_objects(depth=..., db_schema_filter=..., table_name_filter=...)` | Hierarchy, object kind, columns and supported constraints for the requested scope; nested null children at a shallower depth mean not requested, not no children. Consume and close its batch reader. |
| `adbc_get_table_schema` | Arrow field shape for one resolved named relation. Missing typmod/nullability/domain identity is unavailable, never reconstructed from Arrow's default nullable flag. |
| `adbc_execute_schema(query, parameters)` | Prospective output shape, including aliases/expression results, after admission; this is not a table definition, row count or complete column-domain contract. V1 passes no parameters; method support for binding does not extend current query admission. |
| `adbc_get_statistics(approximate=True)` | Optional standard estimates from the connected DB and explicit schema, including approximation flags. Unsupported or absent values remain unavailable; no implicit COUNT(*) or ANALYZE. |
| Core/native catalog inspection | Exact resolved names, privileges and selected facts the ADBC projection omits, including declared model links. Required native body/owner/search_path/grant admission remains separate and is never weakened to metadata presence. |

The implemented discovery maps `schemas` → ADBC `db_schemas` and all deeper depths → `tables`. It decodes the nested discovery records, then uses Core catalog inspection for requested columns and constraints; `adbc_get_table_schema` supplies a separately labeled Arrow shape where SELECT is permitted. `columns` leaves constraints `not_requested`; unsupported exclusions are `unavailable`. This avoids treating incomplete ADBC nested column/constraint metadata as authoritative native facts. Output bounds are enforced and metadata readers close on refusal.

Do not request exact statistics and silently fall back: v1 explicitly requests approximate
statistics when selected. Report source/freshness only when actually supplied; unknown freshness
is not current. Driver `get_info` identifies an observation, not a package inventory. Do not fill
an unavailable driver-version string from an unrelated server/library version.

`no_visible_match` means no match in the observed authorized scope; it does not distinguish
nonexistence from metadata invisibility without further authorized evidence. A denied lookup is
`refused` when the server exposes it as such; don't probe with a stronger principal to invent a
more conclusive answer. An unsupported statistics API does not mean an empty table. A visible
relation with no SELECT grant can still be described as a physical object without granting data
access; the result reports privileges only if actually observed.

### Query-schema admission and lifetime

Reuse `semantic/authored_sql.py::admit_sql` and its syntax/catalog/role checks on the fresh
restricted reader execution login it requires. Its current supported subset requires exactly one
SELECT, qualified known relations and approved functions/types/operators; it rejects SELECT INTO,
row locks, modifying CTEs and unapproved function calls. Preserve that subset for v1 rather than
make this command an arbitrary PostgreSQL expression evaluator. Existing source-qualified error
positions and refusal codes reach both CLI representations. `adbc_execute_schema` does not replace
admission: planning can resolve names/functions even when it returns no rows.

Every submitted query is admitted against its explicit release and current physical model, then
described in a short read-only session under the existing reader principal. Use the admitted parameter-free SELECT exactly; do not substitute user values or prepare it on an admin session. Do not run the query, EXPLAIN ANALYZE, DDL,
DML, volatile application functions or migration operations to discover its schema. Close metadata
readers/cursor, settle read transactions and close ADBC on all exits. No reusable result contains
a live catalog/snapshot handle. Observations are dated descriptions, not an authorization cache
for a later write/import; that operation performs its own current checks.

**Acceptance:** literal names containing SQL/pattern punctuation; qualified duplicate relation
names in different schemas; depth omission versus empty child collection; exact type/alias query
output; missing typmod; unsupported/absent/stale estimates; insufficient privilege versus
no-visible-match; object/output bound; cross-database refusal; expired admission binding; rejected
multi-statement, placeholders/parameters, data-modifying CTE, row lock and unapproved function before effects. Independently
specify expected columns and field statuses. JSON and human output must expose identical meanings.
No runtime SQL data execution is credited by successful schema description.

## PG-10 / PG-I03 — Selected-source export for an intact section

### Settled selection and context design

**PG-I03 outcome: Implemented and targeted Tested, 2026-11-01.** The native selected-source journey and independent reassessment cover the closure below, including nested/ancestor scopes and lossless recognition metadata. The
first consumer is incremental native-formula scientific input preparation, preserving adjacent
text/table context for extraction. It prepares inputs through the existing formula/source-frame
contracts; it does not run new recognition or scientific inference.

Select one section/chapter root already resolved through the pinned source view, with
`membership=descendants` including the root and every contained descendant in native order.
The selector is the original native pointer under that product pin, not heading text or a
reindexed record number. A missing/ambiguous root, wrong pin, unselected product ancestry or
non-section root refuses. A root whose section is legitimately empty exports its root/context,
not an absent package. Actual current section membership is determined by the existing source
selection/containment owner; never substitute a byte-prefix test over JSON pointers.

The selected membership is the owned containment subtree, not arbitrary graph reachability.
Resolve section items set-wise, retain their original record/collection membership, and include
nested native structures and scalar/extension parts needed to represent their values. Physical
native-record containment and document semantic parent/child references are distinct: changing
only `read_pdf_native_events`' physical root seed is insufficient when section descendants live
in document arrays and are linked by native references. The protected selected-source
operation derives that semantic membership and feeds the ordered event machinery for its
records. Do not fetch one item/query per node or hydrate the subtree as a Python document.

The mandatory `section-source-context-v1` closure includes:

1. Root ancestry descriptors, original order/qualified addresses, relevant page dimensions/coordinate
   frames and item/cell/occurrence identity. Ancestors supply headings/context only, not sibling
   content or permission to reinterpret the selected root as a complete document.
2. Selected occurrence rows and relations incident to them, with **all endpoints of each retained
   relation** and their roles/direction/ordinal. Preserve repeated occurrences and endpoints.
3. Coverage applying to the selected root, nested selected sections, ancestor sections, pages and
   whole-document premise, with original scope labels. Whole-document coverage is context, not narrowed into a new section completeness claim.
4. Direct input/source evidence bindings used by retained occurrences, relation endpoints or
   coverage supports; their mapping reports, selection decisions and pertinent health/recognition
   outcomes. Keep alternative observations distinct from selected content.
5. Referenced outside targets as qualified external-reference records, including originating field
   or relation endpoint and target product/address/state. Include their directly required identity,
   frame or evidence descriptors; do not recursively import outside subtrees or scientific values.

This is the first consumer's input contract: a formula can be prepared from its own recognized
LaTeX, successful attributable recognition, pin/address and admitted interpretation recipe.
An outside formula need not be fetched merely because it is referenced. If a demanded scientific
operation needs outside text/value content, the reader returns `additional_context_required`
with qualified references; the caller explicitly requests that context under another selection
rather than silently analyzing an incomplete input. No current source predicate can turn such a
refusal into successful complete science. Closed context is relative to this preparation contract,
not a claim that every possible downstream analysis needs no other source.

Explicitly list omitted families/content, including outside subtree bodies, original binary
artifact bodies, unselected observations and a complete-root Docling envelope. Required exact raw
artifacts remain digest-qualified references resolvable through existing custody; an offline
consumer requesting bytes that were not included gets an explicit unavailable/input requirement.
Do not fabricate page boxes, glyph positions or original TeX from recognition. Coarse or absent
geometry retains its original fidelity/state and coordinate-frame binding. Tables retain full
selected table/cell membership and source addresses; repeated equal formula strings keep distinct
occurrence IDs/pointers even if a later pure computation can reuse prepared work.

### Service, native extension and event package

The existing `ci source native-export`/shared service accepts `format="selected-source-v1"` with
one required section and descendant membership; its output path names a new package directory. Complete `docling-json`/`integrated-json` retain
their full-root meanings and continue to reject partial selectors. The service validates its
`SelectedSourceExportRequest`, obtains one authorized published reader/snapshot and invokes a
protected `ops.read_pdf_selected_source_events` operation. Model-derived request/return
contracts govern root, membership, closure policy and ordered events; native functions recheck
publication/run/project ancestry and derive closure from published relations. No raw table grants.

Selected export implements its set-shaped membership/context query in
`pdf_selected_source_native.py`, reusing native event and companion scalar-part machinery from
`pdf_record_reader_native.py` plus the shared context-row selector. It does not depend on JSON-valued page hydration or a second selection serializer.
The implemented `pdf_storage.py::integrated_source_context` forwards `membership=membership` to
`PublishedPdfReader.source_context`. Selected-source callers consume the owned closure. Native
metadata is streamed losslessly through companion payloads, including nested/collection formula
recognition metadata; the offline reader rejects ambiguous attribution rather than inventing success.

JSONL is a versioned event package, not a fragment masquerading as a DoclingDocument. Each line
is a bounded event; large strings/opaque native JSON use ordered scalar-part events with profile,
part order and byte encoding, not an unbounded line or Python floating conversion. Record fields,
original pointers and collection order are retained without reindexing. The concrete event schema is declared in `model/semantic/selected-source.yaml` and emitted by
`serve/selected_source.py::_write_selected_package`. It uses `header`, `record_start`,
`record_end`, `companion_start`, `companion_end`, `context`, `outside_reference`, `scalar_part`
and `trailer`. Structured descriptor payloads are canonical JSON text in `data`; payload parts
use ordered base64 with `part`, `encoding`, `value` and `final`. Header/receipt bind schema/projection,
physical model, interpretation model and implementation digests, exact selected membership count
and digest, included families, omissions and artifact references.

The event schema defines allowed kinds and required nesting/order. Every `record_start` closes,
scalar parts are contiguous and complete, and all reference records retain qualification.
Trailer counts cover actual event categories and never infer complete scientific coverage.
Compute the full serialization SHA-256/byte length in `SelectedSourceExportReceipt` after writing;
keep it outside the stream to avoid a self-referential trailer digest. The admitted source product
identity remains unchanged. Missing trailer, unterminated record/scalar or unknown required event
kind is an incomplete/unsupported export, not partial scientific success.

Write into a fresh owned temporary destination, close event Result/scalar readers and settle the
read snapshot before publishing the completed file/receipt with no-replace atomic directory
rename. A sink failure publishes neither a complete trailer nor a successful destination receipt.
The receipt binds pin, selector, closure/projection/schema, event counts and actual serialization.
An optional direct streaming sink cannot retract bytes; its consumer therefore accepts completion
only after validating the trailer and out-of-band receipt. The CLI's durable package is the
required v1 path, with cleanup restricted to its own unpublished temporary directory.

### Implemented scientific consumer and retained acceptance controls

`SelectedSourceReader` checks the JSONL header/receipt/event schema,
maintains bounded current-record/scalar assembly and resolves selected/context references through
an owned on-disk index when necessary. It yields source occurrences and context to the existing
source-frame/packet input-preparation functions; it never reconstructs a complete Docling root.
The prepared interpretation recipe comes from the pinned admitted release, not from package code,
network discovery or a mutable current default. The input-preparation caller supplies an already admitted, retained `PreparedInterpretationContext` whose recipe/model binding matches the package pin; a release ID alone cannot construct that context. Recipe artifacts remain digest-qualified retained inputs resolved before offline preparation. Missing context/artifacts produce an explicit input requirement, never implicit network fetching or a current-default substitution. Native formula preparation reuses
`methods/math/pdf.py::FormulaOccurrence.prepare`: successful recognition is a prerequisite,
recognized LaTeX remains separate from original text, and page geometry does not become glyph
coordinates or an HTML macro environment. Check dependencies before demanding an outside value.

`SelectedSourceReader.prepare_formula_inputs` is the integrated scientific/extraction
**input-preparation** consumer delivered with PG-10. Preserve existing
small-source reads and complete export callers. A consumer may incrementally process records,
but it publishes an accepted prepared input only after trailer/receipt validation; failures leave
no accepted partial input. Recipe preparation/parsing remains demand-driven, and no model inference,
new goldens or whole-book validation is imported into this package.

Independently author a selected root with ordered descendants, nested table/cells, repeated equal
formulas, one outside reference, source evidence and partial/unknown coverage. Check exact selected
membership, context versus outside bodies, endpoint multiplicity, original addresses and geometry
fidelity. Verify formula input preparation succeeds from the valid package after PostgreSQL closes;
failed/unknown recognition refuses; demand for an omitted external value returns the qualified
context requirement. Alter root/pin/project, ancestry, membership, a scalar-part boundary/Unicode
sequence, endpoint ordinal, omission declaration, receipt or trailer and require the correct refusal.
A record omitted from the selected set cannot be hidden by equal counts. Compare against small
independently expected inputs, not only the same production closure on both sides. Large synthetic
scalars and early sink/reader abandonment exercise bounded handoff without live inference.

## Library-informed composition and qualification boundary

[ADBC metadata and ownership](../../libraries/postgresql/adbc-driver-postgresql.md),
[SQLAlchemy relational/streaming](../../libraries/postgresql/sqlalchemy.md),
[Psycopg cursor/lifecycle](../../libraries/postgresql/psycopg.md) and
[pool ownership](../../libraries/postgresql/psycopg-pool.md) supply physical mechanisms. Context7
was consulted for ADBC metadata before installed `adbc_driver_manager/dbapi.py` source confirmed
`adbc_get_objects` depth names/filter arguments, `adbc_get_statistics(approximate=True)` and
`adbc_execute_schema` preparation semantics. The documentation/source lookup establishes API meaning; the separate final affected-scope receipt establishes the selected executed provider journeys. The source owner/model supplies scientific meaning and authorization.

The three outputs remain distinct: typed analytical relations, physical/query descriptions and
selected-source/context events. They share source facts and resource mechanics, not one universal
reader. H5/H6/H8/H16/H17 favor useful scope and bounded movement; DP-07/08/15 preserve order,
multiplicity, exactness and evidence. No numerical benefit is claimed.

PG-I03's design and selected empirical controls are closed in the coordinator. The native journey
covers actual selection/closure, ordered membership, nested/ancestor coverage, lossless recognition
metadata and offline formula input preparation after database closure. Missing published-read or
retained interpretation inputs still refuse at runtime. No inference, whole-book qualification,
external MCP delivery or quantitative performance/resource benefit is credited by those tests.
