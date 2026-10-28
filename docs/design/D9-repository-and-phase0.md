# D9 · Repository and phase 0 plan

**Proposed (2026-10-28).** Where the code lives, which libraries it pins, how it is tested, who
works in which lane, and the phase 0 build sequence with acceptance criteria. The active plan in
[docs/plans](../plans/README.md) owns execution status; this document owns the target layout and
the sequence's content.

## 1. Layout

The template gives a uv workspace root (`pyproject.toml`, product packages join as members) and
a dormant Rust workspace (`crates/`). Product code is one Python package; domains are data plus
verifier plug-ins.

```text
python/corpus-structure/                 uv workspace member; distribution corpus-structure
  pyproject.toml
  src/corpus_structure/
    core/            D1 types (Pydantic): values, conditions, claims, the keyed candidate claim,
                     keys, canonical JSON; locators (D1 §3.4); tex.py (the TeX tokenizer and token form);
                     db/ (SQLAlchemy Core table metadata from D3), schemas/ (JSON Schemas of D3 §6)
    schema/          LinkML loading (SchemaView) and the D2 §7 compilers
    validate/        M19's runner and the rule-view builder over core types; M20; the Verifier
                     protocol and runner (M21's host)
    ingest/          M01–M03 (source profiles are data in sources/)
    methods/         M04–M16, M22, M24 packets; llm/ (packet, prompts/, parse); gliner/; math/
    consolidate/     M17, M18, M23 (D5)
    orchestrate/     runs, stage graph, tasks, workers, reuse, policies, metrics (D6)
    evaluate/        golden sets, alignment, scoring, witnesses, experiments, digest (D7)
    serve/           generic typed queries, the domain-query protocol, exports (D8 §5–§6)
    intervene/       MCP server and tool implementations (D8 §2)
    cli/             the Typer app and every `ci` command group (D8 §4)
  alembic/           migrations; 0001 is D3
  tests/
domains/
  core/schema/core.yaml
  statistics/        schema/ (statistics.yaml, rules.yaml, migrations/), guideline.md,
                     policies.yaml, methods.yaml, slices.yaml, verifiers.py, queries.py,
                     reference/, README.md
sources/
  siegrist.yaml      the Siegrist source profile (D2 §12.1, D4 M01), named by the packs that read it
fixtures/
  trace/             the trace as data: segments, target entities and claims per unit (from trace.md)
  s0/                the S0/S0-R2 v1 reference as authored batches with their citation frames
                     (D1 §10.3): fixture proposals; the stored form is derived by the quote cascade
                     on the production renditions, keys are never stored
services/vllm-native/                    the vLLM 0.31 environment (separate uv project, own lock)
.claude/skills/work-queue/SKILL.md       how the Claude Code session works the agent queue (D8 §3);
                                         needs a `!/.claude/skills/work-queue/` line in .gitignore
.mcp.json                                registers the MCP server for Claude Code
```

Dependency direction: `core` ← `schema` ← `validate`, and `core` ← `schema` ← (`ingest`,
`methods`) ← `consolidate` ← `orchestrate` ← (`evaluate`, `serve`) ← `intervene` ← `cli`, with
`consolidate` using `validate` (P0CL-08; operator, 2026-10-28). `validate` sits below
`consolidate` because M19 runs at two call sites, inside `intervene`'s `propose_claims` at
submission and inside consolidation's finalize pass (D5 §8.2). Its runner and the rule-view
builder work over the `core` keyed candidate claim, which a submitted batch and the candidate pool
each adapt into, so `validate` imports neither consolidation's pool nor the batch parser. Domain
plug-ins implement protocols declared in the generic packages: `domains/<name>/verifiers.py`
`validate`'s Verifier, `domains/<name>/queries.py` `serve`'s query protocol (D2 §7.6, D8 §5.2), so
no generic package names a domain predicate (P0CL-07). Source profiles are data in `sources/`,
outside every pack (D2 §12.1).
> Status: **Proposed** (2026-10-28)

