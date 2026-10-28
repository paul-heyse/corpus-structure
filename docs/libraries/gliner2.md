# GLiNER2.5 — Comprehensive Python Library and Model Capability Reference

Research date: October 20, 2026 | Model family: GLiNER2.5 | Python package: `gliner2` 2.1.0 | License: Apache 2.0

## 1. Overview and architectural orientation

GLiNER2.5 is a schema-conditioned, encoder-based information extraction system that unifies named entity recognition, text classification, structured record extraction, relation extraction, and entity-level attribute prediction within a single neural model.

Developed by Fastino AI, GLiNER2.5 was released on August 24, 2026. It replaces the earlier fixed-width span-scoring architecture with a sparse boundary-prediction architecture, enabling longer entities, more flexible extraction, and additional constrained decoding capabilities.

Unlike generative language models that produce structured outputs by autoregressively generating tokens, GLiNER2.5 uses a bidirectional transformer encoder to evaluate text against a supplied schema and decode predictions into structured Python objects.

Its distinguishing feature is not simply zero-shot entity recognition. It is the ability to execute multiple schema-defined information extraction and classification tasks through a common inference interface, with specialized decoders that enforce relationships and constraints across predictions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+2



### Version scope

The latest published Python package verified for this reference is `gliner2` 2.1.0, released October 9, 2026. This follows package version 2.0.0, which introduced GLiNER2.5 on August 24, 2026.

Package 2.1.0 does not replace the GLiNER2.5 model weights. It improves the execution infrastructure, including attention acceleration, inference APIs, schema handling, training correctness, and packaging. This reference therefore covers the GLiNER2.5 checkpoints using capabilities supported by the 2.1.0 package, rather than documenting legacy GLiNER2 checkpoints.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



### Available GLiNER2.5 checkpoints

