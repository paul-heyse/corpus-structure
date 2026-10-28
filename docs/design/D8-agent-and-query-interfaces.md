# D8 · Agent and query interfaces

**Proposed (2026-10-28).** The surfaces through which Opus, the operator and consumers act on
the system: the MCP server Opus works through, work packets and their size caps, the CLI, the
typed query API and exports. Every write through these surfaces becomes an observation, an
intervention or a versioned artifact; nothing writes knowledge rows directly (D1 INV-04).

## 1. Surfaces

| Surface | User | Realization | Writes |
|---|---|---|---|
| MCP server `corpus-structure` | Opus in the Claude Code session | FastMCP 4.1, stdio transport, registered in the repository's `.mcp.json`; a process of its own, separate from the orchestrator (D6 §1) | Observations (`claim_proposal`, `judgment`), proposals, interventions |
| MCP server `corpus-structure-golden` | each golden-pass subagent | the same package with only the golden tools, declared inline in the golden agent file, so every subagent gets its own server process (§2.2) | Golden passes |
| CLI `ci` | The operator; scripts; Opus for read-only inspection | Typer with Rich output | Runs, directions, acks, vetoes, exports |
| Query API | CLI, MCP, later services | `serve/queries.py`: named, typed functions over SQL; generic queries in `serve`, domain queries from the pack's `queries.py` plug-in (§5.2) | Nothing |
| Exports | Downstream tools | JSON Lines and Parquet | Files |

The MCP server and the CLI call the same application functions; the MCP layer only adds
validation messages shaped for an agent and pagination to the bounds of §3.

**Realization** ([interfaces note](../design_review/evidence/2026-10-28_library-interfaces-eval/README.md) §1, IE-1, IE-3; FastMCP 4.1.3, probed 2026-10-28):
- The lifespan runs once per stdio process and holds the connection pool; tools are synchronous and
  run on worker threads. Nothing is printed to stdout at import or lifespan time (the SDK protects
  stdout only while serving).
- Tools return Pydantic models, which give an output schema and a JSON text block; packets return
  `ToolResult(content=text, structured_content=…)`, because whether Claude Code shows
  `structuredContent` to the model is undocumented and the text is what it reads.
- Tool descriptions stay under 4,096 characters (Claude Code's limit).

## 2. MCP tools

### 2.1 Work queue (method M24)

| Tool | Input | Output | Effect |
|---|---|---|---|
| `queue_status` | `run?` | counts of `awaiting_agent` tasks by mode and stage; budgets left | — |
| `queue_next` | `mode?` (`extract`, `adjudicate`), `run?`, `max_units?` (default 1, at most 5) | task ids, unit keys, packet sizes | Leases the tasks to the session (30 minutes, renewed by any call on the task) |
| `read_unit` | `task_id`, `part?` | the packet as the assembler produced it (D4 §4.1; its hash is on the task), as text, one part at a time | — |
| `read_instructions` | `task_id` | the prompt parts for the task's mode (D4 §4.2: system instructions, guideline core, the generated annotator reference, examples, model-facing JSON Schema) with their hashes; identical for all tasks of one run and mode, so read once per session | — |
| `propose_claims` | `task_id`, `batch` (model-facing ClaimProposalBatch) | accepted item count; rejected items with reasons; unlocated quotes | First submission with errors keeps the task open for one corrected resubmission; a clean or second submission completes it (`claim_proposal` observation holding the authored batch with its citation frame, D4 §4.3; an intervention row referencing it). In the same transaction every other `awaiting_agent` task with the same input hash is set `reused`, pointing at the completed task, so a later `complete` run never asks the agent for the same packet twice (D6 §3.1, §4) |
| `adjudicate` | `task_id`, `judgment` (D4 §4.3 judge form) | confirmation | Completes the task (`judgment` observation; an intervention row referencing it). Used from phase 1 |
| `release` | `task_id`, `reason` | — | Returns the task to `awaiting_agent` |

Validation on submission: the compiled batch models (D2 §7.3); quote location (D4 §4.3);
reference and type checks; M19's rules for the `batch` call site, the `guideline:` group included,
run inside the tool over the batch (D2 §7.4, D5 §8.2). Those rules read formula symbols with the
TeX tokenizer, and grammar-dependent rules wait for finalize, so no grammar parse runs in the
tool's worker thread (P0CL-14; operator, 2026-10-28). Messages name the item and field
(`claims[3].qualifiers.param_values.mean: not a key of the normal family's parameters`), so a
correction is a small edit. The `batch` parameter is typed as a plain object, and the tool body
validates it item by item and returns a typed result (accepted count, rejected items with paths,
unlocated quotes, warnings, whether the task stays open) as a successful call. Typing the parameter
as the strict model would fail the whole call on one bad item before the tool body runs, return
pydantic's text in another path form, and so bypass the one-resubmission rule; error text over
about 11,000 characters is also trimmed by Claude Code. The batch schema is served by
`read_instructions` with its hash, not as the tool's input schema (embedding the compiled schema
there failed at registration).

