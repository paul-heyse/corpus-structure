# Design rationale

**Written 2026-10-28 by the original design owner** (Claude, in the claude.ai project conversation),
when design ownership moved to the in-repo agent. The D-documents state *what* the design is; this
document records *why*. It covers:

- the operator's intent and constraints as stated;
- the diagnosis of the previous repository that shaped the design;
- the principles the design rests on;
- for each area, the alternatives that were weighed and rejected, and what would reopen the choice;
- judgment calls made under uncertainty;
- ideas that were considered but never written into a D-document;
- open concerns.

**Authority.** This is not an authority over D0–D9, the trace or the ADRs. Where they differ, the
D-documents and ADRs win, and this file should be corrected. Each decision section below is written
so it can be lifted into an ADR (context, options, decision, reasons, revisit trigger).

**Sources it draws on.**
- The original overview: the claude.ai document "Corpus Intelligence — Target Analysis Structure,
  Data Model and Scaling Path", now marked superseded. Its unique content is reproduced here.
- The design conversation of 2026-10-28.
- The 2026-10-17 review of corpus-intelligence's domain and operational model.
- The design owner's [review of S0 and S1](../design_review/evidence/2026-10-28_design-spikes/design-owner-review-S0-S1.md).

## 1. The operator's intent and constraints

### 1.1 The objective

> "My overall objective remains the same, produce a structured representation of the knowledge
> contained within a set of documents (statistics was a starting example, but the target is for this
> to be used across any domain, and ultimately to be commercializable…)"

- **The product.** It builds a structured representation of a business from its documentation,
  emails and the like. Statistics is the **calibration** domain, chosen to separate building and
  calibrating a capable pipeline from the inherent difficulty of a domain.
- **Why probability and statistics.** Mathematical claims can be *verified*: by SymPy, by simulation,
  against reference parameterizations. That gives ground truth that business text lacks.
  Computer science was an earlier hypothesis only. Thermodynamics is explicitly excluded.
- **Generality was always the requirement.** The design's core may contain nothing
  statistics-specific; statistics lives in a domain pack (D2). When in doubt about a mechanism, ask
  whether it would serve a contract, an email thread, a policy manual or an asset register.

### 1.2 The three original questions (2026-10-28)

1. **Structure.** What is the best high-level structuring of the analysis, leveraging GLiNER2.5,
   pgmpy, spaCy, LinkML, rule-engine, Splink and others? This covers structure, sequencing,
   pairings, and *conditional use of capabilities in response to measured gaps*.
2. **Data model and architecture.** The operator's hypotheses, and the answers given:

   | Hypothesis | Answer |
   |---|---|
   | A more meta data model | Yes, at two levels: the schema is data, and the operations are data |
   | Different database types | No: one PostgreSQL with JSONB, pgvector and full text; graph and RDF are export projections |
   | More specific capture of conditionality in measurement | Yes: every task records the policy rule that fired and the metric values that made it fire |
   | One representation capturing all variation | Yes, at the data level: one claim form whose variation lives in typed qualifiers and the observation log, not in new tables |

3. **Incremental scaling.** Opus in Claude Code bridges gaps first. LLM interventions are recorded
   in the database, goldens are created and updated, and interventions scale back as automated
   analysis matures.

### 1.3 Decisions the operator took (2026-10-28)

| Topic | Decision | Consequence in the design |
|---|---|---|
| Rebuild | A fresh build in a new repository (`corpus-structure`); corpus-intelligence becomes read-only reference ("I think it will be much easier to build afresh") | Port list in D9 §7; nothing copied with its old contracts |
| Models | Hosted models long term. Near term, the Opus in the Claude Code session acts as the strong model, plus a local LLM on the operator's RTX 5090 (32 GB) | Three-tier ladder; one shared packet format; the local LLM is a *directional proxy* for hosted-model prompts |
| Corpus | Statistics only until it stands up; a more NLP-natural corpus later, sooner if math density stalls progress | Phases 0–4 on Siegrist; phase 5 picks the second corpus |
| Goldens | No per-item verification by the operator. The operator works on an outer loop: reviewing goldens not to approve content but to add direction on what they should include, refining guidelines and process | D7 §8 digest and directions; blind authoring; witnesses |
| Cost | Opus cost is not a concern; **output size is**, during heavy debugging ("keep the outputs targeted in size") | Work-packet caps, pagination, debug slices, budgets |
| Detail standard | Documentation detailed enough that the remaining choices are "conclusions on implementation details that a highly intelligent LLM such as Opus 5.5 would make naturally" | The trace as exact data; fresh-reviewer completeness checks |

Later decisions recorded elsewhere:
- Sonnet as golden author, from improved inputs (ADR-0011).
- One math grammar (ADR-0009).
- Evidence records (ADR-0010).
- Several plans may be active and are reconciled later.
- Plans and evidence are never deleted (AGENTS.md).

### 1.4 How the operator works

