# Astroid (Python): Comprehensive Technical and Capability Reference

Research date: November 12, 2026 | Current stable release: 4.3.4 (October 8, 2026)

Project: pylint-dev/astroid\
Repository: `https://github.com/pylint-dev/astroid`\
Documentation: `https://pylint.pycqa.org/projects/astroid/en/stable/`\
Package: `https://pypi.org/project/astroid/`

Compatibility: Python 3.10+, with published support classifiers through Python 3.14; CPython and PyPy.\
License: LGPL-2.1-or-later.\
Primary integration: Pylint.

The release and compatibility information above is verified against PyPI and the upstream release history. The discussion targets Astroid 4.3.4 rather than unreleased changes on the development branch.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



## 1. Executive overview

Astroid is an enriched Python abstract syntax tree and partial static inference engine. It transforms Python source code into a representation that understands more than syntax: lexical scopes, name bindings, imports, class hierarchies, attributes, function calls, potential expression values, and selected dynamic Python behaviors.

Where Python's built-in `ast` module primarily answers what syntax is present?, Astroid can also investigate what Python object or value could this expression represent?

Its distinctive capability is the combination of:

- Semantic AST construction: Rich nodes with parent relationships, scope information, source locations, and representation of Python's language constructs.
- Name and attribute resolution: Inspection of bindings, imports, class members, instance members, inheritance, and method resolution.
- Static value inference: Partial interpretation of expressions, functions, object construction, operations, and certain protocol behaviors.
- Context-sensitive reasoning: Inference of possible results with awareness of calls, bindings, and some branch constraints.
- Extensible Python semantics: Custom AST transforms, inference functions, synthetic module definitions, and special handling for dynamically generated APIs.
- Reusable analysis infrastructure: Building blocks for linters, dependency analyzers, semantic code exploration, API discovery, and other source-analysis systems.

Astroid is the semantic foundation of much of Pylint, but it is independently usable as a Python library. Its value lies in providing an existing Python semantic model rather than requiring consumers to reconstruct Python's binding and object-resolution rules from a basic syntax tree.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

pylint.pycqa.org+2



A particularly important architectural distinction is that Astroid is neither a full Python interpreter nor a complete static type checker. Its inference engine produces possible values and symbolic objects, not an authoritative execution trace or proof of program behavior. It can produce multiple possibilities, encounter ambiguity, or return an explicit unknown result.

This makes it a useful middle layer between syntactic parsing and heavyweight program analysis: considerably more expressive than a raw AST, while remaining a partial, extensible static model.

## 2. Architectural model: from Python source to semantic objects

Astroid's processing model has several distinct layers:

Python source, modules, and stubs

Syntax, imports, definitions, annotations

AST construction and enrichment

NodeNG hierarchy, scopes, locals, parent relationships, transforms

Semantic resolution and inference

Bindings, imports, MRO, calls, attributes, branch constraints, brain models

Consumer-specific analysis

Diagnostics, API models, call relationships, dependency indexes, semantic queries

The bottom layer is deliberately outside Astroid's responsibilities. Astroid supplies semantic primitives; the calling application decides which facts to extract, how to persist them, and what conclusions to draw.

### 2.1 The `NodeNG` object model

Astroid constructs a hierarchy derived from `astroid.nodes.NodeNG`. Nodes resemble Python's built-in AST objects but have their own types, methods, and semantic state.

Consequential capabilities include:

| Capability              | Principal API                                          | Significance                                                                    |
| ----------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------- |
| Hierarchical traversal  | `get_children()`, `nodes_of_class()`                   | Discover syntactic constructs without implementing visitors for every node type |
| Context navigation      | `parent`, `node_ancestors()`, `root()`                 | Recover enclosing syntax and module identity                                    |
| Scope navigation        | `scope()`, `frame()`                                   | Identify the relevant lexical environment                                       |
| Statement association   | `statement()`                                          | Associate an expression with its enclosing executable statement                 |
| Source mapping          | `lineno`, `col_offset`, `end_lineno`, `end_col_offset` | Attach findings to source locations                                             |
| Structural inspection   | `repr_tree()`                                          | Examine the enriched tree and its fields                                        |
| Source reconstruction   | `as_string()`                                          | Produce source-like output from a node                                          |
| Semantic interpretation | `infer()`, `inferred()`                                | Obtain possible symbolic values                                                 |

`nodes_of_class()` can traverse descendants selectively, including excluding subtrees of specified classes. That distinction matters for analyses that, for example, inspect a function's own body without accidentally incorporating nested function definitions.

Astroid also exposes structural field metadata such as `_astroid_fields`, which identifies child-node attributes. This is useful for generic tree walkers and extension authors.

Important boundary: Astroid nodes are not interchangeable with `ast.AST` nodes. Their fields, semantics, construction requirements, and inference behavior differ. An analyzer written for CPython's `ast` cannot be assumed to accept Astroid trees unchanged.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 3.3.6 documentation+1



Sources:\
`https://pylint.pycqa.org/projects/astroid/en/stable/api/base_nodes/astroid.nodes.NodeNG.html`\
`https://pylint.pycqa.org/projects/astroid/en/stable/extending.html`

### 2.2 Semantic node families

Astroid represents ordinary expressions and statements, but the distinction between superficially similar node types matters.

For example, `Name` represents a name reference whereas `AssignName` represents an assignment target. Similarly, `Attribute` represents an attribute access whereas `AssignAttr` represents an attribute assignment. This lets consumers distinguish reading a symbol from establishing or modifying a binding without reconstructing assignment context themselves.

The major families include modules and scopes (`Module`, `ClassDef`, `FunctionDef`, `AsyncFunctionDef`, `Lambda`); bindings and imports (`Name`, `AssignName`, `AssignAttr`, `Import`, `ImportFrom`, `Global`, `Nonlocal`); expression evaluation (`Call`, `Attribute`, `BinOp`, `Compare`, `Subscript`, comprehensions); and flow constructs (`If`, `Try`, `TryStar`, `Match`, loops, generators, context managers, and asynchronous statements).

Modern Python syntax is represented with dedicated nodes, including `TypeAlias`, `TypeVar`, `ParamSpec`, `TypeVarTuple`, structural pattern matching, and Python 3.14's `TemplateStr` and `Interpolation`. Syntax support must not be confused with complete inference support for every construct.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.4 documentation+1



### 2.3 Building and inspecting trees

The entry points serve different purposes:

| Entry point                             | Use                                                                             |
| --------------------------------------- | ------------------------------------------------------------------------------- |
| `astroid.parse(source)`                 | Build a module tree from source text                                            |
| `astroid.extract_node(source)`          | Isolate particular nodes, especially in focused analyses and tests              |
| `AstroidBuilder`                        | Build trees from strings, files, or module objects with configurable transforms |
| `AstroidManager.ast_from_module_name()` | Resolve a module by Python import name                                          |
| `AstroidManager.ast_from_file()`        | Construct a module from a known file                                            |
| `AstroidManager.ast_from_module()`      | Construct from a live Python module                                             |

`extract_node()` is unusually convenient for semantic experiments: its documented `#@` markers can identify expressions or statements of interest without writing a full traversal.

The lower-level builder supports `apply_transforms`, making it possible to distinguish an unmodified syntax-derived representation from one enriched by registered transforms. This is useful when debugging whether a result originates in source syntax or in an extension.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.4 documentation+1



## 3. Static inference: Astroid's defining capability

The central API is `NodeNG.infer(context=None)`.

Rather than returning a single answer, it yields an iterator of possible inference results. This matters because a Python expression can legitimately have several possible values, and static analysis frequently cannot determine which execution path occurs.

### 3.1 Expression evaluation and function calls

Consider:

```
import astroidmodule = astroid.parse("""def combine(a, b):    return a + bleft = 4right = 7combine(left, right)""")expression = module.body[-1].valueresults = list(expression.infer())for result in results:    print(type(result).__name__, getattr(result, "value", None))
```

For this straightforward example, the inference engine can follow the call arguments through the function body and infer a `Const` with the value `11`. This is a static conclusion; Astroid does not need to invoke `combine` through Python execution.

The same basic mechanism underlies resolution of many literal operations, assignments, container operations, simple function returns, calls, and known Python object protocols. It is not unrestricted partial execution: unsupported behavior, side effects, recursion, dynamic dispatch, and ambiguous inputs can prevent a conclusive result.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

pylint.pycqa.org+1



### 3.2 Inference results are richer than syntax nodes

Astroid can return either ordinary nodes or symbolic inference objects not present in the original source tree.

| Result                                                                | Meaning                                                                                  |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `Const`                                                               | A known constant, exposed through `.value`                                               |
| `ClassDef`                                                            | A class definition                                                                       |
| `FunctionDef` / `Lambda`                                              | A function-like definition                                                               |
| `Module`                                                              | A resolved module                                                                        |
| `Instance`                                                            | A symbolic instance of a known class                                                     |
| `BoundMethod` / `UnboundMethod`                                       | A method with binding semantics                                                          |
| `Property`                                                            | A modeled Python property                                                                |
| `Generator` / `AsyncGenerator`                                        | Generator-related proxy objects                                                          |
| `Super`, `FrozenSet`, `PartialFunction` and related inference objects | Representations of Python behavior that cannot always be captured by a source node alone |
| `Uninferable`                                                         | An explicit unknown result                                                               |

This separation is fundamental. For instance, an `Instance` is not necessarily an actual constructed Python object; it is an Astroid proxy representing an object of a particular class.

The proxy model means an analysis can determine which class an expression appears to instantiate, or which methods could be available, without instantiating the application object.

Sources:\
`https://pylint.pycqa.org/projects/astroid/en/stable/inference.html`\
`https://pylint.pycqa.org/projects/astroid/en/stable/api/general.html`

### 3.3 Uncertainty, ambiguity, and failure

Three conditions must remain distinct.

Known inference: The iterator yields a result that can be interpreted, such as `Const(value=11)`.

Multiple possibilities: The iterator yields more than one result. Consumers must preserve ambiguity rather than arbitrarily choosing the first result.

Unknown or failed inference: The engine yields `Uninferable` or encounters an inference error. These are not proofs that the referenced Python value does not exist.

