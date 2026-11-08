# Maverick Coref — Comprehensive Python Library Overview

Research date: November 8, 2026 | Latest verified PyPI release: 1.0.7 (June 10, 2025) | Primary implementation: Python / PyTorch

## 1. Executive overview

`maverick-coref` is a specialized neural coreference-resolution library designed to identify textual mentions referring to the same entity and group those mentions into coherent clusters. Developed by SapienzaNLP, it implements the Maverick architecture introduced at ACL 2024 in Maverick: Efficient and Accurate Coreference Resolution Defying Recent Trends.

The library is particularly interesting because it achieves competitive coreference accuracy using an encoder-based, discriminative architecture rather than relying on large autoregressive language models.

Its distinguishing capabilities include:

- End-to-end coreference resolution: Identify mentions and group them into entity clusters from English text.
- Multiple annotation regimes: Pretrained models for OntoNotes, PreCo, and LitBank, with materially different mention-coverage and singleton conventions.
- Constrained coreference inference: Resolve relationships among externally supplied mentions, or expand previously established coreference clusters.
- Structural outputs: Return token spans, character offsets where supported, mention text, and entity clusters suitable for downstream NLP processing.
- Trainable architectures: Use configurable model implementations, pretrained checkpoints, and dataset-specific training/evaluation pipelines.
- Computational efficiency: Exploit task-specific representations and clustering mechanisms instead of repeatedly generating structured answers autoregressively.

The original paper reports up to 170× faster inference than the previously strongest systems it compared against, alongside substantially lower training-memory requirements. These are historical, benchmark-specific comparisons, not universal performance guarantees or measurements against the latest 2026 models.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://aclanthology.org\&sz=32)

aclanthology.org+1



### Capability map

| Capability                               | Provided by Maverick                        | Important distinction                                                           |
| ---------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------- |
| Mention detection                        | Yes                                         | Learns which spans constitute referential mentions                              |
| Entity coreference clustering            | Yes                                         | Produces clusters of expressions referring to the same entity                   |
| Pronoun and nominal reference resolution | Yes                                         | Groups pronouns, names, and descriptive mentions                                |
| Singleton extraction                     | Yes, model-dependent                        | PreCo/LitBank models are preferable for reliable singleton identification       |
| Externally supplied mention resolution   | Yes                                         | Can isolate clustering from mention detection                                   |
| Cluster-constrained inference            | Yes                                         | Can extend given clusters with additional predicted mentions                    |
| Character-offset mapping                 | Yes, for supported input forms              | Crucial for alignment with original source text                                 |
| Domain-specific model training           | Yes                                         | Requires annotated data and configuration                                       |
| Entity linking to external IDs           | No native end-to-end capability established | Coreference clusters are not knowledge-base identities                          |
| Semantic relation extraction             | Not the library's primary task              | Requires separate extraction or reasoning components                            |
| Cross-document entity reconciliation     | Not established as a native feature         | Document-level clusters must not be mistaken for globally persistent identities |

Package and research sources:

