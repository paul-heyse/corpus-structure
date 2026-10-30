# Python `ast` — Comprehensive Standard Library Reference

Target: Python 3.15.2 (CPython) · Research date: October 30, 2026 · Status: Stable, included in Python

## 1. Executive orientation

Python's `ast` module provides programmatic access to the abstract syntax tree (AST) produced by Python's parser. It is the standard library's principal interface for examining, analyzing, constructing, transforming, and recompiling Python source code at the language-syntax level.

Unlike text-oriented processing, `ast` exposes Python's grammatical structure directly: functions, classes, expressions, assignments, imports, type annotations, control-flow constructs, comprehensions, pattern matching, and other language elements become structured Python objects with defined fields and relationships.

Its most consequential characteristic is its direct integration with CPython's compiler. An AST is not simply a third-party representation of Python syntax. It is the public Python-object representation of the compiler's abstract syntax grammar, allowing source code to be parsed into structured objects and subsequently compiled into executable code.

Python 3.15.2 is the latest stable release as of the research date, released October 25, 2026. Python 3.16 remains in development. This reference targets the documented Python 3.15 AST interface, distinguishing significant version additions where relevant.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.python.org\&sz=32)

Python.org+2



Primary documentation: `https://docs.python.org/3.15/library/ast.html`

### 1.1 Core capability map

| Capability                         | Native mechanisms                                                 | Architectural significance                                                     |
| ---------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Source parsing                     | `ast.parse`, `compile` compiler flags                             | Convert Python syntax into structured representations without executing it     |
| Syntax introspection               | `ast.AST`, `_fields`, `_field_types`, `iter_fields`, `walk`       | Build generic structural analyzers and schema-aware tooling                    |
| Source analysis                    | `NodeVisitor`, `get_docstring`, `get_source_segment`              | Extract definitions, expressions, dependencies, and structural relationships   |
| Structural transformation          | `NodeTransformer`, node constructors                              | Rewrite and generate Python programs without manipulating source text directly |
| Source-code generation             | `ast.unparse`                                                     | Convert constructed or modified trees back into valid Python source            |
| Executable code generation         | `compile(AST, ...)`                                               | Translate structural transformations directly into executable code objects     |
| Source mapping                     | `lineno`, `col_offset`, `end_lineno`, `end_col_offset`            | Associate syntactic findings with source locations                             |
| AST comparison                     | `ast.compare`, `ast.dump`                                         | Compare structural equivalence and inspect tree representations                |
| Safe-subset literal interpretation | `ast.literal_eval`                                                | Decode literal data without permitting arbitrary Python execution              |
| Language feature coverage          | Async, pattern matching, generics, template strings, lazy imports | Analyze modern Python syntax through native grammar nodes                      |

### 1.2 Why `ast` matters architecturally

The module supports three broad classes of systems:

1. Static structural intelligence: Discover definitions, calls, imports, annotations, expressions, and relationships without importing or running target modules.
2. Program transformation: Perform AST-level refactoring, instrumentation, syntactic normalization, and source generation using Python's own grammar.
3. Compiler-integrated metaprogramming: Construct or modify Python programs and compile them directly into executable code, avoiding the need to implement a separate parser or code-generation language.

These capabilities eliminate considerable custom parsing machinery. They are especially valuable where the important distinctions are grammatical rather than textual.

However, the AST is not a complete source document or resolved semantic model. It does not intrinsically preserve ordinary comments, exact formatting, or all spelling choices. Nor does it provide resolved symbols, inferred types, a control-flow graph, or interprocedural call resolution.

That distinction determines where `ast` is sufficient on its own and where other Python tooling becomes necessary.

## 2. The AST model and its relationship to the compiler

### 2.1 The compilation pipeline

Python source

Text, tokens, syntax, comments, formatting

CPython tokenizer and PEG parser

Abstract syntax tree

ast.AST nodes — inspect, traverse, construct, transform

`ast.unparse()`

Generated Python source

`compile()`

Scope analysis, optimization, code generation

Code object → execution

`exec()`, `eval()`, import machinery, runtime

This is a conceptual pipeline, not an assertion that all compilation paths materialize Python-level `ast.AST` objects.

CPython internally constructs and processes its AST through compiler machinery. The `ast` module exposes this structure as Python objects, with lower-level node types implemented by `_ast`.

The public node grammar is defined in `Parser/Python.asdl` in the CPython source tree. Its structure changes as Python introduces syntax features. Consequently, an AST is version-dependent, not a language-independent intermediate representation with a permanently fixed schema.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+1



Source: `https://github.com/python/cpython/blob/v3.15.2/Parser/Python.asdl`

### 2.2 Node types and structural fields

All nodes derive from `ast.AST`. The grammar distinguishes several major categories:

| Category               | Representative nodes                                                | Meaning                                   |
| ---------------------- | ------------------------------------------------------------------- | ----------------------------------------- |
| Root                   | `Module`, `Expression`, `Interactive`, `FunctionType`               | Parsing entry point                       |
| Statements             | `FunctionDef`, `ClassDef`, `Assign`, `If`, `Try`, `Import`          | Executable statement structure            |
| Expressions            | `Call`, `Name`, `Attribute`, `BinOp`, `Compare`, `Lambda`           | Expressions producing or accessing values |
| Contexts and operators | `Load`, `Store`, `Del`, `Add`, `And`, `Eq`                          | Syntactic roles and operations            |
| Supporting structures  | `arguments`, `arg`, `keyword`, `alias`, `comprehension`, `withitem` | Components of larger constructs           |
| Pattern matching       | `Match`, `match_case`, `MatchSequence`, `MatchAs`, `MatchClass`     | Structural pattern matching               |
| Type parameters        | `TypeVar`, `ParamSpec`, `TypeVarTuple`                              | Generic parameter declarations            |

An important distinction is between node fields and source-location attributes.

- `node._fields` describes the node's grammar-defined fields.
- `node._field_types`, available since Python 3.13, maps those fields to their declared types, including AST classes, Python scalar types, unions with `None`, and list types.
- Location attributes such as `lineno` and `col_offset` are metadata rather than grammatical children.

For instance, `ast.BinOp` has `left`, `op`, and `right` fields. A field can hold another node, a list of nodes, a primitive value such as a string, or `None`, depending on the grammar.

