# Status

_Updated 2026-11-13. DDO execution paused at the operator's request. Implementation integrated; qualification incomplete. No production cutover._

## Authority and scope

- The [DDO coordinator](docs/plans/declared-data-operations_2026-11-12.md#audit-repair-execution--2026-11-13) owns package state, five completion-audit findings and acceptance. Authorized scope is those repairs and remaining DDO-03–05; their acceptance and broader DDO-06–12 remain open.
- [ADR-0100](docs/adr/0100-ddo-contextual-identities.md) governs complete project/subject/original/scope identity. Exact decimal JSON scope meaning is preserved; typed body/parameter encodings remain unchanged.
- Source reflection/escape qualification, generated dataclass runtime authentication, typed pull streams, prepared-family ownership, declared outcomes and receipt-bearing commands are integrated. Four immediate consumers hydrate exact pinned native selections.
- Native replay serialization, purpose guards, contextual products, selected graph authentication, discovery/fan-in and support rebind/recovery are integrated. All-lost batch claims cause bounded physical retirement; native stream execution remains DDO-06.

## Last verified · 2026-11-13

- **passed:** `uv run ci check --json`, `ef31917fa4ae44cca9aad5b7ae96d0f1`, all applicable repository checks. Source `561634814`; Rust `rustc 1.102.0-nightly (9c5648833 2026-11-10)`.
- **failed:** v4 native union `0aaa980a87bc415f8c6c682ebacd2214`, 129 passed / 13 failed, retained. Source fixes address trust maps, PDF SQL ambiguity, incomplete product uniqueness and retired-attempt attribution; typed test inputs now reach intended guards.
- **passed:** repaired planner/population/graph/purpose controls, 10/10, `8dc2c54a9a8f44cfa38f40302d5eec15`; trust SQL, 19/19, `cdbe882e2f2547c9873dd82ab6ea6b27`; PDF guard checking/restoration, 1/1, `b452c14cf5cd439f8f8e4b3afe7b1720`. These are bounded controls, not final union credit.
- Earlier source/ports/CPU 296/296, prepared families 57/57, wire/preparation 50/50 and binding/authoring 73/73 receipts remain in the coordinator. Actual spaCy/canonical controls and controlled HanLP checks retain distinct meanings.
- **failed due to operator-requested interruption:** `uv run ci test --workers 4 --json --` the final 51-file union, `2a1fdebfd77749378ce7d4598cba5d68`, source `561634814`: 651 selected, 452 passed, 195 not_run, 4 incomplete. Owned pytest stopped; supervisor custody settled/drained. Receipt held and retained. No replacement is running.
- **passed, pause documentation:** `uv run ci docs check --json`, `26378fcaf892417c81f899044ed6d6c1`; `uv run ci evidence check --json`, `39ad27ce735449d38b59a5849a235286` (zero errors, 42 existing warnings); root `just turn-end` (no source changes). Functional qualification remains incomplete.

## Native custody and next action

- [Archive authoring evidence](docs/design_review/evidence/2026-11-13_ddo-archive-composition/README.md) owns exact artifacts and failed attempts. V5 preview `f85b42104df544b68c292fc3e9e0c9b7`, rollback-only candidate `fa5eaba6351647c581bfec47520baac5`, registration `140d3537f7014c2786f42815cb9ba27e`: **passed**. V2–v5 stay frozen; rejected never-deployed v1 bytes stay preserved outside active discovery.
- Persistent `corpus_structure_dev`/OID25921445, PostgreSQL18/corpus port5434/system7701811359771751232, remains `semantic_bep_located_v2`, checkout head v5. `ci db status --maintenance` confirmed this; direct read-only extension metadata confirms no retained plpgsql_check installation. Registration/tests are not deployment or activation.
- **Paused. Resume only when the operator asks.** Next: `uv run ci test retry 2a1fdebfd77749378ce7d4598cba5d68 --lane ordinary --workers 4 --json`, then `ci test coverage` with the original and retry IDs. Reconcile all 651 required identities and final source/context before closure; reassess affected evidence if implementation/environment changes.
- Keep DDO-06 native streams, DDO-07–10 cutovers, DDO-11 adoption and DDO-12 provider/book/fault qualification open. Clean worker worktrees remain for cleanup after qualification. Concurrent test-system work and operator AGENTS.md edits are preserved. No push.

## Test system: audit, review and plan · 2026-11-13

- **Published, documentation only; nothing implemented.** The [test audit](docs/design_review/test-audit/README.md) was refreshed (`28b4a53db`, DTA-031–036 added, durations read from stored results). The [test system target design review](docs/design_review/reviews/design_review_test-system-target-design_2026-11-13.md) (`89440372a`, Revise) supersedes the 2026-11-12 test review. The [test system target design plan](docs/plans/test-system-target-design_2026-11-13.md) (`4434b0bcc`, TS-00–23, Proposed) owns scheduled disposition of DTA-001, 006, 009, 018, 024–036 and F01–F05.
- **Operator decisions recorded in that plan:** RC01–RC04 accepted (ADR-0032 and ADR-0048 successors are TS-00's work and are not yet written); narrow verified deployment key; once-per-process implementation snapshot; no-unfinished-task seed rule; enforced reader and shared-clone engines.
- **Handovers reconciled by source inspection, 2026-11-13:** the DDO coordinator and contracts companion already record RC03, TS dependencies and retirement owners; the test plan's corresponding handover text needs reconciliation during revision.
- **passed:** `uv run ci adr lint`, `uv run ci docs check` (1,233 canonical pages) and `just turn-end` at `4434b0bcc`. **not_run:** `uv run ci test`, `uv run ci check`; no product or test source changed.
- **Improvement review published, Proposed:** [shorter focused and full test runs](docs/plan_improvement_reviews/test-system-target-design_2026-11-13.md), I01–I11. Priorities are useful-clone/targeted verification, preparation keys, effective affinity, deferred CLI imports and reused DDO setup, with preserved binding/receipt evidence. Plans and production source remain unchanged; duration gains are unmeasured.
- **passed, 2026-11-13, review publication:** `just turn-end`, `git diff --check` and `uv run ci docs check`, `2152cd9ac598460caa45712fe1d4454c` (1,243 canonical pages, zero link errors). **not_run:** product/native/provider tests and `uv run ci check`; documentation only.
- **Next for test-system work:** select amendments and revise the plan from that review when instructed. The existing queue still starts with TS-00, then TS-01/03. No implementation or product qualification is claimed by this review.

## Agent reference guidance · 2026-11-13

AGENTS.md now describes optional Context7 use for implementation approaches, examples and options,
with query framing and version awareness. `uv run ci docs check` **passed**, `0c4f263917dc452389bbdb682632c7d3`.
Product tests and whole-repository checks are **not_run** for this documentation-only change.
