"""Independent frozen scope, selected dependency and runtime custody expectations."""

from __future__ import annotations

import math
from datetime import date
from decimal import Decimal
from typing import cast

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_demands import (
    DiscoverySelection,
    OperationSelection,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_model import MODEL_VERSION
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import SourceArtifact


def operation(name, **changes):
    return {
        "id": name,
        "profile": "derivation",
        "subject": "document",
        "context": [],
        "roles": [
            {
                "name": "result",
                "kind": "integer",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            }
        ],
        "applicability": ["declared"],
        "invariants": ["integer"],
        "coverage": "whole",
        "outcomes": ["produced"],
        "precision": "exact",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "none",
            "cancellation": "call-boundary",
            "ownership": "immutable",
        },
        "behavior": "integer-one-v1",
        "parameters": {},
        "binding": {"operator": "all", "children": []},
        **changes,
    }


def model(*operations):
    return compile_data_operations(
        declarations=(
            SourceArtifact(
                "ops", canonical_bytes({"version": MODEL_VERSION, "operations": operations})
            ),
        )
    )


def freeze(compiled, **changes):
    return freeze_demand(
        compiled,
        roots=(RootSubject("document:one", "source:one", b'{"whole":true}'),),
        targets=("op:result",),
        inference="inference:exact",
        execution_profile="execution:one",
        **changes,
    )


def test_demand_freezes_only_selected_transitive_closure_and_source_membership():
    compiled = model(
        operation("op:base"),
        operation("op:unused"),
        operation("op:result", dependencies=["op:base"]),
    )
    intent = freeze(compiled)
    assert {item["operation"] for item in intent.record["operations"]} == {"op:base", "op:result"}
    assert intent.record["roots"] == [
        {
            "subject": "document:one",
            "original_source": "source:one",
            "analyzed_scope": {"whole": True},
        }
    ]
    exposed = intent.record
    exposed["roots"].append({"subject": "later"})
    assert len(intent.record["roots"]) == 1
    assert intent.record["operations"][1]["definition"].startswith("definition:")


def test_demand_selects_potential_edges_and_rejects_outside_choices():
    compiled = model(
        operation("op:a"),
        operation("op:b"),
        operation("op:result", potential_dependencies=["op:a", "op:b"]),
    )
    selected = freeze(
        compiled, selections=(OperationSelection("op:result", selected_dependencies=("op:b",)),)
    )
    assert {item["operation"] for item in selected.record["operations"]} == {"op:result", "op:b"}
    with pytest.raises(ValueError, match="outside"):
        freeze(
            compiled,
            selections=(OperationSelection("op:result", selected_dependencies=("op:missing",)),),
        )


def test_discovered_targets_are_not_seeded_on_unrelated_root_subjects():
    compiled = model(
        operation("op:discover", profile="discovery"), operation("op:result"), operation("op:child")
    )
    intent = freeze(
        compiled, discovery=(DiscoverySelection("op:discover", "result", "op:child", "passages"),)
    )
    assert set(intent.record["root_operations"]) == {"op:discover", "op:result"}
    assert {item["operation"] for item in intent.record["operations"]} == {
        "op:discover",
        "op:result",
        "op:child",
    }


def test_selected_cycle_refuses_even_if_potential_graph_was_allowed():
    compiled = model(
        operation("op:result", potential_dependencies=["op:other"]),
        operation("op:other", potential_dependencies=["op:result"]),
    )
    with pytest.raises(ValueError, match="cycle"):
        freeze(
            compiled,
            selections=(
                OperationSelection("op:result", selected_dependencies=("op:other",)),
                OperationSelection("op:other", selected_dependencies=("op:result",)),
            ),
        )


def test_frozen_parameter_defaults_match_the_later_binding_manifest():
    compiled = model(
        operation(
            "op:result",
            parameters={"threshold": {"value_type": "integer", "default": 7, "required": False}},
        )
    )
    intent = freeze(compiled)
    assert intent.record["operations"][0]["parameters"] == {"threshold": 7}
    with pytest.raises(ValueError, match="integer"):
        freeze(
            compiled,
            selections=(OperationSelection("op:result", parameters=b'{"threshold":null}'),),
        )


def test_frozen_typed_parameters_survive_jsonb_display_loss():
    from corpus_structure.semantic.data_operation_identity import (
        decode_semantic_value,
        semantic_value,
    )

    values = {"zero": -0.0, "day": date(2026, 11, 13), "amount": Decimal("1.25")}
    compiled = model(
        operation(
            "op:result",
            parameters={
                "zero": {"value_type": "float"},
                "day": {"value_type": "date"},
                "amount": {"value_type": "decimal"},
            },
        )
    )
    intent = freeze(
        compiled,
        selections=(
            OperationSelection(
                "op:result", parameter_meaning=canonical_bytes(semantic_value(values))
            ),
        ),
    )
    selected = intent.record["operations"][0]
    restored = decode_semantic_value(selected["parameter_meaning"])
    assert math.copysign(1, restored["zero"]) == -1
    assert restored["day"] == date(2026, 11, 13)
    assert restored["amount"] == Decimal("1.25")


