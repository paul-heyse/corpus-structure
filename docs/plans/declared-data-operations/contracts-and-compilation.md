# Declared data operations — contracts and compilation

**Status:** Proposed implementation scope; no implementation or qualification claimed.
**Authored:** 2026-11-12. **Packages:** DDO-01–DDO-03.

This companion specifies the governing model, semantic identities and generated binding/port
foundation for the declared-data-operations series. The coordinator owns the assembled target,
execution state, finding dispositions, qualification and accepted rule changes. This page has no
second progress or findings ledger. It consumes the [audited principal review](../../design_review/reviews/design_review_declared-data-operations_2026-11-12.md)
and [target contracts](../../design_review/reviews/declared-data-operations/target-contracts-and-storage.md)
at `64dc6c3e628704941b45e41e19b74cc925162e02`. RC01–RC09 were explicitly accepted by the operator
on 2026-11-12; their decision-record and architectural-owner changes belong to this series.
Earlier plans provide no prerequisite or scope constraint. This is a substantive replacement;
old interfaces and private policy do not become preservation requirements merely because they exist.

All target mechanisms below are **Proposed**. Existing-source and selected-library observations
are **Interface-checked by source inspection, 2026-11-12**, at product source `8c0f4f951`.
No tests, model calls, database queries or protected reference-answer reads were performed to
author this companion. Its acceptance cases describe future implementation checks.

## Responsibility and delivered contracts

One composed released model governs every supported domain operation: source capture and
projection, derivation, discovery, selection, external work, publication, consolidation, and
affected serving/evaluation behavior. Algorithms implement its contracts; they do not own
undeclared applicability, result dependencies, state interpretation or effect authorization.
The model need not turn each semantic operation into a physical task or stored intermediate.

| Package | Owns and delivers | Consumed by |
|---|---|---|
| DDO-01 | Complete effective operation/kind/binding model; validation; phased compilation and explicit semantic dependency graph | DDO-02/03 and every operation-family migration |
| DDO-02 | Canonical kind, definition, recipe, subject and product identity contracts; provider semantic/execution projections; identity vectors | Durable product/support storage, admission, reuse, export and change determination |
| DDO-03 | Typed admitted input/result bundles, adapter capabilities, fixed relational binding lowerings, common binding/explanation result | Demand execution, native publication, discovery, domain adapters and affected readers |

DDO-01 supplies a working normalized model, not merely agreed type names. DDO-02 and DDO-03
can develop against its stable semantic references in parallel, but the generated artifacts
must identify their consumed model/encoding contracts. DDO-03's final port and binding artifacts
depend on DDO-02 fingerprints. Native storage/execution consumers supply concrete relation and
publication bindings; their integrated delivery must not be claimed by these compiler packages.

## Existing foundations and the replacement boundary

The current [release preparation](../../../python/corpus-structure/src/corpus_structure/semantic/prepare.py)
already closes supplied imports without filesystem/network fallback (`:260–355`), materializes
effective inherited slots and bounds (`:624–800`), and archives normalized definitions and
boundary recipes (`:866–887`). The [execution compiler](../../../python/corpus-structure/src/corpus_structure/semantic/contracts.py)
validates a LinkML ExecutionCatalog before structuring immutable dataclasses (`:1474–1513,
1816–1833`). Its relationship, lifecycle and implementation checks are useful starting points
(`:1516–1733`); their existing representations are not sufficient justification for omitting
new role/scope/support distinctions.

[Generated call bindings](../../../python/corpus-structure/src/corpus_structure/semantic/operation_call_generation.py)
resolve qualified field sources and nominal identifiers (`:158–175,351–435`) and emit concrete
request/result signatures (`:675–895`). Extend that mechanism with operation-shaped ports.
Do not reinterpret the existing call-correspondence digest as a semantic kind or recipe digest.

The shared [physical metadata](../../../python/corpus-structure/src/corpus_structure/semantic/metadata.py)
and [relational compiler](../../../python/corpus-structure/src/corpus_structure/schema/relational.py)
already distinguish application-owned fixed tables from candidate release rows (`metadata.py:1–48`,
`relational.py:595–625`). Keep that distinction: release variation is rows and compiled query
plans over admitted projections, not arbitrary schema creation or a generic object store.

