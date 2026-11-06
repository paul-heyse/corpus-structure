# pgTAP, pg_prove, and pg_virtualenv: Comprehensive PostgreSQL Testing Reference

Research date: November 6, 2026 · Scope: SQL-level testing, TAP orchestration, ephemeral PostgreSQL clusters, database verification, and advanced integration capabilities.

## 1. Architectural overview

pgTAP, pg_prove, and pg_virtualenv form three complementary layers of PostgreSQL testing infrastructure. Together, they enable database-native assertions, automated execution and reporting, and disposable PostgreSQL environments running the actual database engine.

They are separate tools with distinct responsibilities, rather than components of a single package.

| Tool          | Primary responsibility                 | Architectural role                                                                                                   |
| ------------- | -------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| pgTAP         | Database assertions and test lifecycle | SQL/PLpgSQL framework for validating data, behavior, schema, constraints, permissions, and other database properties |
| pg_prove      | Test execution and reporting           | Perl-based TAP harness that executes SQL tests through `psql`, interprets results, and coordinates test suites       |
| pg_virtualenv | Temporary database infrastructure      | Debian/Ubuntu PostgreSQL system utility that creates, configures, runs, and destroys disposable PostgreSQL clusters  |

How the components fit together

pg_virtualenv

Create an ephemeral PostgreSQL cluster and configure connection variables

pg_prove

Discover tests, run psql sessions, parse TAP, report failures

pgTAP

Execute assertions inside PostgreSQL and emit TAP results

Conceptual composition; pgTAP and pg_prove can also operate independently of pg_virtualenv.

An important distinction is that `pg_virtualenv` is a public, open-source system utility that creates private, temporary PostgreSQL environments. It is not a proprietary PostgreSQL testing extension, a Python-style virtual environment, or an in-memory PostgreSQL emulator. Its isolation comes primarily from separately created database clusters and their configuration, rather than from database transaction rollback alone.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://manpages.debian.org\&sz=32)

Debian Manpages+1



### Verified release baseline

| Component     | Reference version                                                        | Verification                                                                                                                                        |
| ------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| pgTAP         | 1.3.4, released October 4, 2025                                          | Latest published stable PGXN release. The upstream `main` branch identifies itself as 1.3.5, but that does not establish a published 1.3.5 release. |
| pg_prove      | 3.37, released March 30, 2025                                            | Distributed through the CPAN package `TAP::Parser::SourceHandler::pgTAP`.                                                                           |
| pg_virtualenv | postgresql-common 293, Debian unstable documentation dated July 16, 2026 | Versioned as part of `postgresql-common`, rather than as an independent application.                                                                |

