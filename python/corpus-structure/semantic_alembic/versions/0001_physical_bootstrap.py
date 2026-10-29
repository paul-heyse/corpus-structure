"""Bootstrap the fixed semantic physical model, independently of legacy migrations.

Generated from trusted physical.yaml and reviewed. No semantic release creates tables.
Downgrade deliberately refuses: rebuild a uniquely owned fresh realization instead.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "semantic_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSchema("sem"))
    op.execute(sa.schema.CreateSchema("data"))
    # Frozen explicit projection of the trusted model.
    op.create_table('release',
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('parent_release_id', sa.Text(), nullable=True),
    sa.Column('content_digest', sa.Text(), nullable=False),
    sa.Column('profile', sa.Text(), nullable=False),
    sa.Column('prepared_bytes', postgresql.BYTEA(), nullable=False),
    sa.Column('manifest_bytes', postgresql.BYTEA(), nullable=False),
    sa.ForeignKeyConstraint(['parent_release_id'], ['sem.release.release_id'], name=op.f('fk_release_parent_release_id')),
    sa.PrimaryKeyConstraint('release_id', name=op.f('pk_release')),
    schema='sem',
    info={'model_class': 'release'}
    )
    op.create_table('project',
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('active_release_id', sa.Text(), nullable=True),
    sa.Column('generation', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    sa.CheckConstraint('generation >= 0', name=op.f('ck_project_physical_8313aadc77')),
    sa.ForeignKeyConstraint(['active_release_id'], ['sem.release.release_id'], name=op.f('fk_project_active_release_id')),
    sa.PrimaryKeyConstraint('project_id', name=op.f('pk_project')),
    schema='data',
    info={'model_class': 'project'}
    )
    op.create_table('artifact',
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('artifact_name', sa.Text(), nullable=False),
    sa.Column('media_type', sa.Text(), nullable=False),
    sa.Column('content', postgresql.BYTEA(), nullable=False),
    sa.Column('content_digest', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['release_id'], ['sem.release.release_id'], name=op.f('fk_artifact_release_id')),
    sa.PrimaryKeyConstraint('release_id', 'artifact_name', name=op.f('pk_artifact')),
    schema='sem',
    info={'model_class': 'artifact'}
    )
    op.create_table('class_definition',
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('class_id', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('iri', sa.Text(), nullable=False),
    sa.Column('abstract', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.ForeignKeyConstraint(['release_id'], ['sem.release.release_id'], name=op.f('fk_class_definition_release_id')),
    sa.PrimaryKeyConstraint('release_id', 'class_id', name=op.f('pk_class_definition')),
    sa.UniqueConstraint('release_id', 'iri', name=op.f('uq_class_definition_release_id_iri')),
    schema='sem',
    info={'model_class': 'class_definition'}
    )
    op.create_table('input',
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('input_kind', sa.Text(), nullable=False),
    sa.Column('input_name', sa.Text(), nullable=False),
    sa.Column('content', postgresql.BYTEA(), nullable=False),
    sa.Column('content_digest', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['release_id'], ['sem.release.release_id'], name=op.f('fk_input_release_id')),
    sa.PrimaryKeyConstraint('release_id', 'input_kind', 'input_name', name=op.f('pk_input')),
    schema='sem',
    info={'model_class': 'input'}
    )
    op.create_table('property_definition',
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('property_id', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('iri', sa.Text(), nullable=False),
    sa.Column('value_kind', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['release_id'], ['sem.release.release_id'], name=op.f('fk_property_definition_release_id')),
    sa.PrimaryKeyConstraint('release_id', 'property_id', name=op.f('pk_property_definition')),
    sa.UniqueConstraint('release_id', 'iri', name=op.f('uq_property_definition_release_id_iri')),
    schema='sem',
    info={'model_class': 'property_definition'}
    )
    op.create_table('registry_row',
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('body', postgresql.BYTEA(), nullable=False),
    sa.ForeignKeyConstraint(['release_id'], ['sem.release.release_id'], name=op.f('fk_registry_row_release_id')),
    sa.PrimaryKeyConstraint('release_id', 'kind', 'name', name=op.f('pk_registry_row')),
    schema='sem',
    info={'model_class': 'registry_row'}
    )
    op.create_table('vocabulary_member',
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('vocabulary_id', sa.Text(), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('meaning', sa.Text(), nullable=True),
    sa.Column('label', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['release_id'], ['sem.release.release_id'], name=op.f('fk_vocabulary_member_release_id')),
    sa.PrimaryKeyConstraint('release_id', 'vocabulary_id', 'value', name=op.f('pk_vocabulary_member')),
    schema='sem',
    info={'model_class': 'vocabulary_member'}
    )
    op.create_table('realization',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('project_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('state', sa.Text(), server_default=sa.text("'active'"), nullable=False),
    sa.Column('data_revision', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    sa.CheckConstraint("state IN ('active', 'building', 'retired', 'failed')", name=op.f('ck_realization_physical_3a1078e1fe')),
    sa.CheckConstraint('data_revision >= 0', name=op.f('ck_realization_physical_8c71a80efa')),
    sa.ForeignKeyConstraint(['project_id'], ['data.project.project_id'], name=op.f('fk_realization_project_id')),
    sa.ForeignKeyConstraint(['release_id'], ['sem.release.release_id'], name=op.f('fk_realization_release_id')),
    sa.PrimaryKeyConstraint('realization_id', name=op.f('pk_realization')),
    sa.UniqueConstraint('realization_id', 'release_id', name=op.f('uq_realization_realization_id_release_id')),
    schema='data',
    info={'model_class': 'realization'}
    )
    op.create_table('class_hierarchy',
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('class_id', sa.Text(), nullable=False),
    sa.Column('ancestor_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['release_id', 'ancestor_id'], ['sem.class_definition.release_id', 'sem.class_definition.class_id'], name=op.f('fk_class_hierarchy_release_id_ancestor_id')),
    sa.ForeignKeyConstraint(['release_id', 'class_id'], ['sem.class_definition.release_id', 'sem.class_definition.class_id'], name=op.f('fk_class_hierarchy_release_id_class_id')),
    sa.PrimaryKeyConstraint('release_id', 'class_id', 'ancestor_id', name=op.f('pk_class_hierarchy')),
    schema='sem',
    info={'model_class': 'class_hierarchy'}
    )
    op.create_table('identity_slot',
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('class_id', sa.Text(), nullable=False),
    sa.Column('group_id', sa.Text(), nullable=False),
    sa.Column('position', sa.BigInteger(), nullable=False),
    sa.Column('property_id', sa.Text(), nullable=False),
    sa.CheckConstraint('position >= 0', name=op.f('ck_identity_slot_physical_9039b28f88')),
    sa.ForeignKeyConstraint(['release_id', 'class_id'], ['sem.class_definition.release_id', 'sem.class_definition.class_id'], name=op.f('fk_identity_slot_release_id_class_id')),
    sa.ForeignKeyConstraint(['release_id', 'property_id'], ['sem.property_definition.release_id', 'sem.property_definition.property_id'], name=op.f('fk_identity_slot_release_id_property_id')),
    sa.PrimaryKeyConstraint('release_id', 'class_id', 'group_id', 'position', name=op.f('pk_identity_slot')),
    schema='sem',
    info={'model_class': 'identity_slot'}
    )
    op.create_table('property_applicability',
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('class_id', sa.Text(), nullable=False),
    sa.Column('property_id', sa.Text(), nullable=False),
    sa.Column('range_name', sa.Text(), nullable=False),
    sa.Column('required', sa.Boolean(), nullable=False),
    sa.Column('multivalued', sa.Boolean(), nullable=False),
    sa.Column('minimum_cardinality', sa.BigInteger(), nullable=True),
    sa.Column('maximum_cardinality', sa.BigInteger(), nullable=True),
    sa.Column('constraint_scope', sa.Text(), nullable=False),
    sa.Column('constraints', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.CheckConstraint('maximum_cardinality IS NULL OR maximum_cardinality >= 0', name=op.f('ck_property_applicability_physical_8e24e7a9f5')),
    sa.CheckConstraint('minimum_cardinality IS NULL OR maximum_cardinality IS NULL OR minimum_cardinality <= maximum_cardinality', name=op.f('ck_property_applicability_physical_62e5012383')),
    sa.CheckConstraint('minimum_cardinality IS NULL OR minimum_cardinality >= 0', name=op.f('ck_property_applicability_physical_dd48c61c63')),
    sa.ForeignKeyConstraint(['release_id', 'class_id'], ['sem.class_definition.release_id', 'sem.class_definition.class_id'], name=op.f('fk_property_applicability_release_id_class_id')),
    sa.ForeignKeyConstraint(['release_id', 'property_id'], ['sem.property_definition.release_id', 'sem.property_definition.property_id'], name=op.f('fk_property_applicability_release_id_property_id')),
    sa.PrimaryKeyConstraint('release_id', 'class_id', 'property_id', name=op.f('pk_property_applicability')),
    schema='sem',
    info={'model_class': 'property_applicability'}
    )
    op.create_table('sql_admission',
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('input_kind', sa.Text(), server_default=sa.text("'dependency'"), nullable=False),
    sa.Column('input_name', sa.Text(), nullable=False),
    sa.Column('physical_id', sa.Text(), nullable=False),
    sa.Column('content', postgresql.BYTEA(), nullable=False),
    sa.Column('content_digest', sa.Text(), nullable=False),
    sa.CheckConstraint("input_kind = 'dependency'", name=op.f('ck_sql_admission_physical_022451ced1')),
    sa.ForeignKeyConstraint(['release_id', 'input_kind', 'input_name'], ['sem.input.release_id', 'sem.input.input_kind', 'sem.input.input_name'], name=op.f('fk_sql_admission_release_id_input_kind_input_name')),
    sa.PrimaryKeyConstraint('release_id', 'input_name', 'physical_id', name=op.f('pk_sql_admission')),
    schema='sem',
    info={'model_class': 'sql_admission'}
    )
    op.create_table('batch',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('batch_id', sa.Text(), nullable=False),
    sa.Column('content_digest', sa.Text(), nullable=False),
    sa.Column('content', postgresql.BYTEA(), nullable=False),
    sa.Column('data_revision', sa.BigInteger(), nullable=False),
    sa.CheckConstraint('data_revision > 0', name=op.f('ck_batch_physical_239a1f5235')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_batch_realization_id_release_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'batch_id', name=op.f('pk_batch')),
    sa.UniqueConstraint('realization_id', 'release_id', 'data_revision', name=op.f('uq_batch_realization_id_release_id_data_revision')),
    schema='data',
    info={'model_class': 'batch'}
    )
    op.create_table('coverage',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('coverage_id', sa.Text(), nullable=False),
    sa.Column('family', sa.Text(), nullable=False),
    sa.Column('scope', sa.Text(), nullable=False),
    sa.Column('outcome', sa.Text(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.CheckConstraint("outcome IN ('complete','partial','unanalysed','failed')", name=op.f('ck_coverage_physical_1a0a2904ca')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_coverage_realization_id_release_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'coverage_id', name=op.f('pk_coverage')),
    schema='data',
    info={'model_class': 'coverage'}
    )
    op.create_table('entity',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('entity_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_entity_realization_id_release_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'entity_id', name=op.f('pk_entity')),
    schema='data',
    info={'model_class': 'entity'}
    )
    op.create_table('evidence',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('evidence_id', sa.Text(), nullable=False),
    sa.Column('source_uri', sa.Text(), nullable=False),
    sa.Column('locator', sa.Text(), nullable=False),
    sa.Column('provider', sa.Text(), nullable=False),
    sa.Column('operation_version', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_evidence_realization_id_release_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'evidence_id', name=op.f('pk_evidence')),
    schema='data',
    info={'model_class': 'evidence'}
    )
    op.create_table('membership',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('entity_id', sa.Text(), nullable=False),
    sa.Column('class_id', sa.Text(), nullable=False),
    sa.Column('establishment', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'entity_id'], ['data.entity.realization_id', 'data.entity.release_id', 'data.entity.entity_id'], name=op.f('fk_membership_realization_id_release_id_entity_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_membership_realization_id_release_id')),
    sa.ForeignKeyConstraint(['release_id', 'class_id'], ['sem.class_definition.release_id', 'sem.class_definition.class_id'], name=op.f('fk_membership_release_id_class_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'entity_id', 'class_id', name=op.f('pk_membership')),
    schema='data',
    info={'model_class': 'membership'}
    )
    op.create_index(op.f('ix_membership_realization_id_release_id_class_id_entity_id'), 'membership', ['realization_id', 'release_id', 'class_id', 'entity_id'], unique=False, schema='data')
    op.create_table('typed_value',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('value_id', sa.Text(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('text_value', sa.Text(), nullable=True),
    sa.Column('integer_value', sa.Numeric(), nullable=True),
    sa.Column('numeric_value', sa.Numeric(), nullable=True),
    sa.Column('decimal_lexical', sa.Text(), nullable=True),
    sa.Column('boolean_value', sa.Boolean(), nullable=True),
    sa.Column('entity_id', sa.Text(), nullable=True),
    sa.Column('language', sa.Text(), nullable=True),
    sa.Column('datatype', sa.Text(), nullable=True),
    sa.Column('opaque_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.CheckConstraint("(kind IN ('string','integer','date','datetime','float','expression','missing') AND text_value IS NOT NULL AND decimal_lexical IS NULL AND boolean_value IS NULL AND entity_id IS NULL AND opaque_payload IS NULL) OR (kind IN ('decimal','number') AND text_value IS NULL AND decimal_lexical IS NOT NULL AND boolean_value IS NULL AND entity_id IS NULL AND opaque_payload IS NULL) OR (kind IN ('boolean') AND text_value IS NULL AND decimal_lexical IS NULL AND boolean_value IS NOT NULL AND entity_id IS NULL AND opaque_payload IS NULL) OR (kind IN ('entity') AND text_value IS NULL AND decimal_lexical IS NULL AND boolean_value IS NULL AND entity_id IS NOT NULL AND opaque_payload IS NULL) OR (kind IN ('opaque') AND text_value IS NULL AND decimal_lexical IS NULL AND boolean_value IS NULL AND entity_id IS NULL AND opaque_payload IS NOT NULL) OR (kind IN ('null','sequence','mapping','record','interval') AND text_value IS NULL AND decimal_lexical IS NULL AND boolean_value IS NULL AND entity_id IS NULL AND opaque_payload IS NULL)", name=op.f('ck_typed_value_physical_dcfa9b38a9')),
    sa.CheckConstraint("decimal_lexical IS NULL OR decimal_lexical ~ '^[+-]?([0-9]+(\\.[0-9]*)?|\\.[0-9]+)([eE][+-]?[0-9]+)?$'", name=op.f('ck_typed_value_physical_6d9834e238')),
    sa.CheckConstraint("integer_value IS NULL OR kind = 'integer'", name=op.f('ck_typed_value_physical_b4572e9f51')),
    sa.CheckConstraint("kind <> 'integer' OR text_value ~ '^[+-]?[0-9]+$'", name=op.f('ck_typed_value_physical_053b27098a')),
    sa.CheckConstraint("kind IN ('string','integer','decimal','number','boolean','entity','null','missing','sequence','mapping','record','interval','expression','date','datetime','float','opaque')", name=op.f('ck_typed_value_physical_d01245fe40')),
    sa.CheckConstraint("numeric_value IS NULL OR kind IN ('decimal','number')", name=op.f('ck_typed_value_physical_77f076c9cb')),
    sa.CheckConstraint('CASE WHEN integer_value IS NULL THEN true ELSE integer_value = trunc(integer_value) AND integer_value = text_value::numeric END', name=op.f('ck_typed_value_physical_05579de47e')),
    sa.CheckConstraint('CASE WHEN numeric_value IS NULL THEN true ELSE numeric_value = decimal_lexical::numeric END', name=op.f('ck_typed_value_physical_1338461682')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'entity_id'], ['data.entity.realization_id', 'data.entity.release_id', 'data.entity.entity_id'], name=op.f('fk_typed_value_realization_id_release_id_entity_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_typed_value_realization_id_release_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'value_id', name=op.f('pk_typed_value')),
    schema='data',
    info={'model_class': 'typed_value'}
    )
    op.create_index(op.f('ix_typed_value_realization_id_release_id_entity_id'), 'typed_value', ['realization_id', 'release_id', 'entity_id'], unique=False, schema='data')
    op.create_index(op.f('ix_typed_value_realization_id_release_id_kind_numeric_value'), 'typed_value', ['realization_id', 'release_id', 'kind', 'numeric_value'], unique=False, schema='data', postgresql_where=sa.text('octet_length(numeric_value::text) <= 1024'))
    op.create_index(op.f('ix_typed_value_realization_id_release_id_kind_text_value'), 'typed_value', ['realization_id', 'release_id', 'kind', 'text_value'], unique=False, schema='data', postgresql_where=sa.text('octet_length(text_value) <= 1024'))
    op.create_table('fact',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('fact_id', sa.Text(), nullable=False),
    sa.Column('subject_id', sa.Text(), nullable=False),
    sa.Column('property_id', sa.Text(), nullable=False),
    sa.Column('object_value_id', sa.Text(), nullable=False),
    sa.Column('qualification_value_id', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'object_value_id'], ['data.typed_value.realization_id', 'data.typed_value.release_id', 'data.typed_value.value_id'], name=op.f('fk_fact_realization_id_release_id_object_value_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'qualification_value_id'], ['data.typed_value.realization_id', 'data.typed_value.release_id', 'data.typed_value.value_id'], name=op.f('fk_fact_realization_id_release_id_qualification_value_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'subject_id'], ['data.entity.realization_id', 'data.entity.release_id', 'data.entity.entity_id'], name=op.f('fk_fact_realization_id_release_id_subject_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_fact_realization_id_release_id')),
    sa.ForeignKeyConstraint(['release_id', 'property_id'], ['sem.property_definition.release_id', 'sem.property_definition.property_id'], name=op.f('fk_fact_release_id_property_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'fact_id', name=op.f('pk_fact')),
    schema='data',
    info={'model_class': 'fact'}
    )
    op.create_index(op.f('ix_fact_realization_id_release_id_property_id_object_value_id'), 'fact', ['realization_id', 'release_id', 'property_id', 'object_value_id'], unique=False, schema='data')
    op.create_index(op.f('ix_fact_realization_id_release_id_property_id_subject_id'), 'fact', ['realization_id', 'release_id', 'property_id', 'subject_id'], unique=False, schema='data')
    op.create_table('membership_support',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('entity_id', sa.Text(), nullable=False),
    sa.Column('class_id', sa.Text(), nullable=False),
    sa.Column('evidence_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'entity_id', 'class_id'], ['data.membership.realization_id', 'data.membership.release_id', 'data.membership.entity_id', 'data.membership.class_id'], name=op.f('fk_membership_support_realization_id_release_id_entity_id_class_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'evidence_id'], ['data.evidence.realization_id', 'data.evidence.release_id', 'data.evidence.evidence_id'], name=op.f('fk_membership_support_realization_id_release_id_evidence_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_membership_support_realization_id_release_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'entity_id', 'class_id', 'evidence_id', name=op.f('pk_membership_support')),
    schema='data',
    info={'model_class': 'membership_support'}
    )
    op.create_table('value_role',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('parent_value_id', sa.Text(), nullable=False),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('position', sa.BigInteger(), nullable=False),
    sa.Column('child_value_id', sa.Text(), nullable=False),
    sa.CheckConstraint('position >= 0', name=op.f('ck_value_role_physical_9039b28f88')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'child_value_id'], ['data.typed_value.realization_id', 'data.typed_value.release_id', 'data.typed_value.value_id'], name=op.f('fk_value_role_realization_id_release_id_child_value_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'parent_value_id'], ['data.typed_value.realization_id', 'data.typed_value.release_id', 'data.typed_value.value_id'], name=op.f('fk_value_role_realization_id_release_id_parent_value_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_value_role_realization_id_release_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'parent_value_id', 'role', 'position', name=op.f('pk_value_role')),
    schema='data',
    info={'model_class': 'value_role'}
    )
    op.create_table('derivation',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('derivation_id', sa.Text(), nullable=False),
    sa.Column('conclusion_fact_id', sa.Text(), nullable=False),
    sa.Column('rule', sa.Text(), nullable=False),
    sa.Column('rule_version', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'conclusion_fact_id'], ['data.fact.realization_id', 'data.fact.release_id', 'data.fact.fact_id'], name=op.f('fk_derivation_realization_id_release_id_conclusion_fact_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_derivation_realization_id_release_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'derivation_id', name=op.f('pk_derivation')),
    schema='data',
    info={'model_class': 'derivation'}
    )
    op.create_table('occurrence',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('occurrence_id', sa.Text(), nullable=False),
    sa.Column('fact_id', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('item', sa.Text(), nullable=False),
    sa.Column('batch_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'batch_id'], ['data.batch.realization_id', 'data.batch.release_id', 'data.batch.batch_id'], name=op.f('fk_occurrence_realization_id_release_id_batch_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'fact_id'], ['data.fact.realization_id', 'data.fact.release_id', 'data.fact.fact_id'], name=op.f('fk_occurrence_realization_id_release_id_fact_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_occurrence_realization_id_release_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'occurrence_id', name=op.f('pk_occurrence')),
    sa.UniqueConstraint('realization_id', 'release_id', 'occurrence_id', 'fact_id', name=op.f('uq_occurrence_realization_id_release_id_occurrence_id_fact_id')),
    schema='data',
    info={'model_class': 'occurrence'}
    )
    op.create_index(op.f('ix_occurrence_realization_id_release_id_source_item'), 'occurrence', ['realization_id', 'release_id', 'source', 'item'], unique=False, schema='data')
    op.create_table('selection',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('fact_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'fact_id'], ['data.fact.realization_id', 'data.fact.release_id', 'data.fact.fact_id'], name=op.f('fk_selection_realization_id_release_id_fact_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_selection_realization_id_release_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'fact_id', name=op.f('pk_selection')),
    schema='data',
    info={'model_class': 'selection'}
    )
    op.create_table('derivation_premise',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('derivation_id', sa.Text(), nullable=False),
    sa.Column('position', sa.BigInteger(), nullable=False),
    sa.Column('premise_fact_id', sa.Text(), nullable=False),
    sa.CheckConstraint('position >= 0', name=op.f('ck_derivation_premise_physical_9039b28f88')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'derivation_id'], ['data.derivation.realization_id', 'data.derivation.release_id', 'data.derivation.derivation_id'], name=op.f('fk_derivation_premise_realization_id_release_id_derivation_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'premise_fact_id'], ['data.fact.realization_id', 'data.fact.release_id', 'data.fact.fact_id'], name=op.f('fk_derivation_premise_realization_id_release_id_premise_fact_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_derivation_premise_realization_id_release_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'derivation_id', 'position', name=op.f('pk_derivation_premise')),
    schema='data',
    info={'model_class': 'derivation_premise'}
    )
    op.create_table('occurrence_evidence',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('occurrence_id', sa.Text(), nullable=False),
    sa.Column('evidence_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'evidence_id'], ['data.evidence.realization_id', 'data.evidence.release_id', 'data.evidence.evidence_id'], name=op.f('fk_occurrence_evidence_realization_id_release_id_evidence_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'occurrence_id'], ['data.occurrence.realization_id', 'data.occurrence.release_id', 'data.occurrence.occurrence_id'], name=op.f('fk_occurrence_evidence_realization_id_release_id_occurrence_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_occurrence_evidence_realization_id_release_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'occurrence_id', 'evidence_id', name=op.f('pk_occurrence_evidence')),
    schema='data',
    info={'model_class': 'occurrence_evidence'}
    )
    op.create_table('support',
    sa.Column('realization_id', sa.Text(), nullable=False),
    sa.Column('release_id', sa.Text(), nullable=False),
    sa.Column('fact_id', sa.Text(), nullable=False),
    sa.Column('occurrence_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['realization_id', 'release_id', 'occurrence_id', 'fact_id'], ['data.occurrence.realization_id', 'data.occurrence.release_id', 'data.occurrence.occurrence_id', 'data.occurrence.fact_id'], name=op.f('fk_support_realization_id_release_id_occurrence_id_fact_id')),
    sa.ForeignKeyConstraint(['realization_id', 'release_id'], ['data.realization.realization_id', 'data.realization.release_id'], name=op.f('fk_support_realization_id_release_id')),
    sa.PrimaryKeyConstraint('realization_id', 'release_id', 'fact_id', 'occurrence_id', name=op.f('pk_support')),
    schema='data',
    info={'model_class': 'support'}
    )



def downgrade() -> None:
    raise RuntimeError("semantic bootstrap downgrade is destructive; rebuild the owned realization")
