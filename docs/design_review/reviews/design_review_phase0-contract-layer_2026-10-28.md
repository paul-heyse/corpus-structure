# Design review: phase 0 contract layer (design/target, holistic and library-targeted)

**Reviewer:** fresh `design-reviewer` subagent (Claude), 2026-10-28, read-only; published by the
coordinator without change to its judgment. **Baseline:** `7e3dc23` on `main`, plus `9797921`
(test mechanisms only). **Decision: Revise.**

## Summary

Phase 0 builds the walking skeleton. The meta-model lives in PostgreSQL. Ingest is profile-driven
HTML. Opus extracts claims through a recorded queue. Consolidation turns observations into per-run
knowledge. Typed queries answer from the database. Evaluation scores runs against goldens that
Sonnet re-authors. Most of the contract layer is strong and should survive unchanged:

- the single claim form with typed condition trees and escape leaves;
- methods write observations, and only consolidation writes knowledge, materialized per run;
- the token-form key rule (keys never depend on parser coverage);
- the PostgreSQL queue with `SKIP LOCKED` claiming and `attempt` fencing;
- one packet format and one validation authority (Pydantic) across tiers;
- model-facing and stored batch forms joined by a recorded quote cascade;
- the blind Sonnet golden protocol with a reserved example page.

The contract layer is **not yet ready for the foundations package to write keys**. Four structural
causes need revision first:

1. **Identity and reuse follow physical provenance, not content.** Every segment, statement,
   local-entity and claim key inherits the rendition key. The rendition key hashes the adapter
   configuration, which includes the spaCy version. Reuse digests name upstream task ids. So any
   ingest change re-keys the whole corpus, orphans judgments, detaches goldens from runs, and either
   re-asks the agent for every packet or reuses observations that point at another rendition's rows
   (P0CL-01, -02, -03). The design owner's own principle (keys come from a total, deterministic
   normalization of the written form, not from mechanism versions; rationale §4.5) applies to
   structure as much as to formulas.
2. **Some inputs are neither fixed nor recorded.** Packets include "known entities … proposed
   earlier in this run". Consolidation reads the mutable promoted-run pointer. Neither is fixed when
   the task is created (which is when reuse is resolved), and `ops.run` records neither (P0CL-05).
3. **Phase 0 scope and the gate are not yet coherent.** "Dev pages only" removes almost nothing
   from about 3,600 agent packets under D7's split rule, and the policy cannot express it. The gate
   has no pre-registered readings, yet promotion makes the run the permanent identity reference.
   Served answers carry no coverage, although the promoted run is partial by construction (P0CL-09,
   -10, -11, -12).
4. **The seven-document split has hidden prerequisites and two cycles**, and several statistics-
   and Siegrist-specific rules sit in core packages that §1.3 says must hold nothing
   domain-specific (P0CL-07, -08).

All four can be corrected before drafting, mostly by moving decisions to their semantic owners
rather than adding machinery. **Decision: Revise.** The architecture is accepted for the named
strengths, but the identity/reuse contract, phase 0 scope and dependency structure must be revised
before P0-F2 (keys) and the supporting documents are drafted.

## 1. Scope, outcome and coverage

| Field | Value |
|---|---|
| Subject | Phase 0 contract layer: `docs/plans/phase-0_2026-10-28.md` (§1, §3–§8, §12); DESIGN §1 (incl. §1.3) and §2 (§B1–§B6); ADR-0012 (with its 2026-10-28 amendment) and ADR-0013–0018; the D1–D9 sections amended in `dcb728a`, plus adjacent consumers. Baseline commit `7e3dc23` on `main`. Intervening commit `9797921` was inspected: it adds test mechanisms only (Hypothesis stateful and grammar-generated tests, hypothesis-jsonschema) to D9 §2/§4 and the coordinator §6, and changes no contract (confirmed by the coordinator). Untracked operator overviews `docs/libraries/{html5lib,pgevector,ppi_py,vllm,hypothesis,jsonschema}.md` were available but are not part of the subject |
| Standard | Core design principles and template 3.3 with efficient-architecture heuristics 1.0; code-intelligence profile 1.4 (CI-01–CI-13, CI-G1–CI-G3), read with "code" as "documents": attributed facts, fidelity, unknown ≠ absent, evidence closure, non-circular evaluation and pinned serving apply directly; corpus-structure binding |
| Tier · purpose | Design · target (binding cadence: before a substantial stage) |
| Focus | Combined holistic and library-targeted (operator, 2026-10-28) |
| Audit prerequisite | Not applicable. ADR-0007's audit refresh has nothing to audit: no production code exists. No audit revision was consumed |
| Reviewer · date | Fresh `design-reviewer` subagent (Claude), 2026-10-28; read-only |
| Maturity and outcome | Design accepted in part (ADR-0013–0015 accepted; 0016–0018 proposed until S4/S6), nothing built. This review should shape the seven supporting documents before drafting, and decide what F2 may freeze |
| Supported scope | Phase 0 run flow (coordinator §5); shared contracts (§4); the phase 0 gate (D7 §9); the typed queries D8 §5.1–§5.3; adjacent consumers in phases 1–2 where phase 0 contracts bind them |
| Workload premise | 78 first-pass pages, about 2,479 units and 28,956 math spans (record `s1.corpus`); about 3,600 non-test packets (D6 §7.4); 10⁵ observations and 10⁴–10⁵ claims per run (D3 §11). One operator; one workstation with one RTX 5090 (unused in phase 0); local PostgreSQL 18.6 with 3.3 GB free disk (coordinator §2). The agent tier is Opus in Claude Code sessions (minutes per packet); goldens are about 80 units × 3 Sonnet passes. The run waits across sessions |
| Expected changes | DESIGN §1.3 generality checks (second domain pack; table quantities with units; `valid_time` and attribution; email segment kinds; or/not conditions); phase 1 additions (GLiNER2 tier; local LLM with structured output; embeddings); ingest changes during phase 0 (ports, a spaCy bump, profile fixes) |
| Method and coverage | Static inspection of documents, the cited evidence sections, the research notes' relevant sections and the S4/S6 plans. One Context7 lookup (PostgreSQL 18 text search, 2026-10-28). No probes. Not examined in depth: D2 §9–§10 statistics schema and guideline text, `trace.md`, spike code, the S5 plan, the library overviews beyond cited sections |

## 2. Responsibilities, dependencies and semantic ownership

| Component (coordinator doc) | Responsibility and hidden decisions | Consumer contract | Dependency direction | Expected reason for change |
|---|---|---|---|---|
| `core` (Foundations) | D1 shapes, canonical JSON, keys, `core/tex.py`; D3 metadata, migration 0001, repository, bulk writes; fixtures | Frozen Pydantic types; keys; repository API | depends on nothing (decision 13) | Key rules (frozen once written), new value kinds |
| `schema` (+ `validate` M19 runner) (Schema and rules) | LinkML loading; compilers; batch models per predicate; rule compilation; view builder | Compiled artifacts per schema version; one claim view at two call sites | `core ← schema`; D9 places `validate` above `consolidate` (see P0CL-08) | Pack edits; LinkML/rule-engine upgrades |
| `ingest` (Ingest and math) | M01 profile-driven HTML, M02, M03 b′; grammar, M09, M11 (grammar part), M13; standing context | Renditions, segments, sentences, macro tables; values; standing-context function | `core ← ingest` | Profile edits, spaCy/model bumps, grammar extensions (S5) |
| `orchestrate` (Orchestration) | Project init, registry, runs, tasks, leases, reuse, stages, policies, slices, barrier | Task lifecycle; `input_hash`; run states | above consolidate/validate | Stage graph per phase; policies |
| `intervene`, `methods/llm` (Agent interface) | MCP tools, packets, caps, prompts, quote cascade, M24; golden server | Packets; parse to stored form; submission validation | top tier (IE-7) | Tool caps; tiers |
| `consolidate`, `serve` (Consolidation and queries) | Phase 0 realization (D5 §11 row 0); `extref`; typed queries; acceptance test | Per-run knowledge; query result models | `consolidate ← serve` | Phase 1 slots, linking, confidence |
| `evaluate` (Evaluation and goldens) | Split, sampler, golden authoring, alignment, scores, digest | Golden sets; scores with intervals | top tier | Guideline/schema versions; witnesses |

