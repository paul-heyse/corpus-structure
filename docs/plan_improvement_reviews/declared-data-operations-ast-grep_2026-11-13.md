# DDO structural analysis, codemods and model-driven updates

**Assessed / Proposed · 2026-11-13.** Reviews the remaining change footprint of the
[DDO coordinator](../plans/declared-data-operations_2026-11-12.md) and all nine companions.
Two operator-selected outcomes are assessed separately: migration tooling for the remaining DDO
replacement, and an ongoing model-update capability through existing `ci` preview/apply.
Recommendations do not amend the plan, close findings or authorize implementation.

The inspected checkout advanced to `e1f62fa72` during concurrent test-infrastructure work.
That commit removes the unused legacy identity helpers under TS-19; their removal is not new
work recommended here. Numerous test/support, PDF admission/staging/publication and CLI files
remain concurrently modified. Those edits are not assumed delivered or qualified. Decisive
source inspection concerns the unchanged DDO source frontend, artifact generation and model-change
owners, with current plan state read from its completion reassessment. Existing CA-01–07,
F01–F14, NetworkX and Python-introspection recommendation identities retain their owners.

The full supplied [ast-grep-py reference](../libraries/python_introspection/ast-grep-py.md)
(2,345 lines: original 0.51.0 account and 0.51.1/0.51.2 addenda) and
[LibCST reference](../libraries/python_introspection/libcst.md) (1,611 lines, including the 1.9.0
addendum) were read end to end. Independent library researchers checked consequential tagged
source, and an independent architectural reader assessed integration with the existing owners.
The Python manifest selects LibCST 1.9.0, Griffe 2.4.1, Astroid 4.3.4 and ty 0.0.102; it does
not declare ast-grep-py. Existing ast-grep CLI recipes are a separate capability.

Apply core 3.3, efficient-architecture heuristics, code-intelligence 1.4, test-assessment 1.2 and
repository binding. Library/source observations below are **Interface-checked, 2026-11-13**;
proposed integrations and benefits are not tested or measured. The cancelled qualification
campaign remains stopped. This review performs no dependency, production or native migration change.

## Combined judgment

**Recommend stronger model-aware generation and programmatic LibCST migration, with ast-grep
available for bounded structural discovery. Do not add ast-grep-py as a second DDO Python
frontend on current evidence.** Its native matching is useful, but the actual source frontend
also needs lexical bindings, supplying owners, generated-interface models and explicit unknowns.
Adding a second tree to those paths does not remove those responsibilities.
Griffe retains declaration/inheritance/generated-interface facts, Astroid its bounded supplied-source
resolution, and ty its selected conditional public inspection role. Pyrefly remains the checker.
An ast-grep match can contribute syntax evidence to that composition without acquiring any of
those semantic authorities.

The user's propagation hypothesis is valuable. A model change can produce more of its actual
interface/consumer change together, rather than leaving the operator to discover and repeat every
mechanical edit. The enabling responsibility is an owned semantic change with source-specific
lowerings, not unrestricted structural replacement. Some outputs should be regenerated; some
handwritten callers admit a codemod; others require explicit domain decisions.

The strongest near-term amendment is finite migration assistance during DDO-03/07/08. The ongoing
preview/apply extension is coherent for the same supported transformations, once a real migration
has established their contracts. A general cross-language bidirectional source-model synchronizer
would be a broader product, with different ambiguity and maintenance obligations.

## Baseline and complete alternatives

`semantic/python_operation_sources.py` already prepares LibCST metadata, Griffe declarations and
closed Astroid context over supplied source. Its `_literal`, `_index`, `_syntax`,
`implementation_slice`, `References` and `ArgumentUses` jointly perform recognition, ownership,
normalization and conservative closure. Ast-grep can recognize syntactic subsets, but cannot
replace that complete responsibility. In particular, structural detection of `__builtins__` does
not establish CA-01 runtime authentication or exhaustive dependency closure.

