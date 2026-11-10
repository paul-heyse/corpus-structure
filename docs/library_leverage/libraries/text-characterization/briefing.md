# spaCy and Lark: maximal primary text characterization

**Repeated discovery, 2026-11-10; recommendations and benefits Proposed.** The target is a
comprehensive, formally structured primary representation of the text, including sentence
interpretations, from which later conceptual relationships and analytics can be composed.
The scope permits substantial replacement of current representations and pipeline boundaries.

## Judgment

**Recommended target direction:** primary extraction should own the complete supported language
characterization, including predicates, arguments, complements, modifiers, clause structure,
coordination, voice, polarity, modality, quantification, attribution, scope and sentence function.
These interpretations should be explicit products expressed through library-native annotations,
patterns, grammars, transformations and trainable components, rather than privately reconstructed
by downstream consumers. Several dependent passes can form that primary layer.

The capabilities support a materially richer target than token/sentence segmentation followed by
scattered extraction rules. The principal recommendations are:

| Recommendation | Library functionality and contribution | Judgment |
| --- | --- | --- |
| Retain rich linguistic units and attributes | spaCy [Token/Doc annotations](https://spacy.io/api/doc), dependency traversal, noun chunks and pattern-based constructions expose lexical, morphological and grammatical structure | **Recommended.** Expand the shared primary products beyond the columns already retained |
| Formalize sentence interpretation | [DependencyMatcher](https://spacy.io/api/dependencymatcher) and contextual token patterns, configured [TrainablePipe](https://spacy.io/api/pipe) components, and Lark grammar rules plus typed transformations can represent predicates, roles, qualifiers and scopes | **Recommended direction.** Some semantics need authored rules or learned tasks; formalization is broader than adopting a stock parser |
| Preserve simultaneous characterizations | spaCy [SpanGroup](https://spacy.io/api/spangroup)/[SpanRuler](https://spacy.io/api/spanruler) and multilabel span tasks retain nested/overlapping units and labels | **Recommended.** A single non-overlapping entity sequence cannot express the intended depth |
| Preserve correlated alternative readings and compute over them | Lark [explicit ambiguity/SPPF and forest processing](https://lark-parser.readthedocs.io/en/stable/forest.html), including ForestVisitor, ForestTransformer and TreeForestTransformer expose alternative derivations and direct transformations | **Primary candidate, promising with unresolved realization.** Assess as representation and computation, not merely a speed optimization |
| Compose formal languages with language analysis | Lark lexical/contextual/generalized parsing, [modular grammars](https://lark-parser.readthedocs.io/en/stable/grammar.html), custom typed input and AST construction can combine linguistic and formal constituents | **Recommended to develop in the target.** Select grammar/annotation boundaries by the structure preserved, not current module layout |
| Learn additional characterizations where useful | [SpanFinder](https://spacy.io/api/spanfinder), [SpanCategorizer](https://spacy.io/api/spancategorizer), custom suggesters, shared encoders and custom trainable tasks extend proposal, label and structured-output capabilities | **Promising.** Review usefulness now; supervision, model suitability and artifact qualification determine realization |
| Carry the useful structure into later consumption | Native [annotation interchange](https://spacy.io/api/docbin), positioned ASTs, controlled serialization and reusable preparation retain characterized products | **Recommended supporting capability.** Choose retention by the meaning consumers require rather than forcing all results into one native object type |

These are discovery recommendations, not accepted implementation or measured efficacy claims.
Sentence-internal relationships such as predicate–argument structure belong to the characterization
model. A later edge between independently characterized concepts/assertions has a different role.
A source interpretation also remains distinguishable from an admitted scientific assertion.

## Topic briefings and feature index

All substantive content is directly in this folder. Each feature entry states functionality,
contribution, judgment/reason, prerequisites or residual authored work, and direct primary sources.
Current call sites appear beside relevant capabilities, not in separate journey narratives.

| Topic | Feature coverage |
| --- | --- |
| [Segmentation and lexical analysis](segmentation-and-lexical-analysis.md) | Tokenization/customization, sentence alternatives, POS/morphology/lemma, contextual correction; lexical-only/basic/contextual/dynamic/exhaustive/custom lexing, priorities, Unicode, callbacks, postlex, indentation and ignored material |
| [Sentence structure and interpretation](sentence-structure-and-interpretation.md) | Native dependency queries and operator families; predicates/arguments, clauses, coordination and qualified interpretation; recursive grammars, templates, imports/extensions, starts, aliases and semantic handlers |
| [Ambiguity and alternative interpretations](ambiguity-and-alternative-interpretations.md) | Overlapping annotation states, explicit alternatives and SPPFs; forest nodes, traversal, direct transformation, ambiguity handlers, prioritization/caching/cycles and expansion |
| [Extraction, classification and normalization](extraction-classification-and-normalization.md) | Matcher families/rulers, fuzzy/regex/morphological/custom predicates, NER, finders/categorizers/suggesters, score/candidate retention, passage labels and canonical-ID proposals |
| [Representations and composition](representations-and-composition.md) | Native document/tree models, custom annotations, token/node filtering and positions, ASTs, traversal/transformation variants, structural matching/rewriting/reconstruction and compositions across libraries |
| [Models, supervision and evaluation](models-supervision-and-evaluation.md) | Lexical/contextual encoders, listeners/transformers/Thinc/custom tasks; initialization, freezing/sourcing, supervision/alignment/readers, augmentation/adaptation/scoring and companion producers |
| [Execution, retention and tools](execution-retention-and-tools.md) | Configuration/component lifecycle, batching/errors/memory/hardware, arrays/JSON/binary/DocBin, grammar loading/caching/deployment, diagnostics/interactive recovery, visualization/workflows and ecosystem tooling |

Judgments distinguish **Recommended**, **Promising with unresolved questions**, **Supporting** and
**Not advantageous for this target**. A recommendation concerns functional/design value, not
permission to deploy. Compatibility restrictions are recorded separately from usefulness. A missing
current caller, a missing training set or the absence of a diagnosed defect does not exclude a
capability from this review. Features not selected for the primary layer still receive a reasoned
brief disposition, including features whose value is downstream or operational.

## Research basis and current integration

Both complete supplied guides were reread end to end during the replacement planning: the
[spaCy guide](../../../libraries/parsing/spacy.md), 2,782 lines, and
[Lark guide](../../../libraries/parsing/lark.md), 2,223 lines, including both addenda.
Topic briefings map the relevant guide sections to their feature judgments. Addendum corrections
prevail over earlier guide statements; mutable documentation is checked against selected-version
source where the distinction matters. These guides orient the inquiry; adjacent official API,
reference and implementation links establish the specific mechanisms discussed.

Source baseline is `e283a63c09c8881698a51495c9dbe48f757b44f3`, main, 2026-11-10. The pending
previous discovery revisions were source notes for reassessment and are replaced by this account.
Earlier retained evidence keeps its original dates and limits. Concurrent CLI/refusal/reporting
repairs, D8/DESIGN edits and ADR-0080 arose during publication; they are preserved and excluded
from this discovery's source assessment. Publication page counts include the shared tree. The root uv selection is
spaCy3.8.18, en_core_web_sm3.8.0, Lark1.3.1 and SymPy1.14.0 on Python3.14.10/Linux; companion
installation, configured activation and actual runtime execution are distinct facts. No new
provider run, model fitting or performance measurement was performed for this documentary review.

Current source already has source-aligned token layouts, richer retained linguistic columns,
consumer-local spaCy views, named token/phrase/dependency rules, predicate interpretation recipes,
positioned mathematical parsing and bounded nonmath field grammars. That is useful existing
integration, not the intended ceiling. The review asks which interpretations should move into
coherent primary characterization and which native capabilities should reshape its representation.
The relevant owners remain [D1](../../../design/D1-knowledge-representation.md),
[D4](../../../design/D4-method-catalog.md), [ADR-0062](../../../adr/0062-progressive-contributions.md)
and the [full-book benchmark decision](../../../adr/0070-full-book-method-development.md).
PM2 and WCE retain their execution/qualification dispositions; their immediate scope does not
limit these research judgments.

## Integrated consequences and next decisions

The [integrated functional review](../../../functional_reviews/text-characterization_2026-11-10.md)
now selects a complete proposed target and disposes these discovery leads. It owns comparative
selection; the capability judgments here remain reusable research context.

A full target design should determine the typed sentence-characterization products, including
predicate/argument/qualifier structures and alternative interpretations, before preserving the
current division between annotation, rules, frames and later extraction. It should examine native
spaCy annotations, positioned Lark structures and shared alternatives together. Library mechanisms
supply representation and processing; authored linguistic/domain declarations still define the
specific interpretations, constraints and label meanings.

The most consequential unresolved choice is how far a common ambiguity-aware representation
should extend across linguistic and formal analysis. An SPPF represents derivations of a declared
grammar; a spaCy dependency tree is a predicted analysis, and overlapping spans are different again.
The review recommends preserving these distinctions while investigating a coherent primary product,
not pretending that one format automatically subsumes all three.

Follow-up applicability/comparative work should develop this complete target and its consumer
migration, including removal of superseded private recognition/interpretation mechanisms. It need
not begin by finding a small defect in today's pipeline. The chosen design should explain how a
new sentence characterization is added once and then reused, and how alternative readings remain
available without converting them prematurely into accepted knowledge links.

The [selected principles and heuristics](../../../design_review/design_principles/standard.toml)
favor explicit semantic models, scoped authority, composition and a credible execution route.
Relevant leverage patterns are LOP-03/06/07/09/12 and LOP-X004: broader adopted capability, faithful
representations, reusable preparation, shared characterization and complete prepared products.
No new process gate or alignment lint is introduced.

Publication checks are recorded in STATUS. Product tests, runtime probes, model/provider runs and
benchmarks are **not_run**: this review establishes capability and design judgments through source
and reference investigation, with efficacy and any unresolved realization questions kept explicit.