| Phenomenon or concept | Authority and identity | Revision boundary | Derived forms and consumers |
|---|---|---|---|
| Document, rendition | D1 §3.1, §10.1: `doc` over (project, uri, content hash); `ren` over (doc, **adapter config hash**) | New adapter config means a new rendition | Segments, spans, every downstream key (P0CL-01) |
| Segment, statement, local entity | `seg` (ren, kind, start, end); `stm` (anchor seg + first-sentence ordinal); local `ent` (type, scope seg, symbol) | Inherit rendition | Claim keys; golden units; slices use **locators** instead (rationale §4.6) |
| Claim | `clm` (subject, predicate, object/canonical value, identity qualifiers) | Per run; immutable once finished | Queries, alignment, judgments |
| Value canonical form | D1 §6.2 token form (ADR-0012) | Fixed before first keys | Keys; fusion |
| Domain vocabulary | LinkML pack (ADR-0017, proposed) | Schema version = canonical JSON hash | Compiled artifacts (P0CL-15) |
| D1 shapes | Hand-written Pydantic; `core.yaml` mirror by contract test | Core version | Batch models, JSON Schemas, annotator reference |
| Locator | D6 §8 grammar; **no owner** (P0CL-04) | none declared | Slices, fixtures, `statement(locator)`, `extref`, query evidence locators |
| Reference run | "the promoted run" (D5 §1, D4 §4.1, M14); **not recorded on the run** (P0CL-05) | Mutable `meta.project.promoted_run_id` | Known entities, linking, consolidation identity |

**Fact and fidelity table (profile):**

| Fact family | Provider and revision | Fidelity | Coverage and unknowns | Identity | Consumers |
|---|---|---|---|---|---|
| Rendition, segments, sentences | M01+M03 by adapter config | extracted | `parse_status` partial/failed with reason (good) | rendition-scoped (P0CL-01) | everything |
| Math values, symbol occurrences | grammar (M11/M09), SymPy pinned | derived; `parse` ok/partial/failed; `ambiguous` | per-span status; coverage per page | token form (stable) | keys, packets, M13 |
| Scope (binding sites) | M13 rules | derived (rule heuristic) | `binding: unresolved` explicit | observation | standing context (phase 0), consolidation (phase 1) |
| Claim proposals | M24 (Opus), config hash | inferred (agent) | `empty` outcome recorded; unlocated quotes flagged; `rejected` items kept | observation per task | consolidation |
| Claims | M17/M18 per run | derived | units without a proposal task have **no recorded fate** (P0CL-11) | `clm` per run | queries, eval |
| Verifications | M19 rules | derived | `not_applicable` counted | targets claim key | finalize |
| Golden items | Sonnet A/B/C, guideline version | reference (adjudicated) | `stale` on rule/schema change; **not on rendition change** (P0CL-03) | local refs on a rendition | alignment |

## 3. Contracts, constraints and testing boundaries

What holds: D1 INV-01–INV-10, enforced at write by consolidation (D5 §8.3); absence states typed
per D1 §8.3; outcomes `produced`/`empty`/`failed` per unit (D4 §1 rule 2); the submission contract
with per-item paths and one resubmission (D8 §2.1); M01's refusal of a profile that does not
compile; rules that fail compilation on a type error (D2 §7.4). Consolidation steps run over an
in-memory pool and can be tested without the database (D5 §1). These are good local-reasoning
boundaries.

What does not yet hold, examined in §7:

- the equivalence level of keys (DP-04): byte-identical adapter config, rather than content (P0CL-01);
- the reuse key's basis: task ids and unit text, rather than the content of what was read (P0CL-02);
- which form of an authored batch is the authority (P0CL-03);
- the citation frame (`sN`/`cN`) as a contract shared by packets, the cascade, fixtures and goldens
  (P0CL-03);
- the input set of a packet and of consolidation (P0CL-05);
- coverage semantics of served answers (P0CL-11).

## 4. Composition and execution

| Stage (phase 0) | Semantic in/out | Owning mechanism | Reuse boundary | Effects and publication | Limits and determinism |
|---|---|---|---|---|---|
| ingest | bytes → rendition, segments, sentences | M01/M03 per document | adapter config (P0CL-01) | rows written outside observations (M01/M03 only) | deterministic; html5lib holds the GIL, so processes |
| normalize | math segment → value | M11 grammar, **one task per math segment** | per-span digest (P0CL-02, -13) | `value` observations | Earley; `setitimer` timeout, main thread only (P0CL-14) |
| scope | rendition → `scope` | M13 | task id | observations | deterministic |
| propose | unit → batch | M24 via MCP; policy `propose.phase0.agent_all` | packet digest (P0CL-05) | observation + intervention + `NOTIFY` in one transaction | agent; caps in characters |
| assemble / finalize | observations → knowledge | M17/M18, rebuild per pass | not cached | delete+insert per run, one transaction | pure function, except the reference-run input (P0CL-05) |
| check | candidate claims → `verification` | M19, **one task per claim** | claim key + view digest (P0CL-13) | observations between two rebuilds | deterministic |
| evaluate | run claims × goldens → scores | alignment, bootstrap | — | `eval.*` per run | seeded; unit order recorded |
| golden run | units → passes A/B/C | golden server per subagent | — | `eval.golden_pass` | pass-C task creation owner unstated (Observation 8) |

**Analysis record (profile), for the projections served in phase 0:**

| Question | Projection | Method | Exact/heuristic | Budgets and partial results | Evidence linkage |
|---|---|---|---|---|---|
| `statement`, `family_profile`, `transformations_of` | claims of one run, by status and modality defaults | SQL (D3 §9) | exact over the run's claims | paginated with page tokens; **no coverage statement** (P0CL-11) | keys and evidence locators per row; keys are per run (P0CL-11) |
| `relations_between` | `special_case_of`/`transformation_of`/`limit_of` paths | recursive CTE, depth ≤ 4 | exact within the requested bound, if labelled as a requested bound (CI-08) | depth bound only; frontier unbounded, though small at this scale | claim keys |
| `find` | segments of block kinds | built-in FTS, `ts_rank_cd` | heuristic ranking | paginated | segment locators; **which rendition's segments** needs the run→rendition mapping (Observation 2) |

## 5. Change and failure scenarios

| Scenario (kind) | Owner | Contract change | Observed affected consumers | Independent edits / hidden knowledge | Settling evidence |
|---|---|---|---|---|---|
| **A second domain pack** (domain extension) | pack | none intended | `consolidate` binding rules name statistics predicates (D5 §4 rules 2–4); the rule view's built-in `family_params` (D5 §8.2); `details` → `core:proves` synthesis (D5 §3.5); statistics queries in `serve/` (D8 §5.2, D9 §1); source profiles in the domain pack (D2 §12.1) | core code edits per domain | P0CL-07 |
| **Table segment with quantities and units** (new representation) | core values; M01/M12 | `number` canonical form; gauge basis; `cmp` operands are formulas only (D1 §7) | keys of number-valued claims; conditions over facts | basis carried in a unit string | P0CL-06; Condition widening is additive and legitimately core |
| **Claim with `valid_time` and attribution** (domain concept) | D1 keys | identity qualifiers | two validity intervals in one statement fuse into one claim (D5 §5.3) | — | P0CL-06 |
| **Email thread segment kinds** (new source) | ingest, D1 segment kinds | kinds list (CHECK in 0001; one-line migration); document relations (thread, quoted-from) absent; quoted text inflates independent support | `ingest.email`; source profile location | profile lives in the domain pack | additive except profile location (P0CL-07); support independence is phase 5 |
| **Rule with or/not conditions** (composition) | D1 §7, rule-engine | none: `and`/`or`/`not` exist; canonicalization flattens and sorts; z3 in phase 2 | value-typed `cmp`/`pred` args for "evaluable against facts" | — | accommodated additively |
| **GLiNER2 tier** (mechanism addition) | methods, compilers | new compiled artifact; local-entity scope source moves from proposal `extent` to M13 (D5 §11) | keys of locally-scoped claims move at the phase boundary | — | accepted as a real re-derivation once documented; compiled-artifact identity is P0CL-15 |
| **Local LLM with structured output** (mechanism substitution) | M10 | decoding form separate from validation form (D2 §7.3) | same packet; same Pydantic authority | — | contracts hold, provided the digest rule of P0CL-02/-05 also covers M10 |
| **Embeddings** (extension) | M04, `kb.embedding` | rows "keyed by the target's stable key" (D3 §5) | needs stable segment keys | dev-golden example retrieval | P0CL-01, P0CL-16 |
| **Ingest change mid-phase-0** (mechanism change: spaCy patch, profile fix, M01 version) | ingest | new rendition | every segment, statement, local-entity and claim key; goldens bound to old rows; every agent task's digest | spike-era fixtures already route around it by locator | P0CL-01–03 |
| **First pass across sessions; workstation restart during the barrier** (failure/growth) | orchestration | — | a long-lived `ci run`; ~3,600 packets | — | P0CL-09, P0CL-12 |
| **Pathological formula at submission** (failure) | agent interface, grammar | — | MCP worker thread without a timeout | — | P0CL-14 |
| Journey: trace a served claim across a promotion | serve | page tokens and keys | `promoted` re-resolved per call | — | P0CL-11 |
| Journey: empty answer over unextracted pages | serve | coverage | test pages and unrouted units | — | P0CL-11 |
| Journey: evaluation run | evaluate | — | phase 0 passes (reserved examples; blind passes); phase 1 dev-golden examples do not | — | P0CL-16 |

