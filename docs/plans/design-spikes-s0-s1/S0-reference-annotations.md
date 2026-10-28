# S0 · Reference annotations: plan

**Proposed (2026-10-28).** Part of the [S0/S1 plan series](../design-spikes-s0-s1_2026-10-28.md),
which owns shared decisions, the execution queue and finding disposition. The question is the
[S0 brief](../../design_review/evidence/2026-10-28_design-spikes/S0-reference-annotations.md)'s;
this document extends its scope and specifies how to answer it. Alignment, validation and
agreement are computed by the [comparison instruments](comparison-instruments.md).

## 1. What S0 must establish

1. **Expressiveness.** Whether D1 §1–§11 with the statistics schema v0 and guideline v0
   (D2 §9–§10) can state what the twelve core units say, and where they cannot: schema gaps,
   guideline gaps and representation gaps.
2. **Determinacy.** Whether two independent annotators following the guideline produce the same
   claims, at the core, full and evidence tiers, and where they diverge.
3. **The reference.** One adjudicated batch per unit, with a reason for every decision, which S2
   and S3 are scored against. These are spike references, not goldens; goldens follow D7.
4. **Answers** to the brief's OPEN-D1-2, OPEN-D1-3, OPEN-D1-4, OPEN-D2-4, OPEN-D2-5, OPEN-D5-1
   and OPEN-D8-3, plus OPEN-D4-4 and OPEN-D4-5 and evidence for OPEN-D3-4 and OPEN-D7-2, each
   tied to the units and spans that decide it.

