# Terminology, located grounding and measurement interpretation

**Implementation plan; DMC-06 mechanism selected, remaining targets Proposed, 2026-11-10.** This companion develops DMC-06–DMC-10
and investigations I01/I04/I05 for the [DMC coordinator](../domain-data-model_2026-11-10.md).
The coordinator owns execution state, source correspondence and scheduled disposition;
the package descriptions here define delivery rather than another progress ledger.
Execution starts after the completed PTD-11 handoff and before PM2. Authoring this plan
does not start production changes, acquire an ontology or select a units dependency.

This companion applies the `create-plan` skill and its focused design assessment under
core3.3, heuristics1.0 and code-intelligence1.4; it does not initiate a broad audit.
The selected inputs are the functional review's
[O05–O08](../../functional_reviews/domain-data-model/terminology-and-measurements.md),
the discovery's [DDM-05/06/11/12](../../library_leverage/libraries/domain-data-model/briefings/vocabularies-and-ontology.md)
and the coordinator's common contracts. All proposed benefits below are qualitative.

## Intended capability and current foundation

A domain developer can release one scientifically suitable terminology pack with two
independently useful controlled fields. A researcher can inspect its allowed values,
definitions, selected hierarchy and mapping provenance, then filter source-grounded
records through declared term bindings. A located phrase can receive inspectable
external-term candidates without losing its source coordinates or acquiring an identity
merely because a label matches. An operator can compare two pinned vocabulary releases
and see changes to membership and meaning alongside known consumer evidence and unknown
impact. A measurement reader can group retained values by recognized unit and quantity
kind, and inspect compatibility or unresolved reasons separately from numerical conversion.

**Source-inspected baseline, 2026-11-10:** `8e69e2b5f6dc56bd01c3a63b27b0a7ee28d313da`,
with concurrent PTD-11 documentation/test work preserved. Its completed handoff must be
reconciled before execution; this plan does not certify that work. The architecture owners
are [D1](../../design/D1-knowledge-representation.md),
[D2](../../design/D2-schema-and-guidelines.md),
[D3](../../design/D3-database.md),
[D5](../../design/D5-consolidation-identity-confidence.md) and
[D8](../../design/D8-agent-and-query-interfaces.md).
[ADR-0024](../../adr/0024-semantic-release-preparation.md) retains scoped external-term
authority, immutable prepared releases, source occurrence/fact separation and PostgreSQL
custody. [ADR-0031](../../adr/0031-semantic-execution-closure.md) governs immutable product
opening and enforcement admission. The producing compiler and readable versions are those
in `semantic/types.py` at execution time, rather than a compiler number copied from older
architecture prose.

The actual foundation is useful but incomplete for these consumers:

| Existing owner | Source-inspected behavior and consequence |
| --- | --- |
| [ontology.py](../../../python/corpus-structure/src/corpus_structure/semantic/ontology.py), `expand_enum`, `resolve_vocabularies_from_bytes` | Explicit local ontology bytes, composed enumeration and final subtraction already exist. `_local_path` accepts OBO artifacts only and refuses `import:` declarations. Supplied bytes are materialized in an operation-owned temporary directory. Selecting STATO or any other source does not establish compatibility with that profile. |
| [types.py](../../../python/corpus-structure/src/corpus_structure/semantic/types.py), `VocabularyMember`, `VocabularySnapshot` | The archived member carries value, meaning and label, with snapshot dependency/check information. It cannot supply definitions, qualified mappings or hierarchy by itself. Preserve this archived wire contract; add an explicit richer immutable prepared artifact. |
| [prepare.py](../../../python/corpus-structure/src/corpus_structure/semantic/prepare.py) | Finite admitted constructs and deterministic artifacts are authoritative. Slot bindings/units, permissible-value inheritance and richer relationship roles are not automatically supported. Do not remove their rejections merely to import a library schema. |
| `ontology.py`, `_meaning_checks`, `validate_bindings` | Meaning checks expose unchecked dependencies; nested binding validation is a diagnostic helper, not native publication enforcement. Prefix ownership and adapter preparation currently repeat across enums. |
| [contextual_links.py](../../../python/corpus-structure/src/corpus_structure/semantic/contextual_links.py), [contextual_retrieval.py](../../../python/corpus-structure/src/corpus_structure/semantic/contextual_retrieval.py) | Frozen candidates, source witnesses, assessments and scoped selection already separate proposal from supported relationship. Existing contextual `denotes` is a source-context relationship; it is not an SSSOM exact/close/broad/narrow mapping predicate. Extend the actual supported term-review path rather than relabelling its relation types. |
| [operation_reporting.py](../../../python/corpus-structure/src/corpus_structure/semantic/operation_reporting.py), `compare_semantic_releases`; [CLI schema.py](../../../python/corpus-structure/src/corpus_structure/cli/schema.py), `diff_` | Existing release comparison and `ci schema diff` retain both-side dependencies and unknown coverage. Add vocabulary-specific changes here and to the existing model-change consumer, rather than a second impact register. |
| [core.yaml](../../../python/corpus-structure/src/corpus_structure/model/semantic/core.yaml), `QuantityValue`; [statistics semantic.yaml](../../../domains/statistics/semantic.yaml), `MeasurementRecordFields` | Decimal value, reported unit/basis and source measurement fields already exist. Preserve referent/property/original value/value role/uncertainty/reference quantity and transformed-value provenance. |
| [structural_parsing.py](../../../python/corpus-structure/src/corpus_structure/semantic/structural_parsing.py), `parse_comparison_literal`; [methods/structural_products.py](../../../python/corpus-structure/src/corpus_structure/methods/structural_products.py) | The parser's `quantity` is a source `SYMBOL`. Comparisons withhold stronger threshold consequences for missing or unequal quantity/unit/basis. A symbol is not an externally recognized physical quantity kind; preserve both meanings and current refusals unless an explicitly qualified operation replaces them. |

