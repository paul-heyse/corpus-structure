# Source execution, effect ownership and producer binding

**Completed selected AC scope; Tested2026-11-04.** Companion to the
[audit-closure coordinator](../audit-closure_2026-11-03.md), which alone owns package state,
the execution queue and new-review finding disposition. This document develops AC06–AC08;
it does not copy their status or take disposition of findings from an earlier active plan.
The operator accepted RC01–RC12 for planning on 2026-11-03. Accepted authority changes are
scheduled in AC00, not applied by writing this document.

Current accepted source71a78774/native105 and complete selected functional/native/provider/
nonfunctional evidence are owned by coordinator §15. Original dated grounding and target detail
below are retained; they do not reopen completed AC work or qualify M1.

## Basis and current foundations

**Implemented source, inspected 2026-11-03 at `75db93e1`; assembled qualification open.**
D4/D6 own methods, applicability and execution; ADR-0054 realizes the accepted corrections.
`orchestrate/source_reader.py` supplies owned read operations in place of public raw connections.
Executable policy admission precedes effects. `semantic/claim_lifetime.py:ClaimOwner` maintains
exact task/attempt/holder ownership through custody, preparation and synchronized short terminal
transactions, with finite exact replay and explicit uncertain settlement. Future batches are claimed
just in time, and completed tasks remain individually durable. The registered `complete_unit_result`
operation remains current, even though registration rather than an obvious direct caller reaches it.

Compatible producer binding now supplies policy, queue, packet, submission, automation and coverage
from immutable run/configuration/unit identity. Configured, provider-reported, manual and managed
startup-generation evidence remain distinct. I03's actual managed-provider receipts retain their
original source/context; final-source provider acceptance is outstanding at AC14.

Paths below are under `python/corpus-structure/src/corpus_structure/`. The target and discriminating
cases below specify preserved behavior and remaining acceptance, rather than an instruction to
reimplement existing claim or producer mechanisms. The coordinator owns package state and evidence.

## AC06 — Admit policy execution and own method reads

**Remaining accepted obligation AC-CA01:** current MCP `queue_next` still advertises unsupported
adjudicate and can return empty success. Narrow current advertisement and refuse unsupported modes
at direct session/project boundaries before discovery, even with no pending runs. Preserve normal
empty extraction and independent reference/golden adjudication. The coordinator owns disposition;
AC14 requires actual tool-schema/invocation controls. Raw archived configuration vocabulary is
separate from executable support. Review I01 also requires shared producer membership to reach
coverage and consumers, including general-only/missing mixed-unit cases.


**Required input:** AC00's accepted RC04/RC05/RC11 authority route, the actual source method graph,
the selected immutable run/release binding, and AC01's released dimensions/subsets where consumed.
An agreed context shape permits preparation; only a working admitted context permits effects.
AC13 participates now in affected operation, configuration and public-surface versions.

The policy owner prepares a source-PROPOSE executable language from fields the source runner
actually supplies. Reuse `Language`, typed `rule_engine.Context`/OBJECT attributes, `Rule` and
`Chain`; keep their strict host adapter. Admission checks chains, unit kinds, actions, method
configuration/protocol and field dependencies before source registration or task creation. A
future authored chain may remain valid authoring material while explicitly unavailable for
execution. An available nullable classification is unknown; unavailable judgment, target or
budget capability has no invented `0`, `false` or empty value. Preserve priority, `continue`,
limits, selected scope and the actual recorded trigger/rule inputs. The initially selected route
is a smaller supported language; add a post-compile dependency check only if a concrete expression
must serve several executable contexts, without depending on private rule-engine AST details.

Move every current `Reader.connection()` source caller before removing that public member:

| Actual caller in `ingest/pdf_methods.py` | Replacement owned capability |
|---|---|
| `:181` PDF document selection | Return owned document references selected by the run's project, frozen corpus keys and configured original-source scope. Preserve order and exclusion behavior. |
| `:333` consumer release lookup | Consume the pinned run/release binding already held by the method context; do not query a mutable default. |
| `:689` SourceView document lookup | Resolve the selected views' document references through the reader, preserving document deduplication and deterministic order. |
| `:999` enrichment preflight | Orchestration admits the released operation before effects; method computation does not acquire general database authority. Effect boundaries retain their own native checks. |