The ASDL schema uses `?` for optional fields and `*` for sequences. This gives tools enough structural information to build generic traversals, serializers, schema inspections, or structural validators without hand-coding every node type.

Importantly, `_field_types` describes declared shapes, not inferred semantic types of expressions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+1



### 2.3 Representation is semantic syntax, not source fidelity

Several distinctions illustrate the abstraction boundary:

- `elif` is represented through a nested `If` inside the preceding `If.orelse`.
- Parentheses used only for grouping generally do not become separate nodes.
- `1_000`, `1000`, and equivalent numerical literal spellings can produce the same `Constant.value`.
- A function's name appears as the string `FunctionDef.name`, rather than necessarily as a separate `Name` node.
- A variable binding may be represented as `Name(ctx=Store())`, a function parameter's `arg` string, a pattern capture's `name`, or another construct.

Thus, a complete static analysis cannot simply count `Name` nodes and assume it has found all definitions and references. The meaning of each grammatical field matters.

This semantic abstraction makes many structural analyses much simpler than token processing, but it means exact textual reconstruction is not intrinsic to the AST.

## 3. Parsing capabilities and compiler controls

### 3.1 `ast.parse`: primary entry point

Python 3.15 defines the following signature:

```
ast.parse(    source,    filename="<unknown>",    mode="exec",    *,    type_comments=False,    feature_version=None,    optimize=-1,    module=None,)
```

The modes determine the expected input grammar and the root node:

| Mode        | Root node      | Typical input                            |
| ----------- | -------------- | ---------------------------------------- |
| `exec`      | `Module`       | Full modules or suites of statements     |
| `eval`      | `Expression`   | A single expression                      |
| `single`    | `Interactive`  | Interactive input                        |
| `func_type` | `FunctionType` | PEP 484 function-signature type comments |

The parser returns an AST without executing the source and without importing the modules referenced in it.

Parsing is not equivalent to successful compilation. Some checks, particularly those involving scope or placement of constructs, occur later. For example, a top-level `return` can be represented as an AST node but cannot be compiled as valid module-level Python code.

### 3.2 Version-selective grammar parsing

`feature_version=(3, minor)` instructs the parser to make a best-effort attempt to recognize the requested Python grammar version.

In Python 3.15, the documented supported range runs from `(3, 7)` through the current interpreter's minor version.

This can help tools identify syntax incompatible with an earlier Python release without necessarily running that release's interpreter.

There is an important limitation: this is not a complete historical parser or compatibility checker. It does not guarantee the same acceptance, rejection, AST representation, or compilation behavior as actually running an older Python interpreter.

That distinction matters for syntax validation across supported Python versions and for tools consuming historical code.

### 3.3 Type comments and type-ignore directives

Setting `type_comments=True` enables special handling of PEP 484 and PEP 526 typing comments.

The resulting representation includes:

- `type_comment` fields on relevant nodes such as assignments, function definitions, arguments, and loops.
- `Module.type_ignores`, containing `TypeIgnore` objects with line information and tags for `# type: ignore` directives.
- Validation of misplaced type comments.

Without the option, these comments are generally ignored by the parser, and the associated fields do not contain their text.

This is a narrow preservation feature: it does not make `ast` retain ordinary comments or formatting. Typing annotations written as expressions are represented independently of this option.

`mode="func_type"` additionally supports parsing the older type-comment function-signature grammar directly.

### 3.4 Optimization and compiler flags

The module exposes compiler-control flags that make AST processing more capable than a standalone parser.

| Flag                             | Purpose                                                                      |
| -------------------------------- | ---------------------------------------------------------------------------- |
| `ast.PyCF_ONLY_AST`              | Return an AST instead of a code object                                       |
| `ast.PyCF_OPTIMIZED_AST`         | Return an AST processed with compiler optimizations                          |
| `ast.PyCF_TYPE_COMMENTS`         | Preserve and check supported type comments                                   |
| `ast.PyCF_ALLOW_TOP_LEVEL_AWAIT` | Permit top-level asynchronous constructs in appropriate compilation contexts |

`ast.parse(..., optimize=n)` uses optimized AST generation when `n > 0`. This capability was introduced in Python 3.13.

For source-faithful structural inspection, a nonoptimized AST is generally the appropriate representation. Optimizations can remove or transform constructs, so the resulting AST is a view of compiler-processed syntax rather than a complete inventory of what the author wrote.

Python's compiler optimization levels are:

- `0`: normal compilation, preserving assertions and docstrings.
- `1`: removes assertions and disables `__debug__`.
- `2`: additionally removes docstrings.

The exact transformations observable in an optimized AST are implementation- and version-dependent; compiler optimization levels are not a promise that every possible constant expression will be folded.

`ast.parse()` does not directly expose every `compile()` flag. For example, parsing with top-level-await support can use `compile()` with `PyCF_ONLY_AST | PyCF_ALLOW_TOP_LEVEL_AWAIT`.

Python 3.15 also adds the `module` parameter to `ast.parse()` and `compile()`. It supplies a module name for unambiguous filtering of syntax warnings, rather than changing the root AST node or performing module import resolution.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+2



Sources:

`https://docs.python.org/3.15/library/ast.html#ast.parse`

`https://docs.python.org/3.15/library/ast.html#compiler-flags`

`https://docs.python.org/3.15/builtins/functions.html#compile`

## 4. Structural analysis and traversal

### 4.1 The three traversal abstractions

`ast` provides three levels of tree access:

| Mechanism                    | Behavior                                                         | Appropriate use                                       |
| ---------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------- |
| `ast.iter_fields(node)`      | Yields `(name, value)` for a node's fields                       | Schema-driven extraction, generic serialization       |
| `ast.iter_child_nodes(node)` | Yields immediate child AST nodes                                 | Custom recursive traversal and parent tracking        |
| `ast.walk(node)`             | Yields all descendants, including the root, in unspecified order | Whole-tree searches and simple structural inventories |

For analyses that depend on lexical scope, ancestor relationships, or ordering, `NodeVisitor` or a custom traversal is normally more appropriate than an unrestricted `ast.walk()`.

The standard AST does not supply parent pointers. Parent-child relationships, lexical ancestry, enclosing function/class definitions, and derived graph edges must be maintained by the analysis.

### 4.2 `NodeVisitor`: dispatch-driven analysis

