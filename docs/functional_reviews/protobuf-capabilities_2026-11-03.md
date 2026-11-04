# Protobuf capabilities: relevance to corpus-structure

**Proposed recommendations · reviewed 2026-11-03.** This functional-extension review combines
library applicability and design assessment; it is not adoption authority, a diagnostic audit,
or production qualification. The operator selected broad inquiry, including alternatives to
current authority boundaries. The strongest opportunities are portable release/query discovery,
external typed interfaces when a consumer exists, and descriptor-backed research. Wholesale
replacement of the semantic model, database operations, MCP or Arrow is not justified here.

## Baseline, scope and evidence

Sources: HEAD `7123080e357af031f41421f7afec0a7db84987b1` plus identified concurrent audit-closure
edits; inspected 2026-11-03. The [evidence folder](../design_review/evidence/2026-11-03_protobuf-capabilities/README.md)
retains the source manifest, reproducible probes, original failed attempt and bounded results.
This is a moving-tree assessment, not a frozen product acceptance. The [capability assessment](../library_leverage/libraries/protobuf-ecosystem_2026-11-03.md)
separates reusable mechanisms from contextual applicability.

Inputs are the [Python ecosystem overview](../libraries/python_protobuf_ecosystem.md) and
[installed tools](../libraries/protobuf-grpc-installed-tools.md), with Context7, primary documentation,
installed LinkML source and current code as consequential checks. Overview release statements
are orientation, not implicit upgrades. Criteria: core 3.3, heuristics 1.0, applicable
code-intelligence 1.4 and library-leverage base/additional patterns. Relevant patterns include
mechanical projections, repeated conversion, stable preparation, missing capabilities and
ambient resolver fallbacks; no new pattern or scoring system is needed.

**Operator clarification:** the [audit-closure target](../plans/audit-closure_2026-11-03.md) is
actively being implemented and is the comparison baseline for future behavior. Its coordinator
retains all package/disposition ownership. The structured-logging-observability plan is explicitly
excluded as an implementation premise; observability proposals below stand independently.
No finding is transferred and no existing plan or accepted rule is changed by this review.

### Actual operations and post-audit-closure comparison

Paths below are under `python/corpus-structure/src/corpus_structure/` unless stated otherwise.

| Journey | Existing mechanism | Target obligations that protobuf must consume |
|---|---|---|
| Native source request → task/publication → retained result | `semantic/native_requests.py:request_source_view`; released JSON Schema, canonical parameter digest, generated `_operation_calls.py`, typed SQL/JSONB | AC01/02/05 released memberships, complete rule-value/diagnostic contracts; AC06/08 owned reads and producer binding; protected native effects remain necessary |
| PDF worker → replay → adoption | `ingest/pdf_worker.py:PdfWorker`, Pipe control messages, `semantic/pdf_payloads.py` Arrow IPC and replay acknowledgment | AC07/08 lifetime/producer-generation custody; cancellation, child reaping, immutable replay references and verification remain transport-independent |
| Agent → MCP → semantic submission | `cli/mcp.py`, `intervene/semantic_server.py`, JSON tools and released Pydantic/JSON Schema | Source admissibility, exact evidence handles, producer qualification and terminal settlement; protobuf does not replace the external MCP JSON protocol |
| Named query → coverage/evidence → pages/export | `serve/protocol.py:DomainQuery/QueryResult`, `serve/journey.py`, `semantic/query_compatibility.py` | AC10/11 separate standing, coverage selection before hydration, explicit payload reads, exact bounded directed walks and versioned continuations |

The existing Rust crate has no application protobuf interface. Python protobuf 6.33.6 and
grpcio 1.85.1 are installed/locked transitively through ONNX Runtime and Docling's optional
Triton gRPC family. PDF configuration selects ONNX Runtime OCR; no direct application
protobuf/grpc/Triton invocation was found in inspected source. Installed transport dependencies
do not establish a remote-service requirement.

## Validated boundaries

