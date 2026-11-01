# Analytical, operator and selected-source consumers

**Proposed target, 2026-11-01.** [Coordinator](../postgresql-capability-leverage_2026-11-01.md)
owns PG-06/07/10 and PG-I03. These are selected delivery scope. This document settles their
interfaces, meanings and realization; source inspection is not implementation or runtime acceptance.
Existing published/read contracts are prerequisites; unfinished work in another plan is not imported.

## Baseline and shared application boundary

**Source-inspected, 2026-11-01:** `serve/native_source.py::NativeSourceRequest` qualifies reads
by run/task/product/digest and separates complete native formats from partial selections.
`export_native_source` and `cli/source.py::native_export` are the source-service/CLI seams.
`semantic/pdf_record_reader.py::PublishedPdfReader` supplies bounded row/context reads and
whole-root native event serialization. `pdf_record_reader_native.py::pdf_native_export_sql`
contains the recursive ordered event query, whose current seed is the document root.
`serve/export.py::export_packet` already writes detached Parquet with schemas, row counts and
hashes through a temporary directory; its SPINE requirement makes it a reusable pattern, not a
function to call with an unrelated companion packet. `semantic/analytics.py::load_packet`
already imports one exported snapshot into a fresh ADBC session before reading multiple families.

Retain those responsibilities and extend them through ordinary application functions. The CLI
only resolves settings, parses requests and renders the same results; no CLI-specific semantics,
interactive catalog browser, generic reader engine or second artifact registry is introduced.
The following names describe the selected interfaces to implement; all are **Proposed**:

| Type / operation | Meaning |
|---|---|
| `PublishedSourcePin` | Immutable `project_id`, `run_id`, `release_id`, `task_id`, `product_key`, `content_digest`; validated against the run's authorized selected-product ancestry in an actual read snapshot. Wrap/reuse `ProductReference` for the product portion. |
| `CompanionExportRequest` | Pin, nonempty unique families from `input/relation/coverage/mapping_report`, and a fresh destination directory. Whole published product only; no implicit current/latest selector. |
| `export_companion_parquet(request, settings)` | Shared service; opens its own read resources and returns a detached `CompanionExportManifest` after atomic publication of all requested files. |
| `inventory_companion_export(manifest)` | Local DuckDB operation over verified manifest-listed files, returning `CompanionInventory`; owns no PostgreSQL connection. |
| `compare_companion_exports(left, right)` | Local DuckDB operation returning `CompanionComparison`, including comparability result, source-qualified differences and preservation of multiplicity. |
| `DatabaseDescriptionRequest` / `describe_database` | Literal object selectors, metadata depth, optional admitted read-query description and optional estimates; returns `DatabaseDescription` with independently labeled observations. |
| `SelectedSourceExportRequest` / `export_selected_source` | Exact pin, one intact section root and fresh destination; writes `selected-source-v1` JSONL under the closure rules below, returning `SelectedSourceExportReceipt`. |

Request/result types belong with the existing application/model declarations and trusted boundary
adapters, not a manually synchronized schema beside them. Family fields, endpoint roles, presence,
coverage outcomes and source qualification derive from the model. Stable explicit format versions
name different public meanings; a breaking request change migrates the actual callers together.
Existing exception/failure boundaries consume PG-02 outcomes. Domain refusals remain distinct from
I/O, driver, database and cancellation failures. A transport exception cannot become an empty result.

## PG-06 — Companion Parquet and DuckDB inventory

### Authorized capture and detached manifest

Extend the source CLI with `ci source companion-export`, using the same explicit run,
producing-task, product, digest and output options as `native-export`, plus repeatable `--family`.
The default family set is all four; an explicit subset is recorded and never inferred complete.
`--json` returns the same manifest/receipt structure that the service returns. Add
`ci source companion-inventory <manifest>` and `ci source companion-compare <left> <right>` as
rendering clients of the local operations, supporting JSON and human output from one typed result.
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