The helper `astroid.util.safe_infer()` provides a convenient single-result interface, returning `None` when inference fails or multiple results make it ambiguous. There is an important nuance: an explicit `Uninferable` result is not equivalent to a successful value inference, and callers should test for it rather than treating every non-`None` result as resolved.

Astroid also exposes `bool_value()`, which can distinguish true, false, and unknown truthiness. `callable()` and node-specific operation methods provide narrower semantic questions without necessarily requiring full value materialization.

This suggests a useful general distinction for downstream data models: syntactically observed, semantically resolved, ambiguous, and unknown should not collapse into one category.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.4 documentation+1



### 3.4 Context-sensitive inference

Astroid's `InferenceContext` carries state that influences how a result is inferred. It includes call-related information, bound-object information, recursion tracking, inference caching, and constraints.

Its practical role is to avoid evaluating expressions in isolation when additional context is known. For example, the meaning of `self` inside an inherited method can depend on the subclass instance through which the method was accessed; similarly, an inferred function return may depend on the arguments to a particular call.

Astroid has progressively introduced inference narrowing based on conditions:

| Release | Documented enhancement                                                      |
| ------- | --------------------------------------------------------------------------- |
| 4.0     | Boolean truthiness constraints and ternary-expression constraints           |
| 4.1     | Equality/inequality constraints and `isinstance()`-based type constraints   |
| 4.3     | Additional narrowing in comprehensions, including some filtered-value cases |

These capabilities make inference more useful than naive collection of every assignment in a scope.

They do not establish that Astroid performs exhaustive path-sensitive interpretation, SSA construction, complete data-flow solving, or mathematical proof of reachability. Its constraints are selective mechanisms within a bounded inference engine.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.3 documentation+1



Sources:\
`https://pylint.pycqa.org/projects/astroid/en/stable/api/context/astroid.context.InferenceContext.html`\
`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/constraint.py`

## 4. Name resolution, scopes, and binding analysis

Astroid's semantic scope model is valuable independently of its ability to infer exact values.

### 4.1 Binding dictionaries versus inferred meanings

Scope-bearing nodes expose a `.locals` mapping from names to their defining nodes. A module, class, or function can therefore expose the definitions associated with a symbol without requiring a custom symbol-table pass.

This distinction is important:

- `scope.locals["item"]` identifies definitions or assignments registered in that scope.
- `node.lookup("item")` performs contextual name lookup.
- `node.infer()` attempts to determine the possible meanings or values of an expression.

These answer different questions. A symbol can be definitely declared but not have a reliably inferable runtime value. Several assignment nodes can also contribute to one name.

Astroid accounts for Python constructs such as nested lexical scopes, global and nonlocal declarations, imported names, assignment targets, and comprehension scopes. Its lookup machinery is therefore considerably more expressive than a dictionary of identifiers extracted from source text.

However, `.locals` is not equivalent to a location-specific program state. To determine what a reference may mean at a particular point, use contextual lookup or inference rather than interpreting every registered assignment as simultaneously valid.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.2.0 documentation+1



### 4.2 Qualified identity and aliases

Scoped definitions expose `qname()`, providing hierarchical names such as `package.module.Class.method` when module identity is known.

This enables stable-looking semantic identifiers for modules, classes, and functions. But qualified names have limitations as universal symbol identities.

A name reference or attribute expression does not automatically possess the identity of its target. For example, an imported alias must first be resolved to determine the referenced definition. Furthermore, several aliases can refer to the same object, and names can be rebound at runtime.

For program indexing, a useful distinction is between the declaration's qualified identity, the textual reference appearing in source, and the inferred target or targets. These should be modeled separately if ambiguity, aliasing, or historical changes matter.

Astroid's `.qname()` and inference APIs provide the components, not a comprehensive persistent identity system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.2.0 documentation+1



### 4.3 Assignment and reference relationships

Astroid can expose assignment relationships through methods such as `assigned_stmts()`, while its traversal API can distinguish stores from loads and find enclosing statements.

This supports analyses of binding provenance, including relationships between destructuring targets, assignment values, references, and imported definitions.

For example, a statement like:

```
left, right = source
```

contains two assignment targets associated with a common source expression. A parser-only analysis can record this syntactic relationship, while Astroid can additionally attempt to infer elements of `source` where their values are statically known.

This makes Astroid useful for constructing a partial data-dependency representation. It does not itself provide a complete SSA graph, interprocedural data-flow graph, alias analysis, or whole-program def-use index. Those are additional analyses that can consume its semantic results.

### 4.4 Module-level dependency semantics

Import nodes preserve syntax, while the manager's module-resolution and inference machinery can locate the imported module or symbol. This is helpful when textual import paths differ from the effective target because of relative imports, aliases, re-exports, or package layout.

The distinction between `import package.module` and `from package.module import symbol` remains significant. A static dependency graph can often be refined beyond raw import strings, but the engine cannot be expected to discover every runtime import performed through dynamic loading or arbitrary program execution.

Astroid can help identify resolvable import edges. A complete runtime dependency inventory requires other evidence.

## 5. Python object semantics and class analysis

Astroid's object model is one of the most consequential reasons to use it instead of a basic syntax tree.

### 5.1 Inheritance and method resolution

`ClassDef` exposes class-hierarchy functionality through methods including `ancestors()`, `mro()`, `methods()`, `mymethods()`, `metaclass()`, and related class-inspection operations.

These allow consumers to reason about relationships among a class's declared bases, inherited behavior, member lookup, and effective Python method resolution.

`mro()` is especially useful when multiple inheritance makes the effective lookup order differ from the syntactic list of bases. An API analyzer can distinguish the class in which a method was defined from the class on which it becomes accessible.

The model also exposes class-specific conditions such as dataclass recognition, subtype checks, and `__slots__` information.

Inheritance resolution remains conditional on successfully inferring bases. Invalid, circular, or dynamically generated hierarchies may produce errors or unknown results rather than a complete hierarchy.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.2.0 documentation+2



### 5.2 Class attributes versus instance attributes

Astroid deliberately separates member lookup in class context from member lookup on instances.

A `ClassDef` maintains class-local bindings, while `instance_attrs` describes instance attributes discovered through analysis. The `Instance` proxy handles instance-side lookup, including inherited instance members.

The documented `ClassDef.getattr()` method does not simply merge these two namespaces. It accounts for class-context behavior, potentially including lookup on the class's metaclass. The corresponding `igetattr()` interface performs inference of possible attribute values.

This distinction matters for Python code such as:

```
class Configuration:    default = 10    def __init__(self, value):        self.value = value
```

`default` is established in the class body, whereas `value` is an instance attribute assigned through `self`. Modeling them as identical declarations would obscure their semantics.

Astroid can also recognize some dynamically supplied members and return an unknown result for unresolved attribute lookup when `__getattr__` or `__getattribute__` is involved. That is not equivalent to evaluating an arbitrary dynamic attribute provider.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.2.0 documentation+1



### 5.3 Methods, binding, and descriptors

The inference layer distinguishes ordinary functions from bound and unbound methods. It models important binding behavior involving `self`, `cls`, `staticmethod`, `classmethod`, properties, and selected descriptor patterns.

This enables richer questions than simply finding functions nested within classes. For instance, inference can attempt to determine how a method call's implicit receiver affects the returned object.

`super()` is a particularly subtle case. The 4.3 release corrected resolution for zero-argument `super()` so the inferred behavior follows the actual calling object's class rather than always using the class where the method was defined. This also improves inference through chains involving `typing.Self`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.4 documentation



### 5.4 Built-in object models

Astroid provides special attribute models separate from ordinary source definitions. The `astroid.interpreter.objectmodel` layer includes models for modules, classes, functions, instances, bound and unbound methods, `super`, generators, exceptions, dictionaries, and properties.

This captures object behavior that otherwise would require every analyzer to reconstruct special Python attributes and lookup rules.

The object models work alongside source-derived syntax and inference. A property such as `__class__` need not be represented by a literal assignment in the analyzed source to be meaningful to Astroid.

This is an easily overlooked architectural capability: Astroid models aspects of Python's object protocol, not merely user-authored source declarations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.4 documentation+1



Source:\
`https://pylint.pycqa.org/projects/astroid/en/stable/api/nodes/astroid.nodes.ClassDef.html`

## 6. Function, signature, and typing information

### 6.1 Source-level signatures

Function nodes expose their argument representation, decorators, body, return annotation, and contextual relationships.

The `Arguments` model handles Python's parameter categories: positional-only, regular positional, variadic positional, keyword-only, and variadic keyword parameters. It also exposes defaults and annotations, including the `get_annotations()` helper introduced in 4.1.

This can support structural API discovery, signature inspection, and comparison of declared function contracts.

However, the function's source signature and its effective callable behavior can differ. Decorators, wrappers, dispatch mechanisms, generated `__init__` methods, callable objects, and other runtime transformations can alter behavior or the visible API. Astroid models some important cases but does not guarantee reconstruction of every effective signature.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.3 documentation



### 6.2 Annotation syntax versus resolved types

Astroid represents annotations as syntax and can infer selected typing-related constructs. Its typing models handle common abstractions such as type variables, aliases, `NewType`, `NamedTuple`, and `TypedDict`.

Recent releases improved PEP 695 generic representations, Python 3.13 type parameter defaults, and qualified-name behavior for typing nodes. Version 4.3 also improved inferred `TypedDict` attributes such as `__required_keys__` and `__optional_keys__`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.4 documentation+1



The critical distinction is that a type annotation is a declared constraint or description, not an observed runtime value. Astroid's ability to resolve some annotations does not make it a general replacement for a static type checker implementing full generic constraint solving, variance, overload selection, and protocol compatibility.

Conversely, Astroid's value inference can sometimes resolve concrete values that are not inferable from type annotations alone.

### 6.3 Declaration inspection and synthesized behavior

Dataclasses, `attrs`, named tuples, and similar constructs can produce effective APIs through decorators or factory functions.

Astroid's inference and brain extensions can expose portions of these generated structures as semantic nodes, allowing consumers to reason about attributes or methods that are not written explicitly in the original source.

