# Annotation guideline v1 (statistics)

Guideline v1, frozen for phase 0 (D2 §10 is its design text). Golden passes and the agent work from
it together with the generated annotator reference (§10.10). Sections carrying `<!-- core -->` go
into LLM prompts (D4 §4.2, D7 §2). No section declares unit features, so under `agent_reuse:
by_unit` every section applies to every unit (D2 §10).

## 10.1 Purpose

Produce, for one annotation unit, the complete set of entities, statements and claims that the
source states, in claim form, each with minimal evidence spans. Completeness is judged against
this guideline, not against what any extractor can find. Where this guideline gives a rule, follow
it even if another reading seems natural; where it gives none, choose, and say so in your notes.

## 10.2 The annotation unit and its context

- The unit is a numbered unit of the source, or a paragraph between units. Annotate what the unit
  states.
- The packet's **standing context** lists the sentences outside the unit that the unit depends on:
  the sentences where symbols the unit uses were introduced and are still in force, and
  section-wide suppositions. Each has an id (`c1`, `c2`, …) that you may cite like a unit sentence.
- **Context premises.** When the unit's claims depend on a supposition stated only in the standing
  context ("Suppose that X has …"), record that supposition once: a `Statement` of kind
  `assumption` anchored at its context sentence(s), with its premise claims (modality `supposed`,
  role `premise`) citing the context sentence. The unit's claims then reference those premises in
  their conditions and bind symbols to them (§10.7). Record nothing else from the standing context.
- Collapsible proofs and solutions are statements of kind `proof` or `solution` with a `proves`
  link; their steps are not annotated.

## 10.3 What to capture, and the statement role of each claim
<!-- core -->

A statement's kind is what the source calls it (definition, theorem, corollary, remark, example,
exercise, convention); a unit that mixes kinds ("A corollary of …", "Recall that …") yields one
statement per kind. `assumption` is a statement whose only content is a supposition.

| Statement kind | Capture | `statement_role` |
|---|---|---|
| Definition | the `Statement`; `defines` for each defined entity; the defining formulas; the family's parameters, their domains and roles; the suppositions the definition makes about things it takes as given | stipulated content: `definiens`; suppositions about given things: `premise` |
| Theorem, proposition, corollary | premises; conclusions; variables the statement introduces by formula ("then Y = cX has …") | premises `premise`; the formula defining an introduced variable `definiens`; everything the statement asserts `conclusion` |
| Remark | explicit claims only: identities, memberships, special cases; skip motivation, history, analogies, app instructions | as for a theorem when the remark supposes something and states a consequence; otherwise none |
| Example, exercise | the setup facts; the asked quantity | setup facts `example_value`; the asked quantity is recorded as `unsupported` with reason "asked quantity" (no predicate yet) |
| Convention | the conventional claims | none |
| Proof, solution | `Statement` and `proves` only | none |
| Assumption (context premise) | the supposed claims | `premise` |

Structural claims — `defines`, `proves`, `refers_to`, `follows_from` — take no role.

## 10.4 Entities
<!-- core -->

