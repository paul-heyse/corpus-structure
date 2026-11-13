# ty — Comprehensive Python Type Checker and Language Server Reference

Research date: November 12, 2026 | Version: 0.0.101 | Status: Public beta | License: MIT

ty is a high-performance, Rust-based Python static type checker and language server developed by Astral, the organization behind Ruff and uv.

Unlike a conventional type checker focused primarily on verifying annotated interfaces, ty combines type inference, semantic analysis, control-flow reasoning, incremental dependency tracking, and IDE functionality in a unified analysis engine.

Its distinguishing characteristics are:

- Fine-grained incremental analysis: Tracks dependencies down to individual definitions, allowing changes to invalidate only affected computations rather than requiring complete module reanalysis.
- Advanced type inference: Analyzes annotated and unannotated code, including sophisticated type narrowing, intersection types, and reachability reasoning.
- Gradual typing: Supports partially typed programs, including code that mixes explicitly annotated types with dynamically inferred or unknown types.
- Semantic language services: Provides symbol navigation, references, rename operations, type-aware completion, hover information, and other LSP capabilities using the same underlying analysis.
- Python ecosystem awareness: Resolves project packages, virtual environments, third-party typing information, and selected framework-specific semantics.
- Configurable diagnostics: Supports individual diagnostic severities, selective suppression, project-specific overrides, and incremental adoption mechanisms.

The latest verified release is 0.0.101, published November 11, 2026. Despite substantial functionality, ty remains explicitly classified as beta software. Its type-checking behavior, compatibility, and some configuration or experimental interfaces are still evolving.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



Primary resources:

- Official documentation: `https://docs.astral.sh/ty/`
- Source repository: `https://github.com/astral-sh/ty`
- Release history: `https://github.com/astral-sh/ty/releases`
- Python package: `https://pypi.org/project/ty/`
- Interactive playground: `https://play.ty.dev/`

## 1. Conceptual model and architectural boundaries

ty is best understood as a persistent semantic analysis engine with two public interfaces: a command-line type checker and a Language Server Protocol (LSP) implementation.

It reads Python source and typing declarations, constructs a semantic representation of the program, resolves symbols and imports, infers types, evaluates relationships between types, and produces diagnostics or editor responses.

Its main responsibilities differ from adjacent tools:

| Capability                 | ty's role                                                                               | Important boundary                                                            |
| -------------------------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Static type checking       | Validate types, calls, assignments, attributes, inheritance, and control flow           | Does not execute code or validate runtime values                              |
| Type inference             | Determine expression and variable types; optionally infer unannotated function returns  | Inference is limited by unknown values, dynamic behavior, and available stubs |
| Semantic analysis          | Resolve bindings, definitions, references, and type relationships                       | Not a documented general-purpose Python semantic-index API                    |
| Incremental computation    | Maintain reusable analysis and dependency information                                   | Internal computation graph is not an exposed, stable invalidation interface   |
| IDE functionality          | Serve semantic navigation, completion, diagnostics, and refactoring operations          | Not a formatter or full replacement for every editor feature                  |
| Environment interpretation | Resolve first-party packages, installed dependencies, stubs, and target Python versions | Does not ordinarily manage Python installations or packages itself            |
| Framework understanding    | Apply specialized inference for selected dynamic libraries                              | Not a general runtime introspection or user-extensible plugin mechanism       |

A central distinction is that the internal Rust analysis engine should not be confused with a supported Python library API. Although ty is installable as a Python package, its documented consumer interfaces are primarily `ty check`, `ty server`, configuration files, and LSP. Its internal semantic types and queries are implementation components rather than a promised public schema or query service.

Source: `https://docs.astral.sh/ty/` and `https://github.com/astral-sh/ruff/tree/main/crates/ty_python_semantic`.

## 2. Type-system capabilities

### 2.1 Gradual typing and inference

ty supports conventional Python typing constructs, including generic types, unions, literals, protocols, callable signatures, overloaded functions, and structural interfaces. It also analyzes partially annotated or unannotated Python code.

Crucially, ty distinguishes between explicit and implicit dynamic typing:

| Internal type | Interpretation                                                                      |
| ------------- | ----------------------------------------------------------------------------------- |
| `Any`         | Explicitly dynamic type, generally introduced by annotations or typing declarations |
| `Unknown`     | Implicitly dynamic type arising from insufficient type information                  |
| `Never`       | Bottom type used for impossible values or unreachable paths                         |
| `@Todo`       | Internal indication of a type-checking capability not yet implemented               |
| `Divergent`   | Internal representation associated with recursive inference that has not converged  |

`Unknown` behaves much like `Any` for gradual typing, but preserving its provenance makes implicit uncertainty visible. For example, `Unknown | None` can retain the possibility that a value is absent instead of indiscriminately erasing that distinction.

`@Todo` is especially important when interpreting results: it may indicate an implementation limitation rather than a defect in the analyzed program. Neither `@Todo` nor `Divergent` is intended as a type for user annotations.

Source: `https://docs.astral.sh/ty/reference/typing-faq/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 2.2 Redeclarations and variable-type transitions

Python often reuses a variable name for a different kind of value:

```
from pathlib import Pathdef parse_paths(paths: str) -> list[Path]:    paths: list[str] = paths.split(":")    return [Path(path) for path in paths]
```

ty explicitly accommodates redeclarations that change a variable's type.

This is distinct from control-flow narrowing. Narrowing refines the possible values of an existing variable; redeclaration introduces a new declared type for the reused binding.

That distinction matters for codebases with data-transformation pipelines, parsers, and intermediate representations: such code need not be rewritten merely to preserve a single unchanging variable type.

Source: `https://docs.astral.sh/ty/features/type-system/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 2.3 First-class intersection types

One of ty's most distinctive capabilities is its internal use of intersection types.

A union `A | B` describes values that satisfy either type. An intersection `A & B` describes values that satisfy both.

For example:

```
def process(value: Serializable) -> str:    if isinstance(value, Versioned):        reveal_type(value)  # Serializable & Versioned        return f"{value.serialize_json()}:{value.version}"    return value.serialize_json()
```

The type checker retains both the original structural requirements and the additional knowledge established by the runtime check.

This becomes more consequential in gradual typing. Narrowing an `Unknown` value with `isinstance(value, Iterable)` can produce `Unknown & Iterable`, permitting iteration while retaining dynamically accessible members of the original value.

ty also constructs intersections with synthetic protocols when processing checks such as `hasattr(value, "name")`. It can preserve a class that currently lacks the member because a subclass might introduce it. Marking a class `@final` allows stronger conclusions by excluding such subclasses.

Intersection types are thus not merely display notation: they underpin ty's approach to flow-sensitive reasoning.

Annotation boundary: `A & B` is not ordinary Python typing syntax. ty provides a checker-specific `Intersection` type through `ty_extensions`, currently intended for type-checking-time use. Using it directly introduces portability considerations with other checkers.

Source: `https://docs.astral.sh/ty/features/type-system/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 2.4 Top/bottom materializations and generic narrowing

Python's runtime checks discard generic arguments. `isinstance(value, list)` establishes that the value is a list but does not establish what types its elements contain.

This creates a subtle problem when the starting type contains `Any` or `Unknown`, especially for invariant collections.

ty models the distinction using top and bottom materializations of gradual types. Under its stricter generic narrowing mode, a successful runtime check may produce an internal type such as:

`Top[list[Unknown]]`

This represents the family of possible list specializations, rather than claiming that the list can safely accept elements of any type.

By default, `strict-generic-narrowing` is disabled: ty uses more permissive gradual narrowing, often retaining a useful generic specialization from the original type. Enabling it produces more conservative results for `isinstance`, `issubclass`, class patterns, and `TypeIs` checks.

The practical distinction is between useful inferred types and proof that a mutable generic value has a particular specialization. These are not always equivalent.

Source: `https://docs.astral.sh/ty/reference/configuration/` and `https://docs.astral.sh/ty/features/type-system/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty+1



### 2.5 Flow-sensitive analysis and reachability

ty reasons about the relationships between assignments, conditions, branches, and possible types. Its analysis covers more than straightforward `isinstance` narrowing.

Examples include:

- Positive and negative conditions that eliminate incompatible union members.
- Truthiness and equality reasoning, sometimes refining types to literals.
- `hasattr` checks that establish structural constraints.
- Pattern matching and generic class checks.
- Reachability of branches based on statically known type information.
- Python-version- and platform-dependent conditional code.

A particularly useful case is a branch guarded by a recognized version comparison. ty can identify code that is unreachable under the configured environment and avoid reporting errors as if the branch could execute.

Soundness consideration: ty deliberately provides a `strict-equality-semantics` setting because some intuitive equality-based narrowing is not valid for all Python classes and overloaded equality methods. Enabling it preserves broader types in situations where more aggressive reasoning could be unsound.

These facilities enable deeper analysis of real Python control flow without requiring every intermediate operation to be manually annotated.

Source: `https://docs.astral.sh/ty/features/type-system/` and `https://docs.astral.sh/ty/reference/configuration/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty+1



### 2.6 Bidirectional inference and contextual constraints

The implementation also uses bidirectional type inference: an expected type can influence how an expression is inferred, rather than inference proceeding exclusively from an expression outward.

This is particularly relevant to collection literals, generic specialization, and expressions appearing in annotated assignments or other typed contexts.

The upstream implementation distinguishes a declared contextual type from a type variable's upper bound. The latter constrains which values are valid but does not necessarily supply the preferred specialization for a generic expression.

This is an implementation-level observation, not a separately exposed user API.

Source: `https://github.com/astral-sh/ruff/blob/main/crates/ty_python_semantic/src/types/infer.rs`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 2.7 Generics, protocols, and standard typing features

ty aims to implement the Python typing specification, with support spanning the principal families of modern typing:

| Family                  | Relevant concepts                                                            |
| ----------------------- | ---------------------------------------------------------------------------- |
| Parametric polymorphism | `TypeVar`, generic classes/functions, bounds and constraints, PEP 695 syntax |
| Callable typing         | `Callable`, overloads, parameter specifications, function decorators         |
| Structural typing       | `Protocol`, attribute and method compatibility, generic protocols            |
| Structured records      | `TypedDict`, required/optional keys, `NamedTuple`, dataclasses               |
| Refinement              | `Literal`, `TypeIs`, `TypeGuard`, `assert_type`, `reveal_type`               |
| Class contracts         | `Self`, `ClassVar`, `Final`, `@final`, `@override`                           |
| Typing metadata         | `Annotated`, `NewType`, aliases and stub declarations                        |

This table describes the supported capability families, not a claim that every edge case or PEP is fully implemented. The feature tracker remains authoritative for exact syntax, variance rules, recursive forms, variadic generics, overloaded implementations, and recent typing-spec additions.

