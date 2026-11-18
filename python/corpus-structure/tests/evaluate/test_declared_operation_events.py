"""Current event contracts and finite projection; no native authenticity is fabricated."""

import json
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest
from evaluate.test_selected_operation_events import (
    event_value,
    frame,
)
from evaluate.test_selected_operation_events import (
    nominal_profile as nominal_profile,
)
from evaluate.test_selected_operation_events import (
    nominal_schema as nominal_schema,
)
from jsonschema import Draft7Validator

from corpus_structure.evaluate.declared_operation_events import (
    AUTHORIZATION_EFFECT,
    AUTHORIZATION_FACTORY,
    AUTHORIZATION_OPERATION,
    NAMESPACE,
    operation_event_kind_declarations,
    operation_event_operation_sources,
    validate_operation_event_authority_leaf,
)
from corpus_structure.evaluate.operation_fitting import fit_operation_event
from corpus_structure.evaluate.selected_operation_events import (
    DdoOperationEventFit,
    DdoOperationEventFitSpecification,
    SelectedOperationEventFrameSelection,
    operation_event_parameter_value,
)
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.operation_policy import (
    OperationEventAlgorithm,
    score_operation_event,
)


def fitted(profile):
    values = [event_value(profile, 1), event_value(profile, 2, "We call x y.", "x", "y")]
    actual = frame(profile, values, ("supported", "unsupported"))
    selected = SelectedOperationEventFrameSelection(
        selection=actual.question.prediction_selection,
        use_id="pure:frame-use",
        reference=actual.question_reference.model_copy(
            update={"product_id": "pure:protected-frame"}
        ),
        derivation_id="pure:frame-episode",
        frame_digest=actual.fit_digest,
    )
    specification = DdoOperationEventFitSpecification(
        frame=selected, algorithm=OperationEventAlgorithm()
    )
    return actual, DdoOperationEventFit(
        specification=specification, result=fit_operation_event(actual, specification.algorithm)
    )


def test_current_frame_fit_and_issuer_compile_with_existing_component_and_parameter_kinds():
    from semantic.operation_event_feature_fixture import operation_sources as feature_sources

    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.declared_structural_calls import (
        structural_inputs,
        structural_operation_declarations,
    )
    from corpus_structure.semantic.operation_score_sources import (
        operation_score_inputs,
        operation_score_sources,
    )
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.types import SourceArtifact, SourceBundle

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = structural_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    model = compile_data_operations(
        bundle,
        declarations=(
            structural_operation_declarations(),
            *operation_score_inputs(),
            operation_event_kind_declarations(),
        ),
        python_sources=combine_primary_sources(
            operation_event_operation_sources(), operation_score_sources(), feature_sources()
        ),
    )
    operations = [
        model.operation("operation_event." + name) for name in ("frame", "fit", "authorize")
    ]
    assert [operation.profile for operation in operations] == [
        "derivation",
        "derivation",
        "command",
    ]
    assert operations[0].effects == operations[1].effects == ()
    assert operations[2].effects == (AUTHORIZATION_EFFECT,)
    assert [role.name for role in operations[0].roles if role.direction == "input"] == [
        "question",
        "reports",
        "sources",
    ]
    assert [role.name for role in operations[2].roles if role.direction == "output"] == [
        "parameters"
    ]
    assert all(part.complete for part in model.implementation_slices)
    score = model.operation("urn:corpus:operation:score-operation-event")
    assert score.capabilities.prepared_factory is not None
    assert (
        score.capabilities.prepared_factory.entrypoint
        == "corpus_structure.semantic.operation_policy.acquire_operation_event_score_port"
    )
    assert next(role for role in score.roles if role.name == "features").collection == "sequence"
    assert set(json.loads(score.parameters)) == {
        "corpus_id",
        "event",
        "event_version",
        "producer_version",
    }
    features = model.operation("fixture.operation_event_features")
    assert (
        next(role for role in features.roles if role.direction == "output").collection == "sequence"
    )
    kinds = json.loads(operation_event_kind_declarations().content)["kinds"]
    assert {kind["universe"] for kind in kinds} == {"evaluator"}
    assert {
        NAMESPACE + name
        for name in ("DdoOperationEventQuestion", "DdoOperationEventFrame", "DdoOperationEventFit")
    } <= {kind["id"] for kind in kinds}
    for kind in kinds:
        Draft7Validator.check_schema(kind["json_schema"])


