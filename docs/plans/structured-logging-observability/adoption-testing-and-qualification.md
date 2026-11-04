# Adoption, testing and assembled qualification

**Status:** Proposed; 2026-11-01. [Coordinator](../structured-logging-observability_2026-11-01.md)
owns LOG-11/12 state and overall completion. This plan serves O08 and the integrated acceptance
of every selected opportunity. It neither repeats nor changes PDF plan scope or evidence.

<a id="LOG-11"></a>
## LOG-11 — Incremental migration and useful test diagnostics

Reconcile the following actual consumers as their owning packages land. This is the migration
footprint, not a claim each already emits rich logs. Add a consumer only when source inspection
shows it performs one of the selected operations; no arbitrary repository-wide instrumentation.

| Consumer | Owning change and preservation obligation |
|---|---|
| Installed CLI root, command groups, Settings and failure boundary | LOG-01/02/06: lazy acquisition, typed results, classified refusals and stdout contract |
| Orchestrator and MethodContext methods | LOG-05: selected run/task/attempt/stage, reuse/failure/cancellation; no duplicate task authority |
| Native PDF spawned child and recognition threads/service | LOG-05: explicit initialization/carriers and existing drain/kill/receipt custody |
| Semantic preparation/admission, source/query/export services | LOG-03/05: compact safe references, scoped visibility and original transaction semantics |
| Supervised external model process and owned MCP child | LOG-05/09: explicit sanitized child config, opaque coverage where service lacks instrumentation |
| Direct/embedded FastMCP, injected sessions, stdio launch | LOG-09: host provider ownership, source principal and protocol safety |
| Evaluation/reference-authoring and tests | LOG-07/08/11: isolated reference compartments; independent expectations and existing runner semantics |
| Third-party stdlib producers and migration diagnostics | LOG-02: preserve foreign origin/exception fidelity; no library root-handler reset |

Existing plain warnings, ad-hoc stderr reports and source receipts are not deleted simply because
telemetry exists. Replace duplicated diagnostic interpretation at its owner only after actual
consumers migrate; preserve contractual command results and authoritative records. Do not migrate
historical logs into synthetic fully structured events. Old archives remain explicitly old formats
until an intentional adapter is selected; no source/evidence/database purge is authorized.

`ci diagnostics test -- SELECTION` launches the existing strict pytest configuration with an
argument-list subprocess, selected diagnostic environment and per-process test context. Preserve
runner exit code and original failure; no shell evaluation or new scheduler. `ci diagnostics tests
REPORT` inspects retained failure reports/bundles. Workers initialize their own logging; wrapping
pytest alone cannot instrument child processes. Maintain node/worker/seed/config/trace references
and bounded failures rather than noisy successful output. This command is not automatically a
replacement for repository qualification recipes.

Compare native structlog capture/CapturingLoggerFactory, stdlib capture, SDK in-memory readers and
Logfire capfire if selected. Event capture may bypass processors or miss cached loggers; assertions
must distinguish authored event, safe normalized event, delivery arguments and actual serialized
file. Use independent expectations for code, scope, exception structure and causal relations.
Deterministic IDs/time generators help fixtures but do not prove real process lifecycle. Concurrent
CliRunner calls in one interpreter are forbidden; parallel isolation uses separate processes.

Completion: each listed consumer has migrated or a precise out-of-scope reason at its owning
package; an actual failing test produces inspectable correlated context through Typer without
changing its original exit/receipt. Test plumbing does not expose evaluation references to the model.

<a id="LOG-12"></a>
## LOG-12 — Final-source qualification and activation

Local checks occur with coherent package behavior. Complete selected functional scope first, then
run required functional/provider/nonfunctional checks on final source/context. The root performs
required maintenance before final qualification, re-evaluating affected evidence after subsequent
source/harness/shared-config changes. Use `just test-all` and applicable `just hygiene` as broad
routes; keep empty Rust/rule selections not_run. Do not sum overlapping receipts as independent
coverage or relabel earlier failures after repair. No runtime tests were run by this authoring task.

| Journey | Independent acceptance signal |
|---|---|
| Installed CLI normal/debug/incident/off, Rich/plain/JSON | Result bytes parse; stderr/progress independent; profile/provenance and early errors correct |
| Offline ended-run event/trace/metric inspection and support export | No network/UI dependency; expected known history, units, coverage and safe bundle content |
| Concurrent contexts and real spawned PDF/MCP children | Correct distinct identity/parent/link, no cross-scope leak, initialized child resources |
| Failure value, retry/recovery, cancellation and publication error | Original outcomes retained; incident trigger only for classified failure; telemetry cannot mark committed work failed |
| Rotation, active tails, interrupted records, snapshot cursor and retention | Earlier valid records remain; stable/explicitly expired pages; no silent gap or duplicate occurrence counts |
| Disk/queue failure, slow backend and shutdown deadline | Loss observable independently, bounded cleanup established for actual exporter, original exception survives |
| Metrics reset/temporality/typed dimensions and two simultaneous runs | No cumulative double count, no fake run filtering on process aggregates, final short-command collection |
| Real stdio MCP notifications plus unsupported/ignored client handling | Clean protocol; scoped typed query matches Typer; native context modes and reconnect remain honest |
| Redaction and serializer failure, source/reference compartment denial | Sensitive material absent from all branches and support artifacts, not merely hidden in terminal |
| Optional remote write/read/config | Actual backend evidence with named prerequisite; mocks/in-memory only qualify their local scope |

Activation follows completed local acceptance: ship normal defaults and documented profile controls,
local archive location/retention, safe shutdown and diagnostic check. Verify the actual operator
workflow without changing current project/database defaults as an incidental logging action.
Extend a future deployed principal through explicit authentication and measurement scopes, not a
claim of existing hosted readiness. Disable optional telemetry to recover from an integration
fault without changing task/source truth; keep the failed diagnostic receipt.

Overall completion requires every required local/MCP/migration obligation settled, and conditional
remote obligations either exercised or explicitly left open with prerequisite at LOG-10/I06. Do not
call all-scope qualification complete while a selected required remote journey is unavailable.
Report implemented, tested, measured and unavailable scope separately. No latency/throughput claim
is currently required; measure only if a concrete benefit/capacity claim is introduced.

Update the coordinator's package/disposition rows and STATUS from actual results. Move enduring
contracts to D6/D8/D9/other semantic owners through the selected ADR route. Keep plans and evidence;
no plan deletion, additional status ledger or periodic full-audit machinery is introduced.

Sources: [test assessment](../../design_review/design_principles/core/test-assessment.md),
[structlog](../../libraries/logging/structlog.md) §9,
[Logfire](../../libraries/logging/pydantic-logfire.md) §15,
[Typer](../../libraries/python_introspection/typer.md) testing and advanced addendum §7,
[Rich](../../libraries/python_introspection/rich.md) §7.13.