## 6. Correctness and fidelity gates

| Gate | Verdict | Own evidence | Required action |
|---|---|---|---|
| G1 Authority | **fail** (narrow) | Packet cap held twice: `agent.opus … packet_cap_tokens: 6000` (D2 §12.1) and the tool caps "6,000 tokens" counted as characters (D8 §3). The locator contract has no owner while four documents resolve locators (P0CL-04) | P0CL-04, P0CL-05 |
| G2 Semantic fidelity | **fail** | `valid_time` is not an identity qualifier (D1 §10.1), so distinct facts fuse (D5 §5.3). Fusion has no rule for disagreeing non-identity qualifiers. Number basis is not representable (D1 §6) | P0CL-06 |
| G3 Validity | pass (Proposed) | INV checks at write; submission validation per item; profile and rule compile failures | — |
| G4 Hidden behaviour | **fail** | Consolidation and packet assembly read the mutable promoted pointer and in-run proposals, neither recorded (D5 §1, D4 §4.1, D3 §4) | P0CL-05 |
| G5 Consistency and recovery | **fail** | Partial runs are served without coverage; page tokens bind to `promoted`, not to a run (D8 §3, §5). Orchestrator resume across sessions is unspecified (unresolved part) | P0CL-11, P0CL-12 |
| G6 Transformation and reuse | **fail** | Digests over task ids and unit text (D4 §1 rule 4, D6 §4) either over-invalidate agent work or reuse observations that cite another rendition's rows. Known entities cannot be in a digest computed at creation | P0CL-02, P0CL-05 |
| G7 Truthful capability claims | **fail** | The coordinator §12 mitigation ("dev pages only") for ~3,600 packets has no effect under D7 §3.1's split. The completion boundary claims a first pass with no credible route | P0CL-09 |
| G8 Library leverage | pass | Generic capability comes from libraries throughout (queue SQL, rule-engine, LinkML+Pydantic, Lark, cssselect2, spaCy, rapidfuzz/regex, SciPy); the bespoke parts (claiming statement, cascade, view builder) are small and justified | Observations 1, 3 |
| CI-G1 Fidelity | **fail** | Typed answers over a run with unextracted test pages and unrouted units read as complete (CI-04) | P0CL-11 |
| CI-G2 Evidence closure | unresolved | Within a run, claims cite spans and observations of that run. Under P0CL-02's text-only digest variant, reused observations would cite spans of a rendition the run did not select | P0CL-02 |
| CI-G3 Evaluation integrity | pass for phase 0; **unresolved** for the phase 1 contract | Phase 0 prompts use the reserved page's worked examples. D4 §4.2's phase 1 examples come from dev goldens without self/page exclusion | P0CL-16 |

## 7. Findings

### Index

| ID | Finding (short) | Principles · gate/judgment | Priority · prerequisite of |
|---|---|---|---|
| P0CL-01 | Keys inherit the adapter configuration, not content | DP-04, DP-09, FP-04 · G6, A1, A2 | High · P0-F2 |
| P0CL-02 | Reuse digests follow task ids and unit text | DP-09, H13 · G6, CI-G2, A4 | High · P0-O1 |
| P0CL-03 | Authored batches are kept only in located form; the citation frame is unrecorded | DP-01, DP-04 · G6, A2 | High · P0-F3, E docs, A1 |
| P0CL-04 | The locator contract has no owner | DP-01, FP-01 · G1 | Medium · F2/F3/O2/C2 |
| P0CL-05 | Packet and consolidation inputs are neither fixed nor recorded; packet ownership is split | DP-09, DP-21, CI-10 · G4, G6, G1 | High · O1, A1, C1 |
| P0CL-06 | Decisions for §1.3 constructs are missing before keys freeze | DP-02, DP-04, DP-05 · G2, A2 | Medium-high · P0-F2 |
| P0CL-07 | Statistics and Siegrist semantics in core packages | FP-04, DP-01, DP-17 · A1, A2, A3 | Medium-high · S2, C1, C2 |
| P0CL-08 | Dependency graph: hidden prerequisites, two cycles, a layering conflict | FP-01, DP-17 · A1, A3 | High · all seven documents |
| P0CL-09 | Phase 0 coverage is inconsistent; the agent workload has no credible route | FP-07, DP-08, H11 · A4, G7 | High · phase 0 completion |
| P0CL-10 | The gate has no pre-registered readings while promotion fixes identity | CI-12, DP-22 · A2 | Medium · E docs, O2 |
| P0CL-11 | Typed answers carry no coverage; `promoted` is not pinned across a journey | CI-04, CI-13, DP-19 · CI-G1, G5 | Medium-high · C2, A1 (query tool) |
| P0CL-12 | The multi-session barrier relies on a long-lived orchestrator without durable stage or resume | DP-19, H24, H25 · G5, A4 | Medium · O1/O2 |
| P0CL-13 | M19 runs as per-claim tasks between two rebuilds; M09/M11 per span | FP-07, H2, DP-10 · A4 | Medium-low · O1, S2, C1 |
| P0CL-14 | The grammar's timeout mechanism does not work in MCP worker threads | DP-15, DP-20 · G5 | Medium · S2, A1, A2 |
| P0CL-15 | Compiled artifacts are identified by source content only | DP-01, DP-09 · G6 | Medium-low · S1, F4 |
| P0CL-16 | Split roles in phase 1 contracts (dev examples; test excluded from agent routing) | CI-12, CI-06 · CI-G3 | Medium · E docs (contract now) |

### Identity and reuse follow physical provenance (P0CL-01, -02, -03, -04)

**P0CL-01. Keys inherit the adapter configuration, not content.**

*Diagnosis.* D1 §10.1 builds every downstream key on the rendition key:

- rendition `ren` = (document key, adapter config hash);
- segment = (rendition key, kind, start, end);
- statement = (anchor segment key, first-sentence ordinal);
- local entity = (type, scope segment key, symbol);
- claim = (subject key, predicate, object, identity qualifiers including `statement`).

M03's configuration (spaCy version, model package and version, excluded components) is part of the
adapter configuration (D4 M03), and D1 §3.2 confirms "their keys still differ when their adapter
configurations do".

So a spaCy patch bump, any M01 version bump or a profile fix produces a new rendition and new keys
for nearly every claim in the corpus, even when the canonical text, segments and sentences are
content-identical. D1 §3.2 already defines that equivalence and S1 tested it.

*Consequences:*

- "A key identifies the same meaning across runs, which is how runs are compared, judgments carried
  forward and claims diffed" (D1 §10.2) fails at every ingest change.
- Judgments are orphaned (D5 §7.3).
- Golden unit sampling order changes, because it is `sha256(unit_key + seed)` (D7 §3.1).
- `kb.embedding` rows "keyed by the target's stable key" (D3 §5) have no stable key.
- Phase 0 makes these changes routinely: M01, M03 and M13 are ported during the phase.

The design already routes around the defect for slices (rationale §4.6), fixtures (coordinator
decision 6) and the acceptance test (D9 §4). It has not drawn the consequence for keys, goldens or
reuse. This is the A1 and A2 violation of the review: semantic identity, physical realization and
build provenance are one digest (DP-04).

*Correction (owner: foundations for keys, ingest and math for renditions; decide before P0-F2):*

1. **Content-addressed renditions.** Rendition identity = (document key, digest of the
   content-identity relation of D1 §3.2: canonical text, segment kinds, offsets, non-diagnostic
   attrs, tree, sentences). Adapter configurations map many-to-one onto a rendition in a provenance
   relation that carries `parse_detail` and the config id. A content-preserving change then keeps
   every row and key; ingest still runs M01 (milliseconds per page) and deduplicates by content.
