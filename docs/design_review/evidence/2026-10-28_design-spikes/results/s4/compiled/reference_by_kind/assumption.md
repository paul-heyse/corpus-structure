# Annotation reference (generated from the schema)

Schemas `statistics` 0.2.0, `core` 0.2.0. The guideline says what to capture; this says how to write it: which entity type, which predicate, which qualifiers, how claims take roles, modality and conditions, the exact shape of every item.

## 1. Entity types

| Type | What it is | Scope | Identity slots | Examples |
|---|---|---|---|---|
| `Concept` | A defined mathematical term that is not a distribution family, construction or parameter: the gamma function, the standard score, the moment generating function. | global | — | the gamma function, the standard score |
| `DistributionFamily` | A named family of probability distributions, possibly with parameters: the normal distribution, the gamma distribution, the standard normal distribution. Mentions include adjectival forms ("normally distributed", "has a gamma distribution"). | global | — | the normal distribution, lognormal distribution, normally distributed |
| `FamilyConstruction` | A way of generating a family of distributions from a base distribution, such as the location-scale family, the location family or the scale family associated with a distribution, or the general exponential family. Not itself a single distribution family. | global | — | location-scale family, scale family associated with the given distribution |
| `FamilyParameter` | A parameter of a distribution family or construction, such as the location parameter, the scale parameter, the shape parameter k, the rate, the mean or the standard deviation when these parameterize the family. | global | family, canonical_name | location parameter, shape parameter k, the rate parameter |
| `RandomVariable` | A random variable denoted by a symbol (X, Y, Z, X_1, W) or by an expression in other random variables (a + b X, e^Y, X_1 + X_2). Local to the statement or section that introduces it. | local | — | X, a + b X, X_1 + X_2 |

