# Independent contract consumers, configuration and selected tooling

**Status: Proposed implementation design, 2026-11-10.** This supporting plan develops DMC-13,
DMC-15 and DMC-16 and the DMC-I07–DMC-I09 decision obligations. The
[series coordinator](../domain-data-model_2026-11-10.md) owns authorization, branch dispositions,
execution state, DMC-00's due target review and DMC-17's assembled qualification. Work executes
after completed PTD-11 and before production milestone two. No production changes, provider
qualification, installation or probe follows merely from this document's publication.

## Baseline, sources and shared foundations

The inspected baseline is `8e69e2b5f`, preserving concurrent PTD-11 documentation/test changes.
During authoring, `dfe77f5a3` landed PTD-11 review/native-test work; its final campaign remained
pending. DMC-00 still requires the completed PTD-11 handoff before production execution.
Inputs are [O11](../../functional_reviews/domain-data-model/validation-and-graph-analysis.md#O11),
[O12](../../functional_reviews/domain-data-model/configuration-and-operations.md#O12),
[construction/exchange branches](../../functional_reviews/domain-data-model/construction-and-exchange.md),
and the review's [complete discovery correspondence](../../functional_reviews/domain-data-model_2026-11-10.md#complete-discovery-correspondence).
Discovery's [portable contracts/settings](../../library_leverage/libraries/domain-data-model/briefings/portable-contracts-and-settings.md)
and [executable boundaries](../../library_leverage/libraries/domain-data-model/briefings/executable-boundaries.md)
contain the recorded installed-source observations.

The applicable library baseline is LinkML/runtime1.12.1, Pydantic2.14.1/core2.50.1,
pydantic-settings2.16.1, jsonschema4.26.0/referencing0.37.0, cattrs26.2.1 and OAK0.7.4.
attrs26.1.0 is transitive; msgspec is an uninstalled alternative. These are inherited review
context, not fresh environment qualification. Check the actual selected versions at execution;
later-release addenda do not silently change the relied-on contract.

[D2](../../design/D2-schema-and-guidelines.md) owns released semantic contracts and supported
lowerings. [D8](../../design/D8-agent-and-query-interfaces.md) owns exposed reports/export and
[D9](../../design/D9-repository-and-phase0.md) owns process settings and entry-point lifetime. Settings choose
resources; they do not become an ambient source of released domain meaning or method policy.
Archive ABI/opening and native enforcement remain with their current owners.

The focused assessment under core3.3/heuristics1.0/code-intelligence1.4 favors explicit contract
scope, honest unsupported/unknown outcomes, independent consumer checks and reuse of existing
operation lifetimes. Generated structures, runtime validators and source meanings must remain
distinct. The plan schedules conditional delivery only after its named question has an answer;
it does not require every discovered library capability to be adopted.

DMC-01's immutable inspection/provenance contract is shared: module, logical definition path and
source digest, with effective contributions/origins where available. A consumer must retain that
binding when it leaves the compiling environment. Historical absence is unknown; today's source
tree cannot fill an old package's missing provenance. Concrete dependency slices below require
implemented/usable outputs, not only a settled proposed interface.

<a id="DMC-13"></a>

## DMC-I07 decision and DMC-13 — One selected independent contract consumer

### Existing behavior and precise selection question

Current export is substantial. `ci schema derive` and `schema compile --out` in
[cli/schema.py](../../../python/corpus-structure/src/corpus_structure/cli/schema.py) already
deliver manifests, snapshots and model artifacts. PDF contract preparation in
[pdf_payloads.py](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_payloads.py),
[pdf_records.py](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_records.py)
and [pdf_contracts.py](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_contracts.py)
already uses prepared validators, local registries and retained schema bytes. Native mapping
deliberately admits a narrower local-reference grammar. Detached Arrow exchange is an existing
data consumer, not evidence that independent schema validation has been delivered.

DMC-I07 must name an independent consumer and the operation it needs to perform offline. The
preferred first candidate is a small external research/authoring script validating an exported
release-defined input or report family and returning located failures. The deciding case is
whether it needs shared/multiple schema resources or executable behavior unavailable in today's
standalone schemas. Inspect one actual exported family and that consumer's invocation without
expanding into a generic SDK project. If an existing standalone schema fully supplies the
consumer, select that delivery route and document its limits rather than building a compound
package for its own sake.

The decision records input versus output contract, exact family/release, representation,
consumer language/runtime, required definitions and validation semantics. It selects one of:
existing standalone contract delivery, a closed multi-resource package, a generated structural
consumer, or a named source-to-target transform. A reasoned retained outcome names the missing
consumer/premise and its concrete revisit trigger. It cannot mark selected DMC-13 implementation
complete before that consumer actually works. DMC-13 owns the closed contract and its independent
schema consumer. A selected generator, cross-language runtime or transform beyond that consumer
is DMC-16 delivery, consuming DMC-13 only when it actually needs that package. DMC-I07 owns that
selection once; these are not duplicate implementations or a universal prerequisite chain.

### Closed portable package when selected

Extend the existing derive/export owner to assemble a finite package of required immutable
resources. Include entry resource/fragment addresses, explicit `$schema` dialect, resource IDs,
dependency resource bytes and digests, model/release/source provenance, direction and declared
semantic limitations. Compute dependency closure under the admitted reference grammar before
delivery; do not include every artifact in a release merely because it is available. Reuse
retained bytes when available; regenerate from the exact archived authority only where its
contract supports it. Generating a contract under today's compiler is a new derivation, not
proof of the original producing contract.

For Pydantic-owned structural contracts, use
[`TypeAdapter.json_schemas`](https://docs.pydantic.dev/latest/api/type_adapter/#pydantic.type_adapter.TypeAdapter.json_schemas)
with shared definitions and explicit validation/serialization modes. The
[2.14.1 implementation](https://github.com/pydantic/pydantic/blob/v2.14.1/pydantic/type_adapter.py)
is the version-relevant reference. High-level generation composes existing ownership; it does
not imply that Pydantic custom validators are expressible in JSON Schema. Include that gap in
the package's advertised support, rather than inventing assertions to claim parity. Contract
locations remain the owned definition addresses, including DMC-01 provenance when known.

Create an immutable `referencing.Registry` populated with `Resource` objects and explicit
specifications. Use jsonschema's selected dialect validator and `check_schema` on prepared
resources; reuse the prepared validator for the consumer's operation. See
[jsonschema offline referencing](https://python-jsonschema.readthedocs.io/en/v4.26.0/referencing/),
[referencing0.37.0 Registry/Resource implementation](https://github.com/python-jsonschema/referencing/blob/v0.37.0/referencing/_core.py)
and [jsonschema4.26.0 validator selection](https://github.com/python-jsonschema/jsonschema/blob/v4.26.0/jsonschema/validators.py).
Explicitly reject missing resources, unknown dialects and unsupported required vocabularies;
`validator_for` fallback is not evidence of dialect support. No default remote retrieval is
allowed for this offline contract. A URL-shaped resource identity is not permission to fetch it.

Admit anchors, compound resources, `$dynamicRef`/dynamic anchors or unevaluated-region semantics
only when the chosen dialect and consumer require them and their resolution/evaluation behavior
is established. Static flattening can change dynamic scope; do not rewrite references merely
to obtain one file. Resource composition does not broaden PDF native mapping's local-ref
profile; its existing explicit refusal stays until its owning profile/lowerings are changed.
Formats, defaults, content annotations and extension hooks do not automatically transform data
or execute domain/native constraints. If the selected consumer needs those behaviors, identify
the specific extension protocol/type/format checker or declare the unsupported residual.

The independent tool opens the package without importing the repository compiler or connecting
to the working database, validates known inputs and returns original structural paths/causes
through its own straightforward consumer boundary. DMC-11 detail can be reused when that tool
is shipped as an existing CLI application flow, but an offline package must remain useful
without depending on the local result store. If later retrieval is promised by the local CLI,
use DMC-11/ADR-0069 custody; a detached package's explicit destination is its own delivery form.

### Generator, cross-language and transformation branches

DMC-I07 also makes a bounded decision for the source review's additional independent consumers:

| Branch | Deciding consumer question and delivery if selected |
| --- | --- |
| LinkML documentation/annotator/API references, renderer, schema/grammar generation, scaffolding or JS runtime | Does the selected author/tool need an inspectable representation or runtime that the existing derive/report interface cannot supply? Choose one output and wire it to the same effective model/provenance. A generated page or grammar must disclose its supported subset and nonexecuted constraints. No general authoring application or CLI replacement follows. |
| Rust/PyO3 or language generators | Does an actual independent client need generated structural types or shared executable validation? Compare generated code plus its runtime/build/custody burden with consuming the existing JSON Schema. Record structural versus executable fidelity; do not advertise generated type acceptance as native or scientific validation. Use the selected LinkML/Pydantic generator only after its supported constructs match the chosen family. |
| Map/YARRRML, conversion/flattening, spreadsheets, extraction/ETL | Name source shape, target contract, direction, precision/presence/multiplicity policy and lineage. Select one exchange that removes real maintained conversion work. Verify missing versus null, ordered/parallel values and exact numeric/source identity independently. A flattening export declares what it cannot reconstruct. No generic transformation platform is selected. |
| Dynamic JSON Schema, custom vocabulary/format/type protocols or generated test data | Tie the mechanism to the selected package/consumer. Keep unsupported required vocabularies a refusal; use hypothesis-jsonschema only for supplemental valid-input diversity, alongside independent known-invalid/known-answer expectations. Generation cannot establish the authority's correctness. |

Use the [LinkML1.12.1 generator source](https://github.com/linkml/linkml/tree/v1.12.1/linkml/generators)
and [LinkML Map documentation](https://linkml.io/linkml-map/) as scoped research entry points
when that branch is selected. Generator or transform dependencies remain candidates until the
actual version and contract are selected; this plan does not install them. Source inspection
can settle an unsupported construct; run a bounded compatibility probe only when its behavior
changes the selected consumer route. Do not rebuild the complete generator ecosystem to decide
one contract family.

### Work boundaries, migration and acceptance

DMC-13 needs DMC-01's implemented effective-contract/provenance slice and a stable selected
family. For release archive inputs it also needs the archive-opening slice from the construction
packages; it does not wait for unrelated wire-conversion replacement. For a new native profile
it waits for the profile's implemented lowerings, not just exported metadata. DMC-11 is a
dependency only for a selected shared detail/retrieval interface. Coordinate changes to
derive/export commands, report models and prepared-validator helpers with their current owners.

Deliver producer, dependency closure and independent consumer together. Migrate the chosen
script/client off duplicated handwritten schema fragments and remove superseded copies,
reference rewriting or consumer-local contract assumptions. Keep independently maintained
invalid examples and actual historical contract readers. Do not replace PDF local-registry
preparation or Arrow exchange solely because a new package shares library types. Update D2/D8
at the actual changed meaning and keep generator/SDK/transform support limits discoverable.

Acceptance requires the named consumer disconnected from repository imports, database and
network, using the exact package to distinguish known valid and invalid instances. Cover required
resource omission, unresolved external reference, unknown dialect/required vocabulary, anchored
addresses, input/output mode differences and package digest/provenance mismatch. If dynamic
scope or unevaluated regions are admitted, use independently expected cases that fail under
incorrect flattening/evaluation. Unsupported executable/custom/native rules remain visibly
outside the structural claim. Cross-language or transformation delivery additionally checks
its named fidelity conditions; Arrow transfer success or generator exit zero is insufficient.

Preparing one registry per package and reusing it within the actual consumer operation avoids
repeated parsing without creating global mutable caches. A large unrelated release must not
inflate a selected contract package. Package size/resource bounds and parse failures are
declared separately from semantic validity. No quantitative speed claim or benchmark is required.

<a id="DMC-15"></a>

## DMC-I08 decision and DMC-15 — Selected configuration improvement

### Preserve the working acquisition model

[settings.py](../../../python/corpus-structure/src/corpus_structure/settings.py) owns a frozen
Settings root, nested plain models, constructor-over-environment acquisition and current masking.
`settings_customise_sources` selects only constructor/environment sources; direnv owns acquisition
outside that boundary. The entry point constructs a snapshot and passes it to operations.
`settings_report` already exposes effective values, approximate origins and unknown names.
`known_env_names` enumerates the root and one nested level. This implementation is sufficient
for its present mostly one-level namespace; there is no established missing cache/reload feature.

DMC-I08 examines an actual selected configuration/operation with deeper nesting, aliases,
instance-specific policy or an explicit new provider. The decisive failure is concrete: a
recognized supplied name is reported unknown, an ignored name is reported effective, origins
are wrong after validation/merge, or the selected resource fails to reach its consumer. If the
last occurs, repair the owning operation's propagation; a global provider/cache does not solve
that responsibility. If no selected workflow defeats the present report, retain current
acquisition and list the specific future nested/aliased/provider change that reopens it.

### Explanation design if selected

Extend the existing report at its acquisition boundary. Follow the actual instance's env
prefix/delimiter/case policy and accepted validation aliases, including alias choices/paths
where supported. Recursive field/alias traversal is sufficient for known-name enumeration
when acquisition itself remains unchanged. Do not build `CliSettingsSource` solely to discover
names: it can construct a fallback environment source with policy different from this instance.
Use its `env_var_names` only if native CLI composition is independently selected.

Where source explanation is needed, wrap the selected `PydanticBaseSettingsSource` objects to
observe their actual contributions while preserving source order/execution and validation.
Use [`current_state` and `settings_sources_data`](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#accessing-the-result-of-previous-sources)
as merge inputs, not final-field provenance. The version-relevant sources are
[settings2.16.1 main](https://github.com/pydantic/pydantic-settings/blob/v2.16.1/pydantic_settings/main.py)
and [source base](https://github.com/pydantic/pydantic-settings/blob/v2.16.1/pydantic_settings/sources/base.py).
All configured sources execute; precedence does not imply lower-priority sources are skipped.
Do not add effectful low-priority sources assuming they are dormant when a constructor value wins.

Produce a redacted explanation tied to the constructed snapshot: canonical field path, accepted
supplied name/source, effective value and reason for precedence/validation where known. Source
contribution, normalized/defaulted value and final-field attribution remain distinct. Validators
can combine or derive fields, so report mixed/derived/unknown attribution rather than assigning
a false single origin. Raw provider mappings and credentials are not persisted or logged.
Apply masking before report/failure retention, including credentials in URLs, nested secrets and
validation failures. Report keys/names when safe even when their values are withheld.

The same snapshot must reach the actual operation, including development/deployment target
selection, subprocess handoff where applicable and report context. Show the effective instance;
do not reconstruct a second Settings merely for explanation. Keep process settings separate
from immutable model/recipe policy and preserve CLI/MCP entry-point ownership.

### Provider/lifetime branch decision

DMC-I08 explicitly considers files, filesystem/cloud secrets, decoding controls, nested-default
updates, CLI composition/subcommands, async acquisition, refresh/reload and native settings
caches only against that selected operator workflow. Choose the smallest complete source/lifetime
change. A file/cloud provider selection must state explicit source order, acquisition effects,
credential custody, failure/timeout behavior and snapshot lifetime. Native class caching/cache
clearing competes with existing entry-point construction; it is not automatically an improvement.
Reload must state when an in-flight operation keeps its old snapshot and how the next operation
selects the new one. Avoid mixing resources partway through a pinned operation.

Read-only explanation fits current owners. A selected additional source, reload or source-policy
change requires the coordinator's explicit D8/D9/settings decision and any necessary ADR before
dependent implementation. Until that decision, deliver faithful explanation only or retain the
existing source policy. This is a bounded branch, not an inferred prohibition on proposing a
useful workflow and not permission to introduce providers for coverage.

### Delivery and acceptance

DMC-15 consumes the actual selected settings/operation slice and its entry-point snapshot; it
does not depend on vocabulary or graph work. If its report uses DMC-11 retained detail it waits
only for that report/custody slice. Replace obsolete one-level enumeration or heuristic origins
only where the new selected implementation owns their full responsibility; migrate
`ci context show`, CLI startup and MCP lifespan reports together. Remove duplicated ambient
reads, redundant settings reconstruction or new provider workarounds that this delivery
supersedes. Leave unrelated semantic configuration with its model owner.

Acceptance covers conflicting constructor/environment values; nested JSON plus field override;
an actual deeper field and alias; accepted versus unknown names; invalid acquisition versus
missing source; and the operation consuming its selected development/deployment resource.
Independently expected origins challenge merge/validation rather than repeating the source
wrapper's own mapping. Secrets and sensitive URL data stay masked in normal and failure output.
For selected providers only, exercise acquisition failure/timeout and source execution semantics;
for selected reload only, demonstrate old-operation/new-operation snapshot separation. A mocked
provider does not establish a passed actual-provider obligation.

The expected gain is faithful explanation with bounded operation-local state. Retain the simple
enumerator when it is sufficient. There is no mandated benchmark, global source registry,
provider service or process-wide mutable cache.

<a id="DMC-16"></a>

## DMC-I09 and DMC-16 — Additional tooling/codec/provisional workflow decisions

This obligation prevents capability territory omitted by O11/O12's primary flows from silently
disappearing. It is bounded by named functional questions, not an instruction to investigate
every API. Begin with current workflows and the source correspondence, reuse DMC-01–15 choices,
and record each branch in the coordinator as selected delivery or retained with reason/trigger.
An unavailable consumer is a reason to retain the present route, not a claim that the library
cannot supply the capability. Selected work includes its producer, consumer and removal scope.

| Branch | Functional selection question; bounded settling evidence; delivery or retained route |
| --- | --- |
| msgspec typed/reusable codecs, `Raw`, MessagePack, buffers/views and cattrs delegation | Does one named transport currently decode, map and validate the same data repeatedly, and can a library-owned codec retire that whole responsibility? Compare its actual valid/invalid payloads, constructor invariants, nested hooks, unknown keys, precision, absence/null, tags and error paths with the construction packages' selected route. Select only if the complete consumer improves; otherwise retain the current prepared Pydantic/cattrs boundary and revisit for a concrete transport or format need. Binary/view lifetime and bytes ownership must be explicit. |
| attrs lifecycle/conversion/equality/reflection | Is there a named object-construction responsibility whose invariant timing or representation requires it? Compare native dataclass/Pydantic/cattrs behavior at that actual boundary. Preserve constructor/post-init semantics and exact identity; retain current objects when this merely moves declarations. Transitive attrs presence is not a migration rationale. |
| Partial/lazy/tolerant parsing, omission/fail-fast and provisional provider capture | Does a selected preview/streaming recovery operation need usable incomplete input before the full product exists? Select only with exact raw custody, incomplete/unvalidated status, retained failure/omission information and ordinary complete-boundary admission on completion. Fail-fast presentation must not silently discard evidence. Otherwise retain complete parsing and revisit for the named provider workflow, not as a second admission mode. |
| LinkML Store/Automator or generic workflow/storage alternatives | Is there a distinct authoring/research activity whose operations/persistence cannot be composed through current application, export and managed-result owners? Compare one actual end-to-end activity, including inputs/effects, pinning, transaction/recovery and operator machinery. Select a bounded consumer only if it adds that capability; retain current owners where an additional store/workflow engine duplicates them. No ambient second authority or generic integration framework is implied. |
| OAK federation/native OWL/subsetting, domain enrichment/associations, taxon/statistics, visualization/plugins/LLM assistance | Does a named research/source-investigation question require these semantics and a meaningful corpus/relation? Reuse the terminology packages' source/mapping decisions and DMC-I06's graph projection/engine decision; assess only the remaining domain-specific branch. A selected enrichment view preserves relation meaning, background universe, unresolved identities and suggestion versus accepted assertion. A taxon-specific tool without a statistics-domain question is retained with a trigger for a concrete matching domain/corpus. No ambient ontology service or unsupported factual claim follows. |

For codec selection, use the installed selected contract where one exists:
[cattrs26.2.1 generated converters](https://github.com/python-attrs/cattrs/tree/v26.2.1/src/cattrs/gen),
[Pydantic2.14.1 TypeAdapter](https://github.com/pydantic/pydantic/blob/v2.14.1/pydantic/type_adapter.py)
and [attrs26.1.0 lifecycle source](https://github.com/python-attrs/attrs/tree/26.1.0/src/attr).
[msgspec documentation](https://jcristharif.com/msgspec/) is a candidate research entry point;
choose/pin the version and inspect its required hook/constructor behavior before adoption.
LinkML [Store](https://linkml.io/linkml-store/) and
[Automator](https://linkml.io/linkml-automator/), plus
[OAK0.7.4 source](https://github.com/INCATools/ontology-access-kit/tree/v0.7.4/src/oaklib),
are scoped capability references, not selected new dependencies. The complete operation and
actual consumer decide their fit. Native high-level composition is preferred to custom hooks
where it supplies the selected contract; hooks cover the real residual, not a new framework.

DMC-16 consumes DMC-I07's selected generator/transform/cross-language branches as well as
DMC-I09's additional tooling decisions. Its implementation slice exists only for
a selected outcome and must name files/consumer contracts, supported semantics, actual prerequisite
slices and verification before execution. Depend on construction/archive packages for a changed
archive or codec boundary, terminology packages for grounded source research, DMC-14 for a selected
derived graph engine, or DMC-13 for an actual independent tooling package only when that branch
uses them. Shared library names are not dependencies. Avoid duplicating decisions or consumer
delivery already owned by those packages; cross-reference their coordinator disposition.

For a selected route, replace its maintained conversion/parser/script/store responsibility and
migrate the actual consumers together. Retain raw evidence, archive ABI and independently useful
semantic tests. Delete superseded hooks, duplicate models, configuration and mechanism-only tests
where the selected replacement makes them obsolete. If a branch needs an authority/profile change,
route it before implementation rather than adding a fallback that silently changes meaning.

Acceptance uses independently expected valid/invalid cases for the selected branch, including
interruption and ownership/lifetime where relevant. A codec checks precision, exact bytes or
semantic identity at the specific promised direction; a preview never reaches ordinary admission
as complete; an enrichment view exposes its assumptions and source support. A smaller output or
successful decode does not prove less total work or semantic fidelity. Source inspection can
justify expected simplification; measurements are required only for quantitative claims or a
serious unresolved regression risk.

## Completion and validation boundary

DMC-I07, DMC-I08 and DMC-I09 require actual decisions with reasons/triggers for retained branches. DMC-13,
DMC-15 and DMC-16 require selected delivery and its migrated consumers; decision writing alone
cannot complete implementation of a selected branch. Reasons such as “no concrete consumer”
must identify what future consumer or failed present workflow would reopen the question. The
coordinator owns these dispositions once, including cross-package branches and rule impacts.

Implementation uses appropriate compile checks and targeted `uv run ci test -- PATH` at coherent
capability endpoints. DMC-17 assembles full applicable functional/provider/nonfunctional evidence
using `uv run ci test` and `uv run ci check`; DMC-00 owns formal review timing. Documentation
publication uses `uv run ci docs check`. Planned acceptance cases above are not executed results.
Functional tests, native/provider probes, compatibility experiments and benchmarks for this plan
authoring: **not_run**. All target-benefit claims remain **Proposed, 2026-11-10**.
