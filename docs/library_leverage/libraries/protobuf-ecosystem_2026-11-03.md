# Protobuf ecosystem: capability types and applicability

**Interface-checked library mechanisms; Proposed applicability · 2026-11-03.** Context7 and primary
sources informed this assessment. Baseline HEAD `7123080e` plus concurrent audit-closure changes;
root probes are separately [recorded](../../design_review/evidence/2026-11-03_protobuf-capabilities/README.md).
Comparative preference belongs to the [functional review](../../functional_reviews/protobuf-capabilities_2026-11-03.md).
The actively implemented audit-closure target is the future comparison baseline. The operator
excluded structured-logging-observability as an implementation premise.

The [base patterns](../patterns.md) and [additional patterns](../assessment-patterns.md) support
mechanical derivation, movement, preparation, lifecycle and explicit-input reasoning. No new
pattern is needed. Reusable types below are independent of current local matches.

## Reusable capability types

### protobuf/python-representations

Google protobuf supplies generated/dynamic messages, `HasField`, `WhichOneof`, binary/ProtoJSON
conversion and descriptors. Buf protobuf-py supplies readable generated classes, `Oneof`,
`to_binary/from_binary`, explicit registries and optional native acceleration. Wire conformance
is not Google object compatibility. Proto-plus retains Google's engine and bridges through
`proto.Message.pb()`/`wrap()`. Betterproto2 offers dataclass generation; pure-protobuf offers
annotation-based Python authoring. These differ in schema ownership, mutation, typing, presence,
unknown fields and extension coverage, not just constructor ergonomics.
[Google API](https://protobuf.dev/reference/python/python-generated/),
[Buf runtime](https://protobufpy.com/),
[Proto Plus bridge](https://googleapis.dev/python/proto-plus/latest/reference/message.html),
[Betterproto2](https://github.com/betterproto/python-betterproto2#readme),
[pure-protobuf](https://github.com/eigenein/protobuf#readme).

### protobuf/application-model-integration

Buf's `TypeAdapter(MessageClass)` supports validation, JSON dumps and JSON Schema, and classes
can be Pydantic fields. JSON follows ProtoJSON, unknown fields are ignored, and Python-mode dumps
retain message objects. These APIs do not automatically execute Protovalidate business rules.
`protobuf-to-pydantic` generates BaseModel representations and supports PGV-style rules, but its
upstream README marks Protovalidate support unchecked. A generated adapter must state which
constraints and unknown fields it loses.
[Pydantic integration](https://protobufpy.com/pydantic/),
[adapter feature status](https://github.com/so1n/protobuf_to_pydantic#readme).

### protobuf/schema-defined-validation

Protovalidate exposes `Validator`, `validate`, `collect_violations`, `fail_fast` and distinct
`CompilationError`, `EvaluationError`, `ValidationError`. Current signatures accept Google and
Buf messages. Version 2 moved execution to native protovalidate-cc; violations use Buf messages,
nested fields may be None, JSON uses `.to_json()`, and Google protobuf is no longer supplied
transitively. CEL still executes in the native layer. Residual responsibilities include enforcement
placement, rule identity/path adaptation, validator lifetime and state/evidence/relational rules.
[API source](https://github.com/bufbuild/protovalidate-py/blob/main/protovalidate/__init__.py),
[2.x migration](https://buf.build/blog/faster-protovalidate).

### protobuf/derived-generation-and-discovery

`FileDescriptorSet`, isolated `DescriptorPool` and `message_factory.GetMessageClass` support
unknown-at-development-time schema inspection without application-generated classes. Imported
descriptors/options must resolve from qualified dependencies. Runtime descriptors do not promise
source text or source-retained options. Compiler plugins exchange `CodeGeneratorRequest/Response`.
Buf can build local images, compare FILE/PACKAGE/WIRE_JSON/WIRE compatibility and invoke pinned
plugins. BSR additionally distributes schemas/SDKs; local reflection does not require it.
[Python factory](https://github.com/protocolbuffers/protobuf/blob/main/python/google/protobuf/message_factory.py),
[Buf breaking](https://buf.build/docs/breaking/),
[BSR Python SDKs](https://buf.build/docs/bsr/generated-sdks/python/).

Built-in pyi and mypy-protobuf support static bindings. The latter names mypy/pyright support;
Pyrefly integration is a separate question. Prost/tonic generators enable polyglot interfaces,
with coordinated `extern_path`/well-known-type options and separately selected crate runtimes.
Plain Serde is not automatically ProtoJSON. Documentation/JSON Schema plugins expose derived
views; matching actual parser/semantic validation remains an obligation.
[mypy-protobuf](https://github.com/nipunn1313/mypy-protobuf#readme),
[tonic plugin 0.5.0](https://docs.rs/crate/protoc-gen-tonic/0.5.0/source/README.md),
[JSON Schema plugin](https://github.com/bufbuild/protoschema-plugins#json-schema).

### protobuf/rpc-surfaces

`grpc.aio` supplies C-Core asyncio transport, all four RPC shapes, serializer hooks and owned
channel/server shutdown. Async objects have thread affinity. grpclib supplies asyncio/hyper-h2
and custom codecs. Betterproto2 generation chooses sync grpcio or async grpclib clients and
async server bases; its docs have contradictory defaults, requiring exact-source confirmation.
Connect supplies sync/async clients and ASGI/WSGI surfaces for Connect/gRPC/gRPC-Web, with
`protobuf=google` available independently of changing runtime. HTTP/2 trailers and server/proxy
conformance determine actual gRPC support. Current docs direct that route toward pyvoy, describe
a reflection companion and no built-in health service. Protocol support is not deployment fit.
[gRPC AsyncIO](https://grpc.github.io/grpc/python/grpc_asyncio.html),
[grpclib](https://grpclib.readthedocs.io/en/latest/),
[Betterproto2 generation](https://betterproto.github.io/python-betterproto2/getting-started/),
[Connect compatibility](https://connectrpc.com/docs/python/grpc-compatibility/),
[deployment limits](https://connectrpc.com/docs/python/deployment/).

A Go grpc-gateway can derive HTTP/JSON routes from annotations or configured mappings. OpenAPI
3.1 output is Alpha, does not consume v2 annotations and requires HTTP-bound services. It introduces
a Go deployment lifecycle, unlike simply exporting a descriptor package.
[Gateway](https://github.com/grpc-ecosystem/grpc-gateway#readme),
[OpenAPI limits](https://grpc-ecosystem.github.io/grpc-gateway/docs/mapping/openapi_v3/).

### protobuf/attributed-binary-research

Protoscan extracts embedded descriptors; reproto reconstructs schemas/descriptor databases;
prototext ranks candidate message types; protolens/protoscope assist interactive/wire inspection.
Byte-exact annotated reconstruction and semantic equivalence are different claims. Extracted
schemas establish what was embedded, not original authorship or deployed meaning. Wire inference
cannot recover all field types/names. Blackbox protobuf's current upstream package is bbpb;
`blackboxprotobuf` denotes an older fork, so package identity needs checking before selection.
[Prototools](https://github.com/ThalesGroup/prototools#readme),
[prototext](https://github.com/ThalesGroup/prototools/blob/main/prototext/README.md),
[Blackbox upstream](https://github.com/nccgroup/blackboxprotobuf#readme).

### protobuf/operator-and-event-integration

Reflection clients such as grpcurl can discover/invoke services or use local descriptors;
`-protoset-out` retains a qualified schema observation. Health/status/admin tools address specific
operational questions, not application correctness. OTLP plus Collector pipelines enables common
telemetry exchange, but does not instrument applications. Kafka ProtobufSerializer/Deserializer
and SchemaRegistryClient add message framing/schema identity requiring their own service lifecycle;
Confluent Registry and BSR serve different responsibilities. Shared googleapis-common-protos
contracts can avoid private error/API schema forks.
[grpcurl](https://github.com/fullstorydev/grpcurl#readme),
[Collector pipelines](https://opentelemetry.io/docs/collector/configuration/),
[Kafka client](https://github.com/confluentinc/confluent-kafka-python#readme),
[shared definitions](https://github.com/googleapis/googleapis).

## Contextual applicability and evidence strength

| Responsibility | Fit and limits |
|---|---|
| Immutable semantic release and operation/query discovery | Conditional fit for descriptor export; native LinkML core generation compiles, but tag/enum evolution and fidelity defaults need correction before a public interface |
| DomainQuery registration | Buf TypeAdapter alone is insufficient: current params/result must be BaseModel classes. An owned adapter or deliberate registry contract change remains |
| Native requests, operation calls, source admission | Conditional transport/preflight fit; existing released validation, canonical identity and protected publication remain necessary |
| Arrow/DuckDB analytic transfer | No demonstrated replacement benefit; presence/null/recursive mappings and conversion work remain. Keep columnar data separate from a proposed worker control protocol |
| Query/coverage/evidence consumers | Use post-AC10/11 meanings; protobuf cannot establish standing, bounded walks or snapshot correctness by encoding them |
| Binary/schema corpus research | Conditional new workflow beyond PDF-only intake; require original-byte custody and extracted/inferred distinction |
| Observability | Independent optional diagnostic proposal, without the unselected logging plan as a dependency |
| Kafka/event delivery | No selected bus consumer in inspected code; retained capability, no adoption recommendation |

Project runtime 6.33.6 and grpcio 1.85.1 are transitive installed/locked dependencies. Host protoc
36.2 generates Python requiring 7.36.2; the actual import refusal is preserved in the evidence.
Buf 1.75.0 is available. grpcurl reports a development build rather than the inventory version.
Published metadata identifies protobuf-py 0.7.0 Alpha, Protovalidate 2.1.0 and Connect 0.13.0 Beta;
these are researched candidate baselines, not installed project dependencies. Python 3.14 wheel,
checker and third-party interoperability remain qualification questions if selected.
[Buf metadata](https://pypi.org/project/protobuf-py/),
[Protovalidate metadata](https://pypi.org/project/protovalidate/),
[Connect metadata](https://pypi.org/project/connectrpc/).

The principal review owns comparative recommendations and their validation/delivery scenarios.
No live RPC, alternate-runtime validator, cross-language client, extraction accuracy or performance
was tested by this research contribution. Upstream conformance claims retain their upstream scope.
