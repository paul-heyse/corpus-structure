# D6 · Orchestration, metrics and policies

**Proposed (2026-10-28).** How a run executes: the stage graph, task lifecycle, caching and
reuse, debug slices, GPU sharing on the RTX 5090, the metrics every stage records, and the
policy language that decides which methods run where. Tables are in
[D3 §4](D3-database.md#4-ops-methods-policies-runs-and-tasks); methods in [D4](D4-method-catalog.md).

## 1. Principles

- **One orchestrator, a database queue.** A Python process drives runs; workers claim tasks
  from `ops.task`. No workflow engine: the graph is small and fixed, and the database already
  records everything a workflow engine would.
- **The MCP server is a separate process; the database is the only shared state** (decides
  OPEN-D8-1 and OPEN-D9-2, design authority 2026-10-28, from the [store note](../design_review/evidence/2026-10-28_library-store/README.md) L-S7 and the
  [interfaces note](../design_review/evidence/2026-10-28_library-interfaces-eval/README.md) IE-4). Claude Code starts one stdio server per session (and one per
  golden subagent, D8 §2.2), which dies with that session, while a run's agent tasks are worked
  across sessions (§2, §7.4, ADR-0015). So `ci run` owns the orchestrator; the server only reads and writes tables and,
  through the agent completion primitive (§3.1), sends `NOTIFY cs_agent_task_done` inside its
  submission transaction. FastMCP background tasks are not used: they
  would duplicate `ops.task`, and Claude Code accepts MCP tasks only from the main conversation.
  > Status: **Proposed** (source-read and reasoned; not probed end to end against PostgreSQL)
- **Stages are barriers.** All tasks of a stage reach a terminal status before the next stage
  starts. At this corpus size the simplicity is worth more than overlap (`OPEN-D6-1`).
- **Policies decide escalation; methods never do.** Every task that is not part of a base stage
  names the policy rule that created it and the metric values that rule saw.
- **Every eligible unit's fate is recorded, per run.** A unit is eligible for a stage when its
  method's `select` or an entry of the stage's chain would route it. Each eligible unit gets a
  task: ran and produced, ran and found nothing, failed, reused from cache, waiting for the agent,
  or `skipped` with a reason (`scope`, `limit`, `budget`, `prerequisite_failed`). Nothing is
  silently absent, and the coverage a typed query reports for its scope (units extracted, skipped
  by reason, failed; D8 §5) is counted from these tasks (P0CL-11; operator, 2026-10-28).
  > Status: **Proposed** (2026-10-28)
- **A finished run's fates are fixed at its `finished_at`.** Its fates are its tasks as of
  `ops.run.finished_at`: a task that reaches a terminal status later (an agent task left
  `awaiting_agent` that a later submission settles as a twin, §4) counts as unresolved for that
  run. Every reader applies the same cut: the fate reader, the coverage query (D3 §9),
  `kb.run_observation` (D3 §8) and `ci promote`'s check (D7 §7). So a finished run stays the
  snapshot it was when it finished, and twin settlement can still write to its tasks. A per-run
  fate snapshot table was considered and not adopted: the timestamp cut gives the same answer
  without a second record of the tasks.
  > Status: **Proposed** (2026-10-28)

## 2. The stage graph and run lifecycle

```text
ingest ─► embed ─► extract ─► normalize ─► scope ─► link ─► propose
                                                              │
       ┌──────────────────────────────────────────────────────┘
       ▼
  assemble ─► check ─► finalize ─► measure ─► route ──(new tasks, iteration < limit)──► escalate ─┐
       ▲                                        │                                                │
       └────────────────────────────────────────┼────────────────────────────────────────────────┘
                                                └─(no new tasks)─► derive ─► assemble′ ─► finalize′ ─► measure ─► evaluate ─► finish
```

| Stage | Methods | Unit selection |
|---|---|---|
| `ingest` | M01 (with M03 as a step of its task, D4 M03), M02 | Documents of the run's corpus or slice; M01 tasks reused when bytes and adapter config are unchanged; a changed config re-runs M01, which deduplicates by content, so a content-identical result adds a build to the existing rendition and keeps its keys (D4 M01, P0CL-01) |
| `embed` | M04 | Segments of kinds the configuration names; aliases of the reference run |
| `extract` | M05, M06, M07, M09, M12, M22; M08 when enabled | Base methods on all eligible segments |
| `normalize` | M11 | Renditions; one task each, writing an observation per math span (D4 §3, P0CL-13) |
| `scope` | M13 | Renditions |
| `link` | M14 | Mentions of global classes |
| `propose` | M10, and M24 in phase 0 | Per policy chain `propose` (§7) |
| `assemble` | M17, M18 (assemble pass) | Run |
| `check` | M20 when enabled, M21: the expensive checks | Candidate claims (by key); no tasks in phases 0–1 |
| `finalize` | M17, M18 (finalize pass), with M19 as one run-level step inside it over the in-memory pool (D5 §8.1, P0CL-13) | Run |
| `measure` | metrics (§6) | Run |
| `route` | policy chains `escalate`, `adjudicate`, `identity` (§7) | Units, claims, alternative groups, identity groups |
| `escalate` | whatever `route` created: M10, M16, M24 | Created tasks |
| `derive` | M23, then incremental assemble and finalize | Run |
| `evaluate` | D7 alignment and scoring | Golden units in the run's scope |

A run of kind `ingest` (created by `ci ingest`) has only the `ingest` stage.

**In phase 0** the graph is `ingest → normalize → scope → propose → assemble → finalize → measure
→ evaluate`: there is no `check` stage, because M19 runs inside `finalize` and M20 and M21 do not
exist yet. `normalize` runs the math grammar's part of M11 (validation, canonical form) and M09's
symbol occurrences, one task per rendition each; `scope` runs M13, whose binding sites assemble
the packets' standing context (D4 §4.1, ADR-0011); `propose` is M24, for the units of the run's
scope (§7.4). Consolidation still takes local scopes from the proposals in phase 0 (D5 §11). M13
is the only scope source from phase 1.

**Upstream methods.** Each phase's graph declares, for every method, the methods whose output it
reads (phase 0: M02, M09 and M11 read M01's rendition; M13 reads M09 and M11; M24 reads the
rendition and M13). When a
unit's upstream task `failed`, its downstream task is created `skipped` with reason
`prerequisite_failed`, so the fate names the cause rather than repeating the failure. The
declaration is the graph's, never a method's (D4 §1 rule 6).
> Status: **Proposed** (2026-10-28)

**Iterations.** `route` runs after each `measure`. If it creates tasks and `run.iteration <
run.iteration_limit` (default 3), they run in `escalate` and the loop returns to `assemble`.
Each iteration's measurements are stored with its number, so the effect of escalation is
visible per iteration.

**Agent barrier.** Tasks for M24 are created with status `awaiting_agent`. When `propose` or
`escalate` holds only such tasks, the run's status becomes `awaiting_agent`. The run option `agent_mode` decides
what happens:

| `agent_mode` | Behaviour |
|---|---|
| `wait` (short slice runs only; the default for kind `slice`) | The orchestrator waits until every agent task is terminal, then continues. It `LISTEN`s on `cs_agent_task_done` on a dedicated autocommit connection, re-queries task status on every wake-up and waits with a timeout, because a notification is only a hint: it is delivered at commit, its payload is ignored, it can be missed while not listening, and lease expiry sends none (store note §4) |
| `complete` (every other run, and every long one) | The run finishes with agent tasks left `awaiting_agent`; their units are reported as unresolved. The agent works those tasks across sessions, and a later run reuses each result once submitted (§4) |

**Long runs are sequences of `complete` runs** (P0CL-12; operator, 2026-10-28). Each run of the
sequence reuses every finished task, cheap under content digests (§4), and is a coherent finished
snapshot; the operator promotes the first with no agent task unresolved as of its `finished_at` (§1, §7.4). A later run
recreates the unfinished agent tasks of an earlier one with the same input hash; the submission
that completes either settles its twins (§3.1, §4), so the agent works each packet once, whichever
run's task it pulls. A `wait` run is short by construction, and one whose orchestrator stops (a
restart, a crash) is cancelled and started again, reusing what finished; so `ops.run` needs no
durable stage and `ci run` no resume.
> Status: **Proposed** (2026-10-28)

