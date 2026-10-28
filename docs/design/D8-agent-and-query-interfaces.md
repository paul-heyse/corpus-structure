# D8 · Agent and query interfaces

**Proposed (2026-10-28).** The surfaces through which Opus, the operator and consumers act on
the system: the MCP server Opus works through, work packets and their size caps, the CLI, the
typed query API and exports. Every write through these surfaces becomes an observation, an
intervention or a versioned artifact; nothing writes knowledge rows directly (D1 INV-04).

## 1. Surfaces

| Surface | User | Realization | Writes |
|---|---|---|---|
| MCP server `corpus-structure` | Opus in the Claude Code session | FastMCP 4.1, stdio transport, registered in the repository's `.mcp.json` | Observations (`claim_proposal`, `judgment`), golden passes, proposals, interventions |
| CLI `ci` | The operator; scripts; Opus for read-only inspection | Typer with Rich output | Runs, directions, acks, vetoes, exports |
| Query API | CLI, MCP, later services | `serve/queries.py`: named, typed functions over SQL | Nothing |
| Exports | Downstream tools | JSON Lines and Parquet | Files |

The MCP server and the CLI call the same application functions; the MCP layer only adds
validation messages shaped for an agent and size caps.

## 2. MCP tools

### 2.1 Work queue (method M24)

| Tool | Input | Output | Effect |
|---|---|---|---|
| `queue_status` | `run?` | counts of `awaiting_agent` tasks by mode and stage; budgets left | — |
| `queue_next` | `mode?` (`extract`, `adjudicate`), `run?`, `max_units?` (default 1, at most 5) | task ids, unit keys, packet sizes | Leases the tasks to the session (30 minutes, renewed by any call on the task) |
| `read_unit` | `task_id`, `part?` | the packet (D4 §4.1) as text, one part at a time | — |
| `read_instructions` | `task_id` | the prompt parts for the task's mode (D4 §4.2: system instructions, guideline core, schema inventory, examples, model-facing JSON Schema) with their hashes; identical for all tasks of one run and mode, so read once per session | — |
| `propose_claims` | `task_id`, `batch` (model-facing ClaimProposalBatch) | accepted item count; rejected items with reasons; unlocated quotes | First submission with errors keeps the task open for one corrected resubmission; a clean or second submission completes it (`claim_proposal` observation; an intervention row referencing it) |
| `adjudicate` | `task_id`, `judgment` (D4 §4.3 judge form) | confirmation | Completes the task (`judgment` observation; an intervention row referencing it). Used from phase 1 |
| `release` | `task_id`, `reason` | — | Returns the task to `awaiting_agent` |

Validation on submission: the compiled JSON Schema; quote location (D4 §4.3); reference and type
checks. Messages name the item and field (`claims[3].qualifiers.param_values.mean: not a key of
the normal family's parameters`), so a correction is a small edit.

### 2.2 Goldens (D7 §3)

| Tool | Input | Output | Effect |
|---|---|---|---|
| `golden_next` | `set`, `pass` (`a`, `b`, `c`) | the next unit needing that pass | Leases it |
| `read_golden_unit` | `unit`, `pass` | golden-mode packet; for pass `c` also passes A and B and their alignment diff | — |
| `write_golden` | `unit`, `pass`, `batch`, `decisions?` (pass `c`: per-difference decision and reason, `guideline_gap` marks) | validation result | Stores the pass; pass `c` writes golden items and sets the unit `adjudicated` |

Passes A and B must come from separate subagent sessions; the tool records the session reference
and refuses a pass `b` from the session that wrote pass `a` for the same unit. Test-split units
are served only to golden passes, never to `read_unit` or `query` item views (D7 §4).

### 2.3 Knowledge-level proposals and decisions

| Tool | Input | Effect |
|---|---|---|
| `propose_schema_change` | YAML patch to the domain schema or `rules.yaml`, class (`additive`, `breaking`), rationale, migration mapping for breaking changes | Compiled and checked (D2 §7); stored as a pending schema version; enters through an experiment (D7 §7) |
| `propose_guideline_change` | patch to `guideline.md`, class (`clarification`, `rule`), rationale, `direction_id?` | Clarification: new guideline version immediately; rule: pending until it cites a direction or the operator acks |
| `propose_policy` | patch to `policies.yaml`, rationale | Pending policy version; enters through an experiment |
| `decide_experiment` | `experiment_id`, decision, rationale | Records the decision (D7 §7); the operator may veto |
| `record_direction` | text in the operator's words, `scope?` | Direction intervention and direction-log entry (used when the operator dictates in the session) |

