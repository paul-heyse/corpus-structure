# Complete mathematical decomposition and demand-driven interpretation

**Proposed · library-focused functional review · 2026-10-30.** Inspected production baseline:
`599d47943b842684e315b7194906bd74b1d0d6a2`. The concurrent edits to
`docs/design_review/test-audit/execution-and-qualification.md` and `retirement-transfer.md`
are outside this inquiry. This review proposes changes; it does not change accepted plans,
audit premises, deployed releases, grades or production behavior.

## Recommendation

Make a complete, source-preserving decomposition the shared foundation for mathematical work.
Every source component has a category and half-open start/end coordinates, including components
excluded from a mathematical calculation. Interpret that decomposition through SymPy when a
consumer needs mathematical meaning or calculation. Share compatible preparation and results.

The operator's clarification is decisive: this is a decomposition capability, not just a list of
symbols or a simplified expression. Braces, delimiters, spaces, presentation commands, operators,
text, unknown commands and invalid fragments remain inspectable. Excluding something from a
projection never means deleting it from the decomposition.

SymPy should own supported mathematical representation and algorithms. The domain model owns
which declarations, assumptions, conventions, operations and evidence policies are authorized.
Source occurrence identity remains independent of the symbolic value. These responsibilities
compose; they do not require competing mathematical interpretations.

## Scope, sources and evidence limits

The inquiry covers current source extraction/normalization, rule projections, consolidation,
reference comparison, mathematical identity and credible downstream mathematical questions.
It reads the full capability guides [SymPy](../libraries/parsing/Sympy.md) and
[Tokenizers](../libraries/parsing/tokenizers.md), current Context7 documentation, installed SymPy 1.14.0
and Lark 1.3.1 source, and consequential upstream changes. Static code mapping and independent
architecture/library contributions inform the recommendations. No new product test campaign,
benchmark, dependency installation or database operation was performed for this review.

The governing assessment is core 3.3, its efficient-architecture companion, the applicable
code-intelligence fidelity principles and the repository binding in
[standard.toml](../design_review/design_principles/standard.toml). Especially relevant are FP-04,
FP-05, FP-07, DP-09/13–15 and H4/H6/H12/H15/H28: explicit meanings, complete dependencies,
library delegation and avoiding unnecessary work. This is capability exploration, not a refreshed
diagnostic audit or a claim that the entire codebase meets those principles.

Installed APIs and documented semantics are **Interface-checked** on 2026-10-30. Proposed designs,
coverage improvements and performance benefits remain **Proposed**. Earlier small interactive
examples showed `f(x)` returning function/product alternatives and `x+x` becoming `2*x`; these
illustrate representation differences and supply no corpus coverage or performance result.

## What the code already does

| Responsibility | Actual production route | Implication |
|---|---|---|
| Full lexical coverage | [`core/tex.py`](../../python/corpus-structure/src/corpus_structure/core/tex.py), especially `Token`, `tokens`, `_TOKEN` | Already returns every source character in categorized pieces with code-point offsets, including whitespace and unknown characters. The foundation need not start with another lexer. |
| Recognition | [`math/grammar.py`](../../python/corpus-structure/src/corpus_structure/methods/math/grammar.py), `Parser` and `_reading` | Extends SymPy's shipped LaTeX grammar; Earley recognition retains ambiguous alternatives and propagates source positions. We already leverage SymPy parsing. |
| Meaning and construction | [`math/transform.py`](../../python/corpus-structure/src/corpus_structure/methods/math/transform.py), `ToSympy` | Subclasses SymPy's native transformer, retaining shipped methods and adding supported sets, relations, operators and decorated symbols. Generic functions do not automatically acquire statistical meaning. |
| Source observations | [`math/spans.py`](../../python/corpus-structure/src/corpus_structure/methods/math/spans.py), `read_spans`, `symbol_mentions`, `formula_values` | M09 emits positional occurrences/relations; M11 emits source expressions, bindings and interpretation status. It does not persist every lexical component. |
| Demand and reuse | [`math/prepared.py`](../../python/corpus-structure/src/corpus_structure/methods/math/prepared.py), `PreparedMathInput` | Already retains a reading and constructs its symbolic value lazily. Compatible M09/M11 batches share readings; the grammar also has a bounded memo. This is an extension of existing preparation, not a wholly new service. |
| Context authority | [`semantic/analysis_contracts.py`](../../python/corpus-structure/src/corpus_structure/semantic/analysis_contracts.py) | Release-derived demands, declarations, scopes, assumptions, recipes and dependencies exist. Assumption bytes contribute to identity, but `grammar_context` currently projects roles/constants rather than a complete SymPy assumption environment. |
| Mathematical assessment | [`semantic/scientific_evidence.py`](../../python/corpus-structure/src/corpus_structure/semantic/scientific_evidence.py) | Uses native SymPy sets, relations, polynomial cancellation, simplification and numerical evaluation. Operand/condition reuse exists. Consolidation and reference comparison retain distinct policies and preparation lifetimes. |
| Identity | [`core/keys.py`](../../python/corpus-structure/src/corpus_structure/core/keys.py), `canonical_value` | Token forms, bindings and qualifications determine semantic identity. SymPy equivalence does not currently redefine stored identity. |

