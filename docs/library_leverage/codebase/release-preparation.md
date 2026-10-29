# Release preparation and the prepared-release contract

Opportunities in composing, compiling, reloading and consuming semantic releases. A release binds
local LinkML sources, ontology artifacts, rule profiles and compiler versions into one immutable
`PreparedRelease` ([ADR-0024](../../adr/0024-semantic-release-preparation.md)). Baseline, scope and
labels are in the [README](README.md). Paths are relative to
`python/corpus-structure/src/corpus_structure/` unless they start with `python/` or `docs/`. Line
numbers cite the reconciled tree at `f697233`.

Strengths that bound these opportunities:
- **Strict, explicit-input preparation.** The metamodel allowlist `_inspect` (`semantic/prepare.py:197`)
  runs before LinkML can coerce or ignore fields. Diagnostics carry locations. There are no network
  or installed defaults.
- **The custom Pydantic compiler** encodes semantics that LinkML's `pydanticgen` lacks: constraint
  scopes, conjunctive patterns, keyed-collection checks, `kind`-discriminated abstract ranges and
  frozen strict configuration. The rationale from superseded
  [ADR-0020](../../adr/0020-one-model-generated-projections.md) still holds.
- **Conditional rules** use public JSON Schema generator hooks and one compiled `jsonschema`
  validator per class, so predicate meaning has a single owner.
- **RDF canonicalization** is delegated to LinkML's RDFC path, which replaced a local implementation
  (see the [SP-06 execution-fit evidence](../../design_review/evidence/2026-10-29_sp06-execution-fit/README.md)).
- **The execution catalog's implementation and native-guard allowlists** are trust boundaries, and
  cattrs runs with `forbid_extra_keys` and detailed validation.

<a id="cbo-002"></a>

## CBO-002 — No product release composer; layering uses two unrelated mechanisms

