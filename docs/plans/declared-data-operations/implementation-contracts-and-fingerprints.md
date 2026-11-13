# Implementation-owned contracts and operation fingerprints

**Accepted target with implemented DDO-01/02 foundations · 2026-11-12.** Integrates the
[Python-introspection review](../../plan_improvement_reviews/declared-data-operations-python-introspection_2026-11-12.md)
at `0907dcc23`, I01–I07. Its source-qualified RC01–03 were explicitly accepted by the operator on
2026-11-12. These differ from the original review's RC01–09 and the NetworkX I01–I07. The
[coordinator](../declared-data-operations_2026-11-12.md) owns scheduled disposition/progress and the
bounded implementation/qualification receipt. This companion owns shared authoring/extraction/fingerprint
contracts, not a second catalog or progress ledger. Apply core 3.3, heuristics, code-intelligence 1.4,
test-assessment 1.2 and repository binding. No production behavior is claimed by authoring.

Selected library inputs: LibCST 1.9.0, Astroid 4.3.4, Griffe/griffelib 2.4.1 and ty 0.0.102;
pyrefly 1.4.0 remains the checker. The operator's root manifest/lock additions establish workspace
availability. DDO-01 now declares those same exact LibCST/Astroid/Griffe versions in the production
package. ty remains optional tooling, not the checker. The admitted implementation uses static
Griffe/LibCST acquisition plus preparation-local Astroid structural binding refinement, without
inference, transforms or runtime import discovery. General framework models and broader contextual
dispatch remain unsupported until selected and qualified for actual adapter integration; required
unknowns withhold reuse identity. The coordinator distinguishes the successful real closed operation
from actual inherited-family extraction/refusal and future production admission.

