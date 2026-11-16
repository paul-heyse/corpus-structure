"""An explicitly selected qualification subtype preserves its actual semantic key policy."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from corpus_structure.semantic import (
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.identity import canonical_bytes


def inputs():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    schema = {
        "id": "https://example.org/qualified",
        "name": "qualified",
        "imports": ["semantic_core"],
        "prefixes": {"ex": "https://example.org/", "cs": "https://corpus-structure.dev/semantic/"},
        "default_prefix": "ex",
        "classes": {
            "Thing": {"is_a": "Entity", "attributes": {"label": {"range": "string"}}},
            "ReportQualification": {
                "is_a": "Qualification",
                "attributes": {
                    "reporter": {"range": "string", "annotations": {"cs:key_role": "provenance"}},
                    "channel": {"range": "string", "annotations": {"cs:case": "casefold"}},
                },
            },
            "DomainQualification": {
                "is_a": "ReportQualification",
                "attributes": {"hedge": {"range": "string"}},
            },
            "Unrelated": {"attributes": {"modality": {}, "polarity": {"range": "boolean"}}},
        },
    }
    return SourceBundle(
        "qualified",
        (
            SourceArtifact("qualified", yaml.safe_dump(schema).encode()),
            SourceArtifact("semantic_core", core.read_bytes()),
        ),
    )


def test_explicit_subtype_boundary_and_identity_policy():
    release = prepare_release(inputs())
    observed = dict(
        modality="asserted", polarity=True, reporter="Alice", channel="Straße", hedge="measured"
    )
    assert (
        release.validate_json("DomainQualification", canonical_bytes(observed)).model_dump()
        == observed
    )
    leaf = release.qualification_definition("DomainQualification")
    assert set(leaf.ancestors) == {"Qualification", "ReportQualification"}

    def identity(value):
        return release.fact_identity(
            "scope", "subject", "label", "same", value, qualification_class="DomainQualification"
        )

    first = identity(observed)
    assert identity(dict(observed, reporter="Bob", channel="STRASSE")) == first
    assert identity(dict(observed, hedge="inferred")) != first
    with pytest.raises(ValueError, match="undeclared qualification reporter"):
        release.fact_identity("scope", "subject", "label", "same", observed)
    with pytest.raises(ValueError, match="not an admitted Qualification"):
        release.qualification_definition("Unrelated")
    with pytest.raises(ValidationError):
        release.validate_json("DomainQualification", b'{"reporter":"Alice"}')
