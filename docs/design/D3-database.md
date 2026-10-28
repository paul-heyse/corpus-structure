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
| Lexical search | pg_textsearch 1.5.1 (installed; BM25) | Replaces the old Tantivy crate. Index syntax is checked in spike S6 (`OPEN-D3-1`) |
| Graph traversal | Recursive CTEs; NetworkX and pgmpy projections in memory | The knowledge graph is small per project; path-heavy workloads would revisit this |
| Analytics and evaluation reports | DuckDB reading PostgreSQL (`postgres` extension) or Parquet exports | Read-only; never a second authority |
| Originals | Content-addressed files under `data/originals/<sha256>`; the corpus stays where it is and is referenced by path and hash | Keeps large binaries out of the database |
| Access from Python | SQLAlchemy Core 2.1 table metadata + psycopg 3 (COPY for bulk observation writes) | Same stack as before, without ORM |

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

Creation order follows foreign keys: `meta.project`, `meta.schema_version`, `meta.guideline_version`,
`ops.method`, `ops.method_config`, `ops.policy_version`, `ops.policy_rule`, `ops.debug_slice`,
`ops.run`, `kb.document`, `kb.rendition`, `kb.segment`, `kb.span`, `ops.task`, `kb.observation`,
then the rest.

## 3. `meta`: schema, guidelines and domain declarations

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_textsearch;
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
  compiled      jsonb NOT NULL,                  -- D2 §7 artifacts, keyed by compiler, each with its hash
  migration     jsonb,                           -- D2 §8 mapping from parent, breaking changes only
  state         text NOT NULL DEFAULT 'active' CHECK (state IN ('proposed','active','rejected','retired')),
  created_by    text NOT NULL,                   -- 'human:operator', 'agent:opus-5.5', ...
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, content_hash)
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
  extract             text,
  description         text,
  annotations         jsonb NOT NULL DEFAULT '{}',
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
  applies_to  text NOT NULL,
  severity    text NOT NULL CHECK (severity IN ('warning','error')),
  when_expr   text NOT NULL,
  check_expr  text NOT NULL,
  description text,
  PRIMARY KEY (schema_version_id, rule_id)
);

CREATE TABLE meta.guideline_version (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id        bigint NOT NULL REFERENCES meta.project,
  domain            text NOT NULL,
  label             text NOT NULL,
  content_hash      text NOT NULL,
  body              text NOT NULL,               -- the guideline markdown, inventory included
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version,
  parent_id         bigint REFERENCES meta.guideline_version,
  change_note       text,
  state             text NOT NULL DEFAULT 'active' CHECK (state IN ('proposed','active','rejected','retired')),
  created_by        text NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, content_hash)
);
```

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
  params      jsonb NOT NULL,                    -- canonical JSON; includes compiled-artifact hashes it depends on
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
  chain             text NOT NULL CHECK (chain IN ('propose','escalate','adjudicate','identity')),
  priority          integer NOT NULL,            -- position in the chain (D6 §7.1)
  unit_type         text NOT NULL,               -- the chain's default or the entry's own (D6 §7.1)
  condition         text NOT NULL,               -- rule-engine expression over the unit context
  action            jsonb NOT NULL,              -- {"method_config": "cfg:…", "limit": 50, "then": "stop|continue"}
  enabled           boolean NOT NULL DEFAULT true,
  UNIQUE (policy_version_id, rule_key)
);

CREATE TABLE ops.debug_slice (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id bigint NOT NULL REFERENCES meta.project,
  name       text NOT NULL,
  selector   jsonb NOT NULL,                     -- {"locators": ["special/Normal.html#rel1", "special/Normal.html@p:Suppose again that", ...]}; resolved per rendition (D6 §8)
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, name)
);

CREATE TABLE ops.run (
  id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id           bigint NOT NULL REFERENCES meta.project,
  kind                 text NOT NULL CHECK (kind IN ('ingest','full','slice','experiment','rescore')),
  phase                smallint NOT NULL,        -- 0–5 (D0); policies read it
  options              jsonb NOT NULL DEFAULT '{}',  -- agent_mode, agent_reuse, fresh methods, gpu mode (D6 §2, §4, §5)
  debug_slice_id       bigint REFERENCES ops.debug_slice,
  corpus_hash          text NOT NULL,            -- hash over selected rendition keys
  schema_version_id    bigint NOT NULL REFERENCES meta.schema_version,
  guideline_version_id bigint REFERENCES meta.guideline_version,
  policy_version_id    bigint NOT NULL REFERENCES ops.policy_version,
  code_commit          text NOT NULL,
  parent_run_id        bigint REFERENCES ops.run,
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

## 5. `kb`: evidence, observations, entities and claims

```sql
CREATE TABLE kb.document (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id    bigint NOT NULL REFERENCES meta.project,
  key           text NOT NULL UNIQUE,            -- 'doc:…'
  source_uri    text NOT NULL,                   -- e.g. 'siegrist_random/special/Normal.html'
  content_hash  text NOT NULL,                   -- sha256 of original bytes
  original_path text NOT NULL,                   -- where the bytes are
  mime          text NOT NULL,
  title         text,
  meta          jsonb NOT NULL DEFAULT '{}',     -- licence, source id from SOURCES.tsv, chapter, first_pass ...
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, source_uri, content_hash)
);

