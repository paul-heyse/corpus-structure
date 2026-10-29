# D3 · Database

**Proposed (2026-10-28).** The physical realization of [D1](D1-knowledge-representation.md) and
of the operations model in one PostgreSQL 18 database. PostgreSQL is the transactional authority for
instances; the structure and meaning of the tables are the model's (ADR-0020, ADR-0021). The
database's DDL is **generated**: SQLAlchemy `MetaData` from the model's `system` and `core` modules
(`model/system.yaml`, `model/core.yaml`) into `core/db/_tables.py`, plus the hand-written physical
overlay `core/db/overlay.py`, from which migration 0001 is generated once and then frozen. This
document is not the DDL authority. Its SQL blocks state the target relational shape for the model
to declare, in DDL form because that is the shape a reader checks; the S6-tested DDL is the
reference the first generated `MetaData` is compared against (a pglast-normalized port check,
probe Q-3 and package P0-M-2). Once the generated rendering exists, this document cites it by model
revision and keeps only the explanatory prose. Column comments that would repeat D1 are omitted.
> Decision: [ADR-0020](../adr/0020-one-model-generated-projections.md), [ADR-0021](../adr/0021-instance-and-structure-authorities.md)

## 1. Choices

| Need | Choice | Why not the alternatives |
|---|---|---|
| Authority for instances of knowledge, operations and evaluation | PostgreSQL 18.6 (installed) | One transaction links a task, its observations and the claims they change. A graph or triple store would add a second authority to keep in sync; claims with qualifiers fit relational rows plus JSONB |
| Authority for structure and meaning | The model (`model/core.yaml`, `model/system.yaml` and the packs; ADR-0020); the database enforces what the generated projection declares | D3's DDL text as the authority keeps two writable sources (the hand-ported `core/db` and this document) joined only by review |
| Relationships and decision-relevant scalars | Relational: FK columns, edge tables (`kb.claim_ref`, `kb.claim_entity_ref`), identity rows (`kb.entity_identity`), `ExternalReference` rows; modality, polarity and attribution as `kb.claim` columns (§5) | References inside JSONB leave integrity to repository assertions and joins to JSON paths |
| Values: conditions, values with bindings, schema qualifier maps, observation payloads, configs | typed `jsonb`, each class governed by the model and, where the row outlives a model revision, by the payload-schema registry (`payload_schema_id`, §3); GIN indexes only where queried | Variation lives in data, not in per-type tables (the old repository's 277 contract classes); recursive and tagged values have no lossless relational form |
| Similarity search | pgvector 0.8.7 (installed), `halfvec`, HNSW | Joins and filters in one query. HNSW on `halfvec` supports up to 4,000 dimensions; the embedding dimension is fixed by spike S7 (`OPEN-D3-2`) |
| Lexical search | BM25 through pg_textsearch 1.5.1 (installed: Debian `postgresql-18-pg-textsearch`): a `bm25` partial index over one block level, ranked top-k queries (§5) | Replaces the old Tantivy crate inside the one authority, with no second index to synchronize. Built-in full-text search (`tsvector`, `ts_rank_cd`) has no corpus-level term weighting. Needs preloading and a superuser once (§3; `OPEN-D3-1`) |
| Graph traversal | Recursive CTEs; NetworkX and pgmpy projections in memory | The knowledge graph is small per project; path-heavy workloads would revisit this |
| Set-based consolidation steps, analytics and evaluation reports | DuckDB 2.0 in process, with no persistent state, over model-typed Arrow relations of the pool loaded as of the run's cut; beside a Python reference implementation that must be set-equal (ADR-0021). Analytics and run diffs read Parquet exports | Never a second authority. Identity and canonical forms stay in Python. The `postgres` extension maps unconstrained NUMERIC to DOUBLE, so pool loads go through ADBC or psycopg |
| Originals | Content-addressed files under `data/originals/<sha256>`; the corpus stays where it is and is referenced by path and hash | Keeps large binaries out of the database |
| Access from Python | SQLAlchemy Core 2.1 `MetaData` generated from the model (`core/db/_tables.py`) plus the physical overlay (`core/db/overlay.py`: indexes and partial predicates, BM25 and HNSW, views, the extension assertion; bound by name, failing at import on a missing table or column) + psycopg 3 (COPY for bulk writes) | Same stack as before, without ORM. `gen-sqltables` is not used: native enums, no CHECKs, no JSONB |
| Migrations | Alembic; 0001 generated once from the generated `MetaData` plus overlay, then frozen (it never imports `core/db`); every revision linked to the model revision it realizes (D2 §8) | `alembic check` compares an index's uniqueness and columns only (no `USING`, `WITH`, operator classes or partial `WHERE`, CHECKs by name), so a test compares the catalog after `upgrade head` with `create_all` ([store note](../design_review/evidence/2026-10-28_library-store/README.md) §1) |
| Connections | one psycopg-pool `ConnectionPool` per process; SQLAlchemy borrows through `creator=pool.getconn` with `NullPool` | One owner of connections; `SET LOCAL`, never session `SET`; the JSON serializer set in the pool's `configure` callback, which `create_engine(json_serializer=)` does not reach (store note §3, §5) |

Identifiers are `bigint GENERATED ALWAYS AS IDENTITY`. Deterministic keys from D1 §10 are
`text` columns with unique constraints where identity must hold. **Closed value sets have two
lifecycles** (D2 §3.4, `ci:lifecycle`):
- **Static sets** change with code (statuses, unit types, stages, skip reasons, segment kinds,
  delimiting statuses, polarity, link types, evidence roles, observation kinds). They are `text`
  columns with an explicitly named `CHECK`, never PostgreSQL enum types; the name carries a digest
  of the member list, so a member change is a drop and an add that Alembic's opt-in
  `checkconstraint_byname` detects, and adding a member is a generated one-line migration.
- **Schema-version-scoped sets** can be extended by packs (statement kinds, `ClaimModality`, entity
  classes, predicates and schema qualifiers, pack enums). They are per-version member rows (§3) that
  the referencing rows reach through composite foreign keys `(schema_version_id, value)`, so a value
  outside the row's schema version is refused by the store (INV-03 for predicates). `ClaimModality`
  is version-scoped: core members plus pack members with their member properties, so a pack's
  business modality needs only a pack declaration.

Invariant templates (`ci:invariant`) become CHECKs beside their generated validators. The same-run
foreign keys (INV-03, INV-08; §5) are enforced by FK or, if probe Q-4 shows a material COPY cost, by
the bulk-write primitives with a test per invariant; the tables are the same either way.
> Decision: [ADR-0020](../adr/0020-one-model-generated-projections.md), [ADR-0021](../adr/0021-instance-and-structure-authorities.md)
> Status: **Proposed** (2026-10-28). `checkconstraint_byname` is **Interface-checked** (installed
> Alembic 1.20.0, 2026-10-28); `gen-sqltables`' native enums and missing CHECKs and JSONB are
> **Interface-checked** (installed LinkML 1.12.1, 2026-10-28)

## 2. Layout

Four PostgreSQL schemas:

| Schema | Holds | D1 plane |
|---|---|---|
| `meta` | Projects, schema versions and their declarations, guideline versions | Schema |
| `kb` | Documents, renditions, segments, spans, embeddings, observations, entities, claims | Evidence, entities, claims, provenance |
| `ops` | Methods, configurations, policies, runs, tasks, measurements, interventions, experiments | Operations |
| `eval` | Golden sets, units and items; alignments; results | Evaluation |

Creation order follows foreign keys: `meta.model_revision`, `meta.payload_schema`,
`meta.project`, `meta.schema_version`, its per-version member tables, `meta.compiled_artifact`, `meta.guideline_version`, `ops.method`, `ops.method_config`,
`ops.policy_version`, `ops.policy_rule`, `ops.debug_slice`, `ops.run`, `kb.document`,
`kb.rendition`, `kb.segment`, `kb.span`, `ops.task`, `kb.rendition_build`, `kb.observation`, then
the rest.

## 3. `meta`: schema, guidelines and domain declarations

**Extensions.** Phase 0 needs `pg_textsearch` (1.5.1, installed from the Debian package
`postgresql-18-pg-textsearch`) for BM25 lexical search (§5); `vector` arrives with `kb.embedding`
in phase 1. pg_textsearch loads only through `shared_preload_libraries`, and neither extension is
trusted, so the project's roles cannot create them. `just db-provision` (§13) therefore preloads
pg_textsearch in the cluster's configuration and creates both extensions as `postgres` in the
template database `cs_template`, which `ci db init` and the test databases clone. Migration 0001
does not create an extension: the overlay's extension assertion checks that each expected
extension is present at its expected version, read from the one record of expected extension
versions (DA-018), and fails naming `just db-provision` (design authority, 2026-10-28;
[store note](../design_review/evidence/2026-10-28_library-store/README.md) §0, L-S5;
[overview](../libraries/postgresql-18-pg-textsearch.md) §11.2).
> Status: **Tested** (S6, 2026-10-28, PostgreSQL 18.6 on the interim project-local cluster): as a
> non-superuser in a database cloned from the template, `CREATE EXTENSION` of either extension
> fails with `42501`, the assertion fails with `P0001` and its instruction in a database without
> pg_textsearch, and D3's DDL of §3–§8 (before the model's additions) with fixes F1 (the `::regconfig` cast, §5) and F2 (the
> segment kind CHECK, §5) applies with 0 errors in 73 statements; `task_unit` and the
> per-`target_type` HNSW indexes came after that copy
> ([s6.ddl](../design_review/evidence/2026-10-28_design-spikes/records/s6.ddl.json)). Provisioning
> by `just db-provision` and the version-checking assertion are **Proposed** (2026-10-28)

