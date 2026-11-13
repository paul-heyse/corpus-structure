# Evidence contracts

**Status:** Proposed plan; nothing implemented. **Created:** 2026-11-13.

This companion owns the designs of TS-09 (the refusal contract and its weak sites), TS-13
(provider and controlled test identities, and prerequisites decided before setup) and TS-14
(preservation assertions, the redaction-order control and exact task state for the stdio modes).
The [coordinator](../test-system-target-design_2026-11-13.md) owns package state, the dependency
queue and the disposition of every finding named here.

**Baseline and evidence.** Source was read on `main` between `f03170a89` and `434023ee8`,
2026-11-13, while another session was committing declared-data-operations (DDO) work; line
citations are as read. Every design statement is **Proposed**. Source facts are
**Interface-checked by source inspection, 2026-11-13**. The audit's site lists are carried with
their own limits: counts for files it sampled may be incomplete.

**Paths.** `tests/…` and `src/…` are relative to `python/corpus-structure/`; root paths are written
as root `tests/…`, `scripts/…`, `conftest.py`, `pyproject.toml`. Section references (§4.4 and so
on) are to the [source review](../../design_review/reviews/design_review_test-system-target-design_2026-11-13.md).

## Current baseline and what is reused

- **The strongest refusal form already exists.** `tests/semantic/test_private_records.py:131–176`
  runs a positive control in a savepoint and rolls it back (`:139–149`), then asserts SQLSTATE and
  exact primary message (`:157–160`) and the absence of `ops.task_result` and `kb.observation`
  rows. `tests/semantic/test_local_semantic_admission_native.py:597–621` binds each corruption
  label to its own SQLSTATE with message or constraint name, and adds the diagnostic context for
  the generic `P0002` case (`:622–624`). `tests/semantic/test_native_fixtures.py:192–199` pins
  `42501` per denied statement. TS-09 makes these forms the rule and gives the unwrapping one home.
- **A prerequisite route already exists.** `tests/conftest.py:122–138` decides the `corpus`
  prerequisite at collection: it adds `qualification_prerequisite` and `qualification_reason` to
  the item's user properties and a `skip` marker, so no fixture runs.
  `scripts/test_receipts.py:466–484` classifies a skipped node as `blocked`, or `inapplicable`
  when the item carries `qualification_optional`, and stores the reason.
- **Exact list and tuple assertions are the norm** in the files TS-14 touches; the named sites
  are exceptions inside them.

## Target design and contracts

**The refusal contract** (§4.4). A negative control states three things at its call site.

| Part | What it is | Why |
|---|---|---|
| Reach | A minimal-pair positive control on the same prepared state in the same transaction, rolled back in a savepoint | Shows the case arrives at the guarded boundary, so the refusal is not caused by missing setup |
| Reason | The boundary's own diagnostic identity: SQLSTATE plus constraint name or primary message, and a context field where several guards share a message. For Python and CLI refusals: exception type plus message, or error code plus message | Removing one guard must fail exactly its case |
| Effect | Absence of what the guarded operation would have left, with a presence premise in the same output | An absence check alone passes when nothing ran |

Expected values stay at the call site. Two mutations may legitimately reach one guard; their rows
repeat the reason and the minimal pair still proves reach. Where message text is product wording
that churns, prefer the constraint name, or SQLSTATE with context.

**Evidence class** (§4.5). A provider-backed claim and a controlled claim are different test
identities. A prerequisite is a marker decided at collection; its name and reason enter the
item's receipt properties and the skip happens before any fixture. Whether a missing prerequisite
is `blocked` or `inapplicable` is the qualification policy owner's declaration, not the body's.

**What consumers stop doing.** Accepting any `DBAPIError`; discarding mutation labels; unwrapping
driver errors by hand in each test; reading an asset variable in a body to choose between a
provider and hand-written replies; calling `pytest.skip` after scenario fixtures have run.

**Preserved guarantees.** Positive controls, per-case reason tables, atomicity assertions and
`SERIALIZABLE` where the product uses it. A mocked provider is never `passed`. Independent
expected values are authored, never derived from the implementation under test.

**Intentional behavior changes.** On a host without provider assets the ordinary lane reports the
provider node of `test_pm2_result_native.py` as blocked, where today it passes on a controlled
branch. That is the truthful outcome.

## Pivotal mechanisms