S0 runs the golden protocol of [D7 §3](../../design/D7-evaluation-goldens-outer-loop.md#3-golden-authoring-protocol)
as closely as a spike without the D8 tools can, so its results also test that protocol: golden-mode
packets, blind passes A and B, alignment by D7 §5. It departs from D7 in one place, as the brief
requires: the root adjudicates. A D7-style fresh adjudicator session runs as well, and the two
adjudications are compared (§4.4).

Beyond the brief, S0 tests four design premises that its material can test cheaply: that
models citing evidence by quote (D2 §7.3's model-facing form) can be located reliably and that
offsets would not be better; that a unit packet without the page (D4 §4.1, as M10 and M24 see
it) carries what an annotator needs; that rule-based symbol scoping (D4 M13) reaches the scopes
annotators assign; and that adjudication itself is determinate (root versus a fresh session).

## 2. Inputs and blind packets (S0-A)

Each annotation pass receives a self-contained folder `results/s0/inputs/<pass>/` and nothing
else:

| File | Content |
|---|---|
| `guideline.md` | D2 §10 guideline v0, verbatim |
| `schema.yaml` | D2 §9 statistics schema v0 and the minimal core schema (the instruments' `code/schema/`) |
| `model.md` | D1 §1–§11, verbatim; §12 (the worked example) and §13 are removed |
| `format.md` | The model-facing `ClaimProposalBatch` of [D2 §7.3](../../design/D2-schema-and-guidelines.md#73-to-json-schema-for-llm-claim-proposals) (evidence by sentence id and quote, `extent` on local entities, statement anchors by sentence ids, `alternatives`, local refs in conditions and symbol bindings, condition nodes keyed by `op`), and two invented examples on text that is not in the sample |
| `units/<unit>.md` | The unit's packet in D7 §3.2 golden mode: the D4 §4.1 packet without hints, known entities, alternatives or any pipeline output, with standing context chosen by "previous binding sentences in the same section" computed from the text alone; the unit's sentences numbered (`[s1] …`) |
| `pages/<page>.md` | The page's full canonical text with the units to annotate marked and every sentence numbered (guideline §10.2 allows reading the whole page) |
| `instructions.md` | The procedure below and the list of what must not be read |

The packet text is S1's canonical text, so annotators read exactly what the pipeline will,
including S1's rendering conventions and section headings. Unit boundaries come from
`sample.json` offsets.

**Must not be read:** `docs/design/trace.md`, D1 §12, any other pass's output, the old
repository (`corpus-intelligence`), the Git history of the design documents, and the S0 brief's
interpretation table. The instructions ask each pass to list every file it opened in
`opened_files.txt`; a pass that opened a forbidden file is discarded and rerun with a new agent.

**Separation method (OPEN-D8-3).** Each pass is a new subagent with no conversation history,
started from a brief that names only its input folder and output folder; the tools it may use
are stated in the brief (file reading and writing, and the instruments' validator and locator);
its opened-file list is checked against the forbidden list by the root before its output is
used. The report describes this setup and any rerun, because it is the evidence D8 needs for
the `write_golden` tooling. It is instructed and audited, not sandboxed.

## 3. Passes

### 3.1 Passes A and B (S0-B)

Two fresh Opus 5.5 subagents, A and B, with identical instructions and the same packets. Each:

1. reads the guideline, schema, model and format;
2. annotates every core unit into one model-facing batch per unit, citing evidence by sentence
   id and quote, recording an `unsupported` item for every fact no predicate fits, and recording
   `alternatives` with a one-line reason where the text supports two readings;
3. writes `notes/<unit>.md`: every point where it had to guess, with the guideline section that
   was unclear, and any text that looks mis-rendered (an S1 matter);
4. runs the instruments' validator and quote locator on its batches and fixes malformed output
   or unlocated quotes, keeping its first submission as `first/<unit>.json` — so the
   malformed-output and unlocated-quote rates of a first attempt are measured, as D8's
   submission validation will see them.

Outputs: `results/s0/pass_a/`, `results/s0/pass_b/` (final batches, first submissions, notes,
opened files). The model, effort setting and date are recorded. The root then converts each
final batch to the stored form with `code/s0_locate.py` (the instruments' locator, D4 §4.3) into
`results/s0/stored/<pass>/` and reports unlocated quotes, as the brief specifies.

### 3.2 Offset-form probe

A third fresh agent annotates only T1–T4 with evidence given as character offsets into the unit
text (the stored form), with the same instructions otherwise. Its offsets are checked against
the canonical text and its claims are aligned with the reference. Reported: the share of
evidence offsets that are exact, off by a few characters, or wrong, against the quote form's
located rate. This tests D2 §7.3's premise that models should cite by quote; if offsets prove as
reliable, the model-facing form could be simplified.

### 3.3 Packet-only pass P (S0-E, after the reference exists)

A fresh agent annotates all twelve units from the golden-mode packet alone (§2), without the page
text, which is what M10 and M24 receive in a run apart from hints and known entities. Pass P is
scored against the reference at all tiers, and its differences from A/B are attributed: missing
context (a symbol or premise defined outside the unit and outside the standing context), or
ordinary disagreement. This measures what the packet design loses and bears on OPEN-D1-2 and
OPEN-D4-4. ("Pass P" avoids D7's name "pass C", which there means adjudication.)

## 4. Comparisons and adjudication

### 4.1 Pass versus trace (S0-C), before adjudication

For T1–T4, each pass is aligned with the trace's tables (written as batches by the root for the
instruments' verification). Every difference is classified, with a one-line reason: the trace is
wrong; the pass is wrong; both readings are defensible (the guideline is underspecified). This
classification is done before adjudication, because the root has read the trace and the
adjudicated reference therefore cannot serve as an independent check on it. Output:
`results/s0/trace_diff.md`.

### 4.2 Old-repository witness

`corpus-intelligence/fixtures/siegrist_three_sections/expectations.toml` holds 19 settled
targets, read only by the root. Those that cover core units
(`locationscale-definition`, `normal-parameters-respectively`, `normal-affine-nonzero-scale`,
`lognormal-definition`, `normal-sum-independent-pair`, `rod-hole-two-populations`, and any other
the root maps) are compared with A, B and later the reference at the level they state: parts
and roles (premise, conclusion, problem, sought, proof) and quoted spans. Differences are listed
in `results/s0/witness_diff.md`. These readings were settled independently of this design, so
agreement with them is evidence the reference is not an artefact of the guideline alone.

### 4.3 A versus B (S0-D)

The instruments align A and B per unit by D7 §5 (A as reference, B as prediction, then
symmetrized, as D7 §3.3 specifies) and produce `agreement.tsv` (unit × predicate × tier: A
count, B count, agreed), per-field agreement, binding and scope accuracy, unsupported agreement,
kappa for categorical fields, and key and meaning-key agreement. Per-predicate core, full and
evidence agreement is D7's "ceiling" for later method scores. The reading follows the brief: high core and lower full agreement points
at a guideline rule for qualifiers, conditions or bindings rather than the schema; disagreement
concentrated in one predicate points at its description; frequent `unsupported` items of one
kind point at a schema gap.

### 4.4 Adjudication

The root resolves every A/B difference into one stored-form batch per unit in
`results/s0/reference/<unit>.json`, each decision with a one-line reason and its kind:

| Kind | Meaning |
|---|---|
| guideline | The guideline as written decides it |
| guideline-gap | The guideline does not decide it; the root chose, and the gap is recorded |
| trace-corrected | The trace was wrong (from §4.1) |
| alternative | Both readings kept as an `alternatives` group (D2 §10.8) |
| unsupported | The fact stays an `unsupported` item; the gap is recorded |

Contested items (those A and B disagreed on) are flagged in the reference, so S2/S3 scoring can
report results with and without them. The reference passes the validator and records its
rendition key.

**D7 adjudicator session.** Independently, a fresh agent receives what D7 §3.4 gives pass C:
the guideline, the packets, both passes and the alignment diff (matched, A-only, B-only,
matched with qualifier differences), and decides each difference (keep A, keep B, keep both as
a faithful ambiguity, drop both, rewrite), marking `guideline_gap` where the guideline does not
settle it. Its result (`results/s0/adjudication_d7/`) is aligned with the root's reference.
Agreement between the two measures whether adjudication is determinate under the guideline;
where they differ, the root's decision stands for the S0 reference and the difference is
reported as evidence for D7 §3.4.

## 5. Answering the OPEN questions

| Item | Evidence used | How it is decided |
|---|---|---|
| OPEN-D1-2 (section extent for scopes) | Extents A and B assign to local entities (T2's "Suppose again" `X`; T1's `Z`; any variable used across units); pass P losses; the M13 probe under both section syntheses | `section` extent is needed if annotators agree on section-scoped variables that statement scope plus "again"-resolution cannot express, with the deciding spans |
| OPEN-D1-3 (parameter identity) | `FamilyParameter` entities in T4 (`mu`, `sigma` named by symbol, roles stated afterwards) and wherever a role is unnamed; A/B agreement on identity attributes | The rule that gives identical identities across A and B and the trace; a role-or-symbol rule that annotators applied inconsistently is reported as a guideline gap |
| OPEN-D1-4 (page-level standing assumptions) | T1's lead-in paragraph ("we fixed random variable \(Z\)…") and any similar lead-in on the other pages | Whether `section` (under S1's adopted synthesis) is the extent both annotators and the trace use, or `document` |
| OPEN-D2-4 (property predicates) | Count of distinct property predicates used (`pdf`, `cdf`, `mgf`, `mean_value`, `variance_value`, …) and of `unsupported` items that are properties (U12 `mom1`, skewness, kurtosis) | Many distinct properties, or properties missing from the schema, favour one `has_property` predicate with a `property` qualifier; a few, all present, favour keeping them |
| OPEN-D2-5 (standardized families) | Treatment of "standard normal", "standard score" (U6), "standard gamma" (U10) in A, B and the trace | Which representation gives consistent claims across units without forcing facts into nearby predicates |
| OPEN-D5-1 (slots for non-functional formula predicates) | The brief's step 6 list: every case where one unit states two different objects for the same subject and predicate, or a formula predicate (`pdf`, `cdf`, `mgf`) twice for one family in one statement | Whether D5 §5.4's slot definition would wrongly make them alternatives |
| OPEN-D8-3 (separate blind passes) | The setup in §2 and its audit record | The report describes the method and whether any pass had to be rerun |
| OPEN-D4-4 (unit of LLM work) | Sizes (§7), pass P losses, S1 size distributions | The smallest unit whose packet keeps pass P's full-tier agreement and fits D4 §4.1's caps |
| OPEN-D4-5 (rule scoping) | M13 probe (§6) | Share of reference bindings the rules reproduce, by binding kind |
| OPEN-D3-4 (meaning key) | Meaning-key agreement on aligned claims | Evidence only; decided with D7 |
| OPEN-D7-2 (formula equivalence) | Which tier decided each value comparison (instruments §4) | Evidence only; S5 decides |

## 6. M13 rule probe (S0-E)

A small implementation of D4 M13's rules over the twelve units and their pages:

- **Symbols** from S1's math segments via pylatexenc 3.0b2 `LatexWalker` nodes: letters from
  `LatexCharsNode`, Greek letters from `LatexMacroNode` (`\mu`, `\sigma`), with subscripts kept
  (`X_1`) and powers recorded (`\sigma^2` → base `\sigma`), using 3.0's special nodes for `_` and
  `^` where the default context provides them; what works here is noted for S5 as the M09
  candidate.
- **Binding sites:** a symbol mention in a sentence whose first lemma is in the binder lexicon
  of D2 §12.1 (`binders.sentence_initial`: suppose, let, assume, fix, define, consider, recall;
  `if` tested as an extension; `reopen` and `section_wide` phrases as written there), in a `where`
  or `for` clause, on the left of `\in` in such a sentence, or on the left of a definitional
  `=`; spaCy (S1's adopted pipeline) supplies lemmas and sentences.
- **Extents:** the smallest enclosing unit; outside units, to the end of the section or the next
  binding of the same symbol; "Suppose again" re-opens the previous section-level binding. Run
  under both S1 section syntheses (V4).
- **Comparison:** each symbol mention in the core units is assigned a binding site and extent,
  compared with the reference's local entities and symbol bindings. Reported in
  `results/s0/m13_probe.tsv` by binding kind (`variable`, `param_of`, `free`, `constant`,
  `unresolved`), with the cases the rules miss and why.

## 7. Gaps and sizes (S0-F)

**Gaps** (`results/s0/gaps.md`): every `unsupported` item and every noted guess from A, B and P,
grouped as schema gap (a missing class, predicate, qualifier or enum value, with proposed
addition and examples), guideline gap (a rule that is unclear, with proposed wording), or
representation gap (D1 cannot express it, with the construct needed). Each item lists its units
and a quotation of at most one sentence.

**Sizes** (`results/s0/size.tsv`): per unit and pass, the batch's characters, Qwen3.5-9B tokens
(cached tokenizer via `tokenizers==0.23.3`, revision recorded), approximate tokens by
characters ÷ 4 for comparison, counts of entities, claims, unsupported items and alternatives;
and the input side: unit text tokens and golden-mode packet tokens. These size the D8 work packets
and inform OPEN-D4-4: whether dense units exceed D4 §4.1's 3,000-token local cap in input or
produce batches too large for one local-LLM response.

## 8. Packages

| Package | Scope | Outputs | Done when |
|---|---|---|---|
| S0-A | Packets for A and B | `results/s0/inputs/{a,b}/` | Folders self-contained; S1 rendition key recorded |
| S0-B | Passes A and B; stored-form conversion; offset probe | `pass_a/`, `pass_b/`, `stored/`, `offset_probe/` | Twelve batches per pass validate; unlocated quotes reported; opened-file lists clean |
| S0-C | Trace and witness comparison | `trace_diff.md`, `witness_diff.md` | Every T1–T4 difference classified |
| S0-D | Agreement, root adjudication, D7 adjudicator session | `agreement.tsv`, `reference/`, `adjudication.md`, `adjudication_d7/` | Reference validates; every decision has a reason and kind; the two adjudications compared |
| S0-E | Pass P; M13 probe | `inputs/p/`, `pass_p/`, `pass_p_scores.tsv`, `m13_probe.tsv` | Pass P scored and its losses attributed; probe compared under both section syntheses |
| S0-F | Gaps, OPEN answers, sizes, report | `gaps.md`, `size.tsv`, `S0-report.md` | §9 satisfied |

The brief's data files (`pass_a/`, `pass_b/`, `stored/`, `reference/`, `agreement.tsv`,
`trace_diff.md`, `gaps.md`, `size.tsv`) all appear above.

## 9. What the report must state

`S0-report.md` follows the template. Its "Design implications" table lists proposed changes to
D1, the D2 schema and guideline, D2 §7.3's batch format, D4 §4.1 packets, D5 §5.4 slots and
the D7 §3 golden protocol (packets, separation, adjudication), each with its evidence, and answers every item in §5. It also states:

- the agreement figures at each tier with denominators, and their attribution by field;
- the trace corrections (for the closing package to apply);
- the evidence-form result (quote location rates; offset probe);
- the independence limits: same-model annotators, instructed blindness, root-adjudicated
  reference informed by the trace.

## 10. Choices left to execution

- The cost thresholds in the aligner and the guideline-gap wording, recorded where chosen.
- Which additional `expectations.toml` targets map onto core units.
- The two invented examples in `format.md` (they must use text outside the sample and must not
  hint at the trace's decisions).
