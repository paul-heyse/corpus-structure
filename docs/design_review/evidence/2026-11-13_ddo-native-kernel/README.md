# DDO native kernel migration preparation · 2026-11-13

DDO-04 consumer: prepare and register the forward native candidate for the current physical
model and guarded data-operation kernel. The source request is `change.yaml`. Candidate authoring
uses the normal rollback-only development route. Registration writes frozen migration artifacts;
production deployment and activation are outside this closeout. Isolated test databases qualify
the registered migration before normal target admission can be claimed. The DDO coordinator owns
current outcome, managed receipts and remaining scope.


## Current receipt · 2026-11-13

- Passed preview `f500ce98465a4260845d5772d2e0db53`, apply
  `12ea0387dc004636842dd284a8d88062`, candidate `b0a0b07c907144eab227f891ba28caab`, and
  registration `2ae5b1b7cd7e420fb21d700cb03f0c25`. Candidate and preview are held for DDO-04/11.
- Registered `semantic_ddo_kernel_v1` after `semantic_bep_located_v2`: 26 new tables, two task
  columns, five nullable task fields under the explicit task constraint, two indexes and managed
  native operations. Reviewed candidate source has no table or column drops.
- Refreshed authoring after formatting reproduced the registered upgrade/state/admission hashes
  exactly: `56663896be32a8af822814a55f632676f67b46af5c9edee85e56ea14207f7c38`,
  `f4dbd0815f504397b5a5ca89a7d7ec0da3b1dd79a9396a45dc5a382b04fee439`,
  `4f81819f48986f61199728f15600c9d0499d03019b8b20f5575e1bc22192bcda`.
- Actual frozen migration, normal target catalog admission and native controls are included in
  the final 442-case targeted union `e332a3ef0884454988beaad5af1166b7`, passed. The
  [coordinator](../../../plans/declared-data-operations_2026-11-12.md#ddo-0305-partial-implementation-checkpoint--2026-11-13)
  owns the exact command, repaired failures and unfinished functional scope.
- Persistent target observed: corpus_structure_dev/OID25921445, system7701811359771751232,
  PostgreSQL18/corpus port5434. `ci db status --maintenance --json` still reports
  `semantic_bep_located_v2`; no persistent deployment, activation or protected answer read occurred.