### 2.2 Goldens (D7 §3)

| Tool | Input | Output | Effect |
|---|---|---|---|
| `golden_next` | `set`, `pass` (`a`, `b`, `c`) | the next unit needing that pass | Leases it |
| `read_golden_unit` | `unit`, `pass` | golden-mode packet (query-assembled standing context, D7 §3.2) with the guideline and the generated annotator reference; for pass `c` also passes A and B and their alignment diff | — |
| `write_golden` | `unit`, `pass`, `batch`, `decisions?` (pass `c`: per-difference decision and reason, `guideline_gap` marks) | validation result: errors, and guideline-rule warnings (D2 §7.4) | Stores the pass (the authored batch with its citation frame) with its session reference and model. The transaction that stores the second of passes `a` and `b` also creates the unit's pass-`c` task. Pass `c` sets the unit `adjudicated`; its golden items are derived per rendition (D7 §3.1) |

Golden passes A, B and C are fresh **Sonnet 5.5** subagent sessions dispatched by the Claude Code
session (D7 §3, ADR-0011); the session itself (Opus) does not author goldens. Passes A and B must
come from separate subagent sessions; the tool records the session reference and model and refuses
a pass `b` from the session that wrote pass `a` for the same unit.

**The session reference is the golden server's instance id.** On stdio, MCP's `ctx.session_id`
is a fresh value on every call, and subagents share the parent's connection, so the main server
cannot tell pass A from pass B. The golden agent file declares its own inline server
(`corpus-structure-golden`), so each subagent invocation starts one server process, which mints an
instance id at startup and records it as `session_ref` on every pass and lease
([interfaces note](../design_review/evidence/2026-10-28_library-interfaces-eval/README.md) IE-2). Golden leases are tasks of a `golden` run (D3 §8).
Pass-`c` tasks are created by `write_golden` itself, in the transaction that stores a unit's
second blind pass, so neither `ci run` nor a separate command has to watch for completed pairs.
> Status: **Proposed** (2026-10-28)

> Decision: [ADR-0011](../adr/0011-golden-author-and-annotator-inputs.md)

Test-split units route to the agent like any unit, so `read_unit` serves them (D7 §4; P0CL-16,
operator 2026-10-28). Test goldens are served only to their golden passes: no tool shows the
session test golden items, test alignments or test errors other than as aggregates (D7 §4).

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
| `query` | a typed query's result (§5) for a run id or `promoted` (resolved once), with the run id it was served from and its coverage; paginated by page tokens bound to that run id and the query version |
| `explain` | given a run id and a claim key or unit key, as a query result names them: for a claim, supports by source, confidence by source state, verifications, judgments, alternatives and links; for a unit, tasks with outcomes and the policy rules that created them (or the reason it was skipped) |
| `run_summary` | the run's metric summary (D6 §6), worst units by a chosen metric |
| `digest` | the operator digest (D7 §8.1) |

## 3. Work packets and size caps

