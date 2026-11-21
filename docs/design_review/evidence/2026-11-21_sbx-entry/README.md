# SBX entry premises and shape baseline

**Inspected and tested within the stated scope · 2026-11-21.** Source baseline
`cc64bde7c94d6b6df026554947e981857fdab6de`. This evidence supports SBX-00 and the
generic SBX-01 contract. The coordinator owns the disposition of the entry checks.

The [block census](block_census.py) reads one authentic acknowledged historical sentence
answer. It verifies the acknowledgement identity, request size and request SHA-256 using the
same content framing checked by `CompletionDraftStore._open`, then decodes its tagged body
through the production codec. This is a structural census of retained bytes. Its v1 archived
writer schema and current native applicability are outside this question. It acquires no
PostgreSQL connection and starts no provider.

`uv run python docs/design_review/evidence/2026-11-21_sbx-entry/block_census.py` passed.
[Retained output](block-census.json) records 1,002 blocks, 25,543 tokens and 1,842 sentences.
This answer covers the historical 66-page region identified in the original draft evidence.
It supplies a substantial retained sample and does not claim complete book coverage.

## Block containment and partition size

Every retained sentence and token lies inside its annotation block, and every assigned token
lies inside the indexed sentence. The native sentence validator enforces those properties in
`semantic/sentence_products.py:311`. The canonical projection derives its packets from that
annotation and checks exact sentence/token membership in `canonical_sentences.py:150`.
`hanlp_products.canonical_hanlp_rows:55` preserves the canonical sentence and its closed token
population. HanLP detachment processes that sentence as one unit. Block of origin is therefore
the supported partition owner for these routes. The census tests sentence annotations, while
the canonical and HanLP conclusions are source inspection.

Serialized annotation-block bytes, including lexemes and annotation metadata, have a median of
6,122, p95 of 36,522 and maximum of 100,614. The largest block has 311 tokens and 13 sentences.
The complete block population occupies 11,046,101 bytes inside a 92,292,593-byte completion
request that also contains member packets and other completion facts. These are byte counts
of this retained representation, with no measured timing or future-shape size claim.

The sample supplies no reason to subdivide blocks. Its maximum is below the current core
256 MiB packet and 64 MiB reply defaults (`core/execution_policy.py:25`). A later full-book
population may expose a larger block. If it does, the split belongs in the first-population
cutover before SBX-03 relies on whole-block execution. Region page counts alone cannot settle
partition size.

## Optional fields and stable addresses

The retained token population contains no explicit null token fields and no differing token
field sets. The current producer recursively drops `None` when detaching annotations
(`sentence_products._detach_annotation_block`), while the optional integer `sentence` slot is
declared separately from required token fields in `model/semantic/data-operation-sentences.yaml`.
Readers use both missing/default restoration and optional membership. Preserve absence and
explicit null as distinct tagged mappings in the new group encoding. This avoids relying on
one historical population to narrow the future input contract.

Current block identifiers are source pointers such as `#/texts/86`; table-cell blocks also
include a cell suffix. Neither absolute position nor source digest should enter the new
partition content. Moving a retained block under the same key must preserve its content digest.
Reconversion of an edited source can renumber pointers. Block-relative coordinates alone do
not establish cross-original correspondence for such a renamed block. The source identity and
correspondence owner must establish that mapping before reuse may rely on it.

Absolute start/end and partition order belong in authenticated placement metadata outside the
partition content digest. Consumers that read either fact must include it in their projection.
The content root over key-sorted pairs cannot alone authenticate semantic read order.

## References and input roles

The current model has shared reference carriers without declared target roles. The production
paths inspected here include canonical-to-annotation, HanLP-to-canonical, formal-to-source,
construction-to-formal and sentence, predicate-to-construction, and scoped-relation inputs.
HanLP declares both `source` and `canonical`; scoped relations declare `source`, `constructions`,
`formal` and `predicates`. These immediate references have visible input owners.

An input can itself carry references to earlier products. For example, construction members
copy references obtained from upstream inventories, and the reference closure does not tell
the compiler whether those are direct inputs or references to be followed through the input's
own derivation. Thus the universal premise that every embedded citation is a direct bound
input is **not established** by today's declaration model. SBX-05 must type these paths and
resolve a nested reference through its actual owning derivation, or add a missing input role
where the producing operation directly reads that product. Product indexes and rich support
references retain the explicit exceptions described in the reference companion. No new native
support edge is justified by this inspection.

## Proof boundary and model-host peers

`data_validity_native` constructs the direct validity facts once, materializes the adjacency
facts, then advances a monotone wave until no new valid nodes appear in `ddo_valid_closure`.
`request_attachment_native._binding_validation_program` already owns validation of selected
inputs and support. Put SBX-02 required rule-proof lookups there, after input selection and
outside the validity fixpoint. This settles a safe placement without adding rule-table
queries to every recursive wave. No proposed proof table is installed by this check.

`methods/contextual_embeddings.EncoderNumericalPolicy` explicitly declares cohort-and-order
dependent float32 observations. Keep contextual encoding whole-collection until a narrower
determinant is demonstrated. GLiNER classification constructs a batch digest from all member
requests, checks the ordinal in that batch and derives the observation digest from it
(`methods/pm2_gliner_classification.py:220`). Its current authenticated result therefore depends
on the batch even where numerical independence might eventually hold.

Sentence annotation is produced through the block-local `_detach_annotation_block` path and
HanLP consumes individual canonical sentence populations, but the model host can batch their
execution. Source inspection establishes their explicit input granularity, not exact numerical
independence from physical peers. SBX-07 may adopt block memoization only after accounting for
the actual loaded host and effective numerical policy. Until then these routes retain a
whole-collection execution premise. This entry check runs no new provider inference.

## Evidence limits and next consumers

SBX-01 can proceed with the generic collection and partition contract. The retained census
supports block-sized partitions for the observed annotation population and absence-preserving
group encoding. SBX-02 consumes the binding-only proof placement. SBX-03 owns real producer
conversion and any size-driven split discovered on its final input. SBX-05 must close the
direct and transitive reference-role inventory. SBX-07 owns the per-kernel memoization decision.

The [shape baseline](shape-baseline.md) records the test and fixture consumers that change with
the series. It is an execution checklist in this evidence folder and adds no repository gate.