Source: `https://github.com/astral-sh/ty/issues/1889` and `https://docs.astral.sh/ty/reference/rules/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



## 3. Incremental architecture and performance

### 3.1 Semantic dependency tracking, not just file caching

ty's design is based on reusable semantic queries and fine-grained dependency tracking.

Conceptually, its analysis proceeds through interconnected representations:

Python source, stubs, and environment

Parsing, semantic indexing, and name resolution

Type inference and dependency-aware semantic queries

Scopes, definitions, statements, expressions, and related type computations

Diagnostics

Navigation and references

Completions and IDE services

Conceptual architecture derived from the documentation and source code; not a literal diagram of every internal query.

The source implementation uses Salsa, Rust's incremental computation framework. Type inference is organized into tracked computations for scopes, definitions, statements, and expressions, with mechanisms for handling cyclic dependencies and recursive types.

This has several consequences:

1. A local edit does not necessarily invalidate every analysis result in its containing module.
2. An unchanged semantic dependency may allow downstream work to be reused.
3. Unrelated third-party code can remain unanalyzed when its semantics are not needed.
4. The language server can reuse analysis state across successive editor requests.

These are fundamentally different capabilities from simply storing a checksum per Python file and rerunning a checker when the checksum changes.

Sources: `https://docs.astral.sh/ty/features/language-server/` and `https://github.com/astral-sh/ruff/blob/main/crates/ty_python_semantic/src/types/infer.rs`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty+1



### 3.2 Recursive inference and fixed-point computation

The internal source documents query-cycle handling using iterative recovery. Certain recursive type computations attempt to converge on a fixed point instead of treating every dependency cycle as inherently invalid.

This distinction is important because mutually recursive definitions, recursive type aliases, and cyclic import relationships can be legitimate or semantically meaningful in Python.

However, successful recovery is conditional. ty's FAQ explicitly documents `Divergent` for cases where inference has not converged, and the implementation notes that failure of the underlying query iteration to converge as expected is an implementation problem.

Consequently, recursive-analysis support should not be interpreted as a guarantee that arbitrary recursive typing relationships can always be inferred precisely.

Source: `https://github.com/astral-sh/ruff/blob/main/crates/ty_python_semantic/src/types/infer.rs` and `https://docs.astral.sh/ty/reference/typing-faq/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 3.3 Performance characteristics

Astral reports substantially faster checking than mypy and Pyright in its published benchmarks, particularly for cold project analysis and small incremental changes.

Its December 2025 beta announcement reported an example incremental PyTorch diagnostic update taking approximately 4.7 ms, versus 386 ms for Pyright and 2.38 seconds for Pyrefly, on the cited Apple M4 setup.

Those figures represent a particular benchmark, code change, tool version, and environment. They should not be generalized into guaranteed application-level speedups.

The architectural explanation is more durable than any particular benchmark: ty reduces unnecessary recomputation and can retain intermediate semantic state within a long-lived process. The performance benefit depends on how much of the dependency graph a change actually affects.

Source: `https://astral.sh/blog/ty`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://astral.sh\&sz=32)

astral.sh



### 3.4 Crucial architectural limitation

Although the internal dependency graph is valuable, ty does not currently document a stable external API for:

- Retrieving its complete semantic dependency graph.
- Subscribing to changed type-query results.
- Exporting a normalized, versioned model of every function, class, or module interface.
- Asking whether a code change is semantically equivalent to the prior implementation.
- Using Salsa queries directly from an ordinary Python integration.

Its incrementality is a native implementation mechanism. A system seeking persistent semantic-interface fingerprints or custom invalidation would still need an appropriate public interface or additional analysis layer.

## 4. Project discovery, module resolution, and environment modeling

Correct type analysis depends on more than the source files themselves. ty must reconstruct the importable Python environment against which a program is intended to run.

### 4.1 First-party and third-party resolution

ty distinguishes between source roots, installed packages, standard-library modules, and stub files.

For first-party imports, it recognizes conventional project layouts, including project-root packages and common `src/` layouts. The `[tool.ty.environment]` configuration permits explicit control over:

- `root`: Directories containing first-party importable modules, in priority order.
- `extra-paths`: Additional module search paths, including unusual or externally supplied source trees.
- `python`: The relevant interpreter or virtual-environment path.
- `typeshed`: An alternative standard-library stub directory.

For third-party packages, ty searches the selected Python environment's `site-packages`. It recognizes information supplied by stub packages and inline typing declarations, rather than requiring every dependency to be dynamically imported.

ty also considers environment-related inputs such as `VIRTUAL_ENV`, Conda/Pixi environments, and `PYTHONPATH`. The exact search order matters when multiple importable modules share a name.

A critical distinction is that source inclusion and import resolution are separate concerns. A directory's eligibility as a first-party import root is not the same as the set of files selected for direct diagnostics.

Sources: `https://docs.astral.sh/ty/modules/` and `https://docs.astral.sh/ty/reference/configuration/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty+1



### 4.2 Python versions and platform targeting

ty can analyze code for a target Python version that differs from the interpreter running the type checker.

The target controls syntax compatibility, standard-library typing information, and recognized version-dependent branches. Platform configuration similarly affects code guarded by conditions involving `sys.platform`.

ty officially supports analyzing code targeting Python 3.10 and later. Targets from Python 3.7 through 3.9 remain selectable, but upstream warns of incomplete standard-library stub coverage for those releases.

The Python package's own installation requirement is a separate matter: the packaged executable can be installed in environments that support Python 3.8 or later.

When no target is explicitly configured, ty can use `project.requires-python`, an identified Python environment, or a fallback. The current configuration reference identifies Python 3.15 as that fallback, although an older conceptual documentation page has described an earlier fallback. Explicit target configuration avoids depending on version-sensitive defaults.

Source: `https://docs.astral.sh/ty/reference/configuration/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 4.3 Module stubs and native extensions

For standard-library typing, ty bundles typeshed information into its executable. A different typeshed directory can be configured explicitly.

For third-party modules, static typing may come from source annotations, `.pyi` files, or separately distributed stubs.

This distinction becomes especially important for compiled extension modules. ty does not derive comprehensive type information from arbitrary C-extension or native binary implementations. A library exposing an extension module without sufficiently descriptive stubs can therefore appear dynamically typed even when its runtime behavior is well-defined.

The quality of an external package's typing declarations is a practical ceiling on cross-package inference accuracy.

### 4.4 File selection and configuration layering

ty supports `pyproject.toml` under `[tool.ty]` as well as a dedicated `ty.toml`.

File selection uses `[tool.ty.src]` with `include`, `exclude`, and `respect-ignore-files`. Patterns use gitignore-style path matching, and ignored files are respected by default. Explicitly passed files can be analyzed even when ordinarily excluded, unless exclusion is forcibly enforced.

Configuration supports directory/project discovery, user-level settings, command-line overrides, and per-file or per-directory override tables. This allows one project to use a shared policy while modifying diagnostic severities or selected analysis options for particular source areas.

For reproducible analysis, it is important to distinguish the effective configuration of the CLI from settings injected by an editor. The latter can take precedence.

Sources: `https://docs.astral.sh/ty/configuration/` and `https://docs.astral.sh/ty/exclusions/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



## 5. Diagnostics and type-contract enforcement

### 5.1 Diagnostic families

ty's diagnostics cover the ordinary typing contract and a substantial set of deeper semantic rules.

| Capability family    | Examples of errors detected                                                   |
| -------------------- | ----------------------------------------------------------------------------- |
| Symbol resolution    | Missing imports, missing names, missing module members                        |
| Function contracts   | Incorrect argument types, missing arguments, overload incompatibilities       |
| Return contracts     | Invalid return values, missing returns, return-type unsoundness               |
| Assignments          | Incompatible assignment, immutable/final member violations                    |
| Attribute access     | Missing attributes and attributes absent from some union members              |
| Generic types        | Invalid specialization, missing or incompatible type parameters               |
| Structural contracts | Protocol incompatibility, ambiguous protocol members                          |
| Inheritance          | Incompatible method overrides, property overrides, abstract-class misuse      |
| Structured records   | Invalid `TypedDict` keys, missing fields, incompatible field values           |
| Control flow         | Potentially unbound names, invalid narrowing, unreachable/invalid operations  |
| Async semantics      | Awaitable values created but not awaited                                      |
| Typing declarations  | Invalid aliases, incompatible declarations, improper use of typing constructs |

This coverage is not solely a restatement of annotation checking. Some diagnostics identify potential runtime mistakes, while others enforce consistency between abstract interfaces and their implementations.

A concrete example is checking mutable attribute overrides. If a subclass narrows a writable attribute from `int` to `bool`, code operating through the superclass interface may still assign a non-boolean integer. ty has a dedicated rule for that substitution-safety problem.

Another example is `missing-override-decorator`, which can enforce explicit use of `@override` for inherited methods. This can expose accidental interface changes during refactoring.

Source: `https://docs.astral.sh/ty/reference/rules/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 5.2 Diagnostic explanations and cross-source context

The default terminal diagnostic format is designed to explain why a type relationship failed.

Depending on the rule, a diagnostic can include the failing expression, the expected type, the inferred type, related source locations, and contextual suggestions.

That additional context is useful in cases where the immediate failing expression is correct syntactically but conflicts with a contract defined elsewhere—for example, an inherited method, overloaded function, or `TypedDict` field.

ty also provides `ty explain rule`, which gives rule-specific documentation. The explanation command supports machine-readable JSON output, even though the primary checking command uses a different set of output formats.

Source: `https://docs.astral.sh/ty/features/diagnostics/` and `https://docs.astral.sh/ty/reference/cli/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty+1



### 5.3 Diagnostic severity is not the same as inference soundness

ty exposes three diagnostic severities: `ignore`, `warn`, and `error`.

These determine whether a particular problem is reported and how seriously it is treated. They do not directly determine how all types are inferred.

This is an important distinction because ty has separate analytical controls for changing inference behavior:

| Option                         | Default   | Effect                                                             |
| ------------------------------ | --------- | ------------------------------------------------------------------ |
| `return-type-inference`        | `"never"` | Controls inference of unannotated function return types            |
| `strict-equality-semantics`    | `false`   | Makes equality-based narrowing more conservative                   |
| `strict-generic-narrowing`     | `false`   | Uses more conservative narrowing for unspecialized generic classes |
| `respect-type-ignore-comments` | `true`    | Controls whether standard typing suppressions affect ty            |
| `allowed-unresolved-imports`   | `[]`      | Suppresses selected missing-import diagnostics                     |
| `replace-imports-with-any`     | `[]`      | Replaces selected imported modules' type information with `Any`    |

The most easily overlooked setting is `return-type-inference`.

ty checks the bodies of unannotated functions by default, but its current default is not to infer their outward return types from those bodies. An unannotated function ordinarily receives `Unknown` as its return type.

Setting `return-type-inference = "always"` enables such inference for ordinary functions and methods. The documentation currently excludes generator and asynchronous functions from this behavior; lambda returns are inferred regardless of this setting.

Thus, checking an unannotated function's implementation and deriving a precise callable contract from that implementation are separate capabilities.

Source: `https://docs.astral.sh/ty/reference/configuration/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 5.4 Preserving typing information versus deliberately discarding it

Two import-related controls may appear similar but have substantially different semantics.

`allowed-unresolved-imports` suppresses missing-import diagnostics for selected module patterns. It does not systematically discard type information for imports that are successfully resolved.

`replace-imports-with-any` is stronger: matching modules are treated as `Any` even if their definitions or stubs are available.

The second option can reduce friction with incompatible third-party typing declarations, but it also eliminates meaningful static guarantees across that boundary.

From an architectural perspective, selectively suppressing a known resolution problem and intentionally treating an entire dependency as dynamically typed are different design decisions.

Source: `https://docs.astral.sh/ty/reference/configuration/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 5.5 Example configuration

The following is an illustrative configuration combining several mechanisms; it is not presented as a universal strictness profile.

```
[tool.ty.environment]
python-version = "3.13"
root = ["./src"]

