# S0-C · Passes A and B against the old-repository witness

**Done:** 2026-10-28, by the root, by hand. **Witness:**
`corpus-intelligence/fixtures/siegrist_three_sections/expectations.toml` (revision
`siegrist-three-sections-expectations@2`, coordinator-authored 2026-10-18/24 by reading the
source; read by the root only, never shown to an annotator). It addresses elements by the old
adapter's ids, so targets are mapped to S0 units by their quotes. The witness states parts,
roles and required distinctions in the old representation's terms; it is compared at that level,
not claim by claim. Quotes are not reproduced here beyond identifying phrases.

## Summary

Eleven witness targets cover core units. Both passes satisfy every required distinction and
avoid every forbidden association the witness states, with four exceptions that are the same in
A and B and are representation limits, not annotation choices: units on numbers, independence as
a stated fact, a posed probability, and independence over an indexed sequence. The witness also
sides with the passes against the trace on T4's standard-lognormal sentence (trace diff d17). The
witness was written independently of this design, so the agreement is evidence that the passes'
readings are not an artefact of guideline v0.

## Targets

| Witness target | Unit | Required distinction | A | B | Note |
|---|---|---|---|---|---|
| `locationscale-definition` | T1 | Parts lead-in + definition; restrictions `a ∈ ℝ`, `b ∈ (0, ∞)`, Z fixed and real-valued; a → location, b → scale; not a numbered distribution | yes | yes | Both as `FamilyConstruction`, with `parameter_role` claims and `family_param` bindings |
| `lognormal-definition` | T4 | Y normal (mean μ, sd σ); X = e^Y lognormal (μ, σ); shape σ and scale e^μ (old outcome: outside the representation) | yes | yes | Shape and scale are ordinary claims now, as the trace intends |
| `standard-lognormal-definition` | T4 (s5) | Standard lognormal defined from the standard normal | yes | yes | The trace omits it (d17) |
| `normal-parameters-respectively` | T2 | μ ↔ location ↔ mean, σ ↔ scale ↔ sd; never location ↔ sd; "location" never a parameter value | yes | yes | |
| `normal-affine-nonzero-scale` | T3 | Restrictions `a ∈ ℝ`, `b ∈ ℝ ∖ {0}`; mean a + bμ, variance b²σ²; never sd = bσ or b²σ²; proof linked | yes | yes | Neither states the derived sd (left to the pipeline) |
| `missed-participant-affine` | T3 | `a + b X` is a participant | yes | yes | A local entity in both |
| `normal-sum-independent-pair` | U5 | Explicit pair X₁, X₂; `independent`; one premise governs both list conclusions and each Xᵢ's normality | yes | yes | A conditions the premise on `i ∈ {1, 2}`; B uses `forall i ∈ {1, 2}` over the premise claim |
| `standard-score` | U6 | Standard normality of Z only under the normality premise, never unconditional | yes | yes | Both condition the conclusion on `claim` of the premise |
| `degenerate-normal-convention` | U7 | Convention modality; the variance-0 member kept, not clamped or rejected | yes | yes | Both `conventional`; "mean being the constant" and the validity remarks are `unsupported` in both |
| `rod-hole-two-populations` | U8 | Two populations with their own means and sds (units cm); independence; the sought event; no swapped values | partly | partly | Means, sds, family, no swaps: yes. Units: A writes "1 cm" inside a formula, B drops cm to `unsupported` (`param_values` takes formulas only). Independence and the sought probability: `unsupported` in both. The numeric result is out of scope in v0 |
| `lognormal-product-indexed-family` | U9 | Indexed sequence X₁…Xₙ, i ∈ {1, …, n}; `independent`; product | partly | partly | Both write `independent(X_1, X_2, X_n)`: the condition needs at least two explicit arguments, so the ellipsis is lost |

Targets outside the core units (`locationscale-special-families`, `normal-as-location-scale-family`,
`theorem-with-details-proof`, the beer, peach and income exercises, `lognormal-mu-scale-discrepancy`)
are not compared.

## Representation limits the witness exposes

| Limit | Units | Design owner | Proposal |
|---|---|---|---|
| A parameter value with a unit ("mean 1 cm") | U8 | D2 §9 `ParamValue`, D1 §6 | `param_values` entries accept number values with units (D1 §6 already uses this sentence as its number example) |
| Independence stated as a fact, not a condition | U8 | D2 §9 | An `independent_of` claim predicate (or a `posed`/`exemplified` independence claim) mirroring the condition predicate |
| What an exercise asks for: a probability of an event | U8 | D2 §9, guideline §10.3 | A `posed` claim whose object is an event formula (`\P(Y - X \lt 0)`) |
| Independence over an indexed sequence | U9, (U5) | D1 §7 | An indexed-set argument for `independent` (base, index, range), as the witness's `subject_set` |
