# Complete construction and directional archives

**Selected implementation design, 2026-11-10.** This supporting document develops
[DMC-03](../domain-data-model_2026-11-10.md#DMC-03),
[DMC-04](../domain-data-model_2026-11-10.md#DMC-04) and
[DMC-05](../domain-data-model_2026-11-10.md#DMC-05) for the domain-data-model coordinator.
The coordinator owns execution order, package state, investigation decisions and qualification.
I02 and I03 below retain the delivery contracts and selected mechanisms. The coordinator
records their decisions, package states and evidence; this companion does not duplicate status.

## Purpose, sources and existing owners

The operator/developer should reconstruct a complete retained PDF recipe or release through
one discoverable boundary, receive typed located failures, and add a nested released product
without extending unrelated orchestration traversal. Preserve exact archive bytes, semantic
identity and independently enforced publication/custody guarantees. A shorter conversion path
is valuable only when it preserves the complete directional contract.

The selected source is [O02/O03/O04](../../functional_reviews/domain-data-model/construction-and-exchange.md)
in the [integrated review](../../functional_reviews/domain-data-model_2026-11-10.md), with
[DDM-03/04/13/14](../../library_leverage/libraries/domain-data-model/briefings/executable-boundaries.md).
Current code was inspected at `8e69e2b5f6dc56bd01c3a63b27b0a7ee28d313da`, 2026-11-10,
with concurrent PTD documentation/qualification work present. Execution requires the
**completed PTD-11 handoff**, not merely an agreed design; the coordinator schedules this series
before PM2. Consume the final source and handoff rather than treating provisional PTD changes
as qualified by this plan.

[D2](../../design/D2-schema-and-guidelines.md#release-and-boundary-realization) and
[ADR-0031](../../adr/0031-semantic-execution-closure.md) own release opening/admission;
[D4](../../design/D4-method-catalog.md) owns the finite PDF recipe/producer contract;
[D1](../../design/D1-knowledge-representation.md), [D5](../../design/D5-consolidation-identity-confidence.md)
and [ADR-0065](../../adr/0065-cross-source-structural-products.md) own qualified structural
products/source closure. Archive representation changes update their current owner and ABI
route; they do not silently revise an accepted semantic identity or native profile. These
packages propose no rule impact requiring new native support.

### Source-inspected baseline, 2026-11-10

[PdfRecipe](../../../python/corpus-structure/src/corpus_structure/ingest/pdf.py) is a frozen,
slotted stdlib dataclass. `__post_init__` checks admitted recipe ids, immutable revisions,
positive capacity/deadline and unique named model artifacts/revisions. `to_bytes` uses sorted
compact JSON of `dataclasses.asdict`; `digest` hashes those bytes. `from_bytes` first parses JSON
to require exactly **all dataclass fields**, including constructor-defaulted fields, then creates
`TypeAdapter(cls)` and strictly validates the original JSON again. Imports of native Docling
option classes are inside `options()`, so reconstruction need not initialize the native producer.

[releases.py](../../../python/corpus-structure/src/corpus_structure/semantic/releases.py)
`_products` builds the release product wire, encoding `RegistryRow.body` as `body_hex`.
`_archive_bytes` canonicalizes `semantic-release-archive-3`; `_archive_wire_payload` is a
**different direction**, preparing publication rows by converting bytes/memoryview to
PostgreSQL `\\x` hex and normalizing JSON through `json.dumps(allow_nan=False)` and
`TypeAdapter(JsonValue).validate_json`. Do not confuse either wire with canonical identity bytes,
base64 review-bundle rows or raw evidence bytes.

[archive_reader.py](../../../python/corpus-structure/src/corpus_structure/semantic/archive_reader.py)
uses a strict cattrs converter for typed products and manually checks product roots, registry
row keys/hex, duplicates and artifact references. It authenticates exact archive/manifest/input/
artifact bytes, selected library/compiler compatibility and regenerated boundary schema
correspondence. It uses finalized immutable headers/store-context caching and preserves the
complete coherence path for historical unfinalized archives. Opening reconstructs recorded
products; persistence/activation/run admission retain their separate stronger verification.
[contracts.py](../../../python/corpus-structure/src/corpus_structure/semantic/contracts.py)
has a separately scoped exact-primitive converter. Its distinct responsibility is not a reason
to replace both with a mutable global converter.

[observations.py](../../../python/corpus-structure/src/corpus_structure/semantic/observations.py)
`bind_result` validates the handwritten `StructuralProductReport`, JSON-normalizes nested
`ContextualEnrichmentReport` and `SourceContribution` under its `PreparedRelease`, normalizes
comparison conditions and finally validates `SourceObservationBatch` in Python mode.
The authored [observations schema](../../../python/corpus-structure/src/corpus_structure/model/semantic/observations.yaml)
already nests StructuralProductReport, ContextualEnrichmentReport, ArtifactIdentityProduct and
SourceContribution. O04 corrects the discovery's missing-outer-schema premise. The extra
passes may bridge representations; they are not evidence that the nested schema is absent.
`StructuralProductReport.closure` additionally checks variants/source/citation closure, and
product identity deliberately excludes retrieval derivation. Those are distinct semantic rules.

## Selected realization · 2026-11-10

I02 selects a cached `TypeAdapter(actual_cls)` behind the exact archived-field guard in
`PdfRecipe.from_bytes`. The attempted high-level `BeforeValidator` receives Python lists and
loses strict JSON tuple behavior under Pydantic2.14.1, so the strict second JSON parse remains.
Ordinary constructor defaults and `__post_init__` remain authoritative; archived fields remain
complete. The operator selected the existing timeout acceptance, including NaN, positive infinity
and integer-to-float validation. Actual worker startup already receives a typed recipe; no byte
conversion caller is added there.

`semantic/archive_wire.py` owns a frozen `ArchiveProducts` wire root, `RegistryWireRow` and
artifact references with scoped generated cattrs hooks. Its `body_hex` hook yields bytes on read
and canonical lowercase hex on write. Required root fields, strict primitives, heterogeneous
versus variadic tuples and selective nullable Diagnostic omissions are explicit. The reader
wraps detailed cattrs errors as located `ArchiveDecodeError` diagnostics while retaining the
original exception cause. Authentication, finalized/unfinalized coherence, exact reconstruction,
duplicate identity/reference checks and lazy release adapters stay in their existing owners.
Publication `_archive_wire_payload` retains its JSON round trip and nonfinite refusal; archive
cleanup does not change that accepted-input contract or introduce a binary transport.

I03 selects one canonical-JSON structural-subtree bridge through the supplied release's
`property_adapter("SourceObservationBatch", "structural_product")`. It replaces retrieval-report
and artifact-contribution traversal. The handwritten StructuralProductReport validator,
comparison SourceValue semantic round trip and final outer-batch validation remain because they
establish different properties. A test-only deeper nested extension and two concurrently open
releases with different bounds challenge the replacement without adding another production schema.

## Common construction principles

Select reusable preparation at the valid authority's lifetime: recipe adapters by actual class,
release adapters by supplied immutable release, and directional archive hooks by archive ABI.
No global current-release capture. Use standard Pydantic/cattrs composition before custom
core-schema protocols. Keep ordinary constructor invariants and source semantics with their
existing owners; a conversion hook supplies representation, not a second domain model.

The worthwhile simplification follows the whole operation. Removing repeated adapter creation
or a JSON parse is useful when it removes work without adding a new wire authority. A small
explicit guard can be better than a second handwritten model. A structural-subtree conversion
can be better than serializing a whole observation batch; checking a source closure is still
necessary even when the shape already validates. These choices apply FP-01/03/04/05/07 and
heuristics H4/H12/H15/H18/H20/H28 qualitatively, without a benchmark obligation.

<a id="DMC-I02"></a>

## I02 — Settle recipe and archive fidelity before replacement

I02 is resolved by focused source inspection and only the smallest executable cases needed
to settle the following contracts. If an experiment is needed, retain it in the coordinator's
assigned dated evidence folder under repository custody, not a scratchpad. No exploratory
provider/model initialization or database creation is needed. The decision record belongs at
the coordinator's investigation owner, with links here; it must name each selected/retained
branch so one successful recipe case does not imply archive conversion equivalence.

### Recipe question and branch

Candidate: prepare `TypeAdapter(Annotated[actual_cls, BeforeValidator(require_complete)])`,
with the complete key set derived from `dataclasses.fields(actual_cls)`. The pre-validator
checks a mapping root and exact key equality, reports missing/extra keys without leaking the
whole input, and returns the input unchanged. It does not convert JSON arrays to Python tuples
itself. `validate_json(..., strict=True)` must retain the native JSON-mode dataclass/tuple
behavior and execute the actual class's constructor invariants.

Settle these questions explicitly: does the high-level before-validator retain JSON mode for
nested strict tuple fields; does the final dataclass path invoke `__post_init__`; do subclasses
derive their own field sets and receive their own adapter; and can forward/class annotations be
resolved without private namespace machinery? Include a subclass with one additional field
and an otherwise identical base payload. Reject a shared closure that captures the base class.

The selected outcome is **deliver complete reconstruction with prepared actual-class adapter**.
Use the composed single-parse candidate only if those contracts hold. Otherwise retain the
short exact-presence JSON guard and reuse a class-keyed `TypeAdapter(cls)` for the strict
second parse. That conforming fallback completes the bounded capability; document why one
extra parse is retained. No duplicate recipe-wire class or general caching framework is
selected. A direct constructor still has defaults; an archive still requires them explicitly.

### Archive root and hook questions

Prepare one typed directional archive-product root matching the existing archive-3 product
keys, with typed registry-row wire and artifact-digest entries. Reuse the existing semantic
dataclasses for definitions/vocabularies/queries/diagnostics; do not duplicate their fields in a
parallel domain model. A small wire-only type may own `body_hex` and decode into RegistryRow,
or a scoped generated override may map `body` to `body_hex`. Select the clearer complete
direction in I02. Typed root completeness remains distinct from cross-row duplicate/digest
and archive authenticity checks.

Settle whether cattrs generated hooks with explicit field overrides preserve exact primitive
types, omitted optional historical `execution_model_id`, current diagnostic omission and
registry byte encoding. Verify hooks are registered before nested/root functions capture them.
Missing required product fields and unexpected root/row keys must retain rejection, while
declared historical defaults remain accepted exactly where they were before. Unknown wire
version/ABI refuses; the reader must not infer a new version from whichever fields happen to
be supplied. Confirm how detailed cattrs exceptions become public located paths such as
`products.registry_rows[2].body_hex`, retaining the underlying cause.

The selected outcome is **deliver typed reconstruction** through the existing reader.
Generated mapping is preferred if it removes maintained conversion decisions coherently.
Retain small explicit directional mapping where an override would obscure the wire or weaken
error precision. If the typed root proves to require a second editable semantic model, narrow
it to product-root/wire-only contracts and retain direct typed leaf reconstruction. Do not let
that failure become a reason to skip the useful explicit root/row contract.

### Publication conversion is an independent conditional decision

Inventory the actual values supplied to `_archive_wire_payload` and the native publication
entry point, including tuples, nested mappings, bytes/memoryview, integer/bool/float keys where
actually permitted, nonfinite floats and unsupported objects. Current `json.dumps` semantics
normalize tuples and keys, and reject unsupported/nonfinite values. A replacement must preserve
the accepted input contract and collision/refusal behavior, not merely produce valid JSON for
today's happy-path fixture. JSON key coercion can collapse distinct Python keys: do not silently
change that behavior under a cleanup claim; expose any warranted contract change to its owner.

A generic Pydantic dump is not selected by default: serialization policy may replace NaN with
null. Establish an explicit complete policy before adopting it. If no clearer total route
preserves exact semantics for actual supported inputs, **retain the existing JSON round trip**
and its `allow_nan=False` contract. That justified retain is a completed I02 outcome, not an
unimplemented production feature. msgspec/attrs/MessagePack/zero-copy transport remain optional
only for a named whole-boundary consumer; no new dependency or binary protocol follows from
archive cleanup alone.

<a id="DMC-03"></a>

## DMC-03 — Complete PDF recipe reconstruction boundary

**Consumes:** I02's recipe outcome and actual final PdfRecipe definition. **Produces:** a
reusable complete archive reconstruction operation usable by worker startup and retained-recipe
inspection, with typed located failures and unchanged canonical recipe bytes/digests.

Keep `PdfRecipe.from_bytes` the authoritative entry point; prepare by actual class within that
owner, not each call. Migrate actual worker/stdio, resume and preflight readers that reconstruct
this recipe to the same boundary, removing any superseded ad hoc JSON-to-constructor path.
Do not change `options()`' finite native variants or load assets during inspection. An optional
operator digest/preflight presentation may consume the resulting recipe, but is not a second
validation route. Preserve original constructor exceptions as useful located reconstruction
causes; report malformed JSON/root, complete-field mismatch and typed/invariant error distinctly
where the existing error interface permits it.

Acceptance uses independently specified bytes/expected fields, not a serializer round-trip as
the sole oracle. Cover missing default-valued field, extra field, nonmapping root, nested
array-to-tuple reconstruction, string-versus-integer strictness, zero capacity/invalid revision,
duplicate model artifact/repository, nullable timeout and subclass isolation. A known valid
recipe has unchanged `to_bytes` and digest; the initial payload may differ in harmless JSON
whitespace while reconstruction still uses the established canonical identity. A successful
`from_bytes` must not import Docling option/model modules or invoke model initialization.

At this baseline, a source-wide search for `PdfRecipe.from_bytes` finds no direct production
caller outside its owner; `ingest/pdf_worker.py` receives an already typed recipe through spawn,
and `ingest/pdf_methods.py` builds one from runtime configuration. Preserve those typed routes.
Retained `recipe_bytes` in `orchestrate/pdf_streaming.py`, `semantic/pdf_contracts.py` and
`ingest/pdf_methods.py` include wrapper/adoption representations as well as native recipe bytes;
only exact PdfRecipe payloads belong at this boundary. Confirm that inventory at execution and
migrate any actual same-contract readers found. Do not invent a worker/stdio byte conversion
just to create a caller. [PDF worker controls](../../../python/corpus-structure/tests/ingest/test_pdf_worker_stdio.py)
and streaming consumers can verify preserved recipe identity. This package delivers the reusable
retained reconstruction API without claiming every archive-bearing recipe is a PdfRecipe wire
or promising historical recipe fields omitted from the admitted wire.

<a id="DMC-04"></a>

## DMC-04 — Typed directional release archive reconstruction

**Consumes:** I02's archive and publication outcomes; unchanged recorded archive bytes and
supported compiler/library ABI rules. **Produces:** explicit typed root/row reconstruction,
prepared scoped conversion and useful located failures through existing open/reconstruct APIs.

The complete read flow remains:

```text
caller-owned reader snapshot → observe immutable header → acquire recorded bytes
 → authenticate archive/manifest/input/artifact identities → typed archive/product reconstruction
 → reconstruct recorded boundary recipe and verify supported schema correspondence
 → preserve row coherence/finalization checks → PreparedRelease
```

Reorder only when the checks' premises still hold. In particular, typed decoding cannot replace
independent digest checks; a successfully reconstructed object does not establish native
admission. Keep open-cache keys/lifetime, finalization requirements and conservative tuple-marker
invalidation unless a separately justified defect requires change. Preserve reconstruction's
demand-built adapters; a root decoder should not eagerly build every class boundary.

Add scoped structure/unstructure hooks for archive direction, using generated functions only
after exact primitive and wire hooks are fixed. For `body_hex`, preserve the exact accepted
hex contract (case/whitespace behavior included if it matters to retained fixtures) and canonical
lowercase writer output; do not tighten a historical accepted reader accidentally. Validate
duplicate registry `(kind,name)` rows, duplicate/missing artifacts and digest references in the
owning closure function. Generated shape checks do not discharge those collection relations.
Round-trip back through `_archive_bytes` must still match the exact stored archive; do not
canonicalize malformed input into a different accepted archive.

Migrate `_products` and `reconstruct_release` to one discoverable directional field mapping
where it genuinely replaces both maintained directions. Keep publication bytea conversion a
separate function even if a small exact-primitive factory is shared. Do not mutate the converter
in `contracts.py` or make custody domains share a configurable singleton. Remove manual root/
row key assembly and checks only when replaced by the selected typed contract; retain independent
authenticity, duplicate, ABI and schema checks and useful deliberate corruption fixtures.

DMC-01's inspection product travels through ordinary `PreparedArtifact` descriptors/bytes.
Old supported archives have no such product; preserve them without fabricated detail. Current
root optionality and compiler readers remain explicit. A new wire version is warranted only
for an actual incompatible wire change, with the existing ABI/ADR route and retained-reader
fixtures. Cleaner internal Python types alone do not justify rewriting stored archives,
database migration or current-compiler rederivation.

Acceptance covers malformed/missing/extra product and row fields, wrong primitive types
(including bool-versus-int), malformed hex, duplicate registry keys/artifacts, digest mismatch,
missing inputs, unsupported archive/compiler/library/boundary versions and optional historical
fields. Test independent expected failures and locations using
[archive reader controls](../../../python/corpus-structure/tests/semantic/test_archive_reader.py)
and [archive faults](../../../python/corpus-structure/tests/semantic/archive_faults.py).
Keep a known archived fixture opening with current compiler preparation deliberately unavailable;
exercise altered artifact/schema bytes and finalized/unfinalized coherence paths. If publication
conversion changes, exercise its actual native publication caller and independent tuple/key/
bytea/nonfinite cases. A mocked database/provider is not native `passed` evidence.

<a id="DMC-I03"></a>
<a id="DMC-05"></a>

## I03 and DMC-05 — Select nested normalization that preserves composition

I03 asks what **representation mismatch** the targeted passes in `bind_result` solve, and
whether a prepared structural-subtree operation can own that conversion without duplicating
semantic checks. Inspect the actual generated outer/inner schemas and Python/JSON accepted
representations before changing the code. Use existing ContextualEnrichmentReport and
SourceContribution plus one changed/new nested-product fixture whose introduction otherwise
requires a new consumer traversal branch. A test-only representative product can settle the
extension question without adding unsupported production semantics.

Trace the input/output exactly: native method structural report → handwritten closure/variant
validation → release-specific normalization of only its declared subtree → outer
SourceObservationBatch structural validation → existing publication. Distinguish which stage
turns lists into tuples, reconstructs temporal/decimal values, carries null/absence, or changes
comparison condition scalars. Determine which stages enforce separate source/citation/variant
rules. Keep `source_value`/`source_python`, tagged source scalars, canonical hexadecimal floats,
field positions and identity encoding with their current semantic owners.

Preferred candidate: a prepared subtree adapter, or high-level Pydantic validation composition
explicitly supplied the `PreparedRelease`, using existing `property_adapter`/class adapters
as appropriate. Its input is a named subtree and its declared incoming representation; its
output is strict Python values valid for the enclosing release boundary, with nested located
errors. Cache preparation only inside that immutable release's lifetime/lock. Inspect whether
`model_dump(mode="json")` on **that subtree** followed by the release JSON adapter is the
smallest complete bridge; do not serialize the entire batch merely to normalize one field.
Do not assume property adapters retain enclosing conditional context automatically.

I03 selects one of two completed outcomes:

1. **Deliver DMC-05:** the composed subtree operation removes consumer-specific nesting
   traversal for the selected extension and preserves strict Python/JSON behavior and source
   semantics. Migrate affected `bind_result` and other actual same-contract consumers; remove
   superseded targeted normalization loops and their mechanism-only tests. Keep independent
   outer validation and handwritten closure rules wherever they establish distinct properties.
2. **Justified retain:** targeted normalization remains the clearest complete route because
   proposed composition adds context plumbing, whole-batch encoding or duplicated decisions
   without simplifying the concrete extension. Retain existing loops, state which representation
   gaps each handles and the next trigger for reconsideration. Do not claim missing nested
   schema functionality or require custom core-schema machinery to force a replacement.

Acceptance for a selected replacement uses independent known-good/known-invalid nested
examples under two simultaneously open releases with different constraints. Cover deep error
paths, omitted/null/empty values, source/citation closure, selected variants, exact source scalar
and comparison-condition round trips, identity unchanged by retrieval derivation and rejection
when original-source release context differs. Useful controls include
[observations](../../../python/corpus-structure/tests/semantic/test_observations.py),
[structural products](../../../python/corpus-structure/tests/semantic/test_structural_products.py)
and [typed structural composition](../../../python/corpus-structure/tests/semantic/test_typed_structural_composition.py).
Outer schema validation agreeing with itself is insufficient to establish the handwritten
closure or identity semantics. I03 can settle by source/fixtures; no performance experiment is
required merely to show fewer explicit loops.

## Library contracts and release relevance

**Pydantic2.14.1/core2.50.1** remains selected, not the newer overview addendum's default.
The [TypeAdapter account](../../libraries/data_model/pydantic.md#22-typeadapter-validation-without-a-model-class),
[validator composition](../../libraries/data_model/pydantic.md#51-validator-execution-modes)
and [dataclass lifecycle discussion](../../libraries/data_model/pydantic.md#92-dataclass-lifecycle-and-schema-rebuilding)
orient I02/I03. Installed sources read on 2026-11-10 are
`.venv/lib/python3.14/site-packages/pydantic/type_adapter.py` (`TypeAdapter`, line69;
`validate_json`/`validate_python`), and `pydantic/functional_validators.py`
(`BeforeValidator`, line91). `BeforeValidator` wraps inner validation with a before function;
it does not itself establish recipe JSON-mode equivalence. Types owning their configuration
(dataclasses included) cannot generally be overridden through TypeAdapter's `config` argument.
Avoid private schema/namespace hooks unless the high-level routes demonstrably cannot meet
the bounded selected responsibility; route such a consequential choice back to the coordinator.

**cattrs26.2.1** supplies selected archive composition. The
[cattrs overview §4](../../libraries/data_model/msgspec_attrs_and_cattrs.md#4-cattrs--extensible-objectdata-conversion)
explains generated hooks, overrides, exactness gaps and hook-registration order. Installed
`.venv/lib/python3.14/site-packages/cattrs/gen/__init__.py`
(`make_dict_unstructure_fn`, line254; `make_dict_structure_fn`, line755) documents dataclass/
attrs generation, `AttributeOverride`, default omission, extra-key refusal and detailed
validation. Generated hooks capture nested dispatch; primitive/hex hooks precede root/collection
generation. Keep `forbid_extra_keys=True`, detailed errors and exact primitive hooks, because
the default converter's coercions do not meet this archive boundary. Use `override(rename=...)`
or scoped field hooks for directional names/hex only where I02 establishes the complete mapping.

msgspec typed codecs/Struct/tagged unions/Raw/convert and attrs lifecycle are investigated only
when a named transport/object consumer would retire a whole maintained boundary. The
[same overview](../../libraries/data_model/msgspec_attrs_and_cattrs.md) describes them, but
msgspec is uninstalled at the review baseline and direct decoding does not automatically run
all attrs converters. No substrate migration, binary protocol, lazy admission or zero-copy
contract is selected. Those alternatives must satisfy the same exact presence, constructor,
precision, nested hook and custody cases before any conditional adoption.

## Other conditional construction/exchange branches

Provisional provider preview using partial JSON, lazy iterables, `FailFast`, `OnErrorOmit` or raw
buffers is a separate workflow decision under the coordinator's O04/O11 coverage. A selected
preview must retain exact raw custody and report incomplete/unvalidated status; completion
still passes the ordinary complete boundary. Omitting invalid evidence cannot silently produce
an admitted result. Without an actual preview consumer, retain current complete inputs and
record a justified defer and revisit trigger.

Named spreadsheet/Map/YARRRML/conversion/flattening integrations likewise require an actual
source-to-target exchange, field-presence/multiplicity/precision/source-lineage contract and
consumer acceptance. Retain existing intake until those conditions are met. A library's ability
to decode a representation is not selection of that transport. Cross-language/offline schema
consumers are owned by O11; these construction packages supply faithful directional products
without taking ownership of a generic transformation platform.

## Completion and execution fit

**Proposed benefit:** prepared actual-class recipe reconstruction removes repeated adapter
setup; typed archive roots make malformed fields and future product additions discoverable;
a selected nested boundary localizes release-specific normalization. Preserve the simpler
retained route whenever a replacement shifts more machinery into hooks, caches or wrappers
than it removes. Recipe opening is a small local operation; preparation may be module-local
and lazy. Archive reconstruction should prepare hooks once per supported directional contract
and retain demand-built release adapters. Nested normalization should touch the required
subtree and reuse the release; it must not parse the closure per record or materialize an
entire batch JSON copy. These are qualitative expected improvements, not speed measurements.

Reconstruction is read-only and repeatable from exact retained bytes; no new migration,
resumability protocol or database is needed for the selected internal replacement. A failed
decode exposes its location and leaves existing archive/native state untouched. Publication
retains its atomic guards and immutable custody. Historical wire obligations are addressed
through retained readers/fixtures, not a compatibility adapter for every internal helper.

During execution run scoped recipe, archive and observation functional controls through
`uv run ci test -- PATH` at coherent package endpoints. The coordinator accounts for complete
required-union `uv run ci test`/`uv run ci check` after functional scope, plus applicable native
publication tests if that direction changes. Root `just turn-end` precedes final-source
qualification and `uv run ci docs check` checks publication. Verification for this document-only
assignment is **not_run**; source inspection establishes the described baseline only.
