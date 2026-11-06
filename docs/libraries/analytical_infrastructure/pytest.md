# pytest — Comprehensive Python Library Overview

Research date: November 6, 2026 | Target release: pytest 9.2.0 (October 27, 2026) | Status: Stable

## 1. Executive overview

pytest is an extensible Python testing framework that combines test discovery, dependency injection, resource lifecycle management, assertion introspection, parametrized execution, test orchestration, and reporting within a unified plugin architecture.

Its significance extends well beyond writing tests with ordinary Python `assert` statements. pytest provides a programmable execution framework in which tests are collected as structured objects, their dependencies are resolved through fixtures, their execution passes through extensible lifecycle hooks, and their outcomes become structured reports.

The architecture allows pytest to support not only conventional unit tests but also integration tests, complex resource-dependent workflows, data-driven validation, scientific-computing tests, custom test formats, and distributed execution through companion plugins.

The central distinction is that pytest is both a testing framework and an extensible test-execution engine. Many testing infrastructure problems that might otherwise require bespoke dependency management, execution dispatch, cleanup orchestration, or reporting logic can be expressed through combinations of its native capabilities.

### Version and compatibility

| Attribute              | Verified status                                                 |
| ---------------------- | --------------------------------------------------------------- |
| Current stable         | 9.2.0, released October 27, 2026                                |
| Python requirement     | Python 3.10+                                                    |
| Supported interpreters | CPython and PyPy3                                               |
| Licensing              | MIT                                                             |
| Plugin mechanism       | Pluggy-based hook system                                        |
| Configuration          | Native TOML, legacy TOML compatibility, INI-style configuration |
| Parallel execution     | Through companion plugins; not a native pytest worker scheduler |
| Async execution        | Through compatible plugins or custom hook implementations       |

Version 9.2.0 includes improvements to parametrized test identifiers, assertion-rewriting cache behavior, traceback presentation, and configuration validation. The 9.x series also introduced native TOML configuration and built-in subtests. Subtest support remains explicitly classified as experimental with respect to reporting behavior.

The upstream changelog already contains an unreleased pytest 10.0 draft; those changes are excluded from the stable capability descriptions in this reference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



Primary sources:

- Official documentation: `https://docs.pytest.org/en/stable/`
- Stable changelog: `https://docs.pytest.org/en/stable/changelog.html`
- Source repository: `https://github.com/pytest-dev/pytest`
- Package distribution: `https://pypi.org/project/pytest/`

## 2. Architectural model and capability map

pytest can be understood as a sequence of interrelated subsystems.

Configuration and plugin initialization

Settings, plugin discovery, hook registration, test roots

Collection and parametrization

Collectors, items, node IDs, markers, generated test cases

Selection and scheduling

Filtering, ordering, grouping, optional worker plugins

Setup

Fixture resolution and initialization

Call

Execution and assertions

Teardown

Finalizers and cleanup

Reporting and persistent state

Test reports, captured output, terminal/JUnit results, failure cache

Conceptual lifecycle. Plugin hooks can intercept or extend the stages; the setup, call, and teardown phases have distinct outcomes.

### Native capability families

| Capability family             | Major mechanisms                                                       | Architectural significance                                    |
| ----------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------- |
| Discovery and collection      | Collectors, nodes, items, import modes, node IDs                       | Extensible discovery of executable tests                      |
| Fixtures and dependencies     | Fixture graph, scopes, caching, autouse, finalization                  | Declarative resource management                               |
| Test generation               | Parametrization, indirect arguments, `pytest_generate_tests`, subtests | Data-driven execution and dynamic case generation             |
| Assertions                    | AST rewriting, `raises`, `warns`, `approx`, exception-group matching   | Rich failure diagnostics without custom assertion hierarchies |
| Selection and policy          | Markers, `-k`, `-m`, skip, xfail, strict validation                    | Test classification and execution control                     |
| Isolation and instrumentation | `monkeypatch`, capture fixtures, logging, temporary paths              | Controlled environments and observable execution              |
| Extensibility                 | Pluggy hooks, wrappers, custom collectors, plugin fixtures             | Custom execution, collection, and reporting semantics         |
| Persistence and reporting     | Cache, JUnit XML, session reports, CLI reporting hooks                 | Incremental development and CI integration                    |
| Ecosystem interoperability    | unittest, doctest, external plugins                                    | Reuse of existing test assets and specialized infrastructure  |

The capability families are closely related. For example, parametrization changes what is collected, fixture dependencies determine resource construction, markers influence selection and behavior, and hooks can customize each stage without replacing the runner.

This composability is pytest's principal architectural advantage.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+3



## 3. Test discovery, collection, and execution

### 3.1 Collection is a structured transformation, not just file scanning

pytest normally discovers Python test files matching `test_*.py` and `*_test.py`, identifies test functions and classes, and constructs an object hierarchy representing the collected tests.

The collection model includes:

| Object                                | Role                                                  |
| ------------------------------------- | ----------------------------------------------------- |
| `pytest.Session`                      | Root of the collection and execution session          |
| `pytest.Collector`                    | Base abstraction for objects that collect child nodes |
| `pytest.Directory` / `pytest.Package` | Filesystem and package collection                     |
| `pytest.File` / `pytest.Module`       | File/module-oriented collectors                       |
| `pytest.Class`                        | Collector for test classes                            |
| `pytest.Function`                     | Executable Python test-function item                  |
| `pytest.Item`                         | Base abstraction for executable test cases            |

An important distinction is that a Collector represents discovery structure, whereas an Item represents something executable. Extensions can introduce their own implementations of either.

Each collected item receives a node identifier, typically resembling:

```
tests/test_solver.py::TestOptimizer::test_convergence[case-a]
```

Node IDs are essential for exact selection, result correlation, parametrized test identity, and integrations with external test infrastructure.

The default collection process can be inspected without executing tests:

```
pytest --collect-only -q
```

pytest also exposes collection hooks for modifying or replacing parts of this process. This makes it possible to collect tests from generated specifications, manifest files, structured data, and non-Python formats without requiring an entirely separate test runner.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+2



### 3.2 Custom discovery and collection

Important extension points include:

| API or hook                     | Capability                                     |
| ------------------------------- | ---------------------------------------------- |
| `pytest_ignore_collect`         | Exclude paths conditionally                    |
| `pytest_collect_directory`      | Supply a custom directory collector            |
| `pytest_collect_file`           | Recognize and collect custom file types        |
| `pytest_pycollect_makeitem`     | Customize collection of Python objects         |
| `pytest_collection_modifyitems` | Reorder, deselect, or annotate collected items |
| `pytest_collection_finish`      | Inspect or act after collection                |
| `Collector.collect()`           | Produce child nodes from a custom collector    |
| `Item.runtest()`                | Define how a custom test item executes         |

Custom collectors can therefore implement testing systems based on file contents rather than exclusively on Python functions.

For example, a collection extension could interpret each record in a declarative test manifest as a distinct `pytest.Item`, associate it with markers and metadata, and execute it through the ordinary pytest reporting machinery.

That approach preserves much of pytest's execution and plugin ecosystem without rewriting its discovery engine.

Important limitation: Custom collection items do not automatically acquire every behavior associated with native Python function items. Fixture integration, assertion rewriting, and test-function invocation mechanisms may require explicit support, depending on the collector design.

Sources:

- Custom non-Python collection: `https://docs.pytest.org/en/stable/example/nonpython.html`
- Custom directory collectors: `https://docs.pytest.org/en/stable/example/customdirectory.html`
- Hook/API reference: `https://docs.pytest.org/en/stable/reference/reference.html`

### 3.3 Selection and executable test identity

pytest supports selection at several levels.

| Mechanism                    | Meaning                                             |
| ---------------------------- | --------------------------------------------------- |
| File/directory arguments     | Restrict collection or execution to specified paths |
| `path::Class::test_name`     | Select an exact collection node                     |
| `-k "expression"`            | Filter using names, markers, and other keywords     |
| `-m "expression"`            | Filter by registered marker metadata                |
| `--pyargs`                   | Discover tests relative to an importable package    |
| `--ignore` / `--ignore-glob` | Exclude paths from discovery                        |
| `--deselect`                 | Deselect specified collection nodes                 |
| `@arguments.txt`             | Load test-selection arguments from a file           |

The distinction between `-k` and `-m` matters. `-k` is a flexible keyword-matching mechanism; `-m` evaluates marker expressions and supports matching marker arguments.

Selection is performed within pytest's collection infrastructure. It should not be confused with a general-purpose incremental dependency engine: ordinary selection and last-failed execution do not imply that pytest avoids all import or collection costs.

### 3.4 Import modes and test module identity

pytest supports three principal Python import modes:

| Import mode | Behavior                                                         | Consequence                                                                                    |
| ----------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `prepend`   | Adds an appropriate directory to the beginning of `sys.path`     | Historical default; may create module-name collision and import-path issues                    |
| `append`    | Appends the relevant directory to `sys.path`                     | Can favor an installed package over a local checkout                                           |
| `importlib` | Uses importlib-based loading without the same path modifications | Improves isolation of test module names, but changes import accessibility between test modules |

`--import-mode=importlib` can be advantageous when test files are not conventional packages or when duplicate test-module names exist. However, its different import semantics require intentional handling of shared test utilities.

A related distinction: `rootdir` determines collection identity and configuration context; it does not inherently make that directory importable. Likewise, `python -m pytest` differs slightly from the `pytest` console command because Python adds the current directory to `sys.path`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+2



Reference: `https://docs.pytest.org/en/stable/explanation/pythonpath.html`

## 4. Fixture dependency injection and resource lifecycle management

The fixture system is among pytest's most powerful native capabilities. It is better understood as a scope-aware dependency graph and lifecycle engine than as a collection of setup functions.

### 4.1 Dependency resolution

Fixtures are requested by name through test or fixture function parameters. Fixtures can themselves request other fixtures, producing a directed dependency graph.

pytest resolves that graph, constructs the required resources, caches fixture results according to scope and parametrization, and executes cleanup at the appropriate boundary.

```
import pytest@pytest.fixture(scope="session")def engine():    resource = create_engine()    yield resource    resource.close()@pytest.fixturedef transaction(engine):    tx = engine.begin()    yield tx    tx.rollback()def test_operation(transaction):    assert perform_operation(transaction).valid
```

Illustrative example; not executed.

The `transaction` fixture establishes an explicit dependency on `engine`. This encodes both construction order and resource ownership.

A separate dependency-injection container is therefore unnecessary for many testing-specific resource graphs. pytest already supports dependency discovery, dependency caching, initialization, sharing, and teardown.

However, its dependency injection is intended for tests and fixtures, not general application runtime dependency management.

### 4.2 Scope and resource reuse

pytest supports five scopes:

| Scope      | Lifetime                                |
| ---------- | --------------------------------------- |
| `function` | One test execution                      |
| `class`    | Tests within a test class               |
| `module`   | Tests within a module                   |
| `package`  | Tests within a package collection scope |
| `session`  | The pytest test session                 |

Fixtures are normally initialized lazily, when first requested.

A fixture's scope controls how long its value can be reused and when teardown takes place. The default `function` scope favors isolation; broader scopes allow expensive resources to be shared.

A consequential implementation detail: pytest caches only one instance of a given fixture at a time. Parametrized fixtures can therefore be instantiated more than once even within a broad fixture scope.

Broader scope also does not imply immutable or concurrency-safe resources. Shared mutable fixture values can introduce order dependencies or cross-test contamination.

### 4.3 Fixture ordering is graph-driven

Three factors determine fixture execution order: scope, dependencies, and autouse status.

Higher-scoped fixtures generally execute before lower-scoped ones, while declared dependencies impose ordering constraints. Autouse fixtures are initialized before other applicable fixtures at their scope.

Function names, definition order, and argument order are not reliable general ordering mechanisms.

This has an architectural benefit: complex preparation procedures can be represented by small resource providers with explicit dependencies rather than a manually maintained sequence of global setup operations.

### 4.4 Yield fixtures, finalizers, and failure handling

Two cleanup mechanisms are available.

Yield fixtures run preparation code before `yield`, expose a resource, and execute code after `yield` when the resource's lifetime ends.

`request.addfinalizer()` dynamically registers cleanup callables. This is useful when resource creation has multiple stages or cleanup registration must follow successful acquisition of a particular resource.

Both participate in pytest's teardown ordering.

If a yield fixture raises before reaching `yield`, pytest does not execute that fixture's post-yield code. However, resources from previously successful fixtures remain eligible for cleanup.

For reliable cleanup of partially initialized resources, it can be advantageous to divide acquisition steps among fixtures or register finalizers immediately after successful acquisition.

This helps avoid manually maintaining a large setup/teardown state machine.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



### 4.5 Advanced fixture composition

Several less obvious facilities make fixtures useful beyond static object creation.

| Facility                            | Distinctive behavior                                                       |
| ----------------------------------- | -------------------------------------------------------------------------- |
| `autouse=True`                      | Automatically activates a fixture for applicable tests                     |
| `@pytest.mark.usefixtures`          | Requests fixtures for side effects without receiving their values          |
| `request.getfixturevalue()`         | Dynamically resolves a named fixture                                       |
| `request.param`                     | Accesses the current indirect/fixture parameter                            |
| `request.node`                      | Inspects the requesting collection node                                    |
| `request.config`                    | Accesses pytest configuration                                              |
| `request.node.get_closest_marker()` | Uses test metadata to influence fixture behavior                           |
| `params=` on `@pytest.fixture`      | Generates fixture variants                                                 |
| `scope=<callable>`                  | Determines fixture scope dynamically at definition time                    |
| Fixture factories                   | Return a callable that produces multiple objects within a fixture lifetime |
| Local fixture overrides             | Replace or extend fixtures at more specific collection scopes              |

Dynamic fixture scope is particularly useful when resource sharing should be configurable rather than hard-coded.

The `request` object also makes it possible to derive resource configuration from a test's markers or parametrization. This provides a connection between metadata-driven test selection and dependency construction.

Scope constraint: A wider-scoped fixture cannot directly depend on a narrower-scoped fixture whose lifetime would be insufficient for its dependency. Such designs need compatible scopes or different resource ownership.

### 4.6 Fixture visibility and override resolution

Fixtures can be defined at the test-class level, module level, within hierarchical `conftest.py` files, or in installed plugins.

Fixture lookup is performed from the perspective of the requesting test. More local fixtures can override broader definitions, while plugins can provide reusable fixtures without direct imports into each test module.

This gives pytest a powerful form of context-sensitive dependency resolution: the same test or fixture implementation may receive a different underlying resource depending on its collection context.

pytest 9.1 improved fixture-override precedence for programmatically registered fixtures by prioritizing specificity in the collection tree. It also introduced `pytest.register_fixture()`, an imperative fixture-registration interface designed for advanced plugin authors when declarative decorators are insufficient.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



For extensions that construct fixtures dynamically, the imperative interface is especially relevant: fixture registration need not always originate from statically decorated Python functions.

### 4.7 Tradeoffs

