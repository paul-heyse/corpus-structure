"""Actual released primary-layer contract inputs shared by retained review controls."""

import base64
from pathlib import Path

import pytest

from corpus_structure.semantic.characterization import attachment_policies


@pytest.fixture(scope="module")
def prepared():
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.characterization import characterization_inputs

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    return prepare_release(characterization_inputs(bundle))


def construction_release_inputs():
    """A real added witnessed-rule declaration, not a relabelled release identifier."""
    import yaml

    from corpus_structure.semantic import SourceArtifact, SourceBundle
    from corpus_structure.semantic.characterization import characterization_inputs

    model_root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    model = yaml.safe_load((model_root / "characterization.yaml").read_bytes())
    model["classes"]["ReplayConstructionBasis"] = {
        "is_a": "CharacterizationConstructionBasis",
        "attributes": {
            "rule_id": {"required": True, "equals_string": "replay:body-v1"},
            "premises": {
                "range": "string",
                "multivalued": True,
                "required": True,
                "minimum_cardinality": 1,
            },
        },
    }
    return characterization_inputs(
        SourceBundle("core", (SourceArtifact("core", (model_root / "core.yaml").read_bytes()),)),
        model_content=yaml.safe_dump(model).encode(),
    )


def contract_data(prepared, sources):
    policies = attachment_policies(prepared)
    names = {"AnnotationLayer", "EnrichedDocumentView"} | {
        row["class_name"] for row in policies.values()
    }
    names.update(
        rule["class_name"]
        for policy in policies.values()
        for rule in policy.get("rules", {}).values()
    )
    return dict(
        release_id=prepared.release_id,
        manifest_base64=base64.b64encode(prepared.manifest).decode(),
        schemas={name: prepared.json_schema(name) for name in names},
        attachment_policies=policies,
        sources={
            source.name: base64.b64encode(source.content).decode() for source in sources.sources
        },
        dependencies={},
    )
