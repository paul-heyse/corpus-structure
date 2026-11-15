"""Independent static shapes, exact ingress and captured-schema propagation controls."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
import yaml

from corpus_structure.schema.generate import _format
from corpus_structure.semantic import _data_operation_wire
from corpus_structure.semantic._data_operation_wire import WireClaimDataRequestRequest
from corpus_structure.semantic.data_operation_artifacts import compile_data_operation_artifacts
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_json import json_bytes, wire_json_loads
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    _rename_native_entrypoints,
    native_operation_calls,
    native_operation_declarations,
    native_protocol_sources,
    native_source_digest,
)
from corpus_structure.semantic.data_operation_wire import generated_wire_source, render_wire_types
from corpus_structure.semantic.native_sql_body import body_source
from corpus_structure.semantic.prepared_sql import prepare_sql

REPO = Path(__file__).resolve().parents[4]


def test_checkout_wire_facade_is_generated_from_current_protocol_and_correspondence():
    assert Path(_data_operation_wire.__file__).read_text() == _format(
        "semantic/_data_operation_wire.py", generated_wire_source()
    )
    assert not hasattr(DataOperationStorage, "invoke")


def test_fixed_call_preserves_omission_and_rejects_wrong_union_result():
    class Connection:
        result = '{"payload":{"state":"no-work"}}'

        def __init__(self):
            self.calls = []

        def scalar(self, statement, parameters):
            self.calls.append((statement, parameters))
            return self.result

    connection = Connection()
    storage = DataOperationStorage(cast(Any, connection))
    original = {"request_id": "request:x", "holder": "worker", "lease_seconds": 3}
    assert storage.claim_data_request(cast(WireClaimDataRequestRequest, original)) == {
        "state": "no-work"
    }
    assert wire_json_loads(connection.calls[0][1]["payload"]) == original
    assert "external_packet_id" not in original
    connection.result = '{"payload":{"state":"claimed"}}'
    with pytest.raises(ValueError, match="schema"):
        storage.claim_data_request(cast(WireClaimDataRequestRequest, original))
    before = len(connection.calls)
    with pytest.raises(ValueError, match="schema"):
        storage.claim_data_request(
            cast(WireClaimDataRequestRequest, {**original, "lease_seconds": "3"})
        )
    assert len(connection.calls) == before


def test_captured_structural_calls_keep_decimal_and_changed_protocol_fields(monkeypatch):
    sources = native_protocol_sources()
    protocol = next(item for item in sources if item.name == "native/data-operation-protocol.yaml")
    document = yaml.safe_load(protocol.content)
    request = document["definitions"]["expand_data_obligation_request"]
    request["properties"]["source_revision"] = {"type": "string", "enum": ["reviewed"]}
    request["required"].append("source_revision")
    output = document["definitions"]["expand_data_obligation_result"]
    output["properties"]["analyzed_scope"] = {"$ref": "#/definitions/json_value"}
    output["required"].append("analyzed_scope")
    sources = tuple(
        replace(item, content=yaml.safe_dump(document).encode())
        if item.name in {protocol.name, "native/projection-physical/data-operation-native.yaml"}
        else item
        for item in sources
    )
    model = compile_data_operations(declarations=(native_operation_declarations(sources),), captured_contracts=sources)
    calls = tuple(
        item
        for item in native_operation_calls(model, sources=sources)
        if item[0] == "data.expand_data_obligation"
    )
    artifact = compile_data_operation_artifacts(
        model, calls, native_source_digest=native_source_digest(sources)
    )
    assert b"source_revision: Required[Literal['reviewed']]" in artifact.calls
    assert b"class WireExpandDataObligationRequest(TypedDict)" in artifact.calls
    module = ModuleType("corpus_structure.semantic._wire_generation_control")
    module.__package__ = "corpus_structure.semantic"
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(artifact.calls, "captured-wire-control.py", "exec"), module.__dict__)
    context_checks = []
    module.__dict__["require_call_context"] = lambda *args: context_checks.append(args)
    payload = {
        "demand_id": "demand:x",
        "operation_id": "operation:x",
        "subject": "subject:x",
        "original_source": "source:x",
        "analyzed_scope": {"coordinate": Decimal("0.12345678901234567890123456789")},
        "parameters": {},
        "source_revision": "reviewed",
    }
    prepare = module.__dict__["prepare_expand_data_obligation"]
    with pytest.raises(TypeError):
        prepare(payload=payload)
    statement = prepare(payload=payload, projection_context=object())
    encoded = statement.compile().params["payload"]
    assert (
        wire_json_loads(encoded)["analyzed_scope"]["coordinate"]
        == payload["analyzed_scope"]["coordinate"]
    )
    assert context_checks[0][1] == "data.expand_data_obligation"
    with pytest.raises(ValueError, match="source_revision"):
        prepare(
            payload={key: value for key, value in payload.items() if key != "source_revision"},
            projection_context=object(),
        )

    # Exercise the emitted result function itself, including its exact decoder.
    class Connection:
        def scalar(self, statement):
            return json_bytes(
                {
                    "payload": {
                        "obligation_id": "obligation:x",
                        "analyzed_scope": payload["analyzed_scope"],
                    }
                }
            ).decode()

    result = module.__dict__["expand_data_obligation"](
        Connection(), payload=payload, projection_context=object()
    )
    assert result["payload"]["analyzed_scope"] == payload["analyzed_scope"]
    assert isinstance(result["payload"]["analyzed_scope"]["coordinate"], Decimal)
    # Embedded captured schema is not affected by ambient checkout protocol edits.
    assert (
        json.loads(json.loads(artifact.manifest)["calls"][0][1]["parameters"][0]["wire_schema"])[
            "definitions"
        ]["expand_data_obligation_request"]["required"][-1]
        == "source_revision"
    )


def test_structural_generation_refuses_unsupported_construct_at_its_source():
    with pytest.raises(ValueError, match="#/definitions/new_shape"):
        render_wire_types({"new_shape": {"allOf": [{"type": "string"}]}})


@pytest.mark.skipif(shutil.which("pyrefly") is None, reason="blocked: pyrefly unavailable")
def test_fixed_native_caller_preserves_nominal_ids_unions_and_required_keys(tmp_path):
    source = tmp_path / "consumer.py"
    source.write_text(
        "from corpus_structure.semantic._data_operation_wire import WireDemandId, WireRequestId, WireClaimDataRequestResult\n"
        "from corpus_structure.semantic.identifiers import TaskId, ReleaseId, RuntimeId\n"
        "from corpus_structure.semantic._data_operation_wire import WireInspectDataExecutionRequest, WireOperationId\n"
        "from corpus_structure.semantic.data_operation_storage import DataOperationStorage\n"
        "def good(storage: DataOperationStorage) -> None:\n"
        "    result = storage.claim_data_request({'request_id': WireRequestId('r'), 'holder': 'worker', 'lease_seconds': 3})\n"
        "    if result['state'] == 'claimed':\n"
        "        task: TaskId = result['task_id']\n"
        "    pin: WireInspectDataExecutionRequest = {'operation_id': WireOperationId('o'), 'release_id': ReleaseId('r'), 'runtime_id': RuntimeId('x')}\n"
    )
    executable = shutil.which("pyrefly")
    assert executable is not None
    command = [executable, "check", "--config", str(REPO / "pyproject.toml"), str(source)]
    passed = subprocess.run(command, capture_output=True, text=True, check=False)
    assert passed.returncode == 0, passed.stdout + passed.stderr
    with source.open("a") as stream:
        stream.write(
            "def bad(storage: DataOperationStorage, result: WireClaimDataRequestResult) -> None:\n"
            "    storage.claim_data_request({'request_id': WireDemandId('d'), 'holder': 'w', 'lease_seconds': 3})\n"
            "    storage.claim_data_request({'request_id': WireRequestId('r')})\n"
            "    task: TaskId = result['task_id']\n"
            "    wrong_pin: WireInspectDataExecutionRequest = {'operation_id': WireOperationId('o'), 'release_id': ReleaseId('r'), 'runtime_id': ReleaseId('x')}\n"
        )
    failed = subprocess.run(command, capture_output=True, text=True, check=False)
    assert failed.returncode != 0
    diagnostics = failed.stdout + failed.stderr
    assert (
        "WireDemandId" in diagnostics
        and "lease_seconds" in diagnostics
        and "task_id" in diagnostics
        and "RuntimeId" in diagnostics
    )


def test_native_header_rename_changes_only_selected_declaration_and_preserves_body():
    sql = """-- misleading CREATE OR REPLACE FUNCTION ops.claim_data_request(
SELECT 'CREATE OR REPLACE FUNCTION ops.claim_data_request(';  -- untouched literal
CREATE OR REPLACE FUNCTION "ops"."claim_data_request"(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql AS $body$ BEGIN
 -- CREATE OR REPLACE FUNCTION ops.claim_data_request(
 RETURN jsonb_build_object('header','CREATE OR REPLACE FUNCTION ops.claim_data_request(');
END $body$;
CREATE FUNCTION ops.unrelated() RETURNS text LANGUAGE sql AS $$SELECT 'unchanged'$$;
"""
    changed = _rename_native_entrypoints(sql, {"claim_data_request"})
    before, after = prepare_sql(sql), prepare_sql(changed)
    assert before.excerpt(0) == after.excerpt(0)
    assert before.excerpt(2) == after.excerpt(2)
    from pglast import ast

    function_before, function_after = before.statements[1].stmt, after.statements[1].stmt
    assert isinstance(function_before, ast.CreateFunctionStmt)
    assert isinstance(function_after, ast.CreateFunctionStmt)
    assert body_source(function_before) == body_source(function_after)
    assert [part.sval for part in function_after.funcname or ()] == [
        "ops",
        "ddo_impl_claim_data_request",
    ]


def test_database_capacity_comes_from_owned_pool_or_explicit_unmanaged_reservation():
    from types import SimpleNamespace

    from corpus_structure.orchestrate.data_operations import _database_capacity

    engine = cast(
        Any, SimpleNamespace(_corpus_store=SimpleNamespace(pool=SimpleNamespace(max_size=5)))
    )
    assert _database_capacity(engine, None) == 5
    assert _database_capacity(engine, 3) == 3
    with pytest.raises(ValueError, match="exceeds"):
        _database_capacity(engine, 6)
    with pytest.raises(ValueError, match="explicit"):
        _database_capacity(cast(Any, object()), None)
    for capacity in (0, 1, 2, True):
        with pytest.raises(ValueError, match="capacity"):
            _database_capacity(cast(Any, object()), capacity)
    assert _database_capacity(cast(Any, object()), 6) == 6
