CREATE TABLE ops.run (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	project_id BIGINT NOT NULL, 
	kind TEXT NOT NULL, 
	phase SMALLINT NOT NULL, 
	options JSONB DEFAULT '{}' NOT NULL, 
	debug_slice_id BIGINT, 
	corpus_hash TEXT NOT NULL, 
	schema_version_id BIGINT NOT NULL, 
	guideline_version_id BIGINT, 
	policy_version_id BIGINT NOT NULL, 
	code_commit TEXT NOT NULL, 
	parent_run_id BIGINT, 
	reference_run_id BIGINT, 
	iteration INTEGER DEFAULT 0 NOT NULL, 
	iteration_limit INTEGER DEFAULT 3 NOT NULL, 
	status TEXT NOT NULL, 
	notes TEXT, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_run PRIMARY KEY (id), 
	CONSTRAINT fk_run_project_id FOREIGN KEY(project_id) REFERENCES meta.project (id), 
	CONSTRAINT ck_run_kind_182380918a CHECK (kind IN ('ingest', 'full', 'slice', 'experiment', 'rescore', 'golden')), 
	CONSTRAINT fk_run_debug_slice_id FOREIGN KEY(debug_slice_id) REFERENCES ops.debug_slice (id), 
	CONSTRAINT fk_run_schema_version_id FOREIGN KEY(schema_version_id) REFERENCES meta.schema_version (id), 
	CONSTRAINT fk_run_guideline_version_id FOREIGN KEY(guideline_version_id) REFERENCES meta.guideline_version (id), 
	CONSTRAINT fk_run_policy_version_id FOREIGN KEY(policy_version_id) REFERENCES ops.policy_version (id), 
	CONSTRAINT fk_run_parent_run_id FOREIGN KEY(parent_run_id) REFERENCES ops.run (id), 
	CONSTRAINT fk_run_reference_run_id FOREIGN KEY(reference_run_id) REFERENCES ops.run (id), 
	CONSTRAINT ck_run_status_c083e937b6 CHECK (status IN ('created', 'running', 'awaiting_agent', 'consolidating', 'finished', 'failed', 'cancelled'))
);

CREATE TABLE ops.task (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	run_id BIGINT NOT NULL, 
	stage TEXT NOT NULL, 
	unit_type TEXT NOT NULL, 
	unit_id BIGINT, 
	unit_key TEXT, 
	method_config_id BIGINT NOT NULL, 
	trigger_rule_id BIGINT, 
	trigger_metrics JSONB DEFAULT '{}' NOT NULL, 
	input_hash TEXT NOT NULL, 
	packet_hash TEXT, 
	reused_task_id BIGINT, 
	status TEXT NOT NULL, 
	attempt INTEGER DEFAULT 0 NOT NULL, 
	priority INTEGER DEFAULT 0 NOT NULL, 
	claimed_by TEXT, 
	lease_until TIMESTAMP WITH TIME ZONE, 
	cost JSONB DEFAULT '{}' NOT NULL, 
	error JSONB, 
	reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_task PRIMARY KEY (id), 
	CONSTRAINT fk_task_run_id FOREIGN KEY(run_id) REFERENCES ops.run (id), 
	CONSTRAINT ck_task_unit_type_dbbc309bfc CHECK (unit_type IN ('document', 'rendition', 'segment', 'observation', 'entity', 'claim', 'alternative_group', 'identity_group', 'run', 'golden_unit')), 
	CONSTRAINT fk_task_method_config_id FOREIGN KEY(method_config_id) REFERENCES ops.method_config (id), 
	CONSTRAINT fk_task_trigger_rule_id FOREIGN KEY(trigger_rule_id) REFERENCES ops.policy_rule (id), 
	CONSTRAINT fk_task_reused_task_id FOREIGN KEY(reused_task_id) REFERENCES ops.task (id), 
	CONSTRAINT ck_task_status_9ecb3cedef CHECK (status IN ('pending', 'running', 'awaiting_agent', 'done', 'empty', 'failed', 'skipped', 'reused', 'cancelled'))
);

CREATE TABLE kb.segment (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	rendition_id BIGINT NOT NULL, 
	key TEXT NOT NULL, 
	parent_id BIGINT, 
	kind TEXT NOT NULL, 
	ordinal INTEGER NOT NULL, 
	depth INTEGER NOT NULL, 
	start_offset INTEGER NOT NULL, 
	end_offset INTEGER NOT NULL, 
	text TEXT NOT NULL, 
	ts_config TEXT DEFAULT 'english' NOT NULL, 
	attrs JSONB DEFAULT '{}' NOT NULL, 
	parse_status TEXT DEFAULT 'ok' NOT NULL, 
	parse_reason TEXT, 
	CONSTRAINT pk_segment PRIMARY KEY (id), 
	CONSTRAINT fk_segment_rendition_id FOREIGN KEY(rendition_id) REFERENCES kb.rendition (id), 
	CONSTRAINT fk_segment_parent_id FOREIGN KEY(parent_id) REFERENCES kb.segment (id), 
	CONSTRAINT ck_segment_kind_bc1bdabc7d CHECK (kind IN ('document', 'section', 'unit', 'paragraph', 'list', 'list_item', 'details', 'math_display', 'math_inline', 'heading', 'table', 'table_row', 'table_cell', 'caption', 'footnote', 'figure', 'sentence', 'email_message', 'quoted_block', 'signature')), 
	CONSTRAINT ck_segment_parse_status_ac723c743e CHECK (parse_status IN ('ok', 'partial', 'failed')), 
	CONSTRAINT uq_segment_key UNIQUE (key), 
	CONSTRAINT ck_segment_ordered_eq_ce23619d75 CHECK (start_offset <= end_offset)
);