`Statement` (An authored unit of meaning: a definition, theorem, proof, example, exercise, remark, convention or assumption. Claims belong to statements as premises, conclusions, definientia or example values. Listed in a batch's statements[], never in entities[].) is a `statements[]` item: `{"local_ref": <string>, "kind": "definition" | "theorem" | "proposition" | "lemma" | "corollary" | "proof" | "example" | "exercise" | "solution" | "remark" | "convention" | "notation" | "assumption" | "narrative", "anchor": "unit" | "outside" | [<string>, …]}`; anchor `"unit"`, the sentence ids it lies in, or `"outside"` for a statement outside the unit that the unit refers to.
An `entities[]` item: `{"local_ref": <string>, "type": "Concept" | "DistributionFamily" | "FamilyConstruction" | "FamilyParameter" | "RandomVariable", "label": <string>, "scope": "global" | "local", "extent"?: "statement" | "section", "symbol"?: <string>, "aliases"?: [<string>, …], "identity"?: {<key>: <string>}}`. A local entity has an `extent`; identity holds the class's identity slots, an entity-valued slot as a local-ref string.

## 2. Predicates

Grouped by the schema's predicate subsets; a predicate in two subsets is listed under the first.

### structural

Structural claims, about statements. They take no statement_role, are asserted, and carry no conditions (guideline §10.3, §10.6, §10.7 rule 4).

#### `defines`

- **Subject:** Statement. **Object:** Entity as `<entity ref>`.
- **Meaning:** The statement defines the entity. "is called the location-scale family".
- **Rules:** Structural claims take no statement_role and are asserted (guideline §10.3, §10.6). Structural claims carry no conditions (guideline §10.7 rule 4).
- **In the worked examples:** E1 `c_defines`.

#### `follows_from`

- **Subject:** Statement. **Object:** Statement as `<entity ref>`.
- **Meaning:** The statement is stated to follow from another ("a corollary of the last result").
- **Rules:** Structural claims take no statement_role and are asserted (guideline §10.3, §10.6). Structural claims carry no conditions (guideline §10.7 rule 4).

#### `proves`

- **Subject:** Statement. **Object:** Statement as `<entity ref>`.
- **Meaning:** A proof or solution statement proves (or solves) another statement.
- **Rules:** Structural claims take no statement_role and are asserted (guideline §10.3, §10.6). Structural claims carry no conditions (guideline §10.7 rule 4).
- **In the worked examples:** E2 `c_proves`, E3 `c_proves`.

#### `refers_to`

- **Subject:** Statement. **Object:** Entity as `<entity ref>`.
- **Meaning:** The statement explicitly refers to an entity defined elsewhere ("recall the gamma function").
- **Rules:** Structural claims take no statement_role and are asserted (guideline §10.3, §10.6). Structural claims carry no conditions (guideline §10.7 rule 4).

### unsupported

Something the source states that the schema cannot express; the claim has status unsupported (D1 §8.1).

#### `unschematized`

- **Subject:** Entity. **Object:** PhraseValue as `<phrase>`.
- **Meaning:** Something the source states that the schema cannot express (D1 §8.1).

### formula_definition

Formula claims that define a variable, a concept or a construction by a formula, or a family by a transformation. They hold by the form of the formula: role definiens in a definition or for a formula introducing a variable; modality defined when stipulated, asserted when concluded; no claim nodes, only the restrictions stated with them on their own symbols (guideline §10.7 rule 2).

#### `construction_formula`

- **Subject:** FamilyConstruction. **Object:** Formula as `<formula>`.
- **Meaning:** The formula generating members of the construction, without the variable it defines. "X = a + b Z" gives a + b Z.
- **Its qualifiers:** `base_variable`, `param_symbols` (besides the core qualifiers).
- **Also:** also in family_structure.
- **Rules:** Formula and family-structure claims carry no claim nodes, only restrictions on their own symbols (guideline §10.7 rule 2). A formula that defines a variable or generates a family excludes the variable it defines (guideline §10.7).

#### `defined_as`

- **Subject:** RandomVariable. **Object:** Formula as `<formula>`.
- **Meaning:** The random variable is defined by a formula in other variables. "let X = a + b Z".
- **Rules:** Formula and family-structure claims carry no claim nodes, only restrictions on their own symbols (guideline §10.7 rule 2). A formula that defines a variable or generates a family excludes the variable it defines (guideline §10.7).
- **In the worked examples:** E1 `c_X_def`, E2 `c_Y_def`.

#### `definition_formula`

- **Subject:** Concept. **Object:** Formula as `<formula>`.
- **Meaning:** The formula defining the concept. "the standard score is (X - μ) / σ".
- **Rules:** Formula and family-structure claims carry no claim nodes, only restrictions on their own symbols (guideline §10.7 rule 2).

#### `transformation_of`

- **Subject:** DistributionFamily. **Object:** DistributionFamily as `<entity ref>`.
- **Meaning:** Variables in this family arise by transforming a variable of the other family. "X = e^Y has the lognormal distribution".
- **Its qualifiers:** `transform`, `param_mapping` (besides the core qualifiers).
- **Also:** also in family_structure.
- **Rules:** Formula and family-structure claims carry no claim nodes, only restrictions on their own symbols (guideline §10.7 rule 2).
- **In the worked examples:** E1 `c_W_transform`.

### family_structure

Claims about a family's parameters as such. They hold by the structure of the family: no claim nodes, only the restrictions stated with them on their own symbols (guideline §10.7 rule 2); a parameter symbol binds family_param (§10.7 row 2); stated only in a definition of the family (§10.4).

#### `derived_parameter`

- **Subject:** FamilyParameter. **Object:** Formula as `<formula>`.
- **Meaning:** The parameter equals a formula in the family's other parameters. "e^μ is the scale parameter".
- **Rules:** Formula and family-structure claims carry no claim nodes, only restrictions on their own symbols (guideline §10.7 rule 2).

#### `has_parameter`

- **Subject:** Parameterized. **Object:** FamilyParameter as `<entity ref>`.
- **Meaning:** A family or construction has this parameter. "with shape parameter k and scale parameter b".
- **Rules:** Formula and family-structure claims carry no claim nodes, only restrictions on their own symbols (guideline §10.7 rule 2).
- **In the worked examples:** E1 `c_hp_shape`, E1 `c_hp_scale`.

#### `identical_parameter`

- **Subject:** FamilyParameter. **Object:** FamilyParameter as `<entity ref>`.
- **Meaning:** Two parameter names denote the same parameter of the family. "the location and scale parameters are also the mean and standard deviation, respectively".
- **Also:** symmetric.
- **Rules:** Formula and family-structure claims carry no claim nodes, only restrictions on their own symbols (guideline §10.7 rule 2).

#### `parameter_domain`

- **Subject:** FamilyParameter. **Object:** SetExpr as `<set>`.
- **Meaning:** The set of the parameter's allowed values. "b ∈ (0, ∞)".
- **Also:** one object per subject in a statement.
- **Rules:** Formula and family-structure claims carry no claim nodes, only restrictions on their own symbols (guideline §10.7 rule 2).
- **In the worked examples:** E1 `c_dom_shape`, E1 `c_dom_scale`.

#### `parameter_role`

- **Subject:** FamilyParameter. **Object:** ParameterRole as `{"t": "enum", "enum": "ParameterRole", "v": "location" | "scale" | "shape" | "rate" | "mean" | "variance" | "standard_deviation" | "precision" | "degrees_of_freedom" | "success_probability" | "number_of_trials" | "lower_bound" | "upper_bound" | "other"}`.
- **Meaning:** The parameter plays this role, stated when it differs from its canonical name. "σ is the shape parameter".
- **Rules:** Formula and family-structure claims carry no claim nodes, only restrictions on their own symbols (guideline §10.7 rule 2). A parameter_role claim is stated only when the role differs from the canonical name (guideline §10.4).

#### `special_case_of`

- **Subject:** DistributionFamily. **Object:** Entity as `<entity ref>`.
- **Meaning:** The family is the special case of another family or construction obtained under parameter constraints. "The exponential distribution is the gamma distribution with k = 1".
- **Its qualifiers:** `param_constraints` (besides the core qualifiers).
- **Also:** transitive.
- **Rules:** Formula and family-structure claims carry no claim nodes, only restrictions on their own symbols (guideline §10.7 rule 2).

### distribution

Distribution claims: the parameter values a sentence states, keyed by the family's canonical parameter names (guideline §10.5).

#### `has_distribution`

- **Subject:** RandomVariable. **Object:** DistributionFamily as `<entity ref>`.
- **Meaning:** The random variable has a distribution in the family, optionally with stated parameter values. "X is normally distributed with mean μ and variance σ²".
- **Its qualifiers:** `param_values` (besides the core qualifiers).
- **Also:** one object per subject in a statement.
- **In the worked examples:** E1 `c_Z_basic`, E1 `c_X_weibull`, E2 `c_X_weibull`, E2 `c_Y_weibull`, E3 `c_T_weibull`.

### Claims in no predicate subset

#### `cdf`

- **Subject:** Distributed. **Object:** Formula as `<formula>`.
- **Meaning:** The cumulative distribution function, with its argument domain as a condition.

#### `limit_of`

- **Subject:** DistributionFamily. **Object:** DistributionFamily as `<entity ref>`.
- **Meaning:** The family is a limit of the other under a stated limiting operation.
- **Its qualifiers:** `limit`, `param_mapping` (besides the core qualifiers).

#### `mean_value`

- **Subject:** Distributed. **Object:** Formula as `<formula>`.
- **Meaning:** The mean (expected value) as a formula. "E(X) = μ".

#### `member_of_construction`

- **Subject:** DistributionFamily. **Object:** FamilyConstruction as `<entity ref>`.
- **Meaning:** The family is the construction applied to a base. "The general normal distribution is the location-scale family associated with the standard normal distribution".
- **Its qualifiers:** `base` (besides the core qualifiers).

#### `mgf`

- **Subject:** Distributed. **Object:** Formula as `<formula>`.
- **Meaning:** The moment generating function, with the set of arguments where it is finite as a condition.

#### `pdf`

- **Subject:** Distributed. **Object:** Formula as `<formula>`.
- **Meaning:** The probability density (or mass) function, with its argument domain as a condition.

#### `support`

- **Subject:** Distributed. **Object:** SetExpr as `<set>`.
- **Meaning:** The support of the distribution, the set of values with positive density or mass. "on (0, ∞)".

#### `takes_values_in`

- **Subject:** RandomVariable. **Object:** SetExpr as `<set>`.
- **Meaning:** The random variable's values lie in the set. "with values in ℝ".

#### `variance_value`

- **Subject:** Distributed. **Object:** Formula as `<formula>`.
- **Meaning:** The variance as a formula. "var(X) = σ²".

### Rules for every claim

- A claim's statement_role is one its statement's kind gives (guideline §10.3).
- A claim's modality follows from its statement_role (guideline §10.6).
- Premises and example values carry no conditions except the range of an index they are stated for; restrictions go to the claims that depend on them (guideline §10.7 rule 1).
- Every other claim carries a claim node for the premises it depends on: it references at least one premise of its statement or of a context-premise assumption (guideline §10.7 rule 3).
- Symbol-map keys are written without backslash (guideline §10.7).
- A symbol another claim gives as a parameter value binds param_of, not free or family_param, unless the claim is about the family as such (guideline §10.7 rows 2-4).

## 3. Statement roles and modality

`roles_by_kind`:

- definition: definiens, premise
- theorem: premise, conclusion, definiens
- proposition: premise, conclusion, definiens
- corollary: premise, conclusion, definiens
- lemma: premise, conclusion, definiens
- remark: premise, conclusion, definiens, none
- example: example_value
- exercise: example_value
- convention: none (none: no statement_role)
- assumption: premise
- proof: 
- solution: 

`modality_by_role`:

- premise: supposed
- definiens: defined
- conclusion: asserted
- example_value: exemplified

## 4. Qualifiers

Core qualifiers are allowed on every predicate; the others only where a card lists them. An absent qualifier is omitted, never null; `modality` defaults to `asserted`, `polarity` to `positive`.

| Qualifier | Value | Meaning |
|---|---|---|
| `attribution` (core) | `<entity ref>` | Who the source says states the claim, when it cites someone. |
| `base` | `<entity ref>` | The base family the construction is applied to. |
| `base_variable` | `<entity ref>` | The base variable the construction formula transforms (Z in a + b Z). |
| `conditions` (core) | `<condition>` | The condition tree under which the claim holds (D1 §7). |
| `hedge` (core) | `<phrase>` | A hedging phrase the source attaches to the claim ("usually", "in some settings"). |
| `limit` | `<phrase>` | The limiting operation as stated. "as n → ∞". |
| `modality` (core) | `"asserted" | "supposed" | "defined" | "conventional" | "exemplified" | "posed" | "cited"` | How the source holds the claim (D1 §5.2); asserted when absent. |
| `param_constraints` | `<condition>` | A condition tree (D1 §7) over the base family's parameters under which the special case holds (k = 1). |
| `param_mapping` | `{<key>: <string>}` | An object from the target family's canonical parameter names to the base family's canonical parameter names they correspond to: {"shape": "sigma"}. |
| `param_symbols` | `{<key>: <formula>}` | An object from the construction's canonical parameter names to the symbols that stand for them in its formula: {"location": <formula a>, "scale": <formula b>}. |
| `param_values` | `{<key>: <formula>}` | The parameter values the sentence states, an object from the family's canonical parameter names to formulas: {"shape": <formula>, "scale": <formula>} (guideline §10.5). |
| `polarity` (core) | `"positive" | "negative"` | Whether the claim is stated or denied; positive when absent. |
| `scope` (core) | `"statement" | "section" | "document"` | How far a supposition reaches beyond its statement; model-facing a ScopeExtent value, stored {extent, segment}. |
| `transform` | `<formula>` | The transformation, as a formula in the base variable. "e^Y". |
| `valid_time` (core) | `<interval>` | The time interval over which the claim holds, when the source states one. |

## 5. Enumerations

- **BindKind:** `variable` (The symbol denotes a local entity of the batch.); `param_of` (The symbol is the value of an entry of another claim's parameter map.); `param_expr_of` (The symbol occurs inside the value of such an entry.); `family_param` (The symbol denotes a parameter entity of a family.); `free` (A symbol the statement introduces, restricted by its conditions.); `constant` (A numeric or named constant.); `unresolved` (Not bound; a counted resolution gap.)
- **ClaimModality:** `asserted` (Concluded or stated as true; structural claims.); `supposed` (A supposition: suppose, assume, if, or let about something taken as given.); `defined` (What a definition stipulates, including a formula introducing a variable.); `conventional` (A convention.); `exemplified` (Setup values in examples and exercises.); `posed` (Reserved until an asks_for predicate exists (OPEN-D2-15).); `cited` (Attributed to another source.)
- **ConditionPredicate:** `independent` (The arguments are independent.); `identically_distributed` (The arguments have the same distribution.); `iid` (The arguments are independent and identically distributed.)
- **EvidenceRole:** `primary` (The minimal span that states the claim.); `supporting` (An introducer that determines the modality.); `condition` (The span of a condition.); `definition` (The span of a definition the claim relies on.)
- **ParameterRole:** `location` (A location parameter.); `scale` (A scale parameter.); `shape` (A shape parameter.); `rate` (A rate parameter.); `mean` (The mean as a parameter.); `variance` (The variance as a parameter.); `standard_deviation` (The standard deviation as a parameter.); `precision` (The precision (reciprocal variance) as a parameter.); `degrees_of_freedom` (Degrees of freedom.); `success_probability` (A success probability.); `number_of_trials` (A number of trials.); `lower_bound` (A lower bound of the support.); `upper_bound` (An upper bound of the support.); `other` (Another stated role.)
- **ParseStatus:** `ok` (One reading.); `partial` (Parsed in part.); `ambiguous` (More than one reading, none chosen by declared context.); `failed` (Not parsed.)
- **Polarity:** `positive` (Stated.); `negative` (Denied.)
- **ScopeExtent:** `statement` (The statement that states it.); `section` (The enclosing section from the stating sentence on.); `document` (The whole document.)
- **StatementKind:** `definition` (Stipulates what a term means.); `theorem` (A stated result.); `proposition` (A stated result.); `lemma` (A stated auxiliary result.); `corollary` (A result stated to follow from another.); `proof` (A proof of another statement.); `example` (A worked example with setup values.); `exercise` (An exercise with setup values and an asked quantity.); `solution` (A solution of an exercise.); `remark` (A remark; explicit claims only.); `convention` (A convention the source adopts.); `notation` (A notation the source introduces.); `assumption` (A statement whose only content is a supposition (a context premise).); `narrative` (Narrative text between units that states claims.)
- **StatementRole:** `premise` (A supposition the statement makes.); `conclusion` (What a theorem, corollary or remark concludes.); `definiens` (What a definition stipulates, or a formula introducing a variable.); `restriction` (Reserved; restrictions are condition nodes in guideline v1.); `example_value` (A setup value of an example or exercise.)

## 6. Exact shapes

Fields marked `?` may be omitted; an omitted field is absent, never `null`.

| Item | Shape |
|---|---|
| formula value | `{"t": "formula", "latex": <string>, "symbols"?: {<key>: <binding>}}` |
| set value | `{"t": "set", "latex": <string>, "symbols"?: {<key>: <binding>}}` |
| text value | `{"t": "text", "v": <string>}` |
| number value | `{"t": "number", "v": <string>, "unit"?: <string>, "basis"?: <string>}` |
| bool value | `{"t": "bool", "v": <boolean>}` |
| enum value | `{"t": "enum", "enum": <string>, "v": <string>}` |
| date value | `{"t": "date", "v": <string>}` |
| interval value | `{"t": "interval", "start"?: <number> | <date> | <formula>, "end"?: <number> | <date> | <formula>, "start_incl"?: <boolean>, "end_incl"?: <boolean>}` |
| phrase value | `{"t": "phrase", "text": <string>, "sentence"?: <string>}` |
| entity reference | `{"ref": <string>}` (objects, entity qualifiers and `pred` arguments) |
| binding | `{"bind": "variable" | "family_param", "entity": <string>}` |
| binding | `{"bind": "param_of" | "param_expr_of", "claim": <string>, "param": <string>}` |
| binding | `{"bind": "free" | "constant" | "unresolved"}` |
| condition node | `{"op": "and", "args": [<condition>, …]}` |
| condition node | `{"op": "not", "arg": <condition>}` |
| condition node | `{"op": "claim", "ref": <string>}` |
| condition node | `{"op": "member", "x": {"t": "formula", "latex": <string>, "symbols"?: {<key>: <binding>}}, "set": {"t": "set", "latex": <string>, "symbols"?: {<key>: <binding>}}}` |
| condition node | `{"op": "cmp", "rel": "<" | "<=" | "=" | "!=" | ">" | ">=", "lhs": {"t": "formula", "latex": <string>, "symbols"?: {<key>: <binding>}}, "rhs": {"t": "formula", "latex": <string>, "symbols"?: {<key>: <binding>}}}` |
| condition node | `{"op": "pred", "name": <string>, "args": [<entity ref> | <formula>, …]}` |
| condition node | `{"op": "forall", "var": <string>, "set": {"t": "set", "latex": <string>, "symbols"?: {<key>: <binding>}}, "body": <condition>}` |
| condition node | `{"op": "phrase", "text": <string>, "sentence"?: <string>}` |
| condition node | `{"op": "unsupported", "text": <string>, "reason": <string>, "sentence"?: <string>}` |
| map qualifier | `{<canonical name>: <formula>}` (`param_values`, `param_symbols`), `{<canonical name>: <string>}` (`param_mapping`) |
| evidence | `{"sentence": <string>, "quote": <string>, "role": "primary" | "supporting" | "condition" | "definition"}`; sentence `sN` of the unit or `cN` of its standing context; quote an exact substring |
| alternative | `{"refs": [<string>, …], "reason": <string>}` |
| unsupported | `{"local_ref": <string>, "sentence": <string>, "quote": <string>, "reason": <string>}` |
| claim | `{"local_ref": <string>, "predicate": <predicate>, "subject": <string>, "object": {"t": "formula", "latex": <string>, "symbols"?: {<key>: <binding>}}, "qualifiers"?: {"attribution"?: <entity ref>, "conditions"?: <condition>, "hedge"?: <phrase>, "modality"?: "asserted" | "supposed" | "defined" | "conventional" | "exemplified" | "posed" | "cited", "polarity"?: "positive" | "negative", "scope"?: "statement" | "section" | "document", "valid_time"?: <interval>}, "statement"?: <string>, "statement_role"?: "premise" | "conclusion" | "definiens" | "restriction" | "example_value", "evidence": [<evidence>, …]}` |
| batch | `{"unit_ref": <string>, "entities"?: [<entity>, …], "statements"?: [<statement>, …], "claims"?: [<claim>, …], "alternatives"?: [<alternative>, …], "unsupported"?: [<unsupported>, …]}` |

Condition predicates (`pred` `name`): `independent` (2+ RandomVariable); `identically_distributed` (2+ RandomVariable); `iid` (2+ RandomVariable)

## 7. Worked examples