2. **Locator-anchored identity for statements and scopes.** Statement key = (document key, anchor
   locator, first-sentence ordinal). Local-entity key = (type, scope locator, symbol). The locator
   is the D6 §8 form, author id first, text prefix otherwise, with a uniqueness rule (P0CL-04).
   Segment keys stay physical. A genuine content edit elsewhere on a page then no longer moves the
   keys of unrelated statements, whose offsets shift.

*Challenge case.* Two paragraphs with the same opening text: the locator rule must choose a unique
prefix or add an ordinal. That is a deterministic function of the content, and it fails loudly
(D6 §8 already refuses an ambiguous locator).

*Alternatives:*

- (a) Step 1 only. It removes spurious churn but keeps offset-driven churn within an edited page.
- (b) Freeze the adapter configuration for phase 0 (a `docs/pins.md` hold on spaCy and the model,
  and a profile freeze beside the schema/guideline freeze of D7 §9), plus a locator-based
  key-migration mapping at each change. It costs a migration path and recurring operator work.

Recommended: steps 1 and 2 together, because P0-F2 freezes the key function.

*Closure.* The D1 §10.1 key table is restated. Property tests show two content-identical renditions
from different adapter configs giving identical claim keys, and an edit to one paragraph leaving
other statements' keys unchanged.

*Disposition.* Design-phase plan findings table (a D1 contract), with a dependency note in
coordinator §11.

**P0CL-02. Reuse digests follow task ids and unit text.**

*Diagnosis.* D4 §1 rule 4 and D6 §4 key reuse on "unit text, upstream observations read (by task
id), compiled artifacts, prompt parts, model revision". Two consequences follow:

- **Over-invalidation where it is costly.** M24's digest includes the M13 and M03 task ids, so
  re-running an upstream method with identical output (a new rendition, `--fresh`, a version bump)
  re-requests every agent packet: thousands of Opus interactions, with no change to what the agent
  would see. H13 asks for exactly the opposite: stop propagation when the recomputed value is
  substitutable.
- **Unsoundness where digests are text-only.** For span-level methods (M11 per math segment), a
  digest over the unit's text matches across renditions, so a new run reuses observations whose
  `segment_id`/`span_id` point at the old rendition. Consolidation would then cite spans outside the
  run's selected rendition (CI-11, INV-10). Neither variant is acceptable, and the design does not
  say which applies.

*Correction (owner: orchestration for the digest rule, each method for its digest):*

- digest the **content** of what is read: payload hashes of upstream observations, the canonical
  text of the unit, and for M24/M10 the hash of the assembled packet text plus prompt-part hashes
  and model id;
- with P0CL-01's content-addressed renditions, reuse across content-identical renditions is then
  sound, because the rows are shared;
- keep task ids as provenance (`reused_task_id`), not as dependency.

*Challenge.* An upstream method whose payload is identical but whose semantics changed (a version
bump with the same output) is correctly reused: the consumer read the same content.

*Closure.* The D6 §4 rule is restated. A test: re-running M13 with identical output leaves M24 tasks
`reused`; a new content-identical rendition reuses every task.

*Disposition.* Coordinator §11 (orchestration), with a design-phase row for D4 §1/D6 §4.

**P0CL-03. Authored batches are kept only in located form; the citation frame is unrecorded.**

*Diagnosis.* Golden passes and items store the **stored** (offset) form on a specific rendition
(`eval.golden_pass.batch`, `eval.golden_item.payload`, `eval.golden_unit.rendition_id/segment_id`;
D7 §3.1 "a golden unit is one annotation unit of one rendition"). The authored artifact, however, is
the model-facing batch (sentence id plus quote). D7 §3.5 marks units stale on rule and schema
changes only, never on a rendition change. D7 §5.1's predicted set ("claims whose primary evidence
lies in the unit's segment") compares a run's segments with the golden's segments. After any
rendition change, recall silently drops towards zero for affected units, or a mapping must be
invented.

The same pattern affects fixtures (decision 6). Their `sN`/`cN` citations are packet-relative. `cN`
depends on production M13 reproducing the spike's standing-context choice and order, and the quote
cascade's fallback ("then in the unit") cannot find a context sentence outside the unit. F3 is
marked "can start now" (coordinator §7), but its validity depends on I1, I2 and the cascade.

*Correction (owner: evaluation and goldens for goldens; foundations for fixtures; agent interface
for proposals):*

- Make the authored model-facing batch, plus its **citation frame**, the authority. The citation
  frame maps each `sN`/`cN` to the cited sentence's locator and text.
- Derive the stored form per rendition by the production cascade. This is decision 6 generalized to
  goldens, fixtures and agent proposals.
- Golden unit identity is its locator-based key (P0CL-01); `golden_item` is a derived projection.
- Treat a rendition whose citation frame no longer resolves as a staleness trigger (re-locate, else
  re-author).

*Closure.* A golden authored on rendition R1 aligns unchanged against a run on a content-identical
R2, and against a run on an R3 with an edit elsewhere on the page.

*Disposition.* Design-phase plan (D3 eval DDL, D7 §3, §5.1).

**P0CL-04. The locator contract has no owner.**

*Diagnosis.* The locator grammar is stated in D6 §8 and consumed by:

- slices (orchestration);
- fixtures (decision 6, foundations);
- `statement(locator)` and evidence locators in query results (D8 §5);
- `extref` targets (OPEN-D1-5, consolidation);
- P0CL-01's remedy.

The coordinator §4 table has no row for it. Several documents would each implement resolution and
uniqueness, which can disagree (G1).

*Correction.* One owner: ingest and math. It holds the locator grammar, a resolver over a
rendition's segments, a generator (shortest unique prefix, or author id), and uniqueness and refusal
semantics, as a `core`-level function over segments so foundations can key on it. Add a §4 row.

*Closure.* §4 row added; one resolver used by slices, fixtures, queries and `extref`.

*Disposition.* Coordinator §11.

### Inputs that are neither fixed nor recorded (P0CL-05)

**P0CL-05. Packet and consolidation inputs; packet ownership.**

*Diagnosis:*

- **Known entities.** D4 §4.1: "canonical labels of global entities in the reference run, **or
  proposed earlier in this run**". Reuse is resolved at task creation (D3 §8), and all `propose`
  tasks are created at once. A packet that includes this run's earlier proposals cannot be known
  when its digest is computed. It therefore depends on the order in which the session works the
  queue, so the run cannot be reproduced and the reused result no longer matches its key (DP-09,
  CI-10).
- **Reference run.** D5 §1 makes consolidation a pure function of, among others, "the reference run
  (the promoted run)". M14 and known entities use it too. `ops.run` has no reference-run column
  (D3 §4). The result therefore depends on a mutable pointer at execution time (G4).
- **Split ownership of the packet.** The packet is assembled by agent interface, its standing
  context comes from ingest and math, its known entities from consolidation tables, and its cap from
  `methods.yaml` (`packet_cap_tokens`, D2 §12.1) and from tool constants counted in characters at 3
  per token (D8 §3). Its digest is used by orchestration. M24's method definition (`input_digest`,
  `select`) has no named owner.

*Correction:*

1. `ops.run.reference_run_id`, set at run creation and immutable; consolidation, M14 and packet
   assembly read only it. At bootstrap it is null.
2. Known entities come from the recorded reference run only. At bootstrap, optionally, add a
   deterministic page-level list available at creation (dfn terms and page title from author
   markup, which M01 records).
3. Agent interface owns M24's method definition and the packet as a pure function of recorded
   inputs. Caps are part of M24's configuration (one authority, one unit: characters, stated as
   such). The MCP tool only paginates the parts the assembler produced. The task records the served
   packet's hash.

*Alternative.* Resolve agent reuse lazily at lease time against the served packet. This keeps
in-run known entities, but the run is still not reproducible; not recommended.

*Challenge.* At bootstrap with no known entities, cross-unit label consistency rests on Opus and
label normalization (D5 §3.3 point 5). That is the honest state, and P0CL-10 makes it visible.

*Closure.* D4 §4.1 and D5 §1 restated. A test: two runs over the same inputs, with the queue worked
in different orders, give identical packets and identical knowledge.

*Disposition.* Design-phase plan (D4/D5), coordinator §11 (A1, O1).

### Generality and pre-key semantics (P0CL-06, -07)

**P0CL-06. Decisions for §1.3 constructs are missing before keys freeze.**