Fixture graphs are highly expressive, but their implicit invocation can also obscure expensive setup and shared state. Broad autouse fixtures can increase overhead and introduce unexpected coupling. Excessive use of dynamic `getfixturevalue()` can make the dependency graph harder to understand.

The most important distinction is between resource lifetime, resource visibility, and resource ownership. They are related but not interchangeable.

Primary references:

- Fixture guide: `https://docs.pytest.org/en/stable/how-to/fixtures.html`
- Fixture resolution and ordering: `https://docs.pytest.org/en/stable/reference/fixtures.html`
- Fixture API: `https://docs.pytest.org/en/stable/reference/reference.html`

## 5. Parametrization, test generation, and subtests

pytest offers multiple mechanisms for converting one test definition into many validation cases. The main architectural distinction is whether cases are known at collection time or created during execution.

### 5.1 Declarative test parametrization

`@pytest.mark.parametrize` expands a test function into separate collected items for each parameter set.

It supports multiple arguments, explicit IDs, per-case markers, and stacked decorators. Stacking independent parameter sets produces their Cartesian product.

`pytest.param()` adds case-specific metadata, such as an expected failure, skip condition, or descriptive identifier.

```
import pytest@pytest.mark.parametrize(    "value, expected",    [        pytest.param(2, 4, id="normal"),        pytest.param(0, 0, id="zero"),        pytest.param(-1, 1, id="negative"),    ],)def test_square(value, expected):    assert value * value == expected
```

The cases have independent collection identities. Consequently, they support individual selection, separate reporting, last-failed tracking, and distribution across workers when supported by a parallel-execution plugin.

One easily overlooked behavior is that parameter values are not copied automatically. Mutable parameter objects can retain mutations between cases if reused.

### 5.2 Indirect parametrization and deferred resource construction

With `indirect=True`, a parameter value is sent through a fixture instead of being supplied directly to the test.

The fixture receives the value through `request.param`.

This separates inexpensive case description during collection from potentially expensive resource construction during test execution.

For example, a matrix of connection configurations can be generated without establishing every connection at collection time. The actual resource is constructed only when its fixture executes.

That separation matters for databases, external processes, containers, expensive models, and other resources whose construction cost is materially greater than generating the test parameters.

### 5.3 Dynamic collection-time generation

The `pytest_generate_tests(metafunc)` hook enables generation of parametrized cases based on configuration, external metadata, or other information available during collection.

`Metafunc.parametrize()` can be used to construct those cases programmatically.

This supports capabilities such as configuration-dependent test matrices, schema-driven validation, dynamically determined backend combinations, and reproducible parameterized test catalogs.

`pytest_make_parametrize_id` can customize the identifiers produced for parameter values. This is particularly helpful when parameters are domain objects whose default representations are unsuitable for readable test IDs.

The main limitation is that cases must still be determined during collection. An expensive or nondeterministic generator can make collection slow, unstable, or incompatible with distributed execution.

### 5.4 Parametrized fixtures and resource grouping

Fixture parameters can be specified directly through `@pytest.fixture(params=...)`.

A parametrized fixture can also combine with function-level parametrization, producing a larger matrix of resource variants and test inputs.

pytest attempts to group relevant tests to minimize activation and teardown of parametrized resources.

This enables efficient reuse of expensive fixtures across several related test cases, although resource sharing is constrained by fixture scopes, parameter instances, and the execution scheduler.

Under distributed execution, grouping behavior depends on the companion scheduler rather than pytest alone.

### 5.5 Subtests: runtime validation groups

Native subtest support was introduced in pytest 9.0.

Subtests are especially important when the set of validation cases emerges during execution rather than being completely known beforehand.

```
def test_generated_outputs(subtests, produced_records):    for record in produced_records:        with subtests.test(record_id=record.id):            assert record.is_valid()            assert record.score >= 0
```

Each subtest context can report a failure without terminating the surrounding test function. This allows multiple independent failures to be discovered in one run.

The two mechanisms differ substantially:

| Property                                         | Parametrization                      | Subtests                                  |
| ------------------------------------------------ | ------------------------------------ | ----------------------------------------- |
| Case generation                                  | Collection time                      | Runtime                                   |
| Separate collected items                         | Yes                                  | No                                        |
| Select individual case by node ID                | Yes                                  | No                                        |
| Distribute individual cases                      | Yes, with an appropriate plugin      | Not independently                         |
| Last-failed selection per case                   | Yes                                  | No                                        |
| Discover multiple assertion failures in one test | Across separate cases                | Within one test execution                 |
| Runtime-dependent number of cases                | Limited by collection-time knowledge | Supported                                 |
| Stability                                        | Established                          | Core usage stable; reporting experimental |

pytest's documentation explicitly identifies limitations in individually addressing subtests through execution-oriented plugins. The framework also supports `unittest.TestCase.subTest()`.

The native implementation supersedes the need for the older `pytest-subtests` plugin for most ordinary subtest functionality, although the plugin and core do not have identical configuration options.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



### 5.6 Parameter identity and version 9.2 improvements

Generated test IDs influence developer experience, reproducibility, selection, and some plugin integrations.

pytest 9.2 introduced `parametrize_long_str_id_strategy` to control automatically generated IDs derived from long strings or bytes.

| Strategy   | Effect                                                   |
| ---------- | -------------------------------------------------------- |
| `short`    | Default; long values use an argument-name/index fallback |
| `sha256`   | Generates a SHA-256-based identifier                     |
| `legacy`   | Preserves the old full-string behavior                   |
| `disallow` | Requires explicit IDs for values exceeding the threshold |

The automatic-ID policy does not replace explicitly supplied IDs.

This is useful where input parameters contain large text, documents, serialized payloads, or other values unsuitable for incorporation directly into node identifiers.

Other relevant mechanisms include `pytest.HIDDEN_PARAM` for suppressing one parameter-set identifier and explicit IDs supplied through `ids=` or `pytest.param(id=...)`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.pytest.org\&sz=32)

pytest documentation+1



Primary references:

- Parametrization: `https://docs.pytest.org/en/stable/how-to/parametrize.html`
- Advanced parametrization patterns: `https://docs.pytest.org/en/stable/example/parametrize.html`
- Subtests: `https://docs.pytest.org/en/stable/how-to/subtests.html`

## 6. Assertion introspection and specialized validation

pytest's assertion subsystem is more sophisticated than its ordinary `assert` syntax suggests.

### 6.1 AST-based assertion rewriting

pytest installs an import hook that rewrites assertions in eligible Python modules before bytecode compilation.

The transformation preserves the logical behavior of assertions while enabling detailed explanations of failed expressions.

For example:

```
assert result.values == expected.values
```

A failure can expose the differing elements, intermediate expression values, and context-specific differences without requiring a custom assertion method.

Native comparison explanations exist for sequences, mappings, sets, strings, and other supported structures.

This eliminates much of the need for specialized `assertEqual`, `assertListEqual`, or similar testing-specific assertion APIs.

Important boundaries: Assertion rewriting applies to pytest-discovered test modules and supported plugin modules. Ordinary imported application modules are not automatically rewritten. Plugin packages can call `pytest.register_assert_rewrite()` before importing assertion-helper modules to opt them into rewriting.

The rewrite mechanism can be disabled with `--assert=plain`, and Python optimization settings that remove assertions remain relevant.

pytest 9.2 changed its rewritten-bytecode cache to use source hashes rather than source modification timestamps. This improves cache reuse when file timestamps change without corresponding source changes, notably in restored CI caches.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+2



### 6.2 Custom domain-specific assertion explanations

The `pytest_assertrepr_compare(config, op, left, right)` hook allows domain-aware failure messages for custom objects.

It can transform an unhelpful representation comparison into a report explaining the specific properties that differ.

For example, a testing extension could produce structured explanations of numerical matrix differences, model-state mismatches, or schema deviations.

This capability provides an architectural alternative to proliferating custom assertion functions throughout test code.

A separate, opt-in hook, `pytest_assertion_pass`, can observe successful assertions and receive their rewritten explanations. It requires `enable_assertion_pass_hook=true` and appropriate rewriting-cache handling.

That mechanism can support richer assertion-level instrumentation, but it introduces additional processing on successful assertions and is not enabled by default.

Reference: `https://docs.pytest.org/en/stable/how-to/assert.html`

### 6.3 Approximate equality

`pytest.approx()` supports approximate comparisons for numeric data, including scalars, sequences, mappings, and supported array objects.

It offers relative and absolute tolerance control, along with explicit NaN handling.

This is especially useful in scientific and numerical tests where exact floating-point equality is inappropriate.

The key semantic distinction is that approximate equality is a tolerance-based testing predicate, not a general numerical equivalence relation. Relative tolerances can depend on the reference operand; comparisons should not be assumed to have all the properties of exact equality.

pytest 9.1 additionally introduced support for `datetime` and `timedelta` comparisons with suitable `timedelta` tolerances. Datetime comparisons require an explicit tolerance and do not support relative tolerance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



This does not replace domain-specific numerical validation where vector norms, error distributions, significant figures, conservation tolerances, or scale-dependent error models are required.

### 6.4 Exception testing and structured exception groups

pytest's exception-testing facilities include:

| Mechanism            | Capability                                                       |
| -------------------- | ---------------------------------------------------------------- |
| `pytest.raises()`    | Assert an expected exception type                                |
| `match=`             | Validate exception messages and notes using a regular expression |
| `check=`             | Apply additional validation to an exception                      |
| `ExceptionInfo`      | Inspect exception type, value, traceback, and group contents     |
| `pytest.RaisesExc`   | Define an exception-matching specification                       |
| `pytest.RaisesGroup` | Precisely match `ExceptionGroup` structures                      |

`RaisesGroup` and `RaisesExc` are particularly valuable for modern concurrent Python applications, where multiple failures may be aggregated into an `ExceptionGroup`.

```
import pytestwith pytest.RaisesGroup(    pytest.RaisesExc(ValueError, match="invalid"),    TypeError,):    raise ExceptionGroup(        "validation",        [ValueError("invalid input"), TypeError("wrong type")],    )
```

Illustrative example; not executed.

`RaisesGroup` can validate expected exception types, multiplicity, nested groups, messages, and predicates.

Its matching is stricter than `except*` by default, although `flatten_subgroups` and `allow_unwrapped` provide additional flexibility.

An especially consequential distinction is that `ExceptionInfo.group_contains()` establishes the presence of a matching exception, not the absence of unexpected additional exceptions. For strict validation of the complete group, `RaisesGroup` is the better native abstraction.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



Reference: `https://docs.pytest.org/en/stable/how-to/assert.html`

### 6.5 Warning and deprecation validation

pytest supports warning capture and assertions through `pytest.warns()`, `pytest.deprecated_call()`, and the `recwarn` fixture.

Warning behavior can be controlled using Python warning filters, pytest configuration, CLI flags, and per-test `filterwarnings` markers.

These mechanisms are useful for testing compatibility contracts, scheduled deprecations, numerical instability warnings, and other non-exception failure signals.

pytest 9.1 added `--max-warnings` and the `max_warnings` configuration setting, allowing a test run to fail when its warning count exceeds a specified threshold.

The framework therefore supports treating warnings not merely as diagnostic text but as an enforceable testing condition.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



Reference: `https://docs.pytest.org/en/stable/how-to/capture-warnings.html`

## 7. Markers, conditional execution, and test policies

Markers provide metadata associated with collected tests. They are both a selection mechanism and an extension interface.

### 7.1 Built-in markers

| Marker                       | Purpose                                  |
| ---------------------------- | ---------------------------------------- |
| `pytest.mark.parametrize`    | Generate parameterized test items        |
| `pytest.mark.skip`           | Unconditionally skip a test              |
| `pytest.mark.skipif`         | Conditionally skip based on a predicate  |
| `pytest.mark.xfail`          | Declare an expected failure              |
| `pytest.mark.usefixtures`    | Activate fixtures for their side effects |
| `pytest.mark.filterwarnings` | Apply warning filters to tests           |

Markers can be applied to functions, classes, and entire modules using `pytestmark`.

Custom markers can represent capabilities, environments, resource categories, or other metadata.

By themselves, custom markers do not implement resource scheduling, timeouts, or backend selection. They become operational when pytest selection expressions, fixtures, or plugins interpret them.

### 7.2 Skip versus expected failure

A skipped test is intentionally not executed.

An expected-failure (`xfail`) test ordinarily executes, with a failure classified as expected rather than as a regular test failure.

`xfail` can specify a failure reason, a conditional predicate, and an expected exception class. Modern pytest also supports structured exception matchers such as `RaisesGroup` in its `raises` argument.

The `strict` behavior is important. Without strict handling, an unexpected pass (`XPASS`) does not necessarily fail the overall test session. Strict expected failures make unexpected passes actionable failures.

For known defects, strict xfail can help ensure that a fixed behavior is not silently left under an obsolete expected-failure declaration.

### 7.3 Strict marker and configuration validation

Custom markers should be registered in pytest configuration or by plugins.

With `strict_markers` enabled, unknown marker names are errors rather than warnings. In pytest 9.2, validation also covers names referenced in `-m` selection expressions.

The broader `strict_config` and `strict` settings help make configuration errors explicit.

These controls reduce ambiguity in large suites where silently mistyped markers or configuration options can otherwise change which tests run.

Source: `https://docs.pytest.org/en/stable/how-to/mark.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+2



## 8. Environment isolation, patching, capture, and filesystem testing

pytest provides several complementary facilities for controlling a test's environment. Their scopes and isolation guarantees differ substantially.

### 8.1 `monkeypatch`: reversible process-state modification

The built-in `monkeypatch` fixture can temporarily modify:

| Mechanism             | Operations           |
| --------------------- | -------------------- |
| Object attributes     | `setattr`, `delattr` |
| Mappings              | `setitem`, `delitem` |
| Environment variables | `setenv`, `delenv`   |
| Python import paths   | `syspath_prepend`    |
| Working directory     | `chdir`              |
| Scoped patching       | `context()`          |

Changes are automatically reversed at fixture teardown or at the end of a `monkeypatch.context()` block.

The context-manager mechanism is especially useful when a patch must be removed before subsequent operations within the same test.

For example, temporarily replacing a standard-library function may be safe during a narrow call but dangerous if the replacement remains active while pytest performs its own reporting or cleanup.

`monkeypatch` is complementary to `unittest.mock`, not a full substitute for it. It manages reversible state changes; mock objects provide additional features such as call histories, argument assertions, spies, and behavior specifications.

Isolation boundary: Patching a module attribute or environment variable does not create a separate process or namespace. The change is visible to code sharing that process during the patch's lifetime. Concurrent threads or tasks can therefore observe it.

Reference: `https://docs.pytest.org/en/stable/how-to/monkeypatch.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 8.2 Output capture

pytest distinguishes interception of Python streams from interception of operating-system file descriptors.

