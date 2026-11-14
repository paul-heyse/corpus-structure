"""Shared controlled inputs and builders for characterization support."""

from pathlib import Path
from typing import Any

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization import characterization_inputs, occurrence_id


@pytest.fixture(scope="module")
def prepared():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        characterization_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )


def layer_payload(prepared) -> dict[str, Any]:
    base = {"task_id": 7, "product_key": "document", "content_digest": "a" * 64}
    projection = "b" * 64
    selector = {"projection": projection, "native_pointer": "#/texts/0", "page": 3}
    scope = {
        "source_view_ids": [11],
        "source_views": [
            {
                "source_view_id": 11,
                "key": "section-source-v1",
                "base_document": base,
                "section_pointer": "#/groups/0",
                "membership": "descendants",
                "projection_digest": projection,
                "recipe_digest": "c" * 64,
            }
        ],
        "profile": "full",
        "selectors": [selector],
    }
    extents = [
        dict(
            projection=projection,
            source_view_id=11,
            native_pointer="#/texts/0",
            page=3,
            start=0,
            end=3,
            text="all",
            synthetic=False,
        )
    ]
    occurrence = {"local_id": occurrence_id(base, extents), "extents": extents}

    # This expected graph is literal test data: scope distinction is not produced by a constructor.
    def term(key, kind, value, children=()):
        return {
            "local_id": key,
            "family": "scope",
            "kind": kind,
            "vocabulary": "logic",
            "value": value,
            "status": "interpreted",
            "occurrences": [occurrence["local_id"]],
            "children": list(children),
        }

    def edge(role, target):
        return {"role": role, "target": target, "structural": True}

    return {
        "format": "characterization-layer-v1",
        "base_document": base,
        "release_id": prepared.release_id,
        "operation": {
            "key": "text.characterize",
            "version": "1",
            "runtime": "test-runtime",
            "model": "none",
            "grammar": "logic-1",
            "configuration": "cfg",
            "input": "source-1",
            "context": "section",
            "produced_families": ["scope"],
            "outcomes": ["complete", "partial", "failed"],
            "result_determinants": ["grammar", "input", "context"],
        },
        "source_scope": scope,
        "outcome": "complete",
        "occurrences": [occurrence],
        "terms": [
            term("p", "predicate", "P"),
            term("x", "participant", "x"),
            term("r", "predicate", "R"),
            term(
                "forall",
                "binder",
                "all",
                [edge("variable", "x"), edge("restrictor", "r"), edge("body", "p")],
            ),
            term("not_all", "operator", "not", [edge("target", "forall")]),
            term("not_p", "operator", "not", [edge("target", "p")]),
            term(
                "all_not",
                "binder",
                "all",
                [edge("variable", "x"), edge("restrictor", "r"), edge("body", "not_p")],
            ),
            term("or", "operator", "or", [edge("left", "p"), edge("right", "r")]),
        ],
        "coverage": [
            {
                "family": "scope",
                "operation": "text.characterize",
                "eligible": [selector],
                "examined": [selector],
                "availability": "available",
                "outcome": "complete",
                "profile": "full",
            }
        ],
    }