## DDO-01 — Governing model and effective semantic representation

### Operation and binding definitions

Extend the composed execution schema/catalog and normalized products with typed profiles of
one operation definition. Existing database/protocol contracts and data-operation profiles
reference that definition rather than authoring parallel applicability or effect policies.
Each operation definition owns:

- Stable semantic identity and complete definition revision; subject and contextual scope.
- Named input and output roles, semantic kinds, relation constraints, cardinality, ordering,
  multiplicity and explicit alternative/optional behavior.
- Applicability, invariants, coverage/completeness requirements, supported outcome domains,
  precision/numerical policy and result-affecting dependencies.
- State dimensions/transitions, immutable bindings, effects and their authorization,
  fulfillment/idempotency requirements, and failure/partial/unknown outcomes.
- Admitted implementation capabilities: scalar/batch/stream forms, preparation, cancellation,
  resource/ownership transitions and specialized algorithm limits.

Profiles distinguish pure derivation, closed-population discovery, selection/authorship,
effectful command/publication and governed reads/evaluation where their contracts differ.
They compose shared semantics rather than defining disjoint workflow engines. A successful
command receipt is different from possession of an equal product. Not all profiles are
memoizable or schedulable as product producers.

Input roles carry both a value projection and support requirements. A role may require exact
selected provenance or permit a declared value-based substitution; the declaration determines
which. Source/base/projection identity, analyzed selectors/context, family coverage, outcomes,
selected alternatives, relationship closure and authorization prerequisites are explicit.
Demand population selection chooses independently bound subjects; it does not erase the
source scope actually analyzed by an operation.

Use a closed typed relational binding representation, with semantic references to owned
projection schemas and relationships. Required constructs are role scans/joins; equality and
typed literal predicates; explicit same/distinct subject constraints; minimum/maximum cardinality;
ordered sequences, bags and sets; all-of and explicitly selected alternatives; optional slots;
and closed-population quantification/absence. Operation-owned computed predicates return typed
products through declared operations when relational forms cannot express their semantics.
No arbitrary SQL text, Python callback or newly invented effect program belongs in the binding
declaration. Add a genuinely new construct through its semantic owner and both lowering/validation
contracts, rather than a permissive escape hatch.

### Compile once into effective owned facts

Extract an immutable effective semantic representation shared by preparation, identity,
generation and reporting. It includes admitted effective class/property definitions, resolved
semantic URIs, enum members/meanings, relation endpoints/direction/multiplicity, applicable
invariants and interpretation policies, and normalized operation/binding/state contracts.
Use typed references between these facts. Retain declaration locations for diagnostics outside
semantic identity where they do not affect meaning. Authority belongs to each owned definition: external declarations or admitted implementation-owned
Python facts. The representation is a rebuildable compiler product, never another editable catalog.

Refactor the existing preparation path into these logical phases:

1. Acquire explicitly supplied immutable sources/assets; validate their admitted schema/profile
   and construct closed LinkML views plus admitted Python source collections. Permit closed supplied-
   source implementation extraction; prohibit ambient imports/discovery or executing metadata code.
2. Materialize both authoring frontends, extract callable/member facts and explicit domain metadata,
   resolve names/defaults and construct typed operation and
   binding products. Validate references, cardinalities, scopes, state/effect correspondence,
   capabilities and specialized dependency declarations.
3. Build semantic and admitted implementation-slice dependency graphs and derive kind/definition/recipe/binding identities
   under DDO-02. References inside this graph use stable semantic identifiers, not final release IDs.
4. Use suitable authoritative typed invocation surfaces directly; generate required native/wire
   boundaries, call correspondences and fixed projection/query artifacts
   from those products. Archive the effective products, their identities and generator provenance.
5. Form the final release manifest/identity and bind the execution attestation. Final release
   identity can refer to compiled semantic products; those products never require that final ID
   as an input to their own hash.

