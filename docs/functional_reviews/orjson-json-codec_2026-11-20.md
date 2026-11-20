# orjson and the JSON codec arrangement: functional extension review

**Proposed · 2026-11-20.** Do not adopt orjson. No path in this codebase gains enough from it
to justify a fourth JSON codec, and the paths where JSON volume is highest are the ones where
orjson's contracts do not fit: bytes that are hashed, exact decimals, bounded streaming and a
stdlib-only worker. Keep msgspec as the one conditional alternative, as a possible replacement
for python-rapidjson behind named triggers. The useful result of the inquiry is a set of
improvements that need no new library: declare what the identity recipe accepts, give each use
of canonical bytes its own owner, measure response size once, refuse `NaN` tokens at the worker
boundary, and align jsonschema's number handling with the decoded instances.

## Scope and evidence

The operator asked what opportunities exist to improve the design by leveraging orjson, with
msgspec and jsonschema understood well enough to judge that. The review covers the Python
packages (`python/`, `tools/`, `tooling/`, `scripts/`). The Rust crates and any change to the
D1 key scheme are outside it. The repository baseline is `5172e9a7b`.

Library orientation came from the supplied overviews of
`docs/libraries/analytical_infrastructure/orjson.md`,
[msgspec, attrs and cattrs](../libraries/data_model/msgspec_attrs_and_cattrs.md) and
[jsonschema](../libraries/data_model/jsonschema.md), and from Context7 (`/ijl/orjson`,
`/websites/jcristharif_msgspec`). Design judgment applies FP-04, FP-07, DP-04, DP-11 and
DP-13 to DP-16 with H4 and H12 to H20 from the
[design standard](../design_review/design_principles/standard.toml).

**Inspected · 2026-11-20.** Three delegated passes read the code: a broad map of JSON
production and consumption, a targeted read of the candidate sites, and an independent
design assessment that was given the evidence and not a preferred answer. Call counts are
from grep and are approximate.

