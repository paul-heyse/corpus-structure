# Next corpus enrichment increment

**Proposed · 2026-11-07.** Functional-extension review of the combined recommendations in
`docs/target-pipeline-design/production-miletone-one-further-improved.md`. The later specificity
pass governs wherever the two sections conflict. The crosswalk at the end preserves the
earlier recommendations that remain applicable, the corrections, and the conditional work.
The supplied proposal was present as an untracked working-tree input with SHA-256
`aaef057ef070214e8ff05361649bd2c33f8159498f5a83e811a4920b996515f6`.

## Recommendation and evidence baseline

Start with exact caption projection, located qualification, and witnessed reference and
declaration links. These increments give the operator more source-grounded components and
more useful navigation through existing inspection surfaces. Extend those products into clause
comparison and rooted dossiers. Assess GLiNER descriptions, clause classification and candidate
recovery independently so a change in model outputs can be traced to the change that caused it.
Keep the emitted attachment-event rubric and the shared table-correspondence question as
parallel bounded research. [WCE repair disposition](../plans/witnessed-corpus-enrichment_2026-11-05.md#repair-disposition--2026-11-07)

This review inspects `e68623e26` and the live working tree on 2026-11-07. Relevant concurrent
changes include the reader-side fitting census and CLI, plus native deployment and target
work. The recorded WCE results belong to their own native products and immutable cuts, including
product baseline `07d25b840`, native165, and the contextual correction at run207/cut287. The
selected reference corpus is Grinstead–Snell physical pages 191–310 under ADR-0068. The
12 retained packets and their 48 views supply the bounded source-reference cases used here.
Corporate policy and procedure examples below specify behavior and serve as proposed contract
controls. [Current checkpoint](../../STATUS.md) · [ADR-0068](../adr/0068-single-corpus-method-development.md) ·
[Source reference scope](../design_review/evidence/2026-11-06_wce-completion-repair/source-references/README.md)

| Recorded boundary | What it supports in this review |
|---|---|
| WCE-R15. Scoped dice edges were recovered. Run207 preserved the candidate for affine-transform X and withheld the false red-ball link. | Retain abstention as a useful outcome. The exact formula Z occurrence and the eligible standard-normal target are distinct missing prerequisites. |
| WCE-R17. Rooted dossier delivery passed with two members, both of which fit the budget. | Extend justified membership. Display-optimization benefit still needs a binding budget and competing useful content. |
| WCE-R18. Both weighted table modes selected all nine supported roles at the tested scales. | A different marginal distribution alone supplies no demonstrated selection gain. The native factor reconstruction remains open. |
| WCE-R19. Artifact205 retained 142 occurrences, 116 candidates and 25 exact source nominations. | Existing nominations and native delivery are a real baseline. Three of 13 supported reference-to-caption pairs lack projected endpoints. All 142 alias states in this frame are unknown. |
| WCE09. The bounded census found 82 group-derived defining-text attachment rows and no compatible `relation.defined_by` rows or protected event evaluations. | Establish a precise emitted-event rubric and eligible feature frame before fitting. |

The review uses the full primary library guides and their available addenda for spaCy 3.8.18,
GLiNER2 2.1.0, Lark 1.3.1, Splink 5.0.0, scikit-learn 1.9.1, SciPy 1.18.1, and candidate pgmpy
1.1.2 and Pyro 1.9.2. The first six versions are pinned in the workspace. pgmpy and Pyro are
conditional library candidates. The GLiNER runtime, checkpoint and schema/decoder profile
remain separate identities. The per-opportunity references distinguish inspected interfaces
from proposed compositions. [Workspace pins](../../python/corpus-structure/pyproject.toml) ·
[Library guides](../libraries/README.md) ·
[Design standard](../design_review/design_principles/standard.toml)

<a id="O01"></a>

## O01 · Expose retained native captions as exact structural passages

**Develop first.** A reader inspecting a table reference should be able to follow it to its
original caption. The existing citation contract requires an exact projected passage. In the
three recorded omissions, the captions are already body items reached by both the table's
ordinary children and its caption references. The table branch of `project_section_nodes`
emits cell pieces and returns before it visits those children. The source records and the
projection omission can be inspected independently of the artifact scorer. [Projector](../../python/corpus-structure/src/corpus_structure/ingest/pdf_hierarchy.py) ·
[Recorded source references](../design_review/evidence/2026-11-06_wce-completion-repair/source-references/README.md) ·
[Pinned native document types](https://github.com/docling-project/docling-core/blob/v2.105.0/docling_core/types/doc/document.py)

| Caption | Exact retained occurrence in the frozen selection | Current projected span |
|---|---|---|
| Table 5.8 | Physical page 224, source view 118, table `#/tables/0`, caption `#/texts/65` | Unavailable |
| Table 5.9 | Physical page 224, source view 118, table `#/tables/1`, caption `#/texts/66` | Unavailable |
| Table 6.1 | Physical page 234, source view 124, table `#/tables/0`, caption `#/texts/37` | Unavailable |

**Realization.** In the existing section owner, qualify caption children and caption
references against the exact selected body membership and archived native product. Give the
projector the same eligible set in both the object and record-backed paths. Preserve ordinary
source traversal and cell order. In the table branch, emit qualified caption text after the
cell sequence, using native child order followed by remaining caption reference order.
Deduplicate by caption pointer inside one native product and view. Across overlapping views,
retain each view's citation and the shared physical occurrence identity. Use the original
`text` field, the caption's own pointer and ordinary `native_text` pieces. Keep synthetic
newlines separately addressable. A caption that also appears as an ordinary non-table child
uses its ordinary position, which requires a single admission decision for that view.
Rich-cell content retains its cell-specific identity and traversal. [Published source-view builder](../../python/corpus-structure/src/corpus_structure/ingest/pdf_section_views.py) ·
[Object-backed builder](../../python/corpus-structure/src/corpus_structure/ingest/pdf_methods.py)

The native publication guard reconstructs the selected membership and checks each projected
piece against the original native field. A pointer returned by an exact read can still be
outside that membership. Keep the first increment within existing membership. For any later
caption attached only by reference outside the selection, retain it as an unresolved association
in that view and investigate explicit selected-membership semantics separately. Scope, body
layer, owner identity and source text must be authenticated before admitting such a piece.
[Native publication guard](../../python/corpus-structure/src/corpus_structure/semantic/sql/source_views.sql)

Publish both builders under one new projection recipe identity and regenerate affected source
views and consumers of their offsets. Reuse the immutable native product. Retained annotations
and model reports can be reused where their exact input and mapping dependencies remain
substitutable, with explicit correspondence for any remap. Regenerate changed views,
passages, and downstream products where those premises differ. Expose each recovered caption
through bounded structural passage selection so existing discovery and `ArtifactCitation`
construction can consume it. Compare by native occurrence and exact text before comparing
shifted projection offsets. [Structural source preparation](../../python/corpus-structure/src/corpus_structure/semantic/structural_sources.py) ·
[Artifact discovery](../../python/corpus-structure/src/corpus_structure/methods/artifact_identity.py) ·
[Current-only migration](../adr/0067-witnessed-current-only-cutover.md)

**Acceptance.** All three captions appear once per selected view with the same native pointers
and exact text. Separate tables or captions with equal text remain distinct. Exercise object
and record-backed parity, overlapping and direct section selections, furniture and foreign
caption refusal, rich-cell preservation, publication replay and bounded Reader/export
citations. On the unchanged source reference frame, show each newly representable endpoint
and whether its supported pair becomes reachable. Report discovery and selection separately.
Compare source-side unmatched opportunities as well as emitted outputs.

**Compatible extensions.** Inspect retained fragments and graphical labels where a concrete
consumer can use item-level evidence. Use the existing native item or region reader when a
physical pointer or region is all the source establishes. A text consumer gets a span only
when an exact source field and offsets exist. The first caption increment has a narrower
purpose than expanding OCR or promoting item evidence into exact artifact citations. For
retained GLiNER groups, expose independently valid exact components with unresolved grouping
kept separately under [O09](#O09). A wider recovery pass starts when a specific retained field,
lost during decoding, can be tied to an independently judged useful component.

<a id="O02"></a>

## O02 · Attach located qualifications to the proposition they govern

**Proposed · Recommended.** A reader should be able to see the conditions under which a definition,
assertion or instruction applies, which exception changes it, who made the statement, and which
parts remain unresolved. The source assessment locates Event F, positive variance, normal
parameters, local urn labels, exercise proof requests, and the zero-wait convention. Some of these
details survive elsewhere in retained output. A consumer still needs a witnessed attachment to the
particular statement before it can use the detail as an applicability premise. [Source assessment](../design_review/evidence/2026-11-06_wce-gs120/assessment/benefit-account/README.md)

**Implementation.** Keep a located qualifier contribution independent of its attachment. Reuse
witnessed component and scoped relationship custody. Each proposed attachment should identify the
exact qualifier occurrence or extent set, exact host proposition or relationship, direction and
semantic role, passage/view, applicable scope and version, and source basis. Retain competing host
and scope readings. Support multiple qualifiers for a host and reuse of the same qualifier across
several hosts only through independently justified attachments. Treat condition, assumption,
parameterization, exception, attribution, modality, order and semantic dependency as distinct roles.
Reuse established predicates where their meaning fits and declare any added predicate under the
model release. Order, semantic prerequisite and computation dependency answer different questions.
[Knowledge representation](../design/D1-knowledge-representation.md) · [Structural products](../../python/corpus-structure/src/corpus_structure/semantic/structural_products.py)

Lower a supported reading through the released model's existing `Qualification` and `Condition` contracts. Use atomic,
comparison, membership, claim-reference, conjunction, disjunction or negation types only where the
source and its bindings support the corresponding meaning. Use `EscapeCondition` where an attached condition's
text is established and its formal meaning cannot be represented. An unknown host remains an
unresolved attachment. Scope, polarity, modality and attribution carry their own meaning. Where
required qualification fields remain unknown, retain the contribution and unresolved reading until
the model can represent it without guessing. An exception or ordering cue can remain a separately
typed relation, with Boolean lowering requiring its own supporting interpretation. Keep one
authority for the interpreted condition and references from derived consumers. [Existing model declarations](../../python/corpus-structure/src/corpus_structure/model/semantic/core.yaml)

**Alternatives and delivery.** Inlining every detected qualifier in `LocatedDefinitionComponent` would make an isolated
definition convenient to display, but a shared condition, unknown host or competing attachment would
require repeating or prematurely selecting evidence. A source-bound relation keeps those cases
available for qualified comparison, contextual selection, dossier membership and gap reporting.
Regenerate affected semantic products under a versioned operation. Reprocess source annotations only
where the chosen producer actually changes them. Preserve earlier outputs and let dossier rendering
project the attached qualifiers with their citations. Use existing Reader, CLI, MCP and detached
closure paths for delivery where they expose the affected products.

**Acceptance.** Assess qualifier span, host, attachment kind, scope and logical lowering separately
against the frozen WCE source judgments. Include a positive definition containing negative content,
a shared condition on two coordinated instructions, a nearby unrelated exception, and an attributed
historical claim. In a purchase-review rule, demonstrate a reviewer, form, approval boundary,
high-risk applicability condition and approved exception, with the action and condition available
when the artifact target is unresolved. Ensure downstream readers can tell unknown host, unknown
interpretation and absent from the selected view apart. Quantify any improvement only after matched
assessment.

<a id="O03"></a>

## O03 · Compose predicate and role readings over retained annotations

**Proposed · Recommended.** Start with the current `AnnotationView` and named-rule infrastructure. The view
already checks reconstructed block text and token coordinates, dependency heads, and sentence
ownership. The observed errors are in the use of these annotations as much as in the annotations
themselves. `procedure_frames` starts from prose verbs, nominal expansion can omit complements, and its enclosing
interval can include material between selected tokens. `PreparedAnnotationRules.match` clips certain roles at lexical
boundaries, and named definition construction currently discards matches with any negation extents.
Keep the distinct extraction and interpretation stages so useful source evidence can survive an
unresolved decision. [Annotation views](../../python/corpus-structure/src/corpus_structure/ingest/annotation_views.py) · [Annotation rules](../../python/corpus-structure/src/corpus_structure/methods/annotation_rules.py) · [Procedure roles](../../python/corpus-structure/src/corpus_structure/methods/structural_roles.py) · [Definition applicability](../../python/corpus-structure/src/corpus_structure/methods/definition_applicability.py)

1. **Expand named roles with grammatical limits.** Start from the retained head and base noun chunk
   when available. Include permitted nominal complements such as the prepositional complement in “a
   set of constant density.” Keep the matched token membership and coalesced extents. Emit a
   contiguous span only when all intervening material belongs to the role, retaining gaps and
   partial roles otherwise. Stop at competing coordinated heads and independently predicated
   clauses. Build explicit variants for active, passive and copular definitions, naming, and
   reported assumptions. Use `Matcher` for token and morphological cues, `PhraseMatcher` for controlled terminology,
   and `DependencyMatcher` for named immediate dependencies. A copula or proximity supplies a candidate, while the
   discourse reading determines whether a defining act took place. The subject of the assessed
   integral case is the probability of the stated comparison, which should compete as a full role
   against the spurious lone `Y`.
2. **Attach qualifications by predicate ownership.** Match the host, subordinate predicate and
   marker for initial direct cases, and use separate recipes for nominal exceptions or list/heading
   inheritance. Keep the proposition, its body, its qualifiers and host alternatives. Treat
   dependency output as linguistic evidence. Record the source predicate when coordination licenses
   propagation and retain independent local attachments when both clauses supply their own
   condition. A quoted cue is part of its containing phrase.
3. **Resolve the scope of negation, modality and attribution.** Locate the predicate each cue
   modifies and carry the cue's extent. Preserve a positive defining act with negation in its
   content, withhold a positive definition from “X is not defined here,” and distinguish historical
   attribution and contrast from a definition performed by the source. Keep unresolved negation
   across coordination when supported by competing readings.
4. **Extract neutral predicate frames before interpreting behavior.** Retain actor, action, object,
   voice, polarity, modality, conditions, exceptions and ordering cues. Record inherited roles or
   modals with their origin predicate. Interpret the frame using headings, list structure,
   worked-example context and, where available, [O09](#O09) predictions. Expose definition, explanation,
   reference, assumption or restriction, prescribed action, described process, and unresolved
   readings where applicable. A mathematical “must” can express a restriction. A procedure reader
   receives a prescribed step only when the source and interpretation support that role.
5. **Reuse qualified frames in comparison.** Current `clause_fields` drops repeated fields, `ClauseReading` enforces unique
   dimensions, and comparison builds a dimension-to-field map. Give each dimension a typed
   collection of cited members with explicit single, conjunctive, disjunctive or unresolved
   grouping. Preserve original order and distinguish missing from competing readings. Convert an
   authenticated prior single field only when it establishes a single-member reading. Regenerate
   derived products when the evidence for additional members or grouping is unavailable. Update
   dimension outcomes, applicability, renderers and the comparison-to-root consumer together. Keep
   the existing threshold difference operation where both sides have a supported common quantity,
   unit and basis. For compound conditions, retain per-member evidence and withhold stronger
   consequences until the grouping and semantic comparison are established. [Structural parsing](../../python/corpus-structure/src/corpus_structure/semantic/structural_parsing.py) · [Comparison method](../../python/corpus-structure/src/corpus_structure/methods/structural_products.py)

**Bounded formal parsing.** The current lexer-only and contextual LALR routes are the first choice
for locally delimited comparators, ranges, quantities, dates, identifiers, and explicitly defined
condition notation. Share grammar fragments through imports or templates when two real consumers
need the same syntax, and retain token offsets and typed AST spans. Keep source-language attachment
and discourse in the frame stage. Lower structured readings through [O02](#O02), keeping unsupported syntax
and unresolved value or unit bindings visible. A grammar success establishes syntax. Semantic
applicability needs a source-grounded host and compatible operands. [spaCy DependencyMatcher](https://spacy.io/api/dependencymatcher) · [Lark grammar reference](https://lark-parser.readthedocs.io/en/stable/grammar.html)

**Alternatives and acceptance.** Separate lexical rules are fast for cue discovery and useful for
parity, but clipping at words such as “if” loses grammatical ownership. Unrestricted subtree
expansion introduces competing propositions. A general natural-language condition grammar would
create a second broad interpretation path. Compare the existing baseline with named recipes on the
same retained annotations, then measure separately any changed annotation profile. Use the
historical Huygens passage, the integral and nominal-complement cases, a valid definition with
negative embedded content, and two differently scoped condition clauses. Include fronted shared
condition, quoted “if,” “do not heat and stir,” “do not heat, but stir,” and genuinely repeated
actors or conditions in a comparison. The criteria are correct extents and hosts, preservation of
unresolved readings and unchanged supported singleton comparison semantics. Regenerate rule, frame,
comparison and dossier products under their changed recipe identities and verify replay of the new
products and preserve prior evidence under its original custody.

<a id="O09"></a>

## O09 · Improve GLiNER questions and classify focused clauses

**Proposed · Recommended for descriptions and focused classification.** The pinned GLiNER 2.1.0
package and the selected checkpoint are distinct versioned inputs. `GlinerPack.compile` already uses `Schema.from_dict` and checks
native round trip. The V2 family pack already supports descriptions, optional scalars and multiple
defining fragments. The local definition pack still sends bare entity and relation names. The
JointIE investigation saw 2,143 term proposals, 117 content proposals and 22 proposed attachments
across 149 windows, with plausible-looking erroneous edges such as “binomial distribution” to
“Section 5.2.” Those observations establish concrete candidate and interpretation failures. They do
not identify a better threshold or an adoption case for joint decoding. [GLiNER adapter](../../python/corpus-structure/src/corpus_structure/methods/gliner.py) · [Definition pack](../../python/corpus-structure/src/corpus_structure/methods/definition_applicability.py) · [JointIE evidence](../design_review/evidence/2026-11-06_wce-gs120/joint-ie-investigation001/README.md)

**Implementation.** Give the defined expression, defining content and directed attachment versioned
descriptions. Describe the exact expression whose meaning is stated, the wording or formula that
conveys it including meaningful complements, and the term-occurrence-to-content-occurrence
direction. The pinned preprocessing path feeds entity descriptions to label conditioning and
relation descriptions to the relation prompt. Compare descriptions against the bare pack with the
same checkpoint, selected windows, threshold and decoding mode. Preserve independently located term
or content contributions when the joint attachment or a record grouping fails. Keep optional and
repeated cardinalities. Compare natural anchored and latent records only where actual repeated
instances or missing anchors justify them. Exclusivity can help when a particular field is
demonstrably unique to one assignment. Shared qualifiers need reusable source occurrences. [Pinned schema](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/schema.py) · [Pinned preprocessing](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processor.py)

Use the resident worker with a versioned classification-capable `native-combined-v2` pack. Give each request one
focused clause identity and its admitted context. The native classifier classifies its input as a
whole, so compare exact clause text with bounded context that marks the focus explicitly and
preserves the original context-to-source mapping. Separate clause function from presentation context
so a definition in an attributed historical example remains expressible. Use label descriptions
first and consider task prompts and versioned few-shot examples only as separate policy arms. Keep
label interpretation separate from evidence offsets. The native single-label decoder chooses an
argmax and the multi-label decoder also chooses an argmax when no score clears `cls_threshold`. Retain raw
outputs and make application-level abstention explicit. An `unresolved` semantic label and a decision to
withhold a prediction remain distinguishable. Compose with deterministic interpretation in [O03](#O03) and
preserve disagreement. [Pinned native runtime](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/runtime.py)

**Challengers.** Compare the native combined path with the dedicated `Classifier` only for a demonstrated
constraint over valid labels, recording exactness, feasibility and violations. A genuine implication
may help, while cross-axis mutual exclusion can erase valid readings. Keep Decide as a
classification challenger only if existing checkpoint and linguistic evidence leave a useful
residual gap. Include the smaller English Decide profile where compatible. The 1B card supplies
task-specific evidence and a different architecture, so qualify its worker/profile and selected
behavior separately. Revisit JointIE with corrected candidates and matched independent decoding,
typed endpoints, bounded search, and explicit infeasible handling. Graph consistency alone cannot
establish a relationship. [Classifier implementation](https://github.com/fastino-ai/GLiNER2/tree/v2.1.0/gliner2/classification) · [Decide 1B model card](https://huggingface.co/fastino/GLiNER2.5-Decide-1B)

**Acceptance.** Hold evaluation examples apart from prompt examples and tuning. Record case-level
changes for term and content role, extent, directed attachment, function, presentation context and
abstention. Include located positive and negative cases, both attributed and performed definitions,
examples containing genuine instructions, and conflicting rule/model signals. Keep profile, worker
operation, pack digest, clause identity, context and returned evidence in replay. Regenerate the
changed pack's affected products and downstream interpretations. Preserve earlier packs and outputs
under their original evidence custody.

<a id="O10"></a>

## O10 · Diagnose and recover source-aligned candidates before adding models

**Proposed · Recommended for targeted recovery and diagnostic visibility.** This extends O01, O03
and O09. Split a missed structural result into source extent availability, token alignment,
candidate proposal, scoring, overlap suppression, record grouping and attachment. Expose those
distinctions against inspected operation scope. A known source extent that cannot become a spaCy
span can still be a candidate from a different source-preserving producer.

- **Overlapping and alternate language candidates.** Compare the current flat GLiNER path with `nested`
  and `allow` on independently located nested roles. Use `Doc.spans` and `SpanGroup` to inspect overlapping linguistic
  proposals without flattening competing readings into `Doc.ents`. Use strict `Doc.char_span` as a diagnostic against
  the reconstructed block and compare its offset with the retained source coordinate. Use `SchemaTransformer.transform_record`,
  splitter-aware offset checks and annotation alignment checks around formula punctuation, repeated
  strings and combining marks. If punctuation, layout or segmentation failures recur, compare
  versioned tokenizer or `AttributeRuler` changes and layout-derived sentence starts with current annotation
  products. Never retokenize an already authenticated view in place. `displaCy` dependency and
  overlapping-span output can support targeted diagnosis using existing view data. [spaCy guide](../libraries/parsing/spacy.md) · [GLiNER guide](../libraries/parsing/gliner2.md)
- **Alternative proposals and context.** Test the boundary model's `score_explicit_spans` against validated spaCy or
  Lark spans to separate a missed neural proposal from poor scoring. Verify exact token alignment
  and retained raw evidence before admitting a new adapter. Changing candidate budgets or enabling
  count-guided decoding can alter coverage among proposals, with false additions assessed on the
  same cases. Evaluate context across heading, list, caption and display boundaries using the
  existing layout selection first. Compare native long-window APIs only when overlapping windows
  genuinely help. Preserve original offsets and chunk identities, and route cross-window links
  through explicit relationship selection when endpoints never co-occur. Use a released-format
  validator only for shape checks, keeping rejected raw proposals inspectable. [Pinned boundary model](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/model.py) · [Pinned overlap implementation](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/overlap.py)
- **Partial structure under formal ambiguity.** The existing `captured_formula_symbols` refuses a syntax tree with any `_ambig`.
  Compare that baseline with extracting an occurrence only when its exact extent, symbol and
  relevant syntactic role agree across the admitted parse alternatives. Test formula Z alongside the
  unsupported affine-X link. Keep ambiguity when binders, subscripts or scopes differ and preserve
  operation failure or budget exhaustion. Reuse the existing math grammar and macro context. For
  bounded field grammars consider Earley explicit alternatives or a bounded forest where the
  ambiguity has actual semantic consequences. Keep LALR for deterministic fields and use parser
  conflict checks during grammar preparation. `TextSlice` preserves original coordinates with basic or
  contextual lexers, while prefix line counting can offset its allocation benefit. Compare this with
  the existing slice and explicit base offset before changing the coordinate contract. Interactive
  parser expectations and `UnexpectedInput` diagnostics can help authors distinguish invalid notation from
  unavailable meaning. Synthetic recovery tokens remain diagnostics. [Lark guide](../libraries/parsing/lark.md) · [Pinned lexer](https://github.com/lark-parser/lark/blob/1.3.1/lark/lexer.py) · [Existing formula occurrence producer](../../python/corpus-structure/src/corpus_structure/methods/structural_roles.py)

**Conditional and low-fit routes.** Use `SpanFinder` and `SpanCategorizer` or a custom retained-candidate suggester only if
assessed residual boundary or role failures justify trained supervision. spaCy `Example` and `Scorer` can
support independent checks of alignment, positives, negatives and missing annotation. Consider
alternate spaCy parser profiles or GLiNER fine-tuning and LoRA or DoRA only after that analysis,
with independent located labels, declared source exposure and injection-free proposal recall. Use
source isolation for a separate transfer claim. Keep pinned profiles and adapter state isolated by
execution. spaCy rule IDs and `EntityLinker` are plausible for a controlled vocabulary, with contextual/prior
scoring and NIL, while [O04](#O04) still needs witnessed typed endpoints. Experimental spaCy coreference has
a compatibility constraint below the pinned spaCy version. Domain-specific, multilingual, PII and
safety checkpoints need a matching source workflow. The existing Docling path already owns layout
extraction. Generic extraction wrappers, second source pipelines, standalone parser generation,
alternative parser runtimes and unneeded provider deployment add little for the present cases.
Evaluate worker batching, precision and cache changes only where a material operational limitation
appears. Keep encoded states keyed to the complete effective input and schema. [spaCy SpanCategorizer](https://spacy.io/api/spancategorizer) · [spaCy EntityLinker](https://spacy.io/api/entitylinker) · [spaCy experimental requirements](https://github.com/explosion/spacy-experimental/blob/master/requirements.txt) · [GLiNER 2.1.0 release](https://github.com/fastino-ai/GLiNER2/releases/tag/v2.1.0)

**Acceptance.** Use a matched panel with a supported nested role, formula symbol, repeated surface
form, an ambiguous host, and a genuinely unsupported target. Recover exact evidence and show why it
was previously unavailable. Preserve unrelated candidates, unresolved outcomes, and negative
controls. Report newly captured source opportunities separately from better decisions on unchanged
candidates. Retain prior operation products and expose new outcomes through the existing structural
consumers. Provider execution for these proposals was `not_run`.

<a id="O04"></a>

## O04 · Link distinct occurrences through source witnesses

**Proposed.** Let the corpus reader follow a named reference, controlled artifact mention, or symbol
use to the particular occurrence that explains it, with the source evidence and applicable scope
visible. In the GS120 repair, 90 candidate lists survived, the selector withheld the unrelated
affine-transform `X` link, and the relevant formula `Z` occurrence and eligible standard-normal
target were unavailable. The recorded outcomes distinguish source capture, target inventory,
retrieval and relationship selection. Each layer needs its own remedy. [Contextual repair](../design_review/evidence/2026-11-06_wce-completion-repair/composition/README.md)

The current contextual method already freezes exact target membership, ranks alias, lexical and
dense candidates, and selects through role- and scope-qualified witnesses. Its producer recipes join
located roles from one matched group to an available target label. That can express useful local
evidence, but a matching label in another selected view cannot by itself establish an endpoint. The
existing artifact producer resolves a unique same-view caption by explicit cue and code. The
existing symbol producer emits scoped `declares` relationships. Both supply starting points for
authenticated links between distinct occurrences. [Candidate and witness construction](../../python/corpus-structure/src/corpus_structure/methods/contextual_candidates.py) · [Selector contracts](../../python/corpus-structure/src/corpus_structure/semantic/contextual_links.py) · [Scoped producer](../../python/corpus-structure/src/corpus_structure/methods/scoped_relations.py)

Develop the extension in three parts.

1. **Make the named roles and target identity available.** Use retained source layout, O01 endpoints
   and O03 spaCy patterns for explicit “see Section …”, “as defined in …”, “X, hereafter Y”, acronym
   introductions, renamings and references from a procedure step to a controlled artifact. Bind the
   cue and mention to their original extents. Use structural IDs or explicit naming relations when
   available. spaCy `Matcher` or `DependencyMatcher` can locate the cue and its arguments. The source, section and
   declaration products establish which target those arguments identify. For formula use, compose
   the actual scoped `declares` decision with the use occurrence, with navigation in either direction and
   the declared direction retained. A repeated glyph in a different exercise or an exact string in
   another work remains a candidate until scope is established. [spaCy guide](../libraries/parsing/spacy.md) · [Rule-based matching](https://spacy.io/usage/rule-based-matching)
2. **Bring witnessed targets into the declared candidate space.** Freeze the selected views, cut,
   target inventory, source profiles and version bounds. Materialize an explicit witness route
   alongside the existing retrieval channels so a source-established endpoint can enter even when
   lexical or dense top-k misses it. Preserve all nominations and distinguish a target outside the
   selected inventory, unavailable target representation, no compatible candidate, conflicting
   witnesses and a ready selected edge. If the cue names a section containing several plausible
   definitions, retain the candidate set and its scope. Never select the first label match.
   Independent links remain useful when another unresolved link shares the same passage.
3. **Preserve the relationship and its direction.** Retain exact endpoint contribution and
   occurrence references, the relation kind and endpoint roles, evidence and premise references,
   source scope, work and effective version. Separate an explicit alias, declaration/use, citation,
   specialization, supersession, qualification and scope inheritance. Map an established edge into
   an existing selector relation only when its meaning fits. Several of these kinds fall outside the
   current contextual `RelationKind`. A versioned compatible extension should share selection and refusal
   mechanics where appropriate. Direct relationships already settled by a scoped producer can be
   served from that typed product without a second semantic decision. Reuse O02 host-bound
   attachments for condition inheritance across an explicitly governed list or procedure. Preserve
   the inherited premise and supporting scope, with ambiguous coordination retained as an
   alternative.

Extend the contextual policy and native/detached validators for any new witness channel or relation
vocabulary. Source work and version eligibility come from explicit evidence. Disagreement and
omitted coverage survive in the decision and its query projection. Expose witness and target
explanations through the current Reader/CLI/MCP and portable delivery routes. An old cut retains its
released candidate and decision identities. A changed witness contract regenerates against an
explicitly selected source and policy.

**Assessment.** Trace formula `Z`, the eligible standard-normal target and the unrelated red-ball
`X` separately through capture, eligibility, nomination and selection. Include a cross-view section
cue, an abbreviation reused with different local senses, a symbol with multiple scoped declarations,
a procedure-to-artifact link, and an unresolved external citation. Check exact endpoints, direction,
scope and interpretation against source judgments. A selection failure keeps its prior capture and
candidates visible. Broader retrieval or a language model can supply alternatives, while the
directed edge still depends on its source witness.

<a id="O05"></a>

## O05 · Extend artifact nomination and score one declared identity question

**Proposed.** Recover missing reference targets through O01 and O04, then improve same-lineage
scoring on a suitable cohort. Keep these independently deliverable. The GS120 reference assessment
froze 67 reference-to-caption pairs, including 13 supported pairs. Three supported pairs lacked
projected caption capture. On the inspected product, 25 external nominations overlap the existing
exact-code/lexical union and all 142 alias states are unknown. Discovery supplies titles for
captions only. Those judgments can show newly reachable references and false-link control. A
separate source-backed same-lineage frame with name evidence on both sides is needed to assess fuzzy
title or alias benefit. The current caption extractor already removes the leading designator.
Recheck all producers and exclude separate alias declarations from the comparison text where source
extents establish that boundary. [Artifact assessment](../design_review/evidence/2026-11-06_wce-completion-repair/artifact/README.md) · [Source reference frame](../design_review/evidence/2026-11-06_wce-completion-repair/source-references/README.md) · [Source extraction](../../python/corpus-structure/src/corpus_structure/methods/scoped_relations.py)

**Nomination and eligibility.** Keep physical occurrence identity, reference resolution,
maintained-artifact lineage and immutable revision identity distinct. Retain directed cross-work
citations for navigation even when they fall outside the same-lineage scoring frame. A same-lineage
hypothesis across a work or version boundary needs its own explicit premise and admission policy.
Keep all nomination routes, original relation roles and exact witnesses when normalizing candidate
pair order. Authenticate endpoints against their selected views and origin pins. An exact reference,
alias declaration or lineage statement can nominate across selected views without repeating code
equality. An ambiguous reference retains its alternatives without silently expanding the set of
established links.

Add a source-established numbering namespace, with unknown and unresolved states and references to
the evidence where available. A physical pointer identifies the occurrence. A numbering regime can
instead be per work, per chapter, or explicitly shared between editions. Use declared work/kind
constraints and established incompatibilities to delimit the scoring frame. An unknown namespace
yields unavailable scoped-code evidence. Treat known incompatible namespaces as disqualifying only
when the precise identity question and policy establish that incompatibility. Two overlapping views
of one physical occurrence remain one occurrence, with both citations available.

**Scoring policy.** Retain the fixed exact policy as a comparison control and version a multilevel
policy on the same exact eligible pair set. Use Splink 5 `CustomComparison` with ordered levels and explicit null
behavior.

| Comparison | Initial levels |
| --- | --- |
| Scoped code | Namespace or code unavailable, exact namespace-and-code agreement, comparable disagreement |
| Title and observed aliases | Exact normalized title, authenticated title-to-alias or alias-to-alias overlap, high fuzzy title, moderate fuzzy title, observed disagreement, or unavailable name evidence |

Implement the unavailable level ahead of ordinary scoring levels where its predicate is true. An
unknown alias list preserves an otherwise usable title comparison. When neither the title nor the
alias path is usable, the name comparison contributes neutral evidence. A witnessed known-empty list
remains distinct from an unknown one. Within the name comparison use `CustomLevel` for title-to-alias tests,
`ArrayIntersectLevel` for observed alias arrays and `JaroWinklerLevel` for prose titles. Use 0.95 and 0.85 as challenger bins with an
explanation of their behavior, especially common prefixes. Compare Damerau–Levenshtein for
transpositions and token overlap for reordered titles on relevant errors. Keep controlled-code
normalization and formula symbol identity separate. A single name comparison prevents several
encodings of one title from entering as independent confirmations. If authentic multivalued alias
coverage grows, assess `PairwiseStringDistanceFunctionAtThresholds` on observed alternatives. [Splink guide, comparisons and advanced compound levels](../libraries/scientific_compute/Splink.md) · [Comparison-level API](https://moj-analytical-services.github.io/splink/api_docs/comparison_level_library.html)

Add term-frequency adjustment first to exact normalized title agreement using a prepared input
column and a declared frequency population. Retain the TF lookup identity with the model instance so
incremental or matched assessments use the same population. Keep prior, comparison-level `m` and
`u`, and supported/unsupported/unknown judgment provenance distinct. `estimate_m_from_pairwise_labels` assumes every row is
positive and ignores `clerical_match_score`. Use independently supported same-lineage labels alone for it. Estimate
nonmatch behavior over an eligible, justified frame. `estimate_u_using_random_sampling` is appropriate only where randomly sampled
pairs are predominantly nonmatches and sampling represents the intended universe. With sparse levels
retain provisional parameters and report their effect. Consider complementary EM training blocks
only if there is enough variation to identify the affected levels. Maintain comparable matched-pair
evaluations, separate from newly reachable nominations. [Training API](https://moj-analytical-services.github.io/splink/api_docs/training.html) · [Term-frequency guidance](https://moj-analytical-services.github.io/splink/topic_guides/comparisons/term-frequency.html)

The Python adapter already registers the exact allowed set with `register_blocked_pairs_for_predict`, verifies returned membership,
retains comparison outputs and uses native alias array blocking. Retain that boundary. `inference.score_pairs` evaluates
a Cartesian product of its two inputs. Crucially, `ops.validate_artifact_identity` reconstructs the current code/title levels and
probability and expects exactly four evidence fields. A changed Python comparison model alone would
fail native admission. Define one versioned comparison specification and update the native owner,
Python result contract and detached replay together. Authenticate comparison levels, weights, TF
inputs and pair membership. Reuse native operations where semantics match, and compare DuckDB and
native reconstruction on threshold, Unicode, null and invalid-value boundaries. If exact parity for
a proposed distance or TF term cannot be established within the existing authority boundary, keep it
as an assessment challenger pending a deliberate validation design. Keep excluded pairs unscored and
provider failure distinct from an empty selection. [Current scorer](../../python/corpus-structure/src/corpus_structure/semantic/artifact_identity.py) · [Native validator](../../python/corpus-structure/src/corpus_structure/semantic/sql/structural_products.sql) · [Splink inference](https://moj-analytical-services.github.io/splink/api_docs/inference.html)

**Assessment.** Recover the three known captions and count newly represented, nominated and
supported reference pairs separately. Include same-code collisions across chapters, a cross-view
reference with an observed alias, a true revision and a directed external citation that remains
outside the scored frame. Compare exact and multilevel scorers on frozen eligible same-lineage
pairs, with authenticated name evidence and independent judgments. Inspect changed ranks, false
links, unknown evidence and individual level/weight explanations. A missing suitable cohort leaves
the scorer comparison unavailable and does not delay source and navigation improvements.

<a id="O08"></a>

## O08 · Bind comparisons to their roots and expose scoped gaps and neighborhoods

**Proposed.** Let a reader inspect a concept or clause through witnessed uses, qualifications,
comparisons, revisions and dependencies. Keep the original passages and applicable conditions
visible. Native rooted dossiers already qualify members through a direct scoped target or exact
applicability reading. In the normal-density repair, two members qualified and an unrelated
supported component was excluded. That establishes membership and delivery in the recorded frame. It
leaves open which additional relationships deserve membership and whether a display optimizer could
improve a budget-limited representation. [Rooted dossier repair](../design_review/evidence/2026-11-06_wce-completion-repair/records/wce.repair-rooted-dossier.json)

**Comparison bindings and dependencies.** Add a retained binding between an exact comparison side
and an exact component or clause, with the qualifying relationship decision, premise references,
original citation and selected predecessor identity. Reuse the existing comparison side/reading and
retained reference contracts. Admit comparison-side roles such as exception, revision, variant and
conflict only when the exact root, kind and scope are supported. The other side remains visible as
comparison context. It can qualify independently if it has its own binding. Preserve applicability
under conjunction, alternatives and repeated fields from O02/O03. Semantic `depends_on` can enter the rooted
view through a compatible witnessed relation. Keep producer and file dependencies separate in the
execution record. Shared terms, similarity or an unqualified comparison are insufficient for
membership.

The method currently skips comparison reports for a supplied root because comparison sides lack a
definition-sense endpoint. Add binding checks to that membership path and the native `ops.structural_dossier` producer,
including equality of the exact selected predecessor, source and root premises. Where the dossier
uses contribution-derived assembly, apply the same authority boundary there. Include bindings in
member/facet identities and continuation checks when they affect membership. Extend the current
Reader, CLI and MCP routes and the detached bundle verification that reconstructs the membership.
Preserve the split between complete membership and bounded display. Keep the supported-facet greedy
projection until interacting display constraints are demonstrated on identical membership. A SciPy
`milp` challenger should then specify the constraints and compare useful facet coverage and
preservation of required qualifiers under the same budget. [Membership code](../../python/corpus-structure/src/corpus_structure/methods/structural_products.py) · [Native owner](../../python/corpus-structure/src/corpus_structure/semantic/sql/structural_products.sql) · [Portable verifier](../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py)

**Similarity and concept family browsing.** Keep exact authenticated meaning groups. Produce a
separate bounded projection with a typed witnessed lane for related, broader, narrower, alternative
or differently scoped readings, and an exploratory lane for semantic similarity. Preserve
representative identity, provenance of each original member, pinned profile, representation digests
and distance. Define the browse unit explicitly. For an initial sense-group view use a deterministic
selected representative per exact meaning group and preserve the member provenance. Compare the
existing exact pgvector ranking over the selected inventory with scikit-learn `NearestNeighbors(metric="cosine", algorithm="brute")`. The database
route reuses the resident vectors and source membership checks. The scikit-learn route is a suitable
offline challenger or a consumer of already-resident vectors. For mutual top-five, exclude self, cap
at the available peer count, settle equal-distance ties by stable identity across the cutoff, retain
both directed ranks and preserve zero-distance distinct embeddings. Treat absent or invalid profile
vectors as coverage limits or failure of the declared operation. Display distance and rank rather
than a universal cutoff. Connected components of the similarity projection are exploratory
neighborhoods. [Exact ranking](../../python/corpus-structure/src/corpus_structure/semantic/contextual_retrieval.py) · [NearestNeighbors](https://scikit-learn.org/1.9/modules/generated/sklearn.neighbors.NearestNeighbors.html)

**Gap reports.** Serve three read-only views over existing products and the new bindings. Every row
identifies the selected cut, inspected scope and relevant operation outcome. An operation that
failed, was skipped or lacked inputs yields unavailable coverage. A completed inspection with no
qualifying edge yields a scoped negative result about that inspection.

| Report | Content |
| --- | --- |
| Unresolved binding | Retained use/reference, exact cue, nominated targets and exclusions, reason distinguishing no eligible target, ambiguous targets and insufficient evidence |
| Unknown applicability premise | A required sense, scope, version, convention or parameter premise, observed evidence and why it is unresolved |
| Unconnected supported comparison | Independently assessed comparison and sides, authorized support reference, absent binding or unavailable binding operation |

Use indexed typed joins and stable pagination in the existing Reader/CLI/MCP surface. Expose only
the authorized grade or support summary for the third report. Preserve the protected evaluation
boundary. Extend detached exports when a gap report is part of the ordinary portable review
workflow, with the inspected selection, results and evidence limits intact. Avoid a separate
completeness engine. “No selected declaration link in the inspected selection” is the supported
conclusion.

**Assessment.** Exercise a comparison whose left side is bound to the root and whose right side
carries only context, a legitimately dual-bound comparison, a scope-incompatible comparison, an
explicit dependency and an unrelated high-similarity component. Check native, Reader, CLI, MCP and
detached membership against exact references and continuations. Check one actionable row per gap
report, plus empty, failed and unrun coverage. Validate same-membership display independently from
link discovery and representation.

<a id="O11"></a>

## O11 · Explain candidate routes and trace broken relationship chains

**Proposed.** Add an operator view that can answer why a concrete opportunity is stranded and which
producer or selection to inspect. The current corpus already has recorded examples of a missing
projected endpoint, a represented occurrence without a compatible target, and scored candidates
without selection. An integrated view can follow exact opportunity or occurrence identities across
these stages while preserving independent denominators. It can also identify a weak bridge between
otherwise distinct neighborhoods for manual review. Both activities have clearer consumers than a
general analytics graph.

- **Explain reachability and scoring.** For one frozen selection, surface source opportunity,
  endpoint representation, producer/cut provenance, nomination route memberships and which routes
  contributed marginal candidates, eligibility and refusal reason, comparison levels and match
  weights, and final relationship state. Reuse the existing artifact pilot provider evaluation and
  retained provenance. Splink `count_comparisons_from_blocking_rules(record_sample_proportion=1.0)` and `n_largest_blocks` support rule diagnostics. `match_key` alone identifies the first
  match, so retain the application’s all-route memberships. Consider selective namespace/kind
  SQL/equijoins and native alias blocks instead of checking every Python pair, while preserving
  exact population parity and source-supported recall. Extend the current `prediction_errors_from_labels_table` pilot usage into the
  protected pair review journey. Apply explicit unknown/unassessed and exposure handling, and
  inspect equality at thresholds. [Artifact pilot](../../python/corpus-structure/src/corpus_structure/evaluate/artifact_pilot.py) · [Blocking analysis](https://moj-analytical-services.github.io/splink/api_docs/blocking_analysis.html) · [Evaluation](https://moj-analytical-services.github.io/splink/api_docs/evaluation.html)
- **Navigate additional types of stranded evidence.** Extend the O08 projection for unlinked
  procedure inputs, unattached exceptions, eligible use with no selected definition, and a
  dependency path blocked at a specific endpoint. Scope each question to eligible source
  opportunities and independently witnessed edges. Use typed SQL joins for known paths. Use NetworkX
  `MultiDiGraph` if a bounded multi-hop consumer justifies a graph projection. Carry scope, edge identity,
  relation and original evidence through `ancestors`, `descendants` or bounded traversal. SCCs and cycle views can
  expose contradictions in a declared precedence projection. Analyze `bridges` only on an explicitly
  undirected review projection that preserves the mapping back to the directed relationships and
  multiplicity. Community, centrality and link-prediction outputs can prioritize inspection if a
  concrete workflow emerges. They carry exploratory standing. [NetworkX guide](../libraries/scientific_compute/networkx.md) · [DAG algorithms](https://networkx.org/documentation/stable/reference/algorithms/dag.html) · [Bridges](https://networkx.org/documentation/stable/reference/algorithms/bridges.html)
- **Offer a bounded retrieval challenger.** Compare RapidFuzz `extract_iter` or `cpdist` over scoped strings and
  word/character `TfidfVectorizer` with the present PostgreSQL lexical route for a demonstrated spelling or OCR
  failure. Use `editops` or `opcodes` when the operator benefits from seeing the textual difference. Keep
  derived normalized text and source strings distinct. Measure reached eligible targets and false
  nominations using frozen opportunities and keep witness requirements unchanged. Reuse a sparse `kneighbors_graph`
  or `KNeighborsTransformer` if more than one consumer needs the same neighborhood. Radius or OPTICS/HDBSCAN exploration
  can be revisited when mutual ranks produce a demonstrably poor browse experience. [RapidFuzz guide](../libraries/parsing/rapidfuzz.md) · [RapidFuzz process](https://rapidfuzz.github.io/RapidFuzz/Usage/process.html) · [scikit-learn feature extraction](https://scikit-learn.org/stable/modules/feature_extraction.html)
  · [Neighbors](https://scikit-learn.org/stable/modules/neighbors.html)

For an initial journey, start with a source-authored reference whose caption was omitted and a
second occurrence whose compatible target was nominated but remains unsupported. A Reader query
should distinguish their failing layers and expose the exact evidence and operation outcomes. A
typed dependency example should show the missing endpoint without suggesting that an unrelated
parallel edge repairs the chain. Reuse the same selections for comparisons between releases and
policy arms, with matching projection and input identities or an explicit account of what changed.
Build this on O04/O05/O08 and the existing assessment products. Chunked prediction, cached frequency
lookups across batches, export materialization and graph backend changes become candidates when an
actual consumer needs the additional scale or repeatability.

### Learn only from features and populations that answer the operation question

Use scikit-learn's `Pipeline` and the existing typed parameter artifact as the baseline in
[O07](#O07). Keep alternative features attributable. A `ColumnTransformer` with named output
columns can help when the four-feature baseline leaves a concrete error tied to categorical
layout, cue families or missing measurements. Add those features in separate arms and use
grouped ablations. Consider a shallow tree or histogram boosting only for a residual interaction
with sufficient independently judged cases. Use `GroupKFold` or `StratifiedGroupKFold` when a
separately scoped assessment question and the number of genuine source groups support it.
Fit preprocessing inside each fold, preserve exact exposure and event memberships, and compare
precision–recall and coverage versus selective error. Same-corpus development needs no new
held-out prerequisite. Reliability curves and `CalibrationDisplay` can expose score behavior
when the cohort is adequate. Assess `CalibratedClassifierCV` or a frozen estimator with a
separately justified calibration set before considering sigmoid, isotonic or temperature
calibration. Tune a decision threshold only for a stated consumer decision and use separate
data for its assessment. Brier score and log loss alone combine several effects. [Scikit-learn guide](../libraries/scientific_compute/Scikit-learn.md) ·
[Grouped validation](https://scikit-learn.org/stable/modules/cross_validation.html) ·
[Calibration](https://scikit-learn.org/stable/modules/calibration.html) ·
[Threshold selection](https://scikit-learn.org/stable/modules/classification_threshold.html)

For browsing, consider Neighborhood Components Analysis only when independently judged
relevance exposes a limitation in the pinned embedding geometry. Use `trustworthiness` only
for a lower-dimensional display with an actual reader, and density or outlier scores as
inspection priorities with their feature and population scopes visible. Semi-supervised
labels, broader model families, custom estimator machinery, experimental fit callbacks,
alternate persistence and accelerators need a separate modeling or operational purpose.
Preserve the existing typed result and parameter contracts. A trained ranking or exploratory
cluster has a separate standing from a witnessed relationship. [Scikit-learn capability addendum](../libraries/scientific_compute/Scikit-learn.md)

<a id="O06"></a>

## O06 · Joint interpretation of a specific shared uncertainty

**Proposed. Recommend the shared-correspondence model for a bounded, source-grounded comparison.
Keep learned weights and an additional inference backend conditional.**

The current table producer constructs exact finite requests through `_request`. Its independent arm
distributes a common evidence weight across the supported choices. Its coupled arm awards that
weight once when all linked choices use supported readings. Both are authored scoring models. The
recorded comparison on Table 5.2 used the schematic Table 5.3 and located explanatory prose,
retained nine source-supported roles and five competing ordinary-count readings, and found all nine
supported roles in the top assignment of both weighted arms at all three assessed scales. These data
establish a useful matched control and the value of source weighting on those cases. A changed
marginal, such as 0.414214 to 0.400000 for the column marginal `32`, supplies no additional selection
benefit there. Table 6.1's existing exact header paths are useful controls for known correspondence.
[Table producer](../../python/corpus-structure/src/corpus_structure/methods/table_interpretation.py) · [Native and detached assessments](../design_review/evidence/2026-11-06_wce-completion-repair/table/README.md)

Represent the shared question as an auxiliary decision `M` whose alternatives name the specific
source-bound correspondence between schematic and observed cells, with an unresolved alternative
when available evidence leaves it open. Retain each existing cell role decision `R_j` and its own
unresolved state. Score the correspondence evidence once with a unary factor on `M`. Add a local
compatibility factor on `(M, R_j)` for each cell, identifying its distinct local evidence and the
correspondence it consumes. Apply hard masks only to source-established impossibilities, such as
incompatible row/column extents. Preserve separately co-applicable notes, units, and nested roles.
Emit a located established correspondence directly when the source already decides it. A synthetic
alternate correspondence can test arithmetic and data flow. A source-supported ambiguity is needed
to assess whether the new model improves interpretation. [Current interpretation contract](../../python/corpus-structure/src/corpus_structure/semantic/record_interpretation.py) · [Marginal-role reference](../design_review/evidence/2026-11-06_wce-completion-repair/source-references/marginal-role-reference.json)

Compare four meaningful controls: feasible support, independent weighting, existing authored
coupling, and the explicit shared variable. Where an arm does not consume `M`, use a neutral common
domain or compare after marginalizing `M` and explicitly report the extra candidate dimension. Hold
the role candidates, source selection, requested role events and source-established exclusions
constant. Measure candidate expansion separately. Use a case where the correspondence is ambiguous,
a cell has no supported local reading, and a witnessed local exception overrides the default
correspondence. A good reading may keep the correspondence and several cell roles while leaving the
exception cell unresolved. For later linguistic uses, require similarly specific shared
uncertainties, such as whether a particular scoped declaration governs several clause attachments.
Model consumers should still receive the independently useful components and authenticated source
premises when a joint result is unresolved or unavailable. [Existing numerical realization](../target-pipeline-design/mathematics.md#factorized-and-optimized-alternatives)

Keep model formulation in the operation that interprets the source. Version the new table policy and
bind it to its candidate/anchor inventory, source geometry and schematic correspondence, scope,
factor axes and values, masks, event definitions, and evaluator and executor identities. Retain that
request and its result through the existing contribution operation and preserve exact Reader, CLI,
MCP and detached-export behavior. Regenerate affected interpretation and dependent dossiers under an
explicitly selected release and preserve immutable prior evidence. The native contribution guard
currently authenticates the input and request/result digests, declared table mode/scale, shape, and
selected premises. The WCE plan already owns exact reconstruction from source geometry under
WCE-R18. Carry that obligation forward explicitly. Establish one versioned authoritative derivation
from authenticated source inputs and compare canonical reconstruction of the request before treating
a native result as source-conditioned. Avoid relying on producer-authored factor digests alone.
Demonstrate that a changed factor value or mask with a recomputed digest fails this check, and that
exact replay preserves the original result. [Native admission](../../python/corpus-structure/src/corpus_structure/semantic/sql/source_contributions.sql) · [WCE repair disposition](../plans/witnessed-corpus-enrichment_2026-11-05.md#repair-disposition--2026-11-07)

For learning, fit a small conditional log-linear model only after there are independently judged
cases with meaningful differences in correspondence and role compatibility. For a case with retained
assignments `C_i` and compatible assignments `A_i`, minimize the difference between the log partition
over `C_i` and the log partition over `A_i`, plus ridge regularization. Partial judgments marginalize
unspecified choices. Empty `A_i` exposes missing candidate support or incompatible masks and receives
a separate diagnostic. `A_i = C_i` supplies no discriminating likelihood. Start with separate correspondence
and compatibility weights, using the exact retained sums and the analytic gradient given by the
difference between the two feature expectations plus the ridge gradient. Compare fixed weights
before fitting. The existing nine judgments within the same related tables support a matched
assessment, while their ability to identify several shared weights remains unestablished. Separate
the fit from the operation's authority to select or publish knowledge. [SciPy optimization](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html) · [SciPy logsumexp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.logsumexp.html)

<a id="O07"></a>

## O07 · Fit an emitted attachment event and expose useful uncertainty

**Proposed. Recommend the exact event contract and development baseline. Consider a Bayesian
challenger after the frame exists, and partial pooling after the data identify a meaningful group
effect.**

The availability census counted 82 `definition.defining_text_attachment` relations in the declared completed cuts, zero eligible `relation.defined_by`
rows, and zero matching protected evaluations. The 82 rows identify a population to inspect. They
are private candidates constructed from returned group roles and carry no independent relation-head
score. Independent grades and production scoring authority require their own evidence. Define a new
event asking whether the exact emitted term-to-content attachment is supported in the scope it
claims. Retain separate source judgments for term role, content role, relation direction/attachment
and scope, with omitted content and missing candidates assessed separately. The negative embedded
content of a valid definition, an attachment to a section reference, and correct endpoints with an
incompatible scope are distinct cases. Refusing an attachment should preserve each independently
valid component. [Fitting census](../design_review/evidence/2026-11-06_wce-gs120/assessment/operation-fit-availability/README.md)

Extend the existing event route end to end. The protected output-first rubric freezes exact emitted
contribution and head/tail anchors under the actual cut and producer, binds authentic source
premises, and grades supported, unsupported, ambiguous and unassessed outcomes. Positive
alternatives require exact endpoint roles and scoped witness. Distinguish a contribution identity
from its source origin, so reused tasks and repeated policy arms do not inflate the independent
population. Carry event identity, version and feature order through availability, protected frame
construction, fit admission, parameter applicability and the existing `ci eval operation-event-availability`, `operation-event-fit` and `operation-event-read` routes. Keep
the meaning of `defined_by_correctness` distinct in the event contract and preserve prior fit evidence under its original
custody. Keep protected judgments and authored references in evaluator/fitter custody, with ordinary
consumers receiving only authorized diagnostics or explicit finite parameters. Reuse the project's
applicable environment and exact release binding. [Fitter](../../python/corpus-structure/src/corpus_structure/evaluate/operation_fitting.py) · [Runtime parameter contract](../../python/corpus-structure/src/corpus_structure/semantic/operation_policy.py) · [Native event contract](../../python/corpus-structure/src/corpus_structure/semantic/sql/operation_event_fitting.sql) · [CLI](../../python/corpus-structure/src/corpus_structure/cli/eval.py)

The first feature arm uses `log1p` of the exact term and defining-content character lengths, signed
term-to-content separation divided by the length of the frozen inspected passage, and a binary cue
from a versioned list such as “is defined as,” “is called,” “we call,” and “denoted by.” The feature
contract should specify half-open coordinates, deduplication of overlapping extents, how direction
and overlap map to signed gap, and which exact passage contains both roles. Use the union length for
genuine multi-fragment roles. Define overlap as zero separation, use positive distance for content
after the term and negative distance for content before it, and record the feature arm as
unavailable when no exact common passage can support that measurement. Count such exclusions
independently so the resulting model's applicability is clear. Normalize and tokenize the cue within
the exact inspected context using one versioned recipe. Feature reconstruction must consume
authenticated source anchors and frozen source context, with independence from the grade and
reference-overlap data. Share the feature semantics between fitting and scoring, and verify parity
when the authorized runtime scorer eventually consumes the event. A known antecedent and fragment
case should reproduce features identically from protected frame and ordinary source inputs.

Compare the existing class-prior baseline with `StandardScaler → LogisticRegression` using `C=1`, `lbfgs`, tolerance `1e-6`, up to 2,000
iterations and unit weights. Count all judgment states, keep ambiguous and unassessed examples
outside the binary likelihood, and preserve the current prior-only or unavailable outcome when a
class is missing. Record convergence, coefficient and scaling diagnostics, Brier score and log loss
on the same labeled rows, and the underlying role/scope error counts. For source-grouped diagnostics
where enough independent origins exist, fit the scaler inside each training split and keep any
separately protected assessment outside tuning. Same-corpus development can proceed when the genuine
event frame and classes exist. Calibration, transfer, and performance on new sources require
separate evidence. Preserve structural outputs when fitting is unavailable or inconclusive. [Current model implementation](../../python/corpus-structure/src/corpus_structure/evaluate/operation_fitting.py) ·
[scikit-learn calibration guide](https://scikit-learn.org/stable/modules/calibration.html)

For the Bayesian challenger, use `Bernoulli(logits=...)` with the same labeled observations and frozen standardized
features, zero-centered normal priors with standard deviation 1.5 for the intercept and 1 for each
coefficient, and narrower/wider coefficient-prior sensitivity. A `pyro.plate` over rows is valid only for the
modeled conditional independence. Keep grouping, repeated observations, and unknown labels explicit.
Begin with prior predictive checks and an uncompiled model with validation enabled, trace/site shape
inspection, and NUTS with four chains, 1,000 warm-up steps and 1,000 retained draws as a starting
trial. Record seeds, chain/draw identities, divergence, ESS and split R-hat, then inspect predictive
behavior and sensitivity. Pyro's tagged diagnostics use classical split Gelman–Rubin. Its MCMC API
defaults to disabled validation and can execute multiple chains sequentially. Verify the 1.9.2
version against the selected Python/Torch environment and managed cancellation, including
child-chain cleanup. Compare a cheap Laplace approximation if interval fidelity and compute burden
matter for routine use. [Tagged Pyro MCMC](https://github.com/pyro-ppl/pyro/blob/1.9.2/pyro/infer/mcmc/api.py) · [Tagged diagnostics](https://github.com/pyro-ppl/pyro/blob/1.9.2/pyro/infer/mcmc/util.py) · [Automatic guides](https://docs.pyro.ai/en/stable/infer.autoguide.html)

Publish diagnostic posterior means and credible intervals of event probability through a separate
algorithm/result contract. Compute the logistic probability on each draw before averaging, and use
posterior predictive binary draws for a separately declared predictive check. Bind the draws or
validated summaries to the event, feature scaler, priors, inference configuration, frame and
release. Keep numerical/sampling failure separate from insufficient event evidence. A posterior mean
coefficient vector generally gives a different score from a posterior mean probability. A production
decision rule consuming the posterior requires explicit scope, consumer need and evaluation. Once
there are genuinely replicated contexts with shared residual errors, compare complete pooling,
separate effects and partial pooling. `LocScaleReparam` or an explicit non-centered parameterization can improve
the geometry of a supported random-effect model. Hierarchy over policy runs of the same source would
overstate replication. Jointly estimating uncertain factor weights remains a separate extension with
a normalized conditional likelihood over the retained candidate set. [Hierarchical binary trials](https://pyro.ai/examples/baseball.html) · [Pyro capability guide](../libraries/scientific_compute/pyro-ppl.md)

<a id="O12"></a>

## O12 · Numerical alternatives matched to actual consumers

**Proposed. Recommend the existing SciPy-backed exact and statistical routes where their contracts
fit. Defer additional inference runtimes, approximate routes and display optimization until a
specific question justifies them.**

### Exact inference beyond the current guard

The current interpreter can answer complete candidate-relative requests using the existing
NumPy/SciPy enumeration. It reports a resource limit past 65,536 retained joint states by default.
Its graph components are diagnostic in that contract. Where a useful workload exceeds the guard,
first compare direct conditioning on a small separator with structured elimination. A star of
conditional cell-role factors can sum each cell's allowed states for a fixed correspondence, sum
across correspondence states for the partition, and obtain cell marginals by mixing those local
distributions. Cross-cell masks or event definitions can change the factorization. If separating
disconnected pieces, show how cross-component Boolean events, coherent alternatives and the log
partition compose before changing the supported request contract. Keep the exact small oracle and
compare requests with the same inputs and answers. [Interpreter](../../python/corpus-structure/src/corpus_structure/semantic/record_interpretation.py) · [Numerical design](../target-pipeline-design/mathematics.md)

For a useful sparse model, compare pgmpy 1.1.2's `DiscreteMarkovNetwork` plus `DiscreteFactor`, classic `VariableElimination` and greedy tensor
contraction, junction-tree `BeliefPropagation` for repeated related queries, and `BeliefPropagationWithMessagePassing` for genuinely loop-free factor
graphs. Record weighted intermediate scope cardinalities and required outputs alongside `induced_graph` and `induced_width`.
Classic named elimination-order heuristics such as `WeightedMinFill` are dispatched for discrete Bayesian
networks. An undirected route needs an explicit order or an inspected contraction path.
Markov-network query factors can be unnormalized and `get_partition_function()` multiplies the full joint before summing.
Preserve the scale for a log partition, hard zeros and zero support, and qualify an explicit
normalization strategy against extreme log weights. Validate repeated equal-valued factor
multiplicity and state-name order. The classic path uses sets of factor/origin pairs and requires
special care for eliminated scalar terms. Junction-tree preprocessing and factor graph conversion
must preserve the same factors. [Tagged exact inference](https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/inference/ExactInference.py) · [Tagged Markov model](https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/models/DiscreteMarkovNetwork.py)

A viable backend must support disjoint evaluation of overlapping derivations or a factorized event
indicator, consistent coherent alternatives with deterministic ties, and the current applicable
log-partition and failure semantics. Distinguish verified infeasibility from numerical underflow,
and return no computed answer on cancellation or resource exhaustion. Show how the backend is
bounded or isolated if the underlying kernel lacks cooperative interruption. Preserve unresolved
states, provenance, output probability standing and unknown omitted-candidate mass. A large
full-joint query recreates the original output problem. A MAP call returns an assignment for a
particular optimization query. For an independently justified assignment-only output, compare
pgmpy's `Mplp` and integrality-gap/tightening controls with feasible best-assignment alternatives.
Retain a separate meaning and result type for that output. [MPLP](https://pgmpy.org/api/generated/inference/pgmpy.inference.Mplp.html) · [pgmpy guide and advanced addendum](../libraries/scientific_compute/pgmpy.md)

Use `check_model`, `Independencies.closure/entails`, graphical separation and tiny `JointProbabilityDistribution.check_independence/is_imap` checks where they answer an explicit model-review
question. The outputs concern an attributed model, and statistical independence and corpus facts
require their own evidence. Synthetic known-truth cases, including simulated missingness with a
declared mechanism, can isolate numerical or assessment behavior. `MirrorDescentEstimator` is a candidate if a future
workflow needs to fit an undirected model to comparable empirical marginals. The partial-label
correspondence fit has a different conditional likelihood. Directed CPD estimation and prediction
require a suitable directed generative model. Tagged `DiscreteEM` excludes rows with partially missing
observed variables and cannot simply absorb unknown or unassessed events.
Bayesian/functional/linear-Gaussian models, structure scores, discovery, CI testing, latent causal
graphs, causal estimators and interventions, dynamic models, sampling and interchange each need a
distinct question. Retain ordinary typed relationship graphs for corpus navigation. [Joint distribution API](https://pgmpy.org/api/generated/factors/pgmpy.factors.discrete.JointProbabilityDistribution.html) · [Mirror descent API](https://pgmpy.org/api/generated/parameter_estimation/pgmpy.estimators.MirrorDescentEstimator.html) · [Tagged EM](https://github.com/pgmpy/pgmpy/blob/v1.1.2/pgmpy/parameter_estimator/discrete_em.py)

### Scientific kernels for fitting, comparison and inspection

- Use the installed SciPy 1.18.1 `logsumexp`, `expit` or `log_expit` for stable finite likelihoods and scores. Keep
  bounded exact enumeration and use `minimize(method="L-BFGS-B")` with an explicit analytic gradient for the small conditional
  model. Compare against a finite-difference derivative on a tiny fixture, including hard masks,
  shift invariance and a separately computed gradient. Inspect identifiability before tightening
  optimizer tolerances. A low-dimensional Laplace or quadrature comparison can help assess Bayesian
  intervals without a second production inference runtime. Use `scipy.linalg` factorizations and `scipy.integrate` or `scipy.stats.qmc`
  only when a named low-dimensional approximation needs them. [SciPy guide §§3, 5–6, 8, 12](../libraries/scientific_compute/scipy.md) · [Special functions](https://docs.scipy.org/doc/scipy/reference/special.html)
- Use grouped paired resampling or permutation only when the assessment design supports the
  resampling unit and exchangeability. Small or purposively selected corpora may be better served by
  transparent paired counts and exact disagreements. For a typed navigation projection with a large
  sparse frontier, assess `scipy.sparse` and `csgraph` only on a declared directed and weighted projection with
  explicit relation identity and scope. Compare retained SQL or NetworkX for bounded routes and
  scikit-learn for cosine search. A sparse matrix projection cannot recover evidence discarded by
  its construction. Spatial indexes and pairwise distances can accelerate exact located geometry
  lookup if a genuine hot path appears. [SciPy guide §§4, 8, 10](../libraries/scientific_compute/scipy.md) · [Sparse graph kernels](https://docs.scipy.org/doc/scipy/reference/sparse.csgraph.html)
- Keep dossier membership tied to supported source relationships. Revisit `scipy.optimize.milp` only when eligible
  facets compete under interacting display constraints such as a budget plus inseparable qualifiers.
  Define feasible and unavailable results, deterministic tie handling, and evidence completeness
  before comparison with the current facet selector. `linear_sum_assignment` can compare true one-to-one occurrence
  correspondences with admissible unmatched choices. Many-to-many linkage or shared qualifiers
  require different semantics. Continuous LP, global optimization, nonlinear least squares and root
  finding, general interpolation/ODEs, signal/image kernels, specialized distributions and
  scientific interchange have no demonstrated need in this increment. Array API, compiled callbacks
  and GPU/offloading need an identified physical bottleneck before changing the existing runtime.
  [SciPy guide §§3, 6–13](../libraries/scientific_compute/scipy.md) · [MILP](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html) · [Linear assignment](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html)

### Probabilistic extensions with distinct uses

Pyro's `factor` and discrete enumeration with `TraceEnum_ELBO` or `infer_discrete` are candidates for a later mixed model with
uncertain weights and finite candidate decisions. Specify the parameter-dependent normalizer in the
conditional likelihood and verify marginal, assignment and event semantics separately. `infer_discrete` offers
posterior samples or a MAP mode. Neither output alone fulfills the exact event-union and top-k
contract. Prefer summing the tiny finite conditional model within each sampled weight draw before
adopting symbolic Funsor contraction. The optional Funsor extra pins 0.4.8 in Pyro 1.9.2. Use trace,
seed, conditioning and replay to inspect the model and repeat predictive checks. For SVI, isolate
parameter state and compare `AutoLaplaceApproximation`, `AutoMultivariateNormal` or low-rank/structured guides with NUTS on the declared
intervals. Posterior geometry, approximation quality and operational simplicity determine whether
more advanced guides, reparameterizers, streaming, importance reweighting or acceleration add value.
[Pyro inference API](https://docs.pyro.ai/en/stable/inference_algos.html) · [Tagged package requirements](https://github.com/pyro-ppl/pyro/blob/1.9.2/pyproject.toml)

If protected judgments become scarce and the attachment model already supports useful diagnostic
predictions, compare expected information gain with stratified or disagreement-based case selection
in a separate discovery workflow. Pyro's `contrib.oed` can estimate how much a possible adjudication would
inform a named parameter or uncertain operation. Preserve an independent protected assessment
population. Adaptive acquisition changes what is observed, so it cannot silently become a population
estimate. Unknown grades should stay outside the observed binary likelihood. Pyro's `obs_mask` introduces
latent imputations and requires an explicit missingness model and estimand. Equality-conditioned
sites retain different density terms from value sharing under `equalize`. An explicit shared variable is
clearer for the initial correspondence. Temporal filters, Gaussian/state-space models, nonlinear
Gaussian processes, deep/neural guides, causal effects and intervention handlers, particle methods
and other contributed frameworks require a specific new temporal, causal, simulation or scale
problem. [Optimal experimental design](https://docs.pyro.ai/en/stable/contrib.oed.html) · [Pyro capability guide §§2–12](../libraries/scientific_compute/pyro-ppl.md)

## Source recommendation crosswalk

The source locations use headings from the input digest recorded above. The later pass
begins at line 475.
“Develop” identifies a recommended implementation direction. “Conditional” includes the
entry condition for undertaking the implementation. “Correct” replaces a premise or
mechanism while preserving its viable functional intent.

The review adds [source-aligned candidate recovery](#O10),
[operator diagnosis and navigation](#O11), and [numerical alternatives](#O12) to the
source recommendations.

| Source location | Recommendation and disposition |
|---|---|
| First pass §2 O01, later §2 | **Develop** the three exact caption projections and normal artifact consumption in [O01](#O01). **Conditional** fragment and graphical-label access at authenticated precision. **Correct** broad raw-output recovery to independently valid exact components and a field-specific investigation in [O09](#O09) and [O10](#O10). |
| First pass §2 O02, later §3 condition-model paragraph | **Develop** witnessed condition, assumption, parameterization, exception, attribution, modality and order/dependency attachments in [O02](#O02). **Correct** the proposed representation to reuse the released condition and qualification model. Keep unsupported lowering visible. |
| First pass §3 A, later §3 A–C | **Develop** nominal complements, exact extent sets, grammatical variants, host-owned conditions and scoped polarity in [O03](#O03). Preserve local scope, reported speech and legitimate embedded negation. |
| First pass §3 B, later §3 D | **Develop** neutral predicate frames with provenance for inherited roles, followed by behavior interpretation from source context and optional model evidence in [O03](#O03) and [O09](#O09). |
| First pass §3 C, later §3 E | **Develop** multi-member typed comparison and bounded Lark parsing in [O03](#O03). Preserve explicit grouping and individual anchors. Compare changed responsibility, requirement strength, conditions and exceptions. |
| First pass §4, later §4 | **Develop** descriptive labels and two-axis focused classification in [O09](#O09). **Correct** the suggested schema infrastructure expansion since transport and optional/repeated records already exist. **Conditional** constrained record assignment, targeted Decide and matched JointIE after candidate repair. |
| First pass §5 O04, later §5 A | **Develop** exact witnessed section, definition, declaration/use, naming, specialization, supersession, artifact and qualifying inheritance links in [O04](#O04). Preserve unresolved targets and isolate scoped references from identity. |
| First pass §5 O05 nomination, later §5 A | **Develop** additional authenticated cross-view and alias routes and explicit numbering scope in [O05](#O05). Separate physical occurrence, lineage, revision and citation. **Correct** the change to extend the current exact-pair route rather than introducing new pair custody. |
| First pass §5 O05 comparison, later §5 B–C | **Develop** scoped-code and compound title/alias levels, first Jaro–Winkler bins, missingness, informative frequencies and explanations in [O05](#O05). **Conditional** authentic alias scoring and estimation on populations judged for the actual event. Supply only positives to the positive-pair estimator. |
| First pass §6 O06, later §8 | **Develop** the shared correspondence question on the existing interpreter in [O06](#O06). **Correct** the inference that an authored joint bonus models dependence. **Conditional** partial-label learned weights, analogous linguistic factors and pgmpy behind the same semantic contract. |
| First pass §7 O07, later §7 | **Develop** the emitted group-derived attachment event and baseline fit in [O07](#O07) once compatible binary judgments exist. **Correct** the event mismatch. **Conditional** Bayesian logistic after the point baseline and hierarchy after replicated residual groups are established. Keep production activation a policy decision. |
| First pass §8 concept families, later §6 B | **Develop** separate, bounded similarity navigation and source-supported variants in [O08](#O08). **Correct** any inference from graph connectivity to equivalence. |
| First pass §8 gap analytics, later §6 C | **Develop** the three named reports first in [O08](#O08). **Conditional** wider missing input or exception, weak bridge, and broken dependency analyses with defined inspected projections and a user question. |
| First pass §8 dossiers, later §6 A and C | **Develop** exact comparison-side and typed dependency membership in [O08](#O08). **Conditional** display optimization after an actual competing-member budget. |
| First pass §9, later §9 | **Develop** the staged source-to-role-to-relationship sequence and matched assessment below. Keep statistical research independent of structural delivery. Brier score and log loss are fit diagnostics. Calibration and generalization each require a separate evaluation claim. |

## How to choose and integrate the next increment

| Order | First independently useful change | Evidence that can change the choice |
|---|---|---|
| 1. Source and roles | Publish projected captions through ordinary citations. Add an exact qualifier and host path for selected definition and procedure cases. | A source item outside selected membership needs a separately justified view rule. Matched annotation results should show which errors need annotation repair, role recipes or both. |
| 2. Interpretation and comparison | Assess descriptive GLiNER declarations and focused clause classification separately. Consume admitted predicate frames and repeated conditions in comparison. | Retain independent terms and contents if relationship or clause interpretation remains unresolved. Advance span rescoring or joint decoding only when the loss breakdown identifies their contribution. |
| 3. Linking and delivery | Resolve selected explicit references and declarations, then add justified comparison-to-root members and the three reports. Evaluate artifact nomination and scoring on their respective populations. | A candidate beyond code blocking is useful evidence for nomination. An improvement to fixed-pair scoring needs eligible labeled pairs with informative name fields. Similarity neighbors must help navigation with scope and evidence visible. |
| Parallel statistical development | Author the exact attachment-event rubric and specify the shared table correspondence. Reuse the prior/logistic baseline and exact enumerator first. | Missing binary grades leave fitting unavailable. A model that still selects the same table roles can demonstrate better explanations of uncertainty only against independently assessable alternatives or failure cases. Larger executors and posterior models need a distinct demonstrated use. |

**Comparisons.** Freeze the selected source, operation question, eligible universe and reference
independently of the output. First run on common candidates to attribute changes in interpretation
or ranking. Then inspect actual discovery, including omissions outside the output cohort. Track
the transition from source evidence to addressable occurrence, candidate, supported relationship
and delivered product. Record corrections, newly supported structure, losses, spurious additions,
unresolved alternatives and unavailable work separately. Use grouped or probabilistic summaries
only for the stated population and unit of analysis. Prioritize explicit controls over a larger
experiment that cannot separate the mechanisms. [WCE source and output assessment](../plans/witnessed-corpus-enrichment_2026-11-05.md) ·
[ADR-0068](../adr/0068-single-corpus-method-development.md)

**Adjacent library disposition.** Start with the existing exact lexer and source maps. Bounded
Unicode `regex` captures, repeated capture extents and timeouts can improve candidate cues.
Tokenizer overflow and offset inspection can diagnose omitted model windows while the retained
source mapping remains authoritative. Use a `LatexWalker` and configured macro context as a
challenger only for a named retained LaTeX structure the existing parser misses. Its offsets
are in the LaTeX input and require independent correspondence to the PDF occurrence. Consider
SymPy assumptions and `refine` or SciPy distribution objects only for a grounded mathematical
verification question. Keep local variance and scale bindings explicit. The prepared
`rule-engine` path already serves declared predicates. Z3 can help when an operator needs a
counterexample for a formally represented condition overlap, with exact bindings and an explicit
unknown result. Consider Pynini's finite-state rewriting for recurring, context-dependent
normalization only after simple source-preserving mappings fail. Statsmodels grouped diagnostics
and prediction-powered inference need their own estimands and valid sampling. The latter has
potential for a population-level coverage question with independent probability-sample labels.
[Regex guide](../libraries/parsing/regex.md) · [Tokenizer Encoding](https://huggingface.co/docs/tokenizers/api/encoding) ·
[LaTeX node API](https://pylatexenc.readthedocs.io/en/latest/latexwalker/) ·
[SymPy assumptions](https://docs.sympy.org/latest/modules/assumptions/refine.html) ·
[SciPy distribution guide](https://docs.scipy.org/doc/scipy/tutorial/stats/rv_infrastructure.html) ·
[Z3 guide](https://microsoft.github.io/z3guide/docs/logic/intro/) · [Pynini guide](../libraries/parsing/pynini.md) ·
[Statsmodels mixed models](https://www.statsmodels.org/stable/mixed_glm.html) · [PPI source](https://github.com/aangelopoulos/ppi_py)

**Architecture and execution fit.** The selected realizations localize projection, annotation,
interpretation, assessment and presentation to existing owners (A1 and A3). They need explicit
occurrence, role, grouping, relationship, population and policy meanings at their boundaries
(A2). Reuse retained native input and unchanged annotations. Resolve per-view membership in
sets, scope pair generation before fuzzy comparison, and use SQL for ordinary pinned reads and
gap joins. Keep costly model scoring, fitting and factor execution outside database
transactions. Bound traversal, candidate fan-out and intermediates by the consumer's actual
question. Use prepared rule/schema assets and bounded provider batches where inputs match.
Evaluate repeated reads, skew, partial coverage and cancellation before choosing a new cache,
executor or retained projection (A4). The existing LinkML release owns new semantics, native
admission owns authenticated publication, and assessment keeps separate reference custody.
Semantic contract changes cut over affected producers, readers, CLI, MCP and detached delivery
together, preserving immutable prior evidence and regenerating derived outputs whose meanings
or dependencies change. Any binding decision change belongs in its owning design and ADR.
[Design principles](../design_review/design_principles/core/design-principles.md) ·
[Execution heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md) ·
[Code-intelligence profile](../design_review/design_principles/profiles/code-intelligence/principles.md) ·
[Binding](../design_review/design_principles/binding/corpus-structure.md)

**Evidence limits · 2026-11-07.** The two frozen source-reference reconstructions passed against
the retained JSON. They reproduce the source judgments and anchors. Product and provider
qualification, new fitting, and quantitative performance tests were `not_run` for this review.
WCE12 remains under its existing coordinator. Selected extensions enter implementation planning
through their owning plans and decisions. [Source reference reproduction](../design_review/evidence/2026-11-06_wce-completion-repair/source-references/README.md)

```bash
set -o pipefail
base=docs/design_review/evidence/2026-11-06_wce-completion-repair/source-references
python3 "$base/freeze_reference.py" | cmp - "$base/source-reference.json"
python3 "$base/freeze_reference.py" --marginal-roles | cmp - "$base/marginal-role-reference.json"
```
