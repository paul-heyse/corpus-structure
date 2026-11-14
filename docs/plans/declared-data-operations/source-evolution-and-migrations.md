# Source evolution and model-driven migrations

**DDO-03 preparation implemented; later caller/interface migrations Proposed · 2026-11-13.** Develops source-effect
preparation in DDO-03, actual caller replacement in DDO-07/08, public model-update interfaces in
DDO-10 and preservation/qualification in DDO-11/12. The
[coordinator](../declared-data-operations_2026-11-12.md) alone owns progress and disposition.
Consumes [ast-grep review I01–I06](../../plan_improvement_reviews/declared-data-operations-ast-grep_2026-11-13.md)
at `2e88d02db`. The operator selected full integration on 2026-11-13, preserving conditional
capabilities as conditional. The coordinator owns the resumed DDO-00–05 execution and its scoped acceptance.

## Purpose, foundations and authority

Deliver two related capabilities: finite source migrations that complete the DDO replacement,
and repeatable operator-requested model updates through existing `ci model change preview/apply`.
Apply core 3.3, efficient-architecture heuristics, code-intelligence 1.4 and test-assessment 1.2.
FP-04/DP-01 govern update direction; DP-08/15/19 govern transformation fidelity and publication;
FP-06/07 and H4/H12/H16 favor complete library delegation and reuse of existing preparation.

**Interface-checked baseline · 2026-11-13:** `schema/model_change.py` already owns exact inputs,
`FileEffect`, preview staleness, writer locking, temporary-file replacement and retry of settled
after-bytes. Its generator fingerprint covers schema implementation files. It does not yet own
the source migrations described here. `semantic/data_operation_artifacts.py` already generates
authenticated archive calls/IDs/schemas from effective definitions and resolved correspondences;
those products do not need checkout materialization. `operation_call_generation.py` supplies the
shared emitter. `ClosedPythonSources` supplies logical module/source context with LibCST metadata,
Griffe declarations and bounded Astroid resolution. Existing consumer discovery is bounded
candidate evidence, not complete rename authorization. Concurrent infrastructure and native PDF
work must be reacquired before implementation; it is not qualification for this amendment.

The [implementation-contracts companion](implementation-contracts-and-fingerprints.md) keeps
semantic fact ownership, extraction, recipe and runtime-authentication rules. Change an authored
definition, recompile its effective product, regenerate derived outputs, then migrate affected
handwritten consumers. Implementation-owned Python facts cannot be rewritten merely because a
derived model differs; an explicit requested source change must authorize that direction.
External protocols retain their declaration authority. Neither matcher dictionaries nor generated
stubs become a second editable operation/domain model.

The source-update operation is developer/operator model maintenance. It does not enqueue corpus
analysis, perform inference, publish products, deploy a release or reinterpret historical data.
CA-01 builtin closure, CA-05 population context and CA-06 projection interpretation retain their
existing semantic repair owners. A syntactic match cannot settle those obligations.

## Consumed and delivered interface

Extend the existing typed change request with an optional finite source-migration selection.
Each selection identifies the supported transformation, authored owner/revision, explicit old→new
semantic/interface correspondence and required source-consumer universe. Use ordinary typed records
and named implementation functions; no user-supplied executable matcher DSL or plugin registry.
Existing requests without source migrations keep their existing meaning.

Preview delivers candidate authored source, actual checkout-generated effects and structured
per-migration/per-consumer outcomes. Distinguish changed, already satisfied, intentionally excluded,
ambiguous, unsupported and unresolved consumers. A required unresolved/ambiguous/unsupported consumer
prevents application of that coherent migration. Its proposed effects remain inspectable; partial
recognition cannot silently become a complete update. A resolved unchanged consumer is distinct
from a skipped one. Manual resolution changes inputs and requires a fresh preview.

