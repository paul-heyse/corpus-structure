# Vocabulary sources, bindings and ontology lifecycle

**Source-inspected discovery, 2026-11-10; benefits Proposed.** [Baseline](../briefing.md).
References: [OAK](../../../../libraries/data_model/oaklib.md),
[Valuesets](../../../../libraries/data_model/valuesets.md),
[LinkML](../../../../libraries/data_model/linkml.md) and the dated
[OAK/Term Validator account](../../oaklib/README.md).

## Existing use and actual admission boundary

[ontology.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/ontology.py)
expands enums with local OAK/Term Validator leaves, then applies explicit composition and final
subtraction. `resolve_vocabularies_from_bytes` binds supplied source bytes; released memberships
are archived. This is adopted machinery, although a scoped search of production/domain YAML
found no `reachable_from`, `binds_value_of`, `represents_relationship`, `relational_role` or
Valuesets references. The Valuesets prediction-outcome import in `test_prepare.py` exercises
capability rather than establishing ordinary production vocabulary use.

`validate_bindings` is defined in production but the inspected references are tests. That
does not mean the ontology integration or graph projection is unused: `QualifiedGraphProjection`
and released graph policies have real production consumers.
[prepare.py](../../../../../python/corpus-structure/src/corpus_structure/semantic/prepare.py)
currently excludes slot bindings/units/relational roles, class `represents_relationship` and
permissible-value inheritance from its allowed profile. Richer sources are therefore not
automatically admitted simply because the libraries support them.

<a id="ddm-05"></a>

## DDM-05 — Extend pinned membership into useful semantic bindings

**Status:** existing expansion substrate with dormant/conditional richer binding consumers.
LinkML dynamic enums and bindings, Valuesets source schemas and OAK term access can connect
allowed identifiers with label/meaning consistency, hierarchy, mappings and explicit unchecked
checks. Valuesets `RichEnum` metadata and meaning lookups are useful projections, while authored
LinkML sources retain more hierarchy and mapping semantics than generated Python enums.

**Broader use and value:** identify a current domain vocabulary that should use an external
meaning rather than a locally invented code list. Prepare its selected definition and source
snapshot once, preserve member identifiers, meanings, hierarchy/mapping kinds and provenance,
and feed extraction candidates, validation and operator explanations from that same product.
Bindings could then validate a nested term-valued field where production has a real use.

**Defeater and retain case:** many Valuesets vocabularies are draft and may not match local
absence, confidence, evidence or maturity meanings. A shared label is insufficient. Broader
support needs explicit compiler/profile decisions and faithful projections; ontology existence
and membership cannot establish factual support for a source interpretation. Retain local
vocabularies where their intended meanings differ.

Installed Term Validator0.4.5 still makes final subtraction a repository responsibility:
expansion applies minus before inherited/static members, and lazy membership is not a universal
implementation of composed include/minus semantics. Its binding plugin walks contextual induced
slots but does not bypass these membership limits. The existing whole-union subtraction must
survive any proposed broader integration.

**Next question:** which concrete field would gain meaningful external-term constraints, and
what complete metadata must its release product retain? Select one source vocabulary, examine
its admitted feature subset and compare source semantics with the actual local concept before
proposing a production import or binding.

<a id="ddm-06"></a>

## DDM-06 — Use ontology structure for candidates and controlled change

**Status:** unused/conditional capability families in inspected application integration.
OAK provides field-aware search, lexical matching/grounding, typed mappings, graph traversal,
semantic similarity, usages and KGCL change analysis. Adapter capabilities differ; a common
interface does not promise every backend implements the same semantics.

**Broader use and value:** lexical/ontology neighborhoods could nominate candidate entities
or terminology for the current extraction/resolution workflow, with exact source spans and
mapping predicates preserved. Separately, usages, obsoletion links and ontology diffs could
explain how a proposed pinned-vocabulary update changes released membership or mappings.
The latter can make release review more useful without adding automatic synchronization.

