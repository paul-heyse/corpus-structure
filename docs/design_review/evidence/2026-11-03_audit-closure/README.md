# Audit-closure integration evidence

2026-11-03. Current package/finding disposition belongs to the
[audit-closure coordinator](../../../plans/audit-closure_2026-11-03.md#11-execution-checkpoint--2026-11-03).
This is bounded integration evidence, not complete AC14 or M1 qualification.

## Accepted result and current source

Source commit `e816a212202c22a63392a3100dda11e90d215aa5` integrates the worker contributions,
freezes forward102 from immutable101 and uses semantic compiler16/execution compiler24.
The four checked migration artifacts preserve exact native/body/role/physical contracts.
The live native99 application store/default selections were not upgraded.
A formatter-only configuration correction after testing uses Ruff
[formatter-specific exclusion](https://docs.astral.sh/ruff/configuration/#python-file-discovery)
to preserve frozen semantic revisions while retaining lint. Final maintenance left runtime, test and migration bytes identical
to that source commit; typing, lint, readiness and ADR checks passed afterward. It changes neither
functional selection nor dependencies and is not a new functional qualification claim.

- **Passed:** `targeted-native-final-001.log`, 110 selected integration/consumer cases. This mixed
  selection includes real PostgreSQL, controlled actual CLI/MCP/evaluator paths and supporting
  non-database cases; its recipe/file names are not a claim that every case acquires PostgreSQL.
- **Passed:** `targeted-pure-final-001.log`, 308 selected non-database cases.
- The record below retains the exact selections. Covered behavior includes attributed support,
  structured reasons, inference/direct witnesses, split replay/concurrency/legacy preservation,
  actual index collation comparison, current-head authoring agreement, privilege drift, declared
  method dimensions, renewal/reclaim/uncertain settlement, six SourceViews, bounded image/source
  reads, pinned record consumers and independent reference machinery. These controlled references
  establish no model-quality or five-family release gate.
- Full typing/lint/readiness/ADR outcomes and final maintenance are retained as separate logs;
  final checkpoint receipts identify the last applicable commands. `just docs-check` retains
  pre-existing library publication-link failures outside edited scope.

## Authoring, failures and scope limits

`author-candidate.py` upgrades only an owned bare database to frozen101 and writes a fresh
prospective folder. `prepare-forward.py` was used before102 was committed to materialize its
untracked draft; it is a historical authoring artifact, not a command to overwrite frozen102.
Further changes require a new forward revision. `inspect-native-candidate.py` is a read-only
owned-database diagnostic; the final pytest selection independently asserts current-head agreement.

All attempted logs and prospective products are retained. Important resolved attempts include:
source integration crossing the initial inspection; first-managed historical owner/ACL declarations;
retirement lost from a paired admission file; a private split table's read-role declaration;
cardinality parentheses and PL/pgSQL variable/alias shadowing; missing/incorrect fixture contracts;
actual index collation omitted by library reflection; redundant empty role brackets; and reference
subsets incorrectly read from the domain namespace. Compiler24 gives the corrected execution
product a distinct identity. The provider/coverage composition correction is independently reviewed.

Parallel full-chain installations once exhausted the dedicated test cluster's shared lock table.
Those failed receipts remain; final migrations ran serially without server-setting changes.
The original query-fixture failures and later consumer failures are superseded by the final
selections above, not removed from the evidence.

All three secondary worktrees were removed after their contributions were integrated. The29
historical raw-log/pointer differences in each source/serving worktree had bytes identical to
that worktree's HEAD; copied dependency files and the delivered interactive patch were already
represented on main. No unique task work was discarded. Git branch history remains recoverable.

Actual managed-recognition and authenticated automation receipts live in their own dated folders
and retain their original source/context. They are not final-source provider requalification.
Complete `just test-all`/applicable hygiene, the complete required actual-provider/consumer union
and the subsequent M1 revision/execution remain open at the operator-requested wrap-up.

## Commands

```sh
uv run pytest python/corpus-structure/tests/semantic/test_pdf_native_consumer_journey.py python/corpus-structure/tests/semantic/test_read_contracts.py python/corpus-structure/tests/semantic/test_audit_closure_native.py python/corpus-structure/tests/semantic/test_native_closure.py::test_model_products_match_frozen_current_native_state python/corpus-structure/tests/semantic/test_native_closure.py::test_current_frozen_head_witness_records_current_authoring_provenance python/corpus-structure/tests/semantic/test_native_closure.py::test_live_cross_purpose_privilege_drift_refuses python/corpus-structure/tests/semantic/test_inference.py python/corpus-structure/tests/semantic/test_split_decisions_native.py python/corpus-structure/tests/semantic/test_index_collation_reflection.py python/corpus-structure/tests/semantic/test_method_dimensions_native.py python/corpus-structure/tests/semantic/test_claim_owner_native.py python/corpus-structure/tests/semantic/test_source_jit_native.py python/corpus-structure/tests/semantic/test_semantic_mcp.py python/corpus-structure/tests/semantic/test_published_region_artifact.py python/corpus-structure/tests/semantic/test_published_section_views.py python/corpus-structure/tests/semantic/test_native_source_budgets.py python/corpus-structure/tests/semantic/test_record_consumers.py python/corpus-structure/tests/evaluate/test_record_references_native.py
uv run pytest python/corpus-structure/tests/semantic/test_audit_closure_semantics.py python/corpus-structure/tests/semantic/test_semantic_reason_producers.py python/corpus-structure/tests/semantic/test_bounded_walks.py python/corpus-structure/tests/semantic/test_configured_coverage.py python/corpus-structure/tests/semantic/test_query_compatibility.py python/corpus-structure/tests/semantic/test_method_dimensions.py python/corpus-structure/tests/semantic/test_identity_resolution.py python/corpus-structure/tests/evaluate/test_split_decisions.py python/corpus-structure/tests/evaluate/golden/test_split.py python/corpus-structure/tests/ingest/test_annotations.py python/corpus-structure/tests/ingest/test_managed_recognition.py python/corpus-structure/tests/orchestrate/test_registry.py python/corpus-structure/tests/orchestrate/test_policy.py python/corpus-structure/tests/semantic/test_record_contracts.py python/corpus-structure/tests/semantic/test_source_contexts.py tests/test_native_math_methods.py python/corpus-structure/tests/semantic/test_reference_split_authority.py python/corpus-structure/tests/semantic/test_composed.py python/corpus-structure/tests/semantic/test_contracts.py
just types
uv run ruff check
just ready
just adr-lint
just docs-check
```

No Rust functional result is claimed; Rust source was unchanged. The readiness receipt records
the actual default Rust toolchain. Plans, evidence and frozen predecessors are retained.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**Audit closure integration**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Forward102 scoped integration and legacy preservation](records/ac13.forward102.json) | AC13 | passed | I04, AC13, AC14 selected controls | 2026-11-03 |
<!-- evidence-index:end -->
