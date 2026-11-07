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

# Python `ast` — Advanced Semantics and Compiler Integration Addendum

Target: CPython 3.15.2\
Research date: November 7, 2026\
Status: Stable standard-library functionality\
Companion reference: Python `ast` — Comprehensive Standard Library Reference, October 30, 2026

## Scope and orientation

This addendum extends the primary reference with advanced functionality and semantic distinctions that were not fully developed in the original document. It concentrates on the relationship between Python's abstract syntax representation, lexical binding, evaluation order, compiler-generated symbol tables, source coordinates, and structural transformation.

The additions fall into six connected areas:

- Binding and scope semantics: How different syntactic constructs define, reference, update, or remove names.
- Comprehension semantics: How AST structure relates to implicit scopes, evaluation order, and compiler inlining.
- Structural inspection and identity: Native pattern matching over AST objects, shared node instances, and structural equality.
- Source-location precision: Which grammatical elements expose usable coordinates and where source-range reconstruction is necessary.
- Import and expression representations: Details that affect dependency extraction, generated code, and faithful interpretation of expressions.
- Compiler integration: Additional symbol-table information, compilation flags, asynchronous code objects, and validation boundaries.

These capabilities do not transform `ast` into a complete semantic analyzer. They establish a more precise understanding of which facts can be obtained directly from syntax, which require compiler-derived information, and which remain dependent on runtime behavior or additional analysis.

All functionality discussed below is available in CPython 3.15.2 unless an earlier introduction version or implementation-specific condition is identified.

## 1. Binding semantics: understanding where names are defined

Extends original §§2.3, 5.1, and 5.2.

A central subtlety of Python's AST is that binding is a language-level operation, not a single AST node type.

An identifier may be introduced through an assignment target, function parameter, import, exception handler, pattern capture, generic type parameter, or declaration. The relevant identifier may be held in a `Name` node, a dedicated node with a string-valued field, or a supporting structure.

Consequently, a complete binding inventory requires contextual interpretation of the AST grammar rather than a traversal restricted to `Name(ctx=Store())`.

### 1.1 Distinct assignment representations

| Construct          | AST representation                          | Consequential distinction                                                   |
| ------------------ | ------------------------------------------- | --------------------------------------------------------------------------- |
| `a = b = value`    | `Assign(targets=[...], value=...)`          | Multiple targets share one evaluated right-hand-side expression             |
| `a, *rest = items` | `Assign` with `Tuple` and `Starred` targets | Binding involves sequence unpacking                                         |
| `x: T = value`     | `AnnAssign`                                 | Annotation and optional initializer are represented independently           |
| `obj.x: T`         | `AnnAssign` with `Attribute` target         | Annotates an expression target rather than declaring an ordinary local name |
| `x += value`       | `AugAssign`                                 | Combines a read and an update in one syntactic operation                    |
| `(x := value)`     | `NamedExpr`                                 | Produces a value while binding an identifier in the applicable scope        |
| `del x`            | `Delete` with `Name(ctx=Del())`             | Removes a binding rather than introducing one                               |

The distinction between `Assign` and `AugAssign` is especially important.

For an ordinary name target, both assignments and augmented assignments can contain `Name(ctx=Store())`. However, `AugAssign` also reads the target's existing value before updating it.

For attributes and subscripts, augmented assignment has additional evaluation and write-back semantics. For example, `items[index()] += value` does not simply behave like an arbitrary ordinary assignment with an equivalent arithmetic expression: the target's container and index expressions are evaluated once, and in-place operations may be attempted before fallback operations.

An analyzer that interprets AST contexts as a complete read/write model will therefore miss reads introduced by augmented assignment.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation



### 1.2 `AnnAssign.simple`: a retained syntactic distinction

`AnnAssign.simple` is an integer flag whose meaning is easy to overlook.

- `1` indicates a simple identifier target without enclosing parentheses.
- `0` indicates a parenthesized identifier or a more complex target.

Consider:

```
x: int = 1(x): int = 1
```

Both statements use `AnnAssign` with a `Name` target, but their `simple` values differ.

At module and class scope, this distinction determines whether the annotated name is entered into the corresponding `__annotations__` mapping. The difference survives AST abstraction even though grouping parentheses ordinarily do not have independent AST nodes.

There is an important separation between annotation syntax and annotation evaluation: `AnnAssign` records the declared annotation expression, while the creation and evaluation of runtime annotations follow Python's annotation semantics, including the deferred-evaluation model introduced in Python 3.14.

A structural transformation that preserves the target and annotation but changes `simple` may consequently alter observable annotation behavior.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation



### 1.3 Bindings represented outside `Name` nodes

Several constructs encode binding sites as identifier strings or specialized nodes.