[tool.ty.analysis]
return-type-inference = "always"
strict-equality-semantics = true
strict-generic-narrowing = true

[tool.ty.rules]
missing-type-argument = "error"
missing-override-decorator = "warn"
possibly-unresolved-reference = "warn"

[tool.ty.src]
include = ["src", "tests"]
exclude = ["tests/fixtures/**"]

[[tool.ty.overrides]]
include = ["tests/**"]

[tool.ty.overrides.rules]
missing-override-decorator = "ignore"
```

The analytical options change what ty can conclude; the rules configure which consequences become diagnostics; and the overrides control the policy for particular files.

These distinctions are useful when comparing configurations, especially because a more conservative inference mode may increase the number of reported incompatibilities without enabling any additional diagnostic rule.

## 6. Suppression, baselines, and incremental adoption

### 6.1 Precise diagnostic suppression

ty supports rule-specific inline comments:

```
result = legacy_call(value)  # ty: ignore[invalid-argument-type]
```

It also supports file-level suppression and standard `# type: ignore` comments, including ty-qualified rule identifiers in comments shared with other type checkers.

Specific rule identifiers are preferable to blanket suppression because they preserve unrelated errors and document the particular exception being accepted.

ty can report unused suppression comments, making it possible to identify exceptions that are no longer necessary after code changes.

For codebases using several checkers, `respect-type-ignore-comments = false` can separate generic typing suppressions from ty-specific policy.

Source: `https://docs.astral.sh/ty/suppression/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 6.2 Diagnostic baselines

An especially valuable newer capability is diagnostic baselining, introduced as a preview feature.

A baseline records existing diagnostics so that they can be distinguished from newly introduced violations.

Relevant interfaces include:

```
ty check --update-baseline --baseline ty-baseline.json
ty check --baseline ty-baseline.json
```

A project can also configure the baseline path in `[tool.ty]`.

This enables a different adoption model from suppressing every existing problem inline. Existing diagnostics can be recorded centrally while additional diagnostics remain actionable.

In the editor, existing baseline diagnostics can continue to appear as hints rather than disappearing entirely. This preserves awareness without making every pre-existing issue block ordinary work.

Limitations: Baselines are a preview capability, and their file format may change between releases. They are diagnostic snapshots, not semantic proofs that existing source behavior remains unchanged.

Source: `https://docs.astral.sh/ty/suppression/` and `https://docs.astral.sh/ty/reference/configuration/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



## 7. Language server and semantic development tooling

The language server is a first-class component of ty, rather than a thin editor wrapper around batch checking.

### 7.1 Navigation and semantic queries

The documented LSP supports:

| Operation                    | Capability                                               |
| ---------------------------- | -------------------------------------------------------- |
| Go to definition             | Locate the implementation or defining source of a symbol |
| Go to declaration            | Locate its declaration, potentially in a stub            |
| Go to type definition        | Navigate to the type of the selected value               |
| Go to implementation         | Find known implementations and overrides                 |
| Find references              | Identify symbol usages across the workspace              |
| Call hierarchy               | Explore incoming and outgoing call relationships         |
| Type hierarchy               | Explore relationships among types                        |
| Document/workspace symbols   | Discover and navigate declared symbols                   |
| Hover/signature help         | Inspect inferred types, signatures, and documentation    |
| Rename                       | Request semantic symbol-renaming edits                   |
| Completion and auto-import   | Suggest members or importable symbols                    |
| Inlay hints                  | Display inferred variable types and argument names       |
| Semantic tokens              | Apply highlighting informed by semantic analysis         |
| Code actions                 | Offer applicable quick fixes                             |
| Folding and selection ranges | Provide syntax-aware editor operations                   |

This functionality is important independently of diagnostics: it allows the same semantic analysis to support code exploration, interface discovery, and certain refactoring actions.

However, ty's rename feature should not be interpreted as a guarantee that all dynamic Python references can be transformed safely. References created through reflection, string-based lookup, or external runtime configuration may not be statically discoverable.

Source: `https://docs.astral.sh/ty/features/language-server/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 7.2 Diagnostics modes and multiple language servers

ty supports both LSP push and pull diagnostics.

The editor's `diagnosticMode` offers three scopes:

- `openFilesOnly` — diagnostics for open files; the documented default.
- `workspace` — diagnostics across the configured workspace.
- `off` — no diagnostics, while other language services can remain available.

Separately, `disableLanguageServices = true` disables features such as completion and navigation while leaving ty usable as a diagnostic provider.

These controls allow ty to coexist with another language server when different tools provide preferred capabilities.

For example, one editor may use ty for type diagnostics and another language server for completions. The reverse arrangement is also possible.

Editor-specific configuration can be applied directly through the LSP settings channel, independently of project TOML files.

Source: `https://docs.astral.sh/ty/reference/editor-settings/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 7.3 Jupyter notebook support

ty supports LSP operations on Jupyter notebooks through the notebook document protocol.

It analyzes cells with awareness of their notebook context, providing diagnostics, completions, and other language services across cells.

The important distinction from ordinary module analysis is that notebook cells form a document context rather than an ordinary importable `.py` module.

Static analysis still cannot reproduce arbitrary execution histories, out-of-order cell execution, or all state left in the running kernel.

Source: `https://docs.astral.sh/ty/features/language-server/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 7.4 LSP extensions and unsupported operations

ty also provides a nonstandard full-diagnostic-output extension. A client advertising the experimental `fullDiagnosticOutput` capability can receive rendered multiline diagnostic information, together with ty's original diagnostic identifier.

The rendering may include ANSI styling. Clients that preserve diagnostic data when requesting code actions can keep those operations working.

This is useful for specialized editor clients but is explicitly a best-effort, nonstandard interface.

The documented feature matrix does not include code lenses, color information, document links, or formatting. Formatting is delegated to Ruff.

There is also a documentation/version discrepancy worth observing: the current feature matrix lists `workspace/willRenameFiles` as unsupported, while a recent release note reports adding that capability. For exact LSP method support, the installed release and its capability negotiation should take precedence over a potentially stale matrix.

Source: `https://docs.astral.sh/ty/features/language-server/` and `https://github.com/astral-sh/ty/releases`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty+1



### 7.5 Editors

Documented integration paths include VS Code, PyCharm, Neovim, Zed, Emacs, and other LSP-compatible editors.

VS Code settings can select an installed ty executable or the extension's bundled version. Completion, inlay-hint, and diagnostic behaviors can be configured separately.

This makes editor-version selection an additional reproducibility concern: a locally installed CLI and a bundled editor executable might otherwise use different ty releases.

Sources: `https://docs.astral.sh/ty/editors/` and `https://docs.astral.sh/ty/reference/editor-settings/`.

## 8. Specialized framework semantics

A conventional static checker can understand a framework only as precisely as its ordinary type annotations and stubs permit.

Some Python frameworks generate important interfaces dynamically. ty addresses selected cases with built-in semantic understanding.

### 8.1 Pydantic v2

ty recognizes Pydantic models and infers constructor signatures and instance attribute types from model-field declarations.

Supported behavior includes:

- Required fields, defaults, and default factories.
- Field aliases and metadata through `Field` and `Annotated`.
- Lax versus strict input conversion.
- Extra-field policies.
- Frozen fields and frozen models.
- Inherited, nested, and generic models.
- `RootModel`, Pydantic dataclasses, and settings models.

For example:

```
from pydantic import BaseModelclass Record(BaseModel):    identifier: int    label: strrecord = Record(identifier="123", label="sample")reveal_type(record.identifier)  # int
```

Pydantic's default lax conversion permits certain inputs that do not already have the declared field type. ty models those accepted constructor inputs while preserving the declared type of the constructed instance attribute.

An important limitation: This is static approximation of Pydantic's runtime behavior, not execution of its validation machinery.

A string may be accepted as a potentially convertible integer even when its actual contents would fail validation. Constraints such as numeric bounds, custom validators, dynamic aliases, and other runtime-dependent transformations cannot all be proven statically.

ty's documentation also distinguishes constructor conversion from field defaults and subsequent attribute assignments, which are checked more strictly against their declared types.

Source: `https://docs.astral.sh/ty/features/third-party/pydantic/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 8.2 Django models

ty has dedicated inference for Django models, conditional on the installation of the `django-types` stub package.

It can infer model field attributes, nullable field types, primary-key aliases, forward foreign-key relationships, generated foreign-key ID attributes, and selected generated model methods.

For instance, given a foreign key to a model whose primary key is a string, ty can infer the associated `<field>_id` attribute as a string.

The documentation includes significant limitations:

- Reverse relationships are not yet inferred comprehensively.
- Constructor keyword validation and ORM query field-name validation remain incomplete.
- String-based relationship declarations and custom behavior can require additional annotations.
- Automatically assigned primary keys and assignment-time conversions may not be modeled identically to runtime behavior.

This is therefore valuable model-aware inference, but not a complete static specification of the Django ORM.

Source: `https://docs.astral.sh/ty/features/third-party/django/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 8.3 pytest fixtures

pytest introduces dependencies through fixture names, rather than explicit ordinary function calls.

ty models this relationship for semantic navigation. It can resolve a test-function parameter to its corresponding fixture and find references from fixture declarations to requesting tests.

Fixture lookup follows pytest-like scopes: test classes, test modules, relevant parent `conftest.py` files, and core pytest fixtures.

This effectively exposes a portion of pytest's implicit dependency graph through standard editor navigation.

Limitations remain for fixtures registered by third-party plugins and certain overridden fixtures whose resolution depends on the requesting test's scope.

Source: `https://docs.astral.sh/ty/features/third-party/pytest/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 8.4 Boundary of framework support

These integrations should not be mistaken for a general mechanism whereby an application can register its own semantic hooks.

ty does not currently offer an equivalent of mypy's general plugin system. Framework-specific behavior is implemented within ty itself.

For other dynamic frameworks, conventional annotations, protocols, stub files, and typing metadata remain the primary interoperability mechanisms.

Source: `https://docs.astral.sh/ty/reference/typing-faq/` and `https://docs.astral.sh/ty/coming-from-mypy-or-pyright/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



## 9. Command-line analysis and machine-readable diagnostics

### 9.1 Principal interfaces

ty's primary commands are:

```
ty check
ty check path/to/package
ty check --watch
ty check --fix

ty server
ty version
ty explain rule invalid-argument-type
```

`ty check` analyzes the selected project or source paths. `--watch` maintains a long-lived checking process that responds to source changes, enabling reuse of incremental state.

`--fix` applies supported fixes for diagnostics where a fix is available. It is not a general Python rewrite or automatic type-annotation generator.

The CLI also supports `--add-ignore`, which inserts suppression comments. That is an adoption-oriented operation, not a semantic repair.

### 9.2 Output formats

ty has multiple diagnostic output formats:

| Format    | Typical purpose                        |
| --------- | -------------------------------------- |
| `full`    | Detailed developer diagnostics         |
| `concise` | Compact, one-line diagnostic records   |
| `github`  | GitHub Actions annotations             |
| `gitlab`  | GitLab Code Quality JSON               |
| `junit`   | XML reports for test and CI systems    |
| `sarif`   | Standardized static-analysis reporting |

These outputs provide useful integration points for code-review systems, build pipelines, and diagnostic aggregation.

