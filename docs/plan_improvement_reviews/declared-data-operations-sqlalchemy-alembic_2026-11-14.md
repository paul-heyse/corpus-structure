# SQLAlchemy and Alembic leverage in the declared-data-operations redesign

**Proposed recommendations · 2026-11-14.** Reviews the remaining DDO-00–12 change footprint at
a15f2e197cb7da4e16eae9d6e6fbbbe99e5aa5b2: the
[coordinator](../plans/declared-data-operations_2026-11-12.md) and its ten supporting plans.
DDO-00–05 are complete at their foundation boundary, DDO-06–08 are executing on `main` and DDO-09–12
are open. The Alembic history has 265 revisions and one head, `semantic_ddo_origeps_v1`. The working
tree was clean when the citations below were verified; `main` advanced during the review
(56377252f to a15f2e197), so line numbers are exact only at that commit. Root synthesis with four
bounded independent contributions: two library-contract confirmations at the installed versions, one
producer/consumer map, and one adversarial review of the draft, which withdrew one proposal and
narrowed three. No plan amendment or production change is made by this review.

The root read all 2,950 lines of the [SQLAlchemy reference](../libraries/postgresql/sqlalchemy.md)
(SHA256 7623d90ea8bef3f927eb862da00484ee1b578cc1c873465801b6627f55afb91b) and all 2,417 lines of the
[Alembic reference](../libraries/postgresql/alembic.md)
(a2d1a97b127edf023643c4bbf3ae7e7b578b09e97a34493b36d1213bcfa35f0d), including both addenda. Both are
committed at 5c596c589. SQLAlchemy 2.1.6, Alembic 1.20.1 and psycopg 3.3.6 are installed and exactly
selected; library contracts cited here were confirmed in that installed source, in the tagged
documentation and by offline compilation, never against a database. The overviews supplied leads.
Earlier verdicts are carried with their premises from the
[SQLAlchemy](../library_leverage/libraries/sqlalchemy/README.md) and
[Alembic](../library_leverage/libraries/alembic/README.md) accounts, the
[schema-evolution discovery](../library_leverage/libraries/postgresql/discovery/schema-evolution-and-catalog-admission.md),
[ADR-0047](../adr/0047-current-only-domain-runtime.md),
[ADR-0073](../adr/0073-generated-type-correspondence.md) and
[ADR-0074](../adr/0074-attributed-projection-explanations.md).

Applied core 3.3, efficient-architecture heuristics, code-intelligence 1.4, test-assessment 1.2 and
the repository binding. This is a plan-improvement inquiry, not a broad diagnostic audit, a
completion audit or a formal design review. F01–F14/C1–C7, RC01–09, Python RC01–03, DDO-CA-01–07
and the I-numbers of the [NetworkX](declared-data-operations-networkx_2026-11-12.md),
[Python-introspection](declared-data-operations-python-introspection_2026-11-12.md) and
[ast-grep](declared-data-operations-ast-grep_2026-11-13.md) reviews keep their DDO owner. The
I-numbers below are this review's own.

Plan citations name the companion file and line: for example `contracts-and-compilation.md:75`
is under `docs/plans/declared-data-operations/`. Code paths are relative to
`python/corpus-structure/src/corpus_structure/` unless they begin with `tests/`, `alembic/` or
`sqlalchemy/`.

## Combined judgment

**The DDO series already uses both libraries close to their useful limit at the schema and
migration-lifecycle layers. The worthwhile leverage that remains is narrower than the request
assumed: the relational reads DDO-09 and DDO-10 have not written yet, and the way table privileges
are authored.**

The model compiles to one Core `MetaData`; typed columns and native call bindings are generated;
Alembic's plugin, operation, comparator, renderer and receipt APIs carry the native lifecycle.
Most unused capabilities do not fit this design, for reasons that are deliberate: every DDO table
is unreadable by runtime roles, every effect goes through a native function, releases are rows
rather than schema, and the model and the wire protocol, not Python classes, are the authorities.

What the DDO kernel does not use is the repository's own projection route, in which one Core
statement yields both the Python statement and the native function body
(`semantic/projection_recipe.py`, `companion_projection_native.py`, `native_sql_body.py`). Its
reads are hand-written PL/pgSQL that assemble JSON documents. DDO-09's change and currentness
explanations and DDO-10's pinned read projection for reader, MCP, export and replay are about to
add more of them.

Recommend:

- **[I02](#I02)** for the projections DDO-09/10 still have to build. This is the largest gain.
- **[I04](#I04)** so a declared table-role change produces a recorded operation instead of a
  deployment refusal.
- **[I01](#I01)**, reduced to deriving the stored-fate CHECK and the Python fate types from the
  wire protocol that already owns those sets.
- **[I03](#I03)**, reduced to extending the existing shared binding cases.
- **[I05](#I05)** as a small cleanup.

A proposal to route Core comparison through the native comparison functions was withdrawn: those
functions raise on unknown operands, which is right for verifying one selected binding and wrong
for filtering candidates. Three [observed defects](#observed-defects) are listed separately. ORM
mapping, native ENUM types, Alembic Utils, offline SQL mode and revision branches have no current
fit; [Capability coverage](#capability-coverage) gives the reason for each. No throughput, size or
defect-rate benefit is claimed.

## Current footprint and what is already delegated

| Owner | Observed contract and significance for this lens |
|---|---|
| `schema/relational.py:608–770` | Compiles the trusted LinkML physical model to Core `MetaData`: naming convention, digest-named CHECKs, `Identity`, `Computed`, partial and expression indexes, `Table.info`/`Column.info`. LinkML enums become `Text` + CHECK + `Column.info["enum"]` (`:648–649, 677–686, 713–717`). Adopted foundation. |
| `semantic/typed_generation.py:11–19`, `_typed_columns.py` | Generates SQLAlchemy 2.1 `TypedColumns` with nominal identifiers and `Literal[...]` enums for seven relations, none of them DDO. |
| `model/semantic/data-operation-physical.yaml` | 30 DDO classes with no `enums:` block. Closed sets are raw SQL in `ph:checks` (`:407` fate, `:425` selector kind). Every `ph:read_roles` is empty: runtime roles cannot read a DDO table. |
| `model/semantic/data-operation-native.yaml:1`, `semantic/data_operation_wire.py:3` | The wire protocol declares itself authoritative: "Python, SQL and effective kinds derive from these schemas." It already models recordable, historical and visible fates as three lists (`:648, 663, 680`). It is also a captured source for frozen interpretation. |
| `semantic/projection_recipe.py:404–519`, `companion_projection_native.py:25–167`, `native_sql_body.py:19` | The existing one-definition route. One Core tree; native parameter names bound into it; `RETURNS TABLE` derived from compiled column types; the body from `compile(literal_binds=True)`; `sql_standard_definition` for a SQL-standard body. Reader grants attach to the modeled projection, never to tables. No DDO function uses it. |
| `semantic/sql/data_operations.sql` (1,664 lines) | The DDO kernel. Most public functions take one `jsonb` payload and return `jsonb`. In this file: 119 `jsonb_build_object` calls, 32 positional `INSERT`s out of 37, and 16 uses of `ops.ddo_read_visible`. Effects, locks and fences live here by design. |
| `semantic/data_operation_bindings.py:272–1426`, `data_operation_storage.py:821, 888–911` | Core lowering of the binding AST, run by `DemandPlanner.ready`. It resolves candidate rows over `func.ops.data_binding_rows(...).table_valued(...)` and decides sufficiency. Tagged values are decoded by casts chosen per primitive type. |
| `semantic/sql/data_operation_bindings.sql:322, 621` | PL/pgSQL interpreter of the same archived binding AST, run inside `attach_data_request`. It verifies one selected binding and raises on an unknown or mistyped operand (`:119, 165, 186–188`). No dynamic SQL. |
| `tests/semantic/data_operation_binding_support.py:298–463` | `BINDING_EVIDENCE_CASES`: one case set run through the Core lowering and through protected native admission, with separate expected outcomes for each. The file states that "a compiled insufficient result and a protected-admission refusal are different outcomes, not Boolean parity". |
| `semantic/data_operation_storage.py:317`, `data_operation_service.py:132` | `invoke(name, payload)`: every DDO native call is a JSON payload in and out, validated against the wire schemas. `read_demand_result` already has two consumers, the planner and `ci demands`. |
| `semantic_alembic/env.py`, `semantic/alembic_native.py` | Plugin comparators, `NativeTransitionOp` with frozen before/after owner and ACL custody taken from the declared predecessor, renderer, `on_version_apply`, caller-owned connection. Adopted foundation. |
| `semantic/native_candidate.py:2135–2395` | `prepare_series_candidate` calls `produce_migrations`, then rewrites `upgrade_ops` by hand: `SET LOCAL ROLE` brackets, `OWNER TO`, `GRANT`/`REVOKE` from `Table.info["read_roles"]` for created tables only, a name-matched cross-owner foreign key, `eval` schema usage fix-ups and two table-specific backfills. |
| `semantic/native_products.py:90–209, 262–318`, `semantic/sql/admission.sql:130–158` | Physical products from compiled `CreateTable`/`CreateIndex`; an admission descriptor recording each table's read roles and owner; a native guard that compares the catalog, including table privileges, with it. Detection is in place. |
| `schema/model_deployment.py`, `semantic/migration_chain.py` | Wrapper revisions, SHA-256 custody of three sidecar products per revision, and a `RevisionMap` built from AST-parsed metadata so unverified revision files are never imported. `RevisionMap(generator)` is a documented public constructor. |

Three properties of this baseline bound every recommendation. Releases are rows, never schema
(`contracts-and-compilation.md:75`). Declarations carry no SQL text (`:116`). Effects happen only
inside modeled native operations (`products-and-support.md:55`,
`demand-planning-and-execution.md:70`), and desired state is checked against independently
observed catalog facts. A proposal that needs runtime roles to read tables, executes
release-supplied SQL, or lets one construction serve as both a definition and its check is out of
bounds.

<a id="I01"></a>
## I01 — Derive the stored fate set from the protocol that owns it

**Recommend the fate part · DDO-04 physical model, DDO-05/06 consumers; DP-01, DP-03, DP-06, G1.
Identifier typing is conditional on [I02](#I02).**

**Current approach.** The wire protocol owns three fate sets: 12 values a caller may record, 14
that history can hold, 15 that a reader can see (`data-operation-native.yaml:648, 663, 680`). The
physical model restates the 15-value list by hand as a SQL `IN` in `ph:checks`
(`data-operation-physical.yaml:407`). `ops.record_data_fate` restates the 12
(`semantic/sql/data_operations.sql:543`). Python and SQL also carry purpose-specific subsets
(`semantic/data_operation_demands.py:490`, `data_operations.sql:472`). Nothing compares the
physical list with the protocol.

**Proposed change.** Keep the protocol as the owner. Have the relational compiler take the
stored-fate CHECK from the protocol's `historical_fate` list instead of a hand-written
`ph:checks` string, through the path that already turns a value set into a digest-named CHECK and
`Column.info["enum"]`. Generate the Python `Literal` types for the three sets from the same lists.
Do the same for the revocation selector kind (`:425`) if the protocol states it. The derivation
runs from captured sources when the metadata is compiled; frozen interpretation keeps its captured
copy and never resolves a set at run time.

**Mechanism.** `CheckConstraint` under the existing naming convention and `Column.info`. A changed
set changes the CHECK's digest name, which Alembic's CHECK-by-name comparison already detects.

**Preserved.** The three sets stay distinct. `BindingStatus`
(`semantic/data_operation_bindings.py:43`) and input-role states
(`semantic/data_operation_identity.py:94`) share some strings with fates and are different
domains; they are not merged. Outcome names are release data admitted per operation
(`data_operations.sql:309`), so `data_derivation.outcome` rightly has no column CHECK. No
PostgreSQL ENUM type and no SQLAlchemy `Enum` type are introduced.

**Alternative.** Make the LinkML physical model the owner and derive the wire lists from it. That
reverses a stated authority and would need the DDO-03 decision route. Retaining the hand-written
list with an agreement test keeps two spellings and a third place that lists them.

**Why now.** The persistent database has no DDO relation yet, so a renamed CHECK costs one line in
the next successor and a constraint swap on a populated table after DDO-11.

**Conditional: nominal identifiers.** Product, demand, obligation, request and derivation
identifiers are all `Text`. `Named[NewType]` in a `TypedColumns` class propagates statically to
`Column`, `Select` and `Row` types (confirmed with Pyrefly 1.4.0 against 2.1.6), and `with_cols`
changes nothing at run time. Today that has no consumer: Python reads DDO data only as wire
dictionaries. If I02 lands, type its projection row shapes this way. Type the qualified identity;
`member_id` is local to its product and `subject` is a local name within a qualified context, and a
standalone nominal type would misstate both.

**Closure evidence.** Removing a value from the protocol's historical list changes the CHECK name
in the next candidate and fails static checking where Python uses it. A native control inserting a
value outside the stored set is refused. The expected sets are written independently of the
generator.

<a id="I02"></a>
## I02 — Author the DDO-09/10 read projections through the Core projection route

**Recommend for projections not yet built; conditional for `ops.data_binding_rows` and
`ops.read_demand_result` · DDO-09/10, with DDO-03/05 for binding rows; FP-03/04, DP-01, DP-06,
DP-13/14/16, A2/A3, G8.**

**Current approach.** ADR-0047 makes Core the primary relational execution representation, and
D3's "Unified operation realization" records that model-bound expressions generate eligible native
products. The companion projections do that. The DDO kernel, written afterwards, does not:

- `ops.read_demand_result` (`data_operations.sql:1303–1362`) assembles one JSON page inline. It
  states the bounded-obligation CTE twice and the latest-use lateral twice, pages by obligation id
  with a limit of at most 1,000, and returns product bodies in the same document. It also inserts
  the read boundary (`:1333`), so it mixes an effect with a read.
- `ops.data_binding_rows` (`:1576`) states its 16-column row shape in the SQL `RETURNS TABLE`, in a
  Python name tuple and in name-keyed Core types (`data_operation_storage.py:795–840`), and partly
  in `_MEMBER_COLUMNS` (`data_operation_bindings.py:52`).
- 32 positional `INSERT`s depend on catalog column order. One of the five that name their columns
  is `ops.data_population` (`:576`), whose model class gained a column in the middle (22a9a42e3).
  `plpgsql_check` runs at authoring and validates identifiers and types, not which of two adjacent
  `text` columns receives a value.

DDO-10 plans "a pinned DemandResult/CutSelection projection … derived, read-only and rebuildable"
for reader, `ci`, MCP, export and detached replay (`interfaces-and-evaluation.md:10–20`). DDO-09
plans bounded change, currentness and revocation explanations over indexed joins
(`change-reuse-and-consolidation.md:85–88`). Those readers do not exist yet.

**Proposed change.**

1. Write each new DDO-09/10 projection as a Core select over the shared `MetaData`: selected uses
   and fates per obligation, product and member rows, reverse input and support lineage, cut
   selection. Emit it as a guard wrapper plus body through the existing emitters, and read it in
   Python as a table-valued selectable whose columns come from the same select.
2. Name the fragments these projections repeat (visibility under a read boundary, latest use per
   obligation, admitted product or member) as Core selectables that they compose.
3. Keep acquisition separate from projection. Taking trust-epoch shares and inserting the
   `data_demand_read` boundary is an effect and stays a native operation that returns pins. Rows
   read under those pins are the projection.
4. In new effect functions, emit each `INSERT` from the `Table` (compiled column list and target)
   and embed it in the hand-written procedure, as `pin_guard_sql`
   (`companion_projection_native.py:25–60`) embeds a compiled query today. Attach, claim, publish
   and revoke otherwise stay hand-written PL/pgSQL.

**Mechanism.** `select`, CTE, `lateral`, table-valued functions, ordered aggregates and array
binds; `literal_column` to place native parameter names when the statement is built;
`compile(dialect, literal_binds=True)`; frozen custody through `NativeTransitionOp`. Compiled text
was byte-identical across three hash seeds for a CTE, a scalar subquery and
`INSERT … SELECT … RETURNING` at 2.1.6. Recursive lineage uses the already assessed
[recursive-closure](../library_leverage/libraries/sqlalchemy/README.md#sqlalchemy-recursive-closure)
type; scope and paging use
[composable-predicate-lowering](../library_leverage/libraries/sqlalchemy/README.md#sqlalchemy-composable-predicate-lowering)
and [array-membership-binding](../library_leverage/libraries/sqlalchemy/README.md#sqlalchemy-array-membership-binding).

**Benefit.** One definition gives the native body, the Python statement and the row shape. Table
and column references are resolved against `MetaData` when the projection is built. DDO-10's
consumers receive typed rows with the pins they need, instead of each decoding a page laid out for
the planner. The route is already adopted, so no mechanism is added.

**Limits of the benefit.** `MetaData` checks relational references only. Much of what these
functions decide is JSONB-path predicates over release rows (`data_operations.sql:1590–1640`), and
those stay unchecked text inside a Core expression. Every projection over protected tables must be
`SECURITY DEFINER` with a fixed `search_path`, which admission compares; PostgreSQL does not inline
such a function. A predicate composed outside it is therefore never pushed into its body, so scope,
continuation key and limit must be projection parameters, as they are for the companion
projections. The existing emitter assumes one body (`companion_projection_native.py:65–88`) and the
closed `ProjectionRecipe` AST has no lateral or aggregate node; direct Core selects with declared
parameters avoid extending the AST, and the emitter needs a small extension for a second result
branch. SQLAlchemy makes no promise about compiled text across releases, and a patch release has
already changed bind naming, so a body regenerated in a later successor can differ in bytes with no
semantic change. SQLAlchemy is already a deployment determinant (`semantic/determinants.py:35`).

**Preserved.** Native authority and frozen custody; `plpgsql_check` and catalog admission; empty
table read roles with `EXECUTE` on the modeled projection only; no SQL text in declarations (the
Core expression is application source); releases as rows.

**Conditional parts.** Convert `ops.data_binding_rows` when it is next revised: it has two result
branches and record variables, and DDO-06–08 are changing it now. Convert the read half of
`ops.read_demand_result` when DDO-10 adds the reader, MCP or export shape; that conversion includes
migrating the existing `ci demands` consumer (`semantic/data_operation_service.py:120–132`).

**Alternatives.** Retain hand SQL and only name `INSERT` columns: cheaper, and DDO-09/10 then add
more hand-built JSON readers. Views through `CreateView`: rejected here, because each read must
authorize kind universes and pin a boundary, which a function wrapper does and a view grant does
not.

**Challenge.** The JSON document is an authenticated wire contract that existing consumers
validate. A projection returning rows moves validation from one closed schema to a row type plus
pins, and a consumer that needs the whole page atomically must still get it in one call. Keep the
document form where a consumer needs exactly that; the recommendation is for new consumers whose
needs differ.

**Closure evidence.** A derivation check that the emitted body equals the frozen successor text;
independently specified expected rows for each projection on a seeded demand; one projection read
by `ci` and MCP with the same pins; wrong project, contract, trust or cursor snapshot refused.

<a id="I03"></a>
## I03 — Extend the shared binding cases to typed-comparison edges

**Recommend, small · DDO-03/05/06; DP-08, DP-23, G6.**

**Current approach.** Two lowerings is a sound structure: Core resolves candidates and decides
sufficiency, and the native interpreter verifies a selected binding at attachment. They implement
typed comparison differently. Core casts the lexical form to `BigInteger`, `Float`, `Numeric`,
`Date` or timestamp and uses ordinary operators (`semantic/data_operation_storage.py:893–911`,
`data_operation_bindings.py:730–800`). The native side compares tagged values, decodes hexadecimal
floats exactly and treats integers as `numeric`
(`semantic/sql/data_operation_bindings.sql:138–180`). Both restate the same primitive-type mapping
(`data_operation_bindings.py:627`, `sql:98`). `BINDING_EVIDENCE_CASES` already runs one case set
through both, with the mapping from a Core status to a native acceptance or refusal written per
case. The plan requires literal type, comparison semantics and unknown state to survive "both
Python and SQL lowering" (`demand-planning-and-execution.md:121`).

**Proposed change.** Add cases where the two mechanisms could plausibly diverge, each with its
expected Core status and its expected native outcome stated independently: an integer beyond the
`bigint` range, float equality at adjacent representable values, a typed null against a missing
property, and date and timestamp boundaries. Record a found divergence as a defect for its owner.

**Withdrawn.** The draft of this review proposed that Core call the native comparison functions so
comparison has one implementation. It does not hold. Those functions raise on a null, unknown or
mistyped operand, so one candidate with a missing property would abort the planner's query, where
today it simply fails to match. Runtime roles have no `EXECUTE` on them
(`semantic/data_operation_binding_native.py:47`), and sharing them would remove the independence
of the native check. Compiling each release's binding to SQL for native execution was also
rejected: native code must stay release-generic, and executing release-supplied SQL in a definer
function weakens static checking.

**Conditional.** If I02 gives the tagged `[tag, lexical]` form a second Core consumer, move the
decode at `data_operation_storage.py:888–911` into one `TypeDecorator` or comparator so both
consumers share it. One consumer does not justify it.

**Limit.** No disagreeing input was found. The cluster is provisioned with `C.UTF-8`
(`scripts/pg_provision.sh:93`), so string ordering is not a candidate.

**Closure evidence.** The added cases pass on both paths with their stated outcomes, or each
failure is recorded with its owner.

<a id="I04"></a>
## I04 — Make table and schema privileges compared migration operations

**Recommend · DDO-04 purpose permissions, DDO-10 protected assessment, DDO-11 cutover and
retirement; DP-01, DP-16, FP-05.**

**Current approach.** Functions, triggers and views carry frozen before/after owner and ACL state,
taken from the declared predecessor and checked against the catalog. Tables do not.
`prepare_series_candidate` appends `ALTER TABLE … OWNER TO`, `GRANT SELECT` and `REVOKE ALL` as
`ExecuteSQLOp` strings, bracketed by `SET LOCAL ROLE` strings, and only for tables created in that
candidate (`semantic/native_candidate.py:2250–2337`). Schema usage on `eval` is granted and revoked
from live state in every candidate (`:2338–2355`). A cross-owner foreign key is recognized by
matching one table and column name (`:2258–2291`), and the rendered Python is then repaired by an
AST rewrite for role restoration (`cli/schema.py:412–452`). The default role list is spelled in
`native_products.py:135`, `native_candidate.py:2309` and `:2322`, and twice in
`sql/admission.sql:130`. The admission guard does verify table privileges against the descriptor.
So a `ph:read_roles` change on an existing table changes what admission expects and yields no
operation: the candidate is refused at deployment rather than corrected at authoring.

**Proposed change.** Add a privileges operation to the existing plugin, modeled on
`NativeTransitionOp`, for table owner and ACL and for schema usage. Take `before` from the declared
predecessor's admission descriptor, which already records each table's owner and read roles
(`native_products.py:133–145`); do not read it from the authoring database, whose stray grants
would otherwise enter frozen custody. Keep the stale-before check against the live catalog at
upgrade. Execute under the owner bracket inside the implementation (`native_owner` exists), with a
renderer and `reverse()`. Register a per-table comparator for declared against predecessor state.
Declare the cross-owner foreign key as a property of the constraint. State the default roles once
and let admission SQL be generated from that statement.

**Mechanism.** `Operations.register_operation`, `implementation_for`, `renderers.dispatch_for`
and `Plugin.add_autogenerate_comparator(fn, "table", <element>)`, whose callback receives the
reflected and declared `Table` for each table. These are the APIs `alembic_native.py` already uses.

**Relation to ADR-0074.** That record kept the explicit operation walk because "its privilege
context and global ordering remain necessary under public Rewriter traversal". This amendment does
not convert the walk to `Rewriter` callbacks. With table and schema privileges both in operations,
the walk no longer carries privilege context; global retirement ordering
(`_order_physical_retirement`) remains an explicit pass. Adopting I04 should restate that clause.

**Benefit.** A declared role change yields an operation with recorded before and after state.
Table privileges become compared facts, as function privileges already are. The role strings, the
name match and the AST repair retire.

**Preserved.** Predecessor-declared custody; independent catalog observation at admission and at
upgrade; frozen predecessors.

**Alternative.** Alembic Utils `PGGrantTable`: no. It compares the live database with the current
declaration by simulation, has no frozen before/after payload and does not compare owners.
Retaining the current approach works while table roles never change after creation. DDO-10 and
DDO-11 are where they will.

**Challenge.** About 200 existing tables have no privileges operation in history. No baseline is
needed: their state is already in each predecessor's descriptor, so an operation is emitted only
where declared and predecessor state differ. The first candidate under the new comparator must
produce none for an unchanged model; if it produces any, the descriptor and the declarations
already disagree, and that is worth knowing before DDO-11.

**Closure evidence.** A `ph:read_roles` edit on an existing table produces exactly one privileges
operation and the deployed candidate passes admission. An unchanged model produces none. A stale
before-state is refused at upgrade.

<a id="I05"></a>
## I05 — Keep revision-specific data steps with the change that owns them

**Recommend, low priority · successors authored by DDO-06–11; FP-01/03, DP-16/17, A1.**

**Current approach.** `prepare_series_candidate` (about 260 lines in a 2,413-line module) appends
backfills when a candidate creates `ops.pdf_visual_index` or `kb.characterization_source_scope`
(`semantic/native_candidate.py:2360–2394`). Each served one revision that is now frozen. The same
function adds named columns to `ops.task` and `ops.run` inside a savepoint that is rolled back
(`:2163–2209`); those are authoring prerequisites, not revision steps. `ChangeRequest` already
carries explicit native intent (`schema/model_change.py:63–83`).

**Proposed change.** Let a change request name a data step: a reference to a Python function that
builds a Core statement such as `Insert.from_select`. The authoring route compiles it to SQL text
and appends it to that revision, since Alembic renders `ExecuteSQLOp` only from a string
(`alembic/autogenerate/render.py:1203–1209`). The request model is frozen and closed, so this is a
schema change to it. The request carries a name, never SQL text. Derive the scaffolding columns
from the difference between target and catalog columns. Delete each table-specific backfill branch
once its revision is frozen.

**Benefit.** The remaining packages will author more successors, including DDO-11's retirement of
superseded tables, and each data move would otherwise add a branch to a shared function. Alembic's
own guidance is that a data step belongs to the revision that performs it.

**Challenge.** A branch may still be needed to author a candidate from an old predecessor. Check
that against the registered chain before deleting; the frozen revisions do not call this function.

**Closure evidence.** A successor with a named data step renders it once; an unrelated successor
contains no table-specific operation; the deleted branches have no caller.

<a id="observed-defects"></a>
## Observed defects

These are defects found while reading, separate from the opportunities above. Each is
Interface-checked from source and none was exercised.

1. **The stored-fate CHECK admits a value that is never stored.** `demand_use.fate` allows
   `waiting` (`data-operation-physical.yaml:407`). `waiting` is produced only at read time by
   `coalesce(u.fate,'waiting')` (`semantic/sql/data_operations.sql:1347`) and is absent from the
   protocol's `historical_fate`. The column uses the 15-value visible set where the 14-value stored
   set is meant. I01 corrects it.
2. **A refusal branch in typed-column generation is dead.** `render_typed_column_class` rejects an
   unsupported column type by catching `NotImplementedError` from `python_type`
   (`schema/relational.py:953–957`). In SQLAlchemy 2.1 `TypeEngine.python_type` returns `object` by
   default (`sqlalchemy/sql/type_api.py:687–704`), and no override in SQLAlchemy or pgvector raises.
   An unsupported type would render as `Named[object]`. No current column was shown to reach it.
3. **`NativeTransitionOp` cannot be reported as a difference.** It defines no `to_diff_tuple`, so
   `command.check`, `compare_metadata` and `as_diffs()` raise `NotImplementedError` when a native
   operation is present (`alembic/operations/ops.py:2679–2690`). The only caller,
   `tests/semantic/test_native_closure.py:469–478`, runs where no difference exists. It matters
   only if `check` gains a consumer; give I04's operation the method if that happens.

## Adoption order, interactions and authority

I02 comes first by consequence, and it does not collide with current execution: its recommended
part concerns readers DDO-09 and DDO-10 have not written, and its successors are authored by those
packages. I04 should land before DDO-10 or DDO-11 changes a table's roles. I01's fate derivation
and I03's added cases are small and independent. I05 waits for the next data move.

I01 and I04 each need a native successor, and the chain has a single head that DDO-06–08 are
extending now. They must be serialized into that chain by its current owner; neither should be
authored as a competing successor. I04 adds an operation kind, so the frozen payload version
advances. Neither touches a frozen predecessor.

I01's identifier typing and I03's codec depend on I02. Nothing else has a prerequisite.

Taken together the amendments do not change the undertaking. The kernel stays PostgreSQL, the model
and protocol stay authoritative, and no mechanism is added: each item extends a route that exists.

## Capability coverage

Every section of both references has a disposition. "Delegated" means the repository already uses
the capability for this responsibility.

### SQLAlchemy

| Reference section | Capability | Disposition |
|---|---|---|
| §2.1–2.2, add. §1.6–1.8 | Core composition, CTE, lateral, `values()`, table-valued functions, ordered aggregates, expanding and array binds | Delegated in the binding lowering; extended to DDO projections by [I02](#I02) |
| §2.3, add. §7.3 | Expression typing, `type_coerce`, operator classes | Delegated. Operator classes need no action |
| §2.4 | `@compiles`, `SyntaxExtension`, expression visitors | The visitors module is documented as internal and not fully public, and it cannot see inside `text()`. The existing `native_statement` uses it; new projections should place native names with `literal_column` when built. Do not build read-set or lineage derivation on it. No current fit for `SyntaxExtension` |
| §2.5 | Compiled cache, cache keys, `lambda_stmt` | No current fit. Cache keys include object identity and are in-process only, so they cannot be a persisted fingerprint; reuse identity must stay semantic (RC01) |
| §2.6 | `text()`, `tstring()` | No fit; DDO Python code has one `text()` call |
| §3.1–3.2 | `MetaData`, constraints, naming conventions | Delegated |
| §3.3, add. §2.3 | Reflection, `Inspector.get_multi_*`, `column_reflect` | Delegated for database description. The private `_InspectorConv` use in `alembic_indexes.py` has no public replacement in 1.20.1; keep the adapter |
| §3.4 | `schema_translate_map` | No current fit; test deployments are separate databases |
| §3.5 | `CreateView`, `CreateTableAs` | Conditional: a projection that needs no per-read authorization. Alembic 1.20.1 has no view handling, so such a table needs an `include_object` filter on `Table.is_view`. `CreateTableAs` has no fit: tables are fixed |
| §4.1–4.2 | Dialect types, `TypeDecorator` | Delegated (`ContextJSONB`). A codec for tagged values is conditional under [I03](#I03) |
| §4.3 | ORM annotation inference | No current fit (see the ORM row) |
| §4.4 | `TypedColumns`, `Named`, `with_cols` | Delegated for seven relations; DDO use conditional under [I01](#I01) |
| §5–§7, add. §3–§5 | ORM mapping, relationships, inheritance, hybrids, composites, loaders, bulk DML, sessions | No current fit. Runtime roles cannot select DDO tables, every write is a native call and most rows are immutable, so there is no unit of work to coordinate. The model and protocol are the authorities; mapped classes would be a third. Revisit only if a persisted object graph appears that Python both reads and writes directly |
| §6.6, add. §1.5 | Version counters, `with_for_update` | No fit in Python by design: all locking is inside native operations |
| §8.1–8.4, add. §6.1–6.2 | Engine, transactions, isolation, pooling, engine plugins | Delegated (`core/db/store.py`). DDO pins reads with a native read boundary rather than `REPEATABLE READ`; keep that |
| §8.5, §11.4 | Streaming, `yield_per` | Applies to DDO-10 export under [I02](#I02); already an assessed type |
| §8.6 | asyncio | No current fit |
| §9, add. §8 | PostgreSQL dialect: `ON CONFLICT`, JSONB, partial and covering indexes, `ExcludeConstraint`, DOMAIN, ENUM, computed columns | `ON CONFLICT` lives in native operations. Partial and expression indexes, `Computed` and `Identity` are delegated through `ph:` annotations. `ph:indexes` cannot declare a unique partial index (`schema/relational.py:747–769`); conditional on the first "at most one live row per key" invariant that is not a plain unique key. `ExcludeConstraint`: no interval invariant in the footprint, and it is neither reflected nor compared. DOMAIN: conditional on a scalar rule repeated across many tables. Native ENUM: no; `Text` with a digest-named CHECK changes inside one transaction and is already compared |
| §10.1–10.2, add. §6.3–6.4 | Events, `handle_error` | No current fit. A commit failure reaches `handle_error` with the same empty context as begin and rollback failures, so the hook cannot by itself identify an uncertain commit; the intent and receipt protocol and `store.py`'s phase classification already do |
| §10.3 | Runtime inspection | No fit without mapping |
| §10.4, add. §4 | Sharding, `do_orm_execute`, frozen results | No current fit |
| §11.1, add. §1.1–1.4 | `insertmanyvalues`, sentinels, `Insert.from_select`, `RETURNING` | Bulk transfer is typed COPY staging (ADR-0098). `Insert.from_select` is the form for [I05](#I05) data steps and [I02](#I02) effect inserts |
| add. §2.1–2.2 | Conditional DDL, `sort_tables`, `Table.to_metadata` | `sort_tables` delegated. `to_metadata` drops index `info`; no use identified |
| add. §2.4 | `create_mock_engine` | Not needed; offline `compile(dialect=…)` is in use |
| add. §2.5 | Defaults, `FetchedValue`, `Computed` | Delegated. `data_population.selected_obligation_id` duplicates a JSON path under an equality CHECK (`data-operation-physical.yaml:446`); `ph:computed` would derive it. Optional |
| add. §5 | External transactions, scoped sessions | Delegated: the caller owns the connection |
| add. §7.1–7.2 | SQL NULL versus JSON null, typed JSON accessors | Delegated (`JSON.NULL`, `json_context_value`) |
| add. §9 | 2.1.6 corrections | No action |

### Alembic

| Reference section | Capability | Disposition |
|---|---|---|
| §2, §12 | Revision DAG, branch labels, `depends_on`, multiple bases | Conditional. A new labelled base can be added without editing frozen files, but native objects are checked against an exact predecessor state, so independent lineages touching one kernel would break that check, and `current(check_heads=True)` reports a false "not at head" once `depends_on` is used (observed on SQLite). Trigger: a component with disjoint native objects that must deploy independently |
| §3, add. §2 | Operations, `postgresql_using`, `NOT VALID`, concurrent indexes, `autocommit_block` | Ordinary operations delegated. Deferred validation and concurrent builds: no current fit; adoption is one atomic upgrade of a regenerable database, and `autocommit_block` raises when the caller owns the transaction |
| §4, add. §1 | Autogenerate, filters, type and default comparison | Delegated, with the two narrow adapters retained |
| §5.1–5.3 | `produce_migrations`, `process_revision_directives`, `Rewriter` | `produce_migrations` delegated. It never invokes the directive hook; a `Rewriter` can be called on its result and can target custom operations. ADR-0074 declined callback conversion; [I04](#I04) removes the privilege strings instead |
| §5.4–5.6 | Custom operations, comparators, plugins | Delegated; extended by [I04](#I04) |
| §5.7, add. §3.4 | Post-write hooks, `script.py.mako`, `generate_revision`, `template_args` | No current fit. `generate_revision` imports every revision module, which the custody design avoids, and the wrapper's exact bytes are themselves checked |
| §6 | Batch migrations | No fit (SQLite) |
| §7.1–7.3, add. §5.3 | Online execution, offline SQL, transaction controls | Online delegated. Offline refusal retained: native operations need a live catalog. `transaction_per_migration` has no effect on a caller-owned transaction |
| §7.5, add. §5.4 | `on_version_apply` | Delegated |
| §8.1–8.4, add. §3.1 | `Config`, `command`, `MigrationContext`, `ScriptDirectory`, `RevisionMap` | Delegated. The AST-built `RevisionMap` uses a documented constructor |
| §8.5 | `command.check`, `current(check_heads)` | Covered more strongly by the admission descriptor and guard. See [observed defect 3](#observed-defects) |
| §8.6 | `stamp` | Excluded by the plan (`preservation-adoption-and-qualification.md:47–49`) |
| §8.7 | Custom CLI commands | No fit; `ci` owns the commands |
| §9 | Multiple databases, schemas, tenants, asyncio | No current fit |
| §10 | Reflection cost, concurrency, downgrade limits | Delegated: advisory fence, refused downgrade |
| §11.2–11.3, add. §6 | Alembic Utils, alembic-postgresql-enum, pytest-alembic | No current fit, on the DDO premises as before. Alembic Utils has no frozen before/after state or owner comparison. No native enums exist. pytest-alembic's up/down test fails on a refused downgrade, and its setup expects an engine outside a caller-owned transaction |
| add. §3.2–3.3 | Runtime arguments, `-x` | No fit; the same revision must mean the same change |
| add. §4.1 | `render_python_code` | Delegated. It discards renderer imports, which the existing post-processing supplies |
| add. §4.2–4.4 | `DefaultImpl` hooks, version-table implementation | No current fit; overriding the built-in PostgreSQL implementation is process-global |
| add. §5.1–5.2 | `op.execute`, `bulk_insert` | Delegated where used |
| add. §7–§8 | SQLAlchemy 2.1 integration, 1.20.1 corrections | No action |

One further use was considered and left conditional. `ci model change preview` reports a physical
change as a pair of source-closure identifiers (`schema/model_change.py:383`); the structured
difference appears only at the candidate stage. If operators need it earlier, the candidate
stage's rollback-only `produce_migrations` result is the mechanism to surface.

## Rule impacts and package integration

No recommendation changes a binding decision. Two touch recorded reasoning and should go through
the existing decision owners if adopted:

- I02 applies ADR-0047's Core-authoring target to DDO reads. D3's "Unified operation realization"
  should say which DDO functions are projection-emitted and which are retained procedural kernels.
- I04 changes the premise of ADR-0074's retained-walk clause and extends the frozen operation
  payload. Record it with the plugin's owner in D3.

I01 as recommended keeps the protocol's authority and needs no rule change. Its alternative, making
the physical model the owner, would.

| Recommendation | Packages and companions | Related findings |
|---|---|---|
| I01 | DDO-04 physical model; DDO-05/06 consumers. [Products and support](../plans/declared-data-operations/products-and-support.md) | F13 |
| I02 | DDO-09 change and currentness reads; DDO-10 read projection; DDO-03/05 binding rows when revised. [Interfaces and evaluation](../plans/declared-data-operations/interfaces-and-evaluation.md), [change, reuse and consolidation](../plans/declared-data-operations/change-reuse-and-consolidation.md) | F07, F09 |
| I03 | DDO-03 lowering; DDO-05 planner; DDO-06 attachment. [Demand planning and execution](../plans/declared-data-operations/demand-planning-and-execution.md) | F02, F10 |
| I04 | DDO-04 purpose permissions; DDO-10 protected assessment; DDO-11 cutover. [Preservation, adoption and qualification](../plans/declared-data-operations/preservation-adoption-and-qualification.md) | — |
| I05 | Native successors authored by DDO-06–11 | — |

Related findings show where a recommendation contributes; disposition stays in the coordinator's
tables.

## Evidence account and limits

**Interface-checked, 2026-11-14, libraries.** Installed SQLAlchemy 2.1.6 and Alembic 1.20.1
source, tagged documentation and offline compilation established: visitor traversal is internal;
cache keys are in-process; compiled text is deterministic across hash seeds with no cross-release
promise; `with_cols` is static only and `NewType` propagates to typed results; `python_type`
defaults to `object`; `handle_error` cannot distinguish a commit failure by context; `CreateView`
tables carry `is_view` and Alembic ignores views; `produce_migrations` does not run directive
hooks; `generate_revision` imports all revisions; custom operations need `to_diff_tuple` for
`check`; `ExecuteSQLOp` renders only strings; a caller-owned transaction disables Alembic's
transaction controls; branch-label and `depends_on` behavior. Alembic transaction and graph
observations used in-memory SQLite, not PostgreSQL. That PostgreSQL does not inline a
`SECURITY DEFINER` function with a `SET` clause is established PostgreSQL behavior and was not
re-checked. Companion-package facts were read from upstream at their default branch.

**Interface-checked, 2026-11-14, repository at a15f2e197.** Every code location cited above, read
by the root or by a contribution and, for quoted lines, re-read by the root.

**Changed by the adversarial review.** The withdrawal in I03; the protocol as owner in I01 and the
`waiting` defect; predecessor-sourced before-state and schema privileges in I04; the corrected
inlining and consumer statements in I02; the data-step representation in I05.

**Not established.** No test or probe was run against the product, and no database was used. The
two binding lowerings were not shown to disagree on any input. The `python_type` fallback was not
shown to be reached by a current column. Whether each backfill branch in I05 is unreachable was not
traced. `orchestrate/data_operations.py` and `semantic/data_operation_ports.py` were searched, not
read in full. The operations-cutover, implementation-contracts, graph and source-evolution
companions were read for scope, not line by line; they contain no relational mechanism this review
amends.

**Outside the lens, noted.** Each native successor stores a complete desired-state snapshot
(about 9.8 MB for `semantic_ddo_context_v1`, beside a 3.0 MB upgrade text), and the revision
directory holds 932 files. That growth follows from the custody design, not from either library,
and was not assessed. Generating the effectful procedures themselves from the model would be a
separate undertaking: no library writes PL/pgSQL, and I02 does not need it.

**Checks.** `uv run ci docs check`: outcome recorded in the publishing commit. Product tests,
native controls and providers: `not_run`; this review defines closure evidence and qualifies
nothing.

**Next decision.** Whether to revise the DDO plans from I01–I05. Until then the recommendations
remain proposals here, and the DDO plans are unchanged.
