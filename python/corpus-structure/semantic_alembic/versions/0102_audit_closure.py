"""Audit-closure semantic authority and immutable split decisions; forward from frozen101.

Native and physical sidecars are hash-bound; the owning plan records qualification scope.
"""

import json
from hashlib import sha256
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from alembic.operations import Operations
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_audit_closure_20261103"
down_revision = "semantic_m1_records_20261103"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_audit_closure_20261103_native.json"
NATIVE_STATE_SHA256 = "84810b95b48af69e96dbe1f452270c5dbe5369b5b06a940f828d994865fb4243"
NATIVE_ADMISSION_FILE = "semantic_audit_closure_20261103_admission.sql"
NATIVE_ADMISSION_SHA256 = "58caafdf647c1181ca0d93901dc0c3affcf4168d0c4d4c0c18981a7c8819e4ee"
PHYSICAL_STATE_FILE = "semantic_audit_closure_20261103_physical.sql"
PHYSICAL_STATE_SHA256 = "af070eca7bd79c29500eb6dc8afa601fe1cecd4dd6bae4e437d63521ab984b9f"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("audit-closure native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["predecessor"] != down_revision or state["version"] != 1:
        raise RuntimeError("incompatible audit-closure native predecessor")
    _migration_role = op.get_bind().exec_driver_sql("SELECT current_user").scalar_one()
    op.execute("SET LOCAL ROLE corpus_sem_publisher")
    op.create_table(
        "split_decision",
        sa.Column("decision_id", sa.Text(), nullable=False),
        sa.Column("project_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("intent", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column("digest", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["data.project.project_id"], name=op.f("fk_split_decision_project_id")
        ),
        sa.ForeignKeyConstraint(
            ["release_id"], ["sem.release.release_id"], name=op.f("fk_split_decision_release_id")
        ),
        sa.PrimaryKeyConstraint("decision_id", name=op.f("pk_split_decision")),
        schema="eval",
        info={
            "model_class": "split_decision",
            "immutability": "intrinsic",
            "read_roles": ["corpus_sem_evaluator"],
        },
    )
    op.execute("SET LOCAL ROLE " + op.get_bind().dialect.identifier_preparer.quote(_migration_role))
    op.create_table(
        "scientific_representative",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("fact_id", sa.Text(), nullable=False),
        sa.Column("representative_fact_id", sa.Text(), nullable=False),
        sa.Column("policy_id", sa.Text(), nullable=False),
        sa.Column("component_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "fact_id"],
            ["data.fact.realization_id", "data.fact.release_id", "data.fact.fact_id"],
            name=op.f("fk_scientific_representative_realization_id_release_id_fact_id"),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "representative_fact_id"],
            ["data.fact.realization_id", "data.fact.release_id", "data.fact.fact_id"],
            name=op.f(
                "fk_scientific_representative_realization_id_release_id_representative_fact_id"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id", "release_id", "fact_id", name=op.f("pk_scientific_representative")
        ),
        schema="data",
        info={"model_class": "scientific_representative", "immutability": "admitted"},
    )
    op.create_table(
        "entity_resolution",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("observation_id", sa.BigInteger(), nullable=False),
        sa.Column("local_id", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("basis", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("candidates", sa.Text(), nullable=False),
        sa.Column("key_policy", sa.Text(), nullable=False),
        sa.Column("dependencies", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("operation_id", sa.Text(), nullable=False),
        sa.Column("operation_version", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "basis IN ('declared_key', 'global_label', 'source_local')",
            name=op.f("ck_entity_resolution_physical_1143a31dc3"),
        ),
        sa.CheckConstraint(
            "outcome IN ('resolved', 'ambiguous_anchor', 'incomplete_key', 'ungrounded_cycle')",
            name=op.f("ck_entity_resolution_physical_4b568fb139"),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "entity_id"],
            ["data.entity.realization_id", "data.entity.release_id", "data.entity.entity_id"],
            name=op.f("fk_entity_resolution_realization_id_release_id_entity_id"),
        ),
        sa.ForeignKeyConstraint(
            ["release_id", "observation_id"],
            ["kb.observation.release_id", "kb.observation.id"],
            name=op.f("fk_entity_resolution_release_id_observation_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "observation_id",
            "local_id",
            name=op.f("pk_entity_resolution"),
        ),
        schema="data",
        info={"model_class": "entity_resolution", "immutability": "admitted"},
    )
    op.add_column(
        "assessment",
        sa.Column("semantic_reason", postgresql.JSONB(astext_type=Text()), nullable=True),
        schema="data",
    )
    op.create_index(
        "ix_fact_scoped_adjacency",
        "fact",
        ["release_id", "realization_id", "subject_id", sa.literal_column('fact_id COLLATE "C"')],
        unique=False,
        schema="data",
        postgresql_where=None,
        postgresql_using="btree",
        postgresql_include=["property_id", "object_value_id"],
    )
    op.execute("SET LOCAL ROLE corpus_sem_publisher")
    op.add_column(
        "document_split", sa.Column("decision_id", sa.Text(), nullable=True), schema="eval"
    )
    op.execute("SET LOCAL ROLE " + op.get_bind().dialect.identifier_preparer.quote(_migration_role))
    op.execute("SET LOCAL ROLE corpus_sem_publisher")
    op.add_column("document_split", sa.Column("reason", sa.Text(), nullable=True), schema="eval")
    op.execute("SET LOCAL ROLE " + op.get_bind().dialect.identifier_preparer.quote(_migration_role))
    op.execute("SET LOCAL ROLE corpus_sem_publisher")
    op.create_foreign_key(
        op.f("fk_document_split_decision_id"),
        "document_split",
        "split_decision",
        ["decision_id"],
        ["decision_id"],
        source_schema="eval",
        referent_schema="eval",
    )
    op.execute("SET LOCAL ROLE " + op.get_bind().dialect.identifier_preparer.quote(_migration_role))
    op.execute("ALTER TABLE data.scientific_representative OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.entity_resolution OWNER TO corpus_sem_publisher")
    op.execute("SET LOCAL ROLE corpus_sem_publisher")
    op.execute(_read(PHYSICAL_STATE_FILE, PHYSICAL_STATE_SHA256).decode("utf-8"))
    op.execute("GRANT SELECT ON eval.split_decision TO corpus_sem_evaluator")
    op.execute(
        "GRANT SELECT ON data.scientific_representative TO "
        "corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.entity_resolution TO "
        "corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute("SET LOCAL ROLE " + op.get_bind().dialect.identifier_preparer.quote(_migration_role))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][0]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][1]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][2]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][3]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][4]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][5]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][6]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][7]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][8]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][9]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][10]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][11]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][12]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][13]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][14]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][15]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][16]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][17]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][18]))
    Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(state["operations"][19]))
    admit_native(
        op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"])
    )


def downgrade():
    raise RuntimeError("destructive audit-closure downgrade refused; rebuild an owned database")
