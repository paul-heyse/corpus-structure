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
    model/           the corpus-structure model (ADR-0020): core.yaml and system.yaml, the model
                     revision's modules, and revisions.yaml, the revision log (D2 §2, §8); data
                     packaged with the code, read only by schema/ and the generators
    core/            D1 types (Pydantic): values, conditions, claims, the keyed candidate claim,
                     the citation frame and stored-item models, keys, canonical JSON, label
                     normalization; locators (D1 §3.4); tex.py (the TeX tokenizer and token form);
                     method.py (the D4 §1 method-contract types and the registry interface).
                     Generated from the model, checked in, never edited, each with a drift test:
                     vocab.py (the closed sets with member-property sets), _model/ (qualifiers.py,
                     names.py, sql.py, validators.py), db/_tables.py (the SQLAlchemy MetaData),
                     schemas/ (JSON Schemas with a revision $id, D3 §6). Hand-written beside them:
                     db/overlay.py (the physical overlay: indexes, BM25, views, the extension
                     assertion, bound by name to db/_tables.py, D3 §1)
    schema/          LinkML loading (SchemaView): model.py (the model loader, the declaration check
                     and the model revision), relational.py (the MetaData compiler), the Stage A
                     and B generators and the interchange projections (Arrow, JSON Schema, DuckDB),
                     the change classifier (D2 §8); the D2 §7 pack compilers; and the one
                     rule-language helper that M19's rules and the policy chains share (D2 §7.4)
    validate/        the batch-to-candidate adapter and the reference, type and conformance checks
                     on a batch (D4 §4.3); M19's runner and the rule-view builder over core types;
                     M20; the Verifier protocol and runner (M21's host)
    ingest/          M01–M03 (source profiles are data in sources/)
    methods/         M04–M16, M22, M24 packets; llm/ (packet, prompts/, parse); gliner/; math/
    consolidate/     M17, M18, M23 (D5)
    orchestrate/     runs, stage graph, tasks, workers, reuse, policies, metrics (D6)
    evaluate/        golden sets, alignment, scoring, witnesses, experiments, digest (D7)
    serve/           generic typed queries, the domain-query protocol, exports (D8 §5–§6)
    intervene/       MCP server and tool implementations (D8 §2); testing (the in-process harness the
                     acceptance test and live-run answers submit through)
    cli/             the Typer app and every `ci` command group (D8 §4)
  alembic/           migrations, each linked to a model revision; 0001 generated once from
                     core/db/_tables.py plus core/db/overlay.py, then frozen (D3 §1)
  tests/
domains/
  core/schema/rules.yaml   the core rules, hashed into every schema version (D2 §2, §6)
  statistics/        schema/ (statistics.yaml, rules.yaml, migrations/), guideline.md,
                     policies.yaml, methods.yaml, slices.yaml, verifiers.py, queries.py,
                     reference/ (the worked examples E*, D2 §7.5), eval/ (split.yaml,
                     baselines.yaml and the reference facts, read only by evaluation, D7 §3.1, §6,
                     §7), README.md
sources/
  siegrist.yaml      the Siegrist source profile (D2 §12.1, D4 M01), named by the packs that read it
fixtures/
  trace/             the trace targets as data, hand-authored from trace.md: segments, target
                     entities and claims per unit; independent of s0/, so the proposals are checked
                     against targets they did not produce; corpus/ vendors the trace and spike pages
  s0/                the S0/S0-R2 v1 reference for the 13 annotation units of `core12` (T1 is two:
                     its lead-in paragraph and `dfn1`) as authored batches with their citation
                     frames (D1 §10.3): fixture proposals; the stored form is derived by the quote
                     cascade on the production renditions, keys are never stored
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
builder work over the `core` keyed candidate claim. `validate` owns the adapter from a submitted
batch to that type and the reference, type and conformance checks on a batch; consolidation's pool
adapts into the same type, and at finalize consolidation hands the view builder each claim value's
parse status, kind and symbols as data, so `validate` imports neither the pool, the quote cascade
nor `methods/math`. Domain
plug-ins implement protocols declared in the generic packages: `domains/<name>/verifiers.py`
`validate`'s Verifier, `domains/<name>/queries.py` `serve`'s query protocol (D2 §7.6, D8 §5.2), so
no generic package names a domain predicate (P0CL-07). Source profiles are data in `sources/`,
outside every pack (D2 §12.1). `core` keeps its runtime dependencies (Pydantic and `regex`): its
generated modules import nothing from LinkML, which only `schema/` and the generators need.
> Decision: [ADR-0020](../adr/0020-one-model-generated-projections.md)
> Status: **Proposed** (2026-10-28)

The entry points sit on top: the MCP tools call `serve`'s queries (D8 `query`, `explain`, from
phase 1; in phase 0 the session uses the read-only `ci query` and `ci explain`), and `cli` holds
the Typer app and every `ci` command group, so `serve` holds queries and exports
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
| pydantic, pydantic-settings | 2.14.1, 2.16.1 | core types, method configs, settings |
| sqlalchemy, psycopg[binary], psycopg-pool, alembic | 2.1.5, 3.3.6, 3.3.3, 1.20.0 | core.db (generated `MetaData`, overlay), migrations, bulk COPY; one psycopg-pool `ConnectionPool` per process (D3 §1) |
| pgvector (Python) | 0.5.1 (server extension 0.8.7; [overview](../libraries/postgresql/pgvector.md)) | `halfvec` column type (phase 1, with `kb.embedding`) |
| pg_textsearch (server extension) | 1.5.1 (Debian package `postgresql-18-pg-textsearch`; [overview](../libraries/postgresql/postgresql-18-pg-textsearch.md)) | BM25 lexical search for `find` (D3 §5, D8 §5.1). A phase 0 server prerequisite: in `shared_preload_libraries`, and created once by the operator in the template database, so the cloned test databases (§4) carry it |
| linkml-runtime; linkml (dev) | 1.12.1, 1.12.1 (as probed, schema-rules note) | `schema` loads the model and packs with `linkml-runtime`'s `SchemaView` and generates every projection from it (ADR-0020; added by P0-M-1); `linkml` (the linter, the `PydanticGenerator` Stage B may subclass) is a dev dependency, used in generation, tests and pack checks only |
| pglast (dev) | 8.7 ([overview](../libraries/postgresql/pglast.md)) | the port check of the generated DDL against S6's and the query check of D3 §9 (P0-M-2) |
| pyarrow | 26.0.0 ([overview](../libraries/analytical_infrastructure/pyarrow.md)) | Arrow schemas generated from the model; the pool relations; exports (P0-M-3, pool and interchange) |
| adbc-driver-postgresql | 1.13.0 ([overview](../libraries/postgresql/adbc-driver-postgresql.md)) | the pool loader, if probe Q-5 chooses it over psycopg |
| pgpq | 0.12.0 ([overview](../libraries/postgresql/pgpq.md)) | only if probe Q-5 shows absent versus null, JSONB, numeric and `timestamptz` survive: Arrow-native bulk writes |
| rule-engine | 5.1.0 | M19, policies |
| gliner2 | 2.1.0 | M05–M07 (phase 1; the product environment carries no gliner2 or torch in phase 0) |
| spacy, en_core_web_sm | 3.8.18, 3.8.0 | M03, M08, M13, M22 |
| lxml, html5lib | 6.1.3, 1.1 ([overview](../libraries/primary_intake/html5lib.md)) | M01 (html5lib parser through `lxml.html.html5parser`; D4 M01) |
| cssselect2 | 0.10.1 | M01's role engine (`Matcher`; D4 M01) |
| regex | 2026.9.29 | M01 delimiter pattern, the quote cascade (D4 §4.3), M22 lexicons |
| tokenizers | 0.23.3, phase 1 | M02 token counts and LLM-tier packet caps (D4 §4.1); phase 0's M02 writes character and math features only, and agent-tier caps are characters |
| PyYAML | 6.0.3 | pack files |
| jsonschema (dev) | 4.26.0 ([overview](../libraries/data_model/jsonschema.md)) | **derivation conformance** in tests: the JSON Schemas are generated from the same model as the Pydantic models, so their agreement checks the generators, not the contract; and `check_schema` on generated artifacts. Production validates with Pydantic (D2 §7.3, D3 §6). The independent semantic controls are named per contract: hand-authored known-answer vectors (the key-scheme conformance vectors, D1 §10.1), negative store tests per invariant written from D1 §11, the external S0 and S0-R2 batches, relational key oracles and tex parity (RC16; operator, 2026-10-28) |
| sympy, lark | 1.14.0 (hold, `docs/pins.md`), 1.3.1 | M11 (grammar from phase 0, SymPy conversion from phase 1), M21, alignment |
| pint | latest | M12 |
| z3-solver | 5.3.2.0 | M20 |
| scipy, numpy | 1.18.1, 2.5.4 | M21, alignment |
| rapidfuzz | 3.14.6 | M14, quote location |
| splink, duckdb | 5.0.0, 2.0.0 | M15, analytics, Parquet export; duckdb is a product dependency as consolidation's in-process engine (ADR-0021), with a hold row in `docs/pins.md` (a new major release), added by the package that first uses it |
| pgmpy, scikit-learn | 1.1.2, 1.9.1 | confidence model, calibration |
| networkx | 3.7 | statement and claim graph utilities |
| fastmcp | 4.1.3 | intervene |
| typer, rich | 0.27.3, 15.0.0 | CLI |
| vLLM | as in `services/vllm-native` ([overview](../libraries/analytical_infrastructure/vllm.md)) | M10, M16, M04 pooling if S7 chooses it (phase 1) |
| httpx (or openai) | latest | M10, M16 client to vLLM |
| sentence-transformers | latest, only if S7 chooses in-process embeddings | M04 |
| torch | 2.13.0 (as in the vLLM environment) | GLiNER2, embeddings (phase 1) |
| ppi_python (`ppi_py`) | 0.2.3 ([overview](../libraries/scientific_compute/ppi_py.md)), phase 2 | the random audit's corpus-level precision (D7 §6, OPEN-D7-4) |
| Hypothesis, hypothesis-jsonschema (dev) | 6.170.12, latest at P0.1 ([overview](../libraries/analytical_infrastructure/hypothesis.md)) | property, stateful and grammar-generated tests (§4) |