- **Lanes.** The operator runs multi-agent lanes (build, spike, library-leverage, design) and wants
  lanes kept from creating conflicting sources of truth. Each artifact has exactly one home and one
  writing lane (§4.13).
- **More detail rather than less**, especially on design reasoning.
- **A former BCG consultant and Shell engineer.** Expects decisions argued from evidence, numbers
  with denominators, and a clear separation of what is decided from what is assumed.

### 1.5 History that shaped the operator's hypotheses

The 2026-10-17 review of corpus-intelligence found:

- **A strong domain model on the knowledge side:** about 1,600 frozen pydantic contracts, 209
  table declarations, and `Ref`/`RelationType` metadata used about 250 times.
- **Almost none on the operational side.** Invocations, attempts, phases, lineage and custody lived
  in byte blobs, JSONL files and in-memory runner state.

That is where the operator's diagnostics and CLI friction came from: missing join keys, diagnoses
computed per call instead of queried, and about 9 authority/custody concepts with 8 lock
mechanisms.

The operator's hypothesis was a relational domain model for operations. The new design takes that
hypothesis to its conclusion: **operations are data** (§3, P5). Methods, configurations, policy
rules, runs, tasks with their triggers, measurements, interventions and experiments are all rows.
"Why did this run on that unit, and what did it cost" is then a query, not a debugging session.

## 2. The diagnosis of corpus-intelligence, and what each finding taught

Figures from the 2026-10-28 review of the old repository:

- **Scale:** 566k product lines and 646k test lines, for 70 KB of source text (three Siegrist
  sections and three transfer files of under 1 KB each).
- **No end-to-end output:** no corpus journey ran end to end. The transfer claims the inspection
  tests read were built by hand in test support; no construction stage produced them.

| Root cause | Evidence | Design response | Warning sign to watch for in the new repo |
|---|---|---|---|
| Meaning lived in Python classes | `evidence/model.py`: 10,059 lines, 277 classes; one distinction ("governing association") added 24 classes, 12 tables and three migrations; three evidence generations and 13 kernel revisions coexisted | Schema as data (LinkML); one claim form; a new distinction is a schema edit | A Python class or table named after a domain concept |
| Guarantees before value | `store/`: 114k lines; seven byte/engine families; five separate history promises; process custody | Append-only observations, run-scoped materialization; heavier guarantees only for a named consumer | Machinery whose consumer is "later" or "for safety" |
| Tools adopted per gap, never compared | Three linking mechanisms, six candidate routes, three input-matching functions; no extraction quality ever measured | One observation type for every method; policies route; golden-set experiments decide promotion | A method merged without an experiment row; two methods doing one job with no comparison |
| Domain mechanisms hard-coded | Regex operation reading over math spans, an affine-normal "qualification law" in code, a ProbOnto-only seed | Generic core plus domain packs | Statistics words in `core`, `methods` or `consolidate` |
| Planning outran output | 192 ADRs and 172 plans, 164 superseded; each cycle re-scoped the target before the previous one produced output | Spikes that answer named questions; phase gates on measured output; a size guardrail of about **15k lines for v1** | Plans and ADRs growing faster than working journeys |

**What was right**, and survives as fields and statuses rather than subsystems:

- Source fidelity, mathematical validity, applicability, acceptance, execution success and
  usefulness are different things.
- Unavailable, empty, ambiguous, unsupported, failed and unreviewed are different non-positive
  states.

**About 4.5k lines were judged worth porting.** D9 §7 holds the final list, after the files were
inspected. Three original intentions changed on inspection:

- `_analysis_kernels.py` was to become statistics verifiers. It turned out to be "exact constructors
  and admitted-fragment checks", so it is not ported.
- `identity_matching.py` was to be the starting Splink configuration. It covers person and
  organization nominations, so it is kept for business corpora.
- `runs/domain_laws.py` (1,732 lines) is mined for rule-engine patterns, not ported. D9 does not yet
  list it.

The transfer fixtures (`fixtures/pdt_domain_transfer/`, `fixtures/micro_corpus/`) were to be kept
in reserve for the generality check. D9 does not list them either.

**Retired outright:**
- kernel revisions and successor definitions;
- native admission and fact mappings;
- sealed publication and receipts;
- the Tantivy crate;
- process custody and the GPU lease (a semaphore suffices);
- the retrieval fusion stack;
- the induction analytics (PSL, AMIE, cvxpy, datasketch);
- the protected-evaluation authority.

Of eleven service environments, three were to be kept: vLLM, one PDF parser and the agent MCP
server.

## 3. Principles the design rests on

These are the load-bearing ideas. A change that violates one should come with an ADR that says so.

- **P1 · The domain model is data.** A LinkML pack declares classes, predicates, qualifiers,
  identity and extraction hints. Code is generic over it. *Why:* the old repository's cost of a new
  distinction was a code, codec and migration change. Here it is a schema edit plus a migration
  mapping, and every consumer (GLiNER2, the LLM JSON Schema, rule-engine, the annotator reference,
  the schema tables) is compiled from the same source, so they cannot drift.
