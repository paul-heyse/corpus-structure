"""Actual PostgreSQL lowering against independent typed statement expectations."""

from decimal import Decimal
from typing import Any

from sqlalchemy import text

from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_admission_native import structural_admission_native_sql
from corpus_structure.semantic.structural_products import DIMENSIONS
from semantic.test_declared_structural_admission import comparison_report


def test_native_lowering_preserves_source_citations_and_numeric_kinds(commit_db_engine):
    report = comparison_report()
    left, right = (
        dict(
            source=source.model_dump(mode="python", exclude_none=True),
            start=0,
            end=9,
            text="Ada acts.",
            scope="selected",
        )
        for source in report.inputs.sources
    )
    dimensions: list[dict[str, Any]] = [
        dict(
            dimension=dimension,
            outcome="unknown",
            typed_outcome="unknown",
            assumptions=[],
            left_group=dict(state="absent", members=[], witnesses=[]),
            right_group=dict(state="absent", members=[], witnesses=[]),
        )
        for dimension in DIMENSIONS
    ]
    dimensions[0]["left_group"] = dict(
        state="present",
        grouping="singleton",
        witnesses=[],
        members=[
            dict(
                dimension=DIMENSIONS[0],
                lexical_value="Ada",
                evidence=[left],
                condition=dict(integer=1, floating=1.0, decimal=Decimal("1.00"), nullable=None),
            )
        ],
    )
    expected = dict(
        version="structural-public-statement-3",
        kind="qualified_comparison",
        scope="selected",
        inventory_id="actual",
        input_policy_id="policy",
        coverage_limits=[],
        exclusions=[],
        comparison=dict(
            left=left,
            right=right,
            dimensions=dimensions,
            equivalence="not_asserted",
            identity_standing="not_asserted",
            applicability="unestablished",
        ),
    )
    with commit_db_engine.connect() as connection, connection.begin():
        connection.exec_driver_sql(
            structural_admission_native_sql(), execution_options={"no_parameters": True}
        )
        actual = connection.scalar(
            text(
                "SELECT data.canonical_json(ops.ddo_structural_comparison_statement(CAST(:report AS jsonb)))"
            ),
            dict(report=json_bytes(semantic_value(report.model_dump(mode="python"))).decode()),
        )
        assert actual == canonical_bytes(semantic_value(expected)).decode()
