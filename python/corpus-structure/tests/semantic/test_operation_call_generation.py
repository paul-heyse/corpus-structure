"""The same declared native correspondence drives static calls and actual materialization."""

import shutil
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.semantic import _operation_calls
from corpus_structure.semantic.contracts import (
    OperationFieldBinding,
    compile_execution_model,
    trusted_execution_inputs,
)
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.operation_call_generation import (
    generated_source,
    render_operation_calls,
    render_operation_identifiers,
    validate_call_bindings,
)
from corpus_structure.semantic.operation_value_types import NativeResultViolation
from corpus_structure.semantic.types import PreparationError, SourceArtifact

REPO = Path(__file__).resolve().parents[4]


@lru_cache(maxsize=1)
def current_model():
    return compile_execution_model(trusted_execution_inputs())


def native_row():
    return (
        7,
        3,
        "release:source",
        5,
        "document",
        11,
        "doc",
        "packet",
        2,
        "worker",
        datetime(2026, 11, 2, tzinfo=UTC),
        "invocation",
        None,
    )


def test_generated_call_and_result_are_current():
    assert Path(_operation_calls.__file__).read_text() == generated_source()
    from corpus_structure.schema.generate import _format
    from corpus_structure.semantic import _operation_ids

    assert Path(_operation_ids.__file__).read_text() == _format(
        "semantic/_operation_ids.py", render_operation_identifiers(current_model())
    )
    result = _operation_calls._claim_tasks_result(native_row())
    assert (result.task_id, result.run_id, result.method_config_id, result.attempt) == (7, 3, 5, 2)
    assert result.unit_type is TaskUnitType.DOCUMENT
    assert result.deadline == datetime(2026, 11, 2, tzinfo=UTC)
    assert result.held_progress is None


