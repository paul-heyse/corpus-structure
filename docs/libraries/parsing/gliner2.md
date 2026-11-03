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

# GLiNER2.5 — Supplemental Capability Reference

Addendum to `gliner2.md` | Research date: November 3, 2026 | Python package: `gliner2` 2.1.0

This addendum extends the primary GLiNER2.5 reference with additional record-formation mechanisms, boundary-head capabilities, specialized checkpoints, training controls, schema facilities, and execution interfaces.

The version baseline is the latest verified PyPI release, `gliner2` 2.1.0, published October 9, 2026. Checkpoint-specific information is based on the separately published model configurations and model cards. Implementation-level configuration options are distinguished from behavior enabled in released weights.

Primary release: `https://github.com/fastino-ai/GLiNER2/releases/tag/v2.1.0`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



## 1. Record instance formation and field-to-instance assignment

GLiNER2.5's structured extraction subsystem supports three record-formation strategies, rather than requiring every grouped extraction to originate from a predefined anchor field. These mechanisms constitute a separate learned prediction problem from detecting spans and differ in how record identities are established.

### 1.1 Natural, latent, and anchorless formation

All three modes ultimately produce instance representations, object-selection scores, and field-to-instance assignments. They differ in how candidate instances are generated.

| Mode         | Instance formation                                                                                    | Principal distinction                                              |
| ------------ | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `natural`    | Each detected mention of a designated anchor field provides a potential record instance               | Record identities are grounded in an explicitly selected field     |
| `latent`     | A learned selector scores candidate mentions across the record's fields as possible instance seeds    | The model can choose a useful anchor without the schema naming one |
| `anchorless` | Learned, document-conditioned instance queries predict records and select associated field candidates | An instance need not correspond to a single anchoring mention      |

The implementation resides in `RecordHead`, with declarative specifications compiled into `RecordSpec` and `RecordFieldSpec`. The record head consumes representations derived from the existing boundary candidates rather than independently enumerating a second dense span grid.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



#### Natural formation

In natural mode, the model begins with candidates for a particular anchor field. Each candidate can seed a record, and other field candidates are scored against those instances.

This is useful when documents repeatedly describe objects having a stable identifying field: transactions with transaction identifiers, agreements with named parties, or events with explicit triggers.

The instance's existence depends on the anchor-candidate path. A missed anchor can therefore prevent an otherwise recognizable record from being formed. The model exposes separate anchor-proposal and final-selection thresholds, allowing the candidate set considered for record formation to differ from the final set of accepted instances.

The schema builder allows an explicit `anchor`, but if none is supplied for `mode="natural"`, the first declared field is selected by default. Consequently, field declaration order has additional semantics in this mode.

#### Latent formation

Latent mode removes the requirement for a particular field to act as the anchor.

The learned `latent_seed_head` scores candidate mentions as potential instance seeds. Each selected seed provides an instance representation against which the remaining field values can be assigned.

This supports structures where several fields might identify an instance, but no single field is consistently present or reliable. For example, a document might identify one event by its date, another by an involved organization, and another by an action description.

The model still depends on a detected candidate to seed an instance. If the evidence needed to distinguish two records is not represented among the candidates, latent formation cannot invent that missing evidence.

#### Anchorless formation

Anchorless mode uses a fixed capacity of learned instance queries, controlled by `record_instance_queries`.

Each query develops a document-conditioned representation by attending to field-candidate states. The instance head then produces an object-versus-no-object score and field assignment scores for each potential instance.

This separates the concept of a record from the requirement that one particular source span identify it. It is useful for repeated structured descriptions whose identities emerge from combinations of evidence rather than an obvious anchor.

However, anchorless does not mean source-independent. Field values still come from the model's candidate set. The learned queries provide potential record identities and grouping, not an unrestricted mechanism for generating novel field content.

The instance-query budget also bounds the number of simultaneously representable instances. Increasing it changes model capacity and associated parameters; it should not be treated as an arbitrary inference-only expansion for existing checkpoint weights.

Record count is derived from the accepted decoded instances, rather than obtained directly from a separate count prediction. The boundary model's per-query count head, discussed later, serves a different purpose.

Source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/records.py`

### 1.2 Record field cardinality, absence, and exclusivity

Record mode adds explicit assignment semantics beyond the `dtype="str"` and `dtype="list"` output shapes.

Each field can declare one of four cardinalities:

| Cardinality    | Intended assignment semantics               |
| -------------- | ------------------------------------------- |
| `optional_one` | Zero or one candidate; absence is permitted |
| `required_one` | One candidate is required by the schema     |
| `zero_or_more` | Any number of candidates, including none    |
| `one_or_more`  | At least one candidate is required          |

Scalar assignments are scored with an explicit `ABSENT` alternative. List fields support selection of multiple candidates, with thresholds determining which survive.

The `exclusive=True` option adds a consequential cross-instance constraint: a candidate assigned to one instance should not also be assigned to another instance for the same exclusive field.

The implementation handles these requirements differently for scalar and list fields. For exclusive scalar fields, it constructs a global assignment problem and uses a linear assignment solver to distribute candidates among instances. For exclusive list fields, it allocates an accepted candidate to its strongest instance.

This is more capable than independently selecting the highest-scoring field value for every record. Independent selection can assign the same quantity, date, or participant to several instances even when the document contains distinct values.

The global assignment mechanism can reduce that error without requiring an external record-reconciliation algorithm.

There is an important qualification: cardinality requirements and assignment scoring do not guarantee that the necessary evidence exists. In an under-capacity or missing-candidate situation, even a `required_one` field can fail to obtain a valid value. These constraints express intended decoding semantics, not the truth or completeness of the source document.

### 1.3 Repeated occurrences and ambiguous supervision

Record training must distinguish the identity of a value from its surface string.

A field value such as `"Acme"` might occur in several records. If supervision provides only the surface string, multiple textual occurrences can be plausible matches.

The record subsystem exposes `occurrence_policy` with four values:

| Policy               | Behavior                                                                |
| -------------------- | ----------------------------------------------------------------------- |
| `first`              | Uses the first matching occurrence for scalar supervision               |
| `error_on_ambiguous` | Rejects scalar annotations with multiple matching occurrences           |
| `all`                | Retains the available occurrences                                       |
| `latent_all`         | Retains possible occurrences for latent matching; default record policy |

In the boundary record preprocessing path, `all` and `latent_all` both preserve multiple matched spans for scalar target construction. The distinction should therefore not be interpreted as two universally different inference algorithms. These options primarily govern how ambiguous training annotations are handled.

List fields retain their detected values rather than applying the scalar occurrence reduction.

Explicit character offsets remain the more precise way to identify a particular source occurrence. Occurrence policies are useful when training examples originate from structured values or weakly aligned annotations.

Source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processing/boundary_preprocessing.py`

