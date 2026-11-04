# Statistics M1 source-reading reference guideline

**Proposed reference contract, version `statistics-m1-reference-3`, 2026-11-04.** Freeze its
exact bytes with the intended semantic release and source-ready reference frames before A/B/C.
This guideline defines source readings, not extraction predictions or scientific truth. The
candidate execution policy remains separately versioned in `m1-methods.yaml`.

## Population and eligibility

Inspect every item of each frozen selected source region, including empty, degraded and unsupported
items. The population manifest identifies the original, any excerpt's parent-page map, selected
native products, views and origin partition. Excerpts, editions, HTML copies and overlapping
windows from a common original remain in one origin group. Source selection precedes predictions.
The finite-cut release uses a census of reference occurrences and accepted predictions; it makes
no claim about unseen books. An absent family denominator is an unmet release obligation.

Eligible readings are explicit English statistical definitions, local propositions, numeric
property/value statements, native table data cells, and formula occurrences with local context.
Include worked examples and hypothetical statements with their stated qualifications. Exercise
instructions, page furniture, bibliographies and isolated numbers are outside these five families;
retain their region dispositions. A passage may contain several families. An intake omission,
unreadable source, unsupported layout or source contradiction remains visible in coverage and
original-page inspection; it is not an empty eligible reading.

The supported subset excludes inference of unstated scientific results, global identity merges,
proof verification, algebraic equivalence and reconstruction of unrecovered source words. Record
explicit local source content even when its claim is scientifically incorrect. Where the released
shape cannot represent a reading faithfully, report the limitation with its original source region;
do not force it into a simpler accepted record or silently remove it from the coverage audit.

## Shared field and coordinate rules

The effective `SemanticRecordFields` subclasses in the frozen release own exact roles and
requiredness. Supply every declared role. `present` requires located source content; `unstated`
requires an inspected applicable scope that does not state the role; `inapplicable` requires a
family-specific reason; `unresolved` records the ambiguity, available alternatives and reason.
Decoder omission never establishes any of these source states. Required roles must be present
for an accepted reference reading; meaning-changing unresolved fields prohibit acceptance.
Unrepresentable or genuinely unresolved readings remain in the source limitation account.

Use the shortest complete literal phrase that expresses a role, retaining determiners and
qualifiers that change meaning and excluding unrelated sentence punctuation. Preserve original
spelling, whitespace, numeric notation and mathematical tokens. A defining passage or proposition
ends at its complete clause boundary; do not include a following explanation unless required for
that reading. Preserve discontinuous words as ordered original pieces, with separate anchors;
never insert synthetic words into a source literal. Do not repair fused words or recognition errors
in retained canonical text. An exact location cites the actual coordinate text, not a paraphrase.

Each field has role-labelled evidence sets in its actual source space. Native table/cell/scope
addresses remain native; character spans remain exact selected-projection spans. A coarse native
location is never an exact original PDF box or character span. Classification values need located
cue evidence and an explicit classification policy; their labels are not necessarily source words.
A nonpresent field cites the inspected scope as association/context evidence. Source context may
cross selected views only under the released same-product binding with independently pinned
related sources; occurrence-defining anchors remain primary. Synthetic separators are not evidence.

Do not normalize or derive a numeric value in this initial reference subset. Leave the supplemental
`normalized_value` inapplicable with a reason. Preserve a range/comparator as stated, without binary
float substitution. No implicit positive polarity, certainty, universal quantification, unit,
population, symbol meaning or sample size may be invented. When a classification is explicit in
ordinary grammar, cite the actual grammatical cue; ambiguity stays unresolved.

For the submitted record format, original quoted literal roles use `kind: text` with the exact
source string, or `kind: text_sequence` for separately anchored ordered pieces. This includes
quoted numeric notation: this subset records the original literal, without an additional numeric
parse. Classification roles use their released label value and separate cue evidence. Native
table/cell/scope roles use the actual native pointer. Character evidence uses exact
`selected_projection` offsets and its genuine owning item/cell pointer; do not substitute an
equally spelled native-text coordinate. These representation choices keep independent readings
comparable under the released strict occurrence policy without asserting equivalence between
different source spaces or value kinds.

The native `scope` value is the primary frozen source view's `section_pointer`, identifying its
selected source section. Locate the narrower defining clause, condition and symbol declaration
separately in their own role evidence. Section identity does not make a reading universally
applicable within that section or merge equal symbol spellings across occurrences.

