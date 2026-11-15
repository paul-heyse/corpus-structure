"""Exact declared aliases and bounds, independent of retired publication orchestration."""

import yaml


def test_native_constraints_prepares_datatype_aliases_and_scientific_bounds():

    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.property_constraints import native_constraints

    source = {
        "id": "https://example/alias",
        "name": "alias",
        "prefixes": {"ex": "https://example/"},
        "default_prefix": "ex",
        "types": {
            "decimal": {"base": "Decimal"},
            "Amount": {"typeof": "decimal"},
            "Cost": {"typeof": "Amount"},
        },
        "classes": {"Thing": {"attributes": {"cost": {"range": "Cost", "minimum_value": "1e10"}}}},
    }
    prepared = prepare_release(
        SourceBundle("alias", (SourceArtifact("alias", yaml.safe_dump(source).encode()),))
    )
    constraints = native_constraints(prepared)
    assert constraints["https://example/Thing", "https://example/cost"]["native_range"] == "decimal"
    assert (
        constraints["https://example/Thing", "https://example/cost"]["native_minimum"]
        == "10000000000"
    )

