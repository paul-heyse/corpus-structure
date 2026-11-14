"""Authored conditional-schema inputs shared by compiler and binding controls."""

from __future__ import annotations

from typing import Any

import yaml

from corpus_structure.semantic import SourceArtifact, SourceBundle


def rule():
    return {
        "preconditions": {"slot_conditions": {"status": {"equals_string": "ready"}}},
        "postconditions": {"slot_conditions": {"label": {"required": True}}},
        "elseconditions": {"slot_conditions": {"reason": {"required": True}}},
    }


def schema(rules=None) -> dict[str, Any]:
    return {
        "id": "https://example.org/conditional",
        "name": "conditional",
        "prefixes": {"ex": "https://example.org/", "xsd": "http://www.w3.org/2001/XMLSchema#"},
        "default_prefix": "ex",
        "types": {
            "string": {"base": "str", "uri": "xsd:string"},
            "decimal": {"base": "Decimal", "uri": "xsd:decimal"},
            "date": {"base": "XSDDate", "uri": "xsd:date"},
        },
        "classes": {
            "Thing": {
                "attributes": {
                    "id": {"identifier": True},
                    "status": {"range": "string"},
                    "label": {"range": "string"},
                    "reason": {"range": "string"},
                    "amount": {"range": "decimal"},
                    "when": {"range": "date"},
                },
                "rules": [rule()] if rules is None else rules,
            }
        },
    }


def bundle(data):
    return SourceBundle(
        "conditional", (SourceArtifact("conditional", yaml.safe_dump(data).encode()),)
    )