These are compiler phases, not separate processes, database transactions or mandatory files.
The current execution compiler's companion-schema preparation is reused or separated into the
same phases so that adding kind identities cannot introduce release ↔ execution-model ↔ kind
hash recursion. Retained schema interpretation uses its archived effective products, not new
defaults from the installed compiler.

Reject unresolved references, incompatible inherited constraints, undeclared role semantics,
unqualified cross-source joins, unsupported cycles in operation execution, or explicitly unknown
required dependencies with located diagnostics. Structural compilation does not prove an adapter
has disclosed every dependency; independent conformance remains necessary. Unknown input data
or incomplete discovered coverage is a modeled runtime result, not a malformed declaration.

### Concrete operation shapes

| Shape | Bound inputs and constraints | Result/effect contract |
|---|---|---|
| Source-scoped spaCy evidence | One exact source projection, its original base, declared selector/context, semantic inference recipe; selected source must belong to that base | Native evidence and family coverage over precisely that scope; no implication that a slice covers the document |
| Structural comparison | Authored selected population plus ordered/distinct passage roles; exact source/reading/support closure; aggregate membership witness | Comparison product with declared alternatives and coverage; adding/removing a member changes the binding even when surviving item values do not |
| Characterization publication | Fenced invocation/attempt, admitted layer and optional view members, exact source/dependency/support closure | Atomic multi-output publication and receipt; replay/conflict are transaction outcomes, independent of the analytical family outcomes |

These are minimum integration examples, not the completion boundary for the model inventory.
The full migration must express all supported operation families, including external work,
source discovery, consolidation and serving/evaluation, without keeping hidden method-name
lists or selectors as a second authority.

## DDO-02 — Canonical semantic identity and profile projections

### Identity contracts and acyclic compilation

Use SHA-256 over domain-tagged, versioned canonical semantic values. Each identity archives the
canonical input it names. Separate the complete operation-definition revision, result-recipe
fingerprint, eligibility/binding revision, generated artifact identity and execution attestation.
An operation ordinal names the registered immutable recipe fingerprint; it is not another
manually maintained source of version meaning.

Compile each kind fingerprint from the rooted closure of effective semantic facts relevant to
that kind, including inherited constraints, type/range/enum meaning, relation roles, invariants,
source/coverage interpretation and numerical policies. Dependency edges are typed and authored
or mechanically derived from those owned references; they are not inferred from reader usage.
Output kinds do not depend on incidental producer registration, physical row IDs or the entire
release. Meaning-bearing semantic algorithm/rule revisions remain explicit dependency nodes.

Serialize a finite rooted graph: nodes have stable qualified semantic IDs and effective payloads;
edges carry relation/role and any meaningful position/multiplicity. Canonicalize node and
unordered edge enumeration explicitly. Cyclic type/reference structures are finite references
in that graph, not recursively substituted hashes or a hash fixed point. Self-referential product
reference *types* therefore do not require a product's eventual digest. A change within a rooted
closure changes its digest; an unrelated node or authoring layout change does not. Inheritance
cycles and operational cycles lacking a declared iteration contract remain invalid even when
the generic graph serialization could encode them.

Use the already selected NetworkX 3.7 `DiGraph`, `strongly_connected_components` and cycle/DAG
operations for compile-time closure and diagnostics where needed. Keep semantic edge records
separately so graph connectivity cannot collapse parallel roles or meaningful multiplicity.
Sort semantic IDs rather than relying on graph insertion order or component enumeration.
NetworkX computes derived compile-time or pinned runtime projections under the shared graph
contract; it is neither durable execution authority nor a new scheduler.
The [SCC API](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.components.strongly_connected_components.html)
describes the mechanism; selected 3.7 installed source
`networkx/algorithms/components/strongly_connected.py:17–87` was inspected. No graph-isomorphism
or universal semantic-equivalence inference is introduced.

