# spaCy discovery: a reusable upstream language-characterization layer

**Interface-checked and Proposed · 2026-11-10.** Baseline: `0da4f8e614b162b791ac19dcb63f6cd33178377b`. This read-only contribution considers comprehensive, ordered upstream characterization of language, followed by composition into conceptual relations, labels, groups and analytics. The existing PM2 interventions supply useful failure evidence; they do not bound the target.

The complete 2,782-line [spaCy overview](../../../../libraries/parsing/spacy.md), including its advanced addendum, was read. Representative production consumers, installed spaCy source and model configuration, architecture owners and PM2 investigations were inspected. The selected project pins `spacy==3.8.18` and `en-core-web-sm==3.8.0`; installed metadata agrees. The assigned interpreter is Python 3.14.10. The original overview targets 3.8.16; its addendum and release-matched 3.8.18 checks qualify the older compatibility statements.

## Discovery judgment

**Proposed.** spaCy merits consideration as the common in-process substrate for several upstream characterization passes: source-aligned tokens and sentences; grammatical features and syntax; overlapping phrases and mentions; located constructions, cues and grammatical roles; and learned characterization where stock linguistic annotations are insufficient. Its value is the combination of shared representation, declarative matching, configurable components, trainable tasks and lifecycle support.

That placement would let conceptual consumers reuse explicit characterization products instead of reconstructing grammatical meaning independently. Missing characterization would extend its producing pass. This does not require a universal ontology, a custom workflow engine, or a durable store for every transient intermediate.

The important boundary is semantic. A dependency edge characterizes predicted syntax. A candidate span records a located possibility. A learned score records a model output under a particular task. None independently establishes a conceptual relationship, corpus identity, scientific claim or admitted interpretation.

## Existing integration and consequential evidence

**Implemented, inspected 2026-11-10.** [annotations.py](../../../../../python/corpus-structure/src/corpus_structure/ingest/annotations.py) already streams prepared Docs through the resident pipeline using `nlp.pipe(as_tuples=True, n_process=1)`. It retains lemma, POS, fine tag, morphology, dependency heads and sentence ownership with source, layout, component and configuration identities. It checks actual annotation completeness and refuses changed token coordinates. NER is excluded from this richer profile.

[annotation_views.py](../../../../../python/corpus-structure/src/corpus_structure/ingest/annotation_views.py) reconstructs consumer-local Docs without another model run. [annotation_rules.py](../../../../../python/corpus-structure/src/corpus_structure/methods/annotation_rules.py) prepares validated token, phrase and dependency patterns, named role bindings, native expansions and overlapping contiguous candidates. Its reconciled group mirrors the raw group, and its preset suggester is an integration seam; neither demonstrates a trained classifier.

[predicate_frames.py](../../../../../python/corpus-structure/src/corpus_structure/methods/predicate_frames.py) goes further: it locates predicates and grammatical roles, handles coordination, and constructs modality, negation, attribution and subordinate-clause cues. It also assigns readings such as definition, explanation, example and prescribed action. Thus the current module contains both reusable linguistic characterization and interpretation policy. The redesign question is where that boundary should move, rather than whether all existing frame logic should be generalized.

**Historical Tested evidence, 2026-11-09.** The [definition prerequisite investigation](../../../../design_review/evidence/2026-11-09_pm2-definition-prerequisite/README.md) found an orphan `p.` sentence and an `n` token labeled `ADV/cc`. A diagnostic punctuation split recovered one sentence boundary but not the declaration role. The [HanLP comparison](../../../../design_review/evidence/2026-11-09_pm2-definition-hanlp/README.md) recovered complementary grammatical information; its canonical layout still lost part of the parameter attachment. These findings support an upstream characterization responsibility.

The [matched interpretation investigation](../../../../design_review/evidence/2026-11-09_pm2-interpretation-pair/README.md) also retained host and referent misses when reviewed alternatives were supplied. Better candidate coverage alone therefore cannot settle every composition problem.

## Coherent capability leads

### 1. Shared characterization passes over a source-bound Doc