| Construct                         | Binding representation                              |
| --------------------------------- | --------------------------------------------------- |
| `FunctionDef`, `AsyncFunctionDef` | `name: str`                                         |
| `ClassDef`                        | `name: str`                                         |
| Function parameters               | `arg.arg: str`                                      |
| `Import`, `ImportFrom`            | `alias.name`, `alias.asname`                        |
| `ExceptHandler`                   | `name: str \\| None`                                |
| `Global`, `Nonlocal`              | `names: list[str]`                                  |
| `MatchAs`, `MatchStar`            | Optional captured-name strings                      |
| `MatchMapping`                    | Optional `rest` identifier                          |
| Generic type parameters           | Names on `TypeVar`, `ParamSpec`, and `TypeVarTuple` |
| `TypeAlias`                       | Declaration target in its `name` expression field   |

These representations have different semantics. `Global` and `Nonlocal` are scope declarations, not new local bindings. A `MatchAs` capture is conditional on the relevant pattern matching successfully. Function and class definitions bind names after evaluating the expressions involved in constructing the defined object.

Exception handlers provide another consequential special case. An identifier introduced by `except Exception as exc` is cleared when its handler finishes. This differs from ordinary function-local assignment and matters when reasoning about the lifetime of a binding.

Likewise, an import establishes bindings according to the import statement's rules, rather than necessarily introducing a name corresponding to every component of the imported module path.

Architectural implication: A useful binding abstraction should distinguish declaration, binding occurrence, read, update, deletion, scope redirection, and lifetime effects. The AST supplies the grammatical evidence for these categories; it does not supply a finished occurrence-to-symbol graph.

Sources:

- `https://docs.python.org/3.15/library/ast.html#abstract-grammar`
- `https://docs.python.org/3.15/reference/simple_stmts.html`
- `https://docs.python.org/3.15/reference/compound_stmts.html`

## 2. Comprehensions: syntax, evaluation scopes, and compiler inlining

Extends original §§5.1, 5.7, and 10.1.

Comprehensions illustrate why Python's syntax tree and its compiler symbol tables must be understood as related but distinct representations.

A comprehension has a compact AST representation, yet its evaluation may involve an implicit scope, multiple ordered iteration clauses, nested filters, closures, and assignment expressions that bind outside the comprehension itself.

### 2.1 The `comprehension` node

`ListComp`, `SetComp`, `DictComp`, and `GeneratorExp` contain a `generators` collection of `comprehension` nodes.

Each `comprehension` has four fields:

| Field      | Meaning                                         |
| ---------- | ----------------------------------------------- |
| `target`   | Assignment target receiving each iterated value |
| `iter`     | Expression producing the iterable               |
| `ifs`      | Ordered filtering expressions                   |
| `is_async` | Indicates an asynchronous iteration clause      |

For example:

```
result = [    (group, item)    for group in groups    for item in group    if item.active]
```

This is represented by one `ListComp` with two ordered `comprehension` entries. The first describes iteration over `groups`; the second describes iteration over each `group` and contains the filtering expression.

The generator collection is not an unordered set of syntactic dependencies. Its ordering determines how iteration and filtering are nested.

An analyzer translating comprehensions into control-flow or data-dependency representations must preserve that ordering.

### 2.2 Implicit scopes and the outermost iterable

Python's language semantics distinguish the iterable expression in the leftmost `for` clause from the remainder of the comprehension.

The leftmost iterable expression is evaluated in the enclosing scope. Iteration targets and the remaining comprehension body operate according to the comprehension's isolated binding semantics.

For example:

```
x = "outer"result = [x for x in range(3)]
```

The comprehension's iteration variable does not overwrite the enclosing `x`.

This isolation applies even though CPython's implementation of list, set, and dictionary comprehensions changed substantially in Python 3.12.

PEP 709: inlined comprehensions. CPython 3.12 eliminated the separate comprehension function call for these three comprehension families. The compiler preserves variable isolation using internal save-and-restore mechanisms instead.

Generator expressions remain distinct: they continue to use generator execution semantics rather than the same eager comprehension inlining approach.

This has two important consequences:

1. A comprehension's source-level binding rules cannot be inferred solely from the existence of a separate compiled function or symbol table.
2. Compiler and bytecode representations of comprehensions differ across Python versions even when the source-level AST has the same grammatical structure.

PEP 709 also documents changes visible through introspection, tracing, and profiling, including the absence of the former comprehension call frame in common cases. These are compiler-level effects, not new `ast` node families.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://peps.python.org\&sz=32)

peps.python.org+1



### 2.3 Assignment expressions inside comprehensions

Assignment expressions introduce a scope interaction that is not captured by ordinary syntactic nesting.

```
total = 0partial_sums = [    total := total + value    for value in values]
```

The `NamedExpr` appears inside the comprehension AST, but `total` binds in the containing scope.

This behavior is specified by PEP 572 and applies to list, set, and dictionary comprehensions as well as generator expressions.

There are restrictions:

- An assignment expression cannot rebind a comprehension iteration variable.
- Assignment expressions are prohibited inside comprehension iterable expressions.
- Assignment expressions that would bind into the immediately containing class namespace from a comprehension are prohibited.

These restrictions are significant for program transformation. Moving an expression into or out of a comprehension can change its binding behavior or make formerly valid syntax invalid.

A symbol-resolution system therefore needs rules that distinguish syntactic containment from lexical binding ownership.

### 2.4 Expression evaluation order

Comprehensions also expose ordered evaluation relationships.

