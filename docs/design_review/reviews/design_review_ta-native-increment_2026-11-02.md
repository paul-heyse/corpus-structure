# Native test infrastructure increment

## 1. Scope, outcome and coverage

**Design / target; combined focus; 2026-11-02.** Review TA-01–04 against core3.3,
heuristics1.0, test-assessment1.2, applicable CI1.4 evidence/fidelity obligations and the repository
binding. The operator selected combined library/principle focus. Consume the test-audit publication
`2d450cdd`, source `2495baae` reconciled through `25a23118`, with current plan/source changes inspected.
This is test-support scope, not a refreshed broad production audit.

Base `fb84eb8f` plus the dirty native-auth, native-support, package fixture/entrypoint and receipt
changes. Source inspected includes adjacent runtime credential resolution, database ownership,
process supervision, classifier consumers and authored tests. Unrelated UM documentation is excluded.
The reviewed recovery source snapshot is `scripts/native_auth.py` SHA256
`f45cea35acfe8bd974d6e35fd5843e84b90bad88d71a59ecd6a2dd50693e84e6`;
later revisions require reconciliation of affected conclusions.

**Decision at this snapshot: Accept scoped.**
PgAdmin remains the right sole database owner for this increment. The direct-owner/helper recovery
design includes backend settlement and privileged execution admission for whole-group death.
Targeted native/failure controls passed; source and bounded results support this local judgment.
Integrated final-source qualification is the coordinator's subsequent responsibility.

Adjacent reviewed snapshots: `scripts/native_test_support.py`
`2c2dac52ad0339236641e31519d7c077bd48ec5d642bdcb6c022ac904425dc90`;
`scripts/test_receipts.py` `498940ae5a361574f2bef91edb9e1855302782614e788edb7ed139cc89678d1e`.

## 2. Responsibilities and semantic ownership

PgAdmin owns database reservations, OID/owner acknowledgements, leases, deployment/policy replay
and disposal. Its `alternate_reader` delegates one cluster-authentication responsibility to
`scripts/native_auth.py`; it does not establish a second database janitor. The authentication owner
distinguishes requested acquisition, atomically stamped role creation, acknowledged role OID,
intended exact auth rows, active ownership and recoverable residue.

Package fixtures capture original Settings before installing a refused application target.
`settings_for_native_clone` preserves purpose authentication while changing the owned database.
Production `connection_settings` remains the credential/endpoint authority. Qualification hooks
record observed acquisition; the classifier owns provenance completeness separately from node results.
The plan coordinator owns scheduled DTA disposition, including DTA-002/003/017.

FP-01/03/04/06 are satisfied in these scoped responsibilities: ordinary modules suffice and
consumers reuse their owners. No graph-analysis semantics or graph authority is introduced;
code-intelligence graph-specific obligations are not applicable.

## 3. Contracts and constraints

Preserve actual purpose LOGIN sessions, committed clone isolation, sealed source deployment,
normalized ACL/default replay and authenticated cleanup without forced drops or broadened backend
termination rights. Roles require the recorded cluster identifier, nonce stamp and, after
acknowledgement, matching OID. Auth cleanup removes only recorded exact rows; malformed/foreign
identity is preserved with a refusal. Initial journal publication and subsequent updates are atomic.
Private root permissions and symlink refusal prevent accidental adoption through a displaced path.

An exclusive advisory lease serializes cooperating live authentication owners. An inherited kernel
effect lock prevents next-invocation recovery from overtaking a surviving helper supervisor after
direct Python-owner death. A privileged shared execution lock and journal-phase admission fence
must cover helpers which outlive their unprivileged process group; a fresh recovery generation
distinguishes late helpers from an earlier recovery attempt. Per-operation PGAPPNAME and a bounded backend-exit wait distinguish
client-process completion from database completion after that entire helper process group dies.
Journal-derived exact temporary filenames make interrupted privileged file edits recoverable
without sweeping arbitrary files in the shared configuration directory.

## 4. Composition and execution

Retain the current session-deployed head and fresh PgAdmin clones. A rare alternate-principal test
serializes its cluster edits; there is no reason to serialize unrelated ordinary clone consumers.
Atomic selective file replacement preserves other stable entries, rather than restoring a stale
whole-file snapshot. Recovery attempts independent removals and retains primary/cleanup failures.

TA-03 fencing is test-scoped and leaves production defaults intact. Original settings are captured
before the fence, then in-process/subprocess application routes receive explicit clone settings.
TA-04 reuses existing events, distinguishes requested and acquired fields, associates test versus
session lifetimes, and preserves historical receipts with unavailable provenance. An item-bound
maintenance observation is acquisition evidence, not proof of every application's semantic journey;
required-union applicability remains external judgment.

