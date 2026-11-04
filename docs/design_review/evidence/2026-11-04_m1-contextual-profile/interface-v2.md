# Native v2 interface and warm request cancellation preparation

**Passed, measured 2026-11-04:** [interface-004/summary.json](interface-004/summary.json)
and [external-settlement.json](interface-004/external-settlement.json) retain the actual
base-checkpoint CPU FP32 v2 interface and warm request cancellation control. The input
is the immutable source-only whitelist from contextual-targets/attempt-004, completed
run22/finalcut23 and release `release:407d64d35766538fcb4d270f0a4e0ad5192a364349e4a667a84bc3c2a5b6bd25`.
No training, references, grading, adoption, DB or PDF execution occurred in this runner.

Three complete, ungraded native reports are retained: cold definition15.018 seconds,
warm definition15.545 seconds and warm latent assertion16.469 seconds. Definition used
4039 schema-conditioned subwords/3427 codepoints; assertion used4077/2858. Both selected
inputs remained within the unchanged4096 bounds. The fourth request reused the same
child and raised `asyncio.CancelledError` at0.50194 seconds, with dispatch serial3→4,
live IPC observations and1.87 seconds of observed child CPU growth. Teardown took
0.17018 seconds, with child/IPC absent. The internal native phase remains unobservable.
The wrapper exited0; all four externally observed PID/start-tick identities were absent.

Resource evidence is **partial**:149 samples, peak complete aggregate PSS7579291KiB,
separately named peak RSS sum7853672KiB, peak15 threads and185.03 seconds observed
process CPU deltas. One sample had unavailable PSS and three transient `/proc` discovery
errors remain in the raw sampler/finalizer receipts. These are observations of this bounded
run, with no capacity or whole-M1 qualification conclusion. Complete native outputs are
not source-truth judgements or evidence of quality gain.

Two earlier pre-model failures remain unchanged. The first runner attempt,
`interface-002`, **failed before worker/model creation** because its exact production
profile fingerprint differed from the frozen metadata profile: metadata used direct raw
configuration validation, retaining integer default timeout120, while production registry
resolution materialized/revalidated it as120.0. The timeout bound is numerically equal,
but the declared profile fingerprints differ. No equality guard was weakened. The failed
attempt, logs, resource samples and failed external settlement result remain retained;
all observed process identities were absent at finalization. The coordinator authorized
corrected metadata preparation through the production registry constructor and a fresh
`interface-003` output after its whitelist passed. That attempt exposed a harness error:
the native processor's internal `Schema.build()` mapping was compared with user-facing
`Schema.to_dict()`. Exact raw declarations and pack identities already matched. The
comparison was corrected to the installed processor's actual `.build()` contract and
independently checked for both families before the successful fresh004 execution. Both
failed attempts have logs, failure and settlement receipts; neither constructed a worker
or invoked a model. A reusable `--preflight-only` route now stops after every source/config/
release/schema guard and before worker construction. Its first full run occurred after
the successful004 execution; it does not retroactively replace either failed attempt.

Wait for the coordinator's selected stable release/run/whitelist before any future execution.
Frozen `interface-001`, its runner, finalization and records
remain the account of the earlier interface; these new scripts do not modify them.

`run_interface_v2.py` uses the native `GlinerWorker` and named statistics contextual
configuration. It reads only `source-whitelist-freeze.json`, `contextual-configuration.json`,
`source-contexts.jsonl`, `native-preparation.jsonl`, `source-receipts.json` and `launch.json`
from the selected attempt's immutable source whitelist. The separate full target freeze is
unnecessary: the source-only whitelist closes before target construction completes and binds
the exact completed run, final cut and prepared release. It never opens authored references,
training targets, target origins, request audits, dispositions or grading outputs.
The native preparation entries precede reference eligibility and have `build_targets=False`;
their empty expected-record arrays are preparation metadata, not negative supervision.