### 1.4 Schema composition and limitations

The schema builder exposes record mode, optional anchors, occurrence policies, field cardinality, and exclusivity in the existing `.structure()` and `.field()` interfaces.

An illustrative anchorless event schema is:

```
from gliner2 import AutoExtractormodel = AutoExtractor.from_pretrained(    "fastino/gliner2.5-base-v1")schema = (    model.create_schema()    .structure(        "event",        mode="anchorless",        occurrence_policy="latent_all",    )    .field("actor", dtype="str", cardinality="optional_one")    .field("action", dtype="str", cardinality="required_one")    .field("target", dtype="str", cardinality="optional_one")    .field("participants", dtype="list", exclusive=True))result = model.extract(text, schema, include_spans=True)
```

This illustrates a supported declarative interface, not a tested prediction or a guarantee of accurate anchorless grouping by the pretrained checkpoint.

The released GLiNER2.5 Base checkpoint declares `enable_records=True`, confirming that the record head is present. The actual extraction quality of a particular record-formation mode remains dependent on its learned supervision, candidate coverage, and decoding configuration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face



For latent and anchorless training, instance identity must also be reconciled with annotations that do not prescribe an ordering over records. The implementation includes cost-based record matching, allowing predicted instances to be associated with gold records without assuming that output slots correspond to record order.

This is particularly important for anchorless extraction, where learned instance slots have no inherent semantic identity before assignment.

Record formation therefore offers more than formatted JSON extraction: it provides a native model for instance discovery, mention assignment, missing values, and repeated-record disambiguation.

Primary sources:

`https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processing/records.py`

`https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/schema.py`

`https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/records.py`

## 2. Advanced boundary-head architecture and decoding controls

The sparse boundary extractor is not limited to independent per-query proposals and a fixed pair reranker. Its configuration exposes alternative candidate-pool organizations, optional representation modules, learned abstention and count signals, and multiple candidate-decoding strategies.

These features require a careful distinction between the defaults supplied by `BoundaryHeadSettings` and the configuration stored in a pretrained checkpoint.

### 2.1 Per-query versus shared candidate pools

`BoundaryHeadSettings.candidate_pool` accepts two modes:

`per_query` constructs candidates separately for each schema query. Each label has its own proposal-selection process, so a candidate that is highly relevant to one label but weak under another label's boundary scores may appear only in the first candidate set.

`shared` constructs a document-level pool of spans and scores the pooled candidates against the requested extraction queries. The same candidate span can therefore be evaluated for several labels without independently generating a complete span set for every query.

This changes the computational organization of extraction:

| Characteristic         | Per-query pool                             | Shared pool                                                            |
| ---------------------- | ------------------------------------------ | ---------------------------------------------------------------------- |
| Candidate organization | Separate candidates for each query         | Common candidate set                                                   |
| Candidate reuse        | Primarily within a query                   | Across queries                                                         |
| Proposal coverage      | Governed by per-query budgets              | Governed by pool size, boundary selection, and query coverage controls |
| Candidate interactions | Independent proposal pathways              | Optional pool-level candidate and query interaction                    |
| Main risk              | A query fails to propose its relevant span | A shared pool omits a span needed by one or more queries               |

Shared pooling is especially significant when many requested labels refer to overlapping textual evidence. It makes the representation of a candidate span less tightly coupled to the label that initially proposed it.

The implementation includes `pool_boundary_top_k`, `pool_size`, and `min_pool_per_query`. The last provides a mechanism for maintaining query coverage despite pooling, rather than allocating every candidate solely on global scores.

Optional candidate-attention and query-attention modules provide additional interactions. These are distinct from the shared pool itself; shared candidate generation does not require that either attention module be enabled.

### Released checkpoint behavior

The published configurations for both `gliner2.5-base-v1` and `gliner2.5-multi-v1` specify:

| Configuration                | Value       |
| ---------------------------- | ----------- |
| `candidate_pool`             | `"shared"`  |
| `pool_size`                  | `192`       |
| `min_pool_per_query`         | `8`         |
| `candidate_attention_layers` | `0`         |
| `query_attention_layers`     | `0`         |
| `candidate_budget`           | `192`       |
| `start_top_k` / `end_top_k`  | `24` / `24` |

Thus, shared candidate pooling is not merely a hypothetical experimental feature: it is present in these released checkpoints. The optional candidate/query attention layers, however, are disabled in their published configurations.

The defaults in the library's configuration class differ from these checkpoint-specific values. A reference should not infer active pretrained behavior from configuration-class defaults alone.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co+2



