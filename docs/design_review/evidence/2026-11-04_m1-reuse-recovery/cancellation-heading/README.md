# Actual heading-only M1 cancellation and recovery

**Tested · 2026-11-04. Cancellation fencing, child settlement and native125 new-run recovery passed.**
The original native124 recovery failure and initial native125 publication refusal remain retained.
This is a bounded functional journey on the actual retained Grinstead–Snell source and actual CPU
GLiNER child. It establishes no extraction-quality, all-family or complete-M1 qualification.

The frozen source baseline was `1e631ba7c9a6877d40a0eab7f6e81ddef0b4b99a`, native contract 124,
and release `release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd`.
During the original attempt, only scripts and receipts in this folder were written; runtime, tests,
plans and defaults were unchanged. No reference answers, evaluator outputs, grades or independent
author material were read. The separately authorized SQL-only forward repair was adopted as
native125; the semantic source release remained unchanged.
The coordinator owns acceptance and integration.

The scope was derived from actual run 14 metadata and the retained native section record, rather
than guessed: source view **22**, native section `#/groups/0`, **Chapter 5**, integrated product
`task=1`, `key=integrated`, digest
`e8ee2f72912fe174fdaf76918b7cb347ad245fecdf9c827688814729b9961cba`.
The typed `native_sections` scope sets `include_descendants=false`. The existing
`run_source_methods` API executed `source_graph("readings")`, cloning run 14's actual method
parameters, parent dependencies, source input realization/revision, corpus and guideline. Only
`extract.m1_candidates` was marked fresh. Parent threads=1, model threads=4. No PDF conversion,
OCR or source recognition was requested. PostgreSQL purpose principals used the existing dedicated
development database on port 5434.

Original native124 attempt (`attempt-001`):

| Check | Outcome | Actual receipt |
| --- | --- | --- |
| Resolve actual retained heading | passed | `source-inventory.json`, `inspect-source.log` |
| Observe actual owned child and cancel its run | passed | `attempt-001/events.jsonl` |
| Reject cancelled completion and settle child | passed | `attempt-001/cancellation-exception.json`, `cancellation-settled.json` |
| Refuse finalization of closed cancelled run | passed | `attempt-001/closed-finalization-refusal.json` |
| New run, identical frozen dependencies and scope | failed | `attempt-001.log`, `attempt-001/recovery-failure.json` |
| Recovery result publication | blocked: source-selection reuse defect | no output realization exists |
| Settlement and absence of cancelled source output | passed | `verify-settlement.log`, `attempt-001/settlement-verification.json` |

At 12:25:10.116 UTC, run **17** had candidate task **71**, attempt 1, holder
`semantic-source:17`, running on view 22. The observer saw the actual `native-gliner-cpu` child
PID **3644845**, parent **3643773**, `/proc` start ticks **5971795**. It called only
`cancel_bound_run(engine, 17)`: one task cancelled in **0.0436 s**. The child remained alive when
the cancellation API returned. The executor settled **17.927 s** later with
`OperationConflict: task attempt lost or run sealed`. The traceback shows the actual attempted
empty completion was refused by `ops.complete_task`, through the existing claim owner. Child
and parent were absent at final verification. Run 17 stayed cancelled with no result realization;
task 71 had no result digest, **zero `ops.task_result` rows** and **zero `kb.observation` rows**.
No pending/running/awaiting-agent owned tasks remain.

This observation proves cancellation during actual child startup plus durable completion fencing,
not immediate interruption of native inference. The existing claim renewal interval is 30 s;
this short source operation reached the completion fence before that renewal. The probe did not
observe an inference-start marker and makes no claim about which native family call was active.

Recovery run **18** used the **same dependency bytes and digest** as run 17
(`98e403962d354ef85cf87e90f676e1ed116971217702bbf1ca2171b910cc8d37`). Its retained-ingest task
**72** reused successful task **69** from run 17. Task 69 had selected existing source view 22,
whose actual native producer remains task 1. Run 18 nevertheless had zero source selections and
failed before creating another model child:
`SourceReadRefused: requested native section is unavailable: 'Chapter 5'`.

