# Phase 0: consolidation and queries

**Status:** Proposed (2026-10-28). Part of the [phase 0 series](../phase-0_2026-10-28.md),
which owns shared decisions, contracts, the dependency graph and build findings. Nothing here is
built. **Revised** 2026-10-28 for the [domain-model alignment review](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md)
and its [target model](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28_target-model.md)
("TM"), as the coordinator decided them (§3 decisions 16–24, §9.2): the pool is loaded through
[pool and interchange](pool-and-interchange.md)'s contract as of the run's sealed cut, and its set
steps have a DuckDB implementation beside the Python reference
([R09](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r09));
outside references are typed `ExternalReference` nodes that consolidation resolves (RC11,
[R04](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r04));
the writer adds edge and identity rows and claim columns
([R05](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r05), F04);
drops are counted by code and `explain` reads the sealed M19 task
([R07](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r07),
[R08](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r08)); the
toy pack also exercises the A3 closure.

Packages P0-C-1 to P0-C-4 (coordinator §7: C1, C2, C3, C4). Design owners:
[D5](../../design/D5-consolidation-identity-confidence.md),
[D8 §5](../../design/D8-agent-and-query-interfaces.md#5-typed-queries),
[D3 §8–§10](../../design/D3-database.md#8-runs-snapshots-and-reads),
[D1 §10](../../design/D1-knowledge-representation.md#10-identity-and-keys), the
[trace](../../design/trace.md), [ADR-0014](../../adr/0014-observations-and-run-materialization.md)
and [ADR-0019](../../adr/0019-identity-follows-content.md). Findings carried: P0CL-05 (the
knowledge half), P0CL-06 (fusion), P0CL-07, P0CL-11 and P0CL-13
([review](../../design_review/reviews/design_review_phase0-contract-layer_2026-10-28.md) §7), and
from the alignment review DA-003 (pack statement kinds), DA-007, DA-013, DA-015 (readers), F03 (the
phase 2 merge order) and F04. Their disposition stays with the design-phase plan's table and
coordinator §11, which owns every row of the alignment review. The library
mechanisms come from the [store note](../../design_review/evidence/2026-10-28_library-store/README.md)
and the [interfaces note](../../design_review/evidence/2026-10-28_library-interfaces-eval/README.md)
(2026-10-28). Design claims in this document are **Proposed** (2026-10-28) unless marked otherwise.

## 1. What this document builds

**Responsibilities.**

- **Phase 0 consolidation** (`consolidate/`, P0-C-1). D5 §11 row 0 realized as one pass function
  over the run's effective observations. It selects what the pool holds, loads it through pool and
  interchange's loader, then builds the entities, statements, `ExternalReference` nodes and claims
  with their keys, fusion, alternatives and evidence. At finalize it parses claim values once, runs
  M19 as one run-level step, and sets statuses. It rebuilds the run's knowledge rows inside the
  stage transaction, with edge and identity rows at the final pass. It is the only writer of
  `kb.entity`, `kb.claim` and their children (coordinator §4, per-run materialization).
- **The query layer** (`serve/`, `cli/query.py`, `cli/explain.py`, P0-C-2). This covers:
  - the domain-query protocol and its registry;
  - the run selector, journeys and page tokens;
  - coverage;
  - the generic queries of D8 §5.1 and `explain`;
  - the result models that `--json` writes;
  - the statistics pack's plug-in, `domains/statistics/queries.py` (D8 §5.2).
- **The deterministic acceptance test** (`tests/acceptance/test_trace.py`, P0-C-3). It runs
  coordinator §3 decision 8 end to end and hosts the knowledge half of P0CL-05's
  order-independence check.
- **The toy second pack** (`domains/toy/`, `sources/toy.yaml`, `fixtures/toy/`, P0-C-4). It runs
  the generic stages on a second domain and source with no edit under
  `python/corpus-structure/src/`, which closes P0CL-07 by its diff (coordinator §3 decision 17).

**Where it ends.** Other documents own the following, and this one only calls them:

- the key function, canonical forms, label normalization, the key scheme, typed references, the
  keying resolver with its kind refusals, and the `ExternalReference` node and its key (foundations,
  P0-F-2b, P0-F-2d, P0-F-2e);
- locators (ingest and math, P0-I-0);
- the quote cascade (agent interface, P0-A-0);
- the batch→candidate adapter (T2), the batch checks (the one owner of reference checks for
  batches, RC19), the view builder (T4) and the M19 runner (schema and rules, P0-S-2);
- the grammar (P0-I-2a);
- tasks, fates, the run's cut and the run lifecycle (orchestration);
- the MCP tools (agent interface);
- the model's vocabularies (`DropReason`, `ClaimModality` and its member properties), the generated
  `MetaData` with the edge, identity and column changes, and the overlay's indexes (model and
  projections, P0-M-1, P0-M-2);
- the pool contract, its loader as of the cut, T3 hydration, both implementations of the set steps
  and their set-equality harness, the bulk writer from generated schemas, and the Parquet run export
  (pool and interchange, P0-P-1 to P0-P-3);
- the repository's observation, span and COPY writers (P0-F-4).

This document does not define a batch shape, a key part, a locator form, a task status or a pool
relation. It builds no export: `ci export` is pool and interchange's (P0-P-3). The MCP `query` and
`explain` tools move to phase 1 with the other inspection tools of D8 §2.4, and they will wrap the
functions built here.

**Change scenarios** (from [DESIGN §1.3](../../design/DESIGN.md#section-1-3) and phase 1). They
explain the boundaries; none of them widens phase 0 scope.

| Change | Where it is expressed | What this document reuses | Unaffected here |
|---|---|---|---|
| A second domain pack (ownership: ORG-101 owns P-17) | the pack's schema (classes, predicates, statement-kind members, `ci:key_role`, `ci:case`), `rules.yaml` `views:`, `methods.yaml` `aliases:`, `queries.py`; a source profile | the pass reads class scopes, identity slots, key roles and member properties from the compiled schema and containment claims from the profile; `serve` loads the pack's plug-in | every module under `consolidate/` and `serve/` (P0-C-4 is this scenario run in phase 0) |
| A claim with `valid_time` and a cited source | identity qualifiers declared by key role in the compiled `KeySchema` (D1 §10.1; coordinator decision 20) | fusion by key, with the disagreeing-qualifier rule (D5 §5.3) | no code here names `valid_time` |
| A table segment with quantities and units | `number` values with `unit` and `basis` (D1 §6), keyed by F2b | values are stored and rendered generically | pass and queries |
| An email reference "as I wrote below" | an `ExternalReference` whose descriptor's link target is the message id (R04) | the resolution step after statements are keyed; queries render it resolved or as an unresolved reference | the entry, the writer, coverage |
| Email threads | new segment kinds with their member properties (`annotation_unit`, `statement_anchor`, `container`; TM §11), decided with the email adapter | the anchor rule reads the `statement_anchor` property, never a literal kind list | a design change to D1 comes first; supports from quoted text are phase 5 |
| Phase 1 tiers: encoders, M10, M13 scopes, M14 linking, slots, conflicts, cold-start confidence | new pool contributions and steps between assembly and statuses; slots, conflict self-joins and noisy-OR as further set steps in both implementations (TM §10) | the pass entry, the pool contract, the writer, the query layer | coverage then counts several proposing tasks per unit and must state which fate it reports (D3 §9 note) |
| Merges (phase 2) | union-find over must-links in the declared order, score then key (RC15; D5 §3.6 as amended by P0-D-2) | probe Q-7's fixture (P0-P-Q7; F03) | phase 0 merges nothing |

## 2. Contracts

### 2.1 Consumed

| Contract | Design owner | Built by | Needed by |
|---|---|---|---|
| D1 shapes, stored-item models, citation frame, keyed candidate set; canonical JSON and forms; ent/stm/clm/member/group keys; label normalization over pack alias data | D1 §5–§7, §10.1; D5 §3.3 point 5 | foundations P0-F-2a, P0-F-2b | C1, C2, C4 |
| Declared identity: the compiled `KeySchema` (key roles, conditional roles such as `attribution_identifying`, canonical form by range, case policy) and the key scheme; typed references with per-kind lookups and kind refusals by code; `ExternalReference` with its descriptor and key | D1 §10.1, §10.3; coordinator decisions 20, 21; ADR-0023 (at P0-D-1) | foundations P0-F-2d, P0-F-2e; schema and rules P0-S-1 (the pack's declarations) | C1, C4 |
| The model's vocabularies and member properties: `DropReason`, `FrameFailureReason`, `ClaimModality` (`premise_forming`, `attribution_identifying`, `conflict_bearing`), `SegmentKind` (`statement_anchor`, `search_block`), `StatementKind` per schema version; the SQL-literal constants | TM §11; coordinator decisions 1, 23 | model and projections P0-M-1 | C1, C2, C4 |
| The generated `MetaData` and overlay: `kb.claim_ref`, `kb.claim_entity_ref`, `kb.entity_identity`; `kb.claim.modality`, `polarity`, `attribution_entity_id`, `schema_version_id`; `kb.entity.resolved_to_id`; `UNIQUE (run_id, id)`; the indexes `claim_ref_target`, `claim_entity_ref_entity`, `entity_identity_value`; INV-03 and INV-08 placed by FK or left to the writer, per probe Q-4 | TM §6; coordinator decision 18; ADR-0020 (at P0-D-1) | model and projections P0-M-2; probe P0-F-Q4 | C1 (writer), C2 (joins) |
| The pool contract: model-typed Arrow relations loaded as of `cut_at`; T3 hydration into the keyed candidate set; the engine interface with the Python reference and DuckDB 2.0 implementations of the set steps and their set-equality harness; the determinism rules | TM §10; coordinator decision 22; ADR-0021 (at P0-D-1) | pool and interchange P0-P-1, P0-P-2 | C1 |
| Tables and 0001 (generated from the `MetaData`); the repository's observation writer, span upsert by `unnest`, binary COPY with `Copy.set_types` | D3 §5–§8; store note §2–§3 | foundations P0-F-4 | C1, C2 |
| F-Q4's volume data: run-scale rows on `18/corpus`, with and without same-run FKs, with its `p0q.*` record | coordinator §11 Q-4 | probe P0-F-Q4 | C2 (plans inspected on it) |
| Locator generator and resolver, refusal | D1 §3.4 | ingest and math P0-I-0 | C1 (statement and scope keys, `ExternalReference` resolution), C2 (`statement(locator)`, evidence locators) |
| Renditions, segments, sentences, macro tables, `author_markup` observations including `synthesize` | D1 §3; D4 M01, M03; D3 §6.2 | ingest and math P0-I-1a (functions), P0-I-1b (methods) | C1 (tests build them from P0-I-1a), C3 and C4 (through runs) |
| The grammar: parse status, slot kind, symbols; raises off a process's main thread | D4 M11; D1 §6.2 | ingest and math P0-I-2a | C1 at finalize |
| `parse`: authored batch plus frame → stored form on a rendition, re-location by recorded text, the D5 §5.6 fallback | D4 §4.3 | agent interface P0-A-0 | C1, for proposals stored on another rendition |
| Compiled schema lookup for a schema version; pack location | D2 §3, §7; D3 §3 | schema and rules P0-S-1, P0-S-1b | C1, C2, C4 |
| Batch checks; view builder over the keyed candidate set with `views:`, and its finalize-readings input type; M19 runner with `at:` | D2 §7.4; D5 §8.2 | schema and rules P0-S-2 | C1 |
| Method-contract types and the registry interface (configuration models, `methods.yaml` data) | D4 §1 | orchestration P0-O-0 | C1 |
| Runs with `reference_run_id`, model revision, schema version and key scheme; the assemble and finalize stages calling the pass, the final pass in its own transaction after the seal; the M19 task of unit `run` and the run's sealed final M19 task; the fate reader (tasks as of `ops.run.cut_at`); `kb.run_observation` with that cut | D3 §4, §8; D6 §1–§3.1 (RC10, at P0-D-2); [R08](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r08) | orchestration P0-O-1 | C1, C2 |
| Slices and scope, the `complete`-run protocol, an in-process run driver for tests | D6 §2, §8 | orchestration P0-O-2 | C3, C4 |
| `Client(mcp)` app factory; `queue_next`, `read_unit`, `propose_claims`; `read_unit` structured content holding the packet's sentence map (id → locator, text); the submission harness `intervene.testing` | D8 §2.1; D9 §4 | agent interface P0-A-1 | C3, C4 |
| `fixtures/s0` authored batches with frames (13); `fixtures/trace` targets authored by hand from `trace.md` | coordinator §3 decision 6 | foundations P0-F-3 | C1, C3 |
| Typer app and registration; settings; the shared conftest and database fixtures | D8 §4; D9 §3 | foundations P0-F-1 | C2, C3 |

### 2.2 Produced

| Contract | Design owner | Implemented here | Consumers |
|---|---|---|---|
| `consolidate.run_pass(conn, run, pass, m19_task) -> PassReport` | D5 §1, §11 row 0; D6 §2; ADR-0014 | the entry, the pool selection, assembly, `ExternalReference` resolution, finalize, the writer (§3.1–§3.8) | orchestration's assemble and finalize stages (P0-O-1) |
| The semantics and selection of the pool's set steps (alias-equality linking, fusion by key, alternative grouping, the pack `views:` facts): which steps run, on which relations, and what each result means | D5 §3.3, §5.3, §8.2; TM §10 | §3.2–§3.4 | pool and interchange's two implementations and their harness (P0-P-1, P0-P-2) |
| A run's knowledge rows: entities (`ExternalReference` nodes included), aliases, anchors, mentions, identity rows, claims with their modality, polarity and attribution columns, evidence, supports, links, and the edge rows | D3 §5; D1 §11; TM §6 | §3.3–§3.6 | queries (C2); evaluation's predicted set and readings (P0-E-2b); the next run's known entities, read from its reference run (P0-A-1); the Parquet run export (P0-P-3) |
| Finalize readings, supplied to S2's view builder: per distinct value, parse status, kind and symbols, of the input type P0-S-2 defines | D5 §8.2 | §3.5 | schema and rules P0-S-2 (the finalize-site view) |
| M19 `verification` observations at finalize (failing outcomes only), plus per-rule counts for the M19 task | D4 M19; D5 §8.1 | §3.5 | orchestration (writes the counts onto the task); evaluation (rule-warning rate) |
| `PassReport`: counts by `DropReason` code, statuses, alternative groups, resolved and unresolved external references, propose tasks consumed | D5 (every "counted"); R07 | §3.7 | orchestration (records it; the measure stage) |
| The query protocol (`DomainQuery`, `QueryContext`, `Scope`), registry, run selector, journeys, page tokens, coverage, `QueryResult` | D8 §5, §5.2; D3 §9 | §3.9–§3.10 | the statistics and toy plug-ins; C3; P0-E-2b (live-run answers); the phase 1 MCP tools |
| Generic queries (D8 §5.1) and `explain` (D8 §2.4, bounds of §3) | D8 §5.1, §2.4 | §3.11 | operator, Opus through read-only `ci`, C3, P0-E-2b |
| `domains/statistics/queries.py` | D8 §5.2 | §3.12 | C3; P0-E-2b; the operator |
| `ci query`, `ci explain` | D8 §4; coordinator §3 decision 10 | §3.13 | operator, scripts, Opus |
| The acceptance test | D9 §4; coordinator §3 decision 8 | §3.14 | the phase 0 gate (coordinator §1); C4 (the same journey on the toy pack) |
| The toy pack | DESIGN §1.3; D2 §2 | §3.15 | P0CL-07 closure (design-phase plan); the A3 closure and DA-003's pack-extension check (coordinator §11) |

## 3. Design of the parts

### 3.1 The pass and its transaction (P0-C-1)

Orchestration's assemble and finalize stages call `consolidate.run_pass(conn, run_id, pass_,
m19_task_id)`. The call runs inside the transaction that fences the stage's task (D6 §3.2).
Orchestration does the fencing `UPDATE` first, so a worker that lost its lease writes nothing.
The rebuild, the M19 observations and the task's terminal write then commit together. The
function takes a SQLAlchemy `Connection`, never commits or opens a transaction of its own, and
imports nothing from `orchestrate`: consolidation sits below orchestration (D9 §1). Orchestration
creates the M19 task of unit `run` for a finalize pass (D4 M19). Tasks of unit `run` are never
reused (D6 §4), so each pass's M19 task is new.

`pass_` is `assemble` or `finalize`:

- **Both passes** build the pool (§3.2) and assemble (§3.3–§3.4).
- **Assemble** writes the result with every claim at `candidate`, without edge or identity rows
  (§3.6). The run is not sealed yet, so its pool is the run's current effective observations.
- **Finalize** runs in the final-pass transaction that orchestration opens after the run's seal
  (orchestration §3.8; [R08](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r08)).
  It reads the pool as of `cut_at`, also parses values, runs M19, sets statuses and writes the final
  rows with their edge and identity rows (§3.5–§3.6). It takes no lock on the run row: the cut
  predicate alone fixes what it reads.

Phase 0 has no `check` stage, so nothing reads the assemble rows before finalize replaces them.
The second pool build is the price of keeping D6 §2's stage graph uniform. It is small at phase 0
volume, and it gives a run that fails at finalize visible candidates. In a phase without check
tasks, orchestration may skip the assemble call without any change here.

The pass runs on a process's main thread: the orchestrator's, or a `cpu` worker's. The grammar
needs its `setitimer` timeout and raises when called off a main thread (D4 M11). An MCP thread
never runs a pass.

### 3.2 Loading the evidence pool and placing its steps

**The contract is pool and interchange's.** The pool is a set of model-typed Arrow relations, each
with its M3 schema and `cs.*` metadata, loaded by `pool.load(run, cut)` from `kb.run_observation` and
the payloads as of the run's cut, one read per kind and never per item (D5 §1, "No step queries the
database directly"; P0-P-1; coordinator decision 22). Procedural steps get the keyed candidate set
by T3 hydration (P0-P-1). Consolidation decides **what** the pool holds and which steps run over it;
it does not define a relation, the loader's route (ADBC or psycopg, probe Q-5) or the engine
wrapper.

**What the pool holds** (consolidation's selection):

1. **The run row.** Schema, guideline and policy versions; options; `reference_run_id`; the model
   revision and key scheme; `cut_at` at finalize. The pass never reads
   `meta.project.promoted_run_id` (D3 §4).
2. **The run's renditions** (`kb.run_rendition`). For each: its segment tree, sentences and macro
   table, as P0-F-4's repository returns them. Segment text comes from the rendition's canonical
   text. Math and sentence segments are loaded only for renditions that hold proposals. Rendition
   content is not an observation relation and stays the repository's read.
3. **Effective observations** through the pool loader, as of `cut_at` at finalize
   (`t.finished_at <= r.cut_at`; before the seal, the run's current effective observations). Kinds
   read:
   - `claim_proposal`;
   - `author_markup` (unit, details and `dfn` markup, block hints, `synthesize`);
   - `judgment` (none in phase 0);
   - `verification`, except observations of M19 tasks. A pass recomputes its rule outcomes and
     never reads back an earlier pass's. (M19 tasks of the run's own finalize pass finish after the
     cut anyway; a reused earlier run's M19 task never enters, because `run` tasks are not reused.)

   Phase 0 reads no `scope` (M13) observations (D5 §11 row 0).
4. **The reference run's global aliases**, as a relation of `(type, normalized alias, key)` rows
   (the rows `entity_alias_lookup` serves), when `reference_run_id` is set. The linking step joins
   it.
5. **Domain data.** The compiled schema lookup for the run's schema version (P0-S-1), with its
   `KeySchema` and `views:` declarations, and the pack's `aliases:` data plus the
   `consolidate.entities` configuration through the registry interface (P0-O-0).

**Where each step runs** (TM §10; [R09](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r09)).
Identity stays in Python and reaches the engine as data: keys, canonical forms, label normalization,
the token form, locators, statement anchoring, keying in topological order, `ExternalReference`
resolution, binding resolution, value parsing, rule evaluation, statuses and the invariant
assertions (§3.3–§3.6). The **set steps** have two implementations, both pool and interchange's: the
Python reference and the in-process DuckDB 2.0 engine (P0-P-1, P0-P-2). Consolidation owns their
meaning:

| Set step | Input relations | Result, as a set | Meaning owned here |
|---|---|---|---|
| Alias-equality linking | the pool's global entities with their normalized labels; the reference run's aliases | per entity, the matching reference keys and their count | §3.3: one match links; several are `link_ambiguous`; none makes a new entity |
| Fusion by key | keyed claim candidates with their supports, evidence spans and source votes | one row per claim key with the unions | §3.4 |
| Alternative grouping | fused candidates with the canonical values of their meaning-bearing qualifiers outside the key and their bindings; batch `alternatives[]` | groups by claim key, members by member key | §3.4: disagreement, member and group keys, `ambiguous` |
| The pack `views:` facts | candidates and the facts the pack declares (`same_slot`, `alternative_of`, the pack's own) | one fact row per view attribute and candidate | D5 §8.2, D2 §7.4: the facts S2's view builder reads at finalize |

The pass runs the DuckDB implementation, selected by the `consolidate.claims` configuration
(`engine: duckdb`, the default, or `python`), so the choice is recorded with the pass task. The two
must be set-equal on the same pool (P0-P-2's harness), and C1's tests run every case of §3.3–§3.5
under both. Rule evaluation stays in rule-engine over hydrated views (TM §10); the `views:` facts
reach P0-S-2's view builder as data.

**Which stored form.** A proposal observation's `rendition_id` is normally the run's rendition of
that document, and then its stored `batch` is read as is. Otherwise C1 derives the stored form on
the run's rendition with P0-A-0's `parse`, from the observation's `authored` batch and
`citation_frame`. `parse` re-locates by recorded text, else falls back per D5 §5.6 (D4 §4.3). Under
content digests a reused M24 proposal normally comes from the same rendition, because its digest
holds the packet hash. Re-derivation is the case of an edit elsewhere on the page.

**Shared checks before assembly.** Each stored batch then passes P0-S-2's batch checks, the same
validator `propose_claims` ran at submission (AGENTS.md, "Validators are shared"); `validate` is the
one owner of reference and type checks for batches (RC19). An item that fails is dropped with the
check's code and counted. In phase 0 every proposal entered through that validator, so a drop here
means the schema or the cascade changed since submission. That is worth seeing, and it never fails
the pass. A frame that `parse` cannot resolve drops its items with the cascade's
`FrameFailureReason` code (P0-A-0).

### 3.3 Entities and statements

**Identity is the key, not the label.** In phase 0 a proposal entity is identified by its D1 §10.1
key parts, computed by F2b's key function under the run's key scheme and the compiled `KeySchema`
(identity slots with their key roles, canonical forms by declared range and case policy; P0-F-2d,
P0-S-1; coordinator decision 20):

- a global entity whose class's identity attributes (`unique_keys`) are complete:
  `(type, identity attributes)`;
- any other global entity: `(type, normalized label)`, normalized by F2b over the pack's
  `aliases:` data;
- a local entity: `(type, scope locator, normalized symbol or label)`.

Members with equal keys are one entity across units and batches. This is D5 §3.3 point 5 ("equal
normalized labels are one entity") extended to classes that declare identity keys. Grouping by
label alone would split one `FamilyParameter` that units label differently ("location parameter
of the normal distribution", "location parameter"), and the run's `UNIQUE (run_id, key)` would
then refuse the second row. Entity-valued identity attributes (a parameter's `family`) are
resolved in dependency order. A reference cycle drops the entities on it, counted as
`identity_cycle`. Each identity attribute of a written entity becomes a `kb.entity_identity` row
(§3.6), so queries join on identity instead of reading `attrs` (F04). A slot declared
`ci:case preserve` keeps its case in the key and in the identity row (`ORG-101` and `org-101` stay
apart; `X` and `x` where math-bearing; DA-008). (Proposed)

**Linking to a recorded reference run** (D5 §3.3 point 3, §11 row 0). A global entity is linked
when the reference run has exactly one global entity of the same type with a normalized alias
equal to its normalized label. It then takes that entity's key, but not its label. Several matches
make a new entity and are counted as `link_ambiguous`; no match makes a new entity. The match is the
alias-equality set step (§3.2): an equality join of normalized labels, which Python computed, with
the reference aliases, counted per entity. With an
unchanged key function, the link returns the key the entity would compute anyway. It matters when
alias data or identity attributes have changed between runs: then keys stay stable, which is the
property D1 §10.1 promises. (Proposed)

**Canonical label** (D5 §3.3 point 4, phase 0 reading). The label is the most frequent surface
form among the members' labels and aliases. A `dfn` term from author markup or the page title is
preferred when its normalization equals the entity's; ties break by code point order. Phase 0 has
no mention scores, so the score floor does not apply. Point 1 says identity-keyed classes take a
label "derived from" their identity attributes, but no pack declares how. Phase 0 applies point 4
to them as well, which changes display only, because their key holds no label. This is an open
point for the design owner (§8).

**Aliases, anchors, mentions** (D5 §3.8):

- Aliases are every member label and alias with its normalization: kind `symbol` for a local
  entity's symbol, `term` for a `dfn` term, `label` otherwise.
- Anchors are the scope segment for a local entity and the anchor segment for a statement.
- `kb.entity_mention` lists the proposal observations the entity came from. Phase 0 has no
  `mention` observations, so the supports are the proposals.
- Entity confidence stays null.

**Local scopes.** A local entity's scope segment is the stored form's `scope_segment`. P0-A-0
resolves it from the authored `extent` (D2 §7.3: `statement` is the anchor of the entity's
statement; `section` is the enclosing section from the binding sentence on). C1 generates that
segment's locator with P0-I-0 on the run's rendition and keys the entity by it (D5 §3.4).

**Statements** (D5 §3.5, D1 §10.1):

- **From markup.** Every segment of the run's renditions whose kind carries `statement_anchor`
  (today `unit` and `details`) is a statement ("a segment holds one statement by default"). Its kind comes from the profile's block,
  section and `details_kinds` hints while `use_markup_hints` is on.
- **From proposals.** The anchor segment of a batch statement is found from its first anchored
  sentence: the nearest enclosing segment whose kind carries `statement_anchor` (`details`, then
  `unit`), else the enclosing top-level annotation unit (a paragraph outside units). The kinds are
  read from the generated member-property sets (TM §11; P0-M-1; DA-003), never from a literal list.
  The key is (document key, the anchor's generated locator, the ordinal of the first sentence within
  the anchor), computed by F2b with P0-I-0.
- A proposal statement whose first sentence opens its anchor has the same key as the markup
  statement there, and the two are one. A unit that proposals split by kind gets one key per kind,
  because the first-sentence ordinals differ.
- **Context premises.** An `assumption` statement whose sentences lie inside another statement's
  anchor joins that statement. It takes the key of the statement anchored there whose sentences
  contain its first sentence. For a unit the run did not extract, that is the unit's markup
  statement. Outside units with no other statement, it keeps its own key.
- **Paragraphs outside units** hold a statement only when a proposal places one there, or when an
  `unsupported` item needs a `narrative` statement (D5 §5.1).
- **Kind** precedence is markup, then the most frequent proposal kind, with ties by code point
  order. The label follows D2 §6. The kind is the statement row's `kind` column (D3 §5), a member
  of the run schema version's `StatementKind` (core members plus the pack's), which the per-version
  member table and its composite FK enforce (TM §6; P0-M-2).

So a run whose scope is the whole first-pass corpus materializes a statement, and its synthesized
containment claims, for every unit and `details` block, extracted or not. Coverage (§3.10) says
which units were extracted. Restricting statements to routed units would make knowledge depend on
run scope in a second place, besides the fates. (Proposed)

**External references** (RC11, which decides OPEN-D1-5;
[R04](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r04); TM §6;
DA-007). An authored `outside` item ("the last result", "definition [1]", an author `[n]` link)
reaches the pool as a typed `ExternalReference` in the keyed candidate set (P0-F-2e; T2 by P0-S-2),
with its descriptor (the citing sentence and quote, and the author's link target when there is one)
and its span. It is never an `unsupported` item and never a dropped claim.

- **The node.** C1 writes it as a `kb.entity` of type `core:ExternalReference`: local scope, anchored
  at the citing statement's anchor segment, `kind` null (so D3's statement CHECK holds), keyed by
  F2e from the citing statement's key, the descriptor's text form and the link target when present.
  Claims that cite it keep it as subject, object, `claim` condition target or binding target.
- **Resolution** runs after statements are keyed and before claims are keyed, in Python. A link
  target is resolved to a locator on the run's rendition of the target page (an in-page anchor, or a
  page the run holds); a descriptor locator is resolved directly; both through P0-I-0's resolver.
  When the locator resolves to a segment that anchors a statement of this run, the node records it:
  `kb.entity.resolved_to_id` is that statement's row (the `resolves_to` relation of R04).
- **Re-keying.** A claim citing a resolved reference is keyed with the resolved statement's key in
  place of the reference's, so it fuses with claims that cite the statement directly. The citing
  claim's key therefore depends on whether resolution succeeded; D1 §10.3 lists this as a declared
  stability limit (P0-D-1), and the node keeps its own key either way.
- **Unresolved.** A target outside the run's renditions, a refused locator or a link with no
  anchor leaves the reference unresolved. The claim keeps the reference, is served as conditional on
  it (INV-09) and counts in coverage (§3.10); the `PassReport` counts it as unresolved with its
  refusal code, which is not a drop.

**Typed reference refusals** (RC19; R04, R07; DA-006, DA-013). References in pool candidates are
resolved by kind through F2e's keying resolver: `entity(ref)`, `statement(ref)`, `claim(ref)`. A
reference of the wrong kind, or to a ref the batch does not hold, is refused by that resolver with a
`DropReason` code (`wrong_reference_kind`, `unknown_claim_ref`), and C1 drops the item and counts the
code. In phase 0 every batch passed `validate`'s reference checks at submission, so such a drop means
a candidate changed shape since then; the resolver is the second, pool-side owner the RC19 split
names, not a re-implementation of `validate`.

### 3.4 Claims: candidates, keys, fusion, alternatives, evidence

**Sources in phase 0** (D5 §5.1, restricted to row 0):

- **Proposal claims** (full candidates).
- **Proposal `unsupported` items.** Each becomes predicate `core:unschematized`. Its subject is the
  statement whose anchor holds the item, and its object is a `phrase` value with the stored
  `start`, `end` and `text`.
- **Containment claims a source profile declares** (`synthesize` on an `author_markup`
  observation). The subject is the block's statement. The object is the statement the declared
  relation names (`enclosing_unit` for Siegrist). The claim's `statement` is its subject, because a
  structural claim carries its subject statement (D5 §3.5, as amended). Establishment is `stated`,
  and the evidence is the declared span (the summary) with role `primary`.

An author-stated `proves` for the same pair has the same key and fuses with the synthesized claim,
giving one claim with both supports. `trace.md` shows such rows as `S1 · —`. No consolidation code
names `core:proves`: the predicate comes from the profile.

**References.** Subjects, objects and statements are resolved by kind from local refs to keys
(§3.3's typed refusals). Condition `claim` refs are resolved to claim keys. Binding refs (`variable`
and `family_param` to entity keys; `param_of` and `param_expr_of` to claim keys) are resolved after
claim keys exist, because bindings are not part of a claim key (D5 §4). A reference to a resolved
`ExternalReference` takes the resolved statement's key (§3.3). In phase 0, bindings are taken as the
proposals state them; §4's rules do not run (D5 §11). Every resolved claim → claim and claim → entity
reference is kept with its kind and its path in the value, for the edge rows (§3.6).

**Keys** (D5 §5.2). Claim keys are computed by F2b's key function over F2b's canonical parts, under
the run's key scheme and the compiled `KeySchema`:

- defaults dropped;
- canonical values by declared range: the token form for formulas and sets; the canonical decimal
  for numbers; case kept where the slot declares `ci:case preserve` (P0-F-2d);
- qualifiers by key role: identity qualifiers in the key, meaning-bearing ones outside it (they
  decide alternatives, below), inert ones ignored; a conditional role, such as attribution under a
  modality whose member carries `attribution_identifying`, applies per claim;
- canonical condition trees, under the rules F2b freezes (D1 §6.2, §7).

C1 orders the work: candidates are keyed in a topological order of their condition `claim`
references. A cycle drops every claim on it (`condition_cycle`) and every claim depending on it
(`dropped_dependency`). A supposed claim left unreferenced because its only dependants were dropped
is dropped too (`orphaned_premise`), so INV-06 still holds. The codes are `DropReason` members
(R07), and messages are projections of them. (Proposed; the ordering follows the behaviour of the
spike's `instruments/keys.py`, §4.)

**Fusion** (D5 §5.3; phase 0 fuses by canonical form only, SymPy equivalence is phase 1):

- Candidates with equal keys are one claim. Their supports, evidence spans and source votes are
  unioned. This is the fusion set step (§3.2), a group-by on the key.
- **Disagreement.** Candidates that share a key but disagree on a qualifier whose declared key role
  is meaning-bearing (`hedge`, `scope`, attribution phrasing where attribution does not identify) or
  on their bindings form an alternative group (bindings carry meaning, D5 §5.3 as amended). A value
  that one candidate leaves null and the other sets counts as a disagreement. Grouping is the
  alternative-grouping set step (§3.2); the canonical values it groups by come from Python.
- **Keys in a group.** Each member takes F2b's member key: the claim parts plus its own canonical
  values of the disagreeing qualifiers. The group takes F2b's group key. Members are `ambiguous`.
- **A batch's `alternatives[]`** become a group in the same way, with their own claim keys and
  status `ambiguous` (D5 §11 row 0).
- `valid_time` and the cited source are identity qualifiers, so "ORG-101 owns P-17" for two
  intervals, or one fact from two sources, gives two claims through the key, not through a rule
  here (P0CL-06). Which qualifiers identify is read from the compiled `KeySchema`; no code here
  names one.

**Modality, polarity and attribution** are decision-relevant scalars and leave the qualifier map for
`kb.claim`'s columns (`modality`, `polarity`, `attribution_entity_id`; TM §6; RC06). The candidate's
values are carried to those columns unchanged; equal meaning still gives equal canonical JSON in
the key. `attribution_entity_id` names the attributed entity of this run (the cited source, or an
`ExternalReference` when the attribution is outside the batch).

`alternative_of` links run one per unordered member pair, from the smaller key to the larger. The
link `detail` carries the group key and the batch's reason, so readers group by it.

**Evidence** (D5 §5.6):

- Each stored evidence item (`start`, `end`, `role`, `coarse`) becomes a span through P0-F-4's
  upsert on the run's rendition, and then a `kb.claim_evidence` row with its role.
- `coarse` sets `completeness.evidence_coarse`.
- P0-A-0 gives every unlocated quote a coarse span over its cited sentence (D4 §4.3, as amended), so
  every item reaching C1 has a span. A `stated` claim left with no `primary` evidence is dropped as
  malformed (`malformed_evidence`), which keeps INV-01. An evidence item whose span does not lie on
  the run's rendition is dropped as `segment_not_on_rendition`.
- `completeness` also counts `unresolved_symbols` (bindings the proposal states as `unresolved`)
  and `phrase_conditions`.

### 3.5 Finalize: values, M19, statuses

**Values, once per pass.** C1 collects every distinct formula and set value in the candidates:
objects, map-qualifier entries and condition leaves. Each value is identified by its token form and
its rendition's macro-table digest. C1 parses each distinct value once with P0-I-2a's grammar on
the main thread. The result has three parts: parse status (`ok`, `partial`, `failed`, `ambiguous`),
slot kind, and symbols.

- The status is stored as the value's `parse` field. `sympy` stays absent until phase 1.
- The whole result is handed to P0-S-2's view builder as data, as values of the readings type
  P0-S-2 defines, so `validate` never imports the grammar (D5 §8.2, readers per call site, as
  amended).
- A parse that times out is `failed` with reason `timeout`. It is a value outcome, never a pass
  failure.
- A value that does not parse under its slot's range is a rule outcome (D1 §6.2), visible to rules
  that read the slot kind.

Repeated values (`\R` in every membership leaf) are parsed once. That is the point of parsing per
pass rather than per claim (P0CL-13).

**M19** (D5 §8.1, D4 M19, as amended):

- P0-S-2's view builder makes one claim view per keyed candidate, with the pool facts the pack's
  `views:` declares. Its runner then evaluates every `at: finalize` rule, the `guideline:` group
  included (D2 §7.4).
- Failing outcomes are written as `verification` observations under the M19 task, through P0-F-4's
  observation writer (binary COPY), with `claim_key`, verdict `refuted`, and `detail` holding the
  rule, severity and message.
- Passing outcomes are not written. The pass report carries per-rule counts of evaluated pairs and
  failures, which orchestration writes as `ops.measurement` rows (`rules.evaluated`, scope `rule`)
  carrying the M19 task's id (D3 §5).
- The M19 task is the one the run's seal recorded as its final M19 task (orchestration §3.8; DA-015).
  It finishes after the cut, so its outputs are read through that recorded id, never through the
  cut views (§3.11).
- A rule error makes the claim `rejected` with the rule id as reason. A warning changes no status in
  phase 0. It is recorded, and evaluation reads it for the rule-warning rate among the promotion
  readings (D7 §7).

**Statuses** (D5 §10, restricted to phase 0). In order:

1. `rejected` by a rule error;
2. `unsupported` for `core:unschematized`;
3. `ambiguous` for members of an alternative group;
4. `accepted` for agent proposals and profile-declared claims.

Phase 0 has no judgments, conflict links or `candidate` outcomes. Confidence stays null: cold-start
confidence is phase 1 (D5 §11). D5 §6.3's heading ("phases 0–1") lags that row.

### 3.6 Writing the run's knowledge

Inside the caller's transaction (D5 §1; store note §2–§3):

1. Delete the run's claim links, claims and entities by `run_id`. Their children cascade; the
   `claim_link_to` index serves the cascade (D3 §5).
2. Pre-allocate ids for entities, claims and links with
   `SELECT nextval(pg_get_serial_sequence('kb.claim','id')) FROM generate_series(1, n)` (and its
   equivalents). Parents and children then copy in one pass, with no lookup from key back to id.
   Gaps after a rollback are harmless.
3. Upsert spans through P0-F-4: one `unnest` statement with `ON CONFLICT DO NOTHING RETURNING`,
   one select for the spans that already existed, and one re-query for a concurrent writer's miss.
4. Write by binary COPY with `Copy.set_types`, in dependency order, through P0-F-4's helper over
   the generated `MetaData` (P0-M-2): `kb.entity` (with `resolved_to_id` for resolved
   `ExternalReference` rows), `kb.entity_alias`, `kb.entity_anchor`, `kb.entity_mention`,
   `kb.claim` (with `modality`, `polarity`, `attribution_entity_id` and `schema_version_id` as
   columns), `kb.claim_evidence`, `kb.claim_support`, `kb.claim_link`. Absent JSONB values are SQL
   NULL, never JSON `null`, because `CHECK ((object_entity_id IS NULL) <> (object_value IS NULL))`
   depends on it.
5. **At the final pass only**, the edge and identity rows (TM §6; RC06; F04), derived from the typed
   instances in the same transaction as their claims and entities and never edited:
   - `kb.claim_ref`, one row per claim → claim reference: kind `condition_premise` for a condition's
     `claim` node, `binding_param` for `param_of` and `param_expr_of`, with the JSON pointer of the
     node as `path`, so parallel references stay distinct (CI-03);
   - `kb.claim_entity_ref`, one row per claim → entity reference: role `qualifier` (with the
     prefixed `slot`) for an entity-ranged qualifier, `pred_arg`, `binding_variable` and
     `binding_family_param`, each with its `path`;
   - `kb.entity_identity`, one row per identity attribute of an entity: `value_entity_id` for an
     entity-valued attribute, otherwise `value_text` in its canonical form.

   They serve queries, which refuse unfinished runs (D8 §5), so the assemble pass writes none.
   Deletion follows D3 §8: edges cascade from claims and identity rows from entities.
6. At finalize, write M19's failing outcomes (§3.5).

The writer is P0-F-4's COPY helper over the generated tables. Pool and interchange's bulk writer
from generated schemas (P0-P-3, which follows this package) takes its place without a change of
row content; pgpq is used only on probe Q-5's evidence. No knowledge write needs ids returned, so
`insertmanyvalues` is not used here. It remains the route for small inserts that do return ids, as
in P0-F-4's span upsert.

**Invariants** (D5 §8.3, D1 §11). INV-01, -02, -05, -06 and -10 are asserted over the in-memory rows
before the COPY, and 0001's constraints repeat what the database can express. **INV-03** (every
predicate, class and enum value used exists in the run's schema version) and **INV-08** (condition
trees reference only claims of the same run) are placed as probe Q-4 decides (coordinator decision
18; P0-M-2):

- **by FK**, if Q-4 finds the COPY cost acceptable at run scale: the composite FK
  `(schema_version_id, predicate)` on `kb.claim` (with the per-version member FKs for kinds and
  enum values) and `(run_id, target_claim_id)` on `kb.claim_ref` enforce them, and the in-memory
  assertion stays as the earlier, keyed report;
- **by the bulk writer** otherwise: the writer asserts both over the rows it writes, with a negative
  store test per invariant (written from D1 §11, P0-F-4), and the edge tables stay for queries.

INV-09 is carried by `completeness.phrase_conditions`, by unresolved `ExternalReference` premises
and by the queries (§3.9). The cases a proposal can cause were dropped with counted codes in
§3.2–§3.4, so a violation here is a bug. The pass raises with the offending keys, the transaction
rolls back, and orchestration fails the run (D6 §2).

**Execution fit** (qualitative, coordinator §8):

- **Phase0-golden run.** The work is a pool of a few hundred proposals. Statements come from markup
  for every unit of the first-pass corpus (about 2,500) and for its `details` blocks. That gives
  thousands of rows, one transaction and a few COPY streams. The edge and identity rows add a few
  rows per claim (its premises, entity arguments and bindings) and per identity-keyed entity. The
  pool is tens of megabytes at most (S6 measured about 11.6 kB of payload per unit, Measured on the
  interim cluster, 2026-10-28), moved once per pass into Arrow.
- **The phase 1 full first pass** reaches 10⁴–10⁵ claims (D3 §11). That is still one pass per stage,
  with the pool in memory: the pool grows with the run's observations, not with the history of
  runs. That is where the set steps' engine is expected to matter: the steps are declared once as
  queries over model-named columns, and DuckDB spills where Python lists would not. A speed benefit
  is a hypothesis until measured (R09). Same-run FKs at that volume are Q-4's question.
- **What repeats** is the pool read and the rebuild. D5 §1 accepts that, because rebuilding removes
  a class of incremental-update bugs, and nothing caches consolidation (D6 §4).
- **Failure scope** is one pass. A crash rolls back, and the next attempt rebuilds from the same
  observations.

### 3.7 The pass report and failure behaviour

`PassReport` holds (DA-013; [R07](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r07)):

- totals by status;
- the alternative groups;
- **drops by code**: a count per `DropReason` member (the batch checks' codes, `FrameFailureReason`
  codes from `parse`, `condition_cycle`, `dropped_dependency`, `orphaned_premise`,
  `identity_cycle`, `wrong_reference_kind`, `unknown_claim_ref`, `malformed_evidence`,
  `segment_not_on_rendition`), each with the keys or refs it dropped. Messages are projections of
  the codes; nothing counts by message text;
- **counted outcomes that are not drops**: `link_ambiguous`, re-derived proposals, coarse evidence
  items, and external references resolved and unresolved (by refusal code);
- M19's per-rule counts;
- the number of `propose` tasks whose observations the pass consumed.

Orchestration writes the M19 counts as `ops.measurement` rows carrying the M19 task's id, and the
measure stage reads the report beside the rows (D6 §6). C1 writes no `ops` rows.

A sealed run's fates are its tasks as of `ops.run.cut_at`, and the final pass reads the pool with
the same predicate, `t.finished_at <= r.cut_at`
([R08](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r08); RC10;
orchestration §3.7–§3.9). Knowledge and coverage therefore agree by one predicate, not by a lock
held across the pass: the seal stamps `cut_at` after taking the row lock that every completion's
share lock conflicts with, so no completion can be stamped at or before the cut once the seal has
committed, and one stamped after it is unresolved for the run and absent from its pool. This
supersedes the earlier design, in which the final pass held the run row's update lock while it read
the pool and set `finished_at`. The consumed-task count checks it: C3 checks that the count equals
the fates' `extracted` count.

| Failure | Behaviour |
|---|---|
| Lost lease | orchestration's fencing `UPDATE` fails first; nothing is written |
| Grammar timeout on a value | the value is `parse: failed`; the pass continues |
| A proposal's frame no longer resolves | P0-A-0 re-locates by recorded text (writing a new frame version), else falls back per D5 §5.6; items it cannot place are dropped with their `FrameFailureReason` code |
| An item fails the batch checks | dropped with the check's code and counted |
| A reference of the wrong kind or to an unknown ref | refused by the keying resolver with its code; the item is dropped and counted (§3.3) |
| An external reference does not resolve | kept as an unresolved `ExternalReference`; the claim is served as conditional on it and counted |
| Condition cycle; dropped dependency; orphaned premise; identity cycle | dropped with their codes (§3.3–§3.4) |
| The two set-step implementations disagree | a defect in one of them, found by P0-P-2's harness and C1's tests under both engines; the pass's result is whichever the configuration selects |
| Invariant violation (INV-03 or INV-08 at an FK, or any assertion) | the pass raises with the keys; the run fails (D6 §2) |

### 3.8 Determinism (P0CL-05, the knowledge half)

The output is a function of the pool's content, under pool and interchange's determinism rules
(TM §10; P0-P-1; coordinator decision 22):

- **sets**: a set step's result is a set; nothing downstream reads its row order;
- **explicit `ORDER BY` key**: every output whose order matters (the hydration of candidates, the
  order keys are computed in, the rows handed to the writer) carries an explicit order by key, or by
  unit key and item position in the authored batch, never by observation id, task id or time.
  DuckDB 2.0 gives no row order otherwise;
- **ordered aggregates**: any aggregate whose value depends on order (a concatenation, a sum of
  decimals, phase 1's noisy-OR product) is written with `ORDER BY` key inside it;
- every tie breaks by key, or by code point order where no key exists;
- identity is computed only in Python, so both implementations see the same keys;
- observation ids enter only `kb.claim_support` and `kb.entity_mention`;
- the pass reads only `reference_run_id`, and at finalize only what the cut admits.

Two runs over the same inputs, with the queue worked in different orders, therefore give equal
entity, claim, link, edge and identity rows apart from row ids and supporting observation ids, and
the two engines give set-equal results on one pool. C3 tests this end to end (§3.14). A pass
repeated on the same run gives identical rows.

### 3.9 The query layer (P0-C-2)

**Protocol and registry** (D8 §5.2):

- `serve` owns `DomainQuery`, `QueryContext` and `Scope`. Generic queries are registered in
  `serve`. The project's pack contributes `domains/<pack>/queries.py`, imported from the pack
  directory that P0-S-1's loader reports, and exposing `QUERIES`.
- At load, a plug-in query that lacks a protocol member, or whose name clashes with another query,
  is refused with the reason.
- The registry is built from pack files alone, so shell completion never touches the database
  (interfaces note §3).

**`QueryContext`** carries:

- the pinned run id and a read-only connection;
- the run's schema lookup;
- F2b's label normalization over the pack's alias data;
- helpers for the D3 §9 patterns: claims by subject, predicate and status with the defaults below;
  statement reconstruction; evidence with locators; an entity by key or label.

A plug-in therefore writes SQL only for its own joins. Where it does, it uses SQLAlchemy Core over
the generated `MetaData` (P0-M-2). Relationships are joined through the edge and identity tables
(TM §6; F04): premises through `kb.claim_ref` (kind `condition_premise`, index `claim_ref_target`),
a claim's entity arguments and bindings through `kb.claim_entity_ref` (index
`claim_entity_ref_entity`), and identity attributes through `kb.entity_identity` (index
`entity_identity_value`), never by a JSON path into `qualifiers` or `attrs`. What stays nested (schema
qualifier maps, values, `valid_time`) is read with the JSONB comparators (store note §2):
`.path_exists()` for a qualifier's presence, which yields `@?` and is carried by `claim_pred`, not
by a GIN index (D3 §5). Modality, polarity and attribution filters read `kb.claim`'s columns.

**Plans inspected at volume.** Each generic query, and each statistics query that joins an edge or
identity table, has its plan read with `EXPLAIN (ANALYZE, BUFFERS)` on probe F-Q4's run-scale data
(the same rows, with the FK placement Q-4 chose). The check is that the join uses the overlay's
index and no sequential scan over a run's edges appears where the index applies. It is a reading at
C2's acceptance, recorded with its date, not a lint and not a performance claim (F04's closure
check, coordinator §11: "D8 joins with inspected plans").

**Defaults** (D8 §5):

- status `accepted` unless `include_candidates`;
- modality outside the `premise_forming` member set (today `{supposed}`; the generated SQL constant
  of P0-M-1) unless `include_suppositions`;
- a premise referenced by a returned claim's conditions is always returned with it, marked as a
  premise, found through `kb.claim_ref`;
- every row carries claim keys and evidence locators;
- a claim with a `phrase` or `unsupported` condition leaf, or a premise or argument that is an
  unresolved `ExternalReference`, is marked conditional (INV-09);
- **an unresolved reference is served, never omitted** (DA-007; R04): where a returned claim's
  subject, object, premise or binding target is an unresolved `ExternalReference`, the row carries
  it as "an unresolved reference: <descriptor>" with its citing locator, and a resolved one is
  rendered as the statement it resolved to (`resolved_to_id`).

**Run selector and journeys** (D8 §5, as amended):

- `run` is a run id or `promoted`. `promoted` is resolved once, at the first call of a journey,
  from `meta.project.promoted_run_id`. With none, the call is refused ("no promoted run").
- A run that is not `finished` is refused ("run not finished"). A finished run's rows never change
  (D3 §8), and an unfinished run's rows are rebuilt every pass.
- Every `QueryResult` carries `run_id`, `query`, `version`, `params`, `coverage`, `rows`,
  `next_page_token` and `truncated`.
- **Page tokens** are issued by `serve`, never by the MCP layer. A token is the URL-safe base64 of
  canonical JSON: run id, query name, query version, a digest of the parameters, and the position.
  A continuation names the token, so it names the run id, never `promoted`.
- **Stale tokens** are refused: the query's registered version differs, the parameter digest
  differs, or the run is no longer `finished`. A deletion marker for runs whose rows were deleted
  arrives with the deletion command (phase 1).

Positions are sound because the run is immutable once finished and each query's `rows()` yields in
a deterministic order, which each query's tests check. `explain` takes a run id, so a key returned
by a journey is explained under the run it came from.

**Size bounds.** The caller passes `max_rows` or `max_chars`. The phase 1 MCP tools will pass D8
§3's character bounds. `serve` fills a page until the next row's JSON would exceed the bound, then
issues a token.

### 3.10 Coverage

Coverage counts the run's `propose` fates through orchestration's fate reader, as of the run's
`cut_at` (D3 §8–§9 and D6 §1, as amended by RC10 at P0-D-2; orchestration §3.9). For the scope's
eligible units it gives:

- `extracted`: `done`, `empty`, or `reused` of either;
- `skipped`, by `SkipReason` code;
- `failed`;
- `unresolved`: `awaiting_agent`, or anything that finished after the cut.

Beside the unit fates, coverage reports the **unresolved external references** in the result's
scope: their count, and for a row that depends on one, the reference itself (§3.9). A claim that
rests on an unresolved reference is an answer with a known gap, not a missing answer (CI-04).

A `Scope` is the run, a set of documents, or a set of unit keys. The generic queries' scopes:

| Query | Scope |
|---|---|
| `entity`, `claims`, `find`, `unsupported` | the run |
| `statement` | the unit that holds the resolved anchor |
| `evidence` | the units of the claim's evidence |

A plug-in's `scope()` defaults to the run. A result whose coverage is not complete carries
`partial: true`. A query never fails because coverage is partial: in phase 0 every
`phase0-golden` run is partial by construction (D8 §5).

### 3.11 Generic queries and `explain`

| Query (D8 §5.1) | Reads | Notes |
|---|---|---|
| `entity(key or label)` | `kb.entity`, `kb.entity_alias` (`entity_alias_lookup`), `kb.entity_identity` | a label is normalized by F2b first; several matches are all returned, with their types and identity attributes |
| `claims(subject?, predicate?, object?, status?, modality?)` | `claim_pred`, `claim_subject`, `claim_object`; `kb.claim.modality`; premises through `kb.claim_ref` | values as stored; conditions as the tree plus a text rendering; unresolved references rendered (§3.9) |
| `statement(key or locator)` | P0-I-0's resolver on the run's rendition of the page; D3 §9 statement reconstruction, with premises through `kb.claim_ref` | statements anchored at the resolved segment in ordinal order; the proof link is the `proves` claims whose object is the statement; "what does X follow from" includes an unresolved reference as such, with coverage (DA-007); a refused locator returns the resolver's refusal with its candidates |
| `evidence(claim key)` | D3 §9 evidence pattern | each span with its enclosing sentence's text and an evidence locator |
| `find(text)` | BM25 (D3 §5), alias equality | the query names `kb.segment_bm25` in `to_bm25query`, repeats the index predicate and filters to the run's renditions; scores rank hits within one query only; alias hits are normalized-alias equality over the run's entities |
| `unsupported()` | `core:unschematized` claims | with their statements; no `cluster` parameter (D8 §5.1, as amended) |

An **evidence locator** in a row is `{locator, start, end, text}`:

- `locator` is P0-I-0's generated locator of the span's smallest containing segment on the run's
  rendition;
- the offsets are relative to that segment;
- `text` is the span's text.

A consumer can cite it on any content-identical rendition, and a text mismatch on another rendition
shows the edit. Locators are generated from the rendition's segments, read once per call.

**`explain`** (D8 §2.4, bounds of D8 §3):

- **For a claim:** its supports by source (observation → task → method configuration name), M19's
  failing outcomes, judgments (none in phase 0), the members of its alternative group, its links,
  its premises and entity references from the edge tables, and any external reference with its
  resolution. The top 10 supports and 10 links are listed, with counts for the rest. **M19's
  outcomes are those of the run's sealed final M19 task** (DA-015;
  [R07](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r07),
  [R08](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r08)): `explain`
  reads `verification` observations by that task id, which the seal recorded (orchestration §3.8).
  It never picks a pass by recency and never reads M19 outcomes through `kb.run_observation`, whose
  cut excludes the finalize pass's own tasks.
- **For a unit:** D3 §9's "why a method ran" rows: stage, method, rule key, trigger metrics, status,
  reason (a `SkipReason` code) and cost. Fates are read as of `cut_at`.

### 3.12 The statistics plug-in

`domains/statistics/queries.py` holds D8 §5.2's six queries. They are reimplemented over claims,
with the old repository's `evidence/corpus_queries.py` as functional specification (D9 §7). Each
has a version, a params model and a row model with claim keys and evidence locators. Each takes a
family or construction by label (normalized by F2b within its class) or by key.

- `family_profile` reads the `has_parameter` claims, the `FamilyParameter` entities whose identity
  attribute names the family (a `kb.entity_identity` join on slot `stat:family` and the family's
  entity id, through `entity_identity_value`) and their `parameter_domain`,
  `parameter_role`, `identical_parameter` and `derived_parameter` claims. It also reads the
  family's support, pdf, cdf, mgf, mean and variance claims, special cases, transformations and
  limits.
- `transformations_of` returns statements with a `has_distribution` premise on the family (found
  through `kb.claim_ref` and `kb.claim_entity_ref`) and a conclusion giving the distribution of a
  variable that a definiens of the same statement defines. Each row carries the conclusion's
  conditions, its premise and that definiens.
- `relations_between` follows `special_case_of`, `transformation_of` and `limit_of` claims with a
  recursive CTE to depth 4 (`select(...).cte(recursive=True)` with `union_all` and a depth column;
  SQLAlchemy Core, checked against its documentation 2026-10-28).
- `families_where`, `parameter_mapping` and `construction_profile` follow D8 §5.2's table.

**Reading of D8 §5.3 (Proposed).** D8 §5.3 says "C1 only with `include_suppositions`" for T1 and
T2. This document reads that as: under `include_suppositions`, a profile also returns supposed
claims whose subject or object is the profiled entity (T2's C1), and, for a construction, the
supposed claims about its base variable (T1's C1). If the design owner means otherwise, D8 §5.3
states it and these two queries follow.

### 3.13 `ci query` and `ci explain`

These are two thin modules in `cli/`, registered in the Typer app that foundations owns (D9 §1;
interfaces note §3):

- `ci query NAME [--run RUN] [--param NAME=VALUE]… [--page-token TOKEN] [--json]`;
- `ci explain claim KEY | unit KEY [--run RUN] [--json]`.

`--param` pairs are validated by the query's params model. With `--json`, stdout carries only
`QueryResult.model_dump_json()`, the same model the API returns. Otherwise Rich renders a table to
stdout, with diagnostics on `Console(stderr=True)`. The resolved run id is always printed. A refusal
exits non-zero with its reason, and under `--json` it writes an error object. Opus may run these
commands read-only through its shell (D8 §4).

### 3.14 The acceptance test (P0-C-3)

`tests/acceptance/test_trace.py` follows coordinator §3 decision 8 and D9 §4:

1. **Project and run 1.** Initialize the statistics project (P0-O-1), with the compiled schema
   (P0-S-1b), over P0-F-3's vendored pages (`fixtures/trace/corpus/`, the four spike pages, which
   hold the trace units). Run the `trace` slice with
   `agent_mode: complete` through orchestration's in-process driver. Run 1 finishes with the five
   trace units' M24 tasks `awaiting_agent`; its knowledge holds markup statements only.
2. **Coverage of run 1.** `statement` and `family_profile` over run 1 report the five units
   unresolved.
3. **Submit.** Through P0-A-1's submission harness (`intervene.testing`), which drives one
   session-scoped `Client(mcp)` from P0-A-1's app factory, for each task: `queue_next(run=run 1)`
   → `read_unit` → `propose_claims` with the `fixtures/s0` batch for that unit.
   - Before submission the harness maps each `sN` and `cN` of the fixture to the served packet's id,
     by equal (locator, text) between the fixture's frame and the packet's sentence map. A fixture
     sentence missing from the packet fails the test with its name; that reveals a segmentation or
     standing-context divergence.
   - Each submission returns every item accepted, none rejected and no guideline warnings: the v1
     reference has none (D2 §7.4).
4. **Run 1 is unchanged.** Run 1's coverage still reports five units unresolved, because fates are
   read as of the run's `cut_at`. A coverage that drifts after a run is sealed fails here.
5. **Run 2.** A rerun of the slice finds every M24 task `reused` and every ingest task `reused`.
   Its pass report's consumed-task count equals its `extracted` coverage.
6. **Questions.** The D8 §5.3 questions are asked of run 2 by id, through `serve` and once more
   through `ci query --json` under `CliRunner` (stdout and stderr apart, width fixed). The two JSON
   outputs must be equal.
   - Rows are compared with `fixtures/trace` by locator and structure: subject (type with label or
     symbol, scope locator), predicate, object (entity by type and label, or canonical value),
     canonical qualifiers, statement (anchor locator, kind), role, evidence locators.
   - Key equalities are checked where the targets state them (one `ent:` for the normal family
     across T2, T3 and T4), never key values (D1 §10.1; `fixtures/trace` holds no keys).
   - Each unit's "must not appear" list is asserted absent.
   - T3 D1 (derived) is excluded until phase 2.
   - Coverage reports the slice complete.
7. **Order independence.** A second project in the same test database repeats steps 1–5 with the
   queue worked in reverse order. Its run 2 must equal the first project's in entity, claim and link
   rows, apart from ids and supporting observation ids (§3.8), and in packet hashes (P0-A-1's half
   of P0CL-05).

**The harness.** The submission steps (pull, map, submit) are P0-A-1's `intervene.testing`
(agent interface §3.6), which this test consumes. C4 uses it too, and so does P0-E-2b's
golden-expectation run, which submits pass-C batches as the proposals of a run.

**No skip.** The test reads the original bytes of the four spike pages that P0-F-3 vendors under
`fixtures/trace/corpus/` (foundations §3.7), not the gitignored corpus, so it never skips.

**Assurance.** The test needs no live agent and no GPU. Its expectations come from targets authored
by hand from `trace.md`, so a defect in consolidation or in a query cannot reproduce itself in the
expected rows (AGENTS.md, "Validators are shared").

### 3.15 The toy second pack (P0-C-4)

The toy pack is the generality check the coordinator places in this document (§3 decision 17). It
is built from the §1.3 ownership and identity examples, so it also exercises what statistics never
does. Since the alignment review it is also the closure check of judgment A3, "extend through
composition" (review §12; coordinator §3 decision 17, §10 item 7): a pack's statement kinds,
identifier case, qualifier key roles and modality behaviour are pack declarations, with no core edit
([R01](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r01) and
[R02](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r02),
challenges; review §5, scenario S2).

| File | Holds |
|---|---|
| `domains/toy/schema/toy.yaml` | classes `Organization` (global; identity by registry id through `unique_keys`, so ORG-101 and ORG-202 with one trading name stay two), `Asset` (global), `Source` (global); predicate `owns` (`Organization` → `Asset`) allowing `valid_time`; and the A3 declarations: **pack `StatementKind` members** `toy:clause` (`claim_bearing`) and `toy:notice` (not claim-bearing); the registry id slot declared **`ci:case preserve`**; **`ci:key_role`** on two pack qualifiers, `toy:share` meaning-bearing and `toy:filing_ref` inert; a **pack modality member** `toy:reported` carrying **`attribution_identifying`**. It imports only the `core` module |
| `domains/toy/schema/rules.yaml` | one `views:` entry (the other owners of the same asset) and one finalize warning that reads it; one `guideline:` warning |
| `domains/toy/{guideline.md, policies.yaml, methods.yaml, slices.yaml, README.md}` | a one-page guideline; a `propose` chain only, whose condition reads `unit.claim_bearing`; configurations naming `sources/toy.yaml`; `aliases:` data; a slice `toy` |
| `domains/toy/queries.py` | `ownership_at(asset, date)`: each `owns` claim of the asset with its own interval and an applicability state (`established`, `not_applicable`, `unknown`), the semantics of the old repository's `ownership_at` (`evidence/corpus_queries.py`), reimplemented over claims |
| `sources/toy.yaml` | a minimal profile: paragraphs and sections, no units, no `details` synthesis, language `english`; a block hint naming `toy:clause`, typed against core vocabulary and validated against the run's schema version at run start (orchestration §3.4) |
| `fixtures/toy/` | two short HTML pages and their corpus index; authored batches with citation frames: one ownership over two validity intervals, one fact reported by two cited sources, the two same-named organizations; registry ids `ORG-101` and `org-101` as two organizations; two ownership claims differing only in `toy:filing_ref`, and two differing in `toy:share`; one fact under `toy:reported` from two sources |

The test runs C3's journey on the toy project with P0-A-1's submission harness: init, a
`complete` slice run, submission, a rerun, then queries. It checks:

- the generic `claims(predicate=toy:owns)` answers with coverage;
- `ownership_at` returns two rows with different applicability for the two intervals;
- the two cited reports are two claims;
- the two organizations are two entities;
- **pack statement kinds**: statements of kind `toy:clause` and `toy:notice` are written and pass the
  per-version kind FK; the propose chain routes the `toy:clause` units and not the `toy:notice` ones,
  by the member property, not by a literal; a profile hint naming an undeclared kind refuses the run
  at start (DA-003, DA-010);
- **case policy**: `ORG-101` and `org-101` key apart, and their identity rows keep the case;
- **key roles**: the two claims differing only in the inert `toy:filing_ref` fuse into one claim;
  the two differing in the meaning-bearing `toy:share` form an alternative group;
- **business modality**: the fact under `toy:reported` from two sources gives two claims, keyed apart
  by attribution through `attribution_identifying`, with `kb.claim.modality` holding the pack
  member.

**Closure is the diff.** The package's change touches nothing under `python/corpus-structure/src/`,
the `core` and `system` model modules included, and regenerates no generated file. That is read at
review, not linted (AGENTS.md: no new alignment linting). A core edit the toy pack needs is a P0CL-07
finding against the package that owns that code, recorded in coordinator §11, and leaves A3 open.

## 4. Ports

No spike module is ported into this document's packages. Read-only references for behaviour:

| Reference | Behaviour kept | Not kept |
|---|---|---|
| `code/instruments/keys.py` (design spikes) | keying claims in a topological order of condition references (Kahn), and dropping a cycle and its dependants with a reason | its statement key (sorted anchor segment keys) and its global key that always holds the label: D1 §10.1 replaces both, and F2b owns the key parts |
| `evidence/corpus_queries.py` (old repository, ≈740 lines) | the statistics questions as functional specification (D9 §7); `ownership_at`'s per-claim interval applicability for the toy query | its reader types, issue codes and custody model |
| `results/s0r2/reference_model_v1/*.json` | the fixture inputs, through P0-F-3's authored batches | their shapes are F3's to convert |

## 5. Packages

| Package | Scope | Prerequisites | Acceptance | Revealing failure case |
|---|---|---|---|---|
| P0-C-1 | `consolidate/`: `run_pass`; the pool selection through P0-P-1's loader as of the cut and the set steps' semantics, run on P0-P-2's engine with the Python reference set-equal; entities and statements; `ExternalReference` nodes, their resolution and re-keying; typed reference refusals; claims, keys, fusion, alternatives, evidence; modality, polarity and attribution columns; values once per pass, M19 at finalize, statuses; the writer with edge and identity rows at the final pass; INV-03 and INV-08 per Q-4; invariants; the pass report by code (§3.1–§3.8) | P0-P-1, P0-P-2, P0-F-4, P0-S-2, P0-I-1a, P0-I-2a, P0-A-0, P0-O-0, P0-O-1, P0-F-3, P0-M-2 (coordinator §7) | On renditions built by P0-I-1a and `fixtures/s0` batches located by P0-A-0, the trace units' entities, statements, claims and bindings match `fixtures/trace` by locator and structure, with D1 §11's invariants. Repeating a pass gives identical rows, and the two engines give set-equal results and equal rows. Each §3.3–§3.5 case holds: author and synthesized `proves` fuse; a hedge disagreement gives two `ambiguous` members; two validity intervals give two claims; a cycle is dropped and counted by code; a rule error rejects; a warning writes one `refuted` observation; a reference-run alias match keeps its key; an `outside` item with a resolvable link target resolves, records `resolved_to_id` and re-keys its citing claim, and one without stays an unresolved reference and is counted; a wrong-kind reference is dropped with `wrong_reference_kind`. Edge rows: each condition premise and each binding target of the trace has its `kb.claim_ref` or `kb.claim_entity_ref` row with its path; each identity attribute its `kb.entity_identity` row; none at assemble. An observation completed after the cut is absent from the final pass's pool | T3's batch with `c_proves` and the profile's synthesized `proves` give two claims (the structural statement rule is missing); or T2's "location parameter of the normal distribution" and another unit's "location parameter" with one identity give two rows and a `UNIQUE (run_id, key)` violation (identity keyed by label); or a claim with two premises gives one `kb.claim_ref` row (references keyed without their path, CI-03); or an `outside` reference disappears from the run (dropped as unsupported, DA-007) |
| P0-C-2 | `serve/`: protocol, registry, run selector, journeys and page tokens, coverage with unresolved references, generic queries over the edge and identity tables, `explain` reading the sealed M19 task, result models; `domains/statistics/queries.py`; `cli/query.py`, `cli/explain.py` (§3.9–§3.13) | P0-C-1, P0-O-1, F-Q4's volume data (P0-F-Q4) (coordinator §7) | The trace questions answer over a C1-built run. A run with `skipped(scope)` units reports partial coverage. "What does X follow from" serves an unresolved reference with coverage (DA-007). `explain` shows the sealed final M19 task's outcomes only (DA-015). The premise, entity-argument and identity joins use the overlay's indexes in plans read on F-Q4's data (F04). A promotion between two pages leaves the token's run unchanged. A bumped query version refuses the token. An unfinished run is refused. `ci query --json` equals the API's model. `find` uses the partial BM25 index (`EXPLAIN`) | `family_profile(normal)` over a run whose other units were skipped reports complete coverage; or the second page after a promotion returns the new run's rows; or a claim resting on an unresolved reference is returned as unconditional, or not at all |
| P0-C-3 | `tests/acceptance/test_trace.py` (§3.14), submitting through P0-A-1's harness | P0-A-1, P0-C-2, P0-F-3, P0-O-2 | Passes on two consecutive invocations with identical results; run 1's coverage is unchanged after submission; the reverse-order project gives equal knowledge and packet hashes | A fixture sentence that does not map into the served packet fails, naming it; a rerun that creates new M24 tasks instead of reusing them fails the reuse assertion |
| P0-C-4 | the toy pack (§3.15), widened to the A3 closure: pack `StatementKind` members, a `ci:case preserve` slot, `ci:key_role`, a pack modality member with `attribution_identifying` | P0-C-1, P0-C-2, P0-S-1, P0-S-2, P0-I-1b, P0-A-1, P0-O-2 | The toy run answers through the generic and plug-in queries with coverage; two intervals, two cited sources and two same-named organizations stay apart; each A3 check of §3.15 holds; the change touches nothing under `python/corpus-structure/src/` | A generic module that names a statistics class or predicate, expects `unit` segments, tests a literal kind list, casefolds `ORG-101`, or needs a core modality edit fails on the toy run |

**P0-C-1: mechanisms and records.**

- **Mechanisms:**
  - SQLAlchemy Core over a borrowed connection and the generated `MetaData` (P0-M-2);
  - the pool contract, loader and T3 hydration (P0-P-1), and the engine interface with DuckDB 2.0.0
    and the Python reference (P0-P-2); no DuckDB call is made from `consolidate/` except through it;
  - psycopg binary COPY with `Copy.set_types`, through P0-F-4 (store note §3), until P0-P-3's writer
    replaces the call;
  - `nextval` pre-allocation (store note §3);
  - P0-F-4's `unnest` span upsert (store note §2);
  - F2e's keying resolver and `ExternalReference` keys; P0-I-0's resolver for link targets;
  - rule-engine views and rules through P0-S-2 (D2 §7.4);
  - the Lark grammar through P0-I-2a (D4 M11).
- **Closes, with others** (coordinator §11): DA-007 (the consolidation half, with P0-F-2e and
  P0-C-2); DA-013 (`PassReport` by code, with P0-F-2c and P0-A-0); F04 (edge and identity rows and
  the columns, with P0-M-2, P0-F-4 and P0-C-2); P0CL-13 (values parsed once per pass).
- **Records:**
  - `s6.keys` and `s6.restated`: statement-key agreement under locator anchors. If they contradict
    STMT-01, D1 changes before C1 relies on it.
  - `s6.volume`: COPY of 20,000 claims.
  - `s6.dry-run`: trace rows against the compiled schema.
  - `s6.constraints`: what 0001 enforces, and what the invariant assertions must carry.
  - `s5.keys-property`: through F2a's frozen token form.
  - `s4.rules`: `views:` on the pack, through P0-S-2.
  - `p0q.*` from probe Q-4: INV-03 and INV-08 placement; from Q-5: the loader's route.

**P0-C-2: mechanisms and records.**

- **Mechanisms:**
  - joins through `kb.claim_ref`, `kb.claim_entity_ref` and `kb.entity_identity` and the overlay's
    indexes; JSONB comparators for what stays nested; the recursive CTE (store note §2; SQLAlchemy
    Core);
  - `EXPLAIN (ANALYZE, BUFFERS)` read on F-Q4's volume data;
  - pg_textsearch BM25 with the named partial index (D3 §5, [overview](../../libraries/postgresql-18-pg-textsearch.md)
    §3.3), its kind predicate from the generated `search_block` constant;
  - Pydantic result models;
  - Typer groups with `--json` (interfaces note §3).
- **Closes, with others** (coordinator §11): DA-007 (served with coverage); DA-015 (readers use the
  sealed final M19 task, with P0-O-1); F04 (D8 joins with inspected plans).
- **Records:**
  - `s6.queries`: the D3 §9 and D8 §5.3 queries and their corrections, which the edge-table joins
    replace where they read JSON paths;
  - `s6.bm25`: syntax and the planner's use of the partial index;
  - `p0q.*` from probe Q-4: the volume data the plans are read on.

**P0-C-3: mechanisms and records.**

- **Mechanisms:**
  - FastMCP `Client(mcp)` in process, one session-scoped fixture (interfaces note §1.6, Tested);
  - Typer `CliRunner` (interfaces note §3, Tested);
  - the anyio or pytest-asyncio plugin, whichever foundations' conftest selects.
- **Records:** `s0r2.reference-v1`, through P0-F-3.

**P0-C-4: mechanisms and records.** Nothing beyond C1–C3; the pack declarations are S1's compilers'
(`ci:key_role`, `ci:case`, pack `StatementKind` members) and the model's member properties. Closes,
with others (coordinator §11): A3 (judgment closure, coordinator §10 item 7); DA-003 (pack extension
of `StatementKind`, with P0-M-1 and P0-M-2).

## 6. Tests

| Package | What the tests establish | Shared fixtures used | Thin fixtures added here |
|---|---|---|---|
| P0-C-1 | The trace through D5 row 0: targets by locator and structure; invariants. Rebuild idempotence. Order independence over shuffled observation order. Each fusion, alternative, key-role, cycle, dropped-dependency, orphaned-premise, identity-cycle, wrong-kind reference, coarse-evidence, M19 and linking case of §3.3–§3.5, on small hand-made pools held as Arrow fixtures, run under both engines with set-equal results (no database server needed for these). `ExternalReference`: resolved by link target with `resolved_to_id` and the citing claim re-keyed; unresolved kept and counted; the node's key stable either way. Edge and identity rows at the final pass only, one per reference path. INV-03 and INV-08 violations refused where Q-4 placed them (FK or writer), with a negative test each. A completion after the cut absent from the final pool. An invariant violation injected below the checks rolls back with its keys. A proposal stored on one rendition and consolidated on a content-different rendition (an edit elsewhere on the page) is located on the run's rendition, and statements away from the edit keep their keys | F1's per-session test database and compiled schema; F3's `fixtures/s0` and `fixtures/trace`; P0-P-1's Arrow fixtures and P0-P-2's harness | `pool_run`: a run with renditions written from P0-I-1a's output through P0-F-4's repository, ingest tasks so that `kb.run_rendition` resolves, and proposal observations from P0-A-0's stored forms under synthetic M24 tasks, sealed with orchestration's seal; `arrow_pool`: hand-made pools as Arrow tables |
| P0-C-2 | The registry refuses malformed plug-ins. Selector, journey, token and stale-token behaviour. Coverage counts as of `cut_at` over task rows written directly, including a task finished between the cut and `finished_at`, which reads unresolved. An unresolved external reference served with coverage; a resolved one rendered as its statement. `explain` reads the sealed M19 task's outcomes and ignores another M19 task's rows of the same run. Edge and identity joins with plans read on F-Q4's data. Each generic query and each statistics query over a C1-built trace run against `fixtures/trace` expectations. `find` with `EXPLAIN` showing the partial index. CLI output equal to the API's model, with refusals as non-zero exits | as C1 | `finished_runs`: two finished runs built by `pool_run`, with the promoted pointer set and moved by the test |
| P0-C-3 | The decision 8 journey (§3.14) | F1's conftest; F3; A1's app factory and submission harness | `trace_project`; a session-scoped `mcp_client` |
| P0-C-4 | The toy journey (§3.15) | as C3 | `toy_project` |

Expected values come from `fixtures/trace` and the hand-made pools, never from a C1 run. Validators
P0-S-2 owns are called as validators, not re-tested here. Corpus-gated tests skip when the corpus
is absent (D9 §4). The tests run under `--strict-markers --strict-config`.

## 7. Indicative size

| Part | Product lines (tests excluded) |
|---|---|
| P0-C-1 `consolidate/` | about 820 (pool selection and step calls 60, entities and statements 180, claims, keys and fusion semantics 160, `ExternalReference` resolution and re-keying 90, finalize 100, writer with edge and identity rows 150, report by code and invariants 80) |
| P0-C-2 `serve/` and `cli/` | about 680 (protocol and registry 80, selector and tokens 100, coverage with unresolved references 60, generic queries over edge tables 250, `explain` 110, CLI 80) |
| P0-C-2 `domains/statistics/queries.py` | about 300 |
| P0-C-4 `domains/toy/queries.py` | about 70 (the rest of the pack is data) |
| **Total** | about 1,870, against the coordinator's 1,900 (§8). The pool loader and both implementations of the set steps are pool and interchange's budget, not counted here |

The acceptance test is test code and is not counted; the submission harness is agent interface's.

## 8. Choices left to implementation

- The module split inside `consolidate/` and `serve/`, and the names of the pass report's fields
  (its counts are keyed by code, §3.7).
- How the pool holds segments: per rendition, or per page.
- How a link target maps to a locator for `ExternalReference` resolution, within P0-I-0's resolver
  and the profile's `root`.
- Whether a value's parse result is cached across passes of one run (phase 1 iterations), provided
  each pass still parses every distinct value it lacks.
- The page token's byte form, and whether the parameter digest uses canonical JSON or the params
  model's JSON.
- The text rendering of condition trees in `claims`.
- Row elision when a single row exceeds the caller's character bound (the MCP backstop remains,
  D8 §3).
- Where the plug-in import helper lives once verifiers (phase 4) need the same import: in `serve`
  now, in P0-S-1's loader then.

**Open points for other owners** (none blocks the start of P0-C-1):

- **Canonical labels of identity-keyed classes.** D5 §3.3 point 1 has no derivation template.
  Phase 0 uses point 4 (§3.3). Design owner: confirm, or declare a template in the pack.
- **`kb.entity_mention` for proposal-derived entities.** D3 §5 says "mention observations". Phase 0
  records the proposal observations instead. Design owner: confirm the column's wording.
- **Merges (phase 2) follow the declared must-link order.** D5 §3.6's union-find refuses any union
  joining a cannot-linked pair, so its result depends on processing order (F03). RC15 fixes the
  order: descending match score, then key (D5 §3.6 as amended by P0-D-2). Phase 0 merges nothing;
  probe Q-7 (P0-P-Q7) checks the declared order against DuckDB `USING KEY` components with a
  cannot-link anti-join on a shuffled-order fixture. The phase 2 merge step is written to that
  order, and its implementation is chosen from Q-7's result. Design owner: P0-D-2's amendment.