| Facility            | Captures                               | Useful distinction                           |
| ------------------- | -------------------------------------- | -------------------------------------------- |
| `capsys`            | Python `sys.stdout` and `sys.stderr`   | Python-level stream output                   |
| `capsysbinary`      | Python streams as bytes                | Binary-oriented stream assertions            |
| `capfd`             | OS file descriptors 1 and 2            | Native libraries and subprocess output       |
| `capfdbinary`       | File descriptor output as bytes        | Binary or low-level output                   |
| `capteesys`         | Python streams while forwarding output | Simultaneous capture and visible output      |
| `--capture=fd`      | File descriptors globally              | Default runner capture mode                  |
| `--capture=sys`     | Python streams globally                | Avoids FD-level interception                 |
| `--capture=tee-sys` | Capture plus pass-through              | Useful for live console output and reporting |
| `-s`                | Disables ordinary global capture       | Interactive debugging                        |

`capteesys` became available as a built-in fixture in pytest 9.0.

An important practical distinction is that `capsys` cannot necessarily observe output produced by subprocesses or native code writing directly to file descriptors. `capfd` is designed for that broader class of output.

Capture fixtures support `readouterr()` to retrieve output accumulated since the previous read. Their behavior can also override ordinary global capture settings for the relevant test.

Reference: `https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



### 8.3 Structured logging capture

The `caplog` fixture enables assertions against Python logging records.

It provides access to text, formatted messages, raw `logging.LogRecord` objects, and `(logger name, severity, message)` tuples.

It also supports temporary log-level configuration through `set_level()` and `at_level()`.

A less obvious capability is phase-aware log retrieval. `caplog.get_records("setup")`, `caplog.get_records("call")`, and `caplog.get_records("teardown")` allow tests or fixtures to inspect logs associated with different execution phases.

This can support checks such as prohibiting warning-level messages during resource initialization, even when the test body itself passes.

pytest additionally supports live terminal logging and log-file output.

Limitations: Logger reconfiguration may alter handlers used by pytest's capture infrastructure. Care is needed when tests replace root logging configuration or use complex multiprocessing logging.

Reference: `https://docs.pytest.org/en/stable/how-to/logging.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 8.4 Temporary filesystem resources

`tmp_path` creates a unique temporary directory for a test and returns a standard `pathlib.Path`.

`tmp_path_factory` can create reusable temporary directories from a session-scoped fixture.

This supports a useful combination: expensive shared input artifacts can be generated once per session, while tests can receive distinct working directories for their mutable outputs.

pytest also provides retention controls:

| Setting                     | Effect                                                                |
| --------------------------- | --------------------------------------------------------------------- |
| `tmp_path_retention_count`  | Number of recent sessions whose temporary directories can be retained |
| `tmp_path_retention_policy` | Retain all, failed-test directories, or none                          |
| `--basetemp`                | Specify the base temporary directory                                  |

By default, temporary directories are retained for the last three pytest invocations.

The older `tmpdir` and `tmpdir_factory` interfaces use `py.path.local` rather than `pathlib.Path` and are legacy compatibility mechanisms.

Limit: Temporary directory uniqueness does not imply that external resources, databases, services, or shared system paths are isolated.

Reference: `https://docs.pytest.org/en/stable/how-to/tmp_path.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



## 9. The Pluggy architecture: hooks and extensibility

pytest's plugin system is built on Pluggy, a separate Python library that implements hook specification, registration, validation, and dispatch.

pytest defines the testing lifecycle and its hook contracts; Pluggy provides the underlying extensibility machinery. This separation is important because pytest's architecture is not simply a set of callbacks attached to a runner. Its core behaviors are themselves implemented through cooperating plugins.

### 9.1 Plugin discovery and registration

pytest recognizes three principal plugin categories: built-in plugins, locally discovered `conftest.py` plugins, and installed external plugins.

External distributions register plugins through the `pytest11` entry-point group:

```
[project.entry-points.pytest11]
example_plugin = "example_package.pytest_plugin"
```

At startup, pytest processes explicitly disabled plugins (`-p no:name`), built-ins, explicitly requested plugins (`-p name`), installed entry points, the `PYTEST_PLUGINS` environment variable, and initial `conftest.py` files.

Installed plugins normally load automatically. This can be controlled with `--disable-plugin-autoload` or `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, then enabling selected plugins explicitly.

The distinction is operationally significant: installing a pytest plugin can change test collection or execution even when individual tests never import it.

`pytest --trace-config` reveals the active plugin environment. `config.pluginmanager.get_plugin(name)` allows one plugin to locate another registered plugin.

Local `conftest.py` hooks usually have directory-scoped applicability, but loading a plugin through `pytest_plugins` affects the wider plugin environment. Declaring `pytest_plugins` in non-root `conftest.py` files is deprecated because that distinction can be misleading.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



### 9.2 Hook contracts and dispatch

Hook specifications define the extension points and accepted arguments. Hook implementations declare how a plugin participates.

Pluggy validates implementation signatures and supports forward-compatible argument handling: a hook implementation may accept only the named arguments it needs.

Some hooks collect results from multiple implementations; others use first-result semantics, stopping when an implementation returns a non-`None` result.

This difference is particularly important when extending discovery or replacing default behavior. A hook intended to contribute metadata is not equivalent to one that selects a single implementation of a protocol operation.

Hook implementations can also use:

- `@pytest.hookimpl(tryfirst=True)` to prefer earlier execution.
- `@pytest.hookimpl(trylast=True)` to prefer later execution.
- `@pytest.hookimpl(wrapper=True)` to execute around other implementations.

A wrapper yields exactly once, receiving either the result of the wrapped execution or its exception. This permits cross-cutting instrumentation, result adaptation, and cleanup without directly replacing the underlying implementation.

Hook ordering is priority-driven rather than an arbitrary fixed sequence. Wrappers execute around ordinary implementations, with their own ordering controls.

pytest also allows plugins to publish entirely new hook specifications using `pytest_addhooks`, creating extension contracts that other plugins can implement.

Important limitation: Most non-`pytest_runtest_*` hooks should not raise exceptions. Errors in lifecycle hooks can disrupt the entire session, rather than failing one isolated test.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



Reference: `https://docs.pytest.org/en/stable/how-to/writing_hook_functions.html`

### 9.3 Lifecycle hook families

| Stage                 | Representative hooks                                                                                | Possible extension                                     |
| --------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Configuration         | `pytest_addoption`, `pytest_configure`, `pytest_unconfigure`                                        | Configuration parameters, registration, initialization |
| Collection            | `pytest_collect_file`, `pytest_collect_directory`, `pytest_pycollect_makeitem`                      | New test formats and discovery mechanisms              |
| Generation            | `pytest_generate_tests`, `pytest_make_parametrize_id`                                               | Dynamic cases and stable IDs                           |
| Collection completion | `pytest_collection_modifyitems`, `pytest_collection_finish`                                         | Selection, grouping, annotations                       |
| Test protocol         | `pytest_runtest_protocol`, `pytest_runtest_setup`, `pytest_runtest_call`, `pytest_runtest_teardown` | Specialized execution behavior                         |
| Reporting             | `pytest_runtest_makereport`, `pytest_runtest_logreport`, `pytest_report_teststatus`                 | Structured results, diagnostics, status classification |
| Session completion    | `pytest_sessionfinish`, `pytest_terminal_summary`                                                   | Final result processing and summary output             |

The runtime protocol normally produces separate reports for setup, call, and teardown, not merely one outcome for an entire test function.

That distinction enables reporting systems to distinguish a failed assertion from an unavailable fixture or failed cleanup operation.

Plugins can intercept the protocol itself, inspect the `CallInfo` execution result, construct or adapt `TestReport` objects, and contribute reporting information.

For distributed execution, pytest also exposes report serialization hooks, `pytest_report_to_serializable` and `pytest_report_from_serializable`. They are relevant when plugins add information that must cross process boundaries.

Reference: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+2



### 9.4 Typed extension state with `pytest.Stash`

Plugins often need to associate data with a test item or session configuration during one hook and retrieve it in another.

pytest provides `pytest.Stash` and `pytest.StashKey` for this purpose.

```
import pytestSTARTED_AT = pytest.StashKey[float]()@pytest.hookimpldef pytest_runtest_setup(item):    item.stash[STARTED_AT] = read_monotonic_clock()@pytest.hookimpldef pytest_runtest_teardown(item):    started = item.stash.get(STARTED_AT, None)    if started is not None:        observe_elapsed_time(started)
```

Illustrative plugin sketch; `read_monotonic_clock()` and `observe_elapsed_time()` are placeholders.

A `StashKey` has unique identity and supports typed values. Different plugins can therefore store information without negotiating attribute names or risking collisions on collection objects.

`item.stash` and `config.stash` provide distinct attachment points for item-level and configuration-level state.

This reduces the need for ad hoc global dictionaries keyed by node IDs, dynamically attached private attributes, or custom registries for straightforward per-object metadata.

However, stash values are local Python process state. They are not automatically serialized to pytest-xdist workers or controller processes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 9.5 Plugin testing is a native capability

pytest includes the `pytester` testing plugin, disabled by default, for exercising pytest extensions.

The `pytester` fixture can generate temporary test files and configuration, run nested pytest invocations, and inspect their outputs and outcomes.

It supports both in-process and subprocess execution patterns.

This is valuable for testing custom collection, plugin initialization, CLI options, failure formatting, and reporting behavior—the kinds of extension code that cannot be adequately validated by invoking an ordinary helper function.

Because the plugin is opt-in, it must be activated with `-p pytester` or an equivalent plugin declaration.

Nested runs also require care with installed plugin autoloading: unrelated plugins can affect the behavior being tested.

References:

- Plugin authoring: `https://docs.pytest.org/en/stable/how-to/writing_plugins.html`
- `pytester` reference: `https://docs.pytest.org/en/stable/reference/reference.html`

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1

## 10. Reporting, diagnostics, execution controls, and persistent state

pytest provides several layers of output: interactive terminal reporting, structured test reports, machine-readable result exports, and limited state persisted between invocations.

### 10.1 Test reports are structured execution artifacts

The core report model includes collection reports and test execution reports.

A `TestReport` can represent a setup, call, or teardown phase and carries outcome information, duration, captured output, failure explanations, and user-added metadata.

This is more expressive than a simple Boolean pass/fail result.

A plugin can therefore produce aggregate reports that distinguish resource acquisition failures, assertion failures, cleanup failures, warnings, or specialized result categories without reimplementing test execution.

`pytest_report_teststatus` allows plugins to customize terminal status classifications, short progress indicators, and verbose outcome labels. Other hooks can add report sections or terminal-summary content.

### 10.2 JUnit XML and CI interoperability

Built-in `--junitxml=path` exports test outcomes in JUnit-style XML.

pytest supports configuration of suite naming and execution time reporting. By default, reported testcase time includes setup and teardown as well as the call phase; `junit_duration_report=call` changes the duration semantics.

The `record_property` and `record_testsuite_property` fixtures add custom test-level and suite-level metadata.

These facilities have important compatibility limits:

- `record_property` may produce XML that does not conform to strict newer JUnit schemas.
- `record_xml_attribute` can also create schema incompatibilities.
- `record_testsuite_property` is documented as not working with pytest-xdist.

Consequently, custom JUnit metadata should be evaluated against the receiving CI platform's schema and parallel-execution behavior rather than assumed to be universally portable.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



Reference: `https://docs.pytest.org/en/stable/how-to/output.html`

### 10.3 Diagnostics and execution control

| Facility                               | Purpose                                               |
| -------------------------------------- | ----------------------------------------------------- |
| `-x` / `--maxfail=N`                   | Stop after a specified number of failures or errors   |
| `--pdb`                                | Enter a debugger on failure                           |
| `--trace`                              | Enter a debugger at test execution                    |
| `--tb=short`, `--tb=long`, `--tb=none` | Control traceback detail                              |
| `--full-trace`                         | Disable traceback filtering                           |
| `-r` / `-ra`                           | Configure supplementary summary categories            |
| `--durations=N`                        | Show slowest test durations                           |
| `--setup-show`                         | Display fixture setup and teardown                    |
| `--setup-plan`                         | Preview fixture execution without running test bodies |
| `--fixtures-per-test`                  | Inspect fixture dependencies of selected tests        |
| `--collect-only`                       | Inspect collected tests without running them          |
| `--trace-config`                       | Inspect plugin loading and configuration              |
| `--debug`                              | Generate internal pytest tracing information          |

These facilities can reveal very different classes of problem.

For example, `--durations` identifies long-running reported phases, while `--setup-show` reveals fixture activation and reactivation. Together they help distinguish expensive test logic from expensive resource initialization.

Similarly, `--collect-only` and `--trace-config` help diagnose discovery and plugin-configuration problems before runtime execution begins.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



### 10.4 Persistent cache and incremental development

The built-in `cacheprovider` plugin stores small amounts of state between pytest invocations, normally under `.pytest_cache`.

| Option                    | Behavior                                                          |
| ------------------------- | ----------------------------------------------------------------- |
| `--lf` / `--last-failed`  | Rerun tests recorded as failing previously                        |
| `--ff` / `--failed-first` | Run previous failures before other selected tests                 |
| `--nf` / `--new-first`    | Prioritize tests in newer files                                   |
| `--sw` / `--stepwise`     | Stop on failure and resume at the last failing position next time |
| `--sw-skip`               | Skip the first encountered failure in a stepwise run              |
| `--cache-clear`           | Clear persisted pytest cache state                                |

The `config.cache` API also allows plugins to store and retrieve JSON-encodable values.

This can remove the need for a separate persistence subsystem for modest testing metadata such as last-seen values, test-selection hints, or plugin state between local runs.

However, the cache is not a general-purpose incremental build system or a dependency-aware test impact analyzer. It does not automatically determine which tests are affected by changed source files, and cached outcomes should not be treated as an authoritative substitute for execution.

Reordering options such as `--ff` and `--nf` may also influence fixture reuse and expose test-order dependencies.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



Reference: `https://docs.pytest.org/en/stable/how-to/cache.html`

### 10.5 Programmatic invocation and exit-status semantics

pytest exposes `pytest.main(args, plugins=...)` for programmatic invocation and `pytest.ExitCode` for structured exit-status handling.

The stable reference defines seven exit codes:

| Code | Meaning                                                                             |
| ---- | ----------------------------------------------------------------------------------- |
| `0`  | All collected tests passed                                                          |
| `1`  | One or more tests failed                                                            |
| `2`  | Test execution interrupted                                                          |
| `3`  | Internal pytest error or plugin import exception                                    |
| `4`  | Command-line usage error, including certain plugin or `conftest.py` import failures |
| `5`  | No tests collected                                                                  |
| `6`  | Configured maximum warning count exceeded                                           |

Version-sensitive detail: Exit code `6` is new to the 9.1 series, accompanying `--max-warnings`. Older descriptions that enumerate only codes 0–5 are incomplete for pytest 9.2.

Repeatedly calling `pytest.main()` in one Python process can be problematic because Python imports and module caches persist between invocations. Subprocess execution is more appropriate when independent collection and import state are required.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



Reference: `https://docs.pytest.org/en/stable/reference/exit-codes.html`

