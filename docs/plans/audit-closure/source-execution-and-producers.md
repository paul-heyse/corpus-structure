# Source execution, effect ownership and producer binding

**Proposed implementation plan · 2026-11-03.** Companion to the
[audit-closure coordinator](../audit-closure_2026-11-03.md), which alone owns package state,
the execution queue and new-review finding disposition. This document develops AC06–AC08;
it does not copy their status or take disposition of findings from an earlier active plan.
The operator accepted RC01–RC12 for planning on 2026-11-03. Accepted authority changes are
scheduled in AC00, not applied by writing this document.

## Basis and current foundations

Consume the [principal review](../../design_review/reviews/design_review_audit-closure-target_2026-11-03.md)
at `fd4ea6011ca0a501d0c986829304fe661a3c5751`, especially its
[execution contribution](../../design_review/reviews/audit-closure-target/runtime-boundaries.md),
and the semantic/consumer contributions linked there. The broad audit input is `90ed25c4`.
Source inspection for this plan used `fd4ea601` plus the identified concurrent dirty M1 tree;
no native deployment, provider request or product test was executed. Reacquire relevant dirty
bytes before implementation. Claims about the replacement below remain **Proposed**.

Applicable criteria are core3.3, heuristics1.0, code-intelligence1.4 and test-assessment1.2 from
[standard.toml](../../design_review/design_principles/standard.toml). FP-03/04/05/07 govern
composition, policy meaning, effects and lifetime; H17/H21/H23–25 favor one admitted batch and
short settlement fences over idle claims or another scheduler. CI-01/02/10 require attribution
that says what was actually established. This is focused foundation assessment for plan authoring,
not a new diagnostic audit or runtime certification.

The current architecture owners are [D6](../../design/D6-orchestration-metrics-policies.md),
[D8](../../design/D8-agent-and-query-interfaces.md), and the released operation/binding owner in
[D2](../../design/D2-schema-and-guidelines.md). AC00 reconciles RC04–RC07 and RC11 through their
current decision routes before dependent behavior changes. Source paths below are relative to
`python/corpus-structure/src/corpus_structure/` unless stated otherwise.

| Foundation inspected | What exists and what the plan must change |
|---|---|
| `orchestrate/policy.py:131–185,236–268`, `schema/rulelang.py:200–240`; `orchestrate/semantic.py:985–1075` | Typed authored policy language and compiled chains exist. The current source runner supplies placeholder target/budget/judgment values for capabilities it does not execute. Admit an executable context separately from authored language. |
| `core/method.py:280–360`, `orchestrate/source_reader.py`, `semantic/operations.py:757,1272`; `semantic/query.py:342–362` | Reader operations mostly return owned values, and `read_snapshot` already owns read-only repeatable-read acquisition. The public `connection()` capability still bypasses that promise. Reuse the owner and snapshot route, replacing its four actual callers. |
| `orchestrate/semantic.py:491–722`, `semantic/claim_lifetime.py` | Multiple methods are claimed eagerly; custody/unit preparation occur before renewal, and completion occurs after renewal exits. The owner renews a fixed claim sequence. Its cancellation, deadline and cleanup behavior is reusable, but its active-set/settlement contract must change. |
| `semantic/operations.py:618–704`, `semantic/sql/native_task_completion.sql:6–19`; migration `semantic_0023_execution.sql:343–354` | Completion locks run then task, preserves exact attempt/holder/result-digest replay, and renew rejects terminal tasks. This native contract is a strength; a Python-only reordering that renews completed tasks is insufficient. |
| `orchestrate/semantic.py:151–173,885–899,1024–1031`, `intervene/semantic_server.py:142–159`, `intervene/automated.py` | Method/configuration snapshots, queue/lease machinery and invocation receipts exist, with literal Opus selection repeated across consumers. Extend one binding and migrate these consumers together. |
| `ingest/pdf_recognition_methods.py:72–105`, `ingest/pdf_recognition.py:608–623`; repository `services/nemotron-parse/worker.py:49–106` | Configured weight/tokenizer hashes enter recipe identity; HTTP requests use a model alias and record response model/raw receipts. These do not yet establish which local artifact generation executed the request. Preserve GLiNER's actual byte checks in `methods/gliner.py:111–132,321–330`. |

## AC06 — Admit policy execution and own method reads

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
remain required and open/blocked on the missing binding prerequisite; a weaker unmanaged route
does not complete them. Independent work can continue, but narrowing that accepted target needs
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