The distinction between declared members and synthesized or inferred members is therefore essential when using Astroid for API modeling. An effective member can be valid for consumers even when its source location does not correspond to a normal explicit declaration.

For precise change detection, retaining both representations is generally more informative than collapsing them into a single member list.

## 7. Extension architecture: teaching Astroid new semantics

Astroid's extensibility is a defining feature, not an incidental customization facility. Python libraries routinely construct APIs through decorators, descriptors, metaclasses, factories, and runtime imports. Astroid provides several mechanisms to express the resulting semantics without rewriting its inference engine.

### 7.1 AST transformations

`AstroidManager.register_transform()` associates a transformation with a node class and, optionally, a predicate.

A transform can modify an existing node or return a replacement node. This supports structural normalization, synthetic declarations, and adjustments to how an API is represented.

The registration mechanism has three conceptual components:

| Component               | Purpose                                                             |
| ----------------------- | ------------------------------------------------------------------- |
| Target node class       | Determines which kinds of nodes are eligible                        |
| Predicate               | Restricts the transformation to nodes matching the intended pattern |
| Transformation function | Alters or replaces the eligible node                                |

Predicates are particularly important. A broad transformation registered against every `Call` node can unintentionally modify unrelated expressions, whereas a narrowly matched predicate limits its semantic impact.

Low-level node construction carries obligations. Newly constructed nodes must have appropriate parent relationships, and node-specific child fields may need initialization through `postinit()`. Incorrectly constructed trees can break subsequent navigation and inference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.4 documentation



### 7.2 Custom inference functions

An inference tip changes how Astroid reasons about a specific expression without necessarily changing its syntax representation.

The main APIs are `astroid.inference_tip()` and `AstroidManager.register_transform()`.

A compact illustrative example:

```
from astroid import MANAGER, inference_tip, nodesdef matches_factory(node):    return (        isinstance(node.func, nodes.Name)        and node.func.name == "known_factory"    )def infer_factory_result(node, context=None):    yield nodes.Const(value=42)MANAGER.register_transform(    nodes.Call,    inference_tip(infer_factory_result),    matches_factory,)
```

This illustrates how a known factory call could be assigned custom inference behavior. It is not an executed test, and the textual-name predicate is deliberately simplistic: production extensions generally need to account for aliases, argument validation, and the intended target's identity.

The inference callback accepts the node and an optional inference context and returns an iterator of results.

A consequential detail is that an inference tip can override the previously assigned inference function for that node. The `raise_on_overwrite` argument helps detect accidental collisions. Custom rules should not be assumed to automatically combine with Astroid's default inference or other tips.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.4 documentation



### 7.3 Synthetic modules and module extension

`register_module_extender()` supports enriching the semantic representation of an existing module.

The extender returns an Astroid `Module` containing additional definitions, which Astroid incorporates into the targeted module representation.

This is a simpler mechanism than directly manipulating many individual nodes when the objective is to describe a module's otherwise invisible public API.

For example, an application may expose an attribute dynamically through module-level `__getattr__`, a compiled extension, or runtime registration. A module extender can provide a static representation of known names, classes, or functions.

Such declarations are models of behavior, not evidence that the declarations exist literally in the original source. This provenance distinction should be retained when building documentation, source indexes, or API inventories.

### 7.4 Failed-import hooks

`AstroidManager.register_failed_import_hook()` provides another extension boundary.

The hook receives a module name that normal resolution could not find. It may return a synthetic `Module` or raise `AstroidBuildingError` if it cannot resolve that name.

This is valuable for virtual modules, generated imports, dynamically registered packages, and runtime-dependent environments.

Unlike a module extender, a failed-import hook addresses an unresolved module, rather than enriching a module Astroid has already resolved.

Source for all four extension mechanisms:\
`https://pylint.pycqa.org/projects/astroid/en/stable/extending.html`\
`https://pylint.pycqa.org/projects/astroid/en/stable/api/manager/astroid.manager.AstroidManager.html`

### 7.5 Built-in brain modules

Astroid ships with brain modules, which encode specialized knowledge of Python libraries and runtime behaviors that generic source inference cannot adequately reconstruct.

The upstream source contains brain modules for, among others, `dataclasses`, `attrs`, `typing`, named tuples and enums, `functools`, `collections`, NumPy, `decimal`, `pathlib`, `sqlalchemy`, `boto3`, `pytest`, `hypothesis`, Qt, and various standard-library modules.

These brains are not all equivalent in scope. One might provide synthetic attributes, another might special-case a factory call, and another might model a return type. The presence of a brain module does not establish comprehensive support for the corresponding library.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Several examples illustrate the architecture.

Dataclasses and attrs. The library can account for selected generated initialization and attribute behavior, making otherwise implicit members visible to static analysis.

Named tuples and enums. Factory calls may create classes with fields that are not directly present as ordinary source-level class declarations. Brain inference can synthesize the relevant class model.

Typing constructs. Specialized models help Astroid reason about constructs such as `NamedTuple`, `TypedDict`, `TypeVar`, and other typing-related forms.

NumPy. Brain modules cover selected arrays, operations, and return types. For example, 4.3 added inference for `numpy.fromfile()` returning a NumPy array rather than an unknown result. This does not constitute general NumPy shape inference or full numerical type analysis.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.4 documentation



The architectural value is that a customized semantic model can be reused across many analyses. Rather than every consumer implementing the same dataclass or factory recognition logic, the model becomes part of the common inference layer.

Source tree:\
`https://github.com/pylint-dev/astroid/tree/main/astroid/brain`

## 8. Import resolution, stubs, and live-object inspection

### 8.1 `AstroidManager` as shared infrastructure

`AstroidManager` is responsible for module construction, resolution, caching, and transformation registration.

Its documentation describes a Borg-style shared-state implementation. Multiple manager instances therefore should not automatically be treated as fully independent analysis environments.

Important configuration surfaces include:

| Configuration or operation    | Role                                            |
| ----------------------------- | ----------------------------------------------- |
| `ast_from_module_name()`      | Resolve and build a module using an import name |
| `ast_from_file()`             | Build from a particular source file             |
| `ast_from_module()`           | Build from a live module object                 |
| `ast_from_class()`            | Build a class representation from a live class  |
| `prefer_stubs`                | Control preference for `.pyi` representations   |
| `module_denylist`             | Exclude selected modules from normal handling   |
| `extension_package_whitelist` | Configure supported extension-module handling   |
| `always_load_extensions`      | Control extension loading behavior              |
| `max_inferable_values`        | Bound the number of inferred possibilities      |
| `optimize_ast`                | Control AST optimization behavior               |
| `clear_cache()`               | Reset caches and rebuild required manager state |

The documented manager state initializes `max_inferable_values` to 100 and `prefer_stubs` to `False` in the inspected 4.3-series API. These are configuration values, not universal completeness guarantees.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.1 documentation



### 8.2 Python module discovery

Astroid supports source-based module resolution using Python package and import semantics, including relative imports and namespace packages.

This capability is important because the text appearing in an `ImportFrom` node does not always uniquely identify a filesystem path or a single declaration. Resolution depends on package context, import search paths, and module type.

A module-analysis system can therefore use Astroid to help normalize imports into semantic targets rather than maintaining its own approximation of Python's import rules.

Yet module resolution is environment-sensitive. The same import name can resolve differently in different Python environments, installed package versions, or search-path configurations. Resolved module identities should therefore be understood as facts about a specified analysis environment, not intrinsic properties of a source string.

### 8.3 `.pyi` stub support

Astroid supports Python interface stub files and exposes the `prefer_stubs` manager option.

The release history shows that `.pyi` handling was enhanced in Astroid 3.2, followed by configuration to control precedence. The choice remains semantically significant.

A stub may document declarations and types that are absent from, or only dynamically generated by, an implementation module. Conversely, it may omit executable statements and internal details present in `.py` files.

Thus the preferred representation depends on the analysis:

| Objective                          | Relevant distinction                                                                                     |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Public API inspection              | Stubs may express the intended interface more directly                                                   |
| Implementation dependency analysis | Source files generally expose the implementation relationships                                           |
| Runtime behavior inference         | Stubs contain contracts, not executable implementations                                                  |
| API compatibility comparison       | Comparing both declared interface and inferred implementation behavior can expose meaningful differences |

This is a general architectural implication of the available source and stub representations, not a guarantee that Astroid reconciles all inconsistencies between them.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.3 documentation+1



### 8.4 Introspection of live Python objects

Astroid is not restricted to parsing source files. It can build partial representations from live modules or classes.

This is particularly relevant to built-ins and extension modules whose behavior is not fully described by ordinary Python source. Astroid's builder and manager can use runtime inspection to supply information unavailable from a `.py` file.

There is an important execution boundary: parsing a supplied source string is different from resolving or introspecting an installed module. The latter can involve imports and loaders, and importing Python modules can execute their initialization code.

For analysis of untrusted projects, Astroid's static inference capabilities should not be interpreted as an assurance that every module-resolution operation is side-effect-free. Isolated environments and controlled module-loading policies may be warranted.

The 4.3.4 release specifically fixed recursion problems involving live objects and classes referencing themselves through their attributes, further demonstrating that live-object inspection is a supported and nontrivial part of the implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.1 documentation+1



## 9. Performance, caching, and semantic reliability

### 9.1 Why inference needs limits

Inference can branch rapidly as possible values multiply.

Suppose an expression depends on several uncertain values. Combining their possibilities can produce many inference paths, especially when calls, inheritance, or multiple assignments are involved.

Astroid uses inference contexts, recursion tracking, caching, and configurable limits to make this tractable.

The default `max_inferable_values` configuration is 100, and Astroid can return `Uninferable` rather than continuing an excessive calculation. This is a practical engineering tradeoff: finite analysis cost is prioritized over exhaustive value enumeration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.1 documentation+1



The cap should not be mistaken for a guarantee that 100 values will represent all possibilities or that the engine will always explore alternatives in a semantically complete manner.

### 9.2 Caching and reuse

Astroid caches constructed modules and inferred results. The global inference cache can be used even when the caller does not supply an explicit `InferenceContext`.