The result recipe names behavior revision, semantic parameters/assets, inference policy,
kind contracts and all result-affecting binding/support semantics. The complete definition also
owns eligibility/effects/lifecycle and execution capabilities. Eligibility-only widening preserves
an existing recipe only when result interpretation, actual inputs/scope/coverage, required
support/effects and validity are unchanged. Its new binding revision still governs admission.
Incidental runtime/compiler provenance changes do not automatically invalidate data. An admitted
normalized implementation revision is a result determinant for its supported profile; changing that
slice changes the recipe without a manual version bump. Compiler/generator changes affect recipes
through changed effective products or their explicitly modeled interpretation dependencies.

### Canonical values and subjects

Use the existing [typed value codec](../../../python/corpus-structure/src/corpus_structure/semantic/value_codec.py)
as the semantic primitive foundation: tagged boolean/integer/decimal/float/string/date/instant,
sequences and mappings. Preserve float hex, including signed zero, and finite decimal meaning;
observed decimal representation and raw byte artifacts remain separate. Add declared collection
and optional-input forms around those values: roles/positions, ordered bags, explicit sets,
present-empty, known absent, unavailable and unknown never share a sentinel. Defaults are
resolved and validated before fingerprinting. Source text/bytes receive no implicit Unicode
normalization; any semantic normalization belongs to an explicit contract. Reject duplicate
semantic field aliases/identifiers rather than letting a JSON mapping silently overwrite one.

Canonical semantic encoding uses tagged values with numeric lexical/hex forms represented as
strings, then deterministic JSON framing; do not hash driver-dependent JSONB number spelling.
Keep the primitive normalization contract shared with native enforcement. Extend the existing
[native identity functions](../../../python/corpus-structure/src/corpus_structure/semantic/sql/identity.sql)
where they are the owning boundary; their current `canonical_json` and `value_meaning` are
starting mechanisms, not proof that every new typed encoding already matches Python. Native
publication compares the declared canonical form/digest to admitted content, while exact artifact
digests authenticate original bytes. No new per-read whole-artifact rehash is required.

A subject identity preserves the kind's immutable original source, projection/recipe, source
occurrence and analyzed context/scope/order. Physical IDs can index these subjects but cannot
define their portable meaning. Population selection remains separate. A semantic product is
kind-contract fingerprint + subject identity + canonical body digest. Local members use stable
body-local IDs, qualified externally by the product; producing task/runtime/recipe and derivation
execution IDs stay in support records unless the kind explicitly represents observations about
them. This prevents both hash self-reference and provenance changes defeating equal-value cutoff.

### Provider and execution identity

Derive two projections from the authoritative provider/inference declaration. The semantic
inference recipe includes declared artifacts/model, preprocessing/options, native label schemes,
device class/dtype/backend and numerical policy where they affect result meaning. The complete
execution/admission profile also retains selected runtime, actual thread/process/placement and
startup/resource constraints. Declaration roles, not a hand-maintained exclusion list, determine
the projections. A thread/cohort/placement setting is result-neutral only under the explicitly
selected inference policy; different precision or unqualified provider behavior cannot be hidden
as scheduling provenance.

Preserve exact requested-versus-observed admission, actual scores, batch/member commitments,
raw answers and effective profile evidence. Rework the current
[NativeProfile](../../../python/corpus-structure/src/corpus_structure/methods/native_profiles.py)
fingerprint consumers (`:95–109,173–175`) so whole execution-profile hashing does not accidentally
remain semantic invalidation. Separate executable artifact identity from its release-bound
execution attestation; `runtime_bindings.py:100–123` currently mixes release/model references
with executable inputs. Neither executable identity nor library inventory becomes a reuse
equality condition merely by being archived. Admitted implementation-slice revisions are explicit
recipe determinants under the supported profile; broad runtime/library inventory is not a fallback salt.

## DDO-03 — Authoritative typed ports and shared binding semantics

### Typed ports and trust boundaries

Use the authoritative typed Python invocation surface directly where suitable. Generate necessary
native/wire/protocol correspondences and declaration-owned operation boundaries from DDO-01; do not
maintain redundant parameter/default wrappers for implementation-owned operations. Preserve nominal semantic distinctions through the existing
source/type resolution machinery; do not reduce admitted products, support or capabilities to
untyped dictionaries. Frozen dataclasses/tuples and owned canonical bytes represent internal
immutable bindings. Public mapping access returns detached values; `frozen=True` alone does not
make nested dictionaries immutable.

