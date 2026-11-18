# Status

_Updated 2026-11-17. Owned stage is at model-built N6 with its application active at generation 7. The broader DDO authoring conversion remains open._

## Current owners

- The [DDO coordinator](docs/plans/declared-data-operations_2026-11-12.md#native-follow-through-and-n6--2026-11-17) owns actual rollout and remaining work. The [PostgreSQL companion](docs/plans/declared-data-operations/postgresql-realization-and-retirement.md#model-owned-sql-authoring) owns typed authoring under [ADR-0131](docs/adr/0131-model-owned-postgresql-programs.md).
- N6 includes model-bound facade/DATA generation, typed physical checks and indexes, PDF search configuration, shared-stream writes, producer certification, scratch, closure programs, native privileges, runtime guards and host bootstrap. DuckDB 2.0 owns rich set/view queries, companion analysis, replay sorting and PDF geometry.
- Main adds typed PDF staging, request claim and release, and contextual scoring for a further successor. Its native and application deployment evidence is open.

- [Library-discovery tooling](tooling/docs/plans/library-discovery-tooling_2026-11-17.md) is a separate Proposed series (LDT-00–08, conditional LDT-C1–C3) for the `tooling/` package; it owns the [tooling review](docs/functional_reviews/library-discovery-tooling_2026-11-17.md) O01–O10. Nothing is implemented. Next: operator confirmation of RC1–RC3 and RC6, then LDT-00. Documentation only, 2026-11-17: `uv run ci docs check` passed; product checks `not_run` (no product change).

## Native and data boundary

- `corpus_structure_ddo_stage`, OID130661481/system7701811359771751232, reached `semantic_ddo_pe_n6` in deployment `69c66b4b96b4447db7bf081fc0ba0e9c`. Independent reads observed 15 PDF products, 361 verified streams and 376 parts.
- `release:b0d270dd6924af205eaffbd6b6a7f00322173981bf76cf8fb7df44b5b7bc6709` and its matching source-native runtime passed application deployment `f118665177e5402b8ae89ea564227896`, `ci db check` and `ci release check`. Activation and separate generation-7 read passed. Development remains at `semantic_bep_located_v2`.

## Last verified · 2026-11-17

- **passed:** integrated native/physical/runtime selection `4b427f1f5ebd43ffae381316591200a3` (30), DATA counterfactual and analytical selection `a6b3a7f3961441908180abcb1fcd59fe` (28), and shared-stream publisher expiry retry `211019e6c51c4ff69d92d7d24b006f99` (3). Earlier N5 runtime replay failures and the N6 consumer retry remain in the coordinator. Search hits opening empty source bodies remain under the published item reader.
- **passed on N6:** `ci check --only types --json` `16c5f2f2394e4ef99879f46f860d30da`, `ci check --only lint --json` `37d48033a5bf47a6969c854d195f5de3`, and `just turn-end`. The next source and stage have separate qualification.

## Next execution

- Complete remaining PDF publication and record readers, DDO binding/acquisition/completion and event kernels, general native admission, native test provisioning, and fixture-only occurrence replay retirement. Complete applicable native/application qualification against their exact successor.
- The separate DDO-12 boundary includes actual-book S33 parser adoption, faithful29-original registration and adoption, native scoring/provider/public/rich/graph/export/fault coverage, and same-demand518-page interruption/resume/repeat. Chandra OCR remains excluded. Restart the normal managed Nemotron launcher when recognition is due.