`ast.NodeVisitor` implements node-type dispatch. The visitor searches for a method named `visit_<NodeClass>` and invokes it when that node is encountered.

A method such as `visit_Call()` can inspect calls, while `visit_FunctionDef()` can register function definitions, and `visit_ImportFrom()` can analyze imports.

This supports heterogeneous analyses using one traversal:

- Definition inventories and syntactic ownership hierarchies.
- Import and module-dependency inventories.
- Call-site inventories.
- Annotation and decorator extraction.
- Detection of control-flow constructs and exception handling.
- Extraction of expressions and constants.
- Identification of potentially unsafe syntactic patterns.

`NodeVisitor` permits analysis state to persist across the traversal, including symbol tables, scope stacks, contextual annotations, and relationships between encountered nodes.

Important traversal semantics: If a custom `visit_FunctionDef()` handles a node without calling `generic_visit()` or explicitly visiting its children, traversal stops at that function. Its body is not automatically visited.

This makes it possible to deliberately restrict an analysis to a particular lexical level, but it also creates a common completeness error.

`visit()` may return a computed value to the caller. `NodeVisitor` is therefore usable for structural evaluation or aggregation, not merely side-effect-based collection.

Source: `https://docs.python.org/3.15/library/ast.html#ast.NodeVisitor`

### 4.3 Structural extraction versus semantic resolution

An AST directly answers questions such as:

- Is an expression a function call?
- Is a target assigned or read?
- Is a function asynchronous?
- What syntax appears inside a condition?
- Does a type alias declare a type parameter?
- What import statements appear in a module?

It does not directly answer:

- Which runtime function will a call invoke?
- Is an identifier local, global, nonlocal, or imported?
- What concrete type does an expression produce?
- Can a particular control-flow path execute?
- Which attributes actually exist on a dynamically constructed object?

The first set is grammatical. The second requires additional scope analysis, static inference, flow analysis, or runtime information.

For example, a `Call` node with `func=Name(id="process")` identifies a syntactic call through the name `process`; it does not establish which function object will be called.

This is the crucial boundary between an AST-based structural index and a fully resolved code-intelligence system.

## 5. Significant syntax families and advanced representations

The AST covers considerably more than ordinary functions, assignments, and arithmetic expressions. Several node families expose important language semantics that are easy to overlook.

### 5.1 Expressions, calls, and assignment contexts

Relevant structures include `Name`, `Attribute`, `Subscript`, `Call`, `keyword`, `Starred`, `BinOp`, `BoolOp`, `Compare`, `NamedExpr`, and the collection expressions.

Two particular distinctions matter for analyzers:

Expression context: `Name`, `Attribute`, `Subscript`, `Tuple`, `List`, and `Starred` can carry `ctx` to distinguish `Load`, `Store`, and `Del`. This identifies the syntactic role of a target, although it does not resolve its symbol binding.

Structured argument expansion: `Call.args` may contain `Starred` nodes for `*args`; `Call.keywords` contains `keyword` nodes, where `keyword.arg is None` represents `**kwargs` expansion. A positional argument list is therefore not necessarily an explicitly enumerable list of the eventual runtime arguments.

Other useful distinctions include:

- Chained comparisons are represented as a single `Compare` with parallel operator and comparator lists.
- Repeated `and` or `or` operations can be represented as multi-value `BoolOp` nodes rather than deeply nested binaries.
- `NamedExpr` distinguishes assignment expressions from statement-level `Assign`.
- Dictionary unpacking uses `Dict.keys` entries of `None`, paired with expressions in `Dict.values`.

These structures permit much more precise extraction and transformation than regexes operating on call parentheses, assignment operators, or expression text.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+1



### 5.2 Functions, classes, and signature structure

`FunctionDef`, `AsyncFunctionDef`, and `ClassDef` expose declaration structure without requiring imports or instantiation.

Function-specific capabilities include:

- Decorator expressions and return annotations.
- Positional-only, positional-or-keyword, keyword-only, variadic positional, and variadic keyword parameters.
- Parameter defaults and keyword-only defaults.
- Type comments and modern type parameters.
- Nested function definitions, generators, coroutines, and asynchronous constructs.

The `arguments` node has an important representation detail: `defaults` applies to the trailing positional parameters, while `kw_defaults` aligns with `kwonlyargs`, using `None` where a keyword-only parameter has no default.

For classes, the AST exposes syntactic bases, keyword arguments (including metaclass declarations), decorators, type parameters, and the class-body statements.

These are declaration structures, not evaluated runtime class relationships. In Python, bases, decorators, and metaclasses may involve arbitrary expressions and runtime effects.

### 5.3 Control flow and exception constructs

The relevant nodes include:

| Structure            | Notable AST representation                        |
| -------------------- | ------------------------------------------------- |
| Conditions           | `If` with `test`, `body`, `orelse`                |
| Loops                | `For`, `AsyncFor`, `While` with optional `orelse` |
| Context managers     | `With`, `AsyncWith`, multiple `withitem` entries  |
| Exceptions           | `Try`, `TryStar`, `ExceptHandler`                 |
| Pattern selection    | `Match` containing `match_case` nodes             |
| Generator suspension | `Yield`, `YieldFrom`                              |
| Coroutine suspension | `Await`                                           |

The distinction between `Try` and `TryStar` is important: the latter represents `except*` exception-group handling, introduced in Python 3.11.

Similarly, a loop's `orelse` is not equivalent to an ordinary conditional `else`. It is associated with completing the loop without an intervening `break`.

The AST exposes enough structure to derive a control-flow graph, but does not itself construct basic blocks, predecessor/successor edges, exception-flow paths, or dominance relationships.

### 5.4 Structural pattern matching

Python 3.10 added a dedicated pattern-node hierarchy.

`Match` contains a subject and a series of `match_case` objects. Each case contains a pattern, optional guard, and statement body.

The pattern nodes include:

- `MatchValue` and `MatchSingleton`: value and singleton patterns.
- `MatchSequence`: sequence destructuring.
- `MatchMapping`: mapping keys, subpatterns, and optional rest capture.
- `MatchClass`: class patterns, positional and keyword subpatterns.
- `MatchStar`: starred sequence capture.
- `MatchAs`: captures, aliases, and wildcard patterns.
- `MatchOr`: alternative patterns.