- **P2 · One representation for all knowledge.** A Wikidata-style statement (main value,
  qualifiers, references, rank) carries every fact in every domain (§4.4).
- **P3 · Methods write observations; only consolidation writes knowledge.** *Why:*
  - a nomination can never pass as a fact;
  - every claim lists its supports;
  - two methods can be compared on the same cached inputs;
  - re-consolidation is cheap and deterministic, so changing consolidation never needs re-running
    extraction.

  Opus is a method under this rule: its outputs are observations plus an intervention row, and
  nothing it writes bypasses consolidation.
- **P4 · Measure before mechanism.** No refinement without a target. Every addition is an
  experiment: a hypothesis, the metric it should move, guards it must not hurt, a baseline, a
  decision. Conditional methods enter only when a measured gap names them. *Why:* this is the
  direct fix for the unvetted accumulation the operator described.
- **P5 · Operations are data.** See §1.5.
- **P6 · Evaluation is a diff.** Goldens, agent proposals and every method's output share the claim
  form, so scoring is alignment between two sets of claims, not a bespoke checker per method.
- **P7 · Non-positive states are visible.**
  - Empty is recorded, not silent.
  - Failed is distinct from empty.
  - "Not run" is distinct from "ran, found nothing".
  - An escape leaf (`phrase`, `unsupported`) keeps what the representation cannot state, instead
    of forcing it into a nearby predicate.

  *Why:* the confidence model needs `silent` versus `not_run` (D5 §6.2), and consumers must never
  read an unconditional fact where the source stated a condition the system could not parse.
- **P8 · Determinism and stable identity.** Keys are hashes of canonical JSON of meaning-bearing
  parts. Everything is reproducible from inputs, configuration hashes and model revisions. Runs
  materialize knowledge and are immutable once finished. *Why:* runs must be comparable, judgments
  must carry forward by key, and caching must be valid.
- **P9 · The pipeline never calls Opus.** Opus is the Claude Code session, not an API. The pipeline
  queues `awaiting_agent` tasks; a run waits at a barrier or finishes with those items explicitly
  unresolved. *Why:* Opus has no API in this setup, and a queue keeps the agent's work recorded,
  bounded and resumable.
- **P10 · Small outputs by construction.** Packets, inspection responses and digests are capped and
  paginated, and runs can be scoped to slices. *Why:* the operator's binding constraint during
  debugging is context and review volume, not cost.
- **P11 · Every mechanism needs a consumer.** The heaviest lesson of the old repository. The test:
  name the query, metric, decision or user that reads it.
- **P12 · Always shippable.** Every phase ends with the full loop running on the whole corpus and
  the typed questions answered from the database. A method replaces another only when golden-set
  evaluation shows it matches or beats it.

## 4. Decisions by area: reasons, alternatives, revisit triggers

### 4.1 Fresh build rather than refactor

- **Options:**
  1. Refactor corpus-intelligence toward the target.
  2. Fresh build with a port list.
- **Why the fresh build:**
  - the meaning model was entangled with 277 classes and 120+ migrations;
  - the process layer (ADRs, plans) encoded superseded targets;
  - no output existed to protect.

  A new repository lets the dependency graph, agent instructions and process start clean, with the
  old code as a searchable reference.
- **Revisit:** not applicable. This was a one-time decision.

### 4.2 The store: one PostgreSQL

- **Decision:** PostgreSQL 18 as the single authority, holding knowledge, operations and evaluation
  in one database with four schemas (D3).
- **Why:**
  - one transaction links a task, its observations and the claims they change;
  - JSONB holds variable payloads without per-type tables;
  - pgvector and full text sit in the same query planner;
  - managed hosting exists for the commercial product.
- **Rejected:**

  | Alternative | Why not |
  |---|---|
  | Graph database (property graph) | A second authority to synchronize; path-heavy workloads are not the dominant query; recursive CTEs and NetworkX projections cover traversal at this scale. *Revisit* if path queries dominate |
  | RDF triple store | Qualifiers, evidence and statuses on statements are awkward in triples (reification or RDF-star). Keep RDF and JSON-LD as LinkML-generated exports (D8 §6) |
  | DuckDB as the authority | Single writer, no row-level queue semantics. Excellent for read-only analytics over PostgreSQL or Parquet, which is its role (D3 §1, ADR-0010 catalog) |
  | Per-type tables | The old repository's path (277 classes); variation belongs in data |
  | A separate vector database | Vectors must filter and join with segments and entities; pgvector does both |
  | Tantivy or a separate search engine | pg_textsearch (BM25) in the same database; S6 confirms its syntax |

- **Revisit:** many corpora or tenants; path-dominated queries; write volume beyond one database.

### 4.3 The schema language: LinkML with `ci:` annotations

- **Decision:** LinkML YAML packs, with `ci:` annotations for extraction, identity and scope
  semantics, compiled into every consumer (D2 §7).