Checkpoint configurations:

`https://huggingface.co/fastino/gliner2.5-base-v1/blob/main/config.json`

`https://huggingface.co/fastino/gliner2.5-multi-v1/blob/main/config.json`

### 2.2 Learned abstention and candidate-count guidance

The boundary implementation can learn signals concerning both whether a query has any matching span and approximately how many matches are expected.

`enable_abstention` adds a learned signal for a query having no corresponding extraction. This separates absence of a relevant mention from merely having low scores for all currently proposed candidates.

`enable_count_head` adds a count-prediction mechanism, with the model output representing per-query Poisson log-rates rather than direct integer counts.

When `adaptive_threshold=True`, the decoder can supplement ordinary threshold-selected candidates with the highest-scoring additional candidates up to the predicted count. It takes the union of threshold hits and count-guided selections; it does not discard an already accepted candidate simply because the predicted count is smaller.

This can affect recall in dense documents where a fixed threshold retains too few matches. Conversely, inaccurate count predictions can introduce additional false positives.

These mechanisms do not create new span boundaries. They operate on the available candidate set, so they cannot recover a true mention that was excluded from proposal formation.

Both base and multilingual checkpoint configurations enable the abstention and count heads but set `adaptive_threshold=False`. Therefore, the existence of learned count predictions should not be mistaken for count-guided candidate selection being active by default.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 2.3 Representation enhancements within the boundary head

The boundary architecture contains optional representations that enrich the information available to candidate selection and reranking.

| Mechanism                            | Relevant configuration                                                | Functional significance                                                             |
| ------------------------------------ | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Span-content representation          | `enable_span_content`, `content_dim`                                  | Adds learned information about the content between candidate boundaries             |
| Rotary endpoint encoding             | `enable_rotary_endpoints`, `rotary_base`                              | Enriches endpoint representations with position-dependent structure                 |
| Boundary contextualization           | `boundary_attention_layers`, `boundary_attention_window`              | Adds contextual interactions among boundary representations                         |
| Query-conditioned interior evidence  | `query_conditioned_inside_weight`                                     | Makes interior support depend on the requested query                                |
| Endpoint difference features         | `endpoint_difference_features`                                        | Supplies additional information about the relationship between candidate endpoints  |
| Pair compatibility scoring           | `reranker_endpoint_compat`, `multihead_pair_compat_heads`             | Enriches the evidence used to assess candidate boundary pairs                       |
| Length-sensitive proposal adaptation | `boundary_top_k_alpha`, `boundary_top_k_max`, `boundary_top_k_bucket` | Allows candidate proposal counts to scale with input length under configured limits |

The published base and multilingual configurations enable span-content features, rotary endpoints, query-conditioned inside weighting, and endpoint-difference features. They also specify two boundary attention layers.

These extensions illustrate that sparse boundary prediction is a framework for generating and scoring candidates, not a single immutable scoring formula.

The operational boundary is checkpoint compatibility. Flags that alter parameter shapes or introduce modules must match the saved model's trained configuration. The loader explicitly rejects incompatible boundary-head weights, including mismatches involving candidate pooling, attention layers, representation features, record heads, and relation heads.

Changing such settings is therefore a model-construction or training decision, not automatically a safe inference-time tuning operation.

Source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/model.py`

### 2.4 Candidate budgets, abstention, and explicit-span rescoring

Candidate generation and candidate scoring can be separated, but the distinction becomes important in the shared-pool architecture.

The low-level `score_explicit_spans()` interface accepts caller-provided half-open token spans rather than discovering them through normal boundary proposals. With shared pooling, the implementation injects those explicit spans into the shared candidate pool and scores them using the shared scoring path.

This is useful when spans originate from deterministic parsing, another recognition model, or previously selected candidate boundaries.

It is not an unlimited scoring operation. The shared-pool implementation raises an error when requested explicit spans cannot fit within the available candidate pool. This introduces a capacity obligation that does not arise from simply passing a small number of candidates through an independent pair scorer.

Consequently, externally supplied candidates can bypass the ordinary proposal search, but they do not bypass all capacity restrictions of the scoring architecture.

Source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/model.py`

## 3. Specialized checkpoint families

The `gliner2` package supports several task-specialized checkpoints beyond the three general-purpose GLiNER2.5 boundary models. These expand the range of operations available through the library but must not be interpreted as equivalent model architectures.

### 3.1 GLiNER2.5-Decide-1B

`fastino/GLiNER2.5-Decide-1B` is a roughly one-billion-parameter English classification specialist. Its model card describes schema-conditioned decisions such as intent classification, routing, sentiment, document type, policy categorization, priority, urgency, and multi-label tagging.

The major architectural distinction is that Decide-1B is a `span` checkpoint, not a GLiNER2.5 `boundary` checkpoint.

Its configuration identifies:

- `architecture="span"`
- `model_name="jhu-clsp/ettin-enc-from-dec-1b"`
- A ModernBERT-family encoder configuration with 28 transformer layers and alternating full/sliding attention layers
- A legacy-style `span_head`, including `max_width=8`

This also makes Decide-1B fundamentally different from the 340M English Decide model, which uses DeBERTa-v3-large, and the multilingual Decide model, which uses the boundary architecture.

Despite the shared naming, these checkpoints do not have identical extraction heads or architectural capabilities. In particular, Decide-1B's checkpoint designation does not establish support for the boundary-only record-instance and joint-relation mechanisms discussed elsewhere.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

fastino/GLiNER2.5-Decide-1B at main+2



#### Published classification evaluation

Fastino reports exact-match classification accuracy on `fastino/fast-decisions`, covering 17 English domains with 300 held-out examples per domain.

