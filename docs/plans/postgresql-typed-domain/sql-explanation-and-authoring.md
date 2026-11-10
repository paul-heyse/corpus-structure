# SQL explanation and source-aware authoring

**Status: CA03 validation detail delivered; PTD-04/05 scoped controls passed; I02 decided · 2026-11-10.** Selected package delivery is Tested at the scope recorded by the coordinator; conditional targets remain Proposed. The
[coordinator](../postgresql-typed-domain_2026-11-09.md) owns all package/decision state, source
correspondence and combined qualification. This companion owns the design and local acceptance
below, not another status table. The coordinator records execution separately from original authoring.

## Basis and focused foundation assessment

Consumes [O03/O04](../../functional_reviews/postgresql-typed-domain_2026-11-09.md). PreparedSQL already owns source/slices/Unicode diagnostics/private
clones. ProjectionAnalysisProduct already archives projection-analysis-2 and native impact reporting
compares value and relational dependencies. These owners support the target; retain them rather than
create another SQL compiler, provenance store or full-path graph. Richer detail changes an archived
product contract and must migrate its readers, not rerun today's analyzer to explain old data.

## PTD-04 · Attributed projection explanations

Extend the current product with bounded dependency occurrences: checked model/source reference,
output or clause occurrence, relationship kind (value versus membership/order influence), endpoints
and explicit unknown reason. Identity follows the checked recipe occurrence plus stable structural
role, not mutable AST object identity or a table-name set. Do not enumerate all paths. Capture detail
at preparation and expose bounded requested detail through current operation explain/impact and
validation report owners. Use lineage(on_node)/Node.payload and scope-aware traversal only where
they preserve occurrence attribution through copies/qualification; otherwise retain the explicit
recipe walk. Hooks are an enabling implementation, not a reason to manufacture provenance.

Keep native overload/argument authority with checked helper signatures. udf_mapping alone is not
wired into selected annotate_types; retain explicit helper .type and overwrite_types=False. Unknown
body meaning remains unknown. Treat missing analysis and incomplete coverage as unavailable, not
no dependency. Produce a new explicit product/profile version, with exact source/analyzer/runtime
determinants. Current-only production regenerates affected derived analysis; archived old results
retain truthful available detail without acquiring contemporary analysis by reconstruction.

Migrate preparation, archive admission/reading, compare_semantic_releases/_projection_impact,
projection_validation_report, CLI/model report serialization and registered agent consumers of those
reports. Preserve compact tuple summaries as projections of the same authority, not parallel authoring.
Acceptance: two references with equal endpoints remain separate; WHERE edit differs from output edit;
opaque helper stays unknown; CTE shadowing/correlation is resolved under the correct scope when
supported; input trees remain unchanged; wrong/missing origin refuses. Independent expected roles
must challenge attribution, not simply rerun lineage as an oracle.

## PTD-05 · Candidate SQL diagnostics and impact

Extend existing model-change preview/candidate inspection with source excerpts, located diagnostics,
structural edit descriptions and O03's affected-dependency explanation. Reuse the managed candidate
artifact/report and `ci model change` surfaces; no new generic SQL editor or query endpoint.
AST diff describes edits, not equivalence or safe migration. Native admission/catalog status remains
a distinct observation; source text/rewritten locations must remain distinguishable.

Use existing PreparedSQL and private pglast AST clones/printers for supported structural authoring;
SQLGlot diff is optional when its edits improve the existing report over declaration-level changes.
Preserve loaded overload identities and original Unicode positions. Candidate generation remains
explicitly provisional; inspection never authorizes later effects. Remove only independently rebuilt
source/diagnostic facts that the existing owners now supply.

Deliver current CLI/machine candidate inspection for a changed predicate with affected consumers,
Unicode parse refusal, unchanged declared output with changed membership influence, and an opaque
native helper boundary. Archived/read-only inspection must not execute submitted data queries.

## PTD-I02 · Language, procedural and portability branches

Decide separately: finite nested/aggregate/window/recursive/JSON-path/PIVOT recipe additions;
procedural helper inspection; controlled portability/query laboratory; cross-language serialization,
fingerprints and custom dialect/parser/printer extensions. Select a bounded consumer before expanding
the IR, with Core execution, qualified scopes, output shape and predicate effects co-designed.
Current IR lacks general subqueries; this is no diagnosed nested-query defect.

For procedural inspection, parse_plpgsql dictionaries can describe candidate structure but dynamic
SQL, exception flow and native binding stay unknown. For portability, pin dialect/schema and selected
transforms; unsupported_level=RAISE is refusal behavior, not semantic parity. Use independent known
results at the destination if execution equivalence matters. PythonExecutor, SQLFrame and acceleration
must justify an actual laboratory workload against the existing Core/DuckDB route.