<a id="I01"></a>
**Execution checkpoint · 2026-11-13:** integrated DDO-03–05 foundations are partially
implemented. The [coordinator checkpoint](../declared-data-operations_2026-11-12.md#ddo-0305-partial-implementation-checkpoint--2026-11-13)
owns delivered behavior, exact qualification and all remaining functional scope. The target below
continues to govern unfinished work; this companion is not a second completion ledger.

## Authoring authority and effective model — I01

DDO-00 inventories the actual semantic owner of each supported operation. Externally defined
protocols/model semantics keep declaration-owned contracts and implementation conformance. Coupled
Python algorithms use an implementation-owned typed operation class with colocated domain metadata;
a typed function can supply a simple algorithm under the same profile. Helpers remain internal
dependency nodes unless they genuinely own separate domain semantics. Neither a helper nor its
contract projection creates a task, process, table or persisted product automatically.

DDO-01 supports a closed static authoring pattern: typed records, literals and qualified references
attached to actual implementation definitions. It does not execute arbitrary decorators/configuration
expressions to discover meaning. Stable semantic IDs remain explicit. Extract callable shape and
origin from implementation; author applicability, role/cardinality/source/support/coverage/outcome /
effect/lifecycle/numerical/asset meaning once beside the owner where types cannot establish it.
Never duplicate parameter/default lists in another YAML catalog or infer effects from call names.

Both frontends produce the same immutable effective operation/kind/binding IR. Each field retains
its source and origin category: authored, mechanically extracted, inferred or extension-modeled.
The IR is the compiler product consumed by identity, generated native/wire correspondences,
documentation, explanations and execution. It is not independently editable. An inherited method's
supplying declaration differs from the public subclass/exposed alias; both must remain inspectable.
Nominal domain identifiers do not become interchangeable merely because Python represents them as int.

### Consumed and delivered products

| Product | Meaning, owner and consumers |
|---|---|
| Captured source/extraction context | Exact source bytes, logical package roots, supplied dependencies/stubs, selected models/extensions/configuration and interpreter assumptions; DDO-01 acquisition, archived interpretation |
| Effective operation facts | One authored owner per semantic fact plus extracted callable/member structure and located correspondence; DDO-01, consumed by DDO-02/03/07/08/10 |
| Implementation slice | Finite rooted normalized definitions, typed dependency edges, explicit opaque boundaries and coverage/admission result; DDO-01/02, consumed by recipes/change |
| Native/wire correspondence | Necessary nominal/source/result mapping and ingress/permission checks; DDO-03/04, not a duplicated Python signature |
| Drift/inspection projection | Separate contract, compatibility, documentation, implementation revision and runtime-custody changes; DDO-09/10, same pinned production read owner |

No public wire schema or new service is invented by these conceptual products. Extend existing
normalized/typed boundaries. Source-derived discovery never authorizes execution or publication.

<a id="I02"></a>
## Closed extraction and library responsibilities — I02

Acquire immutable supplied sources before semantic preparation. Analyze captured bytes at release /
preparation time, not on every result read. Archive effective facts and source interpretation so
old products never reopen current installed code. Default target analysis is static; runtime plugin
loading retains its separate admitted boundary. No provider imports, implicit downloads or ambient
search path discovery are part of this compiler route. Trusted extraction libraries/extensions have
explicit identities; they must not import target implementations as an extraction shortcut.

### Griffe 2.4.1: interface, ownership and metadata

Call `griffe.visit(module_name, filepath, code, *, extensions, parent, docstring_parser,
docstring_options, lines_collection, modules_collection)` with the admitted module code and explicit
logical hierarchy/collections. It compiles/parses source into `Module`, `Class`, `Function`,
`Parameter`/`Parameters` and type-alias objects without executing target module code. Parameter kinds,
default expressions, overloads and annotations supply actual callable shape. Direct visit avoids the
ordinary loader's inspection fallback and source-search behavior.
[API](https://mkdocstrings.github.io/griffe/reference/api/agents/),
selected installed source `griffe/_internal/agents/visitor.py:94–143` (2.4.1).

Register admitted modules/parents before cross-module resolution. `GriffeLoader.resolve_aliases`
accepts `implicit`, `external` and `max_iterations`, returning unresolved alias paths and iteration
count. Use `external=False` and a bounded pass over the supplied collection; select implicit alias
coverage deliberately. The result describes attempted alias resolution, not every body dependency.
`Alias.path`, `target_path`, `canonical_path`, `final_target` and reverse aliases distinguish exposed
names from declaration owners. `members`, `inherited_members`, `all_members`, `resolved_bases` and
`mro()` preserve inherited origin. Do not flatten accessible members into locally authored definitions.
[Loader API](https://mkdocstrings.github.io/griffe/reference/api/loaders/),
[navigation](https://mkdocstrings.github.io/griffe/guide/users/navigating/).

Use `Expr.iterate(flat=False)`, `ExprName.reference_path`, resolved names and `Object.resolve()`
for annotation/default/base/decorator references. Same-spelled ExprNames are not identity without
lexical context. Griffe's function-interface extraction is not a body dependency graph; use the
source/binding analyses below. Built-in dataclass synthesis, optional `unpack_typeddict` and explicit
`merge_stubs` earn use for actual generated ports; preserve inheritance, default factories,
keyword-only fields and source-versus-stub policy.
[Expressions](https://mkdocstrings.github.io/griffe/reference/api/expressions/),
[built-in extensions](https://mkdocstrings.github.io/griffe/extensions/built-in/).

A thin `Extension` recognizes the admitted operation metadata pattern through `on_function_node`,
`on_function_instance` and corresponding class/model hooks. Resolve whole-collection references in
an explicit later pass; completion/load hooks are not final resolution guarantees. Export meaningful
metadata into the typed effective IR explicitly: installed 2.4.1 `Object.as_dict` omits `extra`,
even with full JSON, and serializes members as mappings. Native dumps are neither complete operation
exports nor canonical identity bytes.
[Extensions](https://mkdocstrings.github.io/griffe/guide/users/extending/),
[serialization](https://mkdocstrings.github.io/griffe/guide/users/serializing/),
selected installed source `griffe/_internal/models.py:1338–1364` (2.4.1).

**Implemented foundation adjustment · 2026-11-12.** The closed frontend reads the admitted literal
metadata pattern from the same wrapped LibCST syntax used for dependency analysis, rather than
registering a second Griffe extension visitor. Griffe still owns exposed/callable/C3 facts;
explicit effective-model export retains every metadata field and its supplying/exposed origin.
This avoids two recognition passes and an extension lifecycle without losing metadata custody or
making library-native serialization authoritative. A Griffe extension remains available when an
actual supported pattern needs its model hooks.

### LibCST 1.9.0: source/binding evidence and conservative projection

`parse_module` retains source/encoding/formatting. `MetadataWrapper.resolve_many` and batched visitors
share required provider work. Metadata keys refer to wrapped nodes, not nodes from the original
pre-wrapper tree; wrappers copy by default. Recompute after transformations instead of attaching
stale facts to replacement nodes. `ScopeProvider` assignments/references and Access.referents expose
lexical candidates; `QualifiedNameProvider` distinguishes local/import/builtin origins and can return
multiple names. `FullyQualifiedNameProvider`/`FullRepoManager` add explicit repository module context.
These are lexical relationships, not proof of runtime dispatch.
[Metadata API](https://libcst.readthedocs.io/en/latest/metadata.html),
[1.9.0 provider source](https://github.com/Instagram/LibCST/tree/v1.9.0/libcst/metadata).

Use Position/ByteSpan/ParentNode/ExpressionContext providers where source evidence requires them;
LOAD/STORE/DEL, annotation references and arbitrary object-member access have different meanings.
Byte spans, line/column and LSP UTF-16 coordinates need explicit conversion. `libcst.matchers`
metadata predicates, captures and `extractall` replace nested bespoke recognition for supported
operation patterns. Sequence quantifiers must express extra arguments explicitly; callback ordering
is not an implicit orchestration policy.
[Matchers](https://libcst.readthedocs.io/en/latest/matchers.html).

`get_node_fields`/`filter_node_fields`, lexical `children` and evaluated literal values help construct
a normalized definition projection. Field-category filters are not semantic-equivalence rules;
DDO's typed canonical codec owns identity. `get_docstring` extracts prose, while Griffe supplies
structured sections. Preserve original source alongside normalized facts for diagnostics/custody.
[Node-field source](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/helpers/node_fields.py),
[nodes](https://libcst.readthedocs.io/en/latest/nodes.html).

### Astroid 4.3.4: supported resolution refinement

Use supplied-source `parse`/`AstroidBuilder` with selected transform/stub policy; do not allow manager
module lookup to escape the admitted source/environment. `lookup`, `.locals`, `assigned_stmts` and
assignment protocols supply binding provenance. `infer`, `InferenceContext`, `CallContext`, bound
methods and `infer_call_result` refine supported targets/values. MRO/member-origin/decorator APIs
connect inherited implementations and effective class configuration. Preserve all candidates,
Uninferable, failures and budget/coverage limits with source and analysis-model provenance.
[Builder](https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/builder.py),
[protocols](https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/protocols.py),
[contexts](https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/context.py),
[class API](https://pylint.pycqa.org/projects/astroid/en/stable/api/nodes/astroid.nodes.ClassDef.html).

Successful singleton inference is not evidence of exhaustive targets. Supported binding/dispatch
forms and explicit boundaries must justify closure independently of whether inference reports an
unknown. Unsupported reflection/mutation/dynamic loading cannot become complete because infer
returned one object. Shared manager cache/transform state has a preparation-scoped lifecycle;
qualify isolation/order behavior before consequential reuse. Brains/custom `inference_tip`,
`UseInferenceDefault` and module extenders are conditional models for recurring unsupported shapes,
not a second authored domain catalog.
[Manager](https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/manager.py),
[extensions](https://pylint.pycqa.org/projects/astroid/en/stable/extending.html).

<a id="I03"></a>
## Implementation slice and identity policy — I03

DDO-01/02 compile a finite dependency graph rooted at the actual operation's semantic entry points.
Use the existing [graph contract](graph-projections-and-analysis.md), adding distinct lexical,
possible-call, resolved-definition, type-reference and implementation-determinant edge meanings.
A possible call is not a data input, sufficient support or readiness edge. Preserve supplying owner,
role and source evidence. Canonical records sort stable references and retain cycles finitely,
without recursive hash fixed points or incidental NetworkX component IDs.

| Determinant | Required coverage/admission behavior |
|---|---|
| Direct/imported/aliased calls | Resolve declaration targets and include all admitted possibilities, preserving evidence |
| Inherited methods/descriptors/super/class values | Include supplying definitions, relevant bases and receiver/configuration assumptions |
| Callbacks/registries | Closed permitted target population or explicit bound implementation input; no first-inferred-target shortcut |
| Globals/closures/defaults/decorators | Captured immutable values/definitions and definition-time expressions; mutable/environmental inputs modeled explicitly |
| Generated framework behavior | Selected versioned analysis model plus actual field/decorator facts; synthetic origin remains explicit |
| SQL/grammar/template/model/native/provider assets | Explicit captured opaque boundaries and semantic roles; existing language-specific ownership preserved |
| Reflection/source readers/dynamic loading | Justified bounded universe or explicit complete coarse boundary; otherwise reusable-recipe completeness refuses |

For supported profiles, versioned canonical implementation revision becomes an explicit recipe
determinant. Keep domain contract identity, implementation revision and exact execution attestation
separate. A helper/body repair can change the recipe without a manual version increment or signature
change. A new unrelated function outside the closure does not automatically do so. An explicitly
coarse module boundary may conservatively include extra changes; no hidden whole-runtime fallback.
Runtime input unknowns remain modeled operation outcomes; unknown required recipe determinants are
a different admission problem and prevent claiming complete reusable identity.

Normalize conservatively: ignore formatting/comments/positions only under profiles that do not
observe them; source-sensitive readers bind exact source. Retain names, statement/control order,
literals, default/decorator expressions and dependencies. Retain docstrings/annotations by default
because reflection/evaluation may observe them. No alpha-renaming, constant folding, dead-code removal
or inferred-output substitution. LibCST field helpers and Astroid inference assist extraction, not
universal behavior equivalence. Do not hash whole Griffe JSON, Astroid as_string/eq or ty engine state.

Archive normalization specification, meaning-bearing analysis assumptions and effective graph. Tool
run/version provenance alone is not a new recipe salt: an extractor change affects recipes through
changed effective determinants or an explicitly changed interpretation rule. Bootstrap compiler /
extractor behavior through an explicit interpretation contract; do not recursively introspect its
currently running implementation to a self-referential hash. Archived interpretations stay readable.

DDO-09 distinguishes changed implementation revision from proven changed outputs. Recompute only
requested affected operations under native demand; stop downstream propagation at equal admissible
value/support. Historical products and producing episodes stay intact. Conservative recomputation
on some harmless refactors is acceptable; missing a relevant change is not. No destructive reset,
whole-package code equality or claim of universal semantic equivalence follows.

<a id="I04"></a>
## Ports, documentation and drift — I04

DDO-03 uses the authoritative typed Python invocation directly where suitable; generate only needed
native/wire/protocol correspondences from effective facts. Declaration-owned operations still receive
generated boundaries and implementation conformance. Preserve existing nominal IDs, immutable input
ownership and strict Pydantic/native ingress. Extracted discovery is not capability admission.

DDO-10 renders parameter/default/type/role/outcome documentation and source-linked connectivity from
the same effective model. Griffe `Docstring.parse`/typed sections enrich colocated prose from final
parent signatures; parse after enrichment because `parsed` caches results. Emit pinned detached DTOs
through the existing native/ci/MCP read owner, preserving exact source/snapshot and unknown standing.
[Docstrings](https://mkdocstrings.github.io/griffe/reference/docstrings/).

Compare full effective records for additions/removals/changes; classify callable contract, domain
obligations, documentation, implementation revision and runtime custody separately.
`find_breaking_changes` yields structured `Breakage` objects for selected asymmetric API breakages,
not complete drift, behavior equality or safe reuse. Use container scope deliberately; empty output
cannot prove unchanged functions. Preserve unsupported type/value/body changes in the comprehensive
comparison. [Checking](https://mkdocstrings.github.io/griffe/guide/users/checking/).

<a id="I05"></a>
## Consumer migration and retirement — I05

DDO-00 inventory and DDO-07/08 migration cover `semantic/contracts.py` implementation approval,
owner/symbol/call fields and manual source capture, inherited methods and source_dependencies,
getattr-based capability discovery, `schema/model_discovery.py` consumer candidates and source/model
inspection callers. Replace actual duplicated shape/connectivity/version logic with the shared
compiled products, together with immediate consumers. Keep broad runtime archive custody, explicit
non-Python semantic assets, native permission checks and independent reference expectations.

One real simple operation and the inherited interpretation family establish the two authoring
shapes before broad migration. Native provider configuration/source/support semantics remain explicit
inputs. Existing AST generation, Pydantic/LinkML inspection and SQL parsers stay where adequate;
introspection is not permission to rewrite every scanner or replace domain language extraction.
LibCST codemods/import coordination are conditional migration tools where preservation is necessary,
not mandatory source modernization or a new alignment lint.

<a id="I06"></a>
## ty and conditional capability selection — I06

Keep pyrefly 1.4.0 and its existing positive/negative generated-consumer checks. ty 0.0.102 offers
public `server`/LSP definition, declaration, implementation, references, call/type hierarchy, symbols,
hover and signature help for an actual inspection consumer. Negotiate selected capabilities; do not
persist parsed hover prose as canonical facts. A resident server requires a repeated/interactive
consumer, not merely the existence of incrementality.
[Public LSP](https://docs.astral.sh/ty/features/language-server/),
[CLI](https://docs.astral.sh/ty/reference/cli/).

No ty internal Rust/Salsa integration, extra whole-project checker campaign or replacement of
pyrefly is scheduled. Conditional targeted diagnostics/static expectations can resolve a real typed
boundary uncertainty; their outputs are not complete dependency graphs or operation identity.
The following catalogue preserves all reviewed feature selections and limits. Conditional entries
are static design dispositions, not additional pending DDO-12 obligations. Adopt only through an
identified consumer, selected-version API check and focused semantic qualification.

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

<a id="I07"></a>
## Investigations, readiness and qualification — I07

| Package and deciding question | Settling evidence and dependent boundary |
|---|---|
| DDO-00/01: can one actual operation own its contract and invocation without duplicates? | Map a simple algorithm and inherited interpretation family through the closed authoring pattern. Independently expected parameter/domain/capability facts must feed invocation, inventory, docs and native correspondence before broad DDO-07/08 migration. |
| DDO-01/02: is dependency coverage justified for the admitted profile? | Independently expected slices for alias/re-export, helper, base/super, callback alternatives, globals/defaults/decorators and explicit assets. Inference success alone is insufficient; unsupported forms require explicit boundaries or refuse reusable admission. |
| DDO-01/03: are extraction/resolution/export faithful? | Supplied-source fixture whose import would fail; multi-module hierarchy and bounded aliases; generated dataclass/keyword/default-factory/overload/Annotated/generic/TypedDict fields; metadata export and source/stub disagreement. Missing meaningful extra fields block dependent boundary generation. |
| DDO-02/09: do change identities have the intended locality? | Independently expected contract/revision/recipe/custody outcomes for helper-body, inherited-value/default/asset changes versus unrelated/comment/format changes; source-reflection restrictions, cycles and normalization version. No universal refactor invariance requirement. |
| DDO-01/10: is interpretation/lifetime pinned? | Cache/transform/configuration isolation across release/order changes, final-signature docstring enrichment, old archived interpretation and correct source/byte spans. No current-code reinterpretation. |
| DDO-03/04/10: do direct ports preserve enforcement and served facts? | Existing nominal/protocol/strict-ingress/native refusals plus pinned native/ci/actual MCP/export explanations. Static preflight never grants effect/source permissions. |

These investigations belong within the existing packages, not a new plan series or DDO-13. DDO-01
first produces effective owner facts and closed preparation; DDO-02 consumes their stable references
and qualifies normalization/identity; DDO-03 consumes actual working facts/identities for direct or
generated correspondence. Design can overlap; runtime integration requires working native DDO-04
contracts. DDO-05/06 consume admitted determinant manifests and capability profiles, never infer
sufficiency from call connectivity. DDO-07/08 deliver replacements and consumers; DDO-09/10 integrate
change/inspection; DDO-11 preserves old immutable interpretations and retires duplicate authority.

During implementation, use focused compiler/boundary/native controls with independently authored
expected facts, graph memberships, bytes and refusals. Griffe roundtrip, regeneration agreement or
a type-check pass alone is insufficient. DDO-12 includes adopted cases in its final-source required
union, with real provider/native behavior and protected source/prediction separation preserved.
Changed recipes may recompute an operation and still stop at equal downstream value/support.
No benchmark, four-engine voting, architectural lint, recursive self-proof or compulsory optional-tool
campaign is introduced. Share preparation, parse only needed sources/providers and serve archived
compact products; do not retain permanent four-engine mirrors or reparse on every inspection.

**Evidence:** API contracts were Interface-checked by source inspection in the review on 2026-11-12;
plan preparation additionally checked installed Griffe visit/resolution/serialization signatures.
Semantic probes, extraction integration, native/provider/product tests and benchmarks are **not_run**
for authoring. All tests and investigations above are future implementation obligations, not receipts.
