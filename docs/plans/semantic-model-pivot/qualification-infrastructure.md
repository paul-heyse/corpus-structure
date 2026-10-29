# Qualification infrastructure and outcome accounting

**Status:** Planned · **Created/Revised:** 2026-10-29. Consumes improvement review
[I10](../../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md#I10) and
[I11](../../plan_improvement_reviews/semantic-model-pivot_2026-10-29.md#I11), CBO-010/011 and CA-09/10.
[Coordinator §14](../semantic-model-pivot_2026-10-29.md#14-improvement-integration-2026-10-29)
owns state; original SP-10 retains final assembled acceptance. This document owns SP-I08/SP-I09
supporting capabilities, not a new evidence or qualification service.

## Foundation and accepted interpretation

The existing native fixture supplies actual PostgreSQL commits and restricted logins, but repeats
migration preparation for consumer cases. Existing raw qualification output retained a failure
marker and interruption without a final node/assertion summary. Improve preparation reuse and
failure attribution without reducing the declared required union or manufacturing passes.

On 2026-10-29 the operator accepted fresh per-test clones of a session-built migrated template,
with ACL/settings replay and independent posture checks, while cold bootstrap/revision cases
retain actual deployment. This equivalence interpretation belongs in the scheduled decision and
architectural update before fixture adoption. No existing passing types/tests are invalidated by
lint-only work; no automatic re-run follows formatting.

<a id="SP-I08"></a>
## SP-I08 — Session native preparation and actual principal posture

**Owner:** existing native test-support lifecycle. **Input:** SP-I03 purpose/principal contract;
fixture API design and baseline cold path can proceed earlier. **Output:** head template/fresh
clones, bare/revision fixtures, shared evaluator fixture and one residue owner.

Build the frozen semantic deployment from bare once per session. Clone a fresh database per
consumer test, replay database-level ACLs/settings and assert their equivalence; templates do
not copy database GRANTs or ALTER DATABASE SET. Cluster-wide roles remain shared prerequisites.
Do not use outer rollback/TRUNCATE reset instead of real commits and multiple logins.

Keep bare bootstrap for migration/bootstrap/db-init and prior-revision upgrade controls. A
semantic_database_at(revision) route must create era-shaped data before upgrading, including old
CHECK expressions that fresh bootstrap cannot reveal. Use one existing cleanup/lease owner,
close owned pools/readers and wait boundedly for normal backend exit. Do not broaden terminate
rights to make cleanup convenient. Dispose only authenticated owned databases.

Preflight writer/reader/evaluator/publisher/admission roles through the centralized role owner;
actual expected privileges in tests remain independently specified. Posture checks cover TEMP,
schema ownership, direct admitted DML, archive admission, role escalation and clone ACL/settings
loss. The writer workspace policy must match the adopted SP-I03 decision, not whichever grant a
fixture inherited. Scope-only component checks should not require native acquisition.

Prefer session-only template lifetime. Persistent cross-session reuse adds migration/environment/
role-OID key and invalidation obligations without a current need. Standard-release fixture inputs
may use SP-I04 pure composition at session scope after compatibility is settled.

**Acceptance:** clone isolation, missing/alternate roles, database ACL/default mismatch, native
commit/race, cancellation and leaked backend cleanup; both cold and revision-upgrade paths remain
exercised. Reduced repeated setup is structural reasoning, not a measured speedup claim.

<a id="SP-I09"></a>
## SP-I09 — Streamed outcomes and required-scope qualification

**Owner:** root test-command integration and existing evidence conventions.
**Input:** existing pytest/native routes; can be implemented independently of product changes.
**Output:** report stream/watchdog/classification route with explicit context and final-union accounting.

Use pinned pytest-reportlog for flushed collection/setup/call/teardown/session events and installed
pytest 9.2 faulthandler_timeout/faulthandler_exit_on_timeout. The grammar cancels SIGALRM timers;
a signal-based outer timeout can silently disappear. A generous watchdog bound is hang policy,
not a latency target. Preserve worker/node/phase identities and original logs; collection order
cannot infer parallel execution or the hung node.

Classify reported passes/failures as reported; required missing prerequisites remain blocked with
reason; collected but unexecuted obligations are not_run. Preserve intentional inapplicable skips
separately from required-provider absence. Missing SessionFinish is incomplete qualification.
A process failure with unknown node remains a process failure, not an invented assertion. Retain
already completed reports across call/teardown hangs, worker loss and forced exit.

Use a small stdlib classifier over existing artifacts, not another evidence registry. Record masked
settings, source/selection, server and driver context plus rustc version where Rust ran. nextest
zero tests must not establish functional coverage. Keep Hypothesis CI replay/versioned blobs and
durable independent examples; development exploration remains distinct. Add the reporting dependency
exactly and run readiness only when that dependency/process move is actually implemented.

Define the final required functional/native/provider/nonfunctional union in the existing SP-10
owner, with applicable node selections/context rather than overlapping count arithmetic. Supply
meaningful bound-run environment-change evidence for CA-09. Settle actual cross-field invariant
applicability explicitly; do not invent a constraint/test to satisfy prose.

**Acceptance:** collection error, assertion error, teardown failure, call/teardown hang, killed
session, worker loss, required provider skip, optional deselection and absent summary. Preserve
raw failed/interrupted receipts. Classifier controls are independent small event fixtures; no
full product campaign is needed merely to implement reporting.

## Timing and final acceptance

Implement coherent capabilities with targeted functional checks. Resolve structural type errors,
warnings and suppressions at relevant endpoints; unchanged scope may be checked independently.
At complete functional scope, run the applicable final union and broad test/hygiene routes.
Root turn-end formatting does not trigger another type/test campaign. A substantive source,
harness or environment change requires only genuinely affected evidence to be reassessed.

Original SP-09 still requires actual source/provider statistics and transfer workflows, evidence-
backed query/export and independent automated grading, plus current source-frame continuation.
Mocks, fixture construction and report classification cannot establish those results. Existing
reference scores remain unchanged; no human grading, model-quality tuning or regrading is added.
Documentation checks establish publication integrity only.
