# Status

_Updated 2026-11-13. DDO audit repairs and DDO-03–05 implemented; native qualification remains open. No production cutover._

## Authority and current scope

- The [DDO coordinator](docs/plans/declared-data-operations_2026-11-12.md#audit-repair-execution--2026-11-13) owns package state, five completion-audit findings and acceptance. The current execution closes those findings and remaining DDO-03–05. DDO-06–12 retain their broader obligations; this checkpoint does not conclude the approved scope.
- [ADR-0100](docs/adr/0100-ddo-contextual-identities.md) governs qualified subject context through bindings, requests and products. JSON scope numbers retain exact decimal meaning; bool/string/null remain distinct. Typed parameter/body meanings and historical frozen encodings stay unchanged.
- Source reflection/escape and typed input provenance now withhold unsafe reusable recipes. Generated dataclass acquisition authenticates constructors, defaults/factories, standard methods and transformed class fields. Unsupported nominal receiver dispatch remains explicit unknown.
- Typed streams, prepared family/resource ownership, declared successful outcomes and acquired receipt-bearing publication commands are integrated. The four required immediate consumers hydrate exact pinned native selections. Actual provider qualification is distinguished from controlled adapter checks.
- Native replay serialization, purpose guards, contextual identity, selected graph authentication, support rebind/recovery and discovery/closed fan-in are implemented. Lost-all-claims batch work enters physical bounded retirement while useful siblings continue.

## Last verified · 2026-11-13

- **passed:** `uv run ci test --workers 2 --json --` scoped source/compiler/identity/binding/ports/planner/CPU/activity union, 296/296, `b0a886ec084441fab287c5b2644f0786`. Later local typing-only changes passed Pyrefly; native SQL correction is separately qualified below.
- **passed:** the scoped five-family suite through the same test route, 57/57, `bfe48e3b290748e091f3cf2b296bdf13`, including actual spaCy and canonical CPU controls. HanLP controlled behavior is not an actual-provider pass.
- **passed:** `uv run ci check --only types --json`, `d28d13b3ce5e479a984c04bb75f416c4`; `uv run ci doctor --json`, `6b86f461dfd3459da01af5e872e30ae2`. Direct pinned `python-rapidjson==1.25` preserves exact DDO JSON scopes without changing global database adapters.
- **failed:** native union `bc8830741008498da5f364caec09166f`, interrupted after common demand-registration SQL precedence failure (109 required, 2 passed, 20 failed; remaining unrun). Corrected source predicate **passed 7/7** real PostgreSQL controls, `d637175a193b4c9595392ebf8c90caac`. Full native replacement remains open.
- **failed:** `uv run ci check --json`, `6e1ffae4a75b42ee9e1a4946a1339ac7`, only ADR/docs links. Repaired binding references: **passed** ADR lint `0d351b1d3a7645abacca2fe8a721b0f5` and docs `e0e89b31d0b44cc4b60dc3685c8fe905`. Evidence check **passed**, `1da7f7f8ef8c4231861e0f0042a4f559` (zero errors, 42 historical warnings). Final documentation/check reconciliation remains due.

## Native custody and next action

- [Archive authoring evidence](docs/design_review/evidence/2026-11-13_ddo-archive-composition/README.md) owns the exact authoring/registration chain. The invalid never-deployed archive-v1 bytes remain preserved outside active Alembic discovery. V2/v3 apply cleanly; their deferred runtime query errors are corrected by normal successor `semantic_ddo_archive_v4`.
- V4 preview `ad0a9ebb043b4e2aa6f034819c87956b`, rollback-only candidate `b725cb7122424cdc8bc6bb0e458f3849`, registration `aa6793ea4ce64363b768d699fe0d2180`: **passed**. Desired DDO PL/pgSQL functions were actively checked; frozen files remain unchanged after registration.
- Persistent `corpus_structure_dev`/OID25921445, PostgreSQL18/corpus port5434/system7701811359771751232, stays at `semantic_bep_located_v2`. Registration and isolated tests are not deployment or activation; DDO-11 owns adoption/preservation.
- **passed:** critical native/production selection, 7/7 (six genuine native journeys and one preparation control), `78a4a3930af741adb9f2e40f51043418`. Covers atomic/overlapping replay, exact fractional context, null-root product binding, discovery/closed fan-in/resume and unchanged production callable execution/resume. Wire/preparation **passed 50/50**, `dfac6b0e387049d19d0629fc0a71fc4c`; current binding/authoring/boundary controls **passed 73/73**, `f7fe163768034b33ba2ae3014652b2ec`.
- **passed:** `uv run ci check --json`, `0b4fd0a8679b442287303c34e89a7ee4`, including typing, lint, docs, dependencies and Clippy. Later documentation updates need their final publication check. Working-database extension metadata confirms transactional plpgsql_check was not left installed.
- **Running:** complete native/protocol/adjacent-control union, `0aaa980a87bc415f8c6c682ebacd2214`. Source is frozen; diagnose any failure, retain the original receipt, and reconcile actual selected scope/final context before closing findings or DDO-03–05. Earlier v2/v3 runtime failures remain preserved.
- Reconcile coordinator/companions and findings only against final applicable evidence, update this checkpoint, run root `just turn-end` and final applicable checks. No broad DDO-12 provider/book/fault completion is claimed.
- Worker branches are integrated and clean; native/ports/family worktrees remain for cleanup after qualification. Concurrent test-audit work and untracked test-system-target plan files are preserved. No push.

## Test system: audit, review and plan · 2026-11-13

- **Published, documentation only; nothing implemented.** The [test audit](docs/design_review/test-audit/README.md) was refreshed (`28b4a53db`, DTA-031–036 added, durations read from stored results). The [test system target design review](docs/design_review/reviews/design_review_test-system-target-design_2026-11-13.md) (`89440372a`, Revise) supersedes the 2026-11-12 test review. The [test system target design plan](docs/plans/test-system-target-design_2026-11-13.md) (`4434b0bcc`, TS-00–23, Proposed) owns scheduled disposition of DTA-001, 006, 009, 018, 024–036 and F01–F05.
- **Operator decisions recorded in that plan:** RC01–RC04 accepted (ADR-0032 and ADR-0048 successors are TS-00's work and are not yet written); narrow verified deployment key; once-per-process implementation snapshot; no-unfinished-task seed rule; enforced reader and shared-clone engines.
- **Owed to the DDO owner** (the plan's handovers list): the RC03 correction to the contracts companion, gating DDO-06–12 on TS-21/TS-22, and landing TS-05/06/17 before DDO-06 adds native tests.
- **passed:** `uv run ci adr lint`, `uv run ci docs check` (1,233 canonical pages) and `just turn-end` at `4434b0bcc`. **not_run:** `uv run ci test`, `uv run ci check`; no product or test source changed.
- **Next:** TS-00 (two superseding ADRs with D3, DESIGN and D9 §4 amended), then TS-01 and TS-03 in parallel. Implementation needs separate authorization.
