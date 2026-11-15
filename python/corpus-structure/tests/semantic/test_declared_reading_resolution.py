"""Independent reading-score expectations; controlled ingress is not native admission."""

import json
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.reading_resolution_products import (
    RECIPE,
    DeclaredReadingFeatureInstance,
    reading_resolution_inputs,
    reading_resolution_declarations,
    reading_resolution_operation_sources,
    resolve_reading_values,
    resolved_reading_events,
)
from corpus_structure.semantic.record_policy import (
    FEATURES,
    FeatureInstance,
    FitDiagnostics,
    LinearParameters,
    PolicyApplicability,
    RecordAlgorithm,
)
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


def prepared_ingress():
    fields = SimpleNamespace(
        ancestors=("SemanticRecordFields",),
        properties=(
            SimpleNamespace(name="family", equals_string="table"),
            SimpleNamespace(name="value"),
        ),
    )
    return SimpleNamespace(
        release_id="controlled-release",
        index=SimpleNamespace(definitions={"ControlledFields": fields}),
        validate_json=lambda name, content: SimpleNamespace(
            model_dump=lambda **kwargs: json.loads(content)
        ),
    )


def application_model():
    return SimpleNamespace(
        kinds=(SimpleNamespace(name="ControlledFields", semantic_id="controlled-fields-owner", category="class", complete=True),),
        identities=(SimpleNamespace(owner="controlled-fields-owner", domain="kind", key="controlled-family-contract"),
                    SimpleNamespace(owner="resolve.m1_readings/declared", domain="recipe", key="controlled-reading-recipe")),
    )


def candidate_report():
    body = {
        "candidate_type": "record",
        "contract": "ControlledFields",
        "standing": "candidate",
        "family": "table",
        "record_id": "same-occurrence",
        "interpretation_id": "original-reading",
        "policy_version": "actual-source-policy",
        "computation_dependencies": ["native-group:one"],
        "fields": [
            {"role": "value", "state": "present", "evidence_status": "available", "kind": "literal"}
        ],
        "anchors": [{"precision": "exact"}],
    }
    return {
        "standing": "private_uncalibrated_candidates",
        "inspection_outcome": "produced",
        "source_pin": {"source": "actual-retained-source"},
        "members": (
            {
                "member_id": "original-member",
                "kind_contract": "actual-record-kind",
                "context": {"subject": "original-occurrence"},
                "body": body,
            },
        ),
        "diagnostics_json": json.dumps(
            {
                "model_observations": [{"raw_confidence": 0.25}],
                "reports": [
                    {
                        "diagnostics": [
                            {"group_dependency": "native-group:one", "code": "actual", "group": 0},
                            {"group_dependency": "native-group:one", "code": "actual", "group": 1},
                        ]
                    }
                ],
            }
        ),
    }


def feature():
    algorithm = RecordAlgorithm(features=(FEATURES[0],))
    return FeatureInstance(
        algorithm=algorithm,
        applicability=PolicyApplicability(
            release_id="controlled-release",
            family="table",
            subset="controlled-subset",
            assumptions="independent fixed feature fixture",
        ),
        parameters=LinearParameters(
            feature_signature=algorithm.feature_signature,
            names=("present_fraction",),
            coefficients=(3.0,),
            center=(0.5,),
            scale=(2.0,),
            intercept=-0.25,
        ),
        fit=FitDiagnostics(
            partition="feature_fit",
            frame_digest="a" * 64,
            reference_digest="b" * 64,
            coverage_digest="c" * 64,
            provenance="controlled previously fitted fixture",
            negative_count=2,
            positive_count=2,
            declared_origin_group_count=2,
            conditioning_assumptions="fixed finite fixture",
            converged=True,
            iterations=1,
            standing="fitted",
            reason="actual explicit parameters",
        ),
    )


def policy(instances=()):
    return {
        "version": "reading-feature-policy-2",
        "recipe": RECIPE,
        "subset": "controlled-subset",
        "feature_instances": source_value([DeclaredReadingFeatureInstance(feature=value, family_contract="controlled-family-contract", reading_recipe="controlled-reading-recipe").model_dump(mode="json") for value in instances]),
    }


@lru_cache(maxsize=1)
def compiled_readings():
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    bundle = reading_resolution_inputs(
        SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),))
    )
    model = compile_data_operations(bundle, declarations=(reading_resolution_declarations(),), python_sources=reading_resolution_operation_sources())
    return model


def test_reading_producer_has_closed_factory_and_source_witness():
    model = compiled_readings()
    operation = model.operation("resolve.m1_readings/declared")
    assert operation.capabilities.prepared_factory is not None
    assert len(operation.output_witnesses) == 1
    assert all(value.complete for value in model.implementation_slices)


