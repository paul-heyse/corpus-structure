"""Finite legacy capture-manifest validation while its owning capture path retires."""

from .identity import canonical_bytes


def _boundary():
    from .analysis_policies import analysis_boundary

    return analysis_boundary()


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