The distinction between them matters: `ty check` does not document an arbitrary general-purpose JSON semantic output format. GitLab JSON and SARIF describe diagnostics, not a complete exported program model.

Source: `https://docs.astral.sh/ty/reference/cli/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 9.3 Process exit status and operational controls

The documented exit codes distinguish a successful check, reported diagnostics, configuration/operational errors, and internal failures.

By default, warning-level as well as error-level diagnostics can produce a failing process status. `--exit-zero-on-warning` allows warnings without making them block the command, while `--exit-zero` suppresses diagnostic failure status more broadly.

ty exposes operational settings through environment variables, including:

- `TY_CONFIG_FILE` for explicit configuration selection.
- `TY_OUTPUT_FORMAT` for terminal reporting.
- `TY_LOG` for logging and tracing configuration.
- `TY_LOG_PROFILE` for profiling output.
- `TY_MAX_PARALLELISM` for controlling permitted parallel analysis tasks.
- `TY_UV` for enabling optional integration with uv.

`TY_MAX_PARALLELISM` controls the analysis task limit, rather than serving as a direct promise of a fixed operating-system thread count.

Sources: `https://docs.astral.sh/ty/reference/environment/` and `https://docs.astral.sh/ty/reference/exit-codes/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



## 10. uv integration: a significant newer capability

The October 2026 uv–ty integration is particularly important because it goes beyond using uv merely to install or launch ty.

It lets ty incorporate structured dependency and workspace information produced by uv into static analysis.

This integration is experimental, introduced for uv 0.12.3 or later and ty 0.0.76 or later.

Source: `https://astral.sh/blog/uv-ty-integration`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://astral.sh\&sz=32)

astral.sh



### 10.1 Unified project checking

The `uv check` command prepares the relevant project environment and invokes ty.

It supports checking individual packages, entire workspaces, and standalone scripts. In particular:

```
uv check
uv check --all-packages
uv check --package example-package
uv check --script example.py
```

The command can use the ty version recorded in the project's lockfile, aligning dependency resolution and type-checker selection.

The feature remains part of uv's preview functionality. As of the research date, `uv check` invokes ty for type checking; extending the unified command to Ruff linting was described as future work, not an existing capability.

Sources: `https://docs.astral.sh/uv/reference/cli/` and `https://docs.astral.sh/uv/concepts/preview/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

uv+1



### 10.2 Independent environments for PEP 723 scripts

PEP 723 allows standalone Python scripts to declare their own dependencies and Python-version requirements.

With uv integration enabled, ty can use this inline metadata to analyze each script against its own environment rather than assuming that all scripts share the enclosing project's dependencies.

For CLI usage:

```
TY_UV=scripts ty check
```

For broader uv workspace discovery:

```
TY_UV=1 ty check
```

The editor has corresponding experimental `useUv` settings.

This capability is particularly meaningful for collections of independent scripts with different dependencies or Python targets. Without environment separation, analyzing them against one shared environment can yield incorrect import and type assumptions.

A security and reproducibility consideration is that preparing environments may install packages and run third-party installation code. Accordingly, automatic editor-side environment preparation is opt-in and disabled for untrusted workspaces.

Source: `https://astral.sh/blog/uv-ty-integration` and `https://docs.astral.sh/ty/reference/editor-settings/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://astral.sh\&sz=32)

astral.sh+1



### 10.3 Dependency-declaration verification

A less obvious feature is ty's `missing-direct-dependency` diagnostic rule.

This rule connects two information sources:

1. ty's semantic understanding of imported modules.
2. uv's knowledge of installed distributions, package ownership, and declared dependencies.

It can identify imports from packages that are available only because they happen to be transitive dependencies, rather than being declared directly by the importing project.

For example, a project might declare `requests` but import `urllib3` directly. If `urllib3` is installed only transitively through `requests`, this rule can report the missing direct dependency.

The mapping is not based simply on matching an import string to a distribution name: Python package names and importable module names can differ, as with `Pillow` and `PIL`.

This rule is:

- Available in released ty versions.
- Classified as preview functionality.
- Disabled by default.
- Dependent on the optional uv integration and its package-ownership information.

A possible configuration is:

```
[tool.ty.rules]
missing-direct-dependency = "warn"
```

It does not guarantee complete detection. Imports guarded by `TYPE_CHECKING`, ambiguous namespace-package ownership, and cases where a distribution cannot be uniquely identified are documented limitations.

The architectural significance is substantial: the checker can validate relationships between a program's observed imports and its declared packaging contract, rather than treating environment configuration solely as an input for resolving names.

Sources: `https://docs.astral.sh/ty/reference/rules/` and `https://docs.astral.sh/uv/reference/internals/metadata/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty+1



## 11. Relationship to Ruff, uv, mypy, and Pyright

ty occupies a specific portion of the Python tooling ecosystem. Its value is clearest when adjacent responsibilities are kept distinct.

| Tool    | Primary responsibility                                            | Relationship to ty                                                           |
| ------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| ty      | Static semantic type analysis and LSP functionality               | Central subject                                                              |
| Ruff    | Linting, style enforcement, formatting                            | Complementary; can enforce annotation conventions absent from ty             |
| uv      | Package resolution, environment management, lockfiles, workspaces | Supplies environments and, experimentally, structured dependency information |
| mypy    | Python type checking, with an established plugin ecosystem        | Alternative checker with different inference and extensibility behavior      |
| Pyright | Python static type checking and semantic analysis                 | Alternative checker with its own type-system behavior and configuration      |
| Pylance | VS Code language-service experience based on Pyright              | Alternative or complementary editor provider                                 |

### 11.1 ty and Ruff

ty's type diagnostics and Ruff's lint rules address different problems.

For example, ty checks the body of an unannotated function, but does not generally require explicit type annotations. Ruff's `ANN` rules can enforce annotation presence.

Similarly, ty does not provide code formatting, while Ruff does.

The official documentation recommends combining selected ty rules with Ruff's `ANN` and `PYI` categories for projects seeking stronger annotation policies.

Source: `https://docs.astral.sh/ty/coming-from-mypy-or-pyright/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 11.2 ty and mypy

The most consequential distinctions include:

- ty checks unannotated function bodies by default.
- ty uses different inference and narrowing semantics, including its intersection-type representation.
- ty does not implement mypy's user plugin system.
- Equivalent diagnostic policies do not necessarily produce equivalent inferred types.
- ty's rules have different identifiers and defaults.

Consequently, copying a mypy configuration into ty conceptually is not enough to guarantee identical checking behavior.

### 11.3 ty and Pyright

Both provide modern Python type checking and semantic analysis, but their inference behavior, diagnostic taxonomy, editor capabilities, and configuration mechanisms are not identical.

ty emphasizes Salsa-based fine-grained incremental computation and its particular gradual-typing model.

Choosing between the two cannot be reduced solely to speed. Exact handling of generics, overloaded definitions, dynamic frameworks, and editor integrations can materially affect their usefulness in a given problem domain.

### 11.4 Type stubs as the shared interoperability layer

The most portable route for supplying types to several checkers remains ordinary Python typing declarations and PEP 561-compatible stub packages.

Framework-specific ty behavior and checker-specific constructs such as `ty_extensions.Intersection` can provide additional precision, but that precision is not automatically portable.

For broadly distributed Python libraries, standard typing declarations remain the more general interoperability mechanism.

## 12. Important limitations and unresolved boundaries

| Limitation                                        | Consequence                                                                                                  |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Beta release, no stable 1.0 contract              | Diagnostics, rule identifiers, inference details, and some interfaces may change between releases            |
| Incomplete typing-spec edge cases                 | Exact support for advanced or recently introduced typing features needs version-specific verification        |
| No documented public semantic query API           | Internal types and dependency relationships cannot be assumed externally reusable                            |
| No mypy-style plugin API                          | Custom framework semantics generally require upstream implementation or conventional stubs                   |
| Unannotated return inference disabled by default  | Cross-function information may remain `Unknown` despite checking the function body                           |
| Dynamic Python behavior                           | Reflection, runtime code generation, dynamic attributes, and import side effects cannot always be modeled    |
| Native modules without useful typing declarations | Static type information may be absent even when functionality exists at runtime                              |
| Limited monorepo/project configurations           | Complex package layouts can require explicit roots or uv workspace integration                               |
| Framework-specific inference gaps                 | Pydantic, Django, and pytest support is valuable but intentionally incomplete                                |
| No general semantic model export                  | SARIF, GitLab, and LSP outputs are not substitutes for a complete type-annotated intermediate representation |
| Experimental integrations                         | uv-driven environment setup, dependency checks, and diagnostic baselines may evolve                          |
| No runtime guarantees                             | Passing a static check does not prove correct execution or absence of runtime errors                         |

Two distinctions deserve particular emphasis.

First, static type equivalence is not behavioral equivalence. Even a complete model of a function's inferred signature and return type would not prove that a source-code change preserves side effects, output values, exception behavior, or resource usage.

Second, incremental analysis is not the same as externally controllable invalidation. ty may reuse computations internally without exposing the dependency identities and invalidation decisions needed by an independent application.

Sources: `https://docs.astral.sh/ty/reference/typing-faq/`, `https://github.com/astral-sh/ty`, and `https://github.com/astral-sh/ty/issues/1889`.

## 13. Architectural implications of combining capabilities

Several combinations are more consequential than their individual feature descriptions suggest.

### Type-aware development feedback without full-project reanalysis

Semantic queries, dependency tracking, LSP diagnostics, and watch mode combine to support low-latency checking while code is edited.

This is particularly valuable when a program has many imported dependencies but a change affects only a small portion of the actual semantic dependency graph.

The result is an opportunity to avoid separate batch analysis for every editor request.

### Gradual typing with progressive contract precision

ty's `Unknown` model, support for partially typed code, intersection-based narrowing, and selective severity configuration allow type information to be developed without requiring complete annotations upfront.

More precise annotations and standard stubs can then strengthen the same analysis.

This is not equivalent to turning on a single strict mode: the improvement comes from how declared contracts, inference behavior, and diagnostic policy interact.

### Static verification of dynamically generated framework interfaces

Pydantic and Django inference demonstrate how a checker can recover some of the contracts that a framework would otherwise generate at runtime.

Where supported, this can replace substantial manual stub maintenance or duplicated constructor declarations.

However, the benefit is bounded by the framework features that ty actually models.

### Dependency-aware project validation

The experimental uv integration makes a broader form of static validation possible.

Type analysis can use not only source code and stubs, but also workspace dependency metadata. The `missing-direct-dependency` rule is a concrete example: it checks an architectural property of package declarations that ordinary type compatibility alone cannot establish.

This creates a pathway toward richer relationships between dependency management and semantic analysis, although more extensive dependency diagnostics remain subject to the capabilities of released versions.

### Shared semantics across checking and code exploration

Because ty's CLI checker and language server share underlying analysis machinery, a single engine can support both correctness checks and semantic navigation.

That can simplify development tooling relative to maintaining separate symbol-resolution and type-inference implementations.

The opportunity is strongest when standard LSP operations are sufficient. Tooling requiring arbitrary access to internal type graphs still encounters a public-interface boundary.

## 14. Primary documentation and source map

The following are the most useful direct sources for investigating particular capabilities.

