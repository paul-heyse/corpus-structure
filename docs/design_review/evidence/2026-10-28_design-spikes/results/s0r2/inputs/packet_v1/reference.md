# Annotation reference (generated from the schema; guideline v1 §10.10)

Look things up here while annotating: which entity type, which predicate, which qualifiers, how to
bind a symbol, the exact shape of every value. The guideline says what to capture; this says how to
write it. `schema.yaml` and `model.md` are the sources, for background only.

## 1. Entity types

| Type | What it is | Scope | Identity slots | Examples |
|---|---|---|---|---|
| `DistributionFamily` | A named family of probability distributions, possibly with parameters: the normal distribution, the gamma distribution, the standard normal distribution. Mentions include adjectival forms ("normally distributed", "has a gamma distribution"). | global | — | the normal distribution, lognormal distribution, normally distributed |
| `FamilyConstruction` | A way of generating a family of distributions from a base distribution, such as the location-scale family, the location family or the scale family associated with a distribution, or the general exponential family. Not itself a single distribution family. | global | — | location-scale family, scale family associated with the given distribution |
| `FamilyParameter` | A parameter of a distribution family or construction, such as the location parameter, the scale parameter, the shape parameter k, the rate, the mean or the standard deviation when these parameterize the family. | global | family, canonical_name | location parameter, shape parameter k, the rate parameter |
| `RandomVariable` | A random variable denoted by a symbol (X, Y, Z, X_1, W) or by an expression in other random variables (a + b X, e^Y, X_1 + X_2). Local to the statement or section that introduces it. | local | — | X, a + b X, X_1 + X_2 |
| `Concept` | A defined mathematical term that is not a distribution family, construction or parameter: the gamma function, the standard score, the moment generating function. | global | — | — |

A `Statement` is listed in `statements[]`, not `entities[]`: `{local_ref, kind, anchor}`.

## 2. Predicates

Grouped by how they take roles, modality and conditions (guideline §10.3, §10.6, §10.7).

### Structural claims (about statements)

#### `defines`

- **Subject:** Statement. **Object:** Entity as `{"ref": <local ref of a Entity>}`.
- **Meaning:** The statement defines the entity. "is called the location-scale family".
- **Role:** no `statement_role`. **Modality:** `asserted`.
- **Conditions:** none.
- **In the worked examples:** E1 `c_defines`.

#### `proves`

- **Subject:** Statement. **Object:** Statement as `{"ref": <local ref of a Statement>}`.
- **Meaning:** A proof or solution statement proves (or solves) another statement.
- **Role:** no `statement_role`. **Modality:** `asserted`.
- **Conditions:** none.
- **In the worked examples:** E2 `c_proves`, E3 `c_proves`.

#### `refers_to`

- **Subject:** Statement. **Object:** Entity as `{"ref": <local ref of a Entity>}`.
- **Meaning:** The statement explicitly refers to an entity defined elsewhere ("recall the gamma function").
- **Role:** no `statement_role`. **Modality:** `asserted`.
- **Conditions:** none.

#### `follows_from`

- **Subject:** Statement. **Object:** Statement as `{"ref": <local ref of a Statement>}`.
- **Meaning:** The statement is stated to follow from another ("a corollary of the last result").
- **Role:** no `statement_role`. **Modality:** `asserted`.
- **Conditions:** none.

### Formula and family-structure claims

#### `defined_as`

- **Subject:** RandomVariable. **Object:** Formula as `{"t": "formula", "latex": …, "symbols": {…}}`.
- **Meaning:** The random variable is defined by a formula in other variables. "let X = a + b Z".
- **Role:** `definiens` in a definition or for a formula introducing a variable; otherwise as §10.3. **Modality:** `defined` when stipulated, `asserted` when concluded.
- **Conditions:** no `claim` nodes; only restrictions stated with it on its own symbols (§10.7 rule 2).
- **In the worked examples:** E1 `c_X_def`, E2 `c_Y_def`.

#### `construction_formula`

- **Subject:** FamilyConstruction. **Object:** Formula as `{"t": "formula", "latex": …, "symbols": {…}}`.
- **Meaning:** The formula generating members of the construction.
- **Its qualifiers:** `base_variable`, `param_symbols` (besides the core qualifiers).
- **Role:** `definiens` in a definition or for a formula introducing a variable; otherwise as §10.3. **Modality:** `defined` when stipulated, `asserted` when concluded.
- **Conditions:** no `claim` nodes; only restrictions stated with it on its own symbols (§10.7 rule 2).

#### `definition_formula`

- **Subject:** Concept. **Object:** Formula as `{"t": "formula", "latex": …, "symbols": {…}}`.
- **Meaning:** 
- **Role:** `definiens` in a definition or for a formula introducing a variable; otherwise as §10.3. **Modality:** `defined` when stipulated, `asserted` when concluded.
- **Conditions:** no `claim` nodes; only restrictions stated with it on its own symbols (§10.7 rule 2).

