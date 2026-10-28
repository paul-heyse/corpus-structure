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