**Orphaned runs.** The orchestrator's dedicated connection, the one it `LISTEN`s on, holds a
session-level advisory lock keyed by the run id for as long as it drives the run, and PostgreSQL
releases the lock when that session ends, however the process stopped. `ci status` reports a run
in progress (`running`, `awaiting_agent` or `consolidating`) whose lock is free as **orphaned**,
and `ci run cancel RUN` sets it `cancelled` with its open tasks (`pending`, `running`,
`awaiting_agent`). A heartbeat column would need a writer and a staleness
threshold; the lock needs neither.
> Status: **Proposed** (2026-10-28)

**Run statuses** (D3 `ops.run.status`): `created` → `running` → (`awaiting_agent` ↔ `running`)*
→ `consolidating` (during `derive` and the final finalize) → `finished`; `failed` when a stage
cannot complete (any failed task in `ingest`, or a consolidation invariant violation);
`cancelled` by the operator (`ci run cancel`, above).

## 3. Tasks

### 3.1 Lifecycle

```text
pending ──claim──► running ──► done | empty | failed
   │
   ├──► reused     (an equivalent finished task exists, §4)
   ├──► skipped    (reason: prerequisite failed for this unit, a policy limit or budget reached,
   │                or outside the run's scope)
   └──► cancelled
awaiting_agent ──submission──► done | empty | failed
awaiting_agent ──twin done | empty──► reused  (at the twin's completion, or when leased; §4)
```