Of particular interest, PEP 572 standardized dictionary-comprehension evaluation so that the key expression is evaluated before the corresponding value expression.

This permits operations such as:

```
mapping = {    (key := transform(item)): use(key)    for item in items}
```

Here, the value expression can use the identifier bound while evaluating the key.

A static dataflow representation that assumes dictionary key/value expressions are independent, or evaluates the value first, would be incorrect.

Python 3.15's comprehension-unpacking extensions introduce additional structural cases, as covered in the primary guide, but do not eliminate these evaluation-order requirements.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://peps.python.org\&sz=32)

peps.python.org



### 2.5 Implications for semantic extraction

The combination of AST structure, Python's scope rules, and compiler inlining supports several useful analysis capabilities without requiring an alternative Python parser:

- Identifying iteration-variable definitions separately from free references.
- Preserving dependencies across nested iteration and filtering clauses.
- Recognizing assignment-expression bindings that escape comprehension-local isolation.
- Constructing ordered evaluation relationships suitable for dataflow analysis.
- Correlating comprehension variables with compiler-derived symbol classifications.

The remaining work is semantic interpretation: `ast` does not directly produce these relationships or define a general-purpose comprehension-level intermediate representation.

Sources:

- `https://docs.python.org/3.15/library/ast.html#comprehensions`
- `https://docs.python.org/3.15/reference/expressions.html#displays-for-lists-sets-and-dictionaries`
- `https://peps.python.org/pep-0709/`
- `https://peps.python.org/pep-0572/`

## 3. Source-location coverage and precise declaration boundaries

Extends original §7.

The AST's source coordinates are sufficient for many source-linked analyses, but not every grammar node carries a complete location.

### 3.1 Which nodes have locations?

The abstract grammar defines location attributes for statements, expressions, and selected supporting node families.

| Node family                                            | Source-location availability                     |
| ------------------------------------------------------ | ------------------------------------------------ |
| `ast.stmt` subclasses                                  | Start locations; optional end locations          |
| `ast.expr` subclasses                                  | Start locations; optional end locations          |
| Pattern nodes                                          | Start and end locations                          |
| Type-parameter nodes                                   | Start and end locations                          |
| `arg`, `keyword`, `alias`, `ExceptHandler`             | Start locations; optional end locations          |
| `arguments`, `comprehension`, `withitem`, `match_case` | No independent standard location attributes      |
| `Module`, `Expression`, `Interactive`, `FunctionType`  | No standard source spans                         |
| `TypeIgnore`                                           | Line number and tag, rather than a complete span |

This distinction derives directly from `Parser/Python.asdl` and is more precise than assuming every `ast.AST` object has `lineno` and `col_offset`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation



When a supporting structure lacks coordinates, its location must be inferred from positioned children or reconstructed with the original source and lexical information.

For example, `match_case` has no independent span covering the entire `case` clause. Its pattern and body provide positional evidence, but retrieving the precise case header and delimiters may require token inspection.

### 3.2 Definition ranges and decorators

The source span of `FunctionDef`, `AsyncFunctionDef`, and `ClassDef` ordinarily begins at the definition statement itself, rather than its preceding decorators.

Consider:

```
@register@validate(mode="strict")def process(value):    return value
```

The `FunctionDef` node identifies the function beginning at `def process`, while its `decorator_list` contains separate expression nodes corresponding to the two decorators.

An extractor interested in the full decorated declaration must account for the earliest decorator and the definition's ending position.

The same distinction applies to decorated classes.

This affects several operations:

- Retrieving complete declarations rather than only definition statements.
- Associating diagnostics with decorator expressions.
- Identifying source ranges for removal or replacement.
- Building accurate definition-level provenance records.

The AST retains the decorators as expressions but does not expose a separate decorated-definition wrapper or a complete delimiter-preserving source range.

For exact changes to existing source, lexical information may still be needed to include comments, whitespace, or adjacent tokens.

### 3.3 Location repair versus source provenance

Location-management helpers support compilation of generated ASTs, but they do not establish exact output-source positions.

`copy_location()` copies existing coordinates. `fix_missing_locations()` derives missing positions from parents. `increment_lineno()` shifts line positions.

These are not substitutes for regenerating source maps after substantial structural modifications.

In particular, a transformed subtree may contain coordinates inherited from source constructs that no longer correspond precisely to the resulting program.

Architectural distinction: Compiler-acceptable location metadata is weaker than an exact source-to-source provenance mapping. AST-based transformations can use native location helpers to produce compilable trees, while precise editing and diagnostics may still require the original source, token information, or a concrete syntax representation.

Sources:

- `https://docs.python.org/3.15/library/ast.html#abstract-grammar`
- `https://docs.python.org/3.15/library/ast.html#ast.get_source_segment`
- `https://docs.python.org/3.15/library/ast.html#ast.copy_location`

## 4. Structural pattern matching over AST objects

Extends original §4.

Python's structural pattern-matching syntax is useful not only as source code represented by `ast.Match`, but also as a mechanism for examining AST objects.

These are distinct capabilities: one concerns the representation of Python `match` statements; the other concerns using class patterns to inspect Python objects whose classes belong to the AST hierarchy.

