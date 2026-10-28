# Design spikes: execution plan series (S0 and S1 first)

**Status:** Active, alongside [design-phase_2026-10-28](design-phase_2026-10-28.md) by operator
decision (2026-10-28); this plan executes that plan's queue items Q1 (S1) and Q2 (S0) and governs
their procedure. **Revised:** 2026-10-28.
**Label:** Proposed (nothing in this plan has been executed).

This coordinator owns the combined scope, shared decisions, cross-document contracts, the
execution queue, finding disposition and completion conditions for the design spikes. It
starts with S0 and S1 and is meant to grow (§11): later spikes and revisits of earlier ones join
the same series. Three supporting documents develop the current work:

| Document | Owns |
|---|---|
| [S1 ingest and segmentation](design-spikes-s0-s1/S1-ingest-segmentation.md) | HTML library selection, the throwaway M01/M03 adapter, its variants and measurements, `sample.json` |
| [S0 reference annotations](design-spikes-s0-s1/S0-reference-annotations.md) | Blind annotation protocol, adjudication into the S0 reference, determinacy and gap analyses, OPEN answers |
| [Comparison instruments](design-spikes-s0-s1/comparison-instruments.md) | Batch contract and validators, quote locator, aligner, agreement tiers and keys; reused by S2/S3 |

The briefs remain the statement of each spike's question:
[S1 brief](../design_review/evidence/2026-10-28_design-spikes/S1-ingest-and-segmentation.md),
[S0 brief](../design_review/evidence/2026-10-28_design-spikes/S0-reference-annotations.md),
[spike README](../design_review/evidence/2026-10-28_design-spikes/README.md). This plan extends
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

S1 also produces the M01 and M03 rule specifications (D4 §5), including the source profile,
and S0 exercises the evaluation alignment and golden protocol D7 §3 and §5 specify, on real
annotations, before any code depends on them.

## 2. Current state and qualification boundary

- **Exists:** the briefs (S0 and S1 revised by the 2026-10-28 review fold-in) and report template; the corpus under
  `docs/statistics_corpus/` (gitignored); index tables; the design set D0–D5 and the trace.
- **Not yet started:** spike environment, code, results, reports.
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
| LaTeX | `pylatexenc==2.11` (stable; span validation, macro tables, M13-probe symbols, sentence variant (d)), `sympy==1.14.0`; `pylatexenc==3.0b2` only in an isolated overlay for S1 variant V6 (`uv run --no-project --with pylatexenc==3.0b2 …`) |
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
is S0's answer to OPEN-D8-3). No other delegation is planned;
a bounded library question that arises during execution can go to a `library-research` worker
under its [contract](../../.agents/roles/library-research.md).

### 3.4 Where results go

Everything is written under
`docs/design_review/evidence/2026-10-28_design-spikes/`: code in `code/`, results in
`results/s1/` and `results/s0/`, `sample.json` at the folder root, reports `S1-report.md` and
`S0-report.md` from the template. Results stay small and inspectable (JSON, JSONL, TSV,
Markdown); the corpus is quoted at most a sentence at a time. Design documents are not edited
during execution; design consequences go in each report's "Design implications" section and
reach the design through the closing package (§7, package X1).

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

The design-phase plan holds the design owner's rows for every `OPEN-Dn-k` item; the rows here
mirror its dispositions for the items this plan executes or informs, so the spike lane has one
place to record evidence. Where the two differ, the design-phase plan's disposition governs. Rows HTML-01…HTML-07 come from the pre-execution HTML
inventory (2026-10-28) and are scheduled into S1.