**Interface-checked · 2026-11-20.** Contracts were read from tagged sources:
[orjson 3.13.0](https://github.com/ijl/orjson/blob/3.13.0/README.md) and its
[changelog](https://github.com/ijl/orjson/blob/3.13.0/CHANGELOG.md),
[msgspec 0.22.0](https://github.com/msgspec/msgspec/tree/0.22.0), and the installed
psycopg 3.3.6, SQLAlchemy 2.1.6, structlog 26.1.0, pydantic 2.14.1, cattrs 26.2.1 and
jsonschema 4.26.0.

**Tested · 2026-11-20.** A [probe](../design_review/evidence/2026-11-20_orjson-codec-contracts/README.md)
compared orjson and msgspec with this repository's two byte recipes on CPython 3.14.10, using
synthetic values and ephemeral installs. It establishes library behaviour on those values.
It does not establish which values production code actually hashes. Version-to-version
stability, subinterpreter refusal, spawned-process import and the jsonschema and pydantic
number checks were observed by the library-research pass and are not in the recorded probe.

No performance measurement was made. Speed figures in the orjson overview are upstream's.

## What is deployed

Neither orjson nor msgspec is declared or locked. Three codecs already produce JSON bytes, and
PostgreSQL builds JSON text as well.

| Codec | Where | Role |
|---|---|---|
| stdlib `json` | About 780 direct calls in product source | Identity bytes, JSONL files, worker frames, JSONB literals in generated SQL |
| python-rapidjson 1.25, `NM_DECIMAL` | [`data_operation_json.py`](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_json.py): about 380 `json_bytes` and 160 `json_loads`/`wire_json_loads` calls | Exact decimals for declared-data-operation scope values (ADR-0100), cursors, served-row cache, demand export, 19 digests |
| pydantic-core 2.50.1 | `validate_json`, `model_dump_json`, `dump_json` across several hundred sites | Typed boundaries, CLI and MCP output |
| ijson 3.6.0 | [`selected_source.py`](../../python/corpus-structure/src/corpus_structure/serve/selected_source.py) | One streaming structural read |
| PostgreSQL | `data.canonical_json` and `sha256` in generated SQL | Digests computed in the database |

Four properties of this code decide most of what follows.

**JSON bytes are identity.** About 150 sites hash JSON with SHA-256, through at least five
recipes:

- `canonical_bytes` in [`identity.py`](../../python/corpus-structure/src/corpus_structure/semantic/identity.py)
  is stdlib `dumps` with sorted keys, compact separators, UTF-8 output, `allow_nan=False` and
  Decimal written as `{"decimal": text}`. It has about 940 call sites, about 114 of which feed
  a hash.
- `canonical_json` in [`canonical.py`](../../python/corpus-structure/src/corpus_structure/core/canonical.py)
  is the D1 §10.1 key scheme. It adds NFC normalization and refuses floats, Decimals and
  non-string keys.
- rapidjson `json_bytes` feeds 19 digests, cache keys and export manifests.
- About 26 inline `json.dumps` calls feed a hash with mixed options.
- `data.canonical_json` reproduces canonical text in SQL, and
  [`pdf_certification.py`](../../python/corpus-structure/src/corpus_structure/semantic/pdf_certification.py)
  mirrors it in Python as a parity oracle.

Tests pin 29 digests and 18 byte literals. Fifty-seven frozen `target_alembic` program-identity
files depend on the spelling of JSONB literals written by about 20 local `_json` helpers.

**Exact decimals matter.** rapidjson is present because scope values must round-trip as exact
decimals. `1.10` must come back as `Decimal('1.10')`.

**The largest outputs are streamed under bounds.** The PDF record export in
[`pdf_record_reader.py`](../../python/corpus-structure/src/corpus_structure/semantic/pdf_record_reader.py)
assembles JSON as byte chunks, checks for cancellation around every write, passes verified
stored bytes through without decoding them, and hashes the stream. The worker host in
[`native_host.py`](../../python/corpus-structure/src/corpus_structure/methods/native_host.py)
encodes frames with `iterencode` and stops as soon as a frame would pass 8 MiB.

**Some code runs outside the project environment.** The native host worker is launched with
`python -I` in the provider's environment and uses only the standard library. Its frame bytes
must equal the host's, because the receipt digest is checked against both.

## What the libraries do against these recipes

### Encoding

The probe ran 20,000 generated values per domain against the `canonical_bytes` recipe.

| Value domain | orjson `OPT_SORT_KEYS` with `default` | msgspec `order="deterministic"` with callable `decimal_format` |
|---|---|---|
| Strings, 64-bit integers, bool, null, Decimal, nested lists and string-keyed objects | Byte-identical | Byte-identical |
| Finite floats | Differ where the decimal exponent is −9 to −5: `1e-7` for stdlib's `1e-07`, `0.00001` for `1e-05` | Differ in the same band, and for every magnitude from 1e16 up: `1e16` for `1e+16` |
| Integers beyond 64 bits | Refused | Written |
| `NaN`, infinity | Written as `null` | Written as `null` |
| Plain `Enum`, `UUID`, dataclass | Written silently. Dataclasses can be blocked with `OPT_PASSTHROUGH_DATACLASS`; `Enum` and `UUID` cannot | Written silently |
| Integer keys | Refused | Refused |
| `StrEnum` keys | Refused | Written |

Key order and string escapes match the stdlib recipe in both libraries. Both sort by code
point, which is the order D1 §10.1 specifies.

Three of those rows change behaviour that the recipe relies on. The stdlib recipe refuses
`NaN` and refuses unknown types; orjson and msgspec accept them. Restoring refusal means
walking the value in Python first, which gives back much of what a native encoder saves.

orjson gives no byte-stability promise. Its
[3.11.7 release](https://github.com/ijl/orjson/blob/3.13.0/CHANGELOG.md) changed how positive
float exponents are written and told users with byte-exact tests to take note.

Against the rapidjson recipe, msgspec's `Encoder(decimal_format="number")` was byte-identical
on 20,000 values of integers, finite Decimals and text from U+0020 upward. Two differences
remain. rapidjson writes control characters with uppercase hex (`\u000B`) and msgspec with
lowercase. rapidjson refuses a non-finite Decimal and msgspec writes `NaN`, which is not JSON.

### Decoding

| Input | stdlib | rapidjson `NM_DECIMAL` | orjson | msgspec `float_hook=Decimal` |
|---|---|---|---|---|
| `1.10` | float `1.1` | `Decimal('1.10')` | float `1.1` | `Decimal('1.10')` |
| `18446744073709551616` (2⁶⁴) | exact integer | exact integer | **float `1.8446744073709552e+19`, no error** | exact integer |
| `1E400` | float `inf` | refused | refused | `Decimal('1E+400')` |
| `NaN` token | accepted | refused | refused | refused |
| Duplicate keys | last wins | last wins | last wins | last wins |
| Lone surrogate escape, UTF-8 BOM | accepted | refused | refused | refused |

orjson has no decimal mode, no decoder hooks, and turns an integer beyond 64 bits into a
float without raising. In a codebase that stores large exact values as JSON, that last
behaviour rules orjson out as a general-purpose decoder. None of the four libraries detects
duplicate keys. Only stdlib's `object_pairs_hook`, which the worker readers use, can.

### Embedding and streaming

`orjson.Fragment` copies encoded JSON into an outer document with no validation. It works
only inside one `dumps` call over the whole document and has no decode-side counterpart.
`msgspec.Raw` does the same on encode and can also capture an undecoded subdocument during
typed decode. Neither library can encode incrementally or stop at a size bound. The only
route is to encode the whole document and then check its length.

### Other boundaries

- **psycopg.** `set_json_dumps` accepts a function that returns bytes, and `set_json_loads`
  always receives bytes. SQLAlchemy's `json_serializer` never reaches connections supplied
  through `creator=`, so the per-connection `configure` hook in
  [`store.py`](../../python/corpus-structure/src/corpus_structure/core/db/store.py) is the
  correct place for any adapter.
- **pydantic-core.** `to_json` cannot sort keys. `TypeAdapter(Decimal).validate_json(b"1.10")`
  returns `Decimal('1.1')`: JSON numbers pass through a float. It cannot own identity bytes or
  exact decimals.
- **jsonschema.** `type: integer` rejects `Decimal('1')` and accepts float `1.0`. `multipleOf`
  raises `TypeError` when a float and a Decimal meet. `minimum: 0.1` rejects `Decimal('0.1')`.
- **Deployment.** orjson 3.13.0 has CPython 3.14 wheels, no free-threaded wheel, no
  subinterpreter support, no dependencies, and an upstream with no issue tracker. msgspec
  0.22.0 has 3.14 and free-threaded wheels, an open tracker, and is pre-1.0.

## The arrangements compared

| Arrangement | Assessment |
|---|---|
| **A. No new library; fewer named owners for the existing recipes, with pydantic-core doing the parse-once and measure-once work it already owns** | **Recommended.** The problems found are an undeclared input domain, one serialization reused for several purposes, and repeated passes. A faster encoder addresses none of them |
| **B. orjson for paths that are not identity** | Declined. Each candidate path has a disqualifier, set out under [O09](#O09). What remains is a fourth codec for small, unmeasured gains |
| **C. orjson behind `canonical_bytes`** | Declined firmly. Float spelling moves pinned digests, refusals become silent acceptance, upstream promises no stability, and the SQL counterpart and frozen manifests constrain the bytes regardless |
| **D. msgspec, retiring python-rapidjson** | Deferred. It is the only option that removes a codec. See [O08](#O08) for what holds it back and what would release it |
| **E. pydantic-core as the general codec** | Not feasible. No sorted keys, and decimals are not exact |

The independent assessment reached the same ranking from the evidence alone.

## Opportunities

O01 to O07 need no new library. The orjson inquiry surfaced them, and they stand whether or
not a codec is ever added. O08 and O09 are the library questions, both conditional.

<a id="O01"></a>
### O01 — Declare what the identity recipe accepts

**Who benefits:** anyone changing a hashed value, and any later codec decision.

D1 §10.1 says `canonical_json` is one function with no floats. The semantic identities use
`canonical_bytes` instead, which accepts whatever stdlib `dumps` accepts: floats spelled as
CPython's `repr`, integer and boolean keys turned into strings, tuples, and strings that are
not NFC-normalized. Raw floats can reach it through `model_dump(mode="json")` of models with
float fields. The tagged value codec avoids this by writing floats as hex and integers as
strings, and other modules flatten subclasses defensively, so the hazard is known locally but
not stated at the owner.

The SQL counterpart makes this more than tidiness. `data.canonical_json` takes scalar text from
JSONB, which normalizes numbers (`1e2` becomes `100`, `-0.0` becomes `0.0`). A float inside a
value hashed on both sides can already disagree between Python and PostgreSQL.

**Proposed change.** State the accepted domain at `canonical_bytes` and enforce it with an
exact-type walk like the existing `own_json_value`: string keys only, finite values only, no
unknown types. Then decide floats explicitly. Either refuse them in hashed uses, so callers
use the tagged form, or declare the `repr` spelling as the contract.

**Prerequisites.** Find out whether hashed values contain floats today, by running the
identity tests with a temporary refusal. Refusing floats that are present moves digests and
needs an ADR. Declaring the current spelling moves nothing.

**What it removes.** An identity rule that depends on which encoder happens to be in use
(DP-04, DP-11). It also turns any later codec swap into a bounded question.

<a id="O02"></a>
### O02 — Give each use of canonical bytes its own owner

**Who benefits:** developers reading or changing the roughly 940 `canonical_bytes` call sites.

One function serves four purposes: identity, size measurement, input to `validate_json`
(about 60 sites), and `json.loads(canonical_bytes(x))` used to normalize a value (about 20
sites). Only identity needs sorted canonical bytes. A reader cannot tell which calls are
contractual, and every call pays for sorting.

**Proposed change.** Keep `canonical_bytes` for identity. Normalize with
`pydantic_core.to_jsonable_python` or `own_json_value` and skip the encode and decode. Where a
value is serialized only to be validated, use the boundary's existing `validate_accepted_python`
entry point if JSON-mode coercion is not needed at that site.

**Risk.** Strict JSON-mode validation and Python-mode validation differ for some types, and
Decimal tagging differs per site. Each group of sites needs checking before it moves.

<a id="O03"></a>
### O03 — Measure response size once, with the serializer that delivers it

**Who benefits:** agents and operators calling the MCP and serving reads.

About 12 serving sites compare `len(canonical_bytes(response.model_dump(mode="json")))` with a
client byte limit, and two use `json_bytes` instead, so the limit is measured with a recipe
that differs from what is sent. Several shrink a result in a loop and re-encode the whole
response each step ([`graph_inspection.py`](../../python/corpus-structure/src/corpus_structure/semantic/graph_inspection.py),
[`diagnostic_selection.py`](../../python/corpus-structure/src/corpus_structure/semantic/diagnostic_selection.py),
[`change_impact.py`](../../python/corpus-structure/src/corpus_structure/semantic/change_impact.py)).
The observation journal's page loop in
[`observations.py`](../../python/corpus-structure/src/corpus_structure/cli/observations.py)
re-encodes every accumulated row for each row it adds.
[`mcp_results.py`](../../python/corpus-structure/src/corpus_structure/intervene/mcp_results.py)
serializes each result once as a dict and again as text to measure it.

**Proposed change.** One size owner that measures with `model_dump_json` or
`TypeAdapter.dump_json`, the serializer the MCP SDK uses. Find a cut-off from per-item sizes
or by bisection. In the journal, keep a running total of the line lengths already read.

**Evidence.** The repeated-encoding shapes are observed in code. Their runtime cost is not
measured. Limits are bounded (the journal page at 1,000 rows), so this is a design
simplification first.

<a id="O04"></a>
### O04 — Refuse `NaN` tokens at the worker boundary

**Who benefits:** the receipt and digest checks around provider workers.

The host and worker readers pass `parse_float` to enforce finite numbers and
`object_pairs_hook` to refuse duplicate keys. Python sends the bare tokens `NaN` and
`Infinity` to `parse_constant`, which is unset, so they are accepted.
`json.loads('[NaN, Infinity]', parse_float=...)` with a refusing hook returns `[nan, inf]`
(**Tested · 2026-11-20**).

**Proposed change.** Add a refusing `parse_constant` in
[`native_host.py`](../../python/corpus-structure/src/corpus_structure/methods/native_host.py),
`native_host_worker.py` and `pm2_worker.py`. This is a small correctness fix. orjson's decoder
refuses these tokens, but it cannot refuse duplicate keys and cannot run in the worker.

<a id="O05"></a>
### O05 — Make jsonschema see the numbers the instances carry

**Who benefits:** declared-data-operation wire validation and demand-result validation.

Schemas are decoded with stdlib, so their numeric bounds are floats. Instances can hold
Decimals: `analyzed_scope` after `wire_json_loads`, and decoded semantic values validated in
[`demand_results.py`](../../python/corpus-structure/src/corpus_structure/semantic/demand_results.py).
With jsonschema's default type checker a Decimal `1.0` fails `type: integer` and a float
`minimum` can reject an equal Decimal.

**Proposed change.** Either decode schemas in the same exact-number mode as instances, or
build the validator class once with
`validators.extend(Draft7Validator, type_checker=Draft7Validator.TYPE_CHECKER.redefine("integer", ...))`.
Route the validators that are constructed per call (in `demand_results.py`,
`authority_leaf.py` and `data_operation_execution_evidence.py`) through the cached owner that
[`data_operation_wire.py`](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_wire.py)
already has.

**Evidence.** The mechanism is tested. Whether any current schema constrains a number that
arrives as a Decimal is not established; check that before treating this as a defect.

<a id="O06"></a>
### O06 — Parse each selected-source event once

**Who benefits:** the selected-source package writer and reader.

The reader parses each line with stdlib, validates the same line with pydantic, parses the
nested `data` string, and for some kinds re-encodes it to validate again. The writer encodes
each event once to validate and again to emit.

**Proposed change.** Validate the line once and take the event from the validated result.
Validate `event["data"]` directly from its text. On the write side, validate the bytes that
are emitted. The wire format and its digest do not change.

<a id="O07"></a>
### O07 — Contain the exact-decimal codec and the SQL-literal recipe

**Who benefits:** anyone replacing or auditing a codec later.

Three CLI modules import `rapidjson.JSONDecodeError` directly. About 20 `*_native.py` modules
each define a local `_json` helper for JSONB literals, in two real variants.

**Proposed change.** Have `data_operation_json.py` raise its own `ValueError` subtype, so
rapidjson is named in one module (DP-14). Merge the `_json` helpers into one owner that keeps
both spellings byte-exact; the frozen program-identity files are the acceptance check. The
second part is low value alone and fits when those modules are next changed.

<a id="O08"></a>
### O08 — Conditional: msgspec in place of python-rapidjson

**Status:** deferred, with triggers.

msgspec could take over the exact-decimal role and remove a codec. The probe supports that:
`Decoder(float_hook=Decimal)` reproduces `NM_DECIMAL` decoding, and
`Encoder(decimal_format="number", order="deterministic")` reproduces `json_bytes` on finite
values. It would add capabilities rapidjson lacks here: `Raw` capture for envelopes whose
payload is passed on unread, `encode_lines` and `decode_lines` for JSONL, and typed decoding
that keeps Decimal fields exact.

What holds it back:

- The code-identity analyzer admits rapidjson by function name and constant
  ([`external_runtime.py`](../../python/corpus-structure/src/corpus_structure/semantic/external_runtime.py),
  `python_operation_sources.py`). msgspec's modes live on configured encoder and decoder
  objects, so admitting it is new analyzer work.
- `json_bytes` digests and manifests would change for strings that contain control characters.
- Non-finite Decimals would need a check before encoding.
- msgspec is pre-1.0 and states no byte-stability promise.

**Revisit when** python-rapidjson lacks a wheel for a needed interpreter or stops being
maintained, when the project moves to free-threaded CPython, or when a typed boundary appears
where `Struct` with `Raw` would remove whole parse, map and validate passes. O07 should land
first so the replacement is local. This agrees with the existing
[domain-data-model briefing](../library_leverage/libraries/domain-data-model/briefings/executable-boundaries.md),
which holds msgspec conditional on a real transport path.

<a id="O09"></a>
### O09 — Conditional: orjson on a measured encoding path

**Status:** declined now.

Each place orjson might have been used has a specific reason against it.

| Candidate | Why not |
|---|---|
| Identity bytes | Arrangement C above |
| General decoding (JSONB adapter, JSONL readers) | Integers beyond 64 bits become floats silently; no decimal mode. Few Python values pass through the psycopg adapter anyway, because bulk writes use binary COPY or SQL casts |
| Worker frames | The worker is stdlib-only and its bytes must equal the host's. Encoding a whole frame before checking its length loses the early stop at 8 MiB |
| `Fragment` in the PDF record export | It needs one `dumps` call over the whole document, which loses the cancellation checks, bounded memory and stream hashing. The export already passes verified bytes through by hand |
| `Fragment` for selected-source `data` or the demand spool | Lifting `data` out of its string changes a hashed wire format, and readers could not recover the exact bytes without msgspec's `Raw` |
| JSONB text passed through to clients | `jsonb::text` is PostgreSQL's formatting, not canonical bytes, and D3 §6 already rules it out for digests |
| structlog `JSONRenderer(serializer=orjson.dumps)` | It works and is the documented pattern, but the journal is small and bounded and its bytes would change. O03 addresses the actual repeated work |
| MCP size measurement | It would measure with a serializer the SDK does not use |
| Native dataclass encoding in place of `asdict` | The sites feed hashed bytes |

**Revisit when** a measured encoding bottleneck appears on a path with no identity bytes and
no decimals. Adopt it there behind one owner, encode-only, with an exact pin. If O01 has
landed, the accepted value domain is already stated, which makes that adoption a small change.

## Interactions and order

O01 comes first. It settles what identity bytes mean and is the precondition for any codec
question. O02 and O03 follow from it, since separating purposes is easier once the identity
use is fenced. O04 is independent and small. O05 and O06 are local to their modules. O07
prepares O08 and has no other dependency.

Nothing here changes an active plan. If selected, O01 is a design finding that needs an ADR
before implementation, and O04 is a correctness fix that can be taken at any time.

## What would demonstrate each

- **O01:** the accepted domain is written at the owner, a refused value fails with its path,
  and the pinned identity vectors are unchanged or their change is recorded as a migration.
- **O02:** the normalization and validation sites no longer call `canonical_bytes`, with the
  existing boundary tests unchanged.
- **O03:** one size function is used by the serving reads, and a response at the limit is
  accepted or refused consistently with what the client receives.
- **O04:** a frame containing `NaN` is refused on both sides.
- **O05:** a Decimal instance and its float equivalent get the same verdict from the same
  schema.
- **O06:** the selected-source digests are unchanged and each line is parsed once.
- **O07:** `rapidjson` is imported in one module and the frozen program identities are
  unchanged.

## Limits

- The probe used synthetic values. Which value types reach each hashing site was sampled, not
  traced for all of them.
- Whether enums or floats reach particular hashed payloads is not established. O01's first
  step answers the float part.
- Whether the psycopg loader's stdlib `json.loads` already returns floats for any JSONB value
  that should be exact was not checked. If it does, that is a defect independent of this review.
- "No orjson opportunity" covers the worker, database, journal, MCP, export and identity paths
  that were read. It is not a proof over every call site.
- The Rust crates, `services/` and third-party internals were not examined.
