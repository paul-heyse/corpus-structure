# Semantic model, ontology and releases

**Status:** Implemented; scoped acceptance passed (2026-10-29) · **Created:** 2026-10-29 · **Target accepted by ADR-0024; implementation evidence is bounded below.** [Coordinator](../semantic-model-pivot_2026-10-29.md) owns package state and shared scope. Consumes review O01/O02/O04; supplies every other supporting plan.

## Target and foundation

Replace installed-model-only interpretation with an admitted immutable semantic binding. Reuse `schema/model.py`, `pack.py`, `lookup.py`, `batches.py` and `registry.py`, but eliminate their assumption that every runtime must interpret a release through the newest installed model. A prepared binding carries normalized definitions, validators, query mappings and exact dependencies; it need not create a new service or framework.

The domain model has entity identity, class membership, assertion occurrences, semantic facts, qualification, recursive typed values, evidence, coverage and derivation. Stable system types remain model-generated. New domain class/property declarations become data and boundary schemas over those types. Local meanings are authored in LinkML; pinned external ontologies own their terms; the admitted model owns the selected mappings and executable axiom scope.

### Pydantic realization of the LinkML contract

Use generated or dynamically built Pydantic boundary models as a lowering of the admitted LinkML definitions. Reuse existing `schema/batches.py` strict `TypeAdapter.validate_json` and discriminated unions. `BaseModel`/`Field`, `create_model`, validators, serializers and `json_schema` provide the runtime bridge; cache adapters with the binding, not per item. Stable system envelopes may be generated statically; dynamic domain definitions do not require importable regenerated Python modules.

Derive range, aliases, requiredness, multiplicity and missing/null policy from one normalized definition. Avoid independently hand-authoring a Pydantic domain model alongside LinkML. Structural generation does not automatically implement ontology membership or relational constraints; those have explicit term-validator/publication owners. Intentional coercions must be declared lossless boundary translations; canonical scientific values cannot silently change type or precision. Immutable model configuration does not deeply freeze nested mutable containers: use frozen structural products or controlled copies for shared bindings.

