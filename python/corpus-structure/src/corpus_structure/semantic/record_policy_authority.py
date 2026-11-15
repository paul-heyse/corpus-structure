"""Public policy parameters and exact applicability; native issuance grants authority.

These immutable values deliberately cannot authenticate themselves. Protected fitting
and grading retain their complete evidence; ordinary production receives only the
allowlisted instance conclusion and checks each new reading separately.
"""

from __future__ import annotations

import math
from typing import Annotated, Literal, Self

from pydantic import Field, FiniteFloat, model_validator
from scipy.special import expit

from .data_operation_model import EffectContract
from .declared_structural_references import DeclaredStructuralSource
from .identity import canonical_bytes
from .record_policy import (
    Digest, Family, FrozenContract, LinearParameters, Nonempty, ReadingNumericalPolicy,
    RecordAcceptanceInstance, RecordAlgorithm, RecordFeatures, READING_NUMERICS, reading_potential,
)

NAMESPACE = "https://corpus-structure.dev/semantic/data-operation-record-policy/"
AUTHORIZATION_KIND = NAMESPACE + "DdoRecordPolicyAuthorization"
AUTHORIZATION_OPERATION = "record_policy.authorize"
AUTHORIZATION_FACTORY = "corpus_structure.methods.record_policy.RecordPolicyAuthorization.acquire_port"
AUTHORIZATION_EFFECT = EffectContract(
    "native-evaluator-policy-authorization", ("native-purpose:evaluator", "exact-protected-policy-basis"),
    "request-generation/exact-instance", "native-publication-receipt",
)


