# Phase 0: orchestration

**Status:** Proposed (2026-10-28). Part of the [phase 0 series](../phase-0_2026-10-28.md), which
owns shared decisions, contracts, the dependency graph and build findings.

Packages P0-O-0, P0-O-1 and P0-O-2 (coordinator §7: O0, O1, O2). The basis is the design as amended
on 2026-10-28: [D6](../../design/D6-orchestration-metrics-policies.md) in full,
[D3 §4](../../design/D3-database.md#4-ops-methods-policies-runs-and-tasks) and
[§8](../../design/D3-database.md#8-runs-snapshots-and-reads),
[D4 §1](../../design/D4-method-catalog.md#1-the-method-contract), [D8 §4](../../design/D8-agent-and-query-interfaces.md#4-cli),
[ADR-0015](../../adr/0015-agent-work-queue.md) and [ADR-0018](../../adr/0018-policy-routed-escalation.md)
(proposed until S4 reports). The mechanisms come from the
[store note](../../design_review/evidence/2026-10-28_library-store/README.md) §3–§5, the
[interfaces note](../../design_review/evidence/2026-10-28_library-interfaces-eval/README.md) §2 and the
[schema-rules note](../../design_review/evidence/2026-10-28_library-schema-rules/README.md) §5. Nothing
is built. Every design statement here is **Proposed** unless it carries another label.

## 1. What this document builds

Orchestration turns a domain pack and a corpus into recorded runs. It builds:

- **the method contract**: the types every method implements, in `core/method.py`, and the
  registry that turns `methods.yaml` into method and configuration rows, resolved per run;
- **project initialization** and the pack-version upsert that `ci run` and `ci ingest` perform
  first;
- **runs** with their recorded reference run and corpus hash;
- **tasks** with reuse by content digest;
- **queueing**: claiming, leases and `attempt` fencing for workers and for the agent, and the agent
  completion primitive with its twin rule;
- **the phase 0 stage graph** and its barriers, including the calls into consolidation at assemble
  and finalize, the measure stage and the call into evaluation;
- **fates**: a recorded fate for every eligible unit, and the one reader of fates;
- **routing and scope**: policies compiled to rule-engine `Chain`s; slices, the run's corpus and its
  scope; the agent barrier; successive `complete` runs over the `phase0-golden` scope, with an
  in-process run driver for tests;
- **commands**: `ci project init`, `ci run` (with `ci run cancel`), `ci status` and `ci tasks`;
- **pack files**: the statistics pack's phase 0 `policies.yaml` and `slices.yaml`, and the skeleton
  of its `methods.yaml`.

**Where it ends:**

- **Method content.** Orchestration never computes what a method computes. It calls `select` and
  `input_digest`, hashes the returned `Digest` into `input_hash` and records `packet_hash`. What a
  digest covers belongs to the method: A1 for M24, A2 for `golden.pass`, ingest and math for M01–M13.
- **Rows it never writes.** Observation and evidence rows are the repository's (P0-F-4), written
  inside orchestration's transactions. Knowledge rows are consolidation's (P0-C-1). Interventions
  are the agent interface's submission tools'. Golden passes are tasks it leases; the golden store
  (sets, units, passes and items) is evaluation's (P0-E-1).
- **Fates versus coverage.** Orchestration records fates and provides their reader. Consolidation
  and queries presents coverage (P0-C-2), and evaluation's `ci promote` checks the same reader.
- **Tools.** It holds no MCP tool. The agent interface's `queue_next`, `release`, `propose_claims`,
  `golden_next` and `write_golden` call its lease and completion primitives.

**Change scenarios** that explain the boundaries (DESIGN §1.3; phase 1 additions):

| Change | Where it lands | What stays unchanged |
|---|---|---|
| A second domain pack | its `methods.yaml`, `policies.yaml`, `slices.yaml` and source profile | The loaders, the registry's reference resolution, the stage runner and fates: no module under `orchestrate/` names a statistics method, metric, slice or page. The toy pack (P0-C-4) is the check |
| The local LLM tier (M10, phase 1) | a new method with `llm` resources and an async `llm` worker kind; the phase 1 graph adds `route` and `escalate` with iterations; budgets produce `skipped(budget)` | Reuse, leases, fencing, twins, fates and the policy loader. M10's digest holds its packet hash like M24's (D4 §1) |
| Encoders and new segment kinds (tables, email threads) | encoder methods and the `encoder` worker (D6 §3.2, §5); new kinds change which segments are annotation units (D1 §3.4) | The propose stage enumerates annotation units through ingest and math's function, so new kinds need no orchestration change |
| Per-unit dataflow instead of stage barriers (OPEN-D6-1, phase 2) | the stage runner only | Tasks, reuse, leases and fates |
| A rule with `or`/`not` conditions | M19 and the schema compilers | Policy conditions are already full rule-engine expressions |

## 2. Contracts

### 2.1 Consumed

| Contract | Owner (design · this series) | Used by |
|---|---|---|
| Settings built once per entry point; the Typer app, group registration and `--json` emission; the shared conftest and per-session database `ci_test_<pid>` | D9 §3, §4, D8 §4 · [foundations](foundations.md) P0-F-1 | every package's commands and tests |
| `canonical_json`, `digest`, `make_key` (the `cfg:` key), the canonical-decimal helper for loaders | D1 §10.1 · P0-F-2a | O0 (`payload_hash`), O1 (config hashes, `input_hash`, `corpus_hash`) |
| Observation payload and operations JSON models (`ops.run.options`, `ops.policy_rule.action`, `trigger_metrics`, `cost`) | D3 §6.2–§6.3 · P0-F-2b (their content follows §3 here) | O0 drafts, O1, O2 |
| Metadata and migration 0001: the queue's partial indexes, `task_cache` without `run` tasks; the views `kb.run_observation`, `kb.run_rendition` and `ops.run_measurement` with the `finished_at` cut; the pool lent to SQLAlchemy; `get_or_create`, `store_rendition`, `upsert_spans`, `write_observations`, `copy_rows`, `insert_returning`; `classify_error` | D3 §3–§8 · P0-F-4 | O1 (every write), the Reader |
| Locators: parse, resolve and refuse, `LocatorIndex`, unit keys, pages from the profile's `root`; `annotation_units(rendition)` | D1 §3.4 · [ingest and math](ingest-and-math.md) P0-I-0, P0-I-1a | O1 (`unit_key`), O2 (slices, scope, the propose stage's candidates) |
| Source profiles: `load_profile`, `root`, `index`, `language`; statement-kind and `claim_bearing` hints in segment attributes | D4 M01, D2 §12.1 · P0-I-1a | O1 (`ci project init`), O2 (unit context) |
| The phase 0 methods as D4 §1 methods: `ingest.html` (M01 with M03), `profile.segments` (M02), `extract.math` (M09), `normalize.formula` (M11), `resolve.symbol_scope` (M13) · `agent.opus` (M24) · `golden.pass` · `validate.rules` (M19) | D4 §1, §3 · P0-I-1b, P0-I-2b · [agent interface](agent-interface.md) P0-A-1, P0-A-2 · [schema and rules](schema-and-rules.md) P0-S-2 | the phase 0 graph and registry (runtime; O tests use stubs) |
| `schema.registry.ensure()`; compiled artifacts by (schema version, compiler, kind); `ci:claim_bearing` per `StatementKind` value from the schema lookup | D2 §7, D3 §3 · P0-S-1, P0-S-1b | O1 (pack upsert, artifact references), O2 (unit context) |
| The rule-language helper `schema/rulelang.py` (typed contexts, `mapping_attribute_lookup=False`, UTC, one context per rule, banned builtins) | D2 §7.4, D6 §7.1; ADR-0018 · P0-S-2 | O2 (policy `Chain`s) |
| `consolidate.run_pass(conn, run_id, pass_, m19_task_id) -> PassReport` (counts, M19 per-rule counts, consumed propose tasks) | D5 §1, §11 · [consolidation and queries](consolidation-and-queries.md) P0-C-1 | O1 (assemble, finalize, measure) |
| `golden_units(project, label)` (a set's unit keys and their hash); `settle_golden_run` finishing a golden run through O1's `finish_run`; `evaluate.score`, a run-level method of the `evaluate` stage | D7 §3.1, §5 · [evaluation and goldens](evaluation-and-goldens.md) P0-E-1, P0-E-2b | O2 (`{golden_set}`), O1 (golden runs, the evaluate stage) |
| Spike evidence | `s6.queue` (claiming, a kill mid-batch, fencing, `LISTEN`/`NOTIFY`), `s6.ddl` (queue indexes, views) · design-spikes S6 | O1 |

### 2.2 Produced

| Contract | Design owner | What this document implements | Consumers |
|---|---|---|---|
| Method-contract types and the registry interface (`core/method.py`) | D4 §1 | §3.1 (P0-O-0) | ingest and math P0-I-1b, P0-I-2b; agent interface P0-A-1, P0-A-2; schema and rules P0-S-2; consolidation P0-C-1 |
| The registry: named configurations, reference resolution, the run's recorded configuration map; the top-level `methods.yaml` sections it loads as data (`aliases:`, `math:`, `binders:`) | D4 §1, D3 §3, D6 §7.1, D2 §12.1 | §3.2 (P0-O-1) | every method; policies; P0-A-2 (pass-C configuration); foundations' label rules (P0-F-2b's `LabelRules`, from `aliases:`), M09 and M13 (`math:`, `binders:`), consolidation and evaluation (`aliases:`, `math:`) |
| Pack-version upsert (schema through S1b, guideline, policy, slices) and project initialization | D8 §4 | §3.3 (P0-O-1) | P0-I-1b (`ci ingest`), P0-C-3, P0-E-1 |
| Runs: creation with `reference_run_id` and `corpus_hash` at insert, kinds, options, transitions, finishing, cancelling, liveness | D3 §4, D6 §2 | §3.4 (P0-O-1) | P0-I-1b (kind `ingest`), P0-E-1 (kind `golden`), P0-A-1 and P0-C-1 (read the reference run), P0-E-2b |
| Task creation with reuse, `packet_hash`, terminal-at-creation fates, `prerequisite_failed` | D6 §2, §4 | §3.5 (P0-O-1) | P0-E-1 (pass A and B tasks), P0-A-2 (pass-C task) |
| Worker claiming, leases, fencing, retries | D6 §3.2, D3 §8 | §3.6 (P0-O-1) | every worker method, through the runner |
| Agent leases with a candidate filter; the completion primitive (held-open outcome, twins, `NOTIFY`, run-row lock) | D6 §3.1, §4; D8 §2.1 | §3.7 (P0-O-1) | P0-A-1 (`queue_next`, `release`, `propose_claims`), P0-A-2 (`golden_next`, `write_golden`) |
| The stage runner and the phase 0 graph; M19 per-rule counts; phase 0 metrics | D6 §2, §6, D3 §5 | §3.8 (P0-O-1) | P0-C-1 (called), P0-E-2b (called) |
| The fate reader | D6 §1, D3 §8 | §3.9 (P0-O-1) | P0-C-2 (coverage), P0-E-2b (`ci promote`), `ci status` |
| Policies | D6 §7; ADR-0018 | §3.10 (P0-O-2) | P0-C-2 (`explain unit`, the "why a method ran" query of D3 §9) |
| Slices, corpus and scope, with the recorded resolution | D6 §8, D2 §12.2 | §3.11 (P0-O-2) | P0-C-2, P0-C-3, P0-C-4, P0-E-2b |
| The agent barrier, the `complete`-run protocol and the in-process run driver | D6 §2, D7 §7 item 5 | §3.12 (P0-O-2) | P0-C-3, P0-C-4, P0-E-2b's golden-expectation run, qualification |
| `ci project init`, `ci run`, `ci run cancel`, `ci status`, `ci tasks` | D8 §4 | §3.13 | the operator, qualification |
| The stateful lifecycle test | D9 §4 | §6 | phase 0 qualification |

## 3. Design of the parts

### 3.1 The method contract (`core/method.py`, P0-O-0)

The objects of D4 §1's block, as amended. The types live in `core` because the methods sit below
`orchestrate` (in `ingest/`, `methods/`, `validate/` and `consolidate/`, D9 §1) and must import them
without importing orchestration.

- **`Method`** is a `Protocol` with D4 §1's attributes and calls, plus `tier`, which
  `ops.method_config.tier` records. `input_digest` returns a **`Digest`**, a named tuple of the
  digest bytes and `packet_hash`.
- **`UnitRef`** (unit type, id, unit key) and **`UnitView`** (the ref, its document and rendition
  where they apply, and the run view).
- **`RunView`**: the run's id, kind, phase, reference run, schema, guideline and policy versions,
  its options, and a **`Reader`**. The reader returns what a method reads, already scoped to the
  run:
  - the run's documents and its rendition of each (`kb.run_rendition`);
  - rendition content: canonical text, segments, sentences, the macro table;
  - the run's effective observations of a rendition by method and kind (`kb.run_observation`);
  - method-written measurements read through reuse (`ops.run_measurement`);
  - compiled artifacts by hash and the guideline body;
  - a read-only connection for method-specific queries, such as A1's known entities from the
    reference run.

  O1 implements the reader over the database. Upstream outputs must be read through reuse and the
  run's rendition selection. One implementation keeps every method from rediscovering those joins,
  and that is the place where a text-only digest once went wrong (P0CL-02).
- **`ObservationDraft`** (kind, rendition or segment, span offsets, payload, score, outcome) and
  **`MeasurementDraft`** (metric, scope, value, detail). **`UnitResult`** holds the ref, an outcome
  (`produced`, `empty` or `failed`, D4 §1 rule 2), the drafts, an error and the cost. For
  `ingest.html` it also holds F2a's `RenditionContent` and the build's `parse_detail`. O1 turns
  drafts into rows: spans through `upsert_spans`, then `write_observations`. So foundations' writers
  take rows, not drafts, and F4 does not depend on O0.
- **`Resources`** (worker kind `cpu`, `encoder`, `llm` or `agent`; batch size; maximum concurrency)
  and **`MethodContext`** (the run view, the reader, the settings a method may read, a logger).
- **Configuration references**, as `Annotated` markers on `Config` fields. They carry D4 §1's
  merge, with named profiles and embedded configurations resolved to their content, and D3 §3's
  artifact references, without the registry naming any section, profile or compiler:
  - `ArtifactRef(compiler, kind)`: resolved to the hash of the run's schema version's artifact
    (D4 §1 as amended);
  - `ConfigRef(method)`: another method's named configuration, embedded as its resolved params, the
    way `ingest.html` names `segment.sentences/<name>`;
  - `SourceProfileRef`: a profile name, resolved to the parsed `sources/<name>.yaml` through ingest
    and math's loader;
  - `PackSection(name)`: a top-level section of `methods.yaml`, such as `math`, `binders` or
    `aliases`. D2 §12.1 keeps these sections outside `configs:`, while D4 §1 places them in the
    configuration of the methods that read them; the marker connects the two.
- **`payload_hash(payload)`**: SHA-256 of the canonical JSON of an observation payload. This is the
  one form in which digests cite upstream observations (coordinator decision 15). Floats in a payload
  (observation `score`, encoder confidences) are converted to their canonical decimal with
  `decimal_of_float` before hashing, as configuration loaders do; canonical JSON itself still refuses
  floats, so keys never see one (coordinator, 2026-10-28, from P0-F-2b's payload models).
- **`Registry`** and **`ResolvedConfig`** (method, configuration name, `Config` instance, canonical
  params, config hash, `ops.method_config` id): how A2, E1 and the MCP server name a configuration.

### 3.2 The registry and named configurations (P0-O-1)

**Composition.** The generic modules of `orchestrate/` never import a method. The phase 0 method
list and graph live in `orchestrate/phase0.py`, which may import methods because `orchestrate` sits
above them (D9 §1). Each method's package adds one line there: P0-I-1b, P0-I-2b, P0-S-2
(`validate.rules`), P0-C-1 (`consolidate.claims`, the pass task's method), P0-A-1, P0-A-2 and
P0-E-2b (`evaluate.score`). `agent.opus` and `golden.pass` live in `methods/` for that reason
(agent interface §8). A method that must live above `orchestrate` cannot be listed. `evaluate.score`
is one, since `evaluate` sits above `orchestrate`, so its method object is registered by the entry
point (`cli`) into the same registry. Tests build their own registries from stubs.

**Loading `methods.yaml`.** PyYAML `safe_load` reads the file into a model with `version`, the
top-level sections and `configs: {method: {name: params}}`. Validation:

- a configuration of an unregistered method is refused;
- unknown params fail the method's `Config` (`extra="forbid"`);
- a float parameter becomes its canonical decimal before hashing, through F2a's loader helper
  (D1 §10.1).

**Resolution per run.** Every named configuration of every registered method is resolved when the
run is created:

1. Take the method's defaults, overlay the named params, and resolve the references against the
   run's schema version, the current `methods.yaml` and `sources/`.
2. Hash the canonical params to the `cfg:` key, and get-or-create the `ops.method` and
   `ops.method_config` rows (D3 §4).
3. Record the map from `<method>/<name>` to config hash in `ops.run.options.configs` at insert.

Every later lookup for the run reads that map: a policy action's name (D6 §7.1 as amended), A2
creating a pass-C task days after its golden run was created, and the run option
`method_configs` (§3.4). Editing `methods.yaml` therefore never changes what an existing run
resolves. This is "resolved per run against the run's method configurations" made concrete.

### 3.3 Project initialization and pack versions (P0-O-1)

**`ci project init --domain NAME --corpus PATH [--name NAME]`** works as follows:

1. Create `meta.project`; the name defaults to the domain.
2. Read the source profiles that the pack's `ingest.html` configurations name, through
   `load_profile`.
3. Register one document per row of each profile's `index`, through `get_or_create`. The document
   key uses the project name (D1 §10.1). `meta` takes the index's attribute columns (`first_pass`,
   chapter, and so on). The page is `source_uri` minus the profile's `root`, and two documents with
   the same page are refused.
4. Run the pack-version upsert.

It is idempotent: a rerun adds only new documents and versions. New bytes at an existing path are a
new document (D1 §3.1), and a corpus resolves each page to its latest registered document.

**The pack-version upsert** (`ensure_pack_versions`) runs first in every `ci run` and `ci ingest`
(D8 §4), so editing a pack file needs no separate step:

- the schema version and its artifacts, through `schema.registry.ensure()`;
- the guideline version: `guideline.md` by content hash, its label from the file's version line,
  its parent the domain's latest version, its schema version the one just ensured;
- the policy version (§3.10);
- the slices, stored as declared (unexpanded) and upserted by name (§3.11).

Configurations are not upserted here. They are resolved per run (§3.2), because their hashes depend
on the run's schema version.

### 3.4 Runs (P0-O-1)

**Creation.** `create_run` inserts the run in one `INSERT … SELECT` that reads
`meta.project.promoted_run_id` into `reference_run_id` in the same statement, so no promotion falls
between the read and the insert (D3 §4, "recorded, not looked up"). The run store has no function
that writes `reference_run_id` afterwards. Status changes are conditional updates
(`WHERE status = :from`), and an illegal transition raises.

The options are a frozen model stored as canonical JSON:

- `agent_mode`: `wait` is the default for kind `slice`, `complete` for every other kind;
- `corpus`: a slice name, default `first-pass`, or an explicit document list for `ci ingest PATH…`;
  the expanded document keys are recorded;
- `scope`: the slice name with its expanded entries and their hash (§3.11);
- `fresh`: methods whose tasks skip reuse;
- `configs`: the resolved configuration map (§3.2);
- `method_configs`: method → configuration name, overriding a policy action's choice for that run.
  The golden-expectation run names `agent.opus/expectation` this way. Its distinct config hash keeps
  its tasks from settling with, or being reused by, live agent tasks.

`agent_reuse` and the GPU mode are refused in phase 0: the guideline is frozen (coordinator decision
9) and no method uses a GPU. `corpus_hash` is D3 §4's, computed at insert. `code_commit` is
`git rev-parse HEAD`, with a marker when the tree is dirty.

**Kinds:**

- `ingest`: created by `ci ingest`; the ingest stage only.
- `slice`: a debug slice run, never promoted (D6 §8).
- `full`.
- `golden`: task-only. P0-E-1's `ci golden create` creates it through this API with
  `parent_run_id`, along with its pass A and B tasks (D3 §8). It has no stage graph and no
  orchestrator. Evaluation's `settle_golden_run` finishes it through `finish_run` once every unit
  is adjudicated.
- `experiment` and `rescore` are refused in phase 0.

**Finishing** stamps `finished_at = clock_timestamp()` while holding the run row's update lock
(§3.7, §3.8). The fate rule depends on that stamp.

**Liveness** (D6 §2, orphaned runs). `ci run` opens one dedicated autocommit connection outside the
pool for the run's life. On it, it takes `pg_advisory_lock(<namespace>, run_id)`, and in `wait`
mode it `LISTEN`s there too (store note §4: one listener connection outside any pool). A
session-level advisory lock is released when its session ends, even on an ungraceful disconnect.

`ci status` reports a run in `running`, `awaiting_agent` or `consolidating` as orphaned when
`pg_locks` shows no such lock (`locktype = 'advisory'`, `classid` the namespace, `objid` the run id,
`objsubid = 2`). This was checked against the PostgreSQL 18 documentation (§13.3.5 and the
`pg_locks` view), *Interface-checked* (2026-10-28).

`ci run cancel RUN` sets the run and its `pending`, `running` and `awaiting_agent` tasks
`cancelled` (reason `run_cancelled`). A live orchestrator sees the status at its next re-query and
exits. The store note rejected advisory locks as task leases, because they cannot express a
30-minute agent lease and leave no queryable state. Here the lock marks one process's liveness, and
release at disconnect is exactly the property wanted.

### 3.5 Tasks, digests and reuse (P0-O-1)

**Creation.** `create_tasks(conn, run, stage, resolved_config, units, *, trigger=None)` works per
unit:

1. Take the `Digest` from `method.input_digest(unit_view, cfg)`.
2. Compute `input_hash` by D6 §4's formula over the method name, version, config hash and the
   digest bytes. Record `packet_hash` from the digest.
3. Insert in batches with one `INSERT … SELECT … FROM unnest(…) LEFT JOIN LATERAL (…)` over
   `task_cache` (store note §4). A match gives `reused`, with `reused_task_id` and `finished_at`;
   otherwise the task gets its initial status: `pending`, or `awaiting_agent` for agent-tier
   configurations.

There is no lateral lookup for tasks of unit type `run`, which are never reused (D6 §4), or for a
method named in `options.fresh`. `unit_key` is the unit key for annotation units and the document
key for document and rendition tasks, so it stays stable across renditions (D3 §4). Digests are
computed at creation because the task's fate is known then, and the packet is fixed then
(D4 §4.1). A reused agent task therefore never enters the queue.

**Fates written at creation:**

- **`skipped`** fates are inserted with their `reason`, `finished_at` and the sentinel
  `input_hash` `skip:<reason>`, with no digest computed. An out-of-scope unit's packet is never
  assembled. A sentinel can never match: `task_cache` covers only `done` and `empty`, and twins only
  `awaiting_agent`.
- **`prerequisite_failed`** is decided per unit from the graph's declared upstream methods (D6 §2,
  "Upstream methods"). A unit whose upstream task for its rendition `failed` gets this skip instead
  of a digest.
- After a transaction that created agent tasks commits, the orchestrator settles their twins
  (§3.7).

### 3.6 Claiming, leases and fencing for workers (P0-O-1)

**The claim** is the store note §4 statement: one `UPDATE … FROM (SELECT … FOR UPDATE SKIP LOCKED
LIMIT n)` over `pending` or lease-expired `running` tasks of one (run, stage, method
configuration). It increments `attempt` and sets a 5-minute lease. The `task_pending` and
`task_lease` indexes serve it. The claim commits at once, and the method runs with no transaction
open.

**The terminal write uses one transaction per task.** The order is store note §3's:

1. the fencing `UPDATE` on `(id, attempt, status = 'running')`; zero rows raises `LeaseLost` and the
   transaction rolls back;
2. the task's rows: spans, observations (binary COPY with `Copy.set_types`), measurements with
   `task_id`, and for `ingest.html` `store_rendition`;
3. the outcome, `cost` and `finished_at`.

A transaction per task rather than per claimed batch means a lost lease or a bad row rolls back one
task. Phase 0's tasks are per document or per rendition, so the extra commits number in the tens.
Batching writes waits for phase 1's per-segment encoder tasks.

**Renewal and retry:**

- A heartbeat thread in each worker renews its held tasks about every minute, on the pool's second
  connection, with the store note's statement.
- Transient failures, classified by `classify_error` (40001, 40P01, a lost connection), take the
  conditional retry write: `pending` while `attempt < 3`, else `failed`.
- A `failed` unit result, or any other exception, is written `failed` at once.
- A `UniqueViolation` on `(task_id, ordinal)` is a fencing defect and fails loudly.

**Workers.** Phase 0 has only the `cpu` kind (D6 §3.2). `ci run` starts single-threaded worker
processes. Python 3.14's Linux default start method is `forkserver`, so nothing is inherited, and
each worker builds its registry and settings in its initializer and opens its own pool (`min 1`,
`max 2`: work plus heartbeat; store note §5). The method runs on the process's main thread, which
the grammar's `setitimer` timeout needs (D4 M11). `workers=0` runs the same loop inline on the
orchestrator's main thread, for tests and small slices.

**Evidence.** The claiming statement and fencing are source-read (store note §4). `s6.queue` gives
the concurrency evidence, and the statement stays provisional until that record exists.

### 3.7 Agent leases, the completion primitive and twins (P0-O-1)

**Leasing.** `lease_agent_tasks(conn, *, session_ref, method_configs, run=None, where=None,
max_units=1)` runs in one transaction:

1. Settle twins among the candidates: an `awaiting_agent` task whose `(method_config_id,
   input_hash)` twin is `done` or `empty` becomes `reused`.
2. Claim the head task with the store note §4 statement on `status = 'awaiting_agent' AND
   (lease_until IS NULL OR lease_until < now())`. Exclude any task whose twin holds an unexpired
   lease, plus whatever the caller's `where` clause excludes. `golden_next` uses `where` to skip
   units whose earlier pass came from the same server instance (agent interface §3.7).
3. Set `claimed_by = 'agent:<session_ref>'`, a 30-minute `lease_until` and `attempt + 1`, leaving
   the status at `awaiting_agent`.
4. Up to `max_units`, lock same-rendition siblings with a second `SKIP LOCKED` query. `max_units`
   stays 1 until A3 decides.

With no `run` given, the newest run that has leasable tasks of those configurations is used. The
`task_agent` index serves the claim. `renew_agent_lease` and `release` are fenced on `attempt`;
release clears the lease and keeps the status.

**The completion primitive.** `complete_agent_task(conn, task_id, attempt, session_ref, *, clean,
outcome, first_result)` runs in the caller's transaction and is the only path that completes an
agent task (D6 §3.1). A1's `propose_claims` and A2's `write_golden` call it before writing their
observations and intervention.

- **Held open.** When `clean` is false (errors, unlocated quotes or warnings) and the task holds no
  earlier result in `ops.task.error`, it is a first imperfect submission. The primitive writes
  `first_result` into `error` and renews the lease, both fenced on `(id, attempt, status =
  'awaiting_agent')`. It returns `held`. The caller writes nothing else, and no run lock is needed,
  because no status changes.
- **Completed.** A clean submission, or a second one, takes these steps:
  1. Lock the task's run row `FOR SHARE`.
  2. Run the fenced update to `outcome` with `finished_at = clock_timestamp()`. Zero rows raises
     `TaskNotOpen`, with the reason read from the row: settled by a twin, cancelled, or leased
     again. The caller rolls back and says so.
  3. On `done` or `empty`, settle the twins. Lock `FOR SHARE`, in id order, the rows of the runs
     that own `awaiting_agent` tasks with the same `(method_config_id, input_hash)`. Then set those
     tasks `reused` pointing at this one, with `finished_at = clock_timestamp()` and the lease
     cleared. A `failed` outcome settles nothing, because failed tasks are never reused (D6 §4).
  4. Send `pg_notify('cs_agent_task_done', <run id>)`. It is delivered only at commit (store note
     §4), and the payload is informational.

**Why the share locks and `clock_timestamp()`.** A run's final transaction holds its row's update
lock while it reads the pool and stamps `finished_at` (§3.8). A completion's transaction may have
begun long before it reaches the primitive, so `now()` could predate a pass whose read it missed.
With the share lock taken first and the stamp taken after it, every completion falls on one side:

- it commits before the final pass reads, and counts and is consolidated; or
- it waits for the run to finish, is stamped later, and counts as unresolved for that run.

Twin settlement locks every run it writes to for the same reason. A twin in a run that is in its
final transaction waits for that transaction. Locks are taken in id order and the final transaction
locks only its own run, so no cycle forms. The cost is that a submission to a run's task waits while
that run finalizes, which is seconds at phase 0 volume. D6 §3.1 states the share lock on the
completing task's run. The locks on the twins' runs and the `clock_timestamp()` stamps are this
document's realization of it.

**Twins at creation and lease.** Under Read Committed, a run's reuse insert and a concurrent
completion can miss each other. The insert's lateral lookup runs before the completion commits, and
the completion's twin update cannot see the uncommitted insert. That leaves an open task whose
result already exists. Settling after creation commits, and again before each lease, closes the gap,
so no packet is served after its result exists. Both settle points take the same share locks and
stamps.

### 3.8 The stage runner (P0-O-1)

**The phase 0 graph** (D6 §2, phase 0) is data in `orchestrate/phase0.py`. A stage is an ordered
list of steps, and a step names a configuration, its unit source (the method's `select`, or a
policy chain) and its upstream methods:

| Stage | Steps | Upstream |
|---|---|---|
| `ingest` | `ingest.html/default` (M01 with M03 as a step of its task); then `profile.segments/default` (M02) | M02: M01 |
| `normalize` | `extract.math/default` (M09) and `normalize.formula/default` (M11), independent | M01 |
| `scope` | `resolve.symbol_scope/default` (M13) | M09, M11 |
| `propose` | the `propose` chain (§3.10) | M24: M01, M13 |
| `assemble` | one consolidation pass | — |
| `finalize` | one consolidation pass with M19, then measure, evaluate and finish | — |

A run of kind `ingest` has only the `ingest` stage. Scope and slice locators resolve after `ingest`,
which selects the run's renditions (§3.11).

**Barriers.** A step is complete when none of its tasks is `pending` or `running`. Open agent tasks
are the agent barrier's business (§3.12). A `failed` task in `ingest` fails the run (D6 §2). In
later stages, downstream units get `prerequisite_failed`. Run statuses follow D6 §2: `running`
through `assemble`, then `consolidating` (committed before the final transaction begins), then
`finished`.

**Consolidation passes.** The orchestrator creates each pass's tasks itself, `running`, with
`claimed_by = 'orchestrator:<pid>'` and attempt 1, and commits them:

- the pass task (`consolidate.claims`, unit `run`);
- at finalize, also the run-level M19 task (`validate.rules`, unit `run`).

At `assemble`, one transaction calls `consolidate.run_pass(conn, run, 'assemble', None)` and writes
the pass task's fenced terminal status.

At `finalize`, **the final transaction** does the following:

1. Lock the run row `FOR NO KEY UPDATE`. That conflicts with the completions' `FOR SHARE`, but not
   with the `FOR KEY SHARE` taken by the pass's own foreign-key inserts (PostgreSQL 18
   documentation §13.3.2, Table 13.3, *Interface-checked* 2026-10-28).
2. Stamp both tasks' `started_at = clock_timestamp()`.
3. Call `consolidate.run_pass(conn, run, 'finalize', m19_task)`.
4. Write the M19 per-rule counts from the `PassReport` as `ops.measurement` rows: metric
   `rules.evaluated`, scope type `rule`, scope key the rule id, `task_id` the M19 task (D3 §5).
5. Run the measure stage.
6. Run the evaluate stage's `evaluate.score` task inside a savepoint. It is evaluation's run-level
   method, created with the pass tasks and never reused. A failure there is rolled back to the
   savepoint, the task is written `failed` with its error, and the run is scored later with
   `ci eval RUN` (D8 §4). An evaluation defect therefore never discards a consolidated run.
7. Write the tasks' terminal status, fenced, then the run's `finished` status with
   `finished_at = clock_timestamp()`.
8. Commit.

D6 §3.1's rule follows: the final pass sets `finished_at` in the transaction that read the pool.
Consolidation runs on the orchestrator's main thread, where C1 parses claim values once per pass.

**Failure.** An exception before step 7 rolls the transaction back. A second transaction then writes
the pass tasks `failed` with the error and the run `failed` (a consolidation invariant violation,
D6 §2), and the run has no knowledge rows.

**Measure** writes the phase 0 subset of D6 §6 as run metrics (no `task_id`):

- `unit.claims`;
- `run.status.<status>` per predicate;
- `run.conflicts`;
- `method.empty_rate` and `method.failed_rate`, over tasks run, not reused;
- `math.parse_rate` per run and page, from M11's values;
- `cost.agent_packets`: agent tasks this run created open, neither reused nor skipped.

Left out until phase 1: the encoder, confidence, verification and judgment metrics,
`unit.unresolved_symbols` (it feeds escalation) and `intervention.share` (it is 1 with one
proposer). The unlocated-quote and rule-warning rates are evaluation's promotion readings, defined
once there and not recomputed here.

**Evaluate** runs `evaluate.score` (evaluation and goldens P0-E-2b) over the golden units in the
run's scope. Its outcome is `empty` when no adjudicated unit is in scope.

### 3.9 Fates and their reader (P0-O-1)

**Recording.** Every eligible unit gets a task (D6 §1):

- base steps create one for each unit their `select` returns;
- the propose stage creates a task, or a `skipped(scope)` or `skipped(limit)`, for every candidate
  that a chain entry matches (§3.10); a candidate no entry matches is not eligible and has none;
- `prerequisite_failed` skips as in §3.5.

Terminal-at-creation tasks (`reused`, `skipped`) carry `finished_at` from creation (D3 §4).

**The rule** is D6 §1's and D3 §8's: a finished run's fates are its tasks as of
`ops.run.finished_at`. A task whose `finished_at` is later, or null, counts as unresolved for that
run. §3.7 and §3.8 make the cut exact: `finished_at` is stamped in the transaction that read the
pool, under a lock that every agent-task completion must pass.

**One definition.** The cut is the one comparison `t.finished_at <= r.finished_at`. It appears in
the coverage query of D3 §9, `kb.run_observation` and `ops.run_measurement` (P0-F-4's views), and in
the reader here, `fates(conn, run, *, stage='propose', documents=None, unit_keys=None)`. The reader
returns rows of unit key, document, fate and reason, and `unresolved(conn, run)` counts the open
ones. C2's coverage counts these rows, and E2b's `ci promote` requires `unresolved = 0`. For a run
that has not finished, the reader gives the current statuses, which `ci status` shows as progress.

### 3.10 Policies (P0-O-2)

**Loading.** `policies.yaml` goes through PyYAML `safe_load` into a frozen model (`version`,
optional `budgets`, `thresholds` and `priors`, `chains`):

- An action names `<method>/<name>` (D6 §7.1, D3 §6.3 as amended).
- Loading refuses an action whose method the registry does not hold, or whose configuration
  `methods.yaml` lacks (D6 §7.1, "Registered methods only").
- `ops.policy_version` is keyed by the content hash of the parsed file's canonical JSON, with one
  `ops.policy_rule` row per entry (D6 §7.1 "Rows").

**Compilation.** Each chain becomes a rule-engine 5.1 `Chain([(when, entry), …], context=…,
default_value=None)`, built with schema and rules' `schema/rulelang.py`, so routing and M19 share
one expression discipline (ADR-0018). A type error raises at construction, so loading fails naming
the entry (schema-rules note §5, *Tested* by probe P8, 2026-10-28). The entry value carries the rule
key, because `ChainEntry` has no id. `then: continue` evaluates `chain[i+1:]` after
`Chain.index(entry)`, with the same context (rule-engine overview §2.1).

**The unit context** (D6 §7.2) is typed per schema version:

- `phase` and `iteration`;
- `unit`, an OBJECT:
  - `kind`;
  - `statement_kind`: the hint M01 records on the unit's segment from the profile's block and
    section hints;
  - `claim_bearing`: the hint when the profile states it, otherwise the schema's `ci:claim_bearing`
    for the statement kind;
  - the unit- and segment-scope metric names of D6 §6, as nullable floats read through
    `ops.run_measurement`;
- FUNCTIONs `ran(m)` and `outcome(m)` over the run's tasks on the unit;
- `budget`, an OBJECT.

`target`, `judged_by` and `judgment` are typed but empty until phase 1. A metric with no value is
null, so a condition discharges it with `??`.

**Evaluation in the propose stage.** The candidates are `annotation_units(rendition)` (ingest and
math) for each of the run's renditions. For each candidate, `Chain.find` gives the first matching
entry. The entry's configuration comes from the run's map (§3.2). The run option `method_configs`
replaces the entry's configuration name for its method.

- **In scope:** a task, `awaiting_agent` for the agent tier, with `trigger_rule_id` and
  `trigger_metrics`.
- **Out of scope:** `skipped(scope)`.
- **Beyond the entry's `limit`** in the iteration: `skipped(limit)`.
- **No match:** no task.

Budgets bound escalation, not propose (D6 §7.4), so phase 0 creates no `skipped(budget)`. `route`
and its chains arrive in phase 1, with the same loader and compiler.

**The statistics pack's phase 0 `policies.yaml`** holds its `version` and the `propose` chain's one
entry, `propose.phase0.agent_all` (D6 §7.1, §7.5). Budgets, thresholds and priors join with the
methods that read them.

### 3.11 Slices, corpus and scope (P0-O-2)

**Selectors.** `slices.yaml` uses D2 §12.2's forms:

- a locator string (D1 §3.4);
- `{include: <slice>}`;
- `{pages: [<slice>, …]}`: every unit of the pages the named slices' selections lie on;
- `{index: <column>}`: the pages the corpus index marks in that column;
- `{golden_set: <label>}`: each unit of that set, by its unit locator.

Includes expand recursively, and a cycle or an unknown slice fails loading. `ops.debug_slice` stores
the slice as declared.

**At run creation** the `corpus` and `scope` slices are expanded into document keys and a sorted
list of page and unit locators. `{golden_set}` is read from evaluation's set as it stands. The
expansion and its hash go into `ops.run.options` in the insert (D6 §8 as amended), so a later edit
of `slices.yaml`, or a grown golden set, leaves a past run's recorded scope unchanged.

**After the ingest stage**, each recorded locator resolves through ingest and math's resolver on
the run's rendition of its page, using one `LocatorIndex` per rendition. A refusal fails the run's
start with the candidates listed (D6 §8, D1 §3.4). Refusals are: no segment; several segments
without an ordinal; a kind other than page, unit or paragraph.

**What counts as in scope:**

- the annotation units of every page entry;
- the units that unit and paragraph locators select.

A slice run (kind `slice`) ingests the slice's documents. Its units outside the slice get
`skipped(scope)`, so its coverage of its pages is explicit (D6 §8).

**`domains/statistics/slices.yaml`** is D2 §12.2's file: `trace`, `core12`, `spike-pages`,
`phase0-golden` (`{pages: [core12]}` and `{golden_set: p0}`: the four spike pages whole plus every
unit of dev set `p0`, about 234 packets) and `first-pass`.

**Guard.** In phase 0, `ci run` refuses a `full` run with no scope. The phase 0 policy routes every
claim-bearing unit to the agent, so an unscoped run would be the workload P0CL-09 ruled out.

### 3.12 The agent barrier and the `complete`-run protocol (P0-O-2)

**The barrier** applies after the propose step leaves open agent tasks:

- **`wait`.** The status becomes `awaiting_agent`, and the run waits on its dedicated connection:
  1. `LISTEN cs_agent_task_done`;
  2. count the run's open propose tasks;
  3. loop on `conn.notifies(timeout=…, stop_after=1)`, re-counting and re-reading the run's status
     after every wake or timeout;
  4. `LISTEN` again after a reconnect.

  At zero open tasks the run returns to `running`. This follows the store note §4 and interfaces
  note §2, with psycopg's `notifies(*, timeout, stop_after)` signature verified against 3.3.6
  (*Interface-checked* there, 2026-10-28).
- **`complete`.** The run continues at once. Its open tasks stay in the queue and read as
  unresolved for it once it finishes (§3.9).

**The protocol** (D6 §2, D7 §7 item 5): `ci run --scope phase0-golden --agent-mode complete`,
repeated. In each run:

- every finished task is reused: base stages by content digest, and agent tasks whose packet was
  completed before the run was created;
- the still-open agent tasks are twins of earlier runs' open tasks, so a submission to either
  settles both;
- the run finishes as a coherent snapshot.

`ci run` ends by printing the unresolved count, and `ci status` lists it per run. The operator
promotes the first run with zero, through evaluation's `ci promote`.

**Why it converges.** A packet depends only on recorded inputs (D4 §4.1). During the sequence
nothing changes those inputs: base stages are reused, the configurations are the same, and no run
is promoted before convergence, so every run records the same reference run (null at bootstrap)
and serves the same known-entity section. Each packet is asked once and reused by every later run.
A promotion mid-sequence would change the reference run and with it every packet. So the protocol
promotes only at convergence.

The qualification order (coordinator §10) relies on the same reuse. The `spike-pages` run (a
`complete` run of kind `full`, scope `spike-pages`, corpus `first-pass`) is the golden source run.
Its packets are reused by the `phase0-golden` runs, whose scope contains its pages.

**The in-process run driver** (`orchestrate.testing.run_to_completion`) runs a slice or scope to
completion on the caller's settings and registry, with `workers=0`, stub or real methods, and the
agent mode given. It returns the finished run. C3, C4 and E2b's golden-expectation run use it. It
is a product module because evaluation drives it outside pytest.

`wait` stays for short slice runs (D6 §2). A `wait` run whose orchestrator dies is reported
orphaned, cancelled and started again, reusing what finished (§3.4).

### 3.13 Commands (P0-O-1, P0-O-2)

The groups register in foundations' Typer app. Every command's result model is what `--json`
emits (D8 §4):

- `ci project init --domain NAME --corpus PATH [--name NAME]` (§3.3).
- `ci run [--slice NAME | --scope NAME] [--corpus SLICE] [--phase N] [--agent-mode wait|complete]
  [--fresh METHOD]…`, and `ci run cancel RUN`. The latter is a subcommand of a `run` group whose
  callback starts a run when no subcommand is given (Typer `invoke_without_command=True` with
  `ctx.invoked_subcommand`; Typer documentation, *Interface-checked* 2026-10-28). `--slice` and
  `--scope` are P0-O-2's; P0-O-1's `ci run` runs over an explicit corpus.
- `ci status [RUN]`: for each stage, task counts by status and reason; unresolved agent tasks; any
  orphaned run; the settings it resolved (D9 §3).
- `ci tasks [RUN] [--status S] [--method M]`: a bounded listing (unit key, configuration name,
  status, reason, rule key, cost), with counts beyond the bound (D6 §8).

### 3.14 Execution fit and task counts

The workload premise is a phase 0 run over the 78 first-pass pages (about 2,500 annotation units,
D3 §11), with a scope of about 234 agent packets, one operator and one machine.

**Task rows per run** (P0CL-13's closure check, stated qualitatively):

- **Ingest:** two per page (M01 with M03; M02).
- **Normalize:** two per rendition (M09, M11).
- **Scope:** one per rendition (M13).
- **Propose:** one fate per eligible unit. That is a few thousand rows, about 234 of them agent
  tasks and the rest `skipped(scope)`, which are never digested.
- **Passes:** one task at `assemble`; at `finalize`, the pass, M19 and `evaluate.score`.

That is on the order of 3,000 rows. The roughly 400 per-document and per-rendition tasks do real
work in the first run and are reused by every later run. With per-span M09/M11 tasks and per-claim
M19 tasks, the count would have been tens of thousands per run (P0CL-13). The task machinery is
now small beside the work it records.

**Repeated runs** of the sequence cost one reuse insert per step, the propose evaluation and the two
passes. Observations are never copied (`kb.run_observation` resolves them).

**Contention.** One session, plus a few golden subagents, leases from a small partial index with
`SKIP LOCKED`. The run-row share lock delays a submission only while that submission's run, or a
twin's run, is in its final transaction.

**Growth.** Rows grow with runs × eligible units, mostly through skipped fates. Deleting old runs'
materialized rows keeps their tasks (D3 §8). If skipped rows ever mattered, a per-run count could
stand in for units outside scope; nothing at this scale calls for it.

None of these figures is measured.

### 3.15 Failure behaviour

| Failure | Behaviour |
|---|---|
| A worker process dies mid-task | Its lease expires after 5 minutes. The next claim takes the task with a new `attempt`, and the dead worker's late write matches no row |
| Transient database error in a write | Retried while `attempt < 3` |
| A method fails | `failed`, not retried. Downstream units are `skipped(prerequisite_failed)`; in `ingest` the run fails |
| A consolidation pass raises | Rolled back; the pass tasks are written `failed` and the run `failed` |
| Evaluation raises in the final transaction | Rolled back to its savepoint and noted; the run finishes; `ci eval RUN` scores it later |
| The orchestrator dies | Its advisory lock is released, `ci status` reports the run orphaned, `ci run cancel` cancels it, and a new run reuses finished tasks |
| A notification is lost | The timeout re-query finds the change |
| A submission to a task settled by a twin, cancelled or leased again | Fenced out with `TaskNotOpen` and its reason; the caller rolls back |
| A reuse insert passes a concurrent completion | Twins settled after creation and before each lease |
| A completion during a run's final transaction | Waits on the share lock and counts as unresolved for that run |
| A slice locator is refused | The run's start fails with the candidates listed |
| A policy type error or an unregistered method | Loading fails, naming the entry |
| Invalid configuration params | Run creation fails, naming method, configuration and field |
| A promotion during a run | Nothing the run computes changes: the reference run was recorded at insert |

## 4. Ports

No spike module is ported. S6's queue harness (step 7b, record `s6.queue`) is evidence for the
statements adopted from the store note, and it stays in the spike folder (coordinator §13). D9 §7
lists the old repository's `runs/domain_laws.py` as a source of routing conditions. Phase 0's one
propose entry needs none of it, so mining it waits for phase 1's escalation chains.

## 5. Packages

| Package | Scope | Prerequisites | Acceptance | Revealing failure case |
|---|---|---|---|---|
| P0-O-0 | `core/method.py`: protocol, views, `Reader` protocol, drafts, results, resources, context, `Digest`, configuration references, `payload_hash`, registry interface (§3.1) | P0-F-2b (with P0-F-2a) | Stub methods of each unit type check against the protocol under pyrefly. A `Config`'s references are found by introspection. `payload_hash` is equal across key order and NFC variants and refuses a float. A non-packet method's `Digest` has no packet hash | A payload read back from JSONB, keys reordered by PostgreSQL, must hash as it did when written; a hash over `jsonb::text` would move every downstream digest |
| P0-O-1 | Registry and `methods.yaml` loader; pack-version upsert; `ci project init`; runs, options, liveness and `ci run cancel`; tasks and reuse; worker claiming, leases, fencing and retries; agent leases, the completion primitive and twins; the stage runner with the phase 0 graph, the passes, M19 counts, measure and the evaluate call; fates and their reader; `ci run` over an explicit corpus, `ci status`, `ci tasks`; the stateful test (§3.2–§3.9, §3.13) | P0-F-4, P0-S-1b, P0-O-0, P0-I-1a (`load_profile` for `ci project init`); `s6.queue` before the claiming statement is final | See "P0-O-1 acceptance" below | `--fresh` on the M09 stub with identical output must leave the M13 stub's and the agent stub's tasks `reused`; a digest carrying upstream task ids re-creates every downstream task, the agent's included (P0CL-02) |
| P0-O-2 | Policies; slices, corpus and scope with the recorded resolution; `ci run --slice/--scope/--corpus/--agent-mode`; the agent barrier; the `complete`-run protocol and its convergence test; the in-process run driver; `domains/statistics/policies.yaml` and `slices.yaml` (§3.10–§3.12) | P0-O-1, P0-S-2 (`rulelang`), P0-E-1 (golden set by label), P0-I-0, P0-I-1a (`annotation_units`) | See "P0-O-2 acceptance" below | A unit that the propose chain matches outside the scope must get `skipped(scope)`. A chain evaluated only over in-scope units leaves it without a fate, and coverage of its page reads as complete (P0CL-11) |

**P0-O-1 acceptance** (the table row's checks):

- `ci project init` on a test pack over fixture pages registers documents with index attributes and
  pages, the schema version through `ensure()`, the guideline and the slices; a rerun adds no row.
- With stub methods for every phase 0 base step, and C1's `run_pass` or a stub, a `full` run goes
  through every stage to `finished`, with one task per document or rendition and method, one pass
  task at `assemble`, and the pass, M19 and evaluate tasks at `finalize`.
- A second run reuses every task except those of unit `run`. A content-identical new build reuses
  every rendition-level task.
- `reference_run_id` equals the pointer at insert, and moving the pointer during the run changes
  nothing.
- The completion primitive:
  - holds a first unclean submission and completes the second;
  - settles twins in another run, never from `failed`;
  - refuses a late submission to a twin-settled task;
  - after the two-connection race, leaves no open task with a finished twin.
- A completion blocked by a run's final transaction reads as unresolved for that run; one that
  committed first reads as resolved and is in `kb.run_observation`.
- A failing pass leaves the run `failed` with no knowledge rows.
- A killed `ci run` is reported orphaned and is cancelled.
- The stateful test passes.

**P0-O-2 acceptance** (the table row's checks):

- The statistics phase 0 policy compiles. A type error in a `when`, or an unregistered method,
  fails loading and names the entry. `continue` evaluates the remainder.
- A `trace` slice run with a stub agent method creates `awaiting_agent` tasks for the five trace
  units, each with its rule and trigger values, and `skipped(scope)` for the other units of those
  pages.
- A run scoped to `phase0-golden` records its expansion and hash at insert and skips every other
  eligible unit. Its recorded scope is unchanged after a `slices.yaml` edit or a grown set, and a
  refused locator fails its start naming candidates.
- A `wait` run is woken by a completion from another connection and catches a completion committed
  while it was not listening.
- Three `complete` runs, with completions interleaved across them, converge to zero unresolved. No
  `input_hash` is completed twice, and two completion orders give the same converged task set and
  packet hashes.
- Phase 0 refuses an unscoped `full` run.

**P0-O-0.** Mechanisms: `typing.Protocol`, `Annotated` markers, frozen Pydantic models; F2a's
canonical JSON. Evidence: none.

**P0-O-1.** Mechanisms:

- the claiming `UPDATE … FROM (SELECT … FOR UPDATE SKIP LOCKED LIMIT n)` with the expired-lease
  branch, `attempt` fencing, the renewal and retry statements, and the reuse `INSERT … SELECT …
  LEFT JOIN LATERAL` over `task_cache` (store note §4);
- binary COPY through F4 inside the fenced transaction (store note §3);
- one pool per process plus a dedicated autocommit connection holding a session advisory lock
  (store note §5; PostgreSQL 18 §13.3.5);
- `FOR SHARE` and `FOR NO KEY UPDATE` on the run row, with `clock_timestamp()` stamps (PostgreSQL 18
  §13.3.2);
- `pg_notify` inside the completion transaction;
- `forkserver` worker processes running methods on their main thread.

Evidence: `s6.queue` and `s6.ddl`. Findings: P0CL-02 and P0CL-05 (build halves; the real-method
checks belong to P0-A-1, which needs P0-I-2b for the M13 rerun), P0CL-13 (task counts, §3.14).

**P0-O-2.** Mechanisms:

- rule-engine 5.1 `Chain`, `find` and `index`, built on `schema/rulelang.py` (schema-rules note §5,
  probe P8; rule-engine overview §2.1);
- psycopg `notifies(timeout=…, stop_after=…)` on the dedicated connection (store note §4,
  interfaces note §2, psycopg overview §13.1);
- the I0 resolver and `LocatorIndex`.

Evidence: the schema-rules probe P8 for `Chain`; `s4.rules` confirms the rule syntax the helper
compiles. Findings: P0CL-09 (the scope's expression; the packet count is stated in the evaluation
document), P0CL-11 (fates outside scope), P0CL-12 (the convergence test).

**Order inside P0-O-1.** The registry, runs, task creation, agent leases and the completion
primitive come first, because P0-I-1b, P0-I-2b, P0-A-1 and P0-E-1 need them. The stage runner, the
passes, measure, the fate reader and the commands follow. The first part is a convenient milestone,
not a barrier.

## 6. Tests

Shared fixtures are foundations': the per-session database cloned from the migrated template, a
rolled-back outer transaction per test, and commit-capable tests where locks, `LISTEN` or
subprocesses need them. Thin fixtures are added here, under `tests/orchestrate/`:

- a stub registry of deterministic methods for the document, rendition and `run` unit types, plus
  an agent-tier stub whose digest is a pure function of its unit;
- a test pack (`methods.yaml`, `policies.yaml`, `slices.yaml`, a source profile) over fixture
  pages;
- `run_driver`, wrapping §3.12's driver.

| Package | What the tests establish |
|---|---|
| P0-O-0 | Protocol conformance of the stubs (pyrefly); reference markers by introspection; `payload_hash` invariance and float refusal |
| P0-O-1 | **Registry:** resolution with every reference kind; float canonicalization; an unregistered method or unknown param refused; the recorded map used for later lookups. **Runs:** the reference run at insert and no update path; `corpus_hash` stable for equal bytes and configuration. **Tasks:** reuse at creation; `fresh`; never reusing `run` tasks; skipped sentinels never matched; `prerequisite_failed`. **Leases and completion:** held-open then complete; twins, never from `failed`; `TaskNotOpen` reasons. **Two-connection tests** (commit-capable): the reuse/completion race, settled after creation; a completion blocked by a final transaction, unresolved for that run; one that committed first, consolidated. **Lifecycle** (`RuleBasedStateMachine`, below). **Stages:** with stubs, task counts per stage, barriers, a failing pass, evaluate's savepoint. **Liveness** (subprocess): kill `ci run` with `SIGKILL`; `ci status` reports orphaned; `ci run cancel`. **Commands:** `CliRunner` with stdout and stderr apart and a fixed width; `--json` equal to the result model |
| P0-O-2 | **Policies:** load, type error, unregistered method, `continue`, trigger recording, `limit`. **Slices:** include, pages, index and golden-set expansion; cycles; refusal with candidates; the recorded scope immutable. **Scope:** a trace slice run and a scoped run. **Barrier** (commit-capable): `LISTEN` woken by a completion from another connection; a lost notification caught on timeout; cancel noticed. **Convergence:** three `complete` runs; two completion orders; no `input_hash` completed twice. **Guard:** the unscoped phase 0 run. **Driver:** a slice run to completion with stubs |

**The lifecycle state machine** (D9 §4; Hypothesis overview §4, §10.1):

- **Bundles** hold created tasks, worker leases and agent leases. Input hashes are drawn from a
  small alphabet, so reuse and twins occur.
- **Rules:**
  - create tasks in a run, or in a new run;
  - claim, renew, complete or fail a worker lease (completion and failure `consumes` the lease);
  - expire a lease (lease expiry is simulated by moving `lease_until` into the past, because `now()`
    is fixed within the example's transaction);
  - write late from a stale lease;
  - agent lease, release, hold, complete;
  - settle.
- **Invariants after every step**, against a reference model of status, attempt, holder and the set
  of finished hashes:
  - no task is held by two workers;
  - a stale lease commits nothing;
  - `attempt` never decreases;
  - every `reused` task points at a `done` or `empty` task with its configuration and hash;
  - after a settle, no `awaiting_agent` task has a finished twin;
  - every terminal task has `finished_at`.
- **Isolation.** Each example runs in its own rolled-back transaction, with savepoints standing in
  for the separate transactions of claim and write.
- **Not covered.** Scheduling is not explored; real interleavings are `s6.queue`'s and the
  two-connection tests'.

## 7. Indicative size

The coordinator's budget for this document is 1,800 product lines, tests excluded.

| Package | Indicative lines |
|---|---|
| P0-O-0 | about 200 (types 120, references and `payload_hash` 50, registry interface 30) |
| P0-O-1 | about 1,150 (registry and loader 180, project init and pack upsert 140, runs and liveness 120, tasks and reuse 120, worker queue 150, agent leases and completion 150, stage runner, passes and measure 200, fates 40, commands 120, phase 0 graph 30) |
| P0-O-2 | about 450 (policy loader, context and evaluation 220, slices and scope 150, barrier, protocol and driver 80) |
| **Total** | about 1,800 |

The risks are worker-process management and the commands. Neither grows with phase 0's scope; if
either outgrows its share, the inline loop and the result models are where to simplify.

## 8. Choices left to implementation

- Module layout under `orchestrate/` and the stage graph's representation.
- Worker count, renewal cadence, and the `LISTEN` timeout (store note §4 suggests 30–60 seconds).
- How `trigger_metrics` captures the values a condition reads: a walk of the compiled rule's
  symbols, or every unit metric in the context. Both record the rule's inputs.
- The naming of D6 §6 metrics as unit-context attributes.
- Batch sizes for `create_tasks` and the claim.
- The advisory-lock namespace constant, and the form of the dirty marker on `code_commit`.
- Hypothesis settings for the state machine (examples, steps, `deadline=None` for database work).
- Message wording for refusals, and the layout of `ci status` and `ci tasks`.