**Tested, bounded, 2026-11-03:** `probe.py` and `product_probe.py` in the evidence folder.
The first probe's initial attempt failed because YAML interpreted YES/NO as booleans and its
expected enum spelling was wrong; that attempt remains. Explicit ACCEPT/REFUSE fixture names
and a declared xsd prefix resolve the fixture defect. The corrected experiment passes its
assertions while deliberately retaining the candidate refusals below.

| Experiment | Observation | Consequence |
|---|---|---|
| Native LinkML 1.12.1 generation of actual `model/core.yaml` | Generated schema compiles with protoc 36.2 | Native generation is a feasible starting point; compilation is not semantic equivalence |
| Reorder synthetic attributes / enum members | Tags and numeric enum assignments change; `buf breaking` rejects eight changes | Native defaults are unsuitable for a durable public schema without stable allocations/reservations |
| Required integer / omitted value | Empty message serializes; absent and explicit zero encode equally | Requiredness and field-state contracts need explicit presence plus validation |
| Integer `2**40` | Rejected by generated int32 field | Default mapping narrows Python/domain integer range |
| Binary → dynamic message → binary | Known unknown-field fixture survives | Descriptor-backed inspection can preserve unknown bytes through this bounded route |
| Same message through ProtoJSON | Unknown fixture is lost | JSON/Pydantic adaptation must not promise binary forwarding fidelity |
| protoc 36.2 Python generation → locked runtime import | VersionError: generated 7.36.2 versus runtime 6.33.6 | Compiler/plugin/runtime selection must be deliberate; no project upgrade was performed |

Installed generator source also maps Decimal to string, falls back to string for unresolved
ranges, emits ordinary scalar fields without optional presence and does not carry abstract/mixin
semantics into protobuf. Slot `rank` can specify field tags, but does not settle enum stability,
retired-tag reservation, unions or domain invariant lowering. Never overload presentation order
as a public compatibility policy without an explicit contract.

Google's [serialization guidance](https://protobuf.dev/programming-guides/serialization-not-canonical/)
explains why deterministic bytes are not semantic canonicalization. Current
`semantic/identity.py:canonical_bytes/fact_key/occurrence_key` distinguishes exact Decimal and
scoped meaning. Preserve those identities when adding a wire projection; changing them requires
an explicit equivalence specification and migration.

## Opportunities and comparative dispositions

<a id="O01"></a>
### O01 — Release-pinned schema discovery and inspection

**Proposed; strongest developer/research opportunity.** Let an operator or external tool inspect
an exact released interface without importing the application, walking YAML or re-running today's
compiler. Export a bounded descriptor set for selected record/query contracts with an immutable
manifest naming the release, projection ABI, producing toolchain and source products. Inspect
it through `DescriptorPool`, `GetMessageClass` and descriptor-backed documentation. Prepare one
isolated pool per compatible schema collection, rather than registering every release globally.

Compare (a) extending the existing JSON Schema/release inspection surface, (b) adding protobuf
descriptors as another derived artifact and (c) adopting a hosted schema registry. Prefer (a)
for current JSON-only consumers. Pursue (b) when a consumer needs protobuf reflection or generated
bindings; it adds portability and executable structural inspection, but duplicates projection
maintenance. Defer (c): local immutable release custody already exists, and hosting/distribution
must serve an actual sharing workflow. Buf modules/locked plugins and local descriptor images
can provide reproducibility without BSR.

The real core-generation pass supports feasibility, while the counterexamples prohibit exposing
its defaults as the final interface. If selected, use the effective released model as input,
explicit stable tags/enums, presence/union/exact-value mappings and refusal for unsupported
features. Preserve descriptions/IRIs/options only where the contract requires them. Descriptors
remain a structural projection; archived release semantics remain resolvable separately.

**Delivery evidence:** load two archived interfaces in isolated pools, inspect/query a selected
type without production imports, reject missing dependencies, and preserve interface meaning
across adding/reordering/removing fields and vocabulary members. No live application integration
was performed. Revisit when an independent inspector/client is selected.

