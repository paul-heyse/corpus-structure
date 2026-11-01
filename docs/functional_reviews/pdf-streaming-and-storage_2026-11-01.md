# Streaming PDF processing and structural document storage

**Functional-extension review · 2026-11-01 · Proposed.** Inspected production baseline `37757e98`, initially clean. This is a capability and architecture assessment, not a diagnostic audit, implementation or qualification. It consumes the current PDF coordinator and retained publication evidence. No production code, migrations, accepted plans, audit premises, dependencies or runtime services are changed. [Target model](pdf-streaming-and-storage_2026-11-01_target-model.md).

## Recommendation

Adopt a **relationally realized, incrementally built document**, transported in typed Arrow record batches and published by an explicit document seal. Preserve Docling's logical content and native export semantics plus the mandatory integrated evidence companion. Replace the requirement for one native JSONB document and one canonical bytea envelope with lossless, model-governed records and bounded artifact parts. JSON remains useful for bounded native extension values and interchange; it should cease being the mandatory whole-document operational transport.

Default to private incremental preparation followed by atomic visibility of a complete document. Design the same model to express immutable, dependency-closed section snapshots, but enable progressive section consumption only after its closure conditions are established. A page or transport batch is neither a section nor a complete document.

This addresses both the observed JSONB aggregate limit and the next limits in native-content size, artifact size, repeated parsing and whole-document reconstruction. It does **not** establish constant-memory end-to-end Docling processing: pinned upstream assembly remains a material global boundary. Removing that boundary without changing reading-order, heading and enrichment semantics is a named prerequisite, not an assumed benefit.

## Baseline, evidence and limits

The owned PDF deployment is at0060;0061 is committed but undeployed. The current target retains full StandardPdfPipeline with in-page RapidOCR and true Nemotron3.5 A/B/C recognition. Actual recognition covers1589 pages, with1589 A,1589 B,261 C and1433 valid zero-C pages. Primary failures and named recoveries remain distinct. Whole-book integrated publication and downstream assembled adoption remain incomplete.

[Retained prepared sizes](../design_review/evidence/2026-10-31_pdf-integrated-adoption/integration/raw/book-task86-prepared-sizes.json) show558190320 canonical bytes,270447 relations occupying355630981 bytes,213467 occurrences and3441 recognition inputs. The largest relation is25216 bytes. This is an aggregate representation problem, not evidence that individual records are intrinsically too large. Selected native content cast successfully, but that does not establish a safe growth path for a mandatory single content value.

