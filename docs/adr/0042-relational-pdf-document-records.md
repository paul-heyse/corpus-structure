---
id: ADR-0042
title: Realize PDF documents as lossless records with versioned streaming identity
status: superseded
date: 2026-11-01
supersedes: [ADR-0041]
superseded-by: ADR-0045
design: [§B4]
evidence: Proposed
revisit: A supported native field or required independent correspondence cannot be represented without full-document materialization, or a consumer requires an unimplemented stream digest algorithm.
---

## Context

The actual1589-page PDF produced a558190320-byte integrated envelope, including270447 relations
occupying355630981 canonical bytes. Its aggregate relation-array cast exceeded PostgreSQL's
JSONB limit.0060's JSON-text decomposition avoids that cast;0061's shared child-edge join is
committed but undeployed. Neither removes mandatory whole native content/envelope materialization
or the individual-field size boundary. The [streaming review](../functional_reviews/pdf-streaming-and-storage_2026-11-01.md)
and [target](../functional_reviews/pdf-streaming-and-storage_2026-11-01_target-model.md) support
the successor design. RC08/09 were explicitly accepted2026-11-01; PDF-17–19 execute its foundation.

## Options

1. Retain0060/0061 as the final physical design: simplest compatible repair, but still carries
   whole-book objects and canonical bytes through preparation and publication.
2. Store independent page/section documents: convenient batches, but changes native reference,
   cross-page hierarchy/reading-order and evidence meanings. Rejected as canonical structure.
3. Lossless model-governed records, ordered membership and artifact parts, with typed batch
   transport and immutable document finalization. Selected: one logical document with selective
   access and durable progress, at the cost of an explicit native lowering/identity protocol.
4. External object store/Flight/job service or a new graph engine: not required by this local
   workload. Optional immutable IPC/Parquet spools have consumers without a new editable authority.

## Decision

Docling owns its pinned native content schema. The semantic release owns application relations,
field mappings, operations, states and invariants. PostgreSQL retains transactional custody and
independent native enforcement. One logical integrated document plus mandatory companion semantics
is realized as fixed typed record families, ordered memberships, qualified references/native
addresses and bounded artifact parts. Repeating native collections are rows; bounded native
extension detail may remain JSON. Unsupported schema changes refuse rather than omit content.
Physical batches/parts are not semantic section chunks or new originals.

The native mapping is total for the supported schema, including presence/default/null/order,
rich cells, images, references, provenance precision and unselected content. Shared immutable
policy/comparison context may be factored without merging independent occurrence decisions.
Normalization precedes identity under an explicit producer contract; reads do not repair data.

Logical product identity, original/raw exact-byte identity and export serialization identity
are distinct versioned contracts. Historical content_digest remains SHA-256 of its exact
canonical envelope and historical pins stay resolvable. A new domain-separated bounded SHA-256
fold identifies canonical record/byte streams independently of upload boundaries; it is not
represented as SHA-256 of concatenated bytes. Actual records/bytes and their correspondence are
independently checked by PostgreSQL; a claimed hash alone is never admission. Old canonical
bytes and original/raw SHA-256 custody remain unchanged. New algorithm names must disclose their
meaning and cannot impersonate legacy digests.

Private fenced append, immutable freeze, complete validation and atomic final publication reuse
the existing task/attempt/holder authority. Internal forward references may wait privately;
external inputs remain admitted immutable products. Preserve containment/product-input acyclicity,
ordinary cross-reference multiplicity, complete inventories, fences, exact artifact custody,
endpoint/decision/coverage checks and current descriptor/helper/CHECK authoring. Validate the frozen
union without holding unrelated locks, then seal only if its owner and premises still hold.
No public read bypass may expose private rows. Failures preserve independently committed valid
recognition/native products and required evidence. Progressive scopes remain conditional on proven
closure and explicit scope pins; atomic whole-document visibility is the initial contract.

All SQL changes are new frozen forward revisions. Preserve0057–0061 unchanged, including undeployed
0061. Existing0060 JSON-text admission remains the deployed baseline until migration/cutover;
its surviving fences, raw evidence, archived contracts and native semantic protections are carried
forward, not relaxed. No data purge, historical HTML compatibility or grading change is authorized.

## Consequences

The model can retain and inspect large documents without mandatory giant containers. It requires
lossless lowering, versioned identity and an explicit freeze/validation boundary. Docling still
has document-wide reading-order/heading/enrichment dependencies: queue streaming is not proof of
bounded end-to-end memory. These producer obligations remain PDF-22, staging/seal PDF-20/21,
consumer/export migration PDF-24 and data/cutover PDF-25/10/11. No performance or source-fidelity
improvement is established by acceptance. The [coordinator](../plans/pdf-docling-pipeline_2026-10-31.md)
owns implementation, investigation and qualification state.
