# Executable boundaries and directional representations

**Source-inspected discovery, 2026-11-10; benefits Proposed.** [Baseline](../briefing.md).
References: [Pydantic](../../../../libraries/data_model/pydantic.md),
[msgspec/attrs/cattrs](../../../../libraries/data_model/msgspec_attrs_and_cattrs.md),
and the dated [Pydantic](../../pydantic/README.md) and [cattrs](../../cattrs/README.md) accounts.

## Existing adoption

[boundary.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/boundary.py)
already uses `create_model`, `Annotated`, constraints, discriminators, recursive rebuilds,
`MISSING`, strict/frozen/extra-forbidden configuration and reusable adapters.
The earlier per-field/private-adapter premise is superseded by current release-owned adapters.
Handwritten Pydantic models also serve method requests/results, orchestration, evaluation,
CLI/MCP contracts and external provider boundaries. Their existence alone establishes no duplication:
many own different domains or provider-specific validation.

<a id="ddm-03"></a>

## DDM-03 — Extend executable contracts across actual semantic boundaries

**Status:** candidate broader use of an already deeply adopted capability.
Pydantic supports adapters for collections, dataclasses, typed dictionaries and recursive aliases
as well as BaseModel; reusable constrained `Annotated` types and discriminated unions can
carry meaning without imposing an object hierarchy everywhere.

**Broader use and value:** inspect recurring identifier/value variants, bounded numerical fields,
presence rules and parameter/result shapes in method and report consumers. Derive mechanical
boundaries from the applicable released declaration where they share meaning, then reuse prepared
adapters through the product's valid lifetime. Where a hand-owned operational model is the
authority, its ordinary type contract can remain authoritative. This can reduce scattered
constraint interpretation without converting every algorithm into a declaration.

**Defeater and retain case:** typed shape does not establish reference resolution, source support,
native custody or deep immutability. Default validation, copy/update bypasses, instance
revalidation, nested mutable fields and Python-versus-JSON strictness must match the real
construction contract. Frozen outer models alone do not make reuse sound.

**Next question:** for one repeated boundary, which declarations genuinely coincide, and do
all legitimate construction/copy/read paths preserve the same invariant? Preserve independent
negative expectations for malformed variants, absent/null and nonfinite values.

<a id="ddm-04"></a>

## DDM-04 — Make archive and transport representations explicitly directional

**Status:** concrete conversion seam; choice of replacement remains unsettled.
[releases.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/releases.py)
`_archive_wire_payload` converts bytes to PostgreSQL hex, serializes with `json.dumps(allow_nan=False)`
and validates JSON through `TypeAdapter(JsonValue)` to obtain Python data for archive publication.
[archive_reader.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/archive_reader.py)
reconstructs typed products with cattrs and manually checks archive root/registry-row wire shapes.
[contracts.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/contracts.py)
has another exact-primitive converter configured before composite hooks capture it.

**Mechanisms and broader use:** Pydantic directional serializers/shared schema definitions,
cattrs generated structure/unstructure hooks, field overrides and hook factories can own
mechanical representation mapping. A typed archive root could connect product fields and
wire-only `body_hex` representation without making archive reconstruction a second semantic
ingress validator. Share converter configuration only where contracts coincide; keep converter
instances scoped to their own reconstruction responsibilities.

msgspec typed codecs, `Struct`, tagged unions, `Raw`, `convert` and reusable encoders offer
a separate unused option when a real transport path can remove parse/map/validate passes.
attrs converters/validators and lifecycle hooks offer another conditional option where ordinary
object construction needs richer invariants. Neither library needs general adoption to explore
one boundary; msgspec is not installed in the inspected interpreter.

**Defeater and retain case:** current JSON round-tripping deliberately converts tuples to arrays,
applies JSON key behavior and refuses nonfinite numbers. Pydantic's default JSON serialization
can convert nonfinite numbers to null, so a naive dump replacement changes behavior.
Canonical identity bytes, Decimal spelling, presence, PostgreSQL byte encoding, aliases and
subclass projection require explicit fidelity contracts. Direct msgspec decoding of attrs does
not automatically reproduce attrs converters; delegation through cattrs must preserve nested hooks.
Small explicit mappings can remain clearer than configurable conversion infrastructure.

**Next question:** can a directional adapter remove the JSON round-trip while preserving all
wire semantics at `publish_release_archive`, with independent cases for tuples, byte values,
keys and nonfinite input? If that fails, retain the current conversion and investigate only
the independently useful root reconstruction contract.

<a id="ddm-13"></a>

## DDM-13 — Prepare one complete recipe-wire boundary

**Status:** concrete candidate broader Pydantic use.
[ingest/pdf.py](../../../../../python/corpus-structure/src/corpus_structure/ingest/pdf.py)
defines frozen PdfRecipe with ordinary constructor invariants and canonical bytes. `from_bytes`
first parses JSON to require exactly every dataclass field, then uses a newly constructed
`TypeAdapter(cls)` to parse and validate JSON again.

**Mechanism and value:** a prepared dataclass/wire adapter could govern complete field presence,
types and reconstruction with one parse, retaining `__post_init__`. Installed Pydantic's
TypeAdapter initialization generates machinery when the type has no compiled schema to reuse;
reusing the adapter could remove repeated preparation as well as duplicate decoding.

**Defeater and retain case:** archived fields are explicitly required even where the constructor
has defaults. An ordinary dataclass adapter accepting omitted defaults is not equivalent, and a
hand-maintained duplicate wire class may be worse than the small presence check. Dataclasses own
their configuration; overriding adapter configuration is not a general solution.

**Next question:** can explicit archived presence be derived from PdfRecipe through an established
mechanism while retaining strict JSON tuple handling, constructor invariants, subclass behavior
and exact `to_bytes` identity? Retain the current guard if the complete contract cannot simplify.

<a id="ddm-14"></a>

## DDM-14 — Compose nested structural-product contracts under the bound release

**Status:** concrete broader-use candidate in released model composition.
[observations.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/observations.py)
validates/dumps StructuralProductReport, then validates nested ContextualEnrichmentReport and
SourceContribution values through canonical JSON and release-bound adapters before validating
the enclosing SourceObservationBatch. It also explicitly normalizes nested comparison conditions.

**Mechanism and value:** investigate whether the admitted outer model can compile those nested
contracts or use prepared collection adapters with explicit release context. This could let
the product own nested boundary placement rather than requiring consumer-specific traversal.

**Defeater and retain case:** leaf and outer checks may establish different properties. JSON
validation and strict Python validation accept different representations. Tagged source scalars,
hexadecimal floats, field positions, absent/null distinctions and subclass-aware payload dumps
in this module are intentional semantic encoding, not generic conversion to remove.

**Next question:** what nested guarantees are missing from the actual generated outer schema,
and can they compose under a supplied release without global capture or whole-release rebuilding?
Inspect the generated contract before removing any validation step.

## Other surveyed territory

Shared JSON Schema definitions/input-output modes connect to [DDM-09](portable-contracts-and-settings.md#ddm-09).
Aliases, contextual serializers, encoded/binary/temporal types and custom errors deserve targeted
research when a consumer needs them. Prefer high-level `ValidateAs`/annotation composition over
custom core-schema hooks when sufficient. A reusable serializer must preserve the direction's
meaning, not merely emit accepted JSON.

Partial parsing, lazy iterables, `FailFast` and `OnErrorOmit` are conditional tools for provisional
provider output; they cannot imply complete admission or silently discard required evidence.
MessagePack, zero-copy views, plugin interception and instrumentation need a named consumer.
No codec benchmark or broad model-library replacement is warranted by the inspected seams.
