# Rule Engine 5.1.0 — Comprehensive Python Library Overview

Research date: October 20, 2026 | Target: rule-engine 5.1.0 | Python 3.10+

Rule Engine is a lightweight, extensible expression-language engine for evaluating declarative rules against arbitrary Python objects. It provides a custom grammar, an optional but sophisticated static type system, runtime evaluation, structured-object introspection, and mechanisms for integrating rules with Python's existing data models.

The library is particularly interesting because it goes considerably beyond simple condition evaluation. Its native capabilities allow developers to construct typed, schema-aware decision logic without implementing their own expression parser, type checker, symbol-resolution infrastructure, or evaluation interpreter.

Version 5.1.0 was released on October 20, 2026. I verified the release against the upstream GitHub release record and tagged changelog. The published documentation website still identifies itself as 5.0.3 at the time of research, so this overview uses the 5.1.0 tagged source for release-specific behavior.

Primary project resources:

- [GitHub repository](https://github.com/zeroSteiner/rule-engine?utm_source=chatgpt.com)
- [Rule Engine documentation](https://zerosteiner.github.io/rule-engine/?utm_source=chatgpt.com)
- [Version 5.1.0 release](https://github.com/zeroSteiner/rule-engine/releases/tag/v5.1.0?utm_source=chatgpt.com)
- [Version 5.1.0 tagged changelog](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/docs/source/change_log.rst?utm_source=chatgpt.com)
- [PyPI package](https://pypi.org/project/rule-engine/?utm_source=chatgpt.com)

## 1. Architectural orientation

The central abstraction is a compiled `Rule`: a textual expression is parsed into a structured abstract syntax tree (AST), checked against available type information, and subsequently evaluated against supplied Python values.

Rule expression

Declarative predicate, computation, or conditional expression

Parse and optionally type-check

Typed AST / Rule

Reusable expression structure with validated operators and symbol references

Evaluate with Context

Context

Resolvers, type definitions, builtins, numeric and timezone policy

Python object

Mappings, dataclasses, ORM objects, nested collections

Evaluation result

Boolean match, arbitrary expression value, or ordered-chain decision

The architecture has several important properties:

- Separation of rule definition and data: expressions can be authored independently of the Python objects against which they will run.
- Optional static validation: symbol and operator errors can be discovered when a rule is constructed, rather than first encountered during evaluation.
- Host-language integration: type resolvers, object schemas, accessors, and functions connect the expression language to Python data and behavior.
- Reusable evaluation: a parsed rule can evaluate many objects without rebuilding its expression tree each time.
- Constrained expression language: unlike Python's `eval()` or `exec()`, Rule Engine parses and interprets its own grammar.
- Composable decision logic: version 5.1.0 introduces ordered rule chains alongside individual expression evaluation.

### Capability map

| Capability family      | Primary mechanisms                                 | Architectural significance                           |
| ---------------------- | -------------------------------------------------- | ---------------------------------------------------- |
| Expression evaluation  | `Rule`, AST, custom grammar                        | Externalized conditions and calculations             |
| Static typing          | `Context`, `DataType`, type resolvers              | Early validation of rule correctness                 |
| Rich data models       | `OBJECT`, `ARRAY`, `MAPPING`, `SET`                | Rules over nested and structured objects             |
| Schema integration     | Dataclasses, SQLAlchemy ORM                        | Reuse existing Python models as rule schemas         |
| Null handling          | `NULLABLE`, `??`, safe navigation                  | Explicit treatment of optional data                  |
| Functional expressions | Comprehensions, builtins, `FUNCTION`               | Compact transformations and aggregate conditions     |
| Ordered decisions      | `Chain`, `ChainEntry`                              | First-match policy and routing logic                 |
| Diagnostics            | Typed errors, symbol introspection, Graphviz, REPL | Rule validation, explanation and debugging           |
| Runtime customization  | Resolvers, builtins, attributes, decimal context   | Application-defined evaluation semantics             |
| Operational reuse      | Thread-local evaluation state, pickling            | Concurrent evaluation and persisted rule definitions |

The most consequential distinction is that Rule Engine is an expression evaluator with a programmable type and data-access environment, rather than merely a string-based predicate matcher.

It is not, by itself, a database query planner, event-processing service, workflow orchestrator, or general-purpose production rule system with automatic agenda scheduling.

## 2. What's new in version 5.1.0?

Version 5.1.0 is a meaningful functional release, not just a maintenance update.

Its principal addition is the `Chain` abstraction, which introduces first-match ordered rule evaluation.

The other major change repairs serialization behavior involving the `UNDEFINED` sentinel.

These additions build upon the substantial 5.0 release, which introduced typed `OBJECT` schemas, dataclass and SQLAlchemy schema extraction, first-class `NULLABLE` types, and serializable rule contexts.

### 2.1. Ordered rule chains: `Chain` and `ChainEntry`

The new `Chain` class provides an explicit mechanism for first-match-wins decision evaluation.

Rather than manually iterating through rules, checking predicates, and associating each predicate with a result, a chain encapsulates those operations.

A chain accepts an ordered sequence of `(rule, value)` pairs. Each rule can be an expression string or an existing `Rule` instance. The result can be any Python object.

```
import rule_enginechain = rule_engine.Chain(    [        ('amount >= 10000 and risk == "high"', "REVIEW"),        ('risk == "high"', "ESCALATE"),        ('amount < 1000', "APPROVE"),    ],    default_value="STANDARD_REVIEW",)chain.evaluate({"amount": 15000, "risk": "high"})# "REVIEW"chain.evaluate({"amount": 500, "risk": "low"})# "APPROVE"
```

This directly supports policy evaluation, ordered classification, request routing, threshold decisions, and other problems where rule precedence is semantically important.

Decision semantics

Input object

Rule 1

Match → return value 1

Rule 2

Match → return value 2

Rule 3

Match → return value 3

No match → default or exception

The first matching rule terminates evaluation. Later rules are not evaluated.

#### Chain inspection and modification

Version 5.1.0 exposes the following operations.

| API                                | Behavior                                    |
| ---------------------------------- | ------------------------------------------- |
| `Chain.evaluate(thing)`            | Return the first matching entry's value     |
| `Chain.find(thing)`                | Return the matching `ChainEntry`, or `None` |
| `Chain.index(entry)`               | Locate an entry's zero-based position       |
| `Chain.append(rule, value)`        | Append a new entry                          |
| `Chain.insert(index, rule, value)` | Insert an entry at a position               |
| `Chain.delete(index)`              | Remove and return an entry                  |
| `Chain.flush()`                    | Remove all entries                          |
| `chain[index]`                     | Access an entry                             |
| `chain[start:stop]`                | Construct a new chain containing that slice |
| `len(chain)` / iteration           | Inspect the current collection              |

A `ChainEntry` is a named tuple with `rule` and `value` fields.

The distinction between `evaluate()` and `find()` matters. `evaluate()` returns the associated Python value, but `find()` exposes the actual rule responsible for the decision.

```
entry = chain.find({"amount": 15000, "risk": "high"})if entry is not None:    print(entry.rule.text)    print(entry.value)    print(chain.index(entry))
```

This makes it straightforward to associate application-level explanations, rule identifiers, logging, or audit metadata with decisions. The library provides the matching entry; durable audit records and explanation generation remain caller responsibilities.

#### Default and exception behavior

A chain's `default_value` is the result returned if none of its rules match.

If no default is configured, `Chain.evaluate()` raises the new `ChainExhaustedError`, which retains the original evaluated object in its `.thing` attribute.

A critical distinction:

- Chain default: handles the absence of any matching rule.
- Context default: handles a symbol or attribute missing from an object.

These mechanisms are independent. A configured chain default does not suppress missing-symbol exceptions inside its rules.

#### Concurrency and dynamic updates

An important implementation detail is that chains maintain their entries as an immutable tuple and use copy-on-write updates.

This provides useful behavior:

- Evaluations do not acquire the chain's mutation lock.
- Each evaluation observes a consistent snapshot of the ordered entries.
- Multiple writers serialize modifications so updates are not lost.
- Iterators and slices retain stable entry collections.
- Slicing creates a separate chain with the original context and default value.

These guarantees concern the chain's entry collection. They do not make arbitrary user-supplied resolver functions, mutable result values, or underlying application objects thread-safe.

There is also a clear performance tradeoff: mutations copy the existing entry tuple. Constructing a large chain from its full entry list is consequently more efficient than repeatedly appending thousands of rules.

Evaluation remains sequential, stopping at the first match. The library does not claim indexed, parallel, or automatically optimized rule selection.

#### Serialization

Chains support Python `pickle`, provided their constituent contexts, rules, and result values are picklable.

The chain's synchronization lock is recreated during deserialization. Shared context relationships within the serialized object graph are preserved.

This makes chains reusable as persisted decision configurations, although `pickle` should only deserialize trusted data.

Direct 5.1.0 sources:

- [Chain implementation](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/engine/chain.py?utm_source=chatgpt.com)
- [Chain documentation and usage](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/docs/source/getting_started.rst?utm_source=chatgpt.com)
- [Chain behavioral tests](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/tests/chain.py?utm_source=chatgpt.com)

### 2.2. Corrected `UNDEFINED` serialization

The other explicit 5.1.0 change fixes a problem involving the internal `UNDEFINED` sentinel.

Previously, pickling or copying this sentinel could produce a separate object rather than preserve the sentinel's identity. For a restored `Context`, this could cause missing-symbol and missing-attribute handling to behave incorrectly.

Version 5.1.0:

- Preserves sentinel identity through copying and serialization.
- Corrects affected contexts created by earlier versions when those contexts are unpickled.
- Restores the expected `SymbolResolutionError` and `AttributeResolutionError` behavior for contexts using the default missing-value policy.

This is especially relevant when rules and contexts are serialized for reuse across processes or application restarts.

See the [5.1.0 changes to ](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/errors.py?utm_source=chatgpt.com)[`errors.py`](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/errors.py?utm_source=chatgpt.com) and [context restoration](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/engine/context.py?utm_source=chatgpt.com).

## 3. Core rule evaluation and execution model

The principal API is deliberately small.

| API                                      | Purpose                                                 |
| ---------------------------------------- | ------------------------------------------------------- |
| `Rule(expression, context=...)`          | Parse and construct a reusable expression               |
| `Rule.evaluate(thing)`                   | Evaluate and return an arbitrary value                  |
| `Rule.matches(thing)`                    | Evaluate and convert the result to Boolean              |
| `Rule.filter(iterable)`                  | Lazily yield objects matching the rule                  |
| `Rule.is_valid(expression, context=...)` | Check whether an expression can be parsed and validated |
| `Rule.to_graphviz()`                     | Render the expression's AST as a Graphviz graph         |

### 3.1. Expressions are not restricted to Boolean results

A `Rule` may evaluate to a numeric value, string, datetime, compound value, or another supported result.

```
rule = rule_engine.Rule(    'quantity * unit_price * (1 - discount)')rule.evaluate({    "quantity": 8,    "unit_price": 12.50,    "discount": 0.10,})# Decimal("90.000")
```

The corresponding `matches()` operation converts the evaluated result to a Boolean.

This distinction opens two different uses of the same expression engine:

Predicate evaluation determines whether an object satisfies conditions.

Value evaluation computes derived values, classifications, normalized expressions, or other results.

The engine therefore supports more than an externalized collection of `if` statements.

### 3.2. Construction-time and runtime validation

Rule construction parses the expression and performs type checking wherever adequate type information is available.

During parsing, the engine also reduces AST nodes whose values can be determined ahead of time. This constant reduction eliminates some repeated work during subsequent evaluations.

At runtime, evaluation resolves symbols against the supplied object, performs remaining operations, and returns the expression's result.

The validation boundary is significant:

- Syntax errors can be detected before any data is processed.
- Known type mismatches can be detected when a rule is constructed.
- Missing symbol names can be rejected at construction if the type resolver defines the permitted symbol set.
- Runtime values are still checked for compatibility with declared types.
- Actual object access, function execution, and data-dependent errors generally remain runtime concerns.

`Rule.is_valid()` is useful for validating user-authored expressions. It is not a guarantee that every future runtime input will evaluate successfully.

### 3.3. Reusable AST execution

The parsing subsystem uses a vendored implementation of PLY, constructs AST nodes, and performs reductions during parsing.

Once a `Rule` has been constructed, subsequent calls execute the existing AST rather than parsing the expression again.

This creates a useful separation between rule preparation and application to data.

`Rule.filter()` is particularly convenient for ordinary Python collections, but it is a generator over per-object evaluations, not a vectorized query or a database pushdown operation.

Sources: [Rule API](https://zerosteiner.github.io/rule-engine/rule_engine/engine.html?utm_source=chatgpt.com), [Parser architecture](https://zerosteiner.github.io/rule-engine/rule_engine/parser/index.html?utm_source=chatgpt.com), [tagged Rule implementation](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/engine/rule.py?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zerosteiner.github.io\&sz=32)

Rule Engine 5.0.3 documentation

+2



## 4. Expression language and supported operations

Rule Engine's grammar is intentionally smaller than Python's, but it includes substantially more than Boolean comparisons.

Its capabilities cover arithmetic, regular expressions, temporal reasoning, collection membership, transformations, function calls, null handling, and nested data access.

### 4.1. Operators

| Family              | Operators                           | Capabilities                                                                    |
| ------------------- | ----------------------------------- | ------------------------------------------------------------------------------- |
| Arithmetic          | `+`, `-`, `*`, `/`, `//`, `%`, `**` | Numeric calculations, compatible string/byte concatenation, datetime arithmetic |
| Comparison          | `==`, `!=`, `<`, `<=`, `>`, `>=`    | Equality and ordered comparisons                                                |
| Regular expressions | `=~`, `=~~`, `!~`, `!~~`            | Pattern matching and substring searches                                         |
| Logical             | `and`, `or`, `not`                  | Boolean composition                                                             |
| Membership          | `in`, `not in`                      | Collection and string containment                                               |
| Bitwise / sets      | `&`, `\\|`, `^`, `<<`, `>>`         | Integer-like bitwise operations and set operations                              |
| Conditional         | `condition ? a : b`                 | Conditional expression evaluation                                               |
| Null handling       | `??`                                | Null-coalescing                                                                 |
| Attribute access    | `.`, `&.`                           | Normal and null-safe attribute lookup                                           |
| Item access         | `[]`, `&[]`                         | Indexing and null-safe lookup                                                   |
| Slicing             | `[start:stop]`, `&[start:stop]`     | Sequence extraction                                                             |

Several distinctions matter.

Regex matching versus searching: `=~` uses regular-expression matching from the beginning of a string, whereas `=~~` searches for a match anywhere. Their negated forms are `!~` and `!~~`.

Ordered comparison typing: unlike equality, ordered comparisons require compatible types. Strings, arrays, datetimes, numeric values, and other supported types have their respective ordering semantics.

Bitwise arithmetic: bitwise operators acting on numeric values require integer-like values, even though the language represents numbers through its `FLOAT` type.

Operator precedence: version 5.0 changed precedence to align more closely with common programming languages. Expressions inherited from older versions should not be assumed to retain their interpretation without checking ambiguous combinations. Parentheses remain the clearest way to make complex expressions unambiguous.

### 4.2. Literal and compound values

The grammar directly supports:

| Literal    | Example                               |
| ---------- | ------------------------------------- |
| Boolean    | `true`, `false`                       |
| Null       | `null`                                |
| Numeric    | `10`, `1.25`, `1e3`, `0xff`, `0b1010` |
| String     | `"hello"`, `'hello'`                  |
| Raw string | `r"\w+"`                              |
| Bytes      | `b"hello"`                            |
| Datetime   | `d"2026-10-20T12:00:00Z"`             |
| Duration   | `t"P2DT6H"`                           |
| Array      | `[1, 2, 3]`                           |
| Set        | `{"red", "blue"}`                     |
| Mapping    | `{"name": "Ada", "active": true}`     |

Raw strings, introduced in 5.0, reduce escaping friction when writing regular expressions. Datetime literals use ISO-8601 parsing; duration literals support the subset representable by `datetime.timedelta`, excluding years and months.

The availability of compound literals means rules can define their own small lookup sets, membership conditions, and intermediate values without requiring a separate Python callback for every operation.

### 4.3. Array comprehensions

One of the more useful capabilities is native array-comprehension syntax.

```
[x ** 2 for x in values]

[x for x in values if x > 10]

[item["amount"] for item in items if item["active"]]
```

Comprehensions consist of a result expression, a single bound variable, a source iterable, and an optional filtering condition.

They allow declarative extraction and transformation of nested collections inside rules.

For instance:

```
$sum([item["amount"] for item in items if item["approved"]])
```

This combines a comprehension with the built-in `$sum()` function to express an aggregate over selected items.

The engine can iterate arrays and sets; iterating mappings produces their keys.

There are important limits. Comprehensions produce in-memory arrays, do not support tuple unpacking in the loop variable, and are not lazy database queries. Large nested comprehensions can consequently incur substantial Python-level computation and intermediate allocations.

### 4.4. Conditional expressions and short-circuiting

The ternary expression:

```
condition ? true_value : false_value
```

provides conditional selection without requiring a statement-oriented language.

The logical operators `and` and `or` support short-circuit evaluation. This is useful both for efficiency and for conditional operations that would otherwise be invalid for some input values.

For nullable data, however, the type system may still reject an unsafe operation at parse time even if an earlier Boolean guard would prevent that branch from executing. This distinction becomes particularly important with `NULLABLE` types.

### 4.5. Regular expressions and captured groups

Regex operators are backed by Python's `re` functionality and accept configuration through `Context.regex_flags`.

After a successful regex operation, the special `$re_groups` builtin exposes the captured groups from the most recent successful match.

```
email =~ r"^([^@]+)@(.+)$" and $re_groups[1] == "example.org"
```

The group collection is maintained in thread-local evaluation state and is reset at the start of a rule evaluation.

A dynamically supplied pattern may require runtime compilation; literal patterns can be prepared as part of the expression structure.

Regex matching is particularly useful for structured text validation, but Python's regex behavior and susceptibility to expensive patterns remain relevant when expressions come from untrusted authors.

Sources: [Rule syntax](https://zerosteiner.github.io/rule-engine/syntax.html?utm_source=chatgpt.com), [5.1.0 parser grammar](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/parser/__init__.py?utm_source=chatgpt.com), [regex evaluation](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/ast/binary/comparison.py?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zerosteiner.github.io\&sz=32)

Rule Engine 5.0.3 documentation

+1



## 5. The data type system

The type system is arguably Rule Engine's most architecturally valuable feature, particularly after the 5.0 additions that remain available in 5.1.0.

It enables rule definitions to be checked against explicit object schemas without requiring a full-fledged external compiler or custom validation framework.

### 5.1. Supported type families

| `DataType`             | Python representation        | Important characteristics                              |
| ---------------------- | ---------------------------- | ------------------------------------------------------ |
| `BOOLEAN`              | `bool`                       | Truth values                                           |
| `FLOAT`                | `int`, `float`, `Decimal`    | Decimal-backed numeric evaluation                      |
| `STRING`               | `str`                        | Text comparisons, indexing, attributes                 |
| `BYTES`                | `bytes`                      | Binary values and encoding operations                  |
| `DATETIME`             | `date`, `datetime`           | Temporal comparisons and attributes                    |
| `TIMEDELTA`            | `timedelta`                  | Durations and date arithmetic                          |
| `ARRAY(T)`             | Lists, tuples                | Ordered collections with optional member typing        |
| `SET(T)`               | Sets                         | Membership and set operations                          |
| `MAPPING(K, V)`        | Dictionaries                 | Key/value structures                                   |
| `OBJECT(name, schema)` | Schema-backed Python objects | Named typed attributes and nested relationships        |
| `NULL`                 | `None`                       | Explicit null value                                    |
| `NULLABLE(T)`          | `T` or `None`                | Nullable static type                                   |
| `FUNCTION`             | Python callable              | Typed or untyped callable integration                  |
| `UNDEFINED`            | No fixed static type         | Known or inferred symbol whose type is not established |

The last two distinctions are important: `DataType.UNDEFINED` means insufficient static type information, whereas the runtime `errors.UNDEFINED` sentinel represents the absence of a configured value. They are not interchangeable concepts.

### 5.2. Type inference and introspection

`DataType` provides several mechanisms for deriving or examining types.

| API                              | Purpose                                                 |
| -------------------------------- | ------------------------------------------------------- |
| `DataType.from_name(name)`       | Resolve a built-in data type by name                    |
| `DataType.from_type(py_type)`    | Map a supported Python type or type annotation          |
| `DataType.from_value(value)`     | Infer a Rule Engine type from a runtime value           |
| `DataType.is_type(type, family)` | Check membership in a type family                       |
| `DataType.is_compatible(a, b)`   | Evaluate compatibility, including compound member types |

Python annotations such as `list[str]`, `dict[str, int]`, and `str | None` can be translated into corresponding Rule Engine type definitions.

The system is not a general Python typing engine. For example, unions containing multiple non-`None` alternatives are not supported as first-class sum types.

Compound types also have an inherent limitation: a single declared element or value type describes their members. Arbitrarily heterogeneous collections therefore lose some opportunities for precise static checking.

Nevertheless, this is sufficient to make many structured expressions statically analyzable.

### 5.3. `OBJECT`: schema-aware nested data

Introduced in 5.0, `OBJECT` is a major advance over mapping-based evaluation.

An `OBJECT` defines named attributes and their types:

```
from rule_engine import DataType as TAddress = T.OBJECT(    "Address",    attributes={        "city": T.STRING,        "postal_code": T.STRING,    },)Customer = T.OBJECT(    "Customer",    attributes={        "name": T.STRING,        "age": T.FLOAT,        "address": T.NULLABLE(Address),    },)
```

A rule can then be statically checked against the declared schema.

```
context = rule_engine.Context(    type_resolver={"customer": Customer})rule = rule_engine.Rule(    '(customer.address&.city ?? "") == "New York"',    context=context,)
```

An attempt to reference a nonexistent attribute can fail when the rule is constructed, raising `ObjectAttributeError` and potentially suggesting an available attribute name.

This is substantially different from ordinary dictionary traversal, where many invalid field references are not discoverable until runtime.

`OBJECT` uses nominal compatibility: its declared name is significant when comparing object types. It does not automatically infer arbitrary user-defined classes or perform general structural subtyping.

#### Custom storage access

By default, `OBJECT` fields are accessed using Python `getattr()`.

A custom accessor can retrieve declared attributes from mappings, row objects, external data containers, or specialized domain objects.

```
Record = T.OBJECT(    "Record",    attributes={        "id": T.FLOAT,        "status": T.STRING,    },    accessor=lambda obj, name: obj[name],)
```

This separates the logical schema visible to a rule from the physical representation of the data.

That distinction can eliminate substantial custom field-access and type-checking infrastructure when rule expressions must operate across a well-defined data model.

`OBJECT` also has stricter semantics than `MAPPING`: its declared fields are accessed through dot syntax, while indexed access and membership tests on the object itself are rejected.

### 5.4. Recursive and mutually recursive object schemas

`OBJECT` supports nested object graphs, including cycles.

The two principal mechanisms are:

- `DataType.OBJECT.self` for self-references.
- `DataType.OBJECT.reference(name)` for named forward references.

For example:

```
Node = T.OBJECT(    "Node",    attributes={        "name": T.STRING,        "parent": T.NULLABLE(T.OBJECT.self),    },)
```

Mutually recursive schemas can also be registered through a context's type resolver and resolved at rule-parse time.

These capabilities matter for trees, hierarchies, graphs, organizational structures, and relationship-rich domain models.

They permit a nested expression to retain type information across object boundaries instead of degenerating into untyped runtime traversal.

This does not create graph-query execution or cycle-safe recursive traversal automatically. A rule still follows the explicitly written sequence of attribute accesses.

### 5.5. First-class nullability

`NULLABLE(T)` is one of the most consequential features introduced in 5.0.

It encodes optionality in the static type rather than treating every symbol as implicitly nullable.

This allows the parser to distinguish three situations:

| Type          | Meaning                         |
| ------------- | ------------------------------- |
| `T`           | A value with declared type `T`  |
| `NULL`        | The explicit null value         |
| `NULLABLE(T)` | A value that can be `T` or null |

The engine uses Python-style null semantics, not SQL three-valued logic.

For example, with `score` declared as `NULLABLE(FLOAT)`, the expression:

```
score > 20
```

is rejected at parse time.

The rule author must first handle the possibility of null:

```
(score ?? 0) > 20
```

The `??` operator returns its left operand unless that operand is `null`; otherwise it returns the right operand.

This also discharges nullability in the static type, allowing subsequent operations requiring a non-null value.

#### Safe navigation

The nullable access operators offer another mechanism:

```
customer&.address&.postal_code
```

If an intermediate receiver is null, the safe operation returns null instead of raising an exception.

Safe navigation accepts nullability but does not eliminate it from the resulting type.

Consequently, a downstream operation can still require an explicit fallback:

```
(customer&.address&.postal_code ?? "") == "10001"
```

Safe item access similarly supports:

```
data&["optional_key"]
```

This returns null when the container is null or the requested item is unavailable.

Ordinary attribute access does not automatically suppress missing attributes or invalid schema fields.

#### Strict versus lenient operators

The nullable type checker is intentionally stricter for operations such as arithmetic, ordered comparisons, regex matching, indexing, and function argument passing.

Equality, logical operations, ternary expressions, and safe navigation permit nullable inputs.

This produces an important interaction: a Boolean guard is not necessarily enough to make an otherwise ill-typed expression valid.

The null handling must be expressed in a form the static type checker can establish.

For more detail, see the [NULLABLE semantics](https://zerosteiner.github.io/rule-engine/types.html?utm_source=chatgpt.com#nullable) and [tagged AST expression implementation](https://github.com/zeroSteiner/rule-engine/tree/v5.1.0/lib/rule_engine/ast?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zerosteiner.github.io\&sz=32)

Rule Engine 5.0.3 documentation

+1



### 5.6. Decimal-backed numerical semantics

Despite the name `FLOAT`, Rule Engine performs numeric evaluation using Python's `decimal.Decimal`.

This has several consequences:

1. Ordinary decimal fractions can be evaluated without the familiar binary floating-point representation artifacts.
2. Context-specific precision and rounding behavior can be configured.
3. Incoming Python floats are converted using their string representation rather than directly preserving their exact binary fraction.
4. Numeric coercion can change equality and dictionary-key behavior at engine boundaries.

The fourth point is particularly easy to overlook.

A Python `float` and `Decimal` that compare differently under native Python operations may become equivalent after Rule Engine normalizes them.

This can affect compound collections and even collapse dictionary keys that were distinct in the original Python mapping.

The library explicitly warns about collections mixing Python floats and Decimals.

A configurable `decimal.Context` gives control over numeric evaluation, but Decimal arithmetic should not be confused with unlimited precision or an assurance that arbitrary numerical algorithms are exact.

Source: [Numeric type semantics](https://zerosteiner.github.io/rule-engine/types.html?utm_source=chatgpt.com#float) and [type coercion API](https://zerosteiner.github.io/rule-engine/rule_engine/types.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zerosteiner.github.io\&sz=32)

Rule Engine 5.0.3 documentation

+1



## 6. Built-in functions, attributes, and expression composition

Rule Engine provides two complementary forms of reusable functionality:

1. Built-in symbols and functions, accessed with the `$` prefix.
2. Data attributes and methods, accessed from compatible values using dot notation.

These mechanisms can substantially reduce the amount of Python helper code needed for common transformations, predicates, and aggregate calculations.

### 6.1. Built-in function library

| Family                | Builtins                                              | Uses                                    |
| --------------------- | ----------------------------------------------------- | --------------------------------------- |
| Numeric operations    | `$abs`, `$min`, `$max`, `$sum`                        | Numeric calculations and aggregations   |
| Boolean aggregation   | `$all`, `$any`                                        | Evaluate arrays of truth values         |
| Functional operations | `$filter`, `$map`                                     | Apply callable values to arrays         |
| Sequences             | `$range`                                              | Generate numeric sequences              |
| Strings               | `$split`                                              | Tokenization and splitting              |
| Parsing               | `$parse_float`, `$parse_datetime`, `$parse_timedelta` | Convert textual input into typed values |
| Randomness            | `$random`                                             | Random numeric generation               |

Built-in constants and dynamic values include `$e`, `$pi`, `$now`, `$today`, and `$re_groups`.

Some of the most useful combinations involve comprehensions and aggregates:

```
$all([item["valid"] for item in items])

$any([item["severity"] == "critical" for item in findings])

$max([item["score"] for item in items])

$sum([item["quantity"] * item["price"] for item in items])
```

These expressions encode computations over nested data without external loops.

`$map` and `$filter` accept `FUNCTION` values, which can be supplied through the Python environment. Rule authors cannot define arbitrary functions or anonymous lambdas inside rule text, so comprehensions are often the more self-contained option.

### 6.2. Built-in data attributes

The attribute system contains a useful set of typed operations.

| Data type   | Representative attributes and methods                                                                                            |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `STRING`    | `length`, `is_empty`, `as_lower`, `as_upper`, `starts_with()`, `ends_with()`, `to_int`, `to_flt`, `to_ary`, `to_set`, `encode()` |
| `ARRAY`     | `length`, `is_empty`, `starts_with()`, `ends_with()`, `to_set`                                                                   |
| `SET`       | `length`, `is_empty`, `to_ary`                                                                                                   |
| `MAPPING`   | `length`, `is_empty`, `keys`, `values`                                                                                           |
| `BYTES`     | `length`, `starts_with()`, `ends_with()`, `encode`-related conversion through `decode()`, `to_ary`, `to_set`                     |
| `DATETIME`  | `year`, `month`, `day`, `hour`, `minute`, `second`, `weekday`, `date`, `to_epoch`, `zone_name`                                   |
| `TIMEDELTA` | `days`, `seconds`, `microseconds`, `total_seconds`                                                                               |
| `FLOAT`     | `floor`, `ceiling`, `is_nan`, `to_str`, `to_flt`                                                                                 |

These attributes are type-aware and are resolved through the library's attribute-resolution infrastructure.

For example:

```
name.as_lower == "alice"

tags.length > 3

started + t"P7D" < $now

payload.decode("utf-8") == "approved"
```

String encoding and bytes decoding support Python-recognized encodings, along with hexadecimal and Base16/Base64 conversions.

`OBJECT` attributes behave differently: they are restricted to the declared schema, rather than exposing the generic built-in attribute table.

This distinction is valuable because it preserves the intended model boundary for a typed object.

### 6.3. Time-dependent evaluation

`$now` and `$today` are resolved using the context's configured timezone.

Combined with datetime literals, durations, and datetime attributes, these symbols support rules for expiration, age thresholds, elapsed-time conditions, and time-window classification.

The evaluation is time-dependent: running the same expression against unchanged input data can produce a different result later.

If reproducibility is required, the evaluation time can instead be supplied explicitly as an input symbol or controlled through a custom builtin.

Sources: [Builtin functions and symbols](https://zerosteiner.github.io/rule-engine/syntax.html?utm_source=chatgpt.com#builtin-symbols), [Data attributes](https://zerosteiner.github.io/rule-engine/attributes.html?utm_source=chatgpt.com), [5.1.0 builtin implementation](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/builtins.py?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zerosteiner.github.io\&sz=32)

Rule Engine 5.0.3 documentation



## 7. Integration with Python data models

A major benefit of the 5.x architecture is that Rule Engine can derive substantial portions of its type environment from existing Python models.

This is especially useful for minimizing duplicated schema definitions.

### 7.1. Dataclass integration

The principal APIs are:

- `DataType.OBJECT.from_dataclass(name, cls)`
- `type_resolver_from_dataclass(cls)`

The first constructs an explicit `OBJECT` schema. The second creates a type resolver suitable for use with a `Context`.

The extraction machinery understands ordinary dataclass fields, supported Python type annotations, generic collections, optional fields, nested dataclasses, and self-referential or mutually recursive model relationships.

```
from dataclasses import dataclassimport rule_engine@dataclassclass Account:    balance: float    active: bool    region: str | Nonecontext = rule_engine.Context(    resolver=rule_engine.resolve_attribute,    type_resolver=rule_engine.type_resolver_from_dataclass(Account),)rule = rule_engine.Rule(    'active and balance > 100 and (region ?? "") == "US"',    context=context,)rule.matches(Account(250.0, True, "US"))# True
```

The key architectural benefit is the separation of responsibilities:

- The dataclass remains the Python data model.
- The type extractor derives the expression-language schema.
- The context governs data access.
- The rule engine validates and evaluates expressions.

The same model annotations therefore contribute to both Python-side structure and rule-side type validation.

`strict=True` is the default for schema extraction. Unsupported field types produce errors rather than silently becoming untyped. With `strict=False`, unsupported fields become `DataType.UNDEFINED`, sacrificing static checking for those fields.

### 7.2. SQLAlchemy ORM integration

SQLAlchemy integration is another significant addition from version 5.0 that is fully relevant to 5.1.0.

The corresponding APIs are:

- `DataType.OBJECT.from_sqlalchemy(name, cls)`
- `type_resolver_from_sqlalchemy(cls)`

They derive rule schemas from SQLAlchemy ORM mapped classes, including mapped columns and relationships.

The extractor supports several noteworthy distinctions.

| SQLAlchemy construct                   | Rule Engine representation                      |
| -------------------------------------- | ----------------------------------------------- |
| Ordinary mapped column                 | `DataType` inferred from the Python type        |
| Nullable column                        | `NULLABLE(T)`                                   |
| Scalar relationship                    | Nested `OBJECT`, potentially nullable           |
| Collection relationship                | `ARRAY(OBJECT(...))`                            |
| Self-referential relationship          | `OBJECT.self`                                   |
| Mutually recursive relationships       | Named `OBJECT.reference()`                      |
| SQLAlchemy `ARRAY`                     | Typed `ARRAY(T)` when element type is supported |
| SQLAlchemy `JSON`                      | `MAPPING(UNDEFINED, UNDEFINED)`                 |
| Ordinary SQLAlchemy `Enum`             | `STRING`                                        |
| Integer-subclass enum                  | `FLOAT`                                         |
| Unmappable column under `strict=False` | `UNDEFINED`                                     |

An illustrative integration:

```
context = rule_engine.Context(    resolver=rule_engine.resolve_attribute,    type_resolver=rule_engine.type_resolver_from_sqlalchemy(Order),)rule = rule_engine.Rule(    'customer.status == "active" and total > 100',    context=context,)
```

The rule can be checked against the mapped schema, including attributes reached through relationships.

#### What the integration does not provide

The SQLAlchemy integration is schema introspection, not SQL compilation.

`type_resolver_from_sqlalchemy()` does not produce SQLAlchemy `ClauseElement` expressions, construct ORM queries, or push rule evaluation into PostgreSQL or another database.

The rule is still evaluated against Python objects supplied by the caller.

If those objects are live SQLAlchemy ORM instances, dereferencing relationships during evaluation can trigger lazy loading. This may introduce database round trips, particularly for comprehensions over collections or chains evaluating many relationship-dependent rules.

There is no automatic query-plan integration, eager-loading policy, or SQL translation implied by schema extraction.

The documented introspection also has scope limits. Hybrid properties, polymorphic and inherited mapping behavior, and computed `column_property` aggregates are not comprehensively represented by this extractor. Unsupported column types, including common dialect-specific types such as UUID, may require `strict=False` or an explicit schema.

This creates an important distinction between schema interoperability and execution interoperability. Rule Engine provides the former natively, but the latter may still require application-specific integration.

Primary sources: [SQLAlchemy schema extraction](https://zerosteiner.github.io/rule-engine/types.html?utm_source=chatgpt.com#from-a-sqlalchemy-model), [SQLAlchemy type-walking implementation](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/types/sqlalchemy.py?utm_source=chatgpt.com), [type resolver implementation](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/engine/context.py?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zerosteiner.github.io\&sz=32)

Rule Engine 5.0.3 documentation

+1



### 7.3. `OBJECT` as an integration boundary

Taken together, manual `OBJECT` schemas, dataclass extraction, SQLAlchemy extraction, and custom accessors allow the same rule-language architecture to work with several backing representations.

This can be particularly valuable in systems that operate on both persisted objects and transient in-memory structures.

However, the benefits depend on retaining compatible runtime values and access semantics. A shared declared schema does not automatically reconcile inconsistent object representations or guarantee identical behavior from different accessors.

The rule engine supplies a common language and validation layer; the caller remains responsible for ensuring that data sources satisfy the declared model.

## 8. `Context` and runtime extension mechanisms

The `Context` class defines how the expression language interacts with its surrounding Python environment.

Its principal configuration parameters are:

| Parameter                  | Responsibility                                 |
| -------------------------- | ---------------------------------------------- |
| `resolver`                 | Resolve top-level symbol values                |
| `type_resolver`            | Establish symbol types during parsing          |
| `regex_flags`              | Configure regex matching behavior              |
| `default_timezone`         | Establish timezone semantics                   |
| `default_value`            | Handle unresolved symbols and attributes       |
| `decimal_context`          | Define Decimal precision and rounding          |
| `mapping_attribute_lookup` | Control deprecated mapping dot-lookup behavior |

The central architectural distinction is between value resolution and type resolution.

### 8.1. Runtime symbol resolvers

The default resolver, `resolve_item`, obtains symbols from mapping keys.

`resolve_attribute` instead obtains values through Python attribute access.

A custom resolver implements the interface:

```
resolver(thing, name) -> value
```

This permits expressions to operate over alternative data representations, including objects with special retrieval rules or data exposed through a constrained adapter.

A custom resolver should raise `SymbolResolutionError` for unknown symbols, rather than relying on arbitrary host-language exceptions.

The library also provides suggestion utilities that can recommend nearby valid names when a symbol cannot be resolved.

A security consideration is that `resolve_attribute` potentially exposes all attributes on the supplied Python object. The official API explicitly warns that a custom allowlisting resolver should be used when some attributes are sensitive.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zerosteiner.github.io\&sz=32)

Rule Engine 5.0.3 documentation



### 8.2. Type resolvers and schema validation

A type resolver provides:

```
type_resolver(name) -> DataType
```

The parser consults this when constructing a rule.

The simplest configuration is a dictionary:

```
context = rule_engine.Context(    type_resolver={        "name": rule_engine.DataType.STRING,        "age": rule_engine.DataType.FLOAT,        "active": rule_engine.DataType.BOOLEAN,    })
```

The context automatically converts a mapping into the appropriate type resolver.

This supports two distinct validation policies.

A resolver that returns `UNDEFINED` for arbitrary symbols permits flexible expressions while offering weaker type checking.

A resolver with an explicit known-symbol set rejects unknown symbol names during rule construction, enabling schema validation before any records are evaluated.

The latter can be valuable for declarative configuration systems where a misspelled field should fail immediately rather than silently produce incorrect behavior.

### 8.3. Custom callable integration through `FUNCTION`

Python functions can be exposed as symbols or builtin functions.

For typed callables, `DataType.FUNCTION` describes:

- Function name.
- Expected argument types.
- Result type.
- Minimum argument count.

For example:

```
T = rule_engine.DataTypedef normalize(value):    return value.strip().lower()normalize_type = T.FUNCTION(    "normalize",    argument_types=(T.STRING,),    return_type=T.STRING,)context = rule_engine.Context(    type_resolver={        "name": T.STRING,        "normalize": normalize_type,    })rule = rule_engine.Rule(    'normalize(name) == "alice"',    context=context,)rule.matches({    "name": "  Alice  ",    "normalize": normalize,})# True
```

Typed functions can be checked for argument compatibility, and incompatible returned values can produce `FunctionCallError`.

Rule-language calls use positional arguments. Optional trailing arguments are supported through `minimum_arguments`; keyword arguments are not.

A function's own Python implementation remains responsible for its behavior. Rule Engine does not make externally supplied callables pure, side-effect-free, or computationally bounded.

### 8.4. Custom builtins

The `Builtins` class provides a separate namespace from ordinary input symbols.

`Builtins.from_defaults()` retains the standard builtins while allowing additional symbols or overrides.

Replacing the builtin table entirely allows a more constrained language environment.

An application-defined context can, for example, expose standardized conversions, domain predicates, or controlled lookup functions without requiring them to appear repeatedly in every input object.

This is another mechanism for reducing bespoke expression-handling code: callable definitions, type signatures, and rule syntax can remain separate concerns.

The builtin interface also supports dynamically generated values. This is how current-time values and regex-capture state are made available.

Sources: [Context and resolver API](https://zerosteiner.github.io/rule-engine/rule_engine/engine.html?utm_source=chatgpt.com), [Builtins API](https://zerosteiner.github.io/rule-engine/rule_engine/builtins.html?utm_source=chatgpt.com), [5.1.0 builtins source](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/builtins.py?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zerosteiner.github.io\&sz=32)

Rule Engine 5.0.3 documentation



## 9. Diagnostics, validation, and developer tooling

Rule Engine exposes several mechanisms that are useful for understanding why a rule is invalid, inspecting the expression structure, and identifying which rule produced a decision.

### 9.1. Structured exception hierarchy

The library defines its own exception types rather than requiring callers to interpret arbitrary interpreter errors.

| Error family      | Representative exceptions                                  | Significance                                 |
| ----------------- | ---------------------------------------------------------- | -------------------------------------------- |
| Parsing           | `RuleSyntaxError`, `StringSyntaxError`, `RegexSyntaxError` | Invalid grammar or literals                  |
| Type checking     | `EvaluationError`, `SymbolTypeError`, `AttributeTypeError` | Incompatible operations or values            |
| Symbol lookup     | `SymbolResolutionError`                                    | Unknown or inaccessible top-level symbols    |
| Attribute lookup  | `AttributeResolutionError`, `ObjectAttributeError`         | Missing or invalid nested attributes         |
| Collection access | `LookupError`                                              | Failed indexing or key lookup                |
| Functions         | `FunctionCallError`                                        | Argument, invocation, or return-value errors |
| Arithmetic        | `ArithmeticError`                                          | Invalid arithmetic evaluation                |
| Rule chains       | `ChainExhaustedError`                                      | No matching rule and no configured default   |

These exceptions are useful for separating invalid rule definitions from invalid runtime inputs.

For example, a syntax error in a user-authored rule might be returned to the author for correction, whereas an unexpected `SymbolTypeError` during evaluation may indicate that the application supplied data inconsistent with the declared schema.

Symbol and attribute resolution errors can also carry suggestions, improving feedback when expressions reference misspelled names.

The distinction between parse-time and runtime failures remains important. Type information improves early validation but does not eliminate runtime errors from data access, Python callables, or inconsistent values.

Source: [Exception reference](https://zerosteiner.github.io/rule-engine/rule_engine/errors.html?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zerosteiner.github.io\&sz=32)

Rule Engine 5.0.3 documentation



### 9.2. Rule and symbol inspection

`Rule.is_valid()` provides a straightforward validity check.

`Context.symbols` exposes symbol names encountered during rule parsing. This can support dependency inspection, schema validation, or presentation of the external values an expression may require.

A subtle implementation detail is that `symbols` belongs to the `Context`. Multiple rules sharing a context can contribute to the same symbol set, so it should not be treated as an automatically isolated dependency list for each individual rule.

`Rule.statement` also exposes the parsed AST, including its expression structure and result types. However, this is a substantially less stable extension surface.

### 9.3. Graphviz AST visualization

`Rule.to_graphviz()` generates a Graphviz representation of the parsed expression tree.

This can help inspect nested expressions, understand grouping and operator precedence, and diagnose unexpectedly complex rule structures.

The method depends on the optional Python `graphviz` package. Rendering the generated graph may also require the Graphviz system tools.

The upstream documentation explicitly cautions that the `rule_engine.ast` module should be treated as private, even though its classes are documented. Internal AST APIs can change incompatibly without a major version increment.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zerosteiner.github.io\&sz=32)

Rule Engine 5.0.3 documentation



Consequently, AST visualization is an established capability, but direct modification of internal AST nodes is not a comparably stable public extension mechanism.

### 9.4. Debug REPL

Rule Engine includes an interactive debugging interface:

```
python -m rule_engine.debug_repl
```

It supports evaluating expressions against configurable objects and contexts.

The `--edit-console` and `--edit-file` options provide mechanisms for initializing that environment.

In the 5.x series, the REPL requires development dependencies. The tagged implementation checks for IPython and `prompt_toolkit` and directs development installations to use `uv sync --group dev`.

This is a useful distinction between the lightweight runtime library and its richer development tooling.

The REPL's environment-configuration features can execute Python code. They therefore have a different trust boundary from evaluating a rule expression through the normal parser.

Sources: [Debug REPL guide](https://zerosteiner.github.io/rule-engine/debug_repl.html?utm_source=chatgpt.com), [5.1.0 REPL implementation](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/debug_repl.py?utm_source=chatgpt.com).&#x20;

[image](https://www.google.com/s2/favicons?domain=https://zerosteiner.github.io\&sz=32)

Rule Engine 5.0.3 documentation



## 10. Execution architecture, concurrency, and performance

Rule Engine is designed to make reusable expression evaluation relatively inexpensive compared with repeatedly parsing rules. However, its execution strategy is still a Python-level AST interpreter.

Understanding that distinction is essential when considering larger rule collections, nested data, or high-throughput evaluation.

### 10.1. Preparation versus execution

The main performance mechanisms are:

| Mechanism                       | Effect                                                                   |
| ------------------------------- | ------------------------------------------------------------------------ |
| Reusable `Rule` AST             | Avoids reparsing for every evaluated object                              |
| Construction-time type checking | Moves some validation cost out of repeated evaluation                    |
| Constant AST reduction          | Precomputes supported expressions whose results are known during parsing |
| Literal regex compilation       | Avoids recompilation of fixed regular expressions for each match         |
| Short-circuit operators         | Skips unnecessary expression branches                                    |
| Ordered-chain termination       | Skips remaining rules after the first match                              |
| Decimal context management      | Maintains defined numerical behavior across evaluation threads           |

The benefit of these mechanisms depends on workload characteristics.

For example, constant reduction is useful when a complicated expression contains substantial invariant work. It does not eliminate the cost of repeatedly resolving object attributes or traversing large input collections.

Similarly, a `Chain` can avoid evaluating rules after an early match, but selecting a late rule still requires evaluating preceding entries.

### 10.2. Parser synchronization

The tagged parser uses a mutex around the grammar-parsing phase.

This is necessary because parser state is shared and mutable during construction.

The practical implication is that creating rules concurrently is not the same operation as evaluating already-constructed rules concurrently.

Rule construction has a serialized portion. Rule evaluation can reuse the resulting expression structures across threads.

The parser also separates grammar parsing from a subsequent AST-building phase, during which additional validation and expression reduction occur.

See the [tagged parser base implementation](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/parser/base.py?utm_source=chatgpt.com).

### 10.3. Thread-safe evaluation

The library uses thread-local state for evaluation-scoped data, including comprehension assignments and regex captures.

`Rule.evaluate()` resets the relevant thread-local state and uses the configured Decimal context while evaluating the rule.

This enables shared rule and context instances to be evaluated by different threads without mixing their internal temporary expression state.

Version 5.1.0 extends this model with snapshot-based chain evaluation.

However, these guarantees do not extend automatically to mutable Python objects accessed by resolvers or functions.

A custom callable that mutates shared application state still requires whatever synchronization or concurrency controls that callable would ordinarily need.

### 10.4. Rule-chain complexity

The implementation of `Chain.find()` is a sequential loop over the chain's entries.

For a chain containing \\(n\\) rules, the worst-case selection work is proportional to the number of rules examined, assuming a fixed cost per predicate.

In practice, the total cost is determined by both rule position and predicate complexity.

This has several consequences:

- Rule ordering affects performance as well as semantics.
- An inexpensive early predicate may save substantial work if it frequently matches.
- Large comprehensions and costly Python callbacks can dominate the evaluation cost of individual rules.
- Chain mutations copy existing entries, while evaluation reads a stable snapshot.
- The engine does not construct indexes or optimize collections of related predicates into a shared decision structure.

The library therefore reduces orchestration and expression-management code, but it does not supply a general-purpose optimizer for very large rule sets.

### 10.5. Data-access costs

Data retrieval can be more expensive than the expression interpreter itself.

Examples include:

- Resolving Python properties with substantial computation.
- Accessing ORM relationships that trigger database queries.
- Converting large compound values into Rule Engine-compatible representations.
- Repeatedly traversing nested collections.
- Executing expensive Python callables.
- Compiling dynamically supplied regex patterns.

An important architectural possibility is to use Rule Engine after a separate query or processing engine has selected and materialized the necessary records.

That arrangement can combine efficient relational filtering with expressive application-level decisions, without incorrectly assuming that Rule Engine itself provides SQL pushdown or vectorized execution.

These observations are architectural implications of the implementation, not claims that a particular integration delivers measured performance improvements.

### 10.6. Serialization and lifecycle considerations

`Rule` and `Context` support pickling, introduced in 5.0, and `Chain` adds pickling in 5.1.0.

There are noteworthy implementation details:

Rules are reparsed after deserialization. The tagged `Rule.__getstate__()` stores the expression text and context. `Rule.__setstate__()` reconstructs the AST using the parser. Serialization therefore preserves the logical rule configuration rather than simply restoring an already-compiled execution tree.

Custom resolvers must be picklable. Module-level functions are generally more suitable for this than closures or lambdas.

Custom builtin state requires attention. In the 5.1.0 implementation, the base `Context` serialization excludes its builtin table and recreates default builtins when restored. Applications using modified builtin tables may need custom restoration behavior rather than assuming those modifications are serialized by the base class.

Chains preserve shared contexts within the serialized object graph. Existing `Rule` instances in chains retain their individual contexts.

These distinctions matter for serialization caches, process boundaries, and reproducibility.

Sources: [Tagged Rule implementation](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/engine/rule.py?utm_source=chatgpt.com), [Context implementation](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/engine/context.py?utm_source=chatgpt.com), [Chain implementation](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/engine/chain.py?utm_source=chatgpt.com).

## 11. Security and trust boundaries

Rule Engine's independent expression grammar is an important security feature.

It prevents rule text from being interpreted as arbitrary Python source code using `eval()` or `exec()`.

However, this is not equivalent to a resource-constrained execution sandbox.

The distinction matters when expressions are authored by external users or other potentially untrusted sources.

| Risk or boundary          | Relevant behavior                                                                   |
| ------------------------- | ----------------------------------------------------------------------------------- |
| Arbitrary Python syntax   | Not exposed through the expression grammar                                          |
| Host-object access        | Determined by symbol resolvers and declared schemas                                 |
| Python function execution | Explicitly possible through exposed `FUNCTION` values                               |
| Expensive regex           | Uses Python regex functionality, without a documented general execution-time budget |
| Expensive comprehensions  | Can allocate arrays and perform substantial iterative work                          |
| Object properties         | May perform arbitrary work when accessed                                            |
| Database access           | ORM attribute access can invoke lazy loading                                        |
| Serialization             | Python pickle must not be loaded from untrusted sources                             |
| Debug REPL                | Configuration features can execute Python code                                      |

`OBJECT` schemas and explicit type resolvers are valuable mechanisms for constraining the data surface available to rule authors.

For adversarial expressions, additional controls may still be appropriate, including permitted-symbol policies, restricted callable exposure, limits on input and expression complexity, and evaluation isolation where resource exhaustion is a concern.

There is no documented general-purpose evaluator timeout, instruction budget, or memory-allocation limit in the 5.1.0 public API.

Likewise, exposing arbitrary Python objects and callable values can defeat the practical safety benefits of using a restricted expression grammar.

The proper security model is therefore constrained expression syntax plus carefully controlled host-language capabilities, not unrestricted sandboxed execution.

## 12. Version compatibility, deprecations, and dependencies

### 12.1. Version 5.x changes that materially affect usage

Version 5.1.0 inherits several consequential changes from 5.0.0.

| Change                           | Version | Significance                                            |
| -------------------------------- | ------- | ------------------------------------------------------- |
| `OBJECT` schemas                 | 5.0.0   | Typed nested models and parse-time attribute validation |
| Dataclass schema extraction      | 5.0.0   | Derive schemas from Python annotations                  |
| SQLAlchemy ORM schema extraction | 5.0.0   | Reuse mapped columns and relationships                  |
| `NULLABLE(T)`                    | 5.0.0   | First-class optionality                                 |
| `??` operator                    | 5.0.0   | Explicit null-coalescing                                |
| Raw string literals              | 5.0.0   | Easier regular-expression authoring                     |
| Rule and Context pickling        | 5.0.0   | Serialized rule configurations                          |
| Operator precedence changes      | 5.0.0   | Potential semantic differences for existing rules       |
| Vendored PLY                     | 5.0.0   | Removes an external runtime parser dependency           |
| Python 3.6–3.9 support removed   | 5.0.0   | Python 3.10 minimum                                     |
| `Chain` and `ChainEntry`         | 5.1.0   | Ordered first-match decisions                           |
| `ChainExhaustedError`            | 5.1.0   | Explicit unmatched-chain failure                        |
| Thread-safe chain mutation       | 5.1.0   | Snapshot-based concurrent evaluation                    |
| `UNDEFINED` serialization fix    | 5.1.0   | Correct missing-value behavior after restoration        |

### 12.2. Deprecations carried into 5.1.0

Two deprecations from 5.0 deserve particular attention.

Mapping dot access: accessing a mapping key as `mapping.key` is deprecated. The preferred form is `mapping["key"]`.

The context parameter:

```
rule_engine.Context(mapping_attribute_lookup=False)
```

allows an application to disable the deprecated fallback immediately.

The project documents removal of this fallback in version 6.0.

Legacy nullable constructor arguments: the `attributes_nullable` and `value_type_nullable` arguments remain supported for compatibility, but now emit deprecation warnings.

First-class `NULLABLE(T)` wrappers replace these older representations and are the preferred way to define nullable fields and collection members.

The removal of these legacy arguments is documented for the future 6.0 release; it is not a completed change in 5.1.0.

### 12.3. Package dependencies

The tagged `pyproject.toml` declares:

| Dependency or requirement    | Status                                    |
| ---------------------------- | ----------------------------------------- |
| Python 3.10+                 | Required                                  |
| `python-dateutil~=2.7`       | Required runtime dependency               |
| PLY                          | Vendored into the package                 |
| SQLAlchemy 2.0+              | Optional, for ORM schema extraction       |
| Python `graphviz`            | Optional, for AST visualization           |
| IPython and `prompt_toolkit` | Development REPL dependencies             |
| `uv`                         | Used in the upstream development workflow |

Rule Engine is distributed under the BSD 3-Clause license.

Source: [Version 5.1.0 package metadata](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/pyproject.toml?utm_source=chatgpt.com).

## 13. Architectural positioning and consequential limitations

Rule Engine occupies a useful middle ground between handwritten Python predicates and substantially heavier decision-management systems.

It provides a specialized expression interpreter with unusually rich support for Python object typing and introspection.

Its greatest advantages emerge when rule definitions need to be separated from application implementation while preserving structured-data awareness.

### 13.1. Functional boundaries

| Problem family               | Native support                     | Important boundary                                    |
| ---------------------------- | ---------------------------------- | ----------------------------------------------------- |
| Object filtering             | Strong                             | Evaluates supplied Python objects                     |
| User-authored expressions    | Strong                             | Host capabilities and resource limits require control |
| Typed rule validation        | Strong                             | Limited to the supported type system                  |
| Nested object conditions     | Strong                             | Data access may have side effects or retrieval costs  |
| Aggregate expressions        | Supported                          | In-memory array-oriented execution                    |
| First-match decisions        | Strong in 5.1.0                    | Ordered sequential evaluation                         |
| Business-rule classification | Supported                          | No built-in policy authoring or governance platform   |
| Database rule execution      | Schema integration                 | No native SQL compilation or pushdown                 |
| Event-driven rule activation | Not a documented engine capability | Requires external triggering                          |
| Forward-chaining inference   | Not a documented engine capability | No RETE-style agenda or fact engine                   |
| Workflow orchestration       | Not a documented engine capability | No native action lifecycle                            |
| Distributed evaluation       | Not a documented engine capability | Requires external orchestration                       |
| Rule audit/explanation       | Partial building blocks            | No complete built-in provenance system                |

### 13.2. Distinction from a production rule system

The name rule engine can describe several substantially different architectural categories.

This library is principally an expression and ordered-predicate evaluation engine.

It does not implement a RETE network, automatically maintain a working memory of facts, schedule activations when facts change, or derive new facts through repeated forward chaining.

Its new `Chain` abstraction is also not a general workflow engine. A matching entry returns a configured Python value; it does not automatically execute an action, persist state transitions, or manage downstream activities.

These differences are not deficiencies for the library's intended role. They help keep the underlying model understandable and relatively lightweight.

### 13.3. High-value capability combinations

Several native combinations are particularly noteworthy.

Typed models + nullable semantics + parse-time validation

This combination allows expressions to be authored against well-defined schemas, rejecting invalid attribute references and unsupported operations early. It can replace a substantial amount of custom rule validation.

Dataclass or SQLAlchemy extraction + custom value resolvers

Schema extraction can reuse model definitions while runtime resolvers retrieve values from the desired backing representation. This reduces schema duplication while preserving control over data access.

Comprehensions + builtins + numeric/temporal types

This enables relatively expressive conditions over collections and time-dependent values without implementing a separate mini-language or numerous bespoke helper functions.

`Chain` + `Chain.find()` + rule metadata

Ordered evaluation can be combined with application-managed metadata and logging to produce explainable first-match decisions.

Reusable ASTs + serialized configurations + shared contexts

This supports separating rule-definition lifecycle from repeated evaluation, subject to the serialization and concurrency qualifications described earlier.

These mechanisms illustrate where Rule Engine can eliminate custom infrastructure. They do not imply that the library should replace specialized database, analytical, workflow, or high-performance numerical engines.

## 14. Primary-source reference map

The following resources collectively provide a detailed technical reference for 5.1.0. Version-sensitive links point directly to the release tag so that later upstream changes do not silently alter the source being examined.

| Resource                                     | Direct URL                                                                                                                                                                                                        |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Version 5.1.0 release                        | [https://github.com/zeroSteiner/rule-engine/releases/tag/v5.1.0](https://github.com/zeroSteiner/rule-engine/releases/tag/v5.1.0?utm_source=chatgpt.com)                                                           |
| Version 5.1.0 changelog                      | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/docs/source/change_log.rst](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/docs/source/change_log.rst?utm_source=chatgpt.com)                     |
| Getting started, advanced APIs, and chains   | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/docs/source/getting_started.rst](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/docs/source/getting_started.rst?utm_source=chatgpt.com)           |
| Expression grammar and builtins              | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/docs/source/syntax.rst](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/docs/source/syntax.rst?utm_source=chatgpt.com)                             |
| Data type semantics, `OBJECT`, `NULLABLE`    | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/docs/source/types.rst](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/docs/source/types.rst?utm_source=chatgpt.com)                               |
| Data attributes and builtin methods          | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/docs/source/attributes.rst](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/docs/source/attributes.rst?utm_source=chatgpt.com)                     |
| Rule evaluation implementation               | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/engine/rule.py](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/engine/rule.py?utm_source=chatgpt.com)             |
| Context, resolvers, thread-local state       | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/engine/context.py](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/engine/context.py?utm_source=chatgpt.com)       |
| Chain implementation                         | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/engine/chain.py](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/engine/chain.py?utm_source=chatgpt.com)           |
| DataType implementation                      | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/types/datatype.py](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/types/datatype.py?utm_source=chatgpt.com)       |
| Typed object schemas                         | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/types/\_object.py](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/types/_object.py?utm_source=chatgpt.com)        |
| SQLAlchemy model integration                 | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/types/sqlalchemy.py](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/types/sqlalchemy.py?utm_source=chatgpt.com)   |
| Parser and grammar definitions               | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/parser/\_\_init\_\_.py](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/parser/__init__.py?utm_source=chatgpt.com) |
| AST implementation                           | [https://github.com/zeroSteiner/rule-engine/tree/v5.1.0/lib/rule_engine/ast](https://github.com/zeroSteiner/rule-engine/tree/v5.1.0/lib/rule_engine/ast?utm_source=chatgpt.com)                                   |
| Builtin symbol implementation                | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/builtins.py](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/builtins.py?utm_source=chatgpt.com)                   |
| Exception types                              | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/errors.py](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/lib/rule_engine/errors.py?utm_source=chatgpt.com)                       |
| Rule-chain tests                             | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/tests/chain.py](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/tests/chain.py?utm_source=chatgpt.com)                                             |
| Concurrency tests                            | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/tests/thread_safety.py](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/tests/thread_safety.py?utm_source=chatgpt.com)                             |
| Package dependencies and Python requirements | [https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/pyproject.toml](https://github.com/zeroSteiner/rule-engine/blob/v5.1.0/pyproject.toml?utm_source=chatgpt.com)                                             |

The rendered documentation remains valuable for navigation and API descriptions:

- [https://zerosteiner.github.io/rule-engine/](https://zerosteiner.github.io/rule-engine/?utm_source=chatgpt.com)
- [https://zerosteiner.github.io/rule-engine/rule_engine/engine.html](https://zerosteiner.github.io/rule-engine/rule_engine/engine.html?utm_source=chatgpt.com)
- [https://zerosteiner.github.io/rule-engine/rule_engine/types.html](https://zerosteiner.github.io/rule-engine/rule_engine/types.html?utm_source=chatgpt.com)
- [https://zerosteiner.github.io/rule-engine/rule_engine/parser/index.html](https://zerosteiner.github.io/rule-engine/rule_engine/parser/index.html?utm_source=chatgpt.com)
- [https://zerosteiner.github.io/rule-engine/debug_repl.html](https://zerosteiner.github.io/rule-engine/debug_repl.html?utm_source=chatgpt.com)

Because the rendered pages were still labeled 5.0.3 during this research, the tagged files above are the authoritative reference for capabilities newly introduced in 5.1.0.

## Overall assessment

Rule Engine 5.1.0 is best understood as a typed, extensible Python expression engine with ordered decision evaluation.

Its primary value lies in the combination of a standalone rule language, reusable AST evaluation, schema-driven type checking, compound data operations, and controlled access to Python functionality.

The most architecturally consequential developments in the 5.x series are the `OBJECT` and `NULLABLE` type systems, direct dataclass and SQLAlchemy schema extraction, and the new `Chain` abstraction.

Together, these capabilities make it possible to construct sophisticated declarative decision layers using comparatively little custom parser, validator, or rule-dispatch code.

The library's principal constraints are equally clear: evaluation is Python-level and object-oriented rather than vectorized or relationally optimized; typed schemas do not imply database execution; and the constrained grammar does not itself guarantee bounded resource consumption.

For workloads fitting its expression-evaluation model, Rule Engine offers a technically substantive foundation. Its most distinctive capability is not any one operator or API, but the way typed object models, configurable evaluation semantics, and reusable rule definitions compose into a compact declarative decision system.