#### `transformation_of`

- **Subject:** DistributionFamily. **Object:** DistributionFamily as `{"ref": <local ref of a DistributionFamily>}`.
- **Meaning:** Variables in this family arise by transforming a variable of the other family. "X = e^Y has the lognormal distribution".
- **Its qualifiers:** `transform`, `param_mapping` (besides the core qualifiers).
- **Role:** `definiens` in a definition or for a formula introducing a variable; otherwise as §10.3. **Modality:** `defined` when stipulated, `asserted` when concluded.
- **Conditions:** no `claim` nodes; only restrictions stated with it on its own symbols (§10.7 rule 2).
- **In the worked examples:** E1 `c_W_transform`.

#### `has_parameter`

- **Subject:** Entity. **Object:** FamilyParameter as `{"ref": <local ref of a FamilyParameter>}`.
- **Meaning:** A family or construction has this parameter.
- **Role:** `definiens` in a definition or for a formula introducing a variable; otherwise as §10.3. **Modality:** `defined` when stipulated, `asserted` when concluded.
- **Conditions:** no `claim` nodes; only restrictions stated with it on its own symbols (§10.7 rule 2).
- **In the worked examples:** E1 `c_hp_shape`, E1 `c_hp_scale`.

#### `parameter_domain`

- **Subject:** FamilyParameter. **Object:** SetExpr as `{"t": "set", "latex": …, "symbols": {…}}`.
- **Meaning:** The set of allowed values. "b ∈ (0, ∞)".
- **One value per subject** in a statement.
- **Role:** `definiens` in a definition or for a formula introducing a variable; otherwise as §10.3. **Modality:** `defined` when stipulated, `asserted` when concluded.
- **Conditions:** no `claim` nodes; only restrictions stated with it on its own symbols (§10.7 rule 2).
- **In the worked examples:** E1 `c_dom_shape`, E1 `c_dom_scale`.

#### `parameter_role`

- **Subject:** FamilyParameter. **Object:** ParameterRole as an `ParameterRole` value.
- **Meaning:** The parameter plays this role. "σ is the shape parameter".
- **Role:** `definiens` in a definition or for a formula introducing a variable; otherwise as §10.3. **Modality:** `defined` when stipulated, `asserted` when concluded.
- **Conditions:** no `claim` nodes; only restrictions stated with it on its own symbols (§10.7 rule 2).

#### `derived_parameter`

- **Subject:** FamilyParameter. **Object:** Formula as `{"t": "formula", "latex": …, "symbols": {…}}`.
- **Meaning:** The parameter equals a formula in the family's other parameters. "e^μ is the scale parameter".
- **Role:** `definiens` in a definition or for a formula introducing a variable; otherwise as §10.3. **Modality:** `defined` when stipulated, `asserted` when concluded.
- **Conditions:** no `claim` nodes; only restrictions stated with it on its own symbols (§10.7 rule 2).

#### `identical_parameter`

- **Subject:** FamilyParameter. **Object:** FamilyParameter as `{"ref": <local ref of a FamilyParameter>}`.
- **Meaning:** Two parameter names denote the same parameter of the family. "the location and scale parameters are also the mean and standard deviation, respectively".
- **Role:** `definiens` in a definition or for a formula introducing a variable; otherwise as §10.3. **Modality:** `defined` when stipulated, `asserted` when concluded.
- **Conditions:** no `claim` nodes; only restrictions stated with it on its own symbols (§10.7 rule 2).

#### `special_case_of`

- **Subject:** DistributionFamily. **Object:** Entity as `{"ref": <local ref of a Entity>}`.
- **Meaning:** The family is the special case of another family or construction obtained under parameter constraints. "The exponential distribution is the gamma distribution with k = 1".
- **Its qualifiers:** `param_constraints` (besides the core qualifiers).
- **Role:** `definiens` in a definition or for a formula introducing a variable; otherwise as §10.3. **Modality:** `defined` when stipulated, `asserted` when concluded.
- **Conditions:** no `claim` nodes; only restrictions stated with it on its own symbols (§10.7 rule 2).

### Everything else

#### `has_distribution`

- **Subject:** RandomVariable. **Object:** DistributionFamily as `{"ref": <local ref of a DistributionFamily>}`.
- **Meaning:** The random variable has a distribution in the family, optionally with stated parameter values. "X is normally distributed with mean μ and variance σ²".
- **Its qualifiers:** `param_values` (besides the core qualifiers).
- **One value per subject** in a statement.
- **Role:** by statement kind (§10.3): `premise`, `definiens`, `conclusion` or `example_value`. **Modality:** by role (§10.6).
- **Conditions:** premises and example values: none but an index range (rule 1); otherwise a `claim` node per premise it depends on and every stated restriction on its symbols (rule 3).
- **In the worked examples:** E1 `c_Z_basic`, E1 `c_X_weibull`, E2 `c_X_weibull`, E2 `c_Y_weibull`, E3 `c_T_weibull`.