| Area                                | Primary source                                                                             |
| ----------------------------------- | ------------------------------------------------------------------------------------------ |
| Current release and changes         | `https://github.com/astral-sh/ty/releases`                                                 |
| Type-system design                  | `https://docs.astral.sh/ty/features/type-system/`                                          |
| Typing implementation tracker       | `https://github.com/astral-sh/ty/issues/1889`                                              |
| Inference and gradual-typing FAQ    | `https://docs.astral.sh/ty/reference/typing-faq/`                                          |
| Complete diagnostics rule reference | `https://docs.astral.sh/ty/reference/rules/`                                               |
| Configuration schema                | `https://docs.astral.sh/ty/reference/configuration/`                                       |
| Module resolution                   | `https://docs.astral.sh/ty/modules/`                                                       |
| Suppression and baselines           | `https://docs.astral.sh/ty/suppression/`                                                   |
| Language-server capabilities        | `https://docs.astral.sh/ty/features/language-server/`                                      |
| Editor settings                     | `https://docs.astral.sh/ty/reference/editor-settings/`                                     |
| CLI reference                       | `https://docs.astral.sh/ty/reference/cli/`                                                 |
| Environment variables               | `https://docs.astral.sh/ty/reference/environment/`                                         |
| Pydantic inference                  | `https://docs.astral.sh/ty/features/third-party/pydantic/`                                 |
| Django inference                    | `https://docs.astral.sh/ty/features/third-party/django/`                                   |
| pytest integration                  | `https://docs.astral.sh/ty/features/third-party/pytest/`                                   |
| uv–ty integration                   | `https://astral.sh/blog/uv-ty-integration`                                                 |
| uv workspace metadata               | `https://docs.astral.sh/uv/reference/internals/metadata/`                                  |
| Upstream type-inference source      | `https://github.com/astral-sh/ruff/blob/main/crates/ty_python_semantic/src/types/infer.rs` |

## Overall assessment

ty is already much more than a fast replacement for a batch Python type checker. Its most important capabilities are the combination of advanced gradual type inference, definition-level incremental computation, semantic language services, framework-aware inference, and emerging integration with package dependency metadata.

The recent uv integration is particularly notable because it demonstrates an expansion from checking type compatibility within source code to validating relationships between source imports and declared package dependencies.

Its most consequential remaining boundary is external extensibility. ty possesses a sophisticated internal semantic engine, but that engine is not currently exposed as a stable, general-purpose API for querying, persisting, comparing, or independently invalidating rich program models.

For type checking and editor semantics, ty therefore offers a substantial native capability set. For applications requiring an independently reusable semantic knowledge model, its internal architecture is informative, but its existing public interfaces do not eliminate the need for a separate representation or integration layer.

This assessment reflects the documented behavior of ty 0.0.101 as of November 12, 2026, with experimental and development-only functionality distinguished from established features throughout.

# ty (Python) — Advanced Capabilities Addendum

Research date: November 12, 2026 | Target: ty 0.0.101 | Status: Public beta

This addendum extends the original ty reference with capabilities that were omitted or insufficiently explained, focusing on advanced type representations, static assertions, soundness enforcement, generated Python interfaces, specialized diagnostics, and module semantics.

It also clarifies several version-sensitive limitations. All capabilities discussed here are available in the targeted release unless explicitly marked experimental, incomplete, or implementation-specific.

## 1. Checker-specific type representations and assertions

### 1.1 Explicit intersection and negation types

Beyond its automatic use of intersection types during narrowing, ty supports two experimental type-expression operators:

| Syntax  | Meaning                                   |
| ------- | ----------------------------------------- |
| `A & B` | Values satisfying both type constraints   |
| `~A`    | Values outside the set represented by `A` |

Consider these illustrative annotations:

```
from __future__ import annotationsclass Serializable:    def serialize(self) -> bytes: ...class Versioned:    version: intdef process(value: Serializable & Versioned) -> bytes:    return value.serialize()def handle_other(value: ~Versioned) -> None:    ...
```

The first annotation expresses a structural conjunction. A caller must supply a value that satisfies both interfaces, even though the interfaces do not need a common declared subclass.

The second expresses an exclusion constraint. It can represent information that normally arises internally during negative type narrowing.

This is significant because Python's standardized typing system has unions but does not provide general-purpose intersection or complement annotations.

Experimental boundary: These operators are accepted by ty's type-expression machinery but are not standardized typing syntax. The `experimental-syntax` rule warns by default, and other type checkers may reject them.

Using postponed annotations avoids ordinary eager runtime evaluation of these expressions on older Python versions, but it does not make them safe for frameworks that subsequently evaluate annotations with `typing.get_type_hints()` or comparable runtime mechanisms.

A more explicit checker-specific alternative is `ty_extensions.Intersection`. That module is currently a type-checking-time facility and should not be confused with a general runtime typing library.

The primary architectural benefit is expressiveness: conjunction and exclusion constraints can describe relationships that otherwise require synthetic protocols, additional inheritance, or less precise annotations. The cost is reduced portability.

Sources: `https://docs.astral.sh/ty/reference/rules/#experimental-syntax` and `https://docs.astral.sh/ty/features/type-system/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty+1



### 1.2 Exact numeric types and the Python numeric tower

ty provides a more precise representation of `float` and `complex` than the standard annotation names alone suggest.

Python's typing specification permits an `int` where `float` is expected, despite the absence of a subclass relationship. Similarly, annotations using `complex` accept integer and floating-point values.

ty distinguishes the broader annotation contract from a value known to be an actual instance of the corresponding numeric type.

| Type representation | Interpretation                                                                  |
| ------------------- | ------------------------------------------------------------------------------- |
| `float`             | Accepts ordinary floating-point values and integers under numeric promotion     |
| `float*`            | Represents an actual floating-point value, excluding the integer-promotion case |
| `complex`           | Accepts complex, floating-point, and integer values                             |
| `complex*`          | Represents an actual complex value                                              |
| `JustFloat`         | Checker-specific annotation for the narrower actual-float type                  |
| `JustComplex`       | Checker-specific annotation for the narrower actual-complex type                |

The starred forms are displayed in inferred types; they are not valid user-written annotations.

For the narrower contract, ty provides `JustFloat` and `JustComplex` through `ty_extensions`:

```
from typing import TYPE_CHECKINGif TYPE_CHECKING:    from ty_extensions import JustFloatelse:    JustFloat = floatdef require_float(value: JustFloat) -> None:    ...require_float(1.5)  # Accepted by tyrequire_float(1)    # invalid-argument-type
```

This distinction is useful when a type contract needs to specify the actual numeric representation rather than accept implicit numeric promotion.

It also illustrates an important feature of ty's type system: an inferred type can contain distinctions that cannot be expressed directly using standard Python annotation syntax.

`JustFloat` and `JustComplex` are compile-time constraints; they do not introduce automatic runtime validation.

Source: `https://docs.astral.sh/ty/reference/typing-faq/#why-does-ty-show-float-or-complex`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 1.3 Static assertions: `ty_extensions.static_assert`

ty supports a checker-specific assertion mechanism through `ty_extensions.static_assert`.

A static assertion requires an expression to have truthiness that ty can establish as true during analysis.

```
from ty_extensions import static_assertstatic_assert(True)   # Acceptedstatic_assert(False)  # static-assert-error
```

A critical distinction from runtime `assert` is that a condition is not accepted merely because it happens to evaluate to true when the program runs.

For example, ty documents that this assertion fails:

```
static_assert(int(2.0 * 3.0) == 6)
```

Although the expression would evaluate to true in ordinary Python execution, ty does not establish its truthiness statically.

This produces three relevant outcomes:

| Static evaluation                     | Result                |
| ------------------------------------- | --------------------- |
| Provably truthy                       | Assertion accepted    |
| Provably falsy                        | `static-assert-error` |
| Truthiness not statically established | `static-assert-error` |

The associated diagnostic is enabled by default.

The mechanism complements standard typing assertions:

- `reveal_type()` exposes an inferred type for inspection.
- `assert_type()` checks an inferred type against an expected type.
- `assert_never()` verifies that a value has been eliminated from reachable type states.
- `static_assert()` checks a proposition whose truth value ty can determine.

`static_assert` is therefore useful for expressing some compile-time invariants and for constructing tests of static-analysis behavior.

Its capabilities should not be confused with general symbolic computation, theorem proving, or runtime assertion execution. The result depends on ty's supported static semantics.

As a checker-specific extension, `ty_extensions` also requires attention to runtime importability. An unguarded example intended solely for ty checking is not automatically a runnable Python module.

Source: `https://docs.astral.sh/ty/reference/rules/#static-assert-error`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 1.4 Inferring types that are more precise than annotations

ty has a diagnostic specifically addressing situations where the inferred type is more precise than can be represented using standard annotations.

The rule `assert-type-unspellable-subtype` distinguishes these cases from ordinary `assert_type()` failures.

For example, consider a variable of type `int` that has passed a truthiness check:

```
from typing import assert_typedef process(value: int) -> None:    if value:        assert_type(value, int)
```

Inside the branch, ty can represent the refined type as approximately:

`int & ~AlwaysFalsy`

This is more precise than `int`, since the zero value has been excluded.

Consequently, an exact-type assertion against `int` may produce `assert-type-unspellable-subtype`, rather than a standard type-assertion failure.

The distinction matters when using ty to test inference precision. It separates genuine type incompatibility from the case where the inferred type is strictly narrower than the type expressible in portable Python annotations.

Source: `https://docs.astral.sh/ty/reference/rules/#assert-type-unspellable-subtype`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



## 2. Stronger soundness guarantees at dynamic-type boundaries

Python's gradual typing deliberately permits values whose type is `Any` or `Unknown` to pass through many statically typed interfaces.

This makes partially typed programs practical, but it also means an annotation does not necessarily establish that every value flowing through an interface is statically known to satisfy its declared type.

ty provides three optional rules that strengthen this boundary.

### 2.1 Assignability versus subtyping

Ordinary type checking primarily tests assignability.

For example:

```
from typing import Anydef load_value() -> Any:    return "unexpected"value: int = load_value()
```

This is permitted under ordinary gradual typing because `Any` is assignable to `int`.

However, assignability is weaker than subtyping. `Any` does not establish that the actual value is a subtype of `int`.

ty's optional soundness diagnostics use subtype compatibility at selected interfaces.

| Rule                       | Checked boundary                                                 | Default  |
| -------------------------- | ---------------------------------------------------------------- | -------- |
| `unsound-assignment`       | Assignment to a variable with a fully static declared type       | `ignore` |
| `unsound-return-statement` | Return from a function with a fully static return type           | `ignore` |
| `unsound-yield`            | `yield` or `yield from` with a fully static generator yield type | `ignore` |

For example:

```
from typing import Anydef load_value() -> Any:    return "unexpected"def calculate() -> int:    return load_value()  # unsound-return-statement
```

With `unsound-return-statement` enabled, ty reports the return because `Any` does not establish the required subtype relationship.

The same principle applies to variable assignments and generator outputs.

### 2.2 Fully static contracts are necessary

These diagnostics apply only when the destination contract is fully static.

A function annotated `-> int` can be checked against dynamic-value leakage. A function annotated `-> list[Any]` deliberately includes a dynamic component, so it does not establish an entirely static return boundary.

Likewise, a bare `list` annotation implicitly contains an unknown element type.

This means that the soundness checks interact with annotation completeness:

```
[tool.ty.rules]
missing-type-argument = "error"
unsound-assignment = "error"
unsound-return-statement = "error"
unsound-yield = "error"
```