The entry points sit on top: the MCP tools call `serve`'s queries (D8 `query`, `explain`),
and `cli` holds the Typer app and every `ci` command group, so `serve` holds queries and exports
only and Typer and Rich stay out of the lower layers ([interfaces note](../design_review/evidence/2026-10-28_library-interfaces-eval/README.md) IE-7). The
direction is a design rule checked at design reviews; no lint enforces it (an ast-grep rule is
added only from a design-review finding).

**Size.** v1 aims at about 15k lines of product code, the guardrail the design rationale sets
against the old repository's 566k. It is a reading for the end-of-phase review, not a lint; the
spike reference implementations alone are about 8.3k lines, so ports are rewritten against the
contracts rather than copied.

The Rust workspace stays the template's starter crate. No product Rust is planned for phases
0–3; a hot path measured as a bottleneck would be the reason to add one.

## 2. Dependencies

Pinned exactly (`pin-check` skill; `just deps`). Versions below are those S0/S1 tested where they
ran a library, otherwise those the library overviews in [docs/libraries](../libraries/README.md)
document; packages without either take the latest release at phase 0 start, recorded in
`docs/pins.md` when held. Phase 0 installs only what phase 0 methods use (the phase 0 plan's
foundations package); GPU and phase 1–2 libraries arrive with their phases.

| Package | Version | Used by |
|---|---|---|
| pydantic, pydantic-settings | 2.14.1, 2.16.0 | core types, method configs, settings |
| sqlalchemy, psycopg[binary], psycopg-pool, alembic | 2.1.5, 3.3.6, 3.3.3, 1.20.0 | core.db, migrations, bulk COPY |
| pgvector (Python) | 0.5.1 (server extension 0.8.7; [overview](../libraries/pgevector.md)) | `halfvec` column type (phase 1, with `kb.embedding`) |
| pg_textsearch (server extension) | 1.5.1 (Debian package `postgresql-18-pg-textsearch`; [overview](../libraries/postgresql-18-pg-textsearch.md)) | BM25 lexical search for `find` (D3 §5, D8 §5.1). A phase 0 server prerequisite: in `shared_preload_libraries`, and created once by the operator in the template database, so the cloned test databases (§4) carry it |
| linkml (runtime and generators) | 1.12.1 | schema |
| rule-engine | 5.1.0 | M19, policies |
| gliner2 | 2.1.0 | M05–M07 (phase 1; the product environment carries no gliner2 or torch in phase 0) |
| spacy, en_core_web_sm | 3.8.18, 3.8.0 | M03, M08, M13, M22 |
| lxml, html5lib | 6.1.3, 1.1 ([overview](../libraries/html5lib.md)) | M01 (html5lib parser through `lxml.html.html5parser`; D4 M01) |
| cssselect2 | 0.10.1 | M01's role engine (`Matcher`; D4 M01) |
| regex | 2026.9.29 | M01 delimiter pattern, the quote cascade (D4 §4.3), M22 lexicons |
| tokenizers | 0.23.3 | M02 token counts, LLM-tier packet caps (D4 §4.1; agent-tier caps are characters) |
| PyYAML | 6.0.3 | pack files |
| jsonschema (dev) | 4.26.0 ([overview](../libraries/jsonschema.md)) | an independent oracle in tests and `check_schema` on generated artifacts; production validates with Pydantic (D2 §7.3, D3 §6) |
| sympy, lark | 1.14.0 (hold, `docs/pins.md`), 1.3.1 | M11 (grammar from phase 0, SymPy conversion from phase 1), M21, alignment |
| pint | latest | M12 |
| z3-solver | 5.3.2.0 | M20 |
| scipy, numpy | 1.18.1, 2.5.4 | M21, alignment |
| rapidfuzz | 3.14.6 | M14, quote location |
| splink, duckdb | 5.0.0, 2.0.0 | M15, analytics, Parquet export |
| pgmpy, scikit-learn | 1.1.2, 1.9.1 | confidence model, calibration |
| networkx | 3.7 | statement and claim graph utilities |
| fastmcp | 4.1.3 | intervene |
| typer, rich | 0.27.3, 15.0.0 | CLI |
| vLLM | as in `services/vllm-native` ([overview](../libraries/vllm.md)) | M10, M16, M04 pooling if S7 chooses it (phase 1) |
| httpx (or openai) | latest | M10, M16 client to vLLM |
| sentence-transformers | latest, only if S7 chooses in-process embeddings | M04 |
| torch | 2.13.0 (as in the vLLM environment) | GLiNER2, embeddings (phase 1) |
| ppi_python (`ppi_py`) | 0.2.3 ([overview](../libraries/ppi_py.md)), phase 2 | the random audit's corpus-level precision (D7 §6, OPEN-D7-4) |
| Hypothesis, hypothesis-jsonschema (dev) | 6.170.12, latest at P0.1 ([overview](../libraries/hypothesis.md)) | property, stateful and grammar-generated tests (§4) |

