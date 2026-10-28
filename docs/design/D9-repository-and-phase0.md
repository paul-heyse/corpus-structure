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
    core/            D1 types (Pydantic): values, conditions, claims, keys, canonical JSON;
                     db/ (SQLAlchemy Core table metadata from D3), schemas/ (JSON Schemas of D3 §6)
    schema/          LinkML loading (SchemaView) and the D2 §7 compilers
    ingest/          M01–M03, source profiles
    methods/         M04–M16, M22, M24 packets; llm/ (packet, prompts/, parse); gliner/; math/
    consolidate/     M17, M18, M23 (D5)
    validate/        M19, M20, the Verifier protocol and runner (M21's host)
    orchestrate/     runs, stage graph, tasks, workers, reuse, policies, metrics (D6)
    evaluate/        golden sets, alignment, scoring, witnesses, experiments, digest (D7)
    intervene/       MCP server and tool implementations (D8 §2)
    serve/           typed queries, exports, the `ci` CLI (D8 §4–§6)
  alembic/           migrations; 0001 is D3
  tests/
domains/
  core/schema/core.yaml
  statistics/        schema/ (statistics.yaml, rules.yaml, migrations/), guideline.md,
                     policies.yaml, methods.yaml, slices.yaml, verifiers.py, reference/, README.md
fixtures/
  trace/             the trace as data: segments, target entities and claims per unit (from trace.md)
  s0/                adjudicated S0 reference batches (copied from the spike results when accepted)
services/vllm-native/                    the vLLM 0.31 environment (separate uv project, own lock)
.claude/skills/work-queue/SKILL.md       how the Claude Code session works the agent queue (D8 §3);
                                         needs a `!/.claude/skills/work-queue/` line in .gitignore
.mcp.json                                registers the MCP server for Claude Code
```

Dependency direction is as in the [architecture map](README.md): `core` ← `schema` ← (`ingest`,
`methods`) ← `consolidate` ← `validate` ← `orchestrate` ← (`evaluate`, `intervene`, `serve`). An
import-linter contract (or an ast-grep rule from a design-review finding) enforces it once the
packages exist.

The Rust workspace stays the template's starter crate. No product Rust is planned for phases
0–3; a hot path measured as a bottleneck would be the reason to add one.

## 2. Dependencies

Pinned exactly (`pin-check` skill; `just deps`). Versions below are those the library overviews
in [docs/libraries](../libraries/README.md) document; packages without an overview take the
latest release at phase 0 start, recorded in `docs/pins.md` when held.

| Package | Version | Used by |
|---|---|---|
| pydantic, pydantic-settings | 2.14.1, 2.16.0 | core types, method configs, settings |
| sqlalchemy, psycopg[binary], psycopg-pool, alembic | 2.1.5, 3.3.6, 3.3.3, 1.20.0 | core.db, migrations, bulk COPY |
| pgvector (Python) | latest | `halfvec` column type |
| linkml (runtime and generators) | 1.12.1 | schema |
| rule-engine | 5.1.0 | M19, policies |
| gliner2 | 2.1.0 | M05–M07 |
| spacy, en_core_web_sm | 3.8.16, 3.8.x | M03, M08, M13, M22 |
| lxml, html5lib | latest | M01 (html5lib parser through `lxml.html.html5parser`; D4 M01) |
| pylatexenc | 3.0b2 (spike) | M01: page macro tables and the balance check of delimited spans; math itself is read by the grammar (ADR-0012) |
| sympy, lark | 1.14.0, latest | M11, M21, alignment |
| pint | latest | M12 |
| z3-solver | 5.3.2.0 | M20 |
| scipy, numpy | 1.18.1, 2.5.4 | M21, alignment |
| rapidfuzz | 3.14.6 | M14, quote location |
| splink, duckdb | 5.0.0, 2.0.0 | M15, analytics, Parquet export |
| pgmpy, scikit-learn | 1.1.2, 1.9.1 | confidence model, calibration |
| networkx | 3.7 | statement and claim graph utilities |
| fastmcp | 4.1.3 | intervene |
| typer, rich | 0.27.3, 15.0.0 | CLI |
| httpx (or openai) | latest | M10, M16 client to vLLM |
| sentence-transformers | latest, only if S7 chooses in-process embeddings | M04 |
| torch | 2.13.0 (as in the vLLM environment) | GLiNER2, embeddings |
| ppi_python | phase 2, if D7 §6 keeps it | audits |

**Python 3.14.** The root requires ≥ 3.14, and the vLLM environment already runs torch 2.13 on
3.14. Whether gliner2, spaCy, z3 and pgmpy ship 3.14 wheels is checked by the spikes' environment
(`OPEN-D9-1`). **Tested** for the S0/S1 set (2026-10-28, [e0.environment](../design_review/evidence/2026-10-28_design-spikes/records/e0.environment.json)): on 3.14.10 spaCy 3.8.18 with `en_core_web_sm`/`trf` 3.8.0, spacy-curated-transformers, torch 2.14.1 (CPU), lxml, html5lib, sympy 1.14.0, lark, pydantic, linkml-runtime, rapidfuzz, scipy and statsmodels install and import; DuckDB 2.0 installs from its abi3 wheel. gliner2, z3, pgmpy and splink remain for S2, S4 and S5. A missing wheel is resolved per package (build from source, or isolate that method
in a side environment like vLLM), never by lowering the product's Python version silently.

## 3. Conventions

- **Types.** D1 objects are Pydantic models in `core`; database access is SQLAlchemy Core
  (no ORM); JSONB columns are validated against `core/schemas` on write.
- **Settings.** `pydantic-settings`: database URL, data directory for originals, model cache,
  vLLM endpoint, GPU mode. No configuration in code paths.
- **Methods** follow the D4 §1 contract; a method's tests run it on trace units with fixtures.
- **Determinism.** Keys from canonical JSON (D1 §10.1); LLM calls with `temperature: 0` and a
  seed; no wall-clock or random input to any key or digest.
- **Logging** through the standard library, one line per task outcome at INFO; payloads never
  logged.

## 4. Tests

| Layer | What | How |
|---|---|---|
| Types and keys | Canonical JSON, keys, condition canonicalization, value canonical forms | Unit and Hypothesis property tests (permuted keys, reordered `and` arguments give equal keys) |
| Database | Migration 0001 applies and downgrades; invariants as constraints | A per-session test database on the local PostgreSQL 18 (`ci_test_<pid>`), dropped after |
| Ingest | Trace segments and offsets; S1 counts | `fixtures/trace/*.segments.json`; corpus-gated tests skipped when `docs/statistics_corpus` is absent |
| Methods | Each method on trace units | Fixtures; GPU tests marked `gpu`; LLM tests replay recorded responses (stored under `fixtures/llm/`) so they are deterministic and offline |
| Consolidation | The trace through D5: proposals from `fixtures/s0` produce the trace's target claims and keys | End-to-end on the trace slice without GPU or agent |
| Acceptance | The trace's typed questions (D8 §5.3) answered from the database after a `trace` slice run. Phase 0 checks every trace target except derived claims (T3 D1, phase 2), with scopes and bindings as the proposals state them (D5 §11) | `tests/acceptance/test_trace.py`; the phase 0 gate |
| Evaluation | Alignment tiers on hand-made golden/run pairs, including formula equivalence and faithful ambiguity | Unit tests |

The trace is the acceptance spine: a design change that alters a trace target changes
`trace.md`, the fixtures and these tests together.

## 5. Phase 0 build plan

Goal (D0): the meta-model in PostgreSQL, HTML ingest, Opus intervention tools, the query API and
the evaluation harness; Opus extracts all claims; the trace units and spike pages answer their
typed questions from the database; evaluation runs.

| Step | Builds | Depends on | Acceptance |
|---|---|---|---|
| P0.1 | Package skeleton as a workspace member; settings; `ci` with `--help` | — | `just check` passes with the package's first tests |
| P0.2 | `core`: values, conditions, claims, canonical JSON, keys | P0.1 | Property tests; the trace's claims construct and key deterministically |
| P0.3 | Migration 0001 (D3, with S6 corrections); `ci db init`, `ci db migrate` | P0.2, S6 | Upgrade and downgrade on a test database; trace rows of D3 §10 insert and the D3 §9 queries return them |
| P0.4 | `schema`: load `core.yaml` and `statistics.yaml` v0; compilers to schema tables, JSON Schema (both forms, with `cN` citations), the **annotator reference** (D2 §7.5, §10.10, with the worked examples), rules (compiled) including the **`guideline:` warning group** (D2 §7.4), GLiNER2 dicts (compiled, unused until phase 1); `ci schema compile` | P0.2, S4 | Deterministic artifact hashes; a rule with a type error fails compilation; the v1 reference batches validate against the model-facing schema, and their stored form against the stored schema; the generated reference for schema v0 carries the information of `results/s0r2/inputs/packet_v1/reference.md`; the v1 reference and the examples give 0 guideline warnings, and each seeded violation is caught |
| P0.5 | `ingest`: M01 with the Siegrist source profile (D2 §12.1; every source fact read from the profile, including `sections`, references and the rendering conventions), the html5lib parser, M02, M03 (variant b′ from S1) | P0.3, S1 | Trace segment fixtures match; S1 count criterion holds on the 78 pages; invariants hold; canonical text equals the spike renditions on the S0/S0-R2 pages (rendition identity, A12) |
| P0.5b | Math grammar and scoping: the one math grammar (M11's grammar part: validation, slot typing, canonical form; SymPy conversion stays phase 1), M09 symbol occurrences, M13 binding sites; packet standing context from M13 (D4 §4.1) | P0.5, S5 | The S0 M13 probe's 20 of 20 scopes; delimiting reproduces S1's 8 `partial` spans; the property test that tree printer and token form agree on every parsed value (D1 §6.2, ADR-0012); grammar coverage reported per page, not a gate; the trace and core units' packets give the context of `results/s0r2/sample.json` |
| P0.6 | `ci project init` (project, documents, versions, named configurations, slices by locator); `orchestrate` minimum: runs, tasks, queue, reuse, the stages `ingest → normalize (grammar, M09) → scope (M13) → propose → assemble → check (M19) → finalize → measure` (D6 §2), agent barrier (`wait`) | P0.3, P0.5b | A `trace` slice run creates `awaiting_agent` tasks; a second run reuses the ingest tasks |
| P0.7 | `intervene`: MCP server with queue tools, `read_instructions`, `propose_claims` (validation, quote location), golden tools (`read_golden_unit` serves the guideline, the annotator reference and the query-assembled packet; `write_golden` records the model and the inputs, D3 `eval.golden_pass`, and returns guideline warnings), `record_direction`; the work-queue skill, which dispatches golden passes to Sonnet subagents (ADR-0011; `adjudicate` follows in phase 1) | P0.4, P0.6 | Submitting a v1 reference batch completes a task; errors and warnings come back per item; a golden pass without model or inputs is refused |
| P0.8 | `consolidate` phase 0 realization (D5 §11) | P0.6, P0.7 | Fixture proposals for the trace produce the target claims, statements, bindings that the proposals state, and invariants |
| P0.9 | `serve`: typed queries of D8 §5.1–§5.3, `ci query`, claims JSONL export | P0.8 | The trace acceptance test passes |
| P0.10 | `evaluate`: page split with reserved pages and the forced-dev pages of D7 §3.1, unit sampler (`ci golden split`, `ci golden create`), context-premise scoring (D7 §5.1), golden sets (dev 40, test 40; trace and core units in dev), alignment tiers, scores with bootstrap intervals, `ci eval`, digest v0 | P0.7, P0.8 | Alignment unit tests; scoring a run against S0 references gives the S0 A-versus-B numbers when fed the passes |
| P0.11 | Phase 0 runs: `trace`, then `spike-pages`, then `first-pass` with Opus working the queue (test-split units are not sent to the agent and stay unextracted in phase 0); goldens authored by the D7 protocol (Sonnet passes and adjudication, ADR-0011) | all | The D0 phase 0 gate (D7 §9) |

P0.2–P0.4 can proceed in parallel with the spikes S1, S4 and S6, absorbing their results as they
land; P0.5 waits for S1, P0.3 for S6.

## 6. Lanes

| Lane | Who | Writes | Reads |
|---|---|---|---|
| Spikes | The in-repo agent | `docs/design_review/evidence/2026-10-28_design-spikes/` only | D-documents, corpus |
| Library leverage | A parallel in-repo agent | `docs/library_leverage/` accounts; **Library realization** subsections of D4 cards directly; `> Library proposal (L-nn):` blocks anywhere a contract would change | D-documents, library overviews |
| Design owner | Claude in the project conversation | D-documents, trace, plan dispositions | Spike reports, leverage outputs |
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

**From the design spikes** (`../design_review/evidence/2026-10-28_design-spikes/code/`): tested reference implementations, ported against
the D-document contracts with their tests (`code/tests_instruments`), not copied as spike code.

| Spike code | Target |
|---|---|
| `s1_adapter.py`, `profile/siegrist.yaml` | M01, M03; the Siegrist source profile in `domains/statistics/methods.yaml` (D2 §12.1) |
| `mathgrammar/` | the one math grammar: M09, M11's grammar part, canonical form (ADR-0012) |
| `m13_binders.py`, `s0r2_sample.py` | M13; packet standing context (D4 §4.1) |
| `s0_locate.py` | the quote cascade (`methods.llm.parse`, D4 §4.3) |
| `s0r2_inputs.py`, `s0r2_rules.py` | the annotator-reference compiler and the `guideline:` rules (P0.4) |
| `instruments/` (align, conditions, keys, values, validate, scores) | `core` keys and canonical JSON, and the batch validator. Where the alignment and scoring instruments live long-term, in `evaluate/`, in the evidence tooling or shared, waits on the operator's design of the evidence system and its reusable apparatus |

## 8. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D9-1 | Python 3.14 wheels for gliner2, spaCy and its model, z3-solver, pgmpy, splink | Spike environment setup (S1, S2, S4, S5) |
| OPEN-D9-2 | Whether the MCP server and the orchestrator share one process (D8 `OPEN-D8-1`) | P0.7 |
