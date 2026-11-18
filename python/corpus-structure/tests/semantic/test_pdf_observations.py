"""Independent supplied recognition meaning; no provider/publication standing."""

import json
from copy import deepcopy

import pytest
from pglast import parse_plpgsql, parse_sql
from pydantic import ValidationError

from corpus_structure.semantic.pdf_integrated_native import observation_publication_sql
from corpus_structure.semantic.pdf_observations import (
    MEANING_SPEC,
    PdfObservationPublicationContext,
    observation_meaning,
    observation_meaning_digest,
    observation_meaning_spec,
)
from semantic.pdf_native_source_support import native_source as native_source
from semantic.pdf_native_source_support import observation


@pytest.fixture
def meaning_spec():
    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context

    return next(
        source.content
        for source in trusted_pdf_context().domain.sources
        if source.name == MEANING_SPEC
    )


def test_observation_meaning_excludes_native_and_http_custody(native_source, meaning_spec):
    supplied = observation(native_source)
    actual = observation_meaning(supplied, specification=meaning_spec)
    assert set(actual) == {
        "version",
        "source_digest",
        "recipe_digest",
        "observation",
        "occurrences",
        "coverage",
        "mapping_outcome",
        "source_fidelity",
    }
    assert actual["version"] == "pdf-observation-meaning-1"
    assert actual["source_digest"] == supplied["artifact_digest"]
    assert [row["text"] for row in actual["occurrences"]] == ["equal", "equal"]
    assert actual["coverage"] == [
        {
            "coverage_id": "page-1-table",
            "scope": "page:1",
            "family": "table",
            "discovery_policy": "fixture-full-page",
            "outcome": "partial",
        }
    ]
    changed = deepcopy(supplied)
    changed["product_key"] = "a-different-physical-request-directory"
    changed["inputs"] = [
        {
            "task_id": 914,
            "product_key": "different",
            "content_digest": "f" * 64,
            "role": "structural",
        }
    ]
    changed["observation"].update(
        usage_availability="available",
        usage_json='{"total_tokens":999}',
        diagnostic="physical retry metadata",
    )
    decoding = json.loads(changed["observation"]["binding"]["decoding_json"])
    decoding.update(
        receipt_digests={"http": "f" * 64}, service_generation="another-service-process"
    )
    changed["observation"]["binding"]["decoding_json"] = json.dumps(decoding)
    changed["health"]["validation_report"] = "a different publication attempt"
    changed["coverage"][0]["detail"] = "a different human diagnostic"
    assert observation_meaning_digest(
        changed, specification=meaning_spec
    ) == observation_meaning_digest(supplied, specification=meaning_spec)
    assert "inputs" not in actual and "product_key" not in actual
    assert "usage_json" not in actual["observation"]
    assert actual["observation"]["binding"]["decoding_json"] == json.loads(
        supplied["observation"]["binding"]["decoding_json"]
    )


def test_native_observation_meaning_keeps_numeric_settings_and_separates_custody(
    native_rollback,
    native_source,
    meaning_spec,
):
    """Actual installed projection; native retention/ordinary read use other controls."""
    from pglast.stream import RawStream
    from sqlalchemy import text

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.native_objects import execute_native_sql, native_owner
    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
    from corpus_structure.semantic.pdf_integrated_native import observation_value_declarations

    declaration = observation_value_declarations(trusted_pdf_context())["ops", "pdf_observation_meaning"]
    with native_owner(native_rollback.connection, "corpus_sem_publisher"):
        execute_native_sql(native_rollback.connection, RawStream()(declaration))

    supplied = observation(native_source)
    supplied["observation"]["binding"]["decoding_json"] = (
        '{"temperature":1e-8,"nested":{"limit":2.0}}'
    )
    # Literal typed physical references test value projection only. They assert
    # no producer, publication, admission or native lineage standing.
    supplied["inputs"] = [
        {
            "task_id": 1001,
            "product_key": "value-only-input",
            "content_digest": "a" * 64,
            "role": "structural",
        }
    ]
    changed = deepcopy(supplied)
    changed["product_key"] = "another-native-episode"
    changed["inputs"][0]["task_id"] += 17
    changed["observation"]["binding"]["decoding_json"] = (
        '{"nested":{"limit":2},"temperature":0.000000010,"service_generation":"other","receipt_digests":{"http":"another"}}'
    )
    expected = observation_meaning_digest(supplied, specification=meaning_spec)
    assert observation_meaning_digest(changed, specification=meaning_spec) == expected

    def native(value):
        return native_rollback.connection.scalar(
            text(
                "SELECT ops.ddo_digest(data.ddo_json_meaning(ops.pdf_observation_meaning(:payload)))"
            ),
            {"payload": canonical_bytes(value)},
        )

    assert native(supplied) == native(changed) == expected
    changed["observation"]["binding"]["prompt_digest"] = "e" * 64
    assert native(changed) != expected


