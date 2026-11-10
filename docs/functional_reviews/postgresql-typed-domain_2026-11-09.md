# PostgreSQL capabilities for the typed domain model

**Functional-extension review · 2026-11-09 · Proposed recommendations.** This review assesses
product, developer, operator and research value across the full PostgreSQL discovery. It develops
preferred bounded realizations and conditional propositions; it does not authorize implementation.

## Scope, source and evidence

The input is the [discovery briefing](../library_leverage/libraries/postgresql/briefing.md) and
its seven topics/coverage appendix published at `d18183a2244e1aa5cc1f1a5d811263cd21451a14`.
The discovery inspected product source at `51b3c28de` on November9. Review source is `d18183a22`, reconciled through concurrent checkpoint `f917260f8`;
a fresh diff found no changes to the reviewed product, manifests, lockfile, discovery or standard.
Concurrent STATUS/PM2 plans and retained evidence are excluded and preserved. Publication revision
is distinct from this inspected source baseline. Three independent bounded reviewers inspected
owners and local consumers; the coordinator reconciled the proposals and decisive source facts.

Selected environment remains Python3.14.10, SQLAlchemy2.1.6, Alembic1.20.1, pglast8.7,
SQLGlot30.27.0, Psycopg3.3.6/pool3.3.3, pgpq0.12.0, ADBC PostgreSQL/manager1.13.0,
pgvector Python0.5.1 and Arrow26.0.0. The discovery's installed metadata and uv selection retain
their original dates. PostgreSQL18.6/vector0.8.7 are owner-recorded, not freshly queried here.
Capabilities supported only by broader overview material remain candidates until their precise
contract matters; selected-source observations are distinguished in the companions.

Criteria: core3.3, efficient-architecture heuristics1.0, code-intelligence1.4 and repository binding
selected by [standard.toml](../design_review/design_principles/standard.toml), with test-assessment
for independent expectations. FP-04/05 and A2 guide authority; A1/A3 concern locality/composition;
FP-07/A4 concerns qualitative whole-operation fit. This is a functional review, without a diagnostic
audit or a new whole-system conformance verdict. No new product tests, native probes, benchmarks or
provider runs were necessary: those are **not_run**. Source/reference inspection supports the
recommendations, not measured performance or scientific-quality improvements.

## Recommended capability set

Recommend first strengthening model-derived contracts and exposing useful information through
existing owners: precise generated boundaries, attributed SQL explanations, exact retrieval
composition and honest database type inspection. Share acquisition policy where operations already
need it. These offer direct developer/operator value without another semantic store or runtime.

Develop structured exchange, native evolution and larger query capabilities as bounded extensions
when their specified consumers are selected. Keep richer retrieval and operational variants as
fully described conditional propositions. Current callers are evidence of demand, not a prerequisite
for proposing a useful new workflow. The discovery's First/Next labels do not determine this review's
priorities. A broad feature catalogue is not itself a reason to adopt a mechanism.