| Mechanism | Use here | Limit | Reference |
|---|---|---|---|
| psycopg `Error.sqlstate` and `Error.diag` (`constraint_name`, `message_primary`, `context`) under SQLAlchemy's `DBAPIError.orig` | The diagnostic tuple | `context` is present only for errors raised inside functions | Existing use at `test_local_semantic_admission_native.py:612–624` |
| Savepoints (`begin_nested()`) | Positive control and refusal in one transaction | Sequences do not roll back | §7 "Rollback class" |
| Read-only before privilege | Why privilege refusals use the rollback class | `25006` masks `42501` in the read class | §7 "Read class" |
| Markers whose skip is added at collection | Prerequisites before setup | String `skipif` conditions evaluate at setup; booleans at import | §7 "Prerequisites before setup"; pytest 9.1.1 `_pytest/skipping.py` |

## TS-09 — The refusal contract helper and the named weak sites

**Required input.** None. A family that moves to the rollback class in
[TS-10](isolation-and-seeds.md) receives its contract here first or in the same change.

**Implementation vision.**

*The helper.* One small support module at the package tests root (importable by canonical name
from every directory; its name is chosen with [TS-06](scenario-and-support-ownership.md)'s
placement rules). It provides one context manager, `native_refusal(sqlstate, *, constraint=None,
message=None, context=None)`, that:

1. expects a `DBAPIError`, or a production `InvariantViolation` whose cause is one, as
   `test_private_records.py:150–155` unwraps by hand today;
2. requires the driver error to be a `psycopg.Error`;
3. compares `sqlstate` exactly, `constraint` with `diag.constraint_name` and `message` with
   `diag.message_primary` exactly when given, and requires `context` to occur in `diag.context`
   when given;
4. on mismatch reports the whole observed tuple, so a wrong reason is readable in the failure.

It holds no expected values and no table of guards. Its own controls run against literal
statements on the existing `db` rollback connection, so this package does not wait for TS-05;
when TS-05 lands they follow the `db` rename with every other consumer: it accepts a division by zero as `22012` with its message; it rejects
a wrong SQLSTATE, a wrong message, a wrong constraint, a missing context, a non-driver exception
and a block that raises nothing.

*The sites.* Each row gets the three parts of the contract. "Add reach" means a positive control
on the same state; "pin" means SQLSTATE plus message or constraint through the helper.

| Site | Today | Change |
|---|---|---|
| `tests/semantic/test_publication.py:223–232` | Writer inserts a `data.entity` row with no realization; reader calls `data.begin_stage()`; any `DBAPIError` | Pin `42501` per statement. The missing realization would raise `23503`, so `42501` proves the privilege fence without new inputs |
| `tests/semantic/test_arrow_publication.py:180–185` | Same writer-bypass shape | Pin `42501` |
| `tests/semantic/test_native_closure.py:67–75` | Five statements under the admitter; four would also be refused by immutability triggers | Pin `42501` per statement; the trigger block at `:76–90` keeps its messages |
| `tests/evaluate/test_record_references_native.py:97–108` | Bare `DBAPIError`; pass B was already recorded at `:86`, so a uniqueness refusal satisfies the second check | Pin each refusal's own reason; where uniqueness is the intended guard, say so by constraint name |
| `tests/evaluate/test_operation_fitting_native.py:279–307` | Twelve labelled mutations; the label is discarded at `:305` | Bind each label to its diagnostic tuple, as the forged-judged table does |
| `tests/semantic/test_contextual_enrichment_native.py:65–157` | Thirteen corruptions under bare `pytest.raises(DBAPIError)` (`:154`); no positive control | Add reach (complete the uncorrupted envelope in a savepoint, roll back); pin per corruption. Moves with its family in TS-10 |
| `tests/semantic/test_interpretations_native.py:162` | Eight mutations, bare | Pin per mutation |
| `tests/semantic/test_arrow_publication.py:445–495` | Six unbound intents, bare (`:484`) | Pin per case |
| `tests/semantic/test_runtime_bindings_native.py:136–148` | Eight mutations under `23514` alone | Add constraint name or message per mutation |
| `tests/semantic/test_pdf_publication.py:363–369` | `P0002` "query returned no rows" | Add the context naming the guarding function |
| `tests/semantic/test_review_bundle.py:673–773` | Sixteen corruptions ending in bare `pytest.raises(ValueError)` (`:771`) | Bind each corruption to its message |
| `tests/methods/test_m1_cli.py:9–35` | Five pin refusals: exit code 2 and any of four words, one of which the parser echoes for unrelated usage errors | Pin the message for each argument set; keep the no-database guard |
| `tests/test_source_cli.py:356–357` | Nonzero exit for a retired positional form | Pin exit code and message |
| `tests/methods/test_m1_readings.py:200–209` | Training values symmetric about zero, so dropping centering gives the same score | Use training values with a nonzero center (`tests/semantic/test_record_policy.py:76–91`) |

