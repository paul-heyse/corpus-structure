# PostgreSQL tooling and cohort execution

**Status:** Proposed; nothing implemented. **Created:** 2026-11-13.
The [coordinator](../test-system-target-design_2026-11-13.md) owns state, decisions and
completion. This companion owns TS-24/25, selected by the operator's instruction to use
pgTAP, pg_prove and pg_virtualenv to make native infrastructure practical and efficient.
It composes the lifecycle, isolation and evidence owners; it creates no second database owner.

## Basis and foundation assessment

Source inspection, **Interface-checked, 2026-11-13**, at `b1b4a4de0`, builds on improvement
review publication `823c7fac0`, especially I02/I07/I08/I09. All target behavior and duration
benefits below are **Proposed**, not measured. Installed tools are pgTAP 1.3.4,
pg_prove 3.37 and postgresql-common 294. The
[capability reference](<../../libraries/postgresql/pgTAP, pg_prove, and pg_virtualenv.md>)
provides orientation; installed sources establish the selected version's details.

The existing PgAdmin supplies acknowledged creation, leases, policy replay and authenticated
cleanup. Keep it. The existing receipt owner supplies managed selection and native evidence.
Extend that owner, rather than introducing another qualification ledger or writing a TAP parser.
Python remains appropriate for application/driver/concurrency claims. SQL-visible expectations
can execute together inside PostgreSQL without repeatedly starting Python-to-database journeys.
FP-01/03/07 and H4/H12/H20/H21 favor native batching at the actual reusable boundary.

The November 6 writer-TEMP failure remains evidence of that exact route, not a rejection of
pgTAP generally. pgTAP `plan()` creates temporary state; relational assertions also use temp
objects. Maintenance-compatible SQL families can use these capabilities without granting
application writers TEMP. Actual-purpose auxiliary sessions must retain their real authenticated
identity and cannot see uncommitted harness startup rows. Test-only SQL installation belongs in
an isolated owned clone/seed after normal deployment verification, never the production head.

## Shared contracts

| Contract | Owner and behavior |
|---|---|
| Database acquisition | TS-01/02/05/08: tooling requests a verified clone or seed; PgAdmin retains leases and cleanup |
| SQL family selection | TS-24: a finite mapping of existing logical pytest node IDs to unique SQL case names, explicit expectations and a selected source recipe |
| Results | TS-24 extends the existing receipt owner: expected cases, observed case outcomes, TAP diagnostics, psql exit and acquired context stay distinct |
| Evidence mode | TS-13: ordinary versus explicit provider selection is retained through SQL selection and retry |
| Capacity | TS-04/12: one capacity owner; no independent auto-sized pg_prove pool inside each pytest worker |
| Host acquisition | TS-25: an explicit private endpoint/settings value consumed by the existing lifecycle; shared host remains default |

## TS-24 — SQL family execution and TAP evidence

**Needs:** TS-05's maintenance rollback/isolation contract, TS-08's seed operation for inherited
SQL setup, TS-13's selection/provenance contract, and TS-04's explicit worker selection.
An early result/selection contract can be developed before the full consumers migrate.

**Selected first consumer:** maintenance-compatible literal-argument cases in
`python/corpus-structure/tests/semantic/test_local_semantic_admission.py`. Its current
`native_match` calls the deployed `data.local_semantic_case_matches` with independently
specified envelopes. Classify the full module before moving it: retain Python-only construction
checks and any claim requiring another session. This is the actual migration scope, not a mandate
to translate all native tests into SQL. TS-20's protected real-purpose binding checks continue
through their existing seed/connection route and do not wait for this package.

Prepare one test-only SQL recipe per worker/head with pgTAP installed in its own schema, the
unchanged deployed function and independently authored case data/functions. Reuse the committed
recipe seed; run each selected family on its rollback-compatible clone. Installation and source
case setup are preparation; test mutations remain case-local. Use `runtests(schema, pattern)`
with startup once, setup/test/teardown rolled back per case and shutdown once. Use `results_eq`
only for ordered contracts, `bag_eq` where multiplicity matters and `set_eq` only for true set
meaning. Keep reach, reason and effect expectations at the authored case, including SQLSTATE,
constraint/message/context detail where `throws_ok` alone is insufficient.

Invoke pg_prove once per selected family batch, not once per assertion. Use its native
TAP parser, controlled psql startup and `ON_ERROR_STOP=1`; never enable `--ignore-exit`.
A small Perl adapter using `TAP::Parser`/`TAP::Harness` produces the bounded structured case
report and retains raw TAP/stderr/process status under the existing managed result. It must
use the same pgTAP source handler as pg_prove, not implement SQL launching or TAP parsing anew.
Use one job initially under outer pytest scheduling; file-level jobs are available only when
the same capacity owner allocates them and the files have independent state.

Preserve existing logical pytest identities. Collection identifies selected members and gives
the batch operation their exact case-name mapping; the first requesting item executes that
selected batch, and each item consumes only its own result from that invocation. A function
name/pattern is escaped and restricted to the explicit selected set, not arbitrary SQL. Repeated
selection of an equal family uses one batch within that run. Retrying one case executes that
case, rather than claiming a historical pass or rerunning the whole family unnecessarily.
No shared preparation result is a substitute for execution of the selected case.

The SQL source observes database/OID, server incarnation/version and current/session user in
its actual psql session. Associate each observed case execution with its logical item using the
exact case mapping and acquired session context. A Python connection cannot attest psql's
acquisition. Subtest results stay diagnostic detail rather than additional pytest test counts.
Missing/duplicate cases, unknown case names, plan mismatch, malformed TAP, bailout or nonzero
psql exit prevent successful qualification. Preserve any completed case observations, but mark
unexecuted or uncertain cases incomplete/not_run, never manufacture per-case passes.

