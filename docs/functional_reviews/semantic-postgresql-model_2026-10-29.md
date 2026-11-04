# Semantic PostgreSQL and unified LinkML: functional-extension review

**2026-10-29 · Proposed.** This review recommends a complete semantic-model pivot. It is solution reasoning, not an accepted architectural decision, an implementation plan, or product qualification. The [target-model companion](semantic-postgresql-model_2026-10-29_target-model.md) specifies the proposed contracts and operational realization.

## Outcome and evidence boundary

Recommend **one admitted LinkML semantic release governing a stable PostgreSQL entity, qualified-assertion, and typed-value core**, with required ontology dependencies, generated validation/interchange projections, and operation-specific SQL/Arrow/DuckDB execution. Semantic declarations must govern construction, admission, inference, and answers; generating more schemas around unchanged consumer logic would not deliver the requested capability.

The operator fixed PostgreSQL, unified LinkML, formal ontology, all three forms of dynamic evolution (classes, attributes, relationship types), and clean regeneration as the target. Existing runs, identifiers, APIs, and generated storage impose no compatibility requirement. No language rewrite follows from the illustrative Rust example in the [semantic PostgreSQL proposal](../semantic_postgresql_model.md).

**Inspected baseline:** main `7855c4a`, 2026-10-29, including dirty `consolidate/pass_.py`, `tests/agent/test_packet.py`, and untracked `tests/acceptance/test_trace.py`. The supplied semantic-model and LinkML-Datalog/Valuesets/OAK/Schema Automator overviews were untracked inputs. Pending sibling-worktree changes were not integrated or qualified. STATUS and the consolidation plan predate substantial landed query work and were not used as complete implementation inventories.

Evidence is static source/contract inspection, the supplied library overviews, Context7 documentation, and selected primary sources. Two workers contributed consumer and semantic-foundation research; a PostgreSQL reviewer supplied preliminary notes before repeated model-capacity failures, so the coordinator completed that comparison. No new runtime probe, dependency installation, database alteration, or benchmark was performed. All target behavior below is **Proposed**; documentation/API inspection does not establish installed-stack compatibility. Dates and versions in overview titles are research leads, not fresh release verification.

The assessment uses [core 3.3](../design_review/design_principles/core/design-principles.md), [efficient-architecture heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md), code-intelligence profile 1.4, and the repository binding selected by `standard.toml`. Profile fidelity and evidence obligations apply to corpus assertions without pretending this repository analyzes program control flow.

## What changes functionally

Today the repository already has valuable foundations. `schema/registry.py` stores model/pack sources, versions, compiled artifacts and `meta.schema_*` rows. `schema/batches.py` builds pack-dependent Pydantic boundary models; `schema/lookup.py` compiles class, predicate, qualifier, identity and inference declarations. `schema/relational.py` generates system tables and constraints; `schema/interchange.py` generates Arrow schemas. Thus neither runtime schema compilation nor schema-as-data is absent.

The requested extension changes their reach. Installed model projections and table-specific readers currently constrain the operational vocabulary, storage interpretation, and queries. The new release becomes the common executable interpretation for domain extensions, persistent instances, validation scopes, inference inputs, and query handles. A new declared property should become extractable, admissible, and queryable through these contracts without another hard-coded reader or migration.

