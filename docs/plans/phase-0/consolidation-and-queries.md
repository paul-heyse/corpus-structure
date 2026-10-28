# Phase 0: consolidation and queries

**Status:** Proposed (2026-10-28). Part of the [phase 0 series](../phase-0_2026-10-28.md),
which owns shared decisions, contracts, the dependency graph and build findings.

Packages P0-C-1 to P0-C-4 (coordinator §7: C1, C2, C3, C4). Design owners:
[D5](../../design/D5-consolidation-identity-confidence.md),
[D8 §5](../../design/D8-agent-and-query-interfaces.md#5-typed-queries),
[D3 §8–§10](../../design/D3-database.md#8-runs-snapshots-and-reads),
[D1 §10](../../design/D1-knowledge-representation.md#10-identity-and-keys), the
[trace](../../design/trace.md), [ADR-0014](../../adr/0014-observations-and-run-materialization.md)
and [ADR-0019](../../adr/0019-identity-follows-content.md). Findings carried: P0CL-05 (the
knowledge half), P0CL-06 (fusion), P0CL-07, P0CL-11 and P0CL-13
([review](../../design_review/reviews/design_review_phase0-contract-layer_2026-10-28.md) §7).
Their disposition stays with the design-phase plan's table and coordinator §11. The library
mechanisms come from the [store note](../../design_review/evidence/2026-10-28_library-store/README.md)
and the [interfaces note](../../design_review/evidence/2026-10-28_library-interfaces-eval/README.md)
(2026-10-28). Design claims in this document are **Proposed** (2026-10-28) unless marked otherwise.

## 1. What this document builds

**Responsibilities.**

- **Phase 0 consolidation** (`consolidate/`, P0-C-1). D5 §11 row 0 realized as one pass function
  over the run's effective observations. It builds the evidence pool, then the entities,
  statements and claims with their keys, fusion, alternatives and evidence. At finalize it parses
  claim values once, runs M19 as one run-level step, and sets statuses. It rebuilds the run's
  knowledge rows inside the stage transaction. It is the only writer of `kb.entity`, `kb.claim`
  and their children (coordinator §4, per-run materialization).
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

- the key function, canonical forms and label normalization (foundations, P0-F-2b);
- locators (ingest and math, P0-I-0);
- the quote cascade (agent interface, P0-A-0);
- the batch→candidate adapter, the batch checks, the view builder and the M19 runner (schema and
  rules, P0-S-2);
- the grammar (P0-I-2a);
- tasks, fates and the run lifecycle (orchestration);
- the MCP tools (agent interface);
- the repository's observation, span and COPY writers (P0-F-4).

This document does not define a batch shape, a key part, a locator form or a task status. It
builds no exports: those are phase 1 (D8 §6). The MCP `query` and `explain` tools move to phase 1
with the other inspection tools of D8 §2.4, and they will wrap the functions built here.
`extref` (OPEN-D1-5) is deferred to the phase 0 boundary together with OPEN-D2-7…20 (design-phase
plan), so phase 0 consolidation treats outside references as `unsupported` items, as authors
write them.

**Change scenarios** (from [DESIGN §1.3](../../design/DESIGN.md#section-1-3) and phase 1). They
explain the boundaries; none of them widens phase 0 scope.

| Change | Where it is expressed | What this document reuses | Unaffected here |
|---|---|---|---|
| A second domain pack (ownership: ORG-101 owns P-17) | the pack's schema, `rules.yaml` `views:`, `methods.yaml` `aliases:`, `queries.py`; a source profile | the pass reads class scopes, identity slots and identity qualifiers from the compiled schema and containment claims from the profile; `serve` loads the pack's plug-in | every module under `consolidate/` and `serve/` (P0-C-4 is this scenario run in phase 0) |
| A claim with `valid_time` and a cited source | identity qualifiers in F2b's key parts (D1 §10.1) | fusion by key, with the disagreeing-qualifier rule (D5 §5.3) | no code here names `valid_time` |
| A table segment with quantities and units | `number` values with `unit` and `basis` (D1 §6), keyed by F2b | values are stored and rendered generically | pass and queries |
| `extref` at the phase 0 boundary | D1 §6 and §7 decided there | a resolution step after statements are keyed; queries render the value | the entry, the writer, coverage |
| Email threads | new segment kinds, and a decision on which kinds anchor statements (D1 §10.1 names `unit`, `details` and paragraphs outside units) | the anchor rule reads that list | a design change to D1 comes first; supports from quoted text are phase 5 |
| Phase 1 tiers: encoders, M10, M13 scopes, M14 linking, slots, cold-start confidence | new pool contributions and steps between assembly and statuses | the pass entry, the pool loader, the writer, the query layer | coverage then counts several proposing tasks per unit and must state which fate it reports (D3 §9 note) |

## 2. Contracts

### 2.1 Consumed

| Contract | Design owner | Built by | Needed by |
|---|---|---|---|
| D1 shapes, stored-item models, citation frame, keyed candidate set; canonical JSON and forms; ent/stm/clm/member/group keys; label normalization over pack alias data | D1 §5–§7, §10.1; D5 §3.3 point 5 | foundations P0-F-2a, P0-F-2b | C1, C2, C4 |
| Locator generator and resolver, refusal | D1 §3.4 | ingest and math P0-I-0 | C1 (statement and scope keys), C2 (`statement(locator)`, evidence locators) |
| Tables and 0001; the repository's observation writer, span upsert by `unnest`, binary COPY with `Copy.set_types` | D3 §5–§8; store note §2–§3 | foundations P0-F-4 | C1, C2 |
| Renditions, segments, sentences, macro tables, `author_markup` observations including `synthesize` | D1 §3; D4 M01, M03; D3 §6.2 | ingest and math P0-I-1a (functions), P0-I-1b (methods) | C1 (tests build them from P0-I-1a), C3 and C4 (through runs) |
| The grammar: parse status, slot kind, symbols; raises off a process's main thread | D4 M11; D1 §6.2 | ingest and math P0-I-2a | C1 at finalize |
| `parse`: authored batch plus frame → stored form on a rendition, re-location by recorded text, the D5 §5.6 fallback | D4 §4.3 | agent interface P0-A-0 | C1, for proposals stored on another rendition |
| Compiled schema lookup for a schema version; pack location | D2 §3, §7; D3 §3 | schema and rules P0-S-1, P0-S-1b | C1, C2, C4 |
| Batch checks; view builder over the keyed candidate set with `views:`; M19 runner with `at:` | D2 §7.4; D5 §8.2 | schema and rules P0-S-2 | C1 |
| Method-contract types and the registry interface (configuration models, `methods.yaml` data) | D4 §1 | orchestration P0-O-0 | C1 |
| Runs and `reference_run_id`; the assemble and finalize stages calling the pass; the M19 task of unit `run`; the fate reader (tasks as of `ops.run.finished_at`); `kb.run_observation` with that cut-off | D3 §4, §8; D6 §1, §2 | orchestration P0-O-1 | C1, C2 |
| Slices and scope, the `complete`-run protocol, an in-process run driver for tests | D6 §2, §8 | orchestration P0-O-2 | C3, C4 |
| `Client(mcp)` app factory; `queue_next`, `read_unit`, `propose_claims`; `read_unit` structured content holding the packet's sentence map (id → locator, text) | D8 §2.1 | agent interface P0-A-1 | C3, C4 |
| `fixtures/s0` authored batches with frames (13); `fixtures/trace` targets authored by hand from `trace.md` | coordinator §3 decision 6 | foundations P0-F-3 | C1, C3 |
| Typer app and registration; settings; the shared conftest and database fixtures | D8 §4; D9 §3 | foundations P0-F-1 | C2, C3 |

### 2.2 Produced

| Contract | Design owner | Implemented here | Consumers |
|---|---|---|---|
| `consolidate.run_pass(conn, run, pass, m19_task) -> PassReport` | D5 §1, §11 row 0; D6 §2; ADR-0014 | the entry, the pool, assembly, finalize, the writer (§3.1–§3.8) | orchestration's assemble and finalize stages (P0-O-1) |
| A run's knowledge rows: entities, aliases, anchors, mentions, claims, evidence, supports, links | D3 §5; D1 §11 | §3.3–§3.6 | queries (C2); evaluation's predicted set and readings (P0-E-2b); the next run's known entities, read from its reference run (P0-A-1) |
| M19 `verification` observations at finalize (failing outcomes only), plus per-rule counts for the M19 task | D4 M19; D5 §8.1 | §3.5 | orchestration (writes the counts onto the task); evaluation (rule-warning rate) |
| `PassReport`: counts by drop reason, statuses, alternative groups, propose tasks consumed | D5 (every "counted") | §3.7 | orchestration (records it; the measure stage) |
| The query protocol (`DomainQuery`, `QueryContext`, `Scope`), registry, run selector, journeys, page tokens, coverage, `QueryResult` | D8 §5, §5.2; D3 §9 | §3.9–§3.10 | the statistics and toy plug-ins; C3; P0-E-2b (live-run answers); the phase 1 MCP tools |
| Generic queries (D8 §5.1) and `explain` (D8 §2.4, bounds of §3) | D8 §5.1, §2.4 | §3.11 | operator, Opus through read-only `ci`, C3, P0-E-2b |
| `domains/statistics/queries.py` | D8 §5.2 | §3.12 | C3; P0-E-2b; the operator |
| `ci query`, `ci explain` | D8 §4; coordinator §3 decision 10 | §3.13 | operator, scripts, Opus |
| The acceptance test and its submission harness | D9 §4; coordinator §3 decision 8 | §3.14 | the phase 0 gate (coordinator §1); C4; P0-E-2b's golden-expectation run |
| The toy pack | DESIGN §1.3; D2 §2 | §3.15 | P0CL-07 closure (design-phase plan) |

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
- **Assemble** writes the result with every claim at `candidate`.
- **Finalize** also parses values, runs M19, sets statuses and writes the final rows (§3.5).

Phase 0 has no `check` stage, so nothing reads the assemble rows before finalize replaces them.
The second pool build is the price of keeping D6 §2's stage graph uniform. It is small at phase 0
volume, and it gives a run that fails at finalize visible candidates. In a phase without check
tasks, orchestration may skip the assemble call without any change here.

The pass runs on a process's main thread: the orchestrator's, or a `cpu` worker's. The grammar
needs its `setitimer` timeout and raises when called off a main thread (D4 M11). An MCP thread
never runs a pass.

### 3.2 Loading the evidence pool

The pool is built by one read per kind, never per item (D5 §1, "No step queries the database
directly"):

1. **The run row.** Schema, guideline and policy versions; options; `reference_run_id`. The pass
   never reads `meta.project.promoted_run_id` (D3 §4).
2. **The run's renditions** (`kb.run_rendition`). For each: its segment tree, sentences and macro
   table, as P0-F-4's repository returns them. Segment text comes from the rendition's canonical
   text. Math and sentence segments are loaded only for renditions that hold proposals.
3. **Effective observations** through `kb.run_observation`, with the cut-off orchestration applies
   for finished runs (D3 §8). Kinds read:
   - `claim_proposal`;
   - `author_markup` (unit, details and `dfn` markup, block hints, `synthesize`);
   - `judgment` (none in phase 0);
   - `verification`, except observations of M19 tasks. A pass recomputes its rule outcomes and
     never reads back an earlier pass's.

   Phase 0 reads no `scope` (M13) observations (D5 §11 row 0).
4. **The reference run's global entities**, as `(type, normalized alias, key)` rows through
   `entity_alias_lookup`, when `reference_run_id` is set.
5. **Domain data.** The compiled schema lookup for the run's schema version (P0-S-1), and the
   pack's `aliases:` data plus the `consolidate.entities` configuration through the registry
   interface (P0-O-0).

**Which stored form.** A proposal observation's `rendition_id` is normally the run's rendition of
that document, and then its stored `batch` is read as is. Otherwise C1 derives the stored form on
the run's rendition with P0-A-0's `parse`, from the observation's `authored` batch and
`citation_frame`. `parse` re-locates by recorded text, else falls back per D5 §5.6 (D4 §4.3). Under
content digests a reused M24 proposal normally comes from the same rendition, because its digest
holds the packet hash. Re-derivation is the case of an edit elsewhere on the page.

**Shared checks before assembly.** Each stored batch then passes P0-S-2's batch checks, the same
validator `propose_claims` ran at submission (AGENTS.md, "Validators are shared"). An item that
fails is dropped with the check's reason and counted. In phase 0 every proposal entered through
that validator, so a drop here means the schema or the cascade changed since submission. That is
worth seeing, and it never fails the pass.

### 3.3 Entities and statements

**Identity is the key, not the label.** In phase 0 a proposal entity is identified by its D1 §10.1
key parts, computed by F2b:

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
resolved in dependency order. A reference cycle drops the entities on it, with a count.
(Proposed)

**Linking to a recorded reference run** (D5 §3.3 point 3, §11 row 0). A global entity is linked
when the reference run has exactly one global entity of the same type with a normalized alias
equal to its normalized label. It then takes that entity's key, but not its label. Several matches
make a new entity and are counted as `link_ambiguous`; no match makes a new entity. With an
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

- **From markup.** Every `unit` segment and every `details` block of the run's renditions is a
  statement ("a segment holds one statement by default"). Its kind comes from the profile's block,
  section and `details_kinds` hints while `use_markup_hints` is on.
- **From proposals.** The anchor segment of a batch statement is found from its first anchored
  sentence: the nearest enclosing `details` block, else the enclosing `unit`, else the enclosing
  paragraph outside units. The key is (document key, the anchor's generated locator, the ordinal
  of the first sentence within the anchor), computed by F2b with P0-I-0.
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
  order. The label follows D2 §6. The kind is stored as `kb.entity.attrs.kind`, as D3 §10 shows.
  D3 §5's column comment ("identity attributes only") lags here.

So a run whose scope is the whole first-pass corpus materializes a statement, and its synthesized
containment claims, for every unit and `details` block, extracted or not. Coverage (§3.10) says
which units were extracted. Restricting statements to routed units would make knowledge depend on
run scope in a second place, besides the fates. (Proposed)

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

**References.** Subjects, objects and statements are resolved from local refs to keys. Condition
`claim` refs are resolved to claim keys. Binding refs (`variable` and `family_param` to entity
keys; `param_of` and `param_expr_of` to claim keys) are resolved after claim keys exist, because
bindings are not part of a claim key (D5 §4). In phase 0, bindings are taken as the proposals state
them; §4's rules do not run (D5 §11).

**Keys** (D5 §5.2). Claim keys are computed by F2b's key function over F2b's canonical parts:

- defaults dropped;
- canonical values: the token form for formulas and sets; the canonical decimal for numbers;
- canonical condition trees, under the rules F2b freezes (D1 §6.2, §7).

C1 orders the work: candidates are keyed in a topological order of their condition `claim`
references. A cycle drops every claim on it or depending on it (`condition_cycle`). A supposed
claim left unreferenced because its only dependants were dropped is dropped too
(`orphaned_premise`), so INV-06 still holds. (Proposed; the ordering follows the behaviour of the
spike's `instruments/keys.py`, §4.)

**Fusion** (D5 §5.3; phase 0 fuses by canonical form only, SymPy equivalence is phase 1):

- Candidates with equal keys are one claim. Their supports, evidence spans and source votes are
  unioned.
- **Disagreement.** Candidates that share a key but disagree on a meaning-bearing qualifier outside
  the key (`hedge`, `scope`, attribution phrasing) or on their bindings form an alternative group
  (bindings carry meaning, D5 §5.3 as amended). A value that one candidate leaves null and the other
  sets counts as a disagreement.
- **Keys in a group.** Each member takes F2b's member key: the claim parts plus its own canonical
  values of the disagreeing qualifiers. The group takes F2b's group key. Members are `ambiguous`.
- **A batch's `alternatives[]`** become a group in the same way, with their own claim keys and
  status `ambiguous` (D5 §11 row 0).
- `valid_time` and the cited source are identity qualifiers, so "ORG-101 owns P-17" for two
  intervals, or one fact from two sources, gives two claims through the key, not through a rule
  here (P0CL-06).

`alternative_of` links run one per unordered member pair, from the smaller key to the larger. The
link `detail` carries the group key and the batch's reason, so readers group by it.

**Evidence** (D5 §5.6):

- Each stored evidence item (`start`, `end`, `role`, `coarse`) becomes a span through P0-F-4's
  upsert on the run's rendition, and then a `kb.claim_evidence` row with its role.
- `coarse` sets `completeness.evidence_coarse`.
- P0-A-0 gives every unlocated quote a coarse span over its cited sentence (D4 §4.3, as amended), so
  every item reaching C1 has a span. A `stated` claim left with no `primary` evidence is dropped as
  malformed (`malformed_evidence`), which keeps INV-01.
- `completeness` also counts `unresolved_symbols` (bindings the proposal states as `unresolved`)
  and `phrase_conditions`.

### 3.5 Finalize: values, M19, statuses

**Values, once per pass.** C1 collects every distinct formula and set value in the candidates:
objects, map-qualifier entries and condition leaves. Each value is identified by its token form and
its rendition's macro-table digest. C1 parses each distinct value once with P0-I-2a's grammar on
the main thread. The result has three parts: parse status (`ok`, `partial`, `failed`, `ambiguous`),
slot kind, and symbols.

- The status is stored as the value's `parse` field. `sympy` stays absent until phase 1.
- The whole result is handed to P0-S-2's view builder as data, so `validate` never imports the
  grammar (D5 §8.2, readers per call site, as amended).
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
4. Write by binary COPY with `Copy.set_types`, in dependency order, through P0-F-4's helper:
   `kb.entity`, `kb.entity_alias`, `kb.entity_anchor`, `kb.entity_mention`, `kb.claim`,
   `kb.claim_evidence`, `kb.claim_support`, `kb.claim_link`. Absent JSONB values are SQL NULL,
   never JSON `null`, because `CHECK ((object_entity_id IS NULL) <> (object_value IS NULL))`
   depends on it.
5. At finalize, write M19's failing outcomes (§3.5).

No knowledge write needs ids returned, so `insertmanyvalues` is not used here. It remains the
route for small inserts that do return ids, as in P0-F-4's span upsert.

**Invariants** (D5 §8.3, D1 §11). INV-01, -02, -05, -06, -08 and -10 are asserted over the
in-memory rows before the COPY, and 0001's constraints repeat what the database can express. INV-03
is checked against the schema lookup. INV-09 is carried by `completeness.phrase_conditions` and by
the queries (§3.9). The cases a proposal can cause were dropped with counted reasons in §3.2–§3.4,
so a violation here is a bug. The pass raises with the offending keys, the transaction rolls back,
and orchestration fails the run (D6 §2).

**Execution fit** (qualitative, coordinator §8):

- **Phase0-golden run.** The work is a pool of a few hundred proposals. Statements come from markup
  for every unit of the first-pass corpus (about 2,500) and for its `details` blocks. That gives
  thousands of rows, one transaction and a few COPY streams.
- **The phase 1 full first pass** reaches 10⁴–10⁵ claims (D3 §11). That is still one pass per stage,
  with the pool in memory: the pool grows with the run's observations, not with the history of
  runs.
- **What repeats** is the pool read and the rebuild. D5 §1 accepts that, because rebuilding removes
  a class of incremental-update bugs, and nothing caches consolidation (D6 §4).
- **Failure scope** is one pass. A crash rolls back, and the next attempt rebuilds from the same
  observations.

### 3.7 The pass report and failure behaviour

`PassReport` holds:

- totals by status;
- the alternative groups;
- the counts of every drop and fallback named above: batch-check reasons, `condition_cycle`,
  `orphaned_premise`, `malformed_evidence`, `link_ambiguous`, re-derived proposals and coarse
  evidence items;
- M19's per-rule counts;
- the number of `propose` tasks whose observations the pass consumed.

Orchestration writes the M19 counts as `ops.measurement` rows carrying the M19 task's id, and the
measure stage reads the report beside the rows (D6 §6). C1 writes no `ops` rows.

A finished run's fates are its tasks as of `ops.run.finished_at` (D3 §8, as amended), and the pool
reads `kb.run_observation` with the same cut-off. Knowledge and coverage therefore agree: an agent
completion takes a share lock on the run row, and the final pass holds the update lock while it
reads the pool and sets `finished_at` (D6 §3.1), so a completion is either consolidated or counts as
unresolved for that run. The consumed-task count checks it. C3 checks that the count equals the fates' `extracted`
count.

| Failure | Behaviour |
|---|---|
| Lost lease | orchestration's fencing `UPDATE` fails first; nothing is written |
| Grammar timeout on a value | the value is `parse: failed`; the pass continues |
| A proposal's frame no longer resolves | P0-A-0 re-locates by recorded text, else falls back per D5 §5.6; items it cannot place are dropped with a count |
| An item fails the batch checks | dropped with the check's reason and counted |
| Condition cycle; orphaned premise | dropped with a count (§3.4) |
| Invariant violation | the pass raises with the keys; the run fails (D6 §2) |

### 3.8 Determinism (P0CL-05, the knowledge half)

The output is a function of the pool's content:

- inputs are ordered by unit key and by item position in the authored batch, never by observation
  id, task id or time;
- every tie breaks by code point order;
- observation ids enter only `kb.claim_support` and `kb.entity_mention`;
- the pass reads only `reference_run_id`.

Two runs over the same inputs, with the queue worked in different orders, therefore give equal
entity, claim and link rows apart from row ids and supporting observation ids. C3 tests this
end to end (§3.14). A pass repeated on the same run gives identical rows.

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

A plug-in therefore writes SQL only for its own joins. Where it does, it uses SQLAlchemy Core with
the JSONB comparators (store note §2): `.contains()` for identity attributes, which yields `@>`;
`.path_exists()` for a qualifier's presence, which yields `@?` and is carried by `claim_pred`, not
by a GIN index (D3 §5).

**Defaults** (D8 §5):

- status `accepted` unless `include_candidates`;
- modality other than `supposed` unless `include_suppositions`;
- a premise referenced by a returned claim's conditions is always returned with it, marked as a
  premise;
- every row carries claim keys and evidence locators;
- a claim with a `phrase` or `unsupported` condition leaf is marked conditional (INV-09).

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

Coverage counts the run's `propose` fates through orchestration's fate reader, as of
`finished_at` (D3 §8–§9 and D6 §1, as amended). For the scope's eligible units it gives:

- `extracted`: `done`, `empty`, or `reused` of either;
- `skipped`, by reason;
- `failed`;
- `unresolved`: `awaiting_agent`, or anything that finished after the run did.

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
| `entity(key or label)` | `kb.entity`, `kb.entity_alias` (`entity_alias_lookup`) | a label is normalized by F2b first; several matches are all returned, with their types |
| `claims(subject?, predicate?, object?, status?, modality?)` | `claim_pred`, `claim_subject`, `claim_object` | values as stored; conditions as the tree plus a text rendering |
| `statement(key or locator)` | P0-I-0's resolver on the run's rendition of the page; D3 §9 statement reconstruction | statements anchored at the resolved segment in ordinal order; the proof link is the `proves` claims whose object is the statement; a refused locator returns the resolver's refusal with its candidates |
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
  failing outcomes, judgments (none in phase 0), the members of its alternative group, and its
  links. The top 10 supports and 10 links are listed, with counts for the rest.
- **For a unit:** D3 §9's "why a method ran" rows: stage, method, rule key, trigger metrics, status,
  reason and cost. Fates are read as of `finished_at`.

### 3.12 The statistics plug-in

`domains/statistics/queries.py` holds D8 §5.2's six queries. They are reimplemented over claims,
with the old repository's `evidence/corpus_queries.py` as functional specification (D9 §7). Each
has a version, a params model and a row model with claim keys and evidence locators. Each takes a
family or construction by label (normalized by F2b within its class) or by key.

- `family_profile` reads the `has_parameter` claims, the `FamilyParameter` entities whose identity
  attribute names the family (`attrs.contains({"family": key})`) and their `parameter_domain`,
  `parameter_role`, `identical_parameter` and `derived_parameter` claims. It also reads the
  family's support, pdf, cdf, mgf, mean and variance claims, special cases, transformations and
  limits.
- `transformations_of` returns statements with a `has_distribution` premise on the family and a
  conclusion giving the distribution of a variable that a definiens of the same statement defines.
  Each row carries the conclusion's conditions, its premise and that definiens.
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

1. **Project and run 1.** Initialize the statistics project over a corpus that holds the three
   trace pages (P0-O-1), with the compiled schema (P0-S-1b). Run the `trace` slice with
   `agent_mode: complete` through orchestration's in-process driver. Run 1 finishes with the five
   trace units' M24 tasks `awaiting_agent`; its knowledge holds markup statements only.
2. **Coverage of run 1.** `statement` and `family_profile` over run 1 report the five units
   unresolved.
3. **Submit.** Through one session-scoped `Client(mcp)` from P0-A-1's app factory, for each task:
   `queue_next(run=run 1)` → `read_unit` → `propose_claims` with the `fixtures/s0` batch for that
   unit.
   - Before submission the harness maps each `sN` and `cN` of the fixture to the served packet's id,
     by equal (locator, text) between the fixture's frame and the packet's sentence map. A fixture
     sentence missing from the packet fails the test with its name; that reveals a segmentation or
     standing-context divergence.
   - Each submission returns every item accepted, none rejected and no guideline warnings: the v1
     reference has none (D2 §7.4).
4. **Run 1 is unchanged.** Run 1's coverage still reports five units unresolved, because fates are
   read as of `finished_at`. A coverage that drifts after a run finishes fails here.
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

**The harness.** The submission steps (pull, map, submit) are one helper, `tests/support/submit.py`.
C4 uses it, and so does P0-E-2b's golden-expectation run, which submits pass-C batches as the
proposals of a run (evaluation and goldens document).

**Skipping.** The test needs the three trace pages' original bytes. The corpus is gitignored, so
the test skips with the reason "trace pages absent" when they are missing. Qualification must cite
a run of the test that did not skip (§8).

**Assurance.** The test needs no live agent and no GPU. Its expectations come from targets authored
by hand from `trace.md`, so a defect in consolidation or in a query cannot reproduce itself in the
expected rows (AGENTS.md, "Validators are shared").

### 3.15 The toy second pack (P0-C-4)

The toy pack is the generality check the coordinator places in this document (§3 decision 17). It
is built from the §1.3 ownership and identity examples, so it also exercises what statistics never
does:

| File | Holds |
|---|---|
| `domains/toy/schema/toy.yaml` | classes `Organization` (global; identity by registry id through `unique_keys`, so ORG-101 and ORG-202 with one trading name stay two), `Asset` (global), `Source` (global); predicate `owns` (`Organization` → `Asset`) allowing `valid_time`; nothing imported but `core.yaml` |
| `domains/toy/schema/rules.yaml` | one `views:` entry (the other owners of the same asset) and one finalize warning that reads it; one `guideline:` warning |
| `domains/toy/{guideline.md, policies.yaml, methods.yaml, slices.yaml, README.md}` | a one-page guideline; a `propose` chain only; configurations naming `sources/toy.yaml`; `aliases:` data; a slice `toy` |
| `domains/toy/queries.py` | `ownership_at(asset, date)`: each `owns` claim of the asset with its own interval and an applicability state (`established`, `not_applicable`, `unknown`), the semantics of the old repository's `ownership_at` (`evidence/corpus_queries.py`), reimplemented over claims |
| `sources/toy.yaml` | a minimal profile: paragraphs and sections, no units, no `details` synthesis, language `english` |
| `fixtures/toy/` | two short HTML pages and their corpus index; authored batches with citation frames: one ownership over two validity intervals, one fact reported by two cited sources, the two same-named organizations |

The test runs the C3 harness on the toy project: init, a `complete` slice run, submission, a rerun,
then queries. It checks:

- the generic `claims(predicate=toy:owns)` answers with coverage;
- `ownership_at` returns two rows with different applicability for the two intervals;
- the two cited reports are two claims;
- the two organizations are two entities.

**Closure is the diff.** The package's change touches nothing under `python/corpus-structure/src/`.
That is read at review, not linted (AGENTS.md: no new alignment linting). A core edit the toy pack
needs is a P0CL-07 finding against the package that owns that code, recorded in coordinator §11.

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
| P0-C-1 | `consolidate/`: `run_pass`, the pool, entities and statements, claims, keys, fusion, alternatives, evidence, values once per pass, M19 at finalize, statuses, the writer, invariants, the pass report (§3.1–§3.8) | F4, S2, I1a, I2a, A0, O0, F3 (coordinator §7) | On renditions built by P0-I-1a and `fixtures/s0` batches located by P0-A-0, the trace units' entities, statements, claims and bindings match `fixtures/trace` by locator and structure, with D1 §11's invariants. Repeating a pass gives identical rows. Each §3.4–§3.5 case holds: author and synthesized `proves` fuse; a hedge disagreement gives two `ambiguous` members; two validity intervals give two claims; a cycle is dropped and counted; a rule error rejects; a warning writes one `refuted` observation; a reference-run alias match keeps its key | T3's batch with `c_proves` and the profile's synthesized `proves` give two claims (the structural statement rule is missing); or T2's "location parameter of the normal distribution" and another unit's "location parameter" with one identity give two rows and a `UNIQUE (run_id, key)` violation (identity keyed by label) |
| P0-C-2 | `serve/`: protocol, registry, run selector, journeys and page tokens, coverage, generic queries, `explain`, result models; `domains/statistics/queries.py`; `cli/query.py`, `cli/explain.py` (§3.9–§3.13) | C1; O1 for coverage integration | The trace questions answer over a C1-built run. A run with `skipped(scope)` units reports partial coverage. A promotion between two pages leaves the token's run unchanged. A bumped query version refuses the token. An unfinished run is refused. `ci query --json` equals the API's model. `find` uses the partial BM25 index (`EXPLAIN`) | `family_profile(normal)` over a run whose other units were skipped reports complete coverage; or the second page after a promotion returns the new run's rows |
| P0-C-3 | `tests/acceptance/test_trace.py` and the submission harness (§3.14) | A1, C2, F3, O2 | Passes on two consecutive invocations with identical results; run 1's coverage is unchanged after submission; the reverse-order project gives equal knowledge and packet hashes | A fixture sentence that does not map into the served packet fails, naming it; a rerun that creates new M24 tasks instead of reusing them fails the reuse assertion |
| P0-C-4 | the toy pack (§3.15) | C1, C2, S1, S2, I1b, A1, O2 | The toy run answers through the generic and plug-in queries with coverage; two intervals, two cited sources and two same-named organizations stay apart; the change touches nothing under `python/corpus-structure/src/` | A generic module that names a statistics class or predicate, or expects `unit` segments, fails on the toy run |

**P0-C-1: mechanisms and records.**

- **Mechanisms:**
  - SQLAlchemy Core over a borrowed connection;
  - psycopg binary COPY with `Copy.set_types`, through P0-F-4 (store note §3);
  - `nextval` pre-allocation (store note §3);
  - P0-F-4's `unnest` span upsert (store note §2);
  - rule-engine views and rules through P0-S-2 (D2 §7.4);
  - the Lark grammar through P0-I-2a (D4 M11).
- **Records:**
  - `s6.keys` and `s6.restated`: statement-key agreement under locator anchors. If they contradict
    STMT-01, D1 changes before C1 relies on it.
  - `s6.volume`: COPY of 20,000 claims.
  - `s6.dry-run`: trace rows against the compiled schema.
  - `s6.constraints`: what 0001 enforces, and what the invariant assertions must carry.
  - `s5.keys-property`: through F2a's frozen token form.
  - `s4.rules`: `views:` on the pack, through P0-S-2.

**P0-C-2: mechanisms and records.**

- **Mechanisms:**
  - JSONB comparators and the recursive CTE (store note §2; SQLAlchemy Core);
  - pg_textsearch BM25 with the named partial index (D3 §5, [overview](../../libraries/postgresql-18-pg-textsearch.md)
    §3.3);
  - Pydantic result models;
  - Typer groups with `--json` (interfaces note §3).
- **Records:**
  - `s6.queries`: the D3 §9 and D8 §5.3 queries and their corrections;
  - `s6.bm25`: syntax and the planner's use of the partial index.

**P0-C-3: mechanisms and records.**

- **Mechanisms:**
  - FastMCP `Client(mcp)` in process, one session-scoped fixture (interfaces note §1.6, Tested);
  - Typer `CliRunner` (interfaces note §3, Tested);
  - the anyio or pytest-asyncio plugin, whichever foundations' conftest selects.
- **Records:** `s0r2.reference-v1`, through P0-F-3.

**P0-C-4: mechanisms and records.** Nothing beyond C1–C3.

## 6. Tests

| Package | What the tests establish | Shared fixtures used | Thin fixtures added here |
|---|---|---|---|
| P0-C-1 | The trace through D5 row 0: targets by locator and structure; invariants. Rebuild idempotence. Order independence over shuffled observation order. Each fusion, alternative, cycle, orphaned-premise, coarse-evidence, M19 and linking case of §3.3–§3.5, on small hand-made pools. An invariant violation injected below the checks rolls back with its keys. A proposal stored on one rendition and consolidated on a content-different rendition (an edit elsewhere on the page) is located on the run's rendition, and statements away from the edit keep their keys | F1's per-session test database and compiled schema; F3's `fixtures/s0` and `fixtures/trace` | `pool_run`: a run with renditions written from P0-I-1a's output through P0-F-4's repository, ingest tasks so that `kb.run_rendition` resolves, and proposal observations from P0-A-0's stored forms under synthetic M24 tasks |
| P0-C-2 | The registry refuses malformed plug-ins. Selector, journey, token and stale-token behaviour. Coverage counts as of `finished_at` over task rows written directly. Each generic query and each statistics query over a C1-built trace run against `fixtures/trace` expectations. `find` with `EXPLAIN` showing the partial index. CLI output equal to the API's model, with refusals as non-zero exits | as C1 | `finished_runs`: two finished runs built by `pool_run`, with the promoted pointer set and moved by the test |
| P0-C-3 | The decision 8 journey (§3.14) | F1's conftest; F3; A1's app factory | `trace_project`; a session-scoped `mcp_client` |
| P0-C-4 | The toy journey (§3.15) | as C3 | `toy_project` |

Expected values come from `fixtures/trace` and the hand-made pools, never from a C1 run. Validators
P0-S-2 owns are called as validators, not re-tested here. Corpus-gated tests skip when the corpus
is absent (D9 §4). The tests run under `--strict-markers --strict-config`.

## 7. Indicative size

| Part | Product lines (tests excluded) |
|---|---|
| P0-C-1 `consolidate/` | about 780 (pool 120, entities and statements 180, claims and fusion 200, finalize 100, writer 120, report and invariants 60) |
| P0-C-2 `serve/` and `cli/` | about 620 (protocol and registry 80, selector and tokens 100, coverage 50, generic queries 220, `explain` 90, CLI 80) |
| P0-C-2 `domains/statistics/queries.py` | about 300 |
| P0-C-4 `domains/toy/queries.py` | about 60 (the rest of the pack is data) |
| **Total** | about 1,760, against the coordinator's 1,900 (§8); `extref` resolution is not built here (§1) |

The acceptance harness is test code and is not counted.

## 8. Choices left to implementation

- The module split inside `consolidate/` and `serve/`, and the names of the pass report's fields.
- How the pool holds segments: per rendition, or per page.
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
- **The three trace pages for C3.** The corpus is gitignored. Proposed: P0-F-3 vendors their
  original bytes under `fixtures/trace/` with a corpus index, credited under CC BY 2.0, so the gate
  test never skips. Until then it skips with its reason, and qualification needs a non-skipped run.
- **The submission harness.** If P0-E-2b runs live-run answers outside pytest, the harness becomes
  an application function in `intervene`, owned by agent interface.
- **`kb.entity_mention` for proposal-derived entities.** D3 §5 says "mention observations". Phase 0
  records the proposal observations instead. Design owner: confirm the column's wording.
