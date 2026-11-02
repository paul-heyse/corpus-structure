# Native arrangement and assurance comparison

**Tested, bounded, 2026-11-02.** TA-01 comparison for the
[test architecture series](../../../plans/test-architecture-and-evidence_2026-11-02.md).
Base source `fb84eb8f`; concurrent native-support/targeting/context changes are identified in
`raw/source-context.json`. This is evidence for selection, not assembled TA-01–04 qualification.

## Result and selection

Retain PgAdmin as the shared-cluster deployment and sole inner database owner under ADR-0032.
Authenticated recovery of alternate-role/exact-authentication-row effects is the separate TA-02
implementation. A private cluster is feasible, but adds an outer owner and explicit credential,
preload, extension, socket and durability adaptation without being necessary to preserve the
selected shared contract. No architecture rule change or new default library adoption follows.

| Check and command | Outcome and scope |
|---|---|
| `uv run python docs/design_review/evidence/2026-11-02_ta-native-arrangement/native_controls.py shared` | **passed** serialized rerun: current frozen `semantic_bound_only_20261102`, sealed head, exact policy replay, committed clone isolation, actual write/read/evaluate/admit LOGIN identities and restricted posture; all three owned DBs removed |
| Same shared command, earlier overlapping attempt | **failed**, retained `shared-controls.log`: SQLSTATE53200 during frozen0052 migration, hint `max_locks_per_transaction`; serialized rerun above passed without configuration changes |
| `uv run python docs/design_review/evidence/2026-11-02_ta-native-arrangement/native_controls.py shared-policy` | **passed** bounded policy/prepared-content clone control; explicitly not current migration evidence |
| `uv run python docs/design_review/evidence/2026-11-02_ta-native-arrangement/private_owner.py` | **passed** private current deployment/clone/purpose controls, and supervised settlement after SIGKILL at a controlled pre-start boundary and after daemon startup; all owned private parents removed |
| `uv run python docs/design_review/evidence/2026-11-02_ta-native-arrangement/private_owner.py pgtap` | **passed** Python versus pgTAP posture, exact native-error assertion, deliberately incorrect SQLSTATE produces `not ok`; installed pg_prove returns success for the positive control and failure for the negative control |
| pytest-postgresql runtime/server pilot | **not_run**: tagged9.1.1 source establishes its default connection termination; current shared-owner selection has no remaining feasibility question that another server pilot would settle |
| pg_regress/isolationtester/plpgsql_check execution | **not_run**: current increment supplies no selected SQL snapshot, replacement interleaving or static-diagnostic obligation requiring them |

## Ownership and meaningful limits

The shared probe calls PgAdmin directly on fresh unique owned databases and never invokes its
general sweeper. It makes no shared role, authentication-file, service or configuration change.
The private probe uses non-root pg_virtualenv18 with an owned parent TMPDIR, a private socket,
required preload/extension versions, explicit purpose settings, fsync on and synchronous_commit off.
Private role/authentication changes occur only beneath that owned cluster.

The pre-start control gates pg_ctlcluster after cluster files and its marker exist. The running
control kills the outer shell, confirms a server remains via its private postmaster PID and exact
data argument, and stops/drops only that discovered private cluster. This establishes containment
and a feasible settlement path. The still-live pilot supervisor retains ownership knowledge:
**it does not establish production next-invocation recovery, live-owner exclusion, stale-PID safety,
every startup window, power-loss durability or instantaneous SIGKILL cleanup.** TA-02 owns those
selected interruption and identity obligations.

Initial private attempts failed on probe mistakes: the migration table was incorrectly named
`alembic_version`, and pgTAP1.3.4 `results_eq` rejected a bare VALUES query as an EXECUTE cursor.
The corrected query uses `semantic_alembic_version` and `SELECT` expected tuples. Both failed raw
logs remain; their clusters were settled. No raw output is promoted to final-source product
qualification, and no timing/speedup claim is made.

## Library conclusions

- pytest-postgresql9.1.1 `DatabaseJanitor.init/drop` terminates template/target connections.
  [Tagged source](https://github.com/dbfixtures/pytest-postgresql/blob/v9.1.1/pytest_postgresql/janitor.py#L108-L144).
  Preserve PgAdmin's existing disposal authority and restricted termination contract; do not
  recreate most of either implementation through an adapter or install a second janitor.
- Installed pg_virtualenv293 creates nested work/config/data paths and daemonizes the server;
  shell traps and the test process group are insufficient ownership after outer death.
  [Tool documentation](https://manpages.debian.org/unstable/postgresql-common/pg_virtualenv.1.en.html).
- pgTAP1.3.4 provides useful exact-error and relational assertions. The passing posture comparison
  does not independently establish native guard reach, and a plain successful psql exit does not
  interpret failed TAP. The separate pg_prove control demonstrates that distinction.
  [Assertions](https://pgtap.org/documentation.html).
- isolationtester remains a candidate for a named interleaving that improves on current real-client
  race controls; pg_regress needs an independently specified stable SQL output. plpgsql_check's
  runtime-SQL/temporary-table limits prevent treating it as behavioral guard proof. These are
  dispositions for this increment, not claims that the capabilities lack future value.

Probe sources are retained here; `raw/` contains actual logs/results. No cluster directory,
environment, cache or database is retained as an evidence artifact.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**test-architecture-and-evidence**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Bounded native arrangement and SQL assurance comparison](records/ta.native-arrangement.json) | TA-01 | passed | TA-01, TA-02, DTA-002, ADR-0032 | 2026-11-02 |
<!-- evidence-index:end -->
