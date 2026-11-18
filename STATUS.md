# Status

_Updated 2026-11-18. The owned stage is at model-built N12 with its matching application active at generation 13. N13, development adoption and assembled qualification remain open._

## Current owners

- The [DDO coordinator](docs/plans/declared-data-operations_2026-11-12.md#protected-pdf-authoring-and-readers--2026-11-18) owns actual rollout and remaining work. The [PostgreSQL companion](docs/plans/declared-data-operations/postgresql-realization-and-retirement.md#model-owned-sql-authoring) owns typed authoring under [ADR-0131](docs/adr/0131-model-owned-postgresql-programs.md).
- N6 includes model-bound facade/DATA generation, typed physical checks and indexes, PDF search configuration, shared-stream writes, producer certification, scratch, closure programs, native privileges, runtime guards and host bootstrap. DuckDB 2.0 owns rich set/view queries, companion analysis, replay sorting and PDF geometry.
- N7 adds typed PDF staging, request claim and release, contextual scoring and the corrected residual search body reader. N8 adds generated PDF freeze and projection controls, source-set binding and release receipt guards. The superseded Python companion upload wrappers were removed.
- N9 adds typed PDF contract admission, companion reads, validation and sealing, DDO binding operands, and read and epoch-lock boundaries.
- N10 adds typed PDF inventory, contract folds, frozen checks and sealed receipt projection, plus original-document and PDF capture proofs.
- N11 removes the fixture-only PDF occurrence replay writer. Native workers and controlled fixtures use the same certified reply emitter.
- N12 replaces authored PDF companion, observation, export, context, proof, identity and correspondence SQL with generated native programs. The stage also includes generated DDO binding, population and selected-source acquisition, and PDF completion.

- [Library-discovery tooling](tooling/docs/plans/library-discovery-tooling_2026-11-17.md#current-state) (LDT series, [ADR-0132](docs/adr/0132-tooling-package.md)) is implemented for LDT-00–08: the `tooling library` commands `baseline`, `selection`, `metadata`, `inventory`, `census`, `compare` and `overview`, with the discovery guide and skill pointing to them. Verified 2026-11-17: `uv run ci test -- tooling/tests tests/scripts/test_test_receipts.py` passed (`8cd3bc5aa2b24d5a9e5d8d4c4a69270b`, 302 tests) and `uv run ci check` passed (`34811b452107403d90e5035f8a2e0550`); the full product suite is `not_run` for this series (no product change). Conditional LDT-C1–C3 are unstarted and wait for their triggers; the series owns known limits and next work.

## Native and data boundary

- `corpus_structure_ddo_stage`, OID130661481/system7701811359771751232, reached `semantic_ddo_pe_n12` in deployment `41e3ad85978548d1be0370c96038d04d`. Independent reads observed 15 PDF products, 361 verified streams and 376 parts.
- `release:277ac7aa76aef92b6b4c3420d30ac9b92b4ca188f26cf82e1dcd2cc3f62ed3c8` and its source-native runtime passed application deployment `156dff9e2222484fb155e6698fd894a7`, `ci db check` and `ci release check`. Activation and the separate generation-13 read passed. Development remains at `semantic_bep_located_v2`.

## Last verified · 2026-11-18

- **passed on N12:** all 73 selected PostgreSQL PDF controls in `f6544d5c3bee4cb5af0360c23596e8b8`. Original-descriptor registration passed 18 focused controls, including exact 29-descriptor registration into nine projects, repeat and rollback, in `21659bbf93c145bd90ba806c31f50a73`.

- **passed:** integrated native/physical/runtime selection `4b427f1f5ebd43ffae381316591200a3` (30), DATA counterfactual and analytical selection `a6b3a7f3961441908180abcb1fcd59fe` (28), and shared-stream publisher expiry retry `211019e6c51c4ff69d92d7d24b006f99` (3). Earlier N5 runtime replay failures and the N6 consumer retry remain in the coordinator. The residual-body search fix passed both exact journeys in `a556e7fbb6314933b01a7d8c2226b2b4`.
- **passed on N7:** native selection `67082fbd60194f009ecd652aca646320` (17), shared streams and search `a599f5a4a6af49bfa72bf09b5c89e629` (17) and claim/renew/release `f063b540786b45818d61dcd98a0d78e2` (4). N8 native program selection `b18da2abe9994d1f9250dc1d5c03dc7f` (22) passed.
- **passed on N8:** PDF companion, payload, publication and retained-contract consumers `620154b496144b378ec12417752b7a58` (15 passing), plus the corrected projection replay `1f2871a72dc649f8af1647f5bda85ac8`. The coordinator retains the earlier fixture failures and describes their corrections.
- **passed on N9:** 65 native controls `d66a898a8bb946e483c085e45a0a00eb`, six publication journeys `ced70c4b8fb94fedb8a0b36879e5e774`, Pyrefly `bfbe18e106c84b69958a13a93f79ed4f`.
- **passed on N10:** 43 focused controls `4478865c9e9b4591bc23441daa2c24d5`, six publication/projection journeys `df34e1b754424193b6f3e9dadc5c9816`, two corrected integration journeys `3211fb6439c741549ed9dadd122cc192`, model render, Pyrefly `59c7cbe26b014cb78bc5534d53ed2caf`, Ruff `ee804d2e669341029a5a366d2104f0c8` and docs `0b3c2eccf4c745b08f9b0a0761397ef4`.
- **passed on N11:** 22 focused cases across `b34d8c178ebd47b5b224da516b643617` and `6d7c4cf892c041ce9ae1efe6a458c785`, actual three-page Docling recovery `95d99f3e8a8e4e0389a1851b491aff06`, model render, Pyrefly `09df63a6b58e457d8b0552eb9818ce27` and Ruff `d619c83319b14f9bae6d188706291fb4`.

## Next execution

- Complete N13 acquisition, publication, settlement and native admission, then qualify the assembled source against the next successor. The NCE list-host failure came from interpreting current string pointers as Docling reference objects. Six isolated pointer fidelity controls passed after the fix.
- The separate DDO-12 boundary includes actual-book S33 parser adoption, faithful29-original registration and adoption, native scoring/provider/public/rich/graph/export/fault coverage, and same-demand518-page interruption/resume/repeat. Chandra OCR remains excluded. Restart the normal managed Nemotron launcher when recognition is due.