FP-07/A4 favors this composition over an additional server owner. The retained concurrent
shared-memory failure demonstrates that overlapping complete deployments can exhaust shared lock
capacity; the serialized current-deployment control passed without host changes. This establishes
neither a capacity guarantee nor a timing/speedup claim.

## 5. Change and failure scenarios

- A different constructor/environment endpoint still resolves original purpose credentials before
  clone substitution. The sentinel must not contaminate native maintenance acquisition.
- A second live auth owner waits; it cannot recover the first owner's journal. The original shared
  advisory-lock manifestation was corrected to an explicit exclusive lease during review.
- A pre-publication interruption leaves no malformed committed journal; the initial direct-write
  manifestation was corrected to atomic publication during review.
- Direct owner death after acquisition is recoverable by the next context. Death while a surviving
  helper runs is covered by the inherited effect lock's intended lifetime and needs its native control.
- Whole-group death while a PostgreSQL backend is still processing submitted SQL has a concrete
  correction with its native falsifying control below. A new principal/policy is the relevant domain extension;
  pg_virtualenv/plugin replacement is the mechanism-substitution scenario, not a product-model rewrite.

## 6. Correctness and fidelity gates

| Gate | Verdict | Basis |
|---|---|---|
| G1 Authority | pass | Existing lifecycle owns each effect; DTA disposition remains in the coordinator |
| G2 Semantic fidelity | pass, scoped | Credentials, session identities and policy replay retain their distinct meanings |
| G3 Validity | pass, scoped | Owned-root/cluster/stamp/OID/row checks reject incompatible recovery identities |
| G4 Hidden behavior | pass, scoped | Test target fencing and explicit acquisition settings remove ambient application access |
| G5 Consistency and recovery | pass, scoped | Exclusive live-owner lease, inherited effect lock, privileged barrier/fresh phase, backend wait and exact artifact recovery; targeted controls passed |
| G6 Transformation and reuse | pass, scoped | Deployed head, fresh clones and policy equivalence preserved by bounded native controls |
| G7 Truthful capability claims | pass | Source inspection, bounded pilots and later implementation qualification remain separate |
| G8 Library leverage | pass | Complete existing/library arrangements compared; no library chosen by name alone |
| CI-G1/2/3 | n.a. as graph gates | No code-analysis graph/serving pipeline; evidence attribution and independent expectations applied by analogy |

## 7. Material finding and disposition