### 4.1 AST nodes as class-pattern subjects

AST node classes can participate directly in class patterns.

For example:

```
import astdef is_direct_open_call(node: ast.AST) -> bool:    match node:        case ast.Call(func=ast.Name(id="open")):            return True        case _:            return False
```

This is equivalent to testing the outer node's type and then examining the structure of its `func` field.

The pattern is recursive: `ast.Call` is matched first, followed by its nested `ast.Name` expression.

Keyword patterns refer directly to named AST fields. CPython's generated node classes also provide positional matching through `__match_args__`, corresponding to their declared structural fields.

Keyword patterns make field dependencies explicit and are generally easier to interpret across AST schema changes.

A notable difference from ordinary object construction is that a class pattern specifies constraints on existing objects; it does not construct the corresponding AST node.

### 4.2 Relationship to visitors and transformations

Class-pattern matching and visitor dispatch support different operations.

| Mechanism                                  | Primary strength                                                      |
| ------------------------------------------ | --------------------------------------------------------------------- |
| `isinstance()` and direct field inspection | Simple localized recognition                                          |
| `match` / `case` with AST class patterns   | Declarative matching of nested structural shapes                      |
| `NodeVisitor`                              | Recursive traversal with node-specific dispatch and accumulated state |
| `NodeTransformer`                          | Traversal that supports structural replacement                        |
| `ast.compare()`                            | Recursive comparison of two complete AST structures                   |

Pattern matching does not automatically descend through an AST. The caller must still select nodes for matching, whether through `ast.walk()`, a visitor, or another traversal.

It also does not resolve semantic references. Matching `ast.Name(id="open")` identifies the spelling of a syntactic callable, not the identity of the runtime object.

The native capability is nevertheless useful for structural recognizers, syntactic classifiers, and localized transformation predicates. It can reduce bespoke nested type-checking logic while remaining fully compatible with the standard AST representation.

Sources:

- `https://docs.python.org/3.15/reference/compound_stmts.html#class-patterns`
- `https://docs.python.org/3.15/reference/datamodel.html#object.__match_args__`
- `https://peps.python.org/pep-0634/`

## 5. Advanced compiler symbol-table integration

Extends original §10.1.

The `symtable` module exposes a richer set of compiler-derived information than the basic local/global/free-variable classifications described in the primary reference.

Several facilities are particularly useful when correlating AST declarations with lexical scopes and compiler-recognized bindings.

### 5.1 Specialized symbol classifications

| API                          | Capability                                                                                    |
| ---------------------------- | --------------------------------------------------------------------------------------------- |
| `Symbol.is_comp_iter()`      | Identifies comprehension iteration variables                                                  |
| `Symbol.is_comp_cell()`      | Identifies cells associated with inlined comprehensions                                       |
| `Symbol.is_free_class()`     | Identifies class-scoped names that resolve as free names from method scopes                   |
| `Symbol.is_cell()`           | Identifies variables serving as closure cells                                                 |
| `Symbol.is_type_parameter()` | Identifies declared generic type parameters                                                   |
| `Symbol.is_namespace()`      | Identifies names associated with namespace-introducing definitions                            |
| `Symbol.get_namespaces()`    | Retrieves the namespaces associated with a symbol                                             |
| `Symbol.get_namespace()`     | Retrieves the single associated namespace, raising `ValueError` when there is not exactly one |

The comprehension-specific APIs were added in Python 3.14, while `Symbol.is_cell()` was added in Python 3.15.

### 5.2 Comprehension variables and compiler scopes

Following PEP 709, CPython's compiler can inline list, set, and dictionary comprehensions without constructing the separate function scopes used previously.

The symbol table nevertheless retains the information needed to recognize comprehension iteration variables and relevant cell relationships.

`is_comp_iter()` and `is_comp_cell()` expose some of these distinctions directly.

This means compiler-based scope analysis need not rely on discovering an independently materialized child namespace for every comprehension. It can use the classifications the compiler actually provides.

These flags classify symbols rather than individual AST occurrences. An analyzer must still correlate the symbol-table entries with the syntactic comprehension structure.

### 5.3 Class scopes are not ordinary enclosing function scopes

`is_free_class()` represents another subtle lexical distinction.

Consider:

```
def outer():    value = 1    class Example:        value = 2        def method(self):            return value
```

The method's unqualified reference to `value` resolves to the enclosing function's binding, not the name assigned within the class body.

The compiler tracks this distinction, and `is_free_class()` provides relevant classification information.

Without this behavior, an analysis that follows lexical AST ancestry mechanically might incorrectly identify the class assignment as the definition referenced by the method.

This is an example of native compiler functionality providing information that is difficult to derive correctly from syntax alone.

### 5.4 Symbol-table types and annotation scopes

The `SymbolTableType` enumeration distinguishes conventional scopes from specialized annotation-related scopes.

Its members include:

- `MODULE`, `FUNCTION`, and `CLASS`.
- `ANNOTATION`, used for annotation scopes associated with future-annotation behavior.
- `TYPE_ALIAS`, for scopes associated with type-alias expressions.
- `TYPE_PARAMETERS`, for generic type-parameter scopes.
- `TYPE_VARIABLE`, for scopes associated with type-variable bounds, constraints, and defaults.