**Python 3.14.** The root requires ≥ 3.14, and the vLLM environment already runs torch 2.13 on
3.14. Whether gliner2, spaCy, z3 and pgmpy ship 3.14 wheels is checked by the spikes' environment
(`OPEN-D9-1`). **Tested** for the S0/S1 set (2026-10-28, [e0.environment](../design_review/evidence/2026-10-28_design-spikes/records/e0.environment.json)): on 3.14.10 spaCy 3.8.18 with `en_core_web_sm`/`trf` 3.8.0, spacy-curated-transformers, torch 2.14.1 (CPU), lxml, html5lib, sympy 1.14.0, lark, pydantic, linkml-runtime, rapidfuzz, scipy and statsmodels install and import; DuckDB 2.0 installs from its abi3 wheel. gliner2, z3, pgmpy and splink remain for S2, S4 and S5. A missing wheel is resolved per package (build from source, or isolate that method
in a side environment like vLLM), never by lowering the product's Python version silently.

## 3. Conventions

- **Types.** D1 objects are Pydantic models in `core` (frozen, `extra="forbid"`; D2 §6 says why
  they, not LinkML, own the shared shapes); database access is SQLAlchemy Core (no ORM). JSONB is
  validated once at the Pydantic boundary with the compiled per-version models, and
  `core/schemas/*.json` are generated from them (D3 §6).
