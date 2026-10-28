# Phase 0 foundations: package, core types and keys, fixtures, store

**Status:** Active in part. Part of the [phase 0 series](../phase-0_2026-10-28.md), which owns shared
decisions, contracts, the dependency graph and build findings (§11). P0-F-1, P0-F-2a and P0-F-2b were
built and reviewed on 2026-10-28, together with ingest and math's P0-I-0 (coordinator §11, rows
IR-01…IR-15). **Revised** on 2026-10-28 by the
[domain-model alignment review](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md)
and its [target model](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28_target-model.md)
("TM"), decision Revise, with the rule changes decided in coordinator §9.2:
- P0-F-2c, P0-F-2d, P0-F-2e, P0-F-5, P0-F-Q4 and P0-F-Q6 were added;
- P0-F-4 was revised;
- the closed value sets and the table metadata moved to [model and projections](model-and-projections.md)
  ("M").

The rest is not built.

**Baseline.** Commit `e0899cd`, the coordinator's second revision. Built in
`python/corpus-structure/src/corpus_structure/`:
- `settings.py` and `cli/` (F1);
- `core/canonical.py`, `evidence.py` and `tex.py` (F2a);
- `core/locators.py` (I0);
- `core/values.py`, `batch.py`, `frame.py`, `candidates.py`, `payloads.py`, `vocab.py`, `schemas/` and
  `keys.py` (F2b).

The IR rows of coordinator §11 record that review:
- IR-01…IR-12 and IR-15 were fixed on 2026-10-28, with rulings in D1 §3.2, §6.2, §7 and §10.1;
- IR-13 belongs to I1a;
- IR-14 is open (P0-F-5, optional).

