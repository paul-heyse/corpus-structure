---
id: ADR-0024
title: Semantic releases govern interpretation and preserve independent assertion occurrences
status: accepted
date: 2026-10-29
supersedes: [ADR-0013, ADR-0019, ADR-0020, ADR-0021, ADR-0022, ADR-0023]
superseded-by: null
design: [§B1, §B2, §B4, §B5]
evidence: Proposed
revisit: A required semantic construct cannot be faithfully prepared or transactionally enforced, or staged compilation introduces a second writable meaning for the same admitted release.
---

## Context

The operator accepted functional-review RC01–RC04 on 2026-10-29 and authorized SP-00/SP-01
execution. The [review](../functional_reviews/semantic-postgresql-model_2026-10-29.md) and
[target](../functional_reviews/semantic-postgresql-model_2026-10-29_target-model.md) require a
semantic PostgreSQL model governed by LinkML and formal ontology. Existing generation already
uses LinkML, but couples installed revision, shapes and physical metadata. Replacing that
selection now would execute downstream packages before their consumers are ready.

## Options

1. Extend the installed core and regenerate every surface together. Simple initially, but
   deploys physical changes and breaks registered versions before SP-02 and consumer migration.
2. Introduce a separate editable ontology/registry around unchanged consumers. Rejected:
   declarations would still not govern behavior, and meaning could diverge.
3. Prepare explicit immutable semantic releases, then deploy and migrate their realizations
   through the scheduled packages. Selected. A temporary explicit target root is staging, not
   a legacy compatibility API or a second authority for an admitted release.

## Decision

Local LinkML modules own application classes, properties, qualified assertions, recursive typed
values, identities and operation profiles. External pinned ontologies own referenced terms;
releases own their selected mappings and executable scope. SQLAlchemy MetaData is the derived
relational schema model and Core is its execution composition route, not an independent semantic
source. PostgreSQL 18 remains the transactional instance authority. Arrow/DuckDB remain derived
interchange/local execution; files never become authoritative instance stores.

Preparation consumes explicit authored bytes, resolved imports/ontology artifacts and a supported
profile. It produces immutable definitions, boundary adapters/artifacts, logical registry rows,
query descriptors and requirements for downstream enforcement. No database, active project pointer,
installed model default or implicit ontology network call participates. Persistence/activation is
SP-02; protected transactional publication is SP-03. Preparation success is not authorization to
publish facts. Unsupported required semantics refuse; imported descriptive axioms outside the
executable profile remain explicitly unexecuted.

Source observations and qualifications stay distinct from accepted interpretation. Assertion
occurrences have source/publication-and-item identity, independent of semantic fact identity.
Retry preserves one occurrence; repeated occurrences, independent sources and disagreements
survive fusion. Fact identity includes meaning-bearing qualification, not evidence multiplicity or
confidence. Range/membership and cardinality constraints declare their governing scope; cardinality
one on selected values cannot prohibit recording conflicting sources.

Use named ontology classes/properties, declared hierarchy, explicit typed ranges, identities,
scoped constraints and pinned memberships initially. Qualified inverse/symmetric/positive-transitive
rules require explicit eligible premises; negatives do not participate in ordinary transitivity.
RDF source assertions remain qualified resources rather than unconditional triples. SHACL is graph
conformance, not general OWL entailment or database race protection. Required database integrity
needs native/SQL enforcement; no caller-supplied validation flag substitutes for it.

### Clauses carried forward and deliberate replacements

- ADR-0013: preserve n-ary relationships, conditions, symbol bindings, typed values and explicit
  qualifications. Replace one identity serving both occurrence and fact/group with the two
  identities above; do not flatten provenance into a deduplicated claim.
- ADR-0019: preserve source-content/rendition identity, source locators, exact evidence and authored
  citation frames. Replace frozen downstream statement/entity/claim recipes with release-scoped
  declarations. Acquisition success never establishes source meaning or accepted knowledge.
- ADR-0020: preserve one authoring authority, generated mechanical projections, deterministic
  compilers and ordinary domain functions. Replace installed-only interpretation and mandatory
  regeneration of all surfaces with explicit preparation and staged selection.
- ADR-0021: preserve PostgreSQL authority, typed Arrow relations, scoped DuckDB execution and exact
  qualified boundaries. Future supported relational inference may use SQL/Core; this record does
  not select or deploy a new engine in SP-01. Keep one psycopg pool lent to SQLAlchemy NullPool.
- ADR-0022: preserve immutable definitions, complete dependencies and explicit physical revisions.
  Replace mandatory historical upcaster/compatibility routes with clean regeneration. Future
  releases still cannot silently change the meaning of bound operations.
- ADR-0023: preserve declared identity roles, canonical forms and case semantics. Replace the
  frozen key scheme and installed qualifier dependencies for the new target. No pre-pivot key
  compatibility is required.
- ADR-0014 remains in force: methods write observations; consolidation owns knowledge selection.
  Database publication enforces that operation's contract and does not independently choose truth.
  Finished realizations and pinned queries remain immutable; no mutable global knowledge base is
  introduced.

## Consequences and adoption

SP-01 is a prepared foundation only. The selected legacy runtime, generated database metadata and
registered-version dispatch stay operational until their later packages replace them. Existing
architecture sections label that selection explicitly; it is not a promise of legacy API/data
compatibility. No dual writes or upcasters are added. Old plans and evidence remain unchanged.

Acquire once and prepare from complete inputs; cache adapters under their binding. This reduces
repeated interpretation but introduces retained artifact and dependency responsibility. Graph
checks/global constraints may require broad context; narrow returned output alone does not bound
execution. No performance/capacity claim is established.

This accepted target follows the operator's confirmed decisions; implementation and testing are
reported separately by the owning pivot coordinator. SP-00's independent focused target assessment
reconciles these responsibilities without restarting a broad diagnostic inquiry.