Patterns are not simply expressions. For example, a capture pattern can represent a binding in `MatchAs.name`, while a wildcard is represented as `MatchAs` without a captured name. This distinction is vital to symbol-definition analysis.

A generic visitor of expressions will not correctly interpret pattern bindings unless it explicitly understands the pattern hierarchy.

Source: `https://docs.python.org/3.15/library/ast.html#pattern-matching`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+2



### 5.5 Generic type parameters and type aliases

PEP 695 introduced a dedicated syntax family in Python 3.12:

- `TypeAlias` for the `type` declaration.
- `type_params` on functions, async functions, classes, and aliases.
- `TypeVar`, `ParamSpec`, and `TypeVarTuple` for parameter declarations.

Python 3.13 added the `default_value` field to these type-parameter nodes.

A `TypeVar` can also contain a bound or constraints, with constraints represented using a tuple expression.

These nodes provide direct syntactic access to a generic declaration's parameter structure, including defaults, rather than requiring interpretation of assignments involving `typing.TypeVar`.

However, the AST does not implement a type checker. It does not resolve generic substitutions, infer variance, verify constraints, or establish the runtime meaning of annotations.

An associated distinction is that Python 3.14 introduced deferred annotation evaluation as the default. The AST continues to represent the source annotation expressions; runtime evaluation of annotations belongs to the interpreter and facilities such as `annotationlib`. This separation makes static annotation extraction possible without invoking annotation evaluation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+2



Sources:

`https://peps.python.org/pep-0695/`

`https://docs.python.org/3.15/library/annotationlib.html`

### 5.6 F-strings and template strings

F-strings use `JoinedStr`, `FormattedValue`, and `Constant` nodes.

Python 3.14 added distinct AST support for PEP 750 template strings:

- `TemplateStr` represents a template string expression.
- `Interpolation` represents an interpolation with an expression value, original expression text, conversion, and optional format specification.

The `Interpolation.str` field is particularly significant. It holds the text of the interpolation expression and may differ from the constructed `value` AST after a transformation.

When `str=None`, `ast.unparse()` instead generates code from the `value` AST. This enables code generation but can change the textual representation relative to the original template.

The `TemplateStr`/`Interpolation` pair is not interchangeable with `JoinedStr`/`FormattedValue`. The distinction reflects the different runtime purposes of template strings and immediately formatted strings.

For AST transformation tools, that means handling the new node family explicitly and understanding how preserved expression text interacts with generated source.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+1



Source: `https://peps.python.org/pep-0750/`

### 5.7 Python 3.15 syntax additions

Two language additions have particularly consequential AST implications.

Explicit lazy imports — PEP 810. Python 3.15 introduces the `lazy` soft keyword for imports. The abstract grammar includes an `is_lazy` field on `Import` and `ImportFrom`. Ordinary imports have `is_lazy=0`; explicit lazy-import syntax is distinguishable at the AST level.

This matters to import inventories because a syntactic dependency no longer necessarily implies eager module loading. Runtime configuration may also make ordinary imports lazy, so the AST flag alone does not fully determine execution behavior.

Unpacking in comprehensions — PEP 798. Python 3.15 permits constructs such as `[*items for items in groups]` and `{**mapping for mapping in mappings}`. Corresponding AST handling must account for `Starred` expressions in comprehensions and the possibility that `DictComp.value` is `None` when the key expression denotes dictionary unpacking.

Existing structural analyzers that assumed a dictionary comprehension always has both a key and a value expression therefore require compatibility consideration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+2



Sources:

`https://peps.python.org/pep-0810/`

`https://peps.python.org/pep-0798/`

## 6. Program transformation and code generation

### 6.1 `NodeTransformer`: native structural rewriting

`ast.NodeTransformer` extends the visitor model by using the result of each visitor method to modify the tree.

Its replacement contract is fundamental:

| Visitor return | Effect                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------ |
| Original node  | Retain that node, including any in-place modifications                                           |
| New AST node   | Replace the visited node                                                                         |
| `None`         | Remove the node from an appropriate parent location                                              |
| List of nodes  | Replace one statement with multiple statements, when the node occupies a statement-list position |

The list-return mechanism is particularly powerful. It permits insertion of setup statements, checks, instrumentation, or multiple generated statements without implementing a separate statement-list rewriting framework.

For example, an instrumentation pass can replace one statement with a list containing a diagnostic statement followed by the original statement.

There are important constraints:

- Returning a list is supported for statements in statement collections, not arbitrary expression fields.
- Removing a required expression or statement can make the resulting AST invalid.
- Newly generated child nodes are not necessarily visited by the same transformer unless traversal is performed explicitly.
- Child transformations require `generic_visit()` or deliberate visits from custom handlers.
- The transformed root returned by `visit()` should be retained because the root itself can be replaced.

The structure supports nested rewrites, source instrumentation, expression normalization, syntactic policy enforcement, generation of wrappers, and compiler-level metaprogramming.

Source: `https://docs.python.org/3.15/library/ast.html#ast.NodeTransformer`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+1



### 6.2 Concise end-to-end transformation example

This illustrative example rewrites direct calls to `getenv` into calls to `logged_getenv`, then verifies the structural result and compiles it.

```
import astclass RewriteCalls(ast.NodeTransformer):    def visit_Call(self, node):        self.generic_visit(node)        if (            isinstance(node.func, ast.Name)            and node.func.id == "getenv"        ):            replacement = ast.Call(                func=ast.Name(id="logged_getenv", ctx=ast.Load()),                args=node.args,                keywords=node.keywords,            )            return ast.copy_location(replacement, node)        return nodesource = "result = getenv('TOKEN', default=None)"tree = ast.parse(source)tree = RewriteCalls().visit(tree)tree = ast.fix_missing_locations(tree)expected = ast.parse(    "result = logged_getenv('TOKEN', default=None)")assert ast.compare(tree, expected)generated_source = ast.unparse(tree)code = compile(tree, "<transformed>", "exec")
```

The example illustrates native parsing, traversal, replacement, location repair, structural comparison, unparsing, and compilation. It is not a sound general-purpose function refactoring: the `Name` check does not resolve lexical bindings or establish which callable a name refers to. The generated code also assumes `logged_getenv` will be available in its execution environment.

No execution of the generated code is necessary to produce the code object.

