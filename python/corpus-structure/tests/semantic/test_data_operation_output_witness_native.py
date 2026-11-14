"""Real retained-intent writer controls for grouped selected-member agreement."""

from copy import deepcopy
from dataclasses import replace
import json

import pytest
import yaml
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_demands import DemandPlanner
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_model import MODEL_VERSION, json_context_meaning
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identity import canonical_bytes
from semantic.data_operation_binding_support import discover
from semantic.data_operation_demand_support import claim, publish
from semantic.data_operation_kernel_support import POPULATION


def witness_recipe():
    schema = yaml.safe_load(POPULATION.schema_text)
    schema["classes"].update({
        "RecordSourcePin": {"attributes": {name: {"range": "string", "required": True} for name in ("source_product", "source_member", "subject", "analyzed_scope_meaning", "document")}},
        "RecordEnvelope": {"attributes": {"pins": {"range": "RecordSourcePin", "multivalued": True, "inlined_as_list": True, "required": True}}},
    })
    declarations = json.loads(POPULATION.declaration_content)
    declarations["version"] = MODEL_VERSION
    consumer = next(item for item in declarations["operations"] if item["id"] == "urn:consumer")
    next(role for role in consumer["roles"] if role["direction"] == "output")["kind"] = "RecordEnvelope"
    fields = {
        "source_product": ("selected-input", "product", "value"),
        "source_member": ("selected-input", "member", "value"),
        "subject": ("selected-input", "subject", "value"),
        "analyzed_scope_meaning": ("selected-input", "analyzed_scope", "context-meaning-json"),
        "document": ("Sample", "document_subject", "value"),
    }
    consumer["output_witnesses"] = [{"output_role": "result", "records": "/pins/*", "input_role": "items", "comparisons": [
        {"output_field": name, "input": {"role": "items", "projection": projection, "field": field}, "encoding": encoding}
        for name, (projection, field, encoding) in fields.items()
    ]}]
    return replace(POPULATION, name="grouped-output-witness", schema_text=yaml.safe_dump(schema), declaration_content=canonical_bytes(declarations))


WITNESS = witness_recipe()
pytestmark = pytest.mark.parametrize("ddo_kernel", [WITNESS], indirect=True, ids=["grouped-witness"])


def ready_completion(kernel):
    contexts = tuple({"subject": "item:" + str(value), "original_source": "source:test", "analyzed_scope": {"page": page}} for value, page in ((15, 1), (16, 2)))
    demand, _, _ = discover(kernel, values=(15, 16), member_contexts=contexts)
    with kernel["engine"].begin() as connection:
        planner = DemandPlanner(kernel["model"], DataOperationStorage(connection))
        assert planner.ready(planner.resume(demand["demand_id"]), authorization=b"{}") == ()
        (ready,) = planner.ready(planner.resume(demand["demand_id"]), authorization=b"{}")
    assert ready.operation == "urn:consumer"
    members = [member for role in ready.binding_result.roles for member in role.members]
    assert {member.member for member in members} == {"m15", "m16"}
    pins = [{"source_product": member.product, "source_member": member.member, "subject": member.subject, "analyzed_scope_meaning": json_context_meaning(member.analyzed_scope).decode(), "document": "doc"} for member in members]
    binding = json.loads(ready.binding)
    output_kind = next(role.kind for role in kernel["model"].operation(ready.operation).roles if role.direction == "output")
    completion = {
        "outcome": "success", "implementation_revision": "native-test-source-v1", "inputs": binding["inputs"], "support": binding["support"],
        "outputs": [{"role": "result", "position": 0, "multiplicity": 1, "product": {"kind_contract": kernel["identities"][output_kind, "kind"], "body": semantic_value({"pins": pins}), "members": []}}],
    }
    return ready, completion, pins


def test_native_writer_retains_and_publishes_complete_member_witnesses(ddo_kernel):
    ready, completion, _ = ready_completion(ddo_kernel)
    fence = claim(ddo_kernel, json.loads(ready.native))
    with ddo_kernel.purpose("write").begin() as writer:
        intent = DataOperationStorage(writer).invoke("retain_data_completion_intent", {**fence, "runtime_id": ddo_kernel["runtime"], "completion": completion})
    receipt = publish(ddo_kernel, fence, intent)
    assert receipt["derivation_id"]


@pytest.mark.parametrize("fault", ["product", "member", "context", "scope", "coordinate", "hybrid"])
def test_native_writer_refuses_schema_valid_pin_without_one_complete_member(ddo_kernel, fault):
    ready, completion, pins = ready_completion(ddo_kernel)
    forged = deepcopy(pins)
    changes = {"product": ("source_product", "product:foreign"), "member": ("source_member", "m16"), "context": ("subject", "item:foreign"), "scope": ("analyzed_scope_meaning", '["mapping",[]]'), "coordinate": ("document", "other:doc"), "hybrid": ("subject", "item:16")}
    field, value = changes[fault]
    forged[0][field] = value
    completion["outputs"][0]["product"]["body"] = semantic_value({"pins": forged})
    # Independent schema validity: the failure is selected-member agreement.
    ddo_kernel["prepared"].validate_python("RecordEnvelope", {"pins": forged})
    fence = claim(ddo_kernel, json.loads(ready.native))
    with ddo_kernel.purpose("write").begin() as writer:
        with pytest.raises(DBAPIError, match="output witness has no complete selected input member"), writer.begin_nested():
            DataOperationStorage(writer).invoke("retain_data_completion_intent", {**fence, "runtime_id": ddo_kernel["runtime"], "completion": completion})
    with ddo_kernel["engine"].connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM ops.data_completion_intent WHERE request_id=:request"), {"request": fence["request_id"]}) == 0