| Checkpoint             | Approximate size | Reported accuracy |
| ---------------------- | ---------------- | ----------------- |
| GLiNER2.5-Decide       | 340M parameters  | 60.2%             |
| GLiNER2.5-Decide-1B    | 1B parameters    | 59.6%             |
| GLiNER2.5-multi-Decide | 287M parameters  | 56.7%             |

The larger checkpoint does not outperform the 340M English model in this reported average. Domain-level behavior may differ, but the aggregate provides no basis for treating 1B as universally superior.

The evaluation is a developer-reported classification benchmark, not a comparison of general-purpose entity extraction, long-document processing, or relation extraction. Nor does the model's parameter count by itself establish latency or throughput for a particular device.

The 1B model's role is therefore best understood as a distinct, larger encoder-based classification specialist, with selection dependent on task-specific evidence and hardware constraints rather than the GLiNER2.5 name.

Sources:

`https://huggingface.co/fastino/GLiNER2.5-Decide-1B`

`https://huggingface.co/fastino/GLiNER2.5-Decide-1B/blob/main/config.json`

`https://huggingface.co/datasets/fastino/fast-decisions`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

fastino/GLiNER2.5-Decide-1B at main



### 3.2 GLiGuard: schema-conditioned safety classification

`fastino/gliguard-LLMGuardrails-300M` specializes the GLiNER2 span architecture for moderation and safety-related classification.

The checkpoint supports several task families, including prompt safety, prompt toxicity categories, jailbreak or prompt-attack detection, response safety, response toxicity, and refusal classification.

A single classification schema can request several of these judgments. Some are mutually exclusive, while others return multiple applicable labels.

This makes it possible to express multiple moderation questions as one schema-conditioned classification operation rather than requiring separate classifiers for every moderation category.

The model card distinguishes prompt-side and response-side evaluation. For response assessment, the input may include both the original prompt and the model response, allowing the classifier to evaluate the response in context.

These are learned safety classifications, not deterministic security guarantees. Thresholding, label definitions, input formatting, adversarial novelty, and differences between training and deployment distributions remain consequential.

The model card reports favorable benchmark and efficiency results relative to larger generative guardrail models, but those results are tied to the developer's evaluation workloads and should not be extrapolated to arbitrary safety policies.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

fastino/gliguard-LLMGuardrails-300M at main



Primary source: `https://huggingface.co/fastino/gliguard-LLMGuardrails-300M`

### 3.3 Multilingual PII extraction

`fastino/gliner2-privacy-filter-PII-multi` is a specialized span checkpoint for personally identifiable information detection.

The upstream documentation describes 42 supported PII entity types across seven languages: English, French, Spanish, German, Italian, Portuguese, and Dutch.

It uses the familiar entity-extraction interface, allowing a subset of the supported labels to be requested while preserving source-text offsets.

This is different from document-level privacy classification. The model identifies the textual occurrences that may contain sensitive information, enabling downstream systems to apply masking, redaction, replacement, or review policies.

The detection and redaction operations remain separate. GLiNER2 does not guarantee that every sensitive item has been recognized, and span extraction alone does not apply a comprehensive privacy policy.

Primary source: `https://huggingface.co/fastino/gliner2-privacy-filter-PII-multi`

### 3.4 Combined safety and PII checkpoint

`fastino/GLiNER2-Guardrails-PII-Multi` combines safety classification and PII recognition in one checkpoint.

Its distinctive capability is allowing entity extraction and safety classification to share the model execution context, producing structured privacy findings alongside moderation labels.

For workloads requiring both kinds of signal, this can avoid loading two unrelated encoder models solely to detect sensitive spans and classify surrounding text.

The combined checkpoint should nevertheless be evaluated as its own specialized model. Combining task capabilities into one checkpoint does not establish that it retains the accuracy of two independently specialized models under every label set.

All three safety/PII checkpoints described here use the older span architecture, not the GLiNER2.5 boundary head.

Primary tutorial: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/tutorial/16-safety_pii.md`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 4. Advanced training objectives, diagnostics, and distributed execution

The GLiNER2.5 training system exposes mechanisms specifically designed to address the statistical and computational challenges introduced by sparse candidate proposals, mixed supervision, and record-instance formation.

These capabilities are more consequential than ordinary optimizer hyperparameters because they affect whether the model can learn from a correctly annotated example at all.

### 4.1 Gold-candidate injection and proposal-recall training

Sparse candidate selection creates a training dependency: if a correct annotated span is absent from the proposal set, the downstream pair reranker cannot receive direct positive supervision for that span.

The boundary trainer addresses this through scheduled gold-candidate injection.

Relevant `TrainingConfig` fields are:

| Setting                     | Function                                                        |
| --------------------------- | --------------------------------------------------------------- |
| `gold_injection_start`      | Initial probability of injecting gold candidates                |
| `gold_injection_end`        | Final injection probability                                     |
| `gold_injection_hold_frac`  | Initial fraction of training progress held at the starting rate |
| `log_proposal_metrics`      | Collects candidate-generation diagnostics                       |
| `diagnostics_every_n_steps` | Controls the diagnostic collection interval                     |

The trainer holds the initial injection probability during the configured early period, then linearly interpolates toward the final probability.

This gives the pair scorer access to positive examples during early learning, even when the untrained or partially trained boundary proposer cannot reliably discover them.

The important distinction is between learning a good score for a supplied candidate and learning to propose that candidate without assistance.

High downstream accuracy under injected-gold training does not alone establish high inference recall. For that reason, GLiNER2.5 includes a separate proposal-recall diagnostic path.

### 4.2 Injection-free recall validation

`dry_run_recall_steps` enables a diagnostic pass that evaluates candidate proposals with `gold_injection_prob=0.0`, without updating model parameters.

It reports proposal-recall statistics and applies optional gates, including:

- `gate_recall`: minimum overall proposal recall.
- `gate_long_recall`: minimum recall for longer mentions, using the implementation's 9-plus-token length bucket.

The default configured thresholds are 0.97 and 0.93, respectively. These are validation settings, not published guarantees that the pretrained models meet those thresholds on arbitrary corpora.

When this dry-run mode is enabled, the trainer performs the recall assessment and returns its metrics if the gates pass, or raises an error if they fail. It does not proceed into the ordinary weight-update loop.

The implementation can also collect diagnostics for the alternative candidate-pool mechanism, making it possible to examine proposal differences between the shared and per-query pathways without confusing them with reranker performance.

This is a valuable diagnostic distinction: a boundary proposal failure, a pair-scoring failure, and a final decoding failure are separate error classes. Native instrumentation makes the first of these directly observable.

Source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/training/trainer.py`

