# Dipo — Comprehensive Python Library Overview

Research date: November 8, 2026 | Latest verified stable package release: 0.2.1 (October 12, 2026) | Python ≥3.10 | MIT license | Research-oriented, alpha-stage project

## 1. Overview and architectural significance

Dipo (Discourse Parsing Omnibus) is a Python library for automated discourse structure analysis, developed by Luke Gessler at Indiana University's Language and Computation Research group.

Repository: `https://github.com/larc-iu/dipo`

PyPI: `https://pypi.org/project/dipo/`

Dipo provides a unified implementation environment for neural discourse parsers, with pretrained models, training infrastructure, structured discourse representations, evaluation utilities, and command-line interfaces.

Its central capability is recovering the rhetorical organization of a document, rather than merely identifying individual linguistic elements.

Where sentence-level NLP identifies entities, grammatical dependencies, semantic roles, or relationships, discourse parsing attempts to establish how larger spans of text work together to construct a coherent argument, explanation, narrative, or document.

For example, given:

> The experiment showed significant improvement. However, the results could not be replicated. Therefore, the original hypothesis remains uncertain.

A discourse parser can identify that:

- The second statement contrasts with or qualifies the first.
- The third statement expresses a conclusion or consequence.
- The statements participate in a hierarchical structure, rather than forming three unrelated observations.

Dipo's principal formalism is Rhetorical Structure Theory (RST), which represents these relationships using elementary discourse units (EDUs), hierarchical attachments, rhetorical relation labels, and nuclearity assignments.

### Principal capability families

| Capability                         | What Dipo provides                                                                           |
| ---------------------------------- | -------------------------------------------------------------------------------------------- |
| Discourse segmentation             | Partition raw text into elementary discourse units                                           |
| Hierarchical discourse parsing     | Construct RST trees representing relationships between spans                                 |
| Rhetorical relation classification | Identify contrast, elaboration, cause, condition, evidence, and other relations              |
| Nuclearity identification          | Distinguish central discourse spans from supporting spans                                    |
| Neural parsing architectures       | Encoder-based, transition-based, generative, and LLM-based parsing implementations           |
| Multilingual parsing               | Published English, German, Chinese, Persian, and Basque checkpoints                          |
| Model training                     | Configurable training and evaluation, checkpoint management, PEFT, and curriculum mechanisms |
| Structured output                  | RST tree objects and RS3/RS4 serialization                                                   |
| Model distribution                 | Hugging Face Hub integration for pretrained checkpoints and publication                      |

The distinctive feature is not a single novel model. It is the combination of several discourse parsing architectures with common representations and supporting infrastructure, making different approaches to the same linguistic problem accessible through one Python package.

The project was previously named IUDEX, distributed as `larc-iudex`. The current package is `dipo`, and `import iudex` has been replaced by `import dipo`. The old CLI alias remains temporarily available but is deprecated.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



### Current scope

Although the project's name and logo reference several discourse formalisms, the verified implementation is currently concentrated on RST discourse parsing. The source tree contains several RST parser families, but equivalent production implementations for Penn Discourse Treebank (PDTB), Segmented Discourse Representation Theory (SDRT), or general discourse dependency parsing should not be assumed.

That distinction is important: an RST tree describes the rhetorical organization of text, but is not interchangeable with a PDTB connective-based relation graph, semantic dependency graph, coreference graph, or knowledge graph.

## 2. Parser architectures and release status

Dipo uses a parser registry rather than one universal model architecture. This makes it possible to study or deploy substantially different approaches to discourse analysis while retaining common RST representations.

A consequential version distinction emerged from inspecting the source: the `master` branch contains functionality added after PyPI 0.2.1. In particular, the Maekawa parser and standalone generative segmentation mode were added on October 19, 2026, seven days after the latest PyPI release.

| Parser             | Architecture                                                                      | Raw-text inference             | Availability            |
| ------------------ | --------------------------------------------------------------------------------- | ------------------------------ | ----------------------- |
| `dmrst`            | Transformer encoder, joint EDU segmentation, recurrent decoder, pointer attention | Yes                            | 0.2.1                   |
| `topdown_biaffine` | Top-down, neural span splitting and biaffine labeling                             | No; requires EDUs              | 0.2.1                   |
| `sr_biaffine`      | Bottom-up shift-reduce parser with neural action and label heads                  | No; requires EDUs              | 0.2.1                   |
| `gen`              | Transformer language model generating an RST tree serialization                   | Yes                            | 0.2.1                   |
| `icl`              | In-context-learning parser using external LLM endpoints                           | Yes                            | 0.2.1                   |
| `maekawa`          | LoRA-adapted causal LM queried for individual parsing decisions                   | Yes, with segmentation enabled | Development branch only |

The `gen` parser additionally supports an independent `seg` segmentation mode on `master`, but not in 0.2.1.

Source locations:

- Released parser registry: `https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/__init__.py`
- Development registry: `https://github.com/larc-iu/dipo/blob/master/dipo/rst/parsers/__init__.py`
- Changes since release: `https://github.com/larc-iu/dipo/compare/v0.2.1...master`

### 2.1 DMRST: joint segmentation and discourse parsing

`DMRSTParser` is the most straightforward released architecture for end-to-end neural discourse analysis without relying on a large generative language model.

It implements an approach based on DMRST: A Joint Framework for Document-Level Multilingual RST Discourse Segmentation and Parsing (Liu, Shi, and Chen, 2021).

The architecture combines:

1. A transformer encoder to compute contextual representations.
2. A segmentation head identifying EDU boundaries.
3. EDU-level representations and document-context encoding.
4. Recurrent, top-down structure prediction with pointer attention.
5. A classifier predicting nuclearity and rhetorical relations.

The segmentation and structural components are trained jointly, although the objective can be reweighted.

Advanced capabilities include:

- Sliding-window transformer encoding for inputs exceeding a backbone's ordinary positional window.
- Configurable pointer scoring, including dot-product and biaffine attention.
- Configurable aggregation of EDU representations.
- Joint segmentation with binary end-boundary prediction or alternative boundary-labeling schemes.
- Optional conditional random field (CRF) segmentation.
- Dynamic loss weighting between training objectives.
- Decoder activation checkpointing.
- Optional LoRA and encoder-layer freezing.
- Character-aware splitting for unspaced Chinese text.

These mechanisms make DMRST more than a thin wrapper around a pretrained checkpoint.

Architectural advantage: the encoder representation and discourse structure prediction are directly coupled. The parser need not generate the entire source document or a long textual description of its structure.

Tradeoff: the recurrent structural decoder still makes sequential decisions. The parser is not a single independent classification pass over every EDU pair, and its accuracy depends on both segmentation and the successive attachment decisions.

Primary sources:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/dmrst/modeling_dmrst.py`

`https://aclanthology.org/2021.codi-main.15/`

### 2.2 Top-down biaffine parsing

`TopdownBiaffineParser` operates over an existing EDU sequence.

Conceptually, it recursively selects a split point for a discourse span and assigns the nuclearity and rhetorical relation between the resulting children.

For a span containing EDUs \\(e_i,\ldots,e_j\\), the structural decision is approximately:

\\[ k^\*=\arg\max\_{i\leq k\<j}s\_{\mathrm{split}}(i,k,j) \\]

A separate scoring mechanism predicts the label for the selected split.

The implementation uses contextual transformer representations and deep biaffine scorers, allowing interactions between representations of candidate discourse spans.

Important characteristics:

- It does not require generating a long action sequence.
- It supports greedy top-down construction of binary discourse trees.
- Its scoring and labeling components are trained from gold discourse structure.
- It assumes an external or gold EDU segmentation rather than providing its own raw-text segmentation stage.

For systems that already have reliable EDU boundaries, this architecture makes it possible to isolate discourse attachment and relation classification from segmentation.

Source: `https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/topdown_biaffine/modeling_topdown_biaffine.py`

### 2.3 Shift-reduce biaffine parsing

`SRBiaffineParser` is the bottom-up counterpart.

It maintains a stack of constructed discourse spans and a queue of remaining EDUs, repeatedly selecting between:

- `SHIFT`: consume another EDU.
- `REDUCE`: combine the two topmost spans, assigning nuclearity and relation labels.

Its decision architecture contains two heads: an action classifier that decides whether to shift or reduce, and a deep biaffine label classifier for a reduction.

The implementation also applies legality constraints during decoding, for example disallowing a reduction when fewer than two stack items exist.

This has a different inductive bias from top-down parsing: the model builds local constituents before combining them into larger discourse structures.

The library's implementation departs from the reference architecture in some details, particularly its use of a biaffine reduction-label head, joint nuclearity–relation labels, and omission of sentence/paragraph organization features.

These are meaningful differences when interpreting model behavior or comparing reported results.

Source: `https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/sr_biaffine/README.md`

Reference paper: `https://aclanthology.org/2022.findings-emnlp.501/`

### 2.4 `gen`: a configurable generative discourse parser

`GenParser` is Dipo's most architecturally flexible released parser. Rather than predicting splits with a specialized classifier, it fine-tunes a language model to produce a structured representation of the entire discourse tree.

Its design separates two choices:

| Dimension     | Options                   | Consequence                                                        |
| ------------- | ------------------------- | ------------------------------------------------------------------ |
| Backbone      | `seq2seq`, `decoder_only` | Encoder–decoder generation versus causal language-model generation |
| Serialization | `sr`, `sexp`              | Shift-reduce actions versus a nested, bracketed discourse tree     |

These dimensions compose into four model configurations without requiring four independently maintained implementations. A third serialization, `seg`, was subsequently introduced on the development branch.

Shift-reduce serialization represents the discourse tree as a sequence of EDU-consuming actions and reductions. A reduction specifies both the nuclearity arrangement and the rhetorical relation.

S-expression serialization instead describes the nested tree directly. For example, the following is an illustrative structure, not a model prediction:

```
(NS:explanation
    (The system failed.)
    (The configuration was invalid.))
```

The library supports preorder and postorder traversal for these structures.

#### Source copying versus language generation

An unusually important distinction is Dipo's `use_copy` mechanism.

