# Parallel execution and distributed harness

**Proposed,2026-11-06.** The [coordinator](../test-audit-resolution_2026-11-05.md) owns TR-11/12
state and review I01/I02/I04/I08 disposition. Consume the [tooling review](../../plan_improvement_reviews/test-audit-resolution-tooling_2026-11-06.md)
at23d677be. This companion defines scheduling/collection/report integration, not native identity
meaning, test semantic answers or an independent qualification register.

## Foundation and target

Execution mechanisms selected2026-11-06 from the full library references and review addenda:

| Obligation | Library mechanism and limit |
|---|---|
| Exact collection identity | pytest.hookimpl(wrapper=True,tryfirst=True), pytest.StashKey and item.stash; capture before xdist mutation, journal exact aliases, reject collisions |
| Worker lifecycle | xdist setup/ready/collection/down hooks, worker_id and PYTEST_XDIST_WORKER_COUNT plus actual PID-tagged call intervals; created is not working or overlapping |
| Isolated conformance | Explicit child -n0/-n2 and isolated config/plugin loading; pytester scaffolding only if simpler, retaining run_python/run_process receipt and settlement ownership |
| Preparation | Public collected fixturenames and xdist_group, existing scoped fixture DAG/yield cleanup; no private fixture-manager or new cache service |
| Diagnostics | Rewritten asserts, register_assert_rewrite before imports, narrow assertrepr hook, Item.add_report_section, phase user_properties; no protected-label dump |
| Failures | Existing faulthandler bounds and supervisor settlement, warning/exception-group controls where relevant; worker replacement is not semantic retry |

workerinput is bounded configuration and workeroutput an optional orderly summary, not shared
memory or crash-proof evidence. Ordinary serializable report properties/sections are preferred;
report serialization hooks are conditional on a concrete gap. No pytest9.2-only configuration,
types or plugin loading, xdist development-only options, automatic retries or custom scheduler.

Root `conftest.py` wraps collection, marks the entire package math directory with
`xdist_group('math_preparation')`, and rejects mixed/parallel shared-cluster faults after
deselection. `pyproject.toml` pins pytest9.1.1/xdist3.8.0 and defaults to auto/loadgroup;
`just test-all` inherits that configuration. Keep this compatible pair and builtin scheduler.
Session fixtures are worker-local; auto is CPU discovery, not knowledge of database capacity.
Existing per-worker event files retain PID/worker, selected identities, phases and actual native
acquisition; reportlog remains outcome authority. Preserve this crash-surviving journal.

Target: deterministic collection and exact logical identities across placement; bounded native
and nested worker lifetimes; preparation reuse keyed by its real source/configuration premises;
useful parallel execution without forcing every semantic distinction into a process or fixture.
Pure collection must not acquire native services or compile the semantic model. FP-01/03/06/07,
DP-09/10/15/20/21, CI-10 and test-assessment §3/6/8 motivate these boundaries. H12/H17 favor
valid amortization and combined live-state reasoning rather than simply maximizing workers.

## TR-11 — Worker facts and real distributed conformance

Extend existing public pytest hooks and receipt controls. Record requested worker selection and
effective worker count/identity using xdist metadata and existing PID-tagged events; distinguish
workers created, workers actually executing items and observed overlap. Retain scheduler/group
configuration and nested math pool cap8 in the existing invocation/session context. Do not add a
resource estimator, historical timing scheduler or generic telemetry service. Correct current
instruction surfaces, including the PostgreSQL usage inventory, when implementation adopts the
route; do not rewrite historical16-worker receipts.

Use a small isolated child test suite, explicitly selecting serial or two workers. Cases include
ungrouped items, shared groups, composite groups, fixture-dependent marks, parameter IDs containing
literal `@`, deselection, collection errors, setup failure, teardown failure, and bounded worker
loss. Observe actual selected canonical/native-required manifests and phase/report/native events.
Keep independently authored canned-artifact controls and direct supervisor/process-group tests.
Use pytester.runpytest_subprocess for scaffolding/outcome assertions only when simpler than the
existing child/run_python helper; that helper retains runner ownership. Child config must isolate
plugins/addopts so a two-worker control cannot recursively start auto32 workers. Native identity
controls use real acquired contexts; synthetic artifacts assess the classifier only.

### Exact collection identity contract

The receipt plugin owns an injective raw scheduled-ID → logical collected-ID map; the classifier
consumes it for selected/native-required/report/lifecycle/acquisition/required-from identities.
Raw artifacts stay unchanged. Never strip arbitrary `@` suffixes or silently overwrite a map
entry. Conflicting/colliding selected identities refuse classification; no node can absorb another
node's pass. Ordinary parameter IDs and composite group names remain distinguishable.

Preferred amendment: capture original item.nodeid in item.stash using a public collection wrapper
before xdist's mutation, then emit the exact before/after map after collection. Verify actual hook
ordering for the pinned pair before selecting it; if this does not provide a simpler sound map,
retain collection-derived suffix reconstruction with explicit injectivity checks. Stash is local
state, not worker communication. Serialize the map through existing worker events. Keep the active
native observer bridge; replacing `_stream` or `_current_nodeid` wholesale would add routing
machinery without an established benefit.