**DTA-002 — effect ownership must outlive submitted SQL; scoped correction evidenced.**
FP-05, DP-19/20; G5. `native_auth.run_effect` holds an inherited file lock in a waiting Python
supervisor while sudo/psql runs. This resolves the previously identified direct-owner-death race
if the waiting supervisor survives. `scripts/test_receipts._stop_group`, however, signals the whole
group and can kill the supervisor and SQL client together. The PostgreSQL backend is outside that
group. With connection checks disabled by default, the server need not detect client loss until
its next socket interaction. Therefore client/group death cannot by itself establish that submitted
role creation/COMMIT has settled. [PostgreSQL connection-check contract](https://www.postgresql.org/docs/current/runtime-config-connection.html).

The previously possible consequence was recovery seeing no committed role, removing its journal,
and an older backend committing later. The corrected `pg` supplies the journal nonce through
PGAPPNAME at connection startup; `recover` waits boundedly for that tagged operation's backends
before checking role absence/stamp/OID. A timeout retains the journal and refuses recovery.
The original SIGKILL control kills after context yield; the new delayed-backend group-death
control covers this distinct boundary. No orphaned shared role was manufactured by this review.

Privileged file helpers also need actual execution ownership: sudo processes may survive an
unprivileged group signal. The latest correction uses a shared privileged execution lock held
through phase admission and the helper effect. Recovery takes an exclusive barrier and changes
the journal phase before cleanup. A helper already executing settles before that barrier; one
arriving late must refuse the changed phase. Each recovery attempt needs a fresh phase generation,
otherwise a late helper from a dead earlier recovery still matches the constant recovery phase.
Exact temporary-file identities keep interrupted replacement artifacts within that same owner.

The implemented backend identity and normal-exit wait require no daemon, new termination rights,
global registry or host-durability machinery. Closure evidence must delay owned SQL before its
effect/commit, kill the complete helper group, immediately attempt next-context recovery, and
establish that neither a late role nor a removed journal can escape. The actual delayed-backend,
privileged-helper, prior-recovery-phase and owned-temp controls passed within the23-test selection.
Source/controls belong to TA-02 at the
[coordinator](../../plans/test-architecture-and-evidence_2026-11-02.md#findings-disposition).

**DTA-003 — complete acquisition identity, not a self-declared completeness flag.** The reviewed
classifier requires actual host/port/server start/version, database name/OID and both current
and session principal. Bare databases may explicitly lack deployment metadata. Required-union
reuse also requires a complete matching item event in that same receipt when the current manifest
declares native applicability; a historical raw passed node alone is insufficient. Producer fields
exclude passwords, full URLs and query authentication options; the native reader control checks its
actual clone, principal, deployment and requested-field allowlist. No remaining material issue was
identified in that producer/classifier boundary. Acquisition classification remains distinct from
full semantic application-journey assertions.

## 8. Library fit

The finalized [TA-01 evidence](../evidence/2026-11-02_ta-native-arrangement/README.md), record
`ta.native-arrangement`, establishes shared and private current deployment, actual purpose sessions,
committed clone isolation, exact policy replay and bounded private death settlement. It retains
failed probe attempts and the overlapping shared-capacity failure.

pytest-postgresql9.1.1's default janitor terminates template/target connections, conflicting with
shared disposal. [Tagged janitor](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/janitor.py#L108-L144).
pg_virtualenv293 provides useful private cluster construction but requires explicit application
settings, roles, extensions, preloads and a second outer lifecycle; its daemon survives shell death.
The owned parent TMPDIR pilot proves a feasible containment path, not production next-invocation recovery.

pgTAP1.3.4 and installed pg_prove distinguish correct posture/error expectations from a deliberately
wrong SQLSTATE. Narrow future adoption is credible; retaining existing Python assertions now avoids
a redundant runner layer. isolationtester needs a named interleaving consumer; pg_regress needs an
independent stable SQL-output contract. plpgsql_check cannot replace dynamic-SQL/temporary-table
behavioral controls. These capabilities are investigated, not rejected categorically or installed
as new application dependencies.

## 9. Alternatives and tradeoffs

The selected shared extension reuses deployment, privileges and database custody while adding
only the auth-effect recovery actually required. Private pg_virtualenv can confine cluster edits,
but duplicates outer server/configuration/recovery obligations. A plugin-owned disposable server
has the same broader question; its default shared janitor does not fit the current contract.
Keeping only finally cleanup is simpler but fails the supported interruption case. Making all
tests use private servers or persistent scenario caches is unnecessary for the present consumers.

## 10. Verification and uncertainty

**Tested, bounded, 2026-11-02:** commands, outcomes and failed attempts are in the finalized evidence
record. Shared serialized current deployment, private deployment, clone/purpose/policy controls,
controlled pre-start/running outer death and pg_prove positive/negative controls passed. The pilot
does not test the newly implemented shared authentication recovery, stale-PID/live-owner recovery,
all startup windows or whole-group in-flight backend death; implementation controls are separate below.

**Passed, targeted, 2026-11-02:** `CORPUS_TEST_NATIVE_AUTH_CRASH=1 uv run pytest tests/scripts/test_native_auth.py -q`;
23controls, with no skips/failures in `build/ta-auth-final.log`. This includes actual shared alternate-role
recovery, delayed backend/group death, privileged helper settlement, exact temp recovery and stale
recovery-generation refusal, alongside independent malformed/foreign-identity and injected-failure
cases. The command/outcome were supplied by the coordinator and reconciled against actual output
and inspected source; the reviewer did not duplicate that run.

The coordinator/test agent owns targeting/context results and final-source required-union
qualification. This review does not claim that still-running final union passed. `just evidence finalize
2026-11-02_ta-native-arrangement ta.native-arrangement` and `just evidence` passed; the latter reports
127records,0errors and39 retained historical warnings. No integrated product/provider result follows.

## 11. Authority and rule impacts

No rule change is required to retain ADR-0032 and extend its existing owner with authenticated
recovery. Accepted ADRs remain unchanged. Selecting private outer deployment or a terminating
shared janitor would require reassessing the governed lifecycle; neither is selected here.
The review supplies evidence and corrections, not implementation or execution status authority.

## 12. Architectural judgment

| Judgment | Verdict | Scope and action |
|---|---|---|
| A1 Localize change | satisfied | Native effects, application targeting and evidence classification have coherent existing owners |
| A2 Encode domain meaning | satisfied, scoped | Reservation/acknowledgement, principal purpose and acquired-versus-requested context remain explicit |
| A3 Compose capabilities | satisfied | Existing PgAdmin, runtime settings, pytest events and classifier compose without a second janitor |
| A4 Fit execution | satisfied, scoped | Session deployment reuse/fresh clones retained; rare auth serialization justified; no quantitative capacity claim |

**Accept scoped.** No material finding remains within TA-01–04's examined native ownership,
targeting and receipt boundaries. Final formatted-source required-union qualification remains with
the coordinator; scope completion and DTA disposition are not changed by this review itself.
This local judgment does not certify the full test architecture series.
