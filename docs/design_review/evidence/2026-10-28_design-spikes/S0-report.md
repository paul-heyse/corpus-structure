# S0 · Reference annotations — report

**Run:** 2026-10-28, by Claude Opus 5.5 (root) with fresh subagents for every annotation, adjudication
and analysis pass (models below). **Brief:** [S0](S0-reference-annotations.md); **plan:**
[S0 plan](../../../plans/design-spikes-s0-s1/S0-reference-annotations.md). **Status:** passed.
Every figure below is rendered from the evidence catalog; each table names the record it comes from
(`records/`).

## Answer

Yes, with guideline rules still to write. D1's claim model and the statistics schema v0 express
what the twelve core units state, except for a small set of constructs (units on parameter values,
independence as a stated fact, what an exercise asks for, indexed independence, references outside
the unit). Two blind Opus passes agree on *what* is claimed — core F1 0.93 [0.83, 1.00] —
and much less on *how* — full F1 0.63 [0.43, 0.75]: the disagreement is conditions,
statement roles and modality, which are guideline rules, not schema gaps. An independent
Haiku adjudicator agrees with the root's reference at core 0.97 [0.87, 1.00] but full
0.74 [0.57, 0.84]; a Sonnet adjudicator at 0.97 [0.87, 1.00] and
0.82 [0.71, 0.91], so adjudication is close to determinate for a capable adjudicator
with both passes in front of it. Sonnet annotates *what* is claimed at Opus's level; Sonnet and
Haiku both trail on qualifiers, mostly at decisions the inputs leave to inference (unstated
condition, role and binding conventions; positional standing context), which is a defect of the
inputs, not a limit of the models. Holding the model fixed, the packet-only input loses nothing
on what is claimed; Sonnet without the pages loses some qualifier agreement, which the packet's
standing context should restore. M13's scope rules reproduce every annotated symbol scope once two rules are
added. Claim keys are unstable for two reasons in D1 §10.1, both fixable.

## What was run

| Record | Package | Outcome | What |
|---|---|---|---|
| [s0.instruments-ir2](records/s0.instruments-ir2.json) | I-A, I-B, I-R1, I-R2 | passed | Comparison instruments, review and math grammar, with the token form for keys (I-R2) |
| [s0.packets](records/s0.packets.json) | S0-A | passed | Blind annotation packets |
| [s0.offset-probe](records/s0.offset-probe.json) | S0-B | partial | Offset-form evidence probe |
| [s0.pass-a](records/s0.pass-a.json) | S0-B | passed | Pass A: blind annotation of the twelve core units (Claude Opus 5.5, golden inputs) |
| [s0.pass-b](records/s0.pass-b.json) | S0-B | passed | Pass B: blind annotation of the twelve core units (Claude Opus 5.5, golden inputs) |
| [s0.trace-batches](records/s0.trace-batches.json) | S0-C | passed | The worked trace as model-facing batches |
| [s0.trace-diff](records/s0.trace-diff.json) | S0-C | passed | Passes against the trace and the old-repository witness |
| [s0.adjudication](records/s0.adjudication.json) | S0-D | passed | Root adjudication of A and B into the reference |
| [s0.adjudication-d7](records/s0.adjudication-d7.json) | S0-D | passed | D7 adjudicator session (Haiku) |
| [s0.adjudication-d7-sonnet](records/s0.adjudication-d7-sonnet.json) | S0-D | passed | D7 adjudicator session (Sonnet) |
| [s0.adjudication-determinacy-ir2](records/s0.adjudication-determinacy-ir2.json) | S0-D, S0-G | passed | Root adjudication against the D7 adjudicator session |
| [s0.agreement-ir2](records/s0.agreement-ir2.json) | S0-D, S0-G | passed | Agreement between the blind passes, with keys and trace comparisons |
| [s0.pass-h](records/s0.pass-h.json) | S0-E | passed | Pass H: blind annotation of the twelve core units (Claude Haiku 5.5, golden inputs (control for P)) |
| [s0.pass-p](records/s0.pass-p.json) | S0-E | passed | Pass P: blind annotation of the twelve core units (Claude Haiku 5.5, unit packets only) |
| [s0.pass-sg](records/s0.pass-sg.json) | S0-E | passed | Pass SG: blind annotation of the twelve core units (Claude Sonnet 5.5, golden inputs) |
| [s0.pass-sp](records/s0.pass-sp.json) | S0-E | passed | Pass SP: blind annotation of the twelve core units (Claude Sonnet 5.5, unit packets only) |
| [s0.pass-scores-ir2](records/s0.pass-scores-ir2.json) | S0-E, S0-G | passed | Every pass against the reference; packet versus model effect |
| [s0.sonnet-scores-ir2](records/s0.sonnet-scores-ir2.json) | S0-E, S0-G | passed | Sonnet passes and adjudicator against the reference and the Opus passes |
| [s0.m13-probe-2](records/s0.m13-probe-2.json) | S0-E, S0-R1, S0-G | passed | M13 rule scoping against the reference (D2 lexicon with 'if') |
| [s0.gaps](records/s0.gaps.json) | S0-F | passed | Gap analysis |
| [s0.report-2](records/s0.report-2.json) | S0-F | passed | S0 report (with the Sonnet runs and the input diagnosis) |
| [s0.sizes](records/s0.sizes.json) | S0-F | passed | Batch and packet sizes |
| [s0.condition-classes](records/s0.condition-classes.json) | S0-G | passed | Condition failures against the reference, classified by shape |
| [s0.stored](records/s0.stored.json) | S0-G | passed | Stored forms of every batch set (revised quote cascade) |

