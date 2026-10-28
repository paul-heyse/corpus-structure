# S0 · Gap analysis: schema v0, guideline v0 and the D1 representation

**Done:** 2026-10-28 by an analyst worker (Claude Opus 5.5), read-only over `results/s0/`.
**Inputs:** golden-mode guideline, schema, model and format (`inputs/golden/`), the twelve unit
packets, the final batches and notes of passes A, B (Opus, golden inputs), P (Haiku, packet
only) and H (Haiku, golden inputs), the reference (`reference_model/`, the stored form in
`reference/`), the root adjudication (`adjudication.md`, r1–r21), the D7 adjudicator session
(`adjudication_d7/`), `trace_diff.md` (d1–d26, G1–G5) and `witness_diff.md` (limits W1–W4, in
the order of its last table). Counts come from the model-form JSON. The stored-form
`unsupported` counts are the same: A 8, B 13, P 9, H 11, reference 14. No pass and not the
reference has an `alternatives` group.

**How to read a gap.** Each gap names the general construct or rule that is missing. The units
are examples of it. "Hits" counts what each source did: pass notes that flag the point, batch
items such as `unsupported` items and condition leaves, root decisions (r*n*) and D7 decision
rows marked `guideline_gap` yes (D7-gap) or no (D7). "Independent" says whether at least two
sources reached the gap separately. A and B count as independent of each other (they were blind
passes), and so do P and H, the root and D7, and the witness and the trace.

**Merged families.** Each of these has one home here. G1 is in GG-6, G2 in GG-1, G3 in GG-4,
G4 in GG-2 and G5 in GG-7. The root's 14 guideline-gap decisions are r1 (GG-1), r2 (GG-4),
r3, r9, r19 and r21 (GG-2), r6 (GG-3, GG-11), r10 (GG-5), r12, r18 and r20 (RG-2), r13 (GG-11),
and r15 and r16 (RG-1). Its 3 unsupported decisions are r5 (SG-7, SG-8), r14 (SG-4, SG-5) and
r17 (SG-3). The 21 D7-gap rows fall into GG-3 (6), RG-2 (3), RG-1 (3), GG-1 (1), GG-4 (2),
GG-8 (2), SG-8 (1), GG-11 (1), SG-3 (1) and GG-15 (1).

**Root and D7 disagree** on six decision families: GG-2 (3 units), GG-3 (5 units), RG-2
(3 units), RG-1 (U7), GG-4 (T1) and GG-11 (U6). In GG-2, GG-3 and RG-2, *each* adjudicator
thought the guideline decided the point, and they reached opposite answers. That is the
strongest sign of an unclear rule in this spike.

---

## 1. Schema gaps

### SG-1 · No predicate for what an exercise asks for

- **Units:** U8. The construct is needed by every exercise that asks for a quantity.
- **Hits:** each of A, B, P and H recorded 1 `unsupported` item and flagged it in its notes; the
  reference kept it; D7 kept it (D7); witness W3. The schema has no claim that could carry
  modality `posed`, so all six batches contain 0 `posed` claims, although guideline §10.3 asks
  for "the asked quantity as `posed`".
- **Quote (U8 s5):** "Find the probability that the rod is to big for the hole."
- **Proposal:** add a core predicate `asks_for`, with domain `Statement` (kinds `exercise`,
  `example`) and range `Formula | PhraseValue`.
  - The claim carries modality `posed`.
  - The object is a formula when the source writes one, and otherwise a phrase, whose symbols
    may bind to the exercise's local entities.
  - Event probabilities need no new value type: `\P(Y - X \lt 0)` is a formula over local
    variables.
  - Add a guideline line: "the asked quantity is an `asks_for` claim on the exercise
    statement."
- **Independent:** yes (A, B, P, H and the witness).

### SG-2 · Condition predicates have no claim-predicate twin

- **Units:** U8 states independence as a fact. U5, U9 and U11 state it only as a premise, which
  the schema handles.
- **Hits:** each of A, B, P and H recorded 1 `unsupported` item and flagged it in its notes;
  the reference kept it; D7 kept it (D7); witness W2.
- **Quote (U8 s4):** "The machining processes that produce the rod and the hole are
  independent."
- **Proposal:** for every `ConditionPredicate` (`independent`, `identically_distributed`,
  `iid`), declare a claim predicate with the same arguments.
  - Example: `independent_of`, with domain `RandomVariable`, range `RandomVariable`,
    `ci:symmetric: true` and `ci:object: entity`.
  - An n-ary or indexed form follows RG-2.
  - Add a guideline line: independence stated of physical processes is annotated on the random
    variables those processes produce, with the process wording as `supporting` evidence.
  - This keeps setup facts (`exemplified`) and stated facts (`asserted`) out of condition trees,
    where no claim could carry them.
- **Independent:** yes (A, B, P, H and the witness).

### SG-3 · A parameter value can only be a `Formula`

- **Units:**
  - U8: values with units, "mean 1 cm".
  - U7: a value that is the subject itself, "with mean being the constant".
- **Hits:**
  - U8 units: A wrote `1 cm` inside formula LaTeX, where it reads as the symbols c·m. B recorded
    2 `unsupported` items. P and H dropped "cm" from the batch and flag the loss in their notes.
    A and B report that the validator rejected a number value with a unit; P and H note that a
    parameter value must be a formula. The root decided it in r17, D7-gap 1, witness W1.
  - U7 "mean being the constant": each of A, B, P and H recorded 1 `unsupported` item; the
    reference kept it.
- **Quote (U8 s2):** "The radius of the rod is normally distributed with mean 1 cm and standard
  deviation 0.002 cm."
- **Proposal:** widen `ParamValue.value` from `Formula` to the D1 value union.
  - Allow `formula | number (with pint unit) | entity`. D1 §6 already uses this sentence as its
    `number` example.
  - Allow an `entity` value to reference the claim's own subject, so that "mean being the
    constant" is `{mean: {t: entity, ref: <subject>}}`.
  - Apply the same widening to `param_symbols`.
- **Independent:** yes (A, B, P, H, the root, D7 and the witness).

### SG-4 · The property predicates cover fewer quantities than `ParameterRole` names

- **Units:** U6, "standard deviation σ > 0" of a random variable.
- **Hits:**
  - `unsupported` items: A 1, P 1, H 1, reference 1.
  - `unsupported` condition leaves: A 2, B 2, reference 2, D7 2.
  - Notes: A, B, P and H.
  - Root decided it in r14; D7 kept it (D7).
- **Quote (U6 s1):** "Recall that in general, if \(X\) is a random variable with mean \(\mu\) and
  standard deviation \(\sigma \gt 0\), then \(Z = (X - \mu) / \sigma\) is the standard score of
  \(X\)."
