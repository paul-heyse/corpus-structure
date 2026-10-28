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
    rules.yaml           validation rules (rule-engine expressions) and rule views (`views:`), §7.4
    migrations/          schema migration mappings for breaking changes, §8
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
sources/<profile>.yaml          source profiles (D4 M01): how one source's HTML becomes segments;
                                outside every pack, named by the packs that read the source (§12.1)
```

A **schema version** is the content hash over `<name>.yaml`, `rules.yaml` and the imported
`core.yaml`: SHA-256 of the canonical JSON (D1 §10.1) of the parsed files, not of their bytes or
of a SchemaView dump, which carries file paths and varies with the LinkML release
([schema-rules note](../design_review/evidence/2026-10-28_library-schema-rules/README.md) L-07; stable across hash seeds and load paths, probe 2026-10-28). The guideline is versioned separately ([D7 §2](D7-evaluation-goldens-outer-loop.md#2-guidelines)),
because guideline wording changes far more often than the schema.

## 3. The `ci:` annotation vocabulary

**Native LinkML first; annotation values are scalars** (closes OPEN-D2-6, schema-rules note
L-06, probed 2026-10-28). List-valued annotations load in `SchemaView` but fail metamodel
validation in `linkml-lint`, and object-valued ones do not load. So:
`ci:examples` becomes native `examples`; `ci:identity_keys` becomes native `unique_keys`; predicate
groups (`ci:group` and the guideline's predicate groups) become `subsets` with `in_subset`;
`ci:symmetric` becomes native `symmetric` (and `transitive` where it holds); `ci:gliner_label`
defaults from native `title`. `ci:kind` and `ci:object` are derived by the compiler (class
`abstract`/value-class base; slot `range`) and written only to override. The list annotations that
remain (`ci:qualifiers`, `ci:identity_qualifiers`, `ci:target`) are space-separated strings. The
tables below give the meaning; the v0 drafts in §6 and §9 still show the earlier list form and are
replaced by the pack files that S4 and the phase 0 schema package write.
> Status: **Tested** by probe (schema-rules note, 2026-10-28); pack files not yet rewritten

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
| `ci:threshold` | number in (0, 1) | GLiNER2 score threshold for mentions of this class; default from the method configuration ([D4 M06](D4-method-catalog.md#m06-extractgliner_schema)) |
| `ci:parameter_class` | an identity slot name | Entities of this class are parameters of another entity, the one the named identity slot holds; a `family_param` binding names an entity of such a class (D1 §6.1, below). Statistics: `FamilyParameter` with `family` |

### 3.2 On slots (predicates and qualifiers)

| Annotation | Values | Meaning |
|---|---|---|
| `ci:role` | `predicate`, `qualifier`, `identity`, `field` | `predicate`: claims use it. `qualifier`: usable as a qualifier on the predicates that list it. `identity`: an identity attribute of a class. `field`: a field of a value class |
| `ci:object` | `entity`, `formula`, `set`, `text`, `number`, `bool`, `enum`, `date`, `interval`, `phrase`, `map`, `condition` | Object value type (D1 §6); for `entity` the LinkML `range` names the class |
| `ci:qualifiers` | list of qualifier slot names | Schema qualifiers allowed on this predicate (D1 §5.3) |
| `ci:identity_qualifiers` | list | Which of them enter the claim key (D1 §10.1) |
| `ci:extract` | `relation`, `record`, `llm`, `none` | How extraction proposes claims of this predicate: GLiNER2 relation, GLiNER2 record field, LLM only, or not extracted (derived only) |
| `ci:symmetric` | `true` | `identical_parameter`-style predicates; consolidation orders subject and object canonically |
| `ci:functional` | `true` | At most one object per subject and statement: candidates compete in one slot ([D5 §5.4](D5-consolidation-identity-confidence.md#54-slots-core-support-refinements-and-alternatives)), and across statements a second object is a conflict (D5 §5.5) |
| `ci:record`, `ci:anchor` | — | Reserved for GLiNER2 record structures (§7.2). **No v0 predicate uses them**: a record needs fields that one predicate cannot supply, so records are declared only when spike S2 or a measured gap shows a structure earns its place |
| `ci:examples` | list | As on classes |
| `ci:group` | name | Predicate group for acceptance thresholds, confidence priors and reports ([D5 §6](D5-consolidation-identity-confidence.md#6-confidence), D6 §7); default: the predicate itself |
| `ci:param_map` | a qualifier slot name | The predicate's map qualifier whose entries give values to parameters of its object; a `param_of` or `param_expr_of` binding that references a claim of this predicate reads entry `param` of that qualifier (D1 §6.1, below). Statistics: `has_distribution` with `param_values` |

**Binding semantics are pack data** (P0CL-07; operator, 2026-10-28). The core binding kinds
(D1 §6.1) are defined over these annotations, so neither `core` nor `consolidate` names a domain
predicate or class:
- `param_of` (`param_expr_of`) binds a symbol to entry `param` of the map qualifier that the
  referenced claim's predicate names in `ci:param_map`, when the symbol is that entry's value
  (occurs inside it);
- `family_param` binds a symbol to an entity of a class with `ci:parameter_class`;
- the predicates whose claims are about an entity's parameters as such form the pack subset
  **`family_structure`** (native `subsets` with `in_subset`, as the other predicate groups);
  D5 §4's binding rules read the subset, not a list of names. Statistics v0: `has_parameter`,
  `parameter_domain`, `parameter_role`, `derived_parameter`, `identical_parameter`,
  `construction_formula`, `transformation_of`, `special_case_of`.
A second pack with parameterized entities declares the same three things and needs no code.
> Status: **Proposed** (2026-10-28); a toy second pack running the generic stages with no core
> edit is the check (phase 0 consolidation and queries)

### 3.3 On enums and permissible values

| Annotation | Meaning |
|---|---|
| `ci:extract: attribute` with `ci:applies_to: <class>` | Compile to a GLiNER2 span attribute group on mentions of that class |
| `ci:extract: classification` with `ci:target: <segment kind>` | Compile to a GLiNER2 classification task on segments of that kind |
| `ci:z3` (on a permissible value of a condition-predicate enum) | Name of the z3 encoding for this condition predicate, or absent if not encodable |
| `ci:arity` | For condition predicates: `1`, `2`, `2+` |
| `ci:args` | For condition predicates: the class of the arguments |
| `ci:claim_bearing` (on a permissible value of `StatementKind`) | `true` when units of this kind are expected to state claims; policies route proposals by it ([D6 §7.2](D6-orchestration-metrics-policies.md#72-unit-context)). Core defaults: true for every kind except `proof` and `solution` (narrative paragraphs such as T2 state claims) |

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
| `Statement` | entity class, local | D1 §4.3; slot `kind` (enum `StatementKind`), an ordinary attribute: a statement is identified by its anchor segments (D1 §10.1). Label: `<kind> <unit id>`; `<kind> unit <n>` for a unit without an id (n its ordinal among the page's units); else `<kind> ¶<n>` with n the paragraph's ordinal in its section |
| `StatementKind` | enum, `ci:extract: classification`, target `unit` and `paragraph` | Values in D1 §4.3 |
| `Formula`, `SetExpr`, `TextValue`, `NumberValue`, `DateValue`, `IntervalValue`, `PhraseValue` | value classes | Fields as D1 §6 |
| `SymbolBinding` | value class | D1 §6.1 binding kinds |
| `ClaimModality` | enum, `ci:extract: classification`, target `sentence` | D1 §5.2 |
| `defines` | predicate | `Statement` → `Entity` |
| `proves`, `follows_from` | predicates | `Statement` → `Statement` |
| `refers_to` | predicate | `Statement` → `Entity` |
| `unschematized` | predicate | `Entity` → `PhraseValue`; D1 §8.1 status `unsupported` |

**Who owns the value shapes** (schema-rules note L-01; design authority, 2026-10-28). The D1 shapes
that every domain shares, the value union discriminated on `t`, condition nodes discriminated on
`op` (one named recursive `Condition` via `TypeAliasType`), symbol bindings and the batch items,
are hand-written Pydantic models in `core` (frozen, `extra="forbid"`, tuples for lists). They are
domain-independent, so no domain meaning moves into code. The value classes in `core.yaml` are their
**mirror**, restructured with an abstract `Value` base, `t` declared through `equals_string`, and
`conditions` and `param_constraints` ranged on a `Condition` class rather than `string`; a
contract test fails when the two disagree. LinkML owns the domain vocabulary: classes,
predicates, qualifiers, enums and identity. `gen-pydantic` cannot be the source: on LinkML 1.12.1
it rejects the binding shape every batch uses, emits no discriminated unions, defaults missing
tags silently and does not freeze models, and it disagrees with `gen-json-schema` on the same input.
> Status: **Tested** by probe on the 15 v1 model-facing batches (schema-rules note, 2026-10-28)

Draft of `domains/core/schema/core.yaml` v0:

```yaml
id: https://corpus-structure.dev/core
name: core
version: 0.1.0
prefixes:
  linkml: https://w3id.org/linkml/
  ci: https://corpus-structure.dev/ci/
  core: https://corpus-structure.dev/core/
