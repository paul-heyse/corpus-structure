# Qualified graph contracts, navigation and conformance

**Source-inspected discovery, 2026-11-10; benefits Proposed.** [Baseline](../briefing.md).
References: [RDFLib](../../../../libraries/data_model/rdflib.md),
[pySHACL](../../../../libraries/data_model/pyshacl.md) and the dated
[unified semantics assessment](../../unified-model-semantics_2026-11-01.md).

## Preserve the existing graph model

[ontology.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/ontology.py)
`QualifiedGraphProjection` binds release/realization/revision, typed-reference closure, snapshot
lifetime, exact literals, explicit nulls, positions and assertion multiplicity. Its production
consumers include the identity-exclusion graph in
[query.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/query.py).
The simpler `qualified_assertion_graph` helper's test-only callers do not describe this full adoption.

`validate_graph` explicitly selects inference none, advanced false, imports false and no input
mutation. It distinguishes shape-loading errors, engine failures and nonconformance.
`_qualified_shape_triples` already prepares immutable shape triples once and supplies two concrete
SPARQL checks: endpoint distinctness and collection-position uniqueness. Custom SPARQL conformance
is therefore partly adopted; enabling advanced rules is a different question.

<a id="ddm-07"></a>

## DDM-07 — Reuse supported paths and recurring constraints

**Status:** conditional unused path APIs and possible broader use of adopted SPARQL constraints.
A scoped product/test search found no use of RDFLib `parse_shacl_path`, `build_shacl_path` or
native `rdflib.paths` composition. Existing direct-predicate Turtle remains simple and useful.

**Mechanism and broader use:** where a real modeled relationship needs a sequence, inverse,
alternative or repetition, RDFLib Path plus SHACL path translation can serve traversal, shape
authoring and diagnostic presentation. Repeated invariants could use pySHACL's parameterized
constraint components rather than embedding similar queries in each shape. Keep the relationship
or invariant's authoritative definition with its model owner.

**Installed-source checks, 2026-11-10:** RDFLib7.6.0 `extras/shacl.py` parses/builds those
recognized forms. `_build_path_component` can return an unencoded blank node for an unsupported
Path subclass; it does not universally reject unsupported paths. Admit a supported grammar
explicitly, excluding SPARQL negated paths. PySHACL0.40.1 `shape.py` discovers custom constraints
outside its advanced-feature branch; SPARQL constraint components select specialized SELECT or
general ASK validators. `sparql_query_helper.py` substitutes `$PATH` but rejects MINUS, VALUES,
SERVICE and `$shapesGraph` in the inspected restrictions. These are implementation observations,
not proof of arbitrary component compatibility.

**Value:** avoid separately maintaining path walkers/RDF-list encoders or repeated invariant
queries while using native targeting and reporting. This could complement DDM-02's richer
relationship declarations without requiring a generic ontology runtime.

**Defeater and retain case:** no repeated equivalent constraint or complex path consumer has
yet been established. Extracting two unique queries into a configurable framework may add burden.
Graph connectivity does not encode qualified occurrence identity or establish source truth.
Dataset union validation and selective focus do not isolate provenance or compute affected-node
closure; CBD is not the application's required reference closure.

**Next question:** which actual diagnostic or relationship requires composite navigation, or
which invariant recurs across admitted/generated shapes with only parameter differences?
Compare that complete case with current direct constraints before adding a reusable component.

<a id="ddm-08"></a>

## DDM-08 — Make retained graph diagnostics navigable when useful

**Status:** underuse candidate in a concrete existing reporting path.
`GraphDiagnostic` extracts focus, path, source shape, component, severity and joined messages;
paths are stringified. `GraphValidation.report` already retains the canonical full RDF report.
[operation_reporting.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/operation_reporting.py)
hashes/references that report while exposing a narrower located JSON observation.

**Mechanism and broader use:** query the retained report for offending `sh:value`, declared
`sh:sourceConstraint`, nested detail and structural paths, then expose a bounded view for the
review/repair consumer that needs it. This could locate a particular domain constraint or render
a composite path without copying the complete graph into every diagnostic record.

**Installed-source check:** pySHACL's `constraint_component.py` emits those report fields;
`validator.py` clones referenced blank-node structures into the result graph. A blank-node path
identifier alone is consequently not the complete path meaning. Message construction sometimes
creates plain literals, so source language tags are not uniformly guaranteed to survive.

**Defeater and retain case:** the current tuple may be sufficient for refusal and ordinary
overview reporting. Widening every record would duplicate already retained data. Original report
bytes and location identity should remain independently accessible.

**Next question:** which correction workflow needs the value, semantic path or particular
constraint reference? Define its location contract and on-demand report view before adding fields.

## Broader capabilities with explicit conditions

RDFLib prepared SPARQL queries, `initBindings`, CONSTRUCT, graph algebra, native paths, vocabulary
namespaces, semantic graph comparison and collections offer useful established mechanisms when
current consumers repeat those responsibilities. A comparison for consequential blank-node
equivalence should investigate `rdflib.compare`, not rely on Graph.isomorphic's approximate route.
Canonical semantic comparison and the current LinkML RDFC-1.0 identity bytes serve distinct purposes.

SHACL Core logical/qualified-cardinality constraints and Meta-SHACL can deepen conformance when
needed. Focus/shape selection is useful only with an independently sufficient validation universe.
SHACL functions/rules, OWL-RL and SPARQL CONSTRUCT are optional separate derivation directions:
name asserted/derived distinctions, eligible premises, recursion and retraction semantics before
comparing them with existing native inference. Rule iteration is not general deletion-aware truth
maintenance. Result annotations and `sh:entailment` remain unsupported in the documented profile.

RDF4J/GraphDB/Oxigraph backends, RDF Patch, JSON-LD/HTML, NetworkX, Describer/infixowl and server
interfaces remain conditional territory. A store flag or patch transaction marker does not supply
the project's transaction/custody contract. This discovery establishes no reason to replace
PostgreSQL authority, enable remote interpretation or change the selected conformance profile.
