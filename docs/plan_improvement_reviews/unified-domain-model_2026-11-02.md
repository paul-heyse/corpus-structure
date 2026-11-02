# Unified domain model — completion-linked improvement review

**Date:** 2026-11-02. **Baseline:** `fb84eb8f`, product source unchanged from the
`d457bdf0` closeout; initially clean working tree. **Assessment:** Interface-checked by source
inspection and version-matched library research. Recommendations are **Proposed**, not adopted,
implemented or measured by this review. No production changes, service startup, database mutations,
inference or new product tests occurred.

The [coordinator](../plans/unified-domain-model_2026-11-01.md#completion-audit--2026-11-02)
owns completion judgments and UM-CA disposition. This review owns new recommendations; it does
not silently add them to accepted scope. The principal design review's R01–R09/O01–O03 and
ADR-0047 remain the basis. The layered design standard, efficient-architecture heuristics and
test-assessment companion inform the judgments; diagnostic audit premises are unchanged.

## Combined judgment and coverage

The selected architecture is substantially realized. The source contains real model-derived
Core operations, strict generated calls, structured PostgreSQL authoring and frozen evolution,
SQLGlot analysis, directional columnar transport, qualified graph reports and ordinary CLI/MCP
consumers. Replacing these with another universal IR, lifecycle framework or writable ontology
would add burden without an established missing capability.

There is one confirmed incomplete integration obligation: cancellation in companion export does
not span its SQLAlchemy metadata/snapshot phase and ADBC bulk phase. It is UM-CA13, not a new
optional enhancement. Existing native admission, exact values and snapshot guarantees should be
preserved while repairing that ownership seam.

The highest-value additional work is to make provider lifecycle and finite operation settlement
explicit, then compare bounded SDK pipelining with the already-streaming page adapter. These
changes can improve the route to outstanding actual-provider acceptance. Contract-specific report
fingerprints and richer declared impact dependencies can reduce unnecessary preparation and
uncertainty without changing semantic authority.

Bare module names below refer to `python/corpus-structure/src/corpus_structure/semantic/`;
`ingest/`, `serve/` and `cli/` paths are relative to its parent package. `services/` paths
are repository-relative; SDK `vendor/` paths are relative to `services/nemotron-parse/`.
Documentation research covered the selected mechanisms in the supplied
analytical/PostgreSQL/data-model guides and their existing unified-model applicability accounts;
the vLLM and triple-pass guides were examined throughout for the provider assessment. API availability
was checked against exact installed sources where consequential. This is responsibility-oriented
coverage, not a claim that every advertised capability was exercised.

## Accepted library mechanism account

| Family | Actual realization and guarantee | Disposition / limit |
|---|---|---|
| LinkML and Pydantic | LinkML effective definitions feed generated calls and semantic IDs. Pydantic `create_model()`, `model_rebuild()` and discriminated reusable `TypeAdapter` boundaries are connected in `boundary.py:195–274`. `_operation_calls.py:122–128`; generation at `operation_call_generation.py:918–927,1091–1129`. Comparison partition reaches scientific assessment in `domain_operations.py:2546`. | Delivered by source inspection; prior static-positive/negative and native receipts retain their original scope. Annotations alone are not the admission boundary. |
| JSON Schema / normalized products | `conditional_rules.py:220–243` uses LinkML `JsonSchemaGenerator` fragments with `Draft201909Validator.check_schema()` and prepared `iter_errors()` validation. Exact source-bound products remain separate from strict cattrs `Converter` reconstruction (`contracts.py:1099–1125`). | Small supplied-value/reference/serialization visitors retain the accepted fidelity rationale. Generic dumping is not an equivalent replacement merely because it is shorter. |
| RDFLib / pySHACL / valuesets | `ontology.py:726–772` calls pySHACL `validate()` with explicit non-mutating/no-inference/no-import settings and traverses RDFLib SHACL result nodes. Shared located reports (`ontology.py:985–1018`) preserve scope, occurrence identity, failure categories and vocabulary custody. | Implemented, not proof of universal entailment or truth maintenance. Map, Datalog, PyOxigraph/Oxrdflib, OAK and schema automation remain conditional candidates, not omitted required dependencies. |
| SQLAlchemy Core | `projection_recipe.py:404–487` lowers one checked recipe into typed binds, JSON access, casts/case, helper calls, CTE/materialization barriers, joins and stable ordering. Companion projections choose Python text versus native JSONB transport explicitly (`companion_projection.py:98–129`). | Actual consumer realization; maintained raw SQL in protected procedural families has a different scope from ordinary relational authoring. |
| pglast / Alembic / catalogs | `native_sql_body.py:19–74` constructs `CreateFunctionStmt.sql_body` and emits SQL-standard bodies with RawStream. `alembic_native.py:22–219` connects operation invocation, comparator, renderer and exact frozen transitions. `native_catalog.py:96–244` uses typed catalog expressions, ordered aggregates and LATERAL observation. | Selected mechanisms are present beyond imports. Current procedural/AS families are not silently represented as complete procedural generation; frozen products stay immutable. |
| SQLGlot | `projection_analysis.py:267–280` runs MappingSchema, strict qualification, type annotation, reusable scope and lineage; lines297–349 include relational clause dependencies. Materialized boundaries remain explicit; helper-body knowledge stays unknown where unavailable. | Substantive selected capability. Dependency syntax is not authorization, behavioral equivalence or scientific provenance. |
| Arrow / DuckDB | `analytics.py` uses Arrow `pc.call_function()` for column operations, DuckDB `register()`/`unregister()` for owned inputs and `to_arrow_reader()` for guarded batch reads (:1461–1465). Model-derived schemas and directional profiles retain explicit lifetime and exact-value boundaries. | Native compute and relational execution do not imply constant-memory joins/sorts or semantic validity from Arrow metadata alone. |
| Psycopg / pgpq / ADBC | `arrow_transfer.py:87–170` uses fresh pgpq `new_with_encoders()`/`infer_encoder()` products and Psycopg `cursor.copy()` within the caller’s Core transaction. ADBC `fetch_record_batch()` reads a separately imported snapshot using the configured driver. | This composition preserves write atomicity; ADBC ingestion is not an interchangeable same-session publisher. UM-CA13 remains a cancellation integration gap. |

Concrete method tables remain in the companions. Their descriptions must be read alongside the
principal review and accepted amendments; a shorter coordinator summary does not narrow an
obligation. Conversely, illustrative alternatives such as wholesale ORM, general Datalog inference,
Flight or a new RDF storage backend are not adoption quotas.

<a id="I01"></a>
## I01 — Give the provider resource an explicit, small lifecycle contract

**Priority:** prerequisite to dependable provider adoption. **Fit:** UM-09/14 and the existing PDF
provider/runtime owner. **Principles:** FP-01/02/05/07; H2–H4, H11–H12.

`ingest/pdf_capacity.py` intentionally owns GPU handoff, not a process. The service README and
readiness launch receipts provide manual external startup. There is no single durable owner of
launch identity, readiness, continued availability and shutdown across entry points/tool sessions.
That gap should not be filled by letting unrelated callers opportunistically start or kill servers.

Extend existing settings, CLI and operation/resource contracts with owned versus externally managed
service mode, immutable model/export/runtime identity, process identity where owned, readiness
states, GPU phase and terminal outcomes. Reuse the existing provider controller. A PID alone is
insufficient custody; retain group/start identity and verify the endpoint's declared model.
Separate process alive, listener present, model API ready, awake and successful inference.

Compare an externally managed service with explicit prerequisites against a small supervised owned
resource. Do not introduce a distributed serving platform for this personal single-host workflow.
A lifecycle owner must not convert health checks into inference acceptance or weaken exact model
identity. Closure needs missing/wrong model, startup failure, loss between readiness and use,
cancellation and owned shutdown controls through the ordinary entry point.

<a id="I02"></a>
## I02 — Compare bounded public SDK pipelining with current page streaming

**Priority:** investigate after lifecycle ownership is settled. **Fit:** PDF recognition adapter and
UM-09/10 ownership/transport. **Principles:** FP-01/04/07; H4–H8.

Current `ingest/pdf_recognition.py:337` already yields completed pages from a bounded four-page
window with consumer-driven refill. It is not a whole-book result barrier. However, each page
starts another Python process (`:517`), and its one-page invocation opens the PDF again
(`:456–460`). `services/nemotron-parse/worker.py:142–149` invokes serial triple parsing.

Installed `nemotron-parse==3.5.0.post7` provides `DocumentParser.prepare()` and
`parse_prepared(mode="triple", schedule="pipelined", concurrency=..., postprocess_workers=...,
triple_regions="union", allow_partial=False)` (`vendor/nemotron_parse/inference.py:471–504`).
Its dependent crop scheduler can overlap ready A/B/C work. Compare a bounded prepared-page window
with a persistent isolated worker pool that amortizes imports/parser/PDF setup. Retaining the
current adapter is a valid alternative if a batch barrier or observation limitations outweighs reuse.

Important constraints: this public API returns a completed batch, not an incremental page iterator.
Prepared pages retain decoded images; whole-book preparation would undermine streaming. The custom
backend branch of `parse_many()` threads serial parses and is not the same scheduler. Do not inherit
SDK concurrency 128 when the local server recipe limits sequences to 4.

Current geometry/union observers temporarily patch module-level behavior (`worker.py:109–139`).
They are unsafe to share across concurrent crops without a supported, attributed observation seam.
Request indexing and artifact names must also preserve per-page/pass/crop identity. Preserve raw
requests/responses, union regions, alternatives, transforms, replay and cancellation before changing
execution placement. Arrow should carry completed structured observations; token fragments must
not masquerade as complete document rows.

Closure: compare a small discriminating physical-page sample with table/chart/crop dependencies,
including raw special tokens, finish reasons, coordinate mapping, alternatives and integrated
lineage. Establish the bounded working set and partial-consumption behavior qualitatively; no
speedup is claimed without measurement.

<a id="I03"></a>
## I03 — Bound page-operation lifetime and qualify cancellation settlement

**Priority:** before expanding provider acceptance. **Fit:** PDF worker/resource contract.
**Principles:** FP-02/05/07; H2/H4.

`pdf_recognition.py:523–533` polls a live worker without an elapsed page deadline. The worker's
httpx timeout bounds individual HTTP operations, not the entire triple pass or local processing.
A renewed lease can therefore coexist with an indefinitely stalled page.

Define a finite page-operation deadline through the existing resource owner, distinct from request
I/O timeouts and release-owned decoding policy. Preserve unfinished stage, partial receipts and
attempt identity; settle process groups and HTTP/request resources before reporting completion.
Do not silently retry into a complete outcome or discard capped/failed crop evidence.

Installed vLLM 0.26's chat route uses `with_cancellation` for HTTP disconnects. Worker termination
therefore has a source-backed server-cancellation route, but actual GPU/request settlement remains
unqualified. A bounded stalled/cancelled request and restoration control should decide whether
that route suffices; do not invent an abort subsystem before testing the existing one.

<a id="I04"></a>
## I04 — Derive report-contract fingerprints from their effective dependency closure

**Priority:** complementary generation/change-locality improvement. **Fit:** UM-03/07/13.
**Principles:** FP-01/03/07; H5/H9.

`operation_reporting.py:99–111` prepares the entire trusted execution schema for three report
contracts; `:39–55` hashes all source modules into the report-schema source identity. OCR-only schema
changes consequently regenerate the report artifact even when report fields are unchanged. That
artifact is itself an admitted execution input. The native92/93 history makes this coupling visible.

Investigate a generated transitive effective-contract closure for report registration/validation,
including referenced types, rules, validator semantics and compiler/library versions. Share it
between prepared adapters and emitted JSON Schema; do not maintain a second handwritten schema.
Keep full release/model IDs and complete execution-source custody wherever operation meaning
depends on them. A structural report fingerprint cannot replace semantic operation identity.

Compare retaining the broad closure against this narrower generated product. Closure evidence must
show relevant report changes invalidate correctly, unrelated OCR changes do not, and cold/warm
runtime adapters and registered schemas still agree. Do not obtain fewer revisions by suppressing
real source changes or editing frozen migrations.

<a id="I05"></a>
## I05 — Extend impact knowledge using relationships already present in the model

**Priority:** bounded follow-up, not a false-success correction. **Fit:** UM-12.
**Principles:** FP-01/03/04; H5.

Current impact analysis conservatively reports unknown for class-level dependencies it does not
explicitly record. This is compatible with O02; it must not be relabelled a completion defect.
Derive additional class/effective-field/operation edges from the existing normalized model and
qualified projection products where those relationships are actually known. Reuse LinkML effective
resolution and SQLGlot's bounded dependencies; avoid a second manually maintained consumer registry.

Retain unknown for dynamic Python/helper semantics and unsupported inference. Compare whether the
extra declared closure improves actionable regeneration advice enough to justify its maintenance.
Closure needs class, inherited-field and result-type changes with independently expected affected
consumers and counterexamples where knowledge remains incomplete. No claim of universal semantic
change detection follows.

## Version and alternative boundaries

The local vLLM guide targets 0.32.0; the isolated runtime pins 0.26.0, Python 3.12, Nemotron
3.5.0.post7, Torch 2.11.0 and Transformers 5.14.1. Dependency bounds alone do not prove plugin/GPU
compatibility. Context7 `/vllm-project/vllm/v0.26.0` and installed
`entrypoints/serve/dev/sleep/api_router.py:22–28` confirm `mode=wait`; it is not an unsupported call.
See [versioned sleep documentation](https://github.com/vllm-project/vllm/blob/v0.26.0/docs/features/sleep_mode.md).

Any upgrade must qualify the whole plugin/runtime tuple, special tokens, generation semantics and
actual RTX 5090 backend. Recorded effective FA2 differs from requested FA3; a newer guide's MRV2,
preload/cache daemon or snapshot features do not alone justify adopting them. Docling-native
multipass is documented as upstream main, outside the pinned release, and its guarded merge is
not interchangeable with the selected alternatives policy. NIM's different endpoint/detection
contract and local GPU applicability remain unqualified. None is an automatic replacement.

The first intake failure was an OCR empty-inventory schema issue, subsequently fixed. The second
attempt found no listener before Standard conversion or inference. Its cause remains unknown.
The later deliberately stopped readiness service is a separate attempt. API/sleep-wake readiness
receipts establish neither actual recognition nor a completed integrated document.

## Integration order and evidence limits

Repair UM-CA13 through its existing owner. Settle I01/I03 before fresh operational provider
acceptance; then investigate I02 without sacrificing the current page-level backpressure. I04 and
I05 are separable improvements to existing generators/analysis. Their adoption and detailed plan
amendments require subsequent instruction; this review does not alter accepted architecture.

The 232-target native union, 79 unqualified math nodes and fresh PDF/provider obligations retain
exact original scope. No full-book run, broad qualification, performance benchmark or live probe
was necessary to establish the source-level finding and proposed comparisons here. Broader test
architecture work remains with its own plan; its diagnostic premises were not refreshed.
