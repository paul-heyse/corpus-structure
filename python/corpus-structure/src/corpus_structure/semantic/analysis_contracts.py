"""Retiring execution-catalog admission and physical preparation helpers.

Current mathematical context preparation is owned by :mod:`math_context`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Never

from .identity import canonical_bytes
from .types import Diagnostic, PreparationError


def _fail(code: str, location: str, message: str) -> Never:
    raise PreparationError((Diagnostic(code, location, message),))


if TYPE_CHECKING:
    from .contracts import ExecutionModelProducts, InputOwnershipContract
    from .types import PreparedRelease

# Independent implementation support: declarations cannot change resource semantics
# without changing the producer/consumer that implements this bounded profile.
_OWNERSHIP_SUPPORT = {
    "comparison": (
        "CandidateInput",
        "evaluate",
        "scope",
        ("release", "snapshot", "universe", "policy"),
    ),
    "publication": (
        "AppendPublication",
        "publish",
        "operation",
        ("release", "snapshot", "content"),
    ),
    "capture": (
        "CapturedPacket",
        "capture_analytics",
        "detached",
        ("release", "snapshot", "projection", "content"),
    ),
    "invocation": (
        "WorkPacket",
        "schedule",
        "operation",
        ("release", "source", "configuration", "policy"),
    ),
    "read": ("Archive", "reload", "scope", ("release", "archive", "boundary")),
}


def validate_analysis_profiles(model: ExecutionModelProducts) -> None:
    """Validate computational policy and the retiring catalog's own legacy references."""
    from .analysis_policies import validate_math_policy, validate_preparation_policies

    ids = set()
    for profile in model.analysis_profiles:
        location = "analysis_profiles/" + profile.id
        if profile.id in ids:
            _fail("unsupported_analysis_profile", location, "analysis profile ids must be distinct")
        ids.add(profile.id)
        validate_math_policy(profile)
        from .contracts import InvocationPolicyDefinition

        if profile.invocation_policy != InvocationPolicyDefinition(
            "invocation-logical-1",
            "invocation-packet-1",
            ("release", "source", "configuration", "policy", "unit"),
            "absent",
            "required",
        ):
            _fail(
                "unsupported_invocation_policy",
                location,
                "implement changed legacy invocation policy before admission",
            )
        validate_preparation_policies(
            profile.text_policy,
            profile.alignment_policy,
            profile.placement_policy,
            profile.capture_policy,
        )
        if profile.shared_consumers != ("normalize.formula", "extract.math"):
            _fail("unsupported_analysis_recipe", location, "legacy sharing contract differs")
        owners = {item.id: item for item in profile.ownership}
        if len(owners) != len(profile.ownership) or set(owners) != set(_OWNERSHIP_SUPPORT):
            _fail(
                "analysis_ownership",
                location,
                "declare exactly the implemented owned preparation families",
            )
        for owner in profile.ownership:
            if (
                owner.concept,
                owner.operation,
                owner.lifetime,
                owner.dependencies,
            ) != _OWNERSHIP_SUPPORT[owner.id]:
                _fail(
                    "unsupported_analysis_ownership",
                    location + "/" + owner.id,
                    "implement changed producer/consumer ownership before admission",
                )
            if owner.concept not in {c.id for c in model.concepts} or owner.operation not in {
                o.id for o in model.operations
            }:
                _fail(
                    "analysis_ownership_reference",
                    location + "/" + owner.id,
                    "unknown concept or operation",
                )


def _legacy_profile(
    prepared: PreparedRelease, *, require_current_implementations: bool = True
):
    import json

    from .contracts import (
        EXECUTION_COMPILER_VERSION,
        bound_execution_model,
        execution_payload,
    )

    if prepared.execution_model_id is None:
        _fail(
            "missing_execution_model",
            prepared.release_id,
            "analysis requires a composed execution binding",
        )
    else:
        model = bound_execution_model(prepared)
        payload = execution_payload(prepared)
        if (
            payload is None
            or json.loads(payload).get("inputs", {}).get("compiler_version")
            != EXECUTION_COMPILER_VERSION
        ):
            _fail(
                "unsupported_analysis_abi",
                model.model_id,
                f"analysis preparation requires execution compiler {EXECUTION_COMPILER_VERSION}; "
                "historical archives are read-only",
            )
    if len(model.analysis_profiles) != 1 or model.analysis_profiles[0].version != "6":
        _fail(
            "missing_analysis_profile",
            model.model_id,
            "prepare a release with an admitted analysis profile; "
            "historical archives are read-only",
        )
    if (
        require_current_implementations
        and model.implementation_digests != _semantic_implementation_digests()
    ):
        _fail(
            "unsupported_analysis_implementation",
            model.model_id,
            "bind the admitted semantic determinant bytes to this runtime before analysis",
        )
    return model, model.analysis_profiles[0]


