# Unified-model semantics: focused applicability

**Interface-checked and source-inspected, 2026-11-01; applications Proposed.** Source
`1cb8e620`; current diagnostic publication `cc2998d9` (UM-20261101-r2). Core 3.3,
heuristics 1.0, code-intelligence 1.4; framework 0.2 and existing LOP-X004/X006/X009.
This account separates reusable capabilities from contextual fit. Comparative selection belongs
to the [principal review](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md).

## Evidence and versions

All six guides and their November 1 addenda were surveyed. Current declared/installed versions:
LinkML/runtime 1.12.1, RDFLib 7.6.0, pySHACL 0.40.1, Valuesets 0.4.2; existing Term Validator
0.4.5 and OAK 0.7.4 participate in vocabulary resolution. Map 0.5.4 and Datalog 0.2.0 are
unadopted research candidates. Map 0.6.0-rc1, pySHACL 0.40.2 and experimental Datalog branches
remain separate realizations.

Context7 first: `/websites/linkml_io_linkml`, `/rdflib/rdflib`, `/rdflib/pyshacl`,
`/linkml/valuesets`; Map/Datalog resolution returned general LinkML material, followed by tagged
source. Current-main documentation was checked against installed sources for consequential
current behavior. No dependency installation, runtime compatibility probe, performance measurement
or product qualification was performed. Advanced families not named below retain their guide's
evidence strength; the coverage table in the principal review explains relevance.

## Reusable capability types

### linkml/effective-definition-projection

`SchemaView.class_induced_slots`, `induced_slot`, controlled `importmap`, reusable slots/mixins,
`unique_keys`, conditional `rules`, `value_presence` and generator extensions support shared
definitions with explicit target coverage. `represents_relationship`/`relational_role` expose
attributed edge roles; inverse/transitive/disjointness declarations carry semantics beyond shape.
These metadata do not execute graph inference or transactional transitions automatically.

Residual obligations include closed acquisition, duplicate handling, conjunctive type bounds,
input immutability, and feature-specific lowering. In 1.12.1 SHACL rule generation recognizes
selected patterns and can skip others; it is not equivalent to all LinkML conditional semantics.
Rust crate/PyO3 generation supplies structural containers/traits, not current numeric,
dynamic-enum and domain-rule enforcement. See [LinkML](../../libraries/data_model/linkml.md),
especially relationship, presence, runtime-resolution and generator sections.

### rdflib/qualified-graph-projection