- **Why LinkML:**
  - a mature schema language with generators (JSON Schema, Pydantic, JSON-LD, OWL);
  - `SchemaView` for programmatic reading;
  - annotations for our own semantics;
  - readable by models and people;
  - versionable in git.
- **Rejected:**

  | Alternative | Why not |
  |---|---|
  | OWL with SHACL (pyshacl) | Expressive for logic and validation over RDF, but heavier to author, built for open-world reasoning we do not need, and not a natural source for GLiNER2 or LLM schemas |
  | Pydantic models as the schema | That is the old repository's failure: meaning in code |
  | JSON Schema alone | No class hierarchy, no rich slot semantics, no generators to other targets |

- **Why annotations rather than separate config files:** one file per domain carries meaning and
  extraction behaviour together, so a description edit (which changes GLiNER2 and LLM behaviour)
  is visible as a schema version. The library-leverage lane may find LinkML features that replace
  some `ci:` annotations; prefer native features when they exist.
- **Revisit:** if LinkML generators block a compiler (S4 checks this), or a domain needs logical
  inference over the schema.

### 4.4 The claim model

- **Decision:** a claim is subject, predicate, object (entity or typed value) and qualifiers, with
  evidence spans, supports, status and establishment. Core qualifiers apply to every domain; schema
  qualifiers are declared per predicate (D1 §5).
- **Why the Wikidata statement model:** it has held up across open domains for a decade. Main
  value, qualifiers, references and rank map to claim, qualifiers, evidence and status. n-ary facts
  with one primary subject stay one claim (`param_values` on `has_distribution`).

  | Alternative | Why not |
  |---|---|
  | RDF reification or n-ary relation patterns | Verbose and hard to query |
  | Event-centric models everywhere | Over-reify; most facts have a natural subject |
  | Property graphs without qualifiers | Lose conditions and modality |

- **Reification rules (D1 §5.4):** a fact becomes an entity only when it has several equal
  participants, must be referred to as a thing, or recurs as one identity. Statements are reified
  under the second rule, because theorems need premises, conclusions and proofs grouped. That makes
  "reconstruct the affine-transformation theorem" a query.
- **Modality was the most consequential qualifier.** `supposed` keeps hypothetical premises from
  becoming facts: "what is normally distributed" returns nothing from a premise unless suppositions
  are asked for. The old repository spent subsystems on this distinction; here it is one field.
- **Conditions as a typed JSON tree with escape leaves (D1 §7).**
  - Rejected: free text (not checkable); a full logic language (models cannot write it reliably,
    consumers cannot read it).
  - The tree translates to z3 where leaves allow, so consistency and implication can be checked
    (M20).
  - `phrase` and `unsupported` leaves mean a claim is never presented as unconditional when the
    source conditioned it. This was also the reason for INV-09.
- **Symbol bindings (D1 §6.1)** are the general form of the old repository's "governing input
  association": which source-backed symbol supplies which parameter under which premise. Making
  this a value-level map, rather than 24 classes, is the clearest single illustration of P1.
- **Claim links versus claims about claims.** Relations between claims (`derived_from`,
  `contradicts`, `alternative_of`, …) are typed links, so claims stay first-order. Relations between
  statements are ordinary claims with statement subjects.

### 4.5 Identity, keys and runs

- **Keys:** `prefix + sha256(canonical_json(parts))[:32]`. A key identifies the same meaning across
  runs, which is how runs are diffed and judgments carried forward.
- **Run-scoped materialization (D1 §10.2).** Rejected: one mutable global knowledge base updated in
  place.
  - With materialization, experiments compare a candidate run against a baseline run, rollback is
    promotion of a different run, and finished runs are immutable evidence.
  - The cost is storage, acceptable at 10⁴–10⁵ claims per run (D3 §11), and deletion of
    non-promoted runs after their experiments close.
- **Rebuild per consolidation pass (D5 §1)** instead of incremental updates removes a class of
  update bugs. Deterministic keys make verification and judgment observations survive rebuilds.
- **Formula keys must not depend on parser coverage** (design-owner review B1). This was argued
  twice: by the fresh reviewer (finding 10) and again after ADR-0009's canonical-form rule. The
  principle: keys come from a total, deterministic normalization of the written form; structure
  (parse trees, SymPy) is for equivalence and fusion, never for identity.
- **Local versus global entities.** Siegrist's `X` in one theorem is not `X` in another. Scope is a
  segment, and section scope with "Suppose again" re-binding exists because S0 showed it is needed
  (OPEN-D1-2).

### 4.6 The evidence model

- **Renditions** (document plus adapter configuration). An adapter change creates new renditions
  beside the old ones, so offsets cited by older runs and goldens stay valid. *Rejected:* rewriting
  segments in place.
- **Canonical text** keeps LaTeX verbatim. Everything downstream (quotes, spans, the math grammar)
  reads the source form, and rendered-only text is inserted by declared, recorded convention
  (D1 §3.1, S1).