- **Settings.** `pydantic-settings`: database URL, data directory for originals, model cache,
  vLLM endpoint, GPU mode; environment prefix `CORPUS_` (CI systems set `CI` and `CI_*`), `__` for
  nested fields, only constructor and environment sources. Settings are built once at the entry
  point (`cli`, the MCP server's lifespan) and passed down; `extra="forbid"` does not catch a
  mistyped variable, so `ci status` prints the settings it resolved ([interfaces note](../design_review/evidence/2026-10-28_library-interfaces-eval/README.md) §4).
  No configuration in code paths.
- **Connections.** One psycopg-pool per process; SQLAlchemy borrows from it (D3 §1). The MCP
  server's lifespan, which runs once per stdio process, holds its pool; tools are synchronous and
  run on FastMCP's worker threads, so they call the same application functions as the CLI, and
  never the math grammar, whose timeout needs a main thread (D2 §7.4).
- **Methods** follow the D4 §1 contract; a method's tests run it on trace units with fixtures.
- **Determinism.** Keys from canonical JSON (D1 §10.1); LLM calls with `temperature: 0` and a
  seed; no wall-clock or random input to any key or digest.
- **Logging** through the standard library, one line per task outcome at INFO; payloads never
  logged.

## 4. Tests

| Layer | What | How |
|---|---|---|
| Types and keys | Canonical JSON, keys, condition canonicalization, value canonical forms | Unit and Hypothesis property tests (permuted keys, reordered `and` arguments give equal keys); D1 models drawn by `st.builds`/`st.from_type` with strategies registered for constrained fields (`st.from_regex` where a model uses `Field(pattern=…)`, which `from_type` ignores) |
| Math | The token form against the tree printer wherever the grammar reads a span (KEYS-01) | A corpus layer over every first-pass span, and generated layers: strings from the grammar itself (`hypothesis.extra.lark.from_lark`, with explicit strategies for the macro terminals) and metamorphic rewrites of the token form (sizing commands, spacing, brace-equivalent forms); failures shrink to a minimal formula ([Hypothesis overview](../libraries/hypothesis.md) §6.5) |
| Batches | The compiled batch models and the exported JSON Schema agree | `hypothesis-jsonschema.from_schema` draws batches from the exported schema, where its draft support covers it, and Pydantic and jsonschema must both accept them; jsonschema errors are compared sorted by `absolute_path`, since `iter_errors` order is not guaranteed ([jsonschema overview](../libraries/jsonschema.md) §2.1, §9.2) |
| Task lifecycle | Claiming, lease renewal and expiry, fencing, terminal writes and reuse keep the D6 §3 invariants (no task held twice, a lost lease commits nothing, reuse only of `done`/`empty` results) | A `RuleBasedStateMachine` whose bundles hold tasks and workers, `consumes` for terminal writes, invariants after every step against a small reference model, each example in its own rolled-back transaction ([Hypothesis overview](../libraries/hypothesis.md) §4, §10.1); real interleavings are S6's concurrency test, since state machines do not explore scheduling |
| Database | Migration 0001 applies and downgrades (upgrade, downgrade to base, the four schemas empty, upgrade again); the catalog after `upgrade head` equals `create_all`'s, since `alembic check` misses index methods, partial predicates and CHECK bodies; invariants as constraints | A per-session test database cloned from a migrated template keyed by the migrations' hash (`CREATE DATABASE … TEMPLATE`), dropped `WITH (FORCE)`; most tests roll back an outer transaction ([store note](../design_review/evidence/2026-10-28_library-store/README.md) §1) |
| Ingest | Trace segments and offsets; S1 counts | `fixtures/trace/*.segments.json`; corpus-gated tests skipped when `docs/statistics_corpus` is absent |
| Methods | Each method on trace units | Fixtures; GPU tests marked `gpu`; LLM tests replay recorded responses (stored under `fixtures/llm/`) so they are deterministic and offline |
| Consolidation | The trace through D5: proposals from `fixtures/s0` produce the trace's target claims and keys | End-to-end on the trace slice without GPU or agent |
| Acceptance | The trace's typed questions (D8 §5.3) answered from the database after a `trace` slice run with `agent_mode: complete`, the `fixtures/s0` batches for its units submitted through the MCP tools in process (FastMCP's `Client`), and a rerun that reuses them (D6 §4), so the test is deterministic and needs no live agent. Phase 0 checks every trace target except derived claims (T3 D1, phase 2), with scopes and bindings as the proposals state them (D5 §11). Comparisons are by locator and structure, never by literal keys: the fixtures hold authored batches and no keys, and the test checks answers, not the key function (D1 §10.1). The live Opus `trace` and `spike-pages` runs are qualification evidence: their typed-query rows are aligned to expectations derived from the re-authored dev goldens (D7 §9) | `tests/acceptance/test_trace.py`; the phase 0 gate |
| Evaluation | Alignment tiers on hand-made golden/run pairs, including formula equivalence and faithful ambiguity; interval figures reproduced from a recorded seed and unit order | Unit tests |
| Interfaces | MCP tools through one shared in-process `Client(mcp)` fixture (sequential clients re-enter the lifespan); `ci` through Typer's `CliRunner` with stdout and stderr apart and the Rich width fixed | Unit and acceptance tests ([interfaces note](../design_review/evidence/2026-10-28_library-interfaces-eval/README.md) §1, §3) |

The trace is the acceptance spine: a design change that alters a trace target changes
`trace.md`, the fixtures and these tests together.

## 5. Phase 0 build plan

The [phase 0 plan series](../plans/phase-0_2026-10-28.md) owns sequencing, dependencies and packages; the table below states
each step's content and acceptance, and its "Depends on" column is indicative.

