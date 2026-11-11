# Sentence structure and interpretation

**Proposed discovery judgments, 2026-11-10.** The target is primary characterization of all
useful sentence readings: predicates, arguments, grammatical and semantic scope, voice,
polarity, modality, quantification, attribution, discourse function and alternatives. This
is an open design inquiry, not an incremental extension of existing predicate recipes.
Baseline `e283a63c09c8881698a51495c9dbe48f757b44f3` plus pending discovery revisions was
examined; this topic account replaces their treatment. Selected and locally sourced versions
are spaCy **3.8.18**, `en_core_web_sm` **3.8.0**, and Lark **1.3.1**. Claims below are source-based;
no new sentence-accuracy or model-performance result is asserted. [Family scope](briefing.md).

**Recommended direction:** combine spaCy's linguistic structure and structural queries with
Lark's composable grammars and semantic-processing interfaces. Keep interpretation proposals
as structured, source-grounded products whose roles, scope and alternatives remain inspectable.
A complete target can replace the present finite recipes; it need not preserve their boundaries
or assume every sentence has one meaning. Neither a dependency tree nor an application-defined
frame class supplies complete meaning predictions automatically.

## What is available now, and what it establishes

The [richer annotation producer](../../../../python/corpus-structure/src/corpus_structure/ingest/annotations.py)
retains lemmas, POS, tags, morphology, dependency heads/labels and sentences over source-bound
tokens. [Native views](../../../../python/corpus-structure/src/corpus_structure/ingest/annotation_views.py)
restore those columns without rerunning a model.
[Named rules](../../../../python/corpus-structure/src/corpus_structure/methods/annotation_rules.py)
use token, phrase and dependency matchers with explicit role bindings and expansion.
[Predicate frames](../../../../python/corpus-structure/src/corpus_structure/methods/predicate_frames.py),
their [declaration](../../../../python/corpus-structure/src/corpus_structure/semantic/constructions/retained_rules.json)
and [qualifier recipes](../../../../python/corpus-structure/src/corpus_structure/semantic/constructions/retained_rules.py)
derive bounded readings and cues. These are authored interpretations of model syntax, not a
spaCy semantic-role, discourse or logical-form model. They demonstrate composition, not the
complete supported language of a future primary characterization.

The [knowledge representation owner](../../../design/D1-knowledge-representation.md) already
distinguishes candidates, composed interpretation and accepted claims. Discovery may propose a
richer upstream representation without making each linguistic proposal an admitted knowledge
edge. [Representation and composition](representations-and-composition.md) assesses that boundary.

## Native syntax and structural queries

