"""Authored native read-result pages checked against the current wire contract."""

from decimal import Decimal
from typing import Any

from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.data_operation_wire import validate_native_wire


def demand_result_page(*, trust=None, member_id=None, empty=False) -> dict[str, Any]:
    body = dict(
        members=[
            dict(
                member_id="first",
                kind_contract="kind:first",
                context=dict(
                    subject="one",
                    original_source="source:A",
                    analyzed_scope={"scale": Decimal("1.20")},
                    subject_definition="document",
                ),
                body={"amount": Decimal("12.340")},
            ),
            dict(
                member_id="second",
                kind_contract="kind:second",
                context=dict(
                    subject="two",
                    original_source="source:A",
                    analyzed_scope={},
                    subject_definition="document",
                ),
                body={"target": "first", "direction": "outgoing"},
            ),
        ]
    )
    intent = dict(
        version="data-demand-intent-v2",
        model="a" * 64,
        roots=[],
        targets=["op:A"],
        operations=[
            dict(
                operation="op:A",
                parameters={},
                choices={},
                replicate=None,
                dependencies=[],
                definition="definition:A",
                recipe="recipe:A",
                eligibility="eligible",
                parameter_meaning=semantic_value({}),
            )
        ],
        root_operations=["op:A"],
        discovery=[],
        inference="authored-review",
        execution_profile="authored-profile",
    )
    result = dict(
        demand_id="demand:A",
        project_id="project:A",
        release_id="release:A",
        runtime_id="runtime:A",
        selection=intent,
        intent=intent,
        root=[],
        trust_snapshot={} if trust is None else trust,
        read_id="read:A",
        read_snapshot="1:2:",
        frontier_at="2026-11-14T00:00:00+00:00",
        scope={},
        view="products",
        state="active",
        populations=[],
        original_source_admissions=[],
        continuation=None,
        obligations=[
            dict(
                id="obligation:A",
                obligation_id="obligation:A",
                demand_id="demand:A",
                operation_id="op:A",
                subject="root",
                subject_definition="document",
                original_source="source:A",
                analyzed_scope={},
                parameters={},
                inputs_watermark="authored-inputs",
                historical_fate=None if empty else "fulfilled",
                fate="waiting" if empty else "fulfilled",
                native_settlement=None,
                native_readiness=None,
                request_id=None if empty else "request:A",
                generation=None if empty else 1,
                intent_id=None,
            )
        ],
        uses=[]
        if empty
        else [
            dict(
                use_id="use:A",
                obligation_id="obligation:A",
                fate="fulfilled",
                historical_fate="fulfilled",
                request_id="request:A",
                generation=1,
                selection={},
                trust_snapshot={},
                semantic_outcome="success",
                completion_state="success",
                derivation_id="episode:original",
                products=[
                    dict(
                        role="result",
                        position=0,
                        multiplicity=2,
                        product_id="product:A",
                        member_id=member_id,
                        kind_contract="kind:container",
                        subject="root",
                        original_source="source:A",
                        analyzed_scope={},
                        body_state="present",
                        body=semantic_value(body),
                        subject_definition="document",
                    )
                ],
            )
        ],
    )

    return validate_native_wire("read_demand_result", "output", result)
