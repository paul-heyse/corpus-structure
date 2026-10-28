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
  golden subagent, D8 §2.2), which dies with that session, while a waiting run spans sessions
  (§7.4, ADR-0015). So `ci run` owns the orchestrator; the server only reads and writes tables and
  sends `NOTIFY` inside its submission transaction. FastMCP background tasks are not used: they
  would duplicate `ops.task`, and Claude Code accepts MCP tasks only from the main conversation.
  > Status: **Proposed** (source-read and reasoned; not probed end to end against PostgreSQL)
- **Stages are barriers.** All tasks of a stage reach a terminal status before the next stage
  starts. At this corpus size the simplicity is worth more than overlap (`OPEN-D6-1`).
- **Policies decide escalation; methods never do.** Every task that is not part of a base stage
  names the policy rule that created it and the metric values that rule saw.
- **Every unit's fate is recorded.** Ran and produced, ran and found nothing, failed, skipped by
  policy, reused from cache, or waiting for the agent: each is a task status, so nothing is
  silently absent.

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
| `ingest` | M01 (with M03), M02 | Documents of the run's corpus or slice; renditions reused when the adapter config is unchanged |
| `embed` | M04 | Segments of kinds the configuration names; aliases of the reference run |
| `extract` | M05, M06, M07, M09, M12, M22; M08 when enabled | Base methods on all eligible segments |
| `normalize` | M11 | Math segments |
| `scope` | M13 | Renditions |
| `link` | M14 | Mentions of global classes |
| `propose` | M10, and M24 in phase 0 | Per policy chain `propose` (§7) |
| `assemble` | M17, M18 (assemble pass) | Run |
| `check` | M19, M20 when enabled, M21 | Candidate claims (by key) |
| `finalize` | M17, M18 (finalize pass) | Run |
| `measure` | metrics (§6) | Run |
| `route` | policy chains `escalate`, `adjudicate`, `identity` (§7) | Units, claims, alternative groups, identity groups |
| `escalate` | whatever `route` created: M10, M16, M24 | Created tasks |
| `derive` | M23, then incremental assemble and finalize | Run |
| `evaluate` | D7 alignment and scoring | Golden units in the run's scope |

A run of kind `ingest` (created by `ci ingest`) has only the `ingest` stage.

**In phase 0** the graph is `ingest → normalize → scope → propose → assemble → check → finalize →
measure → evaluate`. `normalize` runs the math grammar's part of M11 (validation, canonical form)
and M09's symbol occurrences; `scope` runs M13, whose binding sites assemble the packets' standing
context (D4 §4.1, ADR-0011); `propose` is M24. Consolidation still takes local scopes from the
proposals in phase 0 (D5 §11). M13 is the only scope source from phase 1.

**Iterations.** `route` runs after each `measure`. If it creates tasks and `run.iteration <
run.iteration_limit` (default 3), they run in `escalate` and the loop returns to `assemble`.
Each iteration's measurements are stored with its number, so the effect of escalation is
visible per iteration.

**Agent barrier.** Tasks for M24 are created with status `awaiting_agent`. When `escalate` holds
only such tasks, the run's status becomes `awaiting_agent`. The run option `agent_mode` decides
what happens:

| `agent_mode` | Behaviour |
|---|---|
| `wait` (default while debugging) | The orchestrator waits until every agent task is terminal, then continues. It `LISTEN`s on a dedicated autocommit connection, re-queries task status on every wake-up and waits with a timeout, because a notification is only a hint: it is delivered at commit, carries under 8,000 bytes, can be missed while not listening, and lease expiry sends none (store note §4) |
| `complete` | The run finishes with agent tasks left `awaiting_agent`; their units are reported as unresolved. A later run reuses the agent's results once submitted (§4) |

**Run statuses** (D3 `ops.run.status`): `created` → `running` → (`awaiting_agent` ↔ `running`)*
→ `consolidating` (during `derive` and the final finalize) → `finished`; `failed` when a stage
cannot complete (any failed task in `ingest`, or a consolidation invariant violation);
`cancelled` by the operator.

## 3. Tasks

### 3.1 Lifecycle

```text
pending ──claim──► running ──► done | empty | failed
   │
   ├──► reused     (an equivalent finished task exists, §4)
   ├──► skipped    (prerequisite failed for this unit, or policy limit reached)
   └──► cancelled
awaiting_agent ──submission──► done | empty | failed
```

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

- **What invalidates reuse** is exactly what changes the digest (D4 §1 rule 4): unit text,
  upstream observations read (by task id), compiled artifacts (extraction schema, JSON Schema,
  rules), prompt parts (guideline version, examples, inventory), model revision, method version.
  Nothing else.
- **Failed tasks are never reused.** `--fresh <method>` on the CLI forces new tasks for one
  method.
- **Agent tasks are reused** like any other: an Opus proposal for an unchanged packet is not
  requested again. Changing the guideline changes the packet and so requests new proposals for
  every unit unless the run option `agent_reuse: by_unit` is set, in which case the agent is
  asked only where the operator's change applies (D7 §8).