The source-selection owner explains this failure:
`python/corpus-structure/src/corpus_structure/semantic/sql/source_views.sql:150-151` joins the
reused origin's selections but also requires `v.native_task_id=job.reused_task_id`. Here that
requires `1=69`, discarding the valid retained view. The live database function definition was
captured in `attempt-001/live-owned-function-definitions.json`, rather than assuming installed SQL
matched source. `source-selection-diagnosis.json` retains the actual run/view selections.
The failed run remained failed and unselected, with no output realization. The project selection
remained null, generation 0. No repair or forced ingestion was attempted against the frozen release.

The inspected source owner offers a new source invocation; it does not expose a general same-run
source continuation API. `finalize_bound_run` explicitly refuses cancelled/failed runs. CLI
`regenerate --resume-run` retains the old run and reaches finalization; it does not re-enter
`run_source_methods`. The probe used the actual finalization refusal directly, and did not claim
CLI continuation or source completion receipt replay coverage. Completed source-task reuse is
separate from reuse of a cancelled task result; the latter had no durable rows here.

Commands, executed from the repository root:

```sh
uv run python docs/design_review/evidence/2026-11-04_m1-reuse-recovery/cancellation-heading/inspect_source.py
uv run python docs/design_review/evidence/2026-11-04_m1-reuse-recovery/cancellation-heading/run_probe.py
uv run python docs/design_review/evidence/2026-11-04_m1-reuse-recovery/cancellation-heading/inspect_failure.py
uv run python docs/design_review/evidence/2026-11-04_m1-reuse-recovery/cancellation-heading/verify_settlement.py
```

The second command exited 1 on the retained recovery failure; the other commands exited 0.
The exact combined stdout/stderr is retained in each adjacent `.log`. `run_probe.py` refuses to
reuse its existing `attempt-001` folder, preserving this attempt. At the end of this original attempt, recovered publication remained blocked. Integrated
qualification, all-family quality, recovery during later inference and original-source completion
receipt replay remain `not_run`; the native125 follow-up below completes bounded new-run recovery.

## Authorized forward repair adopted as native125

**Tested · 2026-11-04; all 11 targeted native cases passed under native125.** After the failed journey,
the coordinator authorized a structural correction limited to
`python/corpus-structure/src/corpus_structure/semantic/sql/source_views.sql`'s
`ops.select_reused_source_views` and the new regression file
`python/corpus-structure/tests/semantic/test_retained_source_reuse_native.py`. Runtime Python and
frozen migrations remain unchanged. The coordinator completed independent review, forward native authoring/application, unchanged
semantic release verification and serialized native tests.

The function retains `ops.valid_reuse`, requires a writable target run, and chooses retained views
using the exact declared `native_product` or `integrated_product` task/key/digest. It joins the
published product, original source builds and current document/project custody, and requires the
view and successful-origin/current run to share the consumer release. Historical native producers
retain the cross-release behavior already admitted by source-view publication. Simultaneous
retained product declarations are refused. Whole JSON pin comparison introduces no numeric casts
of untrusted task identifiers. The original native producer-equals-successful-task path remains available even when the task
declares a retained input and publishes a different organized or integrated output. Sibling products selected in the same origin run
are excluded. Existing successful-task reuse resolution remains anchored to the completed task.

Eleven collected cases cover both retained selector fields; a successful task whose source run was
cancelled; repeated reuse; ordinary native production; configured native input with a distinct own output;
a sibling product in the origin run; wrong
digest, key or producer; a nonnumeric task identifier; a different document; conflicting declared
products; and a closed target run. Their small native publication fixture uses the existing
`publish_native_record_fixture`, actual task lifecycle and source selection APIs, with independent
expected source-view identities. No model or recognizer is invoked by these regression tests.

Focused checks:

```sh
uv run ruff check python/corpus-structure/tests/semantic/test_retained_source_reuse_native.py
uv run ruff format --check python/corpus-structure/tests/semantic/test_retained_source_reuse_native.py
uv run pytest --collect-only -q python/corpus-structure/tests/semantic/test_retained_source_reuse_native.py
uv run pyrefly check python/corpus-structure/tests/semantic/test_retained_source_reuse_native.py
git diff --check -- python/corpus-structure/src/corpus_structure/semantic/sql/source_views.sql
```