`missing-type-argument` helps identify incomplete generic contracts, while the three soundness rules strengthen transfers into contracts that are already fully static.

For functions, Ruff's `ANN` rules can complement these checks by requiring return annotations where appropriate.

A significant benefit of this combination is that dynamic typing remains available where explicitly intended, rather than being silently accepted at every typed boundary.

### 2.3 Narrowing can establish the missing proof

An `Any` value can be narrowed before crossing a strict boundary:

```
from typing import Anydef load_value() -> Any:    return 42raw = load_value()assert isinstance(raw, int)value: int = raw  # Accepted with unsound-assignment enabled
```

After the runtime type check, ty can infer an intersection such as `Any & int`, which satisfies the static destination contract.

This connects ty's intersection-based type system with its opt-in soundness diagnostics: dynamic information can be refined into a type acceptable at a stricter interface.

Limitations: These rules do not make all Python typing sound. In particular, `unsound-assignment` checks variable assignments rather than every attribute or subscript assignment; the return and yield rules apply only to their relevant function contracts. The assignment rule also has no effect in stub files.

Sources:

`https://docs.astral.sh/ty/reference/rules/#unsound-assignment`

`https://docs.astral.sh/ty/reference/rules/#unsound-return-statement`

`https://docs.astral.sh/ty/reference/rules/#unsound-yield`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty+1



## 3. Advanced control-flow, reachability, and type-disjointness reasoning

### 3.1 Reachability based on inferred semantic facts

ty's reachability analysis is not limited to recognizing syntactic checks such as `sys.version_info` or `sys.platform`.

Instead, it can use statically inferred properties of expressions to determine whether control-flow branches are reachable.

A consequential example is version-dependent third-party library code:

```
import pydanticfrom pydantic import BaseModelPYDANTIC_V2 = pydantic.__version__.startswith("2.")class Person(BaseModel):    name: strdef serialize(person: Person) -> str:    if PYDANTIC_V2:        return person.model_dump_json()    else:        return person.json()
```

Astral documents that ty can evaluate this version condition at type-checking time. With a recognized Pydantic version installed, it can eliminate the branch that does not apply to that version.

This can permit a single source file to contain multiple version-specific implementations without producing false diagnostics for interfaces that are intentionally unavailable in the selected environment.

The architectural implication is that dependency metadata and inferred expression types participate in determining which program paths are analyzed as reachable.

This is more general than a checker hardcoding a few standard-library version checks. It is not, however, arbitrary execution of Python code or comprehensive evaluation of all possible constants.

A change in the resolved dependency environment can therefore alter not only import resolution but also which source paths ty considers reachable.

Source: `https://docs.astral.sh/ty/features/type-system/#reachability-based-on-types`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 3.2 PEP 800: disjoint bases

PEP 800 introduces `@disjoint_base` to describe class relationships that cannot coexist at runtime.

Two unrelated classes are ordinarily not assumed to have an empty intersection: Python can often create a subclass inheriting from both.

For example:

```
class A:    passclass B:    passclass AB(A, B):    pass
```

A value may therefore be both `A` and `B`, even though the original classes are unrelated.

But this is not always possible. Some built-in and extension types impose incompatible instance-memory layouts, making multiple inheritance impossible.

PEP 800 provides metadata that allows type checkers to distinguish these cases.

The decorator is particularly useful for:

- Negative type narrowing: Eliminating an incompatible class when an `isinstance` condition establishes another.
- Intersection reduction: Recognizing that certain type intersections cannot contain any values.
- Exhaustiveness and reachability: Determining whether a branch can be entered.
- Overload analysis: Establishing when apparently overlapping parameter types cannot actually share a runtime value.
- Class validation: Identifying invalid multiple-inheritance relationships before runtime.

The distinction from `@final` is important.

`@final` prevents valid subclassing of a particular class. `@disjoint_base` does not prevent all subclassing; it constrains the combinations of base classes from which another class may inherit.

PEP 800 is finalized, targets Python 3.15, and is tracked as supported by ty. Its principal intended use is in stubs for built-in and extension-module types.

For example, two classes defining incompatible nonempty `__slots__` layouts can be mutually disjoint even though neither class is final.

The relevant metadata allows type-system reasoning to reflect Python runtime constraints rather than treating every theoretically conceivable multiple-inheritance relationship as valid.

Limitation: This does not establish arbitrary disjointness between unrelated structural protocols. It expresses specific class-inheritance and instance-layout constraints. Moreover, the Python typing specification does not prescribe all the advanced inferences a checker must perform using the resulting information.

Sources: `https://peps.python.org/pep-0800/` and `https://github.com/astral-sh/ty/issues/1889`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://peps.python.org\&sz=32)

peps.python.org+2



### 3.3 Redundant-condition diagnostics

ty provides two distinct levels of redundant-condition analysis.

| Diagnostic                   | Default  | Behavior                                                                                                            |
| ---------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------- |
| `redundant-condition`        | `warn`   | Checks selected conditions whose truthiness is statically fixed, with exclusions designed to reduce false positives |
| `redundant-condition-strict` | `ignore` | Extends detection to cases involving literal truth values, short-circuiting, and assignment expressions             |

The enabled-by-default rule is deliberately selective.

For example:

```
from collections.abc import Callabledef execute_when_ready(    is_ready: Callable[[], bool],) -> None:    if is_ready:        print("Ready")
```

A function object is being tested rather than called. This is almost certainly not the intended behavior.

ty can identify this kind of error through its truthiness reasoning.

The stricter rule reaches cases where a program's semantics guarantee a condition will always succeed or fail, even if that conclusion is less directly represented in the expression's nominal type.

It also examines circumstances involving short-circuit evaluation and assignment expressions.

This distinction matters because redundant conditions can be intentional. Python uses boolean expressions for side effects, defensive assertions, compatibility guards, and compact value-selection idioms.

The stricter rule consequently has greater false-positive potential.

The two levels give a developer control over how aggressively type-derived reachability conclusions should become diagnostics.

Source: `https://docs.astral.sh/ty/reference/rules/#redundant-condition` and `https://docs.astral.sh/ty/reference/rules/#redundant-condition-strict`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 3.4 Exhaustiveness, narrowing, and important incompleteness

ty supports flow-sensitive reasoning across `if`/`elif`, `match`, assertions, terminal statements, and enum members.

One example is the combination of enum-member literal types and `assert_never()`:

```
from enum import Enumfrom typing import assert_neverclass State(Enum):    NEW = "new"    RUNNING = "running"    COMPLETE = "complete"def label(state: State) -> str:    match state:        case State.NEW:            return "Not started"        case State.RUNNING:            return "In progress"        case State.COMPLETE:            return "Finished"    assert_never(state)
```

When all possibilities are eliminated, the final assertion is accepted. Adding a new enum member without handling it can cause the assertion to fail under sufficiently precise narrowing.

This is a way to express an exhaustiveness obligation explicitly, rather than assuming a missing branch will always be diagnosed automatically.

The upstream tracker still identifies additional work on advanced match-pattern inference, tuple-pattern narrowing, control flow through `finally`, and a general opt-in rule for non-exhaustive `match` statements.

Therefore, support for exhaustiveness reasoning should not be equated with comprehensive automatic exhaustiveness diagnostics for every pattern-matching construct.

Source: `https://github.com/astral-sh/ty/issues/1889` (Type narrowing and Control flow analysis).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



## 4. Generated interfaces and Python object-model semantics

One of ty's consequential capability families is its ability to model interfaces produced by Python's class-creation machinery rather than by ordinary explicitly written methods.

The type checker can synthesize or infer aspects of constructors, descriptors, inheritance relationships, structured records, and other dynamically generated interfaces.

### 4.1 Dataclass contract synthesis

For standard `dataclasses`, ty understands the relationship between field declarations and generated instance behavior.

This includes modeling:

- Generated `__init__` signatures.
- Required versus defaulted fields.
- `default` and `default_factory`.
- Keyword-only parameters, including `KW_ONLY`.
- Fields excluded from initialization.
- `InitVar` and `ClassVar`.
- Frozen dataclasses and assignment restrictions.
- Generic dataclasses and inheritance.
- Constructor argument types.
- Selected dataclass configuration incompatibilities.

For example:

```
from dataclasses import dataclass, field@dataclass(kw_only=True)class Job:    identifier: str    priority: int = 0    labels: list[str] = field(default_factory=list)job = Job(identifier="job-1", priority=2)
```

ty can derive the effective constructor interface without the user defining `Job.__init__` manually.

It can also enforce properties of that generated interface. A missing required field or incorrectly typed constructor argument can be diagnosed, and assigning to a frozen dataclass field can be rejected.

This is a different problem from ordinary inference of a handwritten method: it requires understanding the semantics of a decorator that transforms the class.

Current limitations: The upstream tracker identifies incomplete validation around `__post_init__`, certain ordering and inheritance cases, `dataclasses.replace()`, and some `slots=True` interactions. It also does not establish full support for every dynamic dataclass construction function.

In particular, the type checker should not be assumed to prove post-initialization invariants established by arbitrary custom code in `__post_init__`.

Sources: `https://github.com/astral-sh/ty/issues/1889` (Dataclasses) and `https://docs.astral.sh/ty/reference/rules/#invalid-dataclass`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 4.2 PEP 681 `dataclass_transform`: standardized extensibility

`dataclass_transform` is one of the most valuable previously omitted features.

PEP 681 permits a library to declare that a decorator, base class, or metaclass supplies dataclass-like behavior.

Rather than requiring a type checker to recognize a specific third-party framework through a custom plugin, the library communicates its behavior through standardized typing metadata.

For example, a hypothetical framework might declare:

```
from typing import dataclass_transform@dataclass_transform()class ModelBase:    ...class Product(ModelBase):    identifier: int    description: str    quantity: int = 1
```

Given an appropriate implementation of the framework, ty can use the transformation metadata to synthesize a constructor corresponding to those fields.

In this illustrative example, `ModelBase` itself does not generate a runtime constructor. The actual framework must implement the behavior that the typing metadata promises.

The metadata can describe:

| Feature                    | Meaning                                                       |
| -------------------------- | ------------------------------------------------------------- |
| Decorator-based transforms | A function transforms a class into a dataclass-like type      |
| Base-class transforms      | Subclasses acquire generated-field semantics                  |
| Metaclass transforms       | A metaclass supplies dataclass-like behavior                  |
| `eq_default`               | Default equality-generation policy                            |
| `order_default`            | Default ordering policy                                       |
| `kw_only_default`          | Default keyword-only constructor behavior                     |
| `frozen_default`           | Default frozen-instance policy                                |
| `field_specifiers`         | Which functions or classes describe fields and their defaults |

Field specifiers can communicate information about aliases, defaults, default factories, keyword-only behavior, and inclusion in constructors.

The practical result is that frameworks can expose generated constructors and other field contracts through a common typing interface.

This matters because it provides a form of declarative semantic extensibility without requiring ty to expose a custom plugin API.

It is more portable than checker-specific inference: `dataclass_transform` is part of the Python typing specification and is understood by other type checkers.

However, it is not an arbitrary metaprogramming specification. It models dataclass-like behavior, not every possible method, property, or relationship a framework may generate.

ty also has incomplete support for certain interactions, including aspects of converter metadata, metaclass-based frozen defaults, nested transforms, and custom dataclass implementations.