### 2.4 Inspection (read-only)

| Tool | Returns |
|---|---|
| `query` | a typed query's result (§5), paginated |
| `explain` | for a claim: supports by source, confidence by source state, verifications, judgments, alternatives and links; for a unit: tasks with outcomes and the policy rules that created them |
| `run_summary` | the run's metric summary (D6 §6), worst units by a chosen metric |
| `digest` | the operator digest (D7 §8.1) |

## 3. Work packets and size caps

Output size is the binding constraint while debugging, so every tool has a cap and paginates
beyond it:

| Item | Cap |
|---|---|
| Extraction packet text and context (`read_unit` part) | 6,000 tokens; larger units are split at sentence boundaries into parts sharing the standing context (D4 §4.1) |
| Judge packet | 3,000 tokens; at most 6 alternatives |
| Units per `queue_next` | 5, and only units of one page, grouped when their packets together fit one cap |
| Any inspection response | 2,000 tokens, with a page token and a truncation marker |
| `explain` | top 10 supports and 10 links, counts for the rest |

**Debug scoping.** When a run is a slice run, `queue_next` serves only its tasks, and the agent
budget per iteration (D6 §7.4) bounds how many packets the session is asked for.

**Working instructions** for the session live in a repository skill
(`.claude/skills/work-queue/SKILL.md`, D9): how to pull and submit work, to use fresh subagents
for golden passes A, B and C, never to look at test-split items, and to keep rationales to two
sentences.

## 4. CLI

`ci` (Typer), output through Rich, compact by default and `--json` for scripts:

| Command | Does |
|---|---|
| `ci db init`, `ci db migrate` | Create or migrate the database (Alembic) |
| `ci project init --domain NAME --corpus PATH` | Create the project; register the corpus's documents from its index (with `first_pass`); load the pack's schema, guideline, policy and named configurations; declare its slices |
| `ci schema compile [--domain]`, `ci schema diff <a> <b>` | Compile the pack and show the artifacts' hashes; diff two schema versions |
| `ci ingest [--slice NAME | PATH…]` | Run M01–M03 |
| `ci run [--slice NAME] [--phase N] [--agent-mode wait|complete] [--fresh METHOD]…` | Start a run (D6 §2) |
| `ci status [RUN]`, `ci tasks [RUN] [--status S] [--method M]` | Run progress; task listing |
| `ci explain claim KEY`, `ci explain unit KEY` | As the MCP `explain` |
| `ci query NAME [--param VALUE]…` | Typed queries (§5) |
| `ci eval [RUN] [--split dev|test]` | Scores |
| `ci golden split`, `ci golden create --split S --size N [--seed K]`, `ci golden status` | Page split assignment and unit sampling (D7 §3.1); authoring progress |
| `ci experiment new|show|list` | Experiments (D7 §7) |
| `ci digest` | The operator digest |
| `ci direct "TEXT" [--scope S]`, `ci ack CHANGE`, `ci veto EXPERIMENT` | The operator's outer-loop actions |
| `ci promote RUN` | Manual promotion (normally by experiment decision) |
| `ci export claims|statements --format jsonl|parquet [--run RUN]` | Exports (§6) |

`ci ingest` and `ci run` first upsert the pack's schema, guideline, policy and configuration
versions by content hash, so editing a pack file needs no separate step; `ci ingest` creates a
run of kind `ingest`.

Opus may run read-only `ci` commands through its shell; writes go through MCP tools so they are
validated and recorded as interventions.

## 5. Typed queries

Each query is a function with a Pydantic parameter model and result model, implemented over the
D3 §9 SQL patterns. Defaults: the promoted run; status `accepted` (option `include_candidates`);
modality not `supposed` unless `include_suppositions` (D1 §5.2), except that premises referenced
by a returned claim's conditions are always returned with it; every result row carries its
claim keys and evidence locators so a consumer can cite.