There is one important limit to present laziness: `_Resolver.value` can construct SymPy values
while resolving ambiguity inside `reading()`. Avoiding an explicit `symbolic_value()` call does
not mean that recognition/interpretation performed no symbolic work. M09/M11 currently require
interpreted outcomes, and M13 consumes their observations; their work cannot simply be skipped
while continuing to publish the same completeness/status claims.

## O01 — A complete decomposition with explicit links to interpretation

<a id="O01"></a>

**Recommended foundation.** Retain immutable source text and a complete ordered partition. Each
piece has source identity, start, end, lexical category and its original spelling obtainable by
slicing the source. Repeated pieces have distinct occurrence identity. Store text once; materialize
the substrings only where useful. Existing code-point coordinates remain the canonical-text
coordinate system; original HTML/file-byte coordinates are a separate mapping, never silently
treated as interchangeable.

Cover the original math `Segment`, including outer delimiters and edge whitespace. Current
`spans._inner` removes those from the parser input; retain that input as an explicitly mapped
parse view of the complete segment. Trimming or dropping presentation commands changes the
view, not the retained source partition. The existing scanner's lexical `symbol` category means
a TeX control symbol, not a resolved mathematical symbol; a public decomposition must name that
distinction clearly.

For `x + x`, the partition is:

| Range | Source slice | Category |
|---|---|---|
| `[0,1)` | `x` | identifier candidate |
| `[1,2)` | space | whitespace |
| `[2,3)` | `+` | arithmetic operator |
| `[3,4)` | space | whitespace |
| `[4,5)` | `x` | identifier candidate |

SymPy can construct `2*x` without changing any of those five pieces. Its `x` relates to both
source occurrences; its coefficient `2` is derived and has no literal `2` occurrence. This is why
symbolic-object identity cannot be used as occurrence identity, and also why source positions do
not need to be lost.

Keep lexical categories distinct from interpreted categories. A TeX control word can become a
function, macro invocation, formatting instruction, constant or unknown command depending on
the admitted context. An identifier candidate is not automatically a resolved mathematical
variable. Preserve a complete decomposition when interpretation is unknown or fails.

Add syntax relationships over the partition where needed: grouping, numerator/denominator,
base/subscript/exponent, argument lists, binder and bound references. These can overlap the
partition. For example, `\sigma_{X_1}` contains several lexical pieces and a composite symbol
occurrence; its indexed content can also have its own meaningful occurrence. Do not force nested
or overlapping syntax into one flat sequence of disjoint semantic symbols.

Make the interpretation links explicit where a consumer needs them: occurrence to syntax
construct, construct to symbolic object/result, role/assumption to its declaration, and exclusion
from a particular projection to its reason. They may be many-to-many. A discarded presentation
command remains a categorized source piece; a simplified-away term retains source identity.
One expression-level origin is insufficient when an answer claims which subexpression supplied
a result. Conversely, extraction need not store a trace of every internal algebraic rewrite.