Source: `https://github.com/astral-sh/ty/issues/1889` (dataclass_transform) and `https://typing.python.org/en/latest/spec/dataclasses.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 4.3 `NamedTuple` as a generated record type

ty understands the class-based `NamedTuple` declaration form, including generated fields and methods.

These records have multiple overlapping identities:

- They are nominally named record types.
- Their fields have declared names and types.
- Their values are tuple-like and support positional operations.
- Their fields are read-only.
- They expose generated members such as `_fields`, `_asdict()`, `_make()`, and `_replace()`.

The type checker can reason about these generated members and reject invalid declarations, including prohibited field names, unsupported multiple inheritance, and incompatible member overrides.

This provides a richer model than merely treating a `NamedTuple` as a tuple with named attributes.

The functional constructor form, `NamedTuple("Name", [...])`, has separate outstanding support work, so the two declaration mechanisms should not be treated as interchangeable in every advanced case.

Source: `https://github.com/astral-sh/ty/issues/1889` (NamedTuple) and `https://docs.astral.sh/ty/reference/rules/#invalid-named-tuple`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 4.4 `TypedDict` as a structural mapping contract

ty's `TypedDict` support spans several mechanisms that are especially useful for declarative data structures.

These include:

- Required and optional keys.
- `total=False`, `Required`, and `NotRequired`.
- Read-only keys through `ReadOnly`.
- Generic and recursive `TypedDict` declarations.
- Structural assignability between compatible mappings.
- Constructor validation and literal-key access.
- Selected mapping operations such as `get`, `pop`, and `setdefault`.

For example:

```
from typing import Literal, NotRequired, TypedDictclass Result(TypedDict):    identifier: str    status: Literal["ok", "error"]    message: NotRequired[str]
```

The resulting type describes more than the value types of an arbitrary dictionary. It specifies a set of expected fields, which fields must exist, and which values are permitted.

This enables static checking of structured data passed through functions or used to initialize typed objects.

There is an important limit: `TypedDict` is not a runtime schema validator. It does not automatically inspect JSON or arbitrary dictionaries at execution time.

PEP 728 features such as `closed` and `extra_items`, functional `TypedDict` syntax, and certain inheritance and unpacking behaviors remain tracked separately. Their status should not be inferred from support for ordinary class-based `TypedDict` declarations.

Source: `https://github.com/astral-sh/ty/issues/1889` (TypedDict).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 4.5 Enums and literal-member reasoning

ty models enum declarations with more precision than simply assigning every member the containing enum class as its type.

It can infer literal enum members, derive `.name` and `.value` types, recognize selected `auto()` behavior, and use enum membership in reachability and exhaustiveness analysis.

This makes enum definitions useful as finite semantic domains.

Such reasoning can eliminate impossible branches or validate handling of all known members, especially in conjunction with `assert_never`.

The scope is subject to the specific enum forms and operations ty supports. Custom enum behavior, unusual equality methods, and dynamically constructed members can introduce limitations.

Source: `https://github.com/astral-sh/ty/issues/1889` (Enums).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 5. Module resolution, package exports, and public API semantics

Module resolution is not merely identifying the filesystem location of an imported Python file.

ty also needs to determine which names a module exposes, how those names are obtained, and which imported declarations represent public interfaces.

These capabilities are important for understanding Python packages whose public APIs are assembled from multiple implementation modules.

### 5.1 Re-exports and `__all__`

Python packages commonly expose symbols through an `__init__.py` file:

```
# models.pyclass Product:    ...# __init__.pyfrom .models import Product__all__ = ["Product"]
```

The public import path is now `package.Product`, even though the defining class resides in `package.models`.

ty understands the relationships among imported bindings, re-exports, and public names.

The upstream capability tracker documents support for:

- Explicit `__all__` declarations.
- Mutations using `__all__.append()`, `.extend()`, and `+=`.
- Wildcard imports and exports.
- Re-export conventions such as `import X as X`.
- Re-exports through stub files.
- Selected conditional and version-dependent exports.
- Interactions between submodule exports and package-level exports.

This means that ty's understanding of a package's visible symbols can be more precise than a simplistic inventory of declarations appearing directly in each file.

The distinction matters especially for stub packages. A name imported into a `.pyi` file is not necessarily exported under every typing rule; the conventions for explicit re-exports must also be considered.

Boundary: ty resolves these relationships internally for checking and language services. It does not provide a documented public operation that exports a canonical package API model containing all resolved aliases and relationships.

Source: `https://github.com/astral-sh/ty/issues/1889` (Module resolution, imports, packages).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 5.2 Namespace packages and partial stubs

ty supports PEP 420 namespace packages and PEP 561 typing information.

A namespace package can be distributed across multiple independent installable distributions. Its constituent modules may therefore originate from different locations in the module search path.

Partial stub packages introduce a different form of composition.

A stub package marked as partial can supply typing declarations for some submodules while leaving other submodules to be resolved from the underlying installed implementation.

The resolver recognizes the `partial` marker in `py.typed` and allows module resolution to continue into lower-priority sources when an appropriate stub declaration is absent.

This differs from a complete stub package, which can take precedence over the implementation package's source declarations.

The two capabilities interact: resolution may need to combine namespace-package components, stub declarations, and implementation files without incorrectly treating one missing submodule as evidence that the entire module path is unavailable.

This provides a useful mechanism for consuming typing information from partially annotated third-party libraries.

Sources:

`https://docs.astral.sh/ty/modules/`

`https://github.com/astral-sh/ty/blob/main/ruff/crates/ty_module_resolver/src/resolve.rs`

`https://github.com/astral-sh/ty/blob/main/ruff/crates/ty_module_resolver/src/path.rs`

### 5.3 Conditional module members and import safety

A name can exist in a module only under certain runtime conditions.

For example, a module may assign a symbol inside a conditional that cannot be evaluated statically.

ty has distinct diagnostics for unresolved imports, possibly missing imports, possibly missing submodules, and references whose existence cannot be guaranteed.

This is a more refined model than treating module symbols as simply present or absent.

The distinction between `possibly-missing-import` and `possibly-missing-submodule` is useful: an import may resolve to an existing package while a submodule has not been imported or exposed as an attribute of that package.

The practical outcome is that ty can diagnose selected problems in the availability of module interfaces, as well as their types.

Source: `https://docs.astral.sh/ty/reference/rules/` (Import and module-resolution diagnostics).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



## 6. Specialized semantic diagnostics

Beyond ordinary function, assignment, and inheritance checking, ty provides several diagnostic families that exploit its richer understanding of Python semantics.

### 6.1 Detecting impossible or misleading casts

Two diagnostics deserve to be considered together:

| Rule             | Default  | Purpose                                                       |
| ---------------- | -------- | ------------------------------------------------------------- |
| `redundant-cast` | `warn`   | Finds casts that do not meaningfully change the inferred type |
| `disjoint-cast`  | `ignore` | Finds casts between types that cannot share a value           |

Consider:

```
from typing import castdef parse(value: int) -> str:    return cast(str, value)  # disjoint-cast
```

A cast is not a runtime conversion. It simply tells the type checker to treat a value as another type.

When source and destination types are provably disjoint, the cast cannot describe a valid type refinement.

ty can use disjointness reasoning to detect such cases, including distinctions involving invariant generic types and nominal `NewType` declarations.

However, the rule is disabled by default. Some casts are used intentionally to work around incomplete typing information, and aggressive disjointness checking can reject cases that rely on behavior outside the checker's model.

This capability is complementary to the soundness rules described earlier:

- Soundness diagnostics identify insufficiently justified values crossing statically typed boundaries.
- `disjoint-cast` identifies type assertions that contradict the known relationships between types.
- `redundant-cast` identifies assertions that do not contribute additional type information.

Source: `https://docs.astral.sh/ty/reference/rules/#disjoint-cast`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 6.2 Truthiness mistakes involving callables, iterables, and optional values

ty provides targeted diagnostics for three frequent categories of semantic error.

Callable truthiness

`truthiness-test-of-callable` detects cases where a callable value is tested in a boolean context rather than invoked.

```
from collections.abc import Callabledef process(is_ready: Callable[[], bool]) -> None:    if is_ready:  # Suspicious: function object, not its result        ...
```

The rule reports a likely omission of parentheses.

Iterable truthiness

`truthiness-test-of-iterable` detects boolean tests on values declared as `Iterable`, `Iterator`, `Generator`, or similar abstractions.

An iterable is not necessarily a collection. It may not define a meaningful length, and generators are truthy regardless of whether they will yield elements.

```
from collections.abc import Iterabledef process(values: Iterable[int]) -> None:    if values:  # Does not reliably test whether values are available        ...
```

If a contract actually requires sized objects, `Collection` may communicate the intended semantics more accurately. Otherwise, determining emptiness can require consuming or peeking into the iterator.

Optional-value truthiness

`truthiness-test-of-none-union` identifies cases where a value's valid non-`None` alternatives can themselves be falsy.

For example, `if limit:` does not distinguish `None` from the legitimate integer value `0`.

This rule is disabled by default because some programs intentionally treat missing and falsy values equivalently.

The first two rules default to warnings. These diagnostics demonstrate that ty can identify certain behavioral mistakes from the capabilities implied by a type, rather than merely checking whether an operation is permitted.

Source: `https://docs.astral.sh/ty/reference/rules/` (Truthiness diagnostics).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 6.3 Statically identifiable runtime failures

Several other diagnostic rules identify operations that can fail at runtime:

| Rule                          | Problem detected                                                    |
| ----------------------------- | ------------------------------------------------------------------- |
| `unused-awaitable`            | An awaitable returned by a call is discarded without being awaited  |
| `division-by-zero`            | A division operation whose divisor is statically known to be zero   |
| `zero-stepsize-in-slice`      | A slice step known to be zero                                       |
| `index-out-of-bounds`         | Selected provably invalid indexing operations                       |
| `invalid-match-pattern`       | Match patterns that violate runtime pattern-matching requirements   |
| `isinstance-against-protocol` | Invalid `isinstance()` or `issubclass()` checks involving protocols |
| `instance-layout-conflict`    | Class definitions with incompatible multiple-inheritance layouts    |

These are not general runtime-error proofs. They identify failures that can be established from available static information.

Two are particularly significant.

First, `isinstance-against-protocol` understands the distinction between structural typing and runtime-checkability. A `Protocol` may be useful for static structural contracts without supporting arbitrary runtime `isinstance` checks.

Second, `instance-layout-conflict` uses knowledge of Python's object representation to detect invalid class hierarchies, including inheritance combinations involving nonempty `__slots__` or incompatible built-in types.

This is another example of static analysis extending beyond annotations to Python's runtime object semantics.

Sources:

`https://docs.astral.sh/ty/reference/rules/#isinstance-against-protocol`

`https://docs.astral.sh/ty/reference/rules/#instance-layout-conflict`

`https://docs.astral.sh/ty/reference/rules/#unused-awaitable`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty+1



### 6.4 Deprecated symbols and semantic typing metadata

ty recognizes deprecation information associated with PEP 702.

For example, Python 3.13 introduced `warnings.deprecated`, which can mark an interface as deprecated in a manner understood by static tools.

```
from warnings import deprecated@deprecated("Use the replacement API")def old_function() -> None:    ...old_function()  # deprecated
```

ty's `deprecated` rule reports usages of appropriately marked interfaces and defaults to warning severity.