Commands are in each record (`commands`); all run from this folder with
`UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python …`. Environment: [e0.environment](records/e0.environment.json)
(Python 3.14.10; spaCy 3.8.18; pylatexenc 3.0b2; sympy 1.14.0; lark 1.3.1; regex 2026.9.29; rapidfuzz;
pint 0.26.2). The instruments ([s0.instruments-ir2](records/s0.instruments-ir2.json)) passed their own
suite and an independent implementation review, whose blocking finding (F1, the core matching's
dependence on ties) was fixed before any figure here was computed; the aligner reproduced the root's
hand classification of T1–T4 exactly ([aligner_verification](results/s0/aligner_verification.md)).

## Results

### Separation of blind passes (OPEN-D8-3)

| Agent | Model | Separation |
|---|---|---|
| adjudicator | Claude Haiku 5.5 | fresh subagent; read only its input folder and output folder (transcript audit of every file opened, 2026-10-28); wrote only its output folder |
| annotator Pass H | Claude Haiku 5.5 | fresh subagent; read only its input folder and output folder (transcript audit of every file opened, 2026-10-28); wrote only its output folder |
| annotator Pass P | Claude Haiku 5.5 | fresh subagent; read only its input folder and output folder (transcript audit of every file opened, 2026-10-28); wrote only its output folder |
| annotator O | Claude Opus 5.5 | fresh subagent; read only its input folder and output folder (transcript audit of every file opened, 2026-10-28); wrote only its output folder; counted offsets with str.find |
| annotator Pass A | Claude Opus 5.5 | fresh subagent; read only its input folder and output folder (transcript audit of every file opened, 2026-10-28); wrote only its output folder |
| annotator Pass B | Claude Opus 5.5 | fresh subagent; read only its input folder and output folder (transcript audit of every file opened, 2026-10-28); wrote only its output folder |
| adjudicator | Claude Sonnet 5.5 | fresh subagent; read only its input folder and output folder (transcript audit of every file opened, 2026-10-28); wrote only its output folder |
| annotator Pass SG | Claude Sonnet 5.5 | fresh subagent; read only its input folder and output folder (transcript audit of every file opened, 2026-10-28); listed the file names in inputs/ and code/ once, opening none; wrote only its output folder |
| annotator Pass SP | Claude Sonnet 5.5 | fresh subagent; read only its input folder and output folder (transcript audit of every file opened, 2026-10-28); listed the file names in results/s0/ and code/ once, opening none; wrote only its output folder |