Goal (D0): the meta-model in PostgreSQL, HTML ingest, Opus intervention tools, the query API and
the evaluation harness; Opus extracts the claims of the `phase0-golden` slice (the pages holding
dev golden units, the forced-dev pages, and the trace and core-unit pages; D7 §9), while the full
first pass is a phase 1 run with M10 (P0CL-09; operator, 2026-10-28); the trace units and spike
pages answer their typed questions from the database; evaluation runs.

| Step | Builds | Depends on | Acceptance |
|---|---|---|---|
| P0.1 | Package skeleton as a workspace member; settings; `ci` with `--help` | — | `just check` passes with the package's first tests |
| P0.2 | `core`: values, conditions, claims, the keyed candidate claim, canonical JSON, keys, `core/tex.py`, and the locator generator and resolver (D1 §3.4; owned by ingest and math); `fixtures/trace` and `fixtures/s0` as authored batches with citation frames | P0.1 | Property tests; the trace's claims construct and key deterministically |
| P0.3 | Migration 0001 (D3, with S6 corrections); `ci db init`, `ci db migrate` | P0.2, S6 | Upgrade and downgrade on a test database; trace rows of D3 §10 insert and the D3 §9 queries return them |
| P0.4 | `schema`: load `core.yaml` and `statistics.yaml` v0; compilers to schema tables, JSON Schema (both forms, with `cN` citations), the **annotator reference** (D2 §7.5, §10.10, with the worked examples), rules (compiled) including the **`guideline:` warning group** (D2 §7.4); the M19 runner and the rule-view builder in `validate/` over the `core` keyed candidate claim, with the D5 §8.2 context at both call sites and the pack's `views:` compiled (D2 §7.4), submission-time views reading symbols with `core/tex.py` and grammar-dependent rules `at: [finalize]`; compiled artifacts keyed by schema version, compiler, compiler version and kind (D2 §7); `ci schema compile` (GLiNER2 dicts are compiled from phase 1, D2 §7.2) | P0.2, S4 | Deterministic artifact hashes; a compiler version change adds artifacts beside the old ones; a rule with a type error fails compilation; the v1 reference batches validate against the model-facing schema, and their stored form against the stored schema; the generated reference for schema v0 carries the information of `results/s0r2/inputs/packet_v1/reference.md`; the v1 reference and the examples give 0 guideline warnings, and each seeded violation is caught |
| P0.5 | `ingest`: M01 with the Siegrist source profile (`sources/siegrist.yaml`, D2 §12.1; every source fact read from the profile, including `sections`, references and the rendering conventions), the html5lib parser, content-addressed renditions with their builds (D1 §3.1), M02, M03 (variant b′ from S1) | P0.3, S1 | Trace segment fixtures match; S1 count criterion holds on the 78 pages; invariants hold; canonical text equals the spike renditions on the S0/S0-R2 pages (rendition identity, A12) |
| P0.5b | Math grammar and scoping: the one math grammar (M11's grammar part: validation, slot typing, canonical form; SymPy conversion stays phase 1), M09 symbol occurrences, both run per rendition with per-span observations; M13 binding sites; packet standing context from M13 (D4 §4.1) | P0.5, S5 | The S0 M13 probe's 20 of 20 scopes; delimiting reproduces S1's 8 `partial` spans; the property test that tree printer and token form agree on every parsed value (D1 §6.2, ADR-0012); grammar coverage reported per page, not a gate; the trace and core units' packets give the context of `results/s0r2/sample.json` |
| P0.6 | `ci project init` (project, documents, versions, named configurations, slices by locator); `orchestrate` minimum: runs with their recorded reference run, tasks, queue, reuse by content digest, the stages `ingest → normalize (grammar, M09) → scope (M13) → propose → assemble → finalize → measure → evaluate` (D6 §2), with M19 as one run-level step inside finalize and no `check` stage in phase 0; a recorded fate for every eligible unit (`skipped` with reason `scope` outside the run's scope, D6 §7.4, §8); `methods.yaml` loaded into the method registry; the agent barrier (`wait` for short slice runs, `complete` with reuse for long ones) | P0.3, P0.5b | A `trace` slice run creates `awaiting_agent` tasks; a second run reuses the ingest tasks; a run scoped to `phase0-golden` records every other eligible unit as `skipped` with reason `scope` |
| P0.7 | `intervene`: MCP server with queue tools, `read_instructions`, `propose_claims` (validation, quote location, M19 at the `batch` call site), packet assembly from recorded inputs with caps in characters (D4 §4.1, D8 §3), the M24 extract prompt (`methods/llm/prompts/extract.md`); golden tools leased on the task queue (`read_golden_unit` serves the guideline, the annotator reference and the query-assembled packet; `write_golden` stores the authored batch with its citation frame, records the model and the inputs, D3 `eval.golden_pass`, returns guideline warnings, and creates the pass-C task in the transaction that stores the second of passes A and B), `record_direction`; the work-queue skill, which dispatches golden passes to Sonnet subagents (ADR-0011; `adjudicate` follows in phase 1) | P0.4, P0.6 | Submitting a v1 reference batch completes a task; errors and warnings come back per item; a golden pass without model or inputs is refused |
| P0.8 | `consolidate` phase 0 realization (D5 §11), with M19 at finalize as one run-level step over the in-memory pool, bulk-writing `verification` observations | P0.6, P0.7 | Fixture proposals for the trace produce the target claims, statements, bindings that the proposals state, and invariants |
| P0.9 | `serve`: the generic queries of D8 §5.1 and the domain-query protocol, with the run selector, pinning and coverage (D8 §5); the statistics queries of D8 §5.2 in `domains/statistics/queries.py`; `ci query` (exports are phase 1, D8 §6) | P0.8 | The trace acceptance test passes; a query over a run with skipped units reports partial coverage; a promotion between pages leaves a page token's run unchanged |
| P0.10 | `evaluate`: page split with reserved pages and the forced-dev pages of D7 §3.1, unit sampler (`ci golden split`, `ci golden create`), context-premise scoring (D7 §5.1), golden sets (dev 40, test 40; trace and core units forced into dev), goldens keyed by unit key with items derived per rendition (D7 §3.1), the `phase0-golden` page set, alignment tiers, scores with bootstrap intervals, the pre-registered promotion readings (D7 §7 item 5), `ci eval`, digest v0 | P0.7, P0.8 | Alignment unit tests; scoring a run against S0 references gives the S0 A-versus-B numbers when fed the passes |
| P0.11 | Phase 0 runs: `trace`, then `spike-pages`, then the phase 0 first pass: successive `agent_mode: complete` runs over the first-pass corpus scoped to the `phase0-golden` slice (D6 §8), each reusing finished tasks, with Opus working the queue between them (every other eligible unit `skipped` with reason `scope`; the full first pass is a phase 1 run with M10, D7 §9); goldens authored by the D7 protocol (Sonnet passes and adjudication, ADR-0011) | all | The D0 phase 0 gate (D7 §9): the sequence converges with no unresolved agent task, and the operator promotes that run with `ci promote` after reading the pre-registered readings |

P0.2–P0.4 can proceed in parallel with the spikes S1, S4 and S6, absorbing their results as they
land; P0.5 waits for S1, P0.3 for S6.

## 6. Lanes

| Lane | Who | Writes | Reads |
|---|---|---|---|
| Spikes | The in-repo agent | `docs/design_review/evidence/2026-10-28_design-spikes/` only | D-documents, corpus |
| Library leverage | A parallel in-repo agent | `docs/library_leverage/` accounts; **Library realization** subsections of D4 cards directly; `> Library proposal (L-nn):` blocks anywhere a contract would change | D-documents, library overviews |
| Design owner | The in-repo agent (primary design authority from 2026-10-28); the project-conversation Claude reviews for missing reasoning | D-documents, trace, ADRs, plan dispositions | Spike reports, leverage outputs |
| Build (from phase 0 start) | The in-repo agent, per the active plan | `python/`, `domains/`, `fixtures/`, tests | D-documents, accepted spike results |
| Operator | Paul | Directions, acks, vetoes; plan approval | Digests, plan, reports |

Conflicts are avoided by ownership: no lane edits another lane's files, and a design change
reaches the build lane only through a D-document change recorded in the plan.

## 7. What comes from corpus-intelligence

The old repository is read-only. Ported means reimplemented against the new contracts, keeping
the rules and test cases that encoded real corpus behaviour; nothing is copied with its old
contracts.

| Source (`python/corpus/src/corpus/…`) | Lines | Treatment | Target |
|---|---|---|---|
| `source/html_adapter.py` | 1,017 | Port the rules (exclusions, details and summary, entities, TeX retention, link resolution) and its test cases | M01, Siegrist source profile |
| `ident/quantity.py` (Lark grammar), `ident/units.py` | 506, 352 | Port code and tests largely as is: the grammar and pint unit policy are domain-neutral | M12 |
| `source/table_model.py`, `source/quantities.py` | 360, 368 | Port when tables matter (rare in Siegrist; essential for the second corpus) | M01 tables, M12 |
| `ident/domain_quantities.py` | 192 | Reference only | M12 |
| `evidence/corpus_queries.py` | 737 | Functional specification of statistics questions; reimplemented over claims | D8 §5.2 |
| `endpoints/native_spans.py` | 1,240 | Reference for GLiNER GPU session lifetimes; not ported | M06, M07 |
| `link/identity_matching.py` | 273 | Reference for person and organization identity in business corpora (phase 5) | M14, M15 later |
| `evidence/_analysis_kernels.py` | 439 | Not ported | — |
| `services/vllm-native/` (`pyproject.toml`, `uv.lock`) | — | Reuse the environment; run vLLM's standard OpenAI-compatible server instead of the old private socket protocol; `engine.py` is a reference for structured outputs and the reasoning parser | M10, M16, S3 |
| `fixtures/siegrist_three_sections/expectations.toml` | — | Cross-check for trace data | `fixtures/trace` |
| `runs/domain_laws.py` | 1,732 | Mined for rule patterns (validation rules and routing conditions), not ported | `rules.yaml`, `policies.yaml` (M19, D6 §7) |
| `fixtures/pdt_domain_transfer/`, `fixtures/micro_corpus/` | — | Kept in reserve as the generality check's examples (DESIGN §1.3) | design reviews; phase 5 |

**From the design spikes** (`../design_review/evidence/2026-10-28_design-spikes/code/`): tested reference implementations, ported against
the D-document contracts with their tests (`code/tests_instruments`), not copied as spike code.

| Spike code | Target |
|---|---|
| `s1_adapter.py`, `profile/siegrist.yaml` | M01, M03; the Siegrist source profile `sources/siegrist.yaml` (D2 §12.1) |
| `mathgrammar/` | the one math grammar: M09, M11's grammar part, canonical form (ADR-0012) |
| `m13_binders.py`, `s0r2_sample.py` | M13; packet standing context (D4 §4.1) |
| `s0_locate.py` | the quote cascade (`methods.llm.parse`, D4 §4.3) |
| `s0r2_inputs.py`, `s0r2_rules.py` | the annotator-reference compiler and the `guideline:` rules (P0.4) |
| `instruments/` (align, conditions, keys, values, validate, scores) | `core` keys and canonical JSON, and the batch validator. Where the alignment and scoring instruments live long-term, in `evaluate/`, in the evidence tooling or shared, waits on the operator's design of the evidence system and its reusable apparatus |

## 8. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D9-1 | Python 3.14 wheels for gliner2, spaCy and its model, z3-solver, pgmpy, splink | Spike environment setup (S1, S2, S4, S5) |
| OPEN-D9-2 | Whether the MCP server and the orchestrator share one process (D8 `OPEN-D8-1`) | **Decided** (2026-10-28): two processes, the database the only shared state (D6 §1) |