default_prefix: core
imports:
  - linkml:types

classes:
  Entity:
    abstract: true
    description: Base of every entity class; instances are D1 entities.
    slots: [label]
    annotations: {ci:kind: abstract}

  Statement:
    is_a: Entity
    description: >-
      An authored unit of meaning: a definition, theorem, proof, example, exercise, remark,
      convention or assumption. Claims belong to statements as premises, conclusions,
      definientia, restrictions or example values.
    slots: [kind]
    annotations:
      ci:kind: entity
      ci:scope: local
      ci:extract: none          # statements come from segments and markup (D5 §3.5), not mentions
      ci:reify: true

  # value classes (D1 §6)
  Formula:
    description: A formula as written, with its symbol bindings (D1 §6.1).
    attributes:
      latex: {range: string, required: true, annotations: {ci:role: field}}
      sympy: {range: string, annotations: {ci:role: field}}        # added by M11; absent from batches
      parse: {range: ParseStatus, annotations: {ci:role: field}}   # added by M11
      symbols: {range: SymbolBinding, multivalued: true, inlined: true, annotations: {ci:role: field}}
    annotations: {ci:kind: value}
  SetExpr:
    is_a: Formula
    description: A set written in LaTeX, such as \R, (0, \infty) or \R \setminus \{0\}.
    annotations: {ci:kind: value}
  SymbolBinding:
    description: How one symbol of a formula is bound (D1 §6.1).
    attributes:
      symbol: {range: string, identifier: true, annotations: {ci:role: field}}
      bind: {range: BindKind, required: true, annotations: {ci:role: field}}
      entity: {range: string, annotations: {ci:role: field}}   # local ref in batches; entity key once stored
      claim: {range: string, annotations: {ci:role: field}}    # local ref in batches; claim key once stored
      param: {range: string, annotations: {ci:role: field}}    # an entry of the referenced claim's ci:param_map qualifier (§3.2)
    annotations: {ci:kind: value}
  TextValue:
    attributes: {v: {range: string, required: true, annotations: {ci:role: field}}}
    annotations: {ci:kind: value}
  NumberValue:
    attributes:
      v: {range: string, required: true, annotations: {ci:role: field}}      # canonical decimal string (D1 §6.2)
      unit: {range: string, annotations: {ci:role: field}}                   # the unit as stated, or absent
      basis: {range: string, annotations: {ci:role: field}}                  # e.g. gauge or absolute, or absent
    annotations: {ci:kind: value}
  BoolValue:
    attributes: {v: {range: boolean, required: true, annotations: {ci:role: field}}}
    annotations: {ci:kind: value}
  DateValue:
    attributes: {v: {range: string, required: true, annotations: {ci:role: field}}}  # ISO 8601
    annotations: {ci:kind: value}
  IntervalValue:
    attributes:
      start: {range: string, annotations: {ci:role: field}}       # a D1 value as JSON, absent if unbounded
      end: {range: string, annotations: {ci:role: field}}
      start_incl: {range: boolean, annotations: {ci:role: field}}
      end_incl: {range: boolean, annotations: {ci:role: field}}
    annotations: {ci:kind: value}
  PhraseValue:
    description: Text kept but not interpreted; anchored to its span once stored.
    attributes:
      text: {range: string, required: true, annotations: {ci:role: field}}
      start: {range: integer, annotations: {ci:role: field}}
      end: {range: integer, annotations: {ci:role: field}}
    annotations: {ci:kind: value}