The Valuesets prediction-outcome fixture in
[test_prepare.py](../../../python/corpus-structure/tests/semantic/test_prepare.py)
demonstrates selective import, not a scientifically suitable terminology pack or rich metadata
delivery. A scoped inspection of these owners establishes the baseline above; it does not claim
that every repository consumer or potential ontology backend has been assessed.

## Shared semantic and artifact contracts

[DMC-01's early inspection slice](../domain-data-model_2026-11-10.md#DMC-01)
supplies **module + logical declaration path + source hash**
and effective declaration identity. Exact source lines are optional, never fabricated. DMC-06
can consume that slice before the rest of model-authoring delivery is complete. DMC-07–10
retain these references beside release/product identities so source and effective meaning can
be inspected consistently.

The richer terminology artifact is a derived, versioned prepared product under the release
manifest and existing archive custody. Its exact filename is an implementation detail. Its
contract must retain:

- Declared field/enum identity, local member value and meaning identifier; original source
  wording stays on the located record rather than being overwritten by the vocabulary label.
- Selected source revision, exact source bytes/digests, selected definition/import closure,
  prefix ownership and preparation/profile identity. If a source was explicitly converted,
  retain original and converted bytes, converter/version/options and the qualified fidelity limit.
- Label, definition, synonyms with their kinds where supplied, selected broader/narrower
  relationships with predicate/direction and coverage, and mappings with exact original
  predicates, endpoints and available provenance. Preserve missing metadata and unassessed
  relations explicitly; a dbxref does not become an exact match.
- Membership and meaning checks separately, including unchecked dependencies, source mismatch,
  obsoletion/replacement information when provided and source references from the shared locator.
  Absent, unavailable, unsupported and unchecked are distinguishable wherever consumers act on them.

This product supplements `VocabularySnapshot`; it does not introduce another editable term
registry. Its membership projection must agree with the existing complete-union-minus result.
All promised inspection data reopen from archived products with no current endpoint, package
schema or ontology adapter. Existing archives without this product expose its explicit
unavailability while retaining their original membership/read semantics. They are not silently
enriched from today's vocabulary or required to support the new inspection operation.

Metadata display is descriptive. Controlled-field membership is governed by the field's
released declaration, and any selected interpretation/effect must be declared in the model,
strict generated boundary and native custody/admission together. Default native support stays
unchanged. Required unsupported enforcement refuses; descriptive hierarchy or unit annotations
cannot quietly become validation, inference, entailment or a publication capability.

## Consequential mechanisms and retained alternatives

### Closed acquisition and useful operation-scoped preparation

Use the selected LinkML/runtime **1.12.1** source definitions and contextual `SchemaView`
induction under an explicit merged import closure. DMC-06 should reuse the same effective
declaration route as DMC-01. The applicable contracts are
[SchemaView](https://linkml.io/linkml/developers/schemaview.html) and the
[runtime v1.12.1 source](https://github.com/linkml/linkml-runtime/blob/v1.12.1/linkml_runtime/utils/schemaview.py);
source inspection and [D2's preparation owner](../../design/D2-schema-and-guidelines.md#semantic-release-preparation-entry-point)
establish the repository's closed acquisition responsibilities.

For selected OBO sources, OAK **0.7.4** can share one
`ProntoImplementation(wrapped_ontology=pronto.Ontology(BytesIO(data), import_depth=0))`
per source within one preparation operation. Reuse prefix ownership, labels and selected
traversal across the two enums and checks; retain explicit prefix-map setup because the
constructor's supplied-ontology path bypasses parser initialization. OAK's
[tagged Pronto source](https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/implementations/pronto/pronto_implementation.py)
supports `wrapped_ontology` and resource `import_depth`; the
[dated local assessment](../../library_leverage/libraries/oaklib/README.md#oaklib-in-memory-pronto-adapter)
records the complete in-memory construction and import-depth limit. No mutable adapter survives
the owning operation; archived ordinary readers need no adapter.

Term Validator **0.4.5** remains a supported leaf mechanism via `DynamicEnumPlugin.expand_enum`.
Its ordering does not discharge the application's final subtraction across inherited/static
members. A public adapter-injection contract is not established; do not mutate `_adapter_cache`.
Retain the supported temporary-file bridge for those leaves, even when OAK metadata preparation
is shared. See the [validator documentation](https://linkml.io/linkml-term-validator/validation-types/),
the [0.4.5 source-inspected ordering account](../../library_leverage/libraries/oaklib/README.md#linkml-term-validator-enum-expansion)
and [current repository composition](../../../python/corpus-structure/src/corpus_structure/semantic/ontology.py).
Removing all repeated preparation is not a reason to write a second enum interpreter.

I01's source/field slice selects STATO v2026-04-20, commit
`a5910e6115217a88ee86e2666e12983ef2ef2a42`. Explicit acquisition retains the original OWL,
qualified OBO membership projection and `source.json` conversion profile under
`domains/statistics/terminology/sources`. The original OWL digest is
`7e8f945ee30c6b24139f0064d57c2edbcfc988f3f74811cad6b5c84819ce1494`; qualified OBO digest is
`2e4438fb7246e7dc53a90fa04d79eda423b4906910c101608614e4289d9c6581`.
Pronto2.7.4 converts; Fastobo0.14.2 orders the OBO AST deterministically across processes and
reparses it to compare semantic clause sets. Original RDF independently supplies all nine selected
labels, full definitions and asserted named parents for conversion qualification. Imports refuse.
Coverage is this selected metadata/membership profile, not complete OWL equivalence. Conversion
warnings retain stable content while removing incidental XML element memory addresses. ADR-0076
and D2 own this source/projection distinction.

`domains/statistics/terminology.yaml` is a local declaration module imported by the statistics
pack. Its `StatisticalTerminologyFields` offers independent optional `distribution_family`
(hypergeometric, normal, binomial, poisson, gamma, exponential) and `distribution_attribute`
(expected_value, variance, standard_deviation). Meanings identify distribution families and
moments, with no distribution parameterization, sample-estimator or global-identity implication.
They remain separate from MeasurementValueRoleName. The existing explicit-release explorer is
the first real consumer: inspect variance's definition and source declaration, and validate the
controlled value while refusing `sample_variance`. Populated source bindings/filtering, located
term review and the quantity/unit consumer remain the DMC-07/08/10 contracts; this foundation does
not pretend those populations are already bound. I01's measurement slice remains open.

One operation-owned `OntologyPreparation` reuses wrapped Pronto OAK adapters, prefix ownership
and metadata/traversal preparation per captured source; its immutable source map must match the
operation. Public Term Validator leaves keep their supported temporary-file route. Multi-pack
acquisition coalesces the shared terminology namespace and source mapping, refusing conflicting
bytes rather than silently choosing one pack's declarations. No arbitrary remote selector or
aggregate Valuesets schema becomes an ambient preparation input.

### Immutable metadata realization

Compiler21 emits `vocabularies/metadata.json` version1 and inspection locator version2. The
vocabulary artifact preserves member value/meaning, labels, full definitions, synonym scope,
original relationship/mapping predicates, annotations, obsoletion/replacements, source/profile
hashes and separate membership/check/coverage facts. A dbxref remains a dbxref; unavailable
synonym scope remains unclassified. Enum/PV declaration locators preserve module, logical path,
source hash and known contributors; they do not invent a unique inherited winner.

`PreparedRelease.vocabulary_metadata` decodes authenticated retained bytes once per prepared
release. It corroborates enum/member universes, snapshots, unchecked status and definition/source
hashes without opening current files or OAK. Compiler21 missing metadata is corrupt; an older
supported archive reports unavailable new detail. Inspection artifact version1 keeps existing
class detail and honestly reports unavailable enum locators. Existing ContractInspection v1
entries carry the richer metadata through `metadata_json`, keeping its published wire contract.
Archive3, execution28 and boundary12 are unchanged. Exact native compiler guards and the descriptor
advance together through a frozen model-change candidate; that does not activate the release or
select a retained run.

### Rich source metadata and lookup

Valuesets **0.4.2** `RichEnum.get_meaning/get_metadata/get_annotations/from_meaning` can supply
convenient generated projections. Its
[rich enum source](https://github.com/linkml/valuesets/blob/v0.4.2/src/valuesets/generators/rich_enum.py)
shows lookup returns one matching member or `None`; do not use it to discard multiple local
bindings to one meaning. Its
[modular generator](https://github.com/linkml/valuesets/blob/v0.4.2/src/valuesets/generators/modular_rich_generator.py)
omits hierarchy and selected mappings. The authoritative source selection and new prepared
artifact therefore retain those semantics directly. Generated enums are optional consumer
convenience, not the metadata archive. Keep local absence/confidence/lifecycle categories when
external definitions do not mean the same thing.

For OAK **0.7.4**, `label`, `entity_alias_map`, declared relationship traversal and selected
`sssom_mappings` can acquire labels, aliases, neighborhoods and qualified mappings. Read the
[mapping interface](https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/interfaces/mapping_provider_interface.py)
and [Pronto mapping implementation](https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/implementations/pronto/pronto_implementation.py)
for the selected backend: Pronto also emits dbxref mappings and may scan entities for inverse
uses. Preserve predicate fidelity, prepare reusable selected mappings once, and report unavailable
metadata rather than treating a common interface as complete adapter coverage.

I04 selects a deterministic lookup over released labels/synonyms as the preferred first
grounding backend. Compare native `basic_search(SearchConfiguration)`, `lexmatch` or
`annotate_text` only where they improve the actual task. Installed OAK0.7.4 Pronto search has
a truthy label-field condition and its inspected branches do not honor case-insensitive
selection as a general guarantee. The naive annotation path uses the first `text_lower.index`
occurrence, offsets needing adaptation and no active trailing-word guard. The
[tagged search source](https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/implementations/pronto/pronto_implementation.py)
and [annotation interface](https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/interfaces/text_annotator_interface.py)
are the decisive limits. Explicit located input avoids dependence on that extraction behavior.
Automatic whole-document mention production and an upstream OAK repair are outside this plan.

The selected lookup has a versioned normalization, field inclusion, ranking/tie and candidate
coverage contract. A release-owned lookup is built/opened once per valid bounded reader lifetime,
keyed by its exact artifact and lookup policy. Exact/normalized term access should reach an
appropriate index rather than scanning the ontology per located phrase. A local in-memory
index is the default for one selected snapshot; use existing relational access if retained
record filtering needs it. Do not add a service, durable generic cache or an index framework.
Broader neighborhoods are requested explicitly with predicate/direction and partial coverage;
they are not pre-expanded all-pairs paths. Similarity, embedding retrieval and remote endpoints
remain alternatives requiring a concrete consumer and separately declared semantics.

### Vocabulary comparison and measurement boundaries

Exact comparison of the two release-owned membership/metadata products is the authoritative
account of changed admitted meaning. OAK **0.7.4** `DifferInterface.diff/grouped_diff/diff_summary`,
obsoletion relations and supported `UsagesInterface.usages` are optional explanatory sources;
I01/DMC-09 must qualify actual adapter support before exposing their output as available.
See the [differ interface](https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/interfaces/differ_interface.py)
and [usage interface](https://github.com/INCATools/ontology-access-kit/blob/v0.7.4/src/oaklib/interfaces/usages_interface.py).
Ontology usage and repository/corpus use are separate populations. The existing release comparison,
model-change preview and manual review/activation custody remain the route; no KGCL patch,
`migrate_curies`, `save` or current ontology state rewrites an earlier release.

LinkML **1.12.1** `UnitOfMeasure` metadata and Valuesets **0.4.2**
[measurement units](https://github.com/linkml/valuesets/blob/v0.4.2/src/valuesets/schema/units/measurements.yaml)
and [quantity kinds](https://github.com/linkml/valuesets/blob/v0.4.2/src/valuesets/schema/units/quantity_kinds.yaml)
are candidates for recognized identity, not executable conversion contracts. The selected source
subset must retain distinct unit identifiers, physical quantity kinds, reported/parser symbols,
basis, precision and source uncertainty. Equal dimensional expressions do not prove equal
quantities; unknown source basis stays unresolved. Valuesets conversion strings are never
evaluated as governing computation. Native unit declarations remain refused until their actual
supported-profile lowering is deliberately selected and implemented.

I05 chooses identification-only delivery or a named cross-unit operation and established units
engine, with an exact dependency version qualified then. No conversion library/version is selected
by this plan. For numerical conversion the contract must state scale/offset, precision/rounding,
context and basis requirements, uncertainty handling, original values and transformation lineage.
Numerical classification is a separate optional branch: Valuesets can yield multiple matching
categories, so a consumer must preserve all matches unless an explicit domain policy warrants
exclusivity. Neither conversion nor classification changes source/fact identity or rewrites
reported values. Any changed identity or ordinary inference policy requires its own confirmed
decision before implementation.

## Decision-producing investigations and readiness

The coordinator owns [I01](../domain-data-model_2026-11-10.md#DMC-I01),
[I04](../domain-data-model_2026-11-10.md#DMC-I04) and
[I05](../domain-data-model_2026-11-10.md#DMC-I05) disposition.
These investigations choose delivery details inside the selected outcomes. They are bounded
execution work, not prerequisites the operator must settle before authorizing this plan.
Current disposition is recorded at the coordinator; settled investigation decisions and their
evidence revise the owning target here. Accepted architectural changes also update their
D1/D2/D3/D5/D8 owner and ADR through the existing route.

| Investigation | Required decision and concrete deliverable | Dependent readiness |
| --- | --- | --- |
| **I01 — useful source and consumer selection** | Inspect candidate terminology, source distribution/import closure and actual corpus/domain records. Deliver one reviewable selection contract naming the terminology and exact snapshot/digests, acquisition/format route, two useful controlled fields with their local meanings, a real inspection/filter task, a located concept-review task, a measurement browsing/grouping consumer and its applicable quantity/unit source. Inventory every selected producer, boundary, retained product, query/CLI/report and native effect. Name rejected sources and the semantic reason; preserve local categories when unsuitable. The two fields must be useful independently, not duplicate labels or a fixture-only prediction enum. | DMC-06 needs the source/field/acquisition slice and DMC-01 locator artifact. DMC-07 needs the actual consumer inventory. DMC-08 needs the located task slice. DMC-10 needs the measurement slice. A source name alone, an illustrative pair of fields or an unsupported download format is not ready. |
| **I04 — located grounding backend** | Use the selected task and metadata contract to compare deterministic released lookup with the actual supported OAK search/lexical backend. For selected delivery, define the lookup/index representation, normalization/fields/ranking/ties/coverage, source-span contract, mapping-result contract and an independent known-answer case. Prefer explicit located input and metadata lookup unless another route has a material benefit. If this conditional branch is not justified, record a concrete retain/reject/defer decision, reason and revisit trigger rather than manufacturing a backend requirement. | Selected DMC-08 delivery needs this decision and a DMC-06 readable metadata/lookup slice. A justified retain/reject/defer conclusion can complete the investigation and dispose of the conditional opportunity without claiming an implemented consumer. A selected delivery remains open until its actual consumer and required evidence are complete. |
| **I05 — measurement compatibility branch** | Specify the real measurement task, recognition authority, quantity/basis compatibility rules and target consumer. Deliver a decision selecting identification-only with explicit unassessed numerical equivalence, or one cross-unit operation with a qualified engine/version and numeric contract. Separately accept or retain numerical classification with its multi-match semantics. Include affine/context-dependent and unknown-basis cases, and identify any profile/rule change before dependent effects. | DMC-10 identity/grouping can proceed with the I01 measurement slice and settled identity semantics; any numerical comparison/conversion or classification waits for its I05 branch decision and actual required enforcement. A list of candidate units libraries is not ready. |

I04 also compares a separate attributed candidate product with extending contextual contracts.
Select the owner that preserves term-mapping semantics without making ordinary contextual
retrieval depend on ontology preparation; reuse existing candidate/assessment/selection
primitives without forcing incompatible relations into their current result types.

## Delivery packages

### DMC-06 — acquired terminology and immutable metadata foundation

**Purpose:** deliver O05's selected pack and DDM-11's justified reuse as one coherent preparation
capability. Consume the I01 source/field slice, DMC-01's implemented locator artifact and the
completed PTD-11 baseline. Select and capture exact source definitions and ontology bytes through
the explicit acquisition boundary; pure preparation receives only those immutable inputs.
Compile the selected membership and metadata contracts, shared OAK preparation and archive
reader together. Do not pass an aggregate external schema into the finite profile and silently
strip unsupported constructs. Distinguish descriptive retained constructs from executable local
declarations; a required unsupported source feature must be faithfully lowered or refused.

Migration covers acquisition dependencies, compiler/version/manifest inputs, prepared artifact
custody, ordinary archive reading and inspection accessors. Keep `VocabularyMember`'s archived
shape intact; version the new artifact and any affected producing contracts. Retire per-enum
OAK metadata/prefix preparation replaced by operation-owned reuse, while retaining the supported
Term Validator file bridge and final composed subtraction. Existing final subtraction and invalid
source cases remain independent controls. Older archive readers need only the explicit product
availability behavior described above, not a fabricated metadata backfill.

**Ready output:** two useful fields over the selected pinned source, deterministic membership and
metadata with exact source custody, supported checks/unknowns and offline reopen. This foundation
slice can unblock DMC-07/08/09 before their consumers are finished; it does not complete O05.

### DMC-07 — terminology inspection and source-record filtering

**Purpose:** make the foundation useful to the actual I01 developer/researcher. Consume the
DMC-06 readable metadata and membership slice and DMC-01 locator contract. Extend the existing
model inspection/query/CLI report owners for field-to-enum navigation, allowed values, definitions,
hierarchy and qualified mappings. Supply bounded term detail and a filter over the selected
source-grounded record population. Its request pins release, field, predicate/direction when
hierarchy is requested and record/run/data context. Exact-category membership and a declared
descendant-category filter are different operations; neither silently includes ontology entailments.
Filter results retain the source record and its actual checked/selected/unresolved binding state.

Migrate every selected consumer from I01, including its report schema, renderer, released query
description and protected native reader if used. Derive term display from the artifact rather
than rebuilding it from installed Valuesets classes. Filtering should join/filter bound record
references at the owning query boundary and hydrate requested detail after selection, rather
than loading the whole corpus for each term. If selected fields add enforcement beyond existing
enum membership, declare and qualify the strict boundary/native custody change before activation;
a diagnostic label check cannot supply that guarantee.

**Acceptance:** a researcher can inspect either field, distinguish reported wording from selected
term/definition, filter useful records and explain an unmatched or unchecked binding. An empty
result states population/coverage and does not prove the source never discusses the concept.
The same journey reopens under the original release without today's source files or endpoint.

### DMC-08 — located external-term candidate review

**Purpose:** when I04 selects delivery, implement O06's bounded review workflow with explicit
unresolved outcomes. A justified retain/reject/defer decision completes its conditional decision
route without claiming this workflow exists. Input for selected delivery is an existing
source-located concept/phrase and its exact representation/run
binding, selected terminology release and lookup policy. Reuse source-coordinate validation and
candidate/assessment/selection owners; extend their declared contract where external-term targets
require a distinct shape. Produce a fixed examined candidate population, matching reason and
term metadata for each, competing mappings and an explicit unresolved/no-suitable-match outcome.
The candidate ordering is a heuristic, not a factual equivalence assertion.

Selection retains the original phrase/span, candidate population, reviewer/assessment decision,
selected term and vocabulary pins, and mapping predicate/direction with its provenance. Keep
external mapping kinds separate from contextual `denotes` and from global canonical identity.
If the scoped selection contract cannot express those distinctions, update its model, strict
boundary and protected retained publication/read path together; do not overload existing relation
strings. Methods still propose observations and consolidation owns knowledge selection. Existing
local exact/lexical/contextual retrieval continues for its corpus-local task; remove only the
duplicated lookup or adapter paths this selected external-term route actually replaces.

**Acceptance:** disambiguate competing terms by their definitions; retain a close mapping without
promoting it to exact; leave no appropriate term unresolved; preserve two identical spellings at
different supplied source spans as distinct occurrences. No automatic all-occurrence extractor,
scientific-truth decision or new global entity identity is implied. Archived review reopening
uses its examined candidates and original products rather than rerunning current retrieval.

### DMC-09 — explain a proposed vocabulary update

**Purpose:** deliver O07 through existing release/model-change reporting. Consume two DMC-06
products and the DMC-07 declared consumer bindings; DMC-08 retained selections contribute impact
references once available, but are not a prerequisite for comparing prepared terminology products.
Extend `compare_semantic_releases`, its released report contract, `ci schema diff` and model-change
preview/inspection to identify added/removed values, changed labels/definitions/meanings,
hierarchy/mapping predicate changes, obsoletion and applicable unknowns.

Compare exact products once per report, and resolve known declarations/query bindings/retained
uses through the existing dependency and read owners. State the actual surveyed population and
data revision; absent OAK usages or incomplete historical consumer discovery cannot prove no
impact. A source-level OAK diff is optional explanatory evidence, with adapter/version/coverage
reported. Keep source-only changes distinguishable from admission/meaning changes and runtime-only
changes. Do not call the ontology again per changed member to reconstruct the report.

**Acceptance:** a label-only update, removed/obsolete member and close-to-exact mapping change
produce different explanations, including known field/retained-review uses and unassessed scope.
Old reads reproduce old labels/mappings; new activation remains a separate reviewed effect.
Update the existing report/schema consumer together and remove superseded ad hoc vocabulary
comparison formatting where replaced. No automatic synchronization, reinterpretation or migration
framework is added.

### DMC-10 — recognized measurements and selected compatibility

**Purpose:** deliver O08's selected browsing/grouping and compatibility-assessment consumer.
Consume I01's measurement slice, I05's identity/compatibility decision and DMC-06 metadata where
that selected source supplies it. Recognition produces an attributed interpretation beside the
source measurement: reported value/unit, recognized unit and physical quantity kind, source
symbol/reference quantity, basis, role, uncertainty, status and evidence. Unknown or competing
recognitions remain unresolved/ambiguous; the recognition never overwrites original fields.

Provide the actual I01 consumer with grouping by recognized unit/quantity and an explanation of
compatible, incompatible or unresolved context. Identification-only delivery must say when
numerical equivalence/conversion is unassessed, rather than claiming that grouped values are
interchangeable. Existing textual-unit/refusal behavior remains valid for unsupported or unresolved
cases. Do not infer physical quantity kind from `TypedPremise.quantity`, a dimension string or
unit spelling alone. A selected stronger comparison in `methods/structural_products.py` needs a
separate released policy and complete source/basis compatibility witness; changing its parser
label alone is insufficient.

If I05 selects conversion, integrate exactly the named cross-unit consumer, engine/version and
precision/offset/context/uncertainty contract. Retain original values and derived transformation
provenance through generated boundary, persistence, query, export and assessment consumers.
`500 ms` versus `0.5 s` is comparable only after the same actual quantity and basis are established.
If I05 selects numerical classification, retain multiple valid categories and threshold boundary
semantics in a separate result. Branches not selected get an explicit retain decision and revisit
trigger at the coordinator; their absence is not concealed as completed conversion.

**Acceptance:** the reader can group selected source measurements and inspect the recognition;
unknown units/basis remain unresolved; equal dimensions with different quantity kinds do not
establish compatibility; different source symbols are not automatically incompatible physical
quantities or identical ones. Conversion, when selected, additionally handles a known exact scale
case and explicitly supports or refuses affine and contextual cases without precision loss.
Native unit metadata support is introduced only if needed, with all affected consumers migrated
and superseded selected comparison paths removed in the same delivery.

## Integration, verification and completion

Logical readiness is finer than whole-package order. DMC-06's immutable metadata reader enables
DMC-07 inspection, I04/DMC-08 lookup and DMC-09 product comparison. DMC-07's field/consumer bindings
enable known-use reporting. DMC-08's retained selections then extend that same DMC-09 view; do not
hold the basic diff behind grounding. DMC-10 identity/grouping need not wait for DMC-08, and its
numerical branch waits for I05. Agreed schemas alone do not establish these prerequisites: each
ready slice must have implemented producers/readers, migrated consumers needed by its own scope
and targeted functional evidence. The coordinator records the actual ready evidence.

Shared edit surfaces include `ontology.py`, `prepare.py`, `types.py`, model/execution declarations,
release archive readers, `operation_reporting.py` and CLI/report consumers. These are integration
constraints, not additional runtime barriers. Coordinate ownership before concurrent edits;
the I01 consumer inventory and shared contract changes remain one assembled delivery. Persistent
development PostgreSQL18/corpus on port5434 supplies normal native work, with the existing
rollback-only authoring route where a candidate is needed. No new disposable database requirement
or per-package full gate follows.

Independent checks challenge the semantics rather than recomputing expectations through the
same metadata compiler:

| Concern | Suitable acceptance evidence |
| --- | --- |
| Closed acquisition, identity and archive | Hand-authored tiny OBO/declaration fixtures with independent expected values/relations/mapping predicates; missing source, refused import, conflicting prefix owner, source mutation and unsupported required constructs fail honestly. Shuffle inputs for determinism. Remove availability of live source/endpoint and reopen archived products. Tampered or wrong-release products refuse. |
| Complete composition and metadata | Existing inherited/static/include/minus cases retain final subtraction. A member excluded from the union does not bypass validation of its declared ontology dependency. Known definitions/hierarchy/mapping kinds survive and unavailable metadata stays explicit. Two useful real fields and the selected real-source inspection journey establish consumer delivery beyond fixtures. |
| Located review and filtering | Independently located repeated spellings, tied candidates, no suitable match, a dbxref and close/exact alternatives. Wrong source representation/run/release pins and missing evidence fail. Verify source-record filter semantics separately from vocabulary reachability, ranking and selection. |
| Update reporting | Independently specified before/after products for label-only, removed/obsolete member and predicate changes; known consumer references and intentionally unassessed scope remain distinguishable. Earlier archived reads remain unchanged. |
| Measurement interpretation | Independently authored expected unit/quantity/basis and unresolved cases, equal dimensions with different meanings, missing reference basis and source-symbol distinctions. For selected numerical branches use independent known numeric answers, rounding/uncertainty cases, affine/context refusal or supported results and multi-match classification boundaries. |
| Selected effects | Exercise generated strict boundaries and directly affected protected native persistence/read consumers, including malformed/wrong-pin publication. A mocked ontology or database is not native/provider qualification. Metadata-only inspection does not claim new database enforcement. |

During implementation use relevant compile checks (`uv run ci schema check PACK` when the
selected pack requires it) and targeted `uv run ci test -- PATH`, starting with
`python/corpus-structure/tests/semantic/test_ontology.py`, `test_prepare.py`, the affected release
report/archive tests, contextual candidate/selection/native tests and structural-product tests
according to the implemented slice. Add only meaningful tests for the new consumer contracts.
Inspect new snapshot diffs before acceptance. Provider/native applicability follows the selected
mechanism; identification-only needs no units-engine qualification. A serious unresolved runtime
regression may justify a bounded experiment, but no benchmark is required to demonstrate the
size of expected preparation reuse or to justify this capability.

At complete functional scope, the coordinator runs root maintenance and required integrated
`uv run ci test`, `uv run ci check` and applicable `uv run ci docs check`, accounts for the union
and final source/context through managed results, and follows the existing design-review cadence.
The packages close only with affected consumer migration, retirement of what they replace,
archive custody and honest remaining limits. O05 closure includes DMC-06/07; O06 disposition
requires I04's concrete branch decision, and selected delivery additionally requires the
DMC-08 consumer. O07 includes DMC-09 plus all delivered use families; O08 includes
DMC-10's selected identity/compatibility branch and any explicitly selected numerical obligations.

**Rule changes:** none selected by this companion. Metadata display and attributed interpretations
preserve current native profile, identity and entailment defaults. If source/profile selection or
I05 reveals a required rule change, present its concrete consequence through the coordinator's
operator-confirmation route before fixing that dependent target; then schedule its ADR/owner and
all affected lowerings before effects. Do not infer approval from a library's capabilities.

**Checks during plan authoring:** source/reference inspection only; functional, native/provider
tests, probes, installs and benchmarks **not_run**. Documentation publication checks and final
maintenance belong to the coordinator. The coordinator records source/field selection, completed prerequisites and actual execution
evidence. I01's remaining consumer/measurement slice, I04 and I05 stay prerequisites of their
dependent consumers; plan prose alone does not establish delivery.