<a id="O02"></a>
### O02 — Typed external query and operation clients

**Proposed, conditional on a client workflow.** A Python-independent tool could discover a query,
construct typed parameters and consume evidence-backed pages with a generated SDK. This is useful
for eventual Rust tooling, another local application or a hosted consumer, even without replacing
existing CLI/MCP users. No such current caller was identified.

Compare an ordinary HTTP/JSON facade over the existing query contracts, protobuf messages over a
local boundary, grpc.aio and Connect. Select no transport now. JSON is the lowest adaptation
burden for existing interfaces; grpc.aio offers established gRPC ecosystem support; Connect offers
HTTP-friendly multiprotocol clients, with a server-specific HTTP/2/trailer qualification burden.
A Go grpc-gateway adds another deployment lifecycle; choose it only for concrete HTTP/API consumers.
Generated SDK distribution can start locally; BSR is an optional distribution decision.

Project the **post-AC10/11** answer: release/snapshot/cut, producing and installed compatibility,
projection, selection/assessment/establishment, knowledge/coverage, exact typed values, pagination
and refusal outcomes. Do not generate an API around today's incidental rows dictionaries or treat
a streaming RPC as permission to return partial successful walks. `FieldMask` may express output
selection, but must not prune inputs needed for a correct query or authorize arbitrary mutations.
`Any` needs explicit type resolution; it is not a release or authorization boundary.

Prefer Google protobuf first when interoperability with existing generated libraries matters.
Compare protobuf-py if direct typed manipulation materially removes conversion work. Its Pydantic
TypeAdapter integration does not automatically satisfy `DomainQuery`'s BaseModel-class contract.
No serializer substitutes for snapshot selection, operation admission or PostgreSQL enforcement.

**Delivery evidence if selected:** one real independent client traverses query, evidence page,
source payload and export under the same binding; stale tokens, lost presence/precision and
unsupported fields refuse. Then qualify the selected protocol's errors, deadlines, cancellation,
backpressure and shutdown. No live RPC/cross-language application qualification is claimed here.

<a id="O03"></a>
### O03 — Shared schema-defined boundary validation

**Proposed, contingent on O02 or another protobuf producer.** Protovalidate standard constraints
and CEL could give independent clients consistent field/cross-field error paths before invoking
operations. Compare it with existing generated strict Pydantic/JSON Schema and native guards.
For today's internal Python/SQL path, retain existing enforcement: adding CEL would introduce
another expression language and lowering without an independent protobuf boundary to serve.

If selected, compile supported boundary constraints from the same released meanings; keep relational,
source-evidence, applicability, authorization and publication constraints at their existing owners.
Protovalidate compilation/evaluation failures differ from invalid input. Pydantic construction
alone does not establish CEL execution. The protobuf-to-pydantic adapter does not establish
Protovalidate rule preservation. Preserve released AC05 diagnostic identity while adapting library
violation paths, rather than exposing a new independently authored refusal taxonomy.

**Delivery evidence:** equivalent Google/Buf inputs produce independently expected violations;
valid shape/invalid domain data is rejected; unusable rules remain operational failures. Versions,
Python 3.14 wheels and result-message compatibility remain candidate-specific qualification.

<a id="O04"></a>
### O04 — Language-neutral worker control messages

**Proposed, defer pending independently deployed worker.** Typed protobuf control frames could
replace Python-specific pickling when a worker runs a different language/version or host. For the
same-environment serial child, the existing dataclasses/Pipe protocol is simpler. Keep Arrow as
the data plane: protobuf control messages could name replay artifacts, digests and schema profiles
rather than rebuild columnar records or copy large IPC bytes into per-field objects.

Prost/tonic generation makes a Rust worker possible, but installed generators do not provide a
working Rust capability or choose compatible crate dependencies. Any transition retains admission,
producer generation, ACK/custody transfer, renewal/settlement, cancellation/reaping and separate
stderr diagnostics. AC07/08 already own those obligations; protobuf does not repair them.