The specialized types are consequential because modern Python typing syntax introduces scope structures that do not correspond one-to-one with conventional function or class AST nodes.

The documentation recommends using `SymbolTableType` members rather than comparing arbitrary string representations of table types.

### 5.5 Namespace associations

`Symbol.is_namespace()` identifies a name associated with a definition that introduces a namespace, such as a function or class declaration.

`get_namespaces()` returns associated namespaces, allowing analysis of names that introduce multiple definitions.

Importantly, a symbol can have multiple bindings, not all of which introduce namespaces.

For example:

```
def operation():    passoperation = 42
```

The symbol retains evidence of a namespace-introducing definition even though its eventual runtime value can be replaced.

This is why `is_namespace()` should not be interpreted as proof that the symbol always refers to a function, class, or unique namespace.

### 5.6 AST–symbol-table integration boundary

`ast.parse()` returns an AST. `symtable.symtable()` independently accepts source code and returns compiler symbol tables.

There is no public operation that takes an existing AST and returns a complete graph of resolved identifier occurrences linked to their definitions.

The public symbol-table API also does not expose source coordinates for every individual reference.

Correlating the two representations therefore remains a distinct analysis operation.

The combination can establish much stronger lexical classifications than AST traversal alone, but still does not provide general cross-module resolution, runtime attribute dispatch, or inferred expression types.

Compatibility note: `symtable.Class.get_methods()` is deprecated since Python 3.14 and scheduled for removal in Python 3.16. It should not be regarded as a durable mechanism for discovering class methods. The AST and the remaining symbol-table facilities provide alternative structural evidence.

Source: `https://docs.python.org/3.15/library/symtable.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation



## 6. Node identity, mutability, and comparison semantics

Extends original §§2.2, 6.3, and 8.1.

AST nodes are mutable Python objects, but the object model has some important properties that are not apparent from the grammar alone.

### 6.1 Operator and context singleton instances

CPython explicitly documents that operator nodes produced by `ast.parse()` are shared singleton instances.

The affected classes derive from:

- `ast.operator`
- `ast.unaryop`
- `ast.cmpop`
- `ast.boolop`
- `ast.expr_context`

Thus, occurrences of `ast.Add` within a parsed tree may refer to the same object rather than independent instances.

Modifying a shared operator object can affect all occurrences referring to it.

A transformation changing an operator should therefore replace the appropriate parent field with the desired operator node instead of relying on mutation of an existing shared operator instance.

The distinction also matters for metadata systems. Attaching mutable, occurrence-specific annotations directly to operator nodes is unsuitable when those nodes are shared.

This singleton behavior is documented for trees returned by parsing; it should not be generalized into a guarantee about arbitrary manually constructed AST object graphs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation



### 6.2 Object identity versus structural equality

AST nodes do not ordinarily implement recursive structural equality through `==`.

For example:

```
import astfirst = ast.parse("x + 1")second = ast.parse("x + 1")assert first is not secondassert first != secondassert ast.compare(first, second)
```

The first two comparisons concern independently allocated Python objects, while `ast.compare()` examines the node structures.

This distinction becomes important when ASTs are used for caching, transformation verification, structural deduplication, or change detection.

The standard comparison mechanism does not establish semantic equivalence. It also does not provide a canonical hash or persistent identity for an AST subtree.

Such functionality, when needed, requires separately defined equivalence and identity policies.

### 6.3 Shared subtrees and transformation ownership

AST fields can hold references to arbitrary AST instances. Manually constructed or transformed structures may therefore share subtree objects.

If the same mutable node is inserted at several positions, in-place changes to that node affect each reference.

This behavior can complicate transformations that assume the AST is a strictly owned tree in which every occurrence has a unique object identity.

For transformation systems, the distinction is between:

- Structural occurrence: A node's position within a particular parent and field.
- Object identity: The Python object referenced at that position.

They are not guaranteed to be equivalent concepts.

Generic traversals expose objects and child relationships, not immutable occurrence identifiers or automatic copy-on-write semantics.

### 6.4 Legacy visitor compatibility

Another compatibility distinction concerns the removal of legacy constant-node visitor dispatch.

In Python 3.14 and later, these methods are no longer invoked for ordinary constants:

`visit_Num()`, `visit_Str()`, `visit_Bytes()`, `visit_NameConstant()`, and `visit_Ellipsis()`.

`visit_Constant()` is the appropriate visitor method for modern constant nodes.

This matters even if a visitor's original implementation still imports successfully: the old handlers may simply cease receiving callbacks, silently reducing extraction completeness.

The removal is separate from the stricter AST node-constructor behavior introduced in Python 3.15.

Source: `https://docs.python.org/3.15/library/ast.html#ast.NodeVisitor`

## 7. Import representation and Python 3.15 lazy-import controls

Extends original §§5.7 and 11.

### 7.1 Import structure versus imported bindings

`Import` and `ImportFrom` have different representations and binding rules.

