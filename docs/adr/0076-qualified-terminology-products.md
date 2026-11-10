---
id: ADR-0076
title: Retain qualified terminology projections and source metadata with each release
status: accepted
date: 2026-11-10
supersedes: []
superseded-by: null
design: [§B5]
evidence: Proposed
---

## Context

DMC-06 needs two useful statistics vocabulary fields and reproducible descriptive metadata.
The existing member wire retains value/meaning/label but no definitions, qualified mappings
or enum declaration locators. STATO supplies distribution families and mathematical distribution
attributes with meanings distinct from sample estimators and local measurement roles.

## Options

1. Read live ontology metadata during inspection. This changes historical interpretation and
requires external availability for an ordinary released read.
2. Import the complete ontology as executable local declarations. Its OWL semantics exceed the
finite supported profile and would conflate descriptive metadata with admitted enforcement.
3. Retain original source, a qualified OBO membership projection and a versioned descriptive
product under existing release custody. This needs explicit acquisition and fidelity coverage,
but ordinary readers remain bounded and independent of ontology availability.

## Decision

Select option3. Pin STATO v2026-04-20 at commit a5910e6115217a88ee86e2666e12983ef2ef2a42.
Capture original OWL and deterministic Pronto2.7.4 OBO conversion with hashes, options, warnings
and supported coverage. Compare selected labels/definitions/named parents against original RDF;
retain original annotation/mapping predicates instead of claiming OWL equivalence.

The optional independent fields distribution_family and distribution_attribute use explicit
permissible values. They describe attributed source interpretations, not global identity or
selected knowledge. Actual bound filtering and grounding remain DMC-07/08. Mathematical
expectation/variance/standard deviation remain distinct from sample statistics and record roles.

One operation-owned OAK adapter per supplied source serves application metadata and prefix
ownership; supported Term Validator file bridges and complete union/subtraction remain intact.
Emit vocabulary metadata v1 and inspection locators v2, with old detail availability explicit.
Semantic compiler21 versions the new products while archive3, boundary12 and execution28 remain.
Both native compiler guards and the descriptor move together through frozen migration.

## Consequences

Archived metadata opens without today's source or endpoint, while original bytes and conversion
limits remain inspectable. The snapshot copy purchases reproducibility and independent comparison.
Metadata grants no new native inference, unit conversion, mapping equivalence or publication
capability. Revisit source selection when new required terms or predicates exceed this qualified
projection. The DMC coordinator owns implementation and scoped acceptance; this accepted decision
does not establish delivery or close later terminology/measurement consumer obligations.

## Amendments

2026-11-10 factual integration note: Pronto's raw OBO serialization varies in clause/frame order
across processes. The acquisition profile uses pinned Fastobo0.14.2 to canonicalize its AST
ordering, checks semantic clause sets and selected original RDF facts, and retains the resulting
byte digest. This does not strengthen the declared OWL fidelity or alter membership authority.