#### `takes_values_in`

- **Subject:** RandomVariable. **Object:** SetExpr as `{"t": "set", "latex": …, "symbols": {…}}`.
- **Meaning:** The random variable's values lie in the set. "with values in ℝ".
- **Role:** by statement kind (§10.3): `premise`, `definiens`, `conclusion` or `example_value`. **Modality:** by role (§10.6).
- **Conditions:** premises and example values: none but an index range (rule 1); otherwise a `claim` node per premise it depends on and every stated restriction on its symbols (rule 3).

#### `limit_of`

- **Subject:** DistributionFamily. **Object:** DistributionFamily as `{"ref": <local ref of a DistributionFamily>}`.
- **Meaning:** The family is a limit of the other under a stated limiting operation.
- **Its qualifiers:** `limit`, `param_mapping` (besides the core qualifiers).
- **Role:** by statement kind (§10.3): `premise`, `definiens`, `conclusion` or `example_value`. **Modality:** by role (§10.6).
- **Conditions:** premises and example values: none but an index range (rule 1); otherwise a `claim` node per premise it depends on and every stated restriction on its symbols (rule 3).

#### `member_of_construction`

- **Subject:** DistributionFamily. **Object:** FamilyConstruction as `{"ref": <local ref of a FamilyConstruction>}`.
- **Meaning:** The family is the construction applied to a base. "The general normal distribution is the location-scale family associated with the standard normal distribution".
- **Its qualifiers:** `base` (besides the core qualifiers).
- **Role:** by statement kind (§10.3): `premise`, `definiens`, `conclusion` or `example_value`. **Modality:** by role (§10.6).
- **Conditions:** premises and example values: none but an index range (rule 1); otherwise a `claim` node per premise it depends on and every stated restriction on its symbols (rule 3).

#### `support`

- **Subject:** Distributed. **Object:** SetExpr as `{"t": "set", "latex": …, "symbols": {…}}`.
- **Meaning:** 
- **Role:** by statement kind (§10.3): `premise`, `definiens`, `conclusion` or `example_value`. **Modality:** by role (§10.6).
- **Conditions:** premises and example values: none but an index range (rule 1); otherwise a `claim` node per premise it depends on and every stated restriction on its symbols (rule 3).

#### `pdf`

- **Subject:** Distributed. **Object:** Formula as `{"t": "formula", "latex": …, "symbols": {…}}`.
- **Meaning:** The probability density (or mass) function, with its argument domain as a condition.
- **Role:** by statement kind (§10.3): `premise`, `definiens`, `conclusion` or `example_value`. **Modality:** by role (§10.6).
- **Conditions:** premises and example values: none but an index range (rule 1); otherwise a `claim` node per premise it depends on and every stated restriction on its symbols (rule 3).

#### `cdf`

- **Subject:** Distributed. **Object:** Formula as `{"t": "formula", "latex": …, "symbols": {…}}`.
- **Meaning:** 
- **Role:** by statement kind (§10.3): `premise`, `definiens`, `conclusion` or `example_value`. **Modality:** by role (§10.6).
- **Conditions:** premises and example values: none but an index range (rule 1); otherwise a `claim` node per premise it depends on and every stated restriction on its symbols (rule 3).

#### `mgf`

- **Subject:** Distributed. **Object:** Formula as `{"t": "formula", "latex": …, "symbols": {…}}`.
- **Meaning:** 
- **Role:** by statement kind (§10.3): `premise`, `definiens`, `conclusion` or `example_value`. **Modality:** by role (§10.6).
- **Conditions:** premises and example values: none but an index range (rule 1); otherwise a `claim` node per premise it depends on and every stated restriction on its symbols (rule 3).

#### `mean_value`

- **Subject:** Distributed. **Object:** Formula as `{"t": "formula", "latex": …, "symbols": {…}}`.
- **Meaning:** 
- **Role:** by statement kind (§10.3): `premise`, `definiens`, `conclusion` or `example_value`. **Modality:** by role (§10.6).
- **Conditions:** premises and example values: none but an index range (rule 1); otherwise a `claim` node per premise it depends on and every stated restriction on its symbols (rule 3).

#### `variance_value`

- **Subject:** Distributed. **Object:** Formula as `{"t": "formula", "latex": …, "symbols": {…}}`.
- **Meaning:** 
- **Role:** by statement kind (§10.3): `premise`, `definiens`, `conclusion` or `example_value`. **Modality:** by role (§10.6).
- **Conditions:** premises and example values: none but an index range (rule 1); otherwise a `claim` node per premise it depends on and every stated restriction on its symbols (rule 3).

