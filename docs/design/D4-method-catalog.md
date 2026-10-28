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
    Config: type[BaseModel]        # pydantic model of params; canonical JSON → config hash; declares its artifact references
    resources: Resources           # cpu | gpu(encoder) | gpu(llm) | agent; batch size; max concurrency

    def select(self, run: RunView, cfg: Config) -> Iterable[UnitRef]: ...      # default units, when no policy narrows them
    def input_digest(self, unit: UnitView, cfg: Config) -> Digest: ...         # what the result depends on (D6 §4)
    def run(self, units: Sequence[UnitView], cfg: Config, ctx: MethodContext) -> Sequence[UnitResult]: ...

class Digest(NamedTuple):
    bytes: bytes                   # enters the input hash (D6 §4)
    packet_hash: str | None        # packet methods only (M24; M10 from phase 1); None for every other method
```

**The digest carries the packet hash.** A packet method (§4.1) computes its digest from the
assembled packet, so `input_digest` returns that packet's hash beside the digest bytes, from the
same cached assembly; the orchestrator records it on the task when the task is created
(`ops.task.packet_hash`, [D3 §4](D3-database.md#4-ops-methods-policies-runs-and-tasks)), and
`read_unit` serves that assembly (D8 §2.1). The packet is assembled once per task, and the hash the
task records is the one the reuse decision used. Every other method returns `packet_hash = None`.
> Status: **Proposed** (2026-10-28)

**Artifact references.** A `Config` declares the compiled artifacts it reads by `(compiler, kind)`,
for example `(json_schema, batch.model_facing)`, never by hash. The registry resolves each against
the run's schema version (`meta.compiled_artifact`,
[D3 §3](D3-database.md#3-meta-schema-guidelines-and-domain-declarations)) when it builds the run's
method configurations, and the resolved hashes enter the input digest (rule 4), so one named
configuration in `methods.yaml` serves every schema version and a schema change invalidates reuse
without editing the pack.
> Status: **Proposed** (2026-10-28)

The objects in this block (the protocol, `RunView`, `UnitView`, `UnitRef`, `UnitResult`,
`ObservationDraft`, `Resources`, `MethodContext`, `Digest`) and the registry interface are the
method-contract types in `core/method.py` ([D9 §1](D9-repository-and-phase0.md#1-layout)).

Rules every method follows:

1. **Write observations, never knowledge.** A method returns `ObservationDraft`s (kind, span or
   segment, payload, score). Only M01 (with M03, a step of its task) also writes evidence rows
   (renditions, their builds, segments);
   spans are upserted by the repository layer for any writer; only consolidation (M17, M18)
   writes entities and claims.
2. **Outcome per unit.** `produced` (at least one observation), `empty` (ran correctly, found
   nothing: an observation-free `empty` task outcome, so absence is recorded, not silent) or
   `failed` (with an error payload). A unit result never mixes failure with partial output; a
   method that can partially fail reports the failed part as an observation with `outcome:
   failed`.
3. **Deterministic given inputs, or recorded.** Same unit, same config hash, same model weights →
   same observations, for every method except the LLM and agent tiers. Their outputs are
   best-effort reproducible (temperature 0, a seed in the config) but not exactly: online vLLM
   reproduces outputs only under batch invariance, and the agent not at all. Task reuse (D6 §4)
   is valid for them because it reads the recorded observations by input hash instead of
   regenerating them; tests replay recorded responses (D9 §4). S3 measures how often repeated
   local-LLM runs differ.
4. **Declared dependencies, by content.** `input_digest` covers the content the method reads,
   never where that content came from: the unit's content, the payload hashes of the upstream
   observations it reads, the compiled-artifact hashes it uses (extraction schema, JSON Schema,
   rule set; `meta.compiled_artifact`,
   [D3 §3](D3-database.md#3-meta-schema-guidelines-and-domain-declarations)), the prompt-part
   hashes, and the model id and revision. The unit's content is digested so that a reused
   observation never cites another rendition's spans: a rendition-level method digests the
   rendition's content digest ([D1 §10.1](D1-knowledge-representation.md#101-hashing)); a method
   whose observations cite offsets inside a rendition digests the unit's canonical text with its
   segment key, which carries that digest; M24 and M10, whose stored form is derived per rendition
   from a citation frame (§4.3), read the unit only through their packet, and their digest holds
   the hash of the assembled packet text (§4.1), returned beside it as the `Digest`'s
   `packet_hash`. Upstream task ids are provenance
   (`reused_task_id`), never a dependency, so re-running an upstream method with identical output
   leaves its consumers reused (P0CL-02; operator, 2026-10-28). Anything not in the digest must
   not influence output. Methods of unit type `run` (M15, M17, M18, M23, and M19's step in each
   consolidation pass) read the whole run, so their tasks are never reused (D6 §4).
   > Status: **Proposed** (2026-10-28); which form applies is per method, by whether its
   > observations carry rendition offsets
5. **Small payloads.** Payloads carry offsets and references, not copies of segment text.
6. **No routing inside methods.** A method does not decide to call another method or tier.
   Escalation is a policy decision on measured outcomes.

**Configuration.** Defaults live with the method; domain-specific parameters (math macro map,
binder lexicon, alias head words, extraction patterns) live in the domain pack's
`methods.yaml`, keyed by method name. Source profiles are not domain parameters: they live in
`sources/<profile>.yaml` and a configuration names one (M01). The effective configuration is the
merge, with a named profile and a named method configuration it embeds (M03's `segment.sentences/<name>`
inside `ingest.html`'s) resolved to their content, hashed as one canonical JSON document (`cfg:`
key, D1 §10).

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
| M02 | `profile.segments` | profile | rendition | measurements (character and math features; token counts from phase 1) | det. | 0 | base | S1 |
| M03 | `segment.sentences` | ingest | rendition (a step of M01's task) | `sentence` segments | det. | 0 | base | S1 |
| M04 | `embed.segments` | profile | segment, entity (aliases) | embeddings | encoder | 1 | base | S7 |
| M05 | `classify.segments` | extract | segment | `classification` | encoder | 1 | base | S2 |
| M06 | `extract.gliner_schema` | extract | segment | `mention`, `attribute`, `record` | encoder | 1 | base | S2 |
| M07 | `extract.gliner_joint` | extract | segment | `mention`, `relation` | encoder | 1 | base | S2 |
| M08 | `extract.patterns` | extract | sentence | `mention`, `relation` | det. | 1 | conditional | — |
| M09 | `extract.math` | extract | rendition (observations per math span) | `mention`, `relation` | det. | 0 | base | S0, S5 |
| M10 | `llm.propose_claims` | llm | unit packet | `claim_proposal` | local LLM | 1 | base | S3 |
| M11 | `normalize.formula` | normalize | rendition (observations per math span) | `value` | det. | 0 (grammar: validation, slot typing, canonical form); 1 (SymPy conversion) | base | S5 |
| M12 | `normalize.quantity` | normalize | span | `value` | det. | 1 | base | — |
| M13 | `resolve.symbol_scope` | resolve | rendition | `scope` | det. | 0 (packet standing context) | base | S0, S5 |
| M14 | `resolve.concept_link` | resolve | observation (mention) | `link` | det. + encoder | 1 (vectors 2) | base | S7 |
| M15 | `resolve.record_link` | resolve | run | `link` | det. (Splink) | 2 | conditional | — |
| M16 | `llm.judge` | llm | alternative group, claim, identity group | `judgment` | local LLM | 1 | base | S3 |
| M17 | `consolidate.entities` | consolidate | run | entities | det. | 0 | base | S6 |
| M18 | `consolidate.claims` | consolidate | run | claims, links | det. | 0 | base | S6 |
| M19 | `validate.rules` | validate | run (inside the consolidation pass); batch at submission | `verification` | det. | 0 | base | S4 |
| M20 | `validate.conditions` | validate | claim, statement | `verification` | det. (z3) | 2 | conditional | S5 |
| M21 | `verify.statistics` | verify | claim | `verification` | det. | 4 | base | S5 |
| M22 | `classify.cues` | extract | sentence | `classification` | det. | 1 | base | — |
| M23 | `derive.claims` | consolidate | run | `claim_proposal` (derived) | det. | 2 | base | — |
| M24 | `agent.opus` | agent | unit packet; alternative group (phase 1) | `claim_proposal`; `judgment` (phase 1) | agent | 0 | base | S0 |

Not methods: metric computation (D6 §6), alignment and scoring (D7 §5), confidence estimation
(a consolidation step, D5 §6).

**Unit of work.** A task's unit is chosen so that the task, digest and transaction machinery is
small beside the work. M09 and M11 run once per rendition and write one observation set per math
span, so reuse holds at page grain, which is enough (a rendition's content digest changes only
when its content does). M19 is microseconds per claim, and consolidation rebuilds every pass
anyway, so per-claim caching would save nothing: at finalize it is one run-level step inside the
consolidation pass over the in-memory pool, bulk-writing its `verification` observations, and at
submission it runs inside `propose_claims` over the batch (M19 card). Separate tasks per claim
remain only for expensive checks (M20, M21). A run's task count for these methods falls from
tens of thousands (one per claim, one per math span) to one per rendition and one M19 step per
pass (P0CL-13; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28)

**Candidate, not in the catalog: spaCy candidates scored by GLiNER2.** spaCy proposes deterministic
candidate spans (gazetteer hits, identifiers, noun chunks) and GLiNER2 scores them under the
compiled schema with `score_explicit_spans`. Separating candidate generation from scoring shows
which component a recall gap belongs to. It is measured as a variant in S2 and enters the
catalogue as a conditional method only if S2 shows M06's recall gap is a span-proposal problem
(design rationale §4.8, P4).
> Status: **Proposed** (2026-10-28)

## 4. The shared LLM packet and prompt

M10, M16 and M24 (and hosted configurations later) use one packet format and one compiled
output schema. The point is that the agent tier and the local tier see the same evidence in the
same shape, so their outputs are comparable and a prompt tuned on one transfers.

### 4.1 The packet

A packet is assembled by `methods.llm.packet` from the database; nothing in it is free text
written by the pipeline. It is a **pure function of recorded inputs**: the unit's rendition
content, M13's `scope` observations, the known entities of the run's recorded reference run (or
the bootstrap list below), the prompt parts and the method's configuration. Nothing read when the
packet is served enters it: not the order in which the session works the queue, not the live
promoted pointer, not proposals made earlier in this run. So the packet is fixed when its task is
created, where reuse is resolved: `input_digest` assembles it once (cached for the task), puts its
text hash in the digest and returns that hash as the `Digest`'s `packet_hash`, which the task
records, so the packet `read_unit` serves is the one the digest covered (§1). M24's method definition (`select`, `input_digest`,
configuration) and the assembler belong to the agent interface; standing context and known
entities are inputs it reads, not parts other components assemble (P0CL-05; operator,
2026-10-28).
> Status: **Proposed** (2026-10-28)

```text
# Unit <unit_key>  ·  <document title> › <section path>  ·  the source marks it: <statement kind>
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