**Instance.** The project runs on one dedicated PostgreSQL 18 cluster on this machine, apart
from the `main` cluster that other projects use (§13). Its provisioning creates the extensions
as `postgres` in the template database; the project's roles never need superuser. Another
server is used by setting `CORPUS_DATABASE__URL`.

```sql
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_extension WHERE extname = 'pg_textsearch') THEN
    RAISE EXCEPTION 'pg_textsearch is missing or not at its expected version: run just db-provision, then clone the database from cs_template';
  END IF;                                        -- the overlay's assertion; the version check reads the expected-versions record
END $$;

CREATE SCHEMA meta;  CREATE SCHEMA kb;  CREATE SCHEMA ops;  CREATE SCHEMA eval;

CREATE TABLE meta.model_revision (               -- projection of model/revisions.yaml (D2 §2, §8); rows are added, never edited
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  label         text NOT NULL,                   -- LinkML version of core and system
  content_hash  text NOT NULL UNIQUE,            -- canonical JSON of the parsed core and system files (D2 §2)
  compilers     jsonb NOT NULL,                  -- compiler name → version
  key_scheme    integer NOT NULL,                -- ci:key_scheme (D1 §10.1)
  parent_id     bigint REFERENCES meta.model_revision,
  change_record jsonb,                           -- D2 §8; null for the first revision; the model source stays in Git
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE meta.payload_schema (               -- one version of one nested payload class (D2 §8); rows are added, never edited
  id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  model_revision_id   bigint NOT NULL REFERENCES meta.model_revision,
  class               text NOT NULL,             -- prefixed class name, e.g. 'core:MentionPayload'
  kind                text NOT NULL,             -- what it is the payload of: an observation kind, a compiled-artifact kind, ...
  version             integer NOT NULL,
  parent_id           bigint REFERENCES meta.payload_schema,
  compatibility_class text NOT NULL,             -- D2 §8: descriptive, nested-additive, mapped, ...
  json_schema_id      text NOT NULL,             -- $id of the generated JSON Schema
  arrow_schema        bytea NOT NULL,            -- Schema.serialize()
  sql_visible_paths   text[] NOT NULL DEFAULT '{}',
  upcaster            text,                      -- the upcast from the parent version; null for an initial version
  reason              text NOT NULL,
  authorized_by       text NOT NULL,             -- the model rule permitting the change, e.g. 'method_version:mention.gliner/3'
  UNIQUE (class, version)
);

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
  content_hash  text NOT NULL,                   -- D2 §2; covers the model revision id
  model_revision_id bigint NOT NULL REFERENCES meta.model_revision,   -- the core the pack was compiled against
  parent_id     bigint REFERENCES meta.schema_version,
  source        jsonb NOT NULL,                  -- the pack files' text: {"statistics.yaml": "...", "rules.yaml": "...", "core/rules.yaml": "..."}; the core module is named by model_revision_id
  migration     jsonb,                           -- the change record from the parent (D2 §8); null for a first version
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
  payload_schema_id bigint NOT NULL REFERENCES meta.payload_schema,   -- the body's schema (D2 §8)
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (schema_version_id, compiler, compiler_version, kind)
);

CREATE TABLE meta.schema_class (
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version ON DELETE CASCADE,
  name          text NOT NULL,                   -- prefixed: 'stat:RandomVariable', 'core:Statement'
  parent        text,                            -- prefixed
  kind          text NOT NULL CHECK (kind IN ('entity','value','abstract')),
  scope         text CHECK (scope IN ('global','local')),
  identity_keys text[] NOT NULL DEFAULT '{}',
  description   text,
  annotations   jsonb NOT NULL DEFAULT '{}',
  PRIMARY KEY (schema_version_id, name)
);

CREATE TABLE meta.schema_slot (
  schema_version_id   bigint NOT NULL REFERENCES meta.schema_version ON DELETE CASCADE,
  name                text NOT NULL,             -- prefixed: 'stat:has_distribution'; a class-local attribute '<prefix>:<Class>.<attr>', e.g. 'core:Formula.latex'
  role                text NOT NULL CHECK (role IN ('predicate','qualifier','identity','field')),
  domain_class        text,                      -- prefixed class name
  range               text,                      -- prefixed class or enum name, or a built-in type ('string', 'integer', ...)
  object_kind         text,                      -- derived from the range (D2 §3): formula, set, entity, enum, map, condition, ...
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

-- one member table per schema-version-scoped closed set (§1), the target of composite FKs; the
-- generator names them, these two are phase 0's
CREATE TABLE meta.statement_kind (
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version ON DELETE CASCADE,
  value             text NOT NULL,               -- core or pack member, e.g. 'definition', 'toy:clause'
  properties        text[] NOT NULL DEFAULT '{}',   -- member properties (D2 §3.4), e.g. '{claim_bearing}'
  PRIMARY KEY (schema_version_id, value)
);

CREATE TABLE meta.claim_modality (
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version ON DELETE CASCADE,
  value             text NOT NULL,               -- 'asserted', 'supposed', 'cited', ..., or a pack member
  properties        text[] NOT NULL DEFAULT '{}',   -- premise_forming, attribution_identifying, conflict_bearing
  PRIMARY KEY (schema_version_id, value)
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

**Revisions and the payload-schema registry** (ADR-0022). `meta.model_revision` projects the
checked-in revision log, the authority, and is written by the schema registry's `ensure`; it stores
the content hash and change record, not the model source, which stays in Git at the revision. Every
schema version names the model revision it was compiled against, and every run records both (§4).
`meta.payload_schema` holds each version of each nested payload class. The rows that outlive a model
revision carry a `payload_schema_id`: `kb.observation`, `kb.rendition_build` (its `parse_detail`),
`meta.compiled_artifact` (its body), `ops.intervention` (its `refs`) and `eval.golden_pass`. Readers
dispatch on it and refuse an unknown id; per-run materialized rows inherit the run's recorded
revision, schema version and key scheme and carry no id of their own.
> Status: **Proposed** (2026-10-28)

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

**The `meta.schema_*` tables and the member tables are a projection** of the schema-table
artifact (D2 §7.1). When a schema-table compiler version adds its `meta.compiled_artifact` row for
a schema version, that version's `schema_class`, `schema_slot`, `schema_enum`, `schema_rule` and
member rows are **upserted** from it. No run reads them as input: methods read compiled artifacts by
hash, so the projection changes nothing a run computed. They serve SQL joins from claims to their
schema definitions, the grouping of metrics by class and predicate, and, since the model's
relational projection, the composite foreign keys of version-scoped values (`kb.claim.predicate` to
`meta.schema_slot`, `kb.entity.kind` to `meta.statement_kind`, `kb.claim.modality` to
`meta.claim_modality`). Because rows reference them, a compiler change that would remove a name
still referenced fails, which exposes a change that would orphan data.
> Decision: [ADR-0020](../adr/0020-one-model-generated-projections.md), [ADR-0022](../adr/0022-schema-change-modelled.md)
> Status: **Proposed** (2026-10-28). The path from pack to rows is **Tested** (S6, 2026-10-28):
> S4's compiled tables for schema version 0.2.0 register with their content hash and artifact
> hashes recomputed (4 of 4), all 148 compiled rows insert, and the twelve v1 core units inserted
> against that version agree with it on predicates, types and value kinds
> ([s6.dry-run-2](../design_review/evidence/2026-10-28_design-spikes/records/s6.dry-run-2.json))

**One spelling of schema names: prefixed everywhere** (operator, 2026-10-28, on S6). A class,
slot or enum is named by its prefixed name (`stat:RandomVariable`, `core:Statement`,
`stat:param_values`, `core:modality`, `core:ParseStatus`) in every place that names it: the
compiled rows (`schema_class.name` and `parent`, `schema_slot.name`, `domain_class`, `range`,
`qualifiers` and `identity_qualifiers`, `schema_enum.name`), `kb.entity.type`, `kb.claim.predicate`
and the keys of `kb.claim.qualifiers` (§6.1). The SQL joins from claims and entities to their
schema definitions are then plain equalities. The schema-table compiler emits the names
([D2 §7.1](D2-schema-and-guidelines.md#71-to-schema-tables), "To schema tables"), and the
repository writes rows in the same spelling: the model-facing batch writes local names, unique
within a schema version, and the stored form carries the prefixed ones
([D2 §7.3](D2-schema-and-guidelines.md#73-to-json-schema-for-llm-claim-proposals), Names). Names
inside a value are not schema names and keep their own spelling: the keys of a parameter map
(`mean`, `variance`), a condition tree's `op`, a value's `t`.
> Status: **Proposed** (2026-10-28). The mismatch it removes is **Tested** (S6, 2026-10-28): with
> bare types and qualifier keys beside prefixed compiled names, 6 entity types and 5 (predicate,
> qualifier) pairs matched only once prefixed, and 43 `domain_class`/`range` values in the compiled
> rows were bare while class names were prefixed ([s6.dry-run-2](../design_review/evidence/2026-10-28_design-spikes/records/s6.dry-run-2.json))

**Class-local attributes are named by their class.** An attribute of a value class (`v` of
`NumberValue`, `BoolValue` and `TextValue`, `latex` of `Formula`) is a `meta.schema_slot` row named
`<prefix>:<Class>.<attr>` (`core:NumberValue.v`, `core:Formula.latex`) with `domain_class` its
class, so the key `(schema_version_id, name)` holds one attribute name under several classes
without a further key column; free slots keep their plain prefixed names.
> Status: **Tested** (S6, 2026-10-28): S4's compiled tables carry 29 such rows, and all insert
> under the key ([s6.dry-run-2](../design_review/evidence/2026-10-28_design-spikes/records/s6.dry-run-2.json));
> the convention is **Proposed** (2026-10-28)

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
  unit_type         text NOT NULL CHECK (unit_type IN (/* generated from TaskUnitType, as ops.task.unit_type */)),   -- the chain's default or the entry's own (D6 §7.1)
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
  options              jsonb NOT NULL DEFAULT '{}',  -- the resolved run options (an explicit option, else a result-neutral setting's default, else the model default): agent_mode, agent_reuse, fresh methods, gpu_mode (a GpuMode member), corpus (a slice, default 'first-pass'), scope (a slice naming the units routed, with its resolved unit list and that list's hash; the kind stays, so the run can be promoted) (D6 §2, §4, §5, §8)
  debug_slice_id       bigint REFERENCES ops.debug_slice,
  corpus_hash          text NOT NULL,            -- over the corpus's (document key, content hash) set and the ingest config hash (below)
  model_revision_id    bigint NOT NULL REFERENCES meta.model_revision,   -- the revision the run ran under; a run under another installed revision is refused (D2 §8)
  schema_version_id    bigint NOT NULL REFERENCES meta.schema_version,
  key_scheme           integer NOT NULL,         -- the key scheme of the run's keys (D1 §10.1); per-run rows inherit it
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
  cut_at               timestamptz,              -- the run's knowledge cut: stamped once by the seal (D6 §3.1, §8); fates are read against it
  cut_m19_task_id      bigint,                   -- the final M19 task, recorded once by the seal; its outputs are read by this id (§8); FK added after ops.task (§5)
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

**A run records the revisions it ran under**: its model revision, schema version and key scheme,
beside its reference run and its resolved options, all written at insert. Its materialized rows
inherit them. The cut columns are written once by the seal that cuts the run's knowledge (D6 §3.1,
§8).

**Closed sets are generated.** `stage` takes the modelled `Stage`, `reason` the modelled
`SkipReason`, and `ops.task.unit_type` and `ops.policy_rule.unit_type` the one `TaskUnitType`
(which `Method.unit_type` shares, D4 §1); each is a static set with a digest-named CHECK (§1), so a
misspelt stage, reason or unit type fails the write instead of forming its own coverage group.
> Decision: [ADR-0022](../adr/0022-schema-change-modelled.md)
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
  parse_status   text NOT NULL CHECK (parse_status IN ('ok','partial','failed')),   -- from its segments: delimiting status, never 'ambiguous' (below)
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (document_id, content_digest)
);

CREATE TABLE kb.segment (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  rendition_id bigint NOT NULL REFERENCES kb.rendition ON DELETE CASCADE,
  key          text NOT NULL UNIQUE,             -- 'seg:…'
  parent_id    bigint REFERENCES kb.segment,
  kind         text NOT NULL CHECK (kind IN ('document','section','unit','paragraph','list','list_item','details',
                    'math_display','math_inline','heading','table','table_row','table_cell','caption','footnote',
                    'figure','sentence','email_message','quoted_block','signature')),   -- D1 §3.2
  ordinal      integer NOT NULL,                 -- position among siblings
  depth        integer NOT NULL,
  start_offset integer NOT NULL,
  end_offset   integer NOT NULL,
  text         text NOT NULL,                    -- canonical_text[start:end], stored for search
  ts_config    regconfig NOT NULL DEFAULT 'english',   -- from the source profile's language (default 'english'), selecting its BM25 index; not content
  attrs        jsonb NOT NULL DEFAULT '{}',      -- author markup (D1 §3.2); never diagnostics, which live in kb.rendition_build.parse_detail
  parse_status text NOT NULL DEFAULT 'ok' CHECK (parse_status IN ('ok','partial','failed')),   -- delimiting status (D1 §3.1–§3.2), never 'ambiguous'
  parse_reason text,                             -- why `partial`/`failed` (delimiting, D1 §3.1); content, inside the digest
  CHECK ((parse_status = 'ok') = (parse_reason IS NULL)),
  CHECK (start_offset <= end_offset)
);
CREATE INDEX segment_range ON kb.segment (rendition_id, start_offset, end_offset);
CREATE INDEX segment_kind  ON kb.segment (rendition_id, kind);
-- BM25 over one non-overlapping block level, so a token is counted once and hits do not nest
-- (store note L-S3); one partial index per text-search configuration; the regconfig literal is
-- cast, because regconfig = unknown resolves to oid = oid (S6)
CREATE INDEX segment_bm25 ON kb.segment USING bm25 (text) WITH (text_config = 'english')
  WHERE kind IN ('paragraph','heading','list_item','caption') AND ts_config = 'english'::regconfig;

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
  vec             halfvec(1024) NOT NULL,        -- dimension fixed by S7 (OPEN-D3-2): 1024 or 2048
  UNIQUE (target_type, target_id, model_config_id)
);
-- one partial HNSW index per target_type, queried with SET LOCAL hnsw.iterative_scan = relaxed_order (below)
CREATE INDEX embedding_hnsw_segment ON kb.embedding USING hnsw (vec halfvec_cosine_ops) WHERE target_type = 'segment';
CREATE INDEX embedding_hnsw_entity  ON kb.embedding USING hnsw (vec halfvec_cosine_ops) WHERE target_type = 'entity';
CREATE INDEX embedding_hnsw_alias   ON kb.embedding USING hnsw (vec halfvec_cosine_ops) WHERE target_type = 'alias';
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

**Segment kinds and parse statuses are closed sets.** `kb.segment.kind` is checked against the
D1 §3.2 kinds, which the BM25 partial index's kind list relies on. `kb.segment.parse_status` and
`kb.rendition.parse_status` are **delimiting** statuses (D1 §3.1–§3.2): `ok`, `partial` or
`failed`. They are not the compiled `core:ParseStatus` enum, which is the range of a formula
value's `parse` outcome (D1 §6.1) and adds `ambiguous` (a grammar reading a formula in more than
one way); that outcome lives in values inside observation payloads and claims, never in a
segment column, so the two CHECK lists differ by design and no CHECK is generated from the enum.
> Status: the kind CHECK **Tested** (S6, 2026-10-28): D3's block lacked the CHECK its comment
> promised; with it, the constraint sweep's bad rows are refused and every kind S1 emits on the
> four spike pages inserts ([s6.ddl](../design_review/evidence/2026-10-28_design-spikes/records/s6.ddl.json),
> [s6.constraints](../design_review/evidence/2026-10-28_design-spikes/records/s6.constraints.json));
> the parse-status split is **Proposed** (2026-10-28), answering S6's finding that the compiled
> enum has `ambiguous` and these CHECKs do not ([s6.dry-run-2](../design_review/evidence/2026-10-28_design-spikes/records/s6.dry-run-2.json))

**Lexical search** (OPEN-D3-1) is BM25 through pg_textsearch, for the `find` query (D8 §5.1) and
candidate lookup for linking. A query always names the index and repeats its predicate in the
same form, `'english'::regconfig` cast included, because the implicit string form skips partial
BM25 indexes, and a bound parameter defeats it in any case
([overview](../libraries/postgresql-18-pg-textsearch.md) §3.3; store note §6):

```sql
SELECT s.id, s.key, s.text <@> to_bm25query(:q, 'kb.segment_bm25') AS score
FROM kb.segment s
WHERE s.kind IN ('paragraph','heading','list_item','caption') AND s.ts_config = 'english'::regconfig
  AND s.rendition_id = ANY(:renditions)          -- the run's renditions (kb.run_rendition, §8)
