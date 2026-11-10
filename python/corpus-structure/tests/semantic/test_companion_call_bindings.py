"""Protected companion calls keep exact pins and declared result distinctions."""

import pytest
from sqlalchemy.dialects import postgresql

from corpus_structure.semantic import _operation_calls
from corpus_structure.semantic._operation_ids import (
    ContentDigest,
    ProductKey,
    ProjectId,
    ReleaseId,
    RunId,
    TaskId,
)
from corpus_structure.semantic.operation_value_types import SQL_NULL, NativeResultViolation

PIN = {
    "project_id": ProjectId("project:fixture"),
    "run_id": RunId(23),
    "selection_release_id": ReleaseId("release:selected"),
    "task_id": TaskId(37),
    "product_key": ProductKey("integrated"),
    "content_digest": ContentDigest("a" * 64),
}


@pytest.mark.parametrize(
    ("family", "order"),
    [
        ("input", ("input_ordinal",)),
        ("relation", ("relation_id", "endpoint_ordinal")),
        ("coverage", ("coverage_id",)),
        ("mapping_report", ("report_ordinal",)),
    ],
)
def test_protected_companion_call_binds_complete_pin_without_execution(family, order):
    prepare = getattr(_operation_calls, f"prepare_read_published_{family}_batch")
    statement = prepare(**PIN)
    compiled = statement.compile(dialect=postgresql.dialect())
    assert compiled.params == PIN
    sql = str(compiled)
    assert f"ops.read_published_{family}_batch(" in sql
    ordering = sql.rsplit("ORDER BY ", 1)[1]
    positions = [ordering.index(name) for name in order]
    assert positions == sorted(positions)
    assert len(statement._order_by_clauses) == len(order)
    if family in {"relation", "coverage"}:
        assert 'COLLATE "C"' in sql


def coverage_row(supports_json):
    """An independent row fixture arranged in the selected SQL consumer's order."""
    values = {
        **PIN,
        "producer_release_id": "release:producer",
        "projection_id": "companion-projection:fixture",
        "coverage_id": "coverage:one",
        "scope": "page",
        "coverage_family": "future-family",
        "discovery_policy": "declared-scope",
        "outcome": "partial",
        "detail": "remaining region unavailable",
        "supports_json": supports_json,
    }
    statement = _operation_calls.prepare_read_published_coverage_batch(**PIN)
    return tuple(values[col.name] for col in statement.selected_columns), values


@pytest.mark.parametrize("supports_json", [None, "null", '[{"pointer":"/x"}]'])
def test_companion_result_preserves_pins_open_family_and_json_null(supports_json):
    raw, expected = coverage_row(supports_json)
    row = _operation_calls.materialize_read_published_coverage_batch(raw)
    assert row.model_dump(mode="python") == expected
    decoded = row.decoded_json_fields(operation="read_pdf_product")["supports_json"]
    if supports_json is None:
        assert decoded is SQL_NULL
    elif supports_json == "null":
        assert decoded is None
    else:
        assert decoded == [{"pointer": "/x"}]


def test_companion_result_refuses_undeclared_closed_outcome():
    raw, _ = coverage_row("null")
    names = list(
        _operation_calls.prepare_read_published_coverage_batch(**PIN).selected_columns.keys()
    )
    changed = list(raw)
    changed[names.index("outcome")] = "invented-outcome"
    with pytest.raises(NativeResultViolation) as invalid:
        _operation_calls.materialize_read_published_coverage_batch(tuple(changed))
    assert ("outcome",) in invalid.value.locations


@pytest.mark.parametrize(
    ("family", "fields"),
    [
        (
            "input",
            {
                "input_ordinal": 2,
                "input_role": "structural",
                "input_task_id": 17,
                "input_product_key": "native",
                "input_content_digest": "b" * 64,
            },
        ),
        (
            "relation",
            {
                "relation_id": "relation:one",
                "relation_kind": "correspondence",
                "relation_outcome": "matched",
                "comparison": "text",
                "policy": "original-policy",
                "evidence": "original-evidence",
                "endpoint_ordinal": 0,
                "endpoint_role": "input",
                "target_task_id": 17,
                "target_product_key": "native",
                "target_content_digest": "b" * 64,
                "target_occurrence_id": "occurrence:one",
            },
        ),
        *[
            (
                "mapping_report",
                {
                    "report_ordinal": 3,
                    "input_index": 0,
                    "input_task_id": 17,
                    "input_product_key": "native",
                    "input_content_digest": "b" * 64,
                    "occurrence_id": None,
                    "outcome": "unresolved",
                    "label": None,
                    "reason": "ambiguous original",
                    "raw_start": 0,
                    "coordinate_frame": None,
                    "coordinate_scale": None,
                    "normalization": normalization,
                },
            )
            for normalization in (None, "normalized")
        ],
    ],
)
def test_companion_result_preserves_other_families_and_nullable_literal(family, fields):
    values = {
        **PIN,
        "producer_release_id": "release:producer",
        "projection_id": "companion-projection:fixture",
        **fields,
    }
    statement = getattr(_operation_calls, f"prepare_read_published_{family}_batch")(**PIN)
    raw = tuple(values[col.name] for col in statement.selected_columns)
    materialize = getattr(_operation_calls, f"materialize_read_published_{family}_batch")
    assert materialize(raw).model_dump(mode="python") == values
    if family == "mapping_report":
        invalid = dict(values, normalization="invented-normalization")
        with pytest.raises(NativeResultViolation) as error:
            materialize(tuple(invalid[col.name] for col in statement.selected_columns))
        assert ("normalization",) in error.value.locations
