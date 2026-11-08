# Liquid AI d1-2B: Comprehensive Technical and Python Integration Reference

Research date: November 8, 2026 | Model: LiquidAI/d1-2B | Architecture: LFM3-VL

## 1. Executive overview

d1-2B is an open-weight, 1.92-billion-parameter multimodal decision model developed by Liquid AI. It represents a different approach to using language models for structured reasoning: rather than generating textual answers autoregressively, it evaluates a supplied state against one or more explicitly defined questions and returns typed answers, probabilities, or extracted values without generating output tokens.

Released as part of the LFM3 family on October 27, 2026, d1-2B replaces the earlier d1-3B, achieving higher aggregate decision-benchmark performance with approximately 38% fewer parameters.

It is particularly relevant to Python systems that require semantic classification, routing, extraction, ranking, evaluation, or decisions over text and visual inputs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.liquid.ai\&sz=32)

Liquid AI+2



Core specifications

| Property                   | d1-2B                                                                 |
| -------------------------- | --------------------------------------------------------------------- |
| Parameters                 | 1.92 billion                                                          |
| Base model                 | LFM3-VL-2B                                                            |
| Model architecture         | Hybrid convolution + local/global attention                           |
| Layers                     | 24                                                                    |
| Context window             | 128K tokens                                                           |
| Vocabulary                 | 128,000 tokens                                                        |
| Input modalities           | Text, JSON, images, video                                             |
| Output                     | Typed decisions, probabilities, extracted values, spatial coordinates |
| Inference                  | Single forward pass, no autoregressive decoding                       |
| Languages                  | 16                                                                    |
| License                    | LFM Open License v1.0                                                 |
| Primary Python integration | PyTorch + Hugging Face Transformers                                   |

Official resources:

- Model weights and model card: [https://huggingface.co/LiquidAI/d1-2B](https://huggingface.co/LiquidAI/d1-2B?utm_source=chatgpt.com)
- Official model documentation: [https://docs.liquid.ai/lfm/models/d1-2b](https://docs.liquid.ai/lfm/models/d1-2b?utm_source=chatgpt.com)
- Decision model family: [https://docs.liquid.ai/lfm/models/decision-models](https://docs.liquid.ai/lfm/models/decision-models?utm_source=chatgpt.com)
- LFM3 architecture announcement: [https://www.liquid.ai/blog/lfm3](https://www.liquid.ai/blog/lfm3?utm_source=chatgpt.com)

### 1.1 What makes d1-2B distinctive?

The model combines several capabilities that ordinarily require separate components:

- Probabilistic semantic classification: Ask arbitrary natural-language yes/no questions and receive estimated probabilities.
- Dynamic multiclass decisions: Define possible outcomes and their descriptions at inference time, without training a dedicated classifier for every taxonomy.
- Multilabel classification: Evaluate multiple nonexclusive categories and return a probability for each.
- Ordinal scoring: Evaluate ordered rubrics, retaining a distribution across score levels.
- Typed information extraction: Extract text, numeric values, and dates with source spans and explicit missing-value handling.
- Numerical estimation: Produce constrained numeric estimates with uncertainty intervals.
- Visual grounding: Identify objects with normalized bounding boxes, including multiple instances.
- Multimodal decision-making: Evaluate text, images, and video within the same decision interface.
- Multiquestion inference: Answer multiple questions about a shared state without separately processing that state for every question.

These features make d1-2B more than a general-purpose classifier and fundamentally different from a small instruction-tuned language model.

### 1.2 Important conceptual boundary

d1-2B is a model checkpoint with a specialized inference API, not a standalone general-purpose Python package.

Its main implementation interfaces are:

| Component                    | Responsibility                                                                            |
| ---------------------------- | ----------------------------------------------------------------------------------------- |
| `LiquidAI/d1-2B`             | Model weights, architecture, specialized decision heads, and inference implementation     |
| `transformers`               | Python model loading and execution interface                                              |
| `torch`                      | Tensor operations and CPU/GPU execution                                                   |
| `llama.cpp`                  | Alternative optimized GGUF inference engine with a smaller supported decision feature set |
| Python application libraries | Validation, persistence, orchestration, downstream calculations, and decision policies    |

The model does not replace a general LLM for free-form generation, code writing, arbitrary JSON synthesis, conversational agents, or extended reasoning. Its advantage comes from specializing the model's output interface around decisions and typed extraction.

## 2. Architecture and inference mechanism

### 2.1 The LFM3 hybrid backbone

d1-2B inherits the LFM3 architecture, which combines three sequence-processing mechanisms:

| Mechanism                | Layers | Contribution                                 |
| ------------------------ | ------ | -------------------------------------------- |
| Gated short convolutions | 13     | Efficient local sequence processing          |
| Sliding-window attention | 5      | Attention over a bounded local context       |
| Global attention         | 6      | Information exchange over long-range context |
| Total                    | 24     | Hybrid processing                            |

The sliding-window attention layers use a 256-token window; the convolution layers use a kernel size of seven.

LFM3 additionally introduces head-wise attention gating, partial rotary position embeddings in global attention, and normalization around both the input and output of each block. These design choices are intended to combine local computational efficiency with better long-range modeling.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.liquid.ai\&sz=32)

Liquid AI



The hybrid architecture matters for d1-2B because decision workloads often involve reading relatively large documents, JSON records, or multimodal contexts to produce only a few bytes of useful output.

Avoiding autoregressive decoding reduces the output-side inference workload, but the model must still process the input context. A 50,000-token document is therefore substantially more expensive to evaluate than a 100-token ticket.

### 2.2 How decision inference actually works

At a conceptual level, inference follows this process:

The implementation constructs a representation containing the state, each question's instructions, its candidate answers where applicable, and specialized answer positions called slots.

For closed-answer questions, the model reads probabilities over candidate answer tokens at the relevant slots. For extraction, it additionally uses positions in the source state; numeric estimates and bounding boxes use specialized discretized value readouts.

A key distinction is that the categories are defined at inference time. The model is not limited to a fixed label vocabulary learned by a traditional classification head. It evaluates the supplied descriptions and chooses between them.

The released implementation includes model-specific components such as `prompt.py`, `slots.py`, `pointer.py`, `box.py`, `calibration.py`, and `runner.py`. These components are part of the downloadable model code and not separate Python packages.

Source implementation:

[https://huggingface.co/LiquidAI/d1-2B/tree/main](https://huggingface.co/LiquidAI/d1-2B/tree/main?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main+2



### 2.3 Shared-state attention and grouped questions

One of the most important capabilities is that the model can evaluate several questions over a common state while avoiding independently processing the same state for every question.

For example, an invoice might need 12 separate outputs:

- Document type and sender
- Payment amount, currency, and due date
- Fraud indicators and missing information
- Exception severity and processing route

d1-2B allows those to be expressed as one question dictionary.

Internally, the model groups question suffixes after a shared state prefix, using a specialized attention arrangement. The checkpoint's default trained group size is 16 questions.

The implementation also accepts `set_size`, allowing that grouping behavior to be controlled.

An important qualification to the single-pass description: while the API accepts arbitrarily many named questions, questions beyond the grouping capacity may require additional processing passes. Increasing `set_size` can improve speed but is documented to reduce text accuracy somewhat because it moves beyond the model's trained grouping configuration.

This makes the native multiquestion interface especially valuable when several related decisions refer to the same expensive input.

Source: [https://huggingface.co/LiquidAI/d1-2B/blob/main/runner.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/runner.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



## 3. Complete typed-decision capability map

d1-2B supports eight question types, with one type (`choice`) also supporting a multilabel mode.

| Type                  | Semantic operation                | Main output                                     |
| --------------------- | --------------------------------- | ----------------------------------------------- |
| `noul`                | Binary semantic question          | Probability of yes                              |
| `choice`              | Mutually exclusive classification | Selected label and distribution                 |
| `choice` + `multiple` | Multilabel classification         | Selected labels and independent probabilities   |
| `score`               | Ordinal scoring                   | Level, confidence, distribution                 |
| `text`                | Extract source text               | Text, source span, found probability            |
| `number`              | Read numeric data                 | Parsed number, unit, original text, source span |
| `date`                | Read a date                       | ISO date, original text, source span            |
| `number` + `range`    | Constrained numerical estimation  | Estimated value and interval                    |
| `box`                 | Locate one visual object          | Normalized coordinates and confidence           |
| `boxes`               | Locate multiple instances         | Ordered bounding boxes and count                |

Source: [https://docs.liquid.ai/lfm/models/decision-models](https://docs.liquid.ai/lfm/models/decision-models?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.liquid.ai\&sz=32)

Liquid AI Docs



### 3.1 Binary decisions: `noul`

A Noul question evaluates whether a proposition is supported by the supplied state.

```
question = {    "type": "noul",    "instructions": "Does this document contain a payment request?",}result = model.system_one(    "Please remit payment within 30 days.",    {"payment_request": question},)p_yes = result["answers"]["payment_request"]["noul"]
```

Unlike a conventional boolean classifier, the model retains a continuous probability.

That enables confidence-based routing, risk-sensitive policies, and abstention without requiring a separate uncertainty-estimation model.

For example, an application could use a high threshold for automatically accepting a potentially harmful action, and escalate ambiguous cases.

The thresholds are application-level policy decisions, not a universal property of the model.

### 3.2 Multiclass decisions: `choice`

A Choice question selects among named categories.

```
question = {    "type": "choice",    "instructions": "What is the primary document type?",    "criteria": {        "invoice": "A bill requesting payment",        "contract": "A legally binding agreement",        "receipt": "Confirmation of a completed purchase",        "other": "None of the listed document types",    },}
```

Its answer contains:

- `choice`: the selected category identifier.
- `confidence`: probability assigned to the selected category.
- `probabilities`: the probability distribution across all candidates.

The descriptions associated with identifiers are important. They allow categories to be differentiated semantically, rather than relying entirely on potentially ambiguous label names.

This is closed-set classification. If none of the supplied classes is appropriate, the model does not automatically create an alternative class. An explicit `other`, `unknown`, or `insufficient_evidence` option can make the decision space more representative, although such an option must itself be evaluated for reliability.

### 3.3 Multilabel decisions

The `multiple` modifier changes a Choice question from selecting exactly one category to evaluating each category independently.

```
question = {    "type": "choice",    "multiple": True,    "instructions": "Which subjects appear in this document?",    "criteria": {        "pricing": "Prices, discounts, or billing",        "delivery": "Shipment, transport, or delivery dates",        "legal": "Legal terms, liabilities, or obligations",    },}answer = model.system_one(    "The delivery is late, and the invoice includes an incorrect fee.",    {"topics": question},)["answers"]["topics"]labels = answer["choices"]probabilities = answer["probabilities"]
```

Each category has its own probability of being applicable. These probabilities are not a softmax distribution across mutually exclusive labels, and therefore need not sum to one.

The returned `choices` uses a default inclusion threshold of 0.5. The raw probabilities allow the caller to apply different thresholds when needed.

This is suitable for tagging, policy rule detection, and overlapping entity or attribute categories.

### 3.4 Ordered scoring: `score`

A Score question represents an ordered set of levels, not independent categories.

```
question = {    "type": "score",    "instructions": "Assess the severity of this operational incident.",    "criteria": [        "Negligible: no material impact",        "Minor: localized impact",        "Major: significant service interruption",        "Critical: widespread service outage",    ],}
```

The model supports 2–10 levels.

Internally, it produces a distribution over those levels. The default returned `score` is the median level of that distribution.

The model's implementation exposes three score readout strategies:

| Strategy | Interpretation                                          | Useful property                           |
| -------- | ------------------------------------------------------- | ----------------------------------------- |
| `median` | First level at which cumulative probability reaches 0.5 | Minimizes expected absolute ordinal error |
| `mean`   | Probability-weighted expected level                     | Preserves intermediate values             |
| `argmax` | Most probable individual level                          | Returns the modal category                |

These are materially different. An ordinal median is not necessarily the most probable individual level, and a probability-weighted mean need not correspond to any actual rubric category.

The `confidence` field in the implementation reflects the highest individual level probability; it should not automatically be interpreted as confidence in the returned median.

Source: [https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



### 3.5 Source-grounded extraction: `text`, `number`, and `date`

These question types extract values that appear in the input rather than generating an answer.

Example:

```
questions = {    "supplier": {        "type": "text",        "instructions": "Who issued the invoice?",    },    "amount": {        "type": "number",        "instructions": "What is the total amount due?",    },    "due_date": {        "type": "date",        "instructions": "When is the payment due?",    },}
```

These types offer several important properties:

Source spans. The model returns the location of the extracted text, supporting traceability back to the input.

Missing-value detection. The `found` field indicates the probability that the requested value was located. The implementation treats values below 0.5 as absent and sets their values to `None`.

Numeric normalization. Numbers can be parsed from localized representations and retain a unit and original source text.

Date normalization. Dates can be normalized into ISO 8601.

JSON provenance. When the input state is JSON, extracted values can additionally include a `path` field containing an RFC 6901 JSON Pointer to their origin.

The distinction between extraction and computation is critical: the model's numeric and date readers are designed to read written values, not perform arbitrary arithmetic, unit conversion, or invent missing components. A value may be found while its parsed representation remains `None` if parsing is unsuccessful.

Source: [https://huggingface.co/LiquidAI/d1-2B/blob/main/parsing.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/parsing.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main+1



### 3.6 Numerical estimation and uncertainty intervals

Providing a `range` changes `number` from an extraction question into an estimation question.

```
question = {    "type": "number",    "instructions": "How many individual components are visible?",    "range": [0, 40],    "step": 1,}
```

The model evaluates a discrete numeric grid and returns a median estimate and an interval defined by the 10th and 90th percentiles.

This supports constrained estimates such as counts, ratings, or bounded quantities.

Important constraints:

- At most 128 numeric grid values are evaluated.
- `step` must be positive and evenly divide the requested range.
- Estimates do not have `found` or source spans.
- The interval is model-derived uncertainty, not a formal statistical guarantee.
- Liquid AI explicitly reports weaker reliability for unconstrained quantities than for counts and scores.

A numerical estimate should not be confused with an exact numeric extraction, calculation, or measurement.

### 3.7 Visual grounding: `box` and `boxes`

The model supports two distinct spatial decision operations:

`box` locates one described visual entity.

`boxes` identifies multiple instances of a described entity, returning an ordered collection and the number detected.

Bounding box coordinates are expressed as fractions of image dimensions:

```
{    "top": 0.15,    "bottom": 0.24,    "left": 0.06,    "right": 0.28,}
```

This is useful for locating objects from natural-language descriptions without requiring a separate fixed-class detector.

The important limitations are that spatial questions require exactly one image, and the multi-instance reader supports at most 16 instances per question. It returns `at_least` to indicate that additional instances may be present beyond the reported detections.

Image grounding can be combined with document classification or numerical count questions in one request, but it is not a general replacement for segmentation, dense OCR, document layout reconstruction, or specialized object detectors.

Source: [https://docs.liquid.ai/lfm/models/d1-2b](https://docs.liquid.ai/lfm/models/d1-2b?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.liquid.ai\&sz=32)

Liquid AI Docs+1



## 4. Python integration: the native Transformers interface

For the complete d1-2B feature set, the official Hugging Face Transformers implementation is the primary Python interface.

### 4.1 Installation and model loading

The official minimum requirement is Transformers 5.19.

```
uv add "transformers>=5.19" torch torchvision pillow

# Or, in an existing Python environment:
pip install "transformers>=5.19" torch torchvision pillow
```

Load the model using `AutoModel`, not `AutoModelForCausalLM`:

```
import torchfrom transformers import AutoModelMODEL_ID = "LiquidAI/d1-2B"device = (    "cuda" if torch.cuda.is_available()    else "mps" if torch.backends.mps.is_available()    else "cpu")dtype = torch.float32 if device == "cpu" else torch.bfloat16model = AutoModel.from_pretrained(    MODEL_ID,    trust_remote_code=True,    dtype=dtype,).to(device)model.eval()
```

The `trust_remote_code=True` requirement is consequential. The checkpoint supplies custom Python code implementing the decision interface and its model-specific inference machinery. It is not merely a conventional Transformer with different weights.

For production deployments, inspect and pin a specific checkpoint commit, including its custom code and calibration artifacts, rather than automatically tracking the mutable `main` revision.

Official instructions: [https://docs.liquid.ai/lfm/models/d1-2b](https://docs.liquid.ai/lfm/models/d1-2b?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.liquid.ai\&sz=32)

Liquid AI Docs



### 4.2 A complete multiquestion classification example

The example below shows several types of semantic analysis performed in the same invocation.

```
ticket = {    "subject": "Duplicate charge and delayed order",    "message": (        "My credit card was charged twice for order 417. "        "The delivery is also four days late. "        "Please refund the extra charge."    ),    "customer_tier": "business",}questions = {    "refund_requested": {        "type": "noul",        "instructions": (            "Has the customer explicitly requested a refund?"        ),    },    "primary_team": {        "type": "choice",        "instructions": (            "Which team should own the initial resolution?"        ),        "criteria": {            "billing": "Payments, refunds, invoices, and charges",            "logistics": "Shipping, tracking, and delivery problems",            "technical": "Application, account, or website defects",        },    },    "issue_tags": {        "type": "choice",        "multiple": True,        "instructions": (            "Which independently applicable problems are described?"        ),        "criteria": {            "duplicate_charge": "A payment was charged more than once",
```

This example is illustrative and has not been executed here.

Several implementation distinctions matter:

1. The input `state` can be a Python string, a JSON-compatible structure, or `None` when the media alone constitutes the state.
2. Each entry in `questions` is independently named, making the results straightforward to correlate with application logic.
3. The model returns typed Python dictionaries; it does not require JSON parsing of generated text.
4. The caller receives both the selected classification and its probability distribution.
5. `usage` reports input tokens and zero output tokens because the model does not autoregressively generate a response.

The returned values can then be validated or transformed into application-specific Pydantic models or typed dataclasses. Such validation is performed by the Python application, not by d1-2B itself.

### 4.3 Batch inference over many states

`system_one_batch` is an important native capability that should be distinguished from merely running a Python loop over `system_one`.

```
states = [    "My order has not arrived.",    "The application crashes during checkout.",    "Please send a corrected invoice.",]routing_question = {    "team": {        "type": "choice",        "instructions": "Which team should handle this request?",        "criteria": {            "billing": "Payment, invoices, refunds",            "shipping": "Delivery and logistics",            "technical": "Application problems and bugs",        },    }}requests = [    (state, routing_question)    for state in states]results = model.system_one_batch(requests)for state, result in zip(states, results, strict=True):    route = result["answers"]["team"]    print(state, route["choice"], route["confidence"])
```

Batch requests can contain either `(state, questions)` or `(state, questions, media)` tuples. Each request retains its own state and question collection.

The implementation also includes packing, scheduling, and token-budget machinery. This matters because the work represented by a batch depends on both the number of inputs and their lengths. Many short records and a few very long documents impose different compute and memory demands.

The two orthogonal forms of amortization are:

- Multiple questions per state: Share processing of a common context.
- Multiple states per batch: Improve hardware utilization by processing requests together.

They can be combined.

Source: [https://huggingface.co/LiquidAI/d1-2B/blob/main/runner.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/runner.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



### 4.4 Compilation and execution tuning

The model exposes a dedicated `compile()` method:

```
model.compile()
```

This compiles the parts of the inference engine that run `system_one`, using PyTorch compilation and fused kernels.

It can improve warm inference, but the first compilation can be expensive, and the improvement depends on workload, hardware, dynamic input sizes, and batching. Compilation is therefore more relevant to persistent, high-throughput processes than one-off scripts.

Another option is `set_size`:

```
output = model.system_one(    ticket,    questions,    set_size=16,)
```

This controls how many questions can be read together after the shared state. The default matches the model's training configuration. Larger values may increase speed at some cost to accuracy.

For ordinal scores, `score_readout` changes how the probability distribution is converted into a level:

```
median_result = model.system_one(    ticket,    {"severity": questions["severity"]},    score_readout="median",)mean_result = model.system_one(    ticket,    {"severity": questions["severity"]},    score_readout="mean",)modal_result = model.system_one(    ticket,    {"severity": questions["severity"]},    score_readout="argmax",)
```

These are supported model-specific options, not generic Transformer generation parameters.

Source: [https://huggingface.co/LiquidAI/d1-2B/blob/main/modeling_d1.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/modeling_d1.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



### 4.5 Typed extraction from Python documents

The following pattern combines extraction with explicit downstream validation:

```
document = """Supplier: Acme Components Ltd.Invoice: INV-2026-0417Total due: EUR 1,234.50Payment deadline: 15 November 2026"""fields = {    "supplier": {        "type": "text",        "instructions": "What company issued the invoice?",    },    "amount": {        "type": "number",        "instructions": "What is the total amount due?",    },    "deadline": {        "type": "date",        "instructions": "What is the payment deadline?",    },}result = model.system_one(document, fields)answers = result["answers"]def extract_found(answer: dict, key: str, threshold: float = 0.8):    if answer["found"] < threshold:        return None    return answer.get(key)record = {    "supplier": extract_found(answers["supplier"], "text"),    "amount": extract_found(answers["amount"], "number"),    "deadline": extract_found(answers["deadline"], "date"),    "amount_unit": answers["amount"].get("unit"),}
```

This illustrates the distinction between the model's own `found` threshold of 0.5 and a stricter application acceptance threshold of 0.8.

For values extracted from JSON, the optional `path` provides structural provenance. A pipeline can preserve this alongside source spans to keep extracted fields auditable.

A useful design property: source-grounded extraction makes it possible to verify that a claimed field corresponds to material in the input. That is stronger than simply asking a generative model to produce a plausible value, but it does not establish that the extracted value is semantically correct.

### 4.6 Image analysis and bounding boxes

```
from PIL import Imagephoto = Image.open("inspection.jpg").convert("RGB")questions = {    "damage_present": {        "type": "noul",        "instructions": "Is any visible component damaged?",    },    "component_count": {        "type": "number",        "instructions": "How many circular components are visible?",        "range": [0, 20],        "step": 1,    },    "target": {        "type": "box",        "instructions": "Locate the largest circular component.",    },}result = model.system_one(    None,    questions,    media=[photo],)answers = result["answers"]box_answer = answers["target"]if box_answer["box"] is not None:    box = box_answer["box"]    width, height = photo.size    pixel_bounds = (        round(box["left"] * width),
```

The normalized-to-pixel conversion is application code. If visual inputs are resized, cropped, or otherwise transformed before downstream analysis, coordinate mapping must account for those transformations.

For video, the native media interface also accepts video input constructed from frames and associated timing information. Actual processing cost depends on the representation and temporal sampling, and the model should not be assumed to inspect every frame of an arbitrarily long video.

Source: [https://huggingface.co/LiquidAI/d1-2B](https://huggingface.co/LiquidAI/d1-2B?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face



## 5. Other Python deployment paths

The deployment choice has unusually important functional consequences: not every engine implements all the typed answers supported by the full checkpoint.

| Runtime                | Target                            | Python interface                                                  | Decision capability coverage                        |
| ---------------------- | --------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------- |
| Transformers + PyTorch | CPU, CUDA, supported accelerators | `model.system_one`                                                | Full reference feature set                          |
| MLX-VLM                | Apple Silicon                     | `model.system_one`                                                | Broad typed interface, with quantized checkpoints   |
| llama.cpp              | CPU/GPU, GGUF                     | Python HTTP client to `/v1/systemone`                             | `noul`, single `choice`, `score`                    |
| ONNX Runtime           | CPU/GPU/WebGPU                    | ONNX session plus model-specific preprocessing and postprocessing | Model-specific low-level inference artifacts        |
| Liquid hosted API      | Remote cloud                      | `typesafe-sdk`                                                    | Hosted d1.1/d1-ultra, not the same d1-2B checkpoint |

### 5.1 llama.cpp and HTTP access from Python

Liquid AI has published GGUF weights for d1-2B, supported by llama.cpp 0.8.0 / build b11960 and later.

A server can be started using:

```
llama-server \
  -hf LiquidAI/d1-2B-GGUF:Q8_0 \
  -b 8192 \
  -ub 8192
```

The Python application can then call the native decision endpoint:

```
import requestspayload = {    "state": "I was charged twice this month.",    "questions": {        "refund": {            "type": "noul",            "instructions": "Is the customer requesting a refund?",        },        "team": {            "type": "choice",            "instructions": "Which team should investigate?",            "criteria": {                "billing": "Payment or invoice problems",                "technical": "Application faults",            },        },    },}response = requests.post(    "http://127.0.0.1:8080/v1/systemone",    json=payload,    timeout=60,)response.raise_for_status()answers = response.json()["answers"]print(answers["refund"]["noul"])print(answers["team"]["choice"])
```

The important endpoint is `/v1/systemone`, not the normal LLM chat-completions endpoint.

The server can evaluate text, JSON, images, and video, but its decision reader currently lacks multilabel Choice, typed text/number/date extraction, numerical estimates, and bounding boxes. Image inputs use the `images` request field, and video can be supplied through `files`.

The `-b` and `-ub` settings are also significant: a question and its media must fit into the configured batch budget. Too-small budgets can limit image processing.

Official GGUF checkpoint: [https://huggingface.co/LiquidAI/d1-2B-GGUF](https://huggingface.co/LiquidAI/d1-2B-GGUF?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face



### 5.2 MLX-VLM for Apple Silicon

Liquid AI supplies native MLX variants of the same decision model.

```
pip install -U "mlx-vlm>=0.7.11"
```

```
from mlx_vlm import loadmodel, processor = load("LiquidAI/d1-2B-MLX-8bit")result = model.system_one(    "The product arrived damaged.",    {        "damage": {            "type": "noul",            "instructions": "Does the customer report damage?",        }    },)print(result["answers"]["damage"]["noul"])
```

The important distinction is that `mlx_vlm.generate()` is not the correct interface for this checkpoint. The d1-specific interface is `system_one`.

Official quantized variants:

| Variant   | Approximate weight size | Liquid AI's reported validation                                    |
| --------- | ----------------------- | ------------------------------------------------------------------ |
| 4-bit MLX | 1.35 GB                 | 3 of 52 answers changed versus FP32; probability shifts up to 0.25 |
| 8-bit MLX | 2.22 GB                 | All 52 tested answers retained; maximum probability shift 0.008    |
| FP16 MLX  | Larger                  | Higher-precision deployment option                                 |

The substantial probability shift reported for 4-bit is especially important for applications that use calibrated risk thresholds. Weight quantization may preserve many category choices while materially changing confidence values.

Sources:

[https://huggingface.co/LiquidAI/d1-2B-MLX-4bit](https://huggingface.co/LiquidAI/d1-2B-MLX-4bit?utm_source=chatgpt.com)

[https://huggingface.co/LiquidAI/d1-2B-MLX-8bit](https://huggingface.co/LiquidAI/d1-2B-MLX-8bit?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face+1



### 5.3 ONNX Runtime for cross-platform integration

The ONNX export is more sophisticated than a conventional autoregressive language-model export.

Liquid AI supplies a decoder and a separately exported vision encoder, with several precision configurations:

| Variant | Total artifact size | Intended device |
| ------- | ------------------- | --------------- |
| `q4`    | 1.94 GB             | CPU             |
| `q8`    | 2.51 GB             | CPU             |
| `q4f16` | 1.95 GB             | GPU             |
| `q8f16` | 2.34 GB             | GPU             |
| `fp16`  | 3.90 GB             | GPU             |
| `fp32`  | 7.80 GB             | Reference       |

The decoder accepts model-specific tensors including `question_ids` and `slot_positions`, alongside token, attention, position, and media-feature inputs.

It returns answer-slot logits and hidden states. The checkpoint's Python code is required to construct the appropriate inputs and interpret those outputs as typed answers.

This makes ONNX particularly interesting for native applications, embedded or browser deployment, or customized inference systems, but the exported decoder is not a drop-in text-generation model.

The ONNX notes also identify execution-provider constraints:

- GPU deployments should use the FP16-based variants.
- Certain FP32 attention operations otherwise fall back to CPU execution.
- WebGPU uses the WebGPU-specific ONNX Runtime import.
- Packed input length limits are stricter for some quantized WebGPU graphs.

Official ONNX checkpoint and implementation notes:

[https://huggingface.co/LiquidAI/d1-2B-ONNX](https://huggingface.co/LiquidAI/d1-2B-ONNX?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face



### 5.4 Hosted d1 models are separate products

Liquid AI also offers hosted decision models through the Liquid API, including `d1.1` and `d1-ultra`.

These share the central concept of named Noul, Choice, and Score questions, but they are not an API endpoint serving the open d1-2B checkpoint by default.

For example:

```
pip install typesafe-sdk
```

```
import osfrom typesafe_sdk import TypeSafeClient, Noul, Choiceclient = TypeSafeClient(    api_key=os.environ["LIQUID_API_KEY"],    base_url="https://api.liquid.ai",)result = client.system_one(    model="d1.1",    state="The application crashes whenever I upload a file.",    questions={        "is_bug": Noul(            instructions="Is the user reporting a software defect?",        ),        "team": Choice(            instructions="Who should handle this issue?",            criteria={                "engineering": "Software defects and crashes",                "support": "Instructions, questions, and account assistance",            },        ),    },)print(result.answers["is_bug"].noul)print(result.answers["team"].choice)
```

Hosted SDK responses use typed SDK objects; local Transformers responses use dictionaries. The interfaces should not be treated as interchangeable without an adapter.

Liquid AI documents the hosted Python SDK as text-only for now, with image requests sent through the HTTP API. Hosted billing is input-token-based, and each question is charged with its associated state and media, even though no output tokens are generated.

Source: [https://docs.liquid.ai/lfm/models/d1](https://docs.liquid.ai/lfm/models/d1?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.liquid.ai\&sz=32)

Liquid AI Docs+1



## 6. Performance characteristics and benchmark evidence

### 6.1 Reported performance against other open d1 models

Liquid AI's model card provides the following benchmark results. These are upstream-reported evaluations, not measurements independently reproduced for this reference.

| Benchmark                     | d1-2B | d1-omni-2B | d1-3B |
| ----------------------------- | ----- | ---------- | ----- |
| Decision Index v0.3           | 51.1  | 49.0       | 49.0  |
| DecisionBench (Hanno Labs) v1 | 77.1  | 76.4       | 73.1  |
| Decision Bench v4             | 85.2  | 84.7       | 83.6  |
| JevBench v1.4.1               | 77.9  | 75.3       | 76.2  |
| ImajevBench v2.0-lite         | 75.5  | 72.3       | 64.0  |
| WorkflowEvals                 | 81.6  | 77.1       | 74.4  |
| Typed Decisions               | 61.3  | 63.1       | 65.0  |
| Liquid AI's aggregate board   | 63.2  | 61.8       | 58.8  |
| Average of vision benchmarks  | 70.2  | 67.7       | 65.4  |

There are several meaningful conclusions, and limitations, in these results.

d1-2B improves substantially over the earlier d1-3B across the aggregate board despite having fewer parameters. This is consistent with the architectural and training changes in the newer LFM3 generation.

However, it is not uniformly superior. On the reported Typed Decisions benchmark, d1-3B scores 65.0 versus 61.3 for d1-2B. The older model also scores slightly higher on Fast Decisions.

The multimodal results are encouraging but uneven. For example, d1-2B scores 86.1 on CV-Bench but only 26.4 on MMMU-Pro and 29.9 on VisualPuzzles. This matters because recognizing an object or classifying a visual scene is not equivalent to solving a complex visual reasoning problem.

The benchmark methodology also deserves attention. Liquid AI notes that the vision benchmarks were converted into decisions over supplied options, with at most 1,000 examples from each benchmark, and that certain benchmarks were already saturated. Consequently, these numbers do not establish the model's effectiveness at unrestricted visual question answering.

Primary source: [https://huggingface.co/LiquidAI/d1-2B](https://huggingface.co/LiquidAI/d1-2B?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face



### 6.2 Reported inference latency

The published measurements use BF16, warm inference following `model.compile()`, and medians over 20 calls. Compilation itself takes approximately a minute in Liquid AI's reported setup.

| Workload                       | NVIDIA H100 PCIe | AMD MI325X | Apple M5 Pro |
| ------------------------------ | ---------------- | ---------- | ------------ |
| One decision question          | 5.7 ms           | 3.8 ms     | 18.6 ms      |
| Three questions                | 7.6 ms           | 5.6 ms     | 26.5 ms      |
| 5K-token state                 | 52 ms            | 44 ms      | 753 ms       |
| 384-pixel image                | 12.3 ms          | 8.7 ms     | 45.2 ms      |
| One bounding box               | 16.1 ms          | 11.2 ms    | 53.5 ms      |
| Batch of 64 states, throughput | 1,132/s          | 1,699/s    | 109/s        |

These figures illustrate two important performance mechanisms.

First, the cost of three questions is only moderately greater than the cost of one for the benchmarked short states. This reflects the benefit of sharing context processing and avoiding separate autoregressive completions.

Second, long input contexts remain expensive. The difference between a short decision and a 5K-token decision is much larger than the incremental cost of adding questions to the same short state.

The performance benefit is therefore most compelling when output generation would otherwise be a material proportion of the workload, or when many questions reuse the same input.

These numbers should not be transferred directly to a different accelerator, batch distribution, context length, runtime, or quantization format.

Source: [https://huggingface.co/LiquidAI/d1-2B](https://huggingface.co/LiquidAI/d1-2B?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face



### 6.3 Memory and deployment economics

At 1.92 billion parameters, a naive BF16 parameter-only footprint is approximately 3.84 GB in decimal units. Actual runtime memory also includes model-specific components, buffers, activations, image processing, batching, and compilation overhead.

The ONNX and MLX model variants reduce weight storage requirements, but smaller weights do not necessarily mean equivalent inference outputs or proportionally smaller runtime memory.

For decision-oriented applications, the principal efficiency variables are:

- Input token volume and image/video representation.
- The number of questions sharing a state.
- Hardware utilization across independent states.
- Selected precision and runtime implementation.
- Whether inference is warm or includes compilation and loading.
- How much downstream work is avoided by direct typed answers.

The elimination of generated output tokens is an important structural advantage, but it does not eliminate preprocessing, input attention, or multimodal computation.

## 7. Calibration, uncertainty, and semantic reliability

### 7.1 What calibrated probabilities mean

The d1-2B checkpoint includes calibration artifacts. The model's Python wrapper loads `calibration.json` associated with the selected checkpoint revision, and the answer implementation uses those calibration settings when interpreting applicable outputs.

This is stronger than asking a generative model to write an unsupported self-assessed confidence number.

Nevertheless, a calibrated output is not a guarantee that the reported probability is correct for every new task or deployment distribution.

For instance, a probability of 0.9 is useful as a decision signal only if examples receiving similar scores tend to be correct approximately 90% of the time under the relevant evaluation conditions.

Changes in language, document format, image quality, class descriptions, and the candidate label set can change the relationship between reported probabilities and observed accuracy.

Relevant implementation:

[https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py?utm_source=chatgpt.com)

[https://huggingface.co/LiquidAI/d1-2B/blob/main/modeling_d1.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/modeling_d1.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main+1



### 7.2 Binary thresholds and three-way decisions

A simple binary cutoff at 0.5 is not always appropriate.

When false positives and false negatives have different consequences, a useful pattern is to distinguish acceptance, rejection, and uncertainty.

```
def classify_with_review(    probability: float,    negative_threshold: float = 0.2,    positive_threshold: float = 0.8,) -> str:    if probability >= positive_threshold:        return "positive"    if probability <= negative_threshold:        return "negative"    return "review"
```

This is ordinary application logic, but the model's probability output makes it straightforward to implement.

For risk-sensitive systems, thresholds should be selected from measured precision, recall, false-positive cost, and false-negative cost rather than chosen solely because they seem intuitively conservative.

### 7.3 Choice confidence is not the same as ranking separation

A Choice result returns a full probability distribution.

This enables richer acceptance rules than checking the selected category alone. For example:

```
def accept_route(    answer: dict,    min_probability: float = 0.80,    min_margin: float = 0.20,) -> str | None:    ranked = sorted(        answer["probabilities"].items(),        key=lambda item: item[1],        reverse=True,    )    best_name, best_probability = ranked[0]    runner_up_probability = (        ranked[1][1] if len(ranked) > 1 else 0.0    )    if best_probability < min_probability:        return None    if best_probability - runner_up_probability < min_margin:        return None    return best_name
```

The top probability and its margin over the runner-up communicate different things. A decision may have a relatively high top probability while still being ambiguous between two alternatives.

The thresholds above are examples, not calibrated recommendations.

### 7.4 Abstention and explicit unknown categories

There is an easily overlooked distinction in the released Python implementation.

The lower-level `SystemOneApi` supports an `abstain_below` option for Choice questions with an explicit `"I don't know"` candidate. Its logic can select that candidate when the best non-abstention option fails a confidence threshold.

However, the public Transformers `SystemOneModel.system_one()` wrapper currently exposes `score_readout` and `set_size`, not `abstain_below`. The lower-level implementation and the public model wrapper therefore have different signatures.

The most portable approach is to inspect returned probabilities and implement abstention at the application boundary, as in the example above.

A further semantic distinction is worth preserving: unknown, insufficient evidence, and none of the listed categories are different outcomes. They should not automatically be treated as equivalent.

Source: [https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main+1



### 7.5 Source spans and provenance

The source-code implementation provides an additional detail relevant to extraction systems.

Extraction spans are mapped to character positions in the rendered state representation, not simply exposed as token indices.

For a string input, that corresponds to offsets within the model's rendered source text. For JSON-compatible structures, the state is serialized according to the model's rendering rules, so offsets must be interpreted against that representation rather than assumed to index an original external file or independently serialized JSON document.

The `path` field supplies complementary structural provenance for JSON values.

This creates useful possibilities for auditability and reconciliation, but callers must preserve the correct representation when using offsets.

Source: [https://huggingface.co/LiquidAI/d1-2B/blob/main/pointer.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/pointer.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main+1



## 8. Important architectural patterns

d1-2B is most useful when viewed as a specialized semantic decision primitive that can be combined with deterministic application components.

### 8.1 Semantic gates before expensive operations

A lightweight decision can determine whether a subsequent operation is needed.

For example, a document-processing service might first ask whether the document contains contractual obligations, then invoke specialized extraction only when appropriate.

The key is to separate two things:

- d1-2B evaluates semantic evidence and produces probabilities.
- Application logic decides which action to execute based on those results.

The model does not independently orchestrate arbitrary workflows or execute external tools.

### 8.2 Dynamic taxonomies without training a dedicated classifier

A conventional fixed-label classifier typically has categories determined at training time.

d1-2B permits categories and their definitions to be supplied with each request. This can simplify systems where the taxonomy changes frequently or differs across domains.

For example, two independent applications could ask the same checkpoint to classify:

- Financial documents by accounting treatment.
- Scientific abstracts by research methodology.
- Software issues by owning engineering subsystem.

This flexibility is valuable, although changing candidate definitions can affect accuracy and calibration. Stable, evaluated category definitions are still important for production use.

### 8.3 Semantic evaluation and reranking

A Noul question can ask whether a candidate passage supports a requirement, matches an intent, or is relevant to a query.

This supports an architecture such as:

1. A retrieval system returns candidate documents or passages.
2. Each candidate becomes part of a decision state.
3. d1-2B estimates the probability that the candidate satisfies a specific criterion.
4. The application ranks, filters, or escalates candidates using those probabilities.

The model is not itself a vector database, dense embedding model, or traditional cross-encoder reranker, but its decision capabilities can be used in a reranking stage.

The distinction matters: d1-2B allows explicit, task-specific semantic criteria, while an embedding similarity system primarily measures similarity in a learned representation space.

A specialized reranker may still be faster or more accurate for a fixed ranking objective, so the benefit depends on the need for dynamic criteria and calibrated decision signals.

### 8.4 Extract, normalize, validate, reconcile

For structured information processing, the model can fit into a pipeline with distinct responsibilities:

Source document

d1-2B extraction

Deterministic validation

Typed values + source positions + confidence → schema checks, reconciliation, persistence, exception handling

Possible native Python companions include Pydantic for schema validation, date and decimal libraries for exact value handling, and data-engine interfaces for persistence.

The division of responsibility is important:

- d1-2B identifies likely values and their locations.
- A parser establishes whether the returned representation is syntactically valid.
- Domain rules establish whether it is semantically and numerically acceptable.
- Reconciliation checks whether the extracted values are consistent with other evidence.

This is particularly useful where a direct generated JSON response would obscure which values were actually present in the source.

### 8.5 Multiquestion evaluation versus conditional inference

The model can evaluate many named questions on one state, but that does not imply that each question dynamically depends on another question's output.

For example, asking for a document type and a payment deadline in the same invocation does not create a conditional program that only searches for the deadline if the document type is an invoice.

Where such dependency is necessary, Python logic should make it explicit:

```
kind = model.system_one(document, {    "type": {        "type": "choice",        "instructions": "What kind of document is this?",        "criteria": {            "invoice": "A bill requesting payment",            "other": "Any other kind of document",        },    },})["answers"]["type"]if kind["choice"] == "invoice":    extraction = model.system_one(document, {        "due_date": {            "type": "date",            "instructions": "What is the payment due date?",        }    })
```

This introduces an additional inference call, so it trades computational reuse for conditional execution.

Where questions are inexpensive and broadly applicable, a single multiquestion pass may be preferable. Where later questions are costly, numerous, or meaningful only for a small subset of inputs, conditional execution can be attractive.

## 9. Limitations and engineering tradeoffs

### 9.1 Bounded decisions are the central specialization

The model excels at evaluating existing information against a defined decision space. It is not designed to compose arbitrary new content.

Examples that fall outside its principal capabilities include:

- Generating reports, explanations, source code, or summaries.
- Performing open-ended multistep reasoning.
- Computing arbitrary arithmetic expressions or symbolic mathematics.
- Returning an unrestricted newly authored JSON object.
- Executing tools, planning actions, or managing conversational state.
- Learning new class distinctions automatically from an application database.

These tasks require other components, different models, or additional training.

### 9.2 Long contexts are supported but not uniformly reliable

Although the advertised context window is 128K tokens, Liquid AI explicitly warns that answers become less reliable beyond approximately 64K tokens of state.

This makes it important to distinguish architectural context capacity from demonstrated decision reliability at that context length.

Long-document systems may benefit from structural segmentation, retrieval, or hierarchical evaluation, but those approaches should preserve enough surrounding evidence to avoid losing relationships between sections.

### 9.3 Multimodal limits

Visual grounding is bounded to the model's supported box representations and detection capacities. Multiple-instance detection is not unlimited; counting and localization can also be unreliable for dense, small, occluded, or ambiguous objects.

Video evaluation should not be confused with comprehensive temporal reasoning over an arbitrarily long recording.

Audio is also not a native input capability of the d1-2B checkpoint discussed here. Liquid AI offers distinct `d1-omni` models for audio-inclusive workloads.

Source: [https://docs.liquid.ai/lfm/models/d1-omni-2b](https://docs.liquid.ai/lfm/models/d1-omni-2b?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.liquid.ai\&sz=32)

Liquid AI Docs



### 9.4 Fine-tuning is not the same as fine-tuning an ordinary LFM

Liquid AI provides a broader fine-tuning ecosystem supporting SFT, LoRA, DPO, GRPO, and distributed training through Liquid Finetune and companion tooling.

However, those general-purpose instructions do not, by themselves, constitute a verified fine-tuning procedure for d1-2B's specialized answer slots, calibration behavior, and typed readout heads.

The Hugging Face checkpoint is a separately post-trained decision model. Retaining its decision semantics during further training requires more than applying a conventional text-generation SFT recipe.

At the time of this research, I did not verify a complete official, d1-2B-specific training procedure covering all typed tasks and subsequent calibration.

The model's source is available for investigating such work, but a custom objective, training format, and evaluation process would need independent validation.

General fine-tuning documentation: [https://docs.liquid.ai/lfm/fine-tuning/overview](https://docs.liquid.ai/lfm/fine-tuning/overview?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.liquid.ai\&sz=32)

Liquid AI Docs



### 9.5 Runtime compatibility can be misleading

The Hugging Face page includes automatically generated integration examples for text-generation infrastructure such as vLLM, SGLang, and standard image-text chat.

Those examples should not be interpreted as confirmation that a generic chat-completions endpoint supports the d1-2B-specific `system_one` decision protocol.

The verified deployment routes are the specialized model implementation in Transformers and the explicitly documented decision-capable alternatives.

This matters when integrating d1-2B with inference servers, agent frameworks, and libraries that assume all Transformer checkpoints use an autoregressive `.generate()` interface.

## 10. Licensing, security, and operational considerations

### 10.1 The LFM Open License is not Apache 2.0 or MIT

The checkpoint is distributed under the LFM Open License v1.0.

The license grants substantial rights to use, modify, and redistribute the model, but it also imposes a commercial-use restriction tied to an annual-revenue threshold of US$10 million.

Organizations at or around that threshold should review the complete legal definition and applicable license terms carefully. Commercial uses outside the grant may require a separate agreement.

The license also includes conditions covering redistribution, preservation of notices, and marking modified files.

Primary license text:

[https://huggingface.co/LiquidAI/d1-2B/blob/main/LICENSE](https://huggingface.co/LiquidAI/d1-2B/blob/main/LICENSE?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



### 10.2 Custom model code is executable software

Loading through `trust_remote_code=True` grants the repository's custom Python code execution privileges in the running process.

That has implications for dependency management and security review, particularly when the model is used in a persistent service or environment with sensitive credentials.

A reproducible deployment should pin the model revision and related artifacts, review the checkpoint's Python components, and manage updates as software changes rather than only weight changes.

### 10.3 Production observability and evaluation

The model's structure enables unusually useful observability. Applications can retain:

- Model revision and inference runtime.
- Question schema and criteria version.
- Input length and media characteristics.
- Complete category probability distributions.
- Numeric estimates and their intervals.
- Extraction spans and JSON paths.
- Threshold decisions and fallback outcomes.

This makes it possible to distinguish model error from downstream policy error.

For validation, useful metrics include classification confusion matrices, precision/recall by category, Brier score or expected calibration error for probabilities, ordinal error for scores, field-level extraction accuracy, and bounding-box overlap for visual grounding.

Because the model relies on natural-language criteria, evaluation should also test paraphrased category descriptions, overlapping labels, missing evidence, contradictory evidence, and distribution shifts.

For risk-sensitive decisions, the semantic model should remain one input to a system with explicit application rules and independent controls.

## 11. Positioning relative to adjacent model families

The following distinctions help clarify when its architecture matters.

| Model approach                        | Primary strengths                                                        | Key distinction from d1-2B                                                   |
| ------------------------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Fixed-head BERT/ModernBERT classifier | Efficient classification with a trained, stable taxonomy                 | Usually requires task-specific training for new categories                   |
| Encoder similarity or embedding model | Semantic retrieval, clustering, similarity search                        | Does not directly provide the same typed decisions and extraction provenance |
| Cross-encoder reranker                | Joint query-document relevance assessment                                | Often optimized for a narrower scoring objective                             |
| Small generative LLM                  | Flexible JSON generation, explanations, reasoning, text composition      | Uses autoregressive decoding and requires output parsing/validation          |
| d1-2B                                 | Dynamic typed questions, probabilities, extraction, multimodal decisions | Specialized for bounded outcomes rather than content generation              |
| d1-omni-2B                            | Decision interface with audio support                                    | Different checkpoint and input modalities                                    |
| Hosted d1.1 / d1-ultra                | Remote decision inference                                                | Distinct service models and API economics                                    |

The central architectural opportunity is not necessarily replacing every classifier or every LLM. It is replacing unnecessarily generative or bespoke semantic-decision steps when the required output is inherently bounded.

A fixed classifier trained for a highly stable taxonomy may still be cheaper and better calibrated. A specialized NER model may be more effective for exhaustive spans over long documents. A generative model remains appropriate where responses require explanation, synthesis, or new structured content.

What d1-2B adds is the ability to combine multiple dynamic semantic decisions, typed reads, probability distributions, and visual grounding under one consistent interface.

## 12. Primary source reference map

The following sources cover the most important public implementation and research surfaces.

| Topic                                                       | Direct source                                                                                                                                           |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Official model overview and Python quick start              | [https://docs.liquid.ai/lfm/models/d1-2b](https://docs.liquid.ai/lfm/models/d1-2b?utm_source=chatgpt.com)                                               |
| Model checkpoint, benchmark tables, and inference examples  | [https://huggingface.co/LiquidAI/d1-2B](https://huggingface.co/LiquidAI/d1-2B?utm_source=chatgpt.com)                                                   |
| Decision model family and hosted/open-weight distinctions   | [https://docs.liquid.ai/lfm/models/decision-models](https://docs.liquid.ai/lfm/models/decision-models?utm_source=chatgpt.com)                           |
| Complete answer interpretation and calibration logic        | [https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py?utm_source=chatgpt.com)                 |
| Transformers model wrapper and compilation API              | [https://huggingface.co/LiquidAI/d1-2B/blob/main/modeling_d1.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/modeling_d1.py?utm_source=chatgpt.com) |
| Inference scheduler, batching, and attention implementation | [https://huggingface.co/LiquidAI/d1-2B/blob/main/runner.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/runner.py?utm_source=chatgpt.com)           |
| Question schemas and input rendering                        | [https://huggingface.co/LiquidAI/d1-2B/blob/main/prompt.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/prompt.py?utm_source=chatgpt.com)           |
| Extraction pointer mapping and provenance                   | [https://huggingface.co/LiquidAI/d1-2B/blob/main/pointer.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/pointer.py?utm_source=chatgpt.com)         |
| GGUF and llama.cpp decision endpoint                        | [https://huggingface.co/LiquidAI/d1-2B-GGUF](https://huggingface.co/LiquidAI/d1-2B-GGUF?utm_source=chatgpt.com)                                         |
| Apple Silicon MLX, 8-bit                                    | [https://huggingface.co/LiquidAI/d1-2B-MLX-8bit](https://huggingface.co/LiquidAI/d1-2B-MLX-8bit?utm_source=chatgpt.com)                                 |
| Apple Silicon MLX, 4-bit                                    | [https://huggingface.co/LiquidAI/d1-2B-MLX-4bit](https://huggingface.co/LiquidAI/d1-2B-MLX-4bit?utm_source=chatgpt.com)                                 |
| ONNX Runtime model export                                   | [https://huggingface.co/LiquidAI/d1-2B-ONNX](https://huggingface.co/LiquidAI/d1-2B-ONNX?utm_source=chatgpt.com)                                         |
| Hosted decision model Python API                            | [https://docs.liquid.ai/lfm/models/d1](https://docs.liquid.ai/lfm/models/d1?utm_source=chatgpt.com)                                                     |
| General fine-tuning ecosystem                               | [https://docs.liquid.ai/lfm/fine-tuning/overview](https://docs.liquid.ai/lfm/fine-tuning/overview?utm_source=chatgpt.com)                               |
| License                                                     | [https://huggingface.co/LiquidAI/d1-2B/blob/main/LICENSE](https://huggingface.co/LiquidAI/d1-2B/blob/main/LICENSE?utm_source=chatgpt.com)               |

### Overall assessment

d1-2B is technically notable because it treats semantic decision-making as a native inference operation rather than a constrained form of text generation.

Its greatest architectural strengths are the combination of dynamically defined questions, direct probability readouts, shared-context multiquestion evaluation, source-grounded typed extraction, and multimodal grounding—all accessible through a relatively small local model.

For Python, Transformers with `AutoModel` and `system_one` is the definitive integration path when the complete capability set is required. MLX offers an attractive Apple Silicon path, llama.cpp supports a narrower but practical decision interface, and ONNX provides an avenue for lower-level cross-platform deployment.

The most significant tradeoffs are bounded rather than generative outputs, runtime-dependent feature coverage, the reliability limits of long contexts and complex reasoning, sensitivity of calibrated probabilities to distribution and quantization changes, and the commercial restrictions of the LFM Open License.

Taken together, d1-2B occupies a useful middle ground between fixed-task classifiers and generative language models: a programmable, multimodal semantic-decision engine with unusually rich typed outputs for its size.

# Liquid AI d1-2B — Technical Reference Addendum

Research date: November 8, 2026\
Target checkpoint: `LiquidAI/d1-2B`\
Scope: Additional capabilities, advanced Python interfaces, inference mechanisms, and implementation constraints not fully addressed in the original overview.

This addendum supplements the original d1-2B reference without repeating its architecture overview, standard inference examples, benchmark tables, or introductory discussion of decision types.

The additions emphasize functionality verified in the released checkpoint's Python implementation, including capabilities that are not prominently documented in Liquid AI's introductory material.

## 1. Advanced question specification and decision semantics

### 1.1 Explicit binary decision criteria

The `noul` question type accepts an optional `criteria` mapping that explicitly defines what positive and negative answers mean.

```
question = {    "type": "noul",    "instructions": "Does this passage establish a contractual obligation?",    "criteria": {        "true": (            "The passage establishes an enforceable duty "            "or requirement for an identified party."        ),        "false": (            "The passage does not establish an enforceable "            "duty or requirement."        ),    },}
```

These definitions become part of the model's question representation. They are not merely labels attached after inference.

This makes Noul more expressive than a conventional yes/no classifier. A question can provide a compact decision specification consisting of:

- A semantic objective expressed through `instructions`.
- An explicit definition of the positive outcome.
- An explicit definition of the negative outcome.

The distinction is useful for semantic criteria that are easily confused with neighboring concepts. For example, identifying a legal obligation is different from identifying any statement about a contract.

Explicit definitions may help disambiguate the decision boundary, but their presence does not guarantee better calibration or accuracy. The wording of the criteria still influences the model's interpretation.

The implementation accepts criteria through both dictionary-based questions and the native `Noul` question class.

Source: `prompt.py`, `Noul`, `check_question()`, and `as_question()`.

[https://huggingface.co/LiquidAI/d1-2B/blob/main/prompt.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/prompt.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



### 1.2 Choice definitions can separate identifiers from semantic descriptions

The `Choice` implementation represents candidates as a mapping from identifiers to optional descriptions.

For example:

```
question = {    "type": "choice",    "instructions": "Identify the principal relationship.",    "criteria": {        "causes": "The subject directly produces the effect.",        "enables": "The subject makes the effect possible.",        "correlates": (            "The entities vary together without an "            "established causal relationship."        ),        "none": "No specified relationship is supported.",    },}
```

The machine-readable identifiers and natural-language descriptions serve distinct functions.

Identifiers become the keys returned in the probability distribution and selected answer. Descriptions explain the intended meaning of each option to the model.

The native `Choice` dataclass permits `None` descriptions, allowing a candidate name to stand alone. However, explicit descriptions can be important where identifiers are abbreviated, technical, or semantically overlapping.

The implementation also uses an internal option-alias mechanism.

Rather than requiring each user-defined category to correspond to one vocabulary token, the prompt builder assigns distinct answer codes to the categories. The model scores the corresponding token alternatives and maps the result back to the caller's identifiers.

The released code supports alternative coding schemes, including alphabetic and multi-character codes. This decouples category names from the vocabulary-level answer representation.

Consequently, a large or dynamically changing category set is not inherently limited to categories whose names tokenize as single tokens.

This does not establish that arbitrarily large category sets are equally reliable. Larger candidate sets change the decision problem, token budget, calibration conditions, and model's ability to distinguish alternatives.

Source: `prompt.py`, `Choice`, `option_codes()`, `aliases()`, and `readout_ids()`.

[https://huggingface.co/LiquidAI/d1-2B/blob/main/prompt.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/prompt.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



### 1.3 Native question dataclasses

The released model implementation defines Python dataclasses corresponding to its question families.

| Class      | Function                     | Important parameters                          |
| ---------- | ---------------------------- | --------------------------------------------- |
| `Noul`     | Binary classification        | `instructions`, optional `criteria`           |
| `Choice`   | Single or multiple selection | `instructions`, `criteria`, `multiple`        |
| `Score`    | Ordinal evaluation           | `instructions`, `criteria`                    |
| `Read`     | Source-grounded extraction   | `instructions`, `type`, `unit`                |
| `Estimate` | Numeric estimation           | `instructions`, `low`, `high`, `step`, `unit` |
| `Box`      | Single-object localization   | `instructions`                                |
| `Boxes`    | Multi-instance localization  | `instructions`, `max`                         |

All seven classes are declared as frozen dataclasses.

The `Read` class represents three externally visible question types: `text`, `number`, and `date`. The `Estimate` class represents `number` questions that include a range.

The conversion function `as_question()` accepts either a compatible dictionary or an existing question object. Dictionary specifications are converted to the appropriate dataclass before being processed.

This supports a useful architectural separation between:

- Declarative specifications: JSON-compatible dictionaries suitable for persistence, interchange, and external configuration.
- Programmatic specifications: Native Python objects that can be assembled and reused by application code.

These classes are part of the checkpoint's custom implementation, not a separately versioned, stable Python package.

One important distinction in the released code is that `check_question()` returns immediately for recognized native dataclass instances. Its dictionary-specific validation is therefore not applied in the same way to dataclass inputs. Programmatic construction does not automatically inherit every validation check performed on external JSON specifications.

Source:

[https://huggingface.co/LiquidAI/d1-2B/blob/main/prompt.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/prompt.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



## 2. Lower-level Python inference interfaces

### 2.1 The `SystemOneApi` abstraction

The public Transformers wrapper is backed by a lower-level engine accessible through:

```
engine = model.engine
```

The implementation separates three responsibilities:

1. `SystemOneModel`, the Transformers-facing model wrapper.
2. `SystemOne`, the inference runner responsible for prompt processing, batching, and model execution.
3. `SystemOneApi`, the interface responsible for question normalization, probability readouts, and answer construction.

This separation exposes functionality beyond the ordinary `model.system_one()` interface.

| Method                                        | Additional capability                                                                        |
| --------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `ask(question)`                               | Validate and normalize a question specification                                              |
| `named(questions)`                            | Normalize a dictionary of named questions                                                    |
| `probabilities(state, questions, media=None)` | Obtain lower-level probability readouts without constructing the usual named-answer response |
| `answer(state, question, probabilities, ...)` | Convert a question's readouts into a typed answer                                            |
| `render(state, question)`                     | Inspect a question's rendered prompt representation                                          |
| `system_one(..., abstain_below=...)`          | Apply native abstention behavior                                                             |
| `system_one_batch(...)`                       | Batch requests with additional lower-level parameters                                        |
| `run(requests, set_size=None)`                | Execute prepared requests and obtain readouts plus token counts                              |

These interfaces are implemented in the released checkpoint, but the lower-level engine is not guaranteed to remain stable across checkpoint or code revisions.

In particular, `run()` expects normalized question objects and media representations rather than simply accepting the same high-level inputs as `model.system_one()`.

Sources:

[https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py?utm_source=chatgpt.com)

[https://huggingface.co/LiquidAI/d1-2B/blob/main/runner.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/runner.py?utm_source=chatgpt.com)

[https://huggingface.co/LiquidAI/d1-2B/blob/main/modeling_d1.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/modeling_d1.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main+2



### 2.2 Direct access to probability readouts

The engine exposes `probabilities()` for use cases where an application needs probability distributions before they are transformed into ordinary answer dictionaries.

```
questions = [    {        "type": "noul",        "instructions": "Does the document contain a payment obligation?",    },    {        "type": "choice",        "instructions": "What is the primary document category?",        "criteria": {            "invoice": "A request for payment",            "receipt": "Evidence of a completed payment",            "contract": "An agreement establishing obligations",        },    },]distributions = model.engine.probabilities(    "Payment of EUR 500 is required within 30 days.",    questions,)binary_distribution = distributions[0]category_distribution = distributions[1]
```

For a simple Noul question, the returned sequence corresponds to probabilities for positive and negative answers. For ordinary Choice questions, it corresponds to the supplied candidate order.

For specialized typed questions, the underlying readouts are more complex and should not be assumed to have the same simple one-dimensional structure.

This interface is valuable when an application needs to perform custom probability analysis or compare multiple readout interpretations.

It does not eliminate the need to understand how the engine applies calibration. The values returned by `probabilities()` are not universally interchangeable with every field in a completed typed answer.

### 2.3 Native abstention for Choice questions

The lower-level API has an optional `abstain_below` parameter.

This enables an explicit I don't know candidate to be selected when the leading substantive answer fails a confidence threshold.

```
questions = {    "relation": {        "type": "choice",        "instructions": "What relationship does the passage establish?",        "criteria": {            "causal": "One entity directly causes the other.",            "correlative": "The entities are correlated.",            "unknown": "I don't know",        },    },}result = model.engine.system_one(    "The available evidence does not clearly identify the relationship.",    questions,    abstain_below=0.75,)
```

The internal rule is more precise than simply checking whether the selected candidate exceeds 0.75.

Let \\(p_a\\) be the probability assigned to the explicit abstention candidate and \\(p_i\\) the probabilities of the substantive candidates.

The rule selects abstention when

\\[ \max\_{i\ne a}\frac{p_i}{1-p_a}<\tau, \\]

where \\(\tau\\) is `abstain_below` and the denominator is the probability mass assigned to all non-abstention candidates. The implementation also handles the degenerate case where that mass is zero.

This effectively evaluates how dominant the strongest substantive answer is after removing the abstention candidate from the normalization.

There are three important constraints.

First, the implementation identifies abstention through a small set of recognized English descriptions, including `"I don't know"` and `"I do not know"`. An arbitrary label such as `"other"` does not trigger the mechanism.

Second, `abstain_below` operates on ordinary Choice questions. It is not a general confidence threshold for Noul, Score, or every typed extraction question.

Third, the high-level `model.system_one()` wrapper does not expose `abstain_below`. Access requires the lower-level engine or equivalent application-side logic.

An explicitly modeled unknown outcome and a low-confidence abstention policy also represent different semantics. The former is an answer category; the latter is a rule for declining to select a substantive answer.

Source: `api.py`, `abstain_option()`, `choice_index()`, and `SystemOneApi.system_one()`.

[https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



### 2.4 Score readout semantics: median, expected value, and mode

The three supported ordinal readouts deserve a more precise mathematical distinction.

For ordered levels \\(0,\ldots,K-1\\) with probabilities \\(p_i\\):

- `median` returns the lowest level at which cumulative probability reaches 0.5.
- `mean` returns the continuous expected value \\(\sum_i i p_i\\).
- `argmax` returns the level with the greatest individual probability.

The public wrapper exposes this through `score_readout`:

```
result = model.system_one(    state,    {"severity": severity_question},    score_readout="mean",)
```

In the returned answer dictionary, `mean` is not rounded to an integer level. The lower-level helper `score_level()` contains a rounded-mean branch, but `answer()` explicitly calculates and returns the continuous expected value for this option.

These distinctions are consequential when a score is used for arithmetic aggregation or ranking. A continuous expectation can preserve information that a discrete median or mode discards, while a median gives a valid ordinal level without introducing fractional categories.

The `confidence` field is the greatest individual level probability; it is not automatically the probability of the returned median or expected value.

Source:

[https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/api.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



## 3. Typed extraction: additional controls and normalization behavior

### 3.1 Explicit numeric units

Numeric extraction and numerical estimation both accept an optional `unit` field.

```
questions = {    "operating_pressure": {        "type": "number",        "instructions": "What operating pressure is reported?",        "unit": "bar",    },    "annual_revenue": {        "type": "number",        "instructions": "What annual revenue is reported?",        "unit": "USD",    },}
```

For source-grounded numeric extraction, the unit is incorporated into the model's question representation and passed to the deterministic parser.

Its function is primarily interpretive. It does not provide general physical-unit conversion.

For example, the parser does not automatically transform a reported pressure of 100 kPa into 1 bar merely because `unit="bar"` was specified.

The numeric parser is specifically designed to recover written quantities without performing arithmetic or inventing implicit conversions.

It supports a substantial range of numeric conventions:

| Capability                       | Examples or behavior                                                   |
| -------------------------------- | ---------------------------------------------------------------------- |
| International decimal separators | `1,234.50`, `1.234,50`                                                 |
| Space and apostrophe grouping    | `1 234,50`, `1'234.50`                                                 |
| Currency notation                | `$`, `€`, `USD`, `EUR`, `GBP`, and others                              |
| Percentages                      | Identifies an explicit `%` marker                                      |
| Written scales                   | Thousand, million, billion, trillion                                   |
| Regional scales                  | Lakh, crore, 万, 億, and others                                          |
| Abbreviated scales               | `k`, `M`, `bn`, subject to context                                     |
| Accounting negatives             | Parenthesized negative amounts                                         |
| Locale-sensitive interpretation  | Uses evidence from nearby numbers, currencies, and locale declarations |

An important detail is that percentages are returned in percentage points: an extracted `12%` corresponds to a numeric magnitude of 12, not automatically 0.12.

The parser uses `decimal.Decimal` internally but converts its final numeric result to `int` or `float`. Thus, the returned numeric value does not inherently preserve arbitrary decimal precision.

For decimal-exact downstream processing, the original extracted `text` should be retained alongside the normalized value.

Source: `parsing.py`, `parse_number()`, `written_unit()`, and `_decimal_mark()`.

[https://huggingface.co/LiquidAI/d1-2B/blob/main/parsing.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/parsing.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



### 3.2 Date parsing and ambiguity management

The `date` extraction type uses a deterministic date parser after the model identifies a source span.

This parser supports several useful behaviors:

- ISO-style numeric dates.
- Day-first and month-first numeric dates.
- Month names and abbreviations in multiple languages.
- Chinese and Korean date notation.
- Explicitly written times and time-zone offsets.
- Contextual inference of date ordering from locale information or other unambiguous dates.
- Two-digit years when a century can be established from the surrounding source context.

Its handling of ambiguous dates is particularly significant.

For example, `03/04/2026` can denote March 4 or April 3. If the source does not establish the intended ordering, the parser can return `None` rather than silently selecting one interpretation.

Similarly, a two-digit year is not automatically assigned an arbitrary century.

When a time or timezone is explicitly present, the parser attempts to preserve it. It does not add a default time or timezone to a date that lacks one.

This distinguishes the extraction feature from permissive date-parsing libraries that may use current dates, default fields, or environment locale settings to fill missing information.

Source: `parsing.py`, `date_order()`, and `parse_date()`.

[https://huggingface.co/LiquidAI/d1-2B/blob/main/parsing.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/parsing.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



### 3.3 Source-span length limits

The pointer implementation imposes specific maximum extraction lengths.

| Reader   | Maximum span length |
| -------- | ------------------- |
| `text`   | 512 tokens          |
| `number` | 32 tokens           |
| `date`   | 32 tokens           |

The limits operate on model tokens, not characters.

The relevant implementation constant is:

```
SPAN_CAPS = {    "text": 512,    "number": 32,    "date": 32,}
```

Consequently, a single extraction question is not an unrestricted mechanism for returning an entire document or enumerating all occurrences of an entity.

Where exhaustive extraction is required, the model's bounded pointer operation must be distinguished from a sequence-labeling system that returns all entity spans across an input.

A pipeline can pose separate questions or process smaller sections, but that is application-level composition rather than a native unlimited extraction primitive.

### 3.4 Pointer-based source grounding

The implementation uses dedicated source-position readouts.

For a `Read` question, the model produces start and end position queries. These are compared against representations of valid positions in the original state.

The implementation includes a special null position for an absent value and masks positions that do not correspond to valid source text.

The process is therefore different from generating the extracted value as a string and subsequently searching for it in the input.

It also distinguishes three outcomes:

1. The requested source span was not found.
2. A span was found, but its numeric or date representation could not be parsed.
3. A span was found and successfully normalized.

These outcomes should not be collapsed into a single success/failure flag.

For example, `found >= 0.5` can coexist with `number=None` if the source text was identified but deterministic normalization failed.

### 3.5 Character offsets and JSON Pointer provenance

Extraction spans are returned as character offsets into the model's rendered state text.

For a Python string state, that text ordinarily corresponds to the supplied string. For a structured Python object, the default renderer produces a JSON representation.

This creates an important distinction between the original source object and its rendered form.

Suppose a Python dictionary is passed as the state. The model may report an extracted span and a JSON Pointer such as:

```
{    "text": "ACME Components",    "span": [42, 57],    "path": "/supplier/name",}
```

The span refers to the relevant character positions in the rendered representation, whereas `path` identifies a structural location in the JSON object.

The model's pointer implementation maps eligible extracted text spans to JSON string paths using `json_spans.py`. A path is not guaranteed for every extraction, particularly when the span cannot be associated unambiguously with one source string.

The implementation also reconstructs extracted JSON string content from its escaped representation.

This allows provenance to be maintained without conflating a textual offset, a token index, and a structural path.

Sources:

[https://huggingface.co/LiquidAI/d1-2B/blob/main/pointer.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/pointer.py?utm_source=chatgpt.com)

[https://huggingface.co/LiquidAI/d1-2B/blob/main/json_spans.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/json_spans.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



## 4. Numerical estimation: grid mechanics and precision

### 4.1 The 128-value grid limit

Numerical estimation is implemented as classification over an ordered numerical grid.

The grid contains at most 128 discrete values, regardless of how many values the requested range and step would otherwise imply.

For a range \\([a,b]\\) with a requested step \\(s\\), the implementation selects

\\[ N=\min\left(128,\ \operatorname{round}\left(\frac{b-a}{s}\right)+1\right). \\]

The effective grid spacing is

\\[ \Delta=\frac{b-a}{N-1}. \\]

This means `step` is a requested discretization, not necessarily the effective discretization.

Consider:

```
question = {    "type": "number",    "instructions": "Estimate the number of components.",    "range": [0, 1000],    "step": 1,}
```

The request implies 1,001 possible integers. The implementation instead constructs 128 grid values, yielding an effective spacing of approximately 7.874.

As a result, the model cannot distinguish every integer in that range through its native readout.

This behavior has implications beyond speed: it changes the numerical resolution of the answer itself.

A narrower range can provide finer resolution. However, narrowing the range also imposes a stronger assumption about the possible value, potentially excluding the true answer.

### 4.2 Grid distributions and quantile extraction

The model produces a probability distribution across the numerical grid.

The grid implementation supports:

- Probability-weighted mean.
- Median.
- 10th percentile.
- 90th percentile.

The public estimate answer currently returns the median and a two-element interval representing the lower and upper quantiles.

The mean is calculated internally but is not part of the ordinary high-level estimate response.

The returned interval is not an automatically valid frequentist confidence interval. Its reliability depends on the model's estimation behavior and subsequent calibration.

A further distinction is that the reported values are selected from grid positions. Even with a smooth underlying probability distribution, the result is constrained by the discretization.

Sources:

[https://huggingface.co/LiquidAI/d1-2B/blob/main/grid.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/grid.py?utm_source=chatgpt.com)

[https://huggingface.co/LiquidAI/d1-2B/blob/main/prompt.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/prompt.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main+1



## 5. Visual grounding: richer output semantics

### 5.1 Presence and localization confidence are separate quantities

A `box` answer exposes both `found` and `confidence`.

These do not measure the same property.

`found` represents the calibrated probability that the requested object exists in the image.

`confidence` measures the consistency of the predicted bounding box with the underlying coordinate distributions.

The spatial confidence computation is distinctive.

The model predicts probability distributions for the four box edges. The implementation then generates 512 candidate boxes from those distributions using points from a deterministic four-dimensional Halton sequence.

It computes the proportion of sampled boxes whose intersection-over-union with the reported box is at least 0.5.

Formally, the pre-calibration confidence can be understood as

\\[ c\_{\mathrm{box}} = \frac{1}{512} \sum\_{j=1}^{512} \mathbf{1} \left[ \operatorname{IoU}(B_j,\hat{B})\geq0.5 \right], \\]

where \\(\hat B\\) is the reported box and \\(B_j\\) is a candidate sampled from the edge distributions.

This quantity is then passed through the model's localization-calibration mapping.

A model can therefore be confident that an object exists while being uncertain about its precise boundaries.

This distinction can inform how downstream systems evaluate object presence separately from location quality.

### 5.2 Multi-instance presence distributions

The `boxes` reader returns more than the detected boxes and their count.

Its `presence` field contains cumulative probabilities:

\\[ P(N\geq1),P(N\geq2),\ldots,P(N\geq k). \\]

For example, a hypothetical result might include:

```
{    "count": 3,    "at_least": False,    "presence": [0.99, 0.97, 0.86, 0.31],}
```

This conveys greater uncertainty around the fourth instance than around the first three.

Each count-presence probability is calibrated, and the implementation enforces a nonincreasing sequence so that the cumulative probabilities remain consistent.

The `count` is the number of consecutive instance slots whose presence passes the inclusion threshold.

The `at_least` flag is true when all requested instance slots are occupied, indicating that the result may have been truncated.

An important consequence is that a count returned by `boxes` is not identical to a numerical estimate obtained from a separate `number` question. They use different prediction mechanisms.

### 5.3 Box-edge discretization and ordering

The released checkpoint uses numerical box-edge readouts with 1,000 positions spanning 0 through 0.999, in increments of 0.001.

Each edge has its own distribution.

The default coordinate readout uses the distribution's median. The implementation also supports an interpolated median that identifies where the cumulative distribution crosses 0.5 within the selected bin.

This alternative is implemented but is not the published checkpoint's default.

The geometry postprocessor additionally repairs reversed edge ordering. When a predicted lower edge precedes the upper edge, it constructs a minimal-width interval around their midpoint.

For multi-instance output, boxes are sorted spatially by left coordinate and then top coordinate.

This ordering is not a temporal track identifier or a guarantee of persistent object identity.

The released checkpoint's prompt configuration supports a maximum of 16 instance slots per `boxes` question. Although the shared implementation includes support for 64 slots under a newer prompt version, that does not establish 64-instance capability for this checkpoint.

Sources:

[https://huggingface.co/LiquidAI/d1-2B/blob/main/box.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/box.py?utm_source=chatgpt.com)

[https://huggingface.co/LiquidAI/d1-2B/blob/main/config.json](https://huggingface.co/LiquidAI/d1-2B/blob/main/config.json?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main+1



## 6. Multimodal preprocessing and video interfaces

### 6.1 Native video representations

The model's Python media layer accepts video in two principal forms.

A file-backed representation:

```
result = model.system_one(    None,    {        "activity": {            "type": "choice",            "instructions": "What activity is shown?",            "criteria": {                "walking": "A person is walking",                "running": "A person is running",                "stationary": "The person is not moving",            },        }    },    media=[{        "type": "video",        "path": "inspection.mp4",    }],)
```

Alternatively, decoded frames can be supplied explicitly:

```
video_media = [{    "type": "video",    "video": frames,    "fps": 24,}]
```

Here, `frames` is a sequence of decoded video frames compatible with the model processor.

The frame-based representation requires an explicit frames-per-second value. For path-based media, the video processor handles decoding and timing metadata.

These interfaces allow decisions to be based on temporally related visual information rather than treating each image as an entirely separate classification request.

The exact frames included in inference depend on the processor and video decoding configuration. Accepting a video path does not imply that the model inspects every original frame at full resolution.

Video decoding support also depends on the installed Transformers version and its available decoding backend.

### 6.2 Multimodal input composition

The media layer represents inputs through a `Media` dataclass with fields including:

- `type`
- `value`
- `sampling_rate`
- `fps`

The `Reader` implementation converts those inputs into processor-specific token markup and tensors.

It also handles combining inputs of different lengths into model batches. Image patches, video representations, and the associated masks are joined or padded as required.

The generic media implementation contains audio processing because it is shared across multiple model architectures.

However, d1-2B is a vision-language checkpoint. The presence of generic audio code does not confer audio capability on this particular checkpoint. Audio-inclusive decision-making belongs to separately supported models, including d1-Omni.

Likewise, the bounding-box reader is specifically designed around exactly one image input, not arbitrary collections of images or frame-by-frame video tracking.

### 6.3 Image-resolution controls

The published checkpoint records:

```
{
    "d1_vision_max_pixels": 1638400
}
```

Images exceeding this budget are downscaled before processing.

The implementation uses aspect-ratio-preserving resizing with bicubic interpolation.

A lower-level configuration override is available through the environment variable:

```
export D1_VISION_MAX_PIXELS=1638400
```

The model runner also exposes a `max_pixels` parameter at the engine level.

These settings affect the resolution available for subsequent vision inference, which may change small-object visibility, fine-text recognition, latency, and memory consumption.

Increasing the limit is not inherently beneficial. It changes the operating conditions relative to those under which the checkpoint was trained and evaluated.

Sources:

[https://huggingface.co/LiquidAI/d1-2B/blob/main/media.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/media.py?utm_source=chatgpt.com)

[https://huggingface.co/LiquidAI/d1-2B/blob/main/runner.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/runner.py?utm_source=chatgpt.com)

[https://huggingface.co/LiquidAI/d1-2B/blob/main/config.json](https://huggingface.co/LiquidAI/d1-2B/blob/main/config.json?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main+2



## 7. Inference scheduling, batching, and compilation

### 7.1 Question grouping versus request batching

The inference engine implements two distinct forms of computational reuse.

Question grouping combines multiple questions sharing a state, avoiding independent processing of that state for each question.

Request batching groups independent states for execution on the same hardware.

The checkpoint records a trained question-group size of 16.

`set_size` allows the caller to override the grouping size. Larger group sizes can reduce redundant state processing, but they depart from the configuration used during training and may degrade accuracy.

The model does not guarantee that every question in an arbitrarily large request is evaluated in one physical forward pass.

The runner splits question collections into groups when needed and constructs the required prompt and attention layout for each group.

### 7.2 Token-budget-aware batching

The lower-level `SystemOne` constructor exposes:

```
token_budget: int = 65536
```

This budget controls padded tokens in an execution batch.

The scheduler uses input lengths when grouping requests and avoids combining requests that would exceed the budget.

The distinction matters because padding can become a substantial computational cost when request lengths differ significantly.

For example, placing a 100-token request and a 40,000-token request in the same conventional padded batch may require processing a very large amount of padding.

The runner uses length-aware grouping to reduce this problem.

The token budget is not a replacement for the model's maximum context length. It governs batching behavior rather than defining the logical maximum size of an individual input.

### 7.3 Compilation details

`model.compile()` invokes a specialized compilation path.

The implementation uses dynamic-shape `torch.compile()` on the language-model forward path and selected model-specific components. It also applies PyTorch Inductor configuration and uses fused projections where the underlying backbone supports them.

This is a more targeted operation than treating the entire Python inference service as one compiled graph.

The runner explicitly rejects some compilation modes when using its set-attention implementation:

```
model.compile(mode="reduce-overhead")
```

and

```
model.compile(mode="max-autotune")
```

These modes involve CUDA graph behavior that the current packed variable-length attention path does not support.

The default compilation path can still provide kernel fusion without CUDA graphs.

There are also warmup and compilation costs, so the performance benefit depends on whether those costs can be amortized over repeated calls.

Source: `runner.py`, `SystemOne.compile()`, `_batches()`, and `_sequences()`.

[https://huggingface.co/LiquidAI/d1-2B/blob/main/runner.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/runner.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main+1



## 8. Ollama: an additional local Python deployment interface

### 8.1 Native System One integration

Ollama provides a local decision-model runtime and Python client interface supporting the `d1:2b` model tag.

This is distinct from the PyTorch/Transformers implementation and from manually calling llama.cpp over HTTP.

Install the Python client and pull the model:

```
pip install ollama
ollama pull d1:2b
```

Example:

```
from ollama import Clientclient = Client(host="http://localhost:11434")result = client.systemone(    model="d1:2b",    state={        "message": "The customer reports a duplicated payment.",        "priority": "normal",    },    questions={        "billing": {            "type": "noul",            "instructions": "Is this primarily a billing issue?",            "criteria": {                "true": "The issue concerns charges or payments",                "false": "The issue does not concern charges or payments",            },        },        "team": {            "type": "choice",            "instructions": "Which team should handle the issue?",            "criteria": {                "billing": "Charges, invoices, and refunds",                "support": "General customer questions",                "technical": "Software failures",            },        },    },)print(result.answers["billing"].noul)print(result.answers["team"].choice)
```

The Python client implements `systemone()` as an operation against `/v1/systemone`.

It accepts model identifiers, states, questions, images, and a `keep_alive` setting controlling model residency.

Ollama's API also supports multimodal decision requests where the selected model accepts images.

Sources:

[https://ollama.com/library/d1:2b](https://ollama.com/library/d1:2b?utm_source=chatgpt.com)

[https://github.com/ollama/ollama-python/blob/main/ollama/\_client.py](https://github.com/ollama/ollama-python/blob/main/ollama/_client.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://registry.ollama.com\&sz=32)

registry.ollama.com+1



### 8.2 Runtime-specific restrictions

Ollama's System One interface supports Noul, Choice, and Score questions.

The public API does not currently expose the full set of typed readers and visual bounding-box outputs available through the d1-2B Transformers implementation.

Its documented restrictions include:

- Up to 64 named questions per request.
- A single non-streaming response.
- No native tool invocation through the decision endpoint.
- No video input through that endpoint.
- No generic generation controls.
- Request-size and loaded-context restrictions.

Local requests can also supply `keep_alive`, enabling an application to control whether the model remains resident after inference.

For Python services, the client handles request serialization and typed response parsing, while the Ollama process manages model loading and inference.

### 8.3 Cross-runtime score and confidence differences

There is an important semantic incompatibility between the released Transformers implementation and Ollama.

| Output                | Transformers d1-2B                          | Ollama System One                    |
| --------------------- | ------------------------------------------- | ------------------------------------ |
| `score` default       | Median ordinal level                        | Continuous probability-weighted mean |
| Choice `confidence`   | Probability assigned to the selected option | Distribution concentration           |
| Score `confidence`    | Maximum individual level probability        | Distribution concentration           |
| `noul`                | Positive-answer probability                 | Positive-answer probability          |
| `usage.output_tokens` | Zero                                        | May reflect internal scoring work    |

Ollama documents its distribution-concentration measure as

\\[ C=1-\frac{H(p)}{\ln K}, \\]

where \\(H(p)\\) is Shannon entropy and \\(K\\) is the number of candidate outcomes.

This quantity approaches zero for a uniform distribution and one when a single option dominates.

It is not the same as the selected category's probability and should not be interpreted as calibrated correctness.

These differences mean that applications should not blindly compare `confidence` or `score` fields across runtimes.

A normalized internal representation can preserve the full probability distributions and derive consistent application-level metrics independently of the inference engine.

The Ollama model page also contains an outdated introductory description of the older 3B model. The `d1:2b` identifier and published model metadata identify the newer 2B checkpoint.

Sources:

[https://github.com/ollama/ollama/blob/main/docs/openapi.yaml](https://github.com/ollama/ollama/blob/main/docs/openapi.yaml?utm_source=chatgpt.com)

[https://github.com/ollama/ollama/blob/main/docs/capabilities/decision.mdx](https://github.com/ollama/ollama/blob/main/docs/capabilities/decision.mdx?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



## 9. Calibration: native mechanisms and their interactions

### 9.1 Temperature scaling for closed-answer decisions

The checkpoint's `calibration.json` includes a global temperature:

```
{
    "default": 1.337398453966105,
    "temperatures": {}
}
```

The implementation supports optional per-type temperatures for Noul, Choice, and Score questions.

The relevant grouping mechanism can distinguish:

- Binary Noul decisions.
- Score questions by their number of levels.
- Choice questions by candidate-set size.

The code defines Choice calibration buckets for small, medium, large, and inventory-sized candidate sets.

For the released d1-2B calibration artifact, the per-type override dictionary is empty, so the global temperature is used.

Temperature scaling changes the sharpness of probability distributions.

It preserves candidate ordering under a shared positive temperature, but it can change threshold-based selection, the ordinal median, and the continuous expected score.

### 9.2 Monotonic calibration tables for typed answers

The checkpoint additionally contains fitted calibration tables for typed outputs.

| Calibration key | Affected quantity                    |
| --------------- | ------------------------------------ |
| `found:text`    | Text-span presence                   |
| `found:number`  | Numeric-span presence                |
| `found:date`    | Date-span presence                   |
| `found:box`     | Single-object presence               |
| `box`           | Single-box localization confidence   |
| `found:boxes`   | Multi-instance cumulative presence   |
| `boxes`         | Per-instance localization confidence |
| `multiple`      | Multilabel category probabilities    |
| `estimate`      | Numerical-estimate quantile levels   |

These mappings use piecewise-linear interpolation over monotone calibration knots.

For typed outputs, this is different from ordinary softmax temperature scaling.

It allows the model's raw confidence or presence estimates to be adjusted using fitted empirical relationships.

The estimate calibration table is especially interesting because it transforms quantile levels before the values are read from the numerical distribution.

The output interval therefore reflects the checkpoint's calibrated quantile transformation, not simply the unmodified 10th and 90th percentiles of the raw grid distribution.

This creates a general architectural distinction between:

1. Model scoring.
2. Calibration of the score distribution or confidence.
3. Conversion of the calibrated output into a typed application value.

The released model provides all three stages within its implementation.

However, the calibration tables are fitted to specific evaluation distributions. Their presence does not eliminate the need to verify calibration under the intended workload, especially after quantization or changes to category definitions.

Sources:

[https://huggingface.co/LiquidAI/d1-2B/blob/main/calibration.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/calibration.py?utm_source=chatgpt.com)

[https://huggingface.co/LiquidAI/d1-2B/blob/main/calibration.json](https://huggingface.co/LiquidAI/d1-2B/blob/main/calibration.json?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main+1



## 10. Prompt rendering and inference extension points

### 10.1 State serialization and structural escaping

The default state-rendering mode is `json_only`.

Structured Python inputs are serialized using JSON formatting before being incorporated into the inference prompt.

The renderer also contains an escaping mechanism for literal strings that resemble model control tokens.

For example, a source document may contain text resembling ChatML delimiters or special image tokens. Interpreting such strings as actual prompt structure would corrupt the distinction between source content and model instructions.

The implementation inserts a zero-width separator into matching special-token strings so they remain ordinary source text at tokenization time.

This prevents a class of structural prompt-rendering errors, but it should not be confused with a comprehensive defense against semantic prompt injection.

The model can still misinterpret adversarial or misleading source content.

### 10.2 Inspectable rendering

The lower-level engine exposes:

```
rendered = model.engine.render(    state,    model.engine.ask(question),)
```

This provides access to the text representation used for a particular state and question.

It can help explain how the model receives candidate descriptions, binary criteria, structured JSON, and specialized answer markers.

This also reveals a useful distinction between the public question format and the internal prompt format.

For example:

- A Choice question is rendered with candidate aliases.
- An ordinal Score question uses indexed levels.
- A Read question introduces dedicated start/end answer positions.
- A Box question introduces presence and coordinate positions.
- A multilabel Choice question uses separate binary readout positions for its candidates.

These are distinct internal prediction structures, despite being exposed through a common `system_one()` API.

Source: `prompt.py`, `question_block()`, `suffix_layout()`, and `plain_offsets()`.

[https://huggingface.co/LiquidAI/d1-2B/blob/main/prompt.py](https://huggingface.co/LiquidAI/d1-2B/blob/main/prompt.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/d1-2B at main



## 11. Boundaries and unverified extensions

The expanded reference should retain several distinctions between implemented functionality and possible future extensions.

Specialized training: Liquid AI provides general fine-tuning tools for its model family, but the reviewed primary sources do not establish a complete, officially supported d1-2B-specific procedure for retraining every decision type, pointer reader, spatial readout, and calibration component.

Persistent inference caching: Shared-state processing is implemented inside question groups. A stable public API for retaining and reusing a processed state across separate `system_one()` calls has not been established.

Exhaustive entity enumeration: Typed extraction reads a bounded source span for each question. It is not equivalent to a native unrestricted NER system that returns every matching span in a document.

Spatial and temporal tracking: The vision implementation supports object localization and instance detection, while video enables decisions over temporal visual context. A native tracking interface with persistent object identities across frames has not been verified.

Audio: Audio support exists in the shared media implementation, but d1-2B itself is not the audio-capable checkpoint.

Generic generation infrastructure: Hugging Face's autogenerated deployment examples for standard text-generation servers should not be regarded as verification that those servers implement the specialized System One protocol.

Checkpoint-version differences: Source implementation support for newer prompt configurations, including larger instance counts, does not establish equivalent functionality for the released d1-2B checkpoint.

These boundaries are important because model-source repositories frequently contain abstractions intended for several architectures or future checkpoints. A capability should be attributed to d1-2B only when it is actually exposed and supported by that checkpoint.

## 12. Concluding technical perspective

The additional functionality substantially enriches the model's practical capabilities without changing its fundamental identity as a typed semantic-decision engine.

Several mechanisms are especially important architecturally.

First, the decision interface is more programmable than the basic JSON examples suggest. Explicit binary criteria, dynamic candidate aliases, native question dataclasses, lower-level probability access, and abstention support allow applications to express more precise decision semantics.

Second, the typed readers incorporate nontrivial deterministic processing. Pointer-based extraction, locale-aware numeric and date parsing, source-span constraints, and JSON provenance provide stronger structural guarantees than a simple model-generated string.

Third, the numerical and visual readers expose richer probabilistic information than their top-level answers initially suggest. Grid distributions, calibrated quantiles, object-presence probabilities, and localization confidence can support decisions that account for different kinds of uncertainty.

Finally, the runtime interfaces are not semantically identical. Transformers exposes the complete model-specific functionality, while Ollama and llama.cpp provide more restricted decision interfaces with different output conventions.

The most useful interpretation is therefore to treat d1-2B as a combination of a learned semantic representation, specialized answer-slot mechanisms, calibrated readouts, and deterministic typed postprocessing—rather than as a conventional classifier with a more flexible prompt.

That distinction explains much of its functionality, its integration opportunities, and the limitations that matter when using it from Python.