This reduces repeated work for shared expressions, dependencies, and module representations. It can be valuable in analyzers that repeatedly ask related semantic questions.

The tradeoff is lifecycle management.

A cached result is associated with the semantic state in which it was produced. If source content, imported dependencies, configuration, transforms, or synthetic module definitions change, a previously cached result may no longer describe the intended environment.

`AstroidManager.clear_cache()` clears relevant caches, rebuilds required built-in state, and re-registers built-in transformations.

For long-lived analysis services, a correct invalidation strategy must therefore account for more than modifications to the source text of one module. Dependency versions, analysis configuration, transform definitions, and the inference environment may also be semantically relevant.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.1 documentation+1



### 9.3 A current inference-cache caveat

An upstream issue opened on October 12, 2026 reports that inference results truncated by an inference budget can be cached and subsequently reused in a way that makes later results dependent on analysis order.

The issue remains open in the retrieved upstream tracker. The report includes a reproducer and describes the behavior in a development environment, but this research did not independently reproduce it on Astroid 4.3.4. It should therefore be treated as a reported issue worth investigating, not a verified universal characteristic of the stable release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Issue:\
`https://github.com/pylint-dev/astroid/issues/3383`

### 9.4 Protection against expensive inferred operations

Astroid 4.3 introduced additional safeguards against constructing enormous inferred values.

These cover scenarios such as oversized string repetition, concatenation, large integer shifts, formatting widths, and large container constructions.

The motivation is important: a static analyzer may encounter source code that expresses a huge value without ever needing that value to perform its primary analysis. Eagerly constructing the inferred object could consume excessive memory or CPU time.

For supported cases, Astroid now declines expensive inference and returns an unknown result instead.

This improves resilience, but it also illustrates the fundamental distinction between statically representable expressions and expressions the engine will actually evaluate under its resource policy.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.2 documentation



### 9.5 Failure modes and completeness

Astroid distinguishes different classes of inference and construction failures, including `InferenceError`, `NameInferenceError`, `AttributeInferenceError`, and module-building errors.

Consumers should treat these errors in context.

A failed import may mean the analysis environment is incomplete. A name-inference failure may mean a symbol is dynamically supplied. A class-hierarchy failure may arise from invalid or unresolved bases. An unknown operation result may be an intentional complexity limit.

These are not interchangeable findings, and none automatically proves that the analyzed program will fail at runtime.

A reliable semantic consumer should avoid promoting a partial inference result into a claim of exhaustive program correctness.

## 10. Version 4.x: consequential changes

The 4.x release line includes both expanded semantics and API changes relevant to developers integrating Astroid directly.

| Version                             | Important development                                                                                                                                                                     |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 4.0.0 — October 2025                | Python 3.9 support removed; boolean and conditional inference constraints; Python 3.14 template-string nodes; PEP 695 improvements; node-class imports from the `astroid` root deprecated |
| 4.1.0 — February 2026               | Equality and `isinstance()` constraints; `Arguments.get_annotations()`; simple `python -m astroid` AST-output CLI                                                                         |
| 4.1.2 — March 2026                  | Fixes for recursive constraints, MRO recursion, and dataclass inheritance cases                                                                                                           |
| 4.3.0 — August 2026                 | Comprehension narrowing; improved `super()` and `Self`; typing and NumPy brain changes; resource bounds; inference signature changes                                                      |
| 4.3.1–4.3.3 — August–September 2026 | Named-tuple handling, inference correctness, and robustness fixes                                                                                                                         |
| 4.3.4 — October 2026                | Live-object recursion fixes, argument-default corrections, and more conservative failure results                                                                                          |

The `4.2.0` stable version was skipped. An upstream release tag was created during an aborted attempt, and the changes subsequently shipped in 4.3.0.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.3 documentation+1



Two specific compatibility changes deserve attention.

First, importing node classes directly from the `astroid` top-level namespace is deprecated. The recommended form is:

```
from astroid import nodesif isinstance(node, nodes.ClassDef):    ...
```

Second, Astroid 4.3 removed arbitrary `**kwargs` from inference methods. Direct callers should pass `context` rather than relying on previously accepted keyword arguments.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.3 documentation+1



There is also a practical documentation caveat: individual API pages returned by search indexes may be cached from earlier Astroid releases even while the stable documentation landing page identifies 4.3.4. Where signatures differ, the pinned release source and release notes should be preferred over an older generated API page.

Sources:\
`https://pylint.pycqa.org/projects/astroid/en/stable/whatsnew/4/4.3/index.html`\
`https://pylint.pycqa.org/projects/astroid/en/stable/changelog.html`\
`https://github.com/pylint-dev/astroid/tree/v4.3.4`

## 11. Integration boundaries and complementary tooling

Astroid occupies a specific position within the Python analysis ecosystem.

| Tool or layer                                 | Primary responsibility                                          | Relationship to Astroid                                           |
| --------------------------------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------- |
| Python `ast`                                  | Syntax parsing and basic AST manipulation                       | Astroid rebuilds a richer semantic representation                 |
| Astroid                                       | Scopes, lookup, object models, partial inference                | Provides semantic primitives to downstream consumers              |
| Pylint                                        | Lint rules, diagnostics, checkers, reporting                    | Uses Astroid as a major analysis foundation                       |
| Static type checkers such as Pyright and mypy | Type compatibility and type-constraint analysis                 | Can provide type information outside Astroid's inference scope    |
| LibCST                                        | Concrete syntax-preserving inspection and transformation        | Better suited to formatting-preserving source rewrites            |
| Semantic indexes or graph stores              | Persistent identities, relationships, queries, and invalidation | Can consume Astroid-derived facts but are not provided by Astroid |

### 11.1 Where Astroid can replace bespoke analysis

Astroid can remove substantial custom machinery when the desired problem is grounded in Python language semantics.

Its existing scope, import, call, attribute, class, and inference machinery can support analyses that would otherwise need separate implementations of lexical binding, method resolution, builtin semantics, and common dynamic-library behaviors.

These capabilities are especially valuable when composed: a syntactic call expression can be associated with its lexical scope, resolved through an imported alias, inferred as a bound method, and associated with a class hierarchy.

That is materially more informative than storing only the called function's textual name.

### 11.2 Where supplementary analysis remains necessary

Astroid does not provide a complete representation of all runtime behaviors or a persistent program-analysis database.

A sophisticated downstream analyzer may additionally require whole-program call-graph construction, control-flow and data-flow analysis, precise mutation and alias tracking, type-constraint solving, a stable cross-version identity scheme, dependency invalidation, or concrete source transformations.

The presence of `.infer()` should not be taken to imply that these analyses are fully solved.

In particular, source editing deserves separation from semantic analysis. `as_string()` can reconstruct source-like text, and Astroid transformations can change the tree, but an abstract syntax tree does not preserve every comment, whitespace choice, or formatting detail. A concrete syntax tree is more appropriate when lossless editing is required.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.4 documentation



### 11.3 A useful distinction for semantic API models

Astroid supports several qualitatively different kinds of evidence:

| Evidence category   | Example                                         | What can be established                      |
| ------------------- | ----------------------------------------------- | -------------------------------------------- |
| Explicit syntax     | A declared function parameter                   | The parameter occurs in the source           |
| Structural binding  | An assignment recorded in `.locals`             | The name is defined in the analyzed scope    |
| Semantic resolution | An import or attribute resolves to a definition | A likely referenced declaration              |
| Inferred behavior   | A function call yields a known `Const`          | A statically derivable possible value        |
| Synthetic modeling  | A dataclass brain supplies an effective member  | A modeled API feature not explicitly written |
| Unknown result      | An expression yields `Uninferable`              | The analysis cannot conclude a value         |

This taxonomy is an architectural inference from Astroid's APIs, rather than an official Astroid data-model schema.

It highlights an important design opportunity: Astroid can serve as a semantic evidence source without requiring downstream systems to treat every inference result as ground truth.

For API comparison or dependency analysis, explicit declarations, inferred targets, and synthesized behavior should remain distinguishable. A change to an implementation body need not alter the declared interface, while a change to a decorator or inherited base can alter effective behavior without modifying the local declaration.

Astroid provides useful machinery for detecting such differences, but it does not decide which semantic changes are equivalent, nor does it implement a complete change-invalidation policy.

## 12. Principal limitations and decision boundaries

The most important limitations follow directly from Astroid's design.

Inference is partial. Unknown results are expected, particularly for dynamic behavior, side effects, recursion, external state, and unsupported operations.

Results are not necessarily unique. Multiple possible values must be interpreted as ambiguity rather than silently reduced to one answer.

Source declarations and effective Python behavior can differ. Brain modules improve coverage but cannot guarantee complete modeling of decorators, metaclasses, or arbitrary dynamically generated APIs.

Analysis depends on its environment. Installed package versions, module search paths, source/stub preference, loading behavior, and registered transforms affect results.

Inference has finite budgets. Returning `Uninferable` may be a resource-management decision rather than evidence that an expression is intrinsically impossible to resolve.

Manager state is shared. Caches and transforms require deliberate lifecycle handling when reusing Astroid across successive or independent analyses.

Generated nodes may lack ordinary source provenance. An inferred or synthetic value should not automatically be assigned a real source declaration location.

Astroid is not a type checker, lossless rewriting engine, or whole-program analysis framework. Those responsibilities require complementary mechanisms.

These are not peripheral cautions: they determine how Astroid's strongest capabilities should be interpreted.

## 13. Primary-source reference map

The most useful starting points for deeper investigation are grouped below.

