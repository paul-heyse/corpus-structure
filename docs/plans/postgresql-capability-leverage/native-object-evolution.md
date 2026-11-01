# Native object authoring, evolution and syntax

**Proposed target, 2026-11-01.** [Coordinator](../postgresql-capability-leverage_2026-11-01.md) owns PG-01/08/09 and PG-I01. This document addresses O06/O07/O08/O10/O12 and the operator's explicit exclusion of Alembic Utils.

## Selected mechanism and operator correction

**Do not add Alembic Utils.** The operator excluded that separate package and authorized recreating particular valuable features when their value is compelling. The review's companion-library comparison is superseded by this instruction for this series; the source review is preserved as evidence, not silently rewritten.

Select existing SQLAlchemy Core metadata/DDL plus Alembic's supported native extension interfaces: `produce_migrations`, `MigrationScript`/`UpgradeOps`, public `Plugin` comparators, `MigrateOperation` registration/implementation/rendering, `Rewriter` and revision directive hooks. Use pglast for residual syntactic analysis. These are Alembic capabilities, not a claim that core Alembic already discovers every PostgreSQL function/view/trigger/grant.

Recreate only lifecycle responsibilities with demonstrated consumers: an owned native-object inventory, desired-versus-observed comparison sufficient for an actual forward change, and structured create/replace/drop candidate operations with declared prerequisites. Do not build a universal PostgreSQL reconciler, dependency solver, registration framework or reverse-history store. No second object-management dependency is selected by default. Revisit a companion only under a new concrete requirement and operator instruction; Alembic Utils remains excluded.

## Value and responsibility test

Current native generators spread object inventories, ordinary replacement sequencing and descriptor construction across `native_products`, `source_view_native`, record/staging products and admission. The compelling opportunity is one authoritative desired object definition feeding forward authoring and independently checked admission, rather than maintaining the same signature/owner/configuration in unrelated builders.

The application still authors domain SQL bodies and protected policy. Distinguish exact archived source bytes, canonical comparison forms and actual deployed object properties. A pglast AST equality or server-normalized definition is not domain equivalence. Keep object identities—including input-bearing overload signature versus OUT/TABLE arguments—explicit. Do not infer grants, owner or search_path from a body match.

For each proposed custom helper, PG-01 records the real repeated operation it replaces, the native API already used, its residual contract and consumer. A helper that merely wraps `op.execute` has not recreated a useful lifecycle. Dependency order comes from existing model/product prerequisites plus actual candidate application, not a new best-effort solver presented as proof.

| Narrow feature worth recreating | Concrete value and existing native API |
|---|---|
| Owned native-object inventory/comparison | One model-owned signature/configuration reaches authoring and admission; Alembic schema Plugin comparator adds only actual changes to UpgradeOps |
| Inspectable replace/drop operations | Supported MigrateOperation implementation/rendering makes a repeated current forward change reviewable; include reverse information only when that operation actually supports reversal |
| Source-qualified native diagnostics | Shared pglast syntax facts avoid reparsing the same current product; server catalog checks retain authoritative body/configuration/privilege meaning |

The library supplies extension dispatch, revision history and ordinary DDL execution. Application code supplies only the above residual PostgreSQL/domain behavior whose consumer demonstrates value. [Native Plugin API](https://alembic.sqlalchemy.org/en/latest/api/plugins.html) and [autogeneration APIs](https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html) were consulted through Context7 during authoring; schema comparators mutate UpgradeOps and normally continue dispatch, not suppress unrelated comparators by default.

## PG-01 / PG-I01 — Representative native extension integration

Use one current protected function family with overload/OUT arguments, a dependent view, trigger/policy and role/grant boundary. Inspect current forward authoring and core extension hooks first; use a disposable owned authoring database only when needed to settle server semantics. Existing migration credentials remain absent from normal runtime connections.

The result selects the minimum native plugin/operation surface for PG-08. Demonstrate desired declarations producing inspectable operations, no-change comparison empty, changed body/configuration replaced, unowned objects preserved, actual required privileges/configuration independently checked, and caller rollback preserving both object state and revision movement. Intentionally wrong owner/search_path/grant must fail admission. A failed case identifies an exact missing property, not permission to rebuild an entire legacy framework.

Do not copy committing helpers from companion recipes. The existing migration wrapper owns an externally supplied connection/transaction. Simulated DDL must be isolated and rolled back without durable effects; if no simulation is needed, omit it. Do not adopt any external dependency ordering as a proof of closure. This first technical package constrains PG-08, not outcomes, transfer or consumer delivery.

## PG-08 — Library-native candidate operations and own transitions

Derive owned object specifications from current model/native authoring. Use core metadata for ordinary tables/columns/indexes/constraints and explicit native operations for the selected non-table families. Comparators read only the declared object scope. Preserve all unowned objects; unknown/unsupported properties refuse rather than silently normalizing them away. Candidate generation is inspectable; revision-head state and empty autogeneration do not replace actual descriptor/enforcement comparison.

Render candidate operations through Alembic and execute through existing history/caller transaction. Use standard Core/Alembic DDL where its semantics fit. Any residual SQL uses correct identifier composition and explicit contract. Migrate current forward authors and admission consumers alongside the shared specification, then retire their replaced mechanical definitions. Frozen old products and unrelated generators are not cleanup targets; if the better target intentionally breaks compatibility, state and schedule the specific new contract/transition rather than falsify history.

Only this series' new realization/data changes are scheduled. Server-resident source favors set transformation, Arrow replay uses the directional transport, and retained envelope JSON may reuse its existing streaming parser if the selected change needs it. No package completes former PDF migration/adoption. `postgresql_using`, NOT VALID/VALIDATE and concurrent indexes are available choices for concrete DDL, not a shopping list: concurrent indexes need explicit autocommit/restart handling and can remain invalid. Prefer transactional/rebuild work absent a need for continued writers.

## PG-09 — Residual prepared syntax facts

After native extension boundaries settle, identify current consumers of the same immutable SQL: forward inventory, admission, authored-SQL diagnostics and operator inspection. Prepare only useful shared facts with original source/statement coordinates. Use pglast high-level Visitor/actions, `split(only_slices=True)`, scanner/displacement APIs and fresh native printers; original excerpts and regenerated output are separate products. Mutation invalidates old ancestry; raw procedural dictionaries are not typed SQL visitors.

Do not refactor version-specific0050/0052/0053 generators solely because loops look similar. Preserve nested CTE scope, forbidden descendant detection, Unicode locations, function signature meaning and dependency distinctions. Fingerprints may group diagnostic query shapes but never replace semantic/source identity or prove execution safety. Independent expected transformations/catalog facts challenge the result; parse-print-reparse agreement alone cannot establish correctness.

## Basis and architecture

[Alembic original §§4–8/11 and addendum §§1–7](../../libraries/postgresql/alembic.md), [SQLAlchemy schema/type/DDL sections](../../libraries/postgresql/sqlalchemy.md), [pglast parsing/transformation/source sections](../../libraries/postgresql/pglast.md). The original Alembic Utils lead was considered then excluded by operator direction; its generic capabilities are not assumed to be native Alembic features. FP-01/04/06, DP-06/13–16/24 and H4/H12/H27 favor small valuable extensions on an established lifecycle over a bespoke framework. Current source must establish each residual need.
