# Status

_Updated 2026-11-10. Stopped at the operator's request. Development runs
`semantic_tc02_reachability`; `/10` remains default and the project is unselected._

## Current work and authority

- [Text-characterization checkpoint and bulk continuation](docs/plans/text-characterization_2026-11-10.md#stopped-checkpoint-and-bulk-continuation) owns TC-00–02 acceptance and the remaining work. TC-00 authority is complete; TC-01/02 source is implemented, with acceptance incomplete. TC-03–11 remain planned.
- ADR-0081 and D1/D2/D3/D4/D6/D8 retain the enriched-document target: full native document plus immutable identified layers. Each layer retains its original release authority, bytes, pin and provenance; a new rule release can consume old evidence under authenticated archived contracts.
- [Model/retention](docs/plans/text-characterization/model-and-retention.md#delivered-foundation-and-integration-boundary) documents executable contracts, publication, indexed reads, ordinary composition, CLI/MCP and detached replay. No NLP producer, provider efficacy, consumer cutover or full-book qualification is delivered by this checkpoint.
- [Native evidence](docs/design_review/evidence/2026-11-10_text-characterization-native/README.md#stopped-checkpoint--2026-11-10) records all actual deployment effects and preserved failures. Five frozen forward migrations remain authoritative; never rewrite or delete them.
- Latest deployment `b7f9e471e81644fe85769cdd12069d09` passed migration/archive/admission/verification at `semantic_tc02_reachability`. Admitted release is `release:c921ad244b60d4e79556a9042f102936a6d58c853c9c14f9c902c30bbfaca0e2`; native correspondence passed. No activation, promotion or project selection occurred.
- All agent edits are in the shared `main` checkout. No parallel worktrees or background tests remain. Implementation stopped; the pending corrections are not treated as verified closure.

## Last verified · 2026-11-10

- `uv run ci test --json -- python/corpus-structure/tests/semantic/test_characterization.py` **passed**,35 cases, `6aa79d64479e4f608f33b6c87e0419cd`: source/pin/format invariants, exact scores, DAG/choices and original-release authority.
- `uv run ci test --json -- python/corpus-structure/tests/methods/test_characterization_composition.py python/corpus-structure/tests/semantic/test_characterization_replay.py` **passed**,28 cases, `abcf7a3130e64a31982f18aac223e0f2`: composition and authenticated per-release detached contracts. This does not establish the pending native cross-release path.
- `uv run ci test --json -- python/corpus-structure/tests/semantic/test_characterization_native.py` **failed**, `3f98a01daa9b4059ad066da42ca6c2f7`: seven selected, four passed and three failed. Passing controls include protected publication/refusal, shared DAG/cycle checks, and unfinished-run live/detached capture with real page3/4 membership.
- `uv run ci test retry 3f98a01daa9b4059ad066da42ca6c2f7 --lane ordinary --json` **interrupted**, `0a008697b02d4616b51f71a57133536f`: canceled and drained to exit130 at the operator's stop; three unresolved nodes remain.
- Strict receipt JSON decoding and a distinct R2 fixture realization id are implemented but **unverified**. Ordinary compose completion, joint layer/view completion and cross-release new-rule/view/capture remain open in the coordinator.
- Prior endpoint `uv run ci check --only types --view steps --json` **passed** `a7a9d8f8de66406a84cc6ac1016c5e8f`; lint **passed** `03aae453519147f0ac76423bc24a963b`. These predate the final receipt/fixture corrections. Full `uv run ci test` and `uv run ci check` are **not_run** for this scope.
- `uv run ci docs check --json` **passed** `7f42cbca4b54472e8a0bced214cc8339`,869 canonical pages/zero link errors; `just turn-end` **passed**. These are documentary/maintenance evidence, not product qualification. No new NLP/provider invocation, model fitting, benchmark or full-book run occurred.

## Preserved adjacent scopes

- [CLD final acceptance](docs/plans/cli-and-logging_2026-11-10.md#final-acceptance) retains its earlier6033-identity qualification and source boundary. [DMC acceptance](docs/plans/domain-data-model_2026-11-10.md#completion-repair-acceptance) retains its earlier5882-identity qualification. Neither receipt recertifies the changed TC tree; their disposition owners and original failures remain unchanged.
- [PM2](docs/plans/production-milestone-two_2026-11-08.md#post-audit-execution-checkpoint--2026-11-09) retains run487/cut604 and its own replay/comparison/selection work. [WCE](docs/plans/witnessed-corpus-enrichment_2026-11-05.md#repair-disposition--2026-11-07) retains source/factor repairs and bounded receipts. No other implementation plan was edited for TC execution.
- [Functional review](docs/functional_reviews/text-characterization_2026-11-10.md) and [spaCy/Lark feature collection](docs/library_leverage/libraries/text-characterization/briefing.md) remain the TC target/mechanism basis. Their wider O01–O07 obligations stay open with the TC series.

## Next

On resumption, address the remaining completion/fixture/cross-release paths together, then run
one coherent native and directly affected functional selection. Preserve failed/interrupted
receipts; only after the package passes run final maintenance and the full applicable test/check
union. Follow the coordinator's bulk continuation; do not start TC-03 or claim TC-02 complete.