| Topic                                             | Direct source                                                                                           |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Library overview and examples                     | `https://pylint.pycqa.org/projects/astroid/en/stable/`                                                  |
| Inference semantics                               | `https://pylint.pycqa.org/projects/astroid/en/stable/inference.html`                                    |
| AST transforms, inference tips, module extensions | `https://pylint.pycqa.org/projects/astroid/en/stable/extending.html`                                    |
| General public API                                | `https://pylint.pycqa.org/projects/astroid/en/stable/api/general.html`                                  |
| `NodeNG` hierarchy                                | `https://pylint.pycqa.org/projects/astroid/en/stable/api/base_nodes/astroid.nodes.NodeNG.html`          |
| Class and inheritance APIs                        | `https://pylint.pycqa.org/projects/astroid/en/stable/api/nodes/astroid.nodes.ClassDef.html`             |
| Inference context                                 | `https://pylint.pycqa.org/projects/astroid/en/stable/api/context/astroid.context.InferenceContext.html` |
| Manager APIs                                      | `https://pylint.pycqa.org/projects/astroid/en/stable/api/manager/astroid.manager.AstroidManager.html`   |
| Built-in semantic models                          | `https://github.com/pylint-dev/astroid/tree/main/astroid/brain`                                         |
| Inference constraints                             | `https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/constraint.py`                               |
| Object models                                     | `https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/interpreter/objectmodel.py`                  |
| 4.3 release notes                                 | `https://pylint.pycqa.org/projects/astroid/en/stable/whatsnew/4/4.3/index.html`                         |
| Historical changes                                | `https://pylint.pycqa.org/projects/astroid/en/stable/changelog.html`                                    |
| Stable release source                             | `https://github.com/pylint-dev/astroid/tree/v4.3.4`                                                     |

## 14. Overall architectural significance

Astroid is best understood as a reusable Python semantic interpretation layer.

Its strongest contribution is not merely resolving imports or inferring constants. It is the way those capabilities compose: a richly structured AST, scoped bindings, Python object semantics, context-sensitive inference, specialized library models, and extensible rules all operate over a common representation.

This combination can significantly reduce the amount of custom semantic machinery required for advanced Python source analysis.

The most easily overlooked capabilities are its distinction between class and instance attributes, symbolic objects outside the original AST, configurable inference context, specialized object models, module extension hooks, built-in brain modules, and its ability to construct representations from both source and live objects.

The principal tradeoff is completeness. Astroid offers powerful partial semantic knowledge rather than an authoritative model of every possible Python execution.

For systems that preserve that distinction—and can separate observed syntax, resolved identities, inferred possibilities, and synthetic models—Astroid provides a substantial foundation for semantic analysis while leaving room for more specialized type, control-flow, dependency, and persistence machinery where needed.

# Astroid (Python) — Technical Capability Addendum

Research date: November 12, 2026 | Target version: Astroid 4.3.4, released October 8, 2026

This addendum supplements the original Astroid reference with capabilities that were missing or insufficiently developed. It concentrates on assignment provenance, public API discovery, control-flow relationships, function and generator semantics, operation-level inference, source metadata, and extension behavior.

All functionality discussed below is available in the 4.3.4 release unless otherwise qualified. The primary verification basis is the tagged upstream source rather than development-branch documentation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



## 1. Assignment protocols and binding provenance

Astroid's assignment model extends considerably beyond maintaining symbol tables and inferring the values of names. It provides a protocol-based mechanism for identifying which source expressions contribute to particular assignment targets, including assignments whose structure is more complicated than a simple name-to-expression relationship.

### 1.1 Three different levels of assignment analysis

The most useful distinction is between an assignment's syntactic origin, its binding relationship, and its inferred value.

| Mechanism                     | Question answered                                             | Principal APIs               |
| ----------------------------- | ------------------------------------------------------------- | ---------------------------- |
| Assignment ownership          | Which language construct establishes this binding?            | `assign_type()`              |
| Assigned-expression discovery | Which expression supplies the target's value?                 | `assigned_stmts()`           |
| Semantic evaluation           | What value or symbolic object could the expression represent? | `infer()`, `infer_lhs()`     |
| Scope-aware resolution        | Which assignments are relevant to a reference?                | `lookup()`, `scope_lookup()` |

`assign_type()` works through Astroid's assignment-node hierarchy, including `AssignTypeNode` and `ParentAssignNode`. The latter delegates to its parent, allowing an assignment target nested inside another construct to identify the controlling assignment.

`assigned_stmts()` is more specialized. It returns assignment-related expressions without requiring those expressions to be fully inferred. This preserves a useful intermediate relationship between source structure and semantic interpretation.

For example:

```
first, second = (10, 20)
```

The assignment protocol can associate the two targets with the corresponding elements of the right-hand-side tuple. An analysis does not need to infer the complete runtime meaning of every expression simply to recover the syntactic assignment relationship.

This separation makes it possible to preserve both the originating expression and the result of any successful inference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 1.2 Assignment forms supported by dedicated protocols

Astroid dispatches assignment handling according to the syntax construct responsible for the assignment.

Important categories include:

| Assignment form                  | Relevant representation                | Distinctive behavior                                                       |
| -------------------------------- | -------------------------------------- | -------------------------------------------------------------------------- |
| Ordinary and chained assignments | `Assign`                               | Relates one right-hand-side expression to one or more targets              |
| Annotated assignments            | `AnnAssign`                            | Separates the annotation from an optional assigned value                   |
| Augmented assignments            | `AugAssign`                            | Requires the previous left-hand-side value and the right-hand-side operand |
| Sequence destructuring           | `Tuple`, `List`, `Starred`             | Maps source elements to individual targets                                 |
| Loop targets                     | `For`, `AsyncFor`, `Comprehension`     | Obtains target values from iteration semantics                             |
| Context-manager bindings         | `With`, `AsyncWith`                    | Models assignments associated with context-manager entry                   |
| Function parameters              | `Arguments`                            | Resolves parameter bindings using function-call context                    |
| Exception handlers               | `ExceptHandler`                        | Models exception-object bindings                                           |
| Assignment expressions           | `NamedExpr`                            | Represents bindings introduced by `:=`                                     |
| Pattern matching                 | `MatchAs`, `MatchStar`, `MatchMapping` | Models captures established by matching patterns                           |

These protocols share a general interface but do not provide identical guarantees. In particular, resolving the expression assigned to a destructured target may itself require some inference of the source container.

The implementation therefore supports a spectrum of precision: direct syntactic association when possible, partial semantic interpretation when necessary, and an unknown result when the relationship cannot be resolved.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 1.3 Optional assignments and conditional bindings

`NodeNG.optional_assign` records whether a construct may fail to establish its target binding.

Astroid marks `For` and comprehension targets as optional because their input iterables may be empty. `NamedExpr` is also marked optional because its containing expression may not be evaluated.

This provides information that a basic symbol table cannot express.

Consider:

```
for item in collection:    process(item)print(item)
```

The source contains an assignment to `item`, but that assignment is not guaranteed to execute. Astroid's optional-assignment metadata makes the distinction explicit.

It remains a local structural indicator rather than a complete definite-assignment analysis. Whether a particular reference is safe depends on enclosing conditions, earlier assignments, and reachable control-flow paths.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 1.4 Augmented assignment and prior-value inference

Augmented assignments introduce a dependency on the previous state of the target.

For:

```
total += increment
```

the operation depends on both the existing value of `total` and the current value of `increment`.

Astroid exposes `infer_lhs()` on relevant target expressions to support this distinction. Its augmented-assignment inference obtains the left-hand-side and right-hand-side possibilities separately before attempting to apply the operator.

This is materially different from treating the statement as an ordinary assignment whose value is independently determined by its right-hand side.

The mechanism supports selected operations and object behaviors; it should not be mistaken for general mutation tracking or an SSA-based analysis of program state.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 1.5 Scope-relative lookup

`scope_lookup(node, name, offset=0)` is another important complement to the assignment protocols.

Rather than retrieving every assignment registered in a scope, it performs lookup relative to a specified node, taking account of the relevant scope and assignment-order filtering.

It returns the scope node and a collection of associated assignments.

This allows analyses to distinguish names that appear in the same function or module but are not necessarily relevant to the same reference.

Astroid also treats certain contexts specially, including expressions in function parameter defaults, which are evaluated in the enclosing scope rather than the function's own local parameter scope.

A complete data-dependency graph still requires additional reasoning about execution order, side effects, aliasing, and branch reachability. Nevertheless, Astroid supplies considerably more binding logic than a simple namespace index.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Architectural significance: Together, assignment protocols, optional-binding metadata, and scoped lookup provide the foundations for a source-level binding-provenance model. They can identify relationships among declarations, targets, right-hand-side expressions, and possible values while retaining uncertainty instead of manufacturing precise dependencies.

Primary sources:

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/protocols.py`

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/nodes/_base_nodes.py`

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/nodes/node_classes.py`

## 2. Module exports and public API discovery

Astroid has dedicated facilities for identifying names exposed by modules. These are distinct from ordinary symbol lookup and deserve specific treatment because a module's declared names are not necessarily its public interface.

### 2.1 Public names versus wildcard exports

Two `Module` methods provide different views of externally visible names:

`public_names()` returns locally registered names that do not begin with an underscore.

`wildcard_import_names()` determines names that should be exposed by a wildcard import, incorporating a statically resolvable `__all__` definition.

Consider:

```
__all__ = ["Client"]class Client:    passclass Helper:    passclass _Internal:    pass
```

The distinction is:

- `public_names()` identifies `Client` and `Helper` as non-underscore-prefixed names.
- `wildcard_import_names()` can recognize the explicit `__all__` list and return `Client`.

Thus `public_names()` represents a naming convention, whereas `wildcard_import_names()` attempts to model Python's explicit wildcard-export contract.

This is especially useful for package modules that expose selected declarations from deeper implementation modules.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 2.2 How `__all__` is interpreted

The pinned implementation does more than read literal strings directly from an assignment.

It obtains the relevant `__all__` assignment, attempts to infer the assigned expression, and examines the resulting list or tuple. Individual elements may also be inferred to identify constant strings.

This supports some export definitions that are not simply a directly embedded list of string literals.

However, its behavior is deliberately limited.

If `__all__` cannot be resolved to an appropriate list or tuple, Astroid can fall back to non-underscore-prefixed names. If an individual element cannot be inferred to a string, that element may be omitted from the result.

Consequently, an empty or incomplete result should not automatically be interpreted as an authoritative statement that the module exposes no other names.

Dynamic `__all__` modification, module-level `__getattr__`, runtime registration, and more elaborate export construction may require supplementary modeling.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 2.3 Interface declarations versus public accessibility

A useful API representation can distinguish four kinds of relationships:

| Relationship              | Example                                      |
| ------------------------- | -------------------------------------------- |
| Local declaration         | A class is defined in a module               |
| Imported binding          | A module imports a class from another module |
| Publicly named binding    | A name lacks a leading underscore            |
| Explicit exported binding | A name is included in `__all__`              |

A re-export illustrates why these relationships should not be collapsed.

```
from implementation.client import Client__all__ = ["Client"]
```

The public interface of this module includes `Client`, but the class's implementation originates elsewhere.

Astroid can help recover both the exported binding and the imported target, subject to successful resolution.

This enables a distinction between an interface changing and the implementation reached through that interface changing. Astroid does not automatically determine compatibility between the two.

Primary source:

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/nodes/scoped_nodes/scoped_nodes.py`

