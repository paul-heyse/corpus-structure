"""M1 public record projection, protected source references and append-only custody.

Draft qualification artifact; forward only from immutable revision100.
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

revision = "semantic_m1_records_20261103"
down_revision = "semantic_m1_private_20261103"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_records_20261103_native.json"
NATIVE_STATE_SHA256 = "ac80724fb5a7d9fc3e866ba230aca7c819330174ddc3e4da3294edf7842ad760"
NATIVE_ADMISSION_FILE = "semantic_m1_records_20261103_admission.sql"
NATIVE_ADMISSION_SHA256 = "4b2f644d822b8485482a48757a3fbe934003f099b0249f6a9b5a177a340f77d9"


def _read(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("M1 record artifact differs: " + name)
    return content


def upgrade() -> None:
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["predecessor"] != down_revision or state["version"] != 1:
        raise RuntimeError("incompatible M1 record state")
    operations = Operations(op.get_context())
    _migration_role = op.get_bind().exec_driver_sql("SELECT current_user").scalar_one()
    op.create_table(
        "source_record",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("contract", sa.Text(), nullable=False),
        sa.Column("family", sa.Text(), nullable=False),
        sa.Column("occurrence_recipe", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("native_product_task_id", sa.BigInteger(), nullable=False),
        sa.Column("product_key", sa.Text(), nullable=False),
        sa.Column("product_digest", sa.Text(), nullable=False),
        sa.Column("projection_digest", sa.Text(), nullable=False),
        sa.Column("recipe_digest", sa.Text(), nullable=False),
        sa.Column("source_view_id", sa.BigInteger(), nullable=True),
        sa.Column("standing", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("evidence_sets_present", sa.Boolean(), nullable=False),
        sa.Column("computation_dependencies_present", sa.Boolean(), nullable=False),
        sa.Column("assertion_members_present", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_source_record_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            name=op.f("pk_source_record"),
        ),
        schema="data",
        info={"model_class": "source_record", "immutability": "admitted"},
    )
    op.execute("SET LOCAL ROLE corpus_sem_publisher")
    op.create_table(
        "reference_origin_group",
        sa.Column("project_id", sa.Text(), nullable=False),
        sa.Column("origin_group", sa.Text(), nullable=False),
        sa.Column("partition", sa.Text(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(provenance)='object' AND provenance<>'{}'::jsonb",
            name=op.f("ck_reference_origin_group_physical_e953a56fc9"),
        ),
        sa.CheckConstraint(
            "origin_group <> ''", name=op.f("ck_reference_origin_group_physical_e496f41f44")
        ),
        sa.CheckConstraint(
            "partition IN ('development','feature_fit','final_event_calibration"
            "','final_assessment')",
            name=op.f("ck_reference_origin_group_physical_93d7ebbb1a"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["data.project.project_id"],
            name=op.f("fk_reference_origin_group_project_id"),
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "origin_group", name=op.f("pk_reference_origin_group")
        ),
        schema="eval",
        info={
            "model_class": "reference_origin_group",
            "immutability": "intrinsic",
            "read_roles": ["corpus_sem_evaluator"],
        },
    )
    op.execute("SET LOCAL ROLE " + op.get_bind().dialect.identifier_preparer.quote(_migration_role))
    op.create_table(
        "record_admission",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("policy_id", sa.Text(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("calibration", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id"],
            [
                "data.source_record.realization_id",
                "data.source_record.release_id",
                "data.source_record.record_id",
                "data.source_record.interpretation_id",
            ],
            name=op.f("fk_record_admission_realization_id_release_id_record_id_interpretation_id"),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_admission_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            name=op.f("pk_record_admission"),
        ),
        schema="data",
        info={"model_class": "record_admission", "immutability": "admitted"},
    )
    op.create_table(
        "record_anchor",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("anchor_id", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("native_product_task_id", sa.BigInteger(), nullable=False),
        sa.Column("product_key", sa.Text(), nullable=False),
        sa.Column("product_digest", sa.Text(), nullable=False),
        sa.Column("projection_digest", sa.Text(), nullable=False),
        sa.Column("recipe_digest", sa.Text(), nullable=False),
        sa.Column("source_view_id", sa.BigInteger(), nullable=True),
        sa.Column("space", sa.Text(), nullable=False),
        sa.Column("pointer", sa.Text(), nullable=False),
        sa.Column("precision", sa.Text(), nullable=False),
        sa.Column("start", sa.BigInteger(), nullable=True),
        sa.Column("end", sa.BigInteger(), nullable=True),
        sa.Column("source_piece", sa.Text(), nullable=True),
        sa.Column("binding_version", sa.BigInteger(), nullable=True),
        sa.Column("binding_relationship", sa.Text(), nullable=True),
        sa.Column("binding_policy", sa.Text(), nullable=True),
        sa.Column("recognition_selected_occurrence_id", sa.Text(), nullable=True),
        sa.Column("recognition_task_id", sa.BigInteger(), nullable=True),
        sa.Column("recognition_product_key", sa.Text(), nullable=True),
        sa.Column("recognition_content_digest", sa.Text(), nullable=True),
        sa.Column("recognition_occurrence_id", sa.Text(), nullable=True),
        sa.Column("recognition_relation_id", sa.Text(), nullable=True),
        sa.Column("recognition_endpoint_role", sa.Text(), nullable=True),
        sa.Column("recognition_relation_kind", sa.Text(), nullable=True),
        sa.Column("recognition_relation_outcome", sa.Text(), nullable=True),
        sa.Column("recognition_provider_occurrence_json", sa.Text(), nullable=True),
        sa.Column("recognition_observation_json", sa.Text(), nullable=True),
        sa.CheckConstraint("position >= 0", name=op.f("ck_record_anchor_physical_9039b28f88")),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id"],
            [
                "data.source_record.realization_id",
                "data.source_record.release_id",
                "data.source_record.record_id",
                "data.source_record.interpretation_id",
            ],
            name=op.f("fk_record_anchor_realization_id_release_id_record_id_interpretation_id"),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_anchor_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "anchor_id",
            name=op.f("pk_record_anchor"),
        ),
        schema="data",
        info={"model_class": "record_anchor", "immutability": "admitted"},
    )
    op.create_table(
        "record_dependency",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("dependency", sa.Text(), nullable=False),
        sa.CheckConstraint("position >= 0", name=op.f("ck_record_dependency_physical_9039b28f88")),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id"],
            [
                "data.source_record.realization_id",
                "data.source_record.release_id",
                "data.source_record.record_id",
                "data.source_record.interpretation_id",
            ],
            name=op.f("fk_record_dependency_realization_id_release_id_record_id_interpretation_id"),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_dependency_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "position",
            name=op.f("pk_record_dependency"),
        ),
        schema="data",
        info={"model_class": "record_dependency", "immutability": "admitted"},
    )
    op.create_table(
        "record_field",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("meaning_changing", sa.Boolean(), nullable=False),
        sa.Column("evidence_status", sa.Text(), nullable=False),
        sa.Column("value_kind", sa.Text(), nullable=True),
        sa.Column("text_value", sa.Text(), nullable=True),
        sa.Column("decimal_lexical", sa.Text(), nullable=True),
        sa.Column("classification", sa.Text(), nullable=True),
        sa.Column("native_pointer", sa.Text(), nullable=True),
        sa.Column("original", sa.Text(), nullable=True),
        sa.Column("original_pieces_present", sa.Boolean(), nullable=False),
        sa.Column("evidence_sets_present", sa.Boolean(), nullable=False),
        sa.Column("alternatives_present", sa.Boolean(), nullable=False),
        sa.Column("premises_present", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("policy", sa.Text(), nullable=True),
        sa.Column("rule", sa.Text(), nullable=True),
        sa.CheckConstraint("position >= 0", name=op.f("ck_record_field_physical_9039b28f88")),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id"],
            [
                "data.source_record.realization_id",
                "data.source_record.release_id",
                "data.source_record.record_id",
                "data.source_record.interpretation_id",
            ],
            name=op.f("fk_record_field_realization_id_release_id_record_id_interpretation_id"),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_field_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "role",
            name=op.f("pk_record_field"),
        ),
        schema="data",
        info={"model_class": "record_field", "immutability": "admitted"},
    )
    op.create_table(
        "record_private_assertion",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("assertion_ref", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name=op.f("ck_record_private_assertion_physical_9039b28f88")
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id"],
            [
                "data.source_record.realization_id",
                "data.source_record.release_id",
                "data.source_record.record_id",
                "data.source_record.interpretation_id",
            ],
            name=op.f(
                "fk_record_private_assertion_realization_id_release_id_record_id_interpretation_id"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_private_assertion_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "position",
            name=op.f("pk_record_private_assertion"),
        ),
        schema="data",
        info={"model_class": "record_private_assertion", "immutability": "admitted"},
    )
    op.execute("SET LOCAL ROLE corpus_sem_publisher")
    op.create_table(
        "reference_origin_source",
        sa.Column("project_id", sa.Text(), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("origin_group", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "origin_group"],
            ["eval.reference_origin_group.project_id", "eval.reference_origin_group.origin_group"],
            name=op.f("fk_reference_origin_source_project_id_origin_group"),
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "source_uri", name=op.f("pk_reference_origin_source")
        ),
        schema="eval",
        info={
            "model_class": "reference_origin_source",
            "immutability": "intrinsic",
            "read_roles": ["corpus_sem_evaluator"],
        },
    )
    op.execute("SET LOCAL ROLE " + op.get_bind().dialect.identifier_preparer.quote(_migration_role))
    op.create_table(
        "record_alternative",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("alternative_id", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("value_kind", sa.Text(), nullable=False),
        sa.Column("text_value", sa.Text(), nullable=True),
        sa.Column("decimal_lexical", sa.Text(), nullable=True),
        sa.Column("classification", sa.Text(), nullable=True),
        sa.Column("native_pointer", sa.Text(), nullable=True),
        sa.Column("evidence_sets_present", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.CheckConstraint("position >= 0", name=op.f("ck_record_alternative_physical_9039b28f88")),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id", "role"],
            [
                "data.record_field.realization_id",
                "data.record_field.release_id",
                "data.record_field.record_id",
                "data.record_field.interpretation_id",
                "data.record_field.role",
            ],
            name=op.f(
                "fk_record_alternative_realization_id_release_id_record_id_interpretation_id_role"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_alternative_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "role",
            "alternative_id",
            name=op.f("pk_record_alternative"),
        ),
        schema="data",
        info={"model_class": "record_alternative", "immutability": "admitted"},
    )
    op.create_table(
        "record_evidence_set",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("set_id", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("ordering", sa.Text(), nullable=False),
        sa.Column("usage", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name=op.f("ck_record_evidence_set_physical_9039b28f88")
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id", "role"],
            [
                "data.record_field.realization_id",
                "data.record_field.release_id",
                "data.record_field.record_id",
                "data.record_field.interpretation_id",
                "data.record_field.role",
            ],
            name=op.f(
                "fk_record_evidence_set_realization_id_release_id_record_id_interpretation_id_role"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id"],
            [
                "data.source_record.realization_id",
                "data.source_record.release_id",
                "data.source_record.record_id",
                "data.source_record.interpretation_id",
            ],
            name=op.f(
                "fk_record_evidence_set_realization_id_release_id_record_id_interpretation_id"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_evidence_set_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "set_id",
            name=op.f("pk_record_evidence_set"),
        ),
        schema="data",
        info={"model_class": "record_evidence_set", "immutability": "admitted"},
    )
    op.create_table(
        "record_field_piece",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("original_piece", sa.Text(), nullable=True),
        sa.Column("value_piece", sa.Text(), nullable=True),
        sa.CheckConstraint("position >= 0", name=op.f("ck_record_field_piece_physical_9039b28f88")),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id", "role"],
            [
                "data.record_field.realization_id",
                "data.record_field.release_id",
                "data.record_field.record_id",
                "data.record_field.interpretation_id",
                "data.record_field.role",
            ],
            name=op.f(
                "fk_record_field_piece_realization_id_release_id_record_id_interpretation_id_role"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_field_piece_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "role",
            "position",
            name=op.f("pk_record_field_piece"),
        ),
        schema="data",
        info={"model_class": "record_field_piece", "immutability": "admitted"},
    )
    op.create_table(
        "record_occurrence_anchor",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("anchor_id", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name=op.f("ck_record_occurrence_anchor_physical_9039b28f88")
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id", "anchor_id"],
            [
                "data.record_anchor.realization_id",
                "data.record_anchor.release_id",
                "data.record_anchor.record_id",
                "data.record_anchor.interpretation_id",
                "data.record_anchor.anchor_id",
            ],
            name=op.f(
                "fk_record_occurrence_anchor_realization_id_release_id_record_id_in"
                "terpretation_id_anchor_id"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id"],
            [
                "data.source_record.realization_id",
                "data.source_record.release_id",
                "data.source_record.record_id",
                "data.source_record.interpretation_id",
            ],
            name=op.f(
                "fk_record_occurrence_anchor_realization_id_release_id_record_id_interpretation_id"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_occurrence_anchor_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "position",
            name=op.f("pk_record_occurrence_anchor"),
        ),
        schema="data",
        info={"model_class": "record_occurrence_anchor", "immutability": "admitted"},
    )
    op.create_table(
        "record_premise",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("premise_role", sa.Text(), nullable=False),
        sa.CheckConstraint("position >= 0", name=op.f("ck_record_premise_physical_9039b28f88")),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id", "premise_role"],
            [
                "data.record_field.realization_id",
                "data.record_field.release_id",
                "data.record_field.record_id",
                "data.record_field.interpretation_id",
                "data.record_field.role",
            ],
            name=op.f(
                "fk_record_premise_realization_id_release_id_record_id_interpretati"
                "on_id_premise_role"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id", "role"],
            [
                "data.record_field.realization_id",
                "data.record_field.release_id",
                "data.record_field.record_id",
                "data.record_field.interpretation_id",
                "data.record_field.role",
            ],
            name=op.f(
                "fk_record_premise_realization_id_release_id_record_id_interpretation_id_role"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_premise_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "role",
            "position",
            name=op.f("pk_record_premise"),
        ),
        schema="data",
        info={"model_class": "record_premise", "immutability": "admitted"},
    )
    op.create_table(
        "record_report",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("selected_task_id", sa.BigInteger(), nullable=False),
        sa.Column("origin_task_id", sa.BigInteger(), nullable=False),
        sa.Column("cut_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("records_present", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cut_id"], ["ops.input_cut.id"], name=op.f("fk_record_report_cut_id")
        ),
        sa.ForeignKeyConstraint(
            ["origin_task_id"], ["ops.task.id"], name=op.f("fk_record_report_origin_task_id")
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_report_realization_id_release_id"),
        ),
        sa.ForeignKeyConstraint(
            ["selected_task_id"], ["ops.task.id"], name=op.f("fk_record_report_selected_task_id")
        ),
        sa.PrimaryKeyConstraint(
            "realization_id", "release_id", "selected_task_id", name=op.f("pk_record_report")
        ),
        schema="data",
        info={"model_class": "record_report", "immutability": "admitted"},
    )
    op.create_table(
        "record_alternative_evidence",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("alternative_id", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("set_id", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name=op.f("ck_record_alternative_evidence_physical_9039b28f88")
        ),
        sa.ForeignKeyConstraint(
            [
                "realization_id",
                "release_id",
                "record_id",
                "interpretation_id",
                "role",
                "alternative_id",
            ],
            [
                "data.record_alternative.realization_id",
                "data.record_alternative.release_id",
                "data.record_alternative.record_id",
                "data.record_alternative.interpretation_id",
                "data.record_alternative.role",
                "data.record_alternative.alternative_id",
            ],
            name=op.f(
                "fk_record_alternative_evidence_realization_id_release_id_record_id"
                "_interpretation_id_role_alternative_id"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id", "set_id"],
            [
                "data.record_evidence_set.realization_id",
                "data.record_evidence_set.release_id",
                "data.record_evidence_set.record_id",
                "data.record_evidence_set.interpretation_id",
                "data.record_evidence_set.set_id",
            ],
            name=op.f(
                "fk_record_alternative_evidence_realization_id_release_id_record_id"
                "_interpretation_id_set_id"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_alternative_evidence_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "role",
            "alternative_id",
            "position",
            name=op.f("pk_record_alternative_evidence"),
        ),
        schema="data",
        info={"model_class": "record_alternative_evidence", "immutability": "admitted"},
    )
    op.create_table(
        "record_alternative_piece",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("alternative_id", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("value_piece", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name=op.f("ck_record_alternative_piece_physical_9039b28f88")
        ),
        sa.ForeignKeyConstraint(
            [
                "realization_id",
                "release_id",
                "record_id",
                "interpretation_id",
                "role",
                "alternative_id",
            ],
            [
                "data.record_alternative.realization_id",
                "data.record_alternative.release_id",
                "data.record_alternative.record_id",
                "data.record_alternative.interpretation_id",
                "data.record_alternative.role",
                "data.record_alternative.alternative_id",
            ],
            name=op.f(
                "fk_record_alternative_piece_realization_id_release_id_record_id_in"
                "terpretation_id_role_alternative_id"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_alternative_piece_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "role",
            "alternative_id",
            "position",
            name=op.f("pk_record_alternative_piece"),
        ),
        schema="data",
        info={"model_class": "record_alternative_piece", "immutability": "admitted"},
    )
    op.create_table(
        "record_assertion",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("fact_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "fact_id"],
            ["data.fact.realization_id", "data.fact.release_id", "data.fact.fact_id"],
            name=op.f("fk_record_assertion_realization_id_release_id_fact_id"),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id"],
            [
                "data.source_record.realization_id",
                "data.source_record.release_id",
                "data.source_record.record_id",
                "data.source_record.interpretation_id",
            ],
            name=op.f("fk_record_assertion_realization_id_release_id_record_id_interpretation_id"),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_assertion_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "fact_id",
            name=op.f("pk_record_assertion"),
        ),
        schema="data",
        info={"model_class": "record_assertion", "immutability": "admitted"},
    )
    op.create_table(
        "record_evidence_member",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("set_id", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("anchor_id", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name=op.f("ck_record_evidence_member_physical_9039b28f88")
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id", "anchor_id"],
            [
                "data.record_anchor.realization_id",
                "data.record_anchor.release_id",
                "data.record_anchor.record_id",
                "data.record_anchor.interpretation_id",
                "data.record_anchor.anchor_id",
            ],
            name=op.f(
                "fk_record_evidence_member_realization_id_release_id_record_id_inte"
                "rpretation_id_anchor_id"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id", "set_id"],
            [
                "data.record_evidence_set.realization_id",
                "data.record_evidence_set.release_id",
                "data.record_evidence_set.record_id",
                "data.record_evidence_set.interpretation_id",
                "data.record_evidence_set.set_id",
            ],
            name=op.f(
                "fk_record_evidence_member_realization_id_release_id_record_id_inte"
                "rpretation_id_set_id"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_evidence_member_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "set_id",
            "position",
            name=op.f("pk_record_evidence_member"),
        ),
        schema="data",
        info={"model_class": "record_evidence_member", "immutability": "admitted"},
    )
    op.create_table(
        "record_field_evidence",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("set_id", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name=op.f("ck_record_field_evidence_physical_9039b28f88")
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id", "role"],
            [
                "data.record_field.realization_id",
                "data.record_field.release_id",
                "data.record_field.record_id",
                "data.record_field.interpretation_id",
                "data.record_field.role",
            ],
            name=op.f(
                "fk_record_field_evidence_realization_id_release_id_record_id_inter"
                "pretation_id_role"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id", "set_id"],
            [
                "data.record_evidence_set.realization_id",
                "data.record_evidence_set.release_id",
                "data.record_evidence_set.record_id",
                "data.record_evidence_set.interpretation_id",
                "data.record_evidence_set.set_id",
            ],
            name=op.f(
                "fk_record_field_evidence_realization_id_release_id_record_id_inter"
                "pretation_id_set_id"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_field_evidence_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "record_id",
            "interpretation_id",
            "role",
            "position",
            name=op.f("pk_record_field_evidence"),
        ),
        schema="data",
        info={"model_class": "record_field_evidence", "immutability": "admitted"},
    )
    op.create_table(
        "record_report_member",
        sa.Column("realization_id", sa.Text(), nullable=False),
        sa.Column("release_id", sa.Text(), nullable=False),
        sa.Column("selected_task_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.BigInteger(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("interpretation_id", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0", name=op.f("ck_record_report_member_physical_9039b28f88")
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "record_id", "interpretation_id"],
            [
                "data.source_record.realization_id",
                "data.source_record.release_id",
                "data.source_record.record_id",
                "data.source_record.interpretation_id",
            ],
            name=op.f(
                "fk_record_report_member_realization_id_release_id_record_id_interpretation_id"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id", "selected_task_id"],
            [
                "data.record_report.realization_id",
                "data.record_report.release_id",
                "data.record_report.selected_task_id",
            ],
            name=op.f("fk_record_report_member_realization_id_release_id_selected_task_id"),
        ),
        sa.ForeignKeyConstraint(
            ["realization_id", "release_id"],
            ["data.realization.realization_id", "data.realization.release_id"],
            name=op.f("fk_record_report_member_realization_id_release_id"),
        ),
        sa.PrimaryKeyConstraint(
            "realization_id",
            "release_id",
            "selected_task_id",
            "position",
            name=op.f("pk_record_report_member"),
        ),
        schema="data",
        info={"model_class": "record_report_member", "immutability": "admitted"},
    )
    op.execute("SET LOCAL ROLE corpus_sem_publisher")
    op.drop_constraint(
        op.f("fk_reference_set_source_run_id"), "reference_set", schema="eval", type_="foreignkey"
    )
    op.execute("SET LOCAL ROLE " + op.get_bind().dialect.identifier_preparer.quote(_migration_role))
    op.execute(
        "DO $reference_fk$ DECLARE previous_name text:=current_user; introd"
        "uced boolean:=NOT has_column_privilege('corpus_sem_publisher','ops"
        ".run','id','REFERENCES'); BEGIN IF introduced THEN GRANT REFERENCE"
        "S(id) ON ops.run TO corpus_sem_publisher; END IF; SET LOCAL ROLE c"
        "orpus_sem_publisher; EXECUTE 'ALTER TABLE eval.reference_set ADD C"
        "ONSTRAINT fk_reference_set_source_run_id FOREIGN KEY(source_run_id"
        ") REFERENCES ops.run (id)'; EXECUTE format('SET LOCAL ROLE %I',pre"
        "vious_name); IF introduced THEN REVOKE REFERENCES(id) ON ops.run F"
        "ROM corpus_sem_publisher; END IF; END $reference_fk$"
    )
    op.execute("ALTER TABLE data.source_record OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_admission OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_anchor OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_dependency OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_field OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_private_assertion OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_alternative OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_evidence_set OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_field_piece OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_occurrence_anchor OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_premise OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_report OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_alternative_evidence OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_alternative_piece OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_assertion OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_evidence_member OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_field_evidence OWNER TO corpus_sem_publisher")
    op.execute("ALTER TABLE data.record_report_member OWNER TO corpus_sem_publisher")
    op.execute("SET LOCAL ROLE corpus_sem_publisher")
    op.execute(
        "INSERT INTO sem.physical_contract(physical_id,checks,source_digest"
        ") VALUES ('physical:044f1a0b25d8dc115e7dee2ecfe365732a54440e15c5c9"
        'd5b11a78219778f209\',\'[{"expression": "(length(operation_version)'
        ' > 0)", "name": "ck_alternative_group_physical_367a3f1b91", "relat'
        'ion": "data.alternative_group"}, {"expression": "(length(operation'
        '_id) > 0)", "name": "ck_alternative_group_physical_81a8ed4461", "r'
        'elation": "data.alternative_group"}, {"expression": "((confidence '
        "IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::"
        'numeric)))", "name": "ck_assessment_physical_506af7cc40", "relatio'
        'n": "data.assessment"}, {"expression": "((fact_id IS NULL) <> (occ'
        'urrence_id IS NULL))", "name": "ck_assessment_physical_a44e2bbc14"'
        ', "relation": "data.assessment"}, {"expression": "((counterpart_fa'
        'ct_id IS NULL) = (counterpart_occurrence_id IS NULL))", "name": "c'
        'k_assessment_physical_ba2418d4d2", "relation": "data.assessment"},'
        ' {"expression": "(data_revision > 0)", "name": "ck_batch_physical_'
        '239a1f5235", "relation": "data.batch"}, {"expression": "(outcome ='
        " ANY (ARRAY[''complete''::text, ''partial''::text, ''unanalysed'':"
        ":text, ''failed''::text]))\", \"name\": \"ck_coverage_physical_1a0"
        'a2904ca", "relation": "data.coverage"}, {"expression": "((source_o'
        "utcome IS NULL) OR (outcome =\\nCASE\\n    WHEN (source_outcome = "
        "ANY (ARRAY[''unknown''::text, ''unsupported''::text])) THEN ''unan"
        'alysed\'\'::text\\n    ELSE source_outcome\\nEND))", "name": "ck_c'
        'overage_physical_76460b9b2b", "relation": "data.coverage"}, {"expr'
        'ession": "((source_outcome IS NULL) OR (source_outcome = ANY (ARRA'
        "Y[''complete''::text, ''partial''::text, ''unknown''::text, ''unsu"
        "pported''::text, ''failed''::text])))\", \"name\": \"ck_coverage"
        '_physical_e6acac26e8", "relation": "data.coverage"}, {"expression"'
        ': "(\\"position\\" >= 0)", "name": "ck_derivation_premise_physical'
        '_9039b28f88", "relation": "data.derivation_premise"}, {"expression'
        '": "(realization_id <> input_realization_id)", "name": "ck_entity_'
        'input_physical_c3379ef8c3", "relation": "data.entity_input"}, {"ex'
        'pression": "(input_data_revision >= 0)", "name": "ck_entity_input_'
        'physical_ed2a159c88", "relation": "data.entity_input"}, {"expressi'
        'on": "(((rendition_id IS NOT NULL) AND (source_view_id IS NULL) AN'
        "D (native_address IS NULL)) OR ((rendition_id IS NULL) AND (span_i"
        "d IS NULL) AND (source_view_id IS NOT NULL) AND (native_address IS"
        ' NOT NULL)))", "name": "ck_evidence_source_physical_0a487c0ebb", "'
        'relation": "data.evidence_source"}, {"expression": "(realization_i'
        'd <> input_realization_id)", "name": "ck_fact_input_physical_c3379'
        'ef8c3", "relation": "data.fact_input"}, {"expression": "(input_dat'
        'a_revision >= 0)", "name": "ck_fact_input_physical_ed2a159c88", "r'
        'elation": "data.fact_input"}, {"expression": "(left_kind = ANY (AR'
        "RAY[''local''::text, ''known''::text]))\", \"name\": \"ck_iden"
        'tity_exclusion_physical_5b61df693c", "relation": "data.identity_ex'
        'clusion"}, {"expression": "(left_entity_id <> right_entity_id)", "'
        'name": "ck_identity_exclusion_physical_b87f376563", "relation": "d'
        'ata.identity_exclusion"}, {"expression": "(right_kind = ANY (ARRAY'
        "[''local''::text, ''known''::text]))\", \"name\": \"ck_identit"
        'y_exclusion_physical_f8edd6e4f3", "relation": "data.identity_exclu'
        'sion"}, {"expression": "((statement_entity_id IS NOT NULL) OR (sta'
        'tement_role IS NOT NULL))", "name": "ck_occurrence_context_physica'
        'l_e32eb26213", "relation": "data.occurrence_context"}, {"expressio'
        "n\": \"(establishment = ANY (ARRAY[''stated''::text, ''derived"
        "''::text, ''agent_asserted''::text]))\", \"name\": \"ck_occurren"
        'ce_establishment_physical_ef563c839f", "relation": "data.occurrenc'
        'e_establishment"}, {"expression": "(generation >= 0)", "name": "ck'
        '_project_physical_8313aadc77", "relation": "data.project"}, {"expr'
        'ession": "(source_revision >= 0)", "name": "ck_publication_intent_'
        'physical_0ed0eed26f", "relation": "data.publication_intent"}, {"ex'
        "pression\": \"((source_capture_id <> ''''::text) AND (operation_"
        "id <> ''''::text) AND (projection_id <> ''''::text))\", \"na"
        'me": "ck_publication_intent_physical_55ae0caf21", "relation": "dat'
        'a.publication_intent"}, {"expression": "(state = ANY (ARRAY[\'\'ac'
        "tive''::text, ''building''::text, ''retired''::text, ''failed''::t"
        'ext]))", "name": "ck_realization_physical_3a1078e1fe", "relation":'
        ' "data.realization"}, {"expression": "(data_revision >= 0)", "name'
        '": "ck_realization_physical_8c71a80efa", "relation": "data.realiza'
        'tion"}, {"expression": "(\\"position\\" >= 0)", "name": "ck_record'
        '_alternative_physical_9039b28f88", "relation": "data.record_altern'
        'ative"}, {"expression": "(\\"position\\" >= 0)", "name": "ck_recor'
        'd_alternative_evidence_physical_9039b28f88", "relation": "data.rec'
        'ord_alternative_evidence"}, {"expression": "(\\"position\\" >= 0)"'
        ', "name": "ck_record_alternative_piece_physical_9039b28f88", "rela'
        'tion": "data.record_alternative_piece"}, {"expression": "(\\"posit'
        'ion\\" >= 0)", "name": "ck_record_anchor_physical_9039b28f88", "re'
        'lation": "data.record_anchor"}, {"expression": "(\\"position\\" >='
        ' 0)", "name": "ck_record_dependency_physical_9039b28f88", "relatio'
        'n": "data.record_dependency"}, {"expression": "(\\"position\\" >= '
        '0)", "name": "ck_record_evidence_member_physical_9039b28f88", "rel'
        'ation": "data.record_evidence_member"}, {"expression": "(\\"positi'
        'on\\" >= 0)", "name": "ck_record_evidence_set_physical_9039b28f88"'
        ', "relation": "data.record_evidence_set"}, {"expression": "(\\"pos'
        'ition\\" >= 0)", "name": "ck_record_field_physical_9039b28f88", "r'
        'elation": "data.record_field"}, {"expression": "(\\"position\\" >='
        ' 0)", "name": "ck_record_field_evidence_physical_9039b28f88", "rel'
        'ation": "data.record_field_evidence"}, {"expression": "(\\"positio'
        'n\\" >= 0)", "name": "ck_record_field_piece_physical_9039b28f88", '
        '"relation": "data.record_field_piece"}, {"expression": "(\\"positi'
        'on\\" >= 0)", "name": "ck_record_occurrence_anchor_physical_9039b2'
        '8f88", "relation": "data.record_occurrence_anchor"}, {"expression"'
        ': "(\\"position\\" >= 0)", "name": "ck_record_premise_physical_903'
        '9b28f88", "relation": "data.record_premise"}, {"expression": "(\\"'
        'position\\" >= 0)", "name": "ck_record_private_assertion_physical_'
        '9039b28f88", "relation": "data.record_private_assertion"}, {"expre'
        'ssion": "(\\"position\\" >= 0)", "name": "ck_record_report_member_'
        'physical_9039b28f88", "relation": "data.record_report_member"}, {"'
        "expression\": \"((kind <> ''integer''::text) OR (text_value ~ '"
        '\'^[+-]?[0-9]+$\'\'::text))", "name": "ck_typed_value_physical_053'
        'b27098a", "relation": "data.typed_value"}, {"expression": "\\nCASE'
        "\\n    WHEN (integer_value IS NULL) THEN true\\n    ELSE ((integer"
        "_value = trunc(integer_value)) AND (integer_value = (text_value)::"
        'numeric))\\nEND", "name": "ck_typed_value_physical_05579de47e", "r'
        'elation": "data.typed_value"}, {"expression": "\\nCASE\\n    WHEN '
        "(numeric_value IS NULL) THEN true\\n    ELSE (numeric_value = (dec"
        'imal_lexical)::numeric)\\nEND", "name": "ck_typed_value_physical_1'
        '338461682", "relation": "data.typed_value"}, {"expression": "((dec'
        "imal_lexical IS NULL) OR (decimal_lexical ~ ''^[+-]?([0-9]+(\\\\.["
        '0-9]*)?|\\\\.[0-9]+)([eE][+-]?[0-9]+)?$\'\'::text))", "name": "ck_'
        'typed_value_physical_6d9834e238", "relation": "data.typed_value"},'
        ' {"expression": "((numeric_value IS NULL) OR (kind = ANY (ARRAY[\''
        "'decimal''::text, ''number''::text])))\", \"name\": \"ck_typed_"
        'value_physical_77f076c9cb", "relation": "data.typed_value"}, {"exp'
        "ression\": \"((integer_value IS NULL) OR (kind = ''integer''::te"
        'xt))", "name": "ck_typed_value_physical_b4572e9f51", "relation": "'
        'data.typed_value"}, {"expression": "(kind = ANY (ARRAY[\'\'string'
        "''::text, ''integer''::text, ''decimal''::text, ''number''::text, "
        "''boolean''::text, ''entity''::text, ''null''::text, ''missing''::"
        "text, ''sequence''::text, ''mapping''::text, ''record''::text, ''i"
        "nterval''::text, ''expression''::text, ''date''::text, ''datetime'"
        "'::text, ''float''::text, ''opaque''::text]))\", \"name\": \""
        'ck_typed_value_physical_d01245fe40", "relation": "data.typed_value'
        "\"}, {\"expression\": \"(((kind = ANY (ARRAY[''string''::text, '"
        "'integer''::text, ''date''::text, ''datetime''::text, ''float''::t"
        "ext, ''expression''::text, ''missing''::text])) AND (text_value IS"
        " NOT NULL) AND (decimal_lexical IS NULL) AND (boolean_value IS NUL"
        "L) AND (entity_id IS NULL) AND (opaque_payload IS NULL)) OR ((kind"
        " = ANY (ARRAY[''decimal''::text, ''number''::text])) AND (text_val"
        "ue IS NULL) AND (decimal_lexical IS NOT NULL) AND (boolean_value I"
        "S NULL) AND (entity_id IS NULL) AND (opaque_payload IS NULL)) OR ("
        "(kind = ''boolean''::text) AND (text_value IS NULL) AND (decimal_l"
        "exical IS NULL) AND (boolean_value IS NOT NULL) AND (entity_id IS "
        "NULL) AND (opaque_payload IS NULL)) OR ((kind = ''entity''::text) "
        "AND (text_value IS NULL) AND (decimal_lexical IS NULL) AND (boolea"
        "n_value IS NULL) AND (entity_id IS NOT NULL) AND (opaque_payload I"
        "S NULL)) OR ((kind = ''opaque''::text) AND (text_value IS NULL) AN"
        "D (decimal_lexical IS NULL) AND (boolean_value IS NULL) AND (entit"
        "y_id IS NULL) AND (opaque_payload IS NOT NULL)) OR ((kind = ANY (A"
        "RRAY[''null''::text, ''sequence''::text, ''mapping''::text, ''reco"
        "rd''::text, ''interval''::text])) AND (text_value IS NULL) AND (de"
        "cimal_lexical IS NULL) AND (boolean_value IS NULL) AND (entity_id "
        'IS NULL) AND (opaque_payload IS NULL)))", "name": "ck_typed_value_'
        'physical_dcfa9b38a9", "relation": "data.typed_value"}, {"expressio'
        'n": "(\\"position\\" >= 0)", "name": "ck_value_role_physical_9039b'
        '28f88", "relation": "data.value_role"}, {"expression": "(split = A'
        "NY (ARRAY[''dev''::text, ''test''::text, ''reserved''::text]))"
        '", "name": "ck_document_split_physical_a319d8e82e", "relation": "e'
        'val.document_split"}, {"expression": "(((rendition_id IS NOT NULL)'
        " AND (source_view_id IS NULL) AND (projection_digest IS NULL)) OR "
        "((rendition_id IS NULL) AND (source_view_id IS NOT NULL) AND (proj"
        'ection_digest IS NOT NULL)))", "name": "ck_reference_frame_physica'
        'l_01217a18f9", "relation": "eval.reference_frame"}, {"expression":'
        ' "(version > 0)", "name": "ck_reference_frame_physical_429634fbaa"'
        ', "relation": "eval.reference_frame"}, {"expression": "(partition '
        "= ANY (ARRAY[''development''::text, ''feature_fit''::text, ''final"
        "_event_calibration''::text, ''final_assessment''::text]))\", "
        '"name": "ck_reference_origin_group_physical_93d7ebbb1a", "relation'
        '": "eval.reference_origin_group"}, {"expression": "(origin_group <'
        "> ''''::text)\", \"name\": \"ck_reference_origin_group_physical_e4"
        '96f41f44", "relation": "eval.reference_origin_group"}, {"expressio'
        "n\": \"((jsonb_typeof(provenance) = ''object''::text) AND (prove"
        "nance <> ''{}''::jsonb))\", \"name\": \"ck_reference_origin_group_"
        'physical_e953a56fc9", "relation": "eval.reference_origin_group"}, '
        "{\"expression\": \"(pass_kind = ANY (ARRAY[''A''::text, ''B''"
        "::text, ''C''::text]))\", \"name\": \"ck_reference_pass_physical_7"
        '182d42311", "relation": "eval.reference_pass"}, {"expression": "(s'
        "plit = ANY (ARRAY[''dev''::text, ''test''::text]))\", \"name"
        '": "ck_reference_set_physical_23de252598", "relation": "eval.refer'
        'ence_set"}, {"expression": "(((rendition_id IS NOT NULL) AND (sour'
        "ce_view_id IS NULL) AND (projection_digest IS NULL)) OR ((renditio"
        "n_id IS NULL) AND (source_view_id IS NOT NULL) AND (projection_dig"
        'est IS NOT NULL)))", "name": "ck_reference_unit_physical_01217a18f'
        '9", "relation": "eval.reference_unit"}, {"expression": "(ordinal >'
        '= 0)", "name": "ck_observation_physical_ee668cd4ef", "relation": "'
        'kb.observation"}, {"expression": "(role <> \'\'\'\'::text)", "name'
        '": "ck_observation_input_physical_08d176bdbd", "relation": "kb.obs'
        'ervation_input"}, {"expression": "(\\"position\\" >= 0)", "name": '
        '"ck_observation_input_physical_9039b28f88", "relation": "kb.observ'
        'ation_input"}, {"expression": "(input_index >= 0)", "name": "ck_pd'
        'f_mapping_report_physical_61d721fcae", "relation": "kb.pdf_mapping'
        '_report"}, {"expression": "(report_index >= 0)", "name": "ck_pdf_m'
        'apping_report_physical_9c8bca1fd0", "relation": "kb.pdf_mapping_re'
        "port\"}, {\"expression\": \"(kind = ANY (ARRAY[''item''::text, '"
        "'cell''::text, ''formula''::text, ''chart''::text, ''text''::text,"
        " ''region''::text]))\", \"name\": \"ck_pdf_occurrence_physical_367"
        '474e9a3", "relation": "kb.pdf_occurrence"}, {"expression": "(NOT ('
        "pointer IS DISTINCT FROM (body ->> ''pointer''::text)))\", \"nam"
        'e": "ck_pdf_occurrence_physical_4c3854096c", "relation": "kb.pdf_o'
        'ccurrence"}, {"expression": "(\\"precision\\" = ANY (ARRAY[\'\'unk'
        "nown''::text, ''coarse''::text, ''inherited''::text, ''block''::te"
        "xt, ''item''::text, ''cell''::text, ''word''::text, ''glyph''::tex"
        't]))", "name": "ck_pdf_occurrence_physical_77605f0884", "relation"'
        ': "kb.pdf_occurrence"}, {"expression": "(occurrence_id <> \'\'\'\''
        '::text)", "name": "ck_pdf_occurrence_physical_ec6f050edd", "relati'
        'on": "kb.pdf_occurrence"}, {"expression": "(coverage_id <> \'\'\''
        '\'::text)", "name": "ck_pdf_product_coverage_physical_93d06b5b0d",'
        ' "relation": "kb.pdf_product_coverage"}, {"expression": "(family ='
        " ANY (ARRAY[''coverage''::text, ''health''::text, ''input''::text,"
        " ''mapping_report''::text, ''native_metadata''::text, ''occurrence"
        "''::text, ''relation''::text, ''request_outcome''::text]))"
        '", "name": "ck_pdf_record_companion_family_a1f36c0d0c", "relation"'
        ': "kb.pdf_record_companion"}, {"expression": "(product_id = revisi'
        'on_id)", "name": "ck_pdf_record_companion_physical_a18559f6de", "r'
        'elation": "kb.pdf_record_companion"}, {"expression": "(jsonb_typeo'
        "f(body) = ''object''::text)\", \"name\": \"ck_pdf_record_companion"
        '_physical_c92e13f700", "relation": "kb.pdf_record_companion"}, {"e'
        'xpression": "(octet_length((body)::text) <= 65536)", "name": "ck_p'
        'df_record_companion_physical_fb42f25a72", "relation": "kb.pdf_reco'
        'rd_companion"}, {"expression": "(family = ANY (ARRAY[\'\'coverage'
        "''::text, ''health''::text, ''input''::text, ''mapping_report''::t"
        "ext, ''native_metadata''::text, ''occurrence''::text, ''relation''"
        "::text, ''request_outcome''::text]))\", \"name\": \"ck_pdf_record_"
        'companion_field_family_a1f36c0d0c", "relation": "kb.pdf_record_com'
        'panion_field"}, {"expression": "(field_name = ANY (ARRAY[\'\'text'
        "''::text, ''value''::text]))\", \"name\": \"ck_pdf_record_compan"
        'ion_field_field_name_50e2349d3e", "relation": "kb.pdf_record_compa'
        "nion_field\"}, {\"expression\": \"(((family = ''native_metadata'':"
        ":text) AND (field_name = ''value''::text) AND (scalar_kind = ''y''"
        "::text)) OR ((family = ''occurrence''::text) AND (field_name = ''t"
        "ext''::text) AND (scalar_kind = ''s''::text)))\", \"name\": \"ck"
        '_pdf_record_companion_field_physical_795eae16ab", "relation": "kb.'
        'pdf_record_companion_field"}, {"expression": "(product_id = revisi'
        'on_id)", "name": "ck_pdf_record_companion_field_physical_a18559f6d'
        'e", "relation": "kb.pdf_record_companion_field"}, {"expression": "'
        "(scalar_kind = ANY (ARRAY[''s''::text, ''y''::text]))\", \"n"
        'ame": "ck_pdf_record_companion_field_scalar_kind_775eba9be0", "rel'
        'ation": "kb.pdf_record_companion_field"}, {"expression": "(product'
        '_id = revision_id)", "name": "ck_pdf_record_endpoint_physical_a185'
        '59f6de", "relation": "kb.pdf_record_endpoint"}, {"expression": "(o'
        'rdinal >= 0)", "name": "ck_pdf_record_endpoint_physical_ee668cd4ef'
        '", "relation": "kb.pdf_record_endpoint"}, {"expression": "(ordinal'
        ' >= 0)", "name": "ck_pdf_record_membership_ordinal_ee668cd4ef", "r'
        'elation": "kb.pdf_record_membership"}, {"expression": "((value_kin'
        "d = ''scalar''::text) OR (scalar_json IS NULL))\", \"name\": \"ck_"
        'pdf_record_membership_physical_341b42c0f9", "relation": "kb.pdf_re'
        "cord_membership\"}, {\"expression\": \"((value_kind = ''record''::"
        'text) = (record_id IS NOT NULL))", "name": "ck_pdf_record_membersh'
        'ip_physical_8028c34622", "relation": "kb.pdf_record_membership"}, '
        '{"expression": "((member_key IS NULL) OR (member_key_stream_id IS '
        'NULL))", "name": "ck_pdf_record_membership_physical_8bf5b8b4d7", "'
        'relation": "kb.pdf_record_membership"}, {"expression": "(octet_len'
        "gth(convert_to((scalar_json)::text, ''UTF8''::name)) <= 65536)"
        '", "name": "ck_pdf_record_membership_physical_b66e6eb309", "relati'
        'on": "kb.pdf_record_membership"}, {"expression": "((value_kind = '
        "''parts''::text) = (stream_id IS NOT NULL))\", \"name\": \"ck_pdf_"
        'record_membership_physical_df9d6518cd", "relation": "kb.pdf_record'
        '_membership"}, {"expression": "(value_kind = ANY (ARRAY[\'\'parts'
        "''::text, ''record''::text, ''scalar''::text]))\", \"name\""
        ': "ck_pdf_record_membership_value_kind_1ee79cbd9a", "relation": "k'
        'b.pdf_record_membership"}, {"expression": "(family = ANY (ARRAY[\''
        "'cell''::text, ''detail''::text, ''header''::text, ''node''::text,"
        " ''page''::text, ''provenance''::text, ''reference''::text, ''tabl"
        'e\'\'::text]))", "name": "ck_pdf_record_native_family_896b469851",'
        ' "relation": "kb.pdf_record_native"}, {"expression": "(native_type'
        " <> ''''::text)\", \"name\": \"ck_pdf_record_native_physical_1e27d"
        '9c8ce", "relation": "kb.pdf_record_native"}, {"expression": "(json'
        "b_typeof(structure_json) = ''object''::text)\", \"name\": \"ck_pdf"
        '_record_native_physical_39016badae", "relation": "kb.pdf_record_na'
        'tive"}, {"expression": "((native_address IS NULL) <> (native_addre'
        'ss_stream_id IS NULL))", "name": "ck_pdf_record_native_physical_4c'
        '7b8c414a", "relation": "kb.pdf_record_native"}, {"expression": "(j'
        "sonb_typeof(scalars_json) = ''object''::text)\", \"name\": \"ck_pd"
        'f_record_native_physical_af247a6f3c", "relation": "kb.pdf_record_n'
        'ative"}, {"expression": "(octet_length(convert_to((structure_json)'
        "::text, ''UTF8''::name)) <= 65536)\", \"name\": \"ck_pdf_record_na"
        'tive_physical_c09752f060", "relation": "kb.pdf_record_native"}, {"'
        "expression\": \"(octet_length(convert_to((scalars_json)::text, ''U"
        'TF8\'\'::name)) <= 65536)", "name": "ck_pdf_record_native_physical'
        '_c4ce4d92f6", "relation": "kb.pdf_record_native"}, {"expression": '
        '"(record_id <> \'\'\'\'::text)", "name": "ck_pdf_record_native_phy'
        'sical_d10d461f9b", "relation": "kb.pdf_record_native"}, {"expressi'
        'on": "((native_pointer IS NULL) <> (native_pointer_stream_id IS NU'
        'LL))", "name": "ck_pdf_record_reference_physical_15d32f6137", "rel'
        'ation": "kb.pdf_record_reference"}, {"expression": "(((field_name '
        "= ANY (ARRAY[''source_cell_id''::text, ''target_cell_id''::text]))"
        " AND (native_pointer ~ ''^-?[0-9]+$''::text)) OR ((field_name <> A"
        "LL (ARRAY[''source_cell_id''::text, ''target_cell_id''::text])) AN"
        "D (native_pointer ~~ ''#%''::text)))\", \"name\": \"ck_pdf_record_"
        'reference_physical_84ee799da6", "relation": "kb.pdf_record_referen'
        'ce"}, {"expression": "(reference_id <> \'\'\'\'::text)", "name": "'
        'ck_pdf_record_reference_physical_b4d49caa5d", "relation": "kb.pdf_'
        "record_reference\"}, {\"expression\": \"(relation_id <> ''''::text"
        ')", "name": "ck_pdf_relation_physical_58def7fcc7", "relation": "kb'
        '.pdf_relation"}, {"expression": "(kind = ANY (ARRAY[\'\'correspond'
        "ence''::text, ''decision''::text]))\", \"name\": \"ck_pdf_relati"
        'on_physical_fa34f4062b", "relation": "kb.pdf_relation"}, {"express'
        'ion": "(endpoint_index >= 0)", "name": "ck_pdf_relation_endpoint_p'
        'hysical_379ac917ae", "relation": "kb.pdf_relation_endpoint"}, {"ex'
        "pression\": \"(role = ANY (ARRAY[''input''::text, ''output''"
        "::text, ''alternative''::text, ''evidence''::text]))\", \"na"
        'me": "ck_pdf_relation_endpoint_physical_41bc0f1575", "relation": "'
        'kb.pdf_relation_endpoint"}, {"expression": "(artifact_digest = enc'
        "ode(sha256(content), ''hex''::text))\", \"name\": \"ck_source_arti"
        'fact_physical_b9e3edc5d9", "relation": "kb.source_artifact"}, {"ex'
        'pression": "(key <> \'\'\'\'::text)", "name": "ck_source_view_phys'
        'ical_1d77c7a418", "relation": "kb.source_view"}, {"expression": "('
        'native_build_id = native_revision_id)", "name": "ck_source_view_ph'
        'ysical_73dfcc4ba8", "relation": "kb.source_view"}, {"expression": '
        "\"(membership = ANY (ARRAY[''direct''::text, ''descendants'"
        '\'::text]))", "name": "ck_source_view_physical_e3320d3f8a", "relat'
        'ion": "kb.source_view"}, {"expression": "((source_position IS NULL'
        ') OR (source_position >= 0))", "name": "ck_measurement_physical_a0'
        '486ccc73", "relation": "ops.measurement"}, {"expression": "((confi'
        "guration_schema_digest IS NULL) OR (configuration_schema_digest ~ "
        "''^[0-9a-f]{64}$''::text))\", \"name\": \"ck_method_physical_95ee0"
        '996a8", "relation": "ops.method"}, {"expression": "(native_build_i'
        'd = native_revision_id)", "name": "ck_native_region_artifact_physi'
        'cal_73dfcc4ba8", "relation": "ops.native_region_artifact"}, {"expr'
        'ession": "(end_offset > start_offset)", "name": "ck_native_source_'
        'frame_sentence_physical_01f330ec6a", "relation": "ops.native_sourc'
        'e_frame_sentence"}, {"expression": "(start_offset >= 0)", "name": '
        '"ck_native_source_frame_sentence_physical_43e7c4875a", "relation":'
        ' "ops.native_source_frame_sentence"}, {"expression": "(membership '
        "= ANY (ARRAY[''direct''::text, ''descendants''::text]))\", "
        '"name": "ck_native_source_frame_source_physical_6fc6fa39d4", "rela'
        'tion": "ops.native_source_frame_source"}, {"expression": "(role = '
        "ANY (ARRAY[''primary''::text, ''ancestor_context''::text]))"
        '", "name": "ck_native_source_frame_source_physical_c2fa28fa87", "r'
        'elation": "ops.native_source_frame_source"}, {"expression": "(byte'
        '_length >= 0)", "name": "ck_pdf_artifact_part_byte_length_0392ce7a'
        'b3", "relation": "ops.pdf_artifact_part"}, {"expression": "(byte_o'
        'ffset >= 0)", "name": "ck_pdf_artifact_part_byte_offset_5dc7051d0c'
        '", "relation": "ops.pdf_artifact_part"}, {"expression": "(ordinal '
        '>= 0)", "name": "ck_pdf_artifact_part_ordinal_ee668cd4ef", "relati'
        'on": "ops.pdf_artifact_part"}, {"expression": "(sha256_digest = en'
        "code(sha256(body), ''hex''::text))\", \"name\": \"ck_pdf_artifact_"
        'part_physical_266e3bac59", "relation": "ops.pdf_artifact_part"}, {'
        '"expression": "(byte_length <= 65536)", "name": "ck_pdf_artifact_p'
        'art_physical_3bbd16db25", "relation": "ops.pdf_artifact_part"}, {"'
        'expression": "(byte_length = octet_length(body))", "name": "ck_pdf'
        '_artifact_part_physical_9cde4d345e", "relation": "ops.pdf_artifact'
        '_part"}, {"expression": "(byte_length > 0)", "name": "ck_pdf_artif'
        'act_part_physical_f369db0b22", "relation": "ops.pdf_artifact_part"'
        '}, {"expression": "(byte_length >= 0)", "name": "ck_pdf_artifact_s'
        'tream_byte_length_0392ce7ab3", "relation": "ops.pdf_artifact_strea'
        'm"}, {"expression": "(serialization_sha256 ~ \'\'^[0-9a-f]{64}$\''
        '\'::text)", "name": "ck_pdf_artifact_stream_physical_353c63835f", '
        '"relation": "ops.pdf_artifact_stream"}, {"expression": "(encoding_'
        "profile <> ''''::text)\", \"name\": \"ck_pdf_artifact_stream_physi"
        'cal_66ee4db5f7", "relation": "ops.pdf_artifact_stream"}, {"express'
        'ion": "(byte_root ~ \'\'^[0-9a-f]{64}$\'\'::text)", "name": "ck_pd'
        'f_artifact_stream_physical_860f4eb238", "relation": "ops.pdf_artif'
        'act_stream"}, {"expression": "(stream_id <> \'\'\'\'::text)", "nam'
        'e": "ck_pdf_artifact_stream_physical_94d0a9f5c9", "relation": "ops'
        '.pdf_artifact_stream"}, {"expression": "(kind = ANY (ARRAY[\'\'int'
        "egrated''::text, ''native''::text]))\", \"name\": \"ck_pdf_froze"
        'n_build_kind_41bc3f952e", "relation": "ops.pdf_frozen_build"}, {"e'
        "xpression\": \"(kind = ANY (ARRAY[''native''::text, ''recognit"
        "ion_observation''::text, ''integrated''::text]))\", \"name\": \""
        'ck_pdf_product_physical_2b69fdd7c7", "relation": "ops.pdf_product"'
        "}, {\"expression\": \"(contract_digest ~ ''^[0-9a-f]{64}$''::text"
        ')", "name": "ck_pdf_product_physical_361bb11ec1", "relation": "ops'
        '.pdf_product"}, {"expression": "(product_key <> \'\'\'\'::text)", '
        '"name": "ck_pdf_product_physical_37bf79141e", "relation": "ops.pdf'
        '_product"}, {"expression": "(content_digest ~ \'\'^[0-9a-f]{64}$\''
        '\'::text)", "name": "ck_pdf_product_physical_6452181ff1", "relatio'
        'n": "ops.pdf_product"}, {"expression": "(descriptor = ops.pdf_prod'
        'uct_descriptor(payload))", "name": "ck_pdf_product_body_physical_a'
        'cbf4a8f01", "relation": "ops.pdf_product_body"}, {"expression": "('
        '(task_id <> input_task_id) OR (product_key <> input_product_key))"'
        ', "name": "ck_pdf_product_input_physical_6108ddec8c", "relation": '
        '"ops.pdf_product_input"}, {"expression": "(input_index >= 0)", "na'
        'me": "ck_pdf_product_input_physical_61d721fcae", "relation": "ops.'
        'pdf_product_input"}, {"expression": "(role = ANY (ARRAY[\'\'struct'
        "ural''::text, ''recognition''::text, ''alternative''::text, ''poli"
        'cy_input\'\'::text]))", "name": "ck_pdf_product_input_physical_afd'
        '3c389de", "relation": "ops.pdf_product_input"}, {"expression": "(k'
        "ind = ANY (ARRAY[''integrated''::text, ''native''::text]))"
        '", "name": "ck_pdf_published_revision_kind_41bc3f952e", "relation"'
        ': "ops.pdf_published_revision"}, {"expression": "(contract_version'
        " = ''pdf-native-records-v1''::text)\", \"name\": \"ck_pdf_record_d"
        'ocument_contract_version_47929bf068", "relation": "ops.pdf_record_'
        'document"}, {"expression": "(mapping_profile = \'\'pdf-native-reco'
        'rds-v1\'\'::text)", "name": "ck_pdf_record_document_mapping_profil'
        'e_e3d5e39c85", "relation": "ops.pdf_record_document"}, {"expressio'
        'n": "(product_id <> \'\'\'\'::text)", "name": "ck_pdf_record_docum'
        'ent_physical_1246cec1c1", "relation": "ops.pdf_record_document"}, '
        '{"expression": "(source_digest ~ \'\'^[0-9a-f]{64}$\'\'::text)", "'
        'name": "ck_pdf_record_document_physical_1b32a362eb", "relation": "'
        'ops.pdf_record_document"}, {"expression": "(native_schema_digest ~'
        " ''^[0-9a-f]{64}$''::text)\", \"name\": \"ck_pdf_record_document_p"
        'hysical_26e3a40d89", "relation": "ops.pdf_record_document"}, {"exp'
        'ression": "(revision_id <> \'\'\'\'::text)", "name": "ck_pdf_recor'
        'd_document_physical_b85b787d88", "relation": "ops.pdf_record_docum'
        'ent"}, {"expression": "(byte_length >= 0)", "name": "ck_pdf_stage_'
        'artifact_part_byte_length_0392ce7ab3", "relation": "ops.pdf_stage_'
        'artifact_part"}, {"expression": "(byte_offset >= 0)", "name": "ck_'
        'pdf_stage_artifact_part_byte_offset_5dc7051d0c", "relation": "ops.'
        'pdf_stage_artifact_part"}, {"expression": "(ordinal >= 0)", "name"'
        ': "ck_pdf_stage_artifact_part_ordinal_ee668cd4ef", "relation": "op'
        's.pdf_stage_artifact_part"}, {"expression": "(sha256_digest = enco'
        "de(sha256(body), ''hex''::text))\", \"name\": \"ck_pdf_stage_artif"
        'act_part_physical_266e3bac59", "relation": "ops.pdf_stage_artifact'
        '_part"}, {"expression": "(byte_length <= 65536)", "name": "ck_pdf_'
        'stage_artifact_part_physical_3bbd16db25", "relation": "ops.pdf_sta'
        'ge_artifact_part"}, {"expression": "(byte_length = octet_length(bo'
        'dy))", "name": "ck_pdf_stage_artifact_part_physical_9cde4d345e", "'
        'relation": "ops.pdf_stage_artifact_part"}, {"expression": "(produc'
        't_id = revision_id)", "name": "ck_pdf_stage_artifact_part_physical'
        '_a18559f6de", "relation": "ops.pdf_stage_artifact_part"}, {"expres'
        'sion": "(byte_length > 0)", "name": "ck_pdf_stage_artifact_part_ph'
        'ysical_f369db0b22", "relation": "ops.pdf_stage_artifact_part"}, {"'
        'expression": "(byte_length >= 0)", "name": "ck_pdf_stage_artifact_'
        'stream_byte_length_0392ce7ab3", "relation": "ops.pdf_stage_artifac'
        't_stream"}, {"expression": "(serialization_sha256 ~ \'\'^[0-9a-f]{'
        '64}$\'\'::text)", "name": "ck_pdf_stage_artifact_stream_physical_3'
        '53c63835f", "relation": "ops.pdf_stage_artifact_stream"}, {"expres'
        'sion": "(encoding_profile <> \'\'\'\'::text)", "name": "ck_pdf_sta'
        'ge_artifact_stream_physical_66ee4db5f7", "relation": "ops.pdf_stag'
        'e_artifact_stream"}, {"expression": "(byte_root ~ \'\'^[0-9a-f]{64'
        '}$\'\'::text)", "name": "ck_pdf_stage_artifact_stream_physical_860'
        'f4eb238", "relation": "ops.pdf_stage_artifact_stream"}, {"expressi'
        'on": "(stream_id <> \'\'\'\'::text)", "name": "ck_pdf_stage_artifa'
        'ct_stream_physical_94d0a9f5c9", "relation": "ops.pdf_stage_artifac'
        't_stream"}, {"expression": "(product_id = revision_id)", "name": "'
        'ck_pdf_stage_artifact_stream_physical_a18559f6de", "relation": "op'
        's.pdf_stage_artifact_stream"}, {"expression": "(attempt > 0)", "na'
        'me": "ck_pdf_stage_build_physical_0c8a59b69d", "relation": "ops.pd'
        'f_stage_build"}, {"expression": "(source_digest ~ \'\'^[0-9a-f]{64'
        '}$\'\'::text)", "name": "ck_pdf_stage_build_physical_1b32a362eb", '
        '"relation": "ops.pdf_stage_build"}, {"expression": "(recipe_digest'
        " ~ ''^[0-9a-f]{64}$''::text)\", \"name\": \"ck_pdf_stage_build_phy"
        'sical_3058c3002b", "relation": "ops.pdf_stage_build"}, {"expressio'
        'n": "(schema_digest ~ \'\'^[0-9a-f]{64}$\'\'::text)", "name": "ck_'
        'pdf_stage_build_physical_6416099f87", "relation": "ops.pdf_stage_b'
        'uild"}, {"expression": "(build_id <> \'\'\'\'::text)", "name": "ck'
        '_pdf_stage_build_physical_8147daae94", "relation": "ops.pdf_stage_'
        "build\"}, {\"expression\": \"(state = ANY (ARRAY[''abandoned''::te"
        "xt, ''frozen''::text, ''open''::text, ''published''::text]))"
        '", "name": "ck_pdf_stage_build_state_8d8dc4ae4a", "relation": "ops'
        '.pdf_stage_build"}, {"expression": "(family = ANY (ARRAY[\'\'cover'
        "age''::text, ''health''::text, ''input''::text, ''mapping_report''"
        "::text, ''native_metadata''::text, ''occurrence''::text, ''relatio"
        "n''::text, ''request_outcome''::text]))\", \"name\": \"ck_pdf_st"
        'age_companion_family_a1f36c0d0c", "relation": "ops.pdf_stage_compa'
        'nion"}, {"expression": "(product_id = revision_id)", "name": "ck_p'
        'df_stage_companion_physical_a18559f6de", "relation": "ops.pdf_stag'
        'e_companion"}, {"expression": "(jsonb_typeof(body) = \'\'object\''
        '\'::text)", "name": "ck_pdf_stage_companion_physical_c92e13f700", '
        '"relation": "ops.pdf_stage_companion"}, {"expression": "(octet_len'
        'gth((body)::text) <= 65536)", "name": "ck_pdf_stage_companion_phys'
        'ical_fb42f25a72", "relation": "ops.pdf_stage_companion"}, {"expres'
        "sion\": \"(family = ANY (ARRAY[''coverage''::text, ''health'"
        "'::text, ''input''::text, ''mapping_report''::text, ''native_metad"
        "ata''::text, ''occurrence''::text, ''relation''::text, ''request_o"
        'utcome\'\'::text]))", "name": "ck_pdf_stage_companion_field_family'
        '_a1f36c0d0c", "relation": "ops.pdf_stage_companion_field"}, {"expr'
        "ession\": \"(field_name = ANY (ARRAY[''text''::text, ''value'"
        '\'::text]))", "name": "ck_pdf_stage_companion_field_field_name_50e'
        '2349d3e", "relation": "ops.pdf_stage_companion_field"}, {"expressi'
        "on\": \"(((family = ''native_metadata''::text) AND (field_name ="
        " ''value''::text) AND (scalar_kind = ''y''::text)) OR ((family = '"
        "'occurrence''::text) AND (field_name = ''text''::text) AND (scalar"
        "_kind = ''s''::text)))\", \"name\": \"ck_pdf_stage_companion_field"
        '_physical_795eae16ab", "relation": "ops.pdf_stage_companion_field"'
        '}, {"expression": "(product_id = revision_id)", "name": "ck_pdf_st'
        'age_companion_field_physical_a18559f6de", "relation": "ops.pdf_sta'
        'ge_companion_field"}, {"expression": "(scalar_kind = ANY (ARRAY[\''
        "'s''::text, ''y''::text]))\", \"name\": \"ck_pdf_stage_companio"
        'n_field_scalar_kind_775eba9be0", "relation": "ops.pdf_stage_compan'
        'ion_field"}, {"expression": "(contract_version = \'\'pdf-native-re'
        'cords-v1\'\'::text)", "name": "ck_pdf_stage_document_contract_vers'
        'ion_47929bf068", "relation": "ops.pdf_stage_document"}, {"expressi'
        "on\": \"(mapping_profile = ''pdf-native-records-v1''::text)\", \"n"
        'ame": "ck_pdf_stage_document_mapping_profile_e3d5e39c85", "relatio'
        'n": "ops.pdf_stage_document"}, {"expression": "(product_id <> \'\''
        '\'\'::text)", "name": "ck_pdf_stage_document_physical_1246cec1c1",'
        ' "relation": "ops.pdf_stage_document"}, {"expression": "(source_di'
        "gest ~ ''^[0-9a-f]{64}$''::text)\", \"name\": \"ck_pdf_stage_docum"
        'ent_physical_1b32a362eb", "relation": "ops.pdf_stage_document"}, {'
        "\"expression\": \"(native_schema_digest ~ ''^[0-9a-f]{64}$''::tex"
        't)", "name": "ck_pdf_stage_document_physical_26e3a40d89", "relatio'
        'n": "ops.pdf_stage_document"}, {"expression": "(product_id = revis'
        'ion_id)", "name": "ck_pdf_stage_document_physical_a18559f6de", "re'
        'lation": "ops.pdf_stage_document"}, {"expression": "(revision_id <'
        "> ''''::text)\", \"name\": \"ck_pdf_stage_document_physical_b85b78"
        '7d88", "relation": "ops.pdf_stage_document"}, {"expression": "(pro'
        'duct_id = revision_id)", "name": "ck_pdf_stage_endpoint_physical_a'
        '18559f6de", "relation": "ops.pdf_stage_endpoint"}, {"expression": '
        '"(ordinal >= 0)", "name": "ck_pdf_stage_endpoint_physical_ee668cd4'
        'ef", "relation": "ops.pdf_stage_endpoint"}, {"expression": "(ordin'
        'al >= 0)", "name": "ck_pdf_stage_membership_ordinal_ee668cd4ef", "'
        'relation": "ops.pdf_stage_membership"}, {"expression": "((value_ki'
        "nd = ''scalar''::text) OR (scalar_json IS NULL))\", \"name\": \"ck"
        '_pdf_stage_membership_physical_341b42c0f9", "relation": "ops.pdf_s'
        "tage_membership\"}, {\"expression\": \"((value_kind = ''record''::"
        'text) = (record_id IS NOT NULL))", "name": "ck_pdf_stage_membershi'
        'p_physical_8028c34622", "relation": "ops.pdf_stage_membership"}, {'
        '"expression": "((member_key IS NULL) OR (member_key_stream_id IS N'
        'ULL))", "name": "ck_pdf_stage_membership_physical_8bf5b8b4d7", "re'
        'lation": "ops.pdf_stage_membership"}, {"expression": "(product_id '
        '= revision_id)", "name": "ck_pdf_stage_membership_physical_a18559f'
        '6de", "relation": "ops.pdf_stage_membership"}, {"expression": "(oc'
        "tet_length(convert_to((scalar_json)::text, ''UTF8''::name)) <= 655"
        '36)", "name": "ck_pdf_stage_membership_physical_b66e6eb309", "rela'
        'tion": "ops.pdf_stage_membership"}, {"expression": "((value_kind ='
        " ''parts''::text) = (stream_id IS NOT NULL))\", \"name\": \"ck_pdf"
        '_stage_membership_physical_df9d6518cd", "relation": "ops.pdf_stage'
        '_membership"}, {"expression": "(value_kind = ANY (ARRAY[\'\'parts'
        "''::text, ''record''::text, ''scalar''::text]))\", \"name\""
        ': "ck_pdf_stage_membership_value_kind_1ee79cbd9a", "relation": "op'
        's.pdf_stage_membership"}, {"expression": "(family = ANY (ARRAY[\''
        "'cell''::text, ''detail''::text, ''header''::text, ''node''::text,"
        " ''page''::text, ''provenance''::text, ''reference''::text, ''tabl"
        'e\'\'::text]))", "name": "ck_pdf_stage_native_family_896b469851", '
        '"relation": "ops.pdf_stage_native"}, {"expression": "(native_type '
        "<> ''''::text)\", \"name\": \"ck_pdf_stage_native_physical_1e27d9c"
        '8ce", "relation": "ops.pdf_stage_native"}, {"expression": "(jsonb_'
        "typeof(structure_json) = ''object''::text)\", \"name\": \"ck_pdf_s"
        'tage_native_physical_39016badae", "relation": "ops.pdf_stage_nativ'
        'e"}, {"expression": "((native_address IS NULL) <> (native_address_'
        'stream_id IS NULL))", "name": "ck_pdf_stage_native_physical_4c7b8c'
        '414a", "relation": "ops.pdf_stage_native"}, {"expression": "(produ'
        'ct_id = revision_id)", "name": "ck_pdf_stage_native_physical_a1855'
        '9f6de", "relation": "ops.pdf_stage_native"}, {"expression": "(json'
        "b_typeof(scalars_json) = ''object''::text)\", \"name\": \"ck_pdf_s"
        'tage_native_physical_af247a6f3c", "relation": "ops.pdf_stage_nativ'
        'e"}, {"expression": "(octet_length(convert_to((structure_json)::te'
        "xt, ''UTF8''::name)) <= 65536)\", \"name\": \"ck_pdf_stage_native_"
        'physical_c09752f060", "relation": "ops.pdf_stage_native"}, {"expre'
        "ssion\": \"(octet_length(convert_to((scalars_json)::text, ''UTF8'"
        '\'::name)) <= 65536)", "name": "ck_pdf_stage_native_physical_c4ce4'
        'd92f6", "relation": "ops.pdf_stage_native"}, {"expression": "(reco'
        "rd_id <> ''''::text)\", \"name\": \"ck_pdf_stage_native_physical_d"
        '10d461f9b", "relation": "ops.pdf_stage_native"}, {"expression": "('
        'row_count >= 0)", "name": "ck_pdf_stage_receipt_row_count_dd304210'
        '36", "relation": "ops.pdf_stage_receipt"}, {"expression": "((nativ'
        'e_pointer IS NULL) <> (native_pointer_stream_id IS NULL))", "name"'
        ': "ck_pdf_stage_reference_physical_15d32f6137", "relation": "ops.p'
        'df_stage_reference"}, {"expression": "(((field_name = ANY (ARRAY['
        "''source_cell_id''::text, ''target_cell_id''::text])) AND (native_"
        "pointer ~ ''^-?[0-9]+$''::text)) OR ((field_name <> ALL (ARRAY[''s"
        "ource_cell_id''::text, ''target_cell_id''::text])) AND (native_poi"
        "nter ~~ ''#%''::text)))\", \"name\": \"ck_pdf_stage_reference_phys"
        'ical_84ee799da6", "relation": "ops.pdf_stage_reference"}, {"expres'
        'sion": "(product_id = revision_id)", "name": "ck_pdf_stage_referen'
        'ce_physical_a18559f6de", "relation": "ops.pdf_stage_reference"}, {'
        '"expression": "(reference_id <> \'\'\'\'::text)", "name": "ck_pdf_'
        'stage_reference_physical_b4d49caa5d", "relation": "ops.pdf_stage_r'
        "eference\"}, {\"expression\": \"(status = ANY (ARRAY[''created''::"
        "text, ''running''::text, ''consolidating''::text, ''finished''::te"
        "xt, ''failed''::text, ''cancelled''::text]))\", \"name\": \"ck"
        '_run_physical_18b3405cc1", "relation": "ops.run"}, {"expression": '
        '"(input_revision >= 0)", "name": "ck_run_physical_cf2108479f", "re'
        'lation": "ops.run"}, {"expression": "(\\"position\\" >= 0)", "name'
        '": "ck_run_source_view_physical_9039b28f88", "relation": "ops.run_'
        'source_view"}, {"expression": "(attempt >= 0)", "name": "ck_task_p'
        'hysical_3f232544ec", "relation": "ops.task"}, {"expression": "(inv'
        "ocation_key <> ''''::text)\", \"name\": \"ck_task_physical_8afd8b3"
        '0fe", "relation": "ops.task"}, {"expression": "(status = ANY (ARRA'
        "Y[''pending''::text, ''running''::text, ''awaiting_agent''::text, "
        "''done''::text, ''empty''::text, ''failed''::text, ''reused''::tex"
        "t, ''skipped''::text, ''cancelled''::text]))\", \"name\": \"ck"
        '_task_physical_8cb2ac785d", "relation": "ops.task"}, {"expression"'
        ': "(task_id <> dependency_task_id)", "name": "ck_task_dependency_p'
        'hysical_64bb43e797", "relation": "ops.task_dependency"}, {"express'
        "ion\": \"(kind = ANY (ARRAY[''ancestor_source_view''::text, ''"
        'source_view_interpretation\'\'::text]))", "name": "ck_task_depende'
        'ncy_physical_6fe2d0b78b", "relation": "ops.task_dependency"}, {"ex'
        "pression\": \"(branch = ANY (ARRAY[''if''::text, ''then''::t"
        "ext, ''else''::text]))\", \"name\": \"ck_conditional_atom_physical"
        '_7349b348ce", "relation": "sem.conditional_atom"}, {"expression": '
        '"(\\"position\\" >= 0)", "name": "ck_conditional_atom_physical_80e'
        'ec7c0dc", "relation": "sem.conditional_atom"}, {"expression": "((c'
        "hoices IS NULL) OR (choices = ''null''::jsonb) OR (jsonb_typeof(ch"
        "oices) = ''array''::text))\", \"name\": \"ck_conditional_atom_phys"
        'ical_84f8e0b15f", "relation": "sem.conditional_atom"}, {"expressio'
        "n\": \"(presence = ANY (ARRAY[''present''::text, ''absent'':"
        ":text, ''optional''::text]))\", \"name\": \"ck_conditional_atom_ph"
        'ysical_9beafb7d1a", "relation": "sem.conditional_atom"}, {"express'
        "ion\": \"(scope = ANY (ARRAY[''shape''::text, ''accepted_value"
        '\'\'::text]))", "name": "ck_conditional_rule_physical_e64beec5ee",'
        ' "relation": "sem.conditional_rule"}, {"expression": "(\\"position'
        '\\" >= 0)", "name": "ck_identity_slot_physical_9039b28f88", "relat'
        'ion": "sem.identity_slot"}, {"expression": "((minimum_cardinality '
        "IS NULL) OR (maximum_cardinality IS NULL) OR (minimum_cardinality "
        '<= maximum_cardinality))", "name": "ck_property_applicability_phys'
        'ical_62e5012383", "relation": "sem.property_applicability"}, {"exp'
        'ression": "((maximum_cardinality IS NULL) OR (maximum_cardinality '
        '>= 0))", "name": "ck_property_applicability_physical_8e24e7a9f5", '
        '"relation": "sem.property_applicability"}, {"expression": "((minim'
        'um_cardinality IS NULL) OR (minimum_cardinality >= 0))", "name": "'
        'ck_property_applicability_physical_dd48c61c63", "relation": "sem.p'
        'roperty_applicability"}, {"expression": "(input_kind = \'\'depende'
        'ncy\'\'::text)", "name": "ck_sql_admission_physical_022451ced1", "'
        'relation": "sem.sql_admission"}]\'::jsonb,\'6b3270a8924991d79018db'
        "202bd24054a261e9277fff865fe8c00c3ef32bf686')"
    )
    op.execute(
        "GRANT SELECT ON data.source_record TO corpus_sem_writer,corpus_sem"
        "_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute("GRANT SELECT ON eval.reference_origin_group TO corpus_sem_evaluator")
    op.execute(
        "GRANT SELECT ON data.record_admission TO corpus_sem_writer,corpus_"
        "sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_anchor TO corpus_sem_writer,corpus_sem"
        "_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_dependency TO corpus_sem_writer,corpus"
        "_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_field TO corpus_sem_writer,corpus_sem_"
        "reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_private_assertion TO corpus_sem_writer"
        ",corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute("GRANT SELECT ON eval.reference_origin_source TO corpus_sem_evaluator")
    op.execute(
        "GRANT SELECT ON data.record_alternative TO corpus_sem_writer,corpu"
        "s_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_evidence_set TO corpus_sem_writer,corp"
        "us_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_field_piece TO corpus_sem_writer,corpu"
        "s_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_occurrence_anchor TO corpus_sem_writer"
        ",corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_premise TO corpus_sem_writer,corpus_se"
        "m_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_report TO corpus_sem_writer,corpus_sem"
        "_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_alternative_evidence TO corpus_sem_wri"
        "ter,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_alternative_piece TO corpus_sem_writer"
        ",corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_assertion TO corpus_sem_writer,corpus_"
        "sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_evidence_member TO corpus_sem_writer,c"
        "orpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_field_evidence TO corpus_sem_writer,co"
        "rpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute(
        "GRANT SELECT ON data.record_report_member TO corpus_sem_writer,cor"
        "pus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator"
    )
    op.execute("GRANT USAGE ON SCHEMA eval TO corpus_sem_fitter")
    op.execute("SET LOCAL ROLE " + op.get_bind().dialect.identifier_preparer.quote(_migration_role))
    for payload in state["operations"]:
        operations.invoke(NativeTransitionOp.from_payload(payload))
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade() -> None:
    raise RuntimeError("M1 record downgrade refused; rebuild owned realization")