Use Pydantic 2.14.1 strict/extra-forbid boundaries with validated defaults for authored/external
inputs and generated wire results. Declare the wire ingress route explicitly:
`model_validate_json`/`TypeAdapter.validate_json` for JSON, typed Python construction for already
resolved values. Strict JSON admits JSON representations of tuples/dates differently from
strict Python, so Python pre-decoding must not accidentally change admission. Revalidate
untrusted model instances at ingress; a caller-created model does not confer protected
publication or source authority. These conditions follow the selected-version docs for
[strict validation](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/strict_mode.md),
[JSON validation](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/json.md),
[defaults](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/fields.md) and
[faux immutability](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/models.md).
Keep cattrs 26.2.1's existing exact-primitive dataclass structuring after ingress validation;
it is not a second semantic validator (`contracts.py:1474–1513`).

The invocation port receives the resolved binding, semantic parameters, admitted immutable
products and explicitly authorized effect/preparation/cancellation capabilities. It does not
receive a broad Reader that can discover undeclared answer-affecting inputs. Batch/stream/prepare
capabilities remain available where declared, so the port does not force scalar calls or repeat
provider preparation. Physical selectors only execute the declared relational query; `select`,
`input_digest`, `plan` and `close` cannot survive as independently discovered semantic conventions.

### Relational lowering and the Python result

Lower the typed binding specification to parameterized SQLAlchemy Core expressions over shared
fixed relation metadata. Use ordinary joins/`EXISTS` for matching requirements, explicit
`UNION ALL`/selected branches for alternatives, grouped cardinality checks, and ordered
aggregation where a bundle genuinely needs materialization. A semi-join may establish presence
but never substitutes for the complete member/role binding consumed by execution. Project stable
member keys and declared positions; never infer order from row arrival. Deduplicate only where
the declaration says set semantics, preserving distinct evidence episodes and parallel relations.

SQLAlchemy 2.1.6 supplies parameterized Core `select`, joins, `exists`, CTEs and PostgreSQL
ordered aggregate expressions. `lateral` supports correlated set queries when needed; it is
not required for every input. These mechanisms preserve PostgreSQL optimization across a complete
binding query rather than crossing Python once per member. Selected-version primary references:
[selectables/CTEs/lateral](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_1_6/doc/build/core/selectable.rst)
and [PostgreSQL aggregate ordering](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_1_6/doc/build/dialects/postgresql.rst).
Use recursive CTEs only for declared closure queries, not to invent cyclic execution semantics.
Queries are demand/subject scoped with appropriate keyed joins; all operations × all history
is not the baseline evaluation strategy.

Each resolved role returns an explicit state and evidence: present members (possibly an empty
collection), known absence under a closed population, unknown/incomplete discovery, unavailable
support or invalid binding. A common typed BindingResult carries these roles, required witness
identities, reasons and the applicability/sufficiency conclusion. SQL's null/empty aggregate
representations are translated at the generated boundary; they do not define domain meaning.
SQL `NOT EXISTS` establishes a semantic absence only with the declared closed-population witness.
Optional input arrival/removal changes the appropriate population binding. All-of requirements
and explicit alternative selection remain distinguishable; registry order is never a selector.

Python consumes this same BindingResult and validates the structural role/result contract from
the effective representation. It does not maintain a competing live selector/applicability
implementation. Local algorithm callers can construct validated structural input bundles without
unrelated infrastructure; live custody, permissions, current support/trust and publication remain
protected acquisition/admission responsibilities. Detached readers check their authenticated
snapshot closure and expose missing live premises as unknown, rather than claiming fresh
authorization or recomputing a live demand.

Generate `explain_operation` inputs/results from the same binding semantics: report the exact
failed/unknown role, cardinality, scope, family, selection or witness. A human explanation never
introduces another classifier. Live publication rechecks mutable admission under its native
fences; a previously compiled/query-valid binding cannot authorize an effect by itself.

## Package acceptance and independent checks

