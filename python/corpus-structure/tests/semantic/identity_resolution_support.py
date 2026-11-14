"""Shared controlled inputs and builders for identity resolution support."""

from functools import cache
from pathlib import Path
from typing import Any

import yaml

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.proposals import proposal_inputs
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies


@cache
def release(keyed=False):
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    person: dict[str, Any] = {
        "is_a": "Entity",
        "annotations": {"cs:scope": "global"},
        "attributes": {"serial": {"range": "string"}},
    }
    if keyed:
        person["unique_keys"] = {"serial": {"unique_key_slots": ["serial"]}}
    domain = {
        "id": "https://example.org/identity",
        "name": "identity",
        "imports": ["core"],
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "classes": {"Person": person},
    }
    bundle = SourceBundle(
        "domain",
        (
            SourceArtifact("core", core.read_bytes()),
            SourceArtifact("domain", yaml.safe_dump(domain).encode()),
        ),
    )
    return prepare_release(
        proposal_inputs(bundle),
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2"),
    )


def source(*, keyed=False, located=True):
    entities: list[dict[str, Any]] = [
        {
            "id": name,
            "class_iri": "https://example.org/Person",
            "label": "Alice",
            "attributes": [
                {
                    "predicate": "https://example.org/serial",
                    "value": {"kind": "text", "text": "same"},
                }
            ]
            if keyed
            else [],
        }
        for name in ("a", "b", "c")
    ]
    evidence = {
        "sentence": "s",
        "quote": "Two distinct people",
        "role": "primary",
        "placement": "exact",
        "outcome": "located" if located else "unlocated",
        "matches": 1,
        "picked": False,
        "locator": "doc#s",
        "start": 0,
        "end": 19,
    }
    for entity in entities:
        for attribute in entity["attributes"]:
            attribute.update(
                qualification={"modality": "asserted", "polarity": True},
                establishment="stated",
                evidence=[dict(evidence)],
            )
    return {
        "id": 9,
        "observation_key": "observation:stable",
        "payload_definition": "AgentStoredBatch",
        "payload": {
            "unit_ref": "u",
            "entities": entities,
            "identity_exclusions": [
                {
                    "id": "split",
                    "left": {"kind": "local", "target": "a"},
                    "right": {"kind": "local", "target": "c"},
                    "reason": "distinct",
                    "evidence": [evidence],
                }
            ],
        },
    }
