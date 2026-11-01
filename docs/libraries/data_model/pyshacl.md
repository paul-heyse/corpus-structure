# PySHACL 0.40.1 — Comprehensive Library Capability Reference

Python · RDF validation · SHACL · Knowledge graphs · Semantic reasoning · Rule execution

Target version: 0.40.1, released July 28, 2026 Research date: October 21, 2026 Upstream: RDFLib/pySHACL License: Apache 2.0 Python requirement: 3.9 or newer

Primary repository: [https://github.com/RDFLib/pySHACL](https://github.com/RDFLib/pySHACL?utm_source=chatgpt.com)

Package: [https://pypi.org/project/pyshacl/](https://pypi.org/project/pyshacl/?utm_source=chatgpt.com)

Release history: [https://github.com/RDFLib/pySHACL/releases](https://github.com/RDFLib/pySHACL/releases?utm_source=chatgpt.com)

Version 0.40.1 is the latest stable release verified against PyPI and upstream releases. It follows the substantial 0.40.0 release, which introduced native compatibility with Oxigraph-backed RDF stores and a new graph abstraction layer. These changes materially expand PySHACL's role beyond its traditional RDFLib-only validation architecture.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2



## 1. Executive overview

PySHACL is a declarative RDF graph validation engine that also provides semantic reasoning, programmable graph constraints, inference rules, and graph expansion.

Its primary responsibility is to evaluate RDF data against constraints expressed in the W3C Shapes Constraint Language (SHACL). Unlike a conventional Python validation library, where rules are implemented as Python functions or model validators, PySHACL executes constraints defined as RDF graphs themselves.

The resulting architecture separates four concerns:

| Concern                  | Responsibility                                                                         |
| ------------------------ | -------------------------------------------------------------------------------------- |
| RDF data                 | The entities, relationships, and literal values being examined                         |
| SHACL shapes             | Declarative constraints, structural expectations, and validation logic                 |
| Ontologies and inference | Additional semantic knowledge and inferred relationships                               |
| PySHACL engine           | Target discovery, constraint evaluation, rule execution, and standards-based reporting |

This separation is important. Shapes can be maintained, versioned, published, imported, tested, and reused independently of application code. Complex constraints can be expressed using RDF structures, SPARQL queries, and SHACL extension mechanisms rather than bespoke procedural validation.

PySHACL can therefore fulfill several distinct roles:

| Capability family                | What PySHACL provides                                                                                      |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Structural validation            | RDF types, cardinalities, required relationships, literal constraints, property comparisons, closed shapes |
| Relational and graph validation  | Nested shapes, logical composition, qualified counts, recursive paths, cross-node constraints              |
| Programmable validation          | SPARQL-based constraints and custom constraint components                                                  |
| Semantic validation              | RDFS and OWL 2 RL pre-inference combined with SHACL evaluation                                             |
| Declarative graph transformation | SHACL Triple Rules, SPARQL Rules, and rule expansion                                                       |
| Advanced computation             | SHACL functions, node expressions, custom targets, and expression constraints                              |
| JavaScript extensibility         | SHACL-JS constraints, functions, targets, and rules through an optional runtime                            |
| Execution control                | Shape selection, focus-node filtering, severity handling, and early termination                            |
| Data integration                 | RDFLib graphs and datasets, Oxigraph stores, multiple input graphs, and remote SPARQL endpoints            |
| Operational interfaces           | Python API, command-line validation, rules-expansion CLI, HTTP service, and Docker                         |
| Diagnostics and interchange      | RDF validation reports, text reports, machine-readable serialization, and structured errors                |

The distinctive value is the combination of these capabilities. PySHACL can validate the structure and semantics of a graph, derive additional facts using inference or declarative rules, and validate the resulting graph using a common language and execution framework.

Its implementation also builds upon substantial existing infrastructure: RDFLib for RDF operations and SPARQL, OWL-RL for reasoning, and, as of version 0.40.0, optional PyOxigraph support.

Important boundary: PySHACL is not itself a general-purpose graph database, ontology editor, full OWL reasoner, or RDF ingestion platform. Its strength is applying declarative validation and rule semantics to RDF data supplied by those systems.

Official capability matrix: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md](https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md?utm_source=chatgpt.com)

Upstream overview: [https://github.com/RDFLib/pySHACL](https://github.com/RDFLib/pySHACL?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+2

## 2. Standards coverage and semantic model

### 2.1 Supported SHACL specifications

PySHACL implements several related but distinct parts of the SHACL ecosystem.

| Specification                      | Support in PySHACL 0.40.1                                                                   | Status of specification               |
| ---------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------- |
| SHACL Core                         | Broad implementation of the standard constraint components, paths, and targeting mechanisms | W3C Recommendation, 2017              |
| SHACL-SPARQL                       | SPARQL-based constraints and reusable constraint components                                 | Part of the 2017 SHACL Recommendation |
| SHACL Advanced Features (SHACL-AF) | Custom targets, functions, expressions, rules, and annotations                              | W3C Working Group Note, 2017          |
| SHACL-JS                           | JavaScript validators, functions, targets, and rules                                        | W3C Working Group Note, 2017          |
| RDFS / OWL 2 RL                    | Optional pre-inference through OWL-RL                                                       | Separate RDF/OWL standards            |

These are not interchangeable validation modes. SHACL Core supplies the foundational constraints; SHACL-SPARQL expands the kinds of checks that can be expressed; SHACL-AF adds additional computation and graph generation; and SHACL-JS supplies a JavaScript implementation mechanism for extensions.

The `advanced=True` option enables SHACL-AF processing. JavaScript functionality additionally requires the appropriate optional dependency and `js=True`.

A consequential version distinction is that SHACL 1.2 is under active W3C development in October 2026. The latest 1.2 Core publications are Working Drafts, while PySHACL 0.40.1 identifies the 2017 recommendation and associated extension specifications as its implementation targets. Overlap with SHACL 1.2 features does not establish full SHACL 1.2 conformance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+4



Specifications:

SHACL Core and SPARQL: [https://www.w3.org/TR/shacl/](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com)

SHACL Advanced Features: [https://www.w3.org/TR/shacl-af/](https://www.w3.org/TR/shacl-af/?utm_source=chatgpt.com)

SHACL-JS: [https://www.w3.org/TR/shacl-js/](https://www.w3.org/TR/shacl-js/?utm_source=chatgpt.com)

SHACL 1.2 Core Working Draft: [https://www.w3.org/TR/shacl12-core/](https://www.w3.org/TR/shacl12-core/?utm_source=chatgpt.com)

### 2.2 Shape evaluation: the fundamental execution model

The fundamental unit of validation is a focus node evaluated against a shape.

A shape may be a `sh:NodeShape`, which applies constraints to the focus node itself, or a `sh:PropertyShape`, which uses `sh:path` to obtain values from the data graph and evaluates constraints over those values.

Shapes can identify their focus nodes through standard targeting declarations:

| Target                  | Meaning                                                                     |
| ----------------------- | --------------------------------------------------------------------------- |
| `sh:targetNode`         | Explicitly named individual RDF nodes                                       |
| `sh:targetClass`        | Instances of specified RDF classes, including applicable subclass semantics |
| `sh:targetSubjectsOf`   | Subjects having a specified predicate                                       |
| `sh:targetObjectsOf`    | Objects of triples using a specified predicate                              |
| SHACL-AF custom targets | Nodes returned by extension-defined targeting logic                         |

This creates a declarative discovery mechanism. A validator does not necessarily need application code to enumerate which objects should be checked.

It also means that a shape without applicable targets may never be evaluated in an ordinary whole-graph validation. The existence of constraints in a shapes graph does not, by itself, imply that every node is subject to those constraints.

### 2.3 SHACL validation is not conventional ontology reasoning

SHACL validation and OWL reasoning solve different problems.

OWL and RDFS describe semantic entailments: what additional statements follow from the available knowledge and vocabulary.

SHACL evaluates whether a graph satisfies explicitly stated conditions. These conditions can require values that are absent, prohibit additional properties, or enforce bounds on the number of related nodes.

For example, a SHACL property shape with `sh:minCount 1` can report a missing property even though, under open-world OWL semantics, the missing relationship might merely be unknown rather than false.

This distinction enables complementary use:

- Reasoning can establish implicit class memberships, relationships, and other facts.
- SHACL can validate structural and semantic requirements against the resulting graph.

Conformance is relative to the selected shapes, targets, graph contents, and reasoning configuration. It is not proof that the RDF graph is complete, globally consistent under OWL semantics, or correct against business requirements that have not been expressed as shapes.

## 3. SHACL Core: structural and relational validation

PySHACL supports the principal families of Core constraint components documented by its feature matrix. Their importance extends beyond RDF-specific schema checking: many express cross-entity, recursive, conditional, or relational invariants without application-specific validation functions.

### 3.1 Core constraint families

| Family                 | Key constructs                                                                                              | Capability                                                               |
| ---------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Value types            | `sh:class`, `sh:datatype`, `sh:nodeKind`                                                                    | Enforce class membership, literal datatype, and RDF node category        |
| Cardinality            | `sh:minCount`, `sh:maxCount`                                                                                | Enforce minimum and maximum numbers of distinct property values          |
| Ordered ranges         | `sh:minInclusive`, `sh:minExclusive`, `sh:maxInclusive`, `sh:maxExclusive`                                  | Numeric and otherwise comparable literal bounds                          |
| String constraints     | `sh:minLength`, `sh:maxLength`, `sh:pattern`, `sh:flags`                                                    | String length and regular-expression requirements                        |
| Language constraints   | `sh:languageIn`, `sh:uniqueLang`                                                                            | Restrict language tags and detect duplicated language tags               |
| Property comparisons   | `sh:equals`, `sh:disjoint`, `sh:lessThan`, `sh:lessThanOrEquals`                                            | Compare values reached through different properties                      |
| Logical composition    | `sh:and`, `sh:or`, `sh:not`, `sh:xone`                                                                      | Compose reusable constraints into complex logical conditions             |
| Shape composition      | `sh:node`, `sh:property`                                                                                    | Validate related nodes and property values against other shapes          |
| Qualified cardinality  | `sh:qualifiedValueShape`, `sh:qualifiedMinCount`, `sh:qualifiedMaxCount`, `sh:qualifiedValueShapesDisjoint` | Count only values satisfying another shape                               |
| Closure and membership | `sh:closed`, `sh:ignoredProperties`, `sh:hasValue`, `sh:in`                                                 | Restrict allowed properties, require known values, or limit allowed sets |

Upstream feature matrix: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md](https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md?utm_source=chatgpt.com)

W3C constraint definitions: [https://www.w3.org/TR/shacl/#core-components](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com#core-components)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1

### 3.2 Recursive validation and reusable shapes

`sh:node` and `sh:property` allow a shape to reference other shapes. A graph can therefore be validated through a network of reusable structural definitions rather than flat property specifications.

For example, an entity shape might require a relationship to a second entity, whose own shape requires additional relationships or typed values. `sh:node` recursively validates the related node.

Logical operators extend this composition:

`sh:and` requires all referenced shapes to conform, `sh:or` requires at least one, `sh:not` negates a shape, and `sh:xone` requires exactly one to conform.

These are particularly useful for heterogeneous graph models, polymorphic entities, alternative relationship structures, and constraints where the validity of one node depends on the properties of another.

Deeply nested or recursive shapes can also create substantial validation work. PySHACL provides `max_validation_depth` to guard against excessive shape traversal; the engine's default is 15. This is a practical execution limit, not an RDF schema depth limit.

### 3.3 Qualified cardinality: counting by semantic type or structure

Ordinary `sh:minCount` and `sh:maxCount` count values reached through a property.

Qualified cardinality counts only values conforming to another shape. This is a significantly more expressive mechanism.

A constraint can require, for example, at least two related objects satisfying a particular structural condition, regardless of how many other relationships exist.

`sh:qualifiedValueShapesDisjoint` additionally affects how qualifying values are counted relative to sibling qualified shapes.

This can replace custom code involving traversal, classification, filtering, and counting, while keeping the invariant directly in the graph's schema.

### 3.4 Cross-property consistency

Property-pair constraints are among the more valuable Core features for relational data.

`sh:equals` checks equality of property value sets, while `sh:disjoint` prohibits overlapping values. `sh:lessThan` and `sh:lessThanOrEquals` compare values across properties.

These provide native mechanisms for expressing relationships between values rather than checking every property in isolation.

They are appropriate when a validation requirement concerns consistency among different facts associated with the same focus node.

## 4. SHACL property paths: validation over graph topology

SHACL property paths let constraints operate over relationships reached through graph traversal expressions rather than only immediate predicates.

PySHACL's feature matrix covers the principal SHACL property-path forms:

| Path type    | Construct            | Operation                                         |
| ------------ | -------------------- | ------------------------------------------------- |
| Predicate    | RDF predicate IRI    | Follow a single outgoing property                 |
| Sequence     | RDF list of paths    | Follow multiple relationship steps in order       |
| Alternative  | `sh:alternativePath` | Follow any of several paths                       |
| Inverse      | `sh:inversePath`     | Traverse a relationship backward                  |
| Zero or more | `sh:zeroOrMorePath`  | Transitive traversal, including the starting node |
| One or more  | `sh:oneOrMorePath`   | Transitive traversal requiring at least one step  |
| Zero or one  | `sh:zeroOrOnePath`   | Optional traversal of a path                      |

Paths can be nested to express more complex graph navigation.

For example, an inverse path can examine the entities that reference a focus node. A sequence path can validate values several relationships away. A repeated path can examine an entire reachable subgraph.

This is an important alternative to constructing bespoke Python traversals over RDFLib triples.

However, expressive paths introduce performance and semantic considerations. Repeated traversal through highly connected graphs can substantially expand the set of candidate values, and path traversal is evaluated according to RDF graph connectivity, not conventional hierarchical ownership.

Property paths also operate on sets of RDF nodes. RDF does not intrinsically preserve an ordering among the values of an ordinary multivalued property.

The ability to reuse graph traversal definitions across Core constraints, SPARQL translation, node expressions, and rule execution is one of PySHACL's more useful architectural features.

Sources:

SHACL property paths: [https://www.w3.org/TR/shacl/#property-paths](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com#property-paths)

PySHACL feature matrix: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md](https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md?utm_source=chatgpt.com)

## 5. SPARQL-powered constraints and extensibility

SHACL-SPARQL is one of PySHACL's most consequential capabilities because it allows requirements that cannot be conveniently expressed using Core constraint components to remain within the declarative shapes framework.

### 5.1 SPARQL-based validation

A shape can include a `sh:sparql` constraint containing a SPARQL SELECT query.

The query identifies combinations of nodes and values that constitute violations. SHACL-defined variable bindings, including the focus node, allow the query to operate in the context of each applicable shape evaluation.

SPARQL constraints can express requirements such as relationships spanning several hops, aggregate conditions, cross-entity consistency, exclusions, and conditions involving complex graph patterns.

This is a natural extension point when Core constraints become unwieldy but the condition is fundamentally relational.

### 5.2 Reusable custom constraint components

PySHACL also implements the SHACL-SPARQL mechanism for defining custom constraint components through RDF descriptions.

A custom component can be described using `sh:ConstraintComponent`, parameter declarations, and validators such as `sh:SPARQLSelectValidator` and `sh:SPARQLAskValidator`.

These differ from a one-off `sh:sparql` constraint. The reusable component defines a parameterized constraint vocabulary that multiple shapes can reference.

This enables domain-specific validation abstractions while preserving SHACL's core execution and reporting model. Rather than repeatedly embedding variations of a query, a shapes graph can expose one logical constraint with explicit parameters.

The extension is still implemented through the supported SHACL language mechanism. It is not equivalent to registering an arbitrary Python callback as a stable PySHACL public API.

### 5.3 Query execution and portability

SPARQL evaluation is provided by the underlying RDF/SPARQL engine. With RDFLib-backed data, that means RDFLib's SPARQL implementation; with Oxigraph-backed data in 0.40.1, compatible SPARQL operations can execute through Oxigraph.

Consequently, the performance and exact support of advanced query constructs can depend on the backing engine.

The W3C SHACL-SPARQL rules also impose restrictions on query structure and pre-bound variables. A syntactically valid standalone SPARQL query is not necessarily a valid SHACL-SPARQL constraint.

PySHACL's own feature matrix documents that pre-binding the special `$shapesGraph` variable is not supported. This is an explicit compatibility gap to consider for shapes relying on that part of the specification.

Sources:

SHACL-SPARQL: [https://www.w3.org/TR/shacl/#sparql-constraints](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com#sparql-constraints)

Reusable constraint components: [https://www.w3.org/TR/shacl/#sparql-constraint-components](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com#sparql-constraint-components)

PySHACL compatibility matrix: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md](https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1

## 6. SHACL Advanced Features: declarative graph programming

SHACL Advanced Features (SHACL-AF) substantially changes what a shapes graph can express. Rather than merely selecting nodes and checking constraints, it introduces mechanisms for computing values, defining functions, discovering targets dynamically, and creating new RDF statements.

PySHACL enables these mechanisms through `advanced=True`.

### 6.1 Custom targets

Standard SHACL targets identify nodes through explicit IRIs, classes, and predicate relationships. SHACL-AF custom targets support more expressive node selection.

PySHACL implements:

- `sh:target` — attaches a custom target to a shape.
- `sh:SPARQLTarget` — obtains focus nodes through a SPARQL query.
- `sh:SPARQLTargetType` — defines a reusable, parameterized target mechanism.

The distinction between a `SPARQLTarget` and a `SPARQLTargetType` is significant. The former defines a particular selection expression; the latter provides a reusable target abstraction with parameters supplied by individual shapes.

For example, a target may select only nodes associated with a particular class of event, satisfying a relationship pattern, or participating in a graph structure. The same declarative target logic can then be shared by multiple constraints.

Architectural implication: target discovery becomes part of the schema rather than something that must always be implemented by application-level graph queries.

This can simplify validation orchestration, although a complex SPARQL target may be more expensive than a standard `sh:targetClass` or `sh:targetSubjectsOf` declaration.

### 6.2 SHACL functions

PySHACL supports `sh:SHACLFunction` and SPARQL-backed functions through `sh:SPARQLFunction`.

These make reusable computations available to SHACL-aware expressions and SPARQL queries. A function can accept declared parameters, evaluate a graph-dependent expression, and return an RDF term or compatible result.

Functions provide a different abstraction from constraint components:

| Mechanism            | Primary result                                  |
| -------------------- | ----------------------------------------------- |
| Constraint component | Whether a specified condition is satisfied      |
| Custom target        | Which RDF nodes should be evaluated             |
| SHACL function       | A computed value that other expressions can use |
| SHACL rule           | Additional statements to add to a graph         |

A function can therefore act as shared computational machinery supporting multiple validators or rule definitions.

One particularly important improvement in PySHACL 0.40.0 was support for registering and executing SHACL functions, including SHACL-JS functions, on both RDFLib and Oxigraph SPARQL engines. This preserves an important extension mechanism when changing the underlying data-store implementation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

Oxigraph support · RDFLib/pySHACL · GitHub

+1



### 6.3 Node expressions

SHACL-AF node expressions evaluate RDF-term collections through a composable declarative language.

PySHACL's feature matrix identifies support for:

| Expression          | Purpose                                                |
| ------------------- | ------------------------------------------------------ |
| `sh:this`           | Reference the current focus node                       |
| Constant term       | Supply an RDF term directly                            |
| `sh:path`           | Evaluate values reached through a SHACL property path  |
| `sh:filterShape`    | Retain values conforming to another shape              |
| `sh:union`          | Combine expression results                             |
| `sh:intersection`   | Select values common to expressions                    |
| SHACL function call | Evaluate a reusable function with expression arguments |

These mechanisms are useful in SHACL Triple Rules and expression-based validation because they allow graph traversal, filtering, combination, and computation without writing the entire operation as SPARQL.

`sh:ExpressionConstraintComponent` allows expressions to participate directly in validation.

An important qualification: the upstream 0.40.1 feature matrix still marks `sh:filterShape`, `sh:union`, and `sh:intersection` as not tested. The 0.40.1 release specifically fixes an intersection-expression defect, demonstrating that these less-common constructs warrant closer review of tests and behavior when their precise semantics matter.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



### 6.4 Validation-result annotations

SHACL-AF also includes annotation mechanisms:

`sh:annotationProperty`, `sh:annotationVarName`, and `sh:annotationValue`.

Annotations can add contextual RDF statements to validation results. Their value is that validation reports can carry domain-specific explanatory information while remaining RDF graphs.

For example, a custom validation framework could associate a result with an additional classification, reference, or derived context where the annotation mechanism permits it.

This is distinct from merely setting `sh:message` or `sh:severity`. Annotations extend the structured report itself.

Primary specifications:

Custom targets: [https://www.w3.org/TR/shacl-af/#custom-targets](https://www.w3.org/TR/shacl-af/?utm_source=chatgpt.com#custom-targets)

Functions: [https://www.w3.org/TR/shacl-af/#functions](https://www.w3.org/TR/shacl-af/?utm_source=chatgpt.com#functions)

Node expressions: [https://www.w3.org/TR/shacl-af/#node-expressions](https://www.w3.org/TR/shacl-af/?utm_source=chatgpt.com#node-expressions)

Annotations: [https://www.w3.org/TR/shacl-af/#annotations](https://www.w3.org/TR/shacl-af/?utm_source=chatgpt.com#annotations)

## 7. SHACL rules: graph expansion and declarative transformations

Rules are among PySHACL's most significant capabilities beyond validation.

PySHACL implements SHACL-AF rules that derive new triples from existing graph facts. Rules are attached to shapes through `sh:rule`, and their execution is associated with the focus nodes selected by those shapes.

### 7.1 Two primary rule families

Triple Rules (`sh:TripleRule`)

Triple Rules describe generated subject, predicate, and object terms, typically through the corresponding `sh:subject`, `sh:predicate`, and `sh:object` expressions.

They are appropriate when the desired transformation is naturally expressed as relationships generated from node expressions.

A Triple Rule might derive a reciprocal relationship, calculated classification, or normalized link from existing RDF properties.

SPARQL Rules (`sh:SPARQLRule`)

SPARQL Rules use SPARQL `CONSTRUCT` queries to derive triples.

They are better suited to graph transformations involving complex joins, graph patterns, computed values, or other operations naturally represented in SPARQL.

Both mechanisms operate inside the SHACL-AF rules framework, with standard concepts such as rule conditions, applicability, and ordering.

### 7.2 Rule conditions, ordering, and activation

The implemented rule system includes:

- `sh:condition`, controlling when a rule applies.
- `sh:order`, controlling evaluation order.
- `sh:deactivated`, disabling execution of a rule.

Rules are associated with shapes, so focus-node targeting and shape selection participate in deciding what work is performed.

PySHACL's tagged implementation sorts shapes and rules by their respective orders and executes applicable rules against the graph.

This supports explicit dependencies among derivations, but ordering should be treated as meaningful program semantics rather than merely a cosmetic property.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com

+1



### 7.3 Iterative rule execution

With `iterate_rules=True`, PySHACL repeats rule application while additional changes are being made to the graph, subject to implementation limits.

This permits cascading derivations: triples generated by one pass can make further derivations possible.

The implementation has a 100-iteration guard for its rule-application loops. Exceeding that limit raises a runtime error rather than continuing indefinitely.

A subtle architectural distinction is important here. The tagged `apply_rules()` implementation iterates rules within each ordered shape's rule group. It does not establish that every combination of ordered shapes will be repeatedly executed as one globally order-independent fixed-point computation.

When derivation dependencies are complex, the difference between an ordered pass, per-shape iteration, and a global least fixed point can materially affect the result.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 7.4 Validation with rules versus explicit rule expansion

PySHACL exposes two related execution paths:

| API                            | Purpose                                                          | Primary output                            |
| ------------------------------ | ---------------------------------------------------------------- | ----------------------------------------- |
| `validate(..., advanced=True)` | Apply enabled advanced features and validate the resulting graph | Conformance verdict and validation report |
| `shacl_rules(...)`             | Execute rule expansion as the main operation                     | Expanded graph or serialized graph        |

In advanced validation mode, the implementation registers SHACL functions and applies applicable rules before evaluating the selected validation shapes.

This means validation can observe rule-generated triples rather than only the original input data. It is a substantive difference from treating rule processing as a separate after-validation stage.

The dedicated `shacl_rules()` entry point provides graph expansion without requiring validation to be the primary objective. Its result contains the original graph data together with rule-generated statements.

Illustrative Python usage:

```
from pyshacl import validate, shacl_rules# Validate after SHACL-AF processing.conforms, report_graph, report_text = validate(    data_graph,    shacl_graph=shapes_graph,    advanced=True,    iterate_rules=True,)# Separately obtain rule-expanded RDF data.expanded_graph = shacl_rules(    data_graph,    shacl_graph=shapes_graph,    iterate_rules=True,)
```

These examples are illustrative, not executed here.

By default, PySHACL manages graph copying when operations would otherwise mutate a caller-supplied graph. With `inplace=True`, inference and rule expansion can instead modify the supplied graph directly.

The rules expander also supports output serialization through `serialize_expanded_graph` and related format options.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com

+2



### 7.5 Rules are not general-purpose procedural transformations

SHACL Rules are particularly effective for additive derivations. They are not a complete replacement for arbitrary graph-editing or transactional transformation machinery.

Important distinctions include the following.

First, rule expansion adds derived statements. It is not a general update language for deleting obsolete triples, handling conflicting writes, or enforcing transactional invariants.

Second, repeated additions can expand the graph substantially, especially when expressions or queries generate many relationships.

Third, deriving additional facts does not prove their underlying premises are correct. Rule expansion and SHACL validation remain complementary operations.

Finally, when facts are derived into a long-lived graph, their validity following later changes to source statements becomes a separate maintenance problem. PySHACL's rule engine should not be confused with a fully incremental truth-maintenance system.

Rules specification: [https://www.w3.org/TR/shacl-af/#rules](https://www.w3.org/TR/shacl-af/?utm_source=chatgpt.com#rules)

Tagged rule scheduler: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/rules/\_\_init\_\_.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/rules/__init__.py?utm_source=chatgpt.com)

Rules expansion implementation: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/rule_expand_runner.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/rule_expand_runner.py?utm_source=chatgpt.com)

## 8. Semantic inference, ontologies, and graph enrichment

PySHACL integrates RDFS and OWL-RL pre-inference through the separate Python `owlrl` package.

### 8.1 Inference modes

The `inference` option supports:

| Mode            | Meaning                                     |
| --------------- | ------------------------------------------- |
| `none` / `None` | Do not request pre-inference                |
| `rdfs`          | Apply RDFS inference                        |
| `owlrl`         | Apply OWL 2 RL inference                    |
| `both`          | Combine supported RDFS and OWL-RL inference |

Pre-inference computes entailments that may create additional RDF statements relevant to shape evaluation.

For example, an ontology could state that one class is a subclass of another, allowing inferred type information to affect which class constraints or targets apply.

OWL-RL is a rule-oriented OWL profile. This is not equivalent to complete OWL 2 DL reasoning, arbitrary description-logic satisfiability checking, or an unconstrained theorem prover.

### 8.2 Ontology inoculation

The `ont_graph` parameter provides extra ontology information to be incorporated into the validation data context.

This is distinct from the shapes graph:

- The ontology graph supplies semantic definitions and facts relevant to reasoning.
- The shapes graph supplies validation constraints and possibly advanced functions or rules.
- The data graph supplies the entities and relationships being evaluated.

The upstream implementation calls this process inoculation. It incorporates relevant ontology information before pre-inference and validation.

A useful consequence is that ontology definitions do not need to be embedded permanently into the original data graph for them to influence validation.

The same separation can also prevent unnecessary coupling between domain vocabulary management and data-validation definitions.

### 8.3 Importing linked ontologies and shapes

`do_owl_imports=True` enables loading graphs referenced through `owl:imports` when processing shapes and ontology sources.

It does not automatically follow `owl:imports` from the data graph.

This restriction matters: a graph containing import declarations is not necessarily validated with everything that those declarations might appear to reference. Imports need to be explicitly enabled in the relevant loading context.

Network fetching also introduces availability, reproducibility, and trust concerns. For deterministic validation, referenced ontology and shapes versions need to be controlled independently of PySHACL itself.

### 8.4 Meta-SHACL: validating the shapes graph

`meta_shacl=True` checks the shapes graph against the bundled SHACL-SHACL definitions before proceeding with data validation.

This detects structural and formal problems in the validation schema itself.

It addresses a different question from ordinary validation:

| Operation                 | Question                                                                        |
| ------------------------- | ------------------------------------------------------------------------------- |
| Meta-SHACL                | Does the shapes graph conform to the SHACL vocabulary's prescribed constraints? |
| Ordinary SHACL validation | Does the data graph conform to the application-defined shapes?                  |
| Pre-inference             | What additional facts follow under the configured entailment regime?            |

A shapes graph may pass Meta-SHACL and still encode the wrong domain requirements. Meta-SHACL checks formal validity, not the intended business meaning of every constraint.

### 8.5 Interaction and execution order

For an ordinary local advanced-validation run, the high-level flow is:

Load data, shapes, and optional ontology

Optional Meta-SHACL check of shapes

Ontology inoculation and optional RDFS / OWL-RL expansion

Register advanced functions and apply applicable SHACL rules

Evaluate constraints over the resulting graph

Return conformance and SHACL validation report

Not every operation runs in every invocation. The inference and advanced-rule stages are explicitly configurable, and several combinations are unavailable in remote SPARQL mode.

The larger design opportunity is to use ontology semantics for general knowledge, rules for domain-specific derivations, and SHACL constraints for enforceable graph invariants, while maintaining clear distinctions among those responsibilities.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com

+2



Sources:

OWL-RL implementation: [https://github.com/RDFLib/OWL-RL](https://github.com/RDFLib/OWL-RL?utm_source=chatgpt.com)

OWL-RL documentation: [https://owl-rl.readthedocs.io/en/latest/](https://owl-rl.readthedocs.io/en/latest/?utm_source=chatgpt.com)

Validation implementation: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/validator.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/validator.py?utm_source=chatgpt.com)

## 9. SHACL-JS: JavaScript-based extension mechanisms

PySHACL offers optional implementation of the SHACL-JS specification, allowing shapes to execute JavaScript logic.

The feature is not installed by default. It requires the `js` extra, which brings in `pyduktape2`, and JavaScript execution must be enabled in the validation configuration.

```
pip install "pyshacl[js]"
```

### 9.1 Supported extension families

PySHACL's feature matrix identifies the following JavaScript functionality:

| Extension             | Constructs                       | Purpose                                                               |
| --------------------- | -------------------------------- | --------------------------------------------------------------------- |
| Direct JS constraints | `sh:js`                          | Execute JavaScript-based validation conditions                        |
| Reusable validators   | `sh:JSValidator`                 | Define reusable custom validation components                          |
| JS functions          | `sh:JSFunction`                  | Expose computations to SHACL expressions and other supported contexts |
| JS rules              | `sh:JSRule`                      | Generate RDF statements through JavaScript                            |
| JS targets            | `sh:JSTarget`, `sh:JSTargetType` | Discover focus nodes dynamically                                      |

SHACL-JS also defines library-loading mechanisms, including `sh:jsLibrary`, for organizing reusable code.

This provides a mechanism for expressing computations that are difficult or impractical to formulate in Core SHACL or SPARQL alone.

The advantage is not simply that JavaScript is a general-purpose language. SHACL-JS allows custom computation to remain associated with RDF-defined shapes, functions, targets, and rules, rather than requiring application code to manage every invocation separately.

### 9.2 Extensibility and interoperability

There are several important distinctions.

SHACL-JS is an optional extension, not a prerequisite for advanced SHACL. SPARQL functions, custom targets, and Triple/SPARQL Rules can be used without it.

JavaScript capabilities are not equivalent to standard SHACL Core portability. An external validator may implement Core and SHACL-SPARQL while lacking the same JavaScript runtime or SHACL-JS support.

The JavaScript execution runtime belongs to a companion dependency. PySHACL integrates `pyduktape2`; it is not supplying a standalone JavaScript engine of its own.

JavaScript execution expands the trust boundary. Because shapes can reference executable code and external resources, untrusted SHACL-JS definitions require appropriate isolation, resource controls, and review. Installing a JavaScript engine should not be interpreted as establishing a comprehensive security sandbox.

The PySHACL remote SPARQL execution mode explicitly disables SHACL-JS.

SHACL-JS specification: [https://www.w3.org/TR/shacl-js/](https://www.w3.org/TR/shacl-js/?utm_source=chatgpt.com)

PySHACL feature matrix: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md](https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md?utm_source=chatgpt.com)

Dependency declarations: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyproject.toml](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyproject.toml?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+2

## 10. RDF data integration and execution backends

PySHACL 0.40.1 has three meaningfully different integration models: in-process RDFLib graphs, in-process Oxigraph stores, and remote SPARQL endpoints.

These should not be treated as equivalent execution options.

### 10.1 RDFLib integration

RDFLib is PySHACL's foundational RDF ecosystem dependency.

PySHACL supports ordinary `rdflib.Graph` objects and, for multigraph use, `rdflib.Dataset`.

Through RDFLib, applications can supply parsed RDF graphs or ask PySHACL to load RDF from file paths, web URLs, byte buffers, and compatible streams.

Common RDF serializations include Turtle, RDF/XML, JSON-LD, N-Triples, and TriG or N-Quads for dataset-oriented operations, subject to the underlying parser and the relevant input path.

The validator accepts format hints such as `data_graph_format`, `shacl_graph_format`, and `ont_graph_format`, avoiding reliance on automatic detection when that is ambiguous.

The important integration benefit is that RDF parsing, RDF term modeling, graph traversal, SPARQL evaluation, namespaces, and serialization do not need to be reimplemented inside the validation layer.

RDFLib documentation: [https://rdflib.readthedocs.io/en/stable/](https://rdflib.readthedocs.io/en/stable/?utm_source=chatgpt.com)

### 10.2 Native PyOxigraph support — new in 0.40.0

Version 0.40.0 introduced compatibility with `pyoxigraph.Store`, retained in 0.40.1.

```
pip install "pyshacl[oxigraph]"
```

A PyOxigraph store can be passed directly to `validate()` or `shacl_rules()`.

```
from pyoxigraph import Storefrom pyshacl import validatestore = Store()  # Assume RDF data has been loaded.conforms, report_graph, report_text = validate(    store,    shacl_graph="shapes.ttl",)
```

The example is illustrative.

This support is implemented through PySHACL's `DataGraph` abstraction, which adapts supported RDFLib graphs/datasets and Oxigraph stores to a common internal interface.

The result is a particularly valuable architectural separation:

| Layer                | Responsibility                                             |
| -------------------- | ---------------------------------------------------------- |
| PySHACL              | SHACL targeting, validation, functions, rules, and reports |
| `DataGraph` adapter  | Common graph operations across backend implementations     |
| RDFLib or PyOxigraph | RDF storage, query execution, and associated data access   |
| OWL-RL               | Optional semantic pre-inference                            |

PyOxigraph is built around Oxigraph's Rust-based RDF and SPARQL engine. Its Python `Store` API supports in-memory and disk-backed use.

The potential benefit of switching backends is especially relevant to SPARQL-heavy validation and rule expansion, where data access and query execution represent substantial work.

However, PySHACL does not become an entirely Rust-native SHACL validator when using Oxigraph. Shape evaluation, orchestration, and numerous constraint implementations still belong to PySHACL. Performance improvements depend on the workload, query characteristics, graph organization, and conversion overhead.

The upstream 0.40.0 release describes faster SPARQL execution as a reason for the integration, but does not establish a universal end-to-end validation speedup.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

Oxigraph support · RDFLib/pySHACL · GitHub

+1



Sources:

PySHACL Oxigraph release: [https://github.com/RDFLib/pySHACL/releases/tag/v0.40.0](https://github.com/RDFLib/pySHACL/releases/tag/v0.40.0?utm_source=chatgpt.com)

PyOxigraph store API: [https://pyoxigraph.readthedocs.io/en/stable/store.html](https://pyoxigraph.readthedocs.io/en/stable/store.html?utm_source=chatgpt.com)

PySHACL graph abstraction: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/graph_abstraction.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/graph_abstraction.py?utm_source=chatgpt.com)

### 10.3 Dataset support and named-graph semantics

An RDF dataset contains multiple named graphs. This provides a way to retain information about where triples belong without treating all triples as one physically undifferentiated graph.

PySHACL's dataset execution behavior is especially important:

Validation operates on the default union of the dataset's graphs.

That means facts from different named graphs can jointly satisfy a shape. Merely placing triples in separate named graphs does not make them isolated validation domains.

Since version 0.29.0, dataset-based inference and rules can preserve derivation provenance by placing generated triples into separate named graphs. The implementation uses named contexts for operations including ontology inoculation and pre-inference.

This enables a useful distinction between original and derived statements while still allowing validation over their combined logical contents.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



The consequence is that provenance separation and validation isolation are different properties.

For genuinely independent validation scopes, separate validation runs may be necessary. For integrated reasoning across related named graphs, union semantics may instead be the desired behavior.

### 10.4 Multiple data-graph inputs

PySHACL 0.31.0 introduced multi-input validation.

Two modes are available:

| Mode            | Behavior                                                                 | Return structure                                 |
| --------------- | ------------------------------------------------------------------------ | ------------------------------------------------ |
| `combine`       | Load input sources into one RDF dataset and validate their combined data | Standard validation tuple                        |
| `validate_each` | Validate every input independently                                       | Dictionary of input indexes to validation tuples |

`combine` is the default when passing multiple data sources.

Illustrative usage:

```
from pyshacl import validate, validate_eachsources = ["graph-a.ttl", "graph-b.ttl"]# Combined logical graph.combined = validate(    sources,    shacl_graph="shapes.ttl",)# Separate validation results.individual = validate_each(    sources,    shacl_graph="shapes.ttl",)
```

The same per-input mode is also accessible through:

```
validate(    sources,    shacl_graph="shapes.ttl",    multi_data_graphs_mode="validate_each",)
```

In 0.40.1, `validate_each()` returns a dictionary keyed by zero-based integer input index. This was changed in 0.40.0 from earlier source-identifier-based keys.

The distinction is valuable for batch graph processing because it determines whether the validation scope is a combined data model or individual source documents.

Combining documents can expose cross-document inconsistencies, but it can also hide missing facts when one document supplies a value absent from another. Independent validation preserves those boundaries.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+3



### 10.5 Remote SPARQL Graph Mode

PySHACL can validate RDF data stored behind a remote SPARQL endpoint without downloading the entire dataset as a local input file.

The Python interface uses `sparql_mode=True`; the CLI uses `-q` or `--sparql-mode`.

For an endpoint URL, PySHACL constructs an RDFLib `SPARQLStore`. The tagged implementation also reads these optional environment variables:

- `PYSHACL_SPARQL_USERNAME`
- `PYSHACL_SPARQL_PASSWORD`
- `PYSHACL_SPARQL_METHOD`

The default request method is `GET`, unless configured otherwise.

An explicit local shapes graph is required. Remote validation operates read-only.

| Capability                                            | Remote SPARQL mode |
| ----------------------------------------------------- | ------------------ |
| SHACL validation using supported remote graph queries | Available          |
| Local shapes graph                                    | Required           |
| Optional RDFS / OWL-RL pre-inference                  | Unavailable        |
| Extra ontology inoculation                            | Unavailable        |
| SHACL Rules expansion                                 | Unavailable        |
| SHACL-JS                                              | Unavailable        |
| Mutation of remote graph                              | Unavailable        |
| Multiple remote graph inputs in one multi-input run   | Unavailable        |

Advanced validation should therefore not be interpreted as enabling every SHACL-AF capability on a remote endpoint; the engine skips rule execution in this mode.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com

+3



Remote mode avoids moving all graph data into the process, but query count, network latency, endpoint concurrency, indexing, authentication, timeouts, and supported SPARQL behavior become major determinants of performance.

It also does not automatically acquire a transactionally consistent snapshot across the complete validation run. The meaning of a report over concurrently changing remote data depends on the endpoint's consistency guarantees.

Tagged entrypoint: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/entrypoints.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/entrypoints.py?utm_source=chatgpt.com)

RDFLib SPARQLStore: [https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.plugins.stores.sparqlstore/](https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.plugins.stores.sparqlstore/?utm_source=chatgpt.com)

## 11. Python API, execution controls, and diagnostics

### 11.1 Main public entry points

PySHACL's public execution surface centers on three functions.

| Entry point       | Purpose                                     |
| ----------------- | ------------------------------------------- |
| `validate()`      | Validate a graph or combined data sources   |
| `validate_each()` | Validate a sequence of graphs independently |
| `shacl_rules()`   | Perform SHACL rule expansion                |

The most important `validate()` options are:

| Option                           | Effect                                                                    |
| -------------------------------- | ------------------------------------------------------------------------- |
| `shacl_graph`                    | Supply a separate shapes graph; if omitted, derive shapes from input data |
| `ont_graph`                      | Supply additional ontology information                                    |
| `inference`                      | Select semantic pre-inference                                             |
| `advanced`                       | Enable SHACL-AF processing                                                |
| `js`                             | Enable installed SHACL-JS support                                         |
| `iterate_rules`                  | Enable iterative rule execution                                           |
| `meta_shacl`                     | Check shapes graph validity                                               |
| `inplace`                        | Permit modification of the supplied data graph                            |
| `abort_on_first`                 | Stop after the first failing shape evaluation                             |
| `allow_infos` / `allow_warnings` | Change severity handling for the overall verdict                          |
| `focus_nodes`                    | Restrict initial focus-node selection                                     |
| `use_shapes`                     | Restrict shape selection                                                  |
| `max_validation_depth`           | Bound recursive shape evaluation                                          |
| `sparql_mode`                    | Use remote SPARQL read-only validation                                    |
| `serialize_report_graph`         | Return serialized RDF report bytes                                        |
| `debug`                          | Enable detailed logging                                                   |
| `check_dash_result`              | Compare against a DASH expected validation result                         |

The former `abort_on_error` keyword is deprecated in favor of `abort_on_first`.

### 11.2 Focus-node filtering and shape selection

These capabilities deserve particular emphasis because they support precisely scoped validation.

`focus_nodes` alone: restricts validation to the specified IRIs among the focus nodes targeted by shapes.

`use_shapes` alone: evaluates only the explicitly selected NodeShapes or PropertyShapes, rather than the full shapes graph's set of selected top-level shapes.

Both together: passes the supplied focus nodes directly to the selected shapes, without requiring those shapes to declare their own targeting mechanism.

This last combination is especially powerful for testing or validating a known collection of entities against a particular constraint set.

For example:

```
from pyshacl import validateconforms, report, text = validate(    "data.ttl",    shacl_graph="shapes.ttl",    focus_nodes=[        "https://example.org/entity/42",    ],    use_shapes=[        "https://example.org/schema/EntityShape",    ],)
```

The API accepts absolute IRIs and supports CURIE expansion through available namespace bindings.

This is targeted execution, not automatically complete incremental validation. The implementation restricts selected starting shapes and focus nodes; it does not maintain a dependency index proving that all entities affected by a graph mutation have been revalidated.

A nested shape, graph path, rule, or SPARQL constraint can still depend on data beyond the selected focus-node set. Correctness of change-scoped validation therefore depends on how affected nodes are identified.

Release notes: [https://github.com/RDFLib/pySHACL/releases/tag/v0.27.0](https://github.com/RDFLib/pySHACL/releases/tag/v0.27.0?utm_source=chatgpt.com)

Tagged selection implementation: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/validator.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/validator.py?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1

### 11.3 Standards-based validation reports

The ordinary return value of `validate()` is:

```
conforms, results_graph, results_text = validate(...)
```

`results_graph` is normally an RDFLib graph containing a SHACL validation report.

Its RDF representation uses standard SHACL vocabulary terms such as:

| RDF term                       | Information                                                |
| ------------------------------ | ---------------------------------------------------------- |
| `sh:ValidationReport`          | Identifies the report                                      |
| `sh:conforms`                  | Boolean verdict                                            |
| `sh:result`                    | Links to individual validation results                     |
| `sh:focusNode`                 | RDF node to which the result applies                       |
| `sh:resultPath`                | Property path associated with the result, where applicable |
| `sh:value`                     | Relevant offending or evaluated value, where applicable    |
| `sh:sourceShape`               | Shape responsible for the result                           |
| `sh:sourceConstraintComponent` | Constraint component producing the result                  |
| `sh:resultSeverity`            | Severity of the result                                     |
| `sh:resultMessage`             | Human-readable explanatory message                         |
| `sh:detail`                    | Additional nested result information where applicable      |

The report is itself an RDF graph. Consequently, results can be queried using SPARQL, stored in an RDF database, serialized, enriched, and correlated with source RDF entities without inventing a separate validation-result schema.

The text report is useful for humans and logging, but the RDF report is the more powerful interchange and analysis interface.

The SHACL vocabulary also provides non-validating shape metadata such as `sh:name`, `sh:description`, `sh:group`, and `sh:order`. These can support tooling that presents shape definitions alongside validation results, although PySHACL itself is not a complete form or user-interface generator.

W3C validation reporting: [https://www.w3.org/TR/shacl/#validation-report](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com#validation-report)

### 11.4 Severity and conformance

SHACL reports can assign severities such as `sh:Violation`, `sh:Warning`, and `sh:Info`.

PySHACL exposes two options that affect whether lower-severity results cause the overall validation to be nonconformant.

`allow_infos=True` permits Info-level results without making the overall verdict false.

`allow_warnings=True` permits Warning and Info results.

These options do not mean that such issues cease to exist. They change the conformance decision while preserving the distinction between findings and overall acceptability.

This supports validation systems in which informational diagnostics, advisory warnings, and blocking violations must be handled differently.

### 11.5 Validation failures versus ordinary violations

One of PySHACL's most important API distinctions is between a nonconformant validation result and a validation failure.

Ordinary nonconformance means validation successfully ran and found data violating one or more constraints. The API returns a normal validation report.

A SHACL-defined `ValidationFailure` means the validator encountered a formal condition preventing normal validation completion. In that case, the second tuple member is a `ValidationFailure` instance instead of an RDF report graph.

Other errors, including `ShapeLoadError`, `ConstraintLoadError`, `RuleLoadError`, and `ReportableRuntimeError`, can be raised as Python exceptions.

An integration should not assume that every `conforms=False` result contains a queryable report graph.

For example:

```
from pyshacl import validatefrom pyshacl.errors import ValidationFailureconforms, report, text = validate(    "data.ttl",    shacl_graph="shapes.ttl",)if isinstance(report, ValidationFailure):    raise RuntimeError(report.message)if not conforms:    # The RDF report contains ordinary constraint violations.    for triple in report:        pass
```

The example omits exception handling for invalid shapes and runtime errors, which require a separate error path.

### 11.6 Debugging and conformance testing

`debug=True` exposes additional information about shape evaluation, focus nodes, and constraint execution.

Debug output should not be interpreted as a list of blocking validation failures. Diagnostic messages can describe intermediate nonconformance in operations that do not ultimately make the overall report nonconformant.

PySHACL also exposes `check_dash_result`, which checks validation outcomes against DASH test-suite expectations.

That option serves a testing and conformance purpose. It can change the meaning of the first return value from ordinary data conformance to whether an expected test result was matched. It should therefore not be mixed indiscriminately into production validation logic.

Sources:

Python entrypoints: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/entrypoints.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/entrypoints.py?utm_source=chatgpt.com)

Error semantics and API overview: [https://pypi.org/project/pyshacl/](https://pypi.org/project/pyshacl/?utm_source=chatgpt.com)

DASH vocabulary and supporting material: [https://datashapes.org/dash](https://datashapes.org/dash?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com

+2

## 12. Command-line tooling, HTTP services, and deployment

### 12.1 Command-line validator

PySHACL installs a `pyshacl` command-line interface and provides equivalent module execution through `python -m pyshacl`.

A representative invocation is:

```
pyshacl \
  --shapes shapes.ttl \
  --inference rdfs \
  --advanced \
  --format turtle \
  --output report.ttl \
  data.ttl
```

The CLI supports the major programmatic validation features, including Meta-SHACL, ontology imports, remote SPARQL mode, rule iteration, severity controls, focus-node selection, shape selection, multiple inputs, and file-format overrides.

Its report format options include human-readable text, tabular output, Turtle, RDF/XML, JSON-LD, N-Triples, and Notation3.

It also supports shell-appropriate exit status behavior for conformance, runtime errors, and unsupported features.

The package declares additional script entry points, including:

- `pyshacl_rules` for rules expansion.
- `pyshacl_validate` as a validation command alias.
- `pyshacl_server` for the HTTP service.

These are valuable for automating validation outside Python application code—for example, during RDF artifact generation, data exchange, or test execution.

Tagged CLI source: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/cli.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/cli.py?utm_source=chatgpt.com)

Rules CLI source: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/cli_rules.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/cli_rules.py?utm_source=chatgpt.com)

### 12.2 Integrated HTTP REST service

PySHACL includes an optional OpenAPI 3-compatible HTTP validation service.

```
pip install "pyshacl[http]"
pyshacl_server
```

It uses companion Sanic packages and exposes an HTTP interface without requiring an application to build its own validation wrapper from scratch.

The documented default listen address is `127.0.0.1:8099`.

Once the service is running, it exposes documentation endpoints:

```
http://127.0.0.1:8099/docs/swagger
http://127.0.0.1:8099/docs/redoc
http://127.0.0.1:8099/docs/openapi.json
```

The service can be configured using environment variables including `PYSHACL_SERVER`, `PYSHACL_SERVER_LISTEN`, `PYSHACL_SERVER_PORT`, and `PYSHACL_SERVER_HOSTNAME`.

The OpenAPI schema supplies a route into automated HTTP client generation and contract inspection. The HTTP interface is therefore a meaningful integration surface rather than merely a command-line wrapper.

However, it should not be assumed to provide authorization, request isolation, workload quotas, or hardened public multi-tenant execution merely because a REST API is available. Those properties need to be established separately.

### 12.3 Docker distribution

The upstream project also documents a containerized distribution, including use as an HTTP service.

The published container approach is useful when the validation engine should be exposed independently of the Python environment of its caller.

As with other network-facing validation services, external RDF URLs, ontology imports, complex queries, expensive rules, and JavaScript extensions introduce resource and security considerations that warrant explicit deployment controls.

Project documentation: [https://github.com/RDFLib/pySHACL](https://github.com/RDFLib/pySHACL?utm_source=chatgpt.com)

Package scripts and HTTP dependencies: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyproject.toml](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyproject.toml?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1

## 13. Performance, scalability, and correctness boundaries

PySHACL offers several mechanisms for controlling execution cost, but it does not provide a blanket guarantee that every supported validation pattern will scale similarly.

The dominant performance characteristics arise from the shape definitions, target-selection strategy, backing RDF engine, and optional enrichment work.

### 13.1 Important execution-cost mechanisms

| Mechanism                       | Potential benefit                                        | Important qualification                                              |
| ------------------------------- | -------------------------------------------------------- | -------------------------------------------------------------------- |
| Focus-node filtering            | Avoid evaluation of unrelated top-level targets          | Requires correct determination of affected nodes                     |
| Shape selection                 | Avoid executing irrelevant constraints                   | Selected shapes may depend on referenced shapes and shared functions |
| Abort on first failure          | Reduce work when only a failing verdict is needed        | Produces an intentionally incomplete set of findings                 |
| Oxigraph backend                | Improve graph-query execution for suitable workloads     | Python validation overhead remains                                   |
| Remote SPARQL mode              | Avoid copying the complete graph locally                 | Network and endpoint-query costs may dominate                        |
| No pre-inference                | Avoid graph expansion cost                               | May omit inferred facts needed by the intended validation semantics  |
| Noniterative rules              | Bound the number of rule passes                          | May not produce all cascading derivations                            |
| `inplace=True`                  | Avoid unnecessary graph copying for modifying operations | Can mutate shared or persistent input data                           |
| Precompiled pattern constraints | Reuse compiled regular expressions across targets        | Benefits depend on how often patterns are evaluated                  |

PySHACL's release notes explicitly mention precompilation of `sh:pattern` regular expressions, default dataset-union validation, and increasingly selective validation controls. These are useful optimizations, although they do not eliminate expensive graph traversals or SPARQL queries.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



### 13.2 Shape design can dominate execution time

Complexity is not just a function of triple count.

A comparatively small graph can produce expensive validation if its shapes repeatedly traverse transitive paths, execute broad SPARQL queries, or apply deeply nested qualified constraints.

Conversely, a much larger graph with narrow, indexed targets and straightforward property constraints may be comparatively efficient.

The expensive operations to recognize include broad target discovery, recursive shape references, repeated property-path traversal, cross-node aggregation, function evaluation inside SPARQL queries, and repeated inference or rule expansion.

Where data is reused across many validation runs, recomputing the same ontology expansion or derived relationships for every run can become significant. The best placement of those operations is workload-dependent and should preserve the semantic meaning of the resulting graph.

### 13.3 Correctness-sensitive limitations

The following boundaries deserve explicit attention.

SHACL 1.2 compatibility: PySHACL 0.40.1's documented specification baseline remains the established SHACL and extension specifications. It should not be assumed to implement the entire evolving SHACL 1.2 specification.

Incomplete conformance coverage: The project's own feature matrix identifies outstanding test limitations. These include RDFLib's handling of ill-formed literal lexical forms and unsupported pre-binding of `$shapesGraph` in a SHACL-SPARQL test.

Less-tested expression forms: The upstream matrix marks certain node expressions as not tested, despite their appearance in the implemented feature list.

Recursive validation limits: Deep nesting can reach `max_validation_depth`, and nonterminating or unusually expensive recursive structures are not made safe simply by being valid RDF.

Inference completeness: OWL-RL inference is not general OWL reasoning.

Rule convergence: Iterative rules have implementation-defined ordering and execution guards.

Dataset union semantics: Named-graph boundaries do not automatically isolate validation.

Remote execution: Read-only SPARQL access disables features that require mutating or materializing graph data.

RDF data identity: RDF blank nodes have graph-local identity semantics. Combining separately sourced RDF documents and moving them between stores requires care with blank-node scoping and provenance.

No automatic repair: PySHACL reports violations and can derive triples through explicit rules, but a validation report is not itself a transactionally safe remediation procedure.

Primary compatibility matrix: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md](https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md?utm_source=chatgpt.com)

RDFLib literal issue: [https://github.com/RDFLib/rdflib/issues/848](https://github.com/RDFLib/rdflib/issues/848?utm_source=chatgpt.com)

### 13.4 Changes consequential to version compatibility

| Version                | Major change                                                                                                                             |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 0.40.1 — July 2026     | Fixes SHACL expression intersection logic and Python 3.9 typing compatibility                                                            |
| 0.40.0 — July 2026     | Native Oxigraph store support; `DataGraph` abstraction; function execution on both SPARQL engines; removal of `ConjunctiveGraph` support |
| 0.31.0 — January 2026  | Multiple graph inputs, combined and independently validated modes                                                                        |
| 0.29.0 — November 2024 | Inference and rule-generated triples placed into separate named graphs for dataset inputs; Python 3.8 support dropped                    |
| 0.28.0 — October 2024  | Default-union dataset behavior and pattern-related optimization                                                                          |
| 0.27.0 — October 2024  | Dedicated rules expander, focus-node filtering, selected-shape validation, and combined targeted execution                               |

Two upgrade-sensitive distinctions are particularly important.

First, RDFLib's deprecated `ConjunctiveGraph` is not supported as a PySHACL 0.40.x input. Use a `Dataset` for multigraph inputs.

Second, although 0.40.0 release notes refer to OWL-RL 7.6.1 as a minimum, the published 0.40.1 package metadata requires `owlrl>=7.6.2,<8`. The package metadata is the more precise source for the targeted release. Its RDFLib requirement is `rdflib[html]>=7.3.0,<8.0`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+3



Release history: [https://github.com/RDFLib/pySHACL/releases](https://github.com/RDFLib/pySHACL/releases?utm_source=chatgpt.com)

Version-specific package metadata: [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyproject.toml](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyproject.toml?utm_source=chatgpt.com)

## 14. Architectural combinations and integration boundaries

The value of PySHACL is most apparent when its capabilities are considered as composable systems rather than isolated constraint implementations.

### Declarative schema and validation as a reusable asset

Shapes can encode structural, relational, and semantic requirements independently of the code that loads or stores RDF.

This creates a reusable contract that can be applied to data entering a system, already stored data, serialized graph artifacts, or independently maintained datasets.

Core SHACL handles common invariants; SPARQL constraints handle more complex relations; functions and custom targets reduce repetition.

The result can be materially less bespoke validation code, provided the requirements fit RDF's data model and SHACL's supported semantics.

### Reasoning, rules, and validation as distinct engines

A layered semantic pipeline can use RDFS/OWL-RL pre-inference for standard semantic entailments, SHACL-AF rules for application-specific derivations, and validation shapes for enforceable constraints.

These stages have different consequences for persistence and correctness.

Inference and rule expansion can increase the graph's contents; validation ordinarily generates a separate report rather than changing the graph.

Keeping those responsibilities explicit makes it possible to reason about which statements are original, inferred, rule-generated, or merely described in diagnostics.

### Backend independence through RDFLib and Oxigraph

PySHACL's backend abstraction introduces a useful degree of flexibility.

Graph storage and query execution can be delegated to RDFLib or Oxigraph, while validation logic is expressed through a common collection of SHACL definitions.

This avoids tying the conceptual validation schema to one specific physical RDF storage representation.

Backend interchange is nevertheless not equivalent to an unconditional guarantee of identical behavior or performance for every unusual SPARQL construct, custom extension, or store configuration. Those differences should be verified where they are consequential.

### Targeted validation without reimplementing constraint logic

Focus-node and shape selection allow a caller to select a narrow validation scope while retaining the same SHACL constraint engine used for whole-graph validation.

This is a particularly useful distinction from implementing separate “fast validation” and “full validation” algorithms.

However, completeness of targeted validation remains a dependency-analysis question. PySHACL provides the execution controls; it does not claim to provide a universal change-impact graph or incremental constraint-maintenance engine.

### RDF-native diagnostics and downstream analysis

Because reports are RDF graphs, their results can be joined back to source entities, queried, grouped, serialized, or persisted with semantic metadata.

This offers an alternative to inventing bespoke error-object hierarchies or ad hoc JSON validation schemas when RDF is already the common data model.

The report's standard vocabulary is also an interoperability boundary: systems need not share PySHACL's Python process to consume its validation findings.

## 15. Primary-source research map

The following sources are especially useful for an engineer or programming agent investigating specific implementation behavior. All URLs are provided in full.

| Subject                                                            | Source                                                                                                                                                                              |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Overall project, Python usage, CLI, remote mode, HTTP service      | [https://github.com/RDFLib/pySHACL](https://github.com/RDFLib/pySHACL?utm_source=chatgpt.com)                                                                                       |
| Supported SHACL constraints, advanced features, known gaps         | [https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md](https://github.com/RDFLib/pySHACL/blob/v0.40.1/FEATURES.md?utm_source=chatgpt.com)                                     |
| Exact version metadata, dependencies, extras, console scripts      | [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyproject.toml](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyproject.toml?utm_source=chatgpt.com)                               |
| API loading, multiple inputs, Meta-SHACL, serialized reports       | [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/entrypoints.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/entrypoints.py?utm_source=chatgpt.com)               |
| Validation order, graph copying, inference, rules, shape selection | [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/validator.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/validator.py?utm_source=chatgpt.com)                   |
| Rule discovery, ordering, iteration limits                         | [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/rules/\_\_init\_\_.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/rules/__init__.py?utm_source=chatgpt.com)     |
| Graph expansion runner                                             | [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/rule_expand_runner.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/rule_expand_runner.py?utm_source=chatgpt.com) |
| Backend graph adaptation                                           | [https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/graph_abstraction.py](https://github.com/RDFLib/pySHACL/blob/v0.40.1/pyshacl/graph_abstraction.py?utm_source=chatgpt.com)   |
| Rules, constraints, and integration examples                       | [https://github.com/RDFLib/pySHACL/tree/v0.40.1/examples](https://github.com/RDFLib/pySHACL/tree/v0.40.1/examples?utm_source=chatgpt.com)                                           |
| Project regression and specification tests                         | [https://github.com/RDFLib/pySHACL/tree/v0.40.1/test](https://github.com/RDFLib/pySHACL/tree/v0.40.1/test?utm_source=chatgpt.com)                                                   |
| Release history and compatibility changes                          | [https://github.com/RDFLib/pySHACL/releases](https://github.com/RDFLib/pySHACL/releases?utm_source=chatgpt.com)                                                                     |
| SHACL Recommendation                                               | [https://www.w3.org/TR/shacl/](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com)                                                                                                 |
| SHACL Advanced Features                                            | [https://www.w3.org/TR/shacl-af/](https://www.w3.org/TR/shacl-af/?utm_source=chatgpt.com)                                                                                           |
| SHACL-JS                                                           | [https://www.w3.org/TR/shacl-js/](https://www.w3.org/TR/shacl-js/?utm_source=chatgpt.com)                                                                                           |
| OWL-RL reasoning implementation                                    | [https://owl-rl.readthedocs.io/en/latest/](https://owl-rl.readthedocs.io/en/latest/?utm_source=chatgpt.com)                                                                         |
| RDFLib RDF model, datasets, SPARQL, serialization                  | [https://rdflib.readthedocs.io/en/stable/](https://rdflib.readthedocs.io/en/stable/?utm_source=chatgpt.com)                                                                         |
| PyOxigraph storage and SPARQL                                      | [https://pyoxigraph.readthedocs.io/en/stable/store.html](https://pyoxigraph.readthedocs.io/en/stable/store.html?utm_source=chatgpt.com)                                             |

## 16. Overall capability perspective

PySHACL's primary distinguishing characteristic is that it combines graph-native validation with a relatively rich declarative computation model.

The most consequential capabilities beyond ordinary structural SHACL validation are its SPARQL-based constraints, reusable custom constraint components, advanced target selection, SHACL functions, node expressions, iterative rules, RDFS/OWL-RL pre-inference, and RDF-native reporting.

Its recent evolution also strengthens its role as an execution and integration layer. Multi-graph validation, targeted shape/focus-node execution, provenance-aware dataset expansion, and support for Oxigraph-backed stores allow a broader range of RDF processing models than a simple single-file validation tool.

The library's boundaries remain equally important. It depends on external RDF engines for storage and query execution, OWL-RL for semantic reasoning, and an optional JavaScript runtime for SHACL-JS. Its rules are primarily additive derivations, remote mode is read-only with restricted functionality, and selective validation does not automatically provide complete incremental correctness.

For an advanced engineering audience, PySHACL is therefore best understood not merely as a Python SHACL checker, but as a standards-oriented engine for declaring, executing, and reporting graph invariants, enriched by selected semantic reasoning and graph-generation capabilities.

# PySHACL — Capability Reference Addendum

Target version: PySHACL 0.40.2\
Research date: November 1, 2026\
Companion document: PySHACL 0.40.1 — Comprehensive Library Capability Reference\
Upstream: [https://github.com/RDFLib/pySHACL](https://github.com/RDFLib/pySHACL?utm_source=chatgpt.com)

This addendum supplements the original reference with additional capabilities, implementation-level distinctions, compatibility corrections, and newly released behavior. It is intended to be read alongside the existing document without replacing its explanations of SHACL Core, graph paths, reasoning, rules, storage backends, or validation fundamentals.

## 1. Version update: PySHACL 0.40.2

PySHACL 0.40.2 is the current stable release, published to PyPI on October 28, 2026. It follows 0.40.1 with several correctness, interoperability, and robustness improvements. These changes do not introduce a new functional family, but they affect important behavior documented in the original reference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

Robustness · RDFLib/pySHACL · GitHub+1



### 1.1 Oxigraph-backed validation-report performance

Previous implementations could inadvertently execute a full-store count query while constructing validation results.

An internal expression equivalent to `datagraph or shapesgraph` evaluated the truthiness of the `DataGraph` abstraction. For an Oxigraph-backed graph, that truthiness check could invoke `len()`, translating into an expensive `COUNT` operation over the store.

Version 0.40.2 eliminates this behavior.

The distinction is consequential for validation workloads producing many results: report construction should not repeatedly require counting the entire dataset. The improvement targets a specific accidental operation, not all remaining costs of result creation, shape evaluation, or graph querying.

### 1.2 RDF literal equivalence across backends

Oxigraph can expose simple string literals as explicitly typed `xsd:string` literals, whereas RDFLib often represents the corresponding RDF term as a plain string literal.

Previously, this representation difference could cause false constraint violations when comparing data terms against values declared in shapes, notably for `sh:in` and `sh:hasValue`.

Version 0.40.2 normalizes these terms at the backend boundary to preserve the expected equivalence.

This fix is relevant to backend interoperability: a shapes graph should not produce different conformance decisions merely because equivalent simple string literals use different library representations.

### 1.3 Concurrent initialization of shapes graphs

PySHACL adds internal system triples to its shapes-graph context. When multiple validators share an RDFLib graph, concurrent initialization could cause simultaneous writes to a store that does not guarantee safe concurrent mutation.

Version 0.40.2 introduces a lock around these writes and avoids adding system triples that are already present.

This improves the safety of concurrently initializing validators against shared shapes-graph objects. It does not establish general thread safety for concurrent graph mutation, inference, rule expansion, or arbitrary RDFLib store operations.

### 1.4 Full ontology mixer compatibility

The release also fixes a compatibility problem affecting `PYSHACL_USE_FULL_MIXIN=1`, where the ontology mixer could return an ordinary graph rather than the wrapper expected by later execution stages.

The release notes explicitly indicate that a more complete fix is anticipated. The full mixer remains an implementation-sensitive execution option rather than a fully documented replacement for the default ontology inoculation behavior.

Primary sources

[https://github.com/RDFLib/pySHACL/releases/tag/v0.40.2](https://github.com/RDFLib/pySHACL/releases/tag/v0.40.2?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/graph_abstraction.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/graph_abstraction.py?utm_source=chatgpt.com)

[https://pypi.org/project/pyshacl/0.40.2/](https://pypi.org/project/pyshacl/0.40.2/?utm_source=chatgpt.com)

## 2. Specification support corrections

### 2.1 SHACL-AF validation-result annotations are not implemented

The original reference describes the SHACL-AF result-annotation constructs as available mechanisms for attaching additional RDF statements to validation results.

PySHACL's upstream feature matrix explicitly marks the following constructs as not implemented:

- `sh:annotationProperty`
- `sh:annotationVarName`
- `sh:annotationValue`

The SHACL-AF specification defines these properties for declaratively constructing additional statements associated with SPARQL-generated validation results. Their specification-level existence does not imply that PySHACL processes them.

The distinction is between native result generation and post-validation result enrichment.

PySHACL produces standards-based RDF validation reports, including supported metadata such as the focus node, source shape, source constraint, path, value, severity, and message. These reports can subsequently be enriched with additional RDF statements using RDFLib or another RDF-processing implementation.

However, defining SHACL-AF annotation declarations in a shapes graph should not be assumed to trigger automatic generation of the corresponding result triples.

This is a meaningful boundary for systems that treat validation reports as semantically rich, queryable artifacts. Automated result enrichment requires an additional processing mechanism unless the desired information can already be expressed through supported report fields.

### 2.2 The SHACL Rules entailment declaration is unsupported

The feature matrix also identifies `sh:entailment` as unimplemented.

SHACL-AF defines the declaration of an entailment regime as a mechanism for describing the semantic treatment required by a shapes graph. PySHACL does not automatically interpret `sh:entailment` as a request to activate a corresponding reasoning engine.

Its supported RDFS and OWL-RL inference modes instead depend on explicit execution configuration through `inference=` or the corresponding CLI option.

The two mechanisms must therefore remain distinct:

- `sh:entailment` is a specification-defined RDF declaration that PySHACL does not currently implement.
- `inference='rdfs'`, `'owlrl'`, or `'both'` is an implemented PySHACL execution option invoking supported reasoning through OWL-RL.

A shapes graph containing entailment declarations is not sufficient to ensure that a particular inference regime has been applied before validation.

### 2.3 Non-validating property-shape metadata

The upstream feature matrix marks three SHACL non-validating property-shape characteristics as missing from its corresponding functionality coverage:

| Construct         | Specification-level purpose                             | PySHACL distinction                                         |
| ----------------- | ------------------------------------------------------- | ----------------------------------------------------------- |
| `sh:order`        | Suggest presentation ordering of property shapes        | Not implemented as a general presentation-ordering facility |
| `sh:group`        | Associate related property shapes with a property group | No native form-grouping or UI generation behavior           |
| `sh:defaultValue` | Express a suggested default value                       | Does not automatically populate missing RDF values          |

These statements require one qualification: PySHACL does use `sh:order` operationally for SHACL rule and shape execution ordering. That is separate from implementing the non-validating property-shape presentation semantics defined by SHACL Core.

The presence of these RDF annotations does not prevent external consumers from interpreting them. Applications can read the metadata directly from a shapes graph and apply it independently of PySHACL's validation engine.

Primary sources

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/FEATURES.md](https://github.com/RDFLib/pySHACL/blob/v0.40.2/FEATURES.md?utm_source=chatgpt.com)

[https://www.w3.org/TR/shacl-af/#sparql-constraints-annotations](https://www.w3.org/TR/shacl-af/?utm_source=chatgpt.com#sparql-constraints-annotations)

[https://www.w3.org/TR/shacl-af/#rules-entailment](https://www.w3.org/TR/shacl-af/?utm_source=chatgpt.com#rules-entailment)

[https://www.w3.org/TR/shacl/#nonValidation](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com#nonValidation)

## 3. Implicit class targets and shape discovery

### 3.1 Implicit class targets

SHACL Core provides an implicit targeting mechanism for shapes that are also RDFS classes.

A shape does not always require an explicit `sh:targetClass` declaration. If the shape is itself declared to be an instance of `rdfs:Class`, it can implicitly target instances of the class represented by that shape's RDF node.

PySHACL implements this through `Shape.implicit_class_targets()` and includes the discovered class in normal focus-node selection.

For example:

```
@prefix ex:   <https://example.org/> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Equipment
    a rdfs:Class, sh:NodeShape ;
    sh:property [
        sh:path ex:identifier ;
        sh:minCount 1 ;
    ] .
```

Here, `ex:Equipment` simultaneously defines a class and a shape. PySHACL can discover instances of `ex:Equipment` as focus nodes without requiring:

```
sh:targetClass ex:Equipment
```

The implementation also accounts for applicable subclass relationships when discovering class-based focus nodes.

Architectural implication: An RDF vocabulary can carry validation constraints directly on its class definitions. This can reduce duplicated class/shape mappings and support vocabularies that combine semantic declarations with structural requirements.

However, combining ontology and validation definitions also creates coupling: consumers expecting an ontology to be purely descriptive may encounter SHACL constraints attached to the same RDF resources.

### 3.2 Implicit NodeShape and PropertyShape discovery

PySHACL's `ShapesGraph` implementation does more than discover resources explicitly typed as `sh:NodeShape` or `sh:PropertyShape`.

It also identifies shapes from their use in SHACL declarations, including:

- Subjects of standard target declarations.
- Subjects or objects of `sh:node` and `sh:property`.
- Objects of `sh:not` and `sh:qualifiedValueShape`.
- Members of RDF lists used by `sh:and`, `sh:or`, and `sh:xone`.

PySHACL determines whether an implicitly discovered shape is a NodeShape or PropertyShape using its `sh:path` declaration.

This supports reusable anonymous shapes and nested constraint definitions without requiring a separate explicit RDF type declaration for every intermediate shape.

An important distinction remains: shape discovery is not equivalent to focus-node targeting. A shape may be recognized and available for nested validation while having no independently selected focus nodes in a normal whole-graph validation run.

The implicit discovery mechanisms also participate in selected-shape execution. PySHACL has a separate harvesting path for `use_shapes`, which traverses referenced shapes and constructs the relevant subset of the shapes graph.

This is more involved than simply filtering a precomputed list of shapes, although it does not guarantee that every possible dependency of a selectively validated shape has been evaluated.

Primary sources

[https://www.w3.org/TR/shacl/#implicit-targetClass](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com#implicit-targetClass)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/shape.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/shape.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/shapes_graph.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/shapes_graph.py?utm_source=chatgpt.com)

## 4. Declarative deactivation across validation and rules

The original reference discusses `sh:deactivated` in connection with SHACL Rules. PySHACL supports deactivation at additional levels of the validation model.

### 4.1 Shape-level deactivation

A NodeShape or PropertyShape can declare:

```
sh:deactivated true
```

When PySHACL evaluates an explicitly deactivated shape, it treats the shape as conforming without executing its normal constraints.

This works independently of whether the shape was explicitly targeted, implicitly targeted, or reached through another shape.

The ability to disable a shape declaratively is different from selecting a subset of shapes through `use_shapes`.

`use_shapes` is an execution-time selection mechanism supplied by the caller. `sh:deactivated` is part of the shapes graph and travels with that schema when the RDF is distributed or reused.

### 4.2 SPARQL constraint-level deactivation

PySHACL also recognizes `sh:deactivated` on individual SPARQL constraint definitions attached through `sh:sparql`.

This permits a shape to retain its other constraints while disabling a particular SPARQL validation query.

For example, a NodeShape could continue enforcing cardinality, datatype, and class constraints while excluding one expensive or provisionally defined SPARQL constraint.

This is more granular than deactivating the entire shape.

### 4.3 Rule deactivation

SHACL Rules can also be deactivated individually, allowing a shapes graph to retain rule definitions that are not executed during a particular validation or expansion configuration.

Together, the three mechanisms enable declarative control at different levels:

| Level             | Effect                                        |
| ----------------- | --------------------------------------------- |
| Shape             | Skip the shape's validation                   |
| SPARQL constraint | Skip a particular SPARQL validation condition |
| SHACL rule        | Skip a particular derivation rule             |

Deactivation is especially useful for independently versioned constraint vocabularies and collections containing alternative or experimental validation definitions. It does not provide a native policy engine for dynamically choosing active constraints; the enabled/deactivated RDF declarations still have to be maintained or selected by a caller.

Primary sources

[https://www.w3.org/TR/shacl/#deactivated](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com#deactivated)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/shape.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/shape.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/constraints/sparql/sparql_based_constraints.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/constraints/sparql/sparql_based_constraints.py?utm_source=chatgpt.com)

## 5. SPARQL execution context, namespace management, and parameterized diagnostics

PySHACL's SPARQL integration extends beyond submitting arbitrary SELECT and ASK queries to an RDF engine. It implements SHACL-specific query preparation, variable binding, namespace declarations, and validation-message substitution.

These mechanisms are important for building reusable SHACL-SPARQL definitions rather than treating each embedded query as an isolated string.

### 5.1 RDF-defined namespace declarations

PySHACL supports SHACL-SPARQL namespace declarations through:

| Construct      | Responsibility                                                       |
| -------------- | -------------------------------------------------------------------- |
| `sh:prefixes`  | Identifies an RDF resource containing applicable prefix declarations |
| `sh:declare`   | Associates a prefix declaration with that resource                   |
| `sh:prefix`    | Supplies the textual prefix name                                     |
| `sh:namespace` | Supplies the namespace IRI                                           |

The `SPARQLQueryHelper` implementation collects these declarations and constructs the appropriate SPARQL `PREFIX` prologue before query execution.

Declarations may be associated with ontology resources and shapes-graph context. This allows multiple constraints and functions to reuse namespace declarations supplied through the shapes graph.

The result is an RDF-native mechanism for packaging executable SPARQL definitions with the vocabulary information needed to interpret their qualified names.

This can reduce repeated query prologues and support the portability of reusable constraint libraries. It also makes namespace resolution part of the validation artifact rather than wholly dependent on the RDFLib namespace manager maintained by application code.

### 5.2 SHACL-specific variable bindings

SHACL-SPARQL provides a query execution context containing variables associated with the current shape evaluation.

PySHACL's query helper implements the relevant binding and rewriting mechanisms for variables including:

| Variable        | Meaning                                                     |
| --------------- | ----------------------------------------------------------- |
| `$this`         | Current focus node                                          |
| `$value`        | Current value node where the validator context supplies one |
| `$currentShape` | Current shape                                               |
| `$PATH`         | Property-path expression associated with a PropertyShape    |

The `$PATH` mechanism is especially useful for reusable property constraints.

Rather than hardcoding a predicate into a SPARQL query, a constraint can refer to the property path supplied by the current shape. PySHACL translates the SHACL path into a corresponding SPARQL property-path expression.

This permits the same validator definition to operate over different predicates or more complex graph paths.

The shape itself becomes a parameter to the query's graph traversal, not merely a container for the query text.

The implementation does not support pre-binding `$shapesGraph`. Encountering that variable in the relevant query-preparation path raises an unsupported-feature error.

### 5.3 Restrictions on SHACL-SPARQL validation queries

SHACL-SPARQL imposes restrictions beyond ordinary SPARQL syntax, and PySHACL actively checks for several of them.

For SHACL-SPARQL validation queries, its implementation prohibits:

- `MINUS` clauses.
- `VALUES` clauses.
- Federated `SERVICE` clauses.

It also enforces requirements involving potentially pre-bound variables in nested SELECT queries and prohibits rebinding reserved variables through `AS`.

These restrictions apply to the SHACL-SPARQL validation context. They should not be generalized into claims that RDFLib, Oxigraph, or all PySHACL rule/function execution paths lack the corresponding SPARQL capabilities.

Consequently, a valid standalone SPARQL query may require restructuring before it can be used as a SHACL-SPARQL validator.

### 5.4 Parameterized validation messages

PySHACL supports variable substitution within messages associated with SPARQL validation results.

Message templates can reference bound variables using SHACL-style placeholders such as `{?value}` and `{$this}`.

For a query returning additional diagnostic variables, those bindings can contribute explanatory information to the generated validation result.

The report-generation implementation also supports `sh:sourceConstraint`, identifying a particular constraint definition in addition to the more general `sh:sourceConstraintComponent`.

This permits a report consumer to distinguish which reusable constraint mechanism was involved from which particular declared constraint produced the finding.

Architectural implication: A SPARQL constraint can combine reusable query logic, dynamically supplied shape paths, parameter bindings, and structured diagnostic context. This is substantially richer than using SPARQL merely as a Boolean or row-returning validation expression.

Primary sources

[https://www.w3.org/TR/shacl/#sparql-prefixes](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com#sparql-prefixes)

[https://www.w3.org/TR/shacl/#sparql-constraints](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com#sparql-constraints)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/helper/sparql_query_helper.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/helper/sparql_query_helper.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/constraints/constraint_component.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/constraints/constraint_component.py?utm_source=chatgpt.com)

## 6. Specialized reusable custom constraint components

PySHACL implements distinct validator attachment mechanisms for reusable SHACL constraint components.

These mechanisms deserve explicit treatment because they permit the same parameterized constraint vocabulary to select different execution logic depending on whether it is applied to a NodeShape or PropertyShape.

### 6.1 General and specialized validators

| Validator declaration  | Role in PySHACL                                                             |
| ---------------------- | --------------------------------------------------------------------------- |
| `sh:validator`         | General validator used when no applicable specialized validator is selected |
| `sh:nodeValidator`     | Validator specialized for NodeShapes                                        |
| `sh:propertyValidator` | Validator specialized for PropertyShapes                                    |

For SPARQL-backed custom constraint components, the implementation selects a specialized validator when one is available for the corresponding shape type.

The tagged implementation requires SPARQL SELECT validators for these shape-specific forms and a SPARQL ASK validator for the general fallback.

The distinction also affects the meaning of query results. A SELECT validator identifies violations through result bindings, while an ASK validator determines whether a condition is satisfied for the supplied evaluation context.

This allows a constraint vocabulary to use one declarative abstraction while providing different mechanisms for node-level and value-level validation.

### 6.2 Constraint parameter definitions

Reusable constraint components define parameters using `sh:parameter`.

PySHACL represents these declarations through `SHACLParameter`, which exposes information including:

- Parameter path and derived local name.
- Node-kind and datatype metadata.
- Optionality through `sh:optional`.
- Parameter ordering through `sh:order`.

The custom constraint component factory distinguishes mandatory from optional parameters. It requires the component to declare at least one parameter and at least one non-optional parameter.

Parameters are bound to the shape using the component, allowing a general validator to operate with different declared values rather than requiring a separate constraint implementation for every variation.

For example, a domain-specific validation vocabulary could define a parameterized relationship constraint and reuse it across many shapes with different property paths or reference values.

### 6.3 Implementation boundaries

These are declarative SPARQL or JavaScript extension mechanisms. They do not establish a general stable Python plugin API for registering arbitrary validator classes.

The internal `CustomConstraintComponentFactory` constructs implementation-specific validator objects using the shapes graph and the declared constraint component definitions.

It is useful to understand this internal architecture when investigating extension behavior or unsupported features, but direct subclassing or replacement of the internal machinery should not be confused with the standards-based extension model that PySHACL documents.

Primary sources

[https://www.w3.org/TR/shacl/#sparql-constraint-components](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com#sparql-constraint-components)

[https://www.w3.org/TR/shacl/#constraint-components-validators](https://www.w3.org/TR/shacl/?utm_source=chatgpt.com#constraint-components-validators)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/constraints/constraint_component.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/constraints/constraint_component.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/constraints/sparql/sparql_based_constraint_components.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/constraints/sparql/sparql_based_constraint_components.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/parameter.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/parameter.py?utm_source=chatgpt.com)

## 7. SHACL function execution contracts

The original reference describes the role of `sh:SHACLFunction` and `sh:SPARQLFunction`. Their exact invocation and result semantics introduce additional distinctions relevant to composing reliable declarative computations.

### 7.1 SPARQL SELECT versus ASK functions

PySHACL supports two SPARQL function bodies with different result contracts.

A SPARQL function defined through `sh:ask` produces a Boolean RDF literal. If it declares `sh:returnType`, the implementation requires the return type to be `xsd:boolean`.

A function defined through `sh:select` produces a result derived from its SELECT query. On the RDFLib execution path, PySHACL selects the first projected variable from the first result binding.

A function therefore does not automatically expose an arbitrary SELECT result set as its return value.

This matters when a graph computation naturally produces multiple values. A function intended to represent one computed RDF term has a different contract from a query used directly to discover a collection of graph nodes.

### 7.2 Parameter ordering and optional arguments

SHACL functions use parameter declarations with attributes including `sh:order`, `sh:optional`, and `sh:returnType`.

PySHACL determines argument order from the parameter declarations. When explicit parameter ordering is not available, its implementation uses parameter-name ordering.

The implementation's direct execution method also checks argument count against the declared parameter count. In this path, declaring a parameter optional permits a `None` value but does not automatically mean that the positional argument can be omitted without affecting arity.

This distinction is important when translating an RDF-defined function signature into application-level calls or expecting optional parameters to behave like Python default arguments.

### 7.3 Registration with SPARQL execution engines

PySHACL registers supported SPARQL functions with its underlying graph/query abstraction, permitting the functions to be invoked from compatible SPARQL expressions.

The function implementation distinguishes RDFLib and Oxigraph execution paths. For Oxigraph, PySHACL supplies custom function callbacks and converts terms between Oxigraph and RDFLib representations.

This is an important benefit of the newer graph abstraction: reusable function declarations can remain associated with the SHACL vocabulary even when the underlying SPARQL engine changes.

However, backend compatibility is not equivalent to complete behavioral identity in every edge case.

For example, the 0.40.2 source uses different internal no-result representations for SELECT functions on the RDFLib and Oxigraph paths. Applications relying on particular missing-result semantics should therefore verify their behavior on the selected backend.

Function registration and unregistration also occur as part of the validation or rule-expansion lifecycle. These callbacks should not be assumed to remain permanently available in arbitrary external SPARQL execution contexts.

Primary sources

[https://www.w3.org/TR/shacl-af/#functions](https://www.w3.org/TR/shacl-af/?utm_source=chatgpt.com#functions)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/functions/shacl_function.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/functions/shacl_function.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/functions/\_\_init\_\_.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/functions/__init__.py?utm_source=chatgpt.com)

## 8. Additional SHACL Rules semantics

### 8.1 Multiple rule conditions

A SHACL Rule can express applicability through `sh:condition`.

PySHACL's implementation accepts condition references as individual shapes and also recognizes an RDF list containing multiple condition shapes.

For each candidate focus node, PySHACL evaluates the applicable conditions using the validation engine. The focus node qualifies for rule execution only when the required condition shapes conform.

Multiple conditions therefore behave conjunctively in this implementation.

This provides a declarative mechanism for separating the question of whether a derivation is applicable from what statements the derivation produces.

A rule can be gated by existing structural or semantic constraints without repeating their complete validation logic in the rule body.

For example, a rule producing a derived classification could require that its focus node satisfy separate shapes representing evidence availability, relationship completeness, and admissible values.

Because those conditions themselves invoke shape validation, their computational cost and recursion behavior participate in rule execution. Conditions are not merely lightweight filters evaluated independently of the SHACL validation machinery.

### 8.2 Rule-expansion failure representation

`shacl_rules()` differs from `validate()` in how it represents a `ValidationFailure`.

The `validate()` API returns a validation tuple and can place a `ValidationFailure` object in the report position.

The dedicated rule-expansion entry point handles such a failure differently:

- With graph output requested, it constructs an RDF graph describing the failure using `sh:ValidationFailure` and a message.
- With serialized output requested, it returns a textual error description instead of serialized expanded RDF.

Therefore, an ordinary RDF graph returned by `shacl_rules()` does not unconditionally establish that rule expansion succeeded.

A caller expecting a successfully expanded graph must distinguish it from an error-bearing graph. Similarly, a serialized return value is not guaranteed to be parseable RDF when rule expansion encounters a formal validation failure.

Other load or runtime errors can still propagate as exceptions.

Primary sources

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/rules/shacl_rule.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/rules/shacl_rule.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/entrypoints.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/entrypoints.py?utm_source=chatgpt.com)

[https://www.w3.org/TR/shacl-af/#rules](https://www.w3.org/TR/shacl-af/?utm_source=chatgpt.com#rules)

## 9. Ontology inoculation versus complete ontology mixing

The `ont_graph` parameter provides additional ontology information to the validation engine. The default processing behavior is more selective than a general RDF graph union.

### 9.1 Selective ontology inoculation

PySHACL's default inoculation implementation traverses relevant RDFS and OWL declarations in the ontology graph and incorporates associated definitions into the working data graph.

Its processing includes class and property declarations, supported ontology axioms, and referenced blank-node structures. It can also copy associated named-individual structures.

This means inoculation is not restricted exclusively to TBox-style statements, but neither is it a general-purpose transfer of every triple from the supplied ontology graph.

Ordinary instance statements that do not participate in the selected ontology-copying mechanisms may not appear in the resulting validation graph.

The distinction matters when a graph contains both a semantic vocabulary and additional instance facts that shape constraints are expected to inspect.

Ontology inoculation supplies selected semantic context; it is not equivalent to arbitrary graph merging.

### 9.2 Full mixing as an implementation-specific alternative

The validator and rule-expansion runner recognize an environment variable:

```
PYSHACL_USE_FULL_MIXIN=1
```

When enabled, the implementation uses its full graph-mixing routines instead of the default inoculation path.

The variable is read during module initialization in the tagged implementation. Its value therefore needs to be established before the relevant module is imported, rather than treated as a dynamically reconfigurable per-validation option.

This setting is not a replacement for `inference=`. Ontology mixing determines which supplied facts and definitions enter the working graph, while inference derives additional facts under a selected entailment regime.

The two operations can be complementary, but they have different semantics.

Full mixing also introduces different graph-copying and mutation considerations. In particular, `inplace=True` can make modification of the supplied graph observable to the caller.

Because the 0.40.2 release notes identify an interim fix for the full mixer and indicate further improvements are pending, the option should be understood as implementation-sensitive rather than a universally interchangeable mode with guaranteed equivalent provenance and copying behavior.

### 9.3 Architectural distinction

There are three separable operations:

| Operation             | Responsibility                                                  |
| --------------------- | --------------------------------------------------------------- |
| Ontology inoculation  | Import selected semantic definitions and related structures     |
| Complete graph mixing | Incorporate the supplied graph content more broadly             |
| RDFS/OWL-RL inference | Derive additional statements from available facts and semantics |

For graph-processing systems, treating these as separate operations permits clearer control over what constitutes original data, supplied ontology knowledge, and derived knowledge.

In particular, the decision to expose ontology instance data to SHACL constraints should not be conflated with the decision to perform semantic inference.

Primary sources

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/rdfutil/inoculate.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/rdfutil/inoculate.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/rdfutil/clone.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/rdfutil/clone.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/validator.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/validator.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/rule_expand_runner.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/rule_expand_runner.py?utm_source=chatgpt.com)

## 10. Integrated HTTP service: execution contract and limitations

PySHACL's integrated REST service deserves a more precise distinction from the Python API.

The HTTP service is not a complete network-accessible equivalent of every option supported by `validate()`.

### 10.1 Request and response model

The tagged implementation exposes a `POST /validate` endpoint that accepts an `application/json` request.

The request includes a serialized RDF data graph and optionally a serialized shapes graph and ontology graph, together with supported execution settings.

The HTTP schema exposes settings including advanced-feature execution, inference, OWL imports, severity allowances, rule iteration, JavaScript support, and Meta-SHACL.

However, several capabilities available through Python are not exposed through the HTTP request schema.

These include focus-node selection, shape selection, explicit remote SPARQL mode, independently validating multiple inputs through `validate_each()`, and several lower-level execution controls.

The interface therefore provides a dedicated validation service, but callers requiring the full Python execution surface cannot assume that every capability is accessible remotely.

### 10.2 Content negotiation

The service recognizes these response media types:

| Accept header           | Response representation                                                              |
| ----------------------- | ------------------------------------------------------------------------------------ |
| `text/plain`            | Human-readable validation result                                                     |
| `application/json`      | Ordinary JSON containing conformance status, textual report, and failure information |
| `application/ld+json`   | RDF validation report serialized as JSON-LD                                          |
| `text/turtle`           | Turtle-serialized RDF validation report                                              |
| `application/rdf+xml`   | RDF/XML validation report                                                            |
| `application/xml`       | XML serialization of the RDF report                                                  |
| `application/n-triples` | N-Triples validation report                                                          |

The distinction between `application/json` and `application/ld+json` is particularly important.

The former is a conventional API response object, not an RDF graph representation. The latter is intended to preserve the RDF validation-report structure.

When the HTTP handler encounters certain processing failures, its implementation can return a JSON failure response even when an RDF representation was requested.

A nonconformant data graph also does not necessarily produce an HTTP error status. Consumers need to inspect the validation result rather than treating an HTTP 200 response as proof of conformance.

### 10.3 Source-identified HTTP parameter inconsistencies

Direct inspection of the 0.40.1 and 0.40.2 tagged source reveals several mismatches between the arguments supplied by the HTTP handler and those recognized by the Python validation entry point.

| HTTP handler supplies   | Python API expects |
| ----------------------- | ------------------ |
| `ontology_graph`        | `ont_graph`        |
| `ontology_graph_format` | `ont_graph_format` |
| `metashacl`             | `meta_shacl`       |

The Python `validate()` entry point accepts additional keyword arguments through `**kwargs`, but its tagged implementation does not process these particular names as aliases for the intended settings.

As a result, the HTTP handler appears to accept requests for ontology inoculation and Meta-SHACL without activating those features through the expected arguments.

This is a source-identified implementation discrepancy, not a runtime-tested finding. It should not be described as a documented feature or intentional limitation. Its importance is that the server's advertised request schema may not accurately reflect the processing performed by the installed release.

The Python API and primary CLI use the recognized argument names and are not subject to this particular forwarding mismatch.

### 10.4 Source-identified standalone server entry-point mismatch

The 0.40.2 package metadata declares the following console script:

```
pyshacl_server = "pyshacl.http:cli"
```

The tagged package instead contains `pyshacl/sh_http.py`, which exposes a `main()` function. No matching `pyshacl.http` module is present in the tagged source tree.

Consequently, the standalone script declaration appears inconsistent with the packaged implementation.

The main CLI uses the expected module:

```
pyshacl --server
```

This routes through `pyshacl.sh_http.main`, making it the source-supported server invocation.

As with the HTTP parameter discrepancy, this is based on inspection of upstream source and metadata rather than execution of the published wheel.

### 10.5 Operational boundary

The HTTP implementation uses Sanic and associated optional dependencies, and starts a single-process server by default.

Its availability does not establish support for automatic horizontal scaling, workload isolation, authorization, request quotas, or secure execution of untrusted shapes and extension code.

The service is best understood as a convenient HTTP validation interface whose precise supported controls and response contracts are determined by its tagged implementation.

Primary sources

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/sh_http.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/sh_http.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/entrypoints.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/entrypoints.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/cli.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/cli.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyproject.toml](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyproject.toml?utm_source=chatgpt.com)

## 11. Additional Python interfaces and packaged capabilities

### 11.1 Exported engine objects

In addition to its principal functional entry points, PySHACL exposes several implementation classes through the package's top-level exports:

| Export             | Role                                                       |
| ------------------ | ---------------------------------------------------------- |
| `Validator`        | Main validation engine and execution orchestration         |
| `RuleExpandRunner` | Dedicated SHACL Rules expansion engine                     |
| `ShapesGraph`      | Shapes-graph representation, discovery, and caching        |
| `Shape`            | Representation and evaluation of an individual SHACL shape |

These classes expose parts of the engine's conceptual structure directly to Python.

For example, `ShapesGraph` provides access to discovered shapes and shape selection by URI. `Shape` carries properties including its associated graph, RDF node, type, deactivation state, and validation behavior.

This can support advanced introspection, engine investigation, and specialized integration beyond calling `validate()` alone.

However, inclusion in the package's `__all__` does not constitute a guarantee that every method or attribute is maintained as a stable, independently versioned extension API.

The underlying engine classes have implementation-specific assumptions about graph abstractions, options, caches, and constraint machinery. Direct use should be distinguished from the more conventional documented entry points.

Source

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/\_\_init\_\_.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/__init__.py?utm_source=chatgpt.com)

### 11.2 Bundled vocabulary resources

PySHACL packages local representations of several important RDF vocabularies, including SHACL, SHACL-SHACL, the DASH vocabulary, and related schema definitions.

The validator registers recognized vocabulary IRIs with the RDF-loading machinery so that known resources can resolve to packaged representations.

These resources support functionality such as Meta-SHACL validation and compatibility with shapes referencing common ontology definitions.

The architectural benefit is reduced dependence on live network retrieval for certain standard resources whose packaged versions are known to PySHACL.

This does not imply that arbitrary `owl:imports` references are resolved locally, nor that importing a bundled DASH vocabulary automatically enables every capability described by DASH.

It also does not eliminate version considerations: the packaged vocabulary content is associated with the installed PySHACL distribution.

Sources

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/validator.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/validator.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/tree/v0.40.2/pyshacl/assets](https://github.com/RDFLib/pySHACL/tree/v0.40.2/pyshacl/assets?utm_source=chatgpt.com)

### 11.3 CLI exit statuses and automation semantics

The validator CLI distinguishes several outcomes through process exit codes.

| Exit code | Interpretation                                                                         |
| --------- | -------------------------------------------------------------------------------------- |
| `0`       | Validation completed and the selected graph or graphs conformed                        |
| `1`       | Nonconformance or a formal validation failure; certain input errors also use this code |
| `2`       | Shape, constraint, rule-loading, or other runtime errors                               |
| `3`       | An explicitly unimplemented feature was encountered                                    |

The input-error qualification is important. For example, an unavailable input file can result in exit code 1, so this code does not alone establish that validation successfully completed and found a data violation.

For multiple independently validated graphs, the CLI aggregates conformance status and returns a successful exit code only when every input conforms.

The CLI therefore provides a useful process-level interface for validation automation, but applications requiring precise classification of failure modes may need to inspect stderr, returned reports, or the Python API's typed exceptions.

Source

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/cli.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/cli.py?utm_source=chatgpt.com)

### 11.4 Standalone executable packaging

The upstream repository also includes a PyInstaller specification for packaging the CLI into a standalone executable.

This provides a potential distribution route for environments where embedding a complete Python application environment is undesirable.

The presence of the specification does not establish that every release publishes a prebuilt standalone executable, or that all optional functionality is automatically bundled with the executable.

Source

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/pyshacl-cli.spec](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/pyshacl-cli.spec?utm_source=chatgpt.com)

## 12. Additional semantic and implementation boundaries

The following distinctions connect the supplementary capabilities above without repeating the original reference's broader discussion of validation correctness and performance.

### 12.1 Recognizing a shape does not imply evaluating it

A resource can be identified as a NodeShape or PropertyShape through implicit shape discovery without independently acquiring any focus nodes.

The existence of a shape in the shapes graph, or in PySHACL's internal shape cache, does not establish that it participates in every validation run.

Target discovery, reference-based evaluation, deactivation, and explicit shape selection remain separate considerations.

### 12.2 Graph metadata, constraints, and executable extensions are different kinds of declarations

A shapes graph can contain presentation metadata, validation constraints, custom functions, rules, and specification-defined extension declarations.

Not all of these have executable semantics in PySHACL.

In particular, unsupported SHACL-AF annotations and entailment declarations must not be treated like implemented constraints or rules merely because their RDF vocabulary terms are recognized.

This distinction becomes important when treating a shapes graph as a general declarative program rather than as a validation schema alone.

### 12.3 Declaring optionality does not automatically establish Python-style defaults

In custom constraints and functions, `sh:optional` is part of an RDF-defined parameter model.

The exact runtime interpretation depends on the corresponding validator or function execution implementation.

For functions, PySHACL's direct execution path checks the number of supplied arguments against the declared parameter count. Optionality therefore should not be assumed to provide Python-like positional argument omission or automatic default-value evaluation.

### 12.4 Exposing an extension point does not guarantee backend-independent semantics

The 0.40.x graph abstraction permits many common SHACL operations to execute using either RDFLib or Oxigraph.

Nevertheless, SHACL functions, SPARQL query results, RDF literal normalization, graph copying, and custom extension callbacks involve backend-specific conversion and execution paths.

The 0.40.2 fixes demonstrate both the value of this abstraction and the importance of preserving semantic equivalence between engines.

Backend independence is therefore best understood as a shared PySHACL capability interface supported by multiple RDF implementations, not an unconditional guarantee of identical behavior for every unusual extension or data representation.

Primary sources

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/FEATURES.md](https://github.com/RDFLib/pySHACL/blob/v0.40.2/FEATURES.md?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/shape.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/shape.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/graph_abstraction.py](https://github.com/RDFLib/pySHACL/blob/v0.40.2/pyshacl/graph_abstraction.py?utm_source=chatgpt.com)

[https://github.com/RDFLib/pySHACL/releases/tag/v0.40.2](https://github.com/RDFLib/pySHACL/releases/tag/v0.40.2?utm_source=chatgpt.com)