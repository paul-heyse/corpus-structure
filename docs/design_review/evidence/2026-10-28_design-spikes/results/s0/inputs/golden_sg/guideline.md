<!-- Verbatim: docs/design/D2-schema-and-guidelines.md §10 (guideline v0) -->

## 10. Guideline v0 (statistics)

This is the starting content of `domains/statistics/guideline.md`. Opus writes goldens from it
alone ([D7 §3](D7-evaluation-goldens-outer-loop.md#3-golden-authoring-protocol)); the operator
steers it ([D7 §8](D7-evaluation-goldens-outer-loop.md#8-the-operators-outer-loop)). In
`guideline.md`, sections 10.3–10.8 carry the `<!-- core -->` tag that puts them into LLM prompts
(D4 §4.2, D7 §2).

### 10.1 Purpose

Produce, for one annotation unit, the complete set of entities, statements and claims that the
source states, in claim form (D1), each with minimal evidence spans. Completeness is judged
against this guideline, not against what any extractor can find.

### 10.2 The annotation unit and its context

- The unit is a Siegrist numbered unit (`div.unit`), or an unnumbered paragraph between units.
- You may read the whole page for context (running variables, earlier definitions), but you
  annotate only what the unit itself states. A claim restated from earlier in the page is
  annotated again where it is restated, as its own evidence.
- `<details>` blocks are proofs or solutions: annotate a `Statement` of kind `proof` or
  `solution`, and its `proves` link. Do not annotate proof steps in v0.

### 10.3 What to capture

| Statement kind | Capture |
|---|---|
| Definition | The `Statement`; `defines`; the defined entity; its formulas (`defined_as`, `construction_formula`, `definition_formula`, `pdf` …); parameters with `has_parameter`, roles and domains; the premises it supposes |
| Theorem, proposition, corollary | Premises (`supposed`), restrictions (as conditions), conclusions (`asserted`) with conditions referencing premises; derived variables (`defined_as`) |
| Remark or narrative paragraph | Only explicit claims (parameter identities, memberships, special cases); skip motivation, history and analogies |
| Example, exercise | The setup facts as `exemplified` claims; the asked quantity as `posed`; skip the solution's working |
| Proof, solution | `Statement` and `proves` only |
| Convention | Claims with modality `conventional` |

### 10.4 Entities

- Create a `DistributionFamily` for every named family, including standardized members
  ("standard normal distribution"), with a `special_case_of` claim when the source states the
  constraint.
- A construction ("location-scale family associated with …") is a `FamilyConstruction`, never a
  family.
- Random variables are local. Use statement scope unless the source binds the variable for the
  section ("Suppose again", "Throughout this section"); then use section scope with the
  section's first binding as the scope anchor.
- Parameters are global `FamilyParameter` entities identified by family and canonical name. Use
  the role word the source states ("location", "shape"); if none is stated, use the symbol
  (`mu`, `sigma`) and add `parameter_role` claims when a later sentence names the role.

### 10.5 Claims

- Use the predicate whose description fits; if none fits, record an `unsupported` item with the
  text and a reason. Never force a fact into a nearby predicate.
- `has_distribution` carries the parameter values the sentence states, keyed by the family's
  parameter canonical names. "with mean μ and variance σ²" gives `{mean: μ, variance: σ²}`.
- "Respectively" pairs in order; when the pairing is unclear, record both readings as
  alternatives (§10.8).

### 10.6 Modality

Premises introduced by "suppose", "let", "assume", "if" are `supposed`. What a theorem concludes
is `asserted`. What a definition stipulates is `defined`. Values in examples and exercises are
`exemplified`; what an exercise asks for is `posed`.

### 10.7 Conditions and formulas

- Restrictions ("if a ∈ ℝ and b ∈ ℝ ∖ {0}") become `member` or `cmp` nodes of the conclusion's
  condition tree, together with `claim` nodes for its premises.
- Copy LaTeX exactly as written, including the source's macros (`\R`, `\E`, `\var`). Do not
  simplify. Bind each symbol (D1 §6.1); use `unresolved` rather than guessing.
- Do not state derived facts the source does not state (the standard deviation from a variance);
  the pipeline derives them.

### 10.8 Evidence, ambiguity and limits

- Each claim cites the minimal span(s) that state it: usually a clause or a formula plus its
  governing words. Conditions cite their spans with role `condition`.
- If the text supports two incompatible readings, give both claims and mark them as alternatives
  with a one-line reason.
- Out of scope in v0: proof steps, app and simulation descriptions, data sets, biographies,
  computational exercises' numeric answers.

### 10.9 Output

A model-facing `ClaimProposalBatch` (§7.3) per unit, with `statements`, `entities` (local ones
with their `extent`), `claims`, `alternatives` and `unsupported` arrays, citing evidence by
sentence id and quote, written through the `write_golden` tool ([D8](D8-agent-and-query-interfaces.md)).
Until that tool exists (spikes), write the batch as a JSON file.

### 10.10 Generated inventory

*(Generated from the schema version by §7.5: every class, predicate, qualifier and enum value
with its description.)*

### 10.11 Direction log

*(One entry per operator direction: date, the direction in the operator's words, the guideline
change it produced, the golden units re-authored.)*
