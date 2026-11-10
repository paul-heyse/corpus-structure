# Complete construction and directional archive contracts

**Proposed functional judgments, 2026-11-10.** [Shared baseline](../domain-data-model_2026-11-10.md).
Source: discovery [executable boundaries](../../library_leverage/libraries/domain-data-model/briefings/executable-boundaries.md).

<a id="O02"></a>

## O02 — Reusable complete PDF recipe reconstruction

**Recommend a bounded construction improvement.** A developer/worker opening a retained recipe
should receive typed, located reconstruction failure without initializing Docling or model assets.
An operator preflight showing the exact recipe/digest is a useful optional consumer if selected.
The recipe's frozen dataclass remains its authority.

[ingest/pdf.py](../../../python/corpus-structure/src/corpus_structure/ingest/pdf.py) defines
constructor invariants, complete archived presence and canonical bytes. `from_bytes` parses
JSON to compare every dataclass field, then constructs TypeAdapter and parses again. Defaulted
constructor fields are nevertheless explicitly required in the archive. Removing the presence
check on the basis of ordinary default handling would change its contract.

**Preferred candidate and alternatives.** Investigate a class-specific prepared
`TypeAdapter(Annotated[cls, BeforeValidator(...)])` whose presence validator derives keys from
`dataclasses.fields(cls)`. Retain strict JSON reconstruction and `__post_init__`. This is a
candidate mechanism, not a compatibility result; subclasses must prepare by actual class.
Caching the existing adapter while retaining the short presence guard is the smaller conforming
fallback if composition complicates JSON behavior. A separately handwritten wire model duplicates
field authority unless a real new wire version requires it. Moving the recipe wholesale into
LinkML/attrs provides insufficient value from this seam alone.

**Delivery.** Missing default-valued archive fields and extra fields refuse; arrays reconstruct
tuple fields; invalid immutable revisions and repeated artifact names refuse; valid bytes retain
the same `to_bytes` and digest; subclass boundaries do not cross-capture. Pydantic dataclasses
own configuration and do not accept arbitrary overriding adapter config. No generic cache framework
or benchmark is required. A changed identity needs explicit recipe-version treatment.

<a id="O03"></a>

## O03 — Typed directional release archive contracts

**Recommend typed archive reconstruction first; conversion replacement remains conditional.**
The developer/operator could open a retained release offline, locate malformed fields and add a
product field through one discoverable archive contract. Opening stays reconstruction of recorded
products, followed by authenticity/ABI checks; it does not become admission or recompilation.

[releases.py](../../../python/corpus-structure/src/corpus_structure/semantic/releases.py)
constructs archive products and publication rows; [archive_reader.py](../../../python/corpus-structure/src/corpus_structure/semantic/archive_reader.py)
combines strict cattrs reconstruction with manual root/registry-row checks and independently
authenticates artifacts. `contracts.py` uses a separate strict converter for its own responsibility.

**Preferred realization.** An explicitly versioned archive-wire root and prepared cattrs
`make_dict_structure_fn`/`make_dict_unstructure_fn`, field overrides and scoped hooks can pair
logical bytes with `body_hex`. Extra-key refusal, detailed errors and exact primitive hooks remain;
register hooks before composite consumers capture them. Share configuration only where rules
coincide and keep custody-specific converter instances. Semantic definitions remain their owner;
wire names and representations belong to the archive direction.

**Alternatives and boundaries.** Retain direct mapping if a typed root merely obscures a small
clear contract. Pydantic directional serializers are viable with an explicit complete policy.
msgspec typed codecs/Struct/tagged unions can serve a transport that retires whole decode/map/
validate work, but archive cleanup alone does not justify introducing it. attrs lifecycle hooks
are relevant only for a real object-construction need.

Publication `_archive_wire_payload` is a separate decision: `json.dumps(allow_nan=False)` plus
JSON validation intentionally normalizes tuples and keys and refuses unsupported/nonfinite
values. A generic Pydantic JSON dump can turn nonfinite numbers into null. Archive hex,
PostgreSQL bytea hex, raw evidence and canonical semantic identity bytes remain distinct.
Preserve their direction-specific rules or retain the current round trip.

**Delivery.** Valid archive opening needs no current compiler execution; malformed hex/root
fields/duplicate rows give useful locations; optional historical fields retain their meaning;
exact bytes and independent artifact authentication survive. Before replacing publication
conversion, independently check tuple/key/nonfinite behavior and actual supplied input types.
Existing archive ABI compatibility and ADR-0031's opening/admission separation remain binding.

<a id="O04"></a>

## O04 — Localize nested structural-product normalization

**Conditional improvement; the missing-schema premise is corrected.** The generated outer
model already nests the relevant classes: `observations.yaml` links SourceObservationBatch to
StructuralProductReport, its artifact/retrieval fields to ArtifactIdentityProduct and
ContextualEnrichmentReport, and artifact records to SourceContribution. The targeted passes in
[observations.py](../../../python/corpus-structure/src/corpus_structure/semantic/observations.py)
appear to bridge JSON-shaped dictionaries into strict Python values before outer validation.

**Functional value.** A developer adding another release-defined nested product should be able
to compose its normalization without teaching bind_result another special traversal. Investigate
a prepared structural-subtree adapter or high-level validation with an explicitly supplied
PreparedRelease. Keep preparation within that release's lifetime; two releases with different
constraints must coexist without a global current-release capture.

**Compared alternatives.** Retain the current targeted loops when they are the simplest complete
route. A bounded subtree boundary is preferable to converting an entire batch through JSON just
to normalize one field. Custom core-schema machinery or another validation framework is not
warranted. Select a composed route only if it simplifies the actual extension while preserving
Python/JSON distinctions.

Handwritten `StructuralProductReport.closure` separately enforces selected variants and exact
source/citation closure. Product identity deliberately excludes retrieval derivation. Tagged
source scalars, canonical hexadecimal floats, field positions and absent/null distinctions are
semantic encoding, not generic serialization to remove. Shape validation cannot replace these.

**Delivery and revisit.** Choose a new or changed nested product whose normalization currently
requires another consumer branch; show composition with correct nested error paths, source
closure, product identity and conditional rules. If this brings no material simplification,
retain explicit normalization. Current nested-schema presence alone is not missing functionality.

## Provisional inputs and other representations

A provisional provider-preview workflow could use partial JSON, lazy iterables, fail-fast or
typed raw buffers, but it must retain raw custody and expose incomplete/unvalidated status.
Completion still passes the ordinary complete boundary; omission cannot silently discard required
evidence. This is a separate conditional functional selection, not an alternative admission mode.

MessagePack, zero-copy views, attrs conversion/equality/lifecycle and cattrs/msgspec delegation
remain options for a selected transport or object responsibility. Delegate only when nested hooks,
constructor invariants, source precision and error semantics survive the complete route. No
binary protocol or model-library migration is recommended without that consumer.