def test_finite_parameter_value_keeps_real_algorithm_provenance_and_shared_scoring(nominal_profile):
    actual, fit = fitted(nominal_profile)
    parameters = operation_event_parameter_value(fit)
    assert parameters == fit.result.parameters
    assert parameters.frame_digest == actual.fit_digest
    assert parameters.reference_digest == actual.question.digest
    assert parameters.producer_version == actual.producer_version
    first = score_operation_event(
        parameters,
        actual.observations[0].features,
        corpus_id=actual.corpus_id,
        event=actual.event,
        event_version=actual.event_version,
        producer_version=actual.producer_version,
    )
    assert 0 <= first <= 1
    assert first == pytest.approx(fit.result.predictions[0].fitted_probability)
    assert "judgments" not in parameters.model_dump_json()
    with pytest.raises(ValueError, match="successful fit"):
        operation_event_parameter_value(
            fit.model_copy(update={"result": fit.result.model_copy(update={"status": "failed"})})
        )
    with pytest.raises(ValueError, match="selected current frame"):
        DdoOperationEventFit(
            specification=fit.specification.model_copy(
                update={
                    "frame": fit.specification.frame.model_copy(update={"frame_digest": "0" * 64})
                }
            ),
            result=fit.result,
        )


def test_finite_authority_validator_rejects_copied_kind_factory_effect_and_runtime(nominal_profile):
    _, fit = fitted(nominal_profile)
    parameters = operation_event_parameter_value(fit)
    leaf = SimpleNamespace(
        release_id="release:one",
        runtime_id="runtime:one",
        issuer_operation=AUTHORIZATION_OPERATION,
        product_id="product:parameters",
        kind_contract="kind:parameters",
        recipe="recipe:actual",
    )
    products = {
        leaf.product_id: dict(
            kind_contract=leaf.kind_contract,
            canonical_body=semantic_value(parameters.model_dump(mode="python")),
        )
    }
    kinds = {
        leaf.kind_contract: dict(
            kind="urn:corpus:kind:operation-event:parameters", universe="ordinary"
        )
    }
    definitions = {
        (leaf.release_id, leaf.issuer_operation): dict(
            profile="command",
            recipe=leaf.recipe,
            implementation_revision="implementation-slice:" + "a" * 64,
            support_contract=dict(
                effects=[
                    {
                        **asdict(AUTHORIZATION_EFFECT),
                        "authorization": list(AUTHORIZATION_EFFECT.authorization),
                    }
                ],
                capabilities=dict(
                    preparation="native-publication",
                    forms=["scalar"],
                    prepared_factory=dict(entrypoint=AUTHORIZATION_FACTORY, source_digest="b" * 64),
                ),
            ),
        )
    }
    runtimes = {(leaf.release_id, leaf.runtime_id)}
    assert (
        validate_operation_event_authority_leaf(
            leaf, products=products, kinds=kinds, definitions=definitions, runtimes=runtimes
        )
        is leaf
    )
    for mutation in ("kind", "factory", "effect", "runtime", "source"):
        changed = deepcopy(definitions)
        changed_kinds = deepcopy(kinds)
        cap = changed[leaf.release_id, leaf.issuer_operation]["support_contract"]
        if mutation == "kind":
            changed_kinds[leaf.kind_contract]["universe"] = "evaluator"
        elif mutation == "factory":
            cap["capabilities"]["prepared_factory"]["entrypoint"] = "copied.factory"
        elif mutation == "source":
            cap["capabilities"]["prepared_factory"]["source_digest"] = "copied"
        elif mutation == "effect":
            cap["effects"] = []
        with pytest.raises(ValueError):
            validate_operation_event_authority_leaf(
                leaf,
                products=products,
                kinds=changed_kinds,
                definitions=changed,
                runtimes=set() if mutation == "runtime" else runtimes,
            )


