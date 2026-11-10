# Current characterization and conceptual consumers

**Source-inspected, 2026-11-10; broader benefits Proposed.** Uses the
[shared baseline](../briefing.md#baseline-and-evidence). Historical outcomes below retain their
original scope and dates; this pass ran no providers or product tests.

## What is already shared

Native PDF products and projected SourceViews supply text, geometry, item and piece identity.
[Source preparation](../../../../../python/corpus-structure/src/corpus_structure/methods/source_preparation.py)
groups native pieces by block and preserves formula/reference atom extents. It can consume
persisted annotations. Annotation preparation defaults to a configurable 32,768-character block bound; unavailable
coverage must be examined before claiming maximal characterization of the book.

[Sentence preparation](../../../../../python/corpus-structure/src/corpus_structure/ingest/sentences.py)
tokenizes prose and inserts inline formulas and references as native atoms, preserving exact
source reconstruction. Its sentence-only profile excludes NER and lemmatization. A separate
[richer annotation profile](../../../../../python/corpus-structure/src/corpus_structure/ingest/annotations.py)
retains lemma, POS, tag, morphology, dependency/head, sentence ownership, source pieces and
source/layout/model/configuration identities. It checks token stability and required-column
availability. Neither model labels nor the source role `math` establish mathematical meaning.

The [native view](../../../../../python/corpus-structure/src/corpus_structure/ingest/annotation_views.py)
constructs a local mutable spaCy Doc from retained columns. It performs no tokenizer or model
inference and checks reconstructed text, coordinates, head indices and sentence ownership.
Missing persisted products do not silently trigger inference in
[consume_annotations](../../../../../python/corpus-structure/src/corpus_structure/methods/m1_annotations.py).
There is therefore no basis for describing the current pipeline as reparsing prose from zero
for every rule.

Later [named rules](../../../../../python/corpus-structure/src/corpus_structure/methods/annotation_rules.py)
prepare token, phrase and dependency matchers and generate located roles, expansions, overlapping
candidates, availability and source provenance. The reconciled group currently copies the raw
group; a preset suggester is constructed, not a trained classifier. Specialized
[predicate frames](../../../../../python/corpus-structure/src/corpus_structure/methods/predicate_frames.py)
also prepare matchers and perform traversal. Consumers include
[M1 source extraction](../../../../../python/corpus-structure/src/corpus_structure/methods/m1_source.py),
[definition applicability](../../../../../python/corpus-structure/src/corpus_structure/methods/definition_applicability.py)
and [witnessed links](../../../../../python/corpus-structure/src/corpus_structure/methods/witnessed_source_links.py).
Repeated matching and role projection are concrete research territory. Similar code does not
prove equal semantics: polarity, modality, nominal complements and local attachment can differ.

Math has a shared [Lark grammar](../../../../../python/corpus-structure/src/corpus_structure/methods/math/grammar.py)
over installed SymPy LaTeX grammar plus extension, positioned dynamic Earley parsing and explicit
ambiguity. [Occurrence extraction](../../../../../python/corpus-structure/src/corpus_structure/methods/math/spans.py)
maps relative parser positions into source coordinates. The operation's
[PreparedMathInput](../../../../../python/corpus-structure/src/corpus_structure/methods/math/prepared.py)
memoizes lexical capture, syntax, interpretation and optional symbolic work. Syntax projection
can consume an existing tree without reparsing. Moving these capabilities earlier would change
demand and custody boundaries, not introduce sharing where none exists.

Non-math [structural parsing](../../../../../python/corpus-structure/src/corpus_structure/semantic/structural_parsing.py)
already uses cached lexer-only and contextual-LALR grammars for thresholds and explicitly
delimited date/identifier/quantity/range fields. Candidate nomination scans positioned tokens;
comparison-basis and revision recognizers in the same module remain regexes.
[Structural products](../../../../../python/corpus-structure/src/corpus_structure/methods/structural_products.py)
and [predicate contributions](../../../../../python/corpus-structure/src/corpus_structure/methods/predicate_contributions.py)
use these later in typed product preparation. These bounded field grammars are not a general
prose parser. Their admission-side checks are not automatically redundant characterization:
independent verification across that boundary can have a separate purpose.

## Concrete journeys for broader discovery

### Definition 3.6: surface structure before definition membership

The binomial declaration exposes term, naming subject, restrictions involving n/p, B declaration,
formula and explanatory text. The [November9 boundary diagnostic](../../../../design_review/evidence/2026-11-09_pm2-gliner-boundary/README.md)
found term/naming-subject/B proposals, but not the p restriction in the ordinary candidate pool;
intended endpoints were not decoded. Retaining richer phrase, clause, restriction and declaration
characterizations could give several consumers the same exact candidates. It cannot alone decide
which content defines the term or distinguish qualification of the content from qualification of
the defining act. **Next:** map independently expected spans to token representability, proposal
availability and later attachment separately. Reuse the existing diagnostic as dated evidence,
not proof that a spaCy classifier would solve the case.

### Fair coin: condition, action and literal before host selection

The passage beginning “If the coin is fair” contains a conditional cue, assignment action and
the 1/8 probability occurrence. [PM2 interpretation](../../../../plans/production-milestone-two/gliner-and-d1-interpretation.md)
and the [parser account](../../../../plans/production-milestone-two/linguistic-referential-discourse.md)
retain the distinction between literal recovery and unresolved host interpretation, including a
reviewed-candidate diagnostic. Earlier cue, clause, argument and quantity syntax could be shared
across consumers. **Next:** determine whether the ordinary characterization supplies all required
units; evaluate the host decision separately. Correct reviewed candidates are a diagnostic ceiling,
not ordinary source-first recall or an accepted semantic relationship.

### Positive variance: preserve a successful bounded control

The p289 phrase “with positive variance” and neighboring predicate offer a modifier/premise and
attachment case. The [PM2 coordinator](../../../../plans/production-milestone-two_2026-11-08.md)
records a bounded native admission/Reader/CLI/MCP/detached journey, while wider parser comparisons
remain open. **Next:** ask whether a shared modifier/qualification characterization can support
that existing consumer without changing its successful exact source association. A new parser
missing the cue cannot be judged sufficient because its general syntax is richer.

### Section 5.1: reference syntax before target resolution

The printed citation and `see` cue can be characterized independently of the heading they target.
The [retained example](../../../../examples/README.md#a-printed-reference-becomes-a-typed-link)
and [PM2 replay account](../../../../plans/production-milestone-two_2026-11-08.md)
show why native piece/item association matters: character overlap had implicated a different
block. A shared representation could retain cue, designator components, exact native membership
and heading candidates. **Next:** compare grammar-derived designator structure with current
phrase rules; keep target retrieval/selection as a distinct conceptual operation. Equal printed
references at different locations must remain distinct occurrences.

### Affine X/Z: formal syntax before scoped symbol identity

Lark can retain formula structure and exact symbol occurrences; prose contributes declarations.
The [candidate/selection examples](../../../../examples/README.md#candidates-and-selected-relationships)
preserve an unresolved X with candidate referents and a separately witnessed Z declaration link.
The [affine assessment](../../../../plans/production-milestone-two/textbook-assessment-and-adoption.md)
keeps formal characterization and referent support separate. **Next:** determine the reusable
formal/prose units needed for binding while retaining absent, ambiguous and unsupported choices.
Symbol spelling and mathematical normalization cannot substitute for source occurrence identity.

## Additional stress cases and coverage limits

Tables/cells, captions, lists, display formulas, repeated mentions, nested and discontinuous
phrases are selected stress scenarios for the proposed representation. The inspected annotation
producer supports paragraph/list-item/table-cell/caption blocks; this does not establish that all
book instances or cross-block constructions were characterized successfully. Discovery did not
run a fresh enumeration-specific or table-level efficacy assessment. Before generalizing, inspect
exact retained source cases and determine which boundaries preserve real layout structure and
which merely reflect current physical execution.

The map is representative source investigation across the named producers, consumers and linked
PM2/WCE material, not an exhaustive inventory of all extraction code or SQL readers. The current
source demonstrates existing sharing and later rule/field extraction; it does not establish the
best placement of every capability. The [composition inquiry](composition.md) states what the
new target would need to change and how to compare it without an automatic full-book rerun.
