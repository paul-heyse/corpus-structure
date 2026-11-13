# DDO retained-intent recovery successor · 2026-11-13

DDO-04/11 consumer: author and register the retained-intent recovery successor while preserving
the working database at its acquired revision. The active DDO coordinator owns completion state.
The request is `change.yaml`; registration is not deployment or activation.

## Registered artifacts

- Preview `0a88ddad651a4f7bb4ac0bdbc3f3323b`; apply `bfc2fd4e2e924ba8bb2e70ae61a3b16b`;
  rollback-only candidate `17aacbe38ee647fc980213dea38b780e`;
  registration `f95a443640374995bc0bf3462c2a3f55`: **passed** through `uv run ci model change`.
- Frozen revision `semantic_ddo_recovery_v1`, immediate predecessor `semantic_ddo_kernel_v1`.
  Actual acquired start was `semantic_bep_located_v2` on corpus_structure_dev/OID25921445,
  PostgreSQL system7701811359771751232, port5434. Authoring temporarily applied the exact
  registered kernel chain and rolled the enclosing transaction back.
- Three native transitions: `ops.ddo_impl_attach_data_request(jsonb)`,
  `sem.data_operation_native_descriptor()` and `data.execution_contract_descriptor()`.
  Zero ordinary schema operations; no table or column drops.
- Candidate artifacts: Python `f8f9cfbb8baba53aa50c5d5443e8da78ad36705900b6873ea1cf63a0b830057e`,
  operations `a75491a0cc380a96196179cd462991532cf024dad77a52b2b3421575ed68da9e`,
  admission `347e69083f8c359897fbb21da5deb96732ee78e5a0a986a477c641e6f48781fc`.

## Evidence limits

The initial preview `fcb4795372d74365bfc8e967697ffbc1` predates the completed ancestor-artifact
custody repair; the later preview above owns registration. Neither preview authorizes deployment.
The subsequent deployment-account repair changes helper source custody: future adoption must
reacquire/review current source and target, rather than treating this candidate as deploy-ready.
Existing frozen predecessor files were not edited. Native successor qualification passed through `uv run ci test --workers 2 --json --` on
the coordinator’s six-path native union, 61/61, `780320d32c3f4cb7a519230f4b322045`. Full DDO-12 qualification remains
open with the unfinished functional scope.
