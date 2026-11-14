"""Controlled five-family policy-authority composition; no preparation at import."""

from pathlib import Path

import yaml

from corpus_structure.evaluate.record_references import reference_inputs
from corpus_structure.semantic import SourceArtifact, SourceBundle
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_assertions import source_reading_inputs


def policy_inputs(bundle):
    # Alignment owns a five-family contract. Reuse its actual other four families,
    # preserving the deliberately small two-cell table fixture as the fifth.
    document = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / "domains/statistics/semantic.yaml").read_bytes()
    )
    document["classes"].pop("TableRecordFields")
    document["imports"] = ["core"]
    document["name"] = "statistics_policy_fixture"
    module = SourceArtifact("statistics_policy_fixture", yaml.safe_dump(document).encode())
    root = SourceArtifact(
        "policy-fixture-root",
        canonical_bytes(
            dict(
                id="https://example/policy-fixture-root",
                name="policy_fixture_root",
                imports=[bundle.root, module.name],
            )
        ),
    )
    complete = SourceBundle(root.name, (*bundle.sources, module, root))
    return reference_inputs(source_reading_inputs(complete))
