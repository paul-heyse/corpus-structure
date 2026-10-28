# Design phase plan

**Status:** Active; owns design findings, OPEN dispositions and the design queue, beside the [design-spikes series](design-spikes-s0-s1_2026-10-28.md) (spike execution) and the [phase 0 series](phase-0_2026-10-28.md) (the build) (operator decision, 2026-10-28). **Revised:** 2026-10-28.

## Purpose and boundary

Take the proposed design set ([docs/design](../design/README.md), D0–D9 and the trace) from
**Proposed** to **ready for the phase 0 build**: run the design spikes, deepen the library
realization of every method, dispose of every `OPEN-Dn-k` item, record the binding decisions as
ADRs, and replace this plan with the phase 0 build plan of [D9 §5](../design/D9-repository-and-phase0.md#5-phase-0-build-plan).

## Current state (2026-10-28)

| Item | State |
|---|---|
| D0–D9, trace | Written; **Proposed**, with S0/S1/S0-R2 results folded in (2026-10-28, ADR-0012–0011): labels mark what is Tested or Measured |
| Spike briefs S0–S7 | Written ([spike README](../design_review/evidence/2026-10-28_design-spikes/README.md)); S0, S1 and the S0-R2 revisit run and folded in (Q1, Q2, the S0/S1 part of Q5) |
| Library realization in D4 | First-pass realizations written by the design owner; not yet deepened against the library overviews |
| Code | None. The template's scripts and tests only |
| Fresh review | A fresh-eyes completeness review (2026-10-28; 37 findings: 2 blockers, 17 major, 18 minor) was folded into D1–D9, the trace and the S0, S1 and S6 briefs; none remains open |
| DESIGN §1, §2 | §1 objective and out-of-scope written (Proposed); §2 binding decisions wait for ADRs (Q8) |

## Lanes

| Lane | Who | Writes | Must not |
|---|---|---|---|
| Spikes | In-repo agent | `docs/design_review/evidence/2026-10-28_design-spikes/` (code, results, reports) | Edit D-documents or the trace; write under `python/` or `domains/` |
| Library leverage | Parallel in-repo agent | **Library realization** subsections of D4 cards; `> Library proposal (L-nn):` blocks; `docs/library_leverage/` accounts (§Library lane brief) | Change a contract (unit, inputs, outputs, configuration semantics) except through a proposal block |
| Design owner | The in-repo agent (primary design authority, operator direction 2026-10-28); the project-conversation Claude reviews for missing design reasoning | D-documents, trace, ADRs, this plan's findings and dispositions | — |
| Operator | Paul | Directions; approval of this plan's closure | — |

Handoffs: a spike report or a library proposal is input; the design owner folds it into the
D-documents and updates the findings rows below in the same commit, citing the report section
or proposal id.

## Execution queue

| # | Slice | Lane | Depends on | Done when |
|---|---|---|---|---|
| Q1 | S1 ingest and segmentation | Spikes | — | `S1-report.md` with `sample.json` |
| Q2 | S0 reference annotations | Spikes (Opus, then Haiku and Sonnet subagents; S0-R2) | S1 or raw text | `S0-report.md`; references adjudicated |
| Q3 | S4 LinkML compilation; S6 storage smoke | Spikes | — (S0 batches help S4) | Both reports |
| Q4 | Library pass 1: D4 cards, D2 §7 compilers, D3 extension use | Library leverage | — | Every D4 card's realization reviewed; proposals filed. **Phase 0 share done 2026-10-28** (four research folders `docs/design_review/evidence/2026-10-28_library-*`; realizations in D2–D4, D8); later-tier cards with the S2/S3/S5/S7 plans |
| Q5 | Fold-in 1: S1, S0, S4, S6, library pass 1 → D1, D2, D3, D4, trace | Design owner | Q1–Q4 | Findings rows for those OPEN items closed or re-scoped |
| Q6 | S2 GLiNER2.5; S3 local LLM; S5 math and verification | Spikes | Q1, Q2 | Three reports |
| Q7 | S7 embeddings and linking | Spikes | Q6 (S2) | Report |
| Q8 | Fold-in 2 → D4–D7; DESIGN §1 and §2; completeness review by a fresh reviewer. **ADRs written 2026-10-28** (operator decision): ADR-0013 claim model, ADR-0014 observations and run materialization, ADR-0015 agent queue (accepted); ADR-0016 PostgreSQL (after S6), ADR-0017 LinkML packs (after S4), ADR-0018 policy routing (after S4) proposed; DESIGN §2 §B1–§B6 | Design owner (the in-repo agent holds primary design authority from 2026-10-28) | Q5–Q7 | Every OPEN row disposed; the proposed ADRs accepted on their evidence and the design/target review |
| Q9 | Write the phase 0 build plan beside this one (operator decision 2026-10-28: plans are never deleted, three plans active) | Design owner | Step 0 decisions, the proposed ADRs | [Phase 0 series](phase-0_2026-10-28.md) and [phases 1–5 roadmap](roadmap-phases-1-5_2026-10-28.md) written 2026-10-28; this plan stays active for Q3–Q8 |

Q1–Q4 run in parallel where their dependencies allow. Q5 may start per spike as reports land.

Q1 and Q2 were executed in detail under the spike lane's
[S0/S1 execution plan](design-spikes-s0-s1_2026-10-28.md), now **complete** (2026-10-28): Q1 and Q2
are done, and Q5's S0/S1 part (with the S0-R2 revisit) is folded in; Q5's S4, S6 and library-pass parts
remain. By
operator decision (2026-10-28) more than one plan may be active; the plans are reconciled later.

## Library lane brief

**Goal.** For every method and compiler in the design, determine the best use of the chosen
libraries' features, at the versions in [D9 §2](../design/D9-repository-and-phase0.md#2-dependencies),
so that the build lane implements against verified library surfaces rather than assumptions.
The old repository failed partly by wrapping libraries in bespoke machinery; the aim here is the
opposite: use native features (constrained decoding, joint extraction, typed rule contexts,
chains, EM estimators, set operations, BM25 and vector indexes) wherever they do the job.

**Inputs.** The D-documents (D4 first, then D2 §7, D3, D5 §6 and §8, D6 §7, D7 §5), the
[library overviews](../libraries/README.md), library source at the pinned versions where an
overview is unclear. Context7 or upstream docs where the overview is silent.

**Scope, in priority order.**

1. D4 cards M05–M07 (GLiNER2.5: `extract`, `Classifier`, `JointIE`, batching, `extract_long`,
   precomputed states, LoRA adapters for phase 3).
2. D2 §7 compilers (LinkML `SchemaView`, generators; GLiNER2 `Schema.from_dict`; JSON Schema
   generation; rule-engine typed contexts and `Chain`).
3. D5 §6 confidence (pgmpy `DiscreteBayesianNetwork`, `DiscreteBayesianEstimator`, `DiscreteEM`,
   `VariableElimination`; scikit-learn calibration).
4. D4 M13, M14, M15, M22 (spaCy matchers and retokenization; RapidFuzz `process` and scorers;
   Splink 5 on DuckDB).
5. D4 M11, M20, M21 and D7 §5 (SymPy parsing, sets and `sympy.stats`; z3; SciPy distributions).
6. D3 (pgvector `halfvec` and HNSW options; pg_textsearch; psycopg COPY and pipelines;
   SQLAlchemy Core; Alembic).
7. D8 (FastMCP 4.1 tool definitions, validation errors, stdio; Typer and Rich).

**Output, per card or section.**

- Edit the card's **Library realization** subsection directly: exact classes, functions and
  parameters; the feature that does the work; version caveats; what to avoid and why.
- When the best use changes a contract (inputs, outputs, unit, configuration meaning) or adds or
  removes a method, write a block at the relevant place:

  ```text
  > Library proposal (L-07): Use JointIE's `return_lattice` scores as the relation confidence
  > source instead of the decoded score. Changes: D4 M07 payload (adds `lattice_score`), D5 §6.2
  > encoder source states. Evidence: gliner2.md §4.2; source gliner2/joint_ie/decode.py at 2.1.0.
  ```

  Number proposals `L-01`, `L-02`, … across the lane, and list each in the findings table below
  with disposition `open`.
- Record what was inspected (overview section, source file and version) in a short account under
  `docs/library_leverage/libraries/` per library, following the framework's collection-writing
  guidance; the codebase audit stage does not apply yet because there is no code, so the D4
  cards stand in for codebase opportunities.
- Flag anything a spike should measure rather than read, as a proposal naming the spike.

**Review.** The design owner checks each proposal against the vision in D0 (one claim model, meaning
in the schema, methods write observations, policies route on measurements, nothing enters
without a measured gap) and disposes of it in the findings table.

## Findings disposition

`OPEN-Dn-k` items are owned by their D-document's open-questions table; these rows schedule them.
Library proposals join as `L-nn` rows.

| Item | Component | Consequence and intended correction | Disposition · dependency | Closure check |
|---|---|---|---|---|
| OPEN-D1-1 | M03 sentences | Sentence splitting on math-dense prose; choose variant | closed · [S1 report](../design_review/evidence/2026-10-28_design-spikes/S1-report.md): b′ (inline math merged into one token), F1 1.0 vs 0.80; D4 M03 states it (2026-10-28) | D4 M03 states the chosen variant |
| OPEN-D1-2 | M13, D1 §4.2 | Section extent for variable scope | closed · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md): a `section` extent is needed (T1, T2, U12); D4 M13 binds section-wide and reopen phrases (ADR-0012 edit) (2026-10-28) | D1 §4.2 and D4 M13 updated |
| OPEN-D1-3 | D2 §9 FamilyParameter | Role names or symbols for parameter identity | closed · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md), guideline v1 §10.4: role word when the unit states one, else the symbol; rule reworded 2026-10-28 to the phrase that first names the parameter (review B2); parameterizations are OPEN-D2-18; confirmed at the next guideline-revision check | D2 §9, §10.4 updated |
| OPEN-D1-4 | D1 §5.2 `scope` qualifier | Section extent for standing assumptions | closed · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md): `section` under nested h3/h4 synthesis; `document` never needed (2026-10-28) | D1 §5.2 updated |
| OPEN-D2-1 | D2 §7.2 | `Schema.from_dict` keys | open · phase 1 (GLiNER2 compiler moved there); S4-D produces S2's dicts | D2 §7.2 example corrected |
| OPEN-D2-2 | M06, M07 | Raw or masked math | open · S2 | D4 M06 configuration fixed |
| OPEN-D2-3 | D2 §7.4, D5 §8.2 | rule-engine syntax; functions or resolver attributes | answered 2026-10-28 ([schema-rules note](../design_review/evidence/2026-10-28_library-schema-rules/README.md) L-04, L-05; D2 §7.4, D5 §8.2 updated) · S4-C confirms on the pack | S4 record `s4.rules` |
| OPEN-D2-4 | D2 §9 | Property predicates or `has_property` | closed · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md): keep property predicates; standard-deviation property is OPEN-D2-17 (2026-10-28) | D2 §9 decided |
| OPEN-D2-5 | D2 §9, §10.4 | Standard normal as family or parameterization | closed · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md): standardized families as families; guideline v1 §10.4 (2026-10-28) | D2 decided; direction logged if the operator chooses |
| OPEN-D2-6 | D2 §3 | List annotations round-trip | answered 2026-10-28 (schema-rules note L-06; D2 §3 updated) · S4-A confirms on the pack | S4 record `s4.pack-lint` |
| OPEN-D3-1 | D3 §5 | pg_textsearch BM25 syntax (source-read and documented 2026-10-28: partial index named in `to_bm25query`, predicate repeated) | open · S6 runs it on the corpus | S6 record `s6.bm25` |
| OPEN-D3-2 | D3 §5, M04 | Embedding model and dimension | open · S7 | `halfvec(n)` fixed in D3 |
| OPEN-D3-3 | D3 §5 | Keep `kb.segment.text` | closed 2026-10-28 by mechanism: the search column reads same-row text (D3 §5) | D3 §5 decided |
| OPEN-D3-4 | D3 §5, D5 §5.5 | Stored meaning key | open · S6; [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md) evidence recorded in D3 (meaning keys more stable) | D3 and D5 decided |
| OPEN-D4-1 | M10, M16, D6 §5 | Local model choice | open · S3 | D4 M10 and D6 §5 budgets updated |
| OPEN-D4-2 | M10 | Reasoning on or off | open · S3 | D4 M10 configuration |
| OPEN-D4-3 | M11 | LaTeX backend and macro map | open · S5 | D4 M11 configuration |
| OPEN-D4-4 | D4 §4.1, D8 §3 | Unit of LLM work | closed for golden and agent packets · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md), [S0-R2 report](../design_review/evidence/2026-10-28_design-spikes/S0-R2-report.md): the unit packet with query-assembled context; output budget from batch size (D4 §4.1); S3 still measures local-LLM quality per packet size | Packet rules updated |
| OPEN-D4-5 | M13 | Rule-based scoping sufficient | reopened 2026-10-28: the spike probe's 20/20 rested on a paragraph rule applied only to the sample's own parts; phase 0 M13 omits it (21/21 standing contexts, 18/20 scopes) · S5-B and phase 1 decide the paragraph extent | D4 M13 confirmed or changed |
| OPEN-D5-1 | D5 §5.4 | Slot definition for non-functional formula predicates | open · phase 1 (S0 units did not exercise it) | D5 §5.4 updated |
| OPEN-D5-2 | D5 §6.4 | Latent-model data needs and source merging | deferred · phase 2 | Phase 2 experiment |
| OPEN-D5-3 | D5 §5.4 | Auto-resolution margin | deferred · phase 2 | Phase 2 |
| OPEN-D5-4 | D5 §3.1 | Mention overlap rule near math | open · S2 | D5 §3.1 rule fixed |
| OPEN-D6-1 | D6 §1 | Barriers versus dataflow | deferred · phase 2 timing | — |
| OPEN-D6-2 | D6 §5 | GPU mode default | open · S3, S7 | D6 §5 updated |
| OPEN-D6-3 | D6 §7.4 | Iteration and agent budget defaults | deferred · phase 0 practice | Policies v0.2 |
| OPEN-D7-1 | D7 §3.1 | Golden set sizes | deferred · phase 1 | — |
| OPEN-D7-2 | D7 §5.3 | Formula equivalence procedure | open · S5; [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md) evidence recorded in D7 | D7 §5.3 fixed |
| OPEN-D7-3 | D7 §4 | Split granularity | deferred · phase 1 | — |
| OPEN-D7-4 | D7 §6 | PPI implementation | deferred · phase 2 | — |
| OPEN-D8-1 | D8 §1 | MCP server and orchestrator processes | decided 2026-10-28: two processes, the database the only shared state (D6 §1; [store](../design_review/evidence/2026-10-28_library-store/README.md) and [interfaces](../design_review/evidence/2026-10-28_library-interfaces-eval/README.md) notes) · built in phase 0 orchestration and agent interface | phase 0 acceptance test |
| OPEN-D8-2 | D8 §3 | Grouping units in packets | open · phase 0 | Decided on `core12` |
| OPEN-D8-3 | D8 §2.2 | Verifiably separate blind passes | closed · [S0 report](../design_review/evidence/2026-10-28_design-spikes/S0-report.md), [S0-R2 report](../design_review/evidence/2026-10-28_design-spikes/S0-R2-report.md): fresh subagent per pass, one input and one output folder, transcript audit (D8 §7) | S0 report describes the method used |
| OPEN-D9-1 | D9 §2 | Python 3.14 wheels | open · S2, S4, S5 for gliner2, z3, pgmpy, splink; the S0/S1 set resolved on 3.14.10 (D9 §2, 2026-10-28) | D9 §2 updated with resolutions |
| OPEN-D9-2 | D9 §1 | MCP and orchestrator in one process | decided with OPEN-D8-1 | Same as OPEN-D8-1 |
| GOLD-01 | D7 §3, D2 §7.5/§10, D4 §4.1, D8 §2.2 | Golden author and annotator inputs: Sonnet passes and adjudication from a generated annotator reference, guideline v1 and query-assembled context | decided · ADR-0011 (operator direction 2026-10-28, [S0-R2 report](../design_review/evidence/2026-10-28_design-spikes/S0-R2-report.md)); design amended; production tools phase 0 (P0.7) | `write_golden` records the model; reference generator built |
| OPEN-D2-7 … OPEN-D2-20 | D2 §11 | Guideline v1's open points and the S0 schema gaps, one row each in D2 §11: indexed-family arguments (schema, with D1 §7), which premises a claim depends on, section-level suppositions, restricting phrases, recalled definitions, explicit-claim threshold, local definitions, `asks_for`, numbers with units, a standard-deviation property, parameterizations, independence as a fact, concept-of and notation predicates, qualifier shape documentation | open · guideline v2 and schema v0.2, each checked by the D7 §2 rule-change procedure; `asks_for` (OPEN-D2-15) and numbers with units (OPEN-D2-16) first | D2 §9/§10 updated per row |
| OPEN-D1-5 | D1 §6, §7 | References outside the batch (`extref`, S0 gap RG-1, rank 1) | deferred 2026-10-28 to the phase 0 boundary with OPEN-D2-7…20 (keys move there anyway; phase 0 extraction emits none) | D1 states the value and its resolution |
| OPEN-D1-6 … OPEN-D1-8 | D1 §6.1, §4.2 | `bound` binding kind; `param_of` to non-`has_distribution` premises; extent over sibling statements (RG-3, RG-5, RG-6) | open · next schema revision | D1 updated per row |
| KEYS-01 | D1 §6.2, ADR-0012 | Keys depended on grammar coverage (tree form when a value parsed) | decided · ADR-0012 (2026-10-28, [design owner's review](../design_review/evidence/2026-10-28_design-spikes/design-owner-review-S0-S1.md) B1): keys use the token form for every value, with sizing commands removed; property test in P0.5b and S5 | property test passes in P0.5b |
| STMT-01 | D1 §10.1, D5 §3.5 | Statement identity: statements in one block collided; unit and sentence anchors keyed apart; context-premise assumptions (S0 gap GG-11, [design owner's review](../design_review/evidence/2026-10-28_design-spikes/design-owner-review-S0-S1.md) B3) | decided · anchor segment plus first-sentence ordinal; a context premise joins the statement whose anchor holds it (Proposed); S6 recomputes the S0 key figures | S6 figures recorded |
| PARAM-01 | D2 §10.4 | Parameter naming: "role word anywhere" contradicted the reference and trace ([design owner's review](../design_review/evidence/2026-10-28_design-spikes/design-owner-review-S0-S1.md) B2) | decided · the phrase that first names the parameter; passes SV and HV had followed the earlier wording on T4 | confirmed at the next D7 §2 check |
| BIND-01 | D5 §4, §9 | Consolidation's binding and derived-condition rules predated guideline v1 ([design owner's review](../design_review/evidence/2026-10-28_design-spikes/design-owner-review-S0-S1.md) A9) | decided · D5 §4 restates guideline §10.7's rows by first appearance; D5 §9 applies rules 1–4 (Proposed) | phase 1 binding run reproduces golden bindings |
| RENDITION-01 | D4 M01, D9 P0.5 | The S1 corpus and every S0 rendition used libxml2; M01 names html5lib ([design owner's review](../design_review/evidence/2026-10-28_design-spikes/design-owner-review-S0-S1.md) A12) | closed · html5lib rerun (record s1.corpus-html5lib): counts, invariants and locators unchanged; the seven reference pages content-identical, `sourceline` ruled a diagnostic outside the contract (D1 §3.2; record s1.rendition-identity). Spikes keep the libxml2 renditions; phase 0 re-stores references from model-facing batches | — |
| APPARATUS-01 | D9 §7 | Where the spike instruments (alignment, scoring) live long-term ([design owner's review](../design_review/evidence/2026-10-28_design-spikes/design-owner-review-S0-S1.md) A3) | open · waits on the operator's design of the evidence system and its reusable apparatus | — |
| EVID-01 | ADR-0001, ADR-0010, DESIGN §2 | Plans and evidence are never deleted (operator direction), against ADR-0001's retirement clause and ADR-0010's "records retire with their folder" ([design owner's review](../design_review/evidence/2026-10-28_design-spikes/design-owner-review-S0-S1.md) B9) | open · the operator's revised evidence process; the AGENTS.md override is in force meanwhile | superseding ADR accepted |
| OPEN-D7-5 | D7 §3.2 | Whether page text still helps golden passes with query context | open · phase 0 dev comparison | D7 §3.2 confirmed or changed |
| HTML-01 … HTML-07 | D1 §3, D4 M01–M03 | Seven HTML rules S1 found D1/D4 did not state | closed · [S1 report](../design_review/evidence/2026-10-28_design-spikes/S1-report.md); folded into D1 §3 and D4 M01–M03; HTML-07's profile additions and rendering conventions merged into D2 §12.1 with the profile vocabulary in D4 M01 (2026-10-28, review A5/B13); the adapter port reads them in P0.5 | D1 §3, D4 M01–M03 state them |
| PARSE-01 | D1 §6.2, D4 §4.3, M01, M09, M11, M13 | One math grammar; profile-driven delimiting; offset-preserving quote location | decided · ADR-0012; implemented in the spike instruments; production with D4's methods | D4 cards realized in phase 0 |
| P0CL-01 | D1 §3.2, §10.1; ADR-0019 | Keys inherited the adapter configuration, so any ingest change re-keyed the corpus; renditions content-addressed, statement and scope keys locator-anchored ([review](../design_review/reviews/design_review_phase0-contract-layer_2026-10-28.md)) | accepted 2026-10-28 (RC01, operator) · design amended; built in phase 0 foundations (F2) and ingest (I0, I1) | Property tests: content-identical renditions from two configurations give identical claim keys; an edit to one paragraph leaves other statements' keys unchanged |
| P0CL-02 (design half) | D4 §1, D6 §4 | Reuse digests by task id; content digests instead | accepted (RC02) · design amended; built in orchestration (O1) | The coordinator's §11 closure check |
| P0CL-03 | D3 §7, D7 §3, §5.1; ADR-0019 | Authored batches kept only in located form; the authored batch plus citation frame is the authority, items derived per rendition | accepted (RC03) · design amended; built in agent interface (A0) and evaluation (E1) | A golden authored on one rendition aligns unchanged against a content-identical one and against one edited elsewhere on the page |
| P0CL-05 (design half) | D3 §4, D4 §4.1, D5 §1 | Packet and consolidation inputs not recorded; `ops.run.reference_run_id`, known entities from it only | accepted (RC04) · design amended | Order-independence test (coordinator §11) |
| P0CL-06 | D1 §5.2, §6, §6.2, §10.1; D5 §5.3 | `valid_time`, cited source, number form and the fusion rule settled before keys freeze | accepted (RC07) · design amended; built in F2 | A §1.3 fixture pair with two validity intervals stays two claims; number canonicalization properties |
| P0CL-07 | D1 §6.1, D2 §3, §7.4, §12.1, D5 §3.5, §4, §8.2, D8 §5.2, D9 §1 | Statistics and Siegrist semantics in core; moved to pack annotations, `views:`, source profiles and a query plug-in | accepted (RC08) · design amended; built across S2, I1, C1, C2 | A toy second pack runs the generic stages with no core edit |
| P0CL-10 | D7 §3.1, §7, §9 | The gate had no pre-registered readings while promotion fixes identity | accepted (RC06) · design amended; built in evaluation (E2b) | `ci promote` shows the readings before confirmation |
| P0CL-11 | D6 §1, §7.4; D8 §5 | Answers carried no coverage; `promoted` not pinned | accepted · design amended; built in orchestration (fates) and queries (C2) | A query over a run with skipped pages reports partial coverage; a promotion between pages leaves a token's run unchanged |
| P0CL-16 | D4 §4.2, D6 §7.2, D7 §4 | Test pages excluded from routing rather than from training; examples not page-exclusive | accepted (RC11, operator) · design amended | Example retrieval never returns the unit's own page; no test page in any training, fitting or example set |

## Deferred, each with a trigger

| Item | Trigger |
|---|---|
| PSL, AMIE rule mining, cvxpy family selection, causal discovery, MinHash source dependence, retrieval fusion and reranking, sealed publication, exact replay (D0) | A measured gap that names one, and an experiment showing it helps |
| Hosted LLM tier | Local tier and agent tier stable; a cost or throughput need |
| RDF / JSON-LD export | A consumer that needs it |
| Product Rust | A measured hot path |
| Second corpus | Phase 4 gate, or math density stalling statistics progress (D0) |
| Non-LaTeX math notation (`attrs.notation` ∈ latex, html, image, plain; `img alt` for image math; S1-F) | A second source with image or HTML math (design owner's review A14) |

## Risks

| Risk | Mitigation |
|---|---|
| Circularity: goldens scoring runs assisted by the same model | Goldens by Sonnet, the pipeline's agent tier Opus (ADR-0011); D7 §1 mechanisms; test split excluded from agent work; witnesses |
| Math density makes encoders weak, so the LLM tier carries most claims | Accepted for phase 1 (S2 measures it); phase 3 distillation targets it; second corpus earlier if it stalls |
| Machinery growth, the previous repository's failure mode | Every method and table needs a consumer; conditional methods only through experiments; this plan's deferred list |
| Design churn while spikes run | Spikes never edit D-documents; fold-ins are batched (Q5, Q8) |
| Python 3.14 wheel gaps | OPEN-D9-1, resolved per package |
| Output volume overwhelming review during debugging | Slices, caps and budgets (D6 §8, D8 §3) |
| Three active plans drift apart | Each owns its own scope (AGENTS.md, operator decision 2026-10-28): design findings here, spike execution in the spike series, the build in the phase 0 series; cross-references cite package ids and evidence record ids, never copied status |
| The S0/S1 plan was written against D0–D5 before the 2026-10-28 review fold-in, which changed the ClaimProposalBatch (D2 §7.3: model-facing quote form, `extent`, `alternatives`, local refs) and the S0 brief | The spike lane re-reads D2 §7.3 and the S0 brief before fixing its batch contract |

## Standing conventions

- Labels per the design principles §D: all D-document content is **Proposed** until a spike or
  build step moves it.
- Spike outcomes are `passed`, `failed`, `blocked` or `not_run` with the command that produced
  them, dated.
- Commits go to `main` in small steps; nothing is pushed unless the operator asks.