### 6.3 Constructing ASTs directly

AST node constructors permit program construction without parsing Python source text.

This supports generated functions, expressions, conditionals, class definitions, and entire modules.

It also permits composing preexisting subtrees with newly constructed structures, as long as the final result satisfies the AST grammar and compiler expectations.

Several constraints become important when constructing trees programmatically:

Fields must be valid. A node with the wrong field type or incompatible context is not guaranteed to compile.

Source locations matter. Nodes supporting source-location metadata generally need appropriate starting locations for compilation.

Syntactic legality still applies. Constructing a `Return` node outside a function, for example, does not make it legal.

Compilation does not resolve application dependencies. It converts the tree into executable code, but names and dynamic values still depend on the eventual execution environment.

Python 3.15 tightens the constructor contract: missing required fields and unknown keyword arguments now raise `TypeError`. Optional fields, list fields, and expression-context fields retain their documented defaults.

This reduces the risk of silently creating incomplete or misspelled node structures, but it is not a complete validation system for all semantic and contextual invariants.

### 6.4 Location management during transformations

Three helpers are particularly important:

| Helper                            | Behavior                                                           |
| --------------------------------- | ------------------------------------------------------------------ |
| `ast.copy_location(new, old)`     | Copies available starting and ending source positions              |
| `ast.fix_missing_locations(tree)` | Recursively fills missing location metadata using parent locations |
| `ast.increment_lineno(tree, n)`   | Shifts line numbers for a subtree                                  |

They solve related but distinct problems.

`copy_location()` is useful when replacing an existing expression. `fix_missing_locations()` helps make generated nodes acceptable to the compiler. `increment_lineno()` is useful when relocating existing code.

However, these helpers do not establish the exact new textual positions of every generated token. In particular, filling missing metadata from a parent may produce approximate locations sufficient for compilation, not precise source provenance.

That distinction matters for diagnostics, debugging, source maps, and code-generation systems that require trustworthy source-to-output relationships.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+1



### 6.5 Direct compilation versus source regeneration

Once an AST is constructed or transformed, there are two primary output paths.

Direct compilation: `compile(tree, filename, mode)` produces a code object. This is useful when the objective is execution rather than writing modified source to a repository.

Unparsing: `ast.unparse(tree)` generates Python source text. This is useful when the transformed program must be persisted, inspected, distributed, or subjected to ordinary source-code tooling.

Direct compilation avoids the intermediate text-generation and reparsing path. Unparsing, on the other hand, produces source that can be stored and reviewed independently of the original AST objects.

They are complementary capabilities, not interchangeable guarantees.

## 7. Source locations, extraction, and fidelity

### 7.1 Built-in source-coordinate model

Relevant AST nodes carry the following location attributes:

| Attribute        | Meaning                                        |
| ---------------- | ---------------------------------------------- |
| `lineno`         | Starting line, 1-indexed                       |
| `col_offset`     | Starting column as a UTF-8 byte offset         |
| `end_lineno`     | Ending line, 1-indexed                         |
| `end_col_offset` | Exclusive ending column as a UTF-8 byte offset |

The byte-offset distinction is especially important. AST columns are measured in UTF-8 bytes, not Python Unicode string indices.

For example, characters preceding a node may occupy multiple UTF-8 bytes even though each occupies one Python string position.

This creates potential mismatches when correlating AST positions with text editors, token positions, or source lines decoded into Python strings.

Additionally, ending locations are optional for the compiler. Generated or altered nodes may not have complete or accurate source ranges.

### 7.2 `get_source_segment()`

`ast.get_source_segment(source, node, padded=False)` retrieves the original source text corresponding to a node's location.

It supports multiline spans and can preserve starting indentation through `padded=True`.

The function is useful because it bridges two representations:

- The AST tells the caller what grammatical construct exists.
- The original source segment tells it how that construct was written.

This is valuable for diagnostics, code excerpts, structural matching, source-linked extraction, and narrow text modifications.

It is subject to several limitations:

- It requires the original source string.
- Missing position metadata causes it to return `None`.
- Locations must correspond to the source being supplied.
- It does not by itself reconstruct lost comments, delimiters, or formatting outside the selected source span.

### 7.3 `get_docstring()`

`ast.get_docstring(node, clean=True)` extracts the docstring from `Module`, `ClassDef`, `FunctionDef`, or `AsyncFunctionDef` nodes.

With `clean=True`, it uses `inspect.cleandoc()` to normalize indentation.

This is particularly useful for static documentation extraction: it requires neither importing the module nor evaluating decorators or other module-level expressions.

A docstring is represented within the AST as a string-valued expression statement at the beginning of the relevant body. `get_docstring()` encapsulates that recognition logic.

### 7.4 What source information is not preserved

An AST is intentionally lossy relative to a concrete syntax tree.

| Source characteristic                     | Native AST preservation      |
| ----------------------------------------- | ---------------------------- |
| Statement/expression structure            | Yes                          |
| Declared identifiers and literal values   | Yes                          |
| Supported source spans                    | Yes, via location attributes |
| Selected type comments                    | Yes, when explicitly enabled |
| Ordinary comments                         | No                           |
| Exact whitespace and blank lines          | No                           |
| Original quote style and numeric spelling | Generally no                 |
| Parentheses used only for grouping        | Generally no                 |
| Original token stream                     | No                           |
| Exact formatting round-trip               | No                           |

`ast.unparse()` therefore guarantees neither textual identity nor preservation of the original formatting. It attempts to generate source that produces an equivalent AST representation.

For highly complex expression structures, it may also raise `RecursionError`.

This is an important distinction for automated refactoring: AST transformations may be semantically appropriate but generate unnecessarily large textual diffs when written back to existing source files.

Source: `https://docs.python.org/3.15/library/ast.html#ast.unparse`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+1



## 8. Tree comparison, inspection, and debugging

### 8.1 `ast.compare()`

Introduced in Python 3.14, `ast.compare(a, b, compare_attributes=False)` recursively compares two ASTs.

By default, source-location attributes are ignored. With `compare_attributes=True`, attributes also participate.

This enables several useful operations:

- Determine whether two snippets have equivalent AST structure despite formatting differences.
- Validate expected results of transformations.
- Compare generated ASTs with reference ASTs.
- Detect structural changes between source revisions.
- Test syntax normalization without comparing textual output.

