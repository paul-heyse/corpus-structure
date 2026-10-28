# D2 · Schema conventions, compilers and the statistics pack

**Proposed (2026-10-28).** How a domain is declared, how one declaration drives extraction,
LLM output, validation and the annotation guideline, and the first version of the statistics
pack. The knowledge types the schema populates are defined in [D1](D1-knowledge-representation.md).

## 1. Principles

1. **One declaration per domain.** A domain pack's LinkML schema is the single source for entity
   types, predicates, qualifiers, enums, condition predicates, validation rules and the rule
   views over the claim pool. Nothing about a domain is hard-coded in Python except its two
   plug-ins, verifiers and domain queries ([§7.6](#76-domain-verifiers)); the core packages name
   no domain predicate or class (P0CL-07).
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
    rules.yaml           rule-engine rules (`rules:`), the guideline's warnings (`guideline:`), rule
                         views (`views:`), lookup tables (`tables:`) and derivations (`derive:`), §7.4
    migrations/          schema migration mappings for breaking changes, §8
  reference/             the annotator reference's worked examples E1, E2, …: each its packet text
                         (`packet.md`), authored batch (`batch.json`) and, once D1 §3.4 sentence
                         locators exist for the example pages, citation frame (§7.5)
  eval/                  evaluation-only data, read by no method: `split.yaml` (the forced-dev pages
                         and the split seed, D7 §3.1), `baselines.yaml` (the S0-R2 comparison figures
                         with their record ids, D7 §7) and the reference facts (D7 §6)
  guideline.md           the annotation guideline (§10 is v1 for statistics)
  policies.yaml          routing policies for this domain (D6 §7)
  methods.yaml           domain parameters of methods and named configurations (`configs:`):
                         math macro map, binder lexicon, alias head words and adverb rules, cue
                         lexicons, patterns, and the source profile by name (D4 §1, D6 §7.1, §12.1)
  slices.yaml            debug slices and run scopes (D6 §8), by locator (D1 §3.4)
  verifiers.py           optional domain verifiers implementing validate.Verifier (§7.6)
  queries.py             optional domain queries implementing serve's query protocol (§7.6, D8 §5.2)
  README.md              scope of the pack, source corpora, owner notes
domains/core/schema/core.yaml   core classes, predicates, value classes and enums shared by all packs
domains/core/schema/rules.yaml  domain-free rules every pack runs (such as `core.value_kind_matches_slot`,
                                a finalize warning), §7.4
sources/<profile>.yaml          source profiles (D4 M01): how one source's HTML becomes segments;
                                outside every pack, named by the packs that read the source (§12.1)
```

A **schema version** is the content hash over `<name>.yaml`, the pack's `rules.yaml` (its
`guideline:` section included), the imported `core.yaml`, the core `rules.yaml` and the worked
examples in `reference/E*` (each example's packet text as a string and its batch; its citation
frame joins the inputs once the example pages have D1 §3.4 sentence locators): SHA-256 of the
canonical JSON (D1 §10.1) of the parsed files, not of their bytes or of a SchemaView dump, which
carries file paths and varies with the LinkML release
([schema-rules note](../design_review/evidence/2026-10-28_library-schema-rules/README.md) L-07). The worked examples are inside it because
every prompt and golden pass reads them through the annotator reference (§7.5), so changing one is
a schema change for reuse (D6 §4). The guideline is versioned separately ([D7 §2](D7-evaluation-goldens-outer-loop.md#2-guidelines)),
because guideline wording changes far more often than the schema.
> Status: **Tested** (S4, 2026-10-28, record `s4.schema-hash`): over the pack files of §6 and §9,
> both `rules.yaml` files and `reference/E1…E3` (packet text and batch), the hash reproduced in 3
> of 3 subprocess runs with different hash seeds and a copy at another location. The citation-frame
> input is **Proposed**

## 3. The `ci:` annotation vocabulary

LinkML structure (classes, slots, ranges, enums, `is_a`, `mixins`, `abstract`, `multivalued`,
`required`, `description`) keeps its normal meaning, and **native LinkML carries every meaning it
can express**: `title`, `examples`, `unique_keys`, `subsets` with `in_subset`, `symmetric`,
`transitive`, `equals_string` and `ifabsent`. Our extraction and identity semantics that LinkML has
no element for are annotations with prefix `ci: https://corpus-structure.dev/ci/` (declared in
`core.yaml`), and **every annotation value is a scalar**: list-valued annotations load in
`SchemaView` but fail metamodel validation in `linkml-lint`, and object-valued ones do not load
(schema-rules note L-06). The three list annotations (`ci:qualifiers`, `ci:identity_qualifiers`,
`ci:target`) are space-separated strings, which the pack loader splits. Strings read back through
`SchemaView` are LinkML's `extended_str`; the loader casts them to `str` before they reach a compiler
or rule-engine (§7.4).
> Status: **Tested** (S4, 2026-10-28, record `s4.pack-lint`): the pack files of §6 and §9 lint with
> 0 errors (2 `standard_naming` warnings on D1's field names `t` and `v`, kept), and 129 of 129 `ci:`
> annotations read back through `SchemaView` equal to the file's value and type

**Derived, never written.** The compiler derives these facts from the schema, so no annotation
states them:
- **Class kind:** `entity` for a descendant of `Entity` that is neither abstract nor a mixin;
  `abstract` for an abstract class or a mixin; `value` otherwise: the descendants of `Value`, which
  are the D1 values, and the shape classes `EntityRef`, `SymbolBinding` and the `MapEntry`
  subclasses, which are not.
- **Object kind of a slot**, from its range: the value class's tag (its `t`, by `equals_string`:
  `formula`, `set`, `text`, `number`, `bool`, `enum`, `date`, `interval`, `phrase`); `entity` for
  `Entity`, an entity class or a mixin of entity classes; `enum` for an enum; `map` for a `MapEntry` subclass;
  `condition` for `Condition`.
- **Slot role** beyond `ci:role`: `identity` for a slot in a class's `unique_keys`; `field` for
  every other slot that is neither predicate nor qualifier.

### 3.1 On classes

| Annotation or native element | Values | Meaning |
|---|---|---|
| `ci:scope` | `global`, `local` | D1 §4.2. Required for entity classes |
| `unique_keys` (native) | one key `identity` with `unique_key_slots` | Identity attributes beyond the label (e.g. `[family, canonical_name]` for `FamilyParameter`); D1 §10 |
| `ci:extract` | `mention`, `none` | Whether extraction looks for mentions of this class |
| `title` (native) | string | Label shown to GLiNER2 (§7.2); set on the mention classes |
| `examples` (native) | `- value: …` items | Short positive examples, used in the GLiNER2 description, the annotator reference and the LLM prompt |
| `ci:reify` | `true` | Facts of this class are reified entities with role claims (D1 §5.4) |
| `ci:threshold` | number in (0, 1) | GLiNER2 score threshold for mentions of this class; default from the method configuration ([D4 M06](D4-method-catalog.md#m06-extractgliner_schema)). No v0 class sets one |
| `ci:parameter_class` | an identity slot name | Entities of this class are parameters of another entity, the one the named identity slot holds; a `family_param` binding names an entity of such a class (D1 §6.1, below). Statistics: `FamilyParameter` with `family` |

### 3.2 On slots (predicates, qualifiers and value-class attributes)

| Annotation or native element | Values | Meaning |
|---|---|---|
| `ci:role` | `predicate`, `qualifier` | `predicate`: claims use it. `qualifier`: usable as a qualifier on the predicates that list it. Written on predicates and qualifiers only; identity and field roles are derived (above) |
| `ci:qualifiers` | space-separated qualifier slot names | Schema qualifiers allowed on this predicate (D1 §5.3) |
| `ci:identity_qualifiers` | space-separated | Which of them enter the claim key (D1 §10.1) |
| `ci:extract` | `relation`, `llm`, `none` | How extraction proposes claims of this predicate: GLiNER2 relation, LLM only, or not extracted (derived only) |
| `symmetric` (native) | `true` | `identical_parameter`-style predicates; consolidation orders subject and object canonically |
| `transitive` (native) | `true` | The predicate is transitive (`special_case_of`); derivations may close over it (§7.4 `derive:`) |
| `ci:functional` | `true` | At most one object per subject and statement: candidates compete in one slot ([D5 §5.4](D5-consolidation-identity-confidence.md#54-slots-core-support-refinements-and-alternatives)), and across statements a second object is a conflict (D5 §5.5) |
| `ci:param_map` | a qualifier slot name | The predicate's map qualifier whose entries give values to parameters of its object; a `param_of` or `param_expr_of` binding that references a claim of this predicate reads entry `param` of that qualifier (D1 §6.1, below). Statistics: `has_distribution` with `param_values` |
| `in_subset` (native) | subset names | The predicate subsets that hold the predicate (below) |
| `examples` (native) | `- value: …` items | As on classes |
| `ifabsent` (native) | a default | The value a qualifier takes when absent: `modality` `asserted`, `polarity` `positive`. Defaults are filled in for rules (D5 §8.2) and omitted in storage |
| `ci:form` | `model`, `stored`, `consolidated` | On a value-class attribute present in one form only: `PhraseValue.sentence` (model-facing), its offsets and `coarse` (stored), `Formula.sympy` and `parse` (added by consolidation, in neither batch form). The batch models and the contract test (§6) compare each form with its own fields |
| `ci:required_in` | `stored` | The attribute is required in that form only (`PhraseValue.start`, `end`) |
| `ci:extract: record`, `ci:record`, `ci:anchor` | — | Reserved for GLiNER2 record structures (§7.2). **No v0 predicate uses them**: a record needs fields that one predicate cannot supply, so records are declared only when spike S2 or a measured gap shows a structure earns its place |

**Predicate subsets** are native LinkML `subsets`, declared by the schema that owns their meaning
and joined with `in_subset`. They replace any predicate-group annotation: the guideline rules
(§7.4 `applies_to: subset:<name>`, the claim view's `claim.groups`), the annotator reference's card
grouping (§7.5) and the binding rules (below) read them, and each subset's `description` states the
guideline rule it stands for, which the reference renders. Core declares `structural` (`defines`,
`proves`, `follows_from`, `refers_to`) and `unsupported` (`unschematized`); statistics declares
`formula_definition`, `family_structure` and `distribution` (§9). A predicate may be in several
(`transformation_of` and `construction_formula` are in `formula_definition` and
`family_structure`); the guideline's "formula or family-structure claims" (§10.7 rule 2) are
`formula_definition ∪ family_structure`. Acceptance thresholds, confidence priors and reports keyed
by predicate group ([D5 §6](D5-consolidation-identity-confidence.md#6-confidence), D6 §7) read the
same subsets, or a predicate by name; a predicate under several keys takes the most specific
(D5 §6.1).
> Status: **Tested** (S4, 2026-10-28, records `s4.pack-lint`, `s4.rules`): the subsets load and
> drive the 11 guideline rules (0 unexpected fires, 16 of 16 seeds caught) and the reference's
> card grouping; their use as threshold and prior keys is **Proposed**

**Binding semantics are pack data** (P0CL-07; operator, 2026-10-28). The core binding kinds
(D1 §6.1) are defined over these annotations, so neither `core` nor `consolidate` names a domain
predicate or class:
- `param_of` (`param_expr_of`) binds a symbol to entry `param` of the map qualifier that the
  referenced claim's predicate names in `ci:param_map`, when the symbol is that entry's value
  (occurs inside it);
- `family_param` binds a symbol to an entity of a class with `ci:parameter_class`;
- the predicates whose claims are about an entity's parameters as such form the pack subset
  **`family_structure`**; D5 §4's binding rules read the subset, not a list of names. Statistics
  v0: `has_parameter`, `parameter_domain`, `parameter_role`, `derived_parameter`,
  `identical_parameter`, `construction_formula`, `transformation_of`, `special_case_of`.
A second pack with parameterized entities declares the same three things and needs no code.
> Status: **Proposed** (2026-10-28); a toy second pack running the generic stages with no core
> edit is the check (phase 0 consolidation and queries). The rule view's reading of `ci:param_map`
> is **Tested** (S4, 2026-10-28, record `s4.rules`: `guideline.binding_priority`, 157 evaluations)

### 3.3 On enums and permissible values

| Annotation | Meaning |
|---|---|
| `ci:extract: attribute` with `ci:applies_to: <class>` | Compile to a GLiNER2 span attribute group on mentions of that class |
| `ci:extract: classification` with `ci:target: <segment kinds>` | Compile to a GLiNER2 classification task on segments of those kinds (space-separated, `unit paragraph`) |
| `ci:arity` (on a permissible value of `ConditionPredicate`) | `1`, `2`, `2+` |
| `ci:args` (same) | The class of the arguments |
| `ci:symmetric` (same) | `true` when argument order does not matter: D1 §7's canonical form sorts the arguments of a symmetric condition predicate. A permissible value has no native `symmetric` |
| `ci:z3` (same) | Name of the z3 encoding for this condition predicate, or absent if not encodable |
| `ci:claim_bearing` (on a permissible value of `StatementKind`) | `true` when units of this kind are expected to state claims; policies route proposals by it ([D6 §7.2](D6-orchestration-metrics-policies.md#72-unit-context)). Core defaults: true for every kind except `proof` and `solution` (narrative paragraphs such as T2 state claims) |

## 4. Predicates and qualifiers

A predicate is a LinkML slot with `ci:role: predicate`. Its `domain` is the subject class (or a
mixin shared by several classes, such as `Parameterized` or `Distributed`); its `range` is the
object class for an entity-valued predicate, or a value class or enum (the object kind is derived
from the range, §3).

Qualifiers are slots with `ci:role: qualifier`. A predicate lists the schema qualifiers it
accepts in `ci:qualifiers`. Core qualifiers (`modality`, `polarity`, `hedge`, `attribution`,
`conditions`, `scope`, `valid_time`) are always allowed and never listed. A **map** qualifier
ranges over a subclass of the core `MapEntry` (a `key` identifier and a `value`, the subclass
narrowing `value` by `slot_usage`), `multivalued: true`, `inlined: true`, and is written as an
object from key to value. `param_values` is the main example: keys are family-parameter canonical
names, values are formulas.

**Naming.** Predicates are lowercase verbs or verb phrases in snake case (`has_distribution`,
`identical_parameter`); classes are in upper camel case. Outside the schema files and the
model-facing batch, every class, predicate, qualifier and identity-slot name carries its schema's
prefix (`stat:has_distribution`, `stat:RandomVariable`, `stat:param_values`, `stat:family`; core
names use `core:`, as in `core:defines` and `core:modality`): in compiled rows, stored entity
types, stored predicates, stored claim qualifier keys and entity identity attributes, and in the
keys hashed from them (§7.1). The model-facing (authored) batch writes local names, which the
compiler maps to prefixed names when it derives the stored form (§7.3).

## 5. Condition predicates

Condition predicates are the permissible values of an enum named `ConditionPredicate` in the
domain schema, each with `ci:arity`, the class of its arguments (`ci:args`), `ci:symmetric` when
argument order does not matter, and optionally `ci:z3`. They appear in condition trees as `pred`
nodes (D1 §7), whose canonical form sorts the arguments of a symmetric predicate. Statistics v0
declares `independent`, `identically_distributed` and `iid`, all three of arity `2+` over
`RandomVariable` and symmetric. JSON Schema cannot check them, so the entity-type side table (§7.3)
checks each `pred` node's name, its arity against `ci:arity` and its arguments' classes against
`ci:args`.
> Status: **Tested** (S4, 2026-10-28, records `s4.pack-lint`, `s4.batch-validation`): the
> annotations round-trip, and the side table checks arity and argument classes on the 135 listed
> batches; the argument sort is **Proposed** (D1 §7)

## 6. The core schema

`domains/core/schema/core.yaml` is imported by every pack. It declares:

| Element | Kind | Content |
|---|---|---|
| `Entity` | abstract class | Base of all entity classes; slot `label` |
| `Statement` | entity class, local | D1 §4.3; slot `kind` (enum `StatementKind`), an ordinary attribute: a statement is identified by its anchor segments (D1 §10.1). Listed in a batch's `statements[]`, never in `entities[]` (§7.3). Label: `<kind> <unit id>`; `<kind> unit <n>` for a unit without an id (n its ordinal among the page's units); else `<kind> ¶<n>` with n the paragraph's ordinal in its section |
| `Value` | abstract class | Base of the D1 values; slot `t`, which each value class fixes by `equals_string` |
| `Formula`, `SetExpr`, `TextValue`, `NumberValue`, `BoolValue`, `EnumValue`, `DateValue`, `IntervalValue`, `PhraseValue` | value classes | Fields as D1 §6; form-specific fields marked `ci:form` (§3.2) |
| `EntityRef` | shape class | `{ref}`: the one entity-reference shape, a position type, not a value (D1 §6, §7.3) |
| `SymbolBinding` | shape class | D1 §6.1 binding kinds |
| `Condition` | abstract class | Names the condition-tree range; the node shapes are the core Pydantic `Condition` union |
| `MapEntry` | abstract class | `key` and `value`; the base of every map qualifier's range (§4) |
| `structural`, `unsupported` | subsets | §3.2 |
| `StatementKind` | enum, `ci:extract: classification`, `ci:target: unit paragraph` | Values in D1 §4.3, with `ci:claim_bearing` |
| `ClaimModality` | enum, `ci:extract: classification`, `ci:target: sentence` | D1 §5.2 |
| `Polarity`, `StatementRole`, `ScopeExtent`, `BindKind`, `ParseStatus`, `EvidenceRole` | enums | D1 §5.2, §6.1, D4 M11 (`ambiguous` included), guideline §10.3, §10.8 |
| `modality`, `polarity`, `hedge`, `attribution`, `conditions`, `scope`, `valid_time` | core qualifiers | `modality` defaults to `asserted` and `polarity` to `positive` by `ifabsent` |
| `defines`, `refers_to` | predicates, `structural` | `Statement` → `Entity` |
| `proves`, `follows_from` | predicates, `structural` | `Statement` → `Statement` |
| `unschematized` | predicate, `unsupported` | `Entity` → `PhraseValue`; D1 §8.1 status `unsupported` |

**Who owns the value shapes** (schema-rules note L-01; design authority, 2026-10-28). The D1 shapes
that every domain shares, the value union discriminated on `t`, condition nodes discriminated on
`op` (one named recursive `Condition` via `TypeAliasType`), the entity reference, symbol bindings
and the batch items, are hand-written Pydantic models in `core` (frozen, `extra="forbid"`, tuples
for lists). They are domain-independent, so no domain meaning moves into code. The value classes in
`core.yaml` are their **mirror**: an abstract `Value` base with `t` declared through
`equals_string`, and `conditions` and `param_constraints` ranged on the `Condition` class. LinkML
owns the domain vocabulary: classes, predicates, qualifiers, enums and identity. `gen-pydantic`
cannot be the source: on LinkML 1.12.1 it rejects the binding shape every batch uses, emits no
discriminated unions, defaults missing tags silently and does not freeze models, and it disagrees
with `gen-json-schema` on the same input.

The **mirror contract test** is the contract between the two (P0-F-2b, P0-S-1): per batch form, it
compares each value tag's fields, their required-ness, multivalued-ness and range between the core
Pydantic shapes and `core.yaml`'s value classes through `SchemaView` (an attribute counts in a form
by its `ci:form`, and is required there by `required` or `ci:required_in`), and also the bind
kinds, the binding fields, `EntityRef` and the evidence roles. The `scope` qualifier is the one
form-dependent shape LinkML cannot express (model-facing a `ScopeExtent` value, stored
`{extent, segment}`); its range stays `ScopeExtent` and the stored shape is the core Pydantic one.
> Status: **Tested** (S4, 2026-10-28, record `s4.batch-validation`): the contract test passes on the
> file below and fails when `NumberValue.basis` is dropped on the Pydantic side or `TextValue.lang`
> added on the LinkML side

The design copy of `domains/core/schema/core.yaml` (S4's pack file,
`results/s4/schema/domains/core/schema/core.yaml` in the
[design-spikes evidence](../design_review/evidence/2026-10-28_design-spikes/S4-report.md)):

```yaml
id: https://corpus-structure.dev/core
name: core
title: Core schema
description: >-
  Core classes, predicates, qualifiers, value classes and enums shared by every domain pack (D2 §6).
  The value classes are the mirror of the core Pydantic shapes, which own them; a contract test fails
  when the two disagree. Native LinkML is used wherever it carries the meaning; the remaining ci:
  annotations are scalar (D2 §3).
version: 0.2.0
license: https://creativecommons.org/publicdomain/zero/1.0/
prefixes:
  linkml: https://w3id.org/linkml/
  ci: https://corpus-structure.dev/ci/
  core: https://corpus-structure.dev/core/
default_prefix: core
default_range: string
imports:
  - linkml:types

subsets:
  structural:
    description: >-
      Structural claims, about statements. They take no statement_role, are asserted, and carry no
      conditions (guideline §10.3, §10.6, §10.7 rule 4).
  unsupported:
    description: >-
      Something the source states that the schema cannot express; the claim has status unsupported
      (D1 §8.1).

classes:
  Entity:
    abstract: true
    description: Base of every entity class; instances are D1 entities.
    slots: [label]

  Statement:
    is_a: Entity
    description: >-
      An authored unit of meaning: a definition, theorem, proof, example, exercise, remark,
      convention or assumption. Claims belong to statements as premises, conclusions, definientia
      or example values. Listed in a batch's statements[], never in entities[].
    slots: [kind]
    annotations:
      ci:scope: local
      ci:extract: none
      ci:reify: true

  Value:
    abstract: true
    description: >-
      Base of the D1 value classes. Every value carries the tag t, which names its class; the core
      Pydantic value union is discriminated on it.
    slots: [t]

  Formula:
    is_a: Value
    description: A formula as written, with its symbol bindings (D1 §6.1).
    slot_usage:
      t: {equals_string: formula}
    attributes:
      latex:
        required: true
        description: The LaTeX exactly as written, macros included.
      sympy:
        description: The normalized SymPy form; added by M11 during consolidation.
        annotations: {ci:form: consolidated}
      parse:
        range: ParseStatus
        description: The parse outcome; added by M11 during consolidation.
        annotations: {ci:form: consolidated}
      symbols:
        range: SymbolBinding
        multivalued: true
        inlined: true
        description: The binding map, keyed by symbol in token form without backslash.

  SetExpr:
    is_a: Formula
    description: A set written in LaTeX, such as \R, (0, \infty) or \R \setminus \{0\}.
    slot_usage:
      t: {equals_string: set}

  TextValue:
    is_a: Value
    description: Free text that is the value itself.
    slot_usage:
      t: {equals_string: text}
    attributes:
      v: {required: true, description: The text.}

  NumberValue:
    is_a: Value
    description: A number with its unit and basis as stated (D1 §6.2).
    slot_usage:
      t: {equals_string: number}
    attributes:
      v: {required: true, description: The canonical decimal string.}
      unit: {description: "The unit as stated, or absent."}
      basis: {description: "A reference basis the source states, such as gauge or absolute, or absent."}

  BoolValue:
    is_a: Value
    description: A truth value.
    slot_usage:
      t: {equals_string: bool}
    attributes:
      v: {range: boolean, required: true, description: The truth value.}

  EnumValue:
    is_a: Value
    description: A permissible value of a schema enum.
    slot_usage:
      t: {equals_string: enum}
    attributes:
      enum: {required: true, description: The enum's name.}
      v: {required: true, description: The permissible value.}

  DateValue:
    is_a: Value
    description: A date or date-time kept verbatim as ISO 8601.
    slot_usage:
      t: {equals_string: date}
    attributes:
      v: {required: true, description: The ISO 8601 string as written.}

  IntervalValue:
    is_a: Value
    description: An interval of values; an absent bound is unbounded.
    slot_usage:
      t: {equals_string: interval}
    attributes:
      start: {range: Value, inlined: true, description: "The lower bound, a value."}
      end: {range: Value, inlined: true, description: "The upper bound, a value."}
      start_incl: {range: boolean, description: Whether the lower bound is included.}
      end_incl: {range: boolean, description: Whether the upper bound is included.}

  PhraseValue:
    is_a: Value
    description: >-
      Text kept but not interpreted. The model-facing form names the sentence it lies in; the stored
      form adds the offsets the quote cascade located.
    slot_usage:
      t: {equals_string: phrase}
    attributes:
      text: {required: true, description: The text as written.}
      sentence:
        description: The unit sentence (sN) or standing-context sentence (cN) holding the text.
        annotations: {ci:form: model}
      start:
        range: integer
        description: Start offset in the rendition's canonical text.
        annotations: {ci:form: stored, ci:required_in: stored}
      end:
        range: integer
        description: End offset in the rendition's canonical text.
        annotations: {ci:form: stored, ci:required_in: stored}
      coarse:
        range: boolean
        description: The text was not located exactly; the span is the whole cited sentence.
        annotations: {ci:form: stored}

  EntityRef:
    description: >-
      A reference to an entity: a batch local ref, or an entity key once stored. It is a position
      type, not a value; a slot whose range is an entity class takes it.
    attributes:
      ref: {required: true, description: The local ref or entity key.}

  SymbolBinding:
    description: How one symbol of a formula is bound (D1 §6.1).
    attributes:
      symbol:
        identifier: true
        description: The symbol in token form, without backslash.
      bind: {range: BindKind, required: true, description: The binding kind.}
      entity: {description: "variable, family_param: the entity's local ref (key once stored)."}
      claim: {description: "param_of, param_expr_of: the claim's local ref (key once stored)."}
      param: {description: "param_of, param_expr_of: the entry of the claim's ci:param_map qualifier."}

  Condition:
    abstract: true
    description: >-
      A condition tree (D1 §7). Its node shapes are owned by the core Pydantic Condition union,
      discriminated on op; this class is the range that names it.

  MapEntry:
    abstract: true
    description: >-
      One entry of a map qualifier (object kind map, D2 §3): a string key and a value. A map
      qualifier ranges over a subclass, multivalued and inlined, and is written as an object from
      key to value.
    attributes:
      key: {identifier: true, description: The entry's key.}
      value: {description: The entry's value.}

slots:
  label:
    description: Canonical display label (D1 §4.1). Identity follows the key rules of D1 §10.1.
  kind:
    range: StatementKind
    description: The statement's kind.
  t:
    description: The value's tag, naming its class.

  # core qualifiers: allowed on every predicate, never listed in ci:qualifiers (D2 §4)
  modality:
    range: ClaimModality
    ifabsent: string(asserted)
    description: How the source holds the claim (D1 §5.2); asserted when absent.
    annotations: {ci:role: qualifier}
  polarity:
    range: Polarity
    ifabsent: string(positive)
    description: Whether the claim is stated or denied; positive when absent.
    annotations: {ci:role: qualifier}
  hedge:
    range: PhraseValue
    description: A hedging phrase the source attaches to the claim ("usually", "in some settings").
    annotations: {ci:role: qualifier}
  attribution:
    range: Entity
    description: Who the source says states the claim, when it cites someone.
    annotations: {ci:role: qualifier}
  conditions:
    range: Condition
    description: The condition tree under which the claim holds (D1 §7).
    annotations: {ci:role: qualifier}
  scope:
    range: ScopeExtent
    description: >-
      How far a supposition reaches beyond its statement; model-facing a ScopeExtent value, stored
      {extent, segment}.
    annotations: {ci:role: qualifier}
  valid_time:
    range: IntervalValue
    description: The time interval over which the claim holds, when the source states one.
    annotations: {ci:role: qualifier}

  # core predicates
  defines:
    domain: Statement
    range: Entity
    in_subset: [structural]
    description: The statement defines the entity. "is called the location-scale family".
    annotations: {ci:role: predicate, ci:extract: llm}
  proves:
    domain: Statement
    range: Statement
    in_subset: [structural]
    description: A proof or solution statement proves (or solves) another statement.
    annotations: {ci:role: predicate, ci:extract: llm}
  follows_from:
    domain: Statement
    range: Statement
    in_subset: [structural]
    description: The statement is stated to follow from another ("a corollary of the last result").
    annotations: {ci:role: predicate, ci:extract: llm}
  refers_to:
    domain: Statement
    range: Entity
    in_subset: [structural]
    description: The statement explicitly refers to an entity defined elsewhere ("recall the gamma function").
    annotations: {ci:role: predicate, ci:extract: llm}
  unschematized:
    domain: Entity
    range: PhraseValue
    in_subset: [unsupported]
    description: Something the source states that the schema cannot express (D1 §8.1).
    annotations: {ci:role: predicate, ci:extract: llm}

enums:
  StatementKind:
    description: What the source calls a statement (D1 §4.3).
    annotations: {ci:extract: classification, ci:target: unit paragraph}
    permissible_values:
      definition: {description: Stipulates what a term means., annotations: {ci:claim_bearing: true}}
      theorem: {description: A stated result., annotations: {ci:claim_bearing: true}}
      proposition: {description: A stated result., annotations: {ci:claim_bearing: true}}
      lemma: {description: A stated auxiliary result., annotations: {ci:claim_bearing: true}}
      corollary: {description: A result stated to follow from another., annotations: {ci:claim_bearing: true}}
      proof: {description: A proof of another statement., annotations: {ci:claim_bearing: false}}
      example: {description: A worked example with setup values., annotations: {ci:claim_bearing: true}}
      exercise: {description: An exercise with setup values and an asked quantity., annotations: {ci:claim_bearing: true}}
      solution: {description: A solution of an exercise., annotations: {ci:claim_bearing: false}}
      remark: {description: A remark; explicit claims only., annotations: {ci:claim_bearing: true}}
      convention: {description: A convention the source adopts., annotations: {ci:claim_bearing: true}}
      notation: {description: A notation the source introduces., annotations: {ci:claim_bearing: true}}
      assumption: {description: A statement whose only content is a supposition (a context premise)., annotations: {ci:claim_bearing: true}}
      narrative: {description: Narrative text between units that states claims., annotations: {ci:claim_bearing: true}}
  ClaimModality:
    description: How the source holds a claim (D1 §5.2; guideline §10.6).
    annotations: {ci:extract: classification, ci:target: sentence}
    permissible_values:
      asserted: {description: Concluded or stated as true; structural claims.}
      supposed: {description: "A supposition: suppose, assume, if, or let about something taken as given."}
      defined: {description: "What a definition stipulates, including a formula introducing a variable."}
      conventional: {description: A convention.}
      exemplified: {description: Setup values in examples and exercises.}
      posed: {description: Reserved until an asks_for predicate exists (OPEN-D2-15).}
      cited: {description: Attributed to another source.}
  Polarity:
    description: Whether a claim is stated or denied.
    permissible_values:
      positive: {description: Stated.}
      negative: {description: Denied.}
  StatementRole:
    description: The part a claim plays in its statement (guideline §10.3).
    permissible_values:
      premise: {description: A supposition the statement makes.}
      conclusion: {description: "What a theorem, corollary or remark concludes."}
      definiens: {description: "What a definition stipulates, or a formula introducing a variable."}
      restriction: {description: Reserved; restrictions are condition nodes in guideline v1.}
      example_value: {description: A setup value of an example or exercise.}
  ScopeExtent:
    description: How far a supposition or a local entity reaches.
    permissible_values:
      statement: {description: The statement that states it.}
      section: {description: The enclosing section from the stating sentence on.}
      document: {description: The whole document.}
  BindKind:
    description: The kinds of symbol binding (D1 §6.1).
    permissible_values:
      variable: {description: The symbol denotes a local entity of the batch.}
      param_of: {description: The symbol is the value of an entry of another claim's parameter map.}
      param_expr_of: {description: The symbol occurs inside the value of such an entry.}
      family_param: {description: The symbol denotes a parameter entity of a family.}
      free: {description: "A symbol the statement introduces, restricted by its conditions."}
      constant: {description: A numeric or named constant.}
      unresolved: {description: Not bound; a counted resolution gap.}
  ParseStatus:
    description: The math grammar's parse outcome for a value (D4 M11).
    permissible_values:
      ok: {description: One reading.}
      partial: {description: Parsed in part.}
      ambiguous: {description: "More than one reading, none chosen by declared context."}
      failed: {description: Not parsed.}
  EvidenceRole:
    description: The part an evidence span plays for its claim (guideline §10.8).
    permissible_values:
      primary: {description: The minimal span that states the claim.}
      supporting: {description: An introducer that determines the modality.}
      condition: {description: The span of a condition.}
      definition: {description: The span of a definition the claim relies on.}
```

The core `domains/core/schema/rules.yaml` has the same form as a pack's (§7.4), with rules only:

```yaml
# Core rules: domain-free rules every pack runs beside its own (D2 §2, §7.4). Same form as a pack's
# rules.yaml; the core file has no views:, guideline: or tables: of its own.
rules:
  - id: core.value_kind_matches_slot
    applies_to: any
    severity: warning
    at: [finalize]
    description: >-
      A formula or set object parses under its slot's declared kind; the grammar's reading of a
      different kind (a set in a Formula slot, a relation where a formula belongs) is a warning,
      and the value is kept as written. Reads the grammar's parse, so it runs at finalize only.
    when: "(claim.value&.slot_kind ?? '') in ['formula', 'set']"
    check: "claim.value&.math_kind == null or claim.value&.math_kind == claim.value&.slot_kind"
```
> Status: **Tested** (S4, 2026-10-28, records `s4.pack-lint`, `s4.rules`): both files load, lint
> and compile; `core.value_kind_matches_slot` evaluated 24 times on the unseeded pool with 0
> unexpected fires and caught its seed

## 7. Compilers

Each compiler is a pure function of a loaded schema version (`linkml_runtime.SchemaView`) and
returns an artifact plus its hash. Output ordering is deterministic (sorted by name) so equal
schemas produce byte-equal artifacts.

**Artifact identity** (P0CL-15; operator, 2026-10-28). An artifact is identified by its schema
version, its compiler and that compiler's version, and its kind (the batch schema in each form,
the annotator reference, the compiled rules and views, the schema tables' content): one
`meta.compiled_artifact` row each (D3 §3), never a field of the schema version that a compiler fix
would rewrite under runs that used the old output. A compiler fix therefore adds rows beside the
old ones. A method configuration declares the artifacts it reads by compiler and kind; the method
registry resolves them against the run's schema version to artifact hashes, which enter the
configuration hash, so work done with the old artifact keeps its provenance and is not reused for
the new one (D6 §4). Artifacts are deterministic, so
any one can be rebuilt from its schema version and compiler and checked against its stored hash;
compiled rules are rebuilt this way, never pickled (§7.4).
> Status: **Proposed** (2026-10-28)

### 7.1 To schema tables

Writes `meta.schema_class`, `meta.schema_slot`, `meta.schema_enum` and `meta.schema_rule` rows
([D3 §3](D3-database.md#3-meta-schema-guidelines-and-domain-declarations)) with induced slots
(inheritance and mixins resolved through `SchemaView.class_induced_slots`), plus the
`schema_version` row and one `compiled_artifact` row per artifact. These rows let SQL join claims to
their schema definitions and let metrics group by class and predicate.

- **Applicability.** Predicates are free slots with a `domain`, which `class_induced_slots` omits,
  so a predicate applies to a class when `domain ∈ class_ancestors(cls)` (mixins included), read
  through `induced_slot(p, cls)` (schema-rules note L-08).
- **Prefixed names everywhere outside the authored batch** (operator, 2026-10-28). The stored form
  and everything derived from it name every schema element by its prefixed name, from
  `get_uri(…, expand=False)`: classes (`stat:RandomVariable`), predicates (`stat:has_distribution`),
  qualifiers, core ones included (`stat:param_values`, `core:modality`), identity slots
  (`stat:family`, `stat:canonical_name`) and enums (`core:BindKind`). That covers every compiled
  row, including the columns that name a domain class or range and `meta.schema_class.identity_keys`;
  stored entity types, stored predicates and stored claim qualifier keys; the keys of
  `kb.entity.attrs` (D3 §5); enum names inside stored values (`{"t": "enum", "enum":
  "stat:ParameterRole", "v": "scale"}`); and the rule view (§7.4), except its qualifier attributes,
  which stay local because a rule-engine attribute cannot contain `:`. Keys hash the stored-form names, so a claim
  key's predicate and identity-qualifier parts and an entity key's identity attributes are prefixed
  (D1 §10.1). The model-facing (authored) batch writes local names (§7.3); the compiler checks that
  each local name is unique within the schema version and maps it to its prefixed name when the
  stored form is derived. S4's compiled rows spell `identity_keys` with bare slot names
  (`[family, canonical_name]`), a compiler detail P0-S-1 corrects. The prefixes `ci`, `core` and `stat` are kept although
  `linkml-lint`'s `canonical_prefixes` rule reports them as registered elsewhere: every IRI is
  explicit under `https://corpus-structure.dev/`, and an RDF or JSON-LD export carries its own
  prefix map ([D8 §6](D8-agent-and-query-interfaces.md#6-exports)), so the rule is disabled and no
  stored name moves for a tooling convention.
- **Class-local attributes.** A slot row's key is `(schema_version_id, name)` (D3 §3), which cannot
  hold two attributes of the same name in different classes (`v` of `TextValue` and
  `NumberValue`). A class-local attribute's row is therefore named `<prefix>:<Class>.<attribute>`
  (`core:NumberValue.v`, `core:PhraseValue.start`); free slots keep `<prefix>:<slot>`.
> Status: **Tested** (S4, 2026-10-28, record `s4.schema-hash`): 25 class, 97 slot, 10 enum and 16
> rule rows with the `schema_version` and `compiled_artifact` rows, in D3's columns; the prefixed
> domain-class, range and `identity_keys` spellings and the local-to-prefixed mapping of the stored
> form are **Proposed** (S4's rows held those columns unprefixed; P0-S-1)

### 7.2 To GLiNER2 schemas

Compiled from phase 1, when M05–M07 run; phase 0 compiles nothing for GLiNER2, so the product
environment carries no gliner2 or torch until then.

Two artifacts, because GLiNER2's ordinary and joint decoders have different semantics
([library overview](../libraries/gliner2.md) §4.3):

**(a) The extraction schema**, built with `Schema.from_dict`. gliner2 2.1.0 accepts, for v0, the
keys `entities` (label → description), `entity_attributes` (`labels`, `applies_to`,
`qualify_labels`), `classifications` (`task`, `labels` as label → description) and `relations`
(name → `{description}`), and rejects an unknown key:

| GLiNER2 element | Compiled from |
|---|---|
| Entity types with descriptions | Entity classes (§3) with `ci:extract: mention`; label = `title`; description = LinkML `description` plus `examples` |
| Span attribute groups | Enums with `ci:extract: attribute`; `applies_to` = the `title` of `ci:applies_to`; `qualify_labels: true` |
| Classification tasks | Enums with `ci:extract: classification`, labels described by their permissible values' descriptions (run on segments of the `ci:target` kinds by M05) |
| Structures (record mode) | None in v0 (§3.2) |
| Relations (independent) | Predicates with `ci:extract: relation`, label = predicate name in words, description from the slot |

**(b) The joint schema** for `JointIE`: entity types as in (a); one relation per
`ci:extract: relation` predicate with head = the labels of the domain's entity classes (a mixin
domain gives every entity class that has it) and tail = the range's; `max_per_head: 1` where
`ci:functional: true`; no self-loops always; `symmetric` from native `symmetric`.

**Compile check.** `Schema.from_dict(d).to_dict() == d` and `JointSchema.from_dict(d).to_dict() == d`
on the compiled dicts. `to_dict` compacts a description-only entity configuration to a plain string,
so the compiler emits that canonical form (`"random variable": "A random variable denoted by …"`),
of which `to_dict` is a fixpoint.
> Status: **Tested** (S4, 2026-10-28, record `s4.gliner-roundtrip`; closes OPEN-D2-1 for v0): both
> dicts round-trip and ran on T3's first sentence on CPU with `fastino/gliner2.5-base-v1`; the
> extraction dict is 676 Qwen3.5-9B tokens (record `s4.sizes`). Structures and per-type thresholds
> are not exercised, since v0 declares none

**Math in text.** GLiNER2 sees the segment text. Whether LaTeX is passed raw, or each math span
is replaced by a placeholder token (`⟨m3⟩`) whose original is restored after extraction, is
decided by spike S2 (`OPEN-D2-2`). The compiler emits the schema only; the masking choice lives
in the method configuration of M06/M07.

### 7.3 To JSON Schema for LLM claim proposals

The LLM methods (M10, M16) and Opus produce claims in D1 form with local references. The
compiler emits one JSON Schema (draft 2020-12) used both as the vLLM structured-output schema
and for validating Opus submissions:

```text
ClaimProposalBatch                   model-facing form; "stored:" notes where the stored form differs
  unit_ref            string         the packet's unit key
  entities[]          { local_ref, type ∈ enum(entity classes except Statement), label, scope ∈ {global, local},
                        extent?: statement | section        local entities only (D1 §4.2)
                        symbol?, aliases?, identity?{ slot: value } }
                                     stored: adds scope_segment (segment key) for local entities
  statements[]        { local_ref, kind ∈ enum(StatementKind), anchor: "unit" | [sentence ids] | "outside" }
                                     stored: anchor = [segment keys] | "outside"
  claims[]            oneOf per predicate:
                        { local_ref, predicate: const <p>, subject: local_ref,
                          object: <entity ref {ref}> | <value of p>,
                          qualifiers: { core qualifiers, schema qualifiers of p },
                          statement?: local_ref, statement_role?,
                          evidence[]: { sentence, quote, role } }   sentence: sN of the unit or cN of its standing context
                                     stored: evidence[] = { start, end, role, coarse? }
  alternatives[]      { refs: [claim local_refs] (2 or more), reason }
  unsupported[]       { local_ref, sentence, quote, reason }
                                     stored: start, end instead of sentence, quote
  (optional fields are absent, never null)
```

- **Names.** The model-facing (authored) form writes local names (`has_distribution`,
  `RandomVariable`, `param_values`, identity slots `family` and `canonical_name`, core qualifiers
  `modality`, enum names in values `ParameterRole`), as authors, the generated reference and the decoding grammar use them. Deriving the
  stored form maps each to its prefixed name (`stat:has_distribution`, `stat:family`,
  `core:modality`), and the stored form, its keys and everything downstream carry only prefixed
  names (§4, §7.1).
- **Entity references** (S4 variant V1). Every position that may take an entity writes one shape,
  `{"ref": <local ref>}`: claim objects of entity-valued predicates, entity-ranged qualifiers
  (`attribution`, `base`, `base_variable`) and `pred` arguments in condition trees. It is a
  position type (`EntityRef`, §6), not a D1 value: storage already separates entity objects from
  values (D3 `object_entity_id` and `object_value`), and the one union with values (`pred`
  arguments) decodes as `anyOf` without loss. Fields that only ever hold a reference (`subject`,
  `statement`, identity slots, binding targets) stay local-ref strings.
- **Statements only in `statements[]`** (S4 variant V2). A statement outside the unit that a claim
  names ("the last result", a cited "[14]") is a `statements[]` item with `anchor: "outside"`;
  consolidation resolves it through the link targets of the citing claim's evidence or leaves it
  unresolved. An `entities[]` row of type `Statement` would give statements a second identity path,
  since D1 §10.1 keys statements by anchor.
- **Absent, never null.** An optional field is omitted when it has no value; the batch models
  reject `null`, and defaults (`modality`, `polarity`, §3.2 `ifabsent`) are filled in for rules and
  omitted in storage.
- **Local refs** are unique within a batch and are the only way items refer to each other:
  `subject`, `object.ref`, `statement`, condition nodes `{"op": "claim", "ref": …}`, and symbol
  bindings (`variable` and `family_param` name an entity local ref in `entity`; `param_of` and
  `param_expr_of` name a claim local ref in `claim`, plus `param`). Consolidation replaces local
  refs with keys ([D5 §5.2](D5-consolidation-identity-confidence.md#52-normalization-and-keys)).
- **Values.** Formula and set values carry `t`, `latex` and `symbols` (the binding map, D1 §6.1);
  `sympy` and `parse` are added by M11 during consolidation (`ci:form: consolidated`) and appear in
  neither batch form.
- **Global entities** are identified across units by `label` and `identity`; packets list the
  known entities linked to the page (the reference run's global entities with a claim whose
  evidence is on the page, by key, at most 30; D4 §4.1) so proposals reuse their labels.
- **Extent.** `statement` scopes a local entity to the statement that binds it; `section` to the
  enclosing section from the binding sentence on (D1 §4.2). The stored form resolves it to a
  `scope_segment`.
- **Standing-context citations.** Evidence and statement anchors may name a standing-context
  sentence (`cN`, D4 §4.1) as well as a unit sentence (`sN`). A supposition stated only in the
  standing context is recorded once, as a statement of kind `assumption` anchored at its `cN`
  sentences, so the unit's conditions can reference its claims (guideline §10.2); stored offsets
  then lie outside the unit's range, inside the context sentence.
  > Status: **Tested** (S0-R2, 2026-10-28: U12, H3; record s0r2.reference-v1)
- **Exact shapes** for every value, binding and condition node, entity-valued identity slots
  (a local-ref string), `aliases` (strings) and `scope` (a string) are stated in the generated
  annotator reference (§7.5), because models given only this outline guessed them (S0 gap GG-17).
> Status: **Tested** (S4, 2026-10-28, record `s4.batch-validation`): of the 135 listed batches
> (the v1 reference, every S0 pass, the v1 passes and the examples), 90 validate as written and the
> other 45 validate once moved to V1 and V2 (126 recorded rewrites: `{"t": "entity", "ref": r}` in
> `pred` arguments and `base_variable`, a dict-valued identity slot, a `Statement` row in
> `entities[]`); no batch contains a null

**The entity-type side table.** JSON Schema cannot follow local references, so per-predicate
branches restrict the value type and the allowed schema qualifiers, and a side-table check reading
only schema facts runs after the batch models. It checks subject, object and entity-qualifier classes
against the predicate's domain and ranges (mixins and `is_a` included); that every ref resolves to
an item of the right kind; entity scope against the class's `ci:scope`, an extent on every local
entity and none on a global one (INV-05); identity slots against `unique_keys` and their targets'
classes; binding targets (`variable` a local entity, `family_param` an entity of a
`ci:parameter_class` class, `param_of`/`param_expr_of` an existing entry of the claim's
`ci:param_map` qualifier); condition `claim` nodes naming claims of the batch (INV-08) and `pred`
nodes' names, arity and argument classes (§5); primary evidence on every claim (INV-01); and
INV-06. It is the only catcher of reference errors.
> Status: **Tested** (S4, 2026-10-28, record `s4.batch-validation`): clean on 135 of 135 valid
> batches; of 13 seeded errors all are caught, and the five reference errors (wrong subject class,
> unresolved object, a variable binding to a global entity, a missing map entry, a global entity
> with an extent) only by the side table

Enum values are inlined. Descriptions are carried into the model-facing schema so the model sees
them. Prompts carry the annotator reference (§7.5); there is no separate prompt inventory. Filtering
the reference by statement kind does not bring it near a small local-tier budget (D4 §4.2 carries
it whole): the smallest per-kind variant is 6,347 tokens (S4 variant V4, not adopted; record
`s4.sizes`), so the local tier's budget is decided with S3 (P0-A-1).

**Model-facing and stored forms.** The compiler emits the batch schema twice. The *model-facing*
form, given to LLMs and Opus, cites evidence by sentence id and quote and anchors statements by
sentence ids, because models do not count characters reliably. The *stored* form has rendition
offsets and segment keys; consolidation and alignment read it.

**The authored batch is the authority** (P0CL-03; operator, 2026-10-28). What an author wrote (a
golden pass, a fixture, an agent proposal) is kept in the model-facing form with its citation
frame, which maps each cited `sN` and `cN` to the sentence's locator and text
([D1 §10.3](D1-knowledge-representation.md#103-stability-limits)). Sentence ids are
packet-relative; the frame makes them absolute, so the batch means the same on every rendition of
its page. The stored form is derived from batch and frame, per rendition, by the production quote
cascade ([D4 §4.3](D4-method-catalog.md#43-output-form-and-post-processing)), and records the
rendition it was derived on. It is never authored, so an ingest change re-derives it rather than
orphaning it; golden items are this derivation for goldens (D7 §3.1). A quote the cascade cannot
locate becomes a span over the whole cited sentence marked `coarse` (D5 §5.6), never an invented
offset.
> Status: **Proposed** (2026-10-28)

**How the schema is built** (schema-rules note L-02, L-03). The compiler builds one claim model per
predicate with `pydantic.create_model` from `SchemaView` (subject and object types, value type,
allowed qualifiers), unions them discriminated on `predicate`, and wraps them in the batch envelope
over the `core` shapes, once per batch form. One `TypeAdapter` per form both validates submissions
(exact error paths, such as `claims.0.has_distribution.qualifiers.modality literal_error`) and
exports the draft 2020-12 JSON Schema in validation mode, through a custom `GenerateJsonSchema`
(no titles, `$schema` set, deterministic output). `gen-json-schema` is not used: it emits draft
2019-09, has no `t`, and drops predicate and qualifier slots. jsonschema's `Draft202012Validator`
agrees with the models on every verdict but is slower and less precise (its `best_match` stops at
the whole claim under `oneOf`), so the models validate and jsonschema only checks the exported
schemas.
> Status: **Tested** (S4, 2026-10-28, record `s4.batch-validation`): 25 predicate branches; the
> model-facing schema is 42,559 bytes compact; the model-facing, stored and decoding schemas pass
> `check_schema` and are byte-identical across two processes with different hash seeds; the two
> validators agree on 180 of 180 verdicts; median per valid batch 0.073 ms (Pydantic) and 12 ms
> (jsonschema), indicative, on CPU

The **decoding form** given to structured output is a pure transform of the model-facing schema,
following rules the backends need:
- `oneOf`/`anyOf` only where branches are disjoint by a `const` (the predicate), with **every
  branch inlined**: with `$ref` branches xgrammar 0.2.7 cannot prove them disjoint and falls back
  to `anyOf` with a warning, while the same branches inline are kept;
- never `if`/`then`/`not`, which xgrammar ignores; no `allOf` with more than one branch, which
  xgrammar mishandles (newer vLLM rejects such schemas itself); nesting at most 64 levels;
- `discriminator`, `description`, `default` and `title` stripped: constrained decoding does not
  show descriptions to the model, and the annotator reference in the prompt is what it reads;
- one canonical shape per position (one entity-reference shape, one formula shape);
- the grammar fixes the schema's property order, so a batch in another key order is accepted only
  with xgrammar's `any_order=True` (false by default); whether the local tier sets it or relies on
  schema order is decided with vLLM in S3.
Its first consumer is the local tier in phase 1 (M10, M16); phase 0 builds it with structural tests
of the rules above.
> Status: **Tested** in xgrammar 0.2.7, vLLM 0.31's bundled version, offline on CPU (S4,
> 2026-10-28, record `s4.decoding-form`): 8 of 8 `oneOf`s kept with 0 warnings, compiled in 0.03 s,
> 15 of 15 canonical batches accepted (compact and indented, and T3 token by token through the
> matcher), 7 of 7 seeds rejected; 12,716 Qwen3.5-9B tokens (record `s4.sizes`). vLLM itself
> passing the schema through, and generation, are S3's

### 7.4 To rule-engine rules

`rules.yaml` holds named rules and the rule views they read. The core `rules.yaml`
(`domains/core/schema/`, §6) holds the domain-free rules in the same form, such as
`core.value_kind_matches_slot`, a finalize warning, and every pack's rules run beside them. The
sections, with entries from the statistics file (§9):

```yaml
views:                         # pool facts as claim-view attributes, compiled for the generic view builder
  family_params:               # claim.family_params: a list of strings
    description: Canonical names of the parameters the claim's object family has.
    applies_to: stat:has_distribution
    source: stat:has_parameter                 # the source predicate
    match: {source: subject, claim: object}    # source claims whose subject is this claim's object (the family)
    project: object.identity.stat:canonical_name   # what each matching source claim contributes
rules:
  - id: stat.domain_is_set
    applies_to: [stat:parameter_domain, stat:takes_values_in, stat:support]   # predicates, subset:<name>, any, or a list mixing them
    severity: warning          # warning | error
    at: [finalize]             # call sites (D5 §8.2): it reads the grammar's parse status
    description: The object parses as a set; otherwise a warning, and the object is kept as written.
    check: "(claim.value&.parse ?? '') == 'ok'"        # when: omitted, true
guideline:                     # the guideline rules code can check: always warnings, always at [batch, finalize]
  - id: guideline.references_a_premise
    applies_to: any
    description: Every other claim references at least one premise of its statement or of a context-premise assumption (guideline §10.7 rule 3).
    when: >-
      not ('structural' in claim.groups or 'formula_definition' in claim.groups
           or 'family_structure' in claim.groups)
      and not (claim.statement_role in ['premise', 'example_value'])
    check: "claim.statement_premises.is_empty or $any([p in claim.claim_refs for p in claim.statement_premises])"
tables:                        # lookup tables compiled to typed $ builtins; the annotator reference renders them (§7.5)
  roles_by_kind: {definition: [definiens, premise], remark: [premise, conclusion, definiens, none], convention: [none], …}
  modality_by_role: {premise: supposed, definiens: defined, conclusion: asserted, example_value: exemplified}
derive: []                     # derivations (M23), below
```

The compiler parses each `when` and `check` with `rule_engine.Rule` under a typed `Context`
whose type resolver declares the claim context symbols ([D5 §8.2](D5-consolidation-identity-confidence.md#82-rule-context))
generated from the schema version. A rule that fails to type-check fails compilation, so a broken
rule never reaches a run. Severity `error` makes a failing claim `rejected`; `warning` records a
validation observation and lowers confidence (D5 §6). The file itself is checked by a strict model
of its sections (`extra="forbid"`); `linkml-lint` lints the schema files one by one, never the
directory, where it would lint `rules.yaml` as a schema (schema-rules note L-09).

**Rule-engine use** (closes OPEN-D2-3; schema-rules note L-04, L-05; rule-engine 5.1.0):
- Structured symbols are typed `OBJECT`s read through a `getattr` resolver; mapping dot-access is
  off (`mapping_attribute_lookup=False`, deprecated in 5.x and removed in 6.0) and the timezone is
  UTC. A typo, a nullable misuse, a wrong argument type or an unknown symbol fails at compile time.
- **Every nullable access uses `&.` or `??`.** rule-engine does not narrow a type after a null
  test, so `claim.value != null and claim.value.slot_kind` fails to compile; write
  `claim.value&.slot_kind`. Quantifiers are `$all(...)`/`$any(...)`; calls take positional
  arguments only.
- **Strings from `SchemaView` are cast to `str`** by the pack loader before they reach rule-engine:
  LinkML's `extended_str` values compared unequal there.
- **Builtins.** Each table becomes a typed `$<name>` builtin (`$roles_by_kind`); `$enums` maps each
  enum to its values and `$is_a(type, class)` reads schema inheritance. Functions are kept for
  parameterized lookups only.
- **Names in the view are prefixed** (§7.1): `claim.predicate`, `claim.subject.type`, the keys of
  the entity views' `identity` mappings (`claim.subject.identity&['stat:canonical_name']`, and
  `object.identity.stat:canonical_name` in a `views:` projection path), `$is_a`'s class argument
  and `$enums`'s keys (`$is_a(claim.subject.type, 'stat:RandomVariable')`). Qualifier
  attributes of `claim.qualifiers` are their local names (`claim.qualifiers.param_values`), because
  a rule-engine attribute is an identifier and cannot contain `:`; the view builder maps the stored
  prefixed qualifier keys to them, and they are unique within a schema version (§7.3).
- Facts about the claim pool are cached attributes of the claim view, computed once per view by
  one generic view builder, because the language has no recursion or joins. Generic facts are built
  in: flattened condition nodes and the claims they reference, statement premises, the "given as a
  parameter value" pair (read through `ci:param_map`, §3.2, counting only givers whose role is
  `premise` or `example_value`, guideline §10.7 row 3), and slot competitors and alternatives
  (`claim.same_slot`, `claim.alternative_of`). Domain facts are declared by the pack in `views:`
  (source predicate, match, projected field) and compiled with the rules, so `family_params` is
  statistics data, not builder code (P0CL-07; operator, 2026-10-28). The builder and the M19 runner
  live in `validate` and work over the `core` keyed candidate claim, which a batch and the candidate
  pool both adapt into ([D9 §1](D9-repository-and-phase0.md#1-layout)).
- Every entry of `rules:` declares `at:`, the call sites it runs at: `batch` (submission, local
  refs) and/or `finalize` (keys). One compiled rule serves both because the view exposes `claim.id`
  (local ref, later key) and a nullable `claim.key` (D5 §8.2). Entries of `guideline:` declare
  neither `at:` nor `severity`: each is a warning at both call sites. `when` is optional on both
  (default `true`).
- `applies_to` takes a predicate, `subset:<name>` (a predicate subset, §3.2), `any`, or a list
  mixing predicates and subsets. The compiler expands it against the schema version, and a name the
  schema lacks fails compilation. A table value may use the token `none` for "no statement role".
- Each expression is compiled in its own context, and the nondeterministic builtins `$now`, `$today`
  and `$random` are rejected, so a rule's outcome depends only on its inputs (D6 §4 reuse). Compiled
  rules are rebuilt from the schema version, never pickled. These settings (the typed context, UTC,
  one context per expression, the rejected builtins, the `str` cast) live in one rule-language
  helper in `schema/`, which the policy chains reuse
  ([D6 §7.1](D6-orchestration-metrics-policies.md#71-language)), so rules and policies accept the
  same language.
> Status: **Tested** (S4, 2026-10-28, record `s4.rules`): the 16 rules of §6 and §9 (11 guideline
> checks among them) compile; over the 15 v1 batches at the batch site and a 12-unit pool at the
> finalize site, 866 evaluations with 0 unexpected fires, and 16 of 16 seeded violations caught
> (S0-R2's Python checker agrees on the 11 guideline seeds and on every unseeded batch); 7 of 7
> negative compiles rejected (a misspelled attribute, attribute access on a nullable, a wrong
> argument type, an unknown symbol, `$now`, a bare `all(...)`, a keyword argument). The `views:`
> attribute and a `$family_params(id)` function form both type-check and agree on 21 of 21
> evaluations; the attribute is kept. The finalize pool used spike keys, so `stat.param_keys_known`
> is re-run on P0-F-2b's keys
- **Readers per call site** (P0CL-14; operator, 2026-10-28). At `batch` the view reads formula
  symbols with `core/tex.py`'s TeX tokenizer, which is total and fast, never with the math grammar:
  submission runs in MCP worker threads, where the grammar's `setitimer` timeout cannot fire
  ([D4 M11](D4-method-catalog.md#m11-normalizeformula)). The view's parse fields are null at
  `batch`. A rule that needs the grammar (parse status, slot types) declares `at: [finalize]`, as
  `stat.domain_is_set` and `core.value_kind_matches_slot` do, so no grammar parse runs in an MCP
  worker thread.
  > Status: **Proposed** (2026-10-28); a test submits a pathological formula. The finalize reader's
  > hand-over as data is **Tested** in S4 with the I-R2 instruments' grammar reader (`s4.rules`)

**Guideline rules as batch warnings.** The guideline rules that code can check are the top-level
`guideline:` section of `rules.yaml`, part of the schema version (§2). Every entry is a `warning`
run at both call sites: when a model-facing batch is written (golden passes through `write_golden`,
LLM and agent proposals), so the author sees it and fixes the batch or says why the rule does not
apply, and at finalize, which records it on the claim:
- statement role by statement kind; structural claims take no role and are asserted;
- modality by role;
- which claims may carry a condition tree, and what it may hold (structural claims none; premises
  and example values index ranges only; formula and family-structure claims no claim nodes; every
  other claim references a premise);
- a formula excludes the variable it defines (its symbols read by the TeX tokenizer, above);
- symbol-map keys without backslash;
- binding priority;
- `parameter_role` only when it differs from the canonical name.

Rules the code cannot see (which premises a claim depends on, restrictions repeated in each
dependent claim) stay the author's. Invariant INV-06 and the guideline agree (a premise that no
condition references carries `scope: statement`); INV-06 is enforced at submission, where an item
that breaks it is rejected by `validate`'s batch checks (§7.3 side table, D5 §8.3, D8 §2.1), so no
rule repeats it.
> Status: **Tested** (S4, 2026-10-28, record `s4.rules`), the 11 entries of §9's `guideline:`
> section, as above; first in the spike instruments (S0-R2: `code/s0r2_rules.py`)

`rules.yaml` also has a `derive:` section: named derivation rules (for statistics, variance to
standard deviation, transitivity of `special_case_of`, applying a construction's parameter
mapping). Each names its source predicates, a match condition and a template for the derived
claim; M23 applies them ([D4 M23](D4-method-catalog.md#m23-deriveclaims)). Derivations that need
algebra call registered SymPy helpers, never inline code. Statistics v0 declares none.
> Status: **Proposed** (2026-10-28); S4 did not compile `derive:`

### 7.5 To the annotator reference

The compiler generates the **annotator reference** (§10.10) on every schema version, so what
golden passes, the agent and the LLM tiers write from cannot drift from the schema. It reads only
`SchemaView`, the compiled batch models, the rules file and `reference/`; it writes no predicate,
class, subset name or rule text of its own, so a second pack's reference needs no compiler change.
Its parts:

- **Entity types:** each entity class with its description, `ci:scope`, identity slots
  (`unique_keys`) and `examples`.
- **Predicates:** a card per predicate, grouped by the pack's predicate subsets (§3.2) with each
  subset's description at the head of its group, and the predicates in no subset last. Each card
  gives the subject and object types, the object's exact shape from the compiled model, the
  description, the predicate's own qualifiers, `ci:functional`, `symmetric` and `transitive`, and
  the guideline rules that apply to it by `applies_to`, with their descriptions. The statement-role
  and modality rules (guideline §10.3, §10.6) come from the subset descriptions and the tables
  section, never from predicate groups in the compiler.
- **Statement roles and modality:** the pack's `tables:` (§7.4), rendered.
- **Qualifiers and enums**, with their descriptions.
- **Shapes:** the exact JSON shape of every value, binding, condition node and batch item, rendered
  from the core Pydantic models.
- **Worked examples:** the pack's `reference/E*`, each a complete packet's text with its authored
  batch (and its citation frame once the example pages have sentence locators, §2), from pages
  outside every golden split (D7 §3.1, §4). They are inputs of the schema version (§2), and the
  packet assembler has a test that it reproduces each example's packet (D4 §4.1), so the examples
  show the packets models actually receive.
> Status: **Tested** (S4, 2026-10-28, record `s4.reference-diff`): the reference generated from the
> pack files (`code/s4/reference.py`, 25 cards) carries the information of S0-R2's hand-assembled
> one, with no empty meaning (S0-R2's had 6), plus descriptions, every item's exact shape, the tables,
> `unschematized` and the symmetric and transitive flags. Its one loss, the per-card role and modality
> sentence of the six family-structure-only predicates, is restored by the `family_structure`
> subset description (§9). The examples' place and the packet-assembler test are **Proposed**

**Size.** The generated reference is 12,851 Qwen3.5-9B tokens, 6,339 without the worked examples
(predicate cards 2,762, shapes 1,231; S0-R2's hand-assembled one 11,486 and 4,956). Filtering cards
by statement kind leaves at least 6,347 tokens, so it is not adopted (S4 variant V4); the local
tier's budget against D4's packet caps, and whether per-kind filtering earns a schema fact or the
shapes section can be dropped for constrained decoders, are decided with S3 (P0-A-1).
> Status: **Measured** (S4, 2026-10-28, record `s4.sizes`; Qwen3.5-9B tokenizer)

It replaces giving annotators the LinkML schema verbatim with a model excerpt beside it. The raw
schema stays available as background.
> Decision: [ADR-0011](../adr/0011-golden-author-and-annotator-inputs.md)
> Status: **Tested** in the spike (S0-R2, 2026-10-28: `code/s0r2_inputs.py`; the v1 passes did not open
> the raw schema) and as generated (S4, above); the production generator is not built

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

**Domain queries** are the pack's other plug-in, of the same kind: `domains/<name>/queries.py`
implements `serve`'s query protocol, and `serve` loads it beside its generic queries, so the
statistics queries live in the statistics pack
([D8 §5.2](D8-agent-and-query-interfaces.md#52-statistics); P0CL-07; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28)

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

The design copy of `domains/statistics/schema/statistics.yaml` and its `rules.yaml`: S4's pack files
(`results/s4/schema/domains/statistics/schema/` in the
[design-spikes evidence](../design_review/evidence/2026-10-28_design-spikes/S4-report.md)), with
one sentence added to the `family_structure` subset description (§7.5) and the rule view's names
prefixed (§7.1, §7.4). It covers the trace and the spike pages (LocationScale, Normal, LogNormal, Gamma).
Descriptions are model input (§1.3), first versions for spikes S2 and S3 to test and improve.

Modelling choices in the pack file, and why:
- the mixin **`Parameterized`** (on `DistributionFamily` and `FamilyConstruction`) is the domain of
  `has_parameter` and the range of the identity slot `family`, so the side table's class check
  excludes a random variable as a parameter's owner; `stat.no_family_on_variable` is subsumed by it
  and stays as the test of the `$is_a` builtin;
- `parameter_role` is not multivalued: `multivalued` describes one instance record, and a
  predicate's claims are separate records;
- `symbol` is a plain slot of `RandomVariable`, not an identity attribute: batches carry it at the
  top of the entity item, and `identity` holds only `unique_keys` slots;
- `special_case_of` is `transitive`; `identical_parameter` is `symmetric`; the condition
  predicates carry `ci:symmetric` (§5);
- every class, predicate, qualifier and permissible value has a description (`linkml-lint`'s
  `recommended` rules at error), including the shapes of `param_mapping` (`{<name>: <string>}`),
  `param_symbols` (`{<name>: <formula>}`) and `param_constraints` (a condition tree), which the
  generated reference renders (OPEN-D2-10).
> Status: **Tested** (S4, 2026-10-28, records `s4.pack-lint`, `s4.batch-validation`): the file lints
> with 0 errors with its core import, its 25 predicate branches validate the 135 listed batches
> after migration (§7.3), and every `has_parameter` subject and parameter `family` in them is a
> `Parameterized` class. The added subset sentence is **Proposed**

```yaml
id: https://corpus-structure.dev/domains/statistics
name: statistics
title: Statistics schema
description: >-
  Statistics schema v0 (D2 §9) in the native form of D2 §3: it covers the trace and the spike pages
  (LocationScale, Normal, LogNormal, Gamma). Descriptions are model input (D2 §1.3).
version: 0.2.0
license: https://creativecommons.org/publicdomain/zero/1.0/
prefixes:
  linkml: https://w3id.org/linkml/
  ci: https://corpus-structure.dev/ci/
  stat: https://corpus-structure.dev/domains/statistics/
  core: https://corpus-structure.dev/core/
default_prefix: stat
default_range: string
imports:
  - linkml:types
  - ../../core/schema/core

subsets:
  formula_definition:
    description: >-
      Formula claims that define a variable, a concept or a construction by a formula, or a family
      by a transformation. They hold by the form of the formula: role definiens in a definition or
      for a formula introducing a variable; modality defined when stipulated, asserted when
      concluded; no claim nodes, only the restrictions stated with them on their own symbols
      (guideline §10.7 rule 2).
  family_structure:
    description: >-
      Claims about a family's parameters as such. They hold by the structure of the family: no claim
      nodes, only the restrictions stated with them on their own symbols (guideline §10.7 rule 2);
      a parameter symbol binds family_param (§10.7 row 2); stated only in a definition of the family
      (§10.4). In a definition their role is definiens and their modality defined.
  distribution:
    description: >-
      Distribution claims: the parameter values a sentence states, keyed by the family's canonical
      parameter names (guideline §10.5).

classes:
  DistributionFamily:
    is_a: Entity
    mixins: [Distributed, Parameterized]
    title: distribution family
    description: >-
      A named family of probability distributions, possibly with parameters: the normal
      distribution, the gamma distribution, the standard normal distribution. Mentions include
      adjectival forms ("normally distributed", "has a gamma distribution").
    examples:
      - value: the normal distribution
      - value: lognormal distribution
      - value: normally distributed
    annotations:
      ci:scope: global
      ci:extract: mention

  FamilyConstruction:
    is_a: Entity
    mixins: [Parameterized]
    title: family construction
    description: >-
      A way of generating a family of distributions from a base distribution, such as the
      location-scale family, the location family or the scale family associated with a
      distribution, or the general exponential family. Not itself a single distribution family.
    examples:
      - value: location-scale family
      - value: scale family associated with the given distribution
    annotations:
      ci:scope: global
      ci:extract: mention

  FamilyParameter:
    is_a: Entity
    title: distribution parameter
    description: >-
      A parameter of a distribution family or construction, such as the location parameter, the
      scale parameter, the shape parameter k, the rate, the mean or the standard deviation when
      these parameterize the family.
    slots: [family, canonical_name]
    slot_usage:
      family: {required: true}
      canonical_name: {required: true}
    unique_keys:
      identity:
        unique_key_slots: [family, canonical_name]
    examples:
      - value: location parameter
      - value: shape parameter k
      - value: the rate parameter
    annotations:
      ci:scope: global
      ci:extract: mention
      ci:parameter_class: family

  RandomVariable:
    is_a: Entity
    mixins: [Distributed]
    title: random variable
    description: >-
      A random variable denoted by a symbol (X, Y, Z, X_1, W) or by an expression in other random
      variables (a + b X, e^Y, X_1 + X_2). Local to the statement or section that introduces it.
    slots: [symbol]
    examples:
      - value: X
      - value: a + b X
      - value: X_1 + X_2
    annotations:
      ci:scope: local
      ci:extract: mention

  Concept:
    is_a: Entity
    title: mathematical concept
    description: >-
      A defined mathematical term that is not a distribution family, construction or parameter: the
      gamma function, the standard score, the moment generating function.
    examples:
      - value: the gamma function
      - value: the standard score
    annotations:
      ci:scope: global
      ci:extract: mention

  Distributed:
    mixin: true
    description: Things that have a distribution and its characteristics.

  Parameterized:
    mixin: true
    description: Things that have parameters, a family or a construction.

  ParamValue:
    is_a: MapEntry
    description: >-
      One entry of a param_values or param_symbols map: key a canonical parameter name, value the
      formula it takes.
    slot_usage:
      value: {range: Formula, inlined: true}

  ParamMapping:
    is_a: MapEntry
    description: >-
      One entry of a param_mapping map: key the target family's parameter canonical name, value the
      canonical name of the base family's parameter it corresponds to.
    slot_usage:
      value: {range: string}

slots:
  # entity attributes
  family:
    range: Parameterized
    description: The family or construction the parameter belongs to (a local ref in batches).
  canonical_name:
    description: >-
      The parameter's name from the phrase that first names its symbol as a parameter of the
      family: its role word spelled as the ParameterRole value, else the symbol without backslash
      (guideline §10.4).
  symbol:
    description: The symbol or expression that denotes the random variable, as written.

  # predicates
  has_distribution:
    domain: RandomVariable
    range: DistributionFamily
    in_subset: [distribution]
    description: >-
      The random variable has a distribution in the family, optionally with stated parameter
      values. "X is normally distributed with mean μ and variance σ²".
    annotations:
      ci:role: predicate
      ci:qualifiers: param_values
      ci:identity_qualifiers: param_values
      ci:param_map: param_values
      ci:extract: relation
      ci:functional: true
  defined_as:
    domain: RandomVariable
    range: Formula
    in_subset: [formula_definition]
    description: The random variable is defined by a formula in other variables. "let X = a + b Z".
    annotations: {ci:role: predicate, ci:extract: llm}
  takes_values_in:
    domain: RandomVariable
    range: SetExpr
    description: The random variable's values lie in the set. "with values in ℝ".
    annotations: {ci:role: predicate, ci:extract: llm}
  has_parameter:
    domain: Parameterized
    range: FamilyParameter
    in_subset: [family_structure]
    description: A family or construction has this parameter. "with shape parameter k and scale parameter b".
    annotations: {ci:role: predicate, ci:extract: relation}
  parameter_role:
    domain: FamilyParameter
    range: ParameterRole
    in_subset: [family_structure]
    description: >-
      The parameter plays this role, stated when it differs from its canonical name. "σ is the shape
      parameter".
    annotations: {ci:role: predicate, ci:extract: llm}
  parameter_domain:
    domain: FamilyParameter
    range: SetExpr
    in_subset: [family_structure]
    description: The set of the parameter's allowed values. "b ∈ (0, ∞)".
    annotations: {ci:role: predicate, ci:extract: llm, ci:functional: true}
  identical_parameter:
    domain: FamilyParameter
    range: FamilyParameter
    symmetric: true
    in_subset: [family_structure]
    description: >-
      Two parameter names denote the same parameter of the family. "the location and scale
      parameters are also the mean and standard deviation, respectively".
    annotations: {ci:role: predicate, ci:extract: llm}
  derived_parameter:
    domain: FamilyParameter
    range: Formula
    in_subset: [family_structure]
    description: The parameter equals a formula in the family's other parameters. "e^μ is the scale parameter".
    annotations: {ci:role: predicate, ci:extract: llm}
  special_case_of:
    domain: DistributionFamily
    range: Entity
    transitive: true
    in_subset: [family_structure]
    description: >-
      The family is the special case of another family or construction obtained under parameter
      constraints. "The exponential distribution is the gamma distribution with k = 1".
    annotations:
      ci:role: predicate
      ci:qualifiers: param_constraints
      ci:identity_qualifiers: param_constraints
      ci:extract: llm
  transformation_of:
    domain: DistributionFamily
    range: DistributionFamily
    in_subset: [formula_definition, family_structure]
    description: >-
      Variables in this family arise by transforming a variable of the other family. "X = e^Y has
      the lognormal distribution".
    annotations:
      ci:role: predicate
      ci:qualifiers: transform param_mapping
      ci:identity_qualifiers: transform
      ci:extract: llm
  limit_of:
    domain: DistributionFamily
    range: DistributionFamily
    description: The family is a limit of the other under a stated limiting operation.
    annotations:
      ci:role: predicate
      ci:qualifiers: limit param_mapping
      ci:extract: llm
  member_of_construction:
    domain: DistributionFamily
    range: FamilyConstruction
    description: >-
      The family is the construction applied to a base. "The general normal distribution is the
      location-scale family associated with the standard normal distribution".
    annotations:
      ci:role: predicate
      ci:qualifiers: base
      ci:identity_qualifiers: base
      ci:extract: llm
  construction_formula:
    domain: FamilyConstruction
    range: Formula
    in_subset: [formula_definition, family_structure]
    description: >-
      The formula generating members of the construction, without the variable it defines. "X = a +
      b Z" gives a + b Z.
    annotations:
      ci:role: predicate
      ci:qualifiers: base_variable param_symbols
      ci:extract: llm
  support:
    domain: Distributed
    range: SetExpr
    description: The support of the distribution, the set of values with positive density or mass. "on (0, ∞)".
    annotations: {ci:role: predicate, ci:extract: llm}
  pdf:
    domain: Distributed
    range: Formula
    description: The probability density (or mass) function, with its argument domain as a condition.
    annotations: {ci:role: predicate, ci:extract: llm}
  cdf:
    domain: Distributed
    range: Formula
    description: The cumulative distribution function, with its argument domain as a condition.
    annotations: {ci:role: predicate, ci:extract: llm}
  mgf:
    domain: Distributed
    range: Formula
    description: The moment generating function, with the set of arguments where it is finite as a condition.
    annotations: {ci:role: predicate, ci:extract: llm}
  mean_value:
    domain: Distributed
    range: Formula
    description: The mean (expected value) as a formula. "E(X) = μ".
    annotations: {ci:role: predicate, ci:extract: llm}
  variance_value:
    domain: Distributed
    range: Formula
    description: The variance as a formula. "var(X) = σ²".
    annotations: {ci:role: predicate, ci:extract: llm}
  definition_formula:
    domain: Concept
    range: Formula
    in_subset: [formula_definition]
    description: The formula defining the concept. "the standard score is (X - μ) / σ".
    annotations: {ci:role: predicate, ci:extract: llm}

  # qualifiers
  param_values:
    range: ParamValue
    multivalued: true
    inlined: true
    description: >-
      The parameter values the sentence states, an object from the family's canonical parameter
      names to formulas: {"shape": <formula>, "scale": <formula>} (guideline §10.5).
    annotations: {ci:role: qualifier}
  param_constraints:
    range: Condition
    description: A condition tree (D1 §7) over the base family's parameters under which the special case holds (k = 1).
    annotations: {ci:role: qualifier}
  transform:
    range: Formula
    description: The transformation, as a formula in the base variable. "e^Y".
    annotations: {ci:role: qualifier}
  param_mapping:
    range: ParamMapping
    multivalued: true
    inlined: true
    description: >-
      An object from the target family's canonical parameter names to the base family's canonical
      parameter names they correspond to: {"shape": "sigma"}.
    annotations: {ci:role: qualifier}
  limit:
    range: PhraseValue
    description: The limiting operation as stated. "as n → ∞".
    annotations: {ci:role: qualifier}
  base:
    range: Entity
    description: The base family the construction is applied to.
    annotations: {ci:role: qualifier}
  base_variable:
    range: RandomVariable
    description: The base variable the construction formula transforms (Z in a + b Z).
    annotations: {ci:role: qualifier}
  param_symbols:
    range: ParamValue
    multivalued: true
    inlined: true
    description: >-
      An object from the construction's canonical parameter names to the symbols that stand for
      them in its formula: {"location": <formula a>, "scale": <formula b>}.
    annotations: {ci:role: qualifier}

enums:
  ParameterRole:
    description: The role a parameter plays in its family.
    annotations: {ci:extract: attribute, ci:applies_to: FamilyParameter}
    permissible_values:
      location: {description: A location parameter.}
      scale: {description: A scale parameter.}
      shape: {description: A shape parameter.}
      rate: {description: A rate parameter.}
      mean: {description: The mean as a parameter.}
      variance: {description: The variance as a parameter.}
      standard_deviation: {description: The standard deviation as a parameter.}
      precision: {description: The precision (reciprocal variance) as a parameter.}
      degrees_of_freedom: {description: Degrees of freedom.}
      success_probability: {description: A success probability.}
      number_of_trials: {description: A number of trials.}
      lower_bound: {description: A lower bound of the support.}
      upper_bound: {description: An upper bound of the support.}
      other: {description: Another stated role.}
  ConditionPredicate:
    description: The condition predicates of pred nodes (D2 §5).
    permissible_values:
      independent:
        description: The arguments are independent.
        annotations: {ci:arity: 2+, ci:args: RandomVariable, ci:symmetric: true}
      identically_distributed:
        description: The arguments have the same distribution.
        annotations: {ci:arity: 2+, ci:args: RandomVariable, ci:symmetric: true}
      iid:
        description: The arguments are independent and identically distributed.
        annotations: {ci:arity: 2+, ci:args: RandomVariable, ci:symmetric: true}
```

`domains/statistics/schema/rules.yaml`:

```yaml
# Statistics pack rules (D2 §7.4, §9). Sections: views (pool facts compiled for the generic view
# builder), rules (named checks with severity and call sites), guideline (the guideline rules code can
# check: always warnings, at both call sites), tables (lookup tables compiled to typed $ builtins and
# rendered by the annotator reference), derive (derivations, M23; none in v0).
#
# Rule language (one helper, shared with policies): rule-engine 5.1 under a typed context generated
# from the schema version; OBJECT symbols read through getattr; no mapping dot-access; UTC; one
# context per rule; $now, $today and $random rejected. Symbols are the claim view's (D5 §8.2).

views:
  family_params:
    description: Canonical names of the parameters the claim's object family has.
    applies_to: stat:has_distribution
    source: stat:has_parameter                 # the source predicate
    match: {source: subject, claim: object}    # source claims whose subject is this claim's object
    project: object.identity.stat:canonical_name   # what each matching source claim contributes

rules:
  - id: stat.param_keys_known
    applies_to: stat:has_distribution
    severity: warning
    at: [finalize]
    description: >-
      Every param_values key is the canonical name of a parameter the family has in this run, or a
      ParameterRole value. A family's parameters are complete only at finalize.
    check: >-
      $all([k in claim.family_params or k in $enums['stat:ParameterRole']
            for k in (claim.qualifiers.param_values ?? {}).keys])

  - id: stat.one_distribution_per_statement
    applies_to: stat:has_distribution
    severity: error
    at: [batch, finalize]
    description: >-
      At most one asserted or defined stated has_distribution per variable per statement, unless the
      claims are marked as alternatives; derived claims are exempt.
    when: "claim.establishment == 'stated' and claim.qualifiers.modality in ['asserted', 'defined']"
    check: "$all([o in claim.alternative_of for o in claim.same_slot])"

  - id: stat.domain_is_set
    applies_to: [stat:parameter_domain, stat:takes_values_in, stat:support]
    severity: warning
    at: [finalize]
    description: >-
      The object parses as a set (parse ok under the set kind); otherwise a warning, and the object is
      kept as written. Reads the grammar's parse status, so it runs at finalize only.
    check: "(claim.value&.parse ?? '') == 'ok'"

  - id: stat.no_family_on_variable
    applies_to: stat:has_parameter
    severity: error
    at: [batch, finalize]
    description: >-
      The subject of has_parameter is not a random variable. Subsumed by the predicate's domain
      (Parameterized) once the side-table type check runs; kept as the check of the $is_a builtin.
    check: "not $is_a(claim.subject.type, 'stat:RandomVariable')"

guideline:
  - id: guideline.structural_role_modality
    applies_to: subset:structural
    description: Structural claims take no statement_role and are asserted (guideline §10.3, §10.6).
    check: "claim.statement_role == null and claim.qualifiers.modality == 'asserted'"

  - id: guideline.role_by_kind
    applies_to: any
    description: A claim's statement_role is one its statement's kind gives (guideline §10.3).
    when: "not ('structural' in claim.groups) and claim.statement_kind != null"
    check: >-
      not (claim.statement_kind in $roles_by_kind)
      or (claim.statement_role ?? 'none') in $roles_by_kind[claim.statement_kind]

  - id: guideline.modality_by_role
    applies_to: any
    description: A claim's modality follows from its statement_role (guideline §10.6).
    when: "not ('structural' in claim.groups) and claim.statement_role != null"
    check: >-
      not (claim.statement_role in $modality_by_role)
      or claim.qualifiers.modality == $modality_by_role[claim.statement_role]

  - id: guideline.structural_no_conditions
    applies_to: subset:structural
    description: Structural claims carry no conditions (guideline §10.7 rule 4).
    check: "claim.condition_nodes.is_empty"

  - id: guideline.premise_conditions_index_only
    applies_to: any
    description: >-
      Premises and example values carry no conditions except the range of an index they are stated
      for; restrictions go to the claims that depend on them (guideline §10.7 rule 1).
    when: "not ('structural' in claim.groups) and claim.statement_role in ['premise', 'example_value']"
    check: >-
      $all([n.op == 'and' or (n.op == 'member' and (n.x_latex ?? '') in claim.subject.index_symbols)
            for n in claim.condition_nodes])

  - id: guideline.no_claim_nodes_on_form
    applies_to: [subset:formula_definition, subset:family_structure]
    description: >-
      Formula and family-structure claims carry no claim nodes, only restrictions on their own
      symbols (guideline §10.7 rule 2).
    when: "not (claim.statement_role in ['premise', 'example_value'])"
    check: "claim.claim_refs.is_empty"

  - id: guideline.references_a_premise
    applies_to: any
    description: >-
      Every other claim carries a claim node for the premises it depends on: it references at least
      one premise of its statement or of a context-premise assumption (guideline §10.7 rule 3).
    when: >-
      not ('structural' in claim.groups or 'formula_definition' in claim.groups
           or 'family_structure' in claim.groups)
      and not (claim.statement_role in ['premise', 'example_value'])
    check: "claim.statement_premises.is_empty or $any([p in claim.claim_refs for p in claim.statement_premises])"

  - id: guideline.parameter_role_differs
    applies_to: stat:parameter_role
    description: A parameter_role claim is stated only when the role differs from the canonical name (guideline §10.4).
    check: "(claim.value&.v ?? '') == '' or (claim.value&.v ?? '') != (claim.subject.identity&['stat:canonical_name'] ?? '')"

  - id: guideline.formula_excludes_defined_variable
    applies_to: [stat:defined_as, stat:construction_formula]
    description: A formula that defines a variable or generates a family excludes the variable it defines (guideline §10.7).
    check: "not ((claim.value&.latex ?? '') =~ r'\\s*[A-Za-z]\\w*(_\\{?\\w+\\}?)?\\s*=')"

  - id: guideline.symbol_keys_no_backslash
    applies_to: any
    description: Symbol-map keys are written without backslash (guideline §10.7).
    check: "$all([not (b.symbol =~ r'\\\\') for b in claim.bindings])"

  - id: guideline.binding_priority
    applies_to: any
    description: >-
      A symbol another claim gives as a parameter value binds param_of, not free or family_param,
      unless the claim is about the family as such (guideline §10.7 rows 2-4).
    check: >-
      $all([not (b.symbol in claim.given_by_others and b.bind in ['free', 'family_param']
                 and not (b.symbol in claim.gives_symbols)
                 and not ('family_structure' in claim.groups and b.bind == 'family_param'))
            for b in claim.bindings])

tables:
  roles_by_kind:                 # statement kind -> statement roles its non-structural claims take; none: no role
    definition: [definiens, premise]
    theorem: [premise, conclusion, definiens]
    proposition: [premise, conclusion, definiens]
    corollary: [premise, conclusion, definiens]
    lemma: [premise, conclusion, definiens]
    remark: [premise, conclusion, definiens, none]
    example: [example_value]
    exercise: [example_value]
    convention: [none]
    assumption: [premise]
    proof: []
    solution: []
  modality_by_role:              # statement role -> the modality it takes
    premise: supposed
    definiens: defined
    conclusion: asserted
    example_value: exemplified

derive: []                       # derivation rules (D2 §7.4, M23); none in v0
```
> Status: **Tested** (S4, 2026-10-28, record `s4.rules`), as §7.4 reports; the prefixed names in
> `$enums['stat:ParameterRole']`, `$is_a(…, 'stat:RandomVariable')`, the identity key
> `stat:canonical_name` and the `family_params` projection path are **Proposed** (S4's file used
> local names)

`stat.variance_nonnegative` (the conditions imply variance ≥ 0 when the formula parses) is not a
rule: it has no rule-engine expression and is checked by M20 with z3 and by the statistics
verifiers ([D4 M21](D4-method-catalog.md#m21-verifystatistics), §7.6). INV-06 (a `supposed` claim
is referenced by a condition or has a `scope`) has no rule here either: an item that breaks it is
rejected at submission (§7.3, D5 §8.3).

## 10. Guideline v1 (statistics)

This is the design copy of `domains/statistics/guideline.md`. The pack's file is ported from this
section, not from the S0-R2 file (`../design_review/evidence/2026-10-28_design-spikes/s0r2/guideline_v1.md`):
the two differ in one rule, the parameter naming of §10.4 (review B2), which the v1 reference and
trace T4 follow, and otherwise only in cross-reference wording (checked 2026-10-28). Guideline v1,
frozen for phase 0, is this section's text (design authority, 2026-10-28). Golden passes, written by
Sonnet subagents, work from it together with the generated annotator reference (§10.10)
([D7 §3](D7-evaluation-goldens-outer-loop.md#3-golden-authoring-protocol), ADR-0011); the operator
steers it ([D7 §8](D7-evaluation-goldens-outer-loop.md#8-the-operators-outer-loop)). In
`guideline.md`, sections 10.3–10.8 carry the `<!-- core -->` tag that puts them into LLM prompts
(D4 §4.2, D7 §2).

> Decision: [ADR-0011](../adr/0011-golden-author-and-annotator-inputs.md)
> Status: **Measured** as the S0-R2 candidate (2026-10-28): with it, the generated reference and
> query-assembled context, Sonnet and Haiku passes reached full-tier F1 0.77 and 0.68 against the
> reference, from 0.37 and 0.35 under v0, and agreed at 0.76 on six held-out units
> ([S0-R2 report](../design_review/evidence/2026-10-28_design-spikes/S0-R2-report.md)). Every rule states a choice that v0 left to inference
> and the S0 gap analysis found contested (../design_review/evidence/2026-10-28_design-spikes/results/s0/gaps.md, GG-1…17). Its open points are
> OPEN-D2-7 … OPEN-D2-20 (§11).

### 10.1 Purpose

Produce, for one annotation unit, the complete set of entities, statements and claims that the
source states, in claim form, each with minimal evidence spans. Completeness is judged against
this guideline, not against what any extractor can find. Where this guideline gives a rule, follow
it even if another reading seems natural; where it gives none, choose, and say so in your notes.

### 10.2 The annotation unit and its context

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

### 10.3 What to capture, and the statement role of each claim

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

### 10.4 Entities

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
  > Status: **Proposed** (2026-10-28, design owner's review B2). It replaces v1's "the role word
  > stated anywhere in the unit", which contradicted the v1 reference and trace T4 (`sigma` with a
  > `parameter_role` shape). Pass SV, pass HV and the S0-R2 adjudicator followed the earlier wording
  > on T4 (`shape`), so part of their T4 loss was the rule's defect, not theirs.
- `has_parameter`, `parameter_domain` and `parameter_role` are stated only in a definition of the
  family; elsewhere "F with shape parameter k" supplies `param_values` only.

### 10.5 Claims

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

### 10.6 Modality

| Claim | Modality |
|---|---|
| A supposition: "suppose", "assume", "if", or "let" about something taken as given | `supposed` |
| What a definition stipulates, including "let X = …" or "the variable X = b Z" that introduces the defined construction's variable | `defined` |
| What a theorem, corollary or remark concludes; a formula introducing a variable inside a theorem | `asserted` for conclusions; `defined` for the introducing formula |
| Setup values in examples and exercises | `exemplified` |
| A convention | `conventional` |
| Structural claims (`defines`, `proves`, `refers_to`, `follows_from`) | `asserted` |

### 10.7 Conditions, formulas and symbol bindings

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

### 10.8 Evidence, ambiguity and limits

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

### 10.9 Output

A model-facing `ClaimProposalBatch` per unit (§7.3), with `statements`, `entities` (local
ones with their `extent`), `claims`, `alternatives` and `unsupported`, citing evidence by sentence
id and quote.

### 10.10 Generated annotator reference

The annotator reference is generated from the schema (§7.5): every entity type; every predicate with
its subject and object types, description, the qualifiers it takes and the guideline rules that apply
to it, grouped by predicate subset under the subset's description, which states the group's role,
modality and condition rule under §10.3, §10.6 and §10.7 (for `family_structure`: in a definition,
role `definiens` and modality `defined`); the role and modality tables; the binding kinds; the exact
value, node and item shapes; and complete worked examples.
> Status: **Tested** (S4, 2026-10-28, record `s4.reference-diff`); the `family_structure` sentence
> is **Proposed** (§9)

### 10.11 Direction log

*(One entry per operator direction: date, the direction in the operator's words, the guideline
change it produced, the golden units re-authored.)* The log is kept in
`domains/<name>/directions.md` and in the `ops.intervention` rows of kind `direction`, outside the
guideline's content hash: recording a direction must not create a guideline version, or every
direction would invalidate reuse (D6 §4). Only the guideline changes a direction causes do. The
generated reference (§10.10) is hashed with the schema version's compiled artifacts.

| Date | Direction | Guideline change | Units re-authored |
|---|---|---|---|
| 2026-10-28 | "It looks like sonnet is the right call, and the rules establish a clear approach" | v0 → v1 (roles, modality, conditions, bindings, context premises, indexed families, parameter naming); golden author Sonnet (ADR-0011) | None yet (no golden set exists; the S0 reference was conformed to v1 in the spike) |

## 11. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D2-1 | Exact `Schema.from_dict` keys for structures, attributes and per-type thresholds in gliner2 2.1.0 | **Answered for v0** (S4, 2026-10-28, record `s4.gliner-roundtrip`): keys `entities`, `entity_attributes`, `classifications`, `relations`, unknown keys rejected; compile check `Schema.from_dict(d).to_dict() == d` on the canonical form and the same for `JointSchema`, §7.2. Structures and per-type thresholds are unexercised (v0 declares none); the GLiNER2 compiler is phase 1 |
| OPEN-D2-2 | Raw LaTeX or masked math placeholders in GLiNER2 input | Spike S2 |
| OPEN-D2-3 | rule-engine syntax for the `rules.yaml` checks, and whether custom functions such as `family_params` are better as resolver-backed symbols | **Closed** (S4, 2026-10-28, record `s4.rules`; first [schema-rules note](../design_review/evidence/2026-10-28_library-schema-rules/README.md) L-04, L-05): typed `OBJECT` contexts, cached view attributes declared in `views:`, `at:` per rule, functions only for parameterized lookups (`$is_a`); both forms type-check and agree, §7.4, D5 §8.2 |
| OPEN-D2-4 | Whether property predicates (`mean_value`, `pdf`, …) should be one `has_property` predicate with a `property` qualifier instead | Spike S0 annotations: count how many distinct properties appear; **answered by S0** (2026-10-28): keep separate property predicates (only `mean_value` and `variance_value` were needed); add a standard-deviation property, now OPEN-D2-17 |
| OPEN-D2-5 | Whether "standard normal" is better a family with `special_case_of` or a parameterization of the normal family | Spike S0 and outer-loop direction; **answered by S0** (2026-10-28): standardized families as families of their own worked in every pass; `special_case_of` only when the source states the constraint; guideline v1 §10.4 |
| OPEN-D2-6 | Whether LinkML annotation values that are lists (`ci:examples`, `ci:qualifiers`) round-trip through `SchemaView` unchanged | **Closed** (S4, 2026-10-28, record `s4.pack-lint`; first schema-rules note L-06): native `examples`, `unique_keys`, subsets, `symmetric`, `transitive`, `title`, `ifabsent`, and scalar `ci:` annotations only, space-separated for the three list annotations; 129 of 129 round-trip, §3 |
| OPEN-D2-7 | Members of an indexed family as condition arguments: v1 makes `X_i` one entity but lists independence over `X_1, X_2, X_n`; needs an indexed-set argument (base, index, range) and a `forall` over claims (S0 gap RG-2) | Schema change with D1 §7; then a guideline rule |
| OPEN-D2-8 | Which premises a claim depends on: "every premise of its statement" over-references when a statement holds independent results; candidate rule "the premises whose entities or symbols the claim uses" | Next guideline revision, checked on held-out units |
| OPEN-D2-9 | Scope of a section-level supposition that no condition references: `scope: statement` or `section` when the source says "In this section" | Guideline v2 |
| OPEN-D2-11 | Restricting phrases ("In some settings", S0 gap GG-16): a `phrase` condition or a `hedge` | Guideline v2 |
| OPEN-D2-12 | Recalled definitions ("Recall that …", GG-12): kind, modality, `refers_to` or `defines` | Guideline v2 |
| OPEN-D2-13 | What counts as an explicit claim in framing text (GG-8), and the same fact in two predicate forms (GG-10) | Guideline v2 |
| OPEN-D2-14 | Local definitions "where μ = …" (RG-4): a `defined_by` binding | Schema revision with D1 §6.1 |
| OPEN-D2-15 | What an exercise asks for: an `asks_for` predicate (SG-1); `posed` is reserved until it lands (D1 §5.2) | Schema v0.2 |
| OPEN-D2-16 | Numbers with units as parameter values: `ParamValue.value` widened to the D1 value union (SG-3) | Schema v0.2 |
| OPEN-D2-17 | A standard-deviation property predicate, with skewness and kurtosis decided together (SG-4, OPEN-D2-4) | Schema v0.2 |
| OPEN-D2-18 | A family's parameterizations, so canonical parameter names stay stable across units (RG-7, with §10.4) | Schema revision |
| OPEN-D2-19 | Independence stated as a setup fact (SG-2) against guideline v1's "independence is a condition only"; decided with OPEN-D2-7 | Schema revision |
| OPEN-D2-20 | Concept-of ("Y is the standard score of X", SG-5) and notation ("Ω is the set of outcomes", SG-8) predicates, or out of scope; a standard member without a stated constraint (SG-9); a `RandomVariable` without a symbol (SG-10) | Schema revision |
| OPEN-D2-10 | Documented shapes for `param_mapping`, `param_symbols` and `param_constraints` (SG-11), so the generated reference can state them | **Answered** (S4, 2026-10-28, record `s4.reference-diff`): `{<name>: <string>}`, `{<name>: <formula>}` and a condition tree, in the qualifiers' descriptions in statistics.yaml (§9), rendered by the reference |


## 12. Statistics pack files v0

Drafts for the Siegrist source profile and the statistics pack's `methods.yaml` and
`slices.yaml`. Its `policies.yaml` v0 is
[D6 §7.1](D6-orchestration-metrics-policies.md#71-language) and §7.5. The Siegrist rules below
come from inspecting the 78 first-pass pages (2026-10-28); spike S1 checks them and reports what
they miss.

What the inspection found, and why the hints look the way they do:

- Every page defines its LaTeX macros in a `<div class="latex">` block of `\newcommand`s
  (`\R`, `\N`, `\E`, `\var`, `\P`, `\sd`, `\bs`, `\skw`, `\kur`, `\cov`, `\cor`, `\ms`, and a few
  rarer ones). M01 excludes the block from canonical text and records the macros.
- Sections have no wrapper elements: `<h3>` and `<h4>` headings open nested sections. The page
  title is the `<h2>` inside `<header>`; `<header>` and `<footer>` otherwise hold navigation.
- Unit ids are topical (`pdf`, `mom`, `cdf`, `rel`, `qnt`, …), not statement kinds, and many
  units have no id. Statement kinds show in **block classes** instead: `p.dfn` (183) and `p.dfm`
  are definitions, `p.math` (1,862) results, `p.app` (422) instructions for simulation apps. Units
  under the h3 sections "Examples and Applications", "Examples and Special Cases" and
  "Computational Exercises" are examples or exercises.
- `<details>` blocks almost always have the summary "Details:" (1,586 of 1,592) and hold proofs,
  or solutions inside examples and exercises.

### 12.1 `methods.yaml`

A source profile describes a source's HTML, not a domain (D4 M01), so it lives outside the pack in
`sources/<profile>.yaml` (§2): a second domain over the same source reuses it, and a second source
for statistics adds a file without editing the pack. The pack's `methods.yaml` names the profile
and the sentence configuration (`configs: ingest.html`); `ingest.html`'s configuration hash takes
the profile it names, resolved, and the `segment.sentences` configuration it names, resolved,
because M03 runs as a step of M01's task (D4 M03). Adding a profile therefore changes no other
configuration. The profile also declares the claims its containment structure states
(`synthesize:`), which consolidation applies (D5 §3.5), so that convention is source data rather
than consolidation code (P0CL-07; operator, 2026-10-28).

The profile also places the source in the corpus. `root` is the source's directory under the
corpus root, and a document's page, the `page` of its locators (D1 §3.4), is its source URI less
the root, so `siegrist_random/random/special/Normal.html` is `special/Normal.html`. `index` names
the corpus index that `ci project init` registers documents from and that the `{index: …}` slice
selector reads (§12.2); two documents whose pages collide are refused at project init (D8 §4).
`language` names the text-search configuration of the source's segments (`kb.segment.ts_config`,
D3 §5), outside the rendition's content digest (D1 §3.1), since it changes search, not content.
> Status: **Proposed** (2026-10-28) for the location, `synthesize:`, `root`, `index` and
> `language`; the profile's other values are **Tested** (S1, below)

`sources/siegrist.yaml`:

```yaml
version: 0.1.0
root: "siegrist_random/random"                     # relative to the corpus root; page = source URI less root
index:                                             # the corpus index, one row per page
  file: "../index/siegrist_sections.tsv"           # relative to the corpus root
  page: path                                       # column holding the page
  first_pass: first_pass                           # column marking first-pass pages (`yes`)
language: english                                  # kb.segment.ts_config; outside the content digest
applies_to: "siegrist_random/random/**/*.html"     # relative to the corpus root
exclude:                                           # CSS selectors; excluded text is recorded per rule (D4 M01)
  scripts: "script, noscript"
  macro_block: "div.latex"                         # \newcommand block: excluded, macros recorded
  navigation: "header ol.map, footer"
  controls: "button"
  images: "img"                                    # figure captions stay, as `caption` segments
  chapter_lists: "ul.map"                          # S1: 75 chapter-index lists
title: "header h2"
sections: ["h3", "h4"]                             # each heading opens a section nested by level
unit: "div.unit"
block_hints:                                       # statement-kind hints from block classes
  "p.dfn": {statement_kind: definition}
  "p.dfm": {statement_kind: definition}
  "p.dfin": {statement_kind: definition}
  "p.math": {statement_kind: theorem}
  "p.exercise": {statement_kind: exercise}
  "p.exericse": {statement_kind: exercise}         # sic, as in the source
  "p.app": {statement_kind: remark, claim_bearing: false}
  "p.stat": {statement_kind: theorem}              # S1: 10 units open with p.stat
  "p.Proof": {statement_kind: proof}               # S1: 1 (special/Divisible.html)
section_hints:                                     # units under these h3 titles
  "Examples and Applications": example
  "Examples and Special Cases": example
  "Special Cases": example
  "Computational Exercises": exercise
details_kinds:                                     # statements for <details> blocks
  default: proof
  inside_example_or_exercise: solution
  by_summary: {"Answer": solution, "Answwer:": solution, "Notes:": remark}
  synthesize:                                      # claims the containment states; consolidation adds them (D5 §3.5)
    proof: {predicate: core:proves, object: enclosing_unit, evidence: summary}
    solution: {predicate: core:proves, object: enclosing_unit, evidence: summary}
math:
  inline: ["\\(", "\\)"]
  display: ["\\[", "\\]"]
  display_environments: ["align", "align*"]       # S1: 106 bare align blocks without \[
  page_macros: "div.latex"                         # per-rendition macro table; the pack map is only a fallback
references: {selector: "a.ref", render: browser}  # "[n]" as the page's Basic.js renders it
render:
  q: quotes                                        # <q> text in “ ”
  list_markers: {"ol.sub": parenthesized}          # "(a) "
  summary: heading                                 # a details summary is a heading segment
  figure: caption
orphan_text: paragraph                             # with attrs.orphan: true (S1: 44 runs)
# S1 merged (2026-10-28): every value above except `root`, `index`, `language` and `synthesize:` Tested on 78 pages (record s1.corpus); vocabulary in D4 M01
```

`domains/statistics/methods.yaml`:

```yaml
version: 0.1.0

math:
  macros:                                              # fallback when a page does not define a macro
    '\R': '\mathbb{R}'
    '\N': '\mathbb{N}'
    '\Z': '\mathbb{Z}'
    '\Q': '\mathbb{Q}'
    '\P': '\mathbb{P}'
    '\E': '\mathbb{E}'
    '\var': '\text{var}'
    '\sd': '\text{sd}'
    '\cov': '\text{cov}'
    '\cor': '\text{cor}'
    '\skw': '\text{skew}'
    '\kur': '\text{kurt}'
    '\mse': '\text{mse}'
    '\sgn': '\text{sgn}'
    '\bs': '\boldsymbol'
    '\ms': '\mathscr'
  constants: ['e', '\pi']

binders:                                               # M13 binder lexicon
  sentence_initial: [suppose, let, assume, fix, define, consider, recall, if]   # "if": Measured by the S0 M13 probe (2026-10-28, record s0.m13-probe-2), ADR-0012
  clause: [where, for]
  reopen: [again]                                      # "Suppose again …" re-opens the section's earlier binding
  section_wide: ["in this section", "throughout this section"]

aliases:                                               # label normalization (D5 §3.3) and M14
  articles: [the, a, an]
  head_words:
    DistributionFamily: [distribution, distributions]
  rewrites:                                            # applied in order, before head-word removal
    - {match: '^(\w+)ly distributed$', replace: '\1'}  # "normally distributed" → "normal"
    - {match: '^(\w+) distributed$', replace: '\1'}    # "gamma distributed" → "gamma"

cues:                                                  # M22
  negation: [not, no, never, neither, nor, cannot]
  hedge: [approximately, roughly, nearly, typically, usually, essentially]
  attribution: ["according to", "showed", "proved", "due to"]

patterns: []                                           # M08: none until a measured gap (D6 §7.3)

configs:                                               # named configurations, referenced as <method>/<name>
  ingest.html:
    default: {source_profile: siegrist, sentences: segment.sentences/default}   # both resolved into the hash
  segment.sentences:
    default: {model: en_core_web_sm, variant: math_as_word, exclude: [ner, lemmatizer]}
                                                       # b′ (D4 M03): each inline math span and reference marker is one
                                                       # word of a words-and-spaces Doc, no retokenizer (S1, OPEN-D1-1)
  agent.opus:                                          # caps in characters: the one cap authority for agent packets (D8 §3)
    extract: {mode: extract, examples: reference, hints: none, packet_cap_chars: 18000}  # phase 0: the reference's worked examples; dev-golden retrieval needs M04 (phase 1)
    adjudicate: {mode: adjudicate, packet_cap_chars: 9000, max_alternatives: 6}
    expectation: {mode: extract, role: expectation, examples: reference, hints: none, packet_cap_chars: 18000}
                                                       # golden-expectation runs (D7 §9); `role` keeps its digests apart from live tasks'
  llm.propose_claims:                                  # local tier: caps in the served model's tokens (D4 §4.1)
    default: {model: Qwen3.5-9B, temperature: 0, seed: 0, reasoning: false, examples: 2,
              hints: none, repair_retries: 1, packet_cap_tokens: 3000}   # S3 chooses model and reasoning
  llm.judge:
    default: {model: Qwen3.5-9B, temperature: 0, seed: 0, reasoning: false, packet_cap_tokens: 3000}
    identity: {model: Qwen3.5-9B, temperature: 0, seed: 0, reasoning: false, target: identity_group}
  classify.segments:
    default: {checkpoint: fastino/gliner2.5-base-v1, decoder: auto, on_infeasible: min_violations}
  extract.gliner_schema:
    default: {checkpoint: fastino/gliner2.5-base-v1, threshold: 0.5, math: mask, batch_size: 16}  # S2 chooses math
  extract.gliner_joint:
    default: {checkpoint: fastino/gliner2.5-base-v1, optimizer: beam, beam_size: 32, math: mask}
  normalize.formula:
    default: {backend: lark}                           # S5 chooses
  resolve.concept_link:
    default: {k: 5, vectors: false}                    # thresholds are policy (D6 §7.1), not configuration
  consolidate.entities:
    default: {use_markup_hints: true}
```

The vLLM endpoint and model cache are settings (D9 §3), not configuration: they do not change
results, so they stay out of configuration hashes. Model names and revisions do change results
and are configuration.

**Packet caps** are each method's configuration and have no second home. M24's are characters
(`packet_cap_chars`: 18,000 and 9,000, about 6,000 and 3,000 tokens at a conservative 3
characters per token), because the server has no tokenizer for the agent tier; the packet
assembler splits by them, and the MCP tools only paginate what it produced (D8 §3; P0CL-05,
operator 2026-10-28). The local tier's caps stay in tokens of the served model, counted with its
tokenizer (D4 §4.1, phase 1).
> Status: **Proposed** (2026-10-28)

### 12.2 `slices.yaml`

```yaml
version: 0.1.0
# Selectors. A string is a locator, whose forms D1 §3.4 governs (a bare page selects the whole
# page; pages are relative to the source profile's root, §12.1); it must resolve to exactly one
# segment, else it is refused. {include: <slice>} adds another slice's selections as they are;
# {pages: [<slice>, …]} adds every unit of the pages the named slices' selections lie on;
# {index: <column>} adds the pages the corpus index marks in that column; {golden_set: <label>}
# adds each unit of that dev golden set by its unit locator. Everything resolves when a run starts.
slices:
  trace:
    - 'special/LocationScale.html@p:As usual, our starting point'             # T1 lead-in
    - 'special/LocationScale.html#dfn1'                                        # T1
    - 'special/Normal.html@p:Suppose again that \( X \) has the normal distribution with location parameter'   # T2
    - 'special/Normal.html#rel1'                                               # T3
    - 'special/LogNormal.html#dfn'                                             # T4
  core12:
    - {include: trace}
    - 'special/Normal.html#rel2'                                               # U5
    - 'special/Normal.html@p:Recall that in general, if \(X\) is a random variable with mean'   # U6
    - "special/Normal.html@p:In some settings, it's convenient to consider a constant"          # U7
    - 'special/Normal.html@u:A metal rod is designed'                          # U8
    - 'special/LogNormal.html@u:Suppose that \(n \in \N_+\) and that'          # U9
    - 'special/Gamma.html#dfn4'                                                # U10
    - 'special/Gamma.html#rel2'                                                # U11
    - 'special/Gamma.html#mom1'                                                # U12
  spike-pages:
    - special/LocationScale.html
    - special/Normal.html
    - special/LogNormal.html
    - special/Gamma.html
  phase0-golden:                                                               # scope of the phase 0 first pass (D6 §7.4, §8; D7 §9)
    - {pages: [core12]}                                                        # the trace and core units' pages whole: the four spike pages, 208 units
    - {golden_set: p0}                                                         # every dev golden unit by its unit locator (D7 §3.1)
  first-pass:
    - {index: first_pass}                                                      # pages with first_pass = yes in the corpus index
```

A run is over a slice and may be scoped to another: run option `corpus` names the slice it runs
over (default `first-pass`), and run option `scope` the slice whose units the policies route
(D6 §8). `phase0-golden` is such a scope, not a debug slice: a run over the first-pass corpus names
it, proposes for its units only and records every other eligible unit `skipped` with reason
`scope`, and it can be promoted (D6 §7.4, D7 §7). It is the four spike pages whole (LocationScale,
Normal, LogNormal and Gamma, whose 208 units the `spike-pages` run already works and later runs
reuse) and every unit of the dev golden set `p0` by its unit locator, about 234 packets by
simulation ([phase0-golden size](../design_review/evidence/2026-10-28_phase0-golden-size/README.md)). Other
pages, the forced-dev pages of D7 §3.1 among them, enter only through units of that set, and the
reserved page holds none. Its golden part is resolved from the set when a run starts, so it is
never hand-kept, and the resolved unit list and its hash are recorded in the run's `scope` option (`ops.run.options`, D3 §4), so a later change to the set
cannot change what a finished run covered. It holds no test page (P0CL-09; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28)
