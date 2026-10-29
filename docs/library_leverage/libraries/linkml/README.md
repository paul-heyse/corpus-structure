# LinkML and linkml-runtime

**Realization assessed:** linkml and linkml-runtime 1.12.1, with pyoxigraph 0.5.13 (transitive) and
rdflib 7.6.0.

**Researched:** 2026-10-29 by the R3 LinkML cluster.
- Read end to end: the [linkml overview](../../../libraries/linkml.md) and the
  [extension-libraries overview](../../../libraries/linkml_extension_libraries.md).
- Read light: [PyOxigraph](../../../libraries/PyOxigraph.md), canonicalization only.
- Follow-ups: Context7 (`/linkml/linkml`; it documents current main, not exactly 1.12.1), the
  installed source, and one pure-Python probe
  ([evidence](../../../design_review/evidence/2026-10-29_library-leverage-linkml/README.md)).
- Handles use `linkml-runtime/…` where that package owns the capability.

## Reusable opportunity types

<a id="linkml-runtime-in-memory-import-closure"></a>

### `linkml-runtime/in-memory-import-closure`

**Need.** Build a SchemaView over a multi-module schema from bytes already in hand, without
filesystem or network access.

**Recognize.**
- Wrapper-root schemas written out with `yaml.safe_dump`.
- Direct `view.schema_map = …` assignment.
- Pre-checks for missing imports.

**Mechanism.** `SchemaView(root, importmap={import_string: dict})`.
- Dict values are loaded with `YAMLLoader` and never touch disk.
- Keys must match the import text exactly; CURIEs and URLs both work.
- Closure order is depth-first, leaves first (probe-observed).
- Values must be plain dicts, so already-loaded `SchemaDefinition` objects are re-coerced.
- `SchemaBuilder(...).as_dict()` produces a suitable value. Avoid `add_defaults()`, which adds an
  installed `linkml:types` import.

**Discharges.** In-memory loading, closure ordering and `from_schema` injection.

**Residual obligations** (all probe-observed):
- **Missing imports fall back silently.** An import absent from the map is loaded through
  `load_schema_wrap` from the filesystem or network.
- **`linkml:` is pre-mapped** to the installed metamodel unless overridden.
- **Duplicates are never refused.** The unmerged view lets the *last* module win, while
  `merge_imports()` lets the *first* win.
- **Merge copies are shallow.** `merge_schema` shares nested objects with its sources.
- **URIs are relabelled after a merge.** Source-relative URIs survive only on the unmerged view.
  After merging into a fresh view, `get_uri` relabels with the root's `default_prefix`, so URIs must
  be materialized before merging.

**Version.** Dict importmap values exist in 1.12.1 (installed source). The release that introduced
them was not established.