Acceptance covers strict JSON/Python differences, serialization aliases, absent/null/default distinctions, recursive values, rejected extras and schema diagnostics. JSON Schema generation and serialization round trips alone do not establish semantic correctness. Sources: [Pydantic overview](../../libraries/pydantic.md), [dynamic models](https://docs.pydantic.dev/latest/concepts/models/#dynamic-model-creation), [TypeAdapter](https://docs.pydantic.dev/latest/concepts/type_adapter/).

### Identity and interpretation contract

An occurrence key is derived from realization, release, stable source-observation/publication identity and item path/ordinal. Retry reuses that identity; two separate items from the same source remain two occurrences. Do not use database sequence IDs as reproducible source identity. A fact key is derived separately from release, realization and canonical subject/predicate/object plus meaning-bearing qualification. Evidence support and confidence are not fact identity; attribution remains identifying when it changes meaning. Fusion links occurrences to facts and assessments instead of replacing the occurrence rows with one canonical dump.

Class membership has an establishment kind and support. A range can be satisfied by declared class-hierarchy entailment under the binding, not by arbitrary ontology edges. Unknown membership stays unknown; ontology labels/equivalence mappings do not automatically merge entity identities. Domain algorithms retain explicit identity-resolution and cannot-link semantics.

Represent quantity/unit, interval, ordered/n-ary roles, expression, collection and structured values deliberately. Separate absent, explicit null, unknown and not-applicable where behavior depends on them. Store exact numeric meaning independently of any bounded analytical projection. Every constraint declares whether it governs submitted shape, occurrence, selected accepted value, or an attribution/context-specific projection. Cardinality one must not prohibit multiple disagreeing sources from being recorded.

A release digest covers a deterministic sorted manifest of exact source/import/ontology bytes, resolved memberships, prefix interpretation, semantic policy and compiler versions. Formatting changes may change this content identity; it is not a proof of semantic inequality. Runtime artifact identity additionally includes its compiler/version/options. A data snapshot identifies facts separately. Prepared lookups never consult live mutable ontology endpoints.

<a id="SP-00"></a>
## SP-00 — Decisions and supported execution profile

**Input:** coordinator RC01–RC04 confirmations and current D1–D8/ADR owners. **Owner:** model/architecture integration.

Write the superseding/amending ADRs and owning architectural sections required by those impacts before implementation depends on the changes. Preserve PostgreSQL authority, evidence fidelity and explicit model authority while replacing incidental claim/key/storage forms. Apply the existing review cadence for changed §B boundaries; plan authoring itself neither starts a broad audit nor counts as that future review.

Select the initial profile: named classes/properties and hierarchy, declared typed ranges, applicability, required/min/max cardinality in a declared scope, explicit identity/uniqueness, patterns/numeric bounds, pinned enum memberships, qualified inverse/symmetric/positive-transitive inference. Unsupported required integrity constructs refuse activation; descriptive external axioms outside the admitted scope remain available as unexecuted metadata. No general OWL DL or arbitrary expression compiler is promised.

Check exact current pins (LinkML/runtime 1.12.1, SQLAlchemy 2.1.5, psycopg 3.3.6, psycopg-pool 3.3.3, Alembic 1.20.0, Pydantic 2.14.1, Arrow 26.0.0, DuckDB 2.0.0) against Python 3.14.10 and select exact additional ontology dependencies. Start from overviews then Context7/primary/installed source for consequential APIs. Resolve actual compatibility gaps with deliberate narrow dependency changes, not a wholesale lock refresh. `just ready` follows dependency changes.

**Completion:** decisions and profile are concrete enough to implement each admitted construct and refusal; dependency disposition identifies tested versus source-inspected compatibility. An unsupported essential construct blocks its dependent package until a mechanism or explicit target decision resolves it. No generic compatibility layer is the default fallback.

<a id="SP-01"></a>
## SP-01 — Model compiler, ontology preparation and binding

**Input:** SP-00. **Owner:** `core` and `schema`; one writer owns shared model/generated surfaces.

Author the stable concepts and local application ontology mappings in LinkML. Use `SchemaDefinition`/`SchemaView` and induced slots for inheritance/import resolution. Compile immutable typed definitions into queryable registry row products and dynamic boundary schemas; Pydantic `create_model`/`TypeAdapter` can reuse the existing batches approach. Do not execute generated Python for each discovery or add a parallel schema language.

Prepare required ontology artifacts through a local pinned OAK adapter. Use enum `meaning`, `reachable_from` and explicit composition for vocabulary definitions, materializing admitted memberships once. Valuesets supplies suitable vocabulary definitions, not an unconditional dependency on its entire catalog. Term Validator's `PermissibleValueMeaningPlugin`, `DynamicEnumPlugin` and applicable binding validation supply checks; reject unsupported required enum expressions such as unimplemented full `matches`. Record unchecked metadata separately from membership, including offline Not4Curation limitations. Failure to acquire required dependencies prevents activation.

Generate local OWL and SHACL projections only from their authored authority; retain complete external ontology artifacts while declaring which axioms govern executable behavior. RDFLib assertion resources preserve qualifications and occurrence identity; do not emit every source claim as an unconditional triple. PySHACL checks explicitly scoped projections with inference disabled by default; required database integrity rules also need SP-03 enforcement. Named graphs alone do not implement qualification.

Inputs are candidate sources, expected parent and resolved dependencies. Outputs are immutable prepared binding/artifacts or located diagnostics. Preparation is pure after acquisition. SP-02 persists/activates these outputs; SP-01 does not secretly mutate a database. Admission status distinguishes draft/preparation failure from a published release. A project activation pointer is separate from release identity and uses expected-parent conflict detection.

**Acceptance:** independent fixtures for occurrence/fact keys, repeated same-source items, hierarchy/multi-class ranges, units/missingness, nested references, incompatible constraints, namespace collisions and unsupported constructs. Admit a new class/attribute/relation without generating import modules. Independently authored RDF expectations challenge qualified mapping; a round trip alone is insufficient. Changed ontology membership/policy changes binding/reuse dependencies even with identical source documents.

## Mechanisms and alternatives

Reuse existing frozen lookup/dynamic validators before adding wrappers. Generate relational metadata from SP-01 mappings under the [PostgreSQL plan](postgresql-and-publication.md), not from ad hoc per-domain SQL names. LinkML SQLStore/DDL generators are not assumed to supply runtime admission or migrations. LinkML-Datalog is deferred until a required rule exceeds the selected profile and exact values, qualification, modern LinkML coverage and derivation provenance are qualified.

Sources: [review O01](../../functional_reviews/semantic-postgresql-model_2026-10-29.md#O01), [O02](../../functional_reviews/semantic-postgresql-model_2026-10-29.md#O02), [LinkML overview](../../libraries/linkml.md), [term-validator plugins](https://linkml.io/linkml-term-validator/plugin-reference/), [SchemaView](https://linkml.io/linkml/_modules/linkml_runtime/utils/schemaview.html). These are mechanism evidence, not native integration results.

## Execution checkpoint — 2026-10-29

ADR-0024 records the accepted target and current-runtime boundary. `corpus_structure.semantic`
implements the explicit preparation API and `model/semantic/core.yaml` declares the opt-in target.
The existing generator, selected model revision and physical metadata remain unchanged.

The new path resolves supplied imports, normalizes definitions, compiles strict Pydantic boundaries,
retains scoped constraints/query/registry products, and computes distinct occurrence/fact identities.
Ontology expansion re-derives memberships from supplied bytes; RDF projections retain qualified
occurrences. Unsupported constructs/placements refuse with diagnostics; unchecked ontology metadata
is explicit and is not activation/enforcement evidence. SQL deployment remains SP-02/SP-03.

Final package state and verification commands belong to the coordinator's execution evidence;
this checkpoint does not claim broader consumer adoption or assembled qualification.
