# SQL explanation and source-aware authoring

**Status: Planned; execution not started · 2026-11-09.** Target design is Proposed. The
[coordinator](../postgresql-typed-domain_2026-11-09.md) owns all package/decision state, source
correspondence and combined qualification. This companion owns the design and local acceptance
below, not another status table. No product or database changes were made while authoring.

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