Sources: PGXN release [https://pgxn.org/dist/pgtap/1.3.4/](https://pgxn.org/dist/pgtap/1.3.4/?utm_source=chatgpt.com) ; pgTAP upstream [https://github.com/theory/pgtap](https://github.com/theory/pgtap?utm_source=chatgpt.com) ; CPAN distribution [https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP](https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP?utm_source=chatgpt.com) ; Debian man page [https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html](https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html?utm_source=chatgpt.com) .&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.pgxn.org\&sz=32)

pgxn.org+3



The remainder focuses on published functionality, identifying version- and platform-dependent features where material.

## 2. pgTAP — database-native testing and assertion framework

### 2.1 Conceptual model and test lifecycle

pgTAP brings the Test Anything Protocol (TAP) into PostgreSQL.

Unlike frameworks that retrieve data into a client language and then evaluate assertions, pgTAP performs assertions inside the database engine. SQL statements and stored functions generate TAP records such as:

```
1..3
ok 1 - Expected table exists
ok 2 - Foreign key is correctly defined
not ok 3 - Query returned expected rows
# Failed test 3: "Query returned expected rows"
```

TAP establishes a common protocol between the code producing test results and the harness evaluating them. The output includes numbered results, failure diagnostics, test plans, and directives such as `SKIP` and `TODO`.

This separation permits tests authored entirely in SQL to be consumed by pg_prove, Perl's `prove`, or another compatible TAP harness.

pgTAP supports two principal execution models.

SQL-script execution

Tests run sequentially in a SQL script, normally inside an explicitly rolled-back transaction:

```
BEGIN;

SELECT plan(3);

SELECT has_schema('public', 'Public schema exists');

SELECT is(
    2 + 2,
    4,
    'Arithmetic returns the expected value'
);

SELECT has_table('public', 'customers',
                 'Customers table exists');

SELECT * FROM finish();

ROLLBACK;
```

The database evaluates each expression and pgTAP emits its result. `finish()` checks the completed test count against the declared plan and produces final diagnostics.

`finish(true)` can additionally raise an exception when tests fail, which is useful when the caller needs SQL-level failure signaling rather than relying exclusively on TAP parsing.

`no_plan()` allows a variable number of assertions, but removes the fixed assertion-count guarantee. A plan is especially useful for detecting prematurely terminated suites.

Database-resident xUnit execution

Tests can instead be encapsulated in PostgreSQL functions returning `SETOF text`. The `runtests()` function discovers matching functions, executes their lifecycle hooks, collects results into TAP subtests, and handles transaction rollback.

These are different execution models rather than alternative syntax for the same runner. SQL scripts emphasize explicit control of setup, execution, and cleanup; `runtests()` adds function discovery and a predefined fixture lifecycle.

Primary documentation: [https://pgxn.org/dist/pgtap/doc/pgtap.html](https://pgxn.org/dist/pgtap/doc/pgtap.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org+2



### 2.2 Assertion capability families

pgTAP's functionality extends considerably beyond scalar equality checks.

| Capability family           | Representative functions                                                    | What can be verified                                                        |
| --------------------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Scalar assertions           | `ok`, `is`, `isnt`, `cmp_ok`, `isa_ok`                                      | Boolean predicates, typed equality, arbitrary operators, value types        |
| Pattern assertions          | `matches`, `imatches`, `alike`, `ialike`, inverse variants                  | Regular-expression and SQL pattern matching                                 |
| SQL execution behavior      | `throws_ok`, `throws_like`, `throws_matching`, `lives_ok`                   | Expected SQL failures, SQLSTATE codes, error messages, successful execution |
| Query results               | `results_eq`, `results_ne`, `row_eq`, `is_empty`, `isnt_empty`              | Ordered results, row values, presence or absence of query results           |
| Relational equivalence      | `set_eq`, `set_ne`, `bag_eq`, `bag_ne`                                      | Unordered result equality, with or without duplicate sensitivity            |
| Relational inclusion        | `set_has`, `set_hasnt`, `bag_has`, `bag_hasnt`                              | Subsets, duplicate-sensitive containment, disjointness                      |
| Schema inventory            | `tables_are`, `columns_are`, `functions_are`, `extensions_are`, and others  | Exact sets of database objects                                              |
| Object existence            | `has_table`, `has_column`, `has_index`, `has_function`, etc.                | Required or forbidden schema objects                                        |
| Constraints and indexes     | `has_pk`, `has_fk`, `fk_ok`, `has_check`, `index_is_partial`, etc.          | Structural relationships, constraints, index attributes                     |
| Procedure/function metadata | `function_returns`, `volatility_is`, `is_definer`, `is_strict`, etc.        | Stored routine contracts and execution attributes                           |
| Security metadata           | `table_privs_are`, `is_member_of`, `policies_are`, `policy_roles_are`, etc. | Privileges, ownership, role relationships, RLS policy metadata              |
| Timing assertions           | `performs_ok`, `performs_within`                                            | Execution-time thresholds and approximate runtime windows                   |
| Execution control           | `skip`, `todo`, `todo_start`, `todo_end`, `diag`                            | Conditional testing, expected failures, diagnostics                         |

The main architectural value is the ability to test PostgreSQL's own abstractions—catalog objects, function signatures, privileges, relational results, and runtime errors—without separately implementing database introspection and comparison infrastructure.

Source: [https://pgxn.org/dist/pgtap/doc/pgtap.html](https://pgxn.org/dist/pgtap/doc/pgtap.html?utm_source=chatgpt.com)

### 2.3 Relational result comparison: a particularly important capability

One of pgTAP's strongest features is its direct support for different mathematical interpretations of query-result equality.

Comparison semantics for SQL result sets

Ordered — `results_eq`

Order and multiplicity both matter.

Actual: [A, B, A]

Expected: [A, A, B]

Fails: different order

Set — `set_eq`

Order and duplicate counts are ignored.

Actual: [A, B, A]

Expected: [A, A, B]

Passes: same distinct values

Multiset — `bag_eq`

Order is ignored, but duplicate counts must match.

[A, B, A] versus [A, A, B]

Passes

[A, B, A] versus [A, B, B]

Fails

`results_eq(actual, expected)` performs ordered, row-by-row comparison. It supports SQL query strings, prepared statements, PostgreSQL cursors, and appropriately typed arrays for single-column results. It also checks column compatibility and reports the first relevant discrepancy. Queries whose order matters must produce deterministic ordering, generally through an explicit `ORDER BY`.

`set_eq()` compares relations as mathematical sets. Duplicate multiplicity does not matter, making it appropriate for verifying queries whose logical result is an unordered collection of distinct records.

`bag_eq()` preserves multiplicity but ignores ordering. It is particularly useful when testing aggregation pipelines, joins, denormalized outputs, or other SQL operations where duplicate rows are semantically significant.

The related inclusion operations add further expressiveness:

- `set_has(actual, expected)` establishes that every distinct expected record occurs in the actual result.
- `set_hasnt(actual, forbidden)` establishes that the two sets have no common records.
- `bag_has()` uses duplicate-sensitive containment, internally relying on `EXCEPT ALL`.
- `bag_hasnt()` checks duplicate-sensitive overlap using `INTERSECT ALL`.

These operations provide relational assertions directly rather than requiring application-level conversion into Python lists, sets, counters, or custom comparison objects.

The query arguments must be relationally compatible; PostgreSQL data types, casts, collation behavior, and `NULL` semantics still govern the underlying SQL operations.

Source: [https://pgxn.org/dist/pgtap/doc/pgtap.html](https://pgxn.org/dist/pgtap/doc/pgtap.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org+3



### 2.4 Prepared statements, cursors, and typed comparisons

The query-assertion functions accept SQL strings, and many also accept names of prepared statements.

For example:

```
PREPARE actual_rows AS
SELECT id, status
FROM orders
WHERE status = 'open'
ORDER BY id;

PREPARE expected_rows AS
VALUES
    (1, 'open'::text),
    (2, 'open'::text);

SELECT results_eq(
    'actual_rows',
    'expected_rows',
    'Open orders match expectations'
);
```

This is an illustrative example. The expected values and types must match the actual query schema.

Prepared statements help keep complicated query definitions out of doubly quoted SQL strings and enable reuse across multiple assertions.

pgTAP also supports `refcursor` inputs to several `results_eq()` overloads, allowing an assertion to consume existing database cursors. This is useful when tests interact with SQL functions or procedural code that exposes cursor-oriented results.

`row_eq()` compares a query's single-row result with a PostgreSQL record or composite value. PostgreSQL 11 and later support bare `RECORD` arguments for this assertion; older versions require an explicitly defined composite type.

The distinction between SQL values and their textual presentation also matters. `is()` uses `IS NOT DISTINCT FROM` semantics and therefore handles two `NULL` values as equal. By contrast, `cmp_ok()` evaluates an operator, and a resulting SQL `NULL` is a failed assertion.

Primary documentation: [https://pgxn.org/dist/pgtap/doc/pgtap.html](https://pgxn.org/dist/pgtap/doc/pgtap.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org+2



### 2.5 Database catalog and schema-contract verification

pgTAP has a substantial collection of catalog-driven assertions. This is one of the areas where it can eliminate repetitive inspection of `pg_catalog` and `information_schema`.

Exact-object-set assertions support declarative contracts over entire schema families, including tables, views, materialized views, columns, indexes, triggers, functions, procedures, sequences, types, domains, enums, operators, casts, extensions, and roles.

For example:

```
SELECT tables_are(
    'public',
    ARRAY['customers', 'orders', 'order_lines']
);
```

This checks that the scoped table inventory matches the expected list, rather than merely confirming that those three tables exist. The distinction is important: inventory assertions can detect unexpected objects as well as missing objects.

Structural and relational assertions verify more specific database properties:

- Primary and foreign keys: `has_pk`, `has_fk`, `col_is_pk`, `col_is_fk`, `fk_ok`.
- Uniqueness and checks: `has_unique`, `col_is_unique`, `has_check`, `col_has_check`.
- Index properties: `index_is_unique`, `index_is_primary`, `index_is_partial`, `index_is_type`, `is_indexed`.
- Column contracts: `col_type_is`, `col_default_is`, `col_not_null`, `col_has_default`.
- Partitioning and inheritance: `partitions_are`, `is_partitioned`, `is_partition_of`, `has_inherited_tables`, `is_ancestor_of`.

Together, these facilities allow database schemas to be treated as verifiable contracts, covering both the presence of objects and significant aspects of how they relate.

There are limits to the granularity of individual assertions. For example, confirming that a check constraint exists is not necessarily equivalent to proving its complete predicate semantics. Behavioral SQL tests remain important where metadata assertions cannot establish correctness.

### 2.6 Stored-function, procedure, and trigger contracts

pgTAP can verify characteristics of executable database objects beyond their names and existence.

The function-testing family includes:

| Function                          | Verified characteristic                               |
| --------------------------------- | ----------------------------------------------------- |
| `function_returns()`              | Declared return type of a specific function signature |
| `function_lang_is()`              | Implementation language                               |
| `volatility_is()`                 | `IMMUTABLE`, `STABLE`, or `VOLATILE` declaration      |
| `is_strict()` / `isnt_strict()`   | Strict/null-input behavior declaration                |
| `is_definer()` / `isnt_definer()` | Security-definer status                               |
| `is_normal_function()`            | Ordinary function classification                      |
| `is_aggregate()`                  | Aggregate-function classification                     |
| `is_window()`                     | Window-function classification                        |
| `is_procedure()`                  | Stored-procedure classification                       |
| `trigger_is()`                    | Trigger-associated function characteristics           |
| `can()`                           | Availability of named functions or callable routines  |

Function overloads can be distinguished through argument-type signatures, an important capability in PostgreSQL because a function's identity is not determined by its name alone.

These assertions are useful for checking API compatibility during database migrations, especially when a change might preserve a function name while altering its signature, volatility, security model, or return type.

A metadata check such as `volatility_is()` validates the declared attribute; it does not prove the implementation actually satisfies PostgreSQL's volatility contract. That requires separate behavioral analysis or tests.

Stored-procedure-specific assertions require PostgreSQL versions that support procedures.

### 2.7 Database permissions, ownership, and row-level security

pgTAP also supports verification of database authorization structures.

The privilege assertion families include `database_privs_are`, `schema_privs_are`, `table_privs_are`, `column_privs_are`, `function_privs_are`, `sequence_privs_are`, `fdw_privs_are`, and `server_privs_are`.

Ownership assertions cover databases, schemas, relations, views, functions, types, operators, and additional catalog objects.

Role-related assertions include `has_role`, `is_superuser`, `is_member_of`, and `isnt_member_of`.

For row-level security, pgTAP provides:

- `policies_are()` to validate the exact policy-name inventory associated with a table.
- `policy_roles_are()` to validate the roles assigned to a policy.
- `policy_cmd_is()` to validate a policy's SQL-command applicability.

These capabilities make security configuration testable alongside the broader schema contract.

Important boundary: policy metadata verification does not establish that every RLS predicate behaves correctly. For effective authorization testing, pgTAP assertions can be combined with PostgreSQL role changes and queries executed as the relevant identities. That verifies actual access behavior rather than only policy presence.

The same distinction applies to `SECURITY DEFINER` functions and object privileges: declared configuration and effective permissions are related but different properties.

Source: [https://pgxn.org/dist/pgtap/doc/pgtap.html](https://pgxn.org/dist/pgtap/doc/pgtap.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org+1



### 2.8 SQL errors and execution-time assertions

pgTAP's exception assertions provide a native mechanism for testing expected PostgreSQL error behavior.

`throws_ok()` can check that a SQL statement fails with a particular SQLSTATE, optionally including its error message. Related variants support pattern-based message matching, including `throws_like`, `throws_ilike`, `throws_matching`, and `throws_imatching`.

For instance:

```
SELECT throws_ok(
    'SELECT 1 / 0',
    '22012',
    NULL,
    'Division by zero raises the correct SQLSTATE'
);
```

SQLSTATE-based assertions are generally more durable than exact server-error-message matching, since messages may differ by PostgreSQL version or localization.

`lives_ok()` checks that an SQL statement executes without throwing an exception.

pgTAP also includes two timing mechanisms:

| Assertion                                                    | Measurement                                                                                                                                               |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `performs_ok(sql, milliseconds)`                             | Checks that a statement completes below a specified duration                                                                                              |
| `performs_within(sql, average_ms, tolerance_ms, iterations)` | Repeated execution, defaulting to 10 samples, discarding the highest and lowest 10%, and testing the average of the middle 80% against a tolerance window |

The timing assertions include PL/pgSQL dynamic-execution overhead. They are suitable for coarse regression guards, but should not be treated as statistically rigorous benchmarks. Changes in cache state, hardware load, query plans, and data volume can affect results.

Source: [https://pgxn.org/dist/pgtap/doc/pgtap.html](https://pgxn.org/dist/pgtap/doc/pgtap.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org+2



### 2.9 Advanced execution and fixture management

pgTAP provides two function-based orchestration mechanisms that deserve explicit distinction.

`do_tap()`

Discovers and executes matching TAP-producing functions. It can be restricted by schema and regular-expression name pattern, but callers control their own planning and finalization.

`runtests()`

Provides the more complete xUnit lifecycle:

`startup_*` functions, once

Repeated for each test function

Create subtransaction

Run `setup_*` functions

Run the test function

Run `teardown_*` functions

Roll back subtransaction

`shutdown_*` functions, once

Finish TAP reporting and rollback

Functions matching the `startup`, `setup`, `teardown`, and `shutdown` prefixes are discovered automatically. Setup and teardown functions are ordered alphabetically. A teardown function is not guaranteed to run after a test function dies unexpectedly.

Each test executes within a subtransaction, with its setup and teardown changes rolled back before the next test. The overall test execution is also rolled back.

The distinction between transaction rollback and full state restoration matters: PostgreSQL sequence increments are not undone by transaction rollback. Other out-of-database effects likewise require separate lifecycle controls.

`runtests()` also reports nested TAP subtests, giving individual test functions their own assertion counts and diagnostic context.

Source: [https://pgxn.org/dist/pgtap/doc/pgtap.html](https://pgxn.org/dist/pgtap/doc/pgtap.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org+1



### 2.10 Extensibility and less obvious utilities

pgTAP includes mechanisms for composing test logic rather than only consuming predefined assertions.

`check_test()` can validate custom pgTAP assertion functions, including whether they pass or fail and whether they emit the expected descriptions and diagnostics.

`collect_tap()` combines multiple TAP results into a single value, which is particularly useful inside conditional SQL expressions.

`skip()`, `todo()`, `todo_start()`, and `todo_end()` permit version-dependent testing, capability-dependent assertions, and expected failures without discarding test-plan accounting.

`pg_version_num()`, `pg_version()`, `pgtap_version()`, and `os_name()` expose environment-related values that can support conditional tests.

`findfuncs()`, `format_type_string()`, and `display_oper()` provide supporting introspection and formatting functionality.

Because the assertion functions themselves produce TAP records, custom SQL or PL/pgSQL functions can build richer reusable test primitives while still participating in standard plans, numbering, diagnostics, and harness processing.

A particularly useful composition is data-driven assertion generation using SQL relations: `VALUES`, joins, and catalog queries can produce multiple assertions without introducing an external test-generation language.

Documentation: [https://pgxn.org/dist/pgtap/doc/pgtap.html](https://pgxn.org/dist/pgtap/doc/pgtap.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org+2



### 2.11 Installation and integration boundaries

pgTAP is installed in PostgreSQL as an extension, usually with:

```
CREATE EXTENSION IF NOT EXISTS pgtap;
```

It can be installed into a dedicated schema using `CREATE EXTENSION pgtap SCHEMA tap`, provided the schema exists and the caller has the necessary privileges.

The released package supports PostgreSQL 9.1 and later, although capabilities such as partition and procedure assertions are naturally unavailable on server versions predating those features.

The installation files must be available on the PostgreSQL server host. A remote SQL client cannot install missing extension files onto a server merely by issuing `CREATE EXTENSION`.

The distribution also publishes `pgtap-core` and `pgtap-schema` extension components. These are part of the pgTAP distribution rather than alternative testing engines; the usual installation entry point remains `pgtap`.

Sources: [https://github.com/theory/pgtap](https://github.com/theory/pgtap?utm_source=chatgpt.com) and [https://pgxn.org/dist/pgtap/1.3.4/](https://pgxn.org/dist/pgtap/1.3.4/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



## 3. pg_prove — execution, orchestration, and TAP reporting

### 3.1 Execution architecture

`pg_prove` is a Perl command-line application distributed by `TAP::Parser::SourceHandler::pgTAP`. It is not a PostgreSQL extension and does not execute SQL itself.

Its execution chain is:

`pg_prove` → `TAP::Parser::SourceHandler::pgTAP` → `psql` → PostgreSQL/pgTAP → TAP output → `TAP::Parser`/`TAP::Harness`.

This architecture separates database execution from test-result interpretation. PostgreSQL evaluates SQL and emits TAP; the Perl harness verifies assertion counts, interprets pass/fail results and diagnostics, aggregates files, and produces a process exit status suitable for automation.

The tool supports both pgTAP execution models:

```
# SQL-script tests
pg_prove --dbname testdb --ext .sql tests/

# Functions already loaded into the database
pg_prove --dbname testdb --runtests

# Restrict function discovery to a schema and name pattern
pg_prove --dbname testdb \
  --schema test_suite \
  --match '^test_'
```

`--schema` and `--match` imply `--runtests`. This function-based mode invokes pgTAP's database-resident `runtests()` and presents its results to the harness as a single logical test source. It does not individually schedule those database functions as separate harness jobs.

Primary documentation: [https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove](https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org+1



### 3.2 Discovery, configuration, and connection control

`pg_prove` can accept individual files or discover scripts within directories.

The default discovered test-file suffix is `.pg`; `--ext .sql` includes SQL files, and multiple `--ext` options permit additional pgTAP-specific suffixes. `--recurse` enables recursive directory traversal.

Database connectivity follows `psql` and libpq conventions. This permits use of `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, password files, and PostgreSQL service files, while command-line flags override the relevant connection settings.

| Option                                       | Capability                            | Consequential detail                                                             |
| -------------------------------------------- | ------------------------------------- | -------------------------------------------------------------------------------- |
| `--dbname`, `--username`, `--host`, `--port` | Select test database connection       | Supports remote servers and nondefault ports                                     |
| `--psql-bin`                                 | Select the `psql` executable          | Useful where multiple PostgreSQL client versions are installed                   |
| `--pset OPTION=VALUE`                        | Configure psql output formatting      | Changes how SQL results are rendered                                             |
| `--set VAR=VALUE`                            | Define psql variables                 | These are client-side `psql` variables, not PostgreSQL configuration parameters  |
| `--ext`, `--recurse`                         | Discover SQL test scripts             | Supports heterogeneous test-file layouts                                         |
| `--rc`, `--norc`                             | Control `prove` configuration loading | `.proverc` supports standard `prove` options, not every pg_prove-specific option |

The last distinction matters: a psql variable supplied with `--set` does not change server behavior unless the SQL test script explicitly consumes it.

Similarly, pg_prove connects to an existing database and assumes that the necessary schema, functions, and pgTAP extension are available. It does not provision the server, construct the application schema, or automatically install pgTAP.

Source: [https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove](https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org+2



### 3.3 Parallel execution and its isolation boundary

`--jobs N` runs multiple test-script jobs concurrently.

```
pg_prove --ext .sql --jobs 4 tests/
```

This is file-level concurrency managed by the TAP harness. Multiple `psql` processes may execute simultaneously against the same PostgreSQL database.

Parallel execution is not equivalent to test isolation.

Even when each SQL script uses `BEGIN` and `ROLLBACK`, concurrent sessions can still contend over locks, shared schema objects, connections, global resources, and nontransactional state such as sequence values.

The resulting design choices are materially different:

| Test characteristics                               | Implication for concurrency                                   |
| -------------------------------------------------- | ------------------------------------------------------------- |
| Read-only tests over stable data                   | Generally more amenable to parallel execution                 |
| Independent transactional writes                   | Can execute concurrently when locking and shared state permit |
| Tests creating or altering common objects          | Risk collisions, blocking, and nondeterministic behavior      |
| Cluster-wide administrative operations             | May require serialized execution or distinct clusters         |
| xUnit functions inside one `runtests()` invocation | Remain a single harness execution unit                        |

If stronger isolation is required, each worker can be given a separate database or cluster through external orchestration. That is not an intrinsic feature of `--jobs`.

This distinction also explains why `pg_virtualenv` and `pg_prove` are complementary: the former can provision isolated servers, while the latter schedules tests. Neither automatically establishes a separate cluster per harness worker.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org+1



### 3.4 Stateful test scheduling and failure-oriented iteration

An easily overlooked capability is pg_prove's persistent execution history, implemented through the `prove` state mechanism.

With `--state save`, the harness records test-file results and execution metadata in a local `.pg_prove` file. Subsequent invocations can select or order tests according to that recorded history.

| State selector    | Behavior                                                    |
| ----------------- | ----------------------------------------------------------- |
| `failed`          | Execute files that failed in the saved run                  |
| `failed,save`     | Rerun failures and update the state                         |
| `failed,all,save` | Run the entire suite with previous failures first           |
| `hot,all,save`    | Prioritize the most recently failing files                  |
| `slow`            | Order tests from slowest to fastest using recorded timing   |
| `fresh`           | Select files modified since the last recorded run           |
| `new` / `old`     | Order by file modification time                             |
| `last`            | Reproduce the previously recorded test-file selection/order |
| `todo`            | Select tests associated with TODO results                   |

For example:

```
# Save an initial run
pg_prove --ext .sql --state save tests/

# Concentrate on previous failures
pg_prove --ext .sql --state failed,save tests/

# Execute all files, prioritizing slow tests
pg_prove --ext .sql --jobs 4 --state slow,all,save tests/
```

Prioritizing slow files can improve parallel scheduling by placing longer jobs earlier, reducing the possibility that one expensive test remains after most workers finish. This is a scheduling opportunity, not a guaranteed speedup.

The state is based on test sources and recorded outcomes; it does not perform semantic dependency analysis or determine which database tests are affected by a schema change.

Documentation: [https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove](https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org+1



### 3.5 Reporting, diagnostics, and extension points

The reporting interface is substantially richer than a single pass/fail summary.

`--verbose` exposes individual TAP records, `--failures` focuses attention on failing assertions, and `--comments` exposes diagnostic messages. `--directives` can highlight `SKIP` and `TODO` results.

`--parse` reports TAP parsing errors, making it useful when SQL output does not conform to TAP expectations. `--normalize` renders parser-normalized TAP in verbose output.

`--shuffle` and `--reverse` change file execution order. Random-order execution can expose otherwise hidden dependencies between test scripts, although it does not guarantee their detection.

For preserving or integrating results, `--archive` records TAP output in `.tar` or `.tar.gz` archives, while `--formatter` and `--harness` select custom Perl formatter or harness classes.

These extension points allow TAP results to participate in broader reporting infrastructure without modifying PostgreSQL's assertion functions. They do not inherently provide a JUnit XML reporter; that depends on the selected harness or formatter implementation.

One important failure-handling option is `--ignore-exit`. Normally, an abnormal `psql` exit can fail the test source even if its emitted TAP assertions appeared successful. `--ignore-exit` suppresses this process-status check and therefore risks masking serious database or script errors.

Source: [https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove](https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org+2



### 3.6 The Perl TAP source-handler integration

`TAP::Parser::SourceHandler::pgTAP` is independently useful beyond the `pg_prove` executable.

It implements source recognition through `can_handle()` and constructs a PostgreSQL-executing iterator through `make_iterator()`. The handler accepts configuration for connection details, the `psql` binary, and test-file suffixes.

It can be registered alongside Perl's ordinary TAP source handler. For example, the standard `prove` command can execute both Perl `.t` tests and PostgreSQL `.pg` tests in one harness:

```
prove --source Perl \
      --ext .t --ext .pg \
      --source pgTAP \
      --pgtap-option suffix=.pg
```

This can also be integrated through Perl's `Module::Build`, including its `tap_harness_args` configuration.

A less obvious feature is the handler's support for sources prefixed with `pgsql:`, where the remainder is interpreted as SQL. This is a lower-level source-handler capability, not the normal file-oriented pg_prove interface.

This integration makes pgTAP a participant in Perl's general TAP ecosystem without forcing all tests to be implemented in Perl.

Documentation: [https://metacpan.org/pod/TAP::Parser::SourceHandler::pgTAP](https://metacpan.org/pod/TAP::Parser::SourceHandler::pgTAP?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org



### 3.7 Companion utility: `pg_tapgen`

The same CPAN distribution includes `pg_tapgen`, a schema-test generator.

It connects to an existing PostgreSQL database, introspects its structure, and generates pgTAP assertions intended to validate that structure:

```
pg_tapgen --dbname reference_db > schema_test.sql
```

Its options include excluding selected schemas, directing generated files to a directory, and controlling whether the output includes `CREATE EXTENSION pgtap`.

Its status deserves qualification: upstream explicitly describes the utility as experimental. It also requires the Perl `DBI` and `DBD::Pg` packages, which are not automatically checked by the distribution's build process.

Generated assertions encode the current database structure as a reference. They do not independently establish that the structure is desirable or correct. Nonetheless, they offer a way to obtain broad schema-regression coverage without manually authoring each catalog assertion.

Documentation: [https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_tapgen](https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_tapgen?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org



## 4. pg_virtualenv — disposable PostgreSQL clusters

### 4.1 What it actually virtualizes

`pg_virtualenv` is a shell utility distributed with Debian's `postgresql-common` infrastructure. It creates a temporary PostgreSQL server environment, executes a supplied command, and removes the environment when that command exits.

Unlike a PostgreSQL emulator, it runs the real server binaries. Unlike a container or virtual machine, it does not inherently isolate the operating system. Unlike transaction-based database testing, it disposes of an entire cluster.

The standard lifecycle is:

1. Select one or more installed PostgreSQL server versions.
2. Create temporary PostgreSQL clusters named `regress`.
3. Initialize the databases and start the server processes.
4. Configure PostgreSQL connection environment variables.
5. Execute the requested command or open a shell.
6. Report relevant diagnostics on failure and remove the created clusters.

Consequently, it is useful for SQL tests, extension tests, migration verification, version-specific checks, and other operations where database state should be discarded afterward.

Official man page: [https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html](https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://manpages.debian.org\&sz=32)

Debian Manpages+1



### 4.2 Cluster provisioning and environment propagation

With no version specified, pg_virtualenv selects the newest PostgreSQL server version installed locally.

```
# Open a shell connected to a new temporary cluster
pg_virtualenv

# Run one command against a temporary cluster
pg_virtualenv -- psql -c 'SELECT version()'
```

For the normal single-cluster case, it exports:

| Variable     | Meaning                                                                  |
| ------------ | ------------------------------------------------------------------------ |
| `PGHOST`     | Host used to reach the temporary server                                  |
| `PGPORT`     | Allocated port, beginning with the first available port at or above 5432 |
| `PGDATABASE` | Default database, normally `postgres`                                    |
| `PGUSER`     | Database user created for the temporary environment                      |
| `PGPASSWORD` | Generated password for that user                                         |
| `PGVERSION`  | Selected PostgreSQL major version                                        |

The implementation also configures PostgreSQL's service-file environment and, for a single version, `PG_CONFIG` in the inspected Debian source.

The crucial benefit is transparent client compatibility. Applications using libpq-compatible connection conventions can inherit the environment without being rewritten to understand pg_virtualenv.

This includes `psql`, `pg_prove`, many PostgreSQL language drivers, and other command-line tools that honor standard PostgreSQL connection variables.

Port selection is dynamic unless `PGPORT` is set explicitly for a single cluster. This avoids assuming that the standard PostgreSQL port is unused.

Source: [https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html](https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://manpages.debian.org\&sz=32)

Debian Manpages+1



### 4.3 Multi-version PostgreSQL testing

A distinctive capability is running multiple PostgreSQL server versions within one virtual environment.

```
# Versions must already be installed
pg_virtualenv -v '17 18' -- sh -eu -c '
  psql "service=17" -X -v ON_ERROR_STOP=1 -c "SELECT version()"
  psql "service=18" -X -v ON_ERROR_STOP=1 -c "SELECT version()"
'
```

Alternatively, `-a` selects all installed PostgreSQL server versions.

Each version receives a separate cluster and port, with a cluster identifier of the form `<version>/regress`.

In multi-version mode, `PGPORT` and `PGVERSION` are not exported, because neither could unambiguously identify one server.

Instead, a client can select a cluster using a generated libpq service entry such as `service=18`. Debian's PostgreSQL wrapper tools also recognize `PGCLUSTER=18/regress`.

These are not identical mechanisms: `PGCLUSTER` is part of Debian's PostgreSQL wrapper infrastructure; service connection strings are handled by libpq.

The utility provisions multiple server versions, but does not itself execute a test suite separately against each one. That iteration remains the responsibility of the supplied command or an adjacent orchestration tool.

This distinction allows compatibility testing against actual PostgreSQL execution semantics, without maintaining a long-lived database instance for every version.

Documentation: [https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html](https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://manpages.debian.org\&sz=32)

Debian Manpages+1



### 4.4 Server and initialization configuration

pg_virtualenv exposes separate controls for cluster creation, database initialization, and server configuration.

| Option          | Configuration scope                                                   |
| --------------- | --------------------------------------------------------------------- |
| `-c 'options'`  | Additional arguments to `pg_createcluster`                            |
| `-i 'options'`  | Additional arguments passed through to `initdb`                       |
| `-o guc=value`  | PostgreSQL server configuration parameter                             |
| `-v 'versions'` | Explicit PostgreSQL version selection                                 |
| `-a`            | All installed PostgreSQL versions                                     |
| `-t`            | Force temporary-directory cluster placement even when invoked as root |
| `-s`            | Open an interactive shell after the supplied command fails            |
| `-p package`    | Expose staged extension files from a Debian package build             |

The `-o` option is materially different from pg_prove's `--set`: pg_virtualenv changes the temporary server's PostgreSQL configuration, while pg_prove sets variables for `psql`.

For example:

```
pg_virtualenv -v 18 \
  -o max_connections=50 \
  -o log_min_duration_statement=0 \
  -- sh -c 'psql -c "SHOW max_connections"'
```

These parameters apply to the disposable instance, not to an existing production cluster.

The ability to supply `initdb` options also makes it possible to examine PostgreSQL behavior under alternate initialization conditions, subject to what the installed PostgreSQL version supports.

Primary source: [https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html](https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://manpages.debian.org\&sz=32)

Debian Manpages



### 4.5 Non-root operation and cleanup semantics

pg_virtualenv has two materially different filesystem-management modes.

Non-root mode creates a temporary working directory containing cluster data, configuration, logs, and connection-related files. The script exports `PG_CLUSTER_CONF_ROOT` and `PGSYSCONFDIR` so PostgreSQL's Debian management tools use that private configuration tree.

Root mode, by default, creates its clusters under conventional system configuration locations such as `/etc/postgresql`. The implementation refuses to overwrite an existing cluster with the intended `regress` name and saves/restores its PostgreSQL service configuration as necessary.

`-t` forces temporary-directory operation even when invoked as root.

In the inspected implementation, cleanup uses shell exit/signal traps and checks for a marker identifying clusters created by pg_virtualenv before dropping them. This provides protection against inadvertently removing an unrelated cluster with the same name.

It remains important not to equate this mechanism with crash-proof cleanup. An uncatchable termination, a host crash, or interrupted filesystem operations can leave temporary artifacts behind.

The detailed source inspection was against Debian `postgresql-common` 278; the release-293 manual confirms the public behavior, but internal implementation details should not be assumed unchanged without inspecting that exact source revision.

Source code: [https://sources.debian.org/src/postgresql-common/278/pg_virtualenv/](https://sources.debian.org/src/postgresql-common/278/pg_virtualenv/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sources.debian.org\&sz=32)

Debian Sources+1



### 4.6 Fast initialization and durability tradeoffs

The inspected Debian implementation initializes disposable clusters using `fsync=off` and, on supported versions, `initdb --nosync`.

These choices reduce the work required to establish and operate a short-lived test database, particularly filesystem synchronization during initialization and transactional writes.

They are appropriate to the utility's core assumption that the entire environment will be thrown away after the command completes.

However, they introduce a consequential limitation: a default pg_virtualenv environment should not be assumed to reproduce production durability behavior.

Tests of crash recovery, write-ahead-log durability, synchronization guarantees, or failure handling under power loss require a deliberately configured environment. A database engine running under deliberately relaxed durability settings is still real PostgreSQL, but it is not equivalent to a durable production configuration for every property being tested.

This observation is grounded in the inspected v278 implementation; the corresponding settings in a specific later package revision should be verified before relying on them.

Source: [https://sources.debian.org/src/postgresql-common/278/pg_virtualenv/](https://sources.debian.org/src/postgresql-common/278/pg_virtualenv/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sources.debian.org\&sz=32)

Debian Sources



### 4.7 Extension development without system-wide installation

The `-p package` option is a particularly valuable but easily overlooked feature.

It supports testing PostgreSQL extensions from files staged inside a Debian package build tree—typically `debian/<package>/`—without first installing those files into the system PostgreSQL directories.

The utility adjusts PostgreSQL's extension and shared-library search paths so a disposable cluster can load the staged build artifacts.

Version-dependent behavior matters:

- PostgreSQL 18 and later use the `extension_control_path` configuration mechanism.
- Earlier supported versions use Debian-specific `extension_destdir` functionality where available.
- `dynamic_library_path` is adjusted for staged compiled extension libraries.

This mechanism is specific to Debian PostgreSQL packaging conventions and compatible server builds. It should not be assumed to work identically with arbitrary upstream PostgreSQL binaries or a non-Debian filesystem layout.

The distinction is especially important for compiled extensions: the PostgreSQL major version, server headers, built library, control file, and SQL installation scripts must be compatible.

Source: [https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html](https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://manpages.debian.org\&sz=32)

Debian Manpages+1



### 4.8 Integration with pg_buildext, PGXS, and autopkgtest

pg_virtualenv also participates in Debian's PostgreSQL extension packaging and verification machinery.

The companion `pg_buildext` utility builds and installs PostgreSQL extensions for supported major versions. Its `installcheck` action invokes regression tests inside pg_virtualenv.

The wider workflow can include `pg_regress`, PGXS `make installcheck`, and Debian `autopkgtest`, without involving pgTAP or pg_prove at all.

`pg_buildext` also exposes `virtualenv` and `psql` actions, and accepts additional pg_virtualenv arguments via `PG_VIRTUALENV_ARGS`.

This is a useful architectural boundary: pg_virtualenv is a general PostgreSQL test-environment utility, not a pgTAP-specific dependency.

It can host TAP-based tests, PostgreSQL's native regression tests, migration checks, or arbitrary commands that need a temporary server.

Documentation: [https://manpages.debian.org/unstable/postgresql-common/pg_buildext.1.en.html](https://manpages.debian.org/unstable/postgresql-common/pg_buildext.1.en.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://manpages.debian.org\&sz=32)

Debian Manpages+1



### 4.9 Failure diagnosis and operational isolation

If the supplied command fails, pg_virtualenv displays the tail of PostgreSQL server logs. The inspected source also looks for server core dumps and, when `gdb` is available, attempts to generate diagnostic backtraces.

The `-s` option opens a shell inside the environment after a failed command, before cleanup. This is useful for interactive investigation of database state, catalogs, logs, and configuration; it is generally unsuitable for unattended CI processes because it can wait for interactive input.

Optional environment controls permit stronger process-related isolation:

`PG_VIRTUALENV_NEWPID=yes` re-executes through `newpid`, while `PG_VIRTUALENV_UNSHARE=<flags>` invokes Linux `unshare` with the selected namespace flags.

These are optional mechanisms, not proof of an automatically isolated container. They depend on the relevant executables, permissions, and kernel features.

In particular, pg_virtualenv's normal operation should not be considered a security sandbox for untrusted database extensions or arbitrary shell commands. The PostgreSQL server and test process still execute within the host operating system's applicable permissions.

Sources: [https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html](https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html?utm_source=chatgpt.com) and [https://sources.debian.org/src/postgresql-common/278/pg_virtualenv/](https://sources.debian.org/src/postgresql-common/278/pg_virtualenv/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://manpages.debian.org\&sz=32)

Debian Manpages+1



## 5. Composing the three tools

### 5.1 A disposable, end-to-end SQL testing workflow

The simplest composition is to let pg_virtualenv own the server lifecycle, use ordinary `psql` commands to initialize the database, and delegate assertions and reporting to pg_prove.

```
# Assumes PostgreSQL 18 server binaries, pgTAP extension files,
# and the pg_prove command are already installed.
# schema.sql and tests/ are illustrative project inputs.

pg_virtualenv -v 18 -- sh -eu -c '
    psql -X -v ON_ERROR_STOP=1 -f schema.sql

    psql -X -v ON_ERROR_STOP=1 \
      -c "CREATE EXTENSION IF NOT EXISTS pgtap"

    pg_prove --ext .sql --verbose tests/
'
```

In this arrangement, schema construction and database testing occur within the same temporary PostgreSQL cluster. pg_prove inherits the generated connection variables from pg_virtualenv, so no port discovery or explicit connection-string construction is necessary.

When the shell exits, pg_virtualenv reports the command's failure status, provides server diagnostics where applicable, and removes the temporary cluster.

This composition provides three distinct forms of correctness control:

| Layer          | Mechanism                | Scope of protection                                             |
| -------------- | ------------------------ | --------------------------------------------------------------- |
| Assertion      | pgTAP SQL functions      | Evaluate expected database properties                           |
| Test execution | pg_prove and TAP harness | Detect assertion failures, invalid TAP and abnormal execution   |
| Environment    | pg_virtualenv            | Discard database objects and server state after the overall run |

These properties are complementary. For example, temporary-cluster disposal does not detect an incorrect query result, and a passing SQL assertion does not establish that the database is safe to reuse after other tests.

For xUnit-style testing, the initialization stage must also load the test functions, after which pg_prove can use `--runtests` instead of loading SQL test scripts.

The principal prerequisite is that the selected PostgreSQL server must have access to the pgTAP extension files. The `CREATE EXTENSION` SQL command alone cannot supply files missing from the server installation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org+1



### 5.2 Three different levels of isolation

The tools expose an important distinction between subtransactions, transactions, and clusters.

| Isolation level    | Typical mechanism                       | What it does not guarantee                                                         |
| ------------------ | --------------------------------------- | ---------------------------------------------------------------------------------- |
| Subtransaction     | pgTAP `runtests()` per-test rollback    | Reversing sequence increments or external side effects                             |
| Transaction        | `BEGIN` / `ROLLBACK` within SQL scripts | Isolation from concurrently executing scripts and every nontransactional operation |
| Disposable cluster | pg_virtualenv                           | Isolation from the host OS, network, or other external services                    |

A useful general architecture is to use transaction rollback for fast test-local cleanup and disposable clusters for whole-suite isolation. But database ownership, locks, global objects, and external integrations still determine whether concurrent tests are independent.

Notably, a cluster shared by all tests in one pg_prove invocation is still a shared cluster. pg_virtualenv does not automatically create an independent PostgreSQL server for each `--jobs` worker.

### 5.3 Compatibility and testing dimensions

The tools can be combined to exercise several independent dimensions of PostgreSQL behavior.

| Dimension                     | Supported approach                           | Remaining responsibility                                         |
| ----------------------------- | -------------------------------------------- | ---------------------------------------------------------------- |
| PostgreSQL major version      | pg_virtualenv `-v` or `-a`                   | Run the desired suite against each selected server               |
| Database schema compatibility | pgTAP catalog and signature assertions       | Define the expected database contract                            |
| Behavioral SQL compatibility  | Query and exception assertions               | Construct representative inputs and expected results             |
| Security configuration        | pgTAP privilege and RLS metadata assertions  | Test effective authorization under appropriate roles             |
| Parallel workload correctness | pg_prove `--jobs`                            | Control shared state and verify concurrency semantics            |
| Server configuration          | pg_virtualenv `-o` and `-i`                  | Choose relevant configurations and interpret differences         |
| Extension compatibility       | pg_virtualenv `-p`, pg_buildext              | Build the extension for each required server version             |
| Repeatability                 | Disposable clusters plus transactional tests | Ensure test fixtures and external dependencies are deterministic |

An important difference is that these mechanisms verify observed behavior under selected configurations. They do not constitute exhaustive proof of PostgreSQL compatibility, schema correctness, or security.

### 5.4 Relationship to PostgreSQL's native regression infrastructure

PostgreSQL already has several testing mechanisms that overlap with these tools but serve different purposes.

| Mechanism                 | Primary approach                                      | Distinguishing characteristic                                                                           |
| ------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| pgTAP + pg_prove          | SQL assertions emitting TAP                           | Fine-grained, declarative assertions over database behavior and metadata                                |
| pg_regress                | Compare query-output files with expected-output files | Established SQL regression testing, especially for PostgreSQL extensions                                |
| PostgreSQL core TAP tests | Perl TAP tests using PostgreSQL's test infrastructure | Suitable for server processes, command-line tools, replication, recovery, and multi-node test scenarios |
| pg_virtualenv             | Temporary PostgreSQL cluster management               | Supplies database infrastructure; does not prescribe an assertion protocol                              |

PostgreSQL's own TAP tests are not the same thing as pgTAP. They use Perl's TAP infrastructure and can create their own temporary server instances. They do not require the pgTAP SQL extension.

Likewise, `pg_regress` is often a more natural fit when verifying the full textual output of a SQL regression script against an established reference file. pgTAP is especially expressive where the expected result is a relational, structural, or behavioral invariant rather than a complete output transcript.

For cases involving replication, process crashes, authentication handshakes, or physical recovery, PostgreSQL's process-oriented test infrastructure may provide controls that SQL-level assertions alone cannot.

Official PostgreSQL references:

- Regression test execution: [https://www.postgresql.org/docs/18/regress-run.html](https://www.postgresql.org/docs/18/regress-run.html?utm_source=chatgpt.com)
- Output comparison semantics: [https://www.postgresql.org/docs/18/regress-evaluation.html](https://www.postgresql.org/docs/18/regress-evaluation.html?utm_source=chatgpt.com)
- Core PostgreSQL TAP tests: [https://www.postgresql.org/docs/18/regress-tap.html](https://www.postgresql.org/docs/18/regress-tap.html?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org+2

## 6. Important limitations and architectural tradeoffs

The strongest benefits of this toolset come from avoiding unnecessary custom machinery: bespoke catalog introspection, relational-result comparison, TAP parsing, failure-history scheduling, and temporary PostgreSQL cluster lifecycle management.

Its limits are equally important.

Database-native testing is not complete application testing. pgTAP can verify SQL-visible behavior and database metadata directly, but it does not replace tests that exercise ORM behavior, connection-pool failures, external service coordination, or application-specific transaction boundaries.

TAP is a reporting protocol, not an execution sandbox. pg_prove understands TAP and coordinates jobs; database lifecycle management and state isolation remain separate concerns.

Concurrency can invalidate apparently independent tests. Transaction rollback does not eliminate lock contention or all shared-state effects, and increasing `--jobs` can expose assumptions about test ordering.

Disposable clusters have initialization costs. pg_virtualenv must create and start real PostgreSQL servers. That startup work can be worthwhile for stronger isolation, but a persistent test server may be more efficient for frequent small test runs. The tradeoff depends on setup cost, fixture complexity, and how much isolation is needed.

Platform support is asymmetric. pgTAP is a PostgreSQL extension, pg_prove is a portable Perl-based client tool, and pg_virtualenv depends specifically on Debian-style PostgreSQL cluster-management infrastructure. Availability of one does not imply availability of the others.

Test environments do not automatically reproduce production settings. Server version, extensions, collations, configuration, privileges, data distributions, and durability settings can all affect behavior. A disposable real PostgreSQL cluster is more faithful than an SQL emulator, but it is still only as representative as its configuration and fixtures.

The server-side extension is not necessarily superuser-only. The published pgTAP extension control file specifies `superuser = false`, so installation privilege requirements are based on the objects created and the applicable PostgreSQL rules. In practice, the necessary permissions and server-side extension files must still be available. This is distinct from the privileges required by the particular test assertions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



## 7. Primary source reference map

| Topic                                       | Direct source                                                                                                                                                                           |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| pgTAP stable release                        | [https://pgxn.org/dist/pgtap/1.3.4/](https://pgxn.org/dist/pgtap/1.3.4/?utm_source=chatgpt.com)                                                                                         |
| pgTAP complete assertion documentation      | [https://pgxn.org/dist/pgtap/doc/pgtap.html](https://pgxn.org/dist/pgtap/doc/pgtap.html?utm_source=chatgpt.com)                                                                         |
| pgTAP source and development history        | [https://github.com/theory/pgtap](https://github.com/theory/pgtap?utm_source=chatgpt.com)                                                                                               |
| pg_prove command reference                  | [https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove](https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove?utm_source=chatgpt.com)         |
| Perl TAP source-handler integration         | [https://metacpan.org/pod/TAP::Parser::SourceHandler::pgTAP](https://metacpan.org/pod/TAP::Parser::SourceHandler::pgTAP?utm_source=chatgpt.com)                                         |
| pg_tapgen schema-test generator             | [https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_tapgen](https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_tapgen?utm_source=chatgpt.com)       |
| pg_virtualenv reference                     | [https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html](https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html?utm_source=chatgpt.com) |
| pg_virtualenv implementation, Debian v278   | [https://sources.debian.org/src/postgresql-common/278/pg_virtualenv/](https://sources.debian.org/src/postgresql-common/278/pg_virtualenv/?utm_source=chatgpt.com)                       |
| pg_buildext and Debian extension testing    | [https://manpages.debian.org/unstable/postgresql-common/pg_buildext.1.en.html](https://manpages.debian.org/unstable/postgresql-common/pg_buildext.1.en.html?utm_source=chatgpt.com)     |
| PostgreSQL native regression infrastructure | [https://www.postgresql.org/docs/18/regress.html](https://www.postgresql.org/docs/18/regress.html?utm_source=chatgpt.com)                                                               |

The most consequential distinction across the three projects is their separation of responsibilities: pgTAP defines and evaluates database assertions; pg_prove schedules and interprets those assertions; pg_virtualenv supplies and disposes of the PostgreSQL infrastructure in which they execute.

That separation makes each component independently useful, while their composition supports database testing against a real PostgreSQL engine with limited custom orchestration.

# Addendum: Advanced Capabilities and Execution Semantics of pgTAP, pg_prove, and pg_virtualenv

Research date: November 6, 2026

This addendum supplements the original technical overview with additional capabilities, implementation details, and semantic distinctions identified through subsequent upstream research. It concentrates on functionality not previously described in sufficient depth and avoids repeating the original capability inventory.

The verified release baselines are pgTAP 1.3.4, TAP::Parser::SourceHandler::pgTAP / pg_prove 3.37, and Debian postgresql-common 293. Development-branch observations and version-dependent infrastructure behavior are distinguished from published-release guarantees.

## 1. pgTAP: Advanced database-contract verification

### 1.1 PostgreSQL type-system contracts

pgTAP provides assertions over PostgreSQL's type-resolution machinery, not merely the existence of custom types. These support verification of database interfaces whose behavior depends on type coercion, domain representation, and enum ordering.

#### Cast coercion context

`cast_context_is(source_type, target_type, context[, description])` verifies the declared conversion context of a PostgreSQL cast.

PostgreSQL distinguishes three contexts:

| Context      | PostgreSQL behavior                                                                                                               |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| `implicit`   | Permits automatic coercion in expression and function/operator resolution                                                         |
| `assignment` | Permits assignment coercion when a value is stored in a target column, without generally permitting arbitrary expression coercion |
| `explicit`   | Requires an explicitly requested conversion, subject to other available type-conversion mechanisms                                |

pgTAP accepts the complete context names or the abbreviations `i`, `a`, and `e`.

```
SELECT cast_context_is(
    'integer',
    'bigint',
    'implicit',
    'Integer-to-bigint cast permits implicit coercion'
);
```

This is more consequential than a `has_cast()` assertion. A cast may continue to exist while a change to its context alters SQL expression resolution, overloaded-function selection, or assignment behavior.

The assertion checks the declared catalog relationship. PostgreSQL also has conversion mechanisms not represented as explicit `pg_cast` rows, so it should not be treated as a complete test of every possible conversion pathway.

Primary sources:

`https://pgxn.org/dist/pgtap/doc/pgtap.html`

`https://www.postgresql.org/docs/18/sql-createcast.html`

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org

#### Enum-label contracts

`enum_has_labels()` verifies the expected labels of an enum, including their order.

```
SELECT enum_has_labels(
    'public',
    'order_status',
    ARRAY['pending', 'active', 'closed'],
    'Order status enum has the expected labels'
);
```

Ordering matters because PostgreSQL enums have a defined sort order determined by their declaration and subsequent alterations. An enum migration can preserve all label names while changing the expected comparison behavior.

The assertion therefore provides a stronger schema contract than `has_enum()` or `enums_are()`, which concern object existence and inventory.

Source: `https://pgxn.org/dist/pgtap/doc/pgtap.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org



#### Domain underlying-type contracts

`domain_type_is()` and `domain_type_isnt()` check the underlying PostgreSQL type of a domain.

These functions distinguish the name of a domain from its representation. For example, changing a domain from `text` to `integer` can alter accepted values, sorting, arithmetic behavior, and casting despite preserving a domain-level name.

The assertions support schema-qualified domain and base-type names, as well as canonical type names and common PostgreSQL aliases.

```
SELECT domain_type_is(
    'public'::name,
    'postal_code',
    'pg_catalog'::name,
    'text',
    'Postal code domain uses text'
);
```

This verifies the base type, not the complete set of `CHECK`, `NOT NULL`, or default constraints associated with the domain. Those remain separate contract properties.

Source: `https://pgxn.org/dist/pgtap/doc/pgtap.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org



#### Trusted procedural languages

`language_is_trusted()` checks whether PostgreSQL considers a procedural language trusted.

This is a security-relevant catalog property because trusted languages can be made available to users who are not superusers, subject to PostgreSQL's privilege rules.

The assertion does not prove that a language implementation is safe in an absolute sense. It validates the server's declared trust classification.

Capability interaction: type, cast, domain, enum, and procedural-language assertions allow pgTAP to express a broader database compatibility contract. A migration can be tested against not only the visible schema but also the PostgreSQL resolution and execution metadata on which existing SQL depends.

Source: `https://pgxn.org/dist/pgtap/doc/pgtap.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org



### 1.2 SQL rewrite rules and relation semantics

PostgreSQL's rule system transforms statements during query rewriting. Rules are different from triggers: they operate on query representations rather than executing trigger procedures in response to individual statement or row events.

pgTAP exposes two specialized assertions in addition to rule existence and inventory checks.

`rule_is_instead(schema, relation, rule[, description])` verifies the `INSTEAD` property of a rewrite rule.

`rule_is_on(schema, relation, rule, event[, description])` verifies that a rule applies to a particular event: `SELECT`, `INSERT`, `UPDATE`, or `DELETE`. The event argument is case-insensitive and accepts single-letter abbreviations.

```
SELECT rule_is_instead(
    'public',
    'updatable_view',
    'insert_redirect'
);

SELECT rule_is_on(
    'public',
    'updatable_view',
    'insert_redirect',
    'INSERT'
);
```

Together with `has_rule()` and `rules_are()`, these assertions can verify that a relation exposes the expected rewrite configuration.

This matters especially for views and compatibility layers that redirect writes to underlying relations. Two databases can expose identical table/view names and columns but differ materially in whether writes are rewritten, rejected, or handled through other mechanisms.

The assertions validate rule metadata, not full rewrite semantics. Tests of actual insert, update, and delete behavior remain necessary when correctness depends on the rewritten statement's effects.

Source: `https://pgxn.org/dist/pgtap/doc/pgtap.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org



### 1.3 Expression-index and access-path contracts

`has_index()` is more capable than an existence-only assertion. Its overloads accept a named index, optionally accompanied by an indexed column or an array containing indexed columns and expressions.

```
SELECT has_index(
    'public',
    'customers',
    'customers_email_lower_idx',
    ARRAY['lower(email)'],
    'Customer email index uses the expected expression'
);
```

The function compares the expected index keys against PostgreSQL's representation of the index definition. This enables verification of expression indexes, including indexes created to support case-insensitive lookup, computed values, and similar operations.

`is_indexed()` provides a related but distinct contract: it verifies that the specified columns or expressions are indexed without requiring a particular index name. The specified keys or expressions must occur together in an index, rather than being satisfied independently by unrelated indexes.

| Assertion                       | Contract enforced                                                     |
| ------------------------------- | --------------------------------------------------------------------- |
| `has_index(table, index)`       | A specific named index exists                                         |
| `has_index(table, index, keys)` | That named index has the expected key specification                   |
| `is_indexed(table, keys)`       | An index containing the specified keys exists, regardless of its name |
| `index_is_partial()`            | An index is a partial index                                           |
| `index_is_type()`               | An index uses the expected access method                              |
| `is_clustered()`                | A relation is marked as clustered using the specified index           |

#### Expression representation limitations

Expression-index assertions require attention to PostgreSQL's rendered expression syntax.

The documentation specifies lowercase SQL keywords and function names, parentheses around certain nonfunction expressions, and explicit quoting of case-sensitive or unusual column names.

For example, an indexed expression involving a mixed-case column name may need to be represented as:

```
ARRAY['lower("CustomerEmail")']
```

This is not a symbolic-equivalence engine. Two semantically equivalent expressions can differ in rendered form and therefore fail an exact index-expression assertion.

Nor does an index assertion establish that PostgreSQL's planner will choose the index for a particular query. Index presence, index definition, and actual query-plan selection are separate properties.

Source: `https://pgxn.org/dist/pgtap/doc/pgtap.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org



### 1.4 Catalog relationships and additional specialized assertions

Several further pgTAP capabilities extend database-contract verification into less commonly tested PostgreSQL object families.

| Functional area       | Representative assertions                                  | Additional capability                                              |
| --------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------ |
| Operator interfaces   | `has_operator`, `has_leftop`, `has_rightop`                | Validate binary and unary operator definitions and type signatures |
| Inheritance           | `is_descendent_of`, `isnt_descendent_of`, `is_ancestor_of` | Verify inheritance relationships between relations                 |
| Table clustering      | `is_clustered`                                             | Check clustering metadata associated with an index                 |
| Column privileges     | `any_column_privs_are`, `column_privs_are`                 | Distinguish column-level privileges from table-level authorization |
| Foreign-data wrappers | `fdw_privs_are`, `server_privs_are`                        | Verify privileges assigned to foreign-data access infrastructure   |
| Procedural languages  | `language_is_trusted`, `language_privs_are`                | Verify language trust metadata and usage privileges                |
| Tablespaces           | `tablespace_privs_are`, ownership assertions               | Test database storage-administration permissions                   |
| Operator classes      | `opclasses_are` and ownership-related assertions           | Verify index operator-class inventory and ownership                |

These assertions are useful for object-model coverage that would otherwise require application-defined queries over PostgreSQL system catalogs.

However, catalog assertions are evidence about declared database structure and configuration. They do not necessarily establish effective runtime behavior.

For instance, a privilege assertion can demonstrate an expected grant configuration, while effective access may also depend on role inheritance, security-definer functions, ownership, and row-level security.

Similarly, validating an operator's signature does not prove its algebraic properties, such as commutativity or associativity.

Source: `https://pgxn.org/dist/pgtap/doc/pgtap.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org



### 1.5 Scope and completeness of catalog-inventory assertions

The earlier overview described functions such as `tables_are()`, `functions_are()`, and `schemas_are()` as exact-inventory assertions. This description is correct only when interpreted within each function's documented scope.

Exactness does not necessarily mean every matching object in the database or cluster.

`schemas_are()` excludes PostgreSQL system schemas and `information_schema`.

When called without an explicit schema, `tables_are()` and `functions_are()` examine objects visible through the current `search_path`, excluding system catalogs. Explicit schema arguments provide a different scope.

A second distinction concerns overloaded functions.

`functions_are()` checks function and procedure names. It is not a complete signature-level contract over every overload.

For example, an assertion expecting a function named `calculate` does not independently guarantee that all intended argument-type combinations are present or that unexpected overloads are absent.

Signature-sensitive assertions such as `has_function()`, `function_returns()`, `function_lang_is()`, and `volatility_is()` provide the additional precision needed for specific routines.

Likewise, object-category distinctions matter. `tables_are()`, `foreign_tables_are()`, `views_are()`, and `materialized_views_are()` address different PostgreSQL relation categories.

The architectural consequence is that catalog-inventory assertions are most expressive when their scopes are explicit and when exact-name checks are combined with signature- or attribute-level checks for properties that matter.

Sources:

`https://pgxn.org/dist/pgtap/doc/pgtap.html`

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org+1

### 1.6 Distinct test-function execution semantics

The earlier overview introduced `do_tap()` and `runtests()`, but the distinction between them is significant enough to qualify their interchangeable-looking interfaces.

`do_tap()` discovers and executes functions that emit TAP. It does not automatically establish the xUnit fixture lifecycle or per-test rollback behavior of `runtests()`.

Its callers supply their own test plan and finalization:

```
SELECT plan(12);
SELECT * FROM do_tap('test_schema'::name);
SELECT * FROM finish();
```

By comparison, `runtests()` provides its own planning, setup/teardown discovery, TAP subtests, and test-local rollback.

When only a schema name is supplied, it is important to cast it to `name`, because the single-argument text overload is interpreted as a function-name pattern.

The documentation also describes function-name diagnostics during `do_tap()` execution, controlled by PostgreSQL's `client_min_messages` configuration.

#### Test-plan completeness

Database-generated assertions introduce an additional failure mode. Consider an SQL query that generates one assertion per row in a fixture table. If the table unexpectedly contains zero rows, the query can produce zero assertions without emitting a failed assertion.

A declared test plan can detect a missing expected count when `finish()` is called. By contrast, `no_plan()` cannot independently establish how many assertions were intended.

This distinction becomes important for tests that rely on generated SQL, catalog queries, or set-returning functions.

A fixed plan is not a substitute for checking the expected identities of test cases, but it provides an additional structural guarantee over execution completeness.

Source: `https://pgxn.org/dist/pgtap/doc/pgtap.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org



### 1.7 pgTAP's separately published extension components

The pgTAP 1.3.4 distribution metadata publishes three extension artifacts:

| Extension      | Published role                     |
| -------------- | ---------------------------------- |
| `pgtap`        | Unit testing for PostgreSQL        |
| `pgtap-core`   | Unit testing for PostgreSQL        |
| `pgtap-schema` | Schema unit testing for PostgreSQL |

This packaging exposes a distinction between the primary extension and separate core/schema extension artifacts.

The metadata identifies the associated files as `sql/pgtap.sql`, `sql/pgtap-core.sql`, and `sql/pgtap-schema.sql`.

The conventional entry point remains `CREATE EXTENSION pgtap`. The published metadata alone does not establish that either subordinate artifact is a complete independent test framework, nor does it fully specify their installation dependency relationships.

They should therefore be understood as distribution components whose more precise installation semantics are determined by the relevant control and installation scripts.

Source: `https://api.pgxn.org/src/pgtap/pgtap-1.3.4/META.json`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://api.pgxn.org\&sz=32)

api.pgxn.org



## 2. pg_prove: Execution mechanics, source handling, and test-generation capabilities

### 2.1 Exact `psql` invocation and output normalization

The most important additional detail about pg_prove is that its underlying `TAP::Parser::SourceHandler::pgTAP` implementation deliberately configures `psql` to produce output suitable for TAP parsing.

In release 3.37, the source handler constructs a command beginning with the following options:

```
psql \
  --no-psqlrc \
  --no-align \
  --quiet \
  --pset pager=off \
  --pset tuples_only=true \
  --set ON_ERROR_STOP=1
```

Connection arguments, additional print settings, psql variables, and the test source are subsequently appended.

The source handler therefore establishes a controlled client-execution environment rather than relying on the user's normal interactive `psql` configuration.

| Configuration      | Consequence                                                                       |
| ------------------ | --------------------------------------------------------------------------------- |
| `--no-psqlrc`      | Prevents startup configuration from `.psqlrc` files from modifying test execution |
| `--no-align`       | Removes aligned table formatting from query output                                |
| `--quiet`          | Suppresses routine client messages                                                |
| `pager=off`        | Prevents interactive pagination from intercepting the TAP stream                  |
| `tuples_only=true` | Removes column headings and row-count footers                                     |
| `ON_ERROR_STOP=1`  | Causes unexpected SQL errors to terminate script processing                       |

These controls make TAP output more reliable as a machine-readable protocol.

The command-construction code also permits caller-supplied `pset` and `set` values after these defaults. Consequently, explicit overrides can change the expected output behavior or SQL error handling.

This distinction is important when treating pg_prove as an execution framework: its reliability depends partly on maintaining the output and error conventions expected by the TAP parser.

Source: `https://github.com/theory/tap-parser-sourcehandler-pgtap/blob/develop/lib/TAP/Parser/SourceHandler/pgTAP.pm`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 2.2 Independent SQL execution and TAP evaluation failures

pg_prove has two distinct failure-detection channels.

SQL execution failures arise when `psql` cannot complete a script successfully, such as when it encounters an unexpected PostgreSQL exception with `ON_ERROR_STOP` enabled.

TAP assertion failures arise when SQL executes successfully but the assertions report unsuccessful results, incorrect plans, or malformed TAP.

These are not equivalent:

| Situation                                             | PostgreSQL / psql behavior  | TAP interpretation                                               |
| ----------------------------------------------------- | --------------------------- | ---------------------------------------------------------------- |
| A pgTAP assertion reports `not ok`                    | SQL may complete normally   | The test fails                                                   |
| SQL throws an unexpected error                        | `psql` exits unsuccessfully | The test source fails, potentially with incomplete TAP           |
| SQL produces malformed TAP                            | SQL may complete normally   | The parser can report a protocol error                           |
| SQL completes but emits fewer assertions than planned | Process may succeed         | TAP plan mismatch fails                                          |
| A test script omits transaction rollback              | SQL may complete normally   | TAP cannot determine whether unwanted database changes persisted |

The `--ignore-exit` option suppresses the usual failure associated with an abnormal script exit status. It does not convert failed TAP assertions into passing assertions.

Its use therefore changes the interpretation of SQL execution failures and can conceal errors that prematurely terminated a script.

A related distinction concerns transaction control. pg_prove does not automatically surround file-based SQL tests with a transaction. The standard SQL-script pattern remains:

```
BEGIN;

SELECT plan(1);
SELECT pass('Example assertion');

SELECT * FROM finish();

ROLLBACK;
```

With `ON_ERROR_STOP=1`, an unexpected error can terminate the script before its explicit `ROLLBACK` statement executes. PostgreSQL then rolls back the open transaction when the database session ends. This protection applies to transactional database changes, not nontransactional effects.

Source: `https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org



### 2.3 Test-file session boundaries

The source handler's `make_iterator()` implementation selects between two `psql` invocation forms:

```
--file <path>
--command <SQL>
```

Ordinary test files use `--file`. Inline sources beginning with `pgsql:` use `--command`.

Each iterator launches a separate `psql` process. For conventional file-based execution, each test file therefore has its own PostgreSQL database session.

This has several consequences:

| State or resource                 | Across separate test files                    |
| --------------------------------- | --------------------------------------------- |
| Temporary tables                  | Not shared automatically                      |
| Prepared statements               | Not shared automatically                      |
| Session-level GUC settings        | Not inherited from a previous file            |
| Session-level advisory locks      | Do not remain owned by a completed session    |
| Committed database changes        | Remain visible to subsequent sessions         |
| Nontransactional sequence changes | Can remain observable                         |
| Server-level configuration        | Shared when files connect to the same cluster |

This session model permits independent execution of many test files but also constrains the use of session-scoped fixtures.

For example, a temporary table created in one SQL test file cannot ordinarily be used by the next file, even if pg_prove schedules those files sequentially against the same database.

#### Search-path configuration

The source handler does not provide an implemented general-purpose `search_path` configuration key. A proposed mechanism appears in the source as commented-out code.

If pgTAP is installed in a dedicated schema, test scripts must make its functions visible through an appropriate mechanism.

```
SET search_path = public, tap, pg_catalog;
```

Alternatives include explicit schema qualification or appropriate server/session configuration.

Because `--no-psqlrc` is enabled, relying on a local `.psqlrc` file to establish the search path will not work under the default handler invocation.

Source: `https://github.com/theory/tap-parser-sourcehandler-pgtap/blob/develop/lib/TAP/Parser/SourceHandler/pgTAP.pm`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 2.4 Source-handler selection and inline SQL execution

`TAP::Parser::SourceHandler::pgTAP` implements the standard Perl TAP source-handler interface through `can_handle()` and `make_iterator()`.

Its `can_handle()` method returns a confidence score that allows Perl's TAP infrastructure to choose among registered handlers.

For version 3.37, the documented scores are:

| Source type                                   | Confidence |
| --------------------------------------------- | ---------- |
| Inline source prefixed `pgsql:`               | 1.0        |
| File matching an explicitly configured suffix | 1.0        |
| `.pg` file                                    | 0.9        |
| `.sql` file                                   | 0.8        |
| `.s` file                                     | 0.75       |

These scores govern source-handler selection, not test importance, execution order, or assertion success.

When a suffix is explicitly configured, it acts as a filter: the handler accepts the configured suffix rather than automatically claiming every normally recognized file type.

The `pgsql:` mechanism allows a TAP harness or another Perl application to submit an SQL string as a test source without writing a temporary `.pg` file.

This is a lower-level integration capability of the source handler. It is not a replacement for pgTAP's SQL assertion functions, and it does not imply that pg_prove offers a general SQL scripting API.

Source: `https://metacpan.org/pod/TAP::Parser::SourceHandler::pgTAP`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org



### 2.5 Embedding PostgreSQL tests in a broader TAP harness

The source handler can be incorporated directly into Perl's `TAP::Parser`, `TAP::Harness`, and `Module::Build` infrastructure.

For example, `Module::Build` supports a source-handler configuration of the following form:

```
tap_harness_args => {
    sources => {
        Perl  => undef,
        pgTAP => {
            dbname   => 'testdb',
            username => 'postgres',
            suffix   => '.pg',
        },
    },
}
```

This enables PostgreSQL and Perl tests to participate in the same TAP execution and reporting framework.

The architectural distinction is that this is harness-level composition. PostgreSQL assertions remain database-side operations, while source selection, execution, result aggregation, and reporting belong to the Perl testing infrastructure.

Custom test formatters and TAP consumers can be incorporated without modifying pgTAP itself.

The value is greatest when multiple test-producing systems already emit TAP or can be adapted to emit it. It does not require replacing each system's native assertions with a common assertion language.

Source: `https://metacpan.org/pod/TAP::Parser::SourceHandler::pgTAP`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org



### 2.6 Additional harness execution and scheduling controls

The original overview covered pg_prove's principal parallelization, persistent-state, and reporting capabilities. A few additional controls complete those mechanisms.

`--dry` reports the selected test files without executing them, enabling inspection of discovery and filtering behavior.

`--trap` catches Ctrl-C and attempts to print a test summary before termination.

`--timer` reports per-file runtime, while `--merge` combines child-process standard error and standard output.

The persistent-state mechanism additionally supports `passed`, `fast`, and the `adrian` shorthand.

`passed` selects previously successful tests. `fast` orders test files from shortest to longest according to recorded runtime. `adrian` is an upstream shorthand for prioritizing recently failing tests while including the wider suite and updating saved state.

`--comments` is enabled by default, so diagnostic output does not require explicitly enabling it. `--no-comments` suppresses those diagnostics.

`--merge` should be used with awareness of TAP parsing requirements. PostgreSQL exceptions and other standard-error messages are not necessarily syntactically valid TAP records.

These controls operate over test sources and their recorded outcomes. They do not provide dependency-aware incremental testing or automatic selection of tests affected by database schema changes.

Source: `https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org



## 3. pg_tapgen: Generated database contracts and implementation drift

The original overview introduced `pg_tapgen` as an experimental schema-test generator. Its capabilities extend beyond basic schema inventory and deserve a more complete treatment.

### 3.1 Breadth of generated contract tests

`pg_tapgen` connects to a reference PostgreSQL database through Perl's DBI/DBD::Pg infrastructure and emits pgTAP test scripts representing its observed structure.

The upstream release history documents several expansions:

| Version | Added or improved capability                            |
| ------- | ------------------------------------------------------- |
| 3.32    | Foreign-table testing                                   |
| 3.32    | Materialized-view testing                               |
| 3.32    | Object-ownership assertions                             |
| 3.32    | Generated scripts with explicit assertion plans         |
| 3.33    | Trigger assertions                                      |
| 3.33    | Enum and extension assertions                           |
| 3.34    | Function-definition checksum tests                      |
| 3.36    | Separate function-body checks for overloaded signatures |
| 3.36    | Deterministically ordered generated trigger tests       |

These changes make `pg_tapgen` a substantially broader schema-baseline generator than its introductory description suggests.

Rather than manually authoring an expected-object inventory, a database can provide the reference structure from which assertions are generated.

The tool does not establish that the reference database is correct. It expresses the observed structure as a reproducible contract to be evaluated against another database.

Source: `https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/changes`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org



### 3.2 Function-definition checksum testing

The most consequential addition is generated function-checksum verification.

Ordinary schema assertions can verify that a function exists with a particular name, signature, return type, language, or other declared attributes.

A function-definition checksum adds another dimension: whether its stored definition matches the reference used to generate the test.

This can detect implementation changes that leave a function's external signature intact.

For example, a change to the logic of a PL/pgSQL function may preserve its name and return type while modifying its business behavior. A baseline comparison based only on catalog signatures could miss that change; a function-definition checksum can detect a difference in the definition.

The limitations are important:

- A matching checksum does not prove semantic correctness.
- A changed checksum does not necessarily indicate a regression; the implementation may have changed intentionally.
- Definition comparisons can be sensitive to canonicalization or representation differences across PostgreSQL versions.
- A checksum is a change detector, not a proof of functional equivalence.

Release 3.36 improved these checks by generating separate tests for functions distinguished by argument signatures. This prevents overloaded functions from being collapsed into a single name-based definition check.

The resulting mechanism can be valuable for database-baseline verification, especially when stored-program definitions are part of the expected database state.

Source: `https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/changes`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org



### 3.3 Generation controls and reproducibility

`pg_tapgen` exposes several controls that affect the generated tests' scope and portability.

| Option                        | Effect                                                      |
| ----------------------------- | ----------------------------------------------------------- |
| `--exclude-schema`            | Excludes selected schemas; may be supplied repeatedly       |
| `--directory`                 | Specifies an output directory for generated test files      |
| `--create-extension`          | Includes `CREATE EXTENSION pgtap` in generated scripts      |
| `--no-create-extension`       | Omits that extension-creation statement                     |
| PostgreSQL connection options | Select the database from which the reference schema is read |

The tool also automatically excludes `information_schema`.

Generated assertions use explicit plans, so missing assertion execution can be detected through test-count validation rather than relying entirely on dynamically determined counts.

Stable output ordering is relevant as well. Version 3.36 addressed nondeterministic trigger-test ordering, reducing irrelevant differences between successive generated baselines.

Status: `pg_tapgen` remains explicitly documented as experimental. Its DBI and DBD::Pg dependencies are not automatically validated by the distribution's build process, and the upstream documentation reserves the possibility of distributing the utility separately in the future.

Its outputs should therefore be regarded as generated test code whose semantics follow the assertions it emits, not as an independently authoritative model of database correctness.

Sources:

`https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_tapgen`

`https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/changes`

[image](https://www.google.com/s2/favicons?domain=https://metacpan.org\&sz=32)

metacpan.org+1

## 4. pg_virtualenv: Further PostgreSQL infrastructure behavior

### 4.1 Regression-runner integration added in postgresql-common 293

Debian's `postgresql-common` version 293, released July 16, 2026, introduced a specific pg_virtualenv change:

`Set EXTRA_REGRESS_OPTS for pg_regress --temp-instance runs.`

This is consequential because PostgreSQL's regression infrastructure can operate in two distinct modes.

Existing-server regression mode runs regression tests against a server that has already been initialized and started.

Temporary-instance regression mode uses `pg_regress --temp-instance` to initialize and operate its own temporary PostgreSQL server.

pg_virtualenv already provisions temporary clusters for commands running inside its environment. A regression command that independently uses `--temp-instance` creates another server lifecycle, rather than simply reusing the cluster created by pg_virtualenv.

PostgreSQL's build system incorporates `EXTRA_REGRESS_OPTS` into the arguments supplied to regression test executables. The variable is thus a build/test orchestration mechanism, not a PostgreSQL server GUC.

The version-293 change provides additional integration with this execution path.

The release announcement confirms the existence and purpose of the change, but does not specify its precise assigned value or all triggering conditions. Those implementation details should be established from the version-293 script before being treated as guaranteed behavior.

Primary sources:

`https://tracker.debian.org/news/1775690/accepted-postgresql-common-293-source-into-unstable/`

`https://www.postgresql.org/docs/18/regress-run.html`

`https://sources.debian.org/src/postgresql-common/293/`

[image](https://www.google.com/s2/favicons?domain=https://tracker.debian.org\&sz=32)

tracker.debian.org+2

### 4.2 Connection-environment normalization

A less visible feature of pg_virtualenv is that it does not merely set a few connection variables. It also takes steps to prevent inherited connection settings from directing commands toward an unintended PostgreSQL server.

In the inspected postgresql-common version-278 implementation, the utility establishes:

```
export PGHOST="localhost"
export PGDATABASE="postgres"

unset PGHOSTADDR PGPORT PGSERVICE
```

It then exports the appropriate port and version settings when exactly one cluster is selected.

This distinction matters because libpq connection configuration can be influenced by several overlapping environment variables.

For example, `PGHOSTADDR` specifies a network address independently of `PGHOST`, while `PGSERVICE` selects a named connection-service configuration. Leaving either inherited value intact could interfere with the expected temporary-cluster connection.

Clearing those selectors reduces the risk of connecting to a pre-existing database.

For multi-version environments, pg_virtualenv deliberately avoids exporting a single `PGPORT` or `PGVERSION`, instead providing per-version service definitions.

The implementation also exports `PGSYSCONFDIR` so Debian's PostgreSQL wrapper and cluster-management tools can locate the temporary configuration.

Implementation qualification: the environment-reset sequence above was verified in source version 278. The version-293 manual confirms the documented connection behavior, but the exact reset statements have not been independently verified against that later implementation.

This mechanism improves connection targeting; it does not make every libpq setting immutable or prevent an explicitly supplied connection string from selecting a different server.

Sources:

`https://sources.debian.org/src/postgresql-common/278/pg_virtualenv`

`https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html`

[image](https://www.google.com/s2/favicons?domain=https://sources.debian.org\&sz=32)

Debian Sources+1

### 4.3 Root, non-root, and fakeroot execution

pg_virtualenv distinguishes actual administrative privileges from simulated filesystem ownership.

In non-root operation, cluster configuration, data, logs, and supporting files are created under temporary directories rather than the conventional system-level PostgreSQL locations.

When invoked as root, the standard mode uses Debian's system PostgreSQL cluster-management locations. The `-t` option forces temporary-directory behavior even for a root invocation.

The utility also recognizes `fakeroot`.

Under `fakeroot`, a non-root process may appear to have root-style ownership information for packaging operations without possessing actual administrative privileges. pg_virtualenv therefore uses its non-root execution mode in this situation.

The documented behavior also warns that invoking `fakeroot pg_virtualenv` as the real root user fails.

This matters particularly in Debian package-building environments, where packages may be assembled under simulated root ownership even though tests must run using the process's real operating-system permissions.

Source: `https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://manpages.debian.org\&sz=32)

Debian Manpages



### 4.4 Staged extensions versus custom-prefix installations

Two PostgreSQL extension-loading mechanisms deserve distinction from pg_virtualenv's ordinary cluster provisioning.

#### Debian package-stage loading

pg_virtualenv's `-p package` option configures a temporary PostgreSQL cluster to discover extension files staged beneath a Debian package-build directory.

It adjusts extension-control and dynamic-library search paths rather than requiring conventional installation into PostgreSQL's system directories.

The documentation distinguishes PostgreSQL 18 and later, which can use `extension_control_path`, from older Debian installations that use the patched `extension_destdir` mechanism.

This capability belongs to pg_virtualenv and Debian's PostgreSQL packaging infrastructure.

#### PostgreSQL 18 custom-prefix extension installation

The pgTAP 1.3.4 distribution separately documents a custom-prefix installation mechanism for PostgreSQL 18 or later.

```
make install prefix=/usr/local/extras
```

The upstream README specifies that `prefix` applies to the `install` target, not the other `make` targets.

The corresponding PostgreSQL configuration is:

```
extension_control_path = '/usr/local/extras/postgresql/share:$system'
dynamic_library_path   = '/usr/local/extras/postgresql/lib:$libdir'
```

These are related but different approaches.

| Mechanism                           | Primary purpose                                                  | Required infrastructure                              |
| ----------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------- |
| pg_virtualenv `-p`                  | Load extensions staged in Debian build directories               | Debian PostgreSQL packaging support                  |
| pgTAP custom-prefix installation    | Install extension files outside PostgreSQL's default directories | Compatible PostgreSQL installation and configuration |
| PostgreSQL `extension_control_path` | Search additional locations for extension control files          | PostgreSQL 18 or later                               |

The custom-prefix mechanism can also be relevant to testing extensions other than pgTAP, because the underlying file-discovery mechanism belongs to PostgreSQL itself.

For compiled extensions, shared-library search configuration remains a separate consideration from control-file discovery.

Sources:

`https://pgxn.org/dist/pgtap/1.3.4/`

`https://www.postgresql.org/docs/18/extend-extensions.html`

`https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html`

[image](https://www.google.com/s2/favicons?domain=https://pgxn.org\&sz=32)

pgxn.org+2

## 5. Cross-cutting implications and corrected architectural distinctions

The additional findings produce several useful distinctions when the three tools are combined.

### Database contracts versus implementation baselines

pgTAP's type, cast, catalog, and permission assertions verify properties explicitly selected by a test author. `pg_tapgen` can additionally generate broad structural assertions and function-definition checks from a reference database.

These mechanisms answer different questions.

| Mechanism                            | What a passing test establishes                                      |
| ------------------------------------ | -------------------------------------------------------------------- |
| `has_function()` with argument types | A matching function signature exists                                 |
| `functions_are()`                    | The scoped function-name inventory matches expectations              |
| `function_returns()`                 | A selected function has the expected declared return type            |
| `cast_context_is()`                  | A particular cast has the expected coercion context                  |
| Generated function checksum          | The stored function definition matches the generated reference check |
| Behavioral query assertions          | Selected executions produce the expected results                     |

Combining these mechanisms expands coverage, but does not turn them into formal verification. Each establishes only the property actually tested.

### Test-process isolation versus database-state isolation

pg_prove's source handler gives separate SQL files independent client sessions. Transactional SQL tests can roll back most database writes, while pg_virtualenv can discard the entire test cluster.

However, these are different isolation boundaries.

A new `psql` session does not imply a new database. A transaction rollback does not restore nontransactional sequence state. A disposable PostgreSQL cluster does not isolate external services or host-level side effects.

This is particularly consequential for parallel tests, security-sensitive operations, and tests interacting with nontransactional or out-of-database resources.

### Schema visibility versus object identity

pgTAP's catalog assertions interact with PostgreSQL's `search_path` and overloaded-object resolution rules.

A contract defined only by visible object names may not distinguish every object that PostgreSQL could resolve under different execution contexts.

Explicit schemas, argument-type signatures, and attribute assertions can provide more precise contracts, especially for PostgreSQL routines, operators, and custom types.

### Test result completeness versus test execution completeness

A valid TAP summary means that the emitted results were parsed and evaluated according to TAP semantics. It does not inherently guarantee that every logically intended test case was generated.

Fixed plans, explicit fixture-count assertions, and appropriately constrained test discovery can address parts of this limitation.

Similarly, pg_prove's saved test history can select recently failing or modified test files, but cannot infer whether an unselected database behavior was affected by a code or schema change.

## 6. Primary source references

The following sources cover the additional functionality developed in this addendum.

| Reference                                                     | Direct URL                                                                                                    |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| pgTAP 1.3.4 complete assertions, metadata, and test lifecycle | `https://pgxn.org/dist/pgtap/doc/pgtap.html`                                                                  |
| pgTAP 1.3.4 release and installation documentation            | `https://pgxn.org/dist/pgtap/1.3.4/`                                                                          |
| pgTAP published extension components                          | `https://api.pgxn.org/src/pgtap/pgtap-1.3.4/META.json`                                                        |
| pg_prove CLI and harness controls                             | `https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove`                                  |
| pg_prove source-handler implementation                        | `https://github.com/theory/tap-parser-sourcehandler-pgtap/blob/develop/lib/TAP/Parser/SourceHandler/pgTAP.pm` |
| Perl TAP source-handler integration                           | `https://metacpan.org/pod/TAP::Parser::SourceHandler::pgTAP`                                                  |
| pg_tapgen generator documentation                             | `https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_tapgen`                                 |
| pg_prove/pg_tapgen release history                            | `https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/changes`                                            |
| pg_virtualenv 293 manual                                      | `https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html`                              |
| pg_virtualenv inspected source, version 278                   | `https://sources.debian.org/src/postgresql-common/278/pg_virtualenv`                                          |
| postgresql-common 293 source directory                        | `https://sources.debian.org/src/postgresql-common/293/`                                                       |
| postgresql-common 293 release announcement                    | `https://tracker.debian.org/news/1775690/accepted-postgresql-common-293-source-into-unstable/`                |
| PostgreSQL extension packaging and custom search paths        | `https://www.postgresql.org/docs/18/extend-extensions.html`                                                   |
| PostgreSQL native regression-test execution                   | `https://www.postgresql.org/docs/18/regress-run.html`                                                         |

The addendum's implementation observations are grounded in published upstream material; no local database execution or performance measurement was undertaken. The version-293 `EXTRA_REGRESS_OPTS` addition is verified from Debian's release history, while its precise implementation details remain explicitly unverified.

The added material extends the original reference in three substantive ways: pgTAP's ability to express deeper PostgreSQL type and catalog contracts, pg_prove's actual process and TAP-stream semantics, and pg_virtualenv's interaction with extension packaging and independently managed PostgreSQL regression environments.