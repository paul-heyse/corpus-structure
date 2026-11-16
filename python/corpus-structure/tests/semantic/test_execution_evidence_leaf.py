"""Projection interpretation counterexamples; protocol examples establish no native authenticity."""

from copy import deepcopy
from hashlib import sha256

import pytest

from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.execution_evidence_leaf import NativeExecutionEvidenceLeaf, validate_execution_evidence_leaf
from corpus_structure.semantic.identity import canonical_bytes


def protocol_example():
    """Closed wire facts only. These headers are not presented as executed receipts."""
    producer = dict(request_id="request", generation=2, task_id=11, attempt=3, holder="original-holder")
    cpu = dict(request_digest="a" * 64, pid=23, main_thread=True, native_thread_limit=1,
        native_pools_json="[]", result_digest="b" * 64)
    body = semantic_value({"selected": 7})
    completion = dict(implementation_revision="implementation", outcome="success", inputs=[], support=[],
        outputs=[dict(role="result", position=0, multiplicity=1,
            product=dict(kind_contract="kind", body=body, members=[]))],
        execution_evidence=dict(version="native-execution-evidence-v1", **producer, runtime_id="runtime",
            cpu_receipts=[cpu], host_receipts=[]))
    value = dict(format="ddo-native-execution-evidence-leaf-v1", derivation_id="episode", use_id="use",
        issuer_operation="encoder", release_id="release", runtime_id="runtime", recipe="recipe",
        producer=producer, intent_id="intent", intent_payload_digest="c" * 64,
        selected_completion=completion, publication_receipt_id="publication", product_id="product",
        kind_contract="kind", output_role="result", output_position=0, cpu_receipt=cpu,
        whole_reply_digest="b" * 64, member="selected-member", member_ordinal=1, cohort_size=3,
        cohort_membership_digest="d" * 64, input_basis_digest="e" * 64,
        member_output_digest=sha256(canonical_bytes(body)).hexdigest(), physical_cohort="undisclosed",
        verification="native-checked-member-projection")
    closure = dict(products={"product": dict(kind_contract="kind", canonical_body=body)},
        requests={"request": dict(operation_id="encoder")},
        derivations={"episode": dict(request_id="request", intent_id="intent", producer_task_id=11,
            producer_attempt=3, generation=2, runtime_id="runtime", release_id="release", recipe="recipe")},
        receipts={"publication": dict(intent_id="intent", derivation_id="episode")},
        definitions={("release", "encoder"): dict(profile="derivation", recipe="recipe",
            support_contract=dict(effects=[], capabilities=dict(forms=["batch"], preparation="resource")))},
        runtimes={("release", "runtime"): {}}, outputs=[dict(derivation_id="episode", product_id="product",
            role="result", position=0, member_id=None)],
        uses={"use": dict(derivation_id="episode", request_id="request", generation=2, fate="fulfilled")})
    return value, closure


def test_projection_keeps_selected_completion_facts_and_explicit_hidden_cohort():
    value, closure = protocol_example()
    leaf = validate_execution_evidence_leaf(value, **closure)
    assert leaf.selected_completion == value["selected_completion"]
    assert leaf.cohort_size == 3 and leaf.member_ordinal == 1
    assert leaf.physical_cohort == "undisclosed"
    assert "cpu_replies" not in leaf.selected_completion["execution_evidence"]


@pytest.mark.parametrize("change", ["reply", "release", "use", "missing_use", "output", "product", "producer", "runtime", "receipt", "ordinal"])
def test_projection_refuses_conflicting_current_edges_and_original_receipt(change):
    value, closure = protocol_example()
    value = deepcopy(value)
    if change == "reply": value["selected_completion"]["execution_evidence"]["cpu_replies"] = []
    elif change == "release": closure["derivations"]["episode"]["release_id"] = "another-release"
    elif change == "use": closure["uses"]["use"]["generation"] = 3
    elif change == "missing_use": closure.pop("uses")
    elif change == "output": value["selected_completion"]["outputs"][0]["product"]["body"] = semantic_value({"selected": 8})
    elif change == "product": closure["products"]["product"]["canonical_body"] = semantic_value({"selected": 8})
    elif change == "producer": value["producer"]["holder"] = "adopting-holder"
    elif change == "runtime": value["runtime_id"] = "adopting-runtime"
    elif change == "receipt": value["whole_reply_digest"] = "f" * 64
    else: value["member_ordinal"] = 3
    with pytest.raises(ValueError):
        validate_execution_evidence_leaf(value, **closure)


def test_projection_does_not_accept_raw_intent_or_additional_sibling_body():
    value, _ = protocol_example()
    value["sibling_output"] = {"private": "body"}
    with pytest.raises(ValueError):
        NativeExecutionEvidenceLeaf.model_validate_json(canonical_bytes(value))
