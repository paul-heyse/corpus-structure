# Managed recognition generation custody

2026-11-03, AC08/I03. Baseline `1240f9b7` plus the source-execution change set.

**Tested:** the controlled launcher verifies the selected immutable model/tokenizer digests,
archives the complete export manifest and launch arguments, and assigns a fresh process generation.
vLLM0.26.0 imports `custody.GenerationMiddleware` through its supported `--middleware` route.
The worker sends the admitted generation on every inference request and verifies the response
header before assigning `trusted_managed_service`. This is trusted local startup custody,
not cryptographic GPU-content authentication. Unmanaged endpoints remain `provider_reported`.

Actual dedicated RTX5090 service controls (no HTTP mocks):

- `runtime/startup-1.log`, startup manifest `cbd7ed4942c44660a9c50d11c7d7f734.json`,
  `generation-1.json`, `request-1.json`, `response-1.json`: actual image inference succeeded
  under one admitted generation; requested and provider-reported alias are retained separately.
- `controls.py`: missing or wrong request generation refused with409; admitted generation
  returned200. `runtime/replaced-artifact.json` records refusal of replacement bytes under
  the same display alias before launch. This isolated control did not mutate the actual export.
- `runtime/sleep.json` and `wake_up.json`: actual level-one sleep/wake retained the same
  generation and succeeded. These are execution-lifetime controls, not recognition-quality claims.
- `request-crossing.json`, `response-crossing.sse`, `crossing-result.json`: an actual streamed
  request received its first output before the owned service was sent SIGTERM. It completed
  during graceful shutdown with the original response generation, without relabelling.
- `runtime/startup-2.log` and `generation-2.json`: restart admitted a different generation
  for the same verified artifacts. `stale-generation-after-restart.json` records409 for the
  earlier admitted generation; `new-generation-after-restart.json` records200 for the new one.

Commands used the independent service Python at
`/home/paul/corpus-structure/services/nemotron-parse/.venv/bin/python`:
`services/nemotron-parse/launch.py --export <verified-export> --runtime <vllm> --receipts runtime`,
`controls.py`, and the retained request payloads through HTTPX. The application controller also
admits the manifest before result reuse; its recipe distinguishes managed custody from reported
identity. Existing receipts lacking that assurance are never silently promoted.

Source native/policy test results are separate from this actual-provider investigation. The
coordinator owns assembled AC14 qualification; this folder does not establish extraction accuracy,
full-book conversion or scientific release.

`runtime/application-result.json` and `application-journey-attempt-2.log` retain the actual
application controller → isolated public `DocumentParser` triple route, with two successful
requests whose generation matches the managed response. `application-journey-attempt-1.log`
preserves the earlier probe's cleanup-API mistake after its requests succeeded; it is a failed
probe receipt, not a passed end-to-end attempt. `replaced-startup.log` and `replaced-startup.json`
exercise the actual launcher with replacement bytes: it refused before creating any generation
record or starting a service. The two owned live services were shut down after this investigation.

Bounded source controls are retained under `raw/`: the stable-source targeted selection passed123
cases. Earlier failed attempts remain: nested shell activation refused the unreviewed worktree
`.envrc`, the new fixture initially used bare Pydantic `BaseModel`, and a concurrent source edit
invalidated a process-cached implementation binding during consumer setup. Those failures were
corrected without weakening admission. The root owns final source/context and AC14 union accounting.

Method-dimension follow-through (AC01/AC06–08), 2026-11-03: `raw/method-dimensions-component-62.log`,
`method-dimensions-lifetime-27.log` and `method-dimensions-policy-46.log` retain overlapping scoped
passes. The native controls install the prospective owned task/completion guards on an isolated
committed clone, then independently refuse wrong metadata, report family, borrowed task outcome
and confidence provenance, and persist the valid report once. Archive setup precedes prospective
adoption because the working tree intentionally retains the frozen archive descriptor until the
root authors its forward transition. Earlier failed setup attempts remain. `method-dimensions-types.log`
records the scoped Pyrefly pass. These controls do not replace forward installation, integrated
model regeneration, final source/context accounting or the complete AC14 union.

The later existing-consumer selection retained one failed fixture admission in
`raw/method-dimensions-consumers-attempt-1.log`: the intentional `read` fixture's
`author_markup` report was absent from its literal declaration. The declaration now includes it;
production admission was unchanged. After splitting batch original custody into owned reads and
per-task publication transactions, `raw/source-custody-consumers-26.log` passed26 reader,
operation and native claim cases. Its actual native slow-custody control pauses preparation of the
later original until the earlier task renews, then durably settles both. Scoped Ruff passed and
`raw/source-custody-types.log` records Pyrefly0 errors. This is bounded functional evidence, not
assembled scheduler/provider qualification.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**audit-closure**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Actual managed recognition startup and request generation custody](records/ac.i03-managed-generation.json) | AC08 | passed | AC08, I03, DA-051, ADR-0054 | 2026-11-03 |
<!-- evidence-index:end -->
