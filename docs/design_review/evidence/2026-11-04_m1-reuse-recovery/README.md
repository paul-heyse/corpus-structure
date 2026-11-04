# M1 operation reuse and recovery on retained source

**Tested · 2026-11-04.** Bounded actual source execution demonstrated downstream configuration
reuse, completed-result replay, cancellation fencing and new-run recovery. These receipts establish
operational behavior on the stated retained sources, not extraction quality, calibrated probabilities,
all-family coverage or complete M1 qualification. The coordinator owns requirement disposition,
accepted evidence records, assembled qualification and commits.

The journeys use the Grinstead–Snell retained integrated product, task **1**, key **integrated**,
digest `e8ee2f72912fe174fdaf76918b7cb347ad245fecdf9c827688814729b9961cba`, source release
`release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd`.
The source execution baseline is `1e631ba7c9a6877d40a0eab7f6e81ddef0b4b99a`; the bounded
source-selection correction was adopted as native125 without changing that semantic release.
Database operations used the dedicated persistent development database on port 5434 and existing
purpose principals. No PDF conversion, OCR, independent reference answers or evaluator grades
were used for these journeys. Every result remains nondefault.

| Journey | Outcome | Exact boundary and receipt |
| --- | --- | --- |
| Changed resolver subset, actual run 16 | passed | Both original source views, immutable annotation/raw origins reused; resolver ran with changed configuration. `downstream-subset-001/verification.json` |
| Completed actual CLI `--resume-run 14` | passed | Existing finished run 14, sealed cut 13 and publication receipt re-read; no source execution. `attempt-completed-resume-14-003.log` and verification |
| Actual child startup cancellation, run 17 | passed | Cancellation requested during real child startup; completion was fenced and child settled. `cancellation-heading/attempt-001/summary.json` |
| First new-run recovery, native124/run 18 | failed | Retained source-view reuse lost the valid heading; full failure retained. `cancellation-heading/attempt-001/recovery-failure.json` |
| Forward repair regression controls | passed | Coordinator applied native125 and ran all 11 cases. `../2026-11-04_m1-policy-admission/attempt-native-source-reuse125.log` |
| Same frozen heading recovery, native125/run 19 | passed | Three real CPU calls; child joined; final cut 19, nondefault output and exact completed finalization replay. `cancellation-heading/attempt-002/summary.json` |

## Downstream subset configuration reuse

`run_reuse.py` uses the existing `run_source_methods` owner with actual run 14's input realization,
revision, method parameters, parent dependencies, corpus and guideline. The only finite method
parameter changed was the resolver subset, from **`statistics-m1-source-readings-2`** to
**`statistics-m1-reuse-control-1`**. No fitted or calibrated instance was supplied and no quality or
benefit comparison was attempted.

Read-only verification on 2026-11-04 used `purpose="read"` and an explicit PostgreSQL read-only,
repeatable-read transaction. It read metadata and computed producer-output SHA-256 fingerprints
on the server; it did not rerun source execution, a model or a CLI journey. Both runs selected the
exact same source views **22 and 23**, including native product, section, projection and recipe pins.

| Operation / view | Run 14 task | Run 16 task | Observed reuse/configuration |
| --- | --- | --- | --- |
| Retained integrated source / document 1 | 33 | 62 | Same configuration; fresh retained-source task because complete manifest identity changed; no reconversion |
| Annotation / 22 | 34 | 63 | `63→34`; identical configuration, input hash and effective output fingerprint |
| Annotation / 23 | 35 | 64 | `64→35`; identical configuration, input hash and effective output fingerprint |
| Raw candidate / 22 | 36 | 65 | `65→36`; identical configuration, input hash and effective output fingerprint |
| Raw candidate / 23 | 37 | 66 | `66→37`; identical configuration, input hash and effective output fingerprint |
| Resolver / 22 | 38 | 67 | Fresh; configuration 23→44 and input hash changed with the declared subset |
| Resolver / 23 | 39 | 68 | Fresh; configuration 23→44 and input hash changed with the declared subset |

The four reused annotation/raw tasks have no separate output bodies: their effective bodies remain
at the original successful task IDs. Verification records both original result digests and the server
SHA-256 of each effective body. The original producer outputs were not copied, replaced or relabelled
as new inference. The final cut retains those original origin links.