CREATE TABLE kb.rendition (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  document_id       bigint NOT NULL REFERENCES kb.document,
  key               text NOT NULL UNIQUE,        -- 'ren:…'
  adapter_config_id bigint NOT NULL REFERENCES ops.method_config,
  canonical_text    text NOT NULL,
  parse_status      text NOT NULL CHECK (parse_status IN ('ok','partial','failed')),
  parse_detail      jsonb NOT NULL DEFAULT '{}', -- exclusions, warnings
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (document_id, adapter_config_id)
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
  attrs        jsonb NOT NULL DEFAULT '{}',      -- author markup (D1 §3.2)
  parse_status text NOT NULL DEFAULT 'ok' CHECK (parse_status IN ('ok','partial','failed')),
  CHECK (start_offset <= end_offset)
);
CREATE INDEX segment_range ON kb.segment (rendition_id, start_offset, end_offset);
CREATE INDEX segment_kind  ON kb.segment (rendition_id, kind);
-- BM25 over segment text; exact syntax confirmed in S6 (OPEN-D3-1)
CREATE INDEX segment_bm25 ON kb.segment USING bm25 (text) WITH (text_config = 'english');

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

`ops.task` sits here in creation order because observations reference it:

```sql
CREATE TABLE ops.task (
  id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id           bigint NOT NULL REFERENCES ops.run,
  stage            text NOT NULL,                -- D6 §2 stage names
  unit_type        text NOT NULL CHECK (unit_type IN ('document','rendition','segment','observation','entity','claim',
                        'alternative_group','identity_group','run')),
  unit_id          bigint,                       -- id in the table named by unit_type; null for groups and 'run'
  unit_key         text,                         -- stable key of the unit (the group key for groups), for cross-run reuse
  method_config_id bigint NOT NULL REFERENCES ops.method_config,
  trigger_rule_id  bigint REFERENCES ops.policy_rule,  -- null for base-stage tasks
  trigger_metrics  jsonb NOT NULL DEFAULT '{}',  -- the metric values the rule saw
  input_hash       text NOT NULL,                -- D6 §4
  reused_task_id   bigint REFERENCES ops.task,   -- set when status = 'reused'
  status           text NOT NULL CHECK (status IN ('pending','running','awaiting_agent','done',
                        'empty','failed','skipped','reused','cancelled')),
  attempt          integer NOT NULL DEFAULT 0,
  priority         integer NOT NULL DEFAULT 0,
  claimed_by       text,                         -- worker id or agent session while running
  lease_until      timestamptz,                  -- 5 min for workers, 30 min for agent leases (D6 §3.2, D8 §2.1)
  cost             jsonb NOT NULL DEFAULT '{}',  -- {"wall_ms":…, "gpu_ms":…, "tokens_in":…, "tokens_out":…}
  error            jsonb,
  reason           text,                         -- why skipped or cancelled: 'limit', 'budget', 'prerequisite_failed', ...
  created_at       timestamptz NOT NULL DEFAULT now(),
  started_at       timestamptz,
  finished_at      timestamptz
);
CREATE INDEX task_queue ON ops.task (status, priority DESC, id) WHERE status IN ('pending','awaiting_agent');
CREATE INDEX task_cache ON ops.task (method_config_id, input_hash) WHERE status IN ('done','empty');
CREATE INDEX task_run   ON ops.task (run_id, stage);

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
CREATE INDEX observation_payload ON kb.observation USING gin (payload jsonb_path_ops);

CREATE TABLE kb.entity (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id            bigint NOT NULL REFERENCES ops.run ON DELETE CASCADE,
  key               text NOT NULL,               -- 'ent:…' or 'stm:…'
  schema_version_id bigint NOT NULL REFERENCES meta.schema_version,
  type              text NOT NULL,               -- schema class
  label             text NOT NULL,
  scope             text NOT NULL CHECK (scope IN ('global','local')),
  scope_segment_id  bigint REFERENCES kb.segment,
  attrs             jsonb NOT NULL DEFAULT '{}', -- identity attributes only (D1 §4.1)
  confidence        real,
  UNIQUE (run_id, key),
  CHECK ((scope = 'local') = (scope_segment_id IS NOT NULL))
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

CREATE TABLE kb.entity_mention (                 -- which mention observations resolved to the entity
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
CREATE INDEX claim_qual      ON kb.claim USING gin (qualifiers jsonb_path_ops);

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
```