Each pass was a fresh subagent given one self-contained input folder (guideline, schema, model,
format, packets, pages) and one output folder, told what it may not read, and audited afterwards from
its transcript (every file opened), not from its own report. No pass read outside its folders, so
none was rerun. Same-model annotators remain a limit on independence (below).

### Agreement between the two Opus passes

Record [s0.agreement-ir2](records/s0.agreement-ir2.json). F1 with 95% bootstrap intervals over the twelve units.

| Comparison | Core | Full | Evidence |
|---|---|---|---|
| A vs B (symmetrized) | 0.93 [0.83, 1.00] | 0.63 [0.43, 0.75] | 0.60 [0.37, 0.75] |
| Trace vs A (T1–T4) | 0.79 [0.74, 0.90] | 0.23 [0.09, 0.63] | 0.23 [0.09, 0.63] |
| Trace vs B (T1–T4) | 0.77 [0.72, 0.90] | 0.32 [0.17, 0.75] | 0.32 [0.17, 0.75] |

On the 70 core-matched pairs: binding accuracy 1.00
(76 bindings), scope accuracy 1.00 (27 local
entities), Cohen's kappa 0.89 on modality and 0.84
on statement role; 0 full-tier failures cascaded from a failed premise. Full-tier
failures by field:

| Field | Failures |
|---|---|
| conditions | 10 |
| statement_role | 8 |
| modality | 5 |
| param_values.values | 2 |

By predicate (reference side A; agreed at core and at full):

| Predicate | Claims in A | Core | Full |
|---|---|---|---|
| `has_distribution` | 20 | 20 | 12 |
| `defined_as` | 9 | 9 | 4 |
| `has_parameter` | 7 | 7 | 7 |
| `parameter_domain` | 6 | 6 | 6 |
| `proves` | 6 | 6 | 6 |
| `refers_to` | 6 | 0 | 0 |
| `defines` | 4 | 4 | 0 |
| `transformation_of` | 4 | 4 | 3 |
| `mean_value` | 3 | 3 | 2 |
| `parameter_role` | 3 | 3 | 3 |
| `identical_parameter` | 2 | 2 | 0 |
| `variance_value` | 2 | 2 | 1 |
| `construction_formula` | 1 | 1 | 0 |
| `definition_formula` | 1 | 1 | 1 |
| `derived_parameter` | 1 | 1 | 1 |
| `follows_from` | 1 | 0 | 0 |
| `takes_values_in` | 1 | 1 | 1 |

Reading (S0 plan §4.3): high core and low full agreement locates the disagreement in guideline rules
for qualifiers, conditions and roles, not in the schema. `refers_to` and `defines` are the two
predicates whose use itself is unsettled (A recorded cross-references to bracketed statements, B did
not; `defines` modality split). The trace's comparisons are low at full mainly because 22 of its 26
differences with the passes are readings v0 does not decide ([trace_diff](results/s0/trace_diff.md)).

### Each pass against the reference; packet versus model

Record [s0.pass-scores-ir2](records/s0.pass-scores-ir2.json). The reference is the root's adjudication of A and B.

| Pass | Model | Inputs | Core | Full | Evidence | Binding accuracy |
|---|---|---|---|---|---|---|
| A | Opus 5.5 | golden | 0.93 [0.83, 1.00] | 0.80 [0.67, 0.89] | 0.79 [0.63, 0.89] | 1.00 |
| B | Opus 5.5 | golden | 1.00 [1.00, 1.00] | 0.81 [0.59, 0.96] | 0.79 [0.55, 0.96] | 1.00 |
| SG | Sonnet 5.5 | golden | 0.91 [0.88, 0.93] | 0.54 [0.42, 0.67] | 0.51 [0.36, 0.65] | 0.71 |
| SP | Sonnet 5.5 | packet only | 0.92 [0.85, 0.97] | 0.42 [0.29, 0.53] | 0.39 [0.23, 0.51] | 0.64 |
| H | Haiku 5.5 | golden | 0.74 [0.62, 0.85] | 0.38 [0.25, 0.50] | 0.36 [0.23, 0.48] | 0.74 |
| P | Haiku 5.5 | packet only | 0.79 [0.71, 0.89] | 0.43 [0.31, 0.59] | 0.40 [0.28, 0.53] | 0.50 |

