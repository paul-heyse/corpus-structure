# Python introspection and implementation-owned DDO contracts

**Proposed recommendations · 2026-11-12.** Reviews the complete remaining DDO-00–12 footprint:
[coordinator](../plans/declared-data-operations_2026-11-12.md) and its eight companions at
`efdd85f449440beb43e1b48afaeab7ee24ccb5fa`. Production source remains `8c0f4f951`; all target
packages are unimplemented. This review changes no plan, accepted decision or production behavior.

Consumes full end-to-end reads of the supplied [LibCST](../libraries/python_introspection/libcst.md),
[Astroid](../libraries/python_introspection/Astroid.md), [ty](../libraries/python_introspection/ty.md)
and [Griffe](../libraries/python_introspection/griffe.md) references, including their addenda:
1,611 / 1,967 / 2,270 / 2,321 lines respectively. Root synthesis incorporates bounded independent
Astroid, Griffe and ty contributions. The operator installed `libcst==1.9.0`, `astroid==4.3.4`,
`ty==0.0.102`, `griffe==2.4.1` (with griffelib 2.4.1); pyrefly remains 1.4.0.
Those manifest/lock edits and uncommitted library references are operator-owned input, not this
review's changes. The ty overview describes an earlier release; internal/main-branch features
are not assumed to be public contracts of installed 0.0.102.

Apply core 3.3, efficient-architecture heuristics, code-intelligence 1.4, test-assessment 1.2 and
repository binding. No broad diagnostic audit is initiated. Source findings F01–F14/C1–C7 and
NetworkX recommendations retain their DDO disposition owner. All benefits below are **Proposed**;
API/source observations are **Interface-checked, 2026-11-12**, not integrated/tested behavior.

## Combined judgment

**Recommend mixed authoring authority, one effective model, and operation-sensitive implementation
revisions.** A total governing domain model does not require an externally authored duplicate of
every Python operation. For intrinsically coupled algorithms, the typed implementation and its
colocated domain facts should be the source from which the outward contract is compiled. Derivation
is still modeling: the resulting contract explicitly participates in identity, connectivity,
validation, documentation, native binding and change determination.

For externally specified operations, durable protocols and source/model-defined semantics, retain
declaration-owned authoring and implementation conformance. Do not invert those authorities simply
because a Python implementation exists. Within an operation, signatures can own callable shape while
domain facts own support/effects/population meaning. Each fact has one authoring owner.

The libraries can replace meaningful pieces of manual discovery, lexical analysis, interface
reconstruction, documentation and migration machinery. They cannot infer complete arbitrary Python
behavior. This does not defeat practical selective fingerprints: admit a conservative, explicitly
bounded implementation slice for supported operations, make unresolved determinants consequential,
and retain ordinary DDO equal-value/support cutoff after recomputation.

Prefer Griffe for interface/documentation extraction, LibCST for source/binding structure and precise
rewrites, Astroid when supported inference resolves otherwise missing connectivity. Use ty's public
navigation/type observations for concrete inspection needs. This is a division of capabilities,
not a four-analyzer pipeline or consensus system. Select the smallest sufficient composition.

## Actual footprint and replacement opportunities

Paths below are relative to `python/corpus-structure/src/corpus_structure/`.

| Current responsibility | Grounding and target consequence |
|---|---|
| Semantic asset versus executable custody | `semantic/contracts.py:35–137` explicitly classifies model/grammar assets; `:1180–1447` captures a long named inventory and all owned Python/SQL. Preserve custody, but derive selected Python connectivity rather than maintain another per-operation relevance list. |
| Independently repeated implementation identity | `semantic/contracts.py:325` approved implementation mapping and `:623–715` bindings/call fields; DDO-03 generates ports. Derive actual callable identity/shape from its attached operation owner, retaining necessary native/nominal correspondences. Discovery must not grant execution permission. |
| Runtime/source change reports | `semantic/runtime_bindings.py:35–57,100–123` archives exact runtime; `semantic/operation_reporting.py:950–990` reports changed execution as behavior unassessed. Add operation-sensitive revision evidence instead of making runtime bytes a reuse fence. |
| Source consumer discovery | `schema/model_discovery.py:45–204` uses bounded AST/symtable/name matching plus ast-grep, explicitly candidate/unresolved. Replace lexical reconstruction and strengthen alias/owner evidence; keep examined coverage, skipped files and unknown standing. |
| Intrinsic inheritance/capabilities | `methods/interpretations.py:23–125` shares inherited methods while subclasses change class metadata. `methods/math/methods.py` has shared VERSION and source_dependencies; runtime plan/close getattr paths occur in orchestrate/semantic.py, orchestrate/ready.py and semantic/execution_preparation.py. Derive effective members and dependencies without losing supplying-owner identity. |
| Generation and inspection | `schema/stage_b.py:190–220` scans Python names/types; `cli/schema.py:409–451` rewrites generated migration source with ast. Griffe can replace interface scanning; LibCST earns use where lexical fidelity matters. Fresh generated code with adequate ast tooling need not migrate. |
| Plugin boundary | `serve/registry.py:30–100` validates query members and deliberately executes captured plugin bytes. Static inspection can preflight/document shape but cannot replace native permission, admitted loading or actual runtime contract checks. |