Remaining `ops` tables:

```sql
CREATE TABLE ops.measurement (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id     bigint NOT NULL REFERENCES ops.run ON DELETE CASCADE,
  iteration  integer NOT NULL,
  scope_type text NOT NULL CHECK (scope_type IN ('run','rendition','segment','entity','claim','predicate',
                  'class','stage','method')),
  scope_id   bigint,
  scope_key  text,                               -- predicate or class name, stage name, method name
  metric     text NOT NULL,                      -- D6 §6 names
  value      double precision,
  detail     jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX measurement_lookup ON ops.measurement (run_id, metric, scope_type, scope_id);

CREATE TABLE ops.intervention (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  project_id  bigint NOT NULL REFERENCES meta.project,
  run_id      bigint REFERENCES ops.run,
  task_id     bigint REFERENCES ops.task,        -- the agent or human task it completed, if any
  actor       text NOT NULL,                     -- 'agent:opus-5.5', 'human:operator'
  session_ref text,                              -- Claude Code session id or similar
  kind        text NOT NULL CHECK (kind IN ('extract','adjudicate','golden_write','golden_adjudicate',
                   'schema_proposal','guideline_change','policy_proposal','experiment_decision',
                   'direction','ack','veto','audit')),
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

## 6. JSONB contracts

Each JSONB column has a JSON Schema in `corpus_structure/core/schemas/` ([D9 §1](D9-repository-and-phase0.md#1-layout)),
validated on write by the repository layer. Summaries:

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
| `author_markup` | `markup` (`dfn`, `unit`, `details`, `link`, `class`), `value` | `target` (link target) |
| `mention` | `label`, `text`, `start`, `end` | `attributes` {group: {label, score}}, `math_ref` |
| `relation` | `label` (predicate), `head` {`start`,`end`,`label`}, `tail` {…} | `joint` (bool: from `JointIE`), `feasible` |
| `record` | `structure`, `fields` {name: [{`text`,`start`,`end`,`score`}]} | `anchor` |
| `attribute` | `mention_ref`, `group`, `value` | — |
| `classification` | `task`, `labels` [{label, score}] | `feasible`, `violations` (constrained classifier) |
| `value` | `value` (D1 §6) | `parse_error` |
| `scope` | `mention_ref`, `binding_site` (a `mention_ref`), `scope_segment` (key), `extent` | `binding` (provisional kind, D4 M13) |
| `link` | `mention_ref` (M14) or `pair` of entity keys (M15), `candidate` (entity key, or `{"new": {type, label}}`), `score`, `features` | `rank` |
| `claim_proposal` | `batch` (a stored-form `ClaimProposalBatch`, D2 §7.3) | `rationale`; `rejected` [{`item`, `reason`}] (D4 §4.3); `establishment: derived`, `derived_from` (claim keys) and `rule` for M23 |
| `judgment` | `target` {`kind`: observation, claim, alternative_group, identity_group; `ref`}, `decision` (`accept`, `reject`, `choose`, `merge`, `split`, `unsure`), `rationale`, `guideline_version` | `chosen` (for `choose`), `faithful` (bool, with several chosen), `confidence` (`low`, `medium`, `high`) |
| `verification` | `claim_key`, `verifier`, `verdict` (`consistent`, `refuted`, `not_checkable`) | `detail`, `counterexample` |

### 6.3 Operations JSON

- **`mention_ref`** is `{"task": id, "ordinal": n}`, or `{"ordinal": n}` inside the same task,
  because observation ids are assigned only when a task's observations are copied in.
- `ops.task.trigger_metrics`: `{metric_name: value}` exactly as the policy rule evaluated them.
- `ops.task.cost`: `wall_ms`, `gpu_ms`, `tokens_in`, `tokens_out`, `model`.
- `ops.policy_rule.action`: `method_config` (config hash), `limit` (max tasks this rule may
  create per iteration), `then` (`stop` ends the chain for the unit, `continue` evaluates the next
  rule).
- `ops.intervention.target`: `{"kind": "unit"|"claim"|"alternative_group"|"golden_unit"|"schema"|"guideline"|"policy", "ref": …}`.

## 7. `eval`: goldens and results

```sql
CREATE TABLE eval.document_split (               -- page-level split assignment (D7 §3.1, §4)
  project_id  bigint NOT NULL REFERENCES meta.project,
  document_id bigint NOT NULL REFERENCES kb.document,
  split       text NOT NULL CHECK (split IN ('dev','test','reserved')),  -- reserved: worked-example pages, never golden (D7 §3.1)
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
  frozen_at            timestamptz,              -- test sets freeze at phase gates
  created_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, label, split)
);