Extend the existing `BoundReader` and `ScopedSourceReader` with these operations. Internally use
the existing `read_snapshot` composition: SQLAlchemy `execution_options(isolation_level=
'REPEATABLE READ', postgresql_readonly=True)` before `begin`, checked-out only for the coherent
read. Return values/references owned beyond checkout closure; close results/cursors and restore
the bound reader on failure. Do not keep a transaction open during model/native computation.
Method publication remains an explicit `MethodContext` capability. Read-only flags help the
internal transaction contract; they are not a security sandbox for arbitrary trusted Python.
No general extra SQL principal or reader pool is selected for these four callers.

Remove `by_unit` from current executable reuse choices and reject an explicit incompatible
request with an explanatory typed refusal; do not silently substitute another mode. Status
either omits orphan assessment or reports unsupported/not-assessed. An empty list may mean
assessed-empty only when an actual assessment occurred. Migrate CLI/API/MCP/help/configuration
consumers with these changes; orphan discovery itself is not added to this package.

**Completion evidence:** independently authored policy cases distinguish unsupported chain/symbol,
unavailable versus available-unknown and first-match/continue behavior, with no task created on
refusal. Exercise all four replaced reader routes, not merely a protocol fake. Native restricted
reader controls must refuse ordinary persistent writes/registration commits and demonstrate that
returned references survive closure. Evolve the existing policy/source-reader tests and the actual
PDF execution cases. Consumer migration and displaced API retirement are part of AC06, even though
AC13 owns the coordinated version/compatibility contract.

## AC07 — Maintain each claim through durable terminal retirement

**Required input:** AC00's ownership/fence preservation boundary; AC06's admitted source operation
and owned reader contract where used. The working native task completion/replay operations remain
the authority. Changes to their ABI require AC13's version slice and I04 readiness first.

The executor claims the next ready method's bounded batch only when it can own that batch now.
Enter its owner immediately after successful claim, before original/recipe custody, input lookup,
unit preparation, provider work or publication preparation. Keep shared immutable
`MathReadingsBatch` preparation at a valid group lifetime without claiming other methods early.
Settle the owned batch before claiming the next. Preserve dependency-driven readiness; with more
than four views, extraction and earlier normalization can both be ready, without one holding idle
leases while another executes. This changes admission order, not native task identities or the
declared dependency semantics.

Replace the fixed renewal sequence with an owner-local active set keyed by exact task, attempt
and holder. One synchronization discipline governs renewal, fenced terminal settlement and
retirement. Renewal snapshots active entries and serializes its short native renewal transaction
against terminal settlement/retirement so an entry cannot complete while a stale renewal is still
authorized to renew it. Merely taking a list snapshot then releasing the lock before database work
does not settle this race. Keep run→task database lock order and finite lock/statement deadlines;
model inference, source parsing and large private preparation never hold this owner lock or a
publication transaction. A narrower per-entry lock is an implementation choice only if it retains
the same ordering and outcome guarantees.

Complete tasks durably one at a time through `complete_unit_result` and its native receipt, within
the owner. After a known committed completion or exact replay, retire that entry under the same
synchronization. Successful earlier tasks stay committed if a later task fails. Batch-atomic
completion is not selected: it changes per-task durability and would amplify retries. A returned
method list is not durable completion, and recording an application error does not authorize
skipping the terminal settlement contract.

An uncertain commit retains the exact attempt, submitted payload/result digest and receipt intent
until the existing replay/receipt operation settles whether it applied. While the entry is in
settlement uncertainty, renewal must not race ahead as though it were an ordinary known-running
claim. Resolve outcome under the same owner discipline; a matching native terminal receipt allows
retirement. Replaying a different digest is a conflict. `P0004` is not successful retirement: it may
mean another holder/attempt or a sealed run. Compare the exact receipt/fence state, preserve the
typed lost/uncertain outcome, stop affected work and propagate failure when ownership is lost.
Expiry alone does not prove loss; the native fence decides whether the legitimate attempt remains
current. If outcome cannot be resolved, retain its recovery identity and report uncertainty rather
than renewing forever or declaring success. Bound settlement/replay attempts by the existing
operation deadlines; do not hold the owner lock indefinitely while other still-running claims
silently expire. If that batch can no longer maintain ownership, cancel/drain its remaining work
and propagate the unresolved/lost state with the per-task recovery identities intact.

