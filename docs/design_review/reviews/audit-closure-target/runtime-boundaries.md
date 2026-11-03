# Execution and effect target

**Proposed, 2026-11-03.** Supporting contribution by a fresh execution reviewer to the
[principal review](../design_review_audit-closure-target_2026-11-03.md). Baseline90ed25c4 plus
identified dirty M1; static inspection only. Paths omit python/corpus-structure/src/corpus_structure.
No product, database, provider or test execution was performed.

## Policy admission — DA-016

Authoring a policy and admitting it for execution are separate operations. Compile the supported
PROPOSE context against only fields actually produced by source execution. Validate executable
chains, unit kinds, actions and dependencies before source work/task creation. Unknown classification
can remain nullable; an unavailable budget/judgment capability must not be represented by a fake
zero/empty/false value. Retain future language definitions for authoring without claiming that the
current runner executes them. Preserve priority, continue, recorded trigger/rule identity and scope
limits under the existing release/run binding.

Use existing Language/Chain and rule-engine Context.type_resolver/typed OBJECT attributes
(schema/rulelang.py:200–240), not a new DSL. Current compilation permits later-phase inputs
(orchestrate/policy.py:131–185,236–268); propose_agents fabricates context fields
(orchestrate/semantic.py:985–1075). A post-compile dependency walk is an alternative when one
expression genuinely serves multiple contexts; the smaller supported language is simpler now.
Closure: unsupported chains/symbols fail before task creation; available unknown remains distinct
from unavailable; first-match/continue results and recorded inputs remain truthful.

## Narrow method reads — DA-045

Remove Reader.connection after migrating its four source callers, all in ingest/pdf_methods.py:
:181 document selection becomes an owned document-reference query; :333 release lookup uses the
pinned run binding; :689 SourceView document lookup becomes a reader operation; :999 operation
preflight moves to orchestration admission. Methods return/use owned values and retain explicit
MethodContext publication capabilities. BoundReader/ScopedSourceReader no longer expose general
transaction control through the public method interface.

Internally reuse read_snapshot semantics: execution_options(isolation_level='REPEATABLE READ',
postgresql_readonly=True) before begin, with a lifetime only as long as the coherent read needs.
Do not hold a database snapshot through model computation. This protects the effect contract for
trusted methods, not malicious arbitrary Python. A separate arbitrary-SQL reader principal/pool
would add machinery the four callers do not require. Read-only transaction flags alone do not
make an unrestricted raw connection an unchangeable capability.
Closure: no public raw connection; all four routes still work; readers cannot commit registration;
ordinary persistent writes refuse; returned references survive checkout closure.

## Just-in-time owned claims — DA-053

Claim only the next ready method's bounded batch, immediately establish the owner, and retain
ownership through custody, unit preparation, provider work and terminal settlement. Settle that
batch before claiming another. Preserve shared immutable MathReadingsBatch preparation where
useful. Dependency admission delays normalization initially; with more than four views later
extraction and earlier normalization become ready together. Eager claiming across serial methods
currently leaves work outside renewal (orchestrate/semantic.py:491–722).

The owner must synchronize renewal and completion: renewal takes a snapshot of remaining active
claims under the same owner-local synchronization used by fenced terminal settlement and retirement.
Retire only after durable completion or resolved replay/receipt outcome. An uncertain commit retains
attempt identity until its outcome is settled. Keep the short renewal/settlement serialization out
of model inference. Cancellation/loss cannot be swallowed, and P0004 must not be treated as generic
successful retirement: it can mean a different holder/attempt.

Moving completion inside unchanged maintained_claims is insufficient: native renew_claim rejects
terminal tasks (semantic_alembic/versions/semantic_0023_execution.sql:343–354, package-relative).
A racing renewal can report false loss after successful completion. The selected target is
just-in-time claiming plus a synchronized active set within that batch. Atomic batch completion
is an alternative only after assessing its changed per-task durability; this review does not select
it. Renewing all eagerly claimed methods requires idle leases and wider lifecycle bookkeeping.
Preserve native row locks, holder/attempt/replay digest fencing and SKIP LOCKED reclaim
(sql/native_task_completion.sql:6–19; sql/execution_projection.sql:74–87).
Closure: >4-view overlap readiness; slow preparation/run/settlement; renewal/terminal races;
cancellation and competing reclaim. Expiry alone is not corruption or unconditional refusal.

## Producer binding and execution attribution — DA-051/052

Extend the current method/configuration binding with supported unit, proposal protocol/version,
mode and execution kind. Policy, queue_agent, run snapshots, lease/packet preparation and automation
consume that one binding instead of reconstructing agent.opus at each site
(orchestrate/semantic.py:151–173,885–899,1024–1031; intervene/semantic_server.py:142–159;
automated.py:88–97,307–314). Another conforming identity is an explicit binding/configuration
addition. Native completion and consolidation remain the authority for observation/knowledge.
M1 source-record production is a separate protocol, not automatically a knowledge-claim producer.

Record requested/configured identity separately from execution evidence and its assurance:
verified local artifact, trusted managed service, provider-reported receipt, or manual operator
assertion. Preserve trusted manual MCP operation without introducing mandatory authentication or
model attestation. Link existing automated invocation/session receipts to actual task attempts
(automated.py:184–185,249–265,325–328); a client/session identifier is not model proof.