## Family readings

| Family | Occurrence and fields |
|---|---|
| Definition | One explicitly defined term occurrence with its complete defining clause and native local scope. Retain an explicitly stated alias and definition relation; otherwise mark those supplemental roles unstated. An alias must have its own located phrase. A later mere mention creates no new definition. |
| Qualified assertion | One explicit subject–predicate–object/proposition clause. Preserve negation, modality, attributed speaker, quantification, condition and scope in their separate roles when stated. A conditional clause and its conclusion form one qualified reading. A conjunction with distinct predicates or objects creates separate occurrences; do not drop the shared qualification. |
| Measurement | One referent/property/original-value/value-role statement. A stated mean, standard deviation, probability, sample size, bound or comparison keeps its distinct role. Preserve stated unit, comparator, uncertainty, reference quantity and condition. A hypothetical example stays hypothetical in its condition. A derived answer is included only if explicitly stated by the source, without claiming independent computation. |
| Table | One native non-header data cell with its complete ordered header path, native cell/row location and original cell value. Record a quoted row label separately when stated; no parser flag alone establishes its presence or absence. Retain separately located caption, applicable unit and note. Header inheritance follows native row/column extents and explicit note scope. A blank or dash is not zero: preserve its literal/state meaning under the source legend, or report unresolved. Ambiguous spanning headers or note applicability cannot become accepted by proximity. |
| Formula context | One native formula occurrence with its original formula literal and native local scope. Link explicitly declared symbol, meaning, domain and assumption only within that scope, with separately located declaration evidence. A new section reusing a symbol does not establish identity. A formula with several distinct declared symbol bindings yields one reading per binding under the occurrence rule below; do not invent an unobserved declaration. |

The versioned family occurrence policy is `statistics-reading-occurrence-2`. Decoder grouping
anchors are not sufficient occurrence identity. Use these actual primary anchor memberships:
definition term plus complete defining clause; assertion subject, predicate and object; measurement
referent, property and original value; table native table and data cell. A shared predicate word
or numeric string alone cannot merge compatible clauses. Required unavailable primary locations
remain unresolved; related evidence and synthetic separators cannot invent identity.

The versioned formula binding occurrence policy is `formula-symbol-first-use-1`. A binding
record includes the complete primary formula literal anchor and the first exact primary in-formula
use of that declared symbol as occurrence-defining anchors. Related declaration text supplies field
evidence, not occurrence identity. Repeated uses of the same symbol binding in that formula count
once; different declared symbols have different occurrence IDs. Incompatible readings of the same
formula/symbol use remain alternatives. A formula-only record is emitted only when there is no
explicit local binding, with symbol/meaning states justified by the inspected scope. If a macro,
transformed glyph or ambiguous declaration cannot be honestly located, retain an unresolved
source/routing limitation instead of manufacturing a symbol anchor or arbitrarily selecting a binding.
This policy preserves the generic released source-anchor-membership recipe.

When multiple eligible readings share the same occurrence anchors, retain alternatives for one
occurrence rather than fabricating duplicate occurrences. Occurrence identity uses the released
family/source/anchor-membership recipe. Equal strings at different source locations stay distinct;
repeated overlapping windows over one location do not increase the denominator. Full-record
comparison includes all declared role readings and required meaning-changing evidence. Core and
supplemental-evidence scores are separate diagnostics, not substitutes for the full-record gate.

## Independent passes and release evidence

Fresh `gpt-6.1-sol` high A and B sessions receive only the frozen source packet, this guideline,
released output contract and source-only framing instructions. C receives those inputs, both
passes, disagreements and reasons. Retain exact submitted bytes and actor/session/model identity;
the coordinator registers them through protected reference operations. No pass receives production
predictions, fitting features or held-out grades. Reference accepted standing is an evaluator
reading, not production publication authority.

Feature fitting consumes only the protected feature-fit partition. Final-event calibration is
separate; freeze acceptance thresholds and immutable policy-instance identity before final
assessment. If final errors influence development, acquire and freeze a new final population.
Retain all no-output units and report candidate capture, accepted full-record precision and recall
for every family. Required gates remain 90% capture, 97% precision, a one-sided 95% lower precision
bound of 95%, and 70% accepted full-record recall. A census supplies exact finite-cut precision;
undefined denominators or unsupported source coverage cannot become passing gates.
