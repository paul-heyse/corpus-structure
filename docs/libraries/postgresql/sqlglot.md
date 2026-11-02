# SQLGlot — Comprehensive Python Library Capability Overview

Research date: November 1, 2026 | Stable release: 30.27.0 (October 30, 2026) | Python ≥ 3.9 | MIT license

Project: [https://github.com/tobymao/sqlglot](https://github.com/tobymao/sqlglot?utm_source=chatgpt.com)

Documentation: [https://sqlglot.com/sqlglot.html](https://sqlglot.com/sqlglot.html?utm_source=chatgpt.com)

PyPI: [https://pypi.org/project/sqlglot/30.27.0/](https://pypi.org/project/sqlglot/30.27.0/?utm_source=chatgpt.com)

SQLGlot is a Python-based SQL parser, transpiler, optimizer, and lightweight execution engine. Its most important architectural feature is a dialect-independent abstract syntax tree (AST) that provides a shared representation for parsing, analyzing, transforming, comparing, and generating SQL across more than 30 SQL dialects.

Although SQLGlot is commonly described as a SQL transpiler, that description considerably understates its functionality. It is more accurately understood as a reusable SQL compiler and analysis infrastructure, providing many of the components needed to build SQL-aware developer tools, semantic analyzers, query transformation systems, data lineage engines, and database interoperability layers.

The library combines syntactic analysis with schema-aware semantic resolution, expression typing, logical rewriting, structural differencing, and dialect-specific code generation. These capabilities can be used independently or composed into sophisticated workflows without implementing a SQL grammar, expression-tree infrastructure, name-resolution system, or query rewrite framework from scratch.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



## 1. Architectural orientation

SQLGlot's central abstraction is the `Expression` tree, exposed primarily through `sqlglot.exp`. SQL source is converted into structured expressions; those expressions can subsequently be inspected, qualified against schemas, rewritten, compared, serialized, or rendered as SQL.

Source SQL

One of 30+ supported dialects

Tokenizer → Parser

SQLGlot AST

Structured, traversable, mutable expression model

Semantic analysis

AST transformations

Lineage and diff

Dialect-specific Generator

Generated SQL

Target dialect, formatting and compatibility rules

Conceptual architecture. Analysis and transformation stages are optional; SQLGlot can also construct ASTs directly or pass them to its internal query planner and executor.

The major capability families are:

| Capability                      | Principal mechanisms                                 | Architectural value                                           |
| ------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------- |
| SQL parsing                     | Tokenizer, parser, dialect grammars                  | Structured SQL understanding without a bespoke parser         |
| SQL transpilation               | Normalized AST, dialect generators                   | Cross-engine SQL adaptation                                   |
| AST construction and rewriting  | Expression builders, traversal, transforms           | Programmatic query generation and modification                |
| Semantic analysis               | Schema resolution, scopes, qualification             | Understanding what SQL references actually mean               |
| Type analysis                   | Type inference and annotations                       | Type-sensitive transformations and inspection                 |
| Query optimization              | Rule-based optimizer                                 | Canonicalization and relational query rewrites                |
| Data lineage                    | Column-level dependency tracing                      | Explainable relationships between query outputs and inputs    |
| Structural comparison           | AST diff and edit operations                         | SQL change analysis beyond textual differences                |
| Serialization and anonymization | AST serialization, token anonymization               | Persistable query structure and privacy-conscious diagnostics |
| Lightweight SQL execution       | Logical planner, Python executor                     | Small-scale execution and testing                             |
| Extensibility                   | Custom dialects, custom expressions, optimizer rules | Specialized SQL analysis and translation tooling              |

An important distinction governs nearly every capability: SQLGlot operates primarily on SQL representations, not on the database's actual physical execution environment. It can understand and rewrite query structures, but it does not inherently know a database's live catalog, runtime statistics, authorization policies, user-defined function implementations, or physical query plans.

It therefore complements rather than replaces database engines, cost-based optimizers, schema catalogs, and runtime SQL validators.

## 2. SQL parsing and the expression model

### 2.1 Lexical analysis and parsing

SQLGlot implements its own tokenizer and recursive-descent parser, with dialect-specific extensions built upon a shared parsing infrastructure.

Its principal entry points are:

| API                       | Functionality                                                     |
| ------------------------- | ----------------------------------------------------------------- |
| `sqlglot.tokenize()`      | Tokenize SQL with token types, text and source positions          |
| `sqlglot.parse()`         | Parse multiple SQL statements into separate expressions           |
| `sqlglot.parse_one()`     | Parse a single expression, with optional expected expression type |
| `sqlglot.transpile()`     | Parse and generate SQL across dialects                            |
| `Dialect.parse_into()`    | Parse SQL using a specified expression category                   |
| `Parser`                  | Extensible parser implementation                                  |
| `Tokenizer` / `TokenType` | Extensible lexical grammar and token classification               |

The tokenizer recognizes keywords, identifiers, literals, operators, punctuation, comments, and dialect-specific lexical forms. Individual dialects can change identifier delimiters, string escaping, recognized keywords, numeric formats, and special operators.

Token objects expose source-location information, making lexical analysis useful for diagnostic tools, editors, and source-oriented inspections.

The parser handles substantially more than `SELECT` statements. Its expression model encompasses relational queries, CTEs, joins, window functions, set operations, subqueries, table-valued functions, DML operations, DDL statements, constraints, table properties, and numerous database-specific constructs.

This breadth matters for cataloging and static analysis: a SQL dependency analysis system may need to understand `CREATE VIEW`, `INSERT`, `MERGE`, or `ALTER TABLE`, not merely the expressions appearing in a read-only query.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+2



Important limitation: SQLGlot deliberately accepts some queries that a database would reject. Successful parsing does not establish that referenced objects exist, that function signatures are valid, or that a statement can execute on the target engine.

Source: [https://sqlglot.com/sqlglot/parser.html](https://sqlglot.com/sqlglot/parser.html?utm_source=chatgpt.com)

### 2.2 The AST is the primary programmatic interface

Every SQLGlot AST node is a subclass of `exp.Expr` (with `exp.Expression` retained as an interface alias).

The AST is structured around expression types rather than SQL text fragments. Representative nodes include `Select`, `Table`, `Column`, `Identifier`, `Alias`, `Join`, `CTE`, `Subquery`, `Cast`, `Func`, `Literal`, `DataType`, and expression-specific classes for aggregate functions, temporal operations, JSON operations, and relational statements.

Each node exposes structured arguments through `args`. The library also provides convenience accessors and navigation mechanisms:

| API or property                     | Significance                                   |
| ----------------------------------- | ---------------------------------------------- |
| `find()` / `find_all()`             | Locate expressions by type                     |
| `walk()` / `dfs()` / `bfs()`        | Traverse expression trees                      |
| `parent`, `arg_key`, `index`        | Recover a node's structural context            |
| `find_ancestor()` / `parent_select` | Navigate to enclosing constructs               |
| `this`, `expression`, `expressions` | Access common child-expression positions       |
| `transform()`                       | Recursively apply an expression transformation |
| `replace()` / `pop()` / `set()`     | Modify tree structure                          |
| `copy()`                            | Preserve an existing tree before mutation      |
| `sql()`                             | Generate SQL from an expression                |
| `meta`                              | Attach or inspect node metadata                |
| `dump()` / `load()`                 | Serialize and restore expression structure     |

The `args` structure makes SQL syntax inspectable at a considerably richer level than token matching. For example, a `Column` can expose table, database, and catalog qualification; an `Alias` retains its underlying expression separately from its output name; and a `Select` exposes projections, sources, predicates, grouping, ordering, and related clauses through distinct tree relationships.

AST traversal also enables transformations that are invariant to irrelevant textual differences. A rewrite can target all column references inside a query without relying on capitalization, indentation, or alias formatting.

### 2.3 Construction and mutation

SQLGlot provides both low-level expression constructors and higher-level builder methods.

Important facilities include `exp.select`, `exp.column`, `exp.table_`, `exp.to_table`, `exp.to_column`, `exp.cast`, `exp.func`, `exp.case`, `exp.values`, and helpers for `INSERT`, `UPDATE`, `DELETE`, and `MERGE`.

Expression builders support composition through methods such as `.select()`, `.from_()`, `.join()`, `.where()`, `.group_by()`, `.order_by()`, `.limit()`, and `.with_()`.

For example:

```
from sqlglot import exp, parse_onequery = parse_one(    "SELECT customer_id, amount FROM sales",    read="postgres",)# Inspect structured column references.columns = list(query.find_all(exp.Column))# Work on an independent copy.modified = query.copy().where("amount > 100")# Generate SQL in another dialect.sql = modified.sql(dialect="duckdb")
```

This illustrates the principal composition pattern: parse an existing query, understand it through typed expressions, modify the structure, and regenerate target-specific SQL.

The builders are useful well beyond constructing queries from scratch. SQLGlot also includes utilities for table substitution, placeholder replacement, source expansion, and subtree replacement.

A particularly useful distinction is between `transform()` and narrowly targeted mutation. `transform()` recursively visits nodes and can replace matching expressions, while `set()`, `replace()`, and related APIs operate on specific tree relationships. Which approach is preferable depends on whether a rewrite is global, local, scope-aware, or context-dependent.

Mutation semantics deserve care. AST nodes have parent relationships. Reusing or modifying nodes without copying may change the original expression tree or affect ownership relationships. SQL generation and optimizer operations also expose copy controls because transformations can mutate expressions.

Source fidelity is not guaranteed. The AST is a semantic and structural representation, not a lossless concrete syntax tree. Formatting and lexical details can change during regeneration, and comment preservation is best-effort. AST positions should not be assumed to remain valid after arbitrary transformations.

Sources:

[https://sqlglot.com/sqlglot/expressions/core.html](https://sqlglot.com/sqlglot/expressions/core.html?utm_source=chatgpt.com)

[https://sqlglot.com/sqlglot/expressions/builders.html](https://sqlglot.com/sqlglot/expressions/builders.html?utm_source=chatgpt.com)

[https://github.com/tobymao/sqlglot/blob/main/posts/ast_primer.md](https://github.com/tobymao/sqlglot/blob/main/posts/ast_primer.md?utm_source=chatgpt.com)

## 3. Dialect translation and SQL generation

### 3.1 Dialect-independent intermediate representation

SQLGlot's transpiler operates by parsing source-dialect SQL into its common expression representation and generating SQL according to the target dialect.

```
import sqlglotstatements = sqlglot.transpile(    "SELECT TRY_CAST(value AS INT) FROM events",    read="spark",    write="duckdb",)
```

The significance is greater than changing syntax or function names. Different databases express equivalent operations through different functions, argument conventions, date/time formats, data types, indexing rules, and relational constructs.

SQLGlot's normalized expressions allow many of those variations to be addressed through common transformation rules rather than implementing a distinct translation algorithm for every source-target pair.

### 3.2 Supported dialect families

Release 30.27.0 documents over 30 dialects, distinguishing officially maintained, community-maintained, and third-party plugin implementations.

| Family                      | Notable dialects                                                                           |
| --------------------------- | ------------------------------------------------------------------------------------------ |
| Data warehouses             | Snowflake, BigQuery, Redshift, Databricks                                                  |
| Distributed SQL             | Trino, Presto, Spark, Hive, Athena                                                         |
| Analytical databases        | DuckDB, ClickHouse, StarRocks, Druid                                                       |
| Traditional RDBMS           | PostgreSQL, MySQL, SQLite, Oracle, T-SQL                                                   |
| Additional SQL engines      | Teradata, SingleStore, RisingWave, Materialize, Doris, Dremio, Drill, Exasol, Fabric, Dune |
| Specialized query languages | PRQL, DAX, Tableau, Solr                                                                   |
| External plugins            | YDB, MaxCompute, among others                                                              |

The special-purpose language dialects should not be interpreted as having uniform SQL semantics or identical coverage. Similarly, inclusion in the supported-dialect list does not imply complete coverage of every product-specific statement, function, or release version.

SQLGlot classifies official dialects as maintained by its core team. Community dialects have independent contribution patterns, while plugin dialects are distributed separately. The plugin mechanism was introduced in v28.6.0 and is available in the target release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



### 3.3 Dialect-specific semantic behavior

Some important transformations are based on differences that are not immediately visible in the SQL grammar.

Identifiers and namespaces. Dialects differ in case folding, quoting, catalog/database hierarchies, and treatment of aliases. SQLGlot exposes dialect-specific identifier normalization rules rather than assuming all engines resolve names identically.

Data types. Type mappings cover differences between integer, decimal, floating-point, string, binary, temporal, array, and structured data representations. The system can render a common expression into dialect-appropriate type syntax.

Function semantics. Dialect definitions provide specialized parsing and generation for functions and operators. Temporal functions, JSON extraction, string operations, aggregate functions, and casts can require substantial translation logic.

Relational operations. Some SQL constructs need structural rewriting, not just token substitution. SQLGlot includes transformations relevant to `QUALIFY`, `DISTINCT ON`, semi/anti joins, full outer joins, `UNNEST`, `EXPLODE`, window clauses, and recursive CTE-based formulations.

Dialect metadata. Dialect classes expose configuration for behaviors such as null ordering, identifier normalization, array index offsets, type coercion, default set-operation distinctness, JSON path handling, and projection alias resolution.

The existence of these dialect-level switches is architecturally important: it allows SQL analysis and generation to incorporate engine differences at the appropriate layer, rather than scattering vendor-specific conditions throughout application logic.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+2



### 3.4 Generation-time structural rewrites

The `sqlglot.transforms` module provides reusable transformations that generators can invoke when a target dialect lacks a particular construct or expresses it differently.

Representative transformations include:

| Transformation                         | Purpose                                                 |
| -------------------------------------- | ------------------------------------------------------- |
| `eliminate_qualify`                    | Reformulate `QUALIFY` filtering                         |
| `eliminate_distinct_on`                | Replace `DISTINCT ON` with alternative relational logic |
| `eliminate_semi_and_anti_joins`        | Reformulate specialized joins                           |
| `eliminate_full_outer_join`            | Provide an alternative to full outer joins              |
| `unnest_to_explode`                    | Adapt collection-expansion constructs                   |
| `unnest_generate_series`               | Transform sequence generation                           |
| `eliminate_window_clause`              | Resolve named window clauses                            |
| `any_to_exists`                        | Adapt certain quantified predicates                     |
| `move_ctes_to_top_level`               | Adjust CTE placement                                    |
| `remove_precision_parameterized_types` | Remove unsupported type precision parameters            |

The `preprocess()` composition helper allows generator transformations to be chained before an expression is rendered.

This creates a useful separation: a general-purpose AST remains available for analysis, while the target dialect's generator performs the structural adaptation required for output SQL.

Not every rewrite is universally applicable or semantically safe across every dialect. Applicability depends on the construct, generator rules, database behavior, and available schema/type information.

Source: [https://sqlglot.com/sqlglot/transforms.html](https://sqlglot.com/sqlglot/transforms.html?utm_source=chatgpt.com)

### 3.5 Unsupported features and strict translation

SQLGlot distinguishes parse failures from target-generation incompatibilities.

The generator exposes `unsupported_level`, with `ErrorLevel.IGNORE`, `WARN`, `RAISE`, and `IMMEDIATE` behaviors. Its default is `WARN`, meaning generation may proceed despite a reported unsupported feature.

For strict translation:

```
from sqlglot import transpilefrom sqlglot.errors import ErrorLeveltranslated = transpile(    source_sql,    read="spark",    write="postgres",    unsupported_level=ErrorLevel.RAISE,)
```

In strict mode, known unsupported transformations raise an `UnsupportedError` rather than merely logging a warning.

This is especially relevant when translating queries automatically: an apparently successful conversion may otherwise conceal a feature that could not be represented faithfully.

However, even strict unsupported handling is not a proof of semantic equivalence. Differences in implicit casts, collation, arithmetic, null ordering, temporal behavior, built-in functions, and database configuration may require independent compatibility validation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+2



Source: [https://sqlglot.com/sqlglot/generator.html](https://sqlglot.com/sqlglot/generator.html?utm_source=chatgpt.com)

## 4. Schema-aware semantic analysis

This is one of SQLGlot's most consequential capabilities. Parsing alone identifies the syntactic occurrence of a column or table; semantic resolution determines which source a reference belongs to and what type of value it represents.

SQLGlot provides substantial machinery for this process, including schema abstractions, identifier normalization, scope construction, table and column qualification, and type annotation.

### 4.1 Schema representations and catalog integration

The `sqlglot.schema` module defines a `Schema` abstraction and a `MappingSchema` implementation.

A schema may be supplied as a simple nested dictionary:

```
schema = {    "orders": {        "order_id": "INT",        "customer_id": "INT",        "amount": "DECIMAL(18, 2)",    },    "customers": {        "customer_id": "INT",        "name": "VARCHAR",    },}
```

SQLGlot also supports deeper namespace structures that represent databases and catalogs:

```
schema = {    "warehouse": {        "analytics": {            "orders": {                "id": "BIGINT",                "amount": "DOUBLE",            }        }    }}
```

The `Schema` interface exposes operations including `add_table()`, `column_names()`, `get_column_type()`, `has_column()`, and `get_udf_type()`.

`MappingSchema` also supports additional information such as column visibility and UDF return-type mappings. Internally, nested mappings and trie-based lookup facilities help resolve names across namespace depths.

This provides a useful extension boundary: an external catalog can populate or implement SQLGlot's schema interface without requiring SQLGlot itself to manage a database connection or metadata service.

It also permits selective visibility of columns, which can be relevant to schema-dependent operations such as star expansion. This is a representation capability, not an authorization system or a complete implementation of database column-access policies.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+2



Source: [https://sqlglot.com/sqlglot/schema.html](https://sqlglot.com/sqlglot/schema.html?utm_source=chatgpt.com)

### 4.2 Identifier normalization and qualification

The `qualify()` optimizer function rewrites SQL expressions to make table and column references explicit.

For example, given:

```
SELECT amount
FROM orders
```

With an appropriate schema, qualification can produce a structure equivalent to:

```
SELECT "orders"."amount" AS "amount"
FROM "orders" AS "orders"
```

This operation involves more than adding table-name prefixes. SQLGlot can normalize identifier casing, generate table aliases, expand wildcard projections, expand alias references, and resolve column names against a schema.

Important parameters include `expand_stars`, `expand_alias_refs`, `qualify_columns`, `allow_partial_qualification`, `validate_qualify_columns`, `canonicalize_table_aliases`, and `on_qualify`.

The `on_qualify` callback is particularly useful as an extension point for inspecting qualified table expressions during resolution.

Qualification is often foundational for downstream analysis because two apparently different column references may refer to the same underlying source, while identically named columns may refer to different sources.

Without qualification, a simple AST traversal may be sufficient to enumerate the columns mentioned in a query but insufficient to determine the actual table-column dependencies.

Schema completeness matters: `SELECT *` cannot generally be expanded accurately without knowledge of the source columns. Likewise, ambiguous unqualified references may require schema information or may remain unresolved when partial qualification is permitted.

Source: [https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/qualify.py](https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/qualify.py?utm_source=chatgpt.com)

### 4.3 Query scopes and name resolution

The `sqlglot.optimizer.scope` and `sqlglot.optimizer.resolver` modules expose a deeper semantic model.

A `Scope` represents the resolution context of a query expression. It tracks accessible sources, referenced columns, table aliases, and relationships with nested scopes.

SQLGlot distinguishes scope categories including root queries, subqueries, derived tables, CTEs, set operations, and user-defined table functions.

Key APIs include `build_scope()`, `traverse_scope()`, `find_all_in_scope()`, and `find_in_scope()`.

This is especially relevant for SQL containing correlated references, alias shadowing, nested CTEs, lateral relationships, or multiple query levels.

Consider:

```
SELECT c.customer_id
FROM customers AS c
WHERE EXISTS (
    SELECT 1
    FROM orders AS o
    WHERE o.customer_id = c.customer_id
)
```

A purely syntactic traversal can identify both instances of `customer_id`. Scope analysis provides the necessary context to distinguish the inner query's local `o.customer_id` reference from its correlated reference to `c.customer_id` in the outer query.

The distinction is critical for correct lineage, query rewriting, dependency analysis, and detection of correlated subqueries.

Source: [https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/scope.py](https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/scope.py?utm_source=chatgpt.com)

### 4.4 Type inference and expression annotations

The `annotate_types()` function infers expression result types and attaches them to AST nodes.

It combines schema-provided column types with expression-specific typing rules, function metadata, and coercion behavior.

For example:

```
SELECT integer_value + 2.5 AS result
FROM measurements
```

With a schema establishing the input column as an integer type, SQLGlot can infer a floating-point result type.

The mechanism is broader than simple arithmetic. SQLGlot defines rules for numeric promotion, temporal expressions, casts, functions, aggregate expressions, and structured types. The inference machinery supports dialect-specific coercion maps and expression metadata.

Important customization parameters include `expression_metadata`, `coerces_to`, and `overwrite_types`.

The `Schema.get_udf_type()` interface provides another useful interaction: externally supplied UDF signatures can contribute to expression type inference even when SQLGlot does not implement or execute the function itself.

Type annotation improves the reliability of type-sensitive canonicalization and SQL translation. It can also support static analysis of expression compatibility and expected output schemas.

However, type inference is not a complete SQL type checker. Unknown inputs, opaque functions, custom types, polymorphic behaviors, and engine-specific coercion rules may limit what can be inferred. An inferred type should not automatically be interpreted as confirmation that the target database will accept the expression.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Source: [https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/annotate_types.py](https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/annotate_types.py?utm_source=chatgpt.com)

## 5. Rule-based query optimization and canonicalization

SQLGlot includes a substantial logical query optimizer, exposed through `sqlglot.optimizer.optimize()` and its individual transformation modules.

Its primary role is to rewrite SQL ASTs into normalized or simplified logical forms. The same optimizer infrastructure also supports semantic comparison, lineage preparation, and query-plan construction.

### 5.1 Default optimization pipeline

The default optimizer applies a sequence of ordered rules.

| Rule family           | Principal operation                                                               |
| --------------------- | --------------------------------------------------------------------------------- |
| Qualification         | Resolve and normalize identifiers and sources                                     |
| Projection pushdown   | Reduce unnecessarily propagated columns                                           |
| Boolean normalization | Convert logical expressions toward CNF                                            |
| Subquery unnesting    | Rewrite qualifying subquery structures                                            |
| Predicate pushdown    | Move filters toward relevant data sources                                         |
| Join optimization     | Normalize and simplify join relationships                                         |
| Subquery elimination  | Reduce unnecessary query nesting                                                  |
| Subquery merging      | Collapse eligible nested query structures                                         |
| Join elimination      | Remove joins when the transformation is provably applicable under its assumptions |
| CTE elimination       | Remove unused CTEs                                                                |
| Identifier quoting    | Normalize identifier representation                                               |
| Type annotation       | Infer expression types                                                            |
| Canonicalization      | Standardize expressions using semantic/type information                           |
| Simplification        | Reduce expressions and predicates                                                 |

The `RULES` tuple defines the default ordering. `optimize()` also accepts a caller-supplied sequence of rules and passes recognized keyword arguments to individual rule functions.

This means the optimizer is not monolithic. A caller can apply selected passes, alter the pipeline, or introduce custom rules.

Rule ordering matters. Qualification is explicitly documented as a prerequisite for many subsequent optimizations. Removing or rearranging rules without considering these dependencies can result in incorrect rewrites or incomplete transformations.

Source: [https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/optimizer.py](https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/optimizer.py?utm_source=chatgpt.com)

### 5.2 Boolean normalization

SQLGlot provides `normalize()` for converting predicate expressions into conjunctive normal form (CNF) or disjunctive normal form (DNF).

For example, the following:

```
(x AND y) OR z
```

Can be rewritten into CNF:

```
(x OR z) AND (y OR z)
```

Canonical Boolean representations are useful when comparing predicates, pushing conditions into query branches, or analyzing the logical structure of complex filtering expressions.

An important implementation detail is the `max_distance` control. Distribution can cause a substantial increase in expression size; SQLGlot estimates normalization complexity and may skip transformations that exceed the configured threshold.

This makes normalization a bounded, opportunistic rewrite rather than a guarantee that every Boolean expression will be fully normalized.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 5.3 Relational optimization

The optimizer includes a range of relational rewrite mechanisms.

Projection pushdown attempts to avoid carrying unused columns through intermediate query levels. Predicate pushdown attempts to move filtering conditions closer to the sources that can evaluate them. Subquery elimination and merging can reduce unnecessary nesting. Join transformations can simplify eligible join relationships and normalize their representation.

These mechanisms are useful for generating cleaner intermediate query forms and preparing expressions for downstream planning.

They are subject to SQL's semantic constraints, including aggregation boundaries, correlation, outer-join null extension, predicate evaluation, and function behavior.

The optimizer should not be equated with a full database cost-based optimizer. It does not inherently select physical execution strategies based on live table cardinalities, index statistics, distributed execution costs, or hardware-specific performance models.

Its outputs may be structurally preferable or more canonical without necessarily executing faster on a particular database.

### 5.4 Expression simplification and canonicalization

The `simplify()` pass handles logical and algebraic expression reduction.

Its mechanisms include Boolean simplification, selected constant reductions, date/time expression rewrites, and type-aware expression handling. Additional controls include `constant_propagation` and `coalesce_simplification`.

Some rewrites are deliberately conservative because SQL's three-valued logic, type coercion, function semantics, and treatment of NULL can make apparently obvious algebraic transformations invalid.

A notable optional dependency is `python-dateutil`. When installed, SQLGlot can simplify certain constant date and interval expressions, including month arithmetic, that it otherwise leaves unevaluated.

This is a meaningful example of a dependency affecting semantic-analysis capability rather than merely performance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Sources:

[https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/simplify.py](https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/simplify.py?utm_source=chatgpt.com)

[https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/canonicalize.py](https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/canonicalize.py?utm_source=chatgpt.com)

### 5.5 Custom optimizer rules

Custom rules can be supplied to `optimize()` as functions that accept an expression and return an expression.

A rule may also declare supported keyword arguments, such as a schema or dialect, which the optimizer passes by matching argument names.

This provides an extensibility mechanism for domain-specific transformations without forking the main optimizer.

A custom rule could, for example, normalize a particular family of function expressions, rewrite a known relational idiom, or annotate matching subtrees.

The more complex the transformation, the more important it becomes to use qualified scopes and explicit type information rather than relying solely on syntactic patterns.

## 6. Column-level data lineage

SQLGlot includes native lineage analysis through `sqlglot.lineage`, one of its most useful higher-level capabilities.

Lineage identifies how an output column depends on expressions and input columns across a query.

### 6.1 Output-to-source tracing

The `lineage()` function takes a target output column, SQL expression, and schema information. It constructs a graph of `Node` instances describing the relevant transformations and source relationships.

For example:

```
SELECT
    customer_id,
    amount * 1.08 AS adjusted_amount
FROM orders
```

The lineage of `adjusted_amount` identifies its dependency on the `amount` column, retaining the transformation expression rather than reporting only that the `orders` table is referenced.

In more complex queries, tracing can follow dependencies through nested selections, joins, CTEs, derived tables, and set operations.

Lineage nodes carry information such as the expression, source query, name, and downstream dependency nodes.

The `Node.walk()` method traverses the lineage graph, while `Node.to_html()` creates an HTML graph representation.

### 6.2 Multi-column lineage and reusable scopes

An easily overlooked capability is that `lineage(column=None, ...)` can calculate lineage for all top-level output columns in one operation.

This returns a dictionary mapping output-column names to lineage nodes and reuses a shared cache across output columns.

The function additionally accepts:

| Parameter      | Capability                                                  |
| -------------- | ----------------------------------------------------------- |
| `sources`      | Resolve named query sources into their SQL definitions      |
| `scope`        | Reuse a previously constructed query scope                  |
| `trim_selects` | Restrict lineage source expressions to relevant projections |
| `dialect`      | Apply source-dialect semantics                              |
| `copy`         | Control AST copying                                         |
| `on_node`      | Enrich created lineage nodes through a callback             |

The `on_node` callback and `Node.payload` dictionary provide a supported extension path for attaching additional analysis data to individual lineage nodes.

The `sources` argument is particularly valuable for extending lineage through separately defined query sources. SQLGlot can expand named source expressions rather than stopping at a referenced source name.

The lineage implementation also contains specific handling for set operations, pivots, stars, and selected table-valued function constructs, though the completeness of tracing depends on the particular syntax and schema context.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



### 6.3 What lineage does and does not establish

SQLGlot's lineage is static, expression-derived lineage.

It can establish relationships implied by the SQL structure and the supplied schema. It does not independently prove that a production job executed, that a specific dataset was read at runtime, or that a particular row contributed to an output value.

It is also not a complete cross-system lineage catalog. Connecting SQL lineage across stored views, externally defined transformations, historical schema versions, dynamic SQL, and runtime-generated queries requires external metadata and orchestration.

Missing schemas, unresolved wildcard projections, dynamic identifiers, opaque functions, and unsupported constructs can leave lineage incomplete or produce unresolved dependencies.

One useful architectural distinction is between a lineage graph showing which expressions and source columns are connected and a richer semantic graph explaining the kind of dependency. SQLGlot provides the former directly; classifications such as identity-preserving mapping, conditional influence, aggregation semantics, and transformation provenance can be layered on top through additional analysis.

Source: [https://sqlglot.com/sqlglot/lineage.html](https://sqlglot.com/sqlglot/lineage.html?utm_source=chatgpt.com)

## 7. AST differencing and structural change analysis

The `sqlglot.diff` module compares two ASTs and produces a sequence of edit operations describing their differences.

Instead of comparing lines of SQL text, it compares the parsed expression structures.

### 7.1 Edit operations

The diff algorithm uses operation types including:

| Operation | Meaning                                   |
| --------- | ----------------------------------------- |
| `Insert`  | An expression appears in the target tree  |
| `Remove`  | An expression is removed                  |
| `Move`    | An expression changes structural position |
| `Update`  | A matched expression changes              |
| `Keep`    | An expression is retained across trees    |

The primary `diff()` function accepts source and target expressions, optional pre-established node matchings, and `delta_only` to restrict output to changes.

The implementation uses a ChangeDistiller-style AST matching approach. It is designed to produce more meaningful structural changes than line-based textual comparison, particularly where SQL formatting or expression placement changes.

### 7.2 Distinguishing structural from functional changes

Consider two statements differing only in whitespace or keyword capitalization. Their ASTs can be equivalent even though a textual diff reports changes.

Conversely, changing an arithmetic operator or join predicate creates a meaningful structural change that can be identified at expression level.

SQLGlot's diff can therefore serve as the foundation for SQL change review, query similarity analysis, and identifying which components of a query have changed.

A useful combination is to normalize or qualify queries before comparing their ASTs. This can reduce irrelevant differences caused by aliases, name forms, and selected expression representations.

However, AST differencing is not a general proof of semantic equivalence. Two structurally different queries may have identical results, and two similar-looking expressions may behave differently depending on schemas, NULL semantics, and engine-specific rules.

The name semantic diff should be interpreted in its AST-aware, structurally meaningful sense rather than as automated mathematical equivalence verification.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



Source: [https://sqlglot.com/sqlglot/diff.html](https://sqlglot.com/sqlglot/diff.html?utm_source=chatgpt.com)

## 8. AST serialization and query anonymization

SQLGlot provides two distinct mechanisms that are especially useful when SQL analysis extends beyond a single process: AST serialization and source-preserving anonymization.

### 8.1 AST serialization

The `sqlglot.serde` module exposes `dump()` and `load()`.

```
from sqlglot import parse_onefrom sqlglot.serde import dump, loadexpression = parse_one("SELECT a + 1 AS result FROM t")payload = dump(expression)restored = load(payload)
```

`dump()` produces a JSON-serializable list of dictionaries representing the expression tree. The representation records expression classes, parent-child argument relationships, array positions, and supported node attributes such as type annotations, comments, and metadata.

Unlike saving the generated SQL string, serialization can retain structural information that is relevant to subsequent AST analysis.

It therefore supports use cases such as persisting parsed queries, transferring expression trees between processing stages, or caching expensive parsing and annotation results.

The distinction between `dump()` and `Expression.sql()` is important:

| Representation                 | Retains                                                 | Does not inherently provide                           |
| ------------------------------ | ------------------------------------------------------- | ----------------------------------------------------- |
| SQL text                       | Executable or inspectable SQL syntax                    | Complete analysis annotations or object relationships |
| Serialized AST                 | Expression structure, supported types and metadata      | A documented, permanently stable interchange standard |
| Custom semantic representation | Whatever domain-specific facts are explicitly extracted | Automatic SQLGlot reconstruction unless adapted       |

The serialized representation uses SQLGlot's internal expression-class model. Consequently, applications storing ASTs long term should treat the format as version-coupled unless compatibility has been established by testing. The loader also supports resolving custom expression classes, which makes validation and trusted provenance important when accepting serialized payloads from external parties.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



Source: [https://sqlglot.com/sqlglot/serde.html](https://sqlglot.com/sqlglot/serde.html?utm_source=chatgpt.com)

### 8.2 Source-preserving anonymization

The `sqlglot.anonymize` module is a less obvious and particularly useful feature.

`anonymize()` replaces selected sensitive tokens, including identifiers, literals, numeric values, and variables, with consistent aliases that preserve the original character widths. It also blanks comments and hint bodies.

The companion `render()` function reconstructs the anonymized SQL while preserving its positional layout.

This differs materially from parsing an AST and generating new SQL. AST regeneration can change whitespace and source positions; SQLGlot's anonymization mechanism is explicitly designed to preserve the source's length and token alignment.

That makes it valuable for diagnostic traces, error highlighting, query-pattern inspection, and sharing SQL examples while obscuring many source-specific values.

However, the mechanism should not be confused with formally verified data anonymization. Length, structural patterns, SQL keywords, and contextual information may remain visible. Any use involving sensitive data requires checking whether the resulting representation satisfies the applicable disclosure requirements.

The function also mutates a supplied token list, another relevant detail for consumers retaining token objects for later analysis.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



Source: [https://sqlglot.com/sqlglot/anonymize.html](https://sqlglot.com/sqlglot/anonymize.html?utm_source=chatgpt.com)

## 9. JSONPath parsing and semi-structured expressions

SQLGlot contains a separate JSONPath parser, available through `sqlglot.jsonpath.parse()`.

```
from sqlglot.jsonpath import parsepath = parse("$.customers[0].address.city")
```

This returns an `exp.JSONPath` expression rather than leaving the JSONPath as an opaque string.

The JSONPath expression family includes representations for field access, array indexing, wildcards, recursive traversal, slices, selectors, unions, and other supported path constructs.

A dedicated `JSONPathTokenizer` handles lexical conventions that differ from SQL tokenization. The parser is also dialect-aware, allowing JSON path handling to participate in SQLGlot's database-specific expression processing.

This feature matters for SQL dialects whose JSON functions embed meaningful path syntax inside string arguments. Treating those strings as structured expressions can enable more precise inspection, transformation, or comparison of semi-structured-data access.

The distinction is between SQLGlot's representation and parsing of JSONPath expressions and a general-purpose JSONPath evaluation engine. This module does not, on its own, provide complete JSON-document querying or establish compatibility with every vendor-specific JSONPath extension.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



Source: [https://sqlglot.com/sqlglot/jsonpath.html](https://sqlglot.com/sqlglot/jsonpath.html?utm_source=chatgpt.com)

## 10. Logical query planning and Python execution

SQLGlot includes an internal query planner and executor. These components are architecturally interesting because they demonstrate that its AST and optimizer are sufficiently expressive to support actual query interpretation, not just SQL regeneration.

### 10.1 Logical plan construction

The `sqlglot.planner.Plan` class converts an expression into an executable dependency graph.

Its plan representation contains specialized steps such as:

| Plan step      | Responsibility                               |
| -------------- | -------------------------------------------- |
| `Scan`         | Obtain and project data from a source        |
| `Join`         | Combine source relations                     |
| `Aggregate`    | Group rows and compute aggregate expressions |
| `Sort`         | Apply ordering                               |
| `SetOperation` | Combine results of set expressions           |

`Plan.root`, `Plan.leaves`, and `Plan.dag` expose the structure and dependencies of the resulting plan.

These are not merely rendering conveniences. The planner establishes a bridge between relational expressions and operational steps. It also provides a foundation for inspecting the execution dependencies implied by an optimized query.

The plan should nevertheless be distinguished from a production database's physical execution plan. SQLGlot does not provide a general cost model for choosing indexes, storage layouts, distributed exchange operators, or engine-specific physical algorithms.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



Source: [https://sqlglot.com/sqlglot/planner.html](https://sqlglot.com/sqlglot/planner.html?utm_source=chatgpt.com)

### 10.2 In-memory Python execution

The public `sqlglot.executor.execute()` function can run supported queries over Python-resident tables.

```
from sqlglot.executor import executeresult = execute(    "SELECT category, SUM(amount) AS total "    "FROM sales GROUP BY category",    tables={        "sales": [            {"category": "A", "amount": 10},            {"category": "A", "amount": 15},            {"category": "B", "amount": 20},        ]    },)
```

Execution combines schema preparation, optimization, planning, and Python evaluation. The executor supports relational operations such as scans, joins, aggregation, ordering, and set operations, along with supported subquery expressions.

`PythonExecutor` exposes an execution environment that can be extended with supplied functions. Internally, SQL expressions are generated into Python expression code and compiled for evaluation.

The execution infrastructure includes an explicit `Table` representation and evaluation helpers for SQL-oriented behavior.

The resulting capability is useful for small test datasets, inspecting query behavior, and developing or experimenting with SQL transformations. It can also act as a reference implementation of selected relational semantics.

It is not intended as a high-performance analytical engine. The project itself positions Python execution as suitable primarily for testing and experimentation. Nor should it be regarded as a secure sandbox for arbitrary untrusted SQL: its internal evaluation mechanism compiles generated Python expressions, and the documented executor does not establish an isolation boundary.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+2



Sources:

[https://sqlglot.com/sqlglot/executor.html](https://sqlglot.com/sqlglot/executor.html?utm_source=chatgpt.com)

[https://sqlglot.com/sqlglot/executor/python.html](https://sqlglot.com/sqlglot/executor/python.html?utm_source=chatgpt.com)

[https://sqlglot.com/sqlglot/executor/env.html](https://sqlglot.com/sqlglot/executor/env.html?utm_source=chatgpt.com)

### 10.3 The planner as an extension boundary

The internal execution design also exposes a useful architectural possibility.

SQLGlot separates parsing, semantic normalization, logical planning, and evaluation. That separation allows an alternative executor to consume structured logical operations rather than implementing SQL parsing and relational interpretation from the beginning.

For example, an application could theoretically translate supported plan steps into operations performed by Arrow, NumPy, another SQL engine, or custom computation kernels.

This is an architectural extension opportunity, not a claim that SQLGlot ships a complete Arrow-backed or distributed execution backend. The work required to preserve SQL semantics, manage data movement, implement operator coverage, and optimize performance would remain substantial.

## 11. Extensibility: dialects, grammars, expressions, and transformation rules

SQLGlot is designed to be extended at several distinct layers. This is especially valuable because many SQL variants differ in only a subset of their lexical, syntactic, or generation rules.

### 11.1 Custom SQL dialects

A dialect is represented by a subclass of `Dialect`, typically with customized `Tokenizer`, `Parser`, and `Generator` components.

| Extension layer      | Principal controls                                                      | What it enables                                    |
| -------------------- | ----------------------------------------------------------------------- | -------------------------------------------------- |
| Tokenizer            | `KEYWORDS`, `QUOTES`, `IDENTIFIERS`, lexical settings                   | Custom SQL tokens, operators, quoting conventions  |
| Parser               | Expression parsers, `FUNCTIONS`, parsing-method overrides               | Vendor-specific constructs and function syntax     |
| Generator            | `TRANSFORMS`, `TYPE_MAPPING`, SQL methods                               | Custom output syntax and structural translations   |
| Dialect semantics    | Identifier normalization, indexing, coercion, other capability settings | Correct interpretation of engine-specific behavior |
| AST expression model | `exp.Expr` subclasses and expression arguments                          | Structured representations for new constructs      |

A custom dialect can inherit most behavior from an existing dialect, overriding only the necessary differences.

For example, a dialect may reuse PostgreSQL parsing conventions while adding a proprietary function family and modifying generation of a particular data type.

This layered approach avoids having to fork or duplicate an entire SQL grammar.

Importantly, a custom generator can perform complex transformations on normalized expressions, not merely replace strings. Consequently, specialized dialect support can remain compatible with common AST traversal, semantic analysis, and optimizer operations where the underlying expressions are supported.

Source: [https://github.com/tobymao/sqlglot/blob/main/posts/onboarding.md](https://github.com/tobymao/sqlglot/blob/main/posts/onboarding.md?utm_source=chatgpt.com)

### 11.2 Independently packaged dialect plugins

SQLGlot supports third-party dialect plugins through Python package entry points in the `sqlglot.dialects` group.

A plugin may register a dialect class under a name such as `mydb`, after which SQLGlot can discover it and use that name in parsing and transpilation.

This is a released capability introduced in v28.6.0, not a development-only proposal.

The distinction between subclassing and plugin packaging is useful: subclassing defines the dialect's behavior, while entry-point registration distributes that behavior without requiring changes to SQLGlot's upstream repository.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



Source: [https://github.com/tobymao/sqlglot#creating-a-dialect-plugin](https://github.com/tobymao/sqlglot?utm_source=chatgpt.com#creating-a-dialect-plugin)

### 11.3 Other extension surfaces

Custom dialects are only one form of extensibility. SQLGlot also supports custom optimizer rules, schema implementations, expression types, transformation callbacks, lineage-node annotations, and custom function environments for Python execution.

These facilities permit different kinds of additional semantics to be introduced at the relevant processing stage.

For instance, a custom function could be represented as an expression, assigned a return type through schema metadata, handled by an optimizer rule, and rendered using a dialect-specific generator.

Those pieces are complementary but not automatically integrated: adding a parser function does not by itself establish its return type, runtime behavior, or equivalent implementation in every output dialect.

That separation is a strength when building specialized tooling, provided the integration maintains consistent semantics across the relevant layers.

## 12. Diagnostics, command-line tooling, and operational use

### 12.1 Structured parsing errors

SQLGlot defines a hierarchy of errors including `ParseError`, `TokenError`, `UnsupportedError`, `OptimizeError`, `SchemaError`, and `ExecuteError`.

`ParseError.errors` exposes structured diagnostic records with fields such as descriptions, line and column information, source context, and highlighted text.

This is more useful for programming agents, editors, and validation systems than relying solely on exception-message strings.

The parser supports multiple error-handling policies through `ErrorLevel`:

| Level       | Behavior                 |
| ----------- | ------------------------ |
| `IGNORE`    | Ignore reported errors   |
| `WARN`      | Log errors               |
| `RAISE`     | Collect errors and raise |
| `IMMEDIATE` | Raise at the first error |

These policies allow different parsing workflows to balance error recovery against strict failure behavior.

However, parser error reporting remains syntactic in character. A successful parse is not a guarantee of complete semantic validity or target-engine acceptance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



Source: [https://sqlglot.com/sqlglot/errors.html](https://sqlglot.com/sqlglot/errors.html?utm_source=chatgpt.com)

### 12.2 Command-line interface

SQLGlot exposes a CLI through `python -m sqlglot`.

It supports source and target dialect selection, formatting, AST inspection, token inspection, and error-handling configuration.

```
# Translate SQL between dialects
python -m sqlglot \
  "SELECT CAST(x AS INT) FROM t" \
  --read spark \
  --write duckdb

# Inspect the expression tree
python -m sqlglot "SELECT a FROM t" --parse

# Inspect tokens
python -m sqlglot "SELECT a FROM t" --tokenize

# Process SQL from standard input
cat query.sql | python -m sqlglot - --read postgres --write duckdb
```

The CLI additionally exposes `--identify`, `--no-pretty`, `--error-level`, and `--version`.

This is useful for inspecting parsing behavior, diagnosing dialect differences, and applying straightforward translations without constructing a separate Python program.

It is not a database administration CLI, a query-profile interface, or an execution-monitoring system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source: [https://github.com/tobymao/sqlglot/blob/main/sqlglot/\_\_main\_\_.py](https://github.com/tobymao/sqlglot/blob/main/sqlglot/__main__.py?utm_source=chatgpt.com)

## 13. Installation, compiled acceleration, and versioning

SQLGlot's default installation has no required third-party runtime dependencies.

```
pip install sqlglot
```

For higher parsing performance, SQLGlot provides an optional mypyc-compiled implementation distributed through `sqlglotc`:

```
pip install "sqlglot[c]"
```

The compiled distribution is supported for Python 3.10 and later. On Python 3.9, the extra falls back to the pure-Python implementation.

### 13.1 Compiled versus pure-Python execution

The project reports that its compiled implementation is roughly 3–5 times faster for parsing than the pure-Python implementation in its published benchmarks.

Its current benchmark suite uses Python 3.14.3 and includes several SQL query shapes, ranging from short statements to large expressions and join-heavy queries.

This improvement should be interpreted as an upstream parsing benchmark, not a guaranteed whole-pipeline speedup. Workloads dominated by schema resolution, optimizer passes, graph traversal, application callbacks, or external database operations may benefit differently.

A consequential tradeoff is that the mypyc-compiled implementation disables certain runtime subclassing behavior for performance reasons. The project specifically warns that custom dialect subclasses may not work correctly with `sqlglot[c]`.

Thus the pure-Python distribution can be preferable when extending tokenizer, parser, or generator classes, while the compiled distribution is attractive for workloads primarily consuming built-in dialect capabilities.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



### 13.2 Status of the former Rust acceleration path

Older SQLGlot documentation discusses `sqlglotrs`, a Rust-based tokenizer acceleration package.

For the current 30.x release, this guidance is outdated. The upstream source explicitly warns that `sqlglot[rs]` is deprecated and no longer compatible, and directs users toward `sqlglot[c]` instead.

Although the `rs` extra remains visible in PyPI metadata, it should not be interpreted as the preferred or current acceleration mechanism.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Source: [https://github.com/tobymao/sqlglot/blob/main/sqlglot/tokens.py](https://github.com/tobymao/sqlglot/blob/main/sqlglot/tokens.py?utm_source=chatgpt.com)

### 13.3 Version compatibility

SQLGlot's versioning policy differs from conventional interpretations of semantic versioning.

The project states that:

- Patch releases are intended to be backward compatible.
- Minor releases can contain backward-incompatible changes.
- Major releases represent significant backward-incompatible changes.

This has practical consequences for applications using internal AST structures, optimizer behavior, dialect subclasses, or generated SQL as part of persistent interfaces.

Pinning an appropriate release range and testing the SQLGlot-specific integration surface is particularly important where updates could silently change generated SQL or transformation behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



Source: [https://github.com/tobymao/sqlglot#versioning](https://github.com/tobymao/sqlglot?utm_source=chatgpt.com#versioning)

## 14. Capability composition and architectural opportunities

The greatest value of SQLGlot often comes from combining its capabilities rather than treating each operation independently.

The following are general architectural patterns enabled by the verified components, not turnkey applications delivered by SQLGlot.

| Problem class                  | Useful capability combination                                         | Resulting opportunity                                                                        |
| ------------------------------ | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Cross-dialect SQL adaptation   | Dialect parsing → AST transforms → strict generation                  | Maintain one transformation model instead of many source-target string translators           |
| Query impact analysis          | Schema qualification → scope analysis → lineage                       | Determine which output expressions depend on changed columns or sources                      |
| SQL change review              | Parse → canonicalize → AST diff                                       | Distinguish meaningful structural changes from formatting differences                        |
| SQL-aware static analysis      | Parse → scope resolution → AST traversal                              | Implement checks over resolved SQL structure rather than text patterns                       |
| Query fingerprinting           | Parse → normalize → anonymize or serialize                            | Group related query forms while controlling irrelevant textual variation                     |
| Schema-informed transformation | Catalog metadata → qualification → type annotations → optimizer rules | Build transformations with stronger information about source references and expression types |
| Multi-engine query generation  | AST builders → semantic transforms → dialect generators               | Separate logical query construction from target-specific SQL syntax                          |
| Small-scale execution checks   | Parse → optimize → plan → Python executor                             | Test supported query behavior without provisioning a database engine                         |

A particularly important pattern is parse once, perform multiple analyses, then generate or persist the result.

For example, a qualified AST can support dependency extraction, structural inspection, type annotation, and subsequent rewriting. Reusing the appropriate semantic representation reduces the need for separate SQL interpretation implementations.

Such reuse still requires care: optimizer passes mutate or replace AST nodes, lineage can independently qualify expressions, and serialized representations may carry metadata with version-specific assumptions. Copying trees or explicitly managing the lifecycle of analyzed ASTs can be necessary.

The broader architectural lesson is that SQLGlot supplies a substantial portion of the SQL front end needed by advanced data systems: parsing, common representation, semantic resolution, transformations, and code generation. Systems can focus their bespoke logic on additional domain semantics and execution requirements rather than recreating those foundational components.

## 15. Ecosystem boundaries and complementary tools

SQLGlot is used by projects including SQLMesh, Apache Superset, Dagster, Ibis, dlt, Fugue, and SQLFrame, according to the upstream project's published integration list. That demonstrates its applicability across SQL transformation, analytics, orchestration, and expression-generation systems, though the exact level of integration differs by project.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



It is important to distinguish what SQLGlot provides from adjacent capabilities.

| Adjacent technology                   | Primary distinction                                                                                                                                       |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sqlparse`                            | Tokenization, parsing-like grouping, and formatting without SQLGlot's comparable semantic optimizer and dialect-neutral transformation framework          |
| SQLFluff                              | SQL linting, style rules, and automated code-quality fixes; overlaps in parsing but has a different primary purpose                                       |
| SQLAlchemy                            | Database connectivity, SQL expression construction, ORM, and database interaction; SQLGlot focuses on analyzing and transforming SQL syntax and semantics |
| Apache Calcite                        | Broader relational query planning and optimization framework in the JVM ecosystem                                                                         |
| SQLMesh                               | SQL-based data transformation and model orchestration platform that uses SQLGlot; not functionality bundled into SQLGlot itself                           |
| DuckDB / PostgreSQL / other databases | Actual query execution engines, catalogs, indexes, transaction handling, and physical execution optimization                                              |
| Apache Arrow / DataFusion             | Columnar data representation and analytical execution infrastructure; SQLGlot does not provide their computational kernels                                |

These boundaries create several possible integration patterns.

SQLGlot can parse and rewrite queries that are ultimately executed by PostgreSQL, DuckDB, or another SQL engine. It can contribute semantic analysis to a data catalog without replacing that catalog. And its AST can serve as a front-end representation for a separate relational execution system.

However, SQLGlot does not expose a universal, production-ready compiler that automatically translates arbitrary ASTs into DataFusion plans, Arrow compute expressions, or SQLAlchemy expressions. Those integrations require explicit semantic mappings and additional implementation.

## 16. Cross-cutting limitations and correctness considerations

A useful way to assess SQLGlot is to distinguish the guarantees of its different processing stages.

| Stage            | What it can establish                                                | What it cannot establish on its own                                                       |
| ---------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Tokenization     | Recognized lexical components and their source positions             | Full SQL syntactic validity                                                               |
| Parsing          | An expression structure understood by the chosen grammar             | Database acceptance or runtime correctness                                                |
| Qualification    | Resolution under supplied schemas and dialect rules                  | Accuracy of an incomplete or stale catalog                                                |
| Type annotation  | Inferred types under supported typing/coercion rules                 | Exact runtime types for every vendor function and configuration                           |
| Optimization     | Application of supported logical rewrite rules                       | Better physical performance on every database                                             |
| Transpilation    | Target-dialect SQL generation with known incompatibility diagnostics | Guaranteed semantic equivalence for all statements                                        |
| Lineage          | Dependencies inferred from supplied SQL and schemas                  | Actual runtime or row-level provenance                                                    |
| Structural diff  | Expression-tree changes and correspondences                          | Mathematical equivalence or identical query results                                       |
| Python execution | Evaluation of supported operations over Python data                  | Full engine compatibility, production-scale performance, or safe arbitrary-code isolation |

Several recurring issues deserve particular attention.

Dialect specificity. SQLGlot's permissive default grammar is useful for broad ingestion but is not a substitute for specifying the source dialect when known. Parsing the same text under different dialect rules may produce different interpretations.

Identifier semantics. Case sensitivity, quoting, catalog hierarchy, and alias resolution can alter the meaning of references. Qualification and name normalization must be interpreted using the appropriate dialect and schema context.

SQL NULL semantics. SQL's three-valued logic makes many intuitive algebraic rewrites unsafe. Particular care is warranted around predicate simplification, joins, `NOT IN`, and null-sensitive expressions.

Unimplemented semantics. A recognized function or expression is not necessarily fully understood for typing, optimization, lineage, translation, and execution. The presence of an AST node alone does not guarantee support across all processing stages.

Dynamic SQL and external semantics. Queries assembled at runtime, temporary objects, stored procedures, UDF implementations, views defined outside the supplied source set, and engine-specific settings can introduce dependencies that static AST analysis cannot infer automatically.

Security boundaries. SQLGlot can support structural checks over SQL, but permissive parsing, optimization, or strict transpilation should not be treated as sufficient proof that arbitrary user-supplied SQL is safe. Authorization, statement restrictions, resource controls, and execution isolation remain separate responsibilities.

Source preservation. General AST transformations are not lossless source edits. Applications requiring exact source positions, unchanged formatting, or faithful comment placement must distinguish token-oriented operations from expression-tree regeneration.

These limitations do not diminish SQLGlot's utility; they define where a reusable SQL compiler front end ends and where engine-aware validation, metadata, policy, or runtime systems must begin.

## Primary-source reference map

| Subject                                     | Official source                                                                                                                                                                             |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Project, installation, versioning, dialects | [https://github.com/tobymao/sqlglot](https://github.com/tobymao/sqlglot?utm_source=chatgpt.com)                                                                                             |
| API documentation                           | [https://sqlglot.com/sqlglot.html](https://sqlglot.com/sqlglot.html?utm_source=chatgpt.com)                                                                                                 |
| AST expression model                        | [https://sqlglot.com/sqlglot/expressions/core.html](https://sqlglot.com/sqlglot/expressions/core.html?utm_source=chatgpt.com)                                                               |
| Expression builders                         | [https://sqlglot.com/sqlglot/expressions/builders.html](https://sqlglot.com/sqlglot/expressions/builders.html?utm_source=chatgpt.com)                                                       |
| AST primer                                  | [https://github.com/tobymao/sqlglot/blob/main/posts/ast_primer.md](https://github.com/tobymao/sqlglot/blob/main/posts/ast_primer.md?utm_source=chatgpt.com)                                 |
| Tokenizer                                   | [https://sqlglot.com/sqlglot/tokens.html](https://sqlglot.com/sqlglot/tokens.html?utm_source=chatgpt.com)                                                                                   |
| Parser                                      | [https://sqlglot.com/sqlglot/parser.html](https://sqlglot.com/sqlglot/parser.html?utm_source=chatgpt.com)                                                                                   |
| Dialect architecture                        | [https://sqlglot.com/sqlglot/dialects.html](https://sqlglot.com/sqlglot/dialects.html?utm_source=chatgpt.com)                                                                               |
| SQL generator                               | [https://sqlglot.com/sqlglot/generator.html](https://sqlglot.com/sqlglot/generator.html?utm_source=chatgpt.com)                                                                             |
| Generator transformations                   | [https://sqlglot.com/sqlglot/transforms.html](https://sqlglot.com/sqlglot/transforms.html?utm_source=chatgpt.com)                                                                           |
| Schema abstractions                         | [https://sqlglot.com/sqlglot/schema.html](https://sqlglot.com/sqlglot/schema.html?utm_source=chatgpt.com)                                                                                   |
| Optimizer                                   | [https://sqlglot.com/sqlglot/optimizer.html](https://sqlglot.com/sqlglot/optimizer.html?utm_source=chatgpt.com)                                                                             |
| Qualification                               | [https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/qualify.py](https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/qualify.py?utm_source=chatgpt.com)               |
| Scope analysis                              | [https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/scope.py](https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/scope.py?utm_source=chatgpt.com)                   |
| Type annotation                             | [https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/annotate_types.py](https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/annotate_types.py?utm_source=chatgpt.com) |
| Simplification                              | [https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/simplify.py](https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/simplify.py?utm_source=chatgpt.com)             |
| Column lineage                              | [https://sqlglot.com/sqlglot/lineage.html](https://sqlglot.com/sqlglot/lineage.html?utm_source=chatgpt.com)                                                                                 |
| AST differencing                            | [https://sqlglot.com/sqlglot/diff.html](https://sqlglot.com/sqlglot/diff.html?utm_source=chatgpt.com)                                                                                       |
| AST serialization                           | [https://sqlglot.com/sqlglot/serde.html](https://sqlglot.com/sqlglot/serde.html?utm_source=chatgpt.com)                                                                                     |
| Anonymization                               | [https://sqlglot.com/sqlglot/anonymize.html](https://sqlglot.com/sqlglot/anonymize.html?utm_source=chatgpt.com)                                                                             |
| JSONPath parser                             | [https://sqlglot.com/sqlglot/jsonpath.html](https://sqlglot.com/sqlglot/jsonpath.html?utm_source=chatgpt.com)                                                                               |
| Logical planner                             | [https://sqlglot.com/sqlglot/planner.html](https://sqlglot.com/sqlglot/planner.html?utm_source=chatgpt.com)                                                                                 |
| Python SQL executor                         | [https://sqlglot.com/sqlglot/executor.html](https://sqlglot.com/sqlglot/executor.html?utm_source=chatgpt.com)                                                                               |
| Error and diagnostic types                  | [https://sqlglot.com/sqlglot/errors.html](https://sqlglot.com/sqlglot/errors.html?utm_source=chatgpt.com)                                                                                   |
| Current PyPI release                        | [https://pypi.org/project/sqlglot/30.27.0/](https://pypi.org/project/sqlglot/30.27.0/?utm_source=chatgpt.com)                                                                               |

## Overall assessment

SQLGlot's defining strength is not simply that it supports many SQL dialects. It is the combination of a normalized SQL expression model, schema-aware name resolution, type inference, reusable relational rewrites, structural comparison, lineage, and dialect-specific generation within one coherent library.

Its most consequential and easily overlooked capabilities are the scope-resolution system, customizable optimization passes, type-aware canonicalization, lineage graph construction, AST differencing, serialization, and the extensible logical planner. Together, these provide infrastructure for SQL intelligence that goes substantially beyond a conventional parser or formatter.

The primary architectural tradeoff is that SQLGlot provides sophisticated static SQL understanding without complete knowledge of runtime database semantics. Its value is highest when that boundary is made explicit: SQLGlot supplies the reusable language-processing machinery, while external catalogs, databases, and application logic provide the contextual information and guarantees it cannot independently establish.

For advanced Python systems that must understand, transform, compare, or generate SQL programmatically, SQLGlot is therefore best regarded as a general-purpose SQL compiler front end and semantic transformation framework, rather than merely a dialect converter.

# SQLGlot — Advanced Capabilities Addendum

Research date: November 1, 2026 | Target release: SQLGlot 30.27.0 (October 30, 2026) | Python

Purpose: Supplement the existing SQLGlot capability overview with the advanced functionality, architectural distinctions, and ecosystem boundaries identified in the gap analysis. This addendum concentrates on capabilities not adequately developed in the original reference rather than repeating its existing treatment of parsing, optimization, lineage, structural differencing, and execution.

The findings are grounded in SQLGlot's official API documentation and upstream implementation. The target release is confirmed on PyPI. API illustrations are based on documented interfaces and source inspection; they are not presented as results of an independent compatibility test suite.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



## 1. Expression architecture: traits, concrete nodes, and behavioral interfaces

### 1.1 Corrected class hierarchy

SQLGlot 30.27.0 distinguishes between `exp.Expr` and `exp.Expression`. They are not aliases.

- `Expr` is the common expression interface/base, declared with `@trait`. It defines the broad contract for traversable SQL expressions, including structural access, mutation, SQL generation, metadata handling, operator construction, and transformation methods.
- `Expression` is a separate concrete subclass of `Expr`. It implements the underlying expression representation, including argument storage, parent relationships, comments, inferred types, metadata, structural hashing, and mutation behavior.
- Other traits supply reusable behavioral interfaces, allowing expression classes to expose capabilities independently of their particular SQL syntax.

The resulting architecture is better understood as a combination of a concrete expression representation and reusable semantic or behavioral interfaces, rather than a single inheritance hierarchy whose subclasses correspond exclusively to SQL grammar productions.

The source establishes the distinction directly:

```
@traitclass Expr:    ...class Expression(Expr):    ...
```

A representative query expression then combines the concrete implementation with another behavioral interface:

```
class Select(Expression, Query):    ...
```

The expression model therefore supports multiple inheritance in which behavioral traits supplement concrete SQL node classes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



### 1.2 Principal behavioral traits

Several important traits define what an expression can do rather than merely what syntactic construct it represents.

| Trait or interface | Responsibility                                                                            |
| ------------------ | ----------------------------------------------------------------------------------------- |
| `Expr`             | Common expression operations, traversal, transformation, structural inspection            |
| `Selectable`       | Access to projected expressions and their output names                                    |
| `Query`            | Query operations, including CTEs, filtering, ordering, limits, and set-operation builders |
| `DerivedTable`     | Relational expressions usable as derived-table sources                                    |
| `UDTF`             | Table-valued expression behavior and projected output structure                           |
| `Condition`        | Expressions participating in logical conditions                                           |
| `Predicate`        | Boolean-valued SQL conditions                                                             |
| `TimeUnit`         | Shared behavior for temporal units                                                        |
| `IntervalOp`       | Shared structure for interval-oriented operations                                         |

This enables capabilities such as `selects` to be shared by different kinds of expressions, rather than being tied exclusively to `Select`.

For example, a derived relational expression may expose projected output columns without being represented as an ordinary `SELECT` node.

A distinction worth preserving is that traits are interfaces and behavioral abstractions, not a guarantee of full relational semantics. The availability of a method such as `selects` does not establish that every downstream analysis understands the semantics of every expression implementing that interface.

### 1.3 Implications for extension and static inspection

The trait architecture has several consequences for systems operating on SQLGlot expression trees.

Capability-oriented type inspection. A transformation can identify expressions supporting a particular behavioral interface, rather than maintaining an exhaustive list of concrete node types. For example, checking whether a node implements `Selectable` is conceptually different from checking whether it is specifically a `Select`.

Reusable extension behavior. New expression classes can compose relevant interfaces alongside concrete expression implementation. This allows extensions to participate in common APIs where the inherited behavior is appropriate.

Method-resolution considerations. Multiple inheritance makes method-resolution order relevant. A subclass extending SQLGlot must account for methods supplied by traits, methods implemented by `Expression`, and its own overrides.

Representation versus validity. Concrete expressions declare supported arguments using `arg_types`, with required arguments reflected in `required_args`. This provides structured information about AST shape, but is not a complete database semantic type system or grammar validator.

Implementation caveat. These are Python class relationships implemented by SQLGlot, not an independently specified protocol intended to remain stable across arbitrary versions. Expression extensions should be evaluated against the target release, particularly where compiled distributions or subclassing constraints are involved.

Primary sources:

`https://sqlglot.com/sqlglot/expressions/core.html`

`https://sqlglot.com/sqlglot/expressions/query.html`

## 2. Recursive source expansion, query substitution, and table-identity transformations

SQLGlot provides native mechanisms for composing independently defined SQL queries into larger expression trees. These mechanisms are particularly significant because they can replace substantial amounts of custom SQL substitution, reference normalization, and query-definition expansion logic.

### 2.1 Recursive source expansion with `exp.expand()`

`exp.expand()` replaces references to named SQL sources with derived-table expressions containing their definitions.

Its documented signature is:

```
exp.expand(    expression,    sources,    dialect=None,    copy=True,)
```

The `sources` argument is a dictionary mapping source names to `exp.Query` objects or zero-argument callables returning queries.

Consider three SQL definitions:

```
-- Logical source: active_orders
SELECT customer_id, amount
FROM orders
WHERE status = 'active';

-- Logical source: customer_totals
SELECT customer_id, SUM(amount) AS total
FROM active_orders
GROUP BY customer_id;

-- Consuming query
SELECT customer_id, total
FROM customer_totals
WHERE total > 1000;
```

The consuming query can be expanded using SQLGlot's expression API:

```
from sqlglot import exp, parse_onesources = {    "active_orders": parse_one(        "SELECT customer_id, amount "        "FROM orders WHERE status = 'active'"    ),    "customer_totals": parse_one(        "SELECT customer_id, SUM(amount) AS total "        "FROM active_orders GROUP BY customer_id"    ),}query = parse_one(    "SELECT customer_id, total "    "FROM customer_totals WHERE total > 1000")expanded = exp.expand(query, sources)
```

The resulting AST contains nested derived tables corresponding to the definitions of `customer_totals` and `active_orders`.

The transformation recursively expands source references found inside substituted definitions. Consequently, a caller does not need to manually traverse the dependency chain and construct each nested subquery.

The upstream implementation performs several additional operations:

- Normalizes source names using dialect-aware table-name normalization.
- Looks up source definitions through the normalized names.
- Preserves the referenced table alias, using the source name as the alias when one is absent.
- Invokes callable definitions on demand.
- Attaches comments identifying the original logical source, such as `/* source: customer_totals */`.
- Supports copying the input expression before transformation.

These behaviors mean the transformation operates on SQL structure rather than substituting fragments of text.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



Architectural significance. Source expansion can expose the internal operations of separately defined SQL models to later SQLGlot passes. Once definitions have been substituted into the expression tree, subsequent analysis can inspect filters, projections, aggregation boundaries, and underlying table references that were previously hidden behind logical source names.

This is useful for query-model composition, dependency investigation, view-definition expansion, and static SQL analysis spanning multiple definitions.

### 2.2 Source expansion is not a dependency manager

Although `expand()` is recursive, several responsibilities remain outside the helper.

Circular dependencies. The implementation recursively transforms substituted queries without establishing a general dependency-cycle detection mechanism. Cyclic source definitions require caller-side detection or other safeguards to prevent unbounded expansion.

Name resolution and shadowing. Expansion operates by matching normalized table references. It is not a substitute for complete scope-aware resolution. A local CTE with the same name as an external logical source, for example, creates a potential naming conflict that must be handled deliberately.

Definition identity. The source mapping does not inherently distinguish a stored view, materialized table, transient model, or versioned definition. Those distinctions require external metadata.

Expansion size. Repeatedly referenced definitions can be duplicated into large nested trees. This can increase the work required for later normalization, optimization, serialization, or SQL generation.

Semantic preservation. Substituting a query as a derived table can change the context in which identifiers, aliases, or engine-specific constructs are interpreted. SQLGlot provides the AST transformation; it does not prove that every substitution is equivalent under every database's view and query semantics.

The resulting design distinction is that `expand()` is a query-definition substitution primitive, not a complete system for managing SQL model dependencies, versioning, materialization, and runtime evaluation.

### 2.3 Physical-reference discovery and table rewriting

Several complementary expression utilities support narrower operations.

| API                          | Principal behavior                                                                              | Important distinction                                                      |
| ---------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `exp.find_tables()`          | Returns a set of referenced `Table` expressions, excluding references recognized as CTE sources | Does not classify tables versus views or determine actual object existence |
| `exp.replace_tables()`       | Rewrites matching `Table` expressions using a name mapping                                      | Changes references rather than expanding definitions                       |
| `exp.column_table_names()`   | Extracts table qualifiers appearing on `Column` expressions                                     | Reports syntactic qualifiers, not resolved ownership                       |
| `exp.table_name()`           | Converts a table identity into a full name string                                               | Supports dialect-aware rendering and identifier quoting                    |
| `exp.normalize_table_name()` | Normalizes table-name components according to dialect rules                                     | Useful for consistent lookup keys                                          |
| `exp.rename_table()`         | Builds a structured `ALTER TABLE ... RENAME` expression                                         | Constructs DDL rather than rewriting existing query references             |
| `exp.rename_column()`        | Builds a structured column-renaming `ALTER` expression                                          | Includes an optional existence condition                                   |

`replace_tables()` is more sophisticated than simple string replacement: it normalizes mapping keys, preserves non-name table arguments when constructing replacements, and adds a comment recording the original table name.

It also honors the node metadata convention `meta_get("replace") is False`, allowing individual references to be excluded from that transformation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+3



A useful distinction is that `replace_tables()` is a general AST table-reference rewrite, whereas `find_tables()` consults query scopes to distinguish ordinary source references from CTE references. They do not offer identical scope semantics.

Primary source: `https://sqlglot.com/sqlglot/expressions/builders.html`

## 3. Structured SQL templates and AST-level placeholder substitution

SQLGlot provides a native mechanism for substituting reusable SQL placeholders with typed expressions or converted Python values.

The key API is:

```
exp.replace_placeholders(    expression,    *args,    **kwargs,)
```

Unlike string interpolation, this operates on SQLGlot's `Placeholder` expression nodes.

### 3.1 Named and positional placeholders

SQLGlot recognizes positional placeholders such as `?` and named placeholders such as `:tbl` in supported parsing contexts.

A template can contain both kinds:

```
from sqlglot import exp, parse_onetemplate = parse_one(    "SELECT * FROM :tbl WHERE ? = ?")query = exp.replace_placeholders(    template,    exp.to_identifier("customer_id"),    123,    tbl=exp.to_identifier("orders"),)print(query.sql())
```

The expected generated SQL is:

```
SELECT *
FROM orders
WHERE customer_id = 123
```

The important feature is that the substitutions have different semantic roles.

`exp.to_identifier("customer_id")` constructs an identifier, whereas the Python integer `123` is converted to a SQL literal. The named table placeholder similarly receives an identifier expression rather than a quoted string value.

The helper's implementation also recognizes contexts where substituting a query expression requires wrapping it in a subquery. It accounts for selected operand-parenthesization cases, so replacements can respect AST structure rather than requiring callers to manually assemble parentheses.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



### 3.2 Typed substitution as a composition mechanism

The substituted values can be more expressive than scalar constants. SQLGlot's conversion machinery accepts expression objects, allowing templates to incorporate:

- Identifiers representing tables or columns.
- SQL literals constructed from Python values.
- Predicates and arithmetic expression trees.
- Functions, casts, and other expression fragments.
- Complete queries in supported substitution positions.

This permits reusable SQL fragments to be represented as structured templates.

For example, a transformation can define a generic expression pattern and populate its operands with already analyzed or constructed SQLGlot expressions.

The ability to substitute expression objects is especially consequential for dialect implementations. A generator transformation can construct the appropriate target-dialect expression from a reusable SQL template without implementing every AST constructor manually.

SQLGlot's upstream contributor guidance explicitly describes combining `exp.maybe_parse()` and `exp.replace_placeholders()` for this purpose.

Contributor reference:

`https://github.com/tobymao/sqlglot/blob/main/AGENTS.md`

### 3.3 Boundaries and correctness considerations

AST substitution is not driver parameter binding.

`replace_placeholders()` substitutes values into a SQL expression before generation. The generated SQL may contain literal values directly. It does not establish server-side prepared-statement parameters or database-client binding.

This creates three distinct operations:

| Operation                | Responsibility                                                          |
| ------------------------ | ----------------------------------------------------------------------- |
| Template replacement     | Assemble a structured SQL expression                                    |
| SQL generation           | Render that expression according to a dialect                           |
| Driver parameter binding | Supply runtime values through the database client's parameter mechanism |

Identifiers generally cannot be substituted through ordinary scalar database-driver parameters, which makes AST construction useful for structural SQL composition. However, the fact that an identifier is represented structurally does not establish that the identifier names an authorized object.

Incomplete replacement is possible. The implementation leaves a placeholder in the tree when no matching named argument or available positional argument is supplied. Callers requiring complete substitution must verify that unresolved placeholders do not remain.

Dialect context matters. SQLGlot must be able to parse the template and generate its target syntax. Typed AST construction reduces string-manipulation errors but does not remove dialect-specific semantic constraints.

Source-position information may change. Replacing a placeholder changes the tree. The resulting expression is not guaranteed to preserve source locations in a way that can be mapped directly back to the template text.

Primary source: `https://sqlglot.com/sqlglot/expressions/builders.html`

## 4. SQL structural metadata extraction and lightweight dependency analysis

SQLGlot offers a useful layer of structural analysis between raw AST traversal and full schema-qualified lineage.

This layer can extract meaningful query facts without requiring the complete semantic-resolution process.

### 4.1 Projection, CTE, and table-reference accessors

The query expression interfaces expose:

| Mechanism                  | Extracted information                                         |
| -------------------------- | ------------------------------------------------------------- |
| `.selects`                 | Projected expression objects                                  |
| `.named_selects`           | Names of projected outputs                                    |
| `.ctes`                    | CTE definitions attached to a query                           |
| `.output_name`             | Output name of an individual projected expression             |
| `exp.find_tables()`        | Table references accounting for CTE sources                   |
| `exp.column_table_names()` | Explicit table qualifiers on columns                          |
| `traverse_scope()`         | Nested query-resolution contexts                              |
| `.type`                    | Expression result type, when annotated or otherwise available |
| `.meta` / `.meta_get()`    | Expression-associated metadata                                |

The distinction between `selects` and `named_selects` is particularly useful.

`selects` exposes the full SQL expressions, allowing further analysis of functions, dependencies, and computed values. `named_selects` extracts output names without requiring callers to manually inspect aliases and expression-specific naming conventions.

For example:

```
from sqlglot import exp, parse_onequery = parse_one("""    WITH aggregated AS (        SELECT customer_id, SUM(amount) AS total        FROM orders        GROUP BY customer_id    )    SELECT customer_id, total    FROM aggregated""")outputs = query.named_selectsctes = query.ctestables = exp.find_tables(query)
```

The top-level output names are `customer_id` and `total`. The CTE definitions are available as expressions, while scope-aware table discovery can distinguish the `aggregated` CTE reference from the underlying `orders` table reference.

These APIs also illustrate the importance of SQLGlot's behavioral traits: projection access is not limited to ordinary `Select` expressions. The `DDL` interface, for example, exposes projections when a statement contains a query, as in `CREATE TABLE AS SELECT`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+2



### 4.2 Structural extraction versus semantic resolution

There are at least three useful levels of SQL dependency understanding.

| Level                   | Native mechanisms                                               | What can be determined                                                   |
| ----------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Structural inventory    | `find_tables`, `named_selects`, `ctes`, expression traversal    | Referenced names, projections, CTE declarations, syntactic relationships |
| Scope and type analysis | `build_scope`, `traverse_scope`, qualification, type annotation | Resolution contexts, qualified references, inferred types                |
| Column lineage          | `sqlglot.lineage`                                               | Expression-level output-to-input dependency relationships                |

These are complementary levels of analysis, not interchangeable representations.

For example, `column_table_names()` collects the table qualifiers explicitly present on `Column` nodes. If a query references an unqualified column, the absence of a table prefix does not establish the absence of a source dependency.

Similarly, `find_tables()` excludes recognized CTE references but does not establish that a remaining name is a physical table rather than a database view, external table, or other named relation.

A further consideration is that projection names are not universally known from syntax alone. Wildcards, complex expressions without explicit aliases, table-valued functions, and transformations that modify output shape may require schema information or operator-specific logic.

Architectural significance: This intermediate extraction layer can support efficient SQL inventories, dependency discovery, and catalog metadata collection without invoking full qualification and lineage for every operation. More expensive analysis can be applied where the required conclusions depend on resolved SQL semantics.

Primary sources:

`https://sqlglot.com/sqlglot/expressions/query.html`

`https://sqlglot.com/sqlglot/expressions/builders.html`

`https://github.com/tobymao/sqlglot/blob/main/sqlglot/optimizer/scope.py`

## 5. Structured DDL, DML, privileges, transactions, and administrative SQL

The original overview established that SQLGlot can parse non-query SQL. The more consequential capability is that SQLGlot represents many non-query statements using dedicated AST classes with structured arguments.

This means SQLGlot can support analysis of database definitions, schema modifications, permissions, and operational commands—not only relational transformations.

### 5.1 Statement families and their representations

| Statement family     | Representative AST coverage                                                  | Structural information available                                             |
| -------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Schema creation      | `Create`, `Schema`, `ColumnDef`, `Properties`                                | Object kind, object name, definitions, columns, indexes, creation properties |
| Schema alteration    | `Alter`, `AlterColumn`, `RenameColumn`, `AlterRename`                        | Target object, alteration actions, renamed objects, changed definitions      |
| Object deletion      | `Drop`                                                                       | Object identity, kind, existence and other supported flags                   |
| Data mutation        | `Insert`, `Update`, `Delete`, `Merge`, `MultitableInserts`                   | Targets, sources, assignments, conditions, mutation clauses                  |
| Access control       | `Grant`, `Revoke`                                                            | Privileges, principals, securable object, grant and revoke options           |
| Constraints          | `ColumnConstraint`, `ForeignKey`, `Reference`, other specialized constraints | Key definitions, references, nullability, uniqueness, constraint options     |
| Database objects     | Sequence, trigger, index, function and view-related expressions              | Supported definitions, object properties, and dependencies                   |
| Session and metadata | `Set`, `Show`, `Describe`, `Pragma`                                          | Settings, arguments, metadata targets                                        |
| Administration       | `TruncateTable`, `Clone`, `Attach`, `Detach`, `Refresh`                      | Structured targets and supported operation-specific attributes               |
| Transactions         | `Transaction`, `Commit`, `Rollback`                                          | Transaction modes, rollback targets, selected control flags                  |
| Procedural SQL       | Declaration, assignment, conditional and loop-related expressions            | Supported control-flow structures and expressions                            |

Coverage varies substantially by dialect and statement form. These classes establish that SQLGlot has structured representations for the listed families; they do not imply complete support for every dialect-specific variant.

Primary references: `expressions/ddl.html`, `expressions/query.html`, `expressions/constraints.html`, and `parser.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+3



### 5.2 Database-object definitions as analyzable structures

An `exp.Create` expression distinguishes the object being created from its defining expression and its properties.

The implementation exposes arguments including:

```
{    "this": ...,    "kind": ...,    "expression": ...,    "properties": ...,    "exists": ...,    "replace": ...,    "indexes": ...,    "clone": ...,}
```

These are representative argument names from the supported AST model, not a requirement that every `Create` node contain every entry.

For a `CREATE TABLE AS SELECT` statement, SQLGlot can retain both the target object's definition and the source query. The `DDL` behavioral interface additionally exposes `selects`, `named_selects`, and `ctes` when the statement contains an appropriate query.

This is useful because a schema-creation statement can simultaneously describe a database object and establish data dependencies.

For a conventional `CREATE TABLE` declaration, the object definition can contain `ColumnDef` expressions and their associated data types and constraints.

A structural analysis can therefore distinguish:

- The table or view being defined.
- Its declared columns and types.
- Column and table constraints.
- Supported storage and object properties.
- A defining query, where applicable.
- Object references appearing within that query.

The same principle applies to `ALTER`: the target object and the requested alterations are represented separately through `Alter` and action expressions.

This supports database-object inventories, schema-definition extraction, and structural change analysis without a second parser dedicated to DDL.

### 5.3 Permission statements and authorization metadata

SQLGlot's permission model includes dedicated `Grant` and `Revoke` expressions.

The `Grant` representation has required arguments for privileges, the securable object, and principals, with optional attributes for object kind and grant options.

Conceptually, a statement such as:

```
GRANT SELECT, INSERT ON TABLE orders TO reporting_role;
```

can be represented through a node that distinguishes the privileges from the object and recipient.

This is a meaningful alternative to recognizing grants through regular expressions. The caller can inspect the represented privileges, securable targets, and principals independently.

`Revoke` shares the principal argument structure and additionally supports a `cascade` attribute.

However, parsing a permission statement is not equivalent to calculating effective access rights.

Effective authorization can depend on role inheritance, ownership, object hierarchy, default privileges, row-level security, session identity, policies, and database-specific access-control rules.

SQLGlot supplies structured statements that can contribute to such analysis, not a comprehensive authorization evaluator.

Source: `https://sqlglot.com/sqlglot/expressions/query.html`

### 5.4 Structured constraints and schema relationships

SQLGlot's constraints module provides a richer model than simply attaching constraint text to a column.

For example, the `ForeignKey` expression can represent referenced columns and foreign-key actions through separate arguments such as `expressions`, `reference`, `delete`, `update`, and `options`.

This is relevant to extracting declared relational relationships from schema definitions.

A foreign-key declaration can establish a declared relationship between database objects, although SQLGlot cannot independently establish whether the database enforces that relationship, whether existing data satisfies it, or whether the declared relationship is still present in the live schema.

The constraint representation can also support comparison of definitions across dialects. That is more sophisticated than comparing raw column-declaration strings, particularly where engines express constraints differently.

Source: `https://sqlglot.com/sqlglot/expressions/constraints.html`

### 5.5 Transaction and procedural constructs

SQLGlot includes structured representations for selected transactional statements.

For example, `Transaction` represents transaction-related modes, `Commit` includes control options, and `Rollback` can carry a savepoint reference.

Certain procedural constructs also have dedicated representations, including declarations and supported control-flow statements.

These facilities can help classify and inspect SQL scripts that mix query definitions with control operations.

However, parsing a procedural block does not make SQLGlot a complete stored-procedure compiler. Variable lifetimes, exception handling, branching behavior, procedural execution, and transaction-state transitions remain dependent on the supported grammar and database engine.

### 5.6 Opaque-command fallback: the important completeness boundary

SQLGlot's parser can represent certain unsupported or only partially understood statements as `exp.Command`.

Its `Command` expression has a relatively small argument structure:

```
class Command(Expression):    arg_types = {        "this": True,        "expression": False,    }
```

The parser's `_parse_command()` implementation emits an unsupported-syntax warning and constructs a command expression containing the command identifier and remaining command text.

This means a statement can be accepted without becoming a fully structured semantic tree.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



The distinction matters particularly for administrative and procedural SQL.

A command retained in a generic representation may still be useful for preservation, classification, or later handling. But a structural inspector cannot assume that nested objects, privileges, predicates, or declarations are individually represented.

Accordingly, statement recognition, structural completeness, and semantic validity are three separate properties.

For database-definition analysis, the presence of `exp.Command` is therefore an important signal that a statement may require additional inspection or a more specialized parser.

Primary sources:

`https://sqlglot.com/sqlglot/expressions/ddl.html`

`https://sqlglot.com/sqlglot/expressions/query.html`

`https://sqlglot.com/sqlglot/expressions/constraints.html`

`https://sqlglot.com/sqlglot/parser.html`

## 6. Rich data-type representations and nested-data semantics

SQLGlot's type functionality has two related but distinct roles:

1. Representing SQL type declarations as structured AST objects.
2. Inferring the result types of expressions using schemas, expression semantics, and dialect rules.

The first role deserves independent attention because type declarations themselves contain meaningful structure, even when no query is being analyzed.

### 6.1 `exp.DType` and `exp.DataType`

SQLGlot separates type identity from the complete type declaration.

`exp.DType` is an enumeration of recognized type kinds.

`exp.DataType` is a structured expression capable of representing a type kind together with parameters and other attributes.

Its supported argument structure includes:

```
{    "this": ...,    "expressions": ...,    "nested": ...,    "values": ...,    "kind": ...,    "nullable": ...,    "collate": ...,}
```

`this` identifies the type kind, while the other fields provide locations for type-specific details. These are not universally populated, and the interpretation of individual fields depends on the particular type and dialect.

For example, `DECIMAL(18, 2)` consists of a numeric type with precision and scale parameters. `ARRAY<INT>` additionally describes the element type.

A structured type representation makes these distinctions available without requiring repeated parsing of type-declaration strings.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



### 6.2 Breadth of recognized type families

SQLGlot's `DType` enum encompasses numerous conventional, specialized, and vendor-specific types.

| Family                        | Representative types                                                     |
| ----------------------------- | ------------------------------------------------------------------------ |
| Scalar numeric                | `INT`, `BIGINT`, `DECIMAL`, `DOUBLE`, `BIGDECIMAL`, `BIGNUM`             |
| Extended and unsigned numeric | `INT128`, `INT256`, `UINT`, `UBIGINT`, related unsigned types            |
| Text and binary               | `VARCHAR`, `TEXT`, `NVARCHAR`, `BINARY`, `VARBINARY`, `BLOB`             |
| Temporal                      | `DATE`, `TIME`, `TIMESTAMP`, `TIMESTAMPTZ`, `TIMESTAMPNTZ`, `DATETIME64` |
| Collections                   | `ARRAY`, `LIST`, `MAP`                                                   |
| Structured types              | `STRUCT`, `NESTED`, `OBJECT`, `UNION`                                    |
| Semi-structured data          | `JSON`, `JSONB`, `VARIANT`, `SUPER`                                      |
| Geographic and geometric      | `GEOGRAPHY`, `GEOMETRY`, `POINT`, `LINESTRING`, `POLYGON`                |
| Network types                 | `INET`, `IPADDRESS`, `IPPREFIX`, `IPV4`, `IPV6`                          |
| Ranges                        | `RANGE`, `NUMRANGE`, `INT4RANGE`, `INT8RANGE` and multirange variants    |
| Specialized analytical types  | `VECTOR`, `HLLSKETCH`, `TDIGEST`                                         |
| User-defined types            | `USERDEFINED`                                                            |

The presence of a type in the enumeration establishes that SQLGlot can represent that type category. It does not establish that every dialect can generate it faithfully, that equivalent types exist on other engines, or that all operations involving it are supported by type inference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+5



### 6.3 Programmatic construction and inspection

The principal APIs include:

| API                    | Function                                                                         |
| ---------------------- | -------------------------------------------------------------------------------- |
| `DataType.build()`     | Construct a type expression from a type kind, string, or existing representation |
| `DataType.from_str()`  | Parse a type declaration from SQL text                                           |
| `DataType.is_type()`   | Check type identity against one or more supplied types                           |
| `Expression.type`      | Access an expression's assigned or inferred result type                          |
| `Expression.is_type()` | Test an expression's assigned type                                               |

For example:

```
from sqlglot import expdecimal_type = exp.DataType.build("DECIMAL(18, 2)")array_type = exp.DataType.build("ARRAY<INT>")is_decimal = decimal_type.is_type(exp.DType.DECIMAL)
```

`DataType.build()` accepts a dialect for interpreting string declarations. It also supports `udt=True` to permit a user-defined type representation when an input cannot otherwise be parsed as a recognized built-in type.

This provides a way to retain nonstandard types without requiring every proprietary database type to be introduced into SQLGlot's core enumeration.

### 6.4 Type-family classifications

SQLGlot defines reusable type-family sets, including:

- `STRUCT_TYPES` — recognized struct-like representations.
- `ARRAY_TYPES` — array and list representations.
- `NESTED_TYPES` — struct-like and collection types that SQLGlot groups as nested.
- `SIGNED_INTEGER_TYPES`, `UNSIGNED_INTEGER_TYPES`, and `INTEGER_TYPES`.
- `NUMERIC_TYPES`, `FLOAT_TYPES`, and `REAL_TYPES`.
- `TEXT_TYPES`, `BINARY_TYPES`, and `TEMPORAL_TYPES`.

These categories allow type-family reasoning without enumerating every concrete `DType` member.

Importantly, the categories reflect SQLGlot's implementation distinctions rather than a universal SQL type ontology. For example, `JSON` is a semi-structured type, but it should not automatically be assumed to belong to the same internal type category as `STRUCT` or `ARRAY`.

This matters when a transformation depends on particular structural properties, such as directly addressable fields, element typing, or supported casts.

Source: `https://sqlglot.com/sqlglot/expressions/datatypes.html`

### 6.5 Structured columns and dotted-name interpretation

One of the harder problems in SQL static analysis is interpreting dotted references.

Consider:

```
SELECT record.address.city
FROM events;
```

Depending on the dialect, schema, and context, dotted syntax can represent:

- Qualification across namespaces and relations.
- A column belonging to an explicitly named source.
- Access to a field within a structured value.
- A sequence of nested field accesses.
- A combination of relation qualification and nested field access.

These cases cannot be reliably distinguished through the number of dotted components alone.

SQLGlot's schema-aware qualification and type machinery helps resolve these distinctions. It recognizes dialect-specific conventions around structured access, star expansion, pseudocolumns, and circumstances where identifiers normally associated with tables may also be interpreted as column references.

For nested types, the type of the containing expression can be significant. A field access on a known struct has a different interpretation from a similarly written reference involving catalog and table qualifiers.

This offers a valuable interaction between `DataType`, schema resolution, and AST inspection: a system can preserve both the syntactic expression and the inferred or declared type context needed to interpret it.

### 6.6 Boundaries of SQL type interoperability

A shared type representation does not guarantee cross-dialect type equivalence.

Important differences include precision limits, signedness, overflow behavior, nullability, collation, character encodings, timestamp timezone semantics, decimal coercion, and nested-type field naming.

For example, two engines may both support a type rendered as `TIMESTAMP` while using different timezone interpretation rules. Likewise, a structured type's field names or nullability constraints may not survive translation unchanged.

SQLGlot can represent and transform many such types, but a complete database-schema compatibility check still requires target-engine semantics.

Primary source: `https://sqlglot.com/sqlglot/expressions/datatypes.html`

## 7. Operator-aware output-schema reasoning for PIVOT and UNPIVOT

Ordinary projection analysis assumes that output columns are explicitly represented by selected expressions. `PIVOT` and `UNPIVOT` complicate this model because the operator itself can remove, add, and rename columns.

SQLGlot includes dedicated machinery for interpreting those changes.

### 7.1 `exp.Pivot.output_columns()`

The relevant method is:

```
Pivot.output_columns(pre_pivot_columns)
```

It accepts the names of columns visible before the pivot operation and returns an insertion-ordered dictionary mapping:

Post-transformation output name → pre-rename source-side name

The result reflects the output-column ordering and naming conventions supported by the `Pivot` expression implementation.

For example, the upstream documentation demonstrates:

```
from sqlglot import exp, parse_onequery = parse_one(    "SELECT * FROM t "    "UNPIVOT(val FOR name IN (a, b))")pivot = query.find(exp.Pivot)columns = pivot.output_columns(["a", "b", "c"])print(list(columns))
```

The resulting output names are:

```
["c", "name", "val"]
```

The original columns `a` and `b` participate in the unpivot operation and no longer appear independently. The unaffected column `c` remains, while `name` and `val` are generated by the transformation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



### 7.2 Distinct PIVOT and UNPIVOT behavior

For `UNPIVOT`, SQLGlot identifies columns consumed by the operation, retains unaffected columns, and introduces name and value columns.

For `PIVOT`, it analyzes aggregate expressions, pivot fields, and explicitly supplied or inferred output column names.

The implementation also considers:

- Multi-value unpivot expressions.
- Aliased pivot and unpivot fields.
- Explicit pivot output-column definitions.
- Positional renaming through pivot aliases.
- Dialect-dependent output ordering.
- Dialect-specific controls such as `value_columns_first`.

The latter matters because the implementation explicitly accounts for T-SQL's ordering of unpivot value and name columns.

### 7.3 Output names are not complete expression lineage

`output_columns()` establishes an output-name mapping. It should not be interpreted as a complete explanation of each output value's dependency.

For example, a generated unpivot value column can depend on multiple original input columns, with the contributing value varying by output row.

Similarly, a pivot aggregate depends on both the aggregated measure and the grouping and pivot conditions.

A dictionary mapping output names to pre-rename names cannot express all these relationships.

The distinction is between:

1. Output-schema derivation: Which columns exist after the operator?
2. Value dependency analysis: Which input values and expressions contribute to each output?
3. Type derivation: What are the resulting columns' data types?

SQLGlot's dedicated pivot helper addresses the first problem and contributes information useful to the others.

This is an important example of why advanced SQL analysis sometimes requires specialized relational-operator semantics rather than generic traversal of `Column` expressions.

Primary source: `https://sqlglot.com/sqlglot/expressions/query.html`

## 8. Expression DSL, predicate composition, and structural identity

SQLGlot's expression API provides a compositional DSL through Python operators and expression-building methods.

This is a separate capability from parsing SQL strings or constructing nodes through their low-level constructors.

### 8.1 Operator overloading

SQLGlot implements Python operator overloads that construct corresponding SQL AST nodes.

| Python operation  | Constructed SQL expression  |
| ----------------- | --------------------------- |
| `a + b`           | Addition                    |
| `a - b`           | Subtraction                 |
| `a * b`           | Multiplication              |
| `a / b`           | Division                    |
| `a // b`          | Integer-division expression |
| `a % b`           | Modulo                      |
| `a ** b`          | Exponentiation              |
| `a < b`, `a <= b` | Comparison predicates       |
| `a > b`, `a >= b` | Comparison predicates       |
| `a & b`           | Logical `AND`               |
| `a \\| b`         | Logical `OR`                |
| `~a`              | Logical `NOT`               |

These operators return SQLGlot expression objects, rather than evaluating the corresponding SQL operations in Python.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



A complementary method API provides more explicit SQL operations:

`eq()`, `neq()`, `isin()`, `between()`, `like()`, `ilike()`, `rlike()`, `and_()`, `or_()`, `not_()`, `asc()`, and `desc()`.

These methods cover operations that cannot be expressed naturally through Python operator overloading or for which SQL-specific semantics deserve an explicit constructor.

### 8.2 Predicate construction

For example:

```
from sqlglot import expamount = exp.column("amount")status = exp.column("status")predicate = (    amount.between(10, 100)    .and_(status.eq("active")))print(predicate.sql())
```

The resulting predicate is structurally equivalent to:

```
amount BETWEEN 10 AND 100
AND status = 'active'
```

This allows predicates to be assembled from reusable expression objects and passed to builders, transformations, or generator implementations.

The principal advantage is that the resulting expression has explicit node types and child relationships. Later analysis can distinguish `Between`, `EQ`, and `And` operations without reparsing an assembled string.

### 8.3 Python equality is not SQL equality

A particularly consequential distinction concerns `==`.

SQLGlot uses Python equality to compare expression objects structurally. The `Expression.__eq__()` implementation compares the concrete expression type and structural hashes.

Therefore:

```
a == b
```

checks expression equality in Python.

It does not construct the SQL predicate:

```
a = b
```

To construct that predicate, use:

```
a.eq(b)
```

The corresponding inequality builder is `a.neq(b)`.

This distinction matters for both correctness and API ergonomics. A programming agent constructing SQL through operators must not treat every Python comparison operator as an AST-construction operation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



Python's `and` and `or` keywords are likewise not equivalent to SQLGlot's `and_()` and `or_()` methods. For operator-style composition, use `&` and `|`, accounting for Python's precedence rules.

### 8.4 Structural hashing and mutation

SQLGlot expressions implement structural hashing to support comparisons and hash-based collections.

The implementation computes hashes from expression classes and their arguments, caching the result in `_hash`. Supported tree-mutation methods invalidate affected cached hashes.

This can support uses such as:

- Deduplicating structurally equivalent expression objects.
- Comparing AST fragments during transformation.
- Indexing expressions in sets or dictionaries.
- Detecting selected forms of structural repetition.

These hashes are not semantic query fingerprints.

For example, two algebraically equivalent predicates can have different AST structures and therefore different hashes. Conversely, structural equality is not a proof that a query is valid under a particular dialect or schema.

Hash stability also should not be assumed across processes or library versions. Python hashing behavior, SQLGlot's internal representation, and normalization conventions may all affect identity.

Mutable expression objects present an additional consideration: modifying an expression already used as a hash-based dictionary key or set element can violate the assumptions of those collections. Immutable copies or externally derived stable keys are more appropriate where persistent identity is required.

Primary source: `https://sqlglot.com/sqlglot/expressions/core.html`

## 9. Machine-readable SQL comments and parser directives

SQLGlot comments are more than incidental formatting information. Certain comment markers influence AST metadata and, in specific cases, parsing or transformation behavior.

This offers a lightweight mechanism for carrying limited processing directives alongside SQL expressions.

### 9.1 The `sqlglot.meta` convention

`Expression.add_comments()` recognizes the marker:

```
sqlglot.meta
```

When encountered, it parses subsequent comma-separated key-value attributes and records them in the expression's `.meta` dictionary.

For example:

```
from sqlglot import exp, parse_onequery = parse_one("SELECT * FROM orders")table = query.find(exp.Table)table.add_comments(["sqlglot.meta replace=false"])assert table.meta_get("replace") is False
```

The underlying implementation separates the comment at the marker, parses attributes, and converts recognized Boolean-like values.

The resulting metadata is available through:

```
expression.metaexpression.meta_get("attribute")
```

`meta_get()` is a small but useful implementation detail: it reads the metadata without allocating an empty dictionary when the expression has no metadata.

SQLGlot's own `replace_tables()` function demonstrates a practical use of this mechanism:

```
if isinstance(node, Table) and node.meta_get("replace") is not False:    ...
```

This allows an expression to carry a directive preventing a particular transformation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



### 9.2 Comments as transformation controls

This mechanism opens the possibility of embedding lightweight directives in SQL source.

For example, a parser could attach metadata identifying certain references as excluded from substitution, or a transformation could inspect custom expression metadata before performing a rewrite.

Such behavior is particularly useful when a transformation should operate on most matching expressions but leave selected instances unchanged.

However, there are important distinctions:

- `sqlglot.meta` is a recognized SQLGlot convention, not a general SQL standard.
- Metadata values are not a schema-validated configuration language.
- The attachment of comments to particular expressions depends on parsing context.
- Existing SQLGlot transformations do not automatically interpret arbitrary custom metadata keys.
- SQL regeneration and subsequent transformations may affect comment placement or preservation.

Therefore, the mechanism is best understood as a limited AST annotation and transformation-control facility, not a complete source-level metadata framework.

### 9.3 Forcing anonymous function representation

SQLGlot supports a separate comment marker:

```
/* sqlglot.anonymous */
```

The parser ordinarily recognizes known SQL functions and constructs specialized function-expression classes.

For example, a recognized function name may be converted into a canonical SQLGlot function expression with standardized arguments or behavior.

The anonymous marker provides an escape hatch.

When the marker is encountered in the parser's supported position following a function call, SQLGlot can instead construct an `exp.Anonymous` expression, even if the function name normally maps to a recognized built-in function.

This is useful when:

- A user-defined function has the same name as a recognized built-in.
- A function should remain opaque instead of undergoing built-in normalization.
- An application needs to preserve a function's original identity for specialized downstream handling.
- A dialect-specific function should not inherit the assumptions associated with a similarly named standard function.

The marker does not define the function's return type, implementation, or runtime semantics. It changes how the parser represents the call.

Its placement is significant: the upstream parser specifically checks comments associated with the position following the parsed function arguments. This is not a globally applicable directive that can be placed anywhere in a SQL statement.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



Primary sources:

`https://sqlglot.com/sqlglot/expressions/core.html`

`https://sqlglot.com/sqlglot/parser.html`

## 10. AST diagnostics, source-position metadata, and transformation composition

SQLGlot exposes several smaller expression-level facilities that support AST construction, validation, debugging, and instrumentation.

Their significance lies in enabling controlled manipulation of expression trees without requiring every consumer to implement its own navigation, checking, and transformation infrastructure.

### 10.1 AST source-position metadata

`Expr.update_positions()` associates source positions with an expression.

Its supported inputs include:

```
expression.update_positions(    other=None,    line=None,    col=None,    start=None,    end=None,)
```

The `other` argument can be a token or another expression.

When given a token, SQLGlot can copy:

- `line` — source line.
- `col` — source column.
- `start` — starting character position.
- `end` — ending character position.

When given another expression, it transfers the available position metadata. Positions can also be supplied explicitly.

These attributes are stored in the expression's metadata rather than constituting a separately maintained, universal source-map representation.

This is relevant to constructing expressions that retain useful source-origin information and to attaching location data to derived diagnostics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



Important limitation: SQLGlot does not guarantee comprehensive source-position preservation through arbitrary AST transformations.

A replacement expression may inherit selected positions, but the resulting tree can contain generated nodes with no direct correspondence to a contiguous span of original SQL.

Consequently, source positions should be interpreted as available diagnostic metadata, not proof of a lossless transformation history.

### 10.2 Expression argument validation

`Expr.error_messages()` performs localized checks against an expression's declared argument structure.

Its implementation checks required arguments and can report excessive function arguments when an argument sequence is supplied for a non-variadic function.

For example, a function expression may declare particular required arguments through `arg_types`. If those arguments are absent, `error_messages()` can return descriptive messages.

The implementation also performs additional unexpected-key checks in its test-mode path.

This is useful for catching certain errors in programmatically constructed ASTs before they reach later transformation or generation stages.

However, it is not a comprehensive SQL validator. It does not establish:

- Whether referenced tables and columns exist.
- Whether a function is supported by a database.
- Whether the expression's inferred types are acceptable.
- Whether every SQL semantic constraint is satisfied.
- Whether the expression is legal in its particular syntactic context.

Its scope is substantially narrower: validation of selected structural requirements encoded in the expression class.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



### 10.3 `assert_is()` for typed expression handling

`Expr.assert_is()` asserts that an expression is an instance of a specified class and returns the expression.

For example:

```
query = parse_one("SELECT a FROM t")select = query.assert_is(exp.Select)
```

This can be useful in builder chains or transformations where the caller expects a specific expression type and wants an immediate failure if that assumption is incorrect.

It is a runtime class assertion, not an SQL type annotation or semantic validation step.

### 10.4 `pipe()` and `apply()` for transformation chaining

SQLGlot exposes two related composition methods.

| Method                  | Behavior                                                                | Typical role                         |
| ----------------------- | ----------------------------------------------------------------------- | ------------------------------------ |
| `Expr.pipe(func, ...)`  | Passes the expression to a callable and returns the callable's result   | Transformation composition           |
| `Expr.apply(func, ...)` | Invokes a callable for side effects and returns the original expression | Inspection, logging, instrumentation |

A transformation can therefore be expressed as a chain:

```
result = (    expression    .pipe(first_transform)    .apply(inspect_intermediate)    .pipe(second_transform))
```

Here, `first_transform` and `second_transform` are caller-provided functions, while `inspect_intermediate` is a callback that observes or otherwise processes the intermediate expression.

This is a concise way to assemble modular AST processing stages.

`pipe()` is not constrained to returning an `Expr`; its return value is the callable's return value. That provides flexibility, but a chain expecting an expression must ensure its transformations return the appropriate type.

`apply()` retains the original instance, making it useful when a callback should not alter the value being passed through the chain. The callback itself can nevertheless have side effects.

A distinction worth emphasizing is that `Expr.pipe()` is a Python expression-composition utility, not SQL's `|>` pipe syntax. The latter is a parser feature discussed separately below.

Primary source:

`https://sqlglot.com/sqlglot/expressions/core.html`

## 11. Specialized generator transformations

SQLGlot's generator transformations address cases where source and target SQL dialects represent the same broad operation through substantially different SQL structures.

The original overview covered major relational transformations such as `QUALIFY` elimination and join rewrites. Additional transformations reveal greater depth in several specialized areas.

These transformations are particularly relevant because dialect adaptation sometimes requires changing the structure of an entire query or DDL statement rather than simply mapping a function name or type.

### 11.1 Collection expansion and sequence generation

`unnest_generate_date_array_using_recursive_cte()`

This transformation provides a recursive-CTE-based formulation for certain date-array generation and unnesting operations.

Its purpose is to express a sequence-expansion operation using relational constructs available to a target dialect.

The broader significance is that SQLGlot can translate certain specialized table-valued or collection-generating operations into alternative relational formulations.

The resulting query may be more complex than the source, and execution performance will depend on the database's recursive-query implementation.

`explode_projection_to_unnest()`

This transformation converts supported `EXPLODE` and `POSEXPLODE` projection expressions into `UNNEST`-based formulations.

It accepts controls including `index_offset` and `unnest_map`.

These parameters matter because collection expansion can differ across engines in the way it produces positional indexes, handles map entries, and structures output columns.

The transformation therefore does more than replace `EXPLODE` with the word `UNNEST`: it can reorganize projections and relational sources to represent the required expansion.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



### 11.2 Aggregate syntax and percentile translation

Two complementary transformations address percentile-expression conventions:

- `add_within_group_for_percentiles()`
- `remove_within_group_for_percentiles()`

Some database systems express percentile calculations using ordered-set aggregate syntax involving `WITHIN GROUP`.

Others support related calculations through different function forms.

SQLGlot can transform supported percentile expressions between these representations.

This requires understanding both the percentile operation and its ordering expression. The ordering input cannot always be moved through a simple function-name substitution.

A further distinction is that percentile functions can differ in exact versus approximate evaluation, continuous versus discrete interpolation, and null treatment.

The existence of a syntax transformation does not establish numerical equivalence across all percentile implementations.

### 11.3 Recursive CTE compatibility

`add_recursive_cte_column_names()` supplies explicit column names for supported recursive CTE definitions using the output names of the query projections.

This addresses dialects that require or benefit from an explicit recursive CTE column list.

For example, recursive SQL may be written in one dialect without explicitly declaring all output names, while the target dialect requires a declaration of the form:

```
WITH RECURSIVE hierarchy(id, parent_id) AS (...)
```

The transformation uses the available projection structure to construct the corresponding column declarations.

This illustrates an important interaction between query metadata and SQL generation: output-name analysis becomes an input to a compatibility rewrite.

Where output names are unresolved or ambiguous, the quality of this transformation necessarily depends on the available expression structure.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



### 11.4 Boolean and temporal compatibility

`ensure_bools()`

This transformation converts supported numeric expressions appearing in Boolean contexts into explicit comparisons.

For example, a source dialect may permit an integer expression directly in a predicate position, while the target requires an explicitly Boolean expression.

SQLGlot can rewrite eligible expressions into an equivalent comparison against zero under the intended dialect convention.

This is sensitive to type and truthiness semantics. The transformation does not imply that every database interprets arbitrary numeric and nonnumeric values as Boolean conditions in the same way.

`epoch_cast_to_ts()`

Despite its broad-sounding name, this helper performs a narrower transformation: it recognizes supported casts of the special string `epoch` to temporal types and replaces that representation with an equivalent temporal literal.

It should not be interpreted as a general epoch-number conversion library.

The distinction matters because converting an integer number of Unix seconds or milliseconds to a timestamp requires different semantics from interpreting a database's special epoch literal.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



### 11.5 Identifier and pivot qualification

`unqualify_columns()` removes qualification components from column references.

This is useful for generating syntax where qualified columns are not accepted, but it is not generally semantics-preserving when applied arbitrarily to a query containing ambiguous column names.

`unqualify_pivot_fields()` is more specialized.

Certain dialects require unqualified column names in `PIVOT` or `UNPIVOT` field declarations even when qualified expressions are valid elsewhere in the same statement.

The transformation removes qualification in those targeted positions while allowing the surrounding aggregate expression to retain qualification where appropriate.

This is a good example of why dialect generation needs context-sensitive AST transformations rather than blanket identifier normalization.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



### 11.6 DDL schema and storage-property transformations

SQLGlot includes transformations specifically for adapting table-creation syntax.

`move_schema_columns_to_partitioned_by()`

Certain Hive-style table declarations treat partition columns as a separate portion of the schema.

This transformation identifies partition columns, relocates their definitions into an appropriate `PARTITIONED BY` representation, and removes the corresponding columns from the ordinary schema declaration.

`move_partitioned_by_to_schema_columns()`

The complementary transformation adapts partition declarations to the schema representation expected by supported target conventions, including relevant Spark table-creation formats.

These mechanisms are significant because database portability extends to physical and logical schema declarations.

However, translating partition-column syntax does not imply that two engines will implement equivalent partition storage, pruning, metadata management, or performance behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



### 11.7 Temporary table creation and temporary-view substitution

`ctas_with_tmp_tables_to_create_tmp_view()` handles a specialized table-creation compatibility case.

For supported temporary `CREATE TABLE AS SELECT` expressions, the transformation can produce a temporary-view declaration instead.

It also accepts a `tmp_storage_provider` callback for other temporary-storage handling.

This is an especially important example of a syntactically useful transformation whose underlying semantics may differ.

Temporary tables and temporary views can have different persistence, materialization, indexing, mutability, session scope, and transaction behavior.

The transformation provides a target-compatible SQL formulation for the supported use case; it does not make these database objects universally interchangeable.

### 11.8 Struct construction and nested-field naming

Two transformations address structured-value representation.

`struct_kv_to_alias()` converts supported key-value struct arguments into aliased expressions.

For example, a structured field assignment can be represented using a form equivalent to:

```
STRUCT(1 AS y)
```

`inherit_struct_field_names()` addresses a BigQuery-specific convention in which later structs within an array can implicitly inherit field names from the first struct.

Conceptually:

```
ARRAY[
    STRUCT('Alice' AS name, 85 AS score),
    STRUCT('Bob', 92)
]
```

The transformation can make inherited field names explicit in subsequent structs, enabling translation into dialects that lack the same implicit naming behavior.

This illustrates a form of cross-dialect compatibility involving the schema of constructed values rather than ordinary relational tables.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com+1



### 11.9 Legacy Oracle outer-join syntax

`eliminate_join_marks()` handles supported forms of Oracle's legacy `(+)` outer-join syntax.

This syntax represents outer joins through annotations attached to column comparisons rather than ordinary `JOIN ... ON` clauses.

For example:

```
SELECT *
FROM employees e, departments d
WHERE e.department_id = d.department_id(+)
```

Translating this to a conventional outer join requires more than removing the `(+)` marker. The generator transformation must infer the affected relations, join direction, and participating predicates.

The implementation explicitly addresses constraints and irregularities of Oracle's legacy syntax.

This is a notable example of structural SQL translation where a predicate-oriented representation must be reconstructed as a relational join operation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



### 11.10 Architectural role of these transformations

These additional transformations reveal several distinct classes of SQL portability:

| Portability class                 | Representative transformations                                                     |
| --------------------------------- | ---------------------------------------------------------------------------------- |
| Relational operator reformulation | `explode_projection_to_unnest`, `eliminate_join_marks`                             |
| Recursive-query compatibility     | `unnest_generate_date_array_using_recursive_cte`, `add_recursive_cte_column_names` |
| Aggregate syntax adaptation       | `add_within_group_for_percentiles`, `remove_within_group_for_percentiles`          |
| Expression-type compatibility     | `ensure_bools`, `epoch_cast_to_ts`                                                 |
| Identifier compatibility          | `unqualify_columns`, `unqualify_pivot_fields`                                      |
| DDL structure translation         | Partition-column movement, temporary-table adaptation                              |
| Nested-value construction         | `struct_kv_to_alias`, `inherit_struct_field_names`                                 |

These transformations are exposed through `sqlglot.transforms` and can be composed into generator preprocessing where applicable.

Many are specialized for particular AST shapes, and several mutate their input expressions. They should therefore not be regarded as universally applicable normalization functions.

The architectural opportunity is to reuse these native transformations as well-defined components of dialect adaptation, rather than recreating corresponding SQL rewrites in application-specific code.

Primary source: `https://sqlglot.com/sqlglot/transforms.html`

## 12. Pipe-style SQL query syntax

SQLGlot's parser supports a family of pipe-style relational transformations using the `|>` operator.

This differs from conventional SQL, where relational operations are commonly expressed through nested query clauses or subqueries.

### 12.1 Pipe-style relational composition

Pipe-style SQL expresses a sequence of transformations:

```
FROM orders
|> WHERE amount > 100
|> SELECT customer_id, amount
|> ORDER BY amount DESC
|> LIMIT 10
```

This is a conceptual example of the supported syntax family, not a claim that every dialect accepts this particular statement.

Each stage transforms the relation produced by the preceding stage.

The representation can be useful for parsing SQL dialects that expose relational operations through an explicit pipeline syntax.

### 12.2 Supported transformation stages

SQLGlot's parser maintains the `PIPE_SYNTAX_TRANSFORM_PARSERS` registry.

For the audited source, registered stages include:

| Stage         | Intended operation                      |
| ------------- | --------------------------------------- |
| `AGGREGATE`   | Aggregation and grouping transformation |
| `AS`          | Naming or aliasing a pipeline relation  |
| `DISTINCT`    | Duplicate elimination                   |
| `EXTEND`      | Adding projected expressions            |
| `LIMIT`       | Limiting output rows                    |
| `ORDER BY`    | Sorting                                 |
| `PIVOT`       | Pivot transformation                    |
| `SELECT`      | Projection                              |
| `TABLESAMPLE` | Sampling                                |
| `UNPIVOT`     | Unpivot transformation                  |
| `WHERE`       | Filtering                               |

The parser dispatches recognized stages to specialized parsing functions that construct or modify relational expressions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



### 12.3 Normalization into relational expressions

The important capability is not merely recognizing the `|>` token.

SQLGlot can interpret the supported pipe stages and construct corresponding query-expression structures.

This means downstream analysis can work with the relational operations represented by those expressions rather than necessarily requiring a separate analysis framework for pipeline syntax.

For example, a pipeline stage implementing filtering can ultimately contribute a predicate to a relational query representation.

More complex stages may require constructing additional query boundaries or derived tables to preserve sequential semantics.

The exact AST structure depends on the stage and parsing rules.

### 12.4 Compatibility boundaries

Pipe-style SQL is not a single universally implemented grammar.

Database systems can differ in their supported stages, naming conventions, clause ordering, alias visibility, and evaluation semantics.

SQLGlot's parser registry defines a supported subset and interpretation. It does not establish complete compatibility with every vendor's pipeline-query language.

In particular, sequential stages can have visibility rules that differ from a conventional `SELECT`, including whether expressions introduced in one stage are available to the next.

These differences require careful handling when generating SQL for another dialect.

Primary source: `https://sqlglot.com/sqlglot/parser.html`

## 13. Date/time format translation and subsecond precision utilities

SQLGlot exposes lower-level temporal utilities that complement its AST-based temporal expression transformations.

These are useful when translating embedded date/time format strings between dialect conventions.

### 13.1 `sqlglot.time.format_time()`

The function has the signature:

```
format_time(    string,    mapping,    trie=None,)
```

It converts a format string using a supplied token mapping.

The official documentation demonstrates:

```
from sqlglot.time import format_timeformat_time("%Y", {"%Y": "YYYY"})
```

This returns:

```
YYYY
```

Unlike applying a sequence of naive string replacements, SQLGlot uses trie-based token recognition.

This matters because temporal formatting languages contain overlapping token sequences. The intended interpretation of a token can depend on identifying the longest or otherwise appropriate recognized format component.

The optional trie permits reuse of a prepared token structure rather than reconstructing it for every conversion.

The function preserves unrecognized text through its mapping process, but that should not be interpreted as validating the resulting format string against a database's full temporal-format grammar.

An empty input returns `None`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



### 13.2 `subsecond_precision()`

The companion function:

```
subsecond_precision(timestamp_literal)
```

examines an ISO-8601 timestamp literal and determines an appropriate subsecond precision category.

In the audited implementation, the result is one of:

- `0` — no recognized fractional-second precision.
- `3` — millisecond precision.
- `6` — microsecond precision.

The function uses Python datetime parsing and therefore follows relevant constraints of Python's temporal representation.

It should not be interpreted as a general mechanism for preserving arbitrary nanosecond precision or all vendor-specific timestamp formats.

Its purpose is narrower: deriving a useful temporal type precision from supported timestamp literals.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



These utilities can be reused independently where applications need temporal-format translation or timestamp-literal inspection without invoking a complete SQL transpilation operation.

Primary source: `https://sqlglot.com/sqlglot/time.html`

## 14. SQLFrame: the former SQLGlot DataFrame API

An ecosystem distinction is important for interpreting historical SQLGlot documentation.

SQLGlot previously included a PySpark-like DataFrame API under `sqlglot.dataframe`.

That API was extracted into the separate SQLFrame project in SQLGlot v24. SQLGlot's own historical package documentation explicitly identifies this transition.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



SQLFrame now provides a distinct DataFrame-oriented abstraction. It aims to let code written using familiar PySpark DataFrame operations generate and execute corresponding queries on supported database backends.

The responsibilities are therefore different:

| Capability                                          | SQLGlot                                        | SQLFrame                                |
| --------------------------------------------------- | ---------------------------------------------- | --------------------------------------- |
| Parse and represent SQL                             | Core responsibility                            | May rely on SQLGlot                     |
| AST transformation and dialect generation           | Core responsibility                            | Underlying infrastructure               |
| PySpark-like DataFrame programming interface        | Not included in current SQLGlot distribution   | Primary capability                      |
| Execute DataFrame operations on supported databases | Not the role of SQLGlot's former DataFrame API | Supported through SQLFrame integrations |
| Logical optimization and expression analysis        | Native SQLGlot functionality                   | Can use SQLGlot functionality           |

SQLFrame is a companion project, not an installation extra that restores the old `sqlglot.dataframe` namespace.

Its execution capabilities and backend coverage must be assessed independently of SQLGlot's own lightweight Python executor.

Primary sources:

`https://github.com/eakmanrq/sqlframe`

`https://sqlframe.readthedocs.io/en/stable/`

`https://pypi.org/project/sqlglot/30.0.0/`

## 15. Important semantic boundaries and capability interactions

The added capabilities provide a more complete picture of SQLGlot as programmable SQL infrastructure. They also sharpen the distinction between structural processing and full semantic understanding.

### 15.1 Transpilation does not automatically perform schema qualification or type annotation

This is one of the most consequential integration distinctions.

A standard call such as:

```
from sqlglot import transpiletranslated = transpile(    sql,    read="spark",    write="postgres",)
```

does not automatically perform full schema-aware qualification and type inference.

SQLGlot's documentation explicitly explains that some dialect translations require this information, but `qualify` and `annotate_types` are not applied by default during ordinary transpilation because they introduce additional work and complexity.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://sqlglot.com\&sz=32)

sqlglot.com



These are separate analysis operations that can be composed when their information is required.

This separation is useful for two different classes of workload.

Syntax-oriented transformation: When the requested dialect adaptation depends only on information directly available in the parsed expression, additional semantic processing may provide limited value.

Type-sensitive transformation: When the correct target representation depends on the types or identities of expressions, schema qualification and type annotation can supply information necessary to select the appropriate transformation.

The resulting distinction is not that schema-aware transpilation is always preferable. Rather, SQLGlot allows the caller to determine how much semantic processing a translation requires.

### 15.2 SQL source composition changes what can be analyzed

Source expansion, schema qualification, and lineage form complementary mechanisms.

A query referencing a named logical source may initially expose only the source name.

Expanding that source substitutes its underlying query definition.

Qualification can then resolve eligible column references using supplied schema information.

Type annotation can add expression-result types.

Finally, static dependency analysis can inspect relationships exposed by the expanded and qualified representation.

These operations are not automatically interchangeable. Their ordering matters, and some analyses may internally perform their own preparation.

For example, source expansion before qualification may expose additional references that the qualification stage must resolve. Conversely, expansion can introduce source aliases or naming collisions requiring further normalization.

This is an architectural opportunity, not a claim that SQLGlot exposes a single comprehensive function automatically performing every step.

### 15.3 Structural representation versus actual database semantics

Several distinctions apply across the newly detailed capabilities.

| Mechanism                       | What SQLGlot provides                                 | What remains external or uncertain                                        |
| ------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------- |
| `expand()`                      | Recursive AST substitution of named query definitions | Dependency-cycle management, source versioning, materialization semantics |
| `replace_placeholders()`        | Structured placeholder substitution                   | Server-side parameter binding, identifier authorization                   |
| `find_tables()`                 | Scope-sensitive referenced-table discovery            | Live object existence and physical-object classification                  |
| `DataType`                      | Structured SQL type declarations                      | Complete vendor type equivalence and runtime coercion behavior            |
| DDL expression classes          | Structured statements and object definitions          | Actual catalog state, applied migrations, engine acceptance               |
| `Grant` / `Revoke`              | Structured permission statements                      | Effective authorization and policy evaluation                             |
| `Pivot.output_columns()`        | Operator-aware output naming                          | Complete value-level lineage and resulting types                          |
| Expression equality and hashing | Structural identity under implementation rules        | Mathematical SQL equivalence                                              |
| `sqlglot.meta`                  | Limited AST annotations and directives                | General-purpose metadata schema, universal source preservation            |
| Source positions                | Selective AST location metadata                       | Lossless rewritten-to-original source maps                                |
| Generator transformations       | Supported dialect-specific rewrites                   | Guaranteed target-runtime compatibility                                   |
| `exp.Command`                   | Fallback representation of certain statements         | Fully parsed semantics of opaque statement content                        |

### 15.4 Practical capability combinations

The most important architectural implication is that these mechanisms can be combined without introducing an entirely separate SQL parsing or transformation framework.

Three particularly valuable combinations emerge.

SQL-defined model composition. `expand()`, source-name normalization, AST builders, and generator transformations collectively provide a foundation for composing separately defined SQL models, rewriting their references, and generating target SQL.

Structured database-definition analysis. DDL/DML expression classes, constraint representations, `DataType`, `find_tables()`, projection accessors, and query scopes enable extraction of database-object definitions and their declared relationships from SQL source.

Programmable SQL transformation infrastructure. The expression DSL, AST placeholders, metadata directives, expression validation, and generator preprocessing provide mechanisms for constructing and transforming SQL while retaining typed expression structure throughout the process.

These combinations can substantially reduce the need for custom SQL string processing, independently maintained SQL metadata extractors, and specialized transformation code.

The remaining responsibilities are concentrated around information SQLGlot does not inherently possess: the authoritative database catalog, source-definition lifecycle, actual execution behavior, security context, and dialect-specific semantics not captured by the relevant implementation.

## Addendum conclusion

The additional capabilities establish three important extensions to SQLGlot's architectural role.

First, SQLGlot is a structured SQL composition framework, not solely a parser and transpiler. Recursive definition expansion, placeholder substitution, expression builders, and transformation composition allow SQL to be assembled and rewritten directly as structured expressions.

Second, its representation of database semantics extends well beyond relational queries. Structured type declarations, DDL/DML statements, permissions, constraints, and operator-aware output schemas provide reusable infrastructure for analyzing SQL-defined objects and relationships.

Third, its semantic interfaces have deliberately different levels of completeness. The distinction between behavioral traits and concrete expressions, source references and resolved identities, recognized statements and opaque commands, and syntax translation and type-informed transformation is essential to understanding what its APIs actually guarantee.

These additions make SQLGlot substantially more capable as a general-purpose SQL language-processing foundation while preserving the need for external catalogs, runtime validation, and engine-specific semantic knowledge where those are required.