**Python 3.14.** The root requires ≥ 3.14, and the vLLM environment already runs torch 2.13 on
3.14. Whether gliner2, spaCy, z3 and pgmpy ship 3.14 wheels is checked by the spikes' environment
(`OPEN-D9-1`). **Tested** for the S0/S1 set (2026-10-28, [e0.environment](../design_review/evidence/2026-10-28_design-spikes/records/e0.environment.json)): on 3.14.10 spaCy 3.8.18 with `en_core_web_sm`/`trf` 3.8.0, spacy-curated-transformers, torch 2.14.1 (CPU), lxml, html5lib, sympy 1.14.0, lark, pydantic, linkml-runtime, rapidfuzz, scipy and statsmodels install and import; DuckDB 2.0 installs from its abi3 wheel. gliner2, z3, pgmpy and splink remain for S2, S4 and S5. A missing wheel is resolved per package (build from source, or isolate that method
in a side environment like vLLM), never by lowering the product's Python version silently.

## 3. Conventions

**Accepted target (2026-11-07).** The installed CLI dispatches repository automation through
named `just` recipes anchored to the prepared checkout. Bootstrap and recovery retain direct
recipes. Product operations call their owning services. The test supervisor owns its lane
receipts, process groups and coverage policy. Managed result custody supplies identity,
leases, holds, and one-day success or one-week failed/interrupted retention.