### 5.1 Generic (every domain)

| Query | Parameters | Result |
|---|---|---|
| `entity` | key or label | the entity, aliases, claim counts by predicate |
| `claims` | subject?, predicate?, object?, status?, modality? | claims with values and conditions rendered |
| `statement` | statement key or unit locator (`page#unit-id`) | the statement's kind, premises, conditions, conclusions, definientia, proof link, each with evidence |
| `evidence` | claim key | evidence spans with sentence context and segment locators |
| `find` | text | BM25 hits over segments and alias hits over entities |
| `unsupported` | cluster? | `unsupported` items and their clusters |

### 5.2 Statistics

The old repository's `corpus_queries` (≈740 lines) serves as the functional specification; the
port is a reimplementation over claims (D9 §7).

| Query | Answers |
|---|---|
| `family_profile(family)` | Parameters with roles and domains; support; pdf, cdf, mgf; mean and variance; constructions it belongs to; special cases; transformations and limits |
| `families_where(predicate, value?)` | Families with a scale parameter; families whose support is `(0, \infty)` |
| `relations_between(a, b)` | `special_case_of`, `transformation_of`, `limit_of` paths between two families (recursive CTE, depth ≤ 4) |
| `transformations_of(family)` | Theorems whose premise has the family and whose conclusion gives the distribution of a transform, with conditions (T3 answers "a + bX for b ≠ 0 is normal with mean a + bμ and variance b²σ²") |
| `parameter_mapping(construction, family)` | The parameters a construction adds and how the member family's parameters map |
| `construction_profile(construction)` | Construction formula, base variable, parameter symbols, parameters with roles and domains, member families |

### 5.3 The trace's typed questions (phase 0 acceptance)

| Unit | Question | Query | Expected rows (trace claim refs) |
|---|---|---|---|
| T1 | What is a location-scale family, and what are its parameters? | `statement(LocationScale#dfn1)`, `construction_profile(location-scale family)` | Statement S1 (definition) with C2 (definiens, conditions), C3, C4–C8; profile: C4 with base variable Z and parameter symbols, parameters location and scale (C5, C6) with domains ℝ and (0, ∞) (C7, C8). C1 only with `include_suppositions` |
| T2 | What are the location and scale parameters of the normal distribution? | `family_profile(normal)` | Parameters location and scale (C2, C3), identical to mean and standard deviation (C4, C5). C1 only with `include_suppositions` |
| T3 | What is the distribution of an affine transformation of a normal variable, and under what conditions? | `transformations_of(normal)` | C3 with conditions a ∈ ℝ, b ∈ ℝ ∖ {0} and premise C1, and C2 defining Y. D1 from phase 2 |
| T4 | How is the lognormal distribution defined, and what are its shape and scale parameters? | `statement(LogNormal#dfn)`, `family_profile(lognormal)` | C1–C10 in the statement; profile: parameters mu, sigma and scale (C5, C6, C9), sigma's role shape (C8), scale = e^μ (C10), transformation of normal with its mapping (C7) |

Expected answers are the trace's target claims; D9 §4 turns them into tests.

## 6. Exports

| Export | Content | Phase |
|---|---|---|
| Claims JSON Lines | One object per claim: key, subject and object (key, type, label), predicate, value, qualifiers, conditions with referenced keys, status, confidence, evidence locators | 1 |
| Statements JSON Lines | Statements with their claims nested by role | 1 |
| Parquet | Claims, entities, evidence and measurements, written through DuckDB for analysis | 1 |
| RDF / JSON-LD | Deferred until a consumer needs it; LinkML's JSON-LD context generator makes it a small step | later |

## 7. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D8-1 | FastMCP 4.1 stdio server alongside the orchestrator's `LISTEN`/`NOTIFY`: one process or two | Phase 0 |
| OPEN-D8-2 | Whether grouping several small units in one packet lowers agent quality (context interference) | Phase 0 comparison on `core12` |
| OPEN-D8-3 | How the Claude Code session best launches blind golden passes (subagents with restricted tools) so that passes A and B are verifiably separate | Phase 0 |