The detached manifest contains the format `pdf-companion-export-v1`, exact pin, selected family
set, semantic projection id, profile id/digest, model/native schema identity and export time.
Each requested family names a safe relative file path, serialized Arrow schema with metadata,
actual row count, logical-row digest under the declared recipe and file SHA-256/byte length.
Unrequested families are labeled `not_requested`; they are not schema-bearing empty files.
Reuse existing logical-row/artifact utilities and atomic temporary-directory publication.
Never reuse the admitted product digest as an export-byte digest. A snapshot export identifier is
capture provenance, not a durable capability that a detached reader can import later.

A result returned after rename owns no live reader, transaction, connection or temporary spool.
The destination is durable caller-owned output; `close()` must not delete it. Internal scratch
and a not-yet-published manifest remain service-owned and are removed on failure/cancellation.
Reject existing destinations; never overwrite unrelated artifacts. Failed partial files do not
publish a successful manifest. Readers reject absolute/traversing paths and unexpected schema or
hash bindings before use; no current/latest file discovery is permitted.

### Inventory and comparison semantics

`CompanionInventory` carries the manifest pin/projection, included-family statuses and these
operation-shaped tables, each labeled as an inventory of that projection:

- Inputs: counts by modeled role and source product binding, retaining source task/product/digest,
  input occurrence identity and repeated uses. Equal source bytes do not imply one input use.
- Relations: relation occurrence counts by kind; endpoint counts by role, direction and qualified
  target binding/address; outside-selection targets are separately labeled; v1 published endpoints remain fully resolved under the existing occurrence-addressed model. Count relation IDs
  from the relation identity surface, not the number of joined endpoints. Preserve endpoint
  ordinal and repeated endpoints rather than collapsing them with DISTINCT.
- Coverage: outcome distributions keyed by the actual modeled scope/universe/provider where
  declared. Complete, partial, failed, unknown and not-requested remain distinct; missing rows
  do not establish zero failures or successful complete recognition.
- Mapping reports: status counts keyed by input/source-target scope and mapping profile, retaining
  unavailable/partial/conflicting observations rather than coercing them to a success flag.

DuckDB uses explicit schemas and manifest-listed `read_parquet` relations, scoped views/CTEs and
GROUP BY/joins at these keys. It does not read a wildcard directory or auto-union incompatible
schemas. Retain all inputs required by a statistic; output filtering cannot remove endpoints
needed to decide whether a relation is dangling or outside the selected universe.

Comparability is decided before reporting semantic deltas. Require the same semantic projection,
family set and field meanings, compatible schema/profile/digest recipes and comparable source
selection/context policies. Two different product pins are allowed and are precisely what a
revision comparison describes. A different project, native/model schema, interpretation release
or selection policy requires an already explicit equivalence/translation contract; v1 supplies
none and returns `incomparable` with reasons and both inventories instead of a misleading diff.
Different physical batch/file boundaries alone do not make exports incomparable.

For comparable exports return added/removed keyed records and changed values, grouped by family,
with each endpoint still qualified by its own side's pin. Match cross-product records only by a
shared declared logical key; never assume equal local IDs or pointers across different products
mean the same occurrence. Where the projection supplies no such cross-product correspondence,
report source-qualified multiset additions/removals and count differences, not invented edits.
Use grouped counts or `EXCEPT ALL` under canonical typed columns to preserve duplicate multiplicity.
A matched relation with changed endpoints is different from repeated identical relation occurrences.
No equivalence conclusion comes solely from equal aggregate counts. A missing family reports
`not_requested` or incomparable scope, never a zero delta. Exact lexical values remain authoritative;
a rounded analytical numeric column cannot determine exact equality.

### Independent acceptance

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

Extend the existing Typer `db` group and JSON/human emission convention. A request names the
current database target, one or more **literal schema names**, optional literal relation names,
`depth=schemas|relations|columns|constraints`, positive object/column/output bounds and
`estimates=false|true`. Relation filters require their schema; no cross-database traversal is
implied. Query description optionally supplies an admitted query reference, or one SELECT plus
explicit release/model binding through the existing admission route. V1 query description is parameter-free: reject submitted parameters/placeholders before admission. The current `admit_sql` has no bound-parameter input and its supported AST excludes `ParamRef`; extending that authority is not required for useful metadata description.
These are closed request alternatives; an absent query does not mean an arbitrary catalog query.

