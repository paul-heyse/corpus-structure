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

# ast-grep-py — Addendum: Advanced Matching Semantics, Rule Composition, and Integration Details

Supplement to: ast-grep-py — Comprehensive Python Library Overview\
Original target: 0.51.0\
Updated target: 0.51.1\
Research date: November 7, 2026

## Scope and version notes

This addendum extends the original reference with advanced pattern interpretation, recursive utility rules, cross-node capture propagation, declarative transformation pipelines, selector behavior, and consequential correctness distinctions. It also clarifies several API constraints that the original guide describes too broadly.

The additions primarily concern combinations of existing capabilities rather than new top-level Python APIs. They are relevant to structural extraction, syntax-aware indexing, compositional source analysis, and transformations that would otherwise require custom tree traversal or Python-side filtering.

`ast-grep-py` 0.51.1 was published on November 2, 2026. Its relevant upstream changes include a correction to dynamic-language metavariable-sigil expansion and fixes affecting the broader ast-grep engine and distribution. The release does not establish a new Python API family.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



The material below distinguishes Python-exposed functionality from semantics established by the shared Rust engine. Examples are illustrative and source-derived; they have not been separately executed against the published 0.51.1 wheel.

Primary references:

- Release: [https://github.com/ast-grep/ast-grep/releases/tag/0.51.1](https://github.com/ast-grep/ast-grep/releases/tag/0.51.1?utm_source=chatgpt.com)
- Python API: [https://ast-grep.github.io/guide/api-usage/py-api.html](https://ast-grep.github.io/guide/api-usage/py-api.html?utm_source=chatgpt.com)
- Python binding types: [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/\_\_init\_\_.py](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/__init__.py?utm_source=chatgpt.com)

## 1. Effective pattern nodes and structural matching boundaries

Extends original §§3.1–3.2.

### 1.1 Pattern parsing and effective-node extraction are separate operations

When compiling a structural pattern, ast-grep first parses the supplied source-language text into a syntax tree, then extracts the syntax node that will serve as the actual pattern.

This second operation is essential: parsing an expression as a standalone source file often produces multiple wrapper nodes that are not intended to constrain a structural search.

For JavaScript, parsing `foo(bar)` typically produces a hierarchy resembling:

```
program
└── expression_statement
    └── call_expression       ← effective pattern node
        ├── identifier
        └── arguments
            └── identifier
```

By default, ast-grep selects a leaf node or the innermost node with multiple children, according to its documented heuristic. The resulting matcher generally targets the most specific syntax construct that retains the pattern's relevant structural information.

For `foo(bar)`, the effective node is `call_expression`, not the outer `expression_statement`.

This changes more than the search scope. The effective node determines the match's syntax kind and source range, the structural level at which relational predicates operate, and the source span targeted by a subsequent replacement.

In particular, a pattern matching a call expression does not necessarily select its enclosing statement or trailing semicolon.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 1.2 Explicit selectors control match granularity

The `selector` property of an object-style pattern overrides the default effective-node selection.

For example:

```
from ast_grep_py import SgRootsource = """console.log("first");console.log("second");"""root = SgRoot(source, "javascript").root()calls = root.find_all(    pattern="console.log($ARG)")statements = root.find_all(    pattern={        "context": "console.log($ARG);",        "selector": "expression_statement",    })
```

The first matcher targets call expressions. The second explicitly targets their enclosing expression statements.

Selecting the statement is consequential when working with statement-level sibling relationships, precise edits, or statement-level source ranges.

It is therefore useful to distinguish two reasons for selecting an explicit node:

Grammar disambiguation: A larger syntactic context allows an otherwise ambiguous or invalid fragment to parse as the intended grammar construct.

Match-boundary control: The parser already understands the input, but its default effective node is not the syntax unit that the operation needs.

These are separate concerns, although the same `context`/`selector` mechanism addresses both.

The latter is particularly important with `precedes` and `follows`, since the surrounding nodes inspected by those predicates depend on the structural level of the target.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



Source: [https://ast-grep.github.io/advanced/pattern-parse.html](https://ast-grep.github.io/advanced/pattern-parse.html?utm_source=chatgpt.com)

## 2. Metavariable recognition, unnamed syntax, and variadic matching

Extends original §§3.1 and 4.2.

### 2.1 Metavariables are recognized syntax nodes, not textual placeholders

A metavariable is not recognized merely because its text begins with `$`. It must satisfy the metavariable naming convention and correspond to an appropriate node in the parsed pattern.

Ordinary metavariable names use uppercase letters, underscores, and digits, but cannot begin with a digit. Consequently, `$ARG`, `$ARG_1`, and `$_` are valid forms, while `$arg`, `$MixedCase`, and `$123` are not recognized as ordinary metavariables.

More importantly, the metavariable must occupy a recognized syntax-node boundary.

| Pattern fragment | Recognition                                                                           |
| ---------------- | ------------------------------------------------------------------------------------- |
| `$A`             | Single structural metavariable                                                        |
| `$A.$B`          | Separate metavariables where the grammar parses the components into appropriate nodes |
| `$A.method($B)`  | Captures receiver and argument nodes                                                  |
| `obj.on$EVENT`   | Does not capture an identifier suffix                                                 |
| `"Hello $WORLD"` | Does not capture a substring within the string literal                                |
| `a $OP b`        | Cannot generally capture an operator through an ordinary code-shaped pattern          |

This explains why ast-grep's structural matching cannot be treated as a text-template engine. The matcher operates on grammar nodes, while textual interpolation and substring matching operate within node contents.

When the desired variable component is only part of an identifier or string, regex refinement and text transformations may provide the missing operation. When it is a punctuation or operator token, unnamed-node matching may be appropriate.

These mechanisms solve different problems and should not be conflated.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 2.2 Capturing operators and unnamed syntax using field-constrained relations

The `$$NAME` metavariable form permits matching unnamed syntax nodes. Combined with a grammar field and a relational predicate, it can extract tokens that cannot be represented by a generic expression metavariable.

For example, in a language grammar exposing a `binary_expression` node with an `operator` field:

```
rule = {    "kind": "binary_expression",    "has": {        "field": "operator",        "pattern": "$$OP",    },}
```

The `has` relation inspects the operator field, while `$$OP` matches the unnamed operator token.

This allows an expression to remain the primary match while exposing its operator as a metavariable capture.

The distinction is important for structural classification because an operator is often represented as a concrete token rather than a named expression node. Without this mechanism, an analyzer might otherwise enumerate children, identify the operator's source span, and extract its text manually.

The same principle can apply to other grammar-defined punctuation, keywords, and modifiers when the relevant field relationship and node representation are available.

This is a documented core-engine capability expressible through the Python `Rule` configuration. Field names and operator-node representation remain language-grammar-specific.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 2.3 Variadic metavariables have structural stopping behavior

The original guide establishes that `$$$NAME` matches zero or more nodes, but the matching termination rule is also significant.

When a variadic metavariable is followed by additional pattern nodes, ast-grep consumes source nodes until the following pattern node can match. Upstream characterizes this as behavior analogous to non-greedy textual matching.

For example, a pattern containing an argument sequence followed by a fixed final argument structurally constrains where the variadic capture ends.

This does not make `$$$` equivalent to a regular-expression wildcard. It still operates over the syntax-tree node sequence, including potentially unnamed separators, subject to the parsed pattern's structure.

Because capture boundaries depend on following syntax, a variadic metavariable placed between several similar nodes can behave differently from one placed at the end of a pattern. That distinction matters when deriving ordered argument lists, statement sequences, or replacement spans.

Source: [https://ast-grep.github.io/advanced/pattern-parse.html](https://ast-grep.github.io/advanced/pattern-parse.html?utm_source=chatgpt.com)

## 3. Recursive structural matching through utility rules

Extends original §6.2.

### 3.1 Utility rules can define recursive structural predicates

The `utils` and `matches` mechanisms support more than factoring repeated predicates. Utility definitions can reference themselves recursively, provided the recursion advances through syntax-tree relationships.

This enables recognition of arbitrarily nested structural forms without implementing recursive traversal in Python.

For example, consider JavaScript numeric literals surrounded by any number of parenthesized expressions:

```
123
(123)
((123))
(((123)))
```

An ordinary `kind: number` rule recognizes the literal but not its enclosing parenthesized expressions.

A recursive utility rule can recognize both:

```
from ast_grep_py import SgRootsource = "(((123)))"config = {    "rule": {        "matches": "is-number"    },    "utils": {        "is-number": {            "any": [                {"kind": "number"},                {                    "kind": "parenthesized_expression",                    "has": {                        "matches": "is-number"                    }                }            ]        }    }}root = SgRoot(source, "javascript").root()matches = root.find_all(config)
```

The utility recognizes a node when either condition holds: the node is a numeric literal, or it is a parenthesized expression containing a child that recursively satisfies the same utility.

The recursive structure corresponds to the grammar:

\\[ N \rightarrow \text{number}\\;|\\;(\\,N\\,) \\]

This is a useful conceptual distinction. Rather than expressing a fixed maximum nesting depth, the rule describes a recursively recognizable syntax family.

Similar constructions can recognize parenthesized expressions, recursively nested declarations, particular expression trees, and other structurally recursive forms, subject to the language grammar and the expressiveness of ast-grep's relational rules.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 3.2 Structural recursion versus invalid dependency cycles

Ast-grep distinguishes recursion that advances through the syntax tree from recursive references that repeatedly evaluate the same node.

A direct dependency such as:

```
utils:
  recursive:
    matches: recursive
```

does not establish structural progress and creates an invalid dependency cycle.

By contrast:

```
utils:
  recursive:
    has:
      matches: recursive
```

recurses through a descendant relationship. Each recursive evaluation operates on a structurally different node.

The same principle applies to recursion through `inside`, which advances toward enclosing syntax nodes.

Upstream explicitly permits self-reference through relational components while disallowing cyclic dependencies through same-node composite components.

This restriction is important when designing recursive recognizers: a recursive utility must have an appropriate base case and make progress through the relevant structural relationship.

Architectural implication: Recursive utilities allow a declarative matcher to recognize certain grammar-like structural families without constructing a separate tree-walking engine. They do not constitute a general-purpose parser generator or semantic recursion system; recognition remains constrained by the existing Tree-sitter syntax tree and ast-grep's rule vocabulary.

Sources:

[https://ast-grep.github.io/guide/rule-config/utility-rule.html](https://ast-grep.github.io/guide/rule-config/utility-rule.html?utm_source=chatgpt.com)

[https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/\_\_init\_\_.py](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/__init__.py?utm_source=chatgpt.com)

## 4. Capture propagation and rule evaluation semantics

Extends original §§4.1, 4.2, and 5.2.

### 4.1 Relational predicates can contribute metavariable captures

Relational predicates are frequently described as Boolean conditions on a target node. However, their nested matchers can also contribute metavariable bindings to the successful match.

For example, an expression can be selected as the target while an `inside` rule captures information from an enclosing declaration.

Conversely, a declaration can be the target while a `has` rule captures information from a qualifying descendant.

The resulting match can therefore contain information from multiple structural locations.

Conceptually, a matching configuration may produce:

| Component                 | Structural role                    | Information available                    |
| ------------------------- | ---------------------------------- | ---------------------------------------- |
| Primary target            | Node satisfying the principal rule | Target kind, text, range                 |
| `inside` match            | Qualifying enclosing node          | Captures from an enclosing declaration   |
| `has` match               | Qualifying descendant node         | Captures from a nested expression        |
| Other successful subrules | Additional structural conditions   | Captures established by those predicates |

Upstream explicitly documents using metavariables captured within relational rules in subsequent fixes. The Python binding exposes the shared engine's capture environment through `get_match()` and `get_multiple_matches()`.

The resulting composition can support structured extraction without separately locating, navigating to, and correlating every related node in Python.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



There are important limits. Capture availability depends on which predicates actually matched, and captures from unsuccessful or negated branches should not be assumed to exist. The existence of a structural relationship also does not establish semantic name binding, lexical scope identity, or executable dependency.

### 4.2 Explicit `all` lists control evaluation order

Ast-grep supports combining several predicates within one rule object:

```
{    "pattern": "$A + $B",    "inside": {        "kind": "return_statement"    }}
```

Such predicates are logically combined, but the ordinary rule-object representation does not guarantee their evaluation order.

This can become significant when one predicate establishes a metavariable binding that another predicate relies upon.

For ordered evaluation, use an explicit `all` list:

```
{    "all": [        {            "pattern": "$A + $B"        },        {            "inside": {                "kind": "return_statement"            }        }    ]}
```

The `all` operator guarantees evaluation in list order.

This distinction matters primarily for capture-dependent matching, rather than independent Boolean conditions. Reordering independent conditions does not generally change their logical result, but reordering capture-producing and capture-consuming predicates can change how their match environments are constructed.

Source: [https://ast-grep.github.io/guide/rule-config/composite-rule.html](https://ast-grep.github.io/guide/rule-config/composite-rule.html?utm_source=chatgpt.com)

### 4.3 Composite predicates apply to one candidate node

Another consequential semantic distinction is that `all` and `any` quantify over predicates, not over sets of independently matching nodes.

Consider:

```
has:
  all:
    - kind: number
    - kind: string
```

This requires one qualifying descendant to be both a number node and a string node. It does not express the requirement that the target contain one numeric descendant and one string descendant.

The latter requires separate relational predicates:

```
all:
  - has:
      kind: number
  - has:
      kind: string
```

Both `has` conditions are evaluated against the same outer target, but each can find a different qualifying child.

This distinction is important for declaratively recognizing structures containing multiple required components—for example, declarations containing several required statements, objects containing multiple properties, or functions containing different classes of expressions.

With the default `stopBy: neighbor`, these relations search the immediate structural neighborhood. `stopBy: end` extends the search through the relevant descendant or ancestor direction.

The broader pattern is that ast-grep expresses structural existential conditions through relational predicates and combines those conditions through composite rules. Its `all` and `any` operators should not be interpreted as general quantifiers over independently selected syntax-node collections.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 4.4 `field` availability differs among relational operators

The four relational operators share `stopBy`, but they do not have identical configuration surfaces.

| Relational operator | `stopBy`  | `field`       |
| ------------------- | --------- | ------------- |
| `inside`            | Supported | Supported     |
| `has`               | Supported | Supported     |
| `precedes`          | Supported | Not supported |
| `follows`           | Supported | Not supported |

The `field` option constrains grammatical relationships involving enclosing or contained syntax. It is not a general field restriction on arbitrary sibling searches.

This corrects an ambiguity in the original §4.2, which presents the two controls together without distinguishing their availability.

For sibling-based analysis requiring additional field constraints, the relevant conditions may need to be expressed through separate structural predicates rather than by placing `field` directly on `precedes` or `follows`.

Source: [https://ast-grep.github.io/reference/rule.html](https://ast-grep.github.io/reference/rule.html?utm_source=chatgpt.com)

## 5. Chained transformations and derived capture values

Extends original §6.3.

### 5.1 Transformations form ordered text-processing pipelines

The native `transform` mechanism supports sequential derivation: the output of one transformation can become the source of another.

This extends its usefulness beyond isolated case conversion or regex replacement.

For example:

```
from ast_grep_py import SgRootsource = "audit(debug_long_name)"config = {    "rule": {        "pattern": "audit($NAME)"    },    "transform": {        "UNPREFIXED": {            "replace": {                "source": "$NAME",                "replace": "^debug_",                "by": ""            }        },        "NORMALIZED": {            "convert": {                "source": "$UNPREFIXED",                "toCase": "camelCase"            }        }    }}root = SgRoot(source, "python").root()match = root.find(config)if match is not None:    normalized = match.get_transformed("NORMALIZED")    # Expected: "longName"
```

The first transformation removes a prefix from the captured identifier text. The second converts the derived value to camel case.

The underlying sequence is:

```
Captured syntax node
    debug_long_name
          │
          ▼
Regex replacement
    long_name
          │
          ▼
Case conversion
    longName
          │
          ▼
get_transformed("NORMALIZED")
```

The derived values are strings, not new AST nodes. They do not gain independent source ranges or structural relationships.

Importantly, the transformation chain is defined once within the matcher configuration rather than implemented through repeated Python callbacks over individual captures.

The official transformation documentation explicitly supports references to earlier transformed variables. The Python API exposes `transform` in `Config`, and upstream Python tests establish that transformed values can be retrieved through `get_transformed()`. The specific multi-stage example above is illustrative rather than an independently executed test.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



Sources:

[https://ast-grep.github.io/guide/rewrite/transform.html](https://ast-grep.github.io/guide/rewrite/transform.html?utm_source=chatgpt.com)

[https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/tests/test_rule.py](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/tests/test_rule.py?utm_source=chatgpt.com)

### 5.2 Regex capture groups are local to transformations

The `replace` transformation supports Rust-regex capture groups, including named groups such as `(?<NAME>...)`, which can be referenced in the corresponding replacement text.

These capture groups are distinct from structural metavariables.

For example:

```
transform:
  RENAMED:
    replace:
      source: $ORIGINAL
      replace: '^debug(?<SUFFIX>.*)$'
      by: 'release$SUFFIX'
```

Here, `ORIGINAL` is an ast-grep metavariable established by structural matching, while `SUFFIX` is a capture group belonging to the regular expression.

The regex capture is available to the `by` replacement within that transformation. It should not be assumed to become an independent structural capture accessible through `get_match("SUFFIX")`.

The atomic `regex` rule also does not export regex capture groups as structural metavariables.

These distinctions are relevant when choosing between structural extraction, regex-based text derivation, and Python-side postprocessing.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 5.3 Conditional text generation from variadic captures

A more subtle transformation technique is to derive optional text from the presence or absence of a variadic capture.

Consider:

```
transform:
  MAYBE_COMMA:
    replace:
      source: $$$ARGS
      replace: '^.+'
      by: ', '
```

When `$$$ARGS` is empty, the replacement produces no comma. When it contains text, the transformation generates the separator.

The broader ast-grep project uses this technique when adding arguments to calls: a separator is required only if existing arguments are present.

This provides a limited form of conditional text generation without a dedicated conditional-expression operator.

It is useful for constructing replacements whose punctuation depends on matched syntax, but it should not be mistaken for arbitrary branching logic. The result depends on the text of the captured sequence and the behavior of the regex transformation.

For Python callers, the derived value can be retrieved and incorporated into a programmatically constructed replacement string. The Python binding does not automatically interpolate CLI-style `fix` templates passed to `SgNode.replace()`.

Source: [https://ast-grep.github.io/guide/rewrite/transform.html](https://ast-grep.github.io/guide/rewrite/transform.html?utm_source=chatgpt.com)

### 5.4 Regex syntax and correctness limitations

Ast-grep's regex facilities use Rust's `regex` syntax rather than Python `re` or PCRE semantics.

Most importantly, the matching engine does not support arbitrary lookaround assertions or backreferences.

That limitation is relevant to both atomic regex predicates and regex replacement transformations.

A further distinction is that regex rules operate on source text, while structural metavariables represent syntax nodes. Regex-based transformations cannot guarantee that their output respects source-language token boundaries or identifier validity.

For example, normalizing an identifier through string replacement does not establish that the result is a valid identifier in the target language, nor that replacing it preserves symbol identity.

This reinforces the difference between declarative text transformation and semantic refactoring.

Sources:

[https://ast-grep.github.io/guide/rule-config/atomic-rule.html](https://ast-grep.github.io/guide/rule-config/atomic-rule.html?utm_source=chatgpt.com)

[https://ast-grep.github.io/reference/yaml/transformation.html](https://ast-grep.github.io/reference/yaml/transformation.html?utm_source=chatgpt.com)

## 6. Advanced ESQuery positional selection

Extends original §§4.3–4.4.

### 6.1 Positional selection over filtered siblings

Ast-grep's limited ESQuery-style `kind` syntax supports an `of` clause within `:nth-child`.

For example:

```
kind: array > :nth-child(1 of number)
```

This corresponds to a filtered positional rule:

```
all:
  - nthChild:
      position: 1
      ofRule:
        kind: number
  - inside:
      kind: array
```

Rather than selecting the first named child unconditionally, the positional predicate considers the sibling population filtered by the specified rule.

This is useful when a construct contains several kinds of children and an operation needs the first, last, or periodically positioned node of a particular category.

For example, an array containing mixed expressions can be inspected according to the positions of its numeric elements rather than their positions among all named children.

This is distinct from applying `kind: number` and `nthChild: 1` independently: the latter constrains the node's ordinary sibling position, while `ofRule` changes the population over which that position is calculated.

### 6.2 Reverse positional selection

The `:nth-last-child` selector corresponds to `nthChild` with reverse counting:

```
nthChild:
  position: 1
  reverse: true
```

It selects a node according to its position from the end of the relevant sibling population.

The `ofRule` filtering mechanism and reverse counting provide a compact native vocabulary for structural position queries that might otherwise require enumerating siblings and filtering them in Python.

These features remain constrained by the syntax-tree representation. In particular, `nthChild` counts named nodes, not arbitrary punctuation tokens.

The upstream Python type declarations do not fully represent the available object-form options; this distinction is addressed in §7 below.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



Source: [https://ast-grep.github.io/reference/rule/esquery](https://ast-grep.github.io/reference/rule/esquery?utm_source=chatgpt.com)

## 7. Runtime configuration versus Python type declarations

Extends original §§4.3, 6, and 8.2.

The published Python interface includes `TypedDict` declarations for rule configurations, contextual patterns, positional predicates, and custom-language registration.

These declarations aid static checking and discovery, but they are not always a complete or exact representation of the configuration accepted by the native Rust engine.

Several discrepancies are consequential.

| Python declaration | Important distinction                                                                                                                             |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Pattern`          | Its fields are declared in a non-`total=False` `TypedDict`, even though the underlying configuration permits optional `selector` and `strictness` |
| `NthChild`         | The declaration includes `nth`, `position`, and `ofRule`, but does not accurately reflect the documented optionality and omits `reverse`          |
| `Relation`         | Exposes `field` without distinguishing relational operators; the engine permits it only for `inside` and `has`                                    |
| `CustomLang`       | Omits the `extensions` property accepted by the native language-registration structure and used in upstream tests                                 |
| `Config`           | Exposes `rule`, `constraints`, `utils`, and `transform`, but not the complete set of fields available to CLI YAML configurations                  |

These are different categories of mismatch.

A type declaration may incorrectly require fields that are optional at runtime. It may also omit a runtime-supported field, or permit a property that is invalid for some members of a broader configuration family.

For example, the documented `nthChild` configuration supports:

```
{    "nthChild": {        "position": 1,        "reverse": True,        "ofRule": {            "kind": "identifier"        }    }}
```

The native rule vocabulary supports `reverse`, but the Python declaration does not expose it in the corresponding type.

This does not necessarily mean the runtime rejects the configuration. Conversely, a field appearing in a `TypedDict` does not establish that it is valid in every context where the type is used.

These distinctions can matter when using statically checked Python to construct sophisticated declarative matchers.

The authoritative evidence is distributed across the published Python API, the configuration deserializer, upstream tests, and the relevant engine documentation. Runtime behavior should be interpreted in the context of a particular package release rather than assumed from development-branch typing alone.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Sources:

[https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/\_\_init\_\_.py](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/__init__.py?utm_source=chatgpt.com)

[https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/tests/test_register_lang.py](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/tests/test_register_lang.py?utm_source=chatgpt.com)

[https://ast-grep.github.io/reference/rule.html](https://ast-grep.github.io/reference/rule.html?utm_source=chatgpt.com)

## 8. Version-sensitive custom-language behavior and source coordinates

Extends original §§2.2 and 8.3.

### 8.1 Metavariable expansion changes in 0.51.1

Ast-grep 0.51.1 includes a correction to dynamic-language pattern expansion: expansion now replaces metavariable sigils rather than indiscriminately replacing occurrences of the configured character.

This matters to custom-language parsers that rely on `meta_var_char` and `expando_char`.

Such configurations exist to accommodate grammars whose lexical rules cannot directly parse the default metavariable notation. The expansion mechanism therefore participates in the interpretation of source-language patterns.

The 0.51.1 correction addresses how the engine distinguishes metavariable syntax from ordinary source text during expansion.

Its relevance is greatest when a custom grammar uses syntax containing characters that overlap with the metavariable sigil. Incorrect expansion can alter the input passed to the language parser and consequently change the resulting effective pattern.

The release change should be understood as a correction to existing functionality, not a new Python binding API.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Sources:

[https://github.com/ast-grep/ast-grep/releases/tag/0.51.1](https://github.com/ast-grep/ast-grep/releases/tag/0.51.1?utm_source=chatgpt.com)

[https://ast-grep.github.io/advanced/custom-language.html](https://ast-grep.github.io/advanced/custom-language.html?utm_source=chatgpt.com)

### 8.2 Interoperability among character, byte, and UTF-16 source positions

The original guide correctly notes that the Python binding exposes Unicode-character offsets rather than raw Tree-sitter byte offsets.

An additional integration distinction is that external tools may use different coordinate representations.

| Coordinate system         | Typical context                                              | Consequence                                                                      |
| ------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| Unicode code-point index  | Python source-string indexing and ast-grep-py edit positions | Multibyte UTF-8 characters count as one code point                               |
| UTF-8 byte offset         | Native Tree-sitter and byte-oriented source infrastructure   | Non-ASCII characters can occupy multiple bytes                                   |
| UTF-16 code-unit position | Common language-server and editor protocol representation    | Characters outside the Basic Multilingual Plane occupy two code units            |
| Line/column coordinates   | Syntax ranges and compiler diagnostics                       | Column interpretation must be reconciled with the producer's encoding convention |

For ASCII-only source, these representations frequently coincide. With non-ASCII input, they can diverge.

Consider:

```
source = "a😀b"
```

The `b` begins at code-point index 2 in Python. In UTF-8, it begins at byte offset 5. In UTF-16, it follows three code units.

The distinction matters when correlating ast-grep matches with diagnostics, applying external edits, or storing source locations produced by different analysis engines.

The binding's native implementation maintains a `UnicodePosition` conversion structure that maps between character and byte offsets. That does not establish automatic conversion to every external coordinate convention.

Coordinates must also refer to the same source snapshot. Even correctly converted offsets can identify the wrong syntax after earlier source modifications.

Source: [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/unicode_position.rs](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/unicode_position.rs?utm_source=chatgpt.com)

## 9. Combined architectural significance

The capabilities developed in this addendum are especially valuable when used together.

A declarative `Config` can combine a structurally precise pattern, relational context, captures from several syntax locations, recursive utility predicates, metavariable constraints, and chained text transformations.

Conceptually, the resulting analysis operation is:

```
Parse source into syntax tree
            │
            ▼
Select effective pattern node
            │
            ▼
Evaluate structural predicates
  • target syntax
  • ancestors / descendants
  • sibling relationships
  • recursive utility rules
            │
            ▼
Accumulate metavariable captures
            │
            ▼
Apply capture constraints
            │
            ▼
Derive transformed string values
            │
            ▼
Return matching syntax nodes
and associated captured information
```

This composition can replace substantial custom machinery for recognizing recursively nested structures, correlating local syntax, extracting named components, filtering captures, and normalizing extracted text.

Its principal architectural advantage is that several related operations can remain within the native Rust matcher instead of requiring repeated extraction and Python-side inspection of intermediate nodes.

The benefit is conditional on how much of the analysis can genuinely be represented through ast-grep's structural rule vocabulary. Highly dynamic predicates, cross-file correlation, arbitrary aggregation, symbol resolution, and semantic reasoning remain outside that vocabulary.

The resulting abstraction is best understood as a composable structural recognition and extraction engine, with limited native text derivation, rather than a general semantic-analysis framework.

This addendum establishes the additional expressiveness available from that composition while preserving the original guide's distinction between structural recognition, source transformation, and semantic program analysis.

# ast-grep-py — Addendum: Python Binding Semantics, Cross-Structural Matching, Parse Diagnostics, and Edit Correctness

Target version: 0.51.2\
Research date: November 13, 2026\
Supplements: ast-grep-py — Comprehensive Python Library Overview (0.51.0) and its November 7, 2026 addendum (0.51.1)

## Scope and version context

This addendum documents additional behavior and capability interactions in the `ast-grep-py` Python binding, focusing on distinctions that affect structural query correctness, capture management, rule composition, parse validity, and source transformation.

The most consequential distinction is between Python node-refinement methods and declarative relational rules. Although both operate through the Rust-based ast-grep engine, they do not necessarily search the same structural neighborhood. Another important distinction concerns the separation of syntax-node identity from the metavariable environment produced by a particular match.

The addendum targets `ast-grep-py` 0.51.2, published November 11, 2026. The release includes a correction to identifier case conversion involving digits, as well as updates to underlying dependencies and grammar infrastructure. It does not introduce a new family of Python binding APIs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



The explanations below distinguish documented public behavior from observations of upstream implementation. Code examples are illustrative and have not been independently executed against the 0.51.2 wheel.

Primary references:

- Release: [https://github.com/ast-grep/ast-grep/releases/tag/0.51.2](https://github.com/ast-grep/ast-grep/releases/tag/0.51.2?utm_source=chatgpt.com)
- Python package: [https://pypi.org/project/ast-grep-py/0.51.2/](https://pypi.org/project/ast-grep-py/0.51.2/?utm_source=chatgpt.com)
- Python binding implementation: [https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_node.rs](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_node.rs?utm_source=chatgpt.com)
- Python API: [https://ast-grep.github.io/guide/api-usage/py-api.html](https://ast-grep.github.io/guide/api-usage/py-api.html?utm_source=chatgpt.com)

## 1. Imperative node refinement versus declarative relational matching

Extends original §§4.2 and 5.1.

### 1.1 Two interfaces with different traversal semantics

Ast-grep provides relational matching through both the Python `SgNode` methods and nested declarative `Rule` objects.

The operations appear similar, but their default search scopes are different.

| Operation     | Python `SgNode` refinement                   | Declarative relational rule                                |
| ------------- | -------------------------------------------- | ---------------------------------------------------------- |
| `inside`      | Searches successive ancestors up to the root | Immediate parent by default                                |
| `has`         | Searches descendants recursively             | Immediate children by default                              |
| `precedes`    | Searches subsequent siblings                 | Immediate following sibling by default                     |
| `follows`     | Searches preceding siblings                  | Immediate preceding sibling by default                     |
| Depth control | Traversal behavior is built into the method  | `stopBy` controls traversal extent                         |
| Result        | `bool`                                       | Contributes to a matched rule and potentially its captures |

The Python binding delegates `inside`, `has`, `precedes`, and `follows` to corresponding Rust core methods. Their implementations use `ancestors()`, depth-first descendant traversal, `next_all()`, and `prev_all()`, respectively.

The declarative rule engine instead defaults `stopBy` to `"neighbor"`. Using `"end"` extends the search toward the relevant structural boundary. A rule-valued `stopBy` can establish a grammar-defined termination condition.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.rs\&sz=32)

source+2



This distinction means that the following two queries need not produce equivalent results.

```
from ast_grep_py import SgRoot

source = """
def compute(x):
    if x > 0:
        return x
"""

root = SgRoot(source, "python").root()
function = root.find(kind="function_definition")

if function is not None:
    # Recursively examines descendants.
    contains_return = function.has(kind="return_statement")

# Declarative rule: immediate-child search by default.
shallow = {
    "rule": {
        "kind": "function_definition",
        "has": {"kind": "return_statement"},
    }
}

# Declarative rule: recursive descendant search.
deep = {
    "rule": {
        "kind": "function_definition",
        "has": {
            "kind": "return_statement",
            "stopBy": "end",
        },
    }
}

shallow_matches = root.find_all(shallow)
deep_matches = root.find_all(deep)

```

The function contains a `return_statement`, but that statement is nested inside the function's body and an `if_statement`. The imperative method searches that deeper structure; the first declarative rule does not.

The second declarative rule uses `stopBy: "end"` to search descendants recursively, producing the corresponding structural containment behavior.

### 1.2 Traversal direction and target-node identity

An additional consequence is that relational predicates always operate relative to a designated target node.

For example, `has` does not change the node being selected. It establishes that a node satisfying the principal rule contains another qualifying syntax node.

Similarly, `inside` constrains a target using an enclosing node, but does not change the reported match into that enclosing node.

This matters when the selected node is subsequently used for capture extraction, source-range reporting, or replacement.

Consider a rule that identifies a function containing a particular call. The result represents the function node, not the contained call node. The contained call may be available through a metavariable capture, but the primary match remains the function.

Using `stopBy: "end"` changes the search distance, not the identity of the primary target.

### 1.3 Boolean refinement and capture availability

The Python refinement methods return Boolean results. Their matcher evaluations do not return capture-bearing match objects.

For example:

```
contains_call = function.has(
    pattern="process($ARG)"
)

```

This determines whether a qualifying call exists; it does not provide a separate `SgNode` representing the successful nested match or expose the captured `ARG` value.

When a structural relationship and its captures must be retained together, the appropriate interface is a declarative configuration passed to `find()` or `find_all()`.

This yields an important division of responsibility:

Imperative refinement is suitable for Boolean structural tests on an existing node, including naturally recursive ancestor and descendant checks.

Declarative relational matching is suitable when traversal depth, grammatical fields, multiple structural predicates, metavariable bindings, and transformations should be expressed as one matcher.

Neither interface subsumes the other completely. Their different traversal defaults and result models should be preserved when translating between them.

Sources:

[https://docs.rs/ast-grep-core/latest/src/ast_grep_core/node.rs.html](https://docs.rs/ast-grep-core/latest/src/ast_grep_core/node.rs.html?utm_source=chatgpt.com)

[https://ast-grep.github.io/guide/rule-config/relational-rule.html](https://ast-grep.github.io/guide/rule-config/relational-rule.html?utm_source=chatgpt.com)

[https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_node.rs](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_node.rs?utm_source=chatgpt.com)

## 2. Match environments, capture ownership, and node navigation

Extends original §§5.2–5.4.

### 2.1 A successful match contains more than a syntax-node reference

An `SgNode` returned by a successful structural search represents a syntax node together with an environment containing information established during matching.

This environment may contain single-node metavariable captures, variadic captures, and transformed string values.

The Rust binding represents the underlying node through `NodeMatch`, which distinguishes the selected syntax node from the environment associated with its particular successful match.

The distinction is important because a syntax node does not intrinsically own one universal set of metavariable captures.

A single node can satisfy multiple matcher configurations. Different configurations can bind different metavariables, apply different constraints, or derive different transformations without changing the underlying syntax tree.

The same source location can therefore participate in multiple match environments.

### 2.2 Navigation constructs new node wrappers without inheriting the original environment

The Python binding's traversal operations create new `SgNode` wrappers for the syntax nodes they return.

Methods including `parent()`, `child()`, `children()`, `field()`, `field_children()`, and `ancestors()` construct wrappers around the corresponding structural nodes.

The implementation of `get_match()` also converts the captured syntax node into a separate `NodeMatch` using `NodeMatch::from(...)`.

Consequently, these operations preserve access to syntax structure, but do not automatically propagate the original match environment into the returned node.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



For example:

```
from ast_grep_py import SgRoot

root = SgRoot("print(value)", "python").root()
match = root.find(pattern="print($ARG)")

if match is not None:
    argument = match.get_match("ARG")

    if argument is not None:
        # The argument is a navigable syntax node.
        name = argument.text()
        kind = argument.kind()
        parent = argument.parent()

        # The captured node does not inherit the
        # original match's ARG binding.
        inherited = argument.get_match("ARG")
        assert inherited is None

```

The original `match` remains the appropriate object from which to retrieve `ARG`.

A separate structural navigation operation may return the same underlying syntax node, but not the original matcher-specific environment.

This is different from systems in which semantic annotations or query bindings are stored globally on syntax-tree objects.

### 2.3 Syntactic identity and match identity are separate concepts

There are three useful conceptual identities:

| Identity                | Meaning                                                              | Stability                                      |
| ----------------------- | -------------------------------------------------------------------- | ---------------------------------------------- |
| Syntax-node identity    | A particular node within a parsed syntax tree                        | Associated with the parse snapshot             |
| Match identity          | A successful application of a particular matcher to a target node    | Depends on the matcher and capture environment |
| Durable source identity | An externally assigned identity for an entity across source versions | Not supplied natively by ast-grep-py           |

Two match results can refer to equivalent or identical syntax nodes while carrying different captures. Conversely, different syntax nodes can satisfy the same pattern without representing the same program entity.

The Python binding's equality and hashing behavior is based on underlying node identifiers, not on the complete capture environment.

Therefore, equality of `SgNode` objects should not be interpreted as equality of their matching configurations, derived values, or semantic meanings.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



This distinction is particularly important when storing structural matches in dictionaries, sets, indexes, or persistent analysis records.

For example, deduplicating matches solely by syntax-node identity may discard different analytical facts established by different rules.

### 2.4 Architectural significance

Separating syntax nodes from match environments allows the same parsed source tree to support multiple independent structural analyses without mutating its nodes to attach rule-specific information.

This resembles a query-result model in which the result contains both a selected entity and contextual bindings.

For systems constructing structured facts from source, the meaningful record may therefore contain the target node's source identity, the rule or configuration used to select it, and the relevant captures or transformed values.

That representation is an architectural possibility rather than a feature automatically managed by the Python binding.

The principal lesson is that structural navigation and match-result extraction are complementary, but not interchangeable, operations.

Source:

[https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_node.rs](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_node.rs?utm_source=chatgpt.com)

## 3. Cross-structural capture unification

Extends original addendum §4.

### 3.1 Captures can constrain later predicates at different syntax locations

The original addendum establishes that relational rules can contribute metavariable captures and that `all` can control predicate evaluation order.

A further consequence is that a metavariable captured by one predicate can constrain a later predicate that examines a different part of the syntax tree.

Ast-grep's matching environment supports this form of cross-structural consistency.

The engine processes matching predicates and retains bindings established by earlier successful rules. When a later rule encounters the same metavariable, it must respect the previously bound value rather than establishing an unrelated capture.

Upstream demonstrates this with a JavaScript rule identifying functions containing a syntactically matching call to their own name.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 3.2 Example: matching a function with a syntactic self-call

```
from ast_grep_py import SgRoot

source = """
function calculate() {
    helper();
    calculate();
}
"""

root = SgRoot(source, "javascript").root()

config = {
    "rule": {
        "all": [
            {
                "pattern": "function $F() { $$$ }"
            },
            {
                "has": {
                    "pattern": "$F()",
                    "stopBy": "end",
                }
            },
        ]
    }
}

matches = root.find_all(config)

for match in matches:
    function_name = match.get_match("F")
    if function_name is not None:
        print(function_name.text())

```

The first rule recognizes a function declaration and binds `F` to its declared name.

The second rule searches the function's descendants for a call whose function-name syntax is consistent with that same binding.

The explicit `all` list ensures that the declaration pattern is evaluated before the descendant predicate.

The function body also contains `helper()`, but that call cannot independently redefine `F` after the declaration pattern has established its binding.

A direct consequence is that ast-grep can enforce this syntactic relationship during matching instead of returning all functions and all calls for subsequent Python-side comparison.

### 3.3 This is structural unification, not semantic identity resolution

The resulting relationship is stronger than collecting unrelated captures, but weaker than proving recursive function invocation.

For example, a function may contain a local variable that shadows its own name, or use language constructs that alter the binding of an identifier.

Ast-grep can recognize the textual and structural correspondence between a declaration name and a call expression. It does not establish that the call resolves to that declaration.

This distinction matters for source indexing and diagnostics. A structural self-call predicate can identify likely recursive functions, but it cannot independently establish a compiler-equivalent call graph.

The feature is best understood as matcher-enforced syntactic unification across structurally related nodes.

### 3.4 Evaluation order can change whether unification succeeds

Consider reversing the two rules:

```
config = {
    "rule": {
        "all": [
            {
                "has": {
                    "pattern": "$F()",
                    "stopBy": "end",
                }
            },
            {
                "pattern": "function $F() { $$$ }"
            },
        ]
    }
}

```

Now the descendant predicate can establish `F` using the first qualifying call it encounters.

If that call is `helper()`, the later declaration pattern must respect `F = helper`, even when the function's actual name is `calculate`.

The engine does not automatically backtrack over arbitrary alternative bindings to find the best globally consistent assignment.

Thus, `all` is more than a Boolean conjunction when its predicates establish or consume metavariable bindings. Its order can affect the successful matching path.

Upstream explicitly documents this distinction and recommends ordered `all` rules when capture dependencies matter.

Source:

[https://ast-grep.github.io/advanced/faq.html](https://ast-grep.github.io/advanced/faq.html?utm_source=chatgpt.com)

## 4. Parse-error metadata and the boundary of Python syntax inspection

Extends original §2.1.

### 4.1 A recoverable syntax tree is not a complete parse-validity report

Tree-sitter can represent malformed source through error recovery rather than failing to produce a syntax tree.

This is valuable when inspecting incomplete source, but it creates a distinction between obtaining a tree and knowing whether that tree represents syntactically valid input.

The Rust ast-grep core exposes several node-inspection capabilities that help distinguish normal syntax from parser recovery artifacts.

| Rust core method | Meaning                                                           | Python `SgNode` availability |
| ---------------- | ----------------------------------------------------------------- | ---------------------------- |
| `is_error()`     | Tests whether a node is an explicit parser error node             | Not exposed                  |
| `is_missing()`   | Tests whether a node represents syntax inserted by error recovery | Not exposed                  |
| `is_extra()`     | Tests whether a node is classified as extra syntax by its grammar | Not exposed                  |
| `kind_id()`      | Returns the grammar-specific numeric syntax kind                  | Not exposed                  |
| `kind()`         | Returns the grammar-specific kind name                            | Exposed                      |
| `is_named()`     | Distinguishes named from unnamed syntax nodes                     | Exposed                      |
| `range()`        | Returns the node's source location                                | Exposed                      |

These distinctions are established by the Rust core's `Node` implementation and the Python binding's exported methods.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.rs\&sz=32)

source+2



### 4.2 Explicit errors and missing syntax represent different recovery mechanisms

An explicit Tree-sitter error node records source text that the parser could not incorporate into a valid grammatical structure.

Missing syntax is different. The parser may insert an expected token or construct into its recovered representation even though the corresponding text is absent from the original source.

For example, a parser may recover from an incomplete expression by representing a missing expected token instead of treating the entire surrounding construct as one error node.

These recovery forms have different implications.

An explicit error node usually corresponds to a problematic source region. A missing node instead represents a grammatical expectation not satisfied by the supplied source.

Detecting only nodes with kind `ERROR` is therefore not equivalent to examining all error-recovery metadata.

An important additional distinction is that Tree-sitter's classification of extra nodes is not itself an error indicator. Grammars can designate ordinary comments or other syntax as extras. The presence of extra nodes must not automatically be interpreted as malformed source.

### 4.3 What the Python binding can establish

Python callers can inspect node kinds, ranges, named and unnamed children, and surrounding syntax.

Where Tree-sitter exposes an explicit `ERROR` node through the normal syntax tree, its kind can be recognized using `kind()`.

However, the Python binding does not expose the complete set of parser-status predicates provided by the Rust core.

Consequently, a Python-side traversal that searches for error-kind nodes cannot generally establish the absence of missing syntax or reproduce all parser-level validity checks.

This has implications for structural matching against incomplete code. A pattern may successfully match a recovered subtree even though some surrounding syntax is invalid or incomplete.

An analyzer must distinguish the validity of a structural match from the validity of the source file containing it.

### 4.4 Integration boundary

For operations requiring complete parser-recovery diagnostics, the lower-level Python `tree_sitter` bindings or an appropriate language-specific parser can provide functionality beyond `ast-grep-py`.

That integration requires attention to grammar compatibility and source snapshots. Two parser interfaces using different grammar versions can construct different trees for identical source text.

Using an additional parser also creates an information-coordination boundary: syntax nodes obtained from separate parses do not automatically share identity, even when their source ranges coincide.

The additional parser may therefore improve diagnostic completeness, but it is not a transparent extension of the existing `SgNode` objects.

The precise characterization is that ast-grep-py provides useful syntax-tree inspection and error-tolerant matching, but not a complete Python interface to Tree-sitter's parser-recovery metadata.

Sources:

[https://docs.rs/ast-grep-core/latest/src/ast_grep_core/node.rs.html](https://docs.rs/ast-grep-core/latest/src/ast_grep_core/node.rs.html?utm_source=chatgpt.com)

[https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/ast_grep_py.pyi](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/ast_grep_py.pyi?utm_source=chatgpt.com)

[https://tree-sitter.github.io/tree-sitter/](https://tree-sitter.github.io/tree-sitter/?utm_source=chatgpt.com)

## 5. Positive-rule requirements and Python-specific rule construction

Extends original §4.1.

### 5.1 A valid rule requires a positive structural restriction

Ast-grep's rule reference specifies that a rule must contain at least one positive predicate.

A positive predicate restricts the syntax kinds that can satisfy the rule.

The distinction is particularly relevant to the atomic rule vocabulary.

| Predicate | Structural positivity                                          | Reason                                                                    |
| --------- | -------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `kind`    | Positive                                                       | Restricts the target to specified syntax kinds                            |
| `pattern` | Positive                                                       | Its effective pattern node establishes a syntax kind                      |
| `regex`   | Not positive on its own                                        | Can match text belonging to arbitrary syntax kinds                        |
| `not`     | Does not independently establish a positive target restriction | Negates another predicate rather than selecting an eligible syntax family |

Other rule constructs can derive their validity through the positive subrules they contain.

This is more than a performance consideration. A broad textual predicate does not necessarily establish a valid structural search rule simply because it contains a useful regular expression.

The official rule reference explicitly requires positivity and identifies `regex` as nonpositive.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



For example, an identifier restricted by a textual naming convention can be expressed as:

```
rule = {
    "kind": "identifier",
    "regex": r"^debug_",
}

matches = root.find_all(**rule)

```

Here, `kind` selects the eligible syntax category while `regex` refines it according to the identifier's source text.

This produces a different matcher from an unconstrained textual search over arbitrary syntax nodes.

The structural restriction also allows the engine to exploit AST-kind-based candidate selection.

### 5.2 Negation requires mapping-based syntax in Python

The `not` composite operator is supported by the Python rule configuration, but Python's `not` keyword cannot be used as a normal keyword argument.

The exported typing definitions account for this using a `TypedDict` with an explicit `"not"` key.

An illustrative configuration is:

```
rule = {
    "pattern": "print($ARG)",
    "not": {
        "inside": {
            "kind": "function_definition",
            "stopBy": "end",
        }
    },
}

matches = root.find_all(**rule)

```

This selects calls matching `print($ARG)` that are not enclosed by a Python function definition.

The positive `pattern` establishes the target syntax; the negated relation excludes candidates in the specified structural context.

An important distinction from ordinary Python Boolean expressions is that negation participates in the native matcher environment. In particular, successful negation does not establish captures from the predicate that failed to match.

That behavior matters when later rules depend on metavariables introduced by earlier predicates.

The Python rule-construction interface supports this declarative logic, but the host language's keyword syntax requires an explicit mapping for the `not` operator.

Sources:

[https://ast-grep.github.io/reference/rule.html](https://ast-grep.github.io/reference/rule.html?utm_source=chatgpt.com)

[https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/\_\_init\_\_.py](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/ast_grep_py/__init__.py?utm_source=chatgpt.com)

## 6. Edit application: source generation versus verified transformation completeness

Extends original §7.3.

### 6.1 `commit_edits()` does not provide an edit-application report

The Python binding's edit API separates edit construction from source generation.

`replace()` creates a source-span edit, while `commit_edits()` produces rewritten source text from a collection of edits.

The latter does not return a structured account of which edits succeeded, were skipped, or conflicted.

In the implementation reviewed, `commit_edits()` sorts edits by their starting positions, converts Python character offsets into byte offsets, and processes the edits against the original source representation.

When an edit begins before the end of the region already consumed by an earlier edit, it is skipped. The function ultimately returns a string.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



This means that successful return from `commit_edits()` establishes that rewritten text was generated, not that every requested edit was incorporated.

### 6.2 Transformation completeness requires additional invariants

For a source-transformation system that needs to prove complete application of its planned edits, several properties must be distinguished.

| Property                     | Meaning                                                           | Native guarantee      |
| ---------------------------- | ----------------------------------------------------------------- | --------------------- |
| Edit creation                | A source node can produce a replacement edit                      | Supported             |
| Source-coordinate conversion | Python character offsets are converted for native processing      | Supported             |
| Non-overlapping application  | Nonconflicting edits can be composed into output text             | Supported             |
| Conflict detection           | Every overlapping or competing edit is reported                   | Not exposed           |
| Applied-edit accounting      | The caller receives a count or identity of applied edits          | Not exposed           |
| Source-snapshot consistency  | Every edit is known to originate from the intended source version | Caller responsibility |
| Output syntactic validity    | Rewritten text parses as valid code                               | Not guaranteed        |
| Output semantic correctness  | The edit preserves intended program behavior                      | Not guaranteed        |

The key architectural distinction is between a transformation engine that generates source and a transaction-like system that verifies the complete execution of a set of requested modifications.

Ast-grep-py provides the former capability.

### 6.3 Interval validation and conflict ordering

Edits identify half-open source intervals:

\\[ [start,\ end) \\]

Two ordinary replacement intervals overlap when:

\\[ \max(start_1,start_2)<\min(end_1,end_2) \\]

A sequence of ordinary replacements can be checked for overlap after sorting by starting position.

However, zero-length insertions introduce an additional distinction. Multiple insertions at the same source offset do not occupy overlapping nonempty intervals, yet their relative ordering can affect the resulting source text.

Therefore, a generic interval-overlap test is not sufficient to establish deterministic edit composition for every possible edit set.

Similarly, edits targeting enclosing and nested syntax nodes cannot generally be applied independently to the same source snapshot without a conflict policy.

Possible policies include outermost-match precedence, innermost-match precedence, explicit rule priority, or multiple transformation passes with reparsing between passes.

These are ways an external system can resolve conflicts; they are not automatically provided by `commit_edits()`.

### 6.4 Source snapshots are part of edit correctness

The offsets used by an `Edit` refer to the original source snapshot.

This remains important even when the edits themselves have valid, nonoverlapping intervals.

Suppose an edit is generated against source version A, then an unrelated transformation produces source version B. Applying the old edit offsets to B may modify the wrong syntax even if the offsets remain within the new string's bounds.

The Python binding does not attach a durable external source-version identifier to each edit.

An application requiring snapshot consistency must therefore associate the edits with the correct source representation outside the binding.

This is particularly important when edits are generated by several independent analyses or collected across multiple stages.

### 6.5 Architectural significance

A reliable structural transformation system can distinguish three stages conceptually:

Recognition: identify the syntax nodes and establish the captures needed to construct replacements.

Edit composition: resolve conflicts, validate source intervals, and determine an unambiguous set of edits for one source snapshot.

Post-edit validation: examine the generated source using the syntax or semantic checks appropriate to the transformation.

Ast-grep-py can perform substantial work in recognition and source generation, including native matching and precise text-preserving replacements.

It does not make the middle and final stages unnecessary.

The distinction explains why a structural codemod can be syntactically targeted and source-preserving while still requiring explicit completeness and correctness checks.

Source:

[https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_node.rs](https://github.com/ast-grep/ast-grep/blob/main/crates/pyo3/src/py_node.rs?utm_source=chatgpt.com)

## 7. Identifier transformation: separator semantics and version-sensitive digit handling

Extends original §6.3.

### 7.1 Separator-sensitive conversion is a word-segmentation operation

Ast-grep's `convert` transformation does more than change the capitalization of a string.

For the separator-sensitive conversion targets, it first segments the input into words, transforms those words, and rejoins them according to the target case.

The `separatedBy` property controls which input boundaries participate in that segmentation.

The documented separator vocabulary is:

| Separator    | Boundary recognized                                            |
| ------------ | -------------------------------------------------------------- |
| `Dash`       | Hyphen (`-`)                                                   |
| `Dot`        | Period (`.`)                                                   |
| `Space`      | Space                                                          |
| `Slash`      | Forward slash (`/`)                                            |
| `Underscore` | Underscore (`_`)                                               |
| `CaseChange` | Transitions involving lowercase and uppercase letter sequences |

By default, the documented transformation uses all available separator types. A caller can provide a narrower `separatedBy` list to restrict segmentation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



This is especially useful when punctuation or capitalization has a domain-specific meaning that should not be normalized away.

### 7.2 Case-change boundaries recognize acronym transitions

`CaseChange` recognizes more than the simple transition between lowercase and uppercase letters.

It also detects an acronym-like uppercase sequence followed by a capitalized word.

For example, the documented algorithm recognizes:

```
XMLHttpRequest
    ↓
XML | Http | Request
```

This distinction matters because a naïve strategy that splits only before every uppercase character would fragment the acronym into individual letters.

The native transformation can therefore handle several common naming conventions without requiring a custom Python regular expression for each case.

However, this remains a text-based transformation. It does not know whether a particular identifier is an acronym, a symbol with special capitalization, or a name whose spelling should be preserved for semantic reasons.

### 7.3 Separation is configurable; case conversion is not uniformly separator-sensitive

`lowerCase`, `upperCase`, and `capitalize` are documented as non-separator-sensitive operations.

By contrast, `camelCase`, `snakeCase`, `kebabCase`, and `pascalCase` use word segmentation.

This distinction is important because specifying separators is meaningful only for conversion operations that actually split the source into words.

For example:

```
config = {
    "rule": {
        "pattern": "process($NAME)"
    },
    "transform": {
        "NORMALIZED": {
            "convert": {
                "source": "$NAME",
                "toCase": "snakeCase",
                "separatedBy": ["underscore"],
            }
        }
    }
}

```

In this configuration, the transformation is explicitly restricted to underscore-based segmentation rather than using all default separator forms.

The resulting transformed value is still a string derived from the matched source, not a new syntax node.

### 7.4 The 0.51.2 digit-boundary correction

Ast-grep 0.51.2 includes a fix for incorrect word splitting when digit sequences precede lowercase letters.

The upstream change identifies cases such as:

```
Input:            sha256sum
Previous result:  sha25_6sum
Corrected result: sha256sum
```

The earlier implementation could incorrectly treat the final digit of a sequence as though it were part of an uppercase acronym boundary.

The correction restricts the relevant acronym-splitting condition so that it applies only when the preceding character is actually uppercase.

The change does not simply disable splitting around digits. The upstream fix preserves other intended transitions involving identifiers such as `2FAEnabled`, `HTTP2Server`, and `base64Encode`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



This is a version-sensitive correctness improvement for identifier-normalization workflows.

The relevant capability already existed in earlier releases; 0.51.2 corrects its behavior for particular inputs rather than introducing a new transformation operator.

Sources:

[https://ast-grep.github.io/reference/yaml/transformation.html](https://ast-grep.github.io/reference/yaml/transformation.html?utm_source=chatgpt.com)

[https://github.com/ast-grep/ast-grep/pull/3070](https://github.com/ast-grep/ast-grep/pull/3070?utm_source=chatgpt.com)

[https://github.com/ast-grep/ast-grep/releases/tag/0.51.2](https://github.com/ast-grep/ast-grep/releases/tag/0.51.2?utm_source=chatgpt.com)

## 8. Additional Python inspection and distribution details

Extends original §§5.3, 5.4, and 9.

### 8.1 Native Python string representations

The binding implements `SgNode.__str__()` and `SgNode.__repr__()`.

The string representation reports the syntax kind and source range.

The representation used by `repr()` also includes a shortened preview of the node's source text.

These methods provide lightweight diagnostics for interactive inspection and debugging without requiring callers to retrieve each property separately.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



For example, an `SgNode` can be inspected using ordinary Python expressions:

```
print(node)
print(repr(node))

```

These representations are intended for inspection rather than structured serialization.

Their formatting is an implementation detail and should not be treated as a stable interchange format for downstream parsers or persistent indexes.

### 8.2 `is_named_leaf()` is not equivalent to combining `is_named()` and `is_leaf()`

The Rust core explicitly distinguishes `is_named_leaf()` from the Boolean expression:

```
node.is_named() and node.is_leaf()
```

The former concerns the node's named-child structure, whereas `is_leaf()` concerns the absence of children in general.

A syntax node can have unnamed grammar tokens as children while having no named child nodes.

Therefore, these predicates should not be substituted for one another when extracting terminal-like syntax elements or building normalized structural representations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.rs\&sz=32)

source



Source:

[https://docs.rs/ast-grep-core/latest/src/ast_grep_core/node.rs.html](https://docs.rs/ast-grep-core/latest/src/ast_grep_core/node.rs.html?utm_source=chatgpt.com)

### 8.3 Python 3.15 distribution availability

The 0.51.2 release includes CPython 3.15-specific wheel distributions, extending the package's published binary compatibility beyond the Python versions described in the original guide.

This is a distribution capability rather than a new runtime API.

Availability should be assessed by interpreter and platform combination rather than by assuming that the presence of a wheel for one Python version guarantees corresponding wheels for every operating system and architecture.

The published release files remain the authoritative source for those combinations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



Source:

[https://pypi.org/project/ast-grep-py/0.51.2/#files](https://pypi.org/project/ast-grep-py/0.51.2/?utm_source=chatgpt.com#files)

### 8.4 Keep Python coordinates distinct from CLI language-server changes

The 0.51.2 ast-grep release also includes a fix to report language-server columns in UTF-16 code units.

That change concerns the CLI's language-server functionality and should not be interpreted as changing the Python binding's source-coordinate model.

The Python `Range` and `Edit` behavior described in the existing guide continues to distinguish Unicode character offsets from Tree-sitter's internal byte offsets.

This is a useful example of why release changes in the shared ast-grep project must be attributed to the appropriate interface.

Source:

[https://github.com/ast-grep/ast-grep/releases/tag/0.51.2](https://github.com/ast-grep/ast-grep/releases/tag/0.51.2?utm_source=chatgpt.com)

## 9. Combined architectural significance

The additional semantics in this addendum clarify several important boundaries within ast-grep-py's structural-analysis model.

Declarative matching is more than a search predicate. It can enforce relationships across syntax locations, reuse metavariable bindings, and accumulate capture information within one matcher evaluation.

Syntax-tree navigation is independent of matcher-specific information. Nodes obtained through navigation remain structurally useful, but do not automatically inherit capture environments from earlier matches.

Structural matching is not parse validation or semantic analysis. Tree-sitter's error recovery permits analysis of incomplete sources, while the Python binding exposes only part of the underlying parser-status information.

Source editing is not transactional transformation. The binding can construct and apply precise edits, but does not independently establish complete application, deterministic conflict resolution, or post-edit correctness.

These distinctions reveal opportunities to place substantial structural recognition and extraction work inside the native ast-grep matcher while keeping genuinely separate responsibilities—such as source-version management, semantic identity resolution, and transformation validation—outside it.

The result is a more precise understanding of ast-grep-py as a composable structural query and source-rewriting engine, with a Python interface whose semantics must be understood independently from both the Rust core's complete capabilities and the ast-grep CLI.