slots:
  label:
    range: string
    description: Canonical display label (D1 §4.1). Identity follows the key rules of D1 §10.1.
    annotations: {ci:role: field}
  kind:
    range: StatementKind
    annotations: {ci:role: field}

  # core qualifiers: allowed on every predicate, never listed in ci:qualifiers (D2 §4)
  modality: {range: ClaimModality, annotations: {ci:role: qualifier, ci:object: enum}}
  polarity: {range: Polarity, annotations: {ci:role: qualifier, ci:object: enum}}
  hedge: {range: PhraseValue, annotations: {ci:role: qualifier, ci:object: phrase}}
  attribution: {range: Entity, annotations: {ci:role: qualifier, ci:object: entity}}
  conditions:
    range: string
    description: A condition tree (D1 §7).
    annotations: {ci:role: qualifier, ci:object: condition}
  scope:
    range: ScopeExtent
    description: How far a supposition reaches beyond its statement; the stored form adds the segment.
    annotations: {ci:role: qualifier, ci:object: enum}
  valid_time: {range: IntervalValue, annotations: {ci:role: qualifier, ci:object: interval}}

  # core predicates
  defines:
    domain: Statement
    range: Entity
    description: The statement defines the entity. "is called the location-scale family".
    annotations: {ci:role: predicate, ci:object: entity, ci:extract: llm, ci:group: structure}
  proves:
    domain: Statement
    range: Statement
    description: A proof or solution statement proves (or solves) another statement.
    annotations: {ci:role: predicate, ci:object: entity, ci:extract: llm, ci:group: structure}
  follows_from:
    domain: Statement
    range: Statement
    description: The statement is stated to follow from another ("a corollary of the last result").
    annotations: {ci:role: predicate, ci:object: entity, ci:extract: llm, ci:group: structure}
  refers_to:
    domain: Statement
    range: Entity
    description: The statement explicitly refers to an entity defined elsewhere ("recall the gamma function").
    annotations: {ci:role: predicate, ci:object: entity, ci:extract: llm, ci:group: structure}
  unschematized:
    domain: Entity
    range: PhraseValue
    description: Something the source states that the schema cannot express (D1 §8.1).
    annotations: {ci:role: predicate, ci:object: phrase, ci:extract: llm, ci:group: unsupported}