*Diagnosis.* F2 writes canonical forms and keys first, and D1 §6.2 says rules that move keys must be
settled before production keys exist. Four §1.3 constructs fail that test:

- **`valid_time` is not an identity qualifier** (D1 §10.1 lists modality, polarity, statement,
  conditions and schema-listed ones). "ORG-101 owns P-17" for two intervals in one table statement
  keys identically and fuses (D5 §5.3), so the second interval is lost (G2).
- **Attribution** identity is undecided ("attribution phrasing" is excluded, but whether the
  attributed entity changes meaning under `cited` is not stated).
- **Numbers.** "normalized decimal strings with pint base units" (D1 §6.2) leaves several things
  undefined: precision ("300" vs "300.0"), exponent form, and converting a stated unit away from its
  source. Gauge/absolute basis (kPa(g)) is not a pint unit, so it would ride inside a unit string
  (DP-02).
- **Fusion** unions supports and evidence but has no rule when fused candidates disagree on
  non-identity qualifiers (`hedge`, `attribution`, `scope`, and `valid_time` today).

*Correction (owner: foundations, under D1):*

- make `valid_time` a core identity qualifier;
- make the attributed entity an identity qualifier when modality is `cited` (or record why not);
- give `number` a typed `{v, unit, basis?}` with a declared decimal canonicalization (no
  trailing-zero or exponent ambiguity; keep the stated unit; compare converted values only in
  evaluation);
- in D5 §5.3, candidates that agree on the key but disagree on a meaning-bearing non-identity
  qualifier become alternatives, or that qualifier becomes identity.

Widening `cmp`/`pred` operands to typed values for "conditions evaluable against facts" is additive
and can wait.

*Closure.* D1 §5.2, §6, §6.2 and §10.1 restated. Hypothesis properties cover number
canonicalization. A §1.3 fixture pair (two validity intervals) stays two claims.

*Disposition.* Design-phase plan.

**P0CL-07. Statistics and Siegrist semantics in core packages.**

*Diagnosis.* Coordinator §1 requires that "nothing in `core`, `schema`, `consolidate`, `orchestrate`,
`evaluate` or `serve` may assume statistics". The following do:

- D1 §6.1 defines `param_of` as "the value given to parameter `param` in the referenced
  `has_distribution` claim", and `family_param` presupposes `FamilyParameter`; both live in the core
  `BindKind`/`SymbolBinding`.
- D5 §4 rules 2–4 enumerate statistics predicates by name (`has_parameter`, `parameter_domain`, …,
  `has_distribution`).
- D5 §8.2 builds `claim.family_params` into the core rule view. A second domain's cross-claim rule
  therefore needs Python in the view builder.
- D5 §3.5 synthesizes `proof core:proves unit-statement` from a `details` block inside a unit, a
  Siegrist convention in consolidation.
- D8 §5.2's statistics queries go into `serve/` (D9 §1), and P0-C2 builds them now for the
  acceptance test.
- Source profiles live in the domain pack's `methods.yaml` (D2 §12.1). D4 M01 itself says "it is
  about the source's HTML, not the domain". A second domain over the same source duplicates the
  profile, and a second source within statistics edits the domain pack. If the whole
  `source_profiles` map enters `ingest.html`'s config hash, adding a profile re-keys every rendition
  (P0CL-01).

*Correction (owners as named):*