Use existing `FileEffect` for writes. Add source-migration outcome and source-universe premises to
the preview's typed products rather than building another edit lifecycle. Keep generated release
artifacts under normal preparation and `verify_release_products`; only real checkout consumers
become file effects. Generated source is regenerated through its renderer, never patched by CST
or text replacement. File deletion is not initially supported by this source-migration contract;
retire declarations/imports within files. If an actual consumer retirement needs deleting a whole
file, extend the existing effect owner deliberately before claiming that migration complete.

Initially support UTF-8 Python and finite named transformations. Preserve comments, newline style,
literal/source details and unrelated code as required by the selected transformation. Reject an
unsupported encoding rather than silently reencode it. A parameter rename, signature reshape and
behavior change have different applicability contracts; none is inferred from textual similarity.

## Preparation, coverage and publication

1. Acquire the explicitly selected authored inputs, logical module/import context and consumer
   source universe through the existing source owners. Define its roots/exclusions and required
   consumer population from the actual operation/adapter inventory, including relevant new files;
   do not equate a bounded discovery result with all callers.
2. Qualify semantic eligibility using owned correspondences and available scope/name facts.
   Dynamic dispatch, ambiguous referents or unavailable authentic context produce explicit
   unresolved outcomes. Preserve supplying versus exposed inherited owners and role multiplicity.
3. Execute the selected programmatic transformation against immutable acquired source, returning
   candidate after-source and warnings/outcomes. Reparse/reacquire metadata between dependent
   passes. Reuse preparation for independent analyses of the same snapshot; do not run a second
   parser on every already prepared Python module by default.
4. Compile against the proposed snapshot, including any changed implementation recipes and
   generated correspondences. Validate intended old→new domain meaning and required consumer
   coverage, not merely output syntax or agreement between two generated representations.
5. Compose ready checkout effects into the ordinary preview. Bind edited inputs, all source/import
   facts used to justify eligibility, source-set membership, transformation bytes/options and
   selected library identity. Extend staleness coverage beyond the current schema-only generator
   fingerprint. Recheck additions/deletions in the selected source universe; hashing only files
   already found cannot detect a newly added caller.
6. Existing apply owns writes after its normal workspace, HEAD, input and toolchain checks. Keep
   per-file atomic replacement, exact before-byte refusal and retry of already settled after-bytes.
   A mid-apply failure may leave settled files; this is not multi-file atomicity. External editors
   need not honor the writer lock, so retain per-file concurrent-edit checks and honest recovery.

Discovery, semantic eligibility, syntax transformation, compilation and effect publication have
different responsibilities. Compose their existing owners; do not persist a universal edit IR,
second journal, watcher or independent source-update transaction system.

## Selected library mechanisms and required contracts

LibCST 1.9.0 is the selected Python transformation substrate. These references supply enabling
details, not permission to infer domain behavior from syntax. Ast-grep 0.51.2 is the researched
binding version, not a selected Python dependency. Griffe/Astroid/conditional ty roles and the
pyrefly checker remain with their existing owners.