For the dedicated recognition service select trusted startup artifact custody: verify selected
weight/tokenizer files, record an immutable manifest/service generation, and bind each request to
that admitted generation. A replacement under the same alias must create a new binding or refuse.
This does not claim cryptographic proof of GPU contents. Unmanaged endpoints retain unverified
identity and cannot reuse results under an asserted verified-byte premise. Current configured
hashes exceed the HTTP alias evidence (ingest/pdf_recognition_methods.py:72–105;
ingest/pdf_recognition.py:608–623; services/nemotron-parse/worker.py:49–106, repo-relative).
Preserve GLiNER's actual artifact-byte verification (methods/gliner.py:111–132,321–330).
Closure: two producer bindings share the route; incompatible protocol/mode refuses; receipt/trust
premise traces to attempts; alias replacement cannot inherit verified artifact identity.

## Shared candidate preparation and inference — DA-043

Build statement/role/occurrence/symbol indexes once for the pinned candidate cut instead of
rebuilding premise and given-by-others sets per candidate (semantic/domain_operations.py:3253–3273).
Preserve same-statement premises, global assumptions, self-exclusion and occurrence-sensitive symbol
ownership. Prefer an owned membership operation where rules ask membership; retain complete
materialization where a rule truly consumes the full universe. Scientific preparation already
happens outside publication (:2058–2091); do not claim that as a new correction.

Select frontier/delta inference within the existing PostgreSQL/Core workspace: accumulated
conclusions plus newly added frontier; unary rules over new facts, transitive combinations with
at least one new premise, conflict-aware deduplication, termination on empty frontier. Produce
required distinct direct witnesses after the common fixed point, preserving rule versions,
ordered premises and qualification contexts (semantic/inference.py:209–294). Do not replace
qualified rule semantics with plain reachability or silently discard proof multiplicity.

Retain inference inside existing atomic publication initially. Moving it out requires a complete
immutable prospective-input contract plus source/output revision fence, not merely a snapshot name.
No such extra handoff is necessary to eliminate the demonstrated repeated work. DuckDB USING KEY
is a candidate for another complete lowering, not selected: replacement of keyed payloads is not
automatically equivalent to distinct qualified facts/witnesses. Necessary pair comparisons stay.
Closure: independently specified cycles/self-loops/reconvergence, mutual rule enabling, duplicate
conclusions/distinct witnesses, contexts, self-excluded symbols; rollback/replay still coherent.

## Retain necessary trust, remove unsupported promises — DA-032/033/047

Keep frozen predecessor/forward installation, independent live catalog/role checks, cross-row
validation and NOLOGIN publisher trust. No extra blanket triggers, universal certificates or
SHACL-authorized native bypass follow. Reduce assurance only after identifying the exact retained
property and changed trust/concurrency/admin-drift premises; repeated checks alone prove no waste.
(native_candidate.py:789–827,1023–1039; alembic_native.py:90–146; native_products.py:331–342;
sql/admission.sql:5–18,79–152; closure.sql:481–550).

Do not add mandatory per-result deployment identity merely because a field is missing. Preserve
exact deployment history and semantic release/result identity. A demonstrated diagnostic consumer
can bind deployment context to the existing operation/publication receipt; it never becomes fact
identity. Current-only execution remains supported, not universal old-runtime compatibility.

Remove by_unit from advertised current reuse choices until supported. Status must omit orphan
inspection or mark it unsupported/not-assessed, rather than hard-code orphaned=[] as assessed-empty
(cli/orchestrate.py:141; orchestrate/semantic.py:91–95; commands.py:399,441). This does not schedule
orphan-discovery implementation or broad dead-code cleanup.

## Library contracts, sources and alternatives

Selected pins: rule-engine5.1.0, SQLAlchemy2.1.6, Alembic1.20.1, FastMCP4.1.3, DuckDB2.0.0 and
psycopg3.3.6. Context7 resolution preceded scoped queries; relevant guides were rule-engine,
SQLAlchemy/Alembic, concurrency, FastMCP and DuckDB under docs/libraries. Interfaces are
**Interface-checked**; target composition remains **Proposed**. No dependency change is selected.

- [rule-engine typed context](https://github.com/zerosteiner/rule-engine/blob/master/docs/source/getting_started.rst): existing strict host adapter supplies applicability; no new private AST dependency.
- [SQLAlchemy2.1.6 PostgreSQL dialect](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_1_6/lib/sqlalchemy/dialects/postgresql/base.py): readonly execution/reset ownership. Installed base.py:245–274 and psycopg.py:570–574 also inspected. [PostgreSQL18 transaction modes](https://www.postgresql.org/docs/18/sql-set-transaction.html) bound the guarantee.
- [Alembic autogenerate limitations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html): retain existing model-derived/frozen descriptors; generic CHECK-discovery claims were inconsistent, so no reliance on those defaults.
- [FastMCP4.1.3 context](https://github.com/PrefectHQ/fastmcp/blob/v4.1.3/docs/servers/context.mdx) and [authorization](https://github.com/PrefectHQ/fastmcp/blob/v4.1.3/docs/servers/authorization.mdx): request/authentication context is not executing-model authentication. No new auth service is selected.
- [DuckDB recursive state](https://duckdb.org/docs/current/sql/query_syntax/with.html): candidate alternate lowering only; qualify exact pinned semantics and proof preservation before selection.

Reject a new async scheduler, generic provider discovery/authentication framework, extra reader pool
and universal assurance system for these current needs. Each would add lifecycle/maintenance work
without removing the actual missing semantic contract. Retaining an Opus-only route is a viable
narrower alternative only with an explicit substitution limit; the chosen one-binding correction
supports the actual next producer without promising arbitrary provider interchangeability.
