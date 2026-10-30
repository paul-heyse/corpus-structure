# ast-grep — Comprehensive System Tool Reference

Target: ast-grep CLI v0.45.3 | Research date: October 30, 2026 | Ecosystem: Rust, Tree-sitter, CLI, YAML rule engine

## 1. Executive orientation

ast-grep is a structural code-search, analysis, linting, and transformation system built on Tree-sitter syntax trees. It makes source-code structure a directly queryable and transformable substrate without requiring a language compiler, a language server, or a custom parser implementation.

Its distinctive capability is combining syntax-aware matching, composable structural predicates, captured metavariables, and source-preserving rewriting within a declarative rule system.

Rather than only identifying strings or regular-expression matches, ast-grep can identify code constructs according to their syntactic identity and relationships: a particular kind of call, an expression inside a function, a declaration containing another construct, or a syntax node matching a combination of conditions.

The system extends beyond search into declarative linting, codemods, source-code outlining, rule testing, structured machine-readable results, and editor integration.

Version status: v0.45.3 is the latest stable GitHub release identified during research, published August 31, 2026. Version 0.45.0 deprecated the shorter `sg` command in favor of `ast-grep`. This reference consequently uses `ast-grep` throughout. The continuously updated documentation also contains some post-v0.45 functionality; such capabilities must not automatically be attributed to this release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Official sources:

- Documentation: `https://ast-grep.github.io/`
- Repository: `https://github.com/ast-grep/ast-grep`
- Releases: `https://github.com/ast-grep/ast-grep/releases`
- CLI reference: `https://ast-grep.github.io/reference/cli`
- Rule reference: `https://ast-grep.github.io/reference/rule`

### 1.1 Capability map

| Capability                 | Principal mechanisms                                     | Architectural significance                                          |
| -------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------- |
| Structural search          | Patterns, AST kinds, metavariables                       | Identifies code constructs independently of many textual variations |
| Context-sensitive matching | Relational and composite rules                           | Expresses local structural conditions without writing a visitor     |
| Structural selection       | Node kinds, field relationships, ESQuery-style selectors | Extracts syntactically relevant constructs                          |
| Code transformation        | Fix templates, captures, transformations, rewriters      | Builds declarative codemods with reduced bespoke manipulation       |
| Static linting             | YAML rules, severities, diagnostics                      | Provides project-specific syntax policies                           |
| Code outlining             | Symbol, import, export, and member extraction            | Supplies compact structural summaries without reading entire files  |
| Programmatic integration   | JSON, stdin, exit status, CLI orchestration              | Enables deterministic tools and agent workflows                     |
| Language extensibility     | Tree-sitter grammars, custom language configuration      | Extends structural processing to additional syntaxes                |
| Editor integration         | LSP, diagnostics, interactive fixing                     | Connects declarative structural analysis to development workflows   |

The important architectural distinction is that ast-grep packages several traditionally separate activities—search, structural predicates, matching, diagnostics, and patch generation—around the same underlying syntax representation.

### 1.2 Where ast-grep sits in the tooling landscape

ast-grep occupies a useful middle ground:

- Compared with ripgrep and PCRE2, it understands syntax-node structure rather than operating primarily on character sequences.
- Compared with Tree-sitter directly, it provides a substantially higher-level pattern language, relational rule composition, project scanning, and rewriting facilities.
- Compared with compiler-based semantic analysis, it is more lightweight and language-independent, but does not inherently provide resolved names, types, symbol identity, or whole-program relationships.
- Compared with language-specific codemod frameworks, it offers broader language coverage and common rule semantics, while generally providing less language-specific semantic and formatting control.

Its greatest leverage comes when a problem can be expressed using syntactic relationships and substitutions rather than compiler-resolved semantics.

These distinctions are architectural rather than categorical: complex transformations may combine ast-grep with semantic analysis, textual search, language servers, or formatting tools.

## 2. Internal model and execution architecture

### 2.1 Tree-sitter as the syntax engine

The core workflow is:

Source files and query patterns

Language detection, parsing, pattern compilation

Tree-sitter syntax trees

Nodes, children, kinds, fields, text ranges

ast-grep matching engine

Patterns + metavariables + structural predicates + constraints

Matches

JSON / CLI

Diagnostics

Rules / LSP

Patches

Fix / rewrite

Tree-sitter provides a concrete syntax representation retaining information about source locations, punctuation, and code structure. ast-grep builds a higher-level matching and rewriting engine around it.

Important distinctions:

Syntax nodes versus semantic entities. A Tree-sitter `call_expression` represents the syntax of a call, not necessarily which function implementation will execute. A source identifier's text is available, but its resolved binding is not automatically known.

Named versus unnamed nodes. Tree-sitter distinguishes grammatical constructs such as `identifier` and `call_expression` from anonymous syntax tokens such as punctuation and certain keywords. ast-grep's matching strictness controls how these participate.

Source-backed reconstruction. Matches retain relationships to the source text. Captured expressions can be substituted into fixes while retaining their original textual representation. This is not equivalent to reparsing and pretty-printing the entire file.

Local structural evaluation. Rules evaluate candidates using syntax-tree relationships and source text. They do not automatically build a global symbol table, dependency graph, or type environment.

The last distinction is especially important when interpreting matches as evidence. Matching two syntactically identical identifiers does not establish that they refer to the same program entity.

Primary sources:

`https://ast-grep.github.io/advanced/how-ast-grep-works`

`https://ast-grep.github.io/advanced/core-concepts`

`https://ast-grep.github.io/advanced/find-n-patch`

## 3. Structural pattern language

### 3.1 Patterns are executable syntax specifications

A basic pattern is written in the source language itself:

```
ast-grep run -l python -p 'print($VALUE)' src/
ast-grep run -l rust -p 'Some($VALUE)' src/
```

These are illustrative commands; the intended match is a syntactic construct with a captured child, not a text fragment.

The same principle applies to deeply nested expressions. ast-grep searches for matching syntax nodes rather than requiring the pattern to match the source file's root.

Metavariables provide structural placeholders.

| Syntax           | Meaning                                       | Important behavior                      |
| ---------------- | --------------------------------------------- | --------------------------------------- |
| `$NAME`          | Match one named AST node                      | Captures the matched node               |
| `$$NAME`         | Match one node including unnamed syntax nodes | Useful for tokens otherwise excluded    |
| `$$$NAME`        | Match zero or more nodes                      | Captures a sequence                     |
| `$_NAME`         | Anonymous single-node match                   | Avoids capture and equality binding     |
| `$$$`            | Unnamed sequence wildcard                     | Useful for arguments and statements     |
| Repeated `$NAME` | Reuse a capture                               | Requires compatible structural matching |