ORDER BY s.text <@> to_bm25query(:q, 'kb.segment_bm25')
LIMIT :k;
```

- **The predicate is never omitted.** Without it, or in a form the planner cannot prove implies
  the index predicate, the query does not fail: it falls back to standalone scoring over every
  row, rows the index does not hold included. The repository therefore writes the predicate from
  one constant shared with the index definition. The uncast literal fails outright (`22P02`,
  `regconfig = unknown` resolving to `oid = oid`), as does the unqualified index name (`42704`).
- **The kind list** is one non-overlapping block level: `paragraph`, `heading`, `list_item` and
  `caption`. `math_display` is not in it: display formulas nest in paragraphs and list items, and
  a display formula placed bare in a container is already an orphan `paragraph` (D1 §3.2), so
  indexing the kind would count its text twice.
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
  postgresql_where=…)` with the predicate's `::regconfig` cast (store note §2).
- **Same-row text.** The BM25 index reads `kb.segment.text` on the same row, which is why the
  column stays (OPEN-D3-3); no index or generated column can read `kb.rendition`.

> Status: index and query **Tested** (S6, 2026-10-28, PostgreSQL 18.6 and pg_textsearch 1.5.1 on
> the interim project-local cluster, the four spike pages): with the cast predicate repeated, the
> query gives an ordered `Index Scan using segment_bm25`, the forced generic plan of a prepared
> statement uses it too, and all five probe queries use it, with negative scores ascending; the
> uncast form fails with `22P02`, the implicit string form and the unqualified index name with
> `42704`, and an omitted predicate falls back to standalone scoring without error. Under the
> earlier kind list, `math_display` segments nested in indexed paragraphs and list items put 6552 of
> 54826 non-space characters in the index twice; with `('paragraph','heading','list_item','caption')`
> the overlap is 0 and no character of the four pages is left out, the index holding 587 of 2335
> segment rows ([s6.bm25](../design_review/evidence/2026-10-28_design-spikes/records/s6.bm25.json),
> [s6.ddl](../design_review/evidence/2026-10-28_design-spikes/records/s6.ddl.json)). The kind list's
> coverage of the 78-page corpus (tables, footnotes, figures beyond one caption) is not yet checked