## 3. Qualifiers

| Qualifier | Value | Meaning |
|---|---|---|
| `modality` | ClaimModality |  |
| `polarity` | Polarity |  |
| `hedge` | PhraseValue |  |
| `attribution` | Entity |  |
| `conditions` | string | A condition tree (D1 §7). |
| `scope` | ScopeExtent | How far a supposition reaches beyond its statement; the stored form adds the segment. |
| `valid_time` | IntervalValue |  |
| `param_values` | ParamValue (list) |  |
| `param_constraints` | string | A condition tree (D1 §7) over the base family's parameters (k = 1). |
| `transform` | Formula |  |
| `param_mapping` | ParamMapping (list) |  |
| `limit` | PhraseValue |  |
| `base` | Entity |  |
| `base_variable` | RandomVariable |  |
| `param_symbols` | ParamValue (list) |  |

## 4. Enumerations

- **StatementKind:** `definition`; `theorem`; `proposition`; `lemma`; `corollary`; `proof`; `example`; `exercise`; `solution`; `remark`; `convention`; `notation`; `assumption`; `narrative`
- **ClaimModality:** `asserted`; `supposed`; `defined`; `conventional`; `exemplified`; `posed`; `cited`
- **Polarity:** `positive`; `negative`
- **StatementRole:** `premise`; `conclusion`; `definiens`; `restriction`; `example_value`
- **ScopeExtent:** `statement`; `section`; `document`
- **BindKind:** `variable`; `param_of`; `param_expr_of`; `family_param`; `free`; `constant`; `unresolved`
- **ParseStatus:** `ok`; `partial`; `failed`
- **ParameterRole:** `location`; `scale`; `shape`; `rate`; `mean`; `variance`; `standard_deviation`; `precision`; `degrees_of_freedom`; `success_probability`; `number_of_trials`; `lower_bound`; `upper_bound`; `other`
- **ConditionPredicate:** `independent`; `identically_distributed`; `iid`

## 5. Values and condition nodes

| Value | Shape |
|---|---|
| Formula | `{"t": "formula", "latex": "b Z", "symbols": {"b": <binding>, "Z": <binding>}}` |
| Set | `{"t": "set", "latex": "(0, \\infty)", "symbols": {}}` |
| Number | `{"t": "number", "v": "1.2", "unit": null}` (only where a slot takes numbers; parameter values are formulas) |
| Phrase | `{"t": "phrase", "text": "…", "sentence": "s2"}` |
| Entity | `{"ref": "<local_ref>"}` |
| Parameter values | `{"shape": <formula>, "scale": <formula>}`, keyed by canonical parameter names (§10.4) |

| Binding | Shape |
|---|---|
| variable | `{"bind": "variable", "entity": "<local_ref>"}` |
| param_of, param_expr_of | `{"bind": "param_of", "claim": "<claim local_ref>", "param": "<canonical name>"}` |
| family_param | `{"bind": "family_param", "entity": "<FamilyParameter local_ref>"}` |
| free, constant, unresolved | `{"bind": "free"}` |

Which binding applies is the table in guideline §10.7; symbol keys carry no backslash.

| Condition node | Shape |
|---|---|
| and, or | `{"op": "and", "args": [<node>, …]}` |
| not | `{"op": "not", "arg": <node>}` |
| claim | `{"op": "claim", "ref": "<claim local_ref>"}` |
| member | `{"op": "member", "x": <formula>, "set": <set>}` |
| cmp | `{"op": "cmp", "rel": "<" | "<=" | "=" | "!=" | ">" | ">=", "lhs": <formula>, "rhs": <formula>}` |
| pred | `{"op": "pred", "name": "independent", "args": [{"ref": "<local_ref>"}, …]}` |
| phrase | `{"op": "phrase", "text": "…", "sentence": "s3"}` |
| unsupported | `{"op": "unsupported", "text": "…", "reason": "…"}` |

## 6. Worked examples

Three units from a page no annotation unit comes from, annotated under guideline v1.

### E1

Packet:

```text
# Unit E1  ·  The Weibull Distribution › The General Weibull Distribution  ·  the source marks it: definition

## Standing context
Sentences outside the unit that it depends on: where symbols it uses were introduced and are still in force, and section-wide suppositions. Cite them as `cN` (guideline §10.2).

(none)

## Text
[s1] Suppose that \(Z\) has the basic Weibull distribution with shape parameter \(k \in (0, \infty)\).
[s2] For \( b \in (0, \infty) \), random variable \(X = b Z\) has the Weibull distribution with shape parameter \(k\) and scale parameter \(b\).
```

Batch:

```json
{
 "unit_ref": "E1",
 "statements": [
  {
   "local_ref": "st1",
   "kind": "definition",
   "anchor": "unit"
  }
 ],
 "entities": [
  {
   "local_ref": "Z",
   "type": "RandomVariable",
   "label": "Z",
   "scope": "local",
   "extent": "statement",
   "symbol": "Z",
   "aliases": [],
   "identity": {}
  },
  {
   "local_ref": "X",
   "type": "RandomVariable",
   "label": "X",
   "scope": "local",
   "extent": "statement",
   "symbol": "X",
   "aliases": [],
   "identity": {}
  },
  {
   "local_ref": "BW",
   "type": "DistributionFamily",
   "label": "basic Weibull distribution",
   "scope": "global",
   "aliases": [],
   "identity": {}
  },
  {
   "local_ref": "W",
   "type": "DistributionFamily",
   "label": "Weibull distribution",
   "scope": "global",
   "aliases": [],
   "identity": {}
  },
  {
   "local_ref": "pW_shape",
   "type": "FamilyParameter",
   "label": "shape parameter",
   "scope": "global",
   "aliases": [
    "k"
   ],
   "identity": {
    "family": "W",
    "canonical_name": "shape"
   }
  },
  {
   "local_ref": "pW_scale",
   "type": "FamilyParameter",
   "label": "scale parameter",
   "scope": "global",
   "aliases": [
    "b"
   ],
   "identity": {
    "family": "W",
    "canonical_name": "scale"
   }
  }
 ],
 "claims": [
  {
   "local_ref": "c_Z_basic",
   "predicate": "has_distribution",
   "subject": "Z",
   "object": {
    "ref": "BW"
   },
   "qualifiers": {
    "modality": "supposed",
    "param_values": {
     "shape": {
      "t": "formula",
      "latex": "k",
      "symbols": {
       "k": {
        "bind": "free"
       }
      }
     }
    }
   },
   "statement": "st1",
   "statement_role": "premise",
   "evidence": [
    {
     "sentence": "s1",
     "quote": "\\(Z\\) has the basic Weibull distribution with shape parameter \\(k \\in (0, \\infty)\\)",
     "role": "primary"
    },
    {
     "sentence": "s1",
     "quote": "Suppose that",
     "role": "supporting"
    }
   ]
  },
  {
   "local_ref": "c_defines",
   "predicate": "defines",
   "subject": "st1",
   "object": {
    "ref": "W"
   },
   "qualifiers": {},
   "statement": "st1",
   "evidence": [
    {
     "sentence": "s2",
     "quote": "has the Weibull distribution with shape parameter \\(k\\) and scale parameter \\(b\\)",
     "role": "primary"
    }
   ]
  },
  {
   "local_ref": "c_X_def",
   "predicate": "defined_as",
   "subject": "X",
   "object": {
    "t": "formula",
    "latex": "b Z",
    "symbols": {
     "b": {
      "bind": "family_param",
      "entity": "pW_scale"
     },
     "Z": {
      "bind": "variable",
      "entity": "Z"
     }
    }
   },
   "qualifiers": {
    "modality": "defined",
    "conditions": {
     "op": "member",
     "x": {
      "t": "formula",
      "latex": "b",
      "symbols": {
       "b": {
        "bind": "family_param",
        "entity": "pW_scale"
       }
      }
     },
     "set": {
      "t": "set",
      "latex": "(0, \\infty)",
      "symbols": {}
     }
    }
   },
   "statement": "st1",
   "statement_role": "definiens",
   "evidence": [
    {
     "sentence": "s2",
     "quote": "\\(X = b Z\\)",
     "role": "primary"
    },
    {
     "sentence": "s2",
     "quote": "For \\( b \\in (0, \\infty) \\)",
     "role": "condition"
    }
   ]
  },
  {
   "local_ref": "c_X_weibull",
   "predicate": "has_distribution",
   "subject": "X",
   "object": {
    "ref": "W"
   },
   "qualifiers": {
    "modality": "defined",
    "param_values": {
     "shape": {
      "t": "formula",
      "latex": "k",
      "symbols": {
       "k": {
        "bind": "param_of",
        "claim": "c_Z_basic",
        "param": "shape"
       }
      }
     },
     "scale": {
      "t": "formula",
      "latex": "b",
      "symbols": {
       "b": {
        "bind": "family_param",
        "entity": "pW_scale"
       }
      }
     }
    },
    "conditions": {
     "op": "and",
     "args": [
      {
       "op": "claim",
       "ref": "c_Z_basic"
      },
      {
       "op": "member",
       "x": {
        "t": "formula",
        "latex": "k",
        "symbols": {
         "k": {
          "bind": "param_of",
          "claim": "c_Z_basic",
          "param": "shape"
         }
        }
       },
       "set": {
        "t": "set",
        "latex": "(0, \\infty)",
        "symbols": {}
       }
      },
      {
       "op": "member",
       "x": {
        "t": "formula",
        "latex": "b",
        "symbols": {
         "b": {
          "bind": "family_param",
          "entity": "pW_scale"
         }
        }
       },
       "set": {
        "t": "set",
        "latex": "(0, \\infty)",
        "symbols": {}
       }
      }
     ]
    }
   },
   "statement": "st1",
   "statement_role": "definiens",
   "evidence": [
    {
     "sentence": "s2",
     "quote": "random variable \\(X = b Z\\) has the Weibull distribution with shape parameter \\(k\\) and scale parameter \\(b\\)",
     "role": "primary"
    },
    {
     "sentence": "s1",
     "quote": "\\(k \\in (0, \\infty)\\)",
     "role": "condition"
    },
    {
     "sentence": "s2",
     "quote": "For \\( b \\in (0, \\infty) \\)",
     "role": "condition"
    }
   ]
  },
  {
   "local_ref": "c_hp_shape",
   "predicate": "has_parameter",
   "subject": "W",
   "object": {
    "ref": "pW_shape"
   },
   "qualifiers": {
    "modality": "defined"
   },
   "statement": "st1",
   "statement_role": "definiens",
   "evidence": [
    {
     "sentence": "s2",
     "quote": "shape parameter \\(k\\)",
     "role": "primary"
    }
   ]
  },
  {
   "local_ref": "c_hp_scale",
   "predicate": "has_parameter",
   "subject": "W",
   "object": {
    "ref": "pW_scale"
   },
   "qualifiers": {
    "modality": "defined"
   },
   "statement": "st1",
   "statement_role": "definiens",
   "evidence": [
    {
     "sentence": "s2",
     "quote": "scale parameter \\(b\\)",
     "role": "primary"
    }
   ]
  },
  {
   "local_ref": "c_dom_shape",
   "predicate": "parameter_domain",
   "subject": "pW_shape",
   "object": {
    "t": "set",
    "latex": "(0, \\infty)",
    "symbols": {}
   },
   "qualifiers": {
    "modality": "defined"
   },
   "statement": "st1",
   "statement_role": "definiens",
   "evidence": [
    {
     "sentence": "s1",
     "quote": "\\(k \\in (0, \\infty)\\)",
     "role": "primary"
    }
   ]
  },
  {
   "local_ref": "c_dom_scale",
   "predicate": "parameter_domain",
   "subject": "pW_scale",
   "object": {
    "t": "set",
    "latex": "(0, \\infty)",
    "symbols": {}
   },
   "qualifiers": {
    "modality": "defined"
   },
   "statement": "st1",
   "statement_role": "definiens",
   "evidence": [
    {
     "sentence": "s2",
     "quote": "\\( b \\in (0, \\infty) \\)",
     "role": "primary"
    }
   ]
  },
  {
   "local_ref": "c_W_transform",
   "predicate": "transformation_of",
   "subject": "W",
   "object": {
    "ref": "BW"
   },
   "qualifiers": {
    "modality": "defined",
    "transform": {
     "t": "formula",
     "latex": "b Z",
     "symbols": {
      "b": {
       "bind": "family_param",
       "entity": "pW_scale"
      },
      "Z": {
       "bind": "variable",
       "entity": "Z"
      }
     }
    },
    "param_mapping": {
     "shape": "shape"
    },
    "conditions": {
     "op": "member",
     "x": {
      "t": "formula",
      "latex": "b",
      "symbols": {
       "b": {
        "bind": "family_param",
        "entity": "pW_scale"
       }
      }
     },
     "set": {
      "t": "set",
      "latex": "(0, \\infty)",
      "symbols": {}
     }
    }
   },
   "statement": "st1",
   "statement_role": "definiens",
   "evidence": [
    {
     "sentence": "s2",
     "quote": "random variable \\(X = b Z\\) has the Weibull distribution",
     "role": "primary"
    },
    {
     "sentence": "s1",
     "quote": "\\(Z\\) has the basic Weibull distribution",
     "role": "supporting"
    }
   ]
  }
 ],
 "alternatives": [],
 "unsupported": []
}
```

