# Qualification infrastructure and outcome accounting

**Status:** SP-I08/SP-I09 partial after completion audit; scoped receipts retained · **Created/Revised:** 2026-10-29. Consumes improvement review
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
retain actual deployment. [ADR-0032](../../adr/0032-native-test-deployment-equivalence.md) and
D3 now own that interpretation. No existing passing types/tests are invalidated by
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

Use pinned pytest-reportlog for flushed completed collection/setup/call/teardown/session reports
and a public-hook companion for exact collection selections and phase starts. Reportlog does
not supply the node manifest: pytest serializes `CollectReport.result` as null. Use installed
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

## Execution checkpoint — 2026-10-29

**Delivered mechanisms; scoped Tested, with remaining implementation below.** Source is the SP-I08/SP-I09 changes following `8170926`, with
the acceptance fixture dependency repair described in verification. SP-09 operational work and
SP-10 complete qualification retain their owners. No operational database, selected answer,
automated grade or existing MCP host was regenerated or restarted.

### Native mechanisms and retained boundaries

`scripts/native_test_support.py` generalizes the existing `PgAdmin` lifecycle; importing it
acquires no resources. SQLAlchemy `NullPool`, explicit AUTOCOMMIT CREATE/DROP, advisory leases
and authenticated names/comments replace separate semantic cleanup and forced termination.
The semantic head is migrated once per session, its migration engine disposed, then sealed
with `ALLOW_CONNECTIONS false` and `IS_TEMPLATE false`. Fresh consumer clones permit connections
and real commits. The legacy migration/extension-keyed cache and rollback fixtures remain.

`DatabasePolicy` captures owner/connection limit, normalized
`aclexplode(COALESCE(datacl,acldefault('d',datdba)))` including grantors/options, and every
database-specific `pg_db_role_setting` entry. Replay restores database/default ACL state and
database/role defaults, then compares exact normalized catalogs. Current owner-granted ACLs
have a direct replay; non-owner grant graphs refuse explicitly. Role defaults use existing
authorized SET ROLE or an actual matching purpose login on `postgres`, checked through
`current_user/session_user`. Original settings resolve credentials before the owned database
substitution. No administrative password inheritance or new memberships are introduced.
List-valued and read-only defaults use PostgreSQL's parameterized
`pg_catalog.set_config(...,true)` followed by `SET ... FROM CURRENT` inside real READ COMMITTED
SQLAlchemy transactions on `postgres`; plain quoted `TO` values incorrectly change a
`search_path` list into one schema name. Independent all-role, owner-role and restricted-reader
vectors cover exact list values, read-only defaults and restoration. CREATE/DROP/ACL operations
remain AUTOCOMMIT. The package parent owns the single session fixture definition so sibling
acceptance imports cannot accidentally create a second head; a two-directory control observed
one actual `SETUP S semantic_head_template`.

The provisioning script factors canonical principal names once and exposes read-only
`--principals`; one preflight checks publisher/writer/reader/evaluator/admitter. Actual runtime
admissibility remains capability-based, preserving alternate logins. Independent tests require
restricted TEMP/DML/escalation denial and protected publisher workspaces. Generic TEMP is not
restored to the writer or admission login.

`semantic_bare_engine`, reserved absent-name CLI initialization and
`semantic_database_at(revision)` preserve actual deployment controls. Historical archive data
and altered CHECK/kernel variants really start at semantic_0030 and upgrade through 0031/0032.
Shared evaluator/admitter fixtures replace local engines. Fixture-dependency marking includes
semantic resources; `db_support` and component-only controls remain pure. Existing bounded
compiler caches remain; no populated release template or global prepared-release cache was added.

Cleanup protection starts before CREATE/tag/engine construction and handles cancellation,
engine disposal failure and a racing CREATE collision without acquiring disposal authority
over an existing database. Owned connections/pools are closed, then SQLSTATE55006 receives the
existing two-second normal-exit retry. Independent cleanup attempts settle before failure
propagation. A leaked backend remains an actionable bounded failure; no FORCE/terminate rights
are used. Sweeping requires namespace, owner, comment and an exclusive lease. Untagged older
semantic residue is not silently adopted. Actual server/current-user/psycopg context and masked
settings are recorded by both semantic and legacy acquisition routes.

### Reporting, scope and settings mechanisms

