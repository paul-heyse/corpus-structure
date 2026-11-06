# Native lifecycle and provenance

**Status:** Proposed. [Coordinator](../test-audit-resolution_2026-11-05.md) owns TR-06–08
and DTA disposition. Reuse native_test_support, qualification_plugin and test_receipts; no
second janitor, observation subsystem or qualification register is selected.

## TR-06 — A selectable item owns its entire lifecycle evidence

Choose direct tests of shared context-managed owners. The diagnosed defect is a premise split
between test items, not pytest finalizer scheduling; a child-pytest harness would add another
bootstrap/receipt/process lifetime without a relevant assurance gain.

Extract the existing outer rollback lifetime into a small context manager in native test support.
The db fixture delegates to it with with/yield. One test enters it, creates/inserts, independently
observes presence, exits, and checks absence through a fresh connection in that same item.
Include exceptional exit so rollback cannot be inferred merely from never writing anything.
Do not call private fixture.__wrapped__ functions to imitate pytest.

Committed clone lifetime stays with PgAdmin.database. Keep committed contents visible to a second
connection and absent from the session clone; observe database absence after leaving the owned
context in the same item. Reuse/extend semantic/test_native_fixtures.py:41–69, which already owns
these observations. Remove _committed and the separately collected order-dependent drop case.
The committing_db fixture remains a thin delegate to the tested owner. Source review plus
integrated consumers establishes wrapper wiring; reopen a bounded child-pytest option only for
an actual scheduling property not covered by that delegation.

**Acceptance:** each repaired node selected alone establishes its write/acquisition happened,
observes rollback/disposal and passes without another node's execution. Exception cleanup,
committed cross-session visibility, real principal and clone-isolation guarantees remain.
Do not replace committed tests with rollback-only fixtures or broaden shared termination rights.

## TR-07 — Observe only while a consumer is active

Add one narrow public-in-test-support plugin query for active receipt-consumer availability;
the plugin owns its answer from actual sink lifetime. Evaluate it where observation would run,
not once when an engine is created. Import success and an environment variable do not establish
that a stream is currently open. Retain SQLAlchemy's physical connect hook and actual native
facts; closure of the sink disables later optional observation on existing engines.

Guard all observation-only work before acquiring its cursor/connection or computing context:

- observe_connection identity/revision queries, policy hashing, deployment-cache mutation and
  observation-only driver rollback;
- PgAdmin.database's eager maintenance checkout used solely to observe deployment before lending;
- record_server_context's connection opened before recorder availability is checked.

Required credential resolution, deployment checks, policy replay/comparison, clone creation,
lease/ownership and cleanup still execute. No extra pool, weaker authentication or missing native
validation is an acceptable optimization. In an active qualification session establish the sink
before session templates/clones are prepared, so maintenance context can legitimately supply
revision/policy observations for restricted acquisitions. Preserve server/database-incarnation
keys, node binding, requested-versus-acquired values and optional seed attribution.

Migrate semantic/test_native_fixtures.py:469–496: it currently replaces only record_native_context
after metadata preparation. Its new explicit capture-consumer fixture must activate before
clone/preparation dependencies and restore after dependent resource teardown; do not merely
force the query to true after the deployment observation was skipped. If recording is activated
late, absent historical metadata remains unavailable, never fabricated from current Settings.

**Acceptance:** inactive native functionality remains real while observer cursor/hash/rollback
and observer-only eager checkout are forbidden; active capture observes actual deployment then
restricted login; closed consumer disables observation; two acquisitions preserve distinct
identity and node associations. Test consumer restoration even after setup/test failure. Use
bounded call observations for work elimination rather than timing instrumentation.

## TR-08 — State precisely what receipts establish

### DTA-003 decision

