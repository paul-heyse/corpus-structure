# spaCy 3.8.16 — Comprehensive Python Library Overview

Research date: October 20, 2026 | Target: spaCy 3.8.16 (current stable release, published August 24, 2026) | Python: 3.9–3.14 | License: MIT

Primary sources: [spaCy documentation](https://spacy.io/usage?utm_source=chatgpt.com) · [API reference](https://spacy.io/api?utm_source=chatgpt.com) · [GitHub repository](https://github.com/explosion/spaCy?utm_source=chatgpt.com) · [PyPI releases](https://pypi.org/project/spacy/?utm_source=chatgpt.com) · [Model catalog](https://spacy.io/models?utm_source=chatgpt.com)

The current stable release is 3.8.16. The 4.0 development releases visible in the package history are not the stable API target for this reference. spaCy's Python compatibility now includes Python 3.14; older installation instructions that limit support to Python 3.12 are outdated.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+1



## 1. Executive orientation

spaCy is a high-performance natural language processing framework built around a structured representation of documents and a configurable sequence of linguistic, statistical, neural, and rule-based processing components.

Its central value is not simply its collection of pretrained models. It provides a relatively unified runtime and development framework for turning text into reusable, structured linguistic annotations and domain-specific extraction results.

That framework spans:

- Linguistic analysis: tokenization, sentence segmentation, morphological analysis, part-of-speech tagging, lemmatization, dependency parsing, and named entity recognition.
- Structured information extraction: exact and fuzzy matching, linguistic pattern matching, entity identification, overlapping span extraction, entity linking, and document classification.
- Neural NLP: efficient token representations, contextual embeddings, transformer integrations, custom architectures, multitask learning, and trainable pipeline components.
- Hybrid processing: combining dictionaries, rules, syntactic analysis, statistical models, and application-specific logic within one processing pipeline.
- NLP infrastructure: compact document representations, custom annotation schemas, serialization, training-data management, reproducible configuration, evaluation, packaging, and workflow orchestration.
- Extensibility: custom tokenizers, component factories, registered model architectures, reusable pipelines, and interoperability with other Python machine-learning tools.

A consequential architectural characteristic is that these capabilities operate over a common document model, rather than requiring independent tools to exchange loosely structured intermediate results.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation

+2



### 1.1 The conceptual architecture

Raw text

Strings, document streams, application input

Language-specific tokenizer

Produces token boundaries, spacing, offsets, and a Doc

Configurable processing pipeline

Linguistic analysis

Tagger · Parser · Lemmatizer

Neural representations

Tok2Vec · Transformer

Entity & span extraction

NER · SpanCategorizer · Rulers

Custom and hybrid logic

Matchers · Registered components

Components run in a configured order; dependencies and shared representations constrain some arrangements.

Annotated `Doc`

Tokens · Spans · Entities · Dependencies · Categories · Custom attributes

Extraction, classification, indexing, persistence, and downstream processing

Structured application outputs, serialized documents, or inputs to other systems

Conceptually:

1. A `Language` object (`nlp`) owns the tokenizer, shared vocabulary, configuration, and processing pipeline.
2. Tokenization constructs a `Doc`, spaCy's central representation of a text and its token boundaries.
3. Each pipeline component reads and/or writes linguistic annotations on the document.
4. Multiple components can reuse representations produced by earlier components, including shared neural layers.
5. The resulting document can be queried, matched, transformed, serialized, or passed to downstream systems.

The pipeline is configurable rather than fixed. A lightweight rule-based extractor, a multilingual linguistic processor, and a transformer-backed entity recognition system can all use the same broad document and component abstractions.

See [Processing pipelines](https://spacy.io/usage/processing-pipelines?utm_source=chatgpt.com) and [Language API](https://spacy.io/api/language?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation



### 1.2 Capability map

| Functional area          | Principal spaCy mechanisms                                                              | Architectural significance                                                    |
| ------------------------ | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Document representation  | `Doc`, `Token`, `Span`, `SpanGroup`, `Vocab`                                            | Common typed objects for linguistic annotations and extraction                |
| Linguistic preprocessing | `Tokenizer`, `Sentencizer`, `Tagger`, `Morphologizer`, `Lemmatizer`, `DependencyParser` | Reusable linguistic features for downstream analysis                          |
| Rule-based extraction    | `Matcher`, `PhraseMatcher`, `DependencyMatcher`, `EntityRuler`, `SpanRuler`             | Declarative extraction instead of extensive handwritten text-processing logic |
| Statistical extraction   | `EntityRecognizer`, `SpanCategorizer`, `SpanFinder`                                     | Learning entity and span boundaries, including overlapping spans              |
| Entity normalization     | `EntityLinker`, `KnowledgeBase`                                                         | Linking textual mentions to stable identifiers                                |
| Classification           | `TextCategorizer`, `textcat_multilabel`                                                 | Predicting document-level labels                                              |
| Neural representations   | `Tok2Vec`, Thinc, transformer integrations                                              | Configurable representations and parameter sharing                            |
| Training                 | `Example`, `DocBin`, config registry, `spacy train`                                     | Custom trainable NLP pipelines with reproducible configuration                |
| Workflow infrastructure  | `spacy project`, `spacy evaluate`, `spacy package`                                      | Lifecycle management beyond inference                                         |
| Integration              | Custom factories, registry, companion packages                                          | Extend the pipeline without replacing the execution framework                 |

Several especially important capabilities are easy to underestimate: overlapping span annotations, dependency-tree matching, fuzzy linguistic rules, shared neural representations, configurable training through registered functions, and entity linking to custom knowledge bases. These make spaCy useful well beyond conventional named entity recognition.

Python compatibility clarification: spaCy 3.8.8 explicitly dropped Python 3.9 support, although the 3.8.16 PyPI metadata still declares `>=3.9`. The practical supported range for the current release is therefore Python 3.10–3.14, rather than the broader metadata range shown above.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



## 2. Document and annotation architecture

spaCy's internal document representation is one of its most consequential capabilities. It separates the actual annotation storage from the objects through which callers inspect it, and shares lexical information across documents.

### 2.1 `Doc`, `Token`, `Span`, and `Vocab`

| Object        | Responsibility                          | Important capabilities                                                    |
| ------------- | --------------------------------------- | ------------------------------------------------------------------------- |
| `Language`    | Pipeline and language runtime           | Tokenization, component execution, configuration, training, serialization |
| `Doc`         | Owns token sequence and annotations     | Entities, sentences, categories, spans, document tensors, custom data     |
| `Token`       | View of an individual token             | Linguistic properties, dependencies, offsets, extensions                  |
| `Span`        | View of a contiguous token range        | Labels, character boundaries, local linguistic analysis                   |
| `SpanGroup`   | Named collection of spans               | Overlapping annotations, alternative analyses, group metadata             |
| `Vocab`       | Shared lexical state                    | String hashes, lexical attributes, vocabulary vectors                     |
| `Lexeme`      | Context-independent lexical information | Orthography, lexical flags, word-level statistics                         |
| `StringStore` | String-to-hash mapping                  | Compact integer representation of repeated linguistic strings             |

The `Doc` owns the underlying token annotations. `Token` and `Span` are lightweight views into that document, rather than independently owned copies of text and annotations.

`Vocab` provides shared lexical data, allowing many documents to refer to the same stored strings and lexical entries. Textual labels and linguistic attributes are frequently represented internally by integer hashes; attributes with trailing underscores, such as `token.pos_` and `span.label_`, expose human-readable strings.

This design helps reduce redundant storage, supports efficient annotation access, and enables pipeline components to communicate through shared objects.

It also has implications for lifecycle management: spans refer to their parent documents, annotations are tied to token boundaries, and modifying tokenization can invalidate token-index assumptions.

Sources: [Library architecture](https://spacy.io/api?utm_source=chatgpt.com), [Doc](https://spacy.io/api/doc?utm_source=chatgpt.com), [Vocab](https://spacy.io/api/vocab?utm_source=chatgpt.com), [Token](https://spacy.io/api/token?utm_source=chatgpt.com), [Span](https://spacy.io/api/span?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



### 2.2 Overlapping spans and parallel annotation layers

One of spaCy's most valuable distinctions is between `Doc.ents` and `Doc.spans`.

`Doc.ents` represents a set of non-overlapping named entities. This is the conventional output of spaCy's transition-based entity recognizer.

`Doc.spans` provides a dictionary of named `SpanGroup` collections. Within a group, spans can overlap, be nested, or otherwise represent competing or complementary interpretations.

Consider:

Example text

"The New York University research team published its findings."

ORG

New York University

GPE candidate

New York

NP

The New York University research team

Illustrative alternative annotations, not assertions that a pretrained model would assign these particular labels.

All three annotations can coexist in separate span groups without forcing a single segmentation of the text.

For example:

```
doc.spans["organizations"] = organization_spansdoc.spans["locations"] = location_spansdoc.spans["noun_phrases"] = noun_phrase_spans
```

`SpanGroup` also supports group-level attributes, including JSON-serializable metadata. The span categorizer uses group attributes to store prediction scores.

This enables several useful designs:

- Maintain separate rule-based, model-predicted, and reference annotations.
- Preserve nested or overlapping mentions instead of prematurely discarding them.
- Track alternative label systems over the same text.
- Store candidate extractions for subsequent filtering or classification.
- Compose deterministic and statistical recognizers without forcing all outputs into `Doc.ents`.

A limitation is that `SpanGroup` is a collection of spans, not a general-purpose relation graph. Arbitrary relationships between spans still require additional representation.

Sources: [SpanGroup](https://spacy.io/api/spangroup?utm_source=chatgpt.com), [SpanRuler](https://spacy.io/api/spanruler?utm_source=chatgpt.com), [SpanCategorizer](https://spacy.io/api/spancategorizer?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation

+1



### 2.3 Character alignment, offsets, and retokenization

spaCy treats tokenization and text alignment as first-class concerns.

Important mechanisms include:

- `Token.idx`: the token's character offset.
- `Span.start`, `Span.end`: start and exclusive end token indices.
- `Span.start_char`, `Span.end_char`: character offsets.
- `Doc.char_span()`: construct a token-aligned span from character offsets.
- `Doc.retokenize()`: controlled merging or splitting of tokens.
- `Alignment`: mapping between different tokenizations, including one-to-many alignments.

`Doc.char_span()` offers three alignment modes:

| Mode       | Behavior                                                             |
| ---------- | -------------------------------------------------------------------- |
| `strict`   | Requires character boundaries to align exactly with token boundaries |
| `contract` | Includes only tokens fully contained in the character interval       |
| `expand`   | Includes tokens intersecting the character interval                  |

The choice matters when extracting annotations from external models, OCR systems, search engines, or datasets whose tokenization differs from spaCy's.

Retokenization is similarly significant. `Doc.retokenize()` allows merging or splitting tokens while maintaining spaCy's annotation machinery. However, changing token boundaries changes token indices and can affect downstream components, previously computed spans, and training-data alignment. Tokenization conventions should therefore be treated as part of a model's data contract.

spaCy's default tokenization is non-destructive: its token representation preserves enough information to reconstruct the original text, including whitespace.

Sources: [Doc API](https://spacy.io/api/doc?utm_source=chatgpt.com), [Tokenizer](https://spacy.io/api/tokenizer?utm_source=chatgpt.com), [Linguistic features — tokenization and alignment](https://spacy.io/usage/linguistic-features?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation

+1



### 2.4 Custom annotations as part of the document model

`Doc`, `Token`, and `Span` can have custom extension attributes registered with `set_extension()` and accessed through the `._` namespace.

An extension can provide a stored default value, a getter, a setter, or a custom method. This allows domain-specific information to behave like an ordinary part of the spaCy document interface.

For example, custom extensions could represent normalized identifiers, domain-specific classifications, provenance, or results produced by an external processor.

More advanced integration is possible through `Doc.user_hooks`, `Doc.user_token_hooks`, and `Doc.user_span_hooks`, which can override selected property and method behavior for a document and its views.

The important distinction is between spaCy's internal token annotation fields and application-defined extension data. Extensions are powerful composition points, but they do not automatically become new native token columns or new model-predicted attributes.

Persistence also requires care. Some custom extension data is stored through `Doc.user_data`, and preserving it through `DocBin` requires `store_user_data=True`.

Sources: [Custom extensions](https://spacy.io/usage/processing-pipelines?utm_source=chatgpt.com#custom-components-attributes), [Doc API](https://spacy.io/api/doc?utm_source=chatgpt.com), [DocBin](https://spacy.io/api/docbin?utm_source=chatgpt.com).

## 3. Linguistic preprocessing and analysis

spaCy supplies both deterministic and trainable components for turning raw text into linguistically annotated text.

An important distinction is that the library's ability to represent an annotation does not mean a particular installed pipeline predicts it.

A blank language pipeline can tokenize and expose language-specific lexical rules without including pretrained POS, dependency, or NER models.

### 3.1 Tokenization and language-specific processing

spaCy tokenization combines language-specific rules with a configurable processing algorithm. Rather than relying exclusively on whitespace, it handles punctuation boundaries, exceptions, abbreviations, prefixes, suffixes, infixes, and special token classes.

Its tokenizer provides several extension points:

| Mechanism                 | Function                                                        |
| ------------------------- | --------------------------------------------------------------- |
| Special-case rules        | Explicit tokenization of known strings and constructions        |
| Prefix/suffix/infix rules | Control punctuation and separator handling                      |
| `token_match`             | Preserve strings that should not be split by the relevant rules |
| `url_match`               | Preserve recognized URLs                                        |
| `Tokenizer.explain()`     | Explain which tokenization rules were applied                   |
| Custom tokenizer factory  | Replace the tokenizer through spaCy's configuration system      |
| Language subclasses       | Customize defaults, lexical attributes, and language processing |

For example, domain-specific identifiers, chemical names, technical abbreviations, or code-like strings may need different tokenization from general-purpose prose.

Importantly, spaCy can express many such adjustments through rules without requiring an entirely new tokenizer implementation.

Language-specific tokenization and pretrained linguistic models are separate concerns. spaCy supports tokenization and training across more than 70 languages, while downloadable trained pipelines cover a smaller subset with varying annotation capabilities.

Source: [Linguistic features and tokenizer customization](https://spacy.io/usage/linguistic-features?utm_source=chatgpt.com#tokenization).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation



### 3.2 POS tagging, morphology, and lexical normalization

spaCy distinguishes several related annotation families:

- `Token.pos`: coarse-grained part-of-speech category, such as `NOUN` or `VERB`.
- `Token.tag`: language-specific fine-grained grammatical tag.
- `Token.morph`: morphological features such as tense, number, gender, and person.
- `Token.lemma`: canonical base form.
- Lexical flags and attributes: punctuation, numeric likeness, stop-word membership, casing, shape, prefixes, suffixes, and normalization.

This separation matters because the annotations have different sources and dependencies.

The `tagger` learns fine-grained tags, while `morphologizer` can predict coarse-grained POS and morphological features. The `attribute_ruler` can supply mappings and exceptions between surface forms, tags, and other attributes.

spaCy also offers distinct approaches to lemmatization:

| Approach               | Component              | Mechanism                                          |
| ---------------------- | ---------------------- | -------------------------------------------------- |
| Lookup                 | `lemmatizer`           | Dictionary-based base-form lookup                  |
| Rule-based             | `lemmatizer`           | Language rules, often conditioned on POS           |
| POS-conditioned lookup | `lemmatizer`           | Lookup using grammatical information               |
| Trainable              | `trainable_lemmatizer` | Predict edit trees transforming tokens into lemmas |

The trainable `EditTreeLemmatizer` is particularly relevant where lookup coverage or inflection rules are insufficient. It predicts transformations rather than independently memorizing every surface-form/lemma pair.

These annotations can also serve as features for matchers and custom statistical architectures, allowing one linguistic analysis to support multiple downstream operations.

Sources: [Linguistic features](https://spacy.io/usage/linguistic-features?utm_source=chatgpt.com), [Lemmatizer](https://spacy.io/api/lemmatizer?utm_source=chatgpt.com), [EditTreeLemmatizer](https://spacy.io/api/edittreelemmatizer?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation

+1



### 3.3 Syntactic analysis and dependency parsing

`DependencyParser` constructs a labeled dependency tree over tokens.

Each token has a syntactic head and a dependency label, allowing access to grammatical relationships such as subjects, objects, modifiers, complements, and their associated subtrees.

The parser can also establish sentence boundaries, and spaCy exposes noun-chunk extraction for languages with the necessary syntax iterators and annotations.

Its architecture is more specific than a generic graph classifier: spaCy uses a transition-based parser based on a non-monotonic arc-eager system, with pseudo-projective transformations to handle non-projective dependencies.

This makes dependency parsing useful not only as an annotation task, but as a basis for structural queries.

For instance, detecting a verb and its subject/object across different word orders is often better expressed as a dependency pattern than as a contiguous sequence of tokens.

The limitation is that the result is a learned syntactic analysis, not a semantic representation guaranteed to be correct. Parsing errors can propagate to any rules that depend on particular dependency labels.

Source: [DependencyParser](https://spacy.io/api/dependencyparser?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



### 3.4 Sentence segmentation alternatives

spaCy supplies three materially different sentence-boundary mechanisms:

| Component     | Method                                                | Tradeoff                                          |
| ------------- | ----------------------------------------------------- | ------------------------------------------------- |
| `sentencizer` | Deterministic punctuation rules                       | Lightweight, no training required, less adaptable |
| `senter`      | Statistical sentence boundary prediction              | Learns boundaries without a full dependency parse |
| `parser`      | Sentence segmentation jointly with dependency parsing | Rich syntax, more computational work              |

The choice depends on whether sentence boundaries alone are sufficient or syntactic dependencies are also required.

For applications that only need sentence segmentation, using a dependency parser can introduce unnecessary execution cost. spaCy explicitly documents `senter` as a faster alternative to full parsing, while the exact speed and accuracy depend on the model and evaluation data.

Sources: [Pipeline design](https://spacy.io/models?utm_source=chatgpt.com), [SentenceRecognizer](https://spacy.io/api/sentencerecognizer?utm_source=chatgpt.com), [Sentencizer](https://spacy.io/api/sentencizer?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Models Documentation



## 4. Rule-based matching and structured extraction

spaCy's matching framework is one of the strongest reasons to consider it as an extraction platform even when statistical NLP is not required.

It provides multiple engines with different matching semantics.

### 4.1 The matcher families

| Engine              | Matching model                            | Distinctive capability                                   |
| ------------------- | ----------------------------------------- | -------------------------------------------------------- |
| `Matcher`           | Token sequences with attribute predicates | Rich linguistic conditions, quantifiers, fuzzy matching  |
| `PhraseMatcher`     | Pre-tokenized phrase patterns             | Efficient large-scale terminology matching               |
| `DependencyMatcher` | Syntactic dependency relationships        | Structural matches independent of simple token adjacency |
| `EntityRuler`       | Declarative entity patterns               | Integration of deterministic entities with NER           |
| `SpanRuler`         | Declarative span patterns                 | Overlapping and nested matches in `Doc.spans`            |

These are not interchangeable. Their differences reflect the structure of the information being recognized.

Sources: [Rule-based matching guide](https://spacy.io/usage/rule-based-matching?utm_source=chatgpt.com), [Matcher](https://spacy.io/api/matcher?utm_source=chatgpt.com), [PhraseMatcher](https://spacy.io/api/phrasematcher?utm_source=chatgpt.com), [DependencyMatcher](https://spacy.io/api/dependencymatcher?utm_source=chatgpt.com).

### 4.2 `Matcher`: declarative linguistic patterns

`Matcher` expresses token sequences as dictionaries of constraints.

A pattern can depend on surface text or normalized text, lemma, POS, dependency label, morphology, token length, punctuation, lexical flags, or a registered custom extension.

It also supports:

- Optional and repeated tokens through regex-like quantifiers: `?`, `+`, `*`, `{n}`, `{n,m}`.
- Membership comparisons: `IN`, `NOT_IN`.
- Numeric comparisons: `>`, `<`, `>=`, `<=`, `==`.
- Regular expressions over individual token attribute values.
- Fuzzy comparisons using edit distance.
- Set operations over morphological or custom list-valued attributes.
- Callbacks and direct conversion of matches into labeled spans.

For example, an illustrative pattern matching a verb followed by an optional determiner and a noun:

```
pattern = [    {"POS": "VERB"},    {"POS": "DET", "OP": "?"},    {"POS": "NOUN"},]
```

The pattern does not need to hardcode all permitted words. It operates over grammatical annotations that have already been computed.

#### Fuzzy matching

spaCy 3.5 introduced the `FUZZY` operators, an important capability for robust terminology matching.

Patterns can use `FUZZY` with a default edit-distance rule or `FUZZY1` through `FUZZY9` with explicit limits. The comparator is configurable, and fuzzy matching can be combined with membership operators.

For example:

```
pattern = [    {"LOWER": {"FUZZY2": "transformer"}}]
```

This can tolerate limited spelling variation without requiring a separate approximate string matching engine.

The caveat is that this remains token-attribute matching. Fuzzy matching does not automatically provide semantic equivalence, synonym resolution, or approximate document retrieval.

Similarly, `REGEX` within a token pattern operates on token attributes. It is not equivalent to running an arbitrary regular expression over the complete original document.

Source: [Matcher API](https://spacy.io/api/matcher?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



### 4.3 `PhraseMatcher`: efficient large-dictionary lookup

`PhraseMatcher` is designed for matching known phrases against tokenized text.

It accepts `Doc` objects as patterns and can compare attributes such as exact text or lowercase form.

This is useful for:

- Domain-specific terminology libraries.
- Product and organization dictionaries.
- Controlled vocabularies.
- Abbreviation and synonym lists.
- Rule-driven annotation and candidate generation.

It is generally preferable to `Matcher` when the problem is recognizing many known phrases rather than evaluating complex token-by-token linguistic predicates.

Patterns can be constructed using `nlp.make_doc()` when only tokenization is required, avoiding the cost of running trained NLP components on every dictionary entry.

Source: [PhraseMatcher API](https://spacy.io/api/phrasematcher?utm_source=chatgpt.com) and [efficient phrase matching](https://spacy.io/usage/rule-based-matching?utm_source=chatgpt.com#phrasematcher).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation



### 4.4 `DependencyMatcher`: structural pattern recognition

`DependencyMatcher` matches relationships within a parsed dependency tree.

Patterns define nodes, token attributes, and relationships between nodes. The matcher then searches the dependency graph for configurations satisfying those constraints.

This is materially different from `Matcher`, whose patterns operate on sequences.

It enables rules built around structures such as:

- A particular verb and its grammatical subject.
- A named entity occurring as the object of a specified action.
- A modifier attached to a noun.
- Structural relationships between participants in a sentence.
- Linguistic constructions whose intervening words vary.

The result is a set of matched token indices corresponding to the pattern's nodes.

The main advantage is that grammatical structure can replace large collections of sentence-order permutations. The cost is dependency on a parser, its runtime cost, its supported languages, and its accuracy on the target text.

Source: [DependencyMatcher API](https://spacy.io/api/dependencymatcher?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



### 4.5 `EntityRuler` versus `SpanRuler`

`EntityRuler` integrates deterministic entity recognition with the `Doc.ents` representation. It can be placed before or after a statistical recognizer, with ordering and overwrite behavior controlling how rule-based matches interact with model predictions.

For example, exact known entities can be supplied through rules while a statistical recognizer handles entities not captured by the dictionary.

`SpanRuler` generalizes the concept by allowing matches to be written into `Doc.spans`, preserving overlaps. It can optionally assign non-overlapping entities to `Doc.ents` as well.

This makes `SpanRuler` especially useful for multiple extraction layers, overlapping domain mentions, and annotation workflows requiring intermediate candidates rather than a finalized entity sequence.

Both rulers support string-based phrase patterns and token-based patterns. They also support persistence of their patterns and customizable filtering.

Architectural implication: the ruler components make deterministic extraction a native part of spaCy's pipeline and serialization model. They can replace custom rule dispatch, span construction, and annotation integration code, while leaving room for specialized business logic where required.

Sources: [EntityRuler](https://spacy.io/api/entityruler?utm_source=chatgpt.com), [SpanRuler](https://spacy.io/api/spanruler?utm_source=chatgpt.com), [rule-based span matching](https://spacy.io/usage/rule-based-matching?utm_source=chatgpt.com#span-ruler).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



## 5. Statistical extraction, classification, and entity linking

spaCy's trainable components cover several distinct prediction problems. Choosing the appropriate representation of the desired output is often more important than choosing a particular neural architecture.

### 5.1 Named entity recognition: `EntityRecognizer`

The standard `ner` component is a transition-based recognizer that predicts labeled, non-overlapping entity spans and writes them to `Doc.ents`.

It optimizes for correct complete entities, not independent correctness of every token's label. spaCy also documents an architectural bias toward information appearing near an entity's initial tokens.

Those design choices work well for conventional named entity recognition, but are less suitable for some domain extraction tasks involving:

- Nested or overlapping mentions.
- Long spans whose distinguishing information occurs near the end.
- Inconsistent annotation boundaries.
- Multiple valid interpretations of the same text.
- A requirement to preserve alternative candidate spans.

This is a substantive limitation, not something that can necessarily be resolved by changing model size or training for longer.

If overlapping spans are a fundamental property of the output, `SpanCategorizer` or a combined span-finding/categorization system provides a more natural representation.

Source: [EntityRecognizer API](https://spacy.io/api/entityrecognizer?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



### 5.2 `SpanCategorizer`: trainable overlapping extraction

Status: experimental API, available since spaCy 3.1

`SpanCategorizer` (`spancat`) predicts labels for candidate text spans, including spans that overlap.

Its design separates two operations:

1. Candidate generation: a suggester proposes spans that might be relevant.
2. Candidate classification: a learned model assigns labels and scores to the candidates.

This separation is consequential. It allows the candidate-generation problem to be addressed with linguistic rules, bounded n-grams, a previous processing component, or another span detection mechanism while using statistical learning to classify the results.

spaCy provides two main variants:

| Variant               | Label semantics                          | Model output                            |
| --------------------- | ---------------------------------------- | --------------------------------------- |
| `spancat`             | Zero, one, or multiple labels for a span | Independent logistic outputs            |
| `spancat_singlelabel` | At most one positive label for a span    | Softmax with an explicit negative class |

The second variant was introduced in spaCy 3.5.1.

Predictions are written to a configurable `doc.spans[spans_key]`, while per-span scores are available in that group's `attrs["scores"]`.

This enables a separation between recognition and downstream acceptance. For example, candidate spans can be scored, filtered, compared with deterministic rules, or subjected to subsequent normalization.

Important tradeoff: a span classifier can only evaluate candidates that its suggester makes available. Candidate recall, number of candidates, span-length bounds, negative examples, and label ambiguity are therefore part of the overall model design.

Source: [SpanCategorizer API](https://spacy.io/api/spancategorizer?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



### 5.3 `SpanFinder`: learned span proposal

Status: experimental API, added in spaCy 3.6

`SpanFinder` (`span_finder`) provides a complementary capability: it predicts which tokens start and end spans, then generates unlabeled, potentially overlapping candidate spans.

The output is stored in `Doc.spans`.

It can be combined with `SpanCategorizer` to create a two-stage extraction architecture:

Document tokens

SpanFinder

Predict candidate starts and ends

Candidate spans

Unlabeled; may overlap

SpanCategorizer

Filter and label candidates

Labeled `SpanGroup`

The resulting design separates span boundary discovery from span classification.

That can be useful when the span vocabulary is large or the relevant spans are not easily enumerated through fixed-length n-grams or terminology dictionaries.

However, multiple possible starts and ends can produce a large candidate set. Thresholds and minimum/maximum span lengths affect both computational cost and recall. Training components that consume predicted upstream annotations can also require careful configuration so inference-time dependencies are represented during training.

Sources: [SpanFinder API](https://spacy.io/api/spanfinder?utm_source=chatgpt.com), [SpanCategorizer](https://spacy.io/api/spancategorizer?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



### 5.4 Entity linking and knowledge bases

Entity recognition answers a question such as which text span refers to an entity, and what kind of entity is it?

Entity linking answers a different question: which particular entity does that mention identify?

spaCy provides a trainable `EntityLinker` and a `KnowledgeBase` abstraction for associating textual mentions with stable identifiers.

The knowledge base represents entities, aliases, frequencies or priors, and entity vectors. An entity candidate generator obtains plausible identifiers for a mention, and the linking model uses contextual information to choose among candidates.

Important mechanisms include:

- `KnowledgeBase`: the abstract contract for candidate retrieval and entity data.
- `InMemoryLookupKB`: the built-in in-memory implementation.
- `Candidate`: a plausible linked entity together with supporting KB information.
- `get_candidates` and `get_candidates_batch`: customizable mention-to-candidate generation.
- `kb_loader`: initialization integration for supplying a knowledge base.
- `EntityLinker`: the trainable component that resolves mentions to knowledge-base identifiers.
- `Span.kb_id` / `Span.kb_id_`: linked identifier annotations.
- `NIL`: a result indicating no accepted knowledge-base link.

Since spaCy 3.5, `KnowledgeBase` is abstract; earlier versions' concrete implementation is exposed as `InMemoryLookupKB`.

The default candidate generation is based on exact, case-sensitive aliases. More sophisticated candidate generation requires customization.

This is useful for canonicalizing organizations, people, products, biomedical concepts, technical terms, or other mentions against an external ontology. It can reduce custom disambiguation infrastructure when the knowledge base and training examples are suitable.

However, entity linking is not a general database integration layer or universal ontology reasoner. The underlying KB content, identifier scheme, alias coverage, and update procedures remain separate responsibilities.

Sources: [EntityLinker](https://spacy.io/api/entitylinker?utm_source=chatgpt.com), [KnowledgeBase](https://spacy.io/api/kb?utm_source=chatgpt.com), [InMemoryLookupKB](https://spacy.io/api/inmemorylookupkb?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation

+1



### 5.5 Document-level text classification

`TextCategorizer` predicts document-level category scores and writes them to `Doc.cats`.

spaCy distinguishes two important modes:

| Component            | Assumption                      | Score behavior                           |
| -------------------- | ------------------------------- | ---------------------------------------- |
| `textcat`            | Exactly one correct class       | Mutually exclusive scores sum to 1       |
| `textcat_multilabel` | Any number of classes may apply | Independent class scores; no fixed total |

This choice affects both prediction and supervision.

For `textcat`, omitted labels in gold-standard category annotations are treated as false and influence the loss.

For `textcat_multilabel`, missing gold-standard category entries do not contribute to the loss or accuracy calculation.

This is particularly important when a corpus has incomplete annotations or is assembled from several partially overlapping labeling sources. Treating missing labels as negative observations can materially change what the model learns.

The output model is also distinct from span categorization: `Doc.cats` classifies a document rather than identifying exact spans that justify a classification.

Source: [TextCategorizer API](https://spacy.io/api/textcategorizer?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



## 6. Neural architectures, representations, and transformers

spaCy's neural system has several layers that should be distinguished:

1. Static lexical vectors stored in the vocabulary.
2. Trainable contextual token representations.
3. Task-specific neural networks for prediction.
4. Transformer-backed representations supplied through companion packages.
5. The underlying Thinc neural-network framework that composes these architectures.

They have different semantics, resource requirements, and integration surfaces.

### 6.1 Static word vectors versus contextual token representations

spaCy can store pretrained word vectors in `Vocab.vectors`.

These are lexical representations: a vector is associated with a word or lexical key, independently of its context in a particular sentence.

The library exposes vector-related operations through APIs such as `Token.vector`, `Doc.vector`, `Span.vector`, and corresponding similarity methods.

A critical distinction is that spaCy's default `Doc.vector` and `.similarity()` behavior should not be confused with modern transformer sentence embeddings.

Where available, document and span vectors commonly derive from averaging token vectors. Their semantics depend on the lexical vector tables and available tensors, not automatically on a transformer encoder or retrieval-trained embedding head.

Official pipeline packages reflect this distinction:

- `sm` pipelines have no static word vectors.
- `md` and `lg` pipelines commonly provide static vectors, with different table sizes.
- `trf` pipelines use transformers but do not ordinarily include static word vectors.

Consequently, loading a `trf` pipeline does not by itself mean that `Doc.vector` is a purpose-trained semantic search embedding.

Source: [Trained pipeline conventions](https://spacy.io/models?utm_source=chatgpt.com), [Vectors API](https://spacy.io/api/vectors?utm_source=chatgpt.com), [Word vectors and similarity](https://spacy.io/usage/linguistic-features?utm_source=chatgpt.com#vectors-similarity).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Models Documentation



#### Floret vectors

spaCy supports floret subword vectors through its vectors infrastructure.

These use hashed subword representations and can produce vectors for strings not directly present in a conventional word-vector vocabulary.

The benefit is broader lexical coverage and compact representation, particularly for morphologically varied or out-of-vocabulary words.

The limitation is that the hashed representation does not support all operations available with ordinary vector tables. For example, enumerating lexical keys and conventional nearest-neighbor lookup through `Vectors.most_similar()` are not supported in the same way.

Floret vectors should therefore be understood as an alternative lexical representation, not as an automatic replacement for a learned contextual embedding model.

Source: [Vectors API](https://spacy.io/api/vectors?utm_source=chatgpt.com).

### 6.2 `Tok2Vec`: shared contextual token representations

`Tok2Vec` produces contextual token representations that downstream components can use for tagging, parsing, entity recognition, classification, and other tasks.

spaCy's standard architectures allow an embedding subnetwork and contextual encoder to be composed separately.

Examples of registered building blocks include:

- `MultiHashEmbed`: embeddings from multiple hashed lexical attributes.
- `CharacterEmbed`: character-based token representations.
- `MaxoutWindowEncoder`: convolutional contextual encoding.
- `HashEmbedCNN` and `Tok2Vec`: higher-level architectures composed from embedding and encoding layers.

The use of hashed features and CNN-style contextual encoders offers a relatively lightweight alternative to large pretrained transformer networks for many structured NLP tasks.

This is not simply an inference optimization. Multiple trainable components can connect to the same upstream representation producer through `Tok2VecListener`.

For example, a tagger and parser can share the earlier `tok2vec` component, reducing redundant representation computation and allowing them to participate in shared training.

However, sharing depends on the actual configuration. Not every component automatically shares a representation merely because it is in the same pipeline.

In spaCy's standard non-transformer pretrained pipelines, the tagger, morphologizer, and parser may share a common `tok2vec`, while NER commonly has its own internal tok2vec layer.

Sources: [Tok2Vec](https://spacy.io/api/tok2vec?utm_source=chatgpt.com), [Model architectures](https://spacy.io/api/architectures?utm_source=chatgpt.com), [Trained pipeline design](https://spacy.io/models?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Models Documentation



### 6.3 Transformers: two significant integration paths

spaCy has two major transformer integration packages. Neither should be confused with an unconditional dependency of the core `spacy` package.

| Integration                  | Pipeline factory      | Main distinction                                                                          |
| ---------------------------- | --------------------- | ----------------------------------------------------------------------------------------- |
| `spacy-curated-transformers` | `curated_transformer` | Curated selection of supported transformer model families, integrated with spaCy training |
| `spacy-transformers`         | `transformer`         | Broader Hugging Face Transformers model integration                                       |

#### Curated Transformers

Introduced into spaCy's documented architecture in 3.7, `CuratedTransformer` uses the separate `spacy-curated-transformers` package.

Documented model families include BERT, RoBERTa, ALBERT, CamemBERT, and XLM-RoBERTa.

It exposes `Doc._.trf_data` and integrates with downstream components through specialized transformer listener layers.

Source: [CuratedTransformer API](https://spacy.io/api/curatedtransformer?utm_source=chatgpt.com) · [spacy-curated-transformers repository](https://github.com/explosion/spacy-curated-transformers?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



#### Hugging Face Transformers integration

The `spacy-transformers` companion package provides a configurable `transformer` component with access to transformer models through Hugging Face's Transformers library.

It includes:

- Subword tokenization and alignment with spaCy tokens.
- Shared transformer representations for multiple components.
- `TransformerListener` architectures.
- Configurable span selection and model-output handling.
- Access to transformer outputs through `Doc._.trf_data`.
- Integration with spaCy's training and evaluation system.

This allows a pretrained transformer encoder to act as the common representation layer for several structured prediction tasks.

Source: [Transformer API](https://spacy.io/api/transformer?utm_source=chatgpt.com) · [spacy-transformers repository](https://github.com/explosion/spacy-transformers?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



#### Transformer alignment and long-text considerations

Transformer models commonly operate on subword pieces, whereas spaCy operates on its own language-specific tokens.

The transformer integration handles alignment between these representations so that spaCy's token-level prediction heads can use subword-derived contextual information.

The integrations also provide configurable mechanisms for processing text in windows or spans, addressing transformer sequence-length constraints.

Nevertheless, long-document processing remains constrained by transformer context limits, window overlap, memory consumption, and the need to reconcile representations across processed segments.

A transformer integration is therefore not inherently a whole-document semantic reasoning engine, and increasing its context coverage does not eliminate downstream task limitations.

### 6.4 Multitask training, listeners, and freezing

One of the most technically important spaCy features is its distinction between sharing an upstream representation model and copying or independently training a representation model.

A listener architecture allows downstream components to receive representations computed by a shared upstream component and, during training, return gradients through that shared computation.

This can reduce redundant computation and permit task signals to influence shared representations.

It also introduces lifecycle dependencies:

- Pipeline ordering must ensure shared representations are available before listeners consume them.
- Training batches and upstream cached representations need to remain aligned.
- Freezing one component while training another can interact unexpectedly with shared upstream weights.
- A sourced component may need listener replacement to make its internal representation independent of a changing shared model.

spaCy provides `replace_listeners` in the training configuration for this reason.

`training.annotating_components` is another important mechanism. It allows designated components to supply predicted annotations during training, so downstream components can be trained under conditions closer to those encountered during inference.

These settings become particularly relevant in pipelines combining entity recognition, learned span proposal, dependent classifiers, or pretrained frozen components.

Sources: [Training pipelines](https://spacy.io/usage/training?utm_source=chatgpt.com), [Model architectures](https://spacy.io/api/architectures?utm_source=chatgpt.com), [Embeddings and transformers](https://spacy.io/usage/embeddings-transformers?utm_source=chatgpt.com).

### 6.5 Thinc as spaCy's neural composition layer

spaCy uses Thinc for neural-network model construction, training, registries, and framework integration.

Thinc's `Model` abstraction supports compositional network construction, typed forward/backpropagation interfaces, parameter management, and trainable layers.

spaCy exposes these architectures through registered functions referenced in configuration, rather than requiring users to construct every component's neural network procedurally.

Custom architectures can be registered with `@spacy.registry.architectures`, with their parameters, initialization, and training configuration managed through the same broader system.

Thinc also provides mechanisms for integrating external machine-learning frameworks, including PyTorch models, using wrapper or shim architectures where supported.

This matters because a custom neural model does not necessarily require a custom NLP runtime. A task-specific model can potentially use spaCy's document handling, batching, training lifecycle, evaluation, packaging, and annotation interfaces while replacing selected neural operations.

The integration is not cost-free: tensor shapes, gradient propagation, device placement, data conversion, initialization, and serialization must remain compatible with the selected architecture.

Sources: [Thinc documentation](https://thinc.ai/docs/?utm_source=chatgpt.com), [Thinc model API](https://thinc.ai/docs/api-model/?utm_source=chatgpt.com), [spaCy neural architectures](https://spacy.io/api/architectures?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



## 7. Pipeline extensibility and configuration

spaCy's extension model is broader than adding a Python function to a list. Its component registry, configuration system, annotations, and training interfaces collectively provide an extensible NLP execution environment.

### 7.1 Custom components and factories

There are two primary ways to register a custom pipeline component:

| Mechanism             | Intended use                                            |
| --------------------- | ------------------------------------------------------- |
| `@Language.component` | Register a simple function operating on `Doc`           |
| `@Language.factory`   | Construct configurable, potentially stateful components |

A simple component can be registered declaratively:

```
from spacy.language import Languagefrom spacy.tokens import DocDoc.set_extension("word_count", default=0)@Language.component("word_counter", assigns=["doc._.word_count"])def word_counter(doc):    doc._.word_count = len(doc)    return doc
```

It can then be added through `nlp.add_pipe("word_counter")` and represented in a saved pipeline's configuration.

Factories support richer initialization: configuration values, shared resources, component state, access to `nlp`, and integration with component serialization or training interfaces where implemented.

This registration mechanism also underlies many optional spaCy extensions. Companion packages can expose factories through Python package entry points, making their registered components discoverable when installed.

Source: [Custom pipeline components](https://spacy.io/usage/processing-pipelines?utm_source=chatgpt.com#custom-components).

### 7.2 Component contracts and static pipeline analysis

Component registration supports metadata such as:

- `assigns`: attributes the component promises to set.
- `requires`: attributes required from earlier components.
- `retokenizes`: whether a component changes token boundaries.

`nlp.analyze_pipes()` uses this metadata to inspect a pipeline's annotation dependencies.

For example, it can identify a component that requires entities even though no earlier component declares that it assigns them.

This is valuable for complex pipelines because configuration can encode some of the relationships between components instead of leaving them entirely implicit.

There is an important limitation: this analysis is static and relies on declared metadata. It does not execute components or prove that they correctly implement their contracts.

For a custom component, declared requirements and assignments should therefore describe actual behavior, not merely desired behavior.

Source: [Processing pipelines — analyzing components](https://spacy.io/usage/processing-pipelines?utm_source=chatgpt.com#analyzing-pipeline-components).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation



### 7.3 Enabling, disabling, excluding, and sourcing components

spaCy exposes several related operations with different meanings.

| Mechanism                      | Effect                                         |
| ------------------------------ | ---------------------------------------------- |
| `nlp.add_pipe()`               | Add a component through its registered factory |
| `nlp.remove_pipe()`            | Remove a component from the pipeline           |
| `nlp.replace_pipe()`           | Replace an existing component                  |
| `nlp.disable_pipe()`           | Keep a component loaded but inactive           |
| `nlp.enable_pipe()`            | Reactivate a disabled component                |
| `nlp.select_pipes()`           | Temporarily select which components execute    |
| `spacy.load(..., disable=...)` | Load components but disable selected ones      |
| `spacy.load(..., exclude=...)` | Do not load selected components                |
| `source` configuration         | Reuse a component from another pipeline        |

These distinctions matter for resource usage and correctness.

Disabling a component prevents its execution, but does not necessarily remove the cost of loading its model. Excluding it avoids loading the component altogether.

More importantly, disabling an upstream representation component can make downstream listeners unusable or degrade downstream annotations.

Sourcing a trained component from another pipeline also requires attention to vocabulary, vector configuration, and model dependencies. Component reuse is not guaranteed to be equivalent when the surrounding pipeline changes.

Source: [Processing pipelines](https://spacy.io/usage/processing-pipelines?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation



### 7.4 Configuration as an executable model specification

spaCy 3's `config.cfg` format describes not only simple hyperparameters but also the construction of a trainable pipeline.

It can specify:

- Pipeline components and their order.
- Factories and component settings.
- Neural model architectures and sublayers.
- Training and validation data readers.
- Optimizers and learning-rate schedules.
- Batching strategies.
- Data augmentation.
- Model initialization.
- Frozen and annotating components.
- Custom callbacks and registered functions.

Configuration sections use typed values, references, interpolation, and registry identifiers.

For example, the same model architecture can be reused through a registered function:

```
[components.tok2vec]
factory = "tok2vec"

[components.tok2vec.model]
@architectures = "spacy.HashEmbedCNN.v2"
width = 128
depth = 4
```

This is illustrative configuration, not a complete validated training config.

The important architectural feature is dependency injection through registered functions. A different model architecture, optimizer, batcher, or data reader can often be selected by changing the configuration rather than modifying spaCy's implementation.

Registries include `@architectures`, `@optimizers`, `@schedules`, `@batchers`, `@readers`, and other registered function families.

Configuration validation checks registered function arguments and types. `spacy init fill-config` can resolve defaults into a complete configuration suitable for training.

A practical limit is that a config containing custom registry entries is not fully self-sufficient: the Python package or code registering those entries must be available when the pipeline is constructed. The serialized weights do not replace the custom implementation.

Source: [Training configuration system](https://spacy.io/usage/training?utm_source=chatgpt.com#config), [Model architectures](https://spacy.io/api/architectures?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation



## 8. Training infrastructure, evaluation, and lifecycle tooling

spaCy provides more of the supervised NLP lifecycle than its inference-focused reputation might suggest.

### 8.1 `Example`: aligned predicted and reference documents

The `Example` abstraction holds two `Doc` objects:

- `predicted`: the document receiving model predictions.
- `reference`: the document containing gold-standard annotations.

It also contains an `Alignment` between the predicted and reference tokenizations.

That alignment is significant because reference annotations and the runtime tokenizer may not partition text identically.

The abstraction is used across training and evaluation, allowing distinct components to consume reference data through a common representation.

spaCy also provides utilities such as `Example.from_dict()` for constructing examples from annotation dictionaries, and corpus readers for streaming examples from training data.

This can reduce the need for task-specific training-data object models, especially in systems combining several annotation types.

Source: [Example API](https://spacy.io/api/example?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



### 8.2 `DocBin`: compact annotation storage

`DocBin` serializes collections of annotated documents to spaCy's binary `.spacy` format.

Its implementation uses gzipped MessagePack, compact numerical attribute representations, and a shared collection of strings.

Relevant capabilities include:

- Selectively storing token attributes.
- Preserving tokenization, whitespace, and selected linguistic annotations.
- Efficiently serializing multiple documents.
- Optional serialization of custom `Doc.user_data`.
- Producing a standard input format for spaCy training, evaluation, and benchmarking.

Unlike ordinary pickling, `DocBin` can be deserialized without executing arbitrary Python code. However, it is not designed for efficient random access to individual documents.

The `store_user_data` setting is also important when documents contain application-specific extensions. It does not imply that every external object, model intermediate, or custom component state can be automatically restored.

Architectural distinction: `DocBin` is an annotation interchange and persistence mechanism, not a relational database, random-access document store, or replacement for a general analytics format.

Sources: [DocBin API](https://spacy.io/api/docbin?utm_source=chatgpt.com), [Saving and loading](https://spacy.io/usage/saving-loading?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



### 8.3 Training and initialization

The principal training workflow uses `spacy train` with a configuration specifying the model, datasets, and optimization strategy.

spaCy supports:

- Training models from initialized weights.
- Updating existing trained pipelines.
- Reusing pretrained or sourced components.
- Freezing selected components.
- Replacing listeners to separate shared parameters.
- Custom data augmentation and corpus readers.
- Configurable early stopping, evaluation frequency, dropout, batching, and optimization.
- CPU or compatible GPU-backed training.

`nlp.initialize()` configures and initializes trainable components, often using representative `Example` objects to infer output dimensions, label sets, or model parameters.

spaCy also supports low-level training through the Python API for cases requiring more control than the standard CLI workflow.

#### Pretraining token representations

An easily overlooked feature is `spacy pretrain`, an experimental mechanism for initializing token-to-vector models from raw text.

Its documented objective uses pretrained word vectors as targets: a contextual encoder is trained to predict representations resembling those vectors. The resulting weights can initialize a subsequent supervised training run through `init_tok2vec`.

This is conceptually different from pretraining a modern autoregressive language model or masked-language transformer from scratch.

It can be relevant when raw domain text is plentiful but labeled examples are limited, subject to the quality of the target vectors and the suitability of the pretraining objective.

Sources: [Training guide](https://spacy.io/usage/training?utm_source=chatgpt.com), [Training CLI and pretraining](https://spacy.io/api/cli?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation

+1



### 8.4 CLI capabilities beyond training

spaCy's CLI includes a meaningful collection of data, diagnostic, and deployment operations.

| Command family             | Function                                                         |
| -------------------------- | ---------------------------------------------------------------- |
| `spacy init config`        | Generate a training configuration                                |
| `spacy init fill-config`   | Fill and validate configuration defaults                         |
| `spacy init labels`        | Extract label inventories                                        |
| `spacy convert`            | Convert supported external annotations into spaCy formats        |
| `spacy debug config`       | Inspect configuration problems                                   |
| `spacy debug data`         | Check training data and label consistency                        |
| `spacy debug model`        | Inspect Thinc model structure and initialization/update behavior |
| `spacy debug profile`      | Profile pipeline execution                                       |
| `spacy train`              | Train and evaluate configured models                             |
| `spacy benchmark accuracy` | Evaluate pipeline quality                                        |
| `spacy benchmark speed`    | Measure pipeline throughput                                      |
| `spacy apply`              | Apply a pipeline to files and produce annotated `DocBin` output  |
| `spacy find-threshold`     | Evaluate classification thresholds against a selected metric     |
| `spacy assemble`           | Construct a configured pipeline without further training         |
| `spacy package`            | Package a pipeline for distribution                              |
| `spacy validate`           | Check installed pipeline compatibility                           |

Three of these deserve particular attention.

`spacy apply` provides a native batch annotation workflow for raw text, JSONL, and existing `.spacy` data. It supports batching and multiprocessing and writes annotated documents back to a `DocBin`.

`spacy find-threshold` searches prediction thresholds for components whose output depends on a threshold, including multilabel text classification and span categorization. This separates threshold selection from model training.

`spacy benchmark speed` measures words per second after warmup and reports a 95% confidence interval. This provides a built-in benchmark methodology, although measurements remain dependent on hardware, document distribution, component selection, and batch configuration.

Source: [spaCy command-line reference](https://spacy.io/api/cli?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation

+2



### 8.5 Evaluation and scoring

spaCy's `Scorer` and component-specific scoring functions cover multiple annotation families, including:

- Tokenization and sentence boundaries.
- Part-of-speech tagging and morphological annotation.
- Dependency attachment and labels.
- Named entity precision, recall, and F-score.
- Span extraction and categorization.
- Text categorization.
- Entity linking.

The particular metrics available depend on the configured components and gold-standard annotations.

The distinction between span-level, token-level, and entity-level evaluation is important. For example, a recognizer can achieve good token-level behavior while producing poor exact-boundary entity matches.

Likewise, strict boundary evaluation is different from evaluating whether a downstream system extracted a useful concept.

spaCy's scoring system can be extended through registered custom scorers, enabling task-specific evaluation without replacing the broader training and reporting infrastructure.

Source: [Scorer API](https://spacy.io/api/scorer?utm_source=chatgpt.com).

### 8.6 `spacy project`: declarative NLP workflows

`spacy project` provides workflow management around the training and packaging lifecycle.

A `project.yml` can describe:

- Downloadable or externally supplied data assets.
- Commands and reusable workflows.
- Command inputs and generated outputs.
- Environment and version constraints.
- Checksums for data assets.
- Remote storage locations.
- Training, evaluation, packaging, and related custom operations.

The dependency/output declarations let spaCy avoid rerunning commands when their declared inputs and outputs have not changed.

It also supports template cloning, remote artifact push/pull, and integrations with external tools such as DVC.

A key distinction is that spaCy Projects is not a fully automatic dependency-graph execution engine. Its workflow commands run in specified order; running a command does not automatically execute all missing upstream commands. Its documentation explicitly distinguishes this behavior from richer orchestration tools such as DVC.

This can replace lightweight custom scripting for repeatable NLP experiments, but it is not intended to replace arbitrary general-purpose workflow platforms.

Source: [spaCy Projects](https://spacy.io/usage/projects?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation

+1



## 9. Runtime performance, batching, and memory control

Performance is a major design priority in spaCy, but it is useful to distinguish native execution mechanisms from choices that require workload-specific measurement.

### 9.1 Streaming and batch processing

`nlp.pipe()` processes iterable inputs in batches and yields annotated documents.

Compared with repeatedly invoking `nlp(text)` in a Python loop, batch processing can reduce orchestration overhead and enable more efficient execution of neural components.

Key controls include:

- `batch_size`: number of documents processed together.
- `n_process`: number of worker processes.
- `disable`: components to skip for the operation.
- `as_tuples`: preserve caller-provided context alongside documents.
- `component_cfg`: supply supported per-component execution settings.

A common technique is to pair text with its source identifier:

```
texts = [    ("Example document A", {"id": "a"}),    ("Example document B", {"id": "b"}),]for doc, context in nlp.pipe(texts, as_tuples=True):    ...
```

This avoids forcing document identity, source metadata, and other application concerns into the original text.

`nlp.make_doc(text)` provides an even lighter operation when tokenization is sufficient and no pipeline components need to run.

Source: [Efficient text processing](https://spacy.io/usage/processing-pipelines?utm_source=chatgpt.com#processing).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation



### 9.2 Multiprocessing and GPU considerations

spaCy supports multiprocessing through `nlp.pipe(..., n_process=N)`.

Whether it improves performance depends on the interaction among model size, document length, batching, process startup overhead, and memory availability.

On systems using the `spawn` multiprocessing method, each worker may require a separate copy of substantial model state. For short documents, creating and coordinating extra workers can cost more than the parallelism saves.

For transformer-backed execution, GPU utilization, batch size, activation memory, and host/device transfer costs become especially important.

Using additional processes against the same GPU is not inherently faster; multiple independent workers may increase memory pressure and device contention.

spaCy's own documentation warns about the complexities of multiprocessing with GPU models and PyTorch. Process-based parallelism should not be assumed to be an unconditional optimization.

Source: [Multiprocessing guidance](https://spacy.io/usage/processing-pipelines?utm_source=chatgpt.com#multiprocessing).

### 9.3 Memory zones in spaCy 3.8

A major newer capability is `Language.memory_zone()`, introduced in spaCy 3.8.

Long-running pipelines can accumulate lexical entries and other cached data in their shared vocabulary. Memory zones provide an explicit processing lifetime within which spaCy can create temporary document objects, then release associated cache data at the end of the zone.

Conceptually:

```
with nlp.memory_zone():    doc = nlp("Example text")    result = [(ent.text, ent.label_) for ent in doc.ents]# Only use the independent Python result outside the zone.
```

The constraint is unusually important:

All `Doc`, `Token`, `Span`, and `Lexeme` objects created inside the zone become invalid after it exits. Accessing them afterward can cause a segmentation fault.

This is a native-memory lifetime constraint, not just an ordinary Python exception or a warning about stale results.

Consequently, memory zones are appropriate only where the caller can enforce that no spaCy-owned objects escape the processing lifetime. Extracting plain strings, integers, or independently owned data within the zone provides a safer boundary.

This feature can be valuable in long-lived services processing large and varied vocabularies, but it should not be treated as a general-purpose garbage collector or a mechanism for managing arbitrary external resources.

Source: [Memory management](https://spacy.io/usage/memory-management?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation



### 9.4 `doc_cleaner` and intermediate tensor retention

spaCy also provides a `doc_cleaner` component.

Its default behavior clears intermediate data such as:

- `Doc.tensor`.
- `Doc._.trf_data`, when present.

These fields can retain large neural intermediate representations after the downstream prediction components have finished using them.

If many annotated `Doc` objects are retained, such data can unnecessarily consume system or GPU memory.

Placing `doc_cleaner` appropriately near the end of a pipeline can free intermediate representations while retaining final linguistic annotations.

The qualification is that downstream components or consumers relying on those tensors can no longer use the cleared data. Cleanup must occur after all required consumers.

Memory zones and `doc_cleaner` solve different problems: the former manages certain lifetime-bound internal caches, while the latter removes selected data retained on individual documents.

Source: [Clearing document attributes](https://spacy.io/usage/memory-management?utm_source=chatgpt.com#doc-cleaner).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation



### 9.5 Where performance optimization changes the architecture

Several capabilities combine to reduce unnecessary computation:

| Workload characteristic                      | Native mechanism to investigate          | What changes                                             |
| -------------------------------------------- | ---------------------------------------- | -------------------------------------------------------- |
| Large input corpus                           | `nlp.pipe()`                             | Batch overhead and component execution                   |
| Tokenization-only tasks                      | `nlp.make_doc()`                         | Avoids statistical processing entirely                   |
| A few needed annotations                     | `disable` / `exclude`                    | Omits unnecessary models and computations                |
| Many known phrases                           | `PhraseMatcher`                          | Replaces repeated high-level matching logic              |
| Related trainable tasks                      | Shared `Tok2Vec` / transformer listeners | Avoids some duplicate representation computation         |
| Persistent service with growing vocabulary   | `memory_zone()`                          | Allows cache reclamation at explicit lifetime boundaries |
| Large retained transformer-annotated corpora | `doc_cleaner`                            | Removes unused intermediate tensors                      |
| Domain-specific prediction thresholds        | `spacy find-threshold`                   | Improves decision calibration without retraining weights |
| Pipeline throughput comparison               | `spacy benchmark speed`                  | Provides repeatable workload-specific measurements       |

These are architectural options rather than universal performance prescriptions. Their effects depend on pipeline composition, model architecture, runtime environment, and the representation requirements of downstream consumers.

## 10. Ecosystem integrations and companion libraries

The distinction between spaCy core, official companion packages, and third-party extensions is important. Some of spaCy's most interesting capabilities are documented alongside the core API even though they require separate packages and may have different compatibility or stability guarantees.

### 10.1 Companion-package landscape

| Package                                                                                                        | Main capability                                                           | Integration boundary                                                                     |
| -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| [spacy-curated-transformers](https://github.com/explosion/spacy-curated-transformers?utm_source=chatgpt.com)   | Curated pretrained transformer architectures                              | Separate package; supplies the `curated_transformer` factory                             |
| [spacy-transformers](https://github.com/explosion/spacy-transformers?utm_source=chatgpt.com)                   | Hugging Face transformer integration                                      | Separate package; supplies the `transformer` factory                                     |
| [spacy-huggingface-pipelines](https://github.com/explosion/spacy-huggingface-pipelines?utm_source=chatgpt.com) | Wrap pretrained Hugging Face task pipelines                               | Inference-oriented integration, distinct from shared transformer representation training |
| [spacy-llm](https://github.com/explosion/spacy-llm?utm_source=chatgpt.com)                                     | LLM prompting and structured NLP outputs                                  | Separate experimental package                                                            |
| [spacy-layout](https://github.com/explosion/spacy-layout?utm_source=chatgpt.com)                               | Extract layout-aware text and tables from documents                       | Separate package built on Docling                                                        |
| [spacy-experimental](https://github.com/explosion/spacy-experimental?utm_source=chatgpt.com)                   | Experimental components, including coreference and trainable tokenization | Separate package with restricted version compatibility                                   |
| [scispaCy](https://github.com/allenai/scispacy?utm_source=chatgpt.com)                                         | Scientific and biomedical NLP pipelines                                   | Third-party domain-specific models and components                                        |
| [spacy-lookups-data](https://github.com/explosion/spacy-lookups-data?utm_source=chatgpt.com)                   | Linguistic lookup tables                                                  | Separate data package for applicable language-processing components                      |

The official [spaCy Universe](https://spacy.io/universe?utm_source=chatgpt.com) catalogs additional extensions, tools, and integrations. Compatibility and maintenance status need to be established for each package independently of spaCy's own release status.

### 10.2 `spacy-llm`: LLM inference inside structured pipelines

Status: separate experimental package; latest verified release 0.7.4, March 24, 2026

`spacy-llm` introduces components that call language models and translate their responses into spaCy annotations.

Rather than treating LLM invocation as an unrelated post-processing operation, it places prompting and response parsing within the same pipeline model used by deterministic and supervised components.

The architecture distinguishes:

- Task: how to construct prompts and parse responses into annotations.
- Model: which LLM or backend executes the prompts.
- Caching: mechanisms to reuse previously generated results.
- Sharding: mechanisms for splitting documents or prompts and combining results.
- Custom registries: extension points for new tasks, parsers, and model backends.

Documented tasks include named entity recognition, overlapping span extraction, text categorization, entity linking, relationship extraction, sentiment analysis, lemmatization, summarization, translation, and raw prompt execution.

Its integration can be valuable for capabilities that are difficult to express with conventional rules or for rapidly developing structured extraction tasks without an existing labeled corpus.

An important interaction is the ability to combine LLM-derived outputs with deterministic and trainable components. For instance, an LLM can propose spans or classifications while inexpensive rules check admissible labels, normalize identifiers, or reject structurally invalid output.

However, LLM-produced annotations do not inherit the same guarantees as deterministic matches or validated supervised predictions. Prompt sensitivity, output parsing failures, cost, latency, and data-sharing requirements remain important considerations.

The package itself is marked experimental, and its maintainers explicitly caution that minor releases may introduce breaking interface changes.

Sources: [spaCy LLM integration guide](https://spacy.io/usage/large-language-models?utm_source=chatgpt.com), [spaCy LLM API](https://spacy.io/api/large-language-models?utm_source=chatgpt.com), [spacy-llm PyPI](https://pypi.org/project/spacy-llm/?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation

+2



### 10.3 Coreference resolution: experimental and version-constrained

Coreference resolution identifies mentions that refer to the same underlying person, object, or concept.

spaCy documents an experimental `CoreferenceResolver` that creates clusters of mentions in `Doc.spans`. The companion `SpanResolver` can expand word-level mentions into larger referring spans.

These are potentially important capabilities for extracting information that is distributed across sentences or connected through pronouns and repeated references.

They are not standard built-in spaCy 3.8 pipeline components. They are supplied by `spacy-experimental`, using factories such as `experimental_coref`.

There is a specific compatibility caveat: the latest published `spacy-experimental` release I verified is 0.6.4, and its upstream requirements specify `spacy>=3.3.0,<3.8.0`. Consequently, it should not be assumed to install or operate directly with the spaCy 3.8.16 target of this reference.

The experimental package also includes alternative trainable character-based tokenizers and other research-oriented NLP components. These should be evaluated separately from spaCy's stable core capabilities.

Sources: [CoreferenceResolver documentation](https://spacy.io/api/coref?utm_source=chatgpt.com), [spacy-experimental repository](https://github.com/explosion/spacy-experimental?utm_source=chatgpt.com), [published dependency constraints](https://github.com/explosion/spacy-experimental/blob/master/requirements.txt?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation

+2



### 10.4 `spacy-layout`: connecting document structure to linguistic processing

The separate `spacy-layout` package integrates with Docling to process PDFs, Word documents, and other supported input formats.

It converts parsed document contents into spaCy `Doc` objects and preserves layout information through extensions and span groups.

Documented outputs include:

- `Doc.spans["layout"]` for layout regions.
- `Doc._.layout` for document layout information.
- `Doc._.tables` for extracted tables.
- `Doc._.markdown` for a Markdown representation.
- Layout-related span annotations and metadata.

This addresses a significant boundary in NLP pipelines: raw document text often loses meaningful information when extracted without section hierarchy, headings, page structure, or tables.

By representing layout within spaCy's document model, downstream NLP components can potentially operate over structurally selected regions rather than treating all extracted text as one undifferentiated string.

For example, semantic chunking can incorporate document headings and sections, while entity recognition or terminology extraction can be applied to selected content regions.

The document parsing itself belongs to Docling and the `spacy-layout` integration, not to spaCy's core tokenizer or parser. Accuracy and supported formats depend on those underlying capabilities.

Source: [spaCy Layout repository and documentation](https://github.com/explosion/spacy-layout?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 10.5 Scientific and specialized NLP

`scispaCy` extends the spaCy ecosystem with pipelines and components oriented toward biomedical and scientific text.

It illustrates an important property of spaCy's architecture: specialized vocabularies, entity detection approaches, pretrained models, and knowledge-base linking can be delivered as independently maintained packages while retaining spaCy's common document and pipeline interfaces.

Similar integration patterns are possible for legal, financial, technical, and multilingual processing.

However, the existence of a domain-specific model does not guarantee that its labels, tokenization behavior, or training corpus match an arbitrary domain. Model-version compatibility and annotation semantics need to be verified independently.

Source: [scispaCy repository](https://github.com/allenai/scispacy?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 10.6 Visualization and diagnostics

spaCy includes `displaCy` as a core visualization capability.

Supported visualization styles include:

- `dep`: syntax and dependency relationships.
- `ent`: named entities.
- `span`: span annotations, including overlapping spans.

Visualizations can be rendered to HTML and used in notebooks or browser-based inspection.

These are useful for diagnosing tokenization, unexpected entity boundaries, incorrect dependency structures, and disagreement between span annotation layers.

This is a particularly useful complement to quantitative evaluation: aggregate precision or recall metrics can identify a quality problem, while visualization makes the underlying annotation failure more interpretable.

Source: [spaCy visualizers](https://spacy.io/usage/visualizers?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation



## 11. Consequential architectural choices

The greatest design value often comes from combining spaCy capabilities rather than selecting them individually.

The following distinctions are particularly important when evaluating how much custom infrastructure spaCy can replace.

### 11.1 Extraction representation determines what information survives

| Desired result                                            | Natural spaCy mechanism                     | Important boundary                                                   |
| --------------------------------------------------------- | ------------------------------------------- | -------------------------------------------------------------------- |
| One conventional entity label per non-overlapping mention | `EntityRecognizer`, `Doc.ents`              | Nested and overlapping entities cannot be represented together       |
| Deterministic recognition of known terms                  | `PhraseMatcher`, `EntityRuler`              | No inherent contextual disambiguation                                |
| Complex linguistic phrase patterns                        | `Matcher`                                   | Predicates operate on available token annotations                    |
| Grammatical relationships                                 | `DependencyMatcher`                         | Requires a suitable dependency parse                                 |
| Multiple overlapping candidate mentions                   | `SpanRuler`, `Doc.spans`                    | Rule matches still need downstream resolution when ambiguous         |
| Learned overlapping extraction                            | `SpanCategorizer`                           | Candidate coverage and classification are separate concerns          |
| Learned mention proposals                                 | `SpanFinder`                                | Experimental, unlabeled candidates require downstream interpretation |
| Canonical entity identifiers                              | `EntityLinker`                              | Needs a suitable KB and candidate generation                         |
| Whole-document labels                                     | `TextCategorizer`, `Doc.cats`               | Does not identify precise supporting spans                           |
| Relations between extracted entities                      | Custom components or companion integrations | Not equivalent to standard entity recognition                        |

The important question is not merely which algorithm recognizes a string, but which intermediate representations must remain available after recognition.

If overlapping interpretations, alternative hypotheses, or candidate scores matter downstream, collapsing everything into `Doc.ents` can discard valuable information too early.

### 11.2 Hybrid extraction can reduce bespoke control logic

Several combinations are particularly expressive.

Dictionary matching followed by learned disambiguation. `PhraseMatcher` or `SpanRuler` can identify possible domain concepts, while a statistical span classifier determines which candidates are relevant in context.

Rule-based entities and statistical NER. `EntityRuler` can preserve known high-confidence mentions while `EntityRecognizer` handles unseen or context-dependent entities. Pipeline order and overwrite behavior determine their interactions.

Span detection followed by normalization. `SpanFinder` and `SpanCategorizer` can identify mentions, while `EntityLinker` or custom normalization logic maps them to canonical concepts.

Syntactic analysis followed by structural extraction. `DependencyParser` creates a reusable parse, enabling many `DependencyMatcher` patterns to operate without each requiring its own parsing or sentence-structure machinery.

Shared representations supporting several prediction heads. A common tok2vec or transformer representation can support multiple trainable tasks, reducing duplicated encoding while permitting task-specific outputs.

These combinations illustrate how spaCy can function as an annotation and inference kernel: a common execution framework supporting multiple extraction techniques without requiring each technique to define its own tokenization, object model, serialization, and lifecycle.

Their practical benefits depend on annotation quality, component dependencies, model suitability, and the amount of additional conversion or reconciliation required.

### 11.3 Boundary between spaCy and search infrastructure

spaCy is primarily an NLP processing framework, not a comprehensive search or retrieval engine.

It can produce tokens, lemmas, entities, normalized identifiers, classifications, lexical vectors, and other features useful for indexing.

It does not itself supply the full responsibilities of a search platform: persistent inverted indexes, distributed retrieval, comprehensive query planning, or production-grade vector indexing and retrieval.

Likewise, lexical similarity or a transformer-backed NER encoder should not automatically be treated as a retrieval-optimized sentence embedding system.

This suggests a useful separation of concerns:

- spaCy can construct and enrich the linguistic representation of documents.
- A retrieval engine can index and search that representation.
- An embedding model can supply representations optimized for semantic similarity.
- Downstream ranking or reasoning systems can use the resulting candidates and annotations.

The boundary is important because spaCy's native strengths are often complementary to specialized search, database, and embedding systems rather than replacements for them.

### 11.4 Version and reproducibility boundaries

There are at least four independent version dimensions:

| Version dimension           | Example                                       | Why it matters                                                      |
| --------------------------- | --------------------------------------------- | ------------------------------------------------------------------- |
| Core library                | `spacy==3.8.16`                               | Runtime implementation and APIs                                     |
| Trained pipeline package    | `en_core_web_sm` in a compatible 3.8.x series | Weights, tokenizer configuration, labels, and component composition |
| Companion packages          | `spacy-transformers`, `spacy-llm`, etc.       | Optional factories, features, dependencies, and stability           |
| Underlying model/checkpoint | A particular BERT or other pretrained model   | Architecture, weights, tokenizer, licenses, and behavior            |

spaCy's downloadable pipeline version numbers encode spaCy major/minor compatibility and an independent model package revision.

`spacy download` selects a compatible pipeline package using its compatibility information, while `spacy validate` checks compatibility of installed pipelines.

A library patch release and a model package revision are therefore different events and should not be conflated.

Source: [Trained pipeline versions and compatibility](https://spacy.io/models?utm_source=chatgpt.com), [CLI download and validation](https://spacy.io/api/cli?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Models Documentation

+1



## 12. Principal limitations and technical considerations

The following are cross-cutting distinctions that can materially change a spaCy architecture.

| Consideration                                        | Consequence                                                                                          |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Tokenization is foundational                         | Changing token boundaries affects offsets, spans, alignments, and potentially trained model behavior |
| Pretrained capabilities depend on the pipeline       | A blank pipeline and a downloadable pretrained pipeline expose different annotation abilities        |
| Statistical predictions are fallible                 | POS, dependency, entity, and linking errors can propagate into downstream rules                      |
| Standard NER is non-overlapping                      | Overlapping/nested span tasks require other annotation mechanisms                                    |
| Shared representation models create dependencies     | Pipeline ordering, training updates, and freezing require configuration awareness                    |
| Static vectors and contextual representations differ | They should not be treated as interchangeable semantic embeddings                                    |
| Model quality is domain-dependent                    | General-purpose model benchmarks do not establish task-specific extraction accuracy                  |
| Custom extensions have persistence rules             | User data and Python registration code may need explicit handling                                    |
| Multiprocessing increases resource demands           | Startup, model replication, and GPU contention can outweigh parallel execution gains                 |
| Memory zones create strict lifetimes                 | Using spaCy objects after their zone exits can result in unsafe native-memory access                 |
| Experimental APIs may change                         | SpanCategorizer, SpanFinder, `spacy-llm`, and `spacy-experimental` require closer version scrutiny   |
| Companion packages have independent compatibility    | A package documented on spacy.io may not support the current spaCy core release                      |
| `DocBin` is sequential annotation storage            | It does not replace indexed persistence or arbitrary querying                                        |

These do not diminish spaCy's capabilities. They define the boundaries within which its native mechanisms provide the strongest architectural leverage.

## 13. Primary-source reference map

The links below provide a compact navigation index for deeper research. Each is a direct URL and can be used independently of this overview.

| Research area                                              | Authoritative source                                                                                                    |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Overall architecture                                       | [https://spacy.io/api](https://spacy.io/api?utm_source=chatgpt.com)                                                     |
| Language processing and custom components                  | [https://spacy.io/usage/processing-pipelines](https://spacy.io/usage/processing-pipelines?utm_source=chatgpt.com)       |
| Linguistic annotations, morphology, and tokenization       | [https://spacy.io/usage/linguistic-features](https://spacy.io/usage/linguistic-features?utm_source=chatgpt.com)         |
| Rule-based and structural matching                         | [https://spacy.io/usage/rule-based-matching](https://spacy.io/usage/rule-based-matching?utm_source=chatgpt.com)         |
| Trained models and compatibility                           | [https://spacy.io/models](https://spacy.io/models?utm_source=chatgpt.com)                                               |
| Neural architectures and shared representations            | [https://spacy.io/api/architectures](https://spacy.io/api/architectures?utm_source=chatgpt.com)                         |
| Transformer integration                                    | [https://spacy.io/usage/embeddings-transformers](https://spacy.io/usage/embeddings-transformers?utm_source=chatgpt.com) |
| Training, registry configuration, and model initialization | [https://spacy.io/usage/training](https://spacy.io/usage/training?utm_source=chatgpt.com)                               |
| Saving and loading pipelines/documents                     | [https://spacy.io/usage/saving-loading](https://spacy.io/usage/saving-loading?utm_source=chatgpt.com)                   |
| CLI, evaluation, benchmarking, and packaging               | [https://spacy.io/api/cli](https://spacy.io/api/cli?utm_source=chatgpt.com)                                             |
| NLP workflow orchestration                                 | [https://spacy.io/usage/projects](https://spacy.io/usage/projects?utm_source=chatgpt.com)                               |
| Memory management and memory zones                         | [https://spacy.io/usage/memory-management](https://spacy.io/usage/memory-management?utm_source=chatgpt.com)             |
| Core API and release history                               | [https://github.com/explosion/spaCy](https://github.com/explosion/spaCy?utm_source=chatgpt.com)                         |
| Stable package distribution                                | [https://pypi.org/project/spacy/](https://pypi.org/project/spacy/?utm_source=chatgpt.com)                               |
| Companion packages and extensions                          | [https://spacy.io/universe](https://spacy.io/universe?utm_source=chatgpt.com)                                           |

## 14. Overall capability perspective

spaCy is best understood as a structured NLP runtime, annotation model, and trainable pipeline framework, rather than merely a library of pretrained language models.

Its most important architectural capabilities are the combination of:

1. A compact, shared linguistic document representation.
2. Declarative token, phrase, dependency, and span matching.
3. Trainable extraction and classification with distinct output semantics.
4. Shared contextual representation models and transformer integration.
5. A configurable training system with registered architectures and functions.
6. Native serialization, evaluation, benchmarking, and packaging.
7. Extension mechanisms that allow domain-specific processing to participate in the same lifecycle.

Together, these capabilities make it possible to construct sophisticated hybrid NLP systems while reusing much of the infrastructure that would otherwise need to be implemented separately.

The most easily overlooked opportunities lie in treating candidate generation, span classification, entity normalization, shared neural representations, and structured document annotations as composable concerns. Conversely, the most important design risks arise when their boundaries are blurred—for example, treating non-overlapping NER as arbitrary span extraction, lexical similarity as semantic retrieval, or serialized configuration as a fully self-contained implementation.

Within those distinctions, spaCy 3.8 provides a mature and unusually broad foundation for structured language understanding and information extraction.

# Addendum to the spaCy 3.8 Comprehensive Python Library Overview

Advanced annotation semantics, structured extraction, linguistic rules, document interoperability, model extensibility, training infrastructure, and ecosystem integration

Research date: November 5, 2026\
Target release: spaCy 3.8.18\
Python compatibility: 3.10–3.15\
Scope: Supplement to the existing comprehensive overview of spaCy 3.8.16

This addendum documents advanced capabilities and consequential implementation distinctions not fully developed in the original reference. It is intended to be read alongside that document; established explanations of spaCy's core architecture, standard pipeline components, and primary inference mechanisms are not repeated.

The additions emphasize functionality that enables more expressive representations of linguistic knowledge, more sophisticated combinations of deterministic and learned processing, and greater reuse of spaCy's native infrastructure.

## 1. Release and compatibility update

As of November 5, 2026, the latest stable spaCy release is 3.8.18, published October 26, 2026. PyPI declares `Requires-Python: >=3.10,<3.16` and distributes CPython 3.15 wheels alongside wheels for Python 3.10–3.14.

This supersedes the original document's identification of 3.8.16 as the latest stable release and its introductory Python 3.9–3.14 compatibility statement. Python 3.9 is no longer supported by the current distribution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



The functionality documented below is available within the spaCy 3.8 series unless explicitly identified as experimental or belonging to a separately distributed package. The existence of spaCy 4.0 development releases does not make them part of the stable API contract.

Primary source: [https://pypi.org/project/spacy/](https://pypi.org/project/spacy/?utm_source=chatgpt.com)

## 2. Fine-grained entity annotation and supervision

### 2.1 Entity annotations express more than positive spans

spaCy's named entity representation includes distinctions between confirmed entities, confirmed non-entities, deliberately blocked entity predictions, and regions whose annotation is unknown.

The `Doc.set_ents()` method provides explicit controls over these states:

| Argument   | Semantics                                                                 |
| ---------- | ------------------------------------------------------------------------- |
| `entities` | Confirmed labeled entity spans                                            |
| `blocked`  | Regions that the built-in NER component should never treat as entities    |
| `missing`  | Regions for which entity annotation is unknown or unavailable             |
| `outside`  | Regions explicitly known to be outside named entities                     |
| `default`  | Determines the state assigned to tokens not covered by the supplied spans |

The `default` argument accepts `"blocked"`, `"missing"`, `"outside"`, or `"unmodified"`. Its default is `"outside"`.

This is significant because an annotation system must often distinguish the absence of evidence from evidence of absence. A document whose labels are only partially complete should not necessarily treat all unannotated tokens as negative examples.

For instance, a technical corpus may contain verified organization entities while the presence of other entity classes has never been assessed. Treating those unassessed regions as `missing` preserves a different supervision signal from labeling them `outside`.

The distinction also matters when combining multiple annotation providers. A rule-based system might establish certain entity boundaries confidently while leaving the remaining text unresolved.

Important limitation: `blocked` is specifically documented for spaCy's built-in NER component. Other pipeline components may disregard blocked spans. These states do not constitute a universal constraint or truth-maintenance system across all spaCy components.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



Primary source: [https://spacy.io/api/doc](https://spacy.io/api/doc?utm_source=chatgpt.com)

### 2.2 Explicit negative entity examples

The trainable `EntityRecognizer` exposes an additional supervision mechanism through its `incorrect_spans_key` configuration setting.

When configured, the component reads a named `SpanGroup` containing entity spans known to be incorrect. During training, the recognizer learns not to reproduce those exact annotations.

This differs from marking all unannotated tokens as negative. It allows supervision to target specific false-positive hypotheses, including boundaries or entity mentions that a previous recognizer proposed incorrectly.

The mechanism is useful in settings where an annotation process produces reliable corrections, but not necessarily exhaustive positive annotations across every document.

Its scope is narrower than arbitrary negative-label supervision: it discourages prediction of the specified incorrect spans, rather than proving that every overlapping, nested, or alternative entity hypothesis is false.

One consequence is that positive entity annotations, explicitly incorrect candidate spans, and unresolved text can coexist as distinct training information, subject to the recognizer's supported supervision semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



Primary source: [https://spacy.io/api/entityrecognizer](https://spacy.io/api/entityrecognizer?utm_source=chatgpt.com)

### 2.3 Annotation completeness and validation

`Doc.has_annotation()` provides a native way to determine whether a document contains a particular token annotation.

The `require_complete` option distinguishes two conditions:

- The document contains at least some annotation for the requested attribute.
- Every token has the requested annotation.

This distinction is useful when a downstream operation requires complete POS tagging, dependency annotation, or morphological information, rather than merely checking whether the relevant component ran.

For example, partial annotation can result from manual construction, imported corpora, or pipelines that selectively modify documents. Component presence alone does not establish annotation completeness.

`Doc.has_annotation()` is therefore a useful structural prerequisite check before invoking algorithms whose correctness depends on complete token attributes. It does not assess whether the annotations are linguistically correct.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



Primary source: [https://spacy.io/api/doc](https://spacy.io/api/doc?utm_source=chatgpt.com)

### 2.4 Tokenization-aware evaluation and the measurable entity universe

A particularly consequential limitation of spaCy's NER evaluation arises when gold-standard entity boundaries cannot be represented by the tokenizer used during prediction.

spaCy's training documentation explicitly notes that gold entities which cannot be aligned to predicted tokenization may be excluded from NER evaluation.

Consider an annotated dataset with 1,000 reference entities. Suppose the tokenizer makes 150 entity boundaries impossible to represent, leaving 850 alignable entities. An evaluation calculated over alignable entities alone can report a strong F-score even though the system could never recover the excluded 150.

The numbers are illustrative, but the underlying effect is documented.

This introduces two materially different evaluation questions:

1. How accurately does the model recognize entities whose boundaries its tokenizer can express?
2. How completely does the end-to-end system recover entities in the original annotated corpus?

The first measures conditional recognition quality; the second includes tokenization-related coverage losses.

A robust evaluation methodology should therefore retain the original reference-entity count, determine the fraction of reference spans representable under the predicted tokenization, and distinguish unalignable reference annotations from ordinary model false negatives.

An end-to-end measure can then count such coverage failures explicitly, rather than relying only on the built-in NER F-score.

This concern is particularly important for specialized terminology containing punctuation, identifiers, units, chemical nomenclature, abbreviations, or other constructions that may not conform to a general-purpose tokenizer.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation



Primary source: [https://spacy.io/usage/training](https://spacy.io/usage/training?utm_source=chatgpt.com)

## 3. Programmable span generation and multi-stage extraction

### 3.1 Span proposal is a configurable operation

The `SpanCategorizer` architecture separates candidate generation from the classification model. The original overview establishes this distinction, but the candidate-generation interface itself provides additional architectural flexibility.

The suggester is a registered function that receives a batch of `Doc` objects and an optional Thinc `Ops` instance. It returns a `Ragged` array containing candidate `(start, end)` token indices.

spaCy provides several native suggesters:

| Registered function                    | Candidate-generation behavior                                           |
| -------------------------------------- | ----------------------------------------------------------------------- |
| `spacy.ngram_suggester.v1`             | Generates spans of explicitly selected token lengths                    |
| `spacy.ngram_range_suggester.v1`       | Generates spans over an inclusive minimum-to-maximum token-length range |
| `spacy.preset_spans_suggester.v1`      | Reuses spans already stored under a specified `Doc.spans` key           |
| Custom `@spacy.registry.misc` function | Allows alternative, task-specific candidate-generation strategies       |

The distinction between the two n-gram suggesters is useful. One allows noncontiguous selections of span lengths, such as lengths 1, 2, and 5. The other generates every length in a continuous interval.

The preset-span suggester is more architecturally significant: candidate generation can be delegated to an upstream rule engine or learned span finder without requiring the span classifier itself to enumerate every possible text interval.

A custom registered suggester can similarly encode structural restrictions, combine proposals from different mechanisms, or exclude candidates known to be invalid. The resulting candidate-generation logic participates directly in spaCy's configuration-driven model architecture.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



Primary source: [https://spacy.io/api/spancategorizer](https://spacy.io/api/spancategorizer?utm_source=chatgpt.com)

### 3.2 Composition with rule-based and learned candidate producers

A useful capability combination is to distinguish candidate discovery, candidate classification, and final annotation acceptance.

For example, a `SpanRuler` can populate `Doc.spans["candidates"]` with terminology-based matches, including overlapping or nested spans. `SpanCategorizer` can subsequently consume that group using the preset-span suggester and produce learned classifications in a separate output group.

An illustrative configuration excerpt is:

```
[components.spancat.suggester]
@misc = "spacy.preset_spans_suggester.v1"
spans_key = "candidates"
```

The corresponding categorizer output can be configured with a different `spans_key`, such as `"classified"`.

This separation is essential because `SpanCategorizer` overwrites the span group identified by its own output key. Using the same key indiscriminately for candidate input and classified output may discard the original candidate set.

The design is especially useful when a system needs to preserve both raw candidates and accepted predictions for subsequent scoring, comparison, or reconciliation.

The component also exposes `SpanCategorizer.set_candidates(docs, candidates_key)`, which materializes the suggester's proposals into a selected span group. The API is specifically intended for debugging candidate-generation behavior.

Candidate inspection matters because classification quality is bounded by proposal recall. A classifier cannot recover a relevant span that its suggester never produces, regardless of how accurate the classification model might otherwise be.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation+2



Primary sources:

[https://spacy.io/api/spancategorizer](https://spacy.io/api/spancategorizer?utm_source=chatgpt.com)

[https://spacy.io/api/spanruler](https://spacy.io/api/spanruler?utm_source=chatgpt.com)

### 3.3 `SpanRuler` as a configurable candidate-reconciliation component

`SpanRuler` offers more control over preserving, merging, and filtering span annotations than its basic rule-matching role might suggest.

Its relevant configuration settings include:

| Setting                 | Function                                                                   |
| ----------------------- | -------------------------------------------------------------------------- |
| `spans_key`             | Selects the named span group receiving rule matches                        |
| `spans_filter`          | Applies custom filtering before writing to `Doc.spans`                     |
| `annotate_ents`         | Optionally writes a non-overlapping entity representation to `Doc.ents`    |
| `ents_filter`           | Controls which spans survive when producing entity annotations             |
| `overwrite`             | Controls replacement of preexisting annotations at configured destinations |
| `phrase_matcher_attr`   | Chooses the token attribute used for phrase matching                       |
| `matcher_fuzzy_compare` | Supplies the comparison function for fuzzy token-pattern matching          |

The default `spans_filter` is `None`, allowing overlapping spans to be retained. The default `ents_filter` is `util.filter_chain_spans`, because `Doc.ents` cannot represent arbitrary overlaps.

Thus, the same underlying pattern definitions can support two different data products: a broad overlapping candidate inventory and a filtered non-overlapping entity annotation.

Custom filters can implement different reconciliation policies for those destinations. These may use label priorities, existing annotations, span lengths, or other information available to the filtering function.

There is an important distinction between preserving spans and preserving all evidence about them. A `SpanGroup` can contain overlapping candidates, but spaCy does not automatically create a calibrated probabilistic model of their mutual compatibility. A custom filter may implement deterministic policy, while probabilistic reconciliation remains a separate task.

The component's output behavior also makes configuration important: `overwrite=True` is the default, and preexisting annotations can be removed from the configured destination.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



Primary source: [https://spacy.io/api/spanruler](https://spacy.io/api/spanruler?utm_source=chatgpt.com)

### 3.4 Training dependencies between candidate generation and classification

A pipeline that uses predicted upstream spans during inference should make the corresponding training dependencies explicit.

For example, a span classifier trained only with reference candidate spans may see materially different inputs at inference time if its actual candidate producer occasionally misses boundaries or proposes additional false positives.

spaCy's `training.annotating_components` mechanism, described in the original guide, can be used to generate selected upstream annotations during training. In combination with a preset-span suggester, this provides a way to train a downstream classifier with inputs closer to those it will encounter during inference.

The distinction is between optimizing classification on ideal reference candidates and optimizing classification on realistically generated candidates.

This does not eliminate the need for gold labels or guarantee that the resulting pipeline will improve. It provides a native mechanism for controlling a common source of train–inference mismatch.

Primary source: [https://spacy.io/usage/training](https://spacy.io/usage/training?utm_source=chatgpt.com)

## 4. Deterministic linguistic annotation and entity normalization

### 4.1 `AttributeRuler` supports contextual token annotation

The `AttributeRuler` is not limited to ordinary POS tag mapping. It is a reusable rule engine for assigning supported token attributes to selected tokens identified by `Matcher` patterns.

Its central method is:

```
AttributeRuler.add(patterns, attrs, index=0)
```

The `patterns` argument provides token-pattern conditions, `attrs` specifies the attributes to assign, and `index` identifies which token within a matched sequence receives those assignments.

The index may be negative, allowing selection relative to the end of a match.

This enables a useful form of contextual deterministic annotation. A multi-token pattern can recognize a construction while modifying only one token's lemma, POS, tag, or morphological attributes.

For example, a domain-specific abbreviation may have a grammatical interpretation that differs from its general-purpose use. A rule can recognize the relevant context and assign an appropriate analysis without changing the tokenizer or retraining an entire linguistic model.

`AttributeRuler.add_patterns()` additionally supports loading declarative collections of such rules, while `load_from_tag_map()` and `load_from_morph_rules()` adapt established linguistic mapping data into its rule representation.

The component supports initialization and serialization through spaCy's standard pipeline lifecycle.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation+1



The principal architectural benefit is that deterministic correction can be expressed through the same token-pattern vocabulary as other spaCy rule-based processing.

Its limitation is that the assignments mutate annotations rather than establish separate, competing analyses. If multiple rules or components write the same attribute, execution order and applicable rule behavior determine the final value. Alternative interpretations requiring preservation should be represented separately.

Primary source: [https://spacy.io/api/attributeruler](https://spacy.io/api/attributeruler?utm_source=chatgpt.com)

### 4.2 Rule-based canonical identifiers

`EntityRuler` patterns can contain an optional `id` field in addition to `label` and `pattern`.

When a pattern with an ID matches an entity, spaCy populates that entity's `ent_id` / `ent_id_` annotation.

Multiple distinct surface forms can share the same ID, allowing deterministic alias normalization.

For example, the following rules associate two surface forms with one identifier:

```
patterns = [    {        "label": "ORG",        "pattern": "Acme Corporation",        "id": "org:acme",    },    {        "label": "ORG",        "pattern": "Acme Corp.",        "id": "org:acme",    },]ruler.add_patterns(patterns)
```

Here, `ruler` represents an already configured `EntityRuler`. The example is illustrative and has not been executed.

This provides a direct path from terminology matching to canonical identifiers without requiring every recognized alias to pass through a learned entity linker.

spaCy exposes the known pattern IDs through `EntityRuler.ent_ids`. It also provides `EntityRuler.remove(id)` to remove patterns associated with a supplied identifier.

A crucial distinction is that `ent_id` and `kb_id` are separate annotations.

`ent_id` can represent an ID assigned by a deterministic matching rule. `kb_id` is the knowledge-base identifier used by the entity-linking interface. An application can choose to use compatible identifier schemes, but spaCy does not automatically equate their meanings or establish that a rule-assigned ID has been statistically disambiguated.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation+2



Primary sources:

[https://spacy.io/usage/rule-based-matching](https://spacy.io/usage/rule-based-matching?utm_source=chatgpt.com)

[https://spacy.io/api/entityruler](https://spacy.io/api/entityruler?utm_source=chatgpt.com)

[https://spacy.io/api/span](https://spacy.io/api/span?utm_source=chatgpt.com)

### 4.3 Entity linking has independently configurable evidence sources

The `EntityLinker` configuration exposes several controls that affect how a mention is resolved against a knowledge base.

| Configuration          | Consequential behavior                                              |
| ---------------------- | ------------------------------------------------------------------- |
| `incl_prior`           | Determines whether KB prior probabilities contribute to predictions |
| `incl_context`         | Determines whether local contextual information contributes         |
| `n_sents`              | Sets the number of neighboring sentences considered                 |
| `get_candidates`       | Supplies candidates for an individual entity mention                |
| `get_candidates_batch` | Supplies candidates through a batched interface                     |
| `labels_discard`       | Sends selected entity labels directly to `NIL`                      |
| `threshold`            | Rejects predictions below a specified confidence threshold          |
| `overwrite`            | Controls whether existing linking annotations may be replaced       |
| `use_gold_ents`        | Controls use of reference entities during training                  |

These controls make the linker more flexible than a fixed alias lookup followed by a single hardcoded classification policy.

For example, the model can incorporate knowledge-base priors, contextual evidence, or both. Candidate generation can be replaced independently of the prediction architecture, including through batch-oriented retrieval.

The `threshold` option, added in spaCy 3.4, permits predictions below a confidence cutoff to be rejected. If no candidate exceeds the threshold, the result is `NIL`.

`labels_discard` provides a different kind of exclusion: selected entity types can be assigned `NIL` without ordinary linking.

The defaults are meaningful. `incl_prior` and `incl_context` are both enabled, the default candidate generators use exact case-sensitive aliases, and `threshold=None` means confidence filtering is not applied.

Candidate generation, evidence selection, and acceptance thresholds therefore form separate architectural decisions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



The resulting flexibility does not imply that spaCy supplies a complete external knowledge-base management system. Candidate coverage, identity stability, vector quality, and knowledge-base maintenance remain consequential requirements.

Primary source: [https://spacy.io/api/entitylinker](https://spacy.io/api/entitylinker?utm_source=chatgpt.com)

## 5. Advanced syntactic queries and dependency-structure analysis

### 5.1 Native dependency-tree traversal

spaCy provides direct structural operations on the parsed dependency tree through `Token`, `Span`, and `Doc` interfaces. These can eliminate the need to construct a second graph representation merely to answer basic syntactic-relationship queries.

Important operations include:

| API                        | Structural information                                    |
| -------------------------- | --------------------------------------------------------- |
| `Token.children`           | Immediate syntactic dependents                            |
| `Token.ancestors`          | Successive syntactic heads                                |
| `Token.is_ancestor(other)` | Whether one token is an ancestor of another               |
| `Token.subtree`            | Token and all syntactic descendants                       |
| `Token.lefts` / `rights`   | Immediate dependents on either side                       |
| `Token.conjuncts`          | Tokens participating in coordination with the given token |
| `Span.root`                | Syntactic root of a span                                  |
| `Span.conjuncts`           | Tokens coordinated with the span's root                   |
| `Doc.get_lca_matrix()`     | Lowest common ancestors for token pairs                   |
| `Span.get_lca_matrix()`    | Lowest common ancestors within a selected span            |

These functions support several categories of analysis beyond basic dependency inspection.

Phrase expansion. An identified head token can serve as the starting point for exploring its syntactic dependents and reconstructing a larger linguistic expression.

Argument discovery. Given a verb, the dependency tree can be traversed to identify candidate subjects, objects, and associated modifiers.

Coordination expansion. `Token.conjuncts` can expose coordinated expressions that should be analyzed together. This can help avoid losing additional participants when several nouns or predicates are joined syntactically.

Structural proximity. Lowest-common-ancestor operations provide information about the point at which two tokens' dependency paths meet.

These operations are particularly useful in relation extraction, linguistic normalization, semantic-role approximations, and deterministic syntactic feature engineering.

A significant boundary is that the available tree reflects a syntactic parser's predictions. A shared syntactic ancestor does not itself establish a semantic relationship, causal connection, or valid knowledge-graph edge.

The lowest-common-ancestor matrix is also a dense pairwise representation. Its memory footprint grows quadratically with the number of tokens, so constructing it for long documents has different costs from traversing individual dependency paths.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation+2



Primary sources:

[https://spacy.io/api/token](https://spacy.io/api/token?utm_source=chatgpt.com)

[https://spacy.io/api/span](https://spacy.io/api/span?utm_source=chatgpt.com)

[https://spacy.io/api/doc](https://spacy.io/api/doc?utm_source=chatgpt.com)

### 5.2 Full structural expressiveness of `DependencyMatcher`

`DependencyMatcher` supports a broader set of structural relations than immediate parent-child matching.

Its operators express dependency ancestry, sibling relationships, and token-order relationships. Several representative families are:

| Operator  | Meaning                                                      |
| --------- | ------------------------------------------------------------ |
| `A > B`   | A is the immediate syntactic head of B                       |
| `A < B`   | A is the immediate dependent of B                            |
| `A >> B`  | A is an ancestor of B through a dependency chain             |
| `A << B`  | A is a descendant of B through a dependency chain            |
| `A . B`   | A immediately precedes B in token order within the same tree |
| `A .* B`  | A precedes B, not necessarily immediately                    |
| `A $+ B`  | B is an immediate right sibling of A                         |
| `A $++ B` | B is a right sibling of A, not necessarily immediately       |
| `A >+ B`  | A immediately precedes B and is B's parent                   |
| `A >++ B` | B occurs to the right of A and is a child of A               |

Complementary operators express following-token relationships, left siblings, and leftward parent-child relationships.

The operator set was extended in spaCy 3.5.1 with additional relationships combining dependency direction and immediate token ordering.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



These operators permit declarative patterns that would otherwise require procedural traversal and multiple nested conditions.

For example, a rule can constrain an action token to have a particular dependent while separately requiring a second matched token to have a specified ancestral relationship or relative position.

The essential distinction is between syntactic distance and surface-token distance. `>>` follows dependency ancestry, whereas `.*` expresses token-order precedence. Conflating them can produce materially different matches.

A `DependencyMatcher` pattern consists of an anchor node followed by named nodes with `LEFT_ID`, `REL_OP`, `RIGHT_ID`, and `RIGHT_ATTRS`. `RIGHT_ATTRS` uses the same general attribute-predicate language as the regular token matcher.

This makes it possible to combine structural relations with lexical, morphological, and other available token annotations.

Primary sources:

[https://spacy.io/api/dependencymatcher](https://spacy.io/api/dependencymatcher?utm_source=chatgpt.com)

[https://spacy.io/usage/rule-based-matching](https://spacy.io/usage/rule-based-matching?utm_source=chatgpt.com)

### 5.3 Experimental learned token merging in dependency parsing

The `DependencyParser` exposes a less commonly discussed option:

`learn_tokens=True`

This experimental setting allows the transition-based parser to learn merging of subtokens that were split relative to the gold-standard tokenization.

The mechanism addresses a specific mismatch between predicted and reference token segmentation. It is not a general replacement for tokenizer configuration or a universal learned tokenizer.

Its importance lies in the interaction between token boundaries and syntactic parsing: under certain conditions, the parser can participate in correcting token segmentation rather than treating every initial token boundary as immutable.

Because tokenization changes can affect offsets and previously constructed token-index annotations, the option should be understood as an experimental parsing-and-segmentation mechanism with downstream consequences.

The option defaults to `False`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



Primary source: [https://spacy.io/api/dependencyparser](https://spacy.io/api/dependencyparser?utm_source=chatgpt.com)

## 6. Document transformation and structured annotation interchange

### 6.1 Column-oriented numerical access through `Doc.to_array()`

`Doc.to_array()` exports selected token attributes as a NumPy array.

For a document containing \\(N\\) tokens and a request for \\(M\\) attributes, the method returns an \\(N \times M\\) array. Requesting a single attribute returns a one-dimensional array.

Attributes can be specified by their numeric spaCy IDs or their string names.

An illustrative example is:

```
import spacynlp = spacy.load("en_core_web_sm")doc = nlp("The researchers developed a new model.")attributes = ["ORTH", "LEMMA", "POS", "DEP", "HEAD"]array = doc.to_array(attributes)
```

The resulting array contains compact numeric attribute representations, rather than independently materialized Python objects for every property.

The corresponding `Doc.from_array()` method writes supported token attributes from a NumPy array into an existing document.

This permits native interoperability with numerical analysis and data-transformation systems. It is also useful when a downstream consumer only requires selected linguistic features rather than complete `Token` objects.

Important constraints:

- Lexical strings and many linguistic labels are represented through integer identifiers, which depend on spaCy's attribute and vocabulary machinery.
- Array export does not automatically include arbitrary custom extension objects or the complete semantic structure of a document.
- A document reconstructed from numeric attributes still requires valid token boundaries and compatible vocabulary information.
- `from_array()` mutates an existing `Doc`; it is not a complete document-deserialization facility.

A particularly important distinction is that numerical annotation interchange is different from directly obtaining neural representations. `Doc.to_array()` provides selected token attributes, not arbitrary transformer hidden states or embedding tensors.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



Primary source: [https://spacy.io/api/doc](https://spacy.io/api/doc?utm_source=chatgpt.com)

### 6.2 Individual-document binary and JSON serialization

In addition to the corpus-oriented `DocBin` format, spaCy supports serialization of individual documents.

| Operation                       | Representation and purpose                                         |
| ------------------------------- | ------------------------------------------------------------------ |
| `Doc.to_bytes()`                | Serializes an individual document to binary data                   |
| `Doc.from_bytes()`              | Restores a document from its binary representation                 |
| `Doc.to_disk()` / `from_disk()` | Persists and restores individual documents through directories     |
| `Doc.to_json()`                 | Exports a document as structured JSON-compatible data              |
| `Doc.from_json()`               | Reconstructs a document from the corresponding JSON representation |

`Doc.to_bytes()` supports lossless serialization of the document's native annotations, subject to any explicitly excluded fields. Unlike `DocBin`, it does not primarily target compact storage of large collections with shared serialization overhead.

`Doc.to_json()` serves a different purpose: it exports an inspectable structured representation suitable for interchange with systems that do not consume spaCy's binary format.

The `underscore` argument to `Doc.to_json()` allows selected custom document extension attributes to be included, provided their values are JSON-serializable.

This is opt-in rather than automatic export of every custom extension. A consumer must also distinguish the resulting JSON structure from spaCy's deprecated legacy JSON training format.

`Doc.from_json()` was added in spaCy 3.3.1 and supports an optional `validate` setting for checking the input against the expected schema.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation+1



These mechanisms make spaCy suitable for several different interchange requirements without forcing all annotated documents into a single persistence format.

Primary source: [https://spacy.io/api/doc](https://spacy.io/api/doc?utm_source=chatgpt.com)

### 6.3 Creating documents from spans and concatenating documents

Two document-transformation APIs provide complementary operations.

`Span.as_doc()` creates a new, independently owned `Doc` containing the span's content and copied annotation data.

It can optionally copy the original document's user data. When extracting many spans from the same document, precomputed array representations can be supplied to reduce repeated preparation work.

This is useful when a selected passage must subsequently be processed as an independent document.

However, the newly created `Doc` is not an automatically maintained view of the original document. Its token indices are local to the extracted text, and annotations whose meaning depends on surrounding context may require reinterpretation.

`Doc.from_docs()` performs the reverse operation: concatenating a sequence of documents into a new `Doc`.

The source documents must share the same `Vocab`. The method provides options for controlling copied attributes and excluding fields such as spans, tensor data, and user data.

Its `ensure_whitespace` option can insert whitespace between source documents where necessary.

This is particularly consequential for offset preservation. Concatenating separately processed documents can produce a representation whose character offsets differ from offsets in the original source system.

The two operations therefore support document segmentation and recomposition, but they do not provide automatic preservation of every cross-document relationship, source offset, or provenance link.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation+1



Primary sources:

[https://spacy.io/api/span](https://spacy.io/api/span?utm_source=chatgpt.com)

[https://spacy.io/api/doc](https://spacy.io/api/doc?utm_source=chatgpt.com)

## 7. Custom trainable components and model lifecycle integration

### 7.1 `TrainablePipe` is the interface between prediction models and spaCy's training system

spaCy's extensibility extends beyond custom inference components and registered Thinc architectures.

`TrainablePipe` defines the contract through which a custom statistical or neural prediction task participates in the pipeline's training lifecycle.

This separates three architectural responsibilities:

| Responsibility                                       | Relevant mechanism       |
| ---------------------------------------------------- | ------------------------ |
| Construction and configuration                       | `@Language.factory`      |
| Neural computation and differentiation               | Thinc `Model`            |
| Task-specific inference, supervision, and annotation | `TrainablePipe` subclass |

A custom trainable component can therefore replace the prediction task while continuing to use spaCy's training, optimization, evaluation, and packaging machinery.

Important methods include:

| Method               | Role                                                            |
| -------------------- | --------------------------------------------------------------- |
| `initialize()`       | Initialize the component and model using training examples      |
| `predict()`          | Produce scores from a batch of documents without modifying them |
| `set_annotations()`  | Write predictions into the corresponding documents              |
| `get_loss()`         | Calculate task-specific loss and gradients                      |
| `update()`           | Perform supervised model updates                                |
| `score()`            | Evaluate the component against reference examples               |
| `create_optimizer()` | Construct an optimizer for parameter updates                    |
| `finish_update()`    | Apply the optimizer to current gradients                        |
| `use_params()`       | Temporarily substitute model parameters                         |

The basic custom-component implementation requires a model, a `TrainablePipe` subclass implementing the prediction and annotation interfaces, and a registered factory. A fully trainable task must additionally supply suitable supervision and loss behavior.

The distinction between `predict()` and `set_annotations()` is particularly useful. It separates score production from mutation of spaCy's document model, allowing inference, training, and evaluation to invoke the appropriate operations.

A custom component can consequently produce conventional spaCy annotations, custom extension attributes, or other supported document-level outputs without rewriting the entire NLP execution system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation+2



Primary sources:

[https://spacy.io/api/pipe](https://spacy.io/api/pipe?utm_source=chatgpt.com)

[https://spacy.io/usage/processing-pipelines](https://spacy.io/usage/processing-pipelines?utm_source=chatgpt.com)

### 7.2 Dependency injection of neural architectures

spaCy's custom trainable-component guidance explicitly recommends that component factories accept a constructed Thinc model rather than instantiate the neural architecture internally.

The configuration system resolves nested registered functions and architectures before passing the model to the component.

This means the prediction task and its neural implementation can evolve independently.

A custom task could, in principle, use a lightweight lexical encoder, a shared contextual representation, or a wrapped external neural architecture while retaining the same document-level annotation semantics.

The important benefit is not that every architecture can be substituted without modification. Model input/output contracts, backpropagation behavior, and supervision requirements still need to agree.

Rather, spaCy supplies a native separation between task logic, model construction, parameter initialization, and configuration.

This can significantly reduce custom training infrastructure when the desired prediction task can be represented through spaCy's document and example abstractions.

Primary source: [https://spacy.io/usage/processing-pipelines](https://spacy.io/usage/processing-pipelines?utm_source=chatgpt.com)

### 7.3 Experimental model rehearsal

`TrainablePipe.rehearse()` is an experimental method intended to reduce catastrophic forgetting during model updates.

Rehearsal updates teach the current model to produce predictions resembling those of an earlier model. The objective is to preserve previously learned behavior while the model is being adapted.

This is conceptually distinct from ordinary supervised training:

- Supervised updates optimize predictions against annotated reference data.
- Rehearsal updates attempt to preserve agreement with a previous model's behavior.

Rehearsal therefore provides an interface for knowledge-preservation strategies during continued training.

Its effectiveness and exact behavior depend on the particular component and implementation. The existence of the base method does not guarantee that arbitrary custom trainable components automatically provide a complete rehearsal algorithm.

The capability is explicitly marked experimental and should not be treated as a stable, universally applicable continual-learning solution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



Primary source: [https://spacy.io/api/pipe](https://spacy.io/api/pipe?utm_source=chatgpt.com)

## 8. Advanced training-data management and runtime operations

### 8.1 `Corpus` as an extensible training-data interface

spaCy's `Corpus` class manages collections of annotated documents and produces `Example` objects for training and evaluation.

The registered `spacy.Corpus.v1` reader supports `.spacy` files and directories, while the `@readers` registry allows alternative data sources and streaming behavior.

Its options include:

| Setting        | Effect                                                                |
| -------------- | --------------------------------------------------------------------- |
| `path`         | Source of annotated `.spacy` documents                                |
| `gold_preproc` | Constructs examples using reference token and sentence boundaries     |
| `max_length`   | Limits document length, with sentence-based splitting where available |
| `limit`        | Restricts the number of examples                                      |
| `augmenter`    | Transforms examples during corpus iteration                           |
| `shuffle`      | Controls example ordering                                             |

The `gold_preproc` setting is especially consequential.

It allows predicted documents to be prepared using gold-standard segmentation, improving alignment and sometimes producing more consistent training sequences.

However, spaCy explicitly warns that gold preprocessing can reduce runtime accuracy through train–test mismatch. A model trained or evaluated with reference segmentation may behave differently when the actual tokenizer and sentence segmenter must operate without that privileged information.

The broader implication is that corpus readers are part of the model's effective data contract. Changing token preparation, segmentation, augmentation, or sampling can materially alter the learning problem without changing the model architecture itself.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation+1



spaCy also provides `JsonlCorpus` for reading newline-delimited raw-text datasets, notably for its pretraining workflows. This is distinct from the annotated `.spacy` corpus reader.

Primary source: [https://spacy.io/api/corpus](https://spacy.io/api/corpus?utm_source=chatgpt.com)

### 8.2 Registered data augmentation

The training system supports augmentation through registered callbacks operating on `Example` objects.

The built-in `spacy.orth_variants.v1` augmenter can substitute orthographic variants, including punctuation and capitalization variations. Its configuration can reference dictionaries containing single-token and paired-token replacement rules.

Custom augmentation functions can be registered through spaCy's augmenter registry.

An augmentation callback receives the current language pipeline and an example, and yields one or more examples.

This makes augmentation part of the training-data pipeline rather than a necessarily separate preprocessing stage.

A significant detail is that the callback must yield every example that should appear in the resulting training stream. If the original example must remain available alongside augmented variants, the callback needs to yield the original explicitly.

Another important constraint concerns annotation consistency.

Changing token text without modifying token boundaries can be relatively straightforward. Adding or removing tokens may invalidate entity boundaries, dependency relations, and other annotations. In those cases, the corresponding reference `Example` must be reconstructed or adjusted appropriately.

Thus, augmentation needs to preserve the semantic relationship between the transformed text and the training labels, not merely produce plausible new text.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation



Primary source: [https://spacy.io/usage/training](https://spacy.io/usage/training?utm_source=chatgpt.com)

### 8.3 Pipeline error handling

spaCy provides configurable error-handling hooks for processing failures.

`Language.set_error_handler()` applies a callback to pipeline components supporting the corresponding error-handler interface. Trainable components expose `set_error_handler()` and `get_error_handler()` directly.

The callback receives information about the failing component, the affected documents, and the original exception.

This allows custom behavior such as diagnostic recording, error classification, or controlled continuation when a batch encounters an exception.

The default trainable-component error handler reraises the exception.

The scope of the mechanism is important. It is a pipeline-processing exception hook, not a complete transactional execution or recovery framework. A component may already have modified some documents before an error occurs. Installing a handler does not automatically roll back those modifications, retry safely, or guarantee exactly-once processing.

Custom recovery policies must therefore account for possible partial effects and the semantics of the affected batch.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation+1



Primary sources:

[https://spacy.io/api/language](https://spacy.io/api/language?utm_source=chatgpt.com)

[https://spacy.io/api/pipe](https://spacy.io/api/pipe?utm_source=chatgpt.com)

### 8.4 Experiment tracking through `spacy-loggers`

The `spacy-loggers` package supplies independently maintained logging integrations for spaCy's training system.

It includes integrations for Weights & Biases, MLflow, ClearML, PyTorch, and CuPy, together with utilities for composing multiple loggers.

These integrations use spaCy's registered logger configuration rather than requiring training-loop instrumentation to be implemented independently.

For example, `spacy.WandbLogger.v5` can publish training metrics, configuration information, system diagnostics, and selected model artifacts to Weights & Biases.

The package's `ChainLogger` can combine logging behaviors, allowing console reporting and external experiment tracking to coexist.

A relevant operational distinction is that the package is separately versioned even though it is normally installed alongside modern spaCy distributions. External logging providers may still require their own packages, credentials, and configuration.

External experiment tracking also creates a data-disclosure boundary. The W&B integration documents that configuration information and system details may be transmitted to the external service, and it supports exclusion of selected configuration values.

This is important when training configurations contain sensitive paths, infrastructure details, or information that should not be included in external experiment records.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Primary source: [https://github.com/explosion/spacy-loggers](https://github.com/explosion/spacy-loggers?utm_source=chatgpt.com)

## 9. Extensible vector storage and representation backends

### 9.1 `BaseVectors`: custom lexical-vector implementations

spaCy 3.7 introduced the `BaseVectors` abstraction, allowing developers to implement alternative vector-storage and retrieval mechanisms.

This extends spaCy's vocabulary-vector architecture beyond its built-in dense vector tables and floret representations.

`BaseVectors` defines an interface for accessing vectors through lexical keys while permitting custom implementations to control how those vectors are generated, stored, batched, and serialized.

Important extension points include:

| Method                        | Responsibility                                                          |
| ----------------------------- | ----------------------------------------------------------------------- |
| `__getitem__()`               | Retrieve a vector using an integer or string key                        |
| `get_batch()`                 | Retrieve vectors for multiple keys efficiently                          |
| `to_ops()`                    | Transfer or adapt vector storage to a selected Thinc operations backend |
| `to_disk()` / `from_disk()`   | Implement persistent vector serialization                               |
| `to_bytes()` / `from_bytes()` | Implement binary vector serialization                                   |

The official documentation identifies BPEmb subword embeddings as an example of a custom implementation.

The architectural opportunity is that a vocabulary's vector representation need not be limited to a conventional mapping from complete words to stored dense vectors.

A custom backend might construct representations from subword units, use alternative storage arrangements, or implement specialized lookup behavior, provided it satisfies the required interface.

The `get_batch()` method is especially important: spaCy requires it for training models using the `StaticVectors` architecture. A custom implementation that only provides individual vector access is therefore insufficient for that training use case.

Similarly, `to_ops()` matters when vector operations need to use a different Thinc computational backend.

Serialization is another explicit responsibility. The abstract interface provides methods for persistence, but a custom backend must implement the necessary behavior for its data to survive pipeline saving and loading.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



Primary source: [https://spacy.io/api/basevectors](https://spacy.io/api/basevectors?utm_source=chatgpt.com)

### 9.2 Relationship to model architecture and embedding systems

Custom vector storage and custom contextual representation models solve different problems.

`BaseVectors` changes how lexical vectors are supplied to spaCy's vocabulary and compatible model layers.

A Thinc architecture or transformer integration changes how representations are computed and combined during neural inference.

The distinction permits several implementation combinations. A custom lexical-vector backend can supply inputs to a neural encoder, while a contextual model transforms token representations using surrounding text.

However, replacing a vector backend does not automatically make its outputs suitable for semantic retrieval, nor does it establish that the representation is compatible with arbitrary downstream model architectures.

The integration contract must account for vector dimensions, expected key semantics, batching, numerical types, device operations, and persistence.

This separation makes custom vector storage a useful lower-level extension point without conflating lexical lookup with contextual encoding or retrieval-oriented embedding generation.

### 9.3 Importing external word vectors

The CLI provides `spacy init vectors`, which converts supported external word-vector files into a spaCy-compatible representation.

The command supports text-based Word2Vec-style vector tables, including supported compressed text archives.

It generates a spaCy pipeline artifact that can subsequently be referenced during model initialization.

This is distinct from implementing `BaseVectors`. `spacy init vectors` imports an existing vector resource into spaCy's standard vector infrastructure, whereas `BaseVectors` permits the underlying vector implementation itself to be customized.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy API Documentation



Primary source: [https://spacy.io/api/cli](https://spacy.io/api/cli?utm_source=chatgpt.com)

## 10. Additional tooling and ecosystem interoperability

### 10.1 Registry introspection with `spacy find-function`

spaCy 3.7 introduced the `find-function` CLI command.

It locates the source module, file path, and line number associated with a registered function.

For example, configuration files may refer to model architectures, data readers, training callbacks, and other components through registry identifiers rather than direct Python imports.

`spacy find-function` helps determine which concrete implementation corresponds to such a configuration entry.

This is useful for understanding externally supplied pipelines, investigating configuration behavior, diagnosing dependency interactions, and inspecting implementations provided by installed companion packages.

Unlike ordinary Python symbol lookup, the command is specifically designed around spaCy's registry-based configuration system.

Primary source: [https://spacy.io/api/cli](https://spacy.io/api/cli?utm_source=chatgpt.com)

### 10.2 Hugging Face Hub pipeline distribution

The separately distributed `spacy-huggingface-hub` package adds Hugging Face Hub publishing capabilities to spaCy's CLI.

The integration accepts a trained spaCy pipeline packaged as a wheel and publishes the corresponding package, metadata, and documentation to the Hub.

A representative command is:

```
python -m spacy huggingface-hub push model.whl
```

This command requires the companion package and a previously built pipeline wheel.

The package can also be used programmatically through its `push()` function.

This extends spaCy's native pipeline-packaging functionality with an external model-distribution mechanism. The distinction matters because packaging a pipeline and publishing it to a remotely hosted model registry are separate operations.

The integration does not eliminate the need for compatible spaCy versions, custom component implementations, or other dependencies required to load the packaged pipeline.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Primary sources:

[https://github.com/explosion/spacy-huggingface-hub](https://github.com/explosion/spacy-huggingface-hub?utm_source=chatgpt.com)

[https://spacy.io/api/cli](https://spacy.io/api/cli?utm_source=chatgpt.com)

### 10.3 Stanza model interoperability through `spacy-stanza`

The `spacy-stanza` companion package wraps Stanford's Stanza NLP framework and exposes its linguistic annotations through spaCy's `Doc` interface.

The integration can provide:

- Statistical tokenization.
- Sentence segmentation.
- Fine-grained and coarse-grained POS tags.
- Morphological annotations.
- Lemmatization.
- Dependency parsing.
- Named entity recognition, where supported by the selected Stanza model.

A critical distinction is that the linguistic predictions originate from Stanza, not from spaCy's own trained models.

`spacy-stanza` adapts the resulting annotations into spaCy-compatible document structures, making them accessible to downstream components that consume `Token`, `Span`, and `Doc` attributes.

The integration consequently provides an alternative source of linguistic analysis while preserving much of spaCy's processing interface.

This can be valuable when a Stanza model offers suitable linguistic coverage or annotation behavior for a particular language or domain.

There are still important boundaries.

Stanza's tokenization and pipeline structure may differ from those of native spaCy models. Downstream components must be compatible with the annotations and token boundaries produced by the wrapper.

The package also has its own release and dependency compatibility requirements. Support for a particular Python or spaCy version should be established from the companion package rather than inferred from spaCy core.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Universe+1



Primary sources:

[https://github.com/explosion/spacy-stanza](https://github.com/explosion/spacy-stanza?utm_source=chatgpt.com)

[https://spacy.io/universe/project/spacy-stanza](https://spacy.io/universe/project/spacy-stanza?utm_source=chatgpt.com)

### 10.4 Experimental components and spaCy 3.8 compatibility

`spacy-experimental` remains relevant to functionality such as experimental coreference resolution, span resolution, and trainable character-level tokenization.

However, these capabilities must not be presented as automatically available in a standard spaCy 3.8 installation.

The published upstream package configuration for `spacy-experimental` 0.6.4 declares:

```
spacy>=3.3.0,<3.8.0
```

This is incompatible with spaCy 3.8.18 under ordinary dependency resolution.

Consequently, the package's experimental components should be classified as version-constrained ecosystem capabilities, not supported spaCy 3.8 core features.

The dependency constraint also prevents assuming that the documented experimental coreference and tokenization interfaces are directly usable with the current stable release.

A compatible future release, fork, or separately validated adaptation could change that assessment. The upstream package metadata, rather than the presence of API documentation alone, determines the published compatibility boundary.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Primary source: [https://github.com/explosion/spacy-experimental](https://github.com/explosion/spacy-experimental?utm_source=chatgpt.com)

## 11. Installation-dependent functionality and compatibility boundaries

spaCy exposes optional dependencies that determine which companion functionality and hardware integrations are available.

For the 3.8 series, relevant installation extras include:

| Extra                             | Added capability or dependency                                                  |
| --------------------------------- | ------------------------------------------------------------------------------- |
| `lookups`                         | Linguistic lookup data for applicable normalization and lemmatization workflows |
| `transformers`                    | Integration with the separately distributed `spacy-transformers` package        |
| `cuda` and CUDA-specific variants | GPU support through compatible CuPy installations                               |
| `apple`                           | Apple-specific Thinc operations acceleration                                    |
| `ja`                              | Additional Japanese tokenization dependencies                                   |
| `ko`                              | Additional Korean tokenization dependencies                                     |
| `th`                              | Additional Thai tokenization dependencies                                       |

The current distribution also advertises CUDA-specific extras such as `cuda11x` and `cuda12x`, alongside more specific CUDA version selectors.

These extras are not all equivalent kinds of dependency.

Language-specific extras provide functionality required for particular tokenization implementations. Lookup data supports specific linguistic components. GPU extras change available numerical execution backends. Transformer extras introduce additional model integration infrastructure.

A critical distinction is that support for a Python interpreter version in spaCy core does not guarantee compatibility across its ecosystem.

A Python 3.15 installation of spaCy 3.8.18, for example, does not by itself establish that every optional companion package, trained model, or GPU dependency supports the same interpreter and platform combination.

Likewise, installing an optional dependency does not automatically add a trained prediction component to every pipeline.

The actual functionality of a pipeline depends jointly on core spaCy, installed companion packages, configured factories, model packages, and underlying numerical dependencies.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://spacy.io\&sz=32)

spaCy Usage Documentation+1



Primary sources:

[https://spacy.io/usage](https://spacy.io/usage?utm_source=chatgpt.com)

[https://pypi.org/project/spacy/](https://pypi.org/project/spacy/?utm_source=chatgpt.com)

## 12. Cross-cutting architectural implications

The capabilities documented in this addendum expose several additional distinctions that are particularly relevant to the design of sophisticated NLP systems.

### 12.1 Annotations can represent different epistemic states

spaCy distinguishes known entity annotations, explicitly incorrect candidates, missing information, and rule-produced or statistically predicted outputs.

These representations are not interchangeable.

A confirmed entity, an unverified candidate, a known false positive, and a missing annotation carry different information.

Preserving those distinctions can support richer downstream processing than reducing every extraction to a single accepted label.

However, spaCy does not automatically supply a general uncertainty calculus, probabilistic evidence-fusion model, or truth-maintenance engine over those annotations.

The library provides expressive representations and component interfaces from which such systems may be constructed.

### 12.2 Candidate generation can be shared across multiple prediction mechanisms

`SpanRuler`, `SpanFinder`, custom suggesters, and `SpanCategorizer` can participate in architectures that preserve candidate discovery as a distinct operation.

This provides an important opportunity for reducing duplicated extraction logic.

For example, a shared candidate inventory might be examined by several classifiers, normalized through deterministic rules, or evaluated under different acceptance policies.

The gain arises from preserving common span identities and boundaries, not merely placing more components into one pipeline.

A candidate should remain traceable to its source and the scoring or filtering operations that subsequently processed it. spaCy permits custom annotations and named span groups that can support such tracking, but the application must define the corresponding provenance conventions.

### 12.3 Linguistic annotations can support structural analysis without immediate graph conversion

Token-level dependency relationships, syntactic traversal, dependency matching, and lowest-common-ancestor operations collectively permit many linguistic analyses to remain within spaCy's native representation.

This can simplify systems whose immediate objective is to identify grammatical relationships or generate structurally constrained candidates.

External graph representations become more important when the objective requires arbitrary non-tree relationships, persistent entity identity across documents, graph algorithms, or complex knowledge-graph reasoning.

The distinction is between processing a sentence's syntactic dependency tree and maintaining a broader semantic graph of entities and relationships.

### 12.4 Annotation transformation is not equivalent to provenance preservation

`Doc.to_array()`, individual document serialization, `Span.as_doc()`, and `Doc.from_docs()` support useful representation transformations.

Nevertheless, these operations have different preservation guarantees.

A copied span becomes a new document. A concatenation can alter whitespace and offsets. Numerical attribute arrays omit parts of the richer document model. JSON export requires deliberate handling of custom extension values.

Systems requiring exact document provenance, original-source offsets, or stable identity across transformations therefore need to maintain those relationships explicitly.

### 12.5 Native training integration can extend beyond spaCy's predefined tasks

`TrainablePipe`, registered architectures, custom corpora, augmenters, scorers, and external logging integrations collectively provide a reusable training environment.

The resulting opportunity is broader than customizing an existing NER or classification model.

A new prediction task can potentially reuse spaCy's document lifecycle, configuration framework, training orchestration, and model distribution while defining its own outputs and supervision.

The corresponding cost is adherence to spaCy's model and annotation contracts. A task whose natural representation is fundamentally incompatible with those contracts may be better implemented outside the framework or through a specialized integration.

### 12.6 Evaluation must account for the entire prediction chain

The combination of tokenizer-dependent entity coverage, upstream span proposal, downstream classification, and optional entity linking creates several potential sources of end-to-end error.

A useful evaluation can distinguish failures in:

- Representing reference boundaries under the selected tokenization.
- Proposing relevant candidate spans.
- Assigning correct categories to proposed candidates.
- Mapping recognized mentions to the correct identifiers.
- Accepting or rejecting predictions under the configured threshold and filtering policy.

Component-level metrics remain useful, but they do not automatically establish complete system-level extraction quality.

spaCy provides many of the underlying annotation and scoring interfaces needed to examine these stages. The meaning and completeness of a broader evaluation remain dependent on the task definition and reference data.

## Concluding capability perspective

This addendum expands the original spaCy reference in several directions that are consequential for advanced engineering work.

The newly detailed capabilities show that spaCy provides more than a common interface to NLP models. Its underlying representation and extension mechanisms support partially known annotations, explicit negative supervision, programmable candidate discovery, syntactic tree queries, deterministic normalization, custom trainable prediction tasks, alternative vector backends, and several forms of structured interchange.

The most significant architectural distinction is the separation of concerns within a shared processing environment: annotation storage, candidate generation, linguistic analysis, supervised prediction, entity resolution, and training-data management can be independently configured while retaining common document and pipeline interfaces.

That separation allows functionality to be composed without requiring every component to implement its own tokenization, annotation storage, execution orchestration, and training lifecycle.

The boundaries are equally important. spaCy does not automatically provide general probabilistic reasoning, arbitrary semantic graphs, guaranteed preservation of external provenance, or compatibility among every separately distributed model and extension.

Within those boundaries, the additional capabilities documented here substantially extend the expressive and architectural range of the spaCy 3.8 framework without changing the core conceptual model established in the original guide.