`pytest-reportlog==1.0.0` is the only dependency addition. Its flushed reports remain the outcome
source. `qualification_plugin` records collection/deselection, process/worker/node identity,
wrapped phase starts and protocol finishes through public pytest hooks. A passing case requires
successful setup, call and teardown plus completion; omitted complete lines cannot manufacture
a pass. Raw skips, xfail details, assertions and collector/teardown failures remain intact.
Only tagged known external preflight absence/incompatibility is classified as blocked; actual
authentication/configuration/migration/posture/cleanup failures remain failures.

The stdlib `scripts/test_receipts.py` runner accepts `run --out-dir PATH [--python-only]
[--test-timeout SECONDS] [--command-timeout SECONDS] -- PYTEST_ARGS...` and
`classify --receipt-dir PATH [--receipt-dir PATH...] [--required-from MANIFEST...]`.
New directories refuse overwrite. Default watchdogs are 900 seconds per pytest protocol and
14,400 seconds per command, recorded as hang policy rather than latency targets. Pytest's
`faulthandler.dump_traceback_later(exit=True)` is independent of SIGALRM. The parent deadline
covers collection/session hangs and drains surviving owned process groups after ordinary or
abrupt leader exit. Cancellation stops subsequent commands. Completed reports survive forced
exit, missing SessionFinish and truncated streams; unknown attribution stays a process failure.

`test-all` uses this route, with independent Python/Rust attempts; `check`/`py-test` remain
developer commands. Native nextest selection/JUnit/toolchain artifacts are retained. An empty
Rust scaffold is explicitly `not_run` with no functional coverage, and does not create a
nonexistent required Rust obligation. A requested but missing Rust route is incomplete.

Invocation/source context, masked settings, acquired native context and actual outcomes remain
separate. Differing source contexts are surfaced for owner applicability judgment rather than
automatically invalidating evidence after formatting. Explicit required manifests come from
collected selections, not a second maintained registry. Historical failed sessions remain
failed even when later applicable receipts cover repaired required nodes. Hypothesis uses the
existing CI profile and versioned failure blobs; independent examples remain durable controls.

CA-09 now has an actual environment-created MCP lifespan control: a leased valid submission
retains its task/run/release after the default project changes, and a fresh owner refuses the
old run under the new project. Purpose endpoint conflicts cover database, host, port and
non-authentication query options through the existing runtime resolver; no artificial settings
validator was added. Settings reports also mask URL query credentials and endpoint credentials.

### Verification

**passed, 2026-10-29:** 805 distinct required cases have applicable passing reports, with no
unresolved required node. `build/test-receipts/sp-i08-i09/scoped-union.json` records exact node
coverage, individual session/process health and differing source contexts; its recorded command
is `scoped-union-command.txt`. The required manifests are the 802-case affected selection plus
two sibling acceptance cases and one repaired stored-scope adapter case. Additional focused
receipts strengthen the same node obligations rather than increasing the distinct count.

Recorded commands and outcomes:

| Command | Outcome / receipt |
|---|---|
| `uv run python scripts/test_receipts.py run --python-only --out-dir build/test-receipts/sp-i08-i09/affected-final -- python/corpus-structure/tests/semantic python/corpus-structure/tests/db python/corpus-structure/tests/test_db_fixtures.py python/corpus-structure/tests/test_settings.py python/corpus-structure/tests/test_semantic_runtime_settings.py tests/scripts/test_test_receipts.py` | **passed:** 802 cases, complete streamed session; `affected-final/`. |
| Same runner, selecting `python/corpus-structure/tests/acceptance/test_regeneration.py` | **passed:** two cases; `acceptance-fixture-final/`. |
| Same runner, selecting `python/corpus-structure/tests/agent/test_packet.py::test_the_stored_scope_adapter_gives_the_in_memory_standing_context` | **passed:** one case; `stored-scope-adapter-final/`. The legacy test adapter now supplies actual occurrence identities to the current draft builder. Production parsing behavior did not change. |
| Same runner, selecting the three ACL/default, restricted-reader and unsupported-grant-graph policy controls | **passed:** `list-setting-replay/`. Raw failed quoted-list replay remains in `list-setting-control/`. |
| Same runner with `--setup-show`, selecting toy acceptance and native sealed-head controls together | **passed:** `shared-template-owner-final/`, one package-wide head setup across sibling directories. |
| `just test-all tests/scripts/test_test_receipts.py::test_empty_rust_selection_does_not_fail_python_coverage` | **passed:** real combined route `build/test-receipts/qualification/20261030T011531Z-2697066/`; Rust selection is empty, explicitly no functional coverage. `rustc 1.101.0-nightly (41089d07a 2026-10-27)`. |
| `uv run pyrefly check --min-severity warn --summary=none` and warning-aware checks of substantively repaired files | **passed:** zero errors/warnings, no suppression additions. `types.log`, `types-fixture-repairs.log`, `types-final-support.log`; passing results were not invalidated by formatting. |
| `just ready` after the exact reporting dependency addition | **passed** in the reporter implementation handoff. |
| `just lint-agents adr-lint rules-scan rules-test docs-check deps`; `just clippy` | Agent/ADR/docs/dependency/Clippy checks **passed**; rule scan/tests **not_run** because no rules exist. `hygiene-applicable.log`, `clippy.log`. |
| `just turn-end`; `just docs-check`; Ruff on changed Python files; `git diff --check` | **passed:** `turn-end-final.log`, `docs-check-final.log`, `ruff-changed-final.log`. No functional/type rerun followed these maintenance-only edits. |
| `uv run ruff check` | **failed:** 19 existing diagnostics in untouched files; `ruff-all.log`. Whole repository hygiene is not claimed passed. |