- **Proposal:** derive the property vocabulary from one enum so that it cannot drift from
  `ParameterRole`.
  - **Option 1:** add `sd_value` (domain `Distributed`, range `Formula`).
  - **Option 2 (OPEN-D2-4):** one `has_property` predicate with a `property` qualifier, using
    an enum shared with `ParameterRole`'s moment-type values (mean, variance,
    standard_deviation, precision).
  - Today `mean` and `variance` have predicates, while `standard_deviation` exists only as a
    role and as a `param_values` key.
- **Independent:** yes (A, P, H; B as a condition leaf).

### SG-5 · No relation for "Y is the ⟨concept⟩ of X"

- **Units:** U6.
- **Hits:**
  - B recorded 1 `unsupported` item; the reference kept it; the root decided it in r14; D7 kept
    B's item (D7).
  - A, P and H expressed the relation only indirectly, through `defined_as Z = (X − μ)/σ` and
    the concept's `definition_formula`.
- **Quote (U6 s2):** "A corollary of the last result is that if \(X\) has a normal distribution
  then the standard score \(Z\) has a standard normal distribution."
- **Proposal:** add a predicate `concept_value`, with domain `Entity` (in practice
  `RandomVariable`), range `Concept` and a qualifier `of` (entity, multivalued, an identity
  qualifier).
  - Example: "Z is the standard score of X" is `concept_value(Z, standard score, of: [X])`.
  - The same predicate covers "the sample mean of X₁…Xₙ" and "M is the MGF of X".
- **Independent:** partly. B raised it; D7 independently kept it. No other pass named it.

### SG-6 · No predicate for claims about other statements' scope of validity

- **Units:** U7. The text says which results do not hold for a constant, which still hold, and
  that one result "would hold for all a and b".
- **Hits:** each of A, B, P and H recorded 3 `unsupported` items (12 in total) and flagged them
  in its notes; the reference kept all 3; D7 kept them (D7). H calls this "the least clear point
  of the unit".
- **Quote (U7 s4):** "Moreover, the result for linear transformations [24] would hold for all
  \(a\) and \(b\)."
- **Proposal:** add a core predicate `holds_for`, with domain `Statement` and range
  `Entity | condition`.
  - Use the core `polarity` qualifier for "do not hold".
  - Use the core `conditions` qualifier, holding a `claim` node of the convention, for "under
    this convention".
  - Add a qualifier `relaxes`: a condition tree of the target statement's restrictions that no
    longer apply ("all a and b" relaxes `b ≠ 0`).
  - The target statements are outside the unit, so this depends on RG-1.
  - Domains beyond statistics have the same pattern: "this clause does not apply to …".
- **Independent:** yes (A, B, P and H).

### SG-7 · No classes for the probability model a section works in

- **Units:** T1 s1–s3, the sample space, events, the probability measure and "defined on the
  probability space".
- **Hits:**
  - `unsupported` items: A 1 (covering s1–s2), B 2 (s1, s3), H 2 (s1, s3), reference 2.
  - P skipped the sentences as set-up (P notes).
  - Root decided it in r5; D7-gap 1 (whether s1 is a claim or motivation; see GG-8).
- **Quote (T1 s3):** "In this section, we assume that we fixed random variable \( Z \) defined on
  the probability space, with values in \( \R \)."
- **Proposal:** add a class `ProbabilitySpace` (local, like a random variable) and a predicate
  `defined_on`, with domain `RandomVariable` and range `ProbabilitySpace`.
  - The components (Ω, 𝓕, ℙ) become aliases of the space or symbol bindings; see SG-8.
- **Independent:** yes (A, B and H).

### SG-8 · No predicate for notation: "X denotes …" or "Ω is the set of outcomes"

- **Units:**
  - T1 s2, notation for the components.
  - U8 s6, "Let X denote the radius of the rod", which sits in the solution; also U8's standing
    context c2.
- **Hits:**
  - T1: B 1 and H 1 `unsupported` items; the reference kept B's item; D7-gap 1 ("§10.3 has no
    notation row").
  - U8: A, B and P left the radii without symbols. H took X and Y from the solution (notes of
    all four).
  - The `StatementKind` value `notation` exists, but no predicate goes with it.
- **Quote (T1 s2):** "So \( \Omega \) is the set of outcomes, \( \ms F \) the collection of
  events, and \( \P \) the probability measure on the sample space \( (\Omega, \mathscr F) \)."
- **Proposal:** add a core predicate `denoted_by`, with domain `Entity`, range `Formula`
  (the symbol) and default modality `conventional`.
  - Consolidation also turns the claim into an alias of kind `symbol`.
  - Add a guideline line: a symbol introduced in a solution or proof for a setup quantity is
    annotated as `denoted_by` on that quantity, cited in the solution, without annotating the
    solution's working.
- **Independent:** yes (B, H and D7; all four passes for U8).

### SG-9 · No relation between a family and its "standard" member when no constraint is stated

- **Units:** T4 (standard normal, standard lognormal), U6 (standard normal), U10 (standard
  gamma).
- **Hits:**
  - Every pass and the reference made the standard family a `DistributionFamily` with 0
    `special_case_of` claims. In T4, all four passes say in their notes that the constraint is
    not stated (guideline §10.4); H says so for U10 too.
  - For U6 s3, "constructed from a standard normal variable", A, B and H used a
    `transformation_of` without a `transform`. H explicitly weighed §10.5's rule against
    forcing a fact into a nearby predicate. P recorded 1 `unsupported` item.
  - See OPEN-D2-5 below.
- **Quote (U6 s3):** "Conversely, any normally distributed variable can be constructed from a
  standard normal variable."
- **Proposal:** add a predicate `standard_member_of`, with domain `DistributionFamily`, range
  `DistributionFamily` and an optional `param_constraints` qualifier, used when stated.
  - When the source names a construction, `member_of_construction` with `base` remains the
    precise form.
  - A guideline line: "a 'standard F' family gets `standard_member_of F` when the text
    relates them; `special_case_of` only when it states the constraint."
- **Independent:** yes (A, B, P and H).

### SG-10 · `RandomVariable` assumes a symbol or an expression

- **Units:** U7 ("a constant"), U8 ("the radius of the rod").
- **Hits:**
  - In U7, all four passes made a symbol-less `RandomVariable` and say in their notes that this
    is a guess.
  - In U8, A, B and P left the radii without symbols; H used X and Y from the solution.
- **Quote (U7 s1):** "In some settings, it's convenient to consider a constant as having a normal
  distribution (with mean being the constant and variance 0, of course)."
- **Proposal:** widen the class description to "a random variable denoted by a symbol, by an
  expression, or by a description in words, including a degenerate (constant) variable".
  - The identity key of a symbol-less local entity is its normalized label (D1 §10.1 already
    allows "symbol or label").
- **Independent:** yes (A, B, P and H).

### SG-11 · Qualifier semantics are undocumented: `param_symbols`, `base_variable`

