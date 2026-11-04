# S3 · Local LLM: plan

**Status: Proposed (2026-10-28).** Part of the [spike plan series](../design-spikes-s0-s1_2026-10-28.md),
which owns shared decisions (§3.5), the execution queue (row 31, with G1 at row 33) and spike-execution
findings. The question is the [S3 brief](../../design_review/evidence/2026-10-28_design-spikes/S3-local-llm.md)'s;
this document says what S3 must establish now, how each brief step now runs after S0-R2 and the
library research, and which phase 1 item and OPEN item each result feeds.

## 1. What S3 must establish now

S0-R2 froze the inputs S3 uses (annotator inputs v1, record `s0r2.inputs`) and measured the hosted
points it is compared with: Sonnet pass SV at full tier 0.77 and Haiku pass HV at 0.68 against the v1
reference, on the same packets. D2 §7.3 now states the decoding-form rules from the
[schema-rules note](../../design_review/evidence/2026-10-28_library-schema-rules/README.md), D4 §4.1
counts tokens with the served tokenizer ([text-math note](../../design_review/evidence/2026-10-28_library-text-math/README.md)
L-11) and sizes the output budget from batches, and D8 §3 waits on S3's p99 for the output cap. The
environment is fixed by its lock: vLLM 0.31.0 with xgrammar 0.2.7 and llguidance 1.7.6. The served
model, `Qwen/Qwen3.5-9B` at revision `c2022362…`, is an image-text checkpoint whose text model
interleaves linear-attention (Gated DeltaNet) and full-attention layers 3:1, carries an MTP head and
thinks by default.

S3 settles, on those inputs:

- the **local model and precision** (OPEN-D4-1) and **reasoning on or off** (OPEN-D4-2), by a staged
  grid that drops a losing setting early (§3);
- the **unit of LLM work for M10** (OPEN-D4-4): unit or paragraph packets, how paragraph batches merge
  into one unit batch (§3), and the split rule for units whose batch would exceed the output cap;
- the **decoding form** under xgrammar 0.2.7: that it compiles, accepts every reference batch, what it
  costs to compile and whether the compiled grammar is reused; the flat form (S4 V3) if not;
- the **output caps** for M10 and M16 from uncensored p99 sizes, with reasoning tokens counted apart,
  and a proposed M24 extraction cap in characters;
- the **judge** (M16): what a difference presented to it is, agreement with the adjudicated choice,
  and the confidence format;
- **determinism** under online serving, and the recorded-response replay phase 1 tests rely on;
- **cost and memory**, including the server footprint G1 needs for OPEN-D6-2, and whether the local
  tier is a credible first escalation and directional proxy for the hosted passes (D0 tiers).

**Prerequisites.** E4 builds `build/spike-vllm-venv`; I-R2 (scoring) and C1 (contested items) precede
scoring; S4-B's model-facing schema and S4-D's decoding-form result are used when they exist. Disk: a
volume on this machine was full on 2026-10-28; S3-A records free space, and the larger arm needs its
checkpoint downloaded (no 27–35B model is cached). The GPU is exclusive until G1.

## 2. Brief steps as they now run

