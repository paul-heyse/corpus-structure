-- The DDL blocks of §3-§8 of docs/design/D3-database.md as of commit 34cd2a8 (2026-10-28), copied verbatim
-- as the reference of the P0-M-2 port check (model and projections §3.4): D3 is to cite the generated
-- rendering instead of carrying DDL, so the comparison keeps its own copy.

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

CREATE VIEW kb.run_observation AS
SELECT t.run_id, o.*
FROM ops.task t
JOIN ops.run r ON r.id = t.run_id
JOIN kb.observation o ON o.task_id = COALESCE(t.reused_task_id, t.id)
WHERE t.status IN ('done','empty','reused')
  AND (r.cut_at IS NULL OR t.finished_at <= r.cut_at);

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

CREATE VIEW kb.run_rendition AS
SELECT t.run_id, b.document_id, b.rendition_id
FROM ops.task t
JOIN kb.rendition_build b ON b.document_id = t.unit_id AND b.method_config_id = t.method_config_id
WHERE t.stage = 'ingest' AND t.unit_type = 'document' AND t.status IN ('done','reused');
