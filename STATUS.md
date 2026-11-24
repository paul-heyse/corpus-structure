# Status

_Updated 2026-11-24. Development acceptance through SBX-16 is complete on `semantic_sbx_read_visual_bounds`._ [Plan disposition](docs/plans/set-based-execution_2026-11-21.md) · [Development revision](docs/plans/set-based-execution/cutover-and-qualification.md#native-revisions)

## Current owners

- [Set-based execution](docs/plans/set-based-execution_2026-11-21.md) owns package disposition. The [post-SBX-09 amendment](docs/plans/set-based-execution_2026-11-21.md#post-sbx-09-review-amendment) integrates both follow-up reviews through SBX-22. The [efficiency amendment](docs/plans/set-based-execution_2026-11-21.md#validation-postgresql-efficiency-amendment) and [columnar amendment](docs/plans/set-based-execution_2026-11-21.md#columnar-redesign-amendment) retain the earlier review dispositions.
- [ADR-0154](docs/adr/0154-sbx-columnar-populations.md) and the [common analytical basis](docs/plans/set-based-execution/common-analytical-basis.md#columnar-population-target) own the Arrow carrier, DuckDB relational work, retained populations and protected PostgreSQL transfer. [ADR-0155](docs/adr/0155-pdf-producer-custody.md) owns the mode-specific PDF capture and recognition custody.
- [Domain Model Operability](docs/plans/domain-model-operability_2026-11-20.md#completion-and-handoff), the [test-domain coordinator](docs/plans/test-domain-model-and-execution_2026-11-17.md#implementation-evidence), and [library-discovery tooling](tooling/docs/plans/library-discovery-tooling_2026-11-17.md#current-state) retain their existing scopes.

## Last verified

- **Passed · 2026-11-24.** `uv run ci model change deploy cfbc6545a5dc40d882bce2f7f5e56a69` installed the successor (deployment `80af79f0728849dd89d68adb8b735406`). `uv run ci db status --maintenance` confirmed the installed and registered head. `just model check` matched released projections. [Native revision effects](docs/plans/set-based-execution/cutover-and-qualification.md#native-revisions)
- **Passed · 2026-11-24.** `uv run ci check --view steps` passed applicable checks (`88ad07c9bfc5408daa70c1533bb6d036`, `rustc 1.102.0-nightly bdf712ee8`). [Native revision effects](docs/plans/set-based-execution/cutover-and-qualification.md#native-revisions)
- **Passed by selected identity · 2026-11-24.** Private serial `uv run ci test --native-host private --workers 1` covered protected partitions, enrolled cross-source freshness, measured paging, typed archive replay, publication-time revocation, and cached-dossier authorization. The final independent withdrawal check passed (`123fbecd16c1411fbf08737cc6969726`). [Read and evaluation checkpoint](docs/plans/set-based-execution/owner-resolved-reads.md#sbx-through-13-checkpoint)
- **Passed by selected identity · 2026-11-24.** `uv run ci test --native-host private --providers-only --workers 1` passed genuine observed-premise annotation, D1 export and detached replay (`1d39812b1acb4c4aaf67dcea6908edd1` by identity), and genuine whole-block scoring (`b4266ce9474f45b9a1fd1fbf0bfc913a`). D1 selected export took 5.0 seconds and verification and replay took 38.0 seconds on the fixture. [Read and evaluation checkpoint](docs/plans/set-based-execution/owner-resolved-reads.md#sbx-through-13-checkpoint)
- **Passed by selected identity · 2026-11-24.** Private native checks covered captured-policy reconstruction, sparse and combined formula and visual reads, and byte-retaining new-build adoption. Genuine Docling recovery and pinned Chandra page 151 confirmed the selected-file and visual custody routes. [PDF checkpoint](docs/plans/set-based-execution/pdf-path.md#sbx-through-16-checkpoint)
- **Passed · 2026-11-23.** `uv run ci db init` recreated the development database empty on the verified sole SBX-09 root. The accepted ordinary, independent provider and shared fault results remain with the cutover owner. [Reset and baseline acceptance](docs/plans/set-based-execution/cutover-and-qualification.md#development-reset-through-sbx-09)

## Remaining scope

- [SBX-17](docs/plans/set-based-execution/pdf-path.md#sbx-17) owns the typed PDF certifier and retirement of duplicate storage. [SBX-18/19](docs/plans/set-based-execution/kernel-trial.md#sbx-18) owns the complete analytical job and scoped-relations trial.
- Stage installation belongs to [SBX-20](docs/plans/set-based-execution/cutover-and-qualification.md#sbx-20). The final retirement and whole-book campaign belongs to [SBX-21/22](docs/plans/set-based-execution/cutover-and-qualification.md#sbx-21).
- The full repository-wide `uv run ci test` campaign is `not_run` at this checkpoint. The [older interrupted campaign](docs/plans/set-based-execution/cutover-and-qualification.md#sbx-09-qualification-pause) retains its original results and staged fixture custody.
