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
from corpus_structure.semantic._data_operation_wire import WireClaimDataRequestsRequest
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
from corpus_structure.semantic.data_operation_wire import (
    generated_wire_source, render_wire_types, validate_native_wire, wire_contract_digest, wire_contracts, wire_operations,
)
from corpus_structure.semantic.native_sql_body import body_source
from corpus_structure.semantic.operation_value_types import NativeResultViolation
from corpus_structure.semantic.prepared_sql import prepare_sql

REPO = Path(__file__).resolve().parents[4]


def test_checkout_wire_facade_is_generated_from_current_protocol_and_correspondence():
    assert Path(_data_operation_wire.__file__).read_text() == _format(
        "semantic/_data_operation_wire.py", generated_wire_source()
    )
    assert not hasattr(DataOperationStorage, "invoke")


def test_fixed_call_preserves_omission_and_rejects_wrong_union_result():
    class Connection:
        result = json_bytes({"contract_digest": wire_contract_digest(), "payload": {"items": [{"state": "no-work"}]}}).decode()

        def __init__(self):
            self.calls = []

        def scalar(self, statement, parameters):
            self.calls.append((statement, parameters))
            return self.result

    connection = Connection()
    storage = DataOperationStorage(cast(Any, connection))
    original = {"items": [{"request_id": "request:x", "generation": 1}], "holder": "worker", "lease_seconds": 3}
    assert storage.claim_data_requests(cast(WireClaimDataRequestsRequest, original)) == {
        "items": [{"state": "no-work"}]
    }
    assert wire_json_loads(connection.calls[0][1]["payload"]) == original
    assert "external_packet_id" not in original["items"][0]
    connection.result = json_bytes({"contract_digest": wire_contract_digest(), "payload": {"items": [{"state": "claimed"}]}}).decode()
    with pytest.raises(NativeResultViolation) as refusal:
        storage.claim_data_requests(cast(WireClaimDataRequestsRequest, original))
    assert refusal.value.operation == "data.claim_data_requests"
    assert refusal.value.result_class == "urn:corpus:data-wire:claim_data_requests_result"
    assert isinstance(refusal.value.original, ValueError)
    assert "schema" in str(refusal.value.original)
    # Request shape is enforced by SQL; exact Python JSON encodability stays local.
    before = len(connection.calls)
    with pytest.raises(ValueError):
        storage.claim_data_requests(cast(WireClaimDataRequestsRequest, {**original, "holder": object()}))
    assert len(connection.calls) == before


@pytest.mark.parametrize("digest", [None, "another-installed-contract"])
def test_native_client_requires_the_exact_installed_contract_before_result_use(digest):
    class Connection:
        def scalar(self, statement, parameters):
            value = {"payload": {"items": [{"state": "no-work"}]}}
            if digest is not None:
                value["contract_digest"] = digest
            return json_bytes(value).decode()

    storage = DataOperationStorage(cast(Any, Connection()))
    with pytest.raises(NativeResultViolation):
        storage.claim_data_requests({"holder": "worker", "lease_seconds": 3, "items": []})



