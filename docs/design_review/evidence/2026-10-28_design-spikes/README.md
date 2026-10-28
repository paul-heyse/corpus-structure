# Design spikes, 2026-10-28

**Status: all briefs written 2026-10-28; S1, S0, S4 and S6 can run now; S2, S3, S5 and S7 need S0 and S1 outputs (see the table).**
Throwaway investigations that test the proposed design ([docs/design](../../../design/README.md))
against the real statistics corpus before code is built. A spike answers named design questions
(`OPEN-Dn-k`) with evidence. It writes no product code.

## Why spikes first

The previous repository adopted libraries by assumption and never measured them on the target
text. These spikes check, on Siegrist pages, the few behaviours the design depends on: whether
the evidence model fits the HTML, whether the claim model can express what the pages say, what
GLiNER2.5 and a local LLM actually find in math-dense prose, whether LinkML compiles into what
GLiNER2 and the LLM need, and whether LaTeX parses.

## The spikes

| Spike | Question | Informs | Needs | Ready |
|---|---|---|---|---|
| [S1 Ingest and segmentation](S1-ingest-and-segmentation.md) | Does the D1 evidence model (canonical text, segments, spans, author markup) fit Siegrist HTML? Does sentence splitting survive LaTeX? | D1 §3, OPEN-D1-1, D4 M01–M03 | CPU | **Yes** |
| [S0 Reference annotations](S0-reference-annotations.md) | Can the D1 claim model and guideline v0 express what the core units state, and how determinate is it across two blind passes? | D1 §4–§8, OPEN-D1-2/3/4, D2 §9–§10, OPEN-D2-4/5 | Opus (this agent), S1 output or raw page text | **Yes** |
| [S4 LinkML compilation](S4-linkml-compilation.md) | Does the statistics schema compile to GLiNER2, JSON Schema and rule-engine as D2 §7 specifies? | D2 §7, OPEN-D2-1/3/6 | CPU | **Yes** (S0 batches improve the validation step) |
| [S6 Storage smoke](S6-storage-smoke.md) | Does the D3 DDL apply on PostgreSQL 18 with pgvector and pg_textsearch; do trace rows and typed queries work? | D3, OPEN-D3-1/3/4 | Local PostgreSQL | **Yes** (S1 offsets improve the rows) |
| [S2 GLiNER2.5 on statistics text](S2-gliner-on-statistics-text.md) | What do compiled schemas, `JointIE`, span attributes and classification find; raw versus masked math | D4 M05–M07, OPEN-D2-2, OPEN-D5-4 | GPU; S0, S1 | After S0, S1 |
| [S3 Local LLM on the RTX 5090](S3-local-llm.md) | Which model and settings; structured output from the compiled JSON Schema; quality against S0; pre-adjudication | D4 M10, M16, OPEN-D4-1/2/4, OPEN-D6-2 | GPU; S0, S1 | After S0, S1 |
| [S5 Math parsing and verification](S5-math-parsing-and-verification.md) | LaTeX parse rates with the source macros; symbol scoping; formula equivalence; z3; verifiers | D4 M09, M11, M13, M20, M21, OPEN-D4-3/5, OPEN-D7-2 | CPU; S1 (parsing), S0 (the rest) | Parsing after S1; rest after S0 |
| [S7 Embeddings and linking](S7-embeddings-and-linking.md) | Embedding model and dimension; concept linking; example retrieval | D3 embeddings, D4 M14, OPEN-D3-2 | GPU; S0, S1, S2 | After S2 |

Order: S1 first, then S0 (it can start on raw page text while S1 finishes). S4 and S6 are
independent and can run alongside. S2, S3 and S5 run in parallel once S0 and S1 have landed; S7
follows S2. Each spike stops at its question's answer (ground rule 7).