### 4.3 Gold-capacity safeguards and strict training invariants

The boundary trainer exposes `on_capacity_exceeded`, with three policies:

| Policy                  | Effect                                                     |
| ----------------------- | ---------------------------------------------------------- |
| `raise`                 | Stops when annotated targets exceed the supported capacity |
| `truncate_with_warning` | Continues with target truncation while reporting the loss  |
| `skip_sample`           | Excludes the overflowing sample                            |

The default is `raise`.

This matters because a training batch can be computationally valid while silently omitting positive targets if its representation capacity is exceeded. Such omissions change the actual supervised objective.

`max_gold_per_query` and `training_candidate_budget` constrain how many gold candidates can be represented during training. Capacity errors should be interpreted as limitations of the configured training representation, rather than as evidence that the source annotation is incorrect.

Related controls include `strict_training`, `ignore_nonfinite_losses`, `skip_step_errors`, and `allow_invalid_samples`.

Strict training propagates processing and model errors, detects unexpected batch-size discrepancies, and raises on nonfinite losses unless an explicit alternative policy is selected.

The skip-error facility is intentionally more restricted under distributed execution, where skipping a step on only one worker could desynchronize collective operations.

These mechanisms allow a training run to distinguish malformed examples, insufficient target capacity, and numerical instability from ordinary model-learning errors.

### 4.4 Boundary loss families and negative supervision

The boundary head supports several objective families beyond conventional positive span supervision.

| Objective family      | Mechanism                                            | What it trains                                        |
| --------------------- | ---------------------------------------------------- | ----------------------------------------------------- |
| Boundary marginals    | Weighted BCE or asymmetric focal loss                | Start, end, and interior evidence                     |
| Candidate ranking     | Pair scoring, hard negatives, and listwise reranking | Distinguishing correct spans from competing proposals |
| Proposal learning     | Proposal-specific loss                               | Candidate discovery before reranking                  |
| Consistency           | Marginal/pair consistency objectives                 | Agreement between scoring components                  |
| Soft overlap          | Auxiliary soft-IoU objective                         | Approximate boundary alignment                        |
| Abstention            | Null/absence supervision                             | Recognition that a query has no matching span         |
| Count prediction      | Count-related objective                              | Expected number of matching candidates                |
| Records and relations | Dedicated assignment and relation losses             | Structural predictions beyond individual spans        |

These objectives are not interchangeable. For example, improving pair ranking among supplied candidates does not automatically improve boundary proposal recall.

The configuration exposes `boundary_marginal_loss="bce"|"asymmetric_focal"`, positive and negative focal parameters, negative-boundary weighting, hard-negative sampling budgets, and `loss_reduction="global"|"per_query"|"sum"`.

The last distinction affects the weighting of queries and samples. A global normalization and a sum reduction can produce different gradient magnitudes and relative contributions when documents contain different numbers of queries or positive mentions.

The published base checkpoint configuration uses asymmetric focal boundary loss, reduced negative-boundary weighting, and `loss_reduction="sum"`. These are training-configuration facts associated with the released checkpoint, not evidence that those choices are universally optimal.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



#### Training-time objective schedules

The trainer additionally adjusts some objectives over training progress.

Consistency loss uses a warmup controlled by `consistency_warmup_steps`. Auxiliary soft-IoU supervision is annealed toward zero according to `soft_iou_anneal_steps`.

These schedules can allow different components to develop before the full consistency objective applies, while reducing reliance on softer boundary-overlap supervision later in training.

The architecture therefore offers more than static multitask loss weighting: it supports changes in the optimization objective over the course of specialization.

Source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/configuration.py`

### 4.5 Distributed training and execution efficiency

`ExtractorTrainer` includes a native PyTorch `DistributedDataParallel` pathway. The training configuration exposes `local_rank`, `ddp_consensus_check`, `ddp_find_unused_parameters`, and `ddp_static_graph`.

When distributed execution is configured, the trainer initializes the NCCL process group, assigns the local CUDA device, wraps the model in `DistributedDataParallel`, and coordinates rank-aware operations.

Its gradient accumulation path uses `no_sync()` for intermediate microbatches so gradient synchronization is deferred until the appropriate accumulation boundary.

This can reduce unnecessary communication compared with synchronizing gradients after every microbatch.

Several other controls are relevant to throughput and memory:

- `group_by_length` and `length_group_window_batches` reduce padding waste by grouping similarly sized inputs.
- `fused_optimizer`, `allow_tf32`, and `float32_matmul_precision` expose lower-level PyTorch execution choices.
- `compile_model` and `gradient_checkpointing` address computation overhead and activation-memory tradeoffs.
- `profile_first_n_steps`, `debug_global_steps`, and diagnostic intervals support investigation of training execution and preprocessing.

The distributed path depends on a compatible CUDA/NCCL environment. It should not be equated with universal multi-device support across CPU, CUDA, and MPS.

Source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/training/trainer.py`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 4.6 DoRA and the PEFT-backed adapter implementation

