# PostgreSQL typed-domain execution · 2026-11-09

The [owning series](../../../plans/postgresql-typed-domain_2026-11-09.md) owns PTD-00–02 state.
The model-change request binds the acquired development predecessor to the typed source change.
Table shapes remain unchanged; source-derived companion projection identities and execution ABI
require regenerated native admission products. Preview/candidate/deployment and scoped test outcomes
are recorded in the owning plan after execution. No benchmark or quantitative benefit is claimed.

## Native delivery

2026-11-09: final preview `79b053fa24aa4f94b9c23797ee475aa1`, rollback-only candidate
`708d49125fd1412ca852c0568f1611ec`, registration `c503278362e74579950de718cc7079a1`
and deployment `f5cffb0c7ffe4065ba623c4b3738146f` **passed** through `uv run ci model change
preview`, `candidate`, `register` and `deploy`. The exact request is [model-change.yaml](model-change.yaml).
Candidate review used `ci model change inspect --view patch` and `inspect-candidate` plus the
emitted migration source. Five native updates and physical-contract registration preserve table
shapes while replacing source-derived projection and admission identities. The frozen files live
under `python/corpus-structure/semantic_alembic/versions/semantic_ptd_typed_bindings*`.

Deployment reached `semantic_ptd_typed_bindings` from `semantic_pm2_named_pieces`, archiving and
admitting `release:2498340837f5fe3a4e118bdbf00811e67a2912be8e79d3a2765d7372a6cf01de` on the
acquired development target. No project activation, run promotion or default change was performed.
Earlier previews `017fa80d23ed427fa0504db600e27e1c` and `6416f1ffbb384b5ba18f979891e33bd6`
were superseded by final generated-source preparation; neither was deployed.

## Runtime compiler integration correction

The first native acceptance run `b354ccddde814329bf04e6b2bd7c0ae4` **failed** (43 passed,
three failed): the native runtime-binding validator still required compiler27. The correction
supports27/28 and requires manifest/compiler equality with the archived execution model, preserving
the start_run ABI fence. The new compiler_mismatch test independently attempts supported-but-wrong27.

The [follow-up request](runtime-model-change.yaml) binds the exact first PTD predecessor.
Preview `e9453551c1d84cd3af072113608c40ff`, rollback-only candidate
`a0e15cb84b564de0a8f54e4161b2a840`, registration `9deb8c2a7c2a4fbda7937bba43beeb8f`
and deployment `a488fc505b664419be2de459ce8e46b9` **passed** on 2026-11-09 via the same
ci model-change stages. Two native operations and zero ordinary operations reached
`semantic_ptd_runtime_compiler`; the semantic release remained unchanged. Both frozen revisions
are retained. Independent source reviews found no material findings in PTD01, PTD02 or this guard
correction; reviewers did not run tests. Final affected functional selections follow this migration.

## Final functional selections · 2026-11-09

Both commands use `uv run ci test --json --` followed by the following module paths under
`python/corpus-structure/tests/`. Source was frozen and the acquired native head was
semantic_ptd_runtime_compiler. These are scoped package controls, not PTD-11 qualification.

- **passed**, 135/135, result be28b618badb4ea8a26cf3de610658cc: semantic/test_operation_call_generation.py,
  semantic/test_typed_realization.py, semantic/test_core_operation_calls.py,
  semantic/test_companion_call_bindings.py, semantic/test_projection_recipe.py,
  schema/test_relational.py, semantic/test_companion_export.py,
  semantic/test_database_description.py, semantic/test_interop.py, db/test_adbc_lifetime.py,
  semantic/test_runtime_bindings_native.py.
- **passed**, 46/46, result950e50b599334c85919d5fecebe1281d: semantic/test_companion_export_native.py,
  semantic/test_columnar_journey.py, semantic/test_analytics.py, semantic/test_capture_policy.py,
  semantic/test_capture_capacity.py, semantic/test_read_contracts.py.

The runtime controls include unsupported compiler and supported-but-mismatched compiler refusals.
The ADBC controls include real cancellation and driver/resolver parity. Independent expected rows,
closed values and SQL/JSON null controls cover companion materialization and actual detached export.
Final result IDs and both deployment IDs are held for the owning plan.

Earlier results remain distinct: a645562e6e254c7a83f482fcba6a25ec (50 passed/one stale native ABI
failure),393f274eed72444596c9386197168cd8 (three passed/one formatting assertion, repaired),
1f77392c8cfe42a5885e88c6fc6f17ea (14 passed/four incorrect implicit-principal expectations,
repaired),27fbb02fa1644bb18f6a05321445dddd (seven passed/one stale native ABI failure),
and b354ccddde814329bf04e6b2bd7c0ae4 (43 passed/three compiler-guard failures, repaired).
Final full selections supersede these obligations without erasing their original outcomes.
The earlier d34df6bf976b4e2fb81f949f5a7e8922 passed122 before the runtime correction;
the final135 rerun covers that selection plus the runtime controls on corrected native context.