Cancellation/loss stops provider work, cancels the live renewal borrower, attempts all owned
closers and joins/drains owned workers before returning. Preserve primary and cleanup failures,
including failed teardown handles. Do not swallow cancellation, convert generic errors into
successful retirement, increase lease duration to hide gaps, or let source-ready sealing precede
successful cleanup and settlement. Reuse current cancellation/deadline primitives and per-task
receipt machinery, not a new scheduler or durable traversal/job service.

**Completion evidence:** deterministic synchronization controls should force renewal before/after
terminal commit, including a delayed renewal snapshot, terminal rejection and exact replay. Real
native concurrent cases cover slow custody/preparation/provider execution/settlement, >4-view
readiness, cancellation, lost commit response, competing reclaim and a later-task failure after
an earlier durable success. Assert exact attempt/holder/digest and observation multiplicity, not
only eventual task counts. Extend `tests/semantic/test_execution_native.py`,
`tests/orchestrate/test_pdf_cancellation_native.py` and the private/published PDF execution tests
under `python/corpus-structure/`; fake renewal alone cannot establish native race correctness.

## AC08 — Bind compatible producers and truthful execution evidence

**Required input:** AC00's RC06/RC07 authority route; AC06's executable action admission; AC07's
attempt lifetime for invocation/receipt binding. AC13 supplies version slices wherever the binding
changes released configuration, packets, persisted reports or native operations.

Extend the existing method/configuration binding with supported unit, proposal protocol/version,
execution kind and mode. One prepared binding drives policy action admission, `queue_agent`, run
snapshots, lease selection, packet preparation, MCP submission and automation. Remove repeated
`agent.opus` classifications only after these actual consumers migrate. Add a second conforming
producer configuration and demonstrate the same path. A new identity implementing the same
protocol is a binding addition; a genuinely different protocol must declare and implement its own
contract. M1 source-record production remains separate from knowledge-claim proposal.

Keep requested/configured model identity, provider-reported identity, and assurance/trust basis
distinct in retained invocation evidence. Bind automation/session/request receipts to the actual
task attempt and frozen binding. Assurance distinguishes verified local artifact custody, trusted
managed service generation, provider-reported receipt and manual operator assertion. None can be
upgraded merely from an alias, session ID or client-supplied model name. Manual MCP use remains
supported under explicit operator trust; no mandatory model authentication or new authentication
service is introduced. Native completion and consolidation still decide observation/knowledge
admissibility.

### I03 — Settle recognition startup-generation/request binding before verified claims

Inspect the actual dedicated Nemotron launch route, artifact manifest/bootstrap and request
worker, including sleep/wake and restart behavior. Determine how selected immutable weight and
tokenizer bytes can be verified before startup, how one service generation is admitted, and how
each submitted request and durable response receipt binds to that generation. A pre-request
health response alone is insufficient if an alias can switch between check and execution. Establish
the controlled launch/routing lifetime or response-generation binding that closes that gap and
specify behavior when a request spans replacement. This is a bounded feasibility investigation
inside AC08, before claiming verified-artifact execution or reuse.

Use trusted local startup custody: a selected file manifest and immutable generation record under
the existing service/operator owner. Replacement bytes under the same display alias require a
new generation/binding or refusal. Preserve requested/reported identity and admitted generation
on each request/attempt; partial, interrupted and failed requests retain their existing raw receipts.
Verify files at the custody boundary rather than hashing large weights per request. This is not
cryptographic proof of GPU contents. If I03 cannot establish trusted generation binding on a route,
that endpoint remains explicitly unmanaged/unverified and cannot reuse results under a
verified-byte premise. The accepted dedicated managed route and its AC14 provider obligation
remain required. Current source implements that binding and historical actual receipts exist;
final-source AC14 applicability is still open. If a future context lacks the binding, its provider
obligation is blocked on that named prerequisite; a weaker unmanaged route does not complete it. Independent work can continue, but narrowing that accepted target needs
an explicit operator scope decision. Do not hide the limitation with a synthetic configured digest. Retain
GLiNER's actual artifact-byte verification without replacing it with weaker alias evidence.