For example, `$A == $A` matches expressions whose two operands are structurally equivalent under the selected matching strategy. It is not variable-resolution equivalence.

`$$$ARGS` allows a pattern to match variable-length argument lists, parameter lists, or statement sequences. This makes many syntactic variations expressible using a single pattern.

Capture behavior is important beyond convenience: it supports local structural equality checks, constrains match candidates, and supplies the data for rewriting.

Source: `https://ast-grep.github.io/guide/pattern-syntax`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 3.2 Pattern parsing and structural ambiguity

ast-grep parses the supplied pattern using a language grammar, then identifies the effective pattern node.

This has several implications.

Patterns must be parseable. A placeholder cannot arbitrarily replace a language keyword, operator, or grammatical boundary if doing so produces invalid syntax.

Incomplete snippets can be ambiguous. For example, an isolated key-value expression might be parsed as a labeled statement rather than an object property.

Pattern-root selection matters. The node that ast-grep extracts for matching might be a call expression rather than the enclosing statement. Consequently, an otherwise correct pattern may select less source text than intended.

The YAML pattern-object form resolves these issues:

```
rule:
  pattern:
    context: "{ key: $VALUE }"
    selector: pair
    strictness: smart
```

Here, `context` provides parseable surrounding syntax, while `selector` chooses the node that actually participates in matching. The surrounding object is not necessarily the matched unit.

This mechanism can eliminate the need to construct special-purpose parse fragments or write direct Tree-sitter traversals simply to locate syntactically incomplete constructs.

ast-grep includes error-recovery heuristics for patterns that do not form complete source files, but upstream explicitly cautions that their behavior depends on Tree-sitter parsing and may change. Valid contextual patterns are the more durable specification.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



Source: `https://ast-grep.github.io/advanced/pattern-parse`

### 3.3 Matching strictness: an important correctness control

The five documented rule-pattern strictness levels are:

| Level       | Matching behavior                                             | Consequence                                                   |
| ----------- | ------------------------------------------------------------- | ------------------------------------------------------------- |
| `cst`       | Matches all syntax nodes, named and unnamed                   | Highest syntactic fidelity                                    |
| `smart`     | Requires pattern nodes; may skip unnamed target nodes         | Default, permits some target variations                       |
| `ast`       | Matches named nodes in pattern and target                     | Ignores punctuation distinctions represented by unnamed nodes |
| `relaxed`   | Matches named nodes while ignoring comments and unnamed nodes | More tolerant of source variations                            |
| `signature` | Matches named node kinds without checking text                | Broad shape matching                                          |

For example, JavaScript's `function $NAME() {}` under default `smart` matching can also match an `async function` because the additional `async` token may be skipped on the target side.

At `cst` strictness, that difference matters. At `signature` strictness, even textual identities of corresponding named nodes can be ignored.

Why this matters: matching strictness is effectively part of the query's semantic contract. A query intended to identify exact syntax, similar structural shapes, or broad structural families can produce materially different results without changing its pattern text.

`smart` should not be understood as canonical semantic equivalence. Similarly, `signature` should not be interpreted as a guarantee that matched code performs the same operation.

Sources: `https://ast-grep.github.io/advanced/match-algorithm` and `https://ast-grep.github.io/reference/rule`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



## 4. The declarative rule engine

The YAML rule engine is more expressive than an individual structural pattern. Its primary abstraction is a predicate evaluated against a candidate syntax node.

### 4.1 Atomic predicates

| Operator   | Evaluation                                      | Useful distinction                                  |
| ---------- | ----------------------------------------------- | --------------------------------------------------- |
| `pattern`  | Syntactic pattern match                         | Captures and compares syntax fragments              |
| `kind`     | Node-kind identity                              | Selects grammar categories without literal patterns |
| `regex`    | Rust-regex match against the node's source text | Applies text constraints inside structural queries  |
| `nthChild` | Sibling position                                | Supports numbered and `An+B` positions              |
| `range`    | Source location                                 | Restricts matches to a coordinate range             |

`regex` is not a replacement for structural matching: its scope is the text of a candidate node, including descendants. A regex match can occur anywhere in that text unless anchored. The engine uses Rust regular expressions, without PCRE-style lookaround or backreferences.

`nthChild` supports counting from the end and filtering the relevant siblings through `ofRule`. Its indexing is one-based and considers named nodes.

`range` uses zero-based, character-based coordinates, with an inclusive start and exclusive end. It is useful for restricted structural evaluation, but does not create a general source-range query language.

Source: `https://ast-grep.github.io/reference/rule`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 4.2 Relational predicates: structural context

The four relational operators substantially expand expressiveness.

| Operator   | Relationship evaluated                            |
| ---------- | ------------------------------------------------- |
| `inside`   | Candidate appears within another matching node    |
| `has`      | Candidate contains a matching child or descendant |
| `follows`  | Candidate follows a matching sibling              |
| `precedes` | Candidate precedes a matching sibling             |

A relational predicate checks the context surrounding a candidate. It does not change the fundamental unit of matching into a multi-node result.

Two additional controls are particularly important:

`stopBy` controls traversal depth or boundaries. Its values include `neighbor` (default), `end`, or another rule object acting as a stopping condition. With `stopBy: end`, a parent/child relationship can become an ancestor/descendant relationship, and sibling evaluation can extend beyond an immediate neighbor.

`field` targets a specific grammar field in `inside` or `has` relationships. For example, a call node's `function` field is different from its `arguments` field, even though both are descendants of the call. Grammar-field filtering can substantially reduce accidental matches.

A single rule can express a predicate such as find a particular call expression inside a loop body but not inside a nested function, provided the stopping boundary is defined appropriately.

This capability avoids manually writing AST visitors that climb parent chains or traverse selected descendants.

Source: `https://ast-grep.github.io/guide/rule-config/relational-rule`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 4.3 Boolean composition and reusable predicates

Composite rule operators are `all`, `any`, `not`, and `matches`.

Their meaning is precise:

- `all` requires the same candidate node to satisfy every component rule.
- `any` requires one component rule to match.
- `not` excludes candidates satisfying its subrule.
- `matches` evaluates a named reusable utility rule.

A significant potential misunderstanding: `all` refers to predicates, not all children of a node. The expression `has: {all: [...]}` requires a single descendant satisfying every predicate. To require two different descendant categories, compose two `has` predicates under `all`.

Utility rules are named and referenced using `matches`. They can be defined locally within a rule or in globally configured utility-rule directories. They offer reusable structural abstractions and even support recursive rule definitions.

Local utilities can shadow global utilities; capture binding and evaluation ordering are relevant when composing rules with metavariables. These are reasons to treat rules as executable specifications with testable behavior, rather than merely declarative YAML filters.