| Item | Component | Consequence and intended correction | Disposition · dependency | Closure check |
|---|---|---|---|---|
| OPEN-D1-1 | D1 §3, D4 M03 | Sentence splitting may break inside or around math; adopt the variant with the best boundary F1 on the gold | open · S1-C | Variant matrix on the gold sample; adopted variant named in S1 report |
| OPEN-D1-2 | D1 §5.2, D4 M13 | Variable scope may need `section` extent | open · S0-D, S0-E | Reference scopes with deciding spans; M13 probe comparison |
| OPEN-D1-3 | D1 §4, D2 §10.4 | Parameter identity by role or symbol | open · S0-D | Annotator agreement on parameter entities; deciding units |
| OPEN-D1-4 | D1 §5.2 | Extent for page-level standing assumptions | open · S0-D | Reference treatment of T1's lead-in; both section syntheses |
| OPEN-D2-4 | D2 §9 | Property predicates versus `has_property` | open · S0-F | Count of distinct properties used and of `unsupported` property items |
| OPEN-D2-5 | D2 §9, §10.4 | Representation of standardized families | open · S0-D | A/B treatment of "standard normal"/"standard gamma"; adjudication reason |
| OPEN-D4-4 | D4 §4.1, M10 | Unit of LLM work | open · S0-E, S0-F, S1-D; S3 completes | Size distributions in tokens; packet-pass loss |
| OPEN-D4-5 | D4 M13 | Rule scoping versus annotator scopes | open · S0-E; S5 completes | `m13_probe.tsv` agreement by binding kind |
| OPEN-D5-1 | D5 §5.4 | Slots for non-functional formula predicates | open · S0-D | Reference cases with two formula claims of one predicate in one statement |
| OPEN-D3-4 | D3, D5 §5.5 | Whether a stored meaning key is needed | evidence · S0-D; decided with D7 | Key and meaning-key agreement figures |
| OPEN-D8-3 | D8 §2.2 | Blind passes must be verifiably separate | open · S0-A, S0-B | S0 report describes the setup, the opened-file records and any rerun |
| OPEN-D7-2 | D7 §5.3 | Formula equivalence procedure | evidence · S0-D (deciding tier per comparison); S5 decides | Tier counts in the S0 report |
| OPEN-D9-1 | D9 §2 | Python 3.14 wheels | evidence · E0 | Resolution recorded in both reports (all spike pins resolved on 3.14, 2026-10-28) |
| HTML-01 | D1 §3.1, M01 | 106 bare `\begin{align}` blocks without `\[` are display math the rules do not name | open · S1-A, S1-D | Rule stated; counts over 78 pages |
| HTML-02 | D1 §3.1, M01, M09 | 11 unbalanced math delimiters; no rule for resynchronization or `parse_status` | open · S1-A, S1-D | Behaviour per occurrence under both math detectors |
| HTML-03 | D1 §3.1, M01 | Rendered-text conventions absent from the source (1,200 empty JS-filled `a.ref` links, `<q>`, list markers, `details` summaries) | open · S1-A | Convention chosen per case with sentence and quote-location evidence |
| HTML-04 | D1 §3.2, M01, M13 | `section` is not an HTML element in Siegrist; it must be synthesized from `h3`/`h4` | open · S1-A, S0-E | Adopted synthesis; scope analysis under both |
| HTML-05 | M01 | ~26 misnested or unclosed `<p>` repaired differently by parsers; parser error logs do not report them | open · S1-A, S1-D | Parser diff and source-level repair inventory |
| HTML-06 | M01, M09, M11 | `div.latex` macro definitions: per-source map or per-rendition attribute | open · S1-D | Macro tables compared across 78 pages |
| HTML-07 | D4 M01 | Source-profile language (CSS rules with roles) and a fallback for unprofiled HTML | open · S1-A, S1-E, S1-F | Rule-engine agreement, coverage inventory, trafilatura and NIST evidence |
| OPEN-D2-1 | D2 §7.2 | `Schema.from_dict` keys in gliner2 | deferred · S4 | — |
| OPEN-D2-2 | D2 §7.2, M06/M07 | Raw or masked math for GLiNER2 | deferred · S2 (S1 supplies math token cost) | — |
| OPEN-D2-3 | D2 §7.4 | rule-engine syntax | deferred · S4 | — |
| OPEN-D2-6 | D2 §3 | List annotation round-trip in `SchemaView` | deferred · S4 (S0's schema load is a byproduct observation) | — |
| OPEN-D3-1 | D3 | pg_textsearch syntax | deferred · S6 | — |
| OPEN-D3-2 | D3, M04 | Embedding model and dimension | deferred · S7 | — |
| OPEN-D3-3 | D3 | Storing `kb.segment.text` | deferred · S6 | — |
| OPEN-D4-1 | D4 M10 | Local model choice | deferred · S3 | — |
| OPEN-D4-2 | D4 M10 | Reasoning on or off | deferred · S3 | — |
| OPEN-D4-3 | D4 M11 | SymPy LaTeX backend and macro map | deferred · S5 (S1 supplies macro tables) | — |
| OPEN-D5-2 | D5 §6.4 | Latent-truth model minimums | deferred · phase 2 calibration | — |
| OPEN-D5-3 | D5 §5.4 | Auto-resolution margin | deferred · phase 2 | — |
| OPEN-D5-4 | D5 §3.1 | Mention-cluster overlap rule near math | deferred · S2 | — |
| OPEN-D6-1, OPEN-D6-3 | D6 | Barriers versus dataflow; budget defaults | deferred · phase 2 / phase 0 practice | — |
| OPEN-D6-2 | D6 §5 | GPU mode default | deferred · S3, S7 | — |
| OPEN-D7-1, OPEN-D7-3, OPEN-D7-4 | D7 | Golden set sizes; split granularity; PPI implementation | deferred · phases 1–2 | — |
| OPEN-D8-1, OPEN-D8-2, OPEN-D9-2 | D8, D9 | Process layout; packet grouping | deferred · phase 0 build | — |

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