Each package delivers its consumers and retires superseded compiler/protocol machinery for that
scope. Keep existing useful source-coordinate, coverage, alternative and native-publication
controls. Remove tests that merely restate old registries, field lists or stage order; preserve
independent expectations for semantic behavior. Generation drift checks establish reproducibility,
not that the model is complete or the generated semantics are correct.

| Package | Required discriminating checks |
|---|---|
| DDO-01 | Hand-authored inherited/mixin/enum/range/relationship examples retain effective constraints; unresolved/invalid definitions reject with located diagnostics. The three operation shapes above compile with independent expected roles, states, effects and outcomes. Adding a supported operation needs one semantic definition and its specialized implementation, without another private selector list. |
| DDO-02 | Independent literal expected encodings distinguish typed numbers/strings, bool/int, signed zero, missing/null/empty, order/multiplicity and explicit sets. Equivalent source layout/import packaging preserves semantic fingerprints; a meaning-changing inherited constraint changes the correct rooted closures. Cyclic reference kinds terminate canonically, while invalid inheritance/execution cycles refuse. Python/native round trips agree without deriving both expected digests from production. |
| DDO-02 | An unrelated executable edit outside admitted determinants retains the recipe; a normalized in-slice refactor may conservatively change it; eligibility-only widening changes definition/binding but preserves that recipe. An actual scope/model/numerical change changes the appropriate identity. Equal text at different source occurrences stays distinct. Equal semantic output under different producing executions shares product identity while evidence episodes remain distinct. Whole execution-profile/thread changes do not leak into semantic identity under the declared neutral policy. |
| DDO-03 | Native and Python binding-result boundaries retain an independently specified set of members/roles, positions, support and witnesses. Test too-many/too-few roles, wrong-source joins, two distinct passages sharing text, present-empty versus unknown optional input, incomplete negative lookup, member addition/removal and unselected alternatives. Explanations identify the actual unmet obligation. |
| DDO-03 | Untrusted/caller-mutated nested payloads cannot change retained canonical state or gain protected authority. Strict JSON/Python differences and invalid defaults are intentional and covered. Effectful multi-output results retain atomic-bundle/receipt requirements; having a matching payload cannot satisfy a missing required effect. |

Use focused compiler/pure-boundary tests while implementing these packages, and native binding
checks when their real storage projections are available. Native checks use the project's working
database under its ordinary custody; this plan does not require disposable databases. Real provider
execution, assembled migration, serving/evaluation journeys and complete functional/repository
qualification belong to the new series's integrated qualification scope. These packages neither
inherit another plan's qualification nor require a campaign after every slice. The coordinator
records actual commands/receipts and final-source applicability; all checks above are **not_run**
at authoring time.

## Library evidence and remaining implementation discretion