def test_actual_current_cpu_kernels_bind_frame_fit_and_ordered_score_values(nominal_profile):
    """Unadmitted child-value exercise; original source/issuer authenticity is native-only."""
    import inspect

    from corpus_structure.evaluate.declared_operation_events import (
        execute_fit_kernel,
        execute_frame_kernel,
        execute_score_kernel,
    )
    from corpus_structure.evaluate.selected_operation_events import (
        DdoOperationEventFrame,
    )
    from corpus_structure.semantic.data_operation_cpu_basis import (
        CPUInputRole,
        cpu_authority_value,
        cpu_input_basis,
    )
    from corpus_structure.semantic.data_operation_identity import decode_semantic_value
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.identity import canonical_bytes

    for kernel in (execute_frame_kernel, execute_fit_kernel, execute_score_kernel):
        assert inspect.signature(kernel, eval_str=True).return_annotation is dict

    values = [
        event_value(nominal_profile, 1),
        event_value(nominal_profile, 2, "We call x y.", "x", "y"),
    ]
    unadmitted = frame(nominal_profile, values, ("supported", "unsupported"))
    context = SubjectContext(
        unadmitted.question.prediction_selection.project_id,
        "pure:event-context",
        None,
        b"{}",
        subject_definition="fitted-operation-event",
    )

    def role(name, reference, body, position=0):
        selected_context = SubjectContext(
            reference.project_id,
            reference.subject,
            reference.original_source,
            json_bytes(decode_semantic_value(json.loads(reference.analyzed_scope_meaning))),
            subject_definition=reference.subject_definition,
        )
        return CPUInputRole(
            name,
            position,
            1,
            reference.product_id,
            reference.member_id,
            reference.kind_contract,
            selected_context,
            body,
            (),
            producer_output=None,
        )

    roles = [
        role(
            "question", unadmitted.question_reference, unadmitted.question.model_dump(mode="python")
        )
    ]
    for selector, report, source in values:
        roles.append(role("reports", selector.report, report.model_dump(mode="python"), None))
        pin = selector.source
        reference = selector.report.model_copy(
            update=dict(
                product_id=pin.source_product,
                member_id=pin.source_member,
                kind_contract=pin.kind_contract,
            )
        )
        roles.append(role("sources", reference, source.value, None))

    def basis(roles, parameters=None):
        return cpu_input_basis(
            "pure:current-event-recipe",
            context,
            tuple(roles),
            parameters=canonical_bytes(semantic_value(parameters or {})),
            replicate=None,
        )

    input_basis = basis(roles)
    reply = execute_frame_kernel(
        input_basis, "", prepared=nominal_profile.prepared, check_active=lambda: None
    )
    actual = DdoOperationEventFrame.model_validate_json(
        json_bytes(cpu_authority_value(canonical_bytes(reply), expected_basis=input_basis))
    )
    assert actual.frame == unadmitted
    selected = SelectedOperationEventFrameSelection(
        selection=unadmitted.question.prediction_selection,
        use_id="pure:unadmitted-frame-use",
        reference=unadmitted.question_reference.model_copy(
            update={"product_id": "pure:current-frame"}
        ),
        derivation_id="pure:unadmitted-frame-episode",
        frame_digest=actual.frame_digest,
    )
    specification = DdoOperationEventFitSpecification(
        frame=selected, algorithm=OperationEventAlgorithm()
    )
    fit_basis = basis(
        (
            role("frame", selected.reference, actual.model_dump(mode="python")),
            role(
                "specification",
                selected.reference.model_copy(update={"product_id": "pure:spec"}),
                specification.model_dump(mode="python"),
            ),
        )
    )
    fit_reply = execute_fit_kernel(fit_basis, check_active=lambda: None)
    fit = DdoOperationEventFit.model_validate_json(
        json_bytes(cpu_authority_value(canonical_bytes(fit_reply), expected_basis=fit_basis))
    )
    assert fit.result.status == "fitted"
    parameters = operation_event_parameter_value(fit)
    score_roles = [
        role(
            "parameters",
            selected.reference.model_copy(update={"product_id": "pure:params"}),
            parameters.model_dump(mode="python"),
        )
    ]
    score_roles.extend(
        role(
            "features",
            selected.reference.model_copy(update={"product_id": "pure:feature:" + str(position)}),
            value,
            position,
        )
        for position, value in enumerate(actual.frame.observations[0].features)
    )
    score_basis = basis(
        score_roles,
        dict(
            corpus_id=parameters.corpus_id,
            event=parameters.event,
            event_version=parameters.event_version,
            producer_version=parameters.producer_version,
        ),
    )
    score_reply = execute_score_kernel(score_basis, check_active=lambda: None)
    score = cpu_authority_value(canonical_bytes(score_reply), expected_basis=score_basis)
    assert score == pytest.approx(fit.result.predictions[0].fitted_probability)
