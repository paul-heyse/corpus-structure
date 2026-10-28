# Design spikes: the spike plan series (S0–S7)

**Status:** **Active** (revised 2026-10-28): S0 and S1, their revisits and X1 are complete; S2–S7
are planned (rows 23 onward). Reports so far: [S1](../design_review/evidence/2026-10-28_design-spikes/S1-report.md), [S0](../design_review/evidence/2026-10-28_design-spikes/S0-report.md),
[S0-R2](../design_review/evidence/2026-10-28_design-spikes/S0-R2-report.md). This series owns spike execution and its evidence; it executes
design-phase queue items Q1, Q2, Q3 (S4, S6), Q6 (S2, S3, S5) and Q7 (S7) of
[design-phase_2026-10-28](design-phase_2026-10-28.md), which owns design findings and OPEN
dispositions. The production build is the [phase 0 series](phase-0_2026-10-28.md); spike packages
name the phase 0 package each unblocks, and phase 0 cites spike evidence record ids, never this
plan's status cells. **Revised:** 2026-10-28.

This coordinator owns the combined scope, shared decisions, cross-document contracts, the
execution queue, finding disposition and completion conditions for the design spikes. It
started with S0 and S1 and grows (§11): later spikes and revisits of earlier ones join the same
series. The supporting documents:

| Document | Owns |
|---|---|
| [S1 ingest and segmentation](design-spikes-s0-s1/S1-ingest-segmentation.md) | HTML library selection, the throwaway M01/M03 adapter, its variants and measurements, `sample.json` |
| [S0 reference annotations](design-spikes-s0-s1/S0-reference-annotations.md) | Blind annotation protocol, adjudication into the S0 reference, determinacy and gap analyses, OPEN answers |
| [Comparison instruments](design-spikes-s0-s1/comparison-instruments.md) | Batch contract and validators, quote locator, aligner, agreement tiers and keys; reused by S2/S3 |
| [S4 LinkML compilation](design-spikes-s0-s1/S4-linkml-compilation.md) | Schema loading and every D2 §7 compiler on schema v0; rules and the `guideline:` group; the generated annotator reference |
| [S6 Storage smoke](design-spikes-s0-s1/S6-storage-smoke.md) | D3 DDL on PostgreSQL 18; v1 trace rows; queries, BM25 and vectors; the revised statement key |
| [S5 Math parsing and verification](design-spikes-s0-s1/S5-math-verification.md) | Grammar coverage and the token-key property; scoping beyond the core units; equivalence tiers; z3 and verifiers |
| [S2 GLiNER2](design-spikes-s0-s1/S2-gliner2.md) | Encoder extraction on math-dense text: schemas, math variants, long units, candidate scoring |
| [S3 Local LLM](design-spikes-s0-s1/S3-local-llm.md) | Local model and settings under structured output from inputs v1; judge; output caps |
| [S7 Embeddings and linking](design-spikes-s0-s1/S7-embeddings-linking.md) | Embedding model and dimension; concept linking; cross-unit parameter names; example retrieval |

The briefs remain the statement of each spike's question:
[S1 brief](../design_review/evidence/2026-10-28_design-spikes/S1-ingest-and-segmentation.md),
[S0 brief](../design_review/evidence/2026-10-28_design-spikes/S0-reference-annotations.md),
the S2–S7 briefs in the same folder, [spike README](../design_review/evidence/2026-10-28_design-spikes/README.md). This plan extends
their scope; where it differs from a brief, this plan governs.

## 1. Why these spikes, and what they must decide

The target design (D0–D9 and the [worked trace](../design/trace.md), revised by the 2026-10-28
review fold-in) is entirely `Proposed`.
Every later stage cites spans into a canonical text and is scored against claims in D1 form, so
two premises carry most of the risk and are cheapest to test now, before D3 fixes tables:

1. **Evidence model fit (S1).** Siegrist HTML can be linearized into one canonical text per
   rendition with a contiguous segment tree, stable offsets, author markup kept as attributes
   and LaTeX kept verbatim (D1 §3); sentence boundaries survive inline math (OPEN-D1-1).
2. **Claim model and guideline determinacy (S0).** D1 §4–§8 plus the statistics schema and
   guideline v0 (D2 §9–§10) can state what the core units say, and two independent annotators
   following the guideline produce the same claims. S0's adjudicated batches become the
   reference S2 (GLiNER2) and S3 (local LLM) are scored against.

The operator directed (2026-10-28) that both spikes be executed as completely as is useful:
beyond the briefs, investigate the plausible implementation and library variants that could
change the analytical outputs, and through them the design, at higher rigour than the briefs
ask. Outcomes are analytical; wall-clock measurements are incidental and not a criterion. The
spike README's one-session time-box (ground rule 7) does not apply to S0 and S1.

### Design items these spikes settle