- **Size caps** are part of each method's configuration, one authority in one stated unit: the
  agent tier's (M24, `packet_cap_chars`) in characters, the LLM tiers' (`packet_cap_tokens`,
  default 3,000) in tokens of the served model; the values live in
  [D2 §12.1](D2-schema-and-guidelines.md#121-methodsyaml). Phase 0 has only the character cap: its
  one packet method is M24, and token-counted caps arrive with M10 and M16 in phase 1. The assembler
  applies the cap; the MCP tool only paginates the parts the assembler produced (D8 §3). A unit larger than the cap is split
  at sentence boundaries into numbered parts that share the standing context; the split is
  recorded in the task. The **output** budget is sized from
  batch size, not unit size: a batch runs two to nineteen times its unit's tokens (S0 core units:
  units at most 345 tokens, batches up to about 2,500; record s0.sizes, Measured).
- **Counting tokens (phase 1).** Agent packets (M24, golden passes) have no served tokenizer and are capped in
  characters, by the assembler under the method's configuration; phase 0 counts no tokens and does
  not install `tokenizers`. From phase 1, LLM-tier caps are counted with the served model's own `tokenizer.json` (tokenizers
  0.23.3), loaded from the vLLM model snapshot or by `Tokenizer.from_pretrained(repo,
  revision=<sha>)`; the revision and the file's sha256 are recorded in the packet's and M02's
  configuration, because counts depend on them. Counting is `encode_batch_fast(texts,
  add_special_tokens=False)` and the length of each id list (`encode_batch` only where offsets are
  needed; `TOKENIZERS_PARALLELISM=false` in forked workers). Counts are **not additive**: byte-level
  merges change where texts are joined, so M02's per-sentence counts serve only to plan the
  sentence-boundary split, and the assembler counts the assembled packet text once and records that
  count in the task. Characters ÷ 4 is not used as an estimate. The caps cover packet text and
  context only; the chat template is not in `tokenizer.json` (it lives in `tokenizer_config.json`
  and `chat_template.jinja`), so a whole-prompt budget would render the template or ask the server.
  > Status: **Measured** with the Qwen3.5-9B `tokenizer.json` at revision `c2022362…` (2026-10-28, [text-math note L-11](../design_review/evidence/2026-10-28_library-text-math/README.md)): `encode` adds 0 special tokens; on 433 paragraphs (20,095 tokens) `encode_batch_fast` gives ids identical to `encode_batch` in 2.2 ms against 3.9 ms; in 5 of 83 multi-sentence blocks the sentence counts sum to a different total than the joined text (worst 2.0%); 3.27 characters per token, so characters ÷ 4 underestimates. A vLLM `/tokenize` cross-check is not verified
