# Interpretation, mathematical preparation and scientific analysis

**Status:** Implemented with scoped verification; PE-02 decision bounded; F01 remains open · **Created:**2026-10-30.
[Coordinator](../production-efficiency_2026-10-30.md) owns status/disposition. This plan owns
PE-02–PE-04 and review F01–F03. Shared semantics belong to [PE-01](analysis-model-and-contracts.md#PE-01).

## Target and current route

`grammar.py` currently combines Earley recognition, explicit ambiguous trees, recursive resolution,
SymPy collapse and occurrences. `spans.read_spans` always requests `any_value` with constants-only
context. Rule projections similarly parse before reading available bindings; scientific readers
use more context. M09/M11 independently acquire reading inputs; M13 consumes persisted math
observations. Preserve current parser/memo strengths and truthful distinctions while replacing
these cross-consumer decisions with one model-derived interpretation contract.

The target has cheap prepared context, contextual recognition, relative syntax/occurrence products,
interpreted alternatives and lazily requested mathematical values. These are logical capabilities,
not a mandatory serial task chain or five persisted artifacts. Stronger consumer demands require
stronger admitted results. Existing semantic outcome labels cannot simply be reused for a weaker
stage that skipped their defining computation.

<a id="PE-02"></a>
## PE-02 — Settle recognition and ambiguity execution

**Owner:** mathematical interpreter/model integration. **Inputs:** PE-01 agreed demand/context
contracts and PE-00 RC01 decision route; full implementation of PE-01 is not needed for a bounded
algorithm investigation. **Supplies:** selected recognizer/ambiguity design and precise consumer
semantics before PE-03 migration.

Reproduce recognition versus resolution/transform cost through production entry points on normal,
long, ambiguous and context-sensitive source expressions. Existing observations are not an SLA:
one195-span page took6.40s cold/0.00153s warm; instrumentation changed a deadline-sensitive outcome.
Do not attribute the historical172s corpus check to symbolic comparison or derive improvement
percentages by comparing profiled and unprofiled runs.

Compare (1) restructuring the admitted grammar and typed starts, with early sound context pruning;
(2) packed ambiguity with Lark1.3.1 `ambiguity='forest'`, `ForestVisitor(single_visit=True)` and a
suitable forest transformer; (3) qualified LALR/contextual subsets beneath the same interpretation
contract. A structural `pylatexenc` frontend is eligible if it removes real work, not another
mandatory pass. Its `LatexWalker`/`LatexContextDb`/`MacroSpec` own nested syntax and coordinates,
not mathematical truth. Resolve2.10 versus3beta APIs before selecting it.

A forest removes expansion, not Earley chart work. Existing transformers depend on tree inlining
and cannot attach unchanged to the SPPF. Mutable resolver notes/counters are not pure memoizable
transforms. Deterministic parse success is insufficient to prove the general grammar had no other
valid reading. Admit a fast subset only through model-defined grammar/context conditions, with
explicit unsupported/ambiguous handling. No greedy priority may silently decide meaning.

**Decision gate:** record the selected design, preserved/changed outcome contract, supported input
scope, relevant measurements, dependencies and rejected alternatives. If no replacement is qualified,
retain the authoritative general recognizer inside the new prepared contract and state the
remaining recognition limitation/revisit evidence. That does not close F01 merely by adding a cache.
Dependent consumer migration cannot assume an undecided algorithm or changed OK/AMBIGUOUS meaning.

Sources: [Lark forest APIs](https://github.com/lark-parser/lark/blob/1.3.1/docs/forest.rst),
[parser alternatives](https://github.com/lark-parser/lark/blob/1.3.1/docs/parsers.md),
[pylatexenc2.10](https://pylatexenc.readthedocs.io/en/v2.10/latexwalker/), and local
[Lark](../../libraries/parsing/lark.md)/[pylatexenc](../../libraries/parsing/pylatexenc.md) capability orientation.

<a id="PE-03"></a>
## PE-03 — Migrate mathematical consumers to prepared interpretation

**Owner:** production math methods, rule views and scientific operand readers. **Inputs:** working
PE-01 products and PE-02 selected contract. **Supplies:** real shared execution, not declaration-only
model types.

Construct effective macro/context preparation once per valid scope and derive complete stage keys
once. Route source reading, M09/M11, rule projections and scientific readers through the same context
adapter, preserving legitimate differences in available information. Carry requested kind from
admitted model declarations where justified; do not infer it from a generic source "definition"
label. Apply available bindings before expensive interpretation. Early lexical/binder work may
supply declarations only under its modeled authority, without circular dependence on M13.

Share compatible M09/M11 physical preparation/results while retaining separate method observations,
outcomes and provenance. Retire duplicate `_readings`/macro-context translations. Keep the existing
bounded memo where valid; use one operation-local prepared operand/value holder for repeated
`to_sympy` use. Do not persist all trees, keep a second competing cache or collapse occurrences
because the mathematical value is shared. A new grammar/transformer/profile/context invalidates
only products whose declared dependencies change; conditions/policy additionally bind decisions.

**Completion:** all named production consumers adopt the contract; same text in distinct binding
contexts remains distinct; relative positions map correctly to each source occurrence; unresolved,
partial and timeout meanings survive; unsupported demands refuse explicitly. Independent examples
must expose function-versus-variable ambiguity, macro changes, set/formula distinctions, source
scope and repeated evidence. Current `grammar.parse` compatibility helpers are retired or narrowed
to one explicit adapter rather than remain alternate interpretation authority.

<a id="PE-04"></a>
## PE-04 — Prepare scientific comparisons and specialize justified work

**Owner:** scientific evidence/comparison policies. **Inputs:** PE-01 policy/precision dependencies,
PE-03 prepared operands; local duplicate base-evaluation removal can proceed under the current
scientific contract without waiting for a new recognizer. **Supplies:** model-bound scientific
comparison used by consolidation and independent reference evaluation.

Use structural equality first, then transformations applicable to the declared expression domain,
then necessary general symbolic fallback. SymPy1.14 targeted `cancel`, `factor`, `collect` or other
selected operators require conditions showing why they preserve the relevant meaning; do not chain
every available simplifier. Reuse converted operands and identical base/point evaluations within
one comparison. Comparison-side preparation also feeds PE-07 matching rather than being rebuilt
inside every invariant candidate pair.

For genuinely repeated numerical work, qualify `lambdify(..., modules='numpy')`, optional `cse`
and batched points against compilation cost. A twelve-point comparison may be cheaper with direct
evaluation. Restrict generated functions to the admitted expression/function vocabulary; preserve
singularities, finiteness, exact values, deterministic seeds, conditions and separate decision
profiles. Numerical agreement does not become symbolic proof. Reuse cannot survive changed
conditions or policy just because operand text matches.

**Completion:** duplicate operand/base work is removed; old independent scientific distinctions
remain or change only under a declared new profile; both current consumers migrate and repeated
private transformation paths retire. Measure scientific comparison separately from source reading.
If vectorized compilation does not earn its preparation, retain direct evaluation with prepared
operands and document that evidence rather than leave an unused execution branch.

Sources: [SymPy best practices](https://docs.sympy.org/latest/explanation/best-practices.html),
[lambdify](https://docs.sympy.org/latest/modules/utilities/lambdify.html),
[numeric computation](https://docs.sympy.org/latest/modules/numeric-computation.html),
[local capability orientation](../../libraries/parsing/Sympy.md). Check consequential APIs against the
pinned installation through Context7 and primary/installed sources; newer docs are not pin evidence.

## Execution —2026-10-30

**Implemented; scoped verification.** Current delivery follows PE-01, source38f79f5
(operator documentation62565b2 preserved). The coordinator owns package/finding disposition.

### PE-02 decision and limit

Retain general Earley/dynamic recognition. Resolver changes reuse role/value summaries, prune
proven-invalid branches only when a definitely admissible branch exists, and retain unchanged
subtrees. Prepared input lazily converts mathematical values. The bounded200input comparison
preserved status, kind, failure category and occurrence positions. It established no recognizer
speedup or ordinary-workload no-regression claim: recognition dominates, forest tree projection
was small, and the complete grammar failed strict LALR construction. The narrow integer/add/subtract
subset covered none of that sample; this does not rule out useful broader subsets. F01 remains
open for a qualified subset or direct forest interpretation justified by broader source applicability.
No unqualified forest/LALR/pylatexenc production path was added.

Evidence: [interpretation investigation](../../design_review/evidence/2026-10-30_interpretation-scientific-analysis/README.md).

### PE-03 shared execution

Frozen `PreparedMathInput` retains exact text, kind, context and deadline policy; private caches
retain stable values/unrepresentability and exclude transient timeout. Source readers, rule views,
scientific operands and references use that preparation boundary. M09/M11 demand interpreted status
because their observations and coverage require it. Compatible adjacent logical methods physically
share one rendition batch through the source loop, while separate claims, configuration hashes,
completions, observations and provenance remain. Different configuration/deadline inputs stay apart;
batch ownership refuses cross-reader reuse and binds rendition identity/digest. M13 remains downstream.

Analysis profile2 carries actual grammar/transformer recipes, explicit implementation-source/library
determinants, supported sharing and scientific computation profiles. Acquisition supplies these bytes;
pure compilation never reads installed implementation defaults. Invariant context components are
prepared once. Compiler6/current profile2 admission and retained compiler5 reading remain distinct.

### PE-04 scientific execution

Operation-local operands canonicalize/convert once, retain individual contexts, and check binding
compatibility before canonical shortcuts. Conditions are interpreted once, retaining completeness.
Set differences and common base/point evaluations are reused. Each equation orientation meets its
own valid-point threshold. Polynomial-only cancellation precedes bounded simplification without
removing undefined denominator points. Consolidation/reference sampling and decisions stay distinct;
reference numerical agreement remains undecided. Symbolic conversion timeouts remain transient.

Scientific ABI3/profile2 recipes derive from the same explicitly supplied model as runtime settings.
A candidate threshold change reaches recipe and execution; mismatched artifacts refuse. The numerical
investigation selected direct evaluation for current small comparisons. Generated NumPy/CSE results
were bounded probes, without complete domain qualification or a production speed claim.
Evidence: [numeric investigation](../../design_review/evidence/2026-10-30_scientific-computation/README.md).

### Acceptance and deployment

Compiler6 and forward0036 use existing fixed relations. New native products follow final source-byte
acquisition; historical migrations, operational databases, archives and stored grades remain unchanged.
Root receipts: `build/pe234/`; model/native receipts: `build/pe-model/`.
The broader integrated selection failed two source-key cases because a float deadline entered the
strict canonical serializer; using the canonical string fixed both cases and the direct sharing
regression. The failed original and corrected selection remain separately recorded. Grammar/preparation,
scientific/alignment, source grouping, explicit candidate recipe variation and retained-read controls
have focused passing evidence. The existing78page corpus/key oracle and generated properties passed.
Native/source/domain integration remains scoped; no full-series/provider qualification follows.
Initial source setup failed while0036 assets were not yet frozen; that failed attempt is retained.

PE-02's bounded selection is complete; the larger F01 recognition opportunity remains open.
PE-03/PE-04 structural mechanisms are implemented. F03 retains PE-07 consumer/benefit obligations.
No audits or testing-architecture changes were performed. Lint-only edits preserve applicable
functional/type results. PE-12 owns assembled qualification.