## 11. Existing test frameworks and documentation-based testing

pytest can act as a common execution and reporting interface for tests that were not originally written for pytest.

### 11.1 `unittest` compatibility

pytest automatically discovers and executes supported `unittest.TestCase` subclasses and their test methods.

Supported behavior includes familiar unittest lifecycle methods, skip decorators, and—since pytest 9.0—`TestCase.subTest()`.

These tests gain access to pytest's runner-level facilities, including filtering, capture, traceback handling, and compatible third-party execution plugins.

However, unittest compatibility does not make `TestCase` methods equivalent to native pytest functions.

| Capability                                   | Native pytest function  | `unittest.TestCase` method |
| -------------------------------------------- | ----------------------- | -------------------------- |
| Direct fixture-argument injection            | Yes                     | No                         |
| Native `@pytest.mark.parametrize` expansion  | Yes                     | No                         |
| Autouse / `usefixtures` side-effect fixtures | Yes                     | Yes                        |
| unittest lifecycle methods                   | Not directly applicable | Yes                        |
| `unittest.subTest()`                         | Not applicable          | Yes                        |
| pytest runner/reporting facilities           | Yes                     | Generally yes              |
| unittest `load_tests` protocol               | Not applicable          | Unsupported by pytest      |

Another less obvious distinction is that `unittest.TestCase` setup and teardown are performed during pytest's call phase, rather than its normal setup and teardown phases. This affects failure attribution and plugins that inspect phase-specific reports.

Reference: `https://docs.pytest.org/en/stable/how-to/unittest.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 11.2 Doctest integration

pytest includes integration with Python's standard-library `doctest` engine.

It can execute examples from text files or Python docstrings using `--doctest-glob` and `--doctest-modules`.

Its doctest integration includes:

- Normalized output-comparison options and tolerance support.
- The `doctest_namespace` fixture for injecting objects into doctest execution namespaces.
- The `getfixture()` helper for requesting available fixtures from doctests.
- Compatibility with relevant skip behavior and fixture-based environment setup.

This enables executable documentation examples to participate in the ordinary test session.

The important limitations are that doctests use a distinct collection/execution model and do not support fixtures dependent on parametrization, including parametrized autouse fixtures. Fixture scope is also not automatically shared between separately collected Python test modules and doctest modules.

For richer documentation formats, tools such as Sybil or pytest-doctestplus provide complementary functionality rather than native pytest capabilities.

Reference: `https://docs.pytest.org/en/stable/how-to/doctest.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



## 12. Concurrency, asynchronous tests, and specialized testing engines

One of pytest's most important architectural boundaries is between its core execution protocol and the execution engines supplied by companion libraries.

Core pytest ordinarily runs tests sequentially in a single thread. Parallel workers, asynchronous event loops, coverage instrumentation, property-based example generation, and browser automation are provided by separate tools or plugins.

These extensions may cooperate through pytest's collection, fixture, and reporting interfaces, but their execution guarantees are not automatically interchangeable.

### 12.1 Parallel execution with pytest-xdist

Companion package: `pytest-xdist` — not bundled with pytest core

pytest-xdist distributes tests among multiple worker processes, potentially running locally or on remote interpreters.

Its architecture has several consequential properties:

1. Each worker performs its own full test collection.
2. The controller checks that workers collected the same test identifiers in the same order.
3. The controller schedules tests using indexes into that shared collection.
4. Workers execute tests through pytest's normal runtime protocol.
5. Reports return to the controller for aggregation and publication.

This means parallel execution does not eliminate collection overhead. A costly collection phase may be repeated in every worker, and nondeterministic test generation can cause collection-consistency failures.

The worker processes have independent Python interpreter state, fixture caches, and event loops.

A session-scoped fixture executes once per worker session, not necessarily once across the entire distributed test run. Shared resource initialization therefore requires explicit inter-process coordination when exactly-once semantics are necessary. pytest-xdist documents a file-lock approach for this problem.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+1



### 12.2 Scheduling modes and resource locality

pytest-xdist provides several scheduling policies.

| Mode               | Scheduling behavior                            | Architectural implication                       |
| ------------------ | ---------------------------------------------- | ----------------------------------------------- |
| `--dist=load`      | Dynamically assigns tests to available workers | General-purpose load balancing                  |
| `--dist=loadscope` | Groups tests by class or module                | Preserves locality for some scoped fixtures     |
| `--dist=loadfile`  | Keeps tests from the same file together        | Reduces file-level setup fragmentation          |
| `--dist=loadgroup` | Groups tests using `xdist_group` markers       | Explicit affinity for shared resources          |
| `--dist=worksteal` | Redistributes queued work from busy workers    | Can improve balancing when durations vary       |
| `--dist=each`      | Runs the complete test set on every worker     | Useful for testing multiple worker environments |
| `--dist=no`        | Disables distribution                          | Ordinary sequential operation                   |

Custom scheduling is possible through `pytest_xdist_make_scheduler`.

Scheduling policy can have substantial consequences for execution time. Distributing tests evenly by count can be inefficient if setup costs dominate; grouping tests can reduce repeated fixture initialization but leave some workers idle.

The optimal tradeoff depends on test durations, setup costs, resource affinity, and the number of available workers.

The distinction between resource sharing inside a worker and resource sharing across workers is particularly important.

Further limitations include the lack of normal `-s` capture behavior under xdist and the need for plugins to handle cross-process reporting explicitly.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+2



Primary sources:

- Execution architecture: `https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html`
- Scheduling: `https://pytest-xdist.readthedocs.io/en/stable/distribution.html`
- Resource coordination: `https://pytest-xdist.readthedocs.io/en/stable/how-to.html`

### 12.3 Asynchronous testing with pytest-asyncio

Companion package: `pytest-asyncio`

pytest does not, by itself, provide a complete async-test execution environment. The `pytest-asyncio` plugin supplies event-loop management, asynchronous fixture execution, and integration with the `asyncio` runtime.

It supports two main collection modes:

- Strict: Handles tests explicitly marked for pytest-asyncio and appropriately decorated async fixtures.
- Auto: Automatically handles detected asynchronous test functions and fixtures.

Strict mode is the default and is particularly relevant when multiple async-testing plugins coexist.

A consequential distinction is between fixture scope and event-loop scope. They govern different lifetimes, although they must be compatible for resources bound to an event loop.

The plugin exposes `asyncio_default_fixture_loop_scope`, `asyncio_default_test_loop_scope`, and async debugging controls.

An asynchronous client, connection, or task bound to a particular loop cannot necessarily be transferred to another loop simply because its pytest fixture has a broad scope.

Reference: `https://pytest-asyncio.readthedocs.io/en/stable/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-asyncio.readthedocs.io\&sz=32)

pytest-asyncio 1.4.1 documentation+1



### 12.4 AnyIO and multi-backend async testing

AnyIO includes its own pytest plugin, which can execute supported asynchronous tests against different backends, principally asyncio and Trio.

The `anyio_backend` fixture can parameterize tests across backend configurations. It also supports asynchronous fixtures and different resource lifetimes.

An important architectural distinction is AnyIO's treatment of asynchronous fixture and test execution within a test runner. Its documented task and context-variable propagation behavior differs from pytest-asyncio.

This matters when testing cancellation scopes, structured concurrency, task groups, and context-local state.

Plugin conflict: AnyIO's automatic async-test mode conflicts with pytest-asyncio's automatic mode. Compatible configurations generally use explicit marks or leave pytest-asyncio in strict mode.

Reference: `https://anyio.readthedocs.io/en/latest/testing.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://anyio.readthedocs.io\&sz=32)

AnyIO 4.15.1.post12 documentation



### 12.5 Property-based testing with Hypothesis

Separate testing engine with pytest integration

Hypothesis is not simply another parametrization interface.

Where pytest parametrization normally enumerates known cases during collection, Hypothesis uses strategies to generate many examples during execution and can shrink failing examples to simpler counterexamples.

Hypothesis provides the example-generation, search, and shrinking machinery. pytest provides the surrounding test collection, fixtures, reporting, and plugin environment.

These mechanisms can compose: one test can be parametrized over several operations and use Hypothesis to generate inputs for each operation.

The distinction matters for case identity. Hypothesis-generated examples are not generally equivalent to individually collected pytest parameter cases with independently selectable node IDs.

Fixtures also have different reuse implications when one pytest test invocation contains many Hypothesis examples, particularly if a fixture returns mutable state.

Reference: `https://hypothesis.readthedocs.io/en/latest/quickstart.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.14 documentation+1



### 12.6 Other important ecosystem boundaries

| Capability                         | Companion package or engine              | What it adds beyond core pytest                                            |
| ---------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------- |
| Code coverage                      | `pytest-cov` + `coverage.py`             | Coverage measurement, reports, execution contexts, distributed aggregation |
| Mocking and spies                  | `pytest-mock` + `unittest.mock`          | `mocker` fixture, spies, stubs, automatic patch cleanup                    |
| Database/web-framework integration | `pytest-django`                          | Django-specific fixtures and database policies                             |
| Browser end-to-end testing         | `pytest-playwright` + Playwright         | Browser contexts, pages, and browser automation                            |
| Property-based testing             | Hypothesis                               | Generated inputs, shrinking, stateful testing                              |
| Asyncio testing                    | `pytest-asyncio`                         | Async test handling and event-loop lifecycle                               |
| Multi-backend async testing        | AnyIO / `pytest-trio`                    | Alternative asynchronous runtimes                                          |
| Parallel execution                 | `pytest-xdist`                           | Worker processes, scheduling, result coordination                          |
| Timeouts                           | `pytest-timeout`                         | Test timeout enforcement                                                   |
| Retries                            | `pytest-rerunfailures`                   | Reexecution of failed tests                                                |
| Randomized execution order         | `pytest-randomly`, `pytest-random-order` | Order randomization to expose hidden state dependencies                    |
| Behavioral specifications          | `pytest-bdd`                             | Gherkin-oriented specification integration                                 |
| Documentation testing              | Sybil, `pytest-doctestplus`              | Expanded executable-documentation capabilities                             |

Some plugins have consequential version and compatibility constraints.

For example, pytest-cov 7 removed the earlier `.pth` mechanism for measuring subprocess coverage, instead directing users to coverage.py's subprocess instrumentation mechanisms. It also supports per-test coverage contexts through `--cov-context=test`.

That context mechanism can link recorded execution coverage to a complete parametrized pytest node ID, providing a basis for more granular coverage analysis. Coverage measurement itself remains a responsibility of coverage.py and pytest-cov rather than pytest core.

The plugin ecosystem is large, but its capabilities should not be treated as universally present, mutually compatible, or backed by identical lifecycle semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-cov.readthedocs.io\&sz=32)

pytest-cov 7.1.0 documentation+2



Primary references:

- Coverage integration: `https://pytest-cov.readthedocs.io/en/latest/`
- Mocking integration: `https://pytest-mock.readthedocs.io/en/latest/`
- Plugin discovery: `https://docs.pytest.org/en/stable/how-to/plugins.html`

## 13. Configuration, compatibility, and version-sensitive behavior

### 13.1 Native TOML versus INI-compatible configuration

pytest 9.0 introduced a native TOML configuration model.

A representative native configuration is:

```
# pyproject.toml
[tool.pytest]
minversion = "9.0"
testpaths = ["tests"]
addopts = ["-ra", "--strict"]
python_files = ["test_*.py", "*_test.py"]

markers = [
    "integration: tests involving external components",
    "slow: tests with substantial execution cost",
]
```

The critical distinction is between:

| Format                 | Section                     | Value semantics                 |
| ---------------------- | --------------------------- | ------------------------------- |
| Native TOML            | `[tool.pytest]`             | Native TOML types               |
| TOML INI compatibility | `[tool.pytest.ini_options]` | Historical INI-style semantics  |
| Standalone TOML        | `[pytest]` in `pytest.toml` | Native TOML configuration       |
| INI files              | `[pytest]` in `pytest.ini`  | INI-style configuration         |
| Other legacy formats   | `tox.ini`, `setup.cfg`      | Supported compatibility formats |

The two `pyproject.toml` tables, `[tool.pytest]` and `[tool.pytest.ini_options]`, cannot be used simultaneously.

pytest chooses one configuration file; it does not merge settings from all available candidates.

`pytest.toml` has the highest precedence, followed by applicable INI and other recognized configuration files. Configuration-file discovery also determines `rootdir` and node-ID path context.

The `pytest.Config` object exposes configuration properties and option-access methods, making configuration accessible to tests through `pytestconfig` and to plugins through hooks.

Reference: `https://docs.pytest.org/en/stable/reference/customize.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



### 13.2 Configuration as an extension contract

Plugins can add CLI options and configuration settings through `pytest_addoption`.

These values can subsequently influence fixture construction, test selection, collection, or execution.

This provides a native configuration channel shared across the testing ecosystem.

For example, a plugin can register a backend selection option, use that option during collection to generate the relevant test cases, and construct the selected backend lazily through fixtures.

The resulting system does not require a separate configuration parser and dispatch architecture for ordinary test-runner options.

However, plugin registration and initialization happen in stages. Hooks such as `pytest_addoption` must be registered early enough to participate in argument processing; a `conftest.py` discovered later cannot retroactively contribute startup behavior.

The distinction between configuration discovery, plugin initialization, test collection, and fixture execution is essential when designing sophisticated extensions.

### 13.3 Strictness and reproducibility controls

pytest's strict configuration options help reduce accidental ambiguity.

| Control                     | Purpose                                                 |
| --------------------------- | ------------------------------------------------------- |
| `strict`                    | Enable a group of strict checks                         |
| `strict_markers`            | Reject unknown markers                                  |
| `strict_config`             | Treat unknown configuration options as errors           |
| `minversion`                | Require a minimum pytest version                        |
| `--disable-plugin-autoload` | Prevent automatic loading of installed external plugins |
| `--import-mode`             | Control import semantics                                |
| `filterwarnings`            | Define warning-handling policy                          |

Combining explicit plugin loading with strict marker and configuration validation can reduce variability between development environments and CI installations.

It does not, however, freeze Python dependency versions, guarantee deterministic test ordering, or isolate external services. Those remain separate concerns.

### 13.4 Significant changes in the 9.x series

| Version | Notable released changes                                                                                           | Why they matter                                                         |
| ------- | ------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| 9.0     | Native TOML, built-in subtests, `capteesys`, broader exception-group integration                                   | Expands core testing and configuration capabilities                     |
| 9.1     | `pytest.register_fixture()`, warning-count limits, datetime/timedelta comparisons, fixture-precedence improvements | Extends plugin-generated fixtures and validation policies               |
| 9.2     | Parameter-ID strategies, stricter marker-expression validation, source-hash assertion cache                        | Improves collection identity, diagnostics, and configuration robustness |

Some compatibility considerations are especially relevant to advanced extension code:

- `yield_fixture` is deprecated in favor of `fixture`.
- Requesting a previously unrequested fixture through `request.getfixturevalue()` during teardown is deprecated in 9.1.
- `pytest.console_main()` is deprecated; conventional CLI invocation or `pytest.main()` is preferred according to context.
- Several implementation-specific interfaces under `_pytest` are private and are not equivalent to documented public extension APIs.
- Version 9.2 requires a sufficiently recent Pluggy release, so plugins and dependency constraints should be evaluated together.
- Changes described only in unreleased pytest 10.0 development notes should not be assumed available in 9.2.

For `--max-warnings`, exit code `6` applies when the test run would otherwise pass but its warning count exceeds the configured threshold; ordinary test failures retain their failure semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.pytest.org\&sz=32)

pytest documentation+3



Reference: `https://docs.pytest.org/en/stable/changelog.html`