In addition to conventional LoRA, `TrainingConfig` includes `lora_use_dora`, enabling a DoRA-style adaptation option through the package's PEFT-backed adapter implementation.

DoRA augments the usual low-rank weight update with magnitude-related adaptation rather than relying only on the low-rank directional update.

The relevant training configuration includes `use_lora`, `lora_r`, `lora_alpha`, `lora_dropout`, `lora_target_modules`, and `lora_use_dora`.

This option can alter the adaptation parameterization, trainable state, and resulting adapter compatibility. It is not an independent pretrained model family or a guarantee of better specialization accuracy.

The implementation uses the companion `peft` package. Several older GLiNER2-specific LoRA helper abstractions are retained for compatibility but emit `PendingDeprecationWarning`, with newer code directed toward the model's `apply_lora()` interface and PEFT adapter serialization.

An adapter's target modules, architecture, and required PEFT functionality remain part of its compatibility contract.

Primary source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/training/lora.py`

### 4.7 Dataset introspection, validation, and annotation quality

`TrainingDataset` provides more than a container for JSONL examples.

The native utilities include `load()`, `validate()`, `validate_relation_consistency()`, `stats()`, and `print_stats()`.

The statistics surface summarizes entity counts, classification tasks and labels, structure and relation types, text lengths, and the distribution of single-task versus multitask examples.

This helps distinguish dataset composition from model performance. For example, a corpus with many classification-only examples and few relation examples supplies different supervision to the shared model than a balanced multitask corpus.

`validate()` checks that annotated entities, relation values, and structure-field values can be located in the original text, using case-insensitive matching.

Its actual signature in package 2.1.0 is:

```
from gliner2.training.data import TrainingDatasetdataset = TrainingDataset.load("training.jsonl")report = dataset.validate(raise_on_error=False)relation_errors = dataset.validate_relation_consistency()statistics = dataset.stats()
```

The validation report contains valid, invalid, and total counts, invalid example indices, and error details.

A release-specific qualification matters: some upstream tutorial examples still call `validate(strict=True)`. The `strict` argument is no longer accepted; validation is always strict. This mismatch is documented in upstream issue #185.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/training/data.py`

Issue: `https://github.com/fastino-ai/GLiNER2/issues/185`

## 5. Additional schema-conditioning and validation facilities

### 5.1 Classification schemas as richer model inputs

Classification schemas can carry more information than task names and candidate label strings.

The builder supports label-to-description mappings, `prompt`, `examples`, `class_act`, `cls_threshold`, and `top_k`.

These serve different roles.

Label descriptions supply semantic distinctions between candidate choices. This is particularly relevant when labels are short codes, internally defined categories, or closely related concepts.

Task prompts provide additional instructions about the classification question. The prompt is incorporated into the model-facing schema representation rather than serving as an external generative instruction to a language model.

Few-shot examples provide pairs of input text and classification labels that condition the model's interpretation of the task. They are inference-time schema content, not parameter updates or a replacement for supervised fine-tuning.

Activation selection, through `class_act`, specifies the scoring interpretation, including softmax and sigmoid behavior. It must remain consistent with whether the task represents mutually exclusive or independently selectable labels.

Thresholds and top-k limits are decoding controls. `cls_threshold` applies a selection floor, while `top_k` restricts the number of retained labels.

These facilities offer several ways to specialize a classification task without changing model weights, but their effects are conditional on the checkpoint's learned response to schema text. Additional descriptions or examples should not be assumed to improve every task.

Primary source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/schema.py`

### 5.2 Strict schema validation with Pydantic

The library implements `SchemaInput` and associated Pydantic models to validate externally supplied schema dictionaries.

These models cover classification tasks, entity definitions, structure fields, record modes, and related schema metadata. They use strict unknown-field rejection through Pydantic's `extra="forbid"` behavior.

Consequently, misspelled or unsupported configuration keys can produce explicit validation errors instead of being silently ignored.

This is distinct from the model's prediction-time extraction semantics.

Schema validation can establish that a declaration has an accepted syntactic and structural form. It cannot establish that the selected checkpoint understands the intended domain concepts, that a required field will be discovered, or that all declarations can be jointly satisfied on a given document.

The Pydantic models also should not be confused with unrestricted JSON Schema support. They validate the package's own schema language, whose supported field types and constraints are narrower than arbitrary JSON Schema specifications.

Primary source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/inference/schema_model.py`

### 5.3 Builder serialization and declarative configuration

`Schema.from_dict()` and `Schema.to_dict()` provide a representation that can be exchanged between configuration systems and Python model execution.

The 2.1.0 release expands this round-trip capability to include richer classification options, entity and relation metadata, field thresholds, record definitions, and entity-attribute declarations.

This enables the same extraction contract to be represented as Python builder operations or a validated data structure.

Two limitations remain important.

First, schema serialization captures declarations, not model weights or inference state. A serialized schema remains dependent on a compatible checkpoint.

Second, model-facing descriptions, prompts, examples, and label sets contribute to the encoded inference input. Modifying these values can change the representations being scored, meaning that previously computed encoder states are not necessarily reusable under a modified schema.

This is an important boundary for caching and separately scheduled encoder/decoder execution.

Source: `https://github.com/fastino-ai/GLiNER2/releases/tag/v2.1.0`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 6. Inference execution, client orchestration, and model lifecycle

### 6.1 Hosted API batching and long-document orchestration