**Defeater and retain case:** no selected source ontology currently establishes these consumers.
Exact/close/broad/narrow mappings must remain distinct from canonical identity. Similarity
depends on predicates and information-content populations; ontology reachability is not general
entailment. A KGCL patch is not authority to mutate archived releases. Local adapters and explicit
snapshots are preferable to introducing ambient services solely to demonstrate an API.

**Next question:** does a named current source/domain task benefit more from ontology-grounded
candidate formation than from its existing exact/lexical/contextual retrieval? For lifecycle
analysis, which real vocabulary update requires explaining impact beyond the existing model-change
report? These are separate consumer questions and need not result in the same integration.

<a id="ddm-11"></a>

## DDM-11 — Reuse ontology preparation within one release operation

**Status:** concrete candidate underuse of the existing local adapter substrate.
`expand_enum` creates adapters per source within each enum call and plugins per reachable leaf;
`resolve_vocabularies` expands enums independently. `_meaning_checks` creates adapters and
enumerates entities to determine prefix ownership per enum. This is source-visible repeated
preparation, not a measured performance defect; ordinary production external-ontology use is
currently limited by the consumer evidence described above.

**Mechanism and broader use:** OAK's Pronto implementation accepts `wrapped_ontology`, bypassing
parser construction, and honors explicit import-depth controls. One operation-scoped preparation
could supply labels, prefix ownership and traversal to several enums from the same supplied bytes.
It need not become a durable cache or require network lookup.

**Defeater and retain case:** installed Term Validator's inspected adapter access path owns a
private `_adapter_cache`; no public injection route was established. Adapter mutation or subtly
different leaf semantics can defeat reuse. The existing temporary-file bridge remains reasonable
if removing it requires private coupling or another membership interpreter.

**Next question:** when a real multi-enum source is selected, can supported OAK operations share
one prepared adapter while leaving only the necessary supported leaf work to Term Validator?
Expected value is less repeated parsing and scanning, with no quantitative claim.

<a id="ddm-12"></a>

## DDM-12 — Enrich measurement identity when a comparison requires it

**Status:** conditional broader model/vocabulary use with a concrete existing refusal boundary.
`model/semantic/core.yaml` declares QuantityValue with decimal value, textual unit and source
basis. The statistics pack separately retains referent, property, uncertainty, unit and normalized
value. `methods/structural_products.py` withholds stronger threshold consequences when units,
quantity or basis are unknown or unequal. These are meaningful current safeguards.

**Mechanism and broader use:** LinkML UnitOfMeasure/quantity-kind metadata and selected Valuesets
unit/quantity-kind sources could bind recognized identifiers while preserving original spelling
and basis. A separately qualified conversion engine could serve an explicitly requested
cross-unit operation. Units and quantity kinds should remain distinct from representation and
contextual reference basis.

**Defeater and retain case:** native unit metadata is outside the admitted release profile;
draft mappings and shared labels do not establish dimensional or conversion equivalence.
Affine/context-dependent conversions, unknown source units and missing basis can still require
refusal. Neither library supplies the complete conversion operation merely through annotations.

**Next question:** which currently withheld source-grounded comparison would become valid through
recognized unit identity or an explicit conversion? Define that exact operation before adopting
measurement metadata or adding a dependency.

## Additional territory retained

OAK federation, associations/enrichment, validation, subset gap filling, conversion, visualization,
taxon constraints and native OWL access remain conditional on a relevant domain/adapter.
Semantic-SQL's documented SQLite-oriented route is not a native implementation over the
project's PostgreSQL instance model. Valuesets numerical classification can yield multiple
matches; it does not supply unit conversion or exclusive classification policy.
Quantity kinds/units, permissible-value hierarchies and external-source reconciliation deserve
source-level study if a scientific measurement consumer emerges.

Valuesets generators, reports and synchronization utilities need distribution/API verification;
repository scripts are not necessarily installed public tools. Aggregate enum collisions,
dynamic-generation omissions and lossy metadata projections argue for selective source imports.
The existing in-memory OAK adapter research also leaves private Term Validator adapter-cache
coupling unresolved. That is a focused integration question rather than justification for a new
generic ontology service. Mapping metadata, confidence heuristics and source truth remain separate.
