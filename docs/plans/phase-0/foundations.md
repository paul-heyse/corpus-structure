# Phase 0 foundations: package, core types and keys, fixtures, store

**Status:** Proposed (2026-10-28). Part of the [phase 0 series](../phase-0_2026-10-28.md),
which owns shared decisions, contracts, the dependency graph and build findings.

Baseline: commit `5feec8b` with the design and coordinator amendments of 2026-10-28 that reconcile
the seven phase 0 contract sheets (being applied to D0–D9 while this was written, so design
sections are cited by name); nothing is built. Packages P0-F-1, P0-F-2a,
P0-F-2b, P0-F-3 and P0-F-4 correspond to F1, F2a, F2b, F3 and F4 of the coordinator's graph (§7).
Every design claim here is **Proposed** unless it carries another label.

## 1. What this document builds

Foundations builds what every other phase 0 document stands on (D9 §5, P0.1–P0.3):

- **the package and its entry point** (F1): the `corpus-structure` workspace member, settings, the
  `ci` Typer app with its group registration, the shared test configuration and the database
  fixtures;
- **the representation** (F2a, F2b): canonical JSON, the evidence types and the rendition content
  digest, `core/tex.py` (the TeX tokenizer and token form), the D1 shapes in both batch forms, the
  citation frame, the keyed candidate set, the observation and operations JSON models, label
  normalization, canonical forms and every D1 key;
- **the fixtures** (F3): `fixtures/s0`, the v1 reference as authored batches with citation frames,
  and `fixtures/trace`, the trace targets hand-authored from `trace.md`, with the original bytes of
  the four spike pages the fixtures use, so tests on them never depend on the gitignored corpus;
- **the store** (F4): SQLAlchemy Core metadata for every table of migration 0001, the frozen
  migration, `ci db`, one connection pool per process, and the repository: get-or-create, the
  evidence writer, the observation writer, span upsert and the bulk primitives other writers use.

**Where it ends.** Foundations defines shapes and the functions that are total over them; it makes
no decision that needs the pack, a parse or the pipeline's state.

- Locators (grammar, generator, resolver, refusal) are ingest and math's (I0), a core-level
  function over F2a's segment types; foundations calls them.
- The `ClaimProposalBatch` envelope contract is D2 §7.3's; schema and rules (S1) compiles its
  per-predicate branches over F2b's generic shapes, and `validate` (S2) owns the adapter from a
  submitted batch to the keyed candidate set and the batch checks.
- The quote cascade that derives a stored batch from an authored one is agent interface's (A0).
- Which candidates fuse, which become alternatives and which segment is a statement's or scope's
  in a run are consolidation's (C1); foundations computes the keys of what C1 decides.
- Building renditions is ingest's (I1a); foundations stores them. Tasks, leases, fencing and the
  agent completion primitive are orchestration's (O1); the observation writer runs inside O1's
  transaction. Compiled artifacts are written by `schema.registry` (S1b) through F4's metadata.

**Change scenarios** that explain the boundaries (DESIGN §1.3 and the phase 1 additions):

| Change | Where it lands | What foundations must already allow |
|---|---|---|
| A content-preserving ingest change (an M01 port, a spaCy bump, a profile fix that changes no output) | ingest | The content digest covers only content, and segments carry no diagnostics (D1 §3.2), so the rendition, its segments and every key stay; F4 records one more build |
| A table cell "High flow · 300 kPa(g)" | M01 tables, M12 (phase 1) | `number` with `unit` and `basis` kept as written in keys (D1 §6.2); table kinds already in the segment-kind list and the 0001 CHECK |
| "ORG-101 owns P-17, valid 2026-01-01 to 2026-06-30, per ownership.html" | a second pack | `valid_time` (an interval of ISO 8601 dates, kept verbatim) and the cited source are identity qualifiers, so two intervals key apart (D1 §10.1) |
| An email thread | a second source profile | The email segment kinds are in the kind list and the CHECK from 0001, so no migration |
| A second domain pack | `domains/<name>`, `sources/<name>.yaml` | Key functions take schema facts (identity keys, identity qualifiers, symmetric predicates) and label rules as data; `core` names no domain word |
| A rule with `or`/`not` conditions | the pack's `rules.yaml` | The condition tree and its canonical form already hold `or` and `not` (D1 §7) |
| The grammar extended by S5-B (phase 1) | ingest and math | Keys use the token form, which reads no grammar (ADR-0012); a change to `core/tex.py` after its freeze is a key migration and needs a design decision |
| Embeddings (phase 1) | M04, a new migration | Segment rows survive content-preserving re-ingest, so `kb.embedding` rows can reference them; 0001 does not create the table |

## 2. Contracts

### 2.1 Consumed

| Contract | Owner (design · this series) | Used by |
|---|---|---|
| Locators: string and structured forms, the generator, the resolver and its refusal; the annotation unit | D1 §3.4; ADR-0019 · [ingest and math](ingest-and-math.md) P0-I-0 | F2b (statement and local-entity keys, frame resolution), F3 (frames), F4 tests |
| The batch envelope and per-predicate branches; the `KeySchema` facts (identity keys per class, identity qualifiers per predicate, symmetric condition predicates, prefixed predicate names) from the compiled schema | D2 §3, §5, §7.1, §7.3 · [schema and rules](schema-and-rules.md) P0-S-1 | F2b keys take these as arguments; F4's writer receives schema-dependent payloads already validated by S1's adapters |
| The quote cascade (authored batch and frame to stored form on a rendition) | D4 §4.3 · [agent interface](agent-interface.md) P0-A-0 | F3 acceptance |
| Production renditions and the standing-context function | D1 §3, D4 M01–M03, §4.1 · ingest and math P0-I-1a, P0-I-2a | F3 acceptance |
| Label rules (articles, head words, rewrites) | D1 §10.1, D5 §3.3 point 5; the `aliases:` section of the pack's `methods.yaml` (D2 §12.1) · data loaded by the method registry (orchestration O1) | F2b label normalization |
| Fates as of `ops.run.finished_at`; the run's resolved scope; policy actions by `<method>/<name>` | D3 §4, §6.3, §8, D6 §7.1, §8 · [orchestration](orchestration.md) | F4 views and JSON models |
| Spike evidence | S6 records `s6.ddl`, `s6.constraints`, `s6.queries`, `s6.bm25`, `s6.dry-run`, `s6.volume`, `s6.sizes`, `s6.keys`, `s6.restated`; S5 records `s5.keys-property`, `s5.macros`; S4 record `s4.batch-validation` | F4; F2a's freeze; F2b |
| The dedicated PostgreSQL 18 cluster `18/corpus` (`just db-provision`; pg_textsearch preloaded; `cs_template`) | D3 §3 · coordinator §2 | F1's database fixtures, F4 |

### 2.2 Produced