def test_semantic_identifiers_do_not_import_generated_calls_or_arrow():
    result = subprocess.run(
        [
            shutil.which("python") or "python",
            "-c",
            "from corpus_structure.semantic._operation_ids import TaskId; "
            "import sys; assert TaskId(7)==7; "
            "assert 'corpus_structure.semantic._operation_calls' not in sys.modules; "
            "assert not any(name.split('.')[0]=='pyarrow' "
            "for name in sys.modules)",
        ],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_prepared_stream_call_binds_and_validates_without_executing_or_collecting():
    from corpus_structure.semantic._operation_ids import ContentDigest, ProductKey, TaskId

    statement = _operation_calls.prepare_read_pdf_record_rows(
        task_id=TaskId(17),
        product_key=ProductKey("native"),
        content_digest=ContentDigest("a" * 64),
        family="native",
        filters={"record_id": "one"},
        after=None,
        limit=32,
    )
    assert statement.compile().params == {
        "task_id": 17,
        "product_key": "native",
        "content_digest": "a" * 64,
        "family": "native",
        "filters": {"record_id": "one"},
        "after": None,
        "limit": 32,
    }
    row = _operation_calls.materialize_read_pdf_record_rows(('{"_cursor":[],"x":null}',))
    assert row.body == '{"_cursor":[],"x":null}'
    assert row.decoded_json_fields(operation="read_native_source")["body"] == {
        "_cursor": [],
        "x": None,
    }
    materialize = vars(_operation_calls)["materialize_read_pdf_record_rows"]
    with pytest.raises(NativeResultViolation) as invalid:
        materialize((None,))
    assert invalid.value.locations == (("body",),)


def test_admission_purpose_is_finite_and_void_output_errors_are_native_results():
    _operation_calls.prepare_require_runtime_principal(purpose="read")
    prepare = vars(_operation_calls)["prepare_require_runtime_principal"]
    with pytest.raises(ValidationError):
        prepare(purpose="maintenance")
    code = render_operation_calls(current_model(), metadata)
    assert "with native_result_scope('admit', 'require_runtime_principal'):" in code


def test_named_held_transform_preserves_checked_submission():
    row: list[object] = list(native_row())
    row[-1] = {
        "semantic_proposal_first_result": {
            "attempt": 1,
            "holder": "previous",
            "packet_hash": "old-packet",
            "result": {"answer": "kept"},
        }
    }
    result = vars(_operation_calls)["_claim_tasks_result"](tuple(row))
    assert result.held_progress is not None
    assert result.held_progress.model_dump() == {
        "attempt": 1,
        "holder": "previous",
        "packet_hash": "old-packet",
        "result": {"answer": "kept"},
    }


@pytest.mark.parametrize(
    ("position", "value"),
    [
        (0, True),
        (4, "invalid-unit"),
        (9, None),
        (10, None),
        (12, {"semantic_proposal_first_result": {"attempt": 1}}),
    ],
)
def test_malformed_native_result_is_refused(position, value):
    row: list[object] = list(native_row())
    row[position] = value
    with pytest.raises((ValueError, ValidationError)):
        vars(_operation_calls)["_claim_tasks_result"](tuple(row))


def test_missing_required_native_field_retains_its_operation_and_model_path():
    row: list[object] = list(native_row())
    row[9] = None
    with pytest.raises(NativeResultViolation) as invalid:
        vars(_operation_calls)["_claim_tasks_result"](tuple(row))
    assert (invalid.value.operation, invalid.value.result_class, invalid.value.field) == (
        "claim",
        "ClaimedTask",
        "holder",
    )
    assert invalid.value.expected == "non-null" and invalid.value.actual is None


def test_one_declared_result_field_changes_columns_and_positional_materialization():
    model = current_model()
    operation = model.operation("claim")
    call = operation.call
    assert call is not None
    changed = replace(
        operation,
        calls=(
            replace(
                call,
                source_digest=None,
                result_fields=(
                    *call.result_fields,
                    OperationFieldBinding("native_status", "physical:ops.task.status", False),
                ),
            ),
        ),
    )
    model = replace(
        model, operations=tuple(changed if o.id == "claim" else o for o in model.operations)
    )
    model = validate_call_bindings(model, trusted_execution_inputs())
    code = render_operation_calls(model, metadata)
    assert "native_status: str" in code
    assert "_claim_tasks_columns.status," in code
    assert "native_status=row[13]" in code
    assert "from ._operation_ids import RunId as RunId" in code
    assert "RunId = NewType('RunId', int)" in render_operation_identifiers(model)


def test_bad_physical_correspondence_refuses_before_generation():
    inputs = trusted_execution_inputs()
    model = current_model()
    operation = model.operation("claim")
    call = operation.call
    assert call is not None
    changed = replace(
        operation,
        calls=(
            replace(
                call,
                result_fields=(
                    OperationFieldBinding("missing", "physical:ops.task.missing", False),
                ),
            ),
        ),
    )
    model = replace(
        model, operations=tuple(changed if o.id == "claim" else o for o in model.operations)
    )
    with pytest.raises(PreparationError, match="physical source field is unavailable"):
        validate_call_bindings(model, inputs)


def test_unchanged_source_name_cannot_hide_a_changed_field_representation():
    inputs = trusted_execution_inputs()
    physical = next(
        s.content for s in inputs.implementations if s.name == "pdf/record-physical.yaml"
    )
    changed = yaml.safe_load(physical)
    changed["classes"]["task"]["attributes"]["id"]["range"] = "string"
    changed_inputs = replace(
        inputs,
        implementations=tuple(
            SourceArtifact(item.name, yaml.safe_dump(changed, sort_keys=False).encode())
            if item.name == "pdf/record-physical.yaml"
            else item
            for item in inputs.implementations
        ),
    )
    with pytest.raises(PreparationError, match="resolved field representation differs"):
        validate_call_bindings(current_model(), changed_inputs)


@pytest.mark.skipif(shutil.which("pyrefly") is None, reason="blocked: pyrefly not on PATH")
def test_actual_typed_public_call_refuses_wrong_semantic_identifier_parameter_and_result(tmp_path):
    source = tmp_path / "consumer.py"
    source.write_text(
        "from sqlalchemy import Connection\n"
        "from corpus_structure.semantic.operations import claim_tasks, create_task, renew_claim\n"
        "from corpus_structure.semantic._operation_ids import "
        "RunId, MethodConfigId, TaskId, TaskAttempt, DocumentId, ReleaseId\n"
        "from corpus_structure.semantic._operation_calls import "
        "prepare_original_descriptor, materialize_document_registration, "
        "_document_registration_kb_document_columns, CompletionResult\n"
        "def receipt(result: CompletionResult) -> None:\n"
        "    task: TaskId = result.receipt.task_id\n"
        "    run: RunId = result.receipt.run_id\n"
        "    release: ReleaseId = result.receipt.release_id\n"
        "    attempt: TaskAttempt = result.receipt.attempt\n"
        "def good(conn: Connection) -> None:\n"
        "    descriptor = prepare_original_descriptor(id=DocumentId(1))\n"
        "    doc: DocumentId = descriptor.id\n"
        "    column = _document_registration_kb_document_columns.original_path\n"
        "    rows = claim_tasks(conn, run_id=RunId(1), config_id=MethodConfigId(2), holder='w')\n"
        "    if rows: print(rows[0].deadline.isoformat())\n"
        "    if rows:\n"
        "        attempt: TaskAttempt = rows[0].attempt\n"
        "        renew_claim(conn, task_id=rows[0].task_id, attempt=attempt, holder='w')\n"
        "    task: TaskId = create_task(conn, run_id=RunId(1), config_id=MethodConfigId(2), "
        "stage='ingest', unit_type='run', input_hash='fixture')\n"
    )
    executable = shutil.which("pyrefly")
    assert executable is not None
    command = [
        executable,
        "check",
        "--config",
        str(REPO / "pyproject.toml"),
        str(source),
    ]
    good = subprocess.run(command, capture_output=True, text=True, check=False)
    assert good.returncode == 0, good.stdout + good.stderr
    with source.open("a") as stream:
        stream.write(
            "def wrong_receipt(result: CompletionResult) -> None:\n"
            "    task: RunId = result.receipt.task_id\n"
            "    attempt: TaskId = result.receipt.attempt\n"
            "    release: RunId = result.receipt.release_id\n"
            "def bad(conn: Connection) -> None:\n"
            "    rows = claim_tasks(conn, run_id=MethodConfigId(1), "
            "config_id=RunId(2), holder='w')\n"
            "    claim_tasks(conn, run_id=RunId(1), config_id=MethodConfigId(2), "
            "holder='w', missing=True)\n"
            "    if rows: print(rows[0].unit_id + 1)\n"
            "    create_task(conn, run_id=MethodConfigId(1), config_id=RunId(2), "
            "stage='ingest', unit_type='run', input_hash='fixture')\n"
            "    renew_claim(conn, task_id=RunId(1), attempt=TaskId(2), holder='w')\n"
            "    prepare_original_descriptor(id=TaskId(1))\n"
            "    _document_registration_kb_document_columns.invented_column\n"
        )
    bad = subprocess.run(command, capture_output=True, text=True, check=False)
    assert bad.returncode != 0
    output = bad.stdout + bad.stderr
    assert "RunId" in output and "MethodConfigId" in output
    assert "TaskId" in output and "TaskAttempt" in output
    assert "missing" in output and "None" in output
    assert "DocumentId" in output and "invented_column" in output


def test_selected_projection_materializers_preserve_empty_ancestors_and_exact_decimals():
    from decimal import Decimal

    section = _operation_calls._read_published_sections_result(
        ("#/groups/1", None, 4, "section", "body", None, [], None, "")
    )
    assert section.model_dump(mode="python") == {
        "pointer": "#/groups/1",
        "parent_pointer": None,
        "ordinal": 4,
        "label": "section",
        "content_layer": "body",
        "name": None,
        "ancestors": (),
        "section_pointer": None,
        "text": "",
    }
    exact = Decimal("0.10000000000000000000000000001")
    region = _operation_calls._read_published_region_result(
        (
            "build",
            "revision",
            "#/texts/3",
            0,
            2,
            Decimal("600"),
            Decimal("800"),
            exact,
            Decimal("2"),
            Decimal("3"),
            Decimal("4"),
            "TOPLEFT",
        )
    )
    assert region.left is exact
    assert region.model_dump(mode="python")["left"] == exact
    with pytest.raises(NativeResultViolation) as invalid_role:
        _operation_calls._read_published_section_nodes_result(
            (
                "invented-role",
                "build",
                "revision",
                "#/texts/3",
                4,
                "text",
                None,
                None,
                "body",
                "hello",
                '{"self_ref":"#/texts/3"}',
            )
        )

    assert isinstance(invalid_role.value.original, ValidationError)
    assert invalid_role.value.locations == (("role",),)


def test_declared_json_text_result_preserves_sql_null_and_json_values():
    from corpus_structure.semantic.operation_value_types import SQL_NULL, decode_json_text

    assert decode_json_text(None) is SQL_NULL
    assert decode_json_text("null") is None
    assert decode_json_text("[]") == []
    assert decode_json_text("{}") == {}
    materialize = vars(_operation_calls)["_read_published_section_reports_result"]
    for encoded, expected in (("null", None), ("[]", []), ("{}", {})):
        row = materialize(("report", 3, encoded))
        assert row.body == encoded
        assert row.decoded_json_fields(operation="read_native_source")["body"] == expected
    with pytest.raises(NativeResultViolation) as absent:
        materialize(("report", 3, None))
    assert absent.value.field == "body"
    row = materialize(("report", 3, "malformed"))
    with pytest.raises(NativeResultViolation) as malformed:
        row.decoded_json_fields(operation="read_native_source")
    assert malformed.value.field == "body"


def test_json_text_result_uses_text_cast_without_changing_source_json_contract():
    from sqlalchemy.dialects import postgresql

    call = next(
        call
        for call in current_model().operation("read_native_source").calls
        if call.id == "read_published_section_reports"
    )
    assert call.json_read == "json-text-v1"
    body = next(field for field in call.result_fields if field.name == "body")
    assert body.resolved is not None and body.resolved.kind == "json_payload"
    statement = vars(_operation_calls)["_read_published_section_reports_statement"]
    assert "CAST(" in str(statement.compile(dialect=postgresql.dialect()))


def test_consumer_call_context_refuses_absent_or_changed_correspondence_before_execution():
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.operation_value_types import require_call_context
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.types import PreparedRelease, RegistryRow

    model = current_model()
    prepared = PreparedRelease(
        release_id="release:consumer",
        manifest=b"{}",
        definitions=(),
        vocabularies=(),
        queries=(),
        artifacts=(),
        required_capabilities=(),
        diagnostics=(),
        _adapters=(),
        execution_model_id=model.model_id,
        registry_rows=(RegistryRow("execution_model", model.model_id, model.content),),
    )
    require_call_context(
        prepared,
        "read_native_source",
        "read_published_regions",
        _operation_calls.READ_PUBLISHED_REGIONS_CONTRACT_DIGEST,
    )
    with pytest.raises(SemanticRefusal, match="incompatible consumer call"):
        require_call_context(prepared, "read_native_source", "absent", "0" * 64)
    with pytest.raises(SemanticRefusal, match="incompatible consumer call"):
        require_call_context(prepared, "read_native_source", "read_published_regions", "0" * 64)
    body = __import__("json").loads(model.content)
    next(o for o in body["operations"] if o["id"] == "read_native_source")["calls"] = []
    prepared = replace(
        prepared,
        registry_rows=(RegistryRow("execution_model", model.model_id, canonical_bytes(body)),),
    )
    with pytest.raises(SemanticRefusal, match="incompatible consumer call"):
        require_call_context(
            prepared,
            "read_native_source",
            "read_published_regions",
            _operation_calls.READ_PUBLISHED_REGIONS_CONTRACT_DIGEST,
        )


def test_native_completion_envelope_uses_derived_nested_fields_and_present_empty_collection():
    import json

    body = {
        "receipt": {
            "task_id": 7,
            "run_id": 3,
            "release_id": "release:source",
            "attempt": 2,
            "protocol": "empty",
            "observation_ids": [],
            "result_digest": "abc",
        },
        "transaction": "replay",
    }
    result = _operation_calls.CompletionResult.model_validate_json(json.dumps(body), strict=True)
    assert result.receipt.observation_ids == ()
    assert result.receipt.task_id == 7 and result.transaction == "replay"
    for field, bad in [("protocol", "unknown"), ("task_id", True), ("observation_ids", None)]:
        changed = {**body, "receipt": {**body["receipt"], field: bad}}
        with pytest.raises(ValidationError):
            _operation_calls.CompletionResult.model_validate_json(json.dumps(changed), strict=True)
    del body["receipt"]["observation_ids"]
    with pytest.raises(ValidationError):
        _operation_calls.CompletionResult.model_validate_json(json.dumps(body), strict=True)


def test_native_json_parameters_preserve_sql_null_vs_json_null():
    completion = {p.key: p.type for p in _operation_calls._complete_task_function.clauses}
    cancellation = {p.key: p.type for p in _operation_calls._end_source_run_function.clauses}
    from sqlalchemy.dialects.postgresql import JSONB

    error, envelope, failure = completion["error"], completion["envelope"], cancellation["failure"]
    assert isinstance(error, JSONB) and isinstance(envelope, JSONB) and isinstance(failure, JSONB)
    assert error.none_as_null is False
    assert envelope.none_as_null is True
    assert failure.none_as_null is True


def test_batch_mode_cannot_discard_a_native_result_contract():
    model = current_model()
    operation = model.operation("claim")
    assert operation.call is not None
    changed = replace(operation, calls=(replace(operation.call, batch=True),))
    model = replace(
        model, operations=tuple(changed if o.id == "claim" else o for o in model.operations)
    )
    with pytest.raises(PreparationError, match="batch calls require a void native effect"):
        validate_call_bindings(model, trusted_execution_inputs())


def test_source_resolution_cannot_fill_missing_acquired_types_from_installed_files():
    inputs = trusted_execution_inputs()
    inputs = replace(
        inputs,
        implementations=tuple(
            s for s in inputs.implementations if s.name != "unified/linkml-types.yaml"
        ),
    )
    with pytest.raises(PreparationError, match="required source module is unavailable"):
        validate_call_bindings(current_model(), inputs)


def test_explicit_native_integer_width_preserves_semantic_integer_and_other_bindings():
    from sqlalchemy import BigInteger, Integer

    private = {p.key: p.type for p in _operation_calls._read_pdf_frozen_rows_function.clauses}
    from sqlalchemy.sql.functions import FunctionElement

    function = _operation_calls._claim_tasks_function.element
    assert isinstance(function, FunctionElement)
    claim = {p.key: p.type for p in function.clauses}
    assert type(private["limit"]) is Integer
    assert type(claim["limit"]) is BigInteger
    model = current_model()
    operation = model.operation("claim")
    assert operation.call is not None
    parameters = tuple(
        replace(f, native_type="integer") if f.name == "holder" else f
        for f in operation.call.parameters
    )
    changed = replace(operation, calls=(replace(operation.call, parameters=parameters),))
    model = replace(
        model, operations=tuple(changed if o.id == "claim" else o for o in model.operations)
    )
    with pytest.raises(PreparationError, match="native integer width needs one integer parameter"):
        validate_call_bindings(model, trusted_execution_inputs())


def test_projected_requiredness_refines_nullable_source_without_losing_native_diagnostic(
    monkeypatch,
):
    import sys
    from types import ModuleType

    inputs = trusted_execution_inputs()
    artifact = next(
        s for s in inputs.implementations if s.name == "capture/companion-projection-model.yaml"
    )
    body = yaml.safe_load(artifact.content)
    body["classes"]["PublishedItemIndexRow"]["attributes"]["text"]["required"] = True
    inputs = replace(
        inputs,
        implementations=tuple(
            SourceArtifact(s.name, yaml.safe_dump(body, sort_keys=False).encode())
            if s.name == artifact.name
            else s
            for s in inputs.implementations
        ),
    )
    model = current_model()
    operation = model.operation("read_native_source")
    changed = replace(
        operation,
        calls=tuple(
            replace(c, result_fields=(), source_digest=None)
            if c.result_source == "model:PublishedItemIndexRow"
            else c
            for c in operation.calls
        ),
    )
    model = replace(
        model, operations=tuple(changed if o.id == operation.id else o for o in model.operations)
    )
    resolved = validate_call_bindings(model, inputs)
    call = next(
        c
        for c in resolved.operation("read_native_source").calls
        if c.id == "read_published_item_page"
    )
    field = next(f for f in call.result_fields if f.name == "text")
    assert not field.nullable and field.resolved is not None and field.resolved.nullable
    module = ModuleType("corpus_structure.semantic._projection_requiredness_control")
    module.__package__ = "corpus_structure.semantic"
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(
        compile(render_operation_calls(resolved), "<generated-call-control>", "exec"), vars(module)
    )
    materialize = vars(module)["_read_published_item_page_result"]
    with pytest.raises(NativeResultViolation) as invalid:
        materialize(("build", "revision", "#/texts/1", 0, "text", None, None, "body", None))
    assert invalid.value.field == "text"
    assert (
        materialize(("build", "revision", "#/texts/1", 0, "text", None, None, "body", "kept")).text
        == "kept"
    )


def test_output_failure_preserves_original_errors_and_transform_field_locations():
    row: list[object] = list(native_row())
    row[0] = True
    materialize = vars(_operation_calls)["_claim_tasks_result"]
    with pytest.raises(NativeResultViolation) as invalid:
        materialize(tuple(row))
    assert isinstance(invalid.value.original, ValidationError)
    assert invalid.value.original.errors()[0]["loc"] == ("task_id",)
    assert invalid.value.locations == (("task_id",),)
    row = list(native_row())
    row[4] = "unknown-unit"
    with pytest.raises(NativeResultViolation) as enum:
        materialize(tuple(row))
    assert isinstance(enum.value.original, ValueError)
    assert enum.value.locations == (("unit_type",),)
    assert enum.value.actual == "unknown-unit"
    row = list(native_row())
    row[-1] = {"semantic_proposal_first_result": {"attempt": 1}}
    with pytest.raises(NativeResultViolation) as nested:
        materialize(tuple(row))
    assert isinstance(nested.value.original, ValidationError)
    assert ("holder",) in [e["loc"] for e in nested.value.original.errors()]
    assert ("held_progress", "holder") in nested.value.locations


def test_native_width_refusals_remain_input_validation_and_accept_representable_edges():
    claim = {"run_id": 1, "config_id": 2, "holder": "worker"}
    for edge in (-(1 << 63), (1 << 63) - 1):
        assert (
            _operation_calls._claim_tasksRequest.model_validate({**claim, "run_id": edge}).run_id
            == edge
        )
    for outside in (-(1 << 63) - 1, 1 << 63):
        with pytest.raises(ValidationError) as invalid:
            _operation_calls._claim_tasksRequest.model_validate({**claim, "run_id": outside})
        assert not isinstance(invalid.value, NativeResultViolation)
        assert invalid.value.errors()[0]["loc"] == ("run_id",)
    frozen = {
        "build_id": "build",
        "task_id": 1,
        "attempt": 1,
        "holder": "worker",
        "frozen_digest": "digest",
        "family": "native",
        "after": None,
        "filters": {},
    }
    for edge in (-(1 << 31), (1 << 31) - 1):
        assert (
            _operation_calls._read_pdf_frozen_rowsRequest.model_validate(
                {**frozen, "limit": edge}
            ).limit
            == edge
        )
    for outside in (-(1 << 31) - 1, 1 << 31):
        with pytest.raises(ValidationError) as invalid:
            _operation_calls._read_pdf_frozen_rowsRequest.model_validate(
                {**frozen, "limit": outside}
            )
        assert not isinstance(invalid.value, NativeResultViolation)
        assert invalid.value.errors()[0]["loc"] == ("limit",)


def test_published_validation_reader_preserves_original_six_field_receipt():
    statement = _operation_calls.prepare_read_pdf_published_validation(
        task_id=_operation_calls.TaskId(10),
        product_key=_operation_calls.ProductKey("integrated"),
        content_digest=_operation_calls.ContentDigest("logical-book-digest"),
    )
    assert statement.compile().params == {
        "task_id": 10,
        "product_key": "integrated",
        "content_digest": "logical-book-digest",
    }
    contract = current_model().operation("read_pdf_product")
    call = next(c for c in contract.calls if c.id == "read_pdf_published_validation")
    assert [f.native_parameter for f in call.parameters] == ["p_task", "p_key", "p_digest"]
    assert call.cardinality == "optional" and not call.requires_context
    result = _operation_calls.materialize_read_pdf_published_validation(
        (
            "retained-build",
            "frozen-digest",
            "logical-book-digest",
            "projection-contract",
            True,
            "original-v4-native-contract",
        )
    )
    assert result.model_dump() == {
        "build_id": "retained-build",
        "frozen_digest": "frozen-digest",
        "logical_digest": "logical-book-digest",
        "contract_digest": "projection-contract",
        "native_callbacks": True,
        "native_contract_digest": "original-v4-native-contract",
    }
    materialize = vars(_operation_calls)["materialize_read_pdf_published_validation"]
    with pytest.raises(NativeResultViolation) as refused:
        materialize(("b", "f", "l", "contract", "true", "original-native"))
    assert refused.value.locations == (("native_callbacks",),)