Use workerinput only for bounded immutable configuration when required. workeroutput may summarize
orderly completion, but cannot replace journals lost on crash. Ordinary serializable properties
and report sections are preferred to a new report transport. Keep collection, setup, call,
teardown, missing native context, worker loss and process cleanup distinguishable. Do not add
generic crash retries: grouped schedulers do not all support mark_test_pending and external
effects survive some crashes. Faulthandler process termination remains separate from recoverable
per-test timeouts.

**Acceptance:** serial/two-worker selections have the same declared canonical membership;
same-group items have actual affinity; independent work overlaps when enough work is selected;
raw IDs survive; deliberate wrong mapping/grouping is detected; cancellation settles owned
children and leaves incomplete evidence, not a fabricated pass. Fault-lane selection guards are
tested through collection/refusal without repeating actual auth bodies per harness edit.

## TR-12 — Preparation-shaped affinity

Inventory collected dependency closures for `spike_readings/extraction/scoped` and
`s0r2_readings/extraction/scoped`, plus any maintained consumers discovered outside math. These
names locate existing responsibilities, not a permanent external fixture registry. Content-only
fixtures, pure grammar/property kernels and direct cold compiler controls have distinct needs.
Keep staged immutable products and make deliberate mutation consume an owned copy.

Compare coarse directory affinity with dependency-shaped marks under loadgroup. Prefer the narrow
group if it preserves shared parsing/scoping and warm parser/compiler reuse while freeing useful
unrelated work; otherwise record the reason to retain coarse affinity. Fixture closure is the
initial mechanism; an explicit responsibility mark is appropriate only for genuinely dynamic
dependencies not visible to collection. Do not use mere test directory location as the sole
target authority. Keep one shared group where stages share preparation; do not accidentally
split overlapping complete marker combinations across workers.

Loadscope/loadfile provide locality alternatives; worksteal does not preserve loadgroup affinity
in3.8 and uses queue counts, not predicted duration. No custom scheduler is selected. Compare
representative focused and combined selections using actual work counts and retained cases;
elapsed benefit requires measurements if claimed. Do not add a mandatory benchmark campaign.
Consider nested cap8 process work, per-worker model state, native template setup, connections,
locks and storage together. Retain auto as initial default; a justified explicit cap uses existing
CLI/environment settings, not new global server tuning.

**Acceptance:** content-only selection invokes no parsing, read/extract tiers activate no later
stages, combined tiers reuse preparation, and cold compile/positional transport/timeout/cleanup
controls retain their meaning. Independently selected consumers require no collection order.
If narrower grouping is selected, migrate every actual consumer and remove the replaced
directory rule in the same coherent slice. Selection to retain coarse affinity is a valid
decision only with its workload/reuse reasoning recorded at the coordinator.

## Integration and verification timing

TR-11 precedes identity/grouping changes and supplies stable reporting to TR-12/14/15. TR-13 can
develop independent case matrices against delivered WCE04/05 contracts. Their selected auto-worker
322-test result does not qualify new TR-11/12 changes. Definition/applicability and contextual
per-edge-carrier consumers join the harness inventory; their producers are not work to build again.
Native acquisition and
coverage meaning are owned by [native lifecycle](native-lifecycle-and-provenance.md), not here.
TR-09 reconciles replaced helper callers, root hooks and required selections. TR-10 supplies
fresh final-source qualification after selected functionality; focused child controls are not
the full parallel native envelope or WCE semantic qualification.

Sources: [pytest reference](../../libraries/analytical_infrastructure/pytest.md) §4/9/10 and addendum §5/6;
[xdist reference](../../libraries/analytical_infrastructure/pytest-xdist.md) §2–4/6–9 and addendum §1–4;
[pytest9.1.1 hook ordering](https://github.com/pytest-dev/pytest/blob/9.1.1/doc/en/how-to/writing_hook_functions.rst),
[plugin testing](https://github.com/pytest-dev/pytest/blob/9.1.1/doc/en/how-to/writing_plugins.rst),
[xdist3.8 distribution](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/docs/distribution.rst).
These are interface/source grounds; implementation checks, native execution and performance
measurements for TR-11/12 are not_run at plan publication.

## Current implementation — 2026-11-06

Implemented and focused Tested: public Stash capture and exact canonical map, conservative
association eligibility, effective/actual worker facts, real serial/two-worker acquisition using
configured PgAdmin-owned clones, and phase/report-section transport. Existing child/run_python
scaffolding is retained because it already owns receipt/supervisor behavior; pytester is available
but adds no necessary simplification here. Ordinary report sections suffice without a custom
serializer. Workeroutput is not evidence authority.

Dependency-shaped loadgroup replaces the directory rule. Actual172-node math collection has8
staged-preparation consumers and164 independent items. Controlled coarse/narrow selections both
read once and content-only reads zero; warm/cold and spawned worker controls remain. These are
structural work/affinity observations, not measured elapsed benefit. Current receipt/context and
final union are owned by the coordinator; focused counts overlap and do not qualify the full run.
