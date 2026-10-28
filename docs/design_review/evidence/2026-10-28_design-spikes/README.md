# Design spikes, 2026-10-28

**Status, 2026-10-28: S1, S0 and the S0-R2 revisit have run. S2, S3 and S5 are ready; S4 and S6 are ready and independent; S7 waits on S2 (see the table). Later spikes score against the v1 reference, `results/s0r2/reference_v1/`.**
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
| [S1 Ingest and segmentation](S1-ingest-and-segmentation.md) | Does the D1 evidence model (canonical text, segments, spans, author markup) fit Siegrist HTML? Does sentence splitting survive LaTeX? | D1 §3, OPEN-D1-1, D4 M01–M03 | CPU | **Run** ([report](S1-report.md)) |
| [S0 Reference annotations](S0-reference-annotations.md) | Can the D1 claim model and guideline v0 express what the core units state, and how determinate is it across two blind passes? | D1 §4–§8, OPEN-D1-2/3/4, D2 §9–§10, OPEN-D2-4/5 | Opus (this agent), S1 output or raw page text | **Run** ([report](S0-report.md); revisit [S0-R2](S0-R2-report.md)) |
| [S4 LinkML compilation](S4-linkml-compilation.md) | Does the statistics schema compile to GLiNER2, JSON Schema, rule-engine rules (with the guideline warnings) and the annotator reference as D2 §7 specifies? | D2 §7, OPEN-D2-1/3/6 | CPU; the v1 batches | **Yes**, independent |
| [S6 Storage smoke](S6-storage-smoke.md) | Does the D3 DDL apply on PostgreSQL 18 with pgvector and pg_textsearch; do the v1 trace rows and typed queries work; does the revised statement key settle the meaning key? | D3, OPEN-D3-1/3/4 | Local PostgreSQL; S1 offsets, the v1 reference | **Yes**, independent |
| [S2 GLiNER2.5 on statistics text](S2-gliner-on-statistics-text.md) | What do compiled schemas, `JointIE`, span attributes and classification find; raw, masked or Unicode-rendered math | D4 M05–M07, OPEN-D2-2, OPEN-D5-4 | GPU; S1, the v1 and v0 references | **Yes** |
| [S3 Local LLM on the RTX 5090](S3-local-llm.md) | Which model and settings on annotator inputs v1; structured output from the compiled JSON Schema; quality against the v1 reference and pass SV; output caps; pre-adjudication | D4 M10, M16, OPEN-D4-1/2/4, OPEN-D6-2 | GPU; S1, S0-R2 inputs and passes | **Yes** |
| [S5 Math parsing and verification](S5-math-parsing-and-verification.md) | Math grammar coverage on all spans with the rendition macro tables; token canonical form for keys; symbol scoping; formula equivalence; z3; verifiers | D4 M09, M11, M13, M20, M21, D1 §6.2, OPEN-D4-3/5, OPEN-D7-2 | CPU; S1, the v1 reference | **Yes** |
| [S7 Embeddings and linking](S7-embeddings-and-linking.md) | Embedding model and dimension; concept linking, including parameter names across units; example retrieval | D3 embeddings, D4 M14, OPEN-D3-2 | GPU; S1, S2, the v1 reference | After S2 |

Order: S1 and S0 have run, with S0's revisit S0-R2. S2, S3 and S5 can run in parallel now; S4
and S6 are independent and can run alongside them; S7 follows S2. Each spike stops at its
question's answer (ground rule 7).

S0 and S1 are executed under the spike lane's
[S0/S1 execution plan](../../../plans/design-spikes-s0-s1_2026-10-28.md), which extends these
briefs; by operator direction the time-box does not apply to them. Both have run: [S1 report](S1-report.md), [S0 report](S0-report.md), its revisit with annotator
inputs v1 ([S0-R2 report](S0-R2-report.md)), and a [summary for the design owner](summary-for-design-owner.md).
The design owner's [review of S0 and S1](design-owner-review-S0-S1.md) lists the follow-ups and
corrections they call for in the design documents and in the S2–S7 briefs. The core units' locators are
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