The hosted API client provides more than single-request wrappers around Fastino's inference service.

`GLiNER2API`, also exported as `API`, includes client-side batch partitioning and long-document processing for entity extraction, classification, structured extraction, relations, and combined schemas.

Batch requests can be divided into smaller partitions using `batch_size`. Long-document methods split text into overlapping windows, issue inference requests, and merge results using client-side chunking logic.

These are client orchestration capabilities, not proof that the hosted service natively accepts unlimited-context documents or executes the same local checkpoint.

A significant operational feature is partial-failure reporting.

`GLiNER2APIError` contains `partial_results` and `failed_range`, allowing an exception from a partitioned batch to identify work completed before the failure and the input range associated with the failed partition.

This provides a stronger recovery contract than an exception containing only a message and HTTP status. It can support resuming or selectively retrying failed portions without automatically discarding successful earlier requests.

The client also exposes configurable request timeouts, retries, and specialized exceptions for authentication, validation, and server failures.

These mechanisms do not establish exactly-once execution or transactionality. Client-side retries, partial completion, and server-side effects remain separate concerns.

### 6.2 Local and hosted schema APIs are not equivalent

The hosted client's `SchemaAPI` and `StructureBuilderAPI` resemble the local schema builder but do not expose every local capability.

For example, the tagged hosted structure builder does not accept the local `mode`, `anchor`, `occurrence_policy`, `cardinality`, or `exclusive` parameters in its fluent interface.

Similarly, the API-based schema builder does not mirror the full local classification-conditioning interface.

The hosted builder also warns that local `RegexValidator` instances are unsupported and will be ignored.

This is an important distinction between client-method similarity and actual semantic parity.

The presence of a feature in the local `Schema` implementation does not guarantee that it is expressible through the hosted schema builder or supported by the model currently serving hosted requests.

Primary source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/api_client.py`

### 6.3 Runtime word segmentation and source-coordinate preservation

GLiNER2 uses an intermediate word-token representation before the underlying transformer tokenizer processes its input.

The library supplies `WhitespaceTokenSplitter` and `CharLevelSplitter`, together with the ability to provide a custom splitter.

The default whitespace splitter is regex-based rather than a simple call to Python's `str.split()`. It recognizes several structured token patterns and maintains original-string character positions.

The character-level splitter preserves certain Latin character runs while treating other non-whitespace characters individually. It provides an alternative for languages that do not use whitespace-delimited word boundaries.

A model can select a splitter at loading time or change it afterward:

```
model = AutoExtractor.from_pretrained(    "fastino/gliner2.5-multi-v1",    word_splitter="char",)model.set_word_splitter("whitespace")
```

A custom splitter must return `(token, start, end)` tuples with half-open character offsets referencing the original source string.

This matters for more than token counts. Word segmentation determines which boundaries are available for entity alignment, candidate scoring, and mapping predicted spans back to the source text.

The implementation preserves original coordinates while lowercasing token values. This avoids corrupting offsets when Unicode lowercase conversion changes string length.

Version 2.1.0 also corrects segmentation around combining marks and zero-width joiners, which is relevant to several Indic writing systems.

The splitter selection is runtime state, not necessarily part of checkpoint serialization. Saving and reloading a model without explicitly restoring a nondefault splitter can change segmentation behavior.

Changing the splitter can also change the statistical input distribution relative to the model's training data. It should not be interpreted as a guaranteed multilingual accuracy improvement.

Primary source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processing/word_splitter.py`

### 6.4 BF16 conversion and the meaning of quantization

The boundary model's `quantize()` method supports `"fp16"` and `"bf16"`.

```
model = AutoExtractor.from_pretrained(    "fastino/gliner2.5-base-v1",    map_location="cuda",)model.quantize("bf16")
```

The method converts the model's floating-point representation to the selected lower-precision dtype.

This is not equivalent to integer weight quantization, per-channel quantization, or a 4-bit compressed checkpoint format.

The loader's `quantize=True` convenience option selects FP16 by default. The explicit `quantize("bf16")` method provides additional precision control when supported by the execution environment.

BF16's larger exponent range can offer different numerical behavior from FP16, particularly for values spanning a broad dynamic range. However, performance and memory effects depend on the device, kernel implementations, and the model operations involved.

Source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/model.py`

### 6.5 Checkpoint serialization and internal export modes

`save_pretrained()` for a boundary model preserves the model configuration, underlying encoder configuration, tokenizer artifacts, and model weights in Safetensors format.

The saved architecture metadata is necessary for `AutoExtractor` to select the correct implementation when reloading.

This differs from adapter-only serialization, which preserves adaptation state and depends on a compatible underlying checkpoint.

The boundary configuration also exposes `export_mode="auto"|"streaming"|"vectorized"`.

These modes govern internal boundary-head execution strategies. In particular, the vectorized path can trade larger temporary tensor operations against streaming or blockwise processing. The configuration validates compatibility between these strategies and certain adaptive candidate-budget settings.

Despite the parameter name, this is not a model interchange or deployment export API.

The option does not establish ONNX graph export, TensorRT engine construction, OpenVINO conversion, or a separate non-PyTorch runtime.

Those would be distinct integration capabilities requiring explicit exporter, operator compatibility, and runtime support. A native ONNX execution path was not established in the verified 2.1.0 package sources.

Primary source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/configuration.py`

### 6.6 Public preprocessing as an extension point

Package 2.1.0 makes `SchemaTransformer.transform_record()` a public interface for single-record preprocessing.

Its signature accepts text, a schema, an optional maximum length, and an optional target-construction flag.

The method resolves the schema, normalizes input punctuation, and returns a `TransformedRecord` suitable for subsequent batching or serving operations.