With `use_copy=True`, the model predicts a structural `COPY` action for source content. The decoder then takes the next source token from a tracked cursor rather than allowing the model to freely generate an arbitrary replacement token.

This makes source reproduction a structural operation, rather than a natural-language generation task. It can reduce the risk of paraphrasing, omitted content, or textual hallucination during segmentation and parsing.

The scoring architecture depends on how labels are represented:

- `label_style="token"` uses compact special tokens for structural actions and joint nuclearity–relation labels, scored using a small output head.
- `label_style="words"` represents labels using ordinary vocabulary tokens and a terminator, permitting use of the pretrained language-model output head and its learned representations.
- `use_copy=False` permits full-vocabulary source generation with S-expressions, but requires full fine-tuning in the released implementation; combining that setting with LoRA is explicitly rejected.

This distinction matters because generating source text and predicting discourse structure compete for capacity and training loss. Dipo allows those operations to be separated without losing the ability to reconstruct a complete RST tree.

#### Constrained decoding

The generative parser implements legality-aware decoding rather than accepting arbitrary generated text and attempting to repair it afterward.

For shift-reduce output, a state machine tracks which actions are possible given the current stack, source position, and remaining EDUs.

For S-expressions, a pushdown automaton tracks structural validity, including nesting, labels, and legal transitions.

The implementation supports greedy decoding and beam search, including beam-state management and transformer KV-cache reordering. It also supports forcing gold EDU boundaries at evaluation time, which separates attachment and labeling quality from segmentation quality.

Two important limitations follow from the implementation:

1. Constrained syntax does not imply correct rhetorical analysis. A complete, structurally legal tree can still contain incorrect EDU boundaries, attachments, nuclearity, or relation labels.
2. Context budgets are hard constraints. If the model cannot finish its tree within the permitted decode budget or backbone positional limit, Dipo raises an `OverLengthError` rather than treating an unfinished tree as a normal prediction.

The released code also exposes a configuration for explicitly batched greedy decoding. This can amortize model execution over multiple documents, but batching is opt-in because floating-point execution differences can affect nearly tied decoding decisions.

There are two particularly important nonfeatures: `chat_template` and `width_band_loss` appear in the generative configuration, but their non-null behavior is explicitly not yet wired into the released parser. Their presence in a configuration dataclass must not be interpreted as implemented functionality.

Primary source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/gen/configuration_gen.py`

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/gen/decode.py`

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/gen/serializations/`

A published checkpoint demonstrating the architecture is the T5Gemma-based RST-DT parser.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face



### 2.5 `icl`: discourse parsing with frozen language models

`IclParser` provides a different approach: it asks an existing LLM to construct a discourse tree from instructions and worked examples, without performing Dipo-managed weight training.

It composes three independent concerns: the model provider, the tree serialization, and the inference pipeline.

Its provider abstraction supports Anthropic models and OpenAI-compatible endpoints, including self-hosted deployments through compatible inference servers such as vLLM and llama.cpp.

Its pipeline modes are:

| Mode       | Model operation           | Output                                                |
| ---------- | ------------------------- | ----------------------------------------------------- |
| `e2e`      | One call with raw text    | EDU segmentation and a complete RST tree              |
| `two_call` | First segment, then parse | A tree over model-generated EDUs                      |
| `gold_edu` | Parse existing EDUs       | Structure and labels, without evaluating segmentation |

The distinction between one-call and two-call operation is substantive. Separating segmentation from parsing makes the segmentation output independently inspectable and allows the second prompt to focus on the structure of an explicit EDU sequence.

#### Prompt and output infrastructure

The ICL implementation provides capabilities that are easily overlooked:

- Corpus-derived relation inventories inserted into prompts, restricting the intended label vocabulary.
- Reusable few-shot demonstrations, with configurable number, sampling seed, and maximum example size.
- Cached shared prompt prefixes, reducing repeated prompt-processing work where supported by the provider.
- Structured decoding of both shift-reduce and S-expression output into `RstTree`.
- A dry-run facility to inspect the assembled prompt without sending a model request.
- Configurable retries, timeouts, generation budgets, and explicit decoding temperature.
- Evaluation that accounts for malformed or failed parses rather than silently excluding them from aggregate results.

This parser is also notably different from the other families in its resource and deployment model: `IclParser` is not a PyTorch `nn.Module`, has no local model checkpoint, and uses its own prediction and evaluation CLIs.

#### Grammar-constrained LLM parsing

Dipo includes a constrained ICL pathway that can send a grammar to a compatible inference server.

In release 0.2.1, this is limited to GBNF grammars with llama.cpp-compatible serving, using shift-reduce serialization in a non-`e2e` pipeline.

Its constraints can express legal structural sequences and prevent an LLM from producing arbitrary invalid transitions.

The implementation also supports advanced handling for reasoning-enabled models: lazy grammar triggering can allow a model to generate its reasoning first and apply grammar restrictions to the final structural output. An optional client-side budget-forcing mechanism handles cases in which reasoning fails to terminate naturally.

This functionality is backend-sensitive. The configuration names `guidance` and `xgrammar` as alternative grammar backends, but the released implementation explicitly raises `NotImplementedError` for those choices. Likewise, Anthropic's provider path does not support this grammar-constrained mode.

Architectural tradeoff: ICL makes it possible to use large pretrained models without constructing a task-specific training pipeline, but output reliability, API cost, serving latency, privacy, and backend feature compatibility become central concerns.

Sources:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/icl/modeling_icl.py`

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/icl/configuration_icl.py`

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/icl/provider.py`

### 2.6 `maekawa`: decision-by-decision LLM parsing (development branch)

The October 19 development update introduces `MaekawaParser`, independently reimplementing the parsing approach from Maekawa et al. (EACL 2024).

Unlike `gen`, which generates a serialized tree as one continuing output sequence, `maekawa` repeatedly prompts a causal LM for individual parsing decisions.

It supports top-down and bottom-up parsing and three arrangements for its LoRA adapters:

- `unified`: one adapter produces structural and labeling decisions.
- `separate`: distinct adapters produce structural actions, nuclearity, and rhetorical relations.
- `joint`: structural decisions remain separate, while nuclearity and relation are predicted together.

The implementation batches decision requests across documents when they reach equivalent stages of the parsing process. It also records generated answers and fallbacks when a response is illegal.

The development version adds an EDU segmenter implemented using the `gen` segmentation serialization. This makes raw-text parsing possible without relying on externally supplied EDU boundaries.

The distinction from ICL is fundamental: `maekawa` fine-tunes task adapters and carries out a sequence of short model decisions; `icl` primarily prompts a frozen model; `gen` fine-tunes a model to emit a complete serialized output.

This parser should not be treated as available through the current PyPI 0.2.1 distribution. Nor does its inclusion in `master` establish that the author's later experiments have demonstrated superior accuracy across datasets.

Development source:

`https://github.com/larc-iu/dipo/blob/master/dipo/rst/parsers/maekawa/README.md`

Reference paper:

`https://aclanthology.org/2024.eacl-long.171/`

## 3. RST representations, serialization, and information preservation

Dipo's shared data structures are valuable independently of any particular parser. They provide a common way to inspect, transform, serialize, and evaluate discourse trees.

### 3.1 The `RstTree` model

The primary types are defined in `dipo.rst.data.tree`:

| Type      | Responsibility                                                                        |
| --------- | ------------------------------------------------------------------------------------- |
| `RstNode` | Terminal EDU or nonterminal discourse grouping                                        |
| `RstEdge` | Directed rhetorical attachment, with relation label and optional `secondary` marker   |
| `RstTree` | Nodes, edges, root, navigation, span computations, transformations, and serialization |
| `Shift`   | Commit an EDU in a bottom-up action sequence                                          |
| `Reduce`  | Combine spans using a nuclearity arrangement and relation                             |

The principal nuclearity codes are `NS`, `SN`, and `NN`:

- `NS`: left child is nucleus, right child is satellite.
- `SN`: left child is satellite, right child is nucleus.
- `NN`: both children are nuclei in a multinuclear relation.

This distinction is not simply an extra classification label. It establishes which part of a rhetorical construction carries central information and which part supports, qualifies, or elaborates it.

An RST representation can therefore describe both which spans are related and how their rhetorical importance differs.

`RstTree` exposes navigation and extraction operations such as `parent_of`, `relation_of`, `edus`, `edu_strings`, `nonterminals`, `parsing_actions`, `spans`, and `spans_with_ranges`.

The latter operations allow consumers to work with structured span boundaries and labels without traversing the underlying node and edge collections manually.

### 3.2 Multiple equivalent parser representations

The library supports transformations between tree structures and several parser-friendly forms:

| Representation       | Principal methods                             | Characteristics                                     |
| -------------------- | --------------------------------------------- | --------------------------------------------------- |
| RST tree             | `RstTree`, `RstNode`, `RstEdge`               | Hierarchical semantic structure                     |
| Split actions        | `parsing_actions()`, `from_parsing_actions()` | Split positions and labeled child relationships     |
| Shift-reduce actions | `to_shift_reduce()`, `from_shift_reduce()`    | Bottom-up transition representation                 |
| S-expressions        | `to_sexp()`, `from_sexp()`                    | Nested textual representation for generative models |
| RS4 XML              | `to_rs4_string()`                             | Interchange and inspection format                   |

The S-expression conversion supports both source-text-bearing leaves and positional EDU placeholders. It also supports preorder and postorder arrangements.

For the documented plan-style format, source and reconstruction are designed to round-trip when the serialization assumptions are respected.

The shift-reduce representation uses structured `Shift` and `Reduce` objects internally. This matters because a textual token such as `<reduce_ns_some_relation>` may normalize punctuation in a relation name. The compact string is not always independently invertible without the corresponding label mapping.