- **Standing context** is at most six sentences, chosen by M13: for each symbol the unit uses,
  the sentence holding the binding site M13 assigns it when that sentence lies outside the unit,
  plus the site a "Suppose again" reopens. A sentence identical to one of the unit's is left out,
  and when more than six remain, the six latest in page order are kept; they are listed in page
  order. Each carries an id (`c1`, …) that evidence may cite (D2 §7.3). A self-contained unit has none;
  without M13 output the packet has none. The standing-context function works per rendition over
  its annotation units ([D1 §3.4](D1-knowledge-representation.md#34-locators): a `unit`, or a
  paragraph outside units); a block outside every annotation unit (a top-level list, table or
  figure) is returned as `uncovered`, and M13 reports such blocks the same way, so coverage can
  name what no packet holds (D6 §1). A positional rule ("the previous binding sentences in the
  section") is not used: it handed one exercise another exercise's setup and missed a premise stated
  before the unit.
  > Status: **Tested** (S0-R2, 2026-10-28; records s0r2.inputs, s0r2.scores; `code/s0r2_sample.py`)
  > Status: the six-latest cut and `uncovered` blocks are **Proposed** (2026-10-28); phase 0 M13
  > omits the paragraph rule, and its acceptance is the S0-R2 standing contexts (M13)
- **Known entities** are the canonical labels of the global entities of the run's recorded
  reference run (`ops.run.reference_run_id`, [D3 §4](D3-database.md#4-ops-methods-policies-runs-and-tasks)),
  and only there, that are linked to the page: those with a claim whose evidence lies on the page,
  taken by entity key (in key order, at most 30, so the cut is deterministic); proposals made
  earlier in this run never enter, because they depend on queue order. At bootstrap, when the reference run is null,
  the section lists a deterministic page-level list from the author markup M01 records: the page
  title and the `dfn` terms, as terms without a class. Proposals reuse the labels, so identity
  across units holds by label (D5 §3.3). Golden packets omit them (D7 §3.2).
  > Status: **Proposed** (2026-10-28, P0CL-05). Until the first promotion, cross-unit label
  > consistency rests on Opus and label normalization (D5 §3.3 point 5); the identity reading
  > shown at promotion makes that visible (D7 §7, §9)
- **Hints** are encoder observations above a threshold. They are off by default for proposal
  tasks (to keep LLM output independent evidence for confidence, D5 §6) and on for judge tasks.

### 4.2 The prompt

| Part | Source | Changes when |
|---|---|---|
| System instructions | `methods/llm/prompts/<task>.md` | Method version |
| Guideline core rules | Guideline §10 sections tagged `core` (D2 §10) | Guideline version |
| Schema inventory | The generated annotator reference (D2 §10.10): per predicate its subject and object, statement role, modality and condition rule, with value and node shapes; whole for every tier: filtering by statement kind leaves at least 6,347 tokens of the 12,851 (6,339 without worked examples), so it is not adopted, and the local tier's budget is decided with S3 (D2 §7.5; S4, 2026-10-28, record `s4.sizes`, Measured) | Schema version |
| Examples | k (default 2) adjudicated **dev-split** golden units nearest to the unit by M04 embedding, excluding every unit of the unit's own page, so no candidate is scored on a golden it was shown (its own unit, or a page whose units share running examples); rendered as packet + expected batch. Test pages are never in an example set, as in every training, fitting and prompt-optimization set (D7 §4; P0CL-16; operator, 2026-10-28). Golden passes instead get the reference's fixed worked examples, from pages outside every split | Golden set version. In phase 0, before M04 and dev goldens exist, prompts carry the annotator reference's fixed worked examples (`examples: reference`) |
| Packet | §4.1 | Unit |
| Output instruction | "Return one ClaimProposalBatch" plus the JSON Schema for tiers that do not enforce it | Schema version |

The agent tools serve these parts **by part**: `read_instructions` and `read_golden_unit` return
one part per call, each paginated at 24,000 characters, so no single response approaches Claude
Code's result limits (D8 §2.1, §2.2, §3).
> Status: **Proposed** (2026-10-28)

### 4.3 Output form and post-processing

Models cite evidence **by quote, not offset**: each evidence item is `{sentence: "s2", quote:
"…", role}`, and anchors of statements likewise. The authored model-facing batch, with its
**citation frame** (each `sN`/`cN` → the cited sentence's locator,
[D1 §3.4](D1-knowledge-representation.md#34-locators), and text; D1 §10.3), is the authority for agent
proposals as for golden passes and fixtures; the stored (offset) form is derived from it per
rendition by the cascade below, so a proposal reused on a rendition with an edit elsewhere on the
page cites that rendition's spans (P0CL-03; operator, 2026-10-28).

Post-processing has **two owners**. `validate`
([D9 §1](D9-repository-and-phase0.md#1-layout)) owns the batch→candidate adapter, which turns a
model-facing batch into the core keyed-candidate claims, and every check a batch must pass: steps
1, 3 and 4 below, and the D1 §11 invariants a batch can violate (D5 §8.3). One implementation
serves submission (M24's `propose_claims`, golden passes' `write_golden`), M10's post-processing
from phase 1, and the fixtures. `methods.llm.parse` is the quote cascade only (step 2): it is
schema-free, reading a citation frame and a rendition and returning spans, so it serves submission,
the per-rendition derivation of the stored form on reuse, and evaluation's derivation of golden
items (D7 §3.1) alike. The steps, in this order:
> Status: **Proposed** (2026-10-28)

1. **Validate** (`validate`) against the compiled models of the batch (vLLM enforces the JSON
   Schema during decoding; agent output is validated on submission, D8 §2.1).
2. **Locate quotes** (`methods.llm.parse`) by a cascade that never loses source offsets: exact in
   the cited sentence, then in the frame's other sentences (the unit's sentences and its standing
   context); exact up to spacing (a `regex` pattern of the quote's non-space characters
   joined by optional whitespace and spacing commands, matched in the original text, so no
   offset map is needed); the same after expanding the rendition's macros on both sides; then
   two fuzzy steps:
   - **Token sequence first.** The quote and the cited sentence are split into TeX/word tokens
     (control word, control symbol, word, other non-space character) and each distinct token is
     mapped to one private-use character, so whitespace never enters the comparison.
     `rapidfuzz.fuzz.partial_ratio_alignment` picks the window (cutoff 80 in the measured run),
     widened by three tokens, and `rapidfuzz.distance.Levenshtein.opcodes` aligns the quote inside
     it; the span runs from the window token aligned to the quote's first token to the one aligned
     to its last. The alignment alone returns a window of the needle's own length, one token short
     on a dropped-word quote; the opcodes step recovers it.
   - **Character level** when the token step finds nothing or scores below its cutoff:
     `partial_ratio_alignment` (cutoff 85, trailing punctuation stripped), refined inside its
     window by `regex` `BESTMATCH` with a bounded error count. `partial_ratio_alignment` is optimal
     only when the shorter input has at most 64 elements; beyond that its alignment is not
     necessarily the best one. No S0 quote exceeds 64 tokens, while many exceed 64 characters
     (status below), so the token step comes first.
   - When the cited sentence fails, the best sentence of the frame (the unit's sentences and its
     standing context) is chosen by `process.extractOne(quote, frame_sentences,
     scorer=fuzz.partial_ratio, score_cutoff=…)`; `process.cdist(..., workers=-1)` serves only bulk
     re-anchoring between renditions.

   Every regex step runs with a `timeout`, and a `TimeoutError` is a recorded step outcome. Every
   span is snapped outward to word boundaries; each result records its step and edit counts (for
   `BESTMATCH`, `fuzzy_counts`: `BESTMATCH` and `ENHANCEMATCH` select a match, they do not bound
   its errors). Several equal matches (a repeated phrase) are recorded as ambiguity, and a
   typo-level score is never identity. The result is a span (rendition offsets). An unlocated
   quote keeps the item in the batch with a coarse span over the cited sentence (`coarse: true` in
   the stored form, D2 §7.3), which consolidation records as `evidence_coarse` ([D5 §5.6](D5-consolidation-identity-confidence.md#56-evidence)).

   **On reuse.** A reused proposal is located on the run's own rendition from its frame. When a
   frame sentence's locator no longer resolves there, the sentence is re-located by the text the
   frame recorded for it, by the same cascade over the rendition's sentences; failing that, its
   items take D5 §5.6's fallback.
   > Status: the frame-wide fallback and re-location on reuse are **Proposed** (2026-10-28)
   > Decision: [ADR-0012](../adr/0012-math-grammar-token-keys.md)
   > Status: **Tested** in the spike instruments (2026-10-28): 733 of 735 S0 quotes exact, 2 after spacing, none fuzzy ([s0.stored](../design_review/evidence/2026-10-28_design-spikes/records/s0.stored.json))
   > Status: token-sequence step **Measured on synthetic perturbations only** (2026-10-28, [text-math note L-10](../design_review/evidence/2026-10-28_library-text-math/README.md)): on 527 seeded perturbations of 163 S0 quotes, after the same exact, spacing and macro steps, it finds 523 (spike cascade 504), 428 exact (392), 514 at IoU ≥ 0.9 (488), at most 9 ms per quote (214); dropped-word quotes 98 of 99 exact (spike 43); typos 111 of 132 exact (spike 130; 4 not found at cutoff 80, the cases the character-level fallback is for). 58 of the 163 quotes exceed 64 characters, none 64 tokens. The combined order (token step, then character fallback) is **Proposed**; real S0 quotes never reached a fuzzy step, so S3's local-LLM quotes are the real test
3. **Check references and types** (`validate`): local refs resolve; subject and object types match
   the predicate's domain and range (entity-type side table, D2 §7.3); the batch conformance checks
   follow, the D1 §11 invariants a batch can violate (INV-06 is rejected at submission, D5 §8.3).
4. **Normalize math** (`validate`'s adapter): `$…$` and `\(…\)` are equivalent; values of type
   `formula` keep the LaTeX as given and are parsed by M11 in consolidation.
5. **Keep rejects** (`validate`). Items failing 3 or 4 are kept in the observation payload under `rejected`
   with reasons; they count in metrics (malformed-output rate) but are not consolidated.

A judge output is `{target, decision ∈ {accept, reject, choose, merge, split, unsure}, chosen?,
rationale (≤ 2 sentences), confidence ∈ {low, medium, high}}`.

## 5. Ingest and profiling

### M01 ingest.html

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| document | original bytes; adapter config | `kb.rendition` (deduplicated by content), `kb.rendition_build`, `kb.segment` (structural kinds), `author_markup` observations | deterministic · 0 · base |

**Behaviour.** Parse HTML; drop excluded content by declared rules; record the page's
macro definitions (Siegrist's `div.latex` block) as the rendition's macro table; walk the body in reading
order emitting canonical text by D1 §3.1 and a segment for each block element and each math
delimiter pair; attach author markup to segment `attrs` and emit it as `author_markup`
observations (`dfn` terms with offsets, unit ids and classes, `details`, links with targets, and
the claims the profile's `details_kinds.synthesize` declares for a block).
Tables become `table`/`table_row`/`table_cell` segments with cell text in canonical text.
Rendered-only text (reference markers, quotation marks, sub-list markers, `details` summaries)
and orphan text follow D1 §3.1 and §3.2.

**Content-addressed output.** M01 runs on every document it is given (milliseconds per page) and
then deduplicates by content: the rendition is identified by its content digest
([D1 §3.1](D1-knowledge-representation.md#31-document-rendition-and-canonical-text),
[§10.1](D1-knowledge-representation.md#101-hashing)), and a result whose digest already exists
writes only a `kb.rendition_build` row (the configuration, the task, the parser diagnostics in
`parse_detail`) for the existing rendition. A content-preserving change (a port, a spaCy bump,
a profile fix that changes nothing) therefore keeps every row and key (P0CL-01; operator,
2026-10-28). The macro table is content, not build provenance: formula keys read through it
(D1 §6.2), so two builds that record different tables are different renditions (D1 §3.2).
> Decision: [ADR-0019](../adr/0019-identity-follows-content.md)
> Status: **Proposed** (2026-10-28)

**Page macros.** The rendition's macro table is the page's own macro definitions; the domain
pack's macro map supplies only names the page does not define. Consumers that expand or read
macros (the math grammar, M09, M11, quote location) take the rendition's table, because the same name has different bodies on different pages: `\mse` is
`\text{mse}` on some and `\text{MSE}` on others, `\kur` is `\text{kurt}` or `\text{kur}`.
The definitions are read with the shared TeX tokenizer, the one the token form uses (D1 §6.2):
`\newcommand`, `\renewcommand` and `\providecommand`, each with an optional `*`, then the name, an
optional `[n]`, an optional default and the body, read as TeX reads arguments;
`\DeclareMathOperator` is read as an operator when a source uses it. pylatexenc has no production
use: this reader replaces its walk, and M01 runs no span balance check, because segment status
comes from delimiting alone (D1 §3.1) and readability is the value's `parse` status (M11). The
`docs/pins.md` hold on pylatexenc 3.0b2 can be released when the production M01 lands.
**Spike defect, not to be ported:** the S1 adapter's reader (`s1_adapter.macro_table`) accepts
`\newcommand` only, so it misses every `\renewcommand`; on Siegrist the 22 renditions with
`\renewcommand{\P}{\mathbb{P}}` fall back to the pack map for `\P`, whose body happens to agree.
On another source the fallback body would differ and keys would move.
> Status: per-page macros **Tested** on 78 Siegrist pages (S1, 2026-10-28): 29 distinct definitions recorded per rendition; the common names (`\N`, `\R`, `\E`, `\var`, `\P`, `\sd`) agree across pages, several others do not ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json)); the fallback to the pack map is **Proposed**
> Status: tokenizer reader **Measured** on the 78 `div.latex` blocks (2026-10-28, [text-math note L-04](../design_review/evidence/2026-10-28_library-text-math/README.md)): 630 `\newcommand` and 22 `\renewcommand` definitions, no `\def`, `\DeclareMathOperator` or `%`; it gives the pylatexenc walk's table on the other 56 pages and adds `\P` on the 22. pylatexenc's non-tolerant span parse made 0 of 28,956 spans `partial`, and all 8 partials come from delimiting. `\DeclareMathOperator` is **Proposed** (no occurrence)

**Configuration.** A *source profile* (one per source family; Siegrist's is drafted in
[D2 §12.1](D2-schema-and-guidelines.md#121-methodsyaml) as `sources/siegrist.yaml`) is a set of
CSS selectors, each with a role payload: exclusion rules (scripts, the macro block, navigation including Siegrist's
`ul.map` chapter lists, controls, images), the title, section headings (`h3` and `h4` open
nested sections), the unit selector (`div.unit`), statement-kind hints from block classes
(`p.dfn` → definition, `p.math` and `p.stat` → theorem, `p.Proof` → proof, `p.app` → not
claim-bearing) and from section titles ("Computational Exercises" → exercise), `details` kinds
(proof or solution), math delimiters and display environments (`align`, `align*`), the macro
source (`div.latex`), and the rendering conventions of D1 §3.1. The profile is about the source's
HTML, not the domain, so it lives in its own file, `sources/<profile>.yaml`
([D2 §2](D2-schema-and-guidelines.md#2-domain-pack-layout)), and the pack's `methods.yaml` names it
(`ingest.html` configuration `source_profile: siegrist`). A second domain over the same source
reuses the profile, and a second source adds a file without editing a domain pack. Only the
resolved profile enters `ingest.html`'s configuration hash, so adding a profile changes no other
source's builds (P0CL-07; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28)

cssselect2's `Matcher` is
the one role engine: each profile selector is added once with its role payload, and one pass over
`ElementWrapper.from_html_root(root).iter_subtree()` returns, for each element, every matching
payload with its specificity and order, so precedence by specificity and the `role_conflicts`
check (an element claimed by two roles) need no further code. The cssselect→XPath translation
(`etree.XPath(CSSSelector(css, translator="html").path)`) is only an export for tools that take
XPath (trafilatura's `prune_xpath` accepted it unchanged); production does not run both engines,
and the identity of the two stays a profile test. Selectors compile when the profile loads, and
one that does not compile (`cssselect2.SelectorError`; for the export, cssselect's
`SelectorSyntaxError` or `ExpressionError`) rejects the profile. The profile uses cssselect 1.6
syntax (`div.unit:has(> p.app)`); cssselect's custom translator subclasses are not used, their API
being unstable.
> Status: **Tested** on 78 Siegrist pages (S1, 2026-10-28): both engines select identical node sets for every rule on every page, with no role conflicts and no unclassified block ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json))
> Status: **Measured** on html5lib trees of the 78 pages (2026-10-28, [text-math note L-02](../design_review/evidence/2026-10-28_library-text-math/README.md)): identical payload sets on every page for the 19 rules; the `Matcher` takes 65 ms in total against 22 ms for precompiled XPath, so speed does not decide

A second source needs more of the profile than Siegrist does: a `layout` role (tables used for
layout), section rules with a heading source (NIST's subsections are layout-table rows), a
`verbatim` role (`pre` keeps its line breaks), per-selector list markers, and per-selector
rendering of reference links and `img[alt]`. Generic defaults: `pre` keeps whitespace, an
`img` with `alt` text is never silently dropped, and a list without items is a block.

**Profile vocabulary.** Every key a source profile may set, with the default when it is absent;
the adapter reads no source fact from anywhere else (ADR-0012):

| Key | Value | Default |
|---|---|---|
| `applies_to` | glob of source paths | required |
| `encoding` | `sniff`: WHATWG sniffing on the original bytes (BOM, then the 1,024-byte meta prescan, then the windows-1252 fallback; no chardet guessing); or an explicit encoding label, passed to html5lib as `override_encoding`. The detected encoding is recorded per build (`kb.rendition_build.parse_detail`) | `sniff` |
| `exclude` | named CSS selectors; excluded text recorded per rule | scripts and `noscript` only |
| `title` | selector | the first `h1` |
| `sections` | heading selectors, outermost first, each opening a nested section | `h1`…`h6` |
| `section_source` | where headings come from: `body` headings, or a `layout` row selector | `body` |
| `unit` | selector of numbered units | none: paragraphs only |
| `block_hints`, `section_hints` | selector or section title → statement-kind hint, `claim_bearing` | none |
| `details_kinds` | statement kind of `details` blocks, by context and summary text; under `synthesize:`, per kind, the claim the containment states, `{predicate, object, evidence}` (Siegrist: a `proof` or `solution` block `core:proves` its enclosing unit's statement, evidence the summary). M01 records the declared claim on the block's `author_markup` observation, and consolidation turns it into a claim without knowing the convention (D5 §3.5; P0CL-07) | `proof`; nothing synthesized |
| `math` | `inline` and `display` delimiters, `display_environments`, `page_macros` (the macro source selector) | `\(…\)`, `\[…\]`, no environments, no page macros |
| `references` | selector of in-text reference links, and their rendering (`browser` "[n]", `placeholder`, `empty`) | links rendered as their text |
| `render` | rendering conventions for script- or style-produced text: `q` (`quotes`, `bare`), `list_markers` per list selector (`parenthesized`, `browser`, `none`), `summary` (`heading`, `drop`), `figure` (`caption`, `drop`) | `bare`, `none`, `heading`, `caption` |
| `layout` | selectors of tables used for layout (read as blocks, not tables) | none |
| `verbatim` | selectors whose whitespace is kept (`pre`) | `pre` |
| `img_alt` | whether `img[alt]` text is rendered as text | `true` |
| `orphan_text` | how text outside any block is kept | a `paragraph` with `orphan: true` |
> Status: **Proposed** (2026-10-28): the keys Siegrist uses are Tested on 78 pages (S1); `section_source`, `layout`, `verbatim` and `img_alt` come from the NIST probe; `details_kinds.synthesize` moves an existing consolidation rule into the profile and is not yet exercised
> Status: **Proposed**, from the NIST probe on 8 pages (S1, 2026-10-28), where only the Siegrist `scripts` and `images` rules matched anything ([s1.nist](../design_review/evidence/2026-10-28_design-spikes/records/s1.nist.json))
> Status: `encoding` **Tested** (2026-10-28, [text-math note L-03](../design_review/evidence/2026-10-28_library-text-math/README.md)): sniffing detects `utf-8` on all 78 Siegrist pages, with text equal to a UTF-8 decode; an explicit label is **Proposed** (no source needs one yet)

**Parser.** html5lib through `lxml.html.html5parser`, whose HTML5 tree construction closes an
open `<p>` before a block element. libxml2 (`lxml.html.document_fromstring`) keeps a `<details>`
that follows an unclosed `<p>` inside the paragraph, with its summary and proof; it is
acceptable only with a repair rule that closes `<p>` before block elements.
> Status: **Tested** on 78 Siegrist pages (S1, 2026-10-28): the two parsers give canonical texts of equal length on every page and differ in segments on 4 pages, each at an unclosed `<p>` before `<details>`, where html5lib's tree is the correct one ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json)); the html5lib rerun gave the same counts, invariants and locators on all 78 pages, and content-identical renditions on the seven S0/S0-R2 pages, differing only in keys ([s1.corpus-html5lib](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus-html5lib.json), [s1.rendition-identity](../design_review/evidence/2026-10-28_design-spikes/records/s1.rendition-identity.json); RENDITION-01 closed)

**No profile-free fallback.** trafilatura does not produce M01's canonical text for a profiled
source: it drops headings next to units, every `details` summary, captions and short proofs
ending in an empty reference, and returns no units, `details` or sections as structure. It may
draft a provisional rendition (`profile: none`, `parse_status: partial`) to help write the
profile of a new source.
> Status: **Measured** on 78 Siegrist pages (S1, 2026-10-28): trafilatura 2.3.1 misses 5.3% of canonical content, 93% of `h2`–`h4` headings, all `details` summaries and 99% of captions; it keeps every math span it outputs verbatim ([s1.trafilatura](../design_review/evidence/2026-10-28_design-spikes/records/s1.trafilatura.json))

**Library realization.** Source-specific facts (unit, reference, section and layout selectors,
delimiters, the macro source, the encoding) are profile data, never adapter code.

- **Parse.** `parser = html5parser.HTMLParser(namespaceHTMLElements=False)`, then
  `html5parser.document_fromstring(raw_bytes, guess_charset=False, parser=parser)`, with a new
  parser for each document because the parser is stateful (never shared across threads). The
  original bytes go in, not a decoded string, so html5lib's WHATWG sniffing applies (profile
  `encoding`), and `guess_charset=False` keeps chardet out, so detection is deterministic. The flag
  gives element names without a namespace. html5lib's default, which lxml's module-level parser
  and `html5lib.parse(..., treebuilder="lxml")` keep, puts every element in the XHTML namespace,
  where the profile's XPath export matches nothing; so no tag-rewriting or namespace-cleanup pass
  follows the parse. Foreign content (inline SVG, MathML) keeps its namespace, and a profile that
  selects inside it writes `ns|tag`.
- **Parser diagnostics.** The build's `parse_detail` records `parser.documentEncoding`, `parser.errors` as
  position (line, column) and error code, and the number of `html5lib.constants.DataLossWarning`s
  caught around the parse (`warnings.catch_warnings(record=True)`). The tree builder coerces
  non-XML element and attribute names (`,` becomes `U0002C`), U+000C in text and `--` in comments;
  a coerced attribute name can silently defeat an attribute selector. html5lib supplies
  `sourceline` on about one element per page, so `attrs.sourceline` is present only where the
  parser supplies it (D1 §3.2). The walk skips comment nodes and keeps their tails, so no removal
  pass is needed.
- **Roles.** cssselect2's `Matcher` (Configuration above).
- **Math delimiting.** One `regex` pattern generated from the profile's declared delimiters and
  display environments, with `(?V1)` written explicitly (the module default is V0). Named lists
  (`\L<opens>`, `\L<closes>`, `\L<delims>`, `\L<envs>`) hold the declared values as literals, so
  nothing is escaped by hand; compilation rejects a missing or unused list, `named_lists` exposes
  the vocabulary to tests and to the rendition record, and of overlapping items (`$`, `$$`) the
  longer matches. An escaped backslash `\\` is skipped by `(*SKIP)(*F)`, and every declared
  delimiter that does not start with a backslash gets a generated `(*SKIP)(*F)` branch for its
  escaped form (`\$`). The body is possessive (`*+`) and stops at the next delimiter, so an
  unclosed span is `partial` and the scan resynchronizes; a stray closer is recorded. Each block
  is scanned by `finditer(text, timeout=…)` with a small bound, and a `TimeoutError` makes the
  block `partial` with reason `delimiter scan timeout` (D1 §3.1). The pattern checks no brace or
  environment balance and has no recursive groups: segment status comes from delimiting alone.
  Each delimited span is read by the math grammar (M11), whose result is the value's `parse`
  status, not the segment's. `regex` is the one pattern engine in the adapter, declared directly
  with an exact pin.
- **Text.** `unicodedata.normalize("NFC")` on the parser's text, with no `html.unescape`: the
  parser has already decoded character references, so a second decode would turn a literal
  `&amp;lt;` (text `&lt;`) into `<`.
  > Status: **Proposed** (2026-10-28)
- **Processes and caveats.** The html5lib parse is pure Python and holds the GIL, so documents are
  parallelized across processes, not threads. html5lib 1.1 (June 2020) installs from its wheel; its
  sdist does not build on Python 3.14. Its tree construction is not guaranteed to match current
  browsers on newer constructs, and it sets no resource limits.
> Decision: [ADR-0012](../adr/0012-math-grammar-token-keys.md)
> Status: **Tested** in the S1 adapter (2026-10-28): the generated pattern delimits identically to the scanner on 517 blocks ([s1.profile-delimiting](../design_review/evidence/2026-10-28_design-spikes/records/s1.profile-delimiting.json)); so does the named-list form (2026-10-28, [text-math note L-05](../design_review/evidence/2026-10-28_library-text-math/README.md)), where `$` and `$$` match the longer; the per-block timeout is **Proposed**
> Status: **Measured** on the 78 Siegrist pages (2026-10-28, [text-math note L-01](../design_review/evidence/2026-10-28_library-text-math/README.md)): with html5parser's default all 29,425 elements are namespaced and the XPath export matches 0 of 2,479 units; with `namespaceHTMLElements=False` none is and it matches 2,479; sniffing finds `utf-8` on every page; 17 parse errors (`unexpected-end-tag` 7, `expected-named-entity` 6, `unexpected-character-after-attribute-value` 3, `unexpected-start-tag-implies-end-tag` 1), 2 data-loss warnings (an attribute named `,`), 1 comment; median 4.2 ms per page (max 23.6 ms), about 20 times libxml2, negligible at this corpus size

**Measured by.** `parse_status` per rendition and segment; excluded-character share; segment
counts by kind; author-markup counts against the corpus index (`siegrist_sections.tsv`).
> Status: **Measured** on 78 Siegrist pages (S1, 2026-10-28): units, definition units, `dfn` terms, `details` and `\[` display math equal the index on 77 of 78 pages (on the exception the index counts a commented-out unit); `dfn` terms item by item, no difference ([s1.corpus](../design_review/evidence/2026-10-28_design-spikes/records/s1.corpus.json))

**Port.** The rules, not the code shape, of `corpus-intelligence` `html_adapter` (≈1,000 lines;
D9 §7). Spike: S1; its adapter (`s1_adapter.py`) is the tested reference, ported against this card
rather than copied: without its namespace-rewriting pass, its mixed `re`/`regex` use and its
`\newcommand`-only macro reader.

### M02 profile.segments

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| rendition | segments, `author_markup` | `ops.measurement` rows per segment | deterministic · 0 · base |

Computes the features policies route on: length in characters; inline and display math counts;
math character share; presence of `dfn`; the statement-kind hint from block class or section
title; nesting depth; whether the segment sits in a `details` block. **Phase 0 writes these
character and math features only**: no phase 0 consumer reads token counts, because the one
packet method, M24, is capped in characters (§4.1). From phase 1, with M10's token-counted caps,
M02 adds token counts, real counts with the served model's `tokenizer.json` (§4.1), never
characters ÷ 4, per segment and per sentence; the per-sentence counts serve to plan the
sentence-boundary split of an oversized unit, and the packet assembler still counts the assembled
packet once, because counts are not additive. Pure function of the rendition and, from phase 1,
of the tokenizer file whose revision and sha256 its configuration records. No observations: these
are measurements (D6 §6), because nothing consolidates them. Its `ops.measurement` rows carry the
writing task's `task_id` and are read through reuse, as observations are (`kb.run_observation`,
[D3 §8](D3-database.md#8-runs-snapshots-and-reads)): a run whose M02 task is `reused` reads the rows
of the task it points at.
> Status: phase 0 features and reading through reuse **Proposed** (2026-10-28)
> Status: token counting **Measured** (2026-10-28, [text-math note L-11](../design_review/evidence/2026-10-28_library-text-math/README.md)): 3.27 characters per token on Siegrist text; sentence counts summed differ from the joined count in 5 of 83 multi-sentence blocks (§4.1)

### M03 segment.sentences

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| rendition | canonical text, structural and math segments, reference markup | `sentence` segments | deterministic · 0 · base |

**Behaviour.** Splits every `paragraph`, `list_item`, `table_cell` and `caption` into sentence
segments; never splits inside math; never lets a sentence cross its parent block. **M03 is a step
of M01's task**, not a task of its own: `ingest.html`'s configuration names
`segment.sentences/<name>`, and the registry resolves that named configuration into
`ingest.html`'s configuration hash, so the build's adapter configuration (provenance) covers both.
Its sentence segments are part of the rendition's content, so sentence segments are as stable as
the other segments and a configuration change that leaves every sentence unchanged keeps the
rendition (M01, P0CL-01).
> Status: **Proposed** (2026-10-28)

**Library realization (variant b′; `OPEN-D1-1` closed by S1).** spaCy 3.8 `en_core_web_sm` with
the parser's sentence boundaries, on a `Doc` built from words and spaces. Using the math segments
and the reference markup, the prose between inline math spans and rendered reference markers
(`[n]`, D1 §3.1) is tokenized with `nlp.tokenizer`, and each inline math span and each marker
enters as one word: `Doc(nlp.vocab, words=..., spaces=...)` reproduces the block text exactly, so
alignment holds by construction, token offsets stay in canonical text, and no retokenizer and no
offset mapping are needed. Math tokens get `tag_ = "NNP"`; the tagger keeps preset tags and the
attribute ruler maps them to `PROPN`. The tag does not reach sentence boundaries (the parser's
features are `NORM`, `PREFIX`, `SUFFIX`, `SHAPE`, `SPACY`, `IS_SPACE`); it matters to pattern
matchers and lemmas. `is_sent_start = False` is set on reference markers and on every token of a
display formula after its first (located by `Doc.char_span(..., alignment_mode="expand")`, where
over-reach is harmless); the parser respects preset boundaries (`None` leaves a start to the
parser, `False` forbids one). Docs are processed by `nlp.pipe(docs, batch_size=64,
as_tuples=True)`, which carries block keys, with the model loaded with `exclude=["ner",
"lemmatizer"]`; `n_process` is not worth its start-up cost at this corpus size. Methods that need lemmas (M14's
lemma match, M22) build their own Doc with the lemmatizer, and their configuration hashes that
pipeline; M03's Doc is not shared across tasks. Consumers that map
a character span onto tokens use `Doc.char_span` with `strict` to test alignment and `contract` to
take the tokens inside a quote span; quote location itself stays character-based (§4.3). Math is
never presented to spaCy as text: on raw text the parser splits inside formulas, an opaque
placeholder loses real boundaries, and math rendered to Unicode adds false splits after list
markers and mid-clause.
> Status: **Tested** and **Measured** on the four spike pages, 412 blocks (2026-10-28, [text-math note L-08](../design_review/evidence/2026-10-28_library-text-math/README.md)): 3 of 847 inline math spans straddle tokenizer boundaries, where expanding the span and merging it with `retokenize` takes prose into the math token (`mean\( \pm \)standard`), so the token's text is no longer the span; the words-and-spaces Doc reproduces the text of all 412 blocks, with sentence starts identical to the merge route on all 412; the preset `NNP` maps to `PROPN` on 843 of 844 math tokens; `nlp.pipe` with `ner` and `lemmatizer` excluded takes 0.38 s against 1.13 s for a per-block loop over the pipeline, with identical sentences
> Status: **Measured** on a sentence gold of 85 blocks with 49 internal boundaries, marked identically by two independent markers (S1, 2026-10-28): boundary F1 1.00 for b′ against 0.80 for raw text, 20 of whose 24 false splits fall inside math, and 0.70 for an opaque mask; under b′ the rule-based sentencizer reaches 0.99 and the `trf` parser 0.98 ([s1.sentence-gold](../design_review/evidence/2026-10-28_design-spikes/records/s1.sentence-gold.json))

**Configuration.** The model, the variant and the exclusions; M03's named configuration includes
the spaCy version, the model package name and version, and the excluded components, and through
`ingest.html`'s configuration hash changing any of them makes a new build, and a new rendition only where a sentence boundary moves.
`en_core_web_sm` 3.8.0 is installed as a wheel by URL in
`[tool.uv.sources]` (its hash in `uv.lock`), never by `spacy download`; it requires spaCy
`>=3.8.0,<3.9.0`.

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

**Library realization.** `AutoExtractor.from_pretrained` (the 2.5 checkpoint; `GLiNER2.from_pretrained` loads the older span architecture); `Schema.from_dict` from the compiled
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
predicate it emits. Each inline formula is one token of M03's Doc, so patterns can match a
formula as one token.

### M09 extract.math

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| rendition: its `math_inline` and `math_display` segments | LaTeX source, the rendition's macro table | `mention` (label `symbol`), `relation` (`in_set`, `equals`, `compares`), per math span | deterministic · 0 · base |

**Behaviour.** One task per rendition (§3, unit of work); its digest is the rendition's content
digest, macro table included (M01), so a content-identical rendition reuses it.
For each math span it tokenizes LaTeX into a node tree and emits a `symbol` mention for each identifier
occurrence with its decoration (`X_1` keeps the subscript; `\sigma^2` records base `\sigma` and
power 2), and math-internal relations a scoping or binding step needs, under three labels:
`in_set` for membership (`a \in \R`), `equals` for equality (`Y = a + b X`) and `compares` for
comparisons (`x > 0`, `0 < p < 1`). Distribution statements written in notation (`X \sim
N(\mu, \sigma^2)`) are not mapped to a domain predicate in phase 0, because nothing consumes such a
relation before the encoder tier; a pack notation map decides that in phase 1. These observations, with M11's `value` observations, are M13's input for symbols and math
relations (M13), so the grammar parses each span once per rendition.
> Status: the three relation labels are **Proposed** (2026-10-28)

**Library realization.** The math grammar of M11: symbol occurrences with offsets, sub- and
superscripts as tree structure, relations and memberships as typed nodes; the page's macros
recorded by M01, then the pack's fallback macro map (D2 §12.1). No SymPy conversion here.
Occurrence offsets are the parse positions (`propagate_positions=True` gives `sub_symbol` and
`styled` nodes theirs), shifted into the span by the opener's length plus the leading whitespace;
they are never found by searching the span for the parsed text. M09's mentions depend on M11's
whole-name command terminals: under the spike grammar's prefix-matching `\left` terminal, `x
\leftarrow y` reads as the product `x·a·r·r·o·w·y` and would yield the symbols `a`, `r`, `o`, `w`
(M11, spike defect).
> Decision: [ADR-0012](../adr/0012-math-grammar-token-keys.md)
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
| unit packet (mode `extract`); judge packet (mode `adjudicate`, phase 1) | packet via MCP `read_unit`, prompt parts via `read_instructions` (D8) | `claim_proposal` or (phase 1) `judgment`, plus an `ops.intervention` row that references it | agent · 0 · base |

**Behaviour.** The pipeline never calls Opus. A task for M24 is created with status
`awaiting_agent`; the Claude Code session pulls it with `queue_next`, reads the packet, and
submits through `propose_claims` (`adjudicate` joins in phase 1); the submission is validated and
located exactly as §4.3, M19's submission-time rules run over the batch inside the same call, and a
clean or second submission completes the task through the orchestration's agent completion
primitive, in the tool's transaction (D6 §3.1). A first submission with errors leaves the task
`awaiting_agent` for one corrected resubmission and keeps its result (rejected items with
reasons) in `ops.task.error`, so the rejection is recorded even if no resubmission comes (D8 §2.1).
> Status: **Proposed** (2026-10-28)

M24's input digest is the hash of the assembled packet text with
the prompt-part hashes and the model id and revision (§1 rule 4), so a guideline, schema or
example change, or a change to anything the packet shows, requests new proposals, and an upstream
re-run with identical output does not (D6 §4). The method definition and the packet assembler
belong to the agent interface (§4.1). In phase 0 M24 is the only extractor; later it receives what
policies escalate. Golden authoring is not M24: it is a D7 protocol with its own tools and its
own tables.

## 8. Normalization and resolution

### M11 normalize.formula

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| rendition (one `value` observation per math span); also LaTeX strings inside claim proposals (called by consolidation) | LaTeX, the rendition's macro table | `value` (`formula`, `set`, `interval`) | deterministic · 0 (grammar: validation, slot typing, canonical form) · 1 (SymPy conversion) · base |

**Behaviour.** One task per rendition, digested as M09's (§3, unit of work). For each math span
it expands source macros, parses to SymPy, and returns a D1 §6 value with `latex`,
`sympy` (`srepr`), `parse` (`ok`, `partial`, `failed`) and the free symbols. Set expressions
(`\R \setminus \{0\}`, `(0, \infty)`) become SymPy sets. Symbol binding is not done here: it
needs scope (M13) and claims, so consolidation binds (D5 §4).

**Library realization.** One math grammar for every reader of math: SymPy 1.14's Lark LaTeX
grammar, unedited, extended by a separate file through Lark `%extend`/`%override` (typed start
symbols formula, relation, member, set; sub- and superscripts as rules; set constructs; operator
and set macros generated from the rendition's macro table, never named in the grammar). The
shipped grammar file is read directly rather than through SymPy's `LarkLaTeXParser`, whose options
differ (`lexer="auto"`, no positions, start `latex_string`). Construction: `Lark(...,
parser="earley", lexer="dynamic", ambiguity="explicit", propagate_positions=True,
maybe_placeholders=False, keep_all_tokens=True, ordered_sets=True)` with the typed start symbols;
Lark's `regex=True` is not needed.

- **Whole-name command terminals.** An `edit_terminals` callback, applied at build to every
  terminal, rewrites each control-word literal to end at `(?![A-Za-z])`. It also reaches the
  anonymous terminals Lark builds from the shipped grammar's string `%ignore` lines (`"\\left" |
  "\\right"` and others), which no `%override` can. The shipped file stays unedited. **Spike
  defect, not to be ported:** the spike grammar (`mathgrammar/build.py`, `whole_name_overrides()`)
  generates whole-name `%override` lines by a regex over the grammar text, which leaves those
  `%ignore` terminals prefix-matching: `x \leftarrow y` parses `ok` as the product `xarrowy`, `A
  \leftrightarrow B` prints `ArightarrowB`, `a \quadrant b` prints `arantb`, and `x \rightarrow 0`
  is `ambiguous` between the arrow and `\right` plus `arrow`.
- **Ambiguity.** Explicit, resolved only from declared context, otherwise `ambiguous`.
  `ordered_sets=True` is stated although it is the default: the resolver keeps the first of the
  readings with equal SymPy values, so the order of `_ambig` children reaches canonical printing
  and occurrences. `ambiguity="forest"` with `TreeForestTransformer` and `@handles_ambiguity` (or
  a custom prioritizer) is the escalation only if S5's full run shows `_ambig` blow-ups on long
  display formulas; it changes tree shaping and drops position propagation, so it is not a
  drop-in. `CollapseAmbiguities`, which enumerates exponentially, is not used.
- **Failures.** The category is derived deterministically from the exception class
  (`UnexpectedCharacters`, which the dynamic lexer mostly raises; `UnexpectedEOF`;
  `UnexpectedToken`), the TeX token at the error position (read with the shared tokenizer of D1
  §6.2) and the `allowed` terminal set. `UnexpectedInput.match_examples`, documented chiefly for
  LALR, is a last resort only. Transformer failures are unwrapped from `VisitError.orig_exc`.
  Lark has no deadline: a `signal.setitimer` timer gives category `timeout`, and because such a
  timer works only in a process's main thread, grammar work runs in single-threaded worker
  processes, and the grammar API raises when it is called off a process's main thread, so the rule
  is enforced, not only followed. **No grammar or SymPy runs in an MCP worker thread.** The main
  MCP server never imports the grammar: submission-time rules read formula symbols with
  `core/tex.py`'s TeX tokenizer, and rules that need the parse run at finalize (M19; P0CL-14). The
  golden server's pass-A/B diff and agreement (D7 §3.3) compare formula values, so it runs them in
  one spawned single-worker process, on whose main thread the grammar runs; its tool threads only
  hand that process the two passes and read the result.
  > Status: **Proposed** (2026-10-28)
- **Parser cache.** One parser per macro classification (which of the rendition's macros read as
  sets, operators or style wrappers, not the whole table), built lazily in a per-process dict.
  Earley parsers cannot be saved (`Lark.save` and `cache=True` are LALR only) or pickled, and
  construction is cheap, so there is no disk cache and no sharing across processes.
- **SymPy.** A subclass of SymPy's `TransformToSymPyExpr` (the documented customization point)
  holds the extension rules' methods; the base class's method names are internal to a backend
  SymPy marks experimental. The subclass guards products with a non-`Expr` operand (raising
  `NotRepresentable`) rather than relying on SymPy's deprecated path, and tests run with `-W
  error::sympy.utilities.exceptions.SymPyDeprecationWarning`, so a SymPy bump surfaces such cases.
  The ambiguity resolver converts every reading to merge equal ones, so this conversion runs during
  parsing, not only in M11's phase 1 conversion. SymPy is pinned as a hold; on a bump,
  `grammar/latex.lark` (its `%ignore` lines included) and `transformer.py` are diffed against the
  extension. `sympy.srepr` for storage. The ANTLR backend remains the comparison for `OPEN-D4-3`.
- **Canonical form.** Keys come from the token form (D1 §6.2), written by a TeX-rules `regex`
  tokenizer, never from the grammar's lexer or terminals. The grammar extension's added `%ignore`
  lines are generated from the token form's declared drop list, and building the grammar fails if
  any `%ignore` terminal of the assembled grammar is not on the list. The tree printer is checked
  against the token form by the property test of D1 §6.2.
> Decision: [ADR-0012](../adr/0012-math-grammar-token-keys.md)
> Status: **Measured** in the spike instruments (2026-10-28): 976 of 1,532 spans parse on a 78-page sample, the rest ambiguous or failed by recorded category ([s0.instruments](../design_review/evidence/2026-10-28_design-spikes/records/s0.instruments.json)); coverage is S5's question
> Status: **Tested** and **Measured** (2026-10-28, [text-math note L-06](../design_review/evidence/2026-10-28_library-text-math/README.md)): with the `edit_terminals` rule, `\leftarrow`, `\leftrightarrow` and `\quadrant` fail honestly as unknown commands, `x \rightarrow 0` parses `ok` with the right tree, and none of the 918 spike-page spans changes status or printed form (checked on 7 cases and those 918 spans, not yet on the 28,956 corpus spans; S5's full run includes it); `\left( a \right)` stays `ambiguous`, a grammar ambiguity for S5. `Lark.save()` raises `NotImplementedError` for Earley and pickling fails; a parser builds in 0.05 s, with 38 distinct parser keys over 78 pages; `ordered_sets=True` gives 1 distinct tree over 3 rebuilds of an ambiguous value; spike-page spans emit `SymPyDeprecationWarning` (non-`Expr` arguments in `Mul`); median 41 ms, max 826 ms per span on the 1,532-span sample

**Measured by.** Parse rate by math kind and page; failure categories (S5); the property test of
D1 §6.2, both layers.

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
| rendition | segment tree, sentences; M09's observations (`symbol` mentions, `in_set`/`equals`/`compares` relations); M11's `value` observations (`math_kind`, which the bound-symbol rule needs) | `scope` | deterministic · 0 (packet standing context) · 1 (scope source for consolidation) · base |

**Behaviour.** M13 reads the math through M09's and M11's observations, never through a second
grammar parse, so its digest covers their payload hashes (§1 rule 4) and a re-run of either with
identical output leaves M13 reused. It finds binding sites and assigns every symbol mention to one:

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

**Library realization.** Plain Python over the segment tree; binding sites by spaCy patterns
over M03's tokens, compiled at start-up from the binder lexicon in `methods.yaml`, not by regex
over raw text, because a binding site depends on the sentence start, the math token and its kind,
and clause attachment:

- `Matcher(nlp.vocab, validate=True)` for single-word binders: sentence-initial binders including
  "if" (`[{"IS_SENT_START": True, "LOWER": {"IN": sentence_initial}}]`), and clause binders
  followed by a math token (`[{"LOWER": {"IN": clause}}, {"_": {"is_math": True}}]`);
- `PhraseMatcher(nlp.vocab, attr="LOWER")` for multi-word section-wide phrases, with patterns
  from `nlp.make_doc(phrase)`, so a phrase splits as the tokenizer splits rather than on
  whitespace;
- "again" reopens only within the binder's sentence: `[{"IS_SENT_START": True, "LOWER": {"IN":
  sentence_initial}}, {"OP": "{0,3}"}, {"LOWER": {"IN": reopen}}]`;
- each math token (one per inline formula, M03) carries its kind (symbol, relation, membership;
  the `math_kind` of M11's `value` observation for that span) and its symbol occurrences (M09's
  observations for that span) as a token extension, registered once per
  process (guarded by `has_extension`); the values live in `Doc.user_data` and are read in the
  same process, so no `DocBin` is involved;
- `DependencyMatcher` only where clause attachment decides the binding (for example `where`, the
  clause head and a math dependent), behind the token patterns, because it inherits parser errors.

**No paragraph rule in phase 0.** The spike probe added a paragraph rule (a standalone
claim-bearing paragraph is a statement extent, a section-wide binder taking precedence), but
applied it only to the sample's own parts, so its 20 of 20 does not carry over to whole pages.
Phase 0 M13 omits it. Its acceptance is the S0-R2 standing contexts, 21 of 21, with the annotated
scopes reported rather than required (18 of 20 without the rule); the paragraph extent is decided
in phase 1, with S5-B's symbols-and-scoping figures (`OPEN-D4-5`, reopened, §12). Spike evidence:
S0 annotators' scopes (`m13_probe.*.tsv`), S5. The spike's `m13_binders.py` builds phrase patterns
by `phrase.split()` and accepts "again" anywhere in a sentence; the port follows the patterns
above, not those two.
> Decision: [ADR-0012](../adr/0012-math-grammar-token-keys.md)
> Status: **Measured** on the S0 reference (2026-10-28): 20 of 20 annotated symbol scopes reproduced with the paragraph rule, applied to the sample's own parts only; 18 of 20 without it ([s0.m13-probe-2](../design_review/evidence/2026-10-28_design-spikes/records/s0.m13-probe-2.json))
> Status: phase 0 without the paragraph rule, its acceptance, and reading M09's observations are **Proposed** (2026-10-28)
> Status: the `PhraseMatcher` phrases, the sentence-bound "again", the extension guard and the `DependencyMatcher` placement are **Proposed** (2026-10-28, [text-math note L-09](../design_review/evidence/2026-10-28_library-text-math/README.md)); not yet exercised

### M14 resolve.concept_link

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| observation: a `mention` of a **global** class | mention text, alias table of entities in the reference run, embeddings | `link` (top k candidates or a new-entity proposal) | deterministic + encoder · 1 (vectors in 2) · base |

**Behaviour.** Candidate generation in order: normalized-alias exact match; lemma match after
removing the class's head words ("distribution", "family") and mapping adverbial forms
("normally distributed" → "normal"); `rapidfuzz.process.extract` with `token_sort_ratio` (not `token_set_ratio`, which scores "normal distribution" and "standard normal distribution" as identical) over
aliases of the same class; from phase 2, pgvector nearest neighbours on alias embeddings. Each
candidate gets features (exact, lemma, fuzzy score, cosine, page co-occurrence); the score is a
logistic model fitted on golden links once there are enough (before: a fixed rule ordering).
Below the new-entity threshold the payload proposes `{"new": {type, label}}`.

**Configuration.** Head words and adverb rules per class in `methods.yaml`; k; thresholds.

**Reference run.** Linking is against the entities of the run's recorded reference run
(`ops.run.reference_run_id`, set when the run is created and immutable), never the live promoted
pointer and never this run's own proposals, so M14's output does not depend on task order
(P0CL-05; operator, 2026-10-28). A family introduced on its own page still links from other pages
within one run: mentions that each propose `{"new": …}` with the same identity meet in
consolidation, which keys them alike (D5 §3.3).
> Status: **Proposed** (2026-10-28)

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
changes a claim. Consolidation's finalization reads them (D5 §8). M19 runs inside the
consolidation pass; M20 and M21, which are expensive, run as separate tasks per claim between
assemble and finalize (§3, unit of work).

### M19 validate.rules

| Unit | Reads | Writes | Tier · phase · entry |
|---|---|---|---|
| run: the candidate claims of a consolidation pass; at submission, a batch's items | claim view, rule context (D5 §8.2), compiled rules | `verification` with `verifier: rule:<id>` for failing outcomes only, and per-rule counts on the task (at finalize); per-item warnings and errors in the submission result (at submission) | deterministic · 0 · base |

**Call sites.** At finalize, M19 is one run-level step inside the consolidation pass: the view
builder reads the in-memory pool once, every rule runs over every claim view, and the
`verification` observations are bulk-written, recorded as one M19 task of unit `run` per pass,
never reused (§1 rule 4). At submission it runs inside the submitting call (`propose_claims` for
M24, `write_golden` for golden passes; M10's post-processing from phase 1) over the batch's own
items (D5 §8.2; P0CL-13). Submission-time
views read formula symbols with `core/tex.py`'s TeX tokenizer
([D1 §6.2](D1-knowledge-representation.md#62-canonical-form)), which is total and fast; a rule that depends on the grammar's parse declares `at: [finalize]`, so
no grammar parse runs in an MCP worker thread (M11; P0CL-14; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28)

**Library realization.** rule-engine 5.1 `Rule` objects compiled once per schema version under a
typed `Context` (type resolver from the schema, registered functions for parameterized lookups;
pool facts such as `family_params` are cached view attributes, declared by the pack's `views:`,
D5 §8.2); evaluated per claim view.

**What it records.** Only failing outcomes become observations: a `verification` with state
`refuted` and detail `{rule, severity, message}`. A rule whose `when` is false, or that passes,
records nothing per claim; instead the M19 task records, per rule, the count of claim views it
evaluated (its `when` true), which is what verification coverage needs (D5 §8.1). At a few rules
per claim over a run's claims, recording every pass would multiply rows without telling
consolidation anything the counts do not.
> Status: **Proposed** (2026-10-28)

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
`kb.run_observation`), judgments, and the run's recorded reference run (`ops.run.reference_run_id`,
never the live promoted pointer). Steps, specified in D5:
entity resolution (D5 §3), symbol binding (D5 §4), claim assembly and keying (D5 §5),
confidence (D5 §6), applying judgments (D5 §7), validation status with M19 run inside the
finalize pass (D5 §8), derived claims (D5 §9). Phase 0 realization (D5 §11): identity by key,
canonical-form fusion only, status from agent proposals and M19 rules.

## 12. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D4-1 | Which local model: Qwen3.5-9B at full precision, or a larger quantized model that fits 32 GB with an embedding model beside it | Spike S3 |
| OPEN-D4-2 | Reasoning on or off for structured proposals on the local model (quality versus latency) | Spike S3 |
| OPEN-D4-3 | SymPy LaTeX backend (lark or ANTLR) and the macro map that maximizes parse rate | Spike S5 |
| OPEN-D4-4 | Unit of LLM work: whole `unit`, paragraph, or sentence group; set by S0 output sizes and S3 quality per packet size | Spikes S0, S3; **answered by S0 and S0-R2** for golden and agent packets (2026-10-28): the unit, with query-assembled standing context (§4.1); output budget from batch size; S3 measures local-LLM quality per packet size |
| OPEN-D4-5 | Whether M13's rule-based scoping reaches the S0 annotators' scopes, or symbol scope must come from the LLM proposal; and what extent a binding in a standalone claim-bearing paragraph takes | Spike S5-B, then phase 1; **reopened** (2026-10-28): S0's 20 of 20 rested on a paragraph rule the probe applied only to the sample's own parts. Phase 0 M13 omits that rule (sentence-initial "if" stays) and is accepted on the S0-R2 standing contexts, 21 of 21, with scopes reported (18 of 20); S5-B's symbols-and-scoping figures and phase 1 decide the paragraph extent (M13) |
