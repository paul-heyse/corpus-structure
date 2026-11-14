# PostgreSQL tooling and cohort execution — design review

**Date:** 2026-11-13. **Tier / purpose:** design / target.
**Focus:** library-targeted pgTAP, pg_prove and pg_virtualenv; efficient execution with trustworthy
evidence and preservation of the current DDO transition.
**Reviewer:** independent design-reviewer agent; published by the coordinator.

## Scope and decision

**Revise for F01.** The selected SQL-family batch and private-host cohort compose coherently
with the existing lifecycle, selection, supervision and receipt owners. The remaining defect is
ambient prove/harness configuration outside the selected, recorded execution contract. No
tooling reselection or broader redesign is indicated.

The subject is the refined [TS-24/25 target](../../plans/test-system-target-design/postgresql-tooling.md)
read on 2026-11-13, its dependencies and adjacent consumers. Source baseline is
`787264d726fbbe0c4c43541976172f32db5f9651` plus live dirty support inspected that day.
The review consumes test-audit publication `28b4a53db` with the
[bounded reconciliation](../test-audit/README.md#postgresql-tooling-reconciliation).
Later concurrent edits are outside the capture.

Criteria: core 3.3, heuristics 1.0, test-assessment 1.2, code-intelligence 1.4 and repository
binding. Functional purpose: dependable native verification supporting DESIGN §1.1.
Code-intelligence extraction, graph analysis and served answers are outside this boundary.
Target behavior and duration benefits remain **Proposed**; cited integration contracts are
**Interface-checked, 2026-11-13**. This is neither implementation acceptance nor TS-23 qualification.

## Model and responsibilities

| Owner | Responsibility |
|---|---|
| Authored SQL family | Independent inputs/expectations/counts and exact logical pytest mapping |
| Collection adapter | Selected membership and final affinity; no second test-count universe |
| pgTAP | Assertions and xUnit lifecycle, including per-case subtransaction rollback |
| pg_prove / native parser | One controlled psql invocation and native TAP/process interpretation |
| Receipt owner | Observations, batch validity, item-bound acquisition, retry and union eligibility |
| PgAdmin | Acknowledged naming/acquisition, leases, policy replay and authenticated cleanup |
| Private-host adapter | One endpoint and explicit purpose Settings for the selected cohort |
| Existing supervisor | Process ownership, interruption, settlement and artifact custody |

The model distinguishes preparation/execution, logical/physical identity, observation/qualification,
and host mode/server incarnation. These distinctions govern the proposed consumer boundary.
A finite family declaration suffices; no universal SQL registry or parallel ledger is warranted.

The target preserves exact selection, independent assertion counts, outer and bounded de-indented
child parsing, raw evidence, and batch validity gating every member. Actual psql context is bound
to executed logical cases. Existing `_union_node_status` accepts passed identities independently
of global errors (`scripts/test_receipts.py:1391`), so global failure alone is insufficient.
`record_native_context(..., nodeid=...)` supplies explicit binding
(`scripts/qualification_plugin.py:51`); preparation/session observations cannot replace it.
Rollback compatibility remains a property of selected operations. Sequence, auxiliary-session or
nontransactional effects require a suitable isolation route.

## Composition, changes and alternatives

The proposed route fits focused cases, subsets and full finite families: stable preparation at
its valid lifetime, selected assertions together inside PostgreSQL, one outer capacity owner and
one private cluster per cohort. This structurally removes repeated preparation/client crossings
(FP-07; H5/H8/H12/H20/H21/H24/H27); no elapsed-time gain is established. Private startup may cost
more than an existing shared host.

Batching enlarges the failure unit: invalid outer evidence invalidates member qualification.
Completed observations remain diagnostic; retry executes the unresolved selected identity.
New cases change authored case/count/mapping data. New commit or multi-session claims use the
appropriate existing isolation/purpose route. Parser upgrades change the bounded framing adapter.
Host substitution changes acquired Settings while preserving PgAdmin custody. Buffered cancellation
or worker loss leaves unobserved completions incomplete/not_run. Growth in cases/workers does not
create an inner automatic pool.

Keeping Python is simplest for Python construction, application, purpose and concurrency claims.
Per-case SQL simplifies attribution but retains crossings. The selected batch adds bounded
framing/attribution and a larger failure unit for its concrete SQL-only consumer. A custom launcher
or TAP grammar supplies no necessary capability; per-case/per-worker clusters duplicate startup.
No interchangeable-backend framework is needed.

## F01 — Ambient prove/harness inputs can alter execution

**FP-05/06; DP-18/20/21; G4. Interface-checked, 2026-11-13.**

The target controls psql startup/libpq/private-host settings but leaves prove/harness discovery
implicit. Installed pg_prove 3.37 delegates argument processing to App::Prove, which loads
`~/.proverc` and `./.proverc` and prepends their options. These can introduce ignore-exit,
custom harness/formatter/plugins, state selection, execution replacement and jobs:
`/usr/bin/pg_prove:35–73,476–501`;
`/usr/share/perl/5.38.2/App/Prove.pm:150–184,195–248`.

TAP::Harness also discovers `HARNESS_RULESFILE`, then local `testrules.yml` files without
explicit rules (`TAP/Harness.pm:448–450,485–491`). `PERL_TEST_HARNESS_DUMP_TAP` can create
unmanaged spool files (`:889–910`). Perl module/preload inputs can substitute implementation.
Exact case checking catches some omissions but does not govern undisclosed runner changes/writes.

**Proposed correction:** the adapter owns one explicit prove/harness configuration: `--norc`,
explicit jobs/source/adapter/harness/formatter, no prove state filtering, explicit harness rules,
and normalized Perl module/preload and harness spool/rules inputs. Supply the intentional adapter
path explicitly. Raw TAP/stderr stay in the managed result. pg_prove supports `--harness` and
`--formatter`; use those around one real invocation and its native source handler.

**Closure:** amend the target and implement this boundary. Focused verification includes
conflicting prove configuration and unexpected psql exit, preserving selected identities,
capacity and failure interpretation. This is correctness verification, not a benchmark or
additional proof campaign. The [coordinator](../../plans/test-system-target-design_2026-11-13.md#finding-disposition)
owns scheduling/current disposition; the review owns this finding's meaning.

## Native library contracts

Installed pgTAP1.3.4 `_runner`/`runtests` supply startup/shutdown and per-case rollback
(`pgtap--1.3.4.sql:6699–6876`). Synthesized child plans require independent expected counts.
The source handler supplies `--no-psqlrc` and `ON_ERROR_STOP=1`
(`SourceHandler/pgTAP.pm:make_iterator`). Native TAP::Parser interprets TAP; bounded child
framing supplies attribution rather than replacing parsing.

postgresql-common294 `/usr/bin/pg_virtualenv` supplies temporary creation/trap cleanup.
Pre-launch PGPORT consumption, generated endpoint and cleanup order require normalization,
explicit Settings and pre-cleanup logs. It supplies neither crash-proof cleanup nor authenticated
application-purpose/durable-host semantics.

## Independent judgments and limits

| Judgment | Verdict and basis |
|---|---|
| A1 Localize change | satisfied: authored cases, host binding, native integration and qualification have coherent owners |
| A2 Explicit domain meaning | satisfied: identity, execution, observation, qualification and acquisition stay distinct |
| A3 Composition | satisfied: native tools compose with existing lifecycle/receipt custody |
| A4 Execution fit | satisfied: coarse SQL, valid preparation lifetimes, affinity and one cohort avoid nested capacity |
| G1 Authority | pass: existing custody and independent expectations |
| G2 Fidelity | pass: logical IDs, multiplicity, acquisition and uncertainty preserved |
| G3 Validity | pass: missing/duplicate/malformed evidence rejects |
| G4 Hidden behavior | **fail: F01** |
| G5 Recovery | pass: incomplete evidence cannot qualify; retry/incarnation/settlement explicit |
| G6 Reuse | pass: preparation reuse separated from fresh execution |
| G7 Claims | pass: support limits and unmeasured benefits explicit |
| G8 Library leverage | pass: generic behavior stays native; custom work is bounded integration |
| CI-G1–CI-G3 | n.a.: no code-intelligence fact extraction, serving or evaluation |

FP-01/02/03/04/07 are supported for this target; FP-05/06 require F01. No additional material
finding was established. End-to-end adapter behavior, private Settings/bootstrap, cancellation and
cleanup remain Proposed and require the plan's focused implementation checks.

**RC01:** D3 still calls private-cluster/plugin alternatives unselected. Integration must reflect
the operator-selected optional cohort and limits, preserving shared default and lifecycle custody.
This is an already-authorized owner update, not a new tooling decision. F01 changes no policy.

**not_run:** `uv run ci test`, `uv run ci check`, probes and benchmarks; read-only review.
**Enclosing architecture:** not accepted here. TS-02/05/08/13, the current DDO transition and
TS-23 retain their obligations. Correct F01 before integration; no prior DDO architecture returns.
