"""Protected characterization inventory preserves bounded typed summary metadata."""

from pathlib import Path
from typing import Any, cast

from corpus_structure.semantic.characterization_store import (
    CharacterizationProductSummary,
    read_inventory,
)
from corpus_structure.semantic.product_reference import ProductReference


def test_native_inventory_adapter_validates_bounded_summary_without_reading_payload(monkeypatch):
    from corpus_structure.semantic import _operation_calls

    base = ProductReference(7, "integrated", "a" * 64)
    view = ProductReference(9, "view", "c" * 64)
    summary = CharacterizationProductSummary.model_validate(
        dict(
            base_document=base,
            profile="full_characterization",
            outcome=None,
            readiness="enriched",
            coverage=[dict(family="syntax", outcome="complete", availability="available")],
            coverage_omitted=0,
            layer_count=1,
            active_layer_count=1,
            providers=[],
            providers_omitted=0,
        )
    )
    observed = []
    value = dict(
        products=[
            dict(
                reference=view.values(),
                kind="view",
                producer_run_id=300,
                summary=summary.model_dump(mode="json"),
            )
        ],
        continuation=None,
    )
    monkeypatch.setattr(
        _operation_calls,
        "read_characterization_inventory",
        lambda *a, **kw: observed.append(kw) or value,
    )
    result = read_inventory(cast(Any, object()), 11, limit=8, max_bytes=262144)
    assert result["products"][0]["summary"]["readiness"] == "enriched"
    assert observed[0]["limit"] == 8 and observed[0]["max_bytes"] == 262144
    assert "annotations" not in result["products"][0]["summary"]


def test_protected_summary_function_and_inventory_query_have_valid_postgresql_grammar():
    from pglast import parse_sql

    path = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql/characterization.sql"
    source = path.read_text()
    start = source.index("CREATE OR REPLACE FUNCTION ops.read_characterization_inventory(")
    stop = source.index("\nEND $$;", start) + len("\nEND $$;")
    function = source[start:stop]
    assert len(parse_sql(function)) == 1
    # The standalone parser cannot resolve private ops.run composite types.
    # Native candidate qualification owns actual PLpgSQL, catalog and ACL checks.
    query_start = function.index(" SELECT coalesce(jsonb_agg(body")
    query_end = function.index(" ) bounded;", query_start) + len(" ) bounded;")
    assert len(parse_sql(function[query_start:query_end])) == 1