| Item | Question (owner) | Settled by |
|---|---|---|
| OPEN-D1-1 | Sentence segmentation on math-dense paragraphs; masking? ([D1 §13](../design/D1-knowledge-representation.md#13-open-questions)) | S1 §6 |
| OPEN-D1-2 | `section` extent for variable scope, or statement scope + "Suppose again" | S0 §5, with S1's section synthesis |
| OPEN-D1-3 | `FamilyParameter` identity by role name or source symbol | S0 §5 |
| OPEN-D1-4 | `section` extent for page-level standing assumptions | S0 §5 |
| OPEN-D2-4 | Separate property predicates or one `has_property` ([D2 §11](../design/D2-schema-and-guidelines.md#11-open-questions)) | S0 §5 |
| OPEN-D2-5 | "Standard normal": family with `special_case_of`, or parameterization | S0 §5 |
| OPEN-D4-4 | Unit of LLM work: unit, paragraph or sentence group ([D4 §12](../design/D4-method-catalog.md#12-open-questions)) | S0 sizes and packet pass; S1 sizes (S3 completes) |
| OPEN-D4-5 | Does rule-based M13 scoping reach annotator scopes? | S0 M13 probe (S5 completes) |
| OPEN-D5-1 | Slots for non-functional formula predicates ([D5 §13](../design/D5-consolidation-identity-confidence.md#13-open-questions)) | S0 §5 |
| OPEN-D3-4 | Stable `meaning_key` | Evidence only (S0 key agreement); decided with D7 |
| OPEN-D8-3 | How blind passes are kept verifiably separate ([D8](../design/D8-agent-and-query-interfaces.md)) | S0 §2 records the method used |
| OPEN-D7-2 | Formula equivalence: simplification versus numeric sampling | Evidence only (which tier decided each S0 comparison); S5 decides |
| OPEN-D9-1 | Python 3.14 wheels ([D9](../design/D9-repository-and-phase0.md)) | Evidence only: the spike environment's resolution (§3.2) |

### Design items S2–S7 settle

| Item | Question (owner) | Settled by |
|---|---|---|
| OPEN-D2-1; OPEN-D2-3, OPEN-D2-6 (confirmation) | `Schema.from_dict` keys (S2's input); D2-3 and D2-6 answered by the schema-rules note on 2026-10-28, confirmed on the pack files (D2 §11) | S4 |
| ADR-0017, ADR-0018 | LinkML compiled to every consumer; policy-routed escalation: accept, amend or supersede | S4 evidence, then the design/target review |
| OPEN-D3-1, OPEN-D3-3, OPEN-D3-4; STMT-01 | BM25 through pg_textsearch on the corpus (D3 §5); keep `kb.segment.text`; stored meaning key; S0 key figures under the revised statement key (D3 §13, D1 §10.1) | S6 |
| ADR-0016 | PostgreSQL as single authority: accept or amend | S6 evidence, then the review |
| KEYS-01; OPEN-D4-3; OPEN-D7-2 | Token keys agree with the tree printer on every parsed value; LaTeX backend and macro map; formula equivalence tiers | S5 |
| OPEN-D4-5, OPEN-D1-2 (confirmation) | M13 scoping beyond the core units | S5 |
| OPEN-D2-2, OPEN-D5-4 | Raw, masked or Unicode math for encoders; mention overlap near math (D2 §11, D5 §13) | S2 |
| D4 candidate method | spaCy candidates scored by GLiNER2 `score_explicit_spans` | S2 variant |
| OPEN-D4-1, OPEN-D4-2, OPEN-D4-4 (M10) | Local model; reasoning on or off; unit of LLM work for the local tier | S3 |
| Output caps | `max_tokens` for M10 and M16 from measured batch sizes; M24's cap in characters (D4 §4.1, D8 §3) | S3 |
| OPEN-D3-2 | Embedding model and dimension, within HNSW `halfvec` limits | S7 |
| PARAM-01, RG-7 | Canonical parameter names across units, as linking cases | S7 |
| OPEN-D6-2 | GPU mode default (co-residency) | joint package G1 (S2, S3, S7) |
| OPEN-D9-1 | Python 3.14 wheels for gliner2 and z3 (pgmpy and splink in phase 2) | E4 |

The time-box of the spike README (ground rule 7) does not apply to S2–S7 either: each runs to its
question's answer at the rigour S0 and S1 had (operator direction for S0/S1, carried forward).

S1 also produces the M01 and M03 rule specifications (D4 §5), including the source profile,
and S0 exercises the evaluation alignment and golden protocol D7 §3 and §5 specify, on real
annotations, before any code depends on them.

## 2. Current state and qualification boundary

- **Exists:** the briefs (S0 and S1 revised by the 2026-10-28 review fold-in) and report template; the corpus under
  `docs/statistics_corpus/` (gitignored); index tables; the design set D0–D5 and the trace.
- **Executed (2026-10-28):** E0, S1-A…G, I-A, I-B, I-R1, S1-R1, S0-A…G, S0-R1 and the evidence
  records (row 22). Results are finalized as records in the evidence folder
  ([records index](../design_review/evidence/2026-10-28_design-spikes/README.md#records)); reports
  [S1](../design_review/evidence/2026-10-28_design-spikes/S1-report.md) and
  [S0](../design_review/evidence/2026-10-28_design-spikes/S0-report.md). Revisit **S0-R2** (operator direction, 2026-10-28): annotator inputs v1 (guideline v1 candidate,
  schema-generated reference, query context, rule warnings), Sonnet and Haiku passes and a Sonnet
  adjudicator over the core units plus six held-out units
  ([S0-R2 report](../design_review/evidence/2026-10-28_design-spikes/S0-R2-report.md)). **X1 done** (2026-10-28,
  operator direction after reviewing the reports): ADR-0011 (Sonnet golden author, annotator inputs v1);
  D2 §10 is guideline v1, D2 §7.3–§7.5, D4 §4.1–§4.2, D7, D8, D0 and the trace amended; S1's HTML rules in D1 §3
  and D4 M01–M03; dispositions in the design-phase findings table. The S0/S1 scope is complete.
- **Executed (2026-10-28):** E5 (`not_run` outcome), E4a (CPU environment; record `e4.env-cpu`),
  I-R2 (token-form keys; S0/S0-R2 figures unchanged; records `*-ir2`, `i-r2.token-form-parity`),
  S4 (records `s4.*`, [S4 report](../design_review/evidence/2026-10-28_design-spikes/S4-report.md)) and
  S6 (records `s6.*`, [S6 report](../design_review/evidence/2026-10-28_design-spikes/S6-report.md)).
  X2 for S4 and S6 done 2026-10-28: the operator accepted both reports; D1–D3, D5, D6, D8 amended,
  ADR-0016/0017/0018 accepted. X2 for S2, S3, S5 and S7 follows their reports.
- **Planned:** E4b (ANTLR, GPU, vLLM environments), C1, I-R3, S5, S2, S3, S7, G1 (rows 23–34).
- **Pre-execution facts established while planning (2026-10-28)**, recorded so execution does
  not rediscover them:
  - A read-only inventory of all 78 first-pass pages (stdlib parser; summarized in
    [S1 §2](design-spikes-s0-s1/S1-ingest-segmentation.md#2-what-the-html-looks-like)) found
    structures the design does not yet address; they are rows HTML-01…HTML-07 in §8.
  - The spike dependency set resolves on Python 3.14 with the exact versions in §4.
  - Probe in a session scratch environment, not evidence (S1 will re-establish each in its
    evidence folder): lxml 6.1.3 links libxml2 2.14.6; cssselect2 0.10.1 matches over an
    `lxml.html` root and agreed with cssselect on `special/Normal.html`; trafilatura 2.3.1 XML
    output kept 247 of the page's 250 `\(` delimiters and the `details` text but also kept
    `div.latex` and the navigation lists; libxml2's `error_log` stays empty for implied
    `<p>` closures, and html5lib reports none either (HTML5 permits them), so parser repair
    must be detected at source level.
- **Qualification boundary.** Spike code is throwaway and is not tested as product code. A spike
  result is evidence for a design decision, labelled per the
  [design principles §D](../design_review/design_principles/core/design-principles.md):
  a library behaviour confirmed by the spike upgrades the specific design claim to
  `Interface-checked`, a measured property to `Measured`, each citing the evidence folder and
  date. Outcomes in reports are `passed`, `failed`, `blocked` (naming the missing prerequisite)
  or `not_run`, each with the command that produced it.

## 3. Shared decisions

### 3.1 The sample

As the spike README defines it: the four spike pages (LocationScale, Normal, LogNormal, Gamma)
for whole-page work, the twelve core units (T1–T4, U5–U12) for quality comparison, and the 78
`first_pass = yes` pages for corpus-wide measurements. Locator notes found while planning:

| Unit | Note |
|---|---|
| T1 | Lead-in paragraph and `dfn1` are separated by `<h4>Definition</h4>`; the unit is the two blocks together |
| T2 | Two Normal paragraphs begin "Suppose … location parameter"; the core unit is the one with "again" |
| U5, U11 | `rel2` on Normal and on Gamma open with identical text; locate by page plus offsets |
| U8, U9 | Units without ids; U9 is a finite n-tuple product (the brief's "indexed family" is a paraphrase) |
| U12 | Gamma `mom1` has four list items and a `details` block |

Unit identity in all results is `(page, rendition key, start, end, content hash)` from
`sample.json`; HTML ids are attributes only (53% of units have none; three ids repeat).

### 3.2 Environment

One uv project in the evidence folder (`pyproject.toml`, `uv.lock`), with its environment at
`$REPO/build/spike-venv` (`UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run …`), Python
3.14.10 (the repository's interpreter since 2026-10-28). Every dependency is pinned exactly at
the latest release when E0 resolves it (operator direction, 2026-10-28); the versions below were
the latest on 2026-10-28 and are replaced by E0's resolved set. The lock diff is inspected when a
dependency is added.

| Purpose | Pins |
|---|---|
| HTML | `lxml==6.1.3`, `html5lib==1.1`, `cssselect==1.6.0`, `cssselect2==0.10.1` (`tinycss2==1.5.1`), `trafilatura==2.3.1` |
| LaTeX | `pylatexenc==3.0b2` (prerelease, chosen by operator direction 2026-10-28 over 2.11 plus an overlay: its configurable `ParsingState` is what makes LaTeX parsing safe on HTML prose; used for span validation, macro tables, V6, M13-probe symbols and sentence variant (d)), `sympy==1.14.0` |
| Sentences | `spacy==3.8.18`, `en_core_web_sm` 3.8.0 and `en_core_web_trf` 3.8.0 wheels by URL, `spacy-curated-transformers==0.3.1`, `torch==2.14.1` (CPU) |
| Sizing | `tokenizers==0.23.3` with the locally cached `Qwen/Qwen3.5-9B` and `fastino/gliner2.5-base-v1` tokenizers (revision hashes recorded) |
| Instruments | `pydantic==2.14.1`, `linkml==1.12.1`, `rapidfuzz==3.14.6`, `scipy==1.18.1`, `statsmodels==0.15.0`, `numpy==2.5.4` |

Reports record `lxml.etree.LIBXML_VERSION`, `LIBXSLT_VERSION`, the spaCy model versions and the
tokenizer revisions, because libxml2 and model revisions change outputs independently of the
Python pins.

### 3.3 Agents

The root agent (Opus 5.5, this session) executes both spikes, owns adjudication, and writes the
reports. Fresh subagents are used only where independence is the point: S0 annotation passes A
and B, the packet-only pass P, the offset-form probe, and the D7 §3.4-style adjudicator session
(whose result is compared with the root's adjudication); the independent second marking of the
sentence-boundary gold sample. Each receives a self-contained input folder and is told what it
must not read; this blindness is instructed, not sandboxed, and the reports say so (the method
is S0's answer to OPEN-D8-3). **Model (operator direction, 2026-10-28):** golden generation and
annotation subagents run on Haiku 5.5 from now on (pass P, the D7 adjudicator session and any
later golden passes); S0 passes A and B, the offset probe and the sentence-gold markers already
ran on Opus 5.5 and stay as they are. Every pass records its model, and reports keep the two
distinct. After S0-R2 the operator chose Sonnet 5.5 as golden author (ADR-0011, 2026-10-28); D0,
D7 and D8 now say so, and golden, annotation and adjudication subagents run on Sonnet. No other delegation is planned;
a bounded library question that arises during execution can go to a `library-research` worker
under its [contract](../../.agents/roles/library-research.md).

### 3.4 Where results go

Everything is written under
`docs/design_review/evidence/2026-10-28_design-spikes/`: code in `code/`, results in
`results/s1/` and `results/s0/`, `sample.json` at the folder root, reports `S1-report.md` and
`S0-report.md` from the template. Results stay small and inspectable (JSON, JSONL, TSV,
Markdown); the corpus is quoted at most a sentence at a time. Each finalized result gets a
record in `records/` (ADR-0010; `just evidence finalize`, `just evidence`), which the README index
and the catalog are generated from; report figures are rendered from the catalog. Design documents are not edited
during execution; design consequences go in each report's "Design implications" section and
reach the design through the closing package (§7, package X1).

### 3.5 Shared decisions for S2–S7

- **The reference.** The v1 reference (`results/s0r2/reference_v1/`, stored form; model-facing
  `reference_model_v1/` with `decisions_v1.json`) is primary; the v0 reference
  (`results/s0/reference/`) is reported beside it where a brief asks. The adjudicator output
  `results/s0r2/adjudication_v1/` covers the held-out units H1–H6 and is their reference.
- **Contested items** are one shared artifact, `results/s0r2/contested.tsv`, built once by package
  C1: the union of the S0 root adjudication's guideline-gap rows and the S0-R2 adjudicator's
  `guideline_gap` decisions, each mapped onto v1-reference local refs (or marked unmappable with the
  reason). S2 and S3 score with and without them.
- **Renditions.** Anything scored against a reference uses the libxml2 renditions the references
  are stored on (`sample.json`, `results/s0r2/sample.json`); html5lib renditions are
  content-identical on those pages (record `s1.rendition-identity`). Corpus-wide runs record their
  parser. A page outside the stored seven is regenerated by `code/s1_adapter.adapt` with the S1
  configuration and its parser recorded, into the consuming spike's results folder (contract R1).
- **Instruments.** S2–S7 score with the instrument revision **I-R2** (row 24), frozen and named in
  each record's `inputs`. A spike that needs an instrument change makes it as a new revision
  package here, never by editing in place. `S0_SAMPLE` and `S0_COMPARE` select the sample and the
  output folder; context-premise items are scored once (D7 §5.1).
- **Single home after a port.** Once the phase 0 build ports a spike module (mathgrammar, the quote
  cascade, the instruments), the product module is its single home; spikes keep scoring against
  the frozen I-R2 revision. S5-A runs before phase 0 ports the grammar.
- **Inputs v1 are frozen** for S3, so its passes stay comparable with SV and HV; S4 regenerates the
  reference and diffs it against `results/s0r2/inputs/packet_v1/reference.md`, without replacing it.
- **Environments.** One environment per need, each with its `results/environment*.json` from
  `code/e0_environment.py`:

  | Environment | For | Contents |
  |---|---|---|
  | `build/spike-venv` (CPU) | S4, S5, S6, the instruments | the S0/S1 set plus `rule-engine==5.1.0`, an explicit `jsonschema` pin, `z3-solver==5.3.2.0`, `psycopg[binary]==3.3.6`, `pgvector==0.5.1` |
  | `build/spike-gpu-venv` | S2, S7 | CUDA torch, `gliner2[local]==2.1.0`, transformers, an exact `sentence-transformers` pin; the spaCy work of S2 and S7 runs in the CPU environment |
  | `build/spike-vllm-venv` | S3, S4's structured-output check, S7 pooling if chosen | a copy of `services/vllm-native/` from corpus-intelligence (vLLM 0.31, torch 2.13) with its own lock |
  | `build/spike-antlr-venv` | S5's ANTLR comparison only | SymPy 1.14 and `antlr4-python3-runtime` 4.11, without linkml (which pins antlr4 below 4.11) |

- **GPU.** One RTX 5090 (32 GB). Joint package G1 measures co-residency for OPEN-D6-2 across S3's
  server, S2's GLiNER2 and S7's embedder; individual spikes run exclusively until then.
- **Labelling independence.** Annotation, adjudication and hand-labelling (S2 error grouping, S5's
  M13 judgments, S7's unmatched mentions and retrieval relevance) are done by fresh Sonnet
  subagents with instructed blindness and transcript audit, not by the root, which wrote the
  reference.
- **Results and records.** Each spike writes `results/s<n>/`, finalizes records whose `consumed_by`
  names the phase 0 or phase 1 package and OPEN item each result feeds, adds its views to
  `catalog.sql`, and renders its report from a `.j2` template.

## 4. Contracts between the documents

These are the interfaces the supporting documents rely on. Each producer owns its format; a
change is announced to its consumers here.

| Artifact | Producer | Consumers | Content |
|---|---|---|---|
| `results/s1/canonical/<page>.txt` | S1-A | S0, instruments, S2/S3 | Canonical text of the adopted rendition |
| `results/s1/segments/<page>.jsonl` | S1-A | S0, instruments | One segment per line: `key`, `kind`, `start`, `end`, `parent`, `attrs` (element id, classes, `dfn` terms with offsets, link targets, `sourceline`, matched profile rule), `parse_status` with reason |
| `results/s1/renditions.json` | S1-A | all | Per page: rendition key, document key, adapter config (and its hash), rendering conventions chosen, page macro table, parser and libxml2 version |
| `results/s1/sentences/<page>.<variant>.jsonl` | S1-C | S0 (adopted variant), M13 probe | Sentence segments with keys and offsets |
| `sample.json` | S1-B | S0, S2, S3 | Per core unit: page, rendition key, segment keys (D1 §10.1), `start`, `end`, content hash, sentence ids of the adopted variant, first 80 characters |
| Batch model and validators | Instruments | S0, later S2/S3 | `ClaimProposalBatch` in model-facing (quote) and stored (offset) forms |
| Quote locator, aligner, agreement | Instruments | S0, later S2/S3 | See [comparison instruments](design-spikes-s0-s1/comparison-instruments.md) |
| `results/s0/reference/<unit>.json` | S0-D | S2, S3, D7 later | Adjudicated batches in stored form, with decision reasons and the rendition key |
| `results/s0r2/reference_v1/`, `reference_model_v1/` | S0-R2 | S2, S3, S5, S6, S7; phase 0 fixtures | The v1 reference (primary from S2 on) |
| `results/s0r2/sample.json`, `inputs/packet_v1/` | S0-R2 | S3, S4 | 21 units with query-assembled context; annotator inputs v1 (frozen) |
| `results/s0r2/contested.tsv` | C1 | S2, S3 | Contested items mapped onto v1 local refs |
| Instrument revision I-R2 | I-R2 | S2, S3, S5, S6, S7 | Token-form keys (ADR-0012) and sizing commands; the frozen scoring revision |
| `results/s4/compiled/` | S4 | S2, S3, S6 | GLiNER2 dicts, both JSON Schema forms, rules, the generated reference, schema-table rows |
| `results/s2/mentions/<page>.jsonl` | S2-D | S7 | GLiNER2 mentions over the four spike pages from S2's adopted configuration: offsets in the libxml2 renditions, class, score, configuration hash; one file per page |
| `results/s4/compiled/` decoding form | S4-D | S3 | The structured-output schema by D2 §7.3's rules, with its xgrammar compile result |
| `results/s3/replay/` | S3 | phase 1 tests (M10, M16) | Recorded exchanges for deterministic replay |
| `results/s7/segments/` (78 pages, R1) | S7 | S5 (optional) | Regenerated segments with the parser recorded |

**Rendition drift.** S1 decides the rendering conventions and section synthesis on the four
spike pages before the S0 packets are built (S1-A). If S1 later changes a convention that
alters canonical text, the rendition key changes, the instruments' re-anchoring step maps S0
batches onto the new rendition by quote, and anything that fails to re-anchor is listed in both
reports. Annotation is not redone for a rendering change.

## 5. Execution queue

Packages run when their inputs exist; the order below is the intended route, not a barrier per
row. "Needs" names the input a package consumes, not merely an earlier row.

| # | Package | Document | Needs | Produces |
|---|---|---|---|---|
| 1 | E0 Environment and pins | this plan §3.2 | — | uv project, lock, version record |
| 2 | S1-A Adapter on the four pages | S1 | E0 | canonical texts, segments, renditions, conventions, profile rules, variants 1–4 |
| 3 | I-A Batch contract, validators, locator | Instruments | E0; S1-A canonical text for locator tests | batch models, schema lookup, locator with tests |
| 4 | S1-B `sample.json`, invariants, determinism | S1 | S1-A | `sample.json`, `invariants.json`, provisional sentences (spaCy `sm` parser + math merge) |
| 5 | S0-A Blind packets (D7 §3.2 golden mode) | S0 | S1-B, I-A | input folders for passes A, B |
| 6 | S0-B Passes A and B, stored-form conversion, offset probe | S0 | S0-A | `pass_a/`, `pass_b/`, `stored/`, `offset_probe/` |
| 7 | S1-C Sentence gold and variant matrix | S1 | S1-B | `sentence_gold.jsonl`, `sentences.tsv`, adopted M03 variant |
| 8 | S1-D 78-page run | S1 | S1-A rules | counts, parser diff, coverage, markup, macro tables, sizes |
| 9 | I-B Aligner, agreement, keys | Instruments | I-A; pass outputs for real data (built on T1–T4 trace data first) | aligner with verification record |
| 10 | S0-C Trace and witness comparison | S0 | S0-B, I-B | `trace_diff.md`, `witness_diff.md` |
| 11 | S0-D Agreement, root adjudication, D7 adjudicator session | S0 | S0-B, I-B | `agreement.tsv`, `reference/`, `adjudication_d7/` |
| 12 | S0-E Packet-only pass P and M13 probe | S0 | S0-D, S1-C adopted variant | `pass_p/` scores, `m13_probe.tsv` |
| 13 | S1-E trafilatura baseline | S1 | S1-D | `baseline_trafilatura.tsv` |
| 14 | S1-F NIST generality probe | S1 | S1-A | `nist_probe.md` |
| 15 | S0-F Gaps, OPEN answers, sizes, report | S0 | S0-C…E | `gaps.md`, `size.tsv`, `S0-report.md` |
| 16 | S1-G Report | S1 | S1-A…F | `S1-report.md` with M01/M03 specifications |
| 17 | X1 Closing package (with design-phase Q5) | this plan §7 | both reports reviewed by the operator | design updates, dispositions, STATUS |
| 18 | I-R1 Instruments revisit: one math grammar (ADR-0009), slot-type validation, quote cascade | Instruments §3, §4 | I-B; `lark_probe`, `regex_probe` | `code/mathgrammar/`, grammar coverage record, revised locator and value tiers, tests |
| 19 | S1-R1 Profile-driven math delimiting (ADR-0009) | S1 §3.1 | S1-D | delimiter pattern generated from the profile; S1-D checks rerun unchanged |
| 20 | S0-R1 M13 revisit: binders as spaCy patterns, symbols from the grammar | S0 §6 | I-R1 symbol API; S0-D reference | `m13_probe.*.tsv` with the amended rules |
| 21 | S0-G Rerun of every S0 comparison on the revised instruments; passes H and D7 scored | S0 §4 | I-R1 | `compare/`, revised figures for S0-F |
| 22 | E1–E3 Evidence records, catalog and generated reports (ADR-0010) | this plan §3.4 | — | `tools/evidence/`, `records/`, generated indexes, `build/evidence.duckdb` |
| 22a | S1-R2 html5lib rerun and rendition identity (executed 2026-10-28) | S1 | S1-D | `results/s1_html5lib/`; records `s1.corpus-html5lib`, `s1.rendition-identity` |
| 22b | S0-R2 Annotator inputs v1 revisit (executed 2026-10-28) | S0, [S0-R2 report](../design_review/evidence/2026-10-28_design-spikes/S0-R2-report.md) | S0-G | `results/s0r2/`; records `s0r2.*` |
| 23 | E4 Environments for S2–S7: **E4a** the CPU environment now (with gliner2 on CPU torch for the wheel evidence); **E4b** the ANTLR, GPU and vLLM environments when S5, S2, S3 and S7 start (operator, 2026-10-28) | §3.5 | — | the environments with their records; OPEN-D9-1 evidence for gliner2 and z3 |
| 24 | I-R2 Instruments revision: token-form keys (ADR-0012), sizing commands, frozen revision | Instruments | E4 (CPU) | revised `mathgrammar` and `instruments/values`; S0-G and S0-R2 figures rerun, superseding records (nothing removed) |
| 24b | I-R3 Mention-level alignment for S2 and S7 (I-R2 plus one module, checked by hand on T1–T4); kept apart from I-R2 so S5 and S6-F, on phase 0's path, do not wait on it | Instruments, S2 §1 | I-R2 | the alignment module and its hand check |
| 25 | E5 `not_run` outcome in evidence records | §3.5 | — | `tools/evidence` model and test |
| 26 | C1 Contested items mapped onto the v1 reference | §3.5 | — | `results/s0r2/contested.tsv` |
| 27 | S4-A…S4-E | S4 | E4 | see S4; unblocks phase 0 schema-and-rules |
| 28 | S6-A…S6-G (S6-D loads S4-B's compiled rows) | S6 | E4, I-R2 for S6-F, S4-B for S6-D, pg_textsearch preloaded and created in `cs_spike_s6` by the operator | see S6; unblocks phase 0 foundations (store) |
| 29 | S5-A…S5-E | S5 | E4, I-R2 | see S5; S5-A unblocks phase 0 ingest-and-math (grammar port) |
| 30 | S2-A…S2-D | S2 | E4 (GPU), I-R2, I-R3 (S2-C), C1, S4-D optional | see S2 |
| 31 | S3-A…S3-F | S3 | E4 (vLLM, the RTX 5090 support of its wheel confirmed), I-R2, C1, S4-D's decoding form optional; disk for any larger model download | see S3 |
| 32 | S7-A…S7-D | S7 | S7-A: E4 (GPU) only, so it can precede S2; S7-B and S7-C: S2-D's page mentions and I-R3 | see S7 |
| 33 | G1 GPU co-residency (OPEN-D6-2) | §3.5 | S2-B, S3-A, S7-A | co-residency measurement and recommendation |
| 34 | X2 Closing package for S2–S7 | §7 | each report reviewed by the operator | design updates, dispositions, STATUS |

Rows 23 onward (2026-10-28) are ordered by what phase 0 needs first: S4 and S6 are on its critical
path (schema compilers and migration 0001), S5-A precedes its grammar port; S2, S3 and S7 feed
phase 1. Rows 23–26 are shared prerequisites. Each spike's packages are developed in its supporting
document.

Row 22 (2026-10-28, operator direction) precedes S0-G: S0-G's results are the first finalized
through records, and the S0 report's figures are rendered from the catalog.

Rows 18–21 were added 2026-10-28 after the operator approved the parsing recommendation
(ADR-0009: one math grammar, source facts as profile data, offset-preserving quote location,
spaCy patterns for prose constructs). S0-F waits for row 21 so the report's figures come from
the revised instruments.

Rows 6, 7 and 8 proceed in parallel; S0's annotation does not wait for the sentence gold,
because quotes are located in the unit when a cited sentence id is wrong (D4 §4.3), and the
packets record which sentence variant they used. Row 14 is the lowest priority and never
blocks S0.

## 6. Completion conditions

The spikes are complete when:

1. `S1-report.md` and `S0-report.md` exist in the template's form, every outcome labelled with
   its command and date.
2. Every data file named in both briefs exists, plus the extension files each supporting
   document lists, or its absence is reported as `blocked`/`not_run` with the reason.
3. Every scheduled item in §1 has an answer citing the units, spans or measurements that decide
   it, or is explicitly left open with the evidence still needed and the spike that will
   supply it.
4. The S0 reference batches pass the batch validators and invariant checks, and record their
   rendition key.
5. Each report's "Design implications" table ties every proposed change to an item in §1 or a
   row in §8.

The closing package X1 is separate: it follows the operator's review of the reports.

For S2–S7 (rows 23 onward) the spikes are complete when: each report exists in the template's
form with its figures rendered from the catalog and every outcome labelled with its command
(`passed`, `failed`, `blocked`, `not_run`); every data file its brief and supporting document
names exists or is reported `blocked`/`not_run` with the reason; every item in §1's S2–S7 table
has an answer citing its evidence record or is left open with the evidence still needed; every
record's `consumed_by` names the phase 0 or phase 1 package and OPEN item it feeds; and the
proposed ADRs ADR-0016, ADR-0017 and ADR-0018 have the evidence their acceptance waits for. The
closing package X2 (row 34) folds the results in after the operator's review, as X1 did.

## 7. Closing package X1 (gated on the operator's review)

Operator decision (2026-10-28): the plan includes folding results into the design, after the
operator has reviewed both reports. The design-phase plan's Q5 covers the same fold-in for S0
and S1 (with S4, S6 and the library pass); the fold-in is done once, under whichever session
the operator directs, and recorded in both plans' findings tables. X1 then:

- updates D1 (§3 canonical text and segments; §4–§8 where S0 shows a representation gap), D2
  (§9 schema v0, §10 guideline v0), D4 (M01, M02, M03 cards, packet caps if S0/S1 sizes require)
  and `trace.md` (corrections classified "the trace is wrong" in S0-C), each with the evidence
  path and the claim label it now earns;
- records each item's disposition in §8 with its closure evidence, closing rows whose answer is
  accepted and carrying open ones forward with their next trigger;
- writes an ADR only where a real alternative was chosen and a future session would otherwise
  be surprised (for example the M01 parser or the source-profile language);
- updates the spike README's status lines and runs the `handoff` skill.

Implications the operator rejects stay in the report with the reason and do not reach the design.

## 8. Findings disposition

The design-phase plan holds the rows for every `OPEN-Dn-k` item and governs their disposition.
The rows below for S0 and S1 mirrored it while those spikes ran. From S2 on this table records
only spike-execution findings (instrument, environment and procedure defects) and the evidence
each spike adds; OPEN dispositions are recorded in the design-phase table alone, linked from the
spike's report and records. Rows HTML-01…HTML-07 come from the pre-execution HTML
inventory (2026-10-28) and are scheduled into S1.

| Item | Component | Consequence and intended correction | Disposition · dependency | Closure check |
|---|---|---|---|---|
| OPEN-D1-1 | D1 §3, D4 M03 | Sentence splitting may break inside or around math; adopt the variant with the best boundary F1 on the gold | answered · [S1 report](../design_review/evidence/2026-10-28_design-spikes/S1-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | Variant matrix on the gold sample; adopted variant named in S1 report |
| OPEN-D1-2 | D1 §5.2, D4 M13 | Variable scope may need `section` extent | answered · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | Reference scopes with deciding spans; M13 probe comparison |
| OPEN-D1-3 | D1 §4, D2 §10.4 | Parameter identity by role or symbol | answered · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | Annotator agreement on parameter entities; deciding units |
| OPEN-D1-4 | D1 §5.2 | Extent for page-level standing assumptions | answered · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | Reference treatment of T1's lead-in; both section syntheses |
| OPEN-D2-4 | D2 §9 | Property predicates versus `has_property` | answered · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | Count of distinct properties used and of `unsupported` property items |
| OPEN-D2-5 | D2 §9, §10.4 | Representation of standardized families | answered · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | A/B treatment of "standard normal"/"standard gamma"; adjudication reason |
| OPEN-D4-4 | D4 §4.1, M10 | Unit of LLM work | answered · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | Size distributions in tokens; packet-pass loss |
| OPEN-D4-5 | D4 M13 | Rule scoping versus annotator scopes | see design-phase plan | `m13_probe.tsv` agreement by binding kind |
| OPEN-D5-1 | D5 §5.4 | Slots for non-functional formula predicates | not exercised by S0 (no unit states one formula predicate twice for a subject); open · phase 1 (design-phase plan governs) | Reference cases with two formula claims of one predicate in one statement |
| OPEN-D3-4 | D3, D5 §5.5 | Whether a stored meaning key is needed | S0 evidence recorded (meaning keys more stable); open · S6 decides (design-phase plan governs) | Key and meaning-key agreement figures |
| OPEN-D8-3 | D8 §2.2 | Blind passes must be verifiably separate | answered · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | S0 report describes the setup, the opened-file records and any rerun |
| OPEN-D7-2 | D7 §5.3 | Formula equivalence procedure | see design-phase plan | Tier counts in the S0 report |
| OPEN-D9-1 | D9 §2 | Python 3.14 wheels | see design-phase plan | Resolution recorded in both reports (all spike pins resolved on 3.14, 2026-10-28) |
| HTML-01 | D1 §3.1, M01 | 106 bare `\begin{align}` blocks without `\[` are display math the rules do not name | answered · [S1 report](../design_review/evidence/2026-10-28_design-spikes/S1-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | Rule stated; counts over 78 pages |
| HTML-02 | D1 §3.1, M01, M09 | 11 unbalanced math delimiters; no rule for resynchronization or `parse_status` | answered · [S1 report](../design_review/evidence/2026-10-28_design-spikes/S1-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | Behaviour per occurrence under both math detectors |
| HTML-03 | D1 §3.1, M01 | Rendered-text conventions absent from the source (1,200 empty JS-filled `a.ref` links, `<q>`, list markers, `details` summaries) | answered · [S1 report](../design_review/evidence/2026-10-28_design-spikes/S1-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | Convention chosen per case with sentence and quote-location evidence |
| HTML-04 | D1 §3.2, M01, M13 | `section` is not an HTML element in Siegrist; it must be synthesized from `h3`/`h4` | answered · [S1 report](../design_review/evidence/2026-10-28_design-spikes/S1-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | Adopted synthesis; scope analysis under both |
| HTML-05 | M01 | ~26 misnested or unclosed `<p>` repaired differently by parsers; parser error logs do not report them | answered · [S1 report](../design_review/evidence/2026-10-28_design-spikes/S1-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | Parser diff and source-level repair inventory |
| HTML-06 | M01, M09, M11 | `div.latex` macro definitions: per-source map or per-rendition attribute | answered · [S1 report](../design_review/evidence/2026-10-28_design-spikes/S1-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | Macro tables compared across 78 pages |
| HTML-07 | D4 M01 | Source-profile language (CSS rules with roles) and a fallback for unprofiled HTML | answered · [S1 report](../design_review/evidence/2026-10-28_design-spikes/S1-report.md) (2026-10-28); disposed in X1 (2026-10-28): see the design-phase findings table | Rule-engine agreement, coverage inventory, trafilatura and NIST evidence |
| PARSE-01 | D1 §6.2, D4 §4.3, M01, M09, M11, M13 | Math read four ways by string code (scanner, pylatexenc walker, SymPy rewrite shim, regex expression test); review findings F2/F3/F5a; fixed-width fuzzy quote windows cut words; source facts in adapter code | implemented in the spike instruments · ADR-0009; I-R1, S1-R1, S0-R1 done 2026-10-28 (records s0.instruments, s1.profile-delimiting, s0.m13-probe-2); production realization with D4's methods | `code/mathgrammar/` coverage record; F2/F3/F5a regression tests on the grammar; locator cascade reproduces `regex_probe` figures; S1-D checks unchanged under the profile-generated delimiter pattern |
| OPEN-D2-1 | D2 §7.2 | `Schema.from_dict` keys in gliner2 | see design-phase plan | — |
| OPEN-D2-2 | D2 §7.2, M06/M07 | Raw or masked math for GLiNER2 | deferred · S2 (S1 supplies math token cost) | — |
| OPEN-D2-3 | D2 §7.4 | rule-engine syntax | see design-phase plan | — |
| OPEN-D2-6 | D2 §3 | List annotation round-trip in `SchemaView` | see design-phase plan | — |
| OPEN-D3-1 | D3 | pg_textsearch BM25 on the corpus | deferred · S6 | — |
| OPEN-D3-2 | D3, M04 | Embedding model and dimension | deferred · S7 | — |
| OPEN-D3-3 | D3 | Storing `kb.segment.text` | see design-phase plan | — |
| OPEN-D4-1 | D4 M10 | Local model choice | deferred · S3 | — |
| OPEN-D4-2 | D4 M10 | Reasoning on or off | deferred · S3 | — |
| OPEN-D4-3 | D4 M11 | SymPy LaTeX backend and macro map | deferred · S5 (S1 supplies macro tables) | — |
| OPEN-D5-2 | D5 §6.4 | Latent-truth model minimums | deferred · phase 2 calibration | — |
| OPEN-D5-3 | D5 §5.4 | Auto-resolution margin | deferred · phase 2 | — |
| OPEN-D5-4 | D5 §3.1 | Mention-cluster overlap rule near math | deferred · S2 | — |
| OPEN-D6-1, OPEN-D6-3 | D6 | Barriers versus dataflow; budget defaults | deferred · phase 2 / phase 0 practice | — |
| OPEN-D6-2 | D6 §5 | GPU mode default | deferred · S3, S7 | — |
| OPEN-D7-1, OPEN-D7-3, OPEN-D7-4 | D7 | Golden set sizes; split granularity; PPI implementation | deferred · phases 1–2 | — |
| OPEN-D8-1, OPEN-D8-2, OPEN-D9-2 | D8, D9 | Process layout; packet grouping | see design-phase plan | — |

### Deferred, each with a trigger

| Item | Trigger |
|---|---|
| extruct (embedded structured metadata) | A corpus whose pages carry JSON-LD, Microdata, RDFa, Open Graph or Dublin Core; the 78 Siegrist pages carry none (checked 2026-10-28) |
| Parsel | A source whose content sits in script-embedded JSON, where Parsel's CSS → JSON → JMESPath chaining replaces code |
| A formal agreement statistic beyond counts and Cohen's kappa (e.g. Krippendorff's α) | More than two annotators or a golden set large enough for it to be informative (D7) |

## 9. Risks

| Risk | Effect | Handling |
|---|---|---|
| Both annotators are the same model | Agreement can reflect shared bias, not correctness | Independent witnesses: pass-versus-trace before adjudication, the old repository's settled expectations, the M13 rule probe; reported as such |
| Blindness is instructed, not enforced | A pass could read the trace | Inputs are self-contained folders; each pass reports the files it opened; a pass that read a forbidden file is discarded and rerun |
| Twelve units is a small sample | Rates have wide uncertainty | Counts with denominators lead; Wilson intervals and kappa are secondary and given with n |
| Rendering decisions change after S0 starts | Batches point at old offsets | Rendition keys, re-anchoring by quote (§4) |
| libxml2 or model revisions differ between machines | Outputs differ silently | Versions recorded in every report |
| The corpus is gitignored | Results could leak large source text | Results hold offsets and keys; quotes at most a sentence |
| Phase 0 ports a module while a spike still changes it | Two live copies diverge | §3.5 single home after a port; spikes score against the frozen I-R2 revision |
| I-R2 changes key and tier-1 figures already reported | Earlier numbers silently disagree with later ones | I-R2 reruns S0-G and S0-R2 and supersedes their records; reports cite the revision |
| GPU work collides on one card | Out-of-memory or skewed timings | Exclusive runs until G1 measures co-residency |
| The reference was written by the same design process (and model family) | Agreement can reflect shared habits | v1 reference plus the H1–H6 held-out units; pass against pass reported beside pass against reference (D7 §5.4) |

## 10. Standing conventions

- Commands: `UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/<script>.py`
  from the evidence folder; each report's "What was run" table lists them.
- No product code: nothing under `crates/`, `python/` or `domains/`.
- The root runs `just turn-end` at the end of a turn that changed files.
- Commits are small, name the package (`S1-A`, `S0-B`, …) and state the outcome of what was run.

## 11. How the series grows

The series is the long-lived plan for all design spikes (operator direction, 2026-10-28), so
that later spikes and revisits share one set of contracts, environment and finding rows instead
of each starting a new plan.

- **A new spike** joins as a supporting document in `design-spikes-s0-s1/` (the folder and file
  names stay, because other plans link to them), with packages named after it (`S2-A`, …), rows
  in §5's queue and §8's findings table, and its own contracts added to §4.
- **A revisit** of a finished spike (a new question, a design change, a corrected premise) is a
  package with a revisit id (`S1-R1`, …) in the original spike's document, stating its trigger and
  which earlier results it supersedes. Earlier results stay in the evidence folder; the report
  gains a dated section rather than being rewritten.
- **Comparability across revisions** rests on what every result already records: rendition keys
  and adapter configuration hashes (S1), batch envelopes with rendition keys (S0 and the
  instruments), and `results/environment.json` per environment change. A result is compared with
  an earlier one only when these identify what changed.
- **Environment changes** (a library or interpreter upgrade) are a package of their own: the new
  `environment.json` is written, and the results it could affect are listed for re-running or
  marked as produced under the earlier environment.

