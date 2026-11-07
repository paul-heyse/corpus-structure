# Source and linguistic composition

**Development scope audited · 2026-11-07.** Companion to the [next corpus enrichment coordinator](../next-corpus-enrichment_2026-11-07.md). Develops the selected [O01](../../functional_reviews/next-corpus-enrichment_2026-11-07.md#O01), [O02](../../functional_reviews/next-corpus-enrichment_2026-11-07.md#O02) and [O03](../../functional_reviews/next-corpus-enrichment_2026-11-07.md#O03) outcomes.
The coordinator owns combined completion and cross-companion decisions.

Keep source access, grammatical evidence, semantic interpretation and comparison as distinct
operations. A native text occurrence can be accessible without a selected relationship. A frame or
qualifier can be useful without an established interpretation. A change to source coordinates
invalidates dependent evidence unless exact correspondence is demonstrated. The next release
regenerates affected products from immutable inputs and preserves original cuts and evidence under
their original contracts. [ADR-0067](../../adr/0067-witnessed-current-only-cutover.md) · [ADR-0068](../../adr/0068-single-corpus-method-development.md)

<a id="NCE-01"></a>
## NCE-01 · Project eligible native captions

**Outcome.** In the ordinary bounded source selection, a reader can cite a recovered caption and an
artifact method can discover it through its existing projected passage. Work against the archived
native product and the fixed source-reference selection. The known controls are Table 5.8 and 5.9 on
physical page 224, view 118, with caption pointers `#/texts/65` and `#/texts/66`, and Table 6.1 on page 234, view 124,
with `#/texts/37`. [Frozen references](../../design_review/evidence/2026-11-06_wce-completion-repair/source-references/README.md)

**Realization.** The object-backed `_drafts` path computes `item_refs` before projecting. The record-backed `published_section_drafts`
path selects members and ancestors and may also hydrate excluded furniture. Neither the object index
nor the record closure is itself the admissible member set. Pass exact selected body membership from
both builders to the shared projector and derive the eligible associations from Docling Core 2.105.0
`NodeItem.children` and `FloatingItem.captions`. Resolve these exact native references within the authenticated membership set. Require
the table and caption to belong to the same archived native product and selection. Validate native
pointer identity, body layer, caption association and the original `text` field. Use a set keyed by
physical pointer within the view. Keep direct section selection boundaries. A caption accessible
only through a reference outside the selected membership stays unresolved under [NCE-S01](#NCE-S01). [Object builder](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_methods.py) · [Record builder](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_section_views.py) · [Shared projector](../../../python/corpus-structure/src/corpus_structure/ingest/pdf_hierarchy.py)
· [Tagged Docling types](https://raw.githubusercontent.com/docling-project/docling-core/v2.105.0/docling_core/types/doc/items/node.py)

Keep cell and rich-cell traversal unchanged. After the cells of a table, emit qualified captions in
native child order followed by remaining caption reference order. If a caption is already an
ordinary non-table child, leave it in that traversal position. Make that decision before visiting a
table so traversal order cannot move the caption. Emit an ordinary `native_text` piece using its own pointer
and source field. Keep synthetic separators separate. Retain separate occurrences for equal text on
different pointers and separate view citations for a shared occurrence. Do not assign the caption a
table cell index. Ensure the native publication guard checks the same selected membership and exact
source content. Give the two builders one shared new projection recipe identity derived from the
same semantic inputs. [Native publication guard](../../../python/corpus-structure/src/corpus_structure/semantic/sql/source_views.sql)

Admit bounded caption passages in structural source preparation and exercise existing artifact
discovery and `ArtifactCitation`. Regenerate the affected selected views and downstream offset-dependent products
against the archived native input. Explicitly prove unchanged text, input identity and source
mapping before reusing an annotation or model result. Treat shifted offsets as a new projection even
when native occurrence and text are identical. Keep reprocessing to affected views and consumers.
The link companion consumes recovered citations and separately owns new nomination/selection
semantics. [Structural source preparation](../../../python/corpus-structure/src/corpus_structure/semantic/structural_sources.py) · [Artifact discovery](../../../python/corpus-structure/src/corpus_structure/methods/artifact_identity.py)

**Acceptance.** Verify exact text and pointer for all three captions, one projected occurrence per
selected view, unchanged rich-cell positions relative to the cell sequence, and parity across
object/record builders. Exercise overlapping views, direct selection, duplicate paths to one
pointer, two equal strings at different pointers, ordinary caption position, furniture, foreign and
reference-only members, publication refusal/retry, and bounded Reader and detached citations. Trace
each independently supported pair through represented endpoints and candidate admission. A recovered
endpoint alone leaves the support judgment open. Use existing test families `test_pdf_body_selection.py`, `test_pdf_native_consumer_journey.py`, `test_projection_analysis_products.py` and the
applicable artifact discovery controls through `uv run ci test -- PATH`. Keep the previous view reproducible.

<a id="NCE-02"></a>
## NCE-02 · Retain neutral frames and host-bound qualifications

[Development delivery and remaining evidence boundaries](../next-corpus-enrichment_2026-11-07.md#remaining-nce-02-execution-verification)

**Outcome and prerequisite slices.** First publish a bounded neutral frame candidate and exact
clause-focus interface from the retained linguistic operation. This is the prerequisite for [NCE-04](model-candidates-and-clause-interpretation.md#NCE-04).
Then add deterministic interpretation and witnessed attachments on the same identities. The
deterministic operation can run when a model observation is absent or unavailable. A later model
contribution is optional evidence for a new interpretation execution. It neither defines a frame's
identity nor supplies a source span or host by itself. Existing passages let this work start
independently of NCE-01. Use recovered captions only where the new passages are needed.

**Candidate and extent contract.** Reuse `AnnotationView` to reconstruct the original block under its retained
text digest, token locations, dependency heads, sentence ownership, and declared attribute
availability. Publish one source-anchored predicate frame candidate per distinct governing predicate
and proposed reading, with selected source view/passage, exact focus extent, evidence version,
predicate and role identities, token membership and coalesced extents. Record unavailable
annotations and unsupported alignment. Never expand a discontinuous role to its enclosing interval
unless all intervening material belongs to it. Preserve partial roles and competing readings
independently of whether an existing consumer needs a contiguous span. Use a base noun chunk and
permitted nominal complements, stop at competing coordinated heads and independent propositions, and
keep a bounded rule variant for each admitted grammatical construction. Use spaCy 3.8.18 `Matcher` for
local lexical or morphological cues, `PhraseMatcher` for released terminology, and `DependencyMatcher` direct relations for
named predicates and arguments. Reuse retained child and coordination traversal. Keep active,
passive, copular, naming and reported-assumption recipes distinct. Record contributing cue and
interpretation separately. [Annotation reconstruction](../../../python/corpus-structure/src/corpus_structure/ingest/annotation_views.py) · [Named rules](../../../python/corpus-structure/src/corpus_structure/methods/annotation_rules.py) · [spaCy DependencyMatcher](https://spacy.io/api/dependencymatcher)

**Interpretation and qualification.** Separate extraction of actor, action, object, voice, polarity,
modality, condition, exception and order cues from disposition as definition, explanation,
reference, prescribed action, described process, assumption/restriction, example or unresolved. Use
source layout and discourse cues such as headings, lists, quotation, attribution and example
context. Record the origin of any inherited argument, modal or qualification. Qualifier ownership
starts from a directly attached subordinate predicate and marker, with a distinct recipe for nominal
exceptions and explicit layout inheritance. Keep local qualifiers separate and admit shared scope
only when the source supports coordination or list inheritance. Associate each negation, attribution
and modal with its host predicate. Distinguish negation of a defining act from negation embedded in
defining content. Preserve competing attachments and unsupported interpretation. A modal supplies
linguistic evidence, and a source-supported behavior reading governs whether it describes a
prescription. [Current frame producer](../../../python/corpus-structure/src/corpus_structure/methods/structural_roles.py) · [Definition applicability](../../../python/corpus-structure/src/corpus_structure/methods/definition_applicability.py)

Retain the qualifier component even when its attachment is unresolved. A selected attachment
identifies exact qualifier and host proposition or relationship, role and direction, located source
basis, applicable scope/version and predecessor identities. Distinguish condition, assumption,
parameterization, exception, attribution, modality, temporal order and semantic dependency. Reuse
existing witnessed relation contracts and released predicates where the meaning matches. Any new
semantic relation belongs to the existing LinkML release and native admission, with authorized
readers consuming that contract. Lower supported logical meanings into the released `Qualification` and `Condition`
types. Retain a supported located condition as `EscapeCondition` when its formal meaning cannot be represented,
and leave an unknown host unresolved. Required polarity or modality must be established for the
applicable released qualification. An exception needs a justified interpretation before becoming
logical negation. Keep standalone qualifier attachment and qualification lowering distinguishable so
failure of one does not erase source evidence. [Model declarations](../../../python/corpus-structure/src/corpus_structure/model/semantic/core.yaml) · [Knowledge representation](../../design/D1-knowledge-representation.md)

**Acceptance and delivery.** Compare baseline and revised recipes on the same retained annotation
block and exact source selection. Evaluate boundary, host, kind, scope and logical lowering
independently. Retain the probability comparison as the integral's full subject and “of constant
density” as the nominal complement. Distinguish Huygens' historical contrast, quoted “if,” two
independent condition clauses, a fronted condition on coordinated predicates, and embedded negation
in a positive definition. Keep “do not heat and stir” unresolved where scope remains ambiguous and
preserve contrast in “do not heat, but stir.” Include an unrelated exception, an attributed
assumption, mathematical “must” versus policy instruction, and a procedure with a valid actor/action
and unresolved artifact. Use the frozen benefit account for Event F, variance, parameters and
zero-wait conditions where applicable. Validate exact identity and failure preservation with the
existing structural-role, definition, annotation and native admission test families. Exercise the
ordinary read and portable routes for affected products. Version frame and attachment semantics and
regenerate affected derived products without rewriting retained source annotations. [Benefit account](../../design_review/evidence/2026-11-06_wce-gs120/assessment/benefit-account/README.md)

<a id="NCE-03"></a>
## NCE-03 · Compare qualified frames and repeated fields

**Outcome.** Use the deterministic NCE-02 frame and qualifier contract for scope-aware comparisons.
NCE-04/05 experiments can improve evidence later. A model result or improved experimental score is
not a prerequisite for delivery. Supply exact comparison-side and component references for the later
root-binding operation, whose membership and binding decisions remain with its own companion.

**Realization.** Evolve `ClauseReading` and `DimensionComparison` from one field per dimension to a typed collection of
source-backed members. Preserve order, each member's lexical and typed value, source extent and
premises, and single/conjunctive/disjunctive/unresolved grouping. Preserve the distinction between
absent, unresolved and known empty where the source establishes it. Keep distinct host frames or
interpretations separate rather than pooling all fields in a passage. Compare members under declared
source scope, version and applicable quantity/unit/basis, and keep unresolved alignment or grouping
visible. Continue the exact singleton threshold operation and its inclusive/exclusive interval
handling. Version the deterministic reader so current lexical inputs can still nominate a reading
when they identify an exact source cue. Repeated lexical candidates must stay visible and the
consumer must know their basis. Do not infer cross-version succession from a label change or a
shared string. [Current comparison method](../../../python/corpus-structure/src/corpus_structure/methods/structural_products.py) · [Types](../../../python/corpus-structure/src/corpus_structure/semantic/structural_products.py)

Extend the cached lexer-only and contextual LALR paths for bounded, source-delimited comparators,
ranges, quantities, dates, identifiers, and explicitly defined condition syntax. Keep formal syntax
separate from prose attachment. Use Lark 1.3.1 with `parser="lalr"`, `lexer="contextual"`, and `propagate_positions=True` for deterministic bounded
parsing. Use positioned tokens and postparse transforms with explicit source offsets. Share
fragments through `%import` or grammar templates when the same released syntax has multiple consumers. A
well-formed expression alone establishes neither units nor applicability. Unknown or unsupported
terms remain located premises. [Current parser](../../../python/corpus-structure/src/corpus_structure/semantic/structural_parsing.py) · [Lark grammar reference](https://lark-parser.readthedocs.io/en/stable/grammar.html) · [Parser configuration](https://lark-parser.readthedocs.io/en/stable/classes.html)

Native SQL currently derives its own lexical clause fields and compares singleton dimensions. Use
admitted NCE-02 frame and qualifier references and exact source bindings as the authority for the
new route. Change native comparison/admission, released observation declarations, application
reader, native and detached replay, CLI/MCP renderers and side references together. Validate those
inputs against the frozen comparison-side selection before deriving comparison. Avoid a second
independent natural-language parser or accepting submitted role values without admitted evidence.
Preserve existing singleton reports under their original evidence custody. Convert an authenticated
single field to a single-member reading only where it supplies the exact new meaning. Regenerate
when the required grouped evidence is absent. Regenerate selected new comparisons through the new
release and invalidate dependent dossier views only when the bound inputs or membership change. [Native structural functions](../../../python/corpus-structure/src/corpus_structure/semantic/sql/structural_products.sql)
· [Released observations](../../../python/corpus-structure/src/corpus_structure/model/semantic/observations.yaml) · [Portable verification](../../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py)

**Acceptance.** Compare changed responsible role, optional versus required modality, added
exception, narrowed condition and multiple objects or conditions. Exercise an explicit
conjunction/disjunction and an unresolved grouping with identical surface members, ensuring the
latter cannot assert equivalence or an interval consequence. Include missing basis, unknown unit,
incompatible scope and exact directed succession controls. Verify native and application agreement
on singleton and repeated fixtures, replay under the selected contract and ordinary Reader/CLI/MCP
and detached delivery of complete evidence. Target `test_typed_structural_composition.py`, `test_comparison_projection.py`, `test_structural_native_replay.py` and portable bundle checks through
the existing managed test route. A locally passed fixture establishes the declared comparison case
and does not establish aggregate benefit.

## Completion audit follow-up

[Series disposition](../next-corpus-enrichment_2026-11-07.md#completion-audit).

<a id="nce-01-audit"></a>
**NCE-01-A1 · Authenticate the projection recipe at publication.** Both builders emit the
v8 caption projection and the three recovered captions reached artifact admission. The
native writer checks the submitted recipe bytes against the submitted digest and runs the
caption guard when those bytes declare v8. A different recipe identifier can bypass that
guard on a fresh publication. Bind new publications to the selected recipe and preserve
exact historical reuse. Exercise omitted and duplicate captions, a substituted recipe,
and an unchanged retry through the public native writer. The historical caption probe
called the private helper directly. [Native writer](../../../python/corpus-structure/src/corpus_structure/semantic/sql/source_views.sql#L104) ·
[Caption probe](../../design_review/evidence/2026-11-07_nce-source-linguistics/check_caption_admission.py).

<a id="nce-02-audit"></a>
**NCE-02-A1 · Authenticate interpretation and condition lowering.** The selected
antecedents and attachments retain their dated evidence. Native admission binds the
predicate reading to the retained frame but accepts submitted reading and polarity fields
without deriving them from the retained cues. For ordinary conditional cues it checks
condition shape and exact escape wording where present, leaving room for a substituted
formal condition on a nonformal premise. Detached replay derives the complete reading
and may refuse what native admission accepted. Verify parity on a forged polarity or
formal condition and the exact source-backed or escape reading through the ordinary
consumers. [Native predicate guard](../../../python/corpus-structure/src/corpus_structure/semantic/sql/source_contributions.sql#L1088) ·
[Detached reconstruction](../../../python/corpus-structure/src/corpus_structure/serve/review_bundle.py#L1968).

**NCE-02-A2 · Preserve clipped role uncertainty into comparison.** A predicate
frame survives passage selection, but a retained participant whose anchors all fall
outside the selected passage is dropped. Comparison then reports the dimension as
absent. Carry the unresolved role without inventing an extent and test an
action-only passage where the retained annotation supplies a participant outside the
selection. [Role emission](../../../python/corpus-structure/src/corpus_structure/methods/predicate_contributions.py#L438) ·
[Comparison group derivation](../../../python/corpus-structure/src/corpus_structure/methods/structural_products.py#L417).

<a id="nce-03-audit"></a>
**NCE-03-A1 · Compare supported typed members and enforce unresolved grouping.** Run
231/cut 323 retains two premises and withholds a consequence. Both comparison engines
preserve repeated members but compare their lexical arrays. Typed interval logic uses
singleton thresholds and can still issue a consequence when an unresolved grouping in
another dimension affects the comparison. Establish typed member alignment under the
declared scope and basis. Exercise changed typed members, conjunction versus disjunction,
and identical unresolved member lists alongside otherwise comparable singleton thresholds.
Compare native and application decisions and exact detached delivery. [Application comparison](../../../python/corpus-structure/src/corpus_structure/methods/structural_products.py#L163) ·
[Native comparison](../../../python/corpus-structure/src/corpus_structure/semantic/sql/structural_products.sql#L531).

## Owned conditional investigations

| ID | Trigger and bounded investigation |
| --- | --- |
| <a id="NCE-S01"></a>NCE-S01 · Reference-only captions | A source-supported caption outside selected body membership would serve an identified ordinary consumer. Examine whether an explicit selected-membership extension can preserve direct section scope and native guard parity. Keep the first projection within existing membership. |
| <a id="NCE-S02"></a>NCE-S02 · Fragments and graphical labels | A retained native pointer or region would help a named consumer while exact projected text is unavailable. Expose appropriate item/region evidence through the existing reader. Admit exact spans only with a verified source field and mapping. Additional OCR requires a distinct unresolved source need. |
| <a id="NCE-S03"></a>NCE-S03 · Lexer and formal parsing alternatives | For demonstrated mixed Unicode or repeated cue boundaries, compare timeout-bounded `regex` matches using `captures()` and `spans()` for repeated source extents with the current lexer and span validation. For a supported ambiguous formal expression, compare Earley explicit alternatives or a bounded forest with the deterministic route. Preserve alternatives and resource exhaustion. Try `TextSlice` versus local slices with explicit base offsets only for a real coordinate or preparation burden. `TextSlice` supports basic/contextual lexers and may still count preceding text for line positions. Use `UnexpectedInput` and interactive expectations for authoring diagnostics. Recovered synthetic tokens are diagnostics, with original-source custody kept separately. [Regex guide](../../libraries/parsing/regex.md) · [Lark guide](../../libraries/parsing/lark.md) |
| <a id="NCE-S04"></a>NCE-S04 · Formula coverage | An exact symbol extent remains missing in a retained formula. Reuse the prepared math grammar and local macro context. Compare the current ambiguous-tree refusal with admission only when all admitted alternatives agree on extent, symbol and relevant syntactic role. Preserve ambiguity when a binder, subscript or scope differs. For a named missed retained LaTeX construct, compare `LatexWalker` with a configured macro context on that same input and verify its source-to-PDF mapping before emitting a citation. Formula Z and the unsupported affine-X link remain distinct controls. [Formula producer](../../../python/corpus-structure/src/corpus_structure/methods/structural_roles.py) · [pylatexenc guide](../../libraries/parsing/pylatexenc.md) · [LatexWalker API](https://pylatexenc.readthedocs.io/en/latest/latexwalker/) |
| <a id="NCE-S05"></a>NCE-S05 · Alternate annotation recipes | Repeated source/token alignment or heading/list boundary errors under a matched frame justify an `AttributeRuler`, tokenizer exception, layout-derived sentence starts or alternate pinned parser profile. Compare a new annotation identity. Use strict `Doc.char_span` and optional `displaCy` inspection on verified reconstructed text. Use `Doc.spans` and `SpanGroup` for overlapping proposals. Preserve original source coordinates. spaCy's experimental coreference companion is incompatible with the pinned spaCy range. Investigate a compatible anaphora route only if unresolved references justify it. [spaCy guide](../../libraries/parsing/spacy.md) · [Strict span alignment](https://spacy.io/api/doc#char_span) · [SpanGroup](https://spacy.io/api/spangroup) |
| <a id="NCE-S06"></a>NCE-S06 · Grounded mathematical checks | A retained symbolic claim or distribution has source-supported operands, assumptions, scope and parameter bindings. Compare SymPy `refine` under explicit assumptions or SciPy distribution objects for the named numerical verification. Distinguish variance and scale, preserve unknown premises, and require independent expected results. Keep the existing typed value and condition route for ordinary extraction. [SymPy refine](https://docs.sympy.org/latest/modules/assumptions/refine.html) · [SciPy distribution guide](https://docs.scipy.org/doc/scipy/tutorial/stats/rv_infrastructure.html) |
| <a id="NCE-S07"></a>NCE-S07 · Formal overlap or counterexample | A named consumer needs to test overlap or obtain a counterexample for fully bound formal conditions. Use the prepared rule-engine path for declared predicates. Compare Z3 `Solver.check()` and `model()` on explicitly translated typed conditions, with unsupported translations and solver unknown visible. Keep the released condition and source bindings authoritative. [Rule engine guide](../../libraries/scientific_compute/rule-engine.md) · [Z3 solver guide](https://microsoft.github.io/z3guide/docs/logic/intro/) |