@pytest.mark.parametrize(
    "change",
    [
        "raw",
        "model",
        "prompt",
        "geometry",
        "outcome",
        "precision",
        "source",
        "recipe",
        "order",
        "coverage",
    ],
)
def test_observation_meaning_keeps_actual_reading_differences(native_source, change, meaning_spec):
    supplied = observation(native_source)
    changed = deepcopy(supplied)
    if change == "raw":
        changed["observation"]["raw_response_digest"] = "e" * 64
    elif change == "model":
        changed["observation"]["binding"]["weights_digest"] = "e" * 64
    elif change == "prompt":
        changed["observation"]["binding"]["prompt_digest"] = "e" * 64
    elif change == "geometry":
        changed["observation"]["image"]["transform"] = {
            "status": "coarse",
            "normalization": "none",
            "source_space": "pdf_points",
            "target_space": "submitted_pixels",
            "page_width": 200,
            "page_height": 300,
            "page_rotation": 0,
            "crop_left": 0,
            "crop_top": 0,
            "crop_right": 200,
            "crop_bottom": 300,
            "affine": [0.02, 0, 0, 0.02, 0, 0],
        }
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
    assert observation_meaning_digest(
        changed, specification=meaning_spec
    ) != observation_meaning_digest(supplied, specification=meaning_spec)


def test_observation_native_publication_context_has_no_invented_defaults():
    with pytest.raises(ValidationError):
        PdfObservationPublicationContext.model_validate(
            {"version": "pdf-observation-publication-1"}
        )


def test_python_and_native_projection_consume_one_captured_selection(native_source):
    from dataclasses import replace

    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
    from semantic.pdf_domain_support import altered_domain

    context = trusted_pdf_context()
    selected = next(source for source in context.domain.sources if source.name == MEANING_SPEC)
    assert json.loads(selected.content) == observation_meaning_spec(selected.content)
    changed = json.loads(selected.content)
    changed["binding_fields"].remove("seed")
    content = json.dumps(changed).encode()
    supplied = observation(native_source)
    assert (
        "seed"
        in observation_meaning(supplied, specification=selected.content)["observation"]["binding"]
    )
    assert (
        "seed" not in observation_meaning(supplied, specification=content)["observation"]["binding"]
    )
    domain = altered_domain(
        context.domain,
        sources=tuple(
            replace(source, content=content) if source.name == MEANING_SPEC else source
            for source in context.domain.sources
        ),
    )
    original, altered = (
        observation_publication_sql(context),
        observation_publication_sql(replace(context, domain=domain)),
    )
    assert "'seed', observed['binding']['seed']" in original
    assert "'seed', observed['binding']['seed']" not in altered


def test_observation_projection_sql_and_first_write_stamp_are_current_native_inputs():
    from pglast import ast
    from pglast.stream import RawStream

    source = observation_publication_sql()
    statements = parse_sql(source)
    declaration = next(
        row.stmt
        for row in statements
        if isinstance(row.stmt, ast.CreateFunctionStmt)
        and row.stmt.funcname
        and row.stmt.funcname[-1].sval == "pdf_observation_meaning"
    )
    assert parse_plpgsql(RawStream()(declaration))
    assert "publication_context" in source
    assert "'runtime_id',p_runtime" in source
    # Native stamping belongs to the first INSERT. Exact replay returns the old
    # immutable row before the INSERT; no UPDATE can relabel its first attempt.
    assert source.index("RETURN digest") < source.index("INSERT INTO ops.pdf_product(")
    assert "UPDATE ops.pdf_product" not in source