def test_reading_scoring_retains_real_center_scale_parameters_and_raw_observations():
    upstream = candidate_report()
    product = resolve_reading_values(prepared_ingress(), upstream, policy((feature(),)), model=application_model())
    (event,) = resolved_reading_events(product)
    assert event["outcome"] == "completed"
    assert event["final_event_score"] == pytest.approx(-0.25 + (1.0 - 0.5) / 2.0 * 3.0)
    assert event["feature_instance_digest"] == feature().digest
    assert len(event["feature_diagnostics"]) == 1
    detail = json.loads(product["diagnostics_json"])
    assert detail["producer_diagnostics"]["model_observations"] == [{"raw_confidence": 0.25}]
    assert upstream["members"][0]["body"]["interpretation_id"] == "original-reading"
    assert product["members"][0]["body"]["record_id"] == "same-occurrence"
    assert product["members"][0]["body"]["interpretation_id"] != "original-reading"


@pytest.mark.parametrize("mismatch", ["family", "subset"])
def test_reading_policy_never_applies_outside_exact_applicability(mismatch):
    instance = feature()
    values = instance.applicability.model_dump(mode="json")
    values[mismatch] = "definition" if mismatch == "family" else "other"
    instance = instance.model_copy(update={"applicability": PolicyApplicability(**values)})
    product = resolve_reading_values(prepared_ingress(), candidate_report(), policy((instance,)), model=application_model())
    (event,) = resolved_reading_events(product)
    assert event["outcome"] == "not_run"
    assert event["final_event_score"] is None
    assert event["feature_instance_digest"] is None


def test_reading_resolution_keeps_unavailable_policy_honest_and_refuses_duplicate_instances():
    product = resolve_reading_values(prepared_ingress(), candidate_report(), policy(), model=application_model())
    (event,) = resolved_reading_events(product)
    assert event["outcome"] == "not_run" and event["final_event_score"] is None
    with pytest.raises(ValueError, match="repeats a fitted instance"):
        resolve_reading_values(
            prepared_ingress(), candidate_report(), policy((feature(), feature())), model=application_model()
        )


def test_candidate_consumer_validates_actual_refined_kind_without_dropping_fields():
    from corpus_structure.semantic.data_operation_model import BoundRoleMember, ResolvedRoleBinding
    from corpus_structure.semantic.declared_candidate_products import (
        validate_bound_candidate_report,
    )

    model = compiled_readings()
    kind = next(value for value in model.kinds if value.name == "DdoResolvedReadingReport")
    contract = next(
        value.key
        for value in model.identities
        if value.owner == kind.semantic_id and value.domain == "kind"
    )
    member = BoundRoleMember(
        "actual-product", contract, "subject", "original", b"{}", b"{}", (), b"{}"
    , subject_definition="document", support_references=())
    binding = SimpleNamespace(
        sufficient=True,
        operation="resolve.m1_readings/declared",
        roles=(ResolvedRoleBinding("candidates", "present", (member,)),),
    )
    calls = []
    value = {"reading_policy_digest": "actual-policy", "reading_events": source_value([])}

    def validate(name, content):
        calls.append(name)
        return SimpleNamespace(model_dump=lambda **kwargs: json.loads(content))

    prepared = SimpleNamespace(
        definitions=(SimpleNamespace(iri=kind.semantic_id, name=kind.name),), validate_json=validate
    )
    actual = validate_bound_candidate_report(prepared, model, binding, "candidates", value)
    assert calls == ["DdoResolvedReadingReport"]
    # This controlled ingress returns JSON presentation, not a generated typed
    # model: tuple-valued SourceValue.items crosses JSON as an array.
    assert actual == {
        "reading_policy_digest": "actual-policy",
        "reading_events": {"kind": "array", "items": []},
    }


def test_compatible_release_keeps_original_instance_and_checks_consumed_contract_recipe():
    prepared = prepared_ingress()
    prepared.release_id = "later-compatible-release"
    original = feature()
    product = resolve_reading_values(prepared, candidate_report(), policy((original,)), model=application_model())
    (event,) = resolved_reading_events(product)
    assert event["outcome"] == "completed"
    assert event["feature_instance_digest"] == original.digest
    assert original.applicability.release_id == "controlled-release"
    for index in (0, 1):
        model = application_model()
        model.identities[index].key = "changed-consumed-meaning"
        (event,) = resolved_reading_events(resolve_reading_values(
            prepared, candidate_report(), policy((original,)), model=model,
        ))
        assert event["outcome"] == "not_run"
        assert event["final_event_score"] is None
