"""Captured DDO explanations have no legacy catalog or live authorization claim."""

import json
from dataclasses import replace
from functools import cache
from typing import Any, cast

import pytest

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_storage import data_operation_definition_projection
from corpus_structure.semantic.demand_queries import DemandQueryRequest
from corpus_structure.semantic.operation_reporting import explain_operation, report_schema
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.refusal_types import SemanticRefusal
from corpus_structure.semantic.types import (
    PreparedArtifact,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)
from semantic.data_operation_declaration_support import contract, declarations


@cache
def current_release():
    bundle = SourceBundle(
        "m",
        (
            SourceArtifact(
                "m",
                b"""id: https://example.org/current-inspection
name: current_inspection
prefixes: {ex: 'https://example.org/current-inspection/'}
default_prefix: ex
default_range: string
types:
 string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
 integer: {base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}
classes:
 Base:
  attributes:
   value: {range: integer}
""",
            ),
        ),
    )
    prepared = prepare_release(
        bundle,
        data_operation_dependencies(
            ResolvedDependencies(),
            declarations(
                contract(
                    id="inspect.current",
                    precision_description="descriptive precision",
                    coverage_description="explicit inspected population",
                ),
            ),
        ),
    )
    model = bound_data_operation_model(prepared)
    projection = data_operation_definition_projection(
        prepared, model, native_digest="controlled-native-projection"
    )
    return replace(
        prepared,
        artifacts=(
            *prepared.artifacts,
            PreparedArtifact("data_operation_native_definitions.json", projection),
        ),
    )


def test_explanation_retains_checked_definition_binding_and_documentation_without_effect_authority():
    prepared = current_release()
    result = explain_operation(prepared, "inspect.current").model_dump(mode="json")
    assert result["report_version"] == 3
    assert result["recipe"].startswith("recipe:")
    assert result["definition"].startswith("definition:")
    assert result["eligibility"].startswith("eligibility:")
    assert result["precision_description"] == "descriptive precision"
    assert result["coverage_description"] == "explicit inspected population"
    assert json.loads(result["declaration_json"])["subject"] == result["subject_definition"]
    assert json.loads(result["binding_json"])
    assert result["observation_status"] == "not_requested"
    assert result["authority"] == "declaration_and_observation_only"
    assert "observation_json" not in result
    properties = report_schema("OperationExplanation")["properties"]
    assert isinstance(properties, dict) and "task_id" not in properties
    with pytest.raises(SemanticRefusal, match="not declared"):
        explain_operation(prepared, "unknown")


def test_explanation_preserves_actual_native_binding_reasons_and_cut(monkeypatch):
    import corpus_structure.semantic.demand_queries as queries

    prepared = current_release()
    observed = dict(
        cut=dict(
            demand_id="demand:actual",
            project_id="project:actual",
            release_id=prepared.release_id,
            runtime_id="runtime:actual",
            read_id="read:actual",
        ),
        cut_id="cut:actual",
        page_complete=False,
        items=[
            {
                "obligation": {"obligation_id": "obligation:actual"},
                "uses": [
                    dict(
                        use_id="use:actual",
                        obligation_id="obligation:actual",
                        fate="awaiting-inputs",
                        historical_fate="awaiting-inputs",
                        request_id=None,
                        generation=None,
                        derivation_id=None,
                        selection={
                            "reasons": [
                                {
                                    "code": "cardinality",
                                    "location": "input:x",
                                    "detail": "required scalar unavailable",
                                },
                            ]
                        },
                    )
                ],
            }
        ],
        continuation="actual-native-continuation",
    )
    monkeypatch.setattr(queries, "serve_demand_query", lambda connection, request: observed)
    request = DemandQueryRequest(
        demand_id="demand:actual",
        project_id="project:actual",
        view="operations",
        operation_id="inspect.current",
    )
    connection = cast(Any, object())
    report = explain_operation(
        prepared, "inspect.current", connection=connection, observation=request
    ).model_dump(mode="json")
    assert json.loads(report["observation_json"]) == observed
    assert report["observation_status"] == "observed" and not report["complete"]
    native = report["native_observation"]
    assert {key: native[key] for key in observed["cut"]} == observed["cut"]
    assert native["uses"][0]["use_id"] == "use:actual"
    assert native["uses"][0]["historical_fate"] == "awaiting-inputs"
    assert not native["complete"]
    with pytest.raises(ValueError, match="exact selected"):
        explain_operation(
            prepared,
            "inspect.current",
            connection=connection,
            observation=request.model_copy(update={"operation_id": "other"}),
        )
    observed["cut"]["release_id"] = "release:other"
    with pytest.raises(ValueError, match="another release"):
        explain_operation(prepared, "inspect.current", connection=connection, observation=request)