- **schema and rules:** generic binding kinds (`param_of` = "value of entry `param` of the map
  qualifier `q` of the referenced claim"), with the qualifier named by a pack annotation
  (`ci:param_map`); the family-structure predicate set as a pack `subset`; a declarative `views:`
  section in `rules.yaml` (source predicate, match, projected field) compiled by the generic
  builder, so `family_params` becomes pack data;
- **source profile:** statement synthesis from containment declared in the profile (`details_kinds`
  already exists; add the synthesized relation there);
- **consolidation and queries:** domain queries as a pack plug-in (`domains/<name>/queries.py`
  implementing a `serve` protocol, as `verifiers.py` does for `validate`); generic queries stay in
  `serve`;
- **foundations and ingest:** source profiles in their own location (`sources/<profile>.yaml`),
  referenced by name from the pack, hashing only the resolved profile.

*Closure.* A second toy pack (for example the §1.3 ownership example) compiles and runs the generic
stages with no edit to the core packages.

*Disposition.* Design-phase plan (D1/D2/D5/D8), coordinator §11 for C2 placement.

### Dependency structure (P0CL-08)

**P0CL-08. Dependency graph: hidden prerequisites, two cycles, a layering conflict.**

*Diagnosis (coordinator §7 against decisions 2, 3, 5, 6 and D7/D8).*

Missing prerequisites:

- **A1 → S2.** `propose_claims` runs M19 and the `guideline:` rules at submission (decision 3,
  D8 §2.1), but A1 lists only O1, S1, I1 and I2.
- **A2 → alignment.** `read_golden_unit` for pass C returns the A/B alignment diff (D8 §2.2,
  D7 §3.3–§3.4), but A2 lists A1 and E1 only.
- **E2 conflates two consumers.** Golden-vs-golden alignment needs only core claim sets and value
  equivalence. Run-vs-golden scoring needs C1. Lumping them makes E3 (dev goldens, on the gate's
  critical path) wait on consolidation.
- **C1 → parse.** C1's acceptance builds stored-form proposals from `fixtures/s0` through the
  production cascade (decision 6; D9 P0.8 depends on P0.7). The cascade is bundled into A1.
- **F3's validity** needs I1, I2 and the cascade (P0CL-03).

Cycles:

- **A1 ↔ C1.** Packets read known entities from consolidated tables (P0CL-05), while consolidation
  consumes A1's parse output.
- **S2 ↔ C1.** The finalize-site claim view is built over the assembled candidate pool, C1's
  representation, while C1 needs S2.

Layering conflict: D9 §1 orders `consolidate ← validate`, so `validate` imports `consolidate`. But
the M19 runner and view builder are owned by schema and rules (P0.4 puts the runner in `validate/`)
and must be built before C1.

*Correction:*

- a separate early package **P0-A0, parse**: the quote cascade as a pure function (rendition text
  and citation frame + model-facing batch → stored batch), needing F2, `core/tex.py` and I1;
- **E2a**, alignment over two core claim sets with value equivalence (needs F2 and I2's grammar
  transformer), feeding A2; **E2b**, run scoring (needs C1);
- define the **keyed candidate claim** as an F2 core type, so the view builder consumes only core
  types (batch and candidate pool both adapt into it), which breaks S2↔C1;
- known entities from the recorded reference run (P0CL-05), which breaks A1↔C1;
- move the M19 runner and view builder below `consolidate` (`core ← schema ← validate ← …`) or into
  `schema`.

Add the edges A1→S2, A2→E2a, C1→A0 and F3-acceptance→I1/I2/A0.

*Closure.* The revised §7 graph is acyclic, with each edge stated through the capability it needs.

*Disposition.* Coordinator §11.

### Phase 0 scope, gate and serving (P0CL-09, -10, -11, -12)

**P0CL-09. Phase 0 coverage is inconsistent; the agent workload has no credible route.**

*Diagnosis:*

- D7 §3.1 assigns every fifth page per chapter to test and the rest to dev, apart from the reserved
  page(s). "Dev pages" is therefore nearly "all non-test".
- D6 §7.4 counts "about 3,600 non-test packets", which "exceed what sessions should carry", yet
  decision 9 and coordinator §12 handle that risk with "dev pages only". The mitigation removes
  almost nothing.
- The policy `propose.phase0.agent_all` (`unit.split != 'test'`) admits reserved and unassigned
  pages.
- D6 §7.4 says `propose` agent tasks are bounded by run scope, not budget, so no mechanism creates
  the promised `skipped(budget)` tasks.

The completion boundary ("the first first-pass run over the dev pages completes and is promoted")
therefore asks the agent tier for thousands of session interactions before any cheaper tier exists.
This is a predictable failure of the supported workload (A4, H11), and an unbacked claim about the
risk handling (G7).

*Correction (owner: coordinator decision 9; orchestration for the expression).* Declare the phase 0
first-pass as a slice that the evaluation plan determines: the pages holding dev golden units, the
forced-dev pages and the trace/core pages. That is what the gate, D7 §7's experiments ("the dev
golden units") and the reference-run bootstrap need. Express it as run scope, and record other
eligible units as `skipped(scope)` so their fate is explicit (P0CL-11).

The full first-pass then becomes a phase 1 run with M10. Alternatively, keep it as an explicitly
unbounded, best-effort background run outside the gate.

*Challenge.* Fewer extracted pages means fewer global entities in the bootstrap reference run.
Acceptable: phase 1's M14 links against it and adds the rest; the identity reading (P0CL-10) shows
the gap.

*Closure.* Decision 9, D6 §7.4–§7.5 and coordinator §1/§12 restated, with the packet count of the
declared slice stated.

*Disposition.* Coordinator §11, plus design-phase rows for D6/D7.

**P0CL-10. The gate has no pre-registered readings while promotion fixes identity.**

*Diagnosis:*

- The phase 0 gate (D7 §9) is integration-shaped: tests pass, runs "answer their typed questions",
  `ci eval` produces scores. No reading is fixed before results are seen (CI-12: "success criteria
  are written before the evaluation runs").
- Yet promotion (D7 §7 item 5) makes the run the experiment baseline and the identity reference. A
  global entity linked to it "keeps that entity's key and canonical label" (D1 §10.1, D5 §3.3
  point 3), so phase 0's label choices persist.
- The roadmap names cross-unit identity as the likely first large error source (phase 2 risk).
- "Live runs answer their typed questions" has no expected-answer contract outside the
  deterministic test.
- D7 §3.1's sampler does not force trace units into the dev golden set (D9 P0.10 does).

*Correction (owner: evaluation and goldens; operator act at `ci promote`):*

- pre-register the readings shown at promotion: dev full-tier F1 with interval beside the S0-R2
  figures, identity B-cubed against golden canonical labels, unlocated-quote and rule-warning rates;
- define "answers" for live runs as alignment of the typed-query rows to the golden-derived
  expectation;
- state unit-level forcing in D7 §3.1;
- optionally, until the phase 2 identity gate, linking reuses keys but not canonical labels from the
  reference run.

*Closure.* D7 §9 row 0 and §7 item 5 restated.

*Disposition.* Design-phase plan.

**P0CL-11. Typed answers carry no coverage; `promoted` is not pinned across a journey.**

*Diagnosis:*

- **No coverage.** D6 §1 promises every unit's fate is recorded, but a policy chain that matches no
  entry creates no task, so test-page units and any unrouted unit have no fate. D8 §5 queries over
  the promoted run return claims with no statement of what was not extracted. In phase 0 the
  promoted run is partial by construction (test pages, and the slice of P0CL-09). An empty or short
  `family_profile` is then read as absence (CI-04, CI-G1).
- **No pin.** `query` paginates with page tokens (D8 §2.4, §3), and `promoted` is re-resolved per
  call. A promotion between pages, or an `explain claim KEY` after it, resolves keys under another
  run (keys are unique per run, D3), which mixes realizations (CI-13, G5).

*Correction (owner: consolidation and queries, orchestration):*

- record a fate for every eligible unit, as a task with `skipped(reason)` or a coverage measurement
  per run;
- every query result carries the run id it was served from and coverage for its scope (units
  extracted / skipped by reason / failed);
- resolve `promoted` once per journey, bind page tokens, returned keys and `explain` references to
  the run id and query version, and refuse a stale token.

*Closure.* A query test over a run with skipped pages reports partial coverage. A promotion between
pages leaves the token's run unchanged.

*Disposition.* Design-phase plan (D8 §5), coordinator §11.

**P0CL-12. The multi-session barrier relies on a long-lived orchestrator without durable stage or
resume.**

*Diagnosis.* With `agent_mode: wait` the run sits at the `propose` barrier across sessions (D6 §2,
§7.4), and `ci run` owns the orchestrator process (decision 4). `ops.run` records status and
iteration but not the current stage (D3 §4), and no resume contract exists. A restart or crash
during a multi-day wait leaves recovery undefined (DP-19). Meanwhile `agent_mode: complete` plus
reuse already gives a simpler route: decision 8 uses it for the acceptance test.

*Correction (owner: orchestration).* Make the phase 0 first-pass protocol a sequence of `complete`
runs. Each reuses every finished task (cheap under P0CL-02) and is a coherent finished snapshot;
promote the one with no unresolved agent tasks. Reserve `wait` for short slice runs. If `wait` stays
for long runs, add a durable stage to `ops.run` and `ci run --resume RUN`.

*Closure.* D6 §2/§7.4 restated. A test kills the orchestrator mid-barrier and resumes, or the
complete-run sequence is shown to converge.

*Disposition.* Coordinator §11.

### Library composition and execution fit (P0CL-13, -14, -15)

**P0CL-13. M19 runs as per-claim tasks between two rebuilds; M09/M11 per span.**

*Diagnosis:*

- M19's unit is `claim` (D4 §3). The `check` stage runs over "candidate claims (by key)" between the
  assemble and finalize rebuilds (D5 §1, D6 §2). Checks are cached "by claim key plus the digest of
  the claim view" (D6 §4).
- That is tens of thousands of task rows per pass, each with a view digest. The digest needs pool
  facts (`family_params`, flattened conditions), which are rebuilt outside consolidation, although
  "the view builder reads the pool once" (D5 §8.2).
- M19 is microseconds of rule evaluation, so the task, digest and transaction machinery dominate the
  work (H2, DP-10).
- M09 and M11 per math segment (about 29k each per run) repeat the pattern at smaller cost.

*Correction (owners: schema and rules, consolidation, orchestration):*

- run finalize-site M19 as one run-level task inside the consolidation pass over its in-memory pool,
  writing `verification` observations in bulk;
- keep separate tasks only for expensive checks (M20 z3, M21 simulation; phases 2 and 4);
- make M09/M11 per-rendition tasks with per-span observations (reuse at page grain is sufficient).

*Challenge.* Per-claim caching of M19 saves nothing, because consolidation is rebuilt every pass
anyway (D5 §1).

*Closure.* D4 §3/D6 §2 restated; task counts per run stated qualitatively.

*Disposition.* Coordinator §11.

**P0CL-14. The grammar's timeout mechanism does not work in MCP worker threads.**

*Diagnosis.* Lark has no deadline, so D4 M11 bounds a parse with a `signal.setitimer` timer that
works "only in a process's main thread", and runs grammar work in single-threaded worker processes.
FastMCP sync tools run on worker threads (Tested, interfaces note P1; D8 §1).

Submission-time `guideline:` rules include "a formula excludes the variable it defines" (D2 §7.4),
which needs formula symbols. ADR-0012 makes the one grammar the reader of symbols. The MCP and
golden servers would then parse untrusted formulas in a thread where the timeout cannot fire
(DP-20).

*Correction (owner: schema and rules, with agent interface), one of:*

- (a) submission-time views read symbols with the total, fast TeX tokenizer (`core/tex.py`), and
  grammar-dependent rules declare `at: [finalize]`;
- (b) the servers call the grammar through a small process pool with kill-on-timeout.

(a) is simpler and keeps the servers thin.

*Closure.* The view contract states its reader per call site; a test submits a pathological formula.

*Disposition.* Coordinator §11.

**P0CL-15. Compiled artifacts are identified by source content only.**

*Diagnosis.* `meta.schema_version` is unique by (project, content hash of the sources) and stores
`compiled` artifacts (D3 §3). `ci ingest`/`ci run` upsert by content hash (D8 §4). A compiler fix
(frequent while S1/S2 are drafted before S4 reports) yields different artifacts for the same row.
Either the stored artifacts go stale or the row mutates under runs that used the old ones. Method
config hashes keep the artifact hashes, so provenance survives, but the artifacts do not.

*Correction (owner: schema and rules, foundations):* key stored artifacts by (schema content hash,
compiler id and version), in a child table; or store only hashes and rebuild deterministically
(D2 §7.4 already rebuilds rules and "never pickles").

*Disposition.* Coordinator §11.

### Evaluation roles (P0CL-16)

**P0CL-16. Split roles in phase 1 contracts.**

*Diagnosis:*

- **Dev examples.** D4 §4.2's phase 1 prompts retrieve "k adjudicated dev-split golden units nearest
  to the unit by M04 embedding" with no self or same-page exclusion. Experiments "decide on dev"
  (D7 §4, §7). A candidate can be scored on goldens it was shown: its own unit, or a page whose units
  share running examples (OPEN-D7-3). That is CI-12's reference-into-input path.
- **Test exclusion.** D7 §4 item 4 excludes test units from agent routing through the policy symbol
  `unit.split` (D6 §7.2), so test scores measure the system without its agent tier while the
  deployed system escalates. The likely concern, agent output on test pages training phase 3
  adapters, is a training-data rule, not a routing rule.

*Correction (owner: evaluation and goldens):*

- example retrieval excludes the unit's own page; alternatively, partition dev pages into an example
  pool and an evaluation pool;
- either let test units route to the agent while excluding test pages from every training, fitting
  and example set, or keep the exclusion and label test scores "pipeline without agent", relying on
  the PPI audit for deployed quality.

The routing symbol enters phase 0's policy context, so decide now.

*Disposition.* Design-phase plan.

### Observations (not actionable findings)

1. **The `core.yaml` mirror** duplicates the core shapes at field level, held by a contract test
   (G1 pass: a reconciliation protocol exists). Its consumers need class names and descriptions
   (predicate ranges, schema tables), while shape detail comes from Pydantic. A name-level mirror
   would cut machinery (DP-16).
2. **Run → rendition mapping** is implicit: a join through ingest tasks; `corpus_hash` is only a
   hash. `find` and the evaluation predicted set need an explicit view, like `kb.run_observation`.
3. **Canonical JSON.** State the rules (reject floats in key parts; Python `sort_keys` orders by code
   point, not RFC 8785 UTF-16 order), or adopt RFC 8785 with NFC as a pre-step.
4. **Full-text search** hard-codes `'english'` in a stored generated column. A per-row `regconfig`
   column (`to_tsvector(cfg, text)`) is supported for expression indexes (Documented, PostgreSQL 18
   §12.2.2, via Context7 2026-10-28) and avoids a table rewrite for a second language.
5. **M02 token counts** use the served model's tokenizer before S3 chooses the model (OPEN-D4-1).
   Phase 0 has no LLM-tier consumer, so characters would suffice until M10.
6. **Golden item versions.** `eval.result` references a golden set but not the pass-C versions
   scored. Re-authoring replaces items, so results cannot be tied to the items they used (matters
   after the phase 0 freeze).
7. **Inconsistencies:** the `gaps` chain (ADR-0018) is absent from the `ops.policy_rule.chain` CHECK;
   D4 §11 says phase 0 has "no fusion" while D5 §11 has canonical-form fusion; the
   observations-only contract lists two owners (coordinator §4) without dividing them.
8. **Golden-run task creation.** Who creates pass-C tasks ("when passes a and b are both written",
   D3 §8) is unstated: `write_golden` in its transaction, or a `ci golden` command. The two-process
   decision assigns orchestration logic to `ci run`.
9. **Golden independence premise.** Pass separation rests on Claude Code's documented
   one-server-per-invocation behaviour for inline agent servers, not observed end to end (interfaces
   note §1.7). A cheap probe at A2 settles it.

## 8. Library fit and total complexity

| Capability and owner | Mechanism (selected) | Semantic fit and gaps | Burden | Verdict |
|---|---|---|---|---|
| Task queue (orchestration) | One `UPDATE … FROM (SELECT … FOR UPDATE SKIP LOCKED)` taking expired leases; `attempt` fencing; partial indexes; `LISTEN`/`NOTIFY` as hints (store note L-S1, D6 §3) | Exact fit. A queue library (procrastinate, pgqueuer) would be a second authority over `ops.task` | small | keep; S6 step 7b settles concurrency |
| Reuse (orchestration) | `INSERT … SELECT … LEFT JOIN LATERAL` over `task_cache` | Mechanism sound; the key basis is wrong (P0CL-02) | small | keep the mechanism, change the digest |
| D1 shapes and batches (foundations, schema) | Frozen Pydantic, `TypeAliasType` `Condition`, `create_model` per predicate, `TypeAdapter` per form, custom `GenerateJsonSchema` (schema-rules note L-01–L-03, Tested by probe) | Strong; `gen-pydantic` correctly rejected | mirror (Observation 1) | keep |
| Rules and policies (schema) | rule-engine 5.1 typed contexts, `$all`/`&.`/`??`, `Chain`, rejected nondeterministic builtins | Good. No recursion or joins, so the view builder precomputes; domain facts must become pack data (P0CL-07) | small | keep; add `views:` |
| Math (ingest) | Lark Earley over SymPy's grammar with `%extend`, `edit_terminals`, `ordered_sets`, per-process parsers; `setitimer` timeout | Good; the timeout composes badly with threaded hosts (P0CL-14) | moderate (SymPy hold) | keep; fix the call-site reader |
| HTML (ingest) | html5lib via `lxml.html.html5parser` (`namespaceHTMLElements=False`), cssselect2 `Matcher` as the one role engine, `regex` named-list delimiters with timeout | Strong, Tested on 78 pages. html5lib 1.1 (2020) is a maintenance risk, contained by pin and profile tests | small | keep |
| Sentences and binders (ingest) | spaCy Doc from words and spaces, `nlp.pipe`; `Matcher`/`PhraseMatcher` | Strong (b′ F1 1.00) | small | keep; note the M03 config inside the rendition key (P0CL-01) |
| Quote location (agent interface) | regex exact/spacing/macro steps; rapidfuzz `partial_ratio_alignment` + `Levenshtein.opcodes` over token sequences; `BESTMATCH` refine with timeout | Strong; the real test is S3's quotes. Should be its own early package (P0CL-08) | small | keep; relocate |
| MCP (agent interface) | FastMCP 4.1 lifespan pool, sync tools, `ToolResult` text packets, loose batch parameter, golden server per subagent | Good; the separation premise is not observed (Observation 9) | small | keep; probe at A2 |
| Scoring (evaluation) | `linear_sum_assignment(maximize=True)` with masking before assignment; `scipy.stats.bootstrap` percentile, recorded unit order | Strong (IE-5, IE-6) | small | keep |
| Lexical search (consolidation/queries) | built-in FTS, partial GIN on block kinds | Adequate for `find`; per-row language config advisable (Observation 4) | small | keep |

No mechanism is misused in a way that breaks a contract by itself. The defects are in what the
composed mechanisms are keyed on (P0CL-01/-02/-15), where they run (P0CL-13/-14), and whether a
premise is established: S3's model choice for M02 tokenization, and Claude Code's inline-server
behaviour.

## 9. Alternatives and tradeoffs (the two decisions that matter most)

**Identity and reuse:**

| Alternative | Change propagation | Authority and composition | Machinery and risk | Decision |
|---|---|---|---|---|
| Current: rendition = (doc, adapter config); digests by task id | every ingest change re-keys the corpus and re-asks the agent | slices, fixtures and goldens each route around keys | recurring operator and agent cost; silent evaluation breakage | reject |
| Proposed: content-addressed renditions + locator anchors + content digests | only real content changes move keys, and only locally | locators get one owner (P0CL-04); authored batches are the authority (P0CL-03) | one provenance relation; a locator generator | recommend |
| Simplest viable: freeze adapter config and pins for phase 0; locator-based key migration at each change | contained within phase 0, recurs after | migration mapping as a second mechanism | operator work at each change | fallback if RC01 is declined |

**Phase 0 first pass:**

| Alternative | Workload | Gate and experiments | Decision |
|---|---|---|---|
| Current: dev split (≈ all non-test, ~3,600 packets) under `wait` | not credible before cheaper tiers | over-served | reject |
| Golden-pages slice under successive `complete` runs | hundreds of packets, at a granularity sessions can carry | fully served (D7 §7 scope = dev golden units) | recommend |
| Trace and spike pages only; full first pass in phase 1 | smallest | gate served; the reference run is thin | acceptable variant |

## 10. Verification and uncertainty

| Claim or scenario | Evidence label and date | Basis | Gap |
|---|---|---|---|
| Keys move with adapter config (P0CL-01) | Proposed design, statically established 2026-10-28 | D1 §3.2, §10.1; D4 M03; rationale §4.6 | — |
| Dev split ≈ all non-test (P0CL-09) | static, 2026-10-28 | D7 §3.1 vs D6 §7.4 | exact dev packet count not recomputed |
| FastMCP tools run on worker threads | Tested (interfaces note P1, 2026-10-28) | research note | — |
| Lark timeout needs the main thread | stated in D4 M11 | Python signal semantics | not probed |
| PostgreSQL FTS config per row | Documented (PostgreSQL 18 §12.2.2, Context7, 2026-10-28) | primary documentation | — |
| Golden subagent separation | Documented, not observed | interfaces note §1.7 | probe at A2 |
| All mechanism claims in D-sections | as labelled there | not re-verified | — |

**Uncertainties that could change the verdict:**

- If the operator prefers freezing the adapter configuration (the fallback in §9), P0CL-01 narrows
  to a migration obligation, but P0CL-02 and P0CL-03 still stand.
- If "dev pages" was meant as the golden-unit pages, P0CL-09 reduces to restating decision 9 and the
  policy.

**Unexamined breadth (not defects):** the statistics schema and guideline content, `trace.md`, spike
code, S5.

## 11. Authority changes (rule impacts) and dispositions

Each rule change takes effect only after the operator confirms it in plan creation.

| ID | Rule and location | Proposed change | Findings | If kept |
|---|---|---|---|---|
| review#RC01 | D1 §10.1 key table; D1 §3.2 ("keys still differ when adapter configurations do"); ADR-0013 Decision "Keys" clause (accepted: supersede or amend by new ADR); rationale §4.6 | Content-addressed renditions; locator-anchored statement and scope keys | P0CL-01 | Freeze adapter config for phase 0 and add a key-migration mapping |
| review#RC02 | D4 §1 rule 4; D6 §4 "(by task id)" | Content digests; M24/M10 digest = packet hash | P0CL-02 | Include the rendition key in digests; accept agent re-requests on ingest change |
| review#RC03 | D3 `eval.golden_unit/golden_pass/golden_item`; D7 §3.1, §3.5, §5.1; coordinator decision 6 | Authored model-facing batch + citation frame as the authority; stored form derived per rendition | P0CL-03 | Freeze renditions while goldens exist |
| review#RC04 | D4 §4.1 known entities "or proposed earlier in this run"; D5 §1 reference run; D3 `ops.run` | Recorded `reference_run_id`; known entities from it only; packet owned by agent interface; one cap authority | P0CL-05 | Lazy reuse at lease time; non-reproducible runs stated |
| review#RC05 | Coordinator decision 9, §1, §12; D6 §7.4–§7.5; D0 phase row 0; D9 §5 goal | Phase 0 first pass = golden-pages slice; full first pass in phase 1 | P0CL-09 | State the ~3,600-packet workload and its session plan explicitly |
| review#RC06 | D7 §9 row 0; D7 §7 item 5; D1 §10.1 / D5 §3.3 label stickiness | Pre-registered promotion readings; optional label non-stickiness until phase 2 | P0CL-10 | Promotion without readings, recorded as such |
| review#RC07 | D1 §5.2, §6, §6.2, §10.1; D5 §5.3 | `valid_time` (and cited attribution) as identity; typed number with basis and decimal rule; fusion rule for qualifier disagreement | P0CL-06 | Key migration when phase 5 needs them |
| review#RC08 | D1 §6.1 `BindKind`; D5 §3.5, §4, §8.2; D8 §5.2 with D9 §1 `serve/`; D2 §2/§12.1 and D4 M01 profile location | Pack-declared binding semantics and views; profile-declared statement synthesis; domain query plug-ins; sources outside packs | P0CL-07 | Record each as a known core dependency on statistics, revisited at phase 5 |
| review#RC09 | D9 §1 dependency direction; coordinator §7 graph; decisions 2–3 placement | A0 parse package; E2a/E2b split; core keyed-candidate type; `validate` below `consolidate` | P0CL-08 | Sequence S2 after C1 types; accept the cycles as co-development |
| review#RC10 | D4 §3 M19 unit; D6 §2 check stage; D6 §4 check caching | Run-level M19 inside consolidation; per-rendition M09/M11 | P0CL-13 | Per-item tasks kept, stated as a measured choice later |
| review#RC11 | D7 §4 item 4; D6 §7.2 `unit.split` in routing; D4 §4.2 examples | Training-data rule instead of routing exclusion (or labelled test scores); page-exclusive example retrieval | P0CL-16 | Label test scores "pipeline without agent" |
| review#RC12 | D3 `meta.schema_version.compiled`; D8 §4 upsert by content hash | Artifact identity includes compiler version, or hashes only | P0CL-15 | Recompile in place, with stale-artifact risk stated |
| review#RC13 | D6 §2 `wait` for long runs; coordinator decision 4 scope | Successive `complete` runs for the first pass, or a durable stage with resume | P0CL-12 | Specify `--resume` |
| review#RC14 | Coordinator §4 table | Add a locator row (owner: ingest and math); split observations-only ownership | P0CL-04 | — |

**Dispositions.** Per the operator's ownership decision (2026-10-28), D-contract findings (P0CL-01,
-03, -05, -06, -07, -10, -11, -16) go to the **design-phase plan's findings table**. Build-series
findings (P0CL-04, -08, -09, -12, -13, -14, -15, and the build halves of -02 and -05) go to
**coordinator §11**. Coordinator §9 says this review's findings are dispositioned in §11, while §11
says design findings stay in the design-phase table; the coordinator should confirm the split.

## 12. Architectural judgment and decision

| Judgment | Verdict | Scenario evidence and scope | Required action |
|---|---|---|---|
| A1 Localize change | **violated** | Ingest changes propagate to every key, golden and agent task (P0CL-01–03); domain additions need core edits (P0CL-07) | RC01–RC03, RC08 |
| A2 Encode domain meaning explicitly | **violated** | The identity model conflates semantic identity with physical provenance (P0CL-01); `valid_time`, attribution and number semantics are unsettled before keys (P0CL-06); domain semantics in core (P0CL-07). The claim/condition/observation model itself is adequate and governs behaviour where specified | RC01, RC07, RC08 |
| A3 Extend through composition | **unresolved** | Strong primitives (one claim form, one packet, one rule engine, one queue); package composition has cycles and conflations (P0CL-08) and a check stage outside its pool (P0CL-13) | RC09, RC10 |
| A4 Fit execution to the supported workload | **violated** | The phase 0 first pass asks the agent tier for ~3,600 packets with an ineffective mitigation (P0CL-09); agent re-requests on any upstream re-execution (P0CL-02); resume unresolved (P0CL-12). Deterministic stages fit comfortably at this scale | RC05, RC02, RC13 |

**Bounded decision: Revise.** Accepted for named scenarios, at Proposed strength:

- the claim form and condition tree (ADR-0013 apart from its keys clause);
- observations versus knowledge, per run (ADR-0014);
- the recorded agent queue (ADR-0015);
- the token-form rule (ADR-0012);
- PostgreSQL as one authority with the queue mechanics (ADR-0016, pending S6);
- the LinkML-vocabulary/Pydantic-shape split (ADR-0017, pending S4);
- policy chains (ADR-0018, pending S4);
- the M01–M03, M09/M11/M13 realizations;
- the golden protocol.

**Enclosing architecture: needs revision** on identity and reuse, packet inputs, phase 0 scope and
the gate, and package structure, before P0-F2 writes keys and before the seven documents are
drafted. This is not release qualification.

**Priority and prerequisite order:**

| Order | Change and responsible owner | Findings | Closure evidence |
|---|---|---|---|
| 1 | Key semantics (foundations, D1): content-addressed renditions, locator anchors with an owner, §1.3 identity qualifiers and number form | P0CL-01, -04, -06 | Restated D1 §10.1; key property tests |
| 2 | Reuse and inputs (orchestration, agent interface): content digests, recorded reference run, packet ownership | P0CL-02, -05 | Order-independence and reuse tests |
| 3 | Package graph (coordinator): A0, E2a/E2b, core candidate type, layering | P0CL-08 | Acyclic revised §7 |
| 4 | Phase 0 scope, gate and serving (coordinator, D6/D7/D8) | P0CL-09, -10, -11, -12 | Restated decision 9, D7 §9, D8 §5 |
| 5 | Generality moves (schema and rules, consolidation, queries) | P0CL-07 | Toy second pack runs with no core edit |
| 6 | Execution placement (S2, C1, O1, A1) and artifact identity | P0CL-13, -14, -15 | Restated D4/D6; submission timeout test |
| 7 | Phase 1 evaluation contract (evaluation) | P0CL-16 | Restated D7 §4, D4 §4.2 |

**Next consequential decision:** the operator's confirmation of RC01 (identity basis) and RC05
(phase 0 first-pass scope) in plan creation. Both determine what P0-F2 freezes and whether the
phase 0 completion boundary is achievable. Owner: the design authority, through the coordinator.

**Evidence limits.** This was a static review of documents at `7e3dc23`, plus `9797921` (test
mechanisms only), on 2026-10-28. No probes were run and no code exists. Library facts are taken at
the strength the design and research notes label them, plus one Context7 confirmation. Workload
figures are the design's own (S1 counts; "about 3,600 non-test packets") and were not recomputed.
The concurrent S2, S3 and S7 plan drafts were out of scope.