| Contract | Design owner | What this document implements | Consumers |
|---|---|---|---|
| Settings and the `ci` app | D9 §3, D8 §4 | `Settings`, built once per entry point; the Typer app, group registration, the `--json` option and result emission | every document's `ci` group; the MCP lifespan (A1); the orchestrator (O1) |
| Shared tests | D9 §4 | `tests/conftest.py`: Hypothesis profiles, markers, the CLI runner, the per-session test database and its isolation fixtures | every package's tests; other owners add thin fixtures over them (trace slice, compiled schema) |
| Canonical JSON and hashing | D1 §10.1 | `canonical_json`, `digest`, `make_key`, the canonical-decimal helpers for loaders | S1 (schema hash), O1 (configuration hashes, input digests, `corpus_hash`), I1a, A1, E |
| Evidence types and the content digest | D1 §3.1–§3.3, §10.1; ADR-0019 | `Segment`, the segment-kind list, `RenditionContent`, `MacroDef`, `content_digest`; `doc`, `ren`, `seg`, `cfg` keys | I0, I1a, I1b, F4, O1 |
| The token form and the effective macro table | D1 §6.2; ADR-0012; coordinator decision 13 | `core/tex.py`: tokenizer, drop list, text-mode commands, the effective macro table (a rendition's table over the pack's fallback map), expansion, `token_form`, token lookup by position | I1a (macro reader), I2a (the grammar's macro classification, generated `%ignore`, its build check, error tokens, the tree/token property test), A0 (the cascade's macro step), S2 (submission views), F2b |
| D1 shapes in both batch forms | D1 §5–§7, §10.3; D2 §6, §7.3; D3 §6 | Values, conditions, bindings, core qualifiers, generic batch items and envelopes, the citation frame with resolution and re-addressing, the keyed candidate set, observation payload and operations JSON models, the closed value sets, `core/schemas/*.json` | S1, S2, A0, A1, A2, C1, C2, E1, E2a, O0, O1 |
| Canonical forms and keys | D1 §6.2, §7, §10.1; D5 §5.2–§5.3 | Canonical value, condition, binding and symbol forms; label normalization; `ent`, `stm`, `clm`, member, `alt` and `idg` keys; keying a batch in condition-reference order | C1, E2a (canonical forms for the numeric-tier seed), O1 |
| Fixtures | D9 §1, §4; D1 §10.3 | `fixtures/s0` (13 authored batches with frames), `fixtures/trace` (segments, targets, exclusions, question expectations, and the vendored original bytes of the four spike pages) | S1, A0, A1, C1, C3, E3 (the v1 witness), I1a |
| Store | D3 (all of 0001); ADR-0016 | Metadata, migration 0001, `ci db init`/`migrate`, the pool, the repository (only writer of evidence and observation rows; span upsert), bulk primitives | every writer and reader |

## 3. Design of the parts

### 3.1 The package and its entry point (F1)

**Layout** follows D9 §1: `python/corpus-structure/` is a uv workspace member with
`src/corpus_structure/` and `tests/`, and `alembic/` beside them. The root `pyproject.toml` adds the
member to `[tool.uv.workspace]` and `[tool.uv.sources]`, the package's tests to pytest's
`testpaths`, `python/corpus-structure/src` to ruff's `src` and pyrefly's includes. The existing
root `tests/conftest.py` for the process scripts stays as it is. Dependencies are added only by the
package that first uses them, pinned exactly at the versions D9 §2 names (`pin-check` for any
move): pydantic, pydantic-settings, typer and rich in F1; regex in F2a; sqlalchemy, psycopg,
psycopg-pool and alembic in F1 for the database fixtures; jsonschema in the dev group with F2b.

**Settings** follow D9 §3 and the [interfaces note](../../design_review/evidence/2026-10-28_library-interfaces-eval/README.md)
§4 (Tested there): one `Settings(BaseSettings)` with nested plain models (`database`, `paths`,
`llm`, `gpu`), `env_prefix="CORPUS_"`, `env_nested_delimiter="__"`, only init and environment
sources, frozen and `extra="forbid"`. The database setting is one libpq URL (local peer
authentication, no password in settings) plus the template name (`cs_template`); the SQLAlchemy
form is derived in code. Settings are built once at the entry point and passed down; no module
reads the environment. `extra="forbid"` cannot see a mistyped variable (Tested in the note), so
F1 provides `settings_report(settings)`, a result model listing what was resolved (secrets masked)
and any unknown `CORPUS_*` name; `ci status` (orchestration) prints it.

**The CLI** follows D8 §4 and the interfaces note §3 (Tested there): `cli/app.py` holds
`Typer(no_args_is_help=True)` and a root callback that stores a settings factory in `ctx.obj`, so
`ci --help` and completion never build settings or touch the database. Groups are registered from
one tuple in `cli/__init__.py`; each owning document adds its module (`cli/db.py`, `cli/schema.py`,
…) and one entry. A shared `JsonOpt` alias makes `--json` a per-command option, and one
`emit(result, json=…)` helper writes `model_dump_json()` to stdout or renders with Rich, with
diagnostics on a stderr console. Typer and Rich are imported only under `cli/`. The console script
is `ci`; inside `uv run` it shadows GNU RCS's `ci`.

**Shared tests** (`python/corpus-structure/tests/conftest.py`, coordinator decision 10; D9 §4):

- Hypothesis profiles `ci` (`deadline=None`, `derandomize=True`, `database=None`,
  `print_blob=True`, 300 examples) and `dev`, chosen by `HYPOTHESIS_PROFILE` (interfaces note
  §6.1, Tested there);
- markers `db`, `gpu` and `corpus`; `corpus` tests (the 78-page counts, for example) skip when
  `docs/statistics_corpus/` is absent (D9 §4); tests on the trace and spike pages read the vendored
  pages of `fixtures/trace` (§3.7) and never skip; nothing else skips silently;