**Agent completion.** One orchestration primitive completes an agent task, in the caller's
transaction; `propose_claims` (M24) and `write_golden` (golden passes, D7 §3) call it, and no
other path completes an agent task (`ci run cancel` cancels one, §2). In that transaction it:
1. writes the outcome with a fencing `UPDATE` conditioned on the task's `id`, the `attempt` of the
   caller's lease and status `awaiting_agent`, so a session whose lease expired and was taken by
   another commits nothing;
2. settles the twins: when the outcome is `done` or `empty`, every other `awaiting_agent` task with
   the same `(method_config_id, input_hash)` becomes `reused`, pointing at it; a `failed` outcome
   settles none, because failed tasks are never reused (§4);
3. sends `NOTIFY cs_agent_task_done`, whose payload is ignored: a waiting orchestrator re-queries
   (§2).

Completion takes a share lock on its run's `ops.run` row (`FOR SHARE`); a run's final consolidation
pass takes the row's update lock and sets `finished_at` in the same transaction. A completion
therefore either commits before the final pass reads the pool, and is consolidated, or finishes
after the run and counts as unresolved for it (§1), never in between. Twin settlement share-locks
the run of every twin it writes as well, in id order, and both stamp `finished_at` with
`clock_timestamp()` after taking their locks, so a twin settled during another run's final pass
cannot escape that run's cut.
> Status: **Proposed** (2026-10-28)

Twins are also settled where a submission and a task creation could pass each other: task creation
resolves reuse against `done` and `empty` tasks as for every method (§4), and leasing (`queue_next`)
settles, instead of serving, a task whose twin finished after it was created. So no packet is
served twice whichever of two concurrent transactions commits first.
> Status: **Proposed** (2026-10-28)

### 3.2 Workers

| Worker | Claims | Concurrency |
|---|---|---|
| `cpu` | deterministic methods | process pool, one task batch per process |
| `encoder` | M04–M07 | one process holding the models on the GPU; batches tasks of one method config |
| `llm` | M10, M16 | one async process; up to 16 requests in flight to vLLM, which batches |
| `agent` | none: M24 tasks are pulled by the Claude Code session through MCP (D8) | — |

A worker claims up to its batch size of `pending` tasks of one stage and method configuration in
one `UPDATE … FROM (SELECT … FOR UPDATE SKIP LOCKED LIMIT n)` that also takes `running` tasks whose
lease has expired, sets them `running` with `claimed_by` and an incremented `attempt`, runs the
method, and in one transaction (store note §3, §4):
1. runs a fencing `UPDATE` conditioned on `id` and `attempt`, so a worker that lost its lease
   commits nothing;
2. writes observations by binary COPY with `Copy.set_types` (mandatory: a `real` column needs
   `float4`; JSONB as plain dicts once `jsonb` is declared);
3. writes the outcome, `cost` and `finished_at`.
Pipeline mode is not used: it is experimental in psycopg 3.3 and cannot carry COPY. D3 §8 gives
the indexes and the reuse insert.