def test_captured_structural_calls_keep_decimal_and_changed_protocol_fields(monkeypatch):
    sources = native_protocol_sources()
    protocol = next(item for item in sources if item.name == "native/data-operation-protocol.yaml")
    document = yaml.safe_load(protocol.content)
    request = document["definitions"]["record_data_fate_request"]
    request["properties"]["analyzed_scope"] = {"$ref": "#/definitions/json_value"}
    request["properties"]["source_revision"] = {"type": "string", "enum": ["reviewed"]}
    request["required"].append("source_revision")
    output = document["definitions"]["record_data_fate_result"]
    output["properties"]["analyzed_scope"] = {"$ref": "#/definitions/json_value"}
    output["required"].append("analyzed_scope")
    sources = tuple(
        replace(item, content=yaml.safe_dump(document).encode())
        if item.name in {protocol.name, "native/projection-physical/data-operation-native.yaml"}
        else item
        for item in sources
    )
    model = compile_data_operations(
        declarations=(native_operation_declarations(sources),), captured_contracts=sources
    )
    calls = tuple(
        item
        for item in native_operation_calls(model, sources=sources)
        if item[0] == "data.record_data_fate"
    )
    artifact = compile_data_operation_artifacts(
        model, calls, native_source_digest=native_source_digest(sources)
    )
    assert b"source_revision: Required[Literal['reviewed']]" in artifact.calls
    assert b"class WireRecordDataFateRequest(TypedDict)" in artifact.calls
    module = ModuleType("corpus_structure.semantic._wire_generation_control")
    module.__package__ = "corpus_structure.semantic"
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(artifact.calls, "captured-wire-control.py", "exec"), module.__dict__)
    context_checks = []
    module.__dict__["require_call_context"] = lambda *args: context_checks.append(args)
    payload = {
        "obligation_id": "obligation:x",
        "fate": "awaiting-inputs",
        "selection": {},
        "analyzed_scope": {"coordinate": Decimal("0.12345678901234567890123456789")},
        "source_revision": "reviewed",
    }
    prepare = module.__dict__["prepare_record_data_fate"]
    with pytest.raises(TypeError):
        prepare(payload=payload)
    statement = prepare(payload=payload, projection_context=object())
    encoded = statement.compile().params["payload"]
    assert (
        wire_json_loads(encoded)["analyzed_scope"]["coordinate"]
        == payload["analyzed_scope"]["coordinate"]
    )
    assert context_checks[0][1] == "data.record_data_fate"
    omitted = {key: value for key, value in payload.items() if key != "source_revision"}
    # Preparation preserves bytes; the captured SQL request validator rejects omission.
    assert "source_revision" not in wire_json_loads(prepare(
        payload=omitted, projection_context=object()
    ).compile().params["payload"])
    with pytest.raises(ValueError, match="source_revision"):
        validate_native_wire("record_data_fate", "input", omitted, sources)

    # Exercise the emitted result function itself, including its exact decoder.
    class Connection:
        def scalar(self, statement):
            return json_bytes(
                {
                    "contract_digest": wire_contract_digest(sources),
                    "payload": {
                        "use_id": "use:x",
                        "fate": "awaiting-inputs",
                        "analyzed_scope": payload["analyzed_scope"],
                    }
                }
            ).decode()

    result = module.__dict__["record_data_fate"](
        Connection(), payload=payload, projection_context=object()
    )
    assert result["payload"]["analyzed_scope"] == payload["analyzed_scope"]
    assert isinstance(result["payload"]["analyzed_scope"]["coordinate"], Decimal)
    # Embedded captured schema is not affected by ambient checkout protocol edits.
    assert (
        json.loads(json.loads(artifact.manifest)["calls"][0][1]["parameters"][0]["wire_schema"])[
            "definitions"
        ]["record_data_fate_request"]["required"][-1]
        == "source_revision"
    )


def test_set_protocol_uses_one_item_catalogue_and_preserves_nominal_identities():
    operations = {item["name"]: item for item in wire_operations()}
    assert {"attach_data_requests", "claim_data_requests"} <= operations.keys()
    assert not {"attach_data_request", "claim_data_request", "expand_data_obligation"} & operations.keys()
    assert not hasattr(DataOperationStorage, "attach_data_request")
    assert not hasattr(DataOperationStorage, "claim_data_request")
    assert not hasattr(DataOperationStorage, "expand_data_obligation")
    source = generated_wire_source()
    assert "class WireClaimDataRequestsItem(TypedDict):" in source
    assert "request_id: Required[WireRequestId]" in source
    assert "task_id: Required[TaskId]" in source
    assert "def claim_data_requests(" in source
    assert "def claim_data_request(" not in source


def test_captured_set_schema_follows_item_request_and_result_changes():
    sources = native_protocol_sources()
    protocol = next(item for item in sources if item.name == "native/data-operation-protocol.yaml")
    document = yaml.safe_load(protocol.content)
    item_request = document["definitions"]["claim_data_request_request"]
    item_request["properties"]["native_pin"] = {"type": "string"}
    item_request["required"].append("native_pin")
    item_result = document["definitions"]["claim_data_request_result"]["oneOf"][1]
    item_result["properties"]["receipt"] = {"type": "string"}
    item_result["required"].append("receipt")
    changed = tuple(replace(item, content=yaml.safe_dump(document).encode())
                    if item.name in {protocol.name, "native/projection-physical/data-operation-native.yaml"}
                    else item for item in sources)
    schema = wire_contracts(changed)["claim_data_requests"]
    assert "native_pin" in schema["input"]["definitions"]["claim_data_requests_item"]["required"]
    assert "holder" not in schema["input"]["definitions"]["claim_data_requests_item"]["properties"]
    assert "receipt" in schema["output"]["definitions"]["claim_data_requests_claimed_result"]["required"]
    assert wire_contract_digest(changed) != wire_contract_digest(sources)
    with pytest.raises(ValueError):
        validate_native_wire("claim_data_requests", "input", {
            "holder": "worker", "lease_seconds": 3,
            "items": [{"request_id": "request:x", "generation": 1}],
        }, changed)