For ordinary imports, the `names` collection contains `alias` nodes whose `name` fields hold the imported module paths and whose `asname` fields hold optional aliases.

For relative imports, `ImportFrom` exposes:

- `module`: the named module portion, excluding leading dots.
- `level`: the relative-import level, with zero indicating an absolute import.
- `names`: the imported members, each represented through `alias`.

For example:

```
from ..utilities import convert as transform
```

The corresponding `ImportFrom` contains `module="utilities"`, `level=2`, and an alias with `name="convert"` and `asname="transform"`.

For `from . import helper`, `module` can be `None` while `level=1`.

These distinctions are essential when resolving imports relative to a package.

They also separate three concepts that are easy to conflate: the path being imported, the name bound in the importing scope, and the object eventually obtained from the import.

For example, `import package.submodule` normally binds `package`, whereas `import package.submodule as local` binds the alias `local`.

The AST represents the syntax but does not resolve the imported object's eventual runtime identity.

### 7.2 Explicit lazy imports and runtime policy

Python 3.15 adds `is_lazy` to `Import` and `ImportFrom`.

This field identifies explicit use of the `lazy` syntax. It is not sufficient to determine whether an import will actually execute lazily in every environment.

Lazy-import behavior can also be controlled through facilities outside `ast`.

| Mechanism                              | Role                                                     |
| -------------------------------------- | -------------------------------------------------------- |
| `lazy import ...`                      | Explicit source-level lazy import                        |
| `Import.is_lazy`, `ImportFrom.is_lazy` | AST representation of explicit lazy syntax               |
| `__lazy_modules__`                     | Module-level opt-in for selected ordinary imports        |
| `-X lazy_imports`                      | Interpreter-wide configuration                           |
| `PYTHON_LAZY_IMPORTS`                  | Environment-based interpreter configuration              |
| `sys.set_lazy_imports()`               | Runtime selection of lazy-import mode                    |
| `sys.get_lazy_imports()`               | Runtime inspection of the selected mode                  |
| `sys.set_lazy_imports_filter()`        | Policy callback controlling eligibility for lazy loading |

The interpreter-wide modes include `"normal"` and `"all"`.

In normal mode, explicit source-level lazy imports and applicable module-level declarations determine the relevant lazy behavior. In all mode, eligible top-level imports become potentially lazy, subject to the configured restrictions and filter.

The filter can inspect the importing module name, imported module name, and fromlist, allowing policies more selective than a global all-or-nothing setting.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation



The `__lazy_modules__` mechanism is particularly relevant because it enables lazy behavior without changing the import statement's source syntax.

For relative imports, entries in `__lazy_modules__` use fully qualified module names. For `from` imports, the relevant lookup is based on the module being imported from rather than each imported member's name.

### 7.3 Restrictions and observable execution behavior

Explicit lazy-import syntax has several restrictions:

- It is available only at permitted module-level positions, not inside functions, class bodies, or `try`/`except`/`finally` blocks.
- Star imports cannot be explicitly lazy.
- Future imports cannot be explicitly lazy.

Lazy imports also alter exception timing.

For an eligible import, Python can create a lazy proxy without immediately loading the underlying module. Loading and related errors occur when the imported binding is first resolved.

For `lazy from module import name`, individual imported bindings can remain unresolved until accessed, even after another binding has triggered loading of the underlying module.

At runtime, `types.LazyImportType` and `sys.lazy_modules` provide additional inspection capabilities, although the latter has documented implementation-specific limitations and is not a definitive inventory of unresolved dependencies.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation+1



Architectural distinction: A static import inventory can identify explicit lazy-import syntax and infer some module-level declarations, but it cannot generally determine effective lazy behavior from the AST alone. Runtime configuration, filters, and dynamic execution behavior remain additional information sources.

Sources:

- `https://docs.python.org/3.15/reference/simple_stmts.html#lazy-imports`
- `https://docs.python.org/3.15/whatsnew/3.15.html`
- `https://docs.python.org/3.15/library/sys.html`

## 8. Additional expression representation details

Extends original §§5.1 and 5.6.

### 8.1 F-string conversion and nested formatting expressions

`FormattedValue` exposes three semantically important fields:

- `value`: the expression being formatted.
- `conversion`: the requested conversion mode.
- `format_spec`: an optional `JoinedStr` representing the format specification.

The conversion field uses integer codes:

| Value | Meaning                |
| ----- | ---------------------- |
| `-1`  | No explicit conversion |
| `97`  | `!a`                   |
| `114` | `!r`                   |
| `115` | `!s`                   |

Format specifications may contain their own interpolated expressions.

Consider:

```
f"{value!r:{width}.{precision}f}"
```

The outer `FormattedValue` contains an expression for `value`, the `!r` conversion, and a `format_spec` whose nested `JoinedStr` contains additional `FormattedValue` nodes for `width` and `precision`.

Thus, a format specification is not necessarily a static string. It can contain expressions with independent name references, calls, or side effects.

An analyzer that inspects only `FormattedValue.value` and ignores `format_spec` can therefore miss executable expressions and dependencies.

