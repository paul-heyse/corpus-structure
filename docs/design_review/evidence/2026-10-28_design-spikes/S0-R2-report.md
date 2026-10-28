# S0-R2 · Annotator inputs v1 — revisit report

**Run:** 2026-10-28, by Claude Opus 5.5 (root) with fresh subagents for the two passes (Sonnet 5.5, Haiku 5.5)
and the adjudicator (Sonnet 5.5). **Revisits:** [S0 report](S0-report.md), whose diagnosis was that
the smaller models lost points where the inputs left conventions unstated and chose context by
position. **Status:** passed.

## Answer

Yes. With the conventions written down, a reference generated from the schema, worked examples and
context assembled by query, Sonnet annotating from unit packets alone agrees with the reference at
full tier 0.77 [0.59, 0.91], where the same model on the v0 inputs scored
0.37 [0.25, 0.46] and the Opus passes (v0 inputs, with pages) 0.68 [0.49, 0.81]
and 0.68 [0.47, 0.83]; before a three-item reference correction found by reading pass SV,
Sonnet was 0.72 and the Opus passes
0.72 and 0.71. Haiku rises from 0.35 [0.25, 0.48] to
0.68 [0.54, 0.82]. The two passes agree with each other on six units from pages no
rule was written from at 0.76 [0.70, 0.86], so the gain is not confined to
the units the rules came from. Both models can do the task; what they lacked was the information.

## What changed in the inputs

Record [s0r2.inputs](records/s0r2.inputs.json). Everything else (unit text, schema, validator, model
excerpt) is as in S0's packet-only inputs.

| Change | Where | What it fixes |
|---|---|---|
| Guideline v1: statement roles by statement kind; modality by role; which claims carry conditions; bindings by where a symbol first appears; context premises; indexed families; parameter naming | [s0r2/guideline_v1.md](s0r2/guideline_v1.md), a candidate for D2 §10 | the unstated conventions behind most v0 full-tier failures |
| An annotation reference generated from the schema: entity types with identity slots, every predicate with its role, modality and condition rule, qualifiers, enums, exact value and node shapes | `results/s0r2/inputs/packet_v1/reference.md` (`code/s0r2_inputs.py`) | rules scattered over five files, the schema given as raw LinkML |
| Three worked examples from the Weibull page, which no annotation unit comes from | `results/s0r2/examples/` | no complete example batch |
| Standing context by query: the binding sentence M13 assigns each symbol the unit uses, when it lies outside the unit, citable as `cN` | `results/s0r2/sample.json` (`code/s0r2_sample.py`) | context by position (another exercise's setup in U8; U12's premise missing) |
| Guideline-rule warnings in the validator (`--rules`) | `code/s0r2_rules.py` | rules a model must otherwise re-check by reading |

The reference was conformed to v1 ([s0r2.reference-v1](records/s0r2.reference-v1.json)): it already
followed v1 on most points, and the root's decisions, each with its rule, are listed in
`results/s0r2/reference_model_v1/decisions_v1.json`. Three of them (restrictions on two formula
claims in T3 and U10) were added after the v1 passes were scored, when comparing pass SV showed the
reference had missed rule 2. The figures below use the corrected reference. Because the correction
was found by looking at a pass, the record also keeps the figures before it, which are fully fixed in
advance: full-tier SV 0.72, HV
0.63, A 0.72,
B 0.71. Before the correction Sonnet equals the Opus
passes; after it, Sonnet is above them (the correction adds restrictions that the Opus v0 passes,
annotating under v0, did not write).

## Results

Record [s0r2.scores-ir2](records/s0r2.scores-ir2.json). F1 with 95% bootstrap intervals over the units.
The comparisons were rerun under D1 §6.2's token form for keys (I-R2, ADR-0012); no figure changed.

### Each pass against the v1 reference (twelve core units)

| Pass | Model | Inputs | Core | Full | Evidence | Binding accuracy |
|---|---|---|---|---|---|---|
| A | Opus 5.5 | v0, pages | 0.92 [0.81, 0.99] | 0.68 [0.49, 0.81] | 0.66 [0.46, 0.81] | 0.95 |
| B | Opus 5.5 | v0, pages | 0.97 [0.94, 1.00] | 0.68 [0.47, 0.83] | 0.67 [0.43, 0.83] | 0.95 |
| SG | Sonnet 5.5 | v0, pages | 0.92 [0.89, 0.95] | 0.47 [0.35, 0.59] | 0.44 [0.29, 0.57] | 0.65 |
| SP | Sonnet 5.5 | v0, packet only | 0.89 [0.83, 0.93] | 0.37 [0.25, 0.46] | 0.34 [0.19, 0.44] | 0.58 |
| **SV** | Sonnet 5.5 | **v1, packet only** | 0.95 [0.90, 1.00] | 0.77 [0.59, 0.91] | 0.72 [0.56, 0.86] | 0.94 |
| H | Haiku 5.5 | v0, pages | 0.70 [0.61, 0.80] | 0.29 [0.18, 0.37] | 0.27 [0.16, 0.37] | 0.66 |
| P | Haiku 5.5 | v0, packet only | 0.75 [0.69, 0.85] | 0.35 [0.25, 0.48] | 0.32 [0.22, 0.42] | 0.46 |
| **HV** | Haiku 5.5 | **v1, packet only** | 0.82 [0.72, 0.91] | 0.68 [0.54, 0.82] | 0.65 [0.52, 0.79] | 0.89 |

The v0 reference itself scores 0.86 [0.75, 0.94] at full against the v1 reference: the
conformance changed little, so the rise is not an artefact of moving the target.

### Pass against pass (no reference)

