# Design phase plan

**Status:** Active; the sole execution plan. **Revised:** 2026-10-28.

## Purpose and boundary

Take the proposed design set ([docs/design](../design/README.md), D0–D9 and the trace) from
**Proposed** to **ready for the phase 0 build**: run the design spikes, deepen the library
realization of every method, dispose of every `OPEN-Dn-k` item, record the binding decisions as
ADRs, and replace this plan with the phase 0 build plan of [D9 §5](../design/D9-repository-and-phase0.md#5-phase-0-build-plan).

## Current state (2026-10-28)

| Item | State |
|---|---|
| D0–D9, trace | Written; **Proposed**; not yet reviewed against spike evidence |
| Spike briefs S0–S7 | Written ([spike README](../design_review/evidence/2026-10-28_design-spikes/README.md)); none run |
| Library realization in D4 | First-pass realizations written by the design owner; not yet deepened against the library overviews |
| Code | None. The template's scripts and tests only |
| Fresh review | A fresh-eyes completeness review (2026-10-28; 37 findings: 2 blockers, 17 major, 18 minor) was folded into D1–D9, the trace and the S0, S1 and S6 briefs; none remains open |
| DESIGN §1, §2 | §1 objective and out-of-scope written (Proposed); §2 binding decisions wait for ADRs (Q8) |

## Lanes

| Lane | Who | Writes | Must not |
|---|---|---|---|
| Spikes | In-repo agent | `docs/design_review/evidence/2026-10-28_design-spikes/` (code, results, reports) | Edit D-documents or the trace; write under `python/` or `domains/` |
| Library leverage | Parallel in-repo agent | **Library realization** subsections of D4 cards; `> Library proposal (L-nn):` blocks; `docs/library_leverage/` accounts (§Library lane brief) | Change a contract (unit, inputs, outputs, configuration semantics) except through a proposal block |
| Design owner | Claude (project conversation) | D-documents, trace, this plan's findings and dispositions | Write spike results or library accounts |
| Operator | Paul | Directions; approval of this plan's closure | — |

Handoffs: a spike report or a library proposal is input; the design owner folds it into the
D-documents and updates the findings rows below in the same commit, citing the report section
or proposal id.

## Execution queue

| # | Slice | Lane | Depends on | Done when |
|---|---|---|---|---|
| Q1 | S1 ingest and segmentation | Spikes | — | `S1-report.md` with `sample.json` |
| Q2 | S0 reference annotations | Spikes (Opus subagents) | S1 or raw text | `S0-report.md`; references adjudicated |
| Q3 | S4 LinkML compilation; S6 storage smoke | Spikes | — (S0 batches help S4) | Both reports |
| Q4 | Library pass 1: D4 cards, D2 §7 compilers, D3 extension use | Library leverage | — | Every D4 card's realization reviewed; proposals filed |
| Q5 | Fold-in 1: S1, S0, S4, S6, library pass 1 → D1, D2, D3, D4, trace | Design owner | Q1–Q4 | Findings rows for those OPEN items closed or re-scoped |
| Q6 | S2 GLiNER2.5; S3 local LLM; S5 math and verification | Spikes | Q1, Q2 | Three reports |
| Q7 | S7 embeddings and linking | Spikes | Q6 (S2) | Report |
| Q8 | Fold-in 2 → D4–D7; ADRs for the binding decisions; DESIGN §1 and §2; completeness review by a fresh reviewer | Design owner | Q5–Q7 | Every OPEN row disposed; ADRs accepted by the operator |
| Q9 | Replace this plan with the phase 0 build plan (D9 §5) | Design owner | Q8 | This file deleted; the new plan active |

Q1–Q4 run in parallel where their dependencies allow. Q5 may start per spike as reports land.

Q1 and Q2 are being executed in detail under the spike lane's
[S0/S1 execution plan](design-spikes-s0-s1_2026-10-28.md), which governs their procedure. The two
plans should be one: see Risks (two active plans).

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
| OPEN-D1-1 | M03 sentences | Sentence splitting on math-dense prose; choose variant | open · S1 | D4 M03 states the chosen variant |
| OPEN-D1-2 | M13, D1 §4.2 | Section extent for variable scope | open · S0, S5 | D1 §4.2 and D4 M13 updated |
| OPEN-D1-3 | D2 §9 FamilyParameter | Role names or symbols for parameter identity | open · S0 | D2 §9, §10.4 updated |
| OPEN-D1-4 | D1 §5.2 `scope` qualifier | Section extent for standing assumptions | open · S0 | D1 §5.2 updated |
| OPEN-D2-1 | D2 §7.2 | `Schema.from_dict` keys | open · S4 | D2 §7.2 example corrected |
| OPEN-D2-2 | M06, M07 | Raw or masked math | open · S2 | D4 M06 configuration fixed |
| OPEN-D2-3 | D2 §7.4, D5 §8.2 | rule-engine syntax; functions or resolver attributes | open · S4 | D2 §7.4 and D5 §8.2 updated |
| OPEN-D2-4 | D2 §9 | Property predicates or `has_property` | open · S0 | D2 §9 decided |
| OPEN-D2-5 | D2 §9, §10.4 | Standard normal as family or parameterization | open · S0, operator direction | D2 decided; direction logged if the operator chooses |
| OPEN-D2-6 | D2 §3 | List annotations round-trip | open · S4 | D2 §3 notes the representation |
| OPEN-D3-1 | D3 §5 | pg_textsearch syntax | open · S6 | D3 DDL corrected |
| OPEN-D3-2 | D3 §5, M04 | Embedding model and dimension | open · S7 | `halfvec(n)` fixed in D3 |
| OPEN-D3-3 | D3 §5 | Keep `kb.segment.text` | open · S6 | D3 decided |
| OPEN-D3-4 | D3 §5, D5 §5.5 | Stored meaning key | open · S6, S0 | D3 and D5 decided |
| OPEN-D4-1 | M10, M16, D6 §5 | Local model choice | open · S3 | D4 M10 and D6 §5 budgets updated |
| OPEN-D4-2 | M10 | Reasoning on or off | open · S3 | D4 M10 configuration |
| OPEN-D4-3 | M11 | LaTeX backend and macro map | open · S5 | D4 M11 configuration |
| OPEN-D4-4 | D4 §4.1, D8 §3 | Unit of LLM work | open · S0, S3 | Packet rules updated |
| OPEN-D4-5 | M13 | Rule-based scoping sufficient | open · S0, S5 | D4 M13 confirmed or changed |
| OPEN-D5-1 | D5 §5.4 | Slot definition for non-functional formula predicates | open · S0, phase 1 | D5 §5.4 updated |
| OPEN-D5-2 | D5 §6.4 | Latent-model data needs and source merging | deferred · phase 2 | Phase 2 experiment |
| OPEN-D5-3 | D5 §5.4 | Auto-resolution margin | deferred · phase 2 | Phase 2 |
| OPEN-D5-4 | D5 §3.1 | Mention overlap rule near math | open · S2 | D5 §3.1 rule fixed |
| OPEN-D6-1 | D6 §1 | Barriers versus dataflow | deferred · phase 2 timing | — |
| OPEN-D6-2 | D6 §5 | GPU mode default | open · S3, S7 | D6 §5 updated |
| OPEN-D6-3 | D6 §7.4 | Iteration and agent budget defaults | deferred · phase 0 practice | Policies v0.2 |
| OPEN-D7-1 | D7 §3.1 | Golden set sizes | deferred · phase 1 | — |
| OPEN-D7-2 | D7 §5.3 | Formula equivalence procedure | open · S5 | D7 §5.3 fixed |
| OPEN-D7-3 | D7 §4 | Split granularity | deferred · phase 1 | — |
| OPEN-D7-4 | D7 §6 | PPI implementation | deferred · phase 2 | — |
| OPEN-D8-1 | D8 §1 | MCP server and orchestrator processes | open · P0.7 | Decided in build |
| OPEN-D8-2 | D8 §3 | Grouping units in packets | open · phase 0 | Decided on `core12` |
| OPEN-D8-3 | D8 §2.2 | Verifiably separate blind passes | open · S0 practice, P0.7 | S0 report describes the method used |
| OPEN-D9-1 | D9 §2 | Python 3.14 wheels | open · spike environments | D9 §2 updated with resolutions |
| OPEN-D9-2 | D9 §1 | MCP and orchestrator in one process | open · P0.7 | Same as OPEN-D8-1 |

## Deferred, each with a trigger

| Item | Trigger |
|---|---|
| PSL, AMIE rule mining, cvxpy family selection, causal discovery, MinHash source dependence, retrieval fusion and reranking, sealed publication, exact replay (D0) | A measured gap that names one, and an experiment showing it helps |
| Hosted LLM tier | Local tier and agent tier stable; a cost or throughput need |
| RDF / JSON-LD export | A consumer that needs it |
| Product Rust | A measured hot path |
| Second corpus | Phase 4 gate, or math density stalling statistics progress (D0) |

## Risks

| Risk | Mitigation |
|---|---|
| Circularity: Opus goldens scoring Opus-assisted runs | D7 §1 mechanisms; test split excluded from agent work; witnesses |
| Math density makes encoders weak, so the LLM tier carries most claims | Accepted for phase 1 (S2 measures it); phase 3 distillation targets it; second corpus earlier if it stalls |
| Machinery growth, the previous repository's failure mode | Every method and table needs a consumer; conditional methods only through experiments; this plan's deferred list |
| Design churn while spikes run | Spikes never edit D-documents; fold-ins are batched (Q5, Q8) |
| Python 3.14 wheel gaps | OPEN-D9-1, resolved per package |
| Output volume overwhelming review during debugging | Slices, caps and budgets (D6 §8, D8 §3) |
| Two active plans: this plan and the spike lane's S0/S1 plan both declare themselves the sole plan (AGENTS.md allows one) | Operator decision pending: proposed resolution is that this plan stays the single active plan and the S0/S1 plan becomes its supporting document for Q1–Q2, with its findings rows merged here |
| The S0/S1 plan was written against D0–D5 before the 2026-10-28 review fold-in, which changed the ClaimProposalBatch (D2 §7.3: model-facing quote form, `extent`, `alternatives`, local refs) and the S0 brief | The spike lane re-reads D2 §7.3 and the S0 brief before fixing its batch contract |

## Standing conventions

- Labels per the design principles §D: all D-document content is **Proposed** until a spike or
  build step moves it.
- Spike outcomes are `passed`, `failed`, `blocked` or `not_run` with the command that produced
  them, dated.
- Commits go to `main` in small steps; nothing is pushed unless the operator asks.