For each of definition and assertion, selection considers every source-only admitted request,
ordered by schema-conditioned subword count, source UTF-8 bytes and request ID. It preserves
the complete selected source text, intervals, source pins, selection and preparation receipt.
It requires exact current registry/configuration, consumed source snapshots and package versions,
explicit current prepared release and source-run binding, checked pinned base artifacts,
native-combined-v2 packs, definition `defining_text` list/zero_or_more and latent assertion
with no native anchor. Contextual CPU FP32/codepoint bounds remain 4096 source words,
4096 schema-conditioned subwords,4096 context characters and128 pieces. No capacity increases,
truncation, labels, model adaptation or policy acceptance occur here.

The sequence is one cold definition call, the same definition call warm, then a warm assertion
call, all in one resident child. Reports retain complete native output without grading. Actual
preparation and source bytes must equal their frozen receipts. A fourth request uses the larger
of the two selected inputs and the same warmed child. Its existing `check_active` callback raises
`asyncio.CancelledError` after the predeclared0.5 second delay. The control requires observed
dispatch serial advancement, a live existing IPC thread, child CPU growth, typed cancellation,
joined/absent child and settled IPC within10 seconds after cancellation. Completion before
cancellation is retained as an unsuccessful interruption demonstration, with its native output.

The callback cannot observe the internal child phase. Serial/IPC observations show request
exchange started; they do not acknowledge send completion or establish that the child is inside
`batch_extract` rather than native preparation. This control concerns cancellation of a warm,
owned request while awaiting its reply. It establishes neither distributed pipeline cancellation
nor model quality, benefit, adoption, whole-M1 qualification or held-out results. No hooks or
worker implementation changes are introduced.

For a future attempt, first run the complete no-model preflight in an unused folder:

```bash
uv run python -B docs/design_review/evidence/2026-11-04_m1-contextual-profile/run_interface_v2.py \
  --dataset docs/design_review/evidence/2026-11-04_m1-contextual-targets/SELECTED_ATTEMPT \
  --release-id CURRENT_RELEASE --source-run-id CURRENT_RUN --source-cut-id CURRENT_CUT \
  --attempt interface-preflight-NEXT --preflight-only
```

After preflight and authorized stable input selection, the coordinator can replace the uppercase
placeholders and run with unused output names:

```bash
uv run python -B docs/design_review/evidence/2026-11-04_m1-cpu-resources/sample_tree.py \
  --interval 0.5 \
  --out docs/design_review/evidence/2026-11-04_m1-contextual-profile/resources-interface-NEXT.jsonl \
  -- uv run python -B docs/design_review/evidence/2026-11-04_m1-contextual-profile/run_interface_v2.py \
  --dataset docs/design_review/evidence/2026-11-04_m1-contextual-targets/SELECTED_ATTEMPT \
  --release-id CURRENT_RELEASE --source-run-id CURRENT_RUN --source-cut-id CURRENT_CUT --attempt interface-NEXT

uv run python -B docs/design_review/evidence/2026-11-04_m1-contextual-profile/finalize_interface_v2.py \
  --attempt interface-NEXT \
  --resources docs/design_review/evidence/2026-11-04_m1-contextual-profile/resources-interface-NEXT.jsonl
```

Use unused output/resource names for retries; failures remain immutable. The existing sampler
captures the cold parent+descendant tree, aggregate PSS, separately named RSS sum, CPU deltas,
threads and unavailable measurements. Finalization checks wrapper exit, command binding and
observed PID/start-tick absence; polling can miss subinterval or reparented processes. Resource
measurement availability and functional outcomes are reported separately.

Original preparation checks were guarded `--help` and static diagnostics only. Actual004 model
execution followed the coordinator's explicit stable native GO. Preparing or maintaining this
runner does not independently authorize another model, DB, PDF, provider, training or held-out
execution. The adaptation epoch remains a separate coordinator-owned scope.

Library orientation used Context7 `/fastino-ai/gliner2` and the
[native structured extraction documentation](https://github.com/fastino-ai/gliner2/blob/main/tutorial/3-json_extraction.md).
The installed pinned2.1.0 schema/compiler and existing worker lifecycle own consequential
cardinality, latent formation, bounds and cancellation behavior.
