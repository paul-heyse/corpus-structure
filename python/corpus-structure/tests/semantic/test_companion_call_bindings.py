"""Current companion projections retain selected pins and exact Arrow field values."""

import pyarrow as pa
import pytest
from sqlalchemy.dialects import postgresql

from corpus_structure.semantic.companion_projection import projection
from corpus_structure.serve.companion_export import _admit_batch
from semantic.selected_source_contract_support import selection

PIN_REF, CUT, PUBLICATION = selection(
    release="release:selected", producer_release="release:producer", task=37, digest="a" * 64
)
PIN = PIN_REF.model_dump()


def provenance():
    return {
        **PIN,
        "selection_release_id": CUT["release_id"],
        "producer_release_id": PUBLICATION.release_id,
        "task_id": PUBLICATION.task_id,
        "product_key": PUBLICATION.product_key,
        "content_digest": PUBLICATION.logical_digest,
    }


def admit(family, values):
    spec = projection(family)
    batch = pa.RecordBatch.from_pylist([values], schema=spec.arrow_schema)
    _admit_batch(spec, batch, PIN_REF, PUBLICATION.release_id, cut=CUT, publication=PUBLICATION)
    return batch.to_pylist()[0]


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
    statement = projection(family).statement.params(**PIN)
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
    """Independent family values carried through the current Arrow consumer."""
    values = {
        **provenance(),
        "projection_id": projection("coverage").projection_id,
        "coverage_id": "coverage:one",
        "scope": "page",
        "coverage_family": "future-family",
        "discovery_policy": "declared-scope",
        "outcome": "partial",
        "detail": "remaining region unavailable",
        "supports_json": supports_json,
    }
    return values


@pytest.mark.parametrize("supports_json", [None, "null", '[{"pointer":"/x"}]'])
def test_companion_result_preserves_pins_open_family_and_json_null(supports_json):
    expected = coverage_row(supports_json)
    assert admit("coverage", expected) == expected


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
        **provenance(),
        "projection_id": projection(family).projection_id,
        **fields,
    }
    assert admit(family, values) == values