Debug-style f-strings introduce another representational subtlety. An expression such as `f"{value=}"` does not require a dedicated AST node type: the displayed expression text is represented through string content alongside a formatted expression.

This representation supports evaluation and source regeneration but does not retain a complete, token-faithful record of the original f-string spelling.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation



### 8.2 Limited literal-spelling preservation

`Constant.kind` is a narrow exception to the general loss of lexical spelling in the AST.

For string literals written with a `u` prefix, the field can contain `"u"`.

For other constants, `kind` is ordinarily `None`.

For example:

```
u"example"
```

Produces a `Constant` containing the string value and `kind="u"`.

This does not make `Constant` a source-preserving representation. Quote style, escape spelling, numerical separators, and most other lexical details remain outside the AST's retained information.

### 8.3 Subscripting and multidimensional slicing

Modern `Subscript` nodes hold their index or slice representation directly in `slice`.

An ordinary index can be represented by an expression node, while a slice such as `1:5:2` uses `Slice(lower, upper, step)`.

Multidimensional indexing can use a `Tuple` containing a mixture of expression and `Slice` nodes.

For example:

```
array[1, 2:5]
```

Has a `Subscript.slice` represented as a `Tuple` containing a constant and a `Slice`.

This is important for structural processing of numerical and array-oriented Python expressions because multidimensional indexing is not necessarily encoded as a single `Slice`.

The old `Index` and `ExtSlice` wrapper representations are deprecated compatibility constructs and are not the preferred modern representation.

Source: `https://docs.python.org/3.15/library/ast.html#subscripting`

## 9. Definition evaluation order and compiler-context controls

Extends original §§3.4, 5.2, and 6.5.

### 9.1 Decorator ordering

For function and class definitions, `decorator_list` stores decorators in source order, outermost first.

However, decorator application proceeds from innermost to outermost.

Consider:

```
@outer@innerdef operation():    pass
```

Conceptually, the resulting decorated function is obtained through:

```
operation = outer(inner(operation))
```

This distinction matters for AST transformations that insert, remove, or reorder decorators.

The AST's list order represents source order, not the order in which decorator functions are applied.

A transformation that reverses the list will generally change behavior even if the same decorators remain present.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation



### 9.2 Compiler flag inheritance

The built-in `compile()` function provides greater control over compilation context than the primary guide details.

Its parameters include:

```
compile(    source,    filename,    mode,    flags=0,    dont_inherit=False,    optimize=-1,    *,    module=None,)
```

The `flags` parameter controls compiler options and enabled future features.

When `dont_inherit=False`, applicable compiler flags and future features from the calling context may be inherited. Explicit flags are combined with inherited settings.

When `dont_inherit=True`, the compiler ignores those inherited settings and uses the supplied flags.

This matters for compiler-integrated metaprogramming because a generated AST can be compiled under different compiler contexts, even if its structure is unchanged.

Relevant future-feature flags are exposed through the `compiler_flag` attribute of entries in `__future__`.

The `optimize=-1` setting also has contextual significance: it selects the interpreter's current optimization level, whereas explicit `0`, `1`, and `2` request particular optimization levels.

These controls concern compilation, not merely AST construction.

Source: `https://docs.python.org/3.15/builtins/functions.html#compile`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.python.org\&sz=32)

Python 3.15.2 documentation



### 9.3 Top-level asynchronous compilation

`ast.PyCF_ALLOW_TOP_LEVEL_AWAIT` permits top-level asynchronous constructs in supported compilation contexts.

Its effect is more consequential than merely allowing the parser to accept syntax.

Compiled code containing top-level `await` can itself be coroutine code. Executing that code object produces a coroutine that must be awaited or otherwise driven by an appropriate asynchronous execution mechanism.

For example, the following illustrates the distinction:

```
import astimport inspectcode = compile(    "await operation()",    "<interactive>",    "exec",    flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,)assert code.co_flags & inspect.CO_COROUTINE
```

Such code is not equivalent to a conventional synchronous module execution simply because it was compiled in `"exec"` mode.

The caller must account for coroutine execution and its result.

For AST inspection, top-level asynchronous input can be parsed using `compile()` with both `PyCF_ONLY_AST` and `PyCF_ALLOW_TOP_LEVEL_AWAIT`.

This demonstrates that the compiler's accepted-language configuration can be broader than the default behavior of `ast.parse()`.

The distinction is useful for understanding interactive execution, notebook-like environments, and systems that generate executable Python code with asynchronous constructs.

Sources:

- `https://docs.python.org/3.15/library/ast.html#compiler-flags`
- `https://docs.python.org/3.15/builtins/functions.html#compile`
- `https://docs.python.org/3.15/library/inspect.html#code-objects-bit-flags`

### 9.4 Compilation, validation, and error boundaries

Compiling an AST checks important grammar, field, context, and syntactic invariants.

However, compilation is not a comprehensive source transformation validator.

Three separate properties should be distinguished:

| Property                        | What it establishes                                                        |
| ------------------------------- | -------------------------------------------------------------------------- |
| AST construction succeeds       | Python objects representing AST nodes have been created                    |
| `compile(AST, ...)` succeeds    | The compiler accepts the structure under the supplied compilation settings |
| Executed behavior is equivalent | Requires additional reasoning, testing, or formal verification             |