S0 and S1 are executed under the spike lane's
[S0/S1 execution plan](../../../plans/design-spikes-s0-s1_2026-10-28.md), which extends these
briefs; by operator direction the time-box does not apply to them. The core units' locators are
drafted in [D2 §12.2](../../../design/D2-schema-and-guidelines.md#122-slicesyaml); S1 confirms
that they resolve.

## The spike sample

All spikes use the same material, so results can be compared and followed across methods.

**Spike pages** (whole pages, for ingest, throughput and counts), under
`docs/statistics_corpus/corpus/siegrist_random/random/`:

- `special/LocationScale.html`
- `special/Normal.html`
- `special/LogNormal.html`
- `special/Gamma.html`

**Core units** (for detailed quality comparison). Twelve units: the four
[trace units](../../../design/trace.md) and eight more, chosen to cover different mechanisms.

| Id | Page | Locator | Why |
|---|---|---|---|
| T1 | LocationScale | lead-in paragraph + unit `dfn1` | Trace: construction definition |
| T2 | Normal | paragraph beginning "Suppose again that X has the normal distribution with location parameter" | Trace: "respectively" |
| T3 | Normal | unit `rel1` | Trace: theorem with premise, restrictions, conclusion, proof |
| T4 | LogNormal | unit `dfn` with its list items | Trace: family defined by transformation |
| U5 | Normal | unit `rel2` (sum of independent normals) with its list items | One premise governing two conclusions; independence |
| U6 | Normal | paragraph defining the standard score | Conditional definition ("if X has a normal distribution then Z is standard normal") |
| U7 | Normal | paragraph on the degenerate normal convention ("it's convenient to consider a constant…") | Convention modality |
| U8 | Normal | the rod and hole exercise | Exemplified values with units; posed quantity |
| U9 | LogNormal | the product of independent lognormals over an indexed family | Indexed family; `forall` conditions |
| U10 | Gamma | unit `dfn4` (scale family: X = bZ) | Construction applied to a family; parameter mapping |
| U11 | Gamma | unit `rel2` (sum of independent gammas) | Conditions with a common scale parameter |
| U12 | Gamma | unit `mom1` (mean and variance) | Property predicates |

The S1 agent records each core unit's exact segment keys and offsets in `sample.json` once the
canonical text exists, so later spikes address the same spans.

## Ground rules for the executing agent

1. **Read first:** this README, the spike's brief, [D1](../../../design/D1-knowledge-representation.md),
   the [trace](../../../design/trace.md), and the parts of D2 the brief names.
2. **Throwaway code only**, in `code/` inside this folder. Nothing under `python/` or `domains/`.
   The spike environment is a uv project in this folder whose virtual environment lives outside
   it: run with `UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run …` (the evidence folder must
   never contain a venv). Pin what you add exactly.
3. **Reasonable assumptions are fine; record them.** When a brief leaves a choice open, choose,
   and write the choice and why in the report's Assumptions section. Do not stop to ask unless a
   choice would invalidate the spike's question.
4. **Do not edit the design documents.** Put design consequences in the report's "Design
   implications" section, each tied to an `OPEN-Dn-k` id or a section. The design owner folds
   them into the D-documents and records the disposition in the active plan.
5. **Keep outputs small and inspectable.** Results go to `results/<spike>/` as JSON, JSONL, TSV
   or Markdown. Nothing large or binary without Git LFS. The corpus itself is gitignored; refer
   to it by path, quote at most a sentence.
6. **Report** in `<spike>-report.md` using the [report template](report-template.md). Outcomes
   are `passed`, `failed`, `blocked` (name the missing prerequisite) or `not_run`, with the
   command that produced each; date every verified claim.
7. **Time-box.** Each spike should take one working session. If it grows, stop at the question's
   answer and list the rest as follow-ups.

## Folder layout

```text
2026-10-28_design-spikes/
  README.md                this file
  report-template.md
  S0-reference-annotations.md, S1-ingest-and-segmentation.md, …   briefs
  S0-report.md, S1-report.md, …                                    reports (written by the spike agent)
  pyproject.toml, uv.lock  spike environment (venv outside the folder)
  sample.json              core-unit locators and offsets (written in S1)
  code/                    throwaway scripts
  results/s0/, results/s1/, …
```