These are integration seams, not a claim every AST/getattr operation is defective. Keep adequate
stdlib parsing, Pydantic/LinkML inspection and native SQL parsing where they already own the task.
Python tools must not reimplement SQL semantics, provider behavior or document-language extraction.

<a id="I01"></a>
## I01 — Author each operation once, with an explicit direction of derivation

**Recommend · DDO-00/01/03/07/08 · FP-04/05, DP-01/06/08, CI-02/03.**

Extend DDO's effective IR with an admitted Python-owned authoring route. Use a typed operation
class with colocated domain metadata and typed implementation methods for coupled multi-capability
operations; ordinary typed functions can supply simple algorithm implementations under the same
profile. The source compiler supports a closed pattern of typed records/literals/references, not
execution of arbitrary decorator/configuration code. Stable semantic operation IDs are explicit;
module path, spelling and object addresses are provenance/correspondence, not semantic identity.
Do not generate extra wrappers merely to duplicate the already suitable typed invocation surface.

Derive parameter kinds, defaults, annotations, return structure, callable/declaration origins,
accessible inherited methods and source references. Author the missing domain facts once beside
that implementation: applicability, input-role/cardinality/source constraints, support substitution,
coverage/population closure, outcomes, effects, lifecycle, numerical interpretation and asset roles.
Python annotations may carry semantic references, but an `int` must not erase a nominal domain ID.
Do not infer an effect merely from a function name or pretend a signature proves idempotency.

External declarations and Python-owned definitions compile to the same effective operation/kind /
binding products. A fact cannot be independently editable in both. Keep a field-origin mapping so
inspection distinguishes authored, mechanically extracted, inferred and extension-modeled facts.
A helper does not require its own task, table, published product or domain operation: represent
internal implementation dependencies within the owning profile where those steps are inseparable.

Compared alternatives: keeping declaration-only authority retains duplicated shape/connectivity;
moving everything into Python would weaken independently specified/native protocols. Mixed ownership
retains the appropriate source of truth while allowing genuinely derivative outward contracts.
This is substantive improvement to the plan, not just adding a conformance checker.

Challenge/closure: add one actual inherited or simple operation with one authoritative semantic
addition and its genuinely new algorithm. Invocation, inventory, contract documentation and native
correspondence must follow without another owner/symbol/signature/dependency registry. Required
non-derivable native constraints stay explicit. Test mismatched role semantics and generated port
nominal identities independently. No implementation is established by these proposed shapes.

<a id="I02"></a>
## I02 — Compile closed source facts through existing library abstractions

**Recommend · DDO-01–03/07/08/10 · FP-03/06/07, DP-13/16, CI-01/04/10.**

Acquire exact admitted sources, dependency/stub environment and selected extraction settings once
at preparation/release construction. Analyze that captured universe; archived releases never read
new defaults or currently installed source. Derive at preparation time, then serve pinned products;
no request-time reparsing merely to display a contract. Local incremental tools may reuse prepared
facts keyed by the complete source/extractor context.

