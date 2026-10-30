---
id: ADR-0036
title: Preserve source custody through representation-qualified parsing products
status: accepted
date: 2026-10-30
supersedes: []
superseded-by: null
design: [§B4, §B5]
evidence: Proposed
revisit: The qualified HTML source-location route cannot preserve the required original partition or a consumer requires unavailable exact repair provenance.
---

## Context

The operator confirmed complete original and canonical decomposition, PostgreSQL bytea custody,
retained html5lib HTML5 semantics and versioned M09/M11/M13 redesign with complete consumer
migration on 2026-10-30. The [parsing review O01/O02/O03/O06](../functional_reviews/parsing-pipeline_2026-10-30.md)
and its [target model](../functional_reviews/parsing-pipeline_2026-10-30_target-model.md)
identify missing source coordinates, occurrence relationships and transformation custody.
Canonical text and a repaired DOM cannot recover the original spelling or excluded material.

ADR-0024 is the current successor for rendition identity and semantic authority; ADR-0035 is
the current successor for interpretation and demand/preparation. Their decisions survive. This
record adds the source-product contracts and changes D1's canonical-only offset wording and
D4's method target promises; it does not supersede those records or reinterpret old evidence.
The [PP-00 owner](../plans/parsing-pipeline/model-contracts-and-storage.md#PP-00) and
[coordinator](../plans/parsing-pipeline_2026-10-30.md) own implementation and finding disposition.

## Options

1. Retain canonical spans, diagnostics and source files alone. This preserves today's readers
   with least change, but cannot inspect discarded syntax or distinguish exact original mapping
   from repaired output. It does not deliver the selected source-inspection capability.
2. Make a universal persisted AST/workflow service the new authority. It offers one generic
   interface but duplicates model, execution and lifecycle owners; translating every native
   structure adds work and loses useful library operations. Reject this additional machinery.
3. Extend existing model contracts and protected publication with qualified representations,
   compact partitions and identified relationships. Selected. Pure library adapters can be
   tested without database access; native custody/integrity remains enforced at publication.
   Retaining original bytes and a complementary lexical pass adds storage and parsing work,
   justified by fidelity unavailable from DOM serialization. Compact range sequences avoid
   per-character rows; explicit edges serve the joins that require them. Physical layout and
   exact HTML repair mapping remain PP-02/PP-04 responsibilities, with no performance claim.

## Decision

**Accepted target; Proposed implementation (2026-10-30).**

1. D1 owns representation-qualified half-open ranges: representation identity, coordinate unit
   and bounds. Original bytes, decoded source, canonical Unicode code points and expanded TeX
   are distinct spaces. Existing evidence `Span` remains canonical and retains its identities,
   exact-quote checks and citation-frame meaning. Added source ranges never masquerade as spans.
2. D3 owns immutable original-byte custody in PostgreSQL `bytea`, stored once per source content
   identity and linked separately to document/acquisition identity. Retain bytes even on decode
   failure. Files may supply acquisition or derived exports; no external file is the authority
   needed to recover the retained original. Instance publication uses existing protected admission,
   forward migrations and immutable products; no new mutable provenance store is introduced.
3. D1 distinguishes source artifact, representation, complete lexical partition, structural
   occurrence/relationship, transformation mapping, interpretation/assessment and producing
   build/product identities. Raw and canonical partitions cover their declared representation
   exactly once, including unknown material, whitespace and synthetic canonical separators.
   Successful decoding also has its own complete partition; failed decoding retains explicit
   undecoded coverage. Complete partition, structural recognition and complete provenance are
   independent claims. Composite spans can overlap above the disjoint partition.
4. A mapping names ordered source/target extent sets, operation/reason and fidelity/coverage;
   many-to-many, reordered, excluded, synthetic, normalized and derived contributions remain
   explicit. Macro invocation, arguments, definitions, defaults and fallback authorities retain
   artifact/dependency custody. Interpretation and simplified mathematical objects do not collapse
   repeated source occurrences. A coefficient introduced by simplification is derived material.
5. Preserve the full rendition-content identity from ADR-0024: canonical text, complete ordered
   segment tree including status/reason and attributes, sentences and effective macro table.
   Source mappings, diagnostics and implementation provenance belong to build-bound products;
   different products/builds may share a content-identical rendition. Changed canonical content
   or segmentation creates new rendition/anchor identities. Pinned producing-build selection
   follows existing reuse resolution; ambiguous multiple candidates refuse, never select latest.
6. D2 derives bounded runtime, relational and validation contracts from trusted LinkML and
   execution definitions. D4 names discrete decomposition, HTML recognition, canonical projection,
   text preparation, mathematical interpretation/assessment and source publication operations.
   Qualified library algorithms remain ordinary code; finite release-scoped support is admitted
   independently. Unsupported required semantics refuse before effects. This is no general
   workflow interpreter, universal tree schema, task per token or transaction per stage.
7. Version M09/M11/M13 contracts together with affected producers and consumers before selecting
   demand-driven results. A decomposition-only or structure-only output cannot satisfy an older
   interpreted-result promise. D5 binding requires declared occurrences, scope and interpretation
   dependencies without reading downstream resolution circularly. D6 separates durable task
   lifecycle from grammatical outcome and coverage; timeout remains attempt-dependent. Local
   computation need not acquire a durable task merely because it emits a distinct product.
8. Retain html5lib's HTML5 tree construction through lxml. Original lexical custody complements
   repaired structure. Exact provenance of duplicate attributes, encoding changes, implied nodes
   and reordered text remains under investigation in PP-02; line positions, DOM paths and
   reserialization are not exact extents. Publish unavailable/partial mapping coverage explicitly
   or refuse a consumer requiring exact mapping. The complete partition obligation is not waived.
9. D7/D8 retain independent reference preparation, evidence grading and pinned historical reads.
   Migrate source profiles, ingestion/sentences, mathematical methods, binding, quote placement,
   source frames/packets, observations, measurements, query/export and evaluator boundaries
   wherever contracts change. Source interpretation never consumes reference decisions. This
   record authorizes no grading-policy, evidence-strength or ontology-inference change.

## Consequences

Source inspection gains honest custody and occurrence identity without changing canonical
evidence. Preparation and native publication keep their existing owners. More retained products,
forward native constraints and coordinated consumer migration are necessary; declarations alone
do not enforce complete partitions or cross-record integrity. PP-01/PP-04 own those mechanisms,
PP-02/PP-03 own source fidelity and PP-06/PP-10 own method/consumer adoption. PP-09 owns coherent
publication/replay. No runtime, native deployment, full provenance or qualification is claimed
by this documentation decision. Remaining feasibility or rule impacts return to the coordinator;
they cannot be resolved by relabeling partial coverage or silently narrowing the accepted target.