Output size is the binding constraint while debugging, so every response is bounded and
paginates beyond its bound. Every bound is in characters, because the server has no Claude token
counter; the token equivalents below assume a conservative 3 characters per token. **A packet's
cap has one authority**, M24's configuration (`packet_cap_chars`,
[D2 §12.1](D2-schema-and-guidelines.md#121-methodsyaml)): the assembler splits a larger unit into
parts under it (D4 §4.1), and `read_unit` serves those parts as they are, paginating by part and
never re-cutting or re-capping them (P0CL-05; operator, 2026-10-28). The other bounds below are the
tools' own response limits; beyond them a tool returns a page token (bound to a run and a query
version, §5). FastMCP's response-limiting middleware stays only as a backstop: it counts bytes and
drops the structured result. Claude Code warns at 10,000 tokens, stops at 25,000 and writes a
result over 50,000 characters to a file, so every bound below sits well under those (interfaces
note IE-3). The LLM-tier packet caps (D4 §4.1) are counted with the served model's tokenizer
instead. The bounds for the session:

| Item | Bound |
|---|---|
| Extraction packet text and context (`read_unit` part) | M24 `extract`: 18,000 characters (about 6,000 tokens); larger units are split at sentence boundaries into parts sharing the standing context (D4 §4.1) |
| Extraction output (one ClaimProposalBatch) | sized from batches, not units: S0 batches reached about 2,500 tokens on units of at most 345 (record s0.sizes); the bound is set from S3's p99, and 24,000 characters (about 8,000 tokens) for the agent until then |
| Judge packet | M24 `adjudicate`: 9,000 characters (about 3,000 tokens); at most 6 alternatives |
| Units per `queue_next` | 5, and only units of one page, grouped when their packets together fit one cap |
| Any inspection response | 6,000 characters (about 2,000 tokens), with a page token and a truncation marker |
| `explain` | top 10 supports and 10 links, counts for the rest |
> Status: **Proposed** (2026-10-28)

**Debug scoping.** When a run is a slice run, `queue_next` serves only its tasks, and the agent
budget per iteration (D6 §7.4) bounds how many packets the session is asked for.

**Working instructions** for the session live in a repository skill
(`.claude/skills/work-queue/SKILL.md`, D9): how to pull and submit work, to use fresh subagents
for golden passes A, B and C (Sonnet, ADR-0011), never to look at test golden items or test
errors, and to keep rationales to two sentences.

## 4. CLI

`ci` (Typer), output through Rich, compact by default and `--json` for scripts:

| Command | Does |
|---|---|
| `ci db init`, `ci db migrate` | Create or migrate the database (Alembic) |
| `ci project init --domain NAME --corpus PATH` | Create the project; register the corpus's documents from its index (with `first_pass`); load the pack's schema, guideline, policy and named configurations; declare its slices |
| `ci schema compile [--domain]`, `ci schema diff <a> <b>` | Compile the pack and show the artifacts' hashes; diff two schema versions |
| `ci ingest [--slice NAME | PATH…]` | Run M01–M03 |
| `ci run [--slice NAME | --scope NAME] [--phase N] [--agent-mode wait|complete] [--fresh METHOD]…` | Start a run (D6 §2): `--slice` makes a debug slice run (kind `slice`, never promoted); `--scope` is a run option that keeps kind `full`, runs the whole corpus, routes only the named slice's units and can be promoted (D6 §8); a long run is a sequence of `complete` runs, each reusing finished tasks (D7 §7 item 5) |
| `ci status [RUN]`, `ci tasks [RUN] [--status S] [--method M]` | Run progress; task listing |
| `ci explain claim KEY [--run RUN]`, `ci explain unit KEY [--run RUN]` | As the MCP `explain`; the run defaults to the promoted run, resolved once and printed with the result |
| `ci query NAME [--run RUN] [--param VALUE]…` | Typed queries (§5); the run defaults to the promoted run, resolved once; the result names the run id it was served from and its coverage |
| `ci eval [RUN] [--split dev|test]` | Scores |
| `ci golden split`, `ci golden create --split S --size N [--seed K]`, `ci golden status` | Page split assignment and unit sampling (D7 §3.1); authoring progress |
| `ci experiment new|show|list` | Experiments (D7 §7) |
| `ci digest` | The operator digest |
| `ci direct "TEXT" [--scope S]`, `ci ack CHANGE`, `ci veto EXPERIMENT` | The operator's outer-loop actions |
| `ci promote RUN` | Manual promotion (normally by experiment decision); shows the pre-registered readings (D7 §7 item 5) and asks the operator to confirm |
| `ci export claims|statements --format jsonl|parquet [--run RUN]` | Exports (§6) |

