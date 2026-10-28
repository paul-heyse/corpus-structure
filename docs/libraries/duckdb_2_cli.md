# DuckDB 2.0 — CLI and Agent Mode: Comprehensive Capability Reference

Target: DuckDB 2.0.0 LTS (“Cinnamon Teal”) · Released October 21, 2026 · Research date: October 24, 2026

## 1. Overview and architectural model

DuckDB 2.0 substantially expands the usefulness of its command-line interface for both human operators and autonomous programming agents. The most significant development is Agent Mode, which makes the CLI more efficient and reliable when an AI coding agent executes SQL, interprets results, diagnoses errors, and iteratively explores data.

DuckDB 2.0.0 is a released, stable LTS version—not merely a development preview. Agent Mode is included in the official CLI release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+2



An important distinction: DuckDB's Agent Mode is not a separate agent framework, Python package, MCP server, or natural-language-to-SQL system. It is a specialized execution and communication mode within the native DuckDB CLI.

### Core components and responsibilities

| Component                 | Primary responsibility                                                                                                                |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| DuckDB CLI                | Native `duckdb` executable for interactive SQL, scripts, automated queries, administration, and data exploration                      |
| CLI Agent Mode            | Agent-oriented rendering, bounded output, structured errors, query-cost signaling, and execution safeguards                           |
| DuckDB Python API         | In-process database access, parameterized execution, relational operations, Python data integration, and programmatic result handling |
| Quack protocol            | Remote DuckDB connectivity, including connections between CLI sessions, applications, and database-server processes                   |
| External agent frameworks | Natural-language interpretation, tool orchestration, reasoning, query construction, permissions, and autonomous decision-making       |

These components share DuckDB's SQL engine but provide different control surfaces and execution lifecycles.

Conceptual integration architecture

AI coding agent / Python orchestration layer

SQL generation · Tool calls · Result interpretation · Workflow decisions

Native CLI

Agent Mode, shell execution, output contracts

Python API

Connections, SQL, relations, Python objects

DuckDB 2.0 SQL engine

Query planning · Vectorized execution · Storage · Extensions

Local and attached databases · External data · Quack servers

The architectural distinction matters for Python systems:

- An autonomous agent invoking a terminal can use DuckDB's native Agent Mode directly, with no bespoke Python wrapper.
- A Python application normally interacts with DuckDB through the Python API, receiving structured objects rather than Markdown-formatted CLI output.
- A Python tool-hosting framework can expose either interface, but only CLI execution directly inherits the CLI-specific Agent Mode behavior.
- DuckDB 2.0's Quack connectivity introduces a third possibility: multiple clients communicating with a shared DuckDB process instead of independently opening local database connections.

The rest of this reference distinguishes the native CLI's capabilities from Python integration and agent-orchestration concerns.

Primary sources

