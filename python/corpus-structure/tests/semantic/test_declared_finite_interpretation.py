"""Independent finite-result expectations over selected candidate products."""

import json
from dataclasses import asdict
from math import log
from pathlib import Path

import pytest

from corpus_structure.methods.local_interpretation import local_constraint_id
from corpus_structure.semantic import record_interpretation as ri
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.finite_interpretation_products import (
    finite_interpretation_inputs,
    finite_interpretation_operation_sources,
    finite_interpretation_reports,
    finite_interpretation_values,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


def candidates(*, records=(), contributions=()):
    return {
        "standing": "private_uncalibrated_candidates",
        "source_pin": {"source_product": "source:original"},
        "members": tuple(
            {"body": {**row, "candidate_type": kind}}
            for kind, rows in (("record", records), ("contribution", contributions))
            for row in rows
        ),
    }


def policy(mode, requests, dependencies=()):
    return {"version": "finite-interpretation-policy-1", "mode": mode, "requests": source_value(json.loads(canonical_bytes(requests))), "dependencies": dependencies}


def test_finite_operation_has_captured_factory_and_source_witness():
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    bundle = finite_interpretation_inputs(SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),)))
    model = compile_data_operations(bundle, python_sources=finite_interpretation_operation_sources())
    operation = model.operation("interpret.finite_candidates")
    assert operation.capabilities.prepared_factory is not None
    assert len(operation.output_witnesses) == 1
    assert operation.effects == ()
    assert all(item.complete for item in model.implementation_slices)


def test_finite_records_preserve_complete_baseline_without_fabricating_policy():
    records = tuple({"record_id": "occurrence", "interpretation_id": key, "standing": "candidate", "family": "measurement", "computation_dependencies": ("observation",)} for key in ("one", "two"))
    product = finite_interpretation_values(candidates(records=records), policy("records", {}))
    (report,) = finite_interpretation_reports(product)
    assert report["interpretation_ids"] == ["one", "two"]
    assert report["outcome"] == "not_run"
    assert report["probability_standing"] == "not_computed"
    assert "result" not in report
    assert product["standing"] == "private_candidate_relative"


def _local_request(scope):
    return ri.LocalInterpretationRequest(
        decisions=(ri.Decision("role", (ri.Candidate("actor"), ri.Candidate("object"))),),
        potentials=(ri.LogPotential("evidence", ("role",), (log(3), log(1)), ("observation",)),),
        constraints=(),
        dependencies=tuple(ri.Dependency(key, kind, "v1") for key, kind in (("observation", ri.DependencyKind.OBSERVATION), ("model", ri.DependencyKind.MODEL), ("ontology", ri.DependencyKind.ONTOLOGY), ("policy", ri.DependencyKind.POLICY))),
        selection=ri.CandidateSelection(scope, ("observation",)),
        model_dependency_id="model", ontology_dependency_id="ontology", policy_dependency_id="policy",
    )


def test_finite_local_consumer_retains_real_factor_probability_and_dependencies():
    contribution = {"contribution_id": "span", "computation_dependencies": ("observation",)}
    scope = local_constraint_id("role?", (contribution,), ("observation",))
    selected = [{"question": "role?", "contribution_ids": ["span"], "dependencies": ["observation"], "request": asdict(_local_request(scope))}]
    product = finite_interpretation_values(candidates(contributions=(contribution,)), policy("local", selected))
    (operation,) = finite_interpretation_reports(product)
    result = source_python(operation["local_interpretation"]["result"])
    assert operation["outcome"] == "succeeded"
    assert result["marginals"][0]["probability"] == pytest.approx(0.75)
    assert operation["computation_dependencies"] == ["observation"]


def test_finite_local_refuses_foreign_contribution_and_missing_policy_dependency():
    contribution = {"contribution_id": "span", "computation_dependencies": ("observation",)}
    with pytest.raises(ValueError, match="unselected contribution"):
        finite_interpretation_values(candidates(contributions=(contribution,)), policy("local", [{"question": "role?", "contribution_ids": ["foreign"], "dependencies": ["observation"]}]))
    scope = local_constraint_id("role?", (contribution,), ("observation", "required-policy"))
    selected = [{"question": "role?", "contribution_ids": ["span"], "dependencies": ["observation"], "request": asdict(_local_request(scope))}]
    with pytest.raises(ValueError, match="dependencies"):
        finite_interpretation_values(candidates(contributions=(contribution,)), policy("local", selected, ("required-policy",)))