LinkML 1.12.1 supplies effective slot materialization, including `is_a`/mixins/slot_usage.
The [SchemaView documentation](https://github.com/linkml/linkml/blob/main/docs/developers/schemaview.rst)
orients the API; exact selected behavior was checked in installed
`linkml_runtime/utils/schemaview.py:1820–1970,2018–2025`. The source merges inherited numeric
bounds and resolves inherited patterns, while repository preparation adds supported-profile
and non-weakening checks. Thus LinkML supplies materialization, not a replacement for the
project's complete semantic closure or operation validation. Retain the explicit supplied-import
route; do not call an ambient schema loader merely because it can resolve more sources.

The existing pinned LinkML/Pydantic/cattrs/SQLAlchemy/NetworkX families supply the relational/native
foundation. The implementation companion selects Griffe/LibCST/Astroid for the closed Python frontend
and assigns production dependency placement to DDO-01; ty remains conditional tooling. No general
effect interpreter or workflow engine is selected. Exact module names,
helper decomposition, table indexes and SQL expression arrangement remain implementation choices.
The effective facts, identity framing, support/population distinctions and projection ownership
above are shared contracts. If an actual composed declaration cannot be represented faithfully,
repair the owning model/compiler and affected projections; do not substitute a shallow digest,
opaque JSON port or private imperative policy.


### Shared key/admission projection

DDO-02 compiles two explicit projections of a resolved binding. SemanticRequestKey contains recipe,
subject, semantic value references, ordered/multiplicity/population witnesses, support requirements,
only contract-required episode/provider/alternative selections, and replicate. The AdmissionManifest
additionally retains actual selected episodes, definition/eligibility revision, permissions and
trust evidence. Those incidental admission fields are not hashed into SemanticRequestKey unless
their meaning is declared result-affecting. Native registration authenticates both projections;
no caller chooses an ad hoc exclusion list. An eligibility-only revision or substitutable support
change therefore need not manufacture a different logical computation.


## NetworkX projection/compiler integration — I01–I03/I06/I07

Consumes the [shared graph contract](graph-projections-and-analysis.md#projection-contract-and-physical-route--i01)
and [selected topology composition](graph-projections-and-analysis.md#shared-closure-cycles-and-partial-orders--i02i03),
from the NetworkX review at `7c5368faa`. DDO-01 adds declared projection semantics to the effective
model, not another registry: source/contract/selection, universe/filter/completeness, qualified nodes,
typed role/order/multiplicity edges and attribute interpretation. DDO-03 generates typed acquisition /
result correspondences consumed by native bindings and explanations. DDO-02 canonicalizes original
semantic records, independent of physical graph class or iteration order.

Use [`DiGraph`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/classes/digraph.py)
connectivity with original typed edge witnesses: insertion auto-creates endpoints, so validate every
reference and add isolates first. Repeated edges collapse connectivity but must not collapse canonical
roles. [`strongly_connected_components`/`condensation`](https://github.com/networkx/networkx/tree/networkx-3.7/networkx/algorithms/components)
permit finite recursive type closure and precise unsupported-cycle diagnostics. Retain `members` /
`mapping` and original edges; component integers never enter semantic identity. `descendants` excludes
the root: add it explicitly. Stable-key topological order applies to acyclic projections/condensation,
not permitted cyclic reference graphs. Binding sufficiency remains typed relational semantics.

DDO-01/02 qualify actual effective definitions plus independent isolate, unknown endpoint, parallel
role, self-reference and shuffled-input canonical examples before downstream identity consumers use
them. DDO-03 checks that acquisition/explanation retain independently expected roles/completeness.
Add attribute-aliasing controls: freeze does not freeze payload dictionaries. Selected 3.7 APIs need
ordinary typing checks against the older stub selection. No WL/isomorphism-derived identity or new
backend package is selected. All implementation checks remain not_run at authoring.


## Implementation-owned frontend and slice integration — Python I01–I04/I07

Consumes the [shared authoring/extraction contract](implementation-contracts-and-fingerprints.md#I01)
and [implementation identity policy](implementation-contracts-and-fingerprints.md#I03), from review
`0907dcc23`. Its RC01–03 were accepted on 2026-11-12. DDO-01 implements both source frontends into
one effective model; DDO-02 admits complete supported slices as recipe dependencies; DDO-03 uses
suitable authoritative typed invocation directly and generates necessary native/wire correspondence.

Griffe [`visit`](https://mkdocstrings.github.io/griffe/reference/api/agents/) reads supplied source
into callable/member objects; explicit module collections and bounded external-disabled alias
resolution retain source/exposure identity. The thin operation extension exports custom metadata
explicitly because native JSON omits extra. LibCST
[`ScopeProvider`/qualified names](https://libcst.readthedocs.io/en/latest/metadata.html) supply located
binding evidence; Astroid [`lookup`/assignment/inference protocols](https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/protocols.py)
refine supported targets. Successful inference does not certify exhaustive closure. Keep authored /
extracted/inferred/modeled provenance and supported-profile admission separate from graph connectivity.

Qualify one actual simple operation and inherited interpretation family before bulk migration;
require independently expected signatures, nominal roles, metadata export, slice members and
normalization bytes. Preserve existing ingress/native controls. Body/helper/default/base/asset
changes must reach the correct recipe; unrelated or permitted cosmetic changes need not. Unknown
required determinants refuse complete reusable admission. Actual native/provider integration and
final qualification remain with their existing packages; no source-policy fallback or new checker.