| Feature/API | Contribution and judgment | Prerequisites and residual authoring |
| --- | --- | --- |
| `DependencyParser`: `Token.head`, `Token.dep`, sentence breaks | **Recommended:** a shared labeled syntax foundation for predicates, subjects, objects, complements, modifiers and embedded clauses. [API](https://spacy.io/api/dependencyparser). | Requires language/domain-appropriate weights. Dependency labels describe syntax, not universal semantic roles; nominal predicates and parser errors need explicit treatment. A predicted tree represents one analysis, not all possible parses. |
| `Token.children`, `lefts`, `rights`, `n_lefts/n_rights`, `head` | **Recommended:** inspect local arguments/modifiers directly, avoiding a duplicate graph solely to recover relationships already present. [Token API](https://spacy.io/api/token). | Map model-specific label schemes to authored role proposals; preserve omitted/implicit roles as unknown. Left/right describes token position, not semantic direction. |
| `Token.ancestors`, `is_ancestor()`, `subtree`, `left_edge/right_edge`; `Span.root` | **Recommended:** clause containment, governing predicates and phrase expansion using native structure. [Token](https://spacy.io/api/token), [Span](https://spacy.io/api/span). | Descendant membership is not semantic scope. In nonprojective parses, enclosing left/right extents can include nonmembers; retain actual token membership when needed. |
| `Token.conjuncts`, `Span.conjuncts` | **Recommended:** expose coordinated predicates and participants, including alternatives. [Token](https://spacy.io/api/token), [Span](https://spacy.io/api/span). | Shared arguments, distributive/collective readings, ellipsis and negation scope remain authored or learned interpretation. Coordination does not license blindly copying every role. |
| `Doc.noun_chunks`, `Span.noun_chunks`, language syntax iterators | **Supporting:** base nominal constituents around candidate argument heads. [Noun chunks](https://spacy.io/usage/linguistic-features#noun-chunks). | Language support and dependencies are required. Base chunks are not arbitrary noun phrases, complete arguments or a constituency tree; prepositional complements and embedded modifiers need further analysis. |
| `Doc.get_lca_matrix()`, `Span.get_lca_matrix()` | **Supporting:** structural connection/proximity for selected argument or clause pairs. [Doc](https://spacy.io/api/doc#get_lca_matrix), [Span](https://spacy.io/api/span#get_lca_matrix). | Matrix construction is dense and quadratic in token count. Prefer direct traversal for a few paths; a shared ancestor is not evidence of a semantic relation. |
| `DependencyMatcher.add()`: `RIGHT_ID`, `RIGHT_ATTRS`, `LEFT_ID`, `REL_OP`; `validate=True`, callbacks | **Recommended:** declarative named-node constructions combining token attributes with dependency/order constraints. [API](https://spacy.io/api/dependencymatcher). | The anchor precedes references to it; named matches return token-index tuples in pattern order. Role assignment, expansion, alternatives and meaning remain authored. Validation checks pattern form, not linguistic truth. |
| `Matcher` token predicates and `PhraseMatcher(attr=...)` | **Recommended:** lexical cues and construction pieces complementary to graph queries. [Matcher](https://spacy.io/api/matcher), [PhraseMatcher](https://spacy.io/api/phrasematcher). | `ORTH`/`LOWER`/`NORM`/`LEMMA`, POS/tag/DEP, morphology and extensions require their corresponding annotations. Token `REGEX`, `FUZZY`/`FUZZY1`…`9`, membership, numeric comparisons and morphological set predicates are **Supporting** for variation, not semantic equivalence. Sequence quantifiers `!`, `?`, `+`, `*`, `{n}`, `{n,m}`, `{n,}`, `{,m}` and greedy `FIRST`/`LONGEST` select matches, not scope interpretations. |
| Contextual `AttributeRuler`; parser `learn_tokens=True` | **Supporting** for contextual corrections; **Promising-unresolved** for experimental learned merging when segmentation impairs syntax. [AttributeRuler](https://spacy.io/api/attributeruler), [parser option](https://spacy.io/api/dependencyparser). | Both can change the premises of downstream interpretation. They do not create parallel semantic readings; detailed boundary choices are in [segmentation](segmentation-and-lexical-analysis.md). |

Every `DependencyMatcher` structural family below is available in the selected release. Meanings
are relative to `A` in `A operator B`; immediate ordering means adjacent token indices, while
sibling relations additionally require a shared head. The [official operator table](https://spacy.io/api/dependencymatcher#operators)
and installed 3.8.18 `spacy/matcher/dependencymatcher.pyx` operator dispatch establish
these distinctions. Installed `spacy/tokens/token.pyx` supplies the traversal observations.
These are local source observations: the attempted upstream `v3.8.18` tag URL returned
HTTP 404 on 2026-11-10, so it is not used as a release-source citation.

| Operators | Expressed relationship | Judgment and useful distinction |
| --- | --- | --- |
| `>` / `<` | A heads B / A depends on B directly | **Recommended:** local predicate/argument and modifier constructions. |
| `>>` / `<<` | A is ancestor / descendant of B along dependency edges | **Recommended:** embedded clause and governing-context queries; do not substitute token distance for tree distance. |
| `.` / `;` | A immediately precedes / follows B in the same dependency tree | **Supporting:** adjacent cues with an explicit syntax boundary. |
| `.*` / `;*` | A precedes / follows B anywhere in the same dependency tree | **Supporting:** ordered construction members with intervening material; broad patterns can return many combinations. |
| `$+` / `$-` | B is A's immediately adjacent right / left sibling | **Supporting:** ordered same-head constituents when adjacency is meaningful. |
| `$++` / `$--` | B is any right / left sibling of A | **Recommended:** coordinated or parallel dependent constructions without enumerating all intervening words. |
| `>+` / `>-` | B is A's child immediately to its right / left | **Supporting:** combine direct dependency and adjacency in one constraint. |
| `>++` / `>--` | B is A's child anywhere to its right / left | **Recommended:** direction-sensitive argument/modifier constructions. |
| `<+` / `<-` | B is A's parent immediately to its right / left | **Supporting:** reverse anchored forms of the adjacent head relation. |
| `<++` / `<--` | B is A's parent anywhere to its right / left | **Recommended:** reverse anchored forms of directional head queries. |

## Formalizing constructions and their interpretation

Lark can express a syntax for whole controlled sentences, recurring clause constructions,
linguistically typed token sequences, or the declarative recipe language itself. These are
different useful targets. A grammar over recipe declarations formalizes how interpretations
are authored; a grammar over sentence units recognizes those constructions. Neither supplies a
ready-made broad English grammar or semantic lexicon. Existing
[field grammars](../../../../python/corpus-structure/src/corpus_structure/semantic/structural_parsing.py)
and [mathematical grammar composition](../../../../python/corpus-structure/src/corpus_structure/methods/math/grammar.py)
are local examples, not a ceiling on Lark's prose contribution.

| Feature/API | Contribution and judgment | Prerequisites and residual authoring |
| --- | --- | --- |
| Recursive rules, alternatives, grouping, EBNF `?`/`*`/`+`, exact/ranged `~`; `[item]` placeholders | **Recommended:** explicit clause nesting, coordinated arguments, optional auxiliaries, negation and qualified constructions; a recipe grammar can expose these same distinctions rather than bury them in procedural branches. [Grammar](https://lark-parser.readthedocs.io/en/stable/grammar.html), [1.3.1 grammar compiler](https://github.com/lark-parser/lark/blob/1.3.1/lark/load_grammar.py). | Grammar and lexicon are authored. `[item]` with `maybe_placeholders=True` retains absent positions; `item?` does not. Large repetition ranges expand grammar work. CFG recognition alone does not resolve agreement, reference identity or semantic admissibility. |
| Templates `name{parameter,...}` | **Recommended:** reusable separated arguments, paired delimiters and clause/qualifier forms, including a common construction instantiated for different predicate classes. [Templates](https://lark-parser.readthedocs.io/en/stable/grammar.html#templates). | Compile-time syntax reuse, not runtime semantic polymorphism. Template parameters and callbacks must preserve the intended roles. |
| `%import`, symbol aliases/namespaces, `import_paths`, `source_path`, `open_from_package()` | **Recommended:** independently maintained clause, nominal, logical and technical-notation fragments with a shared sentence grammar. [Import](https://lark-parser.readthedocs.io/en/stable/grammar.html#import), [package loading](https://lark-parser.readthedocs.io/en/stable/classes.html#lark.Lark.open_from_package). | Imported dependencies are namespaced; `%ignore` is not inherited. Package resolution and explicit exported symbols remain the composition contract. |
| `%declare`, `%extend`, `%override` | **Recommended:** define typed-token interfaces, add domain constructions, or replace a generic production without copying the whole grammar. [Directives](https://lark-parser.readthedocs.io/en/stable/grammar.html#declare). | Extension/replacement affects every use of that production. A controlled fragment extension is not evidence of full natural-language coverage. Distinguish enrichment from silently overriding a base interpretation. |
| `start=[...]`, `parse(start=...)`; rule priorities and aliases `-> alias` | **Recommended:** one prepared grammar exposes sentence, clause, argument and recipe entry points; aliases produce distinct meaning-oriented construction names. [Lark options](https://lark-parser.readthedocs.io/en/stable/classes.html#lark.Lark), [rules](https://lark-parser.readthedocs.io/en/stable/grammar.html#rules). | Entry-point selection and priorities are authored policy. Priorities rank derivations; they are not probabilities or meaning confidence. |
| LALR/contextual; Earley/dynamic; CYK; `strict=True` | **Recommended:** LALR for deterministic construction/recipe languages; Earley where retaining grammatical alternatives is essential. **Not advantageous:** CYK as the default sentence engine, given Lark's stronger Earley forest and LALR interactive support. [Parsers](https://lark-parser.readthedocs.io/en/stable/parsers.html). | Default parser is Earley; default Earley ambiguity resolution selects a tree. Strict collision checks are **Supporting** while authoring deterministic grammars, not a required new repository gate. Lexical ambiguity and postlex restrictions are covered in [segmentation](segmentation-and-lexical-analysis.md). |
| `_rule`, `?rule`, `!rule`, named/hidden terminals, `keep_all_tokens`, `maybe_placeholders`; custom `tree_class` | **Recommended:** make generated structure directly reflect roles, optional slots and construction variants, removing routine tree reshaping. [Tree construction](https://lark-parser.readthedocs.io/en/stable/tree_construction.html). | Filtering can remove semantically useful punctuation; `?rule` inlines only single-child results after filtering. Custom tree classes are **Supporting** when their ownership contract is useful; an application frame still needs explicit semantics. |
| `Transformer`, `v_args(inline/meta/tree/wrapper)`, `Discard`, `visit_tokens`, defaults, transformer chaining; `merge_transformers()` | **Recommended:** reduce construction nodes to explicit predicate/argument/scope proposals and compose namespaced semantics with grammar fragments. [Visitors](https://lark-parser.readthedocs.io/en/stable/visitors.html), [composition example](https://lark-parser.readthedocs.io/en/stable/examples/composition/main.html), [1.3.1 visitors](https://github.com/lark-parser/lark/blob/1.3.1/lark/visitors.py). | Callbacks implement interpretation. Bottom-up replacement and default copying differ from annotation-only visitation. Chaining is **Supporting**, useful only for distinct semantic passes rather than repeated generic normalization. |
| `Transformer_NonRecursive`, in-place variants; `Visitor` / recursive variant and top-down traversal | **Supporting:** choose deep-tree safety, structural replacement or annotation according to the operation instead of writing a custom walker. [1.3.1 traversal implementations](https://github.com/lark-parser/lark/blob/1.3.1/lark/visitors.py). | In-place mutation and shared nodes need deliberate ownership; nonrecursive traversal does not fix ambiguous meaning. |
| `Interpreter.visit()` / `visit_children()` | **Recommended:** explicit contextual scope traversal for nested modality, attribution, quantifiers or conditions, where parent context matters. [Interpreter](https://lark-parser.readthedocs.io/en/stable/visitors.html#interpreter). | Lark controls dispatch/traversal infrastructure; the application authors scope rules and state. Preserve a reading before evaluating it: interpreting a source sentence need not execute its condition or discard an unevaluated branch. |
| `ast_utils.Ast`, `AsList`, `WithMeta`, `create_transformer(decorator_factory=...)` | **Recommended:** typed meaning-frame/recipe objects with list roles and source metadata, avoiding repetitive constructor dispatch. [AST example](https://lark-parser.readthedocs.io/en/stable/examples/advanced/create_ast.html), [1.3.1 implementation](https://github.com/lark-parser/lark/blob/1.3.1/lark/ast_utils.py). | Constructor order, aliases and placeholders remain authored contracts. Generated methods can overwrite same-named methods; a decorator factory is **Supporting** for a concrete common callback concern, not an invitation to add an assurance framework. |
| Parse-time `transformer=...` versus postparse transformation; `VisitError.orig_exc` | **Supporting:** fuse deterministic LALR recognition/reduction when the intermediate syntax is not needed; preserve grammar versus callback failure distinctions. [Lark 1.3.1 options](https://github.com/lark-parser/lark/blob/1.3.1/lark/lark.py), [visitors](https://lark-parser.readthedocs.io/en/stable/visitors.html). | Internal transformation excludes Earley and limits metadata callbacks/Discard. **Not advantageous** when inspectable full syntax or alternatives are required. Failure records must not turn semantic callback errors into an apparent no-match. |
| `Tree.find_data/find_pred/scan_values/find_token`, bottom-up/top-down iteration; Python structural patterns | **Supporting:** query recognized constructions and dispatch concise local shapes. [Tree API](https://lark-parser.readthedocs.io/en/stable/classes.html#tree), [1.3.1 source](https://github.com/lark-parser/lark/blob/1.3.1/lark/tree.py). | There is no `Tree.match()` in 1.3.1; use Python class patterns. Bottom-up iteration avoids revisiting shared subtrees; top-down source uses preorder stack traversal and can revisit shared nodes, despite a breadth-first docstring. |
| `expand_kids_by_data()`, `Tree.copy()`, deep-copy/pickle | **Supporting** for intentional reshaping; **Not advantageous** as presumed provenance-preserving cloning. [1.3.1 Tree](https://github.com/lark-parser/lark/blob/1.3.1/lark/tree.py), [Token](https://github.com/lark-parser/lark/blob/1.3.1/lark/lexer.py). | Flattening mutates direct children without recomputing metadata; shallow copy shares children and drops root metadata. Deep-copy shares tree metadata; token deep-copy/pickle omits end coordinates. Preserve required positions explicitly. |

## Sentence readings worth exposing

The following are positive discovery directions irrespective of whether a current consumer or
training set exists. Each row distinguishes a native mechanism from the interpretation still
to be supplied. A useful result can retain partial readings and exact unresolved attachments;
it need not flatten them to one label or require a complete universal logical form first.

| Characterization | Mechanism and value judgment | Boundary, residual work and next discriminating question |
| --- | --- | --- |
| Predicate inventory and arguments | **Recommended:** spaCy dependency queries plus lemma/POS/morphology identify verbal, copular, adjectival and nominal predicate candidates; named dependency patterns and Lark construction aliases expose subject/object/complement and modifier slots. [Parser](https://spacy.io/api/dependencyparser), [DependencyMatcher](https://spacy.io/api/dependencymatcher), [grammar shaping](https://lark-parser.readthedocs.io/en/stable/tree_construction.html). | Semantic roles, implicit actors, control/raising, relative gaps and nominalizations require authored mappings or learned extensions. Next: which reusable constructions expose these without assuming syntactic subject always means actor? |
| Voice, tense, aspect, mood and grammatical agreement | **Recommended:** dependencies, auxiliaries and `Token.morph` retain active/passive/copular distinctions and available inflection; grammar alternatives can normalize equivalent argument placements. [Morphology](https://spacy.io/usage/linguistic-features#morphology), [MorphAnalysis](https://spacy.io/api/morphanalysis). | Model feature inventories vary; passive morphology alone does not identify the agent. Preserve overt structure while proposing normalized roles. Next: which voice alternations should share a semantic frame, and which grammatical distinctions remain meaningful? |
| Polarity and negation scope | **Recommended:** `DEP="neg"`, negative determiners/adverbs, lexical cues and nested constructions expose negation operators and their possible hosts. [Matcher](https://spacy.io/api/matcher), [Interpreter](https://lark-parser.readthedocs.io/en/stable/visitors.html#interpreter). | Neither library natively predicts semantic negation scope. Quantifier interaction, coordination, negative raising and lexical negation remain interpretation work. Next: retain `not(all(...))` versus `all(not(...))` as alternatives rather than a sentence-wide negative flag. |
| Modality and evidential status | **Recommended:** auxiliary/tag/morphological cues, modal predicates and Lark scope nodes locate possibility, necessity, permission, obligation and reported evidence. [Token](https://spacy.io/api/token), [grammar](https://lark-parser.readthedocs.io/en/stable/grammar.html). | `may` and `must` do not select epistemic/deontic readings by themselves. Contextual disambiguation is **Promising-unresolved** through authored constructions, classification or a custom predictor. Next: which modal type and target distinctions materially change the retained reading? |
| Quantification, cardinality and distribution | **Recommended:** determiner/number/modifier dependencies plus grammar nodes expose quantifier, restrictor, body, numerical bounds and collective/distributive alternatives. [Dependency matching](https://spacy.io/usage/rule-based-matching#dependencymatcher), [Transformer](https://lark-parser.readthedocs.io/en/stable/visitors.html#transformer). | Universal/existential force, proportional meanings, exceptions and relative quantifier scope are authored/learned semantics. Lark supports representing bindings but supplies no binding model. Next: which quantifiers require explicit variable/role identity rather than a free-text cue? |
| Conditional, temporal, causal, concessive, comparative and exception structure | **Recommended:** clause dependencies plus markers identify related predicates; recursive Lark productions expose antecedent/consequent, ordering, comparison operands and exceptions as distinct roles. [DependencyParser](https://spacy.io/api/dependencyparser), [grammar composition](https://lark-parser.readthedocs.io/en/stable/examples/composition/main.html). | Syntax does not prove causality or convert “unless” to a valid logical rewrite in every context. Relative scope and discourse relations need authored rules or models. Next: what construction inventory covers ordinary readings without forcing causal, temporal and conditional relations into one qualifier kind? |
| Attribution, quotation and propositional embedding | **Recommended:** reporting predicates, clausal complements, quote boundaries and source phrases expose speaker/source, reported content, nesting and stance. [DependencyMatcher](https://spacy.io/api/dependencymatcher), [Token quote attributes](https://spacy.io/api/token). | A quote flag is not a quotation parser; speaker identity, report negation, indirect speech and cross-sentence attribution remain work. Next: retain nested attribution separately from the truth/polarity of its embedded proposition. |
| Sentence function and discourse contribution | **Recommended:** retain interpretable cues for assertion, question, instruction, definition, naming, assumption, example, explanation, hypothesis, contrast and description; combine grammar constructions with source layout/context. [TextCategorizer](https://spacy.io/api/textcategorizer), [SpanCategorizer](https://spacy.io/api/spancategorizer). | Native classifiers learn supplied labels; the selected English parser does not emit this function inventory. Multilabel spans or a custom model are **Promising-unresolved** for overlapping functions. Next: which distinctions require paragraph/document context, rather than treating headings or one lexical trigger as decisive? |
| Reference and shared participants | **Recommended:** preserve mention occurrences and syntactic role identity; **Promising-unresolved:** coreference/semantic-role extensions for pronouns, ellipsis and cross-sentence arguments. [Custom components](https://spacy.io/usage/processing-pipelines#custom-components), [coreference API](https://spacy.io/api/coref). | Coreference is an additional, compatibility-sensitive predictor, not ordinary dependency parsing. General semantic-role predictions need an external or custom trained component and an explicit role vocabulary. Next: which references can remain located unresolved candidates while richer interpretation is retained? See [models](models-supervision-and-evaluation.md). |
| Competing readings and incomplete interpretation | **Recommended:** preserve alternative attachments, argument bindings, scope orders and function proposals; Earley `explicit`/`forest` retains grammatical alternatives, while span groups retain overlapping located labels. [Earley forest](https://lark-parser.readthedocs.io/en/stable/forest.html), [SpanGroup](https://spacy.io/api/spangroup). | A spaCy Doc has one native dependency tree; span overlap is not a correlated full reading. Lark enumerates only the authored grammar's alternatives, not every natural-language meaning. Next: which alternatives need shared identity and mutual exclusion? [Alternative interpretations](ambiguity-and-alternative-interpretations.md) owns the detailed mechanisms. |

## Judgment and research priorities

The highest-value investigation is a unified, explicit sentence interpretation model with
construction recognition delegated to native matchers/grammars and semantic decisions kept in
named recipes or predictors. Grammar formalization is **Recommended** for recurring syntax and
recipe declarations. Broad grammar-led primary characterization over enriched and alternative
linguistic units is **Promising-unresolved** and merits direct comparison with a hybrid of statistical
syntax, deterministic constructions and learned semantic/discourse extensions. Neither route is
settled by the current implementation. Compare the sentence readings each preserves, lexical and
construction coverage, and the authored grammar/model investment. A single complete hand-authored
English CFG is not a prerequisite for investigating grammar-led realization; needing authored
semantics is not a reason to reject it. Learned extensions are likewise **Promising-unresolved**,
not rejected because their models or datasets are not yet selected.

FP-02/03/04 favor explicit domain meaning, scoped authority and composable interpretation.
FP-05 and H15 favor retaining useful partial structure and alternatives instead of reducing them
to an opaque function label. H4/H12 favor native traversal, prepared patterns and grammar-semantic
composition over parallel bespoke parsers. H6/H10 argue for scoped construction analysis and
compact alternatives, not a narrower functional target. No benchmark is needed to recognize
these structural advantages; efficacy and throughput remain unmeasured.

Three questions change the design: what sentence-level meaning distinctions should be first-class;
which constructions have clear deterministic versus learned realization; and how should correlated
alternatives and unresolved roles survive in the retained product? Those are proposed assessment
questions, not new implementation commitments. Representation, learned extraction/classification,
and model qualification continue in [composition](representations-and-composition.md),
[extraction](extraction-classification-and-normalization.md) and
[models](models-supervision-and-evaluation.md).

| Guide-section coverage | Disposition location |
| --- | --- |
| [spaCy](../../../libraries/parsing/spacy.md) base §§3.2–3.3, 4.1–4.4; addendum §§4.1, 5.1–5.3 | Native syntax/traversal, all 20 DependencyMatcher operators, sequence/phrase query options and contextual annotation; segmentation topic deepens morphology/learned merging. |
| [Lark](../../../libraries/parsing/lark.md) base §§2.1–2.3, 3.1–3.5, 6.1–6.3, 7.1–7.7, 12.2–12.4; addendum §§1.1–1.3, 4.1–4.5, 6.1 | Engine choices, grammar expressiveness/composition, output shaping, semantic processing, ASTs, traversal/ownership and interpretation limits above. Priority/ordering and detailed forest processing continue in the alternatives topic; provenance continues in composition. |
| Adjacent value assessed here; detailed family owner elsewhere | spaCy classifications, coreference/custom prediction and span alternatives receive explicit sentence-value judgments above; extraction/models/alternatives topics assess their concrete configuration and release constraints. |

Functional/model tests and performance experiments: **not_run**; source/reference discovery only.