Pass against pass, symmetrized (no reference involved):

| Pair | Models | Core | Full | Evidence |
|---|---|---|---|---|
| A vs B | Opus, Opus | 0.93 [0.83, 1.00] | 0.63 [0.43, 0.75] | 0.60 [0.37, 0.75] |
| A vs SG | Opus, Sonnet | 0.88 [0.79, 0.93] | 0.54 [0.41, 0.68] | 0.52 [0.38, 0.68] |
| B vs SG | Opus, Sonnet | 0.91 [0.88, 0.93] | 0.48 [0.36, 0.60] | 0.47 [0.33, 0.59] |
| SG vs SP | Sonnet, Sonnet | 0.86 [0.79, 0.92] | 0.67 [0.48, 0.79] | 0.67 [0.48, 0.79] |
| H vs P | Haiku, Haiku | 0.79 [0.69, 0.86] | 0.56 [0.44, 0.69] | 0.54 [0.40, 0.68] |

Sonnet records: [s0.pass-sg](records/s0.pass-sg.json), [s0.pass-sp](records/s0.pass-sp.json),
[s0.sonnet-scores-ir2](records/s0.sonnet-scores-ir2.json); its inputs were byte-identical to H's and P's
apart from output paths.

B scores 1.00 at core by construction: every core-level difference was adjudicated in B's favour,
and the reference is built from A and B, so the Opus rows measure agreement with conventions the
Opus passes themselves chose. On *what* is claimed Sonnet is at Opus's level (core
0.91 [0.88, 0.93] and 0.92 [0.85, 0.97] against A's 0.93 [0.83, 1.00]);
Haiku is lower. On qualifiers both trail. Pass against pass separates the model from the reference:
Sonnet against an Opus pass at full (0.54 [0.41, 0.68], 0.48 [0.36, 0.60]) is not
far below Opus against Opus (0.63 [0.43, 0.75]), and two Sonnet passes agree with each other
about as well (0.67 [0.48, 0.79]). The full-tier disagreement is mostly between readings
of rules the inputs do not state, not between capable and incapable annotators (next section).

The packet question is answered by the same model with and without the page: H against P and SG
against SP. Haiku does no better with the pages. Sonnet does no better at core but is better at full
with them (0.54 [0.42, 0.67] against 0.42 [0.29, 0.53]; the intervals
overlap), mainly on statement roles and bindings, where the page shows what kind of statement a unit
sits in and where its symbols were introduced. The packet design holds for what is claimed; for
qualifiers the packet should carry what the page supplied, which is the standing-context remedy
below (OPEN-D4-4).
First drafts needed format repair in five of twelve units for each Sonnet pass and more for Haiku
(aliases as objects, parameter values as lists, units inside values), which the validator caught.
Value comparisons not decided by canonical form were decided by the root and recorded with reasons
([manual_equivalence](results/s0/manual_equivalence.tsv)).

### Where the non-Opus passes lose points, and what the inputs give them

Full-tier failures on core-matched claims, by field (each comparison against the reference):

| Field | A | B | SG | SP | H | P |
|---|---|---|---|---|---|---|
| conditions | 1 | 9 | 19 | 23 | 17 | 17 |
| diag:bindings | 0 | 0 | 8 | 13 | 6 | 16 |
| diag:extent | 0 | 0 | 2 | 0 | 0 | 6 |
| modality | 4 | 1 | 4 | 7 | 2 | 3 |
| param_values.keys | 0 | 0 | 1 | 1 | 3 | 2 |
| param_values.values | 2 | 0 | 2 | 2 | 1 | 0 |
| statement_role | 3 | 5 | 4 | 12 | 7 | 5 |