**Migration and retirement:** remove only the replaced per-case SQL launch/setup/assertion
path; retain independently authored envelopes and Python/app/purpose controls. No universal SQL
registry or compatibility runner is required. Complete the item/provenance mapping before
replacing the current qualified Python path; a bounded prototype cannot close TS-24.

**Acceptance:** a selected single case, subset and full family retain their logical IDs and
independent expectations; two selected cases share stable preparation and one psql batch.
Wrong result, wrong reason, duplicate/missing assertion, truncated stream, unexpected SQL error,
wrong database/login and cancellation remain distinguishable. A mutated case cannot affect its
sibling. Retry and coverage read the same selected identities and actual native context.
Use focused managed tests for the migrated family and receipt adapter; keep integrated
qualification at TS-23. No elapsed-time target is required.

**Pivotal references:**
[pgTAP lifecycle and assertions](https://pgtap.org/documentation.html), corroborated by installed
`/usr/share/postgresql/18/extension/pgtap--1.3.4.sql` (`plan`, `_runner`, `runtests`);
[pg_prove/source-handler contract](https://metacpan.org/dist/TAP-Parser-SourceHandler-pgTAP/view/bin/pg_prove),
corroborated by installed `/usr/share/perl5/TAP/Parser/SourceHandler/pgTAP.pm`.
These features supply subtransactions, diagnostics and native process/TAP interpretation;
they do not supply application acquisition provenance or nontransactional isolation.

## TS-25 — Private PostgreSQL cohort

**Needs:** TS-01/05 infrastructure acquisition, TS-13 host/context reporting and TS-24's
result contract when SQL families are selected. Native driver-only execution need not wait
for the complete SQL-family migration.

Add `ci test --native-host private` on the existing ordinary route, with `shared` as default.
Use pg_virtualenv once around the lane's bootstrap and selected pytest/SQL work, not once per
case or per worker. Select PostgreSQL 18 explicitly and private non-root temporary directories.
The initial supported consumer is the I02 driver-only infrastructure selection; also support
TS-24 SQL families on this acquired host once normal template/role setup is available.
This makes private infrastructure an executable supported route, not a dormant capability lead.

Acquire the new server's actual endpoint, construct explicit Settings/purpose URLs and provision
its extension-ready template and only the roles required by the selected fixture contracts.
Pass those settings to PgAdmin and child psql/Python processes; do not assume PGHOST/PGPORT
can override an explicit application URL. Normalize conflicting libpq selectors, and record
observed cluster identity. Do not inherit credentials or database names pointing at 18/corpus.
All clones/seeds still use the existing naming/lease/acknowledged-cleanup owner.

Retain one cluster for the complete selected cohort, with per-worker/case isolation inside it.
The installed script's fast initialization (`--nosync`, `fsync=off`) is appropriate for this
throwaway functional route. Shared-host authentication/peer controls and durability/crash
claims are outside it; reject incompatible fault selections explicitly. Those tests retain their
real required host or a separately designed durable configuration. Private mode is neither OS
isolation nor a substitute for provider assets.

Persist host choice in invocation context and reapply it on retry/recollection. Reprovisioning
creates a new observed incarnation: coverage must report/reconcile this context rather than
pretend it is the original server. Capture logs before pg_virtualenv cleanup; settle owned
children before shutting down the cohort. Its trap cleanup is not a claim of crash-proof
cleanup after SIGKILL. Preserve uncertain ownership/residue explicitly instead of dropping a
similarly named cluster. No mutation of the persistent working database or other server is part
of this route.

**Acceptance:** one cluster bootstrap serves a multi-case/multi-worker driver selection; direct
SQL observes the selected endpoint and real login; conflicting parent libpq variables cannot
redirect acquisition; bootstrap failure, interrupted child and ordinary teardown preserve logs
and settle owned resources. The shared route retains its existing claims. No new supported
PostgreSQL version or durability assertion enters scope.

**References:** installed `/usr/bin/pg_virtualenv` from postgresql-common 294 is the versioned
implementation basis for environment normalization, fast settings and cleanup;
[public manual](https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html)
and the repository capability reference explain the public contract. Exact-version source
inspection takes precedence over older implementation details in that overview.

## Execution and remaining uncertainty

Implement result/selection and endpoint contracts first, then one complete supported cohort
with its actual consumers. A focused source/probe investigation inside TS-24 must settle whether
the selected family's SQL projection preserves every relevant expectation and whether selected
subtest mapping can be made faithful using the installed parser. This is a feasibility prerequisite
to migration, not permission to lose case identity. If that particular family requires unrelated
Python semantics, keep those cases Python and choose its SQL-only subset; expose any unsupported
mapping before claiming the package complete. TS-25's settings propagation and shutdown are
similarly verified before admitting parallel consumers.

The outcome remains selected tooling adoption with useful SQL and private-host consumers; a
failed experiment does not silently turn it into an evaluated-but-unused package. Reassess the
smallest owning integration if necessary. Benefits are structurally expected from amortized
setup and client execution, without a benchmark quota or a claim that private startup is always
cheaper than an already running server. No tests or probes were run while authoring this plan.

The new runner/host boundary receives a scoped design/target review under the existing binding
before TS-24/25 integration, with the applicable test diagnostic context current for that scope.
This authoring turn initiates neither that review nor an audit. The assembled scope still receives
TS-23's review; one coincident boundary needs one review, not duplicate ceremonies.
