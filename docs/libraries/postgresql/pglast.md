# pglast 8.7 — Comprehensive Python Library Overview

Research date: October 24, 2026 | Target: pglast 8.7 | PostgreSQL grammar: 18 | License: GPL-3.0-or-later

## 1. Executive orientation

pglast is a PostgreSQL-native SQL parsing, abstract syntax tree (AST) manipulation, analysis, and SQL regeneration library for Python. It exposes PostgreSQL's actual parser through `libpg_query`, allowing Python programs to reason about the grammatical structure of PostgreSQL statements rather than manipulate SQL as unstructured strings.

Its significance extends considerably beyond parsing or formatting. pglast provides the foundations for syntax-aware SQL transformations, structural analysis, dependency discovery, query classification, statement fingerprinting, SQL generation, and custom SQL tooling.

Unlike a general-purpose SQL parser, pglast is deliberately tied to PostgreSQL's grammar and internal parse-node model. This provides unusually faithful access to PostgreSQL syntax, but it also means that its AST is PostgreSQL-specific rather than a normalized, database-independent SQL representation.

The central architectural distinction is that pglast operates primarily on PostgreSQL's raw parse tree, not its semantically analyzed or optimized query representation. It understands how SQL is written and structured, but does not independently resolve table definitions, infer all expression types, establish object existence, or reproduce the PostgreSQL planner.

### 1.1 Current version and parser compatibility

The latest stable release verified is pglast 8.7, published October 18, 2026.

- 8.0: Introduced PostgreSQL 18 grammar support, released July 9, 2026.
- 8.5: Updated the bundled `libpg_query` to a revision targeting PostgreSQL 18.6.
- 8.6: Significantly improved expression-parenthesization correctness, AST typing, and construction of serialized child nodes.
- 8.7: Fixed a regression in the `CollateClause` printer.

The major release branches align with PostgreSQL grammar generations: pglast 6 targets PostgreSQL 16, pglast 7 targets PostgreSQL 17, and pglast 8 targets PostgreSQL 18. These are parser-generation relationships, not restrictions on which PostgreSQL servers a client application can connect to.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2



Primary sources:

- Release history: [https://pglast.readthedocs.io/en/v8/changes.html](https://pglast.readthedocs.io/en/v8/changes.html?utm_source=chatgpt.com)
- Version-specific documentation: [https://pglast.readthedocs.io/en/v8/](https://pglast.readthedocs.io/en/v8/?utm_source=chatgpt.com)
- Python package: [https://pypi.org/project/pglast/8.7/](https://pypi.org/project/pglast/8.7/?utm_source=chatgpt.com)
- Source repository: [https://github.com/lelit/pglast](https://github.com/lelit/pglast?utm_source=chatgpt.com)

### 1.2 Capability map

| Capability family     | Principal functionality                                    | Architectural significance                                                  |
| --------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------- |
| PostgreSQL parsing    | `parse_sql`, JSON and Protobuf parsing                     | Work with native PostgreSQL syntax trees                                    |
| Typed AST model       | Generated node classes, enums, constructors                | Represent SQL as structured, mutable Python objects                         |
| AST traversal         | Visitors, node-type dispatch, ancestor tracking            | Implement structural analyses without bespoke parsers                       |
| AST transformation    | Node replacement, deletion, insertion, direct mutation     | Construct syntax-aware SQL rewriting systems                                |
| SQL serialization     | `RawStream`, `IndentedStream`, `prettify`                  | Regenerate executable PostgreSQL SQL from trees                             |
| Printer extensibility | Node printers, special-function printers                   | Customize serialization behavior                                            |
| Lexical analysis      | Token scanner, keywords, comments, statement splitting     | Support source-aware tooling without full AST analysis                      |
| SQL fingerprinting    | `fingerprint`                                              | Group structurally similar SQL statements                                   |
| Structural metadata   | Node equality, location metadata, structural serialization | Compare, inspect, and exchange structured representations                   |
| PL/pgSQL inspection   | Raw procedural-language parsing                            | Inspect procedural function bodies with different representation guarantees |

The strongest use cases typically combine these capabilities. For example, a system can parse SQL into a typed tree, analyze a specific grammatical construct, transform selected nodes, regenerate SQL, and parse the result again to verify that the intended grammatical structure has been preserved.

That workflow can eliminate substantial custom SQL parsing and rewriting logic. It does not, by itself, establish semantic equivalence, execution safety, or correctness against a particular database schema.

## 2. Architecture and execution model

### 2.1 Relationship between PostgreSQL, libpg_query, and pglast

pglast consists of several distinct layers:

Python application / SQL tooling

Analysis, classification, rewriting, validation and generation

pglast AST and visitors

Typed Python objects, traversal, mutations, structural helpers

pglast SQL printers

RawStream, IndentedStream, precedence, specialized printers

pglast.parser — Cython extension

Python bindings for parsing, scanning, splitting, fingerprinting and Protobuf deparsing

libpg_query — embedded PostgreSQL parser

PostgreSQL-derived lexer, grammar and raw parse-tree structures

The Cython extension links against `libpg_query`, which packages PostgreSQL parser functionality for use independently of a running PostgreSQL server.

The AST classes in `pglast.ast` are generated from PostgreSQL's C node definitions, predominantly those under `src/include/nodes`. This makes the Python object model closely reflect PostgreSQL's actual internal syntax structures.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation

+2



Source:

[https://github.com/pganalyze/libpg_query](https://github.com/pganalyze/libpg_query?utm_source=chatgpt.com)

### 2.2 Raw syntax versus analyzed SQL

PostgreSQL's own processing pipeline distinguishes several layers:

| Representation                  | Information available                                          | pglast support         |
| ------------------------------- | -------------------------------------------------------------- | ---------------------- |
| Lexical tokens                  | Keywords, identifiers, literals, punctuation, positions        | Native                 |
| Raw parse tree                  | Statements, expressions, syntactic relations, clauses          | Core capability        |
| Analyzed query tree             | Resolved objects, column bindings, types, expression semantics | Not produced by pglast |
| Rewritten query tree            | Results of PostgreSQL's rule-rewrite phase                     | Not produced by pglast |
| Logical/physical execution plan | Relational execution operations and planner decisions          | Not produced by pglast |

For example, `SELECT foo FROM bar` can be grammatically valid even if neither `foo` nor `bar` exists.

pglast can represent the column reference and relation reference. It cannot, without additional information, establish whether `foo` belongs to `bar`, what its data type is, or whether the query will pass PostgreSQL's semantic analysis.

This is especially consequential for automated dependency analysis and SQL rewriting: structural recognition is native; schema-dependent interpretation requires an additional semantic layer.

### 2.3 PostgreSQL-native rather than dialect-neutral

Because pglast derives its grammar from PostgreSQL, it naturally understands the syntactic families exposed by that version of PostgreSQL, including PostgreSQL-specific DDL, procedural declarations, operators, casts, window specifications, JSON constructs, conflict handling, `MERGE`, partitioning constructs, and other syntax not uniformly shared across databases.

The generated AST API also includes classes describing analyzed/planned PostgreSQL structures, such as `Query` and `Var`. Their existence does not mean that `parse_sql()` produces analyzed queries or execution plans.

An important consequence is that pglast has excellent native compatibility with PostgreSQL syntax, while deliberately offering little dialect abstraction. Converting between PostgreSQL and other SQL dialects is a separate capability typically associated with tools such as SQLGlot.

## 3. Parsing and representation interfaces

pglast exposes several representations of the same underlying PostgreSQL grammar.

### 3.1 Main parsing APIs

| API                                  | Result                         | Principal purpose                                |
| ------------------------------------ | ------------------------------ | ------------------------------------------------ |
| `pglast.parse_sql(sql)`              | Tuple of `ast.RawStmt` objects | Native Python AST manipulation                   |
| `parser.parse_sql_json(sql)`         | JSON-encoded string            | PostgreSQL parse-tree interchange and inspection |
| `parser.parse_sql_protobuf(sql)`     | Protobuf bytes                 | Compact, schema-defined parse-tree serialization |
| `parser.deparse_protobuf(data, ...)` | SQL string                     | Native `libpg_query` SQL regeneration            |
| `parser.parse_plpgsql_json(sql)`     | JSON string                    | Procedural-language parsing                      |
| `pglast.parse_plpgsql(sql)`          | Python dictionaries/lists      | Higher-level procedural-language inspection      |
| `parser.get_postgresql_version()`    | Version tuple                  | Determine underlying PostgreSQL parser version   |

These are alternative interfaces, not merely different formatting settings.

The Python AST representation supports object-oriented inspection and mutation. JSON and Protobuf expose the underlying `libpg_query` serialization formats and are particularly interesting for cross-process or cross-language integration.

The Python object serializer described below is a further, distinct representation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation

+2



Source:

[https://pglast.readthedocs.io/en/v8/parser.html](https://pglast.readthedocs.io/en/v8/parser.html?utm_source=chatgpt.com)

### 3.2 Native AST parsing

For example:

```
from pglast import parse_sql, astsql = """SELECT u.id, count(*)FROM users AS uGROUP BY u.id"""statements = parse_sql(sql)raw_statement = statements[0]select = raw_statement.stmtassert isinstance(raw_statement, ast.RawStmt)assert isinstance(select, ast.SelectStmt)relations = select.fromClausetargets = select.targetListgrouping = select.groupClause
```

This provides direct access to syntactic components without implementing SQL-specific string extraction.

The result is a tuple because a single input can contain multiple SQL statements. Each `RawStmt` carries the enclosed statement node and source-location metadata.

Nested fields generally correspond to PostgreSQL parser structures rather than an independently designed Pythonic SQL object model.

### 3.3 Native tree serialization

Each `ast.Node` can serialize itself into ordinary Python structures:

```
serialized = select(    depth=3,    skip_none=True,)
```

The serialization uses conventions including:

- `@` to identify AST node types.
- `#` to identify enum types, with their names and values.
- Tuples for node collections.
- Ordinary Python scalar values for attributes.
- `depth`, `ellipsis`, `skip_none`, and `enum_name` controls for representation.

A particularly useful capability is reconstructing AST nodes from their serialized dictionary representation:

```
clone = ast.SelectStmt(select())assert clone == selectassert clone is not select
```

This supports structural snapshots, AST cloning, inspection tools, and interchange within a Python-based system.

Important: This dictionary representation is not equivalent to the JSON structure emitted by `parser.parse_sql_json()`. Both describe PostgreSQL syntax, but they have different representation conventions and should not be treated as directly interchangeable schemas.

Source:

[https://pglast.readthedocs.io/en/v8/ast.html](https://pglast.readthedocs.io/en/v8/ast.html?utm_source=chatgpt.com)

## 4. Typed AST objects and programmatic construction

### 4.1 Generated node classes

`pglast.ast` provides Python classes corresponding to PostgreSQL's grammar and parse-node structures.

Significant examples include:

| Functional area         | Representative nodes                                                     |
| ----------------------- | ------------------------------------------------------------------------ |
| Statements              | `SelectStmt`, `InsertStmt`, `UpdateStmt`, `DeleteStmt`, `MergeStmt`      |
| Relations and joins     | `RangeVar`, `RangeSubselect`, `JoinExpr`, `RangeFunction`                |
| Expressions             | `A_Expr`, `BoolExpr`, `FuncCall`, `TypeCast`, `ColumnRef`, `SubLink`     |
| Query organization      | `WithClause`, `CommonTableExpr`, `SortBy`, `WindowDef`                   |
| DDL                     | `CreateStmt`, `AlterTableStmt`, `IndexStmt`, `ViewStmt`, `Constraint`    |
| Literals and parameters | `A_Const`, `String`, `Integer`, `ParamRef`                               |
| JSON-related syntax     | `JsonTable`, `JsonExpr`, `JsonObjectConstructor`, `JsonArrayConstructor` |

Their fields preserve distinctions that text-based SQL manipulation often loses.

For example, a relation reference may be a concrete table name, a subquery, a function-derived relation, or part of a join expression. A function invocation, type cast, and SQL special-function construct may produce similar textual forms yet have different AST representations.

This granularity permits transformations that operate on a specific semantic category of syntax without confusing it with identically named text elsewhere.

### 4.2 Runtime type validation

Node constructors accept recognized fields and validate many of their values.

```
from pglast import aststatement = ast.SelectStmt(all=True)statement.all = False     # validstatement.all = "wrong"   # raises ValueError
```

The generated model validates attribute names and supported Python representations, including PostgreSQL enums. Enum attributes can generally be assigned using enum instances, valid names, or appropriate serialized structures.

This is a useful guard against structurally invalid assignments, but not a guarantee that the resulting AST is a valid or executable PostgreSQL statement.

The library does not replace higher-level domain invariants, expression type-checking, or database catalog validation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation

+1



### 4.3 Structural equality and source metadata

pglast supports comparison between AST nodes based on their attributes while ignoring positional metadata such as:

- `location`
- `stmt_location`
- `stmt_len`

Consequently, statements that differ only in whitespace or comments can often produce equivalent ASTs.

This supports structural regression testing and parse-print-reparse verification without making formatting differences appear as meaningful changes.

However, AST equality should not be confused with SQL semantic equivalence. Two different ASTs can have the same execution semantics, and an AST comparison cannot detect errors introduced by incorrect catalog assumptions.

### 4.4 Construction and transformation capabilities

AST nodes can be created programmatically, not only obtained from parsing.

They can also be modified after construction, allowing pglast to serve as an intermediate representation for PostgreSQL SQL generation.

The architecture permits three approaches:

1. Parse and mutate: Start from an existing statement and change particular nodes.
2. Construct: Build statements from AST classes and serialize the result.
3. Hybrid: Parse a SQL template, replace selected subtrees with constructed nodes, and regenerate SQL.

The hybrid approach is especially useful when most of a complex SQL statement is already valid and only a constrained part needs programmatic generation.

Compared with concatenating SQL fragments, structured construction can reduce quoting mistakes, misplaced clauses, and accidental replacement of matching text in unrelated contexts.

It remains necessary to verify that the constructed tree satisfies PostgreSQL's grammatical and semantic constraints.

## 5. AST traversal, structural analysis, and transformation

The visitor infrastructure is one of pglast's most valuable capabilities. It provides a reusable traversal and mutation mechanism over PostgreSQL's heterogeneous parse-tree structures.

### 5.1 Visitor dispatch

`pglast.visitors.Visitor` performs breadth-first traversal.

Methods follow the naming convention `visit_<NodeClass>`, such as `visit_RangeVar`, `visit_FuncCall`, or `visit_SelectStmt`.

When no specialized method exists, the framework invokes the generic `visit()` method.

```
from collections import Counterfrom pglast import parse_sqlfrom pglast.visitors import Visitorclass NodeStatistics(Visitor):    def __init__(self):        self.counts = Counter()    def visit(self, ancestors, node):        self.counts[type(node).__name__] += 1stats = NodeStatistics()stats(parse_sql("SELECT id FROM users WHERE active"))print(stats.counts)
```

This kind of traversal can support structural inventories, pattern detection, query classification, and syntax-aware diagnostics without independently implementing recursive traversal for every PostgreSQL node.

The visitor dispatches by concrete AST class. More specialized behavior can be implemented using explicit class checks, ancestor inspection, or combinations of visitors.

### 5.2 Visitor actions

Visitors can return special actions that control traversal and modification.

| Action                 | Behavior                                            | Use                                       |
| ---------------------- | --------------------------------------------------- | ----------------------------------------- |
| `None` / `Continue`    | Continue into descendants                           | Ordinary analysis                         |
| `Skip`                 | Do not descend into the current subtree             | Scope restrictions and selective analysis |
| `Delete`               | Remove the visited element or clear its parent slot | Eliminate selected constructs             |
| Replacement `ast.Node` | Replace the current node                            | Syntax rewriting                          |
| `(Add, node, ...)`     | Insert nodes after the current sequence element     | Expand AST collections                    |

`Add` was implemented as documented in the pglast 7.14 line and is available in 8.7.

Visitor-mediated structural modifications are accumulated and applied after traversal. This helps avoid the usual indexing problems associated with deleting or inserting elements while iterating over nested sequences.

An important consequence is that a newly inserted or replacement subtree is not automatically revisited as part of the same traversal. Transformations requiring multiple stages may use successive passes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation

+2



### 5.3 Practical AST rewriting

The following pattern illustrates targeted removal of a syntactic constraint:

```
from pglast import parse_sql, enumsfrom pglast.stream import RawStreamfrom pglast.visitors import Visitor, Deleteclass RemoveExplicitNull(Visitor):    def visit_Constraint(self, ancestors, node):        if node.contype == enums.ConstrType.CONSTR_NULL:            return Deletetree = parse_sql("""CREATE TABLE example (    a integer NULL,    b integer NOT NULL)""")RemoveExplicitNull()(tree)result = RawStream()(tree)
```

This is closely based on the upstream example.

The visitor identifies an AST constraint of a particular type rather than searching for the text `NULL`, which could also occur inside expressions, type declarations, strings, and comments.

That distinction is fundamental to reliable SQL rewriting.

### 5.4 Ancestor tracking and structural context

Each visitor receives an `Ancestor` object representing the path to the current node.

This is more than a parent pointer. It tracks:

- The hierarchical chain from the root.
- The containing AST objects.
- Attribute names and sequence indexes.
- Positions inside nested tuples.
- The nearest ancestor matching a desired type.

The `Ancestor` API supports operations such as indexing into the ancestry chain, `find_nearest()`, and resolving a path against a tree using `@`.

`abs(ancestors)` finds the nearest ancestor that is an AST node rather than an intermediate tuple.

These capabilities matter because SQL meaning depends strongly on context.

For example, a `ColumnRef` occurring in a projection is not equivalent in role to one appearing in a join condition, `WHERE` clause, grouping expression, or assignment target.

Ancestor-aware visitors can distinguish such cases without each analysis independently maintaining a context stack.

The same mechanism is used internally to give node printers sufficient context to serialize constructs correctly.

Source:

[https://pglast.readthedocs.io/en/v8/visitors.html](https://pglast.readthedocs.io/en/v8/visitors.html?utm_source=chatgpt.com)

### 5.5 Built-in relation dependency discovery

A particularly useful higher-level facility is:

```
from pglast.visitors import referenced_relationssql = """WITH selected AS (    SELECT id FROM public.orders)SELECT *FROM selectedJOIN public.customers USING (id)"""relations = referenced_relations(sql)
```

The helper identifies syntactically referenced relations while accounting for common table expressions.

For example, upstream documents:

```
referenced_relations(    "WITH q1(x,y) AS (SELECT 1,2) "    "SELECT * FROM q1, q2")# {'q2'}
```

The underlying `ReferencedRelations` visitor has logic for:

- Relation references represented by `RangeVar`.
- Schema-qualified and catalog-qualified names.
- CTE names that should not be treated as base relations.
- Ordered visibility of nonrecursive CTE definitions.
- Simultaneous visibility of recursive CTE names.
- Relation references within several DML statements.
- Selected `DROP` statement targets.

This is significantly more capable than collecting every `RangeVar` indiscriminately, because CTE names are part of query-local scope.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



Limit: The helper returns syntactic relation names, not catalog-resolved relation identities or complete column-level lineage. It also collapses results into a set, losing occurrence information and the distinction between read, write, and schema-modification relationships.

For detailed dependency analysis, it is best understood as a useful native building block rather than a complete semantic lineage engine.

Source:

[https://github.com/lelit/pglast/blob/v8/pglast/visitors.py](https://github.com/lelit/pglast/blob/v8/pglast/visitors.py?utm_source=chatgpt.com)

## 6. Lexical analysis, splitting, and source locations

AST parsing is not always the appropriate level of abstraction. pglast also provides direct access to PostgreSQL's lexical scanner.

### 6.1 Token scanner

`pglast.parser.scan()` returns a sequence of named tuples representing tokens.

Each token provides:

| Field   | Meaning                                       |
| ------- | --------------------------------------------- |
| `start` | First character index                         |
| `end`   | Last character index, inclusive               |
| `name`  | PostgreSQL token identifier, such as `SELECT` |
| `kind`  | Classification, such as `RESERVED_KEYWORD`    |

For example:

```
from pglast.parser import scansql = "SELECT id FROM users WHERE active"for token in scan(sql):    fragment = sql[token.start:token.end + 1]    print(token.kind, fragment)
```

The scanner is useful for source-aware inspection, keyword identification, highlighting, token-level diagnostics, and tools that need to preserve original text.

It also exposes PostgreSQL lexical rules without requiring the caller to duplicate special handling for quoted identifiers, strings, dollar quoting, comments, or embedded punctuation.

### 6.2 Keyword classification

`pglast.keywords` exposes generated keyword groups:

- `RESERVED_KEYWORDS`
- `UNRESERVED_KEYWORDS`
- `COL_NAME_KEYWORDS`
- `TYPE_FUNC_NAME_KEYWORDS`

These represent PostgreSQL's distinctions between words permitted in different grammatical contexts.

They are useful for identifier quoting, SQL generation, and recognizing when a word must be handled differently in a column-name or function-name position.

The library's native serialization machinery already provides context-specific quoting behavior. Directly consulting these sets is most valuable when implementing additional custom tooling rather than reimplementing the standard printers.

Source:

[https://pglast.readthedocs.io/en/v8/keywords.html](https://pglast.readthedocs.io/en/v8/keywords.html?utm_source=chatgpt.com)

### 6.3 Statement splitting

`pglast.split()` provides syntax-aware segmentation of SQL scripts.

It has two fundamentally different execution modes:

| Mode                | Behavior                   | Appropriate conditions                                                             |
| ------------------- | -------------------------- | ---------------------------------------------------------------------------------- |
| `with_parser=True`  | Uses the PostgreSQL parser | Valid SQL; parsing errors should be surfaced                                       |
| `with_parser=False` | Uses the lexical scanner   | SQL may contain grammatical errors, but its lexical structure remains recognizable |

This is important for SQL scripts containing quoted strings, procedural function bodies, and expressions where semicolons do not necessarily terminate a statement.

```
from pglast import splitsql = "SELECT 1; SELECT 2"statements = split(sql)slices = split(sql, only_slices=True)original_parts = [sql[s] for s in slices]
```

`only_slices=True` is easily overlooked. Instead of returning copied statement strings, it returns Python `slice` objects identifying the corresponding regions in the original input.

This makes it possible to preserve a connection between extracted statements and source text, including when implementing diagnostics, editing tools, and statement-level analysis.

Leading and trailing whitespace are excluded from the extracted statements. The splitter is not a general-purpose lossless document segmentation format.

### 6.4 Unicode and source-coordinate semantics

`libpg_query` operates on UTF-8 data. PostgreSQL parse locations are therefore typically represented as byte offsets in the encoded string.

Python, however, indexes Unicode strings by code-point position.

pglast provides `parser.Displacements` to translate UTF-8 byte offsets into Python string indexes.

There is an important distinction between interfaces:

- Higher-level token scanning and splitting perform relevant offset conversions for Python consumers.
- Raw `libpg_query` JSON structures can contain original PostgreSQL byte offsets.
- AST node location metadata needs careful handling when mapped back to original Unicode source.

Version 7.14 also fixed a Unicode-related `RawStmt.stmt_len` issue.

A source-aware tool should explicitly identify which coordinate system an API is providing, rather than assuming that all reported locations can be used directly for Python string slicing.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation

+2



Sources:

[https://pglast.readthedocs.io/en/v8/parser.html](https://pglast.readthedocs.io/en/v8/parser.html?utm_source=chatgpt.com)

[https://pglast.readthedocs.io/en/v8/usage.html](https://pglast.readthedocs.io/en/v8/usage.html?utm_source=chatgpt.com)

## 7. SQL fingerprinting and structural grouping

### 7.1 Fingerprint generation

`pglast.parser.fingerprint()` exposes the corresponding `libpg_query` function.

```
from pglast import fingerprinta = fingerprint(    "SELECT * FROM orders WHERE id = 100")b = fingerprint(    "SELECT * FROM orders WHERE id = 200")assert a == b
```

The mechanism is designed to group queries whose differences do not change the relevant normalized query structure.

This is useful for identifying repeated query patterns, aggregating diagnostics, clustering SQL workloads, and reducing the cardinality of observed statement variants.

The fingerprint is a compact digest, not a reversible representation of the statement.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation

+1



### 7.2 Relationship to PostgreSQL query identifiers

The underlying `libpg_query` implementation attempts to maintain compatibility with PostgreSQL's query-identifier behavior.

A particularly consequential version-specific change is that PostgreSQL 18 changed how relation schema names and aliases contribute to query identity.

The upstream `libpg_query` documentation explains that its default PostgreSQL 18 fingerprint behavior differs from PostgreSQL 17 compatibility behavior.

The C library provides an option for PostgreSQL 17-compatible handling, but pglast 8.7's public `fingerprint(query)` wrapper exposes only the query argument, not that configuration option.

Thus, the behavior of the underlying PostgreSQL parser generation matters when using fingerprints as durable identifiers or comparing them across versions.

Source:

[https://github.com/pganalyze/libpg_query](https://github.com/pganalyze/libpg_query?utm_source=chatgpt.com)

### 7.3 Fingerprints are not semantic equivalence tests

Several distinctions are essential:

| Mechanism                       | What it establishes                                                                       |
| ------------------------------- | ----------------------------------------------------------------------------------------- |
| SQL string equality             | Exact textual identity                                                                    |
| AST equality                    | Equality under pglast's structural comparison rules                                       |
| SQL fingerprint equality        | Membership in the fingerprint algorithm's normalization class, subject to hash collisions |
| PostgreSQL semantic equivalence | Equivalent behavior under relevant schema, data, types, functions, and execution context  |

These are not interchangeable.

For example, SQL statements may be logically equivalent despite producing different ASTs and different fingerprints. Conversely, two queries with the same fingerprint may differ in the values they use and return different results.

Fingerprinting is therefore particularly useful for observability and query-shape grouping, but not sufficient to validate a rewrite or authorize execution.

## 8. SQL regeneration, formatting, and deparsing

pglast provides more than one SQL regeneration mechanism, with important differences.

### 8.1 `RawStream` and `IndentedStream`

`pglast.stream` provides two main Python AST serialization approaches.

`RawStream` creates a compact, unadorned SQL representation.

`IndentedStream` extends the same machinery with structured formatting and indentation.

Both can receive a SQL string, an AST node, or a supported tuple of AST nodes.

```
from pglast import parse_sql, prettifyfrom pglast.stream import RawStream, IndentedStreamtree = parse_sql(    "SELECT id, name FROM users WHERE active")raw_sql = RawStream()(tree)formatted_sql = IndentedStream(    comma_at_eoln=True)(tree)simple_format = prettify(    "SELECT id, name FROM users WHERE active")
```

Because regeneration is AST-driven, it does not merely modify whitespace in the original source. It reconstructs SQL using PostgreSQL syntax knowledge.

### 8.2 Formatting controls

`RawStream` includes controls for:

| Option                             | Function                                                |
| ---------------------------------- | ------------------------------------------------------- |
| `separate_statements`              | Spacing between multiple statements                     |
| `special_functions`                | Prefer special SQL function syntax where supported      |
| `comma_at_eoln`                    | Position commas at ends rather than beginnings of lines |
| `semicolon_after_last_statement`   | Emit a final semicolon                                  |
| `comments`                         | Supply extracted comments for rendering                 |
| `remove_pg_catalog_from_functions` | Remove selected explicit system-catalog qualification   |

`IndentedStream` additionally supports `compact_lists_margin` and `split_string_literals_threshold`.

These options allow the output layer to accommodate different SQL presentation conventions without changing the underlying AST analysis.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation

+1



### 8.3 Precedence-aware expression printing

A major improvement in pglast 8.6 was replacing ad hoc parenthesization heuristics with explicit expression-precedence and position rules.

The `pglast.precedence` module models PostgreSQL grammar contexts including `a_expr`, `b_expr`, and `c_expr`.

The printer must consider several factors simultaneously:

- The precedence of the enclosing expression.
- The precedence of the operand.
- Whether the operand is on the left or right.
- Operator associativity and nonassociativity.
- The particular grammar context in which an expression is permitted.

The key interfaces include `ExprPrec`, `ExprContext`, `Side`, `expr_precedence()`, `needs_parens_for_precedence()`, and `RawStream.print_operand()`.

For example, preserving the structure of `a - (b - c)` requires different parentheses from preserving `(a - b) - c`.

The same issue becomes much more complex with PostgreSQL-specific operators, casts, `BETWEEN`, `IS`, `AT TIME ZONE`, and specialized SQL constructs.

This makes pglast's native serializer much more useful than a generic string generator for AST transformations.

However, the existence of precedence-correct serialization does not mean that every possible user-constructed AST is valid.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation

+2



Source:

[https://pglast.readthedocs.io/en/v8/precedence.html](https://pglast.readthedocs.io/en/v8/precedence.html?utm_source=chatgpt.com)

### 8.4 Native Protobuf deparsing

An alternative path bypasses the Python AST serializer:

```
from pglast.parser import (    parse_sql_protobuf,    deparse_protobuf,)data = parse_sql_protobuf(    "SELECT id FROM users")sql = deparse_protobuf(    data,    pretty_print=True,    indent_size=4,    max_line_length=80,)
```

`deparse_protobuf()` also supports trailing-newline and comma-position settings.

This path uses `libpg_query`'s own deparser, rather than the Python `RawStream`/`IndentedStream` printers.

The distinction matters:

- Python AST serialization is naturally integrated with pglast visitors, node construction, and custom printers.
- Protobuf serialization provides a schema-defined representation suitable for integration with other tools using the corresponding PostgreSQL parse-tree schema.
- A Protobuf buffer is not automatically an editable `pglast.ast` tree. Transforming it may involve an additional representation conversion.

Neither representation should be assumed byte-stable across major PostgreSQL grammar generations.

### 8.5 Round-trip safety checks

`prettify()` includes a particularly valuable feature:

```
safe_result = prettify(    original_sql,    safety_belt=True,)
```

When enabled, the library:

1. Parses the original SQL.
2. Serializes it to formatted SQL.
3. Parses the formatted SQL again.
4. Compares the two ASTs.
5. Warns and returns the original SQL if reparsing fails or the structures differ.

The safety belt is disabled by default.

This provides a meaningful structural correctness check against serialization regressions, without requiring a PostgreSQL server.

It is not an execution-equivalence proof, but it can detect many cases where a formatter changes the grammatical structure unexpectedly.

Source:

[https://pglast.readthedocs.io/en/v8/api.html](https://pglast.readthedocs.io/en/v8/api.html?utm_source=chatgpt.com)

## 9. Custom SQL printers and serialization extension points

Beyond the built-in serializers, pglast allows applications to extend and override how individual AST constructs are rendered.

This is a substantial capability: the AST and output representation need not be coupled to a single fixed serialization policy.

### 9.1 Node printer registration

`pglast.printers.node_printer()` registers rendering functions associated with AST node types.

```
from pglast import astfrom pglast.printers import node_printer@node_printer(ast.ParamRef, override=True)def custom_parameter(node, output):    output.write(f"${node.number}")
```

The printer receives the node and output stream.

Printer functions can use the stream's facilities for spacing, indentation, list handling, SQL identifiers, literals, and nested nodes rather than implementing SQL syntax from scratch.

The `override` parameter controls whether an existing printer registration can be replaced. Duplicate registrations otherwise raise `PrinterAlreadyPresentError`.

Registrations operate through the `NODE_PRINTERS` registry, so overrides can affect other serialization operations in the same Python process.

### 9.2 Context-specific printer dispatch

An easily overlooked facility is that printers can be registered against the combination of a parent context and a node type.

The decorator supports registrations conceptually equivalent to:

```
@node_printer(parent_type, child_type)def context_specific_printer(node, output):    ...
```

The parent specification can also represent multiple parent types.

This matters because PostgreSQL reuses certain AST structures across contexts that require different SQL representations.

For example, the same `ResTarget` structure can participate in query projections and assignment targets. A single unconditional printer may not be appropriate in every location.

The registry therefore permits specialization without creating artificial AST subclasses solely to distinguish serialization context.

`get_printer_for_node()` implements this context-sensitive lookup.

### 9.3 Special-function printers

PostgreSQL's parser transforms some familiar SQL constructs into function-call representations.

Examples include the relationships between:

| SQL syntax                          | Internal or equivalent function representation |
| ----------------------------------- | ---------------------------------------------- |
| `EXTRACT(field FROM value)`         | `pg_catalog.date_part(...)`                    |
| `value AT TIME ZONE zone`           | `pg_catalog.timezone(...)`                     |
| `POSITION(substring IN string)`     | `pg_catalog.position(...)`                     |
| `TRIM(...)`                         | `pg_catalog.btrim`, `ltrim`, or `rtrim`        |
| `OVERLAY(... PLACING ... FROM ...)` | `pg_catalog.overlay(...)`                      |

The `special_functions` option enables the specialized printers that reconstruct selected SQL syntax forms.

`pglast.printers.special_function()` allows registration of additional function-specific printer behavior.

This is useful when generated SQL needs to follow a particular style, express specialized PostgreSQL constructs, or preserve syntax conventions that would otherwise be lost during parsing.

The feature does not constitute a general SQL expression optimizer or semantic rewrite engine.

### 9.4 Extending the serializer versus modifying the AST

There are two distinct ways to customize output:

| Technique             | Changes                             | When valuable                                                |
| --------------------- | ----------------------------------- | ------------------------------------------------------------ |
| AST transformation    | Underlying syntactic representation | Actual query rewriting                                       |
| Printer customization | Representation of an existing AST   | Formatting, alternate syntax, specialized output conventions |

Keeping these concerns separate is beneficial.

When only the textual representation needs to change, custom printers may eliminate unnecessary AST mutations. Conversely, a printer should not be used as a substitute for a structural transformation when the intended operation really changes the query.

Printer customization also introduces responsibility for correct escaping, parenthesization, and statement validity. It should not be mistaken for safe database-parameter substitution.

Sources:

[https://pglast.readthedocs.io/en/v8/printers.html](https://pglast.readthedocs.io/en/v8/printers.html?utm_source=chatgpt.com)

[https://pglast.readthedocs.io/en/v8/sfuncs.html](https://pglast.readthedocs.io/en/v8/sfuncs.html?utm_source=chatgpt.com)

[https://pglast.readthedocs.io/en/v8/stream.html](https://pglast.readthedocs.io/en/v8/stream.html?utm_source=chatgpt.com)

## 10. Comments, procedural SQL, and command-line tooling

### 10.1 Comments and formatting preservation

By default, `prettify()` does not preserve comments.

To request comment preservation:

```
from pglast import prettifyresult = prettify(    sql,    preserve_comments=True,)
```

pglast extracts comments separately and attempts to place them appropriately in regenerated SQL.

This behavior is necessarily approximate.

Not all PostgreSQL AST nodes contain sufficient location information to determine the exact original placement of comments. The upstream documentation explicitly notes cases where it cannot distinguish a comment before a clause from one after the preceding expression.

There are further differences between output streams.

`RawStream` produces essentially single-line SQL. To avoid swallowing the remainder of that line, it converts SQL-style `--` comments into C-style `/* ... */` comments.

The conversion can change the exact comment text, including escaping embedded C-comment terminators.

Therefore, pglast should not be characterized as a lossless SQL concrete-syntax-tree editor.

Its AST is the authoritative representation of SQL structure, not a complete preservation of every original source character.

For transformations requiring exact retention of comments and formatting, lexical token information and original-source editing may be more suitable than reprinting the entire AST.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation

+1



### 10.2 PL/pgSQL parsing

pglast exposes procedural-language parsing through:

```
from pglast import parse_plpgsqlprocedural_tree = parse_plpgsql(sql)
```

At the lower level:

```
from pglast.parser import parse_plpgsql_jsonjson_tree = parse_plpgsql_json(sql)
```

These interfaces can expose details of PL/pgSQL functions, including blocks, declarations, procedural statements, and expressions.

However, PL/pgSQL support has an important architectural limitation.

pglast 8.7 does not provide the same generated, strongly structured `ast.Node` hierarchy for PL/pgSQL that it provides for ordinary SQL statements.

The higher-level procedural parser returns nested Python dictionaries, lists, and scalar values.

This means the general SQL visitor and printer infrastructure does not automatically provide equivalent capabilities for procedural trees.

Moreover, parsing a `CREATE FUNCTION ... LANGUAGE plpgsql` statement with `parse_sql()` exposes the surrounding SQL definition, but the procedural body is represented differently from a recursively parsed SQL statement tree.

The 8.0 release notes explicitly state that richer PL/pgSQL support was not completed before the release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation

+1



These interfaces can support PL/pgSQL structural inspection, but comprehensive procedural refactoring, scope resolution, and AST rewriting require additional machinery.

### 10.3 `pgpp` command-line utility

The package includes `pgpp`, a PostgreSQL SQL formatter and inspection utility.

Examples:

```
# Format SQL from standard input
echo "select a,b from t" | pgpp

# Compact single-line formatting
pgpp --normalize -S "select a,b from t"

# Inspect a parse tree
pgpp --parse-tree --statement "select 1"

# Preserve comments where possible
pgpp --preserve-comments -S "/* header */ select 1"

# Use alternate special-function syntax
pgpp --special-functions -S \
  "select extract(year from current_timestamp)"
```

Other options control comma placement, compact formatting, and string literal splitting.

One distinction is worth emphasizing: `pgpp --normalize` refers to a compact normalized textual presentation, not the constant-parameter normalization mechanism associated with some `libpg_query` integrations.

The command-line tool is useful for inspecting how pglast interprets SQL and for comparing formatting or regeneration behavior without building a Python wrapper.

Source:

[https://pglast.readthedocs.io/en/v8/usage.html](https://pglast.readthedocs.io/en/v8/usage.html?utm_source=chatgpt.com)

## 11. Architectural applications and capability combinations

The individual APIs become most valuable when combined into larger analysis or transformation operations.

The following are general architectural possibilities rather than claims that pglast implements each entire system.

### 11.1 SQL structural analysis

A native structural-analysis pipeline can be expressed as:

SQL statements

PostgreSQL AST parsing

Statement classification

Relation dependencies

Expression analysis

Structured analysis results

pglast natively supplies the parser, typed structures, visitors, and selected helpers needed for this pipeline.

Applications can build higher-level extraction and classification functionality around them.

For example:

- Classify statements into query, DML, DDL, and transaction families.
- Detect particular operators, function calls, subqueries, or constructs.
- Extract syntactically referenced relations.
- Locate clauses containing expressions of interest.
- Inventory indexes, table constraints, or schema modifications in SQL scripts.
- Identify patterns associated with application-specific SQL rules.

The advantage is that each analysis operates on the same PostgreSQL AST rather than maintaining independent regular expressions or specialized parsers.

### 11.2 Syntax-aware transformation engines

A common transformation pattern is:

`Parse → identify nodes → apply rewrite → regenerate SQL → parse again → compare against the intended result`

This can support such operations as:

- Controlled renaming of explicitly identified relations.
- Replacing or qualifying selected function calls.
- Introducing additional query predicates.
- Modifying selected DDL attributes.
- Rewriting constrained SQL templates.
- Enforcing project-independent SQL structural conventions.

The visitor framework handles traversal and structural mutation. The printers handle SQL reconstruction.

However, the application must supply the transformation rules and their semantic prerequisites.

For example, adding a predicate to a query containing outer joins requires understanding the intended semantics of the join. A syntactically valid rewrite can still alter which rows appear in the result.

### 11.3 Schema and migration inspection

PostgreSQL DDL is unusually rich, making syntax-aware analysis especially valuable.

pglast exposes AST structures for table definitions, indexes, constraints, types, triggers, schemas, views, publications, subscriptions, policies, and numerous `ALTER` operations.

That enables general-purpose tooling to inspect the declared intent of a migration or SQL script.

For example, it can distinguish:

- Adding versus dropping a column.
- Defining versus removing a constraint.
- Creating an index versus altering an existing object.
- Creating a view versus defining a materialized view.
- Specifying partitioning or inheritance-related syntax.

This can support static migration analysis and structured audit records.

It does not reproduce the database's current schema state or prove that a proposed migration can execute successfully against that state.

### 11.4 Query diagnostics and workload analysis

Fingerprinting, relation discovery, statement classification, and structural traversal can work together.

For instance, SQL collected from logs or traces can be classified by query fingerprint, then analyzed for common grammatical characteristics.

That provides a basis for reporting which query shapes use joins, subqueries, aggregations, window functions, particular JSON operators, or other PostgreSQL constructs.

Such structural information can complement execution timings and query plans obtained from PostgreSQL.

The distinction is important: pglast describes the submitted SQL; PostgreSQL execution diagnostics describe how the database handled it.

### 11.5 Syntax-aware SQL interfaces for programming agents

pglast's structured representations can serve as an intermediate layer between natural-language code transformations and executable SQL.

Rather than requiring an agent to manipulate an entire SQL script as text, an interface can expose:

- Statement classification.
- Relevant AST subtrees.
- Serialized node attributes.
- Identified relation references.
- Source positions.
- Candidate rewrite locations.
- Regenerated SQL after mutation.

This supports smaller, more precisely scoped SQL operations.

It can also reduce duplicated parsing logic across analysis, editing, and diagnostics tools.

The remaining requirements—semantic validation, authorization, binding to real database objects, and safe execution—belong to surrounding systems rather than pglast.

## 12. Integrations and adjacent libraries

pglast is most useful when its boundaries relative to other tools are understood.

### 12.1 Integration with the PostgreSQL ecosystem

| Library or component | Relationship to pglast                                  | Important distinction                                                           |
| -------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `libpg_query`        | Underlying native engine                                | Supplies the actual PostgreSQL-derived parser                                   |
| `psycopg`            | Complementary database driver                           | Executes SQL and accesses server-side behavior                                  |
| SQLAlchemy           | Complementary SQL construction and database abstraction | Maintains its own expression system, metadata, and dialect implementations      |
| SQLGlot              | Alternative or complementary SQL AST system             | Focuses on multi-dialect parsing, transformation, and transpilation             |
| `sqlparse`           | Alternative for lightweight SQL handling                | Operates primarily on tokens and formatting rather than PostgreSQL's native AST |
| Rust `pg_query`      | Related binding to the same underlying engine family    | Provides PostgreSQL parsing capabilities in Rust                                |
| PostgreSQL server    | Source of authoritative semantic and execution behavior | Performs catalog resolution, type analysis, rewriting, planning, and execution  |

These relationships do not imply that the libraries share compatible in-memory AST classes or have automatic conversion interfaces.

### 12.2 pglast versus SQLGlot

The two libraries can both parse SQL and expose transformable ASTs, but their architectural objectives differ.

| Dimension                   | pglast                                   | SQLGlot                                                        |
| --------------------------- | ---------------------------------------- | -------------------------------------------------------------- |
| Primary design              | Native PostgreSQL grammar representation | Generalized SQL expression and dialect model                   |
| Parser implementation       | PostgreSQL-derived native parser         | SQLGlot parser with optional compiled acceleration             |
| Dialect coverage            | PostgreSQL version families              | Multiple SQL dialects                                          |
| AST representation          | Mirrors PostgreSQL node structures       | SQLGlot's own expression hierarchy                             |
| PostgreSQL grammar fidelity | Central design objective                 | One supported dialect among many                               |
| SQL translation             | Not a general-purpose feature            | Core capability                                                |
| Schema-aware analysis       | Requires additional semantic information | Provides its own qualification and optimization infrastructure |
| Fingerprinting              | Native `libpg_query` integration         | Separate normalization and analysis mechanisms                 |
| SQL generation              | PostgreSQL-specific printers             | Dialect-specific SQL generators                                |

pglast is particularly compelling where native PostgreSQL syntax fidelity is more important than generalized SQL representation.

SQLGlot becomes more attractive where cross-dialect operations, normalized expression modeling, or relational query transformations are central.

Using both is possible, but their ASTs are different. Any conversion boundary should be treated as potentially lossy unless the relevant PostgreSQL constructs are explicitly supported.

SQLGlot sources:

[https://github.com/tobymao/sqlglot](https://github.com/tobymao/sqlglot?utm_source=chatgpt.com)

[https://sqlglot.com/](https://sqlglot.com/?utm_source=chatgpt.com)

### 12.3 PostgreSQL parsing across Python and Rust

The Rust `pg_query` crate is an especially relevant adjacent tool.

It uses `libpg_query` to provide PostgreSQL parsing and related functionality for Rust programs.

Consequently, Python and Rust systems can potentially exchange PostgreSQL parse-tree information through `libpg_query`-derived representations rather than inventing a completely independent SQL grammar or serialization.

An important distinction is that shared underlying technology does not guarantee identical data models or release compatibility.

The PostgreSQL grammar generation, generated Protobuf schema, underlying library version, and wrapper-level conversion behavior must align.

In particular, a Python system using pglast 8.x should not assume that every Rust `pg_query` version targets PostgreSQL 18.

Rust reference:

[https://docs.rs/pg_query/latest/pg_query/](https://docs.rs/pg_query/latest/pg_query/?utm_source=chatgpt.com)

Underlying library:

[https://github.com/pganalyze/libpg_query](https://github.com/pganalyze/libpg_query?utm_source=chatgpt.com)

### 12.4 Using pglast alongside database metadata

A powerful general combination is:

`pglast syntax tree + database catalog metadata + semantic interpretation`

For example, pglast can identify a `RangeVar` and associated `ColumnRef` nodes.

Database metadata can establish the actual relation definitions, columns, types, and constraints.

A semantic analysis layer can then resolve references and implement rules that are not possible from syntax alone.

This separation allows native PostgreSQL components to provide much of the underlying truth:

- pglast provides grammar and AST structure.
- PostgreSQL provides authoritative catalog information.
- A database driver retrieves catalog information and executes statements.
- An additional semantic layer relates the AST to the catalog.

The intermediate semantic layer is not supplied automatically by pglast, but the combination avoids duplicating PostgreSQL's SQL grammar.

## 13. Performance, correctness, and operational constraints

### 13.1 Performance characteristics

pglast has a different execution profile depending on which capability is used.

| Operation                        | Main execution mechanism                          | Consequence                                                  |
| -------------------------------- | ------------------------------------------------- | ------------------------------------------------------------ |
| SQL parsing                      | Native `libpg_query`, exposed through Cython      | Avoids implementing the SQL grammar in Python                |
| Fingerprinting                   | Native `libpg_query`                              | Does not require materializing a complete Python AST         |
| Lexical scanning                 | Native scanner and Python result conversion       | Suitable for token-level analysis                            |
| Python AST construction          | Native parsing followed by Python object creation | Introduces Python object allocation and representation costs |
| Visitor traversal                | Python visitor machinery                          | Cost depends on tree size, callbacks, and traversal strategy |
| SQL regeneration through streams | Python printers                                   | Formatting and dispatch are performed in Python              |
| Protobuf deparsing               | Native `libpg_query`                              | Alternative to Python stream-based regeneration              |

The distinction between native operations and operations that construct or traverse Python objects is particularly important.

For high-volume query workloads requiring only grouping or fingerprinting, the native fingerprinting path can avoid constructing AST objects unnecessarily.

For richer structural analysis, Python AST materialization is valuable precisely because it exposes the information needed for advanced operations.

The upstream implementation also releases the Python GIL around several native `libpg_query` calls. That does not establish that arbitrary mutation of shared AST objects or globally registered printers is thread-safe.

No general quantitative performance claim is warranted without workload-specific measurements.

### 13.2 Parse errors and diagnostics

`pglast.parser.ParseError` represents parsing failures.

The parser exposes PostgreSQL-derived syntax error messages and source locations.

The source implementation converts many native UTF-8 offsets into Python string indexes when constructing exceptions.

The deparser also exposes `DeparseError` for unsuccessful Protobuf-to-SQL conversion.

A useful distinction is:

- Parsing errors establish grammatical problems detected by the parser.
- AST assignment errors establish incompatibility with the generated node model.
- Deparsing errors indicate problems regenerating SQL from supported representations.
- PostgreSQL execution errors cover a broader range of semantic, permission, catalog, and runtime problems.

These error categories are complementary.

### 13.3 Important correctness boundaries

The following constraints are especially consequential for robust tooling.

| Boundary                      | Implication                                                                |
| ----------------------------- | -------------------------------------------------------------------------- |
| Syntax versus semantics       | Successful parsing does not prove that SQL can execute                     |
| Structural equality           | Equality ignores positions but does not establish execution equivalence    |
| Native AST versus source text | Comments, whitespace, and some syntactic spelling choices can be lost      |
| Parser version                | Different PostgreSQL major versions can change node structures and grammar |
| Visitor mutations             | Rewrites can be structurally valid but semantically incorrect              |
| Printer overrides             | Custom output logic can invalidate regeneration guarantees                 |
| Fingerprinting                | Hash identity is not unique semantic identity                              |
| PL/pgSQL representation       | Does not have the same typed-node and visitor capabilities as SQL          |
| SQL injection                 | AST manipulation is not a substitute for bound database parameters         |
| Object identity               | Relation and column names require schema-aware resolution                  |

Two further operational details deserve attention.

First, pglast exposes `parser.comments()`, but the upstream documentation describes this particular low-level interface as primarily internal and incidentally exposed. It should not be treated as a strongly guaranteed public extension contract.

Second, `remove_pg_catalog_from_functions` can alter the explicit qualification of function names. Depending on namespace resolution and the database environment, removing qualification may be more than a cosmetic change.

### 13.4 Installation, Python support, and packaging

The standard installation is:

```
pip install pglast
```

Version-specific installation:

```
pip install "pglast==8.7"
```

PyPI identifies support for Python 3.10 through 3.15 and distributes platform-specific wheels, including Linux, macOS, and Windows builds. The release also includes free-threaded CPython builds for supported Python versions and platforms.

Because pglast has a native extension and bundles PostgreSQL-derived parser functionality, distribution compatibility matters more than it would for a pure-Python SQL utility.

Source builds involve the project's native build infrastructure.

The project generates substantial portions of its AST definitions, enums, keyword information, documentation, and extension source from PostgreSQL and related inputs. This is important for understanding why upgrading parser generations can change much of the generated API surface.

### 13.5 Licensing

pglast is distributed under GPL-3.0-or-later.

This is a significant consideration for redistribution and integration into proprietary software, particularly when bundled or linked into a distributed product.

The underlying `libpg_query` ecosystem and alternative bindings can have different license conditions. A shared parser lineage does not imply identical licensing.

Source:

[https://pypi.org/project/pglast/8.7/](https://pypi.org/project/pglast/8.7/?utm_source=chatgpt.com)

## 14. Key architectural distinctions

The library's capabilities can be viewed through five distinct roles.

| Role                                   | pglast's contribution                                           | Where the responsibility ends                        |
| -------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------- |
| PostgreSQL grammar engine              | Faithful parsing through `libpg_query`                          | Semantic database validation                         |
| Structural intermediate representation | Typed AST objects and serialization                             | Catalog-resolved relational models                   |
| Transformation framework               | Visitors and mutable tree operations                            | Proof that rewrites preserve intended behavior       |
| SQL output engine                      | Regeneration, formatting, customized printers                   | Exact preservation of original source text           |
| SQL inspection utility                 | Tokens, statement splitting, fingerprinting, relation discovery | Full lineage, workload execution, and query planning |

Several less obvious capabilities deserve particular emphasis.

First, pglast's visitor system is a structural transformation framework, not merely an iterator. Ancestor tracking, insertion, deletion, replacement, and deferred updates can replace a substantial amount of bespoke tree-management code.

Second, pglast contains two materially different SQL deparsing pathways. Python-based AST printing and native Protobuf deparsing provide different integration possibilities and customization boundaries.

Third, pglast supports useful syntax-aware analysis without a database connection. This can substantially simplify static SQL inspection, while still leaving catalog resolution and semantic correctness to other systems.

Fourth, PostgreSQL-specific grammar fidelity is both its principal strength and its central constraint. The closer the problem is to PostgreSQL-native syntax, the more valuable that fidelity becomes. The greater the requirement for portable relational semantics across SQL dialects, the more likely a generalized SQL representation will be appropriate.

Finally, pglast should be understood as infrastructure for creating PostgreSQL-aware tooling, not a comprehensive SQL semantic-analysis framework in its own right. The most valuable architectural opportunities often come from using its parser, AST, visitors, and printers as common underlying mechanisms while keeping semantic responsibilities clearly separated.

## 15. Primary-source reference map

The following source set provides direct access to the major capabilities covered in this overview. All URLs are supplied as plain text for reuse in technical documentation.

| Topic                                            | Primary source                                                                                                                                  |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Project and source                               | [https://github.com/lelit/pglast](https://github.com/lelit/pglast?utm_source=chatgpt.com)                                                       |
| Version-specific documentation                   | [https://pglast.readthedocs.io/en/v8/](https://pglast.readthedocs.io/en/v8/?utm_source=chatgpt.com)                                             |
| Release notes and compatibility                  | [https://pglast.readthedocs.io/en/v8/changes.html](https://pglast.readthedocs.io/en/v8/changes.html?utm_source=chatgpt.com)                     |
| Parser APIs, fingerprinting, scanning, splitting | [https://pglast.readthedocs.io/en/v8/parser.html](https://pglast.readthedocs.io/en/v8/parser.html?utm_source=chatgpt.com)                       |
| Generated AST classes and node methods           | [https://pglast.readthedocs.io/en/v8/ast.html](https://pglast.readthedocs.io/en/v8/ast.html?utm_source=chatgpt.com)                             |
| Visitors and transformations                     | [https://pglast.readthedocs.io/en/v8/visitors.html](https://pglast.readthedocs.io/en/v8/visitors.html?utm_source=chatgpt.com)                   |
| SQL stream generation                            | [https://pglast.readthedocs.io/en/v8/stream.html](https://pglast.readthedocs.io/en/v8/stream.html?utm_source=chatgpt.com)                       |
| Grammar and expression precedence                | [https://pglast.readthedocs.io/en/v8/precedence.html](https://pglast.readthedocs.io/en/v8/precedence.html?utm_source=chatgpt.com)               |
| Printer registration and customization           | [https://pglast.readthedocs.io/en/v8/printers.html](https://pglast.readthedocs.io/en/v8/printers.html?utm_source=chatgpt.com)                   |
| Special PostgreSQL function syntax               | [https://pglast.readthedocs.io/en/v8/sfuncs.html](https://pglast.readthedocs.io/en/v8/sfuncs.html?utm_source=chatgpt.com)                       |
| PostgreSQL enums                                 | [https://pglast.readthedocs.io/en/v8/enums.html](https://pglast.readthedocs.io/en/v8/enums.html?utm_source=chatgpt.com)                         |
| SQL keyword classes                              | [https://pglast.readthedocs.io/en/v8/keywords.html](https://pglast.readthedocs.io/en/v8/keywords.html?utm_source=chatgpt.com)                   |
| Examples and `pgpp` CLI                          | [https://pglast.readthedocs.io/en/v8/usage.html](https://pglast.readthedocs.io/en/v8/usage.html?utm_source=chatgpt.com)                         |
| Upstream visitor implementation                  | [https://github.com/lelit/pglast/blob/v8/pglast/visitors.py](https://github.com/lelit/pglast/blob/v8/pglast/visitors.py?utm_source=chatgpt.com) |
| Native parser wrapper implementation             | [https://github.com/lelit/pglast/blob/v8/pglast/parser.pyx](https://github.com/lelit/pglast/blob/v8/pglast/parser.pyx?utm_source=chatgpt.com)   |
| Upstream parser engine                           | [https://github.com/pganalyze/libpg_query](https://github.com/pganalyze/libpg_query?utm_source=chatgpt.com)                                     |
| Related Rust `pg_query` crate                    | [https://docs.rs/pg_query/latest/pg_query/](https://docs.rs/pg_query/latest/pg_query/?utm_source=chatgpt.com)                                   |
| Alternative multi-dialect SQL engine             | [https://github.com/tobymao/sqlglot](https://github.com/tobymao/sqlglot?utm_source=chatgpt.com)                                                 |

Overall assessment: pglast's distinctive value is its combination of the real PostgreSQL parser, a generated and mutable Python AST, capable visitor-driven transformations, and extensible SQL serialization. For PostgreSQL-specific structural tooling, these facilities can eliminate the need to implement large amounts of SQL parsing, tree traversal, and SQL regeneration machinery. Its principal limitations emerge when requirements cross from syntax into database-resolved semantics, cross-dialect modeling, exact source preservation, or comprehensive PL/pgSQL manipulation.

# Addendum — pglast 8.7: Advanced Capabilities, Implementation Semantics, and API Corrections

Research date: November 1, 2026\
Target: pglast 8.7, PostgreSQL 18 grammar\
Companion document: pglast 8.7 — Comprehensive Python Library Overview

This addendum supplements the original reference with additional functionality, lower-level implementation mechanisms, consequential correctness distinctions, and version-specific corrections. It focuses on capabilities and behaviors not already explained in the main document.

## 1. Advanced fingerprinting semantics and query identity

### 1.1 Relation-name canonicalization and fingerprint controls

The `libpg_query` fingerprinting algorithm performs more extensive structural normalization than replacing literal constants. In particular, relation identifiers are subject to rules that can deliberately group syntactically different relations.

For the PostgreSQL 18 parser generation used by pglast 8.7, default fingerprint behavior includes:

| Structural feature                                       | Default treatment                                               |
| -------------------------------------------------------- | --------------------------------------------------------------- |
| Literal values                                           | Normalized so different values can produce the same fingerprint |
| Schema qualifiers in `SELECT`/DML relation references    | Ignored                                                         |
| Relation aliases                                         | Used in place of the relation name when an alias is present     |
| Runs of two or more consecutive digits in relation names | Ignored by default                                              |
| PostgreSQL source positions                              | Excluded from query identity                                    |

The digit-normalization rule is particularly relevant to partitioned or time-suffixed relations. For example, queries differing only in a table suffix such as `events_202601` versus `events_202602` may receive the same fingerprint. This is intentional workload grouping, not a guarantee that the two queries access equivalent data.

The native engine exposes an options bitmask that modifies its fingerprint calculation:

| Native `libpg_query` option                    | Effect                                                                                 |
| ---------------------------------------------- | -------------------------------------------------------------------------------------- |
| `PG_QUERY_FINGERPRINT_RANGEVAR_IGNORE_ALIASES` | Use relation names rather than aliases                                                 |
| `PG_QUERY_FINGERPRINT_RANGEVAR_INCLUDE_SCHEMA` | Include schema names in `SELECT`/DML relation identity                                 |
| `PG_QUERY_FINGERPRINT_RANGEVAR_PG17_COMPAT`    | Combine the preceding options to reproduce PostgreSQL 17-style relation identification |
| `PG_QUERY_FINGERPRINT_FULL_RELNAME`            | Preserve digit sequences in relation names                                             |

These options belong to the underlying C library. pglast 8.7 exposes `fingerprint(query)` with only the query argument, so they cannot be selected through its existing public Python wrapper.

Where an application needs relation-sensitive identities, including partition identity, the default pglast fingerprint is insufficient as a unique structural key. Supplementary relation information or a differently configured native fingerprinting interface is required.

The underlying algorithm also uses selective field normalization and a recursion-depth cutoff rather than hashing a complete canonical serialization of every AST attribute. Consequently, its digest represents the algorithm's equivalence classes, not exhaustive syntactic identity.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+3



`https://github.com/pganalyze/libpg_query/wiki/Fingerprinting`

`https://github.com/pganalyze/libpg_query/releases/tag/18.1.0`

`https://github.com/lelit/pglast/blob/v8.7/pglast/parser.pyx`

### 1.2 Fingerprinting multi-statement scripts

The fingerprint API accepts SQL containing multiple statements. The underlying algorithm incorporates all statements in the input parse tree into a single digest, rather than returning a collection of per-statement fingerprints.

These operations are therefore different:

```
from pglast import fingerprint, splitscript = """SELECT * FROM orders WHERE id = 100;UPDATE orders SET status = 'paid' WHERE id = 100;"""# One fingerprint representing the entire script.script_identity = fingerprint(script)# Independent fingerprints for the individual statements.statement_identities = tuple(    fingerprint(statement)    for statement in split(script))
```

This distinction matters for workload aggregation, statement registries, and query-shape inventories. A fingerprint for an entire script identifies a compound input shape; it cannot directly substitute for statement-level identities in execution traces or PostgreSQL workload statistics.

Although the underlying fingerprint algorithm is designed to group query structures similarly to PostgreSQL query identifiers, it operates on the raw parse representation. PostgreSQL's server-side query identification can incorporate analyzed information, including resolved object identities. Equality between pglast fingerprints and `pg_stat_statements` identifiers should not be assumed.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



`https://github.com/pganalyze/libpg_query/wiki/Fingerprinting`

## 2. Lower-level AST traversal and mutation machinery

### 2.1 `Visitor.iterate()` is an action-driven generator

The high-level `Visitor.__call__()` interface invokes visitor methods and handles the traversal actions they return. Its underlying `Visitor.iterate()` method exposes a lower-level generator protocol.

The generator yields `(ancestors, node)` pairs and expects the caller to send back an action describing how to handle each visited node.

The distinction is consequential:

- `Continue` traverses the visited node's descendants.
- `Skip` avoids its descendants.
- `Delete`, a replacement node, or an `(Add, ...)` instruction schedules a structural modification.
- The high-level `Visitor.__call__()` converts a callback result of `None` into `Continue`.
- The lower-level `iterate()` generator does not perform that conversion.

As a result, directly consuming `Visitor.iterate()` with an ordinary Python `for` loop is not equivalent to a normal read-only AST walk. An ordinary loop resumes the generator with `None`, which the implementation may interpret as a replacement rather than permission to descend.

For a custom read-only traversal, the generator must be driven explicitly:

```
from pglast import parse_sqlfrom pglast.visitors import Visitor, Continuetree = parse_sql("SELECT id FROM orders")walker = Visitor().iterate(tree)try:    ancestors, node = next(walker)    while True:        # Inspect the current node and its ancestry.        print(type(node).__name__, ancestors)        # Explicitly request traversal into descendants.        ancestors, node = walker.send(Continue)except StopIteration:    pass
```

This illustrates the generator protocol, not an alternative generally preferable to ordinary `Visitor` subclasses.

For most analysis and rewriting, `Visitor.__call__()` is the more appropriate abstraction because it owns the dispatch and action protocol. `iterate()` is valuable when an alternative traversal controller needs explicit control over the action sent after each visit.

An additional mutation distinction: pending changes are applied after traversal finishes. A newly inserted subtree is not visited automatically in that pass, and ancestry paths collected before structural changes should not be assumed to remain valid afterward.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation



`https://github.com/lelit/pglast/blob/v8.7/pglast/visitors.py`

### 2.2 Direct structural edits through `Ancestor.update()` and `Ancestor.apply()`

`Ancestor` exposes two lower-level mutation operations:

| Operation                    | Behavior                                                    |
| ---------------------------- | ----------------------------------------------------------- |
| `Ancestor.update(new_value)` | Records a pending update to the tracked location            |
| `Ancestor.apply()`           | Applies the pending change to the containing tree structure |

These methods handle two structurally different cases.

AST attribute replacement: When a child is held in a writable AST attribute, the update can ultimately assign the replacement to that attribute.

Tuple element replacement: When a child is held inside an immutable tuple, the implementation creates a temporary mutable representation, applies the requested insertions, deletions, or replacements, and reconstructs the tuple. This logic also handles nested tuples, which occur in some PostgreSQL node structures.

`Add` is specifically a sequence-editing action. It cannot be applied to an arbitrary scalar AST attribute; the implementation raises `ValueError` when insertion is requested outside a sequence position.

These primitives explain how pglast supports visitor-mediated structural modification without requiring each transformation to implement its own immutable-container rebuilding algorithm.

They also provide a lower-level extension point for specialized AST editors that need precise control over individual tree locations.

The methods are mutable-tree operations, not persistent-tree or transactional editing primitives. There is no general undo mechanism, semantic validation, or automatic update of previously captured ancestry paths.

Source: `https://github.com/lelit/pglast/blob/v8.7/pglast/visitors.py`

### 2.3 Reflection over generated AST classes

Each `ast.Node` supports iteration over its declared attribute names. This is distinct from walking descendants or serializing the node.

For example:

```
from pglast import parse_sqlstmt = parse_sql("SELECT id FROM orders")[0].stmtfields = tuple(stmt)values = {    field: getattr(stmt, field)    for field in stmt}
```

This exposes the node's field structure without a class-specific field inventory.

It is useful for:

- Generic AST inspectors and schema browsers.
- Structured diagnostics across heterogeneous PostgreSQL node types.
- AST difference and comparison tooling.
- Discovering available attributes during programmatic SQL transformation.

The resulting fields are the generated PostgreSQL parser-model attributes. They are not a stable, dialect-independent SQL schema, and the existence of an attribute does not establish that it will have a meaningful non-null value in every context.

The generated classes also implement validated assignment, so generic reflection can be combined with their existing field-type validation without constructing a separate Python object model.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation



`https://pglast.readthedocs.io/en/v8/usage.html`

### 2.4 Explicit ancestry population and membership queries

`pglast.visitors.populate_ancestors(tree)` populates the `ancestors` attribute of AST nodes without requiring an application to implement a dedicated ancestry-tracking pass.

Ancestry tracking provides additional mechanisms beyond `find_nearest()`:

- `NodeClass in ancestors` tests whether an ancestor of that class exists.
- `ancestors @ root` resolves a recorded structural path against a tree.
- `abs(ancestors)` locates the nearest ancestor referring to an AST node instead of an intermediate tuple.
- `ancestors[n]` retrieves nodes at successive levels above the visited node.

These mechanisms support context-sensitive operations involving expression placement, nested subqueries, parent statement types, and tuple-containing AST fields.

The ancestry information is also a dependency of the SQL printing subsystem. `RawStream.__call__()` populates it automatically before invoking node printers. Code that bypasses this entry point and invokes low-level printing functions directly must account for that requirement.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation+1



`https://pglast.readthedocs.io/en/v8/visitors.html`

## 3. SQL printer internals and reusable generation primitives

### 3.1 Identifier quoting and operator-name handling

The serialization subsystem exposes utilities that can eliminate repetitive PostgreSQL-specific escaping and formatting logic in custom printers.

`pglast.stream.maybe_double_quote_name(name)` examines an individual identifier and applies double quoting when required by its syntax or PostgreSQL keyword classification. Embedded double quotes are escaped according to PostgreSQL identifier rules.

The stream machinery offers higher-level interfaces:

| Interface                                                    | Specific capability                                                                              |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| `maybe_double_quote_name(name)`                              | Quote an individual PostgreSQL identifier when necessary                                         |
| `RawStream.print_name(nodes, sep='.')`                       | Render one or more identifier components with the appropriate separator                          |
| `RawStream.print_symbol(nodes, sep='.')`                     | Render symbols and qualified operator names without incorrectly quoting the operator itself      |
| `RawStream.print_node(node, is_name=False, is_symbol=False)` | Dispatch an individual AST node with identifier/symbol context                                   |
| `RawStream.print_list(...)`                                  | Render AST sequences with separators, indentation, optional parentheses, and identifier handling |
| `RawStream.print_lists(...)`                                 | Render nested AST sequences, including independently delimited sublists                          |

The distinction between identifiers and operator symbols is particularly important in PostgreSQL.

For example, qualified operators use syntax such as `OPERATOR(schema.operator)`. The schema component follows identifier-quoting rules, but the operator's symbolic component must be preserved as an operator.

The standard printers already handle these conventions. Custom serializers can reuse the same mechanisms rather than duplicating PostgreSQL token and quoting rules.

Boundary: Identifier quoting is not the same as arbitrary SQL value escaping, parameter binding, or catalog resolution. `maybe_double_quote_name()` also operates on an individual identifier component; qualified names require component-aware handling.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation



`https://github.com/lelit/pglast/blob/v8.7/pglast/stream.py`

### 3.2 Expression contexts are distinct from operator precedence

The 8.6 precedence improvements introduce machinery that handles not only conventional precedence and associativity but also the distinct expression productions in PostgreSQL's grammar.

The important distinction is between:

- `a_expr`: the broadly permitted expression grammar.
- `b_expr`: a restricted grammar used in particular syntactic positions.
- `c_expr`: a more restricted grammar covering atomic expression forms.

The stream implementation provides complementary methods:

| API                                                | Responsibility                                                                                              |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `print_operand(node, parent_prec, side, ctx=None)` | Decide whether an operand requires parentheses based on precedence, position, and grammar context           |
| `print_b_expr(node)`                               | Render an expression in a position requiring `b_expr`                                                       |
| `print_c_expr(node)`                               | Render an expression in a position requiring `c_expr`                                                       |
| `push_expr_context(ctx)`                           | Temporarily establish the grammar context for nested printing                                               |
| `expression(need_parens)`                          | Emit a parenthesized region when requested; does not independently decide whether parentheses are necessary |

This separation is important because a syntactically valid expression cannot necessarily be emitted without parentheses in every PostgreSQL grammar position, even if ordinary arithmetic precedence would otherwise permit it.

For example, the `BETWEEN` printer must treat its lower and upper bounds according to different grammar constraints. The native implementation uses `print_b_expr()` for the lower bound and `print_operand()` for the upper bound.

The architecture therefore provides two interacting forms of correctness:

1. Precedence correctness: preserving the grouping and associativity of operands.
2. Grammar-position correctness: ensuring that the emitted expression is permitted where it appears.

Both are necessary for reliable deparsing of transformed SQL trees. Custom printers that bypass these facilities can produce SQL whose parse structure differs from the intended AST.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation+1



`https://pglast.readthedocs.io/en/v8/stream.html`

`https://github.com/lelit/pglast/blob/v8.7/pglast/printers/dml.py`

### 3.3 Enum-dependent printing through `IntEnumPrinter`

The `pglast.printers` implementation includes `IntEnumPrinter`, a reusable dispatch helper for AST attributes whose enum values select different SQL output forms.

An `IntEnumPrinter` subclass declares its relevant `enum` type and implements methods corresponding to the enum member names.

When invoked, the dispatcher:

- Resolves enum instances or supported integer-backed representations to enum member names.
- Selects the implementation associated with the resolved member.
- Raises an appropriate exception when the enum value is invalid or its printer implementation is absent.

For example, the upstream `AExprKindPrinter` uses this mechanism to handle the different forms represented by `A_Expr_Kind`, including ordinary operators, `IN`, `BETWEEN`, and related expression categories.

This avoids embedding a large conditional dispatch tree inside every node printer. The resulting structure separates node-type dispatch from enum-dependent syntax selection.

`IntEnumPrinter` is a source-level extension helper rather than a prominently documented, independently versioned public contract. Its implementation should be inspected when relying on it directly.

Source: `https://github.com/lelit/pglast/blob/v8.7/pglast/printers/__init__.py`

### 3.4 Output streams maintain mutable generation state

`OutputStream` extends `io.StringIO` with separator management. `RawStream` adds SQL-specific state, while `IndentedStream` adds indentation and column-position tracking.

These objects are not stateless formatting functions.

Relevant state includes pending separators, emitted content, current expression context, output-column position, indentation, and potentially pending comments.

An important implication is that `RawStream.__call__()` writes into the stream instance and returns its accumulated contents. It does not automatically recreate a fresh output buffer on every invocation.

Therefore, independently generated SQL outputs should not assume that repeated calls on the same stream instance start from an empty buffer. A fresh stream instance provides clearer isolation for separate serialization operations.

For custom printers, the stream's existing state-management methods are useful because they centralize whitespace and indentation conventions. They also create an obligation to preserve those conventions across nested printing operations.

Source: `https://github.com/lelit/pglast/blob/v8.7/pglast/stream.py`

## 4. Comment representations, source spans, and diagnostics

### 4.1 Two distinct comment metadata models

pglast exposes two different representations of SQL comments, serving different purposes.

| Property             | `pglast.parser.comments()`                          | Higher-level `pglast.Comment`                                  |
| -------------------- | --------------------------------------------------- | -------------------------------------------------------------- |
| Primary purpose      | Native deparser-oriented comment metadata           | Comment preservation during Python AST printing                |
| Position information | `match_location`                                    | `location`                                                     |
| Formatting context   | `newlines_before_comment`, `newlines_after_comment` | `at_start_of_line`, `continue_previous`                        |
| Comment content      | `str`                                               | `text`                                                         |
| Extraction mechanism | Native `libpg_query` comment extraction             | Token scanning through pglast's internal `_extract_comments()` |

The most consequential distinction concerns the meaning of `match_location`.

For the native comment interface, `match_location` refers to an anchor associated with the end of the preceding non-comment token. It is not necessarily the original character position where the comment begins.

For example, the documented call:

```
from pglast.parser import commentsresult = comments(    "exists (select /* no columns */ from foo)")
```

returns comment metadata anchored at the preceding SQL token rather than treating the opening delimiter as the native match position.

By contrast, the higher-level comment representation carries source-oriented information obtained through the scanner, including whether the comment begins a line and whether it continues a run of consecutive comments.

These representations should not be interchanged without converting their positional and formatting semantics.

The upstream documentation also describes `parser.comments()` as primarily internal and incidentally exposed. Its existence does not establish a strong compatibility contract for third-party tooling.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation+1



`https://pglast.readthedocs.io/en/v8/parser.html`

`https://github.com/lelit/pglast/blob/v8.7/pglast/__init__.py`

### 4.2 Comment support differs between deparsing paths

The Python `RawStream`/`IndentedStream` path can receive separately extracted comments and attempt to place them during SQL regeneration.

The native `parser.deparse_protobuf()` interface in 8.7 does not expose equivalent user-supplied comment metadata as part of its Python signature.

Its options cover SQL presentation parameters, including formatting, indentation, line length, newline behavior, and comma position. The tagged Cython implementation initializes the native comment pointer and comment count to empty values.

Consequently, the presence of native comment extraction in the underlying library does not imply that pglast 8.7 exposes a complete comment-aware Protobuf deparsing interface.

For exact source preservation, neither AST-based regeneration path constitutes a lossless document editor. Source-preserving transformations need to account separately for tokens, original text, comments, and structural changes.

Source: `https://github.com/lelit/pglast/blob/v8.7/pglast/parser.pyx`

### 4.3 Additional source-boundary metadata in PostgreSQL 18 AST nodes

Some generated AST classes carry more detailed positional metadata than a single `location` field.

Examples include:

| AST class     | Additional positional attributes     |
| ------------- | ------------------------------------ |
| `A_ArrayExpr` | `list_start`, `list_end`             |
| `ArrayExpr`   | `list_start`, `list_end`             |
| `A_Expr`      | `rexpr_list_start`, `rexpr_list_end` |
| `RawStmt`     | `stmt_location`, `stmt_len`          |

These attributes can identify boundaries of selected grammatical regions, including array-element lists and certain right-hand expression lists.

They are useful when a transformation needs a source span associated with a particular syntactic construct, rather than only the position of the construct's first token.

However, PostgreSQL does not provide complete start/end ranges for every AST node. Some location attributes can contain sentinel values indicating that a location is unknown.

Another important distinction concerns equality. Generated node classes extend the attributes ignored during structural equality to include positional fields such as `list_start` and `list_end`.

Therefore, AST structural equality can remain true even when positional metadata differs. That is useful for parse-print-reparse comparisons, but it means AST equality cannot validate the preservation of exact source ranges.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation



`https://github.com/lelit/pglast/blob/v8.7/pglast/ast.py`

### 4.4 Unicode coordinates and structured parser errors

There are several related but nonidentical source-coordinate interfaces.

| Interface                      | Relevant coordinate behavior                                                        |
| ------------------------------ | ----------------------------------------------------------------------------------- |
| `parser.parse_sql_json()`      | Preserves native PostgreSQL byte-offset conventions                                 |
| `parse_sql()`                  | Constructs Python AST objects using the library's displacement-conversion machinery |
| `parser.scan()`                | Converts token boundaries for Python string indexing                                |
| `split(..., only_slices=True)` | Returns slices adapted for Python Unicode strings                                   |
| `ParseError`                   | Exposes a parser error position through its exception arguments                     |
| `DeparseError`                 | Exposes a native deparser error position through a separate path                    |

For `ParseError`, the positional value is available as the second exception argument, `error.args[1]`, rather than as a dedicated `location` attribute.

The tagged parser converts native UTF-8 offsets into Python string indices when constructing these errors. The result may be `None` when the reported position is beyond the final character, as can happen for end-of-input errors.

The `deparse_protobuf()` error path instead passes the native deparser cursor position to `DeparseError` without the same explicit Unicode displacement conversion.

These differences matter to diagnostic systems that use locations for source highlighting, targeted replacement, or structured editor feedback.

A common internal position representation is useful, but conversion must depend on the originating API. Assuming that all pglast coordinates have identical units or end-position conventions can introduce errors when multibyte characters occur before the reported location.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation+1



`https://github.com/lelit/pglast/blob/v8.7/pglast/parser.pyx`

## 5. Procedural-language inspection through the CLI

### 5.1 `pgpp --plpgsql`

The `pgpp` command-line utility supports PL/pgSQL inspection through the `-p` or `--plpgsql` option.

For example, given a SQL file containing a PostgreSQL PL/pgSQL function definition:

```
pgpp --plpgsql functions.sql
```

This option implies parse-tree output.

Rather than producing formatted SQL, the utility invokes the procedural parser and emits its nested Python representation as indented JSON, with sorted object keys.

This is a useful standalone interface for inspecting procedural blocks, declarations, and statements without building a Python wrapper.

However, the output is not equivalent to the ordinary typed SQL AST. The procedural representation remains a hierarchy of dictionaries, lists, and scalar values, without the same generated typed-node construction and rewriting capabilities.

The CLI therefore provides procedural inspection, not a complete PL/pgSQL source transformation pipeline.

Source: `https://github.com/lelit/pglast/blob/v8.7/pglast/__main__.py`

## 6. Version boundaries and corrections to the original guide

### 6.1 `pglast.parser.normalize()` is not released in 8.7

The evolving v8 documentation includes a `parser.normalize(query, utility_only=False)` interface. It delegates to `libpg_query` functionality that replaces SQL constants with parameter references, supporting query-text normalization similar to PostgreSQL workload reporting.

However, the upstream changelog places this API under 8.8 (unreleased) as of November 1, 2026.

It is therefore not an available pglast 8.7 interface.

Three different operations must remain distinct:

| Operation                            | Meaning                                                                | Availability in 8.7 |
| ------------------------------------ | ---------------------------------------------------------------------- | ------------------- |
| `pgpp --normalize`                   | Compact SQL serialization using `RawStream`                            | Available           |
| `pglast.printers.sfuncs.normalize()` | Specialized printer for PostgreSQL's SQL `NORMALIZE()` function syntax | Available           |
| `pglast.parser.normalize()`          | Native query-constant normalization through `libpg_query`              | Not yet released    |

The native normalization interface also includes `utility_only`, which is intended to restrict normalization to utility statements, such as certain administrative SQL commands.

That additional capability should not be retroactively attributed to 8.7 simply because it appears in the live documentation.

The unreleased 8.8 changelog also contains source-distribution and special-function deparsing fixes. Those fixes should similarly be distinguished from functionality guaranteed by the published 8.7 release.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation+2



`https://pglast.readthedocs.io/en/v8/changes.html`

`https://pglast.readthedocs.io/en/v8/parser.html`

### 6.2 AST serialization does not accept `enum_name`

The original guide's §3.3 lists `enum_name` among the controls accepted by `ast.Node` serialization.

The tagged 8.7 implementation has this signature:

```
Node.__call__(    self,    depth=None,    ellipsis=Omissis,    skip_none=False,)
```

There is no `enum_name` argument.

The generated documentation still contains a description of that parameter, but the actual method does not implement it. Supplying `enum_name=` raises `TypeError`.

Enums are serialized using structures that include `#`, `name`, and `value` fields, rather than a caller-selectable enum-name-only mode.

Correction to §3.3: Remove `enum_name` from the supported serialization options.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation



`https://github.com/lelit/pglast/blob/v8.7/pglast/ast.py`

### 6.3 Parser version reporting returns two components

The live parser reference describes `get_postgresql_version()` as returning a tuple containing major, minor, and patch components.

The tagged 8.7 implementation instead returns:

```
(major, minor)
```

This is computed from the compiled PostgreSQL `PG_VERSION_NUM`.

Code consuming this API should use the two-element result provided by the actual implementation rather than assuming a three-element tuple based on the generated documentation.

Source: `https://github.com/lelit/pglast/blob/v8.7/pglast/parser.pyx`

### 6.4 Preserve the published-release boundary

Some pglast documentation and Git branches are updated between releases. Version-specific reference material should therefore distinguish:

- Published package behavior, verified against `v8.7`.
- Changes present in the moving `v8` development branch.
- Features and fixes explicitly assigned to an unreleased version.
- Improvements released or backported in other major-version branches.

In particular, a newer fix appearing in the 7.x release history does not establish that it was already included in the earlier 8.7 build.

For correctness-sensitive interfaces—especially source offsets, custom printer behavior, serialization, and generated AST classes—the version tag is more authoritative than mutable documentation when they disagree.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pglast.readthedocs.io\&sz=32)

pglast v8.7 documentation



`https://github.com/lelit/pglast/blob/v8.7/CHANGES.rst`

### 6.5 Editorial corrections to the existing examples

Several code examples in the original guide have lost their line breaks or statement separation, producing invalid Python source.

This affects examples in the native AST parsing, serialization, visitors, AST rewriting, scanning, splitting, fingerprinting, and deparsing sections.

The examples should be restored to normal executable Python syntax, with separate import statements and correctly indented code blocks. Their underlying instructional content does not require substantive expansion.

The original reference map should also preferentially use immutable tagged source URLs instead of moving branch links for claims about pglast 8.7. Tracking query parameters in existing documentation URLs can be removed without changing their destinations.

## 7. Additional primary-source map

The following references supplement the original document's source map.

| Additional subject                                                 | Direct source                                                           |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| Exact 8.7 AST implementation and serialization signature           | `https://github.com/lelit/pglast/blob/v8.7/pglast/ast.py`               |
| Visitor generator protocol, ancestry, and deferred editing         | `https://github.com/lelit/pglast/blob/v8.7/pglast/visitors.py`          |
| OutputStream state, quoting, nested lists, and expression printing | `https://github.com/lelit/pglast/blob/v8.7/pglast/stream.py`            |
| `IntEnumPrinter` and printer dispatch implementation               | `https://github.com/lelit/pglast/blob/v8.7/pglast/printers/__init__.py` |
| Expression-context printing implementations                        | `https://github.com/lelit/pglast/blob/v8.7/pglast/printers/dml.py`      |
| Comment extraction and native error handling                       | `https://github.com/lelit/pglast/blob/v8.7/pglast/parser.pyx`           |
| High-level comment extraction and formatting safety behavior       | `https://github.com/lelit/pglast/blob/v8.7/pglast/__init__.py`          |
| `pgpp` procedural inspection and normalization options             | `https://github.com/lelit/pglast/blob/v8.7/pglast/__main__.py`          |
| Detailed fingerprinting specification                              | `https://github.com/pganalyze/libpg_query/wiki/Fingerprinting`          |
| Native PostgreSQL 18 fingerprint option support                    | `https://github.com/pganalyze/libpg_query/releases/tag/18.1.0`          |
| Live release-status and compatibility history                      | `https://pglast.readthedocs.io/en/v8/changes.html`                      |

The central architectural addition is that pglast's lower-level infrastructure offers more than typed parsing and visitor dispatch. It exposes reusable mechanisms for immutable-container editing, context-aware SQL emission, identifier handling, source-coordinate adaptation, and configurable traversal control. Understanding these mechanisms helps distinguish work that can be delegated to pglast from additional machinery required for exact source preservation, semantic analysis, and stable query identity.