However, AST structural equality is not equivalent to full program semantic equivalence.

For example, renamed local variables can change the AST structure without changing a program's externally observable behavior. Conversely, two identical AST structures may execute differently in different environments.

`ast.compare()` also does not independently resolve symbol names or normalize arbitrary algebraic equivalences.

### 8.2 `ast.dump()`

`ast.dump()` converts a tree into a readable structural representation.

Important options include:

- `annotate_fields`: include field names.
- `include_attributes`: include source-location metadata.
- `indent`: control multiline formatting.
- `show_empty`: expose otherwise omitted empty fields.
- `color`: generate syntax-highlighted ANSI output, added in Python 3.15.

Python 3.15 also changes the default presentation by omitting optional `Load()` values when `show_empty=False`.

Consequently, default `ast.dump()` output should be treated as a debugging representation, not a permanently stable serialization format.

For tools that need a persistent canonical syntax schema, the actual node classes, fields, field types, and explicitly defined serialization rules are more reliable than comparing default human-readable dumps.

### 8.3 Command-line AST inspection

The standard library includes a command-line interface:

```
python -m ast -a -i 2 example.py
```

It can also read from standard input.

Notable options include `--mode`, `--feature-version`, `--optimize`, `--show-empty`, `--include-attributes`, and `--no-type-comments`.

This provides a convenient way to inspect how CPython represents a particular syntax feature, especially when investigating newly introduced node structures or unexpected parser behavior.

Python 3.15 adds syntax-highlighted CLI output by default, controlled through Python's color-output settings.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+1



Source: `https://docs.python.org/3.15/library/ast.html#command-line-usage`

## 9. Literal interpretation and security boundaries

### 9.1 `ast.literal_eval()`

`ast.literal_eval(node_or_string)` interprets a restricted subset of Python expressions and returns the corresponding Python values.

Supported structures include strings, bytes, numbers, tuples, lists, dictionaries, sets, booleans, `None`, and `Ellipsis`. It also supports an empty set through `set()`.

Unlike `eval()`, it does not provide arbitrary name resolution or general function execution.

It is useful for decoding Python literal data embedded in source code, configuration-like expressions, or static metadata. It can also be applied to an appropriate expression node extracted from a larger AST.

However, it is not a safe general-purpose evaluator for untrusted input. The Python documentation explicitly warns that relatively small inputs may produce excessive memory consumption, CPU consumption, recursion failure, or C-stack exhaustion.

It also does not interpret general arithmetic, attribute access, comprehensions, indexing, or arbitrary function calls.

The distinction is between excluding arbitrary Python execution and guaranteeing bounded resource consumption. `literal_eval()` provides the former, not the latter.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+1



### 9.2 General parsing and transformation safety

Other relevant boundaries include:

- Parsing source into an AST does not execute the source, but sufficiently complex source can exhaust parser/compiler stack resources.
- Compiling an AST creates executable code; subsequent execution can have arbitrary effects.
- Syntax-based checks alone are insufficient to establish that a Python program is safe to execute.
- Program transformations can inadvertently change name resolution, evaluation order, exception behavior, or binding semantics.
- Location metadata and compiler acceptance do not prove that a transformation preserves the intended behavior.

For source submitted by untrusted parties, parsing and other structural analysis may require process isolation and resource limits, even if the source is never executed.

These are constraints on the overall analysis environment, not capabilities provided automatically by `ast`.

## 10. Integration with Python's introspection and parsing ecosystem

`ast` becomes substantially more useful when its grammatical representation is combined with other information sources.

The most important distinction is between tools that enrich AST analysis, tools that operate at another compilation stage, and tools that replace the AST representation with a different syntax model.

### 10.1 The compiler's symbol tables: `symtable`

The closest native complement to `ast` is `symtable`.

Python's compiler constructs symbol tables from the AST before generating bytecode. The `symtable` module exposes compiler-derived scope information through `symtable.symtable()` and associated table and symbol objects.

It can classify identifiers according to properties such as:

- Local, global, and nonlocal.
- Parameter, imported name, and type parameter.
- Assigned, referenced, and annotated.
- Free variable or cell variable.
- Comprehension-related scope behavior.
- Membership in nested function, class, type-alias, or annotation scopes.

Python 3.15 adds `Function.get_cells()` and `Symbol.is_cell()`, further exposing closure-cell analysis. Other specialized symbol APIs support comprehensions and annotation-related scopes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+1



This offers a particularly valuable architectural combination:

`ast` provides the syntax structure, while `symtable` provides the compiler's lexical classification of names.

Together they can support more precise static reference analysis than either alone.

The integration nevertheless has limits. The public interfaces do not provide a single automatically resolved graph linking every AST `Name` occurrence to a unique definition across modules.

An analyzer must correlate relevant scopes and syntax locations and still handle unresolved runtime behavior.

Source: `https://docs.python.org/3.15/library/symtable.html`

### 10.2 Lexical fidelity: `tokenize`

`tokenize` exposes Python's lexical token stream, including comments.

It provides `TokenInfo` objects with token type, text, starting and ending positions, and source text. The `exact_type` property distinguishes individual operators represented through the generic `OP` token category.

The combination of `ast` and `tokenize` provides both grammatical structure and lexical detail.

This can enable structural analysis together with preservation of comments, punctuation, token spelling, and source-local formatting.

Two technical distinctions matter:

1. `tokenize` positions use Unicode code-point columns, whereas AST column offsets use UTF-8 bytes.
2. `tokenize.untokenize()` guarantees round-tripping of token type and text, not exact original whitespace placement.

The tokenizer is also documented for syntactically valid Python input; its behavior on invalid source is not a general error-recovery guarantee.

Source: `https://docs.python.org/3.15/library/tokenize.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation



### 10.3 Runtime introspection: `inspect` and `annotationlib`

`inspect` operates on live Python objects, including functions, classes, modules, code objects, and frames.

It provides information unavailable from syntax alone, such as actual object members, signatures, source retrieval, and runtime function/code metadata.

`annotationlib`, added in Python 3.14, complements this with access to runtime annotations under deferred-evaluation semantics. It supports retrieving annotations as values, forward references, or strings.

Unlike static AST inspection, accessing annotations through `annotationlib` may execute arbitrary Python code, depending on the requested operation and object.

The distinction is therefore:

- `ast` analyzes declared source structure.
- `inspect` analyzes objects that exist at runtime.
- `annotationlib` analyzes runtime annotation representations.

These perspectives can be correlated when source and runtime environments are both available, but they should not be treated as automatically equivalent.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+1



Sources:

`https://docs.python.org/3.15/library/inspect.html`