| Pair | Units | Core | Full |
|---|---|---|---|
| A vs B (Opus, v0 inputs with pages) | core twelve | 0.93 [0.83, 1.00] | 0.63 [0.43, 0.75] |
| SP vs P (Sonnet vs Haiku, v0 packet only) | core twelve | 0.77 [0.70, 0.85] | 0.38 [0.29, 0.47] |
| SV vs HV (Sonnet vs Haiku, v1 packet only) | core twelve | 0.75 [0.61, 0.88] | 0.57 [0.42, 0.73] |
| SV vs HV | six held-out units | 0.90 [0.81, 0.98] | 0.76 [0.70, 0.86] |

The held-out units (Pareto and ChiSquare: two definitions, a theorem that depends on standing context,
a transformation, an indexed sum, an exercise) were chosen by kind before the passes ran and were not
used to write any rule or example; they sit among the core units in one unlabelled list.

### Where the remaining points go

Full-tier failures on core-matched claims, by field:

| Field | SP (v0) | SV (v1) | P (v0) | HV (v1) |
|---|---|---|---|---|
| conditions | 25 | 8 | 20 | 10 |
| diag:bindings | 17 | 2 | 18 | 6 |
| diag:extent | 0 | 0 | 6 | 4 |
| modality | 7 | 0 | 3 | 0 |
| param_values.keys | 1 | 2 | 2 | 2 |
| param_values.present | 0 | 4 | 0 | 0 |
| param_values.values | 2 | 0 | 0 | 1 |
| statement_role | 12 | 1 | 5 | 0 |

Statement roles, modality and bindings, the conventions v1 writes down, nearly vanish for Sonnet.
What remains is concentrated in points v1 still leaves open or gets wrong (next section).

### Adjudication

Record [s0r2.adjudication](records/s0r2.adjudication.json): a fresh Sonnet adjudicator over SV and HV,
given the v1 inputs, both batches and their alignment, against the v1 reference on the core twelve:
core 0.89 [0.84, 0.97], full 0.75 [0.61, 0.87]. It marked
14 of 111 decisions as guideline gaps (the v0 Sonnet
adjudicator over the Opus passes marked 27 of 107). Adjudicating a Sonnet and a Haiku pass adds nothing
over the Sonnet pass alone (0.77 [0.59, 0.91]). Its decision tables mostly keep SV's
version (about 35 rows keep A, about 13 keep B, 15 drop an item only HV had), so the result stays close
to SV, and on net its departures from SV did not move toward the reference. With inputs that state the conventions, a second annotator and an
adjudicator are worth their cost as a check on contested items, not as a way to raise the batch.

## What v1 still leaves open (for v2)

From the passes' and the adjudicator's notes and the remaining failures:

- **Members of an indexed family as arguments.** v1 makes `X_i` one entity, yet asks for independence
  over `X_1, X_2, X_n` as written; both passes passed the indexed entity repeatedly. This is
  representation gap RG-2 (an indexed set argument), which a guideline cannot close.
- **Which premises a claim depends on.** "By default every premise of its statement" over-references
  when a statement has independent premises (T4: the standard-lognormal claim referencing the
  lognormal premise). Better: the premises whose entities or symbols the claim uses.
- **Section-level suppositions that nothing references:** `scope: statement` or `section` when the
  source says "In this section".
- **Not yet in v1:** restricting phrases ("In some settings", GG-16), recalled definitions (GG-12),
  local definitions ("where μ = Σ μ_i", RG-4), and the shapes of `param_mapping`, `param_symbols` and
  `param_constraints` (SG-11).
- **Parameter names across units:** a family's canonical names are fixed by its defining unit, which a
  packet does not show (RG-7); the reference could list each family's parameters once defined.

## Assumptions and limits

- The root wrote the rules, conformed the reference and wrote the examples; the rules were derived
  from adjudicating these twelve units, so their figures favour v1. The held-out units are the check,
  and they are six units with wide intervals.
- One pass per model; same-model biases are not separated.
- The Opus passes ran on v0 inputs; whether Opus also gains from v1 was not run (golden work is on
  Haiku or Sonnet by operator direction).
- The validator's rule warnings are part of the inputs; their separate effect was not measured.

## Design implications

| Design item | Proposed change | Evidence |
|---|---|---|
| D2 §10 guideline | Adopt guideline v1 (with the v2 points above) as the statistics guideline | pass tables |
| D2 §7.5, §10.10 | Generate the annotator reference from the schema as v1 does, with per-predicate role, modality and condition rules and worked examples | inputs record |
| D2 §7.4 | Compile the checkable guideline rules into the validator (warnings), as `s0r2_rules.py` does | inputs record |
| D7 §3.2, D8 §3 | Standing context by query over M13 binding sites, each sentence citable; drop the positional rule | sample; U8, U12 |
| D7 §3 golden author | Sonnet on packets is at Opus's level of agreement with v1 inputs; Haiku viable with adjudication. Keep an independent adjudicator | pass and adjudication tables |
| D3, D8 | The lookups the inputs needed (predicate cards, symbol binding sites, section suppositions) are queries over the stored schema and segment indexes; serve them to agents as tools | inputs record |

<!-- generated by `just evidence render S0-R2-report.md.j2` on 2026-10-28; records: 2026-10-28_design-spikes/s0r2.adjudication, 2026-10-28_design-spikes/s0r2.inputs, 2026-10-28_design-spikes/s0r2.pass-hv, 2026-10-28_design-spikes/s0r2.pass-sv, 2026-10-28_design-spikes/s0r2.reference-v1, 2026-10-28_design-spikes/s0r2.scores-ir2 -->
