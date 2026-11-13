"""Independent nominal packet and typed-value controls for direct scalar/batch ports."""

import copy
import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_ports import (
    PortRefusal,
    PythonBatchMember,
    PythonRoleValue,
    project_product_members,
    resolve_python_port,
)
from corpus_structure.semantic.identity import claim_source_item__data_operation__
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection


@pytest.fixture
def schema():
    content = b"""id: urn:members
name: members
prefixes:
  m: 'urn:members:'
  xsd: http://www.w3.org/2001/XMLSchema#
default_prefix: m
default_range: string
types:
  string: {base: str, uri: 'xsd:string'}
  decimal: {base: Decimal, uri: 'xsd:decimal'}
  date: {base: date, uri: 'xsd:date'}
classes:
  Unit:
    attributes:
      record_type: {required: true, equals_string: unit}
      amount: {range: decimal, required: true}
      when: {range: date, required: true}
  Context:
    attributes:
      subject: {required: true}
      original_source: {required: true}
      analyzed_scope: {required: true}
  Packet:
    attributes:
      member_id: {required: true}
      kind_contract: {required: true}
      context: {range: Context, inlined: true, required: true}
      body: {range: Unit, inlined: true, required: true}
  Container:
    attributes:
      members: {range: Packet, multivalued: true, inlined: true, required: true}
"""
    return SourceBundle("members", (SourceArtifact("members", content),))


def packet_value(model):
    body_kind = next(
        item.key
        for item in model.identities
        if item.owner == "urn:members:Unit" and item.domain == "kind"
    )
    return {
        "members": [
            dict(
                member_id="original-unit",
                kind_contract=body_kind,
                context=dict(
                    subject="original-subject",
                    original_source="original-document",
                    analyzed_scope="selected",
                ),
                body=dict(record_type="unit", amount=Decimal("0.10"), when=date(2026, 11, 13)),
            )
        ]
    }


@pytest.mark.parametrize("form", ["scalar", "batch"])
def test_original_direct_port_projects_actual_nominal_members_and_preserves_decimal_date(
    schema, tmp_path, monkeypatch, form
):
    metadata: dict[str, Any] = copy.deepcopy(claim_source_item__data_operation__)
    metadata["roles"] = [
        dict(
            name="inventory",
            kind="urn:members:Container",
            direction="input",
            minimum=1,
            maximum=1,
            collection="scalar",
            presence="required",
            parameter="inventory",
            support=dict(
                provenance="value_substitution",
                identity_requirements=[],
                source="original-source",
                coverage="selected-scope",
            ),
        ),
        dict(
            name="result",
            kind="urn:members:Container",
            direction="output",
            minimum=1,
            maximum=1,
            collection="scalar",
            presence="required",
        ),
    ]
    metadata["binding"] = {"operator": "scan", "roles": ["inventory"]}
    metadata["capabilities"]["forms"] = [form]
    module = "nominal_member_" + tmp_path.name.replace("-", "_")
    annotation = "dict" if form == "scalar" else "tuple[dict, ...]"
    content = (
        f"def project(inventory: {annotation}) -> {annotation}:\n"
        "    return inventory\n"
        f"project__data_operation__ = {metadata!r}\n"
    ).encode()
    path = tmp_path / (module + ".py")
    path.write_bytes(content)
    monkeypatch.syspath_prepend(str(tmp_path))
    sources = PythonSourceCollection((PythonSource(module, content, str(path)),))
    model = compile_data_operations(schema=schema, python_sources=sources)
    operation = model.operations[0]
    port = resolve_python_port(
        model, sources, operation.semantic_id, schema=schema, authorize=lambda _: None
    )
    kind = next(
        item.key
        for item in model.identities
        if item.owner == "urn:members:Container" and item.domain == "kind"
    )
    value = PythonRoleValue("inventory", kind, packet_value(model))
    completion = (
        port.invoke_python((value,))
        if form == "scalar"
        else port.invoke_batch_python((PythonBatchMember("one", (value,)),)).members[0][1]
    )
    (native,) = completion.outputs[0].members
    fields = dict(json.loads(native)["body"][1])
    assert fields["amount"] == ["decimal", "0.1"]
    assert fields["when"] == ["date", "2026-11-13"]
    assert json.loads(native)["member_id"] == "original-unit"


@pytest.mark.parametrize(
    "defect", ["missing", "extra", "nominal", "discriminator", "duplicate", "noncontainer"]
)
def test_projection_refuses_forged_or_missing_packet_authority(schema, defect):
    model = compile_data_operations(schema=schema)
    value = packet_value(model)
    packet = value["members"][0]
    kind = "urn:members:Container"
    if defect == "missing":
        packet.pop("kind_contract")
    elif defect == "extra":
        packet["kind"] = "invented-header"
    elif defect == "nominal":
        packet["kind_contract"] = "kind:not-admitted"
    elif defect == "discriminator":
        packet["body"]["record_type"] = "other"
    elif defect == "duplicate":
        value["members"].append(packet)
    else:
        kind = "primitive:string"
    with pytest.raises(PortRefusal):
        project_product_members(model, kind, value)
