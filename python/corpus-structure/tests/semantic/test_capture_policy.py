"""The authored capture policy governs executable representation support."""

from dataclasses import replace

import pytest
import yaml

from corpus_structure.semantic.contracts import compile_execution_model, trusted_execution_inputs
from corpus_structure.semantic.types import PreparationError


def test_unknown_capture_storage_cannot_self_attest_support():
    inputs = trusted_execution_inputs()
    catalog = yaml.safe_load(inputs.catalog.content)
    catalog["analysis_profiles"][0]["capture_policy"]["storage"] = "opaque-pickle"
    with pytest.raises(PreparationError, match="implement capture representation"):
        compile_execution_model(
            replace(
                inputs, catalog=replace(inputs.catalog, content=yaml.safe_dump(catalog).encode())
            )
        )


@pytest.mark.parametrize(
    "version,profile,recipe", [("7", "3", "analytical-5"), ("8", "4", "analytical-6")]
)
def test_previous_execution_capture_retains_projection_recipe_and_no_write_capability(
    version, profile, recipe
):
    import json

    from corpus_structure.semantic.analytics import _historical_capture, _projection_recipe
    from corpus_structure.semantic.contracts import require_payload_operation
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.types import RegistryRow

    from .test_analytics import prepared_inputs

    _, _, prepared = prepared_inputs()
    model = compile_execution_model(trusted_execution_inputs())
    historic = json.loads(model.content)
    historic["inputs"]["compiler_version"] = version
    historic["analysis_profiles"][0]["version"] = profile
    if version == "7":
        historic["analysis_profiles"][0].pop("capture_policy")
    payload = canonical_bytes(historic)
    archived = replace(
        prepared,
        execution_model_id=model.model_id,
        registry_rows=(
            *prepared.registry_rows,
            RegistryRow("execution_model", model.model_id, payload),
        ),
    )
    assert _historical_capture(archived)
    assert _projection_recipe(archived, "captured")[1] == recipe
    require_payload_operation(payload, model.model_id, "capture_analytics")
    with pytest.raises(PreparationError, match="read-only"):
        require_payload_operation(payload, model.model_id, "publish")
