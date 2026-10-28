# S3 · Local LLM on the RTX 5090

**Brief, 2026-10-28; revised after S0, S1 and S0-R2.** Ready: S0 and S0-R2 have references,
passes and annotator inputs v1; S1 has canonical text. GPU; reuses the vLLM environment of the
old repository.

## Question

Which local model and settings produce usable claim proposals in the D1 form from the shared
packet and prompt ([D4 §4](../../../design/D4-method-catalog.md#4-the-shared-llm-packet-and-prompt)),
built from annotator inputs v1, under structured output with the compiled JSON Schema, and how
close do they get to the v1 reference and to the hosted passes on the same inputs? Can the local
model pre-adjudicate (pick the adjudicated reading of a disagreement between two passes)? What
does it cost in latency, output length and GPU memory beside the encoders?

## Design questions it answers

| Id | Question |
|---|---|
| OPEN-D4-1 | Qwen3.5-9B at BF16 or FP8, or a larger quantized model |
| OPEN-D4-2 | Reasoning on or off for structured proposals |
| OPEN-D4-4 | Unit of LLM work for the local model: whole unit, paragraph, or sentence group (settled for golden and agent packets by S0-R2; open for M10) |
| OPEN-D6-2 | Co-resident or exclusive GPU mode |
| D4 §4.1, D8 §3 | The output cap beside each input cap: `max_tokens` for M10 and M24 (A13) |
| D4 §4.3 | Quote location works; malformed-output rate under structured output; whether a model without tools can cite by offsets |
| D0 tiers | Is the local tier a credible first escalation and directional proxy for hosted models? |

## Inputs

- **Annotator inputs v1** (record [s0r2.inputs](records/s0r2.inputs.json)): guideline v1
  (`s0r2/guideline_v1.md`; its core sections as `results/s0r2/inputs/packet_v1/guideline.md`
  carries them), the reference generated from the schema
  (`results/s0r2/inputs/packet_v1/reference.md`), the model-facing output format
  (`results/s0r2/inputs/packet_v1/format.md`), the three worked examples from the Weibull page
  (`results/s0r2/examples/`, packets in `results/s0r2/inputs/example_packets/`), and standing
  context assembled by query over M13 binding sites, each sentence citable as `cN`
  (`results/s0r2/sample.json`, built by `code/s0r2_sample.py`; the packets by
  `code/s0r2_inputs.py`).
- **Reference and comparison passes.** The v1 reference, `results/s0r2/reference_v1/` (stored
  form). Pass SV (Sonnet 5.5 on inputs v1, packets only; `results/s0r2/stored/pass_sv`) is the
  upper reference point: core 0.95, full 0.77, evidence 0.72 against the v1 reference. Pass HV
  (Haiku 5.5, `results/s0r2/stored/pass_hv`) is the second point: full 0.68.
- **Differences for the judge test.** S0's A/B differences (`results/s0/compare/a_vs_b/`), with the
  root adjudication (`results/s0/adjudication.md`, folded into the reference) as the adjudicated
  choice; and S0-R2's SV/HV differences (`results/s0r2/compare/sv_vs_hv/`), with the v1 reference as
  the adjudicated choice and the S0-R2 Sonnet adjudicator (`results/s0r2/adjudication_v1/`) as a
  comparison point.
- **Validator.** `code/s0_check.py --rules`: schema validation, the quote cascade into stored form
  and the guideline-rule warnings of `code/s0r2_rules.py`.
- **Sizes.** S0 batches reached about 2,500 Qwen3.5-9B tokens, two to nineteen times their unit
  (record [s0.sizes](records/s0.sizes.json), `results/s0/size.tsv`); S1's unit sizes over 78 pages
  are in `results/s1/sizes.tsv`.
- **Renditions.** M01 produces renditions with html5lib (D4 M01); S0 and S1 used libxml2. On the
  seven pages S0 and S0-R2 use, the two are content-identical: same text, segments, sentences and
  offsets; only keys differ, because the rendition key hashes the parser (record
  [s1.rendition-identity](records/s1.rendition-identity.json)). Take renditions, sentence ids and
  offsets from `sample.json` and `results/s0r2/sample.json`, the libxml2 renditions the references
  are stored on.
- **JSON Schema.** Take S4's compiled model-facing schema if S4 has run; otherwise write it by
  hand from `format.md`, including `cN` citations, `alternatives` and `extent`.
- The vLLM environment: `/home/paul/corpus-intelligence/services/vllm-native/pyproject.toml` and
  `uv.lock` (vllm 0.31.0, torch 2.13.0). Copy both into `code/vllm/` and sync with a venv outside
  the evidence folder (`UV_PROJECT_ENVIRONMENT=$REPO/build/spike-vllm-venv`). Run vLLM's standard
  OpenAI-compatible server (`vllm serve`), not the old private socket protocol; the old
  `engine.py` shows how it passed structured outputs and the reasoning parser.
- Models from the local Hugging Face cache: `Qwen3.5-9B`. For the larger arm, use a quantized
  model of 27–35B that fits about 22 GB if one is cached or can be downloaded; otherwise mark that
  arm `blocked` and say what is needed.

## Procedure

1. **Server and structured output.** Start the server; confirm the request field that enforces a
   JSON Schema (OpenAI `response_format` with `json_schema`, or vLLM's structured-output
   parameters) and that the schema compiles in the structured-output backend. Record schema
   features that fail (`oneOf`, `const`, `$ref` depth) and the workaround.
2. **Packets and prompts.** Write `code/s3_packet.py` that builds D4 §4.1 packets and the D4 §4.2
   prompt from inputs v1, reusing `code/s0r2_inputs.py` and `code/s0r2_sample.py` rather than
   rewriting them: sentence-numbered unit text, query-assembled standing context as `cN`
   sentences, hints off; system, guideline v1 core sections, the generated reference, examples,
   output instruction. Examples: none, or the three Weibull worked examples. The Weibull page is
   reserved for examples (A4): no S3 unit comes from it.
3. **Runs.** For each core unit and each configuration: model ∈ {9B BF16, 9B FP8, larger};
   reasoning ∈ {off, on}; examples ∈ {0, 3}; packet ∈ {unit, paragraph}. Temperature 0, fixed
   seed. Start with `max_tokens` 4,096, above the S0 batch maximum, and record every output that
   reaches it. One repair retry, given the validator's schema errors and its guideline-rule
   warnings. Keep the grid small if time runs short: drop the paragraph packets for the larger
   model first. Run the best two configurations on the six held-out units (H1–H6) as well.
4. **Output sizes (A13).** Run the chosen configuration on at least 100 further units from the 78
   pages, stratified by unit size from `results/s1/sizes.tsv` and excluding the Weibull page,
   with packets built by the same context rule. These are not scored; record output tokens,
   truncations and malformed outputs. Set the recommended `max_tokens` for M10 from the p99 of
   output tokens over all S3 runs, with a stated margin, and propose M24's from the same
   distribution.
5. **Post-process** with the D4 §4.3 steps: `code/s0_check.py --rules` (schema validation, quote
   location into stored form, reference and type checks, rule warnings). Record the stage at
   which each quote located. Count malformed and unlocated outputs, and warnings before and after
   the repair retry.
6. **Score** against the v1 reference with `code/s0d_compare.py`
   (`S0_SAMPLE=results/s0r2/sample.json`) at the core, full and evidence tiers, per predicate and
   per unit, beside SV and HV. On the held-out units there is no reference: score pass against
   pass, the local output against SV.
7. **Offsets without tools.** S0's offset probe did not test this: its annotator counted offsets
   with tool scripts. On T1–T4, ask the 9B model in its best configuration to cite evidence by
   character offsets within each numbered sentence instead of quotes, with no tools. Report the
   share of cited spans that equal, overlap or miss the text the same run's quote form located.
8. **Judge.** For every S0 A/B difference and every S0-R2 SV/HV difference, build a judge packet
   from inputs v1 with the two readings as alternatives and ask the local model to choose (judge
   form, D4 §4.3). Score agreement with the adjudicated choice, and calibration of its stated
   confidence; report the two difference sets separately.
9. **Cost.** Latency per packet (p50, p95), tokens in and out, throughput at concurrency 1, 8,
   16; GPU memory with `--gpu-memory-utilization` at 0.6 and 0.85; whether GLiNER2.5 base
   (from S2) fits beside the server in co-resident mode.

## Data to collect

| File | Content |
|---|---|
| `results/s3/server.md` | Launch arguments per model, structured-output request form, schema workarounds |
| `results/s3/runs/<config>/<unit>.json` | Raw output, warnings, the repair exchange and the post-processed batch |
| `results/s3/scores.tsv` | config × unit × tier: precision, recall, F1 against the v1 reference (and against SV on held-out units); malformed; unlocated |
| `results/s3/sizes.tsv` | config × unit: input tokens, output tokens, truncated; the p99 and the proposed `max_tokens` |
| `results/s3/offsets.tsv` | unit × span: cited offsets, quote-located span, equal / overlap / miss |
| `results/s3/judge.tsv` | difference set × difference × config: chosen, adjudicated, agree, stated confidence |
| `results/s3/perf.tsv` | config × concurrency: latency p50/p95, tokens, throughput, GPU memory |

## How to interpret

| Finding | Reading |
|---|---|
| 9B full-tier F1 within about 0.1 of SV (0.77), or at HV's level (0.68) | The local tier can propose; phase 1 policy as in D6 §7.5 |
| Larger model clearly better and fits beside encoders | Adopt it; `OPEN-D4-1` closed; budgets in D6 §5 updated |
| Reasoning on helps the full tier (conditions, bindings) but not the core tier | Reasoning on for proposals, off for judging, or the reverse, per the numbers |
| Paragraph packets better than unit packets | Proposals at paragraph level with standing context; `OPEN-D4-4` closed for M10 |
| Worked examples help the 9B model as they help the hosted passes | Keep them in the M10 prompt; their token cost goes into D4 §4.1's input cap |
| Malformed rate > 5% despite structured output | Simplify the schema shape (flatten `oneOf`) and record the change for the D2 compiler |
| Rule warnings in the repair retry fix most remaining warnings | Keep the retry with warnings in D4 §4.3 |
| Output p99 well under the starting cap | That p99 plus margin is M10's `max_tokens`; D4 §4.1 and D8 §3 state it beside the input cap |
| Offsets without tools mostly miss | Quote citation stays the model-facing form (D2 §7.3) |
| Judge agreement with adjudication ≥ 0.75 with calibrated confidence | M16 pre-adjudication is worth running before Opus |

## Report

`S3-report.md` from the [template](report-template.md), with the recommended M10 and M16
configurations, the structured-output request form, the output caps, and answers to the OPEN
items above.
