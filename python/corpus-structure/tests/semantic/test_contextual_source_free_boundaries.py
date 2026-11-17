"""Source-free contextual targets retain explicit null without weakening source pins."""

from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.contextual_operations import contextual_inputs
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from semantic.test_contextual_target_vectors import population


@pytest.fixture(scope="module")
def contextual_boundaries():
    from corpus_structure.semantic import contextual_operations

    core = Path(contextual_operations.__file__).parents[1] / "model/semantic/core.yaml"
    return prepare_release(
        contextual_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )


def test_curated_population_boundary_preserves_explicit_source_free_context(contextual_boundaries):
    body = population(("one", "two"))
    value = contextual_boundaries.validate_json("DdoContextualTargetPopulation", json_bytes(body))
    checked = value.model_dump(mode="python", exclude_unset=True)
    for packet in checked["members"]:
        assert (
            "original_source" in packet["context"] and packet["context"]["original_source"] is None
        )
        assert "original_source" in packet["body"] and packet["body"]["original_source"] is None
    for where in ("context", "body"):
        missing = deepcopy(body)
        del missing["members"][0][where]["original_source"]
        with pytest.raises(ValidationError):
            contextual_boundaries.validate_json(
                "DdoContextualTargetPopulation", json_bytes(missing)
            )
        invalid = deepcopy(body)
        invalid["members"][0][where]["original_source"] = 7
        with pytest.raises(ValidationError):
            contextual_boundaries.validate_json(
                "DdoContextualTargetPopulation", json_bytes(invalid)
            )


def test_nullable_scalar_carrier_address_keeps_required_original_source(contextual_boundaries):
    carrier: dict[str, object] = dict(
        product_id="product:occurrence",
        member_id=None,
        kind_contract="kind:occurrence",
        project_id="project:A",
        subject_definition="original-source-view",
        subject="source:A",
        original_source="document:A",
        analyzed_scope_meaning="{}",
        contribution_id="source-contribution:" + "a" * 64,
    )
    value = contextual_boundaries.validate_json("DdoContextualCarrierInput", json_bytes(carrier))
    assert value.model_dump(mode="python", exclude_unset=True) == carrier
    carrier["original_source"] = None
    with pytest.raises(ValidationError):
        contextual_boundaries.validate_json("DdoContextualCarrierInput", json_bytes(carrier))
    assert not contextual_boundaries.index.properties_by_class["DdoContextualPrimaryInput"][
        "original_source"
    ].nullable
