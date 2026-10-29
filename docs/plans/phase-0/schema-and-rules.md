# Phase 0 · Schema and rules

**Status:** Proposed; nothing is built. Part of the [phase 0 series](../phase-0_2026-10-28.md), which
owns shared decisions, contracts, the dependency graph and build findings (§11). Its packages are
P0-S-1, P0-S-1b and P0-S-2.

**What has reported.** S4 (schema compilers; records `s4.*`,
[S4 plan](../design-spikes-s0-s1/S4-linkml-compilation.md)) and S6 (storage) have reported. Their
results were folded in at X2, which the operator accepted on 2026-10-28. ADR-0016–0018 were accepted
then.

**Revised** on 2026-10-28 by the
[domain-model alignment review](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md)
and its [target model](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28_target-model.md)
("TM"), decision Revise, with the rule changes decided in coordinator §9.2.
- **Decisions superseded at P0-D-1.** ADR-0020 supersedes ADR-0017, keeping "the pack owns domain
  vocabulary". ADR-0021 supersedes ADR-0016.
- **What moved.** The model (`core.yaml` and the new `system.yaml`), its generated vocabularies and
  the interim mirror guard moved to [model and projections](model-and-projections.md) ("M").
- **What this document gains.** It gains the pack half of declared identity, the pack name map, the
  rule-view naming rule, literal checks and sole ownership of batch reference checks.

## 1. What this document builds

This document builds the code that turns a domain pack into the artifacts its consumers read. It
also builds the code that checks authored batches against the pack and runs the pack's rules at
both call sites:

- **`schema/`** loads a pack over the model and computes the schema version.
  - **Loading.** It reads `domains/<name>/schema/`, the model's `core` module through M1's model
    loader, the core rules and the worked examples in `reference/`.
  - **The lookup.** A typed lookup exposes the pack's vocabulary and compiles the pack half of
    `KeySchema`.
  - **The compilers.** The phase 0 compilers produce:
    - the schema-table content;
    - the batch models and JSON Schema in the model-facing, stored and decoding forms;
    - the annotator reference;
    - the compiled rules.
  - **Also here.** Compiled-artifact identity and registration in `meta` (including the model
    revision and the payload schemas), the pack name map, the rule-language helper that
    orchestration's policies reuse, and `ci schema compile`
    ([D2 §2](../../design/D2-schema-and-guidelines.md#2-domain-pack-layout),
    [§7](../../design/D2-schema-and-guidelines.md#7-compilers);
    [D3 §3](../../design/D3-database.md#3-meta-schema-guidelines-and-domain-declarations)).
- **`validate/`** holds four things:
  - the batch conformance, reference and type checks: D4 §4.3 steps 1 and 3, and the D1 invariants
    a batch can violate. It is the sole owner of reference checks for batches (RC19);
  - the T2 translation, stored batch → keyed candidate set;
  - the T4 translation, candidate → rule view. One rule-view builder serves both call sites over the
    `core` keyed candidate set;
  - the M19 runner and method definition, beside the view builder
    ([D2 §7.4](../../design/D2-schema-and-guidelines.md#74-to-rule-engine-rules),
    [D5 §8](../../design/D5-consolidation-identity-confidence.md#8-validation),
    [D4 M19](../../design/D4-method-catalog.md#m19-validaterules)).
- **Pack files**, ported from S4's native-form files:
  - `domains/statistics/schema/statistics.yaml` and its `rules.yaml`;
  - the core rules `domains/core/schema/rules.yaml` (D2 §2);
  - `.linkmllint.yaml`;
  - `domains/statistics/guideline.md`, ported from D2 §10: guideline v1 with the §10.4
    parameter-naming rule the v1 reference follows, not the S0-R2 file, which predates that rule;
  - the worked examples `domains/statistics/reference/E1`–`E3`;
  - a minimal compile-test pack in `fixtures/packs/minimal/`.

  The model's `core.yaml` is no longer a pack file. It is promoted to
  `python/corpus-structure/src/corpus_structure/model/core.yaml` by M1 (coordinator decision 1).

**Where it ends.**
- **The model** (`core`, `system`), the model revision and its log, the generated `core/_model/` and
  `core/vocab.py`, Stage A and Stage B, the interim mirror guard, Arrow schemas, the `$id`
  convention, the payload-schema registry content and the change classifier are model and
  projections'. This document consumes them.
- **The `KeySchema` type**, canonical forms by range and the key functions are foundations' (F2d).
  This document compiles the pack half of the facts they read.
- **The quote cascade** is agent interface's A0, which is schema-free. It owns T1's cascade; T1's
  names and checks are `validate`'s (TM §7).
- **Packets, prompts, the MCP tools** and the sequencing of a submission belong to A1 and A2.
- **Writing.** Writing observations belongs to foundations' repository. Consolidation writes M19's
  `verification` observations, and orchestration records the M19 task.
- **Pack data owned elsewhere.** Guideline versions are written by orchestration's pack-version
  upsert. Policy chains are orchestration's (O2), built with this document's rule-language helper.
- **The math grammar** is ingest and math's. At finalize its results reach the view builder as data
  from consolidation, and `validate` never imports `methods/math`.
- **The pool's T3 translation** (pool → candidate) is pool and interchange's, and its loader is P1.
- **The toy second pack** is consolidation's P0-C-4.
- **Not in phase 0.**
  - The GLiNER2 compiler (D2 §7.2), the reference filtered by statement kind (S4 variant V4) and the
    local tier's decoding-form consumer (M10) wait for phase 1.
  - So do `ci schema diff` and the `propose_schema_change` compile path. Schema v0 is frozen
    (coordinator §3 decision 9), and no second version exists.
  - Schema migrations by pack change record (D2 §8, M4's classes) and the compilation of `derive:`
    rules (M23) wait for phase 2. The loader reads `derive:`, and the tables project it.

**Change scenarios that explain the boundaries** (from [DESIGN §1.3](../../design/DESIGN.md), the
phase 1 additions and the review's §5; none is built here beyond what phase 0 needs):

| Change | Where it is expressed | What is reused | What stays unaffected |
|---|---|---|---|
| A second domain pack | New pack files: classes and predicates, `ci:param_map`, `ci:parameter_class`, `ci:key_role`, `ci:case`, pack `StatementKind` members, the `family_structure` subset, `views:`, rules, worked examples | Loader, lookup, every compiler, the view builder, the conformance checks, the runner | Every module of `schema/` and `validate/`; the minimal pack and consolidation's toy pack (P0-C-4) check this |
| Two packs in one project | One schema version compiled from both (coordinator decision 25) | The name map and the rule-view naming rule, each with its compile-time uniqueness or collision check | Rules written against local names stay valid while those names are unique |
| A business identifier slot (`ORG-101`) or a business modality under which attribution identifies | `ci:case preserve` on the slot; a modality member with the `attribution_identifying` property | The compiled `KeySchema` pack half | `core/keys.py` (F2d reads the declaration) |
| A rule with `or`/`not` conditions | `rules.yaml` text | The flattened condition-node attribute, the typed context | The compilers: condition trees are core shapes (D1 §7) |
| A claim with `valid_time` and attribution | Core qualifiers in the model, already admitted on every branch | The per-predicate builder's core-qualifier set, read from M1's `QualifierSpec`s | Keys are foundations' (D1 §10.1, F2d) |
| A table segment with quantities and units | A predicate whose `ci:object` is `number`; the `NumberValue` shape (D1 §6) | The branch builder takes admissible values from the core union | Unit checks wait for M12 (phase 1) |
| The GLiNER2 tier (phase 1) | A new compiler with its own artifact kinds | Artifact identity, registration, method configurations referencing artifacts by (compiler, kind) | The existing artifacts and their rows |
| A compiler or library fix | A new compiler version string | Registration adds rows beside the old ones (§3.4) | Runs that used the old artifacts keep them |
| A model revision (a code release that changes `core` or `system`) | M1's revision log | The schema-version hash covers the model revision id, so each pack's version moves with it | The pack files |

## 2. Contracts

### 2.1 Consumed (cited, never redefined)

| Contract | Owner | Needed by |
|---|---|---|
| Canonical JSON and its hashing ([D1 §10.1](../../design/D1-knowledge-representation.md#101-hashing)), including its float rule | foundations, F2a | S1 (version and artifact hashes) |
| `core/tex.py`: TeX tokenizer, drop list, token form (coordinator §3 decision 13) | foundations, F2a | S2 (batch-site view) |
| The model and its loader: `core` and `system` modules, `SchemaView` over them with the pack, the declaration check, the model revision id | model and projections, P0-M-1 | S1 (loader, version hash), S1b (registers the revision) |
| The generated `core/_model/`: closed sets with member properties (including the static and version-scoped lifecycles), core `QualifierSpec`s, the core local ↔ prefixed name tables, and the generated `core/vocab.py` | P0-M-1 | S1 (KeySchema core half, name map), S2 (literal checks, typed policy symbols) |
| The JSON Schema `$id` convention per model revision and the `referencing.Registry` builder | P0-M-3 | S1 (batch-form schemas) |
| The payload-schema registry content (JSON Schema id, Arrow schema bytes, `sql_visible` paths, upcaster per payload class), reader dispatch and the change-record model | P0-M-4 | S1b (registers payload schemas; `meta.schema_version.migration`) |
| The generated `MetaData` for `meta.schema_version`, `meta.model_revision`, `meta.payload_schema`, `meta.compiled_artifact`, the `meta.schema_*` tables and the per-version member tables with composite FKs; the repository | P0-M-2; foundations, F4 | S1b |
| D1 value, condition and binding shapes. Batch items in both forms, including the generic stored-item models, the `outside` item and `EnumValue` per form. The citation-frame model. The keyed candidate set as a complete translation target, with typed references, `ExternalReference` nodes and typed unkeyed states ([D2 §6](../../design/D2-schema-and-guidelines.md#6-the-core-schema), D9 §1) | foundations, F2b and F2e | S1 (per-predicate models), S2 (T2, T4, checks) |
| The `KeySchema` type and its `QualifierSpec` fields (key role, role condition, canonical form by range, case policy); the typed `DropReason` codes | foundations, F2d, F2c | S1 (compiles the pack half), S2 (kind-refusal codes) |
| Method-contract types and the registry interface (`core/method.py`, [D4 §1](../../design/D4-method-catalog.md#1-the-method-contract)). Method configurations declare artifact references by (compiler, kind), and the registry resolves them against the run's schema version | orchestration, O0 and O1 | S2 (M19's method definition) |
| The modelled operational vocabularies and typed policy symbols (RC14) | coordinator P0-D-2; M1 | S2 (literal checks in the rule-language helper) |
| `fixtures/s0` authored batches with their frames: the files, not F3's acceptance | foundations, F3 | S1, S2 tests |
| Shared conftest, test database and the thin-fixture convention (coordinator §3 decision 10) | foundations, F1 | every package's tests |

### 2.2 Produced

| Contract | Design owner | What this document implements | Consumers |
|---|---|---|---|
| Pack loading and the schema version | D2 §2, §3; RC09 | Loader over M1's model loader, the pack declarations, and the version hash over the pack schema, the pack's `rules.yaml`, the core rules, `reference/` and the model revision id (§3.1) | orchestration O1 (upsert; the run records the version), every artifact consumer |
| The typed schema lookup | D2 §3, §7.1 | A frozen lookup materialized from `SchemaView` (§3.2) | consolidation C1, evaluation E2a and E2b, agent interface A1 |
| The compiled `KeySchema` (pack half, joined with the core half) | ADR-0023 (P0-D-1); TM §8 | Identity keys per class, `entity_identity`, symmetric predicates, prefixed names, and pack `QualifierSpec`s compiled from `ci:key_role` (or `ci:identity_qualifiers`) and `ci:case` (§3.2) | foundations F2d's keys; C1 (slots, conflicts); the rule view |
| The pack name map (X2-01) | D2 §7.1; R04 | Local ↔ prefixed names of the pack's elements from `get_uri(expand=False)`, with a compile-time uniqueness check across the packs of a version (§3.2) | T1 (A0's renaming, `validate`'s checks), the stored form, the compiled rows |
| Compiled artifacts and their identity | D2 §7, D3 §3 | One record per (schema version, compiler, compiler version, kind); registration in `meta` (§3.3, §3.4) | method configurations in O1, A1, A2, C1; reuse ([D6 §4](../../design/D6-orchestration-metrics-policies.md#4-caching-and-reuse)) |
| Batch models and JSON Schema in the model-facing, stored and decoding forms | [D2 §7.3](../../design/D2-schema-and-guidelines.md#73-to-json-schema-for-llm-claim-proposals) | Per-predicate models, one adapter per form, export with `$id`, the decoding transform (T6) (§3.3) | A1 (`read_instructions`, `propose_claims`), A2 (`write_golden`), C1 (per-predicate qualifier validation, D3 §6.1), phase 1 M10 |
| The annotator reference | [D2 §7.5](../../design/D2-schema-and-guidelines.md#75-to-the-annotator-reference), §10.10 | Generator over the lookup, `tables:`, subsets and worked examples (§3.3) | A1 (prompt part), A2 (`read_golden_unit`); evaluation E1 reads the examples' pages as reserved ([D7 §3.1](../../design/D7-evaluation-goldens-outer-loop.md#31-units-and-sets)) |
| Registration of the model revision, the schema version, the per-version members and the payload schemas | D3 §3; ADR-0022 (P0-D-1) | `schema.registry.ensure()` (§3.4) | O1 (the run records the ids), every payload writer (the `payload_schema_id` rows exist) |
| Batch conformance, reference and type checks | [D4 §4.3](../../design/D4-method-catalog.md#43-output-form-and-post-processing) steps 1 and 3; [D1 §11](../../design/D1-knowledge-representation.md#11-invariants); D1 §10.3 as RC19 amends it | `validate.check_batch` for both forms; sole owner for batches (§3.7) | A1, A2, C1 |
| Compiled rules, the views (T4), the batch → candidate adapter (T2), M19 | D2 §7.4, D5 §8.1, §8.2, D4 M19 | Rules compiler with literal checks, the rule-view identifier rule, views at both sites, the runner, the `validate.rules` method (§3.5–§3.8) | A1 and A2 (batch site), C1 (finalize site), E2b (rule-warning reading, D7 §7), P2 (the `views:` facts it reimplements) |
| The finalize-readings input type: per value, parse status, kind and symbols (D5 §8.2 as amended) | D5 §8.2 | The `readings` argument of `build_views` (§3.6) | C1, which supplies its values, computed once per pass on the main thread with ingest and math's grammar |
| The rule-language helper | D2 §7.4, [D6 §7.1](../../design/D6-orchestration-metrics-policies.md#71-language); ADR-0018 | Typed contexts with UTC, a context per rule, banned builtins, literal checks against vocabularies (§3.5) | orchestration O2 (policy `Chain`s, typed policy symbols) |
| `ci schema compile` | [D8 §4](../../design/D8-agent-and-query-interfaces.md#4-cli) | Compile from disk; print or write artifacts and hashes | the operator |

## 3. Design of the parts

### 3.1 Pack and loader

`schema.load_pack(path, model)` reads the pack through `SchemaView` in the D2 §2 layout, over the
model that M1's model loader provides.
- **How the import resolves.** The pack imports the model's `core` module, and M1's loader resolves
  that import to the packaged file. Whether it uses an `importmap` or a materialized layout is M1's
  choice.
- **The pack's own imports** resolve relative to the importing file (Tested by probe, schema-rules
  note P1, 2026-10-28).
- **The declaration check.** M1's check (every project annotation has a named consumer, TM §4) runs
  over the pack too.

The loader then checks the pack's `ci:` vocabulary against D2 §3 and TM §4:
- only declared annotation keys, with scalar values;
- the space-separated lists (`ci:qualifiers`, `ci:identity_qualifiers`, `ci:target`) are parsed,
  and each name is checked against a declared slot;
- `ci:kind` and `ci:object` are derived from `abstract`, value-class ancestry and `range`; a written
  value counts only as a checked override;
- `ci:param_map` names a map qualifier that its predicate lists;
- `ci:parameter_class` names an identity slot;
- no core qualifier appears in `ci:qualifiers`.

The pack declarations of the alignment review (TM §4; coordinator decisions 17, 20) are:
- **`ci:key_role: identity | meaning | inert`** on a schema qualifier slot, with an optional
  **`ci:key_role_when: <member property>`**. A predicate's `ci:identity_qualifiers` list is still
  read: it compiles into the same specification, as `identity` for each listed qualifier and `meaning`
  for the predicate's other listed qualifiers unless a slot declares otherwise. A slot whose role
  contradicts the list is a `PackError`.
- **`ci:case: fold | preserve`** on a string-ranged slot or on a class (for its label). The default
  is `fold`.
- **Pack `StatementKind` members.** `StatementKind` is a version-scoped set (`ci:lifecycle:
  schema_version`). A pack adds members with their member properties (`claim_bearing`), and the
  compiled version's `StatementKind` is the union of the core members and every pack's. A pack member
  that collides with a core member is refused.
- **Pack members of other version-scoped sets**, such as a modality with `attribution_identifying`.
  These are read the same way, but only where the model declares the set version-scoped. A static
  set refuses pack members.

`rules.yaml` is read into a typed file model with the sections `rules:`, `guideline:`, `tables:`,
`views:` and `derive:`.
- **Structure only.** The loader checks structure; S2 compiles the expressions. It refuses unknown
  top-level keys.
- **`derive:`.** Its entries are read and projected into `meta.schema_rule` with group `derive`
  (D3 §3), but nothing compiles them until M23 lands in phase 2.
- **Errors.** Failures raise one `PackError` that lists every problem with its file and element,
  never only the first.

**Schema version** (D2 §2 as amended by RC09). The hash is SHA-256 over the canonical JSON of:
- the parsed pack schema;
- the pack's `rules.yaml`;
- the core rules;
- the worked examples in `reference/`;
- the **model revision id** (M1), which replaces the mirror `core.yaml` that the first revision
  hashed.

A code release that changes `core` or `system` therefore yields a new schema version for every pack.
The hash uses foundations' canonical JSON, so comments and formatting do not count. That stability
was Tested by probe across hash seeds and load paths (schema-rules note P9, 2026-10-28). Following
D1 §10.1's loader rule, a YAML float becomes the canonical decimal string of its shortest round-trip
form before hashing. A YAML value that is not a JSON scalar, such as a date, is refused. The stored
`source` keeps each pack file's text, and only the parsed content is hashed, so a comment-only edit
is not a new version (Proposed).

**Several packs, one version** (coordinator decision 25; alignment review §1). A project that
combines packs compiles them into one schema version. Local names are checked for uniqueness across
them at compile time, and the name map and the rule-view naming rule (§3.3) rely on that check.
Phase 0 has one pack; the check is tested with the minimal pack beside statistics.

**Core rules.** C7 requires the domain-free slot-kind check to be a finalize rule over the grammar's
readings. A core rule belongs in no pack, so it lives in `domains/core/schema/rules.yaml`, as D2 §2
now names it. It is compiled with every pack's rules and hashed into every schema version. Its first
rule is `core.value_kind_matches_slot` (§3.5).

**Pack files** come from S4's `results/s4/schema/` (step 1, record `s4.pack-lint`), which replaces the
v0 drafts in D2 §6 and §9. The core module moves to the model (M1). From D2 §9's rule table, the port
keeps:
- `stat.param_keys_known` and `stat.domain_is_set`, both `at: [finalize]`;
- `stat.one_distribution_per_statement` and `stat.no_family_on_variable`, as errors at both sites.

It drops `stat.supposed_is_used`, because INV-06 is rejected at submission (§3.7), and
`stat.variance_nonnegative`, which is M20's in phase 2.
- **The guideline section.** The `guideline:` section holds the eleven S0-R2 checks.
- **The predicate groups** are native `subsets` with `in_subset`: `structural` in the model's `core`
  module, and `formula` and `family_structure` in the pack. Their descriptions state the condition
  rule the reference prints (§3.3).
- **Linting.** `.linkmllint.yaml` extends `recommended`, with the note's L-09 levels and the prefix
  decision taken in S4-A.
- **Identity.** The pack declares `ci:case preserve` on `RandomVariable` (its label) and on
  `FamilyParameter.canonical_name` (TM §8, under OPEN-D1-3's rule). Its identity qualifiers keep their
  `ci:identity_qualifiers` lists.

### 3.2 The typed lookup, `KeySchema` and the name map

`SchemaView` is used only while compiling. Each compile produces a frozen `SchemaLookup` (dataclasses
and tuples).
- **Why frozen.** Request-time code in the MCP server, consolidation and evaluation reads only this
  lookup. It therefore never touches SchemaView's memoized caches from worker threads, and never pays
  LinkML's lookup cost per item (Proposed).
- **What it holds:**
  - entity classes with their scope, `unique_keys` identity slots, label case policy, examples and
    title;
  - value classes, each with its `t` tag;
  - predicates with prefixed name, domain, range, object kind, allowed and identity qualifiers,
    functional, symmetric, transitive, subsets, `ci:param_map` and extract mode;
  - qualifiers with object kind, range, key role, role condition and case policy;
  - enums and permissible values, with their annotations and member properties, the version-scoped
    sets unioned per version;
  - condition predicates with arity and argument class;
  - `parameter_class` classes;
  - `is_a` over `class_ancestors` (mixins included).
- **Applicability.** Predicate applicability per class is `domain ∈ class_ancestors(cls)`, then
  `induced_slot(p, cls)`, because `class_induced_slots` omits free predicates.
- **Prefixed names** come from `get_uri(…, expand=False)` (D2 §7.1; schema-rules note L-08, Tested
  by probe, 2026-10-28).
- **Citing it.** The lookup's content is the body of the schema-tables artifact. A consumer that must
  record what it read cites that artifact's hash.

**The compiled `KeySchema`** (coordinator decision 20; ADR-0023;
[R02](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r02); TM §8).
`KeySchema` is foundations' type (F2d). This document fills its pack half from the lookup:
- identity keys per class, by prefixed name, from `unique_keys`;
- `entity_identity`, the identity slots that hold entities;
- symmetric condition predicates;
- prefixed predicate names;
- per predicate, a `QualifierSpec` for each schema qualifier: range, key role, role condition,
  canonical form by range and case policy, compiled from the declarations of §3.1;
- the case policy of each class label and string-ranged slot.

It joins that half with the core half from M1's generated `QualifierSpec`s, and records the model's
key scheme. Keys, consolidation's slots and conflict detection, and the rule view all read this one
compiled input, so none of them restates a role or a case rule. The `CompiledSchema` bundle holds it.

**The pack name map** (X2-01, the pack half; R04;
[DA-006](../../design_review/audit/semantic-model-and-authority.md#da-006)).
- **What it holds.** The local ↔ prefixed names of every pack element (classes, predicates, slots,
  enums and permissible values), from `get_uri(expand=False)`. M1's generated tables supply the core
  names.
- **The uniqueness check.** A local name that maps to two prefixed names in one schema version is a
  compile error naming both. This covers the multi-pack premise of decision 25.
- **Who uses it.** T1's renaming (A0's cascade writes the stored form with prefixed names, and
  `validate`'s checks read them), the compiled `identity_keys`, `aliases.head_words` keyed by
  prefixed class, and the stored form's prefixed enum names (F2e's `EnumValue` per form) all use it.

### 3.3 Compilers and artifact identity

Each compiler is a pure function of a loaded pack and the model. It returns
`CompiledArtifact(compiler, compiler_version, kind, body, hash)`, where the hash is SHA-256 of the
body's canonical JSON (D3 §3), and a text artifact is a JSON string. A float in a body is a compile
error, because canonical JSON refuses floats. The kinds this document defines:

| Compiler | Kind | Body |
|---|---|---|
| `schema_tables` | `tables` | rows for `meta.schema_class`, `schema_slot`, `schema_enum`, `schema_rule` (the rule rows from the loaded rules file), and the per-version member rows of the version-scoped sets |
| `json_schema` | `batch.model_facing`, `batch.stored`, `batch.decoding` | draft 2020-12 JSON Schema, each with an `$id` |
| `annotator_reference` | `reference` | the reference as Markdown text |
| `rules` | `rules` | the normalized rule set: ids, group, sites, resolved predicate sets, severity, expression text, tables, normalized views, each site's attribute type map, and the qualifier identifier table (§3.5) |

**Compiler version.** The compiler version is the compiler's own version joined with the versions
of the libraries that shape its output, for example
`json_schema 1+pydantic=2.14.1+linkml-runtime=1.12.1`. Pydantic's policy allows JSON Schema
formatting to change in minor releases (schema-rules note, version caveats).
- **Effect.** A library bump then yields a new artifact identity and new rows. Without the library
  versions, a bump would leave a silent second body under an old identity, which registration refuses
  (§3.4) (Proposed).
- **The bundle.** `CompiledSchema` holds the lookup, the compiled `KeySchema`, the name map, the
  adapters, the compiled rules per site and the artifact records. It is immutable and built once per
  process per schema version.

**Batch models** (D2 §7.3; schema-rules note L-02, L-03):
- One claim model per predicate is built with `pydantic.create_model` from the lookup. It has:
  - a `Literal` predicate and the subject reference;
  - the object, as a typed entity reference or the value variants admitted by `ci:object` and range;
  - a qualifier model holding the core qualifiers (from M1's `QualifierSpec`s) plus the predicate's
    listed schema qualifiers, each typed by its object kind.

  Enum values are `Literal`s per form: local names in the model-facing form, prefixed in the stored
  form. Descriptions come from the slot.
- The claim models form a union discriminated on `predicate`, inside F2b's envelope and item models
  for each form. The stored form uses F2e's stored items: offsets, segment keys, `scope_segment`, the
  typed rendition reference, and the `outside` item with its descriptor.
- One `TypeAdapter` per form validates and exports, through `json_schema(mode="validation",
  schema_generator=…)` with foundations' `GenerateJsonSchema` subclass.
  - The subclass drops field titles and sets `$schema` to draft 2020-12.
  - Each exported schema carries an `$id` under M3's convention, naming the model revision, the
    schema version and the form. A `referencing.Registry` resolves them.
  - The exported dict is serialized as canonical JSON, so the schema text is byte-stable across
    processes. That stability was Tested by probe on the model-facing form (schema-rules note P5,
    P7, 2026-10-28).
- Admissible value variants per position are read from the core value union, not listed in the
  compiler. A core value variant therefore needs no compiler change.
- There is one canonical entity-reference shape and one formula shape per position, and `Statement`
  appears only in `statements[]`, as S4's variants V1 and V2 settle them (record
  `s4.batch-validation`). The spike's three entity-reference forms and bare-LaTeX coercion are not
  admitted. The authored `outside` item (S4 V2) gains its descriptor (F2e; RC11).
- **Validation is on the JSON path.** Submissions are validated with
  `adapter.validate_json(text, strict=True)` on the JSON text of the submitted object.
  - Strict Python-mode validation rejects a list where the frozen core models declare a tuple, while
    strict JSON validation accepts arrays (Interface-checked, Pydantic 2.14.1 docs via Context7,
    2026-10-28).
  - Strict mode keeps `"1"` from coercing to `1`.

**The decoding form** (T6) is a pure transform of the model-facing schema by D2 §7.3's backend rules:
- it strips `discriminator`, `default` and the descriptions (the declared omissions of T6);
- it asserts that every `oneOf`/`anyOf` is disjoint by a `predicate` `const`;
- it asserts the absence of `if`/`then`/`else`/`not`, multi-branch `allOf` and the keywords that
  move vLLM off xgrammar;
- it asserts nesting of at most 64 levels.

A violated assertion is a compile error, so a change to the model-facing form that breaks
decodability fails at compile time. It has no phase 0 consumer, so its tests are structural;
`s4.decoding-form` supplies the xgrammar result.

**The annotator reference** ports `reference()` and `card()` from `code/s0r2_inputs.py` onto the
lookup. It builds a structured document, then renders it as Markdown. The parts follow D2 §7.5:
- **Entity types** are listed with description, scope, identity slots and examples.
- **Predicate cards** are grouped by the pack's subsets.
  - Each card's role and modality lines are rendered from `rules.yaml`'s `tables:`.
  - The conditions line comes from the description of the subset that groups the predicate, or else
    from the `guideline:` rules that apply to it.
  - Guideline text never enters, so the reference is a function of the schema version alone
    (Proposed).
- **The shape tables** are rendered from one example instance per core shape. Each example is
  validated against F2b's adapters when the reference compiles, so a shape change that the reference
  does not follow fails compilation.
- **The worked examples** are embedded verbatim from `reference/E*`: packet text, authored batch and
  citation frame. Each batch is validated against the model-facing adapter at compile time. Agent
  interface owns the test that its packet assembler reproduces those packets; evaluation reserves
  their pages.

The phase 0 agent and golden passes receive the whole reference (D4 §4.2). Its size in tokens is
`s4.sizes`, read for phase 1's filtering.

**Schema tables** (D2 §7.1) are rows built from the lookup and the rules file:
- class identity keys from `unique_keys`;
- slot `subsets`;
- the native metaslots the design reads (`symmetric`, `transitive`, `in_subset`), under
  `annotations`;
- the key role and case policy of each slot;
- the per-version members of every version-scoped set.

They are a projection of the `tables` artifact (§3.4).

### 3.4 Registration (P0-S-1b)

`schema.registry.ensure(conn, project, pack_path, created_by) → SchemaVersionRef`:

1. Load and hash the pack over the installed model.
2. **The model revision.** Insert the installed model revision's `meta.model_revision` row from M1's
   checked-in log, with `ON CONFLICT DO NOTHING`, then select it. The log is the authority, and the
   row is its projection (M §3.1).
3. **The schema version.** Insert the `meta.schema_version` row with `ON CONFLICT (project_id,
   content_hash) DO NOTHING`, then select it.
   - The row records the model revision id.
   - `parent_id` is the project's latest version of the domain.
   - `migration` holds the change record (M4) and is null for a first version. Phase 0 has no
     second version.
4. **The payload schemas.** Register the payload schemas the version and the installed revision use:
   one `meta.payload_schema` row per payload class and version, from M4's registry content (JSON
   Schema `$id`, Arrow schema bytes, `sql_visible` paths, upcaster name), `ON CONFLICT DO NOTHING`.
   Every writer's `payload_schema_id` then exists before the run starts.
5. **The compiled artifacts.** For every installed compiler and kind, insert the
   `meta.compiled_artifact` row if its identity is absent, through foundations' `insert_artifact`
   with its `payload_schema_id`.
6. **The mismatch refusal.** If the row exists, recompile and compare hashes. A different hash under
   an existing identity means a compiler's output changed without a version bump. `ensure` then
   fails, naming the compiler and kind. It never rewrites the row and never adds a second body (D3
   §3: rows are added, never edited).
7. **The projection.** The transaction that inserts a new `schema_tables` artifact also **upserts**
   that version's `meta.schema_*` rows and per-version member rows.
   - Rows now carry FKs from claims, entities and vocabulary columns (composite FKs on
     `(schema_version_id, value)`, M2). The first revision's "replace the projection" therefore
     becomes an upsert, as the review's R05 limits state.
   - A newer compiler's rows that omit a name rows still reference fail on the FK. `ensure` reports
     that as a typed refusal naming the compiler, the element and the referencing table. It is never
     a silent orphan.
   - The projection is a read model for SQL joins, metrics and FKs, never a run input, so upserting
     it breaks no provenance.

Concurrent `ensure` calls are safe, because every insert is conflict-free on its unique key and
upserts are idempotent (Proposed). Orchestration's pack-version upsert calls `ensure` (`ci project
init`, and `ci run` and `ci ingest` per D8 §4). It writes the guideline version against the returned
id, and the run records the model revision, the schema version and the key scheme (O1).

`schema.registry.compiled_for(conn, schema_version_id) → CompiledSchema` rebuilds the bundle from the
stored `source`, never from disk, which may have moved on since.
- **Refusals.** It refuses when the installed model revision differs from the version's model
  revision, because a code release changes the model. It checks every artifact hash against the
  stored rows and refuses on a mismatch.
- **Effect.** A process whose installed model or compilers differ from the run's therefore cannot act
  on that run with different artifacts.
- **Rules.** Compiled rules are rebuilt this way and never unpickled (D2 §7.4).
- **When it is built.** The MCP server builds the bundle once in its lifespan; consolidation and
  evaluation build it once per process.

### 3.5 Rules and the rule language (P0-S-2)

**Rule-language helper** (`schema/rulelang.py`; schema-rules note L-04, L-05):
- It builds a rule-engine `Context` with `type_resolver_from_dict(types)`,
  `mapping_attribute_lookup=False` and `default_timezone="utc"`.
- Structured symbols are `OBJECT`s read through a `getattr` accessor over plain view objects.
- `tables:` become typed `$` builtins through `Builtins.from_defaults(values=…, value_types=…)`.
- Each rule is compiled in its own context, and a rule whose `context.symbols` meets
  `{now, today, random}` is refused.
- **Literal checks at compile** (coordinator decision 23; RC14;
  [DA-012](../../design_review/audit/structure-and-invariants.md#da-012)). Each symbol whose type is a
  vocabulary (a closed set from M1's generated `_model`, a pack enum or a version-scoped set from the
  lookup) is declared with that vocabulary.
  - After construction, the helper walks the parsed expression (`Rule.statement`) for comparisons
    and memberships between such a symbol and a string literal, and refuses a literal outside the
    vocabulary. It names the rule, the symbol and the nearest member.
  - Constant reduction can fold literals during parsing, so the walk reads the reduced tree.
  - rule-engine documents `rule_engine.ast` as private, with no stable extension surface. If the
    walk proves infeasible on 5.1.0, the fallback is to expose each vocabulary as an `$enums`
    builtin. Rules then write membership against it (`x in $enums.modality`), and a lint refuses a
    bare string literal compared with a vocabulary-typed symbol.
  - Which of the two is built is settled inside S2, by a test on the pack's rules and orchestration's
    policies.

Misspelled attributes, nullable misuse, wrong argument types and unknown symbols fail at construction
(Tested by probe, schema-rules note P8, 2026-10-28). With the literal check, a typo in a literal fails
too. Orchestration's policy `Chain`s use the same helper with typed policy symbols, so policies and
rules share one compile discipline (ADR-0018; DA-012's policy half is O2's).

**Rules compiler** (D2 §7.4, D5 §8.2):
- **The sections:**
  - `rules:`, with severity `error` or `warning` and a declared `at:`;
  - `guideline:`, which holds warnings only, with `at: [batch, finalize]` fixed, and belongs to the
    schema version;
  - the core rules (§3.1).
- **`applies_to`** is a predicate, a list, `subset:<name>` or `any`, resolved to a predicate set
  that indexes rules before `when` is evaluated.
- **Per-site type maps.** Each declared site has its own attribute type map.
  - The batch-site map omits the grammar-derived attributes (a value's reading). An `at: [batch]`
    rule that reads the grammar therefore fails compilation instead of silently reading null.
  - This makes D5 §8.2's "a rule that needs the grammar declares `at: [finalize]`" a compile-time
    property.
- **Rules at both sites.** A rule declared at both sites is compiled from one text under each site's
  context (Proposed). The alternative, compiling once and walking the AST for forbidden attributes,
  adds code to enforce what the type checker already gives.
- **No regex on formula text.** Rule text should not use `=~` on formula text. rule-engine regexes
  run on Python `re` without a timeout (Interface-checked, rule-engine source via Context7,
  2026-10-28), so the view supplies token-derived attributes instead (§3.6).
- **Rule ids** are unique across sections and packs. `rules:` ids carry the pack's prefix (`core.` for
  core rules); `guideline:` checks keep D2's `guideline.*` ids (decided in P0-S-2, 2026-10-29). The
  `grp` column records `rules` or `guideline`.
- **The rule-view qualifier identifier rule** (coordinator decision 25; R04).
  - A schema qualifier's attribute name in the view is its local name when that is unique among the
    qualifiers visible at the predicate across every pack of the version. Otherwise it is a mangled
    form, `<pack prefix>__<local name>`.
  - The compiler records the table in the `rules` artifact. A rule that names an ambiguous local
    name fails compilation, naming the colliding qualifiers. The check runs over the whole schema
    version, so adding a second pack cannot silently re-point a rule.

**`core.value_kind_matches_slot`** (`at: [finalize]`, warning) replaces the spike validator's
grammar-based slot check: a set read in a formula slot, a relation where a formula belongs, a formula
in a set position. It reads the finalize readings. It is a warning, not an error, because grammar
coverage is partial and a rejected agent claim would be the grammar's fault (Proposed).

### 3.6 The view builder (T4) and the batch → candidate adapter (T2)

Both translations are complete contracts (coordinator decision 21;
[R04](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r04); TM §7;
[DA-005](../../design_review/audit/semantic-model-and-authority.md#da-005)). Each declares its source
and target classes. A model-derived test, using foundations' completeness harness (F2e), enumerates
the source slots, each either mapped or declared omitted (DP-08).

**Adapter (T2).** `validate.candidates_from_batch(stored, compiled)` takes the stored batch, which is
the accepted items after T1. At submission that is A0's cascade output on the task's rendition (agent
interface §3.6, step 3). It returns foundations' keyed candidate set, and nothing is silent:
- **Every item is carried:** entities, statements, `ExternalReference` items from `outside`, claims
  with `establishment`, `derived_from` and `rule`, alternatives, unsupported items and the rendition
  reference.
- **Ids and keys.** Ids are local refs, and keys are in foundations' typed unkeyed state. Qualifier
  defaults are filled through the core models' defaults. Establishment is `stated`, and statement
  kinds come from `statements[]`.
- **Math delimiters** are normalized here, so `$…$` and `\(…\)` are equivalent (D4 §4.3 step 4). The
  LaTeX is otherwise kept as given.
- **References** are typed by kind: entity, statement and claim references are distinct types.
  - The conformance checks (§3.7) have already refused a wrong-kind or unresolved reference, so a
    candidate's reference is either resolved or a typed `ExternalReference`.
  - A reference to a rejected item resolves to foundations' typed "rejected" state, with its
    `DropReason` code, never to `None`. View attributes stay nullable rather than raising.

The pool's adapter (T3) is pool and interchange's (P1).

**Builder (T4).** `validate.build_views(candidates, compiled, site, readings=None)` returns one plain,
read-only view object per claim, with `functools.cached_property` attributes (schema-rules note §5).
No field is written back. The views hold:
- D5 §8.2's table: `id`, nullable `key`, predicate, subject and object (`id`, `type`, `label`,
  `symbol`, `identity`), value, qualifiers with defaults under their identifiers from §3.5's rule,
  statement, role, establishment, `evidence_count` and `unresolved_symbols`;
- the generic facts D5 §8.2 lists, including the attributes the `guideline:` group needs:
  - `groups`, from subsets, and `statement_kind`;
  - the flattened `condition_nodes`, `claim_refs` (each typed by kind, an unresolved one as an
    external reference) and `bindings`, all from foundations' one condition visitor;
  - `statement_premises`: the same statement or an `assumption` statement;
  - the "given as a parameter value elsewhere" map over every predicate's `ci:param_map` qualifier,
    and the symbols a claim gives;
  - token-derived symbol facts from `core/tex.py`, such as the subject's index symbols and the
    symbol a formula of the form `x = …` defines;
- the pack's `views:` attributes.

The exact names are fixed by `s4.rules` and recorded in D5 §8.2.

**Cross-claim facts** are built by indexing the candidate set once.
- Claims are grouped by predicate and by each `views:` match key (one or more field pairs, such as
  source subject to claim object), and every view reads its group.
- No view scans the pool, so the finalize cost is linear in claims (Proposed).
- Pool and interchange's P2 reimplements the `views:` facts as joins and group-bys, and its harness
  requires set equality with these.

**Sites.**
- **Batch.** The candidates are the batch's own items. `family_params` holds only the batch's
  `has_parameter` claims (D5 §8.2). Symbols are read with `core/tex.py`, which is total and fast.
- **Finalize.** The candidates come from consolidation's pool, through P1's loader and T3, as of the
  run's cut.
  - `readings`, of the type this document defines, maps (claim id, value path) to the grammar's
    (status, kind, symbols), computed by consolidation on the main thread.
  - The finalize view is one evaluation over the pool as assembled, with no fixpoint. A claim that an
    `error` rule rejects in the same pass still contributes to other claims' views, which keeps the
    step deterministic and single-pass.
  - D5 §8.2's "any status except `rejected`" then refers to statuses set before the pass, which phase
    0 does not have (Proposed; open for the D5 owner).

### 3.7 Batch conformance, reference and type checks

`validate.check_batch(batch_json, compiled, form, *, sentence_ids=None, canonical_text=None,
unit_ranges=None) → BatchReport` ports `code/instruments/validate.py` without its grammar calls.

**Sole owner** (RC19; D1 §10.3 as P0-D-1 amends it). `validate` owns reference and type checking for
batches, and the side-table checks below are the only place a batch's references are judged.
Foundations' keying resolver owns kind refusals among pool candidates and never re-checks a batch.
The checks are:

- **It never stops at the first error.** The envelope and every item are validated separately.
- **Schema-owned positions.** Pydantic errors at schema-owned positions (a `union_tag_invalid` on
  `predicate`, a `literal_error` on an enum) are reported under the D1 INV-03 category
  `unknown_schema_element`, at the same path. Metrics and messages then keep the categories of D4
  §4.3 step 5, even though the per-predicate models now catch these structurally (Proposed).
- **The schema-side checks**, which JSON Schema cannot express (D2 §7.3), work through the
  entity-type side table:
  - subject, object and entity-valued qualifier classes against domain and range by `is_a`;
  - entity scope against `ci:scope`;
  - identity slots present and of the right class;
  - condition-predicate arity and argument class;
  - binding targets: `variable` names a local entity; `family_param` names an entity of a
    `ci:parameter_class` class; `param_of` and `param_expr_of` name a claim whose `ci:param_map`
    qualifier has the entry `param`.
- **References, by kind.** It refuses duplicate, unresolved and wrong-kind local refs. For example, a
  `claim` condition naming a statement, or a subject naming a claim. Each refusal carries a typed
  code. It also checks INV-08, condition cycles, and sentence ids against the frame's `sN`/`cN`.
- **`ExternalReference` descriptors** (RC11). An `outside` item must carry a citing sentence id that
  the frame lists, and a non-empty quote. Its link target, when present, must be a locator or an
  author link target of the D1 §3.4 forms. A claim may name it as subject or object only through its
  typed reference.
- **Batch invariants:** INV-01, INV-02, INV-05 and INV-06. A `supposed` claim that no condition
  references and that has no scope is rejected at submission, so the item is fixed or dropped before
  it is written (D1 §11, D5 §8.3 as amended).
- **The stored form.** INV-10 checks spans against the rendition's canonical text, and checks that
  each span lies inside the unit. Stored names must be prefixed, through the name map (X2-01).

**The report.** The report lists issues with category, code, path, message and local ref; the message
is a projection of the code (coordinator decision 23). The submission tools compose their per-item
messages from it (D8 §2.1). The report also yields the rejected items in the `rejected` form of the
`claim_proposal` payload (D3 §6.2), so metrics count them (D4 §4.3 step 5).

**The two submission entry points** follow agent interface §3.6's order (checks, then parse, then
M19). Both submission tools call them, so `propose_claims` and `write_golden` validate identically:
- `validate.check_authored(batch_json, sentence_ids, compiled)` runs the checks on the authored form.
- `validate.check_stored(stored, compiled)` runs the stored-form checks, the adapter (T2), the views
  (T4) and the batch-site rules, and returns issues and rule findings together.

### 3.8 The M19 runner and method

`validate.run_rules(views, compiled, site) → RuleOutcome`:
- for each view, it evaluates the rules indexed under the claim's predicate for that site;
- a false `when` records nothing; a false `check` is a finding (rule id, severity, claim id,
  message);
- the outcome carries, per rule, the count of claim views it evaluated (its `when` true), as D4 M19
  states.

**What happens to findings.**
- **At finalize**, consolidation turns findings into `verification` observations that record failing
  outcomes only (`refuted`, with a detail of rule, severity and message). It bulk-writes them, and the
  counts go on the M19 task for coverage (D3 §6.2, D5 §8.1 as amended). The run's seal records that
  final M19 task (orchestration, DA-015).
- **At submission**, A1 and A2 return the findings in the tool result.

`Rule.evaluate` resets thread-local state, so one compiled rule set is shared safely by the MCP
server's worker threads (Interface-checked, rule-engine source via Context7, 2026-10-28).

**The method definition** `validate.rules` (family `validate`, unit type `run`, from the generated
`TaskUnitType`) implements O0's contract.
- **Its Config** references the rules artifact by (`rules`, `rules`), which the registry resolves
  per run, and its version is the runner's.
- **Reuse.** Tasks of unit type `run` are never reused (D4 §1 rule 4, D6 §4).
- **Who calls it.** Consolidation calls the runner inside the finalize pass; no orchestrator worker
  runs it (D4 M19).

### 3.9 Failure behaviour

| Failure | Behaviour |
|---|---|
| Pack error (vocabulary, structure, lint, an undeclared or consumer-less annotation, a key role contradicting `ci:identity_qualifiers`, a pack member of a static set) | `PackError` with every problem; `ci schema compile` exits non-zero; `ensure` refuses, so no run starts on a broken pack |
| Two local names colliding in one schema version | Compile error naming both prefixed names (§3.2) |
| Rule type error, banned builtin, a literal outside its vocabulary, an ambiguous qualifier identifier | Compilation fails with the rule id and the cause (D2 §7.4) |
| Compiler output changed without a version bump | `ensure` fails, naming compiler and kind (§3.4) |
| A newer projection omits a name that rows reference | `ensure` fails on the FK with a typed refusal naming the element and table (§3.4) |
| Installed model revision or compilers differ from a run's | `compiled_for` refuses that run |
| Rule raises during evaluation | At finalize, the step fails with rule id and claim key, as a defect (D5 §8.3). At submission, the runner reports a finding of severity `internal`, which the tool presents as a server-side failure, never as the author's error |
| Pathological formula at submission | Bounded: the tokenizer is linear, view attributes are linear in tokens, and no grammar or rule regex runs on formula text (P0CL-14) |

**Execution fit** (qualitative, FP-07).
- **Compiling** is per process and schema version: 25 branches built in 37 ms, including the
  SchemaView load (Measured by probe, schema-rules note P7, 2026-10-28, indicative). The literal walk
  and the identifier table add work linear in rule text.
- **A submission** costs per-batch Pydantic validation of about 0.02 ms (Measured, same note), plus
  linear checks, plus about 0.23 ms per claim for views and the eleven guideline rules (Measured,
  P11). That is milliseconds per batch.
- **At finalize** the work grows with claims × applicable rules, after indexing by `applies_to`.
  - With the views indexed and no scans, the phase 0 pool of a few thousand claims stays well under a
    second.
  - Phase 1's 10⁴–10⁵ claims would be tens of seconds per pass by the same indicative ratio. That is
    acceptable beside the rebuild. P2's set-based `views:` facts and a tighter loop per (predicate,
    site) are the routes if it becomes material.
- **Registration.** The upsert of the projection is per version, a few thousand rows at most.

## 4. Ports

| Spike module | Product module | Behaviour and tests kept | Not ported (known spike defects or superseded) |
|---|---|---|---|
| `code/schema/core.yaml` | the model's `core.yaml` (M1, promoted from S4's native-form file) | — (model and projections') | — |
| `code/schema/statistics.yaml` | `domains/statistics/schema/statistics.yaml`, `rules.yaml` (from S4's native-form files) | The v0 vocabulary as S4 corrects it | List-valued annotations; `ci:examples`, `ci:identity_keys` and `ci:symmetric` as annotations (D2 §3) |
| `code/instruments/schema_lookup.py` | `schema/lookup.py` | Predicate rule fields, `is_a` over `class_ancestors`, condition-predicate arity and argument class, enum values | The `_slot_prefix` heuristic (replaced by `get_uri(…, expand=False)`); `importmap` (pack layout); `map_value_kind`'s hard-coded `Formula`/`SetExpr` (replaced by range ancestry to the `Value` base and its `t` tag); `observations()` |
| `code/s0r2_inputs.py` `reference()`, `card()`, `schema()` | `schema/reference.py` | Sections, card fields, "In the worked examples" cross-references, embedded examples | Hard-coded `STRUCTURAL`/`FORM` and `GROUP_RULES` prose (replaced by subsets, `tables:` and subset descriptions); the raw YAML merge (replaced by SchemaView); the hand-written shape table (replaced by validated shape examples). `packet()`, `FORMAT_V1` and `INSTRUCTIONS` are agent interface's |
| `code/s0r2_rules.py` | `guideline:` section of `rules.yaml`, plus the view builder's generic attributes | The eleven checks and their outcomes on the v1 reference and examples | The Python checker itself; hard-coded `has_distribution`, `param_values`, `canonical_name`, `FAMILY`/`FORM` (replaced by `ci:param_map`, identity and subsets). Its outcomes survive as recorded expectations (§6) |
| `code/instruments/validate.py` | `validate/batch.py` | Categories and codes; item-by-item validation; binding-field and target checks; scope against class; identity; condition predicates; INV-01/02/05/06/08/10; cycles; sentence ids; stored spans; the 36 batch-site cases of `tests_instruments/test_validate.py` | `check_slot` and `bare_unit_formula`, which parse with the grammar at submission (P0CL-14): the slot check becomes `core.value_kind_matches_slot` at finalize, and the bare-unit check waits for M12 (phase 1). Also: the three entity-argument forms and `as_formula` coercion; the `default_lookup` global; grammar-coverage `notes`; INV-09 marking (consumers read the condition tree); untyped references, now typed by kind |
| `code/instruments/batch.py` | foundations (F2b) | — | — |

## 5. Packages

| Package | Scope | Prerequisites | Acceptance | Revealing failure case | Closes (coordinator §11) |
|---|---|---|---|---|---|
| P0-S-1 | Pack files (statistics schema and rules, core rules, `.linkmllint.yaml`, `guideline.md`, `reference/E1`–`E3`, `fixtures/packs/minimal/`); the pack loader over M1's model loader; `ci:key_role`, `ci:case` and pack `StatementKind` members; the schema version over the model revision id; the lookup; the compiled `KeySchema` pack half; the X2-01 pack name map with its uniqueness check; compilers for tables, the three batch forms with `$id`, and the reference; artifact identity and `CompiledSchema`; `ci schema compile`. The `core.yaml` mirror contract test is removed: the interim guard is M1's | P0-M-1, P0-F-2d, P0-F-2e, P0-F-3's `fixtures/s0` files (tests) | **Determinism:** artifact hashes equal in two processes with different `PYTHONHASHSEED` and load paths; a model revision change moves the schema version. **Lint:** each file lints clean, or every remaining finding is recorded. **External data:** the twelve v1 reference batches and three examples validate in the model-facing form, and the spike's stored v1 batches in the stored form, with prefixed names. **Schemas:** `check_schema` passes on every exported schema, each with its `$id`; jsonschema agrees with Pydantic on those batches and on Hypothesis draws (derivation conformance). **Reference:** it carries every information item that `s4.reference-diff` lists. **Other:** the decoding form passes its assertions; the minimal pack compiles, and beside statistics in one version its name collisions are reported; the compiled `KeySchema` gives the pack's identity qualifiers the `identity` role and `RandomVariable` labels `preserve` | T1's `{"t": "entity", "ref": …}` object and U6's `Statement` in `entities[]` are each refused at their path, per S4's V1 and V2 outcome; a comment-only edit keeps the version hash, while a description edit changes it | DA-001 (pack half), DA-009 (hash over the model revision), X2-01 (pack name map), F02 (wording here) |
| P0-S-1b | `schema.registry.ensure()`, which registers the model revision, the schema version, the payload schemas and the artifacts, and upserts the projection and per-version members; `compiled_for()` | P0-S-1, P0-F-4, P0-M-4 | `ensure` twice is idempotent. A bumped compiler version adds rows and leaves the old rows byte-identical. The projection is upserted in the inserting transaction. Removing a referenced name fails with the typed refusal. `compiled_for` from stored source reproduces every stored hash, and refuses another model revision. Two concurrent `ensure` calls leave one row per identity (P0CL-15 closure). Every payload class the version's writers use has a `meta.payload_schema` row | Compiler output changed without a version bump: `ensure` fails naming compiler and kind, instead of keeping a stale body or adding a second one | DA-009 (registration) |
| P0-S-2 | Rule-language helper with literal checks; rules compiler (`rules:`, `guideline:`, `tables:`, `views:`, `at:`, `applies_to`, core rules, the qualifier identifier rule with its collision check); T4 view builder at both sites; T2 adapter; batch conformance, reference and type checks as sole owner, with typed codes and `ExternalReference` descriptor checks; M19 runner, `validate.rules`, `check_authored`, `check_stored` | P0-S-1, P0-F-2e, P0-O-0, P0-D-2 | **Compilation:** every pack rule and the eleven guideline checks compile; each compile-time error class fails construction, including a literal outside its vocabulary and an ambiguous qualifier name; an `at: [batch]` rule reading a reading attribute fails compilation. **Outcomes:** the v1 reference and examples give 0 issues and 0 warnings, and every seeded violation is caught by its expected rule; the 36 batch-site validator cases give their expected category and code. **References:** a wrong-kind reference is refused with a code. **Translations:** T2 and T4 completeness tests pass. **Sites agree:** a rule declared at both sites gives the same outcome on a batch and on the candidate set built from it, except `stat.param_keys_known`, which runs only at finalize. **Bound:** a pathological formula completes the batch site within its bound, with `methods.math` never imported (P0CL-14, this document's half) | `stat.param_keys_known` evaluated at the batch site would warn on every batch whose family parameters are stated elsewhere on the page; the `at:` sites and the batch-site type map prevent it. A rule comparing `modality == "suposed"` compiles and never matches | DA-005, DA-006 (checks, owner), DA-012 (rule literals) |

**P0-S-1.**
- **Mechanisms:**
  - LinkML 1.12.1 `SchemaView` over M1's model loader (`class_ancestors`, `induced_slot`,
    `get_uri(…, expand=False)`, `get_class(…).unique_keys`, `permissible_value_ancestors` and
    `annotation_dict` for member properties per Q-2), with `linkml-lint` run per file;
  - pydantic 2.14.1 `create_model`, `Field(discriminator="predicate")`, a `TypeAdapter` per form,
    `json_schema(mode="validation", schema_generator=…)` and `validate_json(strict=True)`;
  - jsonschema 4.26.0 `Draft202012Validator.check_schema`, and validation with a
    `referencing.Registry` of the `$id` resources (tests and external consumers);
  - hypothesis-jsonschema `from_schema` (tests, §6).
- **Owners.** The mechanisms are owned by D2 §2, §3, §7.1, §7.3 and §7.5 and the
  [schema-rules note](../../design_review/evidence/2026-10-28_library-schema-rules/README.md)
  (L-01…L-03, L-06…L-10). The declaration vocabulary is TM §4's.
- **Evidence consumed:**
  - `s4.pack-lint`, `s4.schema-hash`, `s4.batch-validation`, `s4.reference-diff`, `s4.sizes` and
    `s4.decoding-form`;
  - `p0q.member-properties` (M-Q2, the declaration form for pack members);
  - `s0r2.reference-v1`, the v1 reference in both forms, which is the external control;
  - `s0r2.inputs`, guideline v1 and the hand-assembled reference.

**P0-S-1b.**
- **Mechanisms.** SQLAlchemy Core inserts with `ON CONFLICT DO NOTHING` and `on_conflict_do_update`
  for the projection upsert, through foundations' repository, on M2's generated `meta` tables. M4's
  registry content and change-record model.
- **Evidence consumed.** The S6 migration records, as foundations cites them for F4. No `s4.*` record
  is needed beyond P0-S-1's.

**P0-S-2.**
- **Mechanisms.** rule-engine 5.1.0:
  - a typed `Context` and `OBJECT` with a `getattr` accessor;
  - `&.`, `??`, `$all`/`$any` and positional calls;
  - `Builtins.from_defaults`;
  - a context per rule and the thread-local evaluation state;
  - `Rule.statement` for the literal walk, treated as a private surface, with the `$enums` fallback
    (§3.5).
- **Owners.** The mechanisms are owned by D2 §7.4, D5 §8.2, D4 M19, D6 §7.1 (typed symbols, P0-D-2)
  and the schema-rules note L-04 and L-05.
- **Evidence consumed.** `s4.rules`, which fixes the view attribute names and confirms `views:` and
  `tables:` on the pack's own rules (OPEN-D2-3).

## 6. Tests

| Package | What the tests establish | How |
|---|---|---|
| P0-S-1 | Determinism and identity | Hash and artifacts computed in two subprocesses with different hash seeds and with absolute and relative paths; reordered YAML keys and comments give the same version, a description edit gives a new one, and a changed model revision id a new one; a YAML float hashes as its decimal string |
| | Pack validity | `linkml-lint` per file with `.linkmllint.yaml`; each vocabulary error class gives a `PackError` naming the element, including a key role contradicting `ci:identity_qualifiers` and a pack member of a static set |
| | Batch models | The v1 reference, examples and S0-R2 batches validate; these external batches are the independent control (coordinator decision 24, [R12](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r12)). The 40 spike mutation cases run against the adapters and checks. The 36 that remain batch-site keep their expectations, re-stated for the product's categories by hand from the specification, never read back from the code. jsonschema validates the same batches, comparing errors sorted by `absolute_path` (D9 §4). That agreement is **derivation conformance**, not an independent oracle: both validators judge one model's projection, so a shared mistake passes both |
| | Exported schema, derivation conformance | hypothesis-jsonschema states full support for drafts 04, 05 and 07 and resolves non-recursive references only (Interface-checked, project README, 2026-10-28). The test therefore draws from a derived draft-7 copy with `Condition` unrolled to depth two. Pydantic and jsonschema both judge each draw against the full 2020-12 schema. Each exported schema carries its `$id`, and a `referencing.Registry` resolves them |
| | KeySchema and names | The compiled `KeySchema` for statistics and the minimal pack against expectations written from the pack files: each identity qualifier `identity`, each other listed qualifier `meaning`, `RandomVariable` and `FamilyParameter.canonical_name` `preserve`. The name map round-trips every element. Two packs with a shared local name are refused with both prefixed names. Stored v1 batches carry only prefixed names (X2-01) |
| | Reference | The structured reference against the information list from `s4.reference-diff` (test data authored from the S0-R2 reference); shape examples validate; the worked-example batches validate |
| | Generality | `fixtures/packs/minimal/` compiles to every artifact. It has one parameterized entity class, a map qualifier with `ci:param_map`, a `family_structure` subset, one `views:` entry, one rule, one example, one pack `StatementKind` member and one `ci:case preserve` slot |
| P0-S-1b | Registration | Against the per-session test database: idempotence; compiler-bump rows; the projection upsert; refusal when a referenced name is removed; the model-revision and payload-schema rows; stored-source rebuild and refusal under another model revision; concurrent `ensure` from two connections; the mismatch refusal |
| P0-S-2 | Rule compilation | One case per compile-time error class (schema-rules note P8), the banned builtins, a reading attribute in an `at: [batch]` rule, a literal outside its vocabulary (whichever of the walk or the `$enums` fallback is built), and an ambiguous qualifier identifier |
| | Rule outcomes | 0 warnings and 0 issues on the v1 reference and examples. The eleven seeded violations, each with its expected rule id recorded as test data from the note's P11 outcomes, independent of the rule implementation. The finalize-only rules on a candidate set with and without a family's parameters. The error rules at both sites |
| | References and descriptors | A wrong-kind reference in each position is refused with its code; an `outside` item without a frame-listed sentence is refused; an unresolved reference reaches the candidate set as an `ExternalReference`, never as `None` |
| | Translations | T2 and T4 completeness from the model's slot lists, each slot mapped or declared omitted |
| | Sites agree | For every rule declared at both sites, one batch through the batch site and through a hand-built finalize candidate set gives equal findings |
| | Bound and isolation | A formula of tens of thousands of characters with deep brace nesting completes the batch site within a fixed bound, and `corpus_structure.methods.math` is absent from `sys.modules` afterwards |
| | Linear views | A generated candidate set of 10⁴ claims builds views with every `views:` lookup served from the index, checked by counting index reads rather than timing |
| | Readings | `core.value_kind_matches_slot` and `stat.domain_is_set` on hand-made readings, including the three slot-kind cases ported from the spike validator |

**Fixtures and data.** Shared fixtures used, all owned by foundations, are the session test database
(P0-S-1b), the `fixtures/s0` batches and frames, and the conftest's compiled-schema fixture. This
document adds a thin session-scoped fixture that compiles the statistics pack once. Test data this
document adds:
- the spike's stored v1 batches and the S0-R2 reference, copied under `tests/data/`, never imported;
- the seeded violations;
- the minimal pack.

**Independent controls** (coordinator decision 24; R12). Here they are:
- the external S0 and S0-R2 batches;
- the hand-restated spike mutation expectations;
- the P11 rule outcomes recorded as data.

Agreement between generated projections (Pydantic, jsonschema, the decoding form) is labelled
derivation conformance.

## 7. Indicative size

| Part | Package | Product lines |
|---|---|---|
| Loader over the model, pack declarations, version hash, rules-file model | P0-S-1 | 240 |
| Lookup | P0-S-1 | 150 |
| Compiled `KeySchema` pack half, name map and uniqueness check | P0-S-1 | 100 |
| Tables compiler | P0-S-1 | 80 |
| Batch models, export with `$id`, decoding transform | P0-S-1 | 300 |
| Annotator reference | P0-S-1 | 200 |
| Artifact identity, `CompiledSchema`, `ci schema compile` | P0-S-1 | 100 |
| Registration: revision, payload schemas, upsert, typed refusals | P0-S-1b | 150 |
| Rule-language helper with literal checks, rules compiler with the identifier rule | P0-S-2 | 280 |
| View builder (T4) and adapter (T2) | P0-S-2 | 230 |
| Batch conformance, reference and type checks | P0-S-2 | 180 |
| Runner, method, `check_authored`, `check_stored` | P0-S-2 | 60 |
| **Total** | | about 2,070, against the coordinator's 1,900 |

The pack files, the guideline, the worked examples and tests are excluded. The mirror contract test
left with M1's interim guard. The batch checks are the part most likely to shrink, because the
per-predicate models and the typed references already catch most of what the spike validator checked
by hand. The additions of the alignment review (KeySchema, the name map, literal checks, the
identifier rule, the registration upsert) account for the overrun.

## 8. Choices left to implementation

- Module names inside `schema/` and `validate/`, and the split of `CompiledSchema` into lazily built
  parts.
- Whether entities are also discriminated on `type`, with per-class identity models. That would make
  identity-slot errors structural, at the cost of a second union in the exported schema.
- The exact view attribute names, within what `s4.rules` and D5 §8.2 fix.
- The layout of the `rules` artifact body, provided it covers everything that shapes compilation.
- How `compiled_for` materializes stored sources so imports resolve as on disk (a temporary pack
  layout over M1's loader, or an `importmap`). A stored-source build must equal a disk build, which
  is tested.
- The mangled form of an ambiguous qualifier identifier, provided it is deterministic and the
  collision check covers the whole version.
- Card wording and section order of the reference, within D2 §7.5's parts and the information list.
- `ci schema compile` output columns and `--json` shape.
- `linkml-lint` rule levels beyond the note's list.
- The dependency split: `linkml-runtime` at runtime (pinned by M1) and `linkml` (the linter) as a
  dev dependency, since no generator is used for batch shapes (D2 §6, §7.3). This is pinned exactly
  either way.
