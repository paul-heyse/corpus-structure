"""Independent effective constraints, bounded selection and illustrative input behavior."""

from dataclasses import replace
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator

from corpus_structure.semantic.contract_inspection import inspect_contract
from corpus_structure.semantic.operation_reporting import report_schema
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.refusal_types import InvalidContinuation, SemanticRefusal
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
    assert value["report_version"] == 3
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


def test_missing_detail_is_corrupt_without_removing_effective_constraint():
    prepared = release()
    incomplete = replace(
        prepared,
        artifacts=tuple(
            a for a in prepared.artifacts if a.kind != "inspection/effective-model.json"
        ),
    )
    value = inspect_contract(
        incomplete, "property", "Base", property="value", view="detail"
    ).model_dump(mode="json")
    assert value["detail_status"] == "corrupt"
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

    from corpus_structure.intervene.semantic_server import build_retained_reader_server
    from corpus_structure.semantic import read_snapshot, releases, runtime

    prepared = release()
    purposes = []

    def engine(*args, **kwargs):
        purposes.append(kwargs["purpose"])
        return nullcontext(object())

    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(read_snapshot, "read_snapshot", lambda engine: nullcontext(object()))

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
        server = build_retained_reader_server(read_engine=cast(Any, object()))
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
            detailed = await client.call_tool(
                "inspect_contract",
                dict(
                    release=prepared.release_id,
                    subject_kind="class",
                    subject_id="Base",
                    input_json='{"value":"private-input"}',
                    validation_purpose="structural",
                    correction_detail=True,
                    max_errors=10,
                    max_depth=4,
                    max_bytes=16384,
                ),
            )
            assert not detailed.is_error
            structured = detailed.structured_content
            assert structured is not None
            assert structured["report_version"] == 3
            nested = structured["validation_report"]
            assert nested["report_version"] == 5
            assert nested["validation_outcome"] == "nonconformant"
            assert nested["presentation"]["max_errors"] == 10
            assert nested["presentation"]["max_depth"] == 4
            assert "private-input" not in str(structured)
            assert any(
                "Original-engine detail" in block.text
                for block in detailed.content
                if hasattr(block, "text")
            )

    anyio.run(journey)
    assert purposes == ["read"]


def test_current_native_correspondence_keeps_logical_result_and_physical_transport_distinct():
    import json
    from hashlib import sha256

    from corpus_structure.semantic.data_operation_artifacts import compile_data_operation_artifacts
    from corpus_structure.semantic.data_operation_storage import (
        data_operation_definition_projection,
    )
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.types import PreparedArtifact
    from semantic.test_data_operation_artifacts import inputs

    model, calls = inputs()
    base = release()
    manifest = {
        **json.loads(base.manifest),
        "data_operation_model": sha256(model.content).hexdigest(),
    }
    ports = compile_data_operation_artifacts(model, calls, native_source_digest="trusted-native")
    native = data_operation_definition_projection(base, model, native_digest="trusted-native")
    prepared = replace(
        base,
        manifest=canonical_bytes(manifest),
        artifacts=(
            *base.artifacts,
            PreparedArtifact("data_operations.json", model.content),
            PreparedArtifact("data_operation_ports.json", ports.manifest),
            PreparedArtifact("data_operation_native_definitions.json", native),
        ),
    )
    report = inspect_contract(
        prepared, "operation", "data.read_demand_result", view="detail"
    ).model_dump(mode="json")
    rows = [
        json.loads(row["metadata_json"])
        for row in report["entries"]
        if row["category"] == "physical_correspondence"
    ]
    assert rows
    assert all(row["result_class"] == "ReadDemandResult" for row in rows)
    assert all(
        row["physical_kind"] == "json_payload" and row["semantic_class"] is None for row in rows
    )
    assert all(row["source_reference"] == "native:data.read_demand_result.payload" for row in rows)
    assert all("remain distinct" in row["standing"] for row in rows)


def test_input_limit_counts_encoded_unicode_bytes():
    with pytest.raises(SemanticRefusal, match="bounded class input"):
        inspect_contract(
            release(), "class", "Base", input_json="λ" * 600_000, validation_purpose="structural"
        )


@pytest.mark.parametrize("refusal", ["selection", "render"])
def test_mcp_optional_presentation_failure_preserves_native_report(monkeypatch, refusal):
    from contextlib import nullcontext

    import anyio
    from fastmcp import Client

    from corpus_structure.intervene.semantic_server import build_retained_reader_server
    from corpus_structure.semantic import read_snapshot, releases, runtime

    prepared = release()
    monkeypatch.setattr(
        runtime, "open_runtime_engine", lambda *args, **kwargs: nullcontext(object())
    )
    monkeypatch.setattr(read_snapshot, "read_snapshot", lambda engine: nullcontext(object()))
    monkeypatch.setattr(releases, "open_release", lambda *args: prepared)
    expected = inspect_contract(
        prepared,
        "class",
        "Base",
        input_json='{"value":"bad"}',
        validation_purpose="structural",
        correction_detail=True,
    ).model_dump(mode="json")

    def fail(*args, **kwargs):
        raise ValueError("optional presentation could not fit")

    route = (
        "corpus_structure.semantic.diagnostic_selection.select_diagnostic"
        if refusal == "selection"
        else "corpus_structure.cli.correction_rendering.correction_text"
    )
    monkeypatch.setattr(route, fail)

    async def journey():
        async with Client(build_retained_reader_server(read_engine=cast(Any, object()))) as client:
            result = await client.call_tool(
                "inspect_contract",
                dict(
                    release=prepared.release_id,
                    subject_kind="class",
                    subject_id="Base",
                    input_json='{"value":"bad"}',
                    validation_purpose="structural",
                    correction_detail=True,
                ),
            )
            assert not result.is_error
            assert result.structured_content == expected
            assert any(
                "Correction presentation unavailable: ValueError" in block.text
                for block in result.content
                if hasattr(block, "text")
            )

    anyio.run(journey)
