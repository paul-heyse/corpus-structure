"""Projection interpretation counterexamples; protocol examples establish no native authenticity."""

from copy import deepcopy
from hashlib import sha256
from typing import Any

import pytest

from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.execution_evidence_leaf import (
    NativeExecutionEvidenceLeaf,
    execution_evidence_leaf_schema,
    validate_execution_evidence_leaf,
)
from corpus_structure.semantic.identity import canonical_bytes


def protocol_example():
    """Closed wire facts only. These headers are not presented as executed receipts."""
    producer = dict(
        request_id="request", generation=2, task_id=11, attempt=3, holder="original-holder"
    )
    cpu = dict(
        request_digest="a" * 64,
        pid=23,
        main_thread=True,
        native_thread_limit=1,
        native_pools_json="[]",
        result_digest="b" * 64,
    )
    body = semantic_value({"selected": 7})
    completion = dict(
        implementation_revision="implementation",
        outcome="success",
        inputs=[],
        support=[],
        outputs=[
            dict(
                role="result",
                position=0,
                multiplicity=1,
                product=dict(kind_contract="kind", body=body, members=[]),
            )
        ],
        execution_evidence=dict(
            version="native-execution-evidence-v1",
            **producer,
            runtime_id="runtime",
            cpu_receipts=[cpu],
            host_receipts=[],
        ),
    )
    value = dict(
        format="ddo-native-execution-evidence-leaf-v1",
        derivation_id="episode",
        use_id="use",
        issuer_operation="encoder",
        release_id="release",
        runtime_id="runtime",
        recipe="recipe",
        producer=producer,
        intent_id="intent",
        intent_payload_digest="c" * 64,
        selected_completion=completion,
        publication_receipt_id="publication",
        product_id="product",
        kind_contract="kind",
        output_role="result",
        output_position=0,
        cpu_receipt=cpu,
        whole_reply_digest="b" * 64,
        member="selected-member",
        member_ordinal=1,
        cohort_size=3,
        cohort_membership_digest="d" * 64,
        input_basis_digest="e" * 64,
        member_output_digest=sha256(canonical_bytes(body)).hexdigest(),
        physical_cohort="undisclosed",
        verification="native-checked-member-projection",
    )
    closure = dict(
        products={"product": dict(kind_contract="kind", canonical_body=body)},
        requests={"request": dict(operation_id="encoder")},
        derivations={
            "episode": dict(
                request_id="request",
                intent_id="intent",
                producer_task_id=11,
                producer_attempt=3,
                generation=2,
                runtime_id="runtime",
                release_id="release",
                recipe="recipe",
            )
        },
        receipts={"publication": dict(intent_id="intent", derivation_id="episode")},
        definitions={
            ("release", "encoder"): dict(
                profile="derivation",
                recipe="recipe",
                output_roles=[dict(name="result", kind_contract="kind", collection="scalar")],
                support_contract=dict(
                    effects=[],
                    result_fields={},
                    capabilities=dict(forms=["batch"], preparation="resource"),
                ),
            )
        },
        runtimes={("release", "runtime"): {}},
        outputs=[
            dict(
                derivation_id="episode",
                product_id="product",
                role="result",
                position=0,
                member_id=None,
            )
        ],
        uses={
            "use": dict(
                derivation_id="episode", request_id="request", generation=2, fate="fulfilled"
            )
        },
    )
    return value, closure


def test_projection_keeps_selected_completion_facts_and_explicit_hidden_cohort():
    value, closure = protocol_example()
    leaf = validate_execution_evidence_leaf(value, **closure)
    assert leaf.selected_completion == value["selected_completion"]
    assert leaf.cohort_size == 3 and leaf.member_ordinal == 1
    assert leaf.physical_cohort == "undisclosed"
    assert "cpu_replies" not in leaf.selected_completion["execution_evidence"]


