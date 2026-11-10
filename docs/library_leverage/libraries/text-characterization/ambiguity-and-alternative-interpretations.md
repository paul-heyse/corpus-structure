# Ambiguity and alternative interpretations

**Discovery, 2026-11-10; all recommendations and expected benefits Proposed.** Baseline
`e283a63c09c8881698a51495c9dbe48f757b44f3`; pending discovery revisions were source notes,
not accepted conclusions. The target is maximal supported primary characterization of whole
sentences, including predicate arguments, attachments, coordination, polarity, modality,
quantification, attribution and scope. Later conceptual relations consume those characterizations.
The [shared briefing](briefing.md) owns the selection and broader scope. These judgments draw on
the relevant [Lark guide and addendum](../../../libraries/parsing/lark.md) and
[spaCy guide and addendum](../../../libraries/parsing/spacy.md), plus inspected installed
Lark 1.3.1 and spaCy 3.8.18 sources. No behavioral probe or efficacy test was run.

## Lark representations of alternatives

| Feature | Contribution and judgment |
| --- | --- |
| Earley `ambiguity="forest"` | **Promising—unresolved, primary foundation candidate.** Returns a shared packed parse forest (SPPF), preserving alternative derivations and common structure before selecting an interpretation. This can support full-sentence structural and semantic alternatives, beyond mathematical parsing. A useful realization needs an authored linguistic/formal grammar, semantic representation and source mapping; grammar completeness and semantic coverage remain open. The lack of a failing current consumer is no reason to defer this representational value. [Parser configuration](https://github.com/lark-parser/lark/blob/1.3.1/lark/lark.py), [forest API](https://github.com/lark-parser/lark/blob/1.3.1/docs/forest.rst). |
| Earley `ambiguity="explicit"` | **Recommended for bounded alternative families.** Ordinary trees with `_ambig` children fit positioned AST processing and make alternatives inspectable. Tree conversion can enlarge shared derivations and removes cyclic derivation families, so it is not the universal form for maximal ambiguity. The current [math grammar](../../../../python/corpus-structure/src/corpus_structure/methods/math/grammar.py) selects this mode and retains unresolved readings rather than silently guessing. [Earley conversion](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley.py), [conversion implementation](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| Earley `ambiguity="resolve"` | **Supporting for an explicitly selected reading; not advantageous as the sole primary record.** Chooses one derivation using priorities and native tie policy; unselected alternatives are discarded. It is useful for qualified unambiguous sublanguages or a declared interpretation policy, but a deterministic result does not establish a uniquely correct sentence interpretation. Preserve alternatives independently when their loss would weaken the target. [Configuration and defaults](https://github.com/lark-parser/lark/blob/1.3.1/lark/lark.py), [selection](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| `SymbolNode`, including intermediate LR(0) nodes | **Recommended constituent mechanism within the forest candidate.** A symbol and input extent identify a shared constituent; multiple packed children expose its derivations. Intermediate nodes represent partial productions, not authored linguistic units, and need hiding or interpretation in domain output. Native identities are operation-local, not durable annotation identities. [Node definitions](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| `PackedNode` and its rule/left/right children | **Recommended constituent mechanism within the forest candidate.** Preserves which child structures belong to a particular production. This supports correlated alternatives: a scope or attachment choice can remain tied to the predicate/argument interpretation that produced it. Reducing the output to independent label sets would lose this information. The application still defines semantic compatibility beyond the grammar and stable references to derived readings. [Packed derivations](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |

An SPPF compactly represents derivations admitted by the supplied grammar. It does not discover
every linguistically defensible interpretation without such a grammar, and syntactic sharing
does not automatically factor arbitrary semantic constraints. Preserve whole-derivation
dependencies when combining local alternatives; a Cartesian product of independently collected
predicate, referent and scope candidates can invent readings that no derivation supports.
These are design implications of the [native packed structure](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py),
not a claim that Lark supplies a complete natural-language semantic formalism.

## Direct computation over a forest

| Feature | Contribution and judgment |
| --- | --- |
| `ForestVisitor` callbacks for symbol/intermediate/packed/token nodes, entry/exit scheduling | **Recommended traversal substrate.** Allows inspection, constituent annotation and bottom-up analysis without first enumerating sentence trees. Returned children control descent. Semantic labels, cross-constituent checks and the meaning of the analysis remain authored. [Visitor contract](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| `ForestVisitor(single_visit=True)` | **Supporting for context-independent shared-node work.** Avoids repeated visits to non-token nodes. It is unsuitable when the same constituent must be evaluated under different inherited bindings or scope environments unless those environments are part of the application's computation identity. It does not turn arbitrary callbacks into correct dynamic programming. [Traversal implementation](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| `ForestTransformer.transform_symbol_node`, `transform_intermediate_node`, `transform_packed_node`, `transform_token_node` | **Promising—unresolved, primary semantic-computation candidate.** Bottom-up callbacks can return domain objects directly from forest structure, potentially producing packed predicate/argument/scope interpretations while retaining alternative identity. This can replace bespoke forest traversal and premature tree enumeration. The application must define the result algebra: conjunction within a derivation, alternatives across derivations, equivalence, binding context, correlation and source identity. Native traversal supplies none of those semantics automatically. [Transformer contract and implementation](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| `TreeForestTransformer`, rule/alias dispatch and token callbacks | **Promising—unresolved, higher-level realization of the same foundation.** Familiar rule handlers can construct typed interpretations directly from the SPPF. It removes low-level dispatch work but does not reproduce ordinary inlining, token filtering or position propagation. Choose it when its intermediate-node expansion and callback interface preserve the intended packed semantic output; use `ForestTransformer` when direct packed-node control matters. [Tagged class and limitations](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py), [official example](https://github.com/lark-parser/lark/blob/1.3.1/examples/advanced/tree_forest_transformer.py). |
| `@handles_ambiguity` | **Recommended within a `TreeForestTransformer` realization.** A rule-level handler receives the transformed derivations together, enabling explicit alternative objects, semantic equivalence grouping or supported filtering. Set `resolve_ambiguity=False` to retain alternatives before this processing. Handlers must preserve justification and correlations rather than merge readings merely because their surface labels match. [Decorator and dispatch](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| `__default__`, `__default_token__`, `__default_ambig__` | **Supporting extension points.** They permit a consistent domain-node, token and alternative representation across uncustomized rules. Defaults should preserve unknown productions rather than silently treat them as interpreted. Grammar-specific meaning still needs explicit handlers. [Default methods](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| `use_cache=True` | **Supporting after semantic callback design.** Reuses packed transformations within a transformation, useful when alternatives share structure. `TreeForestTransformer` defaults to `False`; cached callbacks must be pure and referentially transparent. Mutable result objects or scope-sensitive hidden state can make reuse wrong. This is a realization detail of the foundation, not a prerequisite for investigating it or an established application speedup. [Cache contract and lifecycle](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| `on_cycle()` / `get_cycle_in_path()` | **Recommended explicit boundary.** Traversal detects cycles and backtracks; the callback can identify grammar recursion corresponding to infinite ambiguity. That does not solve recursive semantics. The target must decide whether to reject such a grammar family, retain a cyclic semantic form, or define a terminating fixed-point interpretation. [Cycle-aware traversal](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| Internal `ForestToParseTree` | **Supporting contract knowledge; not the preferred independent extension interface.** It powers `resolve`/`explicit`, uses rule callbacks and optional packed-result caching, and discards cyclic derivation families during finite tree construction. Conversion is therefore potentially lossy. Prefer the documented forest interfaces unless this lower-level behavior is specifically required. [Implementation](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| `CollapseAmbiguities` | **Supporting for deliberately small enumeration; not advantageous as the general primary representation.** Expands `_ambig` combinations into complete trees and can produce exponentially many results. Useful for inspecting a bounded set of readings, but defeats factorized representation when used indiscriminately. [Expansion implementation](https://github.com/lark-parser/lark/blob/1.3.1/lark/visitors.py). |

Source extents require deliberate treatment. For dynamic lexers, `SymbolNode.start/end` are
character positions; token-stream/basic-lexer chart positions require a token-to-character map.
Token coordinates and the original source remain available, but `TreeForestTransformer` does
not build ordinary `Meta` extents. Empty constituents, ignored material and intermediate nodes
need an explicit extent policy. The present [tree helpers](../../../../python/corpus-structure/src/corpus_structure/methods/math/_tree.py)
and [math tree codec](../../../../python/corpus-structure/src/corpus_structure/methods/math/native.py)
assume `Tree`/`Token` output and would need coherent replacement if the forest becomes primary.
See [native forest coordinates](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py),
[Earley chart construction](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley.py)
and [representations and composition](representations-and-composition.md).

## Ranking, retention and inspection

| Feature | Contribution and judgment |
| --- | --- |
| Declared rule priorities with `priority="normal"` | **Supporting native structural preference.** Expresses an explicit derivation preference without a custom scorer. It is not a probability, semantic truth or permission to discard unsupported alternatives in primary characterization. [Priority compilation](https://github.com/lark-parser/lark/blob/1.3.1/lark/lark.py). |
| `priority="invert"` | **Supporting policy comparison.** Negates rule and terminal priorities, allowing alternative preference policies over one grammar. Because lexical precedence also changes, it is not a clean reversal of sentence-semantic ranking; record the changed recognition conditions. [Implementation](https://github.com/lark-parser/lark/blob/1.3.1/lark/lark.py). |
| `priority=None` | **Recommended option when no priority policy is justified.** Removes rule priorities and zeroes terminal priorities; avoids priority-induced preference, but lexical matching and parser policies still constrain the admitted family. It does not mean all natural-language interpretations have been represented. [Implementation](https://github.com/lark-parser/lark/blob/1.3.1/lark/lark.py). |
| `ForestSumVisitor` | **Supporting native algebra, implementation-level contract.** Adds completed-rule and child priorities within packed derivations and takes the maximum across symbol alternatives. Use this existing additive ranking when suitable; a custom semantic algebra is needed for constraints, nonadditive evidence, probabilities or context-dependent scope decisions. [Priority propagation](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| `prioritizer=` with a custom `ForestVisitor` | **Promising for explicit interpretation preferences.** Separates ranking from grammar recognition and transformation. A domain-specific prioritizer can use structural evidence; its features, calibration and permitted filtering remain authored. Preserve the family before ranking when alternative retention matters. [Official prioritizer example](https://github.com/lark-parser/lark/blob/1.3.1/examples/advanced/prioritizer.py). |
| `ordered_sets=True` / `StableSymbolNode` | **Recommended reproducibility support.** Stable state and family order makes tied results inspectable and repeatable; it does not establish semantic preference. Native packed sorting also considers emptiness, priority and production order. The current math parser explicitly selects this option. [Earley selection](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley.py), [sort keys](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py). |
| `ForestToPyDotVisitor`, `pydot__tree_to_dot/png`, `Tree.pretty()` | **Supporting diagnostics.** Makes packed sharing or conventional tree choices reviewable on small examples. Requires optional pydot/Graphviz for graph output; large forest diagrams are not an interpretation interface or a completeness test. [Forest visualization](https://github.com/lark-parser/lark/blob/1.3.1/lark/parsers/earley_forest.py), [tree utilities](https://github.com/lark-parser/lark/blob/1.3.1/lark/tree.py). |

## spaCy parallel candidates and annotation states

| Feature | Contribution and judgment |
| --- | --- |
| `Doc.spans[key]`, `SpanGroup`, `SpanGroup.attrs` | **Recommended for parallel, overlapping and nested candidates.** Separate groups can retain linguistic constituents, rule/model alternatives, labels and scores without forcing one segmentation. They do not encode a shared derivation forest or correlations between complete sentence readings. Stable candidate identity and cross-candidate compatibility remain application data. [SpanGroup API](https://spacy.io/api/spangroup), [group metadata](https://spacy.io/api/spangroup#attributes). |
| `Doc.ents` | **Supporting final non-overlapping entity annotation; not advantageous as the universal characterization store.** It cannot preserve simultaneous nested entities or a full inventory of predicate/scope alternatives. Keep it for the tasks whose semantics require a single entity sequence. [Doc entity API](https://spacy.io/api/doc#ents). |
| `Doc.set_ents(missing=..., default="missing")` | **Recommended where entity knowledge is partial.** Preserves unassessed regions instead of converting silence to a negative annotation. This is entity annotation state, not generalized uncertainty over all linguistic or semantic fields. [API](https://spacy.io/api/doc#set_ents), [entity states](https://spacy.io/api/doc#set_ents). |
| `Doc.set_ents(outside=...)` | **Supporting explicit entity negatives.** Marks assessed non-entity regions. Use only where the annotation scope supports that conclusion; it says nothing about predicatehood, concepts or other candidate types. [API](https://spacy.io/api/doc#set_ents). |
| `Doc.set_ents(blocked=...)` | **Supporting task-specific prohibition.** Built-in NER treats these regions as blocked, while other components may ignore them. It cannot serve as a universal constraint over combined spaCy/Lark interpretations. The entity-state groups supplied to `set_ents` must not overlap. [API](https://spacy.io/api/doc#set_ents), [entity-state contract](https://spacy.io/api/doc#set_ents). |
| `Doc.set_ents(default="unmodified")` | **Supporting composition of partial entity updates.** Preserves untouched state when adding one provider's assessed regions. Provider precedence and disagreement handling remain explicit work. [API](https://spacy.io/api/doc#set_ents). |
| NER `incorrect_spans_key` | **Supporting targeted negative supervision.** Trains against exact incorrect entity candidates without treating all other text as exhaustively negative. It is not an inference-time alternative representation and does not reject every overlapping hypothesis. [EntityRecognizer API](https://spacy.io/api/entityrecognizer), [models and supervision](models-supervision-and-evaluation.md). |
| `Doc.has_annotation(attr, require_complete=True)` | **Recommended annotation prerequisite check.** Distinguishes some annotation from complete annotation before a dependent interpretation pass. Completeness does not establish correctness, and empty Docs return true. Current [retained column availability](../../../../python/corpus-structure/src/corpus_structure/ingest/annotations.py) carries additional source/profile custody that this check does not replace. [API](https://spacy.io/api/doc#has_annotation), [annotation contract](https://spacy.io/api/doc#has_annotation). |

`SpanRuler`, `SpanFinder`, shared suggesters and multilabel `SpanCategorizer` are valuable
candidate producers and classifiers; their distinct judgments belong in
[matching and candidates](extraction-classification-and-normalization.md) and
[models and supervision](models-supervision-and-evaluation.md). Their output can seed formal
characterization, but a set of scored spans is not itself a correlated sentence interpretation.
The present [linguistic product](../../../../python/corpus-structure/src/corpus_structure/ingest/annotations.py)
retains one head/dependency per token and availability states; it does not thereby retain
alternative dependency parses or these entity supervision states. This is a scoped source
observation, not a prohibition on redesigning that product.

## Coverage and remaining question

The next design question is which native forest/annotation composition can preserve supported
sentence readings, shared constituents and interpretation dependencies with a clear grammar
and semantic algebra. No measured ambiguity growth or application efficacy is claimed.
The consequential native contracts above were checked in installed release sources; links use
matching tagged Lark primary sources or official spaCy APIs. spaCy-specific edge cases were
checked in installed 3.8.18 source; the official APIs are mutable, and an external 3.8.18
source tag was not established. No installation or compatibility qualification
was attempted. Retention and lifecycle choices are in [execution and retention](execution-retention-and-tools.md).

| Guide sections read end to end for this topic | Disposition |
| --- | --- |
| Lark original §§5.1–5.6; addendum §§1.1–1.3, 5.1–5.3, 9.2 | Ambiguity modes; forest objects/traversal/transformation; ranking, cycles, caching and diagnostics above |
| Lark original §§6–7; addendum §§3–4 | Source/sharing constraints above; complete representation judgments in [representations and composition](representations-and-composition.md) |
| spaCy original §§2.1–2.4; addendum §§2.1–2.3, 12.1–12.4 | Overlap and annotation-state judgments above; alignment/composition in [representations and composition](representations-and-composition.md) |
