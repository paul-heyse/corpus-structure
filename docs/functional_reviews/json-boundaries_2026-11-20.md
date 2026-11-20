# JSON boundaries: functional extension review

**Proposed · 2026-11-20.** Give each JSON role one owner with a declared value domain, and
make each schema mean the same thing wherever it is checked. Today JSON is handled by
convention: three codecs, about eight spellings of a decimal, four schema dialects and two
schema engines that disagree on 27 of 56 tested cases. The inquiry started from the
libraries, in the order python-rapidjson, jsonschema, pydantic, pydantic-settings. The
evidence puts the value in a different order. The largest gains are in the schema contract
and in what pydantic is asked to do. python-rapidjson should do one job, exact numbers, and
do it behind one module; most of its unused features do not fit this codebase. Eleven
defects were confirmed on the way and are listed separately from the opportunities.

## Scope and evidence

The operator asked for the best design for everything JSON-related and the changes that reach
it, drawing on python-rapidjson 1.25, jsonschema 4.26.0, pydantic 2.14.1 and pydantic-settings
2.16.1. The review covers the Python packages (`python/`, `tools/`, `tooling/`, `scripts/`)
and the PostgreSQL side where JSON Schema is checked there. The Rust crates are outside it.
The repository baseline is `0888978ad` with a dirty working tree; `cs/` below means
`python/corpus-structure/src/corpus_structure/`.

