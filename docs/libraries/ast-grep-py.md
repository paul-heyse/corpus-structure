# ast-grep-py — Comprehensive Python Library Overview

Target version: 0.51.0 · Research date: October 28, 2026 · Python / Rust / Tree-sitter

## 1. Purpose and architectural positioning

`ast-grep-py` is a native Python binding to the Rust-based ast-grep structural code matching engine. It provides programmatic access to Tree-sitter syntax trees, structural pattern matching, declarative AST rules, syntax-aware traversal, metavariable capture, and source-code transformation.

Unlike Python's standard `ast` module, its functionality extends to multiple programming languages. Unlike regex-based search, it operates on parsed syntax structures. Unlike standalone Tree-sitter bindings, it supplies a higher-level matching and rule engine rather than requiring callers to construct all structural searches manually.

The current stable release is 0.51.0, published October 15, 2026. It is distributed as `ast-grep-py`, imported as `ast_grep_py`, and implemented using PyO3. Its PyPI metadata specifies Python 3.8 or newer, with platform-specific native wheels including CPython 3.14.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



Primary sources:

- Python API: [https://ast-grep.github.io/guide/api-usage/py-api.html](https://ast-grep.github.io/guide/api-usage/py-api.html?utm_source=chatgpt.com)
- API reference: [https://ast-grep.github.io/reference/api.html](https://ast-grep.github.io/reference/api.html?utm_source=chatgpt.com)
- Python binding source: [https://github.com/ast-grep/ast-grep/tree/main/crates/pyo3](https://github.com/ast-grep/ast-grep/tree/main/crates/pyo3?utm_source=chatgpt.com)
- Package: [https://pypi.org/project/ast-grep-py/](https://pypi.org/project/ast-grep-py/?utm_source=chatgpt.com)
- Release history: [https://github.com/ast-grep/ast-grep/blob/main/CHANGELOG.md](https://github.com/ast-grep/ast-grep/blob/main/CHANGELOG.md?utm_source=chatgpt.com)

### 1.1 Capability map

| Functional area       | Principal capabilities                                                                                                  |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Structural parsing    | Multilanguage Tree-sitter parsing, concrete and named syntax nodes, source ranges                                       |
| Pattern matching      | Code-shaped patterns, metavariables, repeated captures, context-sensitive patterns                                      |
| Declarative analysis  | Atomic, relational, composite, and reusable rules; captures and constraints                                             |
| Structural navigation | Parent/child, named fields, ancestors, siblings, subtree searches                                                       |
| Source transformation | Match-dependent replacement text, text edits, batched source rewriting                                                  |
| Python integration    | Programmatic search orchestration, custom predicates, extraction and aggregation, integration with other analysis tools |
| Extensibility         | Custom language parsers, configurable matching, integration with Python-hosted processing                               |
| Automation            | Structural indexing, codemods, compatibility checks, source analysis, automated diagnostics                             |

### 1.2 The essential distinction: Python binding versus ast-grep CLI

Both interfaces reuse the same underlying ast-grep concepts, but their orchestration responsibilities differ.

| Dimension                 | `ast-grep-py`                                 | `ast-grep` CLI                                                  |
| ------------------------- | --------------------------------------------- | --------------------------------------------------------------- |
| Primary role              | Embedded structural-analysis library          | Standalone search, lint, and rewrite tool                       |
| Processing model          | Python-controlled parsing and node operations | CLI-controlled files, rules, and execution                      |
| Input                     | Source strings supplied by Python             | Files, directories, and input streams                           |
| Matching                  | Structural patterns and rules                 | Structural patterns and rules                                   |
| Custom analysis           | Arbitrary Python postprocessing               | Declarative rules and external orchestration                    |
| Transformations           | Programmatically generated edits              | Declarative fixes, rewrites, and interactive application        |
| Repository-scale features | Caller orchestrates discovery and scheduling  | Built-in discovery, parallel scanning, filtering, and reporting |
| Diagnostics               | Caller defines output models and reporting    | Built-in diagnostics and output formats                         |
| Rule testing              | External Python tests                         | Dedicated `ast-grep test` infrastructure                        |

The Python package is not a Python wrapper that repeatedly invokes the CLI executable. It connects directly to native Rust functionality through PyO3. Consequently, it can avoid subprocess invocation and CLI-output serialization when structural analysis is embedded in Python, although Python/Rust boundary crossings still have costs.

The two interfaces are complementary rather than complete substitutes. In particular, CLI-native project scanning, lint execution, configuration management, and reporting should not be assumed to be exposed by the Python API.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+2



## 2. Parsing, syntax trees, and source representation

### 2.1 `SgRoot`: parsing source into a reusable tree

`SgRoot(source: str, language: str)` parses an in-memory source string into a Tree-sitter-backed syntax tree. `root()` returns its root `SgNode`; `filename()` returns `"anonymous"` for these string-created roots.

The binding uses the same built-in language definitions as ast-grep's Rust language layer. These include Python, Rust, JavaScript, TypeScript, TSX, C, C++, Go, Java, HTML, CSS, JSON, YAML, Bash, and numerous others. Native custom grammars extend this set, as discussed in §7.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+3



Structural fidelity: Tree-sitter creates a concrete syntax tree rather than Python's abstract, language-specific `ast.AST` representation. This distinction matters because the tree preserves syntax nodes for punctuation, operators, and other language-specific constructs.

| Concept                    | Implication                                                                                                           |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Named nodes                | Usually meaningful grammar constructs, such as identifiers, calls, expressions, and declarations                      |
| Unnamed nodes              | Grammar tokens such as punctuation and operators; useful for precise syntax matching                                  |
| Source text                | `SgNode.text()` returns the original text corresponding to a node                                                     |
| Node kind                  | `SgNode.kind()` returns its Tree-sitter grammar-defined kind                                                          |
| Source range               | `SgNode.range()` supplies beginning/end positions with line, column, and index                                        |
| Structural fields          | Named grammar relationships can be accessed without relying on fixed child positions                                  |
| Recoverable parsing errors | Tree-sitter can produce useful trees for malformed input; successful parsing does not itself prove syntactic validity |

The Python binding does not expose the full native Tree-sitter parser interface, incremental tree-update API, or Tree-sitter query language. Its API concentrates on ast-grep matching, traversal, and edits.

Source preservation versus syntax validity: Edits can retain the untouched portions of the original source exactly, but inserted replacement strings are not automatically guaranteed to produce valid syntax. Tree-sitter's error recovery is useful when analyzing incomplete files, yet syntax validity and semantic correctness remain separate verification concerns.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+2



Source: [https://tree-sitter.github.io/tree-sitter/](https://tree-sitter.github.io/tree-sitter/?utm_source=chatgpt.com)\
Python binding: [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/lib.rs](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/lib.rs?utm_source=chatgpt.com)

### 2.2 Source locations and Unicode

`Range` contains `start` and `end` `Pos` instances, each exposing `line`, `column`, and `index`. Positions are zero-based, and the end is exclusive.

A consequential Python-specific detail is that `index` represents a Unicode character offset, rather than Tree-sitter's internal UTF-8 byte offset. The binding maintains a conversion structure (`UnicodePosition`) for offset translation. The edit API similarly exposes character-based positions suitable for Python source strings.

Consequently, source ranges are valuable for mapping matches to diagnostics or external indexers, but byte-oriented external systems need explicit coordinate conversion. Source positions also describe a particular source snapshot; after rewriting, old ranges should not be treated as positions in the new source.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



Source: [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/unicode_position.rs](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/unicode_position.rs?utm_source=chatgpt.com)

## 3. Structural pattern matching

### 3.1 Code-shaped patterns and metavariables

ast-grep compiles source-language patterns into syntax-tree matchers. For example, `root.find_all(pattern="print($ARG)")` locates structurally matching Python calls and binds the captured argument.

The significant pattern constructs are:

| Construct        | Matching behavior                              | Consequential distinction                                                |
| ---------------- | ---------------------------------------------- | ------------------------------------------------------------------------ |
| `$NAME`          | Matches and captures one named syntax node     | Does not match arbitrary-length node sequences                           |
| `$$NAME`         | Can capture an unnamed syntax node             | Useful for operators and tokens excluded by ordinary named-node matching |
| `$$$NAME`        | Captures zero or more nodes                    | Suitable for argument lists, parameters, statement sequences             |
| `$_` or `$_NAME` | Noncapturing wildcard                          | Avoids capture bookkeeping; repeated names do not enforce equality       |
| Repeated `$NAME` | Requires structurally equivalent captures      | Useful for repeated expressions without custom comparison code           |
| Literal syntax   | Constrains the corresponding grammar structure | Syntax, not merely text, determines what matches                         |

A single metavariable is not equivalent to `.*` in regex. `print($ARG)` does not generally match arbitrary numbers of arguments; `print($$$ARGS)` expresses variable-length matching.

An important detail in the Python API is that `get_multiple_matches("ARGS")` can return unnamed separator nodes, not merely logical arguments. The documented Python example for a comma-separated call includes comma nodes in the capture result. Therefore, consumers should distinguish captured syntax nodes from semantic argument elements.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



Source: [https://ast-grep.github.io/guide/pattern-syntax.html](https://ast-grep.github.io/guide/pattern-syntax.html?utm_source=chatgpt.com)

### 3.2 Contextual patterns and grammar disambiguation

A pattern string normally needs enough syntactic structure for Tree-sitter to interpret its intended node kind. This is not always possible with isolated fragments.

The object form of `pattern` supplies:

| Property     | Purpose                                                                            |
| ------------ | ---------------------------------------------------------------------------------- |
| `context`    | A larger syntactically valid fragment in which the target appears                  |
| `selector`   | The grammar kind to extract from the parsed context and match against target nodes |
| `strictness` | Controls which syntax-tree details the matcher requires                            |

For instance, a class-field fragment can otherwise be interpreted as a standalone assignment. Supplying a class declaration as `context` and the grammar's field node as `selector` makes the intended structure unambiguous.

`pattern` object is not equivalent to adding `kind` alongside a string pattern. The latter filters the matched target's kind; it does not change how the pattern fragment was parsed. The object form is the mechanism for changing that interpretation.

This matters especially for incomplete-looking syntax, language-specific fragments, modifiers, nested declarations, and grammar ambiguities. Error recovery may make invalid patterns appear to work, but upstream explicitly cautions that this behavior can change with parser versions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



Source: [https://ast-grep.github.io/advanced/pattern-parse.html](https://ast-grep.github.io/advanced/pattern-parse.html?utm_source=chatgpt.com)

### 3.3 Matching strictness

The default matcher uses `smart` strictness. The five supported modes provide materially different semantics:

| Mode        | Matching semantics                                               | Typical role                                  |
| ----------- | ---------------------------------------------------------------- | --------------------------------------------- |
| `cst`       | Match all syntax nodes; skip none                                | Exact syntax-sensitive matching               |
| `smart`     | Require all pattern nodes, but permit extra unnamed target nodes | Default structural matching                   |
| `ast`       | Compare named nodes; ignore unnamed syntax                       | Greater tolerance for punctuation differences |
| `relaxed`   | Ignore unnamed nodes and comments                                | More permissive structural equivalence        |
| `signature` | Match named-node kinds without requiring text equality           | Broad shape-oriented recognition              |

The counterintuitive case is `smart`: a JavaScript function pattern lacking `async` may still match an async function because `async` is an extra unnamed target node. `cst` can prevent that behavior, while `ast` and `relaxed` intentionally loosen textual specificity.

Strictness is therefore part of a rule's meaning, not merely an optimization knob. It changes the false-positive/false-negative balance and should be selected according to the syntax distinctions that matter.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



Source: [https://ast-grep.github.io/advanced/match-algorithm.html](https://ast-grep.github.io/advanced/match-algorithm.html?utm_source=chatgpt.com)

## 4. Declarative rule engine

The principal advantage beyond simple Tree-sitter traversal is that the binding can execute compound ast-grep rules natively. Rules describe relationships among syntax nodes, not just isolated text patterns.

### 4.1 Atomic, relational, and composite predicates

| Rule family | Operators                                       | Advanced use                                                                                           |
| ----------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Atomic      | `pattern`, `kind`, `regex`, `nthChild`, `range` | Match source structure, syntax kinds, text restrictions, sibling position, or exact source coordinates |
| Relational  | `inside`, `has`, `precedes`, `follows`          | Constrain matches by ancestors, descendants, and neighboring nodes                                     |
| Composite   | `all`, `any`, `not`, `matches`                  | Build logical predicates and reuse named utility rules                                                 |

A rule identifies a target node. Relational predicates constrain that target using surrounding nodes. A `has` predicate, for example, can locate a function declaration containing a particular statement; an `inside` predicate can locate the statement only when embedded in a qualifying function.

The matching engine can combine structural and textual conditions without requiring Python to enumerate every node and manually inspect its ancestors or descendants.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+2



Source: [https://ast-grep.github.io/reference/rule.html](https://ast-grep.github.io/reference/rule.html?utm_source=chatgpt.com)

### 4.2 Relational search depth, boundaries, and fields

`inside`, `has`, `precedes`, and `follows` accept nested rule objects and two less obvious controls.

`stopBy`: search termination. By default, relations inspect immediate structural neighbors. `stopBy: "end"` broadens the search to the relevant structural boundary; a rule-valued `stopBy` stops traversal at a node satisfying that rule. The stopping node is inclusive in matching. This makes it possible to express bounded ancestor searches or sibling searches without arbitrary recursive Python traversal.

`field`: grammatical relationship. This limits the relation to a named Tree-sitter field. For instance, a key appearing in an object property's `key` field can be distinguished from an identically spelled identifier appearing in its value field. This often yields greater precision than unrestricted `has` searches.

Relational matching is structural, not scope- or control-flow-aware. `inside` knows that a node is descended from another node; it does not prove that a name refers to a particular binding or that an execution path reaches that node.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



Source: [https://ast-grep.github.io/guide/rule-config/relational-rule.html](https://ast-grep.github.io/guide/rule-config/relational-rule.html?utm_source=chatgpt.com)

### 4.3 Position and ordering rules

`nthChild` supports fixed ordinal positions, CSS-like `An+B` expressions, reverse counting, and optional filtering of siblings through `ofRule`. Its positions are 1-based and count named nodes, unlike `child(n)`, which indexes the concrete child sequence from zero.

`range` matches an exact source-location span using line/column coordinates. It is particularly useful for mapping diagnostics or source locations produced by separate tools back onto AST nodes before further inspection or rewriting.

The Python type declarations for `NthChild` are less complete than the documented rule-object options; notably, the documentation describes reverse counting, while the published Python typing shape does not expose every corresponding field. Runtime rules and static annotations should be treated as distinct sources of truth when exercising these options.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 4.4 ESQuery-style selectors inside `kind`

A less obvious native feature is the limited ESQuery-style syntax accepted by the `kind` rule.

It supports structural selectors resembling CSS: direct child `>`, descendant whitespace, adjacent sibling `+`, following sibling `~`, and comma-separated alternatives. Supported pseudo-classes include `:has`, `:not`, `:is`, `:nth-child`, and `:nth-last-child`.

Thus, `kind="call_expression > identifier"` can encode a parent-child relationship in a compact selector instead of a separate nested relational rule. Internally, the selector is translated into ast-grep rule objects.

This is not the full Tree-sitter query language, nor a complete ESQuery implementation. Upstream documents unsupported selectors and limitations in how pseudo-classes accept nested selector lists.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+2



Source: [https://ast-grep.github.io/reference/rule/esquery.html](https://ast-grep.github.io/reference/rule/esquery.html?utm_source=chatgpt.com)

### 4.5 Regex as a structural refinement

The `regex` atomic rule operates on the entire text of a node, including its descendants. It is unanchored unless explicitly anchored, and uses Rust regex semantics rather than Python `re` or PCRE syntax.

Its most valuable role is usually to refine an already structurally restricted target, such as an identifier, string literal, or specific declaration. Applying regex without a structural restriction is broader and potentially more expensive because it cannot exploit AST-kind filtering in the same way as a `kind` or `pattern` rule.

This combination—AST selection first, textual conditions second—provides functionality that would otherwise require manual Python filtering while retaining native rule-engine execution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



## 5. Python search, navigation, and capture APIs

### 5.1 Search and match lifecycle

`SgNode` provides two search forms: keyword arguments representing a `Rule`, and a `Config` mapping containing a rule plus additional declarative facilities.

| API                                    | Behavior                                        | Distinction                                         |
| -------------------------------------- | ----------------------------------------------- | --------------------------------------------------- |
| `find(**rule)`                         | Returns one matching `SgNode`, or `None`        | Convenient existence or first-match search          |
| `find_all(**rule)`                     | Returns a list of matching nodes                | Materializes the complete result set                |
| `find(config)`                         | Finds using a structured configuration          | Enables constraints, utilities, and transformations |
| `find_all(config)`                     | Collects matches using structured configuration | Preserves declarative conditions in the matcher     |
| `matches(**rule)`                      | Tests the current node                          | Boolean refinement without a separate search        |
| `inside(**rule)`                       | Tests the node's ancestry                       | Useful for contextual filtering                     |
| `has(**rule)`                          | Tests qualifying descendants                    | Useful for structural containment                   |
| `precedes(**rule)` / `follows(**rule)` | Tests structural neighbors                      | Useful for local ordering relationships             |

The refinement methods accept rule keyword arguments, not the richer `Config` object. When constraints or utilities are integral to the match, using `find` or `find_all` with `Config` avoids splitting the logic between declarative and imperative filters.

The binding implements these searches inside Rust and converts matches into Python objects. In particular, `find_all` returns a Python list rather than a streaming iterator.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+2



### 5.2 Capture extraction and transformed values

A matching `SgNode` carries the metavariable environment produced by the rule.

| API                            | Return                         | Meaning                                        |
| ------------------------------ | ------------------------------ | ---------------------------------------------- |
| `get_match("NAME")`            | `SgNode` or `None`             | Single metavariable capture                    |
| `node["NAME"]`                 | `SgNode`, or raises `KeyError` | Required single capture                        |
| `get_multiple_matches("NAME")` | `list[SgNode]`                 | Captures from `$$$NAME`                        |
| `get_transformed("NAME")`      | `str` or `None`                | Value generated by a configured transformation |
| `text()`                       | `str`                          | Original source corresponding to the match     |
| `range()`                      | `Range`                        | Original source coordinates                    |

Capture names omit the `$` prefix. A transformed value is text, not a syntax-tree node; it does not automatically have a grammar kind, location, or parent relationship.

One subtle source-level distinction is that the capture environment belongs to the particular successful match. Captures collected through different `any` branches are not necessarily the same. `all` combines metavariable bindings from successful subrules, and its ordered evaluation is documented, which matters when designing interdependent capture conditions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+2



### 5.3 Traversal beyond matching

A substantial part of the package's value is that structural search results remain navigable.

| Functional group   | Methods                                | Architectural significance                       |
| ------------------ | -------------------------------------- | ------------------------------------------------ |
| Inspection         | `kind`, `text`, `range`                | Extract structural and positional facts          |
| Node properties    | `is_leaf`, `is_named`, `is_named_leaf` | Distinguish meaningful grammar nodes from tokens |
| Structural parents | `parent`, `ancestors`                  | Derive enclosing syntactic context               |
| Direct children    | `child`, `children`, `named_children`  | Inspect precise or normalized child sequences    |
| Grammar fields     | `field`, `field_children`              | Resolve roles from grammar-defined field names   |
| Sibling navigation | `next`, `next_all`, `prev`, `prev_all` | Inspect sequential syntax relationships          |
| Owning parse       | `get_root`                             | Retain access to the originating `SgRoot`        |

`field_children(name)` is an easily overlooked capability. It retrieves multiple children associated with a named grammar field. The Python type stub and Rust implementation expose it even though the main Python guide primarily documents `field(name)`.

Field access often provides a more stable abstraction than positional child indexing. For example, a grammar may expose `name`, `body`, `parameters`, or `arguments` as fields. Such relationships survive many syntactic variations that would change raw child positions.

However, field names remain grammar-specific, not a cross-language semantic ontology. A function in Python and a function in Rust may expose different node kinds and field relationships. A normalized cross-language representation must still define those correspondences.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Source: [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/ast_grep_py.pyi](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/ast_grep_py.pyi?utm_source=chatgpt.com)

### 5.4 Object identity and source ownership

The Rust implementation maintains a reference to the owning `SgRoot` in each `SgNode`, keeping the parse tree alive while Python retains node objects.

The node implementation also exposes equality and hashing based on internal node identifiers. Those identifiers should be understood as tree-local implementation identities, not persistent semantic identifiers suitable for use across reparses, changed files, or separate processes.

For durable indexing, an external representation based on source identity, snapshot/version, range, kind, and additional structural or semantic disambiguation is more appropriate.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 6. Advanced configuration: constraints, utilities, and transformations

The Python `Config` type exposes four fields:

| Field         | Function                                | Distinction                                                  |
| ------------- | --------------------------------------- | ------------------------------------------------------------ |
| `rule`        | Primary structural predicate            | Determines candidate target nodes                            |
| `constraints` | Rules applied to captured metavariables | Filters candidates after primary matching                    |
| `utils`       | Named reusable rule definitions         | Supports local compositional abstraction                     |
| `transform`   | Named text transformations              | Produces derived values accessible through `get_transformed` |

These are Python mappings represented by `TypedDict` declarations, not independent compiled matcher classes. They provide the declarative search portion of ast-grep's configuration system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 6.1 Metavariable constraints

`constraints` associates a captured single metavariable with additional rules applied to that capture.

For example, a call pattern capturing `$ARG` can constrain `ARG` to an identifier, numeric literal, specific expression form, or textual condition, without broadening the primary search to every candidate syntax kind.

Significant semantics:

Evaluation order. The principal rule matches first; constraints subsequently filter the captured variables. This is not equivalent to unrestricted matching of the entire syntax tree.

Single-node scope. Constraints operate on single captures such as `$ARG`, not variadic captures such as `$$$ARGS`. Whole-sequence conditions therefore require another formulation.

Negation. Constraints on metavariables nested inside `not` are not generally reliable; negative predicates do not establish the same capture environment as successful positive matches.

This capability can eliminate repetitive Python-side checks while making extraction assumptions explicit in one matcher definition.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 6.2 Reusable utility rules

`utils` assigns names to rule objects, which can then be invoked using the composite `matches` predicate.

This supports rule factoring. A reusable definition of "function-like syntax," for example, can combine several declaration and expression node kinds; multiple higher-level rules can refer to that definition without duplicating its alternatives.

The distinction between environments is important: the Python `Config` supports local utilities, while the CLI additionally supports global utility-rule files as part of its project configuration workflow. Passing a utility name to the Python API does not imply automatic resolution from a CLI rule directory.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



Source: [https://ast-grep.github.io/guide/rule-config/utility-rule.html](https://ast-grep.github.io/guide/rule-config/utility-rule.html?utm_source=chatgpt.com)

### 6.3 Native metavariable transformations

The `transform` mapping enables additional text processing within the declarative matcher. Its output can be read using `get_transformed`.

| Transformation | Capabilities                                                                         |
| -------------- | ------------------------------------------------------------------------------------ |
| `replace`      | Rust-regex replacement with captured-group substitution                              |
| `substring`    | Character-indexed slicing, including negative positions                              |
| `convert`      | Identifier and general string case conversion                                        |
| `rewrite`      | Experimental AST-aware rewriting of captured subtrees; requires rewriter definitions |

`convert` supports `lowerCase`, `upperCase`, `capitalize`, `camelCase`, `snakeCase`, `kebabCase`, and `pascalCase`. Separator-sensitive conversions can recognize dashes, dots, spaces, slashes, underscores, and capitalization boundaries, with optional `separatedBy` control.

Transformation objects and the compact expression syntax introduced in earlier ast-grep releases are documented by the core engine. In the Python binding, the tested configuration path includes object-style transformations and retrieval through `get_transformed`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+3



Source: [https://ast-grep.github.io/reference/yaml/transformation.html](https://ast-grep.github.io/reference/yaml/transformation.html?utm_source=chatgpt.com)

Important boundary: the upstream `rewrite` transformation is explicitly experimental and depends on rewriter definitions in a configuration field that is not exposed by the Python `Config` type. It should not be treated as equivalent to a fully supported Python-side recursive rewriter facility.

For arbitrary programmatic transformations, Python can instead generate replacement text directly and apply it through the edit API. That offers greater host-language flexibility at the cost of managing transformation correctness and conflict handling.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



## 7. Source transformation and edit management

### 7.1 Immutable source editing

The binding's transformation model has two operations:

`SgNode.replace(new_text)` creates an `Edit` describing a replacement over that node's source span.

`SgNode.commit_edits(edits)` applies those edits to the source text represented by the node on which it is called and returns a new source string.

The original syntax tree remains unchanged. This means a pipeline can analyze a consistent snapshot, accumulate independent edits, produce a new source representation, then parse that representation again.

The Python API intentionally differs from the CLI's declarative `fix` behavior. `replace("new_call($ARG)")` inserts that literal string; it does not interpolate `$ARG`. Captured nodes must be accessed explicitly and incorporated into Python-generated text.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 7.2 Edit structure and advanced manipulation

The `Edit` object exposes mutable fields:

| Field           | Meaning                                   |
| --------------- | ----------------------------------------- |
| `start_pos`     | Starting Unicode character offset         |
| `end_pos`       | Exclusive ending Unicode character offset |
| `inserted_text` | Replacement source text                   |

The binding's own tests demonstrate that an edit created by `replace` can have its range modified before committing. This permits more than simple whole-node substitution: an edit can be adjusted to affect surrounding punctuation or adjacent source text.

There is also a consequential distinction between the node generating an edit and the node committing it. An edit on a deeply nested node is positioned in the original full source; calling `commit_edits` on the root node produces an updated complete source string. Calling it on a subtree instead produces text for that subtree, subject to the edit locations being applicable to that region.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Source: [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/tests/test_fix.py](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/tests/test_fix.py?utm_source=chatgpt.com)

### 7.3 Multiple edits, overlap, and correctness

The Rust implementation sorts edits by starting offset and applies them against the original source snapshot. Overlapping edits are skipped rather than reported as an error.

This is an important correctness limitation. If one edit replaces a parent node while another replaces a child node within it, both cannot be applied independently to the same source span. The implementation's silent skip means a caller that requires complete application must detect or resolve such conflicts before committing.

This matters for codemods in which multiple structural rules can match nested expressions. Plausible strategies include selecting outermost matches, selecting innermost matches, defining rule precedence, or performing explicitly ordered reparsing passes. These are orchestration choices, not automatic guarantees of the Python binding.

The edit engine also does not itself perform formatting, name resolution, import organization, semantic validation, or type checking. Those concerns may be handled separately, depending on the transformation's requirements.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Source: [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_node.rs](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_node.rs?utm_source=chatgpt.com)

### 7.4 Why this is distinct from AST regeneration

Source-span editing offers an important architectural advantage over regenerating an entire file from a simplified abstract syntax representation: unchanged text does not need to be reconstructed.

For localized structural migrations, this can preserve surrounding whitespace, comments, and formatting without a dedicated whole-language pretty-printer. It is not a guarantee that the transformed region itself remains well formatted or syntactically valid.

The resulting capability is best characterized as structurally targeted, text-preserving source editing, not a general semantic refactoring engine.

## 8. Languages and extensibility

### 8.1 Built-in language reach

The engine's built-in language definitions span application languages, systems languages, and structured document syntaxes. Examples include Python, Rust, C/C++, JavaScript/TypeScript, TSX, Go, Java, Kotlin, Ruby, Swift, Bash, Lua, JSON, YAML, HTML, CSS, Markdown, HCL, Nix, Solidity, and Zig.

Language aliases and file-extension mappings are documented primarily for the CLI. In Python, the caller supplies the language string directly to `SgRoot`, so selecting a language does not itself perform file discovery or extension inference.

Language support means Tree-sitter parsing and structural matching against that language's grammar, not compiler-equivalent semantics or complete support for every dialect and preprocessor environment. Grammar versions can affect available node kinds, field names, and matching behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+2



Source: [https://ast-grep.github.io/reference/languages.html](https://ast-grep.github.io/reference/languages.html?utm_source=chatgpt.com)

### 8.2 Dynamic Tree-sitter grammar registration

The Python binding exposes `register_dynamic_language`, enabling additional Tree-sitter grammars to be loaded as native shared libraries.

The underlying Python-language registration code supports configuration of the library path, grammar symbol, metavariable character, and pattern-expansion character. The upstream test also supplies an `extensions` field, even though that field is omitted from the published Python `CustomLang` type definition.

This discrepancy is worth recognizing: the Python type declaration is not fully synchronized with the native registration structure. The runtime deserializer currently has an `extensions` field, and the upstream test passes it explicitly. For advanced custom-language use, the implementation and test are more informative than the type declaration alone.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



Source: [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/tests/test_register_lang.py](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/tests/test_register_lang.py?utm_source=chatgpt.com)

The registration mechanism resolves configuration relative to the process's current working directory. Custom grammars must therefore be supplied as compatible platform-native parser libraries, and the runtime must be able to load them.

Security boundary: loading a Tree-sitter grammar shared library executes native code within the Python process. The CLI introduced explicit custom-language trust/allow controls in ast-grep 0.50.0; those CLI flags are not Python registration controls. The Python host is responsible for deciding which native libraries it loads.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



Source: [https://ast-grep.github.io/advanced/custom-language.html](https://ast-grep.github.io/advanced/custom-language.html?utm_source=chatgpt.com)

### 8.3 Metavariable syntax in nonstandard languages

A distinctive engine feature is its ability to adapt metavariable parsing to language grammars that cannot accept `$NAME` as an ordinary token.

Custom grammars can configure `meta_var_char` and `expando_char`. The latter enables ast-grep to preprocess a pattern into text the grammar can parse while still interpreting metavariable captures.

This makes structural matching feasible for languages whose identifier or interpolation syntax would otherwise conflict with ast-grep's default pattern notation.

The mechanism depends on appropriate language-specific preprocessing and grammar compatibility; changing characters alone does not make an arbitrary grammar understand all pattern constructs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 8.4 Embedded languages and injection boundaries

The broader ast-grep project supports language injection: locating JavaScript or CSS inside HTML, for example, or interpreting configured regions of a host document using another grammar.

However, the documented implementation is centered on CLI discovery, language inference, extraction, and project configuration. The Python binding's public surface does not provide an equivalent complete injection-management API.

Python can still orchestrate the constituent operations: locate embedded regions using the host syntax tree, extract source text, parse it with the appropriate language, and reconcile coordinates. But this is an integration workflow rather than an automatically inherited CLI feature.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



Source: [https://ast-grep.github.io/advanced/language-injection.html](https://ast-grep.github.io/advanced/language-injection.html?utm_source=chatgpt.com)

## 9. Performance characteristics and operational boundaries

### 9.1 Sources of efficiency

The package derives its efficiency chiefly from its native Rust and Tree-sitter implementation.

| Mechanism                   | Potential benefit                                                | Qualification                                                        |
| --------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------- |
| Native parsing and matching | Avoids interpreting every matching operation in Python           | Parse and matching complexity still depend on source and rule        |
| AST-kind-aware matching     | Reduces candidate work for structurally selective rules          | Broad or regex-dominated predicates can lose this advantage          |
| In-process PyO3 binding     | Avoids launching a CLI subprocess for every operation            | Python/native conversions and object materialization still cost time |
| Native relational rules     | Avoids returning large candidate sets merely to filter in Python | Rule complexity and traversal depth remain relevant                  |
| Source-preserving edits     | Avoids whole-file AST regeneration                               | Conflict resolution, validation, and formatting are separate         |

Upstream explicitly notes that `kind` and `pattern` permit candidate filtering by syntax kind, whereas broad text regex searches do not offer the same optimization. This explains why structurally selective rules can be preferable to unconstrained regex scans.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 9.2 Compilation and traversal boundaries

A less obvious limitation appears in the binding source: each call to a search or refinement method constructs a matcher from the supplied Python rule/configuration. There is no public Python API for retaining and reusing a separately compiled matcher object across many searches.

That does not negate the advantages of native matching, but it changes how performance should be understood. Repeated independent Python calls with identical rules can incur repeated rule-construction overhead. A single structurally expressive `find_all` call can reduce Python/native round trips and repeated matcher construction compared with iterative per-node refinements.

`find_all` also collects results into a Python list. Very large match sets therefore incur allocation and object-conversion overhead. The package does not expose the CLI's built-in repository-wide streaming, parallel file discovery, or reporting machinery through the `SgNode` API.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 9.3 Incremental and concurrent processing

Tree-sitter itself supports incremental parsing. The exposed Python `SgRoot` constructor, however, accepts a source string and language; it does not provide an incremental edit/update interface for an existing tree.

Likewise, the binding uses Rust-native internals, but this alone does not establish a particular Python-level multithreading speedup. Any performance claim involving concurrency, GIL behavior, parsing amortization, or throughput would need measurement for the relevant package build and workload.

For frequently changing sources, retaining source snapshots and reparsing can be simpler than attempting to infer unsupported incremental behavior from Tree-sitter's general capabilities.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



## 10. Integration possibilities and architectural distinctions

### 10.1 Structural indexing and code intelligence

The binding can produce structured facts from source files: syntax kinds, source ranges, captured names, parent-child relationships, grammar fields, and matched structural motifs.

Those facts can feed an external relational database, document store, graph representation, or source index. This can support capabilities such as structural code search, symbol-like inventory construction, code-pattern classification, and syntax-based change-impact candidate discovery.

However, syntax relationships are not semantic relationships. ast-grep-py does not by itself resolve imports, name bindings, aliases, types, method dispatch, control flow, or data flow. Such facts require an appropriate compiler frontend, language server, semantic indexer, or other analysis system.

Its strongest architectural role is often as a lightweight structural-analysis layer that can either stand alone or complement more expensive semantic tooling.

### 10.2 Declarative predicates plus arbitrary Python analysis

The most useful composition boundary is between native structural matching and host-language processing.

The native matcher identifies candidate syntax with its declarative rules; Python then handles operations outside the matcher vocabulary, such as aggregation, correlation across files, external lookups, custom classification, schema normalization, or programmatic replacement generation.

This arrangement can reduce bespoke AST walking without attempting to encode general-purpose computation in structural rules. It also supports an incremental escalation path: simple problems remain entirely declarative, while only the genuinely nonstructural portions need custom Python logic.

### 10.3 External diagnostics and structural edits

The `range` predicate and node-location API make it possible to connect diagnostics produced by separate tools with source syntax nodes.

An external compiler or analyzer might identify a source span, while ast-grep-py can locate the corresponding node, inspect the surrounding syntax, and construct a targeted edit.

This is not equivalent to applying a compiler-verified refactoring. The external tool must provide compatible source coordinates and snapshots, and the resulting edit must still satisfy whatever semantic constraints the operation requires.

### 10.4 Comparison with adjacent technologies

| Technology                            | Strongest native capability                                                     | Material distinction from `ast-grep-py`                                                                   |
| ------------------------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `ast-grep` CLI                        | Repository-wide structural search, linting, diagnostics, codemods               | Provides file scanning, configuration and reporting that Python must orchestrate                          |
| Python `tree_sitter`                  | Low-level syntax trees, parser access, Tree-sitter queries, incremental parsing | Greater parser-level control; lacks ast-grep's code-shaped rule engine as a native abstraction            |
| Python standard `ast`                 | Python-specific abstract syntax representation                                  | Stronger alignment with Python language constructs; not multilingual or source-preserving in the same way |
| `LibCST`                              | Python-specific concrete syntax transformations and metadata                    | Designed for Python codemods and richer Python-specific transformation workflows                          |
| Compiler frontends / language servers | Symbol resolution, types, references, language semantics                        | Provide information that syntactic pattern matching cannot derive reliably                                |
| SCIP / semantic code indexes          | Cross-file semantic identities and relationships                                | Complementary structured semantic information, not a replacement for source-level matching                |

The distinction is therefore not simply speed or number of languages. It is where the abstraction sits: ast-grep-py packages a high-level, syntax-aware rule engine as an embeddable Python API, while leaving broader semantic reasoning and project-level orchestration to other components.

## 11. Important correctness and capability limits

| Limitation                                                    | Why it matters                                                                                               |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Grammar-dependent structural matching                         | Node kinds and fields can change across language grammar versions                                            |
| No native symbol resolution                                   | Identically spelled identifiers are not necessarily the same binding                                         |
| Pattern strictness changes semantics                          | `smart` matching can accept extra syntax that an exact comparison would reject                               |
| No implicit metavariable interpolation in Python replacements | Captures must be incorporated into replacement text explicitly                                               |
| Silent skipping of overlapping edits                          | A completed rewrite may not contain every requested modification                                             |
| Immutable parse snapshots                                     | Applying edits does not update the original syntax tree                                                      |
| Limited `Config` relative to CLI YAML                         | Lint metadata, file globs, fixes, rewriter declarations, and project configuration are separate capabilities |
| Eager match results                                           | Large `find_all` outputs materialize Python objects                                                          |
| No exposed compiled-matcher reuse                             | Repeated searches may reconstruct equivalent matchers                                                        |
| No complete Python injection-management API                   | Embedded-language extraction requires separate orchestration                                                 |
| Incomplete typing for some advanced options                   | Published type hints do not capture every field accepted by native configuration structures                  |
| Native custom-language loading                                | Grammar libraries require compatibility and should be treated as executable code                             |

These are not necessarily reasons to avoid the library. They identify the boundaries between structural recognition, source rewriting, semantic validation, and workflow orchestration—boundaries that matter when combining ast-grep-py with other code-analysis systems.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+4



## 12. Source reference map

The most useful primary references for further investigation are grouped below.

| Investigation                     | Direct primary source                                                                                                                                                                                   |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Python API and usage              | [https://ast-grep.github.io/guide/api-usage/py-api.html](https://ast-grep.github.io/guide/api-usage/py-api.html?utm_source=chatgpt.com)                                                                 |
| Exported Python types             | [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/\_\_init\_\_.py](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/__init__.py?utm_source=chatgpt.com)     |
| Python node method signatures     | [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/ast_grep_py.pyi](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/ast_grep_py.pyi?utm_source=chatgpt.com) |
| Structural patterns and captures  | [https://ast-grep.github.io/guide/pattern-syntax.html](https://ast-grep.github.io/guide/pattern-syntax.html?utm_source=chatgpt.com)                                                                     |
| Pattern matching algorithm        | [https://ast-grep.github.io/advanced/match-algorithm.html](https://ast-grep.github.io/advanced/match-algorithm.html?utm_source=chatgpt.com)                                                             |
| Complete rule vocabulary          | [https://ast-grep.github.io/reference/rule.html](https://ast-grep.github.io/reference/rule.html?utm_source=chatgpt.com)                                                                                 |
| ESQuery-style selectors           | [https://ast-grep.github.io/reference/rule/esquery.html](https://ast-grep.github.io/reference/rule/esquery.html?utm_source=chatgpt.com)                                                                 |
| Relational matching               | [https://ast-grep.github.io/guide/rule-config/relational-rule.html](https://ast-grep.github.io/guide/rule-config/relational-rule.html?utm_source=chatgpt.com)                                           |
| Utilities and reuse               | [https://ast-grep.github.io/guide/rule-config/utility-rule.html](https://ast-grep.github.io/guide/rule-config/utility-rule.html?utm_source=chatgpt.com)                                                 |
| Configuration and constraints     | [https://ast-grep.github.io/reference/yaml.html](https://ast-grep.github.io/reference/yaml.html?utm_source=chatgpt.com)                                                                                 |
| Text transformations              | [https://ast-grep.github.io/reference/yaml/transformation.html](https://ast-grep.github.io/reference/yaml/transformation.html?utm_source=chatgpt.com)                                                   |
| Native Python node implementation | [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_node.rs](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_node.rs?utm_source=chatgpt.com)                           |
| Unicode offsets                   | [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/unicode_position.rs](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/unicode_position.rs?utm_source=chatgpt.com)         |
| Custom-language registration      | [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_lang.rs](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_lang.rs?utm_source=chatgpt.com)                           |
| Python behavior tests             | [https://github.com/ast-grep/ast-grep/tree/main/crates/pyo3/tests](https://github.com/ast-grep/ast-grep/tree/main/crates/pyo3/tests?utm_source=chatgpt.com)                                             |
| Built-in languages                | [https://ast-grep.github.io/reference/languages.html](https://ast-grep.github.io/reference/languages.html?utm_source=chatgpt.com)                                                                       |
| Package and distribution          | [https://pypi.org/project/ast-grep-py/](https://pypi.org/project/ast-grep-py/?utm_source=chatgpt.com)                                                                                                   |
| Stable release                    | [https://github.com/ast-grep/ast-grep/releases/tag/0.51.0](https://github.com/ast-grep/ast-grep/releases/tag/0.51.0?utm_source=chatgpt.com)                                                             |

The API documentation and implementation references are maintained upstream and may evolve independently of a specific release. The discussion here targets the stable 0.51.0 capability surface, while source-level implementation details should be rechecked against the installed version whenever behavior is consequential.

Overall: `ast-grep-py` offers considerably more than embedded structural grep. Its most significant capabilities are a composable native rule engine, grammar-aware relational search, rich metavariable capture and transformation, precise source coordinate handling, navigable syntax-tree objects, and programmable source edits. Together, they enable substantial structural analysis and codemod functionality without constructing a custom Tree-sitter query engine or AST-walking framework. Its natural limits arise where structural syntax analysis must become semantic analysis, or where in-memory operations must become a fully managed repository-scale workflow.