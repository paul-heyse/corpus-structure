"""The M1 deployment protects the actual new tables, ACLs and append-only guards."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._operation_calls import begin_stage, end_stage

# Independent migration expectation: eighteen public row families and two origin maps.
RELATIONS = (
    "data.source_record",
    "data.record_admission",
    "data.record_anchor",
    "data.record_dependency",
    "data.record_field",
    "data.record_private_assertion",
    "data.record_alternative",
    "data.record_evidence_set",
    "data.record_field_piece",
    "data.record_occurrence_anchor",
    "data.record_premise",
    "data.record_report",
    "data.record_alternative_evidence",
    "data.record_alternative_piece",
    "data.record_assertion",
    "data.record_evidence_member",
    "data.record_field_evidence",
    "data.record_report_member",
    "eval.reference_origin_group",
    "eval.reference_origin_source",
)


def test_record_migration_admits_table_posture_and_immutable_guards(
    commit_db_engine, commit_writer_engine
):
    with commit_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        descriptor = conn.exec_driver_sql(
            "SELECT data.execution_contract_descriptor()"
        ).scalar_one()
        assert (
            conn.exec_driver_sql(
                "SELECT NOT has_column_privilege('corpus_sem_publisher','ops.run','"
                "id','REFERENCES')"
            ).scalar_one()
            is True
        )
        guarded = {
            (item["relation"], item["name"], item["function"], item["type"])
            for item in descriptor["triggers"]
        }
        for relation in RELATIONS:
            assert (
                relation,
                "semantic_immutable",
                "sem.refuse_immutable_mutation()",
                58,
            ) in guarded
            assert (
                conn.scalar(
                    text(
                        "SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid=to_regcla"
                        "ss(:relation)"
                    ),
                    {"relation": relation},
                )
                == "corpus_sem_publisher"
            )
            assert (
                conn.scalar(
                    text(
                        "SELECT has_table_privilege('corpus_sem_reader',:relation,'SELECT')"
                        "=:public "
                        "AND has_table_privilege('corpus_sem_writer',:relation,'SELECT')=:public "
                        "AND has_table_privilege('corpus_sem_admitter',:relation,'SELECT')=:public "
                        "AND has_table_privilege('corpus_sem_evaluator',:relation,'SELECT') "
                        "AND NOT has_table_privilege('corpus_sem_writer',:relation,'INSERT') "
                        "AND NOT has_table_privilege('corpus_sem_fitter',:relation,'SELECT')"
                    ),
                    {"relation": relation, "public": relation.startswith("data.")},
                )
                is True
            )
            # Statement guards must fire even on empty storage, including owner DML.
            for mutation in (
                "UPDATE "
                + relation
                + " SET "
                + (
                    "project_id=project_id"
                    if relation.startswith("eval.")
                    else "release_id=release_id"
                ),
                "DELETE FROM " + relation,
                "TRUNCATE " + relation + " CASCADE",
            ):
                with (
                    pytest.raises(DBAPIError, match="immutable semantic content"),
                    conn.begin_nested(),
                ):
                    conn.exec_driver_sql(mutation)

    # Disposal must complete inside the transaction, before inference can open a
    # fresh stage. ON COMMIT DROP alone cannot establish this lifecycle contract.
    with (
        commit_writer_engine.connect().execution_options(isolation_level="SERIALIZABLE") as conn,
        conn.begin(),
    ):
        begin_stage(conn)
        for relation in RELATIONS:
            if relation.startswith("data."):
                target = "pg_temp.sp_" + relation.removeprefix("data.")
                assert conn.scalar(
                    text("SELECT to_regclass(:target) IS NOT NULL"), {"target": target}
                )
        end_stage(conn)
        for relation in RELATIONS:
            if relation.startswith("data."):
                target = "pg_temp.sp_" + relation.removeprefix("data.")
                assert conn.scalar(text("SELECT to_regclass(:target) IS NULL"), {"target": target})
        begin_stage(conn)
        end_stage(conn)