def test_ddo_binding_cannot_fall_back_when_installed_contract_authority_is_missing():
    from corpus_structure.semantic.native_call_generation import render_call_bindings

    sources = native_protocol_sources()
    owner, call = next(item for item in native_operation_calls(sources=sources)
                       if item[0] == "data.claim_data_requests")
    with pytest.raises(ValueError, match="captured installed wire contract"):
        render_call_bindings(
            ((owner, replace(call, wire_contract_digest=None)),),
            identifiers_module=".identifiers",
        )



def test_structural_generation_refuses_unsupported_construct_at_its_source():
    with pytest.raises(ValueError, match="#/definitions/new_shape"):
        render_wire_types({"new_shape": {"allOf": [{"type": "string"}]}})


@pytest.mark.skipif(shutil.which("pyrefly") is None, reason="blocked: pyrefly unavailable")
def test_fixed_native_caller_preserves_nominal_ids_unions_and_required_keys(tmp_path):
    source = tmp_path / "consumer.py"
    source.write_text(
        "from corpus_structure.semantic._data_operation_wire import WireDemandId, WireRequestId, WireClaimDataRequestsResult\n"
        "from corpus_structure.semantic.identifiers import TaskId, ReleaseId, RuntimeId\n"
        "from corpus_structure.semantic._data_operation_wire import WireInspectDataExecutionRequest, WireOperationId\n"
        "from corpus_structure.semantic.data_operation_storage import DataOperationStorage\n"
        "def good(storage: DataOperationStorage) -> None:\n"
        "    results = storage.claim_data_requests({'items': [{'request_id': WireRequestId('r'), 'generation': 1}], 'holder': 'worker', 'lease_seconds': 3})\n"
        "    result = results['items'][0]\n"
        "    if result['state'] == 'claimed':\n"
        "        task: TaskId = result['result']['task_id']\n"
        "    pin: WireInspectDataExecutionRequest = {'operation_id': WireOperationId('o'), 'release_id': ReleaseId('r'), 'runtime_id': RuntimeId('x')}\n"
    )
    executable = shutil.which("pyrefly")
    assert executable is not None
    command = [executable, "check", "--config", str(REPO / "pyproject.toml"), str(source)]
    passed = subprocess.run(command, capture_output=True, text=True, check=False)
    assert passed.returncode == 0, passed.stdout + passed.stderr
    with source.open("a") as stream:
        stream.write(
            "def bad(storage: DataOperationStorage, result: WireClaimDataRequestsResult) -> None:\n"
            "    storage.claim_data_requests({'items': [{'request_id': WireDemandId('d'), 'generation': 1}], 'holder': 'w', 'lease_seconds': 3})\n"
            "    storage.claim_data_requests({'items': [{'request_id': WireRequestId('r')}]})\n"
            "    task: TaskId = result['items'][0]['result']['task_id']\n"
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
    sql = """-- misleading CREATE OR REPLACE FUNCTION ops.claim_data_requests(
SELECT 'CREATE OR REPLACE FUNCTION ops.claim_data_requests(';  -- untouched literal
CREATE OR REPLACE FUNCTION "ops"."claim_data_requests"(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql AS $body$ BEGIN
 -- CREATE OR REPLACE FUNCTION ops.claim_data_requests(
 RETURN jsonb_build_object('header','CREATE OR REPLACE FUNCTION ops.claim_data_requests(');
END $body$;
CREATE FUNCTION ops.unrelated() RETURNS text LANGUAGE sql AS $$SELECT 'unchanged'$$;
"""
    changed = _rename_native_entrypoints(sql, {"claim_data_requests"})
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
        "ddo_impl_claim_data_requests",
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
