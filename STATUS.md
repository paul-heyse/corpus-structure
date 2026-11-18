# Status

_Updated 2026-11-17. Owned stage is at model-built N8 with its matching application active at generation 9. The broader DDO authoring conversion remains open._

## Current owners

- The [DDO coordinator](docs/plans/declared-data-operations_2026-11-12.md#pdf-publication-controls-source-binding-and-n8--2026-11-17) owns actual rollout and remaining work. The [PostgreSQL companion](docs/plans/declared-data-operations/postgresql-realization-and-retirement.md#model-owned-sql-authoring) owns typed authoring under [ADR-0131](docs/adr/0131-model-owned-postgresql-programs.md).
- N6 includes model-bound facade/DATA generation, typed physical checks and indexes, PDF search configuration, shared-stream writes, producer certification, scratch, closure programs, native privileges, runtime guards and host bootstrap. DuckDB 2.0 owns rich set/view queries, companion analysis, replay sorting and PDF geometry.
- N7 adds typed PDF staging, request claim and release, contextual scoring and the corrected residual search body reader. N8 adds generated PDF freeze and projection controls, source-set binding and release receipt guards. The superseded Python companion upload wrappers were removed.

- [Library-discovery tooling](tooling/docs/plans/library-discovery-tooling_2026-11-17.md) is a separate Proposed series (LDT-00–08, conditional LDT-C1–C3) for the `tooling/` package; it owns the [tooling review](docs/functional_reviews/library-discovery-tooling_2026-11-17.md) O01–O10. Nothing is implemented. Next: operator confirmation of RC1–RC3 and RC6, then LDT-00. Documentation only, 2026-11-17: `uv run ci docs check` passed; product checks `not_run` (no product change).

## Native and data boundary

- `corpus_structure_ddo_stage`, OID130661481/system7701811359771751232, reached `semantic_ddo_pe_n8` in deployment `94724ef3024249eea00ade9c1bd3f403`. Independent reads observed 15 PDF products, 361 verified streams and 376 parts.
- `release:7ff08724edcd2ef75c83657ac298c7876e3759bc2fd0c9f47ff5a60d02007ea2` and its source-native runtime passed application deployment `df3ec8392c6e4ac199a70318f4f53d9f`, `ci db check` and `ci release check`. Activation and the separate generation-9 read passed. Development remains at `semantic_bep_located_v2`.

## Last verified · 2026-11-17

- **passed:** integrated native/physical/runtime selection `4b427f1f5ebd43ffae381316591200a3` (30), DATA counterfactual and analytical selection `a6b3a7f3961441908180abcb1fcd59fe` (28), and shared-stream publisher expiry retry `211019e6c51c4ff69d92d7d24b006f99` (3). Earlier N5 runtime replay failures and the N6 consumer retry remain in the coordinator. The residual-body search fix passed both exact journeys in `a556e7fbb6314933b01a7d8c2226b2b4`.
- **passed on N7:** native selection `67082fbd60194f009ecd652aca646320` (17), shared streams and search `a599f5a4a6af49bfa72bf09b5c89e629` (17) and claim/renew/release `f063b540786b45818d61dcd98a0d78e2` (4). N8 native program selection `b18da2abe9994d1f9250dc1d5c03dc7f` (22) passed.
- **passed on N8:** PDF companion, payload, publication and retained-contract consumers `620154b496144b378ec12417752b7a58` (15 passing), plus the corrected projection replay `1f2871a72dc649f8af1647f5bda85ac8`. The coordinator retains the earlier fixture failures and describes their corrections.

## Next execution

- Complete remaining PDF publication and record readers, DDO binding/acquisition/completion and event kernels, general native admission, native test provisioning, and fixture-only occurrence replay retirement. Complete applicable native/application qualification against their exact successor.
- The separate DDO-12 boundary includes actual-book S33 parser adoption, faithful29-original registration and adoption, native scoring/provider/public/rich/graph/export/fault coverage, and same-demand518-page interruption/resume/repeat. Chandra OCR remains excluded. Restart the normal managed Nemotron launcher when recognition is due.
