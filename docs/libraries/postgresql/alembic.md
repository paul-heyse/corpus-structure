# Alembic 1.20.0 — Comprehensive Python Library Capability Overview

Research date: October 20, 2026 | Target: Alembic 1.20.0 (latest stable release)

Alembic is a database schema migration framework built on SQLAlchemy. Its central purpose is to coordinate the evolution of relational database structures through versioned, executable migrations while preserving an explicit history of schema changes.

The library is substantially more capable than a utility for generating SQL `ALTER TABLE` statements. It combines a revision dependency graph, a database-aware migration execution engine, declarative schema comparison, programmable DDL operations, extensible migration generation, and orchestration APIs.

Alembic 1.20.0 was released on September 11, 2026. It requires Python 3.10 or later and SQLAlchemy 2.0 or later. Its latest major architectural improvements include an extensible autogeneration plugin framework, improved schema reflection efficiency, enhanced constraint handling, and additional DDL controls. The documentation also contains an unreleased 1.20.1 changelog entry; those changes are excluded from the released capability baseline.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2



Official resources:

- Documentation: [https://alembic.sqlalchemy.org/en/latest/](https://alembic.sqlalchemy.org/en/latest/?utm_source=chatgpt.com)
- Source repository: [https://github.com/sqlalchemy/alembic](https://github.com/sqlalchemy/alembic?utm_source=chatgpt.com)
- Release history: [https://alembic.sqlalchemy.org/en/latest/changelog.html](https://alembic.sqlalchemy.org/en/latest/changelog.html?utm_source=chatgpt.com)
- Package distribution: [https://pypi.org/project/alembic/](https://pypi.org/project/alembic/?utm_source=chatgpt.com)

## 1. Conceptual model and capability map

Alembic sits between the desired database structure, the database's actual structure, and an ordered history of changes.

SQLAlchemy schema model

MetaData, Table, Column, constraints, indexes, SQL types

Autogeneration compares desired and reflected schema

Alembic migration system

Revision graph · Operation directives · Execution context · Dialect handling

Online execution

Apply migrations through SQLAlchemy connections

Offline generation

Compile migrations into SQL scripts

Conceptual architecture. Autogeneration is optional; migrations can be authored entirely by hand.

The key abstraction is that a migration revision is an executable transformation, not merely a snapshot of the schema.

A revision typically defines `upgrade()` and `downgrade()` functions. It carries a unique revision identifier and references earlier revisions through `down_revision`. Alembic uses this information to construct a dependency graph and determine the changes needed to move a database between revision states.

The primary capability families are:

| Capability                 | Native mechanisms                                                                      |
| -------------------------- | -------------------------------------------------------------------------------------- |
| Schema evolution           | `op.create_table`, `op.add_column`, `op.alter_column`, constraint and index operations |
| Migration versioning       | Revision DAG, branches, merge points, dependencies, multiple bases                     |
| Automated change detection | SQLAlchemy metadata comparison, reflection, custom comparators                         |
| Migration execution        | Online connections, transactions, offline SQL generation                               |
| Database portability       | SQLAlchemy dialects, DDL implementations, SQLite batch mode                            |
| Programmatic orchestration | `Config`, `ScriptDirectory`, `MigrationContext`, `alembic.command`                     |
| Customization              | Operation plugins, autogeneration plugins, renderers, rewriters                        |
| Validation                 | `check`, `current --check-heads`, migration state inspection                           |
| Deployment integration     | SQL script generation, connection sharing, async environments, custom CLI commands     |

Alembic deliberately separates several responsibilities:

- SQLAlchemy supplies relational metadata, SQL expression construction, schema reflection, database dialects, and connection management.
- Alembic supplies migration history, change detection, migration-oriented DDL operations, execution coordination, and extensibility.
- The database engine determines which DDL statements are legal, which changes can be transactional, and what locking or physical data movement occurs.
- Application and deployment code remains responsible for deciding whether a schema transition is safe for existing data, concurrent traffic, and different application versions.

This separation makes Alembic useful well beyond ORM-centric applications: its schema operations and migration execution facilities can be used with SQLAlchemy Core or direct SQL without requiring ORM mappings.

Source: [https://alembic.sqlalchemy.org/en/latest/api/overview.html](https://alembic.sqlalchemy.org/en/latest/api/overview.html?utm_source=chatgpt.com)

## 2. Revision graph, dependency management, and schema history

### 2.1 Migration history is a directed acyclic graph

Alembic does not require migrations to form a single linear chain. Instead, revisions form a directed acyclic graph (DAG), with parent-child relationships describing which changes must have occurred before another revision can execute.

Each revision can contain:

| Revision attribute | Meaning                                                    |
| ------------------ | ---------------------------------------------------------- |
| `revision`         | Unique identifier for this migration                       |
| `down_revision`    | Parent revision, tuple of parents, or `None` for a root    |
| `branch_labels`    | Symbolic identifiers for migration branches                |
| `depends_on`       | Additional dependencies without merging revision lineages  |
| `upgrade()`        | Transformation applied when advancing through the revision |
| `downgrade()`      | Reverse transformation, if implemented                     |

The distinction between `down_revision` and `depends_on` is important. Both influence execution ordering, but they express different relationships.

`down_revision` establishes ancestry in a revision lineage. `depends_on` establishes an ordering dependency while allowing separately managed lineages to remain distinct.

### 2.2 Branches and merge revisions

Consider two independent revisions created from a common parent:

```
                         ┌── B ── D ──┐
base ── A ────────────────┤           ├── F
                         └── C ── E ──┘
```

Alembic can recognize both `D` and `E` as heads and can generate a merge revision `F`, whose `down_revision` references both heads.

This has several implications:

- Databases already at `D` can advance through the missing branch and merge.
- Databases already at `E` can advance through the other branch and merge.
- Databases with neither branch can apply both in a valid dependency order.
- A merge revision can contain reconciliation operations, although an empty merge is sufficient when the branches are compatible.

Alembic does not make semantically conflicting DDL automatically compatible. A merge declares the graph relationship; any necessary reconciliation remains part of migration authorship.

### 2.3 Multiple heads and database version tracking

The `alembic_version` table is not necessarily a single-row version register.

When multiple heads are active, Alembic can maintain multiple rows representing the current migration frontier. Advancing through branches and merge points updates this frontier accordingly.

Consequently, `alembic current`, `alembic heads`, and `alembic history` answer different questions:

- `current`: Which revision heads are represented by the database?
- `heads`: Which terminal revisions exist in the migration scripts?
- `history`: What revisions and dependencies exist in the script graph?

A database's version state and the repository's available migration heads are distinct concepts.

### 2.4 Explicit branch management

Alembic supports named branches, symbolic revision references, and targeted movement through those branches.

Examples include:

```
alembic heads
alembic branches --verbose
alembic history --verbose

alembic upgrade heads
alembic upgrade accounting@head

alembic revision --head accounting@head -m "Add invoice fields"
alembic merge heads -m "Merge concurrent schema changes"
```

A revision can also be created from an ancestor that is not currently a head using `--splice`, producing a new branch.

Alembic 1.18.5 extended `--splice` support to the `merge` command, which previously accepted it for revision creation but not for merges.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



### 2.5 Multiple bases and cross-lineage dependencies

An especially useful advanced capability is the support for multiple independent root revisions within one migration environment.

These can reside in separate version directories and share a common `alembic_version` table.

A revision in one lineage can declare a `depends_on` relationship with a revision in another lineage. Alembic incorporates that dependency into upgrade ordering without requiring the lineages to become one merged ancestry.

This provides a native basis for managing schema histories across logically separate components that nevertheless share database objects or require particular cross-component ordering.

The distinction from running entirely separate Alembic environments is consequential:

| Model                            | Appropriate characteristic                                               |
| -------------------------------- | ------------------------------------------------------------------------ |
| Single linear lineage            | One ordered history                                                      |
| Multiple branches with merges    | Concurrent evolution that eventually converges                           |
| Multiple bases with dependencies | Distinct lineages with shared version tracking and cross-dependencies    |
| Separate Alembic environments    | Independent configurations and potentially independent version tables    |
| Multi-engine environment         | One environment coordinating migrations for several database connections |

These models solve different lifecycle problems. Multiple bases are not equivalent to multiple databases, and multiple migration directories do not automatically imply independent histories.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+2



- Working with branches: [https://alembic.sqlalchemy.org/en/latest/branches.html](https://alembic.sqlalchemy.org/en/latest/branches.html?utm_source=chatgpt.com)
- Script directory API: [https://alembic.sqlalchemy.org/en/latest/api/script.html](https://alembic.sqlalchemy.org/en/latest/api/script.html?utm_source=chatgpt.com)

## 3. Migration operations and the DDL abstraction

Alembic's `Operations` system provides a high-level interface for database transformations, exposed in migration files through `alembic.op`.

One distinctive feature is that most operations can be expressed without reconstructing an entire SQLAlchemy `Table` model. Alembic builds the minimal necessary schema constructs internally.

### 3.1 Native schema operations

The main operation families include:

| Functional area                  | Representative APIs                                                 |
| -------------------------------- | ------------------------------------------------------------------- |
| Table lifecycle                  | `create_table`, `drop_table`, `rename_table`                        |
| Column lifecycle                 | `add_column`, `drop_column`, `alter_column`                         |
| Primary and unique constraints   | `create_primary_key`, `create_unique_constraint`, `drop_constraint` |
| Referential integrity            | `create_foreign_key`, `drop_constraint`                             |
| CHECK constraints                | `create_check_constraint`, `drop_constraint`                        |
| Index management                 | `create_index`, `drop_index`                                        |
| PostgreSQL exclusion constraints | `create_exclude_constraint`                                         |
| Schema comments                  | `create_table_comment`, `drop_table_comment`, `alter_column`        |
| Data manipulation                | `execute`, `bulk_insert`, `get_bind`                                |
| Table recreation                 | `batch_alter_table`                                                 |
| Dialect-specific execution       | `get_context`, `run_async`, execution options                       |

Several commands accept SQLAlchemy expressions or dialect-specific keyword arguments, permitting database-native capabilities to be expressed through the same migration interface.

For example, `create_index()` can accept SQL expressions rather than only column names, and dialect-specific options can control the resulting index definition.

The portability boundary is important: the interface is common, but support for individual DDL features remains database-dependent.

### 3.2 Column alteration and backend-specific requirements

`op.alter_column()` can change column names, types, nullability, server defaults, and comments.

The operation is designed to describe the intended change rather than requiring a manually assembled full SQL statement.

However, backend requirements differ. MySQL often requires existing column properties to be supplied because its alteration syntax expects a complete column specification.

The parameters `existing_type`, `existing_nullable`, `existing_server_default`, and `existing_comment` allow migration authors to preserve properties not being changed.

For SQLAlchemy schema types such as `Boolean` or `Enum`, `existing_type` can also be important for identifying associated constraints that need removal.

A representative migration is:

```
from alembic import opimport sqlalchemy as sadef upgrade():    op.alter_column(        "measurements",        "value",        type_=sa.Numeric(18, 8),        existing_type=sa.Numeric(12, 4),        existing_nullable=False,    )
```

This expresses the desired DDL, but the database may still need to validate, rewrite, or lock the affected table. Alembic does not guarantee that a type conversion preserves every existing value or executes without blocking.

### 3.3 Fine-grained DDL controls

Modern Alembic releases include several useful controls for expressing DDL more precisely.

Conditional DDL: Supported operations expose `if_exists` and `if_not_exists` parameters. These generate corresponding SQL clauses on compatible dialects, reducing the need for manual SQL or existence checks.

Inline foreign keys: Since 1.18.2, `op.add_column(..., inline_references=True)` can include a `REFERENCES` clause within the `ADD COLUMN` statement rather than issuing a separate constraint-creation statement. The documentation identifies PostgreSQL, Oracle, MySQL 5.7+, and MariaDB 10.5+ as supporting this syntax. For eligible nullable foreign-key additions, it can avoid a separate full-table constraint validation.

Inline primary keys: `inline_primary_key=True`, introduced in 1.18.4, enables explicit inline primary-key rendering when the SQLAlchemy `Column` also declares `primary_key=True`.

Extensible built-in behavior: Since 1.17.2, `Operations.implementation_for(..., replace=True)` allows an existing operation implementation to be replaced, supporting controlled customization of operations supplied by Alembic itself.

These features make it possible to express more database-native migration behavior without duplicating all the logic for constructing the underlying SQLAlchemy DDL.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+2



### 3.4 Data operations alongside schema changes

Alembic supports data transformations in migration scripts through SQLAlchemy Core and its own execution helpers.

Important APIs include:

- `op.execute()` — execute or emit a SQLAlchemy executable or SQL text.
- `op.get_bind()` — access the current connection for richer online operations.
- `op.bulk_insert()` — insert a collection of rows, including SQL-script-compatible forms.
- `op.inline_literal()` — render values as SQL literals where offline execution requires it.

`op.create_table()` also returns a SQLAlchemy `Table` object, making it possible to immediately perform data operations against a newly created table without separately defining it.

For more substantial changes, SQLAlchemy Core expressions can implement set-oriented `UPDATE`, `INSERT ... SELECT`, and other transformations.

A particularly important design principle is to define any table constructs needed by historical data migrations within the migration itself, rather than depending on application models that might change later.

Alembic provides the execution interface, but the behavior and scalability of data transformations depend on the SQL and database engine involved.

Source: [https://alembic.sqlalchemy.org/en/latest/ops.html](https://alembic.sqlalchemy.org/en/latest/ops.html?utm_source=chatgpt.com)

## 4. Schema autogeneration and metadata comparison

Alembic's autogeneration subsystem compares a SQLAlchemy `MetaData` representation of the desired schema with the live database schema obtained through SQLAlchemy reflection.

The result is a candidate migration: an initial proposal for changing the database, not a guaranteed correct or complete transformation.

This distinction is fundamental. Alembic can identify many structural differences, but it cannot reliably infer application intent from a before-and-after schema comparison.

### 4.1 What autogeneration actually detects

| Schema difference                    | Alembic 1.20.0 behavior                      |
| ------------------------------------ | -------------------------------------------- |
| Added or removed tables              | Detected                                     |
| Added or removed columns             | Detected                                     |
| Column nullability changes           | Detected                                     |
| Basic index changes                  | Detected                                     |
| Explicitly named unique constraints  | Basic detection supported                    |
| Foreign-key changes                  | Basic detection supported                    |
| Column type changes                  | Enabled by default                           |
| Server-default changes               | Optional; disabled by default                |
| Named CHECK additions/removals       | Opt-in plugin, with significant restrictions |
| Table and column renames             | Not inferred; generally appear as add/drop   |
| Unnamed constraints                  | Limited or unreliable comparison             |
| CHECK expression changes             | Not detected by the named-CHECK plugin       |
| Views, stored procedures, triggers   | Require extensions or custom implementation  |
| General-purpose data migration logic | Not inferred                                 |

Type comparison is enabled by default, as of Alembic 1.12.0. The comparator considers dialect equivalences and relevant type arguments, but can intentionally decline to report differences where the database does not reflect sufficient information.

Server-default comparison must be enabled with `compare_server_default=True` or a custom comparator. For PostgreSQL, default equivalence checking may involve evaluating expressions against the database rather than relying solely on textual comparison.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



A schema comparison also cannot tell whether a dropped column was intentionally removed, renamed, consolidated into another column, or replaced by a different representation.

For example, these two changes are not semantically equivalent:

```
# What a naive structural diff might generateop.add_column("customers", sa.Column("full_name", sa.String()))op.drop_column("customers", "customer_name")# What an intentional rename might requireop.alter_column(    "customers",    "customer_name",    new_column_name="full_name",)
```

The former can discard data; the latter expresses an identity-preserving rename, subject to database semantics.

### 4.2 CHECK constraints: an important version-sensitive distinction

Alembic introduced named-CHECK-constraint autogeneration in 1.19.0. It was subsequently made opt-in in 1.19.2.

For 1.20.0, it must explicitly be enabled:

```
context.configure(    connection=connection,    target_metadata=target_metadata,    autogenerate_plugins=[        "alembic.autogenerate.*",        "alembic.ext.checkconstraint_byname",    ],)
```

The plugin detects additions and removals through constraint names, not by checking expression equivalence.

This limitation is intentional. Databases can normalize, rewrite, or expand CHECK expressions during reflection. Comparing reflected SQL against the original expression could generate substantial false-positive differences.

Even with the plugin enabled, changing a constraint's expression while retaining its name is not reliably detected. Dialect support for CHECK reflection also varies.

Naming conventions are therefore particularly important when this capability is used.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+2



### 4.3 Multiple metadata collections

The target schema is not restricted to a single SQLAlchemy declarative base.

`target_metadata` can receive a sequence of `MetaData` collections:

```
target_metadata = [    operational_metadata,    analytical_metadata,    audit_metadata,]
```

This allows independently defined schema models to participate in a single comparison process.

However, the metadata collections must have unique table keys, including schema qualification. Alembic raises an error if the same schema/table identity appears in multiple collections.

This is a meaningful integration capability where database structure originates from several independently maintained Python modules or libraries.

### 4.4 Selective schema reflection

Broad database reflection can become an important cost when databases contain many schemas, tables, or objects outside the desired model.

Alembic provides two complementary filtering mechanisms:

`include_name` filters reflected object names early in the process, before full reflection of excluded objects. It is particularly valuable for restricting schema and table discovery.

`include_object` receives richer SQLAlchemy objects and can examine their metadata, reflected status, and corresponding objects on the other side of the comparison. It supports fine-grained decisions but cannot avoid reflection costs already incurred for database-side objects.

Both can be combined with `include_schemas=True`.

For metadata-backed policies, `include_object` can inspect `Column.info` or `Table.info`, allowing schema definitions to carry migration-related annotations without a parallel registry of objects to exclude.

Conversely, an `include_name` policy can prevent Alembic from treating unrelated existing database tables as tables to drop.

This introduces an important tradeoff: excluding database tables absent from the target metadata prevents destructive false positives, but it also prevents those exclusions from identifying genuine table deletions.

The filtering model offers a useful way to separate ownership of database objects, particularly when Alembic manages only part of a larger database schema.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



### 4.5 Extensible type comparison and rendering

Alembic separates detecting type differences from rendering Python code for those differences.

- `compare_type` can supply a custom equivalence policy for reflected and declared types.
- `render_item` can customize Python rendering of types and other migration objects.
- `user_module_prefix` can establish a stable namespace for application-defined types.
- `AutogenContext.imports` can register imports required in generated migration scripts.
- SQLAlchemy dialect-specific and custom types can participate in migrations when their constructors and renderers can be represented reliably.

A particularly useful architectural pattern is to expose custom types through a stable migration-facing module. Historical migrations can then reference that stable module rather than importing the current location of an ORM or application type, which may change during later refactoring.

Sources:

- Autogeneration behavior and configuration: [https://alembic.sqlalchemy.org/en/latest/autogenerate.html](https://alembic.sqlalchemy.org/en/latest/autogenerate.html?utm_source=chatgpt.com)
- Runtime configuration options: [https://alembic.sqlalchemy.org/en/latest/api/runtime.html](https://alembic.sqlalchemy.org/en/latest/api/runtime.html?utm_source=chatgpt.com)

## 5. Structured migration generation, rewriting, and plugins

One of Alembic's most consequential advanced capabilities is that generated migrations exist as structured Python operation objects before being written to migration scripts.

This makes Alembic more than a SQL diff generator: its schema comparison results can be inspected, transformed, validated, extended, and reused programmatically.

### 5.1 Structured schema differences

Two interfaces expose schema comparison results:

| API                                         | Output                           | Main purpose                                         |
| ------------------------------------------- | -------------------------------- | ---------------------------------------------------- |
| `alembic.autogenerate.compare_metadata()`   | Legacy list of difference tuples | Simple inspection and diff processing                |
| `alembic.autogenerate.produce_migrations()` | Structured `MigrationScript`     | Rich operation inspection, rewriting, and generation |

The richer model includes:

- `MigrationScript`: the overall generated revision.
- `UpgradeOps` and `DowngradeOps`: containers for forward and reverse operations.
- `ModifyTableOps`: grouped modifications for a specific table.
- `AddColumnOp`, `AlterColumnOp`, `CreateTableOp`, `DropConstraintOp`, and other `MigrateOperation` subclasses: concrete schema-change directives.

For example, a schema difference may be represented conceptually as:

```
MigrationScript
├── UpgradeOps
│   ├── CreateTableOp
│   └── ModifyTableOps
│       ├── AddColumnOp
│       └── CreateForeignKeyOp
└── DowngradeOps
    ├── ModifyTableOps
    │   ├── DropConstraintOp
    │   └── DropColumnOp
    └── DropTableOp
```

This intermediary representation enables operations that would otherwise require brittle SQL parsing or handwritten migration-script analysis.

The operation hierarchy is also executable through Alembic's `Operations.invoke()` mechanism. The official cookbook demonstrates traversing generated operation trees and invoking their constituent operations directly, including special handling for batch migrations. This is a lower-level capability and does not automatically provide the normal revision-history lifecycle.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



### 5.2 Intercepting revision generation

The `process_revision_directives` hook receives the revision directives before script generation is finalized.

It can:

- Remove empty autogenerated revisions.
- Inspect and reject certain generated operations.
- Modify the operation hierarchy.
- Replace generated directives.
- Produce multiple revision scripts from a generation process.
- Apply a custom operation-rewriting policy.

The hook participates in autogeneration by default, and can also participate in non-autogenerated revision creation when `revision_environment=True`.

This is a substantial extension point for enforcing migration-generation conventions without manually reimplementing schema comparison.

### 5.3 Operation-tree rewriting

Alembic supplies `alembic.autogenerate.rewriter.Rewriter`, which provides a dispatch-oriented mechanism for transforming migration operations.

Rewrite handlers can be registered for particular operation types, such as `AddColumnOp` or `CreateIndexOp`.

An operation can be replaced by a modified operation or a sequence of operations.

This can support policies such as:

- Introducing conditional DDL parameters into generated operations.
- Adjusting column or index properties.
- Inserting additional operations around selected structural changes.
- Removing redundant index removals when an entire table is already being dropped.
- Normalizing representations before scripts are rendered.

Rewrite transformations still need to respect dependency order, database capabilities, and downgrade semantics. A syntactically valid transformed operation tree is not automatically a safe migration.

Source: [https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html](https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html?utm_source=chatgpt.com)

### 5.4 Custom migration operations

Custom operations are built through the `MigrateOperation` and `Operations` extension APIs.

The key components are:

- `Operations.register_operation()` — expose a custom operation through the migration API.
- `Operations.implementation_for()` — register its execution implementation.
- `MigrateOperation.reverse()` — describe the corresponding reverse directive for autogeneration.
- `renderers.dispatch_for()` — specify how a custom operation becomes Python source code.
- SQLAlchemy SQL constructs and dialect compilers — implement backend-specific DDL without hardcoding every SQL variant.

This can extend migrations to database objects that Alembic's core operations do not model directly, including views, materialized views, database functions, or other vendor-specific structures.

The official cookbook's Replaceable Objects recipe illustrates the distinction between creating, replacing, and dropping versioned definitions of views and stored procedures.

For certain replaceable objects, correct downgrade behavior requires recovering an earlier definition rather than merely reversing a simple column-level change.

This is a capability with broad architectural consequences: schema-related database objects can participate in the same revision graph and deployment lifecycle as ordinary tables without requiring a separate handcrafted migration system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



### 5.5 Autogeneration comparators for new object types

Custom comparison functions can inspect database state and target metadata to emit new `MigrateOperation` instances.

Alembic exposes comparator scopes including schema, table, and column levels. The plugin framework also supports top-level autogeneration comparators.

A complete extension for a custom database object can therefore provide:

1. A representation of the desired object.
2. A mechanism for discovering the corresponding database objects.
3. Logic for identifying differences.
4. Custom upgrade and downgrade operations.
5. Dialect-aware operation implementations.
6. Python rendering for generated revisions.

These components are separable. An extension that implements only the operation APIs does not thereby provide autogeneration.

### 5.6 The plugin framework introduced in 1.18.0

Alembic 1.18.0 introduced a formal plugin system.

Plugins can be distributed through Python package entry points in the `alembic.plugins` group or registered explicitly with `Plugin.setup_plugin_from_module()`.

The central `Plugin` registration object allows an extension package to install operations, implementations, autogeneration comparators, and other handlers.

Autogeneration participation is configurable through `autogenerate_plugins`, whose default is:

```
["alembic.autogenerate.*"]
```

The built-in autogeneration system is divided into components for schemas, tables, types, constraints, defaults, and comments.

Plugin selection supports explicit names, wildcard matching, and negated patterns. Some components depend on others—for example, column-level comparison relies on table discovery—so individual built-ins cannot always be disabled independently without consequences.

Important distinction: disabling a plugin's autogeneration comparator does not necessarily disable the custom migration operations that the plugin registered. Registration and participation in a comparison pass are separate mechanisms.

The framework also provides priority-based comparator dispatch, allowing specialized handlers to participate in or stop further comparison processing.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



### 5.7 Post-generation processing

Alembic supports `post_write_hooks` for processing revision files after generation.

These can invoke Python modules, installed console scripts, executable commands, or custom registered hooks, depending on configuration.

Formatting tools such as Black or Ruff are natural examples. Other potential uses include structural checks, standardization, and static analysis.

Post-write hooks operate on generated files, whereas `process_revision_directives` and `Rewriter` operate on Alembic's migration representation before rendering. These stages have different tradeoffs:

| Extension stage           | What it operates on                    | Distinctive advantage                          |
| ------------------------- | -------------------------------------- | ---------------------------------------------- |
| Autogeneration comparator | Database and target-schema differences | Detect additional change types                 |
| Operation rewriting       | Structured migration directives        | Semantic transformation without source parsing |
| Custom renderer           | Migration operation objects            | Control generated Python representation        |
| Post-write hook           | Generated file                         | Apply formatters and external tooling          |

The interaction between these mechanisms is one of Alembic's strongest opportunities to eliminate repetitive custom migration-generation logic.

Sources:

- Autogeneration extension API: [https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html](https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html?utm_source=chatgpt.com)
- Operation extension API: [https://alembic.sqlalchemy.org/en/latest/api/operations.html](https://alembic.sqlalchemy.org/en/latest/api/operations.html?utm_source=chatgpt.com)
- Plugin API: [https://alembic.sqlalchemy.org/en/latest/api/plugins.html](https://alembic.sqlalchemy.org/en/latest/api/plugins.html?utm_source=chatgpt.com)
- Cookbook, including replaceable objects: [https://alembic.sqlalchemy.org/en/latest/cookbook.html](https://alembic.sqlalchemy.org/en/latest/cookbook.html?utm_source=chatgpt.com)

## 6. Batch migrations, table reconstruction, and constraint identity

### 6.1 SQLite's move-and-copy model

SQLite supports a narrower range of direct table-alteration operations than PostgreSQL and several other relational databases. Alembic addresses this through `op.batch_alter_table()`.

A batch context groups changes to one table:

```
with op.batch_alter_table("measurements") as batch:    batch.add_column(sa.Column("quality_code", sa.Integer()))    batch.drop_column("obsolete_flag")
```

Where table reconstruction is needed, Alembic performs a sequence resembling:

1. Reflect the existing table definition.
2. Construct a replacement table incorporating the requested changes.
3. Copy retained columns using `INSERT ... SELECT`.
4. Drop the original table.
5. Rename the replacement table.

The default `recreate="auto"` behavior performs this move-and-copy process on SQLite when the batch includes operations beyond the eligible simple column-addition case. On other supported backends, the same batch context generally emits ordinary DDL.

`recreate="always"` forces reconstruction, including on databases that otherwise support direct alteration. The documentation identifies this as useful in some circumstances but cautions that constraints referencing the replaced table can require manual intervention.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



### 6.2 Advanced reconstruction controls

Batch migration is configurable rather than being a fixed copy algorithm.

| Mechanism                    | Capability                                                        |
| ---------------------------- | ----------------------------------------------------------------- |
| `reflect_args`               | Override aspects of reflected table structure                     |
| `reflect_kwargs`             | Supply reflection options and event listeners                     |
| `copy_from`                  | Provide an explicit source `Table` instead of reflecting          |
| `naming_convention`          | Name reflected constraints that otherwise lack usable identifiers |
| `table_args`, `table_kwargs` | Supply attributes for the recreated table                         |
| `partial_reordering`         | Specify column-order relationships                                |
| `recreate`                   | Control whether move-and-copy reconstruction is used              |

Reflection hooks can correct or normalize types before the replacement structure is constructed. For example, a SQLAlchemy `column_reflect` event can substitute a more precise type for one that the backend's introspection exposes ambiguously.

This creates an important connection between SQLAlchemy's reflection extensibility and Alembic's ability to reconstruct tables correctly.

### 6.3 Offline reconstruction requires a schema definition

Ordinary batch reconstruction depends on live table reflection.

When offline SQL generation is required, a `copy_from` argument can supply the source `Table` definition, avoiding the need for a live database connection.

However, `render_as_batch=True` does not automatically generate these complete offline table definitions. Migration authors must provide them as necessary.

Consequently, batch operations are not unconditionally compatible with offline SQL generation merely because both capabilities exist in Alembic.

### 6.4 Constraint behavior and the 1.20.0 improvements

Constraint handling is one of the most consequential aspects of table reconstruction.

Named CHECK constraints can be reflected and carried into a recreated table. But when a column is dropped or renamed, Alembic cannot always infer that a separately reflected CHECK constraint refers to that column. Such constraints may need explicit removal.

Unnamed CHECK constraints are more problematic. They cannot be reliably reproduced because Alembic cannot determine whether they reference changed or removed columns.

Alembic 1.20.0 now warns when an unnamed CHECK constraint would be omitted during batch recreation. Earlier versions could silently omit it. Version 1.20.0 also corrected cases involving duplicate or inconsistently named CHECK constraints generated by SQLAlchemy `Boolean` and `Enum` types.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



Foreign keys also require attention. In SQLite, a table-replacement migration may require disabling foreign-key enforcement during the replacement process; the ordinary `PRAGMA foreign_keys` behavior can prevent the original table from being dropped. Other databases have different referential-integrity restrictions.

Because table reconstruction copies data and replaces a physical object, its performance, locking, storage, index, and dependency implications are fundamentally different from a metadata-only `ALTER TABLE` operation.

### 6.5 Naming conventions as an identity mechanism

SQLAlchemy's `MetaData(naming_convention=...)` is particularly synergistic with Alembic.

A naming convention creates reproducible names for indexes and constraints, including those introduced through shorthand SQLAlchemy declarations.

Alembic incorporates the convention when creating operations and when rendering autogenerated migrations.

`op.f("constraint_name")` indicates that a name is already fully formed and should not be expanded again by the naming convention.

The deeper value is not stylistic consistency. Stable constraint names establish durable identities that migrations can reference across database instances and dialects. That supports reliable constraint removal, schema comparison, and table reconstruction.

Sources:

- Batch migrations: [https://alembic.sqlalchemy.org/en/latest/batch.html](https://alembic.sqlalchemy.org/en/latest/batch.html?utm_source=chatgpt.com)
- Constraint naming: [https://alembic.sqlalchemy.org/en/latest/naming.html](https://alembic.sqlalchemy.org/en/latest/naming.html?utm_source=chatgpt.com)

## 7. Online execution, offline SQL generation, and transaction semantics

Alembic supports two substantially different execution models through a common migration interface.

### 7.1 Online execution

Online mode applies migration operations through a SQLAlchemy `Connection`.

The execution context determines the backend dialect and delegates DDL compilation and execution accordingly.

This enables operations that depend on live database state, including:

- Schema reflection.
- Queries that inspect existing rows.
- Data transformations based on current values.
- Conditional decisions based on database results.
- Transactional coordination where supported.

Online execution is the natural mode for migrations that cannot be represented as a predetermined SQL script.

### 7.2 Offline SQL generation

Offline mode compiles migration operations into SQL rather than executing them.

```
alembic upgrade head --sql > upgrade.sql

alembic upgrade abc123:def456 --sql > incremental.sql
```

The second example uses the offline-only revision-range syntax. Because offline mode does not connect to the database and inspect `alembic_version`, the starting revision must be known or supplied; otherwise, SQL generation generally begins from `base`.

The generated SQL can include DDL, transaction delimiters where appropriate, and Alembic version-table updates.

This makes Alembic a useful SQL generation engine for environments where migration execution and migration authoring are institutionally separated.

`output_buffer`, `dialect_name`, `url`, `literal_binds`, and related configuration options enable control over SQL generation and its target dialect. An environment can generate separate SQL streams for multiple databases.

Limit: offline execution does not return database results. A migration that relies on querying actual data or live schema state cannot simply be compiled into an equivalent static SQL script.

Similarly, SQLAlchemy bound parameters may require literal rendering. `op.inline_literal()` and appropriate `bulk_insert()` options address some such cases, but arbitrary Python logic depending on query results remains online-only.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



### 7.3 DDL transaction behavior

`context.begin_transaction()` establishes an Alembic logical transaction boundary.

Whether it results in a real transactional database operation depends on the dialect, the database's DDL semantics, and Alembic configuration.

Relevant controls include:

- `transactional_ddl` — override Alembic's expectation of transactional DDL support.
- `transaction_per_migration` — use a transaction boundary for each migration rather than treating a sequence of migrations as one unit where supported.
- SQLAlchemy connection and transaction ownership — determine how migration execution participates in surrounding code.

These settings do not override the database engine's fundamental transaction capabilities.

For example, a dialect that implicitly commits particular DDL statements cannot be made fully transactional simply by setting `transactional_ddl=True`.

### 7.4 Autocommit blocks

Some database commands must execute outside ordinary transaction blocks.

Alembic exposes `MigrationContext.autocommit_block()`, typically accessed through `op.get_context()`.

```
def upgrade():    with op.get_context().autocommit_block():        op.execute("ALTER TYPE mood ADD VALUE 'new_state'")
```

This pattern is documented for PostgreSQL commands that require autocommit under the relevant server conditions.

The important caveat is that an autocommit block unconditionally commits the transaction preceding the block. The entire migration is therefore no longer atomic.

The documentation recommends `transaction_per_migration` when migrations use these blocks so transaction boundaries more closely match the operational assumptions of those scripts.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



### 7.5 Hooks surrounding migration execution

`EnvironmentContext.configure()` also provides `on_version_apply` callbacks that run for each migration step after its operations have executed but before its transaction is finalized.

The callback receives the migration context, step information, current revision heads, and arguments supplied to the migration run.

This is useful for instrumentation, migration auditing, or integration with an execution framework, subject to the same transaction and exception semantics as the surrounding run.

Alembic also permits customization of the version table through `version_table`, `version_table_schema`, and related parameters.

These are native facilities for controlling migration execution metadata; they are distinct from database-level logging, locking, and auditing systems.

Sources:

- Runtime objects and transaction controls: [https://alembic.sqlalchemy.org/en/latest/api/runtime.html](https://alembic.sqlalchemy.org/en/latest/api/runtime.html?utm_source=chatgpt.com)
- Offline SQL generation: [https://alembic.sqlalchemy.org/en/latest/offline.html](https://alembic.sqlalchemy.org/en/latest/offline.html?utm_source=chatgpt.com)

## 8. Programmatic control, migration-state inspection, and validation

Alembic's command-line interface is a thin layer over a set of Python APIs. Migration execution, revision-history inspection, and DDL operations can all be invoked without launching a subprocess.

This is especially significant when migration functionality must participate in a larger application, test harness, deployment system, or database-management service.

### 8.1 Four important API layers

| Layer                     | Principal objects                          | Responsibility                                       |
| ------------------------- | ------------------------------------------ | ---------------------------------------------------- |
| Command and configuration | `Config`, `alembic.command`                | Invoke migration workflows                           |
| Revision history          | `ScriptDirectory`, `Script`, `RevisionMap` | Inspect and navigate migration scripts               |
| Execution environment     | `EnvironmentContext`, `MigrationContext`   | Configure connections and manage migration execution |
| DDL operations            | `Operations`, `BatchOperations`            | Execute or compile individual migration directives   |

These APIs have different independence characteristics.

`Config` and `ScriptDirectory` are appropriate when working with a migration environment and its revision history.

`MigrationContext` can instead be instantiated from a connection or dialect without a configured migration-script directory.

An `Operations` instance can then use that context to issue migration directives independently of the normal CLI and revision-file machinery.

The latter is useful when Alembic's DDL abstraction is desired without necessarily using its full version-management system.

### 8.2 Programmatic commands

Functions in `alembic.command` generally accept a `Config` instance as their first argument.

```
from alembic import commandfrom alembic.config import Configcfg = Config("alembic.ini")command.ensure_version(cfg)command.upgrade(cfg, "head")command.current(cfg, check_heads=True)
```

Beyond upgrading and downgrading, the API provides revision creation, merging, stamping, branch inspection, history inspection, and autogeneration checks.

A particularly useful integration is connection sharing.

An existing SQLAlchemy connection can be placed in `Config.attributes`, allowing a suitably configured `env.py` to use it rather than creating its own engine:

```
with engine.begin() as connection:    cfg.attributes["connection"] = connection    command.upgrade(cfg, "head")
```

This supports transaction coordination between migration operations and surrounding SQLAlchemy code, to the extent permitted by the database and individual migration operations.

`Config.attributes` accepts arbitrary Python objects, not just configuration strings. It can transport connections, engines, schema objects, or other context into the migration environment.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+2



### 8.3 Direct migration-context usage

For utilities that do not need the revision-file lifecycle, the lower-level APIs can be more appropriate.

The following is an illustrative sketch, not an executed example:

```
from alembic.migration import MigrationContextfrom alembic.operations import Operationswith engine.begin() as connection:    migration_context = MigrationContext.configure(connection)    operations = Operations(migration_context)    operations.add_column(        "events",        sa.Column("source", sa.String(80)),    )
```

This retains Alembic's operation compilation and backend handling but does not, by itself, create a new revision or advance the database's revision history.

That distinction matters: using Alembic's DDL operations and using Alembic's version-tracked migration framework are separate choices.

### 8.4 Revision-graph introspection

`ScriptDirectory` exposes the migration scripts as a navigable graph.

Representative methods include `get_heads()`, `get_bases()`, `get_revisions()`, `iterate_revisions()`, and `generate_revision()`.

The corresponding `MigrationContext` exposes database-side revision information through methods such as `get_current_heads()`.

Methods that expect a single head, including `ScriptDirectory.get_current_head()`, can raise an error when several heads exist. Graph-aware inspection should therefore use plural-head methods when branching is possible.

These facilities can support custom migration reports, revision-path analysis, diagnostic commands, and dependency visualization without separately parsing Python migration files.

Source: [https://alembic.sqlalchemy.org/en/latest/api/script.html](https://alembic.sqlalchemy.org/en/latest/api/script.html?utm_source=chatgpt.com)

### 8.5 Two distinct validation questions

Alembic provides two complementary checks that are easy to conflate.

| Check                           | Question it answers                                         | Important limitation                                                     |
| ------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------ |
| `alembic check`                 | Would autogeneration find pending schema-change operations? | Limited to objects and differences covered by the configured comparators |
| `alembic current --check-heads` | Has the database reached all migration-script heads?        | Does not establish that the physical schema actually matches the models  |

`alembic check` uses the autogeneration comparison machinery and fails when it detects pending upgrade operations, without generating a new revision file.

`current --check-heads` is a revision-state assertion introduced in 1.17.1. It can also be invoked through `command.current(..., check_heads=True)` and raises `DatabaseNotAtHead` when applicable.

These checks are complementary rather than interchangeable. A database can have the expected revision identifier but contain an untracked manual schema change. Conversely, a metadata comparison may detect no differences even when the version table is behind.

For automated validation, this distinction permits a separation between migration history completeness and detectable schema alignment.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



### 8.6 Stamping and baselining

`alembic stamp` updates revision tracking without applying the intervening schema transformations.

This has legitimate uses when introducing revision tracking to an existing database or when a database was constructed through SQLAlchemy's `MetaData.create_all()` and is already equivalent to the expected target schema.

But stamping asserts a migration state; it does not establish schema equivalence.

The command also supports multiple revision targets and a `purge` option for clearing existing version-table entries before stamping.

`ensure_version` is a narrower operation that creates the version table if it does not exist.

These operations make Alembic flexible for baselining and state management, but incorrect stamping can conceal a mismatch between the version history and actual database contents.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+2



### 8.7 Custom command-line tooling

Since Alembic 1.15.3, `CommandLine.register_command()` has allowed custom command functions to be registered with an Alembic CLI instance.

A function's name, signature, and docstring determine its command identity, arguments, and help text.

This permits a purpose-built database-management CLI to incorporate Alembic's existing commands while adding specialized diagnostics, validation, or orchestration functions.

It does not automatically insert subcommands into the globally installed `alembic` executable; the documented mechanism is to instantiate and extend a `CommandLine` object.

Sources:

- Commands: [https://alembic.sqlalchemy.org/en/latest/api/commands.html](https://alembic.sqlalchemy.org/en/latest/api/commands.html?utm_source=chatgpt.com)
- Configuration and custom CLI: [https://alembic.sqlalchemy.org/en/latest/api/config.html](https://alembic.sqlalchemy.org/en/latest/api/config.html?utm_source=chatgpt.com)
- Runtime API: [https://alembic.sqlalchemy.org/en/latest/api/runtime.html](https://alembic.sqlalchemy.org/en/latest/api/runtime.html?utm_source=chatgpt.com)

## 9. Multiple databases, schemas, tenants, and asynchronous execution

Several Alembic mechanisms support database configurations more complex than one application connected to one schema. However, they represent different architectural models and should not be treated as interchangeable.

### 9.1 Multiple independently configured environments

An Alembic configuration can maintain separate environments with different script directories and settings.

The `--name` option selects a named configuration section from an INI file.

This provides independent configuration and migration histories when components or databases should not share a single revision lifecycle.

### 9.2 Multiple engines within one environment

Alembic includes a `multidb` environment template. It can invoke migration execution for multiple SQLAlchemy engines from a shared migration environment.

Autogeneration for multiple engines uses separate `upgrade_token` and `downgrade_token` values for each database.

A single generated migration script can therefore contain distinct upgrade and downgrade functions for each engine.

The structured `MigrationScript` representation supports multiple `UpgradeOps` and `DowngradeOps` collections, each associated with its engine-specific token.

An implementation detail matters for custom revision-generation hooks: `context.run_migrations()` is invoked repeatedly, and accumulated operation collections change shape across invocations. Rewriters or `process_revision_directives` callbacks must account for that rather than assuming a single comparison pass.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



Multi-engine support coordinates migration generation and execution. It does not imply that Alembic provides a distributed atomic transaction across independent databases.

### 9.3 Multi-schema discovery

`include_schemas=True` permits autogeneration to discover objects across schemas exposed by SQLAlchemy's `Inspector`.

Schema-qualified metadata and inclusion filters determine which objects participate.

This is appropriate when different schemas contain different managed objects and are part of a common target model.

It is distinct from using one identical schema model repeatedly for separate tenants.

### 9.4 Multi-tenancy remains a recipe-level capability

Alembic's official documentation explicitly states that it does not provide first-class multi-tenant support.

Its cookbook illustrates schema-level tenant targeting through PostgreSQL's `search_path` or MySQL/MariaDB's `USE` command, typically selecting the tenant through an `-x` argument.

This recipe requires careful handling of SQLAlchemy metadata schema qualification, connection state, and transaction behavior.

The documentation also warns that Alembic does not adequately support SQLAlchemy's `schema_translate_map` for this purpose.

Consequently, applying one migration history across many tenant schemas is possible through custom orchestration, but Alembic does not supply a complete built-in tenant migration coordinator, tenant-state registry, or cross-tenant execution guarantee.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



### 9.5 SQLAlchemy asyncio integration

Alembic works with SQLAlchemy asynchronous engines, including asynchronous DBAPI drivers.

However, its migration interface is fundamentally synchronous. The official documentation explicitly states that Alembic does not provide a direct asynchronous command API.

Instead, the normal integration is an `AsyncEngine` or `AsyncConnection` that invokes synchronous migration code through SQLAlchemy's `run_sync()` adapter.

Alembic provides `async` and `pyproject_async` environment templates for these arrangements.

It is also possible to invoke an Alembic command programmatically through an asynchronous connection by passing the adapted synchronous connection through `Config.attributes`.

Separately, `op.run_async()` allows a synchronous migration's `upgrade()` or `downgrade()` function to invoke an asynchronous callable using an `AsyncConnection` that shares the migration transaction. This method requires execution through an asynchronous dialect.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



The distinction is valuable: asynchronous database connectivity is supported, but Alembic does not itself become a fully asynchronous migration orchestrator.

Sources:

- Asyncio, multi-tenancy, and connection-sharing recipes: [https://alembic.sqlalchemy.org/en/latest/cookbook.html](https://alembic.sqlalchemy.org/en/latest/cookbook.html?utm_source=chatgpt.com)
- Multi-engine autogeneration: [https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html](https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html?utm_source=chatgpt.com)
- Environment configuration: [https://alembic.sqlalchemy.org/en/latest/tutorial.html](https://alembic.sqlalchemy.org/en/latest/tutorial.html?utm_source=chatgpt.com)

## 10. Performance, reliability, and operational boundaries

Alembic's performance characteristics are best understood by separating the cost of discovering schema differences, generating migration instructions, and executing physical changes against a database.

### 10.1 More efficient reflection in Alembic 1.18+

Alembic 1.18.0 introduced a significant autogeneration optimization by adopting SQLAlchemy 2.0's bulk `Inspector` methods.

For selected dialects, including PostgreSQL and Oracle, these methods can reflect collections of tables using a bounded number of batched queries rather than a sequence of queries proportional to the number of tables.

The release notes describe the improvement as a shift from O(N) to O(1) reflection queries for the relevant operations.

This is a query-count improvement, not a guarantee of constant total execution time. The server still processes metadata proportional to the schema being inspected, and Python must still construct and compare the reflected objects.

The benefit depends on the dialect's implementation of bulk reflection and on the number of eligible objects. Filtering with `include_name` remains important, particularly when Alembic should manage only a subset of a database.

The 1.18.3 release also corrected a regression involving foreign keys referencing filtered-out tables, preserving the bulk-reflection optimization while introducing placeholder objects for those references.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation

+1



### 10.2 Migration performance is often dominated by database work

Alembic controls what SQL operations are requested and how they are sequenced. It is not responsible for the database engine's internal DDL algorithms.

An `ALTER TABLE` operation may be:

- A relatively inexpensive metadata modification.
- A constraint validation involving a table scan.
- A table rewrite.
- An index build.
- A locking operation that blocks other transactions.

Which occurs depends on the database version, dialect, table structure, and specific DDL statement.

Alembic's native facilities can influence those outcomes—for example, conditional DDL, inline foreign-key creation, SQLAlchemy dialect-specific options, and choosing direct alteration over batch reconstruction.

They do not eliminate the need to understand database-native behavior.

The 1.18.2 `inline_references` enhancement is a concrete example of a library-level capability that can avoid separate validation work in certain circumstances. Its potential performance value comes from the SQL it asks the server to execute, not from Alembic performing the work faster in Python.

### 10.3 Revision tracking is not schema reconciliation

The `alembic_version` table records the revision frontier that Alembic believes has been applied. It is not a continuously maintained description of all actual database objects.

Manual DDL, incomplete or externally executed scripts, and incorrectly stamped versions can cause the real schema and revision state to diverge.

The documented `check` and `current --check-heads` facilities help reveal particular classes of inconsistency, but neither is a complete database schema verifier.

Similarly, Alembic does not promise that autogeneration will reconcile every object omitted from SQLAlchemy metadata or unsupported by a given dialect.

### 10.4 Migration concurrency and deployment coordination

Revision ordering and database migration concurrency are different problems.

Alembic understands which migration revisions depend on which other revisions. It does not thereby guarantee safe concurrent execution of independent migration processes targeting the same database.

For a migration system used in distributed deployments, coordination and exclusivity may require database-specific advisory locks, deployment serialization, or another external mechanism.

This is an architectural consideration, not an assertion that every Alembic deployment needs additional locking machinery.

The database's own DDL locking and transaction behavior also remains relevant even when only one Alembic process is running.

### 10.5 Data migration and compatibility windows

The official cookbook distinguishes schema migrations from data migrations and cautions that extensive data transformations are not always best placed within Alembic's revision files.

Three approaches are described:

- Small data transformations executed within migrations, including `bulk_insert`.
- Separate data migration scripts coordinated between structural changes.
- Online transitions where old and new representations coexist while data is progressively moved.

The third approach typically requires application-level compatibility logic, such as dual writes or transitional reads. Alembic supplies the database schema transitions but not those application behaviors.

The distinction matters for large databases and continuously available systems.

A migration can be fully valid in terms of Alembic's revision graph while being incompatible with a currently running application version, destructively transforming existing values, or taking an unacceptable amount of time to execute.

### 10.6 Downgrades are not necessarily reversible

Alembic supports downgrade functions and traversing the revision graph backward. This is not a guarantee of lossless reversibility.

Dropping a column, changing a type, deleting data, or replacing an application-dependent database object may destroy information that cannot be reconstructed later.

For some transitions, the technically appropriate downgrade may require restoration from an external backup, a compensating operation, or explicit refusal to perform the downgrade.

The migration author's responsibility is therefore to distinguish an operation that has an executable inverse from one that is actually information-preserving.

Source: [https://alembic.sqlalchemy.org/en/latest/cookbook.html](https://alembic.sqlalchemy.org/en/latest/cookbook.html?utm_source=chatgpt.com)

## 11. Ecosystem integrations and capability boundaries

Alembic derives much of its utility from composability with SQLAlchemy and specialized extensions.

The key question for each integration is which part of the schema-management lifecycle it supplies.

### 11.1 SQLAlchemy Core, ORM, and dialects

SQLAlchemy Core is Alembic's most fundamental dependency. It provides the schema object model, expression construction, database introspection, SQL compilation, and connection abstraction.

SQLAlchemy ORM is optional from Alembic's conceptual perspective. ORM declarative metadata is a convenient way to supply `target_metadata`, but migrations can also operate against Core `MetaData` objects, reflected tables, or handwritten operations.

SQLAlchemy dialects supply backend-specific semantics that Alembic uses and extends through its own DDL implementations.

This relationship avoids requiring Alembic to maintain a standalone SQL parser, SQL type model, expression compiler, or database connectivity system.

The other side of that integration is that Alembic's behavior depends on how accurately the chosen dialect reflects and compiles the relevant database features.

### 11.2 PostgreSQL object autogeneration: Alembic Utils

[Alembic Utils](https://github.com/olirice/alembic_utils?utm_source=chatgpt.com)

Alembic Utils is an independently maintained extension for managing PostgreSQL objects such as functions, views, triggers, and policies through Alembic.

It extends the migration model beyond Alembic's built-in table-oriented autogeneration.

This is distinct from the core Alembic cookbook's replaceable-objects example, which demonstrates how to construct such functionality but is not itself a comprehensive implementation.

For systems that treat database functions or views as important schema objects, such an extension may remove considerable custom comparison, revision-generation, and DDL machinery. Its object coverage, PostgreSQL-version compatibility, and precise semantics belong to the companion project rather than to Alembic itself.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 11.3 PostgreSQL ENUM evolution

[alembic-postgresql-enum](https://pypi.org/project/alembic-postgresql-enum/?utm_source=chatgpt.com)

The `alembic-postgresql-enum` package adds specialized autogeneration for PostgreSQL enum objects and their values, including creation, deletion, and value-set changes.

This is important because database-native enums are independent schema objects with evolution rules that differ from ordinary columns.

The package's documentation describes functionality for detecting additions, removals, alterations, and ordering changes in enum values. This should not be confused with Alembic's basic column-type comparison or MySQL's dialect-specific enum-value comparison.

It is a third-party extension with its own compatibility and configuration requirements.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



### 11.4 Web-framework integration

Framework integrations such as Flask-Migrate wrap Alembic and SQLAlchemy to integrate migration operations with a web application's configuration and command-line environment.

They generally do not replace Alembic's revision graph or migration engine. Instead, they provide framework-aware initialization, configuration, and command execution.

This distinction matters when considering whether an additional framework-specific abstraction is necessary: Alembic already exposes both programmatic commands and customizable execution environments.

### 11.5 SQLAlchemy schema extensions and database-native objects

Many databases expose entities beyond SQLAlchemy's portable table, index, and constraint model:

- Roles, privileges, and policies.
- Extensions and custom types.
- Sequences.
- Views and materialized views.
- Stored procedures and functions.
- Triggers and other procedural definitions.
- Vendor-specific index and storage options.

Alembic does not offer complete, uniform, built-in autogeneration of this entire category.

However, the operation plugin system, custom comparators, SQLAlchemy DDL compilation, and external extensions can bring selected objects under Alembic's revision control.

The distinction between being able to execute DDL for an object and being able to discover and automatically generate changes for that object is especially important.

## 12. Version-specific capabilities and compatibility

Alembic's recent development has materially expanded its extensibility and improved autogeneration efficiency.

| Version | Notable capability or change                                                                          |
| ------- | ----------------------------------------------------------------------------------------------------- |
| 1.15.3  | Programmatic custom CLI commands through `CommandLine.register_command()`                             |
| 1.16.0  | `pyproject.toml` configuration support and related initialization template                            |
| 1.17.1  | Database revision-head assertion through `current --check-heads`                                      |
| 1.17.2  | Replacement of existing operation implementations                                                     |
| 1.18.0  | Plugin system, selectable autogeneration comparators, bulk reflection, nested revision-file templates |
| 1.18.2  | Inline foreign-key references for column additions                                                    |
| 1.18.4  | Explicit opt-in inline primary-key syntax                                                             |
| 1.18.5  | `merge --splice` and dependency-aware head enumeration                                                |
| 1.19.0  | Named-CHECK-constraint autogeneration introduced                                                      |
| 1.19.2  | Named-CHECK autogeneration disabled by default and moved to the opt-in `alembic.ext` namespace        |
| 1.20.0  | SQLAlchemy 2.0 minimum; batch CHECK handling and warnings improved; default-comparison fixes          |

Two details deserve special attention.

First, Alembic 1.18.5 added `ScriptDirectory.get_heads(consider_depends_on=True)`, allowing dependency references to influence which revisions are treated as effective heads for that inspection. This is useful when multiple bases and `depends_on` relationships complicate naïve head enumeration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation



Second, Alembic 1.18.0 made `file_template` capable of creating migration files in nested directories. Such layouts require `recursive_version_locations=True` so Alembic discovers the revisions. This is a source-organization feature, distinct from multiple-base revision management.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.0 documentation



### Important 1.20.0 compatibility notes

- SQLAlchemy 1.4 support has been dropped. Alembic 1.20.0 requires SQLAlchemy 2.0 or later.&#x20;

  [image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

  Alembic 1.20.0 documentation

- Named-CHECK autogeneration remains opt-in, despite its initial default-enabled behavior in 1.19.0 and 1.19.1.

- SQLAlchemy 2.1 offers some additional integration behavior, including improved handling of foreign-key target identifiers containing dots in schema, table, or column names. The relevant 1.19.2 change falls back to older parsing behavior under SQLAlchemy 2.0.&#x20;

  [image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

  Alembic 1.20.0 documentation

- The 1.20.1 changelog section is unreleased as of the research date. It lists prospective fixes, including a plugin-entry-point loading issue. These must not be treated as fixes present in 1.20.0.&#x20;

  [image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

  Alembic 1.20.0 documentation



The complete version history is maintained at:

[https://alembic.sqlalchemy.org/en/latest/changelog.html](https://alembic.sqlalchemy.org/en/latest/changelog.html?utm_source=chatgpt.com)

## 13. Architectural significance

Alembic's capabilities combine into several useful higher-level models of database schema management.

### A versioned schema transformation engine

The revision graph, migration operations, dialect-aware compilation, and version table together provide a system for applying and tracking schema transformations.

The graph is a first-class dependency model, not merely a chronological sequence of files. It accommodates branches, merges, separate roots, and cross-lineage dependencies.

### A structured schema-difference engine

`produce_migrations()` and the autogeneration plugin framework allow schema differences to be treated as structured operations before they become Python source or SQL.

This supports analysis, custom transformation, filtering, and extended object coverage without requiring bespoke diff representations or SQL-string manipulation.

Its limitation is that a schema comparison cannot establish the intent behind every change.

### A reusable database DDL kernel

`MigrationContext` and `Operations` can function independently of the full migration-file framework.

They provide a way to reuse Alembic's backend-aware DDL mechanisms in other Python database-management facilities, while SQLAlchemy continues to handle expression compilation and connectivity.

This is especially useful where a system needs controlled schema operations but does not necessarily need to generate or execute revision files for every operation.

### A programmable migration lifecycle

`Config`, `EnvironmentContext`, the command API, revision-generation hooks, post-write hooks, and custom CLI commands provide composable integration points.

Together, these support migration environments where connection ownership, comparison rules, script generation, validation, and execution behavior are controlled by a surrounding system.

The important distinction is that Alembic makes such orchestration possible without necessarily supplying an end-to-end deployment platform itself.

### An extensible database-object versioning framework

Custom migration operations, autogeneration comparators, renderers, and the plugin system make it possible to bring database-native constructs under a common versioned migration model.

This is one of Alembic's most valuable opportunities for reducing specialized migration infrastructure.

The strongest fit is for database objects whose discovery, desired-state representation, transformation semantics, and reverse behavior can be expressed reliably.

## 14. Primary-source reference map

The following direct URLs provide the most useful routes for deeper engineering investigation. They are organized by the functionality covered rather than by the order in which the documentation was consulted.

| Area                                                  | Source                                                                                                                                                  |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Migration graph, branches, dependencies               | [https://alembic.sqlalchemy.org/en/latest/branches.html](https://alembic.sqlalchemy.org/en/latest/branches.html?utm_source=chatgpt.com)                 |
| Full DDL operation reference                          | [https://alembic.sqlalchemy.org/en/latest/ops.html](https://alembic.sqlalchemy.org/en/latest/ops.html?utm_source=chatgpt.com)                           |
| Autogeneration capabilities and limitations           | [https://alembic.sqlalchemy.org/en/latest/autogenerate.html](https://alembic.sqlalchemy.org/en/latest/autogenerate.html?utm_source=chatgpt.com)         |
| Structured autogeneration and rewriting APIs          | [https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html](https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html?utm_source=chatgpt.com) |
| Operation plugins and implementations                 | [https://alembic.sqlalchemy.org/en/latest/api/operations.html](https://alembic.sqlalchemy.org/en/latest/api/operations.html?utm_source=chatgpt.com)     |
| Plugin registration and comparator selection          | [https://alembic.sqlalchemy.org/en/latest/api/plugins.html](https://alembic.sqlalchemy.org/en/latest/api/plugins.html?utm_source=chatgpt.com)           |
| Runtime and transaction configuration                 | [https://alembic.sqlalchemy.org/en/latest/api/runtime.html](https://alembic.sqlalchemy.org/en/latest/api/runtime.html?utm_source=chatgpt.com)           |
| Programmatic commands and state checks                | [https://alembic.sqlalchemy.org/en/latest/api/commands.html](https://alembic.sqlalchemy.org/en/latest/api/commands.html?utm_source=chatgpt.com)         |
| Revision graph introspection                          | [https://alembic.sqlalchemy.org/en/latest/api/script.html](https://alembic.sqlalchemy.org/en/latest/api/script.html?utm_source=chatgpt.com)             |
| DDL internals and dialect implementation              | [https://alembic.sqlalchemy.org/en/latest/api/ddl.html](https://alembic.sqlalchemy.org/en/latest/api/ddl.html?utm_source=chatgpt.com)                   |
| SQLite and general table reconstruction               | [https://alembic.sqlalchemy.org/en/latest/batch.html](https://alembic.sqlalchemy.org/en/latest/batch.html?utm_source=chatgpt.com)                       |
| Offline SQL script generation                         | [https://alembic.sqlalchemy.org/en/latest/offline.html](https://alembic.sqlalchemy.org/en/latest/offline.html?utm_source=chatgpt.com)                   |
| Constraint naming conventions                         | [https://alembic.sqlalchemy.org/en/latest/naming.html](https://alembic.sqlalchemy.org/en/latest/naming.html?utm_source=chatgpt.com)                     |
| Advanced recipes, async, tenants, replaceable objects | [https://alembic.sqlalchemy.org/en/latest/cookbook.html](https://alembic.sqlalchemy.org/en/latest/cookbook.html?utm_source=chatgpt.com)                 |
| Migration environments and configuration              | [https://alembic.sqlalchemy.org/en/latest/tutorial.html](https://alembic.sqlalchemy.org/en/latest/tutorial.html?utm_source=chatgpt.com)                 |
| Version history and change details                    | [https://alembic.sqlalchemy.org/en/latest/changelog.html](https://alembic.sqlalchemy.org/en/latest/changelog.html?utm_source=chatgpt.com)               |
| Upstream source code                                  | [https://github.com/sqlalchemy/alembic](https://github.com/sqlalchemy/alembic?utm_source=chatgpt.com)                                                   |

### Overall assessment

Alembic's most significant architectural contribution is the combination of a versioned dependency graph, database-aware DDL operations, structured schema comparison, and programmable extension points.

These capabilities allow the library to serve several roles: a conventional migration manager, a schema-drift detector, a programmable migration engine, an operation-generation framework, and a foundation for managing additional database-native object types through extensions.

The areas where its limitations matter most are automated interpretation of schema changes, database-specific DDL semantics, large data transformations, multi-tenant orchestration, and distributed deployment coordination.

The underlying design is particularly strong where SQLAlchemy's metadata and dialect abstractions accurately represent the database structures being managed, and where custom operations or established companion libraries can extend that model instead of creating separate migration machinery.

# Alembic 1.20.x — Advanced Capability Addendum

Research date: November 1, 2026 | Target: Alembic 1.20.1 | Companion to the Alembic 1.20.0 Comprehensive Python Library Capability Overview

## Scope and orientation

This addendum extends the original guide with capabilities, execution semantics, extension mechanisms, and version-specific correctness considerations that were previously omitted or underdeveloped. It assumes familiarity with the original guide's revision graph, migration operations, autogeneration system, batch migrations, and runtime architecture.

Version baseline: Alembic 1.20.1 is the latest stable release verified for this addendum. The upstream changelog dates it October 21, 2026; PyPI records publication on October 22, 2026. Alembic 1.20.2 appears in the upstream changelog without a release date and is not part of the stable capability baseline. Alembic 1.20.x requires Python 3.10+ and SQLAlchemy 2.0+.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



The additions develop five architectural distinctions:

1. Representable versus detectable schema changes: Alembic can execute operations that its autogeneration system cannot independently discover.
2. Abstract DDL versus database-native transitions: SQLAlchemy dialect options and Alembic transaction controls can express specialized database operations without replacing the migration framework.
3. Migration operations versus execution environments: The programmable environment can supply runtime parameters, construct migration contexts, and coordinate revision execution.
4. Structured transformations versus generated source: Schema differences can be represented, modified, rendered, and executed through separable interfaces.
5. Revision correctness versus operational correctness: Schema equivalence, historical upgrade execution, transaction semantics, and physical database behavior require different forms of verification.

## 1. Additional autogeneration limitations and schema normalization

### 1.1 Operation support does not imply automatic change detection

Alembic's autogeneration system has a narrower coverage boundary than the `Operations` API. The following distinctions are particularly consequential.

| Schema construct                         | Native operation or representation                                                 | Autogeneration limitation                                                      |
| ---------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Primary-key constraints                  | `create_primary_key()`, `drop_constraint()`                                        | Some standalone PK additions/removals are not detected                         |
| PostgreSQL exclusion constraints         | `create_exclude_constraint()`, `drop_constraint()`                                 | Standalone EXCLUDE changes are not generally detected                          |
| Standalone sequences                     | SQLAlchemy `Sequence`, DDL constructs, or custom migration operations              | Sequence addition/removal is not implemented in built-in autogeneration        |
| Emulated enums                           | SQLAlchemy `Enum`, often represented through character types and CHECK constraints | Reflected structure may not reveal the original enum intent                    |
| Named CHECK constraints                  | Opt-in name-based comparison                                                       | Same-name expression changes remain invisible                                  |
| Backend-specific constraints and indexes | Dialect-specific SQLAlchemy constructs                                             | Detection depends on the dialect's reflection fidelity and Alembic comparators |

Alembic's official documentation explicitly identifies incomplete detection for standalone primary-key and exclusion constraints, and unavailable detection for standalone sequences. These should be treated as coverage limitations, not universal statements that every change involving these objects is ignored.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



An important architectural consequence follows: a generated migration with no operations is not a general proof that every database object agrees with the intended schema. The comparison proves only that the enabled comparators found no actionable differences among objects they successfully inspected.

Source: [https://alembic.sqlalchemy.org/en/latest/autogenerate.html](https://alembic.sqlalchemy.org/en/latest/autogenerate.html?utm_source=chatgpt.com)

### 1.2 Schema normalization before comparison

Some apparent schema differences arise because database reflection reconstructs a different representation from the original SQLAlchemy metadata.

A database without native enum support, for example, may represent an `Enum` as a character column plus a CHECK constraint. That reflected combination is not uniquely identifiable as an enum: it could have been deliberately modeled as a character column with a constraint.

SQLAlchemy supplies two useful reflection-time extension points:

- `DDLEvents.column_reflect()` can reinterpret or augment a reflected column's metadata before Alembic compares it.
- `DDLEvents.after_parent_attach()` can inspect reflected constraints as they are attached and remove constructs that should not participate in the intended comparison.

These mechanisms can supply domain knowledge that generic reflection cannot recover.

The resulting distinction is between three different extension strategies:

| Strategy                     | Changes                                          | Best-suited problem                                                           |
| ---------------------------- | ------------------------------------------------ | ----------------------------------------------------------------------------- |
| Reflection normalization     | The database-side SQLAlchemy representation      | The database schema is semantically equivalent but reflects differently       |
| Custom comparison            | How reflected and declared objects are evaluated | The objects are represented correctly, but need specialized equivalence rules |
| Custom autogeneration plugin | Which objects and differences are discovered     | A schema-object family is outside standard comparison coverage                |

These approaches are complementary. Normalizing a reflected enum may avoid implementing a specialized comparator; detecting changes to independently managed sequences generally requires additional object discovery and comparison machinery.

The official documentation demonstrates custom sequence autogeneration using metadata annotations, schema-level comparison, and custom `MigrateOperation` directives. This illustrates how the framework can be extended without introducing a separate migration history.

Sources:

[https://alembic.sqlalchemy.org/en/latest/autogenerate.html](https://alembic.sqlalchemy.org/en/latest/autogenerate.html?utm_source=chatgpt.com)

[https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html](https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html?utm_source=chatgpt.com)

### 1.3 Constraint identity and comparison fidelity

The distinction between comparing structural identity and comparing SQL expression equivalence is particularly important for constraints.

Named CHECK autogeneration assumes that matching names identify the same constraint. It does not attempt to prove that the underlying expressions are equivalent.

This is different from comparing ordinary column properties or basic foreign-key structures. SQL expressions can be reformatted, normalized, rewritten, or supplied with implicit casts by a database.

For example, PostgreSQL may reflect:

- An inequality using `<>` rather than `!=`.
- A `BETWEEN` expression as separate lower and upper comparisons.
- An `IN` predicate as an expression involving `ANY` and an array.
- Additional type casts around stored expressions.

Two textually different expressions can therefore be equivalent, while two constraints with identical names can have different semantics.

The built-in name-based CHECK comparator deliberately prioritizes stable identity over expression reconciliation. This makes it useful for detecting named constraint existence, but insufficient as a general CHECK-expression validator.

For systems requiring expression-sensitive comparison, a custom comparator must explicitly define the level of equivalence it promises. Comparing formatted SQL text, parsed expression trees, database-normalized expressions, and actual logical equivalence are different problems.

Source: [https://alembic.sqlalchemy.org/en/latest/autogenerate.html](https://alembic.sqlalchemy.org/en/latest/autogenerate.html?utm_source=chatgpt.com)

## 2. Column-operation semantics and PostgreSQL-native DDL

### 2.1 `add_column()` is not equivalent to creating a complete SQLAlchemy column

`Operations.add_column()` accepts a SQLAlchemy `Column` object but intentionally implements only the properties and constraints that can be expressed through its migration operation.

| `Column` property                                 | `op.add_column()` behavior                              |
| ------------------------------------------------- | ------------------------------------------------------- |
| Name, type, nullable                              | Used to construct the column addition                   |
| `server_default`                                  | Produces a database-side default                        |
| `default`                                         | Python-side default; does not produce database DDL      |
| `unique=True`                                     | Ignored; create the unique constraint separately        |
| `index=True`                                      | Ignored; create the index separately                    |
| `primary_key=True`                                | Does not ordinarily emit an inline PK declaration       |
| `primary_key=True` with `inline_primary_key=True` | Requests an inline PK declaration on supported backends |
| `ForeignKey(...)`                                 | Normally creates a separate constraint statement        |
| `ForeignKey(...)` with `inline_references=True`   | Requests the foreign-key reference within `ADD COLUMN`  |

These behaviors are explicitly documented in Alembic 1.20.1, including the ignored `unique` and `index` flags.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



The independent primary-key controls are deliberate. A column marked `primary_key=True` can influence dialect-specific type behavior without necessarily specifying that a complete primary-key constraint should be generated inline.

Similarly, adding a column with `ForeignKey` and `inline_references=True` is not the same operation as adding the column and subsequently creating a standalone foreign-key constraint. The latter can have different validation and locking behavior.

This matters when automatically converting SQLAlchemy schema declarations into migration operations: a general `Column` is a schema-description object, whereas `add_column()` is a specific database transformation with intentionally narrower semantics.

The `if_not_exists` option changes failure behavior where supported, but does not establish that an existing column has the expected type, nullability, default, or constraints.

Source: [https://alembic.sqlalchemy.org/en/latest/ops.html](https://alembic.sqlalchemy.org/en/latest/ops.html?utm_source=chatgpt.com)

### 2.2 PostgreSQL type conversions through `postgresql_using`

`Operations.alter_column()` supports the PostgreSQL-specific `postgresql_using` keyword argument.

It supplies the SQL expression used by:

```
ALTER TABLE ... ALTER COLUMN ... TYPE ... USING ...
```

This enables Alembic to describe a type alteration and its associated value conversion as one database DDL operation.

An illustrative migration:

```
from alembic import opimport sqlalchemy as safrom sqlalchemy.dialects import postgresqldef upgrade():    op.alter_column(        "events",        "payload",        type_=postgresql.JSONB(),        existing_type=sa.Text(),        postgresql_using="payload::jsonb",    )
```

This relies on every existing `payload` value being convertible to JSONB; invalid values will cause the database operation to fail.

The `postgresql_using` argument is raw SQL, not a SQLAlchemy expression that Alembic automatically quotes or parameterizes. Its identifiers and expressions must be valid for the destination database.

There is also a separate SQLAlchemy PostgreSQL index option named `postgresql_using`, which selects an index access method such as GIN or GiST. The two parameters have the same spelling but completely different meanings.

Architectural significance: The native conversion clause can replace a separately orchestrated sequence of SQL statements where the database supports expressing the transformation within `ALTER TABLE`. It does not eliminate the physical cost of rewriting a table or provide automatic protection against irreversible conversion.

Sources:

[https://alembic.sqlalchemy.org/en/latest/ops.html](https://alembic.sqlalchemy.org/en/latest/ops.html?utm_source=chatgpt.com)

[https://docs.sqlalchemy.org/en/21/dialects/postgresql.html](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html?utm_source=chatgpt.com)

### 2.3 Deferred constraint validation through `postgresql_not_valid`

SQLAlchemy's PostgreSQL dialect supports the `postgresql_not_valid` argument for eligible `CheckConstraint` and `ForeignKeyConstraint` constructs. Alembic passes this option through constraint-creation operations.

For example:

```
op.create_foreign_key(    "fk_orders_customer",    "orders",    "customers",    ["customer_id"],    ["id"],    postgresql_not_valid=True,)
```

This generates a foreign-key addition using PostgreSQL's `NOT VALID` option.

Instead of scanning all existing rows when the constraint is installed, PostgreSQL can defer validation of historical data while enforcing the new constraint against subsequent inserts and updates.

Validation can then occur separately:

```
op.execute(    "ALTER TABLE orders "    "VALIDATE CONSTRAINT fk_orders_customer")
```

The separation is meaningful because the validation step uses a less restrictive lock than the initial full validation typically would. PostgreSQL can validate the pre-existing rows without preventing ordinary concurrent updates.

The behavior has several limits:

- `NOT VALID` is applicable to eligible constraints added through `ALTER TABLE`, not an arbitrary constraint type.
- Existing violations remain possible until validation succeeds.
- Subsequent writes are still subject to the constraint.
- Alembic does not automatically schedule or track deferred validation as an independent lifecycle state.
- The database determines locking and validation behavior.

For large tables, this mechanism can separate constraint enforcement from the potentially expensive verification of historical data. It also permits existing violations to be corrected while preventing new ones from being introduced.

This differs from `inline_references=True`, which controls how a new foreign-key column and its reference are expressed. Deferred validation applies to an independently added constraint and deliberately leaves it unvalidated until a later operation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.1 Documentation+1



Sources:

[https://docs.sqlalchemy.org/en/21/dialects/postgresql.html](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html?utm_source=chatgpt.com)

[https://www.postgresql.org/docs/current/sql-altertable.html](https://www.postgresql.org/docs/current/sql-altertable.html?utm_source=chatgpt.com)

### 2.4 Concurrent PostgreSQL index creation and autocommit

Alembic accepts SQLAlchemy's PostgreSQL-specific index options through `create_index()` and `drop_index()`.

The option `postgresql_concurrently=True` produces PostgreSQL's concurrent index DDL on compatible server versions.

For example:

```
from alembic import opdef upgrade():    with op.get_context().autocommit_block():        op.create_index(            "ix_events_external_id",            "events",            ["external_id"],            postgresql_concurrently=True,        )
```

PostgreSQL does not permit `CREATE INDEX CONCURRENTLY` inside a regular transaction block. Alembic's `autocommit_block()` supplies the relevant execution boundary.

The important interaction is that entering an autocommit block commits the preceding migration transaction. Consequently, the index operation cannot be treated as part of an indivisible transaction containing earlier DDL.

PostgreSQL concurrent index creation also differs substantially from ordinary index creation:

| Property                        | Ordinary index creation                | Concurrent index creation                           |
| ------------------------------- | -------------------------------------- | --------------------------------------------------- |
| PostgreSQL transaction block    | Permitted                              | Not permitted                                       |
| Concurrent table writes         | More restrictive                       | Intended to permit ongoing writes                   |
| Table scans and synchronization | Conventional index build               | Multiple phases and transaction waits               |
| Failure state                   | Transactional rollback where supported | May leave an invalid index                          |
| Execution time                  | Often lower overhead                   | May take longer because of concurrency coordination |

A failed concurrent index build can leave a catalog-visible invalid index. PostgreSQL may continue maintaining such an index on writes even though it is not eligible for normal query planning.

SQLAlchemy 2.1 exposes invalid-index state through reflection, including `postgresql_invalid` within reflected index dialect options. That provides an inspection mechanism, but Alembic does not turn it into an automatic retry or recovery system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.1 Documentation+1



The database also restricts concurrent builds on partitioned tables and concurrent index-build concurrency on a single table.

Sources:

[https://docs.sqlalchemy.org/en/21/dialects/postgresql.html](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html?utm_source=chatgpt.com)

[https://www.postgresql.org/docs/current/sql-createindex.html](https://www.postgresql.org/docs/current/sql-createindex.html?utm_source=chatgpt.com)

### 2.5 Additional PostgreSQL index and constraint options

Alembic's generic index and constraint operations can accept selected dialect-specific arguments that SQLAlchemy understands.

Examples include:

| Option                          | Underlying capability                                              |
| ------------------------------- | ------------------------------------------------------------------ |
| `postgresql_using` on an index  | Select B-tree, GIN, GiST, BRIN, or another supported access method |
| `postgresql_where`              | Partial-index predicate                                            |
| `postgresql_ops`                | Operator classes for indexed columns or expressions                |
| `postgresql_include`            | Covering-index payload columns                                     |
| `postgresql_with`               | Index storage parameters                                           |
| `postgresql_tablespace`         | Index tablespace placement                                         |
| `postgresql_nulls_not_distinct` | PostgreSQL 15+ unique-null semantics                               |
| `postgresql_concurrently`       | Concurrent index creation or removal                               |
| `postgresql_not_valid`          | Deferred CHECK or foreign-key validation                           |

The options belong to SQLAlchemy's PostgreSQL dialect or the database itself; Alembic provides the migration operation and execution context.

Not every dialect option applies to every Alembic operation, and support for emitting DDL is distinct from reliable autogeneration comparison of that option.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.1 Documentation



An especially useful composition is PostgreSQL's ability to create a unique index concurrently and subsequently attach it as a primary-key or unique constraint using `ALTER TABLE ... ADD CONSTRAINT ... USING INDEX`.

The concurrent index operation can be expressed through Alembic's index API. The subsequent attachment may require direct PostgreSQL DDL through `op.execute()`, because the generic `create_primary_key()` operation does not expose every PostgreSQL constraint-attachment form.

This combination can reduce the blocking associated with building a large uniqueness-enforcing index, subject to database-specific restrictions such as column nullability and index compatibility.

Source: [https://www.postgresql.org/docs/current/sql-altertable.html](https://www.postgresql.org/docs/current/sql-altertable.html?utm_source=chatgpt.com)

## 3. Programmable migration environments and configuration

### 3.1 `env.py` is an executable extension boundary

Alembic's migration environment is not merely a configuration file that establishes a database connection.

The `EnvironmentContext` abstraction supplies a programmable boundary between migration commands, the script directory, database connectivity, and execution-specific behavior.

Within `env.py`, the `alembic.context` module is a proxy for the active `EnvironmentContext` instance.

This enables environment logic to customize:

- Connection creation and transaction ownership.
- Migration arguments and backend selection.
- Online versus offline execution.
- Revision-generation hooks and rendering.
- Schema ownership and comparison rules.
- Migration execution callbacks and output streams.

An especially important distinction is that `EnvironmentContext` can be instantiated directly, independently of a top-level `alembic.command` invocation.

The documented mechanism combines `Config`, `ScriptDirectory`, `EnvironmentContext`, and `ScriptDirectory.run_env()`:

```
from alembic.config import Configfrom alembic.script import ScriptDirectoryfrom alembic.runtime.environment import EnvironmentContextconfig = Config()config.set_main_option(    "script_location",    "example_package:migrations",)script = ScriptDirectory.from_config(config)def migration_callback(revision, migration_context):    # Custom revision-selection or inspection logic.    ...with EnvironmentContext(    config,    script,    fn=migration_callback,):    script.run_env()
```

The example is schematic; a functional environment must supply an appropriate callback and configure the database or offline dialect.

`script.run_env()` loads the migration environment. When that environment calls `run_migrations()`, Alembic invokes the callback supplied through `fn`.

This is a lower-level execution interface than `command.upgrade()` or `command.current()`.

It is useful when the surrounding program needs to control the environment lifecycle itself. For ordinary migration execution, Alembic's command functions remain the higher-level abstraction.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



Source: [https://alembic.sqlalchemy.org/en/latest/api/runtime.html](https://alembic.sqlalchemy.org/en/latest/api/runtime.html?utm_source=chatgpt.com)

### 3.2 Runtime arguments passed directly into revisions

`EnvironmentContext.run_migrations(**kw)` forwards keyword arguments to the `upgrade()` and `downgrade()` functions of the selected revision files.

This requires the revision function signatures to accept those arguments. Alembic's `script.py.mako` template can be modified so that newly generated revisions consistently expose them.

For example, a custom migration environment may invoke:

```
context.run_migrations(    engine_name="analytics",)
```

A corresponding custom revision template could define:

```
def upgrade(engine_name: str) -> None:    ...def downgrade(engine_name: str) -> None:    ...
```

The argument becomes part of the execution context rather than the static revision graph.

The mechanism is used by Alembic's multi-database example environment, where one revision file may contain distinct operations for different engines.

It can also convey other execution-specific context, subject to the migration authors defining consistent signatures and behavior.

A consequential limitation is historical reproducibility. If the effect of a revision depends on a runtime argument, the revision identifier alone does not describe which variant was executed.

The argument does not automatically become part of the version table. If that distinction matters, a surrounding system must preserve the relevant execution context separately.

Source: [https://alembic.sqlalchemy.org/en/latest/api/runtime.html](https://alembic.sqlalchemy.org/en/latest/api/runtime.html?utm_source=chatgpt.com)

### 3.3 CLI-supplied environment parameters

Alembic provides two independent command-line argument mechanisms for custom environment logic.

| Mechanism | Accessor                                | Semantics                                                 |
| --------- | --------------------------------------- | --------------------------------------------------------- |
| `-x`      | `EnvironmentContext.get_x_argument()`   | Open-ended user-defined parameters                        |
| `--tag`   | `EnvironmentContext.get_tag_argument()` | One arbitrary tag for environment-specific interpretation |

`get_x_argument(as_dictionary=True)` interprets supplied `key=value` arguments as a dictionary. Without that option, the arguments remain a list.

For example, `alembic -x phase=metadata upgrade head` can convey a phase selector to `env.py`.

These values are not interpreted by Alembic's revision graph. The environment or migration scripts must explicitly define their meaning.

The official cookbook demonstrates conditional migration logic using this mechanism.

There is an important distinction between using CLI arguments as environment selection and using them to change the meaning of a revision. Selecting a database connection generally preserves the revision's intended transformation. Making a revision perform different schema changes depending on a flag can result in databases reporting the same revision while having materially different structures.

Source: [https://alembic.sqlalchemy.org/en/latest/cookbook.html](https://alembic.sqlalchemy.org/en/latest/cookbook.html?utm_source=chatgpt.com)

### 3.4 Revision templates and generation-time arguments

The migration environment also exposes additional controls over how revisions are authored.

`script.py.mako` is a Mako source template from which Alembic constructs new revision files. It can be extended to include custom imports, function signatures, declarations, metadata, and other consistently generated elements.

`EnvironmentContext.configure(template_args=...)` supplies additional template variables during revision generation when the environment participates.

The `revision_environment=True` configuration option causes the environment to run during ordinary revision creation rather than only when autogeneration requires it.

This enables a separation between:

| Mechanism                     | Applies when              | Changes                                               |
| ----------------------------- | ------------------------- | ----------------------------------------------------- |
| `template_args`               | Revision generation       | Values available to the source template               |
| `script.py.mako`              | Revision generation       | Structure and contents of generated Python revisions  |
| `process_revision_directives` | Before revision rendering | Structured migration directives and revision creation |
| `run_migrations(**kw)`        | Migration execution       | Arguments received by revision functions              |
| `-x` / `--tag`                | Command invocation        | Execution environment parameters                      |

These are different stages. Template arguments determine generated source; execution arguments affect the behavior of already-generated revisions.

A customized template does not retroactively change historical migration files, and custom function signatures must remain compatible with the environment that executes those files.

Source: [https://alembic.sqlalchemy.org/en/latest/api/runtime.html](https://alembic.sqlalchemy.org/en/latest/api/runtime.html?utm_source=chatgpt.com)

### 3.5 INI, TOML, and programmatic configuration are not interchangeable

Alembic introduced `pyproject.toml` support in 1.16.0, but several of its configuration APIs intentionally retain different behavior.

`Config` supports `file_` for INI files and `toml_file` for TOML configuration. Either or both can be provided, or a configuration can be constructed entirely through Python.

The key distinctions are:

| Configuration API      | Reads INI             | Reads TOML         | Notable behavior                       |
| ---------------------- | --------------------- | ------------------ | -------------------------------------- |
| `get_main_option()`    | Yes                   | No                 | Uses the active INI section            |
| `get_section_option()` | Yes                   | No                 | Reads a named INI section              |
| `get_alembic_option()` | Yes                   | Yes                | INI takes precedence over TOML         |
| `set_main_option()`    | Programmatic override | No                 | Writes to the INI-backed configuration |
| `toml_alembic_config`  | No                    | Yes                | Exposes TOML `[tool.alembic]` data     |
| `Config.attributes`    | Not a file setting    | Not a file setting | Carries arbitrary Python objects       |

For `get_alembic_option()`, the `-n/--name` selector changes the INI section consulted, but the corresponding TOML section remains `[tool.alembic]`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



The two formats also have different native value representations. INI options are string-oriented, whereas TOML configuration can contain arrays and dictionaries.

This affects configuration consumers that assume a value is always a string.

Programmatic configurations have another important boundary: standard generated environments may attempt to initialize logging through `logging.fileConfig()`. A `Config()` instance constructed without an INI file may not contain the necessary logging sections, so an environment that supports programmatic configuration must account for that.

`Config.attributes` is the appropriate place for passing arbitrary non-string objects such as active connections. Those objects are not equivalent to configuration values serialized in INI or TOML.

Source: [https://alembic.sqlalchemy.org/en/latest/api/config.html](https://alembic.sqlalchemy.org/en/latest/api/config.html?utm_source=chatgpt.com)

## 4. Additional structured-operation and dialect extension APIs

### 4.1 Rendering migration operation trees independently

`alembic.autogenerate.render_python_code()` renders an existing `UpgradeOps` or `DowngradeOps` object into Python migration source.

Unlike `command.revision()`, it does not require writing a new revision file.

A representative use:

```
from alembic.autogenerate import (    produce_migrations,    render_python_code,)migration_script = produce_migrations(    migration_context,    target_metadata,)source = render_python_code(    migration_script.upgrade_ops,    migration_context=migration_context,)
```

This example assumes `migration_context` and `target_metadata` have already been constructed.

The rendering helper also accepts options such as:

- `render_as_batch`, to use batch-operation syntax.
- `render_item`, to customize the representation of individual constructs.
- `imports`, to supply imports for the rendered code.
- `sqlalchemy_module_prefix`, `alembic_module_prefix`, and `user_module_prefix`, to control generated references.

Its role is deliberately narrow: it converts an operation tree into Python text. It does not execute the operations, validate their safety, write the surrounding revision metadata, or advance the version table.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



This makes a useful architectural distinction possible:

| Representation                | What it provides                        | What it does not provide                  |
| ----------------------------- | --------------------------------------- | ----------------------------------------- |
| `compare_metadata()` result   | Difference tuples                       | Full structured migration semantics       |
| `produce_migrations()` result | Structured operations and containers    | A finalized historical revision           |
| `Rewriter`                    | Transformations of operation structures | Database validation of the resulting plan |
| `render_python_code()`        | Python source from operation structures | Migration execution or history updates    |
| `Operations.invoke()`         | Execution of operation directives       | Automatic revision-history lifecycle      |

These mechanisms can support independent inspection and transformation of proposed changes without parsing generated Python code or SQL strings.

When multiple engines participate, the operation model can contain several `UpgradeOps` and `DowngradeOps` collections with separate tokens. Tools consuming that representation must inspect the corresponding lists rather than assuming one upgrade block.

Source: [https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html](https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html?utm_source=chatgpt.com)

### 4.2 The lower-level `DefaultImpl` extension layer

Alembic's public operation plugins provide new migration directives. Below them, `alembic.ddl.impl.DefaultImpl` defines the backend implementation of migration operations.

This distinction is important because different databases may require different sequences of actions to implement the same abstract schema transformation.

Alembic supplies implementations such as `PostgresqlImpl`, `MySQLImpl`, `MSSQLImpl`, and `SQLiteImpl`.

The underlying `DefaultImpl` API exposes functionality including:

| Extension point                     | Responsibility                                                 |
| ----------------------------------- | -------------------------------------------------------------- |
| `compare_type()`                    | Dialect-specific type equivalence                              |
| `compare_server_default()`          | Backend-aware default comparison                               |
| `compare_indexes()`                 | Index comparison using dialect-specific signatures             |
| `compare_unique_constraint()`       | Constraint comparison behavior                                 |
| `autogen_column_reflect()`          | Adjust reflected columns during autogeneration                 |
| `correct_for_autogen_constraints()` | Reconcile reflected constraint/index representations           |
| `requires_recreate_in_batch()`      | Determine when a batch operation requires table reconstruction |
| `cast_for_batch_migrate()`          | Adjust value conversion during batch copying                   |
| `prep_table_for_batch()`            | Prepare backend structures before reconstruction               |
| `render_ddl_sql_expr()`             | Render expressions for DDL contexts                            |
| `render_type()`                     | Control migration-source rendering of particular SQL types     |
| `start_migrations()`                | Initialize implementation state for a migration run            |
| `version_table_impl()`              | Construct a dialect-appropriate Alembic version table          |

For example, SQLite's implementation controls when a requested alteration must become a table recreation. PostgreSQL's batch implementation can prepare constraints before replacing a table so that replacement objects do not conflict with existing constraint names.

MySQL's implementation includes specialized comparison of native ENUM value changes.

SQL Server's implementation accommodates backend-specific behavior such as `IDENTITY INSERT` handling during data insertion.

These behaviors are not simply SQL string formatting. They may alter the operations or preparation required to carry out a migration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



Source: [https://alembic.sqlalchemy.org/en/latest/api/ddl.html](https://alembic.sqlalchemy.org/en/latest/api/ddl.html?utm_source=chatgpt.com)

### 4.3 Choosing the appropriate extension boundary

The extension layers solve different problems.

| Requirement                                          | Relevant abstraction                                     |
| ---------------------------------------------------- | -------------------------------------------------------- |
| Introduce a new migration action                     | `MigrateOperation` and operation registration            |
| Supply execution behavior for that action            | `Operations.implementation_for()`                        |
| Discover a new object type during autogeneration     | Custom autogeneration comparator                         |
| Normalize database reflection                        | SQLAlchemy reflection events or dialect reflection hooks |
| Change generic operation behavior for a backend      | `DefaultImpl` or specialized implementation class        |
| Change generated Python without changing its meaning | Rendering hooks                                          |
| Transform an existing operation plan                 | `Rewriter` or revision directive processing              |
| Change output after Python source is written         | Post-write hooks                                         |

The distinction between custom operations and dialect implementations is especially consequential.

A custom operation can represent something Alembic does not natively model, such as a specialized database object.

A dialect implementation addresses how an existing abstract operation behaves on a particular backend, including differences in DDL sequencing, reflection, or transactional behavior.

The `DefaultImpl` extension surface is more tightly coupled to Alembic's implementation architecture than high-level migration directives. Its usefulness is greatest for specialized dialect integrations or framework-level database support, where overriding low-level behavior avoids duplicating an entire operation stack.

### 4.4 Customizing the Alembic version-table definition

One less obvious `DefaultImpl` hook is `version_table_impl()`.

Added in Alembic 1.14, it allows third-party dialect implementations to supply a different SQLAlchemy `Table` definition for the Alembic version table.

The table must still follow Alembic's essential requirements, including a string-valued `version_num` column.

This is distinct from the public runtime options that merely configure the version table's name, schema, or primary-key behavior.

It can accommodate database-specific table requirements without replacing Alembic's revision tracking. However, it does not make a version table a complete record of execution parameters, data-transform outcomes, or schema drift.

Source: [https://alembic.sqlalchemy.org/en/latest/api/ddl.html](https://alembic.sqlalchemy.org/en/latest/api/ddl.html?utm_source=chatgpt.com)

## 5. Additional execution semantics and backend-specific behavior

### 5.1 `op.execute()` is intentionally a resultless operation

`Operations.execute()` accepts executable SQLAlchemy Core constructs or SQL text, but does not return a database result set.

This design preserves compatibility with Alembic's offline execution mode, in which operations are compiled to SQL text rather than executed against a connection.

For operations requiring database results, online migrations can instead use:

```
connection = op.get_bind()result = connection.execute(statement)
```

Here, `statement` must be an appropriate SQLAlchemy executable.

The distinction is important because the two execution interfaces have different guarantees.

| Interface                 | Online behavior                           | Offline behavior                                   |
| ------------------------- | ----------------------------------------- | -------------------------------------------------- |
| `op.execute()`            | Execute SQL without returning a result    | Emit SQL                                           |
| `op.get_bind().execute()` | Use the active SQLAlchemy connection      | Cannot provide ordinary live query results         |
| `op.inline_literal()`     | Supply an inline-rendered SQL value       | Supply a literal compatible with script generation |
| `op.bulk_insert()`        | Insert rows through the migration context | Render INSERT statements with literal values       |

When `op.execute()` receives a string, Alembic converts it into SQLAlchemy's `text()` construct. Consequently, colon-prefixed expressions may be interpreted as bind parameters. A literal colon may need to be escaped.

SQLAlchemy bind parameters are generally preferable for application queries, but offline migration SQL has no DBAPI execution step in which parameters can be supplied separately.

For that reason, Alembic supports literal rendering. This mechanism is intended for controlled migration content, not arbitrary untrusted runtime input.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



Source: [https://alembic.sqlalchemy.org/en/latest/ops.html](https://alembic.sqlalchemy.org/en/latest/ops.html?utm_source=chatgpt.com)

### 5.2 `bulk_insert(multiinsert=False)` and literal rendering

`Operations.bulk_insert()` normally uses an executemany-style approach in online mode when inserting multiple rows.

However, when individual values are constructed with `op.inline_literal()`, Alembic documents `multiinsert=False` as the compatible execution form.

That setting causes individual INSERT statements to be issued, allowing the literal expressions to be rendered correctly instead of being passed as ordinary bound parameters.

The tradeoff is between efficient parameterized batch execution and the ability to emit special literal expressions consistently across online and offline environments.

For small seed-data migrations, this difference may be insignificant. For large data transfers, individual inserts can be substantially less attractive than database-native bulk operations or set-oriented SQL.

The `multiinsert` setting does not turn Alembic into a generalized high-throughput data-loading framework. Its role is to make migration-oriented insertion work correctly under different SQL rendering modes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



Source: [https://alembic.sqlalchemy.org/en/latest/ops.html](https://alembic.sqlalchemy.org/en/latest/ops.html?utm_source=chatgpt.com)

### 5.3 Raw offline output versus executable migration SQL

`EnvironmentContext.static_output(text)` writes literal text to Alembic's offline SQL output stream.

Unlike an ordinary SQL operation, this text is not treated as a DDL statement. Alembic does not automatically add statement terminators or backend batch separators.

This can be used to emit comments, explanatory markers, or other script content that should remain outside SQL compilation.

It provides a different layer of control from `op.execute()`, which submits an operation to the active migration context for execution or compilation.

Offline output also has backend-specific formatting controls:

| Option                   | Default             | Purpose                                                  |
| ------------------------ | ------------------- | -------------------------------------------------------- |
| `mssql_batch_separator`  | `GO`                | Separate SQL Server command batches                      |
| `oracle_batch_separator` | `/`                 | Separate Oracle script execution units                   |
| `output_buffer`          | Configurable        | Control the destination text stream                      |
| `literal_binds`          | Disabled by default | Attempt automatic literal rendering                      |
| `starting_rev`           | Configurable        | Specify the assumed starting revision for SQL generation |

Batch separators are significant because they are conventions used by SQL execution clients, not simply additional SQL statement terminators.

For example, SQL Server's `GO` is recognized by client tooling and script processors rather than being ordinary T-SQL sent directly to the server.

The emitted SQL therefore has a consumer-side execution contract. A program that executes it must correctly handle the relevant dialect's batch conventions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation+1



Source: [https://alembic.sqlalchemy.org/en/latest/api/runtime.html](https://alembic.sqlalchemy.org/en/latest/api/runtime.html?utm_source=chatgpt.com)

### 5.4 Per-revision execution callbacks and transaction visibility

The `on_version_apply` hook receives one callback invocation for each migration step after that step's operations have executed, but before the surrounding transaction is finalized.

The callback receives keyword arguments including:

| Argument   | Meaning                                            |
| ---------- | -------------------------------------------------- |
| `ctx`      | Active `MigrationContext`                          |
| `step`     | `MigrationInfo` describing the revision transition |
| `heads`    | Current revision frontier                          |
| `run_args` | Keyword arguments supplied to `run_migrations()`   |

The hook provides an instrumentation point that avoids modifying individual revision files.

Potential uses include migration progress reporting, recording revision transitions, and associating execution diagnostics with specific migration steps.

However, a successful callback invocation does not prove that the encompassing transaction eventually committed.

A later migration step or transaction failure can still cause rollback, subject to the database's transactional behavior.

For diagnostics recorded through the same database transaction, rollback can also remove the diagnostic records. For externally emitted telemetry, a recorded event may survive even when the database transaction does not.

This distinction matters when interpreting migration audit records.

The callback is an execution-observation interface, not a transactional outbox or a distributed commit protocol.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



Source: [https://alembic.sqlalchemy.org/en/latest/api/runtime.html](https://alembic.sqlalchemy.org/en/latest/api/runtime.html?utm_source=chatgpt.com)

### 5.5 SQL Server constraint removal and identity behavior

SQL Server associates some column properties with separately named constraint objects. The names may not be known to a migration author.

Alembic provides special options for `drop_column()`:

| Option                        | SQL Server-specific behavior                                               |
| ----------------------------- | -------------------------------------------------------------------------- |
| `mssql_drop_check=True`       | Discover and remove a CHECK constraint before dropping the column          |
| `mssql_drop_default=True`     | Discover and remove the column's DEFAULT constraint                        |
| `mssql_drop_foreign_key=True` | Discover and remove a single foreign-key constraint referencing the column |

These options construct dynamic SQL using SQL Server system catalogs and then remove the identified constraint.

The `mssql_drop_foreign_key` option is documented as supporting a column with exactly one such foreign-key constraint. It is not a general-purpose dependency resolver for arbitrary multi-constraint configurations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



SQL Server also requires special handling for certain inserts into identity columns. Alembic's `MSSQLImpl` participates in generating the necessary `IDENTITY INSERT` behavior around relevant bulk insertion operations.

These capabilities illustrate that dialect-aware migration execution can involve inspection, preparatory statements, or changes to the operation sequence rather than only translating SQL syntax.

Sources:

[https://alembic.sqlalchemy.org/en/latest/ops.html](https://alembic.sqlalchemy.org/en/latest/ops.html?utm_source=chatgpt.com)

[https://alembic.sqlalchemy.org/en/latest/api/ddl.html](https://alembic.sqlalchemy.org/en/latest/api/ddl.html?utm_source=chatgpt.com)

## 6. Historical migration testing and verification

### 6.1 Schema-state checks and migration-history tests answer different questions

Alembic's native commands can assess detectable schema differences and whether the database has reached the expected revision heads.

They do not, by themselves, establish that every historical upgrade executes successfully from an empty schema or that downgrades have the intended behavior.

The third-party `pytest-alembic` project supplies tests designed for these additional questions.

| Test                               | What it establishes                                                                                                      |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `test_upgrade`                     | The revision history can execute forward from base to head                                                               |
| `test_up_down_consistency`         | Downgrade execution succeeds across the tested history                                                                   |
| `test_model_definitions_match_ddl` | Applying the history produces schema DDL consistent with the declared models, within autogeneration's detection coverage |
| `test_single_head_revision`        | The revision history has one head                                                                                        |

The package integrates with pytest and permits migration-specific tests and configuration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-alembic.readthedocs.io\&sz=32)

Pytest Alembic 0.13.2 documentation



These are companion-library capabilities, not features built into Alembic itself.

There are two important qualifications.

First, `test_single_head_revision` assumes a deliberately linearized migration history. Alembic supports valid multiple-head and multiple-base topologies, so one head is not a universal requirement.

Second, successfully exercising migrations does not prove that all possible production data states are compatible. A migration that succeeds on an empty database may fail when existing rows violate a newly introduced constraint or conversion assumption.

Source: [https://pytest-alembic.readthedocs.io/en/latest/quickstart.html](https://pytest-alembic.readthedocs.io/en/latest/quickstart.html?utm_source=chatgpt.com)

### 6.2 Optional tests and stronger validation semantics

`pytest-alembic` also documents additional experimental checks, including `downgrade_leaves_no_trace` and `all_models_register_on_metadata`.

The former is stricter than simply verifying that downgrade functions execute: it examines whether an upgrade followed by downgrade leaves the database schema in an equivalent state according to the available comparison machinery.

The latter addresses a separate source of autogeneration errors: model definitions may exist in Python code but never be imported into the metadata supplied to Alembic.

These experimental tests should not be treated as having the same stability guarantees as the package's standard built-in checks.

The larger distinction is between three categories of correctness:

| Category                       | Question                                                                                                        |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| Revision-graph correctness     | Is the dependency history coherent and executable in the expected order?                                        |
| Schema correctness             | Does the resulting database structure agree with the target description?                                        |
| Data and execution correctness | Do the migrations preserve required data invariants and operate correctly on relevant existing database states? |

Alembic and its testing extensions provide machinery for evaluating parts of each category, but none makes the other categories automatic.

A downgrade can be executable without being lossless, and a schema comparison can succeed while omitting database objects outside its supported detection scope.

Sources:

[https://pytest-alembic.readthedocs.io/en/latest/](https://pytest-alembic.readthedocs.io/en/latest/?utm_source=chatgpt.com)

[https://alembic.sqlalchemy.org/en/latest/autogenerate.html](https://alembic.sqlalchemy.org/en/latest/autogenerate.html?utm_source=chatgpt.com)

## 7. SQLAlchemy 2.1 integration: additional schema DDL and lifecycle semantics

Alembic 1.20.1 supports both SQLAlchemy 2.0 and SQLAlchemy 2.1. However, the versions expose materially different SQLAlchemy schema capabilities.

These changes do not introduce new Alembic revision-management abstractions, but they affect the database objects and SQL constructs available to migration authors.

### 7.1 Native `CREATE VIEW` and `CREATE TABLE AS SELECT`

SQLAlchemy 2.1 introduces the following DDL constructs:

| SQLAlchemy capability | Purpose                                                          |
| --------------------- | ---------------------------------------------------------------- |
| `CreateView`          | Construct a database view from a SQLAlchemy SELECT               |
| `CreateTableAs`       | Construct a table from the results of a SELECT                   |
| `SelectBase.into()`   | Express a table-creation operation from a SELECT                 |
| `CreateView.table`    | Expose a generated SQLAlchemy `Table` representation of the view |
| `CreateTableAs.table` | Expose the resulting table's generated schema representation     |

The constructs use SQLAlchemy's SQL compilation and dialect infrastructure rather than requiring every definition to be expressed through handwritten SQL strings.

They can participate in direct DDL execution and, where supported, SQLAlchemy's `MetaData.create_all()` lifecycle.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.1 Documentation



This changes the integration boundary for Alembic migrations that create views or tables from queries.

Previously, such operations frequently required raw SQL or custom DDL objects. SQLAlchemy 2.1 now supplies more of that SQL-generation machinery natively.

However, the following distinctions remain:

- SQLAlchemy's `CreateView` can construct and execute a view definition.
- Alembic's operation system can execute suitable SQLAlchemy DDL constructs.
- Alembic does not consequently gain general built-in view-change detection, replaceable-object history, or automatic view-definition comparison.
- Third-party extensions and custom autogeneration comparators remain relevant for declarative version management of such objects.

In particular, a view's SELECT definition may need specialized comparison or replacement semantics even though its initial creation can be represented through SQLAlchemy Core.

Sources:

[https://docs.sqlalchemy.org/en/21/changelog/migration_21.html](https://docs.sqlalchemy.org/en/21/changelog/migration_21.html?utm_source=chatgpt.com)

[https://docs.sqlalchemy.org/en/21/core/metadata.html](https://docs.sqlalchemy.org/en/21/core/metadata.html?utm_source=chatgpt.com)

### 7.2 PostgreSQL named-type lifecycle changes

SQLAlchemy 2.1 changes its treatment of database-native named types, especially PostgreSQL `ENUM` and `DOMAIN`.

These types are more strongly associated with `MetaData` rather than with an individual `Table`.

Consequential changes include:

| Behavior                    | SQLAlchemy 2.1 semantics                               |
| --------------------------- | ------------------------------------------------------ |
| Named-type ownership        | Associated more directly with `MetaData`               |
| Default schema              | Inherits the `MetaData` schema by default              |
| `Table.drop()`              | Does not automatically drop shared named types         |
| `MetaData.drop_all()`       | Drops named types after their dependent tables         |
| `SchemaType.inherit_schema` | Deprecated                                             |
| `CheckFirst`                | Adds finer control over schema-object existence checks |

These changes better represent the database's ownership model for named types that can be shared across multiple tables.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.sqlalchemy.org\&sz=32)

SQLAlchemy 2.1 Documentation



They also affect migration generation and historical stability.

A PostgreSQL enum may be a separate database schema object even when its use is expressed through a SQLAlchemy column type. Dropping a column or table does not necessarily imply that the enum itself should be removed.

Similarly, a change in SQLAlchemy's default schema-inheritance behavior can affect the schema qualification of generated DDL.

The Alembic 1.20.1 fix for PostgreSQL `DOMAIN` rendering, described below, is particularly relevant because it improves how these richer type definitions are reproduced in generated migration source.

Source: [https://docs.sqlalchemy.org/en/21/changelog/migration_21.html](https://docs.sqlalchemy.org/en/21/changelog/migration_21.html?utm_source=chatgpt.com)

### 7.3 Computed-column persistence semantics

SQLAlchemy 2.1 also changes its PostgreSQL computed-column compilation behavior in response to PostgreSQL 18.

PostgreSQL 18 introduced virtual computed columns and made `VIRTUAL` the default when a persistence form is not explicitly specified.

SQLAlchemy 2.1 reflects this behavior: an unspecified `Computed.persisted` does not necessarily imply the same generated DDL across PostgreSQL versions.

To express a stored computed column explicitly, SQLAlchemy supports `Computed(..., persisted=True)`.

This distinction matters for migrations because virtual and stored generated columns have different physical storage and computation behavior.

It is not merely a textual variation in the generated SQL. An implicit default that changes with server version can alter the resulting database object.

Source: [https://docs.sqlalchemy.org/en/21/changelog/migration_21.html](https://docs.sqlalchemy.org/en/21/changelog/migration_21.html?utm_source=chatgpt.com)

## 8. Alembic 1.20.1 corrections and unreleased 1.20.2 behavior

### 8.1 Released 1.20.1 fixes

Alembic 1.20.1 is predominantly a correctness release. Several changes directly affect functionality covered in the original guide.

| Area                                            | Behavior corrected in 1.20.1                                                                                                                                 | Engineering significance                                  |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------- |
| Empty comments                                  | Empty-string table and column comments are compared as equivalent to no stored comment on databases that do not preserve the distinction                     | Avoids persistent false-positive migrations               |
| PostgreSQL `DOMAIN`                             | Autogenerated source retains `check`, `not_null`, `default`, `collation`, `constraint_name`, `schema`, `create_type`, and properly rendered underlying types | Prevents loss of important type-definition properties     |
| PostgreSQL computed columns                     | Reflection-added casts such as `::regconfig` or `::text` no longer cause certain false-positive comparison warnings                                          | Improves comparison reliability for generated expressions |
| PostgreSQL expression indexes                   | More forms of casts, nested casts, and ordering modifiers are correctly handled during index comparison                                                      | Reduces spurious index recreation                         |
| PostgreSQL identity columns                     | Fixes invalid or incomplete `ALTER COLUMN` DDL in cases where `existing_server_default` was omitted                                                          | Corrects migration execution behavior                     |
| Plugin entry points                             | Module-valued `alembic.plugins` entry points now load correctly                                                                                              | Restores documented plugin distribution behavior          |
| Dialect-specific constraint arguments           | Additional constraint options survive autogeneration rendering                                                                                               | Preserves vendor-specific DDL semantics                   |
| SQLAlchemy 2.1 type-generated CHECK constraints | Prevents duplicate explicit CHECK constraints during table autogeneration                                                                                    | Avoids invalid migration output                           |
| `CreateTableOp.from_table()`                    | Prevents duplicate type-generated CHECK constraints when directly invoking derived create-table operations                                                   | Improves structured-operation execution fidelity          |

All of these changes are described in the released 1.20.1 changelog.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



Source: [https://alembic.sqlalchemy.org/en/latest/changelog.html](https://alembic.sqlalchemy.org/en/latest/changelog.html?utm_source=chatgpt.com)

### 8.2 Plugin entry-point compatibility

The 1.20.1 plugin-loading correction merits a specific compatibility note.

The formal Alembic plugin framework supports Python package entry points under `alembic.plugins`.

Before 1.20.1, a third-party entry point referring directly to a plugin module, as documented by Alembic, could cause `import alembic` to fail with a `TypeError`.

Version 1.20.1 corrects this behavior.

An entry point referring to a collection of modules remains accepted for compatibility, but now emits a deprecation warning.

The distinction is between the introduction of a plugin registration API in 1.18.0 and the later correction of a particular plugin distribution/loading mechanism. A plugin author targeting 1.20.0 cannot assume that every entry-point form documented for the plugin framework works correctly in that release.

Source: [https://alembic.sqlalchemy.org/en/latest/changelog.html](https://alembic.sqlalchemy.org/en/latest/changelog.html?utm_source=chatgpt.com)

### 8.3 Constraint argument preservation requires compatible SQLAlchemy versions

The 1.20.1 fixes to constraint rendering have an important dependency boundary.

Alembic now preserves dialect-specific arguments on constraints that participate in certain autogenerated operations, including arguments such as `postgresql_not_valid`.

However, preservation of those arguments in autogenerated `op.create_table()` directives additionally requires one of:

- SQLAlchemy 2.0.55 or later in the 2.0 series.
- SQLAlchemy 2.1.5 or later in the 2.1 series.

Earlier SQLAlchemy releases could lose these arguments while copying `Table` structures, independently of Alembic's own rendering logic.

This is an example of a capability whose effective availability depends on both the migration library and its underlying schema library.

The declared minimum SQLAlchemy requirement of Alembic 1.20.1 does not guarantee the corrected `create_table()` behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



Source: [https://alembic.sqlalchemy.org/en/latest/changelog.html](https://alembic.sqlalchemy.org/en/latest/changelog.html?utm_source=chatgpt.com)

### 8.4 Unreleased 1.20.2 fix: expression indexes during batch recreation

Not released in 1.20.1

The upstream changelog contains a pending 1.20.2 correction for expression indexes created inside `Operations.batch_alter_table()`.

Under the affected behavior, an index creation directive containing expressions such as:

```
func.lower(column("name"))
```

or an ordering expression such as:

```
column("name").desc()
```

could lose the expression when batch reconstruction recreated the table.

Instead of preserving the requested expression, Alembic could create the index against the plain column names.

A `text()` expression could instead result in a `KeyError`.

This is more serious than a cosmetic source-rendering problem: the resulting database may contain an index with different semantics from the requested operation.

The documented pending fix preserves the complete expressions of indexes created within the batch operation, in the same way that existing indexes are preserved during reconstruction.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://alembic.sqlalchemy.org\&sz=32)

Alembic 1.20.1 documentation



The distinction concerns specifically the interaction of newly created expression indexes with batch table recreation. It does not establish that all expression-index operations are affected.

As of November 1, 2026, the upstream changelog lists the fix under version 1.20.2 without a release date. It should therefore be treated as a development-branch correction, not functionality guaranteed by Alembic 1.20.1.

Source: [https://alembic.sqlalchemy.org/en/latest/changelog.html](https://alembic.sqlalchemy.org/en/latest/changelog.html?utm_source=chatgpt.com)

## 9. Capability and version boundaries

The additions above highlight several boundaries worth preserving when evaluating or extending Alembic.

| Responsibility                            | Native provider                                   | Important boundary                                                              |
| ----------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------- |
| Revision ordering and state               | Alembic                                           | Does not capture every execution parameter or physical schema property          |
| Candidate migration discovery             | Alembic autogeneration                            | Limited to enabled comparators and reflected objects                            |
| Schema representation and SQL compilation | SQLAlchemy                                        | Dependent on SQLAlchemy version and backend dialect                             |
| PostgreSQL concurrency and validation     | PostgreSQL engine                                 | Database-native locks, scans, transaction rules, and failure states             |
| Custom object autogeneration              | Alembic extension system plus optional extensions | Requires explicit discovery, comparison, operations, and rendering              |
| Dialect-specific operation semantics      | Alembic `DefaultImpl` and SQLAlchemy dialects     | Lower-level behavior may differ even for identical abstract operations          |
| Historical migration testing              | Alembic APIs and optional testing packages        | Execution success is not proof of lossless or production-safe transitions       |
| Structured migration inspection           | Alembic operation model                           | Rendering or inspecting directives does not by itself create a tracked revision |

A final version distinction is relevant to the combined stack: Alembic 1.20.1 supports Python 3.10 with SQLAlchemy 2.0, whereas SQLAlchemy 2.1 requires Python 3.11 or later. Features specifically introduced in SQLAlchemy 2.1 consequently have that narrower Python compatibility boundary.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



The central architectural opportunity is that Alembic can use its existing revision machinery while delegating specialized schema behavior to SQLAlchemy's dialects and the underlying database, and while exposing structured hooks for independently inspecting, transforming, rendering, and testing migrations.

The corresponding limitation is that those layers have separate guarantees. A valid revision graph, a successfully compiled operation, an accurate metadata comparison, and a safe physical database transition are related but non-equivalent properties.

This addendum completes the identified capability gaps without changing the original guide's foundational conceptual model.