The losses concentrate where the inputs leave the decision to inference:

- **Which claims carry conditions.** Record [s0.condition-classes](records/s0.condition-classes.json)
  classifies every condition failure by shape:

  | Class | A | B | SG | SP | H | P |
  |---|---|---|---|---|---|---|
  | pass adds a condition tree the reference lacks | 0 | 0 | 10 | 13 | 5 | 4 |
  | different premise references | 1 | 4 | 2 | 5 | 4 | 2 |
  | pass omits the condition tree | 0 | 3 | 1 | 0 | 2 | 7 |
  | same premises; reference repeats restrictions | 0 | 0 | 4 | 3 | 3 | 1 |
  | premises and restrictions both differ | 0 | 2 | 0 | 2 | 2 | 1 |
  | same premises; pass adds restrictions | 0 | 0 | 2 | 0 | 1 | 2 |

  The largest class for Sonnet is a condition tree the reference does not have: mostly definientia
  conditioned on the definition's premise (X = e^Y "given" Y normal), and premises carrying their own
  parameter restrictions. The reference conditions conclusions only, leaving definientia to their
  statement and restrictions to `parameter_domain` claims. Guideline §10.7 puts restrictions in "the
  conclusion's condition tree" but never says the other claims carry none; both readings are
  defensible, and the reference took the Opus passes' reading.
- **Statement roles.** No rule anywhere in the inputs says which role a claim takes by statement
  kind; the enum is listed in the model excerpt only.
- **Symbol bindings.** The seven binding kinds are a table on line 286 of a 3,800-word model
  excerpt; nothing says when a symbol is a family parameter (`family_param`) rather than the value
  given to a parameter in a stated distribution (`param_of`), the distinction the smaller models miss.
- **Where the rules live.** About 7,100 words of rules sit in five files (instructions, a
  776-word guideline, format, the schema as raw LinkML YAML with internal annotations, and a model
  excerpt); guideline §10.10, the generated per-predicate inventory the design calls for, was a
  placeholder; there is no worked example of a complete batch.
- **Context defects.** The standing context is chosen by "previous binding sentences in the
  innermost section", so U8 received the setup of a different exercise and U5, U9 and U11 unrelated
  sentences, while U12 and T2 lacked a parent-section premise; U8's golden-mode header still read
  `theorem` (fixed only in the packet-only inputs). There is no way to cite a context sentence or a
  statement outside the unit, so a premise that sits there cannot be referenced.

Opus reaches the reference largely because the reference adopted Opus's own choices at these
points. The remedy is in the inputs, not the model: an annotator-facing reference generated from
the schema (per predicate: signature, when to use, the qualifiers it takes, default modality and
role by statement kind, one example from a unit outside the test set), the decision rules above
written into the guideline, and standing context assembled by query over the segment and scope
indexes (the binding sentences of the symbols the unit uses, section-scoped assumptions, the
statements it cites, each citable by id) rather than by position.

### Adjudication determinacy (D7 §3.4)

Records [s0.adjudication-determinacy-ir2](records/s0.adjudication-determinacy-ir2.json) and
[s0.sonnet-scores-ir2](records/s0.sonnet-scores-ir2.json): the root's reference against fresh adjudicators
given what D7 §3.4 gives an adjudicator (guideline, packets, both passes, their alignment diff):
Haiku 5.5 core 0.97 [0.87, 1.00], full 0.74 [0.57, 0.84]; Sonnet 5.5 core
0.97 [0.87, 1.00], full 0.82 [0.71, 0.91]. With both passes in front of it,
Sonnet adjudicates close to the root. The Haiku session marked
21 of 97 decisions as guideline gaps, the Sonnet
session 27 of 107, the root
14 of 21. The Haiku session and the root decided three points oppositely while each believed the guideline settled
them: the modality of `defines`, the role of a variable a theorem derives, and the form of an indexed
premise ([gaps](results/s0/gaps.md)).