**Retries.** Transient failures (CUDA out of memory, a vLLM timeout or 5xx, a dropped database
connection) retry up to twice; an out-of-memory retry halves the batch. Deterministic failures
(a parse error, a schema violation after the repair attempt) are not retried. A worker that dies
leaves `running` tasks whose lease (`lease_until`, 5 minutes, renewed while working) expires; the
next claim takes them, so no reaper runs.

## 4. Caching and reuse

Before creating a task, the orchestrator computes

```text
input_hash = sha256(method name, method version, config hash, method.input_digest(unit, config))
```

and looks for a task with the same `(method_config_id, input_hash)` and status `done` or
`empty` in any kept run. If one exists, the new task is created with status `reused` and
`reused_task_id`; its observations are not copied (`kb.run_observation` resolves them).

- **What invalidates reuse** is exactly what changes the digest (D4 §1 rule 4), which covers the
  **content** a task reads, never its provenance: the unit's content (the rendition's content
  digest for rendition-level methods, the unit's canonical text with its segment key for methods
  whose observations cite offsets, the hash of the assembled packet text for M24 and M10), the
  payload hashes of the upstream observations read, compiled-artifact hashes (extraction schema,
  JSON Schema, rules; `meta.compiled_artifact`, D3 §3), prompt-part hashes (guideline version,
  examples, inventory), model id and revision, and method version. Nothing else (P0CL-02;
  operator, 2026-10-28).
  > Status: **Proposed** (2026-10-28)
- **Task ids are provenance only** (`reused_task_id`), never a dependency. Re-running an upstream
  method with identical output (`--fresh`, a version bump, a new build of a content-identical
  rendition) leaves its consumers `reused`, agent tasks included. Reuse is also sound: a method
  whose observations cite rendition offsets digests the rendition's content (directly, or through
  its unit's segment key), which matches only the same rendition row under content addressing
  (D1 §3.1), while a reused proposal is located on the run's own rendition from its citation frame
  (D4 §4.3, D5 §5.6). So no reused observation cites spans of a rendition the run did not select.
- **Failed tasks are never reused.** `--fresh <method>` on the CLI forces new tasks for one
  method.
- **Agent tasks are reused** like any other: an Opus proposal for an unchanged packet is not
  requested again. Changing the guideline changes the prompt parts and so requests new proposals
  for every unit unless the run option `agent_reuse: by_unit` is set, in which case the agent is
  asked only where the operator's change applies (D7 §8).
- **Twins resolve from a finished twin.** The agent completion primitive (§3.1) sets every other
  `awaiting_agent` task with the same `(method_config_id, input_hash)` to `reused` when a
  submission completes one as `done` or `empty`, in the same transaction (D8 §2.1); task creation
  and leasing settle the rest. Successive `complete` runs (§2) therefore never ask for one packet
  twice. A twin settled after its run finished stays unresolved for that run (§1).
  > Status: **Proposed** (2026-10-28)
- **Tasks of unit type `run` are never reused** (D4 §1 rule 4): they read the whole run, so no
  digest would be cheaper than the work. **Consolidation is not cached**; it is rebuilt each pass
  (D5 §1). M19 runs inside each finalize pass and is not cached either: per-claim caching would
  save nothing, because the pass rebuilds anyway (P0CL-13). M20 and M21 tasks are cached by claim key plus the digest of the claim view
  they read.
- **Deletion.** Deleting a run (D3 §8) keeps tasks that kept runs reuse.

## 5. GPU sharing on the RTX 5090

32 GB is shared by the local LLM server and the encoder worker. Budgets (decided finally by S3,
`OPEN-D4-1`, and S7):

| Component | Memory | Placement |
|---|---|---|
| vLLM with Qwen3.5-9B | weights ≈ 18 GB in BF16 (≈ 10 GB in FP8) plus KV cache; `--gpu-memory-utilization` sets the total | Separate server process from `services/vllm-native` |
| GLiNER2.5 base (M05–M07) | ≈ 1 GB weights, 2–3 GB activations at batch 16 | Encoder worker |
| Qwen3-Embedding-0.6B (M04) | ≈ 1.5 GB | Encoder worker |
| Qwen3-Embedding-8B (M04, if S7 chooses it) | ≈ 16 GB | Encoder worker in **exclusive mode** only |

Two modes, chosen per run from the budgets:

- **Co-resident** (default when the sum ≤ 30 GB): vLLM runs with utilization set to leave the
  encoder budget free; all stages run without restarts.