Run **16** is finished and sealed, source-ready cut **16**, final cut **17**, output
**`m1-reuse-result:16`**, data revision **1**. Its saved publication receipt matches the current
immutable batch ID, content digest and actual stored-byte hash. It contains **212 source reports**
and **500 occurrences**, which are result metadata rather than accuracy claims. The project's
selected result and active release remain **null**, generation **0**. Exact configuration/input hashes,
task/origin/result fingerprints, selected views, cut links and publication identities are in
[`downstream-subset-001/verification.json`](downstream-subset-001/verification.json).

Commands and raw outputs:

```sh
uv run python docs/design_review/evidence/2026-11-04_m1-reuse-recovery/run_reuse.py
uv run python docs/design_review/evidence/2026-11-04_m1-reuse-recovery/verify_reuse.py
```

The original execution is retained in `attempt-downstream-subset-001.log`; the later read-only
verification exited 0 and is retained in `attempt-verify-reuse-001.log`. The verifier refuses to
overwrite its existing receipt. `declared-input.json`, `source-ready.json` and `completed.json`
remain the original execution artifacts under `downstream-subset-001/`.

## Completed actual CLI replay

The coordinator executed this successful command; this verification did not execute it again:

```sh
uv run ci regenerate --domain statistics --corpus docs/design_review/evidence/2026-11-04_m1-source-populations/population-fixtures --project m1-source-grinstead-snell --resume-run 14 --leave-unselected --json
```

`attempt-completed-resume-14-003.log` reports run **14**, `status="complete"`, the original source
realization and output **`m1-result:14:release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd`**,
`provider=null`, and `selected_generation=null`. The first two CLI attempts, which omitted required
`--domain` and then `--corpus`, remain in `attempt-completed-resume-14.log` and
`attempt-completed-resume-14-002.log`.

The actual successful receipt matches the original completed result retained at
`../2026-11-04_m1-cpu-readings/attempt-011/completed-result.json`. Current read-only checks confirm
run 14 remains finished and sealed, final cut **13**, original data revision **1**, with the exact
same original publication batch and content digest. Its original seven task IDs **33–39** and
statuses match the retained pre-replay source summary; only original cuts **12 and 13** exist.
The completed CLI path skips `extract_run` when a result exists; finalization reuses the existing
final cut and `_completed_result` reads its immutable receipt. No source task or output identity was
added or replaced along this completed-result path.

There is no full producer-body hash snapshot bracketing the historical CLI invocation. The verified
comparison is the actual receipt plus unchanged original IDs/statuses, cut identities and immutable
publication receipt, supported by the completed-result owner path. Current producer fingerprints
are retained for precise identity accounting; they are not presented as a historical before/after
hash measurement. This is completed-result replay, not resumption of an interrupted source method
or exact source-completion receipt replay.

## Cancellation and new-run recovery

The detailed account and commands are in
[`cancellation-heading/README.md`](cancellation-heading/README.md). Run 17 was cancelled during
observed actual child startup on **view 22 only**, section **Chapter 5**. The API returned one
cancelled task in **0.0436 s**; the child remained alive at that return. The executor settled
**17.927 s** later when the attempted completion was refused. Cancelled task **71** has zero durable
result or observation rows. This establishes durable completion fencing and eventual child
settlement, not immediate interruption during inference.

Recovery run 18 exposed a retained-product source-selection defect. The reviewed SQL-only native125
repair preserves exact declared product custody and the existing producer-own-output path. Run 19
then used the exact same source/config/scope/dependency bytes as runs 17/18, restored view **22**,
reused successful retained source task **69** and original annotation task **34**, and performed
**three actual CPU calls**. The model child was joined and absent before source readiness returned.

The first publication attempt retained its normal restricted-admission refusal. The existing
**admit** purpose refreshed the exact native deployment admission; the normal **write** purpose
then published **`m1-heading-recovery:19`**, final cut **19**, revision **1**. Repeated finalization
returned the exact same publication receipt. Run 17 remains cancelled and run 18 remains failed;
run 19 is finished and sealed. Cancelled task 71 is excluded from the final cut; no owned tasks
remain open. Defaults remain null, generation 0. The heading result has zero occurrences and
establishes no extraction-quality conclusion.

Same-run source continuation, exact source-completion receipt replay, interruption after an observed
inference-start marker, all-family quality, fitted-parameter benefit and complete-M1 qualification
remain outside these bounded results. The failed and refused attempts remain available alongside
the passing receipts. No evidence record was finalized by this worker.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Actual retained-source reuse cancellation and recovery](records/m1.actual-reuse-recovery125.json) | M1-04 | passed | — | 2026-11-04 |
<!-- evidence-index:end -->