## 14. Less obvious native diagnostics and failure detection

Several built-in behaviors are easy to overlook because they are not expressed as test decorators or fixture arguments.

### 14.1 Fault-handler integration

pytest integrates Python's `faulthandler` infrastructure to improve diagnostics for low-level process failures.

The `faulthandler_timeout` setting can trigger traceback dumps for tests that exceed a configured duration.

This is materially different from a timeout mechanism that stops or terminates a test.

A fault-handler traceback can help diagnose a hang; it does not provide the same execution-interruption or resource-recovery guarantees as a dedicated timeout strategy.

Reference: `https://docs.pytest.org/en/stable/how-to/failures.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 14.2 Unraisable and thread exceptions

pytest includes built-in detection of:

- Unraisable exceptions, such as exceptions occurring in destructors.
- Unhandled thread exceptions, which can otherwise terminate a background thread without directly failing the calling test.

The corresponding built-in plugins issue `PytestUnraisableExceptionWarning` and `PytestUnhandledThreadExceptionWarning`.

These warnings can become enforceable failure signals through suitable warning policies.

This expands testing coverage beyond exceptions that propagate directly through the test's call stack.

It is particularly valuable for code that starts threads, performs cleanup in finalizers, or uses background operations.

However, warning-based detection is not a guarantee that every asynchronous or cross-process failure is observed. Failures outside the relevant interpreter or after its reporting lifecycle may require additional instrumentation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 14.3 Current test identification and failure analysis

pytest exposes `PYTEST_CURRENT_TEST`, which identifies the currently executing test and phase.

This can be useful when investigating hung processes or correlating external diagnostics with pytest activity.

The project's official discussion of flaky tests also emphasizes that failures may originate from shared state, unjoined background threads, timing-sensitive assertions, or order dependencies.

pytest's own primitives are not universally thread-safe. In particular, it is unsafe to assume that concurrent threads can independently use testing primitives such as `pytest.raises()` and `pytest.warns()` without interference.

These limitations matter when tests themselves launch concurrent workloads, even if the pytest runner remains sequential.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



Reference: `https://docs.pytest.org/en/stable/explanation/flaky.html`

## 15. Architectural synthesis: what pytest can replace, and where its boundaries remain

The most consequential opportunities arise from composing pytest's native subsystems, not from using isolated API calls.

| Problem shape                             | Native mechanisms that compose                                         | Machinery potentially avoided                                |
| ----------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------ |
| Complex test resource provisioning        | Fixture dependency graph, scopes, yield cleanup, dynamic fixtures      | Bespoke setup registries and teardown orchestration          |
| Declarative case matrices                 | Parametrization, indirect fixtures, `pytest_generate_tests`, IDs       | Custom test-case enumeration and dispatch                    |
| Extensible validation formats             | Custom collectors, `pytest.Item`, runtime hooks, reporting hooks       | Entire custom test runners                                   |
| Context-dependent test environments       | Hierarchical fixtures, configuration, markers, `request`               | Duplicated environment-specific test implementations         |
| Rich failure diagnostics                  | Assertion rewriting, custom comparison hooks, capture, report sections | Repetitive custom assertion and exception-formatting code    |
| Instrumented execution                    | Lifecycle hooks, `pytest.StashKey`, structured reports                 | Ad hoc instrumentation wrappers and global state registries  |
| Incremental local feedback                | Last-failed cache, stepwise execution, duration reporting              | Simple bespoke failure-history tools                         |
| Structured CI reporting                   | Test reports, JUnit XML, report extension hooks                        | Basic result exporters and status summarizers                |
| Testing testing-infrastructure extensions | `pytester`                                                             | Repeated manual runner invocations and test-file scaffolding |

These are conditional architectural possibilities, not guarantees that pytest should replace every specialized system.

### 15.1 Resource lifetime is not isolation

Fixture scoping controls caching and cleanup, but does not create database transactions, sandboxes, separate processes, or isolated operating systems.

A session-scoped resource can be efficient while exposing tests to shared mutable state. A function-scoped resource can improve independence while multiplying construction cost.

Likewise, automatic cleanup cannot be assumed after abrupt process termination. pytest explicitly does not provide general fixture cleanup handling for signals such as `SIGTERM` or `SIGQUIT`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 15.2 Collection identity is not execution identity

A parametrized test generally produces multiple collected items, each with its own node ID.

A subtest produces runtime observations within a collected item.

Hypothesis may execute many generated examples within one pytest test invocation.

These mechanisms solve different problems. Their reporting, distribution, selection, and failure-reproduction semantics should not be treated as interchangeable.

### 15.3 Worker distribution is not automatic acceleration

Parallel workers can increase throughput for independent tests, but they add process startup, repeated collection, fixture duplication, and result-coordination costs.

For workloads dominated by expensive session initialization or external services with limited concurrency, increasing the worker count may reduce efficiency.

In contrast, suites dominated by independent CPU-bound tests or long-latency operations may benefit substantially from worker processes when the required resources permit concurrency.

These are mechanism-based expectations rather than general benchmark guarantees.

### 15.4 Plugins are powerful but affect the entire execution environment

A plugin can change collection, imports, fixtures, runtime execution, reporting, and CLI behavior.

That extensibility is one of pytest's strongest capabilities, but it also introduces interoperability risks.

Useful distinctions include whether a plugin modifies collection or execution, whether it is compatible with parallel workers, whether it expects particular fixture scopes, and whether it extends a public API or relies on internal `_pytest` implementation details.

The presence of multiple compatible plugins can make a small test suite highly capable; the presence of conflicting plugins can introduce failures before any test body runs.

### 15.5 pytest is not a general workflow engine

pytest has many workflow-like capabilities: dependency resolution, resource lifetimes, dispatch, structured outcomes, and persistence.

But its organizing abstraction is an executable test item within a collection-and-reporting lifecycle.

It does not natively provide durable arbitrary-task scheduling, transactional workflow recovery, distributed state management, comprehensive process isolation, or dependency-based incremental recomputation.

Those responsibilities belong to other systems or require explicit extensions.

The architectural value lies in recognizing which problems genuinely fit pytest's test-execution model—and using its native mechanisms to avoid rebuilding capabilities it already provides.

## 16. Primary documentation resource map

For deeper investigation, these are the most useful upstream entry points. All URLs are given directly for independent reuse.

| Topic                                | Primary documentation                                                  |
| ------------------------------------ | ---------------------------------------------------------------------- |
| Complete API and hook reference      | `https://docs.pytest.org/en/stable/reference/reference.html`           |
| Architecture, fixtures, and ordering | `https://docs.pytest.org/en/stable/reference/fixtures.html`            |
| Collection and custom test formats   | `https://docs.pytest.org/en/stable/example/nonpython.html`             |
| Parametrization and generation       | `https://docs.pytest.org/en/stable/how-to/parametrize.html`            |
| Assertion mechanisms                 | `https://docs.pytest.org/en/stable/how-to/assert.html`                 |
| Hook authoring                       | `https://docs.pytest.org/en/stable/how-to/writing_hook_functions.html` |
| Plugin authoring and testing         | `https://docs.pytest.org/en/stable/how-to/writing_plugins.html`        |
| Configuration reference              | `https://docs.pytest.org/en/stable/reference/customize.html`           |
| Result reporting                     | `https://docs.pytest.org/en/stable/how-to/output.html`                 |
| Cache and incremental execution      | `https://docs.pytest.org/en/stable/how-to/cache.html`                  |
| Official release notes               | `https://docs.pytest.org/en/stable/changelog.html`                     |
| Parallel scheduling                  | `https://pytest-xdist.readthedocs.io/en/stable/distribution.html`      |
| Asynchronous testing                 | `https://pytest-asyncio.readthedocs.io/en/stable/`                     |
| Multi-backend asynchronous testing   | `https://anyio.readthedocs.io/en/latest/testing.html`                  |
| Source code and implementation       | `https://github.com/pytest-dev/pytest/tree/9.2.0`                      |

### Overall assessment

pytest's most distinctive technical contribution is the combination of structured test collection, graph-based fixture resolution, extensible lifecycle protocols, assertion rewriting, and standardized reporting.

Its less obvious capabilities—custom collectors, hook wrappers, typed plugin state, dynamically registered fixtures, collection-time generation, runtime subtests, and test infrastructure testing through `pytester`—make it substantially more expressive than a conventional unit-test runner.

The important boundaries are equally clear: core pytest is sequential, asynchronous and distributed execution depend on distinct integrations, fixture scope does not guarantee isolation, and not every execution model preserves the same test identity or reporting semantics.

Understanding these distinctions allows pytest to serve as a powerful foundation for sophisticated validation systems while retaining the simplicity of ordinary Python tests.

# pytest 9.2.0 — Advanced Capabilities Addendum

Research date: November 6, 2026 | Target: pytest 9.2.0 (stable, released October 27, 2026) | Scope: Additional capabilities, technical distinctions, and corrections to the original overview

This addendum supplements the original pytest reference with capabilities identified during the subsequent gap analysis. It concentrates on functionality not previously covered, or functionality whose architectural significance deserves additional explanation.

The principal additions concern test-generation integrity, advanced collection controls, programmatic execution outcomes, plugin configuration contracts, cross-plugin extensibility, diagnostics, fault handling, and specialized testing integrations.

All core capabilities described below are available in pytest 9.2.0 unless otherwise specified. Companion-plugin functionality is identified separately.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



## 1. Test-generation integrity and strict execution policies

### 1.1 Strict parametrization identifiers

pytest normally tolerates repeated parametrized test identifiers by modifying duplicates to make them unique. For example, two cases explicitly assigned the ID `backend-a` may become `backend-a0` and `backend-a1`.

The `strict_parametrization_ids` configuration option changes this from a name-resolution behavior into a validation error:

```
[tool.pytest]
strict_parametrization_ids = true
```

When enabled, duplicate parameter-set IDs produce a collection error rather than receiving automatically generated disambiguating suffixes.

This matters because pytest node identifiers are not merely display labels. They serve as identifiers for individual collected tests and are consumed by exact test selection, rerun mechanisms, distributed collection verification, and external reporting integrations.

For programmatically generated tests, strict identifier validation can expose several classes of problem:

- Two distinct generated cases have been assigned the same logical identity.
- A case generator has emitted the same case more than once.
- A supposedly unique source identifier is not unique in the resulting test matrix.
- An identifier-generation function has discarded distinguishing input information.

The last two examples are possible implications rather than behaviors diagnosed automatically by pytest: pytest detects ID collisions, not the underlying cause.

This feature is especially relevant when `pytest_generate_tests` builds cases from structured metadata, where deterministic case identity can be as important as the assertions themselves.

Boundary: Unique parameter IDs do not guarantee that the generated test inputs are unique. Two cases with different IDs can still exercise identical inputs, and changes to generated IDs can affect test selection and historical result matching.

Source: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 1.2 Empty parameter sets as explicit execution policy

Dynamic parametrization introduces a subtle problem: what should happen when a generator produces no cases?

pytest exposes `empty_parameter_set_mark`, which defines the outcome of an empty parametrization.

| Value             | Behavior                                               |
| ----------------- | ------------------------------------------------------ |
| `skip`            | Generate a skipped test; the default                   |
| `xfail`           | Generate an expected-failure test that is not executed |
| `fail_at_collect` | Raise an error during collection                       |

For example:

```
[tool.pytest]
empty_parameter_set_mark = "fail_at_collect"
```

An empty test matrix can have fundamentally different meanings depending on the operation being validated.

For optional-backend compatibility testing, zero generated cases might be legitimate because no applicable backend is installed.

For schema-conformance testing, generating zero cases might indicate a broken specification loader, unexpectedly filtered inputs, or missing test metadata.

The same parametrization mechanism supports either interpretation, while `empty_parameter_set_mark` makes the policy explicit.

The default is currently `skip`. The upstream documentation notes that changing this default to `xfail` has been considered for a future release, but that is not the released behavior in pytest 9.2.0.

Architectural significance: This mechanism separates test generation from the decision about whether an empty generated set represents a valid absence of work. It can eliminate bespoke empty-input checks in collection-time generation code where a global policy is sufficient.

Source: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 1.3 Unified strict mode

pytest's `strict` configuration combines four independent policies:

| Option                       | Validation behavior                                                          |
| ---------------------------- | ---------------------------------------------------------------------------- |
| `strict_config`              | Reject unrecognized configuration options                                    |
| `strict_markers`             | Reject unregistered markers, including marker names in selection expressions |
| `strict_parametrization_ids` | Reject duplicate parametrization IDs                                         |
| `strict_xfail`               | Treat unexpectedly passing expected-failure tests as failures                |

These can be enabled collectively:

```
[tool.pytest]
strict = true
```

Individual strictness settings can also be configured separately, including overrides of the collective setting.

Together, they form a lightweight validation layer around the test suite itself. In addition to testing application behavior, pytest can enforce selected invariants of the test definitions, configuration, and expected-failure declarations.

This is valuable because mistakes in testing infrastructure can otherwise generate misleading results: a misspelled marker can alter test selection, a duplicate ID can destabilize case identity, and a non-strict expected failure can remain unnoticed after the underlying behavior changes.

Strict mode should not be confused with an exhaustive specification validator. It does not establish that all intended cases have been generated, all dependencies are isolated, or every requirement has been tested.

Reference: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 1.4 Parametrization signature changes in 9.2

pytest 9.2 made `indirect`, `ids`, and `scope` keyword-only arguments of `Metafunc.parametrize()` and the corresponding parametrization interface.

Correct:

```
metafunc.parametrize(    "backend",    ["sqlite", "postgres"],    indirect=True,    ids=["local", "server"],)
```

This change prevents positional-argument mistakes from being interpreted as fixture-indirection or identifier definitions.

For generated test infrastructure, it strengthens the API's argument contract and provides clearer errors for malformed parametrization calls.

The change is a released backward-incompatible change, not merely a typing annotation improvement. Earlier Python code that passed those arguments positionally requires adjustment for pytest 9.2.