Source: `https://ast-grep.github.io/guide/rule-config/utility-rule`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 4.4 ESQuery-style selectors

Since v0.39, ast-grep has supported a limited ESQuery-style syntax in the `kind` rule. This is available within the target version.

Examples include:

```
kind: call_expression > identifier
```

for direct child relationships, and:

```
kind: function_declaration:has(return_statement)
```

for a structural condition.

The supported subset includes child and descendant combinators, adjacent and following siblings, grouped selectors, and pseudo-classes including `:has`, `:not`, `:is`, and positional selectors.

The practical advantage is a compact expression language for relationships that would otherwise require nested YAML. The implementation translates selectors into ast-grep rule objects.

It is not a complete implementation of arbitrary CSS or ESQuery syntax, and complicated expressions may be clearer when written explicitly as relational and composite rules.

Source: `https://ast-grep.github.io/reference/rule/esquery`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 4.5 Metavariable constraints and match ordering

Top-level YAML rules can additionally specify `constraints`, which apply rule predicates to previously captured metavariables.

For example:

```
id: call-with-string-argument
language: Python
rule:
  pattern: process($ARG)
constraints:
  ARG:
    kind: string
severity: warning
message: Review this call with a string argument.
```

The outer pattern first locates calls, then `constraints.ARG` restricts the captured argument to the required syntax kind.

This separation is useful for maintaining readable rules: the main pattern identifies the construct, relational predicates establish its context, and constraints refine captured entities.

A consequential limitation is that top-level constraints are designed for single-node captures, not `$$$` sequence captures. Captures within negated conditions also have important limitations.

Source: `https://ast-grep.github.io/reference/yaml`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### Version clarification — current stable release is v0.51.0

A cross-check against the version-specific upstream release, Rust package registry, and npm registry identifies v0.51.0, released October 15, 2026, as the current stable version. The original GitHub releases index returned an outdated listing headed by v0.45.3.

The remainder of this reference targets v0.51.0, superseding the earlier version designation. The structural capabilities described in Sections 1–4 remain applicable.

The main changes across the recent release transition are:

| Release | Significant changes                                                                                                         |
| ------- | --------------------------------------------------------------------------------------------------------------------------- |
| 0.44.0  | Introduced the experimental `outline` command                                                                               |
| 0.45.0  | Deprecated the short `sg` command                                                                                           |
| 0.45.3  | Added minimum-severity CLI filtering and improved outlining                                                                 |
| 0.50.0  | Built-in Zig support, additional outline coverage, safer opt-in loading of native custom-language parsers                   |
| 0.51.0  | Improved reliability of bulk file updates; switched YAML implementation to `serde-saphyr`; additional fixes and maintenance |

The v0.50.0 change to custom-language loading has direct operational consequences, discussed below.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+3



Version-specific sources:

`https://github.com/ast-grep/ast-grep/releases/tag/0.51.0`

`https://github.com/ast-grep/ast-grep/blob/0.51.0/CHANGELOG.md`

## 5. Rewriting and transformation engine

ast-grep's rewriting model is best understood as AST-constrained source-text patching, not general-purpose AST mutation followed by code generation.

Its conceptual pipeline is:

1. Identify a target syntax node and bind metavariables.
2. Evaluate structural constraints.
3. Optionally transform captured content.
4. Expand a replacement template.
5. Patch the appropriate source range.

This separation is important: ast-grep uses syntax trees to determine what to change, while retaining source text as the primary medium for how the change is expressed.

### 5.1 Direct replacement

The simplest form substitutes captured source text into a replacement template.

```
id: replace-deprecated-call
language: Python
rule:
  pattern: old_api($$$ARGS)
fix: new_api($$$ARGS)
```

This illustrative rule changes the selected call expression and preserves its captured arguments as source text.

The replacement string is not parsed as a Tree-sitter syntax pattern. Metavariables can therefore appear where they would be syntactically invalid in a search pattern, which is useful for constructing replacement text.

The tradeoff is that ast-grep does not inherently prove the generated replacement is syntactically valid, semantically equivalent, or correctly formatted. Matching correctness and rewriting correctness are separate concerns.

### 5.2 Range-aware fixes

A basic replacement operates on the selected node's source range. This becomes insufficient when deleting list entries, dictionary properties, or other elements whose delimiters lie outside their syntax node.

`FixConfig` adds three fields:

| Field         | Purpose                                                   |
| ------------- | --------------------------------------------------------- |
| `template`    | Replacement text                                          |
| `expandStart` | Expand the replacement range backward according to a rule |
| `expandEnd`   | Expand the replacement range forward according to a rule  |

For example:

```
rule:
  kind: pair
  has:
    field: key
    regex: Remove
fix:
  template: ""
  expandEnd:
    regex: ","
```

The example illustrates how a property and its following comma can be removed together.

This is a consequential capability: it avoids building a separate delimiter-management implementation for a class of structural edits. However, boundary rules must still account for first, middle, and final elements, comments, and formatting differences.

Source: `https://ast-grep.github.io/reference/yaml/fix`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 5.3 Metavariable transformations

The `transform` section derives new values from captured metavariables before applying the final fix.

| Transformation | Functionality                                                            |
| -------------- | ------------------------------------------------------------------------ |
| `replace`      | Rust-regex-based text substitution, including capture-group replacements |
| `substring`    | Extract a portion of captured text using character indices               |
| `convert`      | Convert naming conventions and capitalization                            |
| `rewrite`      | Apply structural rewriter rules inside captured subtrees or sequences    |

`substring` supports negative indices and uses Unicode character positions rather than byte offsets.

`convert` supports `lowerCase`, `upperCase`, `capitalize`, `camelCase`, `snakeCase`, `kebabCase`, and `pascalCase`. Separator handling can be customized for underscores, hyphens, dots, spaces, slashes, and changes in case.

These operations are useful for transformations that need more than literal substitution: renaming syntax constructs, normalizing identifiers, converting access patterns, or generating related names.

The distinction is that `replace`, `substring`, and `convert` operate on captured text, whereas `rewrite` can operate structurally within captured AST content.

Source: `https://ast-grep.github.io/reference/yaml/transformation`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 5.4 Nested structural rewriters

Experimental

The `rewrite` transformation is one of ast-grep's more advanced capabilities. It allows a rule to match a large construct while selectively modifying smaller constructs captured inside it.

A rewriter defines its own `id`, structural `rule`, and `fix`, optionally including constraints, utility predicates, and text transformations.

For a captured metavariable, the engine finds matching descendants and applies the specified rewriters. Important behaviors include:

- Rewriters are considered in their declared order; the first applicable one wins for a particular node.
- Rewriter matches do not overlap. Higher-level AST nodes take precedence.
- Metavariable bindings and local utilities are scoped to their defining rewriter.
- `joinBy` can aggregate rewritten pieces using a specified separator rather than reconstructing their original arrangement.
- A rewriter can itself invoke further rewriters through its transformations.

This creates a limited compositional transformation language: one rule can identify the enclosing construct, while subordinate rules modify components within it.

For example, a transformation of an import declaration could capture its import-specifier list, transform each specifier, and generate a different arrangement of declarations. This is substantially more expressive than replacing a single matched node with a fixed template.

Nevertheless, it is not a general transactional rewrite system. Overlapping edits, nested matching priorities, formatting, and semantic preservation must be considered explicitly. Upstream continues to designate rewriters as experimental.

Sources:

`https://ast-grep.github.io/reference/yaml/rewriter`

`https://ast-grep.github.io/guide/rewrite-code`

`https://ast-grep.github.io/guide/transform-code`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 5.5 Consequences for codemod design

These native capabilities create three distinct levels of transformation complexity:

| Transformation class                                              | Appropriate native mechanism              |
| ----------------------------------------------------------------- | ----------------------------------------- |
| Replace one syntactically identified construct                    | `pattern` + `fix`                         |
| Replace a construct with derived text or adjusted delimiters      | `constraints` + `transform` + `FixConfig` |
| Transform multiple related components inside a captured construct | `rewrite` + `rewriters`                   |

The compositional opportunity is significant: many codemods can be expressed declaratively without developing a custom AST traversal, mutation engine, or source-patch generator.

The boundary is equally important. ast-grep cannot infer type-correct replacements, resolve imports, select among overloaded functions, or guarantee behavior preservation solely from the syntax tree.

For semantic migrations, it can serve as a high-throughput candidate detector or patch executor, with semantic validation supplied by another tool.

## 6. Command-line capabilities and operational modes

The CLI separates one-off structural queries from reusable rule-based analysis.

| Command                | Primary role                           | Key capabilities                                   |
| ---------------------- | -------------------------------------- | -------------------------------------------------- |
| `ast-grep run`         | Ad hoc search and rewrite              | Pattern/kind matching, capture, direct replacement |
| `ast-grep scan`        | Execute YAML rule sets                 | Diagnostics, lint policies, fixes, rule selection  |
| `ast-grep outline`     | Extract file structure                 | Symbols, signatures, imports, exports, members     |
| `ast-grep test`        | Validate rule behavior                 | Positive/negative tests, snapshot assertions       |
| `ast-grep new`         | Generate project/rule/test scaffolding | Configuration and rule authoring assistance        |
| `ast-grep lsp`         | Language-server integration            | Editor diagnostics and related workflows           |
| `ast-grep completions` | Shell integration                      | Command completion scripts                         |

`run` is the implicit default subcommand, so `ast-grep -p 'foo()'` and `ast-grep run -p 'foo()'` are equivalent.

### 6.1 One-off structural queries

`run` supports both full syntax patterns and node-kind selectors:

```
ast-grep run -l rust -p 'unwrap()' src/
ast-grep run -l python -k call src/
```

The first command searches for a particular expression shape; the second selects syntax nodes classified as calls.

Additional controls include `--selector`, `--strictness`, `--debug-query`, `--stdin`, `--json`, `--globs`, and `--threads`.

A particularly useful diagnostic is `--debug-query`, which exposes how the pattern was parsed. Its formats include `pattern`, `ast`, `cst`, and `sexp`. This directly addresses a common source of false negatives: an unintentionally selected pattern root or an unexpected grammar parse.

The v0.51 CLI also documents a `template` matching strictness mode, described as similar to `smart` but matching text without checking node kinds. This is distinct from the five modes described in the YAML pattern-reference discussion. Its presence in the CLI should not be assumed to establish identical support in every API surface without verification.

Source: `https://ast-grep.github.io/reference/cli/run`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 6.2 Declarative scanning

`scan` evaluates rule configurations across source files.

It supports three important operating styles:

- Project scanning: discover a `sgconfig.yml` and load configured rule directories.
- Standalone rule scanning: `ast-grep scan --rule rule.yml`.
- Inline rule scanning: `ast-grep scan --inline-rules '...'`, including multiple YAML documents separated by `---`.

`--filter` selects rules by an ID-matching regular expression, while project and rule configuration determine file and language applicability.

Inline rules are especially useful for programmatic workflows because an external process can construct a structural rule without requiring permanent filesystem scaffolding.

The distinction between `run` and `scan` is more than presentation: `scan` exposes the full rule configuration model, including relational predicates, constraints, transformations, diagnostics, and richer fixes.

Source: `https://ast-grep.github.io/reference/cli/scan`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 6.3 Interactive and bulk rewriting

The CLI distinguishes matching from file modification.

`--interactive` allows individual proposed changes to be accepted, rejected, or edited. `--update-all` (`-U`) applies applicable rewrites without per-match confirmation.

Structured JSON output and interactive editing are mutually exclusive.

For automated changes, this separation allows the same structural search logic to support discovery, preview, and eventual application. The October 2026 v0.51.0 release also includes a correction intended to preserve files when bulk-update writes fail. That is a file-write reliability improvement, not a guarantee that every transformation is semantically safe or that a multi-file migration is atomic.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 6.4 File discovery and execution diagnostics

The CLI respects common ignore sources, including `.gitignore`, `.ignore`, and hidden-file filtering, with explicit overrides.

Its path controls include `--globs`, `--no-ignore`, and `--follow` for symlink traversal.

`--threads` configures an approximate worker count; `0` lets ast-grep choose according to its heuristics.

`--inspect summary` and `--inspect entity` explain file and rule discovery, including what was scanned or skipped. Inspection records go to stderr, allowing them to be separated from machine-readable matches.

This is useful for diagnosing a subtle but consequential difference between no matching syntax was found and the relevant source files or rules were never considered.

Source: `https://ast-grep.github.io/reference/cli/run`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



## 7. Project configuration, linting, and rule verification

### 7.1 Project configuration and rule configuration are different contracts

`sgconfig.yml` governs the project-level operating environment. Individual rule files govern what to recognize and how to report or modify it.

Key project settings include:

| Project key          | Function                                          |
| -------------------- | ------------------------------------------------- |
| `ruleDirs`           | Directories containing YAML rule definitions      |
| `utilDirs`           | Reusable utility-rule collections                 |
| `testConfigs`        | Rule test locations and snapshot configuration    |
| `languageGlobs`      | Language detection/override by file glob          |
| `customLanguages`    | External Tree-sitter parser registration          |
| `languageInjections` | Structural detection of embedded-language regions |

