# TR-15A native assertion comparison

**Partial, 2026-11-06.** The required authenticated-purpose pgTAP comparison is
**blocked**: pgTAP1.3.4 `plan(integer)` needs database `TEMP`, which the current
writer purpose does not have. TR-15A remains open; no executed retain/adopt decision
or pg_prove qualification follows. The [native lifecycle companion](../../../plans/test-audit-resolution/native-lifecycle-and-provenance.md#tr-15a--required-bounded-sql-contract-comparison)
and [coordinator](../../../plans/test-audit-resolution_2026-11-05.md) own disposition.

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
No performance benefit is claimed. Executed relational diagnostics remain unknown
until a suitable authorized comparison route exists.

TR-15B remains dormant: repeated startup while repairing this probe does not
establish that head bootstrap materially obstructs a required concurrent workload.
TR-15C remains dormant: this comparison has no cold-cluster, restart, extension-path
or server-configuration subject. Neither branch was gratuitously probed.

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