`https://docs.python.org/3.15/library/annotationlib.html`

### 10.4 Compiler output: `dis`

`dis` examines CPython bytecode and code objects.

It exposes compiler output through instruction inspection, disassembly, source positions, control-transfer instructions, and implementation-specific execution details.

Combining AST inspection with bytecode analysis enables investigation of how a syntactic construct translates into compiled operations.

This can help distinguish source-level abstractions from lower-level compiler transformations and execution structure.

However, bytecode is explicitly an implementation detail of CPython and changes across Python versions.

It is not a stable, cross-interpreter intermediate representation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation



Source: `https://docs.python.org/3.15/library/dis.html`

### 10.5 Companion parsing and transformation libraries

Several external libraries address limitations of the standard AST.

| Tool                       | Distinguishing capability                                         | Relationship to `ast`                                                |
| -------------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------- |
| `asttokens`                | Token-level positions and access to original token text           | Enriches an existing AST                                             |
| `LibCST`                   | Concrete syntax representation preserving comments and formatting | Alternative tree model for source-preserving transformations         |
| `Parso`                    | Error recovery, multiple syntax errors, round-trip parsing        | Alternative parser, especially useful for incomplete or invalid code |
| `astroid`                  | Richer inferred semantic representations                          | Higher-level analysis model rather than raw compiler AST             |
| Tree-sitter Python grammar | Incremental parsing and syntax-tree queries                       | Independent parser architecture for editor-like workloads            |

`asttokens` is especially complementary. Its `ASTTokens` class can annotate AST nodes with `first_token` and `last_token` references and provide access to associated tokens. Its `LineNumbers` utilities also handle conversion between UTF-8 AST offsets and Unicode text offsets.

Its `ASTText` facility can derive source positions without full token annotation for supported nodes, sometimes including positions inside f-strings. Unsupported cases may fall back to token-based handling.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://asttokens.readthedocs.io\&sz=32)

asttokens documentation+1



`LibCST` instead provides a separate representation designed for preserving source syntax, including whitespace, comments, and parentheses. It also has its own visitor, transformer, metadata, matcher, and codemod facilities.

Its published documentation explicitly describes syntax support through Python 3.13; compatibility with newer Python 3.14–3.15 constructs should therefore be verified against the particular installed LibCST release rather than assumed from CPython's AST support.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://libcst.readthedocs.io\&sz=32)

LibCST documentation



`Parso` provides error recovery and round-trip parsing, addressing a fundamentally different requirement from `ast.parse()`: being useful while source code is invalid or partially written.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://parso.readthedocs.io\&sz=32)

parso 0.8.4 documentation



Sources:

`https://asttokens.readthedocs.io/en/latest/api-index.html`

`https://libcst.readthedocs.io/en/latest/`

`https://parso.readthedocs.io/en/latest/`

## 11. Architectural combinations and practical limits

The most useful combinations often involve several capabilities operating on the same program at different abstraction levels.

| Problem family                  | Useful capability combination                                             | Important remaining responsibility                           |
| ------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Source definition indexing      | `ast.parse` + `NodeVisitor` + source positions                            | Stable identifiers, nesting, cross-file relationships        |
| Import analysis                 | `Import`/`ImportFrom` + `symtable`                                        | Module resolution, dynamic imports, lazy loading             |
| Reference and binding analysis  | `Name.ctx` + `symtable` + lexical scope tracking                          | Binding-site correlation and dynamic resolution              |
| Program rewriting               | `NodeTransformer` + `copy_location` + `fix_missing_locations` + `compile` | Behavioral correctness and binding preservation              |
| Static documentation extraction | `FunctionDef`/`ClassDef` + `get_docstring` + `get_source_segment`         | Cross-references and external symbol resolution              |
| Generated Python execution      | AST constructors + compiler validation + `compile`                        | Controlled execution environment and dependency availability |
| Syntax-level change detection   | `ast.compare` + source mapping                                            | Semantic impact analysis                                     |
| Source-preserving refactoring   | AST-based analysis + token/CST tooling                                    | Exact edit placement and formatting preservation             |

### 11.1 Capability combinations that can eliminate bespoke machinery

Several architectural opportunities follow from these native capabilities.

Generic schema-aware AST processing. `_fields` and `_field_types` expose sufficient structure to build extensible node inspection and transformation frameworks without manually implementing each syntax tree shape.

Compiler-backed syntax validation. Parsing and compiling generated ASTs can replace custom grammar validators for many syntactic constraints, while preserving the distinction between compilation validity and semantic correctness.

Static source intelligence without imports. AST parsing, docstring extraction, annotation extraction, and compiler-symbol-table analysis provide considerable information without loading a module or triggering its import-time behavior.

Semantics-oriented normalization. AST-based comparison and transformation can ignore many insignificant textual differences, allowing syntax-level analyses to focus on program structure.

Compiler-integrated generation. AST construction and direct compilation can avoid maintaining a custom text emitter when the ultimate output is executable Python code rather than a formatted source file.

These benefits are conditional. For instance, source-preserving transformations often favor concrete syntax representations, while precise reference resolution requires additional semantic modeling.

### 11.2 Performance characteristics

The main performance considerations are architectural rather than fixed benchmark claims.

Parsing and representation: CPython provides its native parser and AST construction machinery. The resulting AST is a fully materialized tree of Python-accessible objects. Repeated full-file parsing or retaining many large trees can therefore incur significant CPU and memory costs.

Traversal: Basic tree walking is straightforward, but repeated independent analyses may traverse the same nodes multiple times. Combined visitors or shared derived indexes can reduce redundant work when many properties are required.

Transformation: Native transformations eliminate the need to reimplement Python grammar rules, but still involve Python-object traversal and allocation. Rewriting does not make AST processing intrinsically incremental.

Compilation: Direct AST compilation avoids emitting Python text and then parsing that text again. It does not eliminate symbol analysis, compiler validation, and code generation.