`semantic/data_operation_artifacts.py:compile_data_operation_artifacts` already produces archived
call/identifier/schema products with model, correspondence, generator and source digests.
`operation_call_generation.py:render_call_bindings` is shared across resolved correspondences.
Those archive products should not be materialized into the checkout merely to make them editable.
Actual checkout-generated consumers and handwritten callers are separate from release artifacts.

`schema/model_change.py` supplies `ChangeRequest`, `FileEffect`, `ChangePreview`,
`verify_release_products`, `check_preview` and `apply_preview`. It already checks exact inputs,
toolchain and workspace, publishes each changed file through a temporary file/replace, rechecks
concurrent edits and recognizes settled after-bytes. This is retryable per-file publication,
not an all-or-nothing multi-file transaction or a lock honored by every external editor.

| Complete option | Fit and total burden |
|---|---|
| Current frontend and generation, manual caller migration | Preserves current authority and avoids another parser. Repeated manual consumer discovery and mechanical propagation remain. This is the baseline, not a correctness defect by itself. |
| LibCST programmatic codemods plus owned generation | Best fit for current Python interfaces: metadata, import coordination, rename and annotation facilities can own substantial transformation work. Adds bounded domain-specific migration semantics, not another Python framework. Recommended for supported cases. |
| Existing ast-grep CLI for finite candidate discovery | Useful when filesystem scanning and inspectable match output are the responsibility. Avoids recreating file discovery/scheduling in Python. No new lint gate follows. Conditional per migration. |
| ast-grep-py for embedded structural queries/local edits | Appropriate if an actual supplied-snapshot consumer needs native structural correlation or multilingual queries. Currently adds grammar, coordinate and tree reconciliation without retiring the semantic frontend. Conditional trigger, not a required dependency. |
| ast-grep-py recognition plus LibCST editing everywhere | Two parses, two recognition models and cross-tree correspondence for Python already parsed by LibCST. No present whole-responsibility benefit establishes this as the default. |
| ast-grep as semantic frontend or universal refactoring engine | Does not discharge lexical/program identity, parse validity, imports, runtime closure or complete edit application. Not recommended for these responsibilities. |

<a id="I01"></a>
## I01 — Propagate owned changes through generation and explicit migrations

**Recommend · DDO-01/03/07/08/10.** Classify each changed fact by its authored owner before
planning source effects. Implementation-owned typed definitions remain inputs to the effective
model; externally authored protocols retain declaration authority. A derived effective model
cannot silently rewrite the source from which that same fact was extracted. An explicitly
requested source migration can change that owner and then recompile its derived products.

Use existing compiler products to regenerate mechanical outputs. For a checkout consumer that
actually needs regeneration, compose its owning renderer's result with the model-change preview.
Keep release-only calls/IDs/schemas in their authenticated archive preparation path and retain
`verify_release_products`. Do not CST-patch generated output or create another editable signature,
operation, naming or domain-field registry.

For handwritten consumers, an explicit old→new semantic change supplies the eligible symbols,
roles, types and intended behavior. Syntax tools locate and realize a supported change; they do
not invent support, outcome, coverage, independent-evidence or effect semantics. Adding an analyzed
scope parameter, for example, requires an authentic context expression, not an inserted default
or a guessed local subject. Unavailable correspondence remains an explicit unresolved consumer.

This strengthens FP-04/05, DP-01/06/08/16 and CI-02: one owner governs meaning and mechanical
representations follow it. It fits the planned family/interface migration and removes repeated
manual synchronization. It does not make CA-05's native ambiguity policy or CA-06's projection
definition automatic source edits. Closure requires one representative declaration-owned and
one implementation-owned change reaching their actual generated and handwritten consumers with
independent expected meaning.

<a id="I02"></a>
## I02 — Use complete LibCST codemods for Python migration

**Recommend · DDO-03/07/08; later DDO-10 callers.** Strengthen the existing conditional codemod
selection into concrete migration work where a consumer changes. Prefer programmatic
`transform_module` and context-aware commands, preserving success, skip, warnings and failures.
Use native facilities before writing replacement traversal or import bookkeeping:

- `RenameCommand` for supported qualified symbol moves, with alias/import behavior established
  for the actual migration. A rename is not a signature or domain-policy migration.
