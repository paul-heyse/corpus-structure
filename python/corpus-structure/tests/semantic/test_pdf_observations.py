"""Independent supplied recognition meaning; no provider/publication standing."""

import json
from copy import deepcopy

import pytest
from pglast import parse_plpgsql, parse_sql
from pydantic import ValidationError

from corpus_structure.semantic.pdf_integrated_native import observation_publication_sql
from corpus_structure.semantic.pdf_observations import (
    PdfObservationPublicationContext, observation_meaning, observation_meaning_digest,
)
from semantic.pdf_native_source_support import observation
from semantic.pdf_native_source_support import native_source as native_source


def test_observation_meaning_excludes_native_and_http_custody(native_source):
    supplied = observation(native_source)
    actual = observation_meaning(supplied)
    assert set(actual) == {
        "version", "source_digest", "recipe_digest", "observation", "occurrences",
        "coverage", "mapping_outcome", "source_fidelity",
    }
    assert actual["version"] == "pdf-observation-meaning-1"
    assert actual["source_digest"] == supplied["artifact_digest"]
    assert [row["text"] for row in actual["occurrences"]] == ["equal", "equal"]
    assert actual["coverage"] == [{
        "coverage_id": "page-1-table", "scope": "page:1", "family": "table",
        "discovery_policy": "fixture-full-page", "outcome": "partial",
    }]
    changed = deepcopy(supplied)
    changed["product_key"] = "a-different-physical-request-directory"
    changed["inputs"] = [{"task_id": 914, "product_key": "different", "content_digest": "f" * 64, "role": "structural"}]
    changed["observation"].update(usage_availability="available", usage_json='{"total_tokens":999}', diagnostic="physical retry metadata")
    decoding = json.loads(changed["observation"]["binding"]["decoding_json"])
    decoding.update(receipt_digests={"http": "f" * 64}, service_generation="another-service-process")
    changed["observation"]["binding"]["decoding_json"] = json.dumps(decoding)
    changed["health"]["validation_report"] = "a different publication attempt"
    changed["coverage"][0]["detail"] = "a different human diagnostic"
    assert observation_meaning_digest(changed) == observation_meaning_digest(supplied)
    assert "inputs" not in actual and "product_key" not in actual
    assert "usage_json" not in actual["observation"]


@pytest.mark.parametrize("change", ["raw", "model", "outcome", "precision", "source", "recipe", "order", "coverage"])
def test_observation_meaning_keeps_actual_reading_differences(native_source, change):
    supplied = observation(native_source)
    changed = deepcopy(supplied)
    if change == "raw":
        changed["observation"]["raw_response_digest"] = "e" * 64
    elif change == "model":
        changed["observation"]["binding"]["weights_digest"] = "e" * 64
    elif change == "outcome":
        changed["observation"]["outcome"] = "partial"
    elif change == "precision":
        changed["occurrences"][0]["precision"] = "unknown"
    elif change == "source":
        changed["artifact_digest"] = "e" * 64
    elif change == "recipe":
        changed["recipe_digest"] = "e" * 64
    elif change == "order":
        changed["occurrences"].reverse()
    else:
        changed["coverage"][0]["outcome"] = "unknown"
    assert observation_meaning_digest(changed) != observation_meaning_digest(supplied)


def test_observation_native_publication_context_has_no_invented_defaults():
    with pytest.raises(ValidationError):
        PdfObservationPublicationContext.model_validate({"version": "pdf-observation-publication-1"})


def test_observation_projection_sql_and_first_write_stamp_are_current_native_inputs():
    from pglast import ast
    from pglast.stream import RawStream

    source = observation_publication_sql()
    statements = parse_sql(source)
    declaration = next(
        row.stmt for row in statements if isinstance(row.stmt, ast.CreateFunctionStmt)
        and row.stmt.funcname[-1].sval == "pdf_observation_meaning"
    )
    assert parse_plpgsql(RawStream()(declaration))
    assert "publication_context" in source
    assert "'runtime_id',native_request.runtime_id" in source
    # Native stamping belongs to the first INSERT. Exact replay returns the old
    # immutable row before the INSERT; no UPDATE can relabel its first attempt.
    assert source.index("RETURN digest") < source.index("INSERT INTO ops.pdf_product(")
    assert "UPDATE ops.pdf_product" not in source