Incrementality: The standard `ast` interface does not provide incremental re-parsing of only the affected portion of a source file. Parser architectures designed for editor workloads may be preferable when repeated small edits must be processed with minimal recomputation.

None of these observations establishes a universal performance ranking between AST-based analysis, token processing, or alternative parsers. Performance depends on input size, reuse, analysis complexity, allocation patterns, and the work performed after parsing.

### 11.3 Consequential limitations

The boundaries most likely to affect architecture are:

- No exact source preservation: comments and formatting are not retained as a complete concrete syntax model.
- No error-tolerant parsing model: `ast.parse()` does not expose a partial syntax tree with structured recovery from arbitrary syntax errors.
- No built-in cross-file resolution: import dependencies and reference relationships require further analysis.
- No native semantic graph: symbol-definition edges, call graphs, control-flow graphs, and dataflow relationships are not produced directly.
- No inferred type model: annotations are syntax, not proof of runtime or statically inferred types.
- No automatic transformation-correctness guarantee: generated ASTs require validation and, where appropriate, behavioral testing.
- No version-independent AST schema: new Python syntax can change node types and fields.
- No intrinsic incremental parsing: repeated parsing produces new trees rather than updating an existing persistent parse structure.
- No general sandboxing: parsing, compiling, and literal evaluation have resource and security considerations.

Together these limits define `ast` as a powerful syntax-structure foundation, rather than a comprehensive Python code-intelligence engine.

## 12. Version evolution and compatibility

The following are significant evolution points for modern Python AST consumers, rather than a complete changelog.

| Python release | Important changes                                                                                                                                     |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| 3.8            | Unified `Constant` representation; type-comment parsing; `FunctionType`; `feature_version`; source-segment helpers                                    |
| 3.9            | `ast.unparse`; simplified subscript/slice representation; indented `ast.dump`                                                                         |
| 3.10           | Structural pattern-matching AST nodes                                                                                                                 |
| 3.11           | `TryStar` for exception-group handling                                                                                                                |
| 3.12           | `TypeAlias`, `type_params`, `TypeVar`, `ParamSpec`, `TypeVarTuple`                                                                                    |
| 3.13           | `_field_types`; optimized AST generation; `default_value` on type-parameter nodes; stricter constructor deprecation warnings                          |
| 3.14           | `ast.compare`; `TemplateStr` and `Interpolation`; field values in AST `repr`; removal of legacy constant-node aliases                                 |
| 3.15           | Lazy-import `is_lazy` fields; unpacking in comprehensions; `module` parsing parameter; `ast.dump(color=...)`; stricter constructors; CLI highlighting |

Additional Python 3.15 compatibility points:

- AST constructors now reject missing required fields and unknown keyword fields with `TypeError`.
- Direct instantiation of abstract node classes is deprecated, with removal scheduled for Python 3.20.
- The default `ast.dump()` representation omits certain `Load()` context values, making text snapshots potentially different from prior releases.
- Source analyzers must account for new lazy-import representations and comprehension unpacking behavior.
- `ast.Index` and `ast.ExtSlice` remain deprecated legacy compatibility constructs rather than the preferred modern subscript representation.

The AST schema should therefore be considered part of the Python version compatibility surface. A library that understands Python syntax through 3.13 is not automatically correct for all 3.15 constructs merely because it can import the `ast` module.

For multi-version tooling, direct AST-field introspection can reduce unnecessary hard-coded assumptions, while syntax-specific logic still needs to recognize relevant version-dependent behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+1



## 13. Primary-source reference map

The following source URLs are provided as plain text for reuse and further investigation.

| Topic                                  | Direct source                                                       |
| -------------------------------------- | ------------------------------------------------------------------- |
| Complete AST documentation and grammar | `https://docs.python.org/3.15/library/ast.html`                     |
| CPython 3.15.2 AST grammar             | `https://github.com/python/cpython/blob/v3.15.2/Parser/Python.asdl` |
| CPython AST helper implementation      | `https://github.com/python/cpython/blob/v3.15.2/Lib/ast.py`         |
| Compiler built-in                      | `https://docs.python.org/3.15/builtins/functions.html#compile`      |
| Compiler symbol tables                 | `https://docs.python.org/3.15/library/symtable.html`                |
| Tokenization                           | `https://docs.python.org/3.15/library/tokenize.html`                |
| Runtime object inspection              | `https://docs.python.org/3.15/library/inspect.html`                 |
| Annotation introspection               | `https://docs.python.org/3.15/library/annotationlib.html`           |
| Bytecode analysis                      | `https://docs.python.org/3.15/library/dis.html`                     |
| Python 3.15 changes                    | `https://docs.python.org/3.15/whatsnew/3.15.html`                   |
| Type-parameter syntax                  | `https://peps.python.org/pep-0695/`                                 |
| Template strings                       | `https://peps.python.org/pep-0750/`                                 |
| Unpacking in comprehensions            | `https://peps.python.org/pep-0798/`                                 |
| Lazy imports                           | `https://peps.python.org/pep-0810/`                                 |
| ASTTokens                              | `https://asttokens.readthedocs.io/en/latest/`                       |
| LibCST                                 | `https://libcst.readthedocs.io/en/latest/`                          |
| Parso                                  | `https://parso.readthedocs.io/en/latest/`                           |

## 14. Overall assessment of the capability boundary

Python's `ast` provides an unusually direct relationship between a standard library's public API and its language compiler. It exposes a rich, manipulable representation of Python syntax, with native construction, traversal, source-location support, structural comparison, code generation, and compilation.

Its strongest architectural value lies in removing the need for custom syntax parsing, structural recognition, and basic program-rewriting machinery.

A useful distinction is:

- `ast` establishes what the program syntactically expresses.
- `symtable` establishes compiler-recognized lexical bindings and scope classifications.
- `tokenize` and concrete syntax tools recover textual detail.
- Semantic analysis layers establish higher-order relationships such as references, inferred values, call targets, and execution paths.
- `compile`, `dis`, and runtime introspection connect the representation to executable behavior.

The native AST and its adjacent standard-library facilities already cover a substantial portion of the foundation required for sophisticated Python source analysis and program generation.

The remaining engineering work is principally about semantic resolution, cross-module relationships, source fidelity, incremental processing, and analysis-specific representations—not about reimplementing Python's grammatical structure.