## 3. Structural control-flow relationships

Astroid's branch-aware value inference is only one part of its control-flow-related functionality. It also exposes structural relationships that can be inspected independently of determining expression values.

### 3.1 Mutually exclusive statements

The function:

```
astroid.are_exclusive(    stmt1,    stmt2,    exceptions=None,)
```

determines whether two statements belong to mutually exclusive branches under its supported structural rules.

It works by examining their ancestor relationships, locating a common parent, and checking relevant branches of constructs such as `If` and `Try`.

For example:

```
if condition:    left = build_a()else:    right = build_b()
```

The assignments occupy alternative branches. Their exclusivity can be recognized structurally without inferring the value of `condition` or the results of either factory call.

The optional `exceptions` argument changes how exception-handler exclusivity is considered. The documented behavior discards ordinary `If`-branch handling when examining the specified exception-handler relationship.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylint.pycqa.org\&sz=32)

Astroid 4.3.1 documentation



### 3.2 Exclusivity is not complete path analysis

Three concepts must remain distinct:

| Concept                | What it establishes                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------ |
| Structural exclusivity | Two statements occupy branches treated as mutually exclusive by Astroid              |
| Value constraints      | Some inferred possibilities can be eliminated using conditions                       |
| Path feasibility       | Whether a complete sequence of program states and control-flow transitions can occur |

Astroid supports the first two selectively, but does not expose a comprehensive symbolic-execution or path-feasibility engine.

In particular, `are_exclusive()` should not be interpreted as an interprocedural analysis of all possible execution paths, nor as proof that two statements cannot execute during different iterations or different invocations.

Its value is narrower and more immediately useful: it provides existing Python-aware structural logic for distinguishing certain alternative definitions, assignments, and statements.

### 3.3 Block-oriented navigation

Astroid also exposes several utilities that make block-local analysis simpler:

- `statement()` identifies the enclosing statement corresponding to an expression.
- `block_range(lineno)` identifies a line range associated with a node's block.
- `next_sibling()` and `previous_sibling()` navigate neighboring statements.
- `child_sequence()` locates the sequence containing a child.
- `locate_child()` identifies where a child occurs within its parent.

These facilities can help determine whether statements share a block, recover local statement order, and associate a nested expression with its containing operation.

They do not establish program execution order in the presence of branching, loops, exceptions, or asynchronous scheduling.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



Primary sources:

`https://pylint.pycqa.org/projects/astroid/en/stable/api/general.html`

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/nodes/node_ng.py`

## 4. Function signatures, call binding, and return semantics

Astroid provides several layers of function analysis beyond identifying a `FunctionDef` and inspecting its declared signature. Its callable model distinguishes the syntax of a function definition, parameter bindings, a particular invocation, and the possible results of that invocation.

### 4.1 The `Arguments` model

The `Arguments` node preserves Python's parameter categories rather than reducing them to a flat sequence of names.

Its structural fields include:

| Field                                 | Meaning                                          |
| ------------------------------------- | ------------------------------------------------ |
| `posonlyargs`                         | Positional-only parameters                       |
| `args`                                | Ordinary positional-or-keyword parameters        |
| `vararg`                              | Name receiving excess positional arguments       |
| `kwonlyargs`                          | Keyword-only parameters                          |
| `kwarg`                               | Name receiving excess keyword arguments          |
| `defaults`                            | Defaults associated with positional parameters   |
| `kw_defaults`                         | Defaults associated with keyword-only parameters |
| `annotations`                         | Annotations for ordinary parameters              |
| `posonlyargs_annotations`             | Positional-only parameter annotations            |
| `kwonlyargs_annotations`              | Keyword-only parameter annotations               |
| `varargannotation`, `kwargannotation` | Annotations for variadic parameters              |

This representation preserves distinctions that have direct consequences for valid calls and API compatibility.

For example:

```
def process(source, /, options=None, *, strict=True):    ...
```

Changing `source` to accept keyword arguments modifies the callable contract even if its name, annotation, and default remain unchanged. Similarly, moving `strict` out of the keyword-only group changes how callers may invoke the function.

Astroid supplies several convenience methods for analyzing this structure.

`Arguments.find_argname()` returns an argument's index and corresponding `AssignName` node. `Arguments.default_value()` locates its default expression, raising `NoDefault` when one does not exist. `Arguments.get_annotations()` iterates the explicit annotation nodes.

`FunctionDef.argnames()` provides a simpler consolidated view of parameter names.

These methods reduce the need to reconstruct Python's positional/default alignment rules, particularly the requirement that positional defaults correspond to the final positional parameters.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+3



### 4.2 Call-site contexts and argument interpretation

Astroid's `CallContext` stores:

- `args`: positional argument expressions.
- `keywords`: supplied keyword names and their expressions.
- `callee`: the callable being invoked, when known.

The broader `InferenceContext` carries this information alongside the bound receiver, inference constraints, and contextual state.

This allows parameter inference to depend on an invocation rather than treating parameters as permanently unknown symbols.

For example:

```
def multiply(value, factor=2):    return value * factormultiply(5, factor=3)
```

Astroid can use the call's supplied arguments to infer the result of this particular invocation.

Its parameter-assignment machinery also handles selected combinations of positional, keyword, default, and variadic argument binding. These capabilities are provided through the `Arguments` assignment protocol and the inference context.

The engine does not guarantee complete validation or evaluation of arbitrary calls. Starred arguments, dynamic keyword dictionaries, decorators, and unresolved callable objects may prevent a conclusive interpretation.

A useful architectural distinction is therefore between a function's declared signature, a call's supplied argument structure, and the inferred binding of arguments to parameters.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



Source:

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/context.py`

### 4.3 Callable identity versus call-result inference

`infer_call_result(caller, context)` is implemented on several callable representations, including functions, classes, and bound-method proxies.

It addresses a different question from `infer()` on a reference to a function.

| Operation                     | Result sought                                               |
| ----------------------------- | ----------------------------------------------------------- |
| Infer a function reference    | The function or callable represented by the expression      |
| Infer an attribute access     | The member or bound callable reached through that attribute |
| Infer a call expression       | The possible results of invoking the resolved callable      |
| Inspect `infer_call_result()` | The callable-specific machinery for deriving those results  |

For ordinary functions, Astroid examines return statements while avoiding returns inside nested function scopes.

For classes, inference can account for class instantiation and certain metaclass `__call__` behaviors.

For methods, the binding context can affect how parameters and inherited behavior are interpreted.

One relevant 4.3.4 distinction concerns function bodies containing only `pass` or `...`. Such placeholder bodies can infer as `Uninferable` instead of being treated as definitively returning `None`.

This is deliberate conservative behavior for incomplete or stub-like definitions. It is not a claim that an actual Python function containing only `pass` returns an unknown value at runtime.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



### 4.4 Generator calls versus yielded values

Astroid distinguishes a generator object from the values that can be produced by iterating it.

`FunctionDef.is_generator()` identifies generator-producing definitions while excluding yields belonging to nested functions or lambdas.

`FunctionDef.infer_call_result()` produces a symbolic `Generator` or `AsyncGenerator` when the corresponding function is recognized as a generator.

Separately, `FunctionDef.infer_yield_result(context)` examines `Yield` expressions belonging to that function and attempts to infer their values.

For example:

```
def numbers():    yield 1    yield 2
```

The function call represents a generator object. The yielded values are separate pieces of semantic information.

This distinction matters when characterizing an API. A generator function's callable result and the type or possible values of its iteration elements are different aspects of its contract.

There are important limitations. The current `infer_yield_result()` implementation explicitly traverses `Yield` nodes; it is not a general simulation of generator delegation, `send()`, iteration order, or asynchronous scheduling. Recognition of `AsyncFunctionDef` and `AsyncGenerator` also does not establish complete inference for ordinary coroutine lifecycles.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