enums:
  StatementKind:
    annotations: {ci:extract: classification, ci:target: [unit, paragraph]}
    permissible_values:
      definition: {annotations: {ci:claim_bearing: true}}
      theorem: {annotations: {ci:claim_bearing: true}}
      proposition: {annotations: {ci:claim_bearing: true}}
      lemma: {annotations: {ci:claim_bearing: true}}
      corollary: {annotations: {ci:claim_bearing: true}}
      proof: {annotations: {ci:claim_bearing: false}}
      example: {annotations: {ci:claim_bearing: true}}
      exercise: {annotations: {ci:claim_bearing: true}}
      solution: {annotations: {ci:claim_bearing: false}}
      remark: {annotations: {ci:claim_bearing: true}}
      convention: {annotations: {ci:claim_bearing: true}}
      notation: {annotations: {ci:claim_bearing: true}}
      assumption: {annotations: {ci:claim_bearing: true}}
      narrative: {annotations: {ci:claim_bearing: true}}
  ClaimModality:
    annotations: {ci:extract: classification, ci:target: sentence}
    permissible_values: {asserted: {}, supposed: {}, defined: {}, conventional: {}, exemplified: {}, posed: {}, cited: {}}
  Polarity:
    permissible_values: {positive: {}, negative: {}}
  StatementRole:
    permissible_values: {premise: {}, conclusion: {}, definiens: {}, restriction: {}, example_value: {}}
  ScopeExtent:
    permissible_values: {statement: {}, section: {}, document: {}}
  BindKind:
    permissible_values: {variable: {}, param_of: {}, param_expr_of: {}, family_param: {}, free: {}, constant: {}, unresolved: {}}
  ParseStatus:
    permissible_values: {ok: {}, partial: {}, failed: {}}
