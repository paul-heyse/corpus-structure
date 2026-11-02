# Native infrastructure and qualification

**Status:** Proposed; [coordinator](../test-architecture-and-evidence_2026-11-02.md) owns TA-01–04 state and DTA-002/003/017 disposition.

## Existing foundation and intended boundary

`tests/conftest.py` and `tests/semantic/conftest.py` consume one sealed session deployment;
`scripts/native_test_support.PgAdmin` owns reservations, advisory leases, acknowledged OID/owner
custody, policy replay and cleanup. Production runtime resolves purpose credentials against the
original endpoint before substituting the owned database. Retain these guarantees. A fixture's
administrator is not evidence of the application writer/reader/evaluator/admitter contract.

Separate four responsibilities: provisioning an owned server; deploying and cloning database
state; acquiring application-purpose connections; recording observed acquisition and outcomes.
One mechanism owns each effect. This boundary need not introduce four new abstractions.

## TA-01 — Decide the complete native arrangement

### Inventory and capabilities

Read-only host/catalog inspection during preparation2026-11-02 found Ubuntu24.04.5, PostgreSQL18.6,
postgresql-common293, and online18/corpus5434 alongside unrelated18/main5432 and18/tktest5433.
The installed binaries/dev paths, package candidates, `pg_available_extensions`, `pg_extension`
and active `pg_settings` were inspected without changes. The tree's ops configuration matches
preloads pg_textsearch/pg_stat_statements/auto_explain, max_connections100, max_locks_per_transaction64,
fsync on and synchronous_commit off. These are an observed baseline, not future capacity targets.

| Tool | Actual availability / candidate role |
|---|---|
| pg_virtualenv; pg_createcluster/pg_ctlcluster/pg_conftool | Installed; alternative outer owner for disposable real clusters |
| pgTAP1.3.4; pg_prove | Installed; available extension, absent from cs_template; SQL behavior/privilege assertions |
| plpgsql_check package2.10.16, available extension2.10 | Installed, absent from cs_template; bounded stored-function diagnostics |
| pg_regress, pg_isolation_regress, isolationtester | Installed below /usr/lib/postgresql/18/lib/pgxs/src/test; not on PATH |
| pg_activity, pgBadger; native statistics/auto_explain | Installed; existing diagnostics for a specific lock/setup/recovery uncertainty |
| pytest-postgresql9.1.1 | Documentation research baseline; not selected or added to the Python manifest |

Distinguish package installation, server preload, per-database extension creation and actual use.
Do not add a test extension to the application deployment simply because it is installed.

### Alternatives and decision evidence

Compare PgAdmin on the existing shared cluster; pg_virtualenv as an outer owner with PgAdmin
inner clones; and pytest-postgresql owning disposable server/template state. Also evaluate the
plugin's external-server/template facilities where a selective composition can simplify real work.

The installed pg_virtualenv script exports PGHOST/PGPORT/PGUSER/PGPASSWORD, not application Settings.
It defaults fsync off, catches ordinary signals and immediate-stops its owned cluster. It does not
promise SIGKILL recovery. Explicit version18, private configuration/data/socket paths, application
endpoint adaptation, restricted roles, required preload/extension versions and appropriate durability
settings are part of any pilot. Prefer non-root/private configuration for disposable operation;
sudo remains available for necessary provisioning. Never touch main/tktest or adopt unowned residue.

pytest-postgresql `postgresql_noproc(load=..., depends_on=...)` provides session template layering;
`DatabaseJanitor.init/drop` terminate connections. That default is incompatible with shared-cluster
ADR-0032 disposal. Assess disposable-cluster placement or a genuinely small within-contract adapter;
reject adaptations that recreate most of the library with two competing lifecycle owners. Database
layering does not isolate roles/authentication files. A plugin-provided psycopg connection does not
replace the application's actual SQLAlchemy/psycopg_pool purpose connection.

Execute a small owned native pilot only when implementation of this series is authorized. It must
establish current frozen migration deployment, purpose-login success/refusal, exact ACL/default replay,
explicit application targeting, committed clone isolation and child/server settlement. Inject failure
after creation and between authentication steps; distinguish test-child interruption from outer-owner
termination and hard kill. State residual ownership/recovery obligations honestly. Reuse existing
support and acceptance controls instead of a parallel probe framework.

Return a concrete retain/adopt/adapt disposition per mechanism, selected APIs, removed/retained code,
limitations and revisit conditions. The decision must settle ordinary consumer versus cluster-auth
case placement, supervisor/cluster ownership, and configuration propagation before TA-02 migration.
No runtime measurement is required to establish simpler ownership; quantify benefits only if measured.
If a changed architecture rule is necessary, develop the concrete alternative and obtain its explicit
operator disposition through the coordinator's review/ADR route. Retaining the current owner is a
valid evidence-based result, not a predetermined outcome.

### Native assertion/running tools

Compare one real current guard/posture obligation in pgTAP with its Python counterpart. `throws_ok`
can require SQLSTATE and exact SQLERRM; `results_eq`, `set_eq` and `bag_eq` distinguish ordered/set/
multiplicity semantics. Expectations remain hand-authored, and two-principal guard reach remains
necessary. Use pg_prove's TAP interpretation if selected; do not invent a TAP parser.

