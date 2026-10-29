"""Independent recursive reference positions and consumer-specific collection policies."""

from functools import cache
from typing import Any

import pytest
import yaml

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.domain_operations import (
    _claim_references,
    _entity_references,
    _reference,
)
from corpus_structure.semantic.reference_positions import (
    ReferencePositionError,
    collect_references,
    rewrite_references,
)


@cache
def prepared():
    document: dict[str, Any] = {
        "id": "https://example.org/positions",
        "name": "positions",
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "types": {"string": {"base": "str"}},
        "classes": {
            "Tag": {"attributes": {"id": {"identifier": True}}},
            "Child": {
                "attributes": {
                    "claims": {"multivalued": True, "annotations": {"cs:reference_role": "fact"}},
                    "entity": {"range": "Tag"},
                }
            },
            "Entry": {
                "attributes": {
                    "id": {"identifier": True, "annotations": {"cs:reference_role": "fact"}},
                    "text": {},
                }
            },
            "Root": {
                "attributes": {
                    "plain": {},
                    "claims": {"multivalued": True, "annotations": {"cs:reference_role": "fact"}},
                    "entities": {"range": "Tag", "multivalued": True},
                    "children": {
                        "range": "Child",
                        "multivalued": True,
                        "inlined": True,
                        "inlined_as_list": True,
                    },
                    "entries": {"range": "Entry", "multivalued": True, "inlined": True},
                }
            },
        },
    }
    return prepare_release(
        SourceBundle("positions", (SourceArtifact("positions", yaml.safe_dump(document).encode()),))
    )


def value() -> dict[str, Any]:
    return {
        "plain": "f1",
        "claims": ("f2", "f1", "f2"),
        "entities": ("e2", "e1"),
        "children": ({"claims": ("f3",), "entity": "e3"},),
        "entries": {"a": {"id": "a", "text": "same"}, "b": {"id": "b", "text": "same"}},
    }


def test_multivalued_nested_fact_and_nonentity_class_references_keep_positions():
    release, raw = prepared(), value()
    references = collect_references(release, "Root", raw)
    assert [r.target for r in references if r.path[:1] == ("claims",)] == ["f2", "f1", "f2"]
    assert {r.target for r in references if r.kind == "class"} == {"e1", "e2", "e3"}
    assert any(r.target == "f3" and r.path == ("children", 0, "claims", 0) for r in references)
    assert not any(r.path == ("plain",) for r in references)
    assert _claim_references(release, "Root", raw) == {"f1", "f2", "f3", "a", "b"}
    assert _entity_references(release, "Root", raw) == {"e1", "e2", "e3"}
    rewritten = _reference(release, "Root", raw, {"e1": "E1", "e3": "E3"}, {"f2": "F2", "f3": "F3"})
    assert rewritten is not None
    assert rewritten["claims"] == ("F2", "f1", "F2")
    assert rewritten["entities"] == ("e2", "E1")
    assert rewritten["children"] == ({"claims": ("F3",), "entity": "E3"},)
    assert rewritten["plain"] == "f1"


def test_keyed_collision_policy_is_explicit_and_distinct_members_always_refuse():
    release, raw = prepared(), value()
    mapping = {"a": "merged", "b": "merged"}
    rewritten = rewrite_references(
        release, "Root", raw, classes={}, facts=mapping, collision="equal"
    )
    assert rewritten["entries"] == {"merged": {"id": "merged", "text": "same"}}
    with pytest.raises(ReferencePositionError, match="collides"):
        rewrite_references(release, "Root", raw, classes={}, facts=mapping, collision="reject")
    raw["entries"]["b"]["text"] = "different"
    with pytest.raises(ReferencePositionError, match="collides"):
        rewrite_references(release, "Root", raw, classes={}, facts=mapping, collision="equal")


def test_proposal_and_domain_property_reference_use_declared_nonentity_carrier():
    from pathlib import Path

    from corpus_structure.semantic.domain_operations import _property_value
    from corpus_structure.semantic.proposals import locate_proposal, proposal_inputs

    from .test_proposals import batch, frame

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    declaration = b"""id: https://example.org/reference_domain
name: reference_domain
imports: [core]
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
classes:
  Tag:
    attributes:
      id: {identifier: true}
  Person:
    is_a: Entity
    attributes:
      tag: {range: Tag}
  TagReferenceValue:
    is_a: Value
    attributes:
      kind: {equals_string: tag_ref}
      target: {range: Tag, required: true}
"""
    release = prepare_release(
        proposal_inputs(
            SourceBundle(
                "reference_domain",
                (
                    SourceArtifact("core", core.read_bytes()),
                    SourceArtifact("reference_domain", declaration),
                ),
            )
        )
    )
    raw = batch()
    raw["claims"][0]["predicate"] = "https://example.org/tag"
    raw["claims"][0]["object"] = {"kind": "tag_ref", "target": "known:tag"}
    result = locate_proposal(
        release, raw, frame(), known_classes={"known:tag": ("https://example.org/Tag",)}
    )
    assert result.clean
    person = next(d for d in release.definitions if d.name == "Person")
    prop = next(p for p in person.properties if p.name == "tag")
    assert (
        _property_value(
            release, person, prop, raw["claims"][0]["object"], {"known:tag": "admitted:tag"}
        )
        == "admitted:tag"
    )