Source: `https://docs.pytest.org/en/stable/changelog.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



## 2. Advanced collection and discovery controls

pytest's collection machinery is configurable beyond its default filename and function naming patterns. Several options alter which objects become tests, how collection errors are handled, and which filesystem or package boundaries apply.

### 2.1 Controlling imported-object collection

By default, pytest can collect objects imported into a test module if those objects match the configured test naming conventions.

Consider:

```
# domain.pyclass TestHarness:    pass# test_system.pyfrom domain import TestHarnessdef test_system():    assert True
```

Depending on its structure and eligibility, the imported class may be considered during discovery even though it was not defined in the test module.

The `collect_imported_tests` option, added in pytest 8.4, provides a more explicit definition boundary:

```
[tool.pytest]
collect_imported_tests = false
```

With this setting, pytest collects Python test classes and functions only when defined in the corresponding test file, rather than also collecting imported definitions.

This can reduce unintended collection, warnings about imported classes, and duplicated test discovery caused by reexported test objects.

It is particularly relevant when test modules import substantial amounts of application code or shared testing utilities.

Tradeoff: Some testing systems intentionally import reusable test classes or functions into multiple modules to generate additional instances of a common test suite. Disabling imported-object collection changes that behavior. It is therefore a semantic choice, not simply a performance option.

Reference: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 2.2 Filesystem, package, and naming policies

Several collection options are useful when the default Python discovery rules do not match the intended testing structure.

| Mechanism                     | Additional functionality                            | Important distinction                                                       |
| ----------------------------- | --------------------------------------------------- | --------------------------------------------------------------------------- |
| `python_files`                | Customize test module filename patterns             | Controls candidate files, not Python import semantics                       |
| `python_classes`              | Customize discoverable test class names             | Does not make unsupported class structures automatically valid test classes |
| `python_functions`            | Customize test function/method names                | Changes discovery policy without modifying test bodies                      |
| `testpaths`                   | Define default collection roots                     | Applies when no explicit test paths are supplied                            |
| `norecursedirs`               | Exclude directory patterns from recursive traversal | Affects discovery, not general file accessibility                           |
| `consider_namespace_packages` | Recognize native PEP 420 namespace packages         | Does not support legacy namespace-package mechanisms                        |
| `--collect-in-virtualenv`     | Include tests in virtual environment directories    | Overrides pytest's normal virtual-environment exclusion                     |
| `--confcutdir`                | Limit ancestor `conftest.py` discovery              | Changes fixture and hook availability                                       |
| `--noconftest`                | Disable `conftest.py` loading                       | Removes locally supplied configuration plugins and fixtures                 |

`consider_namespace_packages` is particularly relevant to packages distributed across multiple filesystem locations. It is disabled by default, and the documentation recommends making namespace packages importable—typically by installing them—when this setting is enabled.

The significance of `--confcutdir` and `--noconftest` extends beyond discovery: since `conftest.py` files supply fixtures and hook implementations, these options can change the execution environment even when the same test modules are collected.

Sources:

`https://docs.pytest.org/en/stable/example/pythoncollection.html`

`https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+2



### 2.3 Handling partial collection failures

Normally, collection errors prevent the collected tests from being executed. `--continue-on-collection-errors` allows tests that were collected successfully to execute despite errors elsewhere in collection.

This provides a distinction between collection completeness and execution eligibility.

For a testing system assembled from independently collected packages, schemas, or generated manifests, a failure in one collector need not prevent all other collectors' tests from running.

The overall invocation still reports the collection error; this option does not convert an incomplete collection into a successful test session.

`--keep-duplicates` addresses a separate issue: pytest ordinarily removes duplicate test items arising from overlapping explicit collection targets. Preserving duplicates can be useful when repeated invocation of the same test is intentional, although repeated execution should not be mistaken for additional test coverage.

Reference: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 2.4 Collection mutation and deselection correctness

A custom plugin may filter or reorder collected items through `pytest_collection_modifyitems`.

However, removing items from the collection list is not sufficient to implement well-integrated deselection.

When an extension removes items, pytest's public hook documentation requires it to notify other plugins through `pytest_deselected`:

```
def pytest_collection_modifyitems(config, items):    deselected = [        item        for item in items        if item.get_closest_marker("exclude_from_run")    ]    if deselected:        items[:] = [            item for item in items if item not in deselected        ]        config.hook.pytest_deselected(items=deselected)
```

Illustrative implementation.

This allows reporting plugins and other extensions to distinguish tests intentionally deselected from tests never discovered.

A consequential scope detail is that `pytest_collection_modifyitems` receives the complete item list even when implemented in a local `conftest.py`. It is not restricted to descendants of that file's directory.

A collection-modifying extension therefore needs to establish any intended locality itself.

This illustrates a general property of pytest extension points: hook dispatch scope and the scope of the data passed to a hook are not always identical.

Source: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



## 3. Imperative execution outcomes and optional dependencies

pytest's declarative markers cover conditions known when tests are defined or collected. Its imperative APIs provide corresponding control when eligibility, failure information, or execution policy becomes known only at runtime.

### 3.1 Runtime failure, skip, and expected-failure signaling

| API                                         | Effect                                                 | Primary use                                           |
| ------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------------- |
| `pytest.fail(reason, pytrace=True)`         | Immediately fail the current test                      | Explicit validation failure with a diagnostic message |
| `pytest.fail(..., pytrace=False)`           | Fail without presenting a Python traceback             | Already-complete domain-specific failure reports      |
| `pytest.skip(reason)`                       | Skip an executing test                                 | Runtime-determined inapplicability                    |
| `pytest.skip(..., allow_module_level=True)` | Skip an entire test module during collection           | Module-wide eligibility conditions                    |
| `pytest.xfail(reason)`                      | Immediately terminate execution as an expected failure | Runtime-discovered known failure condition            |
| `pytest.exit(reason, returncode=...)`       | Exit the pytest session                                | Session-wide unrecoverable conditions                 |

These functions raise pytest-specific control exceptions internally; they do not ordinarily return to the calling test code.

For example:

```
def test_validation(specification):    result = validate(specification)    if not result.is_valid:        pytest.fail(            result.explanation,            pytrace=False,        )
```

Illustrative example.

This can be more expressive than a plain Boolean assertion when a validator produces a detailed explanation independently of the Python call stack.

There is an important distinction between `pytest.fail()` and `pytest.exit()`: the former describes an unsuccessful test; the latter terminates the session itself.

Similarly, an imperative `pytest.xfail()` stops execution at that point. A declarative `@pytest.mark.xfail` generally allows the test to execute and then classifies its result.

`--runxfail` disables expected-failure treatment for a run, including the usual effect of imperative `pytest.xfail()`, so known failures can be examined as ordinary test failures.

Source: `https://docs.pytest.org/en/stable/how-to/skipping.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+2



### 3.2 Optional dependency handling with `pytest.importorskip`

`pytest.importorskip()` combines module import, optional version checking, and skip signaling:

```
backend = pytest.importorskip(    "optional_backend",    minversion="2.0",)
```

It returns the imported module when the required dependency is available and satisfies the specified minimum version.

This can express the eligibility of an optional integration test without separately implementing import exception handling, version checks, and pytest skip logic.

A significant change occurred in pytest 9.1.

The default `exc_type` is now `ModuleNotFoundError`, rather than broadly suppressing `ImportError`.

That distinction helps separate two situations:

- A dependency is unavailable, so an optional test can be skipped.
- A module exists but fails during import, potentially indicating a broken installation or implementation defect.

For compatibility with cases that deliberately treat any import error as unavailability, `exc_type=ImportError` remains available.

Limit: `ModuleNotFoundError` can also arise from a missing transitive dependency while importing an installed module. The narrower default is an improvement, not perfect identification of which package is absent.

Reference: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



## 4. Configuration contracts and plugin dependency management

### 4.1 Requiring plugins and validating their versions

Plugin discovery determines what pytest can load. The separate `required_plugins` configuration defines which plugin distributions must be available for a test session to proceed.

```
[tool.pytest]
required_plugins = [
    "pytest-xdist>=3.0",
    "pytest-cov",
]
```

Requirements can include distribution version specifiers.

If a required distribution is unavailable or does not satisfy the specified constraint, pytest reports a startup error.

This allows pytest configuration to express a test environment's required plugin dependencies without implementing a custom check in `pytest_configure`.

It is particularly useful when the testing semantics rely on specialized fixtures, markers, or hook implementations supplied by external distributions.

Important distinction: A required-plugin declaration is not a package installer or full environment lockfile. It checks the expected plugin distributions; it does not provision them, reproduce their dependencies, or independently guarantee compatible behavior among multiple plugins.

Reference: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 4.2 Suite-wide fixture activation through configuration

The `usefixtures` configuration option can apply specified fixtures to all test functions.

```
[tool.pytest]
usefixtures = ["validate_environment"]
```

This is semantically equivalent to applying a `usefixtures` marker across the test suite.

It makes a useful distinction between resource visibility and automatic activation. A fixture can be available globally without executing for every test; configuration-level `usefixtures` explicitly requests it.

Compared with an autouse fixture, this centralizes the activation decision in pytest configuration. It does not require every test signature to declare the resource.

Possible uses include a global environment precondition, test instrumentation, or a mandatory validation fixture whose result is not consumed directly.

The cost is correspondingly global: an expensive function-scoped fixture activated this way can add setup work to every test.

Also, `usefixtures` markers applied dynamically through hooks must be attached before test setup to influence fixture resolution. Applying them to fixture definitions themselves has no effect.

Source: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 4.3 Typed configuration declarations through `Parser.addini`

pytest plugins can define configuration options using `pytest_addoption` and `parser.addini()`.

In version 9.2, `parser.addini()` gained support for Python type expressions in addition to its historical string-valued type descriptors.

Supported declarations include:

- Scalar types: `str`, `bool`, `int`, `float`.
- Enumerated strings: `Literal["fast", "thorough"]`.
- Unions: `int | str`, `int | Literal["auto"]`.
- Historical descriptors such as `"args"`, `"linelist"`, `"paths"`, and `"pathlist"`.

A plugin can therefore declare its allowed configuration domain:

```
from typing import Literaldef pytest_addoption(parser):    parser.addini(        "validation_mode",        "Validation depth",        type=Literal["quick", "full"],        default="quick",    )    parser.addini(        "execution_budget",        "Maximum execution budget",        type=int,        default=100,    )
```

Illustrative plugin registration.

These values can be retrieved from pytest's `Config` object using `config.getini()`.

Invalid values can be rejected during configuration processing, rather than producing unrelated errors later during test execution.

This has an important compositional benefit: a plugin can use the same typed settings when generating tests, registering fixtures, configuring execution hooks, and producing reports.

Version 9.2 also upgraded several built-in settings to declare their accepted values explicitly, including `empty_parameter_set_mark`, `assertion_text_diff_style`, and JUnit reporting settings.

Boundary: Typed ini declarations are not a general constraint solver. Relationships between settings—such as one option being valid only when another is enabled—still require explicit validation.

Source: `https://docs.pytest.org/en/stable/changelog.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 4.4 Plugin identity and registration changes in 9.2

There are several ways to identify and load plugins:

- Importable Python module names.
- Installed `pytest11` entry-point names.
- Explicit `-p` CLI options.
- `pytest_plugins` module declarations.
- The `PYTEST_PLUGINS` environment variable.

As of pytest 9.2, `pytest_plugins` and `PYTEST_PLUGINS` can accept installed plugin entry-point names as well as importable module names.

This aligns them more closely with the behavior of `-p`, reducing the need for callers to know a distribution's internal import-module name.

The 9.2 series also improved capture and reporting of warnings emitted during plugin imports, which can make startup issues more visible to the ordinary pytest warning infrastructure.

These improvements do not eliminate plugin initialization-order constraints: not every hook implementation is available during early argument parsing.

Source: `https://docs.pytest.org/en/stable/changelog.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



## 5. Deeper Pluggy extension mechanisms

### 5.1 Optional hooks and extension discovery

A pytest plugin is not required to depend on every other plugin whose hooks it can implement.

Pluggy supports `optionalhook=True`, which permits registration of a hook implementation even when the corresponding hook specification is not currently available.

For example, a plugin may provide:

```
import pytest@pytest.hookimpl(optionalhook=True)def pytest_testnodedown(node, error):    # This hook belongs to pytest-xdist.    ...
```

If pytest-xdist is present and defines the hook, the implementation can participate. If xdist is unavailable, the optional implementation need not cause hook-specification validation to fail.

Another documented approach is to defer registration of the integration object until the companion plugin has been detected using `config.pluginmanager.hasplugin()`.

This permits plugin functionality to be decomposed into independent integrations without requiring every dependency to be installed.

There are important limits:

- Optional hook registration does not install or activate a missing plugin.
- The exact registered hook specification still determines the implementation's accepted arguments and result semantics.
- Hook availability during early initialization depends on plugin loading order.
- In pytest, hook implementations must still use function names beginning with `pytest_`, even if `specname` specifies another hook name.

This functionality is supplied by Pluggy and exposed through pytest's plugin infrastructure.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pluggy.readthedocs.io\&sz=32)

pluggy.readthedocs.io+1



### 5.2 Multiple implementations through `specname`

Ordinarily, pytest associates a hook implementation with a specification using the Python function's name.

`@pytest.hookimpl(specname=...)` allows a differently named function to implement an existing hook.

```
import pytest@pytest.hookimpl(    specname="pytest_collection_modifyitems",    tryfirst=True,)def pytest_collection_modifyitems_annotate(items):    for item in items:        # Add metadata or perform early collection processing.        ...
```

The implementation can have a unique Python function name while still participating in `pytest_collection_modifyitems`.

This makes it possible to register multiple implementations of a hook from the same module or plugin object without introducing a separate wrapper class solely to avoid Python name collisions.

Each implementation retains its own ordering and wrapper configuration.

This is particularly useful when one plugin has logically independent concerns—such as test annotation, policy enforcement, and selection—that participate in the same hook lifecycle.

The benefit is not merely organization. Independently registered implementations participate directly in Pluggy's ordering and dispatch semantics rather than being manually chained inside one large function.

Reference: `https://pluggy.readthedocs.io/en/stable/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pluggy.readthedocs.io\&sz=32)

pluggy.readthedocs.io



### 5.3 Old-style versus new-style hook wrappers

Pluggy supports two wrapper interfaces that are interoperable but have meaningfully different error and result semantics.

| Characteristic                      | New-style wrapper                     | Old-style wrapper                         |
| ----------------------------------- | ------------------------------------- | ----------------------------------------- |
| Declaration                         | `wrapper=True`                        | `hookwrapper=True`                        |
| Value received at `yield`           | Underlying result                     | `pluggy.Result` object                    |
| Exception handling                  | Ordinary Python exception propagation | Result object inspection and modification |
| Replace result                      | `return replacement`                  | `outcome.force_result(replacement)`       |
| Replace exception                   | Raise an exception                    | `outcome.force_exception(exception)`      |
| Recommended for new implementations | Yes                                   | Primarily for older Pluggy compatibility  |

New-style wrappers were introduced in Pluggy 1.1.

Old-style wrappers remain supported and can interoperate with newer wrappers. However, their control-flow mechanisms differ: old-style wrappers should not raise exceptions directly as a means of changing hook outcomes, because doing so can interfere with subsequent wrappers.

This distinction matters when reading or extending older pytest plugins. A generator-based hook implementation cannot be understood correctly without knowing which wrapper interface it uses.

The ability to compose wrappers around ordinary hook implementations is also useful for cross-cutting instrumentation. A plugin can observe or modify a hook's behavior without directly editing the other plugin's implementation.

Reference: `https://pluggy.readthedocs.io/en/stable/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pluggy.readthedocs.io\&sz=32)