**Delivery evidence:** same semantic request/result over old and proposed control paths, then
failure before ACK, child death, replacement generation and oversized frames. No performance
or safety benefit is established until an actual worker need and complete lifecycle are tested.

<a id="O05"></a>
### O05 — Descriptor-backed corpus and binary-artifact research

**Proposed, independent research extension.** An operator could inspect embedded schemas and
annotate what a software artifact declares. `protoscan → reproto → prototext/protolens`, complemented
by protoscope, can extract descriptors, reconstruct schemas and explore message candidates.
Prefer supplied descriptors and source schemas; inferred wire types cannot recover field names,
original authorship or complete semantic intent. blackboxprotobuf is a fallback for missing schemas,
not an equivalent source of authoritative declarations.

Start with an offline research adapter producing attributed observations and exact artifact spans/
byte custody; compare with a simple descriptor-set importer before a full binary scanner.
Admitting these artifacts into production requires revisiting current PDF-only scope. Embedded
schema facts, decoded messages and heuristic type guesses need distinct fidelity/coverage labels.
Descriptors lacking SourceCodeInfo cannot establish original `.proto` source spans; retain
descriptor-native addresses and explicitly unavailable textual evidence. Reconstructed text is a
derived view, not original `.proto` bytes. No production ingestion or
extraction-accuracy claim follows from installed tooling.

**Delivery evidence:** known source/descriptor/binary → extracted descriptor → reconstructed
schema with independent original comparison; missing imports, ambiguous candidates and malformed
length/nesting retain explicit outcomes. Defer implementation until the operator selects this
new corpus/research workflow; it can proceed independently of a resident RPC service.

<a id="O06"></a>
### O06 — Independent RPC diagnostics and telemetry interoperability

**Proposed, conditional diagnostic value.** For a selected RPC or existing remote inference
integration, standard health/reflection, grpcurl, grpcui, grpc_health_probe and granc can reduce
bespoke inspection. Snapshot reflected descriptors with endpoint/time attribution. Reflection
availability and service health are separate from model readiness, publication success and
scientific correctness. Connect's current documentation describes reflection support through a
companion and no built-in health service; deployment must be checked rather than inferred.

OTLP protobuf → `otelcol-contrib` can correlate an invocation, worker and external call while
preserving existing authoritative task/receipt truth. This is an independent proposal: the
structured-logging-observability plan is not selected or a prerequisite. Compare ordinary structured
stderr/receipts with OTel instrumentation plus a Collector; prefer the former until a concrete
cross-process diagnostic question warrants the latter. Installing a Collector does not instrument
applications. Exclude source text/secrets by default, bound buffering and exporter timeout, and
retain useful command execution when the destination fails.

**Delivery evidence if selected:** one real correlated operation plus cancellation/exporter outage,
with separately checked task truth and bounded cleanup. No telemetry backend, load/capture campaign
or live service was started for this review.

## Architectural alternatives, interactions and decisions

A genuine alternative to the current model is `.proto` authoring plus typed custom options and
Protovalidate, compiled into normalized release products, native database guards and application
projections. This offers strong language-neutral SDK/tooling support. It still needs ownership for
IRIs, contextual roles/subsets, exact values, identity, graph applicability, source evidence,
lifecycle/effects, policy execution and relational rules. Bare message shape plus CEL does not
replace those responsibilities. Compared with a derived interface, authority replacement would
migrate every producer, compiler, archive reader, query and publication contract. The current
operation-shaped model already serves those consumers. Prefer retaining it; reopen if protobuf
schema authors become a primary user group or independent producers make that burden worthwhile.