- **Quotes rather than offsets from models.** Models do not count characters reliably. Quote
  location (D4 §4.3) proved exact for 733 of 735 S0 quotes. Offsets without tools remain untested
  (S3).
- **Locators for slices** (`page#unit-id`, `page@u:…`, `page@p:…`) because segment keys change with
  adapter configuration while author markup and text prefixes do not.
  > Revised by the design authority (2026-10-28, ADR-0019, after the phase 0 contract-layer review,
  > P0CL-01): renditions are now keyed by their content, with adapter configurations as build
  > provenance, so a content-preserving adapter change keeps every key; statement and local-entity keys
  > are anchored by locators (D1 §3.4, §10.1). New renditions still appear beside old ones when content
  > changes.

### 4.7 Libraries: what each is for, and what was weighed

| Library | Role | Why it, and what was weighed |
|---|---|---|
| GLiNER2.5 | Encoder extraction: entities, span attributes, classification, joint entity–relation decoding (M05–M07) | Schema-conditioned zero-shot extraction compiled from the same LinkML descriptions; constrained decoding (`Classifier`, `JointIE`) enforces type and structure rules natively; cheap enough to run on every unit; a LoRA path for distillation (phase 3). Weighed: spaCy NER (needs training data per type), fine-tuned BERT taggers (same), LLM-only extraction (cost and determinism). S2 measures how much it carries on math-dense text; the expectation is that the LLM tier carries most claims in phase 1 here, and encoders more on NLP-natural text |
| spaCy 3.8 | Sentences (M03, with inline math merged into one token: S1's b′), matchers (M08, M13 binders), cue detection (M22) | Deterministic, fast, battle-tested. The math-merging trick keeps spaCy useful on LaTeX-dense prose (boundary F1 1.0 against 0.80 raw) |
| LinkML | The schema language and its compilers | §4.3 |
| rule-engine 5.1 | Validation rules (M19) **and** routing policies (D6) | One expression language for both, with typed contexts that fail at compile time, and ordered `Chain` (new in 5.1) for first-match escalation ladders. Weighed: SHACL (RDF-bound), plain Python predicates (code, not data; not versionable as policy) |
| z3 | Condition consistency and implication (M20) | Only z3-class solvers decide satisfiability of the constraint trees conditions produce. Conditional: enters on measured conflicts |
| SymPy plus the extended Lark grammar | Reading math, canonical form, equivalence, verifiers (M09, M11, M21) | ADR-0009: one grammar for every reader of math, extending SymPy's own Lark grammar by directives. Rejected: string rewriting (recurring defects), a grammar from scratch (loses SymPy conversion), pynini (no offsets or nesting) |
| Splink 5 | Identity of records with several informative attributes (M15) | Its documentation warns against single bag-of-words fields, so single-label concepts go to rapidfuzz and pgvector instead (M14). Splink's natural home is business records: people, organizations, accounts, citations, emails. Conditional in statistics |
| rapidfuzz, pgvector | Concept-linking candidates; quote location | Cheap and well-understood; vectors only once S7 shows they add recall |
| pgmpy | The latent-truth confidence model (D5 §6.4) | A Dawid–Skene style network: a hidden "is in the golden" variable per claim, method outputs as observed children, golden-aligned claims as partial labels, fitted by `DiscreteEM`, exact inference by `VariableElimination`. Weighed: fixed weights (the cold start), Snorkel-style label models (similar idea; pgmpy was already in the stack and is general), learned classifiers (need more labels). Its by-product, per-method sensitivity and false-positive rate per predicate group, is what de-escalation policies read |
| scikit-learn | Isotonic calibration of confidence | Standard and small |
| ppi_python | Prediction-powered inference for corpus-level precision from a random audit (D7 §6) | Escalated items are not representative, so precision estimated only from them is biased; PPI combines a small uniform audit with the full output for a valid interval |
| vLLM 0.31 | Local LLM serving with structured outputs on the RTX 5090 | Already proven in the old repository's environment. Use the standard OpenAI-compatible server, not the old private socket protocol |
| Qwen3.5-9B (to start) | Local tier | Already cached; S3 compares a larger quantized model |
| Qwen3-Embedding | Segment and alias embeddings | Already cached; Matryoshka dimensions let S7 choose the size |
| FastMCP 4.1, Typer, Rich | Agent tools, CLI | Standard |
| DuckDB 2.0, PyArrow | Analytics, Parquet exports, the evidence catalog | Never an authority |
| Docling, MinerU, an email parser | PDF and email ingest (later) | Not needed for Siegrist. MinerU is the escalation for pages whose layout parse fails |

### 4.8 Pairings between methods

These were the core of the original answer to question 1. Some are in D4, some only here.

- **LinkML → GLiNER2.** Class and slot descriptions become label descriptions; slot ranges become
  `JointIE` typed endpoints; cardinalities become record cardinalities; enums become span attributes
  or classifications. The same schema generates the JSON Schema for LLM structured output. *(In D2
  §7.)*
- **spaCy → GLiNER2 candidate scoring.** spaCy proposes deterministic candidates (gazetteer hits,
  identifiers, noun chunks), and GLiNER2 scores them under the schema with `score_explicit_spans`.
  This separates candidate-generation errors from scoring errors, which tells you which component
  to improve. **Not in D4**: a candidate method for when M06's recall gap is a span-proposal problem.
- **GLiNER2 ↔ LLM.** GLiNER2 gives cheap recall and span attributes; the LLM verifies and fills
  qualifiers. Every LLM correction is a labelled example, and accumulated examples train a
  per-domain GLiNER2 LoRA adapter. **This is the main route by which interventions decline**
  (phase 3).
- **Splink plus embeddings plus LLM for identity.** Splink for multi-attribute records, rapidfuzz and
  pgvector for single-label concepts, and the LLM decides only the grey zone (match probability
  roughly 0.3–0.9).
- **rule-engine for validation and routing:** one engine, two uses.
- **pgmpy in two roles:**
  - now, the latent-truth confidence model;
  - later, as an *output*. Dependency and causal claims extracted from business documents form a
    DAG whose implied independencies can be checked and, where business data exists, fitted.

  **The second role is in no D-document.** It matters for the commercial target: a business's
  stated dependencies become a checkable model.
- **SymPy, z3 and simulation as statistics verifiers.** They are domain verifiers, not core stages.
  Other domains will have their own: unit arithmetic, date logic, ledger balances.

### 4.9 Where interventions go when they scale back

This was the mechanism behind question 3; D0 and D6 cover parts of it.

| Intervention pattern | Becomes |
|---|---|
| Repeated corrections of one entity or relation type | Training data for a per-domain GLiNER2 LoRA adapter |
| Corrections a prompted LLM could have made | Few-shot examples, then prompt optimization (gepa) against dev goldens |
| Corrections that follow a regular surface pattern | A spaCy pattern or grammar rule |
| Adjudications that cluster by score | A tuned policy threshold |
| Facts with no schema home | A new schema version |

### 4.10 Gap-triggered escalation: the original starting triggers

D6 §7 holds the current policies. The original triggers were guesses to tune against goldens; the
first and last are **not yet represented** in D6:

| Gap | Measurement | Starting trigger | Action |
|---|---|---|---|
| Coverage | Share of segments an LLM classifier marks *fact-bearing* that hold no claim | Above 15% in a document | LLM open extraction on those segments; facts with no schema home become schema proposals |
| Confidence | Calibrated claim confidence | Below 0.6 for a priority type | Re-decode with `JointIE` constraints, then LLM verification |
| Disagreement | Two or more methods differ on one span | Any, for priority types | LLM adjudication; the decision becomes a golden candidate |
| Constraint | Rule failure | Any | Targeted re-extraction, else a conflict record; never a silent drop |
| Identity | Splink match probability | 0.3–0.9 | LLM adjudication with both contexts |
| Normalization | Parse outcome | Failed | LLM normalization; recurring patterns become grammar work |
| Cross-window | A record's fields fall in different chunks | Any | Section-level LLM pass (GLiNER2 creates no cross-window edges) |
| Regression | Golden-set F1 against the last promoted run | Drop above 1 point | Block promotion |

The "fact-bearing" coverage metric matters most for business text, where much prose carries no
claims. It is the trigger for schema growth (phase 4).

### 4.11 Models, packets and the agent

- **One packet and prompt format for every LLM tier.** A configuration proven locally or with Opus
  carries over to hosted models by changing the endpoint and model name only. This is why the local
  model is a *directional proxy*: prompts and evidence packing are tuned on it before money is spent
  on hosted calls.
- **Opus sees the local model's answer and rationale** in judge packets. This speeds its review and
  measures how often the local tier is right.
- **Work packets are bounded** (P10), and runs scope to debug slices, so heavy debugging costs a few
  paragraphs of context, not the corpus.
- **The agent tier is Opus; golden authoring is Sonnet** (ADR-0011). Two reasons:
  - S0-R2 showed that, with written conventions, Sonnet matches Opus;
  - separating the golden author from the escalation tier means a pipeline tuned toward Opus's
    habits is not rewarded by Opus-written goldens.

### 4.12 Orchestration

- **A database queue rather than a workflow engine** (D6 §1). The stage graph is small and fixed,
  and the database already records everything a workflow engine would. `SELECT … FOR UPDATE SKIP
  LOCKED` with leases is enough for one operator and one GPU.
  - Weighed: Prefect, Dagster, Temporal, Airflow. Each would be a second authority over task
    state.
  - Revisit: multi-tenant production, distributed workers.
- **Stage barriers rather than per-unit dataflow:** simplicity at this corpus size (OPEN-D6-1).
- **Caching by input digest.** Unchanged work is free, and, more importantly, **two configurations
  compare on exactly the same inputs**, which makes experiments cheap and honest.
- **GPU co-residency or exclusive mode** (D6 §5). A semaphore, not a lease system: the old
  repository's GPU lease was retired machinery.

### 4.13 Lanes and homes

The original process recommendation: each artifact gets exactly one home, and each home one writing
lane.

- Code and schema files live in git, owned by the build lane.
- Goldens, interventions, audits and experiment decisions live in the database, written only
  through the intervene tools.
- Neither lane edits the other's home, so lanes cannot create competing sources of truth.

The spike, library-leverage and design lanes (D9 §6) extend this for the design phase. With design
ownership consolidated in the repository, the remaining risk is two plans or two evidence stores
describing the same item. Prefer pointers to copies.

**A tension to keep in view.** The original analysis recommended a *lighter* process than the
template: one short DESIGN.md, an append-only decision log, the experiment table and an evaluation
dashboard. The reason was that the old repository's 192 ADRs and 172 plans outran its output. The
operator chose the template process (ADRs, plans, an evidence system). That is the operator's call,
and it serves the operator's multi-lane way of working. The warning sign from §2 still applies:
plans, records and reports growing faster than working journeys.

### 4.14 Evaluation without human verification

- **What F1 measures.** Without per-item human verification, F1 measures agreement with the golden
  author under the current guideline. That is the intended target: the pipeline should reproduce
  what a careful annotator following the guideline would produce, at a fraction of the effort. The
  operator steers what "careful" means through the guideline, not item by item.
- **The risks and their five mechanisms (D7 §1):**
  - blind authoring;
  - two passes with measured agreement as the ceiling;
  - leakage rules;
  - witnesses independent of the golden author;
  - the operator's outer loop.
- **Re-scoring on guideline change.** Every golden records its guideline and schema versions, and
  kept runs are re-scored, so a metric shift caused by a guideline change is never read as a
  pipeline change.
- **The random audit with PPI** (§4.7).
- **Reading agreement correctly** (S0's lesson, now D7 §5):
  - a reference built from one model's passes favours that model wherever the guideline is silent;
  - compare pass against pass beside pass against reference;
  - check every rule change on units the rule was not written from.

### 4.15 The scaling path

- **A walking skeleton first.** In phase 0, Opus extracts everything through recorded tools, so the
  full loop (ingest, store, consolidate, serve, evaluate) works before any cheap method exists.
  Stages are then handed to cheaper methods one at a time, each only when golden-set evaluation
  shows it matches or beats what it replaces.
- **Two headline numbers:**
  - golden-set F1 per type;
  - intervention share per stage.

  LLM tokens per 1,000 source words sit beside them as the cost normalizer. **D6 §6 has raw token
  counts but not this normalized figure**; add it.
  > Rejected by the operator (2026-10-28): tokens per 1,000 source words is not a sound benchmark,
  > and D6 does not add it. Cost stays as the raw `ops.task.cost` figures D6 §6 reports.
- **Gate targets come from the phase 0 baseline, not from guesses made now** (D7 §9 states gates
  qualitatively for this reason).

### 4.16 Generality: what the design must also serve

The old repository's transfer fixtures were tiny business examples, kept as a generality checklist.
Each names a construct the design must support even though statistics never exercises it:

| Example | Construct |
|---|---|
| ORG-101 "Harbor Systems Ltd", distinct from ORG-202 despite a shared trading name | Multi-attribute identity (Splink), cannot-link |
| "ORG-101 owns P-17, valid 2026-01-01 to 2026-06-30, per ownership.html" | `valid_time` qualifier, attribution, evidence |
| A table cell "High flow · 300" with its header, unit, caption and Note P | Table segments, quantities with units and gauge qualifiers such as kPa(g) (the old quantity grammar does not read gauge suffixes), notes as conditions |
| An inspection duty with a three-part exception | A rule as a derived model: conditions with `or` and `not`, evaluable against facts |
| Email threads | `email_message`, `quoted_block` and `signature` segments; attribution to senders |

When designing anything in `core`, check it against this list.

### 4.17 Deliberately left out, and why

Each item below was plausible, and none earns a place until a measured gap names it:

- **PSL and AMIE rule mining:** induction over claims. They need a mature claim base.
- **cvxpy family selection:** optimization over candidate families; the old repository built it
  without a consumer.
- **Causal discovery:** see §4.8, pgmpy's later role. Discovery needs data, not documents.
- **MinHash source dependence:** for corroboration across copied sources; Siegrist has one source.
- **The retrieval fusion stack and reranking:** retrieval matters for agent packets and examples;
  embeddings alone first (S7).
- **Sealed publication, exact replay of historical executors, process custody:** guarantees without
  a consumer.
- **Hosted LLM tier, multi-tenancy, RDF publication:** later phases.

## 5. Judgment calls made under uncertainty

These were reasoned choices rather than measured ones. Each names what would change it.

| Call | Where | Reasoning | Change it when |
|---|---|---|---|
| Stage barriers | D6 §1 | Simplicity at 78 pages | Runs become long enough that idle GPU time matters |
| Iteration limit 3; agent budget 20 packets per iteration | D6 §2, §7.4 | Keeps debugging output reviewable | The operator finds digests too thin or too long |
| Cold-start priors (agent 0.9, local LLM 0.6/0.4, encoders 0.4, patterns 0.5), noisy-OR, accept threshold 0.8 | D5 §6.3, D6 §7.1 | Order-of-magnitude guesses; noisy-OR assumes independent sources | Enough aligned claims exist to fit the latent model (OPEN-D5-2) |
| Slots: functional predicates keyed by subject, predicate and statement | D5 §5.4 | Only candidates answering the same question should compete | Formula predicates collide (OPEN-D5-1) |
| Core candidates absorbed into full candidates | D5 §5.4 | Encoders cannot produce qualifiers; their value is corroboration | Encoders start producing qualifiers |
| Derived claims excluded from precision, scored for correctness separately | D5 §9, D7 §5.4 | Goldens do not state derived facts by guideline | The guideline changes |
| Golden sets of 40 and 40 units at first | D7 §3.1 | Small while debugging; widen when intervals are too wide | Phase 1 interval widths (OPEN-D7-1) |
| One page in five to test, per chapter | D7 §3.1 | Page-level splits avoid near-duplicate leakage; chapter stratification keeps topics in both | Dev–test gaps suggest chapter-level leakage (OPEN-D7-3) |
| Quote-location thresholds (fuzzy cutoff 85, bounded edits) | D4 §4.3 | Set by the spike | Unlocated rates rise on new models |
| `p.math` → theorem | D2 §12.1 | Siegrist does not distinguish theorem, proposition and corollary in markup; the guideline treats them alike | A consumer needs the distinction |
| `narrative` paragraphs are claim-bearing | D2 core.yaml | T2 is a narrative paragraph with claims | Business text where most narrative is noise; use the fact-bearing classifier (§4.10) |
| Formula keys from the written form, not the parse | D1 §6.2 | §4.5 | — |
| Statement identity by anchor segment | D1 §10.1, design-owner review B3 | Statements are authored units | — |

## 6. Open concerns the new owner inherits

1. **Math density is atypical.** Statistics text is about 35% LaTeX by character, and costs about
   twice the tokens per character. Encoders will look weak here and the LLM tier strong; neither
   generalizes to business text. Do not over-tune the encoder tier to Siegrist, and bring the second
   corpus forward if math dominates the work.
2. **Rules written from twelve units.** Guideline v1 was written from the S0 core units and checked
   on six held-out units. Every revision should keep that discipline (design-owner review A11), or
   the goldens will encode Siegrist's quirks as conventions.
3. **Residual circularity.**
   - Golden context comes from M13, a pipeline method.
   - The guideline's author (the design process) also wrote the trace.
   - Golden author and agent tier are different models of one family.

   The witnesses (D7 §6) are the only fully independent check. Build them early.
4. **Identity across units and pages.** Parameter canonical names (design-owner review B2) and
   families' parameterizations (RG-7) decide whether "the normal's mean parameter" is one entity
   across 78 pages. This will be the first large source of identity errors.
5. **Key stability** (§4.5). Treat any change to canonical form as a key migration.
6. **Process weight** (§4.13).
7. **The output budget of LLM tiers.** Batches run 2–19 times their unit; output caps, not input
   caps, will bind (S3).
8. **External references** ("the last result", "[14]") are the top-ranked representation gap
   (design-owner review A7). Until represented, claims depending on them silently look
   unconditional.

## 7. Where the reasoning lives

| Source | Holds |
|---|---|
| This file | Intent, principles, alternatives, judgment calls, concerns |
| D0–D9, trace | The design itself |
| ADR-0009, ADR-0010, ADR-0011 | Reasons for the decisions taken during the spikes |
| [Design owner's review of S0 and S1](../design_review/evidence/2026-10-28_design-spikes/design-owner-review-S0-S1.md) | Follow-ups and corrections after the spikes |
| Spike reports and `records/` | Evidence for every measured claim |
| Commit messages `e10c4dc`, `3de8664`, `26e74c3` | The design-set additions, the fresh-review fold-in (37 findings) and the Siegrist grounding of the hints |
| The superseded claude.ai overview document | The original reasoning, reproduced in §1–§4 here |

**ADRs still owed** (§4 sections ready to lift):

| Decision | Source section |
|---|---|
| Observations-only methods and consolidation as the sole writer of knowledge | §3 P3 |
| PostgreSQL as the single authority | §4.2 |
| LinkML packs compiled to every consumer | §4.3 |
| The Wikidata-style claim model | §4.4 |
| Agent work through an MCP queue, never pipeline calls | §3 P9, §4.11 |
| Policy-routed escalation on measurements | §3 P4, §4.10 |
| Run-scoped materialization | §4.5 |
