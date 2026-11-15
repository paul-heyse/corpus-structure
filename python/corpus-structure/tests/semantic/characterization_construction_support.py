"""Actual witnessed-rule declarations shared by primary composition controls."""

from pathlib import Path


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

