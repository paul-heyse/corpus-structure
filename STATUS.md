# Status

_Updated2026-11-11. BEP-07/08 implementation and final BEP-09 qualification are in progress.
D1 remains CUDA/BF16; all other selected NLP remains CPU. Native head is
semantic_bep_capacity. Default activation, project result selection and TC plans are unchanged._

## Current implementation and authority

- [BEP coordinator](docs/plans/book-processing-efficiency-and-parallelism_2026-11-11.md) owns current scope, findings, investigations and required union. Its final-increment section records selected operating values and actual receipts. Existing BEP-00–06 scoped acceptance remains there.
- ADR-0087 and D3/D4/D6/D8 own shared validated policy, native demand anchoring/recovery and coherent capacity. The first actual stage owns the frozen demand/freshness seed; children reference its anchor. CLI exposes retained capture and explicit characterization resume.
- Defaults: two regions/CPU workers/submissions/stage runs, four claims, two jobs per provider lane,2GiB encoded state,256MiB CPU packets/64MiB replies; native IPC remains8MiB. CPU native threads1, provider threads4/inter-op1. GLiNER's frozen profile must match; inter-op1 is supported.
- Native canonical layer/full-layer bounds are64MiB; views remain64MiB and each aggregate native read response is bounded256MiB, with exact closure paging. Execution bodies remain charged to regional capacity. Ordinary analytical digest/ancestor/claim scopes now own bounded lifetimes.
- D1 always CUDA/BF16 with120s inference and no CPU fallback. Other selected NLP stays CPU. threadpoolctl3.7.0 was added exactly to the three PM2 CPU service environments for supported loaded native pools.
- New current release03c24857dc91… is admitted/deployed, unselected. Target input is source:bep-book:03c24857dc91. Original capture496/cut614/product1627 remains the authentic316-view/518-page basis; no recognition was repeated.

## Verification2026-11-11

- [Capacity evidence](docs/design_review/evidence/2026-11-11_bep-layer-capacity/README.md): actual view480 complete13-family native body9,253,073bytes; largest-by-text561 complete13-family body49,326,509bytes. Both preserve exact source/context and independent current custody/digests. Original method1 body was not recovered.
- Native capacity publication/replay/export/paging/refusal controls passed6/6,c3df282f91704fa39257f7007f2c6862. Local recovery/anchor/policy/receipt controls passed13/13,4c0bdc4845e6429aa01e9e1cdb52ee0e. Primary-reader capacity controls passed10/10,4561837d285c4564ba2b94503fe6cf4f.
- Candidate bef94253783f46da9bcefcf8469deaad passed; registration7a1c10f3773c4e788510b9a10f1384da and development deployment7b6d0475a0244ad387dde1eaffb54e8e passed. No activation or selection occurred.
- Broad `uv run ci check --view steps --json` a71d30e25b81497aad78a82c82b2c57c passed lint/docs/deps/Clippy, failed only new test-stub typing. `--only types` replacement228fc0b8b1014655bbdd8b18684aad69 passed before the last analytical-lifetime correction. rustc1.102.0-nightly(9c5648833,2026-11-10).
- Native candidate recreation defect repaired in commit9f2f78c82; scoped regression passed. Original failures/refusals and intermediate check failures remain preserved. Final-source native recovery passed2/2,d30ed0edcc3a4ae1832aa32c6bdca97f; native analytical retry694783ed2487403fb6e08d01723a00ea passed. Final default functional/fault campaign and whole-book acceptance remain pending.

## Next

- Production source is frozen with native recovery/analytical controls passed. Run the default functional/fault campaign, remaining selected-provider union and final checks before book execution.
- Execute all316 retained views/all six stages, deliberately qualify interruption/resume preserving settled fresh pins, then verify final exact native/CLI/MCP/export/detached consumers. BEP-E01 final closure waits for that acceptance.
- TC plans remain unchanged; later TC reconciliation and protected assessment retain their existing owners. No new protected reference reads were used for policy or scheduling.
- Main is the sole worktree. Only the native-candidate repair is committed this increment; remaining integrated edits are dirty. No push, activation, selection or promotion.