class DdoRecordPolicyApplicability(FrozenContract):
    """A frozen source population for application, independent of fitting samples."""

    project_id: Nonempty
    sources: Annotated[tuple[DeclaredStructuralSource, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def exact_population(self) -> Self:
        addresses = [canonical_bytes(source.model_dump(mode="json")) for source in self.sources]
        if len(set(addresses)) != len(addresses) or any(
            source.project_id != self.project_id for source in self.sources
        ):
            raise ValueError("policy applicability requires unique sources in its exact project")
        return self

    def require_source(self, source: DeclaredStructuralSource) -> None:
        if source.project_id != self.project_id or source not in self.sources:
            raise ValueError("reading is outside the policy's checked source population")


class DdoRecordPolicyAuthorization(FrozenContract):
    version: Literal["record-policy-authorization-1"] = "record-policy-authorization-1"
    policy_instance_digest: Digest
    feature_instance_digest: Digest
    calibration_digest: Digest
    algorithm: RecordAlgorithm
    parameters: LinearParameters
    family: Family
    family_contract: Nonempty
    source_release_id: Nonempty
    subset: Nonempty
    event_procedure: Nonempty
    threshold_procedure: Nonempty
    threshold: Annotated[FiniteFloat, Field(gt=0, le=1)]
    calibration_slope: FiniteFloat
    calibration_intercept: FiniteFloat
    numerical_policy: ReadingNumericalPolicy
    judgment_basis_digest: Digest
    applicability: DdoRecordPolicyApplicability

    @model_validator(mode="after")
    def compatible_parameters(self) -> Self:
        if (
            self.parameters.feature_signature != self.algorithm.feature_signature
            or self.parameters.names != tuple(feature.name for feature in self.algorithm.features)
        ):
            raise ValueError("authorized parameters differ from their exact algorithm feature order")
        return self


def policy_authorization_value(
    instance: RecordAcceptanceInstance, *, family_contract: str,
    judgment_basis_digest: str, applicability: DdoRecordPolicyApplicability,
) -> DdoRecordPolicyAuthorization:
    """Produce the permitted value only; an actual native issuer must authenticate it."""
    calibration = instance.calibration
    if calibration is None:
        raise ValueError("policy authorization requires fitted final-event calibration")
    feature = instance.feature
    return DdoRecordPolicyAuthorization(
        policy_instance_digest=instance.digest, feature_instance_digest=feature.digest,
        calibration_digest=calibration.digest, algorithm=feature.algorithm,
        parameters=feature.parameters, family=feature.applicability.family,
        family_contract=family_contract, source_release_id=feature.applicability.release_id,
        subset=feature.applicability.subset, event_procedure=calibration.event_procedure,
        threshold_procedure=instance.threshold_procedure, threshold=instance.threshold,
        calibration_slope=calibration.slope, calibration_intercept=calibration.intercept,
        numerical_policy=READING_NUMERICS, judgment_basis_digest=judgment_basis_digest,
        applicability=applicability,
    )


def check_record_policy_application(
    authorization: DdoRecordPolicyAuthorization, *, source: DeclaredStructuralSource,
    source_release_id: str, family: str, family_contract: str,
    record_id: str, interpretation_id: str, features: RecordFeatures,
    events: tuple[dict, ...],
) -> float:
    """Check one completed sealed event against exact public parameters.

    The caller authenticates the issuer, source and events through native selected
    product custody. This function grants no authority from possession of their bytes.
    It does not confuse a calibration sample with a production application population.
    """
    authorization.numerical_policy.require_runtime()
    authorization.applicability.require_source(source)
    if (source_release_id, family, family_contract) != (
        authorization.source_release_id, authorization.family, authorization.family_contract,
    ):
        raise ValueError("reading family interpretation differs from authorized applicability")
    if (
        (features.record_id, features.interpretation_id, features.release_id, features.family)
        != (record_id, interpretation_id, source_release_id, family)
        or features.feature_signature != authorization.parameters.feature_signature
        or features.names != authorization.parameters.names
        or any(value is None for value in features.values)
    ):
        raise ValueError("reading features differ from exact application or ordered parameters")
    matches = tuple(event for event in events if (
        event.get("record_id"), event.get("interpretation_id")
    ) == (record_id, interpretation_id))
    if len(matches) != 1:
        raise ValueError("reading requires one unique sealed final event")
    event = matches[0]
    if (
        event.get("outcome") != "completed"
        or event.get("feature_instance_digest") != authorization.feature_instance_digest
        or event.get("feature_input_digest") != features.input_digest
        or event.get("event_procedure") != authorization.event_procedure
    ):
        raise ValueError("sealed final event differs from exact authorized instance or input")
    score = event.get("final_event_score")
    if type(score) not in (int, float) or not math.isfinite(score):
        raise ValueError("sealed final event requires a finite numeric score")
    expected_score = reading_potential(
        authorization.parameters, tuple(value for value in features.values if value is not None),
    )
    if score != expected_score:
        raise ValueError("sealed final score differs from exact authorized predictor and reading features")
    calibrated = authorization.calibration_slope * score + authorization.calibration_intercept
    if not math.isfinite(calibrated):
        raise ValueError("final-event calibration produced a nonfinite argument")
    probability = float(expit(calibrated))
    if not math.isfinite(probability) or probability < authorization.threshold:
        raise ValueError("final-event probability is below its exact authorized threshold")
    return probability


def record_policy_kind_declarations():
    """One closed nominal owner for the public contract and its nested values."""
    from .data_operation_model import MODEL_VERSION
    from .nominal_schema_kinds import nominal_schema_kinds
    from .types import SourceArtifact

    return SourceArtifact("record-policy/public-kinds.json", canonical_bytes({
        "version": MODEL_VERSION,
        "kinds": nominal_schema_kinds(
            DdoRecordPolicyAuthorization.model_json_schema(), namespace=NAMESPACE,
            root_name="DdoRecordPolicyAuthorization",
        ),
    }))


class DdoFittedRecordPolicy(FrozenContract):
    """Protected fitted conclusion; only its real producing support can authorize use."""

    version: Literal["fitted-record-policy-1"] = "fitted-record-policy-1"
    instance: RecordAcceptanceInstance
    family_contract: Nonempty
    judgment_basis_digest: Digest
    applicability: DdoRecordPolicyApplicability


def protected_record_policy_kind_declarations():
    from .data_operation_model import MODEL_VERSION
    from .nominal_schema_kinds import nominal_schema_kinds
    from .types import SourceArtifact

    return SourceArtifact("record-policy/protected-kinds.json", canonical_bytes({
        "version": MODEL_VERSION,
        "kinds": [dict(row, universe="evaluator") for row in nominal_schema_kinds(
            DdoFittedRecordPolicy.model_json_schema(), namespace=NAMESPACE + "protected/",
            root_name="DdoFittedRecordPolicy",
        )],
    }))


def execute_authorization_profile(receiver, basis):
    # The original typed method supplies callable correspondence. Its acquired
    # physical plan performs preparation; direct invocation grants no effect.
    checked = DdoFittedRecordPolicy.model_validate_json(canonical_bytes(basis))
    return policy_authorization_value(
        checked.instance, family_contract=checked.family_contract,
        judgment_basis_digest=checked.judgment_basis_digest, applicability=checked.applicability,
    ).model_dump(mode="json")


def record_policy_authorization_assets():
    from pathlib import Path
    from .types import SourceArtifact
    from .python_module_projection import admitted_operation_module_meaning

    root = Path(__file__).parents[1]
    paths = (
        "methods/record_policy.py", "semantic/record_policy_authority.py",
        "semantic/record_policy.py", "semantic/declared_structural_references.py",
        "semantic/data_operation_effects.py", "semantic/data_operation_prepared_call.py",
    )
    return SourceArtifact("record-policy/authorization-assets", canonical_bytes({
        "version": "record-policy-authorization-preparation-1",
        "files": [(path, admitted_operation_module_meaning((root / path).read_bytes()).hex()) for path in paths],
    }))


def record_policy_authorization_sources():
    from pathlib import Path
    from .python_operation_sources import PythonSource, PythonSourceCollection

    root = Path(__file__).parents[1]
    paths = (
        "methods/record_policy.py", "semantic/record_policy_authority.py",
        "semantic/data_operation_effects.py", "semantic/data_operation_prepared_call.py",
    )
    return PythonSourceCollection(tuple(PythonSource(
        "corpus_structure." + path.removesuffix(".py").replace("/", "."),
        (root / path).read_bytes(), str((root / path).resolve()),
    ) for path in paths), boundary_contracts=(record_policy_authorization_assets(),))


class AuthorizationInvocationPlan:
    def plan(self, arguments, *, binding, check_active, execution_owner):
        from .data_operation_prepared_call import PreparedCallResult

        yield from ()
        check_active()
        if binding is None or binding.subject_context is None:
            raise ValueError("policy authorization requires an exact acquired project context")
        checked = DdoFittedRecordPolicy.model_validate_json(canonical_bytes(arguments.arguments["basis"]))
        if checked.applicability.project_id != binding.subject_context.project_id:
            raise ValueError("policy applicability belongs to another project")
        value = policy_authorization_value(
            checked.instance, family_contract=checked.family_contract,
            judgment_basis_digest=checked.judgment_basis_digest, applicability=checked.applicability,
        )
        # This is bounded DTO projection. No fitting, inference or native effect
        # occurs in planning; common native completion authenticates issuance.
        return PreparedCallResult(value.model_dump(mode="json"))


def acquire_authorization_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.record_policy import RecordPolicyAuthorization
    from .data_operation_effects import PreparedNativePublicationEffect
    from .data_operation_prepared_call import PreparedOriginalCallPort
    from .data_operation_ports import PortRefusal

    selected = model.operation(operation)
    if (
        selected.semantic_id != AUTHORIZATION_OPERATION or selected.effects != (AUTHORIZATION_EFFECT,)
        or selected.capabilities.prepared_factory is None
        or selected.capabilities.prepared_factory.entrypoint != AUTHORIZATION_FACTORY
    ):
        raise PortRefusal("policy issuer requires its exact command/effect/factory")
    receiver = RecordPolicyAuthorization()
    plan = AuthorizationInvocationPlan()
    wrapped = PreparedOriginalCallPort(
        identity, model, selected, sources, custody, receiver.run, plan.plan,
        "corpus_structure.semantic.record_policy_authority.AuthorizationInvocationPlan.plan",
        authorize, (record_policy_authorization_assets(),), record_policy_authorization_sources(),
    )
    return PreparedNativePublicationEffect(wrapped)
