# Native object authoring, evolution and syntax

**Implemented and targeted Tested, 2026-11-01.** [Coordinator](../postgresql-capability-leverage_2026-11-01.md)
owns PG-01/08/09 and PG-I01. This develops O06/O07/O08/O10/O12 from the
[integrated review](../../functional_reviews/postgresql-capability-leverage_2026-11-01.md)
at `09d3125e`. PG-01/08/09 and PG-I01 are complete within the coordinator's
[final-source targeted qualification](../postgresql-capability-leverage_2026-11-01.md#completion-and-retained-evidence).
The retained design contracts below describe the delivered boundary; extension examples are
identified explicitly. They do not claim a main-database deployment or PDF RC12 cutover.

## Selected mechanism and operator correction

**Do not add Alembic Utils.** The operator excluded that separate package and authorized
recreating particular valuable features when their value is compelling. The review's
companion-library comparison is superseded for this series; the review remains evidence.
Select SQLAlchemy Core metadata/DDL and Alembic's native Plugin, comparator, operation and
rendering interfaces, with pglast for residual syntax work.

Alembic owns comparison dispatch, operation containers, revision history and execution.
SQLAlchemy owns ordinary relational expressions and dialect DDL. The application supplies
only the missing PostgreSQL responsibility: an explicit desired native-object set, comparison
of its meaningful catalog properties, and create/replace/drop operations for selected families.
It retains semantic SQL bodies, privilege policy, deployment identity and independent admission.
This is not a universal reconciler, another revision graph or a reverse-history store.

```text
model definitions + physical metadata + explicit managed scope
  -> prepared desired native objects and comparison expectations
  -> Plugin comparator alongside Alembic's ordinary comparators
  -> MigrationScript / UpgradeOps / supported reverse operations
  -> renderers -> immutable revision payload and authoring artifacts
  -> existing history on the caller's Connection
  -> independent native admission and actual consumer operation
```

The selected migration route is **online only**, matching the current semantic environment.
Rendering operations for inspection is supported; executable offline migration SQL is not
selected. An operation never opens an Engine, borrows another connection, commits, or advances
the version table itself. Alembic's existing history supplies revision movement.

## As implemented and qualified

**Implemented and targeted Tested, 2026-11-01.** Current source maps the selected mechanism to
these public application contracts:

| Responsibility | Delivered route |
|---|---|
| Definition, identity and normalization | [native_objects.py](../../../python/corpus-structure/src/corpus_structure/semantic/native_objects.py): `NativeIdentity`, `NativeDefinition`, `definition_from_sql`, `NativeObject`, `NativeAuthoring` and `prepare_native_authoring`. Explicit dependency-ordered definitions are normalized in rollback-only savepoints on an explicitly owned maintenance database. |
| Comparison, rendering and execution | [alembic_native.py](../../../python/corpus-structure/src/corpus_structure/semantic/alembic_native.py): Plugin `corpus.semantic.native`, `compare_native`, and frozen payload-v1 `NativeTransitionOp`; rendered directives call `op.native_transition`. |
| Recurring candidate and predecessor | [native_candidate.py](../../../python/corpus-structure/src/corpus_structure/semantic/native_candidate.py): `prepare_series_candidate`, `current_native_state`, `load_native_state` and `candidate_admission_sql`. Predecessors come from the revision's digest-bound native-state file or an explicit state file, never live catalog adoption; the bounded 0065 source fallback remains explicit. |
| Operator authoring | [schema.py](../../../python/corpus-structure/src/corpus_structure/cli/schema.py): `ci schema native-candidate --authoring-database … --out … [--predecessor-state …]` writes `native_candidate.py`, `native_operations.json` and `native_admission.sql` after rollback. It requires a separate owned database and new output directory; it does not deploy or advance revision history. `ci schema derive` remains a foundation preview. |
| Frozen realization | [0066](../../../python/corpus-structure/semantic_alembic/versions/0066_postgresql_capability_leverage.py), revision/head `semantic_pg_20261101`, binds ten native objects and admission SQL by digest, executes frozen operations once, and independently admits the desired state on the caller's Connection. The execution ABI is 18. Downgrade refuses before effects. |
| Source-qualified syntax | [prepared_sql.py](../../../python/corpus-structure/src/corpus_structure/semantic/prepared_sql.py): `prepare_sql`, `PreparedSQL`, `SQLSyntaxError`; [native_inventory.py](../../../python/corpus-structure/src/corpus_structure/semantic/native_inventory.py) shares this route with current inventory, authored-SQL admission and native function-body consumers. |

The frozen ten-object set contains the native record shape and context reader, the companion-pin
guard and four published batch readers, the selected-source reader, and the execution descriptor
and enforcing guard. Generic native operations support functions, ordinary views and triggers;
policies, procedures and SQL-standard function bodies are outside the selected implementation.
The narrow [defaults adapter](../../../python/corpus-structure/src/corpus_structure/semantic/alembic_defaults.py)
remains: pinned Alembic's callable-default path accesses `Identity.arg` before identity dispatch.
The adapter routes identity comparison to the existing dialect comparer; its separate volatile
UUID-default exception is scoped to `ops.task.invocation_key`. Neither is replaced by Alembic Utils.

The coordinator retains the exact final command and outcome in
`build/test-receipts/qualification/pg-series-final-c5394eaa`: **passed**, 319 selected affected
cases at production source `c5394eaa`, including actual PostgreSQL/native admission, caller rollback,
recurring authoring and syntax consumers. The native-focused controls are in
`test_alembic_native.py`, `test_postgresql_capability_adoption.py`, `test_prepared_sql.py`,
`test_native_inventory.py` and `test_native_candidate_cli.py`. This document correction changes no
production source. The receipt is targeted series qualification, not a broad repository pass,
main-database deployment or measured performance claim.

## Foundations and integration seams

**Source-inspected, 2026-11-01.** These consumers are the implemented integration baseline.
Their existence does not transfer unfinished PDF obligations into this series.

- [Semantic migrations](../../../python/corpus-structure/src/corpus_structure/semantic/migrations.py)
  supply `Config.attributes['connection']`; `upgrade` runs on the caller's transaction.
  [env.py](../../../python/corpus-structure/semantic_alembic/env.py) configures shared metadata,
  schema filtering, CHECK/default plugins and `on_version_apply`.
- [Native products](../../../python/corpus-structure/src/corpus_structure/semantic/native_products.py)
  compile Core DDL, assemble semantic SQL and inspect functions/grants/triggers for expected
  deployment descriptors. `source_view_native.native_admission_sql` refreshes successor
  inventories while retaining explicitly frozen predecessor material.
- [Record](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_publication_native.py)
  and [staging](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_staging_native.py)
  authors combine physical changes, grants, functions and admission. Current
  [published readers](../../../python/corpus-structure/src/corpus_structure/semantic/pdf_record_reader_native.py)
  provide real forward-function consumers; this series changes their authoring route, not their
  independently owned product behavior.
- [Function signatures](../../../python/corpus-structure/src/corpus_structure/semantic/native_function_signatures.py)
  already distinguish input-bearing arguments from OUT/TABLE outputs.
  [Authored SQL](../../../python/corpus-structure/src/corpus_structure/semantic/authored_sql.py)
  already uses `Visitor`, `referenced_relations`, restricted catalog analysis and original SQL.

Current forward native authoring delegates selected object comparison, replacement sequencing
and rendering to the shared route above. Necessary historical reproduction remains frozen.
Version-specific 0050/0052/0053 helpers are not refactoring targets merely because their loops look alike.

## Desired objects and observed catalog properties

### Preparation and ownership scope

Prepare one immutable authoring input for a candidate: desired owned definitions, their source
references, explicit prerequisites and the predecessor owned inventory. Derive it from current
semantic/native authorities. Ordinary values and functions suffice; no durable registry is added.

Pass it through `Config.attributes['native_authoring']`. `env.py` passes it into
`context.configure(native_authoring=...)`; the comparator reads
`autogen_context.migration_context.opts['native_authoring']`. This is an application-defined
context option, not a built-in Alembic option. Shared runtime `MetaData` stays unchanged.
An ordinary upgrade replays frozen operation payloads without today's desired collection.
Native autogeneration requires this explicit input; absence never means "drop native objects".
If native comparison is requested without it, report the missing authoring context rather than
claim an empty native comparison. Ordinary upgrade execution does not request this comparison.

The comparison scope is the union of explicitly desired and predecessor-owned identities.
The `NativeAuthoring.retire` set must exactly equal removed predecessor identities;
`recreate` must name identities present in both predecessor and desired state. Definition order
is explicit dependency order. Dropping requires accounting for dependents.
Unrelated objects in the same schema survive. Extension-owned objects and externally provisioned
roles remain prerequisites. Schema discovery is not authorization to adopt or remove objects.

### Identity, equality and residual PostgreSQL behavior

| Family | Required identity and comparison meaning |
|---|---|
| Function | Structured schema/name and ordered input-bearing types; INOUT participates, OUT/TABLE does not identify an overload. Compare body, language, return/set semantics, volatility, strictness, security, parallel/leakproof settings, configured GUCs, owner and effective EXECUTE privileges separately. |
| View | Schema/name, view kind and query representation, plus selected options, owner and grants. A changed query does not authorize dropping dependents. |
| Trigger | Owning relation and trigger name; compare called function, event/timing/level, condition, enabled state and selected definition fields. |
| Policy (unselected extension) | No managed policy consumer was selected; policy comparison/operations are not implemented by this route. A future consumer would need relation/name identity, command, roles, permissiveness and USING/WITH CHECK. |
| Privilege/ownership effect | Object identity, grantee/owner and action with explicit before/after expectations. A matching body never establishes the right owner, search_path or grants. |

Use schema-qualified names and native identifier composition. Database OIDs are temporary
catalog locators, never persistent semantic identities. Start from the existing input-signature
helper; PG-01 exercised quoted identifiers, type-alias normalization and INOUT/OUT/TABLE cases.
Resolve overloads through PostgreSQL's input-type identity. Inspect `pg_proc`, namespaces,
languages and types; `pg_get_functiondef` supplies diagnostic text, while actual catalog fields
supply function properties. Compare controlled bodies against `prosrc` under the language
contract. Configured GUCs and owners remain independent checks.

Use PostgreSQL ACL facilities for effective EXECUTE privileges, including default privileges
when `proacl` is NULL, PUBLIC and relevant grant options. A NULL ACL is not an empty privilege
set. Do not recreate an ACL parser. Observe ordinary view and trigger properties through catalog
fields and `pg_get_viewdef` or `pg_get_triggerdef`. No policy projection is selected.
The [pg_proc catalog](https://www.postgresql.org/docs/current/catalog-pg-proc.html) defines the
input-only `proargtypes` and independent function properties;
[system information functions](https://www.postgresql.org/docs/current/functions-info.html)
supply definition and ACL inspection. These are catalog observations, not a second domain model.

Select conservative comparison, not a general SQL equivalence engine. Exact authored bytes,
comparison forms and actual admission properties are distinct. When a selected property needs
server normalization, derive its expected representation by applying the desired candidate in an
owned authoring database under declared settings, then comparing equivalent catalog projections.
The implemented normalization applies complete definitions, then freezes the selected catalog
projection: function body/arguments/result/settings/security/owner/ACL and supporting function
properties, ordinary view query/options/owner/ACL, and trigger definition/owner/enabled state.
Never simulate DDL on a reader or adopt live state as desired meaning. Unsupported selected properties refuse with object/source context;
they are not silently discarded. Empty autogeneration means only that enabled comparison found
no supported change, not that every native contract has been verified.

## Alembic extension, candidate rendering and execution

### Comparator composition

Import a small native extension module from `env.py`, alongside the defaults plugin. Register
its `Plugin` name in `autogenerate_plugins`, retaining `alembic.autogenerate.*` and the selected
CHECK/default plugins. Use `Plugin.add_autogenerate_comparator` at schema scope. Its callback
receives `AutogenContext`, `UpgradeOps` and schemas, observes only the declared native scope,
and appends required native operations to `upgrade_ops.ops`.

Return `PriorityDispatchResult.CONTINUE` normally. `STOP` suppresses subsequent comparators in
the same chain; it does not mean only "this object was handled". This matters when composing
native comparison with existing ordinary schema comparison.

`produce_migrations(MigrationContext, metadata)` produces the standard `MigrationScript`.
Tables/columns/indexes/constraints retain normal Alembic directives. Native effects join its
`UpgradeOps`; they do not form a second executable migration system. The implemented path
validates candidate context and transitions in preparation/comparison and operation construction. `process_revision_directives` and `Rewriter` were considered extension
points, not installed requirements or current application APIs. Generated Python is rendered from
operations, not parsed to manipulate migration meaning. A backend-wide `DefaultImpl` is unnecessary.

Order effects from current model/product prerequisites: create a function before its trigger,
retire an allowed dependent before dropping its provider, and establish owner/grants before
admission and activation. SQLAlchemy handles ordinary table/FK ordering and separately emitted
cyclic constraints. Name sorting is not native dependency analysis. Actual candidate application
and invocation challenge the declared order; no speculative dependency-discovery solver is added.

### Operation payload and historical behavior

The implementation uses one `MigrateOperation` subclass, `NativeTransitionOp`, for selected
create/replace/drop and complete privilege effects. Its frozen payload contains identity and
sufficient before/after definition/effect material for rendering and later execution. Freeze required executable material in revision literals or
existing immutable digest-bound artifacts, not imports of current mutable generators. Source
references provide provenance and diagnostics; they do not substitute for available definitions.

`Operations.register_operation` exposes a directive whose classmethod constructs the operation
and calls `operations.invoke`. `Operations.implementation_for` supplies execution.
`renderers.dispatch_for` supplies Python rendering; add stable imports through
`autogen_context.imports`. `render_python_code` previews the operation representation; normal
revision generation supplies revision IDs and history. Keep the stable operation implementation
and payload format usable by frozen revisions. A future meaning change gets a deliberate new
contract rather than silently reinterpreting an old payload.

Ordinary relational changes retain Alembic directives. Selected native function/view/trigger
definitions retain trusted generated PostgreSQL SQL with explicit identifiers; `CreateView` was
an illustrative option, not an implemented SQLAlchemy Core API used by this route. Execute on
`operations.get_bind()`, using exact driver SQL when preserving archived colon/percent content
requires it: `op.execute(str)` coerces to SQLAlchemy `text()` and can interpret bind syntax.
Runtime values still use parameters. The implementation neither commits nor alters driver
transaction state independently of the caller.

Replacement uses CREATE OR REPLACE only for changes PostgreSQL permits. An incompatible
signature/result change requires explicit dependent changes and an allowed drop/create path;
never add CASCADE implicitly. Owner, grants and configuration remain visible effects when the
body is unchanged. A stale expected before-state refuses instead of overwriting unexpected
catalog changes. Migration execution remains serialized by the operator/deployment owner.
PostgreSQL's [CREATE FUNCTION contract](https://www.postgresql.org/docs/current/sql-createfunction.html)
preserves ownership/permissions on replacement, but other properties take specified or implied
values. Emit the complete selected function configuration so an omitted clause cannot reset a
required property. A return-type change requires a distinct drop/recreate transition.

`reverse()` returns the actual previous definition/effects for supported reversals. A drop is
not recovery of a prior body. If required before-material or a valid reversal is unavailable,
refuse automatic generation of that transition. An explicitly authored forward-only revision
must refuse downgrade before any effects, consistent with the existing semantic rebuild policy.
No reverse-history service or best-effort downgrade is introduced.

All selected transactional object changes and revision movement use the existing caller
transaction. `on_version_apply` observes a step before final commit; it does not prove durable
completion. Independent native admission checks actual installed properties before activation.
Normal application connections never receive migration credentials.

### Exercised forward changes

**Targeted Tested, 2026-11-01.** The representative protected-family control uses a disposable
quoted schema with an overloaded function, dependent view and trigger. It changes body,
strictness and trigger condition alongside an ordinary table alteration, renders and executes
frozen payloads, invokes the view and restricted reader, preserves an unowned overload, detects
forged search_path, and restores prior state on caller rollback. A fresh process executes the
literal without importing today's native author generators. Other native controls cover explicit
retirement/reversal, result/OUT-slot recreation, dependency ordering and ACLs independent of
ambient default grants.

The actual series transition freezes the ten-object set listed above. Adoption controls establish
one current head, byte-bound inputs before effects, ABI 18 native admission, wrong-predecessor
refusal, shared revision/object rollback, regenerated-data activation/publication, and recurring
current-head authoring that remains empty until a controlled definition changes. The earlier
`ops.read_pdf_record_rows` filter-change story was illustrative; no new filter was required or
delivered by this series. PDF product behavior and main-database cutover retain their own owner.

## Prepared syntax: source, mutation and consumer lifetime

`prepare_sql` prepares only useful shared syntax for current forward inventory, native admission input,
authored-SQL diagnostics and operator inspection. Retain exact immutable SQL, source identity,
statement slices and the selected derived facts. This is process-local preparation in an
explicit authoring context, not a persisted universal AST or second SQL semantic model.
Release it when that context ends. Any useful bounded reuse across contexts keys on exact source
and parser/interpretation settings, not filename or model revision alone.

Parse once through `parse_sql`; use high-level `Visitor.__call__` actions and
`referenced_relations` for its supported syntactic relation set. That set loses occurrence and
read/write distinctions; preserve those separately when an actual operation needs them. Catalog
resolution, privilege/volatility policy and live publication/task state remain outside the product.

Shared parsed nodes are read-only by contract. A transforming consumer gets a private clone via
supported node serialization/construction, or reparses exact source when simpler. It never
mutates another consumer's shared tree. Visitor changes are deferred, and inserted/replacement
subtrees are not automatically revisited: use deliberate successive passes and discard ancestry
paths after mutation. `Visitor.iterate()` expects explicit actions; consuming it with an ordinary
for-loop is not an equivalent read-only walk.

Use fresh `RawStream`/`IndentedStream` instances per regenerated product. They own mutable
buffers and expression context; their public call populates ancestry for printing. Reuse native
identifier, list and grammar-position printing instead of recreating precedence rules. Global
printer overrides and a new generic AST framework are not selected. PL/pgSQL bodies remain
strings in the SQL AST; procedural-parser dictionaries do not supply typed-node rewriting or
procedural scope resolution.

For exact diagnostics, combine `split(only_slices=True)` with original text. Retain the full
source because splitting trims statement-edge whitespace. Scanner splitting can identify lexical
statements when grammar failure prevents parser splitting; it does not validate their grammar.
Record the originating coordinate API: raw native/JSON positions are UTF-8-based, higher-level
scan/split interfaces adapt positions for Python strings, and ParseError exposes its position
in `args[1]`, possibly None. Convert known byte offsets with `Displacements`; double conversion
corrupts Unicode positions. Token ends are inclusive. Unknown spans remain unavailable.

Comments are separate metadata: a native match anchor is not a high-level comment-start position.
Exact excerpts come from original source; regenerated SQL has a distinct identity/provenance.
AST equality ignores positions and cannot establish source preservation. Fingerprints can group
diagnostic query shapes but never replace admitted bytes, semantic identity or dependencies.

## Completed work packages and acceptance contracts

**Implemented and targeted Tested, 2026-11-01.** PG-01/08/09 and PG-I01 are closed by the
coordinator's final-source targeted evidence. The retained inputs, outputs and acceptance
contracts below explain the delivered scope; they are not an execution queue. Future extensions
must preserve these boundaries without treating every illustrative mechanism as implemented.

### PG-01 / PG-I01 — Representative native extension integration

**Inputs:** refreshed current forward authors, the desired/observed contract above, existing
Connection/history and native admission. **Output:** the smallest working Plugin comparator,
operation, renderer and authoring-input path for an actual protected family, with resolved
property comparison/server-normalization behavior. This is an integrated prerequisite slice,
not a separate framework or another comparative review.

Inspect native library/source contracts first. Use a disposable owned authoring database only
for remaining server semantics. Exercise input/OUT/TABLE distinction, a dependent view/trigger,
relevant grants, quoted names and literal colon/percent content. Include a policy only when one
is actually managed. Simulated preparation, if required, is explicitly rolled back; no such DDL
runs on ordinary reader connections.

**Completion evidence:** native candidates coexist with ordinary Alembic changes; same supported
state produces none; one changed property produces the correct effect; unowned objects survive.
A fresh process executes the frozen payload without consulting current authoring models. Caller
rollback restores object and revision state. Wrong owner/search_path/grant independently fails
native admission, and a valid restricted consumer still works. PG-I01 records the exact technical
result and any unsupported property; failure does not authorize the excluded package or a
universal reconciler. PG-08 used this resolved integration result.

### PG-08 — Candidate evolution and series-owned transitions

**Inputs:** PG-01's working extension/property surface and relevant shared physical preparation.
**Output:** current forward authoring and admission consume one desired native specification,
Alembic operation lifecycle and explicit transition. Migrate both producers and consumers in
this package, then retire the replaced mechanical inventories/rendering. Keep any necessary
frozen route explicit instead of rewriting historical SQL.

Wire desired preparation into the authoring command/environment, schema comparison into the
normal candidate, renderers/imports into revisions, and execution into existing history.
Descriptor properties must derive from selected definitions rather than stale hardcoded owner,
configuration or function defaults. Independent live admission remains essential: construction
and enforcement consuming one definition do not make a shared producer expectation an oracle.

Schedule only this series' actual data/realization changes. Server rows favor set transformations;
Arrow replay uses directional transfer; envelope JSON reuses its parser only when needed by this
change. `alter_column(postgresql_using=...)` handles a selected SQL conversion, not every data
migration. Eligible NOT VALID/VALIDATE separates installing enforcement from verifying old rows.
Concurrent indexes need a separate deployment transaction/restart contract and may remain invalid
on failure; autocommit commits earlier work. Prefer transactional alteration/rebuild without a
continued-writer requirement. None of this completes former PDF adoption/final validation.

**Completion evidence:** fresh databases reach the intended current managed state; data is regenerated and retained historical baselines require no compatibility support;
incompatible candidates refuse; no-change comparison does not oscillate; frozen before/after
payloads remain executable. Exercise changed body, return/configuration, grant, trigger condition
and explicit retirement against independent expected outcomes. Challenge dependent ordering with
actual invocation, not just parsing. Include rollback after partial transactional DDL, unsupported
reverse refusal before effects and admission rejecting forged catalog state. Integrated product
qualification remains the coordinator's responsibility.

### PG-09 — Residual prepared syntax and author diagnostics

**Inputs:** settled native operation boundaries and actual current diagnostic/inventory consumers.
**Output:** a scoped source-qualified syntax preparation route, explicit mutation ownership and
useful refusal messages naming the actual source/object/statement location. Migrate current
consumers together; retain no competing parse merely to preserve an obsolete helper interface.
This preparation never replaces live admission or current authorization.

**Completion evidence:** nested/nonrecursive/recursive CTE scope, forbidden descendants, multiple
statements, quoted names, semicolons within strings/dollar quotes, and Unicode before a failure.
Two consumers sharing source remain isolated when one transforms it. Changed source invalidates
preparation; stale positions are not applied to transformed text. Assert exact source excerpts
and independently expected transformation meaning. Parse-print-reparse checks cover structural
serialization only. Preserve unknown positions, comment limits and original/rendered identities.

## Library evidence, design reasoning and limits

The extension mechanics were checked through Context7 and primary documentation on 2026-11-01.
Those sources support library-interface claims; the implementation mapping and coordinator receipts
above establish the separately bounded integration result. No measured benefit is claimed.

- [Alembic native Plugin API](https://alembic.sqlalchemy.org/en/latest/api/plugins.html): schema
  callback arguments, comparison-chain participation and CONTINUE/STOP behavior.
- [Operation directives](https://alembic.sqlalchemy.org/en/latest/api/operations.html),
  [autogeneration](https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html) and
  [runtime configuration](https://alembic.sqlalchemy.org/en/latest/api/runtime.html): stateful
  operations, directive/implementation/reverse/render dispatch, context and history boundaries.
- [Local Alembic original §§4–8 and addendum §§1–7](../../libraries/postgresql/alembic.md):
  comparison limits, extension-layer choice, text execution, transaction-sensitive DDL and the
  distinction between schema/history/data verification.
- [SQLAlchemy schema/DDL reference](../../libraries/postgresql/sqlalchemy.md) and
  [Core DDL](https://docs.sqlalchemy.org/en/21/core/ddl.html): metadata, normal schema operations
  and table/FK dependency handling stay with existing library mechanisms.
- [pglast parser/source interfaces](https://github.com/lelit/pglast/blob/v8/docs/parser.rst),
  [Visitor source](https://github.com/lelit/pglast/blob/v8/pglast/visitors.py),
  [stream source](https://github.com/lelit/pglast/blob/v8/pglast/stream.py), and
  [local original/addendum](../../libraries/postgresql/pglast.md): slices/displacements,
  action-driven deferred edits, mutable streams and procedural/source-preservation boundaries.

FP-01/04/06, DP-06/13–16/24 and H4/H12/H27 favor one explicit definition and narrow useful
extensions on an established lifecycle. Work follows the owned candidate rather than every
object in the database. Stable preparation is reused by actual consumers; credentials and
migration exclusion remain outside ordinary processing. The selected normalization and
protected-property integration are implemented and targeted Tested, 2026-11-01. Residual limits are deliberate: owned online authoring only; explicit scope and
dependency order; selected function/view/trigger properties; no implicit CASCADE, universal SQL
equivalence, policy/procedure support, deployment automation or historical-data compatibility.
Historical data may be regenerated during this design phase. The frozen revision is forward-only;
supported individual operations still retain their true before-material for reversal. No quantitative
performance, repository-wide qualification or main-database cutover claim follows.
