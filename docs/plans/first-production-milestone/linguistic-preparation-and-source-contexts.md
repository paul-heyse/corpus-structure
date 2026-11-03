# M1 linguistic preparation and source contexts

**Proposed design and Planned work · 2026-11-03.** This companion develops M1-04 and M1-05.
The [coordinator](../first-production-milestone_2026-11-03.md) owns package state, opportunity
disposition, cross-package dependencies and assembled completion. Local conditions below describe
what the packages must deliver; they do not report implementation progress.

## Basis and current foundations

The [M1 proposal](../../target-pipeline-design/first-production-milestone.md),
[review O01/O05/O06](../../functional_reviews/m1-target-design_2026-11-03.md#O01) and
[GLiNER deployment](../../target-pipeline-design/gliner-deployment.md) supply the selected design.
Source inspected: `4a929aba`, including the operator-owned GLiNER reference at blob
`3daefdd5af8a3118f4767d9a558da4bc712cbacd` without changing it. Initially dirty, those same bytes
were committed externally as `4720b9a7` during authoring. By operator direction on
2026-11-03, prior UM functionality implementation and validation are complete; its remaining agent
assessment/followup stays outside this M1 work. M1's new annotations, contexts and routes still
need implementation and their own evidence.

The [semantic contract companion](semantic-contracts-and-evidence.md) owns shared field/anchor
meaning; [GLiNER/runtime](gliner-execution-and-cpu-runtime.md) consumes mapped contexts and admits
CPU work. [Assembly/interpretation](record-assembly-and-bounded-interpretation.md) consumes context
and annotation references, while [evaluation](evaluation-qualification-and-gap-driven-expansion.md)
owns independent region/role expectations. Context selection does not decide accepted records.

[D1](../../design/D1-knowledge-representation.md) owns source/evidence precision,
[D2](../../design/D2-schema-and-guidelines.md) the released contracts,
[D4](../../design/D4-method-catalog.md) the methods, and
[D6](../../design/D6-orchestration-metrics-policies.md) the run lifecycle. M1-00 resolves authority
changes; M1-01 supplies statistics-first English population and guidelines. Native selected PDF
views from the existing Docling/Nemotron path remain inputs. This work adds no alternate intake.

| Existing seam | Foundation conclusion and M1 change |
| --- | --- |
| [sentences.py](../../../python/corpus-structure/src/corpus_structure/ingest/sentences.py), `SentenceConfig`, `pipeline`, `TextLayout`, `prepare_layout`, `make_doc`, `split` | Reuse exact reconstruction, atom-preserving words/spaces, pinned model and process-resident loading. The current default excludes `ner` and `lemmatizer`; `split` returns sentence extents, not the proposed reusable annotation columns. |
| [proposals.py](../../../python/corpus-structure/src/corpus_structure/semantic/proposals.py), `NativeFrameSource`, `NativeProposalFrame`, `native_frame_entries` | Retain source/product/projection/recipe pins and separate source spaces. The frame presently restricts extra sources to distinct direct ancestors of the same product. Neighbors, captions, notes and arbitrary references need an explicit versioned extension rather than violating that validator. |
| [analytics.py](../../../python/corpus-structure/src/corpus_structure/semantic/analytics.py), `CapturedPacket`, `AnalysisScope` | Reuse scoped analytical input/Arrow ownership for bulk context relations and routing audits. Do not hydrate the whole corpus in Python to select small contexts. |
| [semantic.py](../../../python/corpus-structure/src/corpus_structure/orchestrate/semantic.py), `run_source_methods` | Preserve run/cut/source binding and terminal results. M1-06 supplies CPU admission; context construction does not create another task engine or its own pool. |

The focused foundation assessment favors extending the layout seam once: retokenizing per pack
would multiply work and risk divergent formula/reference boundaries. It also favors source-piece
contexts over whole-section input, because the latter obscures consulted evidence and consumes
candidate/length capacity. Sentence-only users keep their inexpensive contract. Rich annotations
and selected context are derived products, not a second canonical document or independent source
of semantic truth.

## M1-04: one reusable linguistic product

**Proposed.** Consume M1-02's settled linguistic/operation contract and the source/guideline pins
from M1-00/01. Producer integration waits for the admitted release; annotation design may proceed
once the fields and precision semantics are settled. M1-04 does not wait for every assembler or
the full context retrieval implementation.

Extend `SentenceConfig` or its release-bound profile into explicit sentence-only and richer
annotation selections. The richer profile enables/version-pins needed lemmatizer, tagger,
morphology and dependency components; do not assume annotations exist because a `Doc` object
exists. Record component/model/package versions, source/layout recipe and availability per needed
annotation. Model/package mismatch refuses deterministically, following existing `pipeline`.
Keep mathematical and reference atom roles authoritative even when a model assigns misleading
POS/dependency labels to their spellings.

Prepare `TextLayout` once for each source-bound block, create consumer-owned Docs with `make_doc`,
then pass `(Doc, source-context)` tuples through `Language.pipe(..., as_tuples=True)` with bounded
batches. spaCy skips tokenization for preconstructed Docs, allowing existing atom decisions and
offsets to survive. The source context carries stable source/block identity, not an ambient global
lookup. Persist needed token/sentence positions, lemma/POS/morphology, heads/dependency labels and
annotation availability with shared source references. Avoid copying the full passage into every
token, candidate or family record. A mutable `Doc` remains local to processing and is released
after extracting the needed columns/candidates.

This composition is supported by the [spaCy Language API](https://spacy.io/api/language#pipe)
and [pipeline guide](https://spacy.io/usage/processing-pipelines), refreshed through Context7 on
2026-11-03; repository orientation is [spaCy §§2–4, 9](../../libraries/parsing/spacy.md). Their
current documentation supplies capability orientation, while the selected exact product pins
still require local implementation checks. Use `Matcher`/`PhraseMatcher` for lexical/structural
cues and `DependencyMatcher` where a syntax pattern supplies attachment candidates. Overlapping
matches remain in `Doc.spans`/`SpanRuler`, whose [documented behavior](https://spacy.io/usage/rule-based-matching#spanruler)
allows overlap; do not force them through non-overlapping `Doc.ents` and lose nested terms or
numeric spans. A syntax match proposes a candidate, never an unconditional semantic gate.

The product's identity includes selected source/product/projection, layout and annotation recipe,
effective profile/model and relevant normalization. A sentence-only result cannot satisfy a
request for lemmas/dependencies. A changed model invalidates dependent annotations; a changed
extraction schema need not repeat unchanged annotation work. The GLiNER word splitter and
transformer tokenizer remain separately pinned interfaces; spaCy tokens are not their surrogate.
No new shared tensor cache or global mutable Doc cache follows from this reusable product.

### Completion conditions for M1-04

Focused checks extend sentence/layout and relevant native source preparation tests. Independent
expected offsets cover repeated spaces/newlines, repeated words at different positions, combining
marks, non-ASCII symbols, formula atoms, reference markers, paragraph/list/table-cell boundaries,
and exact `Doc.text` reconstruction. Prove that richer-profile annotations are actually available,
sentence-only consumers retain their declared behavior, a missing component is explicit, and
replay consumes the same source/profile identities. Native formula identity must survive a wrong
linguistic label. Boundary validation alone cannot establish linguistic accuracy.

Run the selected actual local spaCy model on retained statistics passages for annotation availability,
coordinate behavior and batching in the M1 preparation environment. This is a local provider check,
separate from deterministic layout tests and from GLiNER inference. Measure only claims needed for
the supported workload; no speed gain is established by using `pipe` alone. Stanza remains a
conditional comparison after a source-grounded annotation/attachment gap, not a dependency here.

## M1-05: bounded typed contexts, reversible maps and coverage-aware routing

**Proposed.** Consume M1-03's working anchor/observation contract and M1-04's working annotations;
use M1-01 source regions and supported family subsets. Settle context and routing shapes early
with M1-02. M1-07 later supplies model role observations; a structural/rule route can be designed
and tested before the model runs. Do not create a circular requirement that routing cannot exist
until every focused pack is qualified.

A context request supplies a selected source pin, family/pack purpose, initial native region,
missing roles/retrieval reason and released widening policy. The selector returns ordered source
pieces, source-view/native addresses and individual coordinate ranges, explicit synthetic pieces,
candidate/retrieval scope, exclusions and terminal selection reason. Preserve ancestry, selected
product/recipe digests and recognition health. Reuse the existing qualified frame interfaces where
their contract holds; extend them through a new supported frame/context version for non-ancestor
sources. Do not weaken the old direct-ancestor meaning or reinterpret a neighbor as an ancestor.

The normal access path selects structural relations in set-oriented queries before expensive
model calls. Project only needed columns; carry shared source references and compact annotation
positions. Cache selected immutable preparation only through existing dependency ownership with
a concrete consumer. Coherent contexts are the execution unit; a semantic distinction does not
force a separate task, query, transaction or materialized full-text copy.

| Family context | Smallest coherent initial region and expansion reason |
| --- | --- |
| Definition | Defined term with explicit defining passage and section/sense context; widen for a declaration or alias whose meaning is actually needed. |
| Qualified assertion | Clause/sentence or paragraph retaining predicate, participants and local qualification; include neighbors when condition/antecedent scope is unresolved. |
| Measurement/comparison | Value/property/referent/role and condition context; retrieve estimand/population/uncertainty declaration when absent locally rather than forcing the nearest noun. |
| Table assertion | Native cell and row key, full header path, caption, unit and applicable notes; preserve spanning and note scope rather than flattening reading order. |
| Formula/symbol | Existing formula occurrence plus separately addressed declarations/assumptions and scope; repeated `X` in another section is a different candidate binding. |

Widen by policy in this order: local neighbor, enclosing declaration/section, explicitly referenced
note/table/formula, then bounded targeted retrieval. An action records reason, candidate universe,
selected/consumed sources, exclusions, resource/time result and terminal reason. Failed retrieval
and absence within a searched scope may affect acceptance and therefore participate in invalidation.
Stop when required roles and faithful-reading conditions are established or the supported bound
is reached. Never silently use whole-document context after a failed bounded search. Missing
scope, conflicting candidates, unsupported source, resource limit and no match remain distinguishable.

### Coordinate contract

Serialization produces model input plus an interval map. Each non-synthetic interval refers to
one exact source piece, its coordinate space, source pin and mapping precision. Inserted header
labels/separators and punctuation are synthetic even if they resemble source text. Original table
header text can be included repeatedly but every inclusion points to its one original native
occurrence; equal strings elsewhere remain separate. If normalization is lossy or many-to-one,
retain the actual mapping relation and precision rather than claiming a reversible one-to-one map.

Literal model spans map back before normalization. A span crossing two source pieces yields a
legal multi-anchor set when the role permits, or remains unresolved/refused. Synthetic-only spans
cannot become source evidence. `SchemaTransformer.transform_record()` may append terminal
punctuation: M1-07 must return that preprocessing delta to this map owner or refuse such anchors.
Do not reconstruct another version of native preprocessing to guess its offsets. Public native
character offsets, model-word spans, subwords, spaCy tokens and recognized-text coordinates are
separate spaces with explicit conversions. An offset mismatch never triggers silent rounding.

### Routing and omission accounting

Run a coverage pass over every selected eligible source region using a modest high-recall role,
anchor and mention schema plus structural cues. Role classification is multi-label; mixed passages
need not choose one family. Table/formula/list structure can independently activate a pack even
when classification is uncertain. The compact focused packs consume applicable contexts and
missing-role requests. Unknown/mixed regions get a bounded broad fallback or explicit pending
disposition; no confidence threshold may silently erase them from denominators.

Record routing before invocation, inspected coverage after invocation, and source-grounded gaps
after assembly/interpretation through their distinct M1-02 meanings. An unrun pack is not an
inspected-empty result. A complete inspection with no candidates is not automatically no eligible
record in the original source. Native proposal suppression and downstream rejection remain
separate loss stages. Independently sample omitted/no-output regions under M1-01/D7; agreement
between routes cannot reveal a shared miss by itself. The broad pass does not promise encoding
reuse for a changed focused schema, because labels/descriptions and shared pools affect encoding
and proposals.

### Completion conditions for M1-05

Focused deterministic tests cover selecting neighboring estimand text, direct ancestors, note
scope restricted to declared cells, multi-level headers, formula/declaration separation, ambiguous
reference retrieval, repeated strings, synthetic separators/punctuation, lossy normalization,
unsupported coordinates and changed retrieval membership. A changed note or newly available
declaration must invalidate only the affected context/dependents under the declared dependency
scope; when dependency scope is uncertain, invalidate conservatively. Retain failed retrieval too.

Routing tests cover mixed labels, classification-unknown with structural trigger, all eligible
regions accounted for, skipped/not-run versus completed-empty, partial/truncated inspection and
bounded fallback exhaustion. Independently authored source-region expectations expose omitted
regions. Actual retained-source CPU role/focused passes are M1-07/provider evidence; deterministic
route fixtures alone do not qualify model recall. The assembled evaluator later measures
end-to-end omissions on the admitted population and cannot replace them with candidate counts.

## Conditional investigations and extension boundaries

| Trigger and question | Evidence and branches |
| --- | --- |
| A retained complete record repeatedly lacks a neighbor/declaration despite an initial local context | Inspect source and retrieval trace; compare bounded widening against existing context on complete records and qualifiers. Adopt the smallest successful policy; retain unresolved/outside-support when references remain ambiguous. Do not add a retrieval service by default. |
| Linguistic attachment errors persist after profile and context repair | Compare spaCy patterns/profile with Stanza on an isolated cohort using independent role/scope references and actual CPU/memory evidence. Keep spaCy if no whole-record benefit; promote a measured routed comparison only if its lifecycle burden is justified. |
| Table serialization erases a necessary relation or precise source location | Demonstrate native row/header/note assembly versus changed serialization. Prefer native structural joins and multi-anchor evidence; reject unsupported layouts rather than fabricating continuous text. |
| Broad routing loses focused candidates through schema competition | M1-07 compares broad/compact/routed schemas on the same source region and complete records, retaining pool/window diagnostics. Separate passes are acceptable when needed; changed schema invalidates encoding assumptions. |

No general coreference model, multilingual pipeline, alternative intake, generative extractor or
custom tokenizer is selected. New source/family capabilities must declare their source pieces,
required annotation profile and routing semantics under the existing owners. All tests and local
provider checks here are **Planned**; for plan authoring, inference, product tests and database
operations are **not_run**. Current states and future receipt links belong to the coordinator.