Every branch closes by reasoned selection, retain/reject, or deferral with a workflow trigger.
A selected expansion gets PTD-10 contracts, affected producers/readers/consumers, admission and
native qualification before effects. Parameterized authored SQL is a pending D8 support decision;
this plan selects no general authored-query expansion in advance. Comments/meta directives and
fingerprints cannot confer semantic identity, and unavailable pglast normalize/enum_name APIs cannot
be dependencies. AST structural equality differs from SQL predicates and equivalence.

Sources: [projection analysis](../../../python/corpus-structure/src/corpus_structure/semantic/projection_analysis.py),
[reporting](../../../python/corpus-structure/src/corpus_structure/semantic/operation_reporting.py),
[SQLGlot30.27 lineage](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/lineage.py),
[scope](https://github.com/tobymao/sqlglot/blob/v30.27.0/sqlglot/optimizer/scope.py),
[pglast8.7 visitors](https://github.com/lelit/pglast/blob/v8.7/pglast/visitors.py).

## PTD-04/05 execution mechanisms · 2026-11-09

Selected SQLGlot30.27 lineage deduplicates equal Column expressions; checked recipe structural
occurrences own multiplicity. Capture value/membership(where/join)/ordering roles, relationship
identity, local derived edges and explicit unknown boundaries. Qualification/explicit helper typing
and annotate_types(overwrite_types=False) remain; helper body meaning stays unknown. Summaries
project the same occurrence authority without all-path expansion or richer IR language adoption.

Write projection-analysis-3 / companion-query-analysis-3; normalize archived2/3 reads with v2 detail
unavailable and no contemporary reanalysis. Semantic compiler19 retains18 reading; native current/
readable guards change together, independently of execution compiler28. Reportversion2/schema/
registered consumers migrate with bounded family/output/occurrence detail and deterministic paging.

Model-change SQL explanation retains original PreparedSQL source/slices/parser/digest/coordinates
and private pglast trees. SQLGlot diff(delta_only=True) describes supported SELECT edits without
establishing equivalence. model-change-explanation-1 publishes under managed sql_explanation;
preview/candidate --view sql can read settled failed diagnostics without effect eligibility.
Captured before-source remains the authority during later inspection; no submitted data query runs.


## PTD-I02 decision account · 2026-11-09

**Interface-checked / Proposed dispositions.** Source inspection at `baea0ed8e`, including
`projection_recipe.Expression`/`core_statement`, `pm2_coverage`, `contextual_retrieval`,
`analytics.AnalysisScope`, `prepared_sql`, `projection_analysis` and `operation_reporting`, settles
this bounded inquiry. These are current consumer comparisons, not claims that other query needs
cannot arise. No executable language extension is selected by I02. Existing specialized Core and
DuckDB operations answer the examined questions without making the model recipe a second general
SQL language (FP-01/03/04, heuristics H3/H8/H12).

| Named branch | Disposition and consumer/alternative comparison | Revisit condition |
| --- | --- | --- |
| Nested/correlated recipe expressions | **Retain** the finite recipe. Existing source qualification and contribution comparisons use specialized Core joins/EXISTS; `core_statement` already lowers declared derived sources to CTEs. Adding general scalar/correlated subqueries would require new scope/cardinality semantics and archived attribution, without removing an examined consumer's custom semantic decision. | A released companion needs a repeated model-authored correlated value/predicate that cannot be represented by current declared sources or a typed operation. |
| Aggregate recipe expressions | **Retain** specialized Core/DuckDB aggregation. Coverage groups and `AnalysisScope.fact_support`, `value_roles` and `disagreements` already own explicit grouping, empty-list/null and occurrence rules. Moving these distinct products into the recipe would also move their semantic ownership. | A released companion output requires model-authored grouping and a declared typed aggregate contract. |
| Window recipe expressions | **Retain** specialized Core `row_number().over()` for retrieval ranks and DuckDB windows for analytical alias counts. These are policy/operation-owned ranks, not missing value constructors. | A released recipe declares a window output with partition, tie and frame meaning shared by execution and explanation. |
| Recursive recipe expressions | **Retain** specialized Core recursion in coverage; resident inference is selected under I03 without expanding recipe syntax. A generic recursive recipe would add cycle/completeness and archive obligations to consumers that do not need them. | A model-owned recursive output, distinct from the existing coverage/inference algorithms, has a concrete consumer and finite edge semantics. |
| JSON/JSONPath expansion | **Retain** existing `JsonPath` lowering for declared field/index/text paths and specialized native/Core JSON recordset/table-valued operations. General JSONPath predicates/array expansion need distinct missing/SQL-null/JSON-null/cardinality rules; no examined companion requires that expansion. | A concrete released nested-value read cannot preserve its meaning with current paths and needs a typed expansion result. |
| PIVOT/UNPIVOT, pipe SQL and temporal-format extensions | **Retain** long-form comparison outputs and existing typed kernels. Current coverage and companion comparison do not require a dynamic column universe; PIVOT would obscure explicit unmatched/incomparable rows. | An actual operator report requires a finite declared column set or an unsupported temporal/path construct, with unknown-category and output-type rules. |
| Procedural helper inspection | **Retain** declared helper signatures, native binding/admission and explicit opaque-body explanation. Native `closure.sql` includes dynamic workspace/DDL operations; dictionary parsing cannot settle their dependency/effect meaning. A second static body account would not replace those authorities. | A concrete helper-body investigation needs a bounded syntactic call/statement inventory; use pglast `parse_plpgsql`, retaining dynamic SQL, exceptions and runtime binding as unknown. |
| Controlled portability | **Retain** native PostgreSQL operations plus purpose-built detached DuckDB kernels. `AnalysisScope.fact_support/value_roles/views` construct analytical products, rather than promise that arbitrary PostgreSQL text runs unchanged on DuckDB. | A named query must run on a second destination; declare source/destination/schema/transforms and independent expected null/cast/numeric/collation results before using `transpile(..., unsupported_level=RAISE)`. |
| Alternative query laboratory | **Retain** existing Core → Arrow → `AnalysisScope`/DuckDB. Its owned relations already support scoped composition and detached reproducibility. SQLGlot Plan/PythonExecutor or SQLFrame would add an executor/DataFrame authority without replacing an unmet examined workflow. | A researcher needs a specific alternative plan/DataFrame operation unavailable through the existing scope and can name its input universe and result consumer. |
| Optimizer passes/compiled acceleration | **Retain** selected current qualification/typing passes and native query planning. No observed semantic need calls for a wholesale optimizer or compiled Python executor. | A concrete unsupported rewrite or serious execution regression remains after operation composition; then compare that one pass/accelerator with the native route. |
| Cross-language JSON/Protobuf/AST serialization | **Deferred**: current Rust crate is a starter, and inspected SQL producers/consumers are Python/native SQL plus versioned explanation JSON. There is no selected caller needing a PostgreSQL AST interchange. | An actual caller needs syntax trees rather than retained SQL/explanation products; pin parser/grammar/protobuf or SQLGlot dump/load versions and keep original SQL separately. |
| Fingerprints/canonicalization/anonymization | **Retain** exact PreparedSQL source/digest and structural explanation. A lossy shape key would not identify model semantics, native overloads, release bindings or an admissible cache entry; no examined diagnostic grouping requires it. | A named diagnostic consumer needs shape grouping with explicitly discarded distinctions; never substitute it for semantic or exact source identity. |
| Custom dialect/parser/printer/compiler extensions | **Retain** supported PostgreSQL pglast printing, checked helper typing and current SQLGlot handling. No inspected current recipe or native authoring fragment needs a new dialect; PTD-05 already supplies supported edit/source diagnostics. | A concrete unsupported construct has a complete typed parse/render/admission consumer. Assess public compiler/GenericFunction or printer extension first, preserve opaque `exp.Command` and original coordinates, and reject silent clause loss. |

Parameter admission is owned by I05; this account accepts no D8 change. Existing internal recipe
parameters are not an authored-query permission. Selected-version API inspection with
`uv run --no-sync python -B` confirmed SQLAlchemy2.1.6, Psycopg3.3.6 and pglast8.7;
`parse_plpgsql(statement)` returns a list of dictionaries, Protobuf parse/deparse are present and
`parser.normalize` is absent. This is an interface check, not a native procedural or portability pass.
`get_udf_type` still does not replace checked overload/body authority.

**Outcome:** all named I02 branches have a bounded decision; there is no selected I02 PTD-10 slice.
The conditions above reopen specific capabilities rather than transfer an unperformed investigation
to another plan. Product/native tests and performance experiments are **not_run** for this
source-settled decision account; no product, archive, compiler or database change was made.


## Completion audit · 2026-11-09

PTD-04's occurrence production, truthful v2/v3 reading and explain/diff consumers are delivered,
but projection_validation_report and ordinary schema compile/check did not expose the accepted
bounded requested occurrence detail. Reuse the retained page authority and migrate the validation
report/schema/consumer with explicit archived-unavailable detail; do not conflate that status with
the compact validation complete flag. PTD-05 retains its source/diagnostic delivery. The coordinator's
[completion audit](../postgresql-typed-domain_2026-11-09.md#completion-audit) owns CA03. Fresh authoring
selection fa82bd7fb4694834bcfdc3ef03f552cb passed27 on current product source; broader qualification
remains bounded. I02 decisions were not audited.


## Repair execution · 2026-11-10

The [coordinator delivery receipt](../postgresql-typed-domain_2026-11-09.md#completion-repairs-and-ptd-10-delivery--2026-11-10)
closes the local audit obligations at the scoped boundary and owns current disposition. Historical
audit descriptions above identify the inspected baseline, not an unrepaired current claim.
LocatedValidationReport v3 optionally attaches the existing ProjectionDependencyPage through
projection_validation_report and schema compile/check flags. Compact observations/complete remain
unchanged; v2 detail stays unavailable without reanalysis. Other report payloads remain v2, and
the schema bundle envelope remains operation-report-schema-2. Registration was regenerated.