[ADR-0041](../adr/0041-json-text-pdf-publication.md) and0060 decompose JSON text into validated records rather than casting the complete relation array. Attempt7 passed that cast and was cancelled during child validation without committing integrated content.0061 replaces the correlated child check with a shared set join; its focused passes do not establish whole-book runtime or publication success. PostgreSQL also has a separate1GB field limit; TOAST does not remove it ([official limits](https://www.postgresql.org/docs/18/limits.html)). Merely changing JSONB to JSON or bytea cannot be the final scaling design.

The source-stable2643-test0060 baseline and0061 focused controls are inherited evidence at their existing strength. This review ran no product tests, inference or database publication and makes no measured speed, memory, fidelity or throughput claim. Source inspection and primary documentation support the mechanisms below; remaining feasibility obligations are explicit.

Standard: core3.3, efficient-architecture heuristics1.0, code-intelligence1.4 and repository binding. FP-04/A2 require connected authoritative structure and behavior; FP-07/A4, especially H15–24, favor operation-shaped representation, limited live state, valid reuse and short publication exclusion. CI attribution, relationship identity, coverage and pinned serving survive every alternative.

## What currently streams, and what does not

| Boundary | Current behavior / inspected source | Consequence |
|---|---|---|
| PDF acquisition and child handoff | `ingest/pdf.py::convert_bytes`, `pdf_worker.py::ConvertRequest` carry full original bytes; native conversion calls `convert` once. | Sequential page work does not imply sequential PDF byte access. Prefer retained seekable source/file handles and incremental hashing where backend contracts allow. |
| Standard page stages | Installed Docling2.145 `standard_pdf_pipeline.py` has bounded inter-stage queues and page resource release, but retains successful pages in `ProcessingResult`. | Queue limits bound decoded pipeline backlog, not all semantic state or retained enrichment images. |
| Standard assembly/enrichment | `_assemble_document` collects all page elements, calls reading-order and heading-hierarchy models; `BasePipeline._enrich_document` then traverses the constructed document per enrichment model. | Earlier content can be merged/referenced later. Independent page conversion plus concatenation is not presumed equivalent. |
| Nemotron requests | `pdf_recognition.py::_parallel_pages` bounds pending page work; CLI retains each request outcome and raw artifacts incrementally. | Reuse this foundation. Public `prepare` caches images; HTTP `parse_many` prepares all supplied images, and backend mode returns a list. |
| Selection/hierarchy | `pdf_reconciliation.py::select_pdf_integration` indexes by page but retains the mutable selected graph, deferred references, origins and all companion collections. `pdf_hierarchy.py::organize` rebuilds ordered hierarchy. | Page-local matching is separable from global finalization; current implementation does not perform that separation physically. |
| Preparation/publication | `semantic/pdf_integrated.py::prepare_integrated_pdf_product` builds/validates the envelope and serializes whole content. Publisher submits one canonical bytea payload. | Streaming inserts alone would leave the producer and exact-byte binder bottlenecks. |
| Existing Arrow publication | `arrow_publication.py::AppendPublication` freezes complete tables through IPC in memory, calls `read_all`/`to_pylist`, sorts rows and builds canonical JSON; `stage_arrow` then uses pgpq COPY. | Reuse the COPY transaction mechanism, not the whole-table constructor/canonical envelope. |
| Existing reads/analytics | `pdf_storage.py` has bounded item/manifest/artifact reads; `analytics.py` has `CapturedPacket.iter_batches`, explicit `to_table`, spooled capture and ADBC readers. | Extend these routes rather than create parallel consumer engines or force native hydration. |

Docling2.145 installed source is more decisive than moving documentation for the selected pipeline. Its helper for concatenating page documents does not establish that StandardPdfPipeline uses a streaming per-page DoclingDocument API. No claim of such a public output API is made here.

## Alternatives compared

| Alternative | Strength | Limitation / disposition |
|---|---|---|
|0060 JSON decomposition +0061 set guard | Minimal compatible realization; retains existing artifact identity and native guards. | Useful existing baseline. Still requires large content/envelope and repeated representation work; not the streaming target. |
|Normalized document records, bounded artifacts, Arrow transport, final seal | Extends existing relational identity/custody, enables selective hydration, incremental retry and set-based closure. | **Recommended foundation.** Requires deliberate native-schema lowering and new artifact/publication contracts. |
|Same foundation plus IPC/Parquet retained analytical artifacts | Useful detached processing, cross-process transfer, selective scans and restart reuse. | Selective addition, not another editable authority. Retain only artifacts with a real replay/analysis consumer. |
|One JSON document per page/section | Easy local processing and storage. | Reject as canonical design: scopes can cross pages; concatenation can renumber references and alter assembly semantics. Physical page batches remain useful. |
|ADBC-only ingestion, external object store, Flight/Jobkit or another workflow engine | Potential capability for distinct deployments/workloads. | Not selected by default. None removes semantic closure, and additional connection/service ownership needs a concrete benefit. |

<a id="O01"></a>
## O01 — Store one logical document as lossless relational records

**Value:** large documents remain representable and queryable without a mandatory giant JSON container. Operators can replay retained source products; scientific/extraction consumers request the content they need.

Evolve the existing item, occurrence, relation, endpoint, input and coverage families, rather than introduce a second generic graph database. Add modeled document headers, ordered collection membership, qualified native-address mappings and artifact-part custody. Preserve every native field, including body/furniture, groups, pages, list ordering, rich cell content, metadata, origin and references. Split unbounded nested collections such as table cells, child refs and provenance inventories into rows. Keep bounded schema-qualified extension values; oversized extension subtrees and long scalar/raw byte values use ordered artifact parts with explicit lossless reconstruction mappings.

Native references are document/product-qualified, not batch-local. Keep stable logical IDs during building and derive final native array addresses from explicit ordered membership. A native-address change must not silently reassign an existing occurrence or citation. Multiple provenance references, repeated values, parallel relations and unknown/unresolved targets remain distinct.

Factor repeated immutable context by meaning: `select_pdf_integration` currently emits a decision
for each occurrence and serializes its origin evidence, including a full policy in the structural
fallback. Keep each decision/occurrence independent, but reference one release-qualified policy
and, where exactly identical in meaning and custody, one shared comparison-evidence record.
Do not deduplicate merely equal text, endpoints or recognizer votes. This removes repeated context
construction/storage without removing decisions; its actual byte contribution is unmeasured.
Existing canonical bytes remain preserved under their old identity rather than silently rewritten.

LinkML release declarations and the imported pinned native schema own the lowering, record types, relation meanings and invariants. Generate Arrow schema, SQLAlchemy metadata, boundary types and native constraints from those owners. The mapping must be total for the supported native schema; unsupported new fields block admission with a specific diagnostic instead of being dropped. Native reconstruction is a governed projection of immutable records, not independently editable JSON.

This is a change to ADR-0041's physical contract and §B4 realization; adoption needs the existing ADR route. Single-document semantics and Docling interoperability remain.

<a id="O02"></a>
## O02 — Incremental staged publication with a document seal

**Value:** durable progress and retry need not hold a whole-book transaction or expose partial authoritative documents.

Use the existing task/attempt/holder fence as the build owner. Persistent private staging survives connection release; temporary COPY tables only buffer one upload transaction. Admit immutable relation batches under product, release, attempt and schema identity. Validate actual submitted values and their artifact correspondence server-side; a client-supplied digest is not sufficient.

Freeze membership before final validation. Validate missing targets, parent/backpointer agreement, unique ownership, containment acyclicity, ordering, native-field reconstruction, exact input inventories and coverage through indexed set operations over that frozen build. Carry0061's corrected join semantics into the new physical realization without copying its old whole-envelope assumptions. Final seal rechecks the owner/fence, immutable validation input and required closure, then atomically exposes the product. A short commit is possible because staged records cannot change between validation and publication; otherwise validation must be repeated.

Model start/append/freeze/validate/seal/abort/reuse and their effects in the existing semantic operation/lifecycle system. Do not add an independent workflow registry. Retry of identical records is idempotent; conflicting replay is refused; ambiguous seal recovery reads the same product identity. Unsealed staged revisions cannot become selected products; independently committed valid native/recognition products survive later producer failure, and existing failure evidence obligations remain.

<a id="O03"></a>
## O03 — Separate page-local work from compact global finalization

**Value:** process and retain useful page outputs without repeatedly carrying the complete selected book through every stage.

Stream rendering/OCR/layout/table extraction and Nemotron page/crop outcomes into model-qualified page assemblies. Preserve full input-frame and raw-response custody before discarding transient pixels. Reconcile local candidates over each page or an explicitly required adjacent-page window. Spool completed assemblies and correspondence records; retain only necessary global indexes, heading state and unresolved links.

The exact Docling reading-order implementation can merge paragraphs and attach captions/footnotes after page extraction; hierarchy inference and configured enrichments can also revisit results. The first implementation investigation must separate compact topology/global inference from heavy content hydration while retaining those algorithms. Preferred route: a narrow adapter around pinned native stages with disk-backed assemblies and equivalent finalization. If the native API requires a whole graph, report and bound that residual explicitly, and pursue the smallest provider extension needed; do not claim strict bounded end-to-end memory by wrapping it in a generator.

Do not substitute independent `page_range` conversion plus `DoclingDocument.concatenate` without differential evidence for paragraph, caption, footnote, heading, IDs and enrichment behavior. No repeated model inference should be required merely to relocate storage.

Use phase-sequential disk spooling on the single GPU as the default: Standard work can finish and release its model before Nemotron wakes, while both phases write bounded outputs. Compare interleaved page groups only if model residency, phase transitions and useful overlap justify it. Streaming does not require both model families resident concurrently.

The bounded research resolved supplied reference unknown U-4 at NVIDIA revision
`4035ffb1d8f8bafcdb867dfaf6f7514f101464f9`: `reference/parsebench/pipeline/parse_results.py::finalize`
adds crops before `postprocess.py::finalize_one` applies guarded replacement, followed by deduplication
and repair. One crop may participate in both. Preserve that order when adapting public finalization;
it does not replace the repository's separate selection policy.

<a id="O04"></a>
## O04 — Arrow batches across processing, transport and analysis

**Value:** one typed operation-shaped representation can serve stage movement, native kernels, COPY and selective analytical reads, reducing repeated Python dictionaries and JSON encoding.

Use schema-bound `RecordBatchReader` producers, not `Table` as the required interface. Prefer scalar/struct columns plus child relations for large repeated fields; ordinary lists/strings and their large-offset variants are chosen per actual wire support. Preserve missing versus null explicitly where it affects native reconstruction, lexical numeric text, row multiplicity and order. Arrow nullability/schema validation is not relationship closure or publication authority.

Use `pyarrow.compute` and Acero projection/filter/hash-join where their semantics and working sets fit; use DuckDB for SQL/global operations when its spill-capable operators are appropriate. Neither engine's streaming output proves its operators have bounded state. Acero order-by accumulates input; do not select it for required external sorting. DuckDB spill support is operator-specific, not universal.

IPC `new_stream`/`open_stream` supports sequential handoff; IPC files and `memory_map` support seekable detached reuse. Parquet `ParquetWriter.write_batch`/`ParquetFile.iter_batches` and Dataset scanner `to_batches` support compressed durable capture and selective scans. Use file paths/IPC for process boundaries: Arrow C Stream is in-process interoperability, not interprocess transport. Keep reader, mapped file and backing buffers alive for all borrowers; slicing can retain a much larger allocation. Arrow allocator accounting is not total process/GPU/mmap memory.

Replace the publication constructor's freeze/`read_all`/`to_pylist`/global canonicalization together with its identity/replay contract. Changing only its COPY loop would not implement this opportunity.

<a id="O05"></a>
## O05 — Keep transactions and validation systematic

**Value:** fast bulk transfer retains independent PostgreSQL enforcement and a single transaction owner.

Preferred writes reuse `ArrowToPostgresBinaryEncoder` (`write_header`, `write_batch`, `finish`) and Psycopg `cursor.copy(... FORMAT BINARY)` / `Copy.write` on the driver connection already owned by SQLAlchemy Core. Compile exact column order and wire types, including explicit JSONB encoding for bounded extension columns. COPY goes only to protected staging, not directly around native publication. SQLAlchemy owns commit/rollback; do not commit its raw connection independently.

ADBC `fetch_record_batch` is appropriate for snapshot-bound bulk reads, reusing existing spooled analytics. ADBC ingestion remains an alternative for a separately owned staging transaction; it cannot be presumed to borrow the Psycopg/SQLAlchemy connection or its temporary tables. Do not create simultaneous SQLAlchemy and psycopg-pool pools for the same traffic without separate ownership. Long inference never holds a checkout.

Reuse Pydantic `TypeAdapter` per admitted record type and JSON Schema draft-specific validators with prechecked schemas and a pinned `referencing.Registry`. Full records, not partially received JSON tails, cross admission. `experimental_allow_partial` may omit invalid trailing values and `model_construct` bypasses validation: neither is a fidelity-preserving admission shortcut. Local validation supports diagnostics; FKs/set checks/native schema rules establish broader invariants.

Use existing pglast AST authoring/inspection and Alembic forward revision mechanisms for changed protected functions, descriptors, constraints and indexes. Regeneration must preserve the current model-derived helper/CHECK path, including authoring counterfactuals; all frozen revisions, including committed but undeployed0061, remain unchanged. Server errors name product, relation, record/native address, invariant and the existing replay/remap/rebuild action, rather than generic JSON failure.

<a id="O06"></a>
## O06 — Selective consumers and lossless streaming export

**Value:** a small section inspection or evidence trace does not reload or serialize the book.

Extend the existing selected-product reader, SourceViews and paged companion/artifact APIs with record/batch readers under one immutable product pin. CLI/MCP and M09/M11/M13 consume the same contract. Global scientific context remains explicitly broader where required; requested output scope must not silently shrink necessary analysis input.

Native JSON and complete integrated JSON remain supported export projections. Write ordered collections incrementally to a sink and hash exact exported bytes incrementally; do not reassemble giant SQL `jsonb_agg` values or call full `model_dump` as the normal export path. Pydantic remains a useful explicit hydration/conformance boundary for bounded scopes and whole-document callers that request it, not mandatory storage. Preserve both logical reconstruction equality and separately archived original serialized bytes where exact-byte replay is required; these are different guarantees.

<a id="O07"></a>
## O07 — Progressive section snapshots with explicit closure

**Value:** potentially begin supported section analysis before the rest of the book completes, without representing provisional content as final.

Recommend atomic complete-document visibility as the initial path. A closed section may later be published as an immutable scoped snapshot only when its heading boundary, content order, necessary context, selected provider outcomes, reference dependencies and fact-family coverage are closed under a declared policy. End-of-section alone is insufficient. Future-target references are either resolved within included dependencies or typed unresolved under a contract that permits them; they must not become false absence.

A later global algorithm changing heading interpretation, selection or membership creates a new snapshot and invalidates affected dependent results through existing dependency semantics. It cannot mutate a section already cited by a knowledge result. Progressive snapshots are qualified scopes of one document, not invented new original documents or section chunks. If heading/enrichment closure cannot be established before full assembly, defer their authoritative publication while retaining useful private progress.

## Investigations that materially constrain adoption

| ID | Required resolution | Delivery boundary |
|---|---|---|
| I01 | Exact bounded/native assembly integration: reading-order merge, caption/footnote links, heading inference, formula/cell enrichment, resource release; determine residual global graph size. | No strict end-to-end streaming claim until the exact path is demonstrated. |
| I02 | Total native-schema decomposition/reconstruction, including extensions, fields-set/null semantics, tables/grid/rich cells, references, images and arbitrarily large leaves. | No lossy mapping or silent native-field omission. |
| I03 | Native record/artifact correspondence and logical identity independent of batch boundaries; deterministic record ordering without whole-document JSON/Arrow materialization. | No hash-only trust or physical-batch-dependent product identity. |
| I04 | Frozen-set native validation and seal under concurrent append, cancellation, lease change and ambiguous commit. | No publication of stale or incomplete validation results. |
| I05 | Actual Arrow→pgpq/PostgreSQL and ADBC type profiles; buffers, resources and operation-specific spill on exact pinned versions. | Keep unsupported types on explicit lossless lowerings; do not claim zero-copy network COPY. |
| I06 | Which section semantics really close before whole-document finalization. | Progressive consumption remains optional until established. |

These are concrete implementation prerequisites, not an additional review framework or an unrequested benchmark campaign. Resolve with existing pinned sources and the smallest discriminating controls; use retained recognition rather than repeat inference.

## Review verification — 2026-11-01

- **passed:** read-only source/capability inspection and independent model/lifecycle assessment.
  The bounded coherence review corrected containment-only cycle semantics, retained-product survival,
  accepted-ADR immutability and preservation of every frozen revision, including undeployed0061.
- **passed:** existing `scripts/docs.py` discovery/staging and `rewrite_links` target resolution
  for both new rendered review pages (`build/pdf-stream-review-links.log`).
- **failed:** `just docs-check` on the existing retired `ingest/profile.py` parsing-plan link and
  moved OpenTelemetry library link in the logging review (`build/pdf-stream-review-docs.log`).
  Those failures are outside these new documents; no complete site-publication pass is claimed.
- **not_run:** product tests, migrations, GPU inference, database publication and performance probes.
  This documentation-only review does not alter the applicability of existing product receipts.

## Acceptance examples and recommendation order

Demonstrate the retained1589-page witness through record staging, seal, pinned reads and streamed native/integrated exports. Assert independent source/relationship expectations, not merely shared validators. Compare exact reconstructed native values, array order, multiplicity, unknown/null distinctions and companion custody; compare full Docling reload/tree validation where feasible without making that hydration mandatory for production admission.

Include cross-page paragraphs/headings/captions/footnotes, forward references, cycles and missing targets, large cell inventories and extension values, zero-C/failed pages, repeated provenance, parallel relationships, empty sections, reordering/batch resizing, duplicate/conflicting batches, cancellation, lease loss, crash before/after freeze and ambiguous seal. Ensure consumers cannot see staging and wrong-pin reads fail. For progressive sections include a late dependency that must prevent sealing and a revision that must not rewrite an existing citation.

Select O01/O02/O04/O05/O06 as one structural foundation; investigate O03's upstream boundary early, rather than postpone it until storage is built. O07 follows evidence of actual closure. A quantitative performance claim needs representative measurements; this review establishes avoidable copies/barriers statically, not a speedup. No new alignment lints, generic workflow service, external object store or human grading is proposed.

## Research sources and source strength

Repository pointers above are relative to `python/corpus-structure/src/corpus_structure/`, at the inspected baseline. The coordinator and [integrated evidence](../design_review/evidence/2026-10-31_pdf-integrated-adoption/README.md) own current accepted scope and historical runtime receipts.

- Supplied capability references: [PyArrow](../libraries/pyarrow.md) §§2,4–9,14; [Docling](../libraries/docling.md), [OCR](../libraries/docling_ocr.md), [exact triple-pass reference](../libraries/docling_nemotron_triple_pass_reference.md) §§7,9,12,14. These orient research; historical runtime/version claims are checked against the installed source/current custody.
- [SQLAlchemy](../libraries/sqlalchemy.md), [Psycopg](../libraries/psycopg.md), [pool](../libraries/psycopg-pool.md), [pgpq](../libraries/pgpq.md), [ADBC PostgreSQL](../libraries/adbc-driver-postgresql.md), [pglast](../libraries/pglast.md), [Alembic](../libraries/alembic.md): transaction, type, streaming and protected migration composition, not independent new services.
- [Pydantic](../libraries/pydantic.md), [JSON Schema](../libraries/jsonschema.md) §§2,4,8 and [DuckDB](../libraries/duckdb_2.md): boundary validation, pinned schemas and actual execution limits.
- Context7 resolved Pydantic/jsonschema, Docling/Nemotron and Arrow/Psycopg during this engagement; consequential behavior was checked against pinned installed source or primary references. Broad Nemotron search results about older model tokens do not establish true3.5 triple-pass behavior.
- Primary: [Arrow IPC](https://arrow.apache.org/docs/python/ipc.html), [Pydantic partial validation](https://docs.pydantic.dev/latest/concepts/experimental/#partial-validation), [jsonschema validation](https://python-jsonschema.readthedocs.io/en/stable/validate/), [Psycopg COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html), [Docling architecture](https://docling-project.github.io/docling/concepts/architecture/). API/source reading establishes mechanisms, not end-to-end qualified behavior.
- Pinned Docling sources: [StandardPdfPipeline2.145](https://github.com/docling-project/docling/blob/v2.145.0/docling/pipeline/standard_pdf_pipeline.py), installed `_build_document`/`_assemble_document` around895–1178; `readingorder_model.py`1053–1228 (paragraph/provenance merges); `heading_hierarchy_model.py`250–661 (global inference and retained heading lines); `base_pipeline.py`173–223 (post-assembly enrichment). [Docling-core2.105 document operations](https://github.com/docling-project/docling-core/blob/v2.105.0/docling_core/types/doc/document.py) concatenate by copying/remapping; they do not rerun Standard's global inference.
- Additional inspected integration sources: `semantic/capture_storage.py::store_relation` and `analytics.py`825–915 export/import an actual PostgreSQL snapshot before ADBC capture, with Parquet batch writes and explicit spool ownership. Installed PyArrow26 `_acero.pyx` documents that order-by accumulates all input; installed pgpq encoder stubs require explicit supported array/composite profiles. [pgpq nested encoders](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/encoders/nested.rs), [SQLAlchemy DBAPI access](https://docs.sqlalchemy.org/en/20/core/connections.html#working-with-the-dbapi-cursor-directly), [ADBC PostgreSQL types](https://arrow.apache.org/adbc/current/driver/postgresql.html) and [DuckDB larger-than-memory guidance](https://duckdb.org/docs/stable/guides/performance/how_to_tune_workloads.html) supply material composition limits. pgpq's nested-list/composite restrictions favor modeled child rows over arbitrary nested binary COPY; timestamp timezone and decimal lexical preservation require explicit lowering.