CREATE TABLE eval.golden_unit (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  golden_set_id bigint NOT NULL REFERENCES eval.golden_set,
  rendition_id  bigint NOT NULL REFERENCES kb.rendition,
  segment_id    bigint NOT NULL REFERENCES kb.segment,   -- the annotation unit
  unit_key      text NOT NULL,
  status        text NOT NULL CHECK (status IN ('draft','adjudicated','stale','retired')),
  agreement     jsonb NOT NULL DEFAULT '{}',     -- A/B agreement by tier and predicate (D7 §3.3)
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (golden_set_id, unit_key)
);

CREATE TABLE eval.golden_pass (                  -- the single store of authored passes (D7 §3)
  id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  golden_unit_id       bigint NOT NULL REFERENCES eval.golden_unit ON DELETE CASCADE,
  pass                 text NOT NULL CHECK (pass IN ('a','b','c')),
  guideline_version_id bigint NOT NULL REFERENCES meta.guideline_version,
  batch                jsonb NOT NULL,           -- stored-form ClaimProposalBatch (pass c: the adjudicated batch)
  decisions            jsonb,                    -- pass c: per-difference decision, reason, guideline_gap marks
  session_ref          text NOT NULL,            -- authoring session; passes a and b of a unit must differ
  model                text NOT NULL,            -- authoring model (ADR-0011: Sonnet 5.5)
  inputs               jsonb NOT NULL,           -- guideline version, annotator-reference hash, packet hash, M13 version that chose the context
  created_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (golden_unit_id, pass, guideline_version_id)
);