### Trace and old-repository witness (S0-C)

Record [s0.trace-diff](records/s0.trace-diff.json): 26
differences on T1–T4; the trace was wrong or incomplete in 2 of 26, a
pass in 2 of 26, and 22 of 26 are
defensible readings grouped under five proposed rules G1–G5. The old repository's independently
settled targets agree with both passes on every core-unit distinction, except four representation
limits ([witness_diff](results/s0/witness_diff.md)). Trace corrections for the closing package: T1
gains `parameter_role` claims (§10.3 asks for roles); T4's unit includes its second paragraph (the
standard lognormal), which the trace omits.

### Claim and meaning keys (OPEN-D3-4)

| Variant | Aligned pairs | Claim keys equal | Meaning keys equal |
|---|---|---|---|
| as D1 §10.1 defines them | 70 | 21 | 41 |
| statement keyed by its covering segment | 70 | 35 | 41 |
| global label dropped when identity is complete | 70 | 21 | 54 |
| both | 70 | 48 | 54 |

A statement's key is its sorted anchor segment keys, so "the unit" and "its sentences" key
differently for the same span; a global entity's key includes its label even when family and
canonical name identify it. With both normalized, the remaining key differences are real
disagreements (conditions, modality). The meaning key (claim key without the statement) is the more
stable of the two, which is evidence for OPEN-D3-4, decided with D7.

### Evidence form: quotes and offsets (D2 §7.3, D4 §4.3)

Record [s0.stored](records/s0.stored.json): 733 of 735 quotes located exactly and
2 of 735 after spacing normalization; none needed the fuzzy step or fell back to
the cited sentence. Citing by quote works for capable annotators. The offset probe
([s0.offset-probe](records/s0.offset-probe.json)) did not test what it meant to: the annotator computed
offsets with tool scripts, so it shows only that tool-assisted conversion works; whether a model
without tools can count offsets moves to S3.

### Sizes (OPEN-D4-4, D8 packets)

Record [s0.sizes](records/s0.sizes.json), Qwen3.5-9B tokens: units at most 345, golden packets at most
637, packet-only packets at most 637; batches median 1083 and at most 2509;
0 packet-plus-batch pairs exceed D4 §4.1's 3,000-token local cap. Output, not input, sets
the local LLM's budget: a batch is two to nineteen times its unit.

### M13 rule scoping (OPEN-D4-5, OPEN-D1-2)

Record [s0.m13-probe-2](records/s0.m13-probe-2.json), symbol extents of local entities in the reference
reproduced by the rules (expression entities such as `a + b X` are outside M13):

| Engine and rules | Nested h3/h4 sections | h3 only |
|---|---|---|
| regex, D2 §12.1 lexicon (with "if") | 18 of 20 | 18 of 20 |
| regex, plus paragraph statements | 20 of 20 | 20 of 20 |
| spaCy patterns, plus paragraph statements | 20 of 20 | 20 of 20 |

Section synthesis makes no difference on these units. The missing rule was that a claim-bearing
paragraph outside any unit (U6) is a statement extent, with section-wide binders ("In this
section", "Suppose again") taking precedence.

### Value equivalence (OPEN-D7-2)

Across the main comparisons, every value pair was decided by canonical form except these distinct
pairs, all judged unequal: 1 by the manual tier, 4 by the numeric tier. Canonical forms are D1 §6.2's token form for every value (ADR-0012; rerun under it in I-R2,
with no figure changed: [s0.instruments-ir2](records/s0.instruments-ir2.json)); the math grammar reads
87 of 92 S0 values under their declared kind (86 of 86 at I-R1: the
input set grew when the Sonnet passes' stored sets were added after that coverage run, and the pre-I-R2
grammar gives the same 92 values and statuses; the 5 not read are text in math, `N \text{ cm}` four
times and `\text{the constant}`); on a 78-page sample
976 of 1532 spans parse, the rest ambiguous (never resolved silently)
or failed by recorded category, for S5.