Together, these representations let training, inference, and evaluation share discourse semantics while different model architectures operate over different action spaces.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/tree.py`

### 3.3 Binary trees, multinuclear relations, and lossy transformations

RST corpora can contain multinuclear structures with more than two children. Many neural parsing formulations, however, produce binary split decisions.

Dipo handles this with binarization, creating binary structures that can be consumed by the parsing algorithms.

The reverse operation, `RstTree.debinarize()`, flattens eligible chains of same-relation multinuclear nodes into larger structures.

This operation is explicitly lossy: a series of binary multinuclear attachments can represent either an originally n-ary construction or deliberate nested annotation. The library cannot always distinguish the two after parsing.

Consequently:

- `debinarize()` returns a new tree rather than mutating the original.
- The returned nonbinary tree is intended for serialization and inspection.
- Operations requiring a binary action sequence, such as `spans()` and `parsing_actions()`, are not supported on that nonbinary result.
- `to_rs4_string()` preserves the binary structure by default instead of automatically flattening it.

This is an important fidelity distinction for corpus conversion, training-data round-tripping, and comparisons of predicted structures with original annotations.

### 3.4 RS3/RS4 ingestion and relation inventories

`dipo.rst.data.reader` provides `read_rst_file()` and `read_rst_dir()` for RS3/RS4 annotation files.

The reader performs more than XML deserialization. It also handles corpus irregularities relevant to modeling:

- Unique node ID and root checks.
- Rejection of malformed XML that could otherwise be silently recovered.
- Normalization of EDU whitespace.
- Repair of certain multinuclear structures containing multiple satellites.
- Optional tree binarization.
- Optional fine-to-coarse relation mapping.

The `infer_relation_types()` utility derives the relation inventory from annotated data. `determine_label_index()` then constructs the joint nuclearity–relation label space required by classification-based parsers.

A single relation name may legitimately occur in both mononuclear and multinuclear contexts. Accordingly, Dipo represents relation inventory entries as `(relation, kind)` pairs rather than assuming that every relation has one globally fixed nuclearity class.

An especially useful design detail is that fine-to-coarse relation mapping is applied at the output boundary. Original labels are retained internally where needed to distinguish different attachment structures.

Secondary edges require care. The data model can ingest and retain secondary relationships, but the standard parsing-action representation is based on primary tree structure. The inspected `to_rs4_string()` implementation also does not emit a secondary-edge section. It should not be used as a lossless general-purpose RS4 round-trip for documents whose secondary edges must survive.

Reader source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/reader.py`

## 4. Inference interfaces and integration boundaries

Dipo offers direct Python and CLI interfaces. The natural integration point for most downstream NLP systems is a structured `RstTree`, not the raw textual output of a language model.

### Python API

The following uses the public usage pattern documented by the project:

```
from dipo.rst.parsers.dmrst.modeling_dmrst import DMRSTParserparser = DMRSTParser.from_pretrained(    "larc-iu/dmrst-ettin-400m-gum-12.1.0")tree = parser.predict_from_text(    "The experiment failed. "    "Therefore, the team revised its hypothesis.")for edu in tree.edus:    print(edu.id, edu.text)for span, nuclearity, relation in tree.spans():    print(span, nuclearity, relation)rs4_xml = tree.to_rs4_string()
```

This illustrates the separation between neural prediction and downstream structural operations. It is based on the documented API and was not executed as part of this research.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### Command-line inference

A released DMRST checkpoint can be invoked through the CLI:

```
dipo dmrst predict \
  --hub-id larc-iu/dmrst-ettin-400m-gum-12.1.0 \
  --text "The experiment failed. Therefore, the team revised its hypothesis."
```

For local batches:

```
dipo dmrst predict \
  --hub-id larc-iu/dmrst-ettin-400m-gum-12.1.0 \
  --text-file ./documents \
  --output-dir ./parsed \
  --device cuda
```

The common prediction CLI recognizes pretrained Hub models, checkpoint paths, and resolved training configurations. It accepts raw text for parsers with segmentation support, and annotated RS3/RS4 inputs for gold-EDU parsing.

It writes RS4 files for file or directory input. These interfaces cover the common mechanics of model loading and output generation without requiring a separate custom inference script for every parser.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Raw text and presegmented EDUs are different inference modes. They do not produce directly comparable segmentation metrics. The top-down and shift-reduce biaffine parsers require EDUs; DMRST and `gen` can infer them.

Some of DMRST's raw-text behavior is also heuristic: its prediction helper can introduce EDU boundaries at blank-line paragraph breaks and short heading-like lines. This can be disabled with `break_at_paragraphs=False`.

The released `gen` models instead normalize whitespace and do not use line and paragraph breaks as explicit structural cues.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### Input and output lifecycle

Raw document text

Or an existing annotated EDU sequence

EDU segmentation

DMRST or generative model, unless boundaries are already supplied

Discourse attachment and labeling

Top-down, shift-reduce, generative, or LLM-based parser

`RstTree`

EDUs, spans, hierarchy, nuclearity, rhetorical relations

Downstream representations

RS4 XML, action sequences, S-expressions, structured span records

The architectural opportunity is to reuse Dipo's parsing and tree representation as a specialized discourse-structure component. It does not itself supply a general document-ingestion system, an ontology, a knowledge graph database, or a semantic reasoner.

## 5. Training, model adaptation, and experiment management

Dipo includes training infrastructure for its neural parser families rather than only providing pretrained inference checkpoints.

### 5.1 Configuration and parser extensibility

Training is configured using Jsonnet files and the `tonga-config` library, with typed configuration classes associated with each parser.

Each parser family has its own model, training loop, and prediction module. Shared infrastructure provides common configuration parsing, checkpoint resolution, logging, and model-distribution behavior.

The parser registry uses `ParserSpec` entries to associate parser names with configuration classes, implementation classes, and capabilities such as raw-text support.

Adding another RST parser can therefore reuse the surrounding command infrastructure while supplying its own model and training logic.

There is also a project-level framework registry (`dipo.FRAMEWORKS`) intended to accommodate additional discourse formalisms. As of the inspected release, it registers only `dipo.rst`.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/__init__.py`

### 5.2 Curriculum learning over discourse subtrees

One of the more distinctive training mechanisms is the configurable curriculum.

`Curriculum` is an extensible strategy interface with two provided implementations:

| Strategy                | Behavior                                                                                  |
| ----------------------- | ----------------------------------------------------------------------------------------- |
| `SimpleCurriculum`      | Train on complete documents in one phase                                                  |
| `SubtreeSizeCurriculum` | Progress from shorter discourse subtrees to larger subtrees and eventually full documents |

The subtree curriculum has configurable EDU-count caps, phase durations, and an optional expansion limit to prevent the number of short training examples from becoming disproportionately large.

The intent is to address the difficulty of learning complex document-level structures from a cold start, particularly for generative parsing architectures.

Its implementation also separates validation from warm-up: subtree phases do not use the full-document dev set for model selection; validation is performed during full-document phases.

The generative training implementation can coordinate this curriculum with a warmup–stable–decay learning-rate schedule, concentrating the final learning-rate decay in the full-document training phase.

These are meaningful optimization mechanisms because a document-level parsing objective has a different structural difficulty from ordinary sequence labeling.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/curriculum.py`

### 5.3 Parameter-efficient training and memory management

The library supports several training approaches, with applicability depending on the parser and backbone.

Adapter training. The shared `PeftConfig` supports LoRA hyperparameters such as rank, scaling, dropout, target modules, and DoRA configuration. Full fine-tuning remains available where supported.

Reduced-precision frozen backbones. Encoder-based parsers can load frozen backbone weights in bfloat16 while keeping trainable components at higher precision.

Gradient checkpointing. Encoder checkpointing trades additional computation for reduced activation storage. DMRST also offers separate checkpointing of its recurrent structural decoder.

4-bit adaptation. The released configuration includes bitsandbytes-based NF4 QLoRA options for compatible causal backbones. This is not a universal capability across encoder–decoder and encoder-only parser configurations.

Generative new-token training. When a serialization adds action tokens to a pretrained vocabulary, Dipo can train the new embedding rows through a shadow-parameter mechanism. This avoids copying an entire large embedding matrix merely to update a small number of structural tokens.

Trainable-only checkpoints. Generative models can save only trainable parameters rather than storing another complete copy of a large frozen backbone.

Optimizer and objective choices. The generative training loop supports AdamW or Adafactor, gradient accumulation, label smoothing, structural-action loss weighting, and document loss weighting based on EDU count.

The last mechanism is especially useful for understanding optimization behavior: without explicit reweighting, a training loss may emphasize the many source-copy positions over the fewer but more consequential rhetorical attachment decisions.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/config.py`

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/gen/train_gen.py`

### 5.4 Corpus and encoder preparation

Dipo includes utilities for dealing with the mismatch between annotated discourse corpora and naturally occurring raw text.

Some corpora contain tokenized EDU strings with punctuation artificially separated. A model trained on those strings may see a different text distribution at inference time.

Dipo provides corpus-preparation scripts and a configurable `SacreMosesDetokenizer` to address this.

The project documents raw-text preparation for RST-DT, the Potsdam Commentary Corpus, the Chinese GCDT, and the Persian RST corpus. For unspaced Chinese, the DMRST tokenizer can split multicharacter CJK tokens so that EDU boundaries remain representable at token boundaries.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



The shared encoder infrastructure also accommodates Hugging Face transformer backbones and, for supported architectures, loading only the encoder portion of an encoder–decoder model. This is different from the generative parser, which requires the language-model decoding machinery.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/encoding.py`

### 5.5 Checkpoints, reproducibility, and Hugging Face publishing

Dipo derives a run identifier from the resolved training configuration. Its checkpoint directories normally contain:

- `last.pt` and related metadata for interrupted-run resumption.
- `best_model.pt` for the selected model.
- `config.json` recording the effective configuration.
- `tb/` containing TensorBoard training and validation metrics.
- Final evaluation outputs when the relevant training loop completes.

The CLI includes `dipo runs list` for inspecting available runs. Reusing the same effective training configuration can resume the corresponding run from its saved state. The implementation also distinguishes training-affecting configuration fields from selected evaluation or runtime fields for hashing purposes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Hugging Face integration is more than checkpoint download. The `push` command generates a model card containing architecture and dataset information, serialized configuration, and available evaluation metrics.

It uploads the weights, configuration, and model card together in a single Hub commit, avoiding a partially updated publication in which the weights and configuration refer to different model states.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Hub integration source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/hfhub/hub.py`

## 6. Evaluation: what the metrics actually measure