### E2

Packet:

```text
# Unit E2  ·  The Weibull Distribution › The General Weibull Distribution › Related Distributions  ·  the source marks it: theorem

## Standing context
Sentences outside the unit that it depends on: where symbols it uses were introduced and are still in force, and section-wide suppositions. Cite them as `cN` (guideline §10.2).

(none)

## Text
[s1] Suppose that \(X\) has the Weibull distribution with shape parameter \(k \in (0, \infty)\) and scale parameter \(b \in (0, \infty)\).
[s2] If \(c \in (0, \infty)\) then \(Y = c X\) has the Weibull distribution with shape parameter \(k\) and scale parameter \(b c\).
--- Details: ---
[s3] By definition [16], we can take \( X = b Z \) where \( Z \) has the basic Weibull distribution with shape parameter \( k \).
[s4] But then \( Y = c X = (b c) Z \).
```

Batch:

```json
{
 "unit_ref": "E2",
 "statements": [
  {
   "local_ref": "st1",
   "kind": "theorem",
   "anchor": [
    "s1",
    "s2"
   ]
  },
  {
   "local_ref": "st2",
   "kind": "proof",
   "anchor": [
    "s3",
    "s4"
   ]
  }
 ],
 "entities": [
  {
   "local_ref": "X",
   "type": "RandomVariable",
   "label": "X",
   "scope": "local",
   "extent": "statement",
   "symbol": "X",
   "aliases": [],
   "identity": {}
  },
  {
   "local_ref": "Y",
   "type": "RandomVariable",
   "label": "Y",
   "scope": "local",
   "extent": "statement",
   "symbol": "Y",
   "aliases": [],
   "identity": {}
  },
  {
   "local_ref": "W",
   "type": "DistributionFamily",
   "label": "Weibull distribution",
   "scope": "global",
   "aliases": [],
   "identity": {}
  }
 ],
 "claims": [
  {
   "local_ref": "c_X_weibull",
   "predicate": "has_distribution",
   "subject": "X",
   "object": {
    "ref": "W"
   },
   "qualifiers": {
    "modality": "supposed",
    "param_values": {
     "shape": {
      "t": "formula",
      "latex": "k",
      "symbols": {
       "k": {
        "bind": "free"
       }
      }
     },
     "scale": {
      "t": "formula",
      "latex": "b",
      "symbols": {
       "b": {
        "bind": "free"
       }
      }
     }
    }
   },
   "statement": "st1",
   "statement_role": "premise",
   "evidence": [
    {
     "sentence": "s1",
     "quote": "\\(X\\) has the Weibull distribution with shape parameter \\(k \\in (0, \\infty)\\) and scale parameter \\(b \\in (0, \\infty)\\)",
     "role": "primary"
    },
    {
     "sentence": "s1",
     "quote": "Suppose that",
     "role": "supporting"
    }
   ]
  },
  {
   "local_ref": "c_Y_def",
   "predicate": "defined_as",
   "subject": "Y",
   "object": {
    "t": "formula",
    "latex": "c X",
    "symbols": {
     "c": {
      "bind": "free"
     },
     "X": {
      "bind": "variable",
      "entity": "X"
     }
    }
   },
   "qualifiers": {
    "modality": "defined",
    "conditions": {
     "op": "member",
     "x": {
      "t": "formula",
      "latex": "c",
      "symbols": {
       "c": {
        "bind": "free"
       }
      }
     },
     "set": {
      "t": "set",
      "latex": "(0, \\infty)",
      "symbols": {}
     }
    }
   },
   "statement": "st1",
   "statement_role": "definiens",
   "evidence": [
    {
     "sentence": "s2",
     "quote": "\\(Y = c X\\)",
     "role": "primary"
    },
    {
     "sentence": "s2",
     "quote": "If \\(c \\in (0, \\infty)\\)",
     "role": "condition"
    }
   ]
  },
  {
   "local_ref": "c_Y_weibull",
   "predicate": "has_distribution",
   "subject": "Y",
   "object": {
    "ref": "W"
   },
   "qualifiers": {
    "modality": "asserted",
    "param_values": {
     "shape": {
      "t": "formula",
      "latex": "k",
      "symbols": {
       "k": {
        "bind": "param_of",
        "claim": "c_X_weibull",
        "param": "shape"
       }
      }
     },
     "scale": {
      "t": "formula",
      "latex": "b c",
      "symbols": {
       "b": {
        "bind": "param_of",
        "claim": "c_X_weibull",
        "param": "scale"
       },
       "c": {
        "bind": "free"
       }
      }
     }
    },
    "conditions": {
     "op": "and",
     "args": [
      {
       "op": "claim",
       "ref": "c_X_weibull"
      },
      {
       "op": "member",
       "x": {
        "t": "formula",
        "latex": "k",
        "symbols": {
         "k": {
          "bind": "param_of",
          "claim": "c_X_weibull",
          "param": "shape"
         }
        }
       },
       "set": {
        "t": "set",
        "latex": "(0, \\infty)",
        "symbols": {}
       }
      },
      {
       "op": "member",
       "x": {
        "t": "formula",
        "latex": "b",
        "symbols": {
         "b": {
          "bind": "param_of",
          "claim": "c_X_weibull",
          "param": "scale"
         }
        }
       },
       "set": {
        "t": "set",
        "latex": "(0, \\infty)",
        "symbols": {}
       }
      },
      {
       "op": "member",
       "x": {
        "t": "formula",
        "latex": "c",
        "symbols": {
         "c": {
          "bind": "free"
         }
        }
       },
       "set": {
        "t": "set",
        "latex": "(0, \\infty)",
        "symbols": {}
       }
      }
     ]
    }
   },
   "statement": "st1",
   "statement_role": "conclusion",
   "evidence": [
    {
     "sentence": "s2",
     "quote": "\\(Y = c X\\) has the Weibull distribution with shape parameter \\(k\\) and scale parameter \\(b c\\)",
     "role": "primary"
    },
    {
     "sentence": "s2",
     "quote": "If \\(c \\in (0, \\infty)\\)",
     "role": "condition"
    },
    {
     "sentence": "s1",
     "quote": "\\(k \\in (0, \\infty)\\)",
     "role": "condition"
    },
    {
     "sentence": "s1",
     "quote": "\\(b \\in (0, \\infty)\\)",
     "role": "condition"
    }
   ]
  },
  {
   "local_ref": "c_proves",
   "predicate": "proves",
   "subject": "st2",
   "object": {
    "ref": "st1"
   },
   "qualifiers": {},
   "statement": "st2",
   "evidence": [
    {
     "sentence": "s4",
     "quote": "But then \\( Y = c X = (b c) Z \\)",
     "role": "primary"
    }
   ]
  }
 ],
 "alternatives": [],
 "unsupported": []
}
```