Compiler acceptance does not establish name-binding preservation across transformations, runtime dependency availability, exception equivalence, or safety.

Compilation can also fail with different exception types depending on the input and failure stage, including syntax, field-validation, and resource-related errors.

There is a small documentation discrepancy worth noting: the Python 3.15 `ast.parse()` reference says null characters raise `ValueError`, while the `compile()` reference documents `SyntaxError` for null-character source input. The exact behavior should not be inferred from the older `ast.parse()` wording alone when implementing exception-specific handling.

This does not affect the documented general-purpose capabilities of `ast`, but it matters to robust parser frontends and compatibility-sensitive error handling.

Sources:

- `https://docs.python.org/3.15/library/ast.html#ast.parse`
- `https://docs.python.org/3.15/builtins/functions.html#compile`

## 10. Consequential capability interactions

The preceding additions make several combinations of native functionality particularly important.

| Combined capabilities                                      | What they enable                                                      | Remaining boundary                                   |
| ---------------------------------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------- |
| Assignment and binding representations + `symtable`        | Lexically informed definition/reference extraction                    | Occurrence-level correlation and runtime resolution  |
| `comprehension` nodes + PEP 709-aware scope information    | More accurate comprehension-local and enclosing-scope analysis        | Explicit modeling of evaluation and dataflow         |
| AST class patterns + `NodeVisitor`                         | Concise recursive recognition of selected syntax structures           | Traversal state, scope, and semantic inference       |
| Source coordinates + original source and token information | More precise excerpts and source-linked transformations               | Exact source preservation and regenerated provenance |
| Import AST nodes + lazy-import configuration               | Distinguishing syntactic dependencies from potential loading behavior | Effective runtime configuration and dynamic imports  |
| AST constructors + explicit compiler flags                 | Controlled generation and compilation of Python code                  | Execution environment and behavioral correctness     |

The architectural significance is that many syntactic and lexical analyses can use CPython's own parser and compiler information rather than recreating those mechanisms.

At the same time, the boundaries between syntax, lexical resolution, compilation, and runtime behavior remain important. A capable analysis system benefits from representing these as distinct layers rather than treating any single representation as complete.

## Primary-reference editorial corrections

Two formatting issues in the original reference should be corrected independently of these capability additions.

First, the `ast.parse()` signature in §3.1 and the transformation example in §6.2 have lost line breaks. The latter consequently contains invalid Python syntax.

Second, repeated source-card fragments, favicon placeholders, and encoded whitespace artifacts should be removed. They are not primary-source evidence and interfere with the document's usefulness as a standalone technical reference.

These corrections do not require changing the guide's substantive organization or duplicating its existing explanations.

## Primary-source reference map for this addendum

| Subject                                        | Direct source                                                                 |
| ---------------------------------------------- | ----------------------------------------------------------------------------- |
| CPython AST grammar, node classes, and helpers | `https://docs.python.org/3.15/library/ast.html`                               |
| Python assignment and import semantics         | `https://docs.python.org/3.15/reference/simple_stmts.html`                    |
| Comprehensions and expression evaluation       | `https://docs.python.org/3.15/reference/expressions.html`                     |
| Decorators and pattern matching                | `https://docs.python.org/3.15/reference/compound_stmts.html`                  |
| Structural class-pattern protocol              | `https://docs.python.org/3.15/reference/datamodel.html#object.__match_args__` |
| Compiler-derived symbol tables                 | `https://docs.python.org/3.15/library/symtable.html`                          |
| `compile()` controls and exceptions            | `https://docs.python.org/3.15/builtins/functions.html#compile`                |
| Comprehension inlining                         | `https://peps.python.org/pep-0709/`                                           |
| Assignment expressions                         | `https://peps.python.org/pep-0572/`                                           |
| Structural pattern-matching specification      | `https://peps.python.org/pep-0634/`                                           |
| Python 3.15 lazy imports                       | `https://peps.python.org/pep-0810/`                                           |
| CPython 3.15.2 AST grammar source              | `https://github.com/python/cpython/blob/v3.15.2/Parser/Python.asdl`           |
| CPython 3.15.2 AST helper implementation       | `https://github.com/python/cpython/blob/v3.15.2/Lib/ast.py`                   |

## Concluding perspective

These additions principally deepen the original reference's treatment of the AST as a compiler-integrated syntax representation with important, but incomplete, semantic information.

Its richness lies not only in the number of node classes or the availability of transformations, but in how its structural information can be combined with the compiler's lexical analysis, explicit compilation controls, and Python's language semantics.

The most consequential distinctions are that syntactic containment is not always binding ownership; compiler scopes and AST structure are not necessarily one-to-one; source coordinates do not cover every grammatical component; and valid AST transformations do not automatically preserve program behavior.

Understanding these boundaries makes the standard library substantially more useful for advanced structural analysis, program generation, source intelligence, and compiler-oriented tooling, while clarifying where additional semantic or source-preserving machinery remains necessary.