pluggy.readthedocs.io



### 5.4 Programmatic fixture registration: visibility and lifecycle

`pytest.register_fixture()` was added in pytest 9.1 to support dynamically defined fixtures.

The complete interface in pytest 9.2 is:

```
pytest.register_fixture(    *,    name,    func,    node,    scope="function",    params=None,    ids=None,    autouse=False,)
```

Unlike a decorator attached to a fixture function, this interface registers an implementation explicitly and binds its visibility to a collector node.

For example, a registration made with `node=session` is visible globally. A registration associated with a particular directory or module collector is available only to tests descending from that node in the collection tree.

This establishes two independent aspects of fixture behavior:

- Visibility: Which collected items can resolve the fixture.
- Lifetime: How long pytest caches the constructed fixture value, as determined by `scope`.

The `params`, `ids`, and `autouse` arguments preserve important behavior from declaratively registered fixtures.

The interface therefore supports generated fixture providers, collection-dependent resource definitions, and selectively visible fixture implementations.

Lifecycle restriction: Registration is officially supported during collection. pytest does not enforce that restriction completely, but registrations made later are outside the documented guarantees.

The related 9.1 change to fixture override precedence reinforces the collection-tree model: a fixture registered for a more specific node takes precedence over a fixture of the same name registered for a broader node, regardless of registration order. Non-comparable scopes or identical visibility retain other precedence rules.

This creates a richer foundation for dynamically registered test dependencies while keeping resource resolution tied to collection structure.

Source: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



### 5.5 Collection-tree introspection and metadata operations

pytest's node objects expose useful operations beyond their identifiers and parent relationships.

| API                             | Functionality                                           |
| ------------------------------- | ------------------------------------------------------- |
| `node.iter_parents()`           | Traverse ancestors, beginning with the current node     |
| `node.listchain()`              | Obtain collection ancestry from root to node            |
| `node.getparent(type)`          | Find the nearest ancestor of a specified collector type |
| `node.iter_markers(name=None)`  | Examine effective marker metadata                       |
| `node.iter_markers_with_node()` | Identify both markers and the nodes that supplied them  |
| `node.get_closest_marker()`     | Resolve the nearest applicable marker                   |
| `node.add_marker()`             | Attach marker metadata dynamically                      |
| `request.applymarker()`         | Attach marker metadata through a fixture request        |
| `request.raiseerror()`          | Raise a fixture lookup error with a custom explanation  |

`iter_markers_with_node()` is particularly useful when marker inheritance matters.

For example, a marker associated with a test function may express an explicit test-specific configuration, while the same marker on an enclosing class or module may provide a default. The iterator preserves information about where each marker originated.

`request.applymarker()` is distinct from applying a decorator at definition time: it modifies metadata on the requesting node during fixture execution.

However, markers added at runtime cannot retroactively change collection-time selection or fixture setup that has already occurred.

This is an important distinction between using markers as declarative input to collection and using them as metadata produced during runtime.

Reference: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



## 6. Advanced reporting, observability, and diagnostics

### 6.1 Collection events, test events, and warning events

pytest's hook system can expose execution at a finer granularity than complete test results.

| Hook                             | Additional information or control                         |
| -------------------------------- | --------------------------------------------------------- |
| `pytest_collectreport`           | Receive collection results, including collection failures |
| `pytest_deselected`              | Observe items removed from the execution set              |
| `pytest_report_collectionfinish` | Add information after successful collection               |
| `pytest_runtest_logstart`        | Observe the beginning of an item execution                |
| `pytest_runtest_logfinish`       | Observe completion of the item's execution protocol       |
| `pytest_runtest_logreport`       | Receive phase-specific test reports                       |
| `pytest_warning_recorded`        | Observe warnings with phase and node context              |
| `pytest_exception_interact`      | Interact with exceptions during test execution            |
| `pytest_report_header`           | Contribute session-level diagnostic information           |

`pytest_warning_recorded` is especially useful for structured warning analysis.

It receives a `warnings.WarningMessage`, a phase identifier (`config`, `collect`, or `runtest`), a node ID when available, and optional source-location information.

A reporting extension can distinguish warnings emitted while loading configuration from warnings during collection or while executing a test.

This provides a better basis for diagnostic attribution than treating every warning as unstructured text in a terminal summary.

The `pytest_runtest_logstart` and `pytest_runtest_logfinish` hooks can similarly delimit item execution, whereas `pytest_runtest_logreport` receives the individual setup, call, and teardown reports.

The difference allows an observer to distinguish whole-item execution duration from individual phase results and associated diagnostics.

Boundary: These are in-process hooks. Plugins requiring distributed event collection, durable telemetry, or cross-run correlation must implement the relevant transport and persistence themselves.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+2



### 6.2 Attaching structured diagnostic sections

`pytest.Item.add_report_section(when, key, content)` appends a named diagnostic section to an item report.

Its parameters identify:

| Parameter | Meaning                        |
| --------- | ------------------------------ |
| `when`    | `setup`, `call`, or `teardown` |
| `key`     | Diagnostic section name        |
| `content` | Textual diagnostic content     |

This can associate supplementary explanations, validation traces, external process output, or other diagnostic artifacts with the test result.

The mechanism complements output and logging capture. Whereas capture records selected streams automatically, custom report sections allow a plugin to attach domain-specific information directly to the appropriate execution phase.

A notable limitation is that the section content is text. Although a plugin can serialize structured data into that content, report sections are not themselves a universal schema for arbitrary binary artifacts or typed diagnostic objects.

Reference: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 6.3 Fine-grained assertion presentation

pytest provides controls for large and complex assertion output that are separate from general terminal verbosity.

| Configuration               | Behavior                                                               |
| --------------------------- | ---------------------------------------------------------------------- |
| `assertion_text_diff_style` | Choose `ndiff` or `block` presentation for string equality differences |
| `verbosity_assertions`      | Independently control assertion explanation verbosity                  |
| `verbosity_test_cases`      | Control test-case progress/reporting detail                            |
| `verbosity_subtests`        | Control subtest reporting detail                                       |
| `truncation_limit_lines`    | Limit assertion explanations by line count                             |
| `truncation_limit_chars`    | Limit explanations by character count                                  |

For example:

```
[tool.pytest]
assertion_text_diff_style = "block"
verbosity_assertions = 2
truncation_limit_lines = 20
truncation_limit_chars = 2000
```

The `block` diff style displays the compared strings in separate blocks rather than relying exclusively on inline difference markers.

This can make large multiline outputs easier to inspect.

An important environment-dependent behavior is that pytest automatically disables the normal assertion truncation limits when it detects a CI environment. Consequently, the same failed assertion may produce different amounts of output locally and in CI.

In version 9.2, pytest also improved large-diff processing by constructing comparison output lazily and limiting it to the truncation budget instead of formatting the entire difference first.

This can reduce wasted diagnostic work for large objects whose complete differences would not be displayed.

Plugin authors can access fine-grained verbosity settings using `config.get_verbosity()`, rather than relying only on a single global verbosity value.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+2



Reference: `https://docs.pytest.org/en/stable/how-to/output.html`

### 6.4 Debugger and output-capture integration

pytest integrates with both `pdb.set_trace()` and Python's built-in `breakpoint()`.

During interactive debugging, pytest suspends capture for the relevant test so debugger interaction is visible. Capture resumes when execution continues.

The `--pdbcls` option allows a custom debugger class to be selected, while `--pdb` provides postmortem debugging after failures.

The distinction from simply invoking a debugger inside an ordinary Python program is that pytest manages capture, runner control flow, and failure reporting around the debugger session.

Python's `sys.last_type`, `sys.last_value`, and `sys.last_traceback` can also expose the most recent failure information for interactive inspection.

These facilities are complementary to pytest's report hooks. The former support interactive investigation; the latter enable programmatic observation and reporting.

Reference: `https://docs.pytest.org/en/stable/how-to/failures.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 6.5 Fault-handler timeouts can terminate the process

This section corrects an incomplete statement in the original overview.

pytest has a built-in integration with Python's `faulthandler`, and pytest 9.0 added `faulthandler_exit_on_timeout`.

```
[tool.pytest]
faulthandler_timeout = 120
faulthandler_exit_on_timeout = true
```

With only `faulthandler_timeout` set, pytest can dump thread tracebacks after a test exceeds the configured duration, including setup and teardown.

With `faulthandler_exit_on_timeout=true`, pytest passes `exit=True` to Python's `faulthandler.dump_traceback_later()`.

This causes process termination after the timeout and traceback dump.

| Mechanism                           | Outcome                                  | Cleanup implications                                           |
| ----------------------------------- | ---------------------------------------- | -------------------------------------------------------------- |
| `faulthandler_timeout`              | Diagnostic traceback dump                | Process continues; normal cleanup remains possible             |
| `faulthandler_exit_on_timeout=true` | Diagnostic dump followed by process exit | Abrupt termination; fixture cleanup cannot be relied upon      |
| Dedicated timeout plugin            | Depends on plugin timeout mode           | May interrupt execution differently; plugin-specific semantics |

This native capability can provide fail-fast behavior for hangs or deadlocks without a separate timeout plugin.

But it should not be considered equivalent to a recoverable per-test timeout. Python's faulthandler uses low-level termination behavior when `exit=True`, so ordinary Python exception handling, fixture finalization, and normal cleanup paths are not guaranteed to execute.

The choice is therefore between observing a hang while retaining the process, forcibly ending the process, and using a specialized timeout mechanism with different interruption guarantees.

Reference: `https://docs.pytest.org/en/stable/reference/reference.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



## 7. Compatibility, type safety, and legacy lifecycle support

### 7.1 Native xUnit-style setup and teardown

pytest supports traditional xUnit-style setup and teardown methods independently of its `unittest.TestCase` compatibility.

The recognized functions cover four levels of test organization.

| Level         | Setup            | Teardown            |
| ------------- | ---------------- | ------------------- |
| Module        | `setup_module`   | `teardown_module`   |
| Class         | `setup_class`    | `teardown_class`    |
| Test method   | `setup_method`   | `teardown_method`   |
| Test function | `setup_function` | `teardown_function` |

These mechanisms can coexist with pytest fixtures.

Since pytest 4.2, xUnit-style setup and teardown have been integrated with the fixture mechanism and observe the relevant fixture scope-ordering rules.

For example, a session-scoped autouse fixture can be initialized before a module's or class's xUnit-style preparation methods.

This matters because legacy and fixture-based test infrastructure do not necessarily operate as entirely separate execution systems.

However, teardown methods are not invoked if their corresponding setup method fails or skips. That behavior should be considered when xUnit methods own external resources.

The architectural distinction is between procedural lifecycle methods and declarative fixture dependencies.

xUnit-style methods organize preparation around test containers. Fixtures organize preparation around named resource dependencies and their scopes.

The latter provide more flexibility for composition, parametrization, and reuse, but the former remain valuable for compatibility with established testing code.

Reference: `https://docs.pytest.org/en/stable/how-to/xunit_setup.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 7.2 Typing fixture implementations and test functions

pytest's fixture injection model works with ordinary Python type annotations.

For example:

```
from collections.abc import Generatorimport pytest@pytest.fixturedef resource() -> Generator[Resource, None, None]:    instance = Resource()    yield instance    instance.close()def test_operation(resource: Resource) -> None:    assert resource.is_ready()
```

Illustrative example.

The distinction between the fixture function's type and the injected value is significant.

A yield fixture is implemented as a generator, but the test receives the yielded resource rather than the generator object.

Likewise, the type of a parametrized test argument is the actual parameter type, not the type of its collection-time parameter descriptor.

This allows ordinary Python static analysis to cover substantial portions of test code without requiring special fixture-specific typing syntax.

The limitation is that a type checker does not automatically prove pytest can resolve a particular fixture name at runtime. Fixture lookup and static Python type compatibility remain distinct concerns.

Reference: `https://docs.pytest.org/en/stable/explanation/types.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



### 7.3 Public types for plugin and test infrastructure development

Recent pytest versions have expanded their public type surface.

| Public type                        | Purpose                                                   |
| ---------------------------------- | --------------------------------------------------------- |
| `pytest.ScopeName`                 | Type annotation for supported fixture scope names         |
| `pytest.ParameterSet`              | Representation returned by `pytest.param()`               |
| `pytest.Approx`                    | Type of objects returned by `pytest.approx()`             |
| `pytest.Config`                    | Configuration and plugin access                           |
| `pytest.Metafunc`                  | Collection-time parametrization interface                 |
| `pytest.Item` / `pytest.Collector` | Test and collection object interfaces                     |
| `pytest.StashKey[T]`               | Typed key for plugin state associated with pytest objects |

`pytest.ScopeName` became public in pytest 9.1.

`pytest.ParameterSet` and `pytest.Approx` became publicly exposed in pytest 9.2, supporting annotations and runtime type checks.

This is especially useful for plugins that construct parameter sets, manipulate collection objects, or expose fixture registration interfaces.

For example, a function that generates a collection of `pytest.ParameterSet` objects can now express its output type without importing an internal `_pytest` implementation class.

The availability of public types does not imply that every internal object exposed through pytest is a stable extension API.

The distinction between documented public interfaces and private `_pytest` classes remains consequential for compatibility across major releases.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+1



Reference: `https://docs.pytest.org/en/stable/reference/reference.html`

### 7.4 Additional doctest controls

The original overview describes pytest's integration with Python's doctest engine. The following additional controls are useful when doctests form a substantial part of a test corpus.

| Option or mechanism              | Functionality                                             |
| -------------------------------- | --------------------------------------------------------- |
| `doctest_optionflags`            | Configure doctest's output-comparison rules               |
| `doctest_encoding`               | Specify the encoding used for doctest files               |
| `--doctest-report`               | Choose the format of doctest difference reports           |
| `--doctest-ignore-import-errors` | Ignore qualifying import errors during doctest collection |
| `--doctest-continue-on-failure`  | Continue evaluating later examples after a failed example |

`--doctest-continue-on-failure` is notable because it changes failure discovery within a sequence of examples.

Rather than stopping at the first failed expectation, pytest can continue evaluating later examples and report additional failures.

This can be useful for identifying multiple documentation regressions in one run, although subsequent examples may rely on state that was supposed to be established by earlier examples.

The doctest subsystem remains distinct from ordinary Python test parametrization and fixture execution.

