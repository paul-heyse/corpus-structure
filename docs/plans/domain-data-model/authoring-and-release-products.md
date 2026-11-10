# Effective-model authoring and release inspection

**Proposed implementation design, 2026-11-10.** This document develops
[DMC-01](../domain-data-model_2026-11-10.md#DMC-01) and
[DMC-02](../domain-data-model_2026-11-10.md#DMC-02) for the domain-data-model coordinator.
The coordinator alone owns package state, investigation scheduling, opportunity disposition,
execution order and completion evidence. Package descriptions below are intended work,
not claims of implementation or qualification.

## Purpose and source baseline

An operator or coding agent should be able to select a release, inspect a class, property or
operation, find the declaration contributing an effective constraint, and validate an illustrative
candidate through the same release. The useful result is a coherent authoring loop without
initializing ingestion, provider models or native publication. An inherited required field must
be explainable as an inherited requirement; a descriptive annotation must not appear to be an
executed guard.

The selected source is the [integrated functional review](../../functional_reviews/domain-data-model_2026-11-10.md)
and its [O01 authoring argument](../../functional_reviews/domain-data-model/model-authoring.md#O01),
including DDM-01/DDM-02 in the [semantic-declarations discovery](../../library_leverage/libraries/domain-data-model/briefings/semantic-declarations.md).
Code inspection for this plan was at `8e69e2b5f6dc56bd01c3a63b27b0a7ee28d313da`,
2026-11-10, with concurrent PTD owner/plan/evidence work present. Read the completed PTD-11
handoff before execution; the coordinator places this work after that handoff and before PM2.
This plan neither qualifies PTD's source nor changes its obligations.

The architectural owners are [D2 release and boundary realization](../../design/D2-schema-and-guidelines.md#release-and-boundary-realization),
[D2 preparation](../../design/D2-schema-and-guidelines.md#semantic-release-preparation-entry-point),
[D8 interfaces](../../design/D8-agent-and-query-interfaces.md) and
[DESIGN §B5](../../design/DESIGN.md#section-b5). ADR-0024 governs pure preparation;
[ADR-0031](../../adr/0031-semantic-execution-closure.md) separates immutable opening from
admission; [ADR-0073](../../adr/0073-generated-type-correspondence.md) retains physical
correspondence distinctions. Enduring changes belong in D2/D8 at implementation. No new
native construct or enforcement profile is selected by these inspection packages.

## Existing foundation and focused assessment

**Source-inspected, 2026-11-10.**
[prepare.py](../../../python/corpus-structure/src/corpus_structure/semantic/prepare.py)
already checks supplied source names, duplicate declarations and namespace collisions,
materializes source-relative URIs, seeds a closed import map, merges the explicit closure and
induces effective class slots. It emits immutable definitions, rows and generated artifacts.
Its preview already exposes effective class/range information. Preserve those checks and their
failure locations. An inspection feature must not reopen imports from ambient files or network.

[PreparedRelease](../../../python/corpus-structure/src/corpus_structure/semantic/types.py)
already owns definition/property indexes, demand-built class/property adapters,
`validate_python`, `validate_json`, accepted-value counterparts, and mode-specific
`json_schema`. [operation_reporting.py](../../../python/corpus-structure/src/corpus_structure/semantic/operation_reporting.py)
already builds trusted model-bound explanations, located validation reports and impact reports.
[semantic_server.py](../../../python/corpus-structure/src/corpus_structure/intervene/semantic_server.py)
exposes `explain_operation` against an explicit archived release in a reader snapshot;
[cli/model.py](../../../python/corpus-structure/src/corpus_structure/cli/model.py) owns the
operator's model-change interaction.
[review_bundle.py](../../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py)
already exports selected release contracts. These are foundations to compose, not missing
services to replace.

Normalized `ClassDefinition`/`PropertyDefinition` do not retain every authoring fact: for
example aliases are in the boundary recipe, while selected authored metadata can be lost on
normalization. Reconstructing a source explanation from today's model would break historical
interpretation. Retain the missing inspection facts at the one point where exact supplied
declarations and effective compiler decisions coexist. Read effective executable meaning from
the existing definitions/products; retain descriptive facts separately and label their standing.
This is the FP-04/05 authority boundary, with FP-01/03 keeping transport and presentation out
of compilation and FP-07/H12/H26 avoiding repeated model preparation for each read.

## Target contract

### Retained facts and honest provenance

DMC-01 emits a deterministic, versioned immutable `inspection/effective-model.json` artifact
during ordinary release preparation. It is a derived product, archived and
authenticated through the existing artifact path, not an independently editable model or a new
native authority. Do not add a root archive field merely to expose an existing prepared artifact.
Use the existing prepared-artifact archive path; DMC-01 does not depend on DMC-04 completion.
Coordinate representation and compiler compatibility with DMC-04’s exact-reconstruction owner
and the existing determinant/version owner. The new product must not accidentally change semantic identity by
including local filesystem names, timestamps or generator-environment details.

Retain compact records keyed by stable release-local class/property/declaration identity:

- authored display/description/alias/subset/annotation facts needed by the selected explorer,
  with the precise supported field set documented; effective range, bounds, cardinality and
  conditional placement continue to come from existing prepared semantic products;
- source references as supplied module name, logical declaration path and exact source digest,
  for example `sources/core.yaml`, `classes/Derived/slot_usage/value/minimum_value`, SHA-256;
- inherited contributors, distinguishing the local declaration, reused slot, ancestor/mixin,
  range/type constraint and compiler-supported normalization contributing to the displayed fact;
- declared versus effective value and descriptive versus executed standing, including which
  projection/profile can enforce an effective constraint and any located refusal.

The source reference promises module/path/digest and inherited contributors, **not exact line
coordinates**. Use paths into the supplied YAML data model rather than a flattened schema's
generated position. Multiple contributors need not be falsely reduced to one winning location:
conjunctive patterns and inherited type bounds can both contribute. If precedence cannot be
attributed exactly, expose the known contributors and an explicit unresolved explanation rather
than inventing a winner. No general source-map service is required.

Preserve the input declaration index before merge/import induction discards authorship context.
Reuse current declaration collision/refusal work and the resulting SchemaView, rather than parsing
the entire closure a second time per class. Normalize provenance references against the supplied
bundle's names and digests. Do not unify the operation-call physical-kind universe with semantic
ranges: shared provenance can describe their correspondence while their own products retain
their respective authority.

An old supported archive lacking this artifact still opens using its recorded products. The
explorer returns the effective facts actually available and `detail unavailable in this archive`
for missing authoring provenance. It must not recompile, silently substitute current source,
or treat unavailable as absent/no constraint. A corrupt or unknown-version inspection artifact
gets a located unsupported/corrupt-detail result; it cannot authorize execution or weaken
ordinary archive authenticity checks.

### One domain read, two transports

DMC-02 adds a shared release-contract inspection function in the semantic/report owner, with
CLI and read-only MCP adapters. A conceptual request is:

```text
inspect_contract(release, subject_kind, subject_id,
                 property=None, view="summary", after=None, limit=...)
```

The exact command/tool names follow existing model and operation conventions. `release` is
explicit; a retained model-change candidate may supply its already prepared immutable release
through the same domain function. No process-global current release is inferred. Subject kinds
cover class, property and operation, with related vocabulary and projection information reached
through bounded detail. An unknown subject refuses with a located missing-subject outcome;
ambiguous class/property names require their declared scope.

The report binds release id, artifact-set digest, subject identity, requested view and any
continuation to the selected immutable products. Summaries include effective fields,
requiredness/presence, cardinality, range and supported constraint placement. Detail includes
provenance contributors, aliases and authored metadata, vocabulary membership/reference,
related operations and physical correspondence where those products exist. Preserve declared,
supported, admitted and observed distinctions: a read-only view of supported native lowering
does not establish the currently installed deployment's posture. Operation effect/precondition
semantics continue to come from `explain_operation`; link or compose that result rather than
reimplementing its policy in an explorer.

Construct illustrative input skeletons as an expressly nonvalidating aid: required unresolved
values have explicit placeholders outside the executable input object; actual defaults are
shown as defaults only if the governing boundary supplies them. Keep absent, null, empty and
defaulted meanings distinct. Do not manufacture scientific labels, identifiers, citations,
timestamps or valid enum members to make an example pass. A class with a recursive required
child must produce finite scaffolding plus a reference/placeholder, not infinite expansion.

An optional supplied candidate is validated through the selected class's existing structural
or accepted-value boundary with its purpose explicit. It returns the normal located validation
result and a reference back to the inspected contract. This operation is pure/read-only:
successful validation establishes that boundary only, not source support, native admission or
publication. O09 owns richer diagnostic custody; consume that interface rather than introducing
another diagnostics archive here.

## Pivotal library mechanisms and limits

The selected LinkML/runtime version is **1.12.1**, inherited from the review and corroborated
by installed source inspection on 2026-11-10. Native contextual induction is selected:
`SchemaView.class_induced_slots`, `induced_slot`, `class_ancestors` and `type_ancestors`, with
the repository's closed `importmap`. The [LinkML account](../../library_leverage/libraries/linkml/README.md#linkml-runtime-in-memory-import-closure)
explains dictionary import maps, mutation and ambient-fallback hazards. Installed contract
references are `.venv/lib/python3.14/site-packages/linkml_runtime/utils/schemaview.py`
(`induced_slot`, line1820; `class_induced_slots`, line2018; `class_ancestors`, line998).
`induced_slot` supplies contextual effective facts, not full source-origin attribution; the
application retains that small responsibility before merge. Do not replace current induction
with `materialize_derived_schema`: the account records bound/pattern fidelity concerns.

The selected executable boundary remains **Pydantic2.14.1/core2.50.1**. Existing
`PreparedRelease.adapter/property_adapter` and `json_schema(mode=...)` provide demand-built
compiled validation and mode-specific contract display. The [Pydantic overview §3/§7](../../libraries/data_model/pydantic.md#7-json-schema-generation-and-machine-readable-contracts)
and installed `.venv/lib/python3.14/site-packages/pydantic/type_adapter.py`
(`TypeAdapter`, line69; `validate_json`; `json_schema`) supply the API contract. JSON Schema
describes a structural projection; it does not represent all source, identity or native guards.
Keep Python/JSON validation modes and existing exact scalar encodings explicit.

LinkML `DocGenerator` is an optional renderer for selected reference pages, **not required for
DMC-01/02 completion**. Installed1.12.1 `linkml/generators/docgen.py` supports class/slot/enum/type/
subset/index templates and import mapping; the [O01 companion](../../functional_reviews/domain-data-model/model-authoring.md#O01)
records the inspected API locations. If used, run on an isolated copied/merged input and augment
it with admitted-product support labels. Do not let generator mutation modify the prepared
authority. OpenAPI's endpoint/security template and separate schema generation do not establish
parity; OpenAPI/GraphQL remain conditional on a concrete service contract.

## Work packages

<a id="DMC-01"></a>

### DMC-01 — Retain effective inspection metadata and provenance

**Consumes:** completed PTD-11 handoff, closed source/dependency bundle and existing normalized
definitions/operation products. **Produces:** the immutable inspection artifact and release-owned
read access; ordinary archive opening authenticates and exposes it without preparation.

Trace an inherited field whose pattern comes from a named type and whose numeric bounds come from slots and whose alias/local description
comes from a derived class. Capture declaration paths before flattening, connect them to the
effective field, and represent all relevant contributors. Add deterministic product preparation
at the existing compiler boundary; reuse the current preparation pass and artifact archival.
Update D2 and compiler/determinant compatibility as required by the actual product change.
Coordinate shared `prepare.py`, `types.py`, archive and operation-generation surfaces with
DMC-04 and PTD owners; a package dependency is not permission for simultaneous conflicting edits.

Accept when independent fixture expectations establish imported source-relative identifiers,
slot/mixin/type contributors, conjunctive constraint attribution, omitted/null/default distinctions,
and located unsupported-construct refusal. Equivalent named supplied bytes produce identical
inspection bytes without filesystem dependence; a changed contributing declaration changes the
relevant product. Archive round-trip reproduces exact product bytes and old fixtures report
unavailable detail. Include one class-valued operation result/physical correspondence case so
inspection does not relabel native type correspondence as semantic equality.

<a id="DMC-02"></a>

### DMC-02 — Deliver release contract explorer through CLI and MCP

**Consumes:** DMC-01's available/unavailable detail contract, existing operation/report readers,
release-owned validation and O09's diagnostic interface when selected detail needs it.
**Produces:** shared typed/domain report, discoverable CLI command and read-only MCP tool with
matching semantics. Core inspection need not wait for optional diagnostic subsidiary pages.

Implement the domain read first, then migrate overlapping existing presentation helpers to
call it where they ask the same question. Keep operation-specific questions in their current
owner; do not replace all model-change reports merely because they mention a release. Extend
model-change candidate inspection to navigate a prepared contract and keep its effect guidance.
Review-bundle contract export adopts shared facts only where its existing detached consumer
needs them; preserve that consumer's export format/version requirements instead of dumping the
entire inspection artifact into every bundle. CLI and MCP must share subject resolution,
bounded detail, failures and release selection, with public output schemas owned by the existing
trusted report mechanism or a coherent extension of that owner. Retire duplicated fact assembly
introduced or superseded by this route, including its mechanism-specific tests.

Accept an authoring journey that inspects an inherited constraint, follows its contributing
source, obtains a finite unresolved skeleton, submits valid/invalid candidates and reaches the
same release-bound located validation/operation explanation through both transports. Exercise
two simultaneously open releases with different bounds; pages and validation may never capture
the other release. Exercise missing subject, unknown view, limit/continuation mismatch, old
archive detail unavailable and unsupported required construct. Use a command/import boundary
check demonstrating the read does not load Docling/models or acquire write credentials.

## Conditional authoring branches and selection boundaries

The coordinator's complete O01/O10/O11/O12 coverage remains authoritative. These branches
describe the authoring obligations relevant to this document rather than a second status table.

- Native `represents_relationship`, `relational_role`, ordered/unique collections, arrays,
  extras, keys and classification/conditional constructs: investigate only against the selected
  real relationship/collection consumer. Existing `RelationshipDefinition`/`EndpointRole`,
  admitted unique keys/presence/inverse/symmetric/transitive behavior remain the baseline. A
  selected new construct needs an explicit supported-profile decision and every affected
  runtime/native/graph lowering before executable-support claims. Otherwise retain/refuse or
  display descriptive metadata with the reason; an explorer is not a profile expansion.
- SchemaBuilder/Schemasheets/data-entry templates, renderer/JS/grammar generation, provider
  previews, Rust/PyO3 and language generators: settle their consumer question within the
  coordinator's conditional investigations. A selected route must name its concrete authoring
  activity or independent tool and preserve release identity, presence, recursion and ordinary
  admission. Without that consumer, retain the CLI/MCP reader plus existing generated schemas
  and record a justified defer with its trigger. No general modeling application is implied.
- Map/YARRRML, spreadsheets and extraction/conversion integrations remain named directional
  exchange decisions under O03/O11. Select only a concrete source-to-target workflow that
  preserves multiplicity, source lineage and precision; otherwise retain existing intake.
- Optional rendered references can follow the reader, but must distinguish authored description
  from admitted execution. Native LinkML documentation alone does not complete DMC-02.

## Fit, failure and qualification

**Proposed benefit:** a new inherited constraint or product field becomes inspectable through
its prepared owner rather than requiring every caller to parse schemas and reproduce inheritance.
Compact provenance generated once per release and indexed on demand suits repeated small
operator/agent reads. Read summaries by subject; page large memberships and contributor lists
without preparing every adapter or copying all schema/artifact bytes. Reuse immutable
PreparedRelease lifetime and existing store-context opening cache; no second durable cache,
ontology service or process-global schema registry is needed. Full-model search may scan a
small prepared index once; a single-property read must not recompile the entire closure.

The revealing failures are attribution to the flattened root instead of the imported module,
an unresolved archived detail presented as no constraint, a skeleton mistaken for an admissible
record, descriptive relationship metadata labeled natively enforced, and two release requests
sharing mutable current-release state. Correctness cases above target these failures directly;
no benchmark is required to justify eliminating repeated preparation or claim a numerical gain.

Execution uses targeted preparation/archive/operation-report/CLI/MCP controls at the coherent
package endpoint, through `uv run ci test -- PATH` with the actual affected paths. At complete
functional scope the coordinator runs the required union through `uv run ci test` and
`uv run ci check`, with `uv run ci docs check` for publication and root `just turn-end` before
qualification. Planned verification is **not_run** during this document-only assignment.
