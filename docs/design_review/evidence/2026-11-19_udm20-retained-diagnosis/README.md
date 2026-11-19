# UDM-20 retained failure diagnosis

**Partial diagnosis, 2026-11-19.** This inquiry rereads the original managed receipts and their
retained bytes. It starts no corpus, provider or reproduction run and changes no database or
diagnostic setting. `summarize.py` opens no database connection. The managed result inspector's
automatic native enrichment reported `NativeResultViolation` on the original book target, so
that view supplies no current native standing. No separate live stage probe was attempted.

## Preserved inputs and target boundaries

| Original managed ID | Original outcome and custody | Durable input |
|---|---|---|
| `1dd5d45ded4b4ea38399fb121a44d28c` | `failed`; operation-account cleanup `established`; held with no expiry | [Native result](../2026-11-18_cli-1dd5d45ded4b4ea38399fb121a44d28c/README.md), and the original sealed observation journal exported here |
| `3fed447a2a5649538c80ac05c1ed7c47` | `failed`; one completed failing call; private children settled | [Discovery/composition fixture receipt](../2026-11-18_cli-3fed447a2a5649538c80ac05c1ed7c47/README.md) |
| `82ba77a0731148faa0bd827ead1373cb` | `interrupted`; supervisor recorded SIGINT, pytest was terminated, private children settled with none pending | [Interrupted retry receipt](../2026-11-18_cli-82ba77a0731148faa0bd827ead1373cb/README.md) |

All three original artifacts already had durable retention. The captured current managed
manifests remain in `raw/`; `summary.json` verifies that their retained native/report files match
the corresponding managed files. The exported journal's SHA-256 is
`fd567ca2bd49f1d1deb2d26a3fd33930c1885153805226189a4f8905e8c0e1cc`, exactly the original sealed
manifest digest. Its 44 parent-journal sequence numbers are contiguous and its manifest records
zero collection omissions. Nested exception detail still has its own explicit omission, below.

The book run acquired **canonical `corpus_structure_dev`, OID `131763263`, port `5434`**, with
demand `demand:c2dc2750c6917f015cb8e6c712098f7c38a9f5306379bd961f0fd974758b1085`.
This is not owned stage `corpus_structure_ddo_stage`, OID `130661481`, on `18/corpus:5434`.
A stage query cannot establish the original canonical intent's absence or resolve its outcome.
Stage is the separate target for subsequent bounded confirmation.

## What the original book evidence establishes

The journal contains nine settlement failures, each reporting SQLSTATE **`57014`** and
`canceling statement due to statement timeout`. They belong to actual tasks **72, 75, 76, 71,
86, 91, 93, 94 and 97**, all at producer attempt 1. The exception context names recursive
`canonical_json`, `ddo_digest`, the retain-intent program, and, in several cases, the actual
`INSERT INTO ops.data_completion_intent` with its payload digest and validation seal. This is
direct evidence for the failure boundary that the original plan only narrated. It is not a
statement-duration or query-plan observation: it does not establish the dominant cost, the
duration inside each function, a lack of lock waiting, or a post-repair margin against 120 seconds.

The completed payload had reached the retain-intent call, including serialized outputs. The
failed statement itself could not add a committed intake row. These artifacts do **not** prove
that no earlier exact intent or independent producer copy existed. In particular, a server
statement cancellation is not evidence of an unknown network commit, and established process
cleanup is not a verdict on publication. The current recovery controls address the missing
durable boundary; they do not retroactively recover these failed payloads.

Four timeout obligations can be joined to the last pinned snapshot: tasks 91, 93, 94 and 97 map
to section pointers `#/groups/467`, `#/groups/447`, `#/groups/489` and `#/groups/391`, respectively.
The other five obligation IDs are absent from that particular snapshot. Exact page extents,
sentence counts and UTF-8 completion sizes for all nine are not recoverable from these inputs.
The driver advertises tens of millions of omitted parameter-representation characters; those
logged omission counts are retained in the summary and are **not** treated as measured payload bytes.

The failure has additional independent causes. Forty individually recorded execution failures
comprise **9 settlement statement cancellations, 23 release-reconstruction refusals, 7 runtime
slice-change refusals, and 1 positioned-construction source refusal**. The aggregate exception
states 41 sub-exceptions and explicitly omits group/chain detail. It cannot identify or classify
the additional nested uncertainty described in the earlier narrative. Neither an exact uncertain
commit identity nor the narrated one unresolved intent is recovered from that aggregate.