Source:

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/nodes/scoped_nodes/scoped_nodes.py`

## 5. Class member origins and function classification

Astroid supports more precise examination of where class functionality originates than a simple merged list of available members.

### 5.1 Distinguishing member accessibility from declaration ownership

The following class-inspection methods are especially relevant:

| Method                          | Behavior                                                                   |
| ------------------------------- | -------------------------------------------------------------------------- |
| `local_attr(name)`              | Finds assignment nodes for a class attribute in the class or its ancestors |
| `instance_attr(name)`           | Finds instance-attribute assignments in the class and ancestors            |
| `local_attr_ancestors(name)`    | Identifies ancestors supplying a class-level name                          |
| `instance_attr_ancestors(name)` | Identifies ancestors supplying an instance attribute                       |

Consider:

```
class Base:    def calculate(self):        return 10class Derived(Base):    pass
```

The method is accessible through `Derived`, but its declaration originates in `Base`.

Astroid can expose the origin relationship instead of requiring a consumer to reconstruct the hierarchy manually.

The implementation also has a consequential distinction between class and instance attributes.

`local_attr()` checks the local class and then uses the first relevant ancestor found through `local_attr_ancestors()`, which prefers the calculated MRO when possible.

`instance_attr()` collects local instance-attribute definitions and contributions from ancestors. Its ancestor helper traverses inferred ancestors rather than simply returning one effective definition.

Thus a collection of instance-attribute assignment nodes is not necessarily equivalent to Python's final runtime descriptor-resolution result.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+3



### 5.2 Symbolic instantiation

`ClassDef.instantiate_class()` creates a symbolic Astroid instance associated with the class.

The implementation may use an `ExceptionInstance` representation for classes inferred to inherit from Python's exception base classes.

This offers a direct bridge between a `ClassDef` representing a class and an `Instance` representing a potential object of that class.

The instance is not a runtime object created by executing the class constructor.

Consequently, this mechanism can provide instance-side attribute inspection without requiring constructor side effects or application initialization.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 5.3 Function and method classification

`FunctionDef` exposes additional classification helpers:

| API                | Purpose                                                            |
| ------------------ | ------------------------------------------------------------------ |
| `is_method()`      | Checks whether the function is modeled as a method in a class      |
| `is_bound()`       | Checks relevant method or classmethod binding semantics            |
| `is_generator()`   | Identifies generator functions                                     |
| `is_abstract()`    | Identifies functions matching selected abstract-method conventions |
| `decoratornames()` | Attempts to infer qualified decorator names                        |
| `argnames()`       | Retrieves parameter names                                          |

Of these, `decoratornames()` is particularly valuable.

A decorator can be referenced through an import alias rather than through its defining name. Astroid attempts to infer each decorator expression and obtain the qualified name of the resulting object.

The implementation also incorporates `extra_decorators`, which can recognize certain assignment-based decorations, such as:

```
class Example:    def create(value):        return value    create = staticmethod(create)
```

The method has no `@staticmethod` syntax, but its effective behavior is altered through assignment. Astroid has specific machinery to recognize selected forms of this pattern.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 5.4 Abstractness is a heuristic

`FunctionDef.is_abstract()` is useful but must be interpreted carefully.

Its parameters include:

```
is_abstract(    pass_is_abstract=True,    any_raise_is_abstract=False,)
```

The implementation considers selected ABC decorators, `NotImplementedError`, and the function body's structure.

With the default parameters, a method whose body consists of `pass` can be classified as abstract.

This is a static-analysis heuristic, not the same as Python's runtime `ABCMeta` enforcement. A concrete method containing `pass` does not automatically become an abstract method at runtime.

The method can therefore support a broader notion of implementation placeholder than ordinary runtime abstractness. Consumers requiring the precise runtime contract must preserve that distinction.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



## 6. Operation-specific inference and diagnostic evidence

Astroid's expression inference includes specialized handling for selected Python operations and protocols. Beyond attempting to calculate results, it can expose evidence about operations that are incompatible with the inferred operands.

### 6.1 Operator-specific type errors

The relevant node classes include:

- `BinOp`
- `UnaryOp`
- `AugAssign`

Each exposes `type_errors(context=None)`.

These methods return collections of objects such as `BadBinaryOperationMessage` and `BadUnaryOperationMessage`.

For example, an expression like:

```
1 + "value"
```

contains an operation whose operands are incompatible under ordinary Python addition semantics.

Astroid's operation inference can identify such cases and represent the failure as a structured diagnostic message rather than merely leaving the expression unresolved.

The message objects preserve information such as the operation and operands or their inferred types. Unary-operation messages can also retain the underlying error.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 6.2 Why an empty error list is not proof of correctness

A particularly important implementation detail is that `type_errors()` returns an empty list when the underlying inference encounters an unknown result or an `InferenceError`.

Therefore:

```
errors = expression.type_errors()
```

An empty `errors` collection does not necessarily mean the operation is valid for all possible inputs.

It can mean the engine did not obtain sufficiently definite values to report the problem.

This is a useful example of a wider principle: Astroid provides diagnostic evidence under successful partial inference, not comprehensive static type safety.

### 6.3 Python protocol semantics

Astroid also models selected Python protocols through methods and object-specific inference behavior.

These include:

- `bool_value()` for truth-value inference, including selected `__bool__` and `__len__` behavior.
- `getitem()` for indexing and subscription operations.
- `itered()` and iterator-related inference for selected iterable objects.
- `infer_binary_op()` and related operation helpers.
- `callable()` and `infer_call_result()` for callable objects.

These operations can be combined.

For example, inferring an element obtained from a container may require first resolving the container, then applying indexing or iteration semantics, and finally inferring the selected element.

Such reasoning is stronger than a purely syntactic model of `Subscript`, `For`, or `BinOp`.

But it remains selective. User-defined special methods, dynamic dispatch, complex mutation, and interactions with external objects may yield `Uninferable` rather than a complete interpretation.

Sources:

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/nodes/node_classes.py`

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/util.py`

## 7. Docstrings, type comments, and source-level API metadata

Astroid preserves several kinds of declared interface information that are not equivalent to inferred runtime behavior.

These capabilities are particularly valuable for documentation extraction, declaration comparison, and analyses that need to distinguish implementation details from explicitly stated contracts.

### 7.1 Docstrings as dedicated AST nodes

`Module`, `ClassDef`, and `FunctionDef` expose `doc_node`.

When present, this is an Astroid `Const` containing the docstring.

For example:

```
def calculate(value: float) -> float:    """Return the normalized value."""    return value / 100
```

Astroid can represent the docstring separately from the function's body statements, parameter definitions, and return annotation.

This makes it possible to associate documentation with the declaration that owns it, without parsing the docstring from reconstructed source text.

The docstring's content is still an arbitrary string. Astroid does not inherently convert NumPy-style, Google-style, or Sphinx-style docstrings into a validated structured contract.

An additional traversal detail is worth noting: metadata-bearing fields and ordinary `get_children()` traversal do not always expose identical content. Consumers should inspect `doc_node` and other declaration metadata explicitly when those fields matter.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 7.2 Legacy type comments

Astroid retains type information expressed through Python type comments.

Relevant fields include:

| Representation             | Field                                                                      |
| -------------------------- | -------------------------------------------------------------------------- |
| Function definitions       | `type_comment_args`, `type_comment_returns`                                |
| Function arguments         | `type_comment_args`, `type_comment_posonlyargs`, `type_comment_kwonlyargs` |
| Assignments                | `type_annotation`                                                          |
| Loop statements            | `type_annotation`                                                          |
| Context-manager statements | `type_annotation`                                                          |

This allows analysis of older Python codebases that use annotations such as:

```
def combine(a, b):    # type: (int, int) -> int    return a + b
```

Astroid's `Arguments.get_annotations()` iterates conventional annotation nodes. It should not be assumed to automatically combine every type-comment representation into a unified signature.

To construct a complete source-declared annotation view, a consumer may need to inspect ordinary annotations and the relevant type-comment fields separately.

Likewise, annotations remain declarations rather than guarantees of runtime values.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+3



### 7.3 Module source provenance

`Module` carries additional source and construction information.

| Attribute or method | Significance                                               |
| ------------------- | ---------------------------------------------------------- |
| `file`              | Path associated with the module, when available            |
| `file_bytes`        | Original source text or bytes retained during construction |
| `file_encoding`     | Source-file encoding                                       |
| `path`              | Package search paths or module path information            |
| `package`           | Whether the representation corresponds to a package        |
| `pure_python`       | Whether the AST was built from source                      |
| `future_imports`    | Recorded `__future__` imports                              |
| `stream()`          | Access to underlying source bytes or file                  |
| `fully_defined()`   | Whether the module was built from a `.py` file             |

These attributes help distinguish a source-derived representation from a partial introspected module or synthetic representation.

There are two important nuances.

First, `fully_defined()` checks whether the module's file ends in `.py`. It does not guarantee that arbitrary dynamically generated behavior has been discovered.

Second, `stream()` can return a newly opened file object. Consumers using it should handle the returned stream's lifecycle appropriately.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



Primary source:

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/nodes/scoped_nodes/scoped_nodes.py`

## 8. Structural pattern matching and nontraditional bindings

Python's `match` statement introduces a different family of binding semantics from ordinary assignments.

Astroid represents structural patterns through dedicated nodes, including `MatchAs`, `MatchStar`, `MatchMapping`, `MatchSequence`, `MatchClass`, and `MatchOr`.

Several of these nodes also participate in the assignment-protocol system.

Consider:

```
match response:    case {"status": status, "payload": payload}:        process(status, payload)
```

The names `status` and `payload` are introduced through a pattern rather than an `Assign` statement.

Astroid represents the captures and provides assignment-handling functions for relevant pattern nodes, including `match_as_assigned_stmts`, `match_star_assigned_stmts`, and `match_mapping_assigned_stmts`.

This allows assignment-oriented analysis to include names created through pattern matching without requiring every consumer to recognize those bindings independently.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



However, pattern matching involves more than binding creation. A pattern can be conditionally successful, a guard can fail, and earlier cases can exclude later ones.

The existence of a captured name in Astroid's representation does not establish that the corresponding case will execute, nor that its subject can always be narrowed to a particular type.

This is another situation where source-level binding provenance and runtime path feasibility must remain separate.