```

## 7. Compilers

Each compiler is a pure function of a loaded schema version (`linkml_runtime.SchemaView`) and
returns an artifact plus its hash. Output ordering is deterministic (sorted by name) so equal
schemas produce byte-equal artifacts.

**Artifact identity** (P0CL-15; operator, 2026-10-28). An artifact is identified by its schema
version, its compiler and that compiler's version, and its kind (the batch schema in each form,
the annotator reference, the compiled rules and views, the schema tables' content): one
`meta.compiled_artifact` row each (D3 §3), never a field of the schema version that a compiler fix
would rewrite under runs that used the old output. A compiler fix therefore adds rows beside the
old ones. Method configurations reference artifact hashes, so work done with the old artifact
keeps its provenance and is not reused for the new one (D6 §4). Artifacts are deterministic, so
any one can be rebuilt from its schema version and compiler and checked against its stored hash;
compiled rules are rebuilt this way, never pickled (§7.4).
> Status: **Proposed** (2026-10-28)

### 7.1 To schema tables

Writes `meta.schema_class`, `meta.schema_slot`, `meta.schema_enum` and `meta.schema_rule` rows
([D3 §3](D3-database.md#3-meta-schema-guidelines-and-domain-declarations)) with induced slots
(inheritance and mixins resolved through `SchemaView.class_induced_slots`). Predicates are free slots
with a `domain`, which `class_induced_slots` omits, so applicability per class is
`domain ∈ class_ancestors(cls)` followed by `induced_slot(p, cls)`; prefixed names come from
`get_uri(…, expand=False)` (schema-rules note L-08). These rows let SQL
join claims to their schema definitions and let metrics group by class and predicate.

### 7.2 To GLiNER2 schemas

Compiled from phase 1, when M05–M07 run; phase 0 compiles nothing for GLiNER2, so the product
environment carries no gliner2 or torch until then.

Two artifacts, because GLiNER2's ordinary and joint decoders have different semantics
([library overview](../libraries/gliner2.md) §4.3):

**(a) The extraction schema**, built with `Schema.from_dict` (package 2.1.0 supports parity with
the builder: descriptions, thresholds, examples, attributes):

| GLiNER2 element | Compiled from |
|---|---|
| Entity types with descriptions | Classes with `ci:kind: entity` and `ci:extract: mention`; label = `ci:gliner_label`; description = LinkML `description` plus `ci:examples` |
| Span attribute groups | Enums with `ci:extract: attribute`; `applies_to` = `ci:applies_to`; `qualify_labels=True` |
| Classification tasks | Enums with `ci:extract: classification` (run on segments of the target kind by M05) |
| Structures (record mode) | None in v0 (§3.2). The fragment below shows the form a hand-written structure takes in spike S2 |
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
ClaimProposalBatch                   model-facing form; "stored:" notes where the stored form differs
  unit_ref            string         the packet's unit key
  entities[]          { local_ref, type ∈ enum(entity classes), label, scope ∈ {global, local},
                        extent?: statement | section        local entities only (D1 §4.2)
                        symbol?, aliases[], identity{ slot: value } }
                                     stored: adds scope_segment (segment key) for local entities
  statements[]        { local_ref, kind ∈ enum(StatementKind), anchor: "unit" | [sentence ids] }
                                     stored: anchor = [segment keys]
  claims[]            oneOf per predicate:
                        { local_ref, predicate: const <p>, subject: local_ref,
                          object: { ref: local_ref } | <value of p>,
                          qualifiers: { core qualifiers, schema qualifiers of p },
                          statement?: local_ref, statement_role?,
                          evidence[]: { sentence, quote, role } }   sentence: sN of the unit or cN of its standing context
                                     stored: evidence[] = { start, end, role, coarse? }
  alternatives[]      { refs: [claim local_refs] (2 or more), reason }
  unsupported[]       { local_ref, sentence, quote, reason }
                                     stored: start, end instead of sentence, quote
```