| Mechanism | Supplies / retained obligation | Detailed reference and acceptance |
|---|---|---|
| `transform_module`, `TransformSuccess/Failure/Skip/Exit`, `SkipFile` | Programmatic candidate source and structured outcomes without delegating writes. Map warnings/refusals into preview; a skipped required site blocks readiness. | [1.9.0 runner](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/_runner.py), [codemod API](https://libcst.readthedocs.io/en/latest/codemods.html). Check success, warning, intentional skip and failure retained through preview. |
| `CodemodContext`, context-aware commands/transformers | Filename/module/package, metadata and invocation-local scratch; reuse native composition and fresh wrapper lifecycle. Do not share stateful instances across parallel file work or reuse old node metadata after replacement. | [Context](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/_context.py), [lifecycle](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/_codemod.py). Check per-file isolation and dependent reparsed passes. |
| `RenameCommand` with qualified-name metadata | Eligible symbol moves, names/attributes and import-related aliases. Qualified-name membership is not proof of unique binding; signature/body migration remains separately authored. | [Rename implementation](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/commands/rename.py). Check imported aliases, re-exports, local shadows and ambiguous negative cases. |
| `AddImportsVisitor`, `RemoveImportsVisitor`, command import methods | Coordinated import addition/removal; native command helpers add before removing. Node-based removal uses the original node, with correct relative module/package context. | [Command helpers](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/_command.py), [removal visitor](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/visitors/_remove_imports.py). Preserve needed exports/string annotations; do not invent star-import resolution. |
| Matcher captures/metadata predicates and `parse_template_*` | Structural construction with inserted CST nodes, preserving explicit eligibility and module parsing conventions. Templates do not infer target operation semantics. | [Matchers](https://libcst.readthedocs.io/en/latest/matchers.html), [template helpers](https://libcst.readthedocs.io/en/latest/helpers.html). Independently check exact source for arguments, defaults, decorators and multiline/comment cases. |
| `ScopeProvider`, `QualifiedNameProvider`, `FullyQualifiedNameProvider`, expression/position metadata | Qualified lexical facts and source correspondence within supported scope. Preserve unknown runtime dispatch/attributes and logical module identities. | [Metadata](https://libcst.readthedocs.io/en/latest/metadata.html), [module helpers](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/helpers/module.py). Check alias/shadow/inherited-owner distinctions; node handles never become semantic IDs. |
| Explicit `ApplyTypeAnnotationsVisitor` stage with `store_stub_in_context` | Reconcile authoritative annotation inputs and coordinated imports using an ephemeral model-derived stub. It does not reshape parameters or migrate callers. Stub storage does not automatically schedule the annotation visitor. | [1.9.0 implementation](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/visitors/_apply_type_annotations.py), [upstream tests](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/visitors/tests/test_apply_type_annotations.py). Resolve the version-specific question below before use. |
| Existing ast-grep CLI / bounded `locate_consumers` | Finite structural candidate discovery where it removes manual search. Keep attributed matches, examined scope and unknowns. No standing alignment lint or new scanner. | [CLI search](https://ast-grep.github.io/guide/quick-start.html), [rule reference](https://ast-grep.github.io/reference/rule.html). Check that same-spelled syntax is not counted as an eligible semantic caller. |

### Pivotal questions and settling evidence

The following questions constrain adoption, not completion of unrelated packages:

- **Annotation route:** tagged 1.9.0 source initializes `tree_with_imports` conditionally on stub
  context before later use. Bare explicit `Annotations` construction is not a confirmed route.
  Select the explicit context-stub visitor stage and qualify it with a focused conflict/import/
  repeat-application case. If that supported route fails, inspect a narrow upstream correction or
  deliberately selected version change; do not build a replacement annotation engine or silently
  claim annotation support. The stub stays disposable and has no independent semantic authority.
- **Required consumer universe:** specify actual roots, inclusion/exclusion and external/dynamic
  boundaries for each migration before implementation. Independently test a newly added caller
  and a removed caller after preview. Unknown outside coverage cannot become proven absence.
- **Initial caller context:** the M1 target selection route requires model/binding, demand/read
  identity, trust snapshot and byte bound. DDO-06/07 must provide these authentically before the
  source migration is eligible. No guessed context, default subject or method-name exception in
  the common orchestrator can bridge the gap.
- **Optional embedded ast-grep:** adopt only for an actual supplied-snapshot consumer whose native
  structural queries remove material custom work. Compare LibCST-only, existing CLI and embedded
  binding routes. Absence of that consumer leaves the Python dependency unselected.

## Conditional capability coverage

Every family in the review has a disposition here. Conditional rows require the named consumer
and qualified contract, not an automatic research project, dependency or DDO-12 campaign.

| Capability family | Selection / trigger, limits and detailed reference |
|---|---|
| Ast-grep `SgRoot`, node fields/children/siblings, named/unnamed nodes and source inspection | Conditional embedded syntax consumer; `is_named_leaf` is grammar-specific, not simply named-and-leaf. No semantic ontology or stable serialization from display strings. [Python API](https://ast-grep.github.io/guide/api-usage/py-api.html), [tagged nodes](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/pyo3/src/py_node.rs). |
| Contextual/effective-node patterns, selectors and single/anonymous/variadic metavariables | Conditional I03 discovery; state expression/statement granularity and distinguish concrete separators/comments from logical arguments. [Pattern syntax](https://ast-grep.github.io/guide/pattern-syntax.html). |
| `cst/smart/ast/relaxed/signature` strictness | Conditional recognition contract only; never substitute for DDO canonical implementation equivalence. [Pattern object](https://ast-grep.github.io/reference/rule.html#pattern). |
| Atomic/composite/positive rules, mapping-based `not` | Conditional native syntax predicates. `all/any` operate on one candidate; negation does not establish positive captures. [Rule semantics](https://ast-grep.github.io/reference/rule.html). |
| Declarative relations, `stopBy`, fields versus imperative refinement | Qualify neighbor/default depth versus recursive/ancestor/all-sibling imperative behavior. Field support is relation-specific. [Relations](https://ast-grep.github.io/guide/rule-config/relational-rule.html), [core nodes](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/core/src/node.rs). |
| `nthChild`, filtered/reverse positions, limited ESQuery selectors | Conditional ordered-shape query; named sibling counts differ from concrete children and filtered populations. [Rule reference](https://ast-grep.github.io/reference/rule.html). |
| Utilities, recursive structural predicates and capture constraints | Local structural factoring with progress/base cases; no same-node cycles, assumed variadic constraints or second domain registry. [Utilities](https://ast-grep.github.io/guide/rule-config/utility-rule.html), [configuration](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/config/src/rule_core.rs). |
| Ordered cross-structural unification, match environments and navigation | Conditional repeated syntactic correlation. Evaluation order and fresh environments matter; syntactic names are not resolved symbols. [NodeMatch](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/core/src/matcher/node_match.rs), [Python API](https://ast-grep.github.io/guide/api-usage/py-api.html). |
| Replace/substring/chained transforms, case conversion and separators/acronyms/digits | Conditional mechanical text derivation from the existing naming authority. Qualify regex/capture locality and selected version's case segmentation. [Transformations](https://ast-grep.github.io/reference/yaml/transformation.html). |
| `replace`, mutable `Edit`, root/subtree `commit_edits` | Conditional local nonoverlapping edits only. Replacement is literal; overlaps can be silently skipped and no applied-edit account is returned. Reject conflicts and order same-offset insertions, or reparse between passes. [Tagged Python editing](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/pyo3/src/py_node.rs). |
| Python typing/runtime options, CLI fixes and rewriters | Check actual release implementation; Python `Config` lacks the full fix/rewriter registration route. No assumed CLI capture interpolation or recursive rewrite support. [Python declarations](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/pyo3/ast_grep_py/__init__.py), [full configuration](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/config/src/rule_config.rs). |
| Built-in/dynamic grammars, custom sigils/extensions, embedded languages and diagnostic-guided edits | Conditional on a substantially affected consumer. Pin native grammar provenance, explicit region extraction and coordinate translation. Diagnostic-guided edits need attributed diagnostics bound to that snapshot; Python does not inherit complete CLI injection/LSP machinery. [Custom languages](https://ast-grep.github.io/advanced/custom-language.html), [Python binding](https://github.com/ast-grep/ast-grep/tree/0.51.2/crates/pyo3). |
| Parse recovery, missing/error syntax, coordinates and distribution evolution | Successful matching is not validity. Python lacks the core's complete error/missing status interface; character offsets differ from bytes/UTF-16. Use the selected language parser/compiler and snapshot owner. [Range](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/pyo3/src/range.rs), [Unicode conversion](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/pyo3/src/unicode_position.rs). |
| Native matcher construction, eager result lists, concurrency and tree lifetime | Batch useful queries/release roots; no assumed public compiled matcher cache, incremental parser or inherited CLI scheduler. No persistent service without a repeated consumer. [Tagged implementation](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/pyo3/src/py_node.rs). |
| LibCST literal/docstring/field inspection and modern grammar | Reuse where actual source inspection needs it. Match statements, generics, template strings and lazy imports require separate parser/metadata/codemod coverage; no blanket modernization. [Nodes](https://libcst.readthedocs.io/en/latest/nodes.html), [field helpers](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/helpers/node_fields.py). |
| LibCST shipped modernization, FullRepoManager/batched visitors/external type metadata | Conditional actual migration/repeated context only. Keep ty's existing public role and pyrefly; no new external type service or broad scanner replacement. [Commands](https://github.com/Instagram/LibCST/tree/v1.9.0/libcst/codemod/commands), [metadata](https://libcst.readthedocs.io/en/latest/metadata.html). |
| LibCST repository/parallel runners, CodemodTest and reentrant generation | Use independent exact-output cases; programmatic results keep current effect custody. Standalone runners can write directly and aggregate counts are not approved effects. Experimental reentrant generation is not selected as a general edit transaction engine. [Runner](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/_cli.py), [testing](https://libcst.readthedocs.io/en/latest/codemods.html#testing), [experimental](https://libcst.readthedocs.io/en/latest/experimental.html). |

The [ast-grep overview](../../libraries/python_introspection/ast-grep-py.md) and
[LibCST overview](../../libraries/python_introspection/libcst.md) orient these capabilities;
version-sensitive implementation/tests above govern actual integration. Neither a missing stub
field nor an empty structural search proves that a runtime capability or caller is absent.

## Package slices, actual consumers and retirement

| Owner | Delivered slice / prerequisite / completion boundary |
|---|---|
| DDO-03 | Typed explicit migration request, programmatic result/effect preparation, supported UTF-8 source and compilation of proposed inputs. Reuse actual generators and archive verification. This slice can develop before whole-family adoption; it does not certify CA-01 closure or grant native execution. |
| DDO-06/07 | Supply authentic frozen bindings/read/trust/capacity context; migrate one actual M1 caller slice through the target capability path. Do not add M1 name dispatch to a common runtime to make a codemod possible. Target helpers beside old selectors are not caller adoption. |
| DDO-07/08 | Extend supported migration semantics across the complete family/consumer inventory. Contextual occurrence selection and structural passage/reading selection challenge population/source/order distinctions. Remove former selectors/digests, duplicate registrations/dependency lists and mechanism-only tests with their migrated callers. |
| DDO-09 | Feed proposed-source compilation into existing definition/recipe/eligibility comparisons and equal-value/support cutoff. Source editing never independently authorizes recomputation or treats every changed byte as a changed result recipe. |
| DDO-10 | Expose the supported ongoing source-migration request, per-consumer outcomes and inspectable file effects through existing `ci model change` preview/apply. Reuse migration semantics; no alternate writer or automatic filesystem-triggered rewriting. Public read/export callers need their pinned DemandResult contract before migration is specified. |
| DDO-11 | Preserve exact source/release/history custody and immutable native revisions; source updates do not bypass coordinated adoption. Retire current fallback machinery when actual consumers/references migrate, not by rewriting old evidence. |
| DDO-12 | Include adopted transformations, actual migrated consumers, source/preview context and retirement in the applicable required union. Conditional catalogue entries are not automatically required cases. |

The initial source inventory starts at
[`orchestrate/semantic.py`](../../../python/corpus-structure/src/corpus_structure/orchestrate/semantic.py)
(`method.select` in ordinary orchestration and agent proposal) and
[`methods/m1_source.py`](../../../python/corpus-structure/src/corpus_structure/methods/m1_source.py)
(`select_bound`, `select_bound_native`, `select_hydrated`). The native selection form consumes
`connection, model, binding` plus keyword `demand_id`, `read_id`, `trust_snapshot`, `max_bytes`;
the hydrated form consumes admitted inputs already acquired under that contract. Select the
physical route from the caller's actual ownership and lifetime. Generic orchestrator syntax alone
does not identify which method is bound; do not rewrite every `method.select` call to the M1 shape.
The actual registry/declaration inventory supplies eligibility and the rest of the consumer set.

DDO-03 establishes preparation before its public/operator consumers rely on it; the first finite
DDO-07 migration supplies usable semantics before DDO-10 exposes the recurring capability.
Independent source preparation and domain repairs can proceed without whole-stage barriers;
actual execution waits for its specific authenticated prerequisites. Retain TS-21 retirement-test
transfer and TS-22 qualification mapping at their existing owners. TS-19 removed the old pure
identity helpers at `e1f62fa72`; reacquire actual CA-07 remaining work rather than scheduling their
deletion again. Completion state is read from the coordinator, not copied here.

## Independent acceptance and change scenarios

Demonstrate both declaration-owned and implementation-owned changes with independently specified
role, kind, parameter/default and caller expectations. Verify generation from authority and actual
handwritten caller migration together. A generated-output round trip proves agreement only.

Required discriminating cases for adopted behavior:

- An eligible aliased/relative import move versus a same-spelled local shadow or ambiguous binding;
  inherited supplying/exposed owners, exports and string annotations retain their distinctions.
- A model-derived interface change with positional/keyword callers and an authentic required
  context; unavailable context blocks readiness rather than inserting guessed values.
- Comments/decorators/multiline syntax, Unicode, CRLF and absent final newline remain correct;
  unsupported encodings and malformed source receive the intended refusal.
- For a selected annotation migration, conflict, explicit overwrite policy, import coordination and repeat application;
  annotate only authoritative declarations, not arbitrary inferred types.
- A required skipped/dynamic/unresolved consumer remains visible and non-applicable. Newly added
  callers, removed inputs, changed import context, transformation code/options or library identity
  make an old completeness claim stale.
- Concurrent source changes after preview, mid-apply interruption and retry of exact settled
  after-bytes preserve the existing publication contract. Nested/equal-offset edits are tested
  only when an adopted backend can produce them.
- The migrated ordinary family path actually uses the target binding/port and the former route
  is removed. Unrelated source is unchanged and a second application has no further effect.

Choose focused functional cases during implementation; final qualification waits for complete
applicable scope and final source/context. Benefits are qualitative: less repeated migration work,
clearer consumer coverage and better change locality. No benchmark campaign, universal behavioral
equivalence proof, extra alignment lint or generic refactoring platform is required. General
bidirectional synchronization, automatic rewriting and language-server repair products remain
separate undertakings. No rule change is assumed; surface a real authority/publication change
through the existing decision route before dependent work relies on it.

## Implemented preparation boundary · 2026-11-13

The typed request uses `SourceMigration` with `symbol_move` or `annotations`, semantic owner ID,
exact authored before-digest/after-source and logical `SourceRoot` mappings. Preview verifies the
owner in acquired and proposed effective models; symbol moves verify the actual old/new callable
declarations. Authored source changes must belong to the acquired operation input closure. Symbol moves preserve callable parameter/default/annotation/return/overload contracts; signature migrations require a separately supported transformation. Source inputs remain UTF-8 (BOM and other encodings explicitly refuse).

LibCST 1.9's rename command does not normalize relative-import matching itself. Preparation
normalizes only target module prefixes through explicit package context, reparses for the native
command and restores supported relative module forms. The native command consistently normalizes
local import aliases to the destination name; existing destination identifiers in any lexical
scope conservatively block that move. Unrelated files bypass rewriting. Required re-export chains,
unresolved attributes and dynamic namespace lookups remain visible and prevent apply. This is a
bounded supported transformation, not a claim of complete Python name resolution.

The explicit annotation stage derives its transient stub from requested authored after-source
and rejects a change the visitor cannot realize. Neither that stub nor proposed effective facts
become another editable model. Readiness binds selected dependency versions and fresh compiler/
implicit-source bytes and membership, separately from result-recipe identity. Current evidence
and remaining later-stage migration obligations are in the coordinator.