Rule files contain the substantive matcher and optional policy data: `id`, `language`, `rule`, `constraints`, `utils`, `severity`, `message`, `note`, `labels`, `files`, `ignores`, `transform`, `rewriters`, and `fix`.

Both `files` and `ignores` use project-relative globs. The rule-level `ignores` exclusions take precedence over rule-level `files` inclusions; these are separate from filesystem ignore behavior.

This division allows syntactic policies to be reused independently of file traversal and project organization.

Sources: `https://ast-grep.github.io/reference/sgconfig` and `https://ast-grep.github.io/reference/yaml`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 7.2 Lint diagnostics and severity

Rules support `hint`, `info`, `warning`, `error`, and `off` severities.

They may carry a concise main `message`, a Markdown-capable explanatory `note`, and `labels` that attach primary or secondary diagnostic highlighting to captured metavariables.

The labels are useful for explaining which parts of a larger syntax construct caused the finding, without requiring the principal match range to be narrowed to those parts.

`scan` supports severity filtering and overrides. Diagnostic output can be emitted in GitHub Actions or SARIF formats, making it suitable for automated code-quality reporting.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 7.3 In-source suppressions and suppression hygiene

ast-grep supports source comments such as:

```
// ast-grep-ignore: no-console
console.log("intentional");
```

A suppression may apply to a particular rule or, without rule IDs, to all diagnostics at the relevant location. The current documentation also describes same-line suppression, multiple rule IDs, and a file-level convention involving a directive on the first line followed by a blank line.

Two built-in policy mechanisms are useful:

- `unused-suppression` reports suppression directives that no longer suppress findings, subject to rule-selection behavior.
- `no-suppress-all` disallows unrestricted suppression comments when enabled.

These make suppressions themselves analyzable rather than opaque exceptions.

Source: `https://ast-grep.github.io/guide/project/severity`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 7.4 Rule testing and snapshots

`ast-grep test` verifies declarative rules using example source snippets.

Tests can distinguish `valid` code that should not match from `invalid` code that should match, and snapshot testing captures expected diagnostic behavior. The CLI provides snapshot review and update workflows.

This matters because structural rules have non-obvious edge cases: grammar parsing, matching strictness, ancestor traversal, captured-node identity, and boundary handling can all change observed results.

A rule test suite therefore becomes an executable specification of the syntactic behavior intended by the rule author.

A particularly useful property is that positive and negative cases can cover multiple language constructs without implementing a bespoke test harness for the underlying AST traversal.

Source: `https://ast-grep.github.io/guide/test-rule`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



## 8. Source-code outlining and structural navigation

Experimental

`ast-grep outline` is one of the most consequential additions for programmatic code exploration. Introduced in v0.44.0 and expanded through subsequent releases, it provides compact, source-located representations of declarations without requiring full-file inspection.

Unlike an arbitrary AST query, outlining produces a normalized structural view designed for navigating source files.

### 8.1 The item/member model

The outline representation distinguishes two levels:

- Items: top-level functions, classes, structs, modules, interfaces, enums, imports, and exports.
- Members: directly contained methods, fields, constructors, enum variants, and similar constructs.

Items can have `isImport` and `isExported` attributes; members can have `isPublic`. These are inferred from language syntax by the corresponding outline extractors.

This is not a fully resolved symbol model. For example, Rust `impl` blocks and Go methods with receivers cannot generally be attached to their type declarations through name or type resolution alone. Outlining retains the organization that source syntax supports.

### 8.2 Selective structural views

`outline` provides two independent selection mechanisms.

| Selection | Options                                     | Purpose                           |
| --------- | ------------------------------------------- | --------------------------------- |
| `--items` | `structure`, `exports`, `imports`, `all`    | Select kinds of top-level entries |
| `--view`  | `names`, `signatures`, `digest`, `expanded` | Select presentation depth         |

A file defaults to `structure` with the `digest` view; a directory defaults to `exports` with the `names` view.

This design creates a useful granularity hierarchy: a directory can be summarized as exported symbol names, a particular file as declarations and member digests, and a particular type as expanded member signatures.

For example:

```
ast-grep outline src/ --items exports --view names
ast-grep outline src/parser.rs --items all --view digest
ast-grep outline src/parser.rs --match Parser --view expanded
```

Additional filters include `--match` for a Rust regular expression over top-level item information, `--type` for symbol kinds, and `--pub-members` for restricting displayed members.

A limitation worth emphasizing: `--match` and `--type` filter top-level items, not arbitrary members nested inside them.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 8.3 Machine-readable outlines

The JSON output has a distinct outline schema rather than merely reusing search-match JSON.

Outline entries include relevant fields such as `name`, `symbolType`, `signature`, `astKind`, `range`, and syntactic visibility indicators. A top-level item may contain a `members` collection.

`--json=stream` produces a JSON object per file, allowing large file collections to be processed incrementally without requiring one aggregate document.

The resulting information can support symbol inventories, navigational indices, source-range selection, import listings, and structural comparison of file versions.

It is an extraction layer, not a durable index managed by ast-grep: persistence, incremental reconciliation, identity across edits, and graph construction remain external responsibilities.

Source: `https://ast-grep.github.io/reference/cli/outline`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 8.4 Custom outline extractors

The outline engine is extensible through YAML extraction rules.

An extractor specifies:

| Field                                | Role                                                  |
| ------------------------------------ | ----------------------------------------------------- |
| `id`, `language`                     | Extractor identity and parser language                |
| `role`                               | `item` or `member`                                    |
| `symbolType`                         | Normalized output category                            |
| `rule`                               | Structural predicate identifying the syntax construct |
| `name`                               | Expression/template supplying the symbol name         |
| `signature`                          | Optional signature template                           |
| `isImport`, `isExported`, `isPublic` | Literal or rule-derived visibility/import attributes  |
| `parentRuleIds`                      | Eligible enclosing item extractors for members        |

Extraction rules can reuse ordinary ast-grep rule machinery, including `constraints`, `utils`, and `transform`.

`--outline-rules` loads additional extractors, while `--no-default-outline-rules` allows a supplied catalog to replace bundled definitions.

This is a useful architectural extension point: a tool can establish a domain-specific concept of a code outline while retaining ast-grep's common parsing, matching, and output machinery.

The boundary is important. `parentRuleIds` relates syntactically contained members to item-extractor identities. It does not provide semantic attachment through receiver types, inheritance, imported names, or resolved references.

Sources:

`https://ast-grep.github.io/reference/outline-rules`

`https://ast-grep.github.io/guide/outline-code`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 8.5 Implications for code-intelligence systems

Outlining offers a distinct interface from structural search:

- Search answers where does a syntactic construct occur?
- Outlining answers what syntactic structures does a file expose?
- Compiler or language-server analysis answers what does a name resolve to, and what are its semantic relationships?

An external system can compose these layers without recreating syntax extraction itself.

In particular, outline information can provide compact first-pass context to a programming agent, while structural queries answer more specific questions and semantic engines investigate name resolution and behavior.

Because the feature remains experimental, its extraction coverage and output contract warrant version-specific validation before treating them as permanent storage schemas.

## 9. Structured output, agent integration, and developer tooling

### 9.1 JSON match results as an integration contract

Both `run` and `scan` support three JSON presentation modes:

| Format           | Output structure         | Typical use                    |
| ---------------- | ------------------------ | ------------------------------ |
| `--json=pretty`  | Indented JSON array      | Human inspection               |
| `--json=compact` | Single-line JSON array   | Compact complete responses     |
| `--json=stream`  | One JSON object per line | Streaming pipelines and agents |

A structural match can include:

| Field                       | Meaning                                            |
| --------------------------- | -------------------------------------------------- |
| `file`                      | Source path                                        |
| `text`                      | Matched source text                                |
| `lines`                     | Surrounding source line content                    |
| `range`                     | Match position and UTF-8 byte offsets              |
| `language`                  | Parser language                                    |
| `metaVariables.single`      | Individual captured syntax nodes                   |
| `metaVariables.multi`       | Captured node sequences                            |
| `metaVariables.transformed` | Derived replacement values                         |
| `replacement`               | Proposed rewritten text, when present              |
| `replacementOffsets`        | Byte range targeted by a replacement, when present |

Rule-based results can additionally include `ruleId`, `severity`, `message`, and `note`.

The presence of both match ranges and replacement offsets is significant: with an expanded fix, the source range selected for modification need not equal the original matched node range.

Positions use zero-based line and column numbering; byte offsets are UTF-8 and have inclusive starts and exclusive ends. Downstream tools must not casually interchange byte offsets and character-oriented positions, particularly for non-ASCII source.

Source: `https://ast-grep.github.io/guide/tools/json`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 9.2 Structural extraction without custom parsers

The combination of `--inline-rules`, metavariable captures, JSON streaming, and file-range metadata makes the CLI useful as a deterministic subprocess for advanced tooling.

A generic pipeline can:

1. Supply structural predicates dynamically.
2. Receive a stream of matched constructs and captured components.
3. Apply independent logic to decide which findings matter.
4. Associate findings with source locations and provenance.
5. Optionally request or apply controlled rewrites.

The ability to return capture contents is particularly useful. A tool does not have to rediscover the argument, receiver, identifier, or other syntax node after obtaining a match; these are already exposed by the rule engine.

For many code-inspection tasks, this is a simpler integration boundary than embedding a parser runtime directly.

It also permits a division of responsibility: ast-grep executes deterministic syntactic queries, while another process handles ranking, persistence, semantic enrichment, or workflow coordination.

### 9.3 Editor and CI integration

ast-grep includes an LSP command and an official VS Code extension. The extension integrates structural search/replacement with language-server diagnostics and code actions.

LSP-backed diagnostics depend on an appropriate project configuration. Editor visibility is also affected by how the extension locates the installed CLI, especially when the editor's environment differs from a terminal session.

The same declarative rules can be surfaced as terminal diagnostics, editor findings, or CI results. In CI contexts, SARIF and GitHub Actions formatting are available through `scan`.

This can eliminate a substantial amount of independent editor-specific and CI-specific diagnostic formatting code.

Sources:

`https://ast-grep.github.io/guide/tools/editors`

`https://ast-grep.github.io/reference/cli/scan`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 9.4 Relationship to the broader ast-grep API ecosystem

The system CLI is not the same distribution or interface as the embedded bindings.

| Interface                    | Role                                                                        | Boundary                     |
| ---------------------------- | --------------------------------------------------------------------------- | ---------------------------- |
| `ast-grep` CLI               | File scanning, structural queries, rules, diagnostics, outline and rewrites | Process invocation           |
| `ast-grep-core` Rust crate   | Core syntax-tree and matching capabilities                                  | Embedded Rust integration    |
| `ast-grep-config` Rust crate | Rule/configuration processing                                               | Embedded rule execution      |
| `@ast-grep/napi`             | JavaScript/Node binding                                                     | Programmatic tree operations |
| `ast-grep-py`                | Python binding via PyO3                                                     | Programmatic tree operations |
| `@ast-grep/wasm`             | WebAssembly interface                                                       | Browser/WASM environments    |

The APIs expose more imperative control than YAML rules: arbitrary traversal, application-specific node selection, computations, and procedural patch construction.

They are not interchangeable with the full system CLI. For example, the CLI's project scanning and outline output should not be assumed to exist as identically packaged operations in every binding.

The official API guide specifically notes that applying YAML-style fixes through JS/Python APIs has experimental aspects; embedded use should be evaluated against its own documented contracts.

Source: `https://ast-grep.github.io/guide/api-usage`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



A system that exposes the CLI as a callable tool to an AI agent does not inherently require an MCP server or one of these language bindings. Such protocols and orchestration layers are separate integration concerns.

## 10. Language coverage, embedded syntax, and parser extensibility

### 10.1 Built-in language support

The v0.51.0 documentation lists built-in support for:

Bash, C, C++, C#, CSS, Elixir, Go, Haskell, HCL, HTML, Java, JavaScript/JSX, JSON, Kotlin, Lua, Markdown, Nix, PHP, Python, Ruby, Rust, Scala, Solidity, Swift, TypeScript, TSX, YAML, and Zig.

Built-in Zig support was introduced in v0.50.0.

Language selection is normally based on filename extension, with explicit `--lang` selection and project `languageGlobs` overrides available.

The important caveat is that language support is parser support, not uniform semantic support. Languages have different Tree-sitter grammars, node kinds, field names, error-recovery behavior, and outline extractor coverage.

Therefore, a syntactically equivalent rule in two programming languages may need substantially different patterns or grammar fields.

Source: `https://ast-grep.github.io/reference/languages`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 10.2 Embedded-language injection

ast-grep can represent selected embedded code regions as separate syntax trees.

Examples include JavaScript inside HTML `<script>` elements and CSS inside `<style>` elements. Project configuration can specify additional injection relationships through `languageInjections`.

This matters because without injection support, an embedded code region might only appear as a string or text node in its host language, making ordinary structural searches against the embedded language ineffective.

With an injection definition, a rule written for the embedded language can operate on that region using its own parser.

The system can also incorporate injected-language structures into outlining where the corresponding extractors are available.