def _semantic_implementation_digests():
    from .contracts import current_implementation

    return current_implementation().semantic_digests


def _boundary():
    from .analysis_policies import analysis_boundary

    return analysis_boundary()


@dataclass(frozen=True)
class OwnedAnalysisInput:
    release_id: str
    model_id: str
    family: str
    lifetime: str
    dependencies: tuple[tuple[str, bytes], ...]


@dataclass(frozen=True)
class BoundAnalysisFamily:
    release_id: str
    model_id: str
    contract: InputOwnershipContract

    def prepare(self, **dependencies: Any) -> OwnedAnalysisInput:
        if set(dependencies) != set(self.contract.dependencies) or any(
            v is None for v in dependencies.values()
        ):
            _fail(
                "analysis_input_dependencies",
                self.contract.id,
                "supply exactly " + ", ".join(self.contract.dependencies),
            )
        if dependencies.get("release") != self.release_id:
            _fail("analysis_input_release", self.contract.id, "input belongs to another release")
        return OwnedAnalysisInput(
            self.release_id,
            self.model_id,
            self.contract.id,
            self.contract.lifetime,
            tuple(
                (name, canonical_bytes(dependencies[name])) for name in self.contract.dependencies
            ),
        )


def bind_analysis_family(prepared: PreparedRelease, family: str) -> BoundAnalysisFamily:
    # Snapshot reads interpret the archived release's own declarations. A new
    # grammar/report schema must not disable an unchanged read contract. Actual
    # numerical/preparation consumers still require current semantic assets.
    model, profile = _legacy_profile(prepared, require_current_implementations=family != "read")
    contract = next((item for item in profile.ownership if item.id == family), None)
    if contract is None:
        _fail("analysis_input_family", family, "use an admitted preparation family")
    if family == "read" and (
        contract.concept, contract.operation, contract.lifetime, contract.dependencies
    ) != _OWNERSHIP_SUPPORT["read"]:
        _fail("analysis_input_family", family, "archived read ownership contract is unsupported")
    model.require_operation(contract.operation)
    return BoundAnalysisFamily(prepared.release_id, model.model_id, contract)



def prepare_text_policy(prepared: PreparedRelease | None = None):
    if prepared is None:
        from .analysis_policies import acquire_analysis_policies

        return acquire_analysis_policies().text
    _, profile = _legacy_profile(prepared)
    assert profile.text_policy is not None
    return profile.text_policy


def prepare_alignment_policy(prepared: PreparedRelease | None = None):
    if prepared is None:
        from .analysis_policies import acquire_analysis_policies

        return acquire_analysis_policies().alignment
    _, profile = _legacy_profile(prepared)
    assert profile.alignment_policy is not None
    return profile.alignment_policy


def prepare_placement_policy(prepared: PreparedRelease | None = None):
    from corpus_structure.methods.llm.cascade import PlacementPolicy

    if prepared is None:
        from .analysis_policies import acquire_analysis_policies

        policy = acquire_analysis_policies().placement
    else:
        _, profile = _legacy_profile(prepared)
        policy = profile.placement_policy
    assert policy is not None
    return PlacementPolicy(
        recipe=policy.recipe,
        candidate_limit=policy.candidate_limit,
        token_cutoff=policy.token_cutoff,
        token_pad=policy.token_pad,
        char_cutoff=policy.char_cutoff,
        char_pad=float(policy.char_pad),
        char_errors=float(policy.char_errors),
        pick_cutoff=policy.pick_cutoff,
        regex_timeout=float(policy.regex_timeout),
        refine_timeout=float(policy.refine_timeout),
    )


def _supported_capture_policy():
    """Finite reader support is independent of current release compilation/admission."""
    from .analysis_policies import CapturePolicyDefinition

    return CapturePolicyDefinition(
        ("resident", "spooled"),
        "semantic-capture-1",
        "canonical-rows-1",
        "primary-key-c",
        "full-spine",
        "parquet",
    )


def prepare_capture_policy(prepared: PreparedRelease | None = None):
    if prepared is None:
        from .analysis_policies import acquire_analysis_policies

        return acquire_analysis_policies().capture
    _, profile = _legacy_profile(prepared)
    assert profile.capture_policy is not None
    return profile.capture_policy


def validate_capture_manifest(manifest):
    """Use the trusted LinkML boundary; physical completeness is checked by its owner."""
    policy = _supported_capture_policy()
    normalized = (
        _boundary()
        .validate_json("CaptureManifest", canonical_bytes(dict(manifest)))
        .model_dump(mode="json")
    )
    if (
        normalized["format"] != policy.manifest
        or normalized["digest_recipe"] != policy.digest
        or normalized["complete"] is not True
    ):
        raise ValueError("unsupported or incomplete captured manifest")
    return normalized