This review follows the [orjson and JSON codec review](orjson-json-codec_2026-11-20.md), whose
conclusion was that no new codec is warranted. [Correspondence](#correspondence-with-the-orjson-review)
states how its O01–O09 relate to the opportunities here. Design judgment applies FP-04, FP-06,
FP-07, DP-01 to DP-04, DP-11, DP-13 to DP-16 and DP-23 from the
[design standard](../design_review/design_principles/standard.toml).

Library orientation came from the supplied overviews of
`docs/libraries/data_model/python-rapidjson.md`,
[jsonschema](../libraries/data_model/jsonschema.md), [pydantic](../libraries/data_model/pydantic.md)
and [pydantic-settings](../libraries/data_model/pydantic-settings.md), from Context7, and from
tagged and installed sources.

**Inspected · 2026-11-20.** Four mapping passes read the code (python-rapidjson and stdlib
JSON, JSON Schema, pydantic models and JSON boundaries, configuration), followed by two
targeted passes on open items and an independent design assessment that was given the
evidence and not a preferred answer. Call counts are from grep and AST passes and are
approximate.

**Interface-checked · 2026-11-20.** Contracts were read from
[python-rapidjson v1.25](https://github.com/python-rapidjson/python-rapidjson/tree/v1.25) and
its [documentation](https://python-rapidjson.readthedocs.io/), the bundled
[RapidJSON schema notes](https://rapidjson.org/md_doc_schema.html), the installed jsonschema
4.26.0 and referencing 0.37.0, [pg_jsonschema v0.3.4](https://github.com/supabase/pg_jsonschema/tree/v0.3.4),
the installed pydantic 2.14.1 and pydantic-core 2.50.1 with the
[version policy](https://docs.pydantic.dev/latest/version-policy/), the installed
pydantic-settings 2.16.1 and psycopg 3.3.6.

**Tested · 2026-11-20.** Eight [probes](../design_review/evidence/2026-11-20_json-boundary-contracts/README.md)
ran against the project environment and, read-only, against the development database. A
claim marked Tested below rests on those outputs.

Limits: nothing was timed, so every efficiency claim is structural and read from source. The
probes show library behaviour on constructed values and on the assembled wire contracts. The
test suite was not run. Where a count or a path is not established, the text says so.

## What is deployed

### Codecs and their uses

| Codec | Entry points | Calls | Used for |
|---|---|---|---|
| stdlib `json` | `json.loads`, `json.dumps` in 13 option combinations | about 618 and 160 | reading identity facts back, PDF and worker payloads, SQL JSONB literals, files |
| stdlib recipe | `canonical_bytes` (`cs/semantic/identity.py:13`) | about 977 | identity, and also size, validation input and normalisation |
| stdlib recipe | `canonical_json` (`cs/core/canonical.py:82`) | 41 | the D1 §10.1 key scheme, four consumers |
| python-rapidjson | `json_bytes`, `json_loads`, `wire_json_loads` (`cs/semantic/data_operation_json.py`) | about 406, 75 and 84 | exact scope and wire values (ADR-0100), cursors, CLI output |
| pydantic-core | `validate_json`, `model_validate_json`, `model_dump_json`, `model_dump` | about 250, 67 and 648 | typed models, presentation |
| PostgreSQL | `data.canonical_json` and related functions | 36 uses | identity mirrored in SQL |

Fifteen modules use four of these and 27 use three. A rule exists and mostly holds: identity
facts go through `canonical_bytes` and are read back with stdlib `json.loads`, exact scope
and wire values use rapidjson, and PDF, worker and SQL-literal paths use stdlib. It is
written nowhere. Departures include four hand-written cursor codecs beside
`cs/semantic/continuation_codec.py`, two CLI output spellings (`emit` writes
`model_dump_json()` at `cs/cli/output.py:167`; about ten commands write
`json_bytes(model_dump(mode="python"))`), and 13 hashes over plain `json.dumps` of which five
are not canonical (default separators at `cs/schema/model_deployment.py:209`,
`model_discovery.py:147` and `cs/semantic/external_runtime.py:120`; unsorted at
`cs/math/grammar.py:200` and `external_runtime.py:222`).

A decimal has about eight JSON spellings: a string from pydantic's JSON mode, a number from
rapidjson, `{"decimal": …}` from `canonical_bytes`, `["decimal", …]` from the value codec and
its SQL mirror, `["decimal-report", …]`, a `default=str` at `cs/semantic/proposals.py:565`,
an integral-to-int conversion at `pdf_publication_native.py:232`, and
`{"__schema_decimal__": …}` at `pdf_payloads.py:436`.

### Identity bytes

`canonical_bytes` accepts raw floats, performs no Unicode normalisation and is declared
independent of the key scheme (`cs/semantic/identity.py:1`). Floats do reach hashed bytes:
`FrozenContract` digests hash `canonical_bytes(model_dump(mode="json"))`
(`cs/semantic/record_policy.py:28-34`) over float-typed coefficients (`:136`, `:150-153`),
`learned_primary.py:149,179` hashes a raw `0.5`, and the wire contract digest contains one
float default. Structural values do not, because the value codec tags floats as hex first.
`canonical_bytes` writes `Decimal(x)` as `{"decimal": "x"}`, so a literal dict of that shape
hashes the same as the decimal; the comparisons at
`cs/orchestrate/data_operations.py:875,901-902` are correct only because of that collision.
About 90 `model_dump` and 85 `asdict` calls sit inside `canonical_bytes` arguments, so a
presentation choice in a model (a serializer, an alias, a pydantic spelling change) moves an
identity. About 20 identities hash `model_json_schema()` output, which pydantic's version
policy allows to change in a minor release.

### Schemas

Seventeen modules import jsonschema and about twenty more use the wire wrapper
(`cs/semantic/data_operation_wire.py:581-614`), which builds `Draft7Validator(schema,
registry=Registry())` behind a cache. Drafts 7, 2019-09 and 2020-12 are all in use.
`TypeChecker`, `FormatChecker`, `validators.extend`, `best_match` and `ErrorTree` are not
used. Validators are rebuilt per call or per row at
`data_operation_execution_evidence.py:104`, `authority_leaf.py:44-46`,
`demand_results.py:509-510,540-542,628-630`, `diagnostic_selection.py:18-33` and
`data_operation_compilation.py:2632,2699`.

The schemas come from authored YAML (`model/semantic/data-operation-native.yaml`, Draft 7,
with generated schemas spliced in), from pydantic models lowered to Draft 7 by hand
(`generated_json_schema`, `data_operation_wire.py:412-483`), from LinkML, and from database
rows (`sem.data_kind_contract`). PostgreSQL checks schemas with pg_jsonschema 0.3.4: 42
installed functions call it. ADR-0128 places one request check in PostgreSQL and one result
check in the client per call. About a dozen paths still validate one payload two or three
times; `DataOperationWireValue` (`cs/semantic/data_operation_ports.py:55-88`) re-runs
jsonschema at every nesting level and deep-copies on every field read, and
`_validate_wire_value` (`data_operation_wire.py:604-614`) makes four passes before the
schema check.

### Models

There are 695 pydantic model classes, 912 stdlib dataclasses and 236 TypedDicts. No model sets
a `ser_json_*` option. Sixty-six sites encode a Python value to JSON only to call
`validate_json`, to obtain JSON-mode strictness
(`cs/intervene/selected_assessment_server.py:25-31` states the intent). About 45
`TypeAdapter`s are rebuilt on every call. Ten unions use a discriminator; about 230 sites
dispatch on `["kind"]` by hand. Eight MCP result formats carry a rapidjson string inside a
pydantic string field (`exact_json`), because pydantic cannot write an exact number; the
string is sent in both the text and the structured content.

### Configuration

One `BaseSettings` class (`cs/settings.py:234-327`) reads constructor arguments and
`CORPUS_*` variables. Its origin report depends on private pydantic-settings internals
(`:214-232`, `:271-315`). Section models are constructed on their own in production code,
where they ignore the environment. Three sites layer configuration afterwards with
unvalidated `model_copy(update=)`, and the execution-policy file has two hand-written
readers. About twenty `CORPUS_*` names are read by hand and are not settings fields.

## What the libraries do at these boundaries

### python-rapidjson 1.25

The product uses `loads`, `dumps` and the decimal number mode. Everything else is unused.

| Capability | Tested behaviour | Use here |
|---|---|---|
| `Decoder` with pair-preserving objects | refuses duplicate keys at any depth, keeps `NM_DECIMAL`, works on streams; two Python calls per object; defining `end_array` as well triggers an upstream bug | adopt (O02) |
| plain `loads` | keeps the last duplicate; an embedded NUL ends the document silently (`[1]\x00garbage` gives `[1]`), fixed in 1.26; depth beyond the recursion limit raises `RecursionError`, not `ValueError`; invalid UTF-8 raises `UnicodeDecodeError` | contain at one owner (O02) |
| output bytes | equal to the stdlib canonical recipe except the hex case of ten control-character escapes (`\u001F` against `\u001f`) and decimal spelling (`1E+2`) | never a hash input (O03) |
| encoder modes | default accepts tuples, iterators and container subclasses; the strictest modes still pass `str`, `int`, `float` and `Decimal` subclasses, and a `Decimal` subclass's `__str__` can emit invalid JSON | cannot replace the exact-type walk |
| `RawJSON` | inserted unvalidated; untouched by `sort_keys` and `allow_nan`; corrupts output with `ensure_ascii=True`; no way to keep sub-document text on decode | declined |
| stream `dump` and `load` | a generator streams without materializing; a byte bound cannot be enforced by raising from `write` (the error is replaced and `dump` can return as if successful); `load` cannot read JSON Lines | declined |
| `Validator` | Draft 4 only; accepts Draft 7 schemas and does not enforce `const`, `if`, `propertyNames`, `contains` or numeric exclusive bounds; never reports schema errors; integers of 2⁶⁴ or more are not integers; segfaults on very deep input | declined |
| psycopg adapters | `set_json_dumps` accepts a bytes-returning function and can be scoped; the exact codec round-trips `Decimal('1.10')` | adopt for loading (O02) |

On the repository's 72 wire schemas the native validator accepted every mutated `const` value
that jsonschema rejected, and rejected 13 of 91 valid instances. The wire uses `const` 104
times and `if`/`then` 12 times.

### jsonschema 4.26.0 and pg_jsonschema 0.3.4

- jsonschema's `integer` rejects every `Decimal`. A float schema constant against a `Decimal`
  instance fails `minimum` and `const` and raises `TypeError` in `multipleOf`. A Decimal-aware
  `TypeChecker` fixes `integer`; the rest needs the schema decoded with the same decimal
  decoder as the instance.
- The default registry retrieves a remote `$ref` over the network. `registry=Registry()`
  prevents it.
- Constructing a validator checks nothing; `check_schema` is separate. A cached validator
  saves the check and setup.
- Machine-readable error fields exist (`validator`, `validator_value`, both paths,
  `context`), but the missing name for `required` and the extra key for
  `additionalProperties` appear only in the message, which embeds input.
- Python's `pattern` uses `re.search`: `$` accepts a trailing newline and `\d` is Unicode.
  pg_jsonschema uses ECMA classes and rejects the newline.
- pg_jsonschema assumes Draft 2020-12 when `$schema` is absent, asserts `format` under
  Draft 7, compiles the schema on every call, and raises an error for an invalid schema.
- Twenty-seven of 56 schema-and-instance cases give different answers in the two engines.

### pydantic 2.14.1

- `validate_json` reads a JSON number for a `Decimal` field through a float: `1.10` becomes
  `Decimal('1.1')` and digits beyond about 17 are lost. A JSON string stays exact.
- No serializer writes a decimal as an exact JSON number. `dump_json` has no key sorting and
  no byte-stability promise.
- Strict JSON mode accepts strings for `Decimal`, dates, enums and UUIDs and lists for tuples;
  strict Python mode refuses all of them. No single call gives JSON-mode semantics on decoded
  data.
- `JsonValue` has no decimal arm.
- A `GenerateJsonSchema` subclass reproduced the hand lowering to Draft 7 exactly on a sample
  model.
- The JSON parser keeps the last duplicate key and limits depth to about 200.

### pydantic-settings 2.16.1

- A section model built on its own ignores the environment; only the root applies it.
- A source placed last can read the documented `settings_sources_data` and report which
  source supplied each value.
- Sources merge by key, and a `JsonConfigSettingsSource` can be added per call.
- An unknown prefixed variable is ignored without error; malformed JSON in a variable raises
  `SettingsError`, which is not a `ValidationError`.

## Confirmed defects

These are separate from the opportunities. Each is small and independent unless noted.

| # | Defect | Evidence | Fix lives in |
|---|---|---|---|
| D1 | The private-cohort scrub names `CORPUS_DEPLOYMENT_DATABASE*`, but the field is `deployment`, so `CORPUS_DEPLOYMENT__URL` passes into the child environment | `scripts/native_private_cohort.py:49,67`, `tests/native_private_bootstrap.py:145-146`, `cs/settings.py:243` | O10 |
| D2 | Six validation sites can fetch a remote `$ref` over the network | Tested; `demand_results`, `authority_leaf`, `diagnostic_selection`, `scientific_evidence`, `schema/integrity`, execution evidence | O04 |
| D3 | One `prefixItems` node reaches the Draft 7 wire contract un-lowered, so tuple element types of `ProviderExecutionReceipt.work_members` are not checked by either engine | spliced at `data_operation_wire.py:122`; `[1,"x",null]` passes | O06 |
| D4 | A fractional `analyzed_scope` value is truncated to float precision in the execution-evidence leaf and written to the demand export | `execution_evidence_leaf.py:115`, `demand_results.py:644`, `serve/demand_export.py:357`; reproduced on `WireMemberContext` | O08 |
| D5 | Seven installed SQL functions pass schemas with no `$schema`, which PostgreSQL reads as 2020-12 while Python reads the same schemas as Draft 7 | catalog survey, listed in the evidence | O05 |
| D6 | Python accepts a 64-hex digest followed by a newline against `^[0-9a-f]{64}$`; PostgreSQL rejects it. The pattern appears 54 times in installed SQL schemas | Tested | O05 |
| D7 | Deeply nested input raises `RecursionError` past the three CLI decode handlers and the continuation codec | `cli/output.py:141`, `cli/orchestrate.py:453`, `cli/interpretations.py:177` | O02 |
| D8 | Trailing data after a NUL byte is accepted by the exact decoder | Tested on 1.25; fixed upstream in 1.26 | O02 |
| D9 | Section models built on their own ignore the operator's environment | `ingest/hosted_spacy.py:114`, `methods/native_host_clients.py:52`, `semantic/sentence_products.py:711`, `semantic/hanlp_products.py:381,541` | O10 |
| D10 | `SettingsError` is not translated; seven `settings()` calls sit outside a failure boundary | `cli/mcp.py:25,36,51`, `cli/db.py:197,416`, `cli/target.py:18`, `cli/managed.py:1131` | O10 |
| D11 | Bare `NaN` and `Infinity` tokens pass the worker readers | orjson review O04 | unchanged there |

D4 has low impact today: nothing in the demand flow compares or uses the truncated copy, and
the only place it leaves the process is the export column. It is a symptom of a wider
exposure. Every site that validates rapidjson-encoded bytes with pydantic would lose
precision silently if its target gained a decimal field.

Three suspicions were refuted. The two decoders applied to the `native` bytes
(`orchestrate/data_operations.py:1509` and `:843`) read only scalar fields and agree. No path
was found where rapidjson-decoded decimals reach a `pydantic.JsonValue` field; request models
use the project's own value type. Draft 7 applied to LinkML output at
`cs/schema/integrity.py:225` loses nothing, since that generator emits no later keywords.

## The target design

Each role has one owner, a declared value domain and declared guarantees.

| Role | Owner | Accepts | Decimal | Float | Guarantees | Byte-stable |
|---|---|---|---|---|---|---|
| Identity bytes | `cs/core/canonical.py` | exact types only, by named profile | tagged or canonical string, by profile | refused in the key profile; declared spelling in the value profile | encode only; never read back as data | yes, a change is a migration |
| Exact interchange | one module holding the rapidjson import | `str`, `int`, finite `Decimal`, `bool`, `None`, `list`, `dict[str]` | JSON number, scale kept | accepted on encode through the walk; never produced on decode | refuses duplicate keys, non-finite tokens, trailing data, invalid UTF-8; one error type | no, and never hashed |
| Typed models and presentation | pydantic with one scalar-types module and one config preset | model-defined | JSON string | finite only | never the first parser of untrusted text where duplicates matter | no |
| Worker frames | the three worker modules, stdlib only | finite JSON | as stdlib | finite | duplicate refusal, size bound, non-finite refusal | yes, host and worker bytes match |
| Database boundary | `cs/core/db/store.py` and one SQL-literal helper | as exact interchange | as exact interchange | — | as exact interchange | only the SQL-literal spelling |
| Schema documents | one validator factory and one generator | JSON Schema with an explicit dialect | constants decoded exactly | — | no network retrieval; schema checked once | hashed through identity |
| Configuration | `cs/settings.py` | settings models | — | — | one construction path; errors translated | no |

Two rules hold the design together.

**A JSON number that must be exact never passes through pydantic's JSON parser.** Typed models
spell a decimal as a string. Exact numeric regions such as scope stay untyped exact values
and are validated in Python mode.

**A schema has one meaning.** It names its dialect, uses only constructs both engines read
alike, and has one writable authority: the authored schema for the wire protocol, the model
for everything pydantic-modelled.

## Opportunities

All are Proposed. Each needs selection and a plan before any implementation.

<a id="O01"></a>
### O01 — Record the JSON roles, their owners and one spelling per scalar

**Now.** The codec rule is unwritten, a decimal has eight spellings, and
`canonical_bytes` and `json_bytes` each serve four or five purposes.

**Proposed.** An ADR records the role table above: the owner of each role, its value domain,
the spelling of decimal, float, datetime and bytes in each, and what is byte-stable. It
extends ADR-0100 and names the value and SQL profiles beside D1 §10.1. The spellings that
have no role are retired: `["decimal-report", …]`, `default=str`, integral-to-int and
`{"__schema_decimal__": …}`.

**Result.** A reader can tell from a call which contract applies, and a new JSON path has one
place to go. This is the frame for O02 to O08; without it they are separate cleanups.

**Why an ADR.** It chooses between real alternatives and changes what identity bytes may
contain. DP-01, DP-02 and DP-04 apply.

<a id="O02"></a>
### O02 — One exact-interchange codec, with the guarantees stated

**Now.** rapidjson is imported in four modules. No rapidjson boundary refuses duplicate keys.
`wire_json_loads` decides whether a number is exact by whether its key is named
`analyzed_scope` (`cs/semantic/data_operation_json.py:42-55`). Three value aliases describe
the same domain (`DdoJsonValue`, `ExactJSONValue`, the generated `WireExactJSONValue`).
`NativeRowResult` fields are decoded with stdlib and yield floats
(`cs/semantic/operation_value_types.py:30-34`), and the psycopg loader is stdlib.

**Proposed.**
- One module owns the rapidjson import and exports one decoder, one encoder, one value alias
  and one error type.
- The decoder is a `rapidjson.Decoder` subclass with pair-preserving object construction, so
  duplicate keys are refused at every depth. It translates `RecursionError` and
  `UnicodeDecodeError` into the one error type.
- Move to python-rapidjson 1.26 for the trailing-data fix, after comparing `json_bytes`
  output over the pinned vectors under both versions.
- `json_loads`, `wire_json_loads`, the stdlib row decoder and the psycopg loader become that
  one decoder. Typed fields then decide float against decimal, which removes the key-name
  rule. The unused stdlib `dumps` adapter is deleted.
- The encoder keeps the `own_json_value` walk before `dumps`, because encoder modes cannot
  enforce exact types.
- Cursors use this codec through one owner; that belongs inside UDM-14.

**Result.** Every exact boundary gives the same refusals. A semantic distinction stops living
in a key name. The code-identity analyzer keeps one call shape to recognise.

**Depends on.** O04's decimal-aware validator, since decimals then reach jsonschema outside
scope. A check is needed first: run the wire tests with the single decoder and confirm what
consumes non-scope numbers as floats.

**Should rapidjson stay?** Yes, for this role only. It is the one installed library with a
public exact-decimal encoder and decoder; stdlib can decode exactly but has no public way to
write a decimal as a JSON number. Its sharp edges are containable at one owner. The decode
segfault needs a raised recursion limit, which nothing in the product sets. msgspec remains
the alternative under the orjson review's O08 triggers.

<a id="O03"></a>
### O03 — One identity encoder with declared profiles

**Now.** Three canonical emitters exist (`canonical_bytes`, `canonical_json`, SQL
`data.canonical_json`) plus a Python mirror of the SQL form
(`cs/semantic/pdf_certification.py:81-105`). Floats are hashed with no stated policy. The
decimal tag collides with literal data. Identity depends on pydantic's presentation output.
Twenty-eight hashes run over rapidjson bytes and five over non-canonical `json.dumps`.

**Proposed.**
- `cs/core/canonical.py` owns one exact-type walker with three named profiles: the D1 §10.1
  key profile as it is, the value profile (today's `canonical_bytes`), and the profile SQL
  computes.
- The value profile declares its float spelling as CPython `repr`, which moves no digest, and
  refuses a literal dict whose only key is `decimal`. Whether real data contains that shape at
  `data_operations.py:875,901` needs checking first.
- Hashes over `json_bytes` and plain `json.dumps` move to this owner, or hash stored bytes
  directly.
- Identity stops depending on `model_dump(mode="json")`: the walker accepts a model and
  applies its own scalar spellings. This moves digests for decimal and datetime fields, so it
  is decided in O01's ADR. Until then, pin the current output with vectors.
- The digit limit becomes a parameter; today computing a digest reaches the running model
  (`cs/semantic/value_codec.py:20-22`).

**Result.** A pydantic release or a presentation change in a model cannot move an identity.
The exact codec can change version without digest risk. FP-06 and DP-04 apply.

<a id="O04"></a>
### O04 — One validator factory

**Now.** `Draft7Validator(...)` and its siblings are constructed in about eleven modules with
different dialects, caches, registries and error handling.

**Proposed.** One function builds every validator and owns:
- the dialect: the schema must name `$schema`, and a missing one is refused;
- `check_schema` once, cached by schema digest;
- `registry=Registry()` always, which closes D2;
- numbers: `validators.extend` with a decimal-aware `integer`, and schemas decoded with the
  exact decoder so constants and instances compare as decimals;
- one translation into the structured form in `cs/semantic/correction_detail.py`, covering
  the six sites that let a raw `ValidationError` escape.

**Result.** Per-row validator construction disappears, number checks agree with exact
decoding, and no validation can reach the network.

**Not proposed.** `best_match` as a diagnostics contract (its heuristic may change between
versions and its messages carry input), and enabling `FormatChecker` (the installed schemas
use only `binary`, and enabling it changes what existing data passes).

<a id="O05"></a>
### O05 — One contract across Python and PostgreSQL

**Now.** ADR-0128 has PostgreSQL check requests and the client check results. Matching
contract digests show the schema text is the same on both sides. They do not show the two
engines read it the same way, and 27 of 56 tested cases differ.

**Proposed.**
- A portable profile, enforced where the factory builds a validator and where SQL schemas are
  generated: explicit `$schema`, ASCII character classes only, anchored patterns, and no
  `format` used as a constraint.
- `$schema` added to the seven SQL schemas that lack it (D5).
- Python's `pattern` aligned with PostgreSQL's (D6). The candidate is an ECMA-262 regex
  engine behind a `pattern` override in the factory. Whether one aligns the two engines on
  the installed patterns is not established and needs the probe re-run with that column.
- The 56-case differential kept as a test of the profile.
- The remaining known difference, PostgreSQL's loose `maximum` comparison near double
  precision, stated as a limit.

**Result.** ADR-0128's single check per direction becomes sound: a request PostgreSQL accepts
is one the client's schema also accepts. DP-11 and DP-23 apply.

**Alternative.** jsonschema-rs in Python is the same engine family as pg_jsonschema and would
remove the difference by construction. It is a new dependency and its handling of decimal
instances is unknown. Revisit if the regex override does not align the engines or the profile
proves costly to keep.

<a id="O06"></a>
### O06 — One schema generator and one authority per contract

**Now.** Three paths lower or adjust pydantic schemas: `_generated_schema_node`
(`data_operation_wire.py:412-482`), `close()` in
`data_operation_execution_evidence.py:49-70`, and direct `model_json_schema()` calls whose
output is hashed. The second never lowers `prefixItems`, which produces D3, and it adds
`minLength` and closed objects that the model does not state.

**Proposed.**
- One `GenerateJsonSchema` subclass emits the project's dialect. Every pydantic-derived
  schema, including those hashed and those sent to SQL, comes from it.
- Project scalar types carry their schema through `WithJsonSchema`, so hashed schema output
  does not move with a pydantic release.
- The constraints `close()` adds move into the model types.
- Authority: the authored YAML for the wire protocol; the model for everything
  pydantic-modelled, with its schema derived; the declared dialect for LinkML and external
  contracts.

**Result.** D3 closes. A model and its schema cannot disagree, and about 70 lines of lowering
and its refusals have one home. DP-01 applies.

<a id="O07"></a>
### O07 — Validate once

**Now.** The paths listed under [What is deployed](#schemas) validate two or three times.
Plan rows PE-RC01 and PE-F04
(`docs/plans/declared-data-operations_2026-11-12.md:1568,1593`) already set one request check
and one result check per call; they carried into the UDM series with no package picking them
up.

**Proposed.**
- Give PE-RC01 and PE-F04 a UDM package owner and implement ADR-0128 as written.
- `DataOperationWireValue`: one exact-type walk, which is also the detached snapshot, then
  one validation. Copy once at ingress.
- `_validate_wire_value`: the walk and the schema check, without the two encodes and the
  decode between them.
- Where a schema is generated from a model, validate with the model only
  (`data_operation_execution_evidence.py:104`, `authority_leaf.py:44-46`).
- Kind bodies: check in SQL on write; rows that passed need no re-check on read. The
  detached export keeps its independent Python check through the factory.

**Result.** Each payload has one authority and one check per boundary. This is where the
execution-fit gain is, and it is structural: re-validation at every nesting level and a deep
copy on every field read grow with document depth and with reads. FP-07 and DP-03 apply. No
new ADR is needed; this executes ADR-0128.

<a id="O08"></a>
### O08 — Pydantic's scalar policy, and strictness without an encode

**Now.** Sixty-six sites encode to validate. Models use pydantic's default spellings. D4 shows
the loss when an exact number meets pydantic's JSON parser.

**Proposed.**
- One scalar-types module: an exact decimal written as a fixed-notation string
  (`Annotated[Decimal, Field(allow_inf_nan=False), PlainSerializer(...)]`), a finite float,
  an aware datetime and a hex digest type; and one shared config preset.
- Retire encode-to-validate in this order. Validate from the original text where a row was
  decoded only to be re-encoded. Validate the enclosing document once where fragments are
  validated after hand dispatch. Use `validate_python(strict=True)`, or nothing, for values
  already typed. Route what remains (JSON-shaped dicts with tuple fields, such as MCP
  arguments) through one helper that states its single encode.
- Build `TypeAdapter`s once at module level.
- CLI output uses `model_dump_json` throughout once decimals are strings.
- With decimals as strings, typed MCP results stay exact and the `exact_json` wrappers and
  their double transmission become unnecessary. That changes an agent-facing contract owned
  by D8 (`docs/design/D8-agent-and-query-interfaces.md:1163-1166`), so D8 decides.

**Result.** D4 closes and the latent exposure with it. One spelling per scalar in typed
output. Fewer passes over each value.

**Open.** Which stored typed bodies have decimal fields and how each is written is not fully
inventoried; the prepared pack classes with dynamic names were not all walked.

<a id="O09"></a>
### O09 — Typed families in place of hand dispatch and hand validation

**Now.** About 230 sites dispatch on `["kind"]`. Fourteen hand-written validators check key
sets, enums and bounds; `cs/semantic/data_operation_cpu_basis.py:193` is about 85 percent
shape checking, and `terminology.py:334` and `inspection_metadata.py:229` validate bytes
their own module wrote.

**Proposed.** When one of these modules next changes, express model families as discriminated
unions (`Field(discriminator=)`, or a callable `Discriminator` with `Tag` for array-tagged
shapes) and move shape checks into a model shared by writer and reader. Start with
`data_operation_cpu_basis`. Leave the value codec as it is: its tagged arrays are mirrored in
SQL and a union would add machinery. Leave `local_interpretation_reports.py:37` alone; it is
mostly cross-field domain logic.

**Result.** One error per mismatched tag, generated schemas with a discriminator, and less
hand-written shape code. This is opportunistic, not a campaign.

<a id="O10"></a>
### O10 — Configuration through one path

**Proposed.**
- Derive the scrub list from the settings model with the existing `known_env_names`
  (`cs/settings.py:364`), which closes D1.
- Production code receives sections from the one `Settings` instance; the bare constructions
  go (D9). `MethodSettings` (`cs/core/method.py:426-439`) derives its defaults.
- Replace the private-API origin tracking with a source placed last that reads
  `settings_sources_data`. Remove the alias handling that serves no aliased field.
- Express the profile swap, the credential rebuild and the authoring database as validated
  construction, and the execution-policy file as a `JsonConfigSettingsSource`, replacing
  `model_copy(update=)` and the two hand-written readers.
- One accessor translates `SettingsError` (D10).
- Product variables read by hand become fields; CI lane variables stay with `ci`. The
  `target_fingerprint` hash moves to the identity encoder.

**Result.** A setting reaches every consumer, every layer is validated, and a
pydantic-settings upgrade stops being a risk to the origin report. This is independent of
O01 to O08 and can proceed at any time. Removing the `llm` and `gpu` sections stays with
SET-01.

<a id="O11"></a>
### O11 — Conditional: one dialect, Draft 2020-12

**Now.** The wire is Draft 7; pydantic, `validator_for` and pg_jsonschema all default to
2020-12.

**Proposed.** Make the dialect explicit everywhere first (O04, O05). Then move the authored
wire schema to 2020-12 when the wire contract digest next moves for another reason, and
delete the lowering. This supersedes ADR-0128's Draft 7 clause.

**Why conditional.** The rewrite is mechanical, but it moves `wire_contract_digest` and the
frozen program identities that depend on wire schema bytes, and that set has not been
listed. With O06 in place, staying on Draft 7 costs one small generator subclass. What should
not continue is the implicit mix (D5, and `Draft7Validator` applied to a `body_schema` that
may be 2020-12 at `cs/semantic/demand_results.py:510`).

## Declined

| Idea | Reason | Revisit when |
|---|---|---|
| `rapidjson.Validator` for the wire | Draft 4 only; lax on 104 `const` and 20 conditional keywords; wrong on large integers; crashes on deep input | the binding exposes a later draft |
| `RawJSON` for embedding | unvalidated, unsafe with `ensure_ascii=True`, and O08 removes the main candidate | a measured need on a non-hashed path with codec-produced fragments |
| rapidjson streams for exports and JSON Lines | no reliable byte bound; cannot read JSON Lines; the hashed PDF export needs its exact bytes | — |
| encoder modes in place of the exact-type walk | subclasses still pass | — |
| pydantic as the identity encoder | no key sorting, no stability promise | — |
| `hypothesis-jsonschema` | installed, never imported; drafts 4, 6 and 7 only | remove the dependency, or use it for Draft 7 wire tests if O11 is not taken |
| msgspec, orjson | as the orjson review's O08 and O09 | the triggers stated there |

## Correspondence with the orjson review

| orjson review | Here |
|---|---|
| O01 declare the identity value domain | carried into O01 and O03, with the float and tag-collision findings added |
| O02 separate owners for uses of canonical bytes | carried into O01, O03 and O08 |
| O03 one response-size measure | unchanged there |
| O04 refuse non-finite tokens at the worker | unchanged there; listed here as D11 |
| O05 jsonschema number alignment and cached validators | superseded by O04, which adds dialect, registry and error ownership |
| O06 parse each selected-source event once | unchanged there |
| O07 contain the exact codec and merge SQL-literal helpers | codec containment carried into O02; the SQL-literal helper stays there |
| O08 msgspec conditional, O09 orjson declined | unchanged there |

## Order and interactions

1. **Defects first, in any order:** D1, D2, D5, D7, D9, D10, D11, and D3 once the splice can
   use the existing lowering. None needs an ADR.
2. **Two decisions:** an ADR for the roles and value domains (O01, with O03's digest
   movement), and an ADR for the schema contract (O04 to O06, the authority rule, and O11's
   dialect question), the second superseding one clause of ADR-0128.
3. **Foundations:** O04 before O02, because the single decoder sends decimals to jsonschema.
   O03 before the 1.26 bump is convenient, since it removes rapidjson bytes from hashes. O06
   before O07 where a schema is model-derived.
4. **Follow-through:** O07 and O08, which remove most of the passes.
5. **Any time:** O10. **Opportunistic:** O09.

The active UDM series touches several of these. UDM-10 authenticates the rapidjson options,
so O02 changes what it authenticates. UDM-13 plans a typed canonical JSON Lines codec for the
disk cache, which should use O03's owner. UDM-14 owns continuations, where the cursor
unification belongs. Nothing here is scheduled in any plan today.

## What would demonstrate each

| Opportunity | Demonstration |
|---|---|
| O02 | duplicate keys, trailing data and over-deep input refused with one error type at every exact boundary; wire tests pass with one decoder |
| O03 | pinned digests unchanged under the declared float policy; a model serializer change does not move a digest |
| O04 | no validator constructed outside the factory; a remote `$ref` fails without a network call; `Decimal('1')` passes `integer` |
| O05 | the differential test shows no disagreement on profile-conforming schemas |
| O06 | generated schemas equal the current lowered output for existing models; `[1,"x",null]` fails `work_members` |
| O07 | one schema check per boundary on the listed paths, shown by test or trace |
| O08 | a fractional scope value survives the leaf and the export exactly |
| O10 | `CORPUS_DEPLOYMENT__URL` is absent from the private-cohort environment; `CORPUS_NEMOTRON__ENDPOINT` reaches every consumer |

## Open checks

- Whether an ECMA regex override aligns Python with PostgreSQL on the installed patterns (O05).
- What consumes non-scope wire numbers as floats (O02).
- Whether the `{"decimal": …}` literal occurs in real compared data (O03).
- Which frozen identities depend on wire schema bytes (O11).
- Which 2020-12 keywords `body_schema` can contain at `demand_results.py:510`.
- `json_bytes` output under python-rapidjson 1.25 against 1.26, and whether code identity
  covers the package version (O02).
- The decimal-field inventory for stored typed bodies (O08).
- The count of `json_matches_schema` uses: the live catalog shows 55 calls in 42 functions,
  one source reading counted 108 and another 506 in the latest migration; these were not
  reconciled.