`ts_config` is the segment's language, set by ingest from the source profile's `language` (default
`english`, [D4 M01](D4-method-catalog.md#m01-ingesthtml)) when a rendition's segments are first
written; it is search configuration, outside the content digest (D1 §3.2).
Each configuration has its own partial BM25 index, whose `text_config` and `ts_config =
'<config>'::regconfig` predicate agree, so a second language is an additive index over rows with
another value, never a rewrite of the table or of the first index; a query chooses the index by the configuration it searches.
> Status: **Proposed** (2026-10-28)

For phase 1 (store note L-S6): `halfvec` HNSW indexes up to 4,000 dimensions (1024 and 2048 fit;
the 8B model's native 4096 does not); pgvector filters after the index scan, so `kb.embedding`
gets one partial HNSW index per `target_type`, and filtered queries set
`hnsw.iterative_scan = relaxed_order` (`SET LOCAL`), re-sorting the few rows returned when exact
order matters. Rows reference their target's row: renditions are content-addressed, so a
content-preserving re-ingest keeps every segment row and no embedding is orphaned, while a
content change makes new segments, which need new embeddings anyway.
> Status: **Measured** (S6, 2026-10-28, pgvector 0.8.7 on the interim project-local cluster, 10,000
> random unit vectors per dimension, a filtered top-10 join with the HNSW scan forced): `halfvec`
> at 1024 and 2048 dimensions loads by binary COPY and indexes (builds of 3.7 s and 7.2 s, indexes
> of 27 MB and 82 MB); recall@10 without iterative scan is 0.15–0.22, with `relaxed_order` 0.80–0.87
> (median 1.6–3.4 ms) and with `strict_order` 0.41–0.47, global or per-`target_type` index alike;
> at that size the planner prefers an exact scan (recall 1.0, about 0.7 ms)
> ([s6.vectors](../design_review/evidence/2026-10-28_design-spikes/records/s6.vectors.json)). Random
> vectors are a worst case for recall; the dimension, `ef_search` and recall with real embeddings
> wait on S7 (OPEN-D3-2), and the design is **Proposed**

`kb.embedding` is created by the phase 1 migration that adds M04, not by 0001: nothing reads it in
phase 0, and its dimension waits on S7 (P11 in the design rationale). The rest of this section is
migration 0001.

`ops.task` sits here in creation order because observations reference it:

```sql
CREATE TABLE ops.task (
  id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id           bigint NOT NULL REFERENCES ops.run,
  stage            text NOT NULL CHECK (stage IN (/* generated from Stage: the stage names of D6 §2 */)),
  unit_type        text NOT NULL CHECK (unit_type IN ('document','rendition','segment','span','observation','entity','claim',
                        'alternative_group','identity_group','run','golden_unit')),   -- TaskUnitType (D4 §1)
  unit_id          bigint,                       -- id in the table named by unit_type (kb.span for 'span', eval.golden_unit for 'golden_unit'); null for groups and 'run'
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
  reason           text CHECK (reason IN ('scope','limit','budget','prerequisite_failed','run_cancelled')),   -- SkipReason: why skipped, or 'run_cancelled' for a task cancelled with its run
  created_at       timestamptz NOT NULL DEFAULT now(),
  started_at       timestamptz,
  finished_at      timestamptz                   -- set by every terminal write, including creation as 'reused' or 'skipped', with clock_timestamp() after the run-row lock (D6 §3.1); fates are read against ops.run.cut_at (§8)
);
-- the queue (store note L-S1): what workers claim, what expires, what the agent leases
CREATE INDEX task_pending ON ops.task (run_id, stage, method_config_id, priority DESC, id) WHERE status = 'pending';
CREATE INDEX task_lease   ON ops.task (lease_until) WHERE status = 'running';
CREATE INDEX task_agent   ON ops.task (run_id, priority DESC, id) WHERE status = 'awaiting_agent';
CREATE INDEX task_cache ON ops.task (method_config_id, input_hash) WHERE status IN ('done','empty') AND unit_type <> 'run';   -- run-level tasks are never reused (§8)
CREATE INDEX task_run   ON ops.task (run_id, stage);
CREATE INDEX task_unit  ON ops.task (run_id, unit_key);   -- "why a method ran" (§9) and per-unit reads
ALTER TABLE ops.run ADD FOREIGN KEY (cut_m19_task_id) REFERENCES ops.task;

CREATE TABLE kb.rendition_build (                -- provenance: which adapter configurations produced a rendition
  document_id      bigint NOT NULL REFERENCES kb.document,
  method_config_id bigint NOT NULL REFERENCES ops.method_config,   -- the adapter configuration (M01 with M03)
  rendition_id     bigint NOT NULL REFERENCES kb.rendition,
  task_id          bigint NOT NULL REFERENCES ops.task,            -- the ingest task that first built it
  parse_detail     jsonb NOT NULL DEFAULT '{}',  -- exclusions, warnings, parser diagnostics: source lines, parse errors with positions (D4 M01); never on segments
  payload_schema_id bigint NOT NULL REFERENCES meta.payload_schema,   -- parse_detail's schema (D2 §8)
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
  payload_schema_id bigint NOT NULL REFERENCES meta.payload_schema,   -- the payload's class and version; readers dispatch on it (D2 §8)
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
  key               text NOT NULL,               -- 'ent:…', 'stm:…' or 'xrf:…' (D1 §10.1)
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version,
  type              text NOT NULL,               -- schema class, prefixed (§3): 'stat:RandomVariable', 'core:Statement', 'core:ExternalReference'
  label             text NOT NULL,
  scope             text NOT NULL CHECK (scope IN ('global','local')),
  scope_segment_id  bigint REFERENCES kb.segment,
  attrs             jsonb NOT NULL DEFAULT '{}', -- non-identity attributes; identity attributes are kb.entity_identity rows (below)
  kind              text,                        -- statements only: the StatementKind value (D1 §4.1, §4.3); a field like label, not identity
  reference_descriptor jsonb,                   -- ExternalReference stored descriptor; model-declared, migration 0002
  statement_ordinal integer,                   -- first-sentence ordinal; historical NULL is unknown, migration 0003
  resolved_to_id    bigint,                      -- ExternalReference only: the statement it resolved to (same run)
  confidence        real,
  UNIQUE (run_id, key),
  UNIQUE (run_id, id),                           -- target of the same-run composite FKs
  FOREIGN KEY (schema_version_id, kind) REFERENCES meta.statement_kind (schema_version_id, value),   -- version-scoped kinds (§1)
  FOREIGN KEY (run_id, resolved_to_id) REFERENCES kb.entity (run_id, id),
  CHECK ((scope = 'local') = (scope_segment_id IS NOT NULL)),
  CHECK ((type = 'core:Statement') = (kind IS NOT NULL)),
  CHECK ((type = 'core:ExternalReference') OR resolved_to_id IS NULL)
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
  predicate        text NOT NULL,                -- prefixed (§3): 'stat:has_distribution'
  object_entity_id bigint REFERENCES kb.entity,
  object_value     jsonb,                        -- D1 §6 value
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version,
  modality         text NOT NULL DEFAULT 'asserted',   -- version-scoped: FK below (§1)
  polarity         text NOT NULL DEFAULT 'positive' CHECK (polarity IN (/* generated from Polarity */)),
  attribution_entity_id bigint,                  -- the attribution qualifier's resolved entity; null: the author
  qualifiers       jsonb NOT NULL DEFAULT '{}',  -- the other core qualifiers (hedge, conditions, scope, valid_time) and the schema qualifiers; keys prefixed (§3, §6.1)
  statement_id     bigint REFERENCES kb.entity,
  statement_role   text CHECK (statement_role IN ('premise','conclusion','definiens','restriction','example_value')),
  status           text NOT NULL CHECK (status IN ('candidate','accepted','rejected','ambiguous','conflicting','unsupported')),
  establishment    text NOT NULL CHECK (establishment IN ('stated','derived','agent_asserted')),
  confidence       real,
  completeness     jsonb NOT NULL DEFAULT '{}',  -- {"unresolved_symbols": 1, "phrase_conditions": 0}
  UNIQUE (run_id, key),
  UNIQUE (run_id, id),                           -- target of the same-run composite FKs
  FOREIGN KEY (schema_version_id, predicate) REFERENCES meta.schema_slot (schema_version_id, name),        -- INV-03
  FOREIGN KEY (schema_version_id, modality)  REFERENCES meta.claim_modality (schema_version_id, value),
  FOREIGN KEY (run_id, attribution_entity_id) REFERENCES kb.entity (run_id, id),
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

-- claim → claim relationships derived from typed values: condition premises and param_of targets (INV-08)
CREATE TABLE kb.claim_ref (
  run_id          bigint NOT NULL,
  claim_id        bigint NOT NULL,
  kind            text   NOT NULL CHECK (kind IN ('condition_premise','binding_param')),
  path            text   NOT NULL,             -- JSON pointer to the node, so parallel references stay distinct (CI-03)
  target_claim_id bigint NOT NULL,
  PRIMARY KEY (claim_id, kind, path),
  FOREIGN KEY (run_id, claim_id)        REFERENCES kb.claim (run_id, id) ON DELETE CASCADE,
  FOREIGN KEY (run_id, target_claim_id) REFERENCES kb.claim (run_id, id) ON DELETE CASCADE
);
CREATE INDEX claim_ref_target ON kb.claim_ref (target_claim_id);

-- claim → entity relationships: entity-ranged qualifiers, pred arguments, binding entity targets
CREATE TABLE kb.claim_entity_ref (
  run_id    bigint NOT NULL,
  claim_id  bigint NOT NULL,
  role      text   NOT NULL CHECK (role IN ('qualifier','pred_arg','binding_variable','binding_family_param')),
  slot      text,                              -- the prefixed qualifier name for role 'qualifier'
  path      text   NOT NULL,
  entity_id bigint NOT NULL,
  PRIMARY KEY (claim_id, role, path),
  FOREIGN KEY (run_id, claim_id)  REFERENCES kb.claim  (run_id, id) ON DELETE CASCADE,
  FOREIGN KEY (run_id, entity_id) REFERENCES kb.entity (run_id, id) ON DELETE CASCADE
);
CREATE INDEX claim_entity_ref_entity ON kb.claim_entity_ref (entity_id, role);

-- identity attributes as rows, one per identity slot
CREATE TABLE kb.entity_identity (
  entity_id       bigint NOT NULL REFERENCES kb.entity ON DELETE CASCADE,
  slot            text   NOT NULL,             -- prefixed identity slot, e.g. 'stat:family'
  value_entity_id bigint REFERENCES kb.entity,
  value_text      text,                        -- canonical form under the slot's case policy
  PRIMARY KEY (entity_id, slot),
  CHECK ((value_entity_id IS NULL) <> (value_text IS NULL))
);
CREATE INDEX entity_identity_value ON kb.entity_identity (slot, value_entity_id);
```

**Relationships are relational; values stay nested** (RC06; ADR-0020). Every relationship a query
joins on or an invariant constrains is a row or a foreign key: claim → claim premise references and
`param_of` targets in `kb.claim_ref`, claim → entity references from qualifiers, `pred` arguments
and binding targets in `kb.claim_entity_ref`, identity slots in `kb.entity_identity`, attribution in
`kb.claim.attribution_entity_id`, an external reference's resolution in `kb.entity.resolved_to_id`.
The scalars that queries, slots and conflicts read (modality, polarity, attribution) are `kb.claim`
columns, NOT NULL with their model defaults, and leave `kb.claim.qualifiers`, so equal meaning still
gives equal JSON. A claim carries its schema version so that its predicate and modality reach the
version's member rows by composite foreign key (INV-03). Values stay typed JSONB governed by the
model: condition-tree structure (whose `claim` references are also projected to `kb.claim_ref`),
schema qualifier maps, values with their bindings, `valid_time` (ISO bounds, possibly partial, which
a range type would lose). A schema qualifier path that a query must filter on is declared
`sql_visible` by its pack, a relational change (D2 §8).
- **Writers.** The consolidation bulk writer writes edge and identity rows from the typed instances
  in the same transaction as their claims and entities; they are derived and never edited. Because
  they serve queries, which refuse unfinished runs, they are written at the run's final pass only.
- **Deletion.** §8's delete order holds: edge rows cascade from claims, identity rows from entities.
- **Same-run integrity** (INV-03, INV-08) is by the composite foreign keys above or, if probe Q-4
  shows a material COPY cost at run scale, by the bulk-write primitives with a test per invariant;
  the tables stay either way.
> Decision: [ADR-0020](../adr/0020-one-model-generated-projections.md), [ADR-0021](../adr/0021-instance-and-structure-authorities.md)
> Status: **Proposed** (2026-10-28). Edge rows are a few per claim, about 10⁵ per run at phase 1
> scale, the order of S6's 40,000 support and evidence rows written in 214 ms (**Measured**, S6,
> 2026-10-28, interim cluster); the cost of the composite FK checks is unmeasured (probe Q-4)

**JSONB indexes only with a query that uses them** (store note L-S4). Earlier drafts had GIN
`jsonb_path_ops` indexes on `kb.observation.payload` and `kb.claim.qualifiers`. Neither had a
consumer: §9's `qualifiers @? '$."stat:param_values".variance'` cannot use a `jsonb_path_ops`
index, which serves only `== constant` path clauses, and is carried by `claim_pred`. Every GIN
index also slows each COPY. A JSONB index is added in the migration that adds the query needing it.
> Status: **Tested** (S6, 2026-10-28): the `@?` query's index condition is `claim_pred`'s
> `(run_id, predicate)`, the path test a filter on the fetched rows
> ([s6.queries](../design_review/evidence/2026-10-28_design-spikes/records/s6.queries.json)); at run
> scale (20,000 claims, no GIN index) it returns 1410 claims in about 1.0 ms on the interim
> project-local cluster (**Measured**, [s6.volume](../design_review/evidence/2026-10-28_design-spikes/records/s6.volume.json))

**A statement row always has a kind; an external reference is an `ExternalReference` row.**
`entity_check` refuses a `core:Statement` entity without a kind. An external reference ("the last
result", "definition [1]", an author `[n]` link) names something outside the batch, so it is
neither a kind-less statement nor an `unsupported` item: it is a typed `core:ExternalReference`
entity (D1 §4.4; RC11), local, anchored at the citing statement's anchor segment, keyed `xrf:` by
the citing statement's key, the descriptor's text form and the author link target when present
(D1 §10.1). Its `kind` stays null, so the statement CHECK holds, and a resolution to a statement of
the same run sets `resolved_to_id` (D1 §4.4's `resolves_to` relation); an unresolved reference stays a
row, and a claim that cites it is served as conditional (INV-09), never dropped.
> Decision: [ADR-0020](../adr/0020-one-model-generated-projections.md)
> Status: the refusal **Tested** (S6, 2026-10-28): the v1 reference's U6 stored "the last result" as a
> Statement-typed entity without a kind; `entity_check` refused it, so it and its claim
> `c_follows` were not loaded, the only misfit of the trace and golden rows
> ([s6.constraints](../design_review/evidence/2026-10-28_design-spikes/records/s6.constraints.json)).
> The `ExternalReference` row is **Proposed** (2026-10-28)

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
  payload_schema_id bigint NOT NULL REFERENCES meta.payload_schema,   -- refs' schema (D2 §8)
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
operations JSON, the citation frame and the generic stored items of D1 §10.3) are classes of the
model (`model/core.yaml`, `model/system.yaml`; ADR-0020) projected to the core Pydantic models, and
`corpus_structure/core/schemas/*.json` ([D9 §1](D9-repository-and-phase0.md#1-layout)) are
generated from them, with a `$id` naming the model revision, and hold only those shapes. Where a
row outlives a model revision, its JSONB carries a `payload_schema_id` (§3), and readers dispatch
on it. What a predicate contributes (its object value
and its qualifiers, schema qualifiers included) is typed by the per-version models compiled from
the run's schema version, which are compiled artifacts (§3), not files in `core/schemas`
([schema-rules note](../design_review/evidence/2026-10-28_library-schema-rules/README.md) L-10).
Defaults are filled for rules and omitted in storage through `Field(exclude_if=…)` (L-11).
> Status: **Proposed** (2026-10-28)

Summaries of the shapes:

### 6.1 Values, qualifiers, conditions

- **Value** (`kb.claim.object_value`, values inside qualifiers and conditions): D1 §6, tagged by
  `t`.
- **`kb.claim.qualifiers`**: an object whose keys are prefixed qualifier slot names (§3): the core
  qualifiers that stay nested (`core:hedge`, `core:conditions`, `core:scope`, `core:valid_time`) or
  schema qualifiers valid for the predicate in the run's schema version (`stat:param_values`);
  values are D1 §6 values, maps of values (`stat:param_values`, whose own keys are parameter names,
  `mean`, `variance`), or the condition tree (`core:conditions`, D1 §7). `core:modality`,
  `core:polarity` and `core:attribution` are the `kb.claim` columns `modality`, `polarity` and
  `attribution_entity_id` (§5) and never appear here, so equal meaning still gives equal JSON; each
  qualifier's store placement is its qualifier specification's (D2 §6).
- **Condition tree**: D1 §7. `claim` nodes carry claim **keys**; readers resolve them within the
  same run, and each is also a `kb.claim_ref` row with its path (§5).
> Decision: [ADR-0020](../adr/0020-one-model-generated-projections.md)

### 6.2 Observation payloads, by kind

Each observation kind has one payload class in the model (`ci:payload: <kind>`, D2 §3.4), registered
by version in `meta.payload_schema` (§3); the class, not this document, is the field-level contract.
Today the classes are `core/payloads.py` (`PAYLOADS`, one model per kind; **Implemented**, P0-F-2b),
which the model's payload classes generate or replace at Stage A and B (ADR-0020). What each kind is
for:

- **`author_markup`**: author markup on a segment (M01); on a block the source profile marks for
  synthesis, it also carries the claim its containment states, which consolidation turns into a
  claim (D4 M01, D5 §3.5).
- **`mention`**, **`relation`**, **`record`**, **`attribute`**, **`classification`**: encoder
  outputs (M05–M07, M09) as spans, labels and scores; `math` on M09's symbol mentions holds the
  occurrence's decoration.
- **`value`**: a parsed value (M11), with its `math_kind`, the typed start symbol that read the span.
- **`scope`**: a binding site and its scope (M13). A payload that refers to another task's mentions
  records their offsets beside each reference, so a reused task's references match by offsets (§6.3).
- **`link`**: an entity-link candidate for a mention (M14) or a pair (M15).
- **`claim_proposal`**: a stored-form batch on the observation's rendition (D2 §7.3). For authored
  proposals (M10, the agent) the model-facing batch as submitted and its citation frame are the
  authority, and the stored batch is derived from them by the quote cascade (D4 §4.3); the payload
  records the cascade version and the schema version that derived it (D2 §8). M23's derived
  proposals record their rule and sources.
- **`judgment`**: a decision on an observation, claim or group, under a guideline version; its
  target records the key scheme of the key it names (D1 §10.1).
- **`verification`**: a verifier's verdict on a claim; M19 writes only failing outcomes (D5 §8.1).
> Decision: [ADR-0020](../adr/0020-one-model-generated-projections.md), [ADR-0022](../adr/0022-schema-change-modelled.md)
> Status: the payload classes **Implemented** in `core/payloads.py` (P0-F-2b, 2026-10-28); their
> place in the model, the registry and the recorded derivation are **Proposed** (2026-10-28)

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
  batch                jsonb NOT NULL,           -- model-facing ClaimProposalBatch as authored (pass c: the adjudicated batch); never rewritten
  decisions            jsonb,                    -- pass c: per-difference decision, reason, guideline_gap marks
  session_ref          text NOT NULL,            -- authoring session; passes a and b of a unit must differ
  model                text NOT NULL,            -- authoring model (ADR-0011: Sonnet 5.5)
  inputs               jsonb NOT NULL,           -- guideline version, annotator-reference hash, packet hash, M13 version that chose the context
  payload_schema_id    bigint NOT NULL REFERENCES meta.payload_schema,   -- the batch's and frames' schema (D2 §8)
  created_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (golden_unit_id, pass, guideline_version_id)
);

CREATE TABLE eval.citation_frame (               -- versions of a pass's citation frame; added, never edited
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  golden_pass_id bigint NOT NULL REFERENCES eval.golden_pass ON DELETE CASCADE,
  version        integer NOT NULL,               -- 1: as authored, written with the pass
  parent_id      bigint REFERENCES eval.citation_frame,   -- the version it re-locates; null for version 1
  frame          jsonb NOT NULL,                 -- {"s1": {"locator": "…", "text": "…"}, "c1": {…}}: each cited sentence id → its locator and text (D1 §10.3)
  reason         text NOT NULL,                  -- 'authored', or the re-location that wrote it (D7 §3.5)
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (golden_pass_id, version),
  CHECK ((version = 1) = (parent_id IS NULL))
);

CREATE TABLE eval.golden_item (                  -- derived: one pass c batch located on one rendition
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  golden_pass_id bigint NOT NULL REFERENCES eval.golden_pass ON DELETE CASCADE,   -- the pass c it projects
  citation_frame_id bigint NOT NULL REFERENCES eval.citation_frame,   -- the frame version it was located through
  rendition_id   bigint NOT NULL REFERENCES kb.rendition,
  cascade_version text NOT NULL,                 -- the quote cascade that derived it (D4 §4.3)
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version,   -- the schema version it was derived under (name maps applied, D2 §8)
  item_type      text NOT NULL CHECK (item_type IN ('entity','statement','claim','alternative','unsupported')),
  local_ref      text NOT NULL,
  payload        jsonb NOT NULL,                 -- a stored item: the core stored-form batch element (D1 §10.3, D2 §7.3), offsets into rendition_id
  context        boolean NOT NULL DEFAULT false, -- a context premise stated outside the unit: scored only through claim nodes here (D7 §5.1)
  UNIQUE (golden_pass_id, rendition_id, cascade_version, schema_version_id, item_type, local_ref)
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
wrote, with its citation frame (D1 §10.3) as frame version 1. `eval.golden_item` is a projection of
one pass c batch onto one rendition: before a run is aligned, evaluation resolves the pass's latest
frame version on the run's rendition (`kb.run_rendition`, §8) and, when items for that pass,
rendition, cascade version and schema version do not yet exist, derives them by the production
quote cascade (D4 §4.3), applying the schema version's name maps; `write_golden` stores passes only
and never derives items. A frame that does not resolve marks the unit `stale` and derives nothing.
Re-location (D7 §3.5) **adds a frame version** with a parent link and new locators, keeping the
batch and the recorded sentence texts; no frame is rewritten, so the frame an earlier result scored
through stays as it was. Re-authoring adds a new pass c beside the old one. Items are never edited,
only derived again for another rendition, pass, cascade or schema version, and each records the
frame version it was located through. `eval.result` records the pass c ids it scored
(`golden_snapshot`), so a result stays tied to the goldens it used after re-authoring (P0CL-03;
operator, 2026-10-28).
> Decision: [ADR-0019](../adr/0019-identity-follows-content.md), [ADR-0022](../adr/0022-schema-change-modelled.md)
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
  The delete runs in one transaction in the order results, alignments, **claims, then
  entities**: deleting claims cascades to their evidence, supports and links, which the cascade
  finds through `claim_link_to` and the `(from_claim_id, …)` unique index, so `kb.claim_link`
  needs no `run_id` index and is never deleted by `run_id` directly (one would be added only for
  such a direct delete). Deleting entities then runs the referential checks on
  `kb.claim.subject_id`, `object_entity_id` and `statement_id`, which reach the `(run_id, …)`
  indexes `claim_subject`, `claim_object` and `claim_statement` through PostgreSQL 18's skip scan,
  so they need no single-column indexes of their own (operator, 2026-10-28, on S6).
  > Status: **Tested** (S6, 2026-10-28): deleting one slice run removed its entities, claims,
  > links, evidence, aliases, alignments and results, kept its run row, tasks and measurements,
  > and left the other run unchanged; every referential check the delete fires is index-backed
  > ([s6.constraints](../design_review/evidence/2026-10-28_design-spikes/records/s6.constraints.json)).
  > **Measured** at run scale on the interim project-local cluster: 25,000 materialized rows
  > (entities, claims and their cascades) deleted in 260.8 ms
  > ([s6.volume](../design_review/evidence/2026-10-28_design-spikes/records/s6.volume.json))
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
  `task_cache` leaves them out (**Proposed**, 2026-10-28). The claim statement, its plan and the
  two-branch form for larger queues are in [D6 §3.2](D6-orchestration-metrics-policies.md#32-workers).
  > Status: claiming and `attempt` fencing **Tested** (S6, 2026-10-28, interim project-local
  > cluster, lease 2 s): 10,200 of 10,200 tasks done exactly once with one observation, no claim
  > while a lease was live, a killed worker's and a stalled worker's batches re-claimed by the
  > ordinary claim, and the stalled worker's late fencing `UPDATE` matching 0 of 50 rows
  > ([s6.queue](../design_review/evidence/2026-10-28_design-spikes/records/s6.queue.json))
- **Promotion.** `meta.project.promoted_run_id` is set by the experiment decision
  ([D7 §7](D7-evaluation-goldens-outer-loop.md#7-experiments-and-promotion)). "Current
  knowledge" queries resolve it once per journey and then name the run by id (D8 §5; P0CL-11);
  nothing a run computes reads it, because each run records its reference run at creation (§4).
- **Every eligible unit has a fate.** For each eligible unit a run creates a task, or a `skipped`
  task with its `reason` (`scope` for a unit outside the run's declared scope, `limit`, `budget`,
  …), so coverage is a count over `ops.task`, never an absence (§9; P0CL-11; **Proposed**,
  2026-10-28).
- **The seal cuts a run's knowledge** (D6 §3.1; RC10, operator, 2026-10-28). Finalize opens with
  one short transaction that locks the run row `FOR NO KEY UPDATE`, creates the finalize tasks
  (the pass, the run-level M19 task, `evaluate`), stamps `ops.run.cut_at = clock_timestamp()`,
  records `cut_m19_task_id` and sets the status `consolidating`, then commits. Agent completions
  and twin settlements share-lock the run row and stamp `ops.task.finished_at` with
  `clock_timestamp()` after the lock, so each falls on one side of the cut. The final pass then
  reads as of the cut in its own transaction, and measure, evaluate and the `finished` update with
  `finished_at` follow, each in its own transaction, `finished_at` last. No lock on the run row is
  held across them (**Proposed**, 2026-10-28).
- **A sealed run's fates are its tasks as of `ops.run.cut_at`.** A task whose `finished_at` is
  later than the cut, or null (an agent task completed after the seal, a twin settled later, a task
  cancelled afterwards) counts as **unresolved** for that run, whatever its status now; nothing
  that finishes later changes what the run reports. Every terminal write sets
  `ops.task.finished_at`, including creation as `reused` or `skipped`, so the rule is one
  comparison, `t.finished_at <= r.cut_at`. The orchestrator's fate reader (D6), the coverage query
  (§9), `kb.run_observation` and `ops.run_measurement` (below), the pool loader (D5 §2) and
  `ci promote`'s check (D7 §7) apply it; a per-run fate snapshot was considered and not adopted.
  A run not yet sealed reads its current statuses (**Proposed**, design authority, 2026-10-28).
- **The run's own finalize-stage outputs are read by task.** The pass, M19 and `evaluate` tasks
  finish after the cut by construction, so the cut views exclude their outputs. M19's
  `verification` observations and its `rules.evaluated` measurements (§5) are read through
  `ops.run.cut_m19_task_id`, never by guessing the current pass and never through the cut views;
  the pool never reads M19 observations (D5 §8.1) (**Proposed**, 2026-10-28).
- **Observations are never deleted** while a task that produced them is referenced by any kept
  run (directly or through `reused_task_id`).
- **Effective observations of a run.** A view resolves reuse and, for a sealed run, the fate
  rule above:

```sql
CREATE VIEW kb.run_observation AS
SELECT t.run_id, o.*
FROM ops.task t
JOIN ops.run r ON r.id = t.run_id
JOIN kb.observation o ON o.task_id = COALESCE(t.reused_task_id, t.id)
WHERE t.status IN ('done','empty','reused')
  AND (r.cut_at IS NULL OR t.finished_at <= r.cut_at);
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
  AND (r.cut_at IS NULL OR t.finished_at <= r.cut_at)
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

**Family profile** (everything stated about a family in the run): the claims whose subject is
the family, and the claims about its parameters, the `stat:FamilyParameter` entities whose
identity names the family (their identity attribute `family` holds the family's entity key,
D1 §4.1). A family's parameters are often stated only on those entities ("the location parameter
is the mean"), with no claim whose subject is the family:

```sql
SELECT NULL AS parameter, c.predicate, c.qualifiers, c.object_value, o.label AS object_label, c.status, c.confidence
FROM kb.claim c
JOIN kb.entity s ON s.id = c.subject_id
LEFT JOIN kb.entity o ON o.id = c.object_entity_id
WHERE c.run_id = :run AND s.type = 'stat:DistributionFamily' AND s.key = :family_key
  AND c.status IN ('accepted','candidate')
UNION ALL
SELECT p.label, c.predicate, c.qualifiers, c.object_value, o.label, c.status, c.confidence
FROM kb.entity p
JOIN kb.claim c ON c.run_id = p.run_id AND c.subject_id = p.id
LEFT JOIN kb.entity o ON o.id = c.object_entity_id
WHERE p.run_id = :run AND p.type = 'stat:FamilyParameter' AND p.attrs ->> 'stat:family' = :family_key
  AND c.status IN ('accepted','candidate');
```

The parameter branch has no index on `attrs`: it filters the run's `stat:FamilyParameter` rows,
found through `entity_type`, which stays small beside the run's claims. `construction_profile`
(D8 §5.2) has the same shape, with a `stat:FamilyConstruction` subject.
> Status: **Tested** (S6, 2026-10-28, on the v1 trace rows): without the parameter branch the
> pattern returns 1 row for the normal family and misses T2's answer; the two-branch form returns
> every expected trace claim of T1's `construction_profile` and of T2's and T4's `family_profile`
> ([s6.queries](../design_review/evidence/2026-10-28_design-spikes/records/s6.queries.json)), run there
> with the bare type names of the rows as stored; the prefixed names (§3) are **Proposed**

**Statement reconstruction** (premises, conditions, conclusions and proof of a theorem):

```sql
SELECT c.statement_role, c.key, c.predicate, c.qualifiers -> 'core:conditions' AS conditions, c.qualifiers
FROM kb.claim c
WHERE c.run_id = :run AND c.statement_id = :statement_id
ORDER BY CASE c.statement_role WHEN 'premise' THEN 0 WHEN 'definiens' THEN 1
                               WHEN 'restriction' THEN 2 ELSE 3 END;
```

**Claims with a qualifier** (all `has_distribution` claims that give a `variance`):

```sql
SELECT key FROM kb.claim
WHERE run_id = :run AND predicate = 'stat:has_distribution'
  AND qualifiers @? '$."stat:param_values".variance';
```

A key with a prefix is quoted in a JSON path (`$."stat:param_values"`) and written as a plain
string with `->` and `?` (`qualifiers -> 'core:conditions'`).
> Status: the query form **Tested** (S6, 2026-10-28) with bare keys, returning the five expected
> claims ([s6.queries](../design_review/evidence/2026-10-28_design-spikes/records/s6.queries.json));
> the quoted prefixed key is **Proposed**

**Evidence for a claim** with the canonical text around it. The unit is the span's nearest
`unit` ancestor, not the span's own segment, which is the smallest containing one (a `sentence`
or a `math_inline`, as a rule); a span outside every unit has no unit:

```sql
SELECT ce.role, sp.text, sp.start_offset, sp.end_offset, seg.kind, u.attrs ->> 'id' AS unit_id
FROM kb.claim_evidence ce
JOIN kb.span sp ON sp.id = ce.span_id
JOIN kb.segment seg ON seg.id = sp.segment_id
LEFT JOIN LATERAL (
  SELECT a.attrs FROM kb.segment a                 -- segment_kind, then the range
  WHERE a.rendition_id = sp.rendition_id AND a.kind = 'unit'
    AND a.start_offset <= sp.start_offset AND sp.end_offset <= a.end_offset
  ORDER BY a.depth DESC
  LIMIT 1
) u ON true
WHERE ce.claim_id = :claim_id;
```
> Status: **Proposed** (2026-10-28). The defect it corrects is **Tested** (S6, 2026-10-28): reading
> `seg.attrs ->> 'id'` from the span's own segment gave a null unit for every evidence row of the
> trace data, whose spans sit in sentences and inline formulas
> ([s6.queries](../design_review/evidence/2026-10-28_design-spikes/records/s6.queries.json)); the range
> lookup over `segment_kind` is the one S6's `statement(page#unit)` sketch ran, and a `parent_id`
> walk would serve equally

**Coverage of a scope** (units extracted, skipped by reason, failed, unresolved), from the fates
of §8 as of the run's `cut_at`, over the documents a query's scope names:

```sql
SELECT fate.status, fate.reason, count(DISTINCT t.unit_key) AS units
FROM ops.run r
JOIN ops.task t ON t.run_id = r.id
JOIN kb.segment s ON s.id = t.unit_id
JOIN kb.run_rendition rr ON rr.run_id = t.run_id AND rr.rendition_id = s.rendition_id
CROSS JOIN LATERAL (
  SELECT CASE WHEN t.finished_at <= r.cut_at THEN t.status ELSE 'unresolved' END AS status,
         CASE WHEN t.finished_at <= r.cut_at THEN t.reason END AS reason
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
> Status: **Measured** (S6, 2026-10-28, interim project-local cluster): without an index on
> `unit_key` the query scans the run's tasks, 0.56 ms at 12,500 tasks and linear in a run's tasks
> ([s6.volume](../design_review/evidence/2026-10-28_design-spikes/records/s6.volume.json)); `task_unit`
> `(run_id, unit_key)` (§5) serves it and other per-unit reads (operator, 2026-10-28, on S6), its
> plan **Proposed**

Every pattern of this section, in the form S6 ran it, returned its rows in under 2 ms on the v1
trace rows of the four spike pages
(**Measured**, S6, 2026-10-28, [s6.queries](../design_review/evidence/2026-10-28_design-spikes/records/s6.queries.json)),
on tables of tens to thousands of rows, so the plans show what the planner chose at that size;
the run-scale figures are §11's.

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
| `stm:rel1` | `core:Statement` | theorem rel1 | `theorem` | local | `seg:n-rel1` |
| `stm:rel1-proof` | `core:Statement` | proof of rel1 | `proof` | local | `seg:n-rel1-d` |
| `ent:X@rel1` | `stat:RandomVariable` | X | — | local | `seg:n-rel1` |
| `ent:Y@rel1` | `stat:RandomVariable` | a + b X | — | local | `seg:n-rel1` |
| `ent:normal` | `stat:DistributionFamily` | normal distribution | — | global | — |

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
| `clm:C1` | `ent:X@rel1` | `stat:has_distribution` | `ent:normal` | `{"core:modality":"supposed","stat:param_values":{"mean":{"t":"formula","latex":"\\mu",…},"variance":{"t":"formula","latex":"\\sigma^2",…}}}` | premise | accepted | stated |
| `clm:C2` | `ent:Y@rel1` | `stat:defined_as` | value `{"t":"formula","latex":"a + b X",…}` | `{"core:modality":"defined","core:conditions":{"op":"and","args":[member(a, ℝ), member(b, ℝ∖{0})]}}` | definiens | accepted | stated |
| `clm:C3` | `ent:Y@rel1` | `stat:has_distribution` | `ent:normal` | `{"stat:param_values":{"mean":{…"latex":"a + b \\mu","symbols":{"mu":{"bind":"param_of","claim":"clm:C1","param":"mean"}}},"variance":{…}},"core:conditions":{"op":"and","args":[{"op":"claim","ref":"clm:C1"},{"op":"member","x":{…"a"},"set":{…"\\R"}},{"op":"member","x":{…"b"},"set":{…"\\R \\setminus \\{0\\}"}}]}}` | conclusion | accepted | stated |
| `clm:C4` | `stm:rel1-proof` | `core:proves` | `stm:rel1` | `{}` | — | accepted | stated |
| `clm:D1` | `ent:Y@rel1` | `stat:has_distribution` | `ent:normal` | `{"stat:param_values":{"mean":…,"standard_deviation":{…"latex":"\\lvert b \\rvert \\sigma"}}, "core:conditions": …}` | conclusion | accepted | derived |

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
> Status: **Measured** (S6, 2026-10-28, on the interim project-local cluster with its small default
> memory settings; a finished synthetic run of 2,500 units with payloads in the §6.2 shapes): binary
> COPY wrote 12,500 tasks in 103 ms, 100,000 observations in 1.1 s, 5,000 entities in 39 ms,
> 20,000 claims in 229 ms and 40,000 support and evidence rows in 214 ms; the per-unit and
> per-claim queries took 0.04–1.0 ms and the run's observations by kind through
> `kb.run_observation` 18 ms; the database held 77 MB
> ([s6.volume](../design_review/evidence/2026-10-28_design-spikes/records/s6.volume.json), [s6.sizes](../design_review/evidence/2026-10-28_design-spikes/records/s6.sizes.json)).
> The figures are to be rerun on `18/corpus` (§13)

## 12. Open questions

| ID | Question | Resolved by |
|---|---|---|
| OPEN-D3-1 | Lexical search: index and query form | **Answered** (2026-10-28, S6): BM25 through pg_textsearch 1.5.1 (§5): one partial `bm25` index per text-search configuration over the block level `('paragraph','heading','list_item','caption')`, with `ts_config = '<config>'::regconfig` in the index predicate and repeated in every query, queried by schema-qualified index name; on the four spike pages the planner uses the index (also under a generic plan), the kind list neither overlaps nor leaves text out, and an omitted predicate falls back silently to standalone scoring ([s6.bm25](../design_review/evidence/2026-10-28_design-spikes/records/s6.bm25.json), [s6.ddl](../design_review/evidence/2026-10-28_design-spikes/records/s6.ddl.json)). Open follow-up: the kind list's coverage on the 78-page corpus |
| OPEN-D3-2 | Embedding model and dimension (Qwen3-Embedding-0.6B at 1024, or 8B truncated by Matryoshka to 1024 or 2048) | Spike S7 |
| OPEN-D3-3 | Whether `kb.segment.text` duplicated from the canonical text is worth its space, or a generated substring view suffices | **Answered by mechanism** (2026-10-28): the BM25 index reads same-row text, and neither an index nor a generated column can read `kb.rendition`; the column stays. The sizes support it (**Measured**, S6, 2026-10-28, interim cluster): about 2.6 kB of segment text per author unit against about 11.6 kB of observation payload per unit at run scale ([s6.sizes](../design_review/evidence/2026-10-28_design-spikes/records/s6.sizes.json)) |
| OPEN-D3-4 | Whether claim keys need a stable cross-run `meaning_key` that ignores `statement` (to compare the same fact stated in two places) | **Migration 0001 has no meaning-key column; phase 1 goldens decide** (operator, 2026-10-28, on S6). S6 evidence (**Tested**, 2026-10-28): on the 70 aligned S0 claim pairs, the revised statement key (ADR-0019) raises claim-key agreement from 21 to 38, and with the label rule to 51 against 54 for meaning keys; the 3 remaining pairs differ by one statement-segmentation disagreement in U6, the other 16 differing pairs disagree about the fact itself; no fact is restated across the twelve units (0 of 71), so nothing calls for a stored meaning key yet ([s6.keys](../design_review/evidence/2026-10-28_design-spikes/records/s6.keys.json), [s6.restated](../design_review/evidence/2026-10-28_design-spikes/records/s6.restated.json)). Rerun on phase 1 goldens drawn across pages |

## 13. Operating PostgreSQL on this machine

The project runs on one dedicated PostgreSQL 18 cluster, `18/corpus` on port 5434, beside the
`main` cluster (5432) that other projects use and that is never changed. It is created with
`pg_createcluster` under postgresql-common, so it runs as the `postgresql@18-corpus` systemd unit,
logs to `/var/log/postgresql/`, and upgrades with `pg_upgradecluster`. One idempotent command,
`just db-provision` (sudo), creates and configures it from files tracked in `ops/postgresql/`, so
a rebuild reproduces it. It holds the project database `corpus`, the template `cs_template` (with
`pg_textsearch` and `vector`, created as `postgres`), the per-session test databases and the spike
databases.
> Status: **Proposed** (2026-10-28; operator direction: set up PostgreSQL with the installed
> tooling, at low overhead while the data can be regenerated;
> [overview](../libraries/PostgreSQL_System_Tooling_for_Ubuntu.md))

**Configuration** (`ops/postgresql/corpus.conf`, one `conf.d` file; nothing set with `ALTER
SYSTEM`), for this host (32 cores, 188 GB RAM shared with GPU work and another cluster, NVMe)
and the workload of §11 (bulk COPY, short indexed queries, a queue):
- preload `pg_textsearch`, `pg_stat_statements`, `auto_explain`;
- `shared_buffers = 8GB`, `effective_cache_size = 64GB`, `work_mem = 64MB`,
  `maintenance_work_mem = 8GB` (index builds);
- `io_method = io_uring`, `effective_io_concurrency = 256`, `random_page_cost = 1.1`,
  `wal_compression = zstd`, `max_wal_size = 8GB`;
- `jit = off` (short queries and bulk writes, where compiling costs more than it saves);
- `synchronous_commit = off`: a crash can lose the last fraction of a second of commits, which is
  acceptable while every row can be regenerated;
- `default_text_search_config = english`; `compute_query_id = on`;
  `auto_explain.log_min_duration = 1s`; `log_min_duration_statement = 250ms` with a pgBadger-ready
  `log_line_prefix`, so `pg_activity` and pgBadger can be pointed at it when a question arises;
- socket only (`listen_addresses = ''`), peer authentication.

**Roles.** The operator's login role owns the project's objects and has `CREATEDB` for test
databases; `corpus_ro` (NOLOGIN, `SELECT` only) is assumed by read-only sessions (the agent's
read-only `ci` commands, DuckDB analytics; D8 §1). No role needs superuser.

**No backups or archiving yet** (operator, 2026-10-28): everything in the database is generated
and can be regenerated, so backup and integrity machinery would be overhead now. **Revisit**
when the database holds work that is costly to redo: the first adjudicated dev golden set
(P0-E-3), or agent interventions and directions worth keeping; then pgBackRest (installed) with
WAL archiving, and a logical `pg_dump` for version-independent copies.

**Operation.** `just db-up`, `just db-down`, `just db-status` (`pg_ctlcluster`, `pg_lsclusters`);
`pg_activity -p 5434` for live sessions; pgBadger over the cluster log for a period's slow
statements. The interim project-local cluster that preceded it was retired on 2026-10-28, after S6.
