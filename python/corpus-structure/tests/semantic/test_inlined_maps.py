"""LinkML maps are keyed collections; list order must not become domain meaning."""

from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from corpus_structure.semantic import (
    SourceArtifact,
    SourceBundle,
    prepare_release,
)


def inputs():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    schema = {
        "id": "https://example.org/maps",
        "name": "maps",
        "imports": ["semantic_core"],
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "classes": {
            "Thing": {"attributes": {"label": {}}},
            "Parameter": {
                "attributes": {
                    "key": {"identifier": True},
                    "value": {"range": "decimal", "required": True},
                }
            },
            "MappedQualification": {
                "is_a": "Qualification",
                "attributes": {
                    "parameters": {"range": "Parameter", "multivalued": True, "inlined": True}
                },
            },
        },
    }
    return SourceBundle(
        "maps",
        (
            SourceArtifact("maps", yaml.safe_dump(schema).encode()),
            SourceArtifact("semantic_core", core.read_bytes()),
        ),
    )


def test_keyed_member_shape_rejects_mismatched_identifier():
    p = prepare_release(inputs())
    with pytest.raises(ValidationError, match="identifier"):
        p.validate_python(
            "MappedQualification",
            {
                "modality": "asserted",
                "polarity": True,
                "parameters": {"wrong": {"key": "scale", "value": Decimal("2")}},
            },
        )


def test_map_order_preserves_typed_qualification_identity():
    prepared = prepare_release(inputs())
    parameters = {
        "scale": {"key": "scale", "value": Decimal("2.00")},
        "shape": {"key": "shape", "value": Decimal("3.00")},
    }
    first: dict[str, object] = {
        "modality": "asserted",
        "polarity": True,
        "parameters": parameters,
    }
    second = {**first, "parameters": dict(reversed(tuple(parameters.items())))}
    assert prepared.fact_identity(
        "identity:scope",
        "subject",
        "https://example.org/label",
        "report",
        first,
        qualification_class="MappedQualification",
    ) == prepared.fact_identity(
        "identity:scope",
        "subject",
        "https://example.org/label",
        "report",
        second,
        qualification_class="MappedQualification",
    )
    changed = {
        **first,
        "parameters": {**parameters, "scale": {"key": "scale", "value": Decimal("4")}},
    }
    assert prepared.fact_identity(
        "identity:scope",
        "subject",
        "https://example.org/label",
        "report",
        first,
        qualification_class="MappedQualification",
    ) != prepared.fact_identity(
        "identity:scope",
        "subject",
        "https://example.org/label",
        "report",
        changed,
        qualification_class="MappedQualification",
    )


def test_distinct_semantic_scope_keeps_distinct_qualification_identity():
    prepared = prepare_release(inputs())
    first: dict[str, object] = {
        "modality": "asserted",
        "polarity": True,
        "scope": {"extent": "section", "locator": "page#one"},
    }
    second = {**first, "scope": {"extent": "section", "locator": "page#two"}}
    assert prepared.fact_identity(
        "identity:scope",
        "subject",
        "https://example.org/label",
        "same",
        first,
    ) != prepared.fact_identity(
        "identity:scope",
        "subject",
        "https://example.org/label",
        "same",
        second,
    )
