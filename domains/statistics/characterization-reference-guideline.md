# Text characterization reference guideline

Version: characterization-reference-1. Source and output assessment have separate populations.
This guideline governs independent references, not production inference or knowledge admission.

## Authoring and custody

Author A and author B receive the same frozen source-only question, source/hierarchy context and
original coordinate bindings in fresh sessions. They must not inspect producer answers, candidate
parse trees or another author's answer. Adjudicator C receives the source and retained A/B passes,
resolves disagreements with reasons and preserves genuinely permissible alternative readings.
Output-first authors receive the explicitly selected outputs as well as source; that exposure is
recorded. Never turn an output-first judgment into an independently discovered source opportunity.

Use only supplied source evidence. Refer to original ordered real extents; do not replace a
cross-page or discontinuous opportunity by one bounding interval. Repeated identical wording is
not one occurrence. Context membership does not imply focal membership or an additional vote.

## Scope and states

The source-first panel spans the chapters and the nine facets below. It does not annotate every
passage or establish exhaustive book-wide semantic accuracy. The full-book execution account
separately covers every physical page and selected family.

Distinguish stated, unstated, unresolved, uninspected and inapplicable source states. Uninspected
source is not negative evidence. Inapplicable remains visible but is excluded from positive/miss
denominators. Ambiguous source can admit multiple compatible readings or an explicit unresolved
result; it must not force a unique answer. Failed or unavailable prediction is not semantic absence.

## Independent facets

1. Source capture: exact token/atom/constituent membership, repeated occurrences, original extents,
   formula/reference boundaries and discontinuous pieces. Alignment failure does not erase a miss.
2. Native fidelity: native labels, endpoints, roots, continuation/reference arguments, score and
   availability. Keep spaCy, UD, PTB and PropBank meanings distinct; fidelity is not prediction truth.
3. Predicates and roles: identify the supported predicate and participants; distinguish grammatical
   from semantic roles, local/inherited/implicit support and unresolved participants. A passive
   subject is not automatically an actor. Preserve collective versus distributive readings.
4. Operators and scope: identify negation, quantification, restrictor/body, modal force, attribution
   and their targets. Preserve nested scope; reported content is not automatically author endorsement.
5. Attachment and binding: identify the supported host, antecedent or binder at the supplied context.
   Preserve distinct equal-spelled binders. Do not propagate across unexamined section/quote boundaries.
6. Choices: distinguish semantic disjunction from analytical alternatives. Preserve correlated
   branches, prerequisite choices and unknown compatibility. Independently acceptable local roots
   do not establish that their crossed combination is acceptable.
7. Provider questions: judge the exact frozen question/options and allowed witnesses. Distinguish
   absent cue, insufficient evidence, none-of-these, missing candidate and policy withholding.
   A region label alone is not located support for an attachment or complete reading.
8. Coverage/failure: assess claimed eligible/examined/unexamined scope and actual family outcome.
   Successful empty can coexist with a source-first miss; unavailable required inference cannot pass.
9. Retained/consumer fidelity: preserve exact source/layer/choice identities, group membership and
   support through reads/export/replay. Scientific correctness is a separate downstream question.

## Grading and corrections

Each V3 case declares its required characterization family; examination by a different family
cannot establish that this question was answered. For graph expectations, freeze the comparison
projection: source_semantics excludes execution identities and irrelevant provider scores,
native_fidelity judges the retained native structure, and retained_identity judges exact custody.
Source-semantic prerequisites and alternatives are sets unless an explicit semantic order exists;
source extent order and ordered term children retain their order.

Declare the assessed facet and permissible source-supported alternatives before grading. Compare
only the declared semantic projection. Ignore incidental serialization order and alpha-renamable
local node identifiers; retain direction, parallel memberships, binder identity and choice correlation.
A validator pass, roundtrip or successful provider invocation is not an independent semantic answer.

Retain both missing opportunities and unsupported emitted structures. Report source limits, native
prediction errors, alignment/projection errors, construction errors and consumer errors separately.
Do not average incompatible native label schemes or confuse two denominators into one coverage rate.

Preserve original answers and grades when production is repaired. A source/question change receives
an explicit new reference version; unchanged source/question meaning may reuse compatible references.
No universal numerical accuracy threshold, forced unique logical form, held-out population or new
human grading step is introduced by this guideline.


## Compatible native task references

A native-scoring case uses `native_reference` as its independent expected structure, without
scalar/graph alternatives or candidate selectors. Declare version `spacy-native-reference-v1`,
scheme `spacy`, its task kind, exact original block text and independent words/spaces reconstructing
that text. Preserve the runtime question's atom policy for formulas and reference markers. Provide
sentence/span character boundaries, inspected category labels or dependency head/label arrays as
appropriate. Missing labels stay explicit. An omitted span state defaults to inspected; an explicit
null state is invalid. Sentence-boundary scoring uses `span_key: sents` and `labeled: false`.

Choose a complete source-native block by its original ordered extents before seeing predictions.
Equal text elsewhere is a different block. Output-first native cases additionally freeze the
corresponding native.block identity. The evaluator restores retained Docs without inference;
unsupported schemes and missing compatible native products remain unavailable, not empty passes.
Native metrics describe their inspected/aligned scope. Exact structural matching grades the
specified case, while partial, uninspected or unavailable native scoring remains unassessed.
This is not a universal accuracy threshold or an adoption gate.