### Gaps

Record [s0.gaps](records/s0.gaps.json): 11 schema, 17
guideline and 7 representation gaps, each stated as the general rule or
construct missing ([gaps](results/s0/gaps.md), with a ranked top ten). The five most consequential:
references to statements outside the unit (RG-1); a statement-role table by statement kind (GG-3);
indexed families and independence over a sequence (RG-2); parameter naming (GG-5, OPEN-D1-3) with
a family's parameterizations (RG-7); modality of structural claims (GG-2).

## Answers to the open items

| Item | Answer | Evidence |
|---|---|---|
| OPEN-D1-2 | A `section` extent is needed: T1's Z ("In this section") and T2's X ("Suppose again") are section-scoped in every pass, the D7 adjudication and the reference, and U12's X in all but pass P, which had no page context and so could not see the binding outside its unit; statement scope cannot express them, and M13 reproduces them with section-wide and reopen binders | m13 table; [s0.agreement-ir2](records/s0.agreement-ir2.json) scope accuracy 1.00 |
| OPEN-D1-3 | Unsettled by v0: A, B and the trace name the lognormal σ `sigma`, P and H `shape`; the normal's parameter keys vary by unit. Rule proposed (GG-5): name by the role the source states, else the symbol, and record the role as a claim | [gaps](results/s0/gaps.md) |
| OPEN-D1-4 | `section` (under nested h3/h4 synthesis) is the extent both annotators and the trace use for T1's page-level assumption; `document` was never needed | trace diff; reference |
| OPEN-D2-4 | Keep separate property predicates: only `mean_value` and `variance_value` were used, both present; add a standard-deviation property (missing in U6) | [gaps](results/s0/gaps.md) |
| OPEN-D2-5 | Standardized families as families of their own worked in every pass; no unit states the constraint, so `special_case_of` was never written; "standard" does not mean parameter-free (standard gamma keeps its shape) | [gaps](results/s0/gaps.md) |
| OPEN-D5-1 | Not tested: no unit states one formula predicate twice for a subject; the four multi-object cases are entity-valued | [gaps](results/s0/gaps.md) |
| OPEN-D8-3 | Fresh subagents, one input and one output folder each, read restrictions, transcript audit of opened files; no rerun needed | separation table |
| OPEN-D4-4 | The unit is the right packet: every packet fits the local cap, and at a fixed model the packet loses nothing on what is claimed. Without the pages Sonnet loses some qualifier agreement (roles, bindings) and Haiku none; U12's X in pass P shows a binding outside the unit. The standing context must carry these (query-assembled, rule below); size the output budget from batch size | pass tables; sizes |
| OPEN-D4-5 | Rules reproduce every annotated symbol scope with two additions (sentence-initial "if", paragraph statements) | m13 table |
| OPEN-D3-4 | Evidence: meaning keys are more stable than claim keys; two D1 §10.1 rules cause most key differences | keys table |
| OPEN-D7-2 | Evidence: canonical form decided nearly every comparison; SymPy and numeric tiers were needed a handful of times, one manual | value equivalence |

## Assumptions

- The reference is the root's adjudication of A and B, informed by the trace (the root read it);
  it is a spike reference, not a D7 golden.
- Guideline-gap decisions follow the proposed rules G1–G5 ([adjudication](results/s0/adjudication.md)).
- Passes A and B, the offset probe and the sentence-gold markers ran on Opus 5.5; from then on golden
  work ran on Haiku 5.5 by operator direction (passes P and H, the Haiku D7 adjudicator); passes SG
  and SP and a second D7 adjudicator ran on Sonnet 5.5 on the same inputs, by operator direction.
- U8's golden-mode packet header read "theorem" for passes A, B, H and SG (a section-hint bug fixed
  only in the packet-only inputs); every pass annotated it as an exercise regardless.

