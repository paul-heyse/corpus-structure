# Griffe (Python): Comprehensive Library Capability Overview

Research date: November 12, 2026 | Current stable release: 2.4.1 (October 22, 2026) | Python ≥3.11 | ISC license

Griffe is a Python API analysis and representation framework that extracts the structural and semantic interface of Python packages without ordinarily executing their code. It converts Python source files, type stubs, and runtime objects into a navigable, serializable object model containing functions, classes, methods, attributes, type aliases, imports, signatures, annotations, docstrings, inheritance relationships, and source locations.

Its primary uses are API documentation generation, programmatic interface inspection, and compatibility analysis. Its more general architectural significance is that it provides a reusable semantic interface layer between raw Python source code and downstream systems that need to understand, compare, document, or process Python APIs.

Griffe can operate statically, dynamically, or in a mixed mode. It also supports custom analysis extensions, structured docstring parsing, import and inheritance resolution, JSON serialization, and detection of breaking changes between package versions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+2



Official resources:

- Documentation: [https://mkdocstrings.github.io/griffe/](https://mkdocstrings.github.io/griffe/?utm_source=chatgpt.com)
- Source repository: [https://github.com/mkdocstrings/griffe](https://github.com/mkdocstrings/griffe?utm_source=chatgpt.com)
- PyPI: [https://pypi.org/project/griffe/](https://pypi.org/project/griffe/?utm_source=chatgpt.com)
- Release history: [https://mkdocstrings.github.io/griffe/changelog/](https://mkdocstrings.github.io/griffe/changelog/?utm_source=chatgpt.com)

## 1. Capability map

| Capability                         | What Griffe provides                                                                                          |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Static API extraction              | AST-based discovery of module structures, declarations, signatures, annotations, and other interface metadata |
| Runtime introspection              | Inspection of compiled, built-in, or highly dynamic Python objects                                            |
| Unified semantic object model      | Modules, classes, functions, attributes, type aliases, and aliases with common navigation facilities          |
| Import and alias resolution        | Links re-exports and imported names to their underlying declarations                                          |
| Inheritance analysis               | Class bases, inherited members, and resolution of inherited object references                                 |
| Type and expression representation | Structured expressions for annotations, defaults, decorators, bases, and attribute values                     |
| Structured documentation           | Google, NumPy, and Sphinx docstring parsing into typed sections and elements                                  |
| API compatibility analysis         | Detection and explanation of selected potentially breaking interface changes                                  |
| Extensible analysis                | Hooks into AST visitation, runtime inspection, and completed object loading                                   |
| Serialization                      | JSON representations, configurable full dumps, and a published schema                                         |
| Source provenance                  | File locations, line ranges, source retrieval, and optional Git metadata                                      |
| Developer tooling                  | CLI commands, version comparisons, CI annotations, and integrations with documentation tooling                |

The important architectural distinction is that Griffe does not attempt to be a complete Python program analyzer. Its representation is deliberately optimized around externally observable API structure, rather than general control-flow analysis, data-flow analysis, inference of arbitrary runtime behavior, or execution semantics.

Consequently, it occupies a useful middle ground between relatively low-level Python syntax-tree libraries and heavyweight program-analysis systems.

## 2. Architecture and execution model

### 2.1 The extraction pipeline

Griffe separates Python API analysis into a sequence of operations:

Python package inputs

Source files · Type stubs · Compiled modules · Runtime objects

Static analysis

AST parsing + Visitor

Dynamic analysis

Runtime inspection + Inspector

Unified Griffe object tree

Members · Aliases · Expressions · Signatures · Metadata

Resolution and enrichment

Imports · Inheritance · Stubs · Extensions · Docstrings

API documentation

Compatibility checks

Structured API data

This is a conceptual pipeline, not a claim that every input passes through every stage. Some operations are optional or interleaved.

The key design is the separation between how information is acquired and how downstream code consumes the result. The same `Module`, `Class`, or `Function` interfaces can represent information derived from syntax or runtime introspection.

Griffe implements the two collection strategies through `Visitor` and `Inspector`, orchestrated by `GriffeLoader`. Extensions can participate in both processes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



Source: [https://mkdocstrings.github.io/griffe/guide/contributors/architecture/](https://mkdocstrings.github.io/griffe/guide/contributors/architecture/?utm_source=chatgpt.com)

### 2.2 Static analysis as the default

Griffe primarily uses Python's standard-library `ast` machinery to parse source code.

Its static visitor collects declarations and associated metadata without importing the target modules. This is especially useful when a package has expensive imports, native dependencies, initialization side effects, or a runtime environment that differs from the analysis environment.

Important characteristics include:

- Source-level annotations and default expressions can be retained without evaluating them.
- Definitions can be extracted even when unrelated runtime dependencies are missing.
- Docstrings, decorators, inheritance expressions, and declaration locations remain accessible.
- Imports and re-exports can be analyzed through the package's static structure.
- Analysis can be performed on source directories and standalone Python files, including packages not installed in the current interpreter.

There is a consequential boundary: static analysis describes what can be determined from source, not necessarily the fully evaluated runtime interface.

A metaclass, decorator, module-level `__getattr__`, or framework registration mechanism can synthesize or replace objects in ways not directly evident from the AST. Griffe supports many standard constructs, but does not attempt general inference of arbitrary Python code. Custom framework behavior may require extensions or targeted inspection.

### 2.3 Dynamic inspection and hybrid analysis

Dynamic inspection uses Python imports and introspection to examine runtime objects.

Griffe falls back to inspection when it cannot find source code, including for built-in and compiled modules encountered during package loading. It also permits explicitly forcing this strategy.

```
import griffe# Prefer source analysis, with runtime fallback.package = griffe.load("example_package")# Use runtime inspection.runtime_package = griffe.load(    "example_package",    force_inspection=True,)# Disallow runtime inspection entirely.static_package = griffe.load(    "example_package",    allow_inspection=False,)
```

The default hybrid behavior has several advantages:

- Pure Python declarations can retain detailed source metadata.
- Native extension modules can contribute introspected interface information.
- Different portions of the same package can be analyzed using different mechanisms.
- Custom extensions can selectively inspect only objects whose static representation is insufficient.

Runtime inspection has corresponding costs. Imports execute Python code, can trigger side effects, require dependencies, and potentially expose the process to untrusted code. Introspection may also yield less accurate source-level information, particularly for transformed functions and dynamically generated objects.

Griffe's documentation explicitly discourages forcing runtime inspection across entire packages unless necessary.

Version 2.4.1 detail: Dynamic discovery supports lazy module attributes exposed through `__dir__` and `__getattr__`. The inspector relies on `inspect.getmembers`, so `__getattr__` alone does not make a lazy symbol discoverable; it must also be advertised through `dir()`.

Source: [https://mkdocstrings.github.io/griffe/guide/users/loading/](https://mkdocstrings.github.io/griffe/guide/users/loading/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



### 2.4 Package discovery, load scope, and reuse

Griffe supports Python import paths, dotted object paths, filesystem paths, and explicit search directories.

The principal interfaces are `griffe.load()` and `griffe.GriffeLoader`.

```
import griffeloader = griffe.GriffeLoader(search_paths=["src"])package = loader.load("example_package")another = loader.load("another_package")# After loading the relevant packages:loader.resolve_aliases()method = package["submodule.MyClass.method"]
```

A request for a particular nested object still loads its containing package. This is intentional: import resolution, inherited members, and symbol relationships depend on surrounding definitions.

Reusing a loader is meaningful because it maintains shared state:

- A module collection containing previously loaded objects.
- A finder that caches filesystem directory listings.
- Shared resolution context across packages.
- Configured extension behavior.

The directory-listing cache does not constitute a general source-content or incremental-analysis cache. Reusing a loader avoids repeated discovery work, but it is not equivalent to a fully incremental compiler or language server.

Additional important controls include `submodules`, `search_paths`, `try_relative_path`, `store_source`, `resolve_aliases`, `resolve_external`, `resolve_implicit`, and options for locating stub packages.

Source: [https://mkdocstrings.github.io/griffe/reference/api/loaders/](https://mkdocstrings.github.io/griffe/reference/api/loaders/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



### 2.5 Type stubs and Python typing information

Griffe can combine information from `.py` source files with associated `.pyi` stub files.

This is valuable for packages where implementation signatures are incomplete, heavily dynamic, or maintained separately from public typing contracts.

Its stub functionality includes:

- Merging corresponding source and stub declarations.
- Preserving typed interface information from stubs.
- Combining signature and overload information with concrete implementations.
- Finding separately installed stub-only distributions when explicitly configured.
- Selecting whether source or stub docstrings take precedence.

By default, source docstrings win when both files document the same object. `prefer_stubs_docs=True` reverses that preference, while retaining source docstrings if no stub docstring is available.

`find_stubs_package=True` enables discovery of separately distributed stub packages. This is distinct from merging adjacent `.py` and `.pyi` files.

Griffe also supports contemporary Python typing syntax, including PEP 695 type parameters and the merging of overload annotations into implementation representations. This is interface extraction, not full type checking or type inference.

Source: [https://mkdocstrings.github.io/griffe/guide/users/loading/](https://mkdocstrings.github.io/griffe/guide/users/loading/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+2



## 3. Unified API object model

Griffe's most reusable capability is its object representation. Rather than exposing raw AST nodes as the primary consumer interface, it creates a set of typed Python models with shared traversal and metadata operations.

### 3.1 Six primary object kinds

| Model       | Representation and distinctive information                                                              |
| ----------- | ------------------------------------------------------------------------------------------------------- |
| `Module`    | Package/module hierarchy, imports, exports, members, module-level overloads, future-annotation settings |
| `Class`     | Bases, resolved bases, MRO, methods, attributes, decorators, constructor parameters, type parameters    |
| `Function`  | Parameters, parameter kinds, defaults, return annotation, decorators, overloads, type parameters        |
| `Attribute` | Annotation, assigned expression, property getter/setter/deleter-related information, labels             |
| `TypeAlias` | Alias value expression and generic type parameters                                                      |
| `Alias`     | Indirection to another Griffe object, preserving the name and location of the reference                 |

The models share concepts such as `name`, `path`, `parent`, `members` where appropriate, `docstring`, visibility flags, labels, and source locations.

Additional representation types include `Parameter`, `Parameters`, `Decorator`, `Docstring`, and structured expression classes. These support the primary object models without requiring a consumer to interpret arbitrary Python syntax.

### 3.2 Hierarchical navigation

A loaded package acts as a tree with direct parent relationships and member dictionaries.

```
import griffepackage = griffe.load("example_package")# Direct member lookup.module = package.members["submodule"]# Navigate using dotted member paths.obj = package["submodule.MyClass.method"]# Access objects by kind.classes = module.classesfunctions = module.functions# Access the enclosing objects.parent = obj.parentroot = obj.package
```

Griffe also exposes `get_member()`, `set_member()`, and `del_member()`.

The distinction between these methods and direct dictionary access matters for extensions. In particular, `set_member()` updates structural relationships appropriately, while writing directly into `members` may leave parent references inconsistent.

Kind-filtered collections such as `classes`, `functions`, and `attributes` are computed properties rather than separately maintained canonical indexes.

For class objects, `members` and `all_members` are distinct. The latter includes inherited members, which require inheritance resolution and can be unavailable or incomplete during initial analysis.

Source: [https://mkdocstrings.github.io/griffe/guide/users/navigating/](https://mkdocstrings.github.io/griffe/guide/users/navigating/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



### 3.3 Object metadata and classification

Griffe associates considerably more information with objects than just their signatures.

Among the useful fields are:

- Classification: `kind`, `is_module`, `is_class`, `is_function`, `is_attribute`, `is_type_alias`, `is_alias`, `labels`, and `has_labels()`.
- Visibility: `is_public`, `is_private`, `is_special`, `is_deprecated`, and explicit `public` and `deprecated` overrides.
- Origin: `analysis`, `filepath`, `lineno`, `endlineno`, source content, and Git-derived source links where available.
- Import status: `imports`, `exports`, `is_imported`, `is_exported`, and `is_wildcard_exposed`.
- Documentation: `docstring`, `has_docstring`, and recursive `has_docstrings`.
- Type structure: annotations, type parameters, and structured expressions.
- Extensibility: namespaced `extra` metadata.

This model makes it possible for consumers to ask questions such as which public methods expose optional parameters, which attributes are deprecated, or which exported classes inherit from a particular base—without repeatedly reconstructing those concepts from raw AST nodes.

These queries are subject to Griffe's resolution completeness and documented semantics; for example, an unloaded external base class will not participate fully in inherited-member analysis.

### 3.4 Signature representation

Function signatures are represented using `Parameters` and `Parameter` objects.

They distinguish the major Python calling conventions:

- Positional-only parameters.
- Positional-or-keyword parameters.
- Variadic positional arguments.
- Keyword-only parameters.
- Variadic keyword arguments.

The representation also retains declared defaults and annotations. Functions and classes offer methods for producing stringified signatures.

Importantly, Griffe preserves source-level expressions rather than assuming that default values can safely be evaluated. A default such as `DEFAULT_CONFIG` is not necessarily reduced to the runtime object referred to by that name.

Multiple declared overloads are also representable, instead of treating an overloaded API as a single signature.

Source: [https://mkdocstrings.github.io/griffe/reference/api/models/function/](https://mkdocstrings.github.io/griffe/reference/api/models/function/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



## 4. Import resolution, inheritance, and public API boundaries

These are among Griffe's most consequential capabilities because a Python package's public interface often differs substantially from where its objects are physically defined.

### 4.1 Aliases represent references, not copied declarations

Consider a package that implements a class in `internal.models`, then re-exports it from its top-level namespace:

```
# example_package/__init__.pyfrom .internal.models import Model__all__ = ["Model"]
```

There are two meaningful locations:

- `example_package.Model`: the name consumers import.
- `example_package.internal.models.Model`: the underlying declaration.

Griffe represents the first as an `Alias` pointing to the second. It preserves both the exposed name and information about the target.

The important attributes are:

| Property                          | Meaning                                                    |
| --------------------------------- | ---------------------------------------------------------- |
| `path`                            | The name at the current location in the Griffe object tree |
| `canonical_path`                  | The underlying declaration path for a resolved alias       |
| `target_path`                     | The path stored by the alias to identify its target        |
| `target`                          | The resolved target object                                 |
| `resolved`                        | Whether the alias has been successfully resolved           |
| `alias_lineno`, `alias_endlineno` | Source location where the alias was introduced             |
| `wildcard`                        | Information about wildcard-import aliases                  |

This allows consumers to distinguish API accessibility from declaration ownership without duplicating the definition.

Griffe 2.4.0 also introduced `reference_path` alongside `canonical_path`; the changelog confirms its availability, although the user guide does not yet fully explain its semantics. Consumers depending on the distinction should consult the versioned API/source rather than assuming that the two properties are interchangeable.

Source: [https://mkdocstrings.github.io/griffe/guide/users/navigating/](https://mkdocstrings.github.io/griffe/guide/users/navigating/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+2



### 4.2 Resolution is a separate operation

An alias initially stores a reference to another object. Successfully following that reference requires the relevant target to have been loaded and identified.

Griffe performs alias resolution after collecting package structures, rather than assuming all imported names can be resolved during the initial AST traversal.

This separation accommodates:

- Re-exports across multiple modules.
- Relative and absolute imports.
- Chains of aliases.
- Wildcard imports.
- Names imported from other packages.
- Inherited members represented as aliases.

For example, an alias can form a chain such as `public.API` → `implementation.API` → `core.API`. Resolution attempts to follow the chain to the final target.

Griffe does not treat a partially resolved chain as a successful result. Cycles may produce `CyclicAliasError`; otherwise inaccessible targets can produce resolution errors when target information is requested.

`GriffeLoader.resolve_aliases()` exposes an explicit resolution phase. Loader configuration also controls whether Griffe attempts to load external packages to resolve imported references.

Architectural implication: A consumer can preserve the exposed API graph separately from the declaration graph. This is useful for cross-references, documentation, package boundary analysis, and version-to-version comparisons where changing a re-export may matter even if the original declaration remains untouched.

The limitation is that external-resolution completeness depends on the chosen loading scope. Aggressively resolving dependencies can significantly increase analysis work.

Source: [https://mkdocstrings.github.io/griffe/guide/users/loading/](https://mkdocstrings.github.io/griffe/guide/users/loading/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



### 4.3 Inheritance is represented without flattening class definitions

Griffe represents declared bases, resolved base classes, and inherited members separately.

For a class, these concepts must not be conflated:

- `bases` captures its declared base expressions.
- `resolved_bases` identifies base classes that Griffe can resolve within loaded objects.
- `mro()` provides the computed method-resolution order when it can be established.
- `members` represents members declared directly on the class.
- `inherited_members` provides inherited members, represented as aliases.
- `all_members` combines direct and inherited members.

Inherited members are not simply copied into subclasses. Their alias representation retains the fact that the implementation belongs to a base class.

Inheritance resolution is load-scope dependent. If a class inherits from a package that has not been loaded, Griffe will not automatically have complete information about that base's members.

There is also a performance consideration: inherited-member dictionaries are computed when accessed, and Griffe recommends caching the result in caller code when it will be reused.

The documentation identifies edge cases involving dynamically generated bases and certain classes for which static inheritance information is insufficient.

Source: [https://mkdocstrings.github.io/griffe/guide/users/navigating/](https://mkdocstrings.github.io/griffe/guide/users/navigating/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 4.4 Public API classification is more than an underscore convention

Griffe implements Python-oriented public interface rules, particularly the interaction among imports, names, and `__all__`.

For module-level declarations, an explicit `__all__` governs exported names. Without it, Griffe generally regards non-private, locally defined members as public, but does not automatically treat ordinary imported symbols as public re-exports.

Thus:

```
from external_lib import TypeAfrom .internal import TypeB__all__ = ["TypeB"]
```

`TypeB` is explicitly public through this module, whereas `TypeA` is not assumed to be part of its public contract merely because the import exists.

The library also distinguishes several related properties:

- `is_public`: whether an object belongs to the public API under Griffe's rules.
- `is_private`: whether the name follows private naming conventions.
- `is_special`: whether the name uses a special double-underscore form.
- `is_imported` and `is_exported`: how an object participates in import/export relationships.
- `public`: an explicit override, commonly set by extensions.

Notably, `is_public` and `is_private` are not mutually exclusive: an intentionally exported underscore-prefixed symbol may satisfy both.

This public-interface model is central to compatibility checking. Whether removing a declaration constitutes a public breaking change depends partly on how it was exposed.

Source: [https://mkdocstrings.github.io/griffe/guide/users/navigating/](https://mkdocstrings.github.io/griffe/guide/users/navigating/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



## 5. Structured expressions and typing semantics

### 5.1 Expressions are richer than rendered annotation strings

Griffe represents annotations and other relevant expressions using its own expression classes.

These include expressions arising from:

- Parameter and return annotations.
- Generic type parameters and type aliases.
- Class bases.
- Decorator expressions.
- Default parameter values.
- Attribute initializers.

Rather than storing only the textual representation, Griffe attaches name-resolution context. It can therefore reason about a referenced symbol's qualified path relative to the enclosing declaration.

For example, a decorator imported under a local alias can still be identified by its underlying qualified name. That enables extensions to recognize framework-specific decorators without relying exclusively on matching source text.

Griffe's expression tree retains structured relationships among names, attributes, calls, subscripts, unions, and other syntax forms. This is important both for analysis and for renderers that need individually addressable symbols.

### 5.2 Expression modernization

`Expr.modernize()` provides an AST-oriented representation transformation for older typing expressions.

It can modernize constructs such as:

| Legacy form          | Modern equivalent |
| -------------------- | ----------------- |
| `typing.List[T]`     | `list[T]`         |
| `typing.Dict[K, V]`  | `dict[K, V]`      |
| `typing.Optional[T]` | `T \\| None`      |
| `typing.Union[A, B]` | `A \\| B`         |

The method returns a new expression rather than rewriting the underlying source file.

This is useful for normalized documentation, cross-reference generation, and comparing API descriptions that use different generations of Python typing syntax.

It does not, by itself, prove semantic equivalence under every Python runtime or type-checker interpretation, nor does it make Griffe a type checker.

### 5.3 Source expressions are not evaluated values

This distinction affects both correctness and compatibility analysis.

Suppose a function declares:

```
def build(config=DEFAULT_CONFIG):    ...
```

Griffe can preserve `DEFAULT_CONFIG` as an expression and resolve its syntactic reference context. That does not imply Griffe has determined the actual object bound to the name when the function is called.

Likewise, an attribute initialized by `create_registry()` should not be interpreted as if Griffe had evaluated that call during static analysis.

This deliberate separation permits source analysis without code execution, but limits conclusions about runtime values and behavior.

Source: [https://mkdocstrings.github.io/griffe/reference/api/expressions/](https://mkdocstrings.github.io/griffe/reference/api/expressions/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



## 6. Structured docstring parsing

Griffe is also a standalone docstring parser. Its docstring capabilities are not merely an auxiliary function of package loading; they can be used independently to convert documentation text into structured semantic records.

### 6.1 Supported styles and differences

Griffe provides parsers for Google-style, NumPy-style, and Sphinx-style docstrings, plus an `auto` detection mode.

| Documentation construct                 | Google    | NumPy     | Sphinx        |
| --------------------------------------- | --------- | --------- | ------------- |
| Parameters, attributes, returns, raises | Supported | Supported | Supported     |
| Module/class member listings            | Supported | Supported | Not supported |
| Structured examples                     | Supported | Supported | Not supported |
| Other parameters                        | Supported | Supported | Not supported |
| Warnings                                | Supported | Supported | Not supported |
| Generator yields/receives               | Supported | Supported | Not supported |

The table reflects Griffe's documented parser coverage rather than the full capabilities of the underlying documentation conventions.

Consequently, a Sphinx-style docstring may contain material that Griffe does not turn into the same structured section types available to its Google and NumPy parsers. A downstream consumer should distinguish text present in a docstring from content recognized as a typed section.

Griffe does not impose a rendering markup language on the extracted text. Whether documentation becomes Markdown, reStructuredText, HTML, or another format is a responsibility of the consuming tool.

Source: [https://mkdocstrings.github.io/griffe/reference/docstrings/](https://mkdocstrings.github.io/griffe/reference/docstrings/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



### 6.2 Typed sections and elements

The parser produces `DocstringSection` objects and related models, allowing downstream programs to inspect documentation semantically.

Relevant classes include:

- `DocstringSectionText`
- `DocstringSectionParameters` and `DocstringParameter`
- `DocstringSectionAttributes`
- `DocstringSectionReturns`
- `DocstringSectionRaises`
- `DocstringSectionWarns`
- `DocstringSectionYields`
- `DocstringSectionReceives`
- `DocstringSectionExamples`
- `DocstringSectionAdmonition`

Rather than scraping a large text field for parameter descriptions, a consumer can operate directly on parsed documentation elements, preserving names, descriptions, inferred or explicit annotations, and applicable defaults.

This is useful for constructing search indexes, generating machine-readable API catalogs, identifying documentation gaps, or associating explanatory text with declarations.

### 6.3 Combining docstrings with signature information

A particularly valuable mechanism is that a `Docstring` can refer to its enclosing Griffe object.

If a function's documentation describes parameter `timeout` but omits its type, the parser can obtain the annotation from the parent function's signature. Similar behavior applies to certain return, generator, attribute, and class documentation sections.

For example:

```
from griffe import (    Docstring,    Function,    Parameter,    Parameters,)function = Function(    "connect",    parameters=Parameters(        Parameter("timeout", annotation="float"),    ),)docstring = Docstring(    """    Connect to the service.    Parameters:        timeout: Maximum connection duration.    """,    parent=function,)sections = docstring.parse("google")
```

This illustrates an important design property: the documentation representation can combine information from multiple sources while maintaining a distinction between declared syntax and prose documentation.

Standalone parsing does not require a package loader. A manually constructed parent provides access to the same enrichment mechanism.

Source: [https://mkdocstrings.github.io/griffe/guide/users/how-to/parse-docstrings/](https://mkdocstrings.github.io/griffe/guide/users/how-to/parse-docstrings/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 6.4 Parsing options, validation, and automatic style detection

The Google and NumPy parsers offer controls including `warn_unknown_params`, `warn_missing_types`, `trim_doctest_flags`, and general warning enablement.

These support several different functions:

- Detecting parameters described in documentation but absent from the function signature.
- Highlighting missing annotations or documented types.
- Removing doctest flags from displayed example text.
- Adjusting style-specific parsing conventions, including ambiguity between named values and type descriptions.
- Controlling treatment of constructor documentation when other tools merge class and initializer descriptions.

The `auto` parser has two meaningful strategies:

1. `heuristics` uses regular expressions to infer a style.
2. `max_sections` tries candidate parsers and selects the one that produces the most recognized sections, using `style_order` for ties.

The second strategy may be useful for heterogeneous documentation corpora but performs additional parsing work and does not guarantee correct classification for ambiguous docstrings.

The default style order documented for automatic detection is Sphinx, Google, then NumPy.

Source: [https://mkdocstrings.github.io/griffe/reference/docstrings/](https://mkdocstrings.github.io/griffe/reference/docstrings/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



### 6.5 Important limitations

Docstring parsing is not a general natural-language understanding system.

Its output reflects recognized conventions and syntax, rather than a determination that a description is complete or factually accurate.

Griffe can identify that a documented parameter is missing from the corresponding signature; it cannot establish that the prose correctly describes the parameter's behavior.

Likewise, a `Raises` section expresses what the author documented, not necessarily the exceptions that every execution path can raise.

This distinction matters when using the parsed sections for automated contracts or compliance checks: docstrings are evidence about an API's intended behavior, not an independently verified behavioral specification.

## 7. API breaking-change detection

Griffe's compatibility checker compares two representations of a Python package and reports changes that could break downstream consumers.

It is more sophisticated than simply diffing source files because it works with normalized interface structures, public exports, parameter semantics, and class relationships.

### 7.1 Structural comparison between versions

The checker takes an earlier and a later package representation and analyzes changes to their exposed interfaces.

Programmatic access uses `find_breaking_changes()`:

```
import griffeold = griffe.load_git("example_package", ref="v1.0.0")new = griffe.load_git("example_package", ref="v2.0.0")for breakage in griffe.find_breaking_changes(old, new):    print(breakage.explain())
```

Each detected issue is represented as a `Breakage` object, allowing a consumer to process findings rather than parsing CLI output.

This makes the checker useful as a reusable analysis component in release tooling and automated API governance.

### 7.2 Detected breakage categories

The current checker covers several distinct classes of interface changes.

| Category                   | Example                              | Why it matters                                              |
| -------------------------- | ------------------------------------ | ----------------------------------------------------------- |
| Positional parameter moved | `f(a, b)` → `f(b, a)`                | Existing calls may silently change meaning                  |
| Parameter removed          | Removing `timeout`                   | Previously valid arguments may be rejected                  |
| Parameter kind changed     | Positional-or-keyword → keyword-only | Existing positional calls may fail                          |
| Parameter default changed  | `enabled=True` → `enabled=False`     | Calls may retain valid syntax but change behavior           |
| Parameter became required  | Removing a default                   | Calls omitting the argument may fail                        |
| Required parameter added   | Adding a mandatory `token`           | Existing calls may become invalid                           |
| Public object removed      | Removing an exported class           | Imports or attribute access may fail                        |
| Public object kind changed | Class replaced by function           | Consumers may depend on object identity or type             |
| Class base removed         | Removing a superclass                | Inheritance relationships and inherited behavior can change |

The deliberate inclusion of default-value changes and class-base changes means the checker addresses more than immediate `TypeError` or `ImportError` failures. It can flag changes that may silently alter downstream behavior.

Nevertheless, these are potentially breaking changes, not proof that any particular consumer will fail.

### 7.3 Checks that are not implemented—or have been removed

Two particularly important exclusions are documented:

- Return type compatibility: The checker does not yet determine whether a changed return annotation is type-compatible.
- Attribute type compatibility: The checker does not yet establish compatibility between changed attribute annotations.

These require more sophisticated type relationships than comparing source expressions.

Version 2.4.1 change: Detection of changed attribute values was removed. Griffe's maintainers found that comparing expressions generated too many false positives, including when different expressions evaluate to the same value.

This means a static attribute's value changing is no longer reported by that check in 2.4.1. Older documentation or result examples that show an attribute-value breakage should not be interpreted as current behavior.

The broader point is that the checker does not provide complete behavioral compatibility, full semantic-versioning verification, or exhaustive static type compatibility. Dynamic exports, decorator transformations, unrecognized framework behavior, and incomplete dependency resolution can affect its results.

Source: [https://mkdocstrings.github.io/griffe/guide/users/checking/](https://mkdocstrings.github.io/griffe/guide/users/checking/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+3



### 7.4 Git history and package-index comparisons

The CLI supports comparing package states from Git tags, branches, and commits.

```
# Compare the current source against the latest Git tag.
griffe check example_package

# Compare two specific revisions.
griffe check example_package -a v1.0.0 -b v2.0.0

# Explicit source layout.
griffe check -s src example_package
```

For Git references, Griffe uses temporary worktrees so it can load older revisions without requiring the caller to manually check out each version.

It can also compare packages obtained from PyPI or another configured package index when the `pypi` extra is installed.

```
griffe check "" \
    -a example-distribution==1.0 \
    -b example-distribution==2.0
```

Here `-a` identifies the older version and `-b` the newer one. The empty positional package name asks Griffe to infer the import package name from distribution metadata.

For index-based comparisons, the packages are installed in a cache directory. Compatibility is therefore constrained by the current environment, and package installation can carry normal build and dependency requirements.

Source: [https://mkdocstrings.github.io/griffe/guide/users/checking/](https://mkdocstrings.github.io/griffe/guide/users/checking/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



### 7.5 CI and machine-readable findings

Griffe can fail a CI job when breaking changes are found.

It supports output formats suited to different consumers: one-line, verbose, Markdown, GitHub workflow annotations, and Azure DevOps logging commands.

These formats are presentation mechanisms over the same analysis, allowing findings to appear at relevant source locations in pull-request checks.

A version comparison also benefits from a complete Git history. Shallow CI checkouts may lack the historical revisions or tags needed for the requested comparison.

Source: [https://mkdocstrings.github.io/griffe/guide/users/checking/](https://mkdocstrings.github.io/griffe/guide/users/checking/?utm_source=chatgpt.com)

## 8. Extension architecture and framework-aware interpretation

The extension system is what makes Griffe substantially more capable than a fixed AST-to-JSON converter.

Griffe exposes hooks at different stages of analysis and permits extensions to enrich, modify, or synthesize object-model content.

### 8.1 Two families of extension events

| Event family    | Examples                                                                                      | Appropriate use                                                               |
| --------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Analysis events | `on_node`, `on_instance`, `on_members`, and kind-specific variants                            | Understanding or changing the initial extraction of source/runtime structures |
| Load events     | `on_object`, `on_module`, `on_class`, `on_function`, `on_attribute`, `on_alias`, `on_package` | Enriching or processing completed package object trees                        |

Analysis events occur while the visitor or inspector is still constructing the tree. Some referenced objects may not exist yet.

Load events occur after package construction and are generally preferable when an extension needs stable object relationships.

This distinction is especially relevant for import resolution, inheritance, and members whose meaning depends on the rest of the package.

Source: [https://mkdocstrings.github.io/griffe/guide/users/extending/](https://mkdocstrings.github.io/griffe/guide/users/extending/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



### 8.2 The extension contract

Extensions subclass `griffe.Extension` and implement methods corresponding to the events they need.

For example, an extension could tag certain functions with additional semantic metadata:

```
import griffeclass CategorizeFunctions(griffe.Extension):    def on_function(        self,        *,        func: griffe.Function,        **kwargs,    ) -> None:        if func.name.startswith("create_"):            func.extra["categorization"]["role"] = "factory"
```

The `extra` field is namespaced, allowing independent extensions and consumers to exchange metadata without introducing new fields into the core model.

Extensions can also override visibility and deprecation flags, change docstrings, adjust signatures, or add generated members.

The framework supports configurable extension constructors, module-based extension discovery, individual extension classes, and extensions loaded from local scripts.

Source: [https://mkdocstrings.github.io/griffe/guide/users/extending/](https://mkdocstrings.github.io/griffe/guide/users/extending/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+2



### 8.3 AST and runtime traversal within extensions

Beyond lifecycle callbacks, Griffe exposes visitor facilities for deeper inspection.

Extensions can traverse AST nodes through `visit()` and `generic_visit()`, implementing handlers for particular syntax types. Runtime object trees have analogous `inspect()` and `generic_inspect()` facilities.

This permits framework-aware extraction that works at different levels:

- Inspecting decorator calls and their arguments.
- Recognizing class-definition conventions.
- Extracting metadata from assignments.
- Interpreting selected syntax that creates implicit interface contracts.
- Examining dynamically generated runtime objects when static analysis is insufficient.

An extension that creates Griffe objects can also invoke the extension dispatcher so other installed extensions can process the newly created objects.

Architectural significance: Framework-specific semantic rules can be implemented as extensions while retaining Griffe's common model, navigational facilities, serialization, and documentation integrations.

### 8.4 Selective dynamic enrichment

One particularly useful pattern is to statically load a package, then dynamically inspect only specific declarations for which source analysis is insufficient.

Griffe documents this approach for dynamically generated docstrings through `griffe.dynamic_import()`.

The same architectural pattern can apply when a decorator or framework synthesizes information that cannot reliably be reconstructed from syntax alone.

Selective inspection is generally more targeted than forcing a dynamic import of an entire package. It does not eliminate execution risks: importing the selected object still executes the relevant Python import path and its dependencies.

Source: [https://mkdocstrings.github.io/griffe/guide/users/how-to/selectively-inspect/](https://mkdocstrings.github.io/griffe/guide/users/how-to/selectively-inspect/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 8.5 Built-in extensions

Griffe includes two particularly meaningful built-in extensions.

`dataclasses` — enabled by default

The dataclasses extension reconstructs initializer signatures for Python dataclasses during static analysis. It accounts for dataclass-specific behavior including `ClassVar`, `KW_ONLY`, `kw_only`, and `init` configuration.

For dynamically inspected dataclasses, generated runtime initializers are already available, so the extension does not need to synthesize them.

This capability demonstrates that Griffe can model some runtime-generated APIs without executing the code that generates them.

Source: [https://mkdocstrings.github.io/griffe/extensions/built-in/dataclasses/](https://mkdocstrings.github.io/griffe/extensions/built-in/dataclasses/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



`unpack_typeddict` — opt-in

This extension interprets `**kwargs: Unpack[SomeTypedDict]` and expands the typed dictionary into explicit keyword parameters in the Griffe representation.

It can also synthesize a TypedDict initializer signature and update structured documentation parameter sections to match.

The resulting representation is often substantially more informative to downstream documentation and interface tools than a single opaque `**kwargs` parameter.

Crucially, these changes affect the Griffe model, not the original function or runtime class.

Source: [https://mkdocstrings.github.io/griffe/extensions/built-in/unpack-typeddict/](https://mkdocstrings.github.io/griffe/extensions/built-in/unpack-typeddict/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 8.6 Official companion extensions

The project maintains separate extension distributions. These are not all included in the core Griffe package.

| Extension                         | Capability                                                                                                    |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `griffe-pydantic`                 | Extracts Pydantic model information, including inheritance-aware metadata, and supports specialized rendering |
| `griffe-inherited-docstrings`     | Copies documentation from parent declarations when an overriding subclass member lacks its own docstring      |
| `griffe-runtime-objects`          | Attaches corresponding live Python objects in namespaced `extra` metadata                                     |
| `griffe-sphinx`                   | Reads Sphinx-style `#:` comments above assignments as attribute docstrings                                    |
| `griffe-typingdoc`                | Extracts documentation from `Annotated` and `typing_extensions.Doc` metadata                                  |
| `griffe-warnings-deprecated`      | Recognizes `@warnings.deprecated`, storing deprecation information and associated documentation               |
| `griffe-public-redundant-aliases` | Marks redundant-alias imports as public according to that convention                                          |
| `griffe-public-wildcard-imports`  | Marks wildcard-imported objects as public                                                                     |
| `griffe-autodocstringstyle`       | Enables automatic docstring style detection for external packages                                             |

Several of these packages influence semantic interpretation, not merely presentation.

For example, the public-alias extensions change which objects are considered part of the public API. That can affect downstream documentation or compatibility analysis.

`griffe-typingdoc` is particularly distinctive because it can derive parameter and return documentation from typing metadata instead of conventional docstring sections. This offers an alternative way to associate structured explanation with declarations.

`griffe-runtime-objects`, conversely, intentionally bridges from a static object model back to executable runtime objects and therefore inherits the risks and environmental constraints of runtime inspection.

Individual documentation:

- [https://mkdocstrings.github.io/griffe/extensions/official/pydantic/](https://mkdocstrings.github.io/griffe/extensions/official/pydantic/?utm_source=chatgpt.com)
- [https://mkdocstrings.github.io/griffe/extensions/official/typingdoc/](https://mkdocstrings.github.io/griffe/extensions/official/typingdoc/?utm_source=chatgpt.com)
- [https://mkdocstrings.github.io/griffe/extensions/official/runtime-objects/](https://mkdocstrings.github.io/griffe/extensions/official/runtime-objects/?utm_source=chatgpt.com)
- [https://mkdocstrings.github.io/griffe/extensions/official/inherited-docstrings/](https://mkdocstrings.github.io/griffe/extensions/official/inherited-docstrings/?utm_source=chatgpt.com)
- [https://mkdocstrings.github.io/griffe/extensions/official/sphinx/](https://mkdocstrings.github.io/griffe/extensions/official/sphinx/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+8

## 9. Serialization and API data interchange

### 9.1 Object-model serialization

Griffe provides several layers of serialization:

- `Object.as_dict()` converts a Griffe object into a dictionary.
- `Object.as_json()` serializes its representation as JSON.
- `Object.from_json()` reconstructs an object from JSON.
- `JSONEncoder` and `json_decoder` offer lower-level control, including support for nested structures such as parameters and expressions.

By default, Griffe serializes the fields required to reconstruct its object models. A `full=True` representation includes additional available and derived information for consumers that do not use Griffe's own decoder.

The distinction is consequential. A minimal serialization optimized for rehydrating the model is not necessarily ideal as a self-contained external catalog.

```
import griffepackage = griffe.load(    "example_package",    resolve_aliases=True,)json_data = package.as_json(full=True)
```

The object tree can also be reconstructed from serialized data, making it possible to separate the initial analysis process from downstream consumers.

Source: [https://mkdocstrings.github.io/griffe/guide/users/serializing/](https://mkdocstrings.github.io/griffe/guide/users/serializing/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 9.2 A published JSON schema

Griffe publishes an explicit JSON schema:

[https://mkdocstrings.github.io/griffe/schema.json](https://mkdocstrings.github.io/griffe/schema.json?utm_source=chatgpt.com)

For automated consumers, this is particularly important because it provides a machine-readable reference for supported serialization structures rather than relying on an informal interpretation of examples.

The serialized format preserves member ordering through arrays rather than encoding members exclusively as unordered dictionaries.

Expressions can contain nested structures with `cls` discriminators identifying Griffe expression classes.

This gives consumers access to structured annotations, defaults, and decorators without having to reparse Python source.

A qualification: serialized data represents the information captured by the chosen loading and extension configuration. A schema-valid dump does not imply all aliases, external dependencies, or dynamic framework features were successfully resolved.

For persistent interchange, consumers should also track the generating Griffe version and extraction configuration. JSON-schema availability does not independently establish a guarantee that every serialized field remains stable across major releases.

Source: [https://mkdocstrings.github.io/griffe/guide/users/serializing/](https://mkdocstrings.github.io/griffe/guide/users/serializing/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

mkdocstrings.github.io+1



### 9.3 Source provenance and Git integration

Griffe associates object metadata with source locations, including filenames, line ranges, and source text where available.

Its Git information system can additionally construct links to the precise declarations in a remote source repository.

Relevant interfaces include `GitInfo`, `git_info`, and `source_link`.

An extension can override package-level Git metadata, including the repository location, hosting service, remote URL, and commit hash. Individual `source_link` values can also be overridden.

An easily overlooked capability is that this mechanism can provide source links to non-Python implementation files when the analyst knows the real origin of an object.

For example, a Python API implemented in a compiled Rust extension may be associated with a Rust source location rather than merely a Python wrapper or generated binding.

This does not mean Griffe analyzes Rust source. It means consumers can attach more accurate provenance to Python-facing objects.

Source: [https://mkdocstrings.github.io/griffe/guide/users/how-to/set-git-info/](https://mkdocstrings.github.io/griffe/guide/users/how-to/set-git-info/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



## 10. Packaging, CLI, and current release considerations

### 10.1 Distribution architecture

Griffe 2.x separates the library and command-line functionality into distributions.

| Distribution | Role                                                |
| ------------ | --------------------------------------------------- |
| `griffelib`  | Core analysis library without the CLI dependencies  |
| `griffecli`  | Command-line tooling                                |
| `griffe`     | Umbrella distribution providing the library and CLI |

Installing `griffelib` still exposes the Python import namespace `griffe`.

For a program that only needs to load and analyze Python APIs, the library-only distribution avoids dependencies needed exclusively by the CLI.

For command-line use, the umbrella distribution provides `griffe dump` and `griffe check`.

```
# Library and CLI
pip install griffe

# Library only
pip install griffelib

# Library and optional accelerator
pip install "griffe[faster]"

# Package-index comparisons
pip install "griffe[pypi]"
```

The current 2.4.1 release requires Python 3.11 or newer. The project lists support for Python 3.11 through 3.15.

Source: [https://mkdocstrings.github.io/griffe/installation/](https://mkdocstrings.github.io/griffe/installation/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



### 10.2 Command-line inspection controls

The `dump` command exposes much of the underlying loader configuration without requiring Python code.

Among its controls are:

- Search directories and whether to include the interpreter's `sys.path`.
- Forced or disabled runtime inspection.
- Stub-package discovery and stub-docstring precedence.
- Configured extensions.
- Docstring style and parser options.
- Alias resolution, including implicit and external imports.
- Full JSON serialization, output paths, and statistics.

For example:

```
griffe dump example_package \
    --search src \
    --full \
    --resolve-aliases \
    --output example_package.json
```

The CLI can also output multiple packages and use `{package}` in an output path to produce separate files.

These controls matter because a serialized API view is not fully determined by a package name alone. Its completeness and interpretation depend on how it was loaded.

Source: [https://mkdocstrings.github.io/griffe/reference/cli/](https://mkdocstrings.github.io/griffe/reference/cli/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 10.3 Performance mechanisms

Griffe's principal performance advantage comes from its focus: it extracts API-relevant structure rather than conducting exhaustive whole-program analysis.

Several mechanisms are relevant.

Source-analysis efficiency. Static parsing avoids the import and initialization costs of a package's runtime execution, although it still incurs filesystem access, parsing, tree construction, and resolution costs.

Finder reuse. A shared loader can reuse filesystem-discovery information rather than independently locating the same modules for every request.

Selective resolution. Keeping external alias resolution scoped can avoid recursively loading large dependency trees.

Optimized model operations. Griffe 2.3 introduced several improvements involving AST visitor dispatch, expression serialization, docstring parsing, annotation caching, inheritance-diff computation, and reduced unnecessary extension-event dispatch.

Optional parser accelerator. Griffe 2.4 introduced an optional `prune-source` accelerator, installed through the `faster` extra.

This separately distributed component uses Ruff-based processing to remove function bodies that Griffe does not need before constructing the CPython AST.

The mechanism can reduce the volume of syntax that must be parsed for packages containing substantial implementation bodies.

There are significant conditions on its use. Griffe falls back to its regular parser when:

- The accelerator is unavailable.
- The source uses Python grammar newer than the accelerator's pinned Ruff version.
- The file is a `.pyi` stub.
- An extension implements an AST-node visit-time hook requiring the original syntax.

That last condition is particularly important: the performance optimization is deliberately subordinated to extension correctness.

There is no general quantitative speedup that can be assumed for arbitrary packages. Benefits depend on how much implementation-body syntax is eliminated relative to package discovery, signature extraction, resolution, and other processing.

Source: [https://mkdocstrings.github.io/griffe/installation/](https://mkdocstrings.github.io/griffe/installation/?utm_source=chatgpt.com)

Changelog: [https://mkdocstrings.github.io/griffe/changelog/](https://mkdocstrings.github.io/griffe/changelog/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+2



### 10.4 Important recent changes

| Release                   | Consequential change                                                                                                |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| 2.4.1 — October 22, 2026  | Improved dynamic discovery of lazy attributes; removed attribute-value breaking-change detection                    |
| 2.4.0 — October 19, 2026  | Added `reference_path`; introduced optional source-pruning acceleration; corrected inherited visibility propagation |
| 2.3.2 — October 6, 2026   | Distribution metadata updated for Python 3.11+                                                                      |
| 2.3.0 — September 4, 2026 | Added precedence control for stub docstrings; substantial internal performance improvements                         |
| 2.2.0 — August 16, 2026   | Extended expression coverage and fidelity                                                                           |
| 2.0.0 — February 9, 2026  | Major distribution reorganization and API cleanup                                                                   |

These changes are relevant when comparing current documentation against older Griffe examples, especially examples involving removed compatibility checks or APIs deprecated before 2.0.

Source: [https://mkdocstrings.github.io/griffe/changelog/](https://mkdocstrings.github.io/griffe/changelog/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+2



## 11. Integration boundaries and architectural implications

Griffe's capabilities become especially valuable when its position among adjacent Python tooling is understood precisely.

### 11.1 Griffe versus other forms of Python inspection

| Tool family                           | Primary concern                                   | Relationship to Griffe                                                                           |
| ------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Python `ast`                          | Syntax-tree structure                             | Griffe builds API objects and resolution facilities over AST-derived information                 |
| `inspect`                             | Live Python objects                               | Griffe uses runtime inspection where needed, while offering a common static/dynamic model        |
| `LibCST`                              | Lossless syntax representation and transformation | Better suited to exact source rewriting; Griffe prioritizes semantic API extraction              |
| Tree-sitter                           | Incremental parsing and language syntax structure | Useful for editor/parser infrastructure; does not by itself supply Griffe's Python API semantics |
| Pyright, mypy, or other type checkers | Type inference and consistency                    | Complementary; Griffe retains typing declarations but is not a full type checker                 |
| Sphinx or MkDocs                      | Documentation construction and rendering          | Griffe provides extracted API information, not the complete publishing system                    |
| `mkdocstrings-python`                 | Python API documentation integration              | Consumes Griffe data and adds presentation, rendering, and documentation-site integration        |

The relevant distinction is not that Griffe replaces these tools. It handles a particular semantic layer that otherwise often requires bespoke code atop lower-level parsers.

### 11.2 Architectural combinations

Several general combinations are possible without imposing assumptions on a particular application.

Structured API catalogs. Griffe can supply declarations, qualified names, re-exports, signatures, docstrings, and source locations. A separate storage or indexing system can then organize those records for search and retrieval.

API-aware documentation systems. The combination of alias resolution, structured expressions, docstring sections, and extension metadata can avoid separate implementations of Python import analysis, signature extraction, and framework-specific API interpretation.

Release compatibility analysis. Serialized snapshots and breaking-change detection can provide a structural evidence layer for release tooling. Behavioral tests and type-checker analysis remain complementary.

Framework-aware inspection. Extensions can interpret decorators, generated constructors, metadata conventions, and selected runtime objects while retaining the common Griffe representation.

Source-linked knowledge graphs. A downstream system could model declarations, imports, exposed aliases, inheritance edges, documentation relationships, and provenance as explicit entities and relationships. Griffe provides much of the input information, although persistent graph modeling, entity reconciliation, querying, and incremental synchronization belong to the downstream system.

Hybrid static/runtime analysis. Static extraction can be used broadly, with selective runtime inspection reserved for dynamically synthesized APIs. This can preserve source-level fidelity without relying on indiscriminate imports.

These are architectural possibilities inferred from the verified capabilities, not advertised turnkey Griffe products.

### 11.3 Boundaries that matter most

The following constraints are especially important when determining what conclusions can be drawn from Griffe data.

| Boundary                                            | Consequence                                                                              |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Static analysis is not execution                    | Computed values and dynamically synthesized objects may be unavailable                   |
| Object classification is not full type inference    | Annotated or parsed expressions do not establish type compatibility                      |
| Import resolution depends on loading scope          | Missing external dependencies can leave aliases or inheritance incomplete                |
| Documentation describes intent                      | Parsed docstrings do not prove behavior                                                  |
| API diffing is not behavioral verification          | Breaking-change detection is necessarily incomplete                                      |
| Runtime inspection executes imports                 | Untrusted code, side effects, and dependency requirements remain concerns                |
| Generated metadata may depend on extensions         | Different extension configurations can produce different API representations             |
| Source location is not always implementation origin | Native or generated objects may need explicit provenance corrections                     |
| JSON is a snapshot format                           | Griffe does not thereby become a persistent database or an incremental dependency engine |

One additional performance boundary deserves emphasis: Griffe does not advertise a general-purpose, source-aware incremental computation framework. Its internal caching optimizations and loader reuse should not be confused with automatic dependency tracking and invalidation across continuously changing repositories.

Likewise, its AST visitor and expression representation do not amount to a complete control-flow graph, data-flow graph, call graph, or symbolic execution engine.

For those tasks, Griffe's declaration and interface metadata can serve as an input to specialized analysis tooling, rather than replacing it.

## 12. Primary-source reference map

The following pages provide the most useful entry points for deeper investigation. All are direct URLs.

| Topic                                            | Primary source                                                                                                                                                                  |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Installation and distribution choices            | [https://mkdocstrings.github.io/griffe/installation/](https://mkdocstrings.github.io/griffe/installation/?utm_source=chatgpt.com)                                               |
| Loading, inspection, stubs, and alias resolution | [https://mkdocstrings.github.io/griffe/guide/users/loading/](https://mkdocstrings.github.io/griffe/guide/users/loading/?utm_source=chatgpt.com)                                 |
| Object-model navigation and API semantics        | [https://mkdocstrings.github.io/griffe/guide/users/navigating/](https://mkdocstrings.github.io/griffe/guide/users/navigating/?utm_source=chatgpt.com)                           |
| Docstring parser syntax, options, and coverage   | [https://mkdocstrings.github.io/griffe/reference/docstrings/](https://mkdocstrings.github.io/griffe/reference/docstrings/?utm_source=chatgpt.com)                               |
| Standalone docstring parsing                     | [https://mkdocstrings.github.io/griffe/guide/users/how-to/parse-docstrings/](https://mkdocstrings.github.io/griffe/guide/users/how-to/parse-docstrings/?utm_source=chatgpt.com) |
| API compatibility checks                         | [https://mkdocstrings.github.io/griffe/guide/users/checking/](https://mkdocstrings.github.io/griffe/guide/users/checking/?utm_source=chatgpt.com)                               |
| Extension lifecycle and implementation           | [https://mkdocstrings.github.io/griffe/guide/users/extending/](https://mkdocstrings.github.io/griffe/guide/users/extending/?utm_source=chatgpt.com)                             |
| JSON serialization                               | [https://mkdocstrings.github.io/griffe/guide/users/serializing/](https://mkdocstrings.github.io/griffe/guide/users/serializing/?utm_source=chatgpt.com)                         |
| JSON schema                                      | [https://mkdocstrings.github.io/griffe/schema.json](https://mkdocstrings.github.io/griffe/schema.json?utm_source=chatgpt.com)                                                   |
| Source provenance and Git links                  | [https://mkdocstrings.github.io/griffe/guide/users/how-to/set-git-info/](https://mkdocstrings.github.io/griffe/guide/users/how-to/set-git-info/?utm_source=chatgpt.com)         |
| Command-line reference                           | [https://mkdocstrings.github.io/griffe/reference/cli/](https://mkdocstrings.github.io/griffe/reference/cli/?utm_source=chatgpt.com)                                             |
| API loader reference                             | [https://mkdocstrings.github.io/griffe/reference/api/loaders/](https://mkdocstrings.github.io/griffe/reference/api/loaders/?utm_source=chatgpt.com)                             |
| API object models                                | [https://mkdocstrings.github.io/griffe/reference/api/models/](https://mkdocstrings.github.io/griffe/reference/api/models/?utm_source=chatgpt.com)                               |
| API checking internals                           | [https://mkdocstrings.github.io/griffe/reference/api/checks/](https://mkdocstrings.github.io/griffe/reference/api/checks/?utm_source=chatgpt.com)                               |
| Release history                                  | [https://mkdocstrings.github.io/griffe/changelog/](https://mkdocstrings.github.io/griffe/changelog/?utm_source=chatgpt.com)                                                     |
| Upstream repository                              | [https://github.com/mkdocstrings/griffe](https://github.com/mkdocstrings/griffe?utm_source=chatgpt.com)                                                                         |

## Overall assessment

Griffe's strongest distinguishing feature is the combination of static source extraction, runtime inspection, symbol resolution, and an extensible semantic object model.

Each individual component has alternatives. Python already provides AST parsing and runtime introspection; type checkers provide more sophisticated typing semantics; documentation frameworks can render source information; and custom analyzers can track declarations and imports.

What Griffe offers is their integration into a purpose-built Python API representation, with additional support for public exports, inherited members, structured docstrings, expression modeling, serialization, and compatibility comparisons.

Its most easily overlooked capabilities are the distinction between exposed and canonical symbol paths, structured expressions with lexical resolution context, type-stub merging, synthesis of otherwise runtime-generated signatures through extensions, selective dynamic enrichment, and the ability to attach framework-specific metadata while retaining a common interface.

The resulting library is particularly well suited to systems that need a reliable, inspectable representation of Python APIs without implementing their own Python-specific declaration, signature, and import-processing machinery.

The natural boundary is equally clear: Griffe describes and compares interfaces. It does not independently establish the full behavior, type correctness, execution dependencies, or runtime semantics of the programs those interfaces expose.

# Griffe (Python) — Technical Capability Addendum

Research date: November 12, 2026 | Target: Griffe 2.4.1 | Supplements the original capability overview

This addendum expands on Griffe's less obvious capabilities, particularly its symbol-resolution machinery, low-level analysis interfaces, expression semantics, programmatic model operations, and extension ecosystem. It also clarifies several important behavioral limitations.

The central additional insight is that Griffe is not only an API extraction framework; it also provides a programmable infrastructure for representing, resolving, constructing, and comparing Python interface models. Several of its lower-level mechanisms can be used independently of package loading, documentation generation, and its built-in compatibility checker.

The descriptions below distinguish Griffe's core functionality from companion extensions and architectural possibilities that would require additional machinery. The verified stable release is 2.4.1, published October 22, 2026.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



## 1. Symbol resolution as an explicit, measurable operation

### 1.1 Resolution completeness and iteration controls

Griffe separates initial object extraction from the resolution of imports and other aliases. The `GriffeLoader.resolve_aliases()` API provides direct control over how extensively it attempts to connect references to their targets:

```
unresolved, iterations = loader.resolve_aliases(    implicit=False,    external=None,    max_iterations=None,)
```

The parameters control three independent aspects of the operation.

| Parameter        | Function                                                                                                     |
| ---------------- | ------------------------------------------------------------------------------------------------------------ |
| `implicit`       | When `False`, eagerly resolves only explicitly exported aliases; when `True`, also attempts implicit aliases |
| `external`       | Controls whether unresolved imports can trigger loading additional packages                                  |
| `max_iterations` | Bounds the number of passes over the module collection                                                       |

`external` has three meaningful settings. `False` prevents loading otherwise unspecified packages, while `True` permits broader external loading. The default, `None`, allows limited special-case loading, including private sibling or origin modules, such as `_ast` when analyzing `ast`.

The return value is particularly useful. `unresolved` is a set of alias paths that Griffe attempted but could not resolve; `iterations` reports how many passes were performed.

For example:

```
import griffeloader = griffe.GriffeLoader(search_paths=["src"])package = loader.load("example_package")unresolved, iterations = loader.resolve_aliases(    implicit=True,    external=False,)print("Unresolved aliases:", unresolved)print("Resolution passes:", iterations)
```

This exposes a distinction between successful structural extraction and complete reference resolution.

An object tree can be valid and useful while still containing unresolved aliases. The return value allows consumers to recognize such incompleteness instead of treating all extracted relationships as authoritative.

There are two qualifications:

1. The unresolved set describes aliases considered under the selected resolution policy. With `implicit=False`, it is not an inventory of every unresolved import in the package.
2. The iteration count is a measure of resolution work, not a percentage-complete metric. More passes do not necessarily indicate a more accurate result.

This separation supports a general architecture in which broad extraction is performed first, while additional packages are loaded only when particular cross-package relationships warrant resolution.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/loaders/](https://mkdocstrings.github.io/griffe/reference/api/loaders/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 1.2 Shared module collections enable cross-package symbol resolution

Griffe provides `ModulesCollection`, the registry through which loaded modules and packages can be found by their qualified names.

A single collection can be shared between independent calls to `griffe.load()`:

```
import griffecollection = griffe.ModulesCollection()package_a = griffe.load(    "package_a",    modules_collection=collection,)package_b = griffe.load(    "package_b",    modules_collection=collection,    resolve_aliases=True,)
```

If `package_b` imports a declaration from `package_a`, Griffe can resolve the alias against the already registered object rather than requiring an independent representation of the same dependency.

A persistent `GriffeLoader` achieves a similar result because it retains its own module collection across loads.

This makes the module collection more than an implementation detail. It provides a shared identity and lookup context for cross-package analysis.

That can reduce duplicate extraction and preserve consistent references among packages. However, it is not a general semantic cache: the collection does not automatically detect filesystem changes or invalidate outdated source representations.

Primary source: [https://mkdocstrings.github.io/griffe/guide/users/loading/](https://mkdocstrings.github.io/griffe/guide/users/loading/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 1.3 Bidirectional aliases and reverse reference discovery

The original overview described imports and re-exports primarily as forward pointers. Griffe also maintains reverse alias relationships.

An `Alias` exposes its `target_path` and, once resolved, its `target`. Conversely, a Griffe `Object` exposes an `aliases` dictionary that maps the paths of aliases pointing at that object to the corresponding alias instances.

Consider:

```
# package/internal.pyclass Widget:    ...# package/__init__.pyfrom .internal import Widget# package/public_api.pyfrom .internal import Widget
```

After the relevant modules and aliases have been loaded and resolved, the underlying `Widget` declaration can be inspected to discover its alternate exposed locations:

```
widget = package["internal.Widget"]for alias_path, alias in widget.aliases.items():    print(alias_path, alias.path)
```

This permits both directions of analysis:

| Direction             | Question answered                                           |
| --------------------- | ----------------------------------------------------------- |
| Alias → declaration   | Which original declaration does this public name reference? |
| Declaration → aliases | Through which other names is this declaration exposed?      |

The second direction is particularly useful when modeling public APIs separately from implementation ownership.

A single declaration may be reachable through several paths, and each exposure can have its own visibility, source location, and documentation context.

The reverse mapping reflects registered, resolved aliases. It should not be interpreted as an exhaustive index of every possible runtime reference to the declaration.

Primary source: [https://mkdocstrings.github.io/griffe/guide/users/navigating/](https://mkdocstrings.github.io/griffe/guide/users/navigating/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 1.4 Lazy alias resolution and failure behavior

Alias objects behave as proxies for many properties of their targets.

Accessing an alias's docstring, members, or other target-derived properties can require Griffe to resolve the underlying reference.

This creates several distinct states:

- An alias has been discovered, but its target has not yet been resolved.
- The target resolves successfully to another Griffe object.
- The alias points to another alias, forming a resolution chain.
- The target is unavailable because its module is missing or not loaded.
- Resolution encounters a cycle.

Relevant APIs and exceptions include `Alias.resolved`, `Alias.resolve_target()`, `Alias.target`, `Alias.final_target`, `AliasResolutionError`, and `CyclicAliasError`.

`final_target` follows indirections to the underlying object. `resolve_target()` explicitly attempts resolution and can raise an error if the necessary declaration is unavailable.

Consumers should therefore not assume that inspecting an arbitrary target-derived property is a side-effect-free operation that always succeeds.

A significant practical distinction is that an unresolved alias is still a meaningful model element: its exposed name and intended target path may be useful even without a resolved declaration.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/models/alias/](https://mkdocstrings.github.io/griffe/reference/api/models/alias/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



## 2. Export construction and public namespace reconstruction

### 2.1 Recursive expansion of `__all__`

Python modules frequently construct their public exports by importing and combining export lists from other modules.

Griffe exposes `GriffeLoader.expand_exports()` to resolve supported export composition patterns.

For example:

```
from .first import __all__ as first_exportsfrom .second import __all__ as second_exports__all__ = [*first_exports, *second_exports, "AdditionalType"]
```

Here the effective public namespace depends on information declared in other modules.

`expand_exports()` recursively expands these referenced export declarations and updates the module's represented exports.

This matters because accurately reconstructing a package API requires understanding not only declarations but also how names are assembled and exposed across modules.

The expansion mechanism supports a range of ordinary static constructs, but does not evaluate arbitrary Python code that might modify `__all__` at runtime. It can leave references unexpanded when necessary modules are unavailable, and the implementation expects export entries that ultimately resolve to valid names.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/loaders/](https://mkdocstrings.github.io/griffe/reference/api/loaders/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 2.2 Wildcard imports are expanded into explicit aliases

`GriffeLoader.expand_wildcards()` processes imports such as:

```
from package.public import *
```

Rather than retaining only an opaque wildcard import, Griffe can discover which members are exposed and construct aliases for the imported names.

The expansion uses the originating module's exposure rules, including `__all__` where present.

There are several consequential details.

Transitive expansion. A module can itself contain wildcard imports. Griffe recursively attempts to expand these dependencies so that the importing module receives individual exposed symbols.

Declaration-order precedence. When a wildcard import introduces a name that already exists, Griffe considers source-line ordering when deciding whether the new imported alias should replace the earlier declaration. This models the common Python behavior in which a later assignment or import overwrites an earlier binding.

Cross-package loading. Like ordinary alias resolution, wildcard expansion can require loading external modules. The `external` parameter controls how aggressively that happens.

Cycle handling. Griffe tracks visited objects to avoid unbounded recursion. The implementation also handles certain self-referencing aliases that can arise from complex wildcard relationships.

There is an important limitation: when a submodule and a wildcard-imported attribute have the same name, Griffe gives precedence to the submodule because its object model cannot store both under the same member key.

Thus, Griffe's reconstructed namespace is not guaranteed to reproduce every possible import-order-dependent Python runtime state.

The important architectural opportunity is the ability to convert common import-mediated public interfaces into explicit, navigable symbol relationships. This avoids requiring every downstream consumer to implement its own wildcard-import interpretation.

Primary sources:

[https://mkdocstrings.github.io/griffe/reference/api/loaders/](https://mkdocstrings.github.io/griffe/reference/api/loaders/?utm_source=chatgpt.com)

[https://mkdocstrings.github.io/griffe/guide/users/recommendations/python-code/](https://mkdocstrings.github.io/griffe/guide/users/recommendations/python-code/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1

## 3. Direct analysis APIs and synthetic Python environments

Griffe's high-level loader is not the only way to obtain its object models. The library exposes the individual analysis agents and a set of utilities for constructing Python source environments programmatically.

These capabilities are particularly valuable when the objective is to analyze individual language constructs, compare interpretation strategies, or test extensions.

### 3.1 Direct static and dynamic analysis

The principal lower-level entry points are `griffe.visit()` and `griffe.inspect()`.

`visit()` performs AST-based analysis of a module. It accepts source information, module identity, and configuration for extensions, documentation parsing, and shared collections.

`inspect()` performs runtime inspection of an imported module or module object and produces the corresponding Griffe representation.

The distinction from `griffe.load()` is one of orchestration. The loader discovers packages, selects analysis strategies, loads submodules, and coordinates resolution. The individual agents operate at the module-analysis level.

This enables three different configurations:

| Analysis mode      | Responsibility                                                                      |
| ------------------ | ----------------------------------------------------------------------------------- |
| `griffe.load()`    | Package discovery, analysis selection, recursive loading, optional alias resolution |
| `griffe.visit()`   | Direct extraction from Python AST/source                                            |
| `griffe.inspect()` | Direct extraction from live Python module objects                                   |

A system examining isolated source constructs need not invoke all of the discovery and loading machinery merely to construct a Griffe model.

Conversely, using `visit()` independently does not automatically provide the full cross-module context normally assembled by a loader.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/agents/](https://mkdocstrings.github.io/griffe/reference/api/agents/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 3.2 Temporary source and package analysis

Griffe exposes context-manager helpers for constructing disposable Python analysis environments.

| Helper                          | Function                                              |
| ------------------------------- | ----------------------------------------------------- |
| `temporary_pyfile()`            | Creates a temporary `.py` file from supplied source   |
| `temporary_pypackage()`         | Constructs a temporary package from supplied modules  |
| `temporary_visited_module()`    | Parses source and yields a statically analyzed module |
| `temporary_visited_package()`   | Creates and statically loads a synthetic package      |
| `temporary_inspected_module()`  | Creates a temporary module for runtime inspection     |
| `temporary_inspected_package()` | Creates and dynamically inspects a synthetic package  |

The distinction between temporary source construction and temporary analysis is important.

`temporary_pypackage()` provides filesystem structure. The visited and inspected helpers additionally execute the appropriate Griffe analysis.

For example:

```
import griffesource = """from typing import Generic, TypeVarT = TypeVar("T")class Container(Generic[T]):    def get(self, index: int) -> T:        ..."""with griffe.temporary_visited_module(source) as module:    container = module["Container"]    get_method = container["get"]    print(get_method.parameters)    print(get_method.returns)
```

Illustrative example; not executed.

The result is an ordinary Griffe `Module`, permitting the same navigation and expression inspection used for installed packages.

The package helpers also support configuration such as extensions, docstring parsing, resolution behavior, and common module collections.

This makes it possible to examine complex cases involving multiple modules without introducing permanent files or requiring an installed distribution.

Potential uses include testing import resolution, `__all__` composition, inherited members, overload handling, stub merging, and the interpretation of framework decorators.

The runtime-inspection variants execute imported Python code. Their temporary nature does not provide security isolation from import side effects.

### 3.3 Programmatic construction of object hierarchies

Three additional helpers are worth distinguishing:

- `vtree()` creates a vertical parent-child chain of Griffe objects.
- `htree()` attaches multiple Griffe objects as members of a common parent.
- `module_vtree()` constructs a module hierarchy from a dotted module path.

For example, a vertical tree can be constructed from separately instantiated `Module`, `Class`, and `Function` objects without parsing Python source.

These helpers support synthetic model construction, particularly for testing consumers and extensions.

They are tree-construction utilities, not visualization renderers. The previous gap analysis characterized them too broadly as tree-representation helpers; their actual purpose is to establish Griffe object relationships.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/helpers/](https://mkdocstrings.github.io/griffe/reference/api/helpers/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



## 4. Package discovery and namespace-package semantics

### 4.1 `ModuleFinder` as a separately accessible component

Griffe exposes the filesystem discovery machinery through `ModuleFinder`.

Its capabilities include `find_package()`, `find_spec()`, `iter_submodules()`, `append_search_path()`, and `insert_search_path()`.

The finder recognizes conventional Python source and stub files, together with supported compiled-module extensions. Its documented accepted extensions include `.py`, `.pyi`, `.pyc`, `.pyo`, `.pyd`, and `.so`.

The finder and loader have distinct responsibilities.

`ModuleFinder` determines where a package or module can be found. `GriffeLoader` then decides how to analyze the discovered files and whether to recurse through submodules.

The finder maintains a directory-listing cache, and a loader ordinarily owns its own finder instance.

Its search paths can be modified without reconstructing the entire analysis environment.

### 4.2 Namespace packages spanning multiple directories

A particularly relevant capability is support for Python namespace packages.

A conventional package typically has an `__init__.py` file. A namespace package may have no such initializer and may aggregate contributions from multiple directories.

The finder distinguishes `Package` from `NamespacePackage`. A `NamespacePackage` contains the package name and a collection of filesystem paths corresponding to its contributing directories.

This enables discovery of interfaces organized across multiple source roots.

Griffe's object models additionally provide the predicates `is_namespace_package` and `is_namespace_subpackage`, alongside conventional `is_package` and `is_subpackage`.

These distinctions matter because no single filesystem directory necessarily contains the complete interface of a namespace package.

A package's representation therefore depends on the configured search paths and which namespace portions are discoverable.

The finder also supports detection of separately distributed stub-only packages. If source and stub distributions are both available, the loading process can combine their information.

A namespace package remains an ordinary Griffe module hierarchy for downstream navigation, but its source provenance can span multiple directories.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/finder/](https://mkdocstrings.github.io/griffe/reference/api/finder/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



## 5. Expression-tree analysis beyond annotations

The original overview describes Griffe's enhanced expressions, but their independent analysis capabilities deserve further explanation.

Griffe's expression types are useful not only for preserving source syntax but also for extracting references and recognizing structurally significant language constructs.

### 5.1 Two traversal modes

The `Expr.iterate()` method provides two different views over an expression:

```
expression.iterate(flat=True)expression.iterate(flat=False)
```

With `flat=True`, Griffe flattens an expression into strings and name-expression elements. This supports reconstruction of readable source while preserving identifiable names.

With `flat=False`, iteration exposes immediate structural elements. Nested expressions remain structured and can be traversed recursively.

Consider:

```
def fetch(    items: list[Model | None],    factory: Callable[[], Model] = default_factory,):    ...
```

Griffe can represent the signature's annotations and default expressions as nested structures rather than isolated strings.

A structural consumer could distinguish the union expression, the `list` subscription, the `Callable` subscription, and the referenced `Model` name. It could then resolve the names independently.

This differs from a simple string-based representation such as `"list[Model | None]"`, which would require reparsing to recover the same relationships.

Griffe also exposes expression-specific fields such as the function and arguments of an `ExprCall`, the base and slice of an `ExprSubscript`, and the elements of an `ExprTuple`.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/expressions/](https://mkdocstrings.github.io/griffe/reference/api/expressions/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 5.2 Reference paths versus canonical paths

Griffe 2.4.0 introduced `reference_path`, which is particularly important for symbolic-reference consumers.

The property belongs to the expression representation, including `ExprName`. It should not be confused with `Alias.target_path` or assumed to be an `Alias` property.

Relevant expression properties include:

| Property         | Meaning                                                                                        |
| ---------------- | ---------------------------------------------------------------------------------------------- |
| `path`           | The expression's resolved full name where available, falling back to its source representation |
| `canonical_path` | Canonical name/path representation                                                             |
| `reference_path` | A reference target suitable for cross-referencing, or `None` when no known target is available |
| `resolved`       | The resolved Griffe object where supported                                                     |
| `parent`         | The lexical or expression context used in resolution                                           |
| `member`         | The contextual member name used for resolution                                                 |

The significant distinction is that `reference_path` is intentionally more selective.

According to the API reference, it accepts names that resolve through explicit parent context and recognized built-ins. Unknown names without an appropriate scope can yield `None`.

This is helpful for consumers generating symbol references because a syntactically valid name does not necessarily identify a symbol that should receive a cross-reference.

For example, the literal `UnknownType` may be preserved in a signature, while the reference system correctly recognizes that Griffe has not established its target.

Architectural implication: A consumer can distinguish retaining a source expression from confidently attaching a relationship to a known declaration.

Source: [https://mkdocstrings.github.io/griffe/reference/api/expressions/](https://mkdocstrings.github.io/griffe/reference/api/expressions/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 5.3 Expression classification and type-parameter recognition

Griffe's expression objects expose several semantic predicates.

Common properties include `is_classvar`, `is_generator`, `is_iterator`, and `is_tuple`.

`ExprName` exposes additional capabilities:

- `is_enum_class`
- `is_enum_instance`
- `is_enum_value`
- `is_type_parameter`

These predicates enable selected structural interpretations without requiring every caller to implement its own recognition logic.

For instance, `is_type_parameter` distinguishes a generic parameter reference from an ordinary referenced class or variable.

This becomes useful when interpreting generic APIs, class variables, enum declarations, and iterator or generator annotations.

The information remains limited by static context and the names Griffe can resolve. These predicates are not substitutes for arbitrary inference about runtime values.

### 5.4 Expression equality is not semantic identity

One easily overlooked detail appears in `ExprName.__eq__`.

The implementation considers two name expressions equal when their `name` values are equal, without considering their parent contexts.

That means two expressions can compare equal as expression names while referring to different declarations in different scopes.

Consequently, raw `ExprName` equality should not be assumed to establish that two references denote the same semantic entity.

For semantic relationship matching, qualified reference information and resolution context are more informative.

This is an important distinction for any consumer constructing persistent identities or comparing symbols across versions.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/expressions/](https://mkdocstrings.github.io/griffe/reference/api/expressions/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 5.5 Standalone expression extraction utilities

The expression API also exposes utilities including `get_expression()`, `safe_get_expression()`, `get_annotation()`, `get_base_class()`, `get_class_keyword()`, and `get_condition()`.

These convert supported Python AST constructs into Griffe's structured expressions.

The `safe_get_*` variants provide error-tolerant extraction behavior for cases where a syntax construct cannot be interpreted normally.

This functionality is useful independently of entire-module loading. A caller already possessing a Python AST can use Griffe's expression interpretation without reconstructing its complete visitor pipeline.

The boundary is that these utilities do not provide general expression evaluation. They construct structured representations from syntax and available context.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/expressions/](https://mkdocstrings.github.io/griffe/reference/api/expressions/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



## 6. Model-level queries, mutation, and interface detail

### 6.1 Composable member filtering

Griffe's `Object.filter_members()` provides a built-in filtering mechanism over an object's direct members.

Its signature accepts multiple predicates:

```
filter_members(    *predicates,) -> dict[str, griffe.Object | griffe.Alias]
```

Each predicate receives a member and returns a Boolean. All predicates must pass for a member to be included.

For example:

```
public_functions = module.filter_members(    lambda member: member.is_public,    lambda member: member.is_function,)
```

This avoids manual filtering of `module.members`.

The method returns a dictionary keyed by member names, retaining the associated Griffe objects.

Two behaviors are important:

It operates on direct members. It should not be confused with independently querying `all_members`, which can include inherited declarations.

With no predicates, it returns the underlying `members` dictionary. Consumers should not assume that calling it without predicates creates a new detached collection.

For aliases, the corresponding operation delegates to the resolved underlying target.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/models/function/](https://mkdocstrings.github.io/griffe/reference/api/models/function/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 6.2 Lexical name resolution through `Object.resolve()`

`Object.resolve(name)` attempts to resolve a name within the current object's scope and enclosing scopes.

It returns a resolved path or raises `NameResolutionError` when the name cannot be resolved.

The implementation examines information such as:

- Generic type parameters declared in the current scope.
- Direct members.
- Aliases and their target paths.
- Enclosing objects and module scopes.

This is separate from `GriffeLoader.resolve_aliases()`.

The loader-level method connects alias objects within the module collection. `Object.resolve()` instead answers a scoped-name question for a particular object.

For example, when a method annotation contains `Result`, resolving that name relative to its enclosing class or module provides more information than looking it up in an unrelated global dictionary.

The source implementation explicitly notes that its rules do not necessarily reproduce every Python lexical-scoping behavior. It should be treated as Griffe's name-resolution mechanism, not a complete substitute for the Python compiler's symbol-table analysis.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/models/class/](https://mkdocstrings.github.io/griffe/reference/api/models/class/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 6.3 Consumer access versus producer mutation

Griffe distinguishes APIs intended for reading a completed object tree from those suitable for constructing or modifying one.

The `members` dictionary and kind-filtered collections are convenient for consumers. However, while an extension is constructing the tree, not all relationships are necessarily ready to be queried.

The methods `get_member()`, `set_member()`, and `del_member()` are designed for structural operations, including those performed by extensions.

`set_member()` maintains appropriate parent relationships when registering a member.

This is important because directly inserting an object into a dictionary may leave the parent hierarchy inconsistent.

Similarly, retrieving members through consumer-oriented properties during partial analysis can trigger inheritance or alias-resolution behavior before the necessary structure has been assembled.

The distinction matters most for extensions that synthesize members, modify generated APIs, or reorganize extracted declarations.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/models/class/](https://mkdocstrings.github.io/griffe/reference/api/models/class/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 6.4 Additional interface semantics

Several existing model fields were omitted or insufficiently developed in the original reference.

| Model feature                              | Additional capability                                                                  |
| ------------------------------------------ | -------------------------------------------------------------------------------------- |
| `Class.keywords`                           | Preserves keyword arguments from class declarations, including metaclass configuration |
| Class and module `overloads`               | Retain overload declarations indexed by name                                           |
| `Function.overloads`                       | Exposes alternative declared function signatures                                       |
| `Attribute.setter` and `Attribute.deleter` | Preserve additional components of property interfaces                                  |
| `Module.imports_future_annotations`        | Records whether postponed annotations were enabled through the future import           |
| `type_parameters`                          | Represents generic type parameters on relevant classes, functions, and type aliases    |
| `deprecated`                               | Stores explicit deprecation status or associated descriptive information               |
| `is_deprecated`                            | Provides Boolean deprecation classification                                            |

These become consequential when modeling interfaces more precisely than a single rendered signature.

For example, a public property may be readable but not writable. Its setter and deleter relationships are therefore meaningful parts of the exposed interface.

A function may provide several overload signatures, meaning its accepted call patterns cannot be inferred solely from the implementation signature.

Similarly, a class's `metaclass=` keyword represents a declaration-level relationship that may influence dynamically generated members or class behavior, even though Griffe does not fully execute those semantics.

Primary source: [https://mkdocstrings.github.io/griffe/guide/users/navigating/](https://mkdocstrings.github.io/griffe/guide/users/navigating/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



## 7. Source retention, stub merging, and analysis instrumentation

### 7.1 Independent source and module collections

Griffe separates extracted API objects from retained source text.

`ModulesCollection` holds the analyzed module hierarchy and provides lookup context.

`LinesCollection` stores source lines associated with file paths.

Both collections can be supplied to relevant loading and analysis APIs.

The `store_source` parameter controls whether the loader retains source text in its lines collection.

This is useful when structural metadata is needed but retaining complete source content would be unnecessary.

However, source retention has functional implications. Consumers relying on source snippets, accurate code excerpts, or operations that read stored lines may require the source collection.

Disabling retained source data does not prevent the original files from being parsed. It changes what remains available after extraction.

### 7.2 Direct stub merging

Griffe also exposes `merge_stubs()` independently of package discovery:

```
merged = griffe.merge_stubs(    source_module,    stub_module,    prefer_stubs_docs=False,)
```

This permits combining two already constructed module representations.

The important separation is between discovering `.py` and `.pyi` counterparts and merging the interface information they contain.

Direct merging permits the second operation to be used when the caller has obtained source and stub models through another process.

The operation enriches Griffe's model rather than rewriting either source file.

Merge semantics remain governed by Griffe's expectations about the corresponding declarations and supported stub constructs. It should not be understood as arbitrary reconciliation of unrelated module trees.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/loaders/](https://mkdocstrings.github.io/griffe/reference/api/loaders/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1



### 7.3 Built-in extraction statistics

`GriffeLoader.stats()` returns a `Stats` object that describes work performed by the loader.

Relevant fields include:

| Statistic                | Meaning                                                    |
| ------------------------ | ---------------------------------------------------------- |
| `by_kind`                | Object counts categorized by Griffe kind                   |
| `packages`               | Number of top-level packages represented                   |
| `modules_by_extension`   | Module counts grouped by source or compiled-file extension |
| `lines`                  | Number of retained source lines                            |
| `time_spent_visiting`    | Time recorded for static analysis                          |
| `time_spent_inspecting`  | Time recorded for dynamic inspection                       |
| `time_spent_serializing` | Serialization timing field, where populated                |
| `as_text()`              | Produces a textual summary                                 |

This can help distinguish workloads dominated by source analysis from those involving substantial runtime inspection.

For example, comparing the number of `.py` modules with compiled modules and the corresponding visit/inspection timings can reveal whether the workload is principally static or hybrid.

The instrumentation does not provide a complete performance profile. The source also initializes some timing fields to zero; a field's existence should not be mistaken for comprehensive measurement of every downstream operation.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/loaders/](https://mkdocstrings.github.io/griffe/reference/api/loaders/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 7.4 Configurable Git provenance discovery

Griffe can discover Git metadata for source-link generation, but also permits environment-level control.

Two documented variables are:

- `GRIFFE_GIT_REMOTE_URL`, specifying a remote URL directly.
- `GRIFFE_GIT_REMOTE`, selecting a named Git remote instead of the default `origin`.

This matters when source analysis runs in an environment where repository metadata is incomplete or the ordinary remote does not correspond to the desired public source location.

It complements the model's direct Git-information overrides, allowing provenance configuration at different levels.

Primary source: [https://mkdocstrings.github.io/griffe/guide/users/loading/](https://mkdocstrings.github.io/griffe/guide/users/loading/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



## 8. Programmatic compatibility checking: exact scope and results

### 8.1 Structured `Breakage` objects

The original overview covers the existence of Griffe's breaking-change checker, but its return model deserves more detail.

`find_breaking_changes()` yields `Breakage` instances containing structured information:

| Field or method | Function                                                |
| --------------- | ------------------------------------------------------- |
| `kind`          | Identifies the breakage category through `BreakageKind` |
| `obj`           | References the relevant Griffe object                   |
| `old_value`     | Holds the previous value or interface representation    |
| `new_value`     | Holds the incompatible replacement                      |
| `details`       | Provides additional contextual information              |
| `as_dict()`     | Serializes the finding                                  |
| `explain()`     | Generates a human-readable explanation                  |

For example:

```
import griffeold = griffe.load_git("example_package", ref="1.0.0")new = griffe.load_git("example_package", ref="2.0.0")breakages = list(griffe.find_breaking_changes(old, new))for change in breakages:    print(change.kind)    print(change.obj.path)    print(change.as_dict())
```

This enables findings to be consumed as classified records without parsing textual descriptions.

The `old_value` and `new_value` fields can contain different data types depending on the breakage category, so downstream consumers should interpret them according to `kind`.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/checks/](https://mkdocstrings.github.io/griffe/reference/api/checks/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 8.2 The checker examines incompatibilities, not all API changes

The checker compares existing public members in the earlier representation against their counterparts in the later representation.

This is deliberately asymmetric.

A newly introduced public function generally does not constitute a breakage and is not reported merely because it did not exist before.

Likewise, changing documentation, adding an optional parameter, or modifying an implementation without changing the modeled interface does not automatically produce a finding.

Consequently, a complete inventory of API changes is a different operation from Griffe's breaking-change detection.

The distinction can be expressed as:

| Change classification                          | Native checker                  |
| ---------------------------------------------- | ------------------------------- |
| Selected incompatible interface modifications  | Supported                       |
| Removal of previously public members           | Supported                       |
| Addition of ordinary new public members        | Not reported as breakages       |
| Every signature and annotation modification    | Not exhaustively reported       |
| Documentation changes                          | Not a general comparison target |
| Runtime behavioral changes                     | Not determined                  |
| Semantic equivalence of implementation changes | Not determined                  |

This limitation is particularly important when interpreting an empty result set.

An empty `find_breaking_changes()` result is not evidence that two API models are identical.

### 8.3 Detection depends on call compatibility and representation

Some of Griffe's parameter checks incorporate the presence of variadic arguments.

For example, removing a previously accepted keyword-only parameter may not necessarily break calls if the new signature accepts arbitrary keyword arguments through `**kwargs`.

Similarly, positional arguments may be absorbed through `*args`.

The checker accounts for selected combinations of these mechanisms rather than treating every removed named parameter as automatically incompatible.

This is an important distinction between syntactic parameter changes and potentially invalidated calling patterns.

However, acceptance by `*args` or `**kwargs` does not establish equivalent runtime behavior. The implementation might no longer interpret a previously recognized keyword.

Another limitation is that changes to parameter defaults are determined from their represented values or expressions, not from full runtime evaluation.

Two different default expressions can evaluate to the same object, while unchanged expressions can acquire different behavior because their dependencies changed.

### 8.4 Existing breakage classes do not imply implemented checks

Griffe's API reference retains `ReturnChangedTypeBreakage` and `AttributeChangedTypeBreakage` classes.

However, the current user guide explicitly labels return-type and attribute-type compatibility checking as unsupported.

Similarly, `AttributeChangedValueBreakage` remains visible in the API reference, but the actual attribute-value check was removed in version 2.4.1.

Thus, the presence of a particular `BreakageKind` or `Breakage` subclass does not establish that `find_breaking_changes()` currently emits that kind.

This distinction matters when constructing automated expectations around the checker.

Source distinction: The classes are documented API representations; the checker’s currently implemented detection behavior is described separately in the checking guide and implementation.

Primary sources:

[https://mkdocstrings.github.io/griffe/guide/users/checking/](https://mkdocstrings.github.io/griffe/guide/users/checking/?utm_source=chatgpt.com)

[https://mkdocstrings.github.io/griffe/reference/api/checks/](https://mkdocstrings.github.io/griffe/reference/api/checks/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe+1

### 8.5 Comparison scope is not equivalent to arbitrary object equality

The signature of `find_breaking_changes()` accepts `Object | Alias` instances:

```
griffe.find_breaking_changes(old_obj, new_obj)
```

This allows comparisons over module and class member hierarchies, not only package roots.

Nevertheless, its implementation begins by traversing members of the supplied objects.

That means passing two leaf `Function` objects directly is not equivalent to invoking a general signature comparator on those functions.

For ordinary function breakage detection, the comparison is reached through corresponding members of enclosing objects.

This is a subtle but important distinction when treating the checker as a reusable programmatic component.

It is designed primarily to identify breaking differences across exposed object hierarchies, not to provide a universal equality or semantic-equivalence operation for every Griffe model type.

Primary source: [https://mkdocstrings.github.io/griffe/reference/api/checks/](https://mkdocstrings.github.io/griffe/reference/api/checks/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



## 9. Docstring parsing lifecycle and cached representations

Griffe preserves the original docstring content separately from its parsed sections.

A `Docstring` provides its underlying value, parser configuration, parser options, and a structured parsed representation.

Parsing is optional during initial loading.

A caller may load objects without requesting a parser and then parse selected docstrings later.

### 9.1 `parsed` is cached

Griffe's `Docstring.parsed` property is cached after parsing.

Changing `parser` or `parser_options` does not automatically invalidate the previously cached representation.

This matters when extensions change how docstrings should be interpreted.

For example, an extension might determine that a particular class uses NumPy-style documentation rather than Google-style documentation. That configuration must be established before depending on already parsed sections, or the parsed representation must be explicitly reconstructed.

The distinction is between:

- Raw documentation text.
- The selected parsing configuration.
- The cached collection of parsed sections.

A consumer that modifies one should not assume the others automatically change.

### 9.2 Parsed documentation can depend on its parent API object

As noted in the original overview, docstring parsers can obtain missing annotations and defaults from enclosing functions, attributes, or classes.

This introduces an additional dependency.

If the enclosing Griffe object changes after parsing—perhaps because an extension modifies its parameters—the cached docstring sections may no longer reflect the latest model state.

The appropriate general interpretation is that parsed docstrings are derived representations whose correctness depends on both the underlying text and their contextual API declarations.

The library provides the relevant parsing mechanisms, but does not advertise a general dependency-tracked invalidation engine for these derived records.

Primary source: [https://mkdocstrings.github.io/griffe/guide/users/navigating/](https://mkdocstrings.github.io/griffe/guide/users/navigating/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



## 10. Additional third-party semantic extensions

Griffe's official extension directory identifies several third-party packages that broaden the semantics available through its model.

These packages are independently maintained and should not be treated as built-in functionality.

### 10.1 Generic type specialization: `griffe-generics`

`griffe-generics` resolves generic type parameters to concrete bound types in subclasses.

Consider:

```
class Repository[T]:    def get(self) -> T:        ...class UserRepository(Repository[User]):    ...
```

Without contextual specialization, an inherited method signature can retain the generic parameter `T`.

The extension substitutes the bound type into inherited method and attribute annotations, allowing a subclass API to expose a representation closer to `get() -> User`.

This is particularly significant for documentation and interface analysis involving generic base classes, because inherited signatures are often the primary public methods of concrete subclasses.

The extension is distinct from a full static type checker. It targets generic parameter substitution within Griffe representations.

Source: [https://mkdocstrings.github.io/griffe/extensions/third-party/generics/](https://mkdocstrings.github.io/griffe/extensions/third-party/generics/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 10.2 Declarative model fields: `griffe-fieldz`

`griffe-fieldz` enriches documentation for classes whose fields are defined through framework conventions.

The documented supported families include:

- Standard-library dataclasses.
- Pydantic `BaseModel`.
- `attrs` classes.
- `msgspec.Struct`.

The extension uses the separate `fieldz` project to obtain field information and injects that information into Griffe's documentation representation.

The value is not merely cosmetic. Declarative models often expose important externally meaningful fields even when their constructors or attributes are not manually documented in conventional function signatures.

The extension makes this field metadata available to documentation consumers without requiring authors to duplicate the information in docstrings.

It is important to distinguish the roles:

`fieldz` provides the framework-specific field abstraction; `griffe-fieldz` integrates that abstraction with Griffe's documentation model.

Source: [https://mkdocstrings.github.io/griffe/extensions/third-party/fieldz/](https://mkdocstrings.github.io/griffe/extensions/third-party/fieldz/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



### 10.3 Framework routes and documentation transformations

Other third-party extensions listed by the project include:

| Extension                           | Additional interpretation                                                                        |
| ----------------------------------- | ------------------------------------------------------------------------------------------------ |
| `griffe-fastapi`                    | Recognizes decorated FastAPI route functions and attaches route-related metadata                 |
| `griffe-inherited-method-crossrefs` | Replaces inherited-method documentation with references to the corresponding parent declarations |
| `griffe-modernized-annotations`     | Applies modern Python typing syntax to annotation representations                                |
| `docstring-inheritance`             | Provides additional docstring inheritance behavior through a Griffe extension                    |

These demonstrate that the extension model supports several different forms of enrichment.

A framework extension may add semantic metadata that is not explicitly represented by standard Python signatures. A documentation extension may change how existing API elements are described without changing their underlying declarations.

An annotation extension may transform a representation into a normalized presentation form.

These are distinct operations and should not be assumed to provide identical guarantees.

The official Griffe directory documents the packages' intended functions, but inclusion in that directory does not establish current compatibility with every Griffe version or guarantee identical support for every version of an underlying framework.

Sources:

[https://mkdocstrings.github.io/griffe/extensions/third-party/](https://mkdocstrings.github.io/griffe/extensions/third-party/?utm_source=chatgpt.com)

[https://mkdocstrings.github.io/griffe/extensions/third-party/fastapi/](https://mkdocstrings.github.io/griffe/extensions/third-party/fastapi/?utm_source=chatgpt.com)

[https://mkdocstrings.github.io/griffe/extensions/third-party/modernized-annotations/](https://mkdocstrings.github.io/griffe/extensions/third-party/modernized-annotations/?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe

## 11. Additional source-fidelity limits

Griffe's AST-based analysis is intentionally more specific than general Python interpretation. Certain edge cases affect not just completeness, but the identity or origin of extracted API elements.

### 11.1 Submodule and member name collisions

Python can exhibit situations where a package submodule and another attribute share the same name.

Runtime behavior may depend on the order in which imports and assignments occur.

Griffe's member model permits only one object under a given name within a particular parent.

As a result, it cannot faithfully represent both a submodule and a distinct attribute with the same qualified path.

The implementation favors the submodule in certain wildcard-expansion cases.

This is a structural limitation of the model rather than merely a failure to follow an import.

### 11.2 Circular wildcard imports

Complex chains of wildcard imports can form ambiguous or self-referential relationships.

Griffe attempts recursive expansion and uses safeguards against cycles, but the upstream documentation acknowledges that some patterns cannot be reconstructed accurately.

Consequently, successful package loading should not be interpreted as proof that every complicated wildcard namespace was resolved according to exact runtime behavior.

### 11.3 Forward references in generic base classes

Certain forms of string-based forward references in class bases can interfere with inheritance analysis.

This can be especially relevant where generic bases refer to types that have not yet been declared or resolved.

The limitation should be distinguished from ordinary postponed annotation handling.

A forward reference in a method's return annotation need not have the same consequence as one participating in a class's base expression.

Because inheritance is used to construct method-resolution order and inherited-member relationships, incomplete base resolution can affect more than a rendered annotation.

### 11.4 Native extension source identity

For compiled Python extension objects, Griffe may depend on runtime metadata to determine where an object was originally defined.

A relevant example occurs when an extension object reports an incorrect or overly public `__module__` value.

If a class is actually defined in an internal compiled module but identifies itself as belonging to a top-level re-export module, Griffe can incorrectly infer that it is a declaration rather than an imported alias, or vice versa.

The upstream recommendations specifically discuss this problem in relation to PyO3.

Correctly supplying module information through metadata such as PyO3's `#[pyclass(module = "...")]` can improve Griffe's interpretation.

This does not enable Griffe to analyze arbitrary Rust implementation bodies. It improves the canonical identity of Python objects obtained through runtime inspection.

Primary source: [https://mkdocstrings.github.io/griffe/guide/users/recommendations/python-code/](https://mkdocstrings.github.io/griffe/guide/users/recommendations/python-code/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mkdocstrings.github.io\&sz=32)

Griffe



## 12. Consequences for semantic API representations

The additional capabilities establish several useful distinctions for advanced consumers of Griffe data.

### Declaration identity versus exposed API identity

A declaration's canonical location and its public aliases need not be the same. Reverse alias indexing enables analysis of both ownership and exposure.

This is important because a public API can change without changing the original declaration, and a declaration can acquire additional public locations without being redefined.

### Structural representation versus semantic resolution

An expression can be successfully extracted even when the names it references cannot be resolved.

Likewise, a module can be fully parsed while some external imports remain unresolved.

Griffe preserves these partially known states rather than requiring every analysis to produce a completely closed object graph.

### Extracted interfaces versus derived interpretations

Several capabilities produce information derived from the underlying API model:

- Inherited member collections.
- Framework-generated signatures.
- Specialized generic annotations.
- Parsed docstring sections.
- Resolved symbol references.
- Breaking-change classifications.

These interpretations depend on the underlying model, loading scope, extension configuration, and sometimes the timing of analysis.

A source declaration, a resolved alias, and a parsed documentation section therefore have different information dependencies.

### Compatibility findings versus semantic equivalence

Griffe's native checker provides a defined set of interface incompatibility checks.

It does not provide a general-purpose method for determining whether two implementations are functionally equivalent, whether two independently extracted API objects are semantically identical, or whether arbitrary internal changes can safely reuse prior analytical results.

Those questions may be informed by Griffe's structured representations, but require comparison and dependency semantics beyond what its native checker establishes.

### Native functionality versus extension-derived semantics

The core library provides Python API structure, reference resolution, and analysis infrastructure.

Extensions can add framework-specific interpretation, generated fields, specialized typing relationships, and documentation transformations.

This combination means Griffe's effective semantic coverage is configurable. It does not mean every supported extension enriches the same fields or participates identically in serialization and compatibility checking.

The distinction between native and extension-derived information remains important when reasoning about completeness, reproducibility, or compatibility across analysis runs.

## Additional primary-source references

These sources complement those in the original overview and cover the mechanisms developed in this addendum.

| Capability                                                                      | Direct documentation                                                                                                                                                                    |
| ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Alias resolution, collections, wildcard expansion, stub merging, and statistics | [https://mkdocstrings.github.io/griffe/reference/api/loaders/](https://mkdocstrings.github.io/griffe/reference/api/loaders/?utm_source=chatgpt.com)                                     |
| Alias targets and resolution exceptions                                         | [https://mkdocstrings.github.io/griffe/reference/api/models/alias/](https://mkdocstrings.github.io/griffe/reference/api/models/alias/?utm_source=chatgpt.com)                           |
| Direct static and runtime analysis                                              | [https://mkdocstrings.github.io/griffe/reference/api/agents/](https://mkdocstrings.github.io/griffe/reference/api/agents/?utm_source=chatgpt.com)                                       |
| Temporary analysis environments and object-tree construction                    | [https://mkdocstrings.github.io/griffe/reference/api/helpers/](https://mkdocstrings.github.io/griffe/reference/api/helpers/?utm_source=chatgpt.com)                                     |
| Package discovery and namespace handling                                        | [https://mkdocstrings.github.io/griffe/reference/api/finder/](https://mkdocstrings.github.io/griffe/reference/api/finder/?utm_source=chatgpt.com)                                       |
| Expression classes and reference-resolution properties                          | [https://mkdocstrings.github.io/griffe/reference/api/expressions/](https://mkdocstrings.github.io/griffe/reference/api/expressions/?utm_source=chatgpt.com)                             |
| Programmatic breakage representations                                           | [https://mkdocstrings.github.io/griffe/reference/api/checks/](https://mkdocstrings.github.io/griffe/reference/api/checks/?utm_source=chatgpt.com)                                       |
| Model navigation and documentation lifecycle                                    | [https://mkdocstrings.github.io/griffe/guide/users/navigating/](https://mkdocstrings.github.io/griffe/guide/users/navigating/?utm_source=chatgpt.com)                                   |
| Python source-fidelity recommendations                                          | [https://mkdocstrings.github.io/griffe/guide/users/recommendations/python-code/](https://mkdocstrings.github.io/griffe/guide/users/recommendations/python-code/?utm_source=chatgpt.com) |
| Independently maintained extensions                                             | [https://mkdocstrings.github.io/griffe/extensions/third-party/](https://mkdocstrings.github.io/griffe/extensions/third-party/?utm_source=chatgpt.com)                                   |

The principal addition to the original capability picture is Griffe's utility as a configurable semantic object-model infrastructure. Its collection management, resolution machinery, direct analysis agents, structured expressions, model-construction helpers, and extension interfaces support applications that go considerably beyond rendering documentation or checking conventional API breakages, while retaining explicit limits around runtime behavior, type inference, and completeness of semantic resolution.