- A `DistributionFamily` for every named family, including standardized members ("standard
  normal", "basic Weibull"), with a `special_case_of` claim only when the source states the
  constraint. "Standard" or "basic" does not mean parameter-free.
- A construction ("the location-scale family associated with …") is a `FamilyConstruction`.
- Random variables are local, with `extent` `statement`, unless the source binds them for the
  section ("In this section", "Throughout", "Suppose again", or a supposition in a lead-in paragraph
  that later units use without rebinding); then `section`.
- A random variable written as an expression (`a + b X`, `X^2`) is a local `RandomVariable` whose
  symbol is the expression as written, with one `defined_as` claim.
- An **indexed** family of variables (`X_i` for `i ∈ {1, …, n}`) is one local entity whose symbol is
  the indexed form (`X_i`); claims about every member are stated once, about `X_i`, with the index
  range as a `member` node in their conditions. Do not expand it into `X_1`, `X_2`.
- **Parameters** are global `FamilyParameter` entities identified by family and canonical name. The
  canonical name comes from the phrase that **first names the symbol as a parameter of the
  family**: its role word if it has one ("shape parameter k" gives `shape`; "mean μ" gives `mean`),
  spelled as the `ParameterRole` value (`standard_deviation`, `degrees_of_freedom`); otherwise the
  symbol without backslash ("parameters μ and σ" gives `mu`, `sigma`). A role stated later ("σ is
  the shape parameter") is a `parameter_role` claim, not a rename. Add a `parameter_role` claim only
  when the role is stated and differs from the canonical name. Fixing the name at first naming
  keeps a parameter's identity the same across units that name its role differently or not at all.
- `has_parameter`, `parameter_domain` and `parameter_role` are stated only in a definition of the
  family; elsewhere "F with shape parameter k" supplies `param_values` only.

## 10.5 Claims
<!-- core -->

- Use the predicate whose description fits (the annotator reference, §10.10); if none fits, record an
  `unsupported` item with the text and a reason. Never force a fact into a nearby predicate.
- A sentence is a claim if it relates two identifiable things (entities, values, statements) in a
  way a consumer could query. Skip pure motivation, framing ("as usual") and scene-setting without a
  quantity.
- `has_distribution` carries the parameter values the sentence states, keyed by the family's
  canonical parameter names (§10.4). "shape parameter k and scale parameter b c" gives
  `{shape: k, scale: b c}`.
- When one sentence states a value both as a parameter and as a property ("mean μ", "E(X) = μ"),
  record both claims; they are not alternatives.
- Independence of variables is a condition (`pred` node, `independent`), not a claim. For a
  sequence written `(X_1, X_2, …, X_n)`, write the arguments as the source lists them, without the
  ellipsis (`X_1, X_2, X_n`).
- "Respectively" pairs in order; when the pairing is unclear, give both readings as alternatives.
- Do not state derived facts the source does not state (a standard deviation from a variance).

## 10.6 Modality
<!-- core -->

| Claim | Modality |
|---|---|
| A supposition: "suppose", "assume", "if", or "let" about something taken as given | `supposed` |
| What a definition stipulates, including "let X = …" or "the variable X = b Z" that introduces the defined construction's variable | `defined` |
| What a theorem, corollary or remark concludes; a formula introducing a variable inside a theorem | `asserted` for conclusions; `defined` for the introducing formula |
| Setup values in examples and exercises | `exemplified` |
| A convention | `conventional` |
| Structural claims (`defines`, `proves`, `refers_to`, `follows_from`) | `asserted` |

## 10.7 Conditions, formulas and symbol bindings
<!-- core -->

**Which claims carry a condition tree.** A claim's conditions say what must hold for that claim, as
the source states it, to be true.

1. **Premises and example values** carry none, except the range of an index they are stated for
   (`member` of `i` in `{1, …, n}`). Restrictions written into a premise ("with shape k ∈ (0, ∞)")
   restrict the premise's symbols: they go into the claims that depend on the premise (rule 3), not
   onto the premise. A premise that no condition references (everything depending on it is a
   formula or family-structure claim, rule 2) carries the qualifier `scope: statement`: it holds
   over its statement.
2. **Formula and family-structure claims** — `defined_as`, `construction_formula`,
   `definition_formula`, `transformation_of`, `has_parameter`, `parameter_domain`,
   `parameter_role`, `derived_parameter`, `identical_parameter`, `special_case_of` — hold by the form
   of the formula or the structure of the family. They carry no `claim` nodes; they carry only the
   restrictions on their own symbols that the source states with them ("For b ∈ (0, ∞), X = b Z").
3. **Every other claim** — distributions, moments, values, whether asserted or defined — carries a
   `claim` node for each premise it depends on (by default every premise of its statement, and any
   context premise, §10.2), and a `member` or `cmp` node for each stated restriction on the symbols
   it uses, repeated in each such claim even when the restriction was written with the premise.
   Several nodes are combined with `and`.
4. Structural claims carry none.

**Formulas.**

- Copy LaTeX exactly as written, including the source's macros (`\R`, `\E`, `\var`). Do not
  simplify or expand.
- A formula that defines a variable or generates a family excludes the variable it defines: the
  object of "X = b Z" is `b Z`; the subject carries X.

**Symbol bindings.** A binding says what a symbol refers to, so that a claim can be read on its own.
Look at where the symbol **first appears** in the unit (or its standing context), then bind it in
each claim by the first row that applies:

| Row | When | Binding |
|---|---|---|
| 1 | The symbol names a random variable or other entity of the batch | `variable` (with `entity`) |
| 2 | The claim is about a family as such (`has_parameter`, `parameter_domain`, `parameter_role`, `derived_parameter`, `identical_parameter`, `construction_formula`, `transformation_of`, `special_case_of`) and the symbol names that family's parameter | `family_param` (with `entity`) |
| 3 | The symbol first appears as (part of) the value a `has_distribution` claim gives to a parameter ("Suppose that X has … with mean μ"), and this is another claim | `param_of` (with `claim`, `param`); when the value is a larger expression containing it (σ in σ²) `param_expr_of` |
| 4 | The unit names the symbol as a parameter of a family it defines or describes ("scale parameter b"), anywhere in the unit, and row 3 does not apply | `family_param` (with `entity`) |
| 5 | Anything else the unit introduces: the value in the claim that introduces it, a symbol introduced by a restriction ("If c ∈ (0, ∞)"), an index, a dummy variable of a function, integral, sum or set | `free` |
| 6 | A numeric or named constant (`e`, `\pi`) | `constant` |
| 7 | None of these | `unresolved` |

In the reference's worked example of the general Weibull definition, k first appears as the shape value of Z's distribution (row 3: `param_of`
that premise elsewhere, `free` in the premise itself), and b first appears in the restriction "For b ∈
(0, ∞)" and is named the scale parameter of the family being defined (row 4: `family_param`).

Symbol maps are keyed by the symbol without backslash (`mu`, `sigma`, `X_i`).

## 10.8 Evidence, ambiguity and limits
<!-- core -->

- Each claim cites the minimal span(s) that state it, quoted exactly from one sentence (a unit
  sentence `sN` or a context sentence `cN`). The primary span excludes introducers ("Suppose that",
  "If", "then"); cite the introducer as `supporting` when it determines the modality.
- A `defined_as` claim cites the expression and its formula. A `proves` claim cites the proof's or
  solution's concluding clause.
- Conditions cite their spans with role `condition`.
- If the text supports two incompatible readings, give both claims and mark them as alternatives
  with a one-line reason.
- Out of scope: proof steps, app and simulation descriptions, data sets, biographies,
  computational exercises' numeric answers.

## 10.9 Output

A model-facing `ClaimProposalBatch` per unit (§7.3), with `statements`, `entities` (local
ones with their `extent`), `claims`, `alternatives` and `unsupported`, citing evidence by sentence
id and quote.

## 10.10 Generated annotator reference

The annotator reference is generated from the schema (§7.5): every entity type; every predicate with
its subject and object types, description, the qualifiers it takes and the guideline rules that apply
to it, grouped by predicate subset under the subset's description, which states the group's role,
modality and condition rule under §10.3, §10.6 and §10.7 (for `family_structure`: in a definition,
role `definiens` and modality `defined`); the role and modality tables; the binding kinds; the exact
value, node and item shapes; and complete worked examples.

## 10.11 Direction log

*(One entry per operator direction: date, the direction in the operator's words, the guideline
change it produced, the golden units re-authored.)* The log is kept in
`domains/<name>/directions.md` and in the `ops.intervention` rows of kind `direction`, outside the
guideline's content hash: recording a direction must not create a guideline version, or every
direction would invalidate reuse (D6 §4). Only the guideline changes a direction causes do. The
generated reference (§10.10) is hashed with the schema version's compiled artifacts.

| Date | Direction | Guideline change | Units re-authored |
|---|---|---|---|
| 2026-10-28 | "It looks like sonnet is the right call, and the rules establish a clear approach" | v0 → v1 (roles, modality, conditions, bindings, context premises, indexed families, parameter naming); golden author Sonnet (ADR-0011) | None yet (no golden set exists; the S0 reference was conformed to v1 in the spike) |