Dipo provides a relatively substantial evaluation subsystem, covering both segmentation and hierarchical discourse correctness.

The distinction between these measurements is particularly important because a parser can accurately identify EDU boundaries while still assigning incorrect rhetorical structure.

### 6.1 Parseval dimensions

The main parsing metrics are:

| Metric        | What must match                            |
| ------------- | ------------------------------------------ |
| Span F1       | Constituent span boundaries                |
| Nuclearity F1 | Constituent span and nuclearity            |
| Relation F1   | Constituent span and rhetorical relation   |
| Full F1       | Constituent span, nuclearity, and relation |

The stricter metrics expose the difference between finding the right grouping and assigning the right rhetorical meaning to it.

For example, a parser could correctly attach two EDUs but label an evidential relationship as an elaboration, producing a structurally correct but semantically incorrect analysis.

### 6.2 Standard versus original Parseval

Dipo explicitly supports two constituent-counting conventions.

The default `compute_parseval_metrics()` uses a parent-span representation that excludes trivially correct leaf-EDU spans. Its `original_parseval=True` option switches to a sibling-oriented representation that includes leaf spans.

The alternative convention can yield substantially higher scores because leaf spans are automatically correct when the gold and predicted trees share EDU boundaries.

This means similarly named Parseval results from different papers or evaluation pipelines may not be on the same numerical scale.

The published Dipo model cards describe their scores as original Parseval with trivial leaf spans excluded. Because the implementation exposes multiple conventions, the exact evaluation routine and span-counting definitions should be preserved when comparing results externally; the word original alone is not sufficient to reconstruct the scoring setup.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/metrics.py`

### 6.3 End-to-end evaluation with differing EDU boundaries

When predicted EDU segmentation differs from gold segmentation, ordinary EDU-index-based comparison is not sufficient.

Dipo handles this by representing constituents in token coordinates for end-to-end evaluation.

It provides:

- Segmentation precision, recall, and F1 from EDU boundary positions.
- Gold-EDU Parseval, where the EDU sequence is supplied.
- End-to-end Parseval, where segmentation and structural prediction are evaluated together.
- Forced-gold-boundary evaluation for appropriate generative models, allowing controlled comparison of parsing performance.

The corpus aggregation code accumulates counts across documents before computing the overall F1.

An implementation detail worth preserving: its segmentation boundary counting includes the mandatory end-of-document boundary. This convention must be considered when comparing segmentation scores to external scorers that use different boundary definitions.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/seg_metrics.py`

### 6.4 Statistical comparisons between parsers

The evaluation module also includes `paired_permutation_test()` for comparing two systems on the same documents.

It performs paired sign-flip permutations and computes a bootstrap confidence interval for the difference in corpus-level micro-F1.

Unlike simply averaging per-document F1 differences, this recomputes the aggregate metric from the relevant counts, preserving the scoring convention used for corpus-level reporting.

This is a useful built-in capability for determining whether an observed difference between parser configurations is robust to document-level variation, especially on small discourse evaluation sets.

It does not, by itself, control for different corpora, label mappings, random seeds, or segmentation conditions.

## 7. Published checkpoints and multilingual coverage

Dipo's published model collection is one of its most immediately useful assets. The available checkpoints cover multiple parsing architectures, languages, and relation inventories.

The following figures are the project's reported test-set end-to-end Full F1 scores, multiplied by 100, including segmentation from raw text. They are not independent measurements performed for this overview.

| Dataset / language                 | Checkpoint                            | Architecture            | Full F1 |
| ---------------------------------- | ------------------------------------- | ----------------------- | ------- |
| RST-DT / English                   | `dmrst-ettin-400m-rstdt-coarse`       | DMRST, Ettin 400M       | 53.2    |
| RST-DT / English                   | `gen-sr-t5gemma-2-1b-1b-rstdt-coarse` | Generative, T5Gemma 2   | 49.6    |
| RST-DT / English                   | `gen-sr-gemma-4-31b-it-rstdt-coarse`  | Generative, Gemma 4 31B | 54.7    |
| GUM 12.1 / English                 | `dmrst-ettin-400m-gum-12.1.0`         | DMRST, Ettin 400M       | 45.6    |
| GUM 12.1 / English                 | `gen-sr-t5gemma-2-1b-1b-gum-12.1.0`   | Generative, T5Gemma 2   | 39.4    |
| GUM 12.1 / English                 | `gen-sr-gemma-4-31b-it-gum-12.1.0`    | Generative, Gemma 4 31B | 45.8    |
| RST Basque Treebank / Basque       | `dmrst-xlm-roberta-base-ert`          | DMRST, XLM-R            | 27.6    |
| Potsdam Commentary Corpus / German | `dmrst-xlm-roberta-base-pcc-2.2`      | DMRST, XLM-R            | 18.6    |
| Persian RST Corpus / Persian       | `dmrst-xlm-roberta-base-prstc`        | DMRST, XLM-R            | 32.2    |
| GCDT / Chinese                     | `dmrst-xlm-roberta-base-gcdt`         | DMRST, XLM-R            | 29.4    |

All checkpoint IDs above use the `larc-iu/` Hugging Face namespace. The official catalog provides the full model URLs and evaluation context.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+3



Model catalog:

`https://huggingface.co/models?other=dipo`

Several distinctions are important when interpreting these numbers.

Corpus-specific label spaces. RST-DT checkpoints use an 18-relation coarse inventory, whereas the published GUM models use 32 more fine-grained relations. The scores are not measures of accuracy over the same classification problem.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face+1



Genre variation. RST-DT is based on Wall Street Journal articles, while GUM includes a much wider range of written and spoken genres. Performance on one is not a direct estimate of performance on the other.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face+1



Model size does not translate linearly to parsing quality. On the published English tests, the 400M-parameter Ettin-based DMRST checkpoints remain competitive with substantially larger generative backbones. This does not establish a speed or resource benchmark, but it illustrates why specialized structural predictors remain important alternatives.

Multilingual support does not mean one universal multilingual parser. The published XLM-R checkpoints are associated with individual language-specific datasets and label inventories. Their reported performance cannot be transferred to arbitrary languages without evidence.

The published checkpoints were generally selected against their development splits, and the model cards caution that small test sets may show several points of variation across training runs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face



## 8. Dependencies, deployment requirements, and operational limits

### Packaging and installation

The released package can be installed with:

```
pip install dipo==0.2.1
```

The project declares Python 3.10 or newer and uses the PyTorch and Hugging Face ecosystem, alongside `tonga-config`, `lxml`, `rich`, `sentencepiece`, `sacremoses`, `peft`, and TensorBoard.

The package metadata lists an alpha-stage development classification. The Python-version requirement should not be interpreted as a guarantee that every possible newer Python, PyTorch, CUDA, or Transformers combination has been tested.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



Configuration examples are not bundled with the PyPI distribution. They are maintained separately in the source repository:

`https://github.com/larc-iu/dipo/tree/v0.2.1/configs`

For dependency management, two distinctions are worth noting:

- The released 0.2.1 package exposes a `dev` extra but not a `qlora` extra. The development branch adds the latter. Although compatible released code supports bitsandbytes quantization settings, the runtime dependency must be made available separately when using those paths.
- The ICL provider code imports LiteLLM when needed, but `litellm` is not listed among the base dependencies in the inspected 0.2.1 package manifest. It therefore requires additional dependency provisioning for those workflows.

The repository also contains a minor version-metadata discrepancy: `pyproject.toml` declares version 0.2.1, while `dipo.__version__` remains `0.2.0`. For identifying the installed distribution, Python's `importlib.metadata.version("dipo")` is a more reliable source than that module constant.

### GPU requirements and model loading

The compute requirements vary substantially by model family.

DMRST's smaller encoder checkpoints have a very different memory profile from the largest causal generative models. The official project documentation reports that its Gemma 4 31B checkpoints require approximately 70 GB of GPU memory, despite their task-specific adapters occupying only about 0.5 GB. The T5Gemma checkpoints store approximately 4.4 GB of full model weights. These are upstream deployment descriptions, not independently measured footprints.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



The released generative checkpoints also depend on access to their original gated Google backbones. Accepting the model terms and authenticating with Hugging Face may be necessary before loading them.

For the published `gen` models, documents exceeding the stated 16,384-token context window are rejected rather than silently truncated.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face



### Corpus and model licensing

The Dipo source code is MIT-licensed, but the same conclusion does not automatically extend to its model weights or training datasets.

For example, the T5Gemma-based checkpoints are subject to the underlying Gemma model terms, and RST-DT is distributed through the Linguistic Data Consortium under its own agreement. Checkpoint-specific model cards describe these restrictions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face



Relevant primary sources:

`https://pypi.org/project/dipo/`

`https://github.com/larc-iu/dipo/blob/v0.2.1/pyproject.toml`

`https://huggingface.co/larc-iu/gen-sr-t5gemma-2-1b-1b-rstdt-coarse`

## 9. Architectural implications and capability boundaries

Dipo provides capabilities that can support several broader kinds of text-analysis systems, but its output should be interpreted according to RST semantics.

### Hierarchical evidence and explanation structures

RST trees can expose the relationship between an assertion and the discourse spans that explain, justify, contrast with, or qualify it.

For applications that need to distinguish central statements from supporting material, this supplies a more expressive structure than a flat collection of sentences or embeddings.

A possible use is to retain document-level rhetorical context while extracting facts, claims, or supporting passages. The RST structure does not establish whether a claim is true, but can help describe how the author presents it.

### Structure-aware retrieval and document navigation

The hierarchy may also be useful for generating retrieval units that preserve coherent discourse spans rather than imposing uniform token windows.

For example, passages under the same explanation or elaboration structure might be considered together when constructing a retrieval candidate.

This is an architectural possibility, not a built-in vector-indexing or retrieval function provided by Dipo. Any retrieval quality improvement would need to be evaluated against the segmentation and attachment errors introduced by the chosen parser.

### Document comparison and rhetorical analysis

Two documents discussing similar facts may differ considerably in how their content is organized. RST provides features that can help describe those differences:

- Relative importance of discourse units.
- Depth and arrangement of rhetorical attachments.
- Distribution of relation types.
- Prevalence of explanatory, evidential, contrastive, and other constructions.

Such features can supplement lexical, semantic, and syntactic analyses. Dipo supplies the underlying structure, while aggregation, statistical modeling, and downstream classification remain the caller's responsibilities.

### Important non-goals

Dipo should not be mistaken for a complete semantic parsing or information-extraction platform.

| Adjacent capability                      | Boundary                                                                                              |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Named-entity recognition                 | RST EDUs and rhetorical relations do not identify entity mentions                                     |
| Coreference resolution                   | RST structure does not directly determine which mentions refer to the same entity                     |
| Semantic role labeling                   | Rhetorical relations differ from predicate–argument roles                                             |
| Dependency parsing                       | RST parses discourse structure, not grammatical dependency arcs                                       |
| Temporal and causal knowledge extraction | A rhetorical cause or temporal relation does not automatically establish a validated event-level fact |
| Ontology induction                       | RST structure may contribute evidence, but does not produce a formal ontology                         |
| Knowledge graph construction             | Tree outputs require additional normalization and mapping before becoming a general knowledge graph   |
| PDTB/SDRT analysis                       | These formalisms are not interchangeable with the implemented RST parser family                       |

The most consequential composition is therefore often discourse structure plus complementary linguistic analysis, rather than treating RST parsing as a replacement for other NLP tasks.

In particular, an RST `evidence` relation describes how a passage functions rhetorically relative to another passage. It should not be equated with independently verified evidence, formal entailment, or factual provenance.

## 10. Source map and further investigation

The repository does not have a large, separately maintained API reference. The README, implementation modules, parser-specific READMEs, and Hugging Face model cards are the principal authoritative sources.

| Area                                         | Primary source                                                                         |
| -------------------------------------------- | -------------------------------------------------------------------------------------- |
| Project orientation, installation, inference | `https://github.com/larc-iu/dipo`                                                      |
| Published package and release metadata       | `https://pypi.org/project/dipo/`                                                       |
| Parser registry and framework extension      | `https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/__init__.py`             |
| RST data model and transformations           | `https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/tree.py`                    |
| Corpus reading and relation inventories      | `https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/reader.py`                  |
| DMRST implementation                         | `https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/dmrst/modeling_dmrst.py` |
| Generative parser architecture               | `https://github.com/larc-iu/dipo/tree/v0.2.1/dipo/rst/parsers/gen`                     |
| ICL provider and constrained generation      | `https://github.com/larc-iu/dipo/tree/v0.2.1/dipo/rst/parsers/icl`                     |
| Evaluation and statistical testing           | `https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/metrics.py`                 |
| Training infrastructure                      | `https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/common/training.py`                  |
| Released checkpoint catalog                  | `https://huggingface.co/models?other=dipo`                                             |
| Post-release development changes             | `https://github.com/larc-iu/dipo/compare/v0.2.1...master`                              |

### Overall characterization

Dipo is a specialized but technically substantial discourse-processing library. Its strongest capabilities are the combination of multiple neural RST parsing architectures, end-to-end EDU segmentation, reusable discourse tree representations, structure-constrained generative decoding, corpus-aware training, and evaluation infrastructure.

Three characteristics are especially consequential:

1. Architectural diversity: DMRST, biaffine, generative, and ICL approaches offer genuinely different tradeoffs in compute, supervision, segmentation, and structural prediction.
2. Representation interoperability: RST trees, span actions, transition sequences, and S-expressions provide a consistent semantic foundation across those architectures.
3. Evaluation and research mechanisms: Gold-EDU versus end-to-end scoring, corpus-aware relation inventories, subtree curricula, parameter-efficient training, and paired statistical testing make the project more capable than a basic pretrained-model wrapper.

The principal limitations are its current concentration on RST, corpus-dependent relation vocabularies, the potential information loss from binarization or serialization, and the gap between structurally valid predictions and semantically accurate discourse analyses.

For advanced text-processing systems, Dipo's distinctive value is recovering document-level rhetorical organization as structured data—a linguistic layer that ordinary sentence embeddings, entity extractors, and syntactic parsers do not directly provide.

# Dipo — Technical Capability Addendum

Research date: November 8, 2026 | Reference version: Dipo 0.2.1 | Supplement to the original library overview

This addendum extends the original Dipo reference with advanced capabilities, implementation mechanisms, and semantic distinctions identified during the subsequent source-code gap analysis. It concentrates on functionality that was omitted or insufficiently explained, together with corrections needed for technical accuracy.

Unless explicitly marked otherwise, the behavior described is present in the published 0.2.1 release (October 12, 2026). The package is classified as alpha-stage software. Features introduced only on the development branch are identified separately.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



Primary repository: `https://github.com/larc-iu/dipo`

## 1. Grammar-constrained discourse parsing: beyond syntax validation

### 1.1 State-indexed grammars that guarantee tree size

Dipo's `icl` parser supports a form of constrained language-model generation that goes considerably beyond requiring syntactically valid shift-reduce actions.

The `sr_parse_grammar()` function constructs a document-specific GBNF grammar from the number of elementary discourse units (EDUs) and the permitted nuclearity–relation labels.

For a binary RST tree containing \\(n\\) EDUs, a valid bottom-up derivation requires exactly:

\\[ N\_{\mathrm{SHIFT}}=n,\qquad N\_{\mathrm{REDUCE}}=n-1 \\]

Dipo represents the state of this derivation using two counters:

- \\(s\\), the number of EDUs already shifted onto the stack.
- \\(d\\), the current stack depth.

The legal transitions are:

\\[ (s,d)\xrightarrow{\mathrm{SHIFT}}(s+1,d+1),\quad s\<n \\]

\\[ (s,d)\xrightarrow{\mathrm{REDUCE}}(s,d-1),\quad d\geq2 \\]

Only \\((n,1)\\) is an accepting state.

The implementation generates a right-linear grammar whose productions correspond to these states. A simplified conceptual production is:

```
state(s,d) ::=
    SHIFT state(s+1,d+1)
  | REDUCE state(s,d-1)
```

Actual productions enumerate legal choices and constrain reductions to the permitted nuclearity–relation vocabulary.

This has several consequential properties.

Exact structural cardinality. A grammar-conforming completion contains exactly the specified EDU count, the corresponding number of reductions, and a valid order of stack operations.

Unambiguous parsing. The emitted prefix uniquely determines the state \\((s,d)\\). This avoids the combinatorial ambiguity that can arise from a grammar that recursively enumerates every possible binary-tree split.

Grammar-driven validity rather than postprocessing. The model selects among legal continuations during generation; the implementation does not depend on repairing arbitrary invalid action sequences afterward.

The implementation uses an exact-count threshold of 512 EDUs by default. Its state-indexed grammar has \\(O(n^2)\\) possible states, so grammar construction and compilation become increasingly expensive for large documents.

Above that threshold, Dipo switches to a compact grammar that still enforces valid shift-reduce structure but no longer fixes the number of EDUs. That fallback weakens the structural guarantee, even if the output remains syntactically valid.

These guarantees also depend on a compatible inference backend correctly applying the supplied grammar. They are not guarantees about the semantic correctness of the resulting rhetorical relationships.

Source: `https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/icl/serialize.py`

### 1.2 Grammar-constrained segmentation as boundary selection

The ICL subsystem also contains `segmentation_grammar()`, which converts raw-text segmentation into a constrained boundary-placement problem.

The grammar enumerates the whitespace-tokenized source sequence and permits alternatives at each token boundary: either continue the current EDU or insert an EDU delimiter.

For an input token sequence \\(w_1,\ldots,w_m\\), the model effectively chooses among \\(m-1\\) possible intertoken boundary positions:

\\[ b_i\in\\{0,1\\},\qquad 1\leq i\<m \\]

The source-token sequence itself is fixed.

This means the model cannot freely omit, reorder, or replace whitespace tokens while satisfying the grammar. Its generation task is to determine where the EDUs begin and end.

The benefit is not merely fewer output-format errors. It removes unrestricted source-text generation from the segmentation problem, allowing the model to focus on the linguistic boundary decisions.

There are two important qualifications. First, the input is normalized using whitespace tokenization, so preserving the ordered token sequence does not imply preserving the original character-level whitespace. Second, the model can still choose linguistically incorrect boundaries; grammar constraints guarantee permitted output form, not segmentation accuracy.

### 1.3 EDU-grounded parsing with `echo_edu_text`

The ICL configuration also exposes:

```
echo_edu_text: bool = False
```

When enabled, the parse-stage serialization includes the text of the EDU being consumed by each shift operation instead of representing it only with an otherwise indistinguishable `<shift>` marker.

This provides direct textual grounding for successive parsing decisions.

For exact-count GBNF parsing, the model does not receive unlimited freedom to generate those strings. Because the grammar state identifies which EDU is next, Dipo can force the corresponding EDU text as a literal part of the next legal shift action.

This connects three capabilities: document-specific grammar construction, EDU identity tracking, and source-text grounding.

The result is a structural generation interface in which the model can reason over the text of each unit while the grammar restricts which unit may be consumed next.

The tradeoffs are larger generated outputs and grammars. The implementation's own comments note that echoing EDU content can roughly double parse-stage output length. When exact-count constraints are disabled by the large-document fallback, forced EDU-text echoing is also unavailable.

The corresponding implementation is in `SrSerialization`, `sr_parse_grammar()`, and `IclConfig`.

Sources:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/icl/configuration_icl.py`

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/icl/serialize.py`

### 1.4 Reasoning-aware constrained decoding and inference-server boundaries

Dipo's grammar-constrained ICL implementation has a specialized pathway for reasoning-enabled language models.

An eager grammar constrains output from the first generated token. That is unsuitable when a model is expected to produce an unconstrained reasoning section before generating a structurally constrained answer.

Dipo can instead configure llama.cpp's lazy grammar functionality to activate after a designated marker, normally `</think>`.

The interaction is significant because some serving paths can silently change the intended semantics of the request. The implementation documents cases where llama.cpp's OpenAI-compatible endpoint failed to preserve lazy grammar settings correctly. Consequently, the lazy grammar pathway uses the server's native `/apply-template` and `/completion` endpoints.