`DatabaseDescription` records actual database/schema/relation context, request selectors/depth,
observation time, principal scope and observations tagged `physical`, `model`, `query_output`
or `estimate`. Each observation has `available`, `not_requested`, `unsupported`, `no_visible_match`
or `refused` meaning where appropriate. Bounds reached produce an explicitly incomplete/refused
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

Map request depth `schemas` → ADBC `db_schemas`, `relations` → `tables`, and `columns`/`constraints` → `all`; for `columns`, omit constraint detail with an explicit not-requested status. Decode actual nested reader fields, not a guessed flat table. If a deeper request cannot be fulfilled by the backend, preserve its unsupported/incomplete fields. Apply output limits incrementally and close the reader when the bounded result refuses further accumulation.

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

A query artifact is rebound/re-admitted when its release/physical/compiler dependencies differ.
Then describe it in a short read-only session under the existing reader principal. Use the admitted parameter-free SELECT exactly; do not substitute user values or prepare it on an admin session. Do not run the query, EXPLAIN ANALYZE, DDL,
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

**PG-I03 design outcome: Proposed, source-grounded closure selected here.** Implementation needs
independent empirical tests of this design, not a later choice of whether to provide it. The
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
in document arrays and are linked by native references. Extend the protected selected-source
operation with that semantic membership first, then use the ordered event machinery for its
records. Do not fetch one item/query per node or hydrate the subtree as a Python document.

The mandatory `section-source-context-v1` closure includes:

1. Root ancestry descriptors, original order/qualified addresses, relevant page dimensions/coordinate
   frames and item/cell/occurrence identity. Ancestors supply headings/context only, not sibling
   content or permission to reinterpret the selected root as a complete document.
2. Selected occurrence rows and relations incident to them, with **all endpoints of each retained
   relation** and their roles/direction/ordinal. Preserve repeated occurrences and endpoints.
3. Coverage applying to the selected scope, pages and whole-document premise, with original scope
   labels. Whole-document coverage is context, not narrowed into a new section completeness claim.
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

Add `format="selected-source-v1"` to the existing `ci source native-export`/shared service with
one required section and descendant membership; its output path names a new package directory. Complete `docling-json`/`integrated-json` retain
their full-root meanings and continue to reject partial selectors. The service validates its
`SelectedSourceExportRequest`, obtains one authorized published reader/snapshot and invokes a
new protected `ops.read_pdf_selected_source_events` operation. Model-derived request/return
contracts govern root, membership, closure policy and ordered events; native functions recheck
publication/run/project ancestry and derive closure from published relations. No raw table grants.

Extend/reuse `pdf_record_reader_native.py` event/containment and context selectors, including
`read_pdf_record_context_rows`, rather than a second serializer with independent selection rules.
If their JSON-valued pages cannot express the required incremental closure, add typed/set-shaped
native subqueries at that owner. Reuse PG-06 typed companion projections where meanings match.
The implemented `pdf_storage.py::integrated_source_context` and
`PublishedPdfReader.source_context` signatures must propagate the actual requested membership:
source inspection currently shows the wrapper calling `source_context(pointers,section_pointer)`
without forwarding its `membership`. New selected-source callers and packet preparation must
consume the one owned closure, not rely on that omitted default or copy its behavior.

JSONL is a versioned event package, not a fragment masquerading as a DoclingDocument. Each line
is a bounded event; large strings/opaque native JSON use ordered scalar-part events with profile,
part order and byte encoding, not an unbounded line or Python floating conversion. Record fields,
original pointers and collection order are retained without reindexing. A schematic stream is:

```jsonl
{"event":"header","format":"selected-source-v1","pin":{"project_id":"statistics","run_id":7,"task_id":70,"product_key":"integrated","content_digest":"1111111111111111111111111111111111111111111111111111111111111111"},"selection":{"root":"#/groups/8","membership":"descendants"},"context_policy":"section-source-context-v1","omissions":["outside_subtree_bodies","original_artifact_bodies","complete_docling_envelope"]}
{"event":"record_start","role":"selected","pointer":"#/texts/42","record_id":"native-record-42","order":[8,2],"label":"formula"}
{"event":"field","name":"orig","value":"x = 1"}
{"event":"scalar_part","name":"text","part":0,"encoding":"utf8","value":"x=1","final":true}
{"event":"record_end","record_id":"native-record-42"}
{"event":"companion","family":"occurrence","local_id":"occ-9","body":{"pointer":"#/texts/42","recognition":"succeeded","geometry":"coarse"}}
{"event":"outside_reference","from_occurrence":"occ-9","relation_id":"rel-4","endpoint_ordinal":1,"target":{"task_id":69,"product_key":"native","content_digest":"2222222222222222222222222222222222222222222222222222222222222222","pointer":"#/texts/3"},"resolution":"qualified_external"}
{"event":"trailer","outcome":"complete","selected_record_count":1,"context_record_count":0,"omissions_declared":true}
```

The example abbreviates fields for readability; actual header also carries the complete pin's
release, schema/projection/selection-policy identities, included families and context rules.
Actual companion rows use model-owned fields, not a second schema inferred from this illustration.
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

### Incremental scientific consumer and independent acceptance

Deliver a `SelectedSourceReader` over verified JSONL that checks the header/receipt/event schema,
maintains bounded current-record/scalar assembly and resolves selected/context references through
an owned on-disk index when necessary. It yields source occurrences and context to the existing
source-frame/packet input-preparation functions; it never reconstructs a complete Docling root.
The prepared interpretation recipe comes from the pinned admitted release, not from package code,
network discovery or a mutable current default. The input-preparation caller supplies an already admitted, retained `PreparedInterpretationContext` whose recipe/model binding matches the package pin; a release ID alone cannot construct that context. Recipe artifacts remain digest-qualified retained inputs resolved before offline preparation. Missing context/artifacts produce an explicit input requirement, never implicit network fetching or a current-default substitution. Native formula preparation reuses
`methods/math/pdf.py::FormulaOccurrence.prepare`: successful recognition is a prerequisite,
recognized LaTeX remains separate from original text, and page geometry does not become glyph
coordinates or an HTML macro environment. Check dependencies before demanding an outside value.

Migrate the selected scientific/extraction **input-preparation** caller with the producer in
PG-10, rather than shipping an unused exporter and promising integration later. Preserve existing
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

## Library-informed composition and remaining uncertainty

[ADBC metadata and ownership](../../libraries/postgresql/adbc-driver-postgresql.md),
[SQLAlchemy relational/streaming](../../libraries/postgresql/sqlalchemy.md),
[Psycopg cursor/lifecycle](../../libraries/postgresql/psycopg.md) and
[pool ownership](../../libraries/postgresql/psycopg-pool.md) supply physical mechanisms. Context7
was consulted for ADBC metadata before installed `adbc_driver_manager/dbapi.py` source confirmed
`adbc_get_objects` depth names/filter arguments, `adbc_get_statistics(approximate=True)` and
`adbc_execute_schema` preparation semantics. These are source-inspected interfaces, not executed
provider journeys. The source owner/model supplies scientific meaning and authorization.

The three outputs remain distinct: typed analytical relations, physical/query descriptions and
selected-source/context events. They share source facts and resource mechanics, not one universal
reader. H5/H6/H8/H16/H17 favor useful scope and bounded movement; DP-07/08/15 preserve order,
multiplicity, exactness and evidence. No numerical benefit is claimed.

PG-I03's design questions are settled by the explicit preparation consumer and closure above.
Remaining empirical questions concern actual native enforcement, completeness, ordering, bounded
resource use and end-to-end consumer behavior under the independent cases, not which context
policy to invent during implementation. If current deployment lacks a selected published read
prerequisite, record that external prerequisite without importing its repair. No probes, product
tests, database changes or library upgrades were performed to author this expansion.