**Proposed correction to claim precision; source reasoning Interface-checked,2026-11-05.**
Existing _complete_native_context explicitly judges an item-bound acquired identity: database/OID,
principal/login, host/port and server incarnation/version. Current minimal-context controls
intentionally omit revision/policy. No current classifier consumer requires full deployment/policy
reproducibility; classify() surfaces those observations for the operator rather than validating
such a stronger property.

Retain native-context/v1 and existing raw fields. Document native_provenance.status=complete as
**complete item-bound acquisition identity**, not whole deployment reproducibility. Keep optional
revision/policy_ref/scenario_seed and explain deployment_status=observed as revision observation,
not proof that policy is complete. Clarify docstrings/operator output at existing owners as
needed; add no per-test metadata registry, new universal status enum or mandatory seed field.
New plan wording supplies this narrower contract without editing older TA plan prose.

Keep separate actual fixture controls for claims needing semantic deployment: current template
revision, ACL/default replay and actual purpose behavior. Bare bootstrap and historical migration
contexts can legitimately have no current revision/policy. Acceptance pairs identity-complete
minimal context with missing-identity rejection, actual deployment/policy observations where
available, and explicit unavailable optional metadata. Reconcile TR-07's active capture with those
controls. DTA-003 closes when the narrower public claim and its consumers agree, not by inventing
stronger coverage or weakening required native identity.

Old receipts/raw node outcomes remain immutable. Applicability-less context remains unavailable;
legacy passes cannot satisfy a current required native union. Historical evidence is not retagged.
A future request for reproducible deployment+policy must define the stronger scope/authorities
before extending the check; this is a future capability trigger, not remaining current repair work.

### Rust local classifier correction

classify_rust currently participates in assembled classification. Unlike Python classification,
it omits cleanup_error, descendants_after_leader_exit and group_present_after_cleanup. A child
that survives leader exit but is eventually killed can produce a locally passing Rust result
where Python reports incomplete, without sticky supervisor interruption. Current empty Rust
selection supplies no functional coverage, but that does not justify inconsistent artifact claims.

Apply the same owned-group settlement predicates before accepting Rust success, retaining failed
results and reporting otherwise-successful results with those defects as incomplete and without
functional_coverage. Preserve explicit early-cancel rust-state outcomes and zero-case not_run;
cleanup faults may make overall evidence incomplete but never turn zero tests into coverage.
Reuse existing process facts/helpers rather than redesign both classifiers.

Independent canned artifact controls cover each cleanup fact, interruption, failed native process,
clean nonempty listing+JUnit, count mismatch, skipped cases, zero selection and absent result.
Exercise assembled aggregation to show a locally incomplete result cannot disappear. These are
classifier tests, not fictional Rust product tests or a new Rust test body. No current erroneous
production/Rust qualification is alleged.

## Tooling and environment disposition

Retain PgAdmin on dedicated18/corpus:5434, actual purpose logins and ADR-0032/0048 recovery/replay.
Persistent corpus_structure_dev remains normal development under ADR-0056. Isolated tests use
owned databases for actual isolation needs; unrelated main/tktest remain untouched.

Installed pgTAP/pg_prove can provide SQL assertions; isolationtester provides sessions/steps/
permutations; pg_virtualenv isolates cluster configuration. None removes the present independent
oracle, lifecycle-premise or inactive-consumer defect. Existing pytest/Psycopg/SQLAlchemy APIs
cover the selected target without extension activation or another runner. No package/service
change is scheduled. Reconsider a tool only for a concrete simplification with its endpoint,
activation, results integration and lifecycle obligations stated; existing sudo installation
authority does not approve a new architecture. Run just ready after any actual environment change.

[Tooling orientation](../../libraries/postgresql/PostgreSQL_System_Tooling_for_Ubuntu.md),
[SQL-only isolation contract](https://raw.githubusercontent.com/postgres/postgres/REL_18_STABLE/src/test/isolation/README),
[pgTAP](https://pgtap.org/documentation.html). TR-09/10 owns fresh integrated qualification;
this document supplies no new native pass or performance measurement.