Source applicability is explicit. The final settings repair changes the default-value replay
branch, covered by the new list/read-only vectors; the frozen consumer head has no such
database defaults. Moving the unchanged head builder to its single parent owner changes
visibility/reuse, covered across sibling consumers. Earlier applicable consumer/type receipts
remain valid. Formatting and documentation do not trigger another functional/type campaign.

The initial broad `just test-all` invocation at
`build/test-receipts/qualification/20261030T010324Z-2538438/` is **failed and incomplete**: it
recorded two missing sibling template dependencies and a stale stored-scope test adapter, then
was interrupted during the existing 78-page mathematical corpus analysis. The scoped repairs
above passed. Raw failure reports, active phase, process interruption and missing session finish
remain available; its completed case reports were retained, and Rust was correctly not started
after cancellation. The corpus analysis is outside this supporting change and remains with
SP-10's broad acceptance. This invocation is not relabelled as passing.

Earlier focused native/type corrections retain their tool-session outcomes; reporter child
failure/hang/kill streams remain under `reporter-controls-20261029/` and
`reporter-review-fixes-20261029/`. OAK/SSSOM and bounded Alembic warnings are third-party/runtime
warnings, not Pyrefly diagnostics. No latency, capacity or extraction-quality benefit was measured.
SP-09 operational workflows and complete SP-10 functional/provider/nonfunctional acceptance
remain open; this supporting package adds no human grading or regrading obligation.

## Completion audit — 2026-10-29

**SP-I08 and SP-I09 are partial at clean `d004504`.** This package assessment is part of the
all-SP-I01–SP-I09 audit, not a separate declaration that the rest of the series is complete.
[Coordinator findings](../semantic-model-pivot_2026-10-29.md#findings-and-remaining-obligations)
own CA-21/CA-22 and actionable closure.

- **CA-21 / SP-I08:** the reserved CLI database route authenticates a database owner but not the
  operation that created it. An intervening same-owner creator can have its database adopted by
  CLI initialization and later dropped by `reserved(... require_comment=False)`. The explicit
  CREATE-collision protection tested for `database()` does not cover this route. Authenticate
  creation/identity before cleanup and verify a reserved-path collision/cancellation case.
- **CA-22 / SP-I09:** external SIGTERM to the supervising runner bypasses its timeout/Ctrl-C
  handler and detached-child drain. Implement supported termination handling, preserve process
  receipts and prevent subsequent Rust work; an actual parent-signal control must discriminate
  this path from existing killed-child and KeyboardInterrupt controls.

The audit credited actual PostgreSQL cloning, normalized ACL/default capture, SQLAlchemy real
transactions with parameterized set_config/SET FROM CURRENT, role-self credentials, canonical
principals, cold/revision migrations and most authenticated cleanup paths. It also credited
reportlog's actual flushed output, public hook gap-filling, pytest's thread watchdog, explicit
required manifests/prerequisites, Hypothesis replay, Rust empty-selection handling and CA-09's
real MCP/settings journey. No API-name-only substitute closed an obligation.

The root independently parsed raw selected manifests, setup/call/teardown records, protocol
finishes and session/process status rather than using the classifier as its own oracle. All
805 selected nodes have applicable passing records across the six named receipts, with source
contexts surfaced. These are valid selected-scope results, not coverage of the two missing
paths. CA-09 stays closed for its named settings obligations; CA-10 and original SP-09/SP-10
remain open. The interrupted corpus campaign and 19 untouched lint diagnostics do not become
passes or automatically invalidate earlier scoped typing/tests. No new test/native/provider
campaign or production repair was performed for these two source-conclusive findings.