**Pattern.** [LOP-X006](../../assessment-patterns.md#lop-x006).

<a id="linkml-runtime-schemaview-lifecycle"></a>

### `linkml-runtime/schemaview-lifecycle`

**Need.** Resolve and induce a schema once, and share it among several consumers.

**Mechanism.**
- **Caching.** `@lru_cache` methods are keyed on `(schema.id, uuid, modifications)`. Only the
  supported mutators call `set_modified()`, so direct object edits leave the caches stale.
- **Induction mutates the asserted schema.** `induced_slot` shallow-copies a slot and then appends
  to the shared `domain_of`; a list went from `[]` to `['A','B']` (probe).
- **`imports_closure` writes `from_schema`** into every loaded schema.
- **Generators mutate their input.** On the SchemaView path they wrap the given `SchemaDefinition`
  without copying it, then set `metamodel_version` and clear `generation_date` (probe:
  `JsonSchemaGenerator`).
- **`materialize_derived_schema()`**:
  - deep-copies the schema;
  - builds a new SchemaView *without* `importmap`/`schema_map`, so an unmerged view would resolve
    its imports ambiently (source);
  - does not preserve constraints (see the next type).

**Residual.** Immutability is the caller's discipline. LinkML has no frozen or read-only view, and
the mutations are idempotent but order-dependent.

<a id="linkml-runtime-type-chain-traversal"></a>

### `linkml-runtime/type-chain-traversal`

**Need.** Walk a datatype's `typeof` chain to derive its primitive, bounds and patterns.

**Mechanism.**
- `type_ancestors(name)` returns the ordered chain `[self, parent, …, primitive]` (probe).
- It follows `typeof` with strict lookup, so an undeclared primitive raises `ValueError`.
- Cycles end silently unless `detect_cycles=True` is passed.

**Semantics are not conjunctive** (probe-observed):
- `induced_type` lets the most specific value win. A child's pattern *replaces* the parent's, and a
  looser child minimum beats the parent's bound.
- `induced_slot` combines slot-level bounds but does not fold in the range type's bounds.
- `materialize_derived_schema` overwrites a slot's own pattern with the range type's pattern.

**Residual.** Any policy that needs the conjunction of all constraints, or the tightest bound.

<a id="linkml-runtime-reference-normalization"></a>

### `linkml-runtime/reference-normalization` (negative result)

**Need.** Uniqueness of identifiers within a document, and resolution of class-ranged, non-inlined
references.

**Finding.**
- `ReferenceValidator` normalizes collection forms and checks required/recommended slots, closed
  classes, types, enums, patterns and rules.
- `normalize_reference` only coerces a reference's value to the identifier type.
- There is **no object index, no dangling-reference check and no uniqueness check.** The probe
  returned no results for a dangling `ref:missing` or a duplicated `ref:a`.

**Other routes.**
- **SHACL `sh:class` through `ShaclValidationPlugin`.** It needs a generated module, an RDF dump and
  pyshacl. Duplicate identifiers merge silently into one RDF subject.
- **linkml-store integrity checks.** A separate package, not installed, and scoped to collections.

**Residual.** A small in-document integrity pass. SchemaView makes it cheap to write generically
with `class_induced_slots`, `induced_slot(...).range`, `get_identifier_slot` and `is_inlined`.

<a id="linkml-runtime-rdfc-canonical-serialization"></a>

### `linkml-runtime/rdfc-canonical-serialization`

**Mechanism.** `canonicalize_rdf_graph(graph, "nt")`:
1. rdflib serializes to N-Triples;
2. `pyoxigraph.parse` reads it back;
3. `Dataset.canonicalize(RDFC_1_0)` relabels blank nodes;
4. the triples are sorted, a step upstream describes as load-bearing;
5. `pyoxigraph.serialize` writes the result.

**Fallbacks.** Each one emits `RDFCanonicalizationWarning`.

**What determines the bytes.** linkml-runtime, rdflib, pyoxigraph and the graph producer.

**Version condition.** pyoxigraph 0.5 enables preliminary RDF 1.2 parsing by default.

<a id="linkml-runtime-structured-annotation-values"></a>

### `linkml-runtime/structured-annotation-values`

**Mechanism.** `Annotation.value: Union[dict, Any]` and nested annotations (probe-observed):
- list values load as lists;
- a mapping must sit under an explicit `value:` key and loads as `JsonObj`, which uses attribute
  access rather than dict access;
- a bare mapping is rejected;
- nested annotations load;
- `json_dumper` round-trips all of these.

**Residual.** Typed validation of the structure, and a reader that does not stringify values.

## Applicability at source `d739b88` (read through `6b2335a`)

<a id="applicability-cbo-002"></a>

### CBO-002 — product release composer: **fits with conditions; premise updated**

**Opportunity:** [CBO-002](../../codebase/release-preparation.md#cbo-002).
**Type:** [in-memory-import-closure](#linkml-runtime-in-memory-import-closure).

**Premise update.** A composer now exists. `semantic/regeneration.py:prepare_pack` (commit
`2c00ab9`, after the codebase baseline) chains the layer helpers and `prepare_release`. It still
nests wrapper roots, and the private `_view` idempotence check still runs on this path.

**Fit.** One synthesized root whose ordered `imports` list covers domain, observations, agent and
analytics, combined with importmap dicts, can express every current schema-side layering in a
deterministic order.

**The codebase keeps:**
- its own duplicate refusal, since LinkML's view and merge disagree on which duplicate wins;
- its missing-import pre-check, including refusing `linkml:` unless that key is supplied;
- URI materialization before merging.

**Mismatch.** importmap takes dicts, while URI materialization operates on loaded objects. The
current `schema_map` seeding avoids a second coercion.

**Agent module.** `SchemaBuilder` adds little over the three targeted dict edits, and switching to
it would change archived bytes.

**Companion inputs as LinkML.** The capability exists. Local fit is unsettled, because cross-record
references still need the residual integrity pass and domain rules are authored text.

<a id="applicability-cbo-021"></a>

### CBO-021 — SchemaView lifecycle: **fits with conditions; `materialize_derived_schema` ruled out**

**Opportunity:** [CBO-021](../../codebase/release-preparation.md#cbo-021).
**Types:** schemaview-lifecycle, type-chain-traversal.

**Imports.** importmap is the supported import route. Direct `schema_map` assignment also works,
because `imports_closure` skips keys that are already present. Neither removes the pre-checks.

**Ruled out.** `materialize_derived_schema()` loses conjunctive constraints, overwrites slot
patterns and needs a merged view. This reinforces the reasoning behind superseded
[ADR-0020](../../../adr/0020-one-model-generated-projections.md).

**Viable shape.** One merged, materialized `SchemaDefinition` per preparation, induced once and
treated as immutable by convention.
- The OWL/SHACL scope projection keeps its own deepcopy, because it rewrites the schema.
- **Residual:** the immutability discipline and the order of induction. OWL input currently depends
  on whether induction has already populated `domain_of`.

<a id="applicability-cbo-017"></a>

### CBO-017 — execution catalog: **ReferenceValidator ruled out for integrity; generators unsettled**

**Opportunity:** [CBO-017](../../codebase/release-preparation.md#cbo-017).

**Integrity.** `ReferenceValidator` checks neither dangling nor duplicate references. Moving the 87
`range: string` references to class ranges gains integrity only if the compiler adds a generic pass.
That pass would also serve SP-08 domain inputs.

**Generators.**
- `gen-python` emits mutable, coercing `YAMLRoot` dataclasses.
- `PydanticGenerator` has templates but no frozen option was found.
- Either would mean checked-in generated output ([LOP-X002](../../assessment-patterns.md#lop-x002)).
- Unsettled. The cattrs side is covered in the [cattrs account](../cattrs/README.md#applicability-cbo-017).

<a id="applicability-cbo-009"></a>

### CBO-009 — identity library set: **fits with conditions**

**Opportunity:** [CBO-009](../../codebase/release-preparation.md#cbo-009).
**Type:** rdfc-canonical-serialization.

**Libraries that change prepared bytes:**
- linkml (generators);
- linkml-runtime (SchemaView, registry `json_dumper`, RDFC);
- rdflib and pyoxigraph (graph bytes);
- pydantic (JSON Schema artifacts; it exact-pins pydantic-core);
- PyYAML (parsing and `safe_dump`).

**Libraries that affect acceptance only:** jsonschema, cattrs, rule-engine (policy compile during
preparation) and pyshacl.

**Libraries that shape vocabulary snapshots:** oaklib, linkml-term-validator and pronto/fastobo.
**Pronto is missing from the current set.**

**Deriving the set.**
- `importlib.metadata.version` and `packages_distributions()` can enumerate the candidates.
- They cannot tell which libraries change bytes, so the set remains a deliberate constant with a
  single owner.
- Exact pinning of pyoxigraph is ordinary policy.

<a id="applicability-cbo-008"></a>

### CBO-008 (informs) — structured physical annotations

**Type:** [structured-annotation-values](#linkml-runtime-structured-annotation-values).

1.12.1 loads lists, mappings under `value:` and nested annotations. However, `ci_annotations`
stringifies values that are not bool or int, so moving `ph:*` off JSON strings needs a typed reader.

<a id="applicability-cbo-013"></a>

### CBO-013 (informs) — range meaning

**Type:** [type-chain-traversal](#linkml-runtime-type-chain-traversal).

`type_ancestors`, with `detect_cycles=True` and a mapped `ValueError`, can be the shared traversal.
`induced_type` and `materialize_derived_schema` cannot replace the conjunctive `_bounds`. For
prefixes, see [curies](../curies/README.md#applicability-cbo-013).

## Coverage limits

- Not inspected: generator output after URI relabelling.
- Not probed: the SHACL `sh:class` route.
- Not exercised: PydanticGenerator and gen-python on the catalog.
- No cost measurements were made.