The feature does not imply automatic discovery of every embedded language. Correct extraction requires an appropriate host-language pattern, content capture, target parser, and source-range handling.

Sources:

`https://ast-grep.github.io/advanced/language-injection`

`https://ast-grep.github.io/reference/sgconfig`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+1



### 10.3 Custom Tree-sitter languages

A language not shipped with the CLI can be registered through `customLanguages`.

The extension contract includes:

- `libraryPath`: location of the compiled native Tree-sitter parser; platform-specific path mappings are supported.
- `extensions`: file extensions associated with the language.
- `languageSymbol`: optional override for the exported Tree-sitter language symbol.
- `expandoChar`: alternate character used to represent metavariable placeholders in syntaxes where `$NAME` cannot be parsed.
- `outlineRules`: optional outline extractor definitions for the custom language.

The parser itself is supplied externally as a native dynamic library built from a Tree-sitter grammar.

This is extensibility at the syntax-engine boundary, not merely an extension allowing additional file extensions to be searched as text.

It allows the same structural matching and diagnostic framework to operate on specialized languages, configuration DSLs, or other grammars with available Tree-sitter parsers.

Source: `https://ast-grep.github.io/advanced/custom-language`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 10.4 Native parser trust boundary

Security-relevant version change

Since v0.50.0, native custom parsers are not loaded automatically from an untrusted project configuration.

The CLI exposes these policies:

| Value    | Behavior                                                     |
| -------- | ------------------------------------------------------------ |
| `allow`  | Load native custom parsers for this invocation only          |
| `trust`  | Interactively approve and remember the configuration path    |
| `ignore` | Skip native custom parsers without changing remembered trust |
| `revoke` | Remove saved trust and skip the parsers                      |

This restriction matters because a `.so`, `.dylib`, or `.dll` loaded into the process can execute arbitrary native code with the process's permissions.

A subtle security limitation is that remembered trust is associated with the canonical configuration path, not a cryptographic hash of the configuration or parser library. Replacing the native library at that path does not automatically invalidate trust.

This security policy applies specifically to CLI loading; the embedded APIs have their own explicit language-registration mechanisms.

Sources:

`https://ast-grep.github.io/blog/new-ver-50`

`https://ast-grep.github.io/advanced/custom-language`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+2



## 11. Additional advanced mechanisms and important distinctions

### 11.1 Parameterized utility rules

The v0.42 release introduced experimental parameterized global utilities, extending reusable rules into something closer to functions.

A global utility can declare an `arguments` collection, and callers can pass other rule objects through `matches`.

Illustrative structure:

```
# Global utility
id: match-selected-call
language: TypeScript
arguments: [receiver-rule]
rule:
  pattern: $OBJECT.$METHOD($$$ARGS)
  has:
    field: function
    has:
      matches: receiver-rule
```

A caller supplies a structural predicate for `receiver-rule` instead of duplicating the enclosing rule.

This is higher-order composition: rule objects become parameters to other rules.

The mechanism also introduces an explicit capture boundary. Captures internal to a global utility do not automatically become visible to its caller; captures produced by caller-supplied argument rules can be exported to the calling rule and subsequently used in constraints or fixes.

That distinction enables reusable structural abstractions while preserving deliberate metavariable scoping.

The feature was introduced with an explicit experimental warning. Its interface and behavior should be treated as less stable than ordinary utility rules, especially where recursive composition or capture propagation is involved.

Source: `https://ast-grep.github.io/blog/new-ver-42`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 11.2 Recursive utility predicates

Ordinary utility rules support recursive structural definitions when each recursion advances through the syntax tree.

For example, a predicate can recognize either a numeric literal or a parenthesized expression containing another instance of that predicate.

However, recursion is subject to an important condition:

- Recursion through a structural relationship such as `has` can advance to a descendant and eventually terminate.
- Direct or cyclic `matches` dependencies that repeatedly evaluate the same node are not supported and can cause nontermination.

This permits certain recursively defined syntactic categories without making the rule language a general recursive programming language.

Source: `https://ast-grep.github.io/guide/rule-config/utility-rule`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 11.3 Exit-status semantics are command-dependent

The exit codes of `run` and `scan` have materially different meanings.

| Command   | Exit status 0                         | Exit status 1                             |
| --------- | ------------------------------------- | ----------------------------------------- |
| `run`     | At least one match found              | No matches found                          |
| `scan`    | No error-severity rule violation      | At least one error-severity rule matched  |
| `outline` | Completed, including an empty outline | Not used for ordinary no-result reporting |

`outline` documents status `2` for fatal read, parse, or configuration failures.

These differences are consequential for agent orchestration. A result that means successfully found matches for `run` can mean policy violation for `scan`.

A calling process should therefore interpret statuses by command, separately capture stdout and stderr, and distinguish ordinary no-result states from operational failures.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep+2



### 11.4 Standard-input integration has its own constraints

Both `run` and `scan` support `--stdin`.

For `run`, the language must be specified explicitly because standard input does not have a file extension.

For `scan`, the official tooling guide documents a restriction to an explicitly supplied single rule when operating on standard input.

Standard-input execution conflicts with interactive mode, which also needs stdin for user responses.

These restrictions matter when exposing ast-grep through a process API: in-memory source analysis is possible without creating temporary source files, but it is not equivalent to the full project-directory scanning interface.

Source: `https://ast-grep.github.io/guide/tooling-overview`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



## 12. Performance architecture and practical limits

### 12.1 Sources of performance advantage

ast-grep's performance characteristics follow from its architecture:

| Mechanism                         | Expected advantage                                           | Condition or tradeoff                                        |
| --------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| Native Rust implementation        | Avoids much of the overhead of scripting-language traversal  | Parsing and rule evaluation still consume resources          |
| Tree-sitter parsing               | Avoids full compiler initialization for syntactic inspection | Provides syntax rather than resolved semantics               |
| Parallel scanning                 | Distributes independent file work across workers             | Depends on file sizes, available cores, and I/O behavior     |
| Filesystem filtering              | Avoids scanning irrelevant paths                             | Incorrect filters can silently exclude relevant files        |
| Node-kind and structural matching | Targets grammar structure directly                           | Matching complexity depends on rule shape and traversal      |
| JSON streaming                    | Allows incremental downstream processing                     | Consumer must handle per-record output and process lifecycle |
| Source-range patching             | Avoids reconstructing entire files through a formatter       | Does not independently validate generated code               |

These are qualitative architectural advantages, not universal speed guarantees.

In particular, regular expressions or literal search may be more economical for simple textual questions because they can avoid syntax parsing entirely.

Conversely, a syntax-aware query can replace complicated textual heuristics and reduce downstream false-positive filtering, even if its initial scan is more expensive.

