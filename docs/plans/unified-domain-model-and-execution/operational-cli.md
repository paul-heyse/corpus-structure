# Operational CLI: exact recovery, attributed observation and managed stop

**Status:** Superseded 2026-11-20 by [Domain model operability](../domain-model-operability_2026-11-20.md).

**Historical checkpoint:** Implemented source and scoped controls tested for UDM-26 and UDM-27. Native
recovery, actual-provider retirement and assembled qualification remain open.
**Created:** 2026-11-18.

This companion owns **UDM-26**, the operator-facing run, recovery, inspection and change-impact
integration, and **UDM-27**, exact managed-invocation stop. It integrates
[I06](../../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md#I06),
[I07](../../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md#I07) and
[I08](../../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md#I08), and
consumes the cache reporting contract of
[I04](../../plan_improvement_reviews/unified-domain-model-and-execution_2026-11-18.md#I04).
The [coordinator](../unified-domain-model-and-execution_2026-11-19.md) owns package state,
dependencies, finding disposition and assembled completion. All target behavior below is
**Proposed**; source descriptions are **Interface-checked by source inspection, 2026-11-18**
against `3726a5cb6`. No run, provider call or performance measurement establishes these proposals.
Source paths below are relative to `python/corpus-structure/src/corpus_structure/`.

## Boundary and foundation assessment

The operator needs to know what will run, which exact context an interrupted operation used,
what is happening now, and what a stop request actually stopped. The current managed invocation,
typed native bindings and bounded observation journal provide that foundation. Extending them
avoids a second workflow controller, telemetry store or independent interpretation of native
completion. This follows FP-02/04, DP-05/14/18/21/24 and the efficient-architecture guidance on
bounded auxiliary work and recovery at the owning boundary.

The existing entry points already converge on `cli/demands.py:execute_request` through
`cli/orchestrate.py:execute_source_choices`. `cli/managed.py:Invocation` owns managed results;
`orchestrate/source_reporting.py` binds native demand, target, release and runtime.
`cli/result_inspection.py:ResultInspection` already carries availability, omissions and next
actions; `cli/observations.py` owns attributed events and bounded pages. These are the integration
owners, rather than justification for a new generic reporting subsystem.

Two current limitations require deliberate changes. Effective execution policy is resolved before
native registration, but the useful request context is retained later. Inspection can reconstruct
only a demand/source-root shell command, losing the original effective policy. Also,
`ci demands plan` **registers a demand**; it is not the passive preview proposed here. Keep that
effect visible in help and reports. The new run preview must not call registration or claim work.

The semantic owners remain separate:

| Authority | Contribution consumed here |
|---|---|
| UDM-04 | Comparison of two compiled models; replacement of the earlier preview and its revision-log decision |
| UDM-09–12 | Program/privilege delta, layered identities, no-native-change outcome and carried/reconfirmed assurance |
| [UDM-25](operation-reuse-and-recovery.md#udm-25) | Native material-reuse, pending-attachment and retained-intent decisions with their supporting attribution |
| UDM-13/14 | Cache statistics, scopes, budgets, clear/prune eligibility and maintenance effects |
| Native demand, request and completion owners | Permission, claim, sharing, cancellation, acknowledgement and publication decisions |
| Process execution host and run owner | Resource custody, cancellation, physical retirement and quarantine |

UDM-26 renders these facts and preserves unknown or unavailable standing. It does not predict a
native decision from a digest, cache hit, process listing or display state. UDM-27 requests the
execution owner's cancellation protocol; it cannot manufacture lease settlement or confirmed
retirement. [ADR-0069](../../adr/0069-cli-operations-custody.md) owns CLI custody and
[ADR-0125](../../adr/0125-process-owned-execution-host.md) owns the host/run boundary.

The supported workload is one operator on the existing single host, with short CLI invocations
and long-lived MCP processes. Bounded native projections and the existing observation page avoid
rescanning every product or replaying bulk logs for each refresh. A richer view should remove
manual reconstruction of the same answer, not add per-primitive events or a general monitoring
service. No numerical improvement is claimed.

## Shared operator contracts

### Pre-execution plan and recovery binding

Retain a versioned typed account before expensive release/provider preparation. It captures the
original typed request or exact demand selection, project, document/scope and demanded family
closure; selected workflow/provider mode; source-root custody; selected release/runtime; and the
nonsecret effective execution policy. Record both the effective values and relevant origins,
including explicit overrides. Do not retain credentials, secret-bearing connection strings, or
live engines/readers. A policy file path alone is insufficient: its contents can change before
recovery. Reuse existing request, policy and binding types where they already express the facts.

Distinguish configured selection from an acquired and verified native target. Retain the
redacted configuration/profile selection and acquired identity when available, with the
observation time and availability. Before acquisition, report the expected target without
pretending its database identity has been established. `cli/target.py` already models configured
and acquired selections; reuse that distinction.

A passive preview reports this account, prerequisites and bounded known native availability.
It neither prepares a provider nor registers a demand, acquires a work claim, loads model weights,
or publishes results. Do not turn preview into a full preflight campaign. A bounded existing
readiness observation may be reported with its scope/time; an unperformed check stays unknown.
Work that only native registration or binding can decide is explicitly conditional. Display
reuse reasons only from the native decision or a clearly identified retained observation.

Recovery selects the prior managed result by exact ID. A new invocation names its predecessor,
reuses its captured request and effective nonsecret policy, re-resolves credentials through the
configured route, and verifies target, release/runtime and source custody before effects. If the
predecessor reached registration, resume its retained demand and eligible intent; otherwise use
the captured request through the ordinary execution owner. Do not invent an older executable
archive or bypass native attachment/claim fences. An explicit policy override is recorded as an
override with the resulting effective values; it must not silently replace the old policy with
the current defaults. A semantic selection change requires a new request rather than an
unlabelled mutation of the predecessor's intent.

The result's typed next action names its operation, selected managed/native identity, required
target context and unresolved inputs. A shell example is a rendering of that action, not its
authority. A predecessor lacking sufficient captured information reports exactly what must be
supplied; no compatibility reconstruction based on guessed defaults is required. Inspection never
opens a receipt-selected arbitrary connection or writes to the configured database. An explicit
configured target route is acquired and checked against the expected identity; wrong-target or
authentication failure is an unavailable native view with a usable managed view and next action.

### Attributed operational projection

Use one typed projection for `ci results inspect`, bounded `watch`, native-demand inspection and
their terminal/JSON renderers. Compose managed lifecycle, exact native read/bindings and bounded
owner observations without replacing their distinct authority. Include:

- Invocation, demand/run, task/attempt/request and provider/worker/device identifiers where the
  corresponding owner can establish them; observed time, freshness, source and omissions.
- Separate loading, ready, submitted inference, completed inference, settlement and publication
  standing. A live process, allocated GPU memory or successful registration proves none of the
  later states. Missing or stale evidence remains unknown or stale.
- Counts with their unit, selected scope and native read cut. Documents, pages, regions, products
  and sentence occurrences remain distinct. A frontier page is partial; a denominator appears
  only when the native owner supplies the matching complete scoped count.
- Native waiting/refusal/reuse reasons, with original derivation or retained-intent references
  when authorized. Physical cache reuse is distinct from native acknowledged-work reuse.
- Outcome, unresolved custody, and the exact next action without treating a full progress bar or
  the end of a watcher as completion.

Keep the current bounded observation/page/log behavior. Refresh from the established observation
cadence and bounded native reads; the renderer launches no extra polling or full-demand scan.
Exiting watch closes the watcher and its display resources, leaving execution and its native
interest unchanged. Demand cancellation reports detachment and any surviving shared interest;
the display must not label it as a physical process stop.

### Change impact and cache presentation

Compose the UDM-04 compiled-model comparison with UDM-09–12's typed program and identity delta
and UDM-25's reuse consequences. Before apply, report authoritative facts that changed, installed
program bytes/privileges that would change, the no-native-change decision, and which prior work
can carry forward, requires validity reconfirmation or requires execution. Identify assumptions
that only live binding/current support can settle. Do not add a second change graph or infer
consequences by parsing the rendered SQL explanation.

Continue the existing `ci model change` preview/inspect/apply and candidate/register/deploy
journey with exact preview, expected revision and bound target, followed by explicit
activation/adoption where applicable. Preserve known committed effects and partial-apply recovery;
an application failure does not imply rollback of an already committed stage. UDM-04/19 own
retirement of the earlier preview's rule digest and obsolete SQL explanation; this package moves
their command/report consumers without retaining a second implementation.

Render the typed UDM-13/14 cache reports through the same output conventions. Statistics identify
the actual observed process/owner and counter scope. A fresh CLI process cannot report another
process's local hits. Long-lived statistics use that owner's diagnostic route. Clear/prune
reports name their tier and prospective/actual eligible bytes; held receipts, retained intents
and acknowledged checkpoints never become cache-pruning candidates. Capacity, eviction and codec
maintenance do not themselves change native authority or material identity.

`ci cache stats --json` reports the current invocation's process identity, observation lifetime,
configured bounds, retained weights, and available counters. `inspect_cache` reports the
long-lived retained-reader MCP process using the same typed shape.

<a id="code-reuse-explanation"></a>

### Local explanation of code reuse

**Approved amendment · 2026-11-20.** Continuation compatibility and cache eligibility have
separate standing under [ADR-0141](../../adr/0141-serving-continuation-and-reuse.md). CLI and MCP
explanations may report reuse withheld while compatible native-authorized continuation remains
available. Report rederivation truthfully. Remove disk-only cache commands/settings with the
retired D2/D4 consumers. Managed results, durable production reuse, provider work and exact stop
retain their own owners and observed states.

**Planned amendment · 2026-11-19.** Integrate
[code-closure review I04](../../plan_improvement_reviews/unified-domain-model-code-dependency-closure_2026-11-19.md#I04)
from commit `1982a20c3` into the existing authoring and selected-read routes. Add the local
`--explain-reuse` option to `ci schema native-candidate`, the model-change preparation routes,
`ci query` and `ci contributions list`. This projects the facts already produced by the owning
operation. The [UDM-10 follow-up](programs-identity-and-revisions.md#udm-10-code-closure)
owns typed closure facts and unknowns, and UDM-14/15 own actual retention eligibility and
native authorization. Requesting explanation never bypasses a prerequisite or performs a
second dependency scan against a later checkout.

The typed bounded explanation names the entry point, affected tier, whether derivation or reuse
proceeded, the blocking source site and semantic owner, the supported dependency path where
known, and the next supported action. Preserve distinct standing for proven relationships,
runtime observations and unresolved edges. A bounded view reports omitted detail explicitly.
The ordinary public read keeps its compact eligibility report, with source detail exposed only
through this opt-in local route. Each response's authorization still governs its native facts.
The JSON and terminal presentations consume one explanation product. A fresh CLI report names
the actual observed process and never claims another process's counters.

Use the existing managed-result inspection route when a retained authoring result is selected,
and its retained explanation where available. Missing prior detail is reported as unavailable.
Do not reconstruct it from current code under the old result's identity. The first-source-site
and omitted-count formatter in `semantic/serving_code.py` moves to the shared typed report
when its CLI and MCP consumers migrate. The compact public projection remains a consumer of
that report. Complete this migration with the new explanation path.

## Library realization and output contract

The installed pins at the source baseline are **Typer 0.28.0** and **Rich 15.0.0**. The repository's
[Typer overview](../../libraries/python_introspection/typer.md) describes 0.27.3; use the selected
0.28.0 APIs where that difference matters. Keep `cli/app.py` and the explicit lazy registry as
the command declaration owner. Use `Typer.add_typer` and ordinary command/callback declarations;
`Annotated[..., typer.Option(..., rich_help_panel=...)]` groups selection, effects and output
options. Bounded local/static completion uses `autocompletion`; completion/help must not connect
to a database or prepare providers. `Context.get_parameter_source` identifies explicit CLI input,
but application policy resolution owns the merged effective policy. `Context.with_resource`
retains the existing command-scope cleanup route. These contracts are in
[Typer 0.28.0 main.py](https://github.com/fastapi/typer/blob/0.28.0/typer/main.py),
[params.py](https://github.com/fastapi/typer/blob/0.28.0/typer/params.py) and
[vendored Context](https://github.com/fastapi/typer/blob/0.28.0/typer/_click/core.py).

Use Rich `Table.add_row` and `Tree.add` for nested reasons, and optionally one `Live` scope over
`cli/output.py:stderr_console` for an interactive watcher. Set `auto_refresh=False`,
`redirect_stdout=False` and `redirect_stderr=False`; update the renderable with
`Live.update(..., refresh=True)` when a new observation arrives. Rich's default stream
redirection would otherwise interfere with machine output. `Progress.add_task(total=None)` can
show an indeterminate phase; `Progress.update` may set known completed/total values only from
the matching scoped owner facts. Native semantics never derive from these display objects.
See [Rich 15.0.0 Live](https://github.com/Textualize/rich/blob/v15.0.0/docs/source/live.rst) and
[Progress](https://github.com/Textualize/rich/blob/v15.0.0/docs/source/progress.rst), with
[Table](https://github.com/Textualize/rich/blob/v15.0.0/rich/table.py) and
[Tree](https://github.com/Textualize/rich/blob/v15.0.0/rich/tree.py) for the nested static view.

Keep `--json` to one versioned typed document on stdout, diagnostics on stderr, and a bounded
plain view for noninteractive watch. Use the existing `emit`/Pydantic 2.14.1
[`BaseModel.model_dump_json()`](https://docs.pydantic.dev/latest/concepts/serialization/#json-mode)
route for JSON rather than serializing Rich renderables. Reuse the output owner's outcome-specific exit and
closed-pipe behavior. Do not cache a console whose captured streams break `CliRunner` or redirect
managed report bytes through a live display. Terminal, plain and JSON representations consume
the same facts. `typer.testing.CliRunner.invoke` supplies focused command tests without creating
another command harness ([0.28.0 testing.py](https://github.com/fastapi/typer/blob/0.28.0/typer/testing.py)).
Cachetools 8.0.1 API choices and their conditions remain in the [cache companion](cache-system.md);
this package adds no cache wrapper or monitoring store.

For the local reuse explanation, declare the option through Typer 0.28.0
`Annotated[bool, typer.Option(..., rich_help_panel=...)]` on the existing commands. Serialize
its Pydantic 2.14.1 report using `BaseModel.model_dump_json()` through the existing output
owner. Use Rich 15.0.0 `Table.add_row` for site and status columns and `Tree.add` for a bounded
dependency path, deriving both from typed facts. A static explanation requires no `Live` scope.
The API references above supply these contracts. Test option forwarding, omitted-detail
standing and matching facts in terminal and JSON with `typer.testing.CliRunner.invoke`.

<a id="udm-26"></a>

## UDM-26 — Typed operational journeys and thin CLI presentation

**Implementation vision.** Extend existing managed and native command owners with the contracts
above. Add a passive `ci run preview` and `ci run resume --result RESULT_ID` for managed-result
recovery; existing `ci run resume DEMAND_ID` remains the explicit native-demand path. Make the
positional demand and `--result` selections mutually exclusive. The important distinction is
managed result versus native demand, never an ambiguous identifier interpreted by guessing.
Existing `ci results inspect/watch`, `ci demands read`, `ci cache stats/prune` and
`ci model change` commands adopt the shared typed reports. Help explains effects at each entry
point, links the next relevant command and gives a bounded request example. These are the
proposed operator interfaces; source/policy files below are supplied through their existing typed
input owners, and credentials/target configuration use the existing explicit configuration route:

```sh
ci run preview --request request.json --source-root SOURCE_ROOT --execution-policy policy.json --json
ci run resume --result RESULT_ID --json
ci run resume --result RESULT_ID --execution-policy revised-policy.json --json
ci results inspect RESULT_ID --json
ci results watch RESULT_ID --seconds 30 --json
ci results stop RESULT_ID --reason "operator-requested interruption" --json
```

`resume --result` obtains the source-root and policy from the captured account when sufficient;
if source custody requires an explicit replacement root, its typed refusal names that missing
input and the supplied root must pass the same basis checks. `watch --json` emits one bounded
final document rather than a stream of unrelated JSON objects. Keep the current direct-demand
route for deliberate native-demand execution; do not infer a managed result ID from its shape.

**Early slice, independent of UDM-20.** Capture the typed request, effective policy and configured
target before preparation; add passive preview, managed recovery selection, typed next actions and
the retained/available observation projection. Existing native binding, request and provider
facts suffice for this slice. Missing future reuse or identity facts stay explicitly unavailable;
early recovery uses the existing exact-demand/request route and does not claim UDM-25's new
retained-work guarantees. Do not construct a temporary predictor. Deliver it before UDM-20's reproduction so diagnosis
consumes the same future-facing interface rather than creating a dependency on the investigation.
UDM-20 may discover a defect and route it to this owner, but is not a prerequisite to implementing
the early contract.

**Mature slice.** Once UDM-04, UDM-09–12 and UDM-25 provide their implemented typed products, wire
compiled-model/program/validity/material-reuse consequences into the existing projection and
model-change reports. Consume UDM-13/14 statistics and maintenance reports as those packages land.
The local code-reuse explanation consumes UDM-10's implemented closure facts and UDM-14/15's
actual eligibility decisions. It can report unresolved custody before real reuse qualifies.
UDM-21/23 exercise Standard/Integrated observations with actual native/provider owners. Deliver
the complete package before UDM-22/23's assembled qualification; an early usable report does not
close its mature integration obligations.

**Complete consumer migration.** Include `cli/orchestrate.py` run/resume/cancel/tasks,
`cli/demands.py` create/plan/read/execute/cancel, `cli/managed.py` inspect/watch,
`cli/result_inspection.py`, `cli/observations.py`, `cli/observation_logging.py`,
`orchestrate/source_reporting.py`, `cli/status.py`, `cli/model.py`, `cli/source_inspection.py`,
`cli/target.py`, `cli/schema.py`, `cli/selected_results.py`, and the output/registration owners
where their interfaces change. Include `semantic/serving_code.py`'s compact report consumers.
Source/PDF
entry points and MCP callers using the same execution/report services must retain their exact
bindings and consume the revised contracts. Enumerate the actual call sites at entry; the list
is migration scope, not permission to duplicate their semantic owners. Coordinate shared edits
with UDM-04/09–14/25 and UDM-27.

**Removes.** Shell-only partial recovery reconstruction, duplicate status/progress interpretation,
ambiguous complete-count displays, the separate first-site code-reuse formatter and stale
preview/report consumers when their successor lands.
Keep legitimate native-demand entry points; no permanent adapter to inferred historical defaults
is required. **Native revision:** none for the presentation/recovery contracts themselves;
native facts and any installed changes remain with their semantic package.

**Acceptance evidence.** Focused native/application and CLI checks establish these distinctions:

- Preview leaves demand registration, claims, provider preparation/inference and publication
  untouched, including on wrong-target and authentication failure. A pre-registration preparation
  failure still retains a usable request/policy account.
- A fresh process recovering an invocation retains its effective physical policy and exact
  selections despite changed defaults or an edited policy file. An explicit memory-policy
  override is visible in both predecessor linkage and the new effective report. Missing old
  capture yields an actionable missing-input result rather than guessed policy.
- Wrong-target inspection preserves managed observations, marks native facts unavailable and
  names the configured selection required. It neither writes nor follows an arbitrary receipt URL.
- Independent expected observations distinguish a partial frontier from a complete scoped count,
  documents from sentence occurrences, provider loaded from inference completed, and stale from
  current activity. Terminal and JSON expose the same distinctions and native reuse reasons.
- A vocabulary change, a validity-only change and an authoring edit with no installed-byte change
  produce the corresponding owner-supplied impact. Exact reviewed changes apply through the
  existing model-change command; stale previews refuse and partial effects remain inspectable.
- Help/completion stays passive. TTY, non-TTY, piped JSON and closed-pipe paths preserve report
  custody and exit behavior. Cancelling watch closes only the watcher. Cache reports do not claim
  remote process counters or native-product invalidation from a local clear/prune.
- `--explain-reuse` shows the actual authoring or read operation's eligibility and owner-supplied
  dependency path in bounded terminal and JSON views. An unresolved site, a proven exclusion
  and a runtime observation keep their distinct standing. Missing prior detail is unavailable.
  The compact public response keeps its eligibility projection, and an opt-in explanation
  grants no additional native authority or reusable identity.

Use independently stated expected selections/counts/effects and injected boundaries that fail if
preview mutates or prepares providers. Do not validate a report by comparing it with another
rendering of the same incorrect transformation. Targeted checks belong at the coherent capability
endpoint; full native/provider/fault coverage remains UDM-22/23, not a new per-report gate.

<a id="udm-27"></a>

## UDM-27 — Exact managed-invocation stop

**Implementation vision.** Add `ci results stop RESULT_ID --reason ...` as a managed action over
one exact execution invocation. It returns a typed stop account and next action, sharing UDM-26's
projection. It is distinct from `ci demands cancel` / `ci run cancel`, whose native effect is
demand detachment and preservation of independent producer interest. Each report states the actual
effect and surviving interest; neither promises a process stopped because a demand detached.

**Prerequisite and bounded control work.** The existing process execution host exposes
process-local retirement, not an authenticated external stop endpoint.
`orchestrate/execution_host.py:ProcessExecutionHost` and the run's cancellation/retirement owner
must provide an exact owned invocation-to-host/run binding and a local authenticated control
route. Capture process-start identity as well as PID, so PID reuse cannot target another process.
Use that route only after verifying invocation ownership and current process identity. Resolve
the smallest supported same-host control mechanism at package entry against the managed process
and host contracts. Do not introduce a daemon, distributed scheduler or broad process-group kill
as a substitute. If a necessary lifecycle decision changes ADR-0125, route the decision through
its existing ADR/design owner before implementation rather than hiding it in the CLI adapter.

**Lifecycle.** The command submits cancellation to the exact active run owner, which stops new
admission and signals cooperative work through its existing protocol. Submitted requests retain
their charges and custody until collection or proven generation retirement. Late replies are
handled by native/run fences. The host retains quarantine on uncertain retirement; provider and
CPU owners settle their resources. Report `stop requested`, `draining`, `unresolved custody` or
`confirmed retirement` only when the corresponding owner establishes that fact. Request acceptance
is not confirmation. Repeating stop reads the known drain/settlement state and cannot create a
second retirement owner. Already terminal invocations return their established outcome.

A stale identity, unsupported ownership, unavailable control route or unreachable host gives an
explicit refusal or unavailable state with a safe next action. The managed observation can record
an external interrupt without claiming physical retirement. Preserve failed/interrupted records
and receipt holds. A later resume uses UDM-26's captured context and UDM-25/native recovery; stop
does not invalidate acknowledged work or independently retained useful evidence.

**Complete consumer scope and removals.** Update managed result actions, invocation/process
identity capture, execution-host/run cancellation entry, observation/inspection rendering and
help. Adopt the exact stop action in qualification's interruption journey and operator recovery
guidance. Replace manual process discovery/unauthenticated kill recipes for this supported journey;
retain documented administrative recovery when ownership or retirement cannot be established.
There is one execution and retirement implementation, with no compatibility stop backend.
**Prerequisites:** UDM-26's exact bindings/projection and the owned authenticated control route
above. Early passive UDM-26 does not wait for this package. **Native revision:** none solely for
the control facade; native settlement changes, if discovery requires them, belong to their owner.

**Acceptance evidence.** Exercise a running invocation, repeated stop, already-terminal stop,
unreachable host, stale/PID-reused identity and unsupported ownership. Verify the wrong process is
never signalled. With two callers sharing native producer interest, cancelling one demand leaves
the other interest useful; stopping one invocation reports its physical effect separately from
that native interest. Controlled in-flight CPU/provider cases establish admission stop, late-reply
handling, lease/intent custody, drain and proven retirement; an unconfirmed join remains quarantined
and never reports released capacity. JSON and terminal retain nested uncertainty and the same
outcome. UDM-23 uses the installed command for actual controlled interruption and managed recovery;
bounded fakes establish refusal/control logic, not actual-provider retirement qualification.

## Completion and documentation integration

**Tested, 2026-11-19.** The installed passive preview returned its typed account with database
and GPU acquisition unavailable. The joined `uv run ci test` selection of execution context,
operational reports, managed stop and model inspection passed all 42 identities
(`d5ab9e5caa774a199c69e878acb8572f`). It exercised exact fractional values through persisted scope
and policy, distinct unavailable native views, and authenticated stop across processes. Pending
stop, stale owner, terminal outcome and unresolved retirement have separate responses. The
owning checks establish these bounded behaviors. Actual-provider drain and repeat across the
exact recovered book demand remain in UDM-22 and UDM-23.

**Tested, 2026-11-20 UTC.** A managed N36 Standard capture was stopped during
observed CUDA compute. It reported `stop_requested` and `draining`, then an
unconfirmed transport-thread retirement. The worker exited and GPU
allocation cleared. A fresh native read still showed a live lease on the
exact attempt. The result retains unresolved custody, and the UDM-27
follow-up must verify join and lease release together. [Actual stop evidence](../../design_review/evidence/2026-11-20_udm27-managed-stop/README.md)

With the transport repair and a freshly admitted N36 runtime, the live
capture stopped while its owned CUDA worker was active. The exact result
`ddaaf6e8c03946b3bca4cf5b9970300e` settled interrupted with
`confirmed_retirement`. The worker, GPU allocation and native task lease
were clear at independent readback. The shared native interest control also
passed under the existing exact request identity.
Managed resume `dc348ca3780f4a96ad7dd8378389cc98` then published three source
receipts on the same demand. Its unchanged repeat
`5b739336836c439b93d8fc47cd151d2e` returned zero new receipts.

An actual stage invocation used `ci run resume --result` and reacquired the original demand after
its Docling capture had already published (`a725a0505d5a455a8fd7f78386805186`). The organizer
subsequently refused stale runtime custody. While that invocation was active, the installed
`ci results watch --seconds 3 --json` returned an available native view and continued execution.
This closed a live watch defect that tried to read a recovery artifact before settlement.
The integrated CLI and reader controls passed all 61 selections after that repair
(`859248a2e468424baa6546ceeab22d5e`).
On 2026-11-19, a passive watch of the corrected N36 one-page Standard invocation
(`bc94c35adc3e438b8e4eb771d4ccb155`) returned an active demand on the acquired stage.
The invocation continued after the watcher exited and published all 11 receipts.
[Live readback](../../design_review/evidence/2026-11-19_udm20-regional-confirmation/raw/n36-full-family-live-watch.json)

An exact managed repeat from the completed result (`815c8161fe4a446892c127d195ec67d6`)
retained the same native demand, frozen selection, execution policy, source root and limits.
The fresh read matched all obligations, producer requests, intents and derivations and
reported zero new publication receipts.
[Exact repeat](../../design_review/evidence/2026-11-19_udm20-regional-confirmation/raw/n36-full-family-exact-repeat.json)

The [D8 interface](../../design/D8-agent-and-query-interfaces.md#shared-policy-settings-status-and-characterization-resume)
records the installed preview, managed resume and cooperative stop routes. Capturing a fractional
scope uses the existing exact DDO JSON codec. Typed model and reuse-explanation reports retain
their ordinary presentation route.

The coordinator owns live package status and finding disposition. At implementation closure,
update the CLI architectural owner and relevant operator guidance with the actual command
signatures, target-selection route and report semantics; extend ADR/design records only where a
binding decision changes. The root integrates UDM-22/23's final-source evidence and preserves
failed/interrupted managed records. Completion requires all affected command/report consumers to
use the authoritative contracts and superseded interpretation/recovery code to be removed; a
new report type or accepted lifecycle decision alone does not complete either package.