- `AddImportsVisitor`/`RemoveImportsVisitor` and supported export/string-annotation collectors
  for imports introduced or retired by the transformation.
- Matcher captures, metadata predicates and templates for local call/declaration construction;
  use scope/qualified-name facts to distinguish a real imported API from a same-spelled local.
- `ApplyTypeAnnotationsVisitor` only for authoritative supplied annotations and a qualified
  integration route. Its stub/context and explicit-annotation paths need their selected-version
  contract checked; do not build a second inference engine or durable stub authority.

Shipped modernization commands are examples or reusable mechanisms when the actual migration
requires them. Blanket typing/string/dataclass modernization does not belong to this undertaking.
Declaration conversion alone cannot establish migration of all constructors or consumers.

The [tagged command collection](https://github.com/Instagram/LibCST/tree/v1.9.0/libcst/codemod/commands),
[rename implementation](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/commands/rename.py)
and [annotation visitor](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/visitors/_apply_type_annotations.py)
supply concrete enabling mechanisms. The inspected annotation implementation warrants caution:
its `tree_with_imports` initialization depends on context contents before later unconditional use.
Bare explicit-annotation construction is therefore not a confirmed working path from source
inspection alone. The command's automatic helper list supplies import visitors, not automatic
annotation application merely because a stub is stored. An adopted annotation migration needs an
explicit visitor stage and one focused conformance case before use.
For a selected annotation migration, prefer the upstream-tested context-stub route as that
stage's input. Generate the stub ephemerally from the authoritative requested facts; it is not
another checked-in interface definition. Annotation application does not add/remove/reorder
parameters or migrate call arguments. `RenameCommand` qualified-name membership also does not
prove a unique binding; ambiguous or shadowed eligible names need the migration's explicit refusal.

Expected benefit is fewer independent migration mechanisms and more local change reasoning
(FP-01/03/06, DP-13–16, H4). Closure includes aliases/re-exports, keyword/positional arguments,
defaults, comments and deliberate refusal of ambiguous dynamic use. Reuse useful selection kernels
when retiring old callers; do not preserve a compatibility dispatch simply to avoid migration.

<a id="I03"></a>
## I03 — Use ast-grep for candidate discovery where structure earns its cost

**Conditional amendment · DDO-00/07/08/10.** Derive the search scope and relevant symbols from
owned operation/interface changes. Structural patterns can identify registration shapes,
colocated metadata, `getattr` capability discovery, old call forms and repeated owner/symbol
boilerplate. They are migration candidates or attributed syntax facts, not complete caller graphs
or permission to rewrite every match.

Use the existing CLI for finite cross-file discovery when it supplies the complete responsibility.
`justfile` already owns ast-grep invocation; that does not imply the Python package is installed
or exposes the CLI's project machinery. No new alignment lint, standing scan or health gate is
recommended. LibCST alone remains sufficient for discovery inside already prepared Python trees.
`schema/model_discovery.py:locate_consumers` already combines bounded AST/symtable and CLI
ast-grep candidate evidence with explicit coverage limits. Reuse or deliberately replace that
owner when a migration needs better discovery; do not introduce a competing inventory. Its
candidate/partial contract must not silently become complete rename coverage or write authority.

Select ast-grep-py only when an embedded supplied-snapshot consumer has enough independent
structural querying to remove meaningful custom work. Good candidates include repeated
cross-structural correlations and a genuine non-Python input family. A short native pattern that
still requires the same Python scope traversal does not meet that trigger. Preserve positive
matches, ambiguous candidates, excluded scope and unknowns; an empty scan is not proof of no use.

The source frontend's literal extraction and canonical `_syntax` are poor replacement targets:
literal meaning and canonicalization are not matching strictness. Its dependency/reference
visitors also use lexical contexts and modeled boundaries that syntax matching cannot establish.
This disposition follows FP-07, H12/H16/H27 and CI-01/02/04, rather than assuming another native
parser necessarily improves the system.

<a id="I04"></a>
## I04 — Extend existing preview/apply for supported source changes

**Recommend the bounded ongoing capability · DDO-03/07/08/10 and the existing model-change owner.**
Reuse a supported migration from I02 as an explicit operator-requested transformation in preview.
Return complete candidate after-source and per-file semantic outcomes to the existing owner;
compose actual checkout changes as `FileEffect`s with their exact before snapshots. Keep native
candidate/registration and immutable migration custody in their existing routes. Source propagation
does not deploy a release, reinterpret archived data or modify frozen migrations.
Include every edited source and each source fact used to justify an edit in preview premises,
along with transform implementation, options, module/import context and selected library identity.
The current generator fingerprint covers schema code; a codemod added elsewhere would need its
own actual input bytes included in staleness checks. An unchanged generator label is insufficient.

Programmatic codemod results fit this responsibility better than a standalone repository writer.
The [LibCST programmatic runner](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/_runner.py)
returns structured results. The
[CLI/repository runner](https://github.com/Instagram/LibCST/blob/v1.9.0/libcst/codemod/_cli.py)
can write files directly and its aggregate result is not an exact source-effect contract. Use
its traversal/parallel facilities only if they can preserve the existing effect owner; do not
delegate writes merely to obtain concurrency.

Resolve all required consumers before declaring a coherent migration ready to apply. Independent
effects may remain inspectable, but a skipped required call site cannot be silently counted as a
complete model update. Recompile the intended model and generated artifacts against the proposed
source, including changed implementation recipes, rather than validating the old release against
new signatures. Reparse/reacquire metadata between dependent transformation passes.

Preserve existing retryable file publication and state that boundary honestly. A mid-apply failure
can leave already settled files; no multi-file atomicity is promised. Current `FileEffect.after`
is text and apply encodes it, so arbitrary non-UTF-8 preservation is not established. Support the
repository's explicit encoding policy or extend the owner deliberately before claiming broader
byte fidelity. Avoid a second edit journal, watcher, transaction framework or migration registry.

This is a worthwhile extension because it completes changes already being made to the same
operation interfaces (FP-03/04/06, DP-18/19/24). Automatic propagation on every model-file edit and
general bidirectional synchronization remain outside the recommended bounded workflow.

<a id="I05"></a>
## I05 — Make syntax/edit fidelity explicit at the library boundary

**Required companion to any adopted transformation · DDO-01/03/07/08.** Treat recognition,
semantic eligibility, edit construction and publication as distinct responsibilities; ordinary
functions and existing result types suffice. Do not manufacture a generic edit IR merely to
combine tools.

For ast-grep-py 0.51.2, tagged
[Python node implementation](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/pyo3/src/py_node.rs)
shows literal replacement text, sorting and silent skipping of overlaps, with only source text
returned. Successful `commit_edits` is not complete edit application. The
[core rule configuration](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/config/src/rule_core.rs)
exposes `rule`, `constraints`, `utils`, `transform`; full `fix`/rewriter registration belongs to
[another configuration](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/config/src/rule_config.rs).
Do not promise the CLI's capture interpolation or recursive rewriter setup through Python.

If ast-grep editing is selected for a genuinely local nonoverlapping case, construct replacements
from explicit captures, reject competing/nested ranges and order same-offset insertions
deliberately, or use separate reparsed passes. Check intended coverage before making the output
an approved file effect. For structural Python changes, LibCST's immutable transformations often
avoid maintaining offset composition at all.

Both trees and metadata describe one source snapshot. Python character positions, UTF-8 bytes and
UTF-16 diagnostic positions need a deliberate conversion at an actual crossing. Ast-grep's
[tagged range code](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/pyo3/src/range.rs)
and [Unicode mapping](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/pyo3/src/unicode_position.rs)
support that distinction. Navigation/capture wrappers do not inherit the original match environment
([NodeMatch source](https://github.com/ast-grep/ast-grep/blob/0.51.2/crates/core/src/matcher/node_match.rs)).
Node equality is not semantic operation identity or equal capture results.

Tree-sitter recovery and an `ERROR` search do not supply a complete Python validity report:
the Python binding lacks the core's missing/error-node status interface. Use the appropriate
language parser/compiler for the supported output and retain semantic validation at its owner.
Neither successful parsing nor identical rewritten text proves domain meaning. This addresses
DP-08/15/19 and CI-02/06/10 without creating recurring proof machinery.

<a id="I06"></a>
## I06 — Keep discovery, preparation and publication economical

**Recommend as an execution constraint on I02–05.** Batch useful queries over one supplied source
snapshot and release native nodes with it. For Python already using LibCST metadata, share that
preparation instead of unconditionally parsing it again. Scope candidate acquisition to the changed
contracts and their relevant consumers; keep diagnostics detached from live trees.

Ast-grep searches compile matchers per call, `find_all` materializes results, and retained nodes
retain their roots. Do not assume public compiled-matcher caching, incremental Tree-sitter updates,
streaming matches, GIL-free scaling or CLI scheduling in the Python binding. For current migrations,
finite file batches and existing preparation are sufficient; a persistent index or daemon needs a
real repeated-query consumer. No numerical speed benefit is claimed.

## Capability coverage and deeper-investigation disposition

This appendix covers the full references, including the less visible addenda. Conditional
features have concrete triggers; they are not new mandatory research or qualification packages.

| Family / documented functionality | Disposition and consequential question |
|---|---|
| `SgRoot`, named/unnamed nodes, fields/children/siblings, text/ranges, inspection and root ownership | Candidate extraction for I03; retain attributed source facts. No cross-language semantic ontology or stable serialization from `repr`/`str`. `is_named_leaf` is a grammar-specific distinction. |
| Code-shaped patterns, contextual selectors/effective nodes, single/anonymous/variadic metavariables | Use only at intended expression/statement granularity. Inspect separators/comments in variadic captures before treating them as logical arguments. |
| `cst`/`smart`/`ast`/`relaxed`/`signature` strictness | Select per recognition contract; permissive shape matching cannot define canonical implementation equality or erase meaningful operators/modifiers. |
| Atomic/composite rules, positive restrictions, mapping-based negation | Useful candidate predicates. `all`/`any` constrain one candidate, not arbitrary node-set quantification; negative matches do not establish captures. |
| Declarative relations, `stopBy`, field constraints; imperative refinement | Qualify defaults: declarative immediate-neighbor versus imperative recursive/ancestor/all-sibling searches differ. Fields belong only to supported relations. |
| Positional `nthChild`, `ofRule`, reverse and limited ESQuery selectors | Conditional ordered-shape recognition. Named sibling counts, concrete child indices and filtered sibling populations are different. |
| Utilities, recursive structural predicates and capture constraints | Factor actual recognition rules locally. Recursion needs structural progress/base cases; no same-node dependency cycles or assumed variadic constraints. No second domain-rule registry. |
| Ordered cross-structural capture unification, capture environments and navigation | Good native local correlation where I03's trigger holds; syntactic repeated-name agreement is not imported symbol identity. Evaluation order and lost capture environments need selected-rule controls. |
| Derived transforms: Rust-regex replace, substring, chaining, conversion, separators/acronyms/digits | Conditional mechanical naming/text derivation from the existing naming authority. Account for regex limits, capture locality and 0.51.2 digit behavior; no domain identifiers inferred from case conversion. |
| `replace`, mutable edits and root/subtree `commit_edits` | I05's qualified local editing only. Literal replacements, skipped overlaps, equal-position insertion order and stale snapshots prevent treating it as a complete migration owner. |
| Python `TypedDict`/runtime option discrepancies, Config versus CLI/full rule configuration | Verify the chosen release's actual path; use straightforward typed mappings where sufficient. Missing stub fields do not prove missing runtime behavior; unsupported rewriter registration is a real boundary. |
| Built-in languages, dynamic native grammar registration, sigil expansion and custom extensions | Conditional on a substantially affected non-Python consumer. Check grammar/version/native-library provenance and process registration before adoption; do not build a universal normalized syntax layer. |
| Embedded languages/injections and diagnostic-guided edits | Python may compose explicit region extraction and a second root, but does not inherit complete CLI injection/LSP infrastructure. Retain existing SQL/native parsers and fragment owners where adequate. |
| Parse errors/missing syntax, Python grammar/wheel evolution, Unicode/UTF-16 | I05 boundaries, not proof of complete parsing. Distribution availability and CLI LSP fixes are distinct from Python grammar/API guarantees. |
| Matcher construction, eager results, native crossings, concurrency and retained trees | I06. No current reason for a second parser cache, worker pool or resident service. Measure only if an actual uncertainty could alter acceptance. |
| LibCST immutable edits, matcher captures/decorators, templates and literal/docstring/field helpers | I02's preferred Python substrate; selective field projections are syntax views, not semantic normalization by themselves. |
| LibCST match statements, PEP 695 generics/type aliases, template strings and lazy-import syntax | Qualify the actual target grammar separately from scope/import/codemod coverage. A parser's ability to represent a construct does not establish that every metadata provider or shipped migration handles it. |
| LibCST scopes, access contexts, qualified names, module paths, aliases, exports/string annotations | Preserve current frontend preparation; use to qualify migrations. Arbitrary attributes, dispatch and runtime builtins remain explicit semantic gaps. |
| Rename/import helpers, annotation application, shipped modernization commands | I02; reuse complete native mechanisms. Preserve original annotations or make the intended overwrite explicit; no blanket source modernization. |
| Codemod contexts/composition, structured results, file/parallel runners, CodemodTest | I02/I04; programmatic results enter existing effect custody. Do not equate aggregate runner counts with exact source effects or complete consumer migration. |
| FullRepoManager/batched visitors/external type metadata and experimental reentrant generation | Conditional repeated repository context only. No new Pyre service, general incremental parser or experimental generator dependency is needed by the current recommendation. |

## Revealing cases, sequencing and limits

Start with one actual Python migration: a qualified interface move or explicit required-context
addition among DDO-07/08 callers. Compare LibCST-only discovery/editing against ast-grep candidate
search plus semantic qualification. Use the existing simple operation and inherited family as
distinct ownership cases. A model-driven update must have independently specified expected roles,
context and caller meaning, not merely output regenerated from the same mistaken model.

Challenge the selected implementation with aliases/re-exports/shadowing, multiple similar calls,
positional versus keyword arguments, defaults/factories, comments/decorators/multiline syntax,
Unicode/CRLF/encoding, malformed input, ambiguous dynamic dispatch and a stale source snapshot.
Include nested edits, equal-position insertion, intentional skip and mid-apply recovery when that
backend can encounter them. Check that a second application has no unintended effect and that
unrelated source remains unchanged. These are revealing acceptance cases for adoption, not a
proposal to rerun the interrupted campaign or create new health gates now.

Once the migration semantics work through actual callers, expose the same supported operation in
the ongoing preview/apply path (I04). Recompile affected effective products and inspect actual
retirement; a candidate inventory cannot certify all consumers were migrated. A new library or
grammar becomes a deliberately pinned dependency only when selected for a concrete consumer.

I01 governs ownership before I02/I04 effects; I05 qualifies any chosen edit backend; I06 prevents
unnecessary orchestration. I03 can help discovery independently but is not a prerequisite to
Python codemods. CA-01 source closure, CA-05 scoped native discovery and CA-06 projection semantics
retain their existing repair obligations. CA-07's dead helpers have changed under concurrent TS-19;
reacquire its actual remaining retirement footprint before implementation. Do not manufacture a
second status table here.

No new architectural rule is accepted by this review. If adoption makes editable projections or
new source-update authority binding decisions, use the existing ADR/owner route; ordinary choice
of a syntax library does not itself require an ADR. General bidirectional synchronization,
automatic filesystem-triggered rewriting, language-server repair products and a universal
cross-language codemod platform are separable opportunities requiring a broader product decision.
The bounded preview/apply recommendation does not depend on building them.

Benefits remain Proposed: reduced mechanical migration work, stronger change locality and clearer
consumer coverage. Primary source inspection settles the library selection boundaries without
an installed ast-grep-py experiment. It does not establish integrated transformation behavior,
linguistic correctness, complete program equivalence or measured performance improvement.