The provider can also impose a reasoning-token budget. When the budget is exhausted before the model terminates its reasoning naturally, the client performs a second completion with the reasoning section explicitly closed and an eager answer grammar applied.

This preserves a distinction between:

- A model that completed its reasoning naturally and generated a constrained answer.
- A model whose reasoning was forcibly terminated before producing a constrained answer.

Evaluation records these events separately, including forced-call counts and the affected documents.

The implementation also supplies configurable retries, request timeouts, explicit temperature, streaming controls, and provider-specific request parameters.

For Anthropic, it implements a reusable prompt prefix with an explicit cache breakpoint. For compatible self-hosted endpoints, reuse of a shared prefix can instead benefit from server-side KV caching. Neither optimization guarantees a cache hit on every request; the effective benefit depends on the serving backend and request pattern.

Backend limitations: the released grammar implementation supports `gbnf` through the llama.cpp pathway. `guidance` and `xgrammar` appear in configuration validation but are not implemented as usable alternatives. The Anthropic provider does not expose the grammar-constrained pathway.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/icl/provider.py`

## 2. Generative parsing: scoring, validity, and execution efficiency

### 2.1 Correction: `use_copy=False` still constrains source content

The original overview described `use_copy=False` as permitting full-vocabulary source generation. This requires correction.

In Dipo 0.2.1, the generative S-expression decoder constrains content to the source-token cursor regardless of the `use_copy` setting.

The setting determines how source tokens are represented and scored, not whether the model may arbitrarily rewrite them.

| Configuration                            | Representation and scoring                                                    | Content constraint                                   |
| ---------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------- |
| `use_copy=True`, `label_style="token"`   | Source positions use a copy action; structural tokens use a small output head | Next source token is fixed by cursor                 |
| `use_copy=True`, `label_style="words"`   | Source copying remains structural; labels use the pretrained vocabulary head  | Next source token is fixed by cursor                 |
| `use_copy=False`, `serialization="sexp"` | Source tokens are scored directly through the pretrained language-model head  | Only the source token at the current cursor is legal |

The last arrangement resembles full-vocabulary text-to-text training, but constrained inference still forbids arbitrary substitution of source tokens.

This distinction matters when interpreting the performance implications of copy mechanisms. The benefits of the compact action head arise partly from reducing the scoring vocabulary and changing the learning objective, not merely from preventing free-text hallucinations.

The released configuration also rejects `use_copy=False` with LoRA. That combination requires training the output machinery used to emit source subwords, which the current parameter-efficient implementation does not support.

Sources:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/gen/configuration_gen.py`

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/sexp_constraints.py`

### 2.2 Probability preservation under legality constraints

Dipo's generative beam search uses a consequential ordering of operations: it computes log-probabilities over the original scoring vocabulary before masking illegal continuations.

For logits \\(z\\) and legal action set \\(A(s)\\) at parser state \\(s\\):

\\[ \ell(a)= \begin{cases} \log\operatorname{softmax}(z)\_a,&a\in A(s)\\\ -\infty,&a\notin A(s) \end{cases} \\]

It does not first mask the logits and renormalize the remaining distribution.

This preserves the model's original probability assigned to a legal action.

The distinction becomes important when the legal set is very small. Renormalization can make a low-probability legal continuation appear almost certain simply because all competing actions have been eliminated.

Across a complete generated tree, that behavior could favor trajectories that encounter particularly restrictive parser states rather than trajectories the underlying model finds intrinsically probable.

Dipo's implementation avoids this distortion by masking after full-vocabulary normalization.

Its beam-selection logic additionally uses length normalization:

\\[ S(y)=\frac{\log P(y)}{|y|^\alpha}, \qquad \alpha=0.6 \\]

Completed hypotheses take precedence over unfinished hypotheses. This avoids preferring a truncated action sequence merely because it accumulated fewer negative log-probability terms.

The beam implementation clones parser state for each candidate continuation, maintains separate legality constraints, and reorders transformer KV caches as beams diverge. Cache reordering is skipped when the required operation is effectively a no-op.

These features interact: the beam search must maintain consistency among token scores, automaton states, candidate histories, and cached model state.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/seqgen.py`

### 2.3 Explicit decoding invariants and exceptional outcomes

The `gen` decoder distinguishes invalid internal state transitions from unsuccessful but structurally legal model predictions.

`DecodeInvariantError` is raised when the legality mask and state machine disagree—for example, when the mask permits an action that the transition function subsequently rejects, or when a live state has no legal continuation.

`OverLengthError` is raised when decoding cannot complete within its allowed generation budget. The effective budget incorporates both the configured maximum output length and any applicable model positional constraint.

This prevents an unfinished tree from being silently accepted as a complete prediction.

However, not every pathological model output is an invariant failure. For example, the S-expression reconstruction code catches certain recursion-depth failures caused by extremely deep valid structures and degrades the result to a single-EDU fallback tree, marked internally as a failed reconstruction.

Therefore, the distinction between valid syntax, completed decoding, usable rhetorical structure, and successful semantic prediction remains important.

The configuration's `min_edu_length` parameter provides an additional decoding constraint by requiring a minimum number of source tokens before an EDU boundary becomes legal, except at the end of the source. Increasing it can suppress very short segments, but also makes legitimately short EDUs impossible to predict.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/gen/decode.py`

### 2.4 Batched decoding and gold-EDU forcing

Dipo provides two distinct forms of parallelism in its generative inference implementation.

Beam search batches multiple hypotheses for one document. Batched greedy decoding instead processes multiple independent documents in the same model forward pass.

The latter maintains separate decoding states, source cursors, legality masks, completion flags, and output budgets for each document. A row that emits EOS retires while the remaining documents continue.

The implementation also exposes `predict_batch_with_gold_edus()`, enabling the same batching machinery to evaluate structure and labeling while forcing known EDU boundaries.

This matters because gold-boundary evaluation can otherwise require a second full autoregressive decoding pass for every document. Batched evaluation provides a way to amortize that work across multiple documents.

Batched greedy decoding is opt-in through `batched_decode`. Its tests check equivalence with single-document decoding, including differently sized inputs. The configuration nevertheless cautions that different GPU matrix-multiplication shapes can change floating-point reduction order and potentially flip nearly tied argmax decisions. Exact bitwise reproducibility across arbitrary hardware and serving configurations is not guaranteed.

Beam search remains document-scoped rather than batching separate documents and beams together.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/gen/modeling_gen.py`

### 2.5 Output-head initialization and memory-bounded optimization

Two additional mechanisms are useful for understanding generative training at larger model scales.

Output-head initialization. `warm_init_head()` initializes rows of a compact structural output head from corresponding rows of the pretrained language model's output-projection matrix where dimensions permit. This preserves some pretrained token-scoring information rather than initializing every output direction independently.

Newly introduced structural tokens may still have randomly initialized representations. If projection dimensions are incompatible, the implementation falls back to random initialization.

Memory-bounded cross-entropy. `chunked_cross_entropy()` implements a custom autograd operation that evaluates full-vocabulary cross-entropy in chunks. This is relevant when labels are represented as natural language tokens rather than a compact structural vocabulary.

It reduces the memory required by the loss computation without changing the intended full-vocabulary classification problem. It does not eliminate the underlying language model's memory requirements.

These mechanisms complement the previously described new-embedding-row optimization. Together, they allow generative discourse parsing to reuse pretrained model representations while limiting some of the additional memory costs introduced by structural tokens and large-vocabulary scoring.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/seqgen.py`

## 3. EDU segmentation, token alignment, and source fidelity

### 3.1 Configurable segmentation objectives and structural constraints

DMRST's segmentation subsystem supports three token-labeling schemes through `dipo.rst.parsers.common.segmentation.Segmenter`.

| Scheme | Interpretation   | Structural characteristics                     |
| ------ | ---------------- | ---------------------------------------------- |
| `BIE`  | Begin–Inside–End | Explicit EDU boundaries and interior positions |
| `BO`   | Begin–Other      | Boundaries represented by EDU starts           |
| `EO`   | End–Other        | Boundaries represented by EDU ends             |

The `BIE` scheme treats a single-token EDU as an `E` label, allowing it to represent degenerate one-token segments without an additional label.

Each scheme can be trained with either a linear-chain conditional random field (`loss="crf"`) or independent token classification (`loss="ce"`).

The distinction is not limited to the training loss.

With CRF training, the segmenter learns transition, start, and end scores. Structural validity masks restrict which transitions can receive probability mass, and decoding uses Viterbi search over the resulting sequence model.

With cross-entropy training, predictions are independently scored, but inference still uses Viterbi decoding with the scheme's fixed structural constraints. There are no learned transition scores in this path.

The `pos_weight` parameter upweights rare boundary labels in the CE objective. It is not used for CRF training.

This allows alternative assumptions about boundary dependence to be investigated while retaining the same surrounding DMRST architecture.

Source: `https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/segmentation.py`

### 3.2 Normalized model input versus recovered document text

Dipo distinguishes the representation passed to a tokenizer from the text that should be returned to a downstream consumer.

The shared `normalize_whitespace()` utility produces:

\\[ (\text{normalized text},\ \text{character mapping}) \\]

The mapping associates each character in the normalized representation with a position in the original input.

This permits whitespace normalization without discarding the ability to recover text spans from the original document.

For instance, a model may receive a document with repeated spaces and line breaks collapsed, while the prediction code uses the character mapping to locate EDU boundaries in the original string.

DMRST uses this mechanism, together with tokenizer offset mappings, when reconstructing its predicted EDUs.

The important distinction is between recovering original source substrings and preserving original formatting exactly. The implementation collapses whitespace in recovered EDU strings, so it should not be treated as a byte-preserving document round-trip.

The underlying mechanism nevertheless avoids another significant problem: decoding token IDs can be lossy.

SentencePiece and other tokenizers may alter punctuation spacing or normalize characters. In particular, the repository documents cases where decoding XLM-R tokens fails to reproduce Persian zero-width non-joiner characters.

