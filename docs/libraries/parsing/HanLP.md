# HanLP — Comprehensive Python Library Overview

Research date: November 8, 2026 | Current stable version: 2.1.7 (October 25, 2026) | License: Apache 2.0 for the library; separate terms for pretrained models and hosted services

HanLP (Han Language Processing) is a multilingual natural-language-processing framework designed for both research and production-oriented linguistic analysis. Its defining capability is the ability to perform multiple complementary NLP tasks—including morphological analysis, syntactic parsing, named entity recognition, semantic role labeling, and semantic graph construction—within a unified modeling framework.

Although HanLP originated from Chinese-language NLP research, its modern Python implementation, HanLP 2.1, provides substantial English-language support, as well as multilingual models built using resources including Universal Dependencies and OntoNotes.

The project advertises support for ten jointly modeled tasks across 130 languages. This is an aggregate statement about its multilingual resources and model capabilities, not a guarantee of equally strong coverage for every task in every language. In particular, its original OntoNotes training data cover English, Chinese, and Arabic, so predictions for certain tasks in other languages depend on cross-lingual generalization.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Primary resources:

- Repository: [https://github.com/hankcs/HanLP](https://github.com/hankcs/HanLP?utm_source=chatgpt.com)
- Documentation: [https://hanlp.hankcs.com/docs/](https://hanlp.hankcs.com/docs/?utm_source=chatgpt.com)
- Python API reference: [https://hanlp.hankcs.com/docs/api/hanlp/index.html](https://hanlp.hankcs.com/docs/api/hanlp/index.html?utm_source=chatgpt.com)
- Package releases: [https://pypi.org/project/hanlp/](https://pypi.org/project/hanlp/?utm_source=chatgpt.com)
- Model catalog: [https://hanlp.hankcs.com/docs/api/hanlp/pretrained/index.html](https://hanlp.hankcs.com/docs/api/hanlp/pretrained/index.html?utm_source=chatgpt.com)

## 1. Architectural orientation

HanLP occupies a useful position between libraries providing individual linguistic models and frameworks that require each processing component to be assembled independently.

Its central architectural idea is that related linguistic tasks can be represented as different supervised predictions over a shared contextual representation of a sentence.

A typical analysis progresses conceptually from text to multiple linguistic structures:

Input sentences or token sequences

Single-language or multilingual text

Contextual encoder

Transformer representations, such as XLM-R or a language-specific encoder

Lexical

Tokens, lemmas, POS, morphology

Syntactic

Dependencies, constituency

Semantic

NER, SRL, semantic graphs

Structured linguistic annotations

Token-aligned arrays, labeled spans, dependency relations, constituent trees and semantic graphs

This diagram describes HanLP's multitask architecture conceptually. Not every pretrained model implements every task, and some capabilities use separate models rather than the shared encoder.

Three architectural choices are particularly important.

Multitask rather than isolated inference. A multitask model can share an encoder and coordinate different prediction heads, avoiding the need to invoke a separate transformer for each linguistic task. This may reduce repeated computation and simplify token alignment, although the benefit depends on the model, selected tasks, and batching.

Native local inference alongside hosted inference. The Python package provides local models and training components. A separate lightweight REST client exposes a remotely hosted API with a similar result structure. They are not interchangeable in licensing, operational requirements, model availability, or input preprocessing.

Structured analysis rather than just embeddings. HanLP produces explicit grammatical and semantic objects. These can be inspected, validated, transformed into graph structures, or combined with other models, unlike opaque sentence embeddings alone.

The distinction matters: HanLP is particularly valuable when the structure of language is the desired result rather than merely a text classification or vector representation.

## 2. Core capability map

HanLP covers a much larger range of linguistic structure than tokenization and NER alone.

| Capability                              | Output and significance                                                                                     |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Tokenization (`tok`)                    | Word boundaries and tokens; supports different segmentation standards and externally supplied tokenization. |
| Lemmatization (`lem`)                   | Canonical lexical forms, enabling morphological normalization and vocabulary consolidation.                 |
| Part-of-speech tagging (`pos`)          | Word-level grammatical categories; supports language-specific and universal tag schemes.                    |
| Morphological features (`fea`)          | Universal Dependencies features such as number, tense, case, mood, and other grammatical properties.        |
| Named entity recognition (`ner`)        | Typed entity mentions, with token spans and configurable model-specific entity label sets.                  |
| Dependency parsing (`dep`)              | Labeled grammatical head–dependent relationships forming a dependency tree.                                 |
| Constituency parsing (`con`)            | Hierarchical phrase structure, including noun phrases, verb phrases, clauses, and nesting.                  |
| Semantic role labeling (`srl`)          | Predicate–argument structures describing participants, events, modifiers, and their semantic roles.         |
| Semantic dependency parsing (`sdp`)     | Directed, labeled semantic graphs that can represent multiple semantic parents for a token.                 |
| Abstract Meaning Representation (`amr`) | Conceptual semantic graphs representing events, entities, roles, and relations more abstractly than syntax. |

These are documented task families, not a promise that every checkpoint exposes all ten simultaneously. The precise output contracts are described in HanLP's data-format specification.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+3



The library also contains standalone components for sentence boundary detection, text classification, semantic textual similarity, and specialized tokenization and tagging. Additional services—particularly coreference resolution, summarization, and keyphrase extraction—are exposed through HanLP's REST interface but must not be mistaken for guaranteed local pretrained capabilities.

## 3. English-language models and pretrained model selection

This is an especially important distinction for current HanLP users: English support is not limited to the older XLM-R multilingual checkpoints.

HanLP introduced English-specific multitask checkpoints using ModernBERT in version 2.1.0, released December 29, 2024, followed by a ModernBERT Large checkpoint in January 2025.

The official model catalog identifies two English-specific checkpoints:

- `EN_TOK_LEM_POS_NER_SRL_UDEP_SDP_CON_MODERNBERT_BASE`
- `EN_TOK_LEM_POS_NER_SRL_UDEP_SDP_CON_MODERNBERT_LARGE`

Both combine an English-focused ModernBERT encoder with decoders for tokenization, lemmatization, POS tagging, named entity recognition, semantic role labeling, Universal Dependencies parsing, semantic dependency parsing, and constituency parsing.

The models require `transformers>=4.48`, according to the published model entries.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+1



### 3.1 English model performance

The official catalog reports the following selected scores. These are upstream checkpoint evaluations, not independently reproduced results or benchmarks against newer alternative frameworks.

| Metric                                | ModernBERT Base | ModernBERT Large |
| ------------------------------------- | --------------- | ---------------- |
| Tokenization F1                       | 99.87%          | 99.87%           |
| POS accuracy                          | 98.00%          | 98.08%           |
| Lemmatization accuracy                | 99.52%          | 99.46%           |
| Named entity F1                       | 84.67%          | 87.11%           |
| Dependency UAS                        | 95.09%          | 95.35%           |
| Dependency LAS                        | 93.21%          | 93.50%           |
| Constituency labeled F1               | 88.71%          | 89.76%           |
| Semantic role labeling, end-to-end F1 | 92.57%          | 95.86%           |
| Semantic dependency DM labeled F1     | 93.08%          | 93.35%           |
| Semantic dependency PAS labeled F1    | 94.65%          | 94.80%           |
| Semantic dependency PSD labeled F1    | 83.36%          | 83.71%           |

Source: official English model entries, [https://hanlp.hankcs.com/docs/api/hanlp/pretrained/mtl.html](https://hanlp.hankcs.com/docs/api/hanlp/pretrained/mtl.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



These scores support several observations.

First, the Large model shows larger reported gains in NER and SRL than in tokenization, lemmatization, or dependency parsing. The relative value of the larger encoder is therefore task-dependent.

Second, the particularly strong SRL results make the English multitask models worth investigating where structured predicate–argument information is important. The reported end-to-end SRL evaluation is much more informative than predicate identification accuracy alone.

Third, the three semantic dependency representations—DM, PAS, and PSD—are separately evaluated. They should not be interpreted as interchangeable names for a single semantic graph. Their annotation schemes encode different linguistic analyses.

Finally, the fact that the English checkpoints use ModernBERT does not mean they inherit the performance of unrelated ModernBERT models on every task. The relevant unit of comparison is the trained HanLP encoder-plus-decoder checkpoint, evaluated on the same datasets and annotation schemes as alternatives.

### 3.2 Multilingual and language-specialized alternatives

The current catalog includes several other model families.

| Family                   | Encoder / specialization                | Consequential distinction                                                                                                   |
| ------------------------ | --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| English MTL              | ModernBERT Base and Large               | English-specific joint linguistic analysis; no separate morphological-feature (`fea`) task advertised in these identifiers. |
| Multilingual MTL         | XLM-R Base                              | Broad linguistic coverage trained using Universal Dependencies and OntoNotes.                                               |
| Smaller multilingual MTL | Multilingual MiniLM variants            | More compact shared-encoder alternatives for multilingual workloads.                                                        |
| Chinese MTL              | ELECTRA and ERNIE variants              | Chinese-specific models, including different corpus and dependency-annotation standards.                                    |
| Japanese MTL             | Japanese character-level BERT           | Japanese-specific tokenization, tagging, parsing, and related annotations.                                                  |
| Classical Chinese MTL    | Ancient Chinese BERT                    | Specialized classical-language vocabulary, segmentation, POS schemes, and syntax.                                           |
| English AMR              | BART-based and graph-pretrained parsers | Separate semantic graph models rather than a decoder automatically included in the ModernBERT MTL checkpoint.               |

The catalog distinguishes open-corpus and closed-corpus Chinese checkpoints. Those distinctions matter for reproducibility, model provenance, and licensing, not just reported accuracy.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+1



Model-selection implications: For English, the ModernBERT checkpoints are the most directly relevant fully integrated MTL options in the published catalog. XLM-R and MiniLM remain relevant where cross-language consistency or broader language coverage matters. Separate specialized models are appropriate when only a narrow task is required or a different modeling objective provides materially better results.

HanLP's catalog should not be treated as an automatically updated registry of every recent Hugging Face architecture: using a newer encoder such as a future ModernBERT derivative requires compatible model integration, trained decoders, and validation. Installing HanLP 2.1.7 does not itself upgrade the historical pretrained checkpoint weights.

## 4. Input contracts and structured output

HanLP's data model is a consequential part of its architecture. It exposes linguistic annotations in a normalized `Document` container, making it possible to combine outputs without forcing every consumer to understand a different neural model's native tensors.

### 4.1 Local inference is sentence-oriented

A local multitask model accepts either a sentence or a batch of sentences. If tokenization is included, sentences are generally strings. Otherwise, inputs are pretokenized sequences.

A distinction that is easy to overlook: passing an entire multiparagraph document to a local model does not automatically provide the same document processing as the REST service. The local documentation explicitly requires sentence segmentation before model inference.

An illustrative English inference example:

```
import hanlpmodel = hanlp.load(    hanlp.pretrained.mtl    .EN_TOK_LEM_POS_NER_SRL_UDEP_SDP_CON_MODERNBERT_BASE)sentences = [    "The board approved the acquisition.",    "The analysts reviewed the financial statements.",]doc = model(    sentences,    tasks=["tok", "pos", "ner", "dep", "srl"],)print(doc.to_json())
```

The model resolves supported task dependencies and produces sentence-aligned annotations. The precise keys are determined by the loaded checkpoint and its task configuration.

For already-tokenized text, HanLP documents `skip_tasks="tok*"` as the mechanism for bypassing tokenization in compatible multitask models. This is useful when token boundaries must match upstream document annotations, although external tokenization must be compatible with the selected taggers and parsers.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+1



Reference: [https://hanlp.hankcs.com/docs/data_format.html](https://hanlp.hankcs.com/docs/data_format.html?utm_source=chatgpt.com)

### 4.2 Annotation structure and indexing

The output is not one homogeneous list of entities or relations. Each task carries its own structural contract.

| Output              | Representation                                  | Important semantics                                                                    |
| ------------------- | ----------------------------------------------- | -------------------------------------------------------------------------------------- |
| `tok`               | Sequence of tokens                              | Word boundaries govern alignment for downstream token-indexed results.                 |
| `pos`, `lem`, `fea` | Arrays aligned to tokens                        | Index-based lexical and morphological attributes.                                      |
| `ner`               | `(mention, label, start, end)`                  | Token-span boundaries, with an exclusive end index. Not necessarily character offsets. |
| `dep`               | `(head, relation)` per token                    | Root head is `0`; nonroot head indices are one-based.                                  |
| `srl`               | Predicate-specific collections of labeled spans | Multiple predicates may generate overlapping argument structures.                      |
| `sdp`               | Multiple `(head, relation)` edges per token     | Semantic graphs may have more than one parent, or no parent, unlike dependency trees.  |
| `con`               | Nested constituents                             | Hierarchical syntactic groups, not a flat span list.                                   |
| `amr`               | Semantic graph / logical triples                | Conceptual relations do not necessarily correspond one-to-one with tokens.             |

These conventions make it possible to translate dependency outputs into graph edges and SRL outputs into event-centered structures, but only after preserving their distinct indexing and semantic assumptions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+1



Several distinctions are particularly important:

- Token indices versus source offsets. NER spans ordinarily refer to token boundaries. If downstream systems require offsets in the original text, an explicit token-to-character alignment must be preserved or reconstructed. The standalone transformer tokenizer also supports token span output through `config.output_spans`.
- Tree versus graph. A grammatical dependency parse conventionally identifies one syntactic head per nonroot token. Semantic dependency parsing can attach several labeled heads to a word, so it should not be forced into a tree without potentially losing information.
- Predicate-specific role structures. Semantic role labels such as `ARG0`, `ARG1`, and `ARGM-TMP` are defined relative to a predicate and annotation convention. They do not constitute a universal ontology of actor, object, or time.
- Annotation schemes are part of the model contract. HanLP exposes different POS conventions, NER ontologies, and dependency formalisms; similarly named outputs can differ semantically.

### 4.3 `Document` as an interoperability boundary

The `hanlp_common.document.Document` class is a dictionary-like container with more than basic JSON serialization.

Its documented functionality includes:

- `to_dict()` and `to_json()` for interoperable structured results.
- `to_conll(...)` to project token, lemma, POS, morphology, syntactic dependencies, and semantic dependencies into CoNLL-style structures.
- `squeeze(i)` to select a sentence from a batch-oriented document.
- `get_by_prefix(...)` for finding a task's output under a qualified key.
- `pretty_print()` and `to_pretty()` for inspecting linguistic annotations.
- `translate(lang, ...)` for translating annotation labels in place—not translating the original text.

`to_conll` is a particularly useful integration mechanism because CoNLL and CoNLL-U are widespread formats for dependency and morphological annotations. The conversion only carries the representable selected fields; richer structures such as AMR, constituency and full predicate–argument information still require their own serialization if needed.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Reference: [https://hanlp.hankcs.com/docs/api/common/document.html](https://hanlp.hankcs.com/docs/api/common/document.html?utm_source=chatgpt.com)

One important engineering qualification is that the `Document` object is a convenient shared representation, not a complete provenance or cross-document identity system. Persistent consumers must independently retain sentence IDs, original text offsets, model/version identifiers, and document-level grouping where those are required.

## 5. Multitask execution, dependencies, and customization

The `MultiTaskLearning` framework is the most architecturally distinctive portion of HanLP 2.

### 5.1 Shared encoder and differentiated task heads

The framework combines a common embedding/encoder with specialized task modules. Transformer representations can be reused across different decoders, while the decoders retain different prediction mechanisms.

The approach goes beyond naïvely placing unrelated models behind one API. It supports:

- Multiple tasks trained against a shared encoder.
- Explicit task dependencies, such as predictions that require the output of an earlier task.
- Task-specific consumption of contextual representations.
- Task-specific optimization configuration.
- Joint evaluation and training orchestration.

The shared encoder is especially relevant for workloads needing several distinct syntactic and semantic annotations. The gain is conditional: decoding itself still incurs work, dependency ordering can affect scheduling, and the memory required for all task heads and hidden states must be considered.

### 5.2 Selecting and skipping tasks

`MultiTaskLearning.predict` supports `tasks` and `skip_tasks`. The task graph can resolve prerequisite tasks automatically, while `skip_tasks` is also used for supplying upstream annotations such as external tokenization.

The model supports removing registered tasks, illustrated in the API with `del mtl["dep"]`. This can reduce the set of available predictions, but it should not be confused with dynamically retraining the remaining decoders or changing the learned shared representation.

A practical conceptual distinction:

- Selecting tasks determines which supported predictions are requested.
- Resolving dependencies determines which prerequisite computations remain necessary.
- Skipping tasks can replace a stage with supplied inputs where the model supports it.
- Removing a task changes the registered task set.

These distinctions matter when optimizing inference or integrating separately produced annotations.

Reference: [https://hanlp.hankcs.com/docs/api/hanlp/components/mtl/mtl.html](https://hanlp.hankcs.com/docs/api/hanlp/components/mtl/mtl.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



### 5.3 Task-specific transformer layer mixing

The `Task` abstraction exposes a `scalar_mix` configuration, allowing task modules to construct learned mixtures of contextual hidden layers instead of necessarily consuming only the transformer's last layer.

This is significant because different linguistic tasks may benefit from different representational depths. Fine-grained grammatical features, syntactic dependencies, and higher-level semantic information need not draw on identical layers.

The interface also exposes `use_raw_hidden_states`, enabling task-specific handling of transformer outputs.

Architectural consequence: A shared encoder need not force every task into the same feature representation. HanLP's design retains opportunities for specialized task behavior without duplicating the whole encoder.

### 5.4 Training new task combinations

`MultiTaskLearning.fit` accepts an encoder and a dictionary of `Task` instances. Its training configuration includes separate encoder and decoder learning rates, warmup, gradient accumulation, gradient clipping, early stopping, and task-sampling parameters.

The `Task` base class supports:

- Independent training, development, and test resources.
- Sampling configuration and task dependencies.
- Different learning rates or separate optimizers.
- Task-specific dataloaders, model construction, loss and metric implementations.
- Transformations that allow a task to consume annotations produced by another task.

The multitask training interface exposes a `tau` parameter for tempering task-data sampling; this is relevant when training datasets vary significantly in size. It should not be interpreted as a guaranteed solution to negative transfer or class imbalance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+1



References:

[https://hanlp.hankcs.com/docs/api/hanlp/components/mtl/tasks/task.html](https://hanlp.hankcs.com/docs/api/hanlp/components/mtl/tasks/task.html?utm_source=chatgpt.com)

[https://hanlp.hankcs.com/docs/api/hanlp/components/mtl/mtl.html](https://hanlp.hankcs.com/docs/api/hanlp/components/mtl/mtl.html?utm_source=chatgpt.com)

The practical value of this extensibility is that new supervised linguistic tasks can, in principle, be integrated within a shared modeling and prediction framework. The boundary is equally important: creating a new `Task` requires appropriate labeled data, decoder logic, objective functions, alignment conventions, and evaluation. It is not an API for automatically learning arbitrary new semantic relations without supervision.

## 6. Specialized components beyond the multitask models

The multitask checkpoints are not the entirety of HanLP. Several useful capabilities reside in dedicated components, pretrained models, or lower-level modeling interfaces.

### 6.1 Sentence boundary detection

HanLP provides `NgramSentenceBoundaryDetector`, as well as the pretrained multilingual `UD_CTB_EOS_MUL` sentence-boundary model trained on combined Universal Dependencies and Chinese Treebank data.

This addresses a requirement of local sentence-level inference: document text must be segmented before being passed to most local parsers.

Sentence segmentation is not a trivial preprocessing operation. An incorrect boundary can separate a predicate from its arguments, truncate a syntactic constituent, or change which entity mentions are available to a sentence-level model. Consequently, sentence segmentation quality affects the semantics of later annotations.

The documented n-gram detector is punctuation-sensitive. It should not be assumed to reliably recover sentence structure from arbitrary unpunctuated transcripts or heavily damaged OCR output.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Reference: [https://hanlp.hankcs.com/docs/api/hanlp/components/eos.html](https://hanlp.hankcs.com/docs/api/hanlp/components/eos.html?utm_source=chatgpt.com)

### 6.2 Tokenization with dictionary constraints

`TransformerTaggingTokenizer` implements transformer-based word-boundary prediction and includes two distinct dictionary mechanisms.

`dict_force` matches dictionary entries against the original input and applies them before model prediction. Matched spans can be protected from further segmentation.

`dict_combine` operates on the tokenizer's predicted output, merging matching sequences after inference.

Both use longest-prefix matching, but they serve substantially different purposes.

The first can impose high-priority lexical boundaries. The second can retain the model's initial segmentation while consolidating selected phrases. HanLP explicitly cautions that indiscriminate forced matching can degrade results, including when an early match prevents a better segmentation.

The component also exposes token spans and training controls involving character-level processing, tagging schemes, maximum sequence lengths, CRF decoding, and transformer layer selection.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Reference: [https://hanlp.hankcs.com/docs/api/hanlp/components/tokenizers/transformer.html](https://hanlp.hankcs.com/docs/api/hanlp/components/tokenizers/transformer.html?utm_source=chatgpt.com)

These mechanisms can replace some custom dictionary-first preprocessing logic, but they are specific to supported tokenizer implementations. They should not be assumed available with identical behavior in every pretrained multitask checkpoint.

### 6.3 Named entity recognition with gazetteer correction

HanLP includes a standalone `TransformerNamedEntityRecognizer` with a transformer tagger, linear output layer, and optional conditional random field (CRF).

A less obvious feature is its ability to combine statistical entity predictions with dictionary-based corrections:

- `dict_whitelist` associates known entity strings with types and can override model outputs.
- `dict_blacklist` suppresses known unwanted entity predictions.

This supports scenarios where reliable vocabulary for particular entity classes exists, but training a new model for every rare or specialized name would be undesirable.

The tradeoff is that a dictionary match does not perform semantic disambiguation. A surface form that is an entity in one context may be ordinary language in another. The correction layer therefore introduces an explicit precision–recall and domain-generalization tradeoff.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+1



Reference: [https://hanlp.hankcs.com/docs/api/hanlp/components/ner/transformer_ner.html](https://hanlp.hankcs.com/docs/api/hanlp/components/ner/transformer_ner.html?utm_source=chatgpt.com)

### 6.4 Independent syntactic and semantic modeling components

HanLP exposes model architectures beyond the packaged MTL decoders.

Its component reference includes biaffine dependency parsers, biaffine semantic dependency parsers, CRF-based constituency parsing, span-ranking and BIO-style semantic role labelers, transformer sequence taggers, RNN taggers, and biaffine NER implementations.

These are useful research and extension surfaces because they permit different decoder architectures to be studied or trained independently.

For example, a dependency parser predicts directed head–dependent links, whereas a span-based constituency parser must recover a hierarchical segmentation of the sentence. SRL can instead be formulated as selecting and labeling spans associated with candidate predicates.

These differences are not merely implementation details: they change output expressiveness, complexity, supervision requirements, and error modes.

API index: [https://hanlp.hankcs.com/docs/api/hanlp/index.html](https://hanlp.hankcs.com/docs/api/hanlp/index.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



### 6.5 Abstract Meaning Representation: parsing and generation

HanLP includes local AMR models that deserve consideration separately from the main multitask predictors.

AMR parsing

AMR converts a sentence into a labeled conceptual graph, often using PropBank-style predicate concepts and relations such as `:ARG0` and `:ARG1`.

Its purpose is to abstract away from some surface grammatical distinctions while representing entities, events, semantic roles, and relations.

The documented models include:

| Model                          | Architecture / scope                                                                                                      |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| `AMR3_SEQ2SEQ_BART_LARGE`      | BART-based sequence-to-sequence AMR 3.0 parsing.                                                                          |
| `AMR3_GRAPH_PRETRAIN_PARSER`   | BART-based parser with additional graph pretraining.                                                                      |
| `MRP2020_AMR_ENG_ZHO_XLM_BASE` | English–Chinese multilingual AMR parser using a permutation-invariant approach; English input requires tokens and lemmas. |
| `MRP2020_AMR_ZHO_MENGZI_BASE`  | Chinese-focused semantic parser.                                                                                          |

The official documentation reports Smatch F1 scores of 83.30 for the standard BART parser and 84.0 for the graph-pretrained parser in its reproduced evaluation. These are historical, model-specific results.

It explicitly notes that the two AMR 3.0 parsers do not perform wikification. This matters when the goal extends beyond identifying semantic concepts to linking them to external knowledge-base identifiers.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Reference: [https://hanlp.hankcs.com/docs/api/hanlp/pretrained/amr.html](https://hanlp.hankcs.com/docs/api/hanlp/pretrained/amr.html?utm_source=chatgpt.com)

AMR-to-text generation

HanLP also publishes `AMR3_GRAPH_PRETRAIN_GENERATION`, a BART-based model for producing natural-language realizations from AMR graphs.

This is an unusual companion capability: the same semantic representation can be used as a target for parsing and as a source for text generation.

Possible general applications include semantic representation inspection, controlled language generation, and evaluating whether important meaning survives transformations. However, parsing followed by generation is not guaranteed to reproduce the original sentence exactly or preserve every distinction.

Reference: [https://hanlp.hankcs.com/docs/api/hanlp/pretrained/amr2text.html](https://hanlp.hankcs.com/docs/api/hanlp/pretrained/amr2text.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



AMR models have their own dependency requirements, provided through `hanlp[amr]`, and should not be assumed to load as just another ModernBERT multitask head.

### 6.6 Classification, similarity and embedding resources

HanLP contains additional components for transformer-based text classification and semantic textual similarity. Its model catalog also includes pretrained resources for word2vec, GloVe, fastText, and masked language modeling.

These facilities broaden the framework's usefulness beyond explicit linguistic structures, but they have a different capability profile:

- Text classification produces labels from a trained category set.
- Semantic textual similarity produces a score for a text pair.
- Word and contextual embeddings provide numerical representations for downstream modeling.

For example, the local pretrained STS catalog includes `STS_ELECTRA_BASE_ZH`, a Chinese ELECTRA-based similarity regressor trained using STS corpora.

A local semantic-similarity model is not necessarily suitable as a modern general-purpose English retrieval embedding model. The model's training task, input format, language, and retrieval evaluation must be considered separately.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



References:

[https://hanlp.hankcs.com/docs/api/hanlp/pretrained/sts.html](https://hanlp.hankcs.com/docs/api/hanlp/pretrained/sts.html?utm_source=chatgpt.com)

[https://hanlp.hankcs.com/docs/api/hanlp/pretrained/index.html](https://hanlp.hankcs.com/docs/api/hanlp/pretrained/index.html?utm_source=chatgpt.com)

## 7. Composition: pipeline orchestration versus shared multitask inference

HanLP has two meaningfully different ways of combining components.

| Aspect              | `MultiTaskLearning`                         | `Pipeline`                                              |
| ------------------- | ------------------------------------------- | ------------------------------------------------------- |
| Composition         | Shared encoder with registered task modules | Ordered sequence of independent callable components     |
| Dependencies        | Explicit task dependency relationships      | Input/output key routing between pipeline stages        |
| Computation         | Can reuse encoder computation across tasks  | May invoke each component's own model separately        |
| Extension           | Custom `Task` implementations and decoders  | Append or insert compatible callables                   |
| Best conceptual use | Jointly modeled linguistic analysis         | Composition of separately implemented processing stages |

`hanlp.pipeline()` constructs a `Pipeline` that supports `append(component, input_key, output_key, **kwargs)`. The `input_key="*"` convention passes previous outputs as a `Document`.

However, the main API documentation explicitly describes this pipeline abstraction as intended for bundling Keras components and directs users toward `MultiTaskLearning` for PyTorch components. Therefore, it should not be assumed that arbitrary Torch models can be combined in a pipeline with the same benefits as HanLP's native MTL design.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+1



References:

[https://hanlp.hankcs.com/docs/api/hanlp/components/pipeline.html](https://hanlp.hankcs.com/docs/api/hanlp/components/pipeline.html?utm_source=chatgpt.com)

[https://hanlp.hankcs.com/docs/api/hanlp/hanlp.html](https://hanlp.hankcs.com/docs/api/hanlp/hanlp.html?utm_source=chatgpt.com)

The broader architectural lesson is that output composition and model-level computation sharing are different properties. HanLP supports both patterns, but choosing between them affects encoder duplication, training coupling, inference execution, and output-alignment obligations.

## 8. REST API and additional hosted NLP capabilities

HanLP provides a separate Python package, `hanlp_restful`, for communicating with a hosted HanLP service.

This is important because the REST interface exposes additional functions that are not necessarily represented by downloadable, locally executable models in the native Python catalog.

### 8.1 Python client interface

```
from hanlp_restful import HanLPClientclient = HanLPClient(    "https://hanlp.hankcs.com/api",    auth="YOUR_API_KEY",    language="en",)doc = client.parse(    text="The board approved the proposal.",    tasks=["tok", "pos", "ner", "dep", "srl"],)
```

Unlike local multitask inference, `parse` accepts complete raw documents, lists of sentences, and explicitly tokenized sentences. The hosted server can perform sentence segmentation itself.

The client exposes `tasks`, `skip_tasks`, and `language`, as well as connection configuration including timeout and TLS certificate verification. A valid service key may be required, and the supported languages and functionality depend on the particular server.

Reference: [https://hanlp.hankcs.com/docs/api/restful.html](https://hanlp.hankcs.com/docs/api/restful.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+1



### 8.2 Hosted task families

The documented Python client includes functions beyond the main local multitask catalog.

| REST functionality                | Output or behavior                                                 |
| --------------------------------- | ------------------------------------------------------------------ |
| `coreference_resolution`          | Clusters mentions that refer to the same entity across a document. |
| `abstract_meaning_representation` | Semantic graph analysis, with optional DOT or SVG visualization.   |
| `extractive_summarization`        | Ranked salient sentences with scores.                              |
| `abstractive_summarization`       | Generates a condensed natural-language summary.                    |
| `keyphrase_extraction`            | Ranked document-level keywords and phrases.                        |
| `grammatical_error_correction`    | Rewrites text to correct grammatical and related errors.           |
| `language_identification`         | Predicts a language, optionally returning ranked scores.           |
| `semantic_textual_similarity`     | Similarity scores for sentence or text pairs.                      |
| `sentiment_analysis`              | Numerical sentiment polarity.                                      |
| `text_classification`             | Model-specific category predictions.                               |
| `text_style_transfer`             | Text rewritten toward a designated style.                          |

These are documented client operations; their existence does not demonstrate that every endpoint is currently enabled for every language, account, or server deployment.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+4



The hosted coreference interface is particularly relevant for document-level semantic analysis.

Its output contains clusters of mentions, with spans indexed against the document's flattened token sequence. It also supports supplying tokenized sentences, and a `speakers` argument is available for dialogue-like inputs.

This permits document-wide reference grouping that sentence-level dependency parsing, NER, and SRL do not provide by themselves.

However, coreference resolution is not entity linking. A cluster may establish that two mentions refer to the same entity without identifying that entity in an external ontology or knowledge base.

Reference: [https://hanlp.hankcs.com/docs/api/restful.html](https://hanlp.hankcs.com/docs/api/restful.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



### 8.3 Operational tradeoffs of remote inference

Hosted inference can remove the need to download, load, and maintain local models, and it makes additional document-level functionality accessible through a compact client.

The tradeoffs include network latency, provider availability, request-size restrictions, rate limits, authentication, confidentiality requirements, and limitations on reproducibility when the server's checkpoint versions are not independently pinned.

The client documents HTTP errors including `400` for invalid requests, `401` for authorization failures, and `429` for rate limiting.

For a local-versus-hosted comparison, it is therefore necessary to distinguish capability breadth from deployment control.

## 9. Installation, dependencies, and execution characteristics

### 9.1 Packages and optional features

The native installation is:

```
pip install hanlp
```

The current package metadata publishes these optional extras:

| Installation      | Intended functionality                                                         |
| ----------------- | ------------------------------------------------------------------------------ |
| `hanlp`           | Default local NLP capabilities without all heavyweight optional dependencies.  |
| `hanlp[amr]`      | Dependencies for AMR parsing and generation, including PENMAN-related tooling. |
| `hanlp[tf]`       | TensorFlow-based components and associated dependencies.                       |
| `hanlp[fasttext]` | Optional fastText-related functionality.                                       |
| `hanlp[full]`     | Broad collection of optional dependencies.                                     |
| `hanlp_restful`   | Lightweight client for hosted inference; separate package.                     |

PyPI declares Python `>=3.6`, but this package-level metadata does not establish compatibility of every pretrained model and optional dependency with every modern Python version. The ModernBERT checkpoints, for example, require compatible releases of Hugging Face Transformers.

References:

[https://hanlp.hankcs.com/docs/install.html](https://hanlp.hankcs.com/docs/install.html?utm_source=chatgpt.com)

[https://pypi.org/project/hanlp/](https://pypi.org/project/hanlp/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



### 9.2 Model loading and resource management

`hanlp.load(...)` accepts a pretrained model identifier, URL, or local checkpoint path. It loads the component and any required dependent resources.

Model artifacts are downloaded into `HANLP_HOME`, with `~/.hanlp` as the usual Unix default. Hugging Face Transformer resources may be cached separately.

This creates two distinct lifecycle concerns: the version of the installed Python library and the exact model artifacts it loads.

A reproducible offline environment needs both the relevant HanLP artifacts and any separately downloaded transformer resources. HanLP's installation documentation explicitly describes preparing its own cache and the Hugging Face cache for offline use.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+1



References:

[https://hanlp.hankcs.com/docs/configure.html](https://hanlp.hankcs.com/docs/configure.html?utm_source=chatgpt.com)

[https://hanlp.hankcs.com/docs/install.html](https://hanlp.hankcs.com/docs/install.html?utm_source=chatgpt.com)

### 9.3 Hardware and performance mechanisms

HanLP uses PyTorch for its principal modern multitask modeling components, although some standalone components use TensorFlow or other optional backends.

The documented execution controls include `CUDA_VISIBLE_DEVICES` and `hanlp.load(..., devices=...)`. For compatible PyTorch components, the API also documents a list of devices for data-parallel execution.

Three factors determine performance more meaningfully than the library name alone.

Encoder reuse. A multitask checkpoint can avoid repeatedly encoding the same text through separate models. The benefit grows with the number and relative cost of predictions, but depends on which decoders are active.

Batching. Processing multiple sentences in a batch can reduce per-invocation overhead and improve accelerator utilization. Larger batches also consume more memory; long sequences may dominate batch cost.

Selected model and tasks. ModernBERT Large has different memory and computational requirements from Base or smaller multilingual encoders. Dependency, constituency, SRL, and semantic-graph decoders also have different computational characteristics.

No general CPU latency, GPU throughput, or VRAM figure can be reliably inferred from the published quality scores. Such estimates require the exact checkpoint, input-length distribution, requested tasks, runtime versions, and hardware.

Reference: [https://hanlp.hankcs.com/docs/configure.html](https://hanlp.hankcs.com/docs/configure.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



### 9.4 Version and release provenance

The latest PyPI release verified for this overview is HanLP 2.1.7, published October 25, 2026.

Much of the online API documentation, however, carries older documentation copyright dates and includes models released in previous years. Consequently, this overview distinguishes the published library release from the catalog of available pretrained models; it does not assume that every documented checkpoint has been retrained for version 2.1.7.

Reference: [https://pypi.org/project/hanlp/](https://pypi.org/project/hanlp/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



## 10. Integration boundaries, limitations, and architectural implications

### 10.1 HanLP is a linguistic parser, not a complete knowledge-extraction system

HanLP's core outputs can be transformed into higher-level structured representations, but several downstream operations are separate concerns.

| Requirement                 | HanLP contribution                  | What remains outside the core contract                               |
| --------------------------- | ----------------------------------- | -------------------------------------------------------------------- |
| Linguistic normalization    | Lemmas, tokens, POS and morphology  | Domain-specific terminology equivalence or canonical concepts        |
| Entity mention detection    | Typed NER spans                     | Entity resolution, external IDs, ontology reconciliation             |
| Event structure             | SRL predicate–argument spans        | Domain-specific event schemas, temporal reasoning                    |
| Syntactic structure         | Dependencies and constituency trees | Application-specific logical interpretation                          |
| Semantic relations          | SDP and AMR graphs                  | Consistent domain predicates, inference, knowledge-base validation   |
| Document reference grouping | Hosted coreference service          | Durable entity identity across unrelated documents                   |
| Retrieval representation    | Embedding and STS components        | Modern retrieval indexing, ranking, and vector-search infrastructure |

This distinction is especially important for semantic graphs. A dependency edge, a semantic dependency edge, an SRL argument and an AMR relation are all different kinds of evidence. Treating them as interchangeable generic relations can discard valuable information or create false semantic equivalences.

### 10.2 The linguistic representations are complementary, not interchangeable

One of HanLP's principal strengths is that it makes multiple views of language simultaneously accessible.

For example, consider:

The committee approved the proposal after reviewing the evidence.

A dependency parse describes grammatical attachment, including the relationship between approved, committee, proposal, and the subordinate reviewing clause.

A constituency parse describes the phrase and clause hierarchy.

SRL identifies predicate-centered structures for approved and potentially reviewing, including relevant participants and modifiers.

A semantic dependency representation provides additional labeled semantic connections under its selected annotation formalism.

AMR offers a more abstract graph of concepts and relationships.

A system that retains these different structures has more options for reasoning about the sentence than one that collapses everything into subject–predicate–object triples. Conversely, preserving all of them increases schema complexity and requires explicit reconciliation of overlapping or inconsistent outputs.

### 10.3 English capability is strong but task-specific

The ModernBERT checkpoints establish that HanLP is a serious English-language linguistic analysis framework, rather than merely a Chinese segmenter with incidental English support.

However, the most important constraints remain:

Task quality varies. The reported results are considerably different across NER, SRL, constituency parsing, and the three semantic dependency graph formalisms.

Label sets are fixed by training. A NER output is constrained by its learned labels and annotation ontology. Arbitrary domain entities or relations are not obtained simply by supplying a new list of label names.

Specialized text requires evaluation. Technical writing, legal clauses, OCR artifacts, tables, mathematical notation, and fragmented text may differ substantially from standard training corpora.

Sentence-level inference limits contextual reach. Most local multitask predictions operate within individual sentences. Pronoun resolution, cross-sentence ellipsis, and document-level reasoning need additional processing.

Multilingual coverage is uneven. Some languages rely on zero-shot predictions for tasks not directly represented in their supervised training resources.

These are not necessarily HanLP-specific defects. They are consequential distinctions between supervised linguistic parsing and more open-ended semantic interpretation.

### 10.4 Additional useful extension points

A few less obvious capabilities are worth highlighting.

Multi-criteria word segmentation. HanLP includes `MultiCriteriaTransformerTaggingTokenizer`, implementing an approach in which different segmentation criteria are signaled to a transformer. This addresses the fact that word boundaries are not uniquely defined for languages such as Chinese: segmentation standards can differ systematically.

Reference: [https://hanlp.hankcs.com/docs/api/hanlp/components/tokenizers/multi_criteria.html](https://hanlp.hankcs.com/docs/api/hanlp/components/tokenizers/multi_criteria.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Word-to-subword alignment. Its transformer tokenization layers manage mappings between word-level annotations and transformer subtokens, which are essential when integrating linguistic labels with subword-based encoders.

Reference: [https://hanlp.hankcs.com/docs/api/hanlp/layers/transformers/tokenizer.html](https://hanlp.hankcs.com/docs/api/hanlp/layers/transformers/tokenizer.html?utm_source=chatgpt.com)

Training-data and evaluation components. The library includes dataset loaders, transforms, samplers, vocabulary machinery, and parsers for formats such as CoNLL-U and CoNLL-2012. These reduce the amount of infrastructure required to train or evaluate conventional supervised NLP tasks.

Reference: [https://hanlp.hankcs.com/docs/api/hanlp/index.html](https://hanlp.hankcs.com/docs/api/hanlp/index.html?utm_source=chatgpt.com)

Model serialization and inspection. Components can be loaded from local paths and saved artifacts, while `Document` offers structured and human-readable inspection. This provides a practical boundary for testing learned predictions independently of downstream transformations.

### 10.5 Licensing distinctions

The Python library itself is published under Apache License 2.0.

However, HanLP's official tutorial states that its pretrained models and RESTful APIs are distributed under CC BY-NC-SA 4.0 terms. The noncommercial restriction is a significant distinction from the permissively licensed source code. Individual models and training datasets may also have additional provenance or usage restrictions that must be examined separately.

This means that permissive source-code licensing must not be interpreted as blanket authorization for commercial use of every downloaded checkpoint or hosted service.

References:

[https://pypi.org/project/hanlp/](https://pypi.org/project/hanlp/?utm_source=chatgpt.com)

[https://hanlp.hankcs.com/docs/tutorial.html](https://hanlp.hankcs.com/docs/tutorial.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



## 11. Overall capability assessment

HanLP is most distinctive when multiple explicit linguistic analyses are required together, rather than when a single isolated classification or embedding task is needed.

Its strongest architectural contributions are:

1. A unified multitask framework that combines heterogeneous linguistic predictions over shared contextual encodings.
2. Substantial English analysis through ModernBERT models, alongside multilingual and language-specialized checkpoints.
3. Rich syntax and semantics, particularly dependency parsing, constituency parsing, SRL, semantic dependency graphs, and independent AMR models.
4. Supervised model extensibility, including task dependencies, custom decoders, layer mixing, and differentiated optimization.
5. Structured output interoperability, with token-level annotations, serialized `Document` objects, and CoNLL conversion.
6. Practical linguistic control mechanisms, including tokenization dictionaries, gazetteer-based NER corrections, and multiple tokenization criteria.
7. Broader hosted capabilities, notably document-level coreference and additional text-processing services.

The principal reason to investigate HanLP is therefore not that it offers an unusually long list of NLP tasks. It is that it provides a relatively coherent architecture for producing, combining, training, and consuming different levels of linguistic structure.

For English, the ModernBERT multitask checkpoints are the most immediately relevant integrated models in the verified catalog. For research involving deeper semantic abstractions, HanLP's SRL, semantic dependency parsing, and AMR facilities offer complementary representations rather than redundant outputs.

The most consequential limitations are the need to respect sentence-level inference boundaries, task-specific annotation conventions, heterogeneous model availability, and the distinction between Apache-licensed framework code and separately licensed model assets.

Taken together, HanLP is best understood as a comprehensive neural linguistic analysis framework: broader than a tokenizer or NER model, more structurally explicit than general-purpose embedding systems, and extensible enough to support both integrated pretrained inference and specialized supervised linguistic modeling.

# HanLP 2.1 — Advanced Capabilities Addendum

Research date: November 8, 2026 | Target release: HanLP 2.1.7 | Scope: Additional functionality and clarifications to the original library overview

This addendum supplements the original HanLP overview with advanced capabilities identified through the subsequent gap analysis. It concentrates on functionality that changes HanLP's architectural possibilities, particularly its handling of structured predictions, long sequences, deterministic linguistic constraints, training, model customization, and efficient execution.

The key distinction throughout is between capabilities implemented by the HanLP framework, capabilities exposed by a particular pretrained checkpoint, and those provided by the companion `hanlp_common`, `hanlp_trie`, or `hanlp_restful` packages.

The referenced APIs are documented in the official HanLP 2.x documentation and upstream source. The latest published Python release verified on PyPI is 2.1.7, dated October 25, 2026. Some generated documentation describes earlier implementations; where appropriate, the addendum identifies component-level support without assuming that every checkpoint enables the capability.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



## 1. Advanced structured prediction

### 1.1 Nested named entity recognition through biaffine span classification

HanLP supports an alternative to conventional BIO/BILOU sequence-tagging NER through `BiaffineNamedEntityRecognizer` and the multitask `BiaffineNamedEntityRecognition` component.

Rather than assigning a sequence of boundary tags, the biaffine formulation treats candidate spans as potential entity mentions. Representations of the span boundaries are scored to predict an entity type or a null label.

For a token sequence of length \\(n\\), there are \\(n(n+1)/2\\) possible contiguous spans. The approach therefore has a substantially different candidate space from tokenwise sequence labeling.

This formulation enables nested entities without requiring them to be reduced to disjoint intervals. For example, a sentence could contain both an organization mention spanning University of Cambridge and a location mention spanning Cambridge.

The principal configuration and extension surfaces are:

| API / configuration              | Function                                                                                        |
| -------------------------------- | ----------------------------------------------------------------------------------------------- |
| `BiaffineNamedEntityRecognizer`  | Standalone biaffine span-based NER implementation.                                              |
| `BiaffineNamedEntityRecognition` | Equivalent task family integrated into HanLP's multitask framework.                             |
| `is_flat_ner`                    | Selects flat-entity behavior or permits nested spans.                                           |
| `tagset`                         | Restricts the entity labels considered in dataset preparation for the multitask implementation. |
| `doc_level_offset`               | Indicates that training annotations use document-level rather than sentence-level offsets.      |

Because entity detection is span-based, the architecture can support overlapping or nested mention structures that cannot be expressed naturally using a single flat BIO tag sequence. This is useful for hierarchically named organizations, locations embedded in organization names, and other nested-mention annotation schemes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+1



The tradeoff is a larger span-scoring space and the associated memory and computational costs. Flat and nested decoding also impose different constraints on the candidate spans. Nested recognition does not imply that the model can infer arbitrary hierarchical entity types or resolve mentions to canonical real-world entities.

Checkpoint qualification: The decoder supports nested NER, but a pretrained checkpoint must have compatible configuration and training data to provide useful nested predictions. The published English ModernBERT model's existence does not by itself establish nested-entity performance.

Primary documentation:

`https://hanlp.hankcs.com/docs/api/hanlp/components/ner/biaffine_ner.html`

`https://hanlp.hankcs.com/docs/api/hanlp/components/mtl/tasks/ner/biaffine_ner.html`

### 1.2 Constrained syntactic and semantic graph decoding

HanLP's biaffine parsers provide structural decoding mechanisms in addition to estimating neural arc and relation scores.

The most relevant distinction is between a dependency parser, which constructs a syntactic tree, and a semantic dependency parser, which predicts a potentially multiheaded graph.

The standalone `BiaffineSemanticDependencyParser` exposes the following controls:

- `apply_constraint`, which activates additional constraints in semantic graph processing.
- `single_root`, which controls restrictions on root attachments.
- `no_zero_head`, which restricts zero-head assignments to nonroot tokens.

These options matter because independent edge predictions can produce structures that violate expectations of the target annotation formalism. Enforcing some constraints within decoding can reduce the need for corrective postprocessing and prevent certain invalid outputs from being emitted.

The exact constraints are limited to those implemented by the parser. They should not be interpreted as guaranteeing arbitrary semantic consistency, acyclicity, connectedness, or satisfaction of an external ontology.

The standard syntactic dependency parser also exposes decoding and tree-structure controls. In both cases, the distinction between independently scored arcs and globally constrained structures is important when interpreting model outputs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+1



Primary documentation:

`https://hanlp.hankcs.com/docs/api/hanlp/components/parsers/biaffine_sdp.html`

`https://hanlp.hankcs.com/docs/api/hanlp/components/parsers/biaffine_dep.html`

### 1.3 Specialized joint Universal Dependencies parsing

The standalone `UniversalDependenciesParser` is an additional architectural option that deserves distinction from HanLP's broader multitask framework.

It implements a joint approach to Universal Dependencies analysis based on 75 Languages, 1 Model: Parsing Universal Dependencies Universally (Kondratyuk and Straka, 2019).

Its scope includes lemmatization, morphological-feature prediction, part-of-speech tagging, and dependency parsing.

The significance is that these grammatical predictions can be modeled in a specialized, coordinated system instead of requiring four independently trained pipelines or a more general multitask checkpoint.

Joint modeling can allow grammatical information to influence related predictions, but it does not establish that every output will be mutually consistent or that the standalone architecture will outperform the newer transformer-based MTL checkpoints. Dataset compatibility and annotation schemes remain material.

Primary documentation: `https://hanlp.hankcs.com/docs/api/hanlp/components/parsers/ud_parser.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



## 2. Long-sequence processing and token alignment

### 2.1 Sliding-window transformer processing

HanLP includes mechanisms for processing sequences longer than the configured transformer context window without necessarily discarding all excess input.

`TransformerSequenceTokenizer` exposes:

- `max_seq_length`, controlling the length of transformer-tokenized sequences.
- `truncate_long_sequences`, which determines whether excess input is truncated or sliding-window processing is used.

The lower-level `TransformerEncoder` separately exposes `max_sequence_length`. Its documentation states that sequences exceeding this limit are handled using a sliding window, with the transformer's `max_position_embeddings` used when no explicit limit is supplied.

This is distinct from simply dividing a document into sentences. A sentence may itself exceed the encoder's maximum length, and specialized technical prose can contain unusually long sentence-like units.

Sliding windows provide a mechanism for processing these sequences with a bounded-context encoder while preserving coverage of the input. The benefit is conditional: overlapping windows require additional computation, and tokens near different window boundaries may receive different context from tokens processed together.

Sliding-window support is not unrestricted document-level attention. It does not establish that a model can reason across arbitrary distances or recover cross-window relationships consistently. Nor does the existence of the lower-level mechanism guarantee that every pretrained task decoder uses it with the same boundary-handling behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+1



Primary documentation:

`https://hanlp.hankcs.com/docs/api/hanlp/layers/transformers/tokenizer.html`

`https://hanlp.hankcs.com/docs/api/hanlp/layers/transformers/encoder.html`

### 2.2 Word-to-subword alignment and configurable representations

HanLP's `TransformerSequenceTokenizer` handles the correspondence between linguistic tokens and transformer subtokens.

This matters because a word-level parser may predict one POS tag, dependency relation, or entity-boundary decision per word, while the encoder uses multiple subword representations for the same word.

The tokenizer provides several useful options:

| Parameter                  | Representation or behavior                                              |
| -------------------------- | ----------------------------------------------------------------------- |
| `ret_token_span`           | Returns each word's span in subtoken coordinates.                       |
| `ret_prefix_mask`          | Identifies the prefix subtoken associated with each input token.        |
| `ret_subtokens`            | Exposes subtoken sequences for use in tokenization-oriented processing. |
| `ret_subtokens_group`      | Exposes subtoken groupings associated with original tokens.             |
| `ret_mask_and_type`        | Returns transformer attention-mask and token-type information.          |
| `cls_is_bos`, `sep_is_eos` | Controls interpretation of special tokens and sequence boundaries.      |
| `use_fast`                 | Attempts to use a Hugging Face fast tokenizer where supported.          |

These capabilities can eliminate separate wordpiece alignment logic when developing token-level models or interpreting their intermediate representations.

At the encoder level, `average_subwords` and `scalar_mix` introduce additional choices about how the subtoken and transformer-layer representations are combined. They influence the learned features available to downstream tasks rather than merely affecting output formatting.

The relevant indexing schemes must remain distinct. Word-to-subword spans are not equivalent to token-to-character offsets in the original document, and neither should be confused with document-global entity-mention offsets.

Primary documentation: `https://hanlp.hankcs.com/docs/api/hanlp/layers/transformers/tokenizer.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+1



## 3. Hybrid deterministic and neural language processing

### 3.1 Trie-based dictionary matching and protected-span processing

HanLP's `hanlp_trie` companion package provides more general dictionary-matching infrastructure than the `dict_force` and `dict_combine` tokenizer options discussed in the original overview.

Its `Trie` implementation accepts either strings or sequences of tokens as matching inputs. This means the same mechanism can operate over individual characters, already-tokenized text, or other sequences of discrete matching units.

The two principal matching operations have materially different semantics:

| Operation                  | Behavior                                                                        | Consequence                                                           |
| -------------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `Trie.parse(text)`         | Returns all occurrences of dictionary entries, including overlapping matches.   | Preserves competing lexical hypotheses for later resolution.          |
| `Trie.parse_longest(text)` | Performs sequential longest-prefix matching and returns nonoverlapping matches. | Produces a deterministic segmentation or prioritized matching result. |

The distinction matters when a corpus contains nested technical terminology. For example, a dictionary might contain neural network, convolutional neural network, and network. Returning all overlapping matches preserves alternatives, whereas longest-prefix selection resolves them according to the matching algorithm rather than contextual semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



The related `TrieDict` class extends this idea into hybrid processing.

Its `split_batch(...)` and `merge_batch(...)` methods support the following workflow:

1. Identify dictionary-matched spans in a batch of input sentences.
2. Separate unmatched text into segments that can be processed independently.
3. Retain the association between those segments and their original sentences.
4. Merge the neural model's outputs with the dictionary-controlled spans.

This is more powerful than simply replacing individual predictions after inference. It allows lexical constraints to determine which segments require statistical processing in the first place.

The approach can be valuable when some surface forms should be recognized deterministically while surrounding material benefits from contextual modeling. It may also reduce unnecessary model computation, although any performance benefit depends on the amount of text bypassed, the cost of segmentation and reassembly, and the underlying model's batching behavior.

The main semantic limitation is that dictionary matching is based on surface forms or token sequences, not contextual disambiguation. Longest-prefix matching also imposes precedence when candidate matches overlap.

An important integration requirement: `TrieDict`'s partitioning and reassembly operate on their own span representations. Downstream models that produce token-indexed annotations, nested spans, or dependency edges may require additional mapping to restore global indices. The ability to concatenate token outputs does not imply that arbitrary structured predictions can be recombined without further processing.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Primary documentation:

`https://hanlp.hankcs.com/docs/api/trie/trie.html`

`https://hanlp.hankcs.com/docs/api/trie/dictionary.html`

### 3.2 Dictionary-enforced sequence tagging

HanLP also incorporates deterministic dictionary corrections directly into its multitask sequence-tagging components.

`hanlp.components.mtl.tasks.pos.TransformerTagging` exposes `dict_tags`, which can associate a string or token sequence with one or more specified tags. Longest-prefix matching identifies matching sequences and overrides corresponding neural predictions.

This extends dictionary-based control beyond tokenization and standalone named entity recognition.

It is useful when a specific vocabulary has established grammatical interpretations or when a tagger must consistently recognize domain-specific token sequences.

Unlike a dictionary that merely stores recognized terms, `dict_tags` can carry an aligned sequence of labels. This makes it applicable to more general sequence-tagging conventions, although its effectiveness depends on compatible tokenization and the model's tag vocabulary.

The same task component exposes additional input-processing controls:

- `max_seq_len`, limiting the length of processed sequences.
- `sent_delimiter`, identifying preferred segmentation points.
- `hard_constraint`, enforcing a split even when a preferred delimiter is unavailable.
- `char_level`, determining whether sequence length is evaluated at character level.
- `crf`, selecting an optional conditional random field decoder.

These controls are especially relevant for unusually long or poorly segmented sentences.

Unlike the transformer sliding-window mechanisms described earlier, delimiter-based splitting changes the linguistic units presented to a downstream tagger. It can reduce sequence length, but it can also sever relationships that would otherwise be visible within the original sentence.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Primary documentation:

`https://hanlp.hankcs.com/docs/api/hanlp/components/mtl/tasks/pos.html`

## 4. Efficient batching and dataset execution

### 4.1 Length-aware and token-budget-aware batch formation

HanLP includes substantial batching infrastructure through `hanlp.common.dataset`.

The important components are `SortingSampler`, `BucketSampler`, and `KMeansSampler`, along with `SortingSamplerBuilder` and `KMeansSamplerBuilder`.

These address a common computational inefficiency in sequence models: batching together examples with very different lengths can cause substantial padding overhead.

`SortingSampler` orders examples by length and groups nearby examples into batches.

`BucketSampler` groups samples according to predefined length-based buckets.

`KMeansSampler` forms buckets by clustering sample lengths, allowing batches to be constructed from examples with similar sequence sizes.

The distinction between the available batch constraints is significant.

`batch_size` limits the number of examples. By contrast, `batch_max_tokens` limits a token budget, which can be more appropriate when sequence length has a large effect on memory consumption.

`SortingSampler` additionally exposes `use_effective_tokens`. When enabled, token budgeting takes into account the effective number of tokens after padding rather than relying solely on unpadded input lengths.

For a padded batch, an approximate accounting measure is:

\\[ T\_{\mathrm{padded}}=B\max_i L_i \\]

where \\(B\\) is the number of examples and \\(L_i\\) is each sequence length.

Grouping examples of similar lengths reduces the difference between this padded cost and the number of actual input tokens.

However, a token budget is not a direct GPU memory guarantee. Actual memory consumption depends on transformer architecture, sequence length, intermediate representations, decoding operations, training versus inference, and numerical precision.

HanLP's `SamplerBuilder` also coordinates batching with gradient accumulation. Its `scale(gradient_accumulation)` operation reduces the configured batch-size and token-budget limits when distributing an effective update batch across multiple optimization steps.

That allows batching policy and gradient accumulation to be coordinated through the library rather than treated as unrelated implementation details.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Primary documentation:

`https://hanlp.hankcs.com/docs/api/hanlp/common/dataset.html`

### 4.2 Field-aware padding and batch conversion

`PadSequenceDataLoader` is HanLP's specialized DataLoader abstraction for linguistic datasets.

It provides automatic padding, tensor conversion, vocabulary-aware processing, and device placement.

A less obvious capability is its use of field-name conventions. Fields ending in suffixes such as `_id`, `_ids`, `_count`, `_offset`, `_span`, or `mask` are recognized for tensor conversion, with additional configurable padding behavior.

This is useful because linguistic batches are frequently heterogeneous. One sample may contain token IDs, word-to-subword offsets, masks, morphological labels, and graph-related structures with different shapes.

The field conventions can reduce repetitive data-collation code, but they also introduce a contract: custom dataset fields must use compatible naming or explicit configuration if the automatic behavior is desired.

For more complex structured data, the caller still needs to verify whether padding and conversion preserve the intended semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



### 4.3 Multiprocessing prefetch with `PrefetchDataLoader`

`PrefetchDataLoader` wraps an existing PyTorch DataLoader and prepares subsequent batches using multiprocessing.

It is particularly intended for workloads in which batch construction is expensive enough to delay model execution.

The component exposes a `prefetch` count and an optional `batchify` callable.

The documentation identifies two important operational constraints:

Multiprocessing start method. The implementation requires the `spawn` start method, with initialization placed under the Python `if __name__ == "__main__":` guard.

Resource consumption. Prefetched batches can reside in a GPU-backed queue. Increasing prefetch depth may improve the overlap between computation and data preparation, but it can also increase memory consumption substantially.

The component additionally provides `close()` to terminate internal processes and queues.

This distinguishes three complementary performance mechanisms:

- Length-aware sampling reduces padding and wasted tensor computation.
- Field-aware collation reduces custom batch-construction overhead.
- Prefetching overlaps batch preparation with model execution.

None guarantees a speedup independently. For example, multiprocessing prefetch may be counterproductive when batch construction is already inexpensive or when memory pressure is the primary bottleneck.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Primary documentation:

`https://hanlp.hankcs.com/docs/api/hanlp/common/dataset.html`

## 5. Training, fine-tuning, and model adaptation

### 5.1 Native teacher–student knowledge distillation

An important capability absent from the initial overview is HanLP's knowledge-distillation framework for token-level models.

`TransformerTagger.distill(...)` allows a student transformer-based tagger to be trained under the supervision of a teacher tagger.

The documented method accepts a teacher, training and development datasets, an output directory, a student `transformer` identifier, and distillation-related configuration such as `temperature_scheduler`.

Its default temperature-scheduler identifier is `flsw`.

The underlying training implementation combines ordinary supervised loss with a knowledge-distillation loss derived from teacher predictions.

Conceptually, the training objective has the form

\\[ \mathcal{L} = \lambda_t\mathcal{L}\_{\mathrm{sup}} + (1-\lambda_t)\mathcal{L}\_{\mathrm{KD}}, \\]

where the weighting factor can vary during training.

The source implementation confirms that teacher predictions are computed without gradient tracking, while the student receives gradients from the combined objective.

This provides a native mechanism for attempting to transfer behavior from a larger or more capable tagger into a different student architecture.

The important architectural advantage is not merely model compression. Distillation also makes it possible to use a trained model as an additional supervisory signal, complementing the original labels.

The scope is narrower than general multitask-model distillation. The verified interface belongs to the transformer tagging framework. It should not be assumed to distill an arbitrary HanLP multitask checkpoint—including every one of its parsing and semantic heads—into another multitask architecture.

Practical compatibility also depends on matching token boundaries, label vocabularies, output dimensions, and training objectives. Distillation does not guarantee that a student achieves the teacher's accuracy, nor that it will operate faster under every runtime configuration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Primary source:

`https://hanlp.hankcs.com/docs/_modules/hanlp/components/taggers/transformers/transformer_tagger.html`

### 5.2 `TorchComponent` and the model lifecycle

`hanlp.common.torch_component.TorchComponent` provides reusable infrastructure for PyTorch-based HanLP components.

Its functionality extends beyond a simple `fit`/`predict` interface.

The class defines a conventional lifecycle covering dataset construction, vocabularies, dataloaders, model initialization, optimization, evaluation, serialization, and device management.

Subclasses can override or bypass parts of this lifecycle, making it an extension framework rather than a rigid training protocol.

A notable feature is its explicit fine-tuning behavior:

- `finetune=False` follows the component's normal initialization procedure.
- `finetune=True` initializes from the designated save directory.
- `finetune=<path>` initializes from an alternative saved component.

The implementation also provides mechanisms for rebuilding or modifying vocabularies during adaptation.

When a model's label vocabulary expands, however, preserving previously trained output weights is a separate problem from merely adding vocabulary entries. HanLP's transformer tagging implementation includes logic for safely transferring compatible parameters and retaining existing classifier parameters when the output size changes.

This reduces custom checkpoint-manipulation work, but it does not establish that all component types can expand their output ontologies without retraining.

Serialization is similarly structured. `TorchComponent` provides separate methods for saving:

| Method              | Artifact                                  |
| ------------------- | ----------------------------------------- |
| `save_config(...)`  | Component configuration.                  |
| `save_vocabs(...)`  | Vocabulary mappings and related metadata. |
| `save_weights(...)` | Model parameter weights.                  |
| `save(...)`         | Higher-level component serialization.     |

`save_weights(..., trainable_only=True)` permits serialization of only trainable parameters, reducing the amount of stored data when a model contains large frozen embeddings.

The qualification is that such an artifact still needs its external or frozen resources to be available at restoration time. Selective serialization should not be confused with producing a completely self-contained checkpoint.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation+2



Primary documentation:

`https://hanlp.hankcs.com/docs/api/hanlp/common/torch_component.html`

### 5.3 A consequential inference detail: `__call__` versus `predict`

The `TorchComponent` documentation explicitly distinguishes ordinary inference through the callable component from direct invocation of `predict(...)`.

`TorchComponent.__call__` is decorated with `torch.no_grad()`, whereas the abstract `predict` method does not independently guarantee that gradient computation is disabled.

Therefore, for ordinary inference:

```
result = model(sentences)
```

is the intended usage.

Calling

```
result = model.predict(sentences)
```

directly may create unnecessary autograd computation and associated memory overhead.

This is particularly relevant for inference-only workflows using large transformer encoders and multiple task decoders.

The distinction is not a claim that direct `predict` calls always produce different predictions; it concerns execution semantics and resource usage.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



### 5.4 Hybrid encoder representations and secondary contextualization

HanLP's standalone transformer tagging architecture can incorporate additional learned representations beyond the output of one transformer.

`TransformerTaggingModel` supports:

- A transformer encoder.
- An optional `secondary_encoder`.
- Additional features through `extra_embeddings`.
- A classifier and optional CRF decoding configuration.

The implementation first obtains the transformer representation, applies the secondary encoder when configured, concatenates the additional embeddings, and passes the resulting features to the classifier.

This creates several architectural possibilities.

A secondary encoder can model contextual dependencies over transformer-derived word representations. Additional embeddings can introduce other token-level signals, potentially including lexical features or separate embedding sources.

These mechanisms can support richer representations without requiring every feature to be learned exclusively by the primary transformer.

The tradeoffs include larger feature dimensions, more trainable parameters, alignment requirements, and additional inference computation. The appropriate configurations depend on the task and training data; extra features do not automatically improve performance.

The framework also exposes controls for transformer-layer selection, layer dropout, and scalar mixing. Together, these support a more flexible representation architecture than a simple last-hidden-state-plus-linear-classifier implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Primary source:

`https://hanlp.hankcs.com/docs/_modules/hanlp/components/taggers/transformers/transformer_tagger.html`

## 6. Dataset engineering and linguistic interoperability

### 6.1 `TransformableDataset` as a reusable preprocessing abstraction

HanLP's `TransformableDataset` supports ordered preprocessing transformations over linguistic datasets.

It includes operations for appending or inserting transformations, transforming individual samples, caching, filtering, shuffling, and constructing dataset subsets.

It also implements dataset splitting and k-fold partitioning.

One useful facility is `generate_idx`, which adds an index to samples so their original order can be reconstructed after a sampler has reordered them.

This matters when length-aware batching changes the processing order but downstream predictions must be associated with the original input sequence.

Its caching mechanism can avoid repeated transformations, while `purge_cache()` allows cached data to be invalidated.

There is a consequential mutability distinction: `transform_sample(..., inplace=True)` can allow transformations to modify existing sample fields repeatedly. HanLP's documentation explicitly warns that transformations which append special tokens, for example, may introduce duplicate tokens if reapplied in place.

This makes the transformation framework more than a convenience wrapper. It provides a reusable abstraction for the sequencing and caching of data transformations, but consumers must still manage idempotence, cache invalidation, and ordering semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Primary documentation:

`https://hanlp.hankcs.com/docs/api/hanlp/common/dataset.html`

### 6.2 Structured CoNLL and CoNLL-U objects

The original overview mentioned `Document.to_conll`, but `hanlp_common.conll` supplies additional functionality for constructing, inspecting, and manipulating dependency annotations.

Its key classes include `CoNLLWord`, `CoNLLUWord`, and `CoNLLSentence`.

`CoNLLSentence` can be constructed from strings, files, or dictionary-based representations.

It also exposes:

- `to_tree(...)`, generating a readable representation of the dependency structure.
- `to_markdown(...)`, producing a tabular representation.
- `projective`, indicating whether the dependency structure is projective.

The `projective` property is particularly relevant to parsing algorithms. Projective dependency trees can be represented without crossing dependency arcs in the sentence's linear ordering.

Some parsing algorithms rely on projectivity assumptions, while others accommodate nonprojective structures. Being able to inspect this property directly is useful for dataset characterization, parser evaluation, and interpreting structural predictions.

These objects can reduce custom treebank processing and inspection code. They are not, however, a substitute for comprehensive corpus validation: structural correctness, annotation-scheme consistency, semantic validity, and dataset provenance require additional checks.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Primary documentation:

`https://hanlp.hankcs.com/docs/api/common/conll.html`

## 7. Additional supervised modeling capabilities

### 7.1 Text-pair classification

HanLP's `TransformerClassifier` supports supervised classification using both single-text and paired-text inputs.

Its training interface exposes `text_a_key` and `text_b_key`, allowing two input fields to be encoded together.

This makes the class relevant to tasks in which a prediction depends on the relationship between two texts rather than the meaning of one text independently.

Examples of possible supervised objectives include textual entailment, paraphrase classification, and binary relevance classification, given suitable labeled datasets.

The class also supports transformer selection, maximum sequence length, truncation controls, token-budget batching, and standard fine-tuning options.

This should be distinguished from HanLP's semantic textual similarity regression model. A classifier predicts labels from a trained category set, while a similarity regressor produces a numerical similarity score. Neither automatically provides open-ended relation extraction or a calibrated measure of semantic truth.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Primary documentation:

`https://hanlp.hankcs.com/docs/api/hanlp/components/classifiers.html`

## 8. Clarifications to the original architectural description

### 8.1 Model-specific multilingual coverage

The original description of ten jointly modeled tasks across 130 languages requires a narrower interpretation.

The published XLM-R and multilingual MiniLM checkpoints combine multiple linguistic tasks, including tokenization, POS tagging, lemmatization, morphological features, NER, SRL, syntactic dependency parsing, semantic dependency parsing, and constituency parsing.

The published model catalog advertises coverage of 130 languages for these multilingual resources.

However, this represents the set of supported languages and task capabilities across the training resources and model architecture; it does not establish equivalent supervision or accuracy across all task–language combinations.

Moreover, AMR is not a decoder included in the advertised XLM-R or English ModernBERT MTL checkpoint identifiers. It is implemented through separate parser models.

The relevant unit of capability is therefore the particular checkpoint and its configured task heads, not the total number of NLP families offered anywhere within the HanLP ecosystem.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hanlp.hankcs.com\&sz=32)

HanLP Documentation



Primary documentation:

`https://hanlp.hankcs.com/docs/api/hanlp/pretrained/mtl.html`

### 8.2 Modern HanLP and the original Java-based ecosystem

`hanlp` 2.x and `pyhanlp` should be treated as distinct implementations.

`pyhanlp` is a Python interface to the older Java-based HanLP 1.x implementation. It provides access to traditional Chinese NLP algorithms and utilities that may not exist in identical form in the modern Python implementation.

The two generations coexist rather than constituting a single API-compatible product line.

This distinction is especially important when researching dictionary operations, older statistical models, rule-based segmentation, keyword extraction, and traditional Chinese linguistic processing.

A capability found in the original Java library should not be attributed to the native Python 2.x package without checking that it was implemented or exposed there.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

hankcs/pyhanlp: 中文分词 · GitHub



Primary source:

`https://github.com/hankcs/pyhanlp`

### 8.3 Framework capability versus pretrained availability

For advanced HanLP functionality, three levels of support must remain separate.

Framework-level support means that the library contains a class, decoder, loss function, transformation, or algorithm capable of implementing a behavior.

Checkpoint-level support means that a specific saved model configures and supplies the learned parameters required for that behavior.

Validated capability means that relevant evaluations or tests establish the desired behavior under identifiable conditions.

For example, the existence of nested NER support in a biaffine decoder does not establish that a particular ModernBERT checkpoint was trained to predict nested entities. Similarly, available distillation machinery does not imply that every MTL task can be distilled automatically, and structural constraints exposed by a standalone graph parser are not necessarily activated in every semantic dependency checkpoint.

The same distinction applies to language-specific accuracy, domain adaptability, throughput, and resource requirements.

## 9. Architectural implications of the additional capabilities

The newly documented functionality establishes that HanLP can serve not only as an inference framework for linguistic annotations, but also as infrastructure for developing more specialized language-processing systems.

Three capability interactions are particularly consequential.

First, HanLP can combine neural predictions with deterministic linguistic constraints. Trie matching, protected-span processing, dictionary-based tagging, and constrained graph decoding act at different stages of the prediction process. These mechanisms can reduce custom rule-integration code, provided their precedence, token alignment, and structural limitations are understood.

Second, HanLP provides multiple complementary mechanisms for efficient execution. Shared transformer encodings, sliding-window processing, length-aware sampling, token-budget batching, field-aware padding, and multiprocessing prefetch address different sources of computational overhead. They can be combined, but their benefits are workload-dependent and some increase memory consumption while reducing other costs.

Third, the training infrastructure supports substantially more adaptation than checkpoint loading alone. Custom task heads, alternative contextualization layers, supplementary embeddings, task-specific decoders, fine-tuning, vocabulary adaptation, and teacher–student distillation provide different routes for learning specialized linguistic predictions. These mechanisms are not interchangeable, and the most advanced capabilities may be restricted to particular component classes rather than universally supported across MTL.

Taken together, these additions expand HanLP's role from a collection of pretrained NLP models to a configurable linguistic modeling and execution framework, with useful built-in machinery for structured prediction, hybrid rules, supervised adaptation, and processing efficiency.

The most important qualification is that HanLP's architectural flexibility should not be conflated with the availability of pretrained weights for every possible configuration. Its native implementations can reduce substantial amounts of custom infrastructure, but the quality and completeness of any new task still depend on appropriate data, trained models, and evaluation.

This addendum completes the significant capability gaps identified in the preceding audit without changing the central characterization of HanLP in the original overview.