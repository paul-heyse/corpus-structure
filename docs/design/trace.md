# Worked trace

**Proposed (2026-10-28).** Four Siegrist units carried through the design as exact data. Each
D-document refers to these units when it specifies behaviour, and phase 0 uses them as acceptance
tests ([D9 §5](D9-repository-and-phase0.md#5-phase-0-build-plan)). They are the first
development-split goldens; they are **not** a test split, because the design was written against
them.

The claims follow guideline v1 (D2 §10). The model-facing batches that spike S0-R2 checked for the
same units are `../design_review/evidence/2026-10-28_design-spikes/results/s0r2/reference_model_v1/T1.json`…`T4.json`; where a detail here is
abbreviated, those batches are exact.

The units map to expectations already settled in the previous repository
(`fixtures/siegrist_three_sections/expectations.toml`), so the source readings are not new
judgments:

| Unit | Expectation id (old repo) | Page | Exercises |
|---|---|---|---|
| T1 | `locationscale-definition` | `special/LocationScale.html` | A definition split across a lead-in and a paragraph; a construction that is not a family; parameter roles and domains |
| T2 | `normal-parameters-respectively` | `special/Normal.html` | "Respectively" pairing; family-level parameter identities; a section-level supposition |
| T3 | `normal-affine-nonzero-scale` | `special/Normal.html` | A theorem with a premise, restrictions, a derived variable, a conclusion, symbol bindings, a proof and a derived standard deviation |
| T4 | `lognormal-definition` | `special/LogNormal.html` | A family defined by transformation; parameters named by symbol; shape and scale roles stated afterwards |

**Acceptance by phase.** Phase 0 checks every target below except derived claims (T3 D1, phase 2,
[D5 §9](D5-consolidation-identity-confidence.md#9-derived-claims)), taking scopes and symbol
bindings as the agent's proposals state them ([D5 §11](D5-consolidation-identity-confidence.md#11-by-phase)).
From phase 1 the same scopes and bindings must also come from M13 and D5 §4.

Notation in the tables: entities are given short local references (`X`, `S1`); `≔` introduces a
formula value; symbol bindings are listed under each claim. Source text is quoted from Siegrist,
*Random* (CC BY 2.0, <https://www.randomservices.org/random/>).

---

## T1 Location-scale family definition

**Source.** Lead-in paragraph of the page (no unit id):

> … In this section, we assume that we fixed random variable \( Z \) defined on the probability
> space, with values in \( \R \).

Unit `dfn1` (`<p class="dfn">`):

> For \(a \in \R\) and \(b \in (0, \infty) \), let \(X = a + b \, Z\). The two-parameter family
> of distributions associated with \(X\) is called the location-scale family associated with the
> given distribution of \(Z\). Specifically, \(a\) is the location parameter and \(b\) the scale
> parameter.

**Segments.** `document` → `section` (page body) → `paragraph` (lead-in); `unit` `dfn1` →
`paragraph` (attrs: `class=dfn`, `dfn` term "location-scale family"); `math_inline` × 7;
`sentence` × 3 in `dfn1`.

**Entities.**

| Ref | Type | Scope | Label and aliases |
|---|---|---|---|
| S0 | `Statement` (kind `assumption`) | local: lead-in paragraph | — |
| S1 | `Statement` (kind `definition`) | local: unit `dfn1` | — |
| Z | `RandomVariable` | local: section | symbol `Z` |
| X | `RandomVariable` | local: S1 | symbol `X` |
| LSF | `FamilyConstruction` | global | "location-scale family" |
| LSF.loc | `FamilyParameter` (identity: LSF, `location`) | global | "location parameter" |
| LSF.scale | `FamilyParameter` (identity: LSF, `scale`) | global | "scale parameter" |

**Claims.**

| Ref | Subject | Predicate | Object | Modality | Statement · role | Conditions |
|---|---|---|---|---|---|---|
| C1 | Z | `takes_values_in` | set ≔ `\R` | supposed, scope `section` | S0 · premise | — |
| C2 | X | `defined_as` | formula ≔ `a + b \, Z` | defined | S1 · definiens | `and(member(a, \R), member(b, (0, \infty)))` |
| C3 | S1 | `defines` | LSF | asserted | — | — |
| C4 | LSF | `construction_formula` | formula ≔ `a + b \, Z` (the generated variable is the subject's, not part of the formula); qualifiers `base_variable: Z`, `param_symbols: {location: a, scale: b}` | defined | S1 · definiens | as C2 |
| C5 | LSF | `has_parameter` | LSF.loc | defined | S1 · definiens | — |
| C6 | LSF | `has_parameter` | LSF.scale | defined | S1 · definiens | — |
| C7 | LSF.loc | `parameter_domain` | set ≔ `\R` | defined | S1 · definiens | — |
| C8 | LSF.scale | `parameter_domain` | set ≔ `(0, \infty)` | defined | S1 · definiens | — |

Symbol bindings: in C2 and C4, `Z` binds `variable Z`; `a` and `b` bind `family_param LSF.loc` and
`family_param LSF.scale` (the unit names them the location and scale parameters, guideline §10.7
row 4), in C2's conditions too. No `parameter_role` claims: the canonical names already are the
roles (§10.4).

**Must not appear.** A `DistributionFamily` named "location-scale family"; a link from LSF to any
specific distribution; `b ∈ ℝ` (the source restricts b to (0, ∞)).

**Evidence.** C1 cites the lead-in sentence; C2–C8 cite the `dfn1` sentences that state them (C7
and C8 also cite the first sentence's restriction spans with role `condition`).

---

## T2 Normal parameters, respectively

**Source.** A paragraph of `special/Normal.html` (no unit id):

> Suppose again that \( X \) has the normal distribution with location parameter \( \mu \in \R \)
> and scale parameter \( \sigma \in (0, \infty) \). As the notation suggests, the location and
> scale parameters are also the mean and standard deviation, respectively.

**Entities.**

| Ref | Type | Scope | Label and aliases |
|---|---|---|---|
| S1 | `Statement` (kind `remark`) | local: paragraph | — |
| X | `RandomVariable` | local: section (the page's running X) | symbol `X` |
| N | `DistributionFamily` | global | "normal distribution", "normal", "normally distributed" |
| N.loc, N.scale, N.mean, N.sd | `FamilyParameter` (N, `location` / `scale` / `mean` / `standard_deviation`) | global | "location parameter", … |

**Claims.**

| Ref | Subject | Predicate | Object | Modality | Statement · role | Conditions |
|---|---|---|---|---|---|---|
| C1 | X | `has_distribution` | N; `param_values {location: ≔ \mu, scale: ≔ \sigma}` | supposed, scope `section` | S1 · premise | — (a premise carries no restrictions; its dependants are family-structure claims, guideline §10.7 rules 1–2) |
| C4 | N.loc | `identical_parameter` | N.mean | asserted | S1 · conclusion | — |
| C5 | N.scale | `identical_parameter` | N.sd | asserted | S1 · conclusion | — |

Symbol bindings: in C1, `\mu` and `\sigma` bind `free` (introduced here). No `has_parameter`
claims: they are stated only in a definition of the family (guideline §10.4), and this is a remark.

**Must not appear.** `N.loc identical_parameter N.sd` or `N.scale identical_parameter N.mean`
(wrong pairing of "respectively"); any claim with subject X and predicate `has_parameter`
(X is a variable, not a family); "location" as a parameter value.

---

## T3 Normal affine transformation

**Source.** Unit `rel1` of `special/Normal.html` (`<p class="math">`):

> Suppose that \(X\) is normally distributed with mean \(\mu\) and variance \(\sigma^2\). If
> \(a \in \R\) and \(b \in \R \setminus \{0\}\), then \(a + b X\) is normally distributed with
> mean \(a + b \mu\) and variance \(b^2 \sigma^2\).

followed by a `<details>` proof beginning "The MGF of \(a + b X\) is …".

**Entities.**

| Ref | Type | Scope | Label and aliases |
|---|---|---|---|
| S1 | `Statement` (kind `theorem`) | local: unit `rel1` | — |
| S2 | `Statement` (kind `proof`) | local: `details` of `rel1` | — |
| X | `RandomVariable` | local: S1 | symbol `X` |
| Y | `RandomVariable` | local: S1 | expression `a + b X` |
| N | `DistributionFamily` | global | as T2 |
| N.mean, N.var | `FamilyParameter` (N, `mean` / `variance`) | global | "mean", "variance" |

**Claims.**

| Ref | Subject | Predicate | Object | Modality | Statement · role | Conditions |
|---|---|---|---|---|---|---|
| C1 | X | `has_distribution` | N; `param_values {mean: ≔ \mu, variance: ≔ \sigma^2}` | supposed | S1 · premise | — |
| C2 | Y | `defined_as` | formula ≔ `a + b X` | defined | S1 · definiens | `and(member(a, \R), member(b, \R \setminus \{0\}))` (restrictions stated with it on its own symbols, §10.7 rule 2) |
| C3 | Y | `has_distribution` | N; `param_values {mean: ≔ a + b \mu, variance: ≔ b^2 \sigma^2}` | asserted | S1 · conclusion | `and(claim C1, member(a, \R), member(b, \R \setminus \{0\}))` |
| C4 | S2 | `proves` | S1 | asserted | — | — |
| D1 | Y | `has_distribution` | N; `param_values {mean: ≔ a + b \mu, standard_deviation: ≔ \lvert b \rvert \sigma}` | asserted, **establishment `derived`** | S1 · conclusion | as C3 |

Symbol bindings:

- C2: `X` binds `variable X`; `a`, `b` bind `free`.
- C3: `\mu` binds `param_of C1 mean`; `\sigma` binds `param_expr_of C1 variance`; `a`, `b`
  bind `free`.
- D1: as C3; `derived_from` C3, using the schema rule `variance = standard_deviation^2` with
  `standard_deviation > 0`.

**Must not appear.** A standard deviation of `b\sigma` (wrong for negative b) or `b^2 \sigma^2`
bound to standard deviation; C3 without the `claim C1` condition; C1 with modality `asserted`.

---

## T4 Lognormal definition

**Source.** Unit `dfn` of `special/LogNormal.html`:

> Suppose that \(Y\) has the normal distribution with mean \(\mu \in \R\) and standard deviation
> \(\sigma \in (0, \infty)\). Then \(X = e^Y\) has the lognormal distribution with parameters
> \(\mu\) and \(\sigma\).

and its list items:

> 1. The parameter \( \sigma \) is the shape parameter of the distribution.
> 2. The parameter \( e^\mu\) is the scale parameter of the distribution.

and the unit's second paragraph (part of `div.unit#dfn`; S0 found the trace had omitted it):

> If \(Z\) has the standard normal distribution then \(W = e^Z\) has the standard lognormal
> distribution.

**Entities.**

| Ref | Type | Scope | Label and aliases |
|---|---|---|---|
| S1 | `Statement` (kind `definition`) | local: unit `dfn` | — |
| Y, X, Z, W | `RandomVariable` | local: S1 | symbols `Y`, `X`, `Z`, `W` |
| N | `DistributionFamily` | global | as T2 |
| LN | `DistributionFamily` | global | "lognormal distribution" |
| N.mean, N.sd | `FamilyParameter` | global | as T2 |
| LN.mu, LN.sigma | `FamilyParameter` (LN, canonical name `mu` / `sigma`: no role named in the definition) | global | symbols `\mu`, `\sigma` |
| LN.scale | `FamilyParameter` (LN, `scale`) | global | "scale parameter" |
| SN, SLN | `DistributionFamily` | global | "standard normal distribution", "standard lognormal distribution" |

**Claims.**

| Ref | Subject | Predicate | Object | Modality | Statement · role | Conditions |
|---|---|---|---|---|---|---|
| C1 | Y | `has_distribution` | N; `param_values {mean: ≔ \mu, standard_deviation: ≔ \sigma}` | supposed | S1 · premise | — |
| C2 | X | `defined_as` | formula ≔ `e^Y` | defined | S1 · definiens | — |
| C3 | X | `has_distribution` | LN; `param_values {mu: ≔ \mu, sigma: ≔ \sigma}` | defined | S1 · definiens | `and(claim C1, member(\mu, \R), member(\sigma, (0, \infty)))` |
| C4 | S1 | `defines` | LN | asserted | — | — |
| C5 | LN | `has_parameter` | LN.mu | defined | S1 · definiens | — |
| C6 | LN | `has_parameter` | LN.sigma | defined | S1 · definiens | — |
| C7 | LN | `transformation_of` | N; qualifiers `transform: ≔ e^Y`, `param_mapping {mu: mean, sigma: standard_deviation}` (canonical names of N's parameters) | defined | S1 · definiens | — |
| C8 | LN.sigma | `parameter_role` | enum `ParameterRole.shape` | defined | S1 · definiens | — |
| C9 | LN | `has_parameter` | LN.scale | defined | S1 · definiens | — |
| C10 | LN.scale | `derived_parameter` | formula ≔ `e^\mu` | defined | S1 · definiens | — |
| C11 | LN.mu | `parameter_domain` | set ≔ `\R` | defined | S1 · definiens | — |
| C12 | LN.sigma | `parameter_domain` | set ≔ `(0, \infty)` | defined | S1 · definiens | — |
| C13 | Z | `has_distribution` | SN | supposed | S1 · premise | — |
| C14 | W | `defined_as` | formula ≔ `e^Z` | defined | S1 · definiens | — |
| C15 | W | `has_distribution` | SLN | defined | S1 · definiens | `claim C13` |
| C16 | S1 | `defines` | SLN | asserted | — | — |
| C17 | SLN | `transformation_of` | SN; qualifier `transform: ≔ e^Z` | defined | S1 · definiens | — |

Symbol bindings: C1 `\mu`, `\sigma` bind `free`; C3 `\mu` binds `param_of C1 mean`, `\sigma`
binds `param_of C1 standard_deviation` (in its conditions too); C10 `\mu` binds `family_param LN.mu` (a
family-structure claim, guideline §10.7 row 2). C11 and C12 state the domains the premise's
restrictions give the parameters that become LN's (§10.4).

**What changed from the old design.** The old representation could not state the shape and scale
sentences (outcome `outside_representation`). Here they are ordinary claims (C8–C10), because
parameter roles and derived parameters are schema predicates rather than fixed slots.

**Must not appear.** `LN.sigma identical_parameter N.sd` as an asserted family identity (the
mapping is via the transformation, C7); a lognormal `mean` parameter equal to `\mu`.

---

## Expected observations, by method

What a well-functioning pipeline should observe on these units. This is guidance for spikes and
method design, not a gold: methods are scored on claims ([D7](D7-evaluation-goldens-outer-loop.md)).

| Method ([D4](D4-method-catalog.md)) | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
| M01 ingest | `dfn1` unit and `dfn` markup "location-scale family" | paragraph | unit `rel1`, `details` | unit `dfn`, list items |
| M06 GLiNER2 entities | "location-scale family", "location parameter", "scale parameter", `Z`, `X` | `X`, "normal distribution", "location parameter", "mean", "standard deviation" | `X`, "normally distributed", "mean", "variance" | `Y`, `X`, "normal distribution", "lognormal distribution", "shape parameter", "scale parameter" |
| M07 `JointIE` relations | — | `has_distribution(X, normal distribution)` | `has_distribution(X, normally distributed)` | `has_distribution(Y, normal)`, `has_distribution(X, lognormal)` |
| M09 math spans (S1 confirms) | 8 inline (lead-in 1, `dfn1` 7) | 3 | 8 | 8 (unit 6, list items 2) |
| M11 SymPy parse | all except `\R` without a macro map | all | all; `\R \setminus \{0\}` as a set | all |
| M13 symbol scope | Z → section; X → S1 | X → section ("again") | X, Y → S1 | Y, X → S1 |
| M10 LLM claims | C1–C8 | C1–C5 | C1–C4 | C1–C10 |
