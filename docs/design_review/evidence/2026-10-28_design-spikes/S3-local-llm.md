# S3 · Local LLM on the RTX 5090

**Brief, 2026-10-28.** Run after S0 (references and passes). GPU; reuses the vLLM environment of
the old repository.

## Question

Which local model and settings produce usable claim proposals in the D1 form from the shared
packet and prompt ([D4 §4](../../../design/D4-method-catalog.md#4-the-shared-llm-packet-and-prompt)),
under structured output with the compiled JSON Schema, and how close do they get to the S0
reference? Can the local model pre-adjudicate (pick the adjudicated reading of an A/B
disagreement)? What does it cost in latency and GPU memory beside the encoders?

## Design questions it answers

| Id | Question |
|---|---|
| OPEN-D4-1 | Qwen3.5-9B at BF16 or FP8, or a larger quantized model |
| OPEN-D4-2 | Reasoning on or off for structured proposals |
| OPEN-D4-4 | Unit of LLM work: whole unit, paragraph, or sentence group |
| OPEN-D6-2 | Co-resident or exclusive GPU mode |
| D4 §4.3 | Quote location works; malformed-output rate under structured output |
| D0 tiers | Is the local tier a credible first escalation and directional proxy for hosted models? |

## Inputs

- S0 references, passes A and B, and the A/B differences (`results/s0/`).
- S1 canonical text and segments.
- Guideline v0 (D2 §10) and the model-facing ClaimProposalBatch (D2 §7.3): write the JSON Schema
  by hand, or take S4's compiled output if S4 has run.
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
   parameters) and that the hand-written schema compiles in the structured-output backend.
   Record schema features that fail (`oneOf`, `const`, `$ref` depth) and the workaround.
2. **Packets and prompts.** Write `code/s3_packet.py` that builds D4 §4.1 packets (standing
   context, sentence-numbered text; hints off) and the D4 §4.2 prompt (system, guideline core,
   inventory, examples, output instruction). Examples: 0 or 2, chosen leave-one-out from the
   other core units' references.
3. **Runs.** For each core unit and each configuration: model ∈ {9B BF16, 9B FP8, larger};
   reasoning ∈ {off, on}; examples ∈ {0, 2}; packet ∈ {unit, paragraph}. Temperature 0, fixed
   seed. One repair retry with validation errors. Keep the grid small if time runs short: drop
   the paragraph packets for the larger model first.
4. **Post-process** with the D4 §4.3 steps: schema validation, quote location (record the stage
   at which each quote located), reference and type checks. Count malformed and unlocated
   outputs.
5. **Score** against the S0 reference with `code/s0_compare.py` at the core, full and evidence
   tiers; per predicate and per unit.
6. **Judge.** For every S0 A/B difference, build a judge packet with the two readings as
   alternatives and ask the local model to choose (judge form, D4 §4.3). Score agreement with the
   adjudicated choice, and calibration of its stated confidence.
7. **Cost.** Latency per packet (p50, p95), tokens in and out, throughput at concurrency 1, 8,
   16; GPU memory with `--gpu-memory-utilization` at 0.6 and 0.85; whether GLiNER2.5 base
   (from S2) fits beside the server in co-resident mode.

## Data to collect

| File | Content |
|---|---|
| `results/s3/server.md` | Launch arguments per model, structured-output request form, schema workarounds |
| `results/s3/runs/<config>/<unit>.json` | Raw output and the post-processed batch |
| `results/s3/scores.tsv` | config × unit × tier: precision, recall, F1; malformed; unlocated |
| `results/s3/judge.tsv` | difference × config: chosen, adjudicated, agree, stated confidence |
| `results/s3/perf.tsv` | config × concurrency: latency p50/p95, tokens, throughput, GPU memory |

## How to interpret

| Finding | Reading |
|---|---|
| 9B full-tier F1 within about 0.1 of the S0 A-versus-B agreement | The local tier can propose; phase 1 policy as in D6 §7.5 |
| Larger model clearly better and fits beside encoders | Adopt it; `OPEN-D4-1` closed; budgets in D6 §5 updated |
| Reasoning on helps the full tier (conditions, bindings) but not the core tier | Reasoning on for proposals, off for judging, or the reverse, per the numbers |
| Paragraph packets better than unit packets | Proposals at paragraph level with standing context; `OPEN-D4-4` closed |
| Malformed rate > 5% despite structured output | Simplify the schema shape (flatten `oneOf`) and record the change for the D2 compiler |
| Judge agreement with adjudication ≥ 0.75 with calibrated confidence | M16 pre-adjudication is worth running before Opus |

## Report

`S3-report.md` from the [template](report-template.md), with the recommended M10 and M16
configurations, the structured-output request form, and answers to the OPEN items above.