`ci ingest` and `ci run` first upsert the pack's schema, guideline, policy and configuration
versions by content hash (configurations with the source profiles they name, resolved from
`sources/`, D2 §12.1), so editing a pack or profile file needs no separate step. They then build
any compiled artifact the schema version lacks for the installed compilers; an artifact is keyed
by schema version, compiler, compiler version and kind, so a compiler fix adds artifacts beside
a version's old ones instead of rewriting them (D2 §7, `meta.compiled_artifact` in D3 §3;
P0CL-15, operator 2026-10-28). `ci ingest` creates a run of kind `ingest`.

Opus may run read-only `ci` commands through its shell; writes go through MCP tools so they are
validated and recorded as interventions.

**Realization** (Typer 0.27, Rich 15; [interfaces note](../design_review/evidence/2026-10-28_library-interfaces-eval/README.md) §3):
command groups through `add_typer`, all in the `cli` package (D9 §1); a root callback builds
settings once; `--json` writes the same result models the query API returns, so scripts and the
MCP tools see one shape; shell completion reads pack files, never the database.

## 5. Typed queries

Each query is a function with a Pydantic parameter model, a result model and a version,
implemented over the D3 §9 SQL patterns. Every query takes a `run`: a run key, or `promoted` (the
default). Without a promoted run, a query that names none fails with that reason instead of
reading an arbitrary run; the trace acceptance test names its slice run.

**Pinning and coverage** (P0CL-11; operator, 2026-10-28):
- **One run per journey.** A journey is a query and its continuations: further pages, and
  `explain` of the keys it returned. `promoted` is resolved once, at the journey's first call;
  every result carries the run id it was served from, and continuations name that run id, never
  `promoted`. A promotion between pages, or before an `explain`, therefore cannot mix runs, which
  matters because keys are unique per run (D3) and a key read under another run is another
  realization.
- **Page tokens** bind the run id and the query version. A token whose query version has changed,
  or whose run's materialized rows have been deleted (D3 §8), is **stale** and refused with that
  reason; the caller starts a new journey.
- **Coverage.** Every result carries coverage for its scope: of the run's eligible units that the
  query reads (the whole run for corpus-wide queries; the page or unit for one named by locator),
  how many were extracted, how many were skipped and for which reason (D6 §1), how many
  failed, and how many are still unresolved at the agent. Every eligible unit has a recorded fate
  (D6 §7.4), so a short or empty answer over a partial run reads as partial, not as absence. In
  phase 0 every run is partial by construction (the `phase0-golden` slice, D7 §9).
> Status: **Proposed** (2026-10-28)

Other defaults: status `accepted` (option `include_candidates`);
modality not `supposed` unless `include_suppositions` (D1 §5.2), except that premises referenced
by a returned claim's conditions are always returned with it; every result row carries its
claim keys and evidence locators so a consumer can cite.

### 5.1 Generic (every domain)