| Checkpoint                                                                                       | Parameters | Encoder                      | Primary role                               |
| ------------------------------------------------------------------------------------------------ | ---------- | ---------------------------- | ------------------------------------------ |
| [`gliner2.5-small-v1`](https://huggingface.co/fastino/gliner2.5-small-v1?utm_source=chatgpt.com) | 74M        | DeBERTa-v3-xsmall            | Low-resource, CPU and edge inference       |
| [`gliner2.5-base-v1`](https://huggingface.co/fastino/gliner2.5-base-v1?utm_source=chatgpt.com)   | 194M       | DeBERTa-v3-base              | General-purpose English extraction         |
| [`gliner2.5-multi-v1`](https://huggingface.co/fastino/gliner2.5-multi-v1?utm_source=chatgpt.com) | 287M       | Multilingual DeBERTa-v3-base | Multilingual extraction and classification |

All three use the `boundary` architecture and share the same core Python extraction interface. The multilingual checkpoint is not simply an English model with additional labels; it uses a multilingual encoder and was trained for cross-language capability.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



### Capability map

| Capability                      | Native mechanism                                                 | Principal APIs                             |
| ------------------------------- | ---------------------------------------------------------------- | ------------------------------------------ |
| Open-schema NER                 | Query-conditioned start/end boundary scoring                     | `extract_entities`, `entities`             |
| Text classification             | Single-label and multi-label query scoring                       | `classify_text`, `classification`          |
| Structured extraction           | Schema-defined fields and grouped records                        | `extract_json`, `structure`, `field`       |
| Relation extraction             | Directed, labeled relationships between text mentions            | `extract_relations`, `relations`           |
| Entity attributes               | Span-specific classification attached to detected mentions       | `AttributeGroup`, `entity_attributes`      |
| Constraint-aware classification | Jointly decoded label assignments satisfying declared rules      | `Classifier`, `ClassificationSchema`       |
| Graph-consistent extraction     | Joint entity/relation selection with graph constraints           | `JointIE`, `JointSchema`                   |
| Long-document processing        | Overlapping chunk inference, offset remapping and deduplication  | `extract_long`, `extract_entities_long`    |
| Efficient execution             | Native batching, sparse candidate proposals, optimized attention | `batch_extract_*`, attention backends      |
| Model specialization            | Supervised training and parameter-efficient adapters             | `ExtractorTrainer`, `TrainingConfig`, LoRA |

The most consequential capabilities to understand in depth are the boundary architecture, the schema abstraction, constrained joint decoding, long-document extraction, and the execution mechanisms that allow these features to be combined without creating separate model pipelines.

## 2. Architecture: query-conditioned boundary extraction

### 2.1 The shared encoder and task-specific heads

GLiNER2.5's inference architecture can be understood as three cooperating layers:

1. Schema-conditioned encoding. A DeBERTa-family encoder processes the input text together with learned representations of the requested labels, descriptions, and extraction queries. The schema changes what the model looks for without requiring a new trained model for each vocabulary of labels.
2. Task-specific scoring. Classification heads score document-level labels, boundary heads locate textual mentions, record heads associate extracted fields, and relation heads score connections between mentions.
3. Decoding and postprocessing. Candidate scores are converted into entities, records, classifications, attributes, or graph structures. This stage is also where overlap policies, thresholds, cardinality requirements, and hard constraints affect the returned result.

The common encoder means multiple extraction tasks can share the expensive contextual representation of a document. The output heads and decoders are not, however, interchangeable: independently scoring several labels is fundamentally different from finding a globally consistent solution to a set of constraints.

### 2.2 Sparse boundary proposals instead of dense span enumeration

The architectural change introduced by 2.5 is the replacement of fixed-width span enumeration with start/end boundary prediction.

For each requested extraction query, the boundary head computes scores over possible beginning and ending positions, together with evidence for tokens inside a candidate mention. It then selects promising boundaries, forms a bounded set of start–end pairs, and reranks those candidates.

The key consequences are:

| Property                       | GLiNER2.5 behavior                                                             |
| ------------------------------ | ------------------------------------------------------------------------------ |
| Maximum mention length         | No separate fixed-width cap; a mention may span the current encoded window     |
| Candidate formation            | Sparse proposals from high-scoring start/end positions                         |
| Candidate ranking              | Boundary compatibility, content evidence, and pair reranking                   |
| Scaling of the extraction head | Approximately linear in text length for a fixed schema and candidate budget    |
| Candidate coverage             | Not exhaustive: top-k proposals and candidate budgets can omit a valid mention |
| Context limit                  | Still bounded by the model's encoded input window                              |

The phrase span-free refers to avoiding the dense enumeration of candidate spans, not to the absence of span predictions. The model still produces explicit textual spans and uses pairwise evidence when scoring them.

Similarly, the reported linear scaling refers to the boundary extraction machinery under fixed budgets. It does not mean the entire transformer encoder has linear-time attention. DeBERTa attention remains a substantial component of execution cost, especially on long inputs.

Relevant source: [Fastino's GLiNER2.5 architecture explanation](https://fastino.ai/blog/gliner2-5-span-free-information-extraction?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://fastino.ai\&sz=32)

fastino.ai



### 2.3 Candidate budgets and the recall–cost tradeoff

The boundary implementation exposes configuration concepts including `start_top_k`, `end_top_k`, `ends_per_start`, `starts_per_end`, and `candidate_budget`.

These controls are architecturally important because the model can represent long spans without enumerating every possible pair of boundaries. There is therefore a separation between representational reach and search coverage.

A valid start or end that falls outside the shortlisted proposals cannot be recovered by the downstream reranker. Increasing proposal budgets expands the search space but also increases pair-scoring and decoding work. Decreasing them can improve latency at the expense of recall, particularly for ambiguous or densely populated documents.

There is also a distinct output-overlap decision. A model may score nested or overlapping mentions but subsequently suppress them under a flat-entity policy. This is not the same thing as a failure of the encoder to identify them.

The relevant implementation surfaces are [boundary configuration](https://github.com/fastino-ai/GLiNER2/blob/main/gliner2/configuration.py?utm_source=chatgpt.com) and [boundary model implementation](https://github.com/fastino-ai/GLiNER2/blob/main/gliner2/models/boundary/model.py?utm_source=chatgpt.com).

### 2.4 Loading the correct architecture

GLiNER2.5 boundary checkpoints should be loaded through `AutoExtractor`, which selects the implementation from the checkpoint's architecture configuration.

```
from gliner2 import AutoExtractormodel = AutoExtractor.from_pretrained(    "fastino/gliner2.5-base-v1")result = model.extract_entities(    "Apple CEO Tim Cook introduced a product in Cupertino.",    ["company", "person", "product", "location"],    include_spans=True,    include_confidence=True,)
```

The distinction matters because `GLiNER2`/`SpanExtractor` denotes the older span-grid implementation, while GLiNER2.5 uses `BoundaryExtractor`. Loading a new checkpoint with the older architecture-specific class should not be treated as equivalent to `AutoExtractor`.

The local model may be loaded from a Hugging Face repository identifier or a compatible local checkpoint directory. Model loading and local execution require the optional inference dependencies discussed later.

Source: [GLiNER2 Python package README and model-loading examples](https://github.com/fastino-ai/GLiNER2/blob/main/README.md?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 3. Core information extraction capabilities

### 3.1 Open-schema named entity recognition

GLiNER2.5 accepts entity categories at inference time. Labels can be terse names or richer descriptions of the desired textual span.

This makes the model applicable to domain-specific concepts without requiring a separately fine-tuned classifier for each new entity taxonomy.

For example, a schema can differentiate a `legal_party`, `contractual_obligation`, and `termination_trigger`, rather than merely requesting generic `organization` and `date` entities.

Descriptions are functional model inputs, not just documentation attached to output fields. They can communicate boundary conventions and distinctions between otherwise ambiguous categories.

The API supports confidence scores and character offsets. With `include_spans=True`, offsets are half-open indices into the original Python string: `text[start:end]` should equal the returned entity text.

Several practical distinctions follow:

- A mention and a real-world entity are not the same thing. Repeated textual mentions are separate extractions; GLiNER2.5 does not inherently canonicalize identities or perform entity resolution.
- A confidence value is a model score, not automatically a calibrated probability of factual correctness.
- Thresholding and overlap suppression can materially change the entity set even when the model weights and input text are unchanged.
- Long spans are permitted inside the model window, but the sparse candidate proposal stage can still fail to nominate a correct boundary pair.

Source: [Entity extraction tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/2-ner.md?utm_source=chatgpt.com).

### 3.2 Single-label and multi-label text classification

`classify_text()` predicts labels associated with a text input. The schema can represent several classification questions simultaneously, with mutually exclusive or nonexclusive labels.

Representative operations include sentiment, intent, topic, document type, severity, and other categorization problems expressed as label sets.

A single-label classifier chooses one label for a category. A multi-label classifier can return several labels, with configurable decision thresholds and selection limits.

An important distinction is that ordinary multi-task classification decodes the tasks independently. If one predicted label logically implies another, `classify_text()` alone does not enforce that implication. GLiNER2.5's separate `Classifier` interface provides the constrained alternative described in Section 4.

The schema builder additionally supports label descriptions and more explicit query instructions. These can disambiguate labels whose natural-language names are insufficiently specific.

Source: [Text classification tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/1-classification.md?utm_source=chatgpt.com).

### 3.3 Structured record extraction

`extract_json()` and the schema builder's `.structure(...).field(...)` interface convert unstructured passages into named fields and grouped objects.

This capability is more specialized than unconstrained language-model JSON generation. GLiNER2.5 is primarily extracting or classifying source-grounded content into a declared structure, rather than freely synthesizing arbitrary JSON values.

Supported schema features include named record types, field descriptions, scalar text fields, lists of extracted values, enumerated choices, and field-level filtering or validation. The builder offers `dtype="str"` and `dtype="list"` and richer field metadata.

A critical GLiNER2.5-specific mechanism is record mode:

```
schema = (    model.create_schema()    .structure("purchase", mode="natural", anchor="buyer")        .field("buyer", dtype="str", cardinality="required_one")        .field("item", dtype="str")        .field("quantity", dtype="str"))
```

This is an illustrative schema, not a claim about model output on a particular input.

Record mode attempts to preserve associations between multiple instances of the same structure. The `anchor` gives the model a field around which to group a record, helping distinguish, for example, a buyer's products and quantities from those belonging to a different buyer in the same text.

This addresses a consequential failure mode of independently extracted field lists: lists of buyers, products, and amounts do not by themselves establish which values belong together.

In record-oriented schemas, cardinality controls such as `required_one`, `optional_one`, `zero_or_more`, and `one_or_more` express field occurrence requirements. The API also exposes record-field exclusivity and ambiguity-handling mechanisms.

These are decoding and schema controls, not guarantees that the underlying document supplies all required facts. A missing field, conflicting statements, or incorrectly detected anchor can still produce an incomplete or incorrect record.

Also, strings containing dates, prices, and numbers are not necessarily normalized into native numeric or temporal types. Applications needing those semantics must distinguish extraction from subsequent parsing and validation.

Source: [Structured data extraction tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/3-json_extraction.md?utm_source=chatgpt.com) and [GLiNER2.5 base model card](https://huggingface.co/fastino/gliner2.5-base-v1?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 3.4 Relation extraction

Relation extraction identifies directed, labeled connections between textual mentions, such as `works_for`, `founded`, `located_in`, or `acquired`.

The ordinary `extract_relations()` interface returns relation candidates without requiring the caller to define a separate knowledge-graph schema.

This is useful for extracting independent tuples or when the goal is simply to obtain possible relationships with confidence scores and source spans.

However, ordinary relation extraction does not guarantee that its endpoints match a separate NER result or that the resulting collection of tuples obeys graph-wide invariants. For example, a `works_for` prediction is not inherently constrained to connect a `person` mention to an `organization` mention.

That distinction is the reason for the separate GLiNER2.5 `JointIE` interface.

Source: [Relation extraction tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/6-relation_extraction.md?utm_source=chatgpt.com).

### 3.5 Span attributes: classification attached to individual mentions

Entity attributes are one of the most distinctive additions in GLiNER2.5.

Where document classification answers a question about the input as a whole, an `AttributeGroup` predicts a label or set of labels for an individual extracted span, using its surrounding context.

For example, a product review can mention two devices with opposite sentiment. Document-level sentiment would collapse that distinction; span attributes can associate each sentiment with the corresponding product mention.

```
from gliner2 import AutoExtractor, AttributeGroupmodel = AutoExtractor.from_pretrained(    "fastino/gliner2.5-base-v1")schema = (    model.create_schema()    .entities(["product"])    .entity_attributes({        "sentiment": AttributeGroup(            ["positive", "negative", "neutral"],            applies_to=["product"],            qualify_labels=True,        )    }))result = model.extract(    "The phone is excellent, but the charger is unreliable.",    schema,    include_spans=True,    include_confidence=True,)
```

The execution sequence is significant: first the model selects entity spans, then it scores applicable attribute groups on those retained spans.

`AttributeGroup` supports single-label softmax decisions and multi-label sigmoid decisions with a threshold. `applies_to` limits an attribute group to particular entity categories. `qualify_labels=True` gives the model disambiguated label queries, such as `sentiment: positive`, while preserving the shorter returned label.

Multiple attribute groups can attach independent properties—such as sentiment, urgency, or aspect—to the same mention.

Limitation: Attribute scoring cannot recover an entity that was discarded earlier by boundary proposal, thresholding, or overlap decoding. It adds contextual classification to selected mentions; it does not provide an independent entity detection path.

Source: [GLiNER2.5 span attributes tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/13-span_attributes.md?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 3.6 Combined extraction with a shared schema

The most important compositional API is `model.create_schema()` followed by `model.extract(text, schema)`.

A combined schema can declare entities, entity attributes, document classifications, relations, and structured fields. GLiNER2.5 can then process the document through a shared contextual encoder rather than requiring separate full-model executions for each task.

This can eliminate custom coordination between separate NER, classification, and record extraction passes while producing one structured result tree.

An illustrative schema is:

```
schema = (    model.create_schema()    .entities(["company", "product", "person"])    .classification(        "document_type",        ["review", "announcement", "complaint"],    )    .relations(["works_for", "manufactures"])    .structure("product_information")        .field("name", dtype="str")        .field("features", dtype="list"))result = model.extract(text, schema)
```

The shared encoder provides contextual reuse, but it does not imply that every output head shares a globally consistent decoder. Ordinary classifications and relations remain independently decoded unless the dedicated constrained-classification or joint-graph machinery is invoked.

Sources: [Combined schemas tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/4-combined.md?utm_source=chatgpt.com) and [span attributes composition](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/13-span_attributes.md?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



## 4. Advanced decoding: constraints and coherent entity–relation graphs

The most consequential distinction in the GLiNER2.5 Python API is between independent predictions and joint decoding under explicit structural constraints.

The constrained interfaces do not merely reject invalid outputs after extraction. They use the model's candidate scores to search for assignments or graphs that jointly satisfy declared rules.

### 4.1 Constrained classification with `Classifier`

The dedicated `gliner2.classification` subsystem separates neural scoring from a constraint-aware classification decoder.

Its principal abstractions are:

| Component              | Responsibility                                                                  |
| ---------------------- | ------------------------------------------------------------------------------- |
| `Classifier`           | Scores and decodes classification tasks using a GLiNER2.5 checkpoint            |
| `ClassificationSchema` | Declares single-label, multi-label, and ordinal tasks                           |
| `constraints` module   | Expresses logical and cardinality relationships between labels                  |
| `ClassificationConfig` | Controls decoding search, candidate budgets, and infeasibility behavior         |
| `ClassificationResult` | Exposes selected labels, probabilities, confidence, feasibility, and violations |

Three task types are supported. `.single()` selects exactly one label; `.multi()` supports sets of labels with minimum and maximum cardinality; `.ordinal()` describes an ordered, exclusive classification scale.

The constraint DSL includes logical implication, equivalence, mutual exclusion, negation, conjunction, disjunction, exactly-one selection, cardinality limits, and ordinal bounds.

For example:

```
from gliner2.classification import (    Classifier,    ClassificationSchema,    ClassificationConfig,)from gliner2.classification import constraints as Cclf = Classifier.from_pretrained(    "fastino/gliner2.5-base-v1")schema = (    ClassificationSchema()    .single("intent", ["read", "write", "delete"])    .multi(        "effects",        ["read_only", "create", "modify", "delete"],        min_labels=1,        max_labels=2,    )    .constrain(        C.implies(("intent", "delete"), ("effects", "delete")),        C.excludes(("intent", "read"), ("effects", "delete")),    ))result = clf.classify(    "Delete the temporary files",    schema,    config=ClassificationConfig(on_infeasible="raise"),)
```

The value of this mechanism is that the globally selected result can differ from the independent per-task argmax. A slightly lower-scoring label combination may be preferred because it satisfies a required implication or exclusion.

#### Decoding strategies and guarantees

`ClassificationConfig` supports `decoder="independent"`, `"exact"`, `"beam"`, or `"auto"`.

Exact decoding searches for a feasible assignment within a configurable node budget. Beam decoding maintains a bounded number of candidate assignments and is useful when combinatorial search grows expensive. Automatic mode chooses between these approaches based on the search problem.

The guarantee has an important qualification: the default infeasibility policy is `on_infeasible="relax"`, which can return a best-effort result even when not all constraints were met. Other policies are `"min_violations"` and `"raise"`.

`ClassificationResult.feasible`, `.violations`, and the reported exactness metadata must therefore be interpreted explicitly. A successful return from `classify()` is not alone proof that all logical conditions were satisfied.

For advanced control, `clf.score()` exposes the scoring stage separately from `clf.decode()`. This permits reuse of scores across alternative decoders or decoding configurations without conflating neural scoring with constraint search.

Compiled classification schemas are fingerprinted and cached, making stable schema reuse valuable beyond ordinary Python object reuse.

There is also `Classifier.classify_long()`, which aggregates scores from document chunks and applies the constraint decoder once at document level. That preserves global logical consistency across the final classification, unlike simply merging independently classified pages.

Primary reference: [GLiNER2.5 constrained classification tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/14-constrained_classification.md?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



### 4.2 Joint information extraction with `JointIE`

`JointIE` extends the same general idea from classification labels to a typed graph of textual mentions and relations.

Rather than running NER, independently extracting relations, and attempting to reconcile the results afterward, the joint decoder chooses entities and edges together from a candidate lattice.

```
from gliner2.joint_ie import JointIE, JointIEConfigjoint = JointIE.from_pretrained(    "fastino/gliner2.5-base-v1")schema = (    joint.create_schema()    .entities(["person", "organization", "location"])    .relation(        "works_for",        head="person",        tail="organization",        unique_head=True,    )    .relation(        "located_in",        head="organization",        tail="location",    )    .no_self_loops())result = joint.extract(    "Alice works for Acme in Paris.",    schema,    config=JointIEConfig(optimizer="beam", beam_size=32),)
```

Here, `works_for` is explicitly typed as a person-to-organization edge, and `unique_head=True` limits each person to at most one selected employer relationship of that type.

`JointSchema` additionally supports directed versus symmetric relations, inverse relation pairs, per-head and per-tail degree limits, maximum edge counts, uniqueness, and acyclicity. The built-in constraint classes include `TypedEndpoints`, `NoSelfLoops`, `UniqueRelationPair`, `SymmetricRelation`, `InverseRelation`, and `AcyclicRelation`.

These mechanisms can directly represent important graph integrity rules that would otherwise require bespoke reconciliation logic.

#### Search and candidate controls

`JointIEConfig` exposes `optimizer="beam"|"greedy"|"auto"`, `beam_size`, entity and relation thresholds, `top_k_entities`, `top_k_roles`, `relation_pair_cap`, and related candidate limits.

Greedy search is less computationally demanding but explores fewer competing graph assignments. Beam search can find stronger joint solutions, subject to its beam width and candidate budgets.

The returned `JointResult` contains entities with IDs and original text offsets, together with relations referencing those IDs. It provides traversal conveniences such as `outgoing()`, `incoming()`, `neighbors()`, and `relations_of()`, as well as optional `to_networkx()` conversion.

For diagnosis or custom downstream analysis, `joint.score()` exposes the scored candidate lattice, and `joint.extract(..., return_lattice=True)` returns it alongside the decoded result.

Feasibility is not optional metadata. `result.feasible=False` indicates the decoder could not satisfy its hard constraints and fell back to an empty assignment. This is semantically different from a feasible result containing no entities because the text had no matching facts.

Joint decoding enforces coherence among the candidates it considers. It cannot guarantee that those candidates are factually correct or that the true entity/relation was present in its bounded search space.

`JointIE` requires a GLiNER2.5 boundary checkpoint with the relation head enabled for relation extraction; entity-only joint extraction can operate without that head.

Primary reference: [GLiNER2.5 joint information extraction tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/15-joint_ie.md?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+2



### 4.3 Choosing between the decoding surfaces

These APIs share the same underlying checkpoint family but offer different semantics.

| Need                                                   | Appropriate surface     | Decoding characteristic                           |
| ------------------------------------------------------ | ----------------------- | ------------------------------------------------- |
| Obtain possible entity spans                           | `extract_entities()`    | Independent span selection                        |
| Obtain possible relation tuples                        | `extract_relations()`   | Independent relation extraction                   |
| Combine several extraction tasks                       | `extract()`             | Shared schema and encoder, task-specific decoding |
| Enforce logical consistency among classifications      | `Classifier.classify()` | Constrained label assignment                      |
| Enforce type and structural rules in a knowledge graph | `JointIE.extract()`     | Constrained joint entity–relation graph search    |

This division matters architecturally. A single call to a combined schema is not automatically equivalent to running `JointIE`, and a multi-task `classify_text()` invocation is not equivalent to constrained `Classifier` decoding.

## 5. Long-context extraction and document-scale semantics

GLiNER2.5 offers two complementary forms of long-context support: a larger native model window and native chunked extraction over arbitrarily longer input documents.

### 5.1 Extended native context

The upstream GLiNER2.5 announcement reports training on sequences as long as approximately 4,096 words, enabled partly by eliminating the dense fixed-width span grid.

This is especially relevant for clause-length entities, multi-sentence references, and other information that cannot be meaningfully split into short independent mentions.

However, a model's trained context length is distinct from an unlimited document length. Inputs exceeding the effective encoded window still require truncation or explicit long-document handling.

The 4,096-word figure should also not be confused with a universal guarantee of 4,096 arbitrary subword tokens, or with an assertion that every possible schema consumes no context budget.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://fastino.ai\&sz=32)

fastino.ai



### 5.2 Native chunking, merging, and offset remapping

The Python library provides task-specific long-input methods and an equivalent full-schema method:

| Task                        | Long-document API            |
| --------------------------- | ---------------------------- |
| NER                         | `extract_entities_long()`    |
| General schema extraction   | `extract_long()`             |
| Classification              | `classify_text_long()`       |
| Structured records          | `extract_json_long()`        |
| Relations                   | `extract_relations_long()`   |
| Constrained classification  | `Classifier.classify_long()` |
| Joint entity–relation graph | `JointIE.extract_long()`     |

Corresponding batch methods exist for the main extraction tasks.

A representative invocation is:

```
result = model.extract_entities_long(    document,    {        "organization": "Named institutions or companies",        "obligation": "Text stating a contractual duty",    },    chunk_size=384,    chunk_overlap=64,    include_spans=True,    include_confidence=True,)
```

The library splits the input into overlapping windows, runs the requested schema for each window, remaps local spans to global character offsets, and merges duplicate candidates across overlaps.

By default, chunk lengths are measured in whitespace-delimited words rather than characters or tokenizer subwords. The checkpoint-associated `word_splitter` determines the segmentation rules.

The native `word_splitter="char"` option supports character-based segmentation for languages that lack whitespace word boundaries, while custom splitters can yield `(token, start, end)` tuples. Changing the splitter may affect model quality because the training-time segmentation assumptions also matter.

### 5.3 Overlap resolution and information preservation

Long-document inference has two kinds of overlap to manage: intentional duplication of text across adjacent chunks, and genuinely overlapping or nested entities within the source document.

The API exposes `overlap_policy` choices including:

| Policy              | Behavior                                                  |
| ------------------- | --------------------------------------------------------- |
| `allow`             | Preserve distinct overlapping mentions                    |
| `nested`            | Permit contained spans                                    |
| `flat` / `disallow` | Suppress overlapping spans deterministically              |
| `longest`           | Prefer longer spans over strictly contained shorter spans |

The boundary model's default flat selection is suitable for conventional nonoverlapping NER. Other policies become important when labels naturally nest, such as a product family contained within a full product identifier, or a named organization contained within a larger contractual reference.

The library deduplicates the same detected occurrence from overlapping chunks using source positions. This is distinct from deduplicating repeated words across an entire document: two identical company names at different positions remain separate mentions.

### 5.4 The cross-window limits

Native chunking removes a substantial amount of custom infrastructure, but it does not transform GLiNER2.5 into an unbounded-context reasoning model.

A span can be extracted only if its full beginning and end are visible together in an encoded window. Overlap can improve the chance of this happening; it cannot recover a span longer than every available chunk.

Similarly, an extracted relation requires both endpoints to occur in a common chunk. `JointIE.extract_long()` explicitly does not synthesize cross-window edges. Overlapping duplicate mentions are merged, but this is not equivalent to full-document entity coreference or globally optimized graph reconciliation.

Ordinary long-document classification aggregates chunk predictions, with stronger chunk evidence favored. `Classifier.classify_long()` instead aggregates label scores before applying its constraints once. This distinction is consequential for document-wide label dependencies.

Structured records may likewise require care where related fields are distributed across distant passages. The native long API supports record extraction, but chunking alone does not guarantee that all fields belonging to one real-world record will be reconciled across windows.

Primary reference: [GLiNER2.5 long-context extraction tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/12-long_context.md?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+3



## 6. Schemas, validation, and extensibility

### 6.1 Schema as a reusable declarative contract

GLiNER2.5 schemas define what the model should predict and, within supported limits, how candidate predictions are filtered or decoded.

Schema inputs can include label names and descriptions, field definitions, record grouping, classification instructions, relation types, per-query thresholds, and examples used to condition the model.

The Python builder is therefore more than a convenience wrapper. It provides a common declarative representation that can be reused across short-input inference, batch inference, long-document processing, and supported multi-task operations.

Package 2.1.0 substantially expanded `Schema.from_dict()` parity with the Python builder. It supports classification thresholds, `top_k`, label descriptions, activation configuration, prompts and few-shot examples, per-type entity/relation descriptions and thresholds, and entity-attribute configuration. Unknown schema keys are rejected rather than silently accepted. `to_dict()` preserves these supported options for round-tripping.

This makes externally configured schemas more viable without requiring callers to reconstruct complex fluent builder calls manually. It also makes schema changes explicit and inspectable.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 6.2 Regex validation

`RegexValidator` provides an extraction-level mechanism for filtering candidates using text patterns.

For example:

```
from gliner2 import RegexValidatorvalidator = RegexValidator(    r"^[A-Z]{3}-\d{6}$",    mode="full",)schema = (    model.create_schema()    .structure("document")        .field("reference_id", dtype="str", validators=[validator]))
```

`mode="full"` requires the entire extracted string to match, while `mode="partial"` permits a substring match. `exclude=True` reverses the filter to reject matching values, and Python regex flags are supported.

This is useful when semantic extraction and deterministic format validation complement each other: the neural model decides what is a relevant candidate, while a regular expression determines whether the candidate has the required textual shape.

It remains post-extraction filtering, not proof that the extracted identifier exists, belongs to the right organization, or is semantically valid. Pattern validators cannot rescue a candidate the model never proposed.

Sources: [Regex validator tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/5-validator.md?utm_source=chatgpt.com) and [schema implementation](https://github.com/fastino-ai/GLiNER2/blob/main/gliner2/inference/schema.py?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 6.3 Lower-level extension points

Beyond the fluent extraction APIs, the boundary implementation exposes primitives for advanced inference control.

Most notably, `score_explicit_spans()` can score caller-supplied span indices using an already encoded batch. This bypasses the ordinary top-k proposal mechanism while retaining the model's boundary compatibility and pair reranking.

That capability opens a different problem shape from open-ended discovery: given externally generated candidate spans, how strongly does the GLiNER2.5 model support them under a schema?

This is useful conceptually when candidate boundaries come from deterministic parsers, external indexing systems, or other extraction stages. It also separates errors caused by candidate generation from errors caused by neural candidate scoring.

Another extension point is the ability to reuse precomputed encoder states in batch inference. As of package 2.1.0, batch extraction, classification, and scoring can accept `hidden_states=`; `encode_tokens(batch, hidden_states=None)` is the model-level encoder gateway, and `BoundaryExtractorModel(load_encoder=False)` can instantiate the task heads without loading the encoder.

These are advanced internal-facing capabilities with more lifecycle and tensor-shape obligations than the high-level `extract()` API. Their value is greatest when the same compatible encoded inputs must support several separately managed scoring operations.

Sources: [Boundary model implementation](https://github.com/fastino-ai/GLiNER2/blob/main/gliner2/models/boundary/model.py?utm_source=chatgpt.com) and [v2.1.0 release notes](https://github.com/fastino-ai/GLiNER2/releases/tag/v2.1.0?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 7. Inference execution, hardware acceleration, and performance mechanisms

### 7.1 Packaging and dependency profiles

The `gliner2` package separates schema construction and hosted API access from local PyTorch inference.

| Installation                                | Supported role                                                             |
| ------------------------------------------- | -------------------------------------------------------------------------- |
| `pip install gliner2`                       | Schema objects, validators, training-data utilities, and hosted API client |
| `pip install "gliner2[local]"`              | Local inference using PyTorch and Transformers                             |
| `pip install "gliner2[train]"`              | Model training, including tokenizer construction dependencies              |
| `pip install "gliner2[disentangled-flash]"` | Local inference with the optional optimized DeBERTa attention backend      |

The base installation does not require PyTorch. This is useful when schemas are manipulated independently of neural execution or when the inference engine is accessed as a service.

Package 2.1.0 declares `torch>=2.1,<3` and `transformers>=4.43,<6` for its local and training profiles. Python 3.10–3.12 are the explicitly tested versions; a newer Python interpreter is not automatically guaranteed to have a compatible set of local inference dependencies.

The model may execute on CPU or an appropriate PyTorch accelerator. The availability and benefit of optimized attention implementations depend on hardware and installed companion libraries.

Sources: [PyPI installation and compatibility](https://pypi.org/project/gliner2/?utm_source=chatgpt.com) and [release v2.1.0 dependency changes](https://github.com/fastino-ai/GLiNER2/releases/tag/v2.1.0?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+1



### 7.2 Native batching and shared work

GLiNER2.5 provides `batch_extract_entities()`, `batch_classify_text()`, and corresponding batch interfaces for other extraction families.

Batching can improve throughput by amortizing framework and device-launch overhead, processing padded tensors together, and allowing the encoder to exploit larger parallel workloads.

There are two distinct ways to reuse computation:

Within a combined schema, multiple requested task families share document encoding in one extraction operation.

Across separate inference operations, the newer precomputed hidden-state interface allows compatible batch calls to reuse encoder outputs.

These approaches solve related but different problems. Combined schemas are the simpler high-level abstraction when tasks can be declared together. Precomputed states provide additional control when encoder and decoder execution must be managed separately.

In either case, reusable tensor representations depend on consistent tokenization, query/schema construction, attention masks, model weights, and device placement. Reusing an encoded state under an incompatible schema or modified model is not a valid general-purpose cache operation.

Batch efficiency also depends on input length distribution. A batch containing one very long document and numerous short ones can waste work on padding unless the execution backend can avoid it.

### 7.3 Precision and compilation

The model loader exposes `quantize=True` and `compile=True`:

```
model = AutoExtractor.from_pretrained(    "fastino/gliner2.5-base-v1",    map_location="cuda",    quantize=True,    compile=True,)
```

An important terminology distinction: `quantize=True` currently requests FP16 conversion, not general INT8 or 4-bit weight quantization. The documentation uses quantize as a convenience API name, but it should not be interpreted as support for every quantization format or backend.

FP16 can reduce memory consumption and improve throughput on compatible hardware, though numerical behavior and kernel support remain relevant.

`compile=True` invokes `torch.compile`-based acceleration. It may reduce execution overhead and fuse supported kernels, with an initial compilation/tracing cost. Benefits depend on input shapes, backend support, workload repetition, and the amount of execution time spent in compilable operations.

Neither option guarantees universal speedups. In particular, PyTorch compilation should not be assumed to accelerate Python-side candidate merging, graph decoding, or all schema-management work to the same extent.

Source: [GLiNER2 inference optimization options](https://github.com/fastino-ai/GLiNER2/blob/main/README.md?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 7.4 Attention backends: standard, FlashDeBERTa, and DisentangledFlash

GLiNER2.5's DeBERTa-based encoder can use several alternative attention implementations.

| `attention_backend`    | Mechanism                                                             | Important conditions                                                                |
| ---------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `"standard"`           | Standard Transformers attention                                       | Broad compatibility and baseline behavior                                           |
| `"flashdeberta"`       | FlashDeBERTa optimized attention                                      | Requires the companion implementation and compatible DeBERTa encoder                |
| `"disentangled_flash"` | Optimized exact DeBERTa disentangled attention, with optional packing | Requires the optional integration; cannot currently be combined with `compile=True` |

DisentangledFlash is particularly noteworthy because it targets DeBERTa's relative/disentangled attention semantics rather than simply substituting a generic attention operation.

The integration provides Triton kernels on supported NVIDIA GPUs and an optimized PyTorch backend elsewhere. It avoids materializing the full attention matrix in supported execution paths, potentially reducing memory movement and intermediate allocations.

A GLiNER2.5-specific loading example is:

```
model = AutoExtractor.from_pretrained(    "fastino/gliner2.5-base-v1",    map_location="cuda",    quantize=True,    attention_backend="disentangled_flash",)
```

#### Automatic unpadded execution

DisentangledFlash also supports packed execution, removing padding from eligible batches.

With the default automatic policy, packing is selected only when the padding fraction and estimated attention workload exceed configured thresholds. The published defaults are at least 15% padding and \\(B \times L^2 \geq 2^{21}\\), where \\(B\\) is batch size and \\(L\\) is padded sequence length.

These thresholds were measured on an H200 GPU and are heuristics for choosing an execution path, not universally optimal cutoffs.

The integration also exposes a differentiable training path through `enable_disentangled_flash(inference=False)`, which is distinct from the inference-oriented loader configuration.

The main performance opportunity is avoiding unnecessary attention work and memory movement—especially in batches of unequal-length documents—not changing the semantics of the extraction schema.

Sources: [DisentangledFlash integration documentation](https://github.com/fastino-ai/GLiNER2/blob/main/README.md?utm_source=chatgpt.com), [v2.1.0 release notes](https://github.com/fastino-ai/GLiNER2/releases/tag/v2.1.0?utm_source=chatgpt.com), and [DisentangledFlash upstream repository](https://github.com/stanford-futuredata/DisentangledFlash?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



### 7.5 Distinguishing the model variants

The three general-purpose 2.5 checkpoints occupy different positions along the parameter-count, language coverage, and execution-cost tradeoff.

The 74M small model is the compact English alternative. The 194M base checkpoint is the general English model, while the 287M multilingual model trades additional parameter and execution cost for multilingual capability.

The package also documents two GLiNER2.5-Decide checkpoints specialized for classification:

- [`fastino/GLiNER2.5-Decide`](https://huggingface.co/fastino/GLiNER2.5-Decide?utm_source=chatgpt.com) — English classification specialist, 340M parameters.
- [`fastino/GLiNER2.5-multi-Decide`](https://huggingface.co/fastino/GLiNER2.5-multi-Decide?utm_source=chatgpt.com) — multilingual classification specialist, 287M parameters.

These require a qualification: the English `GLiNER2.5-Decide` checkpoint is marked as a `span`-architecture model despite its 2.5 name. The multilingual Decide checkpoint is marked `boundary`.

They should therefore be understood as specialized classification checkpoints, not interchangeable replacements for the three general-purpose GLiNER2.5 boundary models or evidence that every 2.5-named model uses boundary extraction.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



## 8. Training and model specialization

### 8.1 Full supervised fine-tuning

The library includes a native training pipeline centered on `InputExample`, `TrainingDataset`, `ExtractorTrainer`, and `TrainingConfig`.

Training can specialize an existing GLiNER2.5 checkpoint for domain terminology, entity boundaries, classifications, structured fields, and relation patterns.

`TrainingConfig` exposes separate encoder and task-head learning rates, batch size and gradient accumulation, optimizers and scheduling, warmup, gradient checkpointing, mixed precision, evaluation frequency, best-checkpoint selection, early stopping, and experiment logging.

A minimal GLiNER2.5-specific sketch is:

```
from gliner2 import AutoExtractorfrom gliner2.training.data import InputExample, TrainingDatasetfrom gliner2.training.trainer import ExtractorTrainer, TrainingConfigmodel = AutoExtractor.from_pretrained(    "fastino/gliner2.5-base-v1")data = TrainingDataset([    InputExample(        text="Acme acquired Nova Systems.",        entities={            "acquirer": ["Acme"],            "acquired_company": ["Nova Systems"],        },    ),])config = TrainingConfig(    output_dir="./specialized_model",    num_epochs=10,    batch_size=8,    encoder_lr=1e-5,    task_lr=5e-4,)trainer = ExtractorTrainer(model, config)
```

This illustrates the training abstractions; it is not an executed training job or a complete recommendation for training parameters.

The trainer supports full-model fine-tuning and checkpoint evaluation/saving without requiring an external training framework to be built around the library.

Source: [Model training tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/9-training.md?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 8.2 Multi-task training-data representation

Training examples can be constructed programmatically or supplied through JSONL files.

The principal serialized forms use an `input`/`output` pair or the equivalent `text`/`schema` representation.

Supervision may contain entity mentions, entity descriptions, classification tasks and true labels, record structures, field descriptions, and relations.

The data model supports combining task families in one training example. That is significant because the model's schema-conditioned capability is not limited to isolated single-purpose datasets.

Entity and field values can be annotated using surface strings or explicit character spans.

Explicit span supervision is especially important for repeated text. A surface string alone can match multiple occurrences; a span with `text`, `start`, and `end` disambiguates the intended occurrence. Package 2.1.0 explicitly improved support for this in the boundary training path.

Relation annotations also have a consistency requirement: repeated instances of one relation type must use the same field structure. `TrainingDataset.validate_relation_consistency()` provides a native check.

Source: [Training data format reference](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/8-train_data.md?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 8.3 Training data alignment and negative supervision

GLiNER2.5's boundary architecture makes accurate annotation alignment consequential.

An extracted string might exist in the raw text yet fail to align with the word-token boundaries expected by the model. The library provides `SchemaTransformer.find_unalignable_entities()` for detecting problematic annotations before training.

The release also changes contained-span supervision: with `dedupe_contained_entity_spans=True`, shorter gold entity matches contained in longer entity mentions are removed by default. This prevents certain accidental duplicate targets but can alter intended supervision when nested labels are genuinely desired.

Negative training examples require an explicit interpretation of which entity types are absent. An empty entity dictionary does not, on its own, establish that the example is a negative for every possible entity label.

For multilingual workloads, version 2.1.0 fixes word splitting involving combining marks and related writing-system characters. This is materially relevant to training and extracting aligned spans in scripts using such marks.

The same release fixes gold-label corruption under synthetic label renaming and half-precision numerical instability in the marginal pair-consistency loss. These are training-correctness changes rather than new model capabilities, and they are reasons to distinguish the 2.1.0 software implementation from the unchanged 2.5 checkpoint weights.

Sources: [Training data tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/8-train_data.md?utm_source=chatgpt.com) and [v2.1.0 training fixes](https://github.com/fastino-ai/GLiNER2/releases/tag/v2.1.0?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



### 8.4 LoRA adapters and specialization without full checkpoint duplication

The training system supports low-rank adaptation through `TrainingConfig(use_lora=True, ...)`, with controls for rank, scaling, dropout, target modules, and adapter-only saving.

This enables specialized domain models to share the same base checkpoint while storing smaller adaptation weights.

The library includes runtime operations for `load_adapter()`, `unload_adapter()`, and adapter status inspection. Loading another adapter can replace the currently active adapter without reloading the complete base model.

The documented adapter-switching interface is meaningful for applications that require multiple task or domain specializations while keeping the core encoder weights shared.

There are two integration qualifications:

First, adapter compatibility depends on the underlying model architecture and targeted modules. An adapter trained for a span-architecture checkpoint should not be assumed compatible with a GLiNER2.5 boundary checkpoint.

Second, loading and unloading adapters changes model state. A service processing concurrent requests for different adapters must account for that shared mutable state; merely switching the adapter before each request does not establish safe concurrent isolation.

The 2.1.0 release includes a fix to ensure LoRA layers are correctly removed even when injected directly into model modules.

Sources: [LoRA adapter tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/10-lora_adapters.md?utm_source=chatgpt.com) and [adapter switching tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/11-adapter_switching.md?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+2



### 8.5 A boundary of attribute supervision

Although entity attributes are supported at inference time, the documented JSONL training format does not yet define a separate attribute-annotation field.

This means that the presence of `AttributeGroup` in the inference API should not be interpreted as evidence of an equally mature, independently annotated training pipeline for every possible span-attribute task.

The upstream training-data guide explicitly identifies that limitation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 9. Evaluation evidence, semantic limits, and architectural tradeoffs

### 9.1 Published benchmark evidence

Fastino reports macro-averaged F1 scores over a suite of 16 classification and extraction tasks. The main comparative results are:

| Task category  | GLiNER2.5 Multi | GLiNER2.5 Base | Earlier Multi | Earlier Base |
| -------------- | --------------- | -------------- | ------------- | ------------ |
| Overall        | 56.17           | 54.87          | 56.09         | 53.34        |
| Classification | 72.44           | 69.86          | 70.32         | 68.89        |
| Extraction     | 46.40           | 45.88          | 47.56         | 44.01        |

These figures establish that the architectural changes did not cause a broad collapse in the vendor's benchmark suite, but they do not demonstrate uniform accuracy improvements.

In particular, the multilingual GLiNER2.5 extraction aggregate is slightly below its earlier counterpart, even though the overall and classification averages are higher.

Some individual tasks improve substantially. The reported multilingual XNLI score rises from 37.55 to 62.30, while several sentiment, intent, topic, and CrossNER evaluations exhibit smaller gains or regressions.

The results are from the developer's published benchmark evaluation, not an independent comparative deployment study. They do not establish real-world latency, throughput, long-document recall, or performance under a particular domain schema.

Source: [GLiNER2.5 benchmark methodology and per-dataset results](https://fastino.ai/blog/gliner2-5-span-free-information-extraction?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://fastino.ai\&sz=32)

fastino.ai



### 9.2 What GLiNER2.5 can replace—and what it cannot

At the capability level, GLiNER2.5 can consolidate several operations previously handled by separate components: open-schema NER, text classification, source-grounded field extraction, mention-level attribute labeling, relation prediction, and some graph or classification consistency enforcement.

It may therefore reduce the need for custom token-labeling models, hand-maintained extraction taxonomies, multi-stage span scoring, separate post-extraction attribute classifiers, bespoke chunk-offset reconciliation, or handcrafted graph-repair logic.

The degree to which this simplifies a system depends on the semantics required.

| Requirement                                                     | GLiNER2.5 coverage or boundary                                  |
| --------------------------------------------------------------- | --------------------------------------------------------------- |
| Extract new entity categories without retraining                | Supported through schema-conditioned inference                  |
| Return source-grounded text offsets                             | Supported for span-oriented extraction                          |
| Enforce some cross-label logic                                  | Supported by constrained classification, subject to feasibility |
| Enforce typed graph edges and local graph constraints           | Supported by `JointIE`                                          |
| Capture long mentions                                           | Supported within an encoded window                              |
| Process arbitrarily long documents                              | Chunked processing; not unrestricted global context             |
| Resolve mentions to canonical real-world identities             | Not provided by mention extraction alone                        |
| Infer relations between distant, separately chunked passages    | Not synthesized by the native long-document graph API           |
| Validate arbitrary business logic or external facts             | Requires mechanisms beyond schema scoring and regex filtering   |
| Generate arbitrary novel JSON or perform open-ended reasoning   | Outside the core encoder-based extraction model                 |
| Return perfectly calibrated or factually guaranteed predictions | Not established by model confidence or constraint feasibility   |

One important distinction is structural validity versus semantic truth.

A `JointIE` output can satisfy all declared endpoint and cardinality constraints while still asserting a relationship unsupported by the document. Likewise, a feasible constrained classification can be internally consistent yet classify the text incorrectly.

The neural prediction problem and the constraint-satisfaction problem are separate. GLiNER2.5 provides mechanisms for both, but success at the second does not guarantee success at the first.

### 9.3 Local execution versus the hosted client

The package also includes a hosted API client, available without local PyTorch inference dependencies.

It exposes similar extraction interfaces and uses `FASTINO_API_KEY` for authentication in package 2.1.0.

However, it is important not to conflate the availability of the client with the exact checkpoint selected by the hosted service. The hosted API tutorial describes a default GLiNER2 model and does not establish that every endpoint or hosted operation is backed by one of the three local GLiNER2.5 checkpoints.

The documentation also identifies differences in capability; for example, local `RegexValidator` support is not mirrored by the hosted API.

Consequently, the hosted client should be regarded as a related execution service with its own model-selection, validation, latency, privacy, and availability boundaries, not as an automatic drop-in guarantee of bit-for-bit local GLiNER2.5 behavior.

Source: [Hosted GLiNER2 API documentation](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/7-api.md?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 9.4 Principal tradeoffs

The main tradeoffs fall into a few connected dimensions.

Model capacity versus execution cost. The smaller checkpoint reduces the model footprint, while larger English and multilingual models may offer better task coverage. Parameter count alone does not predict performance for a particular label taxonomy.

Sparse proposals versus recall. Avoiding exhaustive span enumeration reduces candidate-scoring work, but introduces proposal-selection limits. This becomes important when documents contain many overlapping mentions or subtle boundaries.

One combined model versus specialized decoders. Combined extraction offers shared computation and a common schema, but graph coherence and cross-label consistency require their dedicated decoding interfaces.

Long-window extraction versus chunking. Larger windows preserve more context and allow wider entity spans, while smaller windows can lower per-inference cost and simplify batching. Chunking introduces boundary and cross-window information loss.

Constraints versus decoder search complexity. Stronger consistency requirements make outputs more useful, but exact or approximate search consumes resources and can become infeasible if the candidate set or logical requirements conflict.

Generalization versus fine-tuning. Zero-shot schemas offer flexibility; supervised specialization can improve domain alignment, but introduces training-data quality, model-lifecycle, and adapter compatibility obligations.

These are architectural choices rather than universal rankings. The model's advanced capabilities are valuable precisely because their execution and decoding semantics can be selected independently according to the problem being expressed.

## 10. Primary-source reference map

The following are the most useful direct resources for further investigation. All URLs are explicit and independently accessible.

| Subject                                                                                  | Primary source                                                                                                                                          |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Python package, supported checkpoint catalog, combined APIs, batching, and optimizations | [GitHub README](https://github.com/fastino-ai/GLiNER2/blob/main/README.md?utm_source=chatgpt.com)                                                       |
| Python release and dependency metadata                                                   | [PyPI — gliner2](https://pypi.org/project/gliner2/?utm_source=chatgpt.com)                                                                              |
| Version-specific schema, inference, attention, and training changes                      | [GLiNER2 v2.1.0 release notes](https://github.com/fastino-ai/GLiNER2/releases/tag/v2.1.0?utm_source=chatgpt.com)                                        |
| Architecture and benchmark rationale                                                     | [Fastino — Introducing GLiNER2.5](https://fastino.ai/blog/gliner2-5-span-free-information-extraction?utm_source=chatgpt.com)                            |
| Boundary checkpoint configuration and practical extraction examples                      | [GLiNER2.5 Base model card](https://huggingface.co/fastino/gliner2.5-base-v1?utm_source=chatgpt.com)                                                    |
| Multilingual model characteristics                                                       | [GLiNER2.5 Multi model card](https://huggingface.co/fastino/gliner2.5-multi-v1?utm_source=chatgpt.com)                                                  |
| Entity-level attributes                                                                  | [Span Attributes tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/13-span_attributes.md?utm_source=chatgpt.com)                       |
| Hard cross-task classification constraints                                               | [Constrained Classification tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/14-constrained_classification.md?utm_source=chatgpt.com) |
| Graph constraints, candidate lattices, and joint decoding                                | [Joint Information Extraction tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/15-joint_ie.md?utm_source=chatgpt.com)                 |
| Chunked inference, overlap policies, and global offsets                                  | [Long-Context Extraction tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/12-long_context.md?utm_source=chatgpt.com)                  |
| Grouped records, anchors, and field extraction                                           | [Structured Data Extraction tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/3-json_extraction.md?utm_source=chatgpt.com)             |
| Schema builder and its implementation details                                            | [Schema source](https://github.com/fastino-ai/GLiNER2/blob/main/gliner2/inference/schema.py?utm_source=chatgpt.com)                                     |
| Boundary scoring and lower-level model interfaces                                        | [Boundary model source](https://github.com/fastino-ai/GLiNER2/blob/main/gliner2/models/boundary/model.py?utm_source=chatgpt.com)                        |
| Dataset schemas, explicit spans, and annotation consistency                              | [Training Data Formats](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/8-train_data.md?utm_source=chatgpt.com)                                |
| Trainer, training configuration, and specialization                                      | [Model Training tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/9-training.md?utm_source=chatgpt.com)                                |
| Parameter-efficient fine-tuning and adapter lifecycle                                    | [LoRA Adapters tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/10-lora_adapters.md?utm_source=chatgpt.com)                           |

## 11. Synthesis

GLiNER2.5's central capability is best understood as schema-conditioned information extraction backed by sparse boundary proposals and multiple task-aware decoders.

The boundary architecture removes the old fixed-width span constraint, enabling more flexible extraction of long textual units while controlling candidate-scoring cost. Its common encoder makes combined NER, classification, structured records, relations, and mention-level attributes practical within one inference framework.

Two additional capabilities substantially widen its scope: constrained classification, which searches for logically consistent assignments across tasks, and `JointIE`, which selects typed entity–relation graphs under structural rules. Together, these move the library beyond a collection of independent extraction heads toward declarative structured prediction.

The native long-document APIs, explicit span offsets, overlapping-window deduplication, batched execution, attention acceleration, reusable encoder states, and supervised/LoRA specialization complete a comparatively broad information-extraction toolkit.

Its limits remain equally important: proposal budgets affect recall, the encoded context window remains finite, chunking does not recover arbitrary cross-window relationships, graph feasibility does not establish factual correctness, and declarative schemas do not replace general-purpose semantic validation.

For an advanced engineer or programming agent, the most valuable architectural insight is that GLiNER2.5 can combine neural interpretation, declarative extraction schemas, native candidate selection, and constraint-aware decoding within one library—while retaining explicit boundaries between what the model predicts, what its decoder enforces, and what downstream systems must still establish independently.