This is useful when preprocessing and model execution must be managed separately, particularly for inspection or controlled construction of model inputs.

It is distinct from the high-level `extract()` interface and does not independently perform neural inference.

One subtlety is that the transformation may append terminal punctuation when the supplied string lacks it. This should be accounted for when comparing transformed representations with raw input text and interpreting coordinates.

The related `transform_and_format()` method provides a more general transformation path, while the public `transform_record()` explicitly follows the inference-oriented processing behavior.

Source: `https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/processor.py`

### 6.7 Native Hugging Face Transformers model integration

The published checkpoint configurations also advertise a native Transformers schema-extraction model interface.

Their metadata uses `model_type="gliner2"` and `architectures=["Gliner2ForSchemaExtraction"]`. The model cards provide loading examples using the Transformers class directly, while preserving the existing `AutoExtractor` loading path.

The associated Hugging Face model updates describe integration with a `schema-extraction` pipeline.

This creates a potential distinction between two integration surfaces: GLiNER2's package-specific, schema-oriented facade and the Transformers model/pipeline interface.

The integration metadata is present in published model configurations. However, full feature parity between the Transformers interface and the package's higher-level `Classifier`, `JointIE`, record-formation, and long-document facilities has not been established by that metadata alone.

Consequently, availability of a native Transformers loading class should not be interpreted as evidence that every GLiNER2 inference or decoding facility is available through standard Transformers pipeline calls.

Primary source: `https://huggingface.co/fastino/GLiNER2.5-Decide-1B/discussions/2`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

huggingface.co



## 7. Release-specific packaging qualifications and known issues

### 7.1 PyTorch-free base installation: declared design versus observed imports

The package intentionally separates the basic installation from local neural inference dependencies.

The base package declares lightweight dependencies for schemas, training-data handling, and hosted API access; the `local`, `train`, and optimized-attention extras add their corresponding runtime dependencies.

However, an open upstream issue reports a reproducible import failure with the base-only installations of versions 2.0.0 and 2.1.0.

The failure occurs because importing `gliner2` can transitively import processing and model modules that require PyTorch, even when the caller intends to use only the API client or schema objects.

The reported failure is:

```
ModuleNotFoundError: No module named 'torch'
```

The issue includes a reproduction using a clean virtual environment and identifies the eager import chain responsible for the problem.

This is a packaging/runtime discrepancy, not a limitation of the underlying schema or hosted API abstractions. It is therefore important to distinguish declared optional dependencies from verified import-time dependency isolation.

As of this research date, the issue remains open. No independent wheel execution was performed as part of this addendum.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Primary issue: `https://github.com/fastino-ai/GLiNER2/issues/193`

### 7.2 Model loading and optional extras

Local model inference requires the dependency profile supporting PyTorch and Transformers, conventionally installed through:

```
pip install "gliner2[local]"
```

The model cards are not entirely consistent about this requirement. Some show the base installation before examples that load checkpoints locally, even though the package's optional-dependency structure assigns that functionality to the local profile.

The package metadata accepts Transformers 4.43 through the 5.x series, with additional bounds for the DisentangledFlash integration.

These are dependency constraints, not guarantees of successful execution on every combination of Python version, accelerator backend, checkpoint, and Transformers release.

The 2.1.0 release additionally separates PEFT imports from ordinary inference and full-model training paths. PEFT is required when the applicable LoRA functionality is invoked, rather than necessarily being imported whenever the core model is loaded.

Primary sources:

`https://pypi.org/project/gliner2/`

`https://github.com/fastino-ai/GLiNER2/releases/tag/v2.1.0`

## 8. Cross-capability distinctions

The additional mechanisms described here expose several architectural relationships that are easy to miss when examining individual APIs.

Record formation and entity recognition share candidate evidence but solve different prediction problems. Better candidate generation can benefit record extraction, but accurate mention recognition does not itself establish correct record grouping. Latent and anchorless modes add learned instance selection and assignment rather than merely applying output formatting.

Shared candidate pools and joint decoding operate at different levels. Shared pooling reorganizes the evidence available to span scorers across queries. `JointIE` subsequently selects a coherent entity–relation graph under its declared structural constraints. Shared pooling can improve candidate reuse without enforcing graph consistency; joint decoding cannot restore facts excluded from candidate formation.

Training-time candidate injection and inference-time proposal recall must be evaluated separately. Gold injection provides positive training examples to the reranker. Injection-free diagnostics establish whether the independently operating proposal system can actually find the relevant boundaries.

Classification specialists and general-purpose extractors are not interchangeable solely because they share the `gliner2` interface. Decide-1B, the general GLiNER2.5 boundary checkpoints, and GLiGuard/PII models differ in encoder architecture, trained task distribution, enabled heads, and supported semantics.

Schema validity, model capability, and model accuracy are separate properties. A schema can pass Pydantic validation, be accepted by a particular inference API, and still request predictions for which the checkpoint lacks suitable learned representations or evidence. Likewise, satisfying a structural assignment constraint does not establish factual correctness.

The resulting capability picture is broader than independent entity and relation extraction. GLiNER2.5 provides configurable neural candidate discovery, learned instance formation, cross-field assignment, absence and count estimation, and multiple forms of structured decoding. Its training subsystem exposes corresponding supervision and diagnostic mechanisms, while its surrounding package supports specialized classification checkpoints and alternative deployment interfaces.

These mechanisms can reduce the amount of bespoke candidate generation, record association, validation orchestration, and model-coordination infrastructure required for some structured interpretation workloads. Their suitability ultimately depends on the distinction between implemented machinery, enabled checkpoint configuration, learned behavior, and runtime guarantees.