| Query | Parameters | Result |
|---|---|---|
| `entity` | key or label | the entity, aliases, claim counts by predicate |
| `claims` | subject?, predicate?, object?, status?, modality? | claims with values and conditions rendered |
| `statement` | statement key or a locator ([D1 §3.4](D1-knowledge-representation.md#34-locators): `page#unit-id`, `page@u:…`, `page@p:…`), resolved on the run's rendition of the page | the statement's kind, premises, conditions, conclusions, definientia, proof link, each with evidence |
| `evidence` | claim key | evidence spans with sentence context and segment locators |
| `find` | text | BM25 hits over segments (D3 §5) and alias hits over entities |
| `unsupported` | cluster? | `unsupported` items and their clusters |

### 5.2 Statistics

The old repository's `corpus_queries` (≈740 lines) serves as the functional specification; the
port is a reimplementation over claims (D9 §7).

These queries are the statistics pack's plug-in, `domains/statistics/queries.py`, implementing
`serve`'s query protocol as `verifiers.py` implements `validate`'s (D2 §7.6). `serve` owns the
protocol, the run selector, pinning, coverage and pagination, and the generic queries of §5.1; a
pack's module supplies only its named queries, so a second pack adds queries without editing
`serve`, and nothing in `serve` names a statistics predicate (P0CL-07; operator, 2026-10-28):

```python
class DomainQuery(Protocol):
    name: str
    version: str                          # bound into page tokens (§5)
    params: type[BaseModel]
    result: type[BaseModel]               # one row: values, claim keys, evidence locators
    def rows(self, ctx: QueryContext, p: BaseModel) -> Iterator[BaseModel]: ...
    def scope(self, ctx: QueryContext, p: BaseModel) -> Scope: ...   # units coverage is over; default: the run
```

`QueryContext` carries the pinned run id and read access to the D3 §9 patterns; `serve` wraps
`rows` with pagination and adds the run id and coverage.
> Status: **Proposed** (2026-10-28)

| Query | Answers |
|---|---|
| `family_profile(family)` | Parameters with roles and domains (from `has_parameter` claims and from the `FamilyParameter` entities whose identity names the family); support; pdf, cdf, mgf; mean and variance; constructions it belongs to; special cases; transformations and limits |
| `families_where(predicate, value?)` | Families with a scale parameter; families whose support is `(0, \infty)` |
| `relations_between(a, b)` | `special_case_of`, `transformation_of`, `limit_of` paths between two families (recursive CTE, depth ≤ 4) |
| `transformations_of(family)` | Theorems whose premise has the family and whose conclusion gives the distribution of a transform, with conditions (T3 answers "a + bX for b ≠ 0 is normal with mean a + bμ and variance b²σ²") |
| `parameter_mapping(construction, family)` | The parameters a construction adds and how the member family's parameters map |
| `construction_profile(construction)` | Construction formula, base variable, parameter symbols, parameters with roles and domains, member families |

### 5.3 The trace's typed questions (phase 0 acceptance)

| Unit | Question | Query | Expected rows (trace claim refs) |
|---|---|---|---|
| T1 | What is a location-scale family, and what are its parameters? | `statement(LocationScale#dfn1)`, `construction_profile(location-scale family)` | Statement S1 (definition) with C2 (definiens, conditions), C3, C4–C8 (all definiens except C3); profile: C4 with base variable Z and parameter symbols, parameters location and scale (C5, C6) with domains ℝ and (0, ∞) (C7, C8). C1 only with `include_suppositions` |
| T2 | What are the location and scale parameters of the normal distribution? | `family_profile(normal)` | Parameters location and scale (the `FamilyParameter` entities N.loc and N.scale, whose identity names the family), identical to mean and standard deviation (C4, C5). The trace slice holds no `has_parameter` claim for the normal family: guideline v1 states those only in a family's definition, which T2 is not. C1 only with `include_suppositions` |
| T3 | What is the distribution of an affine transformation of a normal variable, and under what conditions? | `transformations_of(normal)` | C3 with conditions a ∈ ℝ, b ∈ ℝ ∖ {0} and premise C1, and C2 defining Y under the same restrictions. D1 from phase 2 |
| T4 | How is the lognormal distribution defined, and what are its shape and scale parameters? | `statement(LogNormal#dfn)`, `family_profile(lognormal)` | C1–C17 in the statement (with the standard lognormal, C13–C17); profile: parameters mu, sigma and scale (C5, C6, C9) with domains ℝ and (0, ∞) (C11, C12), sigma's role shape (C8), scale = e^μ (C10), transformation of normal with its mapping (C7) |

Expected answers are the trace's target claims; D9 §4 turns them into tests. For live runs the
expectation is derived from the re-authored dev goldens instead, and the rows are aligned to it
(D7 §9).

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
| OPEN-D8-1 | FastMCP 4.1 stdio server alongside the orchestrator's `LISTEN`/`NOTIFY`: one process or two | **Decided** (2026-10-28): two processes, the database the only shared state; the server only `NOTIFY`s (D6 §1) |
| OPEN-D8-2 | Whether grouping several small units in one packet lowers agent quality (context interference) | Phase 0 comparison on `core12` |
| OPEN-D8-3 | How the Claude Code session best launches blind golden passes (subagents with restricted tools) so that passes A and B are verifiably separate | Answered in practice by S0 and S0-R2 (2026-10-28): a fresh subagent per pass, given one input folder and one output folder, told what it may not read, and audited from its transcript (every tool call) rather than its own report; in phase 0 each golden subagent gets its own server process whose instance id is the session reference (§2.2) |