The retained native artifact reports **58 receipt acknowledgments**, without receipt truncation,
and a complete **29-member** discovery population. Its snapshot is explicitly `last-pinned`, at
`2026-11-18T12:32:12.552732-05:00`, and has 94 obligations and 20 intent inspections, all
`committed`. It supplies no noncommitted inspection and no fresh final-state census. In
particular, this artifact alone does not independently establish the quoted 20-region/3,411
sentence total or the current standing of the unresolved intent.

## Discovery fixture outcome and replacement controls

The original two-source fixture reached its call and failed with **`population lacks admitted
declared discovery output`** in `ops.ddo_impl_close_data_population`. Its recorded call lasted
275.6 seconds, including the whole fixture call; that duration is not isolated binder time. Its
retry completed setup, then was interrupted before any call report completed. Both private-host
child settlements are established. The retry proves cleanup, not successful native fan-in.

The following are **Tested** controls at their actual scopes, not a rerun of the book or a
measurement of its failed SQL:

| Receipt | What it establishes | What it does not establish |
|---|---|---|
| [`949abc3179834a57aea9598b7da470b9`](../2026-11-19_cli-949abc3179834a57aea9598b7da470b9/README.md), recorded owned-stage N31 observation | The named stage test passed its explicit OID `130661481`, port `5434`, N31 and source-custody assertions; compatible prior discovery closes through the current admitted use, with wrong-role/scope/revoked controls | Current transition-head confirmation, the original two-region composition's final fan-in, book-sized binding plans or timings |
| [`fac1de3a567d40999ee4c0d8e0b2ccdf`](../2026-11-19_cli-fac1de3a567d40999ee4c0d8e0b2ccdf/README.md), private current native test | A changed population member schedules one child while unchanged children retain their exact episodes; an actual aggregate is 16; the selected scope retains old and current provenance under substitution | The original full-view compositor, withheld-book-region behavior, or stage/provider/book qualification |
| [`bd79f9aa68bf4915a7df0d1aa9e7b360`](../2026-11-19_cli-bd79f9aa68bf4915a7df0d1aa9e7b360/README.md), private native recovery | An acknowledged original answer survives explicit retain rollback; generic cross-generation consume/publication preserves the original producer and distinct adopter; exact replay and stale/lease-only refusal; genuine PDF contributor transfer after confirmed retirement across builds/attempts of the same task | Unknown-network-commit fault injection, cross-generation PDF publication, or recovery of the original book answers |
| [`fdd3cb361f0f406690339d723151e630`](../2026-11-19_cli-fdd3cb361f0f406690339d723151e630/README.md), private native recovery | After consume commits, deleting private ACK/body and retiring the adopter does not lose the mapped intent: a fresh claim reconciles, rejects replacement computation and publishes the original intent once | A network commit-loss reproduction or recovery when the database cannot establish producer retirement |

The recovery controls establish why a separate durable intake and mapped native intent can
survive later failure. They preserve private bytes but refuse transfer when exact producer
retirement cannot be proved; ACK possession and lease expiry alone do not authorize takeover.
Original validation cost and its book-scale margin remain a separate diagnosis.

## Remaining observations

UDM-20 remains partial. Before its performance conclusions or UDM-23 acceptance can close:

- Resolve the original canonical intent through its exact recorded target and native identity,
  or record that it cannot be recovered. The currently unavailable inspector and a stage lookup
  are not evidence of absence. Recover all nine region extents and payload sizes if available.
- On explicitly acquired owned stage `18/corpus:5434`, database `corpus_structure_ddo_stage`,
  OID `130661481`, record the actual deployed head, effective deadlines under the application
  principals, and relevant `pg_db_role_setting`. No instrumentation settings were applied or
  reset in this inquiry.
- On that head, observe the bounded original-class settlement, distinguishing statement work
  from waits, with named durations/plans and the accepted limits. Keep large/small region and
  largest-completed contrasts bounded; no whole-book escalation follows a negative reproduction.
- Complete the actual composition fixture and the withheld-region control, and the bounded
  two/four/eight-input binding comparison. The discovery and selective-child controls do not
  supply those plans or the original final fan-in assertions.
- Confirm deployed recovery and discovery behavior at the transition head under the same
  bounded policy. Keep unknown commit, known rollback and cleanup outcomes distinct. Provider
  and whole-book validation remain with UDM-22/23.

`records/udm20.retained-diagnosis.json` owns this partial conclusion. Re-run the deterministic
summary with `uv run python docs/design_review/evidence/2026-11-19_udm20-retained-diagnosis/summarize.py`.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**Other**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Preserved book failure boundary and bounded replacement controls](records/udm20.retained-diagnosis.json) | UDM-20 | partial | UDM-20, UDM-25 | 2026-11-18 |
<!-- evidence-index:end -->
