# Status

_Updated 2026-11-11. TC-03–09 and their TC-01/02 prerequisites are implemented in shared `main`.
Native head is `semantic_tc03_09_literals`; `/10` remains default and the project unselected._

## Current scope and authority

- [TC coordinator](docs/plans/text-characterization_2026-11-10.md) owns package acceptance, O01–O07 and producer-review F01–F04. Authorized TC-03–09 functional scope and prerequisite integration are complete; TC-10/11 independent semantic assessment and full-book qualification/adoption remain planned.
- ADR-0081/0082 and D1/D2/D3/D4/D6/D8 own the implemented enriched-document contract: the full exact native document, immutable positioned layers under their original released contracts, and explicit active analyses distinct from retained dependency closure.
- Delivered six primary stages: native linguistic evidence, positioned formal evidence, constructions, contextual evidence, eight-family model characterization and one contextual evaluator. Analytics reads their exact retained outputs; old duplicate recognizers and SQL language production are retired.
- Default capture/characterize/consume and demand reuse, typed native admission, indexed live/detached reads, analytical export closure, exact determinants/provider costs, zero-text coverage and bounded provider residency are integrated.
- [Integration evidence](docs/design_review/evidence/2026-11-11_text-characterization-integration/README.md) retains frozen forward migrations, failed receipts and final applicability judgment. Release `81dd8c0986138654fe434c1742072585ed968d70a4973961b6e89aa6e2713371` is deployed privately; no activation, promotion or project selection occurred.
- Work uses the shared `main` tree; no parallel worktrees remain. Implementation is committed as `e9025e949`, with independent SQL inspection repair `088cf9fdd`; this checkpoint accompanies the plan/evidence handoff commit. No push occurred.

## Verification · 2026-11-11

- `CORPUS_PM2_NATIVE_TEST_ASSETS=/home/paul/corpus-structure/build/models/pm2 uv run ci test --json`: **failed**, `71e97b485e59479b80b9d5e086f48570`; ordinary: 6,399 selected/6,394 passed/four failed/one blocked; fault: 8/8 **passed**. Rust **not_run**, zero selected; rustc1.101.0-nightly (2d20b42b8 2026-11-04).
- `CORPUS_GLINER_DIAGNOSTIC=1 uv run ci test --json -- python/corpus-structure/tests/methods/test_contextual_characterization.py python/corpus-structure/tests/methods/test_m1_review_repairs.py python/corpus-structure/tests/semantic/test_analysis_resources.py python/corpus-structure/tests/methods/test_gliner.py`: **passed**,82/82, `2e2d74eb026b42b78068d523ce6ca5da`, including the actual opt-in diagnostic.
- `uv run ci test coverage 71e97b485e59479b80b9d5e086f48570 2e2d74eb026b42b78068d523ce6ca5da --view unresolved --limit 20 --json`: **covered**,6,407/6,407 required identities, zero unresolved/missing lanes/unknown contexts/unsettled attempts. The coordinator judges the three test-local double repairs and scoped native-binding difference applicable; product bytes were unchanged. Original failures remain held, not relabelled passed.
- `uv run ci check --view steps --json`: **passed**, `16c68b4634774b619f59110c779a85a2`; empty rule lanes **not_run**. `uv run ci docs check --json`: **passed**, `45a282ed4379434d84d4a2dbda836824`,872 canonical pages and zero link errors. Earlier publication failure and anchor repair remain in the integration evidence.
- `just turn-end`: **passed**; maintenance left all1108 Python files unchanged. Later receipt-only prose changes do not alter qualified product source.
- `uv run ci doctor`: **passed**, `865caaa0e1014f2fa0e38a23177df4bf`. A transient pinned-wheel metadata timeout used the existing locked cache offline; no dependencies changed.

## Next

TC-10 authors independent source/output expectations and assesses semantic quality. TC-11 then
accounts for all 518 physical textbook pages, selected family coverage and adoption effects under
its separate execution authority. No measured quality, performance or English-completeness claim
follows from the completed implementation's functional checks.