> Decision: ADR-0069

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
  never the math grammar or SymPy, whose timeout needs a main thread (D2 §7.4). The grammar's API
  raises when it is called off a process's main thread, so a violation fails loudly instead of
  running without a timeout. The main MCP server never imports the grammar; the golden server runs
  the A/B alignment and agreement (D7 §3.3) in one spawned single-worker process (D8 §2.2).
- **Methods** follow the D4 §1 contract; a method's tests run it on trace units with fixtures.
- **Determinism.** Keys from canonical JSON (D1 §10.1); LLM calls with `temperature: 0` and a
  seed; no wall-clock or random input to any key or digest.
- **Logging** through the standard library, one line per task outcome at INFO; payloads never
  logged.

## 4. Tests

| Layer | What | How |
|---|---|---|
| Types and keys | Canonical JSON, keys, condition canonicalization, value canonical forms | Unit and Hypothesis property tests (permuted keys, reordered `and` arguments give equal keys); D1 models drawn by `st.builds`/`st.from_type` with strategies registered for constrained fields (`st.from_regex` where a model uses `Field(pattern=…)`, which `from_type` ignores) |
| Math | The token form against the tree printer wherever the grammar reads a span (KEYS-01) | A corpus layer over every first-pass span, and generated layers: strings from the grammar itself (`hypothesis.extra.lark.from_lark`, with explicit strategies for the macro terminals) and metamorphic rewrites of the token form (sizing commands, spacing, brace-equivalent forms); failures shrink to a minimal formula ([Hypothesis overview](../libraries/analytical_infrastructure/hypothesis.md) §6.5) |
| Batches | The compiled batch models and the exported JSON Schema agree | `hypothesis-jsonschema.from_schema` draws batches from the exported schema, where its draft support covers it, and Pydantic and jsonschema must both accept them; jsonschema errors are compared sorted by `absolute_path`, since `iter_errors` order is not guaranteed ([jsonschema overview](../libraries/data_model/jsonschema.md) §2.1, §9.2) |
| Task lifecycle | Claiming, lease renewal and expiry, fencing, terminal writes and reuse keep the D6 §3 invariants (no task held twice, a lost lease commits nothing, reuse only of `done`/`empty` results) | A `RuleBasedStateMachine` whose bundles hold tasks and workers, `consumes` for terminal writes, invariants after every step against a small reference model, each example in its own rolled-back transaction ([Hypothesis overview](../libraries/analytical_infrastructure/hypothesis.md) §4, §10.1); real interleavings are S6's concurrency test, since state machines do not explore scheduling |
| Database | Legacy migration 0001 retains its upgrade/downgrade controls; semantic cold bootstrap and era-shaped forward upgrades execute their own frozen history. Catalog comparison supplements bounded Alembic checks; invariants remain independently exercised. | Accepted target: narrowed semantic consumers clone keyed verified heads; qualification builds a run-private head. Eligible committed recipes use worker-local sealed seeds and claim-specific isolation. Driver-only controls use infrastructure clones. Explicit ACL/default replay and real commits remain where required. The shared leased owner closes resources and waits boundedly for normal backend exit, without FORCE; [D3](D3-database.md#native-test-deployment-equivalence) and ADR-0101/0102 own the contract. CA-21 owns the acknowledged nonce/OID/owner correction and its verification. |
| Ingest | Trace segments and offsets; S1 counts | `fixtures/trace/*.segments.json`, over the trace and spike pages vendored under `fixtures/trace/corpus/`, so those tests always run; the whole-corpus tests (S1 counts) are skipped when `docs/statistics_corpus` is absent |
| Methods | Each method on trace units | Fixtures; GPU tests marked `gpu`; LLM tests replay recorded responses (stored under `fixtures/llm/`) so they are deterministic and offline |
| Consolidation | The trace through D5: proposals from `fixtures/s0` produce the trace's target claims, with key equalities as the targets state them (claims the trace names as one share a key, distinct ones differ), never key values | End-to-end on the trace slice without GPU or agent |
| Acceptance | The trace's typed questions (D8 §5.3) answered from the database after a `trace` slice run with `agent_mode: complete`, the `fixtures/s0` batches for its units submitted through the MCP tools in process (the `intervene.testing` harness over FastMCP's `Client`, mapping fixture sentence ids through each served packet's sentence map, D8 §2.1), and a rerun that reuses them (D6 §4), so the test is deterministic and needs no live agent. Phase 0 checks every trace target except derived claims (T3 D1, phase 2), with scopes and bindings as the proposals state them (D5 §11). Comparisons are by locator, structure and key equality, never by key value: the fixtures hold authored batches and no keys, and the test checks answers, not the key function (D1 §10.1). The live Opus `trace` and `spike-pages` runs are qualification evidence: their typed-query rows are aligned with the rows the same queries return from a golden-expectation run, whose proposals are the trace and core units' pass-C batches submitted by this test's path under M24's own `agent.opus/expectation` configuration (D7 §9) | `tests/acceptance/test_trace.py`; the phase 0 gate |
| Evaluation | Alignment tiers on hand-made golden/run pairs, including formula equivalence and faithful ambiguity; interval figures reproduced from a recorded seed and unit order | Unit tests |
| Interfaces | MCP tools through one shared in-process `Client(mcp)` fixture (sequential clients re-enter the lifespan); `ci` through Typer's `CliRunner` with stdout and stderr apart and the Rich width fixed | Unit and acceptance tests ([interfaces note](../design_review/evidence/2026-10-28_library-interfaces-eval/README.md) §1, §3) |

The trace is the acceptance spine: a design change that alters a trace target changes
`trace.md`, the fixtures and these tests together. Fixture tests compare key equalities, never
key values, so a change of the key rules (D1 §10.1) moves no fixture. The shared fixtures (the
per-session test database, the trace slice, a compiled schema) live in `tests/conftest.py`, owned
by the foundations package; other packages add thin fixtures over them.
> Status: **Proposed** (2026-10-28)

## 5. Phase 0 build plan

The [phase 0 plan series](../plans/phase-0_2026-10-28.md) owns sequencing, dependencies and packages; the table below states
each step's content and acceptance, and its "Depends on" column is indicative.

Goal (D0): the meta-model in PostgreSQL, HTML ingest, Opus intervention tools, the query API and
the evaluation harness; Opus extracts the claims of the `phase0-golden` scope (the four spike
pages whole and every dev golden unit by its unit locator, about 234 packets by
[simulation](../design_review/evidence/2026-10-28_phase0-golden-size/README.md); D2 §12.2, D7 §9),
while the full first pass is a phase 1 run with M10 (P0CL-09; operator, 2026-10-28); the trace
units and spike pages answer their typed questions from the database; evaluation runs.

| Step | Builds | Depends on | Acceptance |
|---|---|---|---|
| P0.1 | Package skeleton as a workspace member; settings; `ci` with `--help` | — | `just check` passes with the package's first tests |
| P0.2 | `core`: values, conditions, claims, the keyed candidate claim, the citation frame and stored-item models, canonical JSON, keys, label normalization, `core/tex.py`, `core/method.py` (D4 §1), and the locator generator and resolver (D1 §3.4; owned by ingest and math); `fixtures/trace` hand-authored from `trace.md`, and `fixtures/s0` as authored batches with citation frames (§1) | P0.1 | Property tests; the trace's claims construct and key deterministically; fixture tests compare key equalities only (§4) |
| P0.3 | The model's relational projection (the generated `MetaData` in `core/db/_tables.py` and the overlay `core/db/overlay.py`, D3 §1; ADR-0020), and migration 0001 generated once from them and frozen; `ci db init`, `ci db migrate` | P0.2, S6 | The pglast port check against S6's tested DDL leaves its residue empty or recorded; upgrade and downgrade on a test database; trace rows of D3 §10 insert and the D3 §9 queries return them |
| P0.4 | `schema`: load the model (`model/core.yaml`, `model/system.yaml`, with the model revision) and the `statistics.yaml` v0 pack over it, with the core and pack `rules.yaml` and the pack's `reference/` (the schema version's inputs, D2 §2); compilers to schema tables, JSON Schema (the model-facing and stored forms, with `cN` citations; the decoding form as a pure transform with structural tests only, D2 §7.3), the **annotator reference** (D2 §7.5, §10.10: predicate cards rendered from the pack's `tables:` and subset descriptions, the worked examples from the pack's `reference/E*`), rules (compiled) including the top-level **`guideline:` section** of warnings (D2 §7.4), through the one rule-language helper; `guideline.md` ported verbatim from the S0-R2 guideline v1 (D2 §10); in `validate/`, the batch-to-candidate adapter and the reference, type and conformance checks, and the M19 runner and the rule-view builder over the `core` keyed candidate claim, with the D5 §8.2 context at both call sites and the pack's `views:` compiled (D2 §7.4), submission-time views reading symbols with `core/tex.py` and grammar-dependent rules `at: [finalize]`; compiled artifacts keyed by schema version, compiler, compiler version and kind (D2 §7); `ci schema compile` (GLiNER2 dicts are compiled from phase 1, D2 §7.2) | P0.2, S4 | Deterministic artifact hashes; a compiler version change adds artifacts beside the old ones; editing a worked example or the `guideline:` section changes the schema version; a rule with a type error fails compilation; the v1 reference batches validate against the model-facing schema, and the spike's stored copies of them against the stored schema (the stored form the production quote cascade derives is accepted with the cascade, P0.7); the generated reference for schema v0 carries the information of `results/s0r2/inputs/packet_v1/reference.md`; the v1 reference and the examples give 0 guideline warnings, and each seeded violation is caught |
| P0.5 | `ingest`: M01 with the Siegrist source profile (`sources/siegrist.yaml`, D2 §12.1; every source fact read from the profile, including its `root`, corpus index, `language`, `sections`, references and the rendering conventions), the html5lib parser and the profile's math delimiting, content-addressed renditions with their builds (D1 §3.1), M02 (character and math features), M03 (variant b′, D4 M03) as a step of M01's task | P0.3, S1 | Trace segment fixtures match; S1 count criterion holds on the 78 pages; delimiting reproduces S1's 8 `partial` spans; invariants hold; canonical text equals the spike renditions on the S0/S0-R2 pages (rendition identity, A12) |
| P0.5b | Math grammar and scoping: the one math grammar (M11's grammar part: validation, slot typing, canonical form; SymPy conversion stays phase 1), M09 symbol occurrences, both run per rendition with per-span observations; M13 binding sites, reading M09's observations; packet standing context from M13 (D4 §4.1) | P0.5, S5 | The standing contexts of `results/s0r2/sample.json` on its 21 units; 18 of the S0 M13 probe's 20 scopes, reported (the probe's paragraph rule is not ported; the paragraph extent is decided in phase 1 with S5-B, D4 M13); the property test that tree printer and token form agree on every parsed value (D1 §6.2, ADR-0035); grammar coverage reported per page, not a gate |
| P0.6 | `ci project init` (project, documents registered from the corpus index the source profile names, refusing pages that collide, versions, named configurations, slices by locator); `orchestrate` minimum: runs with their recorded reference run, tasks, queue, reuse by content digest, the stages `ingest → normalize (grammar, M09) → scope (M13) → propose → assemble → finalize → measure → evaluate` (D6 §2), with M19 as one run-level step inside finalize and no `check` stage in phase 0; a recorded fate for every eligible unit (`skipped` with reason `scope` outside the run's scope, D6 §7.4, §8); `methods.yaml` loaded into the method registry; the agent barrier (`wait` for short slice runs, `complete` with reuse for long ones); the orchestrator's session lock, `ci status`'s orphan report and `ci run cancel` (D8 §4) | P0.3, P0.5b | A `trace` slice run creates `awaiting_agent` tasks; a second run reuses the ingest tasks; a run scoped to `phase0-golden` records its resolved unit list and hash in its `scope` option and every other eligible unit as `skipped` with reason `scope`; a running run whose orchestrator has died is reported orphaned and can be cancelled |
| P0.7 | `intervene`: MCP server (`ci mcp serve`) with queue tools, `read_instructions` (by part), `propose_claims` (the `validate` checks, quote location, M19 at the `batch` call site; completion through orchestration's agent completion primitive), packet assembly from recorded inputs with caps in characters (D4 §4.1, D8 §3), the M24 extract prompt (`methods/llm/prompts/extract.md`); the golden server with its tools leased on the task queue (`read_golden_unit` serves, by part, the guideline, the annotator reference and the query-assembled packet; `write_golden` stores the authored batch with its citation frame, records the model and the inputs, D3 `eval.golden_pass`, returns guideline warnings, and in the transaction that stores the second of passes A and B stores the unit's agreement, computed in the server's single-worker alignment process, and creates the pass-C task; it derives no golden items), the `golden.pass` method; `record_direction` and `ci direct`; the work-queue skill, which dispatches golden passes to Sonnet subagents (ADR-0011). `adjudicate`, `ci ack`, `ci veto` and the D8 §2.3 proposal and §2.4 inspection tools follow in phase 1 (D8 §2) | P0.4, P0.6 | The quote cascade derives from the v1 reference batches a stored form that validates against the stored schema; submitting a v1 reference batch completes a task; errors and warnings come back per item, and the first rejected result stays on the open task; a golden pass without model or inputs is refused; the assembler reproduces the packets of the pack's worked examples (`reference/E*`); the main server never imports the grammar |
| P0.8 | `consolidate` phase 0 realization (D5 §11), with M19 at finalize as one run-level step over the in-memory pool, bulk-writing `verification` observations | P0.6, P0.7 | Fixture proposals for the trace produce the target claims, statements, bindings that the proposals state, and invariants |
| P0.9 | `serve`: the generic queries of D8 §5.1 and the domain-query protocol, with the run selector, pinning, the page tokens `serve` issues and coverage (D8 §5); the statistics queries of D8 §5.2 in `domains/statistics/queries.py`; `ci query` (exports are phase 1, D8 §6) | P0.8 | The trace acceptance test passes; a query over a run with skipped units reports partial coverage; a query over a run that has not finished is refused; a promotion between pages leaves a page token's run unchanged |
| P0.10 | `evaluate`: page split with reserved pages and the forced-dev pages of D7 §3.1, unit sampler and golden run (`ci golden split`, `ci golden create --label`, which creates the set, its units, the `golden` run and the pass A and B tasks), context-premise scoring (D7 §5.1), golden sets (dev 40, test 40; trace and core units forced into dev), goldens keyed by unit key with items derived per rendition by the quote cascade (D7 §3.1), the golden-set unit list (P0.6 resolves the slice), alignment tiers, scores with bootstrap intervals, the pre-registered promotion readings and the pack's `eval/baselines.yaml` (D7 §7 item 5), live-run answers (D7 §9), `ci eval`, digest v0 | P0.7, P0.8 | Alignment unit tests; scoring a run against S0 references gives the S0 A-versus-B numbers when fed the passes; a golden run finishes only when every unit is adjudicated |
| P0.11 | Phase 0 runs: `trace` (a debug slice), then `spike-pages`, a `complete` run of kind `full` over the `first-pass` corpus scoped to `spike-pages`, which is the golden source run (D7 §7 item 5); `ci golden create` from it and the golden authoring; then the phase 0 first pass: successive `agent_mode: complete` runs over the first-pass corpus scoped to the `phase0-golden` slice (D6 §8), each reusing finished tasks (the spike pages' from the `spike-pages` run), with Opus working the queue between them (every other eligible unit `skipped` with reason `scope`; the full first pass is a phase 1 run with M10, D7 §9); goldens authored by the D7 protocol (Sonnet passes and adjudication, ADR-0011) | all | The D0 phase 0 gate (D7 §9): the sequence converges with no unresolved agent task, and the operator promotes that run with `ci promote` after reading the pre-registered readings |

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
| `mathgrammar/` | the one math grammar: M09, M11's grammar part, canonical form (ADR-0035) |
| `m13_binders.py` | M13 (P0.5b) |
| `s0r2_sample.py` `context_for` | the standing-context function (D4 §4.1; P0.5b) |
| `s0_locate.py` | the quote cascade (`methods.llm.parse`, D4 §4.3) |
| `s0r2_inputs.py` `reference()`, `card()` | the annotator-reference compiler (D2 §7.5; P0.4). A card's role, modality and condition text comes from the pack's `tables:` and subset descriptions, so `GROUP_RULES` and the `STRUCTURAL` and `FORM` lists are not ported |
| `s0r2_inputs.py` `packet()`, `FORMAT_V1`, `INSTRUCTIONS` | packet assembly and the prompt parts of the extract and golden modes (D4 §4.1, §4.2, D8 §2; P0.7) |
| `s0r2_adjudication_inputs.py` | pass C's instructions and the rendering of the A/B diff (D7 §3.4, D8 §2.2; P0.7) |
| `s0r2_rules.py` | the `guideline:` section of `rules.yaml` (D2 §7.4; P0.4); its predicate sets become pack subsets and its role and modality maps `tables:` entries |
| `instruments/` (align, conditions, keys, values, validate, scores) | `core` keys and canonical JSON, and the batch validator. Where the alignment and scoring instruments live long-term, in `evaluate/`, in the evidence tooling or shared, waits on the operator's design of the evidence system and its reusable apparatus |
> Status: **Proposed** (2026-10-28)

## 8. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D9-1 | Python 3.14 wheels for gliner2, spaCy and its model, z3-solver, pgmpy, splink | Spike environment setup (S1, S2, S4, S5) |
| OPEN-D9-2 | Whether the MCP server and the orchestrator share one process (D8 `OPEN-D8-1`) | **Decided** (2026-10-28): two processes, the database the only shared state (D6 §1) |
