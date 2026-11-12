# Shared constructions and packed primary interpretation

**Implemented; bounded functional scope Tested on 2026-11-11 source. TC-05 reopened by the
2026-11-12 completion audit: downstream recognizers are not all retired
([TC-E09](../text-characterization_2026-11-10.md#TC-E09), [TC-E11](../text-characterization_2026-11-10.md#TC-E11))
and the coverage meaning of unparsed input is undecided ([TC-E13](../text-characterization_2026-11-10.md#TC-E13)).
TC-06 has no gap.** TC-05 and TC-06 deliver shared
constructions and packed/contextual interpretation; TC-10/11 retain independent assessment and
full-book qualification.
The [series coordinator](../text-characterization_2026-11-10.md) owns selected scope, opportunity
disposition and assembled completion. [Model and retention](model-and-retention.md) owns the
combined enriched-document contract, immutable source base plus identified selected annotation-layer
revisions, coordinates, identities, generated representations and persistence/read custody. This
supporting plan specifies how native evidence becomes reusable primary characterizations within
that contract. It does not create another schema, workflow engine or mutable annotation authority.

The functional target comes from selected
[O02](../../functional_reviews/text-characterization_2026-11-10.md#O02),
[O03](../../functional_reviews/text-characterization_2026-11-10.md#O03), and relevant
[O01/O04/O05/O06/O07](../../functional_reviews/text-characterization_2026-11-10.md#O01).
The complete [seven discovery topics](../../library_leverage/libraries/text-characterization/briefing.md#topic-briefings-and-feature-index)
provide native capability context; the integrated review supplies selection. The target includes
sentence meanings and contextual linguistic dependencies. Later concept identity, scientific
assessment and domain relationships remain consumers of those meanings.

## Authoring baseline and target responsibility · 2026-11-10

Planning source baseline is main `59eee893c`, inspected on 2026-11-10; the integrated review's
earlier source baseline remains attributed to that review. Directly inspected annotation, named-rule,
frame, HanLP and mathematical source paths were unchanged through the working HEAD at authoring.
Concurrent CLI/reporting documentation is excluded. This is source-grounded planning, without new
inference, tests, probes, fitting or performance results.

The existing [named matcher owner](../../../python/corpus-structure/src/corpus_structure/methods/annotation_rules.py)
prepares native `Matcher`, `PhraseMatcher`, `DependencyMatcher` and unfiltered `SpanRuler`, retaining
named roles, actual nodes and dependency identities. This is a useful construction substrate.
[Predicate frames](../../../python/corpus-structure/src/corpus_structure/methods/predicate_frames.py),
[their declaration](../../../python/corpus-structure/src/corpus_structure/semantic/constructions/retained_rules.json),
[procedure roles](../../../python/corpus-structure/src/corpus_structure/methods/structural_roles.py),
[qualifier recipes](../../../python/corpus-structure/src/corpus_structure/semantic/constructions/retained_rules.py)
and [HanLP products](../../../python/corpus-structure/src/corpus_structure/methods/pm2_hanlp_products.py)
then authored overlapping predicate, role, coordination, operator and host policies. The delivered
replacement places the predicate-frame, procedure-role and qualifier-recipe interpretations under
the shared primary construction and interpretation owner. The HanLP products' own interpretation
still runs beside it (TC-E09). Useful native matching and independently expected semantic cases survive.

The [source contribution SQL](../../../python/corpus-structure/src/corpus_structure/semantic/sql/source_contributions.sql)
at that baseline authenticated annotation origin and reconstructed expected role/reading support.
Its exact source and producer authentication survives. Semantic producer policy now belongs
to the executable shared authority; downstream admission consumes typed retained premises and
enforces its owned invariants. Merely calling the producer again in admission or expected test output cannot establish
semantic correctness. The implemented consumer migration preserves source-witness protection while retiring duplicated
interpretation.

The governing architecture remains [D1](../../design/D1-knowledge-representation.md),
[D2](../../design/D2-schema-and-guidelines.md), [D4](../../design/D4-method-catalog.md),
[D5](../../design/D5-consolidation-identity-confidence.md),
[D6](../../design/D6-orchestration-metrics-policies.md) and
[D8](../../design/D8-agent-and-query-interfaces.md). ADR-0081 and the updated owners establish
primary-characterization authority and the implemented producer/consumer contracts.
Nothing here treats a linguistic proposal as an admitted scientific assertion.

**Delivered focused foundation judgment; bounded functional scope Tested, 2026-11-11.**
FP-04/CI-01–04 require occurrences, attributed analyses,
construction instances, roles/attachments, operators, choices and coverage to govern behavior rather
than decorate flat frame payloads. FP-03/06 favor native matchers/grammars plus ordinary typed
functions, with authored linguistic meaning localized by family. FP-07 and H4/H10/H12/H15/H17 favor
prepared resources, retained evidence, direct packed computation and environment-aware reuse.
One universal grammar over every English sentence is not the baseline; model evidence and partial
construction coverage remain useful where an authored grammar does not match. A new modal rule
should improve multiple consumers without another syntax run or private downstream recognizer.

## Contracts and dependencies

TC-05 consumes [TC-03 native linguistic evidence](native-evidence.md#TC-03),
[TC-04's early positioned formal atom/constituent slice](native-evidence.md#TC-04), and TC-02
retained source/layer readers. TC-04's later ambiguous-formal integration consumes the working
TC-06 packed semantics; TC-05 does not wait for that later slice. TC-06
consumes TC-05 construction matches and grammar derivations plus the selected contextual evidence
layers produced by the contextual package. These are input capabilities, not a barrier requiring
all possible evidence families to finish before independent work starts. A lexical-only construction
can run without a dependency parse; a native syntax construction declares its actual requirements.
Unavailable required premises produce unavailable/incomplete family coverage, not an invented match.

Designing grammar resources and handlers can start once TC-01 settles the needed typed meanings,
source mapping and choice contract. Native integration requires functioning TC-02 retained readers
and the needed TC-03/04 output slices. TC-05 and TC-06 should be developed together on an initial
coherent construction family: recognizing syntax without carrying its meaning into retained products
is not useful completion. Other construction families can follow independently against that contract.

Every layer refers to the same immutable document base, preserving source hierarchy, physical pages,
tables, figures, captions, prose and math/reference occurrences. Analysis windows can include
neighboring clauses or blocks without replacing the document with a concatenated text authority.
Discontinuous/cross-boundary members keep their own source occurrence IDs and share a typed group
ID. Native token memberships and source membership remain explicit even when a convenient Span or
bounding interval is also available. TC-01 owns exact field spelling, invariants and identity;
this plan owns the construction and interpretation behavior consuming them.

<a id="TC-05"></a>

## TC-05 · Shared declarative construction recognition

**Implemented; bounded functional scope Tested, 2026-11-11.** Recognizes reusable lexical,
syntactic and recursive constructions across the selected source population, retaining all supported proposals and their declaration identities
before domain mapping. This realizes O02 and produces the construction premises of O03/O04.

### Native pattern composition and authored meaning

Use spaCy **3.8.18** with the retained selected **en_core_web_sm 3.8.0** analysis.
`PhraseMatcher(attr=...)` handles terminology, idioms, aliases and discourse cues. Build lexical
patterns with tokenization only when matching lexical attributes; `LEMMA`/`POS` patterns require
those attributes on the pattern Docs. `Matcher` handles token sequences, morphology membership,
repetition and declared approximate variants, using `with_alignments=True` where repeated pattern
positions carry roles. `DependencyMatcher` uses named `RIGHT_ID` nodes and `REL_OP` structural
relations to retain directed argument/complement/attachment configurations.
[PhraseMatcher](https://spacy.io/api/phrasematcher) · [Matcher](https://spacy.io/api/matcher) ·
[DependencyMatcher operators](https://spacy.io/api/dependencymatcher#operators).

A construction declaration binds its language family/revision, applicability prerequisites, pattern
or grammar identity, role bindings, expansion/membership policy and semantic handler. These are
ordinary authored linguistic resources/modules under the semantic release, not an unbounded rules
language. Technical vocabulary supplies domain terms and mappings; book names, page numbers and
specific benchmark strings never choose linguistic behavior. The application supplies predicate
sense proposals, semantic roles, implicit-role statuses, attachment conditions and supported
inference from model syntax. Native subject/object labels alone do not decide actor/patient.

Preserve named match roles and actual tokens, including discontinuous dependency subtrees.
`Token.subtree`, `conjuncts`, noun chunks and direct children are useful native query operations;
`left_edge/right_edge` is an enclosing interval and cannot replace exact members. Use native
traversal rather than constructing a second graph solely to repeat these queries. A shared ancestor
or token distance does not establish attachment; dense LCA matrices are unnecessary for a small
set of paths. `Matcher`'s `!` is sequence negation, and greedy `FIRST`/`LONGEST` is match selection;
neither is linguistic negation/scope. Approximate `REGEX`/`FUZZY` evidence keeps source spelling,
limits and mechanism separate from canonical identity. [Token structure](https://spacy.io/api/token) ·
[rule capability distinctions](../../library_leverage/libraries/text-characterization/extraction-classification-and-normalization.md).

Use `SpanRuler(spans_filter=None, annotate_ents=False, spans_key=...)` to collect overlapping raw
proposals into a writer-owned group. Reconciliation/classification writes another layer/group and
never overwrites the only rival evidence. `SpanGroup.attrs` can carry working metadata; the
retained model carries declaration IDs, roles, source maps and choices that bare spans do not.
`Doc.ents` remains an optional non-overlapping projection and is not the construction store.
[SpanRuler](https://spacy.io/api/spanruler) · [SpanGroup](https://spacy.io/api/spangroup).

### Recursive source grammar and protected atoms

Select Lark **1.3.1** for recursive constructions using composable grammar resources:
`%import` namespaces, templates, aliases, `%declare`, `%extend` and `%override`, multiple starts
and shared top-level whitespace policy. Imported `%ignore` rules are not inherited. For conventional
tree families, `merge_transformers()` composes namespaced handlers and reports collisions. Direct
forest handlers use the same explicit grammar/rule namespace mapping, without assuming ordinary
Transformer composition dispatches packed nodes automatically.
[1.3.1 grammar reference](https://github.com/lark-parser/lark/blob/1.3.1/docs/grammar.md) ·
[handler composition](https://github.com/lark-parser/lark/blob/1.3.1/lark/visitors.py).

Prose construction grammars consume original positioned source regions with
`parser="earley", lexer="dynamic", ambiguity="forest", priority=None, ordered_sets=True`.
This preserves relevant lexical/grammatical derivations rather than presenting one spaCy token
classification as an exhaustive lexer lattice. Native syntax, candidate matches and formal atoms
are attributed premises for admissibility/semantic handlers; they do not silently erase alternative
raw-source readings. Candidate scopes include complete clauses/sentences and structurally related
neighbors, including sources that never yielded a final definition/procedure record. No-match
retains native evidence and explicit construction coverage.
[Lark parser choices](https://lark-parser.readthedocs.io/en/stable/parsers.html) ·
[1.3.1 frontend constraints](https://github.com/lark-parser/lark/blob/1.3.1/lark/parser_frontends.py).

Protected math/reference occurrences require both lexical constraints and a semantic guard. Build
source-region-specific atom terminals that consume each selected occurrence whole, keyed back to
its source identity. General prose terminals must not consume a partial protected interval or
cross its boundary; use explicit terminal constraints derived from the region's atom boundaries,
not a postlex pass or an annotation field assumed to constrain raw Earley matching. Prevent `%ignore`
from swallowing protected content. Before emitting semantics, check each derivation's terminal
membership against the retained atom map and reject incompatible splits/crossings. This backstop
cannot substitute for lexical constraints: accepting only invalid atom splits and rejecting all of
them would miss an otherwise valid atom-preserving reading. Repeated equal atoms remain distinct
by position/occurrence, even when a terminal pattern can share spelling. Formal interiors attach
only through TC-04's separately positioned products.

The implementation must qualify this constrained-terminal composition on the selected Lark version
before widening the grammar population. If a grammar family cannot preserve an atom whole, emit
unsupported/incomplete coverage for that family and retain other native/construction results;
do not rewrite source bytes to placeholders and silently claim original coordinates. A positioned
reversible input projection is possible only as an explicitly revised contract, not an implicit
fallback for the selected raw-source route.

`dynamic_complete` is conditional on a named boundary-ambiguity family where shorter regex matches
change a supported interpretation. Avoid broad catch-all regex terminals that amplify ambiguous
boundaries. Dynamic Earley does not support `TextSlice` or postlex; use an exact region plus an
explicit region-to-source map. `TextSlice` remains useful for TC-04 basic/contextual parsers.
Custom typed lexers and `InteractiveParser.feed_token` are restricted to deterministic selected
input projections, with explicit positions; neither supplies the general prose ambiguity bridge.
[1.3.1 lexer/source handling](https://github.com/lark-parser/lark/blob/1.3.1/lark/lexer.py) ·
[custom-lexer example](https://github.com/lark-parser/lark/blob/1.3.1/examples/advanced/custom_lexer.py).

### Construction population and execution route

The baseline inventory spans the following families; each needs explicit semantics and meaningful
positive, rival and unsupported cases. Development order follows shared dependencies rather than
one task per row.

| Family | Required behavior supplied to primary interpretation |
| --- | --- |
| Verbal, copular, adjectival and nominal predication | Predication kind, located predicate/focus, overt roles and unresolved/implicit roles; grammatical function separate from semantic role |
| Complements, relatives and modification | Governing/embedded predication, complement versus modifier, relative gap and candidate attachment with premises |
| Voice/tense/aspect/mood | Overt auxiliaries/morphology and normalized proposals, retaining source support and native disagreement |
| Coordination and ellipsis | Conjunct/group identity, connective, local/inherited roles, inheritance witnesses and unresolved gaps; collective/distributive options |
| Negation, modality and quantification | Cue/target, operator kind, restrictor/body/binder sites, nested scope and compatible alternatives |
| Conditional, temporal, causal, concessive, comparative and exception forms | Located clause/operand roles and operator links, separating source wording from scientific causality/validity |
| Reporting and quotation | Reporter/source mention, content/stance, quote boundaries and nested attribution; reported content distinct from author assertion |
| Naming/definition, question, instruction and passage function | Located overlapping function proposals and their linguistic witnesses without domain record selection |

Reuse prepared matchers by rule revision, compatible Vocab and required annotation resources;
reuse prepared parsers by effective grammar, lexer/settings and applicable atom constraints.
A region-specific atom terminal specialization can differ per region while stable grammar resources
and semantic handlers remain shared. Do not rebuild every matcher/model per construction instance,
prepare every possible native head for lexical-only demand, or parse the entire 518-page book as
one Earley input. Work over semantically coherent source regions, retaining neighbor/context scope
and explicit uncovered relations where a window cannot cover them. Repeated overlapping windows
must not independently re-establish identical evidence votes; identity and reuse use actual inputs.

Recognition, matching and detachment occur outside publication locks. Region-level work can share
one operation and transaction with other compatible families. A malformed declaration is an authoring
failure; a missing required annotation is unavailable; valid grammar no-match is recognized coverage
with no construction; an incompatible atom derivation is rejected with cause. Record parser limits,
timeout and truncated region coverage, preserving native evidence and other completed families.
Do not convert these outcomes to sentence-wide negative semantic labels.

### Integration and acceptance

Replace scattered rule preparation and private predicate/procedure/HanLP cue recognition as their
consumers move to the shared layer. Domain consumers read construction IDs/roles and TC-06 meaning
rather than importing grammar resources or relabeling native dependencies. Keep original native
observations and independent source-witness controls. TC-05 delivers retained readable construction
products, declaration introspection and coverage alongside its recognizers; a parser-only library
helper is not package completion.

Functional acceptance requirements (closure evidence is in the coordinator):

- One reusable passive/coordination construction supports both definition and procedure consumers
  with explicit sharing evidence; an unlicensed conjunct does not inherit every neighboring role.
  A second vocabulary exercises the same declaration without page/book dispatch.
- A relative gap, nominal/copular predication and a nonprojective/discontinuous role retain actual
  members. Repeated equal tokens and a cross-block group retain separate occurrence IDs.
- Nested/overlapping pattern matches survive raw collection and retained reads. Missing dependency
  columns disable only dependent families; lexical work remains available. Rule identity and aligned
  role bindings survive repetitions and approximate-match evidence.
- Raw-source Earley recognizes a grammatical alternative that a single typed token classification
  would suppress. Protected atom terminals admit the valid whole-atom reading; semantic guards reject
  partial/crossing derivations. Include repeated atoms, punctuation touching an atom and an ignored-token
  hazard, with independent expected original positions.
- No-match, rejected derivation, missing evidence, parser failure and incomplete region coverage remain
  distinguishable. Useful evidence exists on source scopes that yield no complete domain record.

Use targeted functional/source-mapping checks during implementation; native quality qualification
belongs to the integrated population. Grammar-generated strings can exercise syntax but are not
independent natural-language semantic gold. The coordinator owns broad final qualification.

<a id="TC-06"></a>

## TC-06 · Packed symbolic terms and primary contextual interpretation

**Implemented; bounded functional scope Tested, 2026-11-11.** Turns shared construction/native
evidence into typed, factorized primary meanings with correlated alternatives, then evaluate linguistic context without destroying the
retained symbolic reading. This is a primary semantic responsibility, not a downstream record
adapter or a bottom-up forest callback pretending to own inherited state.

### Phase one: context-independent packed symbolic construction

Use Lark **1.3.1** `ForestTransformer` with `transform_token_node`, `transform_packed_node`,
`transform_intermediate_node` and `transform_symbol_node` for direct SPPF reduction. A token becomes
a source-bound symbolic leaf. A packed production composes its child references conjunctively;
a completed symbol retains alternatives across compatible derivations. Intermediate LR(0) nodes
represent partial productions, not linguistic constituents: flatten their structural sequence only
as warranted by the rule, preserving the child references and derivation identity needed for meaning.
The application defines this algebra and its typed terms; Lark supplies bottom-up traversal and
native packed structure, not roles, binders, correlation, semantic equivalence or durable identity.
[Forest API](https://lark-parser.readthedocs.io/en/stable/forest.html) ·
[1.3.1 forest implementation](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py).

A symbolic term references shared children, the construction/rule revision, native/formal premises,
source members and explicit binder/attachment/operator sites. It does not enumerate complete trees
or copy all child structures into every alternative. Hash-consing/equivalence may share an identical
pure term only when the full meaning-bearing identity and support distinction permit it; equal
text/endpoints alone do not merge independent occurrences or evidence relations. Generated model
constraints own valid role/choice references and acyclicity, with operation-scoped DAG construction
under the existing publication contract.

Coordinate handling follows TC-01: dynamic-lexer forest chart extents are character offsets in the
selected region; token-stream chart indices use an explicit token-to-character map. Packed and
intermediate extents derive from actual children; epsilon constituents carry an insertion boundary
and synthetic/nonliteral status. Native forest object IDs are transient handles mapped to retained
IDs, never durable identities. No ordinary `Meta` propagation is assumed for forest transformation.
Ignored text remains in the base and coverage; missing a callback for meaningful grammar structure
produces preserved uninterpreted syntax and incomplete interpretation, not silent `Discard`.

The low-level transformer is selected because the primary result must retain packing and control
shared semantic references. `TreeForestTransformer(resolve_ambiguity=False)` with
`@handles_ambiguity` remains available only for a deliberately bounded tree-shaped output whose
intermediate expansion is understood. Its conversion can expand alternatives and omit cyclic
families; adding an ambiguity handler does not guarantee compact output. `CollapseAmbiguities`,
`ambiguity="resolve"` and complete-tree enumeration are consumer-specific bounded projections,
never the only primary record. [Tree conversion behavior](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py).

Reuse for pure shared-node work must be explicit. `ForestVisitor(single_visit=True)` visits a
non-token node once, but does not by itself arrange that a transformed result reaches every parent
in the low-level transformer. Implement result reuse within the transformation only where the
selected native traversal/adapter correctly propagates completed immutable terms to each use;
qualify a shared-child case. `TreeForestTransformer(use_cache=True)` is a separate native mechanism
with pure-callback assumptions and bounded tree conversion costs. Neither mechanism keys inherited
context. Avoid hidden mutable environments and do not build another general forest traversal
framework when the native callbacks plus a small operation-local reference map suffice.

Reject non-consuming recursive cycles from the supported construction set during grammar authoring.
If an unexpected cycle is encountered, use `on_cycle`/`get_cycle_in_path` diagnostics and mark that
interpretation family incomplete, preserving independently valid source/native/construction results.
A grammar cycle must not become a cyclic retained semantic DAG or silently disappear during tree
conversion. Fixed-point semantics and infinite semantic inventories are not selected requirements.
This is a grammar/content boundary, not a new repository-wide design lint.

### Phase two: contextual linguistic evaluation

Consume retained symbolic terms plus an explicit selected context: source hierarchy/list/quotation
boundaries, earlier linguistic bindings/attachments and the contextual package's attributed
Maverick mention/cluster, Dipo discourse and selected GLiNER/d1 proposal layers. Context selection
and operation ordering follow declared evidence dependencies. TC-07 owns contextual evidence and
source-local hypotheses, while TC-06 is the sole semantic-node/environment evaluator. TC-08's
candidate questions freeze candidates from phase-one symbols and TC-07 hypotheses, without waiting
for this final evaluation. Execute phase one, contextual/model evidence and then phase two; no
automatic refinement loop or semantic answer feeds its own input. Unresolved final results stay
unknown or require a separately versioned explicit demand. Local symbolic terms can be retained
and inspected before contextual families finish; contextual failure does not erase them. The
contextual package owns provider calls and source-first questions. TC-06 owns the composition and
evaluation of those premises into primary linguistic meaning; it does not invoke an unselected
provider as a fallback.

For a conventional unambiguous tree, Lark `Interpreter.visit()`/`visit_children()` supplies explicit
contextual traversal. For a retained packed DAG, ordinary typed evaluator functions consume symbolic
nodes and explicit immutable environments. Reuse keys include the semantic node and every relevant
inherited environment determinant, including selected context layer revisions and compatible choice
premises. One node evaluated under two binder/attribution environments may produce two different
supported contextual results; node-only memoization is invalid. Lark's bottom-up ForestTransformer
and `single_visit` do not implement this evaluator. Preserve partial bindings/scope order when
context does not choose a unique supported answer.
[Interpreter contract](https://github.com/lark-parser/lark/blob/1.3.1/lark/visitors.py).

The output expresses the meanings below under TC-01's typed DAG/choice contract:

| Meaning | Primary interpretation obligation |
| --- | --- |
| Predication/participants | Predicate sense proposal, explicit grammatical versus semantic role, located overt/implicit/unresolved member, complement/modifier links and premise references |
| Voice/tense/aspect/mood | Normalized proposals tied to native cues, with passive correspondence and rival analysis retained |
| Coordination/ellipsis | Connective/group/conjunct identity, local versus inherited argument, inheritance witness, collective/distributive options and unresolved gap |
| Negation/modality | Nested operator nodes, cue and target, force/type proposals and possible scope; never a sentence-wide Boolean substituted for structure |
| Quantification | Binder, bound occurrence, restrictor/body, cardinality/range and supported relative-scope partial order or alternatives |
| Clause relations | Antecedent/consequent, temporal/comparative/exception and causal/concessive roles, attributed source basis and no inference of scientific truth from a connective |
| Attribution/embedding | Reporter/source, embedded content, stance and scope; source report distinct from author assertion |
| Function/reference | Located overlapping assertion/question/instruction/definition/assumption/example labels, mention occurrences, referential hypotheses and explicit contextual dependencies |

A source semantic disjunction, such as the text saying “A or B,” is an operator inside a reading.
An analytical choice between two possible attachments/readings is uncertainty about the analysis.
A choice group declares exclusive, coexisting or unresolved compatibility and references its
required premises/other choices. A supported reading consists of a root plus its dependent choices.
Do not manufacture a Cartesian product of independently valid role, referent and scope labels.
Jointly required choices travel together; unresolved compatibility stays unresolved. A scope partial
order need not enumerate every total ordering. Ranking is a separately attributed preference and
never turns model scores/grammar priorities into truth or discards unselected primary evidence.

A condition, exception or modal construction describes source meaning; evaluation here does not
execute the condition, test scientific validity, discard a branch because the current world makes
it false, or establish a cross-work concept identity. Linguistic declaration/binding and later
scientific symbol resolution have separate contracts and dependencies. Later admitted conceptual
answers cannot feed back as premises for the original linguistic reading.

### Retention, resource bounds and consumer cutover

Publish immutable symbolic/contextual annotation-layer revisions through TC-02. Queryable units,
roles, operators, choices and coverage use existing generated model/database custody. Larger syntax
and derivation payloads use existing typed report/artifact placement, with explicit retained
references that ordinary readers can follow. Native forest structures can be released once the
needed meaning and reconstructible derivation references are retained. Parser save/cache, Python
pickle, `Doc.to_json()` and the old Tree codec are not substitutes for a qualified semantic codec.
[Retention limits](../../library_leverage/libraries/text-characterization/execution-retention-and-tools.md).

Reconstruction need not recreate a native Python forest merely to answer a typed semantic query.
Hydrate selected DAG neighborhoods and their closed premise references, keeping shared nodes shared.
A display limit constrains rendered results; it must not narrow examined context or imply that
omitted choices were unsupported. Derivation inspection is bounded intentionally without requiring
all readings to expand at once. Stage resources by coherent source scope; release native forest,
Docs and tensors after their last consumer rather than accumulating all 518 pages' live views.

A new construction revision invalidates affected symbolic/contextual products while unchanged native
evidence is reusable. A changed selected context layer invalidates contextual evaluation that used
it, leaving compatible context-independent terms reusable. Existing operation custody owns durable
reuse; the node/environment memo is ephemeral inside one evaluation, not another store or job
engine. Cancellations and limits preserve terminal outcome and partial family coverage through the
existing operation owner. No per-term transaction, lease or durable evaluator checkpoint is added.

Integrate retained readers and selected consumer journeys with interpretation production. Definition
consumers use characterized predication/naming/function/conditions; procedure consumers use actions,
participants/operators/instruction function; comparison/link consumers use operands, mention and
scope structures. A missing reusable language distinction is an extension here rather than a hidden
consumer regex. The consumer package owns final downstream migration, native admission and replay
cutover. TC-06 supplies its typed meanings and authenticatable evidence; completion cannot be claimed
while the only usable route still reconstructs old private frames.

**Open, 2026-11-12 audit (TC-E11, TC-E13).** Two definition-side consumers still hold private
recognition. Assertion qualification consumes primary frames and then re-scans raw tokens for
negation, the modal tag and a dependency gate. Definition declaration recognizes "let … be",
copular, relative-clause and passive naming patterns from raw HanLP dependency columns beside the
primary naming construction; whether that chain is domain-owned interpretation or a missing
reusable distinction is an open decision. Separately, packed recognition reports `empty` for input
the grammar cannot parse or tokenize. "Valid grammar no-match is recognized coverage" above does
not settle whether out-of-grammar input is recognized-empty or unsupported; TC-11's family account
needs that decided.

### Meaningful acceptance and qualification

Functional checks use independent expected structures and exact source members. Examples below are
authored cases, not claimed textbook quotations or qualified model predictions.

- “Not every trial succeeds” retains distinct negation and quantifier nodes with cue/binder/body
  links and supported scope, rather than one negative flag. A nested modal/reporting case retains
  the source of the modality and reported content separately from author assertion.
- An ambiguous attachment has two supported packed derivations with shared child references.
  A required attachment/scope pairing survives ordinary retained read; unsupported cross-products
  are absent. A literal “A or B” remains a semantic disjunction within a reading rather than an
  analysis-choice group masquerading as source wording.
- One symbolic node used under two inherited binder/attribution environments produces appropriate
  separate contextual results. Reversing visitation order does not leak one environment into the
  other. A pure shared child still reaches every parent after native transformation/result reuse.
- A relative gap, epsilon constituent and discontinuous/cross-block role retain synthetic status,
  insertion boundary, per-member source occurrence IDs and shared group identity. No enclosing quote
  falsely claims intervening source as support.
- An unsupported rule callback, cyclic grammar family, atom-incompatible derivation, contextual
  provider failure and interrupted evaluation retain distinct incomplete/failed outcomes without
  erasing valid native evidence or context-independent terms. Unresolved meaning is not empty truth.
- Roundtrip tests check DAG sharing, derivation/premise closure, operators, choice dependencies and
  selected revision fidelity through database/report retention and ordinary inspection. Independent
  invalid inputs exercise dangling choices, foreign layer/source pins and inconsistent membership.
- A construction-only change reuses native inference, and a context-only change reuses symbolic
  terms while changing affected contextual identity. Updated definition/procedure consumers observe
  the new shared meaning without new private interpretation code.

Focused checks establish local correctness during implementation; actual native/contextual provider
runs establish their scoped behavior, not synthetic prediction quality. The assembled qualification
covers all 518 physical Grinstead–Snell pages with explicit scope/family outcomes and source-first
omission assessment, plus a second-vocabulary transfer fixture. No package pass or bounded example
claims universal English coverage. Expected reuse and reduced duplicate interpretation are qualitative
benefits, not numerical speed/quality claims or a mandatory benchmark campaign.

## Material implementation questions and completion boundary

The main architecture choices are settled for planning: attributed native evidence, constrained
raw-source Earley prose, deterministic typed lexer use only, direct packed symbolic construction,
then primary contextual evaluation with environment-aware reuse. The following questions guided
implementation; their delivered baseline and remaining corpus assessment boundary are recorded below:

| Question | Settling work and dependent scope |
| --- | --- |
| Can the composed prose terminals enforce whole protected atoms while admitting the valid surrounding prose alternatives? | Delivered positioned protected-atom controls cover the selected raw-source grammar. A new family must preserve this contract; no hidden placeholder fallback is selected. |
| How do generated typed term constructors express the initial packed semantic algebra and shared references? | Delivered typed DAG/choice contracts, direct packed reduction and independent correlated-choice controls supply the shared representation. |
| Which inherited bindings actually affect each contextual handler? | Delivered contextual evaluation keys reuse by semantic node and relevant environment, with shared-node/different-environment controls and explicit unknown outcomes. |
| Which full-book constructions exceed normal native or grammar region envelopes? | TC-10/11 retain full-book population assessment. Delivered operations retain explicit unsupported/partial family outcomes; limits cannot silently remove pages from the proving population. |

These are implementation evidence/contract questions, not unselected baseline alternatives or a new
standing audit. A consequential changed answer updates the coordinator's target and the semantic
owner through the normal decision route before consumers depend on it.

Authoring evidence on 2026-11-10 was source/reference inspection only; product/provider tests were
**not_run** at that date. The coordinator’s 2026-11-11 account records delivered retained products,
consumer integration, packed diamond/cycle and contextual-choice controls in the applicable
functional union. Independent semantic assessment, fitting, benchmarks and full-book adoption
are not established by those results.