def test_detached_execution_contract_validates_its_explicit_schema_dialect():
    from jsonschema import Draft202012Validator, ValidationError

    schema = execution_evidence_leaf_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(schema)
    value, _ = protocol_example()
    validator = Draft202012Validator(schema)
    validator.validate(value)
    value["member_ordinal"] = -1
    with pytest.raises(ValidationError):
        validator.validate(value)


@pytest.mark.parametrize(
    "change",
    [
        "reply",
        "release",
        "use",
        "missing_use",
        "output",
        "product",
        "producer",
        "runtime",
        "receipt",
        "ordinal",
    ],
)
def test_projection_refuses_conflicting_current_edges_and_original_receipt(change):
    value, closure = protocol_example()
    value = deepcopy(value)
    if change == "reply":
        value["selected_completion"]["execution_evidence"]["cpu_replies"] = []
    elif change == "release":
        closure["derivations"]["episode"]["release_id"] = "another-release"
    elif change == "use":
        closure["uses"]["use"]["generation"] = 3
    elif change == "missing_use":
        closure.pop("uses")
    elif change == "output":
        value["selected_completion"]["outputs"][0]["product"]["body"] = semantic_value(
            {"selected": 8}
        )
    elif change == "product":
        closure["products"]["product"]["canonical_body"] = semantic_value({"selected": 8})
    elif change == "producer":
        value["producer"]["holder"] = "adopting-holder"
    elif change == "runtime":
        value["runtime_id"] = "adopting-runtime"
    elif change == "receipt":
        value["whole_reply_digest"] = "f" * 64
    else:
        value["member_ordinal"] = 3
    with pytest.raises(ValueError):
        validate_execution_evidence_leaf(value, **closure)


def test_projection_does_not_accept_raw_intent_or_additional_sibling_body():
    value, _ = protocol_example()
    value["sibling_output"] = {"private": "body"}
    with pytest.raises(ValueError):
        NativeExecutionEvidenceLeaf.model_validate_json(canonical_bytes(value))