Use [`griffe.visit`](https://mkdocstrings.github.io/griffe/reference/api/agents/) on supplied code,
with explicit module/line collections, to obtain `Function`, `Class`, `Parameter`, overload, default,
annotation and type-alias structure. Register module hierarchy and resolve references in a separate
bounded pass. The [loader/resolution API](https://mkdocstrings.github.io/griffe/reference/api/loaders/)
returns unresolved attempted aliases, not proof of all program dependencies. Avoid ordinary loader
inspection fallback in closed compilation; empty search paths may still select ambient sys.path.
Custom extensions must themselves respect the supplied-source boundary.

Use LibCST `ScopeProvider` assignments/access referents, `QualifiedNameProvider` and repository
`FullyQualifiedNameProvider` for lexical/import evidence with precise spans. Multiple candidate names
remain multiple. `MetadataWrapper` copies by default and keys facts by wrapped node identity; never
join metadata from pre-wrapper or rewritten trees. Reuse `resolve_many`, `visit_batched` and
`FullRepoManager` over an explicit root/source set, instead of repeated bespoke scope/path scanners.
[Metadata contracts](https://libcst.readthedocs.io/en/latest/metadata.html).

Where lexical evidence is insufficient, Astroid `lookup`, `assigned_stmts`, `infer`, `CallContext`,
MRO/member-origin and bound-method facilities can resolve supported aliases, inheritance, constants
and callable targets. Preserve all candidates and `Uninferable`, exceptions and budget-limited
results. A declared brain/transform is an analysis model, not observed execution. Manager caches
and transform registrations have owned preparation lifetimes; shared state must not contaminate
another release. [4.3.4 protocols](https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/protocols.py),
[contexts](https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/context.py),
[manager](https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/manager.py).

Keep typed relations distinct: lexical reference, possible call, resolved declaration, type reference,
implementation determinant and authentic product/support lineage are different edges. Reuse the
DDO NetworkX projection contract for finite graphs, without promoting a call graph into readiness
or sufficiency. Exact source spans/normalization survive serialization; character/byte/UTF-16
coordinates need explicit conversion. Select only analyses needed by the consumer, with bounded
source acquisition and explicit partial results; completeness cannot be inferred from an output cap.

Successful or singleton inference does not establish an exhaustive target set: an analyzer can miss
runtime alternatives without emitting Uninferable. Reusable-slice admission additionally requires a
supported source/dispatch profile and explicit dependency boundaries. Unsupported reflection,
mutation or dynamic behavior requires a justified conservative boundary or prevents reusable-recipe
admission. Preserving reported unknowns is necessary but does not by itself establish completeness.

Closure: actual alias/re-export/inheritance cases replace candidate-name reconstruction; controlled
unsupported dynamic references stay unresolved. Generated models, source/stub disagreement, changed
analysis order and cached prior-release state must not silently change admitted facts.

<a id="I03"></a>
## I03 — Include conservative implementation slices in selected operation recipes

**Recommend · DDO-01/02/09 · FP-04/07, DP-04/09/12, CI-04/06/10.**

For implementation-owned algorithms, compile a finite rooted dependency graph from actual semantic
entry points. Add its versioned canonical **implementation revision** as an explicit recipe
determinant. Distinguish it from contract identity and whole-runtime execution attestation.
Changing a bug-bearing body without changing its signature or manual version must change the
relevant recipe; editing an unrelated function outside the admitted closure need not do so.
No universal behavioral-equivalence solver is required for this conservative policy.

| Determinant | Required slice treatment |
|---|---|
| Direct, imported and aliased calls | Resolved definition targets plus source relationship evidence; preserve all possible targets |
| Inheritance, descriptors, super and class configuration | Supplying definitions, relevant bases/receiver assumptions and effective class values; not subclass-body hashing alone |
| Callbacks and dynamic registries | Closed admissible target set, or explicitly bound implementation input; runtime-selected target is not the first inferred candidate |
| Globals, closures and initialization | Immutable captured values/definitions; mutable state and environment become explicit inputs/configuration/effects |
| Defaults/decorators/generated behavior | Definition-time expressions, referenced implementations/arguments and declared framework-generation model |
| SQL, grammars, templates, model files, native/providers | Explicit typed opaque dependency boundaries with captured identity/meaning; existing language-specific tools retain their authority |
| Reflection/dynamic loading | Resolve a bounded universe or supply an explicit coarse dependency boundary; remaining result-affecting uncertainty prevents complete reusable-recipe admission |

Initially normalize syntax conservatively: remove formatting/comments/positions from implementation
meaning while retaining executable structure, statement order, binding names, literals, defaults,
decorators and typed dependency edges. Retain docstrings/annotations by default: reflection or
runtime annotation consumers can make them operational inputs. Exclude them only under an explicit
profile restriction. Source-sensitive readers likewise require exact source as a determinant.
No automatic alpha-renaming, dead-code removal, constant folding or inferred-output substitution.
LibCST `filter_node_fields` supplies useful field categories, not a semantic normalizer; application
canonicalization must use the existing typed identity machinery.
[Node-field helpers](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/helpers/node_fields.py).

Encode a finite graph of stable qualified references/normalized payloads; cycles do not require
recursive digest fixed points. Include explicit opaque dependencies, normalization contract and
meaning-bearing analysis models. Keep tool-run provenance separately. An extractor upgrade changes
recipes when it changes effective determinants or an admitted interpretation rule, not merely
because a tooling binary changed. Never hash arbitrary Griffe dumps, Astroid `as_string`/`eq`,
LibCST `deep_equals` or ty's private incremental query graph as semantic identity.

A changed slice is a conservative new implementation revision, not proof outputs differ. DDO-09
can recompute the affected operation then stop at equal admissible value/support. Keep historical
products/derivations; change/currentness does not mean destructive deletion. Whole-package runtime
custody remains exact, but never an automatic fallback recipe salt. A deliberately coarse module
boundary is allowed only when explicitly modeled and complete for the chosen operation.

Challenge: function extraction or harmless rename may conservatively cause recomputation. This is
acceptable initial burden compared with unsafely missing a relevant helper change. Unknown mutable
state must not acquire false precision. Closure must independently distinguish helper-body/default /
base/asset changes, unrelated edits, unresolved dynamic dispatch and equal-output propagation cutoff.
Before enabling automatic reuse for a profile, establish these boundaries on actual operations;
unsupported profiles use explicit complete determinants rather than pretending universal inference.

<a id="I04"></a>
## I04 — Derive contracts, documentation and drift from the same effective products

**Recommend · DDO-03/08/10 · FP-02/04/06, DP-06/08/21, CI-03/11/13.**

Render operation documentation, implementation origin, declared/inferred connectivity and typed
call/native correspondences from one effective model. Keep explanatory prose colocated with its
owner; do not maintain separate handwritten parameter/default tables. Griffe `Docstring.parse` and
typed sections can enrich prose using final parent signatures; parse after enrichment because
`parsed` is cached. Alias exposed paths and `canonical_path`/`final_target` preserve public versus
implementation identity. [Navigation](https://mkdocstrings.github.io/griffe/guide/users/navigating/),
[docstrings](https://mkdocstrings.github.io/griffe/reference/docstrings/).

Use a thin Griffe `Extension` for the supported operation authoring pattern, not a general Python
configuration interpreter. Extract explicit domain facts into the DDO effective typed record.
`on_function_node`, `on_function_instance` and completion hooks offer useful syntax/model access,
but load hooks do not guarantee final alias resolution. Perform explicit whole-collection resolution
before claiming connectivity complete. [Extensions](https://mkdocstrings.github.io/griffe/guide/users/extending/).

**Selected-source corrections:** installed 2.4.1 `models.py:1350–1364` serializes members as mappings
and omits `extra` (explicit TODO). Thus `as_json(full=True)` does not preserve custom operation
metadata automatically. Export that metadata explicitly through the typed DDO projection; never
silently drop it. Native source/provenance fields also make whole dumps unsuitable recipe bytes.
The ordinary visitor extracts interfaces rather than a general function-body dependency graph.
These correct stronger readings of the supplied overview; do not copy them into compiler assumptions.

Compare comprehensive effective records to report additions/removals/changes in callable structure,
domain obligations, documentation, implementation revision and custody separately. Supplement with
Griffe `find_breaking_changes`/structured `Breakage` for supported public call incompatibilities.
Its asymmetric selected-breakage result is not an exhaustive diff or safe-reuse proof: body edits,
additions and some type/value changes are outside that contract. Containers versus leaf-function
comparison also matters. [Checking](https://mkdocstrings.github.io/griffe/guide/users/checking/),
[2.4.1 source](https://github.com/mkdocstrings/griffe/tree/2.4.1).

Existing native/ci/MCP inspection returns pinned source-linked contract and change facts with
unresolved standing; it does not choose a newer implementation or execute missing work. Preserve
native permissions and domain validation. Qualification compares independently expected facts,
including metadata export and same-spelled symbols from different owners, not only JSON roundtrips.

<a id="I05"></a>
## I05 — Remove manual machinery with its actual consumers

**Recommend · DDO-00/01/03/07/08/11 · DP-07/13/16/24, H4/H13/H27.**

The following replacements belong in the existing redesign, not a separate introspection platform.

| Responsibility | Selected replacement and retirement boundary |
|---|---|
| Owner/symbol/parameter duplication | Implementation-attached identity and extracted signature, feeding current generated call/native correspondence. Retain only genuinely non-derivable wire/nominal facts; retire independent signature registries. |
| Per-operation version/source_dependencies and helper relevance lists | Admitted implementation slice plus explicit non-Python determinants. Remove duplicated lists/manual behavior revisions only once complete replacement and consumers work. Broad runtime archive custody remains. |
| Method-name/getattr capability routing | Explicit operation-owned capability profile, checked against extracted methods/signatures and consumed by generated invocation. Discovery itself grants no effect or provider permission. |
| Bounded name-based consumer candidates | Scope/qualified-name/alias/member facts with original evidence and unresolved coverage. Retire duplicate lexical reconstruction; keep useful structural search as a candidate source where semantic resolution is unavailable. |
| Handwritten interface/documentation tables | Effective typed record plus structured prose rendering and comprehensive drift; one source-linked inspection owner. |
| Custom source rewrites/import handling | Conditional LibCST codemods where an actual migration requires preservation; keep adequate AST generation for new disposable source. |

Do not replace LinkML effective schemas, Pydantic runtime validation, native SQL constraints or
independent protected evaluation with Python source inference. Source discovery can preflight a
query plugin but cannot establish its live behavior/authorization without its admitted runtime
boundary. Add a new operation through its owned definition and actual algorithm, not a new central
scanner registration as well. If extension/brain code grows into a second bespoke semantic engine,
reduce the supported profile or retain simpler explicit facts rather than recreating the burden.

<a id="I06"></a>
## I06 — Use ty at supported inspection boundaries, retain current checker obligations

**Recommend public inspection route when consumed; no Rust embedding · DDO-03/10/12 · FP-02/07.**

Keep pyrefly as ordinary checker and preserve existing positive/negative generated-port, nominal-ID,
protocol and typed SQL tests. ty's installed CLI exposes `check`, `server`, `version` and `explain`;
use public LSP definition/declaration/implementation, references, call/type hierarchy, symbols,
hover/signature help for a concrete source-inspection consumer. Negotiate selected 0.0.102 server
capabilities; the older overview and current feature matrix disagree on some rename support.
[Public LSP](https://docs.astral.sh/ty/features/language-server/),
[CLI](https://docs.astral.sh/ty/reference/cli/).

Do not parse hover prose into the canonical contract when Griffe/Astroid already supply structured
facts. Internal Rust `SemanticModel`, `HasType`, reaching definitions and ty_ide exports are useful
research alternatives but lack a selected supported Python embedding contract; no custom Rust bridge
or fork is justified here. Salsa incrementality is engine preparation, not an exported operation
invalidation graph. A resident server earns use through repeated/interactive inspection, not merely
availability. No mandatory second whole-project checker campaign follows.

Targeted ty diagnostics and static expectations can clarify generated boundaries where pyrefly and
runtime validation leave a concrete question. Any future checker replacement needs actual-obligation
comparison, not diagnostic counts or speed headlines. No checker-rule changes are adopted here.

<a id="I07"></a>
## I07 — Qualify owned projections and lifecycle without adding proof machinery

**Recommend · DDO-01–12 · DP-06/09/23, CI-04/10/12.**

Use independent small source-change cases and selected real operations at foundation integration.
Cases must distinguish contract shape, compatibility, implementation revision and runtime custody.
Include inheritance, aliases, callback alternatives, mutable globals, defaults/decorators, assets,
async/generators, `.pyi` disagreement, metadata serialization and cache isolation. Failures of inference
remain explicit; an empty API-breakage report or successful type check cannot prove completeness.

Prefer one preparation lifetime per admitted source/configuration. Reuse parsed modules and selected
metadata; avoid serializing/parsing each library's entire model at every stage. A source-faithful
LibCST tree and a compact effective model have different consumers and lifetimes. Do not introduce
per-request whole-repository scans, simultaneous permanent four-engine mirrors, numerical cost
estimators, architecture lints or universal mutation-testing campaigns. Expected simplification
needs no benchmark; investigate serious actual regression uncertainty where it could change adoption.

Qualification follows existing package timing and final DDO-12 union. Actual provider/native behavior
and independent semantic expectations remain protected. No reference answers enter extraction or
identity selection. The source analyzer is itself an operation with explicit inputs/configuration /
outputs; this need not recursively introspect its own running implementation to a hash fixed point.

## Feature coverage, alternatives and conditional uses

The following completes the reference screening beyond selected mechanisms above. Conditional
features are not deferred mandatory DDO work. Their triggers identify when adoption would earn its
continuing burden. Each family retains library-native meaning; none is a universal behavior oracle.

| Library feature family and primary source | Disposition and conditions |
|---|---|
| LibCST `parse_module/expression/statement`, modern match/type-parameter/t-string/lazy-import nodes | Select supported source parsing as needed; retain byte encoding/module context. Grammar support is separate from metadata completeness, especially lazy imports. Parser target-version configuration is not independent interpreter validation. [Parser](https://libcst.readthedocs.io/en/latest/parser.html), [1.9.0 entrypoints](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/_parser/entrypoints.py). |
| LibCST scope/qualified names, positions, parents, LOAD/STORE/DEL, annotation accesses | Select source/binding evidence in I02. Not arbitrary attribute resolution or complete interprocedural effects. ByteSpan, line/column and LSP offsets differ. [Provider source](https://github.com/Instagram/LibCST/tree/v1.9.0/libcst/metadata). |
| LibCST batchable/custom providers, FullRepoManager, relative-module helpers | Select reusable analysis/context where needed. Explicit roots and source sets; no ambient acquisition. External Pyre TypeInferenceProvider is not ty or native LibCST inference; no new Pyre service selected. [Module helpers](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/helpers/module.py). |
| LibCST matchers, captures, sequence quantifiers, metadata predicates and ancestry decorators | Select declarative recognition for actual operation patterns; can remove nested visitor/state logic. Sequence matches are not implicit subsequences; callback ordering is not arbitrary sequencing authority. [Matchers](https://libcst.readthedocs.io/en/latest/matchers.html). |
| LibCST children/node-field filtering, evaluated literals, get_docstring, code_for_node, display/Graphviz | Select compact syntax/value/source evidence where useful. Not general constant propagation or semantic canonicalization. Display/Graphviz optional debugging only. [Helpers](https://libcst.readthedocs.io/en/latest/helpers.html), [node-field source](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/helpers/node_fields.py). |
| LibCST immutable transforms, with_changes/deep_replace, Removal/Flatten sentinels, template parsing | Conditional source-preserving migration/generation consumer. Respect node/field constraints and original versus updated metadata. Deep equality is structural, not behavioral equivalence. [Visitors](https://libcst.readthedocs.io/en/latest/visitors.html). |
| LibCST codemod context/composition, imports/exports/string annotations, ApplyTypeAnnotationsVisitor, RenameCommand and shipped modernization commands | Conditional actual DDO migration; reuse import coordination, strict source/stub matching and structured success/skip/failure results. No blanket NamedTuple/dataclass or string-format modernization: behavioral differences matter. [Codemods](https://libcst.readthedocs.io/en/latest/codemods.html), [shipped commands](https://github.com/Instagram/LibCST/tree/v1.9.0/libcst/codemod/commands). |
| LibCST parallel codemods, CodemodTest, experimental reentrant generation | Conditional multi-file migration with real exact-output expectations; instantiate per-file state appropriately. Experimental statement-level patch reuse has no current core consumer and no generic incremental parser guarantee. [Experimental contract](https://libcst.readthedocs.io/en/latest/experimental.html). |
| Astroid declarations/Arguments/type comments/doc_node/qname/module exports | Select effective callable and located declaration evidence. Exports may be dynamic; qnames are not stable semantic IDs. [4.3.4 node source](https://github.com/pylint-dev/astroid/tree/v4.3.4/astroid/nodes). |
| Astroid lookup/locals/assign_type/assigned_stmts/infer_lhs and inference contexts | Select binding provenance, refine only supported cases. Preserve ambiguous/uninferable/budget/error outcomes; assignment observation is not execution. [Protocols](https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/protocols.py), [inference](https://pylint.pycqa.org/projects/astroid/en/stable/inference.html). |
| Astroid MRO/ancestors/member origins/instances/bound methods/decorators | Select actual inherited adapter closure. Accessible versus locally declared member and receiver identity differ. is_abstract has heuristic behavior, not exact runtime ABC admission. [Scoped nodes](https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/nodes/scoped_nodes/scoped_nodes.py). |
| Astroid exclusivity/navigation, bool/getitem/iteration/operator errors, generators/yields | Conditional diagnostics or targeted refinement; no general path feasibility/lifecycle proof. Empty type_errors may reflect unknowns. Generator object and yielded values differ. [General API](https://pylint.pycqa.org/projects/astroid/en/stable/api/general.html). |
| Astroid brains/dataclass/attrs/typing, inference_tip, transforms, module extenders and failed-import hooks | Conditional recurring framework pattern when it removes real custom machinery. Narrow predicates, versioned modeled provenance and UseInferenceDefault; no broad new plugin interpreter. [Extending](https://pylint.pycqa.org/projects/astroid/en/stable/extending.html). |
| Astroid parse/build/manager/stub preference/modutils/caches | Select controlled supplied-source lifecycle; module loading/introspection can import code. Compare transforms-disabled structural view where modeled facts matter. Check cache/transform isolation and selected inference-order issue applicability before using consequential inference. [Builder](https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/builder.py). |
| Griffe objects/parameters/overloads/TypeAlias, alias paths/targets/reverse aliases, module collections/resolution | Select I01/I02/I04. Re-export exposure differs from declaration owner; unresolved alias sets cover attempted resolution only. [Models/navigation](https://mkdocstrings.github.io/griffe/guide/users/navigating/). |
| Griffe Expr.iterate, ExprCall/Subscript/Name, reference_path/Object.resolve | Select structured annotation/default/decorator references where sufficient. ExprName equality lacks lexical ownership; expressions are not a body call graph. [Expressions](https://mkdocstrings.github.io/griffe/reference/api/expressions/). |
| Griffe inheritance/dataclass synthesis, unpack_typeddict, merge_stubs | Select needed effective generated interfaces after actual-port fidelity checks; `.pyi` policy explicit. Preserve supplying owner, default factory, keyword-only/generic/overload semantics. [Built-in extensions](https://mkdocstrings.github.io/griffe/extensions/built-in/). |
| Griffe hooks/extra/model mutation, typed docstrings, native serialization/diff | Select thin operation extraction plus explicit effective-model export, final resolution and comprehensive drift. Native extra omission, cached parsed docstrings and selected breakage limits require I04's separate treatment. [Serialization](https://mkdocstrings.github.io/griffe/guide/users/serializing/). |
| Griffe LinesCollection/store_source/GitInfo/source_link/load_git, statistics/faster | Select source provenance where consumed. Git worktree loading/statistics/accelerators conditional; no ordinary compiler worktrees. prune-source/body omission conflicts with body-dependent analysis and AST hooks. Loader caching is not edit invalidation. [Git provenance](https://mkdocstrings.github.io/griffe/guide/users/how-to/set-git-info/). |
| Griffe Pydantic/typingdoc/generics/fieldz/framework extensions | Conditional actual unsupported model shape; qualify exact versions, Griffe2/Pydantic2 compatibility, static versus runtime import effects and explicit metadata export. No extensions installed/adopted by this review. [Extension catalogue](https://mkdocstrings.github.io/griffe/extensions/). |
| ty public hierarchy/references/definitions/implementation/symbols/signatures/hover | Conditional actual repeated operator inspection, I06. Selected 0.0.102 capability negotiation required; return structured evidence without treating prose display as canonical model. [LSP features](https://docs.astral.sh/ty/features/language-server/#feature-reference). |
| ty narrowing/Unknown/Any/intersection/negation/reachability/return inference | Conditional semantic assistance/conformance; explicit annotations retain their contract role. return-type-inference=always is opt-in, with async/generator limitations to check at selected version. Not effect/behavior proof. [Type system](https://docs.astral.sh/ty/features/type-system/), [configuration](https://docs.astral.sh/ty/reference/configuration/). |
| ty generated dataclass/PEP681/NamedTuple/TypedDict/enum/Pydantic interfaces and import/re-export/namespace/partial-stub resolution | Conditional targeted comparison when simpler extraction leaves a consequential unknown. Effective typed constructor does not establish runtime validators. Fix environment/Python/platform/stub scope explicitly. [Pydantic](https://docs.astral.sh/ty/features/third-party/pydantic/). |
| ty soundness/override/overload/cast/truthiness/awaitable/deprecation/sentinel/Pydantic-argument diagnostics | Conditional focused check, not automatic replacement/duplication of pyrefly. Distinguish assignability/subtyping and dynamic leakage. [Rules](https://docs.astral.sh/ty/reference/rules/). |
| ty assert_type/assert_never/reveal_type/static_assert, Intersection/JustFloat/JustComplex | Conditional independent type-contract cases; checker-specific runtime portability must be explicit, not introduced to domain annotations incidentally. [Typing FAQ](https://docs.astral.sh/ty/reference/typing-faq/). |
| ty server/watch/Salsa, SARIF/GitLab/JUnit/JSON rule explanations/baselines | Server only with actual repeated consumer; outputs are diagnostics, not full semantic graph exports. Baselines/preview features do not establish drift absence or data validity. Internal Rust embedding not selected. [CLI](https://docs.astral.sh/ty/reference/cli/). |
| ty pytest navigation/direct-dependency uv integration, rename/completion/autoimport/quickfix/notebooks/tokens/folding | Optional developer-tooling opportunities outside required DDO replacement. Fixture connectivity needs actual fixture/plugin scope; direct-dependency integration and rename require selected-version support. No new hook or gate. [pytest](https://docs.astral.sh/ty/features/third-party/pytest/). |

## Rule impacts, package integration and decisions

These are proposals for subsequent plan revision, **not new operator approvals or amended rules**.
Accepted original RC01–RC09 retain their identities. This review's RC IDs are source-qualified here.

| Impact | Current rule / proposed change / consequence if retained |
|---|---|
| RC01 | DDO-01 externally authored declarations as universal authority and no implementation discovery: admit closed implementation-owned definitions into the same IR. Preserve no ambient acquisition. If retained, limit I01/I05 to conformance and keep duplicated authoring burden visible. |
| RC02 | DDO-02/09 source-change exclusion/manual behavior revisions: permit admitted conservative implementation-slice revisions as recipe determinants. Preserve original runtime-provenance/reuse separation; DDO-00 assesses affected ADR0063/0060 successor wording. If retained, introspection only flags drift and automatic selective invalidation is not delivered. |
| RC03 | DDO-03 uniformly generated ports: allow the already authoritative typed Python invocation surface, generating required native/wire projections rather than redundant wrappers. If retained, keep generated ports and explicit correspondence, with extra generation burden. |

No proposal relaxes PostgreSQL admission, explicit selection, total governing model, protected
assessment, source custody or authentic execution attribution. A review of affected accepted ADR
wording belongs to adoption; this review changes no ADR. No rule impact is claimed merely for using
a library or adding an optional inspection consumer.

DDO-00 chooses owner/profile per actual operation and records accepted rule impacts. DDO-01–03
implement source acquisition, effective model, canonical slices and typed boundaries as one foundation.
DDO-04 preserves native admission; extraction never authorizes itself. DDO-05/06 consume actual bound
capabilities and determinant manifests rather than infer readiness from source calls. DDO-07/08 migrate
real families and retire duplicate registries/lists with consumers. DDO-09 integrates slice change /
substitution cutoffs; DDO-10 exposes derived contracts and evidence; DDO-11 preserves old archives;
DDO-12 qualifies the adopted union. NetworkX projection work composes with this scope without a new
scheduler, graph mirror or general analysis platform.

The highest-priority foundation question is whether one genuine operation can own its complete
contract and typed invocation without duplicate descriptions. Next establish dependency coverage on
an inherited operation and a small independently expected source-change matrix before admitting
slice-derived reuse. These are bounded acceptance investigations, not demands for universal proof.
If a selected framework cannot be modeled faithfully, retain an explicit opaque boundary or narrow
that profile; do not silently discard dependencies or fall back to whole-runtime equality.

## Evidence account and limits

**Interface-checked, 2026-11-12:** full references and decisive current source were inspected during
preparation/review. Installed source confirms Griffe serialization/extra limitations; official primary
metadata/inference/compatibility/LSP documentation was consulted. Root independently inspected the
runtime-custody/change-reporting, consumer-discovery, source-rewrite and Griffe serialization seams.
Contributors assessed ownership/fingerprint and library-integration alternatives; root retained mixed
ownership rather than making every operation implementation-owned.

**passed:** `uv run python -` distribution/version inspection selected LibCST1.9.0, Astroid4.3.4,
ty0.0.102, griffe/griffelib2.4.1 and pyrefly1.4.0. `uv run ty --help` confirmed public CLI routes.
These are availability/interface checks only. **not_run:** semantic probes, extraction integration,
LSP protocol negotiation, behavior-change matrix, tests/providers/native/database operations,
performance benchmarks. Source contracts were sufficient to choose the proposed architecture;
actual supported-profile coverage remains a stated implementation acceptance obligation. No speedup,
line-count reduction or complete Python dependency recovery is asserted as measured or tested.

The review is ready for selective plan revision, with RC01–03 explicitly resolved through the existing
operator decision route before dependent target changes are fixed. No standalone implementation,
checker migration, automatic reset, optional extension/backend installation or provider import is
authorized by publication. Historical data and all existing DDO obligations remain intact.
