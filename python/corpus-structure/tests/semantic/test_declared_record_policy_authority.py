"""Pure policy application controls; possession of values grants no native authority."""

import pytest
from typing import Any
from pydantic import ValidationError

from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
from corpus_structure.semantic.record_policy import RecordAcceptanceInstance, score_record
from corpus_structure.semantic.record_policy_authority import (
    DdoRecordPolicyApplicability, DdoRecordPolicyAuthorization,
    check_record_policy_application, policy_authorization_value, record_policy_kind_declarations,
)
from semantic.record_policy_support import fitted, calibrated, vector


def _apply(authorization, arguments: dict[str, Any], **changes: Any):
    values: dict[str, Any] = dict(arguments)
    values.update(changes)
    return check_record_policy_application(authorization, **values)


@pytest.fixture(scope="module")
def application():
    source = DeclaredStructuralSource(
        source='["product:source",null]', subject="native:selected",
        subject_definition="selected-native-source", document="original:one",
        projection_digest="a" * 64, section_pointer="#/groups/0", membership="descendants",
        project_id="project:one", original_source="original:one", analyzed_scope_meaning='["null"]',
        source_product="product:source", kind_contract="kind:source",
    )
    feature = fitted()
    instance = RecordAcceptanceInstance(
        feature=feature, calibration=calibrated(feature), threshold=0.5,
        threshold_procedure="fixed-threshold-1", conditioning_assumptions="explicit source population",
    )
    authorization = policy_authorization_value(
        instance, family_contract="TableReading", judgment_basis_digest="b" * 64,
        reading_recipe="recipe:readings",
        applicability=DdoRecordPolicyApplicability(project_id=source.project_id, sources=(source,)),
    )
    # This new production reading is deliberately absent from fit/calibration samples.
    features = vector(99, 3)
    score = score_record(feature, features, subset="native-tables")
    assert instance.calibration is not None
    event = dict(
        record_id=features.record_id, interpretation_id=features.interpretation_id,
        feature_instance_digest=feature.digest, feature_input_digest=features.input_digest,
        event_procedure=instance.calibration.event_procedure, outcome="completed",
        final_event_score=score.compatibility_potential,
    )
    arguments: dict[str, Any] = dict(
        source=source, source_release_id="release:test", family="table", family_contract="TableReading",
        reading_recipe="recipe:readings",
        record_id=features.record_id, interpretation_id=features.interpretation_id,
        features=features, events=(event,),
    )
    return instance, authorization, arguments


def test_public_policy_exposes_only_permitted_parameters(application):
    instance, authorization, _ = application
    body = authorization.model_dump(mode="json")
    assert body["policy_instance_digest"] == instance.digest
    assert body["parameters"]["names"] == ["present_fraction"]
    assert body["threshold"] == 0.5
    assert body["event_procedure"] == "uncoupled-whole-reading-1"
    assert body["source_release_id"] == "release:test"
    encoded = authorization.model_dump_json()
    for forbidden in ('"fit"', '"correct"', '"origin_group"', '"provenance"', '"authorized"', '"eligible"'):
        assert forbidden not in encoded
    with pytest.raises(ValidationError):
        DdoRecordPolicyAuthorization.model_validate({**body, "authorized": True})
    with pytest.raises(ValueError, match="final-event calibration"):
        policy_authorization_value(
            instance.model_copy(update={"calibration": None}), family_contract="TableReading",
            judgment_basis_digest="b" * 64, applicability=authorization.applicability,
            reading_recipe="recipe:readings",
        )


def test_new_record_checks_actual_population_and_final_event(application):
    _, authorization, arguments = application
    assert _apply(authorization, arguments) > 0.5
    with pytest.raises(ValueError, match="checked source population"):
        _apply(authorization, arguments, source=arguments["source"].model_copy(update={"subject": "another-source"}))
    with pytest.raises(ValueError, match="family interpretation"):
        _apply(authorization, arguments, family_contract="OtherReading")
    with pytest.raises(ValueError, match="family interpretation"):
        _apply(authorization, arguments, reading_recipe="recipe:changed")
    with pytest.raises(ValueError, match="unique sealed final event"):
        _apply(authorization, arguments, events=arguments["events"] * 2)