Reference: `https://docs.pytest.org/en/stable/how-to/doctest.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation



## 8. Additional ecosystem capabilities

These capabilities are provided by companion libraries, not by pytest core. They are worth documenting because they substantially expand the classes of properties that can be validated using pytest's execution and reporting model.

### 8.1 Statistical performance benchmarking with pytest-benchmark

Companion package: pytest-benchmark | Verified documentation: 5.3.1

pytest's native `--durations` option reports how long tests took, but test durations are not equivalent to statistically controlled benchmarks.

pytest-benchmark provides a dedicated benchmark fixture, automatic calibration, repeated measurements, statistical summaries, and comparison against recorded benchmark results.

For example:

```
def test_algorithm(benchmark, dataset):    result = benchmark(run_algorithm, dataset)    assert result.is_valid
```

Illustrative example.

The fixture benchmarks the specified callable, allowing correctness assertions to remain outside the measured operation.

Important mechanisms include:

| Capability             | Functionality                                                    |
| ---------------------- | ---------------------------------------------------------------- |
| Automatic calibration  | Adjust execution rounds to obtain meaningful measurements        |
| Warmup controls        | Configure execution before measurement                           |
| `benchmark.pedantic()` | Provide more explicit control over iterations, rounds, and setup |
| Statistical output     | Report distributions of measured execution times                 |
| Saved results          | Persist benchmark measurements for later analysis                |
| Baseline comparison    | Compare recorded benchmark results across runs                   |
| Regression conditions  | Fail when configured performance constraints are exceeded        |
| `benchmark.extra_info` | Associate additional metadata with saved measurements            |

Version 5.3.0 introduced `--benchmark-precision` and `--benchmark-confidence`.

These enable measurement to continue until a specified relative margin-of-error criterion is reached, within the configured execution limits, rather than relying exclusively on a predetermined number of rounds.

This is useful when the variability or execution cost of a benchmark is not known in advance.

Important limitations

Performance benchmarking requires more control over the measurement environment than functional testing. CPU frequency variation, garbage collection, other processes, cache state, allocation behavior, and setup costs can materially affect results.

pytest-benchmark also automatically disables ordinary benchmarking when pytest-xdist is enabled, by design.

This reflects an important distinction: a scheduler intended to improve test throughput is not necessarily compatible with a measurement process intended to estimate individual operation latency.

Benchmarking performance and parallelizing functional tests solve different optimization problems.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-benchmark.readthedocs.io\&sz=32)

pytest-benchmark 5.3.1 documentation+1



Primary references:

`https://pytest-benchmark.readthedocs.io/en/stable/`

`https://pytest-benchmark.readthedocs.io/en/stable/usage.html`

`https://pytest-benchmark.readthedocs.io/en/stable/comparing.html`

### 8.2 Memory allocation and leak validation with pytest-memray

Companion package: pytest-memray, backed by Bloomberg Memray | Verified release series: 1.11

pytest-memray integrates Memray's allocation-tracing capabilities with pytest's test and reporting infrastructure.

Its functionality extends beyond displaying peak memory usage: it can turn selected memory properties into enforceable test conditions.

Three marker families are particularly significant.

| Marker                                  | Validation                                                                                |
| --------------------------------------- | ----------------------------------------------------------------------------------------- |
| `pytest.mark.limit_memory(...)`         | Fail if peak allocated memory exceeds a specified limit                                   |
| `pytest.mark.limit_leaks(...)`          | Fail when a call stack retains more allocated memory than allowed                         |
| `pytest.mark.limit_leaked_objects(...)` | Fail when tracked Python objects created during the test remain alive after the test body |

Example:

```
import pytest@pytest.mark.limit_memory("128 MB")def test_processing():    process_large_input()
```

Illustrative example.

`limit_leaks` performs more detailed leak analysis by grouping unreleased allocations according to their allocation call stacks.

The plugin can additionally track native allocation frames and Python allocator activity, although these modes can increase instrumentation overhead substantially.

A particularly interesting newer capability is `limit_leaked_objects`, introduced in pytest-memray 1.9.0.

It inspects objects created during execution that remain alive after the test body completes.

The documentation states that this requires Python 3.13.3 or newer; attempting to use the marker on older interpreters causes a collection error.

This provides a different validation model from checking the process's resident memory or peak allocation.

For example, it can help detect objects inadvertently retained in global registries, caches, or other long-lived references.

Limitations and interpretation

A retained allocation is not automatically a software defect.

Python's interpreter, standard library, and pytest itself maintain caches, captured output, and other state that can survive individual tests.

The plugin therefore supports filtering and tolerance thresholds for leak-oriented checks.

`limit_memory` and `limit_leaks` also support a `current_thread_only` option for restricting allocation tracking.

The plugin's `--fail-on-increase` option provides a separate regression-oriented mechanism, comparing memory behavior with prior successful executions for tests using the applicable memory marker.

These mechanisms offer opportunities for memory regression testing, but their results require interpretation in the context of allocator behavior and the measured execution scope.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-memray.readthedocs.io\&sz=32)

pytest-memray+2



Primary references:

`https://pytest-memray.readthedocs.io/en/stable/usage.html`

`https://pytest-memray.readthedocs.io/en/stable/configuration.html`

### 8.3 Snapshot and structured-output regression testing

Companion package: Syrupy | Stable release family: 6.x; 7.x marked unreleased in the project's documentation

Snapshot testing compares an observed result with a previously stored representation of an expected result.

This provides a mechanism for testing rich outputs whose complete expected structure may be cumbersome to encode directly in each assertion.

Syrupy supplies a pytest `snapshot` fixture, serialization facilities, snapshot persistence, output comparison, and controlled update behavior.

A typical assertion resembles:

```
def test_generated_structure(snapshot):    result = generate_structure()    assert result == snapshot
```

The plugin is more capable than a literal serialized-string comparison.

It supports:

- Custom snapshot extensions and serialization.
- Custom comparators and matchers.
- Selective normalization or replacement of dynamic fields.
- Snapshot updates and creation policies.
- Unused snapshot detection.
- Snapshot difference reporting.

A notable distinction is that Syrupy fails when a required snapshot does not exist, rather than silently accepting the current result as the baseline.

Snapshot-update commands are therefore explicit operations.

This is useful for generated structured data, configuration outputs, nested object models, and similar artifacts.

Parallel execution considerations

Syrupy's documented pytest-xdist support includes aggregation of snapshot usage information and coordinated snapshot updates.

However, concurrent updates use file locking and atomic replacement mechanisms with limitations on remote workers and network filesystems.

This matters because an apparently simple assertion may involve shared persistent snapshot state, and therefore have concurrency requirements beyond those of the test function itself.

Testing limitation

Snapshot equality establishes consistency with the stored baseline, not necessarily semantic correctness.

Snapshot testing is most informative when the baseline is meaningful, reviewed, and sufficiently stable. Large, frequently regenerated snapshots can obscure whether a change is desirable.

Reference: `https://syrupy-project.github.io/syrupy/`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://syrupy-project.github.io\&sz=32)

syrupy-project.github.io



### 8.4 Additional pytest-xdist execution controls

The original overview discusses pytest-xdist scheduling strategies but omits several controls that affect worker management and resilience.

| Mechanism                       | Additional functionality                                   |
| ------------------------------- | ---------------------------------------------------------- |
| `pytest_xdist_auto_num_workers` | Customize automatic worker-count selection                 |
| `PYTEST_XDIST_AUTO_NUM_WORKERS` | Supply a worker count through an environment variable      |
| `--maxprocesses`                | Limit the maximum worker count                             |
| `--max-worker-restart`          | Control the permitted number of worker restarts            |
| `--maxschedchunk`               | Control the scheduling chunk size under supported policies |

Worker crash recovery is particularly significant.

pytest-xdist can restart a worker that crashes, report the associated failure, and continue executing remaining tests, subject to its configured restart limit.

This can allow the rest of a large independent suite to complete even when a test triggers a process-level failure.

It does not, however, guarantee recovery of external resources or restoration of state mutated by the crashed worker.

Automatic worker-count selection is also extensible. A plugin can implement `pytest_xdist_auto_num_workers(config)` to determine a worker count from available information rather than relying exclusively on CPU detection.

That is useful when the relevant concurrency limit is something other than the number of CPUs, such as memory capacity or access to a constrained external resource.

The xdist hook takes precedence over its worker-count environment override.

Finally, xdist's `--looponfail` mode remains documented, but is deprecated. It should be treated as a compatibility feature rather than a recommended direction for new execution infrastructure.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+2



Reference: `https://pytest-xdist.readthedocs.io/en/stable/distribution.html`

### 8.5 Environment orchestration with tox and Nox

pytest-xdist parallelizes test execution across workers. It does not replace tools designed to create independent Python environments and execute test suites under different interpreter and dependency configurations.

Two widely used adjacent tools are:

| Tool         | Responsibility                                     | Distinction                                                                           |
| ------------ | -------------------------------------------------- | ------------------------------------------------------------------------------------- |
| tox          | Declarative environment provisioning and execution | Tests different package installations, Python versions, and dependency configurations |
| Nox          | Python-defined environment/session automation      | Provides programmable orchestration of environments and test commands                 |
| pytest       | Execution and reporting within an environment      | Manages collected tests and their fixture dependencies                                |
| pytest-xdist | Distribution within an execution environment       | Adds worker processes and scheduling                                                  |

The compositional model is straightforward: tox or Nox creates an environment, invokes pytest inside it, and pytest optionally delegates item execution to xdist.

This enables separate control over two forms of concurrency or variability:

- Environment-level variation: Different Python runtimes, dependency versions, installation configurations, or package builds.
- Test-level distribution: Parallel execution of tests within a particular environment.

The distinction matters because different workers running in the same pytest-xdist session generally share the surrounding installed environment, even though their processes and fixture caches are separate.

Conversely, different tox or Nox environments may execute the same test definitions under different dependency conditions.

These are complementary orchestration layers, not competing implementations of the same abstraction.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://tox.wiki\&sz=32)

tox.wiki+1



Primary references:

`https://tox.wiki/en/latest/`

`https://nox.thea.codes/en/stable/`

## 9. Additional operational and compatibility details

The following mechanisms require less explanatory depth but complete several remaining gaps.

| Capability                    | Additional behavior or consideration                                                                            |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `--setup-only`                | Execute fixture setup without running the test body; useful for separating preparation behavior from assertions |
| `--cache-show`                | Display persisted pytest cache contents, helping inspect cached failure history and plugin state                |
| `--runxfail`                  | Execute expected-failure tests without ordinary xfail classification                                            |
| `pytestconfig`                | Expose the session's `Config` object as a session-scoped fixture                                                |
| `config.getoption(skip=True)` | Skip when a requested CLI option is undeclared or has no value, subject to default handling                     |
| `pytest_markeval_namespace`   | Supply additional names for evaluating string expressions in `skipif` and `xfail` markers                       |
| `pytest.freeze_includes()`    | Expose module names for cx_Freeze packaging integration                                                         |
| `pytest --pyargs`             | Resolve test targets as importable packages, including supported namespace packages                             |

The most architecturally relevant of these is `pytest_markeval_namespace`.

It allows plugins to provide additional globals for string-based skip and expected-failure conditions. These values are used when evaluating the marker expressions during collection.

However, string-based marker conditions introduce dynamic evaluation and configuration dependencies that are absent from ordinary Boolean conditions. Where possible, explicit Python predicates are easier to analyze and maintain.

`config.getoption(skip=True)` is also useful when a test requires an externally supplied option. It can express the absence of the option as a skip without manually checking for `None` and calling `pytest.skip()`.

The option's declared default still matters: a default may be returned instead of producing a skip.

References:

`https://docs.pytest.org/en/stable/reference/reference.html`

`https://docs.pytest.org/en/stable/how-to/skipping.html`

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+2

## 10. Version and compatibility qualifications

A few additions merit explicit version boundaries because they affect plugin authors and test infrastructure that targets multiple pytest versions.

| Capability or change                             | Version | Compatibility consequence                                             |
| ------------------------------------------------ | ------- | --------------------------------------------------------------------- |
| `strict_parametrization_ids`                     | 9.0     | Duplicate IDs can become collection errors                            |
| `faulthandler_exit_on_timeout`                   | 9.0     | Native timeout-triggered process termination                          |
| `pytest.register_fixture()`                      | 9.1     | Public imperative registration during collection                      |
| `pytest.importorskip()` narrower default         | 9.1     | Default handling catches `ModuleNotFoundError`, not all `ImportError` |
| Public `pytest.ScopeName`                        | 9.1     | Supported scope annotations without private imports                   |
| Python type expressions in `Parser.addini()`     | 9.2     | More expressive configuration contracts                               |
| Keyword-only parametrization options             | 9.2     | Positional uses of `indirect`, `ids`, and `scope` are incompatible    |
| Public `pytest.ParameterSet` and `pytest.Approx` | 9.2     | Public typing and runtime type checks                                 |
| Plugin entry-point names in `pytest_plugins`     | 9.2     | Expanded plugin-loading compatibility                                 |
| Improved large assertion-diff handling           | 9.2     | Reduced unnecessary work preparing truncated differences              |

There are also changes affecting extensions that rely on older implementation details.

In pytest 9.2, the older `yield_fixture` decorator is scheduled for removal in pytest 10 or 11.

Fixtures with module, package, or session scope defined as instance methods are now deprecated, extending the earlier 9.1 deprecation affecting class-scoped instance-method fixtures.

Use of private fixture registration APIs and string-based node-prefix registration is also being phased out in favor of public interfaces and node-based visibility.

Additionally, the private `config.inicfg` attribute is deprecated; `config.getini()` is the appropriate public accessor.

These changes reinforce an architectural direction: fixture identity and visibility are increasingly represented using collection nodes, while plugin configuration and types are becoming more explicitly declared through public interfaces.

The upstream changelog includes pytest 10 development material, but planned removals are not treated as already completed in 9.2.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+2



Reference: `https://docs.pytest.org/en/stable/changelog.html`

## 11. Synthesis of the additional capabilities

This addendum extends the original reference in several consequential ways.

First, pytest provides mechanisms for validating the test system itself. Strict parametrization IDs, empty parameter-set policies, configuration validation, plugin requirements, and collection-error controls allow certain infrastructure mistakes to become explicit errors instead of silently altering execution.

Second, its extension architecture is more expressive than a simple hook registry. Optional hooks, named implementations, typed configuration declarations, collection-tree-aware fixture registration, and node metadata operations provide tools for building modular testing infrastructure without necessarily introducing separate registries, configuration parsers, or resource-dispatch machinery.

Third, pytest exposes a detailed diagnostic lifecycle. Plugins can observe collection and execution phases, attribute warnings, add report sections, and control failure presentation. Native fault handling can now terminate stalled test processes as well as produce diagnostic tracebacks.

Finally, the companion ecosystem expands what can be validated. pytest-benchmark introduces statistically managed performance measurements; pytest-memray supplies allocation and leak-oriented assertions; snapshot plugins support stored structural baselines; and orchestration tools complement pytest's own test-execution lifecycle.

These additions are best understood as extensions to the original conceptual model, not replacements for it. pytest remains a test collection, dependency, execution, and reporting framework. Its strength is that these native subsystems can be combined—and extended through documented contracts—to support substantially more sophisticated testing behavior than ordinary unit-test execution alone.