- Repository and reference implementation: [https://github.com/SapienzaNLP/maverick-coref](https://github.com/SapienzaNLP/maverick-coref?utm_source=chatgpt.com)
- PyPI distribution: [https://pypi.org/project/maverick-coref/](https://pypi.org/project/maverick-coref/?utm_source=chatgpt.com)
- ACL 2024 paper: [https://aclanthology.org/2024.acl-long.722/](https://aclanthology.org/2024.acl-long.722/?utm_source=chatgpt.com)
- Pretrained checkpoints: [https://huggingface.co/collections/sapienzanlp/maverick-coreference-resolution-66a750a50246fad8d9c7086a](https://huggingface.co/collections/sapienzanlp/maverick-coreference-resolution-66a750a50246fad8d9c7086a?utm_source=chatgpt.com)

## 2. Architecture and computational model

Maverick is built around three distinct stages:

Transformer document encoder

DeBERTa-v3 contextualizes input tokens across the document

Mention extraction

Predict span starts → predict conditioned ends → apply sentence-boundary constraints

Mention clustering

Score antecedents using S2E or MES, or build clusters incrementally

Coreference clusters

Groups of mention spans referring to common discourse entities

### 2.1 Transformer-based document encoding

The paper's architectures use DeBERTa-v3, a bidirectional encoder that constructs contextual token representations before mention detection and clustering.

Unlike a generative LLM, Maverick does not need to generate a sequence containing all mention identifiers, brackets, or relationship annotations. Instead, it learns a set of discriminative decisions over contextualized representations.

This has several consequences:

- The document encoder can be executed without autoregressively emitting every relationship.
- Multiple mention candidates reuse contextual representations.
- Downstream scoring operates on structured candidates rather than vocabulary-wide token generation.
- Training can directly optimize mention-boundary and clustering objectives.

The published experiments investigate both base- and large-sized encoders. These are architectural configurations, not interchangeable weights that can be substituted into an existing trained checkpoint without retraining.

### 2.2 Conditional start–end mention detection

A major innovation is how Maverick reduces the cost of identifying candidate spans.

Traditional span-based coreference systems often enumerate a large set of possible spans, score them, and retain the highest-scoring candidates.

Maverick instead performs a conditional two-stage operation.

First, identify likely start positions.

Given contextual token representations \\(h_i\\), a learned network estimates

\\[ P\_{\mathrm{start}}(i)=\sigma(f\_{\mathrm{start}}(h_i)). \\]

Second, predict end positions conditioned on each accepted start.

\\[ P\_{\mathrm{end}}(j\mid i) =\sigma(f\_{\mathrm{end}}([h_i;h_j])). \\]

The paper uses a threshold of 0.5 for each probability.

This structure avoids scoring end positions for tokens that are not plausible mention starts. It also permits multiple end positions for a single start, supporting overlapping or nested mentions.

For example, a document might contain the overlapping mentions:

- the president
- the president of the company

Such spans can be represented independently rather than requiring nonoverlapping sequence labels.

### 2.3 Sentence-boundary regularization

Maverick further restricts possible mention ends to the sentence containing their start.

This is the paper's end-of-sentence (EOS) regularization mechanism.

Its advantages are computational and representational:

- It avoids considering spans crossing sentence boundaries.
- It does not impose the same fixed maximum mention length used by some coarse-to-fine approaches.
- It reduces candidate enumeration before the comparatively expensive clustering stage.

The underlying assumption is that gold mentions do not cross sentence boundaries in the evaluated annotation schemes. This is reasonable for the referenced coreference corpora, but not necessarily universal for arbitrary document structures or unusual text annotation systems.

### 2.4 Candidate pruning without a conventional top-k budget

Earlier coreference models commonly rank mention candidates and retain a configurable fraction of them.

Maverick uses its predicted start/end probabilities to retain likely mentions, rather than imposing the same global top-k rule.

The paper reports the following comparison on the OntoNotes development set:

| Operation                               | Conventional coarse-to-fine | Maverick |
| --------------------------------------- | --------------------------- | -------- |
| Candidate spans initially considered    | 183,577                     | 20,565   |
| Candidates after regularization         | 14,265                      | 777      |
| Mention pairs considered for clustering | 29,334                      | 2,713    |

These figures are averages from the original experimental setup, not fixed runtime limits. They illustrate why improvements in mention extraction can substantially reduce the subsequent pairwise comparison workload.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://aclanthology.org\&sz=32)

aclanthology.org+2



### 2.5 Three clustering architectures

The Maverick research framework implements three approaches to the second half of the problem.

| Architecture    | Clustering mechanism                          | Principal distinction                                              |
| --------------- | --------------------------------------------- | ------------------------------------------------------------------ |
| `Maverick_s2e`  | Start-to-end token-pair scoring               | Relatively simple, efficient antecedent scoring                    |
| `Maverick_mes`  | Linguistically specialized antecedent scoring | Different scoring functions for different mention-pair categories  |
| `Maverick_incr` | Incremental mention-to-cluster scoring        | Uses previous cluster contents to decide where new mentions belong |

#### Maverick-S2E

The S2E variant follows a start-to-end antecedent-scoring formulation.

A mention is represented through its contextualized start and end tokens. Learned projections and bilinear interactions estimate whether one mention corefers with an earlier mention.

This eliminates the need to construct a large, separate representation for every possible span before scoring antecedents.

It is comparatively straightforward to implement and avoids the additional linguistic category selection used by MES.

#### Maverick-MES

MES is the default publicly distributed model family and the most important variant for typical inference use.

MES builds on the LingMess formulation by introducing six specialized scoring functions for linguistically motivated categories of mention pairs.

Rather than relying on one generic scorer, the model can distinguish different kinds of relationships, such as a pronoun referring to a named entity.

This provides additional structure for cases in which coreference evidence depends on the grammatical or lexical nature of the two mentions.

The distinction is important: MES is still a neural model. The specialized scorers do not make it a deterministic pronoun-resolution or grammar-rule system.

#### Maverick-Incremental

The incremental architecture assigns mentions to clusters sequentially.

For a new mention, it evaluates its compatibility with existing clusters, using a lightweight, single-layer transformer to attend to representations of the mentions already assigned to a cluster.

The model either:

1. Assigns the new mention to an existing cluster whose score passes the threshold.
2. Creates a new cluster if no suitable one exists.

Unlike approaches maintaining only a fixed-size vector for each cluster, this architecture retains individual mention representations for cluster-level attention.

The paper reports benefits in long-document and out-of-domain experiments, although this introduces different computational characteristics from direct antecedent scoring.

Availability distinction: All three architectures appear in the research implementation, but the project's prominently advertised ready-to-use Hugging Face checkpoints are MES models. The presence of S2E and incremental model classes should not be interpreted as evidence that equivalent officially supported pretrained checkpoints are distributed for every configuration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://aclanthology.org\&sz=32)

aclanthology.org+2



Architecture source files:

- [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_s2e.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_s2e.py?utm_source=chatgpt.com)
- [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_mes.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_mes.py?utm_source=chatgpt.com)
- [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_incr.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_incr.py?utm_source=chatgpt.com)

## 3. Pretrained models and annotation regimes

The officially documented model collection contains three main MES checkpoints.

| Checkpoint                           | Training corpus | Reported score | Singleton annotation |
| ------------------------------------ | --------------- | -------------- | -------------------- |
| `sapienzanlp/maverick-mes-ontonotes` | OntoNotes       | 83.6           | No                   |
| `sapienzanlp/maverick-mes-preco`     | PreCo           | 87.4           | Yes                  |
| `sapienzanlp/maverick-mes-litbank`   | LitBank         | 78.0           | Yes                  |

Scores are from the project's model table and correspond to different evaluation datasets. They are not directly comparable measurements of general model quality.

### OntoNotes model

OntoNotes contains a diverse collection of English genres, including news, conversational material, and other edited or transcribed text.

Its annotation scheme concentrates on coreferential expressions rather than exhaustively retaining every one-off referential mention.

Consequently, the OntoNotes checkpoint is a general-purpose starting point when the principal objective is finding repeated references to the same discourse entity.

It is less suitable as an exhaustive mention detector, because the absence of annotated singletons affects what the model is encouraged to learn.

### PreCo model

PreCo was specifically developed as a large coreference dataset with extensive singleton annotations.

The PreCo-trained Maverick checkpoint can therefore be more appropriate when retaining entities mentioned only once is important.

This is particularly consequential for downstream processing that needs a comprehensive inventory of detected referential spans rather than just multi-mention clusters.

However, PreCo's domain and annotation conventions differ from OntoNotes. A higher reported score does not establish that the PreCo checkpoint performs better across arbitrary English documents.

### LitBank model

LitBank focuses on literary texts, which introduce distinctive challenges:

- Repeated characters and narrative entities.
- Long-distance references.
- Alternation among names, pronouns, and nominal descriptions.
- Character-focused chains extending through narrative discourse.

The LitBank model also supports singleton annotations.

Its suitability depends on the text being processed and the desired mention inventory. Its literary annotation conventions are not automatically interchangeable with the OntoNotes or PreCo conventions.

### Why the annotation regime matters

The choice of training corpus changes more than accuracy. It changes the operational meaning of a predicted mention.

A model can fail to extract a span because it does not recognize the expression, or because its learned annotation scheme excludes that kind of mention.

This distinction becomes especially important when comparing models, combining coreference with named-entity extraction, or using model outputs to create structured entity records.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

SapienzaNLP/maverick-coref · GitHub+1



Checkpoint pages:

- [https://huggingface.co/sapienzanlp/maverick-mes-ontonotes](https://huggingface.co/sapienzanlp/maverick-mes-ontonotes?utm_source=chatgpt.com)
- [https://huggingface.co/sapienzanlp/maverick-mes-preco](https://huggingface.co/sapienzanlp/maverick-mes-preco?utm_source=chatgpt.com)
- [https://huggingface.co/sapienzanlp/maverick-mes-litbank](https://huggingface.co/sapienzanlp/maverick-mes-litbank?utm_source=chatgpt.com)

## 4. Python inference API and output contracts

The package exposes a compact interface through the `Maverick` class.

### 4.1 Model initialization and loading

```
from maverick import Maverickmodel = Maverick(    hf_name_or_path="sapienzanlp/maverick-mes-ontonotes",    device="cpu",)result = model.predict(    "Ada met Grace. She later spoke with her.")
```

This is an illustrative example, not an executed prediction.

The `hf_name_or_path` argument accepts either an official Hugging Face repository identifier or a local model checkpoint path.

Underneath the public wrapper, the implementation:

1. Resolves `weights.ckpt` from Hugging Face, or uses a local path.
2. Loads the model using PyTorch Lightning's `load_from_checkpoint`.
3. Constructs a Hugging Face fast tokenizer corresponding to the trained encoder.
4. Adds speaker-related special tokens.
5. Runs inference with gradient computation disabled.

The checkpoint is therefore not simply a standard Hugging Face `AutoModelForTokenClassification` checkpoint. The Maverick architecture and Lightning checkpoint-loading implementation are part of its runtime requirements.

Although the README describes the default CUDA device as `cuda:0`, the inspected source uses `device="cuda"`; both target the default CUDA device. CPU execution must be requested explicitly when CUDA is unavailable.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

SapienzaNLP/maverick-coref · GitHub+1



Source: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/maverick_model.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/maverick_model.py?utm_source=chatgpt.com)

### 4.2 Three accepted input formats

| Input                   | Example                                                  | Consequence                                                |
| ----------------------- | -------------------------------------------------------- | ---------------------------------------------------------- |
| Raw string              | `"Ada met Grace. She smiled."`                           | Automatic sentence splitting and word tokenization         |
| Flat word-token list    | `["Ada", "met", "Grace", ".", "She", "smiled", "."]`     | Preserves supplied tokens; sentence boundaries inferred    |
| Sentence-tokenized list | `[["Ada", "met", "Grace", "."], ["She", "smiled", "."]]` | Preserves supplied tokens and explicit sentence boundaries |

The third format is the most structurally controlled interface.

It avoids relying on Maverick to decide where sentences begin and end, and it enables the additional inference modes documented by the project.

For a flat word-token list, the current implementation infers sentence boundaries primarily from tokens equal to `"."`, with the document end as the final boundary. Other punctuation does not receive equivalent handling in that code path.

For raw strings, the implementation uses NLTK sentence tokenization and spaCy word tokenization.

These distinctions matter because sentence boundaries affect the set of spans Maverick is allowed to predict. They are not merely preprocessing metadata.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 4.3 Prediction output

The inspected implementation returns a Python dictionary with the following fields:

| Field                    | Contents                                                   |
| ------------------------ | ---------------------------------------------------------- |
| `tokens`                 | Flat sequence of input word tokens                         |
| `clusters_token_offsets` | Predicted clusters, expressed as document-wide token spans |
| `clusters_token_text`    | Mention strings associated with each cluster               |
| `clusters_char_offsets`  | Character spans, available for raw-string input            |
| `clusters_char_text`     | Present but currently `None`                               |

Each cluster is a collection of mention spans, and each span uses zero-based inclusive start and end indices.

For example, a token span `(4, 5)` refers to `tokens[4:6]`, not `tokens[4:5]`.

Character offsets are also generated with inclusive end positions. Consequently, extracting the original string associated with `(start, end)` requires `text[start:end + 1]`.

#### Important documentation discrepancy

The opening portion of the README calls the mention-text field `clusters_text_mentions`.

However, the inspected source constructs `clusters_token_text`, and later README examples also use that name.

Code relying on the published README's initial response example may therefore access a nonexistent key. The source implementation is the stronger reference for the actual returned dictionary.

The implementation also leaves `clusters_char_text` as `None`, even when character offsets are available.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 4.4 Character-offset alignment caveat

Maverick can produce character offsets for raw-string inputs, but these should not be treated as a universal source-preservation guarantee.

In the inspected preprocessing code, offsets are reconstructed by accumulating the length of each sentence plus one character between sentences:

```
off += len(sentence) + 1
```

That assumes a particular correspondence between sentence segmentation and the original whitespace. Documents containing multiple newlines, irregular spacing, or other nontrivial separators can violate that assumption.

For exact source provenance, a stronger arrangement is to preserve character offsets independently during tokenization, pass explicit word/sentence tokens to Maverick, and map returned token spans through the retained token-to-source alignment.

This is an integration implication derived from the source, not a separate offset-alignment facility provided by Maverick.

## 5. Advanced inference: controlled mentions, clusters, and speaker context

Maverick's additional prediction modes are among its most architecturally useful capabilities. They allow the model to participate in structured NLP workflows without always operating as an entirely unconstrained detector.

### 5.1 Singleton prediction

```
result = model.predict(    sentences,    singletons=True,)
```

Ordinarily, coreference evaluation and downstream use emphasize clusters with at least two mentions. With `singletons=True`, the model can additionally return clusters containing one detected mention.

This is useful when a downstream system needs to preserve both repeatedly mentioned entities and entities introduced only once.

However, the switch does not supply missing training supervision. OntoNotes does not annotate singletons in the same manner as PreCo or LitBank, so its checkpoint is not the appropriate choice when comprehensive singleton extraction is essential.

### 5.2 Clustering externally supplied mentions

```
mentions = [    (0, 0),    (2, 2),    (4, 4),    (7, 7),]result = model.predict(    sentences,    predefined_mentions=mentions,)
```

`predefined_mentions` bypasses the normal mention-extraction decision for the supplied spans and performs clustering over them.

This separates two concerns that are often tightly coupled:

\\[ \text{Mention detection} \quad\longrightarrow\quad \text{Coreference clustering} \\]

That separation creates several possibilities:

- Compare alternative mention detectors without changing the coreference model.
- Use gold-standard spans to measure clustering independently of detection.
- Restrict coreference predictions to an upstream-defined inventory.
- Combine specialized entity or span extraction with a general coreference scorer.

There is a major semantic condition: named entities and coreference mentions are not interchangeable concepts.

Coreference mentions can include pronouns, noun phrases, descriptions, and other referential expressions that conventional NER systems may never return. Feeding only named-entity spans into clustering can therefore discard much of the information required for effective pronoun and nominal-reference resolution.

The capability is most useful when the upstream mention inventory matches the intended coreference annotation regime.

### 5.3 Extending existing clusters

The `add_gold_clusters` parameter enables predictions starting from supplied clusters.

```
initial_clusters = [    [(0, 0), (4, 4)],    [(2, 2)],]result = model.predict(    sentences,    add_gold_clusters=initial_clusters,)
```

The project documents that supplied starting clusters appear first in the resulting token-offset cluster list. It consequently suggests selecting the first \\(N\\) returned clusters, where \\(N\\) is the number of starting clusters, when only the augmented starting clusters are of interest.

This supports a different problem from clustering predefined mentions:

| Mechanism             | What is supplied                | What Maverick determines                            |
| --------------------- | ------------------------------- | --------------------------------------------------- |
| Standard prediction   | Document                        | Mentions and clusters                               |
| `predefined_mentions` | Document and candidate mentions | Relationships among supplied mentions               |
| `add_gold_clusters`   | Document and starting clusters  | Additional assignments around the supplied clusters |

The third mechanism can be useful when some reference relationships are already known with high confidence.

It should not, however, be confused with persistent cross-document memory. The supplied clusters refer to token offsets within the current input, and the package does not thereby establish globally stable entity IDs across documents.

### 5.4 Speaker-aware coreference

Maverick additionally accepts `speakers` for OntoNotes-style sentence-tokenized inputs.

```
result = model.predict(    sentences,    speakers=[        ["Alice", "Alice", "Alice", "Alice"],        ["Bob", "Bob", "Bob", "Bob"],    ],)
```

Each token is associated with its speaker. The implementation inserts `[SPEAKER_START]` and `[SPEAKER_END]` special tokens when speaker identity changes.

This provides evidence that may help disambiguate first- and second-person references in dialogue or transcribed conversations.

It is important not to interpret this as speaker diarization: Maverick consumes speaker identities; it does not infer them from audio or perform diarization itself.

The repository README contains an apparent copy-paste error in its speaker example, passing `speakers=clusters` despite having constructed a `speakers` variable. The intended parameter is `speakers=speakers`.

Official examples and implementation:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

SapienzaNLP/maverick-coref · GitHub+1



[https://github.com/SapienzaNLP/maverick-coref#inference](https://github.com/SapienzaNLP/maverick-coref?utm_source=chatgpt.com#inference)

### 5.5 Linguistically specialized scoring in MES

The MES architecture has a less obvious dependency on lexical categories.

Its six scoring categories distinguish:

1. Compatible pronoun–pronoun pairs.
2. Incompatible pronoun–pronoun pairs.
3. Pronoun–nonpronoun pairs.
4. Mentions with matching content-word sets.
5. Mentions with a containment relationship.
6. Other mention pairs.

The implementation determines categories with pronoun lookup tables and set-based comparisons of mention content.

This is not a separate rule-based coreference engine. Instead, the rules select which learned scoring component contributes to the final decision.

It nevertheless has a consequence for extension: changing the language or token representation can affect these linguistic categories even when the underlying transformer encoder is multilingual.

Custom multilingual training may therefore require examining the category logic as well as replacing the encoder and training data.

Sources:

[https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/util.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/util.py?utm_source=chatgpt.com)

[https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/constants.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/constants.py?utm_source=chatgpt.com)

## 6. Training, fine-tuning, and evaluation

The repository contains substantially more than a pretrained inference wrapper. It includes the model classes, PyTorch Lightning integration, dataset loaders, configurable training infrastructure, and benchmark evaluation scripts.

### 6.1 Configuration architecture

The training system uses Hydra to compose configuration groups.

| Configuration area | Responsibility                                                                 |
| ------------------ | ------------------------------------------------------------------------------ |
| `conf/model/`      | Architecture, transformer encoder, model parameters, optimizer                 |
| `conf/data/`       | Dataset readers, paths, tokenizers, document-length rules, batch configuration |
| `conf/train/`      | Training precision, device configuration, epochs, checkpointing and callbacks  |
| `conf/evaluation/` | Evaluation checkpoint and device settings                                      |
| `conf/logging/`    | Experiment logging, including Weights & Biases                                 |
| `conf/root.yaml`   | Top-level selection and composition                                            |

The model configuration selects architecture-specific implementations such as `Maverick_mes`, rather than merely changing a Hugging Face checkpoint name.

A custom model experiment may therefore vary the encoder, architecture, training parameters, or dataset independently, provided the instantiated components remain compatible.

The standard research commands are:

```
python maverick/train.py
python maverick/evaluate.py
```

These are repository training/evaluation scripts, distinct from the public `Maverick.predict()` inference interface.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Configuration source: [https://github.com/SapienzaNLP/maverick-coref/tree/main/conf](https://github.com/SapienzaNLP/maverick-coref/tree/main/conf?utm_source=chatgpt.com)

### 6.2 Learning objective

Maverick trains the mention-detection and clustering components jointly.

The paper describes an objective composed of three terms:

\\[ \mathcal{L}\_{\mathrm{coref}} = \mathcal{L}\_{\mathrm{start}} + \mathcal{L}\_{\mathrm{end}} + \mathcal{L}\_{\mathrm{cluster}}. \\]

These correspond to mention-start prediction, conditioned mention-end prediction, and the clustering decisions.

This differs from approaches relying exclusively on antecedent marginal-likelihood training over a pruned set of candidate spans.

One important implication is that the quality of mention detection is an explicit optimization target, not merely an incidental consequence of learning antecedent compatibility.

That said, the training objectives remain interconnected: poor mention coverage still limits what the clustering model can recover.

### 6.3 Dataset representation

The training pipeline works with prepared, OntoNotes-like JSON Lines datasets.

The loader and preprocessing machinery operate on sentence-tokenized documents with associated cluster annotations and, where relevant, speaker information.

The repository provides configurations for OntoNotes, PreCo, and LitBank, along with experimental configurations or commented dataset references for additional corpora.

The default OntoNotes configuration specifies a training document-length setting of `max_doc_len: 1500` and batch size 1 for train, validation, and test.

These are configuration choices, not proof that all inference inputs are limited to 1,500 tokens.

Longer documents involve the interaction between model attention, memory, sequence preparation, and available compute.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Source: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/data/datasets.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/data/datasets.py?utm_source=chatgpt.com)

### 6.4 Training control and experiment tracking

The default training YAML provides:

- Single-GPU PyTorch Lightning execution.
- 16-bit mixed precision.
- Gradient accumulation over four batches.
- Gradient clipping.
- Deterministic execution settings.
- Early stopping based on validation CoNLL-2012 F1.
- Best-checkpoint retention based on the same metric.
- Learning-rate monitoring and optional experiment logging.

The configuration allows these choices to be changed, but changing precision, acceleration, or dependency versions may require compatible code and hardware.

The repository includes encoder fine-tuning rather than limiting training to a frozen feature extractor.

For domain adaptation, this means the complete model can potentially learn both different contextual representations and a different mention/clustering distribution.

Source: [https://github.com/SapienzaNLP/maverick-coref/blob/main/conf/train/default_train.yaml](https://github.com/SapienzaNLP/maverick-coref/blob/main/conf/train/default_train.yaml?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 6.5 Coreference evaluation

The official evaluation pipeline reports CoNLL-2012 coreference scores, using the standard combination of:

- MUC, emphasizing the links within coreference chains.
- B³, measuring mention-level cluster precision and recall.
- CEAF-φ4, measuring alignment between predicted and gold clusters.

Their averaged F1 is commonly used as the headline CoNLL coreference score.

The script can also write model predictions to a JSON Lines file under the experiments directory.

The availability of separate mention extraction and clustering components additionally permits diagnostics that hold gold mentions fixed, thereby distinguishing failure to find a mention from failure to assign a detected mention to the correct entity.

This distinction is particularly important when evaluating different domains: an apparent clustering problem may actually originate upstream in mention detection.

Evaluation script: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/evaluate.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/evaluate.py?utm_source=chatgpt.com)

## 7. Performance characteristics and scalability

### 7.1 Published experimental measurements

The ACL 2024 study reports the following results on the OntoNotes benchmark.

| Configuration                 | Parameters | Coreference F1 | Training time | Inference time | Inference peak memory |
| ----------------------------- | ---------- | -------------- | ------------- | -------------- | --------------------- |
| MES, DeBERTa-v3 base          | 223M       | 81.4           | 7 h           | 6 s            | 1.9 GiB               |
| MES, DeBERTa-v3 large         | 504M       | 83.6           | 14 h          | 14 s           | 4.0 GiB               |
| S2E, DeBERTa-v3 large         | 449M       | 83.4           | 14 h          | 13 s           | 4.0 GiB               |
| Incremental, DeBERTa-v3 large | 452M       | 83.5           | 29 h          | 29 s           | 3.4 GiB               |

Historical measurements reported by the authors. Training was measured using a single RTX 4090, and the inference timings describe evaluation over the OntoNotes development set, not individual-document latency. Hardware and methodology must be preserved when interpreting these numbers.

The results illustrate a useful accuracy–efficiency frontier:

- The base MES model is significantly smaller and faster than large MES, at some cost in benchmark accuracy.
- MES and S2E provide closely matched accuracy on OntoNotes.
- The incremental architecture has different runtime behavior and should not be assumed faster simply because it processes clusters incrementally.

The paper's especially large speedup over earlier systems arises substantially from its comparison with autoregressive generative methods.

It should not be interpreted as evidence that Maverick is 170× faster than every modern encoder-based coreference model.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://aclanthology.org\&sz=32)

aclanthology.org+1



### 7.2 Why it is efficient

The important optimizations operate at different levels:

Encoder reuse. Contextual embeddings are calculated and reused rather than regenerating a textual answer token by token.

Conditional mention extraction. Only selected candidate starts require conditioned endpoint scoring.

Sentence-boundary restrictions. Candidate spans crossing sentence boundaries are excluded.

Reduced clustering work. Earlier filtering means fewer mentions and mention pairs reach the clustering stage.

Lightweight scoring structures. The antecedent and incremental-cluster mechanisms are specialized for coreference rather than general-purpose generation.

These optimizations compound. Reducing mention candidates can produce more than a proportional reduction in antecedent-comparison work.

### 7.3 Long-document behavior

Maverick's paper includes long-document experiments and presents the approach as more practical on longer inputs than several competing systems.

However, several limits remain:

- Transformer attention can still grow quadratically with sequence length.
- Model initialization and inference depend on the selected encoder and memory capacity.
- The public `predict()` wrapper does not document automatic document chunking and cross-chunk reconciliation.
- The default training dataset configuration uses document-length controls.
- A collection of separately predicted chunks does not automatically constitute a globally consistent coreference analysis.

The distinction between long-document research results and unbounded document processing is important. Maverick supports the former within the evaluated conditions; the latter is not an established native capability.

### 7.4 Batch and streaming execution

The public `predict()` implementation handles one document per call and constructs model tensors with an explicit batch dimension of size one.

The underlying training system uses PyTorch DataLoaders, but that does not establish a public, optimized multi-document inference batching API.

There is also no documented native streaming interface or online cluster state maintained across independent calls.

A surrounding application can introduce batching, parallel execution, or incremental document workflows, but those capabilities should be attributed to that surrounding infrastructure unless the library itself is extended.

## 8. Integration boundaries and architectural opportunities

Maverick is most useful when its output is understood as a document-local equivalence relation over textual mentions.

It determines that several spans refer to the same discourse entity. It does not determine everything about that entity.

### 8.1 Relation to named-entity recognition

NER and coreference solve different problems.

NER generally identifies and classifies spans such as people, organizations, and locations.

Coreference identifies whether different expressions refer to the same thing:

> The company announced a merger. Its board approved the transaction.

The pronoun its may be part of the company's coreference chain even though a conventional NER model would not identify its as a named entity.

Combining the two systems can provide richer entity structures than either alone, but their spans and label semantics must be reconciled.

### 8.2 Relation to entity linking

Entity linking maps an entity mention or cluster to a canonical entity in an external knowledge base.

Maverick does not natively provide that mapping.

A coreference cluster can supply better context for linking—for example, combining a surname, full name, and several descriptive mentions—but it does not itself establish a Wikidata identifier or persistent application-level entity ID.

Similarly, two separate documents describing the same organization can receive internally correct clusters without Maverick establishing that those clusters represent the same real-world organization.

### 8.3 Relation to information and relation extraction

Coreference can help downstream extraction attribute facts to the intended entity.

For example, an extraction pipeline can use a predicted coreference chain to associate a later pronoun with an earlier noun phrase.

But coreference edges are not semantic relation edges.

Maverick can predict that it refers to the refinery. It does not, by itself, predict that the refinery is located in Texas, is owned by a corporation, or has a particular production capacity.

Those facts require separate extraction, grounding, or reasoning mechanisms.

### 8.4 Structured outputs versus textual rewriting

A notable advantage of Maverick is that it produces explicit span groupings rather than rewriting the entire input to replace every pronoun.

This keeps reference resolution separate from text generation and permits downstream applications to retain original passages, tokenize spans, and associate extracted records with original evidence.

However, the public output is clusters—not a canonical-entity object schema, confidence-calibrated entity registry, or provenance graph. Those are different layers of functionality.

## 9. Packaging, dependencies, licensing, and operational limitations

### 9.1 Distribution and dependency requirements

The latest verified PyPI release is 1.0.7, published June 10, 2025.

The package declares Python `>=3.8.0`. That is a minimum-version requirement, not a verified compatibility guarantee for all later Python versions.

The published distribution is a source archive rather than a prebuilt wheel.

Significant declared dependencies include:

| Component         | Declared dependency        | Role                                  |
| ----------------- | -------------------------- | ------------------------------------- |
| Transformers      | `transformers>=4.34`       | Encoder and tokenizer infrastructure  |
| PyTorch Lightning | `pytorch-lightning>=1.8.0` | Checkpoint loading and model training |
| Hydra             | `hydra-core>=1.2`          | Configuration composition             |
| spaCy             | `spacy>=3.7.2`             | Input preprocessing                   |
| NLTK              | `nltk==3.8.1`              | Sentence segmentation                 |
| SentencePiece     | `sentencepiece==0.2.0`     | Tokenizer dependency                  |
| Protobuf          | `protobuf==3.20`           | Pinned dependency                     |
| JSON Lines        | `jsonlines==4.0.0`         | Dataset handling                      |

The explicit pins on older versions of NLTK, Protobuf, and SentencePiece are worth distinguishing from the library's broader `>=` requirements.

Current versions of Python, PyTorch, and Transformers can introduce compatibility changes outside the original tested environment.

The project also depends on tokenizer assets and an English spaCy pipeline for relevant preprocessing paths. The source can attempt to obtain missing language resources at runtime, which introduces an additional dependency on resource availability.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



[https://github.com/SapienzaNLP/maverick-coref/blob/main/setup.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/setup.py?utm_source=chatgpt.com)

[https://github.com/SapienzaNLP/maverick-coref/blob/main/requirements.txt](https://github.com/SapienzaNLP/maverick-coref/blob/main/requirements.txt?utm_source=chatgpt.com)

### 9.2 Licensing

The project's PyPI page identifies the software and data license as Creative Commons Attribution-NonCommercial-ShareAlike 4.0.

This is a consequential constraint.

The NonCommercial condition means the project should not be treated as equivalent to a permissively licensed library such as MIT or Apache-2.0.

Use in commercial products, services, or enterprise deployments requires a separate licensing assessment or appropriate authorization.

The exact implications of model checkpoints, training datasets, and derivative models should also be considered individually rather than assuming every associated artifact has unrestricted licensing.

Primary license declaration: [https://github.com/SapienzaNLP/maverick-coref/blob/main/LICENSE.txt](https://github.com/SapienzaNLP/maverick-coref/blob/main/LICENSE.txt?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



### 9.3 Reported compatibility problems

Several 2026 issue reports indicate that the released package can encounter difficulties with newer environments.

One issue describes empty clusters from the official checkpoints on a macOS ARM environment. A later commenter reported differing results across checkpoints, so the issue does not demonstrate that all models are universally broken.

Another report describes a PyTorch dtype mismatch during prediction.

These are user-reported, environment-specific problems, not established guarantees about every installation. I did not run the package or independently reproduce them.

Nevertheless, they are relevant because package metadata allows fairly broad dependency versions while the published implementation relies on PyTorch Lightning checkpoints and older pinned packages.

Issue references:

- Empty prediction clusters: [https://github.com/SapienzaNLP/maverick-coref/issues/17](https://github.com/SapienzaNLP/maverick-coref/issues/17?utm_source=chatgpt.com)
- Prediction dtype failure: [https://github.com/SapienzaNLP/maverick-coref/issues/15](https://github.com/SapienzaNLP/maverick-coref/issues/15?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1

### 9.4 Other limitations and unverified capabilities

| Area                               | Established position                                                                              |
| ---------------------------------- | ------------------------------------------------------------------------------------------------- |
| Languages                          | Official highlighted checkpoints target English                                                   |
| Multilingual models                | Architecture can be adapted, but equivalent official multilingual checkpoints are not established |
| Cross-document coreference         | No documented native persistent identity mechanism                                                |
| Confidence scores                  | Not exposed by the documented high-level prediction dictionary                                    |
| Token-level provenance             | Token offsets provided; exact original-character alignment needs care                             |
| Concurrent inference               | No explicit thread-safety or concurrency guarantee established for `Maverick.predict()`           |
| Native REST service                | Not part of the documented original package API                                                   |
| ONNX/TensorRT export               | No official optimized export path established in the reviewed documentation                       |
| Arbitrary-length document handling | No native automatic segmentation-and-reconciliation guarantee                                     |
| Continued development              | Research code is available, but future support and compatibility are not guaranteed               |

These are boundaries of the documented, inspected implementation—not claims that the functionality could never be implemented.

### 9.5 Related German-language implementation

A separately maintained project, `maverick-coref-de`, adapts Maverick for German.

Repository: [https://github.com/uhh-lt/maverick-coref-de](https://github.com/uhh-lt/maverick-coref-de?utm_source=chatgpt.com)

German checkpoint: [https://huggingface.co/fynnos/maverick-mes-de10](https://huggingface.co/fynnos/maverick-mes-de10?utm_source=chatgpt.com)

This is useful evidence that Maverick's architecture can be applied beyond English. It should nevertheless be treated as a distinct implementation with its own checkpoints, packaging, behavior, and deployment features.

In particular, the German fork documents deployment interfaces that should not be automatically attributed to the original `maverick-coref` Python package.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 10. Overall technical assessment

Maverick's most distinctive contribution is its combination of efficient neural mention extraction, specialized coreference clustering, and unusually useful inference constraints.

Several aspects make it more than a straightforward pretrained model wrapper.

First, its conditional start–end formulation reduces the candidate span problem before clustering. That makes the model's efficiency gains structural rather than merely attributable to using a smaller encoder.

Second, the presence of three clustering architectures provides meaningful research and extension flexibility. MES introduces linguistically specialized scoring, whereas incremental clustering operates over evolving entity clusters.

Third, the public inference interface supports separable and constrained processing. `predefined_mentions` allows independent mention detection, and `add_gold_clusters` allows existing document-local clusters to participate in further resolution. Those capabilities can reduce the need for custom mechanisms that would otherwise reproduce parts of a coreference model.

Fourth, the PreCo and LitBank checkpoints support singleton-aware outputs. This substantially changes what constitutes a usable mention inventory, especially when coreference is integrated with broader structured text processing.

Its main constraints are equally consequential: the official checkpoints and linguistic categorization are English-oriented; the high-level API does not implement cross-document identity management or optimized batching; raw-text offset alignment can be fragile; current dependency compatibility is not comprehensively established; and the noncommercial license materially restricts deployment options.

The central architectural distinction is that Maverick supplies document-local mention detection and coreference clustering—not entity linking, knowledge-graph construction, or general semantic understanding. Within that defined responsibility, it offers a technically substantive, configurable, and computationally efficient alternative to autoregressive coreference extraction.

## Primary source map

For further technical investigation, the most useful sources are:

| Subject                                               | Direct source                                                                                                                                                                                                                             |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Public API and documented inference modes             | [https://github.com/SapienzaNLP/maverick-coref](https://github.com/SapienzaNLP/maverick-coref?utm_source=chatgpt.com)                                                                                                                     |
| Actual inference implementation and outputs           | [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/maverick_model.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/maverick_model.py?utm_source=chatgpt.com)                             |
| Research architecture, loss functions, and benchmarks | [https://aclanthology.org/2024.acl-long.722.pdf](https://aclanthology.org/2024.acl-long.722.pdf?utm_source=chatgpt.com)                                                                                                                   |
| MES scoring implementation                            | [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_mes.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_mes.py?utm_source=chatgpt.com)                                       |
| Incremental clustering implementation                 | [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_incr.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_incr.py?utm_source=chatgpt.com)                                     |
| Mention-pair linguistic categories                    | [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/util.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/util.py?utm_source=chatgpt.com)                                                 |
| Training configuration                                | [https://github.com/SapienzaNLP/maverick-coref/tree/main/conf](https://github.com/SapienzaNLP/maverick-coref/tree/main/conf?utm_source=chatgpt.com)                                                                                       |
| Pretrained checkpoints                                | [https://huggingface.co/collections/sapienzanlp/maverick-coreference-resolution-66a750a50246fad8d9c7086a](https://huggingface.co/collections/sapienzanlp/maverick-coreference-resolution-66a750a50246fad8d9c7086a?utm_source=chatgpt.com) |
| Package releases and requirements                     | [https://pypi.org/project/maverick-coref/](https://pypi.org/project/maverick-coref/?utm_source=chatgpt.com)                                                                                                                               |

The overview distinguishes the upstream research findings, documented public behavior, inspected source implementation, and engineering implications. No local execution or independent benchmarking was performed.

# Maverick Coref — Technical Capability Addendum

Research date: November 8, 2026 | Applies to `maverick-coref` 1.0.7 and the reviewed upstream research implementation

This addendum supplements the original `maverick-coref` overview with capabilities and implementation details identified during the subsequent gap analysis. It concentrates on functionality not adequately covered previously, particularly alternative transformer backbones, long-document processing, incremental cluster modeling, training controls, evaluation tools, and consequential differences between internal model interfaces and the public Python API.

The latest verified PyPI release remains 1.0.7, published June 10, 2025. Source-level mechanisms described below should not automatically be interpreted as tested, stable public APIs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



## 1. Transformer backbone flexibility and Longformer integration

### 1.1 Configurable document encoders

Although the main published Maverick checkpoints use DeBERTa-v3, the research implementation supports other transformer backbones through Hugging Face's `AutoModel` and `AutoConfig` abstractions.

The MES configuration directory includes:

| Configuration               | Encoder family   |
| --------------------------- | ---------------- |
| `mes/deberta-base.yaml`     | DeBERTa-v3 base  |
| `mes/deberta-large.yaml`    | DeBERTa-v3 large |
| `mes/longformer-base.yaml`  | Longformer base  |
| `mes/longformer-large.yaml` | Longformer large |

The model constructs its contextual encoder from the configured Hugging Face model identifier, rather than hardcoding a DeBERTa-specific implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



This matters because the contextual encoder and task-specific coreference architecture solve different problems.

The encoder supplies contextual representations for the document's subtokens. Maverick's mention-extraction and clustering components subsequently use those representations to identify referential spans and their relationships.

Separating these responsibilities makes it possible to investigate different encoder families while retaining the general coreference formulation.

However, the implementation is not completely architecture-independent. It relies on assumptions about token embeddings, hidden-state shapes, tokenization, and model outputs.

For example, model construction accesses `self.encoder.embeddings.word_embeddings` when resizing embeddings to accommodate speaker-related special tokens. An encoder whose embedding interface differs from that assumption may require implementation changes.

Consequently, support for Hugging Face `AutoModel` should be understood as extensibility, not universal compatibility with arbitrary transformer architectures.

### 1.2 Longformer and sparse attention

Longformer is particularly relevant because it offers a different document-contextualization strategy from standard full self-attention.

For ordinary full attention, the attention interaction count grows approximately as

\\[ O(L^2) \\]

for a sequence of length \\(L\\).

Longformer uses a combination of sliding-window and selected global attention. Under bounded local windows and a bounded number of global tokens, the attention computation can scale more favorably with sequence length.

This can make longer document representations more practical than with a conventional full-attention encoder.

The advantage is conditional, however. A Longformer backbone does not automatically eliminate the quadratic structures elsewhere in Maverick, including mention-pair scoring and the dense sentence-boundary mask used by parts of its preprocessing.

It also does not automatically improve coreference accuracy. DeBERTa and Longformer differ in their attention patterns, pretrained representations, and training characteristics.

### 1.3 Model availability versus architectural support

Three distinct capabilities must be separated:

- Implemented: Maverick includes model configurations and code paths supporting Longformer-based experiments.
- Evaluated in research: The ACL 2024 work investigates long-context architectural alternatives.
- Publicly distributed: The main officially advertised inference checkpoints remain the MES models trained on OntoNotes, PreCo, and LitBank.

The presence of a Longformer configuration does not establish that a ready-to-use, equivalently trained Longformer checkpoint is available for every dataset.

Similarly, replacing an encoder in a configuration normally requires compatible model initialization and training; it is not equivalent to substituting a new backbone into existing DeBERTa-trained weights.

Sources:

MES configurations: [https://github.com/SapienzaNLP/maverick-coref/tree/main/conf/model/mes](https://github.com/SapienzaNLP/maverick-coref/tree/main/conf/model/mes?utm_source=chatgpt.com)

MES implementation: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_mes.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_mes.py?utm_source=chatgpt.com)

Published research: [https://aclanthology.org/2024.acl-long.722/](https://aclanthology.org/2024.acl-long.722/?utm_source=chatgpt.com)

## 2. Internal long-document inference

Maverick contains a less obvious long-document mechanism in the MES implementation. It is separate from the standard `Maverick.predict()` interface.

### 2.1 Three internal execution modes

`Maverick_mes.forward()` accepts an optional `longdoc` argument.

| Mode       | Implementation behavior                                        |
| ---------- | -------------------------------------------------------------- |
| `None`     | Standard full-document encoder execution                       |
| `"naive"`  | Calls `naive_long_doc_forward()` to segment encoder processing |
| `"proper"` | Placeholder without a completed implementation                 |

The `"proper"` branch contains only `pass`. It should not be treated as a functioning, more sophisticated alternative to the naive implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 2.2 Segmented encoding with joint mention clustering

The `naive_long_doc_forward()` method uses a default `max_seq_len` of 2,000 tokens.

Its processing strategy is structurally different from predicting independent coreference clusters for every chunk.

The method identifies segmentation points using the document's end-of-sentence mask, constructs input segments, applies the transformer encoder to individual segments, and performs mention extraction on the segment representations.

It then collects mention representations and their indices for subsequent clustering by the surrounding MES forward method.

Conceptually, for document segments \\(D_1,\ldots,D_k\\):

\\[ H_i=E(D_i), \\]

\\[ M_i=\operatorname{MentionExtract}(H_i), \\]

followed by

\\[ C=\operatorname{Cluster}(M_1\cup\cdots\cup M_k). \\]

Here \\(H_i\\) represents the contextual embeddings produced for segment \\(i\\), while \\(M_i\\) contains the retained mention representations.

This is a conceptual abstraction of the implementation rather than an exact reproduction of the source's tensor operations.

The key capability is that coreference decisions can still be made among mentions originating from different encoder segments.

This avoids the need to first produce disconnected clusters and subsequently reconcile their identities with an entirely separate clustering system.

There is an important limitation: the encoder representations are still calculated using segment-local context. Cross-segment clustering cannot reconstruct all contextual information that would have been available under joint full-document encoding.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 2.3 Runtime and memory limitations

The internal segmented approach does not establish arbitrary-length, constant-memory inference.

Several costs remain:

Dense EOS masking. The public wrapper constructs a NumPy array of shape \\(L\times L\\) for the sentence-boundary mask. Its storage and construction costs grow quadratically with the encoded sequence length.

Cross-document-segment mention comparisons. Joint clustering must process the collection of mentions identified across the segments. Its cost therefore depends on the total mention inventory, not only on the size of individual encoder segments.

Segmentation heuristics. The method uses sentence-boundary-derived indices and assumes that these provide suitable segmentation points. Long or irregularly segmented sentences can complicate that assumption.

Incomplete alternative mode. The `longdoc="proper"` branch does not implement an alternative production strategy.

Additionally, the code for the naive method contains bookkeeping and slicing logic that should be treated as research implementation details rather than a documented guarantee of correct reconstruction for every document shape.

### 2.4 Public API boundary

The public method has the following signature:

```
Maverick.predict(    sample,    singletons=False,    add_gold_clusters=None,    predefined_mentions=None,    speakers=None,)
```

It does not expose `longdoc`.

A caller using the standard wrapper therefore receives ordinary model execution, not automatic selection of segmented long-document inference.

Accessing `longdoc="naive"` requires working below the high-level prediction interface and handling the model's tensor inputs, token mappings, and output reconstruction.

Architectural implication: The internal method provides a foundation for joint clustering across separately encoded segments, but it is not a drop-in streaming or unlimited-document capability.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_mes.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_mes.py?utm_source=chatgpt.com)

## 3. Incremental clustering: DistilBERT-based mention-to-cluster attention

The original overview described Maverick's incremental architecture but did not fully explain the mechanism that represents and evaluates existing clusters.

### 3.1 Specialized cluster-compatibility transformer

`Maverick_incr` constructs an internal `DistilBertForSequenceClassification` model with a custom configuration.

The implementation exposes these defaults:

| Parameter                       | Default |
| ------------------------------- | ------- |
| `incremental_model_hidden_size` | 384     |
| `incremental_model_num_layers`  | 1       |
| Number of output labels         | 1       |

Rather than processing ordinary text through a pretrained DistilBERT tokenizer, this component consumes representations already produced by Maverick.

Its embedding sequence consists of the new mention representation followed by representations of the mentions belonging to an existing cluster.

Those embeddings are passed through `inputs_embeds`, with an attention mask identifying valid representations.

The classifier computes a compatibility logit for the candidate mention and cluster.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 3.2 Mention-to-cluster scoring rather than centroid matching

This formulation differs from assigning each cluster a fixed-dimensional centroid.

Given a new mention \\(m\\) and an existing cluster

\\[ C_j=\\{m_1,m_2,\ldots,m_n\\}, \\]

the incremental classifier evaluates a sequence conceptually equivalent to

\\[ [\mathbf h_m,\mathbf h\_{m_1},\ldots,\mathbf h\_{m_n}]. \\]

A transformer-based scoring network can attend across the sequence and capture interactions between the new mention and different existing cluster members.

This may be valuable when a cluster contains heterogeneous expressions.

For example, an entity might be mentioned by a complete name, shortened name, pronouns, and descriptive noun phrases. A compatibility decision based on the individual members can access evidence that would be obscured by a simple average representation.

This is an architectural possibility, not a guarantee that all such relationships are correctly resolved.

### 3.3 Inference-time assignment

For each newly considered mention, the model evaluates candidate existing clusters.

The implementation applies a sigmoid threshold of 0.5 to determine whether any cluster is compatible.

If none passes the threshold, it creates a new cluster containing the mention.

If at least one passes, it selects the highest-scoring candidate cluster using `argmax`.

This produces a greedy incremental clustering process rather than a global optimization over all possible partitions.

Earlier decisions influence the cluster representations considered for later mentions.

Consequently, the approach introduces an order dependency: an incorrect early assignment can affect subsequent classification decisions.

### 3.4 Training-time cluster-size sampling

The implementation contains a significant asymmetry between training and inference.

In `get_cluster_states_matrix()`, clusters with more than 30 mentions are sampled down to a maximum of 30 during training.

The selection retains the first and final mentions and samples 28 additional mentions.

For shorter clusters, all members are retained.

During inference, the same explicit 30-mention restriction is not applied.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



This distinction affects both computational behavior and the distribution of representations seen by the cluster classifier.

Training operates on bounded cluster-context sequences, improving tractability for entities mentioned many times.

Inference may process substantially longer cluster-context sequences.

As a result:

- Cluster representation costs are not necessarily fixed at inference.
- Large clusters can require more attention computation and memory.
- Inference on very long mention chains can encounter sequence-length constraints that are less visible during training.
- Training samples only a subset of relationships within large clusters, while inference potentially sees the complete accumulated cluster context.

The sampling code itself includes the two endpoint mentions among the candidates passed to `random.sample()`. Thus, the exact source does not guarantee that the 28 sampled members are distinct from the endpoints; the intended 30-member representation may contain repeated mention positions.

### 3.5 Relation to online coreference

The architecture is incremental with respect to mentions within a document, but this does not establish a persistent online processing API.

Maverick still performs document encoding and constructs its mention representations from the supplied input.

The incremental cluster classifier then traverses those mentions sequentially.

It does not natively expose a durable cluster-state object that can be updated indefinitely as new documents arrive.

Supporting that behavior would require additional state management and decisions about how to represent contextual embeddings across independently encoded text.

Source: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_incr.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_incr.py?utm_source=chatgpt.com)

## 4. MES scoring: universal and linguistically specialized components

### 4.1 Seven scoring channels, not six independent scorers

The MES architecture's scoring mechanism is more nuanced than simply selecting one of six linguistic experts.

The implementation defines six linguistic categories and adds a seventh, universal category:

```
self.num_cats = len(CATEGORIES) + 1  # +1 for ALL
```

For each eligible mention–antecedent pair, the model uses the scoring channel associated with its linguistic category together with the universal channel.

The resulting score can be summarized conceptually as

\\[ s(m_i,m_j) = s\_{\mathrm{universal}}(m_i,m_j) + s\_{\mathrm{category}(i,j)}(m_i,m_j). \\]

The actual implementation calculates category-specific start-to-start, end-to-end, start-to-end, and end-to-start interactions with learned projections and bilinear scoring matrices.

It then applies category masks, restricts scores to valid antecedent positions, and sums the applicable category contributions before decoding.

The resulting architecture combines shared compatibility evidence with parameters specialized for different linguistic relationships.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 4.2 Category assignment is deterministic

The six linguistic categories are determined by `get_category_id()` using mention-level lexical information.

| Category              | Selection criterion                                  |
| --------------------- | ---------------------------------------------------- |
| Compatible pronouns   | Both mentions have the same pronoun-group identifier |
| Incompatible pronouns | Both are pronouns from different groups              |
| Pronoun–entity        | Exactly one mention is identified as a pronoun       |
| Matching mentions     | The normalized content-token sets are equal          |
| Containment           | One content-token set is contained in the other      |
| Other                 | No preceding category applies                        |

These categories are evaluated in precedence order.

A mention is recognized as a pronoun only when its normalized token set contains exactly one token found in the predefined pronoun groups. The implementation also removes specified English stopwords before comparing nonpronoun content sets.

Notably, these rules operate on sets rather than complete ordered token sequences. The matching and containment tests therefore capture lexical overlap, not full syntactic or semantic equivalence.

### 4.3 Consequences for alternative languages and domains

The categorization logic depends on explicit English-language resources, including pronouns such as he, she, it, they, and you, along with English stopwords.

This creates an important distinction between encoder portability and complete model portability.

A multilingual or domain-specific encoder could generate valid contextual representations while the MES category logic still assigns inappropriate linguistic classes.

For example, pronouns in a morphologically rich language may not match the English lookup tables. Similarly, lexical normalization that is adequate for ordinary English may be insufficient for specialized terminology or heavily inflected expressions.

Adapting the model can therefore involve both learning new contextual representations and changing the deterministic category-assignment layer.

The category machinery is relatively small compared with the transformer backbone, making it a clearly identifiable extension point. However, modifying category definitions also affects the distribution of inputs to the learned specialized scorers, so retraining or fine-tuning may be necessary.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



Category definitions: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/constants.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/constants.py?utm_source=chatgpt.com)

Category assignment: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/util.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/util.py?utm_source=chatgpt.com)

## 5. Additional training and optimization capabilities

### 5.1 Encoder freezing

The model constructors support a `freeze_encoder` configuration parameter.

When enabled, the implementation sets `requires_grad=False` on the document encoder's parameters.

This permits training the coreference-specific components while retaining fixed contextual representations from the underlying transformer.

The distinction is useful when comparing adaptation strategies:

| Dimension                    | Full encoder fine-tuning             | Frozen encoder                     |
| ---------------------------- | ------------------------------------ | ---------------------------------- |
| Contextual representations   | Adapted to coreference training data | Remain fixed                       |
| Task-specific layers         | Trained                              | Trained                            |
| Encoder gradient computation | Required                             | Avoided for encoder parameters     |
| Encoder optimization state   | Generally required                   | Not required for frozen parameters |
| Adaptation flexibility       | Greater                              | More restricted                    |

Encoder freezing can reduce training computation and optimization-state memory, although it does not eliminate the forward-pass cost of the encoder.

It can also constrain adaptation when domain-specific language differs substantially from the encoder's pretraining distribution.

The setting is present in the MES, S2E, and incremental implementations. The published DeBERTa-large configuration sets it to `False`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



### 5.2 RAdam and Adafactor optimization

The training infrastructure includes two distinct optimizer paths.

RAdam is selected when the model's `opt` configuration equals `"RAdam"`. This path instantiates the configured `torch.optim.RAdam` optimizer.

Adafactor is used by the alternative `custom_opt()` path.

That path implements four parameter groups, distinguishing parameters by head membership and weight-decay eligibility.

| Parameter group             | Learning rate        | Weight decay |
| --------------------------- | -------------------- | ------------ |
| General model parameters    | \\(2\times10^{-5}\\) | 0.01         |
| General no-decay parameters | \\(2\times10^{-5}\\) | 0            |
| Head parameters             | \\(3\times10^{-4}\\) | 0.01         |
| Head no-decay parameters    | \\(3\times10^{-4}\\) | 0            |

The higher head learning rate reflects the architectural distinction between pretrained encoder parameters and task-specific prediction components.

This can allow newly initialized components to adapt faster than the pretrained backbone.

However, the implementation's head-identification logic contains a consequential detail:

```
head_params = ["representaion", "classifier"]
```

The identifier `representaion` is misspelled.

Since parameter names are matched through substring tests, parameters containing the correctly spelled `representation` will not match that entry.

Some task-specific parameters may therefore be assigned to the general parameter groups rather than the intended higher-learning-rate groups.

This does not demonstrate that every published training run was affected in the same way, but it means the source's actual grouping behavior should not be assumed equivalent to its apparent design intent.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 5.3 Learning-rate scheduling

The custom Adafactor path uses `transformers.get_linear_schedule_with_warmup()`.

It calculates warmup steps as 10% of the configured total training steps.

This is a subtle distinction from the Hydra configuration, which separately includes a `num_warmup_steps` value. The inspected custom optimizer code derives its warmup count from `num_training_steps` instead of directly using that configured warmup field.

The RAdam path returns the optimizer directly without the same explicit scheduler.

Thus, optimizer selection also changes the learning-rate scheduling behavior.

### 5.4 Representation-layer extensibility

Maverick contains a reusable `RepresentationLayer` abstraction supporting multiple layer types:

| Type                 | Implementation                                                                |
| -------------------- | ----------------------------------------------------------------------------- |
| `Linear`             | Linear projection                                                             |
| `FC`                 | Fully connected network with nonlinear activation, normalization, and dropout |
| `LSTM-left`          | LSTM-based representation path                                                |
| `LSTM-right`         | Alternative LSTM-based path                                                   |
| `LSTM-bidirectional` | Bidirectional LSTM representation                                             |
| `Conv1d`             | One-dimensional convolutional representation path                             |

The model implementations currently select `"FC"` directly for their relevant representation layers.

Therefore, the abstraction exposes additional source-level architectural possibilities, but these should not be presented as fully supported configuration switches.

Some alternative branches also contain tensor-shape assumptions that would need examination before use.

The practical significance is that Maverick already separates representation transformations from its mention-extraction and clustering logic. Alternative representations can be investigated without redefining the entire coreference architecture, but their correctness and performance are not established by the presence of those branches.

Source: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/util.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/util.py?utm_source=chatgpt.com)

## 6. Dataset processing, caching, and annotation transformations

### 6.1 Processed dataset caching

The training dataset implementation uses the Hugging Face Datasets library for processed dataset storage.

`OntonotesDataset` first attempts to load a previously processed dataset through `load_from_disk()`.

If the processed dataset is unavailable, it reads the source annotation data into a DataFrame, creates a Hugging Face dataset, applies preprocessing and encoding transformations, and saves the processed result for eligible stages.

This separates potentially expensive document preparation from repeated model-training experiments.

The cached data contains tokenized representations and document metadata rather than only the original JSON Lines annotations.

That makes caching valuable, but creates a compatibility obligation.

A cached dataset prepared for one tokenizer or annotation convention may not remain valid after changing the encoder, tokenization rules, speaker handling, or input dataset.

The implementation's cache lookup is path-based. It does not establish automatic validation against all relevant preprocessing parameters.

A dataset-cache path should therefore be regarded as identifying a particular prepared representation, not merely a particular source corpus.

### 6.2 Filtering rather than automatic truncation

The training dataset provides both `prepare_data()` and `cut_document_to_length()`.

The distinction between them is important.

`prepare_data()` filters the training dataset using the tokenized sequence length:

```
len(tokenizer(tokens)["input_ids"]) <= max_doc_len
```

The constructor invokes this filtering operation for newly processed training data.

By contrast, the invocation of `cut_document_to_length()` is commented out.

As implemented in the reviewed path, overlength training documents are therefore excluded rather than automatically shortened to fit the configured maximum length.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



This behavior has consequences for model adaptation.

Length-based filtering changes the training distribution, potentially underrepresenting long documents, complex narratives, and entities whose reference chains span many sentences.

A different strategy that divided long documents into shorter examples would preserve more source material but change the available cross-segment coreference supervision.

Neither strategy is universally preferable. The relevant distinction is that Maverick's configured training limit currently acts as a filter in the reviewed dataset path.

### 6.3 Word-to-subtoken mapping

Maverick performs coreference over contextual transformer representations, while source annotations are usually defined over words.

The dataset preparation machinery explicitly maintains mappings between these coordinate systems.

The main structures include:

| Structure                | Responsibility                                                        |
| ------------------------ | --------------------------------------------------------------------- |
| `token_to_new_token_map` | Map original word indices to positions after speaker-token insertion  |
| `new_token_map`          | Map modified word-sequence positions back to original word indices    |
| `subtoken_map`           | Associate transformer subtokens with modified word-sequence positions |
| `EOS_indices`            | Represent sentence boundaries in tokenized coordinates                |
| `gold_clusters`          | Gold mention spans converted to encoded-sequence coordinates          |

Gold mention boundaries are converted using Hugging Face fast-tokenizer functionality such as `word_to_tokens()`.

For a source span \\((a,b)\\), the model-space span uses the first subtoken of word \\(a\\) and the last subtoken of word \\(b\\).

The end offset is adjusted because the fast tokenizer's span endpoint is exclusive, whereas Maverick stores inclusive mention endpoints.

This explicit mapping is important for preserving coreference relationships through subword tokenization and speaker-token insertion.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 6.4 Filtering invalid special-token spans

The `original_token_offsets()` utility reconstructs original word spans from model-space predictions.

It also filters mention spans when the relevant positions cannot be mapped back to ordinary source tokens.

The implementation comments identify special tokens and inserted speaker names as examples of positions that may otherwise be predicted as mentions.

This is a useful correction mechanism at the boundary between neural predictions and the external output contract.

It does not guarantee that every returned mention is semantically valid. It specifically addresses predictions whose boundaries are incompatible with the maintained token mappings.

The distinction matters when interpreting apparently missing mentions: some candidates may have been removed during output reconstruction rather than rejected by mention extraction itself.

Source: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/util.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/util.py?utm_source=chatgpt.com)

## 7. Expanded evaluation functionality

The repository contains a richer evaluation framework than the standalone CoNLL-2012 scoring command reveals.

### 7.1 Separate mention and clustering diagnostics

`BasePLModule.evaluate()` maintains separate evaluators for mention starts, complete mentions, and mentions contained in predicted clusters.

Its output includes the following metric families:

| Metric prefix      | Meaning                                                            |
| ------------------ | ------------------------------------------------------------------ |
| `start_`           | Accuracy of predicted mention-start positions                      |
| `mention_`         | Accuracy of complete predicted mention spans                       |
| `cluster_mention_` | Agreement between gold and predicted clustered-mention inventories |
| `muc_`             | MUC cluster evaluation                                             |
| `b_cubed_`         | B³ cluster evaluation                                              |
| `ceafe_`           | CEAF-φ4 cluster evaluation                                         |
| `conll2012_`       | Averaged CoNLL evaluation                                          |

Each family supplies precision, recall, and F1.

This supports a more informative decomposition of coreference performance than aggregate cluster F1 alone.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



For example, suppose a model correctly detects most mention starts but performs poorly on complete mention spans.

That suggests mention-boundary prediction is a more important contributor to error than initial start detection.

Alternatively, high complete-mention accuracy combined with poor coreference F1 indicates that antecedent selection or clustering is a major source of failure.

These diagnostics therefore make it possible to distinguish problems in different stages of the architecture without implementing entirely separate evaluation machinery.

Source-level caveat: In the reviewed implementation, `cluster_mention_evaluator.update()` appears to receive gold mentions as its first argument and predicted mentions as its second. The evaluator defines its first argument as predictions.

If used unchanged, this reverses the intended precision and recall interpretation for that metric family, while leaving its F1 unchanged.

### 7.2 LEA evaluation utility

The metrics module additionally implements `lea()`.

LEA, or Link-based Entity-Aware evaluation, assigns importance to entities according to their size and measures how successfully their internal coreference links are recovered.

Unlike some conventional coreference metrics, LEA explicitly incorporates entity importance into the scoring formulation.

The Maverick implementation computes the number of correctly resolved links within each cluster and weights the resulting contribution by the cluster's size.

This provides an additional evaluation perspective when large entity clusters matter.

However, `lea()` is a lower-level function in `maverick/common/metrics.py`.

It is not included in the default `OfficialCoNLL2012CorefEvaluator`, which initializes MUC, B³, and CEAF evaluators.

Therefore, LEA is implemented but is not an automatically reported headline metric.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Source: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/metrics.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/common/metrics.py?utm_source=chatgpt.com)

### 7.3 Additional evaluation datasets

The repository contains dataset configurations extending beyond its primary OntoNotes, PreCo, and LitBank checkpoint families.

| Dataset configuration | Purpose                                               |
| --------------------- | ----------------------------------------------------- |
| `gap.yaml`            | Pronoun-reference disambiguation evaluation           |
| `wikicoref.yaml`      | Evaluation on Wikipedia-derived coreference documents |
| `litbank-ns.yaml`     | LitBank evaluation without singleton annotations      |
| `preco-ns.yaml`       | PreCo evaluation without singleton annotations        |

The `-ns` configurations are particularly important for interpreting benchmark comparisons.

Singleton annotations materially affect the mention inventory used in evaluation. Filtering them changes what the evaluation is measuring, even when the underlying documents are unchanged.

These configurations allow the experimental framework to accommodate different annotation conventions.

They do not establish the existence of separate officially published pretrained checkpoints for every configuration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source: [https://github.com/SapienzaNLP/maverick-coref/tree/main/conf/data](https://github.com/SapienzaNLP/maverick-coref/tree/main/conf/data?utm_source=chatgpt.com)

### 7.4 GAP-specific pronoun disambiguation

The standalone evaluation script contains a special branch for GAP, a benchmark involving potentially ambiguous pronouns and candidate antecedents.

For each example, it determines whether the target pronoun belongs to the coreference cluster containing candidate A or candidate B.

The branch writes a tab-separated output containing a document identifier and Boolean decisions for each candidate.

Conceptually, given predicted clusters \\(C\\) and mentions \\(p,a,b\\), the evaluation determines:

\\[ A=\mathbb{1}[\operatorname{cluster}(p)=\operatorname{cluster}(a)] \\]

and

\\[ B=\mathbb{1}[\operatorname{cluster}(p)=\operatorname{cluster}(b)]. \\]

A candidate that is missing from the relevant predicted cluster does not receive a positive coreference decision.

This is a specialized evaluation transformation built on Maverick's ordinary cluster predictions.

It is useful because it demonstrates how cluster predictions can support an externally defined candidate-selection task without training a separate pronoun classifier.

Nevertheless, this is a benchmark-specific script path, not a general-purpose pronoun-disambiguation API.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/evaluate.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/evaluate.py?utm_source=chatgpt.com)

### 7.5 Visualization helper is not an established supported feature

The evaluation script defines a `jsonlines_to_html()` helper that invokes a separate JSON Lines-to-HTML conversion script.

However, its use is commented out in the reviewed evaluation workflow.

The invoked conversion script is not established as a working, packaged component of the official distribution.

Consequently, this should be described as an incomplete or unverified visualization integration, rather than an advertised native capability for rendering interactive or color-coded coreference documents.

## 8. Public inference and internal model interfaces: critical distinctions

### 8.1 MES, S2E, and incremental models are not fully interchangeable

The public `Maverick` class loads a Lightning checkpoint and invokes the underlying model with keyword arguments including:

```
tokens=...subtoken_map=...new_token_map=...singletons=...add=...
```

The MES forward method supports these arguments.

The inspected S2E and incremental forward methods have narrower signatures that omit those additional parameters.

This means loading an S2E or incremental checkpoint through the public wrapper does not, by itself, establish a compatible end-to-end prediction path.

The mismatch is especially important because the research implementation contains working model components and training-related machinery for those architectures.

Their presence should not be interpreted as proof that the published high-level interface provides the same capabilities for all model families.

The distinction is between:

| Layer                                                        | Availability                                                     |
| ------------------------------------------------------------ | ---------------------------------------------------------------- |
| MES research architecture                                    | Implemented                                                      |
| MES pretrained checkpoints                                   | Officially advertised                                            |
| MES high-level inference                                     | Documented and specifically supported by the wrapper             |
| S2E and incremental research implementations                 | Implemented                                                      |
| Equivalent S2E/incremental use through the unchanged wrapper | Not established; forward-signature incompatibilities are visible |

The exact runtime consequences of the mismatches were not independently tested.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



Public wrapper: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/maverick_model.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/maverick_model.py?utm_source=chatgpt.com)

S2E implementation: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_s2e.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_s2e.py?utm_source=chatgpt.com)

Incremental implementation: [https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_incr.py](https://github.com/SapienzaNLP/maverick-coref/blob/main/maverick/models/model_incr.py?utm_source=chatgpt.com)

### 8.2 Externally supplied mentions control clustering inputs, not every extraction computation

The public `predefined_mentions` argument is documented as clustering-only prediction.

Semantically, it allows the caller to specify the mentions used for clustering rather than relying on Maverick's predicted mention inventory.

However, the MES model still runs its `eos_mention_extraction()` method before selecting the externally supplied mention positions for clustering.

Consequently, using `predefined_mentions` should not be assumed to eliminate the computational cost of mention extraction.

Its principal value is semantic control of the clustering input, not a documented acceleration mechanism.

This matters when comparing alternative mention detectors. It permits consistent clustering experiments using an externally defined span inventory, but the default model forward pass may still perform unnecessary mention-extraction work for that mode.

### 8.3 Seeded clusters are not arbitrary logical constraints

The `add_gold_clusters` mechanism allows prediction to begin with supplied document-local clusters.

That is useful when some mention relationships are already established.

However, it does not provide a general framework for arbitrary clustering constraints.

In particular, the interface does not establish support for cannot-link rules, conflict resolution among inconsistent supplied clusters, or globally optimized constrained partitions.

Seeded cluster extension and constraint-based clustering are different mechanisms.

The former supplies initial cluster structure; the latter would require explicit semantics for allowable and prohibited assignments.

### 8.4 Model logits are not exposed as calibrated confidence scores

Internally, Maverick computes logits for mention starts, mention boundaries, antecedent relationships, and cluster compatibility.

These are useful model-level quantities.

However, the public `Maverick.predict()` dictionary does not return the full set of these scores.

It returns the reconstructed token sequence and coreference clusters, along with supported offset and mention-text representations.

Consequently, downstream confidence estimation cannot simply rely on a documented `confidence` property in the standard output.

Furthermore, applying a sigmoid to an internal logit does not establish calibrated probability semantics.

Applications requiring reliable uncertainty estimates would need to examine the appropriate internal model outputs and evaluate calibration against representative held-out data.

### 8.5 Preprocessing has avoidable repeated initialization costs

The public preprocessing function invokes `download_load_spacy()` for raw-text inputs and flat word-tokenized inputs.

That helper loads the English spaCy pipeline and checks for NLTK tokenizer resources.

Because this is performed inside the prediction preprocessing path, repeated calls may incur initialization work that could otherwise be reused.

The sentence-tokenized input path does not invoke the same helper.

Therefore, supplying sentence-tokenized input can provide more than explicit control over sentence segmentation: it can also avoid this portion of the wrapper's preprocessing work.

The magnitude of the difference depends on the runtime environment and workload and has not been measured here.

### 8.6 Research evaluation code also has interface mismatches

A related issue appears in `BasePLModule.test_step()`.

The method passes an `eos_indices` keyword argument to the underlying model, but the inspected MES forward signature does not accept that keyword.

This is a static source-level mismatch. It does not prove that every evaluation workflow fails, since the standalone evaluation script has its own prediction path.

It does mean that the presence of a Lightning testing method should not be taken as sufficient evidence that it works unchanged with the current MES implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



The most useful distinction is between a capability demonstrated by a public example, one implemented by the research scripts, and one implied by a lower-level class whose call sites may no longer agree with its signature.

## 9. Synthesis of the additional capabilities

The added material reveals several important architectural characteristics that are not apparent from the public API alone.

Encoder architecture and coreference architecture are separately configurable. Maverick can pair its task-specific mechanisms with different contextual encoders, including Longformer configurations, although the implementation imposes compatibility assumptions and the published checkpoints cover a narrower selection.

Long-document handling has an internal research implementation. Independently encoding segments while clustering their mentions jointly is a more powerful mechanism than merging independently predicted clusters, but its current code is not a documented production inference API.

Incremental clustering uses explicit attention over cluster members. This enables mention-to-cluster decisions based on the contents of an evolving cluster rather than solely on a fixed representation. The training-time sampling mechanism and unbounded inference cluster histories introduce important tradeoffs.

MES combines shared and specialized scoring. The universal scorer captures general compatibility while deterministic linguistic categories select additional learned scoring components. This makes its English-specific categorization machinery an important adaptation boundary.

The training and evaluation implementation contains more configurable machinery than the package documentation emphasizes. Encoder freezing, optimizer parameter groups, representation-layer abstractions, processed-data caching, separate mention diagnostics, LEA, and specialized benchmark paths are relevant capabilities.

Finally, the implementation contains several source-level inconsistencies affecting optimizer grouping, evaluation interfaces, and reported diagnostic semantics. These do not negate the published research results, but they are important when distinguishing usable library functionality from experimental or incompletely integrated code.

The combined overview and this addendum should therefore be read with three distinct levels of availability in mind: documented public functionality, internally implemented research functionality, and extension mechanisms that require additional engineering or validation.

All implementation observations above are based on upstream source inspection, not independent execution or benchmarking.