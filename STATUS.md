# Status

_Updated2026-11-11. Testing cancelled by the operator after Cursor/Codex memory-pressure crash.
No tests or book processing may restart without renewed instruction. BEP-09 remains incomplete._

## Current implementation

- [BEP coordinator](docs/plans/book-processing-efficiency-and-parallelism_2026-11-11.md) owns current scope, findings, receipts and required union. BEP-07/08 is implemented with scoped native checks; final campaign/book qualification is incomplete. TC plans are unchanged.
- Commits:9f2f78c82 (native candidate recreation),4ec2020fa (ADR-0087/shared policy/native recovery/capacity/threadpoolctl3.7.0),a040ac996 (raw summaries through LFS; artifact bytes unchanged). Main is the sole worktree; no push/activation/result selection/promotion.
- Defaults: two regions/CPU workers/submissions/stage runs, four claims, two jobs per provider lane,2GiB encoded state,256MiB CPU inputs/64MiB replies,8MiB native frames. CPU native threads1; providers4/inter-op1. D1 always CUDA/BF16/120s; all other selected NLP remains CPU.
- Native head semantic_bep_capacity; release03c24857dc91… admitted/deployed, unselected. Target input source:bep-book:03c24857dc91. Authentic source remains capture496/cut614/product1627:316views over518pages; no recognition rerun.
- First actual stage stores frozen native demand/seed; children reference its anchor. Retained capture/characterization resume use that authority. Full native layer/read cap64MiB, aggregate response256MiB/page, exact closure paging. Digest/ancestor/claim scopes own bounded analytical reads.

## Verified scope2026-11-11

- [Capacity evidence](docs/design_review/evidence/2026-11-11_bep-layer-capacity/README.md): actual complete13-family bodies9,253,073bytes (view480) and49,326,509bytes (largest-by-text561), independent current custody/digests. Original method1 body was not recovered.
- Native capacity publication/replay/export/paging/refusal passed6/6,c3df282f91704fa39257f7007f2c6862. Final-source native recovery passed2/2,d30ed0edcc3a4ae1832aa32c6bdca97f; exact analytical native retry passed694783ed2487403fb6e08d01723a00ea, with10preparation controls from73edf3d9b7394f22bbf25fb88e48c69b. Original failed attempts remain.
- `uv run ci check --view steps --json` passedecd5be13e49c43da8c1379b7d570dc24 (rules not_run: empty registry). `uv run ci doctor --json` passed8bf3d144537a4d268c202878b995cc05. rustc1.102.0-nightly(9c5648833,2026-11-10). Assembled review is Interface-checked, not native qualification.

## Interrupted campaign and next work

- Default `uv run ci test --json`,0a78c71ce1a949e38e906c9c5392c1f3, was interrupted in ordinary; fault not_started. Sixteen xdist workers were running. Bounded live observations showed at least29failures, not a complete final inventory. No full-campaign pass is claimed.
- systemd-oomd killed Cursor's application cgroup at23:47:43 local after167.1G group usage. Per-process attribution is unknown. PostgreSQL server is a separate service cgroup; last sampled test queries were reads/publication/runtime registration, not migration. Earlier development migration had finished. [Raw journal](docs/design_review/evidence/2026-11-11_bep-whole-book/raw/test-campaign-oomd.log).
- No pytest/test_receipts/ci-test processes were observed after crash; original parent already gone before requested SIGINT. `ci results recover` refuses unproven settlement; managed receipt still says running/custody_unsettled and is held. Do not manually relabel it or retry without resolving custody.
- BEP-E04 owns preflight-before-DB regression and affected settings/callback fixtures; not repaired yet. BEP-E05 owns aggregate test-memory diagnosis and dead-owner custody before a memory-safe, operator-authorized retry. Source workers are stopped; no testing/book restart.
- Whole-book execution, book interruption/resume, remaining selected-provider union and actual consumers/export/detached replay are not_run. Prepared consumer utility is unexecuted. BEP-E01 final book acceptance and BEP-09 remain open.