Found while confirming TS-10's families (2026-11-13):

| Site | Today | Change |
|---|---|---|
| `tests/semantic/test_domain_operations.py:864–992` | `declaration`, `resolution` and `cut` use `match=None` (`:963–971`) | Pin all five refusals; `valid` is the family's reach |
| `tests/semantic/test_imported_declaration_membership.py:228–333` | `revision` and `run` share one message; `entity`, `class` and `establishment` share another (`:308–313`) | Add SQLSTATE and, where the guard is one function for several mutations, the context; state in the table which mutations share a guard |
| `tests/semantic/test_identity_exclusions_native.py:21–230` | Regex `match=`; two expected strings are weak (`"check constraint"`, `"identity differs"`); `23514` only for the eight attribute cases (`:221–222`); no positive control | Add reach (publish the untampered batch in a savepoint, roll back); pin all eighteen; replace the two weak strings with constraint name or full message |
| `tests/semantic/test_occurrence_context.py:143–199` | Regex message; no positive control | Add reach; pin SQLSTATE with the message |
| `tests/semantic/test_private_records.py:223–263` | Regex `match=`; no positive control | Pin; add reach when it moves to `publish_on_connection` |
| Permission refusals: `test_identity_exclusions_native.py:233–244` (three statements), `test_domain_operations.py:246`, `test_occurrence_context.py:315` | Message regexes; none pins a SQLSTATE | Pin `42501` per statement, keeping the message |
| `tests/semantic/test_domain_operations.py:254` | `"untrusted staging relation sp_record_report"` after a committed `GRANT TEMP` | This is the disposal guard's refusal, not a privilege error; pin its own SQLSTATE and message |

DDO sites, edited in coordination with TS-18 and the DDO session, which is changing the file:

| Site | Today | Change |
|---|---|---|
| `tests/semantic/test_data_operation_storage.py:2019` forged-graph family | `match=r"graph\|closure\|discovery"` for each of four mutations | One reason per mutation |
| `tests/semantic/test_data_operation_storage.py:40`, `test_data_operation_wire.py:111` | `len(...) == 18` | An authored set of names where the set is the claim; otherwise remove |

**Consumers migrated.** The hand unwrapping at `test_private_records.py:150–160` and
`test_local_semantic_admission_native.py:612–624` moves onto the helper, so one form exists.

**Example and failure case.** A forged-custody case passes because `complete_task` refuses with
`23514` and the custody message. If the custody guard were removed, a neighbouring check might
still refuse the forged record with `23514` and another message; today's strongest sites would
catch that, the bare sites would not, and after this package each of them fails with the observed
tuple printed.

**Acceptance and closure.** Each named site pins reach, reason and effect. Removing one guard
fails exactly its case; this is established by reasoning over the guard conditions for each
site, written in the commit, not by mutating production (DTA-001).

**Verification.** `uv run ci test -- PATH` for each edited module, and the helper's own controls.

**Open premises.** Some mutations may turn out to reach a different guard than their label
suggests. That is a finding about the test's input: fix the mutation so it reaches the named
guard, or relabel it; do not widen the expected reason.

## TS-13 — Provider and controlled identities; prerequisites before setup

**Required input.** None.

**Implementation vision.**

*The marker.* `pytest.mark.prerequisite(name)` is registered in root `pyproject.toml` beside the
existing markers (`:70–73`) and declared like `corpus` in `tests/conftest.py:101–103`. A small
registry in the package conftest maps each name to a check that returns a reason or `None`:

| Name | Check | Replaces |
|---|---|---|
| `pm2_native_assets` | `CORPUS_PM2_NATIVE_TEST_ASSETS` is set and names a directory | Body skips at `tests/semantic/test_characterization_native.py:1727–1729` and `:2112–2114`; `skipif` at `test_pm2_parser_stage_native.py:42–44` and `test_combined_native_qualification.py:36–38`; the body read at `test_pm2_result_native.py:325` |
| `page85_native_capture` | The retained capture and original exist and are hydrated from Git LFS | `tests/semantic/test_native_documents.py:93,97` |
| `task86_witness` | The retained canonical-byte witness exists | `tests/semantic/test_pdf_json_publication.py:211` |
| `nemotron_runtime` | The isolated parser environment exists | `tests/ingest/test_pdf_recognition.py:166–172`, for the tests that really start the parser |
| `corpus` | Unchanged check (`tests/conftest.py:106–119`) | — |