Their regression tests survive every rework step below (coordinator §7, "How the built code is
reworked"). Packages P0-F-1…P0-F-5, P0-F-Q4 and P0-F-Q6 correspond to F1…F5, F-Q4 and F-Q6 of the
coordinator's graph (§7). Every design claim here is **Proposed** unless it carries another label.

## 1. What this document builds

Foundations builds what every other phase 0 document stands on (D9 §5, P0.1–P0.3):

- **the package and its entry point** (F1): the `corpus-structure` workspace member, settings, the
  `ci` Typer app with its group registration, the shared test configuration and the database
  fixtures;
- **the representation** (F2a, F2b), which consists of:
  - canonical JSON, the evidence types and the rendition content digest;
  - `core/tex.py`, the TeX tokenizer and token form;
  - the D1 shapes in both batch forms, the citation frame and the keyed candidate set;
  - the observation and operations JSON models;
  - label normalization, canonical forms and every D1 key;
- **the reworks of the alignment review**, layered on the built F2b rather than rewritten:
  - typed dispatch, one condition visitor and typed outcome codes (F2c,
    [R03](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r03));
  - declared identity (F2d, [R02](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r02)):
    `KeySchema` compiled from qualifier specifications, canonical forms by range, case policy, and
    the key scheme recorded beside keys with its carry-over map;
  - complete translations and typed references (F2e,
    [R04](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r04)), with
    `ExternalReference`. F2e also freezes key scheme 1 with conformance vector v1;
- **the fixtures** (F3), which consist of:
  - `fixtures/s0`, the v1 reference as authored batches with citation frames;
  - `fixtures/trace`, the trace targets hand-authored from `trace.md`;
  - the original bytes of the four spike pages the fixtures use, so tests on them never depend on
    the gitignored corpus;
- **the store** (F4), which consists of:
  - migration 0001, generated once from M2's `MetaData` and overlay and then frozen;
  - `ci db`;
  - one connection pool per process, with an extension-version check at startup;
  - the repository: get-or-create, the evidence writer, the observation writer with
    `payload_schema_id`, span upsert, and the bulk primitives other writers use;
- **infrastructure facts** (F5,
  [R11](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r11)'s local
  fixes):
  - expected extension versions;
  - template retention;
  - one source per coordinate;
  - the Python-manifest pin check;
- **two probes**: Q-4 on foreign-key cost at run scale (F-Q4) and Q-6 on key carry-over and vector
  stability (F-Q6).

**Where it ends.** Foundations defines shapes and the functions that are total over them. It makes no
decision that needs the pack, a parse or the pipeline's state.

- **Model and projections own these** (M):
  - the model (`core` and `system`) and its revision;
  - the generated `core/_model/` and `core/vocab.py`;
  - the generated `MetaData` (`core/db/_tables.py`) and the physical overlay (`core/db/overlay.py`);
  - Arrow schemas and versioned JSON Schemas;
  - the payload-schema registry, reader dispatch, change records and the Alembic hooks.

  Foundations consumes them and never restates them.
- **Locators** (grammar, generator, resolver, refusal) are ingest and math's (I0). They are a
  core-level function over F2a's segment types, which foundations calls.
- **Batch contracts are split.** The `ClaimProposalBatch` envelope contract is D2 §7.3's. Schema and
  rules (S1) compiles its per-predicate branches over F2b's generic shapes, and the pack half of
  `KeySchema` and the pack name map. `validate` (S2) owns the T2 and T4 translations (target model
  §7): stored batch → keyed candidate set → rule view. It also owns the reference and type checks
  for batches (RC19). Foundations owns the types those translations fill and the keying resolver's
  kind refusals for pool candidates.
- **The quote cascade** that derives a stored batch from an authored one is agent interface's (A0).
- **Consolidation (C1) decides the run's groupings**: which candidates fuse, which become
  alternatives, and which segment is a statement's or scope's. It also resolves `ExternalReference`
  nodes and re-keys the citing claims. Foundations computes the keys of what C1 decides.
- **The pool and its engine** (the T3 loader, DuckDB, the bulk writer from generated schemas,
  `ci export`) are pool and interchange's (P).
- **Ingest and orchestration own their records.**
  - Building renditions is ingest's (I1a); foundations stores them.
  - Tasks, leases, fencing, the run cut and the agent completion primitive are orchestration's (O1).
    The observation writer runs inside O1's transaction.
  - Compiled artifacts are written by `schema.registry` (S1b) through F4's repository.

**Change scenarios** that explain the boundaries (DESIGN §1.3, the phase 1 additions and the review's
§5):

| Change | Where it lands | What foundations must already allow |
|---|---|---|
| A content-preserving ingest change (an M01 port, a spaCy bump, a profile fix that changes no output) | ingest | The content digest covers only content, and segments carry no diagnostics (D1 §3.2). So the rendition, its segments and every key stay; F4 records one more build |
| A table cell "High flow · 300 kPa(g)" | M01 tables, M12 (phase 1) | `number` keeps `unit` and `basis` as written in keys (D1 §6.2); the table kinds are already members of the model's segment-kind set |
| "ORG-101 owns P-17, valid 2026-01-01 to 2026-06-30, per ownership.html" | a second pack | `valid_time` and the cited source are identity by their specifications (TM §8). The pack declares `ci:case preserve` on the identifier slot, so `ORG-101` is not guessed from shape |
| A business modality under which attribution identifies | a second pack | The pack gives its member the `attribution_identifying` property. `KeySchema` reads the role condition, so there is no core edit (consolidation's C4 checks this) |
| An email thread, "as I wrote below" | a second source profile | The email kinds are model members with their properties, so there is no migration. The back-reference is an `ExternalReference` whose link target is the message id |
| A second domain pack | `domains/<name>`, `sources/<name>.yaml` | Key functions take `KeySchema` (qualifier specifications with key roles, case policies, identity keys, symmetric predicates) and label rules as data; `core` names no domain word |
| A rule with `or`/`not` conditions | the pack's `rules.yaml` | The condition tree and its canonical form already hold `or` and `not` (D1 §7) |
| A canonical-form fix | `core/keys.py` after the freeze | A key-bearing change (M4's class) needs a new key scheme, a carry-over map and a new conformance vector. Keys are never silently migrated |
| The grammar extended by S5-B (phase 1) | ingest and math | Keys use the token form, which reads no grammar (ADR-0012). A change to `core/tex.py` after its freeze is a key-bearing change |
| Embeddings (phase 1) | M04, a new migration | Segment rows survive content-preserving re-ingest, so `kb.embedding` rows can reference them. The `EmbeddingSpec` is declared in `system` (M1); 0001 does not create the table |

## 2. Contracts

### 2.1 Consumed

| Contract | Owner (design · this series) | Used by |
|---|---|---|
| Locators: string and structured forms, the generator, the resolver and its refusal; the annotation unit | D1 §3.4; ADR-0019 · [ingest and math](ingest-and-math.md) P0-I-0 | F2b (statement and local-entity keys, frame resolution), F3 (frames), F4 tests |
| The model: `core` and `system` modules, the model revision, `ci:key_scheme` | ADR-0020 (P0-D-1); D2 §2–§3 · [model and projections](model-and-projections.md) P0-M-1 | F2d, F2e (types, scheme), F4 (records the revision) |
| The generated `core/_model/`, consumed in three parts. First, the `StrEnum`s with member-property frozensets. Second, the core `QualifierSpec`s (range, default, key role, role condition, canonical form by range, store placement). Third, the local ↔ prefixed name tables, the SQL-literal constants and the templated validators. Also consumed: the generated `core/vocab.py` | ADR-0020 · P0-M-1 | F2b's shapes (literals, defaults, qualifier list), F2c's codes once generated, F2d (`KeySchema` core half, case policies), F2e (name tables) |
| The generated `MetaData` (`core/db/_tables.py`) and the physical overlay (`core/db/overlay.py`): tables, digest-named CHECKs, per-version member tables, edge and identity tables, indexes, BM25, views and the extension assertion | D3 citing the model; ADR-0020, ADR-0021 · P0-M-2 | F4 (0001, repository, catalog comparison) |
| Arrow schemas and JSON Schemas with `$id` per model revision | ADR-0020 · P0-M-3 | F2b's committed `core/schemas/*.json` (the `$id`) |
| The payload-schema registry content, reader dispatch with typed refusal, and the Alembic hooks (`template_args`, `process_revision_directives`, `on_version_apply`) | ADR-0022; D2 §8; D3 §3 · P0-M-4 | F4 (writes `payload_schema_id`; 0001's `env.py`) |
| The batch envelope and per-predicate branches. The pack half of `KeySchema`: identity keys per class, compiled `ci:key_role` (from `ci:identity_qualifiers`) and `ci:case`, symmetric condition predicates, prefixed predicate names, and `entity_identity` (which identity slots hold entities). The pack name map (X2-01) | D2 §3, §5, §7.1, §7.3 · [schema and rules](schema-and-rules.md) P0-S-1 | F2d's keys take these as data. F4's writer receives schema-dependent payloads already validated by S1's adapters |
| The quote cascade (authored batch and frame to stored form on a rendition) | D4 §4.3 · [agent interface](agent-interface.md) P0-A-0 | F3 acceptance |
| Production renditions and the standing-context function | D1 §3, D4 M01–M03, §4.1 · ingest and math P0-I-1a, P0-I-2a | F3 acceptance |
| Label rules (articles, head words, rewrites) | D1 §10.1, D5 §3.3 point 5; the `aliases:` section of the pack's `methods.yaml` (D2 §12.1) · data loaded by the method registry (orchestration O1) | F2b label normalization |
| Fates as of `ops.run.cut_at`; the run's resolved scope; policy actions by `<method>/<name>` | D3 §4, §6.3, §8, D6 §3.1, §7.1, §8 · [orchestration](orchestration.md) | F4 views (through the overlay) and JSON models |
| Spike evidence: S6 records `s6.ddl`, `s6.constraints`, `s6.queries`, `s6.bm25`, `s6.dry-run`, `s6.volume`, `s6.sizes`, `s6.keys` and `s6.restated`; S5 records `s5.keys-property` and `s5.macros`; S4 record `s4.batch-validation` | spike series | F4 and F-Q4; F2a's freeze; F2b, F2e |
| The dedicated PostgreSQL 18 cluster `18/corpus`: `just db-provision`, pg_textsearch preloaded, `cs_template` | D3 §13 · coordinator §2 | F1's database fixtures, F4, F5, F-Q4 |

### 2.2 Produced

| Contract | Design owner | What this document implements | Consumers |
|---|---|---|---|
| Settings and the `ci` app | D9 §3, D8 §4; coordinator decision 26 | `Settings`, built once per entry point and result-neutral by contract; the Typer app, group registration, the `--json` option and result emission | every document's `ci` group; the MCP lifespan (A1); the orchestrator (O1) |
| Shared tests | D9 §4 | `tests/conftest.py`: Hypothesis profiles, markers, the CLI runner, the per-session test database and its isolation fixtures, coordinates from `Settings()` (F5) | every package's tests; other owners add thin fixtures over them (trace slice, compiled schema) |
| Canonical JSON and hashing | D1 §10.1 | `canonical_json`, `digest`, `make_key`, the canonical-decimal helpers for loaders | S1 (schema hash), M1 (model revision), O1 (configuration hashes, input digests, `corpus_hash`), I1a, A1, E |
| Evidence types and the content digest | D1 §3.1–§3.3, §10.1; ADR-0019 | `Segment`, `RenditionContent`, `MacroDef`, `content_digest`; `doc`, `ren`, `seg`, `cfg` keys. The segment-kind set is generated by M1 | I0, I1a, I1b, F4, O1 |
| The token form and the effective macro table | D1 §6.2; ADR-0012; coordinator decision 13 | `core/tex.py`: tokenizer, drop list, text-mode commands, the effective macro table (a rendition's table over the pack's fallback map), expansion, `token_form`, token lookup by position | I1a (macro reader), I2a (the grammar's macro classification, generated `%ignore`, its build check, error tokens, the tree/token property test), A0 (the cascade's macro step), S2 (submission views), F2b |
| D1 shapes in both batch forms | D1 §5–§7, §10.3; D2 §6, §7.3; D3 §6 | Values with `EnumValue` per form, conditions, bindings, core qualifiers, generic batch items and envelopes with the `outside` item, the citation frame with resolution and re-addressing, the keyed candidate set as a complete translation target, typed references, `ExternalReference`, observation payload and operations JSON models, and `core/schemas/*.json`. The shape structure stays hand-written until M5 | S1, S2, A0, A1, A2, C1, C2, E1, E2a, M1, M5, O0, O1, P1 |
| Typed outcome codes | coordinator decision 23; RC14 | `KeyingError` and `FrameFailure` carry codes from the closed sets `DropReason` and `FrameFailureReason`; messages are projections of the codes | C1 (`PassReport` by code), A0, E1 |
| Canonical forms, declared identity and keys | D1 §6.2, §7, §10.1; D5 §5.2–§5.3; ADR-0023 (P0-D-1); TM §8 | The pieces are: the `KeySchema` type; canonical forms by declared range; case policy; label normalization; and the `ent`, `stm`, `clm`, member, `alt` and `idg` keys and the `ExternalReference` key. Batches are keyed in condition-reference order, with typed drop codes. Keying preparation is done once per `KeyContext` | C1, E2a (canonical forms for the numeric-tier seed), O1, S2 (rule-view facts) |
| The key scheme, beside keys | ADR-0023; D1 §10.1 (RC07, RC08) | Every keyed output carries the scheme of its keys; no key hashes the scheme | O1 (runs record it), E1 (judgment targets record it), C1, E2b |
| Conformance vectors | ADR-0023; RC07; R12 | Per scheme, hand-authored inputs with hand-written expected key parts and keys; vector v1 for scheme 1 | every key consumer (a change fails until the scheme moves) |
| Key carry-over (T8) | TM §7, §8; RC08 | `carry_over(…)`, an old key → new key map computed by keying stored authored inputs under both schemes; inputs that are unavailable are reported | C1 (reference-run key reuse), E1 and E2b (carried judgments, cross-run comparison), M4 (the `key-bearing` change class) |
| Fixtures | D9 §1, §4; D1 §10.3 | `fixtures/s0` (13 authored batches with frames) and `fixtures/trace` (segments, targets, exclusions, question expectations, and the vendored original bytes of the four spike pages) | S1, A0, A1, C1, C3, E3 (the v1 witness), I1a, F-Q6 |
| Store | D3 §1; ADR-0021 (P0-D-1) | Migration 0001 generated from M2's `MetaData` and overlay; `ci db init`/`migrate`; the pool and its startup version check; the repository (the only writer of evidence and observation rows, with `payload_schema_id`; span upsert); bulk primitives; negative store tests per invariant | every writer and reader; P3's bulk writer builds on the primitives |
| Infrastructure facts | R11; DA-018…DA-020, DA-022 | The expected-extension-version record, template retention with advisory locks, one coordinate source, and Python manifests in `check_pins.py` | provisioning, fixtures, F4, `just deps` |

## 3. Design of the parts

### 3.1 The package and its entry point (F1, built)

**Layout** follows D9 §1:
- `python/corpus-structure/` is a uv workspace member with `src/corpus_structure/` and `tests/`, and
  `alembic/` beside them.
- The root `pyproject.toml` adds the member to `[tool.uv.workspace]` and `[tool.uv.sources]`. It adds
  the package's tests to pytest's `testpaths`, and `python/corpus-structure/src` to ruff's `src` and
  pyrefly's includes.
- The existing root `tests/conftest.py` for the process scripts stays as it is.

Dependencies are added only by the package that first uses them, pinned exactly (`pin-check` for any
move):
- pydantic, pydantic-settings, typer, rich, sqlalchemy, psycopg and alembic came with F1;
- regex came with F2a, and jsonschema in the dev group with F2b;
- psycopg-pool, which F1 had planned but not added (coordinator §2), is added at F4 as 3.3.3.

The model's dependencies (linkml-runtime, linkml, pglast, pyarrow) are M's.

**Settings** follow D9 §3 and the [interfaces note](../../design_review/evidence/2026-10-28_library-interfaces-eval/README.md)
§4 (Tested there):
- one `Settings(BaseSettings)` with nested plain models (`database`, `paths`, `llm`, `gpu`);
- `env_prefix="CORPUS_"` and `env_nested_delimiter="__"`;
- only init and environment sources, frozen and `extra="forbid"`.

The database setting is one libpq URL (local peer authentication, no password in settings) plus the
template name (`cs_template`); the SQLAlchemy form is derived in code. Settings are built once at the
entry point and passed down, and no module reads the environment.

`extra="forbid"` cannot see a mistyped variable (Tested in the note). F1 therefore provides
`settings_report(settings)`, a result model listing what was resolved (secrets masked) and any unknown
`CORPUS_*` name; `ci status` (orchestration) prints it.

**Coordinator decision 26** (focused pydantic-settings review, 2026-10-28) makes three rules:
- **Result-neutral.** Settings are never stored, hashed or recorded as configuration. A setting may
  supply only a result-neutral default, and the run records the resolved value.
- **Imported sets.** From M1 on, `settings.py` imports the generated closed sets `GpuMode` and
  `AgentMode` instead of restating them (M1's consumer migration).
- **Only `Settings` is a `BaseSettings`.** No model-projected class is a `BaseSettings` (§3.5).

**The CLI** follows D8 §4 and the interfaces note §3 (Tested there):
- `cli/app.py` holds `Typer(no_args_is_help=True)` and a root callback that stores a settings factory
  in `ctx.obj`, so `ci --help` and completion never build settings or touch the database.
- Groups are registered from one tuple in `cli/__init__.py`. Each owning document adds its module
  (`cli/db.py`, `cli/schema.py`, …) and one entry.
- A shared `JsonOpt` alias makes `--json` a per-command option. One `emit(result, json=…)` helper
  writes `model_dump_json()` to stdout or renders with Rich, with diagnostics on a stderr console.
- Typer and Rich are imported only under `cli/`.
- The console script is `ci`; inside `uv run` it shadows GNU RCS's `ci`.

**Shared tests** (`python/corpus-structure/tests/conftest.py`, coordinator decision 10; D9 §4):

- Hypothesis profiles `ci` (`deadline=None`, `derandomize=True`, `database=None`,
  `print_blob=True`, 300 examples) and `dev`, chosen by `HYPOTHESIS_PROFILE` (interfaces note
  §6.1, Tested there);
- markers `db`, `gpu` and `corpus`:
  - `corpus` tests (the 78-page counts, for example) skip when `docs/statistics_corpus/` is absent
    (D9 §4);
  - tests on the trace and spike pages read the vendored pages of `fixtures/trace` (§3.7) and never
    skip;
  - nothing else skips silently;
- a `cli` fixture: Typer's `CliRunner` with stdout and stderr apart and the width fixed;
- **database fixtures** ([store note](../../design_review/evidence/2026-10-28_library-store/README.md)
  §1, Interface-checked there), described below. When `cs_template` or an extension at its expected
  version is missing, `db` tests fail with D3 §13's provisioning instruction. They are never skipped,
  so a missing prerequisite cannot pass as success.

The database fixtures are:
- **A migrated template**, `cs_tpl_<hash>`, cloned from `cs_template` once per migration state.
  - Since F5 the hash covers the Alembic versions directory and `cs_template`'s extension versions.
  - It is built with every engine disposed, because a template must have no other connection while
    it is cloned.
- **A session database**, `ci_test_<pid>`, cloned from that template on an autocommit connection to
  `postgres` and dropped `WITH (FORCE)` at teardown.
- **A sweep at session start.** It drops `ci_test_%` databases whose process is gone, and templates
  under F5's retention rule. It touches only these two prefixes, because the cluster holds other
  projects' templates.
- **A `db` fixture**, which hands over a SQLAlchemy connection inside an outer transaction rolled
  back after the test.
- **A `committing_db` fixture** with its own clone, for tests that need commits (the queue, `NOTIFY`,
  COPY followed by commit).

F1 also created `alembic/` with `env.py` set as the store note §1 says, and an empty versions
directory. The `env.py` settings are:
- schemas included and filtered to the four, views excluded from comparison;
- server defaults compared;
- the CHECK-by-name plugin;
- one transaction per migration;
- `alembic_version` in `public`;
- the connection shared through `config.attributes` for tests.

F4 adds M4's Alembic hooks and 0001.

### 3.2 Canonical JSON and hashing (F2a, built)

`canonical_json(obj) -> bytes` implements D1 §10.1 exactly. A pre-walk builds the normalized value
and refuses, with the path of the offending part, anything outside JSON's integers, strings,
booleans, null, arrays and string-keyed objects. That covers:
- a `float`, a `Decimal`, a date, bytes or a set;
- a non-string key;
- a string that is not valid UTF-8 (a lone surrogate);
- two keys of one object that are equal after NFC.

It then serializes with sorted keys (Python's code-point order over NFC strings), no insignificant
whitespace, `ensure_ascii=False` and `allow_nan=False`, encoded as UTF-8. `digest(obj)` is the full
SHA-256 hex; `make_key(prefix, parts)` is `prefix:` plus its first 32 hex digits. Since F2c, canonical
JSON is applied only to the final key parts, never to reinterpret a dump (R03).

Floats never reach a hash. Two helpers serve the loaders that meet them (YAML pack files, method
configurations, policies):
- `decimal_of_float(x)` gives the canonical decimal string of the shortest round-trip form (`repr`),
  refusing NaN and infinities;
- `canonical_decimal(s)` turns a decimal literal into the D1 §6.2 canonical string. IR-14 (an
  unbounded exponent) is F5's optional item.

The loaders are orchestration's and schema and rules'; the rule (refuse in the hash, convert
explicitly in the loader) is D1 §10.1's.

Alternatives: RFC 8785 would differ in key order (UTF-16) and number form, and D1 §10.1 has chosen
Python's order, so it is not used.

### 3.3 Evidence types and the content digest (F2a, built)

`core/evidence.py` holds the in-memory D1 evidence shapes, the types I0's locator function reads and
I1a produces:

- **The segment kinds**, the D1 §3.2 kinds, email kinds included. Since M1 the set is generated from
  the model with its member properties:
  - `annotation_unit`, `statement_anchor`, `search_block` and `container`;
  - its CHECK and the BM25 kind predicate come from M2's generated forms, not from a list here.

  The short locator forms `u` and `p` are I0's grammar, not kinds. M1 merges `SegmentParseStatus`
  and `evidence.ParseStatus` into the generated `DelimitingStatus`.
- **`Segment`** holds:
  - `kind`, `start` and `end`;
  - `parse_status` (`ok`, `partial`, `failed`);
  - `parse_reason`, the D1 §3.1 reason of a `partial` or `failed` segment, null otherwise;
  - `attrs`, author markup only (D1 §3.2 forbids diagnostics there);
  - `children`.

  Text is not stored on the node; it is the canonical text's substring. Children are ordered by
  start, then the longer first, then kind, and the model sorts them on validation. The reason is
  that siblings may overlap (a paragraph's `sentence` and `math_inline` children) and the digest
  needs one order. The span-ordering check calls M1's generated `ordered` validator (F01).
- **`MacroDef`**: `nargs`, optional `default` (an optional first argument), `body`. The rendition's
  macro table maps names to it (D4 M01).
- **`RenditionContent`**: `canonical_text`, the `document` root and the macro table. Validation
  refuses:
  - a segment outside its parent or the text;
  - `start > end`;
  - two segments with the same kind and offsets, because they would share a segment key.

  `parse_status` of the rendition is a derived property, the worst of its segments'.

`content_digest(content)` is the SHA-256 of the canonical JSON of the model dumped in JSON mode: the
canonical text, the whole segment tree and the macro table (D1 §3.2). Segments carry no diagnostic
attributes, so there is no exclusion list. The search configuration (`ts_config`, from the source
profile's `language`) is not part of the model and so is outside the digest (D3 §5).

The keys of this package are:
- `document_key(project_name, source_uri, content_hash)`, using the project's name, never its
  database id (D1 §10.1);
- `rendition_key(document_key, content_digest)`;
- `segment_key(rendition_key, kind, start, end)`;
- `config_key(method, version, params)`.

**Where the partial reason lives.** The writer stores `parse_reason` under the reserved `attrs` key
`parse_reason`, outside the author-markup names. A `kb.segment.parse_reason` column is the cleaner
alternative for SQL. If M2's model places it as a column, only F4's mapping changes, not the content
model.

### 3.4 `core/tex.py` (F2a, built)

The module implements the token form of D1 §6.2 and ADR-0012 and is the only TeX reader below the
grammar ([text-math note](../../design_review/evidence/2026-10-28_library-text-math/README.md)
§2.3, §3.3):

- **Tokens.** `tokens(latex)` gives TeX's tokens with their positions:
  - a control word is `\` followed by letters, never a `*`;
  - a control symbol is `\` and one other character, and TeX's control space is one token `\ `
    however it is spelled (IR-15);
  - `{`, `}` and `#n` are their own kinds;
  - a whitespace run is one token;
  - anything else is one character.

  `%` is an ordinary character: the corpus has none in math (text-math note §2.3), and comment
  handling would be a source-profile matter. `token_at(latex, pos)` returns the token containing a
  position, which I2a uses to name a grammar error.
- **One drop list**, `DROP`: every `%ignore` literal of SymPy 1.14's `latex.lark`, and the sizing
  commands `\big`, `\Big`, `\bigg`, `\Bigg` with their `l`, `r` and `m` forms, as D1 §6.2 lists them.
  The list's contents were Interface-checked against the installed grammar's lines 1–11 on
  2026-10-28. I2a generates the grammar's added `%ignore` lines from it, and fails its build when an
  `%ignore` terminal of the assembled grammar is not on it.
- **Text-mode commands**, `TEXT_MODE`: `\text`, `\mathrm`, `\textrm`, `\mbox`, `\operatorname`.
  Inside their arguments a whitespace run becomes one space instead of being removed.
- **Macros.**
  - `effective_macros(rendition_table, pack_map)` is the one effective macro table: the rendition's
    table over the pack's fallback map. The pack's map applies only to names the page does not
    define (D1 §6.2, D2 §12.1).
  - The grammar (I2a), the token form and the quote cascade's macro step (A0) all take it from this
    function, so no consumer merges on its own.
  - `expand(tokens, table)` replaces control words by whole name. It reads arguments as TeX does: a
    group or one token, spaces skipped, and an optional `[…]` first argument with its default.
  - Expansion is bounded at depth 16 and at 100,000 tokens of output (D1 §6.2). A token left
    unexpanded at the bound is kept and reported, never dropped.
- **The form.** `token_form(latex, table)` does the following:
  - it strips one outer pair of math delimiters (`\(…\)`, `\[…\]`, or an environment's
    `\begin`/`\end`), but not `$`, which Siegrist uses as prose (D1 §6.2);
  - it expands macros;
  - it removes whitespace and every drop-list token outside text-mode arguments. Inside them,
    drop-list tokens are removed and whitespace collapses;
  - it drops braces around a single token (`b^{2}` is `b^2`);
  - it serializes with one space after a control word that is followed by a letter, so `\mu x` stays
    apart from `\mux`.

  With unbalanced braces it skips the brace step and stays total.

**Properties** (D1 §6.2's metamorphic layer, F2a's tests):
- the form is total (it never raises on any string) and idempotent;
- it is unchanged by inserting `\,`, `\;`, `\!`, sizing commands, braces around a single token, or
  whitespace between tokens outside text mode;
- it never merges `\P` with `\Phi`, `\mu x` with `\mux`, or `x \leftarrow y` with `xarrowy` (whole
  names in the tokenizer);
- `\text{ for all }` keeps its spaces;
- `\cmd*` is two tokens.

The corpus layer (tree printer against token form on every span) belongs to I2a, because it needs the
grammar.

**Freeze.** The module is frozen once S5's `s5.keys-property` record is final; `s5.macros` checks
the expansion rules on the corpus's macro tables (coordinator §7). The two implementation choices
that move keys were settled in D1 §6.2 on 2026-10-28 (IR review): the outer-delimiter strip and the
depth bound. Before the freeze, a change needs only the module's tests. After it, any change that
alters an output is a key-bearing change: a new key scheme with carry-over (§3.6).

### 3.5 D1 shapes (F2b built; reworked by F2c and F2e)

**Authority** (coordinator decision 1; ADR-0020 at P0-D-1, superseding ADR-0017;
[R01](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r01)). The
corpus-structure model is the authority for these shapes. The first revision's split, with
hand-written Pydantic owning the shapes and `core.yaml` a mirror, is superseded.

- **What the generated module supplies.** From M1 on, the shapes read these from `core/_model/`:
  - the closed sets with their member properties;
  - the core qualifier list and its defaults;
  - the local ↔ prefixed name tables;
  - the templated invariant validators.

  M1 regenerates `core/vocab.py` at its import path ([RC04](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#rc04)).
  The `Literal`s in `batch.py`, `DEFAULT_MODALITY`, `CORE_QUALIFIERS` and `STORED_CORE_QUALIFIERS`
  then read `_model` (M1's consumer migration).
- **What stays hand-written.** The shape structure (the discriminated unions, form variants and
  item fields) stays hand-written here until M5. At M5, Stage B generates it, or the fallback emits
  `core.yaml`'s shape classes from these models. Until then M1's interim mirror guard checks every
  shape fact Stage A does not generate.
- **Behaviour** stays in hand-written functions over the types.

Every model is a frozen Pydantic model with `extra="forbid"` and tuples for sequences
([schema-rules note](../../design_review/evidence/2026-10-28_library-schema-rules/README.md) §1,
Tested there). Names the schema owns (predicates, classes, statement kinds, condition predicates, a
pack's qualifier names) stay plain strings in the generic models. An unknown name is therefore a
schema error reported by S1's compiled models, not a malformed-JSON error. Under X2-01 the authored
form names schema elements by local name and the stored form by prefixed name (D2 §7.1).

**Two forms, one factory.** The model-facing (authored) and stored forms differ only where a text
is anchored:
- `phrase` values and `phrase`/`unsupported` condition leaves carry `text` and an optional
  `sentence` when authored, and `start`, `end`, `text` and an optional `coarse` when stored (D1 §6,
  §7);
- evidence and `unsupported` items carry `sentence` and `quote` when authored, against `start`, `end`
  and `coarse` when stored (D2 §7.3).

One function builds, for a given form, the value union and the named recursive `Condition`
(`TypeAliasType`, discriminated on `op`, one `$defs` entry), so the two unions share every other
model. The alternative was a single model with all fields optional and a form check. It would accept
a stored offset in an authored batch and report it later and less exactly.

**Values** (D1 §6):
- `text`;
- `number`: `v` is constrained by `Field(pattern=…)` to the canonical decimal of D1 §6.2, so a
  non-canonical number is refused with the canonical spelling in the message and never rewritten.
  `unit` and `basis` are kept as written;
- `bool`;
- `enum`, which has a variant per form since F2e (R04): the authored form takes the local enum name,
  and the stored form requires the prefixed one;
- `entity` (`ref`);
- `formula` and `set`, which carry `latex` and `symbols`, plus `sympy` and `parse` with `MISSING`
  defaults. `sympy` and `parse` are refused in both batch forms and set only by M11 in consolidation;
  `parse` (generated `ParseOutcome`) includes `ambiguous` (D1 §6.1);
- `date`: ISO 8601 by pattern, kept verbatim;
- `interval`, whose bounds are values or null;
- the form's `phrase`.

**Bindings.** A symbol binding has `bind` (the D1 §6.1 kinds) and the `entity`, `claim` and `param`
fields its kind requires, checked by a model validator.
- **Why one class.** The model declares one binding class, and its per-kind field requirements are
  `iff_present` invariants where the templates express them. That is why a discriminated union per
  kind is not used.
- **How the validator is kept.** Requirements the templates cannot express stay in the hand
  validator until M5, and M1's interim guard covers them.

Formula positions take only value objects. The v1 batches already do so (checked over
`reference_model_v1`, 2026-10-28), and D2 §7.3's decoding rules want one shape per position.

**Conditions** (D1 §7): `and`, `or`, `not`, `claim`, `member`, `cmp`, `pred`, `forall`, and the
form's `phrase` and `unsupported` leaves. The arguments of `pred` are entity references or formula
values.

**Core qualifiers.** `CoreQualifiers` carries:
- `modality` and `polarity`, with defaults that `Field(exclude_if=…)` leaves out of dumps (so equal
  meaning gives equal JSON, D3 §6.1) and fills in for rule views (schema-rules note L-11, Tested
  there);
- `hedge`, `attribution`, `conditions`, `scope` and `valid_time`, absent by `MISSING`. `scope` is the
  extent when authored, and the segment key and extent when stored.

The qualifier list, the defaults and the stored range of `scope` come from M1's `QualifierSpec`s
(TM §8). The generic model accepts extra keys as raw JSON for schema qualifiers. S1's per-predicate
models subclass it with `extra="forbid"` and typed fields.

**Typed dispatch** (F2c; R03; [DA-004](../../design_review/audit/semantic-model-and-authority.md#da-004)).
Operations consume the typed model, never a dump.
- **Pattern matching.** Canonical forms, traversals, citation finding and re-addressing
  pattern-match on the typed unions (`match v: case FormulaValue(): …`). Exhaustiveness is enforced
  with `typing.assert_never`, which pyrefly checks. A test enumerates each union's members, from the
  union's `typing.get_args` now and from the model after M5, and drives every member through each
  dispatch.
- **One condition visitor.** A condition tree has one typed visitor that yields nodes, consumed by
  `claim_refs`, `canonical_condition` and binding collection. The three walks with different
  unknown-operator handling collapse into one. An unknown operator is unrepresentable after
  validation, so the `ValueError` that escaped `key_claims`'s no-raise contract disappears.
- **Citations by type.** Citation positions are the fields whose declared type is `SentenceId` (an
  annotated pattern type now, the model's `SentenceId` type later, TM §4), enumerated from the form
  model. `cited_sentences` and the frame's rewrite stop treating every key named `sentence` or
  `anchor` as a citation, so a pack qualifier named `sentence` is safe.

**Typed references and complete translations** (F2e; R04; coordinator decision 21; DA-005, DA-006).
- **The whole meaning.** The stored batch and the keyed candidate set carry everything a batch
  holds:
  - a typed rendition reference, not a `KeyContext` supplied on the side;
  - alternatives and unsupported items;
  - each claim's `establishment`, `derived_from` and `rule`.

  Every optional field follows the `MISSING` convention. "Not yet keyed" and "awaiting resolution"
  are typed states, never `None`.
- **References typed by kind.** In each context there is an entity reference, a statement reference
  and a claim reference: each a local ref when authored and a key once stored. The subject is "entity
  or statement" by type, not by comment.
- **Who checks references** (RC19).
  - `validate`'s batch checks (S2) own reference and type checking for batches.
  - Foundations' keying resolver has per-kind lookups (`entity(ref)`, `statement(ref)`,
    `claim(ref)`) and refuses a wrong-kind reference among pool candidates with a typed drop code.
- **Completeness.** Each translation whose types live here declares its source and target classes.
  A model-derived test enumerates the source slots, each either mapped or declared omitted (DP-08).
  T2's function is S2's and T3's is P1's; the completeness harness and the target types are
  foundations'.

**`ExternalReference`** (F2e; [RC11](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#rc11);
[DA-007](../../design_review/audit/semantic-model-and-authority.md#da-007)). References outside the
batch become a typed core node, closing OPEN-D1-5 at P0-D-1.
- **Authored.** The `outside` item carries a descriptor: the citing sentence (`SentenceId`) and
  quote, and the author's link target when there is one.
- **Stored.** It is stored with its span.
- **Keyed.** It is keyed by the citing statement's key plus the descriptor's text form (§3.6), and
  claims keep it as subject or object.
- **Resolved by consolidation** (C1), which records a `resolves_to` relation and re-keys the citing
  claim to the resolved statement (a declared stability limit). An unresolved reference stays a typed
  node, never a dropped claim.

**Batch items and envelopes.** Generic `EntityItem`, `StatementItem`, `ClaimItem`, `AlternativeItem`,
`UnsupportedItem` and, since F2e, the `outside` item, in both forms. In `ClaimItem` the predicate is
a string and the qualifiers are the generic `CoreQualifiers`. The generic `AuthoredBatch` and
`StoredBatch` envelopes carry D2 §7.3's fields.
- **Who uses them.** A0 (schema-free), the fixtures and the `claim_proposal` payload use these generic
  models. S1's compiled envelope over the same item bases is the full validation.
- **The rendition.** The stored batch names its rendition by the typed reference above. The record
  that holds the batch (`kb.observation.rendition_id`, `eval.golden_pass`) keeps its row-level
  column.

**The citation frame** (D1 §10.3) maps each sentence id (`s1`, `c1`, …, typed `SentenceId`) to its
locator string and canonical text. Two functions come with it, both built on I0's resolver:
- `resolve_frame(frame, rendition)` selects, for every entry, the one sentence segment whose text
  equals the recorded text. Otherwise it refuses with the failing entries and the resolver's
  candidates.
- `readdress(batch, frame, served_frame)` rewrites an authored batch's sentence ids into those of a
  served packet by matching locator and text, refusing an entry the packet lacks. This is how the
  acceptance test submits fixture batches through the MCP tools (C3).

Since F2c each failure is a `FrameFailure` with a `FrameFailureReason` code. The codes are: text
differs; the locator is refused; the locator selects a non-sentence; cited but not in the frame; not
in the served packet. The message is a projection of the code. A re-location writes a new frame
version with a parent link and never edits a frame in place (coordinator decision 2; R06). The rows
that hold frames record the versions (A0, E1).

**The keyed candidate set** is the core claim shape that `validate`'s view builder reads at both
call sites (D5 §8.2). S2's T2 adapter and P1's pool loader (T3) both produce it. It holds:
- **entities**: `id`, `key` or the unkeyed state, type, label, scope, symbol, aliases and identity;
- **statements**: `id`, `key` or the unkeyed state, kind and anchor;
- **`ExternalReference` nodes**: `id`, key, descriptor and resolution state;
- **claims**: `id`, `key` or the unkeyed state, predicate, typed subject reference, object entity
  reference or value, stored-form qualifiers, statement reference, statement role, establishment,
  `derived_from`, `rule` and stored evidence;
- **alternatives and unsupported items**;
- **the rendition reference**.

At submission ids are local refs and keys are in the unkeyed state; at finalize ids are keys. The
view builder takes two further things as arguments, and they are not fields here: the derived view
attributes, and the grammar's facts at finalize. The grammar's facts are each value's parse status,
kind and symbols, which C1 hands over as data (D9 §1, D5 §8.2).

**Observation payloads and operations JSON** (D3 §6.2–§6.3 as amended). There is one model per
observation kind, registered by kind, including:
- `mention.math`, `value.math_kind` and `scope.reopens`;
- the `verification` detail `{rule, severity, message}` that M19 writes for a failing rule;
- a `claim_proposal` payload whose `authored` and `citation_frame` are present together or not at
  all (a `together` invariant, F01). Since F2e it also records its derivation: the cascade version
  and the schema version that derived its stored `batch`
  ([R06](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r06)).

The operations JSON models are `mention_ref`, `trigger_metrics`, `cost`, the policy action (a
`<method>/<name>` reference, a limit, `then`) and the intervention target.

Each payload class is a registered payload schema (M4's registry content). A reader dispatches by the
row's `payload_schema_id` and never parses a stored payload under current defaults.

**Operations models stay frozen `BaseModel`, never `BaseSettings`** (coordinator decision 26). This
covers the operations JSON models above, run options and method `params`. Validating a `BaseSettings`
reads the environment: `model_validate({})` returned the environment's value under pydantic-settings
2.16.1. That is a scratch check, recorded as `p0q.settings-env` by F5. A stored `ops.run.options` or
a method's `params` re-read through such a class would silently mix in the current environment
(DP-24, DP-09).

**Closed value sets** move to model and projections (M1;
[DA-002](../../design_review/audit/semantic-model-and-authority.md#da-002),
[DA-012](../../design_review/audit/structure-and-invariants.md#da-012)).
- **What is replaced.** F2b's hand-written `core/vocab.py` mirrors D3's CHECK lists. M1 replaces it
  with a file generated at the same import path from the model's static and version-scoped sets.
- **What M1 changes in it.** M1 adds the TM §11 sets, merges `SegmentParseStatus` into
  `DelimitingStatus`, renames the formula outcome `ParseOutcome`, and gives `PolicyChain` its `gaps`
  member.
- **How the CHECKs are built.** M2 builds the 0001 CHECKs from the same declarations.

Foundations no longer owns a vocabulary list. Its consumers import the generated names.

**JSON Schemas.** `core/schemas/*.json` are generated from the core adapters (D3 §6) by one
deterministic `GenerateJsonSchema` subclass: no titles, `$schema` set to 2020-12, stable order.
- **Where it lives.** It lives in `core` because both these files and S1's batch schemas need it, and
  `core` cannot import `schema`. S1 reuses it.
- **The `$id`.** M3 adds the `$id` per model revision.
- **Drift.** The files are committed. A test regenerates them and fails on a difference, runs
  `Draft202012Validator.check_schema` on each, and validates fixture payloads with jsonschema.

That agreement between Pydantic and jsonschema is **derivation conformance**, not an independent
oracle: both come from one model, so a shared mistake passes both (coordinator decision 24;
[R12](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r12); F02).
F2c corrects the wording in the `core/schemas` docstring and in `tests/core/test_shapes.py`. The
independent controls for these shapes are:
- the external S0 and S0-R2 batches (`fixtures/s0`, S1's acceptance);
- the hand-authored conformance vectors (§3.6);
- the negative store tests (§3.8);
- tex parity.

### 3.6 Canonical forms, declared identity and keys (F2b built; reworked by F2c and F2d; frozen at F2e)

**Identity is declared** (coordinator decision 20; ADR-0023 at P0-D-1, extending ADR-0019; R02;
[TM §8](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28_target-model.md);
[DA-001](../../design_review/audit/semantic-model-and-authority.md#da-001)). Every qualifier, core
and schema alike, has a `QualifierSpec`. It holds the qualifier's range and default, and its **key
role**, which is one of:
- `identity`: it enters the claim key;
- `meaning`: it carries meaning outside the key, so a disagreement makes alternatives;
- `inert`.

It may also hold a **role condition** (`key_role_when: <member property>`). Beyond those, it holds
its **canonical form by range**, its **case policy** and its store placement.

**The core qualifier specifications** are generated by M1 into `core/_model/qualifiers.py`:

| Qualifier | Key role | Condition |
|---|---|---|
| `modality` | identity | — |
| `polarity` | identity | — |
| `hedge` | meaning | — |
| `attribution` | meaning | identity when modality ∈ `attribution_identifying` (today `{cited}`) |
| `conditions` | identity | — |
| `scope` | meaning | — |
| `valid_time` | identity | — |

`statement` stays a key part of its own, beside the qualifiers (D1 §10.1). Schema qualifiers take
their role from the pack: S1 compiles `ci:key_role` on the slot, or compiles the existing
`ci:identity_qualifiers` list into the same specification.

**`KeySchema`** is the one compiled input that keys, consolidation's slots and conflict detection,
and the rule view read. F2d defines the type in `core`; the core half comes from `_model` and the
pack half from S1's compiled lookup. It holds:
- identity keys per class, prefixed;
- `entity_identity`;
- symmetric condition predicates;
- prefixed predicate names;
- the qualifier specifications per predicate (core ∪ pack);
- the case policy of each class's label and of each string-ranged slot;
- the key scheme.

`claim_parts` stops hard-coding the role rule, and the literal `cited` leaves `keys.py`.

**Canonical form by range** replaces `canonical_qualifier`'s JSON-shape test (TM §8):

| Range | Canonical form |
|---|---|
| `Formula`, `SetExpr` | `{t, latex: token_form}` over the effective macro table, with `symbols`, `sympy` and `parse` outside (ADR-0012) |
| `TextValue`, `PhraseValue` | text form: NFC, whitespace collapsed, case per policy (fold by default) |
| a string identifier (`string` range, `ci:case` declared) | NFC, whitespace collapsed, the declared case |
| an enum | `{enum: <prefixed enum name>, v: <member>}` verbatim |
| an entity class or `Entity` | the resolved key, after the resolver's kind check |
| `IntervalValue` | recursive over bounds and inclusivity |
| a `MapEntry` subclass | an object from key (NFC) to the canonical form of the entry's value range |
| `NumberValue` | the (already canonical) decimal `v`, with `unit` and `basis` NFC and collapsed, never converted (D1 §6.2) |
| `DateValue`, `BoolValue` | verbatim |

A map entry `{"ref": "Smith"}` whose declared value range is a string is canonicalized as a string,
no longer read as an entity reference, and `"Shape-Rate"` is canonicalized by its slot's declared case
(DA-001's closure cases).

**Conditions** take D1 §7's canonical form, through F2c's one visitor:
- nested `and`/`or` are flattened, empty ones are dropped (an empty tree is no condition), and a
  one-argument `and`/`or` is replaced by its argument;
- `and`/`or` arguments are sorted by canonical JSON;
- `>`/`>=` are written as `<`/`<=` with the sides swapped;
- `pred` arguments are sorted only for predicates the schema declares symmetric;
- `phrase`/`unsupported` leaves are keyed by text form, and other leaves by their range's form.

**Bindings** have a canonical form too, used only for alternative member keys. It holds the symbol in
token form (a lone control word without its backslash), the bind kind, the referenced entity or claim
key, and `param`. **Symbols** enter keys the same way (`\mu` is `mu`, D1 §6.1, §10.1) and keep their
case (`symbol_form`).

**Case policy** (`ci:case`; [DA-008](../../design_review/audit/semantic-model-and-authority.md#da-008)).
- `fold` applies to prose labels and prose literals.
- `preserve` applies to math-bearing text:
  - labels of classes declared math-bearing (`RandomVariable`, whose label is the defining
    expression when it has no symbol);
  - literal identity slots whose fallback is a symbol (`FamilyParameter.canonical_name`, under
    OPEN-D1-3's rule).

`text_form` stops casefolding math labels, so the label and symbol paths become consistent. `X`/`x`
and `\Sigma`/`\sigma` key apart where declared math-bearing, and stay equal under `fold`.

**Label normalization** (D1 §10.1, D5 §3.3 point 5) is one generic function,
`normalize_label(text, type, rules, case)`. Its steps run in this order:
1. the text form, under the class's case policy;
2. one leading article removed;
3. the pack's rewrites applied in their declared order, each a `match`/`replace` pattern (D2 §12.1);
4. the class's head words removed as trailing whole words;
5. whitespace collapsed again.

`LabelRules` (articles, head words per prefixed class, rewrites) is a core model filled from the
pack's `aliases:` section; core holds no word list. Keys, phase 0 linking by normalized alias and
canonical-label choice all call it. So one change of the rules moves all of them together and is
visible in the configuration hash.

**Keys** (D1 §10.1, D5 §5.2–§5.3) take a `KeyContext` (the document key, the rendition content with
I0's generator, the merged macro table) and a `KeySchema`:

- **global entity** `ent`: type and identity attributes (entity keys, or the canonical form of a
  literal by its range), plus the normalized label only when the class's declared identity keys are
  incomplete;
- **local entity** `ent`: type, the scope segment's generated locator in structured form, and the
  symbol in key form or, without a symbol, the normalized label;
- **statement** `stm`: the anchor's generated locator in structured form, plus the 1-based ordinal of
  the statement's first sentence among the anchor's sentences.
  - The anchor is found by containment: the innermost segment of a kind with the generated
    `statement_anchor` property (`details`, `unit`) that contains the first sentence.
  - Otherwise it is the annotation unit (D1 §3.4) that contains it. That is how D1 §10.1's "the
    unit, the `details` block, the paragraph outside units" reads without depending on the
    statement kind (M1 replaces the literal kind subset, DA-003).
- **external reference**: the citing statement's key plus the descriptor's text form (F2e);
- **claim** `clm`:
  - the subject key, the prefixed predicate, and `{key}` or `{value: canonical}`;
  - `statement` (its key);
  - each qualifier whose specification gives it the `identity` role, or whose role condition holds,
    in its range's canonical form. `modality` and `polarity` enter only when not default;
    `attribution` (its key) enters only when the modality has `attribution_identifying`;
- **alternative member**: the claim's parts plus the member's canonical values of the disagreeing
  `meaning`-role qualifiers, or its canonical bindings when the bindings disagree (D5 §5.3).
  Referenced claims in those bindings are named by their base keys, so member keys cannot form
  cycles. `member_parts` reuses `claim_parts`;
- **groups**: `alt` and `idg` over the sorted member keys (D1 §10.1);
- **batch keying**: `key_claims(candidates, …)` keys claims in a topological order of their
  condition `claim` references. Beside the keys it returns the claims it dropped, because they lie on
  or behind a reference cycle or fail a lookup, each with a `DropReason` code (D5 §5.2). Which claims
  are alternatives and which disagree is C1's decision, passed in.

**Preparation once** (F2c; [DA-025](../../design_review/audit/execution-fit.md#da-025)). A
`KeyContext` prepares the rendition's annotation units and segment keys once, and reads stored
segment keys where the store has them. Per-claim keying no longer repeats rendition-wide work.

**Typed outcomes** (F2c; decision 23;
[DA-013](../../design_review/audit/structure-and-invariants.md#da-013)). `KeyingError` carries a
`DropReason` code, the ref and structured detail; `str(error)` is no longer a reason. The codes are:
- an unknown predicate;
- a segment not on the rendition;
- a statement outside the unit;
- an unknown or dropped item;
- an identity naming an unknown entity;
- an identity cycle;
- a condition cycle;
- since F2e, a wrong-kind reference.

F2c declares `DropReason` and `FrameFailureReason` as `StrEnum`s beside their consumers. M1 then
takes them into the model and the generated vocabulary with the same members. C1's `PassReport`
counts by code.

**The key scheme is recorded beside keys, never inside them** (RC07, RC08).
- **Where it is declared.** The model declares `ci:key_scheme: N` in `core`, and F2d reads it from
  `_model`.
- **Where it is recorded.** Every keyed output carries the scheme of its keys. Orchestration records
  it per run (O1), and evaluation records it per judgment target (E1).
- **How keys are compared.** Readers compare keys only within one scheme, or through the carry-over
  map.

Why beside: a scheme number hashed into every key would move every key on any scheme fix, even one
that changes no output for most inputs. That would orphan every judgment and cross-run diff (DP-04,
DP-09; review R02).

**Conformance vectors** (F2e; [RC07](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#rc07);
R12). Each scheme has a vector of inputs written by hand:
- values of every range form;
- condition trees;
- entities with identity;
- statements on a small rendition;
- an external reference.

Each input has its **expected key parts written by hand** from D1 §10.1 and TM §8. Its expected key
is computed by the test with `hashlib` over those hand-written bytes, never through `make_key` or
`canonical_json`, so the answers do not derive from the code under test. Any change to an output
fails until the scheme moves. Vector v1 is written when scheme 1 freezes, after `s5.keys-property`
(TM §12). Fixtures still compare key equalities, never values (D1 §10.1).

**Carry-over (T8)** (F2d builds it; F-Q6 probes it).
- **The function.** `carry_over(inputs, from_scheme, to_scheme)` returns the old key → new key map. It
  is computed by keying the stored authored inputs under both schemes. Keys whose input is unavailable
  are reported, never guessed.
- **Who uses it.** Cross-run comparisons, carried judgments and reference-run key reuse go through
  the map when the schemes differ.
- **What Q-6 settles.** It settles how the outgoing scheme's functions stay callable when a scheme
  changes: a frozen module per scheme, or a map computed by the outgoing release.

**Stability limits** ([DA-014](../../design_review/audit/structure-and-invariants.md#da-014); D1 §10.3
as P0-D-1 amends it):
- locator regeneration;
- the first-sentence ordinal shift within an anchor, when an earlier sentence in that anchor is
  inserted or re-segmented;
- key-derivation changes, handled only through scheme versions and carry-over.

A test shows the ordinal shift. Inserting a sentence before a statement's first sentence in its
anchor moves that statement's key and the keys of later statements in that anchor, and no other
statement key.

**Freeze.** Key functions freeze at F2e, as scheme 1, once three things are in:
- R02's specifications (F2d);
- R03's typed dispatch (F2c);
- `s5.keys-property`, which freezes `core/tex.py` (TM §12).

After the freeze, a change to any output is M4's `key-bearing` class: a new scheme, a carry-over map
and a new conformance vector.

These functions are pure and read neither the database nor the schema files. S1, C1 and the tests
supply the facts. C1 fills the keyed candidate set's key fields with these functions.

### 3.7 Fixtures (F3)

**`fixtures/s0`** holds the 12 v1 reference batches as 13 files, one per annotation unit of
`core12`. The spike's T1 is two annotation units: the lead-in paragraph
(`special/LocationScale.html@p:As usual, our starting point`) and `#dfn1`, both in the `trace` slice
(D2 §12.2). Each file holds:
- the unit key;
- the authored batch, its `unit_ref` the unit key rather than the spike's `T1`…`U12`;
- the citation frame;
- provenance: the source file in `results/s0r2/reference_model_v1/`, the decisions of
  `decisions_v1.json` that touched it, and for T1 the split.

The three parts of the file set are these.
- **The T1 split.**
  - The assumption statement `st1`, `Z`, `c_Z_values` and the three unsupported items (all on
    `s1`–`s3`) move to the lead-in file.
  - The definition and its claims move to the `#dfn1` file, which redeclares `Z` (local, extent
    `section`) because `c_X_def` and `c_constr` bind it.
  - Sentence ids stay as authored; the frame makes them absolute. Acceptance shows that both
    declarations of `Z` key alike, so consolidation meets one entity.
- **Frames** are built once from the spike packets (`results/s0r2/inputs/packet_v1/units/`, which
  number sentences and list standing context). They are built with I0's generator over the S1
  renditions the references are stored on.
  - The conversion reads the spike results as data and never imports spike code.
  - Its output, committed, is the authority from then on. The conversion script is kept beside the
    fixtures only as provenance.
- **Acceptance** comes after I1a, I2a and A0 (coordinator decision 6). It requires:
  - every frame resolves on the production rendition;
  - A0's stored form gives the same evidence offsets as `reference_v1`. This is the
    rendition-identity check against the spike, since the renditions are content-identical;
  - each `cN` entry (U12's) is in I2a's standing context for its unit;
  - the batches validate against F2b's authored models. S1 validates them against the compiled
    schema in its own acceptance.

**`fixtures/trace`** is written by hand from `trace.md`'s tables, independently of `fixtures/s0`,
so the acceptance test checks proposals against targets they did not produce (D9 §1). It holds:

- **`<unit>.segments.json`** for the five trace annotation units. Each file lists every segment's
  kind, generated locator, offsets, author attributes and parse status, with the counts `trace.md`
  states (math spans, sentences).
  - Kinds, counts and attributes come from `trace.md`.
  - Offsets come from the S1 renditions, so this part is also a rendition-identity check.
  - I1a's acceptance compares production output with it.
- **`<trace unit>.target.json`** for T1–T4. Each holds:
  - the target entities and claims as an authored batch with a citation frame. T1 cites the
    sentences of both its annotation units;
  - `must_not`, each "must not appear" line as a partial claim pattern;
  - `questions`, each D8 §5.3 query with its parameters and the target refs it must return, with and
    without `include_suppositions`;
  - phase marks (T3's D1 is phase 2).

  Exact formula text is copied from `trace.md` where it states it, and from the v1 batch where
  `trace.md` abbreviates (it says the batches are exact there). Each such item records which.

**Vendored pages.** `fixtures/trace/corpus/` holds the original bytes of the four spike pages the
fixtures use: `special/LocationScale.html`, `Normal.html`, `LogNormal.html` and `Gamma.html`, about
98 KB.
- **Where they sit.** They sit at the same paths under the same root as in
  `docs/statistics_corpus/corpus/` (`siegrist_random/random/special/…`).
- **What comes with them.** The index entries the source profile's corpus index needs for them (that
  index's format is ingest and math's), and a `NOTICE` keeping Siegrist's CC BY 2.0 attribution.
- **Why this matters.** Because the bytes, the paths and the root are the corpus's, so are their
  source URIs, content hashes, document keys and locators. The acceptance test (C3) and ingest's
  trace tests therefore run without the gitignored corpus and never skip.
- **The check.** When the corpus is present, a test checks the vendored bytes against
  `docs/statistics_corpus/MANIFEST.sha256`.

The citation frames come from the S0-R2 v1 packets. Those use the same packet rendering as the pack's
worked examples (`reference/E*`, D4 §4.1), so the fixtures and the examples number sentences and
present standing context alike. The examples themselves are schema and rules' and agent interface's.

The target shapes beyond F2b's (the `must_not` pattern, the question entry) are small models in the
tests' support package, documented in `fixtures/trace/README.md`.

**The agreement check.** Fixture tests compare key equalities, never key values (D1 §10.1, D9 §4).
F3's agreement check derives both the targets and the trace units' fixture batches on the production
rendition and keys them with the key functions (scheme 1 once frozen). It then requires three things:
- equal key sets over the phase 0 targets;
- no fixture claim matching a `must_not` pattern;
- every difference explained and resolved, by correcting a fixture or by a `trace.md` correction
  from the design owner.

The comparison of query rows with targets in the acceptance test is C3's. The fixtures are also the
stored authored inputs that F-Q6 keys under two schemes.

### 3.8 The store (F4)

**What F4 builds on** (coordinator decision 18; [R05](../../design_review/reviews/design_review_domain-model-alignment_2026-10-28.md#r05);
RC03, RC05, RC06). F4 no longer hand-writes table metadata.
- **The generated metadata.** The SQLAlchemy `MetaData` is generated from the model into
  `core/db/_tables.py`, and the physical overlay is `core/db/overlay.py`. Both are M2's. They cover:
  - tables and columns;
  - digest-named CHECKs for static sets;
  - per-version member tables with composite FKs for version-scoped sets;
  - the edge tables `kb.claim_ref` and `kb.claim_entity_ref`, and `kb.entity_identity`;
  - the `modality`, `polarity`, `attribution_entity_id` and `schema_version_id` columns of
    `kb.claim`;
  - `UNIQUE (run_id, id)`;
  - `kb.entity.resolved_to_id`, `ops.run.cut_at` and the run's revision, schema and scheme columns;
  - `meta.model_revision`, `meta.payload_schema` and `payload_schema_id`;
  - indexes, the BM25 partial index, the three views and the extension assertion.
- **What it supersedes.** It supersedes this document's earlier plan, which declared every table
  "exactly as D3 §3–§8 state them" with "CHECK lists built from `core/vocab.py`". D3 now cites the
  model files and their generated renderings (RC03).
- **The S6 additions.** S6 folded additions into D3 on 2026-10-28:
  - the `meta.schema_slot` and `meta.schema_rule` columns;
  - `kb.entity.kind`;
  - `ops.measurement.task_id` and the `rule` scope type;
  - the `task_cache` predicate;
  - `eval.golden_set.sampling` and the seed and reason on `eval.document_split`;
  - the intervention kind `promotion`;
  - `kb.segment.ts_config`.

  They are now model and overlay declarations, which M2's pglast port check compares with `s6.ddl`.
- **What F4 owns.** F4 owns migration 0001, `ci db`, the pool and the repository.

**Migration 0001** is generated once and frozen; it never imports `core/db`.
- **How it is generated.** It is rendered once by `alembic revision --autogenerate` against an empty
  clone of `cs_template`, from the generated `MetaData` plus the overlay.
- **The hooks.** `env.py` carries M4's Alembic hooks:
  - `template_args` puts the model revision into the revision file;
  - `process_revision_directives` refuses a revision not registered in the model-revision log;
  - `on_version_apply` records applied revisions.
- **How it is reviewed.** It is reviewed by hand against the generated `MetaData`, the overlay and
  M2's recorded port-check residue.
- **What `op.execute` carries** (only what metadata cannot):
  - the overlay's extension assertion, which since DA-018 asserts each extension's `extversion`
    against F5's record of expected versions, not mere presence. 0001 is frozen with the versions
    recorded when it is generated. A later extension move is its own migration, which asserts the
    new versions;
  - the four `CREATE SCHEMA` statements;
  - the overlay's views.
- **The downgrade** drops the four schemas with `CASCADE` and leaves the extensions, which role
  `paul` could not recreate.
- **The catalog comparison.** `alembic check` misses index methods, `WITH` options, operator
  classes, partial predicates and CHECK bodies. A test therefore compares the catalog after
  `upgrade head` with the catalog after `create_all` of the generated `MetaData` plus the overlay's
  DDL (store note §1).
- **Same-run FKs.** The same-run composite FKs for INV-03 and INV-08 are in 0001 only if F-Q4 chooses
  FK enforcement (M2 declares, Q-4 places). Otherwise the bulk writer checks them, and the negative
  store tests below cover both placements.

**`ci db`** has two commands. Both report the head revision and the model revision, with `--json`.
- `init` creates the configured database `TEMPLATE cs_template` on an autocommit connection to
  `postgres`. It checks that the server encoding is UTF-8 (offsets are code points on both sides only
  then), and that each extension's version equals F5's record. Then it upgrades to head.
- `migrate` upgrades an existing database.

**Connections** (D3 §1; store note §5, Interface-checked there).
- **The pool.** `open_store(settings, application_name, min_size, max_size)` opens one psycopg-pool
  3.3.3 `ConnectionPool` per process (pin added here with `pin-check`) with these settings:
  - `close_returns=True`;
  - `check=ConnectionPool.check_connection`;
  - a `configure` callback that only sets the JSON dumps and loads and leaves the connection idle.

  The pool is lent to SQLAlchemy through `creator=pool.getconn` with `NullPool`. Callers choose the
  sizes the store note lists per process.
- **The version check at startup.** After `pool.open()` and `pool.wait(timeout)`, `open_store` runs
  `SELECT extname, extversion FROM pg_extension` once on a borrowed connection. It refuses with a
  typed `ExtensionVersionMismatch` that names the expected and found versions.
  - **Why outside `configure`.** The check never runs inside `configure`. The pool treats every
    exception there as a connection failure (`CLIENT_EXCEPTIONS = Exception`, `pool.py:35` at tag
    `pool-3.3.3`), so a mismatch would turn into retries and then a `PoolTimeout` that hides the
    cause. Source-checked by the review's contributor B;
    [psycopg-pool overview](../../libraries/psycopg-pool.md) §5.1, §7.2; R11.
- **Session state** is set only with `SET LOCAL`.
- **COPY.** A COPY inside an SQLAlchemy transaction uses `connection.driver_connection`, never its
  own commit.

**The repository** (`core/db/repo.py`) is the only writer of evidence and observation rows
(coordinator §4). It is also the only writer of `ops.intervention`, `eval.golden_pass`, and a golden
unit's `status` and `agreement` (D3 §5 "Writers", §7, as amended). It holds the primitives other
writers use:

- `get_or_create(conn, table, values, unique)` serves the content-hash version tables, methods,
  method configurations and documents. It runs `insert().on_conflict_do_update(...).returning(id)`
  with PostgreSQL 18's `old` to report whether the row was new (store note §2, Interface-checked
  there).
- `store_rendition(conn, document, content, build)` does the following:
  - it computes the digest and key, and inserts the rendition unless `(document_id, content_digest)`
    exists;
  - it writes the segments only when the rendition is new. Ids are pre-allocated from the identity
    sequence so parent links go in one statement; `ts_config` comes from the build's profile
    language; the text is taken from the canonical text;
  - it records the build `(document_id, method_config_id)` every time, with its
    `payload_schema_id`.

  A build row that already names a different rendition for the same configuration and bytes is
  refused. It means an ingest that is not deterministic, which a silent overwrite would hide.
- `upsert_spans(conn, rendition_id, ranges)` runs one `INSERT … SELECT … FROM unnest(…) ON CONFLICT DO
  NOTHING RETURNING`.
  - The text is cut from the rendition's canonical text in SQL, and the smallest containing segment
    is found there (D1 §3.3).
  - Then one select reads the rows that existed, and one re-query reads keys a concurrent writer
    took.
  - A range outside the text is refused, so INV-10 holds by construction.

  C1 is its high-volume caller; ingest and the observation path are the others.
- `write_observations(conn, task_id, rows)` writes by binary COPY with `Copy.set_types` from the
  generated column types, inside the caller's transaction, after O1's fencing update.
  - Rows arrive with span and segment ids resolved, and each payload as the validated core model of
    its kind (the parameter's type says so), dumped with defaults omitted.
  - Each row's `payload_schema_id` is taken from M4's registry for the payload's class. A class with
    no registered schema is refused before any write.
  - The method-contract `ObservationDraft` is O0's, and O1 turns drafts into rows, so F4 does not
    depend on O0.
- `record_intervention(conn, …)`, `store_golden_pass(conn, …)` and `set_golden_unit(conn, unit,
  status, agreement)` are typed primitives over the generated columns. The first two write
  `payload_schema_id`.
  - The first is called by the agent interface's submission tools and CLI commands.
  - The golden ones are called by evaluation's golden store (P0-E-1), which `write_golden` calls.

  Their callers own when and why; the rows' shape and the single write path are F4's.
- `copy_rows(conn, table, columns, rows)`, `allocate_ids(conn, table, n)` (`nextval` over the
  identity sequence) and `insert_returning(conn, table, rows)` (`insertmanyvalues` where ids come
  back) serve the bulk writers of other documents. C1's materialization of claims, edge rows and
  identity rows comes first; P3's bulk writer from generated schemas builds on them.
- `insert_artifact(conn, row)` writes `meta.compiled_artifact` with its `payload_schema_id` and has
  no update path (P0CL-15's store share). S1b writes through it.

**Reading payloads.** A reader of a payload-bearing row dispatches through M4's reader dispatch by
the recorded `payload_schema_id`. It refuses an unknown id with M4's typed error, and never parses a
stored payload under the current defaults (R06; DP-24).

**The validation boundary** (D3 §6 as amended; schema-rules note §4, Measured there at about
1.5–2 µs per value in Pydantic against 118–338 µs in jsonschema).
- **Validate once.** JSONB is validated once, where it enters: a method's output, a submission, a
  loader. The repository takes validated models and writes `model_dump(mode="json")` without
  validating again.
- **Schema-dependent parts.** A stored batch's per-predicate claims and `kb.claim.qualifiers` are
  validated by the caller with S1's compiled models, because `core/db` sits below `schema`. The
  agreement result model is evaluation's.
- **Absent values.** An absent value is SQL NULL, never `Jsonb(None)`, which would store JSON `null`
  and defeat `kb.claim`'s object CHECK (store note §3).

**Failure behaviour.**
- A bad row aborts the whole transaction: COPY applies CHECKs and foreign keys, and its `ON_ERROR`
  options exist only for text formats (store note §3).
- `classify_error(exc)` separates retryable SQLSTATEs (40001, 40P01, a lost connection) from defects.
  A unique violation on `(task_id, ordinal)` is a fencing defect, not a retry.
- An extension at the wrong version fails 0001, `ci db init` and `open_store`, each with D3 §13's
  instruction.
- Key collisions are refused before any write, in `RenditionContent` validation.

**Negative store tests per invariant** (R12; coordinator decision 24; F01's store side). For every
D1 §11 invariant the store enforces, and for D3's stated cross-column rules, a test builds a
violating row by hand from the invariant's text. The set is the one `s6.constraints` established,
plus INV-03 and INV-08 as F-Q4 places them, the edge-table FKs and INV-10 in span upsert. It expects the refusal, whether a CHECK, an FK, a unique key or a repository
assertion refuses it. The test never reads its expectation from `_model`, the generated `MetaData` or
the overlay. That a CHECK lists exactly the model's set is derivation conformance, tested separately
and called so.

**Execution fit.** At D3 §11's volumes (about 10⁵ observations and 10⁴–10⁵ claims per run, a few
edge rows per claim, a few thousand segments per page set), the write paths are set-based:
- COPY for observations and materialized rows;
- one `unnest` statement per span batch;
- one segment statement per new rendition;
- row-by-row upserts only for the low-volume version tables.

Content-preserving re-ingest writes one build row per document and no segments. Validation is
Pydantic only in production. Tests clone a migrated template per session and roll back per test, so
only commit tests pay for a clone. The cost of same-run composite FK checks at this volume is
unmeasured. F-Q4 measures it before 0001 is generated, beside the `s6.volume` rerun on `18/corpus`.
Everything else here is a qualitative reading.

### 3.9 Infrastructure facts (F5)

R11's local fixes. Each names the one source of its fact.

- **DA-018, extension versions** ([DA-018](../../design_review/audit/boundaries-and-composition.md#da-018)).
  - **The record.** One record holds the expected `extversion` per extension: `pg_textsearch 1.5.1`
    and `vector 0.8.7`. It is a file under `ops/postgresql/` beside `corpus.conf`, read by the shell
    and through one Python loader.
  - **The hold row.** A `docs/pins.md` hold row is added with `pin-check`. Its reason: keys and BM25
    plans are read against these versions.
  - **Who reads it.** Provisioning reads it: `just db-provision` runs `ALTER EXTENSION … UPDATE TO`
    on `cs_template`. `just db-status` reports versions, labelled as such. F1's fixture check, 0001's
    assertion and `open_store` (F4) read it too.
  - **The template hash.** The template hash includes `cs_template`'s extension versions.
- **DA-019, template retention** ([DA-019](../../design_review/audit/boundaries-and-composition.md#da-019)).
  - **Retention.** The sweep retains templates by lease or age, no longer by "not current, so drop".
  - **Locks.** A clone or a build takes a shared session advisory lock keyed by the template name,
    which the sweep takes exclusively (`pg_try_advisory_lock`). The sweep skips any template whose
    lock it cannot take.
  - **Effect.** A parallel checkout's template therefore survives a sweep. The advisory lock replaces
    the checkout-local file lock for cross-checkout safety.
- **DA-020, one coordinate source** ([DA-020](../../design_review/audit/boundaries-and-composition.md#da-020)).
  - **The Python side** reads the cluster's coordinates through `Settings()`.
    - `tests/conftest.py`'s `server_url()` builds `Settings()`, which reads `CORPUS_DATABASE__URL`
      through its own environment source.
    - It derives the admin URL with `make_url(settings.database.sqlalchemy_url).set(database="postgres")`.
    - `LOCAL_CLUSTER_URL` and the direct `os.environ` read are deleted.
    - The stale "project-local cluster" docstring and the `PROVISION` message are corrected to the
      dedicated cluster `18/corpus` and `just db-provision` (D3 §13).
  - **The shell side** keeps reading `corpus.conf`.
  - **D3 §3's provisioning prose** gives way to D3 §13; that edit is P0-D-1's.
- **DA-022, Python manifests in the pin check** ([DA-022](../../design_review/audit/local-reasoning-and-assurance.md#da-022)).
  - `scripts/check_pins.py` (stdlib only) also checks every `pyproject.toml` in the workspace:
    project dependencies, dependency groups and optional dependencies, each pinned `==x.y.z`. A range
    fails `just deps`, so the stated `just deps` property holds.
  - Its tests are in `tests/scripts/`.
- **`p0q.settings-env`** (coordinator decision 26). The scratch check is recorded as an evidence
  record in `docs/design_review/evidence/2026-10-28_phase0-model-probes/`: validating a `BaseSettings`
  with `model_validate({})` reads the environment, under pydantic-settings 2.16.1.
- **IR-14, optional.** `canonical_decimal` bounds its exponent (a loader meeting `1e5000000` gets a
  refusal, not a huge string).

### 3.10 Probes (F-Q4, F-Q6)

Evidence goes in `docs/design_review/evidence/2026-10-28_phase0-model-probes/`, with record ids
`p0q.*` owned by this series (coordinator decision 10). The probes run in a scratch environment, and
neither changes product code.

- **P0-F-Q4** (Q-4; record `p0q.fk-cost`).
  - **What it measures.** It runs binary COPY at run scale on `18/corpus`: 10⁵ observations and
    2×10⁴ claims with a few edge rows each, the volumes of `s6.volume`. It runs twice: with the
    same-run composite FKs `(run_id, id)` and the per-version vocabulary FKs
    `(schema_version_id, value)`, and without them. The table shapes come from a scratch sketch over
    S6's DDL.
  - **The pairing.** It is paired with the `s6.volume` rerun on the dedicated cluster (D3 §11's
    pending rerun).
  - **What it decides.** It decides whether INV-03 and INV-08 are enforced by FK or by the bulk
    writer (M2, C1). ADR-0021's variants are named at P0-D-1, so the result selects a variant and
    does not reopen the decision.
  - **The dataset.** The volume dataset is kept: its generator and seed in the evidence folder, and
    a dump through Git LFS. C2 inspects its edge-join plans on the same data.
- **P0-F-Q6** (Q-6; record `p0q.key-carry-over`).
  - **The carry-over.** It computes the carry-over between scheme 1 and a synthetic scheme 2 (one
    changed canonical form, for example a slot's case policy) over the `fixtures/s0` and
    `fixtures/trace` authored inputs. The map must be complete: every key whose input exists is
    mapped, and every key whose input is missing is reported.
  - **Vector stability.** It checks that conformance vector v1 is stable across two processes with
    different `PYTHONHASHSEED`, and across a Pydantic patch bump in the scratch environment.
  - **What it settles.** It settles how an outgoing scheme stays callable (§3.6).

## 4. Ports

Spike modules are under `docs/design_review/evidence/2026-10-28_design-spikes/code/`. They are
rewritten against the contracts above, keeping their cases. The spike folder is never imported, and
the spike series keeps scoring with its frozen revision (coordinator decision 12).

| Spike module | Product module | Behaviour and cases kept | Known spike defects not ported |
|---|---|---|---|
| `instruments/batch.py` | `core/values.py`, `core/conditions.py`, `core/batch.py` | Discriminated value and condition unions, schema-owned names as strings, per-item validation, both item forms, error paths with the tag | The spike envelope; bare strings in formula and entity positions (`FormulaArg`, three `EntityArg` shapes); lists in frozen models; the anonymous condition union re-inlined at every site; one phrase model for both forms; `number` without `basis` |
| `instruments/conditions.py` (`canonical_json`, `canonical_condition`, `normalize_tree`) | `core/canonical.py`, `core/keys.py` | Flatten, collapse, drop empty, swap `>`/`>=`, sort `and`/`or` by canonical JSON, leaves by text | Floats accepted and no NFC-collision check in `canonical_json`; `pred` arguments sorted as if every predicate were symmetric; `trees_equivalent` (evaluation's, E2a) |
| `instruments/keys.py` | `core/keys.py` | `make_key`, the parts layout, topological keying with cycles dropped and their reason (now a code) | Statements keyed by sorted segment keys; local scopes by segment key; the label always in global keys; no `valid_time` or cited-source identity; no member or group keys; the meaning key (no consumer: `s6.keys` and `s6.restated` call for none in 0001); `mismatch_causes` (a spike diagnostic) |
| `instruments/values.py` (`text_norm`, `_dec_str`, `canonical_value`, `canonical_symbol`) | `core/values.py`, `core/keys.py` | The text form; the decimal rules (as the `number` pattern and the loader helper); `\mu` = `mu` | Units converted to pint base units (D1 §6.2 keeps them as stated); `FALLBACK_MACROS` in code (pack data, D2 §12.1); canonical LaTeX printed from the parse tree; the SymPy and numeric tiers and `PARSE_LOG` (E2a's); dispatch by `t` on dumps, which is replaced by typed dispatch and canonical form by range (F2c, F2d); casefolding every string |
| `mathgrammar/printer.py` (`tex_tokens`, `_expand`, `_read_arg`, `_tree`, `_simplify`, `_flatten`, `serialize`, `tokens_canonical`, `strip_delimiters`) | `core/tex.py` | Macro expansion by TeX's argument rules, single-token brace removal, the separator after a control word, delimiter stripping | The drop set read from the shipped grammar's string `%ignore` lines (it misses the sizing commands); `\cmd*` as one token; deleted text-mode whitespace; `tree_canonical`, `leaves` and `node_text` belong to I2a's grammar |
| `tests_instruments/test_values.py` `test_d1_rules`, `test_macros_page_over_fallback`, `test_numbers_and_text` | F2a and F2b tests | The D1 rule cases (`b^{2}`, `\left( x \right)`, `a + b \, Z`, `\mu x` against `\mux`, `\R \setminus \{0\}`), page macros over the fallback, `\abs{x}` with one argument | `1 cm` equal to `0.01 m` (now two keys); `2.50` normalized (now refused as non-canonical) |
| `results/s0r2/reference_model_v1/`, `inputs/packet_v1/units/`, `results/s0r2/sample.json`, `reference_v1/` | `fixtures/s0` | The 12 batches item for item, their standing-context citations, the stored offsets as the identity check | Spike unit ids as `unit_ref`; packet-relative sentence ids without a frame; T1 as one unit |

## 5. Packages

| Package | Scope | Prerequisites | Acceptance | Revealing failure case | Closes (coordinator §11) |
|---|---|---|---|---|---|
| P0-F-1 (built 2026-10-28) | Workspace member, settings, `ci` app and registration, `tests/conftest.py` with Hypothesis profiles, markers, the CLI runner and the database fixtures; `alembic/` scaffold | none; the database fixture's own check needs the operator's `cs_template` | `just check` passes with the package's first tests; `ci --help` lists the registered groups; settings resolve from `CORPUS_*` with `__`, and init beats the environment; a session clones and drops `ci_test_<pid>` | `ci --json status` (a root option) exits 2 while `ci status --json` works; two `Settings` built with different init values in one process do not leak into each other | — |
| P0-F-2a (built 2026-10-28) | `canonical_json` and hashing; evidence types, `RenditionContent`, `MacroDef`; `content_digest`; `doc`/`ren`/`seg`/`cfg` keys; `core/tex.py` | P0-F-1 | Canonical JSON and token-form properties (§6); digest invariance and sensitivity; `core/tex.py` frozen after `s5.keys-property` | `\big/` keeps its sizing command; `\text{ for all }` becomes `\text{forall}`; a float in a configuration silently hashes | — (its IR rows fixed 2026-10-28, coordinator §11) |
| P0-F-2b (built 2026-10-28) | D1 shapes in both forms, generic items and envelopes, citation frame with resolution and re-addressing, keyed candidate set, payload and operations JSON, the interim hand-written `vocab.py` (generated from M1 on), JSON Schema files; canonical forms, label normalization, every remaining key and batch keying | P0-I-0 (on P0-F-2a) | Key properties of D1 §10.1 (§6); round trips; generated schemas current and accepted by jsonschema (derivation conformance); the T3 claims of D3 §10 key deterministically | Two `valid_time` intervals on one claim key alike; `owns(A, B)` and `owns(B, A)` key alike for a predicate not declared symmetric; an edit inside one paragraph moves another block's statement key | — (its IR rows fixed 2026-10-28, coordinator §11) |
| P0-F-2c | Typed dispatch with `match` and `assert_never` over the value, condition and item unions; one condition visitor; citations by `SentenceId` type; typed codes for `core/keys.py`'s `KeyingError` (`DropReason`) and for `core/frame.py`'s `FrameFailure` (`FrameFailureReason`), with messages projected from them; keying preparation once per `KeyContext`, with `member_parts` reusing `claim_parts`; canonical JSON only on final key parts; the F02 relabel ("derivation conformance" in the `core/schemas` and `test_shapes.py` docstrings, each contract naming its independent controls) | P0-F-2b. **Ready now** | Exhaustive typed dispatch, with a test driving every union member through each dispatch; a pack qualifier named `sentence` passes frame resolution, re-addressing and keying; every drop and frame outcome carries a code, and no `str(error)` reason remains; annotation units and segment keys computed once per context (counted); the IR regression tests unchanged and passing | A schema qualifier `{"sentence": "s3"}` is rewritten as a citation by `readdress`; a malformed condition raises `ValueError` out of `key_claims` | DA-004, DA-013 (core), DA-025, F02 (wording) |
| P0-F-2d | Declared identity: the `KeySchema` type compiled from `QualifierSpec`s (core from `_model`, pack via S1); `key_role` and `key_role_when` read in `claim_parts`; canonical form by range (TM §8); `ci:case` in `text_form` and `normalize_label`; the key scheme from `_model` carried by every keyed output; `carry_over` (T8); the ordinal-shift limit test | P0-M-1, P0-F-2c | A map entry `{"ref": …}` under a string range and `"Shape-Rate"` canonicalized by range; `X`/`x` and `\Sigma`/`\sigma` key apart under `preserve` and alike under `fold`; attribution enters a key only under an `attribution_identifying` modality, with no literal `cited` in `keys.py`; keys, slots and conflicts read one compiled spec; the ordinal-shift test shows the stated limit; no key hashes the scheme; IR tests pass | A business modality given `attribution_identifying` in a test pack still keys attribution out, because the role is hard-coded | DA-001, DA-008, DA-009 (scheme), DA-014 (test) |
| P0-F-2e | Complete translations and typed references (R04's core half): the stored batch and keyed candidate set carry the rendition reference, alternatives, unsupported items, `establishment`, `derived_from` and `rule`, with typed unkeyed and awaiting states; entity, statement and claim reference types; per-kind resolver lookups with wrong-kind refusal by code; `ExternalReference` with the authored `outside` descriptor and its key; `EnumValue` per form; the derivation fields on the `claim_proposal` payload model in `core/payloads.py` (cascade version and schema version; DA-009; consumed by A0 and A1); the model-derived translation completeness harness; then **key scheme 1 frozen** with conformance vector v1 of hand-authored known answers | P0-F-2d, P0-M-1; the freeze after `s5.keys-property` | Translation completeness tests (each source slot mapped or declared omitted); the candidate set carries the whole batch; a wrong-kind reference refused with a code; an unresolved outside reference kept as a typed node; stored enums prefixed; vector v1 passes, and a seeded canonical-form change fails it | A `claim` condition naming a statement is keyed as a claim reference; an `outside` item disappears between the stored batch and the candidate set | DA-005, DA-006, DA-007 (core), DA-009 (derivation fields), X2-01 (consumer half) |
| P0-F-3 | `fixtures/s0` (13 files), `fixtures/trace` (5 segment files, 4 target files, the four vendored pages with their index entries and attribution), their README and support models | P0-F-2b; acceptance needs P0-I-1a, P0-I-2a, P0-A-0 | Frames resolve on production renditions; derived offsets equal `reference_v1`'s; `cN` entries are in the standing context; targets and fixtures agree by key equality with no unexplained difference | A frame entry whose recorded text differs from the production sentence (a rendering convention, a `[n]` marker) is refused rather than matched approximately; T1 submitted unsplit cannot be re-addressed to the `#dfn1` packet | — |
| P0-F-4 (revised) | Migration 0001 generated from M2's `MetaData` and overlay with M4's Alembic hooks; the extension-version assertion, reading F5's record `ops/postgresql/extensions.txt` through a product reader (moved from the conftest); `ci db`; the psycopg-pool 3.3.3 pin; the pool with the startup version check outside `configure`; the repository with `payload_schema_id` writes and reader dispatch; bulk primitives; INV-03 and INV-08 as F-Q4 places them; the negative store tests per invariant written from D1 §11; the catalog comparison | P0-M-2, P0-M-4, P0-F-2e, P0-F-5, P0-F-Q4; `s6.ddl`, `s6.constraints`, `s6.bm25` | Upgrade, downgrade, upgrade; the catalog comparison against the generated `MetaData` plus overlay; an unregistered revision refused; each negative store test refused as its invariant states; D3 §10's T3 rows insert and D3 §9's queries return them; the BM25 query uses the partial index; rendition deduplication and the `cut_at` cutoff in the views; an extension at the wrong version fails startup with the typed error, not a `PoolTimeout`; every payload-bearing row carries a registered `payload_schema_id`, and an unknown id is refused on read | A CHECK body or partial-index predicate changed under its old name passes `alembic check` and fails the catalog comparison; a second build of identical content writes segments; a version check placed in `configure` turns a mismatch into a timeout | DA-018 (assertion), F01 (store side), F04 (store share) |
| P0-F-5 | R11's local fixes: the DA-018 expected-`extversion` record, `ALTER EXTENSION … UPDATE` in provisioning, the template-hash input and the `docs/pins.md` hold row; DA-019 lease or age retention with advisory locks; DA-020 one coordinate source (`server_url()` through `Settings()`, `LOCAL_CLUSTER_URL` and the direct `os.environ` read deleted, the stale docstring fixed; the shell keeps `corpus.conf`); DA-022 Python manifests in `check_pins.py`; the `p0q.settings-env` record; IR-14 (optional) | P0-F-1. **Ready now** | A version mismatch fails provisioning's check and the fixtures; a template built under another extension version gets another name; a parallel checkout's template survives a sweep; one source per coordinate; a Python range fails `just deps`; record `p0q.settings-env` finalized | Changing the `DatabaseSettings` default moves the application but leaves the fixtures on `LOCAL_CLUSTER_URL`'s port; a sweep in one checkout drops the template another checkout is cloning | DA-018 (record), DA-019, DA-020 (code half), DA-022, IR-14 |
| P0-F-Q4 | Probe Q-4 (§3.10): COPY at run scale with and without same-run composite FKs and per-version vocabulary FKs on `18/corpus`, paired with the `s6.volume` rerun; the volume dataset kept for C2 | none. **Ready now** | Record `p0q.fk-cost` finalized; FK or bulk-writer enforcement chosen | — | Q-4 |
| P0-F-Q6 | Probe Q-6 (§3.10): carry-over between scheme 1 and a synthetic scheme 2 over the fixtures; vector stability across processes and a Pydantic patch bump | P0-F-2e, P0-F-3's files | Record `p0q.key-carry-over` finalized; carry-over complete; vectors stable | — | Q-6 |

**P0-F-1** (built).
- **Mechanisms.**
  - pydantic-settings with nested models and init and environment sources only.
  - Typer `add_typer`, a root callback, a per-command `--json` alias and `CliRunner` (interfaces note
    §3–§4).
  - `CREATE DATABASE … TEMPLATE` with a migrated template keyed by the versions directory's hash,
    `DROP DATABASE … WITH (FORCE)` and rolled-back outer transactions (store note §1).
- **Evidence:** none.

**P0-F-2a** (built).
- **Mechanisms.** The `regex` module for the TeX tokenizer (D1 §6.2); `json` with sorted keys over an
  NFC pre-walk; Pydantic frozen models for the evidence types.
- **Evidence.** `s5.keys-property` freezes `core/tex.py`, and `s5.macros` checks the expansion rules
  on the corpus's tables. Nothing that stores keys runs before the freeze except tests.

**P0-F-2b** (built).
- **Mechanisms** (schema-rules note §1, Tested there):
  - `TypeAliasType` for the recursive `Condition`, and `Field(discriminator=…)`;
  - `Field(exclude_if=…)` defaults, and `MISSING` where absent and null differ;
  - `strict=True` for authored batches on the JSON path;
  - `Field(pattern=…)` for canonical numbers, dates and sentence ids;
  - a custom `GenerateJsonSchema`;
  - Hypothesis `st.builds` and `st.from_type`, with `st.from_regex` registered for patterned fields
    (interfaces note §6.1, Tested there).
- **Settings.** Operations models (run options, method `params`, the operations JSON) stay frozen
  `BaseModel`, never `BaseSettings` (coordinator decision 26; §3.5).
- **Evidence.** `s4.batch-validation`, which found no core shape that the v1 batches or the worked
  examples need differently.

**P0-F-2c.**
- **Mechanisms** (R03):
  - Python 3.14 `match` over Pydantic discriminated unions;
  - `typing.assert_never`, checked by pyrefly;
  - `typing.get_args` to enumerate union members in the exhaustiveness test;
  - an `Annotated` `SentenceId` type with `Field(pattern=…)`, found among `model_fields` by its
    annotation;
  - `StrEnum` codes;
  - `functools.cached_property` on `KeyContext` for the prepared annotation units and segment keys.
- **Layering.** It works on the built files that M1 then touches (coordinator §7).
- **Evidence:** none.

**P0-F-2d.**
- **Mechanisms.** M1's generated `QualifierSpec`s and member-property frozensets (role conditions read
  as `modality in ATTRIBUTION_IDENTIFYING`), dispatch by declared range through F2c's `match`, and
  `unicodedata.normalize("NFC", …)` with case per policy (R02, TM §8).
- **Evidence:** the IR rulings in D1 §6.2 and §10.1.
- **ADR.** ADR-0023 is accepted at P0-D-1.

**P0-F-2e.**
- **Mechanisms.**
  - `MISSING` and typed sentinel states;
  - per-form `EnumValue` variants in the form factory;
  - a completeness harness that enumerates the source class's fields (from `model_fields` now, from
    the model after M5) against a declared mapping;
  - conformance vectors as committed JSON with hand-written expected parts, checked with `hashlib`
    directly.
- **Evidence.** `s5.keys-property` (the freeze); `s4.batch-validation` (the S4 side table caught 13
  of 13 seeded reference errors, which establishes the check S2 owns).

**P0-F-3.**
- **Mechanisms.** F2b's models and frame functions, I0's generator and resolver, and A0's cascade.
- **Evidence.** None from the spike records; the reference data are the S0-R2 results named in §4.

**P0-F-4.**
- **Mechanisms.**
  - Alembic 1.20 autogenerate once over the generated `MetaData`, with the CHECK-by-name plugin and
    M4's `template_args`, `process_revision_directives` and `on_version_apply` hooks, plus a catalog
    comparison;
  - psycopg-pool 3.3.3 (`open=False`, `open()`, `wait(timeout)`, `configure` limited to JSON
    adapters, `check_connection`) lent to SQLAlchemy through `creator` and `NullPool`, with the
    version check as an ordinary query after `wait`;
  - binary COPY with `Copy.set_types`;
  - `unnest` with `ON CONFLICT DO NOTHING`;
  - `on_conflict_do_update(…).returning()` with PostgreSQL 18's `old`;
  - ids pre-allocated with `nextval` (D3 §1, store note §1–§5).
- **Evidence.**
  - `s6.ddl`, through M2's port check, and `s6.constraints`, which established which constraints
    fire and which invariants stay in the repository;
  - `s6.bm25` and `s6.queries` (index syntax and plans), and `s6.dry-run` (compiled schema rows
    against the tables);
  - `s6.volume` and `s6.sizes`, with `p0q.fk-cost` from F-Q4;
  - `s6.keys` and `s6.restated`, which found that no meaning-key column is needed in 0001.

**P0-F-5.**
- **Mechanisms.**
  - `pg_extension` and `ALTER EXTENSION … UPDATE TO`;
  - `pg_advisory_lock_shared` and `pg_try_advisory_lock` on session connections;
  - SQLAlchemy `make_url(...).set(database="postgres")`;
  - stdlib `tomllib` in `check_pins.py`.
- **Evidence.** `p0q.settings-env`, written here.

**P0-F-Q4 and P0-F-Q6.** Their mechanisms and evidence are in §3.10.

## 6. Tests

| Package | What the tests establish |
|---|---|
| P0-F-1 | The settings contract: prefix, nesting, sources, init over environment, and the report of unknown names. The CLI contract: groups registered, `--json` per command, stdout and stderr apart, no settings built for `--help`. The database fixtures clone, isolate (a rolled-back write is invisible to the next test), sweep and drop |
| P0-F-2a | **Canonical JSON:** equal output under permuted object keys and NFD input (`key(x) == key(nfd(x))`); refusal of floats, `Decimal`, dates, bytes, lone surrogates and NFC-colliding keys; the decimal helpers on generated decimal strings (idempotent, canonical by pattern). **Digest:** equal for two `RenditionContent` values built in different child orders; different after any one change to text, an offset, a kind, a parse status or reason, an attribute or a macro body. **Token form:** the metamorphic properties of §3.4 under Hypothesis, the D1 rule cases ported from the spike, and macro cases (whole names, arguments, optional defaults, the depth bound); tex parity 918/918 as the independent control |
| P0-F-2b | **Models:** round trips of every model drawn by `st.builds`/`st.from_type`; per-form refusals (offsets in an authored batch, `sympy` in a batch, a non-canonical number). **Keys, on synthetic segment trees with I0's generator:** <br>• two contents with identical content and different builds give identical claim keys; <br>• an edit inside one paragraph that leaves every block's opening words unchanged leaves every other statement key unchanged; <br>• permuted `and` arguments and present-or-absent defaults give equal keys; <br>• two `valid_time` intervals, two cited sources, and `pred` arguments of a non-symmetric predicate in two orders give different keys; <br>• an attribution outside `cited` does not move a key; <br>• candidates differing only in bindings get distinct member keys; <br>• a condition cycle is dropped with its reason. <br>**Labels:** label normalization on the D5 §3.3 cases ("the normal distribution", "normally distributed") with test-local rules. **JSON Schemas:** the files are current, pass `check_schema` and accept the dumped instances, which is derivation conformance and not an independent oracle |
| P0-F-2c | Exhaustiveness: every member of each typed union driven through each dispatch, and `assert_never` reachable only for an unrepresentable member. A pack qualifier named `sentence` passes frame resolution, re-addressing and keying unchanged. One visitor serves `claim_refs`, canonical conditions and binding collection, and a seeded unknown operator is refused at validation. Every `DropReason` and `FrameFailureReason` member has a case that produces it. Preparation counted once per `KeyContext`. The IR regression tests unchanged |
| P0-F-2d | The TM §8 range table, one case per row, written from TM §8's text. The DA-001 cases (`{"ref": "Smith"}` under a string range; `"Shape-Rate"`) and the DA-008 cases (`X`/`x`, `\Sigma`/`\sigma` under `preserve` and `fold`). Attribution under a test-pack modality given `attribution_identifying`. The ordinal shift (§3.6). `carry_over` on a hand-built two-scheme pair, reporting missing inputs. No key value changes when only the recorded scheme number changes |
| P0-F-2e | Translation completeness from the model's slot lists (each mapped or declared omitted). Typed references: a wrong-kind reference refused with its code; the subject typed "entity or statement". `ExternalReference`: authored descriptor to stored span to key; unresolved kept. `EnumValue`: authored local and stored prefixed, each refused in the other form. Derivation fields present on `claim_proposal`. **Conformance vector v1:** each entry's key equals `hashlib` over its hand-written parts; a seeded change to one canonical form fails the vector |
| P0-F-3 | The fixture acceptance of §3.7, gated on its prerequisites: frames resolve; offsets equal `reference_v1`'s; standing-context entries are present; both `Z` declarations of T1 key alike; targets and fixtures agree by key equality; no fixture claim matches a `must_not` pattern. With the corpus present, the vendored pages' bytes match the corpus manifest |
| P0-F-4 | **Migration:** upgrade, downgrade to base (the four schemas gone, the extensions kept), and upgrade again; the catalog after `upgrade head` equals the generated `MetaData`'s `create_all` plus the overlay; `alembic check` clean; an unregistered revision refused by the hook. **Negative store tests:** one per enforced invariant and cross-column rule, written from D1 §11 and D3 (independent). Separately, every digest-named CHECK refuses a value outside its model set (derivation conformance). **Queries and indexes:** D3 §10's T3 rows, built from `fixtures/trace` segments and hand-made entities, claims and edge rows, insert, and D3 §9's queries return them; the BM25 query plan names `segment_bm25`. **Repository:** `store_rendition` twice with identical content writes one rendition and its segments once, and two builds for two configurations; span upsert returns the same ids on repeat and refuses an out-of-text range; an observation COPY inside a transaction whose fencing update found no row commits nothing; every payload row carries a registered `payload_schema_id`, and reading an unknown id is refused. **Views:** the run views ignore a task finished after `cut_at`; `kb.run_rendition` selects the rendition the run's ingest configuration built. **Startup:** an extension version mismatch raises `ExtensionVersionMismatch` from `open_store` |
| P0-F-5 | **Versions:** a seeded version mismatch fails the fixture check, and the template name changes with the extension versions. **Sweep:** a template held under the shared advisory lock by another connection survives a sweep, and an aged unheld one is dropped. **Coordinates:** `server_url()` follows `CORPUS_DATABASE__URL` through `Settings()`, and no test module reads the environment for coordinates. **Pin check:** a `>=` range in a `pyproject.toml` fails `check_pins.py` (`tests/scripts/`). **Optional:** `canonical_decimal("1e5000000")` refused (IR-14) |

Shared fixtures used: the `db` and `committing_db` fixtures and the Hypothesis profiles (F1), and the
`fixtures/trace` segments (F3) in F4's row test. Tests that need the corpus are marked `corpus`.

**Independent controls, by contract** (coordinator decision 24; R12):

| Contract | Control |
|---|---|
| Keys | The hand-authored conformance vectors (F2e); the relational key oracles of the key tests (differences required by D1 §10.1's text) |
| Token form | Tex parity |
| Shapes | The external S0 and S0-R2 batches |
| Store | The negative store tests (F4) |

Generated-against-generated agreement is labelled derivation conformance wherever it appears.

## 7. Indicative size

The coordinator's budget for foundations is 2,300 product lines, tests excluded (§8). The built
packages were counted on 2026-10-28 as code lines: an AST and token count excluding blank lines,
comments and docstrings. Counted that way they already hold about 1,800 of those lines.
- **What moved out.** The table metadata (about 450 lines) moved to model and projections. The
  hand-written `vocab.py` (about 210 counted lines) becomes generated, and is excluded.
- **What was added.** F2c–F2e and F5 add the rest.

| Package | Indicative lines | Bulk |
|---|---|---|
| P0-F-1 | 210 (built) | settings, the app and registration, the `alembic/` scaffold |
| P0-F-2a | 550 (built) | `core/tex.py` (about 330), canonical JSON, evidence types and the digest |
| P0-F-2b | 1,250 (built, `vocab.py` excluded) | values, conditions and items in both forms (about 450), payload and operations models (about 180), keys and canonical forms (about 490), frame, candidate set and labels |
| P0-F-2c | about 0 net | one visitor replaces three walks; codes and dispatch arms add about as much |
| P0-F-2d | 100 | `KeySchema`, range dispatch, case policy, carry-over |
| P0-F-2e | 150 | reference types, `ExternalReference`, candidate-set fields, the completeness harness |
| P0-F-3 | data | fixtures and vectors are JSON; the support models are test code |
| P0-F-4 | 400 | the repository (about 300), `ci db`, the pool and its version check |
| P0-F-5 | 30 | the extension-record loader; the rest is test configuration and a process script |
| **Total** | about 2,700 | against the coordinator's 2,300 |

Migration 0001, `core/_model/`, `core/vocab.py`, `core/db/_tables.py` and `core/schemas/*.json` are
generated, and are outside the count. The overrun over the coordinator's figure comes from the built
packages being larger than their first estimates, not from the reworks. It is for the end-of-phase
review (coordinator §8, §12).

## 8. Choices left to implementation

- Module boundaries inside `core/` beyond those named, and file names for fixtures (each file holds
  its unit key).
- Whether segments of a new rendition go in by one `unnest` statement or by binary COPY. Binary COPY
  would need a dumper for `regconfig`, which psycopg may not provide by default (an inference to
  confirm at F4). `unnest` with a cast is therefore the expected route.
- Pool sizes per process within the store note's table, and the Hypothesis example counts.
- How the one-time fixture conversion is scripted, as long as its output is reviewed and committed.
- Where the conformance vectors live (`fixtures/keys/` is the default) and their file layout.
- The `ExternalReference` key's prefix, within D1 §10.1's prefix list as P0-D-1 amends it.
- The expected-extension record's file format, and the template retention age.
- Whether the outgoing scheme's key functions are kept as a frozen module or the carry-over map is
  computed by the outgoing release (F-Q6 decides).