Ruff, formatting, collection and whitespace checks passed; collection retained in
`repair-final-collection.log`. `repair-sql-parse.json` records a passing PostgreSQL outer
`CREATE FUNCTION` parse, which does not execute or semantically validate the PL/pgSQL body.
`repair-pyrefly.log` retains the initial focused typing result. The reviewer-requested own-output
correction is covered by `repair-own-output-collection.log` (11 collected cases),
`repair-own-output-pyrefly.log` (0 errors) and `repair-own-output-sql-parse.json`. The coordinator
then ran all 11 native cases successfully, retained in
`../../2026-11-04_m1-policy-admission/attempt-native-source-reuse125.log`. The bounded actual
recovery below exercised the corrected function in the persistent development database.

## Actual recovery under native125

**Tested · 2026-11-04.** `run_recovery.py` created new run **19** with the exact source input,
revision, scope, extraction configuration and full dependency bytes of cancelled run 17 and failed
run 18. Only the original fresh raw candidate setting was retained; no fresh ingestion workaround
was added. Native125 fixed the selected-view custody failure without changing semantic release
`release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd`.

Source task **73** reused successful retained source task **69**. Annotation task **74** reused
original annotation task **34**, the same original to which run17 annotation task **70** points.
New candidate task **75** and resolver task **76** completed empty. The actual source view selection
was exactly **22**, with the same native product pin and section. One actual GLiNER child, PID
**3760677**, parent **3759783**, `/proc` start ticks **6193415**, performed **3 native calls**,
**1 cold call**, on **1 context**, maximum **9 input bytes**. Its retained native inference total
was **4.7358 s**. Definition, assertion and measurement execution reported complete. These are
operational outcomes; no source-reading quality or useful knowledge claim follows from the empty
heading result. The child was joined and absent when source preparation returned.

The initial publication attempt correctly refused to create the output realization because the
new exact native deployment needed restricted admission. `attempt-002.log` retains that failure:
`native admission requires restricted admission phase`. `publish_recovered.py` used the existing
`execution_admission.require_native_execution` API under the **admit** purpose to verify and record
the exact deployed enforcement admission, then retried finalization through the normal **write**
purpose. This required no new model call, source execution, migration or default mutation.

| Native125 check | Outcome | Receipt |
| --- | --- | --- |
| Same frozen input/config/scope/dependency bytes | passed | `attempt-002/source-task-origin-links.json` |
| Retained task reuse restores heading view 22 | passed | same task links and `events.jsonl` |
| Actual CPU calls and child settlement | passed | `attempt-002/source-ready.json` |
| Exact native deployment admission | passed | `attempt-002/restricted-admission.json` |
| Nondefault result publication | passed | `attempt-002/publication.json` |
| Completed finalization receipt replay | passed | `attempt-002/completed-finalization-replay.json` |
| No cancelled result in final cut; no open owned tasks | passed | `attempt-002/summary.json` |

The recovered run is **finished and sealed**, final cut **19**, output realization
**`m1-heading-recovery:19`**, data revision **1**. The final cut's task/origin links are
**73→69**, **74→34**, **75→75**, **76→76**. Cancelled task **71** is absent from the cut and still
has zero task-result and observation rows. Run 17 remains cancelled; run 18 remains failed.
No pending/running/awaiting-agent tasks remain across owned runs 17–19. The project's selected
result remains **null**, active release remains **null**, generation remains **0**. The result
has one source report and zero occurrences.

A repeated `finalize_bound_run(19, "m1-heading-recovery:19")` returned the exact same `DomainResult`
and publication receipt. This checks completed publication receipt re-read, independently from
source-task completion replay, which was not exercised. Closed run 17 was never reopened.

Commands, from the repository root:

```sh
uv run python docs/design_review/evidence/2026-11-04_m1-reuse-recovery/cancellation-heading/run_recovery.py
uv run python docs/design_review/evidence/2026-11-04_m1-reuse-recovery/cancellation-heading/publish_recovered.py
```

The first command returned source-ready but exited 1 at the retained initial publication refusal;
the second exited 0 after normal admission, publication and receipt replay. Their complete outputs
are `attempt-002.log` and `attempt-002-publication.log`. The final structured receipt is
`attempt-002/summary.json`. These results close heading-only new-run recovery and completion
fencing. They do not establish immediate inference interruption, same-run source continuation,
exact source completion receipt replay, all-family quality or complete-M1 qualification.