`Graph`, `Dataset`, relationship resources, paths, canonical comparison and serialization support
semantic projections. `build_shacl_path`/`parse_shacl_path` can share supported path definitions.
Triple sets discard duplicate assertion identity and ordering unless modeled explicitly. Named
graphs alone establish neither provenance nor transaction isolation. Independent blank nodes must
be scoped correctly when combining graphs; see [merge semantics](https://github.com/rdflib/rdflib/blob/main/docs/merging.md).
SPARQL and SHACL path grammars differ. Store/backend changes require their own lifetime and
isolation contract. See [RDFLib](../../libraries/data_model/rdflib.md).

### pyshacl/scoped-conformance-diagnostics

`validate`, SHACL Core paths/logical/qualified-cardinality constraints, parameterized SPARQL
components, target/focus selection and RDF reports can discharge scoped graph conformance.
`shacl_rules` is a separate additive derivation mechanism. Focus selection does not compute a
complete incremental impact closure; Dataset validation uses a union. Rules provide neither
general truth maintenance nor concurrent transition authority. Result annotations and
`sh:entailment` are unimplemented. The guide's 0.40.2 corrections are candidate-version facts,
not guarantees of installed 0.40.1. See [pySHACL](../../libraries/data_model/pyshacl.md).

### valuesets/semantic-vocabulary-source

LinkML vocabulary schemas, permissible-value metadata/hierarchies, dynamic expressions,
SSSOM mappings and `RichEnum.get_metadata/get_meaning/from_meaning` support reusable vocabulary
sources and projections. Generated Python enums retain only part of the meaning; installed
modular generation skips dynamic `reachable_from` enums. `from_meaning` is lookup, not semantic
equivalence. Numeric classification may return multiple matches and provides neither unit
conversion nor exclusivity policy. See [Valuesets](../../libraries/data_model/valuesets.md).

### linkml-map/explicit-context-translation

`TransformationSpecification`, class/slot/enum derivations, `ObjectTransformer.map_object` /
`transform_object`, `SchemaMapper`, sentinel normalization, units and heterogeneous source
derivations can express pure structural translations into typed targets.

The stable [join engine](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/transformer/join_engine.py)
reduces lookup matches to one row per key without a general deterministic multi-match contract.
The [SQL compiler](https://github.com/linkml/linkml-map/blob/v0.5.4/src/linkml_map/compiler/sql_compiler.py)
does not implement full interpreter expression/constant/unit parity. Columnar writing stages
JSONL and infers types through DuckDB; it is not direct schema-preserving Arrow transformation.
Version 0.6 identifier/coercion/decimal changes require separate qualification. See
[Map](../../libraries/data_model/linkml-map.md).

### linkml-datalog/schema-derived-recursive-relations

`DatalogGenerator.serialize`, `TupleDumper.dump`, `DatalogEngine.run`, `inferred_slot_values`
and custom Soufflé output relations offer schema-derived recursive computation. The tagged
[generator](https://github.com/linkml/linkml-datalog/blob/bf1e265/linkml_datalog/generators/dataloggen.py)
and [engine](https://github.com/linkml/linkml-datalog/blob/bf1e265/linkml_datalog/engines/datalog_engine.py)
show material limits: class-specific `_asserted` predicates can consume derived relations;
de-reification can derive triples; exact typed numeric reconstruction and source-proof identity
are not supplied. Materialization is incomplete and absent from the ordinary CLI execution path.
Modern Python/LinkML/Soufflé compatibility is untested here. Unmerged Snakelog work is not
released capability. See [Datalog](../../libraries/data_model/linkml-datalog.md).

## Contextual applicability

Source paths below are relative to `python/corpus-structure/src/corpus_structure/`.

| Responsibility | Current realization and fit | Residual work / condition |
|---|---|---|
| Effective definitions | `semantic/prepare.py:248–334` closes import resolution, rejects duplicates/prefix conflicts, materializes source URIs and protects downstream generators. Existing LinkML substrate fits. | Preserve these safeguards; native materialization has different precedence/mutation/bound semantics. |
| Qualified relationships | `semantic/ontology.py:496–720` binds exact release/contract, closure, snapshot, explicit nulls, occurrence positions and exact literals. RDFLib is already a faithful selected realization. | Richer standard role metadata fits conditionally when all relevant lowerings preserve the same relation identity and universe. |
| Graph validation | `ontology.py:722–770` explicitly disables inference/advanced/imports/mutation; separates invalid shape, execution failure and nonconformance. | Reusable SPARQL constraint components fit repeated graph invariants; graph constraints cannot replace native all-writer/concurrency enforcement. |
| Vocabulary membership | `ontology.py:290–380` composes Term Validator leaves under explicit local subtraction semantics; supplied ontology bytes are pinned. Valuesets fits as a vocabulary source. | Preserve full metadata/snapshot lineage; do not replace with lossy RichEnum imports or equate mapping with identity. |
| Comparison grouping | `domain_operations.py:2589–2603` interprets qualifier lists separately from typed key roles. DA-001 remains a narrowed authority question. | Compile a distinct named comparison projection and validate its references; coarser grouping can be correct. |
| Source/target translations | Map has a conceptual match to pure adapters. No complete current translation replacement is established by this assessment. | Name the source/target, cardinality, presence, precision, context and lineage before any adoption; current typed batch/publication paths exceed stable Map's contract. |
| Qualified inference | `semantic/inference.py:59–276` uses repeatable snapshot, canonical qualifier contexts, common fixed point, finite direct witnesses and revision-fenced publication. | Datalog replacement fit remains unestablished; output closure alone would not preserve the complete current operation. |

No new diagnostic defect was established in this semantic-library slice. A suspected mismatch
between permissible-value keys and `text` was rejected after installed-source inspection:
LinkML normalization requires equality before expansion. Feature refusal alone is not a defect.
