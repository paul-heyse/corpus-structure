# Assembled CLI operations target review

**2026-11-07 · design/target · Interface-checked.** Independent combined library and principle
review of `a41798432` under ADR-0069, core 3.3, heuristics 1.0, test assessment 1.2 and code
intelligence 1.4. The review inspected the installed routes and underlying owners. Its read-only
`just --dry-run test-all -q -k 'literal expression' python/corpus-structure/tests/test_cli.py`
showed the intended positional forwarding. Functional and provider checks were `not_run` in the review.

**Decision: Revise.** Typer, `just`, the test supervisor, managed custody and PostgreSQL make
suitable owners for the supported workload. The first assembled version lost part of their
authority when composing operations. A1–A3 fail at the following ownership boundaries. A4
remains unresolved for integrated qualification. Local leases and the native transaction route
are still proportionate to the single-host use.

| Finding | Observed gap and required correction |
|---|---|
| F01 · Custody | Pending candidate and named receipt dependencies did not reach the hold owner. A published classification could still describe a surviving child. Protect pending work and distinguish settlement from outcome for both Python and Rust. |
| F02 · Approved input | Candidate construction could rebuild changed pack inputs after preview. Bind the reviewed release to the preview and verify it before authoring and again before deployment. |
| F02a · Native effect | The authoring and deployment endpoint were a single binding. Native authoring needs the development database and the committed effect needs its own declared target. The migration owner needs an explicit frozen wrapper registration step. Keep direct migration bounded to development and explicit recovery. |
| F03 · Test dispatch | A display-only suffix could narrow qualification. Retry selection did not surface changed source or tool context, used a different collection environment and could start a second lane after interruption. Reuse the selector and managed environment policy, and stop on incomplete settlement. |
| F04 · Read authority | Source inspection obtained a reader after startup had already acquired a writer. Acquire writer authority for queue work and allow pure reads to start with only reader credentials. Apply the reader to status and task listing. |
| F05 · Replay identity | Numeric run and cut IDs could resolve in another database during retry. Bind the acquired database and immutable completed roots under the original snapshot, and verify that binding before replay. |

G1/G2/G3/G5/G6 and CI-G2 have corrections above. G7 depends on the final installed journeys
and applicable qualification union. G8 remains interface-checked for the selected mechanisms.
The [CLI plan](../../plans/cli-operations_2026-11-07.md#execution-disposition--2026-11-07) owns
all implementation and evidence dispositions. The [initial target review](design_review_cli-operations-target_2026-11-07.md)
established the original four correction areas. No new rule impact was identified.

## Completion audit repair assessment

**2026-11-07 · design/target · Tested in the stated development scope.** An independent assembled
inspection started from `e68623e26` and traced the repairs across CLI, managed test receipts,
Alembic, PostgreSQL and MCP. The assembled product qualification spans `107053d33` and the
affected fixes in `52623af68` and `562b3e49e`.

| Scenario | Integrated judgment |
|---|---|
| A published test directory has a substituted member, or an interrupted lane lacks an authoritative collection | The result owner authenticates the published entry. The supervisor opens receipt members without following links. Coverage retains missing required lanes and records which candidate supplies a valid collection. Recovery distinguishes process settlement from exact retry eligibility. |
| A physical declaration is changed through preview and a later candidate executes on an explicit target | The proposed physical closure determines both the reviewed release and candidate admission metadata. The migration adapter verifies and stages the exact wrapper bytes at a private path. A stale checkout bytecode cache cannot supply those bytes. Native fixtures exercised interruption, retry, role and target refusal, and separate activation. |
| The same installation reads retained corpus knowledge, loses a supervisor, or receives SIGTERM during export | Pure tools use reader authority. A dedicated PostgreSQL session records active custody or intentional handoff. A missing lease with retained active evidence identifies an orphan. Review retry requires exact selection, acquired source and settled predecessor. |
| Host, output and fitting prerequisites differ | Host status reports unhealthy exit. Safe settings and diagnostics preserve caller meaning. Fitting availability names the missing prerequisite and its owner before starting a fit. |

A1–A3 follow the stated owners in these scenarios. A4 fits the single-host workload through compact
managed summaries, short reader snapshots, a dedicated supervisor connection and rollback-only
native authoring on the working database. The applicable G7 evidence is reconciled in the
[CLI plan](../../plans/cli-operations_2026-11-07.md#repair-verification--2026-11-07). Live production
G7 evidence is `blocked` on configured target and effect authority. No new rule impact was identified.
