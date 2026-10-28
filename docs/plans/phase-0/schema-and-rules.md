# Phase 0 · Schema and rules

**Status:** Proposed (2026-10-28). Part of the [phase 0 series](../phase-0_2026-10-28.md), which
owns shared decisions, contracts, the dependency graph and build findings. Packages P0-S-1 and
P0-S-2 are drafted against the [schema-rules note](../../design_review/evidence/2026-10-28_library-schema-rules/README.md)
and finalized when S4 reports (records `s4.*`, [S4 plan](../design-spikes-s0-s1/S4-linkml-compilation.md));
ADR-0017 and ADR-0018 stay proposed until then.

## 1. What this document builds

This document builds the code that turns a domain pack into the artifacts its consumers read. It
also builds the code that checks authored batches against the pack and runs the pack's rules at
both call sites:

- **`schema/`**: it loads a pack (`domains/<name>/schema/`, the imported `core.yaml` and the
  worked examples in `reference/`) and computes the schema version. A typed lookup exposes the
  pack's vocabulary. The phase 0 compilers produce the schema-table content, the batch models and
  JSON Schema in the model-facing, stored and decoding forms, the annotator reference and the
  compiled rules. Compiled-artifact identity and registration in `meta` belong here too, along
  with the rule-language helper that orchestration's policies reuse and `ci schema compile`
  ([D2 §2](../../design/D2-schema-and-guidelines.md#2-domain-pack-layout), [§7](../../design/D2-schema-and-guidelines.md#7-compilers);
  [D3 §3](../../design/D3-database.md#3-meta-schema-guidelines-and-domain-declarations)).
- **`validate/`**: it holds the batch conformance checks (D4 §4.3 steps 1 and 3, and the D1
  invariants a batch can violate) and the batch→candidate adapter. One rule-view builder serves
  both call sites over the `core` keyed candidate set, and the M19 runner and method definition
  sit beside it ([D2 §7.4](../../design/D2-schema-and-guidelines.md#74-to-rule-engine-rules),
  [D5 §8](../../design/D5-consolidation-identity-confidence.md#8-validation),
  [D4 M19](../../design/D4-method-catalog.md#m19-validaterules)).
- **Pack files.** These are `domains/core/schema/core.yaml`, `domains/statistics/schema/statistics.yaml`
  and `rules.yaml`, ported from S4's native-form files. Beside them come `.linkmllint.yaml`,
  `domains/statistics/guideline.md` (ported from D2 §10, guideline v1 with the §10.4 parameter-naming rule the v1 reference follows; not from the S0-R2 file, which predates that rule), the worked examples
  `domains/statistics/reference/E1`–`E3`, and a minimal compile-test pack in
  `fixtures/packs/minimal/`.

**Where it ends.**
- The quote cascade is agent interface's A0, which is schema-free.
- Packets, prompts, the MCP tools and the sequencing of a submission belong to A1 and A2.
- Writing observations belongs to foundations' repository. Consolidation writes M19's
  `verification` observations, and orchestration records the M19 task.
- Guideline versions are written by orchestration's pack-version upsert. Policy chains are
  orchestration's (O2), built with this document's rule-language helper.
- The math grammar is ingest and math's. At finalize its results reach the view builder as data
  from consolidation, and `validate` never imports `methods/math`.
- The toy second pack is consolidation's P0-C-4.
- **Not in phase 0.** The GLiNER2 compiler (D2 §7.2), the reference filtered by statement kind
  (S4 variant V4) and the local tier's decoding-form consumer (M10) wait for phase 1. So do
  `ci schema diff` and the `propose_schema_change` compile path, since schema v0 is frozen
  (coordinator §3 decision 9) and no second version exists. Schema migrations (D2 §8) and the
  compilation of `derive:` rules (M23) wait for phase 2; the loader reads `derive:` and the
  tables project it.

**Change scenarios that explain the boundaries** (from [DESIGN §1.3](../../design/DESIGN.md) and
the phase 1 additions; none is built here beyond what phase 0 needs):

| Change | Where it is expressed | What is reused | What stays unaffected |
|---|---|---|---|
| A second domain pack | New pack files: classes and predicates, `ci:param_map`, `ci:parameter_class`, the `family_structure` subset, `views:`, rules, worked examples | Loader, lookup, every compiler, the view builder, the conformance checks, the runner | Every module of `schema/` and `validate/`; the minimal pack and consolidation's toy pack (P0-C-4) check this |
| A rule with `or`/`not` conditions | `rules.yaml` text | The flattened condition-node attribute, the typed context | The compilers: condition trees are core shapes (D1 §7) |
| A claim with `valid_time` and attribution | Core qualifiers in `core.yaml`, already admitted on every branch | The per-predicate builder's core-qualifier set | Keys are foundations' (D1 §10.1) |
| A table segment with quantities and units | A predicate whose `ci:object` is `number`; the `NumberValue` shape (D1 §6) | The branch builder takes admissible values from the core union | Unit checks wait for M12 (phase 1) |
| The GLiNER2 tier (phase 1) | A new compiler with its own artifact kinds | Artifact identity, registration, method configurations referencing artifacts by (compiler, kind) | The existing artifacts and their rows |
| A compiler or library fix | A new compiler version string | Registration adds rows beside the old ones (§3.4) | Runs that used the old artifacts keep them |

## 2. Contracts

### 2.1 Consumed (cited, never redefined)

| Contract | Owner | Needed by |
|---|---|---|
| Canonical JSON and its hashing ([D1 §10.1](../../design/D1-knowledge-representation.md#101-hashing)), including its float rule | foundations, F2a | S1 (version and artifact hashes) |
| `core/tex.py`: TeX tokenizer, drop list, token form (coordinator §3 decision 13) | foundations, F2a | S2 (batch-site view) |
| D1 value, condition and binding shapes; batch items in both forms, including the generic stored-item models; the citation-frame model; the keyed candidate set (claims, entities and statements, each with an `id` and a nullable `key`) ([D2 §6](../../design/D2-schema-and-guidelines.md#6-the-core-schema), D9 §1) | foundations, F2b | S1 (per-predicate models, mirror test), S2 (adapter, view) |
| Method-contract types and the registry interface (`core/method.py`, [D4 §1](../../design/D4-method-catalog.md#1-the-method-contract)); method configurations declare artifact references by (compiler, kind), and the registry resolves them against the run's schema version | orchestration, O0 and O1 | S2 (M19's method definition) |
| `meta.schema_version`, `meta.compiled_artifact` and the `meta.schema_*` tables, with `meta.schema_rule` carrying `at`, `grp` and `applies_to text[]` and `meta.schema_slot` carrying `subsets` and `annotations` (D3 §3 as amended), and the repository | foundations, F4 | S1b |
| `fixtures/s0` authored batches with their frames: the files, not F3's acceptance | foundations, F3 | S1, S2 tests |
| Grammar readings at finalize: per value, status, kind and symbols, computed once per pass on the main thread (D5 §8.2 as amended) | consolidation, C1 (from ingest and math's grammar) | S2 (finalize-site view) |
| Shared conftest, test database and the thin-fixture convention (coordinator §3 decision 10) | foundations, F1 | every package's tests |

### 2.2 Produced

| Contract | Design owner | What this document implements | Consumers |
|---|---|---|---|
| Pack loading and the schema version | D2 §2, §3 | Loader, annotation parsing, version hash over the pack schema, `rules.yaml`, `core.yaml` and `reference/` (§3.1) | orchestration O1 (upsert), every artifact consumer |
| The typed schema lookup | D2 §3, §7.1 | Frozen lookup materialized from `SchemaView` (§3.2) | consolidation C1, evaluation E2a and E2b, agent interface A1 |
| Compiled artifacts and their identity | D2 §7, D3 §3 | One record per (schema version, compiler, compiler version, kind); registration in `meta` (§3.3, §3.4) | method configurations in O1, A1, A2, C1; reuse ([D6 §4](../../design/D6-orchestration-metrics-policies.md#4-caching-and-reuse)) |
| Batch models and JSON Schema in the model-facing, stored and decoding forms | [D2 §7.3](../../design/D2-schema-and-guidelines.md#73-to-json-schema-for-llm-claim-proposals) | Per-predicate models, one adapter per form, export, the decoding transform (§3.3) | A1 (`read_instructions`, `propose_claims`), A2 (`write_golden`), C1 (per-predicate qualifier validation, D3 §6.1), phase 1 M10 |
| The annotator reference | [D2 §7.5](../../design/D2-schema-and-guidelines.md#75-to-the-annotator-reference), §10.10 | Generator over the lookup, `tables:`, subsets and worked examples (§3.3) | A1 (prompt part), A2 (`read_golden_unit`); evaluation E1 reads the examples' pages as reserved ([D7 §3.1](../../design/D7-evaluation-goldens-outer-loop.md#31-units-and-sets)) |
| Batch conformance checks | [D4 §4.3](../../design/D4-method-catalog.md#43-output-form-and-post-processing) steps 1 and 3; [D1 §11](../../design/D1-knowledge-representation.md#11-invariants) | `validate.check_batch` for both forms (§3.7) | A1, A2, C1 |
| Compiled rules, the view builder, the batch→candidate adapter, M19 | D2 §7.4, D5 §8.1, §8.2, D4 M19 | Rules compiler, views at both sites, runner, `validate.rules` method (§3.5–§3.8) | A1 and A2 (batch site), C1 (finalize site), E2b (rule-warning reading, D7 §7) |
| The rule-language helper | D2 §7.4, [D6 §7.1](../../design/D6-orchestration-metrics-policies.md#71-language); ADR-0018 | Typed contexts with UTC, a context per rule, banned builtins (§3.5) | orchestration O2 (policy `Chain`s) |
| `ci schema compile` | [D8 §4](../../design/D8-agent-and-query-interfaces.md#4-cli) | Compile from disk; print or write artifacts and hashes | the operator |

## 3. Design of the parts

### 3.1 Pack and loader

`schema.load_pack(path)` reads the pack through `SchemaView` in the D2 §2 layout. Imports resolve
relative to the importing file, with no `importmap` (Tested by probe, schema-rules note P1,
2026-10-28). The loader then checks the `ci:` vocabulary against D2 §3:
- only declared annotation keys, with scalar values;
- the space-separated lists (`ci:qualifiers`, `ci:identity_qualifiers`, `ci:target`) are parsed
  and each name is checked against a declared slot;
- `ci:kind` and `ci:object` are derived from `abstract`, value-class ancestry and `range`, and a
  written value counts only as a checked override;
- `ci:param_map` names a map qualifier that its predicate lists;
- `ci:parameter_class` names an identity slot;
- no core qualifier appears in `ci:qualifiers`.

`rules.yaml` is read into a typed file model with the sections `rules:`, `guideline:`, `tables:`,
`views:` and `derive:`. The loader checks structure only; S2 compiles the expressions. The loader
refuses unknown top-level keys. `derive:` entries are read and projected into `meta.schema_rule`
with group `derive` (D3 §3), but nothing compiles them until M23 lands in phase 2. Failures raise one `PackError` that
lists every problem with its file and element, never only the first.

**Schema version.** SHA-256 over the canonical JSON of the parsed pack schema, `rules.yaml`,
`core.yaml` and the worked examples in `reference/` (D2 §2 as amended for the worked examples).
It uses foundations' canonical JSON, so comments and formatting do not count; that stability was
Tested by probe across hash seeds and load paths (schema-rules note P9, 2026-10-28). Following
D1 §10.1's loader rule, a YAML float becomes the canonical decimal string of its shortest
round-trip form before hashing. A YAML value that is not a JSON scalar, such as a date, is
refused. The stored `source` keeps each file's text, and only the parsed content is hashed, so
a comment-only edit is not a new version (Proposed).

**Core rules.** C7 requires the domain-free slot-kind check to be a finalize rule over the
grammar's readings. A core rule belongs in no pack, so the proposal is a
`domains/core/schema/rules.yaml`, compiled with every pack's rules and hashed with `core.yaml`.
Its first rule is `core.value_kind_matches_slot` (§3.5). D2 §2's source list must name this
file. That amendment is an open point for the design owner, reported to the coordinator
(Proposed).

**Pack files** come from S4's `results/s4/schema/` (step 1, record `s4.pack-lint`), which
replaces the v0 drafts in D2 §6 and §9. From D2 §9's rule table, the port keeps:
- `stat.param_keys_known` and `stat.domain_is_set`, both `at: [finalize]`;
- `stat.one_distribution_per_statement` and `stat.no_family_on_variable`, as errors at both
  sites.

It drops `stat.supposed_is_used`, because INV-06 is rejected at submission (§3.7), and
`stat.variance_nonnegative`, which is M20's in phase 2. The `guideline:` section holds the
eleven S0-R2 checks. The predicate groups (`structural` in `core.yaml`; `formula` and
`family_structure` in the pack) are native `subsets` with `in_subset`, and their descriptions
state the condition rule the reference prints (§3.3). `.linkmllint.yaml` extends `recommended`,
with the note's L-09 levels and the prefix decision taken in S4-A.

### 3.2 The typed lookup

`SchemaView` is used only while compiling. Each compile produces a frozen `SchemaLookup`
(dataclasses and tuples). Request-time code in the MCP server, consolidation and evaluation reads
only this lookup, so it never touches SchemaView's memoized caches from worker threads and never
pays LinkML's lookup cost per item (Proposed). The lookup holds:
- entity classes with their scope, `unique_keys` identity slots, examples and title;
- value classes, each with its `t` tag;
- predicates with prefixed name, domain, range, object kind, allowed and identity qualifiers,
  functional, symmetric, transitive, subsets, `ci:param_map` and extract mode;
- qualifiers with object kind and range;
- enums and permissible values with their annotations;
- condition predicates with arity and argument class;
- `parameter_class` classes;
- `is_a` over `class_ancestors` (mixins included).

Predicate applicability per class is `domain ∈ class_ancestors(cls)`, then `induced_slot(p, cls)`,
because `class_induced_slots` omits free predicates. Prefixed names come from
`get_uri(…, expand=False)` (D2 §7.1; schema-rules note L-08, Tested by probe, 2026-10-28). The
lookup's content is the body of the schema-tables artifact. A consumer that must record what it
read cites that artifact's hash.

### 3.3 Compilers and artifact identity

Each compiler is a pure function of a loaded pack. It returns `CompiledArtifact(compiler,
compiler_version, kind, body, hash)`, where the hash is SHA-256 of the body's canonical JSON
(D3 §3) and a text artifact is a JSON string. A float in a body is a compile error, because
canonical JSON refuses floats. The kinds this document defines:

| Compiler | Kind | Body |
|---|---|---|
| `schema_tables` | `tables` | rows for `meta.schema_class`, `schema_slot`, `schema_enum`, `schema_rule` (the rule rows from the loaded rules file) |
| `json_schema` | `batch.model_facing`, `batch.stored`, `batch.decoding` | draft 2020-12 JSON Schema |
| `annotator_reference` | `reference` | the reference as Markdown text |
| `rules` | `rules` | the normalized rule set: ids, group, sites, resolved predicate sets, severity, expression text, tables, normalized views and each site's attribute type map (§3.5) |

**Compiler version.** The compiler version is the compiler's own version joined with the
versions of the libraries that shape its output, for example
`json_schema 1+pydantic=2.14.1+linkml-runtime=1.12.1`. Pydantic's policy allows JSON Schema
formatting to change in minor releases (schema-rules note, version caveats). A library bump then
yields a new artifact identity and new rows. Without the library versions it would be a silent
second body under an old identity, which registration refuses (§3.4) (Proposed). The bundle
`CompiledSchema` holds the lookup, the adapters, the compiled rules per site and the artifact
records. It is immutable and built once per process per schema version.

**Batch models** (D2 §7.3; schema-rules note L-02, L-03):
- One claim model per predicate is built with `pydantic.create_model` from the lookup: a
  `Literal` predicate, the subject reference, the object as an entity reference or the value
  variants admitted by `ci:object` and range, and a qualifier model holding the core qualifiers
  plus the predicate's listed schema qualifiers, each typed by its object kind. Enum values are
  `Literal`s and descriptions come from the slot.
- The claim models form a union discriminated on `predicate` inside F2b's envelope and item models
  for each form. The stored form uses F2b's stored items: offsets, segment keys,
  `scope_segment`, and the rendition the form was derived on.
- One `TypeAdapter` per form validates and exports, through `json_schema(mode="validation",
  schema_generator=…)` with a `GenerateJsonSchema` subclass. The subclass drops field titles and
  sets `$schema` to draft 2020-12. The exported dict is serialized as canonical JSON, so the
  schema text is byte-stable across processes. That stability was Tested by probe on the
  model-facing form (schema-rules note P5, P7, 2026-10-28).
- Admissible value variants per position are read from the core value union, not listed in the
  compiler. A core value variant therefore needs no compiler change; `extref` (OPEN-D1-5) is
  deferred to the phase 0 boundary.
- One canonical entity-reference shape and one formula shape per position, and `Statement` only
  in `statements[]`, as S4's variants V1 and V2 settle them (record `s4.batch-validation`). The
  spike's three entity-reference forms and bare-LaTeX coercion are not admitted.
- **Validation is on the JSON path.** Submissions are validated with
  `adapter.validate_json(text, strict=True)` on the JSON text of the submitted object. Strict
  Python-mode validation rejects a list where the frozen core models declare a tuple, while strict
  JSON validation accepts arrays (Interface-checked, Pydantic 2.14.1 docs via Context7,
  2026-10-28). Strict mode keeps `"1"` from coercing to `1`.

**The decoding form** is a pure transform of the model-facing schema by D2 §7.3's backend rules:
- it strips `discriminator` and drops descriptions;
- it asserts that every `oneOf`/`anyOf` is disjoint by a `predicate` `const`;
- it asserts the absence of `if`/`then`/`else`/`not`, multi-branch `allOf` and the keywords that
  move vLLM off xgrammar;
- it asserts nesting of at most 64 levels.

A violated assertion is a compile error, so a change to the model-facing form that breaks
decodability fails at compile time. It has no phase 0 consumer, so its tests are structural only;
`s4.decoding-form` supplies the xgrammar result if S4 ran it (Proposed).

**The annotator reference** ports `reference()` and `card()` from `code/s0r2_inputs.py` onto
the lookup. It builds a structured document, then renders it as Markdown. The parts follow D2
§7.5:
- Entity types are listed with description, scope, identity slots and examples.
- Predicate cards are grouped by the pack's subsets.
- Each card's role and modality lines are rendered from `rules.yaml`'s `tables:`. The conditions
  line comes from the description of the subset that groups the predicate, or else from the
  `guideline:` rules that apply to it. Guideline text never enters, so the reference is a
  function of the schema version alone (Proposed).
- The shape tables are rendered from one example instance per core shape. Each example is
  validated against F2b's adapters when the reference compiles, so a shape change that the
  reference does not follow fails compilation.
- The worked examples are embedded verbatim from `reference/E*`: packet text, authored batch and
  citation frame. Each batch is validated against the model-facing adapter at compile time.
  Agent interface owns the test that its packet assembler reproduces those packets; evaluation
  reserves their pages.

The phase 0 agent and golden passes receive the whole reference (D4 §4.2). Its size in tokens is
`s4.sizes`, read for phase 1's filtering.

**Schema tables** (D2 §7.1) are rows built from the lookup and the rules file: class identity
keys from `unique_keys`, slot `subsets`, and native metaslots the design reads (`symmetric`,
`transitive`, `in_subset`) under `annotations`. They are a projection of the `tables` artifact
(§3.4).

### 3.4 Registration (P0-S-1b)

`schema.registry.ensure(conn, project, pack_path, created_by) → SchemaVersionRef`:

1. Load and hash the pack.
2. Insert the `meta.schema_version` row with `ON CONFLICT (project_id, content_hash) DO NOTHING`,
   then select it. `parent_id` is the project's latest version of the domain; `migration` is null
   in phase 0.
3. For every installed compiler and kind, insert the `meta.compiled_artifact` row if its
   identity is absent.
4. If the row exists, recompile and compare hashes. A different hash under an existing identity
   means a compiler's output changed without a version bump, and `ensure` fails, naming the
   compiler and kind. It never rewrites the row and never adds a second body (D3 §3: rows are
   added, never edited).
5. The transaction that inserts a new `schema_tables` artifact also replaces that version's
   `meta.schema_*` rows. They are a projection read for SQL joins and metrics, never a run input,
   so replacing them breaks no provenance (D3 §3 as amended).

Concurrent `ensure` calls are safe because every insert is conflict-free on its unique key and
only the inserting transaction replaces the projection (Proposed). Orchestration's pack-version
upsert calls `ensure` (`ci project init`, and `ci run` and `ci ingest` per D8 §4) and writes the
guideline version against the returned id.

`schema.registry.compiled_for(conn, schema_version_id) → CompiledSchema` rebuilds the bundle from
the stored `source`, never from disk, which may have moved on since. It checks every artifact
hash against the stored rows and refuses on a mismatch. A process whose installed compilers
differ from the run's therefore cannot act on that run with different artifacts. Compiled rules
are rebuilt this way and never unpickled (D2 §7.4). The MCP server builds the bundle once in its
lifespan; consolidation and evaluation build it once per process.

### 3.5 Rules and the rule language (P0-S-2)

**Rule-language helper** (`schema/rulelang.py`; schema-rules note L-04, L-05):
- It builds a rule-engine `Context` with `type_resolver_from_dict(types)`,
  `mapping_attribute_lookup=False` and `default_timezone="utc"`.
- Structured symbols are `OBJECT`s read through a `getattr` accessor over plain view objects.
- `tables:` become typed `$` builtins through `Builtins.from_defaults(values=…, value_types=…)`.
- Each rule is compiled in its own context, and a rule whose `context.symbols` meets
  `{now, today, random}` is refused.

Misspelled attributes, nullable misuse, wrong argument types and unknown symbols fail at
construction (Tested by probe, schema-rules note P8, 2026-10-28). Orchestration's policy `Chain`s
use the same helper, so policies and rules share one compile discipline (ADR-0018).

**Rules compiler** (D2 §7.4, D5 §8.2):
- The sections are `rules:` with severity `error` or `warning` and a declared `at:`;
  `guideline:`, which holds warnings only with `at: [batch, finalize]` fixed and belongs to the
  schema version; and the core rules (§3.1).
- `applies_to` is a predicate, a list, `subset:<name>` or `any`, resolved to a predicate set that
  indexes rules before `when` is evaluated.
- Each declared site has its own attribute type map. The batch-site map omits the
  grammar-derived attributes (a value's reading), so an `at: [batch]` rule that reads the grammar
  fails compilation instead of silently reading null. This makes D5 §8.2's "a rule that needs
  the grammar declares `at: [finalize]`" a compile-time property.
- A rule declared at both sites is compiled from one text under each site's context (Proposed).
  The alternative, compiling once and walking the AST for forbidden attributes, adds code to
  enforce what the type checker already gives.
- Rule text should not use `=~` on formula text. rule-engine regexes run on Python `re` without
  a timeout (Interface-checked, rule-engine source via Context7, 2026-10-28), so the view
  supplies token-derived attributes instead (§3.6).
- Rule ids are unique across sections and carry the pack's prefix (`core.` for core rules). The
  `grp` column records `rules` or `guideline`.

**`core.value_kind_matches_slot`** (`at: [finalize]`, warning) replaces the spike validator's
grammar-based slot check: a set read in a formula slot, a relation where a formula belongs, a
formula in a set position. It reads the finalize readings. It is a warning, not an error,
because grammar coverage is partial and a rejected agent claim would be the grammar's fault
(Proposed).

### 3.6 The view builder and the batch→candidate adapter

**Adapter.** `validate.candidates_from_batch(batch, compiled)` takes the items of a model-facing
batch that passed the conformance checks. It returns F2b's keyed candidate set: ids are local
refs and keys are null. Qualifier defaults are filled through the core models' defaults,
establishment is `stated`, and statement kinds come from `statements[]`. Math delimiters are
normalized here, so `$…$` and `\(…\)` are equivalent (D4 §4.3 step 4); the LaTeX is otherwise
kept as given. A reference to a
rejected item resolves to null, so view attributes stay nullable rather than raising. The pool
adapter is consolidation's.

**Builder.** `validate.build_views(candidates, compiled, site, readings=None)` returns one plain
view object per claim, with `functools.cached_property` attributes (schema-rules note §5):
- D5 §8.2's table: `id`, nullable `key`, predicate, subject and object (`id`, `type`, `label`,
  `symbol`, `identity`), value, qualifiers with defaults, statement, role, establishment,
  `evidence_count`, `unresolved_symbols`;
- the generic facts D5 §8.2 lists, including the attributes the `guideline:` group needs:
  - `groups`, from subsets, and `statement_kind`;
  - the flattened `condition_nodes`, `claim_refs` and `bindings`;
  - `statement_premises`: the same statement or an `assumption` statement;
  - the "given as a parameter value elsewhere" map over every predicate's `ci:param_map`
    qualifier, and the symbols a claim gives;
  - token-derived symbol facts from `core/tex.py`, such as the subject's index symbols and the
    symbol a formula of the form `x = …` defines;
- the pack's `views:` attributes.

The exact names are fixed by `s4.rules` and recorded in D5 §8.2.

Cross-claim facts are built by indexing the candidate set once. Claims are grouped by predicate
and by each `views:` match key (one or more field pairs, such as source subject to claim object),
and every view reads its group. No view scans the pool, so the finalize cost is linear in claims
(Proposed).

**Sites.**
- **Batch.** The candidates are the batch's own items: `family_params` holds only the batch's
  `has_parameter` claims (D5 §8.2), and symbols are read with `core/tex.py`, which is total and
  fast.
- **Finalize.** The candidates come from consolidation's in-memory pool, and `readings` maps
  (claim id, value path) to the grammar's (status, kind, symbols), computed by consolidation on
  the main thread. The finalize view is one evaluation over the pool as assembled, with no
  fixpoint. A claim that an `error` rule rejects in the same pass still contributes to other
  claims' views, which keeps the step deterministic and single-pass. D5 §8.2's "any status except
  `rejected`" then refers to statuses set before the pass, which phase 0 does not have (Proposed;
  open for the D5 owner).

### 3.7 Batch conformance checks

`validate.check_batch(batch_json, compiled, form, *, sentence_ids=None, canonical_text=None,
unit_ranges=None) → BatchReport` ports `code/instruments/validate.py` without its grammar calls:

- It never stops at the first error: the envelope and every item are validated separately.
- Pydantic errors at schema-owned positions (a `union_tag_invalid` on `predicate`, a
  `literal_error` on an enum) are reported under the D1 INV-03 category `unknown_schema_element`,
  at the same path. Metrics and messages then keep the categories of D4 §4.3 step 5 even though
  the per-predicate models now catch these structurally (Proposed).
- The schema-side checks, which JSON Schema cannot express (D2 §7.3), work through the entity-type
  side table:
  - subject, object and entity-valued qualifier classes against domain and range by `is_a`;
  - entity scope against `ci:scope`;
  - identity slots present and of the right class;
  - condition-predicate arity and argument class;
  - binding targets: `variable` names a local entity; `family_param` names an entity of a
    `ci:parameter_class` class; `param_of` and `param_expr_of` name a claim whose
    `ci:param_map` qualifier has the entry `param`.
- References: duplicate, unresolved and wrong-kind local refs; INV-08; condition cycles; sentence
  ids against the frame's `sN`/`cN`.
- Batch invariants: INV-01, INV-02, INV-05 and INV-06. A `supposed` claim that no condition
  references and that has no scope is rejected at submission, so the item is fixed or dropped
  before it is written (D1 §11, D5 §8.3 as amended).
- In the stored form, INV-10 checks spans against the rendition's canonical text and checks that
  each span lies inside the unit.

The report lists issues with category, code, path, message and local ref. The submission tools
compose their per-item messages from it (D8 §2.1). The report also yields the rejected items in
the `rejected` form of the `claim_proposal` payload (D3 §6.2), so metrics count them (D4 §4.3
step 5). `validate.check_authored(batch_json,
sentence_ids, compiled)` is the one entry point both submission tools call. It runs the checks,
the adapter and the batch-site rules, and returns issues and rule findings together, so
`propose_claims` and `write_golden` validate identically.

### 3.8 The M19 runner and method

`validate.run_rules(views, compiled, site) → RuleOutcome`:
- for each view, it evaluates the rules indexed under the claim's predicate for that site;
- a false `when` records nothing; a false `check` is a finding (rule id, severity, claim id,
  message);
- the outcome carries, per rule, the count of claim views it evaluated (its `when` true), as
  D4 M19 states.

At finalize, consolidation turns findings into `verification` observations that record failing
outcomes only (`refuted`, detail with rule, severity and message). It bulk-writes them, and the
counts go on the M19 task for coverage (D3 §6.2, D5 §8.1 as amended). At submission, A1 and A2
return the findings in the tool result.

`Rule.evaluate` resets thread-local state, so one compiled rule set is shared safely by the MCP
server's worker threads (Interface-checked, rule-engine source via Context7, 2026-10-28).

The method definition `validate.rules` (family `validate`, unit type `run`) implements O0's
contract. Its Config references the rules artifact by (`rules`, `rules`), which the registry
resolves per run, and its version is the runner's. Tasks of unit type `run` are never reused
(D4 §1 rule 4, D6 §4). Consolidation calls the runner inside the finalize pass; no orchestrator
worker runs it (D4 M19).

### 3.9 Failure behaviour

| Failure | Behaviour |
|---|---|
| Pack error (vocabulary, structure, lint) | `PackError` with every problem; `ci schema compile` exits non-zero; `ensure` refuses, so no run starts on a broken pack |
| Rule type error or banned builtin | Compilation fails with the rule id and rule-engine's message (D2 §7.4) |
| Compiler output changed without a version bump | `ensure` fails, naming compiler and kind (§3.4) |
| Installed compilers differ from a run's artifacts | `compiled_for` refuses that run |
| Rule raises during evaluation | At finalize, the step fails with rule id and claim key, as a defect (D5 §8.3). At submission, the runner reports a finding of severity `internal`, which the tool presents as a server-side failure, never as the author's error |
| Pathological formula at submission | Bounded: the tokenizer is linear, view attributes are linear in tokens, and no grammar or rule regex runs on formula text (P0CL-14) |
| An S4 result changes a contract | P0-S-1 and P0-S-2 are provisional until the `s4.*` records exist (coordinator §12) |

**Execution fit** (qualitative, FP-07). Compiling is per process and schema version: 25
branches built in 37 ms including the SchemaView load (Measured by probe, schema-rules note P7,
2026-10-28, indicative). A submission costs per-batch Pydantic validation of about 0.02 ms
(Measured, same note) plus linear checks and about 0.23 ms per claim for views and the eleven
guideline rules (Measured, P11). That is milliseconds per batch. At finalize the work grows with
claims × applicable rules, after indexing by `applies_to`. With the views indexed and no scans,
the phase 0 pool of a few thousand claims stays well under a second, and phase 1's 10⁴–10⁵
claims would be tens of seconds per pass by the same indicative ratio. That is acceptable beside
the rebuild, and a tighter loop per (predicate, site) is the route if it becomes material.

## 4. Ports

| Spike module | Product module | Behaviour and tests kept | Not ported (known spike defects or superseded) |
|---|---|---|---|
| `code/schema/core.yaml`, `statistics.yaml` | `domains/core/schema/core.yaml`, `domains/statistics/schema/statistics.yaml`, `rules.yaml` (from S4's native-form files) | The v0 vocabulary as S4 corrects it | List-valued annotations, `ci:examples`/`ci:identity_keys`/`ci:symmetric` as annotations (D2 §3) |
| `code/instruments/schema_lookup.py` | `schema/lookup.py` | Predicate rule fields, `is_a` over `class_ancestors`, condition-predicate arity and argument class, enum values | The `_slot_prefix` heuristic (replaced by `get_uri(…, expand=False)`); `importmap` (pack layout); `map_value_kind`'s hard-coded `Formula`/`SetExpr` (replaced by range ancestry to the `Value` base and its `t` tag); `observations()` |
| `code/s0r2_inputs.py` `reference()`, `card()`, `schema()` | `schema/reference.py` | Sections, card fields, "In the worked examples" cross-references, embedded examples | Hard-coded `STRUCTURAL`/`FORM` and `GROUP_RULES` prose (replaced by subsets, `tables:`, subset descriptions); the raw YAML merge (replaced by SchemaView); the hand-written shape table (replaced by validated shape examples). `packet()`, `FORMAT_V1` and `INSTRUCTIONS` are agent interface's |
| `code/s0r2_rules.py` | `guideline:` section of `rules.yaml` plus the view builder's generic attributes | The eleven checks and their outcomes on the v1 reference and examples | The Python checker itself; hard-coded `has_distribution`, `param_values`, `canonical_name`, `FAMILY`/`FORM` (replaced by `ci:param_map`, identity, subsets). Its outcomes survive as recorded expectations (§6) |
| `code/instruments/validate.py` | `validate/batch.py` | Categories and codes, item-by-item validation, binding-field and target checks, scope against class, identity, condition predicates, INV-01/02/05/06/08/10, cycles, sentence ids, stored spans; the 36 batch-site cases of `tests_instruments/test_validate.py` | `check_slot` and `bare_unit_formula`, which parse with the grammar at submission (P0CL-14): the slot check becomes `core.value_kind_matches_slot` at finalize, and the bare-unit check waits for M12 (phase 1); the three entity-argument forms and `as_formula` coercion; the `default_lookup` global; grammar-coverage `notes`; INV-09 marking (consumers read the condition tree) |
| `code/instruments/batch.py` | foundations (F2b) | — | — |

## 5. Packages

| Package | Scope | Prerequisites | Acceptance | Revealing failure case |
|---|---|---|---|---|
| P0-S-1 | Pack files, `.linkmllint.yaml`, `guideline.md`, `reference/E1`–`E3`, `fixtures/packs/minimal/`; loader and schema version; lookup; compilers for tables, the three batch forms and the reference; artifact identity and `CompiledSchema`; `ci schema compile`; the `core.yaml` mirror contract test | F1, F2b (F2a); finalized after S4; `fixtures/s0` files | Artifact hashes equal in two processes with different `PYTHONHASHSEED` and load paths. Each file lints clean, or every remaining finding is recorded. The twelve v1 reference batches and three examples validate in the model-facing form, and the spike's stored v1 batches in the stored form. `check_schema` passes on every exported schema, and jsonschema agrees with Pydantic on those batches and on Hypothesis draws. The mirror test fails on a seeded difference on either side. The reference carries every information item that `s4.reference-diff` lists. The decoding form passes its assertions. The minimal pack compiles | T1's `{"t": "entity", "ref": …}` object and U6's `Statement` in `entities[]` are each refused at their path, per S4's V1 and V2 outcome; a comment-only edit keeps the version hash while a description edit changes it |
| P0-S-1b | `schema.registry.ensure()`, `compiled_for()`, the schema-table projection | S1, F4 | `ensure` twice is idempotent. A bumped compiler version adds rows and leaves the old rows byte-identical. The projection is replaced in the inserting transaction. `compiled_for` from stored source reproduces every stored hash. Two concurrent `ensure` calls leave one row per identity (P0CL-15 closure) | Compiler output changed without a version bump: `ensure` fails naming compiler and kind, instead of keeping a stale body or adding a second one |
| P0-S-2 | Rule-language helper; rules compiler (`rules:`, `guideline:`, `tables:`, `views:`, `at:`, `applies_to`, core rules); view builder at both sites; batch→candidate adapter; batch conformance checks; M19 runner, `validate.rules`, `check_authored` | S1, F2b (F2a's `core/tex.py`), O0 | Every pack rule and the eleven guideline checks compile. Each compile-time error class fails construction. An `at: [batch]` rule reading a reading attribute fails compilation. The v1 reference and examples give 0 issues and 0 warnings, and every seeded violation is caught by its expected rule. The 36 batch-site validator cases give their expected category and code. A rule declared at both sites gives the same outcome on a batch and on the candidate set built from it, except `stat.param_keys_known`, which runs only at finalize. A pathological formula completes the batch site within its bound with `methods.math` never imported (P0CL-14, this document's half) | `stat.param_keys_known` evaluated at the batch site would warn on every batch whose family parameters are stated elsewhere on the page; the `at:` sites and the batch-site type map prevent it |

**P0-S-1.** Mechanisms:
- LinkML 1.12.1 `SchemaView` (`class_ancestors`, `induced_slot`, `get_uri(…, expand=False)`,
  `get_class(…).unique_keys`, `class_induced_slots` for the mirror test), with `linkml-lint` run
  per file;
- pydantic 2.14.1 `create_model`, `Field(discriminator="predicate")`, a `TypeAdapter` per form,
  `json_schema(mode="validation", schema_generator=…)` and `validate_json(strict=True)`;
- jsonschema 4.26.0 `Draft202012Validator.check_schema` and validation with a `referencing.Registry`
  of URN resources (tests);
- hypothesis-jsonschema `from_schema` (tests, §6).

The mechanisms are owned by D2 §2, §3, §7.1, §7.3 and §7.5 and the
[schema-rules note](../../design_review/evidence/2026-10-28_library-schema-rules/README.md) L-01…L-03 and
L-06…L-10. Evidence consumed: `s4.pack-lint`, `s4.schema-hash`, `s4.batch-validation`,
`s4.reference-diff`, `s4.sizes`, `s4.decoding-form` where run; `s0r2.reference-v1` (the v1
reference in both forms) and `s0r2.inputs` (guideline v1 and the hand-assembled reference).

**P0-S-1b.** Mechanisms: SQLAlchemy Core inserts with `ON CONFLICT DO NOTHING` through foundations'
repository on the D3 §3 tables. Evidence consumed: the S6 migration records as foundations cites
them for F4. No `s4.*` record is needed beyond P0-S-1's.

**P0-S-2.** Mechanisms: rule-engine 5.1.0 typed `Context`, `OBJECT` with a `getattr` accessor,
`&.`, `??`, `$all`/`$any`, positional calls, `Builtins.from_defaults`, a context per rule, and the
thread-local evaluation state. They are owned by D2 §7.4, D5 §8.2 and D4 M19, and the
schema-rules note L-04 and L-05. Evidence consumed: `s4.rules`, which fixes the view attribute
names and confirms `views:` and `tables:` on the pack's own rules (OPEN-D2-3).

## 6. Tests

| Package | What the tests establish | How |
|---|---|---|
| P0-S-1 | Determinism and identity | Hash and artifacts computed in two subprocesses with different hash seeds and absolute and relative paths; reordered YAML keys and comments give the same version, and a description edit a new one; a YAML float hashes as its decimal string |
| | Pack validity | `linkml-lint` per file with `.linkmllint.yaml`; each vocabulary error class gives a `PackError` naming the element |
| | Batch models | The v1 reference, examples and S0-R2 batches validate. The 40 spike mutation cases run against the adapters and checks: the 36 that remain batch-site keep their expectations, re-stated for the product's categories by hand from the specification, never read back from the code. jsonschema validates the same batches as an independent oracle, comparing errors sorted by `absolute_path` (D9 §4) |
| | Exported schema as an oracle | hypothesis-jsonschema states full support for drafts 04, 05 and 07 and resolves non-recursive references only (Interface-checked, project README, 2026-10-28). The test therefore draws from a derived draft-7 copy with `Condition` unrolled to depth two, and Pydantic and jsonschema both judge each draw against the full 2020-12 schema |
| | Mirror contract | Each `Value` descendant's induced slots (names, required, multivalued) and `equals_string` tag in `core.yaml` against F2b's model fields and `Literal` tags; seeded differences on either side fail it |
| | Reference | The structured reference against the information list from `s4.reference-diff` (test data authored from the S0-R2 reference); shape examples validate; the worked-example batches validate |
| | Generality | `fixtures/packs/minimal/` (one parameterized entity class, a map qualifier with `ci:param_map`, a `family_structure` subset, one `views:` entry, one rule, one example) compiles to every artifact |
| P0-S-1b | Registration | Against the per-session test database: idempotence, compiler-bump rows, projection replacement, stored-source rebuild, concurrent `ensure` from two connections, and the mismatch refusal |
| P0-S-2 | Rule compilation | One case per compile-time error class (schema-rules note P8), the banned builtins, and a reading attribute in an `at: [batch]` rule |
| | Rule outcomes | 0 warnings and 0 issues on the v1 reference and examples; the eleven seeded violations, each with its expected rule id recorded as test data from the note's P11 outcomes, independent of the rule implementation; the finalize-only rules on a candidate set with and without a family's parameters; the error rules at both sites |
| | Sites agree | For every rule declared at both sites, one batch through the batch site and through a hand-built finalize candidate set gives equal findings |
| | Bound and isolation | A formula of tens of thousands of characters with deep brace nesting completes the batch site within a fixed bound, and `corpus_structure.methods.math` is absent from `sys.modules` afterwards |
| | Linear views | A generated candidate set of 10⁴ claims builds views with every `views:` lookup served from the index, checked by counting index reads rather than timing |
| | Readings | `core.value_kind_matches_slot` and `stat.domain_is_set` on hand-made readings, including the three slot-kind cases ported from the spike validator |

Shared fixtures used, all owned by foundations: the session test database (P0-S-1b), the
`fixtures/s0` batches and frames, and the conftest's compiled-schema fixture. This document adds
a thin session-scoped fixture that compiles the statistics pack once. Test data this document
adds: the spike's stored v1 batches and the S0-R2 reference copied under `tests/data/` (copied,
never imported), the seeded violations, and the minimal pack.

## 7. Indicative size

| Part | Package | Product lines |
|---|---|---|
| Loader, version hash, rules-file model | P0-S-1 | 250 |
| Lookup | P0-S-1 | 150 |
| Tables compiler | P0-S-1 | 80 |
| Batch models, export, decoding transform | P0-S-1 | 300 |
| Annotator reference | P0-S-1 | 200 |
| Artifact identity, `CompiledSchema`, `ci schema compile` | P0-S-1 | 100 |
| Registration | P0-S-1b | 120 |
| Rule-language helper and rules compiler | P0-S-2 | 230 |
| View builder and adapter | P0-S-2 | 230 |
| Batch conformance checks | P0-S-2 | 200 |
| Runner, method, `check_authored` | P0-S-2 | 60 |
| **Total** | | about 1,920, against the coordinator's 1,900 |

The pack files, the guideline, the worked examples and tests are excluded. The batch checks are
the part most likely to shrink, because the per-predicate models already catch most of what the
spike validator checked by hand.

## 8. Choices left to implementation

- Module names inside `schema/` and `validate/`, and the split of `CompiledSchema` into lazily
  built parts.
- Whether entities are also discriminated on `type`, with per-class identity models. That would
  make identity-slot errors structural at the cost of a second union in the exported schema.
- The exact view attribute names, within what `s4.rules` and D5 §8.2 fix.
- The layout of the `rules` artifact body, provided it covers everything that shapes compilation.
- How `compiled_for` materializes stored sources so imports resolve as on disk (a temporary pack
  layout or an `importmap`), provided a stored-source build equals a disk build (tested).
- Card wording and section order of the reference, within D2 §7.5's parts and the information
  list.
- `ci schema compile` output columns and `--json` shape.
- `linkml-lint` rule levels beyond the note's list.
- The dependency split: `linkml-runtime` at runtime and `linkml` (the linter) as a dev
  dependency, since no generator is used (D2 §6, §7.3). This is pinned exactly either way.