@pytest.mark.parametrize("state", ["committed", "known-uncommitted", "unavailable"])
def test_resume_preserves_exact_completion_observation_separate_from_frontier(state):
    from hashlib import sha256

    from corpus_structure.semantic.data_operation_demands import DemandPlanner
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage

    compiled = model(operation("op:result"))
    snapshot = {
        "intent": {"model": sha256(compiled.content).hexdigest()},
        "obligations": [
            {"intent_id": "intent:old", "request_id": "request:one", "generation": 3},
            {"intent_id": None},
        ],
    }
    observation = {"state": state, "intent_retained": state != "unavailable"}
    calls = []

    class Storage:
        def invoke(self, operation, payload):
            calls.append((operation, payload))
            return snapshot if operation == "read_demand_result" else observation

    resumed = DemandPlanner(compiled, cast(DataOperationStorage, Storage())).resume("demand:one")
    assert calls == [
        ("read_demand_result", {"demand_id": "demand:one", "limit": 100}),
        (
            "inspect_data_completion",
            {
                "intent_id": "intent:old",
                "demand_id": "demand:one",
                "request_id": "request:one",
                "generation": 3,
            },
        ),
    ]
    assert resumed["completion_inspections"] == {"intent:old": observation}
    assert "completion_inspections" not in snapshot


@pytest.mark.parametrize(
    ("native", "expected"),
    [
        ({"action": "compute", "retained_intent_id": None}, "compute"),
        ({"action": "reconcile", "retained_intent_id": "intent:old"}, "reconcile"),
        ({"action": "reconcile"}, None),
        ({"action": "compute", "retained_intent_id": "intent:old"}, None),
        ({"action": "reuse"}, None),
        ({"action": "compute", "retained_intent_id": ""}, None),
    ],
)
def test_ready_request_retains_native_execution_disposition(native, expected):
    from corpus_structure.semantic.data_operation_bindings import BindingResult
    from corpus_structure.semantic.data_operation_demands import ReadyDataRequest
    from corpus_structure.semantic.data_operation_model import ResolvedOperationBinding

    binding = ResolvedOperationBinding(
        "op:result", "subject:one", (), b"{}", "exact", b"{}", b"{}", "cpu"
    )
    original = BindingResult(
        "op:result",
        "subject:one",
        (),
        "ready",
        (),
        b"{}",
        b"{}",
        "data-operation-model-v2",
        "definition:one",
        "eligibility:one",
        (),
    )

    def request():
        return ReadyDataRequest(
            "obligation:one",
            "op:result",
            "subject:one",
            b"{}",
            b"{}",
            canonical_bytes(native),
            b"{}",
            binding,
            original,
        )

    if expected is None:
        with pytest.raises(ValueError):
            request()
    else:
        ready = request()
        assert ready.action == expected
        assert ready.retained_intent_id == native["retained_intent_id"]


def test_frozen_source_sets_are_explicit_selected_operation_scope():
    from dataclasses import replace

    from corpus_structure.semantic.data_operation_model import InputSupport, OperationRole
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, SourceSetEntry
    from corpus_structure.semantic.structural_products import ExternalSourceRef

    compiled = model(operation("op:result"))
    op = compiled.operations[0]
    role = OperationRole(
        "source",
        "primitive:string",
        "input",
        1,
        1,
        "scalar",
        "required",
        InputSupport(
            "exact",
            "frozen-source-set",
            "whole",
            identity_requirements=("episode",),
            source_set="inputs",
            source_reference_field="source_ref",
        ),
    )
    compiled = replace(compiled, operations=(replace(op, roles=(role,)),))
    reference = ExternalSourceRef(
        project_id="project",
        run_id=1,
        cut_id=2,
        release_id="release",
        result_revision=0,
        source_view_id=3,
        native_task_id=4,
        native_product_key="native:key",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )
    entry = SourceSetEntry.from_structural_source(
        reference,
        original_source="source:foreign",
        subject="view:original",
        analyzed_scope=b'{"page":1}',
        product="product:one",
    )
    scope = FrozenSourceSet("inputs", (entry,))
    with pytest.raises(ValueError, match="lacks.*source set"):
        freeze(compiled)
    frozen = freeze(compiled, source_sets=(scope,))
    assert frozen.record["source_sets"]["inputs"][0]["original_source"] == "source:foreign"
    assert frozen.record["roots"] == [
        {
            "subject": "document:one",
            "original_source": "source:one",
            "analyzed_scope": {"whole": True},
        }
    ]
    with pytest.raises(ValueError, match="exactly match"):
        freeze(compiled, source_sets=(scope, FrozenSourceSet("unused", (entry,))))