`pytest_collection_modifyitems` (`tests/conftest.py:122–138`) evaluates each named check once per
session and, for an item whose prerequisite is missing, extends `user_properties` with
`("qualification_prerequisite", name)` and `("qualification_reason", reason)` and adds
`pytest.mark.skip(reason=reason)`: exactly the `corpus` route, generalized. The `corpus` marker
keeps its name and goes through the same loop. No fixture of a skipped item runs, which closes
the DTA-018 instances where a clone, release, PDF and published source are built before the skip.

*Receipts.* Nothing new is needed in `scripts/test_receipts.py`. A skipped node already
classifies as `blocked` with the stored reason (`:481–482`), and the prerequisite name is in its
properties. The registry never sets `qualification_optional`; a policy owner who declares a
prerequisite inapplicable for a lane does so in the qualification policy, and the classification
at `:481` honors it.

*The split.* `tests/semantic/test_pm2_result_native.py:284–553` reads the asset variable at
`:325` and, when it is unset, completes through hand-written replies with a `controlled-test`
checkpoint (`:356`). It becomes two tests over one shared scenario helper:

| Identity | Marker | Body |
|---|---|---|
| Provider | `prerequisite("pm2_native_assets")` | Opens the real workers, settles the claim, then runs the reassignment-after-lease-loss control (`_settle_reassigned_dipo`, `:555–613`) |
| Controlled, named as such | None | The hand-written replies and `controlled-test` profile; its name and docstring say no provider runs |

The existing controlled test in the same file (`:102–278`) shows the naming. The parametrization
at `:279–283` stays on both. If the reassignment control has no controlled form, it exists only
under the provider identity and the controlled test says what it leaves out.

**Consumers migrated.** The sites in the registry table. The scheduling control in
`test_pdf_recognition.py:381–417` is handled in [TS-07](scenario-and-support-ownership.md); it
takes the `nemotron_runtime` marker only if its owner cannot be constructed without the runtime.

**Superseded machinery removed.** Body-level `pytest.skip` after fixtures at the listed sites; the
asset branch in `test_pm2_result_native.py`; the two `skipif` decorators, replaced by the marker
so the receipt names the prerequisite.

**Acceptance and closure.** No test body reads an asset variable to choose its evidence class;
no body-level provider skip follows scenario fixtures; a run without assets records the provider
nodes as blocked with `qualification_prerequisite` in their properties and the controlled nodes
as passed (DTA-028, DTA-018). A run with assets is the operator's to make; this package reports
that outcome as `not_run` unless it was made.

**Verification.** `uv run ci test -- python/corpus-structure/tests/semantic/test_pm2_result_native.py
python/corpus-structure/tests/semantic/test_pm2_parser_stage_native.py
python/corpus-structure/tests/semantic/test_native_documents.py`, then read the result's
blocked nodes and their properties through `ci`.