**Mechanism.** `Language.component`, `Language.factory`, extension attributes and configured component order can support independently understandable passes over the same Doc. `assigns`, `requires` and `retokenizes` describe dependencies; `analyze_pipes()` inspects those declarations, while actual annotation checks remain necessary. [Pipeline documentation](https://spacy.io/usage/processing-pipelines)

**Current use and new placement.** Existing preparation, annotation retention and reconstruction provide a strong foundation. Extend the upstream producer to own reusable phrase, clause, construction and cue characterizations. Keep transient spaCy objects local; emit independently owned, source-bound products for later composition.

**Countercondition.** Components whose natural scope is several blocks or a document graph should not be forced into token-local extension fields. Conversely, a semantic boundary need not introduce another process, persistence hop or materialization.

**Decisive question.** Which distinctions currently reconstructed by multiple consumers—predicate boundaries, grammatical participant candidates, coordination, quotation, modality and clause attachment—can be defined once as upstream products without embedding a particular conceptual interpretation?

### 2. Tokenization, segmentation and morphology as characterization contracts

**Mechanism.** Tokenizer exceptions and matching hooks, parser-respected sentence boundaries, `senter`, `sentencizer`, `Morphologizer`, rule/lookup lemmatization and `EditTreeLemmatizer` provide distinct alternatives. `Doc` accepts explicitly prepared words, spaces and annotations; exact character spans require token-aligned boundaries. [Doc API](https://spacy.io/api/doc)

**Current use and new value.** [sentences.py](../../../../../python/corpus-structure/src/corpus_structure/ingest/sentences.py) already tokenizes prose around protected math/reference atoms and constructs exact Docs. The target can retain that source fidelity while making segmentation and linguistic recipe selection explicit upstream responsibilities. Morphology can characterize tense, number, person and mood for later grouping and qualified-statement analysis.

**Countercondition.** Changing segmentation changes the pretrained model’s input distribution and downstream identities. General-purpose token splitting, retokenization and experimental parser `learn_tokens` are not harmless repairs. Formula atoms need their source-owned treatment.

**Decisive question.** What ordinary upstream policy represents technical identifiers and declaration punctuation correctly while preserving abbreviations, protected atoms and existing meaningful sentence boundaries?

### 3. Deterministic contextual annotation and terminology layers

**Mechanism.** `AttributeRuler.add(patterns, attrs, index)` applies contextual token corrections. `Matcher` handles linguistic predicates, morphology and bounded fuzzy comparison; `PhraseMatcher` recognizes terminology; `SpanRuler` writes overlapping results with configurable filtering. The latter defaults to replacing its destination, so keys and overwrite policy matter. [AttributeRuler](https://spacy.io/api/attributeruler), [SpanRuler](https://spacy.io/api/spanruler)

**Current use and new value.** Existing named patterns can become reusable characterization producers for naming constructions, comparison phrases, attribution markers, quantification, procedural language and terminology occurrences. Domain phrase inventories can supplement model discovery without becoming conceptual identity assertions.

**Countercondition.** Attribute correction mutates the analysis; it does not preserve competing hypotheses. A restored incumbent Doc must not be modified and then represented as its original evidence. Fuzzy lexical similarity supplies spelling tolerance, not semantic equivalence.

**Decisive question.** Which recurring characterization families have stable linguistic definitions suitable for authored patterns, and which require genuine contextual prediction rather than a growing list of exceptions?

### 4. Native syntax queries and grammatical-role characterization

**Mechanism.** `DependencyMatcher` supports direct dependencies, ancestry, siblings and token order. Native `children`, `ancestors`, `subtree`, `conjuncts`, noun chunks and span roots support phrase expansion and role discovery without constructing another syntax graph. Its operator distinctions matter: ancestry and surface precedence express different facts. [DependencyMatcher](https://spacy.io/api/dependencymatcher)

**Current use and new value.** Annotation rules and predicate frames already use several of these operations. An upstream pass could retain grammatical predicate/argument candidates, coordination relationships, subordinate clauses and scope-bearing constructions for many conceptual consumers.

**Countercondition.** The English model’s dependency scheme and UD are not interchangeable. A subtree can be discontinuous; a contiguous envelope can include unrelated text. Dense LCA matrices are unnecessary for ordinary path queries and scale quadratically.

**Decisive question.** Can one explicit grammatical-role product serve predicate framing, terminology attachment and procedural analysis while retaining discontinuity, unresolved attachment and provider-specific labels?

The resulting relations remain syntactic or attributed linguistic hypotheses. Promoting them to “defines,” “causes,” “requires” or corpus identity requires separately owned conceptual operations.

### 5. Overlapping characterization inventories with learned span labels

**Mechanism.** `Doc.spans`/`SpanGroup` preserve nested and overlapping spans. `SpanCategorizer` separates proposal from classification; `spancat` permits multiple labels, whereas `spancat_singlelabel` chooses at most one positive label. Native suggesters include selected n-gram lengths, ranges and preset upstream spans. [SpanCategorizer](https://spacy.io/api/spancategorizer)

**Current use and new value.** The existing raw candidate group and preset suggester offer a direct route to learned upstream characterization: qualifying clauses, referring expressions, definitional-content candidates, comparison spans or discourse markers. Independent layers can coexist over the same words.

**Countercondition.** Stock span input is a token start/end pair. It does not encode discontinuous arguments, relation endpoints, candidate provenance or alternative host bindings. Geometry deduplication must preserve those distinctions in the owning products.

**Decisive question.** Which useful characterization questions are genuinely span-label tasks, and what independent labels exist for them?

**Installed-source observation.** In `spacy/pipeline/spancat.py`, `predict()` returns candidate indices and scores; `set_candidates()` begins at line 362 and `set_annotations()` at line 380. Annotation assignment writes selected positive spans and corresponding scores. Ordinary output is not a complete retained candidate-score matrix. Preserve the earlier result deliberately when later consumers require rejected alternatives.

Standard `EntityRecognizer` is a separate upstream candidate for conventional names, organizations and bibliographic mentions. Its non-overlapping `Doc.ents` output and complete-entity objective are a poor universal representation for nested technical phrases or long role spans. Compare a useful independent NER layer with span-based alternatives rather than enabling the currently excluded model by default. The next question is whether its actual label inventory contributes reusable textbook characterizations that other producers miss. [EntityRecognizer](https://spacy.io/api/entityrecognizer)

### 6. Learned boundary discovery where candidate generation limits coverage

**Mechanism.** `SpanFinder` predicts span starts and ends, creates overlapping unlabeled candidates, and supports length and threshold controls. It can feed a preset-suggester span classifier. [SpanFinder](https://spacy.io/api/spanfinder)

**Current use and new value.** The inspected producer relies on linguistic patterns and other providers rather than a fitted spaCy span finder. A learned upstream proposer could discover long or novel expressions that fixed terminology and bounded n-grams fail to enumerate.

**Countercondition.** Candidate combinations can grow substantially; a finder cannot fix boundaries that the tokenizer cannot represent. Both SpanFinder and SpanCategorizer are documented experimental APIs. A broader candidate inventory also creates more false alternatives to interpret.

**Decisive question.** After accounting for token representability, which characterization families lose coverage at proposal generation rather than classification or conceptual attachment?

This should inform a coherent upstream inventory, rather than introducing a finder separately inside each downstream consumer.

### 7. Custom trainable characterization and relation tasks

**Mechanism.** `TrainablePipe` separates batch prediction, annotation assignment, initialization, supervision and loss. Factories can receive registered Thinc models, allowing task semantics to remain separate from encoder architecture. [TrainablePipe](https://spacy.io/api/pipe)

**Current use and new value.** Existing frame logic supplies identifiable linguistic questions. Where stock span labels cannot express a needed distinction, a custom task could characterize predicate–argument attachment, cue–clause attachment, mention relationships or discontinuous structures while reusing batching, training and packaging.

**Countercondition.** This removes generic training machinery, not task-specific modeling. Pair candidates, direction, negative examples, abstention, supervision and output meaning still need explicit contracts. A custom component does not become a general relation reasoner.

**Decisive question.** Is the residual problem naturally a pair or structured prediction task, or can stock span classification plus deterministic grammatical composition express it adequately?

The target should allow this extension without requiring every characterization to be a bespoke model. Learned attachments remain attributed proposals until the conceptual consumer applies its own meaning and acceptance rules.

### 8. Shared representations and deliberate model specialization

**Mechanism.** `Tok2VecListener`, transformer listeners, sourced components, freezing and listener replacement support shared or independent representations. Curated and Hugging Face transformer integrations are separately packaged alternatives. [Embeddings and transformers](https://spacy.io/usage/embeddings-transformers)

**Current use and new value.** Installed `en_core_web_sm` configuration shares tok2vec between tagger and parser; its NER has an internal encoder, and `senter` is disabled. The richer producer excludes NER. New characterization heads could share a deliberately selected encoder rather than independently encoding identical text.

**Countercondition.** Shared training couples tasks and freezing behavior. Static vectors, contextual representations and retrieval embeddings have different meanings. A transformer introduces subword alignment and bounded context; it does not supply whole-document conceptual understanding automatically.

**Decisive question.** Which characterization heads benefit from shared domain adaptation, and which require independent representations to preserve established linguistic behavior?

Static/floret vectors, `init vectors`, `BaseVectors` and pretraining remain candidates for lexical coverage or representation needs, not default redesign requirements. Custom vectors additionally require batching, device and serialization support. [BaseVectors](https://spacy.io/api/basevectors)

### 9. Passage characterization and canonical-identity proposals

**Mechanism.** `textcat` and `textcat_multilabel` classify the Doc being processed. `EntityRuler` IDs support deterministic alias labels; `EntityLinker` combines KB candidates, priors and contextual evidence, with configurable NIL rejection. [TextCategorizer](https://spacy.io/api/textcategorizer), [EntityLinker](https://spacy.io/api/entitylinker)

**Current use and new value.** Passage function is currently derived in predicate frames and compared through GLiNER/d1 operations. A separately trained characterization of source-bound passages could support inspection, analytical grouping and composition. Linker proposals could normalize technical mentions against an independently owned identifier inventory.

**Countercondition.** Passage labels do not locate their supporting spans. An alias ID, a coreference cluster, a KB suggestion and admitted corpus identity are distinct products. Repeated mathematical symbols require contextual bindings; a global alias table would erase scope.

**Decisive question.** Which useful labels characterize linguistic function independently of a downstream task, and which canonical-identity questions have sufficient candidates and stable authoritative identifiers?

Native `EntityLinker` expects recognized entities, so arbitrary overlapping mentions may need separate candidate handling rather than forced conversion into one non-overlapping entity sequence.

### 10. Training data and evaluation as reusable lifecycle capabilities

**Mechanism.** `Example` and alignment, `Corpus`/registered readers, augmenters, component scorers, `annotating_components`, configuration and packaging support a characterization training lifecycle. `DocBin` is useful corpus interchange; custom user data requires explicit preservation. [Training](https://spacy.io/usage/training), [DocBin](https://spacy.io/api/docbin)

**New value.** Independent characterization references could supervise several tasks over common source-bound examples. Evaluation can distinguish representable boundaries, proposed candidates, correct labels, linguistic attachment and subsequent conceptual correctness.

**Countercondition.** These supervision systems differ. Installed `spancat.py`, in `get_loss()` beginning at line 449, initializes candidate-label targets to zero and marks aligned positives; sparse positive labels do not automatically mean unknown. NER missing/outside/blocked states and incorrect spans have task-specific semantics. Multilabel text classification handles omitted labels differently. Gold preprocessing and ideal candidate inputs can conceal runtime losses.

**Decisive question.** What annotation-completeness policy makes each selected training task truthful, and which upstream predictions must be generated during training to match inference?

Augmentation must preserve source/label consistency. Experimental rehearsal and raw-text pretraining have potential adaptation uses, but neither substitutes for independent characterization references.

## Companion and operational screening

**Proposed, with compatibility unresolved unless stated.**

| Family | Potential contribution and screening disposition |
|---|---|
| `spacy-stanza`, specialized models, language extras and lookups | Alternative upstream linguistic producers for domains or languages. Stanza predictions remain Stanza’s; compare tokenization and annotation schemes before adoption. scispaCy’s biomedical specialization does not establish suitability for mathematical textbooks. [Stanza integration](https://github.com/explosion/spacy-stanza) |
| Experimental coreference, SpanResolver and character tokenization | Relevant to reference characterization, but `spacy-experimental` **0.6.4** declares `spacy>=3.3.0,<3.8.0`, excluding the selected core. This is a checked release constraint, not a claim that all future alternatives are unavailable. Existing Maverick evidence remains a meaningful comparator. [Tagged requirements](https://raw.githubusercontent.com/explosion/spacy-experimental/v0.6.4/requirements.txt) |
| `spacy-llm`, Hugging Face task wrappers | Possible producers for characterization unavailable from conventional models. Prompt/task/model separation is useful, but wrappers do not eliminate alignment, custody or interpretation responsibilities. Investigate only against a defined missing characterization. [LLM integration](https://spacy.io/usage/large-language-models) |
| `spacy-layout` | Native layout spans and tables could connect document structure to linguistic passes. Existing Docling/source custody means a second parsing route needs a concrete preservation or simplification benefit. [Layout integration](https://github.com/explosion/spacy-layout) |
| Arrays, bytes/JSON, `Span.as_doc`, `Doc.from_docs`, extensions/hooks | Useful transient interchange and model inputs. Explicit source maps remain necessary after slicing or concatenation; arrays are not full provenance, and hooks should not conceal altered semantics. |
| Streaming, memory and hardware | Existing `nlp.pipe` is appropriate. Use shared encoding and batching before adding residents/processes. `doc_cleaner` belongs after tensor consumers; `memory_zone()` invalidates created Docs, Tokens, Spans and Lexemes at exit. No such objects may escape. GPU extras require their own compatible environment. [Memory management](https://spacy.io/usage/memory-management) |
| CLI, Projects, logging, visualization and distribution | Config/data debugging, `find-function`, displaCy, evaluation, threshold selection and packaging can support concrete development needs. Projects/loggers should not create competing workflow/evidence owners. Hub publication is a separate distribution choice. Benchmarking becomes useful for a material execution question, not discovery ceremony. |

## Complete overview coverage disposition

“Base” refers to the original overview; “Addendum” to the November 5 supplement.

| Overview sections | Disposition in this discovery |
|---|---|
| Base §§1–2; Addendum §§6,12.1–12.4 | Shared runtime, overlapping layers, source alignment, extensions and interchange: leads 1–2,5 and screening. |
| Base §3; Addendum §§4.1,5.3 | Tokenization, sentence alternatives, morphology, lemma, contextual correction and learned merging: leads 2–3. |
| Base §4; Addendum §§3,5.1–5.2 | All matcher/ruler families, programmable candidates, traversal, LCA and structural operators: leads 3–6. |
| Base §5; Addendum §§2,4.2–4.3 | NER, overlapping extraction, proposal, classification, alias IDs, linking and supervision states: leads 5–6,9–10. |
| Base §6; Addendum §9 | Static/floret/custom vectors, tok2vec, both transformer paths, listeners and Thinc: leads 7–8. |
| Base §7; Addendum §7 | Factories, metadata, configuration, sourcing, custom trainable tasks and rehearsal: leads 1,7–8,10. |
| Base §8; Addendum §8 | Examples, storage, training, corpora, augmentation, scoring, CLI, Projects, handlers and loggers: lead 10 and screening. |
| Base §9 | Batching, multiprocessing, memory zones, cleaning and execution choices: screening. |
| Base §10; Addendum §§10–11 | Every named companion, visualization, Hub and installation-dependent feature: screening and lead 8. |
| Base §§11–14; Addendum §§1,12.5–12.6 and conclusion | Composition, retrieval boundary, release distinctions, custom-task scope and whole-chain evaluation: applied across the judgment and leads. |

**Recommended discovery priority, Proposed.** First define the reusable characterization products and their boundary with conceptual interpretation. Then assess native matching/span composition and learned span/pair tasks against those definitions. Encoder, companion and lifecycle choices should follow the information and supervision requirements. Comprehensive characterization is an extensible upstream responsibility; it does not mean running every available component on every input.

**Evidence limits and work performed.** Source inspection establishes selected mechanisms and contracts, not extraction efficacy. Historical PM2 results retain their original dates and bounded populations. No inference, probes, tests, installs or measurements ran; those are **not_run** under the assignment. Read-only `cat`, `sed`, `rg`, `git rev-parse HEAD` and `git status --short` completed successfully. The pre-existing untracked `docs/design_review/evidence/2026-11-10_schema-diagnostic-failure-boundaries/` folder was preserved. This topic research changed no product source; the coordinator integrates its documentation publication.
