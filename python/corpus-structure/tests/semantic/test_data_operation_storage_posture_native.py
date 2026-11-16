"""Current immutable DDO products/episodes remain publisher-owned and RPC-scoped."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

# Independent actual storage expectations, rather than the removed record-stage tables.
RELATIONS = (
    ("kb.data_product", "id"),
    ("kb.data_product_member", "product_id"),
    ("ops.data_derivation", "id"),
)
PURPOSE_ROLES = (
    "corpus_sem_reader",
    "corpus_sem_writer",
    "corpus_sem_admitter",
    "corpus_sem_evaluator",
    "corpus_sem_fitter",
)


def test_current_product_and_episode_storage_has_exact_owner_acl_and_immutable_guards(
    commit_db_engine,
):
    with commit_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        for relation, key in RELATIONS:
            owner = conn.scalar(
                text(
                    "SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid=to_regclass(:relation)"
                ),
                {"relation": relation},
            )
            assert owner == "corpus_sem_publisher"
            triggers = conn.execute(
                text(
                    "SELECT t.tgname,t.tgtype,n.nspname||'.'||p.proname||'()' "
                    "FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid "
                    "JOIN pg_namespace n ON n.oid=p.pronamespace "
                    "WHERE t.tgrelid=to_regclass(:relation) AND NOT t.tgisinternal"
                ),
                {"relation": relation},
            ).all()
            assert ("semantic_immutable", 58, "sem.refuse_immutable_mutation()") in triggers
            # Ordinary/protected purposes read through their scoped native RPCs, not raw rows.
            for role in PURPOSE_ROLES:
                for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                    assert (
                        conn.scalar(
                            text("SELECT NOT has_table_privilege(:role,:relation,:privilege)"),
                            {"role": role, "relation": relation, "privilege": privilege},
                        )
                        is True
                    )
                for privilege in ("SELECT", "INSERT", "UPDATE"):
                    assert (
                        conn.scalar(
                            text("SELECT NOT has_any_column_privilege(:role,:relation,:privilege)"),
                            {"role": role, "relation": relation, "privilege": privilege},
                        )
                        is True
                    )
            # Owner DML must refuse even on empty tables: no manufactured body rows are needed.
            for mutation in (
                f"UPDATE {relation} SET {key}={key}",
                f"DELETE FROM {relation}",
                f"TRUNCATE {relation} CASCADE",
            ):
                with (
                    pytest.raises(DBAPIError, match="immutable semantic content"),
                    conn.begin_nested(),
                ):
                    conn.exec_driver_sql(mutation)