Recovering text from source coordinates rather than token-ID decoding avoids those tokenizer-specific transformations.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/whitespace.py`

### 3.3 Whole-document tokenization and EDU-to-token tiling

A related capability concerns how gold EDUs are aligned to transformer subwords.

A naive approach would tokenize each EDU independently and concatenate the results. This is not necessarily equivalent to tokenizing the original document continuously.

For example, tokenizers sensitive to leading whitespace may produce different subwords at the beginning of an independently tokenized EDU than they produce at the same location in the full document.

If a segmentation model trains on independently tokenized EDUs but predicts on continuously tokenized text, it may learn boundary cues that disappear during inference.

Dipo's `tokenize_document()` avoids this mismatch by tokenizing the reconstructed document as one continuous string and then mapping EDU boundaries into that token sequence.

The generative implementation uses a related utility, `align_edus_to_tokens()`, which assigns source subwords to gold EDUs in a monotonic pass.

Its invariant is that the EDU token ranges collectively cover the source-token sequence without gaps or overlaps:

\\[ \bigcup\_{i=1}^{n}[s_i,e_i)=[0,T) \\]

with the ranges ordered and adjacent.

This is important because the generative copy mechanism consumes source tokens using a cursor. If training-time EDU alignment and inference-time cursor advancement operate over different tokenizations, the predicted structure can drift relative to the source document.

Dipo's alignment approach provides a consistent token axis for those operations, although token boundaries can still be an approximation of character-level EDU boundaries.

In particular, a token that straddles a boundary cannot always be assigned perfectly to two adjacent EDUs. The implementation contains explicit handling and validation for these cases.

### 3.4 CJK boundaries and language-specific tokenization constraints

The optional `split_cjk_tokens` behavior addresses cases where a multilingual tokenizer emits a subword spanning multiple CJK characters.

An EDU boundary inside such a subword would be unrepresentable as a token boundary.

Dipo can attempt to split the subword into character-level vocabulary entries while maintaining corresponding source offsets. It preserves the original token when the required character-level representation is not available.

The operation is thus conditional on tokenizer vocabulary support; it is not a universal guarantee that every character can be represented independently.

This is a noteworthy example of an algorithmic constraint arising from the interaction between linguistic annotation and model tokenization.

Sources:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/encoding.py`

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/seqgen.py`

### 3.5 Dual parsing from a shared DMRST encoder pass

`DMRSTParser.predict_both()` exposes a useful evaluation-oriented API that was absent from the original overview.

Given a gold `RstTree`, it computes a contextual encoding and produces both a parse over the supplied EDUs and a parse over model-predicted EDU boundaries.

Its return structure includes:

```
{    "gold_pred": RstTree,    "gold_edu_mapping": [...],    "gold_edu_ends": [...],    "e2e_pred": RstTree | None,    "pred_edu_mapping": [...],     "pred_edu_ends": [...],}
```

The two structural predictions reuse the same encoder computation, although their downstream discourse-decoding operations differ.

This reduces redundant encoder work when computing both evaluation conditions and exposes the alignment metadata required to compare them.

If segmentation is disabled, the end-to-end fields are `None`, rather than containing artificial predictions.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/dmrst/modeling_dmrst.py`

### 3.6 Encoder-family adaptation and long-document representation

Dipo's shared encoder-loading infrastructure supports ordinary encoder-only Hugging Face models and a selected set of encoder–decoder models used in encoder-only mode.

For supported architectures such as T5Gemma, it can instantiate the encoder component without allocating the decoder.

Its sliding-window encoding also adapts to tokenizer-specific sequence boundaries. BERT-like models use CLS/SEP wrappers where available; other supported tokenizers may use BOS/EOS or no wrappers.

Overlapping windows are combined into a single sequence of token embeddings. When positions occur in multiple windows, the implementation retains embeddings from the earlier window.

This is an important semantic qualification: sliding-window processing permits longer documents to be encoded, but it does not provide the same token-level contextualization as a hypothetical full-document attention pass.

The encoder-based prediction CLI additionally exposes `--compile-encoder`, allowing PyTorch compilation on supported CUDA paths. The initial compilation cost is relevant, so the potential benefit is generally greater for repeated inference than for isolated short predictions.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/encoding.py`

## 4. RST representation semantics and information-loss boundaries

### 4.1 `RstTree` equality is structural equality

Dipo's `RstTree.__eq__()` implementation compares the sets of labeled discourse spans returned by `spans()`.

Consequently, equality does not imply identical complete tree objects.

Two `RstTree` instances can compare equal despite differences in their EDU text, node identifiers, auxiliary metadata, or secondary edges, provided their computed span structures agree.

This distinction matters when using tree equality in testing, deduplication, caching, or corpus validation.

In particular, testing:

```
tree_a == tree_b
```

does not establish that the underlying documents are identical or that serialization would preserve every annotation.

Likewise, `spans_with_ranges()` returns ranges in EDU-index coordinates, not character offsets in the original source.

Applications requiring character-level provenance must establish and maintain that mapping separately.

### 4.2 Primary RST structure versus complete annotation preservation

Dipo's node and edge types permit secondary relations, but the principal parsing algorithms operate on primary tree structure.

The `to_rs4_string()` implementation serializes the principal RST nodes, attachments, and relation inventory. It does not serialize the stored secondary-edge collection.

The tree also contains optional `prefix` metadata describing the string preceding each EDU. These prefixes are relevant when reconstructing documents containing glued segments or other nonstandard inter-EDU spacing.

The inspected RS4 serializer does not emit that metadata either.

Therefore, it is useful to distinguish several levels of information preservation:

| Property                               | Behavior                                                          |
| -------------------------------------- | ----------------------------------------------------------------- |
| Primary discourse structure            | Represented and exported                                          |
| EDU surface content                    | Exported, subject to normalization and reconstruction behavior    |
| Node identifiers                       | Represented, but reconstruction from actions may generate new IDs |
| Secondary edges                        | Stored in memory but not emitted by `to_rs4_string()`             |
| Original inter-EDU whitespace          | Not fully preserved in RS4 export                                 |
| Original n-ary attachment distinctions | May be lost through binarization/debinarization                   |

This means Dipo's transformations are suitable for discourse parsing and structural interchange, but they do not form a general lossless annotation-archive abstraction.

### 4.3 Subtree extraction and structure-preserving examples

`RstTree.subtrees_up_to()` provides direct extraction of discourse subtrees bounded by their number of EDUs.

Rather than cutting arbitrary text windows, the operation selects existing rhetorical constituents and reconstructs them as independent trees containing valid structure and labels.

This is the foundation of `SubtreeSizeCurriculum`, but the operation is independently useful for representing bounded discourse constructions.

Possible applications include structure-preserving sampling, local rhetorical analysis, and constructing smaller examples from annotated documents.

The important limitation is that a subtree is not necessarily semantically self-contained. An EDU may depend on antecedents, entities, or broader rhetorical context outside its extracted constituent.

Sources:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/tree.py`

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/curriculum.py`

## 5. Cross-parser evaluation, alignment, and diagnostic analysis

### 5.1 Different parsers operate on different evaluation coordinates

Dipo's evaluation infrastructure does not use one universal definition of a token position.

The relevant coordinate systems include:

| Evaluation path                                     | Coordinate system                       |
| --------------------------------------------------- | --------------------------------------- |
| Neural encoder and generative end-to-end evaluation | Model subword positions                 |
| ICL end-to-end evaluation                           | Whitespace-token positions              |
| Official DISRPT segmentation evaluation             | Corpus-defined token positions          |
| `compare_runs.py` end-to-end comparison             | Whitespace-stripped character positions |
| Gold-EDU structural Parseval                        | EDU-indexed constituents                |

These coordinates are not automatically interchangeable.

For example, one whitespace token might correspond to several transformer subwords, and different tokenizers may split the same string differently.

This means that an identical EDU segmentation can receive different boundary-count representations depending on the evaluation path.

The original overview's description of end-to-end token-range Parseval therefore needs this additional qualification: the metric family is shared, but its token axis depends on the inference and evaluation implementation.

### 5.2 Monotonic alignment of unconstrained ICL output

The ICL evaluation module contains `_project_onto_gold()`, which addresses an additional problem.

Unlike copy-constrained generative models, an unconstrained ICL response may reproduce the source with omissions, insertions, or wording changes.

Its predicted EDU boundaries therefore cannot always be mapped directly onto the gold document by cumulative token counts.

Dipo first checks whether the predicted whitespace-token sequence exactly matches the gold sequence.

If not, it uses `difflib.SequenceMatcher` to derive token correspondences and constructs a monotonic projection of predicted EDU ranges into the gold coordinate system.

Unmatched EDUs may collapse to zero-width spans in the projection.

This allows evaluation to proceed without treating source-text drift as if it were an exact alignment. It does not repair the original prediction or guarantee the correctness of the projection.

The mechanism is especially relevant when comparing unconstrained language-model approaches against neural parsers that reproduce source content deterministically.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/icl/eval_metrics.py`

### 5.3 Official DISRPT segmentation compatibility

The repository includes a separate evaluation pathway using the official DISRPT shared-task segmentation scorer.

`scripts/disrpt_seg_rescore.py` converts predicted RST segmentations into the required token-level representation and invokes a vendored copy of the official scoring implementation.

This matters because Dipo's native segmentation F1 and DISRPT's BeginSeg-based scoring conventions are not automatically numerically equivalent.

The rescorer includes checks intended to ensure that gold-token sequences, document identities, and segment-boundary counts match the expected inputs.

It also has corpus-specific caveats. In particular, the Dipo repository documents differences between its GUM 12.1 RST data and the earlier eRST-based GUM variant used by DISRPT 2025. The two should not be assumed to provide identical gold annotations.

The ability to reproduce an external benchmark's scoring convention is valuable, but it is distinct from directly supporting every task or discourse representation used in that benchmark.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/scripts/disrpt_seg_rescore.py`

### 5.4 Error-cascade analysis

`scripts/cascade_probe.py` provides a specialized diagnostic analysis for hierarchical parsing errors.

For each gold constituent, it examines whether the constituent and its immediate children appear in the predicted tree.

This distinguishes two broad mechanisms:

Local attachment failure: both gold children are correctly represented, but their expected parent relationship is missing.

