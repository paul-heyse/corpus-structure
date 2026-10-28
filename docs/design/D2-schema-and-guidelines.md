# D2 · Schema conventions, compilers and the statistics pack

**Proposed (2026-10-28).** How a domain is declared, how one declaration drives extraction,
LLM output, validation and the annotation guideline, and the first version of the statistics
pack. The knowledge types the schema populates are defined in [D1](D1-knowledge-representation.md).

## 1. Principles

1. **One declaration per domain.** A domain pack's LinkML schema is the single source for entity
   types, predicates, qualifiers, enums, condition predicates and validation rules. Nothing about
   a domain is hard-coded in Python except verifiers ([§7.6](#76-domain-verifiers)).
2. **Compiled, not interpreted ad hoc.** Every consumer of the schema (GLiNER2, the LLM prompt
   and JSON Schema, the rule engine, the database's schema tables, the guideline inventory)
   receives a deterministic compiled artifact. The artifact's hash is part of the configuration
   hash of every method that uses it, so a schema change invalidates exactly the work it affects
   ([D6 §4](D6-orchestration-metrics-policies.md#4-caching-and-reuse)).
3. **Descriptions are functional.** GLiNER2 uses label descriptions as model input and the LLM
   reads them in its prompt. A class or predicate description is written for those readers:
   what the span or fact looks like in text, with a short example.
4. **The schema grows by versions.** Additions are cheap; renames and splits carry a migration
   that also rewrites claims in kept runs and goldens ([§8](#8-versioning-and-migration)).

## 2. Domain pack layout

```text
domains/<name>/
  schema/
    <name>.yaml          LinkML schema; imports ../../core/schema/core.yaml
    rules.yaml           validation rules (rule-engine expressions), §7.4
    migrations/          schema migration mappings for breaking changes, §8
  guideline.md           the annotation guideline (§10 is v0 for statistics)
  policies.yaml          routing policies for this domain (D6 §7)
  methods.yaml           domain parameters of methods: source profiles, math macro map, binder
                         lexicon, alias head words, cue lexicons, patterns (D4 §1)
  verifiers.py           optional domain verifiers implementing validate.Verifier (§7.6)
  README.md              scope of the pack, source corpora, owner notes
domains/core/schema/core.yaml   core classes, predicates, value classes and enums shared by all packs
```

A **schema version** is the content hash over `<name>.yaml`, `rules.yaml` and the imported
`core.yaml`. The guideline is versioned separately ([D7 §2](D7-evaluation-goldens-outer-loop.md#2-guidelines)),
because guideline wording changes far more often than the schema.

## 3. The `ci:` annotation vocabulary

LinkML carries our extraction and identity semantics in annotations with prefix
`ci: https://corpus-structure.dev/ci/` (declared in `core.yaml`). LinkML structure (classes,
slots, ranges, enums, `is_a`, `mixins`, `multivalued`, `required`, `description`) keeps its
normal meaning.

### 3.1 On classes

| Annotation | Values | Meaning |
|---|---|---|
| `ci:kind` | `entity`, `value`, `abstract` | `entity`: instances become D1 entities. `value`: a value class (Formula, SetExpr). `abstract`: not instantiated |
| `ci:scope` | `global`, `local` | D1 §4.2. Required for `entity` classes |
| `ci:identity_keys` | list of slot names | Identity attributes beyond the label (e.g. `[family, canonical_name]` for `FamilyParameter`); D1 §10 |
| `ci:extract` | `mention`, `none` | Whether extraction looks for mentions of this class |
| `ci:gliner_label` | string | Label shown to GLiNER2; defaults to the class name in words |
| `ci:reify` | `true` | Facts of this class are reified entities with role claims (D1 §5.4) |
| `ci:examples` | list of strings | Short positive examples, used in the GLiNER2 description and the LLM prompt |

### 3.2 On slots (predicates and qualifiers)

| Annotation | Values | Meaning |
|---|---|---|
| `ci:role` | `predicate`, `qualifier`, `identity`, `field` | `predicate`: claims use it. `qualifier`: usable as a qualifier on the predicates that list it. `identity`: an identity attribute of a class. `field`: a field of a value class |
| `ci:object` | `entity`, `formula`, `set`, `text`, `number`, `enum`, `date`, `interval`, `map` | Object value type (D1 §6); for `entity` the LinkML `range` names the class |
| `ci:qualifiers` | list of qualifier slot names | Schema qualifiers allowed on this predicate (D1 §5.3) |
| `ci:identity_qualifiers` | list | Which of them enter the claim key (D1 §10.1) |
| `ci:extract` | `relation`, `record`, `llm`, `none` | How extraction proposes claims of this predicate: GLiNER2 relation, GLiNER2 record field, LLM only, or not extracted (derived only) |
| `ci:symmetric` | `true` | `identical_parameter`-style predicates; consolidation orders subject and object canonically |
| `ci:functional` | `true` | At most one accepted object per subject and context; a second one is a conflict (D5 §8) |
| `ci:record` | structure name | For `ci:extract: record`, the GLiNER2 structure that carries it (§7.2) |
| `ci:anchor` | `true` | On a record field: the GLiNER2 record-mode anchor |
| `ci:examples` | list | As on classes |

### 3.3 On enums and permissible values

| Annotation | Meaning |
|---|---|
| `ci:extract: attribute` with `ci:applies_to: <class>` | Compile to a GLiNER2 span attribute group on mentions of that class |
| `ci:extract: classification` with `ci:target: <segment kind>` | Compile to a GLiNER2 classification task on segments of that kind |
| `ci:z3` (on a permissible value of a condition-predicate enum) | Name of the z3 encoding for this condition predicate, or absent if not encodable |
| `ci:arity` | For condition predicates: `1`, `2`, `2+` |

## 4. Predicates and qualifiers

A predicate is a LinkML slot with `ci:role: predicate`. Its `domain` is the subject class (or a
mixin shared by several classes); its `range` is the object class for `ci:object: entity`, or a
value class.

Qualifiers are slots with `ci:role: qualifier`. A predicate lists the schema qualifiers it
accepts in `ci:qualifiers`. Core qualifiers (`modality`, `polarity`, `hedge`, `attribution`,
`conditions`, `scope`, `valid_time`) are always allowed and never listed. A qualifier with
`ci:object: map` is a mapping from string keys to values; its LinkML range is a class with a
`key` and a `value` slot, `multivalued: true`, `inlined: true`. `param_values` is the main
example: keys are family-parameter canonical names, values are formulas.

Naming: predicates are lowercase verbs or verb phrases in snake case (`has_distribution`,
`identical_parameter`), stored with the domain prefix (`stat:has_distribution`). Core
predicates use `core:`.

## 5. Condition predicates

Condition predicates are the permissible values of an enum named `ConditionPredicate` in the
domain schema, each with `ci:arity`, the class of its arguments (`ci:args`) and optionally
`ci:z3`. They appear in condition trees as `pred` nodes (D1 §7). Statistics v0 declares
`independent`, `identically_distributed` and `iid`.

## 6. The core schema

`domains/core/schema/core.yaml` is imported by every pack. It declares:

| Element | Kind | Content |
|---|---|---|
| `Entity` | abstract class | Base of all entity classes |
| `Statement` | entity class, local | D1 §4.3; slot `kind` (enum `StatementKind`) as identity attribute |
| `StatementKind` | enum, `ci:extract: classification`, target `unit` and `paragraph` | Values in D1 §4.3 |
| `Formula`, `SetExpr`, `TextValue`, `NumberValue`, `DateValue`, `IntervalValue`, `PhraseValue` | value classes | Fields as D1 §6 |
| `SymbolBinding` | value class | D1 §6.1 binding kinds |
| `ClaimModality` | enum, `ci:extract: classification`, target `sentence` | D1 §5.2 |
| `defines` | predicate | `Statement` → `Entity` |
| `proves`, `follows_from` | predicates | `Statement` → `Statement` |
| `refers_to` | predicate | `Statement` → `Entity` |
| `unschematized` | predicate | `Entity` → `PhraseValue`; D1 §8.1 status `unsupported` |

## 7. Compilers

Each compiler is a pure function of a loaded schema version (`linkml_runtime.SchemaView`) and
returns an artifact plus its hash. Output ordering is deterministic (sorted by name) so equal
schemas produce byte-equal artifacts.

### 7.1 To schema tables

Writes `meta.schema_class`, `meta.schema_slot`, `meta.schema_enum` and `meta.schema_rule` rows
([D3 §3](D3-database.md#3-meta-schema-guidelines-and-domain-declarations)) with induced slots
(inheritance and mixins resolved through `SchemaView.class_induced_slots`). These rows let SQL
join claims to their schema definitions and let metrics group by class and predicate.

### 7.2 To GLiNER2 schemas

Two artifacts, because GLiNER2's ordinary and joint decoders have different semantics
([library overview](../libraries/gliner2.md) §4.3):

**(a) The extraction schema**, built with `Schema.from_dict` (package 2.1.0 supports parity with
the builder: descriptions, thresholds, examples, attributes):

| GLiNER2 element | Compiled from |
|---|---|
| Entity types with descriptions | Classes with `ci:kind: entity` and `ci:extract: mention`; label = `ci:gliner_label`; description = LinkML `description` plus `ci:examples` |
| Span attribute groups | Enums with `ci:extract: attribute`; `applies_to` = `ci:applies_to`; `qualify_labels=True` |
| Classification tasks | Enums with `ci:extract: classification` (run on segments of the target kind by M05) |
| Structures (record mode) | One structure per `ci:record` name; fields from the predicates that name it; anchor = the field marked `ci:anchor: true`; cardinalities from `required` and `multivalued` |
| Relations (independent) | Predicates with `ci:extract: relation`, label = predicate name in words, description from the slot |

**(b) The joint schema** for `JointIE`: entity types as in (a); one `.relation(name, head=…,
tail=…)` per `ci:extract: relation` predicate with head = domain class label and tail = range
class label; `unique_head=True` where `ci:functional: true`; `.no_self_loops()` always;
`symmetric` and `inverse` from `ci:symmetric` and `inverse`.

Illustrative fragment of (a) for statistics v0 (the exact key names of `Schema.from_dict` are
checked in spike S4; `OPEN-D2-1`):

```json
{
  "entities": {
    "random variable": {"description": "A symbol denoting a random variable, such as X, Y, Z or X_1 …"},
    "distribution family": {"description": "A named family of probability distributions, such as the normal, gamma or lognormal distribution; also adjectival uses such as 'normally distributed'"},
    "distribution parameter": {"description": "A named parameter of a distribution family: location parameter, scale parameter, shape parameter k, rate …"}
  },
  "structures": {
    "distribution statement": {
      "mode": "natural", "anchor": "variable",
      "fields": {
        "variable": {"dtype": "str", "cardinality": "required_one"},
        "family": {"dtype": "str", "cardinality": "required_one"},
        "parameter": {"dtype": "list"}
      }
    }
  }
}
```

**Math in text.** GLiNER2 sees the segment text. Whether LaTeX is passed raw, or each math span
is replaced by a placeholder token (`⟨m3⟩`) whose original is restored after extraction, is
decided by spike S2 (`OPEN-D2-2`). The compiler emits the schema only; the masking choice lives
in the method configuration of M06/M07.

### 7.3 To JSON Schema for LLM claim proposals

The LLM methods (M10, M16) and Opus produce claims in D1 form with local references. The
compiler emits one JSON Schema (draft 2020-12) used both as the vLLM structured-output schema
and for validating Opus submissions:

```text
ClaimProposalBatch
  unit_ref            string
  entities[]          { local_ref, type ∈ enum(entity classes), label, scope ∈ {global, local},
                        symbol?, aliases[], identity{…} }
  statements[]        { local_ref, kind ∈ enum(StatementKind), anchors[] (span offsets) }
  claims[]            oneOf per predicate:
                        { local_ref, predicate: const <p>, subject: local_ref,
                          object: local_ref | <value schema of p>,
                          qualifiers: { core qualifiers, schema qualifiers of p },
                          statement?, statement_role?, evidence[] { start, end, role } }
  unsupported[]       { text, start, end, reason }
```

Per-predicate branches restrict the subject and object types (via an `entity_types` side table
resolved at validation, because JSON Schema cannot follow local references), the value type, and
the allowed schema qualifiers. Enum values are inlined. Descriptions are carried into the schema
so the model sees them. The same compiler emits a compact **prompt inventory**: one line per
class and predicate with its description and examples, ordered by class.

**Model-facing and stored forms.** The compiler emits the batch schema twice. The *model-facing*
form, given to LLMs and Opus, cites evidence and statement anchors by quote (`{sentence, quote,
role}`), because models do not count characters reliably. The *stored* form, held in
`claim_proposal` observations and golden items, has rendition offsets (`{start, end, role}`).
Quote location is shared post-processing ([D4 §4.3](D4-method-catalog.md#43-output-form-and-post-processing)).

LinkML's own `gen-json-schema` is used for the value classes (`Formula`, `SetExpr`, …) and the
compiler assembles the batch schema around them.

### 7.4 To rule-engine rules

`rules.yaml` holds named rules:

```yaml
rules:
  - id: stat.param_keys_known
    applies_to: stat:has_distribution
    severity: warning          # warning | error
    description: Every param_values key is a parameter the family has.
    when: "claim.predicate == 'stat:has_distribution'"
    check: "all([k in family_params(claim.object) for k in claim.qualifiers.param_values.keys])"
```

The compiler parses each `when` and `check` with `rule_engine.Rule` under a typed `Context`
whose type resolver declares the claim context symbols ([D5 §8.2](D5-consolidation-identity-confidence.md#82-rule-context))
and registered functions such as `family_params`. A rule that fails to type-check fails
compilation, so a broken rule never reaches a run. Severity `error` makes a failing claim
`rejected`; `warning` records a validation observation and lowers confidence (D5 §6). The exact
expression syntax is checked in spike S4 (`OPEN-D2-3`).

`rules.yaml` also has a `derive:` section: named derivation rules (for statistics, variance to
standard deviation, transitivity of `special_case_of`, applying a construction's parameter
mapping). Each names its source predicates, a match condition and a template for the derived
claim; M23 applies them ([D4 M23](D4-method-catalog.md#m23-deriveclaims)). Derivations that need
algebra call registered SymPy helpers, never inline code.

### 7.5 To the guideline inventory

The guideline (§10) has a generated section listing every class, predicate, qualifier and enum
value with its description. The compiler regenerates it on every schema version, so the
guideline Opus writes goldens from cannot drift from the schema.

### 7.6 Domain verifiers

A verifier is Python in `domains/<name>/verifiers.py` implementing:

```python
class Verifier(Protocol):
    name: str
    version: str
    predicates: frozenset[str]          # which claims it can check
    def verify(self, claim: ClaimView, ctx: VerifyContext) -> Verification: ...
```

`Verification` is `consistent`, `refuted` or `not_checkable`, with detail. Verifiers write
`verification` observations; they never change claims directly. The statistics pack's verifiers
are listed in [D4 M21](D4-method-catalog.md#m21-verifystatistics).

## 8. Versioning and migration

| Change | Classification | What happens |
|---|---|---|
| Add a class, predicate, qualifier, enum value or rule | Additive | New schema version. Cached work whose compiled artifacts did not change is reused (most of it: extraction schemas change, so extraction re-runs; ingest does not) |
| Edit a description or examples | Additive | New version; extraction re-runs, because descriptions are model input |
| Rename, split, merge or remove a class or predicate | Breaking | New version plus a migration: a YAML mapping (`old → new`, with a split rule for splits) applied to golden items and, optionally, to kept runs' claims. Orphans are reported |
| Change an identity key or identity qualifier | Breaking | As above; claim keys change, so cross-run comparison uses alignment, not keys |

Opus proposes schema changes through `propose_schema_change` ([D8](D8-agent-and-query-interfaces.md));
a proposal is a diff plus rationale plus, for breaking changes, the migration mapping. The
operator does not approve content but sets direction through the guideline ([D7 §8](D7-evaluation-goldens-outer-loop.md#8-the-operators-outer-loop));
promotion of a schema version follows the experiment rule ([D7 §7](D7-evaluation-goldens-outer-loop.md#7-experiments-and-promotion)).

## 9. Statistics schema v0

Draft for `domains/statistics/schema/statistics.yaml`. It covers the trace and the spike pages
(LocationScale, Normal, LogNormal, Gamma). Descriptions are first drafts for spikes S2 and S3 to
test and improve.

```yaml
id: https://corpus-structure.dev/domains/statistics
name: statistics
version: 0.1.0
prefixes:
  linkml: https://w3id.org/linkml/
  ci: https://corpus-structure.dev/ci/
  stat: https://corpus-structure.dev/domains/statistics/
  core: https://corpus-structure.dev/core/
default_prefix: stat
imports:
  - linkml:types
  - ../../core/schema/core

classes:
  DistributionFamily:
    is_a: Entity
    mixins: [Distributed]
    description: >-
      A named family of probability distributions, possibly with parameters: the normal
      distribution, the gamma distribution, the standard normal distribution. Mentions include
      adjectival forms ("normally distributed", "has a gamma distribution").
    annotations:
      ci:kind: entity
      ci:scope: global
      ci:extract: mention
      ci:gliner_label: distribution family
      ci:examples: ["the normal distribution", "lognormal distribution", "normally distributed"]

  FamilyConstruction:
    is_a: Entity
    description: >-
      A way of generating a family of distributions from a base distribution, such as the
      location-scale family, the location family or the scale family associated with a
      distribution, or the general exponential family. Not itself a single distribution family.
    annotations:
      ci:kind: entity
      ci:scope: global
      ci:extract: mention
      ci:gliner_label: family construction
      ci:examples: ["location-scale family", "scale family associated with the given distribution"]

  FamilyParameter:
    is_a: Entity
    description: >-
      A parameter of a distribution family or construction, such as the location parameter,
      the scale parameter, the shape parameter k, the rate, the mean or the standard deviation
      when these parameterize the family.
    slots: [family, canonical_name]
    annotations:
      ci:kind: entity
      ci:scope: global
      ci:identity_keys: [family, canonical_name]
      ci:extract: mention
      ci:gliner_label: distribution parameter
      ci:examples: ["location parameter", "shape parameter k", "the rate parameter"]

  RandomVariable:
    is_a: Entity
    mixins: [Distributed]
    description: >-
      A random variable denoted by a symbol (X, Y, Z, X_1, W) or by an expression in other
      random variables (a + b X, e^Y, X_1 + X_2). Local to the statement or section that
      introduces it.
    slots: [symbol]
    annotations:
      ci:kind: entity
      ci:scope: local
      ci:extract: mention
      ci:gliner_label: random variable
      ci:examples: ["X", "a + b X", "X_1 + X_2"]

  Concept:
    is_a: Entity
    description: >-
      A defined mathematical term that is not a distribution family, construction or
      parameter: the gamma function, the standard score, the moment generating function.
    annotations:
      ci:kind: entity
      ci:scope: global
      ci:extract: mention
      ci:gliner_label: mathematical concept

  Distributed:
    mixin: true
    description: Things that have a distribution and its characteristics.
    annotations:
      ci:kind: abstract

  ParamValue:
    description: One parameter-to-value entry of a param_values map.
    attributes:
      key: {range: string, identifier: true, annotations: {ci:role: field}}
      value: {range: Formula, annotations: {ci:role: field}}
    annotations:
      ci:kind: value

  ParamMapping:
    description: One target-parameter to source-parameter entry of a param_mapping map.
    attributes:
      key: {range: string, identifier: true, annotations: {ci:role: field}}
      value: {range: string, annotations: {ci:role: field}}
    annotations:
      ci:kind: value

slots:
  # identity attributes
  family:
    range: Entity
    annotations: {ci:role: identity}
  canonical_name:
    range: string
    description: The parameter's role name when stated (location, scale, shape, …), else its source symbol.
    annotations: {ci:role: identity}
  symbol:
    range: string
    annotations: {ci:role: identity}

  # predicates
  has_distribution:
    domain: RandomVariable
    range: DistributionFamily
    description: >-
      The random variable has a distribution in the family, optionally with stated parameter
      values. "X is normally distributed with mean μ and variance σ²".
    annotations:
      ci:role: predicate
      ci:object: entity
      ci:qualifiers: [param_values]
      ci:identity_qualifiers: [param_values]
      ci:extract: relation
      ci:record: distribution statement
  defined_as:
    domain: RandomVariable
    range: Formula
    description: The random variable is defined by a formula in other variables. "let X = a + b Z".
    annotations: {ci:role: predicate, ci:object: formula, ci:extract: llm}
  takes_values_in:
    domain: RandomVariable
    range: SetExpr
    description: The random variable's values lie in the set. "with values in ℝ".
    annotations: {ci:role: predicate, ci:object: set, ci:extract: llm}
  has_parameter:
    domain: Entity
    range: FamilyParameter
    description: A family or construction has this parameter.
    annotations: {ci:role: predicate, ci:object: entity, ci:extract: relation}
  parameter_role:
    domain: FamilyParameter
    range: ParameterRole
    multivalued: true
    description: The parameter plays this role. "σ is the shape parameter".
    annotations: {ci:role: predicate, ci:object: enum, ci:extract: llm}
  parameter_domain:
    domain: FamilyParameter
    range: SetExpr
    description: The set of allowed values. "b ∈ (0, ∞)".
    annotations: {ci:role: predicate, ci:object: set, ci:extract: llm, ci:functional: true}
  identical_parameter:
    domain: FamilyParameter
    range: FamilyParameter
    description: Two parameter names denote the same parameter of the family. "the location and scale parameters are also the mean and standard deviation, respectively".
    annotations: {ci:role: predicate, ci:object: entity, ci:symmetric: true, ci:extract: llm}
  derived_parameter:
    domain: FamilyParameter
    range: Formula
    description: The parameter equals a formula in the family's other parameters. "e^μ is the scale parameter".
    annotations: {ci:role: predicate, ci:object: formula, ci:extract: llm}
  special_case_of:
    domain: DistributionFamily
    range: Entity
    description: The family is the special case of another family or construction obtained under parameter constraints. "The exponential distribution is the gamma distribution with k = 1".
    annotations:
      ci:role: predicate
      ci:object: entity
      ci:qualifiers: [param_constraints]
      ci:identity_qualifiers: [param_constraints]
      ci:extract: llm
  transformation_of:
    domain: DistributionFamily
    range: DistributionFamily
    description: Variables in this family arise by transforming a variable of the other family. "X = e^Y has the lognormal distribution".
    annotations:
      ci:role: predicate
      ci:object: entity
      ci:qualifiers: [transform, param_mapping]
      ci:identity_qualifiers: [transform]
      ci:extract: llm
  limit_of:
    domain: DistributionFamily
    range: DistributionFamily
    description: The family is a limit of the other under a stated limiting operation.
    annotations: {ci:role: predicate, ci:object: entity, ci:qualifiers: [limit, param_mapping], ci:extract: llm}
  member_of_construction:
    domain: DistributionFamily
    range: FamilyConstruction
    description: The family is the construction applied to a base. "The general normal distribution is the location-scale family associated with the standard normal distribution".
    annotations: {ci:role: predicate, ci:object: entity, ci:qualifiers: [base], ci:identity_qualifiers: [base], ci:extract: llm}
  construction_formula:
    domain: FamilyConstruction
    range: Formula
    description: The formula generating members of the construction.
    annotations: {ci:role: predicate, ci:object: formula, ci:qualifiers: [base_variable, param_symbols], ci:extract: llm}
  support:
    domain: Distributed
    range: SetExpr
    annotations: {ci:role: predicate, ci:object: set, ci:extract: llm}
  pdf:
    domain: Distributed
    range: Formula
    description: The probability density (or mass) function, with its argument domain as a condition.
    annotations: {ci:role: predicate, ci:object: formula, ci:extract: llm}
  cdf:
    domain: Distributed
    range: Formula
    annotations: {ci:role: predicate, ci:object: formula, ci:extract: llm}
  mgf:
    domain: Distributed
    range: Formula
    annotations: {ci:role: predicate, ci:object: formula, ci:extract: llm}
  mean_value:
    domain: Distributed
    range: Formula
    annotations: {ci:role: predicate, ci:object: formula, ci:extract: llm}
  variance_value:
    domain: Distributed
    range: Formula
    annotations: {ci:role: predicate, ci:object: formula, ci:extract: llm}
  definition_formula:
    domain: Concept
    range: Formula
    annotations: {ci:role: predicate, ci:object: formula, ci:extract: llm}

  # qualifiers
  param_values:
    range: ParamValue
    multivalued: true
    inlined: true
    annotations: {ci:role: qualifier, ci:object: map}
  param_constraints:
    range: Formula
    description: A condition tree over the base family's parameters (k = 1).
    annotations: {ci:role: qualifier, ci:object: formula}
  transform:
    range: Formula
    annotations: {ci:role: qualifier, ci:object: formula}
  param_mapping:
    range: ParamMapping
    multivalued: true
    inlined: true
    annotations: {ci:role: qualifier, ci:object: map}
  limit:
    range: PhraseValue
    annotations: {ci:role: qualifier, ci:object: text}
  base:
    range: Entity
    annotations: {ci:role: qualifier, ci:object: entity}
  base_variable:
    range: RandomVariable
    annotations: {ci:role: qualifier, ci:object: entity}
  param_symbols:
    range: ParamValue
    multivalued: true
    inlined: true
    annotations: {ci:role: qualifier, ci:object: map}

enums:
  ParameterRole:
    annotations: {ci:extract: attribute, ci:applies_to: FamilyParameter}
    permissible_values:
      location: {}
      scale: {}
      shape: {}
      rate: {}
      mean: {}
      variance: {}
      standard_deviation: {}
      precision: {}
      degrees_of_freedom: {}
      success_probability: {}
      number_of_trials: {}
      lower_bound: {}
      upper_bound: {}
      other: {}
  ConditionPredicate:
    permissible_values:
      independent: {annotations: {ci:arity: "2+", ci:args: RandomVariable}}
      identically_distributed: {annotations: {ci:arity: "2+", ci:args: RandomVariable}}
      iid: {annotations: {ci:arity: "2+", ci:args: RandomVariable}}
```

Initial `rules.yaml` (expressions to be syntax-checked in S4):

| Rule id | Applies to | Severity | Check |
|---|---|---|---|
| `stat.param_keys_known` | `has_distribution` | warning | Every `param_values` key is a canonical name of a parameter the family has in this run, or a `ParameterRole` value |
| `stat.supposed_is_used` | any `supposed` claim | warning | INV-06: referenced by a condition or has a `scope` |
| `stat.one_distribution_per_statement` | `has_distribution` | error | At most one asserted or defined `has_distribution` per variable per statement |
| `stat.domain_is_set` | `parameter_domain`, `takes_values_in`, `support` | error | Object parses as a set (`parse = ok`) or is kept as `phrase` with status `unsupported` |
| `stat.variance_nonnegative` | `has_distribution` with a `variance` key | warning | z3: the conditions imply variance ≥ 0 when the formula parses |
| `stat.no_family_on_variable` | `has_parameter` | error | Subject is not a `RandomVariable` |

## 10. Guideline v0 (statistics)

This is the starting content of `domains/statistics/guideline.md`. Opus writes goldens from it
alone ([D7 §3](D7-evaluation-goldens-outer-loop.md#3-golden-authoring-protocol)); the operator
steers it ([D7 §8](D7-evaluation-goldens-outer-loop.md#8-the-operators-outer-loop)).

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

A `ClaimProposalBatch` (§7.3) per unit, with `statements`, `entities`, `claims` and
`unsupported` arrays, written through the `write_golden` tool ([D8](D8-agent-and-query-interfaces.md)).
Until that tool exists (spikes), write the batch as a JSON file.

### 10.10 Generated inventory

*(Generated from the schema version by §7.5: every class, predicate, qualifier and enum value
with its description.)*

### 10.11 Direction log

*(One entry per operator direction: date, the direction in the operator's words, the guideline
change it produced, the golden units re-authored.)*

## 11. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D2-1 | Exact `Schema.from_dict` keys for structures, attributes and per-type thresholds in gliner2 2.1.0 | Spike S4 |
| OPEN-D2-2 | Raw LaTeX or masked math placeholders in GLiNER2 input | Spike S2 |
| OPEN-D2-3 | rule-engine syntax for the `rules.yaml` checks, and whether custom functions such as `family_params` are better as resolver-backed symbols | Spike S4 |
| OPEN-D2-4 | Whether property predicates (`mean_value`, `pdf`, …) should be one `has_property` predicate with a `property` qualifier instead | Spike S0 annotations: count how many distinct properties appear |
| OPEN-D2-5 | Whether "standard normal" is better a family with `special_case_of` or a parameterization of the normal family | Spike S0 and outer-loop direction |
| OPEN-D2-6 | Whether LinkML annotation values that are lists (`ci:examples`, `ci:qualifiers`) round-trip through `SchemaView` unchanged | Spike S4 |