**Completion evidence:** two producer bindings use one queue/packet/completion route; wrong
unit/protocol/mode refuses before effects; manual-trust and provider-reported results remain
distinguishable from verified-local/managed-service evidence. Actual automated invocation receipts
trace to attempts. For the managed recognition route, perform actual startup/request/restart and
same-alias artifact replacement controls, plus a request crossing a generation boundary; an HTTP
fake can check parsing but cannot establish the provider claim. Preserve unmanaged/manual cases
as supported weaker trust, not failed attestation.

## Selected mechanisms, resources and verification timing

Carry forward the review's **Interface-checked** library research; this plan adds no dependency or
new library qualification. Selected mechanisms and conditions are:

- Existing rule-engine5.1.0 typed `Context`, `Language`, `Chain` and strict adapter from
  [the runtime review](../../design_review/reviews/audit-closure-target/runtime-boundaries.md#library-contracts-sources-and-alternatives)
  and [typed context source](https://github.com/zerosteiner/rule-engine/blob/master/docs/source/getting_started.rst).
  The host owns applicability and supplied values; a declared field alone does not establish availability.
- SQLAlchemy2.1.6 read-only execution options and PostgreSQL18 transaction modes through
  existing `read_snapshot`, with [dialect source](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_1_6/lib/sqlalchemy/dialects/postgresql/base.py)
  and [transaction modes](https://www.postgresql.org/docs/18/sql-set-transaction.html).
  Pool reset and cursor closure stay with the existing owner; no read transaction spans model/
  provider computation or private scientific preparation. AC09 rule inference remains inside its
  existing atomic publication transaction.
- Python3.14 `RLock`/event/thread lifecycle and the existing `BorrowerCancellation` supply local
  synchronization and cancellation. The semantic contract is the active-set/receipt discipline,
  not a promise that thread cancellation has a hard total shutdown time.
- [FastMCP4.1.3 context](https://github.com/PrefectHQ/fastmcp/blob/v4.1.3/docs/servers/context.mdx)
  carries request context; it does not authenticate an executing model. Reuse existing session and
  automation receipts and explicit trust rather than add an authentication framework.

For the local concurrent deployment, just-in-time claiming bounds live leases by useful current
work. Owned reads reduce connection hold time; shared immutable math preparation avoids repeated
parsing. A serial batch can still retain multiple large method outputs: settle/release each output
at its last required use, or use existing bounded product drafts, while preserving the method's
declared batch contract and per-task durability. Slow service work must remain cancellable outside
database fences. No speed/RSS/capacity result follows from these structural choices.

During implementation run focused checks at coherent capability endpoints. Representative commands
are `uv run pytest python/corpus-structure/tests/orchestrate/test_policy.py
python/corpus-structure/tests/orchestrate/test_source_reader.py` for AC06, and
`uv run pytest python/corpus-structure/tests/semantic/test_execution_native.py
python/corpus-structure/tests/orchestrate/test_pdf_cancellation_native.py` for AC07; select added
race/provider/consumer nodes explicitly as they exist. AC08 also extends
`python/corpus-structure/tests/intervene/test_automated_receipts.py` and the recognition tests,
then exercises the actual configured provider. Expectations for meaning/race outcomes must be
independent of the changed classifier/settlement implementation. Reuse native acquisition support;
do not weaken a required provider/native test into a mock pass.

No tests are run for this plan-writing task. AC14 owns final-source assembled qualification and
the required union, including actual CLI/MCP/provider consumers where affected. Package completion
does not trigger `just test-all` or full hygiene. DA-032/033 retain current deployment history,
native checks and assurance; only their existing concrete diagnostic-consumer or changed
trust/concurrency/admin-drift triggers reopen them, not this lifecycle correction.
