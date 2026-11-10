# Inspectable terminology, grounding and measurement meaning

**Proposed functional judgments, 2026-11-10.** [Shared baseline](../domain-data-model_2026-11-10.md).
Sources: [DDM-05/06/11/12](../../library_leverage/libraries/domain-data-model/briefings/vocabularies-and-ontology.md),
[OAK overview](../../libraries/data_model/oaklib.md) §§4–7,11,13 and
[Valuesets](../../libraries/data_model/valuesets.md) including addendum §§1,4,9.

<a id="O05"></a>

## O05 — Release inspectable concept and vocabulary bindings

**Recommend a bounded terminology-authoring capability.** A domain developer could declare
several controlled fields over one supplied ontology snapshot; a researcher could inspect
allowed terms, definitions, selected broader/narrower relations and mapping provenance, then
filter source-grounded records by those declared categories. A credible scientific terminology
pack could separately classify concept families and statistical methods. Source selection and
semantic suitability remain open; [STATO](https://stato-ontology.org/) is an investigation lead,
not a qualified chosen vocabulary or a claim that its terms already match this corpus.

The interaction should retain reported wording, selected identifier, vocabulary revision,
definition, mapping predicate and check status. Source wording and external vocabulary meaning
have different authorities. Neither establishes scientific truth or global canonical identity.

[ontology.py](../../../python/corpus-structure/src/corpus_structure/semantic/ontology.py)
already expands supplied definitions with final whole-union subtraction;
[prepare.py](../../../python/corpus-structure/src/corpus_structure/semantic/prepare.py) prepares
snapshots. Current VocabularyMember in
[types.py](../../../python/corpus-structure/src/corpus_structure/semantic/types.py) retains value,
meaning and label; the proposed richer inspection needs an explicit additional metadata product
and consumer work. The prediction-outcomes test demonstrates selective Valuesets import, but
its draft enum has no ontology meanings and cannot alone demonstrate richer binding.

**Preferred realization.** Select source LinkML definitions, induce them under the explicit import
closure and compile the promised vocabulary metadata as a release-owned immutable product.
Use Valuesets `RichEnum.get_meaning/get_metadata/get_annotations/from_meaning` as convenient
projections only where they retain the promised semantics; generated enums omit hierarchy and
some mappings. Keep application-specific absence/confidence/lifecycle categories local where
their meaning differs. Aggregate imports and a live terminology endpoint are inferior defaults:
they either lose selection fidelity or introduce availability/snapshot obligations.

DDM-11's reuse fits this actual multi-enum workflow: one operation-owned OAK preparation can
supply prefix ownership, labels and traversal for two useful enums and their checks. OAK
`ProntoImplementation(wrapped_ontology=...)` and explicit import-depth controls are concrete
mechanisms. A public Term Validator adapter-injection route remains unestablished, so retain
supported temporary-file leaf handling rather than build on its private cache.

**Prerequisites and delivery.** `prepare.py` excludes native bindings/unit metadata/PV hierarchy
and richer roles from its finite profile. Supporting selected constructs means defining their
lowerings, validation and consumer meaning, not deleting rejections. Diagnostic `validate_bindings`
does not enforce PostgreSQL publication. Preserve final subtraction and explicit unchecked meanings.
Deliver one pack with two independently useful controlled fields, an inspection/filter consumer,
hierarchy/mapping-kind fidelity and archived reopening without a current ontology endpoint.
Keep source mismatch visible. No broad external vocabulary adoption follows automatically.

<a id="O06"></a>

## O06 — Offer terminology candidates for located concepts

**Conditional research extension; prefer explicit located input first.** A researcher reviewing
a source definition could select a phrase, request vocabulary candidates, compare labels and
definitions, retain competing mappings and leave the result unresolved where appropriate.
This extends current corpus-local linking into external grounding without requiring automatic
whole-document annotation or granting ontology matches selection authority.

Compose release-derived labels/synonyms with OAK `label`, `entity_alias_map`, selected
`sssom_mappings` and controlled neighborhoods, then reuse existing candidate/assessment/selection
owners. Preserve repository source coordinates. Native `basic_search(SearchConfiguration)`,
`annotate_text` and `lexmatch` are candidate mechanisms requiring backend qualification.

**Consequential installed-source observations.** OAK0.7.4's naive TextAnnotatorInterface path
uses the first `text_lower.index` occurrence, an offset convention needing adaptation and a
commented trailing-word guard. Pronto basic_search has a truthy label-field branch and its visible
branches do not implement the advertised case-insensitive control. These observations in
`interfaces/text_annotator_interface.py:143–176` and
`implementations/pronto/pronto_implementation.py:800–847` defeat any assumption of faithful
all-occurrence extraction or configured-field search without qualification. A deterministic
lookup view derived from explicit term metadata is the preferred first option; no product
repair to OAK is authorized by this review.

**Alternatives.** Retain local exact/lexical/contextual retrieval for local concepts. Use the
released terminology lookup for external candidates. Consider pairwise/termset similarity only
with declared predicates and information-content population; embedding/remote providers require
their own benefit and provenance case. Similarity ranks rather than proves equivalence.

**Delivery and trigger.** Select one meaningful terminology source and a located concept review
task. Multiple candidates expose matching reasons and exact/close/broad/narrow mapping kinds;
no suitable match remains unresolved; choosing a candidate retains both original source and
vocabulary pins. Automatic occurrence extraction needs an independent offset/completeness
contract before it can replace repository mention production. No source-quality gain is claimed.

<a id="O07"></a>

## O07 — Explain vocabulary updates before activation

**Recommend alongside useful vocabulary adoption.** The operator could compare supplied
snapshots and inspect changed admitted values, labels, meanings and mappings, known field uses
and retained interpretations that may warrant review. This is a concrete model-change activity,
not automatic synchronization or reinterpretation of earlier releases.

Extend [compare_semantic_releases](../../../python/corpus-structure/src/corpus_structure/semantic/operation_reporting.py)
and the existing `ci schema diff`/model-change workflow. Exact prepared membership/metadata
comparison is the minimal authoritative explanation of admission changes. OAK
`DifferInterface.diff/grouped_diff/diff_summary`, obsoletion/migration relations and supported
`UsagesInterface.usages` may explain source changes, but their adapter coverage must be explicit.
Ontology uses and repository consumers are separate populations: no OAK hit cannot prove no
corpus impact. Report unassessed downstream scope rather than invent completeness.

**Alternatives.** Prepared-product comparison suffices before KGCL; native typed diff adds
value when the selected backend explains a rename/obsoletion/relation faithfully. Raw source
diff is useful supporting evidence but weak as the sole semantic view. Automatic KGCL patching,
`migrate_curies` or `save` does not supply release publication or authority over old answers.
Retain current manual review/activation custody.

**Delivery and trigger.** Once O05 has a selected evolving vocabulary, compare a label-only
change, removed/obsolete member and close-to-exact mapping change. Show known consumer evidence
and unknown scope; old release reads reproduce their original meaning. No mutable impact register,
remote vocabulary service or generic migration framework is required.

<a id="O08"></a>

## O08 — Recognize measurement identity before enabling conversion

**Recommend recognized unit/quantity interpretations as a scoped functional extension;
numerical conversion remains conditional.** A researcher could browse/group reported measurements
by recognized quantity/unit and inspect why two values are comparable, convertible or unresolved.
The interpretation preserves original spelling, value role, reference basis and uncertainty.
This is a useful credible workflow beyond present callers, not a claim that current comparisons
are incorrectly refused.

`QuantityValue` currently carries decimal/textual unit/basis. The statistics pack retains
referent/property/original value/role/unit/uncertainty/reference quantity/transformed value.
[structural_products.py](../../../python/corpus-structure/src/corpus_structure/methods/structural_products.py)
correctly withholds stronger threshold consequences when quantity, unit or basis is missing or unequal.

**Preferred first realization and alternatives.** Add selected released unit and quantity-kind
references as interpretations of retained source fields, composing O05 when useful. Valuesets
measurement/quantity-kind sources and LinkML UnitOfMeasure metadata are concrete source leads;
their draft annotations are not an executable conversion engine. Retain current text/refusal
when identity or basis is unresolved. Equal dimensions do not establish equal quantities.

For an explicitly selected cross-unit question, assess an established units engine separately
and declare precision, offset/scale, context, uncertainty and original values. Do not execute
arbitrary Valuesets conversion strings as governing computation. Numerical classification is
a distinct conditional policy and can return several matches; do not force exclusivity or
replace uncertainty. No conversion dependency is chosen here.

**Delivery.** Identification-only delivery needs a browsing/grouping consumer, source/recognized
distinctions and unresolved outcomes, with no conversion engine. If selected later, `500 ms`
versus `0.5 s` must establish the same quantity/basis before comparison. Unknown basis stays
unresolved; affine temperatures and contextual units challenge any conversion contract.
Admitting native unit metadata requires deliberate compiler/profile and affected consumer work.
All benefits remain Proposed; no measurement probe or runtime qualification ran in this review.