| Judgment | Conclusion within this scope |
|---|---|
| A1 Localize change | Derived descriptors/SDKs can compose under existing release owners; a second writable semantic definition would fragment authority |
| A2 Encode meaning | Existing/post-AC meanings exceed message structure; native generator counterexamples show compilation alone cannot establish equivalence |
| A3 Extend through composition | One effective-model-to-interface projection is preferable to manual pb/Pydantic/SQL copies; stable tags and migration rules remain real work |
| A4 Execution fits the workload | Prepare descriptor pools/adapters once per release; retain set-shaped SQL operations and Arrow batches; avoid per-record RPC, duplicate validation and unnecessary whole-artifact copies |

Correctness/fidelity findings remain independent of these architectural judgments. None establishes
whole-system acceptance. No performance measurements or capacity promises are made.

O01 can support O02/O03; O04 requires its own worker demand. O05 can stand alone. O06 follows an
actual diagnostic journey and does not require adopting O01–O05 as a bundle. Stable semantic
identities and original bytes remain independent of all derived encodings.

**Proposed rule impacts, unaccepted:** RC01 would replace LinkML semantic authority (§B5) only if
the unselected authority alternative is later selected. RC02 would expand PDF-only ingest for O05.
RC03 would add an externally reachable service/deployment boundary for a remote O02/O04 choice;
local SDK/descriptor export alone does not require it. RC04 would version directional wire presence, tag allocation, unknown-field and encoded-byte/framing
budgets for a selected alternate encoding; it must not silently replace AC11 canonical-envelope
budgets. No recommendation changes PostgreSQL instance authority (§B4). Any selected change follows existing ADR/owner/plan routes, with future findings
scheduled in their actual owning plan rather than in audit closure by implication.

## Coverage and next decisions

| Family | Relevance disposition |
|---|---|
| Google protobuf, descriptors, protoc, well-known types | Conditional foundation for O01/02/05; directly probed bounded reflection and semantic limits |
| protobuf-py, proto-plus, betterproto/betterproto2, pure-protobuf | Candidate representations for a selected interface; none warrants replacing current generated domain classes by ergonomics alone |
| mypy-protobuf, types-protobuf, built-in pyi; import-layout helpers | Developer support when generating bindings; validate with Pyrefly, do not introduce a second checker |
| Protovalidate/CEL, PGV, protobuf-to-pydantic | O03 conditional; PGV legacy compatibility only; no blanket replacement of validators |
| grpcio/aio, grpclib, Connect and supporting health/reflection/status/testing/admin packages | O02/O06 conditional; package support and selected deployment remain distinct |
| Buf/BSR, protofetch, protoweld, lint/format/doc generators | Useful interface build/distribution components; use one locking/generation route, avoid parallel dependency authorities |
| Prost/tonic/serde/crate generators; Go/gRPC/gateway/OpenAPI; C++ plugin | Independent-language clients/workers conditional; no current application consumer, no inferred runtime compatibility |
| protoscope, prototools/reproto, blackboxprotobuf | O05 and debugging; extraction versus inference fidelity explicit |
| googleapis-common-protos | Reuse compatible error/API contracts if needed; distinct from runtime well-known types |
| confluent-kafka + Schema Registry | Defer: no selected message-bus/event consumer; Confluent framing is not bare protobuf, and its registry is not BSR |
| otelcol-contrib and HTTP/2/packet/system/profile/load tools | O06 or named performance/failure investigation; tool availability alone creates no instrumentation/capture requirement |

**Recommended next decisions:** select a concrete O01/O02 discovery/client workflow or O05 research
workflow before implementation planning. If none is selected, retain the existing transports and
this reusable capability account. No blanket protobuf migration is recommended. Audit closure
continues independently; after its target lands, refresh only affected interface premises before
planning selected opportunities.

**Verification limits:** focused generator/wire probes passed their stated assertions; deliberate
Buf compatibility and generated-runtime failures are preserved. Live RPC, third-party validators,
Rust/Go clients, descriptor extraction accuracy, database adoption and complete product qualification
were **not_run**, because no corresponding production capability is selected. Their delivery
obligations above remain prospective, not silently passed or prerequisites for this review's
conditional conclusions.
