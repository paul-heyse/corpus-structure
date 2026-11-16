"""Reference split membership follows the explicitly supplied schema."""

import pytest
import yaml

from corpus_structure.semantic import (
    PreparationError,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)


def domain(*, explicit_splits=False):
    document = {
        "id": "https://example.org/reference-test",
        "name": "reference_test",
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "classes": {"Thing": {}},
    }
    if explicit_splits:
        document["enums"] = {
            "ReferenceSplit": {
                "permissible_values": {
                    "domain_only": {"in_subset": ["executable"]},
                    "hidden": {},
                }
            }
        }
    return SourceBundle("domain", (SourceArtifact("domain", yaml.safe_dump(document).encode()),))


def test_schema_uses_its_explicit_splits_and_missing_schema_refuses():
    prepared = prepare_release(domain(explicit_splits=True))
    assert prepared.reference_splits() == {"domain_only"}
    with pytest.raises(PreparationError) as failure:
        prepare_release(domain()).reference_splits()
    assert failure.value.diagnostics[0].code == "missing_reference_splits"


def test_independent_supplied_split_schemas_never_share_membership():
    bundle = domain(explicit_splits=True)
    first = prepare_release(bundle)
    document = yaml.safe_load(bundle.sources[0].content)
    document["enums"]["ReferenceSplit"]["permissible_values"] = {
        "holdout": {"in_subset": ["executable"]},
        "domain_only": {},
    }
    second = prepare_release(
        SourceBundle(bundle.root, (SourceArtifact("domain", yaml.safe_dump(document).encode()),))
    )
    assert first.reference_splits() == {"domain_only"}
    assert second.reference_splits() == {"holdout"}
    assert first.release_id != second.release_id