Source:

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/nodes/node_classes.py`

## 9. Advanced transform lifecycle and inference customization

The original overview describes Astroid's principal extension mechanisms. Several operational details materially affect how extensions compose and how their results should be interpreted.

### 9.1 Transformation order and replacement semantics

`TransformVisitor` walks the AST recursively and transforms child nodes before transforming their parent.

Within a node class, applicable transforms are evaluated in registration order.

A transformation can modify a node or return a replacement. If it returns a replacement of another node class, the visitor stops applying the remaining transforms registered for the original class.

This matters because extensions may depend on the results of earlier transformations. A parent-level transformation can observe an already transformed child, but later transforms are not guaranteed to run after a node's type changes.

The 4.3.4 implementation also warrants care with transforms that mutate nodes in place and return `None`: its subsequent class comparison operates on the returned object, so such a result can terminate the current transform chain.

This is behavior observed in the pinned source, not a separate documented composition guarantee.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 9.2 Explicitly applying and removing transforms

`AstroidManager` exposes:

- `register_transform()`
- `unregister_transform()`
- `visit_transforms()`

`visit_transforms()` can apply currently registered transformations to an existing tree.

This provides a way to distinguish initial AST construction from later semantic enrichment.

At the parsing layer, the top-level `astroid.parse()` function also accepts:

```
astroid.parse(    source,    module_name="example",    apply_transforms=False,)
```

Disabling transforms suppresses registered transformations during construction; it does not turn Astroid into Python's built-in `ast` representation.

The resulting tree remains an Astroid AST with its own node classes and construction semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 9.3 Falling back to default inference

A custom inference implementation can raise `UseInferenceDefault` when it cannot handle a particular node.

`NodeNG.infer()` catches this exception and proceeds to the normal inference path.

This creates a useful distinction between:

- A custom inference rule that can conclusively model the expression.
- A custom rule that explicitly produces an unknown result.
- A custom rule that delegates to the default inference engine.

The third case is particularly valuable for extensions that support recognizable patterns but should not replace Astroid's established behavior for unrelated expressions.

The explicit inference path is part of the node's core inference mechanism, not merely a feature of one built-in brain module.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 9.4 Cache invalidation and transform registration

`AstroidManager.clear_cache()` performs more than deleting the module cache.

It clears inference-tip caches and the global inference cache, resets module and path-related caches, bootstraps built-in representations, and re-registers Astroid's built-in brain transformations.

The pinned implementation resets the transform registry as part of this operation.

Consequently, independently registered custom transformations should not be assumed to survive a cache reset automatically. An extension host that deliberately clears manager state needs to account for external registrations.

Similarly, the transform visitor invalidates inference caching when a transformation returns a non-`None` replacement. Arbitrary mutation of an existing node should not be assumed to trigger the same invalidation behavior.

These details matter in long-lived analysis processes where source trees, inference results, and semantic extensions evolve over time.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 9.5 Shared manager state and concurrency

`AstroidManager` uses shared state across manager instances, including module caches, registered transforms, and configuration.

Additionally, the `AstroidBuilder` module explicitly states that its builder is not thread-safe and cannot be used to parse different sources simultaneously through the same builder instance.

This does not establish that every possible parallel Astroid operation is unsafe, but it precludes treating its construction facilities as universally thread-safe.

Independent analysis processes provide a clearer isolation boundary than assuming separately constructed managers possess independent configuration and cache state.

The appropriate concurrency design depends on the exact APIs being invoked and the desired isolation guarantees.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



Primary sources:

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/transforms.py`

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/manager.py`

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/builder.py`

## 10. Additional structural and module-analysis utilities

Several smaller capabilities merit inclusion because they can eliminate custom tree-navigation or import-discovery logic.

### 10.1 AST field navigation and structural metadata

`NodeNG` exposes `_astroid_fields`, identifying attributes containing child nodes.

For generalized analyzers, this complements `get_children()` and enables field-aware traversal.

Two useful methods are:

`locate_child(child)` — returns the field containing a child, together with the corresponding node or sequence.

`child_sequence(child)` — returns the sequence containing the child.

This is useful when the role of an expression matters, not just its presence.

For instance, a node appearing within an `If.test` field has a different structural role from one appearing within `If.body`.

Other relevant methods include `op_precedence()` and `op_left_associative()`, which expose precedence and associativity rules for expression representations.

`repr_tree(ast_state=True)` can also display derived AST information, including scope-related state, rather than only basic syntax fields.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



### 10.2 Structural equality is not supplied as a general semantic contract

`NodeNG.eq()` should not be mistaken for a universal structural or semantic equivalence operation.

The base implementation returns `False`.

Accordingly, two Astroid nodes having similar source syntax, qualified names, or inferred values does not imply the library has established their semantic equivalence.

A separate comparison mechanism would be required to distinguish changes in formatting, declarations, effective interfaces, or behavior.

Astroid provides information from which such comparisons might be constructed, but no complete equivalence guarantee follows from the presence of AST objects or inference results.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 10.3 `modutils` as reusable import infrastructure

`astroid.modutils` contains lower-level helpers for Python module discovery and path resolution.

Important functions include:

| API                        | Capability                                                        |
| -------------------------- | ----------------------------------------------------------------- |
| `modpath_from_file()`      | Derives a module name from a filesystem path                      |
| `file_from_modpath()`      | Resolves a split module path to its corresponding file            |
| `file_info_from_modpath()` | Returns richer import/module-spec information                     |
| `get_source_file()`        | Finds a matching source file, with stub preference support        |
| `is_python_source()`       | Recognizes supported Python source extensions                     |
| `is_stdlib_module()`       | Checks whether a module name belongs to Python's standard library |
| `module_in_path()`         | Checks module location against supplied paths                     |
| `load_module_from_name()`  | Loads a Python module by import name                              |

This functionality can be useful independently of full AST construction.

For example, `modpath_from_file()` and `file_from_modpath()` help translate between filesystem identities and Python import identities, including consideration of package layout and import search paths.

A notable semantic boundary is that `load_module_from_name()` uses `importlib.import_module()`. It is a runtime module loader, not a purely static dependency resolver.

Astroid captures standard output and standard error during this loading operation, but the import can still execute Python initialization code and produce side effects.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+3



Source:

`https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/modutils.py`

### 10.4 Additional manager construction paths

`AstroidManager.ast_from_string()` is a useful direct construction entry point alongside file- and module-based construction.

The manager also handles source-file preference, namespace-package representations, extension-module loading permissions, and module caching.

A notable distinction is that `AstroidBuilder.module_build()` first attempts to recover source through the module's loader, then through a corresponding source file, and finally may construct a partial representation through live-object introspection.

Thus a module supplied as a live Python object does not necessarily produce an introspection-only tree. Source-derived information may still be preferred when available.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



## 11. Consequential interactions across these capabilities

The additional capabilities become particularly valuable when understood as combinations rather than isolated methods.

### 11.1 Declaration provenance and effective member resolution

An inherited method can involve several separate pieces of information:

1. The declaration's source location and containing class.
2. The subclass through which it is accessible.
3. The member-resolution path through the inheritance hierarchy.
4. Decorators or descriptors affecting invocation behavior.
5. The argument bindings and possible result of a particular call.

Astroid provides partial native support for each layer.

This can enable a richer understanding of a callable than a flattened class-method inventory. In particular, the method's declaration, accessible identity, and invocation behavior need not be identical.

### 11.2 Source contracts and inferred behavior

A function or class may expose several overlapping descriptions of its interface:

| Information                         | Evidence source                                |
| ----------------------------------- | ---------------------------------------------- |
| Parameter categories and defaults   | `Arguments`                                    |
| Declared parameter and return types | Annotations and type comments                  |
| Human-authored documentation        | `doc_node`                                     |
| Decorator identities                | `decoratornames()` and decorator inference     |
| Generated members                   | Built-in or custom brain models                |
| Possible return values              | `infer_call_result()`                          |
| Generator element possibilities     | `infer_yield_result()`                         |
| Public module exposure              | `public_names()` and `wildcard_import_names()` |

These fields can support different forms of comparison.

For example, the source signature could remain unchanged while an inherited implementation changes. Conversely, a parameter annotation might change without any observable change in the function's statically inferred return value.

Neither observation alone establishes complete behavioral equivalence.

The important capability is that Astroid exposes much of the underlying information separately, allowing a consumer to preserve distinctions rather than reduce everything to source-text comparison.

### 11.3 More precise semantic dependencies

The combination of scope-aware lookup, assignment provenance, class-member origins, import resolution, and call-specific inference can help construct dependencies more precise than textual references alone.

For example, a function call might be traced through:

Source-level reference

Scope and assignment resolution

Import, alias, or inherited-member resolution

Callable and argument interpretation

Possible semantic targets and results

This is an architectural composition of Astroid's capabilities, not a claim that it automatically exports a complete dependency graph in this form.

A downstream analysis can distinguish dependencies established by explicit syntax from those established by inference or synthetic semantic rules.

Such distinctions are especially important for change-impact analysis: a dependency on a declaration, a dependency on its effective public interface, and a dependency on inferred implementation behavior may have different invalidation conditions.

Astroid supplies useful semantic evidence for those decisions. Persistent dependency indexing, equivalence rules, and invalidation remain separate responsibilities.

## 12. Additional primary-source reference map

These are the most relevant sources for the functionality expanded in this addendum. URLs point to the 4.3.4 release where possible.

| Capability                                       | Primary source                                                                                 |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| Assignment protocols                             | `https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/protocols.py`                       |
| Assignment node hierarchy                        | `https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/nodes/_base_nodes.py`               |
| Function signatures, operators, pattern matching | `https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/nodes/node_classes.py`              |
| Function, class, and module capabilities         | `https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/nodes/scoped_nodes/scoped_nodes.py` |
| Inference and call contexts                      | `https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/context.py`                         |
| Node navigation and inference fallbacks          | `https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/nodes/node_ng.py`                   |
| Transform mechanics                              | `https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/transforms.py`                      |
| Manager, caches, and transform registration      | `https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/manager.py`                         |
| Builder and construction semantics               | `https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/builder.py`                         |
| Import and module-resolution utilities           | `https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/modutils.py`                        |
| Operation diagnostic representations             | `https://github.com/pylint-dev/astroid/blob/v4.3.4/astroid/util.py`                            |

## 13. Addendum conclusion

The functionality documented here broadens the architectural picture of Astroid in three important ways.

First, Astroid provides native structural and provenance-oriented analysis, not just value inference. Its assignment protocols, scope-relative lookups, branch-exclusivity checks, member-origin helpers, and export-discovery APIs enable relationships to be established without reconstructing significant portions of Python's semantics.

Second, Astroid represents multiple layers of callable and API information. Source signatures, type comments, docstrings, decorators, argument bindings, inherited members, inferred return values, and generated API elements can be inspected separately. These distinctions enable more precise semantic models than either raw syntax trees or inferred values alone.

Third, its extension and inference infrastructure has important composition and lifecycle semantics. Transformation order, explicit inference fallback, shared manager state, cache resets, and builder concurrency constraints affect the correctness and maintainability of systems that use Astroid as a long-lived semantic-analysis component.

Combined with the original overview, this addendum provides a substantially more complete picture of Astroid's capabilities as a Python source-analysis substrate, while preserving its central limitation: Astroid produces valuable but potentially incomplete semantic knowledge, rather than an exhaustive model of Python execution.