@pytest.mark.parametrize("changes", [
    {"outcome": "not_run"}, {"feature_instance_digest": "c" * 64},
    {"feature_input_digest": "c" * 64}, {"event_procedure": "other-procedure"},
    {"final_event_score": float("inf")}, {"final_event_score": True},
    {"final_event_score": -100.0},
])
def test_changed_or_invented_event_refuses(application, changes):
    _, authorization, arguments = application
    event = {**arguments["events"][0], **changes}
    with pytest.raises(ValueError):
        _apply(authorization, arguments, events=(event,))


def test_source_population_refuses_duplicates_and_cross_project(application):
    _, authorization, arguments = application
    source = arguments["source"]
    for sources in ((source, source), (source.model_copy(update={"project_id": "another"}),)):
        with pytest.raises(ValueError, match="unique sources"):
            DdoRecordPolicyApplicability(project_id=source.project_id, sources=sources)
    assert authorization.applicability.sources == (source,)


def test_public_policy_has_one_closed_nominal_owner():
    import json
    from jsonschema import Draft7Validator
    kinds = json.loads(record_policy_kind_declarations().content)["kinds"]
    root = next(row for row in kinds if row["name"] == "DdoRecordPolicyAuthorization")
    Draft7Validator.check_schema(root["json_schema"])
    assert root["json_schema"]["additionalProperties"] is False
    assert root["json_schema"]["properties"]["threshold"]["maximum"] == 1


def test_policy_issuer_has_closed_current_command_and_protected_input():
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.record_policy_authority import (
        AUTHORIZATION_EFFECT, AUTHORIZATION_FACTORY, AUTHORIZATION_KIND,
        protected_record_policy_kind_declarations, record_policy_authorization_sources,
    )

    model = compile_data_operations(
        declarations=(record_policy_kind_declarations(), protected_record_policy_kind_declarations()),
        python_sources=record_policy_authorization_sources(),
    )
    operation = model.operation("record_policy.authorize")
    assert operation.effects == (AUTHORIZATION_EFFECT,)
    assert operation.capabilities.prepared_factory is not None
    assert operation.capabilities.prepared_factory.entrypoint == AUTHORIZATION_FACTORY
    assert operation.profile == "command"
    assert operation.roles[1].kind == AUTHORIZATION_KIND
    protected = next(kind for kind in model.kinds if kind.semantic_id == operation.roles[0].kind)
    import json
    assert json.loads(protected.facts)["universe"] == "evaluator"
    assert all(slice.complete for slice in model.implementation_slices)


def test_compatible_release_change_preserves_original_policy_lineage(application):
    _, authorization, arguments = application
    features = arguments["features"].model_copy(update={"release_id": "release:compatible"})
    assert _apply(authorization, arguments, source_release_id="release:compatible", features=features) > 0.5
    assert authorization.source_release_id == "release:test"


def test_private_parameter_custody_preserves_exact_canonical_bytes(application):
    from corpus_structure.semantic.record_policy_authority import DdoFittedRecordPolicy, execute_authorization_profile

    instance, authorization, _ = application
    basis = DdoFittedRecordPolicy.from_instance(
        instance, family_contract="TableReading", reading_recipe="recipe:readings",
        judgment_basis_digest="b" * 64, applicability=authorization.applicability,
    )
    assert execute_authorization_profile(None, basis.model_dump(mode="json")) == authorization.model_dump(mode="json")
    body = basis.model_dump(mode="python")
    body["feature_canonical_json"] += " "
    with pytest.raises(ValueError, match="canonical bytes"):
        DdoFittedRecordPolicy.model_validate(body)