**Open premises.** The ordinary lane's required set must not count a blocked provider node as a
failure of the lane where the policy treats provider evidence as opt-in; that declaration belongs
to the qualification policy owner and is confirmed before this package's first managed run. The
series' completion depends on it too, since the final `uv run ci test` passes on a host without
provider assets only if it holds; the coordinator lists it as a
[premise](../test-system-target-design_2026-11-13.md#candidates-rejected-options-and-open-premises)
to be settled before TS-23. TS-22 depends on this marker for the DDO-12 provider obligation.

## TS-14 — Preservation assertions, redaction order and exact task state

**Required input.** TS-08 for the two-run comparison only; the other sites are independent.

**Implementation vision.**

*DTA-006: preservation where the claim is preservation.*

| Site | Today | Change | Wrong implementation it then catches |
|---|---|---|---|
| `tests/semantic/test_identity_exclusions.py:124–143` | Row counts and one distinct `establishment` value | Assert which two entities were grounded: the exact set of `(entity, class, establishment)` memberships and the exclusion's endpoints | One that grounds the wrong entities, or one entity twice |
| `tests/semantic/test_exclusion_comparison.py:106–119` | Compares a run with itself; requires no changes and equal examined counts | Compare two runs with one known difference and assert the exact change list. The changed run is a commit clone of the exclusion seed plus one change ([TS-08](isolation-and-seeds.md)) | A comparison that examines rows and always reports no change |
| `tests/semantic/test_reference_evaluation.py:127–163` | Passes A, B and C carry the same content, so every score is perfect | Add one submission with an unmatched extra claim and a missing claim; assert the exact precision, recall and unmatched lists | A matcher that counts every submitted claim as matched |
| `tests/semantic/test_execution_projection.py:127–133` | Diagnostic fields checked for truthiness | Assert the exact `contract_id`, `consumer`, `expected`, `actual` and `remedy` for the selected diagnostic | One that fills fields with any non-empty text |
| `tests/semantic/test_contextual_workflow_native.py:189,198,202` | Substring and non-empty checks for retained compatible edges | Assert the exact retained edge tuples in the page and in the exported rows | One that retains an incompatible edge or drops one of two |

The whitespace-only difference of pass B in the reference evaluation is deliberate and stays.

*DTA-027: redact before clip.* `tests/test_cli.py:93–106` passes under either order, because no
secret straddles the clip boundary. Production redacts with `safe_text` and then keeps the last
12,000 characters of standard output and the last 6,000 of the diagnostic
(`src/corpus_structure/cli/operations.py:161,186–187`). The control is rebuilt so that order
decides the result:

- Place a credential-bearing URL so that the 12,000-character window, measured on the raw text,
  begins inside the credential. Clip-first then leaves a tail fragment of the secret with no
  `user:` prefix or scheme for redaction to recognize.
- Assert that the fragment is absent, and that the mask token appears at the position the
  redact-first order produces. The presence of the mask is the presence premise for the absence.
- Add the same control for standard error and the 6,000-character diagnostic clip, which has no
  ordering control today.

The filler length is computed from the redacted length, not the raw length, so the test states
the arithmetic it relies on. A clip-first implementation fails by construction.

*DTA-016 residue: exact task state.* `tests/semantic/test_runtime_entrypoints.py:463–608` runs
four stdio modes and asserts for the three non-complete ones only `task_row != "done"` (`:608`).

| Mode | What the journey does (`:521–541`) | Assert |
|---|---|---|
| `early_exit` | Lists tools and returns before any queue call | The task's exact status as queued for an agent, attempt unchanged, no holder, no lease |
| `cancelled` | Cancels at a checkpoint before `lease_and_read` | The same |
| `tool_failure` | Leases the task, then fails a `read_unit` on another task id | The exact status, attempt, holder and lease the shutdown leaves, and no observation or result row |

The assertion reads `status`, `attempt`, `claimed_by` and `lease_until` in one row and compares
the tuple. For `tool_failure` the expected tuple is what production's session shutdown is
specified to leave: either still leased under attempt 1 until expiry, or released. The
implementer reads the shutdown path, states which, and pins it; a guess is not written into the
test.

**Acceptance and closure.** Each DTA-006 site fails for the wrong implementation in its row. A
clip-first implementation fails the redaction controls by construction. The three non-complete
stdio modes assert their exact task state.

**Verification.** `uv run ci test -- python/corpus-structure/tests/test_cli.py
python/corpus-structure/tests/semantic/test_runtime_entrypoints.py
python/corpus-structure/tests/semantic/test_exclusion_comparison.py
python/corpus-structure/tests/semantic/test_reference_evaluation.py`.

**Open premises.** Whether `safe_text` recognizes a credential by its `user:secret@` shape, by
the scheme or by both decides where the boundary must fall; the implementer reads it and places
the boundary so the surviving fragment matches no pattern. The state a `tool_failure` session
leaves is read from production as described above.

## Outside this companion

- Which refusal families move to the rollback class, and their seeds:
  [isolation classes and scenario seeds](isolation-and-seeds.md) (TS-10).
- The DDO refusal and lease families and their classes:
  [data-operations test alignment](data-operations-test-alignment.md) (TS-18); the DDO-12
  evidence mapping and provider run (TS-22).
- The audit's minor notes under DTA-027 on `tests/test_settings.py` and the naming notes under
  DTA-028 are recorded there and are not scheduled.
- Blocked versus inapplicable for a missing provider prerequisite is the qualification policy
  owner's declaration.