CREATE TABLE eval.golden_item (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  golden_unit_id bigint NOT NULL REFERENCES eval.golden_unit ON DELETE CASCADE,
  item_type      text NOT NULL CHECK (item_type IN ('entity','statement','claim','alternative','unsupported')),
  local_ref      text NOT NULL,
  payload        jsonb NOT NULL,                 -- ClaimProposalBatch element (D2 §7.3), offsets into the rendition
  context        boolean NOT NULL DEFAULT false, -- a context premise stated outside the unit: scored only through claim nodes here (D7 §5.1)
  UNIQUE (golden_unit_id, item_type, local_ref)
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
  detail        jsonb NOT NULL DEFAULT '{}',
  created_at    timestamptz NOT NULL DEFAULT now()
);
```

## 8. Runs, snapshots and reads

- **Run lifecycle.** `created` → `running` (base stages, then route iterations) → possibly
  `awaiting_agent` (only agent tasks remain) → `consolidating` → `finished`, or `failed` /
  `cancelled`. Details in [D6 §2](D6-orchestration-metrics-policies.md#2-the-stage-graph-and-run-lifecycle).
- **Materialization.** Entities, claims, links and alignments are written per run and never
  updated after `finished`, except that a run may be deleted whole (cascade) when it is not the
  promoted run, not an experiment's baseline or candidate, and not referenced by a golden set.
- **Promotion.** `meta.project.promoted_run_id` is set by the experiment decision
  ([D7 §7](D7-evaluation-goldens-outer-loop.md#7-experiments-and-promotion)). "Current
  knowledge" queries go through views on the promoted run.
- **Observations are never deleted** while a task that produced them is referenced by any kept
  run (directly or through `reused_task_id`).
- **Effective observations of a run.** A view resolves reuse:

```sql
CREATE VIEW kb.run_observation AS
SELECT t.run_id, o.*
FROM ops.task t
JOIN kb.observation o ON o.task_id = COALESCE(t.reused_task_id, t.id)
WHERE t.status IN ('done','empty','reused');
```

## 9. Query patterns

These back the typed queries of [D8 §5](D8-agent-and-query-interfaces.md#5-typed-queries).

**Family profile** (everything stated about a family in the promoted run):

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

| key | type | label | scope | scope segment |
|---|---|---|---|---|
| `stm:rel1` | `Statement` | theorem rel1 | local | `seg:n-rel1` |
| `stm:rel1-proof` | `Statement` | proof of rel1 | local | `seg:n-rel1-d` |
| `ent:X@rel1` | `RandomVariable` | X | local | `seg:n-rel1` |
| `ent:Y@rel1` | `RandomVariable` | a + b X | local | `seg:n-rel1` |
| `ent:normal` | `DistributionFamily` | normal distribution | global | — |

`attrs` of statements hold `{"kind": "theorem"}` / `{"kind": "proof"}`.

`kb.claim` (`statement_id` = `stm:rel1` for C1–C3):

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
| OPEN-D3-1 | Exact pg_textsearch index and query syntax (`USING bm25`, `<@>`, `to_bm25query`), and whether it indexes `kb.segment.text` in place | Spike S6 |
| OPEN-D3-2 | Embedding model and dimension (Qwen3-Embedding-0.6B at 1024, or 8B truncated by Matryoshka to 1024 or 2048) | Spike S7 |
| OPEN-D3-3 | Whether `kb.segment.text` duplicated from the canonical text is worth its space, or a generated substring view suffices | Spike S6 |
| OPEN-D3-4 | Whether claim keys need a stable cross-run `meaning_key` that ignores `statement` (to compare the same fact stated in two places) | Spikes S6 and S0; phase 1 goldens if S0 has too few units; S0 evidence (2026-10-28): on 70 aligned claim pairs, meaning keys agreed for 41 (54 after the D1 §10.1 key-rule changes) against 21 (48) for claim keys; S6 decides storage |
