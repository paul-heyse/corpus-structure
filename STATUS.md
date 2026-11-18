# Status

_Updated 2026-11-17. Owned stage is at model-built N7 with its matching application active at generation 8. The broader DDO authoring conversion remains open._

## Current owners

- The [DDO coordinator](docs/plans/declared-data-operations_2026-11-12.md#staging-request-lifecycle-and-n7--2026-11-17) owns actual rollout and remaining work. The [PostgreSQL companion](docs/plans/declared-data-operations/postgresql-realization-and-retirement.md#model-owned-sql-authoring) owns typed authoring under [ADR-0131](docs/adr/0131-model-owned-postgresql-programs.md).
- N6 includes model-bound facade/DATA generation, typed physical checks and indexes, PDF search configuration, shared-stream writes, producer certification, scratch, closure programs, native privileges, runtime guards and host bootstrap. DuckDB 2.0 owns rich set/view queries, companion analysis, replay sorting and PDF geometry.
- Main adds typed PDF staging, request claim and release, and contextual scoring in N7, including the corrected residual search body reader.

- [Library-discovery tooling](tooling/docs/plans/library-discovery-tooling_2026-11-17.md) is a separate Proposed series (LDT-00–08, conditional LDT-C1–C3) for the `tooling/` package; it owns the [tooling review](docs/functional_reviews/library-discovery-tooling_2026-11-17.md) O01–O10. Nothing is implemented. Next: operator confirmation of RC1–RC3 and RC6, then LDT-00. Documentation only, 2026-11-17: `uv run ci docs check` passed; product checks `not_run` (no product change).

## Native and data boundary

- `corpus_structure_ddo_stage`, OID130661481/system7701811359771751232, reached `semantic_ddo_pe_n7` in deployment `2505f822f86c49cda439333ed695c030`. Independent reads observed 15 PDF products, 361 verified streams and 376 parts.
- `release:e9898a7362e50114989d2fe4bf351343dad6f9d185aa49b82b4f46aad845ba96` and its source-native runtime passed application deployment `4322ccef591046ee940efb4dd45640ec`, `ci db check` and `ci release check`. Activation and the separate generation-8 read passed. Development remains at `semantic_bep_located_v2`.

## Last verified · 2026-11-17

- **passed:** integrated native/physical/runtime selection `4b427f1f5ebd43ffae381316591200a3` (30), DATA counterfactual and analytical selection `a6b3a7f3961441908180abcb1fcd59fe` (28), and shared-stream publisher expiry retry `211019e6c51c4ff69d92d7d24b006f99` (3). Earlier N5 runtime replay failures and the N6 consumer retry remain in the coordinator. The residual-body search fix passed both exact journeys in `a556e7fbb6314933b01a7d8c2226b2b4`.
- **passed on N7:** native selection `67082fbd60194f009ecd652aca646320` (17), claim/renew/release `f063b540786b45818d61dcd98a0d78e2` (4), types `4ad8c5fc909e45ea8395c075d060faaa`, lint `ecd3c02dc6b4495a8c4ef33c144bd05e`, and docs `ccb40a01281b485abaf9f1ad333314a7`.

## Next execution

- Complete remaining PDF publication and record readers, DDO binding/acquisition/completion and event kernels, general native admission, native test provisioning, and fixture-only occurrence replay retirement. Complete applicable native/application qualification against their exact successor.
- The separate DDO-12 boundary includes actual-book S33 parser adoption, faithful29-original registration and adoption, native scoring/provider/public/rich/graph/export/fault coverage, and same-demand518-page interruption/resume/repeat. Chandra OCR remains excluded. Restart the normal managed Nemotron launcher when recognition is due.