- **Consolidation is not cached**; it is rebuilt each pass (D5 §1). Checks are cached by claim
  key plus the digest of the claim view they read.
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
scope `method`.

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
    - key: propose.phase0.agent_all
      when: "phase == 0 and unit.claim_bearing and unit.split != 'test'"
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
  `methods.yaml` under `configs:`. Loading the policy version resolves each to a config hash and
  creates the `ops.method_config` row with that name.
- **Rows.** Each chain entry becomes one `ops.policy_rule` row: `chain` = the chain's name,
  `priority` = the entry's position, `rule_key` = `key`, `condition` = `when`, `action` =
  `{method_config: <hash>, limit, then}`, `unit_type` = the entry's `unit_type` or the chain's
  default (`propose`, `escalate`: `segment`; `adjudicate`: `alternative_group`, or `claim` for
  entries that target claims; `identity`: `identity_group`). The `propose` chain is evaluated in
  stage `propose`; the others in stage `route`, and the tasks they create run in `escalate`.
- `limit` caps tasks this entry creates per iteration (in addition to global budgets); excess
  units are recorded as `skipped` with reason `limit`.
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
| `unit.split` | `dev`, `test` or null: the split of the unit's document (`eval.document_split`, D7 §3.1) |
| `unit.kind`, `unit.statement_kind`, `unit.claim_bearing` | segment kind; statement kind from markup or M05; whether the kind is claim-bearing (schema `ci:claim_bearing` on `StatementKind` values) |
| `unit.<metric>` | the unit's latest measurements (§6) |
| `target.kind` (`alternative_group`, `claim`, `identity_group`), `target.size`, `target.max_confidence`, `target.margin` | for adjudication and identity targets |
| `ran(m)`, `outcome(m)` | whether method `m` ran on the unit in this run, and its outcome |
| `judged_by(m)`, `judgment(m)` | whether a judgment from `m` exists for the target, and its decision or confidence |
| `budget.agent_packets_left`, `budget.llm_tokens_left` | remaining budgets |

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

**Phase 0 coverage.** A first-pass run in phase 0 proposes for the units of the dev-split pages:
about a fifth of the first-pass corpus is test and stays unextracted (D7 §4), and the dev pages give
the baseline the gate and the first experiments need. The remaining non-test units are created
`skipped` with reason `budget`, so their absence is explicit. The queue persists, so the agent
works a run's tasks across as many sessions as it takes while the run waits at its barrier
(`--agent-mode wait`); each session pulls bounded packets (D8 §3).
> Status: **Proposed** (2026-10-28, design authority): about 3,600 non-test packets exceed what
> sessions should carry before encoders and the local tier exist (S1 counts, record s1.corpus)

### 7.5 Initial statistics policies, by phase

| Phase | `propose` | `escalate` | `adjudicate`, `identity` |
|---|---|---|---|
| 0 | M24 on every claim-bearing unit outside the test split (test units stay unextracted in phase 0, D7 §4) | — | — (alternatives are rare with one proposer; adjudication arrives in phase 1) |
| 1 | M10 on every claim-bearing unit | M10 retry with hints where symbols are unresolved; M24 where M10 produced nothing | M16, then M24 for `unsure` or low |
| 2 | as 1 | as 1 | as 1, plus identity grey zone |
| 3 | M10 only where `unit.encoder_coverage` < 0.7 or the statement kind's encoder sensitivity < 0.8 | M24 only below calibrated confidence 0.5 | M24 only for groups with margin < 0.1 |

Phase 3 rules are the scale-back: each refers to measured reliability, so as goldens and adapters
improve encoders and the local model, fewer units cross the thresholds and `intervention.share`
falls.

## 8. Debug slices and output size

Named slices (`ops.debug_slice`) restrict a run to selected documents and units; the run kind is
`slice`, and a slice run is never promoted.

Slices are declared in the domain's `slices.yaml` ([D2 §12.2](D2-schema-and-guidelines.md#122-slicesyaml))
by **locator**: `page` (a source URI), `page#unit-id`, `page@u:<text prefix>` (a unit, for the
many units without ids) or `page@p:<text prefix>` (a paragraph outside units, such as T1's
lead-in and T2); prefixes match with whitespace collapsed and must select exactly one segment. Locators resolve to segments of
the selected rendition when a run starts, so a slice survives adapter changes; a locator that
does not resolve fails the run's start.

| Slice | Content | Use |
|---|---|---|
| `trace` | T1–T4 units ([trace](trace.md)) | Acceptance tests; every design change |
| `core12` | the twelve spike core units | Method comparison |
| `spike-pages` | the four spike pages | Throughput, counts |
| `first-pass` | the 78 first-pass pages | Phase gates |

While debugging, outputs stay small by construction: CLI reports summarize (counts, the ten
worst units by a chosen metric, links to `explain` commands), agent packets are capped (D8 §3),
and per-iteration agent budgets bound how much Opus is asked to do (§7.4).

## 9. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D6-1 | Stage barriers versus per-unit dataflow once the corpus grows beyond first-pass chapters | Phase 2 timing |
| OPEN-D6-2 | Co-resident or exclusive GPU mode by default, given the S3 model choice | Spikes S3, S7 |
| OPEN-D6-3 | Default iteration limit and agent budgets that keep debugging output reviewable | Phase 0 practice |