### E3

Packet:

```text
# Unit E3  ·  The Weibull Distribution › Computational Exercises  ·  the source marks it: exercise

## Standing context
Sentences outside the unit that it depends on: where symbols it uses were introduced and are still in force, and section-wide suppositions. Cite them as `cN` (guideline §10.2).

(none)

## Text
[s1] The lifetime \(T\) of a device (in hours) has the Weibull distribution with shape parameter \(k = 1.2\) and scale parameter \(b = 1000\).
[s2] (a) Find the probability that the device will last at least 1500 hours.
[s3] (b) Approximate the mean and standard deviation of \(T\).
[s4] (c) Compute the failure rate function.
--- Details: ---
[s5] (a) \(\P(T \gt 1500) = 0.1966\)
[s6] (b) \(\E(T) = 940.7\), \(\sd(T) = 787.2\)
[s7] (c) \(h(t) = 0.000301 t^{0.2}\)
```

Batch:

```json
{
 "unit_ref": "E3",
 "statements": [
  {
   "local_ref": "st1",
   "kind": "exercise",
   "anchor": [
    "s1",
    "s2",
    "s3",
    "s4"
   ]
  },
  {
   "local_ref": "st2",
   "kind": "solution",
   "anchor": [
    "s5",
    "s6",
    "s7"
   ]
  }
 ],
 "entities": [
  {
   "local_ref": "T",
   "type": "RandomVariable",
   "label": "T",
   "scope": "local",
   "extent": "statement",
   "symbol": "T",
   "aliases": [],
   "identity": {}
  },
  {
   "local_ref": "W",
   "type": "DistributionFamily",
   "label": "Weibull distribution",
   "scope": "global",
   "aliases": [],
   "identity": {}
  }
 ],
 "claims": [
  {
   "local_ref": "c_T_weibull",
   "predicate": "has_distribution",
   "subject": "T",
   "object": {
    "ref": "W"
   },
   "qualifiers": {
    "modality": "exemplified",
    "param_values": {
     "shape": {
      "t": "formula",
      "latex": "1.2",
      "symbols": {}
     },
     "scale": {
      "t": "formula",
      "latex": "1000",
      "symbols": {}
     }
    }
   },
   "statement": "st1",
   "statement_role": "example_value",
   "evidence": [
    {
     "sentence": "s1",
     "quote": "The lifetime \\(T\\) of a device (in hours) has the Weibull distribution with shape parameter \\(k = 1.2\\) and scale parameter \\(b = 1000\\)",
     "role": "primary"
    }
   ]
  },
  {
   "local_ref": "c_proves",
   "predicate": "proves",
   "subject": "st2",
   "object": {
    "ref": "st1"
   },
   "qualifiers": {},
   "statement": "st2",
   "evidence": [
    {
     "sentence": "s7",
     "quote": "\\(h(t) = 0.000301 t^{0.2}\\)",
     "role": "primary"
    }
   ]
  }
 ],
 "alternatives": [],
 "unsupported": [
  {
   "local_ref": "u1",
   "sentence": "s1",
   "quote": "(in hours)",
   "reason": "The unit of measurement of a random variable cannot be stated (no predicate)."
  },
  {
   "local_ref": "u2",
   "sentence": "s2",
   "quote": "Find the probability that the device will last at least 1500 hours",
   "reason": "asked quantity"
  },
  {
   "local_ref": "u3",
   "sentence": "s3",
   "quote": "Approximate the mean and standard deviation of \\(T\\)",
   "reason": "asked quantity"
  },
  {
   "local_ref": "u4",
   "sentence": "s4",
   "quote": "Compute the failure rate function",
   "reason": "asked quantity"
  }
 ]
}
```

