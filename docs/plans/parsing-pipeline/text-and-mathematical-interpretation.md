# Text structure and context-bound mathematical interpretation

**Implementation in progress · 2026-10-30.** The coordinator owns current qualification. This supporting plan develops
[PP-05](../parsing-pipeline_2026-10-30.md#PP-05) and
[PP-06](../parsing-pipeline_2026-10-30.md#PP-06). The coordinator is the sole owner of current
package state, opportunity/finding dispositions, shared decisions and assembled acceptance.
These work descriptions do not imply implementation or repeat a mutable status table.

## Intended behavior and responsibility

A caller can request complete prose/TeX decomposition and useful structure without implicitly
requesting mathematical interpretation, symbolic values or calculations. A stronger consumer
requests those capabilities explicitly against archived, admitted context. Every supported
reading retains its source occurrences, effective macro/declaration basis, ambiguity and
conditions. SymPy owns supported native mathematics; the domain model owns what the source
establishes and what an operation is allowed to conclude.

Inputs are the [parsing review O01/O02/O04/O05/O07](../../functional_reviews/parsing-pipeline_2026-10-30.md),
its [connected target §§2–5](../../functional_reviews/parsing-pipeline_2026-10-30_target-model.md),
and the earlier [symbolic math review O01–O07 and full capability assessment](../../functional_reviews/symbolic-math-decomposition_2026-10-30.md).
The operator approved planning redesigned M09/M11/M13 boundaries, outputs, versioning and
consumer migration. This authorizes this target plan; it does not silently change accepted ADRs,
method contracts or deployed releases. PP-00 owns their adoption route; PP-01 owns authoritative
definitions and operation contracts; PP-04 owns durable products; PP-08 owns execution and
lifetime; PP-09 owns protected publication/read selection; PP-10 owns assembled consumer adoption. PP-07 owns query/graph and
quote/extraction views consuming the source-bound products developed here.

## Baseline and foundations

Static source inspected at `b3a8313c984a5a0be41b25eea832e74fa822b469` on 2026-10-30.
[The product manifest](../../../python/corpus-structure/pyproject.toml) pins SymPy 1.14.0,
Lark 1.3.1, regex 2026.9.29, spaCy 3.8.18, `en-core-web-sm` 3.8.0 and RapidFuzz 3.14.6.
Tokenizers 0.23.3 belongs to retained spike dependencies, not product parsing. pylatexenc has
no current production role; 2.10's stable structural API is a candidate, distinct from the
historical 3.0b2 hold and prerelease version-3 interfaces. Adoption must inspect the current
[holds](../../pins.md), deliberately pin any selected dependency, and qualify its actual version.

| Producer/consumer | Current behavior and resulting obligation |
|---|---|
| [`core/tex.py`](../../../python/corpus-structure/src/corpus_structure/core/tex.py), `Token`, `tokens`, `effective_macros`, `expand`, `token_form` | Total code-point scanner already captures whitespace/unknown characters. Its `symbol` means TeX control symbol, not resolved mathematical symbol. Expansion retains tokens/unexpanded names but not multi-artifact provenance; token forms are identity-sensitive. Preserve that distinction and the existing expansion bounds. |
| [`ingest/macros.py`](../../../python/corpus-structure/src/corpus_structure/ingest/macros.py), `read_macros`; [`ingest/html.py`](../../../python/corpus-structure/src/corpus_structure/ingest/html.py), `_macro_table` | Existing `newcommand`/`renewcommand`/`providecommand`/`DeclareMathOperator` semantics and page-over-fallback selection remain authoritative. Token offsets are discarded and DOM text is joined; provenance needs producer changes, including fallback artifact custody. |
| [`ingest/sentences.py`](../../../python/corpus-structure/src/corpus_structure/ingest/sentences.py), `TextLayout`, `make_doc`, `split` | Immutable source-bound layouts feed consumer-owned `Doc(words, spaces)` and `Language.pipe(as_tuples=True)`. Math/reference atoms and spacing flags serve current segmentation; they are not complete canonical decomposition. Keep the configured parser selection and sentence behavior unless a deliberate new recipe changes them. |
| [`methods/math/grammar.py`](../../../python/corpus-structure/src/corpus_structure/methods/math/grammar.py), `parser_for`, `_reading`, `_Resolver.value` | SymPy's shipped grammar plus extensions; typed starts, dynamic Earley, explicit ambiguity, whole-name terminals and propagated positions. `_Resolver.value` can construct SymPy values while resolving ambiguity, so `reading()` is not syntax-only work. |
| [`methods/math/prepared.py`](../../../python/corpus-structure/src/corpus_structure/methods/math/prepared.py), `PreparedMathInput`; [`semantic/analysis_contracts.py`](../../../python/corpus-structure/src/corpus_structure/semantic/analysis_contracts.py), `PreparedInterpretationContext` | Shared readings and lazy values already exist. Release demands, roles, missing declarations, scope, assumptions and stage keys are present. `grammar_context` projects roles/constants; hashing assumption bytes alone does not supply native assumption semantics. |
| [`methods/math/spans.py`](../../../python/corpus-structure/src/corpus_structure/methods/math/spans.py), `_inner`, `read_spans`, `formula_values` | Strips outer delimiters/edge whitespace into an exact-offset parse view; M09/M11 currently require interpreted results. New capture must retain the whole original Segment and map that view rather than replacing it. |
| [`methods/math/methods.py`](../../../python/corpus-structure/src/corpus_structure/methods/math/methods.py), M09/M11/M13; [`methods/math/scope.py`](../../../python/corpus-structure/src/corpus_structure/methods/math/scope.py) | M09 positional mentions/relations and M11 values feed M13 scope; mention ordinal references and output hashes affect reuse. Current method/payload versions are `3`/`1`. A weaker capture result cannot continue under those old completeness claims. |
| [`semantic/scientific_evidence.py`](../../../python/corpus-structure/src/corpus_structure/semantic/scientific_evidence.py) | Native sets, relations, polynomial cancellation, simplification and numerical evidence already exist. Consolidation and reference have distinct decision policies/preparation. Preserve that separation and current stored identity; neither new parsing nor SymPy equivalence changes it automatically. |

Architecture owners are [D1 §§3/6/8/10](../../design/D1-knowledge-representation.md),
[D4 M03/M09/M11/M13 and prepared execution](../../design/D4-method-catalog.md),
[D5 scientific evidence](../../design/D5-consolidation-identity-confidence.md#shared-scientific-evidence-and-analytical-inputs)
and [D6 prepared execution](../../design/D6-orchestration-metrics-policies.md#prepared-interpretation-execution).
Historical ADR-0012 token-key/grammar behavior and ADR-0019 rendition identity explain preserved
obligations. PP-00 identifies their current successor clauses and those of ADR-0035 model-governed
analysis before adoption; do not amend historical records as if they were current authorities. Preserve one semantic authority and one
preparation owner; a universal math gateway, global cache or universal persisted AST would add
work and lifetime machinery without a current consumer.

The foundation improvement is to make each demand mean what actually runs, connect lexical
and structural products to context, and migrate downstream promises coherently. Core FP-04/05/07,
DP-09/13–15 and the heuristic companion favor shared immutable text/ranges, native preparation at
its valid scope and selective expensive work. A source-inspection request should not enter
Earley or SymPy; a binding-dependent occurrence request may legitimately need recognition and
context. Laziness shifts latency to the first demander and saves no recognition work when every
consumer still requires it. Complete capture adds work; existing M09/M11 sharing is not a new
benefit. No numerical performance claim is made.

## Target products, context and outcomes

The complete partition remains source evidence, separate from syntax and symbolic value. Keep
delimiters, braces, scripts, argument punctuation, whitespace, text-mode content, presentation
commands, unknown commands and invalid fragments. Lexical categories must never assert symbol,
function, constant, probability or binder semantics without the admitted reading. Composite
structures such as `\sigma_{X_1}`, groups, numerator/denominator and bound references overlap
the disjoint partition through identified typed relationships.

For `x + x`, both `x` occurrences survive after native construction gives `2*x`; the coefficient
is derived. One SymPy object can link to several source occurrences, and one macro invocation
can generate several structures. `free_symbols` describes free variables of the interpreted
object; it is not an occurrence list or a complete binder model. Keep source definedness before
construction can turn `x/x` into `1`. `evaluate=False` is useful at qualified constructors but
is neither complete definedness preservation nor source fidelity.

Macro mapping names the invocation representation, argument ranges, selected page/fallback
definition artifact, definition/default-body ranges, expansion recipe/release and target extents.
An argument copied twice creates two target extents with the same input origin; default argument
text comes from its definition, not guessed invocation positions. Selection dependencies include
the losing/missing definitions where their absence affects the outcome. Definitions in excluded
HTML macro blocks and separately archived pack/fallback files remain retrievable. Partial or
unavailable HTML origin propagates honestly; equal expanded spelling cannot prove provenance.

Prepare admitted declarations into native symbol/function/constant/set construction and supported
assumptions. Preserve scope and identity for same-spelling variables; binder normalization may
use `Dummy`/`as_dummy` only after source binding is established. Compile supported conditions to
explicit `Q` predicates, use `ask`/`refine` under operation-local assumptions, retain unsupported
conditions and contradictions as typed outcomes. Do not use ambient global assumptions. In
SymPy 1.14, `ask(Q.positive(x), x > 0)` is not a general relational-inference solution.
Reconcile current `N → Naturals0` and unqualified set-builder real-domain conventions as admitted
meaning with a recorded basis; do not make every variable real or every `P` a probability.
M13's later output cannot secretly determine extraction that supplies M13's own inputs.

Requested capabilities separate lexical capture, syntax, occurrence candidates, interpretation,
native symbolic values and named assessments. Computation state (not requested, pending/running,
available, failed, cancelled as needed) is separate from coverage (complete/partial) and semantic
outcome (resolved, ambiguous, unsupported, invalid, unknown). A retryable timeout is an attempt
outcome, never a timeless semantic cache result. An unevaluated `Integral` is available structure;
its calculation remains unrequested. `None` from a native property/equality question is unknown,
not false. Absence of an assessment row never establishes absence of a property.

## Native realization and retained guide choices

Carry the concrete research from both reviews rather than rediscovering capabilities during
execution. Context7 was consulted on 2026-10-30 for pinned-version boundaries; installed/tagged
source prevails over synthesized current signatures. Native handles remain operation-owned.

| Mechanism | Intended realization and pitfalls |
|---|---|
| Current regex scanner, `tokens`, `expand` | Extend source records/ranges and expansion derivations at the existing owner first. Preserve total coverage and depth/token bounds; a bounded expansion retains its unexpanded invocation/reason. The source partition never adopts token-form drop/normalization rules. |
| Lark 1.3.1 grammar composition, typed starts, `propagate_positions=True`, `edit_terminals` | Retain shipped grammar plus explicit extensions and whole-name control-word matching, including ignored anonymous terminals. Preserve alternatives and positions rather than replacing with stock `parse_latex`. Pure resolver summaries can be cached operation-locally; declaration/binding context remains part of identity. [Lark parser documentation](https://lark-parser.readthedocs.io/en/stable/parsers.html). |
| Lark `ForestVisitor(single_visit=True)`, `ForestTransformer`, `TreeForestTransformer` | Bounded candidate if ambiguity expansion causes real work. Preserve correlated alternatives, ordering, ordinary tree shaping/filtering and source positions explicitly. Packed forests avoid expansion, not Earley recognition; forest transformers do not reproduce normal tree shaping automatically. Do not use exponential `CollapseAmbiguities`. LALR `save`/cache and TextSlice restrictions are not speedups for current dynamic Earley. [Forest contracts](https://lark-parser.readthedocs.io/en/stable/forest.html). |
| pylatexenc stable 2.10 `LatexWalker.get_latex_nodes`, `LatexContextDb`, `MacroSpec`, `EnvironmentSpec` | Conditional structure-only adapter when it avoids unnecessary mathematical recognition for a real consumer. Use `pos`, `len`, `latex_verbatim`, `nodeargd.argnlist` and declared macro/argument specs; include both `LatexMathNode` and math `LatexEnvironmentNode`. Context/tolerance/malformed recovery are recipe semantics. `%` comment semantics differ from the existing scanner, where `%` is an ordinary character; neither may silently rewrite the other's partition contract. No current product pass exists for this library to replace. [2.10 walker](https://pylatexenc.readthedocs.io/en/v2.10/latexwalker/), [macro specs](https://pylatexenc.readthedocs.io/en/v2.10/macrospec/). |
| pylatexenc version 3 parsing state/context and `parse_content` | Prerelease candidate only if an identified requirement needs it and migration/support are qualified. Do not mix version-3 APIs with stable 2.10 construction. `latex2text`/Unicode encoding/rendering are explicitly lossy derived projections, not complete decomposition or mathematical authority. |
| Tokenizers 0.23.3 `Split(Regex(...), behavior="isolated").pre_tokenize_str`, `NormalizedString` | Compare only as a replacement lexical owner or needed alignment mechanism. Preserve matches plus unmatched stretches, category boundaries, character-coordinate contract and normalization mapping. No full Tokenizer/learned vocabulary is needed. `contiguous` can merge desired boundaries; subword IDs are not mathematical symbols. [Tagged split implementation](https://github.com/huggingface/tokenizers/blob/v0.23.3/tokenizers/src/pre_tokenizers/split.rs), [alignment API](https://huggingface.co/docs/tokenizers/api/encoding). |
| Tokenizers normalization, added/special tokens, post-processing, truncation/padding/overflow and decoding | Each changes alignment or coverage; offsets do not imply reversibility, special tokens may be synthetic, truncation cannot supply a complete source partition, and decoding IDs does not recover original text. Avoid offset-free batch APIs for this contract. Training, Hub acquisition, multilingual models and 1.0 transition features have no selected requirement; custom Python components may not serialize portably. Native Rayon/process concurrency belongs with PP-08 if adopted. |
| spaCy 3.8.18 `Doc(words, spaces)`, `Language.pipe(as_tuples=True)`, Matcher/DependencyMatcher | Shared immutable layouts feed separately owned mutable Docs, exact canonical ranges and explicit annotation prerequisites. Keep configured components/model versions and historical parser selection; sentence alternatives require an explicit recipe and identity change. Retokenization needs declared source mappings. `memory_zone` is conditional on retention needs and no Doc/Token/Span/Lexeme may outlive it. Training/transformer/entity-linking families require a selected separate capability. [Pipeline docs](https://spacy.io/usage/processing-pipelines). |
| RapidFuzz 3.14.6 token `partial_ratio_alignment`, `Levenshtein.opcodes`, `process.extract`/`extract_iter` | Reuse shared text/token coordinates and prepared candidates in PP-07 placement consumers; retain edit evidence, cascade step, scope and competing matches. Long-needle partial alignment does not prove a unique global optimum. `cpdist` is selected-pair work; `cdist` creates dense Cartesian work and is not an index. Similarity never establishes exact source identity. [Process APIs](https://rapidfuzz.github.io/RapidFuzz/Usage/process.html). |
| SymPy 1.14.0 grammar, `TransformToSymPyExpr`, native objects | Extend the current `ToSympy` adapter and retire local extension methods only when upstream demonstrably replaces them. `LarkLaTeXParser(transform=False, grammar_file=..., transformer=...)` exists, but stock branch positions/ignored material do not satisfy current source contract. [Pinned parser](https://github.com/sympy/sympy/blob/1.14.0/sympy/parsing/latex/lark/latex_parser.py). |
| Development SymPy `locals` / `parse_latex_lark_all` | Candidates from [PR 30571](https://github.com/sympy/sympy/pull/30571) at merge `9d8ca701f8ba75b9b3cb1e23e6dcdac6572d7e73`, absent from production 1.14. `locals` is transformation substitution, not arbitrary role inference or recognition pruning; all-readings filtering/deduplication may lose alternatives our contract retains. No upgrade is required for this plan. |

### Mathematical questions and full SymPy guide scope

Retain source review O04–O07's distinction between central foundation, conditional realization
and useful future capability. PP-06 establishes the context and dispatch contract; it does not
make every available SymPy subsystem a mandatory extraction calculation.

| Guide family / requested question | Mechanism, required semantics and bounded disposition |
|---|---|
| Native structure, rewriting and assumptions (§§2–4) | `func`, `args`, `atoms`, traversal and `has` inspect native structure; `Symbol`, `Function`, declared constants, `Q`, `ask`, `refine` construct/query qualified meaning. Central PP-06 work. `subs` is mathematical substitution; `xreplace` is exact-node replacement. Keep that operation distinction and scoped unknowns. [Assumptions](https://docs.sympy.org/latest/guides/assumptions.html). |
| Polynomial/rational equality and exact domains (§5) | Route admitted polynomial cases to `Poly` with explicit generators/coefficient domain; rational cases to `together`/`cancel` plus retained denominator exclusions. Exact algebraic domains can improve eligible questions; ring reuse is conditional on repeated same-domain work. Gröbner elimination, algebraic extensions and ring series need a selected question. Do not silently change partial-function equality into rational-field equality. |
| Sets, logic, equations and inequalities (§§7/11) | Use native relation classes, `Eq`, `Contains`, `Interval`, `ConditionSet`, symmetric difference and supported `solveset`/`linsolve` questions under explicit domains. Structural `==`, residual equality and equal solution sets are different questions. `x=0` and `2*x=0` distinguish them. `.equals()`/`simplify()` are tools with undecided outcomes, not universal proof. Integer/Diophantine solving needs integer premises; propositional satisfiability is not an arithmetic prover. [Solution sets](https://docs.sympy.org/latest/modules/solvers/solveset.html). |
| Calculus, transforms, ODE/PDE and recurrences (§8) | Preserve `Integral`, `Derivative`, `Sum`, `Product`, `Limit`, `Piecewise` and supported conditions without forcing `doit`. Explicit later demand chooses differentiation, integration, convergence or solver methods. Audit inherited constructor evaluation; not every constructor is lazy. Unsupported source mappings remain adapter limits even if a native type exists. |
| Statistics/stochastic processes (§12) | Strong future consumer route: admitted random-variable/distribution/event/dependence bindings can construct `Probability`, `Expectation`, `Variance`, `Covariance`, `given`, `density` and `sympy.stats` distributions. Generic `Function`/`Given` wrappers do not supply those premises. D4 M21's Normal/moment/support verifier is a proposed consumer, not existing product support or mandatory capture. Select exact model/consumer scope before implementing these algorithms. [Statistics](https://docs.sympy.org/latest/modules/stats.html). |
| Matrices, DomainMatrix/FLINT, arrays, indexed tensors and geometry (§§6/10) | Declared shapes/index binders may use `MatrixSymbol`, `MatrixExpr`, `Indexed` or exact-domain `DomainMatrix`, avoiding eager entry expansion. Preserve ordinary decorated scalar symbols when shapes are unknown. No broad matrix/tensor/geometry workload was selected; no automatic conversion during capture. |
| Special/holonomic functions (§9) | Map admitted known functions to native special functions where qualified. Holonomic representations remain question-specific; they do not replace every expression or infer a function from typography. |
| Number theory, combinatorics and discrete transforms (§11) | Retain as on-demand families after a concrete integer/discrete question exists. Their library availability is not an extraction requirement. |
| Mechanics/control/units/quantum (§13) | Future declared domains only. Do not infer a physical model or replace existing units/knowledge contracts from symbol spelling. |
| Numerical evaluation/code generation (§14) | Keep direct `evalf(subs=...)` for current small/precision-sensitive comparisons; retained PE-04 selected direct evaluation. For genuinely repeated demand compare `lambdify` with explicit argument order/backend, joint outputs, `cse=True`, `docstring_limit=0`, `dummify=True`; compilation/CSE cost must earn reuse. `ufuncify`/`autowrap` are conditional. Code generation accepts admitted objects/functions, never unrestricted persisted input. [Lambdify](https://docs.sympy.org/latest/modules/utilities/lambdify.html). |
| Parsing/printing/custom objects (§15) | Preserve grammar/transformer strengths and source relationships; printers, `srepr` and pickle are not stable executable interchange. Custom `Function` hooks may represent selected novel semantics; expensive work belongs in requested `doit`/assessment, not eager `eval`. Never use unrestricted `eval` to reload stored text. |
| Backends and combinations (§§16–19) | FLINT/GMP may accelerate selected exact arithmetic; NumPy/JAX or compilation selected numerical kernels. Arrays/joins stay with appropriate NumPy/SciPy/Arrow/DuckDB owners. None universally removes recognition work; no automatic universal subsystem selector or second CAS framework. |

## Execution packages

<a id="PP-05"></a>

### PP-05 — Produce shared prose/TeX structure and macro provenance

**Prerequisites:** [PP-01](../parsing-pipeline_2026-10-30.md#PP-01)'s enforced lexical/structure/
mapping/context products and the relevant [PP-03](source-decomposition-and-html.md#PP-03)
source products. Pure canonical TeX/prose work can begin once its representation contract exists;
original HTML and page-definition custody require PP-03's actual qualified mappings. PP-04's
durable contract is required when products must survive operation lifetime. Do not wait for every
HTML consumer merely to extend the existing canonical scanner, and do not claim original source
provenance before its producer is ready.

1. Expose complete canonical/math-segment decomposition using the current scanner first. Retain
   outer delimiters and edge whitespace; turn `_inner` into an explicitly related parse view.
   Supply lexical categories independent of interpreted roles and composite structural links
   without multiplying native object copies. Derive TextLayout's compatible atom/token projection
   from the same coordinate authority; whole-canonical coverage includes separators and material
   outside sentence blocks supplied by PP-03.
2. Change `read_macros` to retain the existing Token extents while preserving current definition
   and redefinition semantics. Relate `_macro_table` text collection to source fragments rather
   than losing origin through `''.join(itertext())`. Record accepted/ignored/replaced definitions,
   invocation/argument/default/body extents and the selected effective macro environment. Archive
   fallback definition text/structured artifact and release selection as well as page definitions.
   Where original source extents are unavailable, retain named decoded/canonical origin and mark
   the stronger mapping unavailable; do not synthesize an exact byte offset.
3. Extend bounded expansion at the same owner to emit many-to-many derivations while preserving
   current expansion/token-form output unless an explicitly approved identity migration changes
   it. Keep source invocation at depth/token bounds, cycles or unsupported definitions. Distinguish
   original, expanded and token-form coordinates. A macro with identical output under a different
   definition still has a different dependency/custody account where provenance is requested.
4. Settle the structure-only adapter by a bounded comparison for the selected consumer: current
   scanner plus qualified native structural support versus pylatexenc 2.10 with declared context;
   consider Tokenizers only if it replaces lexical work or supplies needed alignment. Cases cover
   groups, optional/default/multiple arguments, math delimiters/environments, text mode, comments,
   unknown macros, malformed groups, scripts and macro expansion provenance. Exit by selecting
   the exact capability/recipe, retaining an unsupported outcome, or recording a missing mechanism
   that blocks the consumer. Do not add an unconditional second TeX pass or require mathematical
   equality to satisfy structure-only demand. Local exact Python signatures can follow selected
   native capabilities; public meaning must already be explicit.
5. Reuse one configured spaCy pipeline per valid worker and shared source-bound layout for M03,
   M13 and matching consumers; instantiate independently mutable Docs. Preserve annotation/model
   prerequisites and exact ranges after retokenization. PP-07 quote placement consumes layouts and
   alignment evidence rather than retokenizing through an unrelated coordinate owner. PP-04/09
   integrate durable build selection; source/rendition equality alone cannot choose a layout/map.

PP-05 finishes when complete source-bound capture and selected structure capabilities, including
macro derivations, work through their actual consumers and expose truthful unsupported/partial
states. It does not finish PP-06's interpretation, PP-07's complete placement recipe, PP-09's
publication/read contract or PP-10's whole public journey.

<a id="PP-06"></a>

### PP-06 — Redesign lazy interpretation and migrate mathematical consumers

**Prerequisites:** PP-05's usable decomposition/parse-view/context products and
[PP-01](../parsing-pipeline_2026-10-30.md#PP-01)'s enforced demands, interpretations and method
contracts. [PP-04](../parsing-pipeline_2026-10-30.md#PP-04) is required for durable context/products
and readback, and [PP-08](../parsing-pipeline_2026-10-30.md#PP-08)'s actual ownership/cancellation/
deadline route must be ready before any newly retained demand result is published. Pure preparation
can be developed before runtime publication is ready; it cannot certify the latter.

First settle the method boundary against actual consumers. Selected direction is broad complete
capture with independently requested stronger interpretation, using one prepared expression
owner. Keep M09 interpreted mentions/relations and M11 interpreted values as named capabilities;
allow their capture/structural output to be useful without asserting those stronger results.
Choose whether the lower capability is an explicit companion method or a versioned output of
the existing methods by examining scheduling, task digests, public methods and existing callers.
The exit must state exact method IDs/versions, payload versions, output kinds, eligible input
universe, required demand, coverage semantics and direct caller migration. This is a bounded
design decision, not permission to leave the old promises running over weaker data.

| Consumer boundary | Required coherent migration |
|---|---|
| M09 `extract.math` | Lexical candidates/structure remain distinct from interpreted symbol mentions and value-level relations. Preserve source occurrence multiplicity and ordering; emit interpreted relations only when their demand succeeds. A total lexical result can coexist with ambiguous interpretation without reporting complete interpreted extraction. |
| M11 `normalize.formula` | Retain source expression and parse-view custody without fabricating `parse=ok` or mathematical kind. Version values/coverage if capture is available before interpretation. Consolidation's direct LaTeX/proposal callers request the required interpretation, not a hidden eager fallback. |
| M13 `resolve.symbol_scope` | Declare the actual prerequisites of each rule: structural candidates, interpreted relation/kind, prose annotations and admitted context. Ensure required stronger demand is available before a rule uses it; unavailable/ambiguous inputs give explicit coverage/refusal. Preserve ordinal references or migrate them together with stored references and semantic occurrence IDs. Never feed M13's result back into its own upstream capture. |
| Standing context, packets and source frames | Preserve binding-site source extents and current standing-context scope. Missing interpretation/scope is unavailable coverage, not proof of no relevant context. PP-09 supplies archived selection; PP-10 updates public contracts/frames coherently. |
| Consolidation, scientific comparison, rules/verifiers | Use the shared prepared owner with explicit kind/roles/assumptions/definedness and named question. Keep identity policy independent from equivalence and preserve differences between native proof, numerical evidence, counterexample and undecided. Rules that need parsing continue on the process-main-thread route, never MCP threads. |
| Evaluation/reference comparisons, observations/measurements/exports | Pin source/build/release and payload compatibility; keep reference inputs/preparation/policies separate. Migrate coverage denominators, reports and queries with changed demand meaning, without changing grading policy merely because parsing changes. PP-10 owns assembled adoption. |

Extend `PreparedMathInput`/`PreparedInterpretationContext` rather than introduce another cache
service. Distinguish reusable syntax from context-qualified readings, native values and question-
specific assessments. A syntax-only entry point must bypass `_Resolver.value`; if ambiguity needs
native equality, retain alternatives under the weaker result or explicitly satisfy interpretation
demand. Do not report no symbolic work merely because `symbolic_value()` was not called.

Compile admitted roles/assumptions into native construction before transformations use them.
Keep legitimate unknown/conflicting declarations, binder scopes, source definedness and
convention basis inspectable. Qualify selected native constructors/questions against revealing
cases: `f(x)` function/product ambiguity; same spelling under two scopes; `sqrt(x**2)` under
unknown-complex/real/positive assumptions; `x/x` at zero; `x=0` versus `2*x=0`; unsupported set
or statistical notation; an unevaluated integral; an inconclusive solver/property result.
Realize existing admitted cases and expose typed support limits. Broader native statistics,
matrix/solver/backend families require concrete selected semantics/consumer demand before
implementation; their absence cannot be disguised by a generic function named like the construct.

Key each product on exactly its meaning-bearing dependencies: representation/text and coordinate
binding, frontend/grammar revision, profile/kind, effective macros, scoped declarations including
absent declarations, assumptions and transformer/library implementation. A purely lexical key
need not include unrelated scientific policy. Assessment keys additionally include operands,
conditions, question, decision/evidence policy, precision and sampling. Bind occurrence anchors
separately from reusable relative computation. In particular, adding a previously absent function
declaration invalidates the interpretation that relied on absence. Timeouts remain retryable and
must not poison semantic caches.

Use the rendition/comparison/operation scope first. Avoid unbounded retention of native trees or
`Basic` objects. Durable decomposition/context enables later reconstruction when useful; retained
native output needs an explicit versioned interchange compatibility contract, not `srepr`/pickle
assumed executable forever. On-demand work pins archived source and release instead of current
defaults, and publishes a new immutable product through PP-08/09 rather than mutating a completed
run. Reference evaluation can reuse pure algorithms but cannot seed extraction/context caches,
declarations, random seeds or decisions from reference answers.

Migrate method/config/digest identities, model release definitions, generated payload boundaries,
native storage compatibility and all actual readers together. Current `VERSION="3"` and
`PAYLOAD_VERSION="1"` cannot be reused for changed meanings. Coordinate new admitted version
selection with PP-00/01/04/09/10; explicitly rebuild affected derived observations/measurements when
needed and preserve old archived interpretation under its recorded version. Do not overwrite
historical anchors, change token keys without their migration, or add a permanent compatibility
pipeline without a real consumer. Retire duplicated preparation/scans and obsolete output readers
after cutover; current public callers must not silently invoke an old eager route.

## Acceptance, lifecycle and qualification boundary

Local execution checks should target the responsible producer/consumer, not launch a full corpus
campaign per slice. Existing homes include `python/corpus-structure/tests/core/test_tex.py`,
`tests/ingest/test_html.py`, `tests/math/test_spans.py`, `tests/math/test_prepared.py`,
`tests/math/test_scope.py`, `tests/semantic/test_shared_math.py`,
`tests/semantic/test_expression_context.py` and `tests/semantic/test_stored_text_layouts.py`
under the product project. A future focused command is `uv run pytest
python/corpus-structure/tests/math/test_prepared.py
python/corpus-structure/tests/math/test_spans.py
python/corpus-structure/tests/semantic/test_shared_math.py`; select other tests from the actual
changed contract. The root owns maintenance and final required-union qualification. Tests and
probes are **not_run** for plan authoring; only read-only document/source inspection occurred.

Completion needs independent expectations capable of detecting these mistakes:

- Lexical partitions cover the entire original math Segment and canonical input, with correct
  categories and exact parse-view mapping. Unknown/invalid syntax still yields complete lexical
  capture; syntax acceptance does not grant mathematical completeness. Hand-established ranges
  and macro provenance cases challenge the production transformation rather than using its own
  expanded text as expected origin.
- Macro tests include defaults, repeated arguments, later page redefinitions, page/fallback
  overrides, absent definitions, excluded definition blocks, multiple named artifacts and bounded
  expansion. Effective value equality does not erase different custody. The actual definition
  producer retains offsets; a populated mapping table alone is insufficient.
- Weak demands perform only their declared work; stronger demands share compatible preparation.
  Independent observations of entry-point invocation can catch hidden `_Resolver.value` work
  without a permanent instrumentation framework. Context or implementation changes invalidate
  appropriate products while two source anchors retain distinct occurrences under eligible reuse.
- Ambiguity and assumptions produce the declared outcomes; `None`, unsupported, timeout and
  cancellation never become false, absent or complete. Same-name bound/free variables and source
  domain holes survive native normalization. Numerical agreement is never relabeled symbolic proof.
- M09/M11/M13 and direct consolidation/rule callers use the new versioned demand/payload contract.
  Their scope references, packet standing context, coverage and readback remain meaningful;
  selected build/release is explicit, and missing historical products follow a declared remedy.
- Archived on-demand interpretation survives changed current defaults, reference data cannot
  influence source preparation, and cancelled/failed work cannot publish a complete product.
  These durable/runtime/publication journeys require PP-04/08/09 acceptance, beyond pure unit tests.

Benefits remain **Proposed**: weaker consumers avoid unnecessary recognition, compatible consumers
reuse actual preparation, and explanations retain source distinctions. If a quantitative
performance claim becomes relevant, measure a representative mix of weak and strong demands,
including first-use preparation and failures. Existing component/historical receipts are not
new product qualification. Open capability choices and missing prerequisites remain at the
coordinator's PP owners rather than being treated as completed work here.