CREATE TABLE kb.claim (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	run_id BIGINT NOT NULL, 
	key TEXT NOT NULL, 
	subject_id BIGINT NOT NULL, 
	predicate TEXT NOT NULL, 
	object_entity_id BIGINT, 
	object_value JSONB, 
	qualifiers JSONB DEFAULT '{}' NOT NULL, 
	statement_id BIGINT, 
	statement_role TEXT, 
	status TEXT NOT NULL, 
	establishment TEXT NOT NULL, 
	confidence REAL, 
	completeness JSONB DEFAULT '{}' NOT NULL, 
	CONSTRAINT pk_claim PRIMARY KEY (id), 
	CONSTRAINT fk_claim_run_id FOREIGN KEY(run_id) REFERENCES ops.run (id), 
	CONSTRAINT fk_claim_subject_id FOREIGN KEY(subject_id) REFERENCES kb.entity (id), 
	CONSTRAINT fk_claim_object_entity_id FOREIGN KEY(object_entity_id) REFERENCES kb.entity (id), 
	CONSTRAINT fk_claim_statement_id FOREIGN KEY(statement_id) REFERENCES kb.entity (id), 
	CONSTRAINT ck_claim_statement_role_f56ac0d3bf CHECK (statement_role IN ('premise', 'conclusion', 'definiens', 'restriction', 'example_value')), 
	CONSTRAINT ck_claim_status_56c4715ee9 CHECK (status IN ('candidate', 'accepted', 'rejected', 'ambiguous', 'conflicting', 'unsupported')), 
	CONSTRAINT ck_claim_establishment_947b296bf3 CHECK (establishment IN ('stated', 'derived', 'agent_asserted')), 
	CONSTRAINT uq_claim_run_id_key UNIQUE (run_id, key), 
	CONSTRAINT ck_claim_exactly_one_a0e97ac0f0 CHECK ((object_entity_id IS NULL) <> (object_value IS NULL))
);

CREATE TABLE meta.schema_slot (
	schema_version_id BIGINT NOT NULL, 
	name TEXT NOT NULL, 
	role TEXT NOT NULL, 
	domain_class TEXT, 
	range TEXT, 
	object_kind TEXT, 
	multivalued BOOLEAN DEFAULT false NOT NULL, 
	qualifiers TEXT[] DEFAULT '{}' NOT NULL, 
	identity_qualifiers TEXT[] DEFAULT '{}' NOT NULL, 
	subsets TEXT[] DEFAULT '{}' NOT NULL, 
	extract TEXT, 
	description TEXT, 
	annotations JSONB DEFAULT '{}' NOT NULL, 
	CONSTRAINT pk_schema_slot PRIMARY KEY (schema_version_id, name), 
	CONSTRAINT fk_schema_slot_schema_version_id FOREIGN KEY(schema_version_id) REFERENCES meta.schema_version (id), 
	CONSTRAINT ck_schema_slot_role_8d98a3cc53 CHECK (role IN ('predicate', 'qualifier', 'identity', 'field'))
);

CREATE INDEX segment_range ON kb.segment (rendition_id, start_offset, end_offset);

CREATE INDEX segment_kind ON kb.segment (rendition_id, kind);

CREATE INDEX segment_bm25 ON kb.segment USING bm25 (text) WITH (text_config = 'english') WHERE kind IN ('paragraph', 'list_item', 'heading', 'caption') AND ts_config = CAST('english' AS REGCONFIG);

CREATE INDEX task_pending ON ops.task (run_id, stage, method_config_id, priority DESC, id) WHERE status = 'pending';

CREATE INDEX task_lease ON ops.task (lease_until) WHERE status = 'running';

CREATE INDEX task_agent ON ops.task (run_id, priority DESC, id) WHERE status = 'awaiting_agent';

CREATE INDEX task_cache ON ops.task (method_config_id, input_hash) WHERE status IN ('done', 'empty') AND unit_type != 'run';

CREATE INDEX task_run ON ops.task (run_id, stage);

CREATE INDEX claim_pred ON kb.claim (run_id, predicate, status);

CREATE INDEX claim_subject ON kb.claim (run_id, subject_id);

CREATE INDEX claim_object ON kb.claim (run_id, object_entity_id);

CREATE INDEX claim_statement ON kb.claim (run_id, statement_id);