### 12.2 Parser speed is not end-to-end query speed

Upstream's July 2026 performance investigation is instructive.

The project reported that a faster standalone parser implementation initially caused worse performance in a complete ast-grep workload. The difference arose from costs outside the isolated parsing benchmark: parser setup, memory management, and syntax-tree traversal.

Subsequent optimization considered the complete application workload rather than treating parser throughput as a sufficient performance proxy.

This reinforces a general distinction between optimizing an underlying engine and improving the full source-analysis pipeline.

Source: `https://ast-grep.github.io/blog/tree-sitter-end-to-end`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



### 12.3 Important limitations

| Limitation                                         | Consequence                                                                    |
| -------------------------------------------------- | ------------------------------------------------------------------------------ |
| No compiler-resolved symbol identity               | Identical names may refer to different definitions                             |
| No native whole-program type reasoning             | Cannot establish type compatibility or overload selection from syntax alone    |
| No automatic global call/dependency graph          | Structural relationships are primarily local to parsed source                  |
| Grammar-dependent syntax                           | Rules and node kinds are not universally portable across languages             |
| Source-text-based fixing                           | Generated text may be syntactically invalid or behavior-changing               |
| No automatically maintained persistent code index  | Long-term identity, history, and incremental graph reconciliation are external |
| Experimental outline and nested rewrite facilities | Coverage and contracts can evolve between releases                             |
| Native custom parsers                              | External parser loading crosses an executable-code trust boundary              |

These limitations do not make ast-grep merely a preliminary search utility. They define the boundary of a powerful syntax-processing layer.

Its native capabilities may eliminate large amounts of bespoke parsing, structural matching, linting, and patching machinery, while retaining clear integration points for semantic and persistent analysis.

## 13. Distribution and system integration

The system CLI is distributed through several package ecosystems.

| Channel                  | Package or command                |
| ------------------------ | --------------------------------- |
| Cargo                    | `cargo install ast-grep --locked` |
| npm                      | `npm install -g @ast-grep/cli`    |
| Python package installer | `pip install ast-grep-cli`        |
| Homebrew                 | `brew install ast-grep`           |
| MacPorts                 | `sudo port install ast-grep`      |
| Nix                      | `nix-shell -p ast-grep`           |
| Upstream binaries/source | GitHub releases and repository    |

The Python distribution `ast-grep-cli` installs the system CLI; it is distinct from `ast-grep-py`, which exposes a Python programming interface.

There is also a naming consideration on Linux: `sg` traditionally identifies a system utility associated with group execution. The fully qualified command `ast-grep` avoids ambiguity and is the preferred interface for v0.51.0 automation.

Source: `https://ast-grep.github.io/guide/quick-start`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://ast-grep.github.io\&sz=32)

ast-grep



## 14. Primary-source reference map

The following direct URLs are independently usable outside ChatGPT.

| Research area                       | Source                                                          |
| ----------------------------------- | --------------------------------------------------------------- |
| Latest stable release               | `https://github.com/ast-grep/ast-grep/releases/tag/0.51.0`      |
| Tagged changelog                    | `https://github.com/ast-grep/ast-grep/blob/0.51.0/CHANGELOG.md` |
| Core architecture                   | `https://ast-grep.github.io/advanced/how-ast-grep-works`        |
| Pattern syntax                      | `https://ast-grep.github.io/guide/pattern-syntax`               |
| Pattern parsing                     | `https://ast-grep.github.io/advanced/pattern-parse`             |
| Match algorithm                     | `https://ast-grep.github.io/advanced/match-algorithm`           |
| Rule operators                      | `https://ast-grep.github.io/reference/rule`                     |
| ESQuery selectors                   | `https://ast-grep.github.io/reference/rule/esquery`             |
| Utility rules                       | `https://ast-grep.github.io/guide/rule-config/utility-rule`     |
| YAML rule configuration             | `https://ast-grep.github.io/reference/yaml`                     |
| Replacement fixes                   | `https://ast-grep.github.io/reference/yaml/fix`                 |
| Metavariable transformations        | `https://ast-grep.github.io/reference/yaml/transformation`      |
| Nested rewriters                    | `https://ast-grep.github.io/reference/yaml/rewriter`            |
| Project configuration               | `https://ast-grep.github.io/reference/sgconfig`                 |
| CLI command reference               | `https://ast-grep.github.io/reference/cli`                      |
| Structural query CLI                | `https://ast-grep.github.io/reference/cli/run`                  |
| Rule scanning CLI                   | `https://ast-grep.github.io/reference/cli/scan`                 |
| Outlining                           | `https://ast-grep.github.io/guide/outline-code`                 |
| Outline extractor specification     | `https://ast-grep.github.io/reference/outline-rules`            |
| JSON output                         | `https://ast-grep.github.io/guide/tools/json`                   |
| Rule testing                        | `https://ast-grep.github.io/guide/test-rule`                    |
| Editor integration                  | `https://ast-grep.github.io/guide/tools/editors`                |
| Custom languages                    | `https://ast-grep.github.io/advanced/custom-language`           |
| Embedded-language processing        | `https://ast-grep.github.io/advanced/language-injection`        |
| Programmatic APIs                   | `https://ast-grep.github.io/guide/api-usage`                    |
| Advanced parameterized rules        | `https://ast-grep.github.io/blog/new-ver-42`                    |
| v0.50 security and language changes | `https://ast-grep.github.io/blog/new-ver-50`                    |

## 15. Architectural synthesis

The most useful way to understand ast-grep is as a declarative structural processing engine with a complete system-tool interface.

Its capability combinations are more consequential than any single feature.

Structural querying + relational predicates + metavariable constraints produces expressive syntax analysis without custom visitors.

Structural matching + transformations + range-aware fixes + nested rewriters produces a capable codemod system without requiring general-purpose AST mutation machinery.

Declarative rules + diagnostics + suppressions + tests + LSP + SARIF supplies a coherent policy and verification layer across terminal, editor, and CI environments.

Outlining + structural search + JSON streaming + source coordinates offers a compact, deterministic interface for agents and code-intelligence systems to discover, characterize, and navigate source code.

Custom parsers + language injection + custom outline extractors extends much of that machinery to additional languages and embedded syntaxes.

The enduring distinction is between structural knowledge and semantic knowledge. ast-grep provides substantial native machinery for the former. Systems that require resolved references, types, interprocedural relationships, or long-term identity can compose it with semantic tooling rather than reconstructing its syntactic capabilities.

For a system tool, that is ast-grep's central architectural value: it makes sophisticated source-structure operations available through a common CLI and declarative rule framework, while keeping its integration boundaries explicit.