| Opportunity | Proposed result | Recommendation and detailed argument |
| --- | --- | --- |
| <a id="O01"></a>O01 · Meaningful generated boundaries | Prioritize: retain released distinctions through query/result contracts | [Full proposition](postgresql-typed-domain/domain-realization.md#O01) |
| <a id="O02"></a>O02 · Structured values and native invariants | Bounded adaptation first; native/ORM expansion conditional on complete value lifecycle | [Full proposition](postgresql-typed-domain/domain-realization.md#O02) |
| <a id="O03"></a>O03 · Attributed SQL explanations | Prioritize useful typed origins/dependencies; retain unknown helper semantics | [Full proposition](postgresql-typed-domain/sql-understanding-and-authoring.md#O03) |
| <a id="O04"></a>O04 · SQL authoring and impact workflows | Develop bounded source/impact tools; broader dialect/procedural execution conditional | [Full proposition](postgresql-typed-domain/sql-understanding-and-authoring.md#O04) |
| <a id="O05"></a>O05 · Complete relational operations | Compose operation intent before adding preparation/batching layers | [Full proposition](postgresql-typed-domain/relational-operations-and-retrieval.md#O05) |
| <a id="O06"></a>O06 · Exact contextual retrieval | Prioritize typed transient binding and composed channels while preserving admission | [Full proposition](postgresql-typed-domain/relational-operations-and-retrieval.md#O06) |
| <a id="O07"></a>O07 · Richer retrieval modes | Conditional product/research capability, explicit precision/quality/scale contract | [Full proposition](postgresql-typed-domain/relational-operations-and-retrieval.md#O07) |
| <a id="O08"></a>O08 · Faithful directional exchange | Extend existing model-owned profiles for selected import/export consumers | [Full proposition](postgresql-typed-domain/analytical-exchange.md#O08) |
| <a id="O09"></a>O09 · Analytical research access | Conditional derived analytical workflow; no second publication authority | [Full proposition](postgresql-typed-domain/analytical-exchange.md#O09) |
| <a id="O10"></a>O10 · Honest type inspection | Prioritize useful observed metadata and explicit unknown constraints | [Full proposition](postgresql-typed-domain/native-inspection-and-evolution.md#O10) |
| <a id="O11"></a>O11 · Governed native evolution | Supported structured authoring extensions; retain independent drift observation | [Full proposition](postgresql-typed-domain/native-inspection-and-evolution.md#O11) |
| <a id="O12"></a>O12 · Consistent ADBC ownership | Prioritize explicit acquisition/resolver policy with independent cleanup | [Full proposition](postgresql-typed-domain/operational-control.md#O12) |
| <a id="O13"></a>O13 · Operational control | Select bounded workflows; defer distributed/async machinery without a sufficient scenario | [Full proposition](postgresql-typed-domain/operational-control.md#O13) |

## Coherence, alternatives and governing decisions

New native value types cannot be chosen separately from generated adapters, directional Arrow
mapping, migration/OID identity and session replacement (O01/O02/O08/O11/O13). First preserve
meaning in a released contract; do not infer one native type/table/operation per semantic distinction.
O01 can proceed without an ORM or named-type migration. O02 is not a prerequisite for every other
recommendation. Existing explicit codecs and guarded membership remain valid alternatives.

SQL explanation and new query forms share owned helper/parameter signatures (O03/O04/O05).
SQLGlot metadata cannot supply native binding or missing helper-body semantics. Nested scopes
need qualification under their own sources, not a relaxed global collector. Retain the present
explicit helper typing unless an integrated hook discharges the full requirement.

Compose retrieval channels before deciding to relocate fusion policy (O05/O06). A materialized CTE
is statement-local; combining three channels is a smaller change than moving all RRF to SQL.
Complete inventory refusal, exact neighbor membership, channel ranks and witness precedence are
preserved. O07 does not silently replace the exact baseline; candidate precision and final
ranking/support have separate contracts and evaluations.

Type inspection and analytical access share acquisition facts but can need different resolvers
(O08/O09/O10/O12). One explicit policy owner must support builtin and server discovery without
forcing broad discovery onto ordinary capture. Table schema, prospective result schema, observed
metadata and released domain declarations remain distinct. Bound ADBC results are not incremental
COPY; partial consumption can affect later bound executions.

Native evolution uses frozen inputs and independently observed actual state (O11). Rewriter may
simplify local operation traversal; it cannot replace application FK/ACL/retirement ordering.
Likewise pgpq checks do not replace full semantic schema identity. Existing same-session COPY,
fresh encoder state, snapshot capture, exact decimal/hex-float normalization, purpose roles and
cause/phase/effect custody are preservation requirements, not unused capabilities.

The [knowledge](../design/D1-knowledge-representation.md), [compiler](../design/D2-schema-and-guidelines.md),
[database](../design/D3-database.md) and [interface](../design/D8-agent-and-query-interfaces.md)
owners remain authoritative. ADR-0024/0047/0067 govern derived relational realization and current-only
consumer migration. Recommended local extensions fit those authorities. A general ORM/UoW shift,
new independent publication path, native-type lifecycle or changed retrieval policy needs its
concrete architectural consequences assessed and, when selected, routed through the owning section
and ADR rules. Rule impact is a decision to make, not a blanket prohibition or advance approval.

Expected benefits are qualitative: fewer independent decisions, faithful representations, simpler
composition and clearer operator information. No speed, memory, capacity or retrieval-quality gain
is quantified. A smaller returned result does not alone establish less examined work.

## Delivery evidence and unresolved choices

Subsequent planning should retain the companions' consumer scenarios and independent expectations.
Relevant cases include wrong identifier/closed-value construction; SQL-null/JSON-null/omission;
range and numeric precision; opaque helpers/CTE shadowing/correlation; exact inventory and ranking
ties; observed metadata versus unavailable constraints; stale native state; snapshot/stream cleanup;
and uncertain commit acknowledgement. Choose tests for the selected changed responsibility, not
a universal campaign covering every library feature.

Recommended targets are suitable for create-plan, with detailed API design/implementation packages
owned there. Conditional targets state the capability, alternatives and the premise selecting it.
Remaining decisive questions are local: which typed distinctions actual consumer contracts require;
which analysis detail has an explanation consumer; whether a composed retrieval result should
include Python or SQL fusion; and which metadata is useful to the database-description consumer.
These can be settled during bounded target planning without treating every unused API as a task.
A native or type-inference feasibility claim left uncertain must remain conditional until the
named source inspection or narrow probe settles it. No recommendation audit is inserted.

## Complete discovery crosswalk

The following is source correspondence, not another execution register. Topic shortlist rows
are identified by document and row order at the input revision; mechanism names retain their
original wording. Each maps to the detailed proposition where its value, limits and disposition
are assessed. Multiple source rows can support one opportunity. Inline source observations,
conditional paragraphs and corrections are reconciled explicitly below the row tables.

### All 38 shortlist entries

| Discovery source / row | Mechanism or responsibility | Review disposition owner |
| --- | --- | --- |
| [domain-types-and-invariants, row 1](../library_leverage/libraries/postgresql/discovery/domain-types-and-invariants.md) | Extend existing generated TypedColumns/Named and result protocols beyond currently selected tables/functions | [O01](#O01) |
| [domain-types-and-invariants, row 2](../library_leverage/libraries/postgresql/discovery/domain-types-and-invariants.md) | SQLAlchemy TypeDecorator bind/result processors, coerce_compared_value/comparator_factory, bind_expression/column_expression and cache_ok at repeated codec boundaries | [O02](#O02) |
| [domain-types-and-invariants, row 3](../library_leverage/libraries/postgresql/discovery/domain-types-and-invariants.md) | Psycopg scoped Dumper/Loader, CompositeInfo/register_composite, EnumInfo/register_enum and range/multirange registration | [O02](#O02) |
| [domain-types-and-invariants, row 4](../library_leverage/libraries/postgresql/discovery/domain-types-and-invariants.md) | class_row, args_row/kwargs_row and custom RowFactory/RowMaker for small domain reads | [O02](#O02) |
| [domain-types-and-invariants, row 5](../library_leverage/libraries/postgresql/discovery/domain-types-and-invariants.md) | DOMAIN, ExcludeConstraint, native range/multirange and qualified FK/unique/deferrable constraints | [O02](#O02) |
| [domain-types-and-invariants, row 6](../library_leverage/libraries/postgresql/discovery/domain-types-and-invariants.md) | Imperative Table mapping, composite(), dataclasses, hybrids, association objects/proxies and custom collections | [O02](#O02) |
| [relational-operations-and-preparation, row 1](../library_leverage/libraries/postgresql/discovery/relational-operations-and-preparation.md) | Composable EXISTS/correlated predicates, ANY array binds, joins and database-derived key sets in readers/retrieval | [O05](#O05) |
| [relational-operations-and-preparation, row 2](../library_leverage/libraries/postgresql/discovery/relational-operations-and-preparation.md) | CTEs/add_cte, lateral(), table_valued(), VALUES, windows and aggregate_order_by() in projection/retrieval | [O05](#O05) |
| [relational-operations-and-preparation, row 3](../library_leverage/libraries/postgresql/discovery/relational-operations-and-preparation.md) | Insert.from_select, UPSERT, DML CTEs, RETURNING correlation/from_dml_column | [O05](#O05) |
| [relational-operations-and-preparation, row 4](../library_leverage/libraries/postgresql/discovery/relational-operations-and-preparation.md) | GenericFunction, compiler extensions, typed text/tstring, CreateView/CreateTableAs/Select.into | [O04](#O04) |
| [relational-operations-and-preparation, row 5](../library_leverage/libraries/postgresql/discovery/relational-operations-and-preparation.md) | Structural compiled caches/cache_ok/inherit_cache and lambda_stmt at existing preparation owners | [O05](#O05) |
| [relational-operations-and-preparation, row 6](../library_leverage/libraries/postgresql/discovery/relational-operations-and-preparation.md) | Core partitions/yield_per and server cursors for ordinary row exports | [O08](#O08) |
| [relational-operations-and-preparation, row 7](../library_leverage/libraries/postgresql/discovery/relational-operations-and-preparation.md) | Psycopg prepare_threshold/prepare/prepared_max, pipeline/sync, executemany(returning=True)/results | [O05](#O05) |
| [relational-operations-and-preparation, row 8](../library_leverage/libraries/postgresql/discovery/relational-operations-and-preparation.md) | ADBC adbc_prepare/adbc_execute_schema and positional bound results | [O10](#O10) |
| [sql-analysis-and-source-fidelity, row 1](../library_leverage/libraries/postgresql/discovery/sql-analysis-and-source-fidelity.md) | lineage(on_node=...), Node.payload and existing AST model-origin metadata | [O03](#O03) |
| [sql-analysis-and-source-fidelity, row 2](../library_leverage/libraries/postgresql/discovery/sql-analysis-and-source-fidelity.md) | Scope.sources/traverse_scope/find_all_in_scope and scope-aware find_tables versus local table/CTE collection | [O03](#O03) |
| [sql-analysis-and-source-fidelity, row 3](../library_leverage/libraries/postgresql/discovery/sql-analysis-and-source-fidelity.md) | Schema.get_udf_type/udf_mapping, expression_metadata and protected declared .type annotations | [O03](#O03) |
| [sql-analysis-and-source-fidelity, row 4](../library_leverage/libraries/postgresql/discovery/sql-analysis-and-source-fidelity.md) | DataType representations and structured JSONPath/nested-field analysis | [O04](#O04) |
| [sql-analysis-and-source-fidelity, row 5](../library_leverage/libraries/postgresql/discovery/sql-analysis-and-source-fidelity.md) | pglast shared AST facts, visitor actions/Ancestor helpers and printer precedence/name primitives | [O04](#O04) |
| [sql-analysis-and-source-fidelity, row 6](../library_leverage/libraries/postgresql/discovery/sql-analysis-and-source-fidelity.md) | SQLGlot diff, selected canonicalization, error metadata and serialization; pglast source spans/comments | [O04](#O04) |
| [schema-evolution-and-catalog-admission, row 1](../library_leverage/libraries/postgresql/discovery/schema-evolution-and-catalog-admission.md) | Alembic operation trees/Rewriter/renderers/directive hooks around frozen candidate generation | [O11](#O11) |
| [schema-evolution-and-catalog-admission, row 2](../library_leverage/libraries/postgresql/discovery/schema-evolution-and-catalog-admission.md) | SQLAlchemy Inspector get_multi/reflection hooks/Table.to_metadata and supported comparator APIs | [O11](#O11) |
| [schema-evolution-and-catalog-admission, row 3](../library_leverage/libraries/postgresql/discovery/schema-evolution-and-catalog-admission.md) | CreateView/CreateTableAs, named-type DDL, conditional compilation and dialect operation constructs | [O11](#O11) |
| [schema-evolution-and-catalog-admission, row 4](../library_leverage/libraries/postgresql/discovery/schema-evolution-and-catalog-admission.md) | Existing ADBC object/table/query schemas and Core catalog observations in database_description | [O10](#O10) |
| [schema-evolution-and-catalog-admission, row 5](../library_leverage/libraries/postgresql/discovery/schema-evolution-and-catalog-admission.md) | DOMAIN/exclusion/deferrable constraints, NOT VALID/VALIDATE, concurrent indexes, generated-column distinctions | [O11](#O11) |
| [typed-copy-and-arrow-transfer, row 1](../library_leverage/libraries/postgresql/discovery/typed-copy-and-arrow-transfer.md) | Model-derived directional profiles extended to an actual new value family | [O08](#O08) |
| [typed-copy-and-arrow-transfer, row 2](../library_leverage/libraries/postgresql/discovery/typed-copy-and-arrow-transfer.md) | Psycopg typed output COPY/set_types, custom Writer/FileWriter and vector binary adaptation | [O08](#O08) |
| [typed-copy-and-arrow-transfer, row 3](../library_leverage/libraries/postgresql/discovery/typed-copy-and-arrow-transfer.md) | pgpq lists/structs, explicit encoder maps and qualified OIDs | [O08](#O08) |
| [typed-copy-and-arrow-transfer, row 4](../library_leverage/libraries/postgresql/discovery/typed-copy-and-arrow-transfer.md) | ADBC Arrow C Array/C Stream binding/fetch and target-aware adbc_ingest | [O09](#O09) |
| [typed-copy-and-arrow-transfer, row 5](../library_leverage/libraries/postgresql/discovery/typed-copy-and-arrow-transfer.md) | Existing normalization and schema metadata at analytics/export boundary | [O08](#O08) |
| [transactions-pools-and-outcomes, row 1](../library_leverage/libraries/postgresql/discovery/transactions-pools-and-outcomes.md) | Scoped adapters/custom typed connections, pool drain and replacement | [O13](#O13) |
| [transactions-pools-and-outcomes, row 2](../library_leverage/libraries/postgresql/discovery/transactions-pools-and-outcomes.md) | Existing transaction characteristics/savepoints/force_rollback/Rollback(target) in provisional work | [O13](#O13) |
| [transactions-pools-and-outcomes, row 3](../library_leverage/libraries/postgresql/discovery/transactions-pools-and-outcomes.md) | Existing cause/phase/effect diagnostics plus native transaction status/capability flags | [O13](#O13) |
| [transactions-pools-and-outcomes, row 4](../library_leverage/libraries/postgresql/discovery/transactions-pools-and-outcomes.md) | Zero-minimum persistent pools, resize/drain/readiness and callable connection parameters | [O13](#O13) |
| [typed-retrieval-and-vector-search, row 1](../library_leverage/libraries/postgresql/discovery/typed-retrieval-and-vector-search.md) | Generated VECTOR/profile/dimension/normalization contracts and typed VALUES parameters | [O06](#O06) |
| [typed-retrieval-and-vector-search, row 2](../library_leverage/libraries/postgresql/discovery/typed-retrieval-and-vector-search.md) | One relational composition of eligible membership and three channels, windows/CTEs and RRF | [O06](#O06) |
| [typed-retrieval-and-vector-search, row 3](../library_leverage/libraries/postgresql/discovery/typed-retrieval-and-vector-search.md) | Psycopg register_vector/binary codecs on existing physical connections/COPY | [O06](#O06) |
| [typed-retrieval-and-vector-search, row 4](../library_leverage/libraries/postgresql/discovery/typed-retrieval-and-vector-search.md) | Vector avg/sum/l2_normalize/vector_dims and typed comparators | [O07](#O07) |

### All 23 retained capability families

Conditional source families are developed or evaluated in their referenced opportunity; they are
not automatically rejected for lacking an existing caller. Nonpreferred mechanisms remain valid
alternatives under the conditions stated in the detailed arguments.

| Source family | Review disposition owner | Functional assessment |
| --- | --- | --- |
| ORM mappings, composites, dataclass/attrs integration, inheritance, hybrids, expression properties, association proxies/objects and mutable/ordered collections | [O02](#O02) | Bounded value/object mapping; general UoW not preferred over released Core authority |
| ORM loaders, UoW/cascades, versioning, WriteOnlyMapped, loader criteria, session scoping, registry/type-annotation events, interception and frozen-result merging | [O02](#O02) | Only as part of a justified object-graph lifecycle; no standalone loader adoption |
| SQLAlchemy schemas/translation, async, sharding, engine plugins, hints and other dialects | [O13](#O13) | Explicit deployment/participant scenario; no speculative platform expansion |
| pglast printer registries, formatting/safety-belt, comments, keyword inspection and pgpp | [O04](#O04) | Source diagnostics and reviewable authoring; printers remain syntax tools |
| pglast PL/pgSQL inspection, JSON/Protobuf parse/deparse, fingerprints and cross-language pg_query interchange | [O04](#O04) | Bounded procedural/interchange workflow; fingerprints never semantic identity |
| SQLGlot optimizer passes, diff, serialization, anonymization, custom dialect/plugins and parser/generator extension | [O04](#O04) | Explain change with typed structural evidence; no semantic-equivalence promise |
| SQLGlot specialized generator transforms: QUALIFY/DISTINCT ON/windows, joins, UNNEST/EXPLODE/generate_series, recursion, percentile syntax, booleans/epoch, identifier/pivot fields, partition/schema movement, temporary CTAS and nested struct construction | [O04](#O04) | Select actual source/target construct; no wholesale transpilation project |
| SQLGlot PIVOT/UNPIVOT output schemas, pipe SQL, temporal-format/subsecond utilities | [O04](#O04) | Develop operator/path/format need before enlarging admitted query vocabulary |
| SQLGlot Plan/PythonExecutor, SQLFrame, compiled acceleration | [O04](#O04) | Alternative query workbench; another executor/acceleration not presently preferred |
| Psycopg row factories, adaptation contexts, value-sensitive dumpers, NumPy/UUID/network/hstore, temporal infinities and experimental spatial adapters | [O02](#O02) | Value-specific adaptation; spatial or new primitive families need declared semantics |
| Psycopg RawCursor/ClientCursor, t-strings, named/server/refcursors, held/scrollable/chunked streams, result navigation and offline COPY writers | [O08](#O08) | Export or result-lifetime consumer; no blanket driver-path replacement |
| Pool async/custom connections, dynamic credentials, zero-minimum/null strategies, health/reset/drain/resize and metrics | [O13](#O13) | Lifecycle policy for selected operation; preserve regular-pool return contract |
| Psycopg notifications/notices, safe cancellation/capability checks, PGconn/PGresult tracing, libpq services/security/multihost and two-phase | [O13](#O13) | Wakeup and diagnostics scenario; two-phase only with actual distributed effect authority |
| Alembic branches/merges/multiple bases/depends_on, version inspection, config/templates/runtime kwargs and callbacks | [O11](#O11) | Independent histories only if lifecycle requires them; frozen revision meaning preserved |
| Alembic offline/batch reconstruction/multi-database/async, pytest-alembic, Alembic Utils and enum extensions | [O11](#O11) | Use companion/reconstruction only for demonstrated full-contract gap |
| pgpq generated schema/DDL and composites, nested OIDs, Rust traits/BytesMut/encoder APIs | [O08](#O08) | Nested or cross-language exchange; native objects retain governed schema/OID lifecycle |
| arrow-json companion | [O08](#O08) | Nested JSON bridge only with explicit null and precision mapping |
| ADBC target-aware ingestion, create/append/create_append/replace, temporary targets and native COPY coercion | [O09](#O09) | Independent derived import operation, not a parallel protected publisher |
| ADBC parameter schemas, bound result streams, direct C interfaces and connection cloning | [O09](#O09) | Schema/bind/stream workflow; snapshot and PGresult buffering remain explicit |
| ADBC metadata/statistics/info, resolver modes, driver manifests/profiles and DuckDB community extension | [O10](#O10) | Observed metadata and selected analytical access; profiles must not duplicate settings authority |
| pgvector VECTOR/HALFVEC/SPARSEVEC/BIT, metric comparators, aggregates, normalization, arrays and binary codecs | [O07](#O07) | Model-owned metrics/shapes; new representations belong to a complete retrieval proposition |
| pgvector HNSW/IVFFlat, iterative/filtered search, half precision, quantization/reranking, subvectors, sparse/multivector/late interaction | [O07](#O07) | Conditional scale/quality or new retrieval product; exact baseline retained |
| pgvector other ORMs/drivers, ML/cross-encoder examples, replicas/partitioning/sharding | [O13](#O13) | Conditional participant/function; external ML/ORM examples do not create demand |

### Observations, questions and corrections outside the tables

| Source contribution | Disposition |
| --- | --- |
| Briefing First/Next/Supporting attention rankings | Reassessed in the recommendation synthesis; not inherited as adoption priority |
| Primitive-only generated columns despite richer Column.info; JSONB Python/Arrow materializations | O01/O02/O08 preserve directional meaning and assess useful generated distinctions |
| Dataclass composite factory alone lacks bidirectional dumping; adapter contexts do not update existing sessions | O02/O13 constrain any structured-value route and session-generation design |
| Direct model-bound helper .type and overwrite_types=False; get_udf_type absent from annotate_types call path | O03 retains explicit helper authority; relocation needs a real new capability |
| Current recipe has no general subquery form; local expansion cycle/collision safeguards | O03/O04 propose an extension boundary, not an established current nested-query bug |
| Visitor.iterate action protocol, printer/source units, comments, RawStmt cloning | O04 preserves established preparation and bounds new source-editing propositions |
| Structural == vs .eq, replace_placeholders vs driver binding, meta directives, exp.Command | O03/O04 keep syntax, substitutions, declared semantics and unsupported content distinguishable |
| pglast8.7 normalize/enum_name unavailable; version tuple has two elements | O04 version constraints; no target relies on unavailable APIs |
| Frozen-operation traversal and FK/ACL retirement order; default/collation private adapters | O11 compares local rewriting with retaining purposeful version-sensitive glue |
| ADBC description hardcodes unavailable field metadata; parameters currently refused | O10 develops typed observed metadata and conditional parameter description rather than inventing a current parameter defect |
| Direct ADBC description acquisition vs configured driver/owned cleanup | O12 selects one explicit acquisition policy preserving resolver differences |
| Decimal half-even/overflow flags, exact hex-float source columns | O08 retains owned numerical policy; no generic-cast replacement established |
| pgpq positional checks/partial bytes and composite DDL lifetime/schema limitations | O08 preserves complete profile checks/fresh streams and conditions nested exchange |
| ADBC parameterized SELECT correction, PGresult path, consumption-driven later bindings | O09/O10 distinguish bound schemas/results from COPY and side-effect completion |
| Pool async drain exists; null-pool close_returns differs; readiness and metric limits | O12/O13 preserve exact selected release behavior; no transparent null-pool swap |
| Transient vector str(list(...)) despite typed adapter; dimensions/profile separately validated | O06 selects typed binding without claiming binary transport or speed |
| CTE materialization repeated per statement; RRF60/channel evidence and witness precedence | O06 compares composed channels with wider SQL fusion, preserving all admission/selection rules |
| ANN/halfvec scale/quality triggers, opaque custom types and native version not freshly checked | O07/O08 conditional adoption and honest fidelity; no fresh runtime qualification claimed |
| Existing PG series, typed metadata, native admission, borrowed publication and outcome model | Preserved foundation across all opportunities; earlier receipts retain original dates/scope |

## Publication and handoff

The functional-review index routes here. Existing active plans retain current accepted scope and
finding disposition; this account owns unscheduled recommendations and their revisit conditions.
Only research documents, navigation and handoff change in this publication. No dependencies,
production interfaces, native schema, project selection or corpus operations change.
Documentation validation is reported by actual command/outcome in STATUS. Selected opportunities
can proceed through create-plan with their O references and concrete mechanisms preserved.