- **Local refs** are unique within a batch and are the only way items refer to each other:
  `subject`, `object.ref`, `statement`, condition nodes `{"op": "claim", "ref": …}`, and symbol
  bindings (`variable` and `family_param` name an entity local ref in `entity`; `param_of` and
  `param_expr_of` name a claim local ref in `claim`, plus `param`). Consolidation replaces local
  refs with keys ([D5 §5.2](D5-consolidation-identity-confidence.md#52-normalization-and-keys)).
- **Values.** Formula and set values carry `t`, `latex` and `symbols` (the binding map, D1 §6.1);
  `sympy` and `parse` are added by M11 during consolidation and appear in neither batch form.
- **Global entities** are identified across units by `label` and `identity`; packets list the
  canonical labels already known for the page (D4 §4.1) so proposals reuse them.
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

Per-predicate branches restrict the subject and object types (via an `entity_types` side table
resolved at validation, because JSON Schema cannot follow local references), the value type, and
the allowed schema qualifiers. Enum values are inlined. Descriptions are carried into the schema
so the model sees them. Prompts carry the annotator reference (§7.5), filtered per statement kind
for the local tier (D4 §4.2); there is no separate prompt inventory.

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
orphaning it; golden items are this derivation for goldens (D7 §3.1).
> Status: **Proposed** (2026-10-28)

**How the schema is built** (schema-rules note L-02, L-03). The compiler builds one claim model per
predicate with `pydantic.create_model` from `SchemaView` (subject and object types, value type,
allowed qualifiers), unions them discriminated on `predicate`, and wraps them in the batch envelope
over the `core` shapes. One `TypeAdapter` per form both validates submissions (exact error paths,
about 0.02 ms per batch) and exports the draft 2020-12 JSON Schema in validation mode, through a
custom `GenerateJsonSchema` (no titles, `$schema` set, deterministic output; byte-identical across
processes in the probe). `gen-json-schema` is not used: it emits draft 2019-09, has no `t`, and
drops predicate and qualifier slots.

The **decoding form** given to structured output follows rules the backends need: `oneOf`/`anyOf`
only where branches are disjoint by a `const` (the predicate); never `if`/`then`/`not`, which
xgrammar ignores; no `allOf` with more than one branch, which xgrammar mishandles (newer vLLM rejects
such schemas itself); the `discriminator` keyword stripped; nesting at most 64 levels (ours nest 9–11);
one canonical shape per position (one entity-reference shape, one formula shape). Descriptions are
optional in the decoding schema: constrained decoding does not show them to the model, and the
annotator reference in the prompt is what it reads. Which xgrammar the vLLM in use bundles, and its
grammar compile cost for a 49–73 KB schema, are measured in S3.
> Status: **Tested** by probe for the model-facing form (25 branches, 15 batches, seeded errors;
> schema-rules note, 2026-10-28); the stored form and the decoding form against vLLM not yet built

### 7.4 To rule-engine rules

`rules.yaml` holds named rules and the rule views they read:

```yaml
views:                         # pool facts as claim-view attributes, compiled for the generic view builder
  family_params:               # claim.family_params: a list of strings
    applies_to: stat:has_distribution
    source: stat:has_parameter                 # the source predicate
    match: {source: subject, claim: object}    # source claims whose subject is this claim's object (the family)
    project: object.identity.canonical_name    # what each matching source claim contributes
rules:
  - id: stat.param_keys_known
    applies_to: stat:has_distribution
    severity: warning          # warning | error
    description: Every param_values key is a parameter the family has.
    at: [finalize]             # call sites (D5 §8.2): a family's parameters are complete only at finalize
    when: "claim.predicate == 'stat:has_distribution'"
    check: "$all([k in claim.family_params for k in (claim.qualifiers.param_values ?? {}).keys])"
tables:                        # lookup tables compiled to typed builtins
  roles_by_kind: {theorem: [conclusion, premise], definition: [definition]}
```

The compiler parses each `when` and `check` with `rule_engine.Rule` under a typed `Context`
whose type resolver declares the claim context symbols ([D5 §8.2](D5-consolidation-identity-confidence.md#82-rule-context))
generated from the schema version. A rule that fails to type-check fails compilation, so a broken
rule never reaches a run. Severity `error` makes a failing claim `rejected`; `warning` records a
validation observation and lowers confidence (D5 §6).

**Rule-engine use** (closes OPEN-D2-3; schema-rules note L-04, L-05, probed with rule-engine 5.1.0):
- Structured symbols are typed `OBJECT`s read through a `getattr` resolver; mapping dot-access is
  off (`mapping_attribute_lookup=False`, deprecated in 5.x and removed in 6.0) and the timezone is
  UTC. A typo, a nullable misuse, a wrong argument type or an unknown symbol fails at compile time.
- Nullable access uses `&.` and `??`; quantifiers are `$all(...)`/`$any(...)`; calls take positional
  arguments only.
- Facts about the claim pool are cached attributes of the claim view, computed once per claim by
  one generic view builder, because the language has no recursion or joins; functions are kept
  for parameterized lookups. Generic facts are built in: flattened condition nodes, statement
  premises, and "given as a parameter value elsewhere" (read through `ci:param_map`, §3.2).
  Domain facts are declared by the pack in `views:` (source predicate, match, projected field) and
  compiled with the rules, so `family_params` is statistics data, not builder code (P0CL-07;
  operator, 2026-10-28). The builder and the M19 runner live in `validate` and work over the `core`
  keyed candidate claim, which a batch and the candidate pool both adapt into
  ([D9 §1](D9-repository-and-phase0.md#1-layout)).
  > Status: **Proposed** (2026-10-28); the `views:` form is checked on the pack's own rules in S4
- Every rule declares `at:`, the call sites it runs at: `batch` (submission, local refs) and/or
  `finalize` (keys). One compiled rule serves both because the view exposes `claim.id` (local ref,
  later key) and a nullable `claim.key` (D5 §8.2).
- **Readers per call site** (P0CL-14; operator, 2026-10-28). At `batch` the view reads formula
  symbols with `core/tex.py`'s TeX tokenizer, which is total and fast, never with the math grammar:
  submission runs in MCP worker threads, where the grammar's `setitimer` timeout cannot fire
  ([D4 M11](D4-method-catalog.md#m11-normalizeformula)). A rule that needs the grammar (parse
  status, slot types) declares `at: [finalize]`, as `stat.domain_is_set` does, so no grammar parse
  runs in an MCP worker thread.
  > Status: **Proposed** (2026-10-28); a test submits a pathological formula
- Each rule is compiled in its own context, and the nondeterministic builtins `$now`, `$today` and
  `$random` are rejected, so a rule's outcome depends only on its inputs (D6 §4 reuse). Compiled
  rules are rebuilt from the schema version, never pickled.
> Status: **Tested** by probe (all 11 guideline checks of `code/s0r2_rules.py` compiled as rules: 0
> warnings on the 15 v1 batches, 11 of 11 seeded violations caught; schema-rules note, 2026-10-28)

**Guideline rules as batch warnings.** The guideline rules that code can check are compiled as a
`guideline:` group of `warning` rules applied to model-facing batches when they are written (golden
passes through `write_golden`, LLM and agent proposals), so the author sees them and fixes the batch
or says why the rule does not apply:
- statement role by statement kind;
- modality by role;
- which claims may carry a condition tree, and what it may hold;
- a formula excludes the variable it defines (its symbols read by the TeX tokenizer, above);
- symbol-map keys without backslash;
- binding priority;
- `parameter_role` only when it differs from the canonical name.

Rules the code cannot see (which premises a claim depends on, restrictions repeated in each
dependent claim) stay the author's. The validator's invariant INV-06 and the guideline agree: a
premise that no condition references carries `scope: statement`.
> Status: **Tested** in the spike instruments (S0-R2, 2026-10-28: `code/s0r2_rules.py`; the v1
> reference, the worked examples and both v1 passes end with no warnings)

`rules.yaml` also has a `derive:` section: named derivation rules (for statistics, variance to
standard deviation, transitivity of `special_case_of`, applying a construction's parameter
mapping). Each names its source predicates, a match condition and a template for the derived
claim; M23 applies them ([D4 M23](D4-method-catalog.md#m23-deriveclaims)). Derivations that need
algebra call registered SymPy helpers, never inline code.

### 7.5 To the annotator reference

The compiler generates the **annotator reference** (§10.10) on every schema version, so what
golden passes, the agent and the LLM tiers write from cannot drift from the schema. Its parts:

- **Entity types:** each with its description, scope, identity slots and examples.
- **Predicates:** a card per predicate, grouped as structural, formula and family-structure, and
  other. Each card gives the subject and object types, the description, the predicate's own
  qualifiers, and the predicate's statement role, modality and condition rule from guideline §10.3,
  §10.6 and §10.7.
- **Qualifiers and enums.**
- **Shapes:** the exact JSON shape of every value, binding and condition node.
- **Worked examples:** complete packets with their batches, from pages outside every golden split
  (D7 §4).

It replaces giving annotators the LinkML schema verbatim with a model excerpt beside it. The raw
schema stays available as background.
> Decision: [ADR-0011](../adr/0011-golden-author-and-annotator-inputs.md)
> Status: **Tested** in the spike (S0-R2, 2026-10-28: `code/s0r2_inputs.py`; the v1 passes did not open
> the raw schema); production generator not built

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
    description: >-
      One entry of a param_mapping map. key is the target family's parameter canonical name; value
      is the canonical name of the base family's parameter it corresponds to.
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
      ci:functional: true
      ci:group: distribution
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
    range: string
    description: A condition tree (D1 §7) over the base family's parameters (k = 1).
    annotations: {ci:role: qualifier, ci:object: condition}
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
    annotations: {ci:role: qualifier, ci:object: phrase}
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
| `stat.param_keys_known` | `has_distribution` | warning | Every `param_values` key is a canonical name of a parameter the family has in this run, or a `ParameterRole` value; reads the `family_params` view (§7.4), `at: [finalize]` |
| `stat.supposed_is_used` | any `supposed` claim | warning | INV-06: referenced by a condition or has a `scope` |
| `stat.one_distribution_per_statement` | `has_distribution` | error | At most one asserted or defined `stated` `has_distribution` per variable per statement; derived claims are exempt |
| `stat.domain_is_set` | `parameter_domain`, `takes_values_in`, `support` | warning | Object parses as a set (`parse = ok`); otherwise a warning, and the object is kept as written. `at: [finalize]`, because it reads the grammar's parse status (§7.4) |
| `stat.variance_nonnegative` | `has_distribution` with a `variance` key | warning | Checked by M20 with z3, not by rule-engine: the conditions imply variance ≥ 0 when the formula parses |
| `stat.no_family_on_variable` | `has_parameter` | error | Subject is not a `RandomVariable` |

## 10. Guideline v1 (statistics)

This is the starting content of `domains/statistics/guideline.md`. Golden passes, written by
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

The annotator reference is generated from the schema: every predicate with its subject and object types,
description, the qualifiers it takes and its role and modality under §10.3 and §10.6, the binding
kinds, the value shapes, and complete worked examples.

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
| OPEN-D2-1 | Exact `Schema.from_dict` keys for structures, attributes and per-type thresholds in gliner2 2.1.0 | Spike S4 |
| OPEN-D2-2 | Raw LaTeX or masked math placeholders in GLiNER2 input | Spike S2 |
| OPEN-D2-3 | rule-engine syntax for the `rules.yaml` checks, and whether custom functions such as `family_params` are better as resolver-backed symbols | **Answered** (2026-10-28, [schema-rules note](../design_review/evidence/2026-10-28_library-schema-rules/README.md) L-04, L-05): cached view attributes, `at:` per rule, §7.4; domain view attributes are declared in `views:` (P0CL-07); S4 confirms on the pack's own rules |
| OPEN-D2-4 | Whether property predicates (`mean_value`, `pdf`, …) should be one `has_property` predicate with a `property` qualifier instead | Spike S0 annotations: count how many distinct properties appear; **answered by S0** (2026-10-28): keep separate property predicates (only `mean_value` and `variance_value` were needed); add a standard-deviation property, now OPEN-D2-17 |
| OPEN-D2-5 | Whether "standard normal" is better a family with `special_case_of` or a parameterization of the normal family | Spike S0 and outer-loop direction; **answered by S0** (2026-10-28): standardized families as families of their own worked in every pass; `special_case_of` only when the source states the constraint; guideline v1 §10.4 |
| OPEN-D2-6 | Whether LinkML annotation values that are lists (`ci:examples`, `ci:qualifiers`) round-trip through `SchemaView` unchanged | **Answered** (2026-10-28, schema-rules note L-06): they load but fail `linkml-lint`; native slots and scalar strings, §3 |
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
| OPEN-D2-10 | Documented shapes for `param_mapping`, `param_symbols` and `param_constraints` (SG-11), so the generated reference can state them | Schema description update |


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
(`configs: ingest.html`), and only the resolved profile enters `ingest.html`'s configuration hash,
so adding a profile changes no other configuration. The profile also declares the claims its
containment structure states (`synthesize:`), which consolidation applies (D5 §3.5), so that
convention is source data rather than consolidation code (P0CL-07; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28) for the location and `synthesize:`; the profile's values are
> **Tested** (S1, below)

`sources/siegrist.yaml`:

```yaml
version: 0.1.0
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
# S1 merged (2026-10-28): every value above except `synthesize:` Tested on 78 pages (record s1.corpus); vocabulary in D4 M01
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
    default: {source_profile: siegrist}                # sources/siegrist.yaml, resolved by name
  segment.sentences:
    default: {model: en_core_web_sm, variant: merged}  # b′: inline math merged into one token (S1, OPEN-D1-1)
  agent.opus:                                          # caps in characters: the one cap authority for agent packets (D8 §3)
    extract: {mode: extract, examples: reference, hints: none, packet_cap_chars: 18000}  # phase 0: the reference's worked examples; dev-golden retrieval needs M04 (phase 1)
    adjudicate: {mode: adjudicate, packet_cap_chars: 9000, max_alternatives: 6}
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
# Locators (D1 §3.4): page | page#unit-id | page@u:<text prefix> (a unit) | page@p:<text prefix>
# (a paragraph outside units), with an ordinal page@u[n]:… where prefixes coincide. Pages are
# relative to siegrist_random/random/. Prefixes match the start of the segment's canonical text
# with whitespace collapsed; each locator must resolve to exactly one segment, else it is refused.
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
  phase0-golden:                                                               # scope of the phase 0 first pass (D6 §7.4, §8)
    - {include: spike-pages}                                                   # the pages of trace and core12, forced dev
    - special/Pareto.html                                                      # forced dev: S0-R2 held-out pages (D7 §3.1)
    - special/ChiSquare.html
    # + the pages holding dev golden units: declared by name here, filled by `ci golden create` from the dev set (D7 §3.1)
  first-pass:
    - {index: first_pass}                                                      # pages with first_pass = yes in the corpus index
```

`phase0-golden` is a run scope, not a debug slice: a run over the first-pass corpus names it
(run option `scope`, D6 §8), proposes for its units only and records every other eligible unit
`skipped` with reason `scope`, and it can be promoted (D6 §7.4, D7 §7). Its golden-unit pages are
resolved from the dev golden set, so they are not hand-kept: `ci golden create` fills them when it
samples the set. It holds no test page (P0CL-09; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28)