Current owners remain the [architecture map](../design/README.md), DESIGN §B1–B5, D1/D2/D3/D5/D8 and ADR-0020–0023; their accepted wording remains in force until explicitly changed. [Phase 0 §11](../plans/phase-0_2026-10-28.md#11-findings-disposition) continues to own scheduled alignment findings. This review creates no competing disposition register and closes none of those findings.

## Complete alternatives

| Realization | Useful capability | Material consequence | Judgment |
|---|---|---|---|
| Extend current generated per-system layout and add ontology checks | Least immediate disruption; keeps existing writers/readers | New declarations can still leave storage, inference and queries interpreting different subsets; ontology becomes an accessory | Insufficient as the complete pivot, though compiler mechanisms are reusable |
| RDF/SemSQL-oriented primary statement store inside PostgreSQL | Uniform ontology statements, RDF interchange and graph queries | Corpus assertion occurrences, qualification, exact values and transactional admission still need explicit modeling; RDF set semantics and adapter execution do not supply these automatically | Viable alternative if RDF/SPARQL becomes the dominant product interface; not preferred for current typed evidence/query workflows |
| Stable relational semantic core plus generated typed projections | Dynamic domain definitions with native keys, SQL joins, qualified assertions and strong operational tables | Requires a bounded semantic compiler and transactional admission boundary; some joins are less convenient than dedicated tables | **Recommended**, with RDF/SHACL views for ontology and graph validation and Arrow/DuckDB for appropriate set operations |

The selected hybrid has one editable meaning per scope, not one physical representation. It avoids both per-domain DDL and an untyped universal JSON document store. It does require project-specific lowering from admitted semantics to operational storage: no reviewed library supplies that complete contract. Keep that lowering bounded to the supported model, reusing LinkML's metamodel, inherited-slot resolution, generators and validators rather than inventing another schema language.

<a id="O01"></a>
## O01 — Admit semantic extensions as complete immutable releases

**Value:** the operator and extraction agents can introduce classes, properties and relationship types without coordinating SQL migrations, Python imports and manual query definitions. Discovery proposes a model change; it does not automatically authorize its use as knowledge.

Use LinkML `SchemaDefinition`, `SchemaView` and induced slots to resolve a modular import closure. Admit candidate declarations against the metamodel, local ontology mappings and the explicitly supported execution profile. Compile normalized class/property constraints, identities, boundary schemas, ontology/SHACL views, vocabulary membership and query mappings once per release. `Validator` accepts a schema definition directly; generated Python source is not a prerequisite for every dynamic extension. [Validator source](https://linkml.io/linkml/_modules/linkml/validator/validator.html), [SchemaView source](https://linkml.io/linkml/_modules/linkml_runtime/utils/schemaview.html).

Store canonical authored sources and resolved dependencies with the release. Relational registry rows and generated artifacts are replaceable projections, not a second editable model. Cache compiled bindings by complete dependencies. Activation points a project to a release; operations already bound to another release retain their meaning.

**Alternative:** mutate registry rows in place and refresh caches. Reject: earlier facts could acquire different meanings without their identifiers changing. Clean regeneration removes historical migration obligations now; it does not remove the need for reproducible future interpretation.

**Delivery example:** declare a new `Inspection` class, a measured property and an attributed relationship; extract, admit, explain and query them with no domain-specific code or DDL changes. New primitive algorithms or datatypes can still require implementation. Unsupported declarations must refuse activation with their location and reason.

<a id="O02"></a>
## O02 — Required ontology with one scoped authoring authority

**Value:** class/property identities, vocabulary membership, units, mappings and rule premises have explicit meanings shared by extraction and downstream tools.

Use local LinkML modules to author local structural semantics and ontology mappings. Import external ontologies as pinned dependencies; LinkML does not replace their authority. Generate local ontology projections with `class_uri`, `slot_uri`, enum `meaning`, hierarchy and supported axiom declarations. No hand-maintained parallel OWL copy of the same local definitions. If a needed axiom cannot be represented by the admitted LinkML profile, either add a precisely owned extension or refuse it; do not hide independent semantics in generated output.

Select a deliberately bounded ontology profile: named classes/properties, declared hierarchy, typed mappings, vocabulary bindings, and explicitly declared inverse/symmetric/transitive relations. RDFS/OWL vocabulary is formal meaning, not a promise of full OWL DL inference. Generated `gen-owl` is an open-world interpretation of structural declarations; it is not PostgreSQL integrity enforcement. [LinkML OWL generator](https://linkml.io/linkml/generators/owl.html).

Recommend OAK for pinned ontology access, labels, hierarchy and term metadata; use Valuesets definitions when they fit actual domain vocabularies, without importing its whole collection. Use `PermissibleValueMeaningPlugin`, `DynamicEnumPlugin` and appropriate binding validation from **linkml-term-validator**, an important companion beyond the initial list. Materialize permitted memberships at release preparation for reproducible normal operation; live ontology services are authoring/acquisition inputs, not request-time authorities. `reachable_from` and enum composition have concrete support; `matches` is recognized but full matching is not implemented. [Plugin reference](https://linkml.io/linkml-term-validator/plugin-reference/).

Labels, CURIE spellings, normalized IRIs, ontology mappings and entity identity stay distinct. `skos:exactMatch` or similar labels do not merge corpus entities. Ontology relation changes and obsolete terms produce an explicit new semantic release and diagnostics. An unavailable ontology is an unavailable prerequisite, not proof a term does not exist. OAK's SemanticSQL adapter is not assumed to be a production PostgreSQL backend for this application; its relation patterns are useful design input, not a turnkey deployment.

<a id="O03"></a>
## O03 — A PostgreSQL core that enforces semantic admission

**Value:** evolving domain data gains database identity, relationship integrity and race-safe admission while retaining efficient SQL access.

Adopt the companion's stable entity/membership, qualified assertion, recursive typed value and evidence relations. Generate stable physical tables from the system portion of the model; compile domain definitions into versioned registry data. Optional subject properties that carry evidence are assertions too. Display caches and specialized columns derive from these facts.

Use native composite FKs, uniqueness, null/tag checks and indexes for static structural invariants. Enforce model-dependent ranges, class applicability, cardinality and uniqueness over the candidate's declared scope through a single publication operation. Candidate preparation can occur outside its transaction; final validation must include concurrent state. Recommend SERIALIZABLE publication with bounded whole-transaction retry, immutable releases and no ungoverned base-table write path. A database error remains a failed publication, never partially accepted knowledge.

COPY loads transaction-local staging; a set-based publication inserts only after required checks. PostgreSQL `CHECK` cannot safely encode general cross-table semantic rules. Do not turn those rules into functions hidden inside CHECK expressions. [PostgreSQL constraints](https://www.postgresql.org/docs/18/ddl-constraints.html).

Use SQLAlchemy Core `MetaData`, `Table`, `select` and DML expressions for set operations; psycopg `Cursor.copy()`/`Copy.set_types()` for typed staging on the same owned transaction. The SQLAlchemy-managed connection and its underlying driver connection must not independently commit or roll back. pglast `parse_sql()` supplies syntax trees for authored SQL; semantic handle resolution and approved operation contracts decide what it means and may access. Alembic is recommended for the physical revision graph, not each new class. Select one pool owner: retain the existing SQLAlchemy route initially; use psycopg-pool only if direct psycopg ownership replaces it, never as a nested second pool. Alembic autogeneration produces candidate physical migrations requiring review; it cannot infer semantic intent. See [SQLAlchemy connection ownership](https://docs.sqlalchemy.org/en/20/core/connections.html), [psycopg COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html), [pglast parsing](https://pglast.readthedocs.io/en/latest/introduction.html) and [Alembic autogeneration](https://alembic.sqlalchemy.org/en/latest/autogenerate.html). These live documentation versions are not a dependency bump or locked-stack test.

**Tradeoff:** runtime semantic rules require real enforcement code. The benefit is one publication boundary shared by scalar, agent and bulk submissions rather than validators that callers can bypass. Arbitrary future rule languages are not promised.

<a id="O04"></a>
## O04 — Explicit conformance, entailment and domain operations

**Value:** consumers can distinguish valid structure, logically derived knowledge, and the results of numerical, symbolic or heuristic work.

Use LinkML validation for object structure; generated SHACL plus RDFLib/PySHACL for supported graph constraints on a declared validation graph. Use `pyshacl.validate` with explicit inference/rule settings and retain structured results. Ordinary SQL operations need not serialize the whole corpus into RDF for each write. The release compiler assigns each supported constraint to its enforcement point. Initially, required graph integrity rules must also have faithful transactional SQL/native lowering; otherwise activation refuses them. PySHACL provides preparation and declared graph diagnostics, not a bypass around this requirement. Standalone SHACL success does not establish transactional database safety. [PySHACL API and limits](https://github.com/RDFLib/pySHACL).

Recommend initial ontology hierarchy and declared relationship closure in PostgreSQL set/recursive SQL over an explicit eligible assertion projection. Keep derived assertion identity, rule revision, premises and qualification. Conditions and attribution do not evaporate through a transitive relation. The companion restricts the initial supported inference profile rather than claiming general conditional logic.

LinkML-Datalog is a promising optional compiler/execution direction, not the unconditional foundation. Primary source confirms `DatalogEngine` invokes external Soufflé and has an unfinished materialization helper; `TupleDumper` converts through RDF triples. Exact numeric lowering, modern LinkML coverage, assertion occurrence identity and proof lineage require qualification before production selection. Reconstructing a safe generic reasoning service around it would be substantial work. [Engine source](https://raw.githubusercontent.com/linkml/linkml-datalog/main/linkml_datalog/engines/datalog_engine.py), [tuple conversion](https://raw.githubusercontent.com/linkml/linkml-datalog/main/linkml_datalog/dumpers/tupledumper.py), [overview §8](../libraries/data_model/linkml-datalog.md#81-numeric-representation).

Do not replace symbolic equivalence, identity resolution, confidence combination or evaluation matching with ontology entailment. Keep these explicit domain operations with model-defined inputs, applicability and outputs. No general negation-as-failure over incomplete corpus evidence; a missing fact is not an ontological denial.

<a id="O05"></a>
## O05 — Model-governed consumer and query contracts

**Value:** newly admitted semantic types become usable throughout the product, and answers retain enough context to be trusted.

Compile typed class/property handles into SQLAlchemy expressions over the stable core and declared physical projections. Use ordinary domain query functions for specialized questions; do not build a general SQL optimizer or demand all scientific algorithms be declarative. Query results carry semantic release, data snapshot, inference selection, evidence references and coverage. Continuations bind all result-affecting selections. An output selector cannot remove intermediate nodes required for a traversal or proof of absence.

Extraction receives the admitted model and vocabulary with a source frame. Intervention checks the same binding before publication. Consolidation consumes qualified candidates under that release; inference is a distinct operation. Explain resolves an assertion's evidence and derivation within the same snapshot. Evaluation uses shared data contracts and independent reference expectations, preserving gold isolation and undecided outcomes.

Existing `schema/batches.py`, `schema/lookup.py`, `consolidate/assemble.py`, `intervene/submission.py`, `serve/protocol.py`, `serve/read.py`, `serve/journey.py`, `evaluate/align.py` and `evaluate/equivalence.py` show reusable mechanisms and affected consumers. They are not promised source-compatible. The proposed query interface replaces table-specific reconstruction as the generic extension path.

<a id="O06"></a>
## O06 — Semantic Arrow interchange and local relational execution

**Value:** batch extraction, fusion, analytical joins and evaluation can operate on typed data without repeatedly hydrating every fact into Python objects.

Compile Arrow projections from the admitted binding: class/property identity, typed values, qualifications, units, missing/null policy, projection version and snapshot context. Metadata carries context but does not enforce it. Operators may strip metadata; only a known output mapping can reattach a semantic claim. Decimal ranges require explicit conversion: PostgreSQL NUMERIC, Arrow decimal types and DuckDB DECIMAL do not have interchangeable bounds.

Use DuckDB for suitable local set operations, candidate fusion, aggregations and evaluation joins. Keep projection preparation and connection ownership explicit; no second durable semantic catalog, graph authority, or live ontology network dependency. Prefer pushdown and narrow projections where they preserve required context.

Current `pool/load.py` already obtains a REPEATABLE READ, READ ONLY source transaction, but `.read_all()` materializes its relations. Current `pool/duckdb_engine.py` registers Arrow inputs and unregisters them in `finally`; preserve that lifecycle. A future streaming reader must own its connection and registrations until consumption or cancellation. [Arrow RecordBatchReader](https://arrow.apache.org/docs/python/generated/pyarrow.RecordBatchReader.html), [Arrow decimal256](https://arrow.apache.org/docs/python/generated/pyarrow.decimal256.html), [DuckDB relation implementation](https://github.com/duckdb/duckdb-python/blob/main/duckdb/_relation.py).

This expands Arrow/DuckDB after the core semantic contract is fixed; neither is an alternative meaning registry. Streaming, capacity and speed improvements are unmeasured.

## Selection, dependencies and architectural assessment

O01–O03 form one foundation: admitting declarations without their ontology dependencies or enforcement would not deliver a complete pivot. O04–O05 establish authoritative behavior rather than a storage-only rewrite. O06 follows their contracts, with existing set execution reusable earlier when useful. LinkML-Datalog can be revisited when a concrete recursive rule workload exceeds the selected SQL profile and compatibility/fidelity are demonstrated. Schema Automator can suggest draft models later; inferred schemas are not automatically admitted semantics.

| Judgment | Assessment of the proposed realization |
|---|---|
| A1 boundaries and change locality | New domain declarations remain data; physical optimizations and new primitive algorithms have separate owners. This needs consumer replacement, not a registry facade. |
| A2 model adequacy and authority | Release governs types, ontology dependencies, qualified assertions, validation, inference and operations. Proposed adequate for the bounded profile; general ontology reasoning is not claimed. |
| A3 composition and local reasoning | Prepare immutable bindings once; compose existing validators and relational operations. No additional service required for the single operator. |
| A4 execution fit | Stable indexes and set-based publication avoid per-type physical growth; SQL selection precedes hydration, RDF graphs are scoped, and Arrow supports batch kernels. High-degree closure and global constraints can still require broad work; no capacity claim is established. |

Fidelity remains an independent condition: parallel relationships, unresolved references, unknown coverage, derived/asserted distinction, evidence closure and independent evaluation are mandatory in the target. The review does not mark CI-G1–G3 or product correctness as passed for unimplemented behavior.

## Required rule impacts and adoption decisions

<a id="RC01"></a>
**RC01 — Semantic contract and identity.** Revisit §B1 and ADR-0023/D1: qualified assertions and recursively typed values may replace the current frozen claim/key form. Preserve semantic distinctions; do not preserve key scheme 1 for historical compatibility.

<a id="RC02"></a>
**RC02 — Model and storage realization.** Revisit §B4/§B5 and ADR-0020/0022 with D2/D3: unify semantic releases, required ontology imports and dynamic registry-backed domain storage; distinguish release changes from physical revisions. Preserve PostgreSQL instance authority, not every old projection.

<a id="RC03"></a>
**RC03 — Operational publication and inference.** Revisit §B2, D5/D6 and affected ADR-0014/0019 responsibilities: define the admission/publication contract for observations, selected assertions and derived facts. Do not bypass consolidation policy by calling a generic writer.

<a id="RC04"></a>
**RC04 — Interchange, query and scope.** Revisit ADR-0021, D7/D8 and DESIGN §1.2: ontology and RDF validation become internal required capabilities, distinct from public RDF publication. Replace query contracts and evaluation bindings. SQL/Python/Arrow execution placement follows operations rather than a mandatory engine for every task.

These are proposed decision topics, not accepted supersessions. Accepted ADRs remain immutable. Subsequent plan creation should select the integrated target, route ADR/DESIGN amendments and reconcile the old phase 0 work explicitly. Do not quietly mark its incomplete acceptance complete or copy its findings into this review.

Clean regeneration means build a new dedicated database/model realization and regenerate inputs under the new contract; no migration of old runs or maintenance of legacy APIs. It does not authorize deleting current evidence, plans, databases or unrelated worktrees. PostgreSQL cluster `18/corpus` remains the designated service; other projects' clusters are untouched.

## Demonstrating delivery and remaining uncertainty

The companion's scenarios define the review's proposed behavioral expectations. Implementation planning must turn them into native integration checks with independent expectations, then apply repository qualification at complete scope. No benchmark or new alignment gate is required merely to adopt this review.

| Obligation | Present outcome |
|---|---|
| Static source and documentation inquiry | Completed 2026-10-29; conclusions bounded as above |
| Focused runtime compatibility/fidelity probes | `not_run`: no installed-stack execution claim; required before selecting unsupported generator/inference features |
| Product tests (`just test-all`, `just hygiene`) | `not_run`: review-only changes do not qualify the paused implementation |

Before production selection, verify exact pins together on Python 3.14.10, LinkML generator feature behavior, the chosen OAK local adapter/import closure, SHACL graph scope, and the transactional publisher under concurrent conflicting submissions. These are bounded implementation acceptance obligations, not unresolved choices between the complete architectural alternatives. If a needed LinkML construct cannot be faithfully lowered, narrow the supported profile or change the selected mechanism explicitly; never activate a partly enforced model silently.
