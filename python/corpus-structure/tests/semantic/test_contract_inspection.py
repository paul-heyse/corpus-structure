"""Independent effective constraints, bounded selection and illustrative input behavior."""

from dataclasses import replace
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator

from corpus_structure.semantic.contract_inspection import inspect_contract
from corpus_structure.semantic.operation_reporting import report_schema
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.refusals import InvalidContinuation, SemanticRefusal
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


def release(bound=3):
    return prepare_release(
        SourceBundle(
            "m",
            (
                SourceArtifact(
                    "m",
                    f"""id: https://example.org/inspection
name: inspection
prefixes: {{ex: 'https://example.org/'}}
default_prefix: ex
default_range: string
types:
 string: {{base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}}
 integer: {{base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}}
classes:
 Base:
  attributes:
   value: {{range: integer, required: true, minimum_value: {bound}}}
 Derived:
  is_a: Base
  attributes:
   child: {{range: Derived, inlined: true, required: true}}
""".encode(),
                ),
            ),
        )
    )


def test_effective_inherited_constraints_and_finite_unresolved_skeleton():
    prepared = release()
    value = inspect_contract(prepared, "class", "Derived", view="detail").model_dump(mode="json")
    fields = {item["name"]: item for item in value["entries"] if item["category"] == "property"}
    assert fields["value"]["minimum"] == "3"
    assert fields["value"]["required"] is True
    assert value["skeleton_json"] == "{}"
    assert {p["path"] for p in value["placeholders"]} == {"/value", "/child"}
    assert value["report_version"] == 1
    assert value["release_id"] == prepared.release_id
    Draft202012Validator(report_schema("ContractInspection")).validate(value)


def test_cursor_cannot_cross_release_subject_view_or_limit():
    a, b = release(), release(7)
    page = inspect_contract(a, "class", "Derived", limit=1).model_dump(mode="json")
    assert not page["complete"]
    assert inspect_contract(a, "class", "Derived", limit=1, after=page["next_after"])
    for selected, subject, view, limit in [
        (b, "Derived", "summary", 1),
        (a, "Base", "summary", 1),
        (a, "Derived", "detail", 1),
        (a, "Derived", "summary", 2),
    ]:
        with pytest.raises(InvalidContinuation):
            inspect_contract(
                selected,
                "class",
                subject,
                view=cast(Any, view),
                limit=limit,
                after=page["next_after"],
            )


def test_structural_validation_uses_selected_release_and_keeps_input_location():
    prepared = release()
    value = inspect_contract(
        prepared,
        "property",
        "Base",
        property="value",
        input_json='{"value":2}',
        validation_purpose="structural",
    ).model_dump(mode="json")
    assert value["validation_report"]["observations"][0]["input_path"] == "/value"
    assert value["validation_report"]["release_id"] == prepared.release_id
    passed = inspect_contract(
        prepared, "class", "Base", input_json='{"value":3}', validation_purpose="accepted"
    ).model_dump(mode="json")
    assert passed["validation_report"]["observations"] == []
    assert passed["validation_report"]["complete"]


def test_missing_old_detail_never_means_missing_effective_constraint():
    prepared = release()
    old = replace(
        prepared,
        artifacts=tuple(
            a for a in prepared.artifacts if a.kind != "inspection/effective-model.json"
        ),
    )
    # An old producing compiler, not a compiler20 malformed product.
    import json

    manifest = json.loads(old.manifest)
    manifest["profile"]["compiler_version"] = "19"
    from corpus_structure.semantic.identity import canonical_bytes

    old = replace(old, manifest=canonical_bytes(manifest))
    value = inspect_contract(old, "property", "Base", property="value", view="detail").model_dump(
        mode="json"
    )
    assert value["detail_status"] == "unavailable"
    assert value["entries"][0]["minimum"] == "3"


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(subject_kind="property", subject_id="Base"),
        dict(subject_kind="class", subject_id="missing"),
        dict(subject_kind="class", subject_id="Base", view="other"),
        dict(subject_kind="class", subject_id="Base", input_json="null"),
    ],
)
def test_located_request_refusals(kwargs):
    with pytest.raises(SemanticRefusal, match="inspect_contract/"):
        inspect_contract(release(), **kwargs)


def test_cli_and_mcp_share_explicit_release_read_only_result(monkeypatch, cli):
    import json
    from contextlib import nullcontext

    import anyio
    from fastmcp import Client

    from corpus_structure.intervene.semantic_server import build_semantic_server
    from corpus_structure.semantic import query, releases, runtime

    prepared = release()
    purposes = []

    def engine(*args, **kwargs):
        purposes.append(kwargs["purpose"])
        return nullcontext(object())

    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(query, "read_snapshot", lambda engine: nullcontext(object()))

    def open_selected(conn, selected):
        assert selected == prepared.release_id
        return prepared

    monkeypatch.setattr(releases, "open_release", open_selected)
    result = cli(
        "schema",
        "inspect",
        "--release",
        prepared.release_id,
        "--subject-kind",
        "property",
        "--subject",
        "Base",
        "--property",
        "value",
        "--view",
        "detail",
        "--json",
    )
    assert result.exit_code == 0, result.output
    expected = json.loads(result.stdout)

    async def journey():
        server = build_semantic_server(read_engine=cast(Any, object()))
        async with Client(server) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            annotations = tools["inspect_contract"].annotations
            assert annotations is not None
            assert annotations.read_only_hint is True
            answer = await client.call_tool(
                "inspect_contract",
                dict(
                    release=prepared.release_id,
                    subject_kind="property",
                    subject_id="Base",
                    property="value",
                    view="detail",
                ),
            )
            assert not answer.is_error
            assert answer.structured_content == expected

    anyio.run(journey)
    assert purposes == ["read"]


def test_class_valued_result_keeps_physical_kind_distinct(monkeypatch):
    import json
    from types import SimpleNamespace

    from corpus_structure.semantic import contracts
    from corpus_structure.semantic.contracts import (
        OperationCallBinding,
        OperationFieldBinding,
        OperationFieldType,
        OperationRecordBinding,
    )

    prepared = replace(release(), execution_model_id="execution:test")
    field = OperationFieldBinding(
        "value",
        "physical:data.measurement.value",
        False,
        semantic_type="Base",
        resolved=OperationFieldType("integer", False, False, model_class="Base"),
    )
    call = OperationCallBinding(
        "read",
        "data.read",
        (),
        result_class="Base",
        result_fields=(field,),
        cardinality="one",
        ordered=False,
        records=(OperationRecordBinding("nested", (field,)),),
    )
    operation = SimpleNamespace(id="read_measurement", inputs=(), results=("Base",), calls=(call,))
    monkeypatch.setattr(
        contracts,
        "bound_execution_model",
        lambda selected: SimpleNamespace(operations=(operation,)),
    )
    value = inspect_contract(prepared, "class", "Base", view="detail").model_dump(mode="json")
    row = next(
        entry for entry in value["entries"] if entry["category"] == "physical_correspondence"
    )
    correspondence = json.loads(row["metadata_json"])
    assert correspondence["semantic_class"] == "Base"
    assert correspondence["physical_kind"] == "integer"
    assert correspondence["source_reference"] == "physical:data.measurement.value"
    assert "remain distinct" in correspondence["standing"]
    assert any(entry["name"] == "read_measurement/read/nested/value" for entry in value["entries"])


def test_input_limit_counts_encoded_unicode_bytes():
    with pytest.raises(SemanticRefusal, match="bounded class input"):
        inspect_contract(
            release(), "class", "Base", input_json="λ" * 600_000, validation_purpose="structural"
        )
