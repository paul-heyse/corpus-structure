# D3 · Database

**Proposed (2026-10-28).** The physical realization of [D1](D1-knowledge-representation.md) and
of the operations model in one PostgreSQL 18 database. The DDL below is the specification for
the first Alembic migration; column comments that would repeat D1 are omitted.

## 1. Choices

| Need | Choice | Why not the alternatives |
|---|---|---|
| Authority for knowledge and operations | PostgreSQL 18.6 (installed) | One transaction links a task, its observations and the claims they change. A graph or triple store would add a second authority to keep in sync; claims with qualifiers fit relational rows plus JSONB |
| Variable payloads: qualifiers, values, conditions, observation payloads, configs | `jsonb` with GIN indexes where queried | Variation lives in data, not in per-type tables (the old repository's 277 contract classes) |
| Similarity search | pgvector 0.8.7 (installed), `halfvec`, HNSW | Joins and filters in one query. HNSW on `halfvec` supports up to 4,000 dimensions; the embedding dimension is fixed by spike S7 (`OPEN-D3-2`) |
| Lexical search | BM25 through pg_textsearch 1.5.1 (installed: Debian `postgresql-18-pg-textsearch`): a `bm25` partial index over one block level, ranked top-k queries (§5) | Replaces the old Tantivy crate inside the one authority, with no second index to synchronize. Built-in full-text search (`tsvector`, `ts_rank_cd`) has no corpus-level term weighting. Needs preloading and a superuser once (§3; `OPEN-D3-1`) |
| Graph traversal | Recursive CTEs; NetworkX and pgmpy projections in memory | The knowledge graph is small per project; path-heavy workloads would revisit this |
| Analytics and evaluation reports | DuckDB reading PostgreSQL (`postgres` extension) or Parquet exports | Read-only; never a second authority |
| Originals | Content-addressed files under `data/originals/<sha256>`; the corpus stays where it is and is referenced by path and hash | Keeps large binaries out of the database |
| Access from Python | SQLAlchemy Core 2.1 table metadata + psycopg 3 (COPY for bulk observation writes) | Same stack as before, without ORM |
| Migrations | Alembic; 0001 generated once from the Core metadata, then frozen (it never imports `core/db`) | `alembic check` compares an index's uniqueness and columns only (no `USING`, `WITH`, operator classes or partial `WHERE`, CHECKs by name), so a test compares the catalog after `upgrade head` with `create_all` ([store note](../design_review/evidence/2026-10-28_library-store/README.md) §1) |
| Connections | one psycopg-pool `ConnectionPool` per process; SQLAlchemy borrows through `creator=pool.getconn` with `NullPool` | One owner of connections; `SET LOCAL`, never session `SET`; the JSON serializer set in the pool's `configure` callback, which `create_engine(json_serializer=)` does not reach (store note §3, §5) |

Identifiers are `bigint GENERATED ALWAYS AS IDENTITY`. Deterministic keys from D1 §10 are
`text` columns with unique constraints where identity must hold. Closed value sets are `text`
with `CHECK` constraints rather than PostgreSQL enum types, so adding a value is a one-line
migration.

## 2. Layout

Four PostgreSQL schemas:

| Schema | Holds | D1 plane |
|---|---|---|
| `meta` | Projects, schema versions and their declarations, guideline versions | Schema |
| `kb` | Documents, renditions, segments, spans, embeddings, observations, entities, claims | Evidence, entities, claims, provenance |
| `ops` | Methods, configurations, policies, runs, tasks, measurements, interventions, experiments | Operations |
| `eval` | Golden sets, units and items; alignments; results | Evaluation |

Creation order follows foreign keys: `meta.project`, `meta.schema_version`,
`meta.compiled_artifact`, `meta.guideline_version`, `ops.method`, `ops.method_config`,
`ops.policy_version`, `ops.policy_rule`, `ops.debug_slice`, `ops.run`, `kb.document`,
`kb.rendition`, `kb.segment`, `kb.span`, `ops.task`, `kb.rendition_build`, `kb.observation`, then
the rest.

## 3. `meta`: schema, guidelines and domain declarations

**Extensions.** Phase 0 needs `pg_textsearch` (1.5.1, installed from the Debian package
`postgresql-18-pg-textsearch`) for BM25 lexical search (§5); `vector` arrives with `kb.embedding`
in phase 1. pg_textsearch loads only through `shared_preload_libraries` (on this machine currently
`pg_stat_statements,auto_explain`), and neither extension is trusted, so role `paul` cannot create
them. The operator therefore, once, adds `pg_textsearch` to `shared_preload_libraries`, restarts
the server, and creates it (and later `vector`) as `postgres` in the template database
`cs_template`, which `ci db init` and the test databases clone. Migration 0001 does not create the
extension: it asserts it and fails with that instruction (design authority, 2026-10-28, after the
operator confirmed the installed package; [store note](../design_review/evidence/2026-10-28_library-store/README.md)
§0, L-S5; [overview](../libraries/postgresql-18-pg-textsearch.md) §11.2).

**Interim instance (operator, 2026-10-28).** Until the system instance is set up, development and
tests use a project-local PostgreSQL 18 cluster built from the system's PG18 binaries: `just db-up`
initializes it once under `build/pg/` (owned by the developer, who is its superuser), starts it on its
own port and socket with `shared_preload_libraries = 'pg_textsearch'`, and creates `cs_template` with
both extensions; `just db-down` stops it. No sudo and no restart of the system cluster is needed.
Moving to the system instance later changes only `CORPUS_DATABASE__URL` (P0-F-1).
> Status: **Interface-checked** (store note §0, 2026-10-28): the 1.5.1 install script refuses to
> run unless the library is preloaded, and neither control file is marked trusted; the
> provisioning step and the assertion are **Proposed** (2026-10-28)

```sql
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_extension WHERE extname = 'pg_textsearch') THEN
    RAISE EXCEPTION 'pg_textsearch is missing: add it to shared_preload_libraries, restart, then as postgres run CREATE EXTENSION pg_textsearch in cs_template and clone the database from it';
  END IF;
END $$;

CREATE SCHEMA meta;  CREATE SCHEMA kb;  CREATE SCHEMA ops;  CREATE SCHEMA eval;

CREATE TABLE meta.project (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name            text NOT NULL UNIQUE,
  domain          text NOT NULL,                 -- domain pack name, e.g. 'statistics'
  promoted_run_id bigint,                        -- FK added after ops.run
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE meta.schema_version (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id    bigint NOT NULL REFERENCES meta.project,
  domain        text NOT NULL,
  label         text NOT NULL,                   -- version: field of the YAML, e.g. '0.1.0'
  content_hash  text NOT NULL,                   -- D2 §2
  parent_id     bigint REFERENCES meta.schema_version,
  source        jsonb NOT NULL,                  -- {"statistics.yaml": "...", "rules.yaml": "...", "core.yaml": "..."}
  migration     jsonb,                           -- D2 §8 mapping from parent, breaking changes only
  state         text NOT NULL DEFAULT 'active' CHECK (state IN ('proposed','active','rejected','retired')),
  created_by    text NOT NULL,                   -- 'human:operator', 'agent:opus-5.5', ...
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, content_hash)
);

CREATE TABLE meta.compiled_artifact (           -- D2 §7 compiler outputs; rows are added, never edited
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version ON DELETE CASCADE,
  compiler          text NOT NULL,               -- 'json_schema', 'gliner2', 'rules', 'annotator_reference', ...
  compiler_version  text NOT NULL,
  kind              text NOT NULL,               -- which artifact of that compiler, e.g. 'batch.model_facing', 'batch.stored', 'batch.decoding'
  hash              text NOT NULL,               -- sha256 of canonical JSON of body (D1 §10.1); what method configurations reference
  body              jsonb NOT NULL,              -- the artifact (a text artifact is a JSON string)
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (schema_version_id, compiler, compiler_version, kind)
);

CREATE TABLE meta.schema_class (
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version ON DELETE CASCADE,
  name          text NOT NULL,
  parent        text,
  kind          text NOT NULL CHECK (kind IN ('entity','value','abstract')),
  scope         text CHECK (scope IN ('global','local')),
  identity_keys text[] NOT NULL DEFAULT '{}',
  description   text,
  annotations   jsonb NOT NULL DEFAULT '{}',
  PRIMARY KEY (schema_version_id, name)
);

CREATE TABLE meta.schema_slot (
  schema_version_id   bigint NOT NULL REFERENCES meta.schema_version ON DELETE CASCADE,
  name                text NOT NULL,             -- prefixed: 'stat:has_distribution'
  role                text NOT NULL CHECK (role IN ('predicate','qualifier','identity','field')),
  domain_class        text,
  range               text,
  object_kind         text,                      -- D2 §3.2 ci:object
  multivalued         boolean NOT NULL DEFAULT false,
  qualifiers          text[] NOT NULL DEFAULT '{}',
  identity_qualifiers text[] NOT NULL DEFAULT '{}',
  subsets             text[] NOT NULL DEFAULT '{}',  -- the named predicate subsets the slot belongs to (e.g. 'family_structure'; rules' subset:<name>)
  extract             text,
  description         text,
  annotations         jsonb NOT NULL DEFAULT '{}',   -- the slot's scalar ci: annotations (ci:param_map, symmetric, ...)
  PRIMARY KEY (schema_version_id, name)
);

CREATE TABLE meta.schema_enum (
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version ON DELETE CASCADE,
  name        text NOT NULL,
  values      jsonb NOT NULL,                    -- [{"value": "scale", "description": "...", "annotations": {...}}]
  annotations jsonb NOT NULL DEFAULT '{}',
  PRIMARY KEY (schema_version_id, name)
);

CREATE TABLE meta.schema_rule (
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version ON DELETE CASCADE,
  rule_id     text NOT NULL,
  grp         text NOT NULL CHECK (grp IN ('rules','guideline','derive')),   -- the rules.yaml section (D2 §7.4)
  applies_to  text[] NOT NULL,                   -- the predicate set compiled from a predicate, a list, subset:<name> or any
  at          text[] NOT NULL DEFAULT '{}',      -- call sites, 'batch' and 'finalize' (D5 §8.2); empty for derive rules
  severity    text CHECK (severity IN ('warning','error')),   -- null for derive rules; always 'warning' in grp 'guideline'
  when_expr   text NOT NULL,                     -- a derive rule's match condition
  check_expr  text,                              -- null for derive rules, whose templates stay in the compiled rules artifact
  description text,
  PRIMARY KEY (schema_version_id, rule_id),
  CHECK ((grp = 'derive') = (severity IS NULL)),
  CHECK ((grp = 'derive') = (check_expr IS NULL))
);

CREATE TABLE meta.guideline_version (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id        bigint NOT NULL REFERENCES meta.project,
  domain            text NOT NULL,
  label             text NOT NULL,
  content_hash      text NOT NULL,
  body              text NOT NULL,               -- the guideline rules (D2 §10.1–§10.9); the generated reference and direction log are hashed elsewhere (D2 §10.10–§10.11)
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version,
  parent_id         bigint REFERENCES meta.guideline_version,
  change_note       text,
  state             text NOT NULL DEFAULT 'active' CHECK (state IN ('proposed','active','rejected','retired')),
  created_by        text NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, content_hash)
);
```

**Compiled artifacts** are identified by what produced them as well as by the sources: a
schema version row holds sources only and never changes, and each compiler output is a
`meta.compiled_artifact` row of (schema version, compiler, compiler version, kind). A compiler fix
adds rows beside the old ones, so runs that used the old artifacts keep them. A method
configuration declares the artifacts it reads by (compiler, kind); the method registry resolves
them against the run's schema version, and the resolved hashes are part of the configuration's
canonical params (`ops.method_config.params`), so a new artifact is a new configuration.
Compilers are deterministic, so a lost or pruned artifact is rebuilt from the sources and its
hash checked, never edited (P0CL-15; operator, 2026-10-28).
> Status: **Proposed** (2026-10-28)

**The `meta.schema_*` tables are a projection** of the schema-table artifact (D2 §7.1). When a
schema-table compiler version adds its `meta.compiled_artifact` row for a schema version, that
version's `schema_class`, `schema_slot`, `schema_enum` and `schema_rule` rows are replaced from
it. No run reads them as input: methods read compiled artifacts by hash, so replacing the
projection changes nothing a run computed. They serve SQL joins from claims to their schema
definitions and the grouping of metrics by class and predicate.
> Status: **Proposed** (2026-10-28)

## 4. `ops`: methods, policies, runs and tasks

```sql
CREATE TABLE ops.method (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name        text NOT NULL,                     -- 'extract.gliner_schema'
  version     text NOT NULL,                     -- implementation version, bumped on behaviour change
  family      text NOT NULL CHECK (family IN ('ingest','profile','extract','normalize','resolve',
                    'consolidate','validate','verify','measure','llm','agent','human','eval')),
  description text,
  UNIQUE (name, version)
);

CREATE TABLE ops.method_config (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  method_id   bigint NOT NULL REFERENCES ops.method,
  name        text NOT NULL DEFAULT 'default',   -- named configuration from methods.yaml: '<method>/<name>'
  params      jsonb NOT NULL,                    -- canonical JSON; its (compiler, kind) artifact references resolved to hashes for one schema version (§3)
  config_hash text NOT NULL UNIQUE,              -- D1 §10.1 'cfg:' key
  tier        text CHECK (tier IN ('deterministic','encoder','local_llm','agent','hosted_llm','human')),
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ops.policy_version (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id   bigint NOT NULL REFERENCES meta.project,
  label        text NOT NULL,
  content_hash text NOT NULL,
  source       text NOT NULL,                    -- policies.yaml as loaded
  state        text NOT NULL DEFAULT 'active' CHECK (state IN ('proposed','active','rejected','retired')),
  created_by   text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, content_hash)
);

CREATE TABLE ops.policy_rule (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  policy_version_id bigint NOT NULL REFERENCES ops.policy_version ON DELETE CASCADE,
  rule_key          text NOT NULL,               -- 'escalate.low_confidence.local_llm'
  chain             text NOT NULL CHECK (chain IN ('propose','escalate','adjudicate','identity','gaps')),
  priority          integer NOT NULL,            -- position in the chain (D6 §7.1)
  unit_type         text NOT NULL,               -- the chain's default or the entry's own (D6 §7.1)
  condition         text NOT NULL,               -- rule-engine expression over the unit context
  action            jsonb NOT NULL,              -- {"method": "<method>/<name>", "limit": 50, "then": "stop|continue"} (§6.3)
  enabled           boolean NOT NULL DEFAULT true,
  UNIQUE (policy_version_id, rule_key)
);

CREATE TABLE ops.debug_slice (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id bigint NOT NULL REFERENCES meta.project,
  name       text NOT NULL,
  selector   jsonb NOT NULL,                     -- the slice as declared (D2 §12.2, D6 §8): locators ("special/Normal.html#rel1", ...), pages, includes, {"index": …}, {"golden_set": label}; resolved at run start, locators per rendition (D1 §3.4)
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, name)
);

CREATE TABLE ops.run (
  id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id           bigint NOT NULL REFERENCES meta.project,
  kind                 text NOT NULL CHECK (kind IN ('ingest','full','slice','experiment','rescore','golden')),
  phase                smallint NOT NULL,        -- 0–5 (D0); policies read it
  options              jsonb NOT NULL DEFAULT '{}',  -- agent_mode, agent_reuse, fresh methods, gpu mode, corpus (a slice, default 'first-pass'), scope (a slice naming the units routed, with its resolved unit list and that list's hash; the kind stays, so the run can be promoted) (D6 §2, §4, §5, §8)
  debug_slice_id       bigint REFERENCES ops.debug_slice,
  corpus_hash          text NOT NULL,            -- over the corpus's (document key, content hash) set and the ingest config hash (below)
  schema_version_id    bigint NOT NULL REFERENCES meta.schema_version,
  guideline_version_id bigint REFERENCES meta.guideline_version,
  policy_version_id    bigint NOT NULL REFERENCES ops.policy_version,
  code_commit          text NOT NULL,
  parent_run_id        bigint REFERENCES ops.run,    -- kind 'golden': the run whose renditions and M13 output the golden packets read (§8)
  reference_run_id     bigint REFERENCES ops.run,    -- the promoted run when this run was created; null at bootstrap; written at insert only (§8)
  iteration            integer NOT NULL DEFAULT 0,   -- current route iteration (D6 §2)
  iteration_limit      integer NOT NULL DEFAULT 3,
  status               text NOT NULL CHECK (status IN ('created','running','awaiting_agent',
                            'consolidating','finished','failed','cancelled')),
  notes                text,
  started_at           timestamptz,
  finished_at          timestamptz,
  created_at           timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE meta.project ADD FOREIGN KEY (promoted_run_id) REFERENCES ops.run;
```

**The reference run is recorded, not looked up.** Consolidation, M14 and packet assembly read
`ops.run.reference_run_id`, never `meta.project.promoted_run_id`, so a promotion during a run
changes nothing the run computes, and a run re-executed over the same inputs reads the same
reference (P0CL-05; operator, 2026-10-28). The repository sets it in the `INSERT` that creates the
run and has no update path for it.
> Status: **Proposed** (2026-10-28)

**The corpus hash is computable at insert.** `ops.run.corpus_hash` is the SHA-256 of the
canonical JSON (D1 §10.1) of the set of (document key, content hash) pairs of the documents the
run's corpus selects (run option `corpus`, D6 §8), in document-key order, together with the hash
of the run's ingest configuration. Both are known before ingest runs, so the hash does not wait
for renditions; two runs with equal corpus hashes read the same bytes through the same adapter
configuration.
> Status: **Proposed** (2026-10-28)

## 5. `kb`: evidence, observations, entities and claims

```sql
CREATE TABLE kb.document (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id    bigint NOT NULL REFERENCES meta.project,
  key           text NOT NULL UNIQUE,            -- 'doc:…'
  source_uri    text NOT NULL,                   -- e.g. 'siegrist_random/random/special/Normal.html'
  content_hash  text NOT NULL,                   -- sha256 of original bytes
  original_path text NOT NULL,                   -- where the bytes are
  mime          text NOT NULL,
  title         text,
  meta          jsonb NOT NULL DEFAULT '{}',     -- licence, source id from SOURCES.tsv, chapter, first_pass ...
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, source_uri, content_hash)
);

CREATE TABLE kb.rendition (                     -- one content of a document (D1 §3.1, §3.2)
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  document_id    bigint NOT NULL REFERENCES kb.document,
  key            text NOT NULL UNIQUE,           -- 'ren:…' over (document key, content digest)
  content_digest text NOT NULL,                  -- sha256 of canonical JSON of the content-identity relation (D1 §3.2)
  canonical_text text NOT NULL,
  macros         jsonb NOT NULL DEFAULT '{}',    -- the page's macro table (D4 M01); content, inside the digest
  parse_status   text NOT NULL CHECK (parse_status IN ('ok','partial','failed')),   -- from its segments
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (document_id, content_digest)
);

CREATE TABLE kb.segment (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  rendition_id bigint NOT NULL REFERENCES kb.rendition ON DELETE CASCADE,
  key          text NOT NULL UNIQUE,             -- 'seg:…'
  parent_id    bigint REFERENCES kb.segment,
  kind         text NOT NULL,                    -- D1 §3.2; checked against a list in the migration
  ordinal      integer NOT NULL,                 -- position among siblings
  depth        integer NOT NULL,
  start_offset integer NOT NULL,
  end_offset   integer NOT NULL,
  text         text NOT NULL,                    -- canonical_text[start:end], stored for search
  ts_config    regconfig NOT NULL DEFAULT 'english',   -- from the source profile's language (default 'english'), selecting its BM25 index; not content
  attrs        jsonb NOT NULL DEFAULT '{}',      -- author markup (D1 §3.2); never diagnostics, which live in kb.rendition_build.parse_detail
  parse_status text NOT NULL DEFAULT 'ok' CHECK (parse_status IN ('ok','partial','failed')),
  parse_reason text,                             -- why `partial`/`failed` (delimiting, D1 §3.1); content, inside the digest
  CHECK ((parse_status = 'ok') = (parse_reason IS NULL)),
  CHECK (start_offset <= end_offset)
);
CREATE INDEX segment_range ON kb.segment (rendition_id, start_offset, end_offset);
CREATE INDEX segment_kind  ON kb.segment (rendition_id, kind);
-- BM25 over one non-overlapping block level, so a token is counted once and hits do not nest
-- (store note L-S3); one partial index per text-search configuration; the kind list is confirmed
-- on the corpus by S6
CREATE INDEX segment_bm25 ON kb.segment USING bm25 (text) WITH (text_config = 'english')
  WHERE kind IN ('paragraph','heading','list_item','math_display') AND ts_config = 'english';

CREATE TABLE kb.span (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  rendition_id bigint NOT NULL REFERENCES kb.rendition ON DELETE CASCADE,
  start_offset integer NOT NULL,
  end_offset   integer NOT NULL,
  segment_id   bigint NOT NULL REFERENCES kb.segment,   -- smallest containing segment
  text         text NOT NULL,
  UNIQUE (rendition_id, start_offset, end_offset),
  CHECK (start_offset < end_offset)
);

CREATE TABLE kb.embedding (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  target_type     text NOT NULL CHECK (target_type IN ('segment','entity','alias')),
  target_id       bigint NOT NULL,
  model_config_id bigint NOT NULL REFERENCES ops.method_config,
  vec             halfvec(1024) NOT NULL,        -- dimension fixed by S7 (OPEN-D3-2)
  UNIQUE (target_type, target_id, model_config_id)
);
CREATE INDEX embedding_hnsw ON kb.embedding USING hnsw (vec halfvec_cosine_ops);
```

**Renditions are content-addressed** (D1 §3.1, §3.2). A rendition row is one content of a
document, unique by `(document_id, content_digest)`; the adapter configuration that produced it is
provenance in `kb.rendition_build` (below `ops.task`, whose rows it references), one row per
(document, configuration), many builds to one rendition. Ingest computes the digest over the
combined M01 and M03 output before writing, then inserts the rendition with `ON CONFLICT
(document_id, content_digest) DO NOTHING`, writes segments only when the rendition row is new, and
records its build either way. A content-preserving ingest change (a port, a spaCy bump, a profile
fix that changes nothing) therefore keeps every rendition, segment and span row and every key;
parser diagnostics (source lines, parse errors with positions) and exclusion records, which
depend on the configuration, live on the build's `parse_detail`, and no segment carries them, so
the digest covers whole segments (P0CL-01; operator, 2026-10-28).
> Decision: [ADR-0019](../adr/0019-identity-follows-content.md)
> Status: **Proposed** (2026-10-28)

**Lexical search** (OPEN-D3-1) is BM25 through pg_textsearch, for the `find` query (D8 §5.1) and
candidate lookup for linking. A query always names the index and repeats its predicate, because
the implicit string form skips partial BM25 indexes, and a bound parameter defeats it in any case
([overview](../libraries/postgresql-18-pg-textsearch.md) §3.3; store note §6):

```sql
SELECT s.id, s.key, s.text <@> to_bm25query(:q, 'kb.segment_bm25') AS score
FROM kb.segment s
WHERE s.kind IN ('paragraph','heading','list_item','math_display') AND s.ts_config = 'english'
  AND s.rendition_id = ANY(:renditions)          -- the run's renditions (kb.run_rendition, §8)
ORDER BY s.text <@> to_bm25query(:q, 'kb.segment_bm25')
LIMIT :k;
```

- **Scores** are negative, best first (ascending order). Corpus statistics are those of the
  partial index, every row in it, renditions no current run selects included (overview §8.2), so
  a score ranks hits within one query; it is not calibrated and not comparable across indexes.
- **Filters.** Under an ordered BM25 scan the rendition condition is a post-filter, and the scan
  widens its batch until the limit fills; a selective prefilter may instead score qualifying rows
  standalone and sort, with the same statistics (store note §6). Boolean and phrase filters use
  `s.text @@ to_tsquery('english', …)` with the index's configuration (overview §2.3); combined
  with ranking, the filter is evaluated first and its matches scored and sorted, which suits
  selective filters.
- **SQLAlchemy** writes `WITH` values verbatim: `Index("segment_bm25", segment.c.text,
  postgresql_using="bm25", postgresql_with={"text_config": "'english'"},
  postgresql_where=…)` (store note §2).
- **Same-row text.** The BM25 index reads `kb.segment.text` on the same row, which is why the
  column stays (OPEN-D3-3); no index or generated column can read `kb.rendition`.

> Status: index and query syntax **Interface-checked** (2026-10-28): source-read for 1.5.1 (store
> note §6) and documented (overview §2–§3); the design is **Proposed**. S6 runs it on the corpus
> with the partial index and checks with `EXPLAIN` that the planner uses it

`ts_config` is the segment's language, set by ingest from the source profile's `language` (default
`english`, [D4 M01](D4-method-catalog.md#m01-ingesthtml)) when a rendition's segments are first
written; it is search configuration, outside the content digest (D1 §3.2).
Each configuration has its own partial BM25 index, whose `text_config` and `ts_config =` predicate
agree, so a second language is an additive index over rows with another value, never a rewrite of
the table or of the first index; a query chooses the index by the configuration it searches.
> Status: **Proposed** (2026-10-28)

For phase 1 (store note L-S6): `halfvec` HNSW indexes up to 4,000 dimensions (1024 and 2048 fit;
the 8B model's native 4096 does not); pgvector filters after the index scan, so `kb.embedding`
gets one partial HNSW index per `target_type` plus `hnsw.iterative_scan`. Rows reference their
target's row: renditions are content-addressed, so a content-preserving re-ingest keeps every
segment row and no embedding is orphaned, while a content change makes new segments, which need
new embeddings anyway.

`kb.embedding` is created by the phase 1 migration that adds M04, not by 0001: nothing reads it in
phase 0, and its dimension waits on S7 (P11 in the design rationale). The rest of this section is
migration 0001.

`ops.task` sits here in creation order because observations reference it:

```sql
CREATE TABLE ops.task (
  id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id           bigint NOT NULL REFERENCES ops.run,
  stage            text NOT NULL,                -- D6 §2 stage names
  unit_type        text NOT NULL CHECK (unit_type IN ('document','rendition','segment','observation','entity','claim',
                        'alternative_group','identity_group','run','golden_unit')),
  unit_id          bigint,                       -- id in the table named by unit_type (eval.golden_unit for 'golden_unit'); null for groups and 'run'
  unit_key         text,                         -- stable key of the unit across renditions (D1 §3.4 unit key for annotation units; the group key for groups)
  method_config_id bigint NOT NULL REFERENCES ops.method_config,   -- the configuration the run resolved for the stage or for the rule's '<method>/<name>' (§6.3)
  trigger_rule_id  bigint REFERENCES ops.policy_rule,  -- null for base-stage tasks
  trigger_metrics  jsonb NOT NULL DEFAULT '{}',  -- the metric values the rule saw
  input_hash       text NOT NULL,                -- D6 §4
  packet_hash      text,                         -- the packet hash the method's input digest returns (D4 §1): for M24 and M10, the hash of the packet text the assembler produced and the task served (D4 §4.1, D8 read_unit); null otherwise
  reused_task_id   bigint REFERENCES ops.task,   -- set when status = 'reused'
  status           text NOT NULL CHECK (status IN ('pending','running','awaiting_agent','done',
                        'empty','failed','skipped','reused','cancelled')),
  attempt          integer NOT NULL DEFAULT 0,   -- fencing token: incremented at claim; renewals and terminal writes require it (§8)
  priority         integer NOT NULL DEFAULT 0,
  claimed_by       text,                         -- worker id or agent session while running
  lease_until      timestamptz,                  -- 5 min for workers, 30 min for agent leases (D6 §3.2, D8 §2.1)
  cost             jsonb NOT NULL DEFAULT '{}',  -- {"wall_ms":…, "gpu_ms":…, "tokens_in":…, "tokens_out":…}
  error            jsonb,                        -- failure detail; an agent task also keeps its first rejected submission result here while it stays awaiting_agent for its one resubmission (D8)
  reason           text,                         -- why skipped or cancelled: 'scope', 'limit', 'budget', 'prerequisite_failed', ...
  created_at       timestamptz NOT NULL DEFAULT now(),
  started_at       timestamptz,
  finished_at      timestamptz                   -- set by every terminal write, including creation as 'reused' or 'skipped'; fates are read against ops.run.finished_at (§8)
);
-- the queue (store note L-S1): what workers claim, what expires, what the agent leases
CREATE INDEX task_pending ON ops.task (run_id, stage, method_config_id, priority DESC, id) WHERE status = 'pending';
CREATE INDEX task_lease   ON ops.task (lease_until) WHERE status = 'running';
CREATE INDEX task_agent   ON ops.task (run_id, priority DESC, id) WHERE status = 'awaiting_agent';
CREATE INDEX task_cache ON ops.task (method_config_id, input_hash) WHERE status IN ('done','empty') AND unit_type <> 'run';   -- run-level tasks are never reused (§8)
CREATE INDEX task_run   ON ops.task (run_id, stage);

CREATE TABLE kb.rendition_build (                -- provenance: which adapter configurations produced a rendition
  document_id      bigint NOT NULL REFERENCES kb.document,
  method_config_id bigint NOT NULL REFERENCES ops.method_config,   -- the adapter configuration (M01 with M03)
  rendition_id     bigint NOT NULL REFERENCES kb.rendition,
  task_id          bigint NOT NULL REFERENCES ops.task,            -- the ingest task that first built it
  parse_detail     jsonb NOT NULL DEFAULT '{}',  -- exclusions, warnings, parser diagnostics: source lines, parse errors with positions (D4 M01); never on segments
  created_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (document_id, method_config_id)    -- one configuration on one document's bytes yields one rendition
);
CREATE INDEX rendition_build_rendition ON kb.rendition_build (rendition_id);

CREATE TABLE kb.observation (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  task_id      bigint NOT NULL REFERENCES ops.task,
  ordinal      integer NOT NULL,
  kind         text NOT NULL CHECK (kind IN ('author_markup','mention','relation','record','attribute',
                    'classification','value','scope','link','claim_proposal','judgment','verification')),
  rendition_id bigint REFERENCES kb.rendition,
  segment_id   bigint REFERENCES kb.segment,
  span_id      bigint REFERENCES kb.span,
  payload      jsonb NOT NULL,                   -- §6.2, by kind
  score        real,
  outcome      text NOT NULL CHECK (outcome IN ('produced','empty','failed')),
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (task_id, ordinal)
);
CREATE INDEX observation_span    ON kb.observation (span_id);
CREATE INDEX observation_segment ON kb.observation (segment_id, kind);

CREATE TABLE kb.entity (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id            bigint NOT NULL REFERENCES ops.run ON DELETE CASCADE,
  key               text NOT NULL,               -- 'ent:…' or 'stm:…'
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version,
  type              text NOT NULL,               -- schema class
  label             text NOT NULL,
  scope             text NOT NULL CHECK (scope IN ('global','local')),
  scope_segment_id  bigint REFERENCES kb.segment,
  attrs             jsonb NOT NULL DEFAULT '{}', -- identity attributes only (D1 §4.1); empty for statements, which key by anchor locator
  kind              text,                        -- statements only: the StatementKind value (D1 §4.1, §4.3); a field like label, not identity
  confidence        real,
  UNIQUE (run_id, key),
  CHECK ((scope = 'local') = (scope_segment_id IS NOT NULL)),
  CHECK ((type = 'Statement') = (kind IS NOT NULL))
);
CREATE INDEX entity_type ON kb.entity (run_id, type);

CREATE TABLE kb.entity_alias (
  entity_id  bigint NOT NULL REFERENCES kb.entity ON DELETE CASCADE,
  alias      text NOT NULL,
  normalized text NOT NULL,
  alias_kind text NOT NULL CHECK (alias_kind IN ('label','symbol','abbreviation','term','expression')),
  PRIMARY KEY (entity_id, normalized, alias_kind)
);
CREATE INDEX entity_alias_lookup ON kb.entity_alias (normalized);

CREATE TABLE kb.entity_anchor (                  -- statements and local entities: where they are
  entity_id  bigint NOT NULL REFERENCES kb.entity ON DELETE CASCADE,
  segment_id bigint NOT NULL REFERENCES kb.segment,
  PRIMARY KEY (entity_id, segment_id)
);

CREATE TABLE kb.entity_mention (                 -- which observations resolved to the entity: mentions, or (phase 0) proposals' entity items
  entity_id      bigint NOT NULL REFERENCES kb.entity ON DELETE CASCADE,
  observation_id bigint NOT NULL REFERENCES kb.observation,
  PRIMARY KEY (entity_id, observation_id)
);

CREATE TABLE kb.claim (
  id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id           bigint NOT NULL REFERENCES ops.run ON DELETE CASCADE,
  key              text NOT NULL,                -- 'clm:…'
  subject_id       bigint NOT NULL REFERENCES kb.entity,
  predicate        text NOT NULL,                -- 'stat:has_distribution'
  object_entity_id bigint REFERENCES kb.entity,
  object_value     jsonb,                        -- D1 §6 value
  qualifiers       jsonb NOT NULL DEFAULT '{}',  -- core + schema qualifiers, incl. conditions
  statement_id     bigint REFERENCES kb.entity,
  statement_role   text CHECK (statement_role IN ('premise','conclusion','definiens','restriction','example_value')),
  status           text NOT NULL CHECK (status IN ('candidate','accepted','rejected','ambiguous','conflicting','unsupported')),
  establishment    text NOT NULL CHECK (establishment IN ('stated','derived','agent_asserted')),
  confidence       real,
  completeness     jsonb NOT NULL DEFAULT '{}',  -- {"unresolved_symbols": 1, "phrase_conditions": 0}
  UNIQUE (run_id, key),
  CHECK ((object_entity_id IS NULL) <> (object_value IS NULL))
);
CREATE INDEX claim_pred      ON kb.claim (run_id, predicate, status);
CREATE INDEX claim_subject   ON kb.claim (run_id, subject_id);
CREATE INDEX claim_object    ON kb.claim (run_id, object_entity_id);
CREATE INDEX claim_statement ON kb.claim (run_id, statement_id);

CREATE TABLE kb.claim_evidence (
  claim_id bigint NOT NULL REFERENCES kb.claim ON DELETE CASCADE,
  span_id  bigint NOT NULL REFERENCES kb.span,
  role     text NOT NULL CHECK (role IN ('primary','supporting','condition','definition')),
  PRIMARY KEY (claim_id, span_id, role)
);

CREATE TABLE kb.claim_support (
  claim_id       bigint NOT NULL REFERENCES kb.claim ON DELETE CASCADE,
  observation_id bigint NOT NULL REFERENCES kb.observation,
  PRIMARY KEY (claim_id, observation_id)
);

CREATE TABLE kb.claim_link (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id        bigint NOT NULL REFERENCES ops.run ON DELETE CASCADE,
  from_claim_id bigint NOT NULL REFERENCES kb.claim ON DELETE CASCADE,
  link_type     text NOT NULL CHECK (link_type IN ('derived_from','contradicts','equivalent_to','alternative_of','refines')),
  to_claim_id   bigint NOT NULL REFERENCES kb.claim ON DELETE CASCADE,
  detail        jsonb NOT NULL DEFAULT '{}',     -- rule id, reason, alternative group id
  UNIQUE (from_claim_id, link_type, to_claim_id)
);
CREATE INDEX claim_link_to ON kb.claim_link (to_claim_id);   -- cascading deletes (store note L-S4)
```

**JSONB indexes only with a query that uses them** (store note L-S4). Earlier drafts had GIN
`jsonb_path_ops` indexes on `kb.observation.payload` and `kb.claim.qualifiers`. Neither had a
consumer: §9's `qualifiers @? '$.param_values.variance'` cannot use a `jsonb_path_ops` index, which
serves only `== constant` path clauses, and is carried by `claim_pred`. Every GIN index also slows
each COPY. A JSONB index is added in the migration that adds the query needing it.

Remaining `ops` tables:

```sql
CREATE TABLE ops.measurement (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id     bigint NOT NULL REFERENCES ops.run ON DELETE CASCADE,   -- the run whose task or orchestrator wrote it
  task_id    bigint REFERENCES ops.task,         -- the method task that wrote it; null for the orchestrator's run metrics (D6 §6); read through reuse (§8)
  iteration  integer NOT NULL,
  scope_type text NOT NULL CHECK (scope_type IN ('run','rendition','segment','entity','claim','predicate',
                  'class','stage','method','rule')),
  scope_id   bigint,
  scope_key  text,                               -- predicate or class name, stage name, method name, rule id
  metric     text NOT NULL,                      -- D6 §6 names; e.g. 'rules.evaluated' (scope a rule) from each M19 pass
  value      double precision,
  detail     jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX measurement_lookup ON ops.measurement (run_id, metric, scope_type, scope_id);
CREATE INDEX measurement_task   ON ops.measurement (task_id) WHERE task_id IS NOT NULL;

CREATE TABLE ops.intervention (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id  bigint NOT NULL REFERENCES meta.project,
  run_id      bigint REFERENCES ops.run,
  task_id     bigint REFERENCES ops.task,        -- the agent or human task it completed, if any
  actor       text NOT NULL,                     -- 'agent:opus-5.5', 'human:operator'
  session_ref text,                              -- Claude Code session id or similar
  kind        text NOT NULL CHECK (kind IN ('extract','adjudicate','golden_write','golden_adjudicate',
                   'schema_proposal','guideline_change','policy_proposal','experiment_decision',
                   'promotion','direction','ack','veto','audit')),   -- promotion: setting meta.project.promoted_run_id (D7 §7)
  target      jsonb NOT NULL,                    -- what it acts on (unit key, claim key, golden unit, ...)
  refs        jsonb NOT NULL DEFAULT '{}',       -- where the content is: {"observations": [...], "golden_pass": id,
                                                 --   "schema_version": id, "guideline_version": id, "policy_version": id, "experiment": id}
  body        text,                              -- a direction's text; otherwise null (content lives where refs point)
  rationale   text,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX intervention_run ON ops.intervention (run_id, kind);

CREATE TABLE ops.experiment (
  id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id       bigint NOT NULL REFERENCES meta.project,
  hypothesis       text NOT NULL,
  target_metric    text NOT NULL,
  guard_metrics    jsonb NOT NULL DEFAULT '[]',
  baseline_run_id  bigint REFERENCES ops.run,
  candidate_run_id bigint REFERENCES ops.run,
  candidate_change jsonb NOT NULL,               -- config, policy, schema or guideline change under test
  result           jsonb,
  decision         text CHECK (decision IN ('promote','reject','inconclusive')),
  decided_by       text,
  decided_at       timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now()
);
```

**Method-written measurements belong to their task.** A measurement a method writes carries its
`task_id` and is read through reuse (`ops.run_measurement`, §8); the orchestrator's run metrics
(D6 §6) carry none. Each M19 pass records its per-rule counts of evaluated (rule, claim) pairs
as measurements of its own task (metric `rules.evaluated`, scope type `rule`, scope key the rule
id), which coverage reads beside the `verification` observations that hold failing outcomes only
(D4 M19). M19 tasks are of unit `run` and never reused (§8), so these rows always belong to the
run that wrote them.
> Status: **Proposed** (2026-10-28)

**Writers.** The repository layer writes `ops.intervention`, `eval.golden_pass`, and a golden
unit's `status` and `agreement` (§7), through primitives that their owners call: the agent
interface's submission tools (`propose_claims`, `write_golden`) and the CLI commands record
interventions, `write_golden` stores passes, and evaluation supplies the agreement and status it
computes. No owner writes these rows with its own SQL.
> Status: **Proposed** (2026-10-28)

## 6. JSONB contracts

Keys and rendition content digests (D1 §10.1, §3.2) are computed in Python from canonical JSON, never from `jsonb::text`, whose key order and number formatting are PostgreSQL's.

JSONB is validated once, at the Pydantic boundary where it enters (a method's output, a
submission, a loader), never again on write: the repository layer takes validated models. The
domain-independent shapes (values, condition trees, the observation payloads by kind, the
operations JSON, the citation frame and the generic stored items of D1 §10.3) are core models,
and `corpus_structure/core/schemas/*.json` ([D9 §1](D9-repository-and-phase0.md#1-layout)) are
generated from them and hold only those shapes. What a predicate contributes (its object value
and its qualifiers, schema qualifiers included) is typed by the per-version models compiled from
the run's schema version, which are compiled artifacts (§3), not files in `core/schemas`
([schema-rules note](../design_review/evidence/2026-10-28_library-schema-rules/README.md) L-10).
Defaults are filled for rules and omitted in storage through `Field(exclude_if=…)` (L-11).
> Status: **Proposed** (2026-10-28)

Summaries of the shapes:

### 6.1 Values, qualifiers, conditions

- **Value** (`kb.claim.object_value`, values inside qualifiers and conditions): D1 §6, tagged by
  `t`.
- **`kb.claim.qualifiers`**: an object whose keys are core qualifier names (`modality`,
  `polarity`, `hedge`, `attribution`, `conditions`, `scope`, `valid_time`) or schema qualifier
  names valid for the predicate in the run's schema version; values are D1 §6 values, maps of
  values (`param_values`), or the condition tree (`conditions`, D1 §7). Defaults are omitted
  (`modality: asserted`, `polarity: positive` are not stored), so equal meaning gives equal JSON.
- **Condition tree**: D1 §7. `claim` nodes carry claim **keys**; readers resolve them within the
  same run.

### 6.2 Observation payloads, by kind

| Kind | Required fields | Optional |
|---|---|---|
| `author_markup` | `markup` (`dfn`, `unit`, `details`, `link`, `class`), `value` | `target` (link target); `synthesize` (on a block whose kind the source profile's `details_kinds.synthesize` names: the claim its containment states, `{predicate, object, evidence}`, which consolidation turns into a claim; D4 M01, D5 §3.5; P0CL-07) |
| `mention` | `label`, `text`, `start`, `end` | `attributes` {group: {label, score}}, `math_ref`; `math` (M09 `symbol` mentions: the occurrence's decoration, such as its base, subscript and power; D4 M09) |
| `relation` | `label` (predicate), `head` {`start`,`end`,`label`}, `tail` {…} | `joint` (bool: from `JointIE`), `feasible` |
| `record` | `structure`, `fields` {name: [{`text`,`start`,`end`,`score`}]} | `anchor` |
| `attribute` | `mention_ref`, `group`, `value` | — |
| `classification` | `task`, `labels` [{label, score}] | `feasible`, `violations` (constrained classifier) |
| `value` | `value` (D1 §6) | `parse_error`; `math_kind` (the typed start symbol that read the span: formula, relation, membership or set; D4 M11) |
| `scope` | `mention_ref` with the mention's `start`, `end`; `binding_site` (a `mention_ref`) with its `start`, `end`; `scope_segment` (key), `extent` | `binding` (provisional kind, D4 M13); `reopens` (for a "Suppose again" binding site: the `mention_ref` and offsets of the earlier binding site it reopens, D4 M13) |
| `link` | `mention_ref` (M14) or `pair` of entity keys (M15), `candidate` (entity key, or `{"new": {type, label}}`), `score`, `features` | `rank` |
| `claim_proposal` | `batch` (a stored-form `ClaimProposalBatch` on the observation's rendition, D2 §7.3); for authored proposals (M10, agent) also `authored` (the model-facing batch as submitted) and `citation_frame` (D1 §10.3), which are the authority, `batch` being derived from them by the quote cascade (D4 §4.3) | `rationale`; `rejected` [{`item`, `reason`}] (D4 §4.3); `establishment: derived`, `derived_from` (claim keys) and `rule` for M23 |
| `judgment` | `target` {`kind`: observation, claim, alternative_group, identity_group; `ref`}, `decision` (`accept`, `reject`, `choose`, `merge`, `split`, `unsure`), `rationale`, `guideline_version` | `chosen` (for `choose`), `faithful` (bool, with several chosen), `confidence` (`low`, `medium`, `high`) |
| `verification` | `claim_key`, `verifier`, `verdict` (`consistent`, `refuted`, `not_checkable`) | `detail`, `counterexample`; M19 writes only failing outcomes, `verdict: refuted` with `detail {rule, severity, message}` (D5 §8.1) |

### 6.3 Operations JSON

- **`mention_ref`** is `{"task": id, "ordinal": n}`, or `{"ordinal": n}` inside the same task,
  because observation ids are assigned only when a task's observations are copied in. A payload
  that refers to another task's mentions also records their offsets beside each ref (`scope`,
  §6.2): a task reused by content digest (M13) keeps refs to the M09 task it first read, which
  may be older than the run's own, and readers match by offsets on the rendition, which the
  digest makes identical (**Proposed**, 2026-10-28).
- `ops.task.trigger_metrics`: `{metric_name: value}` exactly as the policy rule evaluated them.
- `ops.task.cost`: `wall_ms`, `gpu_ms`, `tokens_in`, `tokens_out`, `model`.
- `ops.policy_rule.action`: `method` (a named configuration, `<method>/<name>`, of the domain's
  `methods.yaml`), `limit` (max tasks this rule may create per iteration), `then` (`stop` ends the
  chain for the unit, `continue` evaluates the next rule). The name is resolved per run against
  the run's method configurations (D6 §7.1), never stored as a config hash, so a policy version
  is independent of the artifacts its methods read; the task a rule creates records the resolved
  `method_config_id` beside `trigger_rule_id`.
  > Status: **Proposed** (2026-10-28)
- `ops.intervention.target`: `{"kind": "unit"|"claim"|"alternative_group"|"golden_unit"|"schema"|"guideline"|"policy"|"run", "ref": …}`; a `promotion` targets the run it promotes.

## 7. `eval`: goldens and results

```sql
CREATE TABLE eval.document_split (               -- page-level split assignment (D7 §3.1, §4)
  project_id  bigint NOT NULL REFERENCES meta.project,
  document_id bigint NOT NULL REFERENCES kb.document,
  split       text NOT NULL CHECK (split IN ('dev','test','reserved')),  -- reserved: worked-example pages, never golden (D7 §3.1)
  reason      text NOT NULL,                     -- why the page is in its split: the seeded order, reserved, forced to dev, or an operator direction (D7 §3.1)
  seed        text,                              -- the split seed of an assignment by the seeded order; null otherwise
  assigned_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, document_id)
);

CREATE TABLE eval.golden_set (
  id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id           bigint NOT NULL REFERENCES meta.project,
  label                text NOT NULL,
  split                text NOT NULL CHECK (split IN ('dev','test')),
  schema_version_id    bigint NOT NULL REFERENCES meta.schema_version,
  guideline_version_id bigint NOT NULL REFERENCES meta.guideline_version,
  sampling             jsonb NOT NULL,           -- how the units were drawn (D7 §3.1): seed, size, strata, allocation, forced units, sampler version
  frozen_at            timestamptz,              -- test sets freeze at phase gates
  created_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, label, split)
);

CREATE TABLE eval.golden_unit (
  id                    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  golden_set_id         bigint NOT NULL REFERENCES eval.golden_set,
  unit_key              text NOT NULL,           -- identity: the annotation unit's locator-based unit key at creation (D1 §3.4); never changes
  current_locator       text NOT NULL,           -- the unit's locator on its latest resolving rendition; re-location updates this, not the key (D7 §3.5)
  authored_rendition_id bigint NOT NULL REFERENCES kb.rendition,  -- provenance: the rendition the passes' packets came from
  status                text NOT NULL CHECK (status IN ('draft','adjudicated','stale','retired')),
  agreement             jsonb NOT NULL DEFAULT '{}',   -- evaluation's agreement result model (D7 §3.3): by tier and predicate, with the A/B diff; validated at the evaluation boundary
  created_at            timestamptz NOT NULL DEFAULT now(),
  UNIQUE (golden_set_id, unit_key)
);

CREATE TABLE eval.golden_pass (                  -- the single store of authored passes (D7 §3): the authority
  id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  golden_unit_id       bigint NOT NULL REFERENCES eval.golden_unit ON DELETE CASCADE,
  pass                 text NOT NULL CHECK (pass IN ('a','b','c')),
  guideline_version_id bigint NOT NULL REFERENCES meta.guideline_version,
  batch                jsonb NOT NULL,           -- model-facing ClaimProposalBatch as authored (pass c: the adjudicated batch)
  citation_frame       jsonb NOT NULL,           -- {"s1": {"locator": "…", "text": "…"}, "c1": {…}}: each cited sentence id → its locator and text (D1 §10.3)
  decisions            jsonb,                    -- pass c: per-difference decision, reason, guideline_gap marks
  session_ref          text NOT NULL,            -- authoring session; passes a and b of a unit must differ
  model                text NOT NULL,            -- authoring model (ADR-0011: Sonnet 5.5)
  inputs               jsonb NOT NULL,           -- guideline version, annotator-reference hash, packet hash, M13 version that chose the context
  created_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (golden_unit_id, pass, guideline_version_id)
);

CREATE TABLE eval.golden_item (                  -- derived: one pass c batch located on one rendition
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  golden_pass_id bigint NOT NULL REFERENCES eval.golden_pass ON DELETE CASCADE,   -- the pass c it projects
  rendition_id   bigint NOT NULL REFERENCES kb.rendition,
  item_type      text NOT NULL CHECK (item_type IN ('entity','statement','claim','alternative','unsupported')),
  local_ref      text NOT NULL,
  payload        jsonb NOT NULL,                 -- a stored item: the core stored-form batch element (D1 §10.3, D2 §7.3), offsets into rendition_id
  context        boolean NOT NULL DEFAULT false, -- a context premise stated outside the unit: scored only through claim nodes here (D7 §5.1)
  UNIQUE (golden_pass_id, rendition_id, item_type, local_ref)
);

CREATE TABLE eval.alignment (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id         bigint NOT NULL REFERENCES ops.run ON DELETE CASCADE,
  golden_item_id bigint NOT NULL REFERENCES eval.golden_item,
  target_type    text NOT NULL CHECK (target_type IN ('entity','claim')),
  target_id      bigint,                         -- null: unmatched golden item
  tier           text NOT NULL CHECK (tier IN ('none','core','full','evidence')),
  score          real,
  detail         jsonb NOT NULL DEFAULT '{}'
);

CREATE TABLE eval.result (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id        bigint NOT NULL REFERENCES ops.run ON DELETE CASCADE,
  golden_set_id bigint NOT NULL REFERENCES eval.golden_set,
  scope_type    text NOT NULL,                   -- 'all', 'predicate', 'class', 'unit_kind', 'stage'
  scope_key     text,
  metric        text NOT NULL,                   -- 'precision', 'recall', 'f1', 'unsupported_rate', ...
  tier          text NOT NULL CHECK (tier IN ('core','full','evidence')),
  value         double precision,
  n             integer NOT NULL,                -- denominator
  golden_snapshot bigint[] NOT NULL,             -- the pass c rows (eval.golden_pass ids) this result scored
  detail        jsonb NOT NULL DEFAULT '{}',
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX alignment_run ON eval.alignment (run_id);   -- deleting a run's materialized rows (§8)
CREATE INDEX result_run    ON eval.result (run_id);
```

**Authored passes are the authority; items are derived.** A golden unit is identified by its unit
key, a locator (D1 §3.4), so it is the same unit on every rendition of its page; the rendition its
packets came from is provenance. Each pass stores the batch in the model-facing form its author
wrote, with its citation frame (D1 §10.3). `eval.golden_item` is a projection of one pass c batch
onto one rendition: before a run is aligned, evaluation resolves the frame on the run's rendition
(`kb.run_rendition`, §8) and, when items for that pair do not yet exist, derives them by the
production quote cascade (D4 §4.3); `write_golden` stores passes only and never derives items. A
frame that does not resolve marks the unit `stale` and derives nothing. Re-location (D7 §3.5) rewrites only the frame's locators, keeping the batch and the
recorded sentence texts; re-authoring adds a new pass c beside the old one. Items are never
edited, only derived again for another rendition or pass. `eval.result` records
the pass c ids it scored (`golden_snapshot`), so a result stays tied to the goldens it used after
re-authoring (P0CL-03; operator, 2026-10-28).
> Decision: [ADR-0019](../adr/0019-identity-follows-content.md)
> Status: **Proposed** (2026-10-28)

**Sampling and splits are recorded with their inputs.** `eval.golden_set.sampling` holds what
drew the set's units (D7 §3.1): the seed, the size, the strata, the allocation, the forced units
and the sampler's version, so a set can be redrawn and compared with a later sampler.
`eval.document_split` records, per page, the reason for its assignment and, for pages assigned by
the seeded order, the seed.
> Status: **Proposed** (2026-10-28)

## 8. Runs, snapshots and reads

- **Run lifecycle.** `created` → `running` (base stages, then route iterations) → possibly
  `awaiting_agent` (only agent tasks remain) → `consolidating` → `finished`, or `failed` /
  `cancelled`. Details in [D6 §2](D6-orchestration-metrics-policies.md#2-the-stage-graph-and-run-lifecycle).
- **Materialization.** Entities, claims, links and alignments are written per run and never
  updated after `finished`. A run that is not the promoted run, not the reference run of a kept
  run, not an experiment's baseline or candidate, and not referenced by a golden set may have its
  **materialized rows deleted** (entities,
  claims, links, alignments, results, by `run_id`); the `ops.run` row and its tasks stay, because
  later runs may reuse those tasks (D6 §4) and observations are kept while referenced (below)
  (store note L-S2). `eval.alignment` and `eval.result` are indexed by `run_id` for that delete.
- **Golden passes are tasks** of a run of kind `golden` (one per golden set, guideline
  version and authoring round), with `unit_type = 'golden_unit'` and method `golden.pass` (configs `golden.pass/a`,
  `/b`, `/c`), so `golden_next` leases through the same queue and fencing as every other task
  (D8 §2.2). `ci golden create` (D7 §3.1) creates the golden set and its units, the golden run
  and the pass `a` and `b` tasks; the run's `parent_run_id` is the run whose renditions and M13
  output the golden packets read, and those renditions are the units' `authored_rendition_id`.
  `write_golden` completes its task through the shared agent-completion step (D6 §3, D8 §2.1)
  and writes through the repository's primitives (§5, Writers); when it stores the second of
  passes `a` and `b` of a unit, evaluation's agreement result for the unit
  (`eval.golden_unit.agreement`, D7 §3.3) is stored and the pass `c` task created in the same transaction,
  so no other process watches for it. Golden items are derived by evaluation (§7), never by
  `write_golden`, and evaluation finishes the golden run when every unit is adjudicated
  (**Proposed**, design authority, 2026-10-28).
- **Claiming and fencing** (store note L-S1). Workers claim with one
  `UPDATE … FROM (SELECT … FOR UPDATE SKIP LOCKED LIMIT n)` that also takes expired leases, so no
  reaper process exists. The claim increments `attempt`; every lease renewal and every terminal
  write is conditioned on that `attempt`, so a worker that lost its lease commits nothing. Agent
  leases keep status `awaiting_agent`, so their expiry needs no action. Reuse (D6 §4) is resolved at
  task creation in one `INSERT … SELECT … LEFT JOIN LATERAL` over `task_cache`. Tasks of
  `unit_type 'run'` (an M19 pass, D4 M19) are never reused: their input is the run itself, and
  `task_cache` leaves them out (**Proposed**, 2026-10-28).
- **Promotion.** `meta.project.promoted_run_id` is set by the experiment decision
  ([D7 §7](D7-evaluation-goldens-outer-loop.md#7-experiments-and-promotion)). "Current
  knowledge" queries resolve it once per journey and then name the run by id (D8 §5; P0CL-11);
  nothing a run computes reads it, because each run records its reference run at creation (§4).
- **Every eligible unit has a fate.** For each eligible unit a run creates a task, or a `skipped`
  task with its `reason` (`scope` for a unit outside the run's declared scope, `limit`, `budget`,
  …), so coverage is a count over `ops.task`, never an absence (§9; P0CL-11; **Proposed**,
  2026-10-28).
- **A finished run's fates are its tasks as of `ops.run.finished_at`.** A task the run still held
  open when it finished (an agent task completed later, a twin settled later, a task cancelled
  afterwards) counts as **unresolved** for that run, whatever its status now; nothing that
  finishes later changes what the run reports. Every terminal write sets `ops.task.finished_at`,
  including creation as `reused` or `skipped`, so the rule is one comparison. The orchestrator's
  fate reader (D6), the coverage query (§9), `kb.run_observation` and `ops.run_measurement`
  (below) and `ci promote`'s check (D7 §7) apply it; a per-run fate snapshot was considered and
  not adopted (**Proposed**, design authority, 2026-10-28).
- **Observations are never deleted** while a task that produced them is referenced by any kept
  run (directly or through `reused_task_id`).
- **Effective observations of a run.** A view resolves reuse and, for a finished run, the fate
  rule above:

```sql
CREATE VIEW kb.run_observation AS
SELECT t.run_id, o.*
FROM ops.task t
JOIN ops.run r ON r.id = t.run_id
JOIN kb.observation o ON o.task_id = COALESCE(t.reused_task_id, t.id)
WHERE t.status IN ('done','empty','reused')
  AND (r.finished_at IS NULL OR t.finished_at <= r.finished_at);
```

- **Effective measurements of a run.** Method-written measurements carry their `task_id` and are
  read through reuse like observations, so a reused task's measurements (M02's character and math
  features, for example) count for the run that reuses it; the orchestrator's run metrics have no
  task and are read by `run_id` (**Proposed**, 2026-10-28):

```sql
CREATE VIEW ops.run_measurement AS
SELECT t.run_id, m.id, m.task_id, m.iteration, m.scope_type, m.scope_id, m.scope_key,
       m.metric, m.value, m.detail
FROM ops.task t
JOIN ops.run r ON r.id = t.run_id
JOIN ops.measurement m ON m.task_id = COALESCE(t.reused_task_id, t.id)
WHERE t.status IN ('done','empty','reused')
  AND (r.finished_at IS NULL OR t.finished_at <= r.finished_at)
UNION ALL
SELECT m.run_id, m.id, m.task_id, m.iteration, m.scope_type, m.scope_id, m.scope_key,
       m.metric, m.value, m.detail
FROM ops.measurement m
WHERE m.task_id IS NULL;
```

- **Selected renditions of a run.** A run selects one rendition per document through its ingest
  tasks: the rendition that the task's adapter configuration built from the document. `find`,
  evaluation's predicted set and golden item derivation read this view rather than re-deriving
  the join (**Proposed**, design authority, 2026-10-28):

```sql
CREATE VIEW kb.run_rendition AS
SELECT t.run_id, b.document_id, b.rendition_id
FROM ops.task t
JOIN kb.rendition_build b ON b.document_id = t.unit_id AND b.method_config_id = t.method_config_id
WHERE t.stage = 'ingest' AND t.unit_type = 'document' AND t.status IN ('done','reused');
```

## 9. Query patterns

These back the typed queries of [D8 §5](D8-agent-and-query-interfaces.md#5-typed-queries).
`:run` is the run id the journey resolved once (§8), never `promoted_run_id` read again per call;
each result carries it, with the coverage of its scope (below). A run that has not finished is
refused before any of these runs (D8 §5).

**Family profile** (everything stated about a family in the run):

```sql
SELECT c.predicate, c.qualifiers, c.object_value, o.label AS object_label, c.status, c.confidence
FROM kb.claim c
JOIN kb.entity s ON s.id = c.subject_id
LEFT JOIN kb.entity o ON o.id = c.object_entity_id
WHERE c.run_id = :run AND s.type = 'DistributionFamily' AND s.key = :family_key
  AND c.status IN ('accepted','candidate');
```

**Statement reconstruction** (premises, conditions, conclusions and proof of a theorem):

```sql
SELECT c.statement_role, c.key, c.predicate, c.qualifiers -> 'conditions' AS conditions, c.qualifiers
FROM kb.claim c
WHERE c.run_id = :run AND c.statement_id = :statement_id
ORDER BY CASE c.statement_role WHEN 'premise' THEN 0 WHEN 'definiens' THEN 1
                               WHEN 'restriction' THEN 2 ELSE 3 END;
```

**Claims with a qualifier** (all `has_distribution` claims that give a `variance`):

```sql
SELECT key FROM kb.claim
WHERE run_id = :run AND predicate = 'stat:has_distribution'
  AND qualifiers @? '$.param_values.variance';
```

**Evidence for a claim** with the canonical text around it:

```sql
SELECT ce.role, sp.text, sp.start_offset, sp.end_offset, seg.kind, seg.attrs ->> 'id' AS unit_id
FROM kb.claim_evidence ce
JOIN kb.span sp ON sp.id = ce.span_id
JOIN kb.segment seg ON seg.id = sp.segment_id
WHERE ce.claim_id = :claim_id;
```

**Coverage of a scope** (units extracted, skipped by reason, failed, unresolved), from the fates
of §8 as of the run's `finished_at`, over the documents a query's scope names:

```sql
SELECT fate.status, fate.reason, count(DISTINCT t.unit_key) AS units
FROM ops.run r
JOIN ops.task t ON t.run_id = r.id
JOIN kb.segment s ON s.id = t.unit_id
JOIN kb.run_rendition rr ON rr.run_id = t.run_id AND rr.rendition_id = s.rendition_id
CROSS JOIN LATERAL (
  SELECT CASE WHEN t.finished_at <= r.finished_at THEN t.status ELSE 'unresolved' END AS status,
         CASE WHEN t.finished_at <= r.finished_at THEN t.reason END AS reason
) fate
WHERE r.id = :run AND t.stage = 'propose' AND t.unit_type = 'segment'
  AND rr.document_id = ANY(:documents)
GROUP BY fate.status, fate.reason;
```
> Status: **Proposed** (2026-10-28, P0CL-11). In phase 0 each unit has one `propose` task; once
> several tiers propose (phase 1), a unit counts under each of its tasks' fates, and the query
> layer (D8 §5) states which fate it reports

**Why a method ran** on a unit:

```sql
SELECT t.stage, m.name, pr.rule_key, t.trigger_metrics, t.status, t.cost
FROM ops.task t
JOIN ops.method_config mc ON mc.id = t.method_config_id
JOIN ops.method m ON m.id = mc.method_id
LEFT JOIN ops.policy_rule pr ON pr.id = t.trigger_rule_id
WHERE t.run_id = :run AND t.unit_key = :unit_key
ORDER BY t.id;
```

## 10. The trace as rows (T3)

How [trace unit T3](trace.md#t3-normal-affine-transformation) lands in the tables, in one finished
run (ids illustrative; keys abbreviated).

`kb.segment` (rendition of `special/Normal.html`):

| key | kind | parent | attrs |
|---|---|---|---|
| `seg:n-rel1` | `unit` | section | `{"id": "rel1", "class": ["unit"]}` |
| `seg:n-rel1-p` | `paragraph` | `seg:n-rel1` | `{"class": ["math"]}` |
| `seg:n-rel1-d` | `details` | `seg:n-rel1` | `{}` |
| 8 × `math_inline` | `math_inline` | `seg:n-rel1-p` | `{"latex": "\\mu"}` … |

`kb.entity`:

| key | type | label | kind | scope | scope segment |
|---|---|---|---|---|---|
| `stm:rel1` | `Statement` | theorem rel1 | `theorem` | local | `seg:n-rel1` |
| `stm:rel1-proof` | `Statement` | proof of rel1 | `proof` | local | `seg:n-rel1-d` |
| `ent:X@rel1` | `RandomVariable` | X | — | local | `seg:n-rel1` |
| `ent:Y@rel1` | `RandomVariable` | a + b X | — | local | `seg:n-rel1` |
| `ent:normal` | `DistributionFamily` | normal distribution | — | global | — |

A statement's kind is its `kind` column, a field chosen by consolidation (D1 §4.1); its `attrs`
are empty, because a statement is keyed by its anchor locator and first-sentence ordinal, not by
identity attributes.

The statement and local-entity keys hash locators, not segment keys (D1 §3.4, §10.1): `stm:rel1`
is the document key, the anchor locator `#rel1` and first-sentence ordinal 1; `stm:rel1-proof`
anchors at the `details` block, which has no id, so its locator is `@details:` with the shortest
unique prefix of its text; `ent:X@rel1` is the type, the scope locator `#rel1` and the symbol `X`.
They survive any rendition change that leaves those locators unchanged. The scope segment column
names the segment row of the run's rendition, and the `seg:` keys above are physical, so they
change with the rendition.

`kb.claim` (`statement_id` = `stm:rel1` for C1–C3 and D1; for the structural claim C4 it is its
subject statement, `stm:rel1-proof`, so the `proves` claim the Siegrist profile synthesizes from
the `details` block and one the author states share a key, D1 §5.5):

| key | subject | predicate | object | qualifiers (abridged) | role | status | establishment |
|---|---|---|---|---|---|---|---|
| `clm:C1` | `ent:X@rel1` | `stat:has_distribution` | `ent:normal` | `{"modality":"supposed","param_values":{"mean":{"t":"formula","latex":"\\mu",…},"variance":{"t":"formula","latex":"\\sigma^2",…}}}` | premise | accepted | stated |
| `clm:C2` | `ent:Y@rel1` | `stat:defined_as` | value `{"t":"formula","latex":"a + b X",…}` | `{"modality":"defined","conditions":{"op":"and","args":[member(a, ℝ), member(b, ℝ∖{0})]}}` | definiens | accepted | stated |
| `clm:C3` | `ent:Y@rel1` | `stat:has_distribution` | `ent:normal` | `{"param_values":{"mean":{…"latex":"a + b \\mu","symbols":{"mu":{"bind":"param_of","claim":"clm:C1","param":"mean"}}},"variance":{…}},"conditions":{"op":"and","args":[{"op":"claim","ref":"clm:C1"},{"op":"member","x":{…"a"},"set":{…"\\R"}},{"op":"member","x":{…"b"},"set":{…"\\R \\setminus \\{0\\}"}}]}}` | conclusion | accepted | stated |
| `clm:C4` | `stm:rel1-proof` | `core:proves` | `stm:rel1` | `{}` | — | accepted | stated |
| `clm:D1` | `ent:Y@rel1` | `stat:has_distribution` | `ent:normal` | `{"param_values":{"mean":…,"standard_deviation":{…"latex":"\\lvert b \\rvert \\sigma"}}, "conditions": …}` | conclusion | accepted | derived |

`kb.claim_link`: `clm:D1 derived_from clm:C3` with `detail {"rule": "stat.variance_to_sd"}`.

`kb.claim_evidence` for `clm:C3`: the span "then \(a + b X\) is normally distributed with mean
\(a + b \mu\) and variance \(b^2 \sigma^2\)" (primary), the spans "\(a \in \R\)" and
"\(b \in \R \setminus \{0\}\)" (condition).

## 11. Volume and growth

The first-pass chapters hold about 2,500 units; at a few dozen observations and ten to twenty
claims per unit, a run is on the order of 10⁵ observations and 10⁴–10⁵ claims. Every query
pattern above is index-backed at that scale. Growth axes to watch, qualitatively: observations
grow with methods × units × iterations, so reuse (D6 §4) matters more than indexes; claims grow
per run, so old non-promoted runs should be deleted after their experiments close. No
partitioning is needed until a project holds many corpora.

## 12. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D3-1 | Lexical search: index and query form | **Answered** (2026-10-28): BM25 through pg_textsearch 1.5.1, installed (§5): one partial `bm25` index per text-search configuration over one block level, queried by named index; syntax source-read (store note §6) and documented (overview); S6 runs it on the corpus and checks the planner uses the partial index |
| OPEN-D3-2 | Embedding model and dimension (Qwen3-Embedding-0.6B at 1024, or 8B truncated by Matryoshka to 1024 or 2048) | Spike S7 |
| OPEN-D3-3 | Whether `kb.segment.text` duplicated from the canonical text is worth its space, or a generated substring view suffices | **Answered by mechanism** (2026-10-28): the BM25 index reads same-row text, and neither an index nor a generated column can read `kb.rendition`; the column stays |
| OPEN-D3-4 | Whether claim keys need a stable cross-run `meaning_key` that ignores `statement` (to compare the same fact stated in two places) | Spikes S6 and S0; phase 1 goldens if S0 has too few units; S0 evidence (2026-10-28): on 70 aligned claim pairs, meaning keys agreed for 41 (54 after the D1 §10.1 key-rule changes) against 21 (48) for claim keys. Migration 0001 has no meaning-key column; one is added only if an `s6.*` record calls for it (design authority, 2026-10-28) |