- **Exclusive**: the orchestrator stops the vLLM server for `embed` and `extract` and starts it
  for `propose` and `escalate` (start-up is about a minute, once per run).

The orchestrator records the mode and the vLLM launch arguments in the run notes.

## 6. Metrics

Metrics are rows in `ops.measurement` per run, iteration and scope. Evaluation scores against
goldens are in `eval.result` (D7 §5); confidence model products are stored as measurements with
scope `method`. Rows a method writes (M02's segment features) carry the writing task's `task_id`
and are read through reuse, as observations are: a run whose M02 task is `reused` reads the rows
of the task it points at (D4 M02). In phase 0 M02 writes character and math features only.

| Metric | Scope | Definition | Used by |
|---|---|---|---|
| `segment.chars`, `segment.math_share`, `segment.inline_math`, `segment.display_math` | segment | M02 profile | routing, packet splitting |
| `unit.claims` | segment (unit) | claims with status ≠ `rejected` whose statement anchor is the unit | routing, reports |
| `unit.encoder_coverage` | segment (unit) | share of the unit's sentences containing at least one core candidate | escalation to M10 |
| `unit.core_absorbed` | segment (unit) | share of core candidates absorbed into full claims (D5 §5.4) | encoder–LLM agreement |
| `unit.llm_core_supported` | segment (unit) | share of M10 full claims that have an encoder core support | encoder–LLM agreement |
| `unit.unresolved_symbols` | segment (unit) | unresolved bindings in the unit's claims | escalation, scope debugging |
| `unit.low_confidence` | segment (unit) | candidate claims below the accept threshold | escalation to M16 |
| `run.status.<status>` | predicate | claims per status | reports, gates |
| `run.alternative_groups` | run, predicate | unresolved alternative groups | routing to judges |
| `run.identity_grey_zone` | run, class | identity groups | routing to judges |
| `run.conflicts` | run, predicate | `contradicts` links | reports |
| `run.orphaned_judgments`, `run.stale_judgments` | run | D5 §7.3 | reports |
| `method.empty_rate`, `method.failed_rate` | method | outcomes over tasks run (not reused) | reports, gates |
| `method.malformed_rate`, `method.unlocated_quote_rate` | method | LLM post-processing (D4 §4.3) | prompt and model choice |
| `method.latency_p50`, `method.latency_p95`, `method.tokens` | method | from task `cost` | budgets |
| `method.sensitivity`, `method.false_positive_rate` | method × predicate group | from the confidence model's fitted tables (D5 §6.4) | de-escalation |
| `math.parse_rate` | run, page | M11 `parse = ok` share | S5, M11 tuning |
| `verify.coverage`, `verify.refuted` | predicate | verifier outcomes over eligible claims | phase 4 |
| `confidence.ece` | predicate group | expected calibration error on dev goldens | gates |
| `intervention.share` | predicate group, stage | accepted claims whose status was set by an agent judgment or supported only by M24, over accepted claims | **the scale-back KPI** (D0 phase 3 gate) |
| `cost.agent_packets`, `cost.llm_tokens` | run, iteration | task counts and tokens | budgets |

## 7. Policies

### 7.1 Language

A domain's `policies.yaml` holds ordered **chains**, one per routing point. Each entry has a
condition (a rule-engine expression over the unit context, §7.2) and an action:

```yaml
version: 0.1.0
budgets:
  agent_packets_per_iteration: 20
  llm_tokens_per_run: 2_000_000
thresholds:
  accept: {default: 0.8, distribution: 0.85}   # by predicate group (ci:group)
  identity: {accept: 0.85, margin: 0.1, new_entity: 0.4}
priors:                                        # cold-start source priors (D5 §6.3)
  agent: 0.9
  local_llm_full: 0.6
  local_llm_core: 0.4
  encoders: 0.4
  patterns: 0.5
chains:
  propose:
    - key: propose.phase0.agent_all              # the run's scope bounds it (§7.4), not a split
      when: "phase == 0 and unit.claim_bearing"
      do: {method: agent.opus/extract, then: stop}
    - key: propose.local_llm.claim_bearing
      when: "phase >= 1 and unit.claim_bearing"
      do: {method: llm.propose_claims/default, then: stop}
  escalate:
    - key: escalate.unresolved_symbols.local_llm
      when: "unit.unresolved_symbols > 0 and not ran('llm.propose_claims')"
      do: {method: llm.propose_claims/default, then: stop}
    - key: escalate.low_coverage.agent
      when: "unit.claim_bearing and unit.claims == 0 and ran('llm.propose_claims')"
      do: {method: agent.opus/extract, limit: 10, then: stop}
  adjudicate:
    - key: adjudicate.alternatives.local
      when: "target.kind == 'alternative_group' and not judged_by('llm.judge')"
      do: {method: llm.judge/default, then: stop}
    - key: adjudicate.alternatives.agent
      when: "target.kind == 'alternative_group' and judgment('llm.judge') in ['unsure', 'low']"
      do: {method: agent.opus/adjudicate, limit: 20, then: stop}
  identity:
    - key: identity.grey_zone.local
      when: "target.kind == 'identity_group' and not judged_by('llm.judge')"
      do: {method: llm.judge/identity, then: stop}
```

- `method` names a method and a named configuration, `<method>/<name>`, declared in the domain's
  `methods.yaml` under `configs:`. The action keeps the name, not a hash: each run resolves it
  against the run's own method configurations, which the registry builds at run start (artifact
  references resolved against the run's schema version, D4 §1), and each task records the
  resolved `method_config_id` (D3 §6.3). One policy version therefore serves runs over different
  schema versions.
- **Registered methods only.** Loading a policy refuses an action whose method the registry does
  not hold, so a policy cannot name a method that does not exist in the build. The example above
  is the statistics policy's shape across phases; **the phase 0 `policies.yaml` holds only the
  `propose` chain** with its phase 0 entry, because phase 0 registers neither M10 nor M16.
  > Status: **Proposed** (2026-10-28)
- **Rows.** Each chain entry becomes one `ops.policy_rule` row: `chain` = the chain's name,
  `priority` = the entry's position, `rule_key` = `key`, `condition` = `when`, `action` =
  `{method: <method>/<name>, limit, then}`, `unit_type` = the entry's `unit_type` or the chain's
  default (`propose`, `escalate`: `segment`; `adjudicate`: `alternative_group`, or `claim` for
  entries that target claims; `identity`: `identity_group`). The `propose` chain is evaluated in
  stage `propose`; the others in stage `route`, and the tasks they create run in `escalate`.
- `limit` caps tasks this entry creates per iteration (in addition to global budgets); excess
  units are recorded as `skipped` with reason `limit`.
- **Run scope.** When the run declares a scope (§8), a unit an entry matches outside that scope
  gets a `skipped` task for the entry's method with reason `scope`, so the unit's fate is recorded
  (§1) and the run's coverage is explicit.
- `then: stop` ends the chain for the unit; `then: continue` evaluates the rest of the chain.
- Chains compile to rule-engine 5.1 `Chain` objects under a typed context; a type error fails
  policy loading. Evaluation takes the first matching entry (`Chain.find`), and `continue`
  re-evaluates the slice after it.
  The entry's rule key travels as the `Chain` entry's value, so the task records which rule fired;
  calls take positional arguments; contexts are typed as in D2 §7.4 (OBJECT symbols, no mapping
  dot-access, UTC, nondeterministic builtins rejected), so a run's routing depends only on its
  inputs ([schema-rules note](../design_review/evidence/2026-10-28_library-schema-rules/README.md) L-04).
  > Status: **Tested** by probe for `Chain` construction and type errors (2026-10-28)

### 7.2 Unit context

| Symbol | Content |
|---|---|
| `phase`, `iteration` | run settings |
| `unit.kind`, `unit.statement_kind`, `unit.claim_bearing` | segment kind; statement kind from markup or M05; whether the kind is claim-bearing (the source profile's explicit hint first, else schema `ci:claim_bearing` on `StatementKind` values) |
| `unit.<metric>` | the unit's latest measurements (§6) |
| `target.kind` (`alternative_group`, `claim`, `identity_group`), `target.size`, `target.max_confidence`, `target.margin` | for adjudication and identity targets |
| `ran(m)`, `outcome(m)` | whether method `m` ran on the unit in this run, and its outcome |
| `judged_by(m)`, `judgment(m)` | whether a judgment from `m` exists for the target, and its decision or confidence |
| `budget.agent_packets_left`, `budget.llm_tokens_left` | remaining budgets |

The context has no split symbol. Test units route to the agent like any unit, so test scores
measure the system as deployed, agent tier included; what keeps evaluation honest is that test
pages never enter a training, fitting, prompt-optimization or example set (D7 §4, D4 §4.2), a
rule on data, not on routing (P0CL-16; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28)

### 7.3 Gap policies and conditional methods

Conditional methods (D4 §3) never switch on automatically. A `gaps` chain evaluated at run
level over metrics and evaluation results names candidate interventions:

```yaml
gaps:
  - key: gap.pattern_candidate
    when: "eval.recall(predicate) < 0.6 and eval.recall_trend(predicate, 2) <= 0.02"
    propose: {method: extract.patterns, scope: predicate}
  - key: gap.record_link
    when: "eval.identity_error_rate(cls) > 0.05"
    propose: {method: resolve.record_link, scope: cls}
  - key: gap.coverage.fact_bearing
    when: "doc.fact_bearing_share > 0 and doc.fact_bearing_without_claims / doc.fact_bearing_share > 0.15"
    propose: {method: llm.open_extraction, scope: document}   # facts with no schema home become schema proposals
```

The coverage gap reads a per-segment *fact-bearing* classification (an LLM classifier, phase 4 with
schema depth): the share of fact-bearing segments that hold no claim. It matters most for business
text, where much prose carries no claims, and it is the trigger for schema growth. The regression
guard (golden-set F1 falling more than a point below the promoted run blocks promotion) is the
experiment rule's guard tolerance (D7 §7).
> Status: **Proposed** (2026-10-28, from the design rationale §4.10); `llm.open_extraction` and the
> classifier are phase 4 methods, not yet in D4

A gap rule's output is a **proposal** in the run report. It becomes active only through an
experiment (D7 §7): a candidate policy version enabling the method, run against the baseline on
the dev goldens, promoted if the target metric improves without guard regressions.

### 7.4 Budgets

Budgets bound cost per run and per iteration. When an agent budget is exhausted, further agent
tasks are created as `skipped` with reason `budget`, so the report shows exactly what was not
asked. During heavy debugging the operator keeps `agent_packets_per_iteration` small (default
20). It bounds escalation iterations (`escalate`, `adjudicate`; phase 1 on). The `propose` stage's
agent tasks are bounded by the run's scope instead.

**Phase 0 coverage.** The phase 0 first pass is a run over the first-pass corpus whose scope is
the declared slice `phase0-golden` (§8), drawn at unit level: the four spike pages whole (the
`spike-pages` slice, 208 units, which hold the trace and core units; the `spike-pages` run already
covers them, and the first pass reuses its tasks) plus each dev golden unit by its unit locator,
about 234 packets in all. That is what the gate, the first experiments (which decide on the dev
golden units, D7 §7) and the bootstrap reference run need. Whole golden pages were the earlier
scope; simulation put them at about 1,655 packets, so the operator chose the unit-level slice
(2026-10-28; [evidence](../design_review/evidence/2026-10-28_phase0-golden-size/README.md)).
Every other eligible unit gets a `skipped` task with reason `scope` (§7.1), so its absence is
explicit and the promoted run reports its coverage (§1). The protocol is the sequence of §2:
successive `agent_mode: complete` runs, each reusing every finished task, while the agent works
the open tasks across as many sessions as it takes, each pulling bounded packets (D8 §3); the
operator promotes the first run with no unresolved agent tasks. The full first pass over every
eligible unit of the first-pass corpus moves to phase 1, where M10 carries it and M24 receives
only what policies escalate (P0CL-09, P0CL-12; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28): a full first pass, about 3,800 packets outside the test and
> reserved pages, exceeds what sessions should carry before encoders and the local tier exist (S1
> counts, record s1.corpus); the unit-level scope's about 234 packets (231–235) and the whole-page
> alternative's about 1,655 (1,405–1,914) come from simulating the dev sample over 500 seeds
> (2026-10-28 evidence folder `2026-10-28_phase0-golden-size`); the exact count follows from the
> sampled set (D7 §3.1)

### 7.5 Initial statistics policies, by phase

| Phase | `propose` | `escalate` | `adjudicate`, `identity` |
|---|---|---|---|
| 0 | M24 on every claim-bearing unit in the run's scope, the `phase0-golden` slice (the spike pages whole plus the dev golden units, §7.4); other eligible units `skipped` with reason `scope`. The phase 0 `policies.yaml` holds this `propose` chain only (§7.1) | — | — (alternatives are rare with one proposer; adjudication arrives in phase 1) |
| 1 | M10 on every claim-bearing unit | M10 retry with hints where symbols are unresolved; M24 where M10 produced nothing | M16, then M24 for `unsure` or low |
| 2 | as 1 | as 1 | as 1, plus identity grey zone |
| 3 | M10 only where `unit.encoder_coverage` < 0.7 or the statement kind's encoder sensitivity < 0.8 | M24 only below calibrated confidence 0.5 | M24 only for groups with margin < 0.1 |

Phase 3 rules are the scale-back: each refers to measured reliability, so as goldens and adapters
improve encoders and the local model, fewer units cross the thresholds and `intervention.share`
falls.

## 8. Debug slices and output size

Named slices (`ops.debug_slice`) serve two uses:

- **Debug slice runs** are restricted to the slice's documents and units; the run kind is
  `slice`, and a slice run is never promoted.
- **Run scope.** A run of another kind may name a slice as its scope (run option `scope`): it runs
  over its whole corpus, the policy chains route only the scope's units, and every other unit they
  match gets a `skipped` task with reason `scope` (§7.1). Such a run can be promoted; its coverage
  says what it left out (§1). The phase 0 first pass is the case in view (§7.4).
- **Corpus.** The run option `corpus` names the slice a run's ingest, normalize and scope stages
  cover (default `first-pass`, the documents the source profile's index marks). The `spike-pages`
  run of phase 0 has corpus `first-pass` and scope `spike-pages`, so M13 output exists for every
  dev page before golden packets are assembled (D7 §9).
- **Method configurations.** The run option `method_configs` (method → named configuration)
  overrides the policy's choice for that run. The golden-expectation run names
  `agent.opus/expectation` through it; that configuration's distinct hash keeps its tasks from
  settling or being reused by live agent tasks (D7 §9).
> Status: **Proposed** (2026-10-28, P0CL-09); the locator contract is D1 §3.4's (P0CL-04)

Slices are declared in the domain's `slices.yaml` ([D2 §12.2](D2-schema-and-guidelines.md#122-slicesyaml))
by **locator**. The locator grammar, its generator and its resolver over a rendition's segments
are [D1 §3.4](D1-knowledge-representation.md#34-locators)'s; slices use page, unit and
paragraph locators (a bare page selects the whole page), and a slice locator must resolve to
exactly one segment, an ambiguous one being refused. Besides locators, a slice may include pages
(`{pages: […]}`), another slice, and a golden set (`{golden_set: <label>}`), whose units enter by
their unit locators. Locators resolve to segments of the selected rendition when a run starts, so
a slice survives ingest changes; a locator that does not resolve fails the run's start. A
`golden_set` selector is resolved at run start too, from the set as it then stands, and the run
records the resolved unit list and its hash in `ops.run.options.scope`, so what a scoped run
covered stays readable after the set grows.
> Status: the `pages` and `golden_set` selectors and the recorded resolution are **Proposed** (2026-10-28)

| Slice | Content | Use |
|---|---|---|
| `trace` | T1–T4 units ([trace](trace.md)) | Acceptance tests; every design change |
| `core12` | the twelve spike core units | Method comparison |
| `spike-pages` | the four spike pages | Throughput, counts |
| `phase0-golden` | the four spike pages whole (`{pages: […]}`, which hold `trace` and `core12`) and each dev golden unit by its unit locator (`{golden_set: <dev label>}`, resolved at run start from the set `ci golden create` samples, D7 §3.1) | Scope of the phase 0 first pass (§7.4) |
| `first-pass` | the 78 first-pass pages | Phase gates; the phase 1 full first pass |

While debugging, outputs stay small by construction: CLI reports summarize (counts, the ten
worst units by a chosen metric, links to `explain` commands), agent packets are capped (D8 §3),
and per-iteration agent budgets bound how much Opus is asked to do (§7.4).

## 9. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D6-1 | Stage barriers versus per-unit dataflow once the corpus grows beyond first-pass chapters | Phase 2 timing |
| OPEN-D6-2 | Co-resident or exclusive GPU mode by default, given the S3 model choice | Spikes S3, S7 |
| OPEN-D6-3 | Default iteration limit and agent budgets that keep debugging output reviewable | Phase 0 practice |