Propagated failure: at least one required child constituent is already missing, so the parent cannot be correctly reconstructed from the predicted structure.

The script groups results by constituent width and computes quantities including:

\\[ P(\text{both gold children present}) \\]

and

\\[ P(\text{parent present}\mid \text{both gold children present}) \\]

It also reports conditional nuclearity and relation accuracy on matched spans.

These measurements help distinguish poor high-level attachment decisions from errors cascading upward from smaller constituents.

That distinction is particularly useful in recursive parsing systems: a single incorrect low-level boundary or attachment can cause multiple incorrect ancestors, inflating aggregate error counts.

This is a diagnostic decomposition rather than a causal proof. The presence of both gold children does not establish that the model's internal decision process explicitly considered the correct parent.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/scripts/cascade_probe.py`

### 5.5 Paired comparisons and failed-document accounting

The standalone `compare_runs.py` utility applies Dipo's paired permutation and bootstrap machinery to predictions from two model runs.

It supports gold-EDU comparisons and end-to-end comparisons using whitespace-stripped character coordinates.

The latter can be stricter than the training-time token-coordinate evaluation, so its absolute scores should not be assumed to reproduce the training logs exactly.

Its principal purpose is to estimate differences between models over matched documents.

Dipo's ICL evaluation also explicitly accounts for failed predictions. A document whose model response cannot be reconstructed into a tree remains in the evaluation denominator and contributes no correct predicted constituents.

The output distinguishes successful predictions from failures and records per-document execution information.

Additional diagnostics include elapsed time, predicted EDU count, reasoning-budget forcing, and available generation-token counts.

The evaluation CLI can process documents concurrently through a thread pool, while its aggregation results are ordered deterministically after the workers finish.

These mechanisms make model failure rates visible as part of evaluation, rather than allowing selective exclusion of difficult examples to improve reported accuracy.

Sources:

`https://github.com/larc-iu/dipo/blob/v0.2.1/scripts/compare_runs.py`

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/icl/eval_icl.py`

### 5.6 Parseval naming and benchmark comparability

A further qualification concerns the terminology used for published parsing metrics.

Dipo's `compute_parseval_metrics()` implementation distinguishes a parent-keyed standard Parseval convention from an original, sibling-keyed convention activated by `original_parseval=True`.

The former excludes trivial leaf constituents. The latter includes leaf constituents, which can increase reported scores when EDU segmentation is held fixed.

Some published model descriptions refer to original Parseval with trivial leaf spans excluded. That shorthand is not sufficient to identify the implementation's exact counting procedure.

For precise comparisons, the scoring function, constituent enumeration, segmentation condition, and relation mapping must be identified together.

This is a documentation and comparability qualification, not evidence that the published results are incorrect.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/data/metrics.py`

## 6. Experiment lifecycle, checkpoints, and research tooling

### 6.1 Full `dipo runs` management interface

The original overview mentioned configuration-hash-based experiments and `runs list`, but the released CLI provides a larger management interface.

| Command                | Function                                                          |
| ---------------------- | ----------------------------------------------------------------- |
| `dipo runs list`       | Enumerate runs and selected metadata                              |
| `dipo runs show`       | Inspect configuration, metrics, files, and checkpoint information |
| `dipo runs diff`       | Compare configuration fields across two runs                      |
| `dipo runs rename`     | Rename a run while retaining its hash-based identity              |
| `dipo runs archive`    | Archive completed run artifacts                                   |
| `dipo runs delete`     | Remove a specified run                                            |
| `dipo runs delete-all` | Remove all runs after explicit confirmation                       |

The archive mechanism is the most consequential addition.

It extracts durable experimental records—configuration files, evaluation results, predictions, and selected snapshots—without necessarily retaining every expensive model checkpoint.

It includes an archive index (`INDEX.tsv`) containing fields such as parser type, model name, dataset, seed, decoding beam count, and selected evaluation metrics.

Archived records are grouped by parser and run identifier.

### 6.2 Verified archival and disk reclamation

The archival implementation includes several safeguards.

It selects completed runs using the presence of `final_metrics.json`, stages archived files into a temporary directory, records SHA-256 hashes in a manifest, validates archived JSON files, and replaces the destination with the staged archive.

These checks reduce the risk of treating an incomplete experimental run as a finished artifact.

The hash manifest provides provenance and later integrity-checking information, although its existence should not be mistaken for a complete cryptographic verification of every copied file against its original during the archive operation.

The optional `--delete-pt` flag removes source checkpoint files and TensorBoard data after the archive has been created and validated.

That operation reclaims disk space but does not preserve enough information to resume model training or reconstruct a full checkpoint from the archive alone.

The distinction between preserving experimental evidence and preserving resumable model state is therefore explicit.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/runs.py`

### 6.3 Atomic checkpointing and recovery behavior

Dipo's shared training utilities write checkpoints and metadata through temporary files followed by `os.replace()`.

This reduces the risk of leaving an existing checkpoint partially overwritten when training is interrupted.

Checkpoint loading also uses CPU mapping before moving relevant state into the model and optimizer. This avoids temporarily allocating a second full checkpoint on the GPU during restoration.

The resumption path checks the stored configuration hash against the expected training configuration.

If a checkpoint is truncated or unreadable, the implementation can fall back to the best-model checkpoint when available. If no usable checkpoint remains, training may begin from a fresh state.

Configuration mismatches are reported rather than silently treated as equivalent training runs.

For trainable-only checkpoints, Dipo reconstructs the frozen backbone separately and restores the saved trainable parameters. Unexpected state-dictionary keys are treated as evidence of an incompatible checkpoint rather than silently ignored.

These mechanisms are relevant to large-model training where checkpoint size, interruption risk, and resumption consistency can be significant operational concerns.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/common/training.py`

## 7. Release, security, and implementation-status qualifications

### 7.1 Development-only functionality

The original overview distinguished the post-release `maekawa` parser and generative segmentation-only serialization from the published package. That distinction remains necessary.

The repository's `master` branch added `maekawa` and the `gen` serialization mode `seg` after the 0.2.1 release.

The new `seg` mode generates EDU boundaries using copy and shift actions, without requiring rhetorical reductions. Its returned tree contains placeholder structure; only the segmentation is meaningful.

This allows the same broad generative architecture to provide an EDU segmenter independently of complete rhetorical parsing.

The development-only Maekawa parser can use this functionality as a separate segmentation stage before its decision-by-decision parsing process.

These features are implemented in the inspected development source but are not part of the published 0.2.1 package.

Development sources:

`https://github.com/larc-iu/dipo/blob/master/dipo/rst/parsers/gen/serializations/seg.py`

`https://github.com/larc-iu/dipo/blob/master/dipo/rst/parsers/maekawa/README.md`

### 7.2 Declared configuration fields are not always executable capabilities

Several configuration fields exist for compatibility or future integration without providing the behavior their names might suggest.

In particular, the released generative configuration declares `chat_template` and `width_band_loss`, but their non-null behaviors are not fully wired into the `gen` training and inference implementation.

The shared PEFT configuration also retains certain historical fields that are explicitly inert, including `modules_to_save` and `train_only_new_embedding_rows`. Their accepted values are constrained to maintain compatibility with archived configurations rather than providing independent current behavior.

Similarly, the ICL configuration recognizes grammar backend names beyond `gbnf`, but the corresponding emitters are not implemented.

These are examples where examining configuration dataclasses alone can overstate the library's executable capability.

Source:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/gen/configuration_gen.py`

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/rst/parsers/common/config.py`

### 7.3 Published version metadata

The current published PyPI release verified for this addendum is 0.2.1, released October 12, 2026. It should be described as the latest published release rather than a stable or production-mature release, because the package metadata identifies it as alpha-stage software.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



The inspected 0.2.1 source also contains an internal metadata discrepancy: `pyproject.toml` declares `0.2.1`, while `dipo.__version__` remains `0.2.0`.

When identifying an installed package version, the installed distribution metadata is therefore more reliable than the module-level version constant:

```
from importlib.metadata import versionprint(version("dipo"))
```

### 7.4 Checkpoint deserialization and trust boundaries

Dipo's checkpoint-loading code explicitly calls `torch.load()` with `weights_only=False`.

This permits deserialization of arbitrary Python objects through the underlying pickle machinery.

PyTorch's own documentation warns against loading untrusted files with this mechanism, since deserialization can execute code.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.14 documentation



This limitation applies to checkpoint trust, not to the mathematical correctness of the parsing algorithms.

For systems that ingest arbitrary third-party artifacts, a Dipo `.pt` checkpoint should therefore be treated as trusted executable input rather than an inert data file.

The fact that a checkpoint is hosted on Hugging Face or can be downloaded automatically does not, by itself, establish that it is safe to deserialize.

Sources:

`https://github.com/larc-iu/dipo/blob/v0.2.1/dipo/common/training.py`

`https://docs.pytorch.org/docs/stable/generated/torch.load.html`

## Addendum synthesis

The additional capabilities establish three useful architectural distinctions that extend the original Dipo reference.

First, Dipo's constrained parsing mechanisms operate at several levels. They can constrain output syntax, legal parser transitions, the number of EDU-consuming actions, and even the source content associated with those actions. These guarantees are distinct from rhetorical accuracy, and their availability depends on the model family and inference backend.

Second, document identity is not a single invariant throughout the library. Source characters, normalized characters, whitespace tokens, transformer subwords, EDU indices, and rhetorical spans are different coordinate systems. Dipo contains substantial machinery for relating them, but its representations and serializers preserve different subsets of the original information.

Third, Dipo provides more than training and inference. It includes specialized mechanisms for controlled evaluation, error decomposition, cross-model comparisons, checkpoint recovery, model-serving behavior, and durable experimental records.

Together, these capabilities make Dipo a substantive discourse-parsing framework rather than merely a collection of pretrained RST models. Its strongest advanced features are the interactions between structural validity, source-text alignment, model-specific decoding, and evaluation consistency—with clear boundaries where those mechanisms do not establish semantic correctness or lossless document preservation.

The descriptions above are based on upstream source and documentation inspection. They do not imply that the library was executed or independently benchmarked during this review.