# M2 retrieval, composition, and delivery

**Proposed · 2026-11-08.** Owns PM2-08–PM2-10. Realizes
[O06](../../functional_reviews/production-milestone-two_2026-11-08.md#O06),
the candidate route for [O05](../../functional_reviews/production-milestone-two_2026-11-08.md#O05),
and conditional [O09](../../functional_reviews/production-milestone-two_2026-11-08.md#O09).
The [coordinator](../production-milestone-two_2026-11-08.md) owns scope and disposition.

<a id="PM2-08"></a>

## PM2-08 · Compose located evidence and deliver independently useful parts

**Inputs and result.** Consume selected source and exact upstream observations or
coverage outcomes, using PM2-01 bindings. Join by authenticated occurrence, local
scope, and declared endpoint and witness roles. Preserve each original product
alongside distinct candidate, interpretation and selection records. Compose
HanLP frame candidates, GLiNER mentions and structured fields, Maverick referents,
Dipo context candidates, and d1 interpretations through the released operation
and consolidation owners. Keep compatible qualified parts even when another
attachment is contested or no admissible complete record exists. A failed stage
leaves an attributable gap. A successful empty stage reports its inspected scope.

Use the existing component contracts where their meanings fit. Add only missing
typed roles, relations or fields through the release owner and migrate the
corresponding admission, Reader, MCP and detached-read consumers with them.
The declaration supplies the operation question, endpoint signature, applicability,
evidence roles and interpretation constraints. Provider-native role names and
labels remain intact. A product's meaning and operation are independent of the
benchmark corpus. The same attachment mechanism can connect a premise to an
assertion or a condition to an instruction under a different released vocabulary.
An input form such as a formula or caption may have a representation-specific
map from PM2-01. It does not choose a separate domain workflow.

| Product | Retained meaning and consumer |
| --- | --- |
| Entity/concept occurrence | Exact source mention with separate lexical, model and local referent evidence. Corpus links retain their own type, scope, and witness. |
| Predicate/action frame | Located predicate and argument extents, native roles, optional declared semantic roles, and missing or competing participants. |
| Qualified statement | Separate scope and witnesses for applicable polarity, attribution, modality, condition, exception or temporal fields. Preserve supported partial readings. |
| Partial procedure or workflow | Located participants, actions and independently evidenced ordering, prerequisite or responsibility, where the release defines them. Unestablished branches remain open. |
| Statement-and-context package | Focal product with references to bounded EDUs, source pieces, referents, candidate alternatives and named external context. Return a selected view over retained products. |

Use Dipo's ordered child ranges and EDU anchors to nominate relevant context.
A singleton remains addressable. A bounded display states omitted context and
can reference the wider tree without rereading it for every focal product.
Native nuclearity, sequence or rhetorical support may guide context selection.
An asserted causal, prerequisite or support relationship still needs its own
declared semantics and witness. Local entity referents do not establish event
reference or corpus identity. Ambiguous links remain proposals. Avoid merging
branches solely because their displayed source strings agree.

**Meaning, uncertainty, and publication.** Keep native score type, candidate
availability, model decision, constraint check, independent assessment and public
standing distinguishable. Treat agreement as a feature when providers share
source, representations, or candidate evidence. When a named event and reference
population support fitting, use existing operation-event machinery. For a bounded
finite problem with defined joint assignments, reuse the current interpreter and
displayed-support bounds. Count the mass of each distinct supporting assignment
once. A partial report's omitted mass constrains its display claims. Rank by
unfitted scores where suitable and withhold calibration claims. Revisit pgmpy or
Pyro only for a defined inference question beyond the finite route. Revisit Splink
only for a selected identity-linkage question. [D5 consolidation](../../design/D5-consolidation-identity-confidence.md) ·
[DMA support consistency](../domain-model-alignment/semantic-admission.md#DMA-04)

**Delivery and closure.** Use the existing contribution read facets and exact
source and contextual readers. Expose operation outcomes, selected meanings,
alternatives and public standing with bounded continuation under the same selection.
Keep large raw provider output behind its existing explicit read path. An initial
journey follows a located condition and host through the native observations,
d1 candidate choice, contribution, and Reader and fresh external MCP. For example,
the textbook's positive-variance premise is a control for attaching a condition
to the intended predicate. Use an independently reviewed missed source opportunity
to show that source-first discovery can add a different useful part. Withhold
one provider or attachment and verify the surviving contribution, source and gap
through those same consumers. Extend the journey to each selected family. A new
typed read earns scope only if the current consumers cannot deliver that behavior.
[D8 contribution inspection](../../design/D8-agent-and-query-interfaces.md#independent-contribution-inspection) ·
[Current Reader controls](../../examples/README.md)

<a id="PM2-09"></a>

## PM2-09 · Improve candidate context using Sentence Transformers

Reuse the existing contextual encoder, target registry, lexical channel, dense
channels, bounded fusion and witnessed selection. The current profiles use
`sentence-transformers==6.2.0` with E5-small-v2
`ffb93f3bd4047442299a41ebb6fa998a38507c52` and Qwen3-Embedding-0.6B
`97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`. Preserve each profile's dimensions,
prompt roles, pooling, normalization and actual token limits. The CPU encoder
already dispatches through `encode_query` and `encode_document` with explicit
prompts. Those routes and prompt bytes belong to the profile and final input
identity. A profile may be declared for a named relation task. Do not apply the
existing definition-retrieval prompt to a different question without establishing
that task's rendering and semantics.
[Contextual encoder](../../../python/corpus-structure/src/corpus_structure/methods/contextual_embeddings.py) ·
[Sentence Transformers guide §§2, 3.2, 8, 12](../../libraries/parsing/sentence-transformers.md) ·
[6.2.0 encoder source](https://github.com/huggingface/sentence-transformers/blob/v6.2.0/sentence_transformers/sentence_transformer/model.py)

**First comparison.** Hold profiles, target population and candidate bounds fixed.
Compare current located-context rendering with a released variant containing the
same literal and a bounded anchored frame, local referent descriptor or discourse
neighbor. Introduce one added signal at a time. Keep the original source map and
separate rendered input. Use actual tokenizer lengths to preserve the literal
and discriminating context. Record omissions and reject an over-limit required
core. Authenticate reusable document vectors against exact rendered bytes,
profile, representation, and source. A new context recipe invalidates changed
vectors and affected candidate inventories. It need not recalculate unaffected
target descriptors. Respect the existing limits on examined targets and retained
pairs. Use the existing native candidate and storage path. An exact semantic
search utility can serve a bounded comparison of ranking behavior under the same
inputs. It does not replace native selection or prove semantic correctness.

**Ordering versus retrieval versus meaning.** Evaluate the inventory first on
source-defined targets. Report eligible target coverage and candidate recall at
the declared cutoff, then ordering and semantic selection separately. If enough
reviewed correct targets reach the list but their ordering limits the consumer,
compare Sentence Transformers `CrossEncoder.predict` over the same bounded
pairs. Qualify a specific pinned ranking checkpoint and pair-length behavior.
Record its score as a ranking signal. Keep lexical and dense input ranks, frozen
inventory and prior decision evidence. Use `CrossEncoderRerankingEvaluator`
only if its selected mode preserves the same prespecified candidate population
and failed/empty cases. Otherwise use current paired assessment over the retained
reports. If correct targets are absent, first improve context, registry coverage
or the relevant lexical route. Investigate `SparseEncoder` or
`MultiVectorEncoder` only after a recurring recall gap survives those changes
and their native storage, index and scoring consequences can be compared.
Review training, Matryoshka truncation or vector quantization only for a measured
quality or operating gap, with new representation identity and parity evidence.
[Sentence Transformers guide §§4–6, 11, 12.8](../../libraries/parsing/sentence-transformers.md) ·
[6.2.0 CrossEncoder source](https://github.com/huggingface/sentence-transformers/blob/v6.2.0/sentence_transformers/cross_encoder/model.py)

**Closure.** Keep richer context only where the paired textbook evidence shows
incremental correct target availability or usable ranking with preserved source
controls. Otherwise keep the current rendering and record the result. Within
the book, cover cross-chapter definition-use or reference links, competing same
surface symbols, and candidate-empty cases. Retain the same interpretation and
admission path regardless of ranking result. The rejected affine `X` link and
witnessed `Z` resolution test different outcomes. Document-to-document identity
remains deferred. [Frozen inventory and fusion](../../../python/corpus-structure/src/corpus_structure/semantic/contextual_retrieval.py) ·
[Relationship selection](../../../python/corpus-structure/src/corpus_structure/semantic/contextual_links.py)

<a id="PM2-10"></a>

## PM2-10 · Inspect an exact retained visual region when needed

Run only for a named visual ambiguity where the existing text, geometry and
candidate routes are insufficient. Start with a single exact retained crop and
one released question. Compare current Reader/geometry and, where relevant,
the existing Chandra candidate route on the same region. PM2-07's pinned d1
profile may use Choice, `box`, or bounded `boxes`. Bind the processor and
image/render identity, crop-to-source transform, native normalized coordinates,
presence, localization confidence and any count limit. Preserve original and
clipped coordinates when clipping is required. Withhold an exact source
relationship when the region cannot map to the selected visual product.
Keep source selection and publication under the existing visual owner.

**Activation and closure.** Require a reviewed source ambiguity where the route
adds distinct correct evidence and a wrong-crop and out-of-bounds control where
it refuses attribution. Preserve prior valid source reads. If the textbook
provides no suitable ambiguity or the route adds no useful evidence, keep the
profile off and record a trigger. Consider video or general visual replacement
only under separate selected scope and custody. [Visual evidence owner](../domain-model-alignment/visual-evidence.md) ·
[Chandra functional review](../../functional_reviews/chandra-2-post-nemotron_2026-11-08.md) ·
[Pinned d1 box implementation](https://huggingface.co/LiquidAI/d1-2B/blob/652f920e544ea37f81e4b0ce89b81d4ed0da90b1/box.py)