| Step | Now | Mechanism (source) |
|---|---|---|
| 1 Server | `vllm serve` on the snapshot with `--language-model-only` (no vision tower), `--reasoning-parser qwen3`, `--structured-outputs-config '{"backend":"xgrammar","disable_any_whitespace":true}'`, `--generation-config vllm`, `--enable-prefix-caching`, `--max-model-len 65536`. Chat completions carry the schema as `response_format` `{"type":"json_schema","json_schema":{"name":"ClaimProposalBatch","schema":…}}`, the field a hosted endpoint also takes (D4 §2). The backend is named, never `auto`, so a schema xgrammar rejects fails visibly; launch arguments and versions go in `server.md` | `response_format` becomes `StructuredOutputsParams(json=…)` (`structured_outputs_from_response_format`); under `auto`, `SamplingParams` moves a rejected request to guidance (`_backend_was_auto`); `disable_any_whitespace` (`StructuredOutputsConfig`); checkpoint generation defaults are otherwise inherited ([vLLM overview](../../libraries/analytical_infrastructure/vllm.md) §9.1); model card; corpus-intelligence `services/vllm-native/engine.py` |
| 1a Decoding form (new) | S4-D's form and result if S4-D ran; else derived here from S4-B's model-facing schema by the D2 §7.3 rules (`discriminator`, titles and descriptions stripped; `oneOf` only over `predicate` consts; no `if`/`then`/`not`; nesting ≤ 64), plus two checks 0.31 does not make for itself: `has_xgrammar_unsupported_json_features` is false, and no `allOf` has two or more branches. Without S4-B, hand-built from `format.md` and `reference.md` §5. Offline: `GrammarCompiler(TokenizerInfo.from_huggingface(tok, vocab_size=…), max_threads=8, cache_enabled=True).compile_json_schema(text, any_whitespace=False)`, time and peak memory; every v1 reference model-facing batch, the three examples and SV's and HV's first and final batches, compact, accepted token by token (`GrammarMatcher.accept_token`, then the stop token), as the old `schema_check.py` does for guidance; xgrammar's warnings kept (an unprovably disjoint `oneOf` becomes `anyOf`). Online: first against repeated request latency on one schema text. Where S4's canonical shapes differ from what inputs v1 teach, the scored runs decode the inputs-v1 shape and the difference is listed | D2 §7.3; schema-rules note §3; vLLM 0.31 `backend_xgrammar.py` (compiler cache, `VLLM_XGRAMMAR_CACHE_MB` 512); stable docs add the `allOf` check (xgrammar issue 937); xgrammar 0.2.7 `matcher.py` |
| 1b Reasoning (new) | Per request `chat_template_kwargs: {"enable_thinking": false}` or `true`. Off, the template writes an empty think block, the parser finds reasoning ended in the prompt and the grammar constrains from the first token; on, reasoning is unconstrained and the grammar starts after `</think>`. `max_tokens` bounds reasoning plus batch; `usage.completion_tokens_details.reasoning_tokens` separates them; `thinking_token_budget` bounds reasoning once `--reasoning-config` is set. Checked on two units before the grid | vLLM reasoning outputs and thinking budget; `resolve_reasoning_ended`; `enable_in_reasoning` false; the snapshot's `chat_template.jinja` |
| 1c Determinism and replay (new) | Each core packet twice at concurrency 1 and once inside a 16-request burst; byte-identical outputs counted; repeated with `VLLM_BATCH_INVARIANT=1` (beta) if it starts on this model and GPU, with its cost. Every exchange is stored with its request body, prompt token count, raw text, reasoning, usage, finish reason, model revision, schema sha256 and versions, keyed by the sha256 of the canonical request body; a fixture set (clean batch, repair exchange, truncated output, unlocated quote, judge exchange) is cut for phase 1's tests | vLLM reproducibility: online runs reproduce only under batch invariance (overview §11.4) |
| 2 Packets and prompts | Core and held-out units use the frozen `packet_v1/units/<unit>.md`. Prompt order: system instructions, `guideline.md`, `reference.md`, `format.md`, then the packet, so about 15,000 tokens of parts (50 KB at 3.27 characters per token) form one shared prefix; `schema.yaml` and `model.md` stay out. `code/s3_packet.py` reuses `code/s0r2_inputs.py` and `code/s0r2_sample.py` for paragraph packets and step 4. Packet text counted by L-11; the whole prompt from `usage.prompt_tokens`, cross-checked with `/tokenize` (L-11's open item). Weibull stays reserved | D4 §4.1–§4.2; text-math note §7 |
| 3 Runs | The staged grid of §3; temperature 0, request `seed` 0 (D2 §12.1); `max_tokens` 16,384 with reasoning off and 32,768 on, so no size is censored at the brief's 4,096; outputs reaching the cap are recorded as truncated, never closed by repair. One repair retry with the validator's errors and rule warnings. The best two configurations also on H1–H6 | §3 |
| 4 Output sizes | At least 100 claim-bearing units from the 78 pages, stratified by `qwen_tokens` in `results/s1/sizes.tsv` (2,479 units, p99 739, max 2,197) with all ten units above 1,000 tokens; Weibull excluded; pages outside the stored seven regenerated by `s1_adapter.adapt` (R1) into `results/s3/`, context by the `s0r2_sample.py` M13 query. Batch tokens are completion minus reasoning, plus compact-JSON characters. M10's `max_tokens` = p99 batch tokens over all S3 runs of the chosen configuration plus a stated margin (plus the thinking budget when on); M16's likewise over judge outputs; M24's extraction cap proposed in characters (D8 §3 counts characters). The p99 output-to-unit ratio gives the split rule (a unit whose predicted batch exceeds M10's cap goes to paragraph packets), with the share of corpus units it would split | D4 §4.1, D8 §3 |
| 5 Post-process | `code/s0_check.py --rules` at I-R2, the cascade step of each quote recorded; every quote reaching a fuzzy step also through the text-math note's `p6_quote_tokens.py` token-sequence locator, the first real test of D4 §4.3's proposed order; malformed, truncated, unlocated and warnings before and after the retry; `entity_types` checks stay after generation | D4 §4.3; text-math note L-10; D2 §7.3 |
| 6 Score | `code/s0d_compare.py` at I-R2 against the v1 reference: core, full, evidence, per predicate and unit, with and without `contested.tsv`. First tries beside SV's and HV's `first/` batches (their validator loop is the counterpart of the retry), retried batches beside their final ones. H1–H6 against `adjudication_v1/`, their reference (§3.5; the brief's "no reference" is superseded), and against SV | Instruments §7 |
| 7 Offsets | As the brief, under a decoding-form variant with `{sentence, start, end}` in place of `{sentence, quote}`; T1–T4, best 9B configuration | D2 §7.3 |
| 8 Judge | A difference is one row of the instrument's pass-against-pass diff, in the S0-R2 adjudicator's `diffs/` form: a matched claim pair whose fields differ gives two alternatives (`choose`, `reject` or `unsure`); a claim only one pass has gives one (`accept`, `reject` or `unsure`). D4 §4.1 judge packet from inputs v1, hints none (S2 has not run), the source pass hidden, alternative order seeded; a subset in both orders measures position bias. Adjudicated choice: the reading matching the v1 reference at full tier (neither: `reject`); for A/B also the v0 root adjudication; on H units `adjudication_v1/`; the S0-R2 adjudicator as comparison point. Confidence as D4 §4.3's `low`/`medium`/`high`, scored as agreement per level with n, beside V7. Sets separately, with and without contested items | D4 §4.1, §4.3, M16 |
| 9 Cost | Real packets from an async client at concurrency 1, 8 and 16 (D6 §3.2): latency p50/p95, tokens, throughput; prefix-cache hits and KV usage from `/metrics`; outputs with prefix caching on and off compared on a subset (the hybrid model caches linear-attention state at block boundaries, `mamba_cache_mode: align`); `--gpu-memory-utilization` 0.6 and 0.85; resident memory per model for G1. Co-residency with GLiNER2 is G1's (row 33) | vLLM prefix caching and metrics; `MambaModelConfig` |

## 3. Variants

| Variant | Alternatives | What it would change |
|---|---|---|
| V1 model | 9B BF16 · 9B FP8 (online `--quantization fp8` from the BF16 snapshot) · a 27–35B Qwen3.5-family checkpoint in a vLLM-supported 4-bit or FP8 format with about 22 GB of weights, `blocked` with what is needed if none can be downloaded | OPEN-D4-1; D2 §12.1 `model`; D6 §5's weights row |
| V2 reasoning | off · on | OPEN-D4-2; a kept reasoning-on cell reruns with `thinking_token_budget` at its measured p90 to show quality holds, and M10's `max_tokens` gains that budget |
| V3 examples | 3 (frozen `reference.md` with its §6) · 0 (§6 removed, about 5,000 tokens less) | D4 §4.2's examples part for M10 and its prompt cost |
| V4 packet | unit · paragraph | OPEN-D4-4 for M10; D4 §4.1's split rule |
| V5 decoding form | per-predicate `oneOf` on the `predicate` const · flat (S4 V3: predicate enum, permissive qualifiers, predicate checks after generation) | Only on rejection, slow compile or a malformed rate above 5%; then D2 §7.3 states the flat form for the local tier |
| V6 reasoning sampling | greedy · seeded sampling at the model card's thinking settings | Only if greedy reasoning repeats to the cap; then M10's determinism rests on the seed and the recording |
| V7 judge confidence | stated level · normalized token probability of the chosen label (`logprobs`, `top_logprobs` over the labels the grammar allows; S3-A first checks whether 0.31 returns logprobs before or after the grammar mask) | D4 §4.3's `confidence` field and what D5 §6 consumes |
| V8 reference | whole · filtered by statement kind (S4 V4, if built) | D4 §4.2's local-tier filter above 1,500 tokens; best configuration only |
| V9 MTP | off · `--speculative-config '{"method":"qwen3_next_mtp","num_speculative_tokens":2}'` | Cost only (step 9): D6 §5 latency and M10's launch arguments; outputs compared, not scored |

**The grid.** Not the 24-cell product. From the base cell (9B BF16, reasoning off, three examples,
unit packets) S3 crosses reasoning, then examples, then packet on the 9B model, then FP8 and the larger
model on the surviving settings. A value is dropped when, on the twelve core units, its full-tier F1
is lower by 0.05 or more with the 95% paired-bootstrap interval of the difference below zero (units
resampled jointly, from the per-unit counts in `scores.tsv`), or its malformed-plus-truncated rate
exceeds 5%; a value that is not clearly better yields to the cheaper one (off, fewer prompt tokens,
unit, FP8, 9B). At most four cells are live at once; each decision and its numbers go in `grid.md`. If
the top two change order on H1–H6, both are reported and the OPEN item stays open with that evidence.

**Paragraph packets.** A unit's blocks (S1 segments: paragraphs, list items, `details`) are its
parts. A part packet keeps the unit's sentence numbering and shows only its own `[sN]` lines; it carries
the unit's standing context plus, as further `cN` lines, the sentences of earlier parts that M13 assigns
as binding sites for symbols the part uses, mapped back to their `sN` on merge. Merging prefixes local
refs by part, unifies entities by the I-R2 entity keys (local: type, scope segment, normalized symbol;
global: type, identity, normalized label), unifies claims with equal claim keys and unions their
evidence, and merges statements of one kind whose anchors overlap. A premise a later part restates as
a context-premise assumption (guideline §10.2) unifies with the earlier part's claim by key, so its
condition references survive. The merged batch is scored as a unit batch; unmerged duplicates and
dangling references are counted as merge losses.

## 4. Consumers

| Output | Feeds |
|---|---|
| Launch arguments, request form, backend | phase 1 local LLM tier (M10, M16 Library realization: "exact request field checked in S3"); D2 §12.1 configurations; D6 §5's launch record |
| Decoding form, compile and acceptance results | D2 §7.3's local-tier form (with `s4.decoding-form`); phase 1 M10, the decoding form's consumer |
| Grid and held-out scores | OPEN-D4-1, OPEN-D4-2, OPEN-D4-4 (M10) in the design-phase plan; D2 §12.1 `llm.propose_claims`; D6 §7.5 phase 1 policy; D0 tiers |
| Sizes, caps, split rule | D4 §4.1 and D8 §3 output caps (M10, M16) in phase 1; a later revision of M24's cap (18,000 characters in phase 0); OPEN-D4-4 for long units |
| Determinism results, replay fixtures | phase 1 M10/M16 tests (served from recordings); D4 §1 rule 3's wording for LLM methods; D6 §4 reuse |
| Quote-location steps on local-LLM quotes | D4 §4.3's fuzzy order; phase 1 M10's quotes through the cascade |
| Malformed rate, repair effect | D4 §4.3 (retry with warnings); D2 §7.3 (flat form if above 5%) |
| Judge agreement, calibration, confidence format | phase 1 M16 (pre-adjudication before M24 or not; D6 §7.5 `adjudicate`); D4 §4.3 judge output; D5 §6 |
| Offsets | D2 §7.3 (quote citation stays or not) |
| Performance, memory | G1 (OPEN-D6-2); D6 §5 budgets |

## 5. Packages

| Package | Scope | Outputs | Done when | Consumer |
|---|---|---|---|---|
| S3-A | Steps 1, 1a, 1b, 1c in the vLLM environment | `results/s3/server.md`, `decoding_form/` (schema, sha256, `grammar.tsv`), `determinism.tsv`, `replay/` | The decoding form (or V5's) compiles and accepts every listed batch, or each rejection is a listed form defect; reasoning accounting confirmed on both settings; resident memory recorded for G1 | phase 1 M10, M16 (launch, request and decoding form, replay); G1 |
| S3-B | Steps 2, 3, 5, 6 and the grid (V1–V4; V5, V6 if triggered; V8 if built) | `code/s3_packet.py`, `runs/<config>/<unit>.json`, `scores.tsv`, `grid.md` | Every cell run on the core units or dropped by the rule with its numbers; the best two on H1–H6; scores with and without contested items | phase 1 M10; OPEN-D4-1, OPEN-D4-2, OPEN-D4-4 |
| S3-C | Steps 4 and 9; V9 | `sizes.tsv`, `caps.md`, `perf.tsv` | p99 from uncensored runs with the margin stated; caps for M10 and M16 and the M24 proposal; the split share; each measurement taken or `blocked` naming what is missing | phase 1 M10, M16 caps; a later M24 cap revision; G1 (OPEN-D6-2) |
| S3-D | Step 7 | `offsets.tsv` | Equal, overlap and miss shares on T1–T4 | phase 1 M10 (D2 §7.3's citation form) |
| S3-E | Step 8; V7 | `judge.tsv`, `calibration.tsv` | Agreement and calibration per difference set and confidence form, with and without contested items, position bias stated | phase 1 M16 |
| S3-F | Report | `S3-report.md`, records `s3.*` | The template is satisfied; recommended M10 and M16 configurations, request form, caps and OPEN answers | X2 |

Records (`consumed_by` names the phase 1 item, M10 or M16 card, or G1, and the OPEN item, until phase 1
has package ids): `s3.server`, `s3.determinism`, `s3.replay`, `s3.grid`, `s3.scores`, `s3.held-out`,
`s3.sizes`, `s3.caps`, `s3.perf`, `s3.offsets`, `s3.judge`, and `s3.decoding-form` where S4-D did not
produce it; an arm that cannot run is recorded `not_run` (E5) or `blocked` with its reason.

## 6. Choices left to execution

- The cap margin and its rounding, stated with the p99 it is added to.
- How alternatives are rendered compactly in judge packets, as long as both readings render alike and
  neither names its pass.
- The larger checkpoint, among those that exist with a vLLM-supported quantization and fit.
- The size of the both-orders judge subset and the number of determinism repeats.