- a `cli` fixture: Typer's `CliRunner` with stdout and stderr apart and the width fixed;
- **database fixtures** ([store note](../../design_review/evidence/2026-10-28_library-store/README.md)
  §1, Interface-checked there): a migrated template
  `cs_tpl_<hash of the Alembic versions directory>` cloned from `cs_template` once per migration
  state, built under a file lock with every engine disposed (a template must have no other
  connection while it is cloned); a session database `ci_test_<pid>` cloned from it on an
  autocommit connection to `postgres`, dropped `WITH (FORCE)` at teardown; a sweep at session
  start of `ci_test_%` databases whose process is gone and of templates for old hashes, touching
  only these two prefixes (the cluster holds other projects' templates); a `db` fixture that hands
  a SQLAlchemy connection inside an outer transaction rolled back after the test; and a
  `committing_db` fixture with its own clone for tests that need commits (the queue, `NOTIFY`,
  COPY followed by commit). When `cs_template` or the extension is missing, `db` tests fail with
  D3 §3's provisioning instruction; they are never skipped, so a missing prerequisite cannot pass
  as success.

F1 also creates `alembic/` with `env.py` set as the store note §1 says (schemas included and
filtered to the four, views excluded from comparison, server defaults compared, the CHECK-by-name
plugin, one transaction per migration, `alembic_version` in `public`, the connection shared through
`config.attributes` for tests) and an empty versions directory; F4 adds 0001.

### 3.2 Canonical JSON and hashing (F2a)

`canonical_json(obj) -> bytes` implements D1 §10.1 exactly. A pre-walk builds the normalized value
and refuses, with the path of the offending part, anything outside JSON's integers, strings,
booleans, null, arrays and string-keyed objects: a `float`, a `Decimal`, a date, bytes, a set, a
non-string key, a string that is not valid UTF-8 (a lone surrogate), and two keys of one object that
are equal after NFC. It then serializes with sorted keys (Python's code-point order over NFC
strings), no insignificant whitespace, `ensure_ascii=False`, `allow_nan=False`, encoded as UTF-8.
`digest(obj)` is the full SHA-256 hex; `make_key(prefix, parts)` is `prefix:` plus its first 32
hex digits.

Floats never reach a hash. Two helpers serve the loaders that meet them (YAML pack files, method
configurations, policies): `decimal_of_float(x)` gives the canonical decimal string of the shortest
round-trip form (`repr`), refusing NaN and infinities, and `canonical_decimal(s)` turns a decimal
literal into the D1 §6.2 canonical string. The loaders are orchestration's and schema and rules';
the rule (refuse in the hash, convert explicitly in the loader) is D1 §10.1's.

Alternatives: RFC 8785 would differ in key order (UTF-16) and number form, and D1 §10.1 has chosen
Python's order, so it is not used.

### 3.3 Evidence types and the content digest (F2a)

`core/evidence.py` holds the in-memory D1 evidence shapes, the types I0's locator function reads and
I1a produces:

- `SegmentKind`, the D1 §3.2 kinds, email kinds included; the 0001 CHECK on `kb.segment.kind` is
  built from it. The short locator forms `u` and `p` are I0's grammar, not kinds.
- `Segment`: `kind`, `start`, `end`, `parse_status` (`ok`, `partial`, `failed`), `parse_reason`
  (the D1 §3.1 reason of a `partial` or `failed` segment, null otherwise), `attrs` (author markup
  only; D1 §3.2 forbids diagnostics there) and `children`. Text is not stored on the node; it is the
  canonical text's substring. Children are ordered by start, then the longer first, then kind, and
  the model sorts them on validation, because siblings may overlap (a paragraph's `sentence` and
  `math_inline` children) and the digest needs one order.
- `MacroDef`: `nargs`, optional `default` (an optional first argument), `body`; the rendition's
  macro table maps names to it (D4 M01).
- `RenditionContent`: `canonical_text`, the `document` root and the macro table. Validation
  refuses a segment outside its parent or the text, `start > end`, and two segments with the same
  kind and offsets, because they would share a segment key. `parse_status` of the rendition is a
  derived property, the worst of its segments'.

`content_digest(content)` is the SHA-256 of the canonical JSON of the model dumped in JSON mode: the
canonical text, the whole segment tree and the macro table (D1 §3.2). Segments carry no diagnostic
attributes, so there is no exclusion list; the search configuration (`ts_config`, from the source
profile's `language`) is not part of the model and so outside the digest (D3 §5). The keys of this
package are `document_key(project_name, source_uri, content_hash)` (the project's name, never its
database id, D1 §10.1), `rendition_key(document_key, content_digest)`,
`segment_key(rendition_key, kind, start, end)` and `config_key(method, version, params)`.

**Where the partial reason lives.** D3 has no column for it, so the writer stores `parse_reason`
under the reserved `attrs` key `parse_reason`, outside the author-markup names. The alternative, a
`kb.segment.parse_reason` column, is cleaner for SQL; if S6 or the D3 owner prefers it, only F4's
mapping changes, not the content model.

### 3.4 `core/tex.py` (F2a)

The module implements the token form of D1 §6.2 and ADR-0012 and is the only TeX reader below the
grammar ([text-math note](../../design_review/evidence/2026-10-28_library-text-math/README.md)
§2.3, §3.3):

- **Tokens.** `tokens(latex)` gives TeX's tokens with their positions: a control word is `\`
  followed by letters, never a `*`; a control symbol is `\` and one other character; `{`, `}` and
  `#n` are their own kinds; a whitespace run is one token; anything else is one character. `%` is
  an ordinary character (the corpus has none in math, text-math note §2.3; comment handling would be
  a source-profile matter). `token_at(latex, pos)` returns the token containing a position, which
  I2a uses to name a grammar error.
- **One drop list**, `DROP`: every `%ignore` literal of SymPy 1.14's `latex.lark` and the sizing
  commands `\big`, `\Big`, `\bigg`, `\Bigg` with their `l`, `r` and `m` forms, as D1 §6.2 lists
  them (the drop list's contents Interface-checked against the installed grammar's lines 1–11 on
  2026-10-28). I2a generates the grammar's added `%ignore` lines from it and fails its build when an
  `%ignore` terminal of the assembled grammar is not on it.
- **Text-mode commands**, `TEXT_MODE`: `\text`, `\mathrm`, `\textrm`, `\mbox`, `\operatorname`.
  Inside their arguments a whitespace run becomes one space instead of being removed.
- **Macros.** `effective_macros(rendition_table, pack_map)` is the one effective macro table: the
  rendition's table over the pack's fallback map (D1 §6.2, D2 §12.1: the pack's map only for names
  the page does not define). The grammar (I2a), the token form and the quote cascade's macro step
  (A0) all take it from this function, so no consumer merges on its own. `expand(tokens,
  table)` replaces control words by whole name, reads arguments as TeX does (a group or one token,
  spaces skipped, an optional `[…]` first argument with its default), and stops at a fixed depth;
  a token left unexpanded at the bound is kept and reported, never dropped.
- **The form.** `token_form(latex, table)` strips one outer pair of math delimiters (`\(…\)`,
  `\[…\]`, an environment's `\begin`/`\end`; not `$`, which Siegrist uses as prose; D1 §6.2), expands macros, removes whitespace and every drop-list token outside
  text-mode arguments (inside them, drop-list tokens are removed and whitespace collapses), drops
  braces around a single token (`b^{2}` is `b^2`), and serializes with one space after a control
  word that is followed by a letter, so `\mu x` stays apart from `\mux`. With unbalanced braces it
  skips the brace step and stays total.

**Properties** (D1 §6.2's metamorphic layer, F2a's tests): the form is total (it never raises on any
string) and idempotent; it is unchanged by inserting `\,`, `\;`, `\!`, sizing commands, braces
around a single token, or whitespace between tokens outside text mode; it never merges `\P` with
`\Phi`, `\mu x` with `\mux`, or `x \leftarrow y` with `xarrowy` (whole names in the tokenizer);
`\text{ for all }` keeps its spaces; `\cmd*` is two tokens. The corpus layer (tree printer against
token form on every span) belongs to I2a, because it needs the grammar.

**Freeze.** The module is written now against these rules and frozen once S5's
`s5.keys-property` record is final; `s5.macros` checks the expansion rules on the corpus' macro
tables (coordinator §7). Before the freeze a change needs only the module's tests; after it, any
change that alters an output is a key migration and goes through the design owner.

Two rules here are implementation choices the design does not state and that move keys: stripping
one outer delimiter pair, and the expansion depth bound. Both are listed for the design owner in
§8 and must be settled at the freeze.

### 3.5 D1 shapes (F2b)

Every model is a frozen Pydantic model with `extra="forbid"` and tuples for sequences
([schema-rules note](../../design_review/evidence/2026-10-28_library-schema-rules/README.md) §1,
Tested there), hand-written in `core` as coordinator decision 1 and D2 §6 require. Names the schema
owns (predicates, classes, statement kinds, condition predicates, qualifier names of a pack) stay
plain strings here, so an unknown name is a schema error reported by S1's compiled models, not a
malformed-JSON error.

**Two forms, one factory.** The model-facing (authored) and stored forms differ only where a text
is anchored: `phrase` values and `phrase`/`unsupported` condition leaves carry `text` and an
optional `sentence` when authored, and `start`, `end`, `text` and an optional `coarse` when stored
(D1 §6, §7); evidence and `unsupported` items carry `sentence` and `quote` against `start`, `end`
and `coarse` (D2 §7.3). One function builds the value union and the named recursive `Condition`
(`TypeAliasType`, discriminated on `op`, one `$defs` entry) for a given form, so the two unions
share every other model. A single model with all fields optional and a form check was the
alternative; it would accept a stored offset in an authored batch and report it later and less
exactly.

**Values** (D1 §6): `text`, `number` (`v` constrained by `Field(pattern=…)` to the canonical decimal
of D1 §6.2, so a non-canonical number is refused with the canonical spelling in the message and
never rewritten; `unit` and `basis` as written), `bool`, `enum`, `entity` (`ref`), `formula` and
`set` (`latex`, `symbols`, and `sympy` and `parse` with `MISSING` defaults, refused in both batch
forms and set only by M11 in consolidation; `parse` includes `ambiguous`, D1 §6.1), `date` (ISO 8601
by pattern, kept verbatim), `interval` (bounds are values or null) and the form's `phrase`. A
symbol binding has `bind` (the D1 §6.1 kinds) and the `entity`, `claim` and `param` fields that kind
requires, checked by a model validator; a discriminated union per kind was considered and not used,
because the `core.yaml` mirror (S1's contract test) declares one class. Formula positions take only
value objects: the v1 batches already do so (checked over `reference_model_v1`, 2026-10-28), and
D2 §7.3's decoding rules want one shape per position.

**Conditions** (D1 §7): `and`, `or`, `not`, `claim`, `member`, `cmp`, `pred` (arguments are
entity references `{ref}` or formula values), `forall`, and the form's `phrase` and `unsupported` leaves.

**Core qualifiers.** `CoreQualifiers` carries `modality` and `polarity` with defaults that
`Field(exclude_if=…)` leaves out of dumps (so equal meaning gives equal JSON, D3 §6.1) and fills in
for rule views (schema-rules note L-11, Tested there), and `hedge`, `attribution`, `conditions`,
`scope` (authored: the extent; stored: segment key and extent) and `valid_time`, absent by
`MISSING`. The generic model accepts extra keys as raw JSON for schema qualifiers; S1's per-predicate
models subclass it with `extra="forbid"` and typed fields.

**Batch items and envelopes.** Generic `EntityItem`, `StatementItem`, `ClaimItem` (predicate a
string, qualifiers the generic `CoreQualifiers`), `AlternativeItem` and `UnsupportedItem` in both
forms, and generic `AuthoredBatch` and `StoredBatch` envelopes with D2 §7.3's fields. They are what
A0 (schema-free), the fixtures and the `claim_proposal` payload use; S1's compiled envelope over the
same item bases is the full validation. The stored batch does not name its rendition; the record
that holds it does (`kb.observation.rendition_id`, `eval.golden_item.rendition_id`).

**The citation frame** (D1 §10.3) maps each sentence id (`s1`, `c1`, …, by pattern) to its
locator string and canonical text. Two functions come with it, both on I0's resolver:
`resolve_frame(frame, rendition)` selects, for every entry, the one sentence segment whose text
equals the recorded text, or refuses with the failing entries and the resolver's candidates; and
`readdress(batch, frame, served_frame)` rewrites an authored batch's sentence ids into those of a
served packet by matching locator and text, refusing an entry the packet lacks. The second is how
the acceptance test submits fixture batches through the MCP tools (C3).

**The keyed candidate set** is the core claim shape that `validate`'s view builder reads at both
call sites (D5 §8.2) and that S2's batch adapter and C1's pool both produce: entities (`id`,
`key` or null, type, label, scope, symbol, aliases, identity), statements (`id`, `key` or null,
kind, anchor), and claims (`id`, `key` or null, predicate, subject id, object entity id or value,
stored-form qualifiers, statement id, statement role, establishment, stored evidence). At submission
ids are local refs and keys are null; at finalize ids are keys. Derived view attributes and the
grammar's facts at finalize (each value's parse status, kind and symbols, which C1 hands over as
data; D9 §1, D5 §8.2) are the view builder's arguments, not fields here.

**Observation payloads and operations JSON** (D3 §6.2–§6.3 as amended): one model per observation
kind, registered by kind, including `mention.math`, `value.math_kind` and `scope.reopens`, the
`verification` detail `{rule, severity, message}` that M19 writes for a failing rule, and a
`claim_proposal` payload whose `authored` and `citation_frame` are present together or not at all;
`mention_ref`, `trigger_metrics`, `cost`, the policy action (a `<method>/<name>` reference, a limit,
`then`) and the intervention target.

**Closed value sets.** `core/vocab.py` holds, as string enums, every list a 0001 CHECK names (run
kinds and statuses, task unit types and statuses, observation kinds and outcomes, claim statuses,
establishments, statement roles, link types, evidence roles, alias kinds, scopes, method families,
tiers, policy chains with `gaps`, intervention kinds with `promotion`, splits, golden statuses,
passes, item types, tiers), so the types and the CHECKs cannot disagree (store note §1).

**JSON Schemas.** `core/schemas/*.json` are generated from the core adapters (D3 §6) by one
deterministic `GenerateJsonSchema` subclass (no titles, `$schema` set to 2020-12, stable order). It
lives in `core` because both these files and S1's batch schemas need it and `core` cannot import
`schema`; S1 reuses it. The files are committed; a test regenerates them and fails on a difference,
runs `Draft202012Validator.check_schema` on each, and validates fixture payloads with jsonschema as
an independent implementation (schema-rules note §4).

### 3.6 Canonical forms and keys (F2b)

**Canonical forms** follow D1 §6.2: text NFC, casefolded and whitespace-collapsed; numbers as their
(already canonical) `v` with `unit` and `basis` NFC and collapsed, never converted; formulas and
sets as `{t, latex: token_form}` with the merged macro table, their `symbols`, `sympy` and `parse`
outside; dates verbatim; intervals recursively; entity references (`{ref}`) and claim references by key;
`phrase` by text form. **Conditions** take D1 §7's canonical form: flatten nested `and`/`or`, drop
empty ones (an empty tree is no condition), replace a one-argument `and`/`or` by its argument, sort
`and`/`or` arguments by canonical JSON, write `>`/`>=` as `<`/`<=` with sides swapped, sort `pred`
arguments only for predicates the schema declares symmetric, and key `phrase`/`unsupported` leaves
by text form. **Bindings** have a canonical form too (symbol in token form, a lone control word
without its backslash; bind kind; referenced entity or claim key; `param`), used only for
alternative member keys. **Symbols** enter keys the same way (`\mu` is `mu`, D1 §6.1, §10.1).

**Label normalization** (D1 §10.1, D5 §3.3 point 5) is one generic function,
`normalize_label(text, type, rules)`: text form, then one leading article removed, then the pack's
rewrites applied in their declared order (each a `match`/`replace` pattern, D2 §12.1), then the
class's head words removed as trailing whole words, then whitespace collapsed again. `LabelRules`
(articles, head words per class, rewrites) is a core model filled from the pack's `aliases:`
section; core holds no word list. Keys, phase 0 linking by normalized alias and canonical-label
choice all call it, so one change of the rules moves all of them together and is visible in the
configuration hash.

**Keys** (D1 §10.1, D5 §5.2–§5.3) take a `KeyContext` (the document key, the rendition content with
I0's generator, the merged macro table) and a `KeySchema` (data from S1's compiled lookup):

- **global entity** `ent`: type and identity attributes (entity keys, or the canonical form of a
  literal), plus the normalized label only when the class's declared identity keys are incomplete;
- **local entity** `ent`: type, the scope segment's generated locator in structured form, and the
  symbol in key form or, without a symbol, the normalized label;
- **statement** `stm`: the anchor's generated locator in structured form and the 1-based ordinal of
  the statement's first sentence among the anchor's sentences. The anchor is found by containment:
  the innermost `details` or `unit` that contains the first sentence, otherwise the annotation unit
  (D1 §3.4) that contains it, which is how D1 §10.1's "the unit, the `details` block, the paragraph
  outside units" reads without depending on the statement kind;
- **claim** `clm`: subject key, prefixed predicate, `{key}` or `{value: canonical}`, and the identity
  qualifiers: `modality` and `polarity` when not default, `statement` (its key), canonical
  `conditions`, `valid_time`, `attribution` (its key) only under `cited`, and each qualifier the
  predicate lists in `ci:identity_qualifiers`, in canonical form;
- **alternative member**: the claim's parts plus the member's canonical values of the disagreeing
  qualifiers, or its canonical bindings when the bindings disagree (D5 §5.3); referenced claims in
  those bindings are named by their base keys, so member keys cannot form cycles;
- **groups**: `alt` and `idg` over the sorted member keys (D1 §10.1);
- **batch keying**: `key_claims(candidates, …)` keys claims in a topological order of their
  condition `claim` references and returns, beside the keys, the claims it dropped because they lie
  on or behind a reference cycle, each with its reason (D5 §5.2). Which claims are alternatives and
  which disagree is C1's decision, passed in.

These functions are pure and read neither the database nor the schema files; S1, C1 and the tests
supply the facts. The keyed candidate set's `key` fields are filled by C1 with them.

### 3.7 Fixtures (F3)

**`fixtures/s0`** holds the 12 v1 reference batches as 13 files, one per annotation unit of
`core12`, because the spike's T1 is two annotation units: the lead-in paragraph
(`special/LocationScale.html@p:As usual, our starting point`) and `#dfn1`, both in the `trace` slice
(D2 §12.2). Each file holds the unit key, the authored batch (its `unit_ref` the unit key, not the
spike's `T1`…`U12`), the citation frame and provenance (the source file in
`results/s0r2/reference_model_v1/`, the decisions of `decisions_v1.json` that touched it, and for T1
the split).

- **The T1 split** moves the assumption statement `st1`, `Z`, `c_Z_values` and the three
  unsupported items (all on `s1`–`s3`) to the lead-in file, and the definition and its claims to the
  `#dfn1` file, which redeclares `Z` (local, extent `section`) because `c_X_def` and `c_constr` bind
  it. Sentence ids stay as authored; the frame makes them absolute. Acceptance shows that both
  declarations of `Z` key alike, so consolidation meets one entity.
- **Frames** are built once from the spike packets (`results/s0r2/inputs/packet_v1/units/`, which
  number sentences and list standing context) with I0's generator over the S1 renditions the
  references are stored on. The conversion reads the spike results as data and never imports spike
  code; its output, committed, is the authority from then on, and the conversion script is kept
  beside the fixtures only as provenance.
- **Acceptance** comes after I1a, I2a and A0 (coordinator decision 6): every frame resolves on the
  production rendition; A0's stored form gives the same evidence offsets as `reference_v1` (the
  rendition-identity check against the spike, since the renditions are content-identical); each
  `cN` entry (U12's) is in I2a's standing context for its unit; and the batches validate against
  F2b's authored models (S1 validates them against the compiled schema in its own acceptance).

**`fixtures/trace`** is written by hand from `trace.md`'s tables, independently of `fixtures/s0`,
so the acceptance test checks proposals against targets they did not produce (D9 §1):

- `<unit>.segments.json` for the five trace annotation units: each segment's kind, generated
  locator, offsets, author attributes and parse status, with the counts `trace.md` states (math
  spans, sentences). Kinds, counts and attributes come from `trace.md`; offsets come from the S1
  renditions, so this part is also a rendition-identity check. I1a's acceptance compares production
  output with it.
- `<trace unit>.target.json` for T1–T4: the target entities and claims as an authored batch with a
  citation frame (T1's citing sentences of both its annotation units); `must_not`, each "must not
  appear" line as a partial claim pattern; `questions`, each D8 §5.3 query with its parameters and
  the target refs it must return, with and without `include_suppositions`; and phase marks
  (T3's D1 is phase 2). Exact formula text is copied from `trace.md` where it states it and from the
  v1 batch where `trace.md` abbreviates (it says the batches are exact there), and each such item
  records which.

**Vendored pages.** `fixtures/trace/corpus/` holds the original bytes of the four spike pages the
fixtures use (`special/LocationScale.html`, `Normal.html`, `LogNormal.html`, `Gamma.html`, about
98 KB), at the same paths under the same root as in `docs/statistics_corpus/corpus/`
(`siegrist_random/random/special/…`), with the index entries the source profile's corpus index needs
for them (that index's format is ingest and math's) and a `NOTICE` keeping Siegrist's CC BY 2.0
attribution. Because the bytes, the paths and the root are the corpus's, their source URIs, content
hashes, document keys and locators are the corpus's too, so the acceptance test (C3) and ingest's
trace tests run without the gitignored corpus and never skip. When the corpus is present, a test
checks the vendored bytes against `docs/statistics_corpus/MANIFEST.sha256`.

The citation frames come from the S0-R2 v1 packets, which use the same packet rendering as the
pack's worked examples (`reference/E*`, D4 §4.1), so the fixtures and the examples number sentences
and present standing context alike; the examples themselves are schema and rules' and agent
interface's.

The target shapes beyond F2b's (the `must_not` pattern, the question entry) are small models in the
tests' support package, documented in `fixtures/trace/README.md`. Fixture tests compare key
equalities, never key values (D1 §10.1, D9 §4): F3's agreement check derives both the targets and
the trace units' fixture batches on the production rendition and keys them with F2b, then requires
equal key sets over the phase 0 targets, no fixture claim matching a `must_not` pattern, and every
difference explained and resolved (by correcting a fixture, or by a `trace.md` correction from the
design owner). The comparison of query rows with targets in the acceptance test is C3's.

### 3.8 The store (F4)

**Metadata** (`core/db/tables.py`) declares every table, view and index of migration 0001 exactly as
D3 §3–§8 state them as amended on 2026-10-28, `kb.embedding` excepted (phase 1). That includes the
additions folded in that day: the `meta.schema_slot` and `meta.schema_rule` columns for S1's
projection rows, `kb.entity.kind` for statement kinds with its CHECK, `ops.measurement.task_id`
and the `rule` scope type, the `task_cache` predicate that leaves out run-level tasks,
`eval.golden_set.sampling`, the seed and reason on
`eval.document_split`, the intervention kind `promotion`, and `kb.segment.ts_config` set from the
source profile's language. Mechanisms (store note §1–§2, Interface-checked there):
`Identity(always=True)` ids; one naming convention with every CHECK named; CHECK lists built from
`core/vocab.py`; `Text` plus a named CHECK instead of `sa.Enum`; `use_alter` for
`meta.project.promoted_run_id`; `REGCONFIG` for `ts_config` (Interface-checked, SQLAlchemy
documentation through Context7, 2026-10-28); the partial BM25 index through `postgresql_using`,
`postgresql_with` (values rendered verbatim, so quoted inside the string) and `postgresql_where`;
referencing-side indexes for the cascades; no JSONB index without a consuming query. The three
views, `kb.run_observation`, `ops.run_measurement` and `kb.run_rendition`, are frozen SQL text;
the first two count a finished run's task only as of `ops.run.finished_at` (D3 §8 as amended).

**Migration 0001** is rendered once by `alembic revision --autogenerate` against an empty clone of
`cs_template`, reviewed by hand against D3 and `s6.ddl`, and frozen: it never imports `core/db`.
`op.execute` carries only what metadata cannot: the `pg_textsearch` assertion of D3 §3, the four
`CREATE SCHEMA` statements and the three views. The downgrade drops the four schemas with `CASCADE`
and leaves the extensions, which role `paul` could not recreate. Because `alembic check` misses index
methods, `WITH` options, operator classes, partial predicates and CHECK bodies, a test compares the
catalog after `upgrade head` with the catalog after `create_all` plus the view text (store note §1).

**`ci db`**: `init` creates the configured database `TEMPLATE cs_template` on an autocommit
connection to `postgres`, checks that the server encoding is UTF-8 (offsets are code points on
both sides only then) and that the extension is present, then upgrades to head; `migrate` upgrades
an existing database. Both report the head revision, with `--json`.

**Connections** (D3 §1; store note §5, Interface-checked there): `open_store(settings,
application_name, min_size, max_size)` opens one psycopg-pool `ConnectionPool` per process with
`close_returns=True`, `check=ConnectionPool.check_connection` and a `configure` callback that sets
the JSON dumps and loads and leaves the connection idle, and lends it to SQLAlchemy through
`creator=pool.getconn` with `NullPool`. Callers choose the sizes the store note lists per process.
Session state is set only with `SET LOCAL`. A COPY inside an SQLAlchemy transaction uses
`connection.driver_connection`, never its own commit.

**The repository** (`core/db/repo.py`) is the only writer of evidence and observation rows
(coordinator §4), of `ops.intervention`, `eval.golden_pass` and a golden unit's `status` and
`agreement` (D3 §5 "Writers", §7, as amended), and holds the primitives other writers use:

- `get_or_create(conn, table, values, unique)` for the content-hash version tables, methods, method
  configurations and documents: `insert().on_conflict_do_update(...).returning(id)` with
  PostgreSQL 18's `old` to report whether the row was new (store note §2, Interface-checked there).
- `store_rendition(conn, document, content, build)`: computes the digest and key, inserts the
  rendition unless `(document_id, content_digest)` exists, writes its segments only when it is new
  (ids pre-allocated from the identity sequence so parent links go in one statement; `ts_config` from
  the build's profile language; text taken from the canonical text), and records the build
  `(document_id, method_config_id)` every time. A build row that already names a different
  rendition for the same configuration and bytes is refused: it means an ingest that is not
  deterministic, which a silent overwrite would hide.
- `upsert_spans(conn, rendition_id, ranges)`: one `INSERT … SELECT … FROM unnest(…) ON CONFLICT DO
  NOTHING RETURNING`, the text cut from the rendition's canonical text in SQL and the smallest
  containing segment found there (D1 §3.3), then one select for the rows that existed and one
  re-query for keys a concurrent writer took. A range outside the text is refused, so INV-10 holds
  by construction. C1 is its high-volume caller, ingest and the observation path the others.
- `write_observations(conn, task_id, rows)`: binary COPY with `Copy.set_types` from the metadata's
  column types, inside the caller's transaction, after O1's fencing update. Rows arrive with span and
  segment ids resolved and each payload as the validated core model of its kind (the parameter's
  type says so), dumped with defaults omitted. The method-contract `ObservationDraft` is O0's; O1
  turns drafts into rows, so F4 does not depend on O0.
- `record_intervention(conn, …)`, `store_golden_pass(conn, …)` and `set_golden_unit(conn, unit,
  status, agreement)`: typed primitives over D3's columns. The first is called by the agent
  interface's submission tools and CLI commands; the golden ones by evaluation's golden store
  (P0-E-1), which `write_golden` calls. Their callers own when and why; the rows' shape and the
  single write path are F4's.
- `copy_rows(conn, table, columns, rows)`, `allocate_ids(conn, table, n)` (`nextval` over the
  identity sequence) and `insert_returning(conn, table, rows)` (`insertmanyvalues` where ids come
  back) for the bulk writers of other documents, C1's materialization first.
- `insert_artifact(conn, row)` for `meta.compiled_artifact`, with no update path (P0CL-15's store
  share; S1b writes through it).

**The validation boundary** (D3 §6 as amended; schema-rules note §4, Measured there at about
1.5–2 µs per value in Pydantic against 118–338 µs in jsonschema): JSONB is validated once, where it
enters (a method's output, a submission, a loader), and the repository takes validated models and
writes `model_dump(mode="json")` without validating again. Schema-dependent parts (a stored batch's
per-predicate claims, `kb.claim.qualifiers`) are validated by the caller with S1's compiled models,
because `core/db` sits below `schema`; the agreement result model is evaluation's. An absent value
is SQL NULL, never `Jsonb(None)`, which would store JSON `null` and defeat `kb.claim`'s object CHECK
(store note §3).

**Failure behaviour.** A bad row aborts the whole transaction: COPY applies CHECKs and foreign keys
and its `ON_ERROR` options exist only for text formats (store note §3). `classify_error(exc)`
separates retryable SQLSTATEs (40001, 40P01, a lost connection) from defects; a unique violation on
`(task_id, ordinal)` is a fencing defect, not a retry. A missing extension fails 0001 with D3 §3's
instruction. Key collisions are refused before any write, in `RenditionContent` validation.

**Execution fit.** At D3 §11's volumes (about 10⁵ observations and 10⁴–10⁵ claims per run, a few
thousand segments per page set), the write paths are set-based: COPY for observations and
materialized rows, one `unnest` statement per span batch, one segment statement per new rendition,
row-by-row upserts only for the low-volume version tables. Content-preserving re-ingest writes one
build row per document and no segments. Validation is Pydantic only in production. Tests clone a
migrated template per session and roll back per test, so only commit tests pay for a clone. These
are qualitative readings; `s6.volume` gives the measured COPY figures.

## 4. Ports

Spike modules are under `docs/design_review/evidence/2026-10-28_design-spikes/code/`. They are
rewritten against the contracts above, keeping their cases; the spike folder is never imported, and
the spike series keeps scoring with its frozen revision (coordinator decision 12).

| Spike module | Product module | Behaviour and cases kept | Known spike defects not ported |
|---|---|---|---|
| `instruments/batch.py` | `core/values.py`, `core/conditions.py`, `core/batch.py` | Discriminated value and condition unions, schema-owned names as strings, per-item validation, both item forms, error paths with the tag | The spike envelope; bare strings in formula and entity positions (`FormulaArg`, three `EntityArg` shapes); lists in frozen models; the anonymous condition union re-inlined at every site; one phrase model for both forms; `number` without `basis` |
| `instruments/conditions.py` (`canonical_json`, `canonical_condition`, `normalize_tree`) | `core/canonical.py`, `core/keys.py` | Flatten, collapse, drop empty, swap `>`/`>=`, sort `and`/`or` by canonical JSON, leaves by text | Floats accepted and no NFC-collision check in `canonical_json`; `pred` arguments sorted as if every predicate were symmetric; `trees_equivalent` (evaluation's, E2a) |
| `instruments/keys.py` | `core/keys.py` | `make_key`, the parts layout, topological keying with cycles dropped and their reason | Statements keyed by sorted segment keys; local scopes by segment key; the label always in global keys; no `valid_time` or cited-source identity; no member or group keys; the meaning key (no consumer unless `s6.keys`/`s6.restated` call for one); `mismatch_causes` (a spike diagnostic) |
| `instruments/values.py` (`text_norm`, `_dec_str`, `canonical_value`, `canonical_symbol`) | `core/values.py`, `core/keys.py` | The text form; the decimal rules (as the `number` pattern and the loader helper); dispatch by `t`; `\mu` = `mu` | Units converted to pint base units (D1 §6.2 keeps them as stated); `FALLBACK_MACROS` in code (pack data, D2 §12.1); canonical LaTeX printed from the parse tree; the SymPy and numeric tiers and `PARSE_LOG` (E2a's) |
| `mathgrammar/printer.py` (`tex_tokens`, `_expand`, `_read_arg`, `_tree`, `_simplify`, `_flatten`, `serialize`, `tokens_canonical`, `strip_delimiters`) | `core/tex.py` | Macro expansion by TeX's argument rules, single-token brace removal, the separator after a control word, delimiter stripping | The drop set read from the shipped grammar's string `%ignore` lines (it misses the sizing commands); `\cmd*` as one token; deleted text-mode whitespace; `tree_canonical`, `leaves` and `node_text` belong to I2a's grammar |
| `tests_instruments/test_values.py` `test_d1_rules`, `test_macros_page_over_fallback`, `test_numbers_and_text` | F2a and F2b tests | The D1 rule cases (`b^{2}`, `\left( x \right)`, `a + b \, Z`, `\mu x` against `\mux`, `\R \setminus \{0\}`), page macros over the fallback, `\abs{x}` with one argument | `1 cm` equal to `0.01 m` (now two keys); `2.50` normalized (now refused as non-canonical) |
| `results/s0r2/reference_model_v1/`, `inputs/packet_v1/units/`, `results/s0r2/sample.json`, `reference_v1/` | `fixtures/s0` | The 12 batches item for item, their standing-context citations, the stored offsets as the identity check | Spike unit ids as `unit_ref`; packet-relative sentence ids without a frame; T1 as one unit |

## 5. Packages

| Package | Scope | Prerequisites | Acceptance | Revealing failure case |
|---|---|---|---|---|
| P0-F-1 | Workspace member, settings, `ci` app and registration, `tests/conftest.py` with Hypothesis profiles, markers, the CLI runner and the database fixtures; `alembic/` scaffold | none; the database fixture's own check needs the operator's `cs_template` | `just check` passes with the package's first tests; `ci --help` lists the registered groups; settings resolve from `CORPUS_*` with `__` and init beats the environment; a session clones and drops `ci_test_<pid>` | `ci --json status` (a root option) exits 2 while `ci status --json` works; two `Settings` built with different init values in one process do not leak into each other |
| P0-F-2a | `canonical_json` and hashing; evidence types, segment kinds, `RenditionContent`, `MacroDef`; `content_digest`; `doc`/`ren`/`seg`/`cfg` keys; `core/tex.py` | P0-F-1 | Canonical JSON and token-form properties (§6); digest invariance and sensitivity; `core/tex.py` frozen after `s5.keys-property` | `\big/` keeps its sizing command; `\text{ for all }` becomes `\text{forall}`; a float in a configuration silently hashes |
| P0-F-2b | D1 shapes in both forms, generic items and envelopes, citation frame with resolution and re-addressing, keyed candidate set, payload and operations JSON, closed value sets, JSON Schema files; canonical forms, label normalization, every remaining key and batch keying | P0-I-0 (on P0-F-2a) | Key properties of D1 §10.1 (§6); round trips; generated schemas current and accepted by jsonschema; the T3 claims of D3 §10 key deterministically | Two `valid_time` intervals on one claim key alike; `owns(A, B)` and `owns(B, A)` key alike for a predicate not declared symmetric; an edit inside one paragraph moves another block's statement key |
| P0-F-3 | `fixtures/s0` (13 files), `fixtures/trace` (5 segment files, 4 target files, the four vendored pages with their index entries and attribution), their README and support models | P0-F-2b; acceptance needs P0-I-1a, P0-I-2a, P0-A-0 | Frames resolve on production renditions; derived offsets equal `reference_v1`'s; `cN` entries in the standing context; targets and fixtures agree by key equality with no unexplained difference | A frame entry whose recorded text differs from the production sentence (a rendering convention, a `[n]` marker) is refused rather than matched approximately; T1 submitted unsplit cannot be re-addressed to the `#dfn1` packet |
| P0-F-4 | Metadata, migration 0001, `ci db`, the pool, the repository and bulk primitives, the store tests | P0-F-2b; `s6.ddl`, `s6.constraints`, `s6.bm25`; the operator's `pg_textsearch` provisioning | Upgrade, downgrade, upgrade; the catalog comparison; every named CHECK fires; D3 §10's T3 rows insert and D3 §9's queries return them; the BM25 query uses the partial index; rendition deduplication and the `finished_at` cutoff in the views | A CHECK body or partial-index predicate changed under its old name passes `alembic check` and fails the catalog comparison; a second build of identical content writes segments |

**P0-F-1.** Mechanisms: pydantic-settings with nested models and init and environment sources only;
Typer `add_typer`, a root callback, a per-command `--json` alias and `CliRunner` (interfaces note
§3–§4); `CREATE DATABASE … TEMPLATE` with a migrated template keyed by the versions directory's hash,
`DROP DATABASE … WITH (FORCE)` and rolled-back outer transactions (store note §1). Evidence: none.

**P0-F-2a.** Mechanisms: the `regex` module for the TeX tokenizer (D1 §6.2); `json` with sorted keys
over an NFC pre-walk; Pydantic frozen models for the evidence types. Evidence: `s5.keys-property`
freezes `core/tex.py`; `s5.macros` checks the expansion rules on the corpus' tables. The module can
be written and used before both report; nothing that stores keys runs before the freeze except
tests.

**P0-F-2b.** Mechanisms: `TypeAliasType` for the recursive `Condition`, `Field(discriminator=…)`,
`Field(exclude_if=…)` defaults and `MISSING` where absent and null differ, `strict=True` for
authored batches on the JSON path, `Field(pattern=…)` for canonical numbers, dates and sentence ids
(schema-rules note §1, Tested there); a custom `GenerateJsonSchema`; Hypothesis `st.builds` and
`st.from_type` with `st.from_regex` registered for patterned fields (interfaces note §6.1, Tested
there). Evidence: `s4.batch-validation`, where S4 finds a core shape that the v1 batches or the
worked examples need differently.

**P0-F-3.** Mechanisms: F2b's models and frame functions, I0's generator and resolver, A0's cascade.
Evidence: none from the spike records; the reference data are the S0-R2 results named in §4.

**P0-F-4.** Mechanisms: SQLAlchemy Core metadata with identity columns, the naming convention and
dialect index options; Alembic autogenerate once, the CHECK-by-name plugin and a catalog
comparison; psycopg-pool lent to SQLAlchemy; binary COPY with `Copy.set_types`; `unnest` with
`ON CONFLICT DO NOTHING`; `on_conflict_do_update(…).returning()` with PostgreSQL 18's `old`; ids
pre-allocated with `nextval` (D3 §1, store note §1–§5). Evidence: `s6.ddl` (the corrected DDL that
0001 follows), `s6.constraints` (which constraints fire and which invariants stay in the
repository), `s6.bm25` and `s6.queries` (index syntax and plans), `s6.dry-run` (compiled schema rows
against the tables), `s6.volume` and `s6.sizes` (COPY and size readings), `s6.keys` and
`s6.restated` (whether a meaning-key column is needed; none is created unless they call for it).

## 6. Tests

| Package | What the tests establish |
|---|---|
| P0-F-1 | The settings contract (prefix, nesting, sources, init over environment, the report of unknown names); the CLI contract (groups registered, `--json` per command, stdout and stderr apart, no settings built for `--help`); the database fixtures clone, isolate (a rolled-back write is invisible to the next test), sweep and drop |
| P0-F-2a | Canonical JSON: equal output under permuted object keys and NFD input (`key(x) == key(nfd(x))`); refusal of floats, `Decimal`, dates, bytes, lone surrogates and NFC-colliding keys; the decimal helpers on generated decimal strings (idempotent, canonical by pattern). Digest: equal for two `RenditionContent` values built in different child orders; different after any one change to text, an offset, a kind, a parse status or reason, an attribute or a macro body. Token form: the metamorphic properties of §3.4 under Hypothesis, the D1 rule cases ported from the spike, and macro cases (whole names, arguments, optional defaults, the depth bound) |
| P0-F-2b | Round trips of every model drawn by `st.builds`/`st.from_type`; per-form refusals (offsets in an authored batch, `sympy` in a batch, a non-canonical number); the key properties of D1 §10.1 on synthetic segment trees with I0's generator: two contents with identical content and different builds give identical claim keys, and an edit inside one paragraph that leaves every block's opening words unchanged leaves every other statement key unchanged; permuted `and` arguments and present-or-absent defaults give equal keys; two `valid_time` intervals, two cited sources, and `pred` arguments of a non-symmetric predicate in two orders give different keys; an attribution outside `cited` does not move a key; candidates differing only in bindings get distinct member keys; a condition cycle is dropped with its reason; label normalization on the D5 §3.3 cases ("the normal distribution", "normally distributed") with test-local rules; the JSON Schema files are current, pass `check_schema` and accept the dumped instances (jsonschema as the independent oracle) |
| P0-F-3 | The fixture acceptance of §3.7, gated on its prerequisites: frames resolve, offsets equal `reference_v1`'s, standing-context entries present, both `Z` declarations of T1 key alike, targets and fixtures agree by key equality, no fixture claim matches a `must_not` pattern; with the corpus present, the vendored pages' bytes match the corpus manifest |
| P0-F-4 | Upgrade, downgrade to base (the four schemas gone, the extensions kept), upgrade again; the catalog after `upgrade head` equals `create_all`'s plus the views; `alembic check` clean; every named CHECK refuses a value outside its `core/vocab.py` set, and the cross-column CHECKs fire on their bad rows (`s6.constraints`); D3 §10's T3 rows, built from `fixtures/trace` segments and hand-made entities and claims, insert, and D3 §9's queries return them; the BM25 query plan names `segment_bm25`; `store_rendition` twice with identical content writes one rendition and its segments once and two builds for two configurations; span upsert returns the same ids on repeat and refuses an out-of-text range; an observation COPY inside a transaction whose fencing update found no row commits nothing; `kb.run_observation` ignores a task finished after its run; `kb.run_rendition` selects the rendition the run's ingest configuration built |

Shared fixtures used: the `db` and `committing_db` fixtures and the Hypothesis profiles (F1);
`fixtures/trace` segments (F3) in F4's row test. Tests that need the corpus are marked `corpus`.

## 7. Indicative size

The coordinator's budget for foundations is 2,500 product lines, tests excluded (§8).

| Package | Indicative lines | Bulk |
|---|---|---|
| P0-F-1 | 200 | settings, the app and registration, the `alembic/` scaffold |
| P0-F-2a | 450 | `core/tex.py` (about 250), canonical JSON, evidence types and the digest |
| P0-F-2b | 1,000 | values, conditions and items in both forms (about 350), payload and operations models (about 200), keys and canonical forms (about 300), frame, candidate set and labels |
| P0-F-3 | data | fixtures are JSON; the support models are test code |
| P0-F-4 | 850 | metadata for about 35 tables (about 450), the repository (about 300), `ci db` and the pool |
| **Total** | about 2,500 | |

Migration 0001 is generated and frozen, and `core/schemas/*.json` are generated; both are outside
the count. The metadata is the largest single risk: it mirrors D3 line for line, and the catalog
comparison is what keeps that from being a second copy that drifts.

## 8. Choices left to implementation

- Module boundaries inside `core/` beyond those named, and file names for fixtures (each file holds
  its unit key).
- Whether segments of a new rendition go in by one `unnest` statement or a binary COPY; binary COPY
  would need a dumper for `regconfig`, which psycopg may not provide by default (an inference to
  confirm at F4), so `unnest` with a cast is the expected route.
- Pool sizes per process within the store note's table, and the Hypothesis example counts.
- How the one-time fixture conversion is scripted, as long as its output is reviewed and committed.
- For the design owner, before `core/tex.py` freezes: whether `token_form` strips one outer pair of
  math delimiters (the spike did, and quotes and display spans carry them), and the macro-expansion
  depth bound; both move keys and D1 §6.2 states neither. Until decided, the module implements the
  spike's stripping and a depth of 16, and records both in its tests.
