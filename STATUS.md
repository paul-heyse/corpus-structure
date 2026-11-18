# Status

_Updated 2026-11-17. Owned stage is at model-built N9 with its matching application active at generation 10. The broader DDO authoring conversion remains open._

## Current owners

- The [DDO coordinator](docs/plans/declared-data-operations_2026-11-12.md#typed-pdf-validation-and-ddo-read-bounds--2026-11-17) owns actual rollout and remaining work. The [PostgreSQL companion](docs/plans/declared-data-operations/postgresql-realization-and-retirement.md#model-owned-sql-authoring) owns typed authoring under [ADR-0131](docs/adr/0131-model-owned-postgresql-programs.md).
- N6 includes model-bound facade/DATA generation, typed physical checks and indexes, PDF search configuration, shared-stream writes, producer certification, scratch, closure programs, native privileges, runtime guards and host bootstrap. DuckDB 2.0 owns rich set/view queries, companion analysis, replay sorting and PDF geometry.
- N7 adds typed PDF staging, request claim and release, contextual scoring and the corrected residual search body reader. N8 adds generated PDF freeze and projection controls, source-set binding and release receipt guards. The superseded Python companion upload wrappers were removed.
- N9 adds typed PDF contract admission, companion reads, validation and sealing, DDO binding operands, and read and epoch-lock boundaries.

- [Library-discovery tooling](tooling/docs/plans/library-discovery-tooling_2026-11-17.md) is a separate Proposed series (LDT-00–08, conditional LDT-C1–C3) for the `tooling/` package; it owns the [tooling review](docs/functional_reviews/library-discovery-tooling_2026-11-17.md) O01–O10. Nothing is implemented. Next: operator confirmation of RC1–RC3 and RC6, then LDT-00. Documentation only, 2026-11-17: `uv run ci docs check` passed; product checks `not_run` (no product change).

## Native and data boundary

- `corpus_structure_ddo_stage`, OID130661481/system7701811359771751232, reached `semantic_ddo_pe_n9` in deployment `88962959ffc64da98cd88e58e9c842d5`. Independent reads observed 15 PDF products, 361 verified streams and 376 parts.
- `release:73cff998d48d56e462e5a545aff7388f2a313224bd77516b8a40652c5777d8d5` and its source-native runtime passed application deployment `3add92d7c5b642599c5c5467a7c05179`, `ci db check` and `ci release check`. Activation and the separate generation-10 read passed. Development remains at `semantic_bep_located_v2`.

## Last verified · 2026-11-17

- **passed:** integrated native/physical/runtime selection `4b427f1f5ebd43ffae381316591200a3` (30), DATA counterfactual and analytical selection `a6b3a7f3961441908180abcb1fcd59fe` (28), and shared-stream publisher expiry retry `211019e6c51c4ff69d92d7d24b006f99` (3). Earlier N5 runtime replay failures and the N6 consumer retry remain in the coordinator. The residual-body search fix passed both exact journeys in `a556e7fbb6314933b01a7d8c2226b2b4`.
- **passed on N7:** native selection `67082fbd60194f009ecd652aca646320` (17), shared streams and search `a599f5a4a6af49bfa72bf09b5c89e629` (17) and claim/renew/release `f063b540786b45818d61dcd98a0d78e2` (4). N8 native program selection `b18da2abe9994d1f9250dc1d5c03dc7f` (22) passed.
- **passed on N8:** PDF companion, payload, publication and retained-contract consumers `620154b496144b378ec12417752b7a58` (15 passing), plus the corrected projection replay `1f2871a72dc649f8af1647f5bda85ac8`. The coordinator retains the earlier fixture failures and describes their corrections.
- **passed on N9:** 65 native controls `d66a898a8bb946e483c085e45a0a00eb`, six publication journeys `ced70c4b8fb94fedb8a0b36879e5e774`, Pyrefly `bfbe18e106c84b69958a13a93f79ed4f`.

## Next execution

- Complete remaining PDF publication and record readers, DDO binding/acquisition/completion and event kernels, general native admission, native test provisioning, and fixture-only occurrence replay retirement. Complete applicable native/application qualification against their exact successor.
- The separate DDO-12 boundary includes actual-book S33 parser adoption, faithful29-original registration and adoption, native scoring/provider/public/rich/graph/export/fault coverage, and same-demand518-page interruption/resume/repeat. Chandra OCR remains excluded. Restart the normal managed Nemotron launcher when recognition is due.
