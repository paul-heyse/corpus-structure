# Status

_Updated 2026-11-17. The owned stage is at model-built N4 with its matching application active. DDO and the PostgreSQL authoring conversion remain open._

## Current owners

- [DDO current execution](docs/plans/declared-data-operations_2026-11-12.md#model-owned-postgresql-execution--2026-11-17) owns stage results and remaining obligations. [PostgreSQL realization](docs/plans/declared-data-operations/postgresql-realization-and-retirement.md#model-owned-sql-authoring) owns the authoring contracts under [ADR-0131](docs/adr/0131-model-owned-postgresql-programs.md).
- Main integrates typed PDF preparation, scratch, shared readers, validity, search, SourceValue codecs, physical defaults and generated projections, DATA effects, selected runtime queries and database administration. Native preview renders the original-document and typed-column facades alongside physical effects. N4 generates wire admission and removes the duplicate demand-read field guard.
- Remaining owners include shared-stream writes and verification, PDF publication, DDO kernels, physical checks/index expressions, native admission and privileges, scientific routines and administration beyond the database CLI. Remaining generation work covers other Python facades, search configuration correspondence and DATA builders bound to proposed physical models.
- [Library-discovery tooling](tooling/docs/plans/library-discovery-tooling_2026-11-17.md) is a separate Proposed series (LDT-00–08, conditional LDT-C1–C3) for the `tooling/` package; it owns the [tooling review](docs/functional_reviews/library-discovery-tooling_2026-11-17.md) O01–O10. Nothing is implemented. Next: operator confirmation of RC1–RC3 and RC6, then LDT-00. Documentation only, 2026-11-17: `uv run ci docs check` passed; product checks `not_run` (no product change).

## Native and data boundary

- Owned stage `corpus_structure_ddo_stage`, OID130661481/system7701811359771751232, independently read at `semantic_ddo_pe_n4`. N4 preview `71e0ea10c2c44919ba18f631721f0132`, candidate `5652429e4dd040d3b77ba3395ad05297`, registration `84ce03a78771490aa5723fc38d147b70` and deployment `e3ff00b57edb40929abe52b5bf3a4893` passed.
- N3 retained 15 products, retired seven unqualified historical validation receipts and replaced the two part tables with 361 verified shared streams over 376 parts. An independent N4 read observed the same product and shared-byte counts on 2026-11-17.
- Matching `release:0f016a1cce193cefdc639e08e440a4cc5ee8784f80b447ffffce557103bd2495` is active for `ddo-current-pdf-bounded` at generation6. Deployment `5a335c6524a940b488d71f1c9f439b10`, explicit `ci db check --release …`, `ci release check --release …` and activation passed. Development OID25921445 remains at `semantic_bep_located_v2`.

## Last verified · 2026-11-17

- **passed:** `ci test --workers 2 --json -- …` fresh-root render/replay, wire and original-document18 in `983d99ea225a4591b0d9fc92b34b7a88`; native preview and generated-output custody3 in `78e30bf4fab443f5b847cd5d40c523ea`. The two PostgreSQL search cases passed via `ci test retry 33b37a199ad54e79ba5a644d8ba21512 --lane ordinary --json`, `53917fc838d146f8862e26e330a3ca51`.
- Shared-stream reuse passed in retry `adb5228fe7fc4e07ab1d51416e1edf91`. Its two search failures and older failed receipts remain in the coordinator with their dispositions. Database CLI and ownership cases passed in the bounded original selection `5d696cb866624916902caeae4e5f0e63`. Earlier source-bounded provider evidence keeps its original context.
- **passed:** `ci check --only types --json` `886edad9909d4fb293e093bb79932651`, `ci check --only lint --json` `9308fb254f6243a28f3b895dc46c799a`, `ci adr lint --json` `1526d872b3724c1688b0cbea205b49ff`, `ci docs check --json` `f6f0a33597b946a9915fe2e0e7575ca0`, and `just turn-end`.

## Next execution

- Convert remaining SQL owners and remove superseded code with their consumers. Move remaining controlled PDF fixtures through production certification before removing their legacy replay helper. Complete applicable native and application consumer qualification.
- Complete actual-book S33 parser adoption, faithful29-original registration/adoption, native scoring/provider/public/rich/graph/export/fault coverage, and same-demand518-page interruption/resume/repeat before the DDO-12 union. Chandra OCR remains excluded. Restart the normal managed Nemotron launcher when recognition is due.
- Task workers and worktrees are concluded. No push. Preserve the working development database until the coordinated adoption boundary.