DuckDB 2.0 release announcement:\
[https://duckdb.org/2026/10/21/announcing-duckdb-200](https://duckdb.org/2026/10/21/announcing-duckdb-200?utm_source=chatgpt.com)

DuckDB 2.0 CLI documentation:\
[https://duckdb.org/docs/2.0/clients/cli/overview](https://duckdb.org/docs/2.0/clients/cli/overview?utm_source=chatgpt.com)

DuckDB 2.0 Agent Mode documentation:\
[https://duckdb.org/docs/2.0/clients/cli/agent_mode](https://duckdb.org/docs/2.0/clients/cli/agent_mode?utm_source=chatgpt.com)

DuckDB engineering article on Agent Mode:\
[https://duckdb.org/2026/10/09/agent-mode](https://duckdb.org/2026/10/09/agent-mode?utm_source=chatgpt.com)

## 2. Native DuckDB 2.0 CLI: execution, inspection, and automation

The CLI is a full SQL client, not merely a thin wrapper around SQL execution. It combines DuckDB's query engine with its own command language, result formatting, interactive editing, script execution, and database connectivity.

### 2.1 Execution modes

| Mode                  | Interface                               | Principal use                                                |
| --------------------- | --------------------------------------- | ------------------------------------------------------------ |
| Interactive session   | `duckdb` or `duckdb database.duckdb`    | Exploration, analysis, inspection, iterative SQL development |
| One-shot execution    | `duckdb -c "SELECT ..."`                | Shell scripts, agent tool calls, individual diagnostics      |
| SQL scripts           | `duckdb -f script.sql`                  | Repeatable SQL operations and batch processing               |
| Standard input        | `duckdb < script.sql`                   | Unix pipelines and generated SQL                             |
| Startup configuration | `~/.duckdbrc`, `-init FILE`, `-no-init` | Session initialization, extensions, output settings          |
| Read-only access      | `-readonly`                             | Inspecting a persistent database without modifying it        |
| Remote session        | `-serve`, `-connect`                    | Serving or connecting to a DuckDB session over Quack         |

A common distinction is between executing a new CLI process and maintaining a long-running session. Each new `duckdb -c ...` invocation creates its own process and connection. Temporary tables, connection settings, and in-memory state do not automatically survive across invocations. Persistent databases, SQL initialization files, or a remote server provide different ways of maintaining state.

### 2.2 Arguments and execution composition

The command-line argument parser supports sequentially interleaved options and commands:

```
duckdb -csv -c "SELECT 42 AS answer" \
       -json -c "SELECT 84 AS answer"
```

The first command uses CSV and the second JSON. This makes output-mode control available without writing a wrapper around each individual query.

Other consequential arguments include `-bail` to stop on an error, `-cmd` to execute a preliminary command, `-no-init` to suppress startup-file execution, and `-format` or `-format-file` to format SQL independently of executing it. The SQL formatter provides a useful code-generation and SQL-authoring tool even when no database operation is required.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+1



### 2.3 Dot commands: the CLI's secondary control language

Dot commands are interpreted by the CLI rather than by the SQL parser. They begin at the start of a line, have no trailing SQL semicolon, and are not generally interchangeable with SQL.

The most relevant families are:

| Family                | Representative commands                           | Capability                                                        |
| --------------------- | ------------------------------------------------- | ----------------------------------------------------------------- |
| Schema and catalog    | `.tables`, `.schema`, `.databases`, `.indexes`    | Inspect databases, relations, types, DDL, and indexes             |
| SQL documentation     | `.manual FUNCTION`, `.help`                       | Inspect function signatures and examples directly in the terminal |
| Data acquisition      | `.import`, `.read`, `.dump`                       | Import files, execute scripts, reconstruct SQL exports            |
| Result presentation   | `.mode`, `.maxrows`, `.maxbytes`, `.maxcellwidth` | Control formats and output budgets                                |
| Output routing        | `.once`, `.output`, `.pager`, `.last`             | Redirect, page, or revisit results                                |
| Diagnostics           | `.timer`, `.log`, `.show`, `.progress_bar`        | Inspect execution and CLI state                                   |
| Interactive authoring | `.edit`, `.history`, `.auto_format`, `.highlight` | Edit SQL and navigate previous work                               |
| Database lifecycle    | `.open`, `.safe_mode`                             | Change database or restrict the session                           |

Several features are particularly valuable for agent-driven exploration.

Native introspection reduces custom metadata-query machinery. `.tables` and `.schema` provide quick catalog views. The SQL-facing `information_schema`, `duckdb_tables()`, `duckdb_columns()`, and related system functions provide relational forms suitable for programmatic inspection. `.manual FUNCTION` and `duckdb_functions()` make installed SQL functionality discoverable without maintaining a separate function registry.

Import and export need not go through Python objects. `.import` recognizes CSV, JSON, and Parquet; SQL functions such as `read_parquet`, `read_csv`, and `read_json` can scan external data directly. `COPY` writes structured results, including Parquet, without first materializing them in a Python DataFrame.

Output routing is part of the shell, not SQL semantics. `.once` applies to the next command; `.output` redirects subsequent output until changed. This differs from SQL's `COPY ... TO`, which delegates result serialization to DuckDB's data-export facilities. The latter is generally the stronger interface for preserving structured, potentially large datasets.

The CLI is a substantial interactive editor. Autocompletion, syntax highlighting, history, external-editor integration, and automatic formatting make it useful for developing SQL, while batch mode remains preferable for deterministic automation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+1



Official references:

CLI arguments:\
[https://duckdb.org/docs/2.0/clients/cli/arguments](https://duckdb.org/docs/2.0/clients/cli/arguments?utm_source=chatgpt.com)

Dot commands:\
[https://duckdb.org/docs/2.0/clients/cli/dot_commands](https://duckdb.org/docs/2.0/clients/cli/dot_commands?utm_source=chatgpt.com)

CLI output formats:\
[https://duckdb.org/docs/2.0/clients/cli/output_formats](https://duckdb.org/docs/2.0/clients/cli/output_formats?utm_source=chatgpt.com)

Interactive editing:\
[https://duckdb.org/docs/2.0/clients/cli/editing](https://duckdb.org/docs/2.0/clients/cli/editing?utm_source=chatgpt.com)

## 3. Agent Mode: behavior, guarantees, and implications

Agent Mode changes how the CLI communicates with an automated consumer. Its distinguishing feature is not that agents can submit SQL—they already could—but that the CLI now expresses execution results and diagnostic context in forms designed to avoid common failures in agent workflows.

### 3.1 Activation and precedence

Automatic activation requires all three conditions:

1. A recognized agent environment variable is set.
2. Standard output is not a terminal.
3. No explicit output-format flag was supplied.

Recognized variables include `AI_AGENT`, `AGENT`, `CLAUDECODE`, `CODEX_CI`, `CODEX_SANDBOX`, `CODEX_THREAD_ID`, `CURSOR_AGENT`, `GEMINI_CLI`, and GitHub Copilot agent variables.

Explicit activation is available independently of the host agent:

```
duckdb -agent -c "SELECT 42 AS answer"
```

The alternative environment-level control is:

```
DUCKDB_AGENT_MODE=1 duckdb -c "SELECT 42 AS answer"
```

Use `-no-agent` or `DUCKDB_AGENT_MODE=0` to disable it. Explicit CLI flags take precedence over the environment variable.

One nuance: `-agent -csv` retains agent behavior while using CSV result rendering. In contrast, supplying `-csv` alone prevents automatic agent detection. Explicit settings, including `.mode` and settings in `~/.duckdbrc`, can override Agent Mode defaults.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+1



### 3.2 Structured and bounded result presentation

Illustrative Agent Mode output

```
| customer_id:INTEGER | orders:BIGINT | total:DECIMAL(12,2) |
|---|---|---|
| 101 | 4 | 1250.00 |
| 102 | 2 | 840.50 |
```

Column names and SQL types appear together; the Markdown table has no width-padding overhead. Output shown here is illustrative, not from an executed query.

The important controls are distinct:

| Mechanism             | Default behavior                                                    | Why it matters                                                              |
| --------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Row budget            | Up to 1,000 rows rendered fully                                     | Avoids excessively large results                                            |
| Byte budget           | Up to 10,000 bytes of row data                                      | Limits output even for wide or text-heavy rows                              |
| Large-result sampling | First and last 20 rows, with explicit omitted-row marker            | Makes incompleteness visible                                                |
| Cell width            | 500 characters per cell                                             | Prevents a single large field from dominating context                       |
| Result footer         | Row count and, when available, result hash                          | Supports result completeness checks and comparisons                         |
| Early stopping        | Stops after consuming 100,000 additional rows beyond the output cap | Avoids processing arbitrarily large results solely to render a small sample |

Agent Mode's result limits can be changed using `.maxrows`, `.maxbytes`, and `.maxcellwidth`.

The early-stop behavior requires careful interpretation. A query that would return a billion rows may stop after reading enough rows to reach the output budget and additional counting threshold. DuckDB then reports a lower bound on the number of rows, rather than claiming to know the complete cardinality.

This is especially consequential for autonomous analysis: the output is an intentional preview, not proof that all matching data has been examined. It is inappropriate to infer completeness, absence of particular values, or exact total cardinality from an early-stopped result.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+1



### 3.3 Order-independent result hashes

When execution fully consumes a result, Agent Mode can report an order-independent hash covering the result, including rows omitted from display.

This provides a lightweight mechanism for detecting whether the returned rows changed between two queries without printing both complete results. DuckDB's implementation distinguishes SQL `NULL` from the literal string `'NULL'`.

There are important boundaries:

- The hash does not encode row order, so changes in ordering alone may be invisible.
- A hash is not an exact equality proof or a cryptographic integrity guarantee.
- No full-result hash is supplied when execution stops early.
- The footer appears for empty results, results of at least ten rows, and capped results; it is not necessarily present for every small nonempty result.

The mechanism is therefore valuable for inexpensive regression-oriented observation, but should not replace exact comparisons where correctness requires them.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 3.4 Structured errors

Agent Mode emits SQL and CLI errors on `stderr` as JSON. A binder error can include fields such as:

```
{
  "exception_type": "Binder",
  "exception_message": "Referenced column ... not found",
  "error_subtype": "COLUMN_NOT_FOUND",
  "position": "7",
  "name": "unknown_column"
}
```

This is a schematic field-level example; actual fields depend on the error.

This is significantly more useful than treating a formatted terminal traceback as an unstructured string. It enables conditional remediation based on error category, offending identifier, and location.

The distinction is also architectural: `stdout` is primarily the result channel, while `stderr` carries errors and execution diagnostics. However, `stderr` is not exclusively JSON. Startup notices, cost estimates, and progress reports are also written there as text. A tool adapter should not assume that the entire `stderr` stream is one JSON document.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 3.5 Compact query plans and workload signals

Agent Mode changes plan presentation as well as data presentation.

`EXPLAIN` uses a compact, indented operator representation rather than relying on a wide terminal diagram. It preserves useful operator identities, estimated cardinalities, and properties. `EXPLAIN ANALYZE` additionally reports runtime and execution details.

The same compact format is available explicitly outside Agent Mode:

```
EXPLAIN (FORMAT compact)
SELECT customer_id, COUNT(*)
FROM orders
GROUP BY customer_id;
```

For statements estimated to read one million or more rows, Agent Mode reports an approximate scan estimate on `stderr` before execution. Long-running statements produce plain-text progress updates approximately every five seconds.

These signals can inform an agent's decision to continue, interrupt, inspect an execution plan, or rewrite a query. They are planning estimates and progress observations, not exact resource guarantees. A low expected row count or absent estimate does not imply a cheap query.

A separate query timeout can be set through DuckDB's `max_execution_time` configuration. The operating system or calling process should still enforce an independent deadline for robust automation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+1



### 3.6 Query and schema discovery

DuckDB's own introspection facilities are especially useful with Agent Mode:

| Operation                                                             | Preferred interface                      |
| --------------------------------------------------------------------- | ---------------------------------------- |
| Inspect accessible tables and their columns                           | `.tables`                                |
| Read original or formatted table definitions                          | `.schema`                                |
| Determine query output types without executing the full query         | `DESCRIBE SELECT ...`                    |
| Examine distributions, nulls, extrema, or approximate distinct counts | `SUMMARIZE`                              |
| Discover installed functions and examples                             | `duckdb_functions()`, `.manual FUNCTION` |
| Understand the planned query                                          | `EXPLAIN`                                |
| Measure actual execution                                              | `EXPLAIN ANALYZE`                        |
| Understand Agent Mode settings                                        | `.help agent`, `.show`                   |

The broader architectural opportunity is that agents can discover data shape, available functions, and execution behavior through the database's native metadata interfaces, rather than through separately maintained instructions or handwritten metadata adapters.

### 3.7 Evidence on token efficiency

DuckDB's own Agent Mode evaluation used Claude Code on 22 TPC-H analytical questions at scale factor 100, with three runs per question in each mode.

CLI output tokens

# −59%

123.6k → 50.8k

Correctness

# 100%

Both configurations

Overall input savings

# \~0.5%

Dominated by other context

The overall runtime and cost did not improve materially in that experiment; Agent Mode took slightly more turns. This distinguishes the demonstrated result—substantially smaller DuckDB outputs—from a general claim that agent workflows will become correspondingly cheaper or faster.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



Primary sources for Agent Mode

Versioned Agent Mode reference:\
[https://duckdb.org/docs/2.0/clients/cli/agent_mode](https://duckdb.org/docs/2.0/clients/cli/agent_mode?utm_source=chatgpt.com)

Engineering rationale, detailed behavior, and benchmark:\
[https://duckdb.org/2026/10/09/agent-mode](https://duckdb.org/2026/10/09/agent-mode?utm_source=chatgpt.com)

## 4. Python integration: where Agent Mode fits and where it does not

DuckDB 2.0 exposes two different interfaces to Python:

1. The native `duckdb` Python module, which embeds the engine directly in the Python process.
2. The separate `duckdb` CLI executable, which a Python program can launch as an external process.

Agent Mode belongs to the second interface. Installing the Python package does not, by itself, establish that the native CLI executable is installed or available on `PATH`.

### 4.1 Installation and version compatibility

```
# Python package
python -m pip install "duckdb==2.0.0"

# Inspect the installed Python binding
python -c "import duckdb; print(duckdb.__version__)"

# Inspect the separately installed native CLI
duckdb -version
```

The native CLI is distributed through DuckDB's standalone installation mechanisms and release assets.

DuckDB Python 2.0 requires Python 3.11 or newer and does not support free-threaded CPython builds. On Python 3.10, an unrestricted package installation can select a compatible DuckDB 1.x version instead.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+2



Native CLI installation:\
[https://duckdb.org/docs/2.0/operations_manual/installing_duckdb/install_script](https://duckdb.org/docs/2.0/operations_manual/installing_duckdb/install_script?utm_source=chatgpt.com)

Python package overview:\
[https://duckdb.org/docs/2.0/clients/python/overview](https://duckdb.org/docs/2.0/clients/python/overview?utm_source=chatgpt.com)

### 4.2 Python invoking the native Agent CLI

A Python process can use `subprocess` to launch DuckDB with explicit Agent Mode settings.

```
import subprocessdef run_duckdb_agent_query(    sql: str,    database: str,) -> subprocess.CompletedProcess[str]:    return subprocess.run(        [            "duckdb",            "-no-init",            "-readonly",            database,            "-agent",            "-bail",            "-c",            sql,        ],        capture_output=True,        text=True,        timeout=30,        check=False,    )result = run_duckdb_agent_query(    "SELECT COUNT(*) AS n FROM events",    "analytics.duckdb",)print("Exit code:", result.returncode)print("Results:", result.stdout)print("Diagnostics:", result.stderr)
```

Illustrative, unexecuted Python adapter. Assumes the native DuckDB 2.0 CLI is installed and the database file already exists.

This gives the Python caller access to the CLI's Agent Mode behavior, including compact previews, explicit truncation, result hashes, and `stderr` diagnostics.

It also introduces a process boundary. Each invocation incurs process startup and connection initialization, has a separate transaction/session lifecycle, and communicates through serialized text rather than Python or Arrow objects. The subprocess timeout is separate from DuckDB's own query execution timeout.

Consequently, this approach is most naturally suited to terminal-agent interactions, subprocess isolation, CLI compatibility, or inspection tools. It is not necessary simply to execute DuckDB queries from Python.

### 4.3 Native Python DB-API execution

For structured application-level data access, DuckDB's DB-API is generally a more direct interface:

```
import duckdbwith duckdb.connect("analytics.duckdb", read_only=True) as con:    rows = con.execute(        """        SELECT customer_id, SUM(amount) AS total        FROM orders        WHERE status = ?        GROUP BY customer_id        ORDER BY total DESC        LIMIT 10        """,        ["completed"],    ).fetchall()
```

Here, parameter binding is native, errors are Python exceptions, and the application receives Python values rather than formatted Markdown. DuckDB supports positional `?` / `$1` parameters and named `$name` parameters.

The 2.0 DB-API also introduces an important result-lifecycle consideration. `execute()` can leave a query result open until fully consumed. A further query on the same connection may raise `ResourceInUseException` while a result is outstanding. `complete()` and `abort()` provide explicit ways to finish or cancel an open result. Separate cursors provide independent connections for other work.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 4.4 The relational API and Arrow streaming

DuckDB 2.0 makes a stronger separation between connection execution and relational operations than 1.x.

| Need                                     | DuckDB Python 2.0 interface                                     |
| ---------------------------------------- | --------------------------------------------------------------- |
| Execute SQL with side effects            | `con.execute(...)`                                              |
| Fetch rows using DB-API                  | `con.execute(...).fetchall()`, `fetchmany()`, `fetchone()`      |
| Build a composable relation              | `con.sql(...)`, `con.table(...)`, file-reading relation methods |
| Export a relation to Arrow               | `rel.to_arrow_table()`                                          |
| Stream Arrow batches                     | `rel.to_arrow_reader()`                                         |
| Convert a relation to Polars             | `rel.pl()`                                                      |
| Iterate relation rows in Python          | `rel.iter_rows()`                                               |
| Execute and retain the relation's result | `rel.materialize()`                                             |

A 2.0-native streaming example:

```
import duckdbwith duckdb.connect("analytics.duckdb", read_only=True) as con:    relation = con.sql("""        SELECT customer_id, SUM(amount) AS total        FROM orders        GROUP BY customer_id    """)    with relation.to_arrow_reader() as reader:        for batch in reader:            # Process each PyArrow RecordBatch.            consume(batch)
```

Illustrative; `consume` is an application-defined batch handler. PyArrow is required for Arrow interoperability.

This is especially relevant to agent tools that need typed, potentially large query results. Instead of converting a database result into Markdown and parsing it back into structured data, the host can use the Arrow schema and batches directly, then choose exactly what compact representation to provide to an LLM.

DuckDB 2.0's relational results can be re-executed upon consumption. `materialize()` instead captures a result for reuse. Arrow readers keep a connection resource in use until exhausted or closed, making their lifetime significant for concurrency.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+2



### 4.5 DuckDB 2.0 Python migration distinctions

Several changes are sufficiently consequential to affect wrappers, agents generating Python code, and data-processing libraries.

| Capability                     | 1.x pattern                                               | 2.0 behavior                                                           |
| ------------------------------ | --------------------------------------------------------- | ---------------------------------------------------------------------- |
| Arrow/Polars result conversion | `con.execute(...).fetch_arrow_table()`, `.pl()`, etc.     | Prefer `con.sql(...).to_arrow_table()`, `.pl()`, `.to_arrow_reader()`  |
| Relation fetching              | `rel.fetchone()`, `rel.fetchmany()`                       | Removed; use connection DB-API or `rel.iter_rows()`                    |
| Relation execution             | `rel.execute()`                                           | Removed; `rel.materialize()` when results should be retained           |
| Arrow batch default            | 1,000,000 rows                                            | 131,072 rows                                                           |
| Expression strings             | Often interpreted as column references                    | Plain strings represent values; use `col()` and `lit()` explicitly     |
| Dotted column references       | `ColumnExpression("t.x")`                                 | Use `col("t", "x")`                                                    |
| Dictionary conversion          | Some non-string-key dictionaries became structs           | Non-string keys produce map semantics                                  |
| Parallel calls                 | Shared-connection behavior could be relied on differently | Busy connections reject concurrent calls; use separate cursors         |
| Database files                 | 1.x default storage                                       | New 2.0 default storage format has backward-compatibility implications |

These changes make it particularly important to verify the Python API version separately from the CLI binary version. An agent that generates valid DuckDB 1.x Python code may generate methods that no longer exist in 2.0.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+1



Python DB-API documentation:\
[https://duckdb.org/docs/2.0/clients/python/dbapi](https://duckdb.org/docs/2.0/clients/python/dbapi?utm_source=chatgpt.com)

Python relational API:\
[https://duckdb.org/docs/2.0/clients/python/relational_api](https://duckdb.org/docs/2.0/clients/python/relational_api?utm_source=chatgpt.com)

Python 2.0 migration guide:\
[https://duckdb.org/docs/2.0/clients/python/migration](https://duckdb.org/docs/2.0/clients/python/migration?utm_source=chatgpt.com)

## 5. Quack: shared sessions between the CLI, Python, and other clients

One of DuckDB 2.0's most consequential additions for agent and Python integration is the Quack remote protocol.

Quack allows one DuckDB instance to expose its database session to other DuckDB instances using an HTTP-based protocol. This changes DuckDB's usual embedded-process model, without turning the Python API or CLI into a general-purpose agent framework.

### 5.1 Starting a server from the CLI

```
# Terminal A: run a DuckDB server backed by a database file
duckdb analytics.duckdb -serve

# Terminal B: connect to that server
duckdb -connect
```

With the default local configuration, the server listens on `localhost:9494` and manages a Quack secret for authentication. A named secret can also be supplied.

The same facility is accessible through SQL from clients, including Python:

```
CALL quack_serve('quack:localhost');
```

This exposes the source session's accessible state, including in-memory tables and attached databases, to authenticated clients. The host DuckDB process must remain alive to serve requests.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+1



### 5.2 Three distinct remote-query mechanisms

| Mechanism                       | Execution model                                        | Architectural significance                                  |
| ------------------------------- | ------------------------------------------------------ | ----------------------------------------------------------- |
| `ATTACH 'quack:host' AS remote` | Remote catalog accessible through qualified references | Allows local and remote data to participate in a query      |
| `ATTACH ...; CONNECT remote`    | Routes subsequent SQL execution to the remote session  | Provides a remote interactive/programmatic database session |
| `quack_query(uri, sql)`         | Stateless remote query invocation                      | Useful for isolated SQL calls without persistent attachment |

For a Python process, the same connection can use DuckDB SQL to attach a Quack endpoint, connect to it, query it, and retrieve results through Python's ordinary DB-API or relation interfaces.

`CONNECT` and plain `ATTACH` are not equivalent. `CONNECT` routes the session's query execution remotely; `ATTACH` exposes the remote as another catalog within the local engine, allowing federated query structures.

The protocol uses DuckDB's internal serialization rather than JSON or Markdown interchange, preserving complex SQL values, including nested data, decimals, and intervals. Large results can stream in chunks.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 5.3 Why Quack matters alongside Agent Mode

Quack and Agent Mode solve orthogonal problems.

Quack solves session sharing and transport. It can let different CLI and Python processes access a common executing database session, reducing the limitations of repeated process-local in-memory databases and local-file connection contention.

Agent Mode solves CLI output interpretation. A CLI client connected to a Quack server can still render returned results in agent-oriented form, while Python clients can retrieve typed results directly.

The combination permits a long-lived database session with short-lived agent CLI invocations and independent Python analytical clients, without requiring a custom SQL-over-HTTP service purely to expose DuckDB functionality.

This remains subject to concurrency, authentication, authorization, and server-resource considerations; it is not equivalent to a distributed transactional database.

### 5.4 Security and extension boundaries

Quack defaults to local-only binding and token authentication. Crucially, its default authorization hook is permissive: after authentication, the client is generally allowed to invoke the server's exposed SQL capabilities. Configurable authentication and authorization functions can change that behavior.

SQL macros or compiled DuckDB extensions can implement authorization policies. Python UDFs registered on a specific connection cannot directly serve as Quack authorization callbacks, because those callbacks execute through fresh server-side connections. This is an important extension boundary for Python-based control planes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



Official Quack references:

Protocol, transport, and client usage:\
[https://duckdb.org/docs/2.0/quack/overview](https://duckdb.org/docs/2.0/quack/overview?utm_source=chatgpt.com)

Quack security and authorization:\
[https://duckdb.org/docs/2.0/quack/security](https://duckdb.org/docs/2.0/quack/security?utm_source=chatgpt.com)

Quack function and configuration reference:\
[https://duckdb.org/docs/2.0/quack/reference](https://duckdb.org/docs/2.0/quack/reference?utm_source=chatgpt.com)

## 6. Agent tooling, MCP, and companion integrations

Agent Mode is one part of a wider set of possible DuckDB agent interfaces. The boundaries between them are important because they differ in where execution lives, how tools are exposed, and what the agent actually controls.

### 6.1 DuckDB's official agent skills

DuckDB maintains the `duckdb-skills` repository, a Claude Code plugin that builds agent workflows around the native CLI.

The repository provides composable capabilities for querying, attaching databases, exploring external files, searching documentation, managing extensions, and retrieving prior session information.

A particularly interesting mechanism is SQL-based session restoration. The skills maintain a `state.sql` file containing commands such as `ATTACH`, `USE`, extension loading, macros, and configuration. Individual calls can reconstruct a usable session with the CLI's `-init` argument.

This is an example of how a state-restoration layer can compensate for short-lived CLI invocations without maintaining a persistent Python worker or a bespoke state serialization format.

The distinction remains clear: the skills supply agent instructions and orchestration; DuckDB supplies SQL execution and Agent Mode rendering. The published skill implementation targets Claude Code and lists macOS/Linux testing, with Windows support not yet complete.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

duckdb/duckdb-skills · GitHub



Official project:\
[https://github.com/duckdb/duckdb-skills](https://github.com/duckdb/duckdb-skills?utm_source=chatgpt.com)

### 6.2 DuckDB MCP extension

A separate community-maintained DuckDB extension, `duckdb_mcp`, provides actual Model Context Protocol integration. It is not DuckDB's built-in CLI Agent Mode.

Its documented capabilities are notably broader than simply forwarding SQL queries.

| Capability                  | MCP extension mechanism                                                     |
| --------------------------- | --------------------------------------------------------------------------- |
| DuckDB as an MCP server     | `mcp_server_start()` and server lifecycle functions                         |
| Published data resources    | `mcp_publish_table()`, `mcp_publish_query()`                                |
| Published executable tools  | `mcp_publish_execution_tool()`                                              |
| DuckDB as an MCP client     | Attach an MCP server through `TYPE mcp`                                     |
| External resource access    | `mcp://` paths through supported file-reading interfaces                    |
| External tool invocation    | `mcp_call_tool()`                                                           |
| Resource and tool discovery | `mcp_list_resources()`, `mcp_list_tools()`                                  |
| Security configuration      | Transport configuration, command/URL allowlists, and server policy settings |

The extension documents parameterized execution tools, typed JSON values, multiple output formats, and dual client/server operation. These are capabilities of the community extension, not claims about the core DuckDB 2.0 CLI.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB Community Extensions



An important version qualification: the community catalog lists the extension, but its displayed compatibility matrix does not clearly establish available DuckDB 2.0.0 builds across platforms. Its own version 2.0/2.1 feature labels also refer to extension versions, not the DuckDB engine version. Installation compatibility should therefore be independently verified before treating it as part of a deployable DuckDB 2.0 stack.

Extension catalog:\
[https://duckdb.org/community_extensions/extensions/duckdb_mcp](https://duckdb.org/community_extensions/extensions/duckdb_mcp?utm_source=chatgpt.com)

Upstream source and implementation documentation:\
[https://github.com/teaguesterling/duckdb_mcp](https://github.com/teaguesterling/duckdb_mcp?utm_source=chatgpt.com)

### 6.3 Python-based MCP servers and other agent hosts

A Python MCP server can also use `duckdb` directly, for example through a framework such as FastMCP.

That arrangement has a different set of capabilities and responsibilities:

| Responsibility           | Native CLI Agent Mode                     | Python MCP host using DuckDB                            |
| ------------------------ | ----------------------------------------- | ------------------------------------------------------- |
| SQL execution            | Native CLI                                | Embedded Python binding                                 |
| SQL tool discovery       | CLI commands and SQL metadata             | Explicitly published MCP tool schemas                   |
| Output presentation      | Compact Markdown with truncation/hash     | Host-controlled typed JSON, summaries, or other formats |
| Parameterization         | SQL supplied to CLI                       | Native Python prepared-statement binding                |
| Result streaming         | CLI process output                        | Arrow readers or DB-API fetching                        |
| Permission model         | CLI/engine/OS restrictions                | Host policy plus DuckDB/OS restrictions                 |
| Agent protocols          | No built-in MCP protocol                  | MCP implemented by host framework                       |
| Persistent process state | Requires long-lived CLI or reconstruction | Can retain connection/session state in a Python service |

The Python approach can expose purpose-built tools, such as `describe_table`, `summarize_relation`, `explain_query`, or `execute_readonly_query`, rather than requiring every agent action to be free-form SQL.

Such tools can derive much of their functionality from DuckDB's relational catalog, prepared statements, optimizer, and execution interfaces. The result is an opportunity to reduce bespoke database-inspection logic while retaining a controlled external interface.

However, that is an architectural possibility, not a capability automatically provided by installing DuckDB.

## 7. Security, resource control, and correctness boundaries

Agent-facing database execution warrants more careful controls than interactive SQL used by a trusted engineer.

DuckDB's official security guidance explicitly treats untrusted SQL as potentially executable code: it can access files, consume substantial resources, communicate over networks, and use extensions. Agent Mode makes output easier to interpret; it does not make submitted SQL trustworthy.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### 7.1 Native CLI restrictions

| Control                   | What it does                                                                    | Important limitation                                            |
| ------------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `-readonly`               | Opens a database without permitting writes to that database                     | Does not by itself restrict all external file or network access |
| `-safe`                   | Restricts external filesystem interaction and disables sensitive shell commands | Also prevents many useful file-ingestion operations             |
| `-no-init`                | Skips the startup configuration file                                            | Does not otherwise restrict SQL capabilities                    |
| `-bail`                   | Stops batch execution on an error                                               | Does not limit successful but expensive queries                 |
| `max_execution_time`      | Sets a DuckDB query execution time limit                                        | Does not replace process-level timeouts                         |
| OS/container restrictions | Constrain files, processes, and networking                                      | Require a separately configured execution environment           |

The CLI's `-safe` option is stronger than `-readonly` for filesystem access. It disables commands including `.import`, `.read`, `.open`, and shell execution; it also sets `enable_external_access=false`, preventing external reads through functions such as `read_parquet` and `read_csv`, as well as file-oriented `COPY` operations.

Safe Mode cannot be deactivated within the same session after being enabled. Its restrictions therefore make it unsuitable for some legitimate workflows in which the agent's purpose is precisely to inspect or transform external files.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



CLI Safe Mode:\
[https://duckdb.org/docs/2.0/clients/cli/safe_mode](https://duckdb.org/docs/2.0/clients/cli/safe_mode?utm_source=chatgpt.com)

General security model:\
[https://duckdb.org/docs/2.0/operations_manual/securing_duckdb/overview](https://duckdb.org/docs/2.0/operations_manual/securing_duckdb/overview?utm_source=chatgpt.com)

### 7.2 Result completeness is separate from query correctness

Agent Mode has three importantly different result states:

| State                                  | What can safely be inferred                                                                                |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Fully rendered, fully consumed         | All result rows were available in the output                                                               |
| Truncated presentation, fully consumed | DuckDB consumed the complete result, but only a sample was shown; a full-result hash may be present        |
| Early-stopped execution                | Only a prefix of the result stream was consumed; reported count is a lower bound, with no full-result hash |

This has consequences for diagnostics and automated validation.

For example, an agent cannot reliably use a sampled `SELECT * FROM large_table` result to conclude that a value is absent from the table. An explicit SQL predicate, aggregate, `EXISTS` query, or full streaming read would be required, depending on the question.

Similarly, the result hash can provide an inexpensive observation of equality-like behavior, but it is not a substitute for validation based on keys, row counts, typed comparisons, or application-defined invariants.

### 7.3 Resource estimates versus resource limits

Agent Mode's reported scan estimates are useful for anticipating expensive operations. They do not prevent a query from performing large joins, sorts, aggregations, decompression work, remote reads, or other operations whose costs are not captured by an estimated number of input rows.

Result-output limits likewise do not always limit the work performed by the engine. A query returning one scalar aggregate may need to scan a very large dataset before emitting any result.

For bounded execution, the useful combination is DuckDB resource settings, appropriate query structure, process-level deadlines, and environmental resource isolation.

### 7.4 Concurrency and database ownership

For local embedded DuckDB database files, the core concurrency model distinguishes one read/write process from multiple read-only processes. Within a single writer process, DuckDB supports concurrency using MVCC and optimistic conflict detection.

Quack provides a path for multiple processes to issue writes through a shared server instance. It does not remove the importance of transactional conflicts, server ownership, or connection lifecycles.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



There are also Python-specific restrictions: shared connection objects reject concurrent calls while busy, and outstanding Arrow readers or DB-API results can occupy connection resources.

These concerns are especially relevant when a Python application simultaneously hosts agent tools, application SQL operations, and analytical streams.

Concurrency reference:\
[https://duckdb.org/docs/2.0/connect/concurrency](https://duckdb.org/docs/2.0/connect/concurrency?utm_source=chatgpt.com)

## 8. Related DuckDB 2.0 engine features that increase CLI usefulness

Several major 2.0 changes are not Agent Mode features but still increase the value of DuckDB as an interactive or agent-driven analytical engine.

### Asynchronous I/O

DuckDB 2.0 introduces asynchronous I/O for CSV, Parquet, and native storage. The I/O layer can issue and manage reads independently of query execution threads.

For agent workloads involving remote object storage, this can reduce the cost of exploratory scans and repeated analytical questions where reading external data was the limiting factor.

This optimization belongs to the DuckDB engine and benefits supported workloads regardless of whether the caller is the native CLI, a Python process, or a remote Quack client. Actual improvements depend on storage latency, bandwidth, query structure, and other bottlenecks.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### First-class `VARIANT` support

DuckDB 2.0 fully integrates its `VARIANT` type for semi-structured data, including columnar representation, Parquet support, and `variant_*` operations.

An agent examining heterogeneous JSON records can potentially preserve semi-structured values in the database and use native inspection and extraction operations, rather than implementing Python-side schema-normalization machinery for every field.

This is especially useful where schema discovery and heterogeneous event exploration are substantial parts of the workload. The tradeoff is that semi-structured values still require explicit semantics when an operation expects stable, typed fields.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### Extensible SQL parser

DuckDB 2.0 adopts its PEG-based parser by default. Extensions can participate in extending the SQL grammar, and parsing errors provide more precise source locations.

The practical implications for agents are better diagnostics for generated SQL and a broader mechanism for exposing extension-defined SQL constructs.

It does not imply that DuckDB has become a general SQL transpiler, nor that arbitrary dialect syntax is supported automatically.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



### SQL introspection and execution plans

The combination of catalog functions, `DESCRIBE`, `SUMMARIZE`, `EXPLAIN`, `EXPLAIN ANALYZE`, and SQL-level relational operations creates a compact native substrate for data exploration and automated diagnostics.

Agent Mode improves the presentation of these capabilities, but the underlying SQL functionality is also available to Python, Quack clients, and other supported bindings.

DuckDB 2.0 release and engine-level changes:\
[https://duckdb.org/2026/10/21/announcing-duckdb-200](https://duckdb.org/2026/10/21/announcing-duckdb-200?utm_source=chatgpt.com)

## 9. Choosing among the available interfaces

These interfaces should be understood as complementary, rather than as interchangeable implementations of the same concept.

| Requirement or workload                            | Strongest native fit                              | Reason                                                            |
| -------------------------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------- |
| Engineer interactively exploring a database        | Standard DuckDB CLI                               | Terminal editor, dot commands, convenient rendering               |
| Coding agent executing SQL from a shell            | CLI Agent Mode                                    | Compact and explicit result communication                         |
| Python application querying a database             | DuckDB Python DB-API                              | Direct structured execution, parameter binding, Python exceptions |
| Python application composing relational operations | Python relational API                             | Composable relations, typed output conversion                     |
| High-volume typed output                           | Python Arrow reader or DuckDB `COPY`              | Avoids Markdown serialization and display limits                  |
| Deterministic shell-to-program data transfer       | CLI `-json`, `-jsonlines`, CSV, or exported files | Explicit interchange formats instead of agent-oriented previews   |
| Multiple processes using the same database session | Quack                                             | Shared remote execution and session access                        |
| Tool-based agent integration through MCP           | Python MCP host or compatible MCP extension       | Typed tool schemas and protocol integration                       |
| Reusable Claude Code DuckDB workflows              | `duckdb-skills`                                   | Agent instructions and CLI session restoration                    |
| Restricting untrusted database execution           | DuckDB settings plus operating-system isolation   | Agent Mode is not a security boundary                             |

A particularly useful distinction is human/LLM-readable output versus machine-native result transport.

Agent Mode's Markdown previews, column types, and hashes are appropriate for an LLM deciding what query to run next. Arrow streams, prepared statements, and explicit export formats are better suited to systems that must ingest complete, typed datasets.

Combining the two is often more valuable than forcing all operations through one interface: use compact introspection and previews for reasoning, and typed database operations for complete data handling.

## 10. Versioning and remaining limitations

DuckDB 2.0.0 is the first stable release of the 2.0 line, with LTS support announced through at least October 2027. The functionality above reflects the published 2.0 documentation as of October 24, 2026.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB



The following limitations materially affect integration:

CLI and Python releases are distinct artifacts. Matching their versions avoids differences in parser behavior, storage support, and API semantics, but the Python installation does not confer the CLI's Agent Mode interface.

Dot commands are CLI-specific. Commands such as `.tables` and `.maxrows` cannot simply be passed to `duckdb.connect().execute()` as SQL. Equivalent Python tooling uses SQL catalog functions, DB-API operations, or application-level result formatting.

Agent Mode output is intentionally lossy under its default budgets. It is designed for interpretation, not lossless transmission of arbitrary datasets.

Remote Quack access introduces an authenticated SQL-server boundary. Token authentication, permissive default authorization, server visibility, and remote resource ownership must be considered independently of Agent Mode.

Python 2.0 introduces meaningful source incompatibilities. Earlier examples relying on relation fetching or DB-API Arrow methods may require revision.

DuckDB 2.0's default database storage format is not automatically readable by DuckDB 1.5. The CLI exposes `-storage-version`, and Python exposes `storage_compatibility_version`, for cases requiring older-format compatibility.

MCP integration is not part of the core Agent Mode contract. The community MCP extension and Python MCP frameworks add tool protocols, with their own releases, compatibility requirements, and security behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://duckdb.org\&sz=32)

DuckDB

+2



## Consolidated technical source map

All URLs below are primary documentation or upstream project sources, grouped by their role in the stack.

| Subject                                                 | Direct source                                                            |
| ------------------------------------------------------- | ------------------------------------------------------------------------ |
| DuckDB 2.0 release, supported line, and engine features | `https://duckdb.org/2026/10/21/announcing-duckdb-200`                    |
| Native CLI arguments and remote options                 | `https://duckdb.org/docs/2.0/clients/cli/arguments`                      |
| CLI dot-command reference                               | `https://duckdb.org/docs/2.0/clients/cli/dot_commands`                   |
| CLI output formats                                      | `https://duckdb.org/docs/2.0/clients/cli/output_formats`                 |
| CLI Agent Mode specification                            | `https://duckdb.org/docs/2.0/clients/cli/agent_mode`                     |
| Agent Mode engineering rationale and benchmark          | `https://duckdb.org/2026/10/09/agent-mode`                               |
| CLI Safe Mode                                           | `https://duckdb.org/docs/2.0/clients/cli/safe_mode`                      |
| Python binding                                          | `https://duckdb.org/docs/2.0/clients/python/overview`                    |
| Python DB-API                                           | `https://duckdb.org/docs/2.0/clients/python/dbapi`                       |
| Python relational API and Arrow conversion              | `https://duckdb.org/docs/2.0/clients/python/relational_api`              |
| Python migration to 2.0                                 | `https://duckdb.org/docs/2.0/clients/python/migration`                   |
| Quack server/client protocol                            | `https://duckdb.org/docs/2.0/quack/overview`                             |
| Quack security and authorization                        | `https://duckdb.org/docs/2.0/quack/security`                             |
| Concurrency                                             | `https://duckdb.org/docs/2.0/connect/concurrency`                        |
| General execution security                              | `https://duckdb.org/docs/2.0/operations_manual/securing_duckdb/overview` |
| Official DuckDB agent skills                            | `https://github.com/duckdb/duckdb-skills`                                |
| Community MCP extension                                 | `https://github.com/teaguesterling/duckdb_mcp`                           |

### Architectural conclusion

The significance of DuckDB 2.0's Agent Mode is that it makes the existing native CLI substantially more suitable as an agent-facing analytical interface, without requiring agents to adopt a new database API or custom SQL execution service.

Its most valuable features are the combination of compact typed previews, explicit completeness information, result fingerprints, machine-readable errors, and useful execution feedback.

For Python-based systems, the broader capability is the composition of Agent Mode, the native Python relational/DB-API interfaces, Arrow, and Quack. These provide distinct but compatible surfaces for agent reasoning, typed data access, bulk result movement, and shared execution state.

That combination can eliminate significant amounts of bespoke query-inspection, output-formatting, session-management, and data-transfer machinery—provided each layer is used for the responsibilities it actually supports.