Macro expansion needs a distinct source-to-expanded mapping when expansion changes the string
being parsed. Expansion output may originate from an invocation, argument and definition; those
ranges cannot all be represented by one guessed offset. Current `tex.expand` provides expanded
tokens but not that full provenance relation. If the grammar reads the original macro invocation,
retain those original positions directly. Never assign expanded-string offsets to source text.

**Storage recommendation:** persist the useful decomposition alongside existing expression/source
products using model-derived types. A compact sequence of token records is a plausible physical
form; joins that actually need occurrence or binding identity can use relational rows. No separate
PostgreSQL row, task or index is required per whitespace piece. Neither all intermediate Lark trees
nor all SymPy objects need durable storage. Unknown raw components and incomplete decompositions
must be distinguishable; a caught scanner limit cannot masquerade as a complete partition.

### Does Tokenizers help?

Yes, it supplies real mechanisms for the proposed source partition:
`pre_tokenizers.Split(Regex(...), behavior="isolated").pre_tokenize_str(...)` can retain matches
and unmatched stretches with original character offsets. `NormalizedString` maintains alignment
when supported normalization changes characters. A full `Tokenizer` and learned vocabulary are
unnecessary merely to obtain such boundaries.
[Tagged Python pre-tokenizer binding](https://github.com/huggingface/tokenizers/blob/v0.23.3/bindings/python/src/pre_tokenizers.rs#L183),
[split implementation](https://github.com/huggingface/tokenizers/blob/v0.23.3/tokenizers/src/pre_tokenizers/split.rs).

For this codebase, first extend/reuse `core.tex.tokens`, whose scanner already provides total
coverage, categories and exact coordinates used by macro reading and keys. A generic Tokenizers
split does not itself supply capture-group category labels, nested TeX semantics or macro
provenance. `contiguous` can merge adjacent matches, which may erase desired lexical boundaries.
Vocabulary encodings may split a mathematical symbol into subwords; language-model token identity
is not mathematical occurrence identity. Retaining only encoded tokens can omit whitespace or
introduce synthetic special-token offsets, depending on configuration.

Compare a native Tokenizers lexical implementation if it can replace the current scanner while
preserving these contracts, or when normalization/alignment reuse is itself valuable. Do not run
both TeX lexers permanently. Tokenizers 0.23.3 is present in retained spike dependencies, not the
product manifest inspected here; adoption would be an explicit dependency and lexical-recipe
change. The recommendation favors the complete decomposition, not a predetermined lexer.

## O02 — Extend laziness to the computation actually requested

<a id="O02"></a>

**Recommended.** Use one owned prepared expression whose capabilities are requested as needed:

- Complete lexical decomposition and original source slices.
- Supported syntax structure and candidate occurrences.
- Contextual interpretation, including remaining alternatives and qualified roles.
- A SymPy object for an admitted interpretation.
- Specific assessments, transformations or numerical calculations.

These are capabilities and dependency boundaries, not five mandatory persisted artifacts or
serial jobs. A lexical request must not secretly perform general recognition or symbolic equality.
An occurrence request that requires binding structure may still need parsing. A mathematical
question may require the entire expression even when it returns only one property.

The observable distinctions must include not requested/not computed, available, ambiguous,
unsupported, invalid, timed out and failed where applicable. An unevaluated `Integral` is an
available representation with an unevaluated calculation, not a parse failure. SymPy's `None`
property answer is unknown, not a false assertion. A missing assessment row does not imply that
an expression has no relevant property.

There are two useful adoption boundaries. First, keep M09/M11's existing interpretation obligations
while removing redundant preparation and delaying optional values/assessments. Second, if broad
corpus capture should become decomposition-only, explicitly introduce that capability and change
M09/M11/M13 scheduling, status, coverage and downstream requirements together. Required
interpretation must execute before a consumer relies on it. Lazy execution shifts latency to the
first demander and does not remove work that every expression must eventually undergo.

If ambiguity resolution still requires SymPy comparison, either fulfill interpretation demand at
that point or preserve pending alternatives for a weaker decomposition result. Do not call an
unresolved candidate an interpreted result. Parsing one expression once means one shared result
per compatible source/context/recipe within its supported lifetime; it is not a promise never to
recompute after eviction, process restart or changed context.

## O03 — One context and preparation boundary, with deliberately scoped reuse

<a id="O03"></a>

**Recommended.** Extend `PreparedInterpretationContext` and `PreparedMathInput`; do not add another
math gateway, global cache or generic workflow engine. Reuse compatible syntax products and
symbolic values across real consumers. Keep occurrence anchors separate so identical expression
text in two locations can share eligible computation without becoming one source occurrence.

Product keys must include the dependencies that can affect that product: exact text/coordinate
binding, frontend recipe, effective macros, permitted kind, declaration scope and explicit missing
declarations, assumptions, operator interpretation and library/adapter revision. Assessment keys
add both operands, conditions, mathematical question, evidence policy, precision and sampling
parameters. Negative lookups matter: adding a previously absent function declaration changes an
earlier ambiguous interpretation. Source/custody metadata may share a relative computational
product only when its semantic dependencies are genuinely equal.

Choose reuse at the existing rendition/comparison/operation lifetime first. Avoid cloning a full
syntax tree per request or keeping an unbounded corpus of live `Basic` objects. Durable products
are justified when later independent operations need them; otherwise rebuild from retained
decomposition/context. Do not assume `srepr`, printed LaTeX or pickle is a stable executable
interchange contract. Keep typed source/context and supported derived result representations,
with versioned compatibility; never reconstruct stored text through unrestricted `eval`.

Consolidation and independent evaluation may reuse an implementation of pure mathematical
operations, but they retain separate input custody, caches, seeds and evidence decisions. Reference
data must not populate extraction preparation or influence source interpretation. Later on-demand
requests pin the expression's archived release and context rather than reading current defaults.
Computation remains outside protected publication transactions; newly retained assessments use
the existing immutable, fenced publication route instead of mutating a completed historical run.

## O04 — Compile declarations into native mathematical objects and assumptions

<a id="O04"></a>

**Recommended next mathematical improvement.** The model's declarations should construct the
right SymPy `Symbol`, `Function`, constants, sets and, where declared, shaped/indexed objects.
Use structural inspection (`func`, `args`, typed traversal, `atoms`) for operations and
`free_symbols` only for its stated free-variable meaning. It is a set and cannot count occurrences
or represent bound variables. Preserve binder scope for sums/integrals and distinguish two same-name
variables with different meanings. `Dummy`/`as_dummy` can support deliberate bound-variable
normalization; they cannot supply a source binding that was never established.

Project justified assumptions into symbol construction and explicit `Q` predicates, then use
`ask`/`refine` for supported questions. For example, `sqrt(x**2)` requires different treatment for
an unknown complex value, a real value and a positive value. Conditions and assumptions must
remain evidence-backed and scoped, including contradictions and unknowns. Hashing assumption
bytes without supplying them to the mathematical operation is insufficient.
[SymPy assumptions](https://docs.sympy.org/latest/guides/assumptions.html).

Lower only supported, model-admitted condition forms into `Q` predicates. Arbitrary relational
conditions are not automatically usable assumptions: installed 1.14's `ask` documentation
specifically warns about inferring `Q.positive(x)` directly from `x > 0`. Retain unlowered
conditions and report an inconclusive property rather than dropping them. Keep assumptions
operation-local, avoiding ambient global assumptions that could leak between documents.

Do not silently assume every document symbol is real, every `P` is probability or every `f(x)` is
a function. Model-admitted conventions can select a reading, but retain that basis as a convention
or declaration rather than claiming the text alone established it. More context is useful only
when available through an authorized non-circular producer; M13's later resolution cannot be a
hidden prerequisite of the extraction that feeds M13.

Reconcile existing conventions explicitly: the current transformer maps `N` to `Naturals0` and
uses `S.Reals` for an unqualified set-builder. These choices need admitted model meaning and
recorded basis just as function/constant conventions do; native defaults are not source evidence.

### Version boundary and upstream parser developments

Installed SymPy 1.14.0 supports `LarkLaTeXParser(transform=False, grammar_file=..., transformer=...)`.
It parses first and optionally transforms afterward. Its stock parser does not propagate branch
positions, although token leaves have positions; ignored material is absent from the parse tree.
Our current parser enables propagated positions and adds necessary grammar extensions. Replacing
it with a stock `parse_latex` call would not automatically preserve these capabilities.
[Pinned parser source](https://github.com/sympy/sympy/blob/1.14.0/sympy/parsing/latex/lark/latex_parser.py#L43).

PR [#30571](https://github.com/sympy/sympy/pull/30571), merged 2026-10-21, adds wider grammar
support, `locals` overrides and `parse_latex_lark_all` in development code. `locals` replaces
permitted named constants/functions during transformation after parsing; it does not infer all
symbol roles or prune recognition from arbitrary variable declarations. The all-readings API
also applies a parallel-choice filter and deduplicates mathematical results. It is not a complete
source decomposition or a guarantee to preserve our independent ambiguity combinations.

The source at merge commit
[`9d8ca701`](https://github.com/sympy/sympy/blob/9d8ca701f8ba75b9b3cb1e23e6dcdac6572d7e73/sympy/parsing/latex/lark/latex_parser.py)
is the inspected development baseline; it is not installed production support. Context7 returned
some synthesized Lark signatures containing `local_dict`/`global_dict` that disagree with source;
those signatures are not adoption evidence. Reassess newer SymPy against the grammar/transformer
hold in [pins](../pins.md). Review and retire local extensions where upstream genuinely replaces
them, preserving independently needed behavior. An upgrade is a candidate, not the prerequisite
for the decomposition/laziness design.

## O05 — Ask a precise mathematical question before choosing the algorithm

<a id="O05"></a>

**Recommended.** Consolidate shared mathematical mechanisms while retaining model-owned question
and decision profiles. Current code already uses native SymPy; the improvement is to specialize
operations by mathematical meaning rather than apply a broader generic simplifier everywhere.

| Requested meaning | Suitable native mechanisms to assess | Conditions and limits |
|---|---|---|
| Operation/function/symbol classification | `func`, `args`, `atoms`, `has`, traversal | Describes the interpreted representation, not every original occurrence. |
| Exact structural equivalence | `==`, explicitly governed binding normalization | Different structure is inconclusive for mathematical equivalence. |
| Polynomial equality | `Poly`, explicit generators/domains, exact coefficient comparison or subtraction | Confirm polynomial eligibility and coefficient meaning before conversion. |
| Rational-function equality | `together`, `cancel`, numerator/denominator analysis | Preserve original definedness and denominator exclusions; field equality and equality as partial functions differ. |
| Assumption-dependent simplification | `ask`, `refine`, specific supported transformations | Unknown remains unknown; branch/domain premises accompany the result. |
| Sets, domains and solution sets | `Contains`, `Interval`, `ConditionSet`, symmetric difference; `solveset`/`linsolve` for supported questions | Empty/unevaluated/unknown are distinct; a failed solver is not proof of inequivalence. |
| Mathematical substitution | `subs` | Binding-aware mathematical substitution differs from exact-node `xreplace`. |
| Formula relation/equation comparison | `Eq`, relation classes, explicitly scoped residual or solution-set comparison | Same residual up to sign, algebraic rearrangement and same solution set are different contracts. |

The current polynomial-only cancellation guard is useful but cannot restore information already
removed during ordinary expression construction. For instance, a constructed `x/x` can become
`1` before a comparison sees it. Source decomposition and original operator relationships make
it possible to retain definedness obligations before construction/simplification. Ordinary
`evaluate=False` can help at selected constructors; it is not a complete source-location or
definedness solution. Audit each selected transformation's premises during implementation.

Likewise, `x=0` and `2*x=0` have the same solution set over ordinary real scalars, whereas the
functions `x` and `2*x` differ. A solution-set operation is a worthwhile additional capability,
not permission to change the existing residual-comparison policy silently. SymPy can leave a
`ConditionSet` when a supported solver cannot fully resolve the answer. Broad `.equals()` and
`simplify()` remain possible tools, not universal proof procedures or replacements for typed
outcomes. [Best practices](https://docs.sympy.org/latest/explanation/best-practices.html),
[solution sets](https://docs.sympy.org/latest/modules/solvers/solveset.html).

Native numerical sampling is still evidence under the declared policy, not symbolic proof.
Retain separate consolidation/reference decisions, deterministic sampling and condition handling.
Do not treat tolerances, counterexamples, unknowns or numerical agreement as interchangeable.

## O06 — Use unevaluated native representations for richer mathematics

<a id="O06"></a>

**Recommended where supported; extensions need explicit semantics.** Preserve `Integral`,
`Derivative`, `Sum`, `Product`, `Limit`, `Piecewise`, sets and mathematical relations as native
objects without immediately evaluating them. Invoke `doit`, a targeted transformation, solver
or numerical operation only when requested. Much of the shipped transformer already constructs
unevaluated calculus objects; review the inherited constructor/evaluation behavior rather than
assuming all SymPy calls are lazy or that all require calculation.

Probability/statistics is particularly relevant to this corpus. Current generic `Function`
objects and a generic `Given` wrapper do not give SymPy the random-variable/distribution/dependence
model required by `Probability`, `Expectation`, `Variance`, `Covariance`, `given`, `density` or
`sympy.stats` distributions. Extend the model's declared roles and bindings, then construct those
native objects when their premises are established. Undefined functions remain a sound
representation where only a name/application is known. Do not infer a distribution, independence
or event semantics from typography alone. Evaluating a supported probability question becomes
a distinct requested calculation, with unknown distribution/dependence retained explicitly.
[SymPy statistics](https://docs.sympy.org/latest/modules/stats.html).

This is a stronger domain-model opportunity than merely adding faster symbol extraction:
the same qualified statistical object could support extraction explanation, source-grounded
formula comparison and later analytical questions. These are proposed consumer capabilities;
their presence in the library does not make them current requirements or qualified product support.

There is already a concrete architectural consumer: [D4 M21](../design/D4-method-catalog.md#m21-verifystatistics)
proposes affine-normal, moments and support verifiers using `sympy.stats.Normal`, `E`, variance
and support comparison. Static inspection of production Python and `domains/statistics` found
no `sympy.stats` calls; this is a proposed route, not an implemented verifier claim. Its declared
premise claims and parameter bindings are the appropriate inputs for native statistical objects.
The decomposition foundation can support it without making verification mandatory for every span.

Also distinguish library limits from adapter limits. Current transformer refusals for cases,
subset relations and other constructs identify unsupported mappings in this interpreter; native
`Piecewise`, set and function representations may cover some of them once the source meaning
and adapter contract are established. A constructor's existence alone does not settle ambiguous
norms, extrema, event sets or convergence notation.

## O07 — Specialize repeated execution only after a useful demand exists

<a id="O07"></a>

**Conditional.** For repeated numerical evaluation of the same admitted expressions, prepare
`lambdify` callables once with explicit argument order/backend and consider joint outputs,
`cse=True`, `docstring_limit=0` and `dummify=True`. Bind varying points/parameters afterward.
`evalf(subs=...)` remains appropriate for small or precision-sensitive comparisons. CSE itself
and compilation add work; the retained PE-04 investigation selected direct evaluation for the
current small comparisons, so this review does not reverse that result without a new workload.
[Lambdify](https://docs.sympy.org/latest/modules/utilities/lambdify.html).

Generated functions require admitted expressions/functions and explicit numerical semantics,
including singularities, complex branches, precision and backend behavior. `lambdify` is code
generation, not a parser for unrestricted stored input. `ufuncify`/`autowrap`, native exact-algebra
backends and alternative symbolic engines merit investigation only when a particular demand
benefits; none removes general LaTeX recognition work. Keep numerical arrays/joins in the
appropriate NumPy/SciPy/Arrow/DuckDB route rather than replacing them with scalar SymPy loops.

## Full SymPy capability assessment

The full guide was used to assess applicability, not to adopt every subsystem. The following
dispositions cover its capability families and preserve useful future leads:

| Guide sections | Applicability to this target |
|---|---|
| §2–4 representation, assumptions, rewriting and CSE | Central: native objects, explicit assumptions, targeted interpretation and deferred calculation; source decomposition remains alongside them. |
| §5 polynomial domains, rings, algebraic numbers, Gröbner bases and ring series | `Poly` and exact domains are relevant to bounded equality/normalization. Dedicated rings can amortize repeated same-domain operations. Gröbner elimination, algebraic extensions and ring-series computation need a concrete mathematical question; do not run them during extraction. |
| §6 matrices/DomainMatrix/FLINT | Relevant future representations for declared matrix expressions and exact systems. `MatrixExpr` avoids eager entry expansion; `DomainMatrix` serves exact-domain algorithms. No current general matrix workload was established that warrants changing extraction. |
| §7 equations/inequalities/Diophantine solving | Solution-set questions can improve assessments under explicit domains. Numerical roots and unrestricted solving do not establish complete equivalence; integer-specific solvers require a declared integer problem. |
| §8 calculus, transforms, ODE/PDE and recurrences | Native unevaluated objects fit lazy interpretation. `diff`, integration, convergence conditions, solver classification and recurrence operations support later requested analyses. No automatic solve-every-formula stage. |
| §9 special/holonomic functions | Map declared known functions to native special functions where qualified. Holonomic representations are a useful later algorithmic choice, not a default replacement for every formula. |
| §10 matrices/arrays/indexed tensors/geometry | Use declared shapes and index/binder semantics; `Indexed` and `MatrixSymbol` can avoid opaque scalar names when the domain actually establishes those meanings. Retain ordinary decorated symbols when it does not. |
| §11 sets/logic/number theory/combinatorics/discrete transforms/geometry | Sets and qualified logical conditions are immediately relevant. Other families remain on-demand question-specific capabilities; propositional satisfiability is not a universal arithmetic prover. |
| §12 statistics/stochastic processes | Strong functional opportunity after distribution, event and dependence bindings are modeled; retain unevaluated probability/expectation until requested and supported. |
| §13 mechanics/control/units/quantum | Native models are valuable for a future declared domain. Do not replace current knowledge-graph/units contracts or infer a physical model merely because a symbol resembles one. |
| §14 numerical evaluation/code generation | Repeated numerical workloads can specialize once; retain precision/evidence policy and compare preparation burden. Code printers are not complete deployable runtimes. |
| §15 parsing/printing/custom objects | Reuse native LaTeX grammar/transformer and retire replaced extensions where qualified. Custom `Function` hooks can represent supported novel mathematics; expensive work belongs in explicit `doit`/assessment operations rather than eager `eval`. |
| §16 backends/dependencies | FLINT/GMP accelerate supported exact arithmetic; NumPy/JAX and compilation accelerate selected numerical execution. They do not universally accelerate parsing or source decomposition. |
| §17–19 combinations, specialized subsystems and sources | Representation can change with the question under explicit mappings. No separate universal CAS wrapper or automatic subsystem selection framework is justified by this inquiry. |

## Alternatives and net work implications

| Complete approach | Judgment |
|---|---|
| Retain current eager interpretation with local caches | Useful current behavior and lowest immediate change, but no durable complete decomposition and limited ability to serve weaker demands without recognition. |
| Call stock `parse_latex` and inspect the resulting expression | Too weak as the complete source contract: ignored syntax, canonicalization, occurrence multiplicity, our grammar extensions and interpretation conventions need explicit treatment. |
| Persist a complete source decomposition, interpret through the existing SymPy-based owner on demand | Preferred. Retains existing strengths and supplies the missing reusable source capability; model/consumer changes are explicit. |
| Add Tokenizers as an additional permanent TeX pass, then run the current pipeline unchanged | Does not remove recognition work and duplicates lexical ownership. Select only if it replaces a responsibility or supplies otherwise-needed alignment. |
| Persist every alternative/tree/rewrite and every possible assessment eagerly | Unnecessary amplification and retention. Preserve useful decomposition, needed ambiguity and explicit outcomes; compute mathematical questions as requested. |

The descriptive savings are deferred recognition for consumers that only need decomposition,
shared recognition where consumers currently prepare separately, avoided symbolic conversion for
consumers that never ask for it, and reuse of compatible native objects/assessments. Total lexical
capture and storage add work. Existing M09/M11 sharing and lazy conversion are already present,
so they cannot be counted again as new benefits. If every expression still needs interpretation
under unchanged contracts, this design alone does not remove that recognition work. It also does
not establish an Earley speedup, corpus runtime reduction or lower memory footprint.

## Integration, priorities and remaining decisions

1. Establish O01's complete decomposition and projection-exclusion contract, reusing the current
   TeX scanner first. Decide persistence granularity from actual query/consumer needs, retaining
   all components without duplicating source strings or inventing a generic math database.
2. Implement O02/O03 as extensions of the existing model/preparation boundary. Decide which
   existing methods keep interpretation requirements and which new decomposition-only capability
   is needed. State materialized-demand outcomes explicitly and preserve M13 dependencies.
3. Make O04/O05's context, assumptions, binder identity, definedness and mathematical question
   explicit before broadening native transformations. Compare newer upstream parser support
   against actual local extensions and the pinned hold; do not depend on synthesized API claims.
4. Pursue O06's statistical and other native representations when their model prerequisites and
   concrete consumers are selected. Revisit O07 only for repeated numerical workloads that warrant
   preparation. These capabilities can be adopted incrementally without another global engine.

Material investigation questions remain: which decomposition categories and overlapping syntax
relationships actual consumers need; where source-to-expanded provenance is required; which
declaration producers can supply context early; the mathematical equality/definedness contract;
useful persistent product granularity; and qualified upstream replacement coverage. These are
bounded design questions for subsequent planning, not reasons to discard the overall direction.

Acceptance examples should expose `x+x` with two occurrences, ignored formatting/whitespace,
nested decorated symbols, invalid/unknown fragments, expanded macros with original origins,
bound/free same-name variables, `f(x)` under different declarations, `x/x` definedness,
unevaluated integrals, unknown assumptions, separate reference policy and a decomposition-only
consumer that performs no hidden symbolic calculation. They identify consequential contracts;
this review does not authorize implementation or an extensive testing campaign.

### Architectural and plan implications

The recommendation strengthens explicit source/meaning/assessment relations (A2) and reusable
native operations with local ownership (A1/A3). A4 favors removing unrequested calculation and
duplicate preparation while keeping memory/storage proportional. Scope-bound reasoning is
favorable; implementation correctness, source/meaning mappings and benefit remain unqualified.

The existing [interpretation plan](../plans/production-efficiency/interpretation-and-scientific-analysis.md)
and [ADR-0035](../adr/0035-model-governed-analysis.md) already anticipate demand-driven
preparation and qualified frontends. A complete persisted decomposition, changed M09/M11
coverage, new native statistical meanings, changed identity/equality or altered historical
publication would require explicit adopted scope and updates to D1/D4/D5/D7 and the governing
decision where its meaning changes. New derived result definitions belong to the LinkML release
and its generated persistence/validation/analytical projections, not independent hand-maintained
tables or rule registries. No new standing alignment lint, audit gate or evidence machinery is
recommended. Existing F01 disposition remains with its owning plan; this review supplies options
and does not close it or revise any audit premise.