## Design implications

| Design item | Proposed change or answer | Evidence |
|---|---|---|
| D2 §10 guideline | Write rules G1–G5 and the top-ten gaps: binding of symbols named as parameters later; modality inside definitions; restrictions in premises; structural claims asserted and anchored; formulas without the generated variable; a statement-role table by kind; references outside the unit | trace diff, adjudication, gaps |
| D2 §9 schema | Number values with units in `param_values`; an independence claim predicate; a `posed` claim for what an exercise asks; a standard-deviation property | witness diff, gaps SG-1, SG-3 |
| D1 §7 | An indexed-set argument for `independent` (base, index, range) | witness diff, gaps RG-2 |
| D1 §10.1 keys | Key a statement by the segment its anchor covers; drop the label from a global entity's key when its identity is complete | keys table |
| D4 M13 | Sentence-initial "if" in the binder lexicon (done in D2 §12.1); a standalone claim-bearing paragraph is a statement extent | m13 table |
| D7 §3 golden protocol | Golden author: any of the three models can author once the inputs state the conventions; Sonnet already matches Opus on core content and adjudicates close to the root. Keep an independent adjudicator pass, and rerun a Sonnet/Haiku pair on the revised inputs to confirm | pass tables; adjudication determinacy |
| D2 §10.10, D7 §3.2, D8 | Annotator inputs: generate the per-predicate reference from the schema (signature, when to use, qualifiers, default modality and role by statement kind, one example outside the test set); write the condition, role and binding rules; assemble standing context by query over segment and scope indexes, citable by id; serve the same lookups as agent tools (D8) | where the non-Opus passes lose points |
| D7 §3.2 standing context | The innermost-section rule misses parent-section bindings (T2's empty standing context) and picks unrelated sentences (U5, U8, U9, U11); select binding sentences of symbols the unit uses (M13) | packets; pass notes |
| D4 §4.1, M10 | Size the output budget from batches (up to ~2,500 tokens here), not from units | sizes |
| D2 §7.3 evidence form | Keep quotes; offsets untested without tools (S3) | quote location; offset probe |
| trace.md | T1 gains `parameter_role` claims; T4 includes its second paragraph | trace diff |

## Independence limits

Same-model annotators (A and B are both Opus 5.5; SG and SP Sonnet 5.5; P and H Haiku 5.5) share biases that blind
separation cannot remove; blindness was instructed and audited, not enforced by the environment;
the reference is root-adjudicated and informed by the trace; the guideline under test was written
by the same design process as the trace.

## Follow-ups

- S2/S3 score GLiNER2 and the local LLM against this reference, with and without contested items.
- S3: offsets without tools; output budgets from the sizes above.
- S5: the math grammar's failure categories; formula equivalence tiers.
- After the guideline rules are written and the inputs restructured (generated predicate reference,
  query-assembled standing context): a Sonnet and a Haiku pass and an adjudicator pass on the same
  units, plus a few units from other pages not used to write the rules, to measure whether full-tier
  agreement and adjudication determinacy rise and whether the rise holds outside these twelve.

<!-- generated by `just evidence render S0-report.md.j2` on 2026-10-28; records: 2026-10-28_design-spikes/s0.adjudication-determinacy-ir2, 2026-10-28_design-spikes/s0.agreement-ir2, 2026-10-28_design-spikes/s0.condition-classes, 2026-10-28_design-spikes/s0.gaps, 2026-10-28_design-spikes/s0.instruments-ir2, 2026-10-28_design-spikes/s0.m13-probe-2, 2026-10-28_design-spikes/s0.offset-probe, 2026-10-28_design-spikes/s0.pass-scores-ir2, 2026-10-28_design-spikes/s0.sizes, 2026-10-28_design-spikes/s0.sonnet-scores-ir2, 2026-10-28_design-spikes/s0.stored, 2026-10-28_design-spikes/s0.trace-diff -->