- **Units:** T1.
- **Hits:**
  - P left `param_symbols` out because its meaning "is not defined" (P notes).
  - A, B and H used it with keys `location`/`scale` and formula values.
  - The values of `base_variable` take two shapes: A, B and H wrote `{t: entity, ref}`, P wrote
    `{ref}`.
- **Quote (T1 s4):** "For \(a \in \R\) and \(b \in (0, \infty) \), let \(X = a + b \, Z\)."
- **Proposal:** give every schema qualifier a description and a value example in the generated
  inventory (guideline §10.10), including whether a key is a canonical name or an entity.
- **Independent:** no (P only; the other passes' consistent use suggests their reading).

---

## 2. Guideline gaps

### GG-1 · Modality of "let"/"suppose"/"if" inside a definition (G2)

- **Units:** T1 s4; T4 s3–s4 (d22); U10 "if b ∈ (0, ∞)".
- **Hits:**
  - T1 `defined_as` for X: A `defined`/`definiens`, P `defined`/`definiens`, B
    `supposed`/`premise` and H `supposed`/`premise`. That is a 2–2 split. B, P and H flagged it
    in their T1 notes, and A flagged the same question for T4 s3–s4.
  - Root decided it in r1 (trace d2, d22); D7-gap 1.
  - H treated U10's "if b ∈ …" as a restriction, not a supposition.
  - Side effect: B's `supposed` reading forced an INV-06 reference, so B conditioned one
    stipulation on another (d6, "pass wrong").
- **Quote (T1 s4):** "For \(a \in \R\) and \(b \in (0, \infty) \), let \(X = a + b \, Z\)."
- **Proposal (G2, refined):**

  > Inside a definition, a "let", "suppose" or "if" clause about an entity *other than the one
  > being defined* is `supposed` (a premise). A clause that introduces the variable or formula
  > by which the defined entity is constructed, and every property the definition attaches to
  > the defined entity, is `defined` with role `definiens`. A membership clause on a symbol
  > ("if b ∈ (0, ∞)") is a restriction, not a supposition.

- **Independent:** yes (A, B, P, H, the root, D7 and the trace).

### GG-2 · Modality and anchor of structural claims: `defines`, `proves`, `refers_to`, `follows_from` (G4)

- **Units:** T1, T3, T4, U6 and U10.
- **Hits:**
  - Modalities of the `defines` claims:

    | Source | Modality | `defines` claims |
    |---|---|---|
    | A | `defined` | 4 |
    | P | `defined` | 5 |
    | H | `defined` | 2 |
    | B | default (`asserted`) | 4 |
    | Reference | default | 4 |
    | D7 | `defined` | 4 |

  - Root decided `asserted` in r3, r9, r19 and r21. D7 chose `defined` in 4 rows and marked the
    guideline as deciding it (D7). The two adjudicators read the guideline oppositely.
  - H has no `defines` claim in T4 or U10.
  - Trace differences d4, d16 and d20.
- **Quote (T1 s5):** "The two-parameter family of distributions associated with \(X\) is called
  the location-scale family associated with the given distribution of \(Z\)."
- **Proposal (G4, extended):**

  > Structural claims (`defines`, `proves`, `refers_to`, `follows_from`) are `asserted` and have
  > the defining, proving or referring statement as both subject and `statement`; they take no
  > `statement_role`. A definition unit carries one `defines` claim per entity it introduces,
  > whether or not it uses "is called".

- **Independent:** yes (A, B, P, H, the root, D7 and the trace).

### GG-3 · `statement_role` has no rule by statement kind and claim kind

- **Units:** T1, T2, T3, T4, U5, U6, U9 and U11.
- **Hits:**

  | Case | A | B | P | H | Root | D7 |
  |---|---|---|---|---|---|---|
  | Derived variable's `defined_as` in a theorem (T3, U5, U9, U11) | `definiens` ×4 | none ×4 | no claim | no claim | `definiens`, r8: "the guideline decides" | none ×4, D7-gap 4 |
  | Remark identities (T2) | none | `conclusion` | none | none | `conclusion`, r6 | none (D7) |
  | `parameter_domain` (T1) | `definiens` | `definiens` | `definiens` | `restriction` | `definiens` | `definiens` |

  - A definition's "then" clause (T4): P gave `conclusion`, the others `definiens` (d19).
  - T1 `defined_as` role: D7-gap 1. U6 s3 role: D7-gap 1.
  - Trace differences d7, d9, d13 and d19.
- **Quote (T3 s2):** "If \(a \in \R\) and \(b \in \R \setminus \{0\}\), then \(a + b X\) is
  normally distributed with mean \(a + b \mu\) and variance \(b^2 \sigma^2\)."
- **Proposal:** a role table in §10.3:
  - In a theorem or corollary, a premise gets `premise`, a conclusion `conclusion`, a
    restriction stated apart from any premise `restriction`, and the definition of a derived
    variable `definiens`.
  - In a definition, the supposed premises get `premise`; everything stipulated about the
    defined entity (formulas, parameters, roles, domains) gets `definiens`.
  - In a remark, narrative or convention, claims take no role.
  - Example and exercise claims get `example_value`.
  - Structural claims take none (GG-2).
- **Independent:** yes (A, B, P, H, the root, D7 and the trace).

### GG-4 · Where restrictions and premise references go (G3)

- **Units:** T1, T2, T4, U9, U10 and U11.
- **Hits:**
  - T1: where A, B, P and H put `claim` nodes on definiens claims.

    | Pass | `defined_as` conditions | `construction_formula` conditions |
    |---|---|---|
    | A | Z premise | — |
    | B | — | its own `defined_as` |
    | P | Z premise | Z premise |
    | H | — | Z premise and the "let" claim |

    The root decided neither (r2). D7 followed A (D7-gap 1), and marked a second D7-gap row for
    construction conditions.
  - Restrictions stated inside a premise:
    - T2: A, B and H put them on the supposed claim, because the unit has no conclusion.
    - T4: A and B put them on the conclusion; H and the trace on the premise (d18).
    - U10: P put them on the premise. U9 and U11: H put them on the premise; the others on the
      conclusion.
  - Trace difference d3.
- **Quote (T4 s1):** "Suppose that \(Y\) has the normal distribution with mean \(\mu \in \R\) and
  standard deviation \(\sigma \in (0, \infty)\)."
- **Proposal (G3, extended):**

  > A restriction written inside a premise ("mean μ ∈ ℝ") is a condition of that premise's
  > claim. A conclusion references its premises by `claim` nodes and repeats only restrictions
  > stated outside them. Definiens claims carry `claim` nodes only for premises of the same
  > definition that the text makes them depend on; a section-scoped supposition is not
  > referenced unless the definition restates it.

- **Independent:** yes (A, B, P, H, the root, D7 and the trace).

### GG-5 · Parameter naming: role word, symbol, or something stable across units (OPEN-D1-3)

- **Units:** T1, T2, T3, T4, U5, U8, U9 and U10.
- **Hits:**
  - Notes: A 3 (T1, T2, T4), B 3 (T1, T2, T4), P 5 (T1, T2, T3, T4, U9) and H 5 (T1, T2, T3,
    T4, U9).
  - Root decided it in r10 (redundant `parameter_role` kept); trace differences d8, d23 and d25.
  - See the OPEN-D1-3 block for the identities. In short:
    - A, B and the trace name the lognormal's σ `sigma`; P and H name it `shape`.
    - A and B apply the "later sentence" rule differently in T1 and T4 (A notes: "conflicts in
      spirit with T1").
    - `parameter_role` claims: A 3, B 4, P 6, H 4.
- **Quote (T4 s3):** "(a) The parameter \( \sigma \) is the shape parameter of the distribution."
- **Proposal:**

  > A family parameter's canonical name is the role word if the *unit* states it anywhere
  > (including a later sentence), else the source symbol without backslash (`mu`). The name is
  > spelled as the `ParameterRole` value (`standard_deviation`). A `parameter_role` claim is
  > added only when the role is stated and differs from the canonical name. Across units, the
  > canonical name of a family's parameter is fixed by the family's defining unit; later units
  > use it (the pipeline's consolidation, not the annotator, merges by `identical_parameter`).

  The last sentence needs RG-7.
- **Independent:** yes (A, B, P, H and the trace).

### GG-6 · Symbol binding when one symbol plays several parts (G1)

- **Units:** T1, T3, T4, U5, U10 and U11.
- **Hits:**
  - T1: `a` and `b` are `family_param` in A, B and P; H binds them `free` in `defined_as`
    and `family_param` in `construction_formula`; the trace binds them `free` (d1).
  - U10: A and B bind `b` `free` in the conclusion and `family_param` in `transform`, and both
    flag it in their notes. P binds it `param_of` its own conclusion; H binds it `free`.
  - U11: the shared scale `b` is `free` and `param_of` in A, B and H; `param_of` only in P.
  - P binds a premise's own symbols `param_of` the premise itself (T3, T4, U5), where A, B and
    H bind them `free`.
- **Quote (U10 s1):** "If \(Z\) has the standard gamma distribution with shape parameter \(k \in
  (0, \infty)\) and if \( b \in (0, \infty) \), then \(X = b Z\) has the gamma distribution with
  shape parameter \(k\) and scale parameter \(b\)."
- **Proposal (G1, extended):**

  > A symbol is `free` in the claim that introduces it. It is `param_of` a premise only where it
  > is used *after* that premise gives it as a parameter value. It is `family_param` where the
  > claim is about the family or construction (`construction_formula`, `transform`,
  > `derived_parameter`) and the unit names it a parameter. Within one statement, the same
  > symbol in claims of the same kind binds the same way.

- **Independent:** yes (A, B, P, H and the trace).

### GG-7 · Whether a formula object includes the generated variable (G5)

- **Units:** T1 (`construction_formula`) and T4 (`transform`).
- **Hits:**
  - All four passes, the reference and D7 write `a + b \, Z` and `e^Y`.
  - The trace (the design's own worked example) writes `X = a + b \, Z` and `X = e^Y` (d5, d21).
- **Quote (T4 s2):** "Then \(X = e^Y\) has the lognormal distribution with parameters \(\mu\) and
  \(\sigma\)."
- **Proposal (G5):** formula objects and `transform` exclude the left-hand variable. The
  variable is the claim's subject or its `base_variable`. Put the rule in the schema
  descriptions of `construction_formula` and `transform`, not only in the guideline.
- **Independent:** yes (the trace against the passes). The passes agree with each other, so the
  gap is in the design's own example.

### GG-8 · No threshold for what counts as an explicit claim in setup, framing and remarks

- **Units:** T1 s1–s3, T2 (`has_parameter`), U7 s3–s4, U8 s1 and U10 (`has_parameter`).
- **Hits:**
  - T1: A 1, B 3 and H 3 `unsupported` items; P recorded none.
  - U8 s1: B 1 `unsupported` item; the reference kept it.
  - D7-gap 2 (T1 s1 "framing or motivation"; U8 setup sentence).
  - T2 `has_parameter` for "the normal distribution with location parameter μ": the trace has it,
    no pass does (d12). All four passes explain the omission in their notes.
  - U10: A, B and P record `has_parameter` from "with shape parameter k"; H does not, citing
    the same reason as for T2.
  - U7 s3–s4: all four passes recorded `unsupported` items, although §10.3 limits remarks to
    "parameter identities, memberships, special cases".
- **Quote (U8 s1):** "A metal rod is designed to fit into a circular hole on a certain assembly."
- **Proposal:**

  > A sentence is a claim if it relates two identifiable things (entities, values, statements)
  > in a way a consumer could query, whether or not a predicate exists; record it as
  > `unsupported` when none fits. Pure motivation ("this convention simplifies …"), framing
  > ("as usual") and physical scene-setting without a quantity are skipped. "F with ⟨role⟩
  > parameter k" states `has_parameter` only in a definition of F; elsewhere it supplies
  > `param_values` only.

- **Independent:** yes (A, B, H, D7 and the trace).

### GG-9 · Restrictions in a premise against "do not state derived facts"

- **Units:** T4 and U10. The `parameter_domain` of the defined family is taken from the
  restrictions on the *base* family's parameters.
- **Hits:**
  - `parameter_domain` claims: A 6, B 6, P 0, H 2 (T1 only), reference 6.
  - A and B carried them over and flagged it in their notes (T4, U10); trace difference d24.
- **Quote (U10 s1):** see GG-6.
- **Proposal:**

  > A definition's parameter domains are stated when the defining sentence restricts the
  > symbols that become the defined family's parameters, even if the restriction is written on
  > the premise; this is a reading of the stated text, not a derived fact. Facts that need a
  > computation (σ from σ², a standard deviation from a variance) remain derived.

- **Independent:** yes (A, B and the trace; P and H show the alternative in their data).

### GG-10 · The same stated fact in two predicate forms

- **Units:**
  - U5: `has_distribution` `param_values` {mean, variance} plus `mean_value` and
    `variance_value` from the (a)/(b) items.
  - U6: `defined_as Z` plus the concept's `definition_formula`.
  - U10: `defined_as X = bZ` plus the scale value in `has_distribution`.
- **Hits:**
  - U5: all four passes and the reference record both forms, and all four flag it in their
    notes.
  - U6 and U10: H flags it.
- **Quote (U5 s3):** "(a) \(\E(X_1 + X_2) = \mu_1 + \mu_2\)"
- **Proposal:**

  > When one sentence states a value both as a distribution parameter and as an explicit
  > equation for a property, record both: they are different predicates and the property claim
  > has its own evidence. Mark nothing as an alternative. Consolidation links them (D5
  > `equivalent_to` within a statement).

  D5 §5.4 should say that such pairs never form a slot (they don't today, as the predicates
  differ), and the scoring should not count them as duplicates.
- **Independent:** yes (A, B, P and H).

### GG-11 · Segmentation of a mixed paragraph into statements, and the kind of each statement

- **Units:** T1, T2, T4 and U6.
- **Hits:**
  - Statement kinds chosen:

    | Unit | A | B | P | H | Reference | D7 |
    |---|---|---|---|---|---|---|
    | T1 lead-in | `assumption` | `assumption` | `assumption` | `narrative` | — | — |
    | T2 | `narrative` | `remark` | `assumption` + `remark` | `narrative` | — | — |
    | T4 | 1 `definition` | 1 `definition` | 3 statements, `assumption` + 2 × `definition` | 1 `definition` | — | — |
    | U6 | 1 statement | 2 | 2 | 3 | 2 | 3 |

  - Root decided it in r6 and r13; D7-gap 1 (U6); trace difference d11 (remark against
    narrative).
- **Quote (U6 s2):** see SG-5.
- **Proposal:**

  > A unit or paragraph yields one statement per self-identified kind ("A corollary of …",
  > "Recall that …", "it's convenient to consider" → convention). Otherwise one statement per
  > unit. `remark` is a paragraph that states a result or identity; `narrative` is one that
  > states none of the §10.3 captures; `assumption` is a paragraph whose only content is a
  > section-level supposition.

- **Independent:** yes (A, B, P, H, the root, D7 and the trace).

### GG-12 · Recalled or restated definitions

- **Units:** U6 s1, and U5 standing context c2.
- **Hits:**
  - P and H made a `defines` claim for the standard score; A, B and the reference made a
    `refers_to` claim.
  - All gave the definition formula modality `defined`.
  - A and B say in their notes that §10.6 does not cover "Recall"; P makes the same point
    (point 1).
  - Statement kind: `narrative` (A), `remark` (B, P, reference, D7), `definition` (H).
- **Quote (U6 s1):** see SG-4.
- **Proposal:**

  > "Recall that …" restating a definition from elsewhere is a `remark` with `refers_to` the
  > concept, plus the restated definitional claims with modality `defined` (they are the
  > definition's content). It carries no `defines` claim; the defining statement is elsewhere
  > (RG-1).

- **Independent:** yes (A, B, P and H).

### GG-13 · Random variables denoted by expressions

- **Units:** T3 (`a + b X`), U5 and U11 (`X_1 + X_2`), U9 (`\prod X_i`).
- **Hits:**
  - Three representations:
    - A, B, the reference and D7: `symbol` = the expression, plus a `defined_as` claim.
    - H: `symbol` = the expression, no `defined_as` (4 units).
    - P: no `symbol` and no `defined_as` (3 units; in U9 P labelled the product "product of
      X_i").
  - The trace gives no symbol (d14).
  - The expression-variable cases of GG-3 and D7's span decisions (5 rows) follow from this.
- **Quote (U5 s2):** "Then \(X_1 + X_2\) is normally distributed with"
- **Proposal:**

  > A random variable written as an expression gets a local `RandomVariable` whose `symbol` is
  > the expression as written and one `defined_as` claim (role per GG-3) citing the expression
  > span; its other claims bind the expression's variables through that claim.

- **Independent:** yes (A, B, P, H and the trace).

### GG-14 · Standing context, section-binding cues and scope anchors outside the unit

- **Units:** T1, T2, U12, plus U5, U8, U9 and U11 (irrelevant standing context).
- **Hits:**
  - T2: the section's first binding is outside the unit. A and B anchored on s1, P left the
    anchor unknown and H gave no anchor; all four discuss the anchor in their notes.
  - U12: the governing supposition exists only in the standing context.
    - All four passes bound `k` `unresolved` and left the conclusions unconditional (notes of
      all four).
    - X's extent is `section` in A, B and H and `statement` in P.
  - T1: P notes that "In this section, we assume" is not one of §10.4's cue phrases. In U12, B
    notes that the context sentence has no cue at all.
  - Standing context that binds nothing in the unit: U5, U8, U9 and U11 per A; U8 per B, P and
    H.
  - Bears on OPEN-D1-2 and OPEN-D1-4.
- **Quote (U12 s1):** "The mean and variance of \( X \) are"
- **Proposal:**

  > §10.4: section-binding cues are "again", "in this section", "throughout", and any
  > supposition in a lead-in paragraph or subsection opening that later units use without
  > rebinding. §10.2: a supposition in the standing context that governs the unit is cited, not
  > re-annotated: conclusions reference it by an external claim reference (RG-1) and symbols
  > bind `param_of` that reference. The packet builder includes in the standing context only
  > section bindings in force at the unit.

  The last sentence is a packet fix, not a guideline fix.
- **Independent:** yes (A, B, P and H).

### GG-15 · Evidence-span conventions for structural, supposed and derived-variable claims

- **Units:** T2, T3, T4, U5, U6, U8, U9, U10 and U11.
- **Hits:**
  - `proves` span:
    - T3: A, B and P each chose the closing clause and flagged it in their notes.
    - U8: A cited s6, B s7; D7-gap 1.
    - U9: A cited s4, B s3.
  - D7 rows that are span conventions, all marked D7: 7 rows keep the supposition marker
    ("Suppose that", "If") out of the primary span (T2, T3, T4, U5, U6, U10, U11), and 5 rows
    narrow a `defined_as` claim's span to the expression (T3, U5, U6, U9, U11).
- **Quote (T3 s3):** "… which we recognize as the MGF of the normal distribution with mean \(a +
  b \mu\) and variance \(b^2 \sigma^2\)." The sentence is shortened here; the full s3 contains
  the display.
- **Proposal:**

  > The primary span of a claim excludes its introducer ("Suppose that", "If", "Then"); cite
  > the introducer as `supporting` when it determines modality. A `defined_as` claim cites the
  > expression and the formula. A `proves` claim cites the proof's or solution's concluding
  > clause (the result it reaches), not its first step.

- **Independent:** yes (A, B, P and D7).

### GG-16 · Hedge or condition for restricting phrases ("In some settings")

- **Units:** U7.
- **Hits:**
  - A, B and the reference recorded a `phrase` condition (A flags the choice against a hedge in
    its notes); P and H recorded neither a hedge nor a condition.
  - `hedge` is used 0 times in all batches.
- **Quote (U7 s1):** see SG-10.
- **Proposal:**

  > A phrase that limits where or when a claim holds ("in some settings", "for large n") is a
  > `phrase` condition. A phrase that weakens the author's commitment ("typically",
  > "approximately") is a `hedge`.

- **Independent:** partly (A, with B's data in agreement; P and H silent).

### GG-17 · The model-facing format leaves value shapes open

- **Units:** all of them.
- **Hits:**
  - Entity-valued identity slot: P wrote `{"ref": …}` in every `family` slot; A, B and H wrote
    plain strings.
  - Symbol-map keys: P used LaTeX (`\mu`); A, B and H used plain names (`mu`); P's canonical
    names include `\mu`.
  - Aliases: the format accepts plain strings only, so D1 §4.1's alias kinds are lost (P notes).
  - Spelling of the `scope` qualifier (P notes); spelling of a multi-word canonical name (A and B
    notes).
- **Quote:** not applicable (format).
- **Proposal:** in format.md and the generated JSON Schema:
  - give the exact shape of entity-valued identity slots (a local-ref string);
  - key symbol maps by the LaTeX symbol without backslash;
  - give aliases as `{text, kind}`;
  - give `scope` as an enum string in batches;
  - use canonical names in `ParameterRole` spelling.
- **Independent:** yes (P's notes; A and B on spelling; the data show the divergence).

---

## 3. Representation gaps

### RG-1 · No reference to statements, claims or entities outside the unit

- **Units:** U6 ("the last result"), U7 ([14], [17], [23], [24], [26]), U9 ("definition [1]"),
  U12 (the standing premise and "[3]").
- **Hits:**
  - U6:
    - A and B each declared a stand-in local `Statement`. The root kept B's (r15); D7-gap 1 for
      its label.
    - P and H resolved "the last result" to the unit's own s1. A's notes identify it as the
      linear-transformation theorem (T3).
  - U7: A made 5 `refers_to` claims to stand-in statements; B, P and H made none. The root
    dropped them (r16). D7 kept them, with D7-gap 2: one row for using `refers_to` on a
    convention, one for the stand-ins' labels.
  - U12: all four passes left the conclusions without their premise (see GG-14).
  - Notes: A 3, B 3, P 4 and H 4 units.
- **Quote (U7 s3):** "Of course, the formulas for the probability density function [14] and the
  distribution function [17] do not hold for a constant, but the other results involving the
  moment generating function [23], linear transformations [24], and sums [26] are still valid."
- **Construct needed:** an *external reference* value, `{t: "extref", target: <anchor>, kind:
  statement | claim | entity}`.
  - The target is a segment key, an author-markup link target or element id (D1 §3.2 keeps
    them), or a numbered label.
  - The construct is usable as a claim object (`follows_from`, `refers_to`, SG-6), as a `claim`
    node in condition trees, and as a binding target (`param_of` an external claim).
  - Consolidation resolves it to a key and reports an unresolved one, like an `unresolved`
    binding.
  - It also closes a silent hole: a claim whose premise is an unresolved external reference
    must count as conditional, which INV-09 does not cover today. This applies to U12.
- **Independent:** yes (A, B, P, H, the root and D7).

### RG-2 · Indexed families of variables and quantified premises

- **Units:** U5 and U11 ({1, 2}), U9 ({1, …, n}).
- **Hits:**
  - Four forms of the same premise:

    | Form | Sources |
    |---|---|
    | One `X_i` claim with `member(i ∈ …)` on the premise | A, reference |
    | `forall i ∈ …` wrapping a `claim` node in the conclusion | B; D7 combined it with A's `member` |
    | A flat `member(i ∈ …)` in the conclusion with `i` unbound | P |
    | Two expanded premises on X₁, X₂ | H |

  - H's expansion wrote LaTeX the source does not contain (`\mu_1`, `\sigma_1^2`), against
    §10.7's copy-exactly rule.
  - Instance bindings: A, B and P bound μ₁ and μ₂ `param_of` the `X_i` premise. A and B say in
    their notes that the binding kinds have no index instantiation, so this is approximate.
  - Independence of a sequence:
    - A, B, the reference and D7: `independent(X_1, X_2, X_n)`. The validator rejected the
      single sequence argument that A and B first gave.
    - P: `independent(X_1, X_n)`.
    - H: an `unsupported` condition leaf on 2 claims.
  - Root decided it in r12, r18 and r20; D7-gap 3 (U5, U9, U11), with D7 choosing the other
    form (B's `forall`); witness W4.
- **Quote (U9 s1):** "Suppose that \(n \in \N_+\) and that \((X_1, X_2, \ldots, X_n)\) is a
  sequence of independent variables, where \(X_i\) has the lognormal distribution with
  parameters \(\mu_i \in \R\) and \(\sigma_i \in (0, \infty)\) for \(i \in \{1, 2, \ldots,
  n\}\)."
- **Construct needed:**
  1. An *indexed local entity*, `X_i` with `index: i` and `index_set`, plus an `instance_of`
     link from the entities X₁ and X₂ to it.
  2. A `forall` node whose body may be a `claim` node, so that a premise claim on `X_i` holds
     for every index. D1 §7 does not say this today; A reads it as not allowed, and B and D7
     as allowed.
  3. A binding kind `instance_of_param`: "μ₁ is μ_i at i = 1".
  4. Condition predicates that accept an indexed set argument (base, index, range) in place of
     2+ entities.
  - A guideline line then fixes one form.
- **Independent:** yes (A, B, P, H, the root, D7 and the witness).

### RG-3 · No binding kind for a variable bound inside the formula

- **Units:** U9 (Σ and ∏ over i; the bound n); proofs in U12 and U11 (∫ … dx), not annotated in
  v0.
- **Hits:** A and H flag it in their notes. A, B, H, the reference and D7 bind `i` `free`; P
  leaves `i` out of the symbol map in U9.
- **Quote (U9 s2):** "Then \(\prod_{i=1}^n X_i\) has the lognormal distribution with parameters
  \(\mu\) and \(\sigma\) where \(\mu = \sum_{i=1}^n \mu_i\) and \(\sigma^2 = \sum_{i=1}^n
  \sigma_i^2\)."
- **Construct needed:** a `BindKind` value `bound` (bound by an operator in the same formula:
  sum, product, integral, set-builder). It is excluded from completeness metrics, which today
  count it as `free`.
- **Independent:** yes (A and H).

### RG-4 · No local symbol definitions ("where μ = …") inside a claim

- **Units:** U9.
- **Hits:**
  - P and H each recorded 1 `unsupported` item.
  - A, B, the reference and D7 wrote the equations as `cmp =` nodes in the condition tree.
  - A's notes say that neither §10.5 nor §10.7 covers "where" clauses. A and B kept Σμᵢ out of
    `param_values` so as not to derive σ = √(Σσᵢ²).
  - P and H found no predicate for the equations. P's notes reject a `cmp` because the equations
    "state values rather than restrictions".
- **Quote (U9 s2):** see RG-3.
- **Construct needed:** a `SymbolBinding` kind `defined_by`, with a `formula` field (the
  right-hand side, or the equation when the left side is an expression of the symbol, as with
  σ²).
  - A condition tree states *when* a claim holds; a `where` binding states *what a symbol
    means*.
  - Equations given as definitions stay out of z3 consistency checks as restrictions.
- **Independent:** yes (A, B, P and H).

### RG-5 · `param_of` binds only to a `has_distribution` value

- **Units:** U6 (μ is X's mean via a `mean_value` premise), U12 (k, through RG-1).
- **Hits:**
  - A explains in its notes that μ had to be bound `free` because `param_of` refers only to
    `has_distribution` claims.
  - μ is `free` in U6 in all six batches.
- **Quote (U6 s1):** see SG-4.
- **Construct needed:** generalize `param_of` to `value_of`: a claim ref, plus an optional
  `param` key when the claim's object is a map, for any claim whose object or qualifier holds
  the symbol's value.
- **Independent:** no. Only A raised it in its notes; the other batches show the same `free`
  binding without comment.

### RG-6 · A local entity's extent cannot cover a run of sibling statements

- **Units:** U6. X and Z are bound in the s1 remark and used again in the s2 corollary.
- **Hits:** B, P and H flag it in their notes; all batches give `statement` extent, which is
  wrong for one of the two statements.
- **Quote (U6 s2):** see SG-5.
- **Construct needed:** an extent `unit`, or an explicit list of statements, between
  `statement` and `section` in D1 §4.2 and `ScopeExtent`. This bears on OPEN-D1-2.
- **Independent:** yes (B, P and H).

### RG-7 · No notion of a family's parameterizations

- **Units:** T2, T3, T4, U5, U7 and U8 (normal), T4 and U9 (lognormal).
- **Hits:**
  - Key sets for the normal family, identical in all four passes and the reference:

    | `param_values` keys | Units |
    |---|---|
    | {location, scale} | T2 |
    | {mean, variance} | T3, U5 |
    | {mean, standard_deviation} | T4, U8 |
    | {variance} | U7 |

  - No batch declares a `FamilyParameter` with canonical name `variance`, so the `variance` key
    names no entity.
  - `identical_parameter` links only location ≡ mean and scale ≡ standard_deviation (T2).
  - P (T2, T3, T4) and H (T2, T3) flag the clash in their notes, and P asks for "a single
    canonical name per family parameter".
- **Quote (T2 s2):** "As the notation suggests, the location and scale parameters are also the
  mean and standard deviation, respectively."
- **Construct needed:** a `Parameterization`: a named, ordered set of a family's parameters,
  such as normal(mean, variance), normal(location, scale) or lognormal(μ, σ).
  - It is a global entity, or an identity qualifier of `has_distribution` and `param_values`.
  - The validator checks `param_values` keys against the parameterization's parameters.
  - Relations between parameterizations (variance = scale²) are derived claims.
  - Standard members can be expressed as fixed points of a parameterization, which is the
    second option of OPEN-D2-5.
- **Independent:** yes (P and H; data in all passes).

---

## 4. Evidence for the OPEN items

### OPEN-D2-4 · Property predicates or one `has_property`

- **Property predicates used:** the schema declares six on `Distributed` (`support`, `pdf`,
  `cdf`, `mgf`, `mean_value`, `variance_value`) plus `definition_formula` on `Concept`.

  | Predicate | Claims in each of A, B, P, H, reference, D7 | Units |
  |---|---|---|
  | `mean_value` | 3 | U5, U6, U12 |
  | `variance_value` | 2 | U5, U12 |
  | `definition_formula` | 1 | U6 |
  | `support`, `pdf`, `cdf`, `mgf` | 0 | — |

  Two distinct distribution properties are used.
- **Property-like predicates also used:** `takes_values_in` 1 claim (T1) in every batch;
  `parameter_domain` A 6, B 6, P 0, H 2, reference 6.
- **Unsupported items that are properties:**
  - The standard deviation of a random variable (U6): `unsupported` items in A, P, H and the
    reference; condition leaves in A, B, the reference and D7 (SG-4).
  - Close to properties:
    - "with mean being the constant" (U7, all passes): a value-form limit, SG-3.
    - "σ² = Σσᵢ²" (U9, P and H): a symbol-definition limit, RG-4.
    - "the formulas for the pdf [14] and cdf [17] do not hold" (U7, all passes): property
      *names* in a statement-scope claim, SG-6.
- **Properties in the text but out of scope:** the MGF is stated only in proofs (T3 s3, U5 s5,
  U11 s3), and E(X²) only in U12's proof. The brief's examples U12 `mom1`, skewness and kurtosis
  do not occur in S0's U12, which states only the mean and variance.
- **The same quantity in three constructs:**
  - "mean" appears as a `param_values` key (T3, T4, U5, U8), as a `FamilyParameter` (T2) and
    as a property predicate (`mean_value`).
  - In U5, all four passes state it twice (GG-10).
  - "standard deviation" has the first two forms but no predicate.
- **Reading:**
  - The text uses few properties, and one of them (the standard deviation) is missing from the
    schema.
  - The overlap with parameter names argues for one shared quantity vocabulary, whichever
    predicate form is chosen.
  - Twelve units are too few to count properties: S0 does not decide the question.

### OPEN-D2-5 · How "standard normal", "standard score" and "standard gamma" were represented

| Item | A | B | P | H | Reference |
|---|---|---|---|---|---|
| Standard normal (T4, U6), standard lognormal (T4), standard gamma (U10) | `DistributionFamily` ×4 | same | same | same | same |
| `special_case_of` to the general family | 0 | 0 | 0 | 0 | 0 |
| T4 `transformation_of` SLN → SN, transform `e^Z` | yes | yes | no | no | yes |
| U10 `transformation_of` gamma → standard gamma, transform `b Z`, mapping {shape: shape} | yes | yes | no | no | yes |
| U6 `transformation_of` normal → SN, no transform | yes | yes | `unsupported` | yes | yes |
| Standard gamma carries a parameter (`param_values` {shape: k}) | yes | yes | yes | yes | yes |
| "Standard score" | `Concept`, `refers_to` + `definition_formula` | same, plus `unsupported` "is the standard score of X" | `Concept`, `defines` + `definition_formula` | same as P | as B |
| Trace (T1–T4) | — | — | — | — | omits T4 s5, so it has no standard lognormal (d17); the witness requires it |

- **Agreement:** every annotator agrees on "family, no `special_case_of`", because §10.4 asks
  for the constraint only when it is stated, and no unit states μ = 0, σ = 1.
- **What breaks:**
  - Nothing connects SN to N in T4 except through the lognormal pair.
  - The standard gamma is a parameterized family, so "standard" does not mean "parameter-free".
  - A parameterization reading must allow a standard member that fixes only some parameters
    (scale 1, shape free).
- **Remedies:** SG-9 (a relation usable without a stated constraint) and RG-7 (the
  parameterization form). "Standard score" is a `Concept` in every pass, and the open issue there
  is SG-5, not D2-5.

### OPEN-D5-1 · Two claims with the same subject and predicate in one statement

Same statement, subject and predicate, different objects, in the reference:

| Unit | Subject | Predicate | Objects |
|---|---|---|---|
| T1 | LS | `has_parameter` | location, scale (2) |
| T4 | LN | `has_parameter` | mu, sigma, scale (3) |
| T4 | the definition statement | `defines` | LN, SLN (2) |
| U10 | G | `has_parameter` | shape, scale (2) |

- **Effect of D5 §5.4:** all four are entity-valued and non-functional, so the slot includes the
  object core and none of them becomes an alternative group. A, B, P and H have the same
  pattern; A also has 5 `refers_to` claims in U7, entity-valued as well.
- **Formula predicates:** no subject has the same formula predicate twice, in the reference or in
  any pass, within a statement or across the unit. The predicates checked were `defined_as`,
  `construction_formula`, `definition_formula`, `derived_parameter`, `mean_value`,
  `variance_value`, `pdf`, `cdf`, `mgf`, `support`, `takes_values_in` and `parameter_domain`.
  `pdf`, `cdf` and `mgf` are not used at all.
- **Functional `has_distribution`:** never occurs twice for one subject in one statement.
- **Nearest case:** U5's `has_distribution` {mean, variance} and its `mean_value`/`variance_value`
  restate one fact under different predicates. They fall into different slots, so they neither
  fuse nor compete (GG-10).
- **Reading:** S0 does not exercise OPEN-D5-1. A unit with a piecewise pdf, or with two
  equivalent forms of one formula ("equivalently, …"), is needed.

### OPEN-D1-3 · Parameter identity: role or symbol

| Family | A | B | P | H | Reference | Trace |
|---|---|---|---|---|---|---|
| Location-scale (T1) | location, scale | same | same | same | same | same |
| Normal (T2) | location, scale, mean, standard_deviation | same | same | same | same | same |
| Lognormal (T4) | mu, sigma, scale | mu, sigma, scale | `\mu`, shape, scale | mu, shape, scale | mu, sigma, scale | mu, sigma, scale |
| Gamma (U10) | shape, scale | same | same | none declared | shape, scale | — |
| Lognormal `param_values` keys (T4, U9) | {mu, sigma} | {mu, sigma} | T4 {`\mu`, shape}, U9 {`\mu`, `\sigma`} | {mu, shape} in both (U9 from the page's context) | {mu, sigma} | — |
| T4 `param_mapping` | {mu: mean, sigma: standard_deviation} | same as A | {`\mu`: mean, shape: standard_deviation} | none | same as A | same as A |

- **Agreement:**
  - A, B, the reference and the trace agree everywhere: when a role is named in a later
    sentence, T1 uses the role word and T4 uses the symbol.
  - P and H apply the role word whenever the unit states it (`shape` from T4 s3), and the
    symbol otherwise (μ).
  - P is inconsistent across its own units (T4 `shape`, U9 `\sigma`) and uses LaTeX names.
- **Role and symbol together:**
  - Every pass adds `parameter_role` claims that repeat a role-word canonical name: in T1 all
    four; in T4 B, P and H for scale; in U10 P only.
  - All four flag the redundancy in their notes.
- **Reading:**
  - Neither rule gives stable identities across units by itself: a family's σ is `sigma` in
    one unit and `shape` in another, depending on what each unit states.
  - The normal family's keys vary by parameterization (RG-7).
  - The evidence favours GG-5: the role word if the unit states it, the canonical name fixed
    by the family's defining unit, and RG-7 for parameterizations.

---

## 5. The ten gaps to fix first

Ranked by the units and passes they affect and by how far they generalize beyond this text.

| Rank | Gap | Units | Sources | Why first |
|---|---|---|---|---|
| 1 | RG-1 external references | U6, U7, U9, U12 | A, B, P, H, root, D7 | Every cross-referencing document. Today it causes wrong referents (P and H in U6) and silently unconditional conclusions (U12, all passes) |
| 2 | GG-3 statement roles by kind | 8 units | A, B, P, H, root, D7, trace | Domain-independent. Root and D7 decided it oppositely |
| 3 | RG-2 indexed families and n-ary independence | U5, U9, U11 | A, B, P, H, root, D7, witness | Four incompatible forms. Forces invented LaTeX (H) and truncated arguments |
| 4 | GG-5 parameter naming (with RG-7) | 8 units | A, B, P, H, trace | Global entity identity across units. Decides OPEN-D1-3 |
| 5 | GG-2 structural-claim modality (G4) | T1, T3, T4, U6, U10 | A, B, P, H, root, D7, trace | Every definition and proof in every domain. Root and D7 decided it oppositely |
| 6 | GG-1 modality inside definitions (G2) | T1, T4, U10 | A, B, P, H, root, D7, trace | 2–2 split among the passes. Interacts with INV-06 |
| 7 | SG-3 `ParamValue` range | U7, U8 | A, B, P, H, root, D7, witness | Units and entity values occur in any applied text. The design's own D1 example is rejected |
| 8 | GG-4 restriction placement (G3) | 6 units | A, B, P, H, root, D7, trace | Decides condition trees, so it drives z3 checks and scoring |
| 9 | SG-1 posed quantity | U8, and every exercise | A, B, P, H, witness | The guideline asks for `posed` claims the schema cannot hold: 0 in every batch |
| 10 | GG-11 statement segmentation and kind | T1, T2, T4, U6 | A, B, P, H, root, D7, trace | Statements are the home of every claim (D1 §4.3); no two passes segmented U6 alike |

Next in line: GG-13 expression variables (4 units, three forms), SG-2 independence as a claim
(U8, all passes, the witness), GG-14 standing context (U12, all passes), and SG-9 standard
members (OPEN-D2-5).

---

## 6. Inputs not interpreted, and excluded points

- **`trace_diff.md` counts:** the summary says twelve of the 22 defensible differences come from
  G1–G5, but the file's own rule table, and the `(Gn)` tags in its difference tables, list ten
  ids (d1, d2, d22, d3, d18, d4, d16, d20, d5, d21). The ten are used here.
- **The S0 brief** (`S0-reference-annotations.md` §5) names U12 `mom1`, skewness and kurtosis
  as property evidence. U12's packet states only the mean and variance, so those items do not
  exist in S0.
- **Excluded as packet defects** (not schema, guideline or representation gaps):
  - U8's header says "statement kind: theorem", but the text is an exercise (flagged by A, B
    and H; all four passes used `exercise`).
  - Standing context that belongs to other units (U5, U8, U9, U11). The guideline side of it is
    in GG-14.
  - Source typos ("to big", "Generlization"); spacing and `\gt` quote-tier notes.
- **Validator-forced edits:**
  - `pass_p/first/U5.json` and `pass_h/first/U9.json` are not valid JSON.
  - The first and final batches differ for 11 A units, 3 B units, 12 P units and 12 H units.
  - The changes this analysis relies on (units in U8, the sequence argument of `independent` in
    U9, aliases as strings, INV-06 scoping) are those the pass notes describe. The first
    versions were not diffed field by field.