This allows deprecation policy to be communicated through library typing information rather than relying exclusively on runtime warnings or external linting conventions.

Source: `https://docs.astral.sh/ty/reference/rules/#deprecated`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 6.5 Sentinel definitions and identity-sensitive contracts

ty also provides `mismatched-sentinel-name`, an opt-in diagnostic associated with PEP 661-style sentinel declarations.

For example:

```
from typing_extensions import SentinelMISSING = Sentinel("OTHER")  # mismatched-sentinel-name
```

The rule checks that the name supplied to a sentinel constructor agrees with the name being assigned.

Sentinels are important because they can represent values that are distinct from `None` and from ordinary user data.

The diagnostic does not validate every possible sentinel-related invariant. It enforces consistency in the declared identity information.

A related `mismatched-type-name` rule checks naming consistency for other typing constructs that accept a string name, including legacy `TypeVar`, `NewType`, and functional typing declarations.

Source: `https://docs.astral.sh/ty/reference/rules/#mismatched-sentinel-name`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 6.6 Pydantic arguments that runtime validation silently discards

ty includes a specialized diagnostic, `pydantic-discarded-extra-argument`, enabled at warning severity by default.

Pydantic models configured with `extra="ignore"` can silently discard unknown constructor keyword arguments.

```
from pydantic import BaseModelclass User(BaseModel):    name: str    admin: bool = Falseuser = User(name="Alice", admni=True)
```

Here, `admni` is likely a misspelling of `admin`.

Under an ignore-extra policy, the resulting runtime model can be created successfully while retaining the default `admin=False`.

ty's rule detects that the provided argument does not correspond to a recognized model field and would be discarded.

This capability goes beyond inferring Pydantic constructors. It identifies situations where the framework's own runtime configuration permits a likely programming mistake to pass silently.

It also illustrates a general architectural pattern: static semantic analysis can sometimes enforce stronger guarantees than a framework's permissive runtime validation policy.

Source: `https://docs.astral.sh/ty/reference/rules/#pydantic-discarded-extra-argument`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



## 7. Operational and integration capabilities

### 7.1 Official pre-commit integration

Astral maintains a companion repository:

`https://github.com/astral-sh/ty-pre-commit`

It supports both `pre-commit` and `prek`.

An example configuration for the targeted release is:

```
repos:
  - repo: https://github.com/astral-sh/ty-pre-commit
    rev: v0.0.101
    hooks:
      - id: ty
```

The important distinction is that this hook does not simply invoke a standalone ty executable against a list of changed files.

Instead, it invokes uv's preview `uv check` command.

Each hook revision pins the corresponding ty release and an associated uv release. Project dependencies can therefore be resolved from the project's own dependency declarations.

The hook deliberately checks the configured project rather than only files changed in the commit.

This is necessary because a modification to one module may introduce type errors in dependent modules that were not directly edited.

Consequently, the hook does not pass individual filenames to ty. Its file-selection policy comes from the project's ty configuration.

There are important operational implications:

- The default invocation can update `uv.lock`, create a virtual environment, or install dependencies.
- uv's `--isolated` option can avoid modifying the existing project environment.
- `additional_dependencies` for the hook do not provide typing dependencies in the same way as normal project dependency declarations.
- The hook supports ordinary CI runners but is not compatible with the hosted `pre-commit.ci` runner because of that service's network-access restrictions.

This is a meaningful companion integration, not a core capability of ty's own CLI.

Source: `https://github.com/astral-sh/ty-pre-commit`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 7.2 Standalone-script file selection

ty can recognize PEP 723 inline script metadata.

It also provides a mechanism to exclude such scripts from ordinary project-wide checking while allowing them to be checked explicitly.

For example:

```
[tool.ty.src]
exclude-scripts = true
```

The equivalent CLI option is `--exclude-scripts`, with `--include-scripts` available to reverse that choice.

This is distinct from selecting the Python environment used for a script.

One mechanism determines whether a script participates in a project-level check. The other determines which interpreter, dependencies, and version constraints apply to its analysis.

That distinction matters particularly when uv's experimental per-script environment support is enabled.

Sources: `https://docs.astral.sh/ty/reference/configuration/#exclude-scripts` and `https://docs.astral.sh/ty/reference/cli/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty



### 7.3 CLI configuration overrides and shell completion

The CLI supports explicit configuration overrides using `--config`.

For example, individual TOML configuration values can be supplied without modifying the project's configuration file.

`--config-file` permits selection of a particular `ty.toml`, while `TY_CONFIG_FILE` provides the corresponding environment-variable mechanism.

ty also includes `generate-shell-completion` for shell integration.

These features are comparatively minor, but useful in environments where the same source files need to be checked under different configuration policies.

Source: `https://docs.astral.sh/ty/reference/cli/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.astral.sh\&sz=32)

ty+1



## 8. Version-sensitive corrections and implementation limits

The original gap analysis identified several version issues. Further verification clarifies their status.

### 8.1 Correction: `TypeGuard` narrowing is implemented

The earlier gap analysis incorrectly characterized `TypeGuard` narrowing as an outstanding capability.

Core `TypeGuard` narrowing support was implemented and the corresponding upstream issue was closed on December 30, 2025. It is therefore available in the targeted ty release.

The original issue:

`https://github.com/astral-sh/ty/issues/117`

The implementation was tracked through upstream pull request #20974.

`TypeGuard` and `TypeIs` are distinct typing mechanisms.

| Feature                    | `TypeGuard[T]`                                                  | `TypeIs[T]`                                  |
| -------------------------- | --------------------------------------------------------------- | -------------------------------------------- |
| True branch                | Can replace the original type with `T`                          | Narrows using the intersection with `T`      |
| False branch               | Does not generally narrow the target                            | Can narrow by excluding `T`                  |
| Relationship to input type | May narrow to a type not otherwise assignable to the input type | Requires a compatible narrowing relationship |

The difference is important for generic collections and user-defined validation functions.

Both have support in ty, but some method-related, recursive, and advanced narrowing cases remain under development.

The feature tracker contains follow-up items, so a linked issue in that tracker should not automatically be interpreted as evidence that the entire feature is missing.

Sources: `https://github.com/astral-sh/ty/issues/117` and `https://github.com/astral-sh/ty/issues/1889`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 8.2 Diagnostic-rule changes in ty 0.0.100

Version 0.0.100, released November 9, 2026, introduced several important diagnostic taxonomy changes.

These affect configuration files, inline suppressions, and downstream systems that group diagnostics by rule identifier.

| Former rule                | Current interpretation                                                                            |
| -------------------------- | ------------------------------------------------------------------------------------------------- |
| `invalid-overload`         | Removed; replaced by separate overload declaration, implementation, and decorator rules           |
| `invalid-key`              | Retained only as an alias for `invalid-typed-dict-key`; other cases moved to separate diagnostics |
| `invalid-mutable-override` | Renamed to `incompatible-mutable-override`                                                        |
| `unresolved-import`        | Renamed to `import-not-found` in 0.0.97; old identifier remains a compatibility alias             |

The overload split is particularly significant. It now distinguishes:

- `single-overload`
- `missing-overload-implementation`
- `inconsistent-overload-implementation`
- `inconsistent-overload-decorator`
- `misplaced-overload-decorator`

The former `invalid-key` diagnostic was divided into:

- `invalid-typed-dict-key`
- `unknown-typed-dict-constructor-key`
- `non-literal-typed-dict-key`

This permits more targeted diagnostic configuration than was possible with the older combined rules.

An important compatibility detail: `invalid-overload` was removed, whereas `invalid-key` retains a narrower compatibility alias. They therefore require different treatment when interpreting older configurations.

The current documentation also distinguishes missing attributes on a particular union member from attributes missing across all members. This is another example of the diagnostic system becoming more semantically specific.

Sources: `https://github.com/astral-sh/ty/releases/tag/0.0.100` and `https://docs.astral.sh/ty/reference/rules/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



### 8.3 File-rename language-server support

The previous overview noted a discrepancy between the LSP feature table and release notes regarding `workspace/willRenameFiles`.

Upstream release 0.0.99, published November 6, 2026, explicitly added support for this request.

It should therefore be treated as released functionality in ty 0.0.101, subject to normal LSP capability negotiation and editor support.

This method allows a language server to participate in file-rename operations, including producing related workspace edits where supported.

Source: `https://github.com/astral-sh/ty/releases/tag/0.0.99`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 8.4 Areas where typing support remains incomplete

The upstream typing-feature tracker continues to identify gaps involving several advanced language constructs.

These should be distinguished from the fully or partially implemented capabilities discussed above.

| Area                      | Important outstanding or incomplete functionality                              |
| ------------------------- | ------------------------------------------------------------------------------ |
| Variadic generics         | Full `TypeVarTuple` and `Unpack` interactions                                  |
| Generic inference         | Certain recursive and advanced constraint-solving cases                        |
| Protocols                 | Some classmethod, staticmethod, property, and metaclass interactions           |
| `TypedDict`               | PEP 728 `closed`/`extra_items` and certain functional or inheritance forms     |
| Dataclasses               | Some `__post_init__`, replacement, slots, and inheritance behaviors            |
| Constructors              | Certain custom `__new__` and metaclass `__call__` interactions                 |
| Pattern matching          | Some advanced tuple, class, and exhaustive-match cases                         |
| Control flow              | Certain loop and `finally` interactions                                        |
| Stub and module semantics | Some forms of dynamic imports, custom builtins, and compiled-module resolution |

A tracker entry is not always proof that an entire capability is unsupported. Some entries refer to a specific edge case, follow-up implementation, or test-coverage limitation.

For exact version-sensitive claims, the relevant released tests and issue status should be checked rather than assuming a feature family is wholly implemented or wholly absent.

Source: `https://github.com/astral-sh/ty/issues/1889`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+3



## 9. Architectural significance of the additional capabilities

The additions reveal three aspects of ty that deserve stronger emphasis in its overall capability model.

First, ty is a richer Python semantic reasoner than ordinary annotation checking suggests. Its negative and intersection types, static assertions, disjoint-base reasoning, reachability inference, and strict subtype-boundary diagnostics allow it to establish properties that are not directly expressible through conventional type annotations alone.

Second, standardized typing metadata can expose dynamically generated Python contracts. `dataclass_transform`, dataclass synthesis, `TypedDict`, `NamedTuple`, enum inference, and import re-export conventions give ty access to interfaces that are not necessarily present as explicit source-code definitions. This can substantially reduce the need for manually duplicated interface declarations, provided the behavior is within ty's supported semantics.

Third, the diagnostic system increasingly represents distinct semantic guarantees rather than broad categories of type errors. The separation of unsound transfers, invalid casts, potentially missing symbols, disjoint class relationships, deprecated APIs, and malformed generated interfaces allows more precise enforcement policies.

These capabilities interact with ty's incremental analysis engine, but they do not change its public integration boundary. The resulting semantic knowledge remains primarily available through type diagnostics and language-server operations rather than a stable externally queryable type graph.

Taken together, the addendum establishes a more complete picture of ty as a flow-sensitive, incrementally evaluated Python semantic analysis engine with specialized support for generated interfaces, advanced type constraints, and optional soundness enforcement.

The material limitations remain the beta status of its interfaces, incomplete coverage of some advanced typing constructs, checker-specific extensions, and the absence of a documented general-purpose semantic-model export API.