**Label:** accepted planned (SP-09's "prepares a release" step; SP-08 consumers). **Altitude:**
subsystem.

**Operation and consumer.** Build the release a realization runs under: domain modules, then the
observation, agent and analytics layers, then metrics, domain rules and execution contracts. The
consumers are the
[SP-09](../../plans/semantic-model-pivot/regeneration-and-acceptance.md#SP-09) reproducible command
path, the SP-08 CLI and MCP, and every native test.

**Current mechanism.** No production code composes a release. In `src`, `prepare_release(` is called
only for the contract companion (`semantic/contracts.py:651`) and on reload
(`semantic/releases.py:444`). Callers compose through two unrelated mechanisms.

- **Schema-side layers synthesize a wrapper root in Python.** Each wraps the previous root plus one
  module and dumps it with `yaml.safe_dump`:
  - `semantic/observations.py:28`, which calls the private `prepare._view` to test idempotence;
  - `semantic/proposals.py:33`, which runs a full `preview_schema` (`:45`) and edits the loaded
    agent model dictionary in place;
  - `semantic/analytical_profile.py:19`.

  Root names differ with layering order, so release identity depends on the recipe.
- **Dependency-side layers are reserved-name artifacts.** `prepare` dispatches on their names
  (execution inputs, analytical profile, domain rules, metrics, rules-policy admission), and
  consumers look them up by name.
- **Validation differs per artifact:**
  - metrics and the analytical profile cross the LinkML-derived Pydantic boundary;
  - the execution catalog goes through Pydantic, cattrs and hand checks ([CBO-017](#cbo-017));
  - domain-rules YAML gets an `isinstance(dict)` check plus hand source validation.
- **Three loaders handle LinkML's location-tagged YAML strings:** `_SchemaYamlLoader`
  (`prepare.py:250`), the contracts unwrapping (`contracts.py:346-354`) and a domain-operations
  variant.

The test audit diagnosed the test-side consequence:
[DTA-005](../../design_review/test-audit/support-structure.md#dta-005), where 18 modules each
assemble their own recipe.

**Why it matters.**
- SP-09 needs one command that prepares the release. SP-08 consumer tests need the composition the
  product uses.
- Adding a release-bound input today means editing a composer helper, a `prepare` branch, an
  archive rule and a consumer lookup, with no shared contract.

**Patterns.** LOP-12, LOP-02 (adding an input kind needs parallel edits), LOP-09 (three validation
routes), LOP-03 (dictionary edits where LinkML offers an API).

**Preservation constraints.**
- Pure preparation with explicit inputs and no installed or filesystem defaults (ADR-0024).
- Refusal of reserved names, and every input archived and hashed.
- Identity covers every input byte. Changing composition changes ids; that is acceptable under clean
  regeneration but must be deliberate.

**Counterevidence.**
- Each layer helper is a single owner.
- The agent module is genuinely computed from the candidate release (entity classes, predicates,
  statement kinds).
- Minimal test releases may be deliberate.

**Research leads.** [linkml](../../libraries/linkml.md): linkml-runtime 1.12.1 `SchemaView`
accepts an `importmap` of in-memory schema dictionaries, loaded without filesystem or network
access (seen in the installed `schemaview.py`; not yet assessed). Also one synthesized root with an
ordered import list, and `SchemaBuilder` for the agent module.
[linkml_extension_libraries](../../libraries/linkml_extension_libraries.md).

**Questions for library research.**
1. Can one root schema with ordered imports plus importmap dictionaries express every current
   layering while keeping duplicate refusal and the materialization of source-relative URIs?
2. Should companion inputs (rules, metrics, profile, execution) be LinkML-declared and cross one
   validation boundary?

**Related.** [CBO-004](engineering-workflows.md#cbo-004) (command path);
[CBO-021](#cbo-021) (SchemaView import seeding);
[DTA-008](../../design_review/test-audit/support-structure.md#dta-008).

<a id="cbo-003"></a>

## CBO-003 — Every read session rebuilds and re-verifies the immutable release

**Label:** current; intensified by accepted planned SP-08 serving. **Altitude:** component with
reach across consumers.

**Operation and consumer.** Turn an archived release id into a usable, verified `PreparedRelease`.
Callers:
- every read and explain session (`semantic/query.py:345`);
- cut materialization (`semantic/domain_operations.py:705`);
- `orchestrate/commands.py:344` and `orchestrate/project.py:320`;
- activation.

**Current mechanism.** `load_release` (`semantic/releases.py:391`) does all of this on every call:
- reads every archived input;
- re-runs `prepare_release` (`:444`), which means SchemaView, `create_model` per class, per-class
  JSON Schema, conditional rules, OWL and SHACL generation with RDF canonicalization, and the rules
  policy;
- checks library versions exactly (`:442`);
- re-reads every `sem.*` projection row and compares canonical bytes (`_compare_rows`, `:279`).

The only reuse is the process-lifetime `lru_cache(8)` (`prepare.py:573`). Each new CLI process,
which is SP-08's normal shape, pays cold preparation plus a full archive comparison. Consumers have
started their own caches: the semantic MCP server keeps a per-session `self.prepared` under a lock
(`intervene/semantic_server.py:59-66`).

Several prepared artifacts have no production reader: the OWL and SHACL graphs
(`semantic/ontology.py:227-235`) and the per-class `json_schema/{name}` artifacts
(`prepare.py:905`). Consumers call `prepared.json_schema()` instead.

**Why it matters.**
- Every SP-08 query, explain or MCP request would pay full reconstruction and comparison for an
  immutable release.
- Consumer-local caches will multiply, each with its own invalidation rules.
- SP-10's "immutable archival products persist" and "release-sensitive reuse" evidence runs through
  this route.

**Patterns.** LOP-07 (verification repeated within a longer valid lifetime; preparation without
demand), LOP-09 (consumer-local caches), LOP-05.

**Preservation constraints.**
- Exact reconstruction and tamper refusal at the trust boundary (ADR-0024 and
  [ADR-0025](../../adr/0025-semantic-publication.md)).
- OWL and SHACL bytes are archived and compared, so making them lazy changes the archive format.
- Never infer validity from an unchanged label.
- The test audit's [DTA-007](../../design_review/test-audit/evidence-and-discrimination.md#dta-007)
  shows the process cache already hides cold-reload behaviour. A reuse design must not deepen that.

**Counterevidence.**
- Full re-verification is a deliberate integrity property. Who can mutate `sem.*` rows (the
  migration owner, not the publisher) decides how long a verification remains valid.
- SP-08 schema or export commands might become consumers of the OWL, SHACL or JSON Schema
  artifacts; no plan text says so.
- The cost is unmeasured.

**Research leads.** Mostly not a library question. Candidates are a native verification record
keyed by release id and content digest, a digest-keyed in-process reuse scope, and
[pydantic](../../libraries/pydantic.md) `models_json_schema` for one shared-`$defs` schema.

**Questions for library research.**
1. Which reload checks are needed once per release and process, and which on every session?
2. Does any SP-08 consumer need the OWL, SHACL or per-class JSON Schema artifacts?

<a id="cbo-009"></a>

## CBO-009 — Identity dependency sets are hand-chosen, duplicated and have drifted

**Label:** current; an operational risk for accepted planned SP-09 cutover. **Altitude:** function
with system effects.

**Operation and consumer.** Release identity and run manifests record which library versions can
change their results. `load_release` refuses when the set differs.

**Current mechanism.**
- The 11-name release list exists twice, in different orders: `semantic/prepare.py:414-426` and
  `semantic/releases.py:30-42`. The manifest is rebuilt independently on validation, and
  `load_release` refuses on any inequality (`releases.py:442`).
- The list does not match what actually affects compilation:
  - **pyoxigraph** is a member but is undeclared and unpinned. It arrives transitively through
    linkml-runtime and is the RDFC engine behind graph canonicalization.
  - **valuesets** is declared and listed, but never imported in `src`.
  - **PyYAML** (source parsing) and **rule-engine** (admission compile) are absent.
- The run manifest maps methods to libraries by hand (`orchestrate/semantic.py:130-139`).
  `extract.math` and `normalize.formula` add only `lark`, yet `methods/math/grammar.py:65-66` imports
  SymPy and its LaTeX Lark grammar. SymPy changes extraction output but is missing from the
  manifest.

**Why it matters.**
- After SP-09 cutover, any lock bump of a listed library, including a transitive pyoxigraph bump,
  makes the active release unloadable. Because `read_session` calls `load_release`, serving stops
  until the release is re-prepared and re-activated.
- If the two lists drift apart, every load fails.
- Run reproducibility claims rest on a manifest that already omits a determinant.

**Patterns.** LOP-09, LOP-02, LOP-07 (its countercondition: never infer validity from an unchanged
label).

**Preservation constraints.**
- Compiler versions in the release digest are documented
  (`docs/plans/semantic-model-pivot/semantic-model-and-releases.md`).
- Declared dependencies are exactly pinned (repository policy), and `docs/pins.md` holds remain.

**Counterevidence.** Binding the full transitive closure would invalidate identities on every patch
bump. The determinants have to be chosen deliberately.

**Research leads.** Python `importlib.metadata` (`requires`, `packages_distributions`) to derive the
set; declaring and pinning pyoxigraph ([PyOxigraph](../../libraries/PyOxigraph.md));
[valuesets](../../libraries/valuesets.md).

**Questions for library research.**
1. Which libraries actually change prepared bytes or run outputs?
2. What is the intended operator route when a library bump strands the active release: re-prepare
   under SP-09, or a recorded hold?

<a id="cbo-013"></a>

## CBO-013 — The prepared-release contract leaves range meaning, adapters and name maps to consumers

**Label:** current; multiplied by accepted planned SP-08 consumers. **Altitude:** component (the
product contract).

**Operation and consumer.** Consumers ask the prepared release for typed lookups: a property's
native range, item adapters, enum members, prefix expansion and compaction, metric definitions.
The consumers are publication, consolidation, domain operations, proposals, query and the coming
SP-08 readers.

**Current mechanism.**
- **Native range is rederived.** `PropertyDefinition` carries only the range name.
  `publication.native_constraints` (`semantic/publication.py:387`) re-walks the archived type rows to
  find the native range, with an alias map duplicated from `prepare.py`. Despite promising "once per
  release projection", it is called per property value in `domain_operations.py:435`, and also in
  `proposals.py:205` and `releases.py:152`.
- **Adapters are rebuilt per call.** `property_adapter` builds a new `TypeAdapter` on each call and
  reads the private `adapter._type` (`semantic/types.py:275-281`). It is called per item by
  consolidation, domain operations and proposals; only `query.py` caches it.
- **Name lookups scan and re-parse.**
  - `expand_name` (`types.py:176`) and `enum_members` (`:189`) scan registry rows linearly and parse
    JSON on every call.
  - `metric_definitions` (`semantic/metrics.py:27-29`) decodes registry rows on each validation.
  - `domain_operations.py` has eight `json.loads(row.body)` calls, one inside a per-fact scan.
  - It also has two separate `compact()` implementations (`:816`, `:2539`).
- **Range meaning is resolved by five independent type walks:**
  - `_primitive` (`prepare.py:348`) and `_bounds` (`:379`);
  - `_is_string` (`semantic/conditional_rules.py:126`);
  - `carrier_range` (`semantic/ontology.py:148`);
  - the post-preparation walk in `native_constraints`.

  Consumers also keep their own range-to-type maps (proposals; the rule policy's `qtypes`).

**Why it matters.** Every new SP-08 reader adds another re-derivation. This is also where
native-range semantics can drift; the test audit's
[DTA-008](../../design_review/test-audit/support-structure.md#dta-008) shows publication tests
exercising a `native_range` fallback that production never takes.

**Patterns.** [LOP-X004](../assessment-patterns.md#lop-x004), LOP-07, LOP-09, LOP-10 (private
`_type`), LOP-03 (partial; SchemaView type traversal).

**Preservation constraints.**
- The release is frozen and immutable.
- Strict validation semantics.
- `registry_rows` bytes are archived; derived indices must not enter identity unless that is
  deliberate.
- `_bounds` deliberately takes the *conjunction* of every pattern and the tightest bound along the
  type chain. SchemaView's `induced_type` lets a child's pattern override its parent's, so it cannot
  simply replace `_bounds`. `type_ancestors` could serve as the shared traversal.
- Prefix resolution uses only prefixes archived with the release, never installed namespaces, with
  longest-namespace compaction.

**Counterevidence.** Each lookup is cheap alone. No hot path has been measured.

**Research leads.** [pydantic](../../libraries/pydantic.md) (build `TypeAdapter`s once per field);
[linkml](../../libraries/linkml.md) (`SchemaView.type_ancestors`); `curies`, installed transitively,
for a `Converter` built from archived prefix rows (no overview page).

**Questions for library research.**
1. Which derived facts should preparation emit once: native range, per-property adapter,
   name/IRI maps, metric definitions, a resolved range record?
2. Does a `curies.Converter` built from archived rows match current expansion, compaction and
   refusal of unknown prefixes exactly?

**Related.** [CBO-016](consumers-and-operations.md#cbo-016) (instance traversal).

<a id="cbo-017"></a>

## CBO-017 — The execution catalog is a second structural form with hand-written reference integrity

**Label:** current; accepted planned SP-08 adds operation and implementation bindings.
**Altitude:** component.

**Operation and consumer.** Compile the code-owned execution catalog (`model/semantic/contracts.yaml`
and its execution model) into typed products used by admission and operations.

**Current mechanism.**
1. The companion LinkML schema is prepared, and the catalog is validated by Pydantic
   (`semantic/contracts.py:650-658`).
2. The result is dumped, and absent collections are patched by `_collection_defaults` (`:609`).
   That patch exists because optional multivalued slots compile to `MISSING` and `ifabsent` is
   unsupported.
3. cattrs structures it into about 20 hand-written frozen dataclasses that mirror the classes in
   `contracts.yaml`.
4. `_validate` (`:403-606`) runs.

Much of `_validate` is generic id uniqueness and reference resolution (`_index`, `_refs`;
`:357-364`). That would be expressible as class-ranged, non-inlined references, but `contracts.yaml`
uses `range: string` (87 occurrences). Even with class ranges, the compiler lowers a non-inlined
class range to `str` without checking the reference.

**Why it matters.** SP-08 bindings add operations and implementations, so each addition passes
through four forms and hand reference checks.

**Patterns.** LOP-02, LOP-03, LOP-01 (reference-integrity kernel).

**Preservation constraints.**
- The approved-implementation registry and native-guard allowlist are trust boundaries; module
  strings are never authored in the catalog.
- Lifecycle, terminal and outcome invariants are domain rules.
- Consumers need typed static products.
- cattrs was selected by the pivot.

**Research leads.** `linkml_runtime` `ReferenceValidator`; whether it checks dangling references is
unverified. LinkML generators for a trusted, code-owned schema; ADR-0020's rejection concerned domain
releases. [linkml](../../libraries/linkml.md),
[msgspec/attrs/cattrs](../../libraries/msgspec_attrs_and_cattrs.md).

**Questions for library research.**
1. Should the release compiler check in-document references for non-inlined class ranges? That
   would also serve SP-08 domain inputs.
2. Could the static product dataclasses be generated from `contracts.yaml`?

<a id="cbo-021"></a>

## CBO-021 — The compiler works against SchemaView's lifecycle

**Label:** current. **Altitude:** component.

**Operation and consumer.** Resolve and induce the schema once per preparation for the Pydantic
compiler, the conditional-rule generator and the OWL/SHACL projection.

**Current mechanism.**
- **Import seeding.** `prepare.py:329-345` assigns `view.schema_map` directly (`:338`), with CURIE
  or URL keys although SchemaView annotates them as NCNames. It then calls `imports_closure()` and
  `merge_imports()`, and builds a new SchemaView over the merged result.
- **Defensive copies.** SchemaView induction mutates its source ("induced-slot resolution can
  populate domain_of"). Each preparation therefore builds several private views, each recomputing
  induced slots:
  - a deep copy for the ontology projection (`semantic/ontology.py:140-141`);
  - another for conditional rules;
  - the generators' internal views.
- **Extra previews.** `proposal_inputs` runs a full preview, and `observation_inputs` may run
  `_view` again.

**Why it matters.** Preparation time and fragility grow with every consumer view. The supported
in-memory import route may make seeding unnecessary. This relates to [CBO-002](#cbo-002), which
shares the importmap lead.

**Patterns.** LOP-10, LOP-07.

**Preservation constraints.**
- No filesystem or network fallback.
- Refusal on a missing import.
- Source-relative URI materialization before merging.

**Counterevidence.** The copies are correct defences against a real upstream mutation hazard.

**Research leads.** [linkml](../../libraries/linkml.md): `importmap` dictionaries and
`SchemaView.materialize_derived_schema()`.

**Question for library research.** Can one derived, read-only schema built once per preparation
serve all three consumers, given that the generators take a `SchemaDefinition`?

<a id="cbo-024"></a>

## CBO-024 — The ontology path works around enum composition order and reparses ontologies

**Label:** current capability, exercised only by tests. No production model uses dynamic enums.
**Altitude:** function. Low pivot priority.

**Current mechanism.**
- Enum composition is written by hand because "Term Validator 0.4.5 applies minus before
  inherits" (`semantic/ontology.py:263`).
- Meaning checks construct adapters and plugins per source and per enum, reparsing ontologies.
- Ontology bytes are written to a temporary directory because OAK parses from a path (`:656`).

**Patterns.** LOP-11 (revisit when the validator's order changes), LOP-07.

**Research leads.** [oaklib](../../libraries/oaklib.md),
[linkml_extension_libraries](../../libraries/linkml_extension_libraries.md).

**Question for library research.** Does a newer linkml-term-validator compose `minus` over the full
union, and can OAK adapters be built from in-memory bytes?
