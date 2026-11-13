# Status

_Updated 2026-11-13. DDO-03–05 partial implementation closeout: integrated, targeted qualification passed; functional scope remains open. DDO-00–02 retain their completed foundation boundary. No production cutover._

## Current authority and implementation

- The [DDO coordinator checkpoint](docs/plans/declared-data-operations_2026-11-12.md#ddo-0305-partial-implementation-checkpoint--2026-11-13) owns integrated behavior, exact verification, repaired failures and remaining functional obligations. Supporting contracts, products/support, demand, graph and implementation-profile pages link to that one owner.
- Implemented foundations include typed Core/native binding semantics, scalar pure direct Python ports, generated closed native/wire contracts, explicit target preparation/archive/runtime paths, native products/support/requests/fenced intents/publication/revocation/pinned reads, and frozen-demand planning. These are bounded primitives; DDO-03–05 are not claimed complete.
- Forward migration `semantic_ddo_kernel_v1` is registered. Tests install the real frozen migration and use normal target catalog admission; the former test-only acquired-candidate bypass is removed. The candidate CLI reuses the exact production-authored admission, avoiding redundant regeneration after row-type scaffolding rollback.
- Legacy completion, consolidation, source-frame, agent packet, listing and proposal reads now project their consumed task fields. Generated calls preserve required legacy result fields with explicit nullable-row refusal. Selected legacy producers/readers remain until their coordinated replacement.
- ADR-0092–0095 and D1–D8 remain the accepted target authorities. Multi-package F01–F14/C1–C7 and source-review obligations remain open with the coordinator; targeted primitive passes do not establish production replacement or DDO-12 completion.

## Last verified · 2026-11-13

- **passed:** `uv run ci test --workers 6 --json --` with the coordinator's exact 28-path union: **442 selected / 442 passed**, `e332a3ef0884454988beaad5af1166b7`. [Durable receipt](docs/design_review/evidence/2026-11-13_cli-e332a3ef0884454988beaad5af1166b7/README.md). Includes real PostgreSQL migration/admission/permission/fence/replay/revocation/snapshot controls and affected legacy/CLI/archive consumers; no provider-model pass.
- **passed:** `uv run ci check --only types --json` `4648e4089fc842c7a111ddb8ada13753`; `uv run ci check --only lint --json` `237f6a6ef87d444a8d646becaffdb335`. Outputs retained durably. Source was formatted before the final union; subsequent receipt/documentation edits do not alter those production/test bytes.
- **passed:** final rollback-only candidate `b0a0b07c907144eab227f891ba28caab`, preview `f500ce98465a4260845d5772d2e0db53`, registration `2ae5b1b7cd7e420fb21d700cb03f0c25`. `ci model change inspect-candidate` verifies registration and dependency availability. Candidate and preview are held for pending DDO-04/11 consumption. The [native receipt](docs/design_review/evidence/2026-11-13_ddo-native-kernel/README.md) records exact sources/hashes and no table/column drops.
- **passed:** `uv run ci db status --maintenance --json` observes persistent `corpus_structure_dev` still at `semantic_bep_located_v2` (repository head now `semantic_ddo_kernel_v1`). No persistent migration, deployment or activation occurred; candidate authoring rolled back and native qualification used isolated test databases.
- Earlier failed unions and worker crash `8faf0c6270ff448aba560dfe137d5fcc` are preserved with their original scope and incomplete crash reporting. The exact crash node passed on retry and in the final union; its cause remains unknown. The coordinator records repairs and evidence limits.
- **passed:** root `just turn-end` (1189 files unchanged), `uv run ci docs check --json` `9e7cd45393344cf59db1defeb34545e3` (zero link errors), and `uv run ci evidence check --json` `f236f0e888dc4099bff1d3bb92cc3d95` (zero errors, 42 historical warnings). Commit `c2da716c6` preserves qualified production/test bytes; later updates are receipt/documentation only.
- Broad series/provider/book/fault qualification: **not_run**, because functional scope remains open. DDO-12 owns final assembled qualification. Original foundation receipt `9d485175a11e44018135cf84b59c7a29` retains its original date/scope, not additional final-source credit.

## Next and preserved boundaries

- Resume the [remaining functional scope](docs/plans/declared-data-operations_2026-11-12.md#remaining-functional-scope-and-next-execution): invalidated retained-intent generation recovery, real consumer/discovery/fan-in/frontier integration and remaining adapter capability profiles. Persistent adoption requires reacquired exact candidate/source/target bindings and DDO-11 custody; registration is not deployment.
- DDO-06–12 remain open. Provider/staged-artifact/independent-strength and unsupported schema/profile capabilities refuse until their actual owner admits them; no implicit fallback substitutes for the required contract.
- Old `0a78c71ce1a949e38e906c9c5392c1f3` remains held/unsettled. Original source/reference/evidence remains protected; no memory/BrokenPipe cause is established.
- All worker assignments are concluded. All three implementation worktrees/branches were merged and removed; only main remains checked out. No push. Operator NetworkX edits and untracked Astroid/griffe/ty reference documents remain untouched/uncommitted.