Use isolationtester/.spec sessions/steps/permutations for a named transactional-interleaving claim
where it removes incidental synchronization. Keep actual application race tests when their client
boundary matters. pg_regress is a candidate only for a stable independently specified SQL contract.
All native runners get explicit endpoints/owned database names, never default regression targets.

plpgsql_check_function_tb is a candidate diagnostic for a bounded useful function/trigger set.
Runtime-assembled SQL and temporary tables constrain its coverage. It neither establishes native
semantic correctness nor requires new alignment lint or a universal static-analysis gate. Native
statistics, pg_activity and pgBadger are used only to resolve a concrete question; no default profiler,
backup/HA stack, snapshot service or benchmark campaign is introduced.

If another tool is selected, identify its exact version/package provenance, prerequisite installation,
activation and service effects. Relevant sudo installation is already authorized. Use the existing
ready check after environment changes, inspect selective package actions, and avoid wholesale upgrades.

## TA-02 — Own cluster authentication effects and native recovery

`test_alternate_principal.py` currently changes a role and two shared authentication files. Select
isolation in an owned disposable cluster if TA-01 establishes it; otherwise put authenticated recovery
under the existing lifecycle, with exact effect ownership and live-owner exclusion. Do not equate a
Python finally block or database sweep with recovery of committed cluster effects.

Acquire ownership before effects; record sufficient existing-lifecycle context to distinguish owned
partial setup from unrelated resources. Drain application engines/workers before owned disposal.
Attempt independent cleanups and retain primary plus cleanup failures. Do not broaden shared-cluster
termination privileges. An outer disposable owner can bound cluster-local effects but must still
settle its child process group and acknowledge unrecovered hard-kill residue.

Acceptance: two concurrent sessions cannot dispose each other's resources; failure between role,
first/second auth edit and reload preserves unrelated entries; normal success/failure/cancellation
settles owned resources; owner death is recovered or reported as an explicit outstanding obligation.
An outstanding recovery obligation prevents closure of that TA-02/DTA-002 scope and TA-12
acceptance. Alternatively, an explicitly accepted narrower interruption envelope must retain
its limitation and revisit trigger; reporting residue alone is never closure.
Fresh clone commits/races and cold migration controls remain actual. A native pilot is not product
or full-provider qualification.

## TA-03 — Separate acquisition credentials from application defaults

Capture original coordinates/purpose credentials for native acquisition first. Provide explicit
Settings to test application entrypoints and explicit CORPUS configuration to spawned processes.
Unbound application acquisition receives a refused sentinel target in test scope. Do not change
production defaults merely to make tests hermetic, and do not let that sentinel contaminate the
native administrative or purpose-credential capture. Keep endpoint consistency checks intact.

Migrate package CLI helpers, direct runtime acquisitions, MCP subprocesses and affected tests together.
Explicit empty/override behavior is checked at their real entrypoint. Acceptance pairs an omitted-target
refusal before application SQL with an actual owned-clone success and wrong-endpoint/purpose refusal.
The audit's exposure was suspected; source/controls must establish the path being protected, not
claim a historical misrouted write occurred.

## TA-04 — Record actual acquired context through existing receipts

Extend `record_native_context`/qualification_plugin, not a second evidence system. Keep requested
settings distinct from observed server, database name/OID, deployment revision, replayed-policy
identity and actual purpose principal. Associate acquisition with invocation and available worker/
node/lifetime; session preparation and per-test purpose acquisition have different lifetimes.
Mask secrets and use compact stable references rather than repeating full catalogs per assertion.

Native claims requiring context must not silently report observed provenance when the event is absent.
Retain actual node outcomes, but classify provenance completeness explicitly; pure selections do not
require database events. Extend existing classifier compatibility so old receipts remain historical
with unavailable context rather than being rewritten or falsely upgraded. Selected SQL/TAP/isolation
runners retain stdout/stderr/exit/prerequisites through the existing runner and an unambiguous required
obligation association. Prefer a pytest-facing adapter when it preserves node/phase classification;
a plain successful psql exit cannot stand for successful TAP assertions.

Acceptance covers differing clone versus ambient URL, reader versus maintenance identity, missing
context, pure-only runs, masked credentials, interrupted setup/teardown and old receipts. TA-12 owns
combined required-union acceptance; context hashes alone never establish semantic validity.

## Source references and research strength

Orientation: [Ubuntu tooling](../../libraries/postgresql/PostgreSQL_System_Tooling_for_Ubuntu.md),
[pytest-postgresql](../../libraries/postgresql/pytest-postgresql.md), [psycopg](../../libraries/postgresql/psycopg.md).
Context7 was queried for pytest-postgresql, pytest9.2.0, PostgreSQL18, pgTAP and plpgsql_check;
consequential plugin behavior was checked against tagged9.1.1 source and pg_virtualenv against the
installed293 script. These are Interface-checked capabilities, not successful integration pilots.

- [Plugin factories9.1.1](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/factories/noprocess.py)
- [Plugin janitor9.1.1](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/janitor.py)
- [pg_virtualenv293 documentation](https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html)
- [pgTAP1.3.4 assertions](https://pgtap.org/documentation.html)
- [PostgreSQL18 isolation runner](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/test/isolation/README)
- [plpgsql_check limits](https://github.com/okbob/plpgsql_check#limits)