`sample.json` records each core unit's exact segment keys and offsets (written in S1), so later
spikes address the same spans. `results/s0r2/sample.json` adds, with their standing context
assembled by query over M13 binding sites, six held-out units (H1–H6, from the Pareto and
ChiSquare pages) and the three worked-example units (E1–E3, from the Weibull page, which is
reserved for examples: no spike annotates or scores it).

**Renditions.** M01 produces renditions with html5lib (D4 M01), while S0 and S1 used libxml2. On
the seven pages S0 and S0-R2 use they are content-identical, differing only in keys
([s1.rendition-identity](records/s1.rendition-identity.json)). Spikes take renditions and offsets
from `sample.json` and `results/s0r2/sample.json`, the libxml2 renditions the references are stored
on.

**Reference.** Later spikes score against the v1 reference, `results/s0r2/reference_v1/` (stored
form; model-facing form in `results/s0r2/reference_model_v1/`): the S0 reference conformed to
guideline v1 (record [s0r2.reference-v1](records/s0r2.reference-v1.json)). The v0 reference,
`results/s0/reference/`, stays as a second reference where a brief asks for it.

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
  records/                 one record per finalized result (ADR-0010); index below
  catalog.sql              catalog views over this folder's results (when present)
```

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 46 current, 10 superseded.


**Environment**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Spike environment and model revisions](records/e0.environment.json) | E0 | passed | OPEN-D9-1 | 2026-10-28 |
| [CPU spike environment for S4, S6 and I-R2](records/e4.env-cpu.json) | E4a | passed | OPEN-D9-1 | 2026-10-28 |

**Parsing (ADR-0009)**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Lark grammar-extension probe](records/parse.lark-probe.json) | PARSE-01 | passed | PARSE-01, ADR-0009, OPEN-D4-3 | 2026-10-28 |
| [regex probe: quote cascade and math delimiting](records/parse.regex-probe.json) | PARSE-01 | passed | PARSE-01, ADR-0009, D4 §4.3 | 2026-10-28 |

**S0 Reference annotations**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Comparison instruments, review and math grammar, with the token form for keys (I-R2)](records/s0.instruments-ir2.json) | I-A, I-B, I-R1, I-R2 | passed | D7 §5, D4 §4.3, D1 §6.2, ADR-0012, OPEN-D7-2 | 2026-10-28 |
| [Blind annotation packets](records/s0.packets.json) | S0-A | passed | OPEN-D8-3, D7 §3.2 | 2026-10-28 |
| [Offset-form evidence probe](records/s0.offset-probe.json) | S0-B | partial | D2 §7.3 | 2026-10-28 |
| [Pass A: blind annotation of the twelve core units (Claude Opus 5.5, golden inputs)](records/s0.pass-a.json) | S0-B | passed | OPEN-D8-3, OPEN-D1-2, OPEN-D1-3, OPEN-D2-4, OPEN-D2-5 | 2026-10-28 |
| [Pass B: blind annotation of the twelve core units (Claude Opus 5.5, golden inputs)](records/s0.pass-b.json) | S0-B | passed | OPEN-D8-3, OPEN-D1-2, OPEN-D1-3, OPEN-D2-4, OPEN-D2-5 | 2026-10-28 |
| [The worked trace as model-facing batches](records/s0.trace-batches.json) | S0-C | passed | D1 §12, trace.md | 2026-10-28 |
| [Passes against the trace and the old-repository witness](records/s0.trace-diff.json) | S0-C | passed | trace.md, D2 §10 | 2026-10-28 |
| [Root adjudication of A and B into the reference](records/s0.adjudication.json) | S0-D | passed | D7 §3.4, OPEN-D1-3, OPEN-D2-5 | 2026-10-28 |
| [D7 adjudicator session (Haiku)](records/s0.adjudication-d7.json) | S0-D | passed | D7 §3.4 | 2026-10-28 |
| [D7 adjudicator session (Sonnet)](records/s0.adjudication-d7-sonnet.json) | S0-D | passed | OPEN-D8-3 | 2026-10-28 |
| [Root adjudication against the D7 adjudicator session](records/s0.adjudication-determinacy-ir2.json) | S0-D, S0-G | passed | D7 §3.4 | 2026-10-28 |
| [Agreement between the blind passes, with keys and trace comparisons](records/s0.agreement-ir2.json) | S0-D, S0-G | passed | D7 §3.3, D7 §5, OPEN-D3-4, D1 §10.1 | 2026-10-28 |
| [Pass H: blind annotation of the twelve core units (Claude Haiku 5.5, golden inputs (control for P))](records/s0.pass-h.json) | S0-E | passed | OPEN-D4-4, OPEN-D1-2 | 2026-10-28 |
| [Pass P: blind annotation of the twelve core units (Claude Haiku 5.5, unit packets only)](records/s0.pass-p.json) | S0-E | passed | OPEN-D4-4, OPEN-D1-2 | 2026-10-28 |
| [Pass SG: blind annotation of the twelve core units (Claude Sonnet 5.5, golden inputs)](records/s0.pass-sg.json) | S0-E | passed | OPEN-D4-4 | 2026-10-28 |
| [Pass SP: blind annotation of the twelve core units (Claude Sonnet 5.5, unit packets only)](records/s0.pass-sp.json) | S0-E | passed | OPEN-D4-4 | 2026-10-28 |
| [Every pass against the reference; packet versus model effect](records/s0.pass-scores-ir2.json) | S0-E, S0-G | passed | OPEN-D4-4, OPEN-D1-2, D7 §3 | 2026-10-28 |
| [Sonnet passes and adjudicator against the reference and the Opus passes](records/s0.sonnet-scores-ir2.json) | S0-E, S0-G | passed | OPEN-D4-4, OPEN-D7-2 | 2026-10-28 |
| [M13 rule scoping against the reference (D2 lexicon with 'if')](records/s0.m13-probe-2.json) | S0-E, S0-R1, S0-G | passed | OPEN-D4-5, OPEN-D1-2, D4 M13 | 2026-10-28 |
| [Gap analysis](records/s0.gaps.json) | S0-F | passed | D2 §9, D2 §10, D1, OPEN-D2-4, OPEN-D2-5, OPEN-D5-1, OPEN-D1-3 | 2026-10-28 |
| [S0 report (with the Sonnet runs and the input diagnosis), re-rendered after I-R2](records/s0.report-3.json) | S0-F | passed | OPEN-D1-2, OPEN-D1-3, OPEN-D1-4, OPEN-D2-4, OPEN-D2-5, OPEN-D5-1, OPEN-D8-3, OPEN-D4-4, OPEN-D4-5, OPEN-D3-4, OPEN-D7-2 | 2026-10-28 |
| [Batch and packet sizes](records/s0.sizes.json) | S0-F | passed | OPEN-D4-4, D4 §4.1 | 2026-10-28 |
| [Condition failures against the reference, classified by shape](records/s0.condition-classes.json) | S0-G | passed | OPEN-D4-4 | 2026-10-28 |
| [Stored forms of every batch set (revised quote cascade)](records/s0.stored.json) | S0-G | passed | D4 §4.3, ADR-0009 | 2026-10-28 |
| [Adjudicator (Sonnet) over passes SV and HV, inputs v1](records/s0r2.adjudication.json) | S0-R2 | passed | OPEN-D8-3 | 2026-10-28 |
| [Annotator inputs v1: guideline v1, schema-generated reference, worked examples, query context](records/s0r2.inputs.json) | S0-R2 | passed | OPEN-D4-4, OPEN-D1-2 | 2026-10-28 |
| [Pass HV: Haiku 5.5 on inputs v1, unit packets only](records/s0r2.pass-hv.json) | S0-R2 | passed | OPEN-D4-4 | 2026-10-28 |
| [Pass SV: Sonnet 5.5 on inputs v1, unit packets only](records/s0r2.pass-sv.json) | S0-R2 | passed | OPEN-D4-4 | 2026-10-28 |
| [The S0 reference conformed to guideline v1](records/s0r2.reference-v1.json) | S0-R2 | passed | — | 2026-10-28 |
| [S0-R2 report (re-rendered after I-R2)](records/s0r2.report-2.json) | S0-R2 | passed | OPEN-D4-4 | 2026-10-28 |
| [S0-R2 scores: v0 and v1 passes against the v1 reference; pass against pass on core and held-out units](records/s0r2.scores-ir2.json) | S0-R2 | passed | OPEN-D4-4, OPEN-D7-2 | 2026-10-28 |

**S1 Ingest and segmentation**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Adapter variants and rendering conventions](records/s1.variants.json) | S1-A | passed | HTML-02, HTML-03, HTML-04, HTML-05, HTML-07 | 2026-10-28 |
| [Adapter on the four spike pages, sample and invariants](records/s1.adapter.json) | S1-A, S1-B | passed | D1 §3, HTML-01, HTML-02, HTML-03, HTML-04, HTML-07 | 2026-10-28 |
| [Sentence-boundary gold and segmentation matrix](records/s1.sentence-gold.json) | S1-C | passed | OPEN-D1-1, D4 M03 | 2026-10-28 |
| [78-page corpus run](records/s1.corpus.json) | S1-D | passed | HTML-01, HTML-02, HTML-05, HTML-06, OPEN-D4-4, OPEN-D2-2 | 2026-10-28 |
| [trafilatura baseline](records/s1.trafilatura.json) | S1-E | passed | HTML-07 | 2026-10-28 |
| [NIST generality probe](records/s1.nist.json) | S1-F | partial | HTML-07, D4 M01 | 2026-10-28 |
| [78-page corpus run and reference renditions under html5lib](records/s1.corpus-html5lib.json) | S1-G | partial | D4 M01 parser, OPEN-D4-4 | 2026-10-28 |
| [S1 report](records/s1.report.json) | S1-G | passed | OPEN-D1-1, HTML-01, HTML-02, HTML-03, HTML-04, HTML-05, HTML-06, HTML-07 | 2026-10-28 |
| [Profile-driven math delimiting (S1-R1)](records/s1.profile-delimiting.json) | S1-R1 | passed | ADR-0009, HTML-07 | 2026-10-28 |
| [html5lib and libxml2 renditions of the S0/S0-R2 pages are content-identical](records/s1.rendition-identity.json) | S1-R2 | passed | — | 2026-10-28 |

**Token form (ADR-0012)**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Token form of every math span of the four spike pages (parity file for core/tex.py)](records/i-r2.token-form-parity.json) | I-R2 | passed | D1 §6.2, ADR-0012 | 2026-10-28 |

**Superseded**

| Record | Superseded by | Finalized |
|---|---|---|
| [Comparison instruments, review and math grammar](records/s0.instruments.json) | s0.instruments-ir2 | 2026-10-28 |
| [Root adjudication against the D7 adjudicator session](records/s0.adjudication-determinacy.json) | s0.adjudication-determinacy-ir2 | 2026-10-28 |
| [Agreement between the blind passes, with keys and trace comparisons](records/s0.agreement.json) | s0.agreement-ir2 | 2026-10-28 |
| [Every pass against the reference; packet versus model effect](records/s0.pass-scores.json) | s0.pass-scores-ir2 | 2026-10-28 |
| [Sonnet passes and adjudicator against the reference and the Opus passes](records/s0.sonnet-scores.json) | s0.sonnet-scores-ir2 | 2026-10-28 |
| [M13 rule scoping against the reference](records/s0.m13-probe.json) | s0.m13-probe-2 | 2026-10-28 |
| [S0 report](records/s0.report.json) | s0.report-2 | 2026-10-28 |
| [S0 report (with the Sonnet runs and the input diagnosis)](records/s0.report-2.json) | s0.report-3 | 2026-10-28 |
| [S0-R2 report](records/s0r2.report.json) | s0r2.report-2 | 2026-10-28 |
| [S0-R2 scores: v0 and v1 passes against the v1 reference; pass against pass on core and held-out units](records/s0r2.scores.json) | s0r2.scores-ir2 | 2026-10-28 |
<!-- evidence-index:end -->
