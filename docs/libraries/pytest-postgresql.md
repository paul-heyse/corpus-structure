# pytest-postgresql — Comprehensive Python Library Overview

Version 9.1.1 · Released October 4, 2026 · Research verified October 29, 2026

Package: `pytest-postgresql`\
Import namespace: `pytest_postgresql`\
Category: PostgreSQL integration testing, pytest fixtures, database lifecycle management\
Requirements: Python ≥3.10, pytest ≥8.2, psycopg 3; PostgreSQL ≥14 is the documented tested range\
License: LGPL-3.0-or-later

Primary sources:

- Repository: [https://github.com/dbfixtures/pytest-postgresql](https://github.com/dbfixtures/pytest-postgresql?utm_source=chatgpt.com)
- Package: [https://pypi.org/project/pytest-postgresql/](https://pypi.org/project/pytest-postgresql/?utm_source=chatgpt.com)
- Release history: [https://github.com/dbfixtures/pytest-postgresql/blob/main/CHANGES.rst](https://github.com/dbfixtures/pytest-postgresql/blob/main/CHANGES.rst?utm_source=chatgpt.com)

Version 9.1.1 is the latest published stable release as of the research date. The 9.0 series introduced substantial capabilities, particularly asynchronous fixtures, configurable maintenance databases, and SQL-loader autocommit support.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2



## 1. Architectural orientation

`pytest-postgresql` is a pytest plugin for testing applications against real PostgreSQL databases, with automated provisioning, reusable initialized database templates, per-test isolation, and deterministic cleanup.

Its most important architectural distinction is the separation of three responsibilities:

1. Server lifecycle: Start an isolated PostgreSQL instance or connect to an externally managed server.
2. Database state lifecycle: Create and populate reusable template databases, clone them for tests, and remove transient databases.
3. Client lifecycle: Expose synchronous or asynchronous database connections through pytest fixtures while retaining independent control over database state.

This separation allows a single PostgreSQL server to support many independently initialized tests without restarting the server or replaying all initialization steps for every test.

### 1.1 Capability map

| Capability family         | Principal mechanisms                                                | Architectural significance                                                                    |
| ------------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| PostgreSQL provisioning   | `postgresql_proc`, `postgresql_noproc`                              | Separates managed server processes from externally provisioned PostgreSQL                     |
| Test isolation            | Template databases, database cloning, `DatabaseJanitor`             | Recreates database state rather than relying exclusively on transaction rollback              |
| Initialization            | SQL-file loaders, callable loaders, session-level prepopulation     | Amortizes expensive schema and data initialization                                            |
| Layered state             | `postgresql_noproc(depends_on=...)`                                 | Composes reusable database templates into progressively enriched states                       |
| Client access             | `postgresql`, `postgresql_async`                                    | Provides native psycopg 3 connections for synchronous and asynchronous tests                  |
| Lifecycle extension       | `DatabaseJanitor`, `AsyncDatabaseJanitor`                           | Supports custom database management outside the standard fixture hierarchy                    |
| Parallel testing          | `pytest-xdist` coordination, port allocation, worker-specific names | Enables parallel execution with separated infrastructure and database identities              |
| Environment configuration | Factory parameters, pytest CLI, pytest configuration                | Allows database behavior to vary without modifying test implementations                       |
| Ecosystem integration     | psycopg, SQLAlchemy, Alembic, Docker, CI-managed PostgreSQL         | Supplies PostgreSQL infrastructure while leaving higher-level database interfaces independent |

The central value is database-state reproducibility with amortized initialization cost. The library can substitute for substantial custom machinery that would otherwise initialize PostgreSQL, execute schema setup, establish connections, reset databases, and coordinate fixture cleanup.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



## 2. Fixture architecture and database lifecycle

### 2.1 Four built-in fixtures

| Fixture             | Scope    | Return type               | Responsibility                                                              |
| ------------------- | -------- | ------------------------- | --------------------------------------------------------------------------- |
| `postgresql_proc`   | Session  | `PostgreSQLExecutor`      | Initialize, start, supervise, and stop a local PostgreSQL server            |
| `postgresql_noproc` | Session  | `NoopExecutor`            | Represent an existing PostgreSQL server and manage test databases within it |
| `postgresql`        | Function | `psycopg.Connection`      | Create an isolated database, connect, and clean up after the test           |
| `postgresql_async`  | Function | `psycopg.AsyncConnection` | Asynchronous equivalent of `postgresql`                                     |

The default `postgresql` and `postgresql_async` fixtures depend on `postgresql_proc`. To use an external server, a client fixture must instead reference `postgresql_noproc` or a custom process fixture.

The distinction between an executor and a client is important: the executor represents database infrastructure; the client represents a transient test database and connection. An executor does not itself supply the application-facing database session.

Source: [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/plugin.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/plugin.py?utm_source=chatgpt.com)

### 2.2 Exact lifecycle: template initialization and cloning

The standard fixture arrangement performs the following operations:

SESSION-SCOPED INITIALIZATION

PostgreSQL server

Managed process or existing server

Template database: `tests_tmpl`

Schema, extensions, reference data, initialized state

REPEATED FOR EACH TEST

Test A

Clone → connect → execute → drop

Test B

Fresh clone → connect → execute → drop

Tests receive independent database states; the initialized template remains available throughout the session.

The default database is `tests`; the corresponding template is `tests_tmpl`.

Session setup

1. Provision a PostgreSQL server or resolve an existing server.
2. Create a database named `<dbname>_tmpl`, marking it as a PostgreSQL template with `IS_TEMPLATE = true`.
3. Execute configured initialization loaders against the template.
4. Retain the template for subsequent client fixtures.

Per-test execution

1. Create the test database using PostgreSQL's `CREATE DATABASE ... TEMPLATE ...` mechanism.
2. Establish a psycopg connection to the new database.
3. Yield the connection to pytest.
4. Close the connection during fixture teardown.
5. Prevent new database connections, terminate remaining backends, and drop the test database.

The template is removed when its session-scoped fixture tears down. In managed-process mode, the PostgreSQL server and associated temporary resources are also removed.

A consequential property is that test isolation is database-level, rather than merely transaction-level. Changes committed during one test, including most schema modifications, do not become the initial state of the next test.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



### 2.3 Server executors and exposed connection information

Both executor classes provide an interface useful for custom fixtures and integrations:

| Member                | Meaning                                     |
| --------------------- | ------------------------------------------- |
| `.host`, `.port`      | Server connection endpoint                  |
| `.user`, `.password`  | PostgreSQL authentication                   |
| `.dbname`             | Base test database name                     |
| `.template_dbname`    | Derived template database name              |
| `.maintenance_dbname` | Database used for administrative operations |
| `.options`            | PostgreSQL client connection options        |
| `.version`            | PostgreSQL server version                   |

`PostgreSQLExecutor` additionally exposes managed-process details such as `.datadir`, `.logfile`, `.unixsocketdir`, and process start/stop functionality. `NoopExecutor` supplies connection metadata without controlling the underlying server.

The interface enables other fixtures to construct connections, connection strings, SQLAlchemy engines, and process-dependent resources without needing to own PostgreSQL startup.

Source: [https://github.com/dbfixtures/pytest-postgresql/tree/v9.1.1/pytest_postgresql/executors](https://github.com/dbfixtures/pytest-postgresql/tree/v9.1.1/pytest_postgresql/executors?utm_source=chatgpt.com)

## 3. Server provisioning and execution modes

### 3.1 Managed PostgreSQL: `postgresql_proc`

`factories.postgresql_proc(...)` creates a session-scoped pytest fixture wrapping a managed `PostgreSQLExecutor`.

Its lifecycle includes:

- Executable discovery: Resolve the PostgreSQL `pg_ctl` binary.
- Version enforcement: Reject PostgreSQL versions older than 14.
- Port allocation: Select and reserve an available TCP port.
- Cluster initialization: Create a temporary PostgreSQL data directory through `pg_ctl initdb`.
- Authentication initialization: Configure the initial superuser and optional password.
- Process readiness: Start PostgreSQL through `pg_ctl` and use `mirakuru` for readiness and process coordination.
- Cleanup: Drop the template, stop PostgreSQL, and remove temporary data, logs, and port-reservation files.

Managed mode is useful when test behavior benefits from control over PostgreSQL startup parameters, process lifetime, server version, and a dedicated database cluster.

Important operational distinctions

`startparams` controls `pg_ctl` invocation arguments, while `postgres_options` supplies parameters for the underlying `postgres` executable. They are different from `options`, which configures client connection behavior.

The executor starts PostgreSQL with `-F` (disabling `fsync`) and disables the logging collector. These are testing-oriented defaults; the managed instance is not automatically representative of production durability or logging behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org



The implementation initializes PostgreSQL with `--auth=trust` when no password is supplied. When a password is provided, it uses password authentication and a temporary password file during initialization. This makes the network exposure and operating-system permissions of a managed fixture relevant to test-environment security.

### 3.2 External PostgreSQL: `postgresql_noproc`

`factories.postgresql_noproc(...)` does not launch or stop PostgreSQL. Instead, it creates a session-scoped fixture that connects to an existing server and manages its test-template lifecycle.

Supported server arrangements include a local PostgreSQL service, a Docker or Docker Compose container, a Kubernetes-managed instance, or a database supplied by a CI environment.

What `noproc` does not mean: It is not a read-only connector or a passive connection fixture. The implementation still creates, loads, clones, and drops databases on the external server.

This requires permissions for database creation and deletion, and potentially permissions to terminate active connections. PostgreSQL normally requires the `CREATEDB` role attribute or superuser privileges for `CREATE DATABASE`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org



The external server defaults to `127.0.0.1:5432`, but host, port, user, password, maintenance database, and initialization behavior can be overridden.

### 3.3 Managed versus external execution

| Dimension                                    | `postgresql_proc`                       | `postgresql_noproc`                             |
| -------------------------------------------- | --------------------------------------- | ----------------------------------------------- |
| Server started by plugin                     | Yes                                     | No                                              |
| Requires local `pg_ctl`                      | Yes                                     | No                                              |
| Owns PostgreSQL data directory               | Yes                                     | No                                              |
| Creates and drops test templates             | Yes                                     | Yes                                             |
| Supports schema/data prepopulation           | Yes                                     | Yes                                             |
| Supports template layering with `depends_on` | Can be a base                           | Implements layering                             |
| PostgreSQL configuration control             | Server startup and client configuration | Client configuration; server managed separately |
| Isolation from unrelated databases           | Dedicated cluster                       | Shared cluster unless externally isolated       |

The choice is not simply local versus remote. It determines which component owns the PostgreSQL process, startup configuration, privileges, and lifetime.

Source: [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/factories/noprocess.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/factories/noprocess.py?utm_source=chatgpt.com)

## 4. Database initialization and reusable state

### 4.1 Session-level template population

Both process factories support `load`, a sequence of initialization operations executed against the template database.

| Loader form              | Mechanism                             | Important distinction                                                                   |
| ------------------------ | ------------------------------------- | --------------------------------------------------------------------------------------- |
| `pathlib.Path` to `.sql` | Execute SQL file through psycopg      | Direct SQL initialization                                                               |
| Import string            | Resolve and invoke a Python function  | External initialization logic without importing it directly into the fixture definition |
| Callable                 | Invoke Python initialization function | Arbitrary initialization, including ORM or migration-tool interactions                  |

Import strings support dotted or colon-style references, such as `package.module:load_database`.

A loader receives keyword arguments for `host`, `port`, `user`, `dbname`, `password`, and, in version 9, `autocommit`.

The loader may create a connection itself, execute migrations, populate reference records, install compatible extensions, or run arbitrary initialization logic.

The plugin's SQL loader reads a file and executes its contents using psycopg. It is not a `psql` shell-script interpreter; `psql`-specific metacommands and specialized import workflows need separate handling.

Source: [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/loader.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/loader.py?utm_source=chatgpt.com)

### 4.2 Why template initialization matters

The amortization mechanism is straightforward:

| Repeated setup                       | Template-based setup             |
| ------------------------------------ | -------------------------------- |
| Start with an uninitialized database | Initialize a database once       |
| Recreate schema for each test        | Clone populated schema           |
| Re-run common migrations             | Inherit initialized schema state |
| Reinsert shared reference data       | Clone populated reference data   |
| Reconfigure database objects         | Inherit database-local objects   |

This is particularly useful when the initial state requires complex DDL, migrations, indexes, extensions, or a substantial reference dataset.

The performance benefit depends on the relative costs of initialization and PostgreSQL database cloning. A physical database clone is not free, particularly when the template contains significant data.

### 4.3 Per-test initialization versus session initialization

The library deliberately distinguishes reusable initial state from test-specific state.

Session-level initialization: Define `load` on a process fixture. Data is initialized once and subsequently cloned.

Per-test initialization: Compose an intermediary pytest fixture on top of `postgresql` or `postgresql_async`. It operates on the already cloned database before the test consumes that fixture.

This division avoids unnecessarily rebuilding common state while preserving the ability to create different test-specific datasets.

The `load` parameter is no longer supported on client fixture factories; that capability was removed in version 7.0 in favor of process-level initialization and pytest fixture composition.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 4.4 SQL-loader autocommit

Version 9.0 added explicit control over SQL-loader transaction behavior.

Available configuration surfaces include `load_autocommit` on process factories, `postgresql_load_autocommit` in pytest configuration, and `--postgresql-load-autocommit` on the command line.

This matters for SQL statements that cannot run inside a transaction block, including `CREATE DATABASE`.

The setting affects the loader connection, not the normal client fixture's transaction behavior or the janitor's administrative cursor. Administrative database creation and deletion already require autocommit.

An additional tradeoff is that autocommit changes initialization failure semantics: earlier statements may persist even if a later statement fails, rather than all changes being rolled back together.

Sources:

[https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/loader.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/loader.py?utm_source=chatgpt.com)

[https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/CHANGES.rst](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/CHANGES.rst?utm_source=chatgpt.com)

## 5. Advanced capability: hierarchical database templates

Introduced in version 8.0

One of the library's more distinctive features is template inheritance across fixtures.

The `depends_on` argument to `factories.postgresql_noproc(...)` allows a new template to be cloned from another fixture's template and then extended with additional initialization operations.

### 5.1 Composition mechanism

Base template

Common schema and extensions

Derived template A

Base + shared reference data

Derived template B

Template A + specialized scenario data

Test database 1

Clone of B

Test database 2

Independent clone of B

A typical composition has the form:

- `base_proc = factories.postgresql_proc(load=[load_schema])`
- `seeded = factories.postgresql_noproc(depends_on="base_proc", load=[load_reference_data])`
- `scenario = factories.postgresql_noproc(depends_on="seeded", load=[load_scenario])`
- `client = factories.postgresql("scenario")`

Each derived fixture creates its own template and uses its parent template as the starting point.

### 5.2 Architectural implications

Reusable initialization layers. Schema migrations, common reference data, and specialized datasets can be represented by separate fixtures without rerunning all parent initialization functions.

Independent testing variants. Multiple derived templates may share one base template while applying different fixture-specific initialization operations.

Explicit fixture dependencies. The dependency hierarchy becomes part of pytest's fixture graph, allowing pytest to coordinate setup and teardown.

Database-local state inheritance. The layers inherit database-local objects and data through PostgreSQL cloning, rather than through a custom serialization or fixture-replay format.

### 5.3 Constraints

All layers need a compatible PostgreSQL server and suitable database privileges. The library inherits connection settings from the referenced base fixture unless explicitly overridden.

Template names must also be distinguishable. When `depends_on` is supplied without an explicit `dbname`, the implementation derives a distinct database name using the dependency fixture name.

Hierarchical templates do not isolate PostgreSQL cluster-wide resources such as roles and server configuration. They are database-level layers, not nested server instances.

This capability can materially reduce custom initialization orchestration when many test scenarios differ by relatively small additions to a shared schema and dataset.

Source: [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/factories/noprocess.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/factories/noprocess.py?utm_source=chatgpt.com)

## 6. Advanced lifecycle API: DatabaseJanitor

`pytest_postgresql.janitor.DatabaseJanitor` is the underlying database-management abstraction. It can be used directly, independently of the predefined pytest fixtures.

### 6.1 Principal operations

| API                    | Functionality                                                                                        |
| ---------------------- | ---------------------------------------------------------------------------------------------------- |
| `DatabaseJanitor(...)` | Configure database identity, authentication, templates, maintenance database, and lifecycle behavior |
| `.init()`              | Create a database, optionally cloning an existing template                                           |
| `.load(...)`           | Initialize the database with a SQL file or callable                                                  |
| `.drop()`              | Terminate connections and remove the managed database                                                |
| `.cursor(dbname=None)` | Open an administrative cursor, normally connected to the maintenance database                        |
| `with janitor:`        | Create a database on entry and drop it on exit                                                       |

The corresponding asynchronous API, `AsyncDatabaseJanitor`, exposes awaitable `init()`, `load()`, and `drop()` methods, an asynchronous `cursor()` context manager, and `async with` lifecycle management.

### 6.2 Significant constructor options

| Parameter                          | Purpose                                                  |
| ---------------------------------- | -------------------------------------------------------- |
| `dbname`                           | Database being created or managed; required              |
| `template_dbname`                  | Existing database to clone from                          |
| `as_template`                      | Whether to mark the newly created database as a template |
| `maintenance_dbname`               | Administrative database; defaults to `postgres`          |
| `user`, `password`, `host`, `port` | Connection identity                                      |
| `isolation_level`                  | Optional psycopg isolation level                         |
| `autocommit`                       | Autocommit behavior of initialization loaders            |
| `connection_timeout`               | Connection retry window; defaults to 60 seconds          |

All constructor arguments are keyword-only.

The formerly supported `version` constructor parameter is deprecated in version 9.0.

### 6.3 Database cleanup semantics

The janitor performs more than `DROP DATABASE IF EXISTS`.

Before dropping a database, it:

1. Checks whether the database exists.
2. Sets `ALLOW_CONNECTIONS = false`.
3. Terminates backends connected to that database.
4. Clears the template flag if it is managing a template database.
5. Executes the database drop.

Before cloning an existing template, the janitor also terminates connections to the source template.

The SQL operations use psycopg's identifier-composition facilities for database names.

These mechanisms help make cleanup resilient to applications that leave connections open. They are also destructive: clients connected to a database being removed may receive connection errors, and reused database names on shared infrastructure require careful ownership boundaries.

### 6.4 Administrative connections and retry behavior

`cursor()` defaults to the configured maintenance database. Its administrative connection runs in autocommit mode, because `CREATE DATABASE` and `DROP DATABASE` cannot execute inside normal transaction blocks.

The janitor retries connection attempts when psycopg raises `OperationalError`. The default retry window is 60 seconds, with roughly one-second pauses between attempts.

This supports startup coordination, but it is not a generalized retry framework for arbitrary failed SQL statements or application transactions.

### 6.5 Architectural applications

The direct janitor API is useful for custom pytest fixture hierarchies, database creation outside the standard client fixture, specialized provisioning tools, and integration tests requiring explicitly managed database lifetimes.

It can also support nonstandard database identities and independently managed template chains.

The janitor does not own a PostgreSQL process. It depends on the caller to ensure that an appropriate PostgreSQL server exists.

Source: [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/janitor.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/janitor.py?utm_source=chatgpt.com)

## 7. Asynchronous PostgreSQL testing

Introduced in version 9.0

Version 9 adds first-class asynchronous client fixtures and janitor operations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 7.1 Asynchronous fixture support

`factories.postgresql_async(process_fixture_name, dbname=None, isolation_level=None)` creates a function-scoped async generator fixture that yields a `psycopg.AsyncConnection`.

Its lifecycle mirrors the synchronous counterpart:

- Resolve the session-scoped process fixture.
- Create an isolated test database through `AsyncDatabaseJanitor`.
- Establish an asynchronous psycopg connection.
- Apply an optional isolation level.
- Yield the connection.
- Close the connection and drop the database asynchronously.

It uses `pytest_asyncio.fixture` rather than merely declaring an ordinary pytest fixture wrapping an asynchronous function.

The optional `async` extra installs `pytest-asyncio >=1.4` and `aiofiles >=23.0`. The latter is specifically needed for asynchronous SQL-file loading.

### 7.2 Important distinction: asynchronous clients do not imply asynchronous template setup

The normal `postgresql_proc` and `postgresql_noproc` fixtures remain synchronous session fixtures.

Their template initialization proceeds through the synchronous `DatabaseJanitor`, even when clients use `postgresql_async`.

The execution boundaries are:

| Operation                                   | Normal fixture implementation |
| ------------------------------------------- | ----------------------------- |
| Server startup                              | Synchronous                   |
| Template initialization                     | Synchronous                   |
| Per-test database creation for async client | Asynchronous                  |
| Per-test database connection                | Asynchronous                  |
| Per-test database deletion                  | Asynchronous                  |
| Direct `AsyncDatabaseJanitor.load(...)`     | Asynchronous-capable          |

This distinction matters for event-loop behavior, expensive initialization functions, and async-only data loaders.

### 7.3 Asynchronous loading behavior

`AsyncDatabaseJanitor.load()` can process:

- Asynchronous Python loader functions, awaiting their results.
- Synchronous Python loader functions, running them through `asyncio.to_thread`.
- SQL `Path` loaders via `sql_async`, which uses `aiofiles` and `psycopg.AsyncConnection`.

It also handles returned awaitables from loader calls.

This enables both synchronous and asynchronous initialization logic to participate in an asynchronous database-management workflow without requiring every loader to implement an asynchronous interface.

### 7.4 Windows event-loop compatibility

Psycopg's asynchronous implementation is incompatible with the default Windows `ProactorEventLoop`; it requires a selector-compatible event loop.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

psycopg 3.3.7.dev1 documentation



In version 9.1.1, the plugin integrates with pytest-asyncio's loop-factory hook on Windows, supplying a `SelectorEventLoop` when no previous hook implementation has supplied another factory.

This behavior applies to the pytest-asyncio testing environment, not exclusively to one PostgreSQL fixture. Existing higher-priority loop factories are preserved.

For pytest-asyncio's default strict mode, async tests must be explicitly marked with `@pytest.mark.asyncio`; automatic mode can detect unmarked async tests.

Source: [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/\_asyncio_compat.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/_asyncio_compat.py?utm_source=chatgpt.com)

## 8. Configuration and customization

### 8.1 Configuration precedence

The documented precedence is:

Fixture factory arguments → pytest command-line options → pytest configuration → built-in defaults.

This allows independently configured process fixtures to coexist while retaining project-wide and execution-specific defaults.

Source: [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/README.rst](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/README.rst?utm_source=chatgpt.com)

### 8.2 Configuration surface

| Configuration purpose         | pytest configuration key        | CLI option                        |
| ----------------------------- | ------------------------------- | --------------------------------- |
| PostgreSQL executable         | `postgresql_exec`               | `--postgresql-exec`               |
| Hostname                      | `postgresql_host`               | `--postgresql-host`               |
| Port                          | `postgresql_port`               | `--postgresql-port`               |
| Port search attempts          | `postgresql_port_search_count`  | `--postgresql-port-search-count`  |
| Username                      | `postgresql_user`               | `--postgresql-user`               |
| Password                      | `postgresql_password`           | `--postgresql-password`           |
| Connection options            | `postgresql_options`            | `--postgresql-options`            |
| PostgreSQL startup parameters | `postgresql_startparams`        | `--postgresql-startparams`        |
| PostgreSQL server options     | `postgresql_postgres_options`   | `--postgresql-postgres-options`   |
| Unix socket directory         | `postgresql_unixsocketdir`      | `--postgresql-unixsocketdir`      |
| Default database              | `postgresql_dbname`             | `--postgresql-dbname`             |
| Maintenance database          | `postgresql_maintenance_dbname` | `--postgresql-maintenance-dbname` |
| Initialization loaders        | `postgresql_load`               | `--postgresql-load`               |
| Loader autocommit             | `postgresql_load_autocommit`    | `--postgresql-load-autocommit`    |
| Cleanup of leftover databases | No ini equivalent               | `--postgresql-drop-test-database` |

The CLI load option accepts repeated occurrences, allowing more than one initialization entry.

Some settings apply only to managed processes, others to externally managed servers, and some to both.

Subtle implementation detail: Several factory arguments are combined with defaults through truth-value fallback (`argument or configured_value`). Thus a supplied empty string or empty loader list does not necessarily override a configured value. `load_autocommit` is handled separately, allowing an explicit `False` override.

### 8.3 PostgreSQL binary discovery

For managed mode, version 9.1.1 uses the following discovery order when `executable` is not explicitly supplied:

1. Configured `postgresql_exec`, defaulting on Unix-like systems to `/usr/lib/postgresql/14/bin/pg_ctl`.
2. The executable directory returned by `pg_config --bindir`.
3. On Windows, versioned PostgreSQL installations under `%ProgramFiles%\PostgreSQL`.
4. `pg_ctl` on the system `PATH`.

Discovered executable paths are checked before use. A manually supplied factory `executable` is used directly.

A machine with multiple PostgreSQL versions may therefore need explicit executable selection to ensure that the test server uses the intended version.

Installing only PostgreSQL client-development components is insufficient for `postgresql_proc`; it needs the server executable.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



### 8.4 Port allocation

`postgresql_proc` supports more than a fixed port:

| `port` value              | Behavior                                 |
| ------------------------- | ---------------------------------------- |
| Integer or numeric string | Request a specific port                  |
| `None`                    | Select an available port                 |
| `-1`                      | Use the configured port selection        |
| Range tuple               | Select an available port within a range  |
| Set                       | Select among specified ports             |
| Range/set collections     | Select from multiple allowed port groups |

Port selection delegates to `port-for`.

The default port-search count is five. This is relevant when many server fixtures or parallel pytest workers may compete for limited port availability.

## 9. Parallel execution and concurrency

### 9.1 `pytest-xdist` support

`pytest-postgresql` incorporates two distinct parallel-execution mechanisms.

Managed-process workers: The process fixture uses `port-for` and exclusive-create sentinel files in a shared temporary directory to reduce collisions between workers starting separate PostgreSQL processes.

External-server workers: The no-process fixture incorporates the `PYTEST_XDIST_WORKER` identifier into the database name, so workers such as `gw0` and `gw1` can create separate templates and test databases on the same PostgreSQL server.

These mechanisms were introduced incrementally in earlier releases and remain part of version 9.1.1.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 9.2 Scope of isolation

Parallel safety is not equivalent to complete independence.

| Resource                       | Isolation behavior                                               |
| ------------------------------ | ---------------------------------------------------------------- |
| Test database contents         | Independent test databases                                       |
| Managed PostgreSQL server      | Separate processes for separate managed process fixtures/workers |
| External PostgreSQL server     | Shared server                                                    |
| External server roles          | Shared                                                           |
| External server configuration  | Shared                                                           |
| Database-level schema and data | Isolated through cloning                                         |
| Shared external services       | Not isolated by the plugin                                       |

Worker suffixing reduces naming collisions within an xdist run. It is not a globally unique namespace across independent pytest invocations.

For example, two unrelated pytest sessions using the same external PostgreSQL server and the same base database name can still interfere with each other, even when both use xdist worker identifiers.

### 9.3 Connection termination versus concurrent application activity

The janitor actively terminates connections during cleanup.

This is useful when an application leaves connections open, but it does not provide graceful shutdown coordination for arbitrary background tasks or connection pools.

Tests that use independent application engines, worker processes, or background activity should account for those resources before database teardown.

In particular, an application that continues to reconnect to a database after fixture teardown begins can produce connection errors or cleanup interference.

## 10. Integration boundaries

`pytest-postgresql` provides database infrastructure and native psycopg connections. It is not itself an ORM, migration engine, connection pool, container orchestrator, or general database-testing framework.

### 10.1 psycopg 3

The plugin requires psycopg 3 for its own administrative operations and client fixtures.

Consequently, returned connections support the capabilities of the installed psycopg version, including PostgreSQL transaction controls, cursors, COPY operations, and other native psycopg functionality.

These are psycopg capabilities, not additional pytest-postgresql abstractions.

An application using psycopg 2 can still be tested against the managed PostgreSQL database, provided its application connection is created separately.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.psycopg.org\&sz=32)

PostgreSQL adapter for Python



### 10.2 SQLAlchemy

The upstream documentation explicitly demonstrates creating a SQLAlchemy engine and session using PostgreSQL connection information from the fixture.

Useful integration mechanisms include:

- Building an engine using the `postgresql+psycopg` dialect.
- Creating ORM sessions scoped to a pytest fixture.
- Using `NullPool` to avoid retaining unwanted connections through teardown.
- Creating schema objects from SQLAlchemy metadata.
- Loading SQLAlchemy-managed reference data into the process template.

Important distinction: The supplied `postgresql` fixture is a psycopg connection, not an SQLAlchemy engine or session. SQLAlchemy constructs remain application- or fixture-owned.

Source: [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/README.rst](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/README.rst?utm_source=chatgpt.com)

### 10.3 Alembic

Alembic integration is indirect but particularly relevant to template initialization.

A process-fixture loader can invoke Alembic to initialize or migrate the template database once. Subsequent test databases inherit the resulting schema.

This can avoid repeated migration execution in tests whose objective is to validate application behavior against a known schema.

However, migration testing itself is a different operation. Testing upgrade paths, downgrade paths, or migrations from different historical states requires appropriately constructed initial databases and explicit migration execution.

`pytest-postgresql` does not supply specialized Alembic revision management, migration assertions, or downgrade verification.

### 10.4 Docker and Testcontainers

The integration boundary is straightforward:

| Component               | Responsibilities                                                               |
| ----------------------- | ------------------------------------------------------------------------------ |
| `pytest-postgresql`     | Database template management, fixture creation, connection management, cleanup |
| Docker / Docker Compose | Container provisioning, image selection, container networks, lifecycle         |
| Testcontainers          | Programmatic container provisioning and lifecycle                              |
| PostgreSQL              | Actual SQL execution, transactions, storage, locking, cloning                  |
| psycopg / SQLAlchemy    | Client interactions and application database access                            |

`postgresql_noproc` can consume server connection details provided by container tooling.

The plugin does not need to control how the server was provisioned, but it still requires sufficient database-administration capabilities within that server.

### 10.5 Other drivers and frameworks

The infrastructure can support application code using other PostgreSQL clients, such as asyncpg or an ORM with a different driver.

However, `postgresql_async` returns a psycopg async connection, not an asyncpg connection. Integration with other client types must be implemented by constructing those clients against the fixture's database endpoint.

This division is useful: the library manages isolated PostgreSQL state, while application tests use the same driver and transaction behavior as their production application.

## 11. PostgreSQL semantics and material limitations

### 11.1 Cloning is not a metadata-only snapshot

The library relies on PostgreSQL's native database cloning through `CREATE DATABASE ... TEMPLATE`.

PostgreSQL copies the source database rather than merely creating a lightweight metadata pointer to its contents.

PostgreSQL documentation distinguishes `WAL_LOG` and `FILE_COPY` database-creation strategies, with different write-ahead-log and checkpoint costs. The plugin itself does not expose a dedicated database-cloning strategy argument.

Consequently, clone cost can increase substantially with template size. An extremely large reference dataset can shift the performance balance away from one-database-per-test cloning.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org



### 11.2 PostgreSQL template restrictions

PostgreSQL requires that no other sessions be connected to the source database when cloning begins.

The janitor mitigates this by terminating connections to the source template, but this is not the same as supporting continuous concurrent activity against that template.

Additionally, PostgreSQL database cloning does not copy database-level `GRANT` permissions from the source database. The new database receives its default database-level permissions.

This distinction matters for tests specifically validating database access control. Database objects and database-level privileges do not necessarily have identical inheritance semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org



### 11.3 Database isolation versus cluster isolation

Tests on the same PostgreSQL server can share resources that are not contained within individual databases.

Important examples include server roles, server configuration, physical storage, server-level resource pressure, and some extension or background-worker behavior.

Therefore:

- Database-level changes generally remain within the test database.
- Cluster-level changes may affect other tests on the same server.
- A dedicated `postgresql_proc` instance provides a stronger isolation boundary than separate databases on a shared external server.

This is particularly consequential for tests of role management, server configuration, resource exhaustion, or other cluster-wide behavior.

### 11.4 Not a transaction-rollback fixture

The plugin's standard isolation model is database creation and deletion.

It does not rely on a persistent surrounding test transaction that is rolled back after every test.

This makes committed operations and many DDL changes naturally compatible with isolation, but it also entails the overhead of creating and dropping databases.

A transaction-rollback strategy may be cheaper for small, entirely transactional tests. Conversely, database cloning can be preferable when tests need to commit transactions, exercise multiple independent connections, or perform schema-level operations.

The correct performance comparison depends on the workload; neither approach universally dominates.

### 11.5 Persistent servers and destructive cleanup

With `postgresql_noproc`, the plugin does not own the underlying server. Nonetheless, it creates and deletes databases.

The risk is particularly important when configuring custom database names and connecting to externally managed infrastructure.

The `--postgresql-drop-test-database` flag exists to recover from databases left behind by failed or interrupted runs. The upstream help text explicitly advises caution and discourages using it in CI.

It is not a general-purpose database cleanup command and should not be treated as harmless on an external server.

### 11.6 Other boundaries

| Boundary                           | Consequence                                                                                                      |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| PostgreSQL server required         | The plugin cannot provide PostgreSQL semantics using an in-memory Python substitute                              |
| Administrative privileges required | Restricted shared or managed services may not support all fixture operations                                     |
| Database-template cloning          | Large templates can impose substantial I/O and WAL overhead                                                      |
| Session-scoped initialization      | Loader code is not automatically rerun for every test                                                            |
| Application connection pools       | The plugin cannot guarantee graceful disposal of independently managed connections                               |
| External resources                 | Files, queues, caches, and other services are outside its isolation boundary                                     |
| Version fidelity                   | Managed tests use the discovered/configured PostgreSQL executable, not necessarily the production server version |
| Server-specific defaults           | Managed-process performance and durability settings may differ from production                                   |

## 12. Release evolution and compatibility

Understanding the more recent major releases is important because several capabilities and signatures changed substantially.

| Release              | Significant changes                                                                                                                            |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 7.0 — February 2025  | Removed client-level `load`; added improved cleanup recovery and parallel port coordination                                                    |
| 8.0 — January 2026   | Introduced hierarchical template chaining with `depends_on`; explicit janitor template management; PostgreSQL ≥14 and pytest ≥8.2 requirements |
| 8.1 — May 2026       | Added Windows support for managed PostgreSQL executors                                                                                         |
| 9.0 — August 2026    | Async fixtures and janitor, loader autocommit, configurable maintenance database, keyword-only factory parameters                              |
| 9.1 — September 2026 | Improved automatic `pg_ctl` discovery on Windows                                                                                               |
| 9.1.1 — October 2026 | Maintenance and dependency-management release; no major new runtime feature announced                                                          |

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

Three compatibility issues deserve particular attention:

Loader signatures changed in 9.0. Custom loader functions must accept the additional `autocommit` keyword argument.

Factory signatures became stricter. Parameters following `dbname` in the process factory signatures are keyword-only. Existing code using positional arguments for options, loaders, or dependencies may need adjustment.

Janitor construction changed in 8.0. The `dbname` parameter became required and template management moved to the explicit `as_template` model.

These changes affect existing test infrastructure more than ordinary tests consuming the default `postgresql` fixture.

## 13. Capability interactions and architectural opportunities

The library's strongest capabilities emerge from combinations rather than individual fixtures.

| Capability combination                | Resulting architectural option                                            | Important condition                                                |
| ------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Managed process + template population | Self-contained integration tests against initialized PostgreSQL           | Local PostgreSQL server binaries available                         |
| External server + template cloning    | Reuse container or CI PostgreSQL while preserving per-test database state | Database creation/deletion privileges                              |
| Template chaining + reusable loaders  | Composable schema, reference-data, and scenario layers                    | Compatible initialization and database-local state                 |
| Janitor + custom fixtures             | Explicit database lifecycles beyond standard fixture return types         | Caller manages identities and resource lifetimes                   |
| Async fixture + async janitor         | End-to-end asynchronous client database management                        | Compatible pytest-asyncio environment                              |
| SQLAlchemy/Alembic + process loader   | Initialize application schema and data once, then clone                   | Tests do not require initialization to run independently each time |
| xdist + managed processes             | Parallel test workers with independently provisioned PostgreSQL           | Adequate ports, CPU, memory, and storage                           |
| xdist + external PostgreSQL           | Worker-specific test databases on a shared server                         | Avoid cross-run name collisions and cluster-wide interference      |

Three architectural conclusions are especially significant.

First, initialization is reusable state, not necessarily repeated work. The distinction between template construction and test-database construction makes initialization complexity largely independent of the number of tests, though the database-cloning cost remains.

Second, database lifecycle is independent of application connection lifecycle. This allows applications to test multiple simultaneous connections, independent transactions, separate ORM sessions, or alternative database drivers without requiring the plugin to mediate their operations.

Third, template chaining provides a form of compositional database-state modeling. Rather than maintaining many unrelated SQL dumps or repeating initialization pipelines, test-state variants can share a common initialized base and add only their distinguishing operations.

These are architectural possibilities enabled by the released library, not guarantees of superior performance in every test environment.

## 14. Source map for further investigation

The following links point to the version-specific implementation or authoritative PostgreSQL behavior.

| Investigation area                 | Primary source                                                                                                                                                                                                                      |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Fixture factories and signatures   | [https://github.com/dbfixtures/pytest-postgresql/tree/v9.1.1/pytest_postgresql/factories](https://github.com/dbfixtures/pytest-postgresql/tree/v9.1.1/pytest_postgresql/factories?utm_source=chatgpt.com)                           |
| Managed-process initialization     | [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/factories/process.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/factories/process.py?utm_source=chatgpt.com)     |
| External servers and chaining      | [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/factories/noprocess.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/factories/noprocess.py?utm_source=chatgpt.com) |
| Synchronous/asynchronous clients   | [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/factories/client.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/factories/client.py?utm_source=chatgpt.com)       |
| Administrative database lifecycle  | [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/janitor.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/janitor.py?utm_source=chatgpt.com)                         |
| Database loading                   | [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/loader.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/loader.py?utm_source=chatgpt.com)                           |
| Configuration and default fixtures | [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/plugin.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/plugin.py?utm_source=chatgpt.com)                           |
| Managed server executor            | [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/executors/proc.py](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/executors/proc.py?utm_source=chatgpt.com)           |
| PostgreSQL template semantics      | [https://www.postgresql.org/docs/18/manage-ag-templatedbs.html](https://www.postgresql.org/docs/18/manage-ag-templatedbs.html?utm_source=chatgpt.com)                                                                               |
| PostgreSQL database-cloning costs  | [https://www.postgresql.org/docs/18/sql-createdatabase.html](https://www.postgresql.org/docs/18/sql-createdatabase.html?utm_source=chatgpt.com)                                                                                     |
| Release and migration history      | [https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/CHANGES.rst](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/CHANGES.rst?utm_source=chatgpt.com)                                                           |

## 15. Overall synthesis

`pytest-postgresql` is best understood as a PostgreSQL lifecycle and isolated database-state orchestration layer for pytest.

Its defining capabilities are not limited to starting PostgreSQL or producing a database connection. They are the coordinated management of session-scoped servers, populated template databases, independently cloned test databases, and cleanup across synchronous, asynchronous, custom, and parallel fixture configurations.

The most valuable advanced capabilities to recognize are hierarchical template chaining, programmatic janitor APIs, external-server integration, reusable initialization loaders, and the asynchronous facilities added in version 9.

The main architectural boundary is equally important: database-level isolation is not server-level isolation, and PostgreSQL database cloning is not a free snapshot operation. Understanding those two constraints is central to reasoning correctly about the library's scalability, correctness, and integration opportunities.

The overview is grounded in the published 9.1.1 release, upstream documentation, tagged source, and PostgreSQL primary documentation. No runtime benchmarks or empirical integration tests were performed for this reference.