def test_two_role_execution_projections_keep_complete_detached_output_custody():
    from decimal import Decimal

    from corpus_structure.semantic.data_operation_identity import (
        body_identity,
        contextual_product_identity,
    )
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.demand_results import verify_detached_result
    from semantic.test_demand_results import _detached_closure

    native, records = _detached_closure()
    product = next(row["record"] for row in records if row["relation"] == "kb.data_product")
    definition = next(
        row["record"] for row in records if row["relation"] == "sem.data_operation_definition"
    )
    definition.update(
        profile="derivation",
        input_roles=[],
        output_roles=[
            dict(name=role, kind_contract=product["kind_contract"], collection="scalar")
            for role in ("result", "vector")
        ],
    )
    definition["support_contract"].update(
        effects=[],
        result_fields={"result": "query", "vector": "vector"},
        capabilities=dict(forms=["batch"], preparation="resource"),
    )
    sibling = deepcopy(product)
    sibling["canonical_body"] = semantic_value({"amount": Decimal("17.50")})
    sibling["body_digest"] = body_identity({"amount": Decimal("17.50")}).key
    sibling["id"] = contextual_product_identity(
        kind=product["kind_contract"],
        body=sibling["body_digest"],
        context=SubjectContext(
            product["project_id"],
            product["subject"],
            product["original_source"],
            json_bytes(product["analyzed_scope"]),
            subject_definition=product["subject_definition"],
        ),
    ).key
    records = [row for row in records if row["relation"] != "ops.data_completion_intent"]
    records.extend(
        (
            dict(relation="kb.data_product", key="second-product", record=sibling),
            dict(
                relation="ops.data_derivation_output",
                key="second-output",
                record=dict(
                    derivation_id="episode:A",
                    role="vector",
                    position=0,
                    multiplicity=1,
                    member_id=None,
                    product_id=sibling["id"],
                ),
            ),
        )
    )
    native["uses"][0]["products"].append(
        dict(
            product_id=sibling["id"],
            member_id=None,
            role="vector",
            position=0,
            multiplicity=1,
            body=sibling["canonical_body"],
        )
    )
    leaves: list[dict[str, Any]] = []
    for role, selected_product in (("result", product), ("vector", sibling)):
        value, _ = protocol_example()
        producer = dict(
            request_id="request:A", generation=1, task_id=1, attempt=1, holder="original-holder"
        )
        value.update(
            derivation_id="episode:A",
            use_id=None,
            issuer_operation="op:A",
            release_id="release:A",
            runtime_id="runtime:A",
            recipe="recipe:A",
            producer=producer,
            intent_id="intent:A",
            publication_receipt_id="receipt:A",
            product_id=selected_product["id"],
            kind_contract=product["kind_contract"],
            output_role=role,
            member_output_digest=sha256(
                canonical_bytes(selected_product["canonical_body"])
            ).hexdigest(),
        )
        value["selected_completion"]["outputs"] = [
            dict(
                role=role,
                position=0,
                multiplicity=1,
                product=dict(
                    kind_contract=product["kind_contract"],
                    body=selected_product["canonical_body"],
                    members=[],
                ),
            )
        ]
        value["selected_completion"]["execution_evidence"].update(
            **producer, runtime_id="runtime:A"
        )
        leaves.append(
            dict(relation="ops.data_execution_evidence_leaf", key="leaf:" + role, record=value)
        )
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.native_definition_projection import NativeOperationProjection

    fields = set(table("sem.data_operation_definition").c.keys())
    complete_definition = {name: definition.get(name) for name in fields}
    exported_fields = fields & {"release_id", *NativeOperationProjection.__required_keys__}
    definition.clear()
    definition.update({name: complete_definition[name] for name in exported_fields})
    options = dict(
        wire_schema={},
        runtimes={("release:A", "runtime:A")},
        definitions={("release:A", "op:A"): complete_definition},
    )
    assert verify_detached_result(native, records=[*records, *leaves], **options)
    assert all(len(row["record"]["selected_completion"]["outputs"]) == 1 for row in leaves)
    with pytest.raises(ValueError, match="output inventory"):
        verify_detached_result(native, records=[*records, leaves[0]], **options)
    changed = deepcopy(leaves)
    changed[1]["record"]["intent_payload_digest"] = "f" * 64
    with pytest.raises(ValueError, match="conflicting member custody"):
        verify_detached_result(native, records=[*records, *changed], **options)
    changed = deepcopy(leaves)
    changed[1]["record"]["output_role"] = "foreign-role"
    with pytest.raises(ValueError, match="selected producer/publication"):
        verify_detached_result(native, records=[*records, *changed], **options)
    changed = deepcopy(leaves)
    changed[1]["record"]["selected_completion"]["outputs"][0]["member_id"] = "foreign-member"
    with pytest.raises(ValueError, match="exact logical output"):
        verify_detached_result(native, records=[*records, *changed], **options)


def test_execution_leaf_program_uses_explicit_target_metadata_and_archived_result_fields():
    from types import SimpleNamespace

    from pglast import parse_sql
    from sqlalchemy import MetaData

    from corpus_structure.semantic.execution_evidence_leaf import execution_evidence_leaf_native_sql
    from corpus_structure.semantic.metadata import get_metadata

    proposed_output = (
        get_metadata()
        .tables["ops.data_derivation_output"]
        .to_metadata(MetaData(), name="captured_output")
    )
    target = SimpleNamespace(
        tables={**get_metadata().tables, "ops.data_derivation_output": proposed_output}
    )
    source = execution_evidence_leaf_native_sql(target)
    assert parse_sql(source)
    assert "ops.captured_output" in source and "FROM ops.data_derivation_output" not in source
    assert "result_fields" in source
    assert "exact single-output logical member" not in source
