# Test-resolution tooling comparison and qualification

**Operator disposition: Retain Python, 2026-11-06.** The operator explicitly chose
"Retain Python and record the demonstrated pgTAP incompatibility as the comparison
disposition (Recommended)." This amends the TR-15A comparison completion boundary:
the demonstrated incompatibility and independent Python/native controls are
accepted as sufficient for this selection. The
[native lifecycle companion](../../../plans/test-audit-resolution/native-lifecycle-and-provenance.md#tr-15a--required-bounded-sql-contract-comparison)
and [coordinator](../../../plans/test-audit-resolution_2026-11-05.md) own the amendment
and current package disposition.

The [finalized probe result](records/tr15.native-assertion-comparison.json) remains
**partial** and unchanged. Its original pending/open conclusion describes the
pre-decision boundary; this dated operator disposition replaces that current-status
statement without changing the observed result. Actual-purpose pgTAP assertions
were blocked: pgTAP1.3.4 `plan(integer)` needs database `TEMP`, which the writer
purpose does not have. Equivalent TAP assertions did not pass, and no pg_prove
qualification follows.

## Subject, authority and isolation

The baseline is `a1e500c8dc2a4860fc878356a4149df798775707`; each attempt's
`source_context` event records relevant source hashes and concurrent changes. The
probe uses the WCE worker's extracted `semantic/witnessed_scenario_support.py`
fixture mechanics, following the current publication test's delivered exact
component contract. Expected statements remain independently authored literal
`definition_components`/`[0,2)`/`12` values, with the immutable fixture's source pins.
No production statement projector supplies the expected statement. Constructed
producer/reference inputs establish mechanism controls, not corpus semantic efficacy.

`compare_native.py` uses PgAdmin's acknowledged database ownership, advisory leases,
normal deployment check, sealed migrated template, exact database-policy replay,
purpose credential resolution and cleanup. Native156
(`semantic_wce_target_20261106`) is freshly migrated. No temporary156–162 artifacts
are restored. Each clone's four required application extensions are checked before
maintenance installs test-only pgTAP1.3.4 into that clone. The normal template,
persistent development database, server configuration and grants are unchanged.
The general sweeper is not called.

Actual writer/evaluator connections observe their own `current_user`,
`session_user`, database/OID, endpoint, server version/incarnation and port. The
maintenance revision observation is associated by that acquired database OID;
restricted identities do not receive migration-table privileges. These are
standalone comparison receipts, not emitted pytest qualification contexts, and do
not attest a psql session. No psql provenance bridge or permanent TAP parser is added.

## Attempts and receipts

Each command is `uv run python
docs/design_review/evidence/2026-11-06_test-resolution-tooling/compare_native.py
--attempt NNN`. Raw receipts retain the probe bytes, exact SQL, TAP when emitted,
errors, acquisition identities and cleanup observations. A successful probe process
does not turn its explicitly `blocked` or `not_run` events into passed assertions.

| Attempt | Outcome | Actual boundary |
|---|---|---|
| [001](raw/attempt-001/events.jsonl) | failed | Probe omitted its source-fixture directory; migrated owned resources settled. |
| [002](raw/attempt-002/events.jsonl) | failed | Writer identity query incorrectly selected protected migration-version table; no grants changed. |
| [003](raw/attempt-003/events.jsonl) | blocked | Actual writer invalid-basis refusal is SQLSTATE23514; pgTAP `plan(2)` then raises SQLSTATE42501 on temporary-table creation, before TAP is emitted. |
| [004](raw/attempt-004/events.jsonl) | partial | Corrected evidence driver records pgTAP's prerequisite and continues independent Python controls. |

Attempt004's independent Python/native controls **passed** for the exact single
component policy/statement row, detection of duplicate and missing rows, valid
located-component custody, invalid-basis SQLSTATE23514, and stronger-applicability
SQLSTATE23514. The actual application finalization also refuses stronger
applicability at `data.structural_publication_candidates`. Its writer/evaluator
identities are respectively `corpus_sem_writer` and `corpus_sem_evaluator`, with
matching session identities, PostgreSQL18.6, `/var/run/postgresql`:5434 and the
observed native156 clone OIDs. Both clones and the sealed template report absent
after settlement. A separate read-only [cleanup audit](raw/cleanup-audit.json)
checks every attempt's named owned database is absent and that `cs_template`
still has no pgTAP. No product, harness or existing-test files were changed by
this evidence assignment; no full suite, turn-end or integrated qualification ran.

`raw/attempt-004/custody-refusal.sql` retains the intended fixed plan and independent
expected23514 plus deliberately wrong42501 SQLSTATE assertions. Its
`custody-refusal.error.txt` retains the actual42501 from `plan()`, and its `.tap` is
empty because the plan never emits. This is an initialization refusal, not a
passing `throws_ok` test. Subsequent pgTAP cases are `not_run` after the established
prerequisite; their authored SQL is preserved without a repeated blocked call.

## Comparison judgment and limits

The installed pgTAP source gives `bag_eq` duplicate-sensitive relational equality
and `throws_ok` exact SQLSTATE/message diagnostics. Those capabilities match the
selected unordered publication rows and native refusal obligations. The competing
Python route uses a direct native query plus standard-library `Counter`, and a
savepoint plus the driver's SQLSTATE/message. Both can express the independently
authored expected statement without a new domain validator.

The SQL declaration is compact for exact bags and refusals, but it does not remove
the current application setup, separate authenticated purpose sessions,
committed-session checks or PgAdmin ownership. An adopted pg_prove lane additionally
needs its own actual psql identity bridge, bounded subprocess settlement, fixed
plan/TAP/process-error interpretation and pytest receipt association. This probe
does not implement or qualify that branch. Under the current role posture,
pgTAP cannot even initialize its assertion state as the actual writer; changing
grants or asserting as maintenance would change the comparison's premises.
No performance benefit is claimed. Executed relational diagnostics remain unknown.
The operator selected the existing Python route on the demonstrated role
incompatibility and the added lifecycle/reporting burden described above. No
maintenance-role substitute, new grants, pg_prove lane or psql identity bridge is
needed to complete this amended comparison disposition. This selects the test
route; it does not establish full-plan or corpus semantic qualification.

TR-15B remains dormant: repeated startup while repairing this probe does not
establish that head bootstrap materially obstructs a required concurrent workload.
TR-15C remains dormant: this comparison has no cold-cluster, restart, extension-path
or server-configuration subject. Neither branch was gratuitously probed.

## Follow-up: permitting writer TEMP

**Proposed follow-up; static assessment, 2026-11-06.** The operator asked whether
the real writer's TEMP restriction could be removed if no blocker existed. A
concrete privileged-read ordering gap prevents that conclusion; Retain Python
remains selected. This inquiry made no grant, migration, source change or probe run.

The writer-callable `SECURITY DEFINER` function
[`data.publish_derived_batch_v2`](../../../../python/corpus-structure/src/corpus_structure/semantic/sql/derived_publication.sql#L19)
checks release admission at line43, then its accepted-inference branch reads
`pg_temp.sp_*` relations at lines83–87. The generated empty-stage expressions are
also direct temporary-relation reads
([native_products.py lines238–255](../../../../python/corpus-structure/src/corpus_structure/semantic/native_products.py#L238)).
Only afterward, at line95, does it call `data.publish_contract_batch`, whose
publisher ownership/relation-shape verification precedes reads
([transport.sql lines10–13](../../../../python/corpus-structure/src/corpus_structure/semantic/sql/transport.sql#L10);
[routines.py lines17–38](../../../../python/corpus-structure/src/corpus_structure/semantic/routines.py#L17)).
This is a real pre-verification surface for caller-created temporary relations or
views if generic TEMP is enabled and the admission restriction is relaxed. It is
a source-identified trust gap, **not an executed privilege-escalation exploit**.

Today, admission rejects any canonical runtime role with TEMP
([admission.sql lines150–152](../../../../python/corpus-structure/src/corpus_structure/semantic/sql/admission.sql#L150)),
and actual-purpose startup independently rejects the caller's TEMP
([closure.sql lines133–146](../../../../python/corpus-structure/src/corpus_structure/semantic/sql/closure.sql#L133);
[runtime.py lines84–93](../../../../python/corpus-structure/src/corpus_structure/semantic/runtime.py#L84)).
A grant alone would therefore break supported runtime opening/admission. These
checks are changeable policy owners, but removing them alone would expose the
ordering gap. Other inspected paths already have independent protections:
`publish_batch` verifies transport before stage reads, private PDF scratch checks
publisher ownership and rejects triggers/rewrites, and inference workspaces reject
preexisting relations and verify owner/shape before disposal.

The minimum safe change would first put the existing shared custody verification
before every affected privileged temporary-relation read, including the derived
inference branch, and check the adjacent writer-callable paths for the same
ordering. Then a writer-only TEMP policy could be expressed coherently in the
runtime/release attestations, forward native deployment and its exact admitted
function identities, database ACL policy/replay, and the ADR-0031/0032/design owners.
Reader, evaluator, fitter and admission restrictions need not change. Focused
hostile temporary-table/view/trigger controls and real writer publication/runtime
checks would be required before granting it in ordinary databases. That repair and
verification are not part of this read-only assessment; no broader security audit
or claim that all TEMP risks are discharged follows.

## Documentation method

Context7 resolved `/theory/pgtap` first and supplied `bag_eq`/`throws_ok` semantics.
Its development documentation is bounded by installed1.3.4 source, particularly
`/usr/share/postgresql/18/extension/pgtap--1.3.4.sql` lines25–62 (`plan` TEMP objects),
657–695 (`throws_ok`) and7016–7020 (`bag_eq`). Installed control declares1.3.4 and
`superuser=false`; availability and extension-install permissions do not grant the
writer `TEMP`. The supplied [PostgreSQL testing reference](<../../../libraries/postgresql/pgTAP, pg_prove, and pg_virtualenv.md>),
including its advanced addendum, and the
[tooling review](../../../plan_improvement_reviews/test-audit-resolution-tooling_2026-11-06.md)
inform the lifecycle comparison. `pg_prove --version` reports3.37; no pg_prove or
pg_virtualenv functional run is claimed here.

## Final integrated test qualification — 2026-11-06

**Tested; required union covered.** [TR-10 final record](records/tr10.final-required-union.json)
consumes [owner applicability summary](raw/qualification/summary.json),
[all23 DTA/TR10-F01/F02 current witnesses](raw/qualification/preservation.json),
[raw final classification](raw/qualification/final-union.json) and
[read-only native audit](raw/qualification/final-native-context-audit-notes.md).
The [coordinator](../../../plans/test-audit-resolution_2026-11-05.md#final-required-union)
owns current package/finding disposition. This evidence does not create another acceptance service.

| Attempt | Actual outcome and boundary |
|---|---|
| Full ordinary552fefb7 | just test-all -n auto;4828 passed/45 failed,4873 selected;16 created/ready/executing processes, observed peak16,920.07s |
| Repairfa1956a4 | Explicit64 affected/failed/new nodes;61 passed/2 failed/1 setup error; retained native lease race and short watchdog |
| Final repair69b9524c | Explicit4 nodes;4 passed,45.67s; includes changed serial/parallel conformance premises and setup-error victim |
| Exclusive fault69b9524c | just test-native-faults;8 passed,27.99s, serial;7 native-required and1 filesystem-only stale guardian |

Final current required scope is4874 ordinary plus8 fault nodes,854 native-required. No required
node is unresolved. The aggregate classifier status/CLI remain failed/1 because unsuccessful
attempt history is retained. source_contexts_differ remains true. The owner excludes18 original
admission negative successes with invalid premises and the earlier parallel conformance success
whose lease/deadline premise changed; the repair receipts supply those obligations. A natural
version2→3 negative case replaces its old canonical ID, and one real importlib regression is added.
Other successful results retain applicability after bounded independent review. No recipe counts
are added as though they were disjoint coverage, and old WCE322/unfinished1390 counts do not define
this union.

Safe unresolved export preserved collection configuration after its first real full-manifest
validation correctly refused a package-relative import error. Actual body-free validation produced
47 then3 unresolved nodes. Explicit -n0/lane overrides remain, with no empty/stale selection fallback.
Nested pytest now drops inherited worker/session identity variables while preserving parent and
configuration. Native conformance uses the existing exact-name semantic-bare lease family; only
native child controls receive180/60-second bounds after the retained20.521-second checkpoint and
20.556-second DROP. Failure/loss controls retain40/15; no automatic assertion retries, force drops
or server tuning were introduced.

Full hygiene passed on552fefb7. Applicable changed Python typing/Ruff and maintenance passed at
repair endpoints; unchanged dependency/Rust/rule/process checks remain applicable. Rust release
nextest selected0 tests: not_run/empty-selection, with actual rustc version retained. Native
context/cleanup auditing found no receipt-observed transient names remaining, including failed
outer222653/child225748 resources. Two outside-receipt resources were preserved. Actual server
and default extension/native156 context remain in the audit; no universal capacity claim follows.

The initial stderr retains one unattributed SQLAlchemy weakref KeyboardInterrupt warning. No
node/PID/timestamp establishes attribution; reporting and process cleanup completed. Earlier
focused147/1 and20-pass temporary child artifacts aged out under pytest retention; only their
conversation/tool summaries survive. This limitation is explicit rather than a raw-evidence claim.
Current full/repair/fault receipts, child controls, failed validation and exact PostgreSQL excerpts
are retained. The Python/pgTAP comparison above has its separate partial outcome and operator
route disposition. No broader WCE12 efficacy/full-book/new live-provider qualification follows.

The TEMP follow-up also checked Context7's PostgreSQL18 material and the
[primary security-definer guidance](https://www.postgresql.org/docs/18/sql-createfunction.html#SQL-CREATEFUNCTION-SECURITY):
temporary object masking is a relevant concern, while the repository-specific blocker is the
actual privileged-read/custody-check ordering documented above. No exploit or policy change is claimed.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 2 current, 0 superseded.


**test-audit-resolution**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Final test-audit-resolution required functional and native union](records/tr10.final-required-union.json) | TR-09/10 | passed | TR-09, TR-10, TR-11, TR-12, TR-13, TR-14, DTA-001, DTA-002, DTA-003, DTA-004, DTA-005, DTA-006, DTA-007, DTA-008, DTA-009, DTA-010, DTA-011, DTA-012, DTA-013, DTA-014, DTA-015, DTA-016, DTA-017, DTA-018, DTA-019, DTA-020, DTA-021, DTA-022, DTA-023, TR10-F01, TR10-F02 | 2026-11-06 |
| [Partial native Python and pgTAP assertion comparison](records/tr15.native-assertion-comparison.json) | TR-15A | partial | TR-15, TR-15A, I05 | 2026-11-06 |
<!-- evidence-index:end -->
