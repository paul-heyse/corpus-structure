"""Independent entity/exclusion semantics for current rich identity controls."""

from typing import Any


def source_values(*, keyed=False, located=True):
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
    }
