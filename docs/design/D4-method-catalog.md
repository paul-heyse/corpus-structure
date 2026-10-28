# D4 · Method catalog

**Proposed (2026-10-28).** Every analysis method the pipeline can run: what it reads, which
observations it writes ([D1 §9](D1-knowledge-representation.md#9-observations)), how a library
realizes it, how it is configured and measured, and when it enters. Policies decide which
methods run on which units ([D6](D6-orchestration-metrics-policies.md)); consolidation turns
their observations into entities and claims ([D5](D5-consolidation-identity-confidence.md)).

The cards are deliberately complete on contract (unit, inputs, outputs, configuration) and
lighter on library detail. The library-leverage lane may deepen each card's **Library
realization** subsection directly; anything that changes a contract goes in a
`> Library proposal (L-nn):` block for the design owner ([plan](../plans/README.md)).

## 1. The method contract

A method is a Python class in `methods/` (or `ingest/` for M01–M03) registered under a stable
name:

```python
class Method(Protocol):
    name: str                      # 'extract.gliner_schema'
    version: str                   # bump on any behaviour change
    family: str                    # D3 ops.method.family
    unit_type: str                 # 'rendition' | 'segment' | 'span' | 'entity' | 'claim' | 'alternative_group' | 'run'
    Config: type[BaseModel]        # pydantic model of params; canonical JSON → config hash
    resources: Resources           # cpu | gpu(encoder) | gpu(llm) | agent; batch size; max concurrency

    def select(self, run: RunView, cfg: Config) -> Iterable[UnitRef]: ...      # default units, when no policy narrows them
    def input_digest(self, unit: UnitView, cfg: Config) -> bytes: ...          # what the result depends on (D6 §4)
    def run(self, units: Sequence[UnitView], cfg: Config, ctx: MethodContext) -> Sequence[UnitResult]: ...
```

Rules every method follows:

1. **Write observations, never knowledge.** A method returns `ObservationDraft`s (kind, span or
   segment, payload, score). Only M01 and M03 also write evidence rows (renditions, segments);
   spans are upserted by the repository layer for any writer; only consolidation (M17, M18)
   writes entities and claims.
2. **Outcome per unit.** `produced` (at least one observation), `empty` (ran correctly, found
   nothing: an observation-free `empty` task outcome, so absence is recorded, not silent) or
   `failed` (with an error payload). A unit result never mixes failure with partial output; a
   method that can partially fail reports the failed part as an observation with `outcome:
   failed`.
3. **Deterministic given inputs.** Same unit, same config hash, same model weights → same
   observations. Sampling LLM methods fix a seed and record it in the config. This is what makes
   task reuse (D6 §4) valid.
4. **Declared dependencies.** `input_digest` covers the unit's text, every observation kind it
   reads (by their task ids), the compiled-artifact hashes it uses (extraction schema, JSON
   Schema, rule set), and model revisions. Anything not in the digest must not influence output.
5. **Small payloads.** Payloads carry offsets and references, not copies of segment text.
6. **No routing inside methods.** A method does not decide to call another method or tier.
   Escalation is a policy decision on measured outcomes.

**Configuration.** Defaults live with the method; domain-specific parameters (math macro map,
binder lexicon, alias head words, extraction patterns) live in the domain pack's
`methods.yaml`, keyed by method name. The effective configuration is the merge, hashed as one
canonical JSON document (`cfg:` key, D1 §10).

## 2. Tiers

| Tier | Methods | Cost per unit | Used for |
|---|---|---|---|
| Deterministic | M01–M03, M08, M09, M11–M13, M15, M17–M23 | ms | Everything they can do; never skipped |
| Encoder (GPU or CPU) | M04, M05, M06, M07, M14 | 10–100 ms | Candidate mentions, relations, labels, links on every unit from phase 1 |
| Local LLM (vLLM on the RTX 5090) | M10, M16 | 1–20 s | Claim proposals where encoders leave gaps; pre-adjudication |
| Agent (Opus via MCP) | M24 | minutes, batched | Phase 0 extraction; final adjudication; dispatches golden passes, which Sonnet subagents author (D7 §3, ADR-0011) |
| Hosted LLM (later) | M10 and M16 configurations against a hosted endpoint | s, priced | Production escalation |

The LLM tiers share one prompt and packet format (§4), so a configuration that worked on the
local model moves to a hosted model by changing the endpoint and model name only.

## 3. Catalog

**Entry**: *base* methods run in every run of their phase; *conditional* methods enter only
when a named measured gap calls for them (D6 §7, D0 "deliberately left out").

| Id | Name | Family | Unit | Writes | Tier | Phase | Entry | Spike |
|---|---|---|---|---|---|---|---|---|
| M01 | `ingest.html` | ingest | document | rendition, segments, `author_markup` | det. | 0 | base | S1 |
| M02 | `profile.segments` | profile | rendition | measurements | det. | 0 | base | S1 |
| M03 | `segment.sentences` | ingest | rendition | `sentence` segments | det. | 0 | base | S1 |
| M04 | `embed.segments` | profile | segment, entity (aliases) | embeddings | encoder | 1 | base | S7 |
| M05 | `classify.segments` | extract | segment | `classification` | encoder | 1 | base | S2 |
| M06 | `extract.gliner_schema` | extract | segment | `mention`, `attribute`, `record` | encoder | 1 | base | S2 |
| M07 | `extract.gliner_joint` | extract | segment | `mention`, `relation` | encoder | 1 | base | S2 |
| M08 | `extract.patterns` | extract | sentence | `mention`, `relation` | det. | 1 | conditional | — |
| M09 | `extract.math` | extract | math segment | `mention`, `relation` | det. | 1 | base | S5 |
| M10 | `llm.propose_claims` | llm | unit packet | `claim_proposal` | local LLM | 1 | base | S3 |
| M11 | `normalize.formula` | normalize | math segment | `value` | det. | 1 | base | S5 |
| M12 | `normalize.quantity` | normalize | span | `value` | det. | 1 | base | — |
| M13 | `resolve.symbol_scope` | resolve | rendition | `scope` | det. | 1 | base | S0, S5 |
| M14 | `resolve.concept_link` | resolve | observation (mention) | `link` | det. + encoder | 1 (vectors 2) | base | S7 |
| M15 | `resolve.record_link` | resolve | run | `link` | det. (Splink) | 2 | conditional | — |
| M16 | `llm.judge` | llm | alternative group, claim, identity group | `judgment` | local LLM | 1 | base | S3 |
| M17 | `consolidate.entities` | consolidate | run | entities | det. | 0 | base | S6 |
| M18 | `consolidate.claims` | consolidate | run | claims, links | det. | 0 | base | S6 |
| M19 | `validate.rules` | validate | claim | `verification` | det. | 0 | base | S4 |
| M20 | `validate.conditions` | validate | claim, statement | `verification` | det. (z3) | 2 | conditional | S5 |
| M21 | `verify.statistics` | verify | claim | `verification` | det. | 4 | base | S5 |
| M22 | `classify.cues` | extract | sentence | `classification` | det. | 1 | base | — |
| M23 | `derive.claims` | consolidate | run | `claim_proposal` (derived) | det. | 2 | base | — |
| M24 | `agent.opus` | agent | unit packet, alternative group | `claim_proposal`, `judgment` | agent | 0 | base | S0 |

Not methods: metric computation (D6 §6), alignment and scoring (D7 §5), confidence estimation
(a consolidation step, D5 §6).

## 4. The shared LLM packet and prompt

M10, M16 and M24 (and hosted configurations later) use one packet format and one compiled
output schema. The point is that the agent tier and the local tier see the same evidence in the
same shape, so their outputs are comparable and a prompt tuned on one transfers.

### 4.1 The packet

A packet is assembled by `methods.llm.packet` from the database; nothing in it is free text
written by the pipeline:

```text
# Unit  <unit_key>  ·  <document title> › <section path>  ·  kind: <segment kind>[, statement kind: <label>]
## Standing context
[c1] <sentence that binds a symbol used in the unit, from M13 scope observations>
[c2] …
## Known entities                         (canonical labels already identified for this page)
- distribution family "normal" · aliases: normal distribution, normally distributed
- family parameter "normal · mean"
## Text
[s1] <first sentence of the unit, canonical text, LaTeX kept verbatim>
[s2] …
## Hints                                   (optional, config hints: none | mentions | mentions+relations)
- mention "normally distributed" [s1] → distribution family (0.91)
- relation has_distribution(X, normally distributed) [s1] (0.77)
## Alternatives                            (judge packets only)
A1: <claim in compact form> · evidence [s2] · from M10 (0.62)
A2: …
```

- **Size caps.** Default 3,000 tokens of text and context for the local LLM, 6,000 for the agent
  (D8 §3). A unit larger than the cap is split at sentence boundaries into numbered parts that
  share the standing context; the split is recorded in the task. The **output** budget is sized from
  batch size, not unit size: a batch runs two to nineteen times its unit's tokens (S0 core units:
  units at most 345 tokens, batches up to about 2,500; record s0.sizes, Measured).
- **Standing context** is at most six sentences, chosen by M13: for each symbol the unit uses,
  the sentence holding the binding site M13 assigns it when that sentence lies outside the unit,
  plus the site a "Suppose again" reopens; a sentence identical to one of the unit's is left out.
  Each carries an id (`c1`, …) that evidence may cite (D2 §7.3). A self-contained unit has none;
  without M13 output the packet has none. A positional rule ("the previous binding sentences in the
  section") is not used: it handed one exercise another exercise's setup and missed a premise stated
  before the unit.
  > Status: **Tested** (S0-R2, 2026-10-28; records s0r2.inputs, s0r2.scores; `code/s0r2_sample.py`)
- **Known entities** are the canonical labels of global entities in the reference run, or
  proposed earlier in this run, that are linked to the page (at most 30). Proposals reuse them,
  so identity across units holds by label (D5 §3.3). Golden packets omit them (D7 §3.2).
- **Hints** are encoder observations above a threshold. They are off by default for proposal
  tasks (to keep LLM output independent evidence for confidence, D5 §6) and on for judge tasks.

### 4.2 The prompt

| Part | Source | Changes when |
|---|---|---|
| System instructions | `methods/llm/prompts/<task>.md` | Method version |
| Guideline core rules | Guideline §10 sections tagged `core` (D2 §10) | Guideline version |
| Schema inventory | The generated annotator reference (D2 §10.10): per predicate its subject and object, statement role, modality and condition rule, with value and node shapes; filtered to the classes and predicates relevant to the segment's statement kind when it exceeds 1,500 tokens (local LLM); whole for the agent and golden passes | Schema version |
| Examples | k (default 2) adjudicated **dev-split** golden units nearest to the unit by M04 embedding, rendered as packet + expected batch; never the test split (D7 §4). Golden passes instead get the reference's fixed worked examples, from pages outside every split | Golden set version |
| Packet | §4.1 | Unit |
| Output instruction | "Return one ClaimProposalBatch" plus the JSON Schema for tiers that do not enforce it | Schema version |

### 4.3 Output form and post-processing

Models cite evidence **by quote, not offset**: each evidence item is `{sentence: "s2", quote:
"…", role}`, and anchors of statements likewise. Shared post-processing in `methods.llm.parse`:

1. **Validate** against the compiled JSON Schema (vLLM enforces it during decoding; agent
   output is validated on submission, D8).
2. **Locate quotes** by a cascade that never loses source offsets: exact in the cited sentence,
   then in the unit; exact up to spacing (a `regex` pattern of the quote's non-space characters
   joined by optional whitespace and spacing commands, matched in the original text, so no
   offset map is needed); the same after expanding the rendition's macros on both sides; then
   `rapidfuzz.fuzz.partial_ratio_alignment` (cutoff 85, trailing punctuation stripped), refined
   inside its window by `regex` `BESTMATCH` with a bounded error count and a timeout. Every span
   is snapped outward to word boundaries; each result records its step and edit counts. The
   result is a span (rendition offsets). An unlocated quote leaves the item in the batch with
   `evidence_unlocated: true`; consolidation treats such items as unsupported by evidence (D5).
   > Decision: [ADR-0009](../adr/0009-math-grammar-authority.md)
   > Status: **Tested** in the spike instruments (2026-10-28): 733 of 735 S0 quotes exact, 2 after spacing, none fuzzy ([s0.stored](../design_review/evidence/2026-10-28_design-spikes/records/s0.stored.json))
3. **Check references and types**: local refs resolve; subject and object types match the
   predicate's domain and range (entity-type side table, D2 §7.3).
4. **Normalize math**: `$…$` and `\(…\)` are equivalent; values of type `formula` keep the LaTeX
   as given and are parsed by M11 in consolidation.
5. **Keep rejects.** Items failing 3 or 4 are kept in the observation payload under `rejected`
   with reasons; they count in metrics (malformed-output rate) but are not consolidated.

A judge output is `{target, decision ∈ {accept, reject, choose, merge, split, unsure}, chosen?,
rationale (≤ 2 sentences), confidence ∈ {low, medium, high}}`.

## 5. Ingest and profiling

### M01 ingest.html

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| document | original bytes; adapter config | `kb.rendition`, `kb.segment` (structural kinds), `author_markup` observations | deterministic · 0 · base |

**Behaviour.** Parse HTML; drop excluded content by declared rules; record the page's
`\newcommand` macros (Siegrist's `div.latex` block) in the rendition's `parse_detail.macros`; walk the body in reading
order emitting canonical text by D1 §3.1 and a segment for each block element and each math
delimiter pair; attach author markup to segment `attrs` and emit it as `author_markup`
observations (`dfn` terms with offsets, unit ids and classes, `details`, links with targets).
Tables become `table`/`table_row`/`table_cell` segments with cell text in canonical text.
Rendered-only text (reference markers, quotation marks, sub-list markers, `details` summaries)
and orphan text follow D1 §3.1 and §3.2.

**Page macros.** The rendition's macro table is the page's own `\newcommand` definitions
(`parse_detail.macros`); the domain pack's macro map supplies only names the page does not
define. Consumers that expand or read macros (the math grammar, M09, M11, quote location) take
the rendition's table, because the same name has different bodies on different pages: `\mse` is
`\text{mse}` on some and `\text{MSE}` on others, `\kur` is `\text{kurt}` or `\text{kur}`.
> Status: per-page macros **Tested** on 78 Siegrist pages (S1, 2026-10-28): 29 distinct definitions recorded per rendition; the common names (`\N`, `\R`, `\E`, `\var`, `\P`, `\sd`) agree across pages, several others do not ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json)); the fallback to the pack map is **Proposed**

**Configuration.** A *source profile* (one per source family; Siegrist's is drafted in
[D2 §12.1](D2-schema-and-guidelines.md#121-methodsyaml)) is a set of CSS selectors, each with a
role payload: exclusion rules (scripts, the macro block, navigation including Siegrist's
`ul.map` chapter lists, controls, images), the title, section headings (`h3` and `h4` open
nested sections), the unit selector (`div.unit`), statement-kind hints from block classes
(`p.dfn` → definition, `p.math` and `p.stat` → theorem, `p.Proof` → proof, `p.app` → not
claim-bearing) and from section titles ("Computational Exercises" → exercise), `details` kinds
(proof or solution), math delimiters and display environments (`align`, `align*`), the macro
source (`div.latex`), and the rendering conventions of D1 §3.1. The profile lives in the domain
pack's `methods.yaml`; it is about the source's HTML, not the domain. Either selector engine,
cssselect2's `Matcher` or the cssselect→XPath translation, evaluates the profile identically;
the `Matcher` also reports an element claimed by two roles, and the XPath form is portable to
other tools (trafilatura's `prune_xpath` accepted it unchanged).
> Status: **Tested** on 78 Siegrist pages (S1, 2026-10-28): both engines select identical node sets for every rule on every page, with no role conflicts and no unclassified block ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json))

A second source needs more of the profile than Siegrist does: a `layout` role (tables used for
layout), section rules with a heading source (NIST's subsections are layout-table rows), a
`verbatim` role (`pre` keeps its line breaks), per-selector list markers, and per-selector
rendering of reference links and `img[alt]`. Generic defaults: `pre` keeps whitespace, an
`img` with `alt` text is never silently dropped, and a list without items is a block.
> Status: **Proposed**, from the NIST probe on 8 pages (S1, 2026-10-28), where only the Siegrist `scripts` and `images` rules matched anything ([s1.nist](../design_review/evidence/2026-10-28_design-spikes/records/s1.nist.json))

**Parser.** html5lib through `lxml.html.html5parser`, whose HTML5 tree construction closes an
open `<p>` before a block element. libxml2 (`lxml.html.document_fromstring`) keeps a `<details>`
that follows an unclosed `<p>` inside the paragraph, with its summary and proof; it is
acceptable only with a repair rule that closes `<p>` before block elements.
> Status: **Tested** on 78 Siegrist pages (S1, 2026-10-28): the two parsers give canonical texts of equal length on every page and differ in segments on 4 pages, each at an unclosed `<p>` before `<details>`, where html5lib's tree is the correct one ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json)); the corpus run used libxml2, and a rerun with html5lib as the default is open

**No profile-free fallback.** trafilatura does not produce M01's canonical text for a profiled
source: it drops headings next to units, every `details` summary, captions and short proofs
ending in an empty reference, and returns no units, `details` or sections as structure. It may
draft a provisional rendition (`profile: none`, `parse_status: partial`) to help write the
profile of a new source.
> Status: **Measured** on 78 Siegrist pages (S1, 2026-10-28): trafilatura 2.3.1 misses 5.3% of canonical content, 93% of `h2`–`h4` headings, all `details` summaries and 99% of captions; it keeps every math span it outputs verbatim ([s1.trafilatura](../design_review/evidence/2026-10-28_design-spikes/records/s1.trafilatura.json))

**Library realization.** The parser above; CSS selectors through `lxml.cssselect` for exclusions
and unit selection; math delimiting by one `regex` pattern generated from the profile's declared
delimiters and display environments (an escaped backslash is skipped; a span stops at the next
delimiter, so an unclosed one is `partial` and the scan resynchronizes); each span validated by
the math grammar (M11); `html.unescape`, `unicodedata.normalize("NFC")`. Source-specific facts
(unit, reference, section and layout selectors, delimiters, the macro source) are profile data,
never adapter code.
> Decision: [ADR-0009](../adr/0009-math-grammar-authority.md)
> Status: **Tested** in the S1 adapter (2026-10-28): the generated pattern delimits identically to the scanner on 517 blocks ([s1.profile-delimiting](../design_review/evidence/2026-10-28_design-spikes/records/s1.profile-delimiting.json))

**Measured by.** `parse_status` per rendition and segment; excluded-character share; segment
counts by kind; author-markup counts against the corpus index (`siegrist_sections.tsv`).
> Status: **Measured** on 78 Siegrist pages (S1, 2026-10-28): units, definition units, `dfn` terms, `details` and `\[` display math equal the index on 77 of 78 pages (on the exception the index counts a commented-out unit); `dfn` terms item by item, no difference ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json))

**Port.** The rules, not the code shape, of `corpus-intelligence` `html_adapter` (≈1,000 lines;
D9 §7). Spike: S1.

### M02 profile.segments

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| rendition | segments, `author_markup` | `ops.measurement` rows per segment | deterministic · 0 · base |

Computes the features policies route on: length in characters and approximate tokens; inline
and display math counts; math character share; presence of `dfn`; the statement-kind hint from
block class or section title; nesting depth; whether the segment sits in a `details` block. Pure
function of the rendition. No observations: these are measurements (D6 §6), because nothing
consolidates them.

### M03 segment.sentences

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| rendition | canonical text, structural and math segments, reference markup | `sentence` segments | deterministic · 0 · base |

**Behaviour.** Splits every `paragraph`, `list_item`, `table_cell` and `caption` into sentence
segments; never splits inside math; never lets a sentence cross its parent block. Runs as part
of rendition construction: its configuration hash is part of the rendition's adapter
configuration, so sentence segments are as stable as the other segments.

**Library realization (variant b′; `OPEN-D1-1` closed by S1).** spaCy 3.8 `en_core_web_sm` with
the parser's sentence boundaries, after a step that, using the math segments and the reference
markup, merges each inline math span and each rendered reference marker (`[n]`, D1 §3.1) into
one token with `doc.retokenize()` (`POS=PROPN`, `TAG=NNP`) and sets `is_sent_start = False` on
reference markers and on every token of a display formula after its first. The parser respects
preset boundaries, and token offsets stay in canonical text, so no offset mapping is needed.
Math is never presented to spaCy as text: on raw text the parser splits inside formulas, an
opaque placeholder loses real boundaries, and math rendered to Unicode adds false splits after
list markers and mid-clause.
> Status: **Measured** on a sentence gold of 85 blocks with 49 internal boundaries, marked identically by two independent markers (S1, 2026-10-28): boundary F1 1.00 for b′ against 0.80 for raw text, 20 of whose 24 false splits fall inside math, and 0.70 for an opaque mask; under b′ the rule-based sentencizer reaches 0.99 and the `trf` parser 0.98 ([s1.sentence-gold](../design_review/evidence/2026-10-28_design-spikes/records/s1.sentence-gold.json))

**Measured by.** Boundary F1 against S1's sentence gold whenever the pipeline, model or math
presentation changes. Sentences per paragraph and the share of sentences beginning lower-case
or with a math token are diagnostics only, not quality measures.
> Status: **Measured** (S1, 2026-10-28): the two proxies flag 3 of the 20 blocks the raw-text pipeline segments wrongly, so they cannot stand in for a gold ([s1.sentence-gold](../design_review/evidence/2026-10-28_design-spikes/records/s1.sentence-gold.json))

### M04 embed.segments

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| segment (`unit`, `paragraph`, `sentence`); entity (its aliases) | text | `kb.embedding` | encoder · 1 · base |

**Behaviour.** Embeds segments for example selection (§4.2) and retrieval in agent packets, and
entity aliases with their class description for concept linking (M14). Not an observation:
embeddings are derived data keyed by model configuration.

**Library realization.** Qwen3-Embedding (0.6B or 8B, dimension by S7, `OPEN-D3-2`), served by
vLLM's pooling runner or `sentence-transformers` in process (D6 §5 decides GPU placement);
query-side instruction prefixes as the model card specifies; Matryoshka truncation to the
stored dimension, then L2 normalization; stored as `halfvec`.

## 6. Encoder extraction

### M05 classify.segments

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| segment of the target kind of each classification enum (`unit`, `paragraph` for `StatementKind`; `sentence` for `ClaimModality`) | text, M02 hints | `classification` | encoder · 1 · base |

**Behaviour.** One classification task per schema enum with `ci:extract: classification`.
Author-markup hints are not inputs to the classifier; a policy may skip classification where
markup gives the statement kind, and consolidation weighs both (D5 §6).

**Library realization.** GLiNER2 `Classifier` with a `ClassificationSchema` compiled from the
enums (`.single()` per task); constraints from the schema where they exist (for example
`C.excludes((modality, posed), (statement_kind, definition))` if the guideline states it);
`ClassificationConfig(decoder="auto", on_infeasible="min_violations")`. Payload records
`feasible` and `violations`; infeasible results score lower in consolidation.

### M06 extract.gliner_schema

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| `paragraph`, `list_item`, short `unit` (≤ 384 words) | text (raw or masked), compiled schema (a) (D2 §7.2) | `mention`, `attribute` (`record` once the schema declares a structure; none in v0) | encoder · 1 · base |

**Behaviour.** One combined `extract` call per segment with entity types, span attribute groups
and record structures from the compiled schema. Mentions inside a math span are kept with
`math_ref` (the math segment key).

**Configuration.** Checkpoint (`gliner2.5-base-v1` first), per-type thresholds (schema
`ci:threshold` or method default 0.5), math handling (`raw` or `mask`, by S2, `OPEN-D2-2`),
batch size.

**Library realization.** `GLiNER2.from_pretrained`; `Schema.from_dict` from the compiled
artifact; `batch_extract(..., include_spans=True, include_confidence=True)`; long units through
`extract_long` with chunk overlap rather than truncation. Masking replaces each inline math span
by a placeholder token (`⟨m3⟩`) and maps placeholders back to the math segment afterwards.

**Measured by.** Mentions per 100 words by type; share inside math; recall against goldens by
type (D7).

### M07 extract.gliner_joint

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| as M06 | text, compiled joint schema (b) (D2 §7.2) | `mention`, `relation` | encoder · 1 · base |

**Behaviour.** Joint entity–relation decoding for predicates with `ci:extract: relation`.
Relation observations reference their head and tail mention observations from the same task.
An infeasible decode is recorded as one observation with `outcome: failed` and `feasible:
false`, never as an empty result.

**Library realization.** `JointIE.from_pretrained`; schema built with `joint.create_schema()`
from the compiled artifact (typed endpoints, `unique_head` for functional predicates,
`no_self_loops()`); `JointIEConfig(optimizer="beam", beam_size=32)`; `return_lattice=True` only
in debug slices (lattices are large).

### M08 extract.patterns

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| sentence | spaCy parse, math segments, `author_markup` | `mention`, `relation` | deterministic · 1 · **conditional** |

**Enters when** a measured recall gap on a predicate or class persists after schema
descriptions and examples were improved (D6 §7 policy `gap.pattern_candidate`). Candidates
known from the trace: `respectively` alignment of coordinated lists ("location parameter μ and
scale parameter σ, respectively"), `<dfn>` terms as mentions of the class the definition
introduces, "X has the F distribution with P p" frames.

**Library realization.** spaCy `Matcher`, `PhraseMatcher` and `DependencyMatcher`, with
patterns in the domain pack's `methods.yaml`, each pattern naming the schema class or
predicate it emits. Math tokens are merged as in M03 so patterns can match a formula as one
token.

### M09 extract.math

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| `math_inline`, `math_display` | LaTeX source, macro map | `mention` (label `symbol`), `relation` (`in_set`, `equals`) | deterministic · 1 · base |

**Behaviour.** Tokenizes LaTeX into a node tree and emits a `symbol` mention for each identifier
occurrence with its decoration (`X_1` keeps the subscript; `\sigma^2` records base `\sigma` and
power 2), and math-internal relations a scoping or binding step needs: membership (`a \in \R`),
equality (`Y = a + b X`), distribution statements written in notation (`X \sim
N(\mu, \sigma^2)`) as `relation` with label `stat:has_distribution` when the domain pack maps
the notation.

**Library realization.** The math grammar of M11: symbol occurrences with offsets, sub- and
superscripts as tree structure, relations and memberships as typed nodes; the page's macros
recorded by M01, then the pack's fallback macro map (D2 §12.1). No SymPy conversion here.
> Decision: [ADR-0009](../adr/0009-math-grammar-authority.md)
> Status: **Implemented** in the spike instruments (2026-10-28), exercised by the M13 probe; production code not written

## 7. LLM proposals and judgments

### M10 llm.propose_claims

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| unit packet (§4.1): a `unit`, or a `paragraph` outside units | packet, prompt parts (§4.2) | `claim_proposal` | local LLM · 1 · base |

**Behaviour.** One ClaimProposalBatch per packet. Policies select which units get it: in phase 1
every unit whose statement kind is claim-bearing; from phase 3 only units where encoder coverage
is measured as insufficient (D6 §7).

**Configuration.** Endpoint and model (`Qwen3.5-9B` first; S3 compares a larger quantized model,
`OPEN-D4-1`), `temperature: 0`, `seed`, `max_tokens`, reasoning on or off (`OPEN-D4-2`), hints
mode, examples k, one repair retry with validation errors appended.

**Library realization.** vLLM 0.31 OpenAI-compatible server from the existing
`services/vllm-native` environment; structured output in JSON Schema mode with the compiled
schema (exact request field checked in S3); prefix caching on, since system, guideline and
inventory form a shared prefix across units.

**Measured by.** Malformed-output rate; unlocated-quote rate; claims per unit; precision and
recall against goldens by predicate; tokens and latency (task `cost`).

### M16 llm.judge

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| alternative group, low-confidence claim, or identity group (D5 §3.7) | judge packet (§4.1 with Alternatives) | `judgment` | local LLM · 1 · base |

**Behaviour.** Pre-adjudication: decides what it can and writes a rationale either way. Its
judgments enter confidence as one more source (D5 §6); a `judgment` with confidence `low` or
decision `unsure` leaves the unit for the agent tier if a policy routes it there.

### M24 agent.opus

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| unit packet (mode `extract`) or judge packet (mode `adjudicate`) | packet via MCP `read_unit`, prompt parts via `read_instructions` (D8) | `claim_proposal` or `judgment`, plus an `ops.intervention` row that references it | agent · 0 · base |

**Behaviour.** The pipeline never calls Opus. A task for M24 is created with status
`awaiting_agent`; the Claude Code session pulls it with `queue_next`, reads the packet, and
submits through `propose_claims` or `adjudicate`; the submission is validated and parsed exactly
as §4.3 and completes the task. The prompt parts' hashes are part of M24's input digest, so a
guideline, schema or example change requests new proposals (D6 §4). In phase 0 M24 is the only extractor; later it receives what
policies escalate. Golden authoring is not M24: it is a D7 protocol with its own tools and its
own tables.

## 8. Normalization and resolution

### M11 normalize.formula

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| math segment; also LaTeX strings inside claim proposals (called by consolidation) | LaTeX, macro map | `value` (`formula`, `set`, `interval`) | deterministic · 1 · base |

**Behaviour.** Expands source macros, parses to SymPy, and returns a D1 §6 value with `latex`,
`sympy` (`srepr`), `parse` (`ok`, `partial`, `failed`) and the free symbols. Set expressions
(`\R \setminus \{0\}`, `(0, \infty)`) become SymPy sets. Symbol binding is not done here: it
needs scope (M13) and claims, so consolidation binds (D5 §4).

**Library realization.** One math grammar for every reader of math: SymPy 1.14's Lark LaTeX
grammar, unedited, extended by a separate file through Lark `%extend`/`%override` (typed start
symbols formula, relation, member, set; sub- and superscripts as rules; set constructs; operator
and set macros generated from the rendition's macro table, never named in the grammar); Earley
with explicit ambiguity resolved only from declared context, otherwise `ambiguous`; failures
carry Lark's error class, position and a category; a subclass of SymPy's `TransformToSymPyExpr`
for the extended rules; canonical form (D1 §6.2) written from the tree; one parser cached per
macro table; SymPy pinned as a hold. The ANTLR backend remains the comparison for `OPEN-D4-3`;
`sympy.srepr` for storage.
> Decision: [ADR-0009](../adr/0009-math-grammar-authority.md)
> Status: **Measured** in the spike instruments (2026-10-28): 976 of 1,532 spans parse on a 78-page sample, the rest ambiguous or failed by recorded category ([s0.instruments](../design_review/evidence/2026-10-28_design-spikes/records/s0.instruments.json)); coverage is S5's question

**Measured by.** Parse rate by math kind and page; failure categories (S5).

### M12 normalize.quantity

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| span (numbers in text and table cells) | text | `value` (`number`, `interval`, quantity with unit) | deterministic · 1 · base |

Numbers with units, ranges, percentages and tolerances in prose and tables (the rod-and-hole
exercise, U8). **Port** of `corpus-intelligence` quantity and units (≈860 lines) and table
quantities (≈730 lines), with pint for units (D9 §7).

### M13 resolve.symbol_scope

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| rendition | segment tree, sentences, `symbol` mentions (M09), math relations | `scope` | deterministic · 1 · base |

**Behaviour.** Finds binding sites and assigns every symbol mention to one:

1. A **binding site** is a symbol mention in a binder context: a sentence starting with a binder
   ("Suppose", "Let", "Assume", "Fix", "Define"), a `where`/`for` clause, a membership relation
   (`a \in \R`) in such a sentence, or the left side of a definitional equality.
2. Its **extent** is the smallest enclosing `unit`; a binding in a paragraph outside units binds
   to the end of the enclosing `section` or until the same symbol is bound again in that section
   (`OPEN-D1-2`, `OPEN-D1-4`). "Suppose again" re-opens the previous section-level binding
   instead of creating a new one.
3. Every other mention of the symbol is assigned to the innermost binding site whose extent
   contains it. A mention without one gets `binding: unresolved`.

The payload names the binding site's mention, the extent segment, and, when the binding sentence
states it, the provisional binding kind (`variable`, `param_of`, `constant`); consolidation
completes bindings with claims (D5 §4).

**Library realization.** Plain Python over the segment tree; binding sites by spaCy `Matcher`
patterns over tokens, generated from the binder lexicon in `methods.yaml` (sentence-initial
binders including "if", clause binders, section-wide phrases, "again"), with each merged math
token carrying its kind from the math grammar (symbol, relation, membership) and its symbol
occurrences; `DependencyMatcher` only where clause attachment decides the binding. A standalone
claim-bearing paragraph is a statement extent; a section-wide binder takes precedence. Spike
evidence: S0 annotators' scopes (`m13_probe.*.tsv`), S5.
> Decision: [ADR-0009](../adr/0009-math-grammar-authority.md)
> Status: **Measured** on the S0 reference (2026-10-28): 20 of 20 annotated symbol scopes reproduced, 18 of 20 without the paragraph rule ([s0.m13-probe-2](../design_review/evidence/2026-10-28_design-spikes/records/s0.m13-probe-2.json))

### M14 resolve.concept_link

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| observation: a `mention` of a **global** class | mention text, alias table of entities in the reference run, embeddings | `link` (top k candidates or a new-entity proposal) | deterministic + encoder · 1 (vectors in 2) · base |

**Behaviour.** Candidate generation in order: normalized-alias exact match; lemma match after
removing the class's head words ("distribution", "family") and mapping adverbial forms
("normally distributed" → "normal"); `rapidfuzz.process.extract` with `token_set_ratio` over
aliases of the same class; from phase 2, pgvector nearest neighbours on alias embeddings. Each
candidate gets features (exact, lemma, fuzzy score, cosine, page co-occurrence); the score is a
logistic model fitted on golden links once there are enough (before: a fixed rule ordering).
Below the new-entity threshold the payload proposes `{"new": {type, label}}`.

**Configuration.** Head words and adverb rules per class in `methods.yaml`; k; thresholds.

**Reference run.** Linking is against the entities of the promoted run plus entities proposed
earlier in the current run (D5 §3), so a family introduced on its own page links from other
pages.

### M15 resolve.record_link

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| run: candidate entities of classes with several identity attributes | candidate entity records (from M17's first pass) | `link` (pair, match probability) | deterministic · 2 · **conditional** |

**Enters when** identity errors on such classes are measured (D7 identity metrics) above the
policy threshold. Example: `FamilyParameter` across pages (family, role, symbol, domain).

**Library realization.** Splink 5 on the DuckDB backend: comparisons per identity attribute
(exact on family key, Jaro-Winkler on label, exact on symbol), blocking on family key, EM
training on unlabeled pairs, `m` probabilities seeded from golden identity pairs and agent
`merge`/`split` judgments when available; `predict()` above a floor becomes `link`
observations, and `cluster_pairwise_predictions_at_threshold` is not used (clustering is
consolidation's job).

## 9. Validation and verification

All three write `verification` observations targeting a claim key of the current run; none
changes a claim. Consolidation's finalization reads them (D5 §8).

### M19 validate.rules

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| claim | claim view, rule context (D5 §8.2), compiled rules | `verification` with `verifier: rule:<id>` | deterministic · 0 · base |

**Library realization.** rule-engine 5.1 `Rule` objects compiled once per schema version under a
typed `Context` (type resolver from the schema, registered functions such as `family_params`);
evaluated per claim; a rule whose `when` is false records nothing.

### M20 validate.conditions

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| claim with conditions; statement | condition trees, values | `verification` with `verifier: z3:<check>` | deterministic · 2 · **conditional** |

**Enters when** conflicts among conditional claims are measured (D5 §5) or verifiers need
satisfiable parameter points. Checks: a claim's conditions are satisfiable (`b \ne 0 ∧ b = 0` is
refuted); two claims with the same subject and predicate and different values have
non-overlapping conditions (else `conflicting`); one claim's conditions imply another's
(`refines` link proposal).

**Library realization.** z3 `Solver` over the D1 §7 condition tree: `member` over reals and
intervals as arithmetic constraints, `cmp` as comparisons, `claim` nodes as Boolean atoms,
`forall` over finite index sets unrolled up to a bound, `phrase` and `unsupported` nodes as
free Boolean atoms (they never make a check `refuted`).

### M21 verify.statistics

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| claim with predicate in the verifier's set | claim view, premise claims of its statement | `verification` | deterministic · 4 · base |

The statistics pack's verifiers (`domains/statistics/verifiers.py`, D2 §7.6):

| Verifier | Checks | How |
|---|---|---|
| `affine_normal` | `has_distribution` conclusions about affine transforms of normal variables (T3) | `sympy.stats.Normal`; compute `E` and `variance` of the transform symbolically and compare with the claimed `param_values` |
| `moments` | `mean_value`, `variance_value` of families with known SymPy distributions | `sympy.stats` closed forms under the claim's parameter bindings |
| `simulate` | `has_distribution` conclusions of transformations and sums (U5, U9, U11) | scipy.stats sampling at parameter points satisfying the conditions (z3 model or a grid), Kolmogorov–Smirnov against the claimed distribution; `consistent` only at p > 0.01 for every point, `refuted` at p < 10⁻⁶ |
| `support` | `support` claims | SymPy set equality with the family's support |

A verifier that cannot map a claim to a computable form returns `not_checkable`; that is
measured (coverage of verification) and is never evidence against the claim.

## 10. Small deterministic helpers

### M22 classify.cues

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| sentence with at least one `relation` or `claim_proposal` evidence span | spaCy parse | `classification` for `polarity`, `hedge`, `attribution`, with cue spans | deterministic · 1 · base |

Negation cues (`neg` dependencies, "not", "never", "no"), hedge cues ("approximately",
"roughly", "it seems", "can be"), attribution frames ("X showed", "according to"). Lexicons in
`methods.yaml`. These complement the learned modality classification of M05 and give
consolidation explicit cue spans to cite.

### M23 derive.claims

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| run (after a first consolidation pass) | accepted and candidate claims | `claim_proposal` with `establishment: derived` and `derived_from` keys | deterministic · 2 · base |

Applies derivation rules declared in the domain pack (`rules.yaml`, section `derive:`): for
statistics, variance → standard deviation (`|b| σ` in T3), transitivity of `special_case_of`,
applying a construction's parameter mapping to a member family. A derived claim inherits the
conjunction of its sources' conditions. Consolidation runs a second, incremental pass for
derived proposals (D6 §2).

## 11. Consolidation (summary)

### M17 consolidate.entities and M18 consolidate.claims

The only writers of `kb.entity` and `kb.claim`. Inputs: every observation of the run (through
`kb.run_observation`), judgments, and the promoted run as reference. Steps, specified in D5:
entity resolution (D5 §3), symbol binding (D5 §4), claim assembly and keying (D5 §5),
confidence (D5 §6), applying judgments (D5 §7), validation status (D5 §8), derived claims
(D5 §9). Phase 0 realization: identity by key, one claim per proposal, no fusion, status from
agent proposals only.

## 12. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D4-1 | Which local model: Qwen3.5-9B at full precision, or a larger quantized model that fits 32 GB with an embedding model beside it | Spike S3 |
| OPEN-D4-2 | Reasoning on or off for structured proposals on the local model (quality versus latency) | Spike S3 |
| OPEN-D4-3 | SymPy LaTeX backend (lark or ANTLR) and the macro map that maximizes parse rate | Spike S5 |
| OPEN-D4-4 | Unit of LLM work: whole `unit`, paragraph, or sentence group; set by S0 output sizes and S3 quality per packet size | Spikes S0, S3; **answered by S0 and S0-R2** for golden and agent packets (2026-10-28): the unit, with query-assembled standing context (§4.1); output budget from batch size; S3 measures local-LLM quality per packet size |
| OPEN-D4-5 | Whether M13's rule-based scoping reaches the S0 annotators' scopes, or symbol scope must come from the LLM proposal | Spikes S0, S5; **answered by S0** (2026-10-28): 20 of 20 annotated scopes with two additions, sentence-initial "if" and paragraph statements (M13); S5 checks math-heavy symbols |
