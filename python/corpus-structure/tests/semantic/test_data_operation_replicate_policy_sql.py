"""Native replicate policy is closed and independently enforces fresh-sample custody."""

from typing import get_args

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


@pytest.mark.db
def test_native_policy_has_three_explicit_modes_and_refuses_unknown(semantic_bare_engine):
    from corpus_structure.semantic.data_operation_subjects import subject_scope_values
    from corpus_structure.semantic.demand_authority_native import demand_authority_sql
    from corpus_structure.semantic.metadata import metadata
    from semantic.native_program_support import temporary_routine

    helper = temporary_routine(
        demand_authority_sql(
            metadata, lowering_digest="checked", subject_scopes=subject_scope_values()
        ),
        "ops",
        "ddo_replicate_required",
    )
    with semantic_bare_engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql(helper)
            for policy, expected in (
                ("deterministic-single-result", False),
                ("retained-observation-single-result", False),
                ("explicit-replicates", True),
            ):
                required = connection.scalar(
                    text("SELECT pg_temp.ddo_replicate_required(:policy)"), {"policy": policy}
                )
                assert required is expected
            for policy in (None, "", "independent-fresh", "deterministic"):
                with connection.begin_nested() as savepoint:
                    with pytest.raises(DBAPIError, match="unknown operation replicate policy"):
                        connection.execute(
                            text("SELECT pg_temp.ddo_replicate_required(:policy)"),
                            {"policy": policy},
                        )
                    savepoint.rollback()
        finally:
            transaction.rollback()


def test_checked_python_policy_enum_matches_native_semantic_modes():
    from corpus_structure.semantic.data_operation_model import ReplicatePolicy

    assert set(get_args(ReplicatePolicy)) == {
        "deterministic-single-result",
        "retained-observation-single-result",
        "explicit-replicates",
    }
