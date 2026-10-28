# Hypothesis — Comprehensive Python Library Capability Reference

Target: Hypothesis 6.170.12 · Research date: October 28, 2026 · Python · Property-based, stateful, differential, and generative testing

Hypothesis is a property-based testing framework that combines composable input generation, automated exploration, failure minimization, and reproducible regression discovery. Its capabilities extend well beyond conventional randomized testing: Hypothesis can generate structurally valid objects, recursive data, sequences of state-changing operations, numerical edge cases, and inputs satisfying complex relationships.

It also provides an increasingly extensible testing engine, with coverage-guided fuzzing, SMT-assisted input generation, persistent example databases, machine-readable execution observations, and integration with specialized scientific and application libraries.

Version 6.170.12 was published on October 26, 2026. The documentation also contains changes for 6.170.13 dated October 28; this reference targets the verified published 6.170.12 release and distinguishes companion packages and implementation-level extension points.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



Primary sources:

- Documentation: [https://hypothesis.readthedocs.io/en/latest/](https://hypothesis.readthedocs.io/en/latest/?utm_source=chatgpt.com)
- Source repository: [https://github.com/HypothesisWorks/hypothesis](https://github.com/HypothesisWorks/hypothesis?utm_source=chatgpt.com)
- Package releases: [https://pypi.org/project/hypothesis/](https://pypi.org/project/hypothesis/?utm_source=chatgpt.com)
- API reference: [https://hypothesis.readthedocs.io/en/latest/reference/api.html](https://hypothesis.readthedocs.io/en/latest/reference/api.html?utm_source=chatgpt.com)
- Strategy reference: [https://hypothesis.readthedocs.io/en/latest/reference/strategies.html](https://hypothesis.readthedocs.io/en/latest/reference/strategies.html?utm_source=chatgpt.com)

## 1. Conceptual architecture and capability map

The central abstraction is a `SearchStrategy[T]`, a composable description of how to generate values of type `T` and constrain their valid domain.

A strategy is not simply a random-value-producing callable. It participates in an execution engine that can generate examples, replay prior executions, simplify counterexamples, and interact with different generation backends.

| Capability                     | Principal mechanisms                                      | Architectural significance                                                    |
| ------------------------------ | --------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Property-based testing         | `@given`, `@example`, `find`                              | Exercise general behavioral properties over generated inputs                  |
| Domain modeling                | `st.*`, `map`, `flatmap`, `composite`, `recursive`        | Encode valid data structures and interdependent constraints                   |
| Failure minimization           | Conjecture engine, shrinking, example reuse               | Convert complex failures into small, interpretable reproductions              |
| Stateful testing               | `RuleBasedStateMachine`, `Bundle`, `rule`, `invariant`    | Explore sequences of operations and state transitions                         |
| Type-directed generation       | `from_type`, `builds`, `register_type_strategy`           | Generate objects from Python types and constructor signatures                 |
| Search optimization            | `target`, alternative generation backends                 | Direct exploration toward unusual or difficult behavior                       |
| Fuzzing and symbolic execution | HypoFuzz, CrossHair, `fuzz_one_input`                     | Combine structured data generation with other exploration engines             |
| Specialized data               | NumPy, pandas, Array API, Django, Lark                    | Generate domain-specific values without constructing every generator manually |
| Regression infrastructure      | Example databases, seeds, replay blobs                    | Reuse discovered failures across executions and environments                  |
| Observability and tooling      | `event`, `note`, pytest statistics, observation callbacks | Inspect generation quality, failures, and search-engine behavior              |

The execution model has three distinct layers:

1. Strategies define admissible inputs and their structure. They express constraints, dependencies, constructors, and relationships.
2. The engine explores the resulting search space. It combines generated choices, reuse, targeting, and shrinking.
3. Tests supply behavioral oracles. Assertions, exceptions, invariants, reference implementations, and metamorphic relationships determine correctness.

This separation is consequential: Hypothesis does not need to understand application semantics to generate and minimize counterexamples. Conversely, it cannot establish correctness without a meaningful property, oracle, or invariant.

A useful distinction is between ordinary randomized testing, which principally samples inputs, and Hypothesis testing, which integrates search, replay, structural constraints, and minimization. Hypothesis remains a testing system rather than a formal proof engine; bounded successful runs do not establish that a property holds universally.

## 2. Strategy system: modeling valid input spaces

Hypothesis's strategy algebra is one of its most valuable features. It allows generation to follow a domain's actual structural constraints instead of producing arbitrary data and subsequently discarding most of it.

### 2.1 Primitive, scalar, and structured generators

| Family                   | Important APIs and capabilities                                                                                                                          |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Numeric                  | `integers`, `floats`, `decimals`, `fractions`; bounds, excluded endpoints, NaN/infinity policies, subnormal floats, and selectable floating-point widths |
| Text and binary          | `text`, `characters`, `binary`, `from_regex`; Unicode categories, character exclusion, encodings, regular-expression constraints                         |
| Enumerated               | `sampled_from`, `one_of`, `just`, `none`, `nothing`; finite choices, alternatives, constants, empty domains                                              |
| Collections              | `lists`, `sets`, `frozensets`, `dictionaries`, `fixed_dictionaries`, `tuples`, `iterables`; size bounds, uniqueness, required/optional fields            |
| Temporal and identifiers | `dates`, `times`, `datetimes`, `timedeltas`, `timezones`, `uuids`, `ip_addresses`; timezone and daylight-saving behavior                                 |
| Functions and randomness | `functions`, `randoms`, `random_module`; generated callbacks and controlled pseudorandom state                                                           |

The important distinction is that these are semantic generators, not merely constructors for Python values.

For example, floating-point strategies can generate signed zero, very large and very small magnitudes, and different non-finite values. Testing an algorithm with `st.floats(width=32)` consequently explores a different representable numerical domain from testing with default Python double-precision floats.

Similarly, `st.from_regex()` generates matching strings but defaults to search semantics rather than an implicit full-string match; `fullmatch=True` is necessary when the entire string must satisfy the expression. Unicode strategies can exercise cases that ASCII-only test data misses, including unusual categories, normalization-sensitive strings, and complex encodings.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation+1



Collection constraints are structural. `lists(..., unique=True)` and `unique_by` can enforce uniqueness during generation; `fixed_dictionaries()` can model required and optional fields. These are generally more efficient and more informative than generating unconstrained collections and asserting afterward that their structure is acceptable.

Relevant reference: [https://hypothesis.readthedocs.io/en/latest/reference/strategies.html](https://hypothesis.readthedocs.io/en/latest/reference/strategies.html?utm_source=chatgpt.com)

### 2.2 Strategy composition and dependent generation

The following mechanisms solve different classes of input-modeling problems.

| Mechanism                   | What it expresses                                           | Important distinction                                                    |
| --------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------ |
| `map(f)`                    | Deterministic transformation of generated values            | May obscure the structure available to the shrinker                      |
| `flatmap(f)`                | A generated value determines a subsequent strategy          | Supports dependent dimensions and correlated fields                      |
| `filter(predicate)`         | Values satisfying a post-generation predicate               | Excessive rejection can make generation inefficient or unsatisfiable     |
| `@st.composite` / `draw()`  | Imperative, sequential construction of a structured example | Useful for several mutually dependent draws and domain validation        |
| `st.data()` / `data.draw()` | Draw more values during execution of the test itself        | Enables choices based on results observed from the system under test     |
| `st.recursive()`            | Recursively nested structures with bounded leaf complexity  | A natural model for ASTs, expressions, and nested documents              |
| `st.deferred()`             | Lazily defined or mutually recursive strategies             | Resolves circular strategy definitions                                   |
| `st.shared()`               | Reuses a generated value within one test execution          | Expresses identity or correlation, not persistence across separate tests |

The architectural distinctions matter more than the individual methods:

Constructive validity versus rejection. A strategy that generates a sorted sequence directly, or generates an index within a previously generated sequence length, makes valid inputs available by construction. A strategy that generates unrelated values and filters away invalid combinations can waste the test budget on rejected examples. Hypothesis optimizes some common filters, but arbitrary predicates do not automatically become efficient constraint solvers.

Generation-time dependency versus execution-time dependency. `flatmap()` and `@composite` express relationships already known while constructing an input. `st.data()` is different: it allows subsequent draws to depend on information discovered inside the test, such as the length of a response, available keys in a generated index, or the behavior of a parser. This supports adaptive tests without requiring separate, nested `@given` invocations.

Recursion as a first-class search structure. `recursive()` and `deferred()` can generate nested expressions, JSON-like values, syntax trees, and mutually recursive grammar objects. Because the recursive structure belongs to Hypothesis's search representation, shrinking can simplify both the tree's shape and its leaves. This is generally more useful than using an opaque generator that only returns fully materialized random trees.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation+2



### 2.3 Advanced generation mechanisms

Several less-obvious strategies expand what can be modeled without writing a custom engine.

`st.functions()` generates callable objects compatible with a specified signature and return-value strategy. It supports callback-oriented APIs and can generate async callables; its `pure=True` option models deterministic memoized responses for the same arguments, subject to its documented restrictions. Generated callables are intended for use during the active test execution, not as persistent fixtures.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation



`st.shared()` creates relationships between otherwise separate positions in a generated structure. It can represent two fields referencing the same conceptual entity, repeated identifiers, or shared parameters. Its sharing boundary is the individual test case; it is not an inter-test state registry.

`st.randoms()` and `st.random_module()` allow pseudorandom behavior itself to be brought under Hypothesis's control. This is particularly useful when a tested algorithm internally samples random numbers: Hypothesis can search over seeds or random behavior instead of leaving an uncontrolled source of nondeterminism. `register_random()` supports coordinated treatment of custom random-number generators, with lifecycle restrictions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation



`st.from_regex()` can generate strings satisfying supported regular-expression syntax. Complex assertions and lookarounds may require slower filtering or have restrictions; it is not a general-purpose grammar generator. For syntactically rich languages, the Lark integration discussed below supports a different modeling approach.

### 2.4 Type-directed generation and extensibility

Hypothesis also provides a type-based generation layer:

- `st.from_type(T)` resolves a strategy for Python types, `typing` constructs, unions, generic structures, and supported registered types.
- `st.builds(callable, ...)` constructs objects, using annotated required parameters where inference is possible.
- `st.register_type_strategy(T, strategy_or_resolver)` adds or overrides type-to-strategy mappings.
- `@given(parameter=...)`, `@given(parameter=infer)`, or `@given(...)` explicitly request generation from type annotations.

This creates a useful distinction between type-level validity and domain-level validity. A Python annotation such as `list[int]` defines a broad representation space; it does not encode sortedness, uniqueness, referential integrity, or other application invariants. Such constraints must come from a more specific registered strategy, a constructor, or explicit strategy composition.

`register_type_strategy()` may accept a resolver function for generic types; directly registering one specific parameterized generic is not the supported extension pattern. Registrations can influence multiple generation sites, so changing a globally registered strategy can also change unrelated tests' input distributions.

An important compatibility detail: `builds()` may infer missing annotated constructor arguments, whereas `@given` intentionally does not silently infer all test parameters, because some may be supplied by pytest fixtures. Inference must be requested explicitly.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation+1



Direct documentation: [https://hypothesis.readthedocs.io/en/latest/reference/strategies.html](https://hypothesis.readthedocs.io/en/latest/reference/strategies.html?utm_source=chatgpt.com)

Extension boundary: `SearchStrategy` is part of the supported public API for typing and composition, but its class is not intended to be subclassed or instantiated directly by third-party strategy authors. The supported route for custom domain generators is to compose strategies, typically with `@composite`, `flatmap()`, `builds()`, or a type-strategy registration. More advanced engine customization uses a separate, less stable interface.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.169.4 documentation



## 3. Search engine, shrinking, and execution control

### 3.1 The Conjecture execution model

Hypothesis uses its Conjecture engine to explore examples while retaining enough structure to reproduce and simplify them.

Conceptually, strategies request primitive choices from a provider. The engine tracks the resulting choice sequence, applies generation and mutation heuristics, and searches for an input that produces a test failure. Its shrinker subsequently attempts transformations that preserve the failure while simplifying the choice sequence.

This supports several forms of simplification simultaneously:

- Reducing the size of containers and recursive structures.
- Reducing integer magnitudes and simplifying floating-point values.
- Removing irrelevant operations from stateful traces.
- Simplifying strings, nested fields, and dependent selections.

The key advantage over printing a random seed is that a failure can often be expressed as a small, meaningful example. However, “minimal” is not a guarantee of the globally smallest possible counterexample under every ordering. Results depend on the represented search space, shrinking heuristics, test determinism, and available execution budget. The engine may also retain different failures when `report_multiple_bugs=True`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.12 documentation+1



The current architecture exposes five primitive choice categories to generation providers: booleans, integers, floats, strings, and bytes. This common representation is also why different generation backends can retain much of Hypothesis's shrinking and example-replay machinery.

Internal architecture: [https://hypothesis.readthedocs.io/en/latest/reference/internals.html](https://hypothesis.readthedocs.io/en/latest/reference/internals.html?utm_source=chatgpt.com)

### 3.2 Phases, search settings, and targeted testing

The `settings` object governs the testing lifecycle, not just the number of generated examples.

| Control               | Behavior                                                        |
| --------------------- | --------------------------------------------------------------- |
| `Phase.explicit`      | Execute fixed `@example` cases                                  |
| `Phase.reuse`         | Replay persisted examples                                       |
| `Phase.generate`      | Generate new test cases                                         |
| `Phase.target`        | Mutate cases toward desired numerical targets                   |
| `Phase.shrink`        | Minimize discovered failures                                    |
| `Phase.explain`       | Attempt additional failure explanations, on a best-effort basis |
| `max_examples`        | Limit the number of satisfying generated test cases             |
| `deadline`            | Detect unexpectedly slow test executions                        |
| `stateful_step_count` | Bound generated rule sequences                                  |
| `backend`             | Select the input-generation backend                             |

`hypothesis.target(observation, label=...)` is especially significant. Rather than treating every valid input as equally informative, it provides numerical feedback for directed search. Hypothesis attempts to maximize the reported finite value.

Relevant target metrics include floating-point error, resource usage, queue depth, compression ratio, iteration count, or a distance to a known pathological threshold. Multiple independent targets can be distinguished by labels.

Targeting composes with ordinary property tests: the test still supplies the correctness oracle, while the target metric influences which examples are explored. It is most compelling when the metric correlates with a failure mechanism. Poor metrics can instead consume effort exploring irrelevant extremes; the official documentation notes that targeting generally becomes more evident at substantially higher test budgets.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation



`assume(condition)` and `reject()` have a different role: they invalidate an example without indicating a defect in the tested implementation. A failing `assert` is an observed error; a failed `assume` means the generated example should not count as a valid case. Excessive rejection can exhaust generation, and health checks may identify it.

Settings reference: [https://hypothesis.readthedocs.io/en/latest/reference/api.html](https://hypothesis.readthedocs.io/en/latest/reference/api.html?utm_source=chatgpt.com)

### 3.3 Standalone predicate search

The exported `hypothesis.find(strategy, condition, ...)` searches for a value satisfying a predicate and returns a minimized result, rather than decorating a test. This is a valuable form of counterexample discovery or witness search when the desired outcome is a concrete object rather than a test report.

It is built on the same strategy and failure-search machinery. The source-defined defaults and search budget differ from an ordinary `@given` test, and failure to find a result is not proof that no satisfying value exists.

This API is confirmed in the upstream source, although it is not currently described alongside the main functions in the published API reference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



Source: [https://github.com/HypothesisWorks/hypothesis/blob/master/hypothesis/src/hypothesis/core.py](https://github.com/HypothesisWorks/hypothesis/blob/master/hypothesis/src/hypothesis/core.py?utm_source=chatgpt.com)

## 4. Stateful and model-based testing

`hypothesis.stateful` extends property-based testing from individual inputs to generated programs of operations. The framework selects actions, arguments, and execution order, then minimizes the sequence that causes a violation.

This is particularly powerful for protocols, databases, mutable data structures, caches, resource lifecycle management, and other systems where correctness depends on history rather than a single call.

### 4.1 Rule-based state-machine architecture

| Element                       | Role                                                                                       |
| ----------------------------- | ------------------------------------------------------------------------------------------ |
| `RuleBasedStateMachine`       | Encapsulates the evolving test state and available operations                              |
| `@rule(...)`                  | Declares an operation whose arguments are generated by strategies or selected from bundles |
| `Bundle(name)`                | Stores values produced by earlier rules for later reuse                                    |
| `target=` / `targets=`        | Captures a rule's output in one or multiple bundles                                        |
| `multiple(...)`               | Supplies multiple generated outputs from one rule                                          |
| `consumes(bundle)`            | Selects and removes a previously generated value                                           |
| `@initialize(...)`            | Runs initialization actions before normal rules                                            |
| `@precondition(...)`          | Enables a rule only when the current machine state permits it                              |
| `@invariant(...)`             | Checks a property after each state transition                                              |
| `teardown()`                  | Cleans up machine resources after the run                                                  |
| `run_state_machine_as_test()` | Runs a machine without relying on its generated unittest class                             |

Bundles are a distinguishing feature. They allow the engine to maintain a universe of generated resource identifiers, objects, references, or handles and feed those values into subsequent operations. A sequence can create an object, update that same object, delete it, and then attempt to access it again without repeatedly inventing unrelated identifiers.

The ability to consume bundle values is especially useful for linear-resource semantics such as closing handles, transferring ownership, removing queued work, or retiring tokens. `Bundle.filter()` and `Bundle.map()` compose with consumption, allowing more selective reuse.

By contrast, ordinary instance variables represent the machine's internal state but are not automatically drawable by rules. When an argument must be derived from arbitrary machine state, `st.runner().flatmap(...)` or `st.data()` can provide dynamic access.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation



### 4.2 Preconditions, initialization, and invariants

These mechanisms serve different purposes:

Preconditions determine whether an operation is currently legal. They prevent the engine from wasting steps on actions that cannot execute. They should not be confused with correctness assertions: an illegal operation may itself be worth testing as a separate rule with an expected rejection behavior.

Initialization establishes the starting state and can populate bundles. Multiple initializer methods each execute once, but their relative order is not guaranteed; they should not silently depend on a specific order.

Invariants establish what must remain true across transitions. These can check conservation laws, consistency between indexes, resource counts, referential integrity, or correspondence with a reference model.

A particularly valuable composition is model-based differential testing: maintain a simple reference model in the state machine, apply generated commands to both the model and the real implementation, and compare observable results after each relevant transition. The model need not replicate the implementation architecture; it needs to represent the externally promised semantics.

Stateful testing preserves Hypothesis's minimization advantage. If a failure originally required dozens of operations, the engine can often reduce it to a short reproduction containing only the necessary setup and actions. The resulting report is represented in Python-like rule invocations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation



### 4.3 Scope and limitations

The defaults are 100 state-machine examples and up to 50 rule steps per example, although settings and early failures change the actual executed count. These dimensions interact: increasing both can make the search substantially more expensive.

State-machine rules are not ordinary fixture-driven pytest functions. Fixture and parametrization injection into arbitrary rules is limited, and the machine owns its own per-run state. For a simple sequence with only a few dependent draws, an ordinary `@given` test using `st.data()` can be less complex than defining a state-machine class.

Concurrency scheduling is not automatically explored merely because operations are stateful. Testing races, interleavings, or asynchronous scheduling requires additional scheduling control or a specialized integration.

Documentation: [https://hypothesis.readthedocs.io/en/latest/stateful.html](https://hypothesis.readthedocs.io/en/latest/stateful.html?utm_source=chatgpt.com)

## 5. Persistence, regression reproduction, and shared example corpora

Hypothesis provides an example database abstraction that makes testing incremental across executions. Successful generation is useful, but preserving and replaying previously discovered failures can make subsequent runs much more effective.

### 5.1 Example database implementations

| Implementation                  | Capabilities and tradeoffs                                                       |
| ------------------------------- | -------------------------------------------------------------------------------- |
| `DirectoryBasedExampleDatabase` | Default local persistent storage under `.hypothesis/examples`                    |
| `InMemoryExampleDatabase`       | Ephemeral storage, useful for isolated execution or database testing             |
| `GitHubArtifactDatabase`        | Reads examples from GitHub Actions artifacts, supporting CI-to-developer reuse   |
| `ReadOnlyDatabase`              | Prevents writes or deletions against a backing store                             |
| `MultiplexedDatabase`           | Combines multiple databases for shared/local corpus access                       |
| `BackgroundWriteDatabase`       | Defers writes to a background thread, while fetches wait for pending writes      |
| `RedisExampleDatabase`          | Redis-backed shared example storage with configurable expiration                 |
| Custom `ExampleDatabase`        | Allows a specialized persistence system through the documented storage interface |

The abstract database exposes methods such as `save`, `fetch`, `delete`, and `move`, with change-listening support relevant to continuous fuzzing.

An important interaction is local and shared corpus composition. A read-only shared database can provide previously discovered cases, while a writable local database stores new cases. `MultiplexedDatabase` enables this arrangement without requiring the testing engine to understand the remote storage topology.

The artifact and Redis backends have distinct operational models: GitHub artifacts support published corpora associated with workflows; Redis supports a mutable, centrally accessible corpus. `BackgroundWriteDatabase` can reduce write overhead in high-volume exploration but is not a general-purpose nonblocking database abstraction, because reads may wait for pending writes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation+2



### 5.2 Replay mechanisms and their guarantees

| Mechanism                           | Best use                                                           | Persistence distinction                                                        |
| ----------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| Example database                    | Automatically replay previously interesting examples               | Encoded engine representation; not a stable domain-data interchange format     |
| `@example(...)`                     | Commit an explicit, human-readable regression case                 | Ordinary Python values; durable and visible in source                          |
| `@seed(...)`                        | Reproduce a particular random sequence under comparable conditions | Does not guarantee identical behavior across Hypothesis or environment changes |
| `settings.derandomize=True`         | Use test-derived deterministic generation                          | Suitable for repeatable CI, not equivalent to preserving a discovered input    |
| `@reproduce_failure(version, blob)` | Temporarily recreate a specific failure                            | Version-locked, intentionally unsuitable as a permanent regression artifact    |

`@example` has additional functionality that is easy to overlook: `.xfail(...)` can document an intentionally failing example, and `.via("origin")` attaches a machine-readable provenance label. The latter is useful for tools that generate or curate permanent regression cases.

Explicit examples do not shrink, and they do not count against `max_examples`. This is a useful separation between curated fixtures and exploratory generation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation



### 5.3 Built-in CI behavior

Hypothesis has distinct `default` and `ci` settings profiles. The built-in CI profile changes more than seeding:

| Setting                | Default profile                   | CI profile |
| ---------------------- | --------------------------------- | ---------- |
| `max_examples`         | 100                               | 100        |
| `derandomize`          | `False`                           | `True`     |
| `deadline`             | 200 ms                            | Disabled   |
| `database`             | Local example database by default | `None`     |
| `print_blob`           | `False`                           | `True`     |
| Slow-test health check | Enabled                           | Suppressed |

The crucial consequence is that the built-in CI profile disables persistent example storage. A shared CI corpus requires deliberately configuring a database or registering a revised profile. This should not be confused with the separate ability to share failures through GitHub artifacts, Redis, or external fuzzing tools.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation



Reference: [https://hypothesis.readthedocs.io/en/latest/reference/api.html](https://hypothesis.readthedocs.io/en/latest/reference/api.html?utm_source=chatgpt.com)

## 6. Scientific, structured-data, and framework-specific generation

Hypothesis provides first-party extensions that understand the semantics of several specialized Python ecosystems. These can be substantially more useful than generating arbitrary Python objects and converting them into library-specific representations.

### 6.1 NumPy: arrays, dtypes, broadcasting, and indexing

`hypothesis.extra.numpy` provides much more than `ndarray` generation.

| Capability         | Principal APIs                                                                              | Why it matters                                                  |
| ------------------ | ------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Array generation   | `arrays(dtype, shape, elements, fill, unique)`                                              | Generate arrays under explicit data and shape constraints       |
| Shape generation   | `array_shapes`, `broadcastable_shapes`, `mutually_broadcastable_shapes`                     | Exercise shape compatibility and broadcasting rules             |
| Dtype generation   | `scalar_dtypes`, `array_dtypes`, `nested_dtypes`, integer/floating/complex dtype strategies | Explore precision, signedness, byte order, and compound layouts |
| Value generation   | `from_dtype`                                                                                | Generate dtype-compatible elements and numerical edge cases     |
| Indexing           | `basic_indices`, `integer_array_indices`, `valid_tuple_axes`                                | Test slicing, advanced indexing, and reductions                 |
| Time-valued arrays | `datetime64_dtypes`, `timedelta64_dtypes`                                                   | Explore temporal units and precision-sensitive behavior         |

Two advanced mechanisms are especially important.

Structural shape compatibility. Rather than generate arbitrary pairs of shapes and repeatedly fail broadcasting preconditions, `broadcastable_shapes()` and `mutually_broadcastable_shapes()` encode the relationship at generation time. This supports testing array operators, broadcasting engines, and shape inference. The related index strategies generate valid indexing expressions for a given array shape, including relevant combinations of slices, axes, ellipses, and integer-array indices.

Background fill values. `arrays()` may generate selected array elements independently and fill other positions with one shared background value. This is valuable for both performance and minimization: a large array can contain a few significant anomalies against a simple baseline. Setting `fill=st.nothing()` instead forces independently generated values, increasing diversity but potentially making large arrays substantially more expensive to construct and shrink.

The `unique` constraint has nuanced semantics for NaNs, whose equality behavior differs from ordinary values. Generated dtype policies also remain subject to the capabilities and representable values of the underlying NumPy dtype.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation+1



### 6.2 Array API: backend-agnostic array generation

`hypothesis.extra.array_api.make_strategies_namespace(xp, api_version=...)` generates a strategy namespace associated with an Array API-compatible numerical library.

It provides equivalents of array, dtype, shape, broadcasting, indexing, and axis strategies while following the selected Array API standard version. This creates a useful separation between an array's abstract numerical and shape semantics and the particular array engine that materializes it.

Potential engines include NumPy and compatible interfaces from PyTorch, JAX, CuPy, Dask, and others. This does not mean every engine implements every Array API feature identically: the supplied `xp` namespace, its reported standard version, available dtypes, supported devices, and actual implementation behavior constrain the resulting tests.

The `api_version` parameter refers to the Array API specification version, not the Hypothesis release. It may be inferred from `xp.__array_api_version__` or supplied explicitly where supported.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation



The architectural opportunity is cross-backend differential testing: generate inputs constrained by a shared specification, execute equivalent operations in multiple compatible array engines, and compare results under explicit tolerances and dtype rules. Hypothesis supplies the input modeling; it does not automatically define a correct cross-backend numerical equivalence relation.

### 6.3 pandas: relational and columnar structure

`hypothesis.extra.pandas` provides `indexes()`, `range_indexes()`, `series()`, `data_frames()`, `column()`, and `columns()`.

Its significant capabilities include named and typed columns, index-driven row counts, uniqueness restrictions, fill values, and generation of records with relationships between fields.

Row-oriented and column-oriented generation express different constraints. Column strategies are natural when each column can be generated independently and its dtype and uniqueness constraints are the important properties. A `rows=` strategy is more useful when fields must be related within a record—for example, lower and upper bounds, correlated identifiers, or values constrained by a shared enum.

The two approaches can be combined. Column specifications determine names and dtypes, while row strategies determine values and cross-column dependencies. The documentation notes that dtype inference from row strategies is not generally automatic when combining them, so schema specification still matters.

The pandas integration also covers timezone-aware datetime dtypes and `NaT`-sensitive generation. Its published compatibility language commits to the latest pandas version and describes older versions on a best-effort basis; the stated historical tested-minor range should not be treated as an exhaustive current compatibility matrix.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation+1



### 6.4 Django: models, forms, field constraints, and database isolation

`hypothesis.extra.django` adds two distinct categories of functionality.

Schema-aware generation includes `from_model()`, `from_form()`, `from_field()`, and `register_field_strategy()`. Field-instance introspection can use lengths, validators, and other metadata to generate admissible inputs. `from_model()` creates database-backed model instances; relationships and mandatory dependent objects may require explicit construction rather than being universally inferred.

Test execution integration includes Hypothesis-aware Django test classes such as `TestCase`, `SimpleTestCase`, `TransactionTestCase`, and live-server variants. The critical difference from ordinary Django test classes is that Hypothesis can arrange isolation per generated test case, rather than only around the enclosing Python test function.

Without appropriate isolation, repeated generated examples can contaminate one another through database state. Full transaction handling may be expensive when repeated many times, so `TransactionTestCase` has a more substantial runtime cost than simpler available isolation mechanisms.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation



### 6.5 Lark and grammar-based generation

`hypothesis.extra.lark.from_lark()` generates strings accepted by a context-free grammar represented by a Lark parser.

This is a different capability from `st.from_regex()`: a grammar can express recursive and nested language structures that are inconvenient or impossible to describe accurately with conventional regular expressions.

It supports selecting grammar start symbols and supplying explicit strategies for terminals. Important limitations include native Lark EBNF support, restrictions around custom lexing, and special handling for undefined terminals declared using `%declare`. It generates grammar-conforming strings; semantic validity beyond grammar acceptance may still require additional modeling.

This is a useful foundation for parsers, formatters, compilers, query languages, and protocol-text processors. The separate `hypothesmith` project builds on related techniques to generate syntactically valid Python source code; that package is not part of Hypothesis core.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation



### 6.6 Timezones and other extras

Hypothesis provides standard-library `zoneinfo` timezone strategies, with optional `dateutil` and `pytz` integrations for ecosystems using those timezone representations.

The `pytz` extra is explicitly deprecated in the documentation, with standard-library `zoneinfo` preferred where feasible. Timezone-aware datetime generation is useful for daylight-saving gaps, ambiguous local times, and interactions between wall-clock and absolute time.

Source: [https://hypothesis.readthedocs.io/en/latest/reference/strategies.html](https://hypothesis.readthedocs.io/en/latest/reference/strategies.html?utm_source=chatgpt.com)

## 7. Alternative generation engines, fuzzing, and symbolic execution

Hypothesis has a meaningful separation between its strategy language and the backend used to produce primitive choices. This permits different search approaches to operate against substantially the same high-level tests.

### 7.1 Available generation backends

| Backend / tool                        | Search approach                            | Distinctive capability                                                               |
| ------------------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------ |
| `hypothesis`                          | Default Conjecture generation and mutation | General-purpose property-based testing, shrinking, and replay                        |
| `hypothesis-urandom`                  | System entropy source                      | Alternative entropy behavior for specialized testing environments                    |
| `hypofuzz`                            | Coverage-guided adaptive fuzzing           | Continuous exploration, corpus management, and test prioritization                   |
| `crosshair`                           | SMT-assisted symbolic execution            | Search for values satisfying difficult branch and equality conditions                |
| External fuzzers via `fuzz_one_input` | Fuzzer-supplied byte streams               | Reuse structured Hypothesis tests with Atheris, python-afl, or other fuzzing engines |

The documented backends are selected through `settings.backend`; companion packages supply additional implementations. Importantly, an alternative provider generally changes how primitive choices are found, not how strategies describe values or how the test defines failure. The documented alternatives retain integration with Hypothesis's example database and shrinking machinery.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.12 documentation



Backend reference: [https://hypothesis.readthedocs.io/en/latest/strategies.html](https://hypothesis.readthedocs.io/en/latest/strategies.html?utm_source=chatgpt.com)

### 7.2 HypoFuzz: continuous, coverage-guided property testing

Companion package: `hypofuzz`, not part of the base Hypothesis installation.

HypoFuzz extends Hypothesis tests into longer-running adaptive fuzzing campaigns. Its operational model differs materially from executing `pytest` with a larger `max_examples`.

Adaptive allocation. HypoFuzz runs multiple worker processes and prioritizes tests and inputs that discover new code coverage or otherwise useful behavior. Rather than allotting each test an identical fixed budget, it can devote more time to promising or complex targets.

Structured coverage-guided mutation. The fuzzer leverages Hypothesis's strategy encoding to mutate semantically meaningful test inputs. This is especially useful for structured formats, where byte-level mutations often destroy syntax and fail at the parser boundary rather than exploring deeper application behavior.

Corpus distillation and sharing. HypoFuzz retains examples representing interesting coverage, events, or target scores, and uses Hypothesis shrinking to keep them comparatively simple. It can load newly discovered examples from a database to support shared or ensemble exploration.

Dashboard and visibility. Its companion dashboard reports test progress, code coverage, generated-input behavior, and failure information. A local dashboard and separate worker processes can be controlled through `hypothesis fuzz`, with configurable process counts and pytest-based test discovery.

HypoFuzz's key tradeoff is operational: its additional instrumentation and adaptive scheduling are most useful when a campaign runs long enough to exploit the feedback. For short, ordinary test-suite executions, the built-in engine may be preferable because it avoids the additional coordination and instrumentation costs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypofuzz.com\&sz=32)

HypoFuzz docs+1



Sources:

- [https://hypofuzz.com/docs/features.html](https://hypofuzz.com/docs/features.html?utm_source=chatgpt.com)
- [https://hypofuzz.com/docs/manual/cli.html](https://hypofuzz.com/docs/manual/cli.html?utm_source=chatgpt.com)

### 7.3 CrossHair: SMT-assisted generation

The `crosshair` backend uses symbolic execution and satisfiability solving to investigate Python branches. It can be substantially more effective than undirected generation for constraints involving exact equality or narrow conditions, such as reaching a branch guarded by an otherwise unlikely integer value.

This is an important architectural alternative to placing `assume()` conditions on a strategy and hoping random generation reaches the desired region.

However, symbolic execution does not make every Python program or external operation solver-understandable. Effectiveness depends on whether operations encountered during execution can be represented symbolically and on solver tractability. Native extensions, side effects, unsupported operations, and complex nonlinear constraints can limit the benefit.

The backend integration is provided by `hypothesis-crosshair` through the optional `hypothesis[crosshair]` dependency. It is not a guarantee of exhaustive path coverage or proof.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.12 documentation+1



### 7.4 External fuzzers and `fuzz_one_input`

A `@given`-decorated test exposes a `test.hypothesis.fuzz_one_input(...)` interface that accepts a byte buffer, interprets it using the test's strategies, and runs the resulting example.

This supports an architecture where an external fuzzer controls byte mutations and coverage feedback while Hypothesis continues to define valid high-level inputs and facilitate later failure minimization.

Important distinctions:

- `fuzz_one_input` executes a single candidate and bypasses the normal multiphase `@given` test lifecycle.
- Ordinary `max_examples`, generation phases, and deadline behavior do not control its invocation in the same manner as a normal Hypothesis run.
- Failures may be persisted to the example database for later reproduction, shrinking, and deduplication by the ordinary test runner.
- The input-buffer representation is an engine interface, not a permanent serialized domain-object specification.

This makes external fuzzing most compelling when the external tool offers meaningful additional feedback, particularly for native-code coverage. For primarily Python workloads, the Hypothesis documentation recommends investigating HypoFuzz first.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.12 documentation



Source: [https://hypothesis.readthedocs.io/en/latest/how-to/external-fuzzers.html](https://hypothesis.readthedocs.io/en/latest/how-to/external-fuzzers.html?utm_source=chatgpt.com)

### 7.5 Custom backend architecture

For tool builders and researchers, `hypothesis.internal.conjecture.providers.PrimitiveProvider` is the core extension mechanism.

A provider implements five primitive drawing methods: `draw_boolean`, `draw_integer`, `draw_float`, `draw_string`, and `draw_bytes`.

Additional hooks cover provider lifetime (`test_function` versus `test_case`), symbolic-value realization, constraints, observation metadata, and lifecycle behavior. This permits experimentation with solver-driven generation, domain-specific distributions, alternate feedback signals, and hybrid search techniques without rewriting all higher-level strategies.

This is unusually powerful, but it is explicitly an internal API. Hypothesis states that its internals are not covered by normal deprecation guarantees and may change in minor or patch releases. A custom backend therefore has a materially different maintenance and compatibility burden from an ordinary custom `@composite` strategy.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.12 documentation



Internal interface: [https://hypothesis.readthedocs.io/en/latest/reference/internals.html](https://hypothesis.readthedocs.io/en/latest/reference/internals.html?utm_source=chatgpt.com)

## 8. Test generation, automation, and introspection

### 8.1 Ghostwriter: generating property tests from callable interfaces

`hypothesis.extra.ghostwriter` generates editable Python test source from functions and modules.

Its most interesting capability is not merely the generation of input values but the recognition of potentially meaningful algebraic and behavioral properties.

| Ghostwriter          | Generated property                                                                      |
| -------------------- | --------------------------------------------------------------------------------------- |
| `magic()`            | Inspects a module or functions and selects suitable test-generation approaches          |
| `fuzz()`             | Check that admissible inputs do not produce unexpected exceptions                       |
| `roundtrip()`        | Check composition of operations such as encode/decode or serialize/deserialize          |
| `equivalent()`       | Compare alternative implementations on shared inputs                                    |
| `idempotent()`       | Check that repeated application has no additional effect                                |
| `binary_operation()` | Check algebraic laws such as associativity, commutativity, identity, and distributivity |
| `ufunc()`            | Exercise NumPy ufunc/gufunc broadcasting and dtype behavior                             |

These mechanisms can expose useful testable contracts with relatively little manual scaffolding.

The important limitation is oracle quality. A generated test for associativity is only valid if the operation is actually intended to be associative. A generated differential test is meaningful only if the implementations are expected to behave equivalently under the tested inputs.

Ghostwriter uses signatures, names, and type information as hints. For insufficiently specified parameters, it may emit `st.nothing()` placeholders and `TODO` comments. Such output is a starting point for substantive property design, not automatically evidence of correctness or comprehensive coverage.

The `hypothesis write` CLI is supplied through the relevant extras, and the generated source can be maintained independently afterward. The ghostwriter requires Black; its generated output is made available under CC0.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.12 documentation



Reference: [https://hypothesis.readthedocs.io/en/latest/reference/integrations.html](https://hypothesis.readthedocs.io/en/latest/reference/integrations.html?utm_source=chatgpt.com)

### 8.2 Observability and execution statistics

Hypothesis exposes several levels of diagnostic information.

In-test reporting: `note(value)` attaches human-readable context to a test case; `event(value, payload=...)` records a named event for aggregate statistics; `target()` records optimization metrics.

Pytest integration: `--hypothesis-show-statistics` reports generation timing, valid/invalid examples, event frequencies, and why exploration stopped. Additional arguments select profiles, control verbosity, supply seeds, and enable failure explanation. Hypothesis automatically marks generated tests with `pytest.mark.hypothesis`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.12 documentation



Experimental structured observability: setting `HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY` enables JSON Lines output under `.hypothesis/observed/`. This records information on generated test cases, their status, timing, arguments, events, notes, and related execution observations. Some low-level choice and span data can also be exposed for tools studying how Hypothesis generated an input.

The distinction between these levels is important. `event()` and pytest statistics are stable, established interfaces for understanding behavior. The structured observability feature is explicitly marked experimental and unstable, and its choice-level representation is an internal implementation detail. The Tyche VS Code extension is one separate visualization consumer for Hypothesis observability data.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.12 documentation+1



Observation reference: [https://hypothesis.readthedocs.io/en/latest/reference/integrations.html](https://hypothesis.readthedocs.io/en/latest/reference/integrations.html?utm_source=chatgpt.com)

### 8.3 Codemods, CLI tooling, and test discovery

Hypothesis also provides tooling that supports authoring and maintenance rather than generation itself.

The optional `hypothesis[codemods]` functionality provides automated transformations for certain deprecated Hypothesis API usages, built on LibCST. The `hypothesis[cli]` / ghostwriter tools add command-line workflows. The public `is_hypothesis_test()` utility allows integrations to recognize Hypothesis-decorated tests without relying on unstructured source inspection.

These tools serve different layers: codemods revise existing test source; ghostwriter generates new source; pytest discovery and the `hypothesis` marker expose existing test functions to external runners. None of these should be confused with the Conjecture engine's runtime search capability.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.12 documentation+1



## 9. Ecosystem integration and extension discovery

### 9.1 Third-party strategy ecosystem

The extension ecosystem broadens Hypothesis from built-in Python values into schema-driven and domain-specific generation.

| Integration family       | Representative libraries                                                            | Capability boundary                                                        |
| ------------------------ | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Declarative schemas      | `hypothesis-jsonschema`, `hypothesis-graphql`, `hypothesis-pb`                      | Derive input strategies from JSON Schema, GraphQL, or Protocol Buffers     |
| Database and objects     | `hypothesis-sqlalchemy`, Pydantic, Pandera                                          | Generate values or records based on ORM, validation, or dataframe schemas  |
| Numerical and scientific | `hypothesis-torch`, `hypothesis-awkward`, `hypothesis-rdkit`, `hypothesis-geometry` | Generate specialized tensors, arrays, molecular structures, and geometries |
| Graphs and protocols     | `hypothesis-networkx`, `hypothesis-ros`, `hypothesis-geojson`                       | Generate graphs, robotics messages, and structured interchange formats     |
| Source-code generation   | `hypothesmith`                                                                      | Generate syntactically valid Python source                                 |
| API testing              | Schemathesis                                                                        | Derive HTTP API test cases and requests from API specifications            |
| Design by contract       | `deal`, `icontract-hypothesis`                                                      | Derive or check tests using explicit contracts                             |
| Asynchronous testing     | `pytest-trio`, `hypothesis-trio`                                                    | Execute async tests and explore specialized concurrent stateful behavior   |

These integrations differ in their degree of automation. A schema-derived strategy can ensure that generated values satisfy supported schema constraints, but it does not necessarily guarantee relational consistency, business invariants, or compatibility with every downstream consumer.

The Hypothesis documentation explicitly states that inclusion in its third-party extensions catalog does not constitute project endorsement. Compatibility and maintenance should be evaluated at the extension-package level, independently of Hypothesis's own release cadence.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.11 documentation



Ecosystem directory: [https://hypothesis.readthedocs.io/en/latest/extensions.html](https://hypothesis.readthedocs.io/en/latest/extensions.html?utm_source=chatgpt.com)

### 9.2 Automatic extension registration

Hypothesis supports Python packaging entry points under the group `hypothesis`.

An extension can expose initialization code that registers custom type strategies or pseudorandom generators when Hypothesis is imported. This removes the need for every downstream test module to manually invoke the registration helper.

The capability is convenient but has implications for initialization order: automatic plugin loading can import an extension before other instrumentation has initialized. The upstream documentation specifically describes interactions with `pytest-cov`. The `HYPOTHESIS_NO_PLUGINS` environment variable disables automatic Hypothesis plugin loading, primarily for troubleshooting.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.11 documentation



This creates three distinct extension levels:

| Extension level            | Appropriate mechanism                                       | Stability characteristics                                          |
| -------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------ |
| Domain-specific values     | Composed strategies, `@composite`, `from_type` registration | Supported public API                                               |
| Automatic integrations     | `hypothesis` packaging entry points                         | Supported discovery interface; initialization-order considerations |
| Alternative search engines | `PrimitiveProvider` and associated internals                | Powerful but explicitly outside ordinary compatibility guarantees  |

## 10. Correctness boundaries and execution semantics

### 10.1 Test-case isolation is fundamental

A `@given` test is executed repeatedly, potentially hundreds or thousands of times. Every generated case must be evaluated against a sufficiently independent environment.

This creates several important correctness distinctions.

pytest fixtures do not reset per generated case. A function-scoped pytest fixture runs once for the enclosing test function, not once for every Hypothesis-generated input. Hypothesis identifies this through `HealthCheck.function_scoped_fixture`.

Object mutation may leak between examples. `st.just(value)` returns the specified object, not a defensive copy; wrapping a mutable preconstructed object can inadvertently share it between test executions. Constructing fresh objects through `st.builds()` or an appropriate strategy avoids that particular failure mode.

Global services require explicit isolation. Database contents, filesystem changes, process state, network resources, and caches are not automatically rolled back by the default executor.

Hypothesis's `execute_example` extension hook can wrap individual executions in a transaction, context manager, subprocess, or other execution environment. This is the mechanism underlying some specialized integrations, including Django's per-example transaction handling.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation+2



### 10.2 Async and concurrent execution

Hypothesis does not independently provide a universal asynchronous event-loop runner. An `async def` test needs an appropriate executor or an integration such as `pytest-asyncio` or `pytest-trio` to manage coroutine execution.

This distinction separates generating asynchronous callables, which `st.functions()` can do, from executing an asynchronous test, which requires event-loop integration.

Hypothesis itself became officially thread-safe in version 6.136.9, including simultaneous invocation of the same Hypothesis test from multiple threads. That is a library execution guarantee, not an assertion that the application under test is thread-safe, or that Hypothesis automatically explores every possible concurrent interleaving.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



Concurrency announcement: [https://hypothesis.works/articles/thread-safe/](https://hypothesis.works/articles/thread-safe/?utm_source=chatgpt.com)

### 10.3 Flakiness and reproducibility diagnostics

Hypothesis actively detects situations where replayed tests or strategies behave inconsistently.

| Exception or signal       | Meaning                                                                               |
| ------------------------- | ------------------------------------------------------------------------------------- |
| `FlakyFailure`            | An input failed previously but does not reproduce the same failure                    |
| `FlakyStrategyDefinition` | Strategy generation changes inconsistently under replay                               |
| `FlakyBackendFailure`     | A failure from an alternative backend cannot be reproduced under the standard backend |
| `Unsatisfiable`           | Too few generated inputs satisfy the declared assumptions                             |
| `DeadlineExceeded`        | A test execution exceeded the configured deadline                                     |
| `ResolutionFailed`        | Type-directed strategy inference could not resolve a required type                    |
| `InvalidArgument`         | An invalid strategy, decorator, or settings configuration                             |
| `DidNotReproduce`         | A specified reproduction artifact no longer causes the expected failure               |

Flaky outcomes can result from uncontrolled randomness, changing external state, concurrency, time-sensitive behavior, or unstable strategy logic. A fixed Hypothesis seed cannot correct nondeterminism originating outside the engine.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation



### 10.4 Health checks are not interchangeable

Hypothesis distinguishes performance-related health checks from potential correctness violations.

`filter_too_much`, `too_slow`, `data_too_large`, and `large_base_example` indicate circumstances that can make exploration inefficient or incomplete. In contrast, `function_scoped_fixture` and `differing_executors` signal conditions that may undermine the validity or reproducibility of results.

The distinction is consequential: suppressing an expensive-generation warning can be a deliberate test-budget tradeoff; suppressing a state-isolation warning without correcting its cause may allow tests to pass or fail for misleading reasons.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation



### 10.5 Coverage, distributions, and proof boundaries

Hypothesis offers extensive exploration but retains several fundamental limitations.

Distribution is not a stable contract. Generated cases are deliberately influenced by shrinking, example databases, strategy composition, and implementation heuristics. A test should not assume that uniformly sampling a domain, or repeatedly executing it with the same seed, produces stable statistical coverage across library versions.

Finite testing is not proof. Successful runs demonstrate that no failure was found among the examples explored. Coverage-guided and solver-assisted extensions improve exploration in particular circumstances without making arbitrary Python behavior exhaustively verified.

A meaningful property remains necessary. No-crash tests are useful, but weaker than well-defined equivalence, invariance, preservation, round-trip, or state-transition properties.

Numerical equivalence needs explicit semantics. Differential tests of floating-point implementations must distinguish exact equality, tolerance-based equivalence, NaN handling, signed-zero behavior, overflow, and backend-specific precision. Hypothesis generates relevant values; it does not define those semantics on behalf of the implementation.

Shrinking requires reproducible failures. A counterexample that depends on mutable external conditions, timing races, or hidden random state may be impossible to simplify reliably.

These limitations define Hypothesis's role as an exploration and falsification engine rather than a universal specification or verification system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.12 documentation+2



## 11. Release, compatibility, and architectural status

### 11.1 Package requirements and first-party extras

The verified PyPI release, 6.170.12, requires Python 3.11 or later, with CPython and PyPy distributions. The package uses the MPL-2.0 license and provides optional extras including `numpy`, `pandas`, `django`, `lark`, `crosshair`, `redis`, `ghostwriter`, `cli`, `codemods`, `dateutil`, `pytz`, and `zoneinfo`. `sortedcontainers` remains a required dependency.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



There is an important packaging change: starting with Hypothesis 6.156.0 in July 2026, the maintainers began migrating selected internals from Python to Rust. As a result, building Hypothesis from source requires a Rust toolchain, while supported platforms can install prebuilt native wheels.

This does not mean the entire Conjecture engine has been rewritten in Rust. The documented migration began with internal helpers and is incremental.

The 6.170.12 release reports reduced generation overhead and faster shrinking for simple tests, with smaller improvements in many other workloads. These reported gains are not universal speedup guarantees; actual performance depends on strategy complexity, test execution time, and how much work occurs inside Hypothesis versus the tested system.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation+1



Release history: [https://hypothesis.readthedocs.io/en/latest/changelog.html](https://hypothesis.readthedocs.io/en/latest/changelog.html?utm_source=chatgpt.com)

### 11.2 Stability categories

| Interface or capability                          | Status                                                                         |
| ------------------------------------------------ | ------------------------------------------------------------------------------ |
| `@given`, strategies, `@example`, settings       | Established public APIs                                                        |
| Stateful rule machines and bundles               | Established public APIs                                                        |
| Example database classes and extension interface | Public APIs, with backend-specific requirements                                |
| NumPy, pandas, Django, Lark, Array API           | Released first-party integrations                                              |
| Alternative backends                             | Released integration model; backend availability depends on companion packages |
| `hypothesis.provisional.domains()` and `urls()`  | Provisional APIs; may change without standard deprecation process              |
| Structured observability                         | Experimental; schema and behavior may change                                   |
| `PrimitiveProvider` and Conjecture internals     | Internal and not subject to ordinary API compatibility guarantees              |
| `pytz` extra                                     | Documented as deprecated; `zoneinfo` preferred where feasible                  |

The documentation site already contains an entry dated October 28, 2026 for 6.170.13, concerning a codemod fix. PyPI's latest verifiable published package at research time remained 6.170.12, which is the version targeted throughout this reference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://hypothesis.readthedocs.io\&sz=32)

Hypothesis 6.170.13 documentation+5



## 12. Architectural implications and capability combinations

The most useful capabilities often emerge from combining features rather than considering each in isolation.

| Problem class                            | Composed Hypothesis capabilities                                                  | Resulting architectural option                                                             |
| ---------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Recursive language processing            | `st.recursive` or `from_lark` + differential or round-trip properties + shrinking | A grammar-aware test system that produces minimized parser or serializer counterexamples   |
| Mutable resource management              | `RuleBasedStateMachine` + bundles + `consumes` + invariants                       | Generated operation histories that test resource ownership and lifecycle rules             |
| Numerical engines                        | dtype/shape strategies + Array API integration + `target`                         | Structured exploration of precision, shape, and numerical instability                      |
| Dataframe transformations                | pandas row/column strategies + schema constraints + reference-model comparison    | Data-driven testing of relational transformations and cross-field invariants               |
| Database or protocol behavior            | state machines + per-example isolation + example database                         | Reproducible sequence testing across independent executions                                |
| Complex input constraints                | `@composite` / `flatmap` + CrossHair backend                                      | Constructive generation supplemented by symbolic branch exploration                        |
| Continuous fuzzing                       | Existing `@given` tests + HypoFuzz + shared example database                      | Adaptive exploration reusing an established test specification                             |
| Automated test authoring                 | Ghostwriter + registered type strategies + observability                          | Generated property-test source whose input quality and execution behavior can be inspected |
| Agentic and machine-driven test analysis | `event`, `note`, pytest statistics, experimental observability                    | Structured evidence about tested inputs, invalid cases, coverage, and discovered failures  |

The recurring design principle is to retain a single declarative description of valid inputs while allowing different execution, exploration, persistence, and observation mechanisms to operate on it.

This is where Hypothesis can replace substantial bespoke testing infrastructure: custom random-data factories, hand-written operation-sequence generators, failure minimizers, persistent fuzz corpora, and portions of schema-aware test-data generation can often be expressed through native strategies and companion tools.

The qualification is that each layer has a separate responsibility. The strategy defines the input space; an executor establishes isolation; the test defines correctness; the engine searches; the database persists examples; and observability describes what happened. Preserving those distinctions makes the resulting system more expressive without confusing generated validity with verified correctness.

## Primary-source reference map

The following sources provide the most useful paths for deeper technical investigation, with direct URLs suitable for use independently of this overview.

| Subject                                                 | Direct source                                                                                                                                                               |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Core API, settings, databases, stateful API             | [https://hypothesis.readthedocs.io/en/latest/reference/api.html](https://hypothesis.readthedocs.io/en/latest/reference/api.html?utm_source=chatgpt.com)                     |
| Strategies, combinators, NumPy, pandas, Lark, Array API | [https://hypothesis.readthedocs.io/en/latest/reference/strategies.html](https://hypothesis.readthedocs.io/en/latest/reference/strategies.html?utm_source=chatgpt.com)       |
| Stateful testing concepts and composition               | [https://hypothesis.readthedocs.io/en/latest/stateful.html](https://hypothesis.readthedocs.io/en/latest/stateful.html?utm_source=chatgpt.com)                               |
| Ghostwriter, pytest, observability                      | [https://hypothesis.readthedocs.io/en/latest/reference/integrations.html](https://hypothesis.readthedocs.io/en/latest/reference/integrations.html?utm_source=chatgpt.com)   |
| Backend internals and extension interfaces              | [https://hypothesis.readthedocs.io/en/latest/reference/internals.html](https://hypothesis.readthedocs.io/en/latest/reference/internals.html?utm_source=chatgpt.com)         |
| Alternative generation backends                         | [https://hypothesis.readthedocs.io/en/latest/strategies.html](https://hypothesis.readthedocs.io/en/latest/strategies.html?utm_source=chatgpt.com)                           |
| External fuzzing interface                              | [https://hypothesis.readthedocs.io/en/latest/how-to/external-fuzzers.html](https://hypothesis.readthedocs.io/en/latest/how-to/external-fuzzers.html?utm_source=chatgpt.com) |
| First-party optional integrations                       | [https://hypothesis.readthedocs.io/en/latest/extras.html](https://hypothesis.readthedocs.io/en/latest/extras.html?utm_source=chatgpt.com)                                   |
| Third-party ecosystem and extension registration        | [https://hypothesis.readthedocs.io/en/latest/extensions.html](https://hypothesis.readthedocs.io/en/latest/extensions.html?utm_source=chatgpt.com)                           |
| HypoFuzz adaptive search                                | [https://hypofuzz.com/docs/features.html](https://hypofuzz.com/docs/features.html?utm_source=chatgpt.com)                                                                   |
| Current package requirements and published versions     | [https://pypi.org/project/hypothesis/](https://pypi.org/project/hypothesis/?utm_source=chatgpt.com)                                                                         |
| Release history and compatibility changes               | [https://hypothesis.readthedocs.io/en/latest/changelog.html](https://hypothesis.readthedocs.io/en/latest/changelog.html?utm_source=chatgpt.com)                             |

Overall: Hypothesis is most accurately understood as a composable, strategy-driven test exploration platform—not merely a randomized test decorator. Its advanced capabilities are strongest where structurally valid data generation, state transitions, minimization